export default function SearchBar({ value, onChange, onSubmit, loading }) {
  const handleSubmit = (e) => {
    e.preventDefault()
    const v = (value || '').trim()
    if (!v || loading) return
    onSubmit(v)
  }

  return (
    <form className={`searchbar ${loading ? 'loading' : ''}`} onSubmit={handleSubmit}>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Gene or variant — BRCA2, EGFR, rs334..."
        disabled={loading}
        aria-label="Gene or variant query"
      />
      <button type="submit" disabled={loading || !(value || '').trim()}>
        {loading ? 'Tracing…' : 'Trace'}
      </button>
    </form>
  )
}
