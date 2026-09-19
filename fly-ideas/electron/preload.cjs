const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("fly", {
  isElectron: true,
  // --- пути / окружение ---
  getPaths: () => ipcRenderer.invoke("fly:getPaths"),
  checkEnv: () => ipcRenderer.invoke("fly:checkEnv"),
  openPath: (p) => ipcRenderer.invoke("fly:openPath", p),
  openExternal: (url) => ipcRenderer.invoke("fly:openExternal", url),
  chooseFolder: (kind, title) => ipcRenderer.invoke("fly:chooseFolder", kind, title),
  pickFolder: (title) => ipcRenderer.invoke("fly:pickFolder", title),
  resetFolder: (kind) => ipcRenderer.invoke("fly:resetFolder", kind),
  saveFile: (opts) => ipcRenderer.invoke("fly:saveFile", opts),
  openFile: (opts) => ipcRenderer.invoke("fly:openFile", opts),
  listExternal: () => ipcRenderer.invoke("fly:listExternal"),
  readRunFile: (dir, name) => ipcRenderer.invoke("fly:readRunFile", dir, name),
  exportRun: (dir) => ipcRenderer.invoke("fly:exportRun", dir),
  // --- рабочее место проекта ---
  projectPaths: (projectId) => ipcRenderer.invoke("fly:projectPaths", projectId),
  chooseProjectFolder: (projectId, kind, title) => ipcRenderer.invoke("fly:chooseProjectFolder", projectId, kind, title),
  resetProjectFolder: (projectId, kind) => ipcRenderer.invoke("fly:resetProjectFolder", projectId, kind),
  getPermissions: () => ipcRenderer.invoke("fly:getPermissions"),
  setPermissions: (patch) => ipcRenderer.invoke("fly:setPermissions", patch),
  // --- данные мозга ---
  listData: () => ipcRenderer.invoke("fly:listData"),
  download: (item, destDir) => ipcRenderer.invoke("fly:download", item, destDir),
  cancelDownload: (id) => ipcRenderer.invoke("fly:cancelDownload", id),
  onDownloadProgress: (cb) => {
    const h = (_e, p) => cb(p);
    ipcRenderer.on("fly:downloadProgress", h);
    return () => ipcRenderer.removeListener("fly:downloadProgress", h);
  },
  // --- скрипты проекта ---
  listScripts: (projectId) => ipcRenderer.invoke("fly:listScripts", projectId),
  readScript: (projectId, name) => ipcRenderer.invoke("fly:readScript", projectId, name),
  writeScript: (projectId, name, content, opts) => ipcRenderer.invoke("fly:writeScript", projectId, name, content, opts),
  deleteScript: (projectId, name) => ipcRenderer.invoke("fly:deleteScript", projectId, name),
  runScript: (projectId, name, args) => ipcRenderer.invoke("fly:runScript", projectId, name, args),
  killRun: (runId) => ipcRenderer.invoke("fly:killRun", runId),
  onRunOutput: (cb) => {
    const h = (_e, p) => cb(p);
    ipcRenderer.on("fly:runOutput", h);
    return () => ipcRenderer.removeListener("fly:runOutput", h);
  },
  // --- секреты (ключи API хранятся в userData, не в localStorage) ---
  getSecret: (k) => ipcRenderer.invoke("fly:getSecret", k),
  setSecret: (k, v) => ipcRenderer.invoke("fly:setSecret", k, v),
  // --- LLM-прокси: ключ не покидает main-процесс ---
  llmChat: (req) => ipcRenderer.invoke("fly:llmChat", req),
  // --- результаты прогонов ---
  listRuns: (projectId) => ipcRenderer.invoke("fly:listRuns", projectId),
  readRun: (dir) => ipcRenderer.invoke("fly:readRun", dir),
});
