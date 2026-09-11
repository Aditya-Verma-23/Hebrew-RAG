import { useState, useEffect } from 'react'
import styles from './SettingsPanel.module.css'
import { validateSettings } from '../hooks/useRAG'

export default function SettingsPanel({ open, settings, onChange, onClose }) {
  const [local, setLocal] = useState(settings)
  const errors = validateSettings(local)

  useEffect(() => { setLocal(settings) }, [settings])

  const apply = () => {
    if (errors.length === 0) { onChange(local); onClose() }
  }

  const update = (key, val) => setLocal(prev => ({ ...prev, [key]: val }))

  if (!open) return null

  return (
    <>
      <div className={styles.backdrop} onClick={onClose} />
      <div className={styles.panel} role="dialog" aria-label="הגדרות">
        <div className={styles.header}>
          <h3 className={styles.title}>⚙️ הגדרות שאילתה</h3>
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        {errors.length > 0 && (
          <div className={styles.errors}>
            {errors.map((e, i) => <div key={i} className={styles.errItem}>⚠️ {e}</div>)}
          </div>
        )}

        <div className={styles.body}>
          {/* Top K */}
          <div className={styles.group}>
            <label className={styles.label}>
              מספר קטעים (Top K)
              <span className={styles.val}>{local.topK}</span>
            </label>
            <input
              type="range" min={1} max={10} value={local.topK}
              onChange={e => update('topK', Number(e.target.value))}
              className={styles.slider}
            />
            <div className={styles.sliderLabels}><span>1</span><span>10</span></div>
          </div>

          {/* Temperature */}
          <div className={styles.group}>
            <label className={styles.label}>
              טמפרטורה (יצירתיות)
              <span className={styles.val}>{local.temperature.toFixed(2)}</span>
            </label>
            <input
              type="range" min={0} max={100} value={Math.round(local.temperature * 100)}
              onChange={e => update('temperature', Number(e.target.value) / 100)}
              className={styles.slider}
            />
            <div className={styles.sliderLabels}><span>0.0 (מדויק)</span><span>1.0 (יצירתי)</span></div>
          </div>

          {/* N Candidates */}
          <div className={styles.group}>
            <label className={styles.label}>
              מועמדים לאחזור
              <span className={styles.val}>{local.nCandidates}</span>
            </label>
            <input
              type="range" min={5} max={50} step={5} value={local.nCandidates}
              onChange={e => update('nCandidates', Number(e.target.value))}
              className={styles.slider}
            />
          </div>

          {/* Toggles */}
          {[
            { key: 'useHybrid', label: 'חיפוש היברידי (BM25 + Semantic)', desc: 'ממזג חיפוש לקסיקלי וסמנטי' },
            { key: 'useReranker', label: 'שימוש ב-Reranker', desc: 'Cross-encoder לדיוק גבוה יותר' },
          ].map(({ key, label, desc }) => (
            <div key={key} className={styles.toggleRow}>
              <div>
                <div className={styles.toggleLabel}>{label}</div>
                <div className={styles.toggleDesc}>{desc}</div>
              </div>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={local[key]}
                  onChange={e => update(key, e.target.checked)}
                />
                <span className={styles.toggleSlider} />
              </label>
            </div>
          ))}
        </div>

        <div className={styles.footer}>
          <button className={styles.btnGhost} onClick={onClose}>ביטול</button>
          <button
            className={styles.btnPrimary}
            onClick={apply}
            disabled={errors.length > 0}
          >
            החל הגדרות
          </button>
        </div>
      </div>
    </>
  )
}
