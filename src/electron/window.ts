import { globalShortcut } from 'electron'

export type WindowLike = {
  isVisible: () => boolean
  show: () => void
  focus: () => void
  hide: () => void
  on: (event: 'blur', handler: () => void) => void
}

export function toggleWindow(window: WindowLike) {
  if (window.isVisible()) {
    window.hide()
    return
  }

  window.show()
  window.focus()
}

export function attachBlurToHide(window: WindowLike) {
  window.on('blur', () => window.hide())
}

export function registerToggleShortcut(
  toggle: () => void,
  accelerator = 'CommandOrControl+/',
) {
  return globalShortcut.register(accelerator, toggle)
}
