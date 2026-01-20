import { spawn, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'
import net from 'node:net'
import path from 'node:path'

let backendProcess: ChildProcess | null = null
let backendPort: number | null = null

function resolvePythonExecutable(backendDir: string) {
  const envPython = process.env.CUMO_PYTHON
  if (envPython) {
    return envPython
  }

  const venvPath =
    process.platform === 'win32'
      ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
      : path.join(backendDir, 'venv', 'bin', 'python')

  if (fs.existsSync(venvPath)) {
    return venvPath
  }

  return process.platform === 'win32' ? 'python' : 'python3'
}

function isPortFree(port: number) {
  return new Promise<boolean>((resolve) => {
    const server = net.createServer()
    server.unref()

    server.once('error', (err: NodeJS.ErrnoException) => {
      if (err.code === 'EADDRINUSE') {
        resolve(false)
      } else {
        // If we can't confidently determine, assume "not free" to avoid failing to spawn.
        resolve(false)
      }
    })

    server.listen(port, '127.0.0.1', () => {
      server.close(() => resolve(true))
    })
  })
}

async function resolveBackendPort() {
  const raw = process.env.CUMO_BACKEND_PORT
  if (raw) {
    const parsed = Number.parseInt(raw, 10)
    return Number.isFinite(parsed) ? parsed : 5000
  }

  for (const candidate of [5001, 5000, 5002, 5050]) {
    // eslint-disable-next-line no-await-in-loop
    const free = await isPortFree(candidate)
    if (free) return candidate
  }

  // Last resort: use 5001 and let Flask error if something truly odd is happening.
  return 5001
}

function buildBackendEnv(port: number) {
  return {
    ...process.env,
    CUMO_BACKEND_PORT: String(port),
  }
}

export function getBackendPort() {
  return backendPort
}

export async function startBackend() {
  if (backendProcess) {
    return backendProcess
  }

  const backendDir = path.join(process.cwd(), 'backend')
  if (!fs.existsSync(backendDir)) {
    console.warn('[backend] Missing backend directory, skipping Python spawn.')
    return null
  }

  const python = resolvePythonExecutable(backendDir)
  const port = await resolveBackendPort()
  backendPort = port

  const child = spawn(python, ['-u', 'app.py'], {
    cwd: backendDir,
    env: buildBackendEnv(port),
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  child.stdout?.on('data', (chunk) => {
    console.log(`[backend] ${chunk.toString().trimEnd()}`)
  })
  child.stderr?.on('data', (chunk) => {
    console.error(`[backend] ${chunk.toString().trimEnd()}`)
  })
  child.on('error', (error) => {
    console.error(`[backend] Failed to start: ${error.message}`)
  })
  child.on('exit', (code, signal) => {
    backendProcess = null
    backendPort = null
    if (code !== null) {
      console.log(`[backend] Exited with code ${code}`)
    } else if (signal) {
      console.log(`[backend] Exited with signal ${signal}`)
    }
  })

  backendProcess = child
  return child
}

export function stopBackend() {
  if (!backendProcess) {
    return
  }

  backendProcess.kill()
  backendProcess = null
}

