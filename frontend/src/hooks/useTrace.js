import { useCallback, useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || ''

export function useTrace() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/history`)
      if (!res.ok) throw new Error(`history failed (${res.status})`)
      const data = await res.json()
      setHistory(data)
    } catch (err) {
      console.warn('history error', err)
    }
  }, [])

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const runTrace = useCallback(
    async (query) => {
      const q = query.trim()
      if (!q) return
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API_BASE}/trace`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q }),
        })
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}))
          throw new Error(detail.detail || `request failed (${res.status})`)
        }
        const data = await res.json()
        setResult(data)
        loadHistory()
      } catch (err) {
        setError(err.message || 'Unknown error')
      } finally {
        setLoading(false)
      }
    },
    [loadHistory]
  )

  const loadFromHistory = useCallback((item) => {
    setResult({
      query: item.query,
      brief: item.brief,
      eval_score: item.eval_score,
      sources: [
        { source: 'clinvar', hits: item.clinvar_hits, data: [], error: null },
        { source: 'pubmed', hits: item.pubmed_hits, data: [], error: null },
        { source: 'uniprot', hits: item.uniprot_hits, data: [], error: null },
      ],
      created_at: item.created_at,
    })
    setError(null)
  }, [])

  const deleteHistoryItem = useCallback(
    async (id) => {
      try {
        const res = await fetch(`${API_BASE}/history/${id}`, { method: 'DELETE' })
        if (!res.ok) throw new Error(`delete failed (${res.status})`)
        // optimistic local refresh then full reload to stay in sync
        setHistory((prev) => prev.filter((h) => h.id !== id))
        loadHistory()
      } catch (err) {
        console.warn('delete error', err)
      }
    },
    [loadHistory]
  )

  return {
    loading,
    error,
    result,
    history,
    runTrace,
    loadFromHistory,
    deleteHistoryItem,
  }
}
