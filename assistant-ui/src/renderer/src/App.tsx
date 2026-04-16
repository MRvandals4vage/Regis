import { useState, useRef, useEffect } from 'react'
import './assets/assistant.css'

interface LogEntry {
  type: 'user' | 'ai' | 'loading'
  content: string
  steps?: any[]
  statusMessage?: string
}

export default function App() {
  const [command, setCommand] = useState('')
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const handleCommand = async () => {
    if (!command.trim() || loading) return
    
    const currentCmd = command
    setCommand('')
    setLoading(true)
    
    setLogs((prev) => [
      ...prev, 
      { type: 'user', content: currentCmd },
      { type: 'loading', content: 'Thinking...' }
    ])

    try {
      const res = await fetch('http://127.0.0.1:8000', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: currentCmd })
      })

      const data = await res.json()
      
      setLogs((prev) => {
        const withoutLoading = prev.filter(l => l.type !== 'loading')
        return [
          ...withoutLoading,
          { 
            type: 'ai', 
            content: data.message, 
            steps: data.steps,
            statusMessage: data.message 
          }
        ]
      })
    } catch (err) {
      setLogs((prev) => {
        const withoutLoading = prev.filter(l => l.type !== 'loading')
        return [
          ...withoutLoading,
          { type: 'ai', content: '❌ Error connecting to Brain. Is server.py running?' }
        ]
      })
    } finally {
      setLoading(false)
    }
  }

  const handleVoice = async () => {
    if (loading) return
    setLoading(true)
    setLogs((prev) => [...prev, { type: 'loading', content: '🎙️ Listening...' }])

    try {
      const res = await fetch('http://127.0.0.1:8000/voice', { method: 'POST' })
      const data = await res.json()
      
      setLogs((prev) => prev.filter(l => l.type !== 'loading'))
      
      if (data.success && data.text) {
        setCommand(data.text)
        // Optionally auto-run the command
        // setTimeout(() => handleCommand(), 100);
      } else {
        setLogs((prev) => [...prev, { type: 'ai', content: '🔇 No voice detected or recording failed.' }])
      }
    } catch (err) {
      setLogs((prev) => {
        const withoutLoading = prev.filter(l => l.type !== 'loading')
        return [
          ...withoutLoading,
          { type: 'ai', content: '❌ Error connecting to microphone service.' }
        ]
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="assistant-container">
      {/* Draggable Title Bar */}
      <div className="title-bar">
        Regis Assistant
      </div>

      {/* Chat Logs */}
      <div className="chat-logs">
        {logs.length === 0 && (
          <div style={{color: 'rgba(255,255,255,0.3)', fontSize: '12px', textAlign: 'center', marginTop: '50px'}}>
            How can I help you today?
          </div>
        )}
        
        {logs.map((log, i) => (
          <div key={i} className={`message ${log.type}`}>
            {log.content}
            {log.steps && log.steps.length > 0 && (
              <div style={{ marginTop: '10px' }}>
                <div style={{ fontSize: '11px', fontWeight: 'bold', marginBottom: '5px', opacity: 0.8 }}>
                  PLAN ({log.steps.length} STEPS):
                </div>
                {log.steps.map((s: any, j: number) => (
                  <div key={j} className="plan-step">
                    {s.action} → {JSON.stringify(s.params)}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input Area */}
      <div className="input-area">
        <button 
          disabled={loading}
          onClick={handleVoice}
          className="voice-btn"
          title="Voice Command"
        >
          🎙️
        </button>
        <input 
          autoFocus
          disabled={loading}
          className="input-box"
          type="text" 
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCommand()}
          placeholder="Type a command..."
        />
        <button 
          disabled={loading || !command.trim()}
          onClick={handleCommand}
          className="run-btn"
        >
          Run
        </button>
      </div>
    </div>
  )
}

