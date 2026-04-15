import { useState, useRef, useEffect } from 'react'

export default function App() {
  const [command, setCommand] = useState('')
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const handleCommand = async () => {
    if (!command.trim()) return
    const currentCmd = command
    setCommand('')
    setLoading(true)
    setLogs((prev) => [...prev, `🟢 You: ${currentCmd}`, '[Thinking...]'])

    try {
      const res = await fetch('http://127.0.0.1:8000', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: currentCmd })
      })

      const data = await res.json()
      
      let newLog = `📋 Plan:\n`
      if (data.steps && data.steps.length > 0) {
        data.steps.forEach((s: any, i: number) => {
           newLog += `  ${i + 1}. ${s.action} → ${JSON.stringify(s.params)}\n`
        })
        newLog += `\n✅ ${data.message}`
      } else {
        newLog = `❌ No steps returned.`
      }

      setLogs((prev) => [...prev.filter(l => l !== '[Thinking...]'), newLog])
    } catch (err) {
      setLogs((prev) => [...prev.filter(l => l !== '[Thinking...]'), `❌ Error connecting to Brain (server.py)`])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100vh', 
      backgroundColor: '#1E1E1E', color: '#FFF', fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
      borderRadius: '8px', overflow: 'hidden', border: '1px solid #333'
    }}>
      {/* Draggable Title Bar */}
      <div style={{
        height: '30px', WebkitAppRegion: 'drag' as any, backgroundColor: '#252526', 
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 'bold'
      }}>
        Regis Assistant
      </div>

      {/* Chat Logs */}
      <div style={{
        flex: 1, padding: '15px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px'
      }}>
        <div style={{color: '#888', fontSize: '12px', textAlign: 'center'}}>Ask me to open an app, search something, or type text.</div>
        {logs.map((log, i) => (
          <div key={i} style={{
            backgroundColor: log.startsWith('🟢') ? '#264F78' : '#2D2D30',
            padding: '10px', borderRadius: '6px', whiteSpace: 'pre-wrap', fontSize: '13px'
          }}>
            {log}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input Box */}
      <div style={{ padding: '15px', backgroundColor: '#252526', display: 'flex', gap: '10px' }}>
        <input 
          autoFocus
          disabled={loading}
          type="text" 
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCommand()}
          placeholder="Ask me to do something..."
          style={{
            flex: 1, padding: '8px 12px', borderRadius: '6px', border: '1px solid #444', 
            backgroundColor: '#3C3C3C', color: '#FFF', outline: 'none'
          }}
        />
        <button 
          disabled={loading}
          onClick={handleCommand}
          style={{
            padding: '8px 15px', borderRadius: '6px', border: 'none', 
            backgroundColor: '#0E639C', color: '#FFF', cursor: 'pointer', fontWeight: 'bold'
          }}
        >
          Run
        </button>
      </div>
    </div>
  )
}
