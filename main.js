const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

let win = null;
let py = null;
let apiKey = process.env.GROQ_API_KEY || '';

const memoryPath = () => path.join(app.getPath('userData'), 'memory.md');

function emit(event) {
  if (win && !win.isDestroyed()) win.webContents.send('agent-event', event);
}

function startBridge() {
  if (py) py.kill();
  if (!apiKey) return emit({ type: 'need-key' });

  const cmd = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
  const proc = spawn(cmd, ['-u', path.join(__dirname, 'bridge.py')], {
    cwd: __dirname,
    env: { ...process.env, GROQ_API_KEY: apiKey, MEMORY_PATH: memoryPath(), PYTHONIOENCODING: 'utf-8' },
  });
  py = proc;

  readline.createInterface({ input: proc.stdout }).on('line', (line) => {
    if (proc !== py) return;
    try { emit(JSON.parse(line)); } catch { /* ignore non-JSON output */ }
  });
  proc.stderr.on('data', (d) => { if (proc === py) emit({ type: 'error', text: d.toString() }); });
  proc.on('error', (e) => { if (proc === py) emit({ type: 'fatal', text: `Could not start Python (${cmd}): ${e.message}` }); });
  proc.on('exit', (code) => { if (proc === py) emit({ type: 'exit', code }); });
}

function createWindow() {
  win = new BrowserWindow({
    width: 980,
    height: 720,
    minWidth: 520,
    minHeight: 480,
    title: 'Local File Agent',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.setMenuBarVisibility(false);
  win.loadFile('index.html');
  win.webContents.on('did-finish-load', startBridge);
}

ipcMain.on('to-agent', (_e, msg) => {
  if (py && py.stdin.writable) py.stdin.write(JSON.stringify(msg) + '\n');
});
ipcMain.handle('memory-get', () => {
  try { return fs.readFileSync(memoryPath(), 'utf8'); } catch { return ''; }
});
ipcMain.handle('memory-set', (_e, text) => {
  fs.writeFileSync(memoryPath(), String(text || ''), 'utf8');
  return true;
});
ipcMain.on('set-key', (_e, key) => {
  apiKey = String(key || '').trim();
  startBridge();
});

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (py) py.kill(); app.quit(); });
