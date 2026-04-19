import { app, shell, BrowserWindow, Tray, Menu, nativeImage, screen } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { spawn, ChildProcess } from 'child_process'
import { appendFileSync } from 'fs'
import icon from '../../resources/icon.png?asset'

let tray: Tray | null = null
let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null

// Use a log file in the user's home directory for maximum visibility
const LOG_FILE = join(app.getPath('home'), 'regis_debug.log')
function log(msg: string) {
  const line = `[${new Date().toISOString()}] ${msg}\n`
  try {
    appendFileSync(LOG_FILE, line)
  } catch (e) {}
}

function startBackend(): void {
  const isDev = is.dev && process.env['ELECTRON_RENDERER_URL']
  log(`Starting backend... isDev: ${isDev}`)
  
  if (isDev) {
    const backendPath = join(app.getAppPath(), '..', 'ai_assistant')
    const pythonExecutable = join(backendPath, '.venv', 'bin', 'python')
    
    log(`Dev backend path: ${backendPath}`)
    backendProcess = spawn(pythonExecutable, ['server.py'], {
      cwd: backendPath,
      stdio: 'inherit'
    })
  } else {
    const launcherPath = join(process.resourcesPath, 'backend_launcher.sh')
    log(`Prod launcher path: ${launcherPath}`)
    
    backendProcess = spawn('bash', [launcherPath], {
      cwd: process.resourcesPath,
      shell: true,
      env: { ...process.env, PATH: '/opt/homebrew/bin:/usr/local/bin:' + process.env.PATH }
    })
  }

  backendProcess?.on('error', (err) => { log(`Backend spawn error: ${err.message}`) })
  backendProcess?.on('exit', (code) => { log(`Backend exited with code: ${code}`) })
}

function createWindow(): BrowserWindow {
  log('Creating window...')
  const win = new BrowserWindow({
    width: 420,
    height: 680,
    show: false,
    frame: false,
    transparent: false, // Turn off transparency for debugging
    backgroundColor: '#0d0d14',
    alwaysOnTop: true,
    autoHideMenuBar: true,
    resizable: false,
    skipTaskbar: false, // Show in dock for now so user can find it
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
    }
  })

  win.once('ready-to-show', () => {
    log('Window ready to show')
    win.show() // Force show
    win.focus()
  })

  win.on('close', (event) => {
    if (!(app as any).isQuitting) {
      event.preventDefault()
      win.hide()
    }
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
  const primaryDisplay = screen.getPrimaryDisplay()
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize

  log(`Tray bounds: ${JSON.stringify(trayBounds)}`)

  let x = Math.round(trayBounds.x + trayBounds.width / 2 - winBounds.width / 2)
  let y = Math.round(trayBounds.y + trayBounds.height + 4)

  // Fallback if tray bounds are weird
  if (trayBounds.width === 0 || trayBounds.height === 0) {
    x = screenWidth - winBounds.width - 20
    y = 40
  }

  if (x + winBounds.width > screenWidth) x = screenWidth - winBounds.width - 10
  if (x < 0) x = 10
  if (y + winBounds.height > screenHeight) y = screenHeight - winBounds.height - 10
  if (y < 0) y = 40

  log(`Positioning window at: ${x}, ${y}`)
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

;(app as any).isQuitting = false

app.whenReady().then(() => {
  log('App ready event fired')
  electronApp.setAppUserModelId('com.regis.assistant')

  startBackend()
  mainWindow = createWindow()

  const trayIcon = nativeImage.createFromPath(icon).resize({ width: 18, height: 18 })
  trayIcon.setTemplateImage(true)

  tray = new Tray(trayIcon)
  tray.setToolTip('Regis — AI Assistant')

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Show Regis', click: () => { positionNearTray(); mainWindow?.show(); mainWindow?.focus() } },
    { label: 'Hide Regis', click: () => { mainWindow?.hide() } },
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
  log('App quitting...')
  if (backendProcess) {
    backendProcess.kill()
  }
})
