import { spawn, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

let backendProcess: ChildProcess | null = null

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

function buildBackendEnv() {
  return {
    ...process.env,
    CUMO_BACKEND_PORT: process.env.CUMO_BACKEND_PORT ?? '5000',
  }
}

export function startBackend() {
  if (backendProcess) {
    return backendProcess
  }

  const backendDir = path.join(process.cwd(), 'backend')
  if (!fs.existsSync(backendDir)) {
    console.warn('[backend] Missing backend directory, skipping Python spawn.')
    return null
  }

  const python = resolvePythonExecutable(backendDir)
  const child = spawn(python, ['-u', 'app.py'], {
    cwd: backendDir,
    env: buildBackendEnv(),
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

