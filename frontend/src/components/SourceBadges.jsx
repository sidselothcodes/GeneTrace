const LABELS = {
  clinvar: 'ClinVar',
  pubmed: 'PubMed',
  uniprot: 'UniProt',
}

export default function SourceBadges({ sources }) {
  const order = ['clinvar', 'pubmed', 'uniprot']
  const bySrc = Object.fromEntries(sources.map((s) => [s.source, s]))

  return (
    <div className="badges">
      {order.map((key) => {
        const item = bySrc[key] || { hits: 0 }
        const active = item.hits > 0
        return (
          <span key={key} className={`badge ${active ? 'active' : ''}`}>
            {LABELS[key]} · {item.hits}
          </span>
        )
      })}
    </div>
  )
}
