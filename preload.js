const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('agent', {
  send: (msg) => ipcRenderer.send('to-agent', msg),
  getMemory: () => ipcRenderer.invoke('memory-get'),
  setMemory: (text) => ipcRenderer.invoke('memory-set', text),
  setKey: (key) => ipcRenderer.send('set-key', key),
  onEvent: (cb) => ipcRenderer.on('agent-event', (_e, event) => cb(event)),
});
