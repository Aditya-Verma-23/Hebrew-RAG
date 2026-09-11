import styles from './Header.module.css'

export default function Header({ serverStatus, onIngest, onSettings, onClear, books = [], chatBook, onChatBookChange }) {
  const indexed = serverStatus?.docsCount > 0

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        {/* Logo */}
        <div className={styles.logo}>
          <div className={styles.logoIcon}>א</div>
          <div className={styles.logoText}>
            <span className={styles.logoTitle}>עברית RAG</span>
            <span className={styles.logoSub}>מערכת חיפוש חכמה</span>
          </div>
        </div>

        {/* Actions */}
        <div className={styles.actions}>

          {/* Chat Context Dropdown */}
          <select 
            className={styles.bookSelect}
            value={chatBook || ''}
            onChange={e => onChatBookChange(e.target.value || null)}
            title="בחר ספר לחיפוש"
          >
            <option value="">כל הספרים</option>
            {books.filter(b => b.status === 'Ready').map(b => (
              <option key={b.filename} value={b.filename} title={b.filename}>
                {b.filename}
              </option>
            ))}
          </select>

          {/* Index Status */}
          {indexed && (
            <div className={`${styles.badge} ${styles.ok}`} title="מסמכים מאונדקסים">
              <span className={`${styles.dot} ${styles.ok}`} />
              <span className={styles.badgeText}>{serverStatus.docsCount.toLocaleString()} קטעים</span>
            </div>
          )}

          {/* Clear chat */}
          <button className={styles.iconBtn} onClick={onClear} title="נקה שיחה">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>
              <path d="M9 6V4h6v2"/>
            </svg>
          </button>

          {/* Settings */}
          <button className={styles.iconBtn} onClick={onSettings} title="הגדרות">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>

          {/* Ingest */}
          <button className={styles.btnPrimary} onClick={onIngest}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            טעינת ספר
          </button>
        </div>
      </div>
    </header>
  )
}
