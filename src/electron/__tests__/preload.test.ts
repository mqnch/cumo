import { expect, it, vi } from 'vitest'
import { IPC_CHANNELS } from '../ipc'

const mocks = vi.hoisted(() => ({
  exposeInMainWorld: vi.fn(),
  invoke: vi.fn(),
}))

vi.mock('electron', () => ({
  contextBridge: {
    exposeInMainWorld: mocks.exposeInMainWorld,
  },
  ipcRenderer: {
    invoke: mocks.invoke,
  },
}))

it('exposes the electron API and wires IPC calls', async () => {
  vi.resetModules()
  await import('../preload')

  expect(mocks.exposeInMainWorld).toHaveBeenCalledOnce()

  const [, api] = mocks.exposeInMainWorld.mock.calls[0]

  api.hideWindow()
  expect(mocks.invoke).toHaveBeenCalledWith(IPC_CHANNELS.hideWindow)

  api.resizeWindow({ width: 320, height: 160 })
  expect(mocks.invoke).toHaveBeenCalledWith(IPC_CHANNELS.resizeWindow, { width: 320, height: 160 })

  await api.getBackendPort()
  expect(mocks.invoke).toHaveBeenCalledWith(IPC_CHANNELS.getBackendPort)
})
