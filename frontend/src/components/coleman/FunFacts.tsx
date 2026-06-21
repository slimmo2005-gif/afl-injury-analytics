interface FunFactsProps {
  facts: string[]
}

export default function FunFacts({ facts }: FunFactsProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:p-6">
      <h3 className="text-sm font-medium text-slate-300 mb-4">Fun facts from the data</h3>
      <ul className="space-y-3">
        {facts.map((fact, i) => (
          <li
            key={i}
            className="flex gap-3 text-sm text-slate-300 leading-relaxed animate-in fade-in"
          >
            <span className="shrink-0 mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-afl-green/40 text-afl-gold text-xs font-bold">
              {i + 1}
            </span>
            <span>{fact}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
