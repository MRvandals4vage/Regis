import { app, shell, BrowserWindow, Tray, Menu, nativeImage } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { spawn, ChildProcess } from 'child_process'
import icon from '../../resources/icon.png?asset'

let tray: Tray | null = null
let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null

function startBackend(): void {
  const isDev = is.dev && process.env['ELECTRON_RENDERER_URL']
  
  if (isDev) {
    const backendPath = join(app.getAppPath(), '..', 'ai_assistant')
    const pythonExecutable = join(backendPath, '.venv', 'bin', 'python')
    
    console.log(`Starting backend in dev: ${backendPath}`)
    backendProcess = spawn(pythonExecutable, ['server.py'], {
      cwd: backendPath,
      stdio: 'inherit'
    })
  } else {
    // In production, we use the launcher script
    const launcherPath = join(process.resourcesPath, 'resources', 'backend_launcher.sh')
    
    console.log(`Starting backend via launcher: ${launcherPath}`)
    backendProcess = spawn('bash', [launcherPath], {
      cwd: process.resourcesPath,
      stdio: 'inherit'
    })
  }

  backendProcess?.on('error', (err) => {
    console.error('Failed to start backend:', err)
  })
}

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
    skipTaskbar: true, // Don't show in dock when visible
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
    }
  })

  win.once('ready-to-show', () => {
    // We don't necessarily show it on start if it's a menu bar app
    // but the user might want it to pop up. Let's keep it hidden initially
    // or show it if they just opened the app from Applications.
    if (!app.getLoginItemSettings().wasOpenedAtLogin) {
      toggleWindow()
    }
  })

  win.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault()
      win.hide()
    }
  })

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
  
  // Center window horizontally under the tray icon
  const x = Math.round(trayBounds.x + trayBounds.width / 2 - winBounds.width / 2)
  // Position window vertically below the tray icon
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

// Custom property to handle closing
;(app as any).isQuitting = false

app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.regis.assistant')

  // Set to launch at login
  app.setLoginItemSettings({
    openAtLogin: true,
    openAsHidden: true
  })

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // Hide dock icon on macOS — pure menu-bar app
  if (process.platform === 'darwin' && app.dock) {
    app.dock.hide()
  }

  startBackend()
  mainWindow = createWindow()

  const trayIcon = nativeImage.createFromPath(icon).resize({ width: 18, height: 18 })
  trayIcon.setTemplateImage(true)

  tray = new Tray(trayIcon)
  tray.setToolTip('Regis — AI Assistant')

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Open Regis',   click: () => { positionNearTray(); mainWindow?.show(); mainWindow?.focus() } },
    { type: 'checkbox', label: 'Launch at Login', checked: app.getLoginItemSettings().openAtLogin, click: (item) => {
      app.setLoginItemSettings({ openAtLogin: item.checked })
    }},
    { type: 'separator' },
    { label: 'Quit Regis',   click: () => {
      ;(app as any).isQuitting = true
      app.quit()
    }}
  ])
  tray.setContextMenu(contextMenu)

  tray.on('click', toggleWindow)
})

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill()
  }
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
