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

async function readResponse(res) {
  const contentType = res.headers.get('content-type') || ''
  const text = await res.text()
  if (contentType.includes('application/json')) {
    try {
      return { data: JSON.parse(text), text }
    } catch {
      return { data: null, text }
    }
  }
  return { data: null, text }
}

function CumoInput() {
  const [text, setText] = useState('')
  const [backendBaseUrl, setBackendBaseUrl] = useState(null)
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [calendarOptions, setCalendarOptions] = useState([])
  const [selectedCalendarId, setSelectedCalendarId] = useState(null)
  const [calendarLoading, setCalendarLoading] = useState(false)
  const [calendarError, setCalendarError] = useState(null)
  const [calendarRetries, setCalendarRetries] = useState(0)
  const [submitError, setSubmitError] = useState(null)
  const [submitLoading, setSubmitLoading] = useState(false)

  const mode = parseMode(text)
  const debouncedText = useDebouncedValue(text, 250)
  const showRawJson = import.meta.env.DEV
  const needsCalendar =
    mode === 'natural' &&
    !selectedCalendarId &&
    !calendarLoading &&
    calendarOptions.length > 0

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

    const needsExtraSpace =
      mode === 'natural' && (preview || error || needsCalendar || submitError || submitLoading)
    const height = needsExtraSpace ? 380 : 130
    window.electron.resizeWindow({ width: 700, height })
  }, [mode, preview, error, needsCalendar, submitError, submitLoading])

  useEffect(() => {
    if (!backendBaseUrl) return

    let active = true
    let retryTimer = null

    const attemptLoad = (attempt) => {
      if (!active) return
      setCalendarLoading(true)
      setCalendarError(null)
      setCalendarRetries(attempt)

      fetch(`${backendBaseUrl}/settings`)
        .then(async (res) => {
          const { data, text } = await readResponse(res)
          if (!res.ok) {
            throw new Error(data?.error || text || `Settings error (${res.status})`)
          }
          return data
        })
        .then((settings) => {
          if (!active) return
          const stored = settings?.selectedCalendarId
          if (stored) {
            setSelectedCalendarId(stored)
          }
        })
        .catch((err) => {
          if (!active) return
          setCalendarError(String(err?.message || err))
        })
        .finally(() => {
          if (!active) return
          fetch(`${backendBaseUrl}/calendars`)
            .then(async (res) => {
              const { data, text } = await readResponse(res)
              if (!res.ok) {
                throw new Error(data?.error || text || `Calendars error (${res.status})`)
              }
              return data
            })
            .then((data) => {
              if (!active) return
              const calendars = Array.isArray(data?.calendars) ? data.calendars : []
              setCalendarOptions(calendars)
              const primary = calendars.find((item) => item?.primary)
              if (primary?.id) {
                setSelectedCalendarId((current) => current ?? primary.id)
              }
            })
            .catch((err) => {
              if (!active) return
              const message = String(err?.message || err)
              setCalendarError(message)
              if (attempt < 3) {
                retryTimer = setTimeout(() => attemptLoad(attempt + 1), 1000 * (attempt + 1))
              }
            })
            .finally(() => {
              if (active) setCalendarLoading(false)
            })
        })
    }

    attemptLoad(0)

    return () => {
      active = false
      if (retryTimer) clearTimeout(retryTimer)
    }
  }, [backendBaseUrl])

  const handleCalendarChange = (event) => {
    const calendarId = event.target.value
    if (!calendarId) return
    setSelectedCalendarId(calendarId)
    setCalendarError(null)

    fetch(`${backendBaseUrl}/settings/calendar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ calendarId }),
    })
      .then(async (res) => {
        const { data, text } = await readResponse(res)
        if (!res.ok) {
          throw new Error(data?.error || text || `Calendar update failed (${res.status})`)
        }
      })
      .catch((err) => {
        setCalendarError(String(err?.message || err))
      })
  }

  const handleSubmit = async () => {
    if (!backendBaseUrl) return
    if (mode !== 'natural') return
    if (!selectedCalendarId) {
      setSubmitError('Select a calendar before scheduling.')
      return
    }

    const payload = preview ? { event: preview } : { text }
    setSubmitLoading(true)
    setSubmitError(null)

    try {
      const res = await fetch(`${backendBaseUrl}/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const { data, text } = await readResponse(res)
      if (!res.ok) {
        throw new Error(data?.error || text || `Schedule failed (${res.status})`)
      }
      setText('')
      setPreview(null)
      setError(null)
      window.electron?.hideWindow?.()
    } catch (err) {
      setSubmitError(String(err?.message || err))
    } finally {
      setSubmitLoading(false)
    }
  }

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
        const { data, text } = await readResponse(res)
        if (!res.ok) {
          throw new Error(data?.error || text || `Backend error (${res.status})`)
        }
        if (!data) {
          throw new Error('Backend returned non-JSON response')
        }
        setPreview(data)
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
    <div className="h-full w-full overflow-hidden p-1.5">
      <div className="h-full w-full overflow-hidden rounded-xl border border-white/10 bg-gradient-to-b from-zinc-950 via-zinc-950 to-zinc-900/70 px-3 pt-2 pb-3 shadow-[0_16px_48px_rgba(0,0,0,0.5)]">
        <div className="flex items-center justify-between gap-2">
          <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[10px] uppercase tracking-[0.18em] text-white/60">
            {mode === 'command' ? 'Command' : 'Natural'}
          </div>
          {mode === 'natural' && calendarOptions.length > 0 ? (
            <select
              className="w-auto max-w-[400px] rounded border border-white/10 bg-zinc-900/70 px-1 py-0 text-[14px] leading-none text-white/80 outline-none transition focus:border-white/30 focus:ring-1 focus:ring-white/20"
              value={selectedCalendarId ?? ''}
              onChange={handleCalendarChange}
            >
              <option value="" disabled>
                Select a calendar…
              </option>
              {calendarOptions.map((cal) => (
                <option key={cal.id} value={cal.id}>
                  {cal.summary}
                  {cal.primary ? ' (Primary)' : ''}
                </option>
              ))}
            </select>
          ) : null}
        </div>

        {mode === 'command' ? (
          <div className="mt-2 text-[12px] text-white/50">Command mode coming next.</div>
        ) : (
          <div className="mt-3 space-y-2">
            {calendarLoading ? (
              <div className="text-[12px] text-white/50">
                Loading calendars…
                {calendarRetries > 0 ? ` (retry ${calendarRetries})` : ''}
              </div>
            ) : null}

            {calendarError ? (
              <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-2.5 py-1.5 text-[12px] text-amber-100">
                {calendarError}
              </div>
            ) : null}

            <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-white/90 shadow-inner transition focus-within:border-white/30 focus-within:bg-white/10">
              <div className="select-none text-xs font-semibold text-white/40">{'>'}</div>
              <input
                autoFocus
                className="w-full bg-transparent text-sm text-white outline-none placeholder:text-white/40"
                placeholder="Type an event… (or start with / for commands)"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleSubmit()
                  }
                }}
              />
            </div>

            {isLoading ? <div className="text-[12px] text-white/50">Parsing…</div> : null}

            {error ? (
              <div className="rounded-md border border-red-500/30 bg-red-500/10 px-2.5 py-1.5 text-[12px] text-red-200">
                {error}
              </div>
            ) : null}

            {submitLoading ? <div className="text-[12px] text-white/50">Scheduling…</div> : null}

            {submitError ? (
              <div className="rounded-md border border-red-500/30 bg-red-500/10 px-2.5 py-1.5 text-[12px] text-red-200">
                {submitError}
              </div>
            ) : null}

            {preview ? (
              showRawJson ? (
                <pre className="max-h-32 overflow-hidden rounded-md border border-white/10 bg-zinc-900/80 px-2.5 py-2 text-[12px] text-white/80">
                  {JSON.stringify(preview, null, 2)}
                </pre>
              ) : (
                <div className="rounded-md border border-white/10 bg-zinc-900/80 px-2.5 py-2 text-[12px] text-white/70">
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
