$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$runtimeRoot = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
$bundledNode = Join-Path $runtimeRoot "node\bin\node.exe"
$bundledPython = Join-Path $runtimeRoot "python\python.exe"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$electronCli = Join-Path $projectRoot "node_modules\electron\cli.js"
$electronExe = Join-Path $projectRoot "node_modules\electron\dist\electron.exe"

Set-Location $projectRoot

Write-Host "Starting Manim Teaching Animation Generator..." -ForegroundColor Cyan
Write-Host "Project: $projectRoot" -ForegroundColor DarkGray

if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeExe = (Get-Command node).Source
} elseif (Test-Path $bundledNode) {
    $nodeExe = $bundledNode
} else {
    Write-Host "Node.js was not found. Install Node.js 18+ from https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example" -ForegroundColor Green
}

if (-not (Test-Path $venvPython)) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $bootstrapPython = (Get-Command python).Source
    } elseif (Test-Path $bundledPython) {
        $bootstrapPython = $bundledPython
    } else {
        Write-Host "Python was not found. Install Python 3.11+ first." -ForegroundColor Yellow
        Read-Host "Press Enter to close"
        exit 1
    }

    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    & $bootstrapPython -m venv ".venv"
}

Write-Host "Checking lightweight backend dependencies..." -ForegroundColor Cyan
& $venvPython -m pip install -r requirements-backend.txt

if (-not (Test-Path $electronCli)) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "Installing Electron dependencies..." -ForegroundColor Cyan
        npm install
    } else {
        Write-Host "Electron dependencies are missing and npm is not available." -ForegroundColor Yellow
        Write-Host "Install Node.js 18+ or run npm install in this project." -ForegroundColor Yellow
        Read-Host "Press Enter to close"
        exit 1
    }
}

if (-not (Test-Path $electronExe)) {
    Write-Host "Completing Electron binary installation..." -ForegroundColor Cyan
    & $nodeExe (Join-Path $projectRoot "node_modules\electron\install.js")
}

$env:MANIM_APP_PYTHON = $venvPython
$env:PATH = "$(Split-Path $nodeExe);$(Split-Path $venvPython);$env:PATH"

Write-Host "Launching desktop app..." -ForegroundColor Green
& $nodeExe $electronCli $projectRoot
