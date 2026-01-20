import { contextBridge, ipcRenderer } from 'electron'
import { IPC_CHANNELS } from './ipc'

type ResizePayload = {
  width: number
  height: number
}

const api = {
  hideWindow: () => ipcRenderer.invoke(IPC_CHANNELS.hideWindow),
  resizeWindow: (size: ResizePayload) => ipcRenderer.invoke(IPC_CHANNELS.resizeWindow, size),
}

contextBridge.exposeInMainWorld('electron', api)
