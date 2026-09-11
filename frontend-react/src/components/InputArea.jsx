import { useState } from 'react'
import styles from './InputArea.module.css'
import { validateQuery } from '../hooks/useRAG'

const SUGGESTIONS = [
  { icon: '👤', text: 'מי הדמויות הראשיות בסיפור?' },
  { icon: '📖', text: 'על מה מדבר הספר?' },
  { icon: '🌅', text: 'מה קורה בתחילת הספר?' },
  { icon: '⭐', text: 'תאר את הסצנה החשובה ביותר' },
  { icon: '💡', text: 'מה הנושא המרכזי של הסיפור?' },
  { icon: '🏁', text: 'כיצד מסתיים הספר?' },
]

export default function InputArea({ onSend, onCancel, isQuerying, validationErrors, onClearErrors, isEmpty }) {
  const [query, setQuery] = useState('')
  const [touched, setTouched] = useState(false)

  // Live client validation
  const liveErrors = touched ? validateQuery(query) : []
  const allErrors = validationErrors.length > 0 ? validationErrors : liveErrors
  const hasError = allErrors.length > 0

  const handleSend = () => {
    setTouched(true)
    const errs = validateQuery(query)
    if (errs.length > 0) return
    onSend(query)
    setQuery('')
    setTouched(false)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isQuerying) handleSend()
    }
  }

  const handleChange = (e) => {
    setQuery(e.target.value)
    if (validationErrors.length > 0) onClearErrors()
    // Auto-resize
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`
  }

  const handleSuggestion = (text) => {
    setQuery(text)
    setTouched(false)
    onClearErrors()
  }

  return (
    <div className={styles.wrapper}>
      {/* Welcome + suggestions when chat is empty */}
      {isEmpty && (
        <div className={styles.welcome}>
          <div className={styles.heroIcon}>
            <span className={styles.heroChar}>א</span>
            <div className={styles.ring} style={{ '--d': '0s' }} />
            <div className={styles.ring} style={{ '--d': '.8s', '--scale': '1.15' }} />
            <div className={styles.ring} style={{ '--d': '1.6s', '--scale': '1.3' }} />
          </div>
          <h1 className={styles.heroTitle}>ברוכים הבאים למערכת RAG העברית</h1>
          <p className={styles.heroSub}>חיפוש חכם בספרים עבריים באמצעות AI מתקדם עם חיבור WebSocket דו-כיווני</p>

          <div className={styles.suggestions}>
            <p className={styles.sugLabel}>שאלות מוצעות</p>
            <div className={styles.sugGrid}>
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className={styles.sugChip} onClick={() => handleSuggestion(s.text)}>
                  <span className={styles.sugIcon}>{s.icon}</span>
                  {s.text}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input box */}
      <div className={styles.inputArea}>
        {/* Validation errors */}
        {hasError && (
          <div className={styles.errorBanner} role="alert">
            {allErrors.map((e, i) => (
              <div key={i} className={styles.errorItem}>⚠️ {e}</div>
            ))}
          </div>
        )}

        <div className={`${styles.inputBox} ${hasError ? styles.inputError : ''}`}>
          <textarea
            value={query}
            onChange={handleChange}
            onKeyDown={handleKey}
            onBlur={() => setTouched(true)}
            placeholder="שאל שאלה על הספר בעברית..."
            rows={1}
            dir="rtl"
            aria-label="שאל שאלה"
            aria-invalid={hasError}
            maxLength={2000}
            disabled={isQuerying}
            className={styles.textarea}
          />

          <div className={styles.btnGroup}>
            {isQuerying ? (
              <button className={styles.cancelBtn} onClick={onCancel} title="ביטול">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <rect x="3" y="3" width="18" height="18" rx="2"/>
                </svg>
              </button>
            ) : (
              <button
                className={styles.sendBtn}
                onClick={handleSend}
                disabled={!query.trim()}
                title="שלח שאלה"
                aria-label="שלח"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </button>
            )}
          </div>
        </div>

        <div className={styles.footer}>
          <span className={`${styles.charCount} ${query.length > 1800 ? styles.charWarn : ''}`}>
            {query.length} / 2000
          </span>
          <span className={styles.hint}>Enter לשליחה · Shift+Enter לשורה חדשה</span>
        </div>
      </div>
    </div>
  )
}
