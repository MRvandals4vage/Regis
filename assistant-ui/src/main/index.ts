import { app, shell, BrowserWindow, Tray, Menu, nativeImage } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'

let tray: Tray | null = null
let mainWindow: BrowserWindow | null = null

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 420,
    height: 680,
    show: false,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    autoHideMenuBar: true,
    resizable: false,
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
    }
  })

  // Show window when it's ready to prevent flash
  win.once('ready-to-show', () => {
    win.show()
    win.focus()
  })

  // Hide when focus lost (menu-bar style)
  win.on('blur', () => {
    if (!is.dev) win.hide()
  })

  win.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }

  return win
}

const positionNearTray = () => {
  if (!mainWindow || !tray) return
  const trayBounds = tray.getBounds()
  const winBounds = mainWindow.getBounds()
  const x = Math.round(trayBounds.x + trayBounds.width / 2 - winBounds.width / 2)
  const y = Math.round(trayBounds.y + trayBounds.height + 4)
  mainWindow.setPosition(x, y)
}

const toggleWindow = () => {
  if (!mainWindow) return
  if (mainWindow.isVisible()) {
    mainWindow.hide()
  } else {
    positionNearTray()
    mainWindow.show()
    mainWindow.focus()
  }
}

app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.regis.assistant')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // Hide dock icon on macOS — pure menu-bar app
  if (process.platform === 'darwin' && app.dock) {
    app.dock.hide()
  }

  mainWindow = createWindow()

  // Tray icon — use 16x16 template image on macOS for automatic dark/light mode
  const trayIcon = nativeImage.createFromPath(icon).resize({ width: 18, height: 18 })
  trayIcon.setTemplateImage(true)

  tray = new Tray(trayIcon)
  tray.setToolTip('Regis — AI Assistant')

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Open Regis',   click: () => { positionNearTray(); mainWindow?.show(); mainWindow?.focus() } },
    { label: 'Hide',         click: () => mainWindow?.hide() },
    { type: 'separator' },
    { label: 'Quit Regis',   click: () => app.quit() }
  ])
  tray.setContextMenu(contextMenu)

  tray.on('click', toggleWindow)
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
