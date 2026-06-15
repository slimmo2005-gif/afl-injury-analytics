-- Run once after creating the D1 database:
-- npx wrangler d1 execute afl-visits --remote --file=schema.sql

CREATE TABLE IF NOT EXISTS visits (
  session_id TEXT PRIMARY KEY NOT NULL,
  country TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_visits_country ON visits (country);
CREATE INDEX IF NOT EXISTS idx_visits_created ON visits (created_at);

CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message TEXT NOT NULL,
  contact_email TEXT,
  contact_whatsapp TEXT,
  contact_discord TEXT,
  word_count INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback (created_at);

CREATE TABLE IF NOT EXISTS excluded_sessions (
  session_id TEXT PRIMARY KEY NOT NULL,
  excluded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
