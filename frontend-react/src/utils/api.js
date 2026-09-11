/**
 * api.js — REST calls for status, ingestion, chapters
 */
const BASE = import.meta.env.DEV ? 'http://localhost:8000' : ''

export async function fetchStatus() {
  const res = await fetch(`${BASE}/api/status`)
  if (!res.ok) throw new Error('Status fetch failed')
  return res.json()
}

export async function fetchChapters() {
  const res = await fetch(`${BASE}/api/sources`)
  if (!res.ok) throw new Error('Chapters fetch failed')
  return res.json()
}

export async function fetchBooks() {
  const res = await fetch(`${BASE}/api/books`)
  if (!res.ok) throw new Error('Books fetch failed')
  return res.json()
}

export async function triggerIngest(opts = {}) {
  const res = await fetch(`${BASE}/api/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Ingest failed')
  }
  return res.json()
}

export async function fetchIngestionStatus() {
  const res = await fetch(`${BASE}/api/ingestion-status`)
  if (!res.ok) throw new Error('Ingestion status failed')
  return res.json()
}

export async function queryDirect(opts, fetchOpts = {}) {
  const res = await fetch(`${BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts),
    ...fetchOpts,
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Query failed')
  }
  return res.json()
}
