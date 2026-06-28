const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

let backendProcess = null;

app.setName("Manim 教学动画生成器");

async function isBackendReady() {
  try {
    const response = await fetch("http://127.0.0.1:8765/health");
    return response.ok;
  } catch (_error) {
    return false;
  }
}

async function waitForBackend() {
  for (let index = 0; index < 30; index += 1) {
    if (await isBackendReady()) return true;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

async function startBackend() {
  if (await isBackendReady()) {
    console.log("[backend] Reusing existing local backend.");
    return;
  }

  const root = path.resolve(__dirname, "..");
  const bundledPython = path.join(root, ".venv", "Scripts", "python.exe");
  const pythonExe = process.env.MANIM_APP_PYTHON || (fs.existsSync(bundledPython) ? bundledPython : "python");
  backendProcess = spawn(pythonExe, ["-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8765"], {
    cwd: root,
    shell: false,
    windowsHide: true,
    env: { ...process.env, PYTHONUNBUFFERED: "1" }
  });

  backendProcess.stdout.on("data", (data) => console.log(`[backend] ${data}`));
  backendProcess.stderr.on("data", (data) => console.error(`[backend] ${data}`));

  await waitForBackend();
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: "#0f172a",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  win.loadFile(path.join(__dirname, "renderer.html"));
}

app.whenReady().then(async () => {
  await startBackend();
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProcess) backendProcess.kill();
});

ipcMain.handle("select-output-dir", async () => {
  const result = await dialog.showOpenDialog({ properties: ["openDirectory", "createDirectory"] });
  return result.canceled ? null : result.filePaths[0];
});
