import { app, BrowserWindow, globalShortcut } from 'electron'
import path from 'node:path'
import { startBackend, stopBackend } from './backend'
import { registerIpcHandlers } from './ipc'
import { attachBlurToHide, registerToggleShortcut, toggleWindow } from './window'

const WINDOW_WIDTH = 700
const WINDOW_HEIGHT = 130

function getPreloadPath() {
  return path.join(process.cwd(), 'dist-electron', 'preload.cjs')
}

function getRendererTarget() {
  const devUrl = process.env.VITE_DEV_SERVER_URL

  if (devUrl) {
    return { type: 'url' as const, value: devUrl }
  }

  return { type: 'file' as const, value: path.join(process.cwd(), 'dist', 'index.html') }
}

function createMainWindow() {
  const mainWindow = new BrowserWindow({
    width: WINDOW_WIDTH,
    height: WINDOW_HEIGHT,
    frame: false,
    transparent: false,
    backgroundColor: '#01000f',
    alwaysOnTop: true,
    skipTaskbar: true,
    show: false,
    resizable: false,
    webPreferences: {
      preload: getPreloadPath(),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // On macOS, make sure the window appears above fullscreen apps
  if (process.platform === 'darwin') {
    mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })
  }

  registerIpcHandlers(mainWindow)
  attachBlurToHide(mainWindow)
  registerToggleShortcut(() => toggleWindow(mainWindow))

  const target = getRendererTarget()
  if (target.type === 'url') {
    void mainWindow.loadURL(target.value)
  } else {
    void mainWindow.loadFile(target.value)
  }

  return mainWindow
}

app.whenReady().then(() => {
  void startBackend()
  createMainWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('will-quit', () => {
  stopBackend()
  globalShortcut.unregisterAll()
})
