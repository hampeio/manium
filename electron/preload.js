const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopApi", {
  selectOutputDir: () => ipcRenderer.invoke("select-output-dir"),
  apiBase: `http://127.0.0.1:${/^\d+$/.test(process.env.MANIM_PORTABLE_PORT || "") ? process.env.MANIM_PORTABLE_PORT : "8765"}`
});
