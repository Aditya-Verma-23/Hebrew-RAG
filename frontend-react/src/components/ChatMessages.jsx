import { useEffect, useRef } from 'react'
import styles from './ChatMessages.module.css'

function TypingDots() {
  return (
    <div className={styles.typing}>
      <span className={styles.dot} />
      <span className={styles.dot} />
      <span className={styles.dot} />
    </div>
  )
}

function StatusLine({ msg }) {
  if (!msg) return null
  return <div className={styles.statusLine}>⏳ {msg}</div>
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const isError = msg.error
  const isEmpty = !msg.content && msg.streaming

  const formattedContent = msg.content
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')

  return (
    <div className={`${styles.message} ${isUser ? styles.user : styles.assistant}`}>
      <div className={styles.avatar}>
        {isUser ? 'א' : '🤖'}
      </div>
      <div className={styles.bubbleWrap}>
        <div className={`${styles.bubble} ${isError ? styles.bubbleError : ''}`}>
          {isEmpty ? (
            <TypingDots />
          ) : (
            <span
              className={msg.streaming ? styles.streaming : ''}
              dangerouslySetInnerHTML={{ __html: formattedContent }}
            />
          )}
        </div>
        <div className={styles.meta}>
          {msg.time?.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })}
          {msg.cancelled && ' · בוטל'}
          {msg.error && ' · שגיאה'}
        </div>
      </div>
    </div>
  )
}

export default function ChatMessages({ messages, statusMsg }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, statusMsg])

  if (messages.length === 0) return null

  return (
    <div className={styles.container}>
      <div className={styles.inner}>
        {messages.map(msg => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        {statusMsg && <StatusLine msg={statusMsg} />}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
