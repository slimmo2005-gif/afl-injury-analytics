import { UKRAINE_TRACKER_URL } from '../constants'

const products = [
  {
    name: 'Ukraine War Territory Tracker',
    description: 'Live map of territorial control changes',
    url: UKRAINE_TRACKER_URL,
    icon: '🗺️',
  },
]

export default function OtherProducts() {
  return (
    <div className="rounded-xl border border-slate-700/80 bg-slate-900/90 p-4 min-w-[220px] max-w-sm">
      <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-2">
        Other Slim Analytics products
      </p>
      <ul className="space-y-2">
        {products.map((p) => (
          <li key={p.url}>
            <a
              href={p.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-2 rounded-lg px-2 py-2 -mx-2 hover:bg-slate-800/80 transition-colors group"
            >
              <span className="text-lg shrink-0" aria-hidden>
                {p.icon}
              </span>
              <span className="min-w-0">
                <span className="text-sm text-slate-200 group-hover:text-cyan-300 block">
                  {p.name}
                  <span className="text-[10px] text-slate-500 ml-1" aria-hidden>
                    ↗
                  </span>
                </span>
                <span className="text-xs text-slate-500 block">{p.description}</span>
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}
