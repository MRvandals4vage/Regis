import { app, shell, BrowserWindow, Tray, Menu } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'

let tray: Tray | null = null
let mainWindow: BrowserWindow | null = null

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 400,
    height: 500,
    show: false, // Don't show immediately, wait for tray
    frame: false, // Frameless UI for floating look
    transparent: true,
    alwaysOnTop: true, // Float above other windows
    autoHideMenuBar: true,
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true
    }
  })

  // Hide the window when user clicks somewhere else
  win.on('blur', () => {
    win.hide()
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

const toggleWindow = () => {
  if (!mainWindow) return
  if (mainWindow.isVisible()) {
    mainWindow.hide()
  } else {
    mainWindow.show()
    mainWindow.focus()
  }
}

app.whenReady().then(() => {
  // Set app user model id for windows
  electronApp.setAppUserModelId('com.electron')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // Hide dock icon correctly on macOS to make it a pure Menu Bar app
  if (process.platform === 'darwin' && app.dock) {
    app.dock.hide()
  }

  mainWindow = createWindow()

  // Setup System Tray
  tray = new Tray(icon) // (Using default electron icon, natively you provide a 16x16 .png)
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Toggle Chat Window', click: toggleWindow },
    { type: 'separator' },
    { label: 'Quit Regis', click: () => app.quit() }
  ])
  tray.setToolTip('Regis Assistant')
  tray.setContextMenu(contextMenu)

  // Clicking the tray icon itself toggles the window
  tray.on('click', toggleWindow)
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
