import { useState, useRef, useEffect, useCallback } from 'react'
import './assets/app.css'
import regisImg from './assets/regis.png'

interface Message {
  id: number
  role: 'user' | 'ai' | 'system'
  text: string
  steps?: { action: string; params?: Record<string, unknown> }[]
  loading?: boolean
}

const BACKEND = 'http://127.0.0.1:8000'
let msgId = 0
const nextId = () => ++msgId

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const [voiceLevel, setVoiceLevel] = useState(0)
  const [connected, setConnected] = useState<boolean | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const animFrame = useRef<number | null>(null)

  // ── health ping ──────────────────────────────────────────────────────────
  const pingServer = useCallback(async () => {
    try {
      const r = await fetch(`${BACKEND}/health`, { signal: AbortSignal.timeout(2000) })
      setConnected(r.ok)
      
      // If we are not currently doing something, sync history in case a hotword triggered a command
      if (r.ok && !busy && !listening) {
        const hRes = await fetch(`${BACKEND}/history`)
        const hData = await hRes.json()
        if (hData.history && Array.isArray(hData.history)) {
          // Only update if the history length changed to avoid unnecessary re-renders
          if (hData.history.length * 2 !== messages.length) {
             const loadedMessages: Message[] = []
             hData.history.forEach((entry: any) => {
               loadedMessages.push({ id: nextId(), role: 'user', text: entry.command })
               const reply = entry.reply || `Done — executed ${entry.steps?.length ?? 0} steps.`
               loadedMessages.push({ id: nextId(), role: 'ai', text: reply, steps: entry.steps })
             })
             setMessages(loadedMessages)
          }
        }
      }
    } catch {
      setConnected(false)
    }
  }, [busy, listening, messages.length])

  useEffect(() => {
    const init = async () => {
      await pingServer()
      try {
        const res = await fetch(`${BACKEND}/history`)
        const data = await res.json()
        if (data.history && Array.isArray(data.history)) {
          const loadedMessages: Message[] = []
          data.history.forEach((entry: any) => {
            loadedMessages.push({ id: nextId(), role: 'user', text: entry.command })
            const reply = entry.reply || `Done — executed ${entry.steps?.length ?? 0} steps.`
            loadedMessages.push({ id: nextId(), role: 'ai', text: reply, steps: entry.steps })
          })
          setMessages(loadedMessages)
        }
      } catch (err) {
        console.error('Failed to load history:', err)
      }
    }
    init()
    pingTimer.current = setInterval(pingServer, 5000)
    return () => { if (pingTimer.current) clearInterval(pingTimer.current) }
  }, [pingServer])

  // ── scroll to bottom ─────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── helpers ───────────────────────────────────────────────────────────────
  const pushMsg = (msg: Omit<Message, 'id'>) =>
    setMessages(prev => [...prev, { ...msg, id: nextId() }])

  const patchLast = (patch: Partial<Message>) =>
    setMessages(prev => {
      const clone = [...prev]
      clone[clone.length - 1] = { ...clone[clone.length - 1], ...patch }
      return clone
    })

  // ── send command ──────────────────────────────────────────────────────────
  const sendCommand = useCallback(async (cmd: string) => {
    const trimmed = cmd.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setInput('')
    pushMsg({ role: 'user', text: trimmed })
    pushMsg({ role: 'ai', text: '', loading: true })

    try {
      const res = await fetch(`${BACKEND}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: trimmed }),
        signal: AbortSignal.timeout(30_000),
      })
      const data = await res.json()
      const reply = data.reply || data.message || `Done — ${data.steps?.length ?? 0} steps.`
      patchLast({ text: reply, steps: data.steps, loading: false })
    } catch (err: unknown) {
      const msg = err instanceof Error && err.name === 'TimeoutError'
        ? '⏱️ Request timed out. Is the server running?'
        : '❌ Could not reach Regis server. Start server.py first.'
      patchLast({ text: msg, loading: false })
    } finally {
      setBusy(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [busy])

  // ── voice capture ─────────────────────────────────────────────────────────
  const handleVoice = useCallback(async () => {
    if (busy || listening) return
    setListening(true)
    setBusy(true)

    // Animate the voice bar while waiting
    let phase = 0
    const animate = () => {
      phase += 0.15
      setVoiceLevel(0.4 + 0.6 * Math.abs(Math.sin(phase)))
      animFrame.current = requestAnimationFrame(animate)
    }
    animFrame.current = requestAnimationFrame(animate)

    try {
      const res = await fetch(`${BACKEND}/voice`, {
        method: 'POST',
        signal: AbortSignal.timeout(15_000),
      })
      const data = await res.json()

      if (data.success && data.text) {
        setInput(data.text)
        // Auto-send the transcribed command
        await sendCommand(data.text)
      } else {
        pushMsg({ role: 'system', text: '🔇 No speech detected. Try speaking louder.' })
      }
    } catch {
      pushMsg({ role: 'system', text: '❌ Voice capture failed. Check microphone permissions.' })
    } finally {
      if (animFrame.current) cancelAnimationFrame(animFrame.current)
      setVoiceLevel(0)
      setListening(false)
      setBusy(false)
    }
  }, [busy, listening, sendCommand])

  const bars = 16

  return (
    <div className="app">
      {/* ── Drag region / title bar ── */}
      <div className="titlebar">
        <div className="titlebar-dot red" />
        <div className="titlebar-dot yellow" />
        <div className="titlebar-dot green" />
        <span className="titlebar-label">Regis</span>
        <div className={`status-pill ${connected === null ? 'idle' : connected ? 'on' : 'off'}`}>
          {connected === null ? 'Connecting…' : connected ? 'Online' : 'Offline'}
        </div>
      </div>

      {/* ── Regis avatar ── */}
      <div className="avatar-section">
        <div className={`avatar-ring ${busy ? 'pulsing' : ''}`}>
          <img src={regisImg} alt="Regis" className="avatar-img" draggable={false} />
        </div>
        {messages.length === 0 && (
          <p className="greeting">Hi, I'm <strong>Regis</strong>. How can I help?</p>
        )}
      </div>

      {/* ── Chat log ── */}
      {messages.length > 0 && (
        <div className="chat">
          {messages.map(m => (
            <div key={m.id} className={`bubble ${m.role} ${m.loading ? 'loading' : ''}`}>
              {m.loading ? (
                <span className="dot-wave"><span /><span /><span /></span>
              ) : (
                <>
                  <p className="bubble-text">{m.text}</p>
                  {m.steps && m.steps.length > 0 && (
                    <div className="steps">
                      <div className="steps-label">PLAN ({m.steps.length} steps)</div>
                      {m.steps.map((s, i) => (
                        <div key={i} className="step-row">
                          <span className="step-num">{i + 1}</span>
                          <span className="step-action">{s.action}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {/* ── Voice visualiser bar ── */}
      <div className={`voice-bar ${listening ? 'active' : ''}`}>
        <div className="voice-bars">
          {Array.from({ length: bars }).map((_, i) => {
            const seed = Math.sin(i * 1.3) * 0.5 + 0.5
            const height = listening
              ? 6 + (voiceLevel * 28 * seed)
              : 4
            return (
              <div
                key={i}
                className="voice-bar-line"
                style={{ height: `${height}px` }}
              />
            )
          })}
        </div>
        <span className="voice-status">
          {listening ? 'Listening…' : busy ? 'Processing…' : 'Tap 🎙️ to speak'}
        </span>
      </div>

      {/* ── Input row ── */}
      <div className="input-row">
        <button
          id="voice-btn"
          className={`icon-btn mic ${listening ? 'recording' : ''}`}
          disabled={busy && !listening}
          onClick={handleVoice}
          title="Voice input"
          aria-label="Voice input"
        >
          🎙️
        </button>
        <input
          id="command-input"
          ref={inputRef}
          className="cmd-input"
          type="text"
          placeholder="Ask Regis anything…"
          value={input}
          disabled={busy}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendCommand(input)}
          autoFocus
        />
        <button
          id="send-btn"
          className="icon-btn send"
          disabled={busy || !input.trim()}
          onClick={() => sendCommand(input)}
          title="Send"
          aria-label="Send command"
        >
          ↑
        </button>
      </div>
    </div>
  )
}
