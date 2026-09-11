/**
 * useRAG.js
 * Core RAG state machine — handles messages from WebSocket,
 * builds chat history, manages settings and validation.
 */
import { useState, useCallback, useRef, useEffect } from 'react'
import { queryDirect, fetchStatus } from '../utils/api'

export const DEFAULT_SETTINGS = {
  topK: 5,
  temperature: 0.1,
  useHybrid: true,
  useReranker: true,
  nCandidates: 20,
}

// ── Validators (client-side, mirrors backend) ────────────────
export function validateQuery(query) {
  const errors = []
  const q = query.trim()
  if (!q) errors.push('השאלה לא יכולה להיות ריקה')
  else if (q.length < 2) errors.push('השאלה קצרה מדי (לפחות 2 תווים)')
  else if (q.length > 2000) errors.push('השאלה ארוכה מדי (עד 2000 תווים)')
  return errors
}

export function validateSettings(s) {
  const errors = []
  if (s.topK < 1 || s.topK > 20) errors.push('Top K חייב להיות בין 1 ל-20')
  if (s.temperature < 0 || s.temperature > 1) errors.push('טמפרטורה חייבת להיות בין 0 ל-1')
  if (s.nCandidates < 5 || s.nCandidates > 50) errors.push('מועמדים חייב להיות בין 5 ל-50')
  return errors
}

export function useRAG() {
  const [messages, setMessages] = useState([])
  const [sources, setSources] = useState([])
  const [settings, setSettings] = useState(DEFAULT_SETTINGS)
  const [serverStatus, setServerStatus] = useState({ docsCount: 0, model: '', ollama: false })
  const [isQuerying, setIsQuerying] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')
  const [validationErrors, setValidationErrors] = useState([])
  const [chatBook, setChatBook] = useState(null)
  const abortControllerRef = useRef(null)

  // ── Fetch server status ────────────────────────────────────
  const refreshStatus = useCallback(async () => {
    try {
      const data = await fetchStatus()
      setServerStatus({
        docsCount: data.docs_count || 0,
        model: data.model || '',
        ollama: data.ollama_running || false,
        modelAvailable: data.model_available || false,
      })
    } catch (err) {
      console.error('Failed to fetch status', err)
    }
  }, [])

  useEffect(() => {
    refreshStatus()
    // Optionally poll every 10s
    const interval = setInterval(refreshStatus, 10000)
    return () => clearInterval(interval)
  }, [refreshStatus])

  // ── Send a query ─────────────────────────────────────────
  const sendQuery = useCallback(async (query) => {
    // Client-side validation
    const qErrors = validateQuery(query)
    const sErrors = validateSettings(settings)
    const allErrors = [...qErrors, ...sErrors]

    if (allErrors.length > 0) {
      setValidationErrors(allErrors)
      return false
    }

    setValidationErrors([])

    // Add user message
    const userId = `user-${Date.now()}`
    const assistantId = `asst-${Date.now()}`

    setMessages(prev => [
      ...prev,
      { id: userId, role: 'user', content: query.trim(), time: new Date() },
      { id: assistantId, role: 'assistant', content: '', streaming: true, time: new Date() },
    ])

    setSources([])
    setIsQuerying(true)
    setStatusMsg('שולח שאלה...')

    try {
      // Setup abort controller
      abortControllerRef.current = new AbortController()

      const payload = {
        query: query.trim(),
        top_k: settings.topK,
        temperature: settings.temperature,
        use_hybrid: settings.useHybrid,
        use_reranker: settings.useReranker,
        n_candidates: settings.nCandidates,
      }
      if (chatBook) {
        payload.book_filename = chatBook
      }

      const res = await queryDirect(payload, { signal: abortControllerRef.current.signal })

      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: res.answer, streaming: false, done: true }
          : m
      ))
      setSources(res.sources || [])
      setStatusMsg('')
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: '[בוטל על ידי המשתמש]', streaming: false, cancelled: true }
            : m
        ))
      } else {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: `שגיאה: ${err.message}`, streaming: false, error: true }
            : m
        ))
      }
      setStatusMsg('')
    } finally {
      setIsQuerying(false)
      abortControllerRef.current = null
    }

    return true
  }, [settings])

  const cancelQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }, [])

  const clearChat = useCallback(() => {
    setMessages([])
    setSources([])
    setStatusMsg('')
    setValidationErrors([])
  }, [])

  return {
    messages,
    sources,
    settings,
    setSettings,
    serverStatus,
    isQuerying,
    statusMsg,
    validationErrors,
    setValidationErrors,
    sendQuery,
    cancelQuery,
    clearChat,
    refreshStatus,
    chatBook,
    setChatBook,
  }
}
