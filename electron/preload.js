const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopApi", {
  selectOutputDir: () => ipcRenderer.invoke("select-output-dir")
});
