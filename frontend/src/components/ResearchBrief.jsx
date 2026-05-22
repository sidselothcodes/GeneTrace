import { useState } from 'react'
import SourceBadges from './SourceBadges.jsx'
import EvalScore from './EvalScore.jsx'

const SECTION_TITLES = [
  'GENE OVERVIEW',
  'ASSOCIATED CONDITIONS',
  'PROTEIN FUNCTION',
  'RECENT RESEARCH HIGHLIGHTS',
  'CLINICAL SIGNIFICANCE SUMMARY',
]

function parseSections(brief) {
  if (!brief) return {}
  const escaped = SECTION_TITLES.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const headerRegex = new RegExp(
    `^\\s*(?:#+\\s*|\\*\\*)?(${escaped.join('|')})\\s*[:：]?\\s*(?:\\*\\*)?\\s*$`,
    'i'
  )

  const out = {}
  const lines = brief.split('\n')
  let current = null
  let buffer = []
  const flush = () => {
    if (current) out[current] = buffer.join('\n').replace(/^\n+|\n+$/g, '')
  }
  for (const raw of lines) {
    const line = raw.trim()
    const match = line.match(headerRegex)
    if (match) {
      flush()
      current = match[1].toUpperCase()
      buffer = []
    } else if (current) {
      buffer.push(raw)
    }
  }
  flush()
  return out
}

function classifySignificance(sig) {
  if (!sig) return { label: 'Not classified', cls: 'sig-neutral' }
  const s = sig.toLowerCase()
  if (s.includes('likely pathogenic')) return { label: 'Likely pathogenic', cls: 'sig-pathogenic' }
  if (s.includes('pathogenic')) return { label: 'Pathogenic', cls: 'sig-pathogenic' }
  if (s.includes('likely benign')) return { label: 'Likely benign', cls: 'sig-benign' }
  if (s.includes('benign')) return { label: 'Benign', cls: 'sig-benign' }
  if (s.includes('uncertain') || s.includes('conflicting'))
    return { label: 'Uncertain significance', cls: 'sig-uncertain' }
  return { label: sig, cls: 'sig-neutral' }
}

function bySrc(sources) {
  return Object.fromEntries(sources.map((s) => [s.source, s]))
}

function GeneHeaderCard({ query, sources, brief, score, index }) {
  return (
    <div className="card gene-header" style={{ '--i': index }}>
      <div className="gene-name brico">{query}</div>
      <SourceBadges sources={sources} />
      <EvalScore score={score} sources={sources} brief={brief} />
    </div>
  )
}

function GeneOverviewCard({ sections, index }) {
  const text = sections['GENE OVERVIEW']
  if (!text) return null
  return (
    <div className="card" style={{ '--i': index }}>
      <div className="card-label">Gene Overview</div>
      <div className="card-content">{text}</div>
    </div>
  )
}

function ConditionsCard({ clinvar, index }) {
  const hasData = clinvar.data && clinvar.data.length > 0
  return (
    <div className="card" style={{ '--i': index }}>
      <div className="card-label">Associated Conditions · ClinVar</div>
      {hasData ? (
        clinvar.data.map((v, i) => {
          const sig = classifySignificance(v.clinical_significance)
          const conditions = (v.conditions || []).filter(Boolean).join(', ')
          return (
            <div className="variant-row" key={v.id || i}>
              <div className="variant-row-top">
                <span className="variant-name" title={v.variant_name}>
                  {v.variant_name || 'Variant'}
                </span>
                <span className={`sig-chip ${sig.cls}`}>{sig.label}</span>
              </div>
              {conditions && <div className="condition-text">{conditions}</div>}
            </div>
          )
        })
      ) : (
        <div className="empty-state">No ClinVar variants returned</div>
      )}
    </div>
  )
}

function ProteinCard({ uniprot, sections, index }) {
  const [expanded, setExpanded] = useState(false)
  const hasData = uniprot.data && uniprot.data.length > 0
  const fallback = sections['PROTEIN FUNCTION']

  if (!hasData && !fallback) {
    return (
      <div className="card" style={{ '--i': index }}>
        <div className="card-label">Protein Function · UniProt</div>
        <div className="empty-state">No reviewed UniProt entry available</div>
      </div>
    )
  }

  if (!hasData) {
    return (
      <div className="card" style={{ '--i': index }}>
        <div className="card-label">Protein Function · UniProt</div>
        <div className="card-content">{fallback}</div>
      </div>
    )
  }

  const u = uniprot.data[0]
  const full = u.function || ''
  const isLong = full.length > 400
  const shown = expanded || !isLong ? full : full.slice(0, 400) + '…'

  return (
    <div className="card" style={{ '--i': index }}>
      <div className="card-label">Protein Function · UniProt</div>
      <div className="protein-header">
        {u.protein_name} · {u.accession}
        {u.sequence_length ? ` · ${u.sequence_length} aa` : ''}
      </div>
      <div className="card-content">{shown}</div>
      {isLong && (
        <span className="show-more" onClick={() => setExpanded((v) => !v)}>
          {expanded ? 'Show less' : 'Show more'}
        </span>
      )}
    </div>
  )
}

function PubMedCard({ pubmed, index }) {
  const hits = pubmed?.hits ?? 0
  const hasData = pubmed?.data && pubmed.data.length > 0
  if (hits === 0 || !hasData) return null

  return (
    <div className="card" style={{ '--i': index }}>
      <div className="card-label">Recent Research · PubMed</div>
      {pubmed.data.map((p, i) => {
        const meta = [
          (p.authors || []).slice(0, 3).join(', '),
          p.journal,
          p.year,
        ]
          .filter(Boolean)
          .join(' · ')
        return (
          <div className="paper-row" key={p.pmid || i}>
            <div className="paper-title">{p.title}</div>
            {meta && <div className="paper-meta">{meta}</div>}
          </div>
        )
      })}
    </div>
  )
}

function SummaryCard({ sections, index }) {
  const text = sections['CLINICAL SIGNIFICANCE SUMMARY']
  if (!text) return null
  return (
    <div className="card" style={{ '--i': index }}>
      <div className="card-label">Clinical Significance Summary</div>
      <div className="card-content">{text}</div>
    </div>
  )
}

export default function ResearchBrief({ result }) {
  const { query, brief, eval_score, sources } = result
  const sections = parseSections(brief)
  const sourceMap = bySrc(sources)

  return (
    <>
      <GeneHeaderCard
        query={query}
        sources={sources}
        brief={brief}
        score={eval_score}
        index={0}
      />
      <GeneOverviewCard sections={sections} index={1} />
      <ConditionsCard clinvar={sourceMap.clinvar || { data: [] }} index={2} />
      <ProteinCard uniprot={sourceMap.uniprot || { data: [] }} sections={sections} index={3} />
      <PubMedCard pubmed={sourceMap.pubmed || { hits: 0, data: [] }} index={4} />
      <SummaryCard sections={sections} index={5} />
    </>
  )
}
