const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("fly", {
  isElectron: true,
  // --- пути / окружение ---
  getPaths: () => ipcRenderer.invoke("fly:getPaths"),
  checkEnv: () => ipcRenderer.invoke("fly:checkEnv"),
  openPath: (p) => ipcRenderer.invoke("fly:openPath", p),
  openExternal: (url) => ipcRenderer.invoke("fly:openExternal", url),
  // --- данные мозга ---
  listData: () => ipcRenderer.invoke("fly:listData"),
  download: (item) => ipcRenderer.invoke("fly:download", item),
  cancelDownload: (id) => ipcRenderer.invoke("fly:cancelDownload", id),
  onDownloadProgress: (cb) => {
    const h = (_e, p) => cb(p);
    ipcRenderer.on("fly:downloadProgress", h);
    return () => ipcRenderer.removeListener("fly:downloadProgress", h);
  },
  // --- запуск скриптов ---
  listScripts: () => ipcRenderer.invoke("fly:listScripts"),
  readScript: (name) => ipcRenderer.invoke("fly:readScript", name),
  writeScript: (name, content) => ipcRenderer.invoke("fly:writeScript", name, content),
  runScript: (name, args) => ipcRenderer.invoke("fly:runScript", name, args),
  killRun: (runId) => ipcRenderer.invoke("fly:killRun", runId),
  onRunOutput: (cb) => {
    const h = (_e, p) => cb(p);
    ipcRenderer.on("fly:runOutput", h);
    return () => ipcRenderer.removeListener("fly:runOutput", h);
  },
  // --- секреты (ключи API хранятся в userData, не в localStorage) ---
  getSecret: (k) => ipcRenderer.invoke("fly:getSecret", k),
  setSecret: (k, v) => ipcRenderer.invoke("fly:setSecret", k, v),
  // --- LLM-прокси (ключ не покидает main-процесс) ---
  llmChat: (req) => ipcRenderer.invoke("fly:llmChat", req),
  // --- результаты прогонов ---
  listRuns: () => ipcRenderer.invoke("fly:listRuns"),
  readRun: (dir) => ipcRenderer.invoke("fly:readRun", dir),
});
