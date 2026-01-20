import { describe, expect, it, vi } from 'vitest'

vi.mock('electron', () => ({
  globalShortcut: {
    register: vi.fn(() => true),
  },
}))

import { globalShortcut } from 'electron'
import { attachBlurToHide, registerToggleShortcut, toggleWindow } from '../window'

type HandlerMap = { blur?: () => void }

function createWindow(visible: boolean) {
  const handlers: HandlerMap = {}

  return {
    isVisible: vi.fn(() => visible),
    show: vi.fn(),
    focus: vi.fn(),
    hide: vi.fn(),
    on: vi.fn((event: 'blur', handler: () => void) => {
      handlers[event] = handler
    }),
    handlers,
  }
}

describe('toggleWindow', () => {
  it('hides the window when currently visible', () => {
    const window = createWindow(true)

    toggleWindow(window)

    expect(window.hide).toHaveBeenCalledOnce()
    expect(window.show).not.toHaveBeenCalled()
    expect(window.focus).not.toHaveBeenCalled()
  })

  it('shows and focuses the window when currently hidden', () => {
    const window = createWindow(false)

    toggleWindow(window)

    expect(window.show).toHaveBeenCalledOnce()
    expect(window.focus).toHaveBeenCalledOnce()
    expect(window.hide).not.toHaveBeenCalled()
  })
})

describe('attachBlurToHide', () => {
  it('hides the window when blur fires', () => {
    const window = createWindow(true)

    attachBlurToHide(window)

    expect(window.on).toHaveBeenCalledWith('blur', expect.any(Function))
    window.handlers.blur?.()
    expect(window.hide).toHaveBeenCalledOnce()
  })
})

describe('registerToggleShortcut', () => {
  it('registers the accelerator with the provided handler', () => {
    const toggle = vi.fn()

    const result = registerToggleShortcut(toggle)

    expect(globalShortcut.register).toHaveBeenCalledWith('CommandOrControl+/', toggle)
    expect(result).toBe(true)
  })
})
