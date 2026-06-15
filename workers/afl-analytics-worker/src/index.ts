/**
 * Edge analytics for static hosting (e.g. GitHub Pages).
 * - POST /visit { sessionId } — records one row per browser session (CF-IPCountry).
 * - POST /admin/stats { password } — returns session totals and counts by country (excludes owner devices).
 * - POST /admin/exclude-session { password, sessionId } — stop counting this browser; removes existing row.
 * - POST /admin/include-session { password, sessionId } — allow counting again (optional).
 * - POST /admin/device-status { password, sessionId } — whether this tab’s session is in visitor logs.
 * - POST /feedback { message, contactEmail?, contactWhatsapp?, contactDiscord? }
 * - POST /admin/feedback { password } — list feedback grouped by date.
 *
 * Deploy: see ../SETUP.txt. Set secret ADMIN_PASSWORD (do not commit real passwords).
 */

export interface Env {
  DB: D1Database;
  ADMIN_PASSWORD: string;
}

const JSON_HEADERS = {
  'content-type': 'application/json; charset=utf-8',
} as const;

function corsHeaders(origin: string | null): HeadersInit {
  const allow =
    origin &&
    (/^https:\/\/[a-z0-9-]+\.github\.io$/i.test(origin) ||
      /^http:\/\/localhost(:\d+)?$/i.test(origin) ||
      /^http:\/\/127\.0\.0\.1(:\d+)?$/i.test(origin))
      ? origin
      : '*';
  return {
    'access-control-allow-origin': allow,
    'access-control-allow-methods': 'GET, POST, OPTIONS',
    'access-control-allow-headers': 'content-type',
    'access-control-max-age': '86400',
  };
}

const SESSION_ID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isValidSessionId(sessionId: string): boolean {
  return SESSION_ID_RE.test(sessionId);
}

async function isSessionExcluded(env: Env, sessionId: string): Promise<boolean> {
  const row = await env.DB.prepare(
    `SELECT 1 AS x FROM excluded_sessions WHERE session_id = ? LIMIT 1`,
  )
    .bind(sessionId)
    .first<{ x: number }>();
  return Boolean(row);
}

async function verifyAdminPassword(env: Env, password: string): Promise<boolean> {
  const expected = (env.ADMIN_PASSWORD || '').trim();
  const supplied = password.trim();
  return Boolean(expected && supplied === expected);
}

/** Idempotent — stats/exclude features need this table (migration may not have been run). */
async function ensureExcludedSessionsTable(env: Env): Promise<void> {
  await env.DB.prepare(
    `CREATE TABLE IF NOT EXISTS excluded_sessions (
      session_id TEXT PRIMARY KEY NOT NULL,
      excluded_at TEXT NOT NULL DEFAULT (datetime('now'))
    )`,
  ).run();
}

const VISITS_NOT_EXCLUDED = `NOT EXISTS (
  SELECT 1 FROM excluded_sessions e WHERE e.session_id = visits.session_id
)`;

