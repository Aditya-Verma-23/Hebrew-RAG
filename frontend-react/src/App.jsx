import { useState, useCallback, useEffect } from 'react'
import { useRAG } from './hooks/useRAG'
import Header from './components/Header'
import ChatMessages from './components/ChatMessages'
import InputArea from './components/InputArea'
import SourcesPanel from './components/SourcesPanel'
import SettingsPanel from './components/SettingsPanel'
import IngestModal from './components/IngestModal'
import { fetchBooks } from './utils/api'
import styles from './App.module.css'

export default function App() {
  const [showSettings, setShowSettings] = useState(false)
  const [showIngest, setShowIngest]     = useState(false)
  const [books, setBooks] = useState([])

  const {
    messages, sources, settings, setSettings,
    serverStatus, isQuerying, statusMsg,
    validationErrors, setValidationErrors,
    sendQuery, cancelQuery, clearChat, refreshStatus,
    chatBook, setChatBook,
  } = useRAG()

  // Fetch books globally for the header dropdown
  const loadBooks = useCallback(async () => {
    try {
      const data = await fetchBooks()
      setBooks(data.books || [])
    } catch (err) {
      console.error('Failed to fetch books', err)
    }
  }, [])

  useEffect(() => {
    loadBooks()
  }, [loadBooks])

  const handleSend = (query) => sendQuery(query)
  const handleCancel = () => cancelQuery()

  const handleIngestComplete = () => {
    refreshStatus()
    loadBooks() // Refresh book list after ingestion
  }

  return (
    <div className={styles.app}>
      {/* Animated background */}
      <div className={styles.orbs} aria-hidden>
        <div className={`${styles.orb} ${styles.orb1}`} />
        <div className={`${styles.orb} ${styles.orb2}`} />
        <div className={`${styles.orb} ${styles.orb3}`} />
      </div>

      {/* Header */}
      <Header
        serverStatus={serverStatus}
        onIngest={() => setShowIngest(true)}
        onSettings={() => setShowSettings(s => !s)}
        onClear={clearChat}
        books={books}
        chatBook={chatBook}
        onChatBookChange={setChatBook}
      />

      {/* Settings */}
      <SettingsPanel
        open={showSettings}
        settings={settings}
        onChange={setSettings}
        onClose={() => setShowSettings(false)}
      />

      {/* Ingest Modal */}
      <IngestModal
        open={showIngest}
        onClose={() => setShowIngest(false)}
        onComplete={handleIngestComplete}
      />

      {/* Main layout */}
      <main className={styles.main}>
        {/* Chat */}
        <div className={styles.chatCol}>
          <ChatMessages messages={messages} statusMsg={statusMsg} />

          <InputArea
            onSend={handleSend}
            onCancel={handleCancel}
            isQuerying={isQuerying}
            validationErrors={validationErrors}
            onClearErrors={() => setValidationErrors([])}
            isEmpty={messages.length === 0}
          />
        </div>

        {/* Sources */}
        <SourcesPanel sources={sources} />
      </main>
    </div>
  )
}
