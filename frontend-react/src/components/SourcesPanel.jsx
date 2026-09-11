import { useState } from 'react'
import styles from './SourcesPanel.module.css'

function SourceModal({ source, onClose }) {
  return (
    <div className={styles.modalOverlay} onClick={onClose} role="dialog" aria-modal>
      <div className={styles.modalBox} onClick={e => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <span className={styles.modalTitle}>📄 {source.chapter_title || '—'}</span>
          <button className={styles.closeBtn} onClick={onClose} aria-label="סגור">✕</button>
        </div>
        <div className={styles.modalBody} dir="rtl">{source.text}</div>
        <div className={styles.modalFooter}>
          <span className={styles.tag}>{source.search_type}</span>
          <span className={styles.tag}>ציון: {source.rerank_score?.toFixed(3) ?? '—'}</span>
          <span className={styles.tag}>קטע {(source.chunk_index || 0) + 1}</span>
        </div>
      </div>
    </div>
  )
}

export default function SourcesPanel({ sources }) {
  const [selected, setSelected] = useState(null)

  return (
    <aside className={styles.panel} aria-label="מקורות">
      <div className={styles.header}>
        <h2 className={styles.title}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          מקורות
        </h2>
        <span className={styles.count}>{sources.length}</span>
      </div>

      <div className={styles.list}>
        {sources.length === 0 ? (
          <div className={styles.empty}>שאל שאלה לצפייה במקורות</div>
        ) : (
          sources.map((src, i) => (
            <div
              key={src.id || i}
              className={styles.card}
              onClick={() => setSelected(src)}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && setSelected(src)}
              title="לחץ לצפייה בטקסט מלא"
            >
              <div className={styles.cardHeader}>
                <span className={styles.cardTitle}>{src.chapter_title || '—'}</span>
                <span className={styles.rank}>#{i + 1}</span>
              </div>
              <p className={styles.preview} dir="rtl">{src.text_preview}</p>
              <div className={styles.tags}>
                <span className={`${styles.tag} ${styles[src.search_type]}`}>{src.search_type}</span>
                {src.rerank_score != null && (
                  <span className={styles.tag}>{src.rerank_score.toFixed(3)}</span>
                )}
                <span className={styles.tag}>קטע {(src.chunk_index || 0) + 1}</span>
              </div>
            </div>
          ))
        )}
      </div>

      {selected && <SourceModal source={selected} onClose={() => setSelected(null)} />}
    </aside>
  )
}
