import { BrowserWindow, ipcMain } from 'electron'

export const IPC_CHANNELS = {
  hideWindow: 'cumo:hideWindow',
  resizeWindow: 'cumo:resizeWindow',
} as const

type ResizePayload = {
  width: number
  height: number
}

export function registerIpcHandlers(window: BrowserWindow) {
  ipcMain.handle(IPC_CHANNELS.hideWindow, () => {
    window.hide()
  })

  ipcMain.handle(IPC_CHANNELS.resizeWindow, (_event, payload?: Partial<ResizePayload>) => {
    const width = payload?.width
    const height = payload?.height

    if (typeof width === 'number' && typeof height === 'number') {
      window.setSize(width, height)
    }
  })
}
