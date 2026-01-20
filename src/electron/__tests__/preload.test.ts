import { expect, it, vi } from 'vitest'
import { IPC_CHANNELS } from '../ipc'

const exposeInMainWorld = vi.fn()
const invoke = vi.fn()

vi.mock('electron', () => ({
  contextBridge: {
    exposeInMainWorld,
  },
  ipcRenderer: {
    invoke,
  },
}))

import '../preload'

it('exposes the electron API and wires IPC calls', () => {
  expect(exposeInMainWorld).toHaveBeenCalledOnce()

  const [, api] = exposeInMainWorld.mock.calls[0]

  api.hideWindow()
  expect(invoke).toHaveBeenCalledWith(IPC_CHANNELS.hideWindow)

  api.resizeWindow({ width: 320, height: 160 })
  expect(invoke).toHaveBeenCalledWith(IPC_CHANNELS.resizeWindow, { width: 320, height: 160 })
})
