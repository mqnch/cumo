import { useEffect, useState } from 'react'

function App() {
  return <CumoInput />
}

export default App

function useDebouncedValue(value, delayMs) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(t)
  }, [value, delayMs])

  return debounced
}

function parseMode(text) {
  const trimmed = text ?? ''
  if (trimmed.startsWith('/')) return 'command'
  return 'natural'
}

async function resolveBackendBaseUrl() {
  const maybePort = await window.electron?.getBackendPort?.()
  const port = typeof maybePort === 'number' ? maybePort : 5000
  return `http://127.0.0.1:${port}`
}

function CumoInput() {
  const [text, setText] = useState('')
  const [backendBaseUrl, setBackendBaseUrl] = useState(null)
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const mode = parseMode(text)
  const debouncedText = useDebouncedValue(text, 250)
  const showRawJson = import.meta.env.DEV

  useEffect(() => {
    let mounted = true
    resolveBackendBaseUrl()
      .then((url) => {
        if (mounted) setBackendBaseUrl(url)
      })
      .catch(() => {
        // Fallback: allow dev to run backend manually on 5000.
        if (mounted) setBackendBaseUrl('http://127.0.0.1:5000')
      })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (!window.electron?.resizeWindow) return

    const height = mode === 'natural' && (preview || error) ? 320 : 110
    window.electron.resizeWindow({ width: 700, height })
  }, [mode, preview, error])

  useEffect(() => {
    if (!backendBaseUrl) return

    const currentMode = parseMode(debouncedText)
    if (currentMode !== 'natural') {
      setPreview(null)
      setError(null)
      setIsLoading(false)
      return
    }

    const query = (debouncedText ?? '').trim()
    if (!query) {
      setPreview(null)
      setError(null)
      setIsLoading(false)
      return
    }

    const controller = new AbortController()
    setIsLoading(true)
    setError(null)

    fetch(`${backendBaseUrl}/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: query }),
      signal: controller.signal,
    })
      .then(async (res) => {
        const body = await res.json().catch(() => ({}))
        if (!res.ok) {
          throw new Error(body?.error || `Backend error (${res.status})`)
        }
        setPreview(body)
      })
      .catch((e) => {
        if (e?.name === 'AbortError') return
        setPreview(null)
        setError(String(e?.message || e))
      })
      .finally(() => {
        setIsLoading(false)
      })

    return () => controller.abort()
  }, [backendBaseUrl, debouncedText])

  return (
    <div className="h-full w-full p-2">
      <div className="h-full w-full rounded-2xl border border-white/10 bg-zinc-950 px-4 py-3 shadow-xl">
        <div className="flex items-center gap-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-white/60">
            {mode === 'command' ? 'Command' : 'Natural'}
          </div>
          <div className="text-xs text-white/40">{backendBaseUrl ? backendBaseUrl : 'backend…'}</div>
        </div>

        <div className="mt-2 flex items-baseline gap-2">
          <div className="select-none text-lg font-semibold text-white/40">{'>'}</div>
          <input
            autoFocus
            className="w-full bg-transparent text-lg text-white outline-none placeholder:text-white/30"
            placeholder="Type an event… (or start with / for commands)"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>

        {mode === 'command' ? (
          <div className="mt-2 text-sm text-white/50">Command mode coming next.</div>
        ) : (
          <div className="mt-2">
            {isLoading ? <div className="text-sm text-white/50">Parsing…</div> : null}

            {error ? (
              <div className="mt-2 rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-sm text-red-200">
                {error}
              </div>
            ) : null}

            {preview ? (
              showRawJson ? (
                <pre className="mt-2 max-h-44 overflow-auto rounded-lg border border-white/10 bg-zinc-900 p-2 text-xs text-white/80">
                  {JSON.stringify(preview, null, 2)}
                </pre>
              ) : (
                <div className="mt-2 rounded-lg border border-white/10 bg-zinc-900 p-2 text-sm text-white/80">
                  Parsed.
                </div>
              )
            ) : null}
          </div>
        )}
      </div>
    </div>
  )
}