function jsonResponse(
  env: Env,
  request: Request,
  status: number,
  body: unknown,
): Response {
  const origin = request.headers.get('Origin');
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...JSON_HEADERS, ...corsHeaders(origin) },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const origin = request.headers.get('Origin');
    const baseCors = corsHeaders(origin);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: { ...baseCors } });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/$/, '') || '/';

    try {
      await ensureExcludedSessionsTable(env);

      if (path === '/visit' && request.method === 'POST') {
        let payload: { sessionId?: string };
        try {
          payload = (await request.json()) as { sessionId?: string };
        } catch {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid JSON' });
        }
        const sessionId = typeof payload.sessionId === 'string' ? payload.sessionId.trim() : '';
        if (!isValidSessionId(sessionId)) {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid sessionId' });
        }
        if (await isSessionExcluded(env, sessionId)) {
          return jsonResponse(env, request, 200, { ok: true, recorded: false, excluded: true });
        }
        const country = request.headers.get('CF-IPCountry')?.trim() || 'XX';
        const safeCountry = country.length <= 4 ? country.toUpperCase() : 'XX';

        const result = await env.DB.prepare(
          `INSERT OR IGNORE INTO visits (session_id, country) VALUES (?, ?)`,
        )
          .bind(sessionId, safeCountry)
          .run();

        const inserted = (result.meta?.changes ?? 0) > 0;
        return jsonResponse(env, request, 200, { ok: true, recorded: inserted });
      }

      if (path === '/admin/stats' && request.method === 'POST') {
        let payload: { password?: string };
        try {
          payload = (await request.json()) as { password?: string };
        } catch {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid JSON' });
        }
        const password = typeof payload.password === 'string' ? payload.password : '';
        if (!(env.ADMIN_PASSWORD || '').trim()) {
          return jsonResponse(env, request, 503, {
            ok: false,
            error:
              'ADMIN_PASSWORD is not set on the worker. Run: cd workers/analytics-worker && npx wrangler secret put ADMIN_PASSWORD',
          });
        }
        if (!(await verifyAdminPassword(env, password))) {
          return jsonResponse(env, request, 401, {
            ok: false,
            error: 'Incorrect password. Reset with: npx wrangler secret put ADMIN_PASSWORD',
          });
        }

        const totalRow = await env.DB.prepare(
          `SELECT COUNT(*) AS c FROM visits WHERE ${VISITS_NOT_EXCLUDED}`,
        ).first<{ c: number }>();
        const totalSessions = Number(totalRow?.c ?? 0);

        const excludedRow = await env.DB.prepare(
          `SELECT COUNT(*) AS c FROM excluded_sessions`,
        ).first<{ c: number }>();
        const excludedDeviceCount = Number(excludedRow?.c ?? 0);

        const byCountry = await env.DB.prepare(
          `SELECT country, COUNT(*) AS count FROM visits WHERE ${VISITS_NOT_EXCLUDED}
           GROUP BY country ORDER BY count DESC`,
        ).all<{ country: string; count: number }>();

        const byDay = await env.DB.prepare(
          `SELECT date(created_at) AS day, COUNT(*) AS count
           FROM visits
           WHERE ${VISITS_NOT_EXCLUDED}
           GROUP BY date(created_at)
           ORDER BY day ASC`,
        ).all<{ day: string; count: number }>();

        const rows = (byCountry.results ?? []).map((r) => ({
          country: r.country,
          count: Number(r.count),
        }));

        const dayRows = (byDay.results ?? []).map((r) => ({
          day: r.day,
          count: Number(r.count),
        }));

        return jsonResponse(env, request, 200, {
          ok: true,
          totalSessions,
          excludedDeviceCount,
          byCountry: rows,
          byDay: dayRows,
        });
      }

      if (path === '/admin/exclude-session' && request.method === 'POST') {
        let payload: { password?: string; sessionId?: string };
        try {
          payload = (await request.json()) as { password?: string; sessionId?: string };
        } catch {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid JSON' });
        }
        const password = typeof payload.password === 'string' ? payload.password : '';
        if (!(await verifyAdminPassword(env, password))) {
          return jsonResponse(env, request, 401, { ok: false, error: 'Unauthorized' });
        }
        const sessionId = typeof payload.sessionId === 'string' ? payload.sessionId.trim() : '';
        if (!isValidSessionId(sessionId)) {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid sessionId' });
        }
        await env.DB.prepare(
          `INSERT OR IGNORE INTO excluded_sessions (session_id) VALUES (?)`,
        )
          .bind(sessionId)
          .run();
        const deleteResult = await env.DB.prepare(`DELETE FROM visits WHERE session_id = ?`)
          .bind(sessionId)
          .run();
        const removedFromVisits = (deleteResult.meta?.changes ?? 0) > 0;
        return jsonResponse(env, request, 200, {
          ok: true,
          excluded: true,
          sessionId,
          removedFromVisits,
        });
      }

      if (path === '/admin/include-session' && request.method === 'POST') {
        let payload: { password?: string; sessionId?: string };
        try {
          payload = (await request.json()) as { password?: string; sessionId?: string };
        } catch {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid JSON' });
        }
        const password = typeof payload.password === 'string' ? payload.password : '';
        if (!(await verifyAdminPassword(env, password))) {
          return jsonResponse(env, request, 401, { ok: false, error: 'Unauthorized' });
        }
        const sessionId = typeof payload.sessionId === 'string' ? payload.sessionId.trim() : '';
        if (!isValidSessionId(sessionId)) {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid sessionId' });
        }
        const del = await env.DB.prepare(`DELETE FROM excluded_sessions WHERE session_id = ?`)
          .bind(sessionId)
          .run();
        const wasExcluded = (del.meta?.changes ?? 0) > 0;
        return jsonResponse(env, request, 200, {
          ok: true,
          excluded: false,
          sessionId,
          removedFromExcludedList: wasExcluded,
        });
      }

      if (path === '/admin/device-status' && request.method === 'POST') {
        let payload: { password?: string; sessionId?: string };
        try {
          payload = (await request.json()) as { password?: string; sessionId?: string };
        } catch {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid JSON' });
        }
        const password = typeof payload.password === 'string' ? payload.password : '';
        if (!(await verifyAdminPassword(env, password))) {
          return jsonResponse(env, request, 401, { ok: false, error: 'Unauthorized' });
        }
        const sessionId = typeof payload.sessionId === 'string' ? payload.sessionId.trim() : '';
        if (!isValidSessionId(sessionId)) {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid sessionId' });
        }
        const visitRow = await env.DB.prepare(
          `SELECT country FROM visits WHERE session_id = ? LIMIT 1`,
        )
          .bind(sessionId)
          .first<{ country: string }>();
        const isExcluded = await isSessionExcluded(env, sessionId);
        return jsonResponse(env, request, 200, {
          ok: true,
          sessionId,
          isExcluded,
          isInVisitsTable: Boolean(visitRow),
          countsInVisitorStats: Boolean(visitRow) && !isExcluded,
          country: visitRow?.country ?? null,
        });
      }

      if (path === '/feedback' && request.method === 'POST') {
        let payload: {
          message?: string;
          contactEmail?: string;
          contactWhatsapp?: string;
          contactDiscord?: string;
        };
        try {
          payload = (await request.json()) as typeof payload;
        } catch {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid JSON' });
        }
        const message = typeof payload.message === 'string' ? payload.message.trim() : '';
        if (!message) {
          return jsonResponse(env, request, 400, { ok: false, error: 'Message is required' });
        }
        const words = message.split(/\s+/).filter((w) => w.length > 0);
        if (words.length > 200) {
          return jsonResponse(env, request, 400, { ok: false, error: 'Message exceeds 200 words' });
        }
        const email =
          typeof payload.contactEmail === 'string' ? payload.contactEmail.trim().slice(0, 200) : '';
        const whatsapp =
          typeof payload.contactWhatsapp === 'string'
            ? payload.contactWhatsapp.trim().slice(0, 120)
            : '';
        const discord =
          typeof payload.contactDiscord === 'string' ? payload.contactDiscord.trim().slice(0, 120) : '';

        await env.DB.prepare(
          `INSERT INTO feedback (message, contact_email, contact_whatsapp, contact_discord, word_count)
           VALUES (?, ?, ?, ?, ?)`,
        )
          .bind(
            message,
            email || null,
            whatsapp || null,
            discord || null,
            words.length,
          )
          .run();

        return jsonResponse(env, request, 200, { ok: true });
      }

      if (path === '/admin/feedback' && request.method === 'POST') {
        let payload: { password?: string };
        try {
          payload = (await request.json()) as { password?: string };
        } catch {
          return jsonResponse(env, request, 400, { ok: false, error: 'Invalid JSON' });
        }
        const password = typeof payload.password === 'string' ? payload.password : '';
        if (!(await verifyAdminPassword(env, password))) {
          return jsonResponse(env, request, 401, { ok: false, error: 'Unauthorized' });
        }

        const rows = await env.DB.prepare(
          `SELECT id, message, contact_email, contact_whatsapp, contact_discord, word_count,
                  date(created_at) AS day, created_at
           FROM feedback
           ORDER BY created_at DESC
           LIMIT 500`,
        ).all<{
          id: number;
          message: string;
          contact_email: string | null;
          contact_whatsapp: string | null;
          contact_discord: string | null;
          word_count: number;
          day: string;
          created_at: string;
        }>();

        const items = (rows.results ?? []).map((r) => ({
          id: r.id,
          message: r.message,
          contactEmail: r.contact_email ?? '',
          contactWhatsapp: r.contact_whatsapp ?? '',
          contactDiscord: r.contact_discord ?? '',
          wordCount: r.word_count,
          day: r.day,
          createdAt: r.created_at,
        }));

        const byDayMap = new Map<string, typeof items>();
        for (const item of items) {
          const list = byDayMap.get(item.day) ?? [];
          list.push(item);
          byDayMap.set(item.day, list);
        }
        const byDay = [...byDayMap.entries()]
          .sort((a, b) => b[0].localeCompare(a[0]))
          .map(([day, dayItems]) => ({ day, items: dayItems }));

        return jsonResponse(env, request, 200, { ok: true, total: items.length, byDay });
      }

      if (path === '/health' && request.method === 'GET') {
        return jsonResponse(env, request, 200, { ok: true, service: 'afl-injury-analytics' });
      }

      return jsonResponse(env, request, 404, { ok: false, error: 'Not found' });
    } catch (e) {
      console.error(e);
      return jsonResponse(env, request, 500, { ok: false, error: 'Server error' });
    }
  },
};
