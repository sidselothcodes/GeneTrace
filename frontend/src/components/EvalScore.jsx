function scoreColor(value) {
  if (value >= 80) return 'var(--green)'
  if (value >= 50) return 'var(--amber)'
  return 'var(--red)'
}

function countWords(text) {
  if (!text) return 0
  const matches = text.match(/\b\w+\b/g)
  return matches ? matches.length : 0
}

function fmt(n) {
  return n.toFixed(1)
}

export default function EvalScore({ score, sources, brief }) {
  const value = Math.max(0, Math.min(100, Number(score) || 0))
  const color = scoreColor(value)

  const bySrc = Object.fromEntries(sources.map((s) => [s.source, s]))
  const clinvarHits = bySrc.clinvar?.hits ?? 0
  const pubmedHits = bySrc.pubmed?.hits ?? 0
  const uniprotHits = bySrc.uniprot?.hits ?? 0
  const words = countWords(brief)

  const clinvarPts = 30 * Math.min(clinvarHits / 3, 1)
  const pubmedPts = 30 * Math.min(pubmedHits / 3, 1)
  const uniprotPts = 20 * Math.min(uniprotHits / 1, 1)
  const briefPts = 20 * Math.min(words / 250, 1)
  const total = clinvarPts + pubmedPts + uniprotPts + briefPts

  return (
    <>
      <div className="eval-score">
        <span className="eval-score-label">Eval Score</span>
        <span className="eval-score-value" style={{ color }}>
          {fmt(value)} / 100
        </span>
      </div>
      <table className="eval-table">
        <thead>
          <tr>
            <th>Source</th>
            <th>Condition</th>
            <th>Points</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>ClinVar</td>
            <td>{clinvarHits} hits returned</td>
            <td>{fmt(clinvarPts)} pts</td>
          </tr>
          <tr>
            <td>PubMed</td>
            <td>{pubmedHits} hits returned</td>
            <td>{fmt(pubmedPts)} pts</td>
          </tr>
          <tr>
            <td>UniProt</td>
            <td>{uniprotHits} reviewed entries</td>
            <td>{fmt(uniprotPts)} pts</td>
          </tr>
          <tr>
            <td>Brief</td>
            <td>{words} words generated</td>
            <td>{fmt(briefPts)} pts</td>
          </tr>
          <tr className="total">
            <td>Total</td>
            <td></td>
            <td>{fmt(total)} / 100</td>
          </tr>
        </tbody>
      </table>
    </>
  )
}
