import { useState } from 'react'
import SearchBar from './components/SearchBar.jsx'
import ResearchBrief from './components/ResearchBrief.jsx'
import HistoryPanel from './components/HistoryPanel.jsx'
import { useTrace } from './hooks/useTrace.js'

const QUICK_GENES = [
  { symbol: 'BRCA2', label: 'Breast Cancer' },
  { symbol: 'EGFR', label: 'Lung Cancer' },
  { symbol: 'TP53', label: 'Tumor Suppressor' },
  { symbol: 'APOE', label: "Alzheimer's Risk" },
  { symbol: 'CFTR', label: 'Cystic Fibrosis' },
  { symbol: 'rs334', label: 'Sickle Cell' },
]

function GeneChip({ symbol, label, onPick, disabled }) {
  const [hover, setHover] = useState(false)
  const active = hover && !disabled

  return (
    <button
      type="button"
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
      onClick={() => onPick(symbol)}
      aria-label={`Trace ${symbol} — ${label}`}
      style={{
        background: active ? 'var(--accent-bg)' : 'var(--surface-2)',
        border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 20,
        padding: '6px 14px',
        display: 'inline-flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'background .15s ease, border-color .15s ease',
        outline: 'none',
      }}
    >
      <span
        style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: 12,
          fontWeight: 500,
          color: active ? 'var(--accent)' : 'var(--text-1)',
          lineHeight: 1.3,
          transition: 'color .15s ease',
        }}
      >
        {symbol}
      </span>
      <span
        style={{
          fontFamily: "'IBM Plex Sans', sans-serif",
          fontSize: 11,
          color: 'var(--text-3)',
          lineHeight: 1.3,
        }}
      >
        {label}
      </span>
    </button>
  )
}

export default function App() {
  const {
    loading,
    error,
    result,
    history,
    runTrace,
    loadFromHistory,
    deleteHistoryItem,
  } = useTrace()
  const [query, setQuery] = useState('')

  const handlePick = (symbol) => {
    setQuery(symbol)
    runTrace(symbol)
  }

  return (
    <div className="app">
      <header className="header" style={{ marginBottom: 36 }}>
        <div
          style={{
            fontFamily: "'Bricolage Grotesque', sans-serif",
            fontSize: 42,
            fontWeight: 600,
            color: 'var(--text-1)',
            letterSpacing: '-0.01em',
            lineHeight: 1.1,
          }}
        >
          GeneTrace
        </div>
        <div
          style={{
            fontFamily: "'IBM Plex Sans', sans-serif",
            fontSize: 16,
            color: 'var(--text-2)',
            marginTop: 4,
          }}
        >
          Biomedical Research Briefs
        </div>
        <p
          style={{
            fontFamily: "'IBM Plex Sans', sans-serif",
            fontSize: 13,
            color: 'var(--text-3)',
            maxWidth: 520,
            margin: '10px auto 0',
            lineHeight: 1.7,
          }}
        >
          GeneTrace pulls live data from ClinVar, PubMed, and UniProt to generate
          structured research briefs on any human gene or variant. Enter a gene symbol,
          variant ID, or select a quick example below.
        </p>
      </header>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          justifyContent: 'center',
          margin: '20px 0 24px',
        }}
      >
        {QUICK_GENES.map((g) => (
          <GeneChip
            key={g.symbol}
            symbol={g.symbol}
            label={g.label}
            onPick={handlePick}
            disabled={loading}
          />
        ))}
      </div>

      <div className="layout" style={{ marginTop: 24 }}>
        <main className="main">
          <SearchBar
            value={query}
            onChange={setQuery}
            onSubmit={runTrace}
            loading={loading}
          />

          {error && <div className="error">{error}</div>}

          {!result && !loading && (
            <div className="empty">
              Enter a gene symbol or variant identifier above to generate a structured
              research brief synthesized from ClinVar, PubMed, and UniProt.
            </div>
          )}

          {result && <ResearchBrief result={result} />}
        </main>

        <HistoryPanel
          items={history}
          onSelect={loadFromHistory}
          onDelete={deleteHistoryItem}
        />
      </div>
    </div>
  )
}
