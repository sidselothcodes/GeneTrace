function chipClass(score) {
  if (score >= 80) return 'good'
  if (score >= 50) return 'warn'
  return 'bad'
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path
        d="M2.5 4.5h11M6.5 4.5V3a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1.5M4 4.5l.6 8.4a1 1 0 0 0 1 .9h4.8a1 1 0 0 0 1-.9L12 4.5"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function HistoryPanel({ items, onSelect, onDelete }) {
  return (
    <aside className="history">
      <div className="history-title">Recent Traces</div>
      {items.length === 0 ? (
        <div className="history-empty">No traces yet</div>
      ) : (
        items.map((item) => (
          <div
            key={item.id}
            className="history-item"
            role="button"
            tabIndex={0}
            onClick={() => onSelect(item)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onSelect(item)
              }
            }}
          >
            <span className="history-item-name">{item.query}</span>
            <span className="history-item-right">
              <span className={`history-chip ${chipClass(item.eval_score)}`}>
                {Number(item.eval_score).toFixed(1)}
              </span>
              <button
                type="button"
                className="history-delete"
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete(item.id)
                }}
                aria-label={`Delete ${item.query}`}
              >
                <TrashIcon />
              </button>
            </span>
          </div>
        ))
      )}
    </aside>
  )
}
