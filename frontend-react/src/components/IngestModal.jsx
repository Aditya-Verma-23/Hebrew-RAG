import { useState, useEffect, useRef } from 'react'
import styles from './IngestModal.module.css'
import { triggerIngest, fetchIngestionStatus, fetchBooks } from '../utils/api'

export default function IngestModal({ open, onClose, onComplete }) {
  const [opts, setOpts] = useState({ clear_existing: false, remove_nikud: true })
  const [phase, setPhase] = useState('idle') // idle | running | done | error
  const [progress, setProgress] = useState(0)
  const [msg, setMsg]   = useState('')
  const [books, setBooks] = useState([])
  const [selectedBook, setSelectedBook] = useState('')
  const [loadingBooks, setLoadingBooks] = useState(false)
  const [result, setResult] = useState(null)
  const pollRef = useRef(null)

  const reset = () => { setPhase('idle'); setProgress(0); setMsg(''); setResult(null) }

  const stopPoll = () => { if (pollRef.current) clearInterval(pollRef.current) }

  useEffect(() => { 
    if (open) { 
      setLoadingBooks(true)
      fetchBooks()
        .then(data => {
          setBooks(data.books || [])
          if (data.books?.length > 0) {
            setSelectedBook(data.books[0].filename)
          }
        })
        .catch(err => console.error(err))
        .finally(() => setLoadingBooks(false))
    } else { 
      stopPoll()
      reset() 
    } 
  }, [open])

  const handleStart = async () => {
    try {
      setPhase('running'); setProgress(5); setMsg('מתחיל טעינה...')
      await triggerIngest({ ...opts, epub_path: selectedBook })

      // Animate fake progress
      let fake = 5
      const fakeTimer = setInterval(() => {
        fake = Math.min(fake + Math.random() * 3, 85)
        setProgress(Math.round(fake))
      }, 800)

      // Poll real status
      pollRef.current = setInterval(async () => {
        try {
          const data = await fetchIngestionStatus()
          setMsg(data.message || 'מאנדקס...')
          if (data.status === 'done') {
            clearInterval(fakeTimer)
            stopPoll()
            setProgress(100)
            setPhase('done')
            setResult(data.progress || {})
            onComplete?.()
          } else if (data.status === 'error') {
            clearInterval(fakeTimer)
            stopPoll()
            setPhase('error')
            setMsg(data.message || 'שגיאה')
          }
        } catch {}
      }, 1500)

    } catch (e) {
      setPhase('error'); setMsg(e.message)
    }
  }

  if (!open) return null

  return (
    <div className={styles.overlay} onClick={phase === 'idle' ? onClose : undefined}>
      <div className={styles.box} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>📚 טעינת ספר עברי</h2>
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div className={styles.body}>
          {/* Book info */}
          <div className={styles.bookCard}>
            <span className={styles.bookIcon}>📖</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              {loadingBooks ? (
                <div className={styles.bookTitle}>טוען רשימת ספרים...</div>
              ) : books.length > 0 ? (
                <select 
                  className={styles.bookSelect} 
                  value={selectedBook} 
                  onChange={e => setSelectedBook(e.target.value)}
                  title={selectedBook}
                >
                  {books.map(b => (
                    <option key={b.filename} value={b.filename} title={b.filename}>
                      {b.filename} {b.status === 'Ready' ? '(מוכן)' : ''}
                    </option>
                  ))}
                </select>
              ) : (
                <div className={styles.bookTitle}>לא נמצאו ספרים בתיקיית data/</div>
              )}
              <div className={styles.bookMeta}>ספר עברי · EPUB</div>
            </div>
          </div>

          {/* Options */}
          {phase === 'idle' && (
            <div className={styles.options}>
              {[
                { key: 'clear_existing', label: 'נקה אינדקס קיים', desc: 'מחיקה ואינדוס מחדש' },
                { key: 'remove_nikud',   label: 'הסרת ניקוד', desc: 'מומלץ לחיפוש טוב יותר' },
              ].map(({ key, label, desc }) => (
                <label key={key} className={styles.optRow}>
                  <div>
                    <div className={styles.optLabel}>{label}</div>
                    <div className={styles.optDesc}>{desc}</div>
                  </div>
                  <span className={styles.toggle}>
                    <input
                      type="checkbox"
                      checked={opts[key]}
                      onChange={e => setOpts(p => ({ ...p, [key]: e.target.checked }))}
                    />
                    <span className={styles.slider} />
                  </span>
                </label>
              ))}
            </div>
          )}

          {/* Progress */}
          {(phase === 'running' || phase === 'done') && (
            <div className={styles.progress}>
              <div className={styles.progressBar}>
                <div className={styles.fill} style={{ width: `${progress}%` }} />
              </div>
              <p className={styles.progressMsg}>
                {phase === 'done' ? '✅ הטעינה הושלמה!' : msg || 'מאנדקס...'}
              </p>
              {result && (
                <div className={styles.summary}>
                  <span>📄 {result.chapters} פרקים</span>
                  <span>🔷 {result.chunks_stored?.toLocaleString()} קטעים</span>
                  <span>⏱️ {result.elapsed_seconds}s</span>
                </div>
              )}
            </div>
          )}

          {phase === 'error' && (
            <div className={styles.errorBox}>❌ {msg}</div>
          )}
        </div>

        <div className={styles.footer}>
          <button className={styles.btnGhost} onClick={onClose}>
            {phase === 'done' ? 'סגור' : 'ביטול'}
          </button>
          {phase === 'idle' && (
            <button className={styles.btnPrimary} onClick={handleStart}>
              ▶ התחל טעינה
            </button>
          )}
          {phase === 'error' && (
            <button className={styles.btnPrimary} onClick={reset}>
              נסה שוב
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
