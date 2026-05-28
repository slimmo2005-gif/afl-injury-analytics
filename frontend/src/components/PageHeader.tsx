interface PageHeaderProps {
  title: string
  subtitle: string
}

export default function PageHeader({ title, subtitle }: PageHeaderProps) {
  return (
    <div className="mb-6">
      <h2 className="text-2xl font-semibold text-slate-100">{title}</h2>
      <p className="text-slate-400 mt-1 text-sm max-w-2xl">{subtitle}</p>
    </div>
  )
}
