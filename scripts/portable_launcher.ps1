$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$electronExe = Join-Path $projectRoot "node_modules\electron\dist\electron.exe"
$pythonExe = Join-Path $projectRoot "runtime\python\python.exe"
$pythonRoot = Join-Path $projectRoot "runtime\python"
$errorLog = Join-Path $projectRoot "startup_error.log"

try {
    Set-Location $projectRoot
    $env:MANIM_APP_PYTHON = $pythonExe
    $env:MANIM_PORTABLE_ROOT = $projectRoot
    $env:MANIM_PORTABLE_PORT = "18765"
    $env:PYTHONHOME = $pythonRoot
    $env:PYTHONPATH = Join-Path $pythonRoot "Lib\site-packages"
    $env:PYTHONNOUSERSITE = "1"
    $env:NO_PROXY = "127.0.0.1,localhost"
    $env:PATH = "$pythonRoot;$(Join-Path $pythonRoot 'Scripts');$(Join-Path $projectRoot 'node_modules\electron\dist');$env:PATH"

    if (-not (Test-Path $electronExe) -or -not (Test-Path $pythonExe)) {
        throw "Portable runtime is incomplete. Extract the entire ZIP archive before starting."
    }

    if (Test-Path $errorLog) {
        Remove-Item -LiteralPath $errorLog -Force
    }
    & $electronExe $projectRoot
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        throw "Electron exited with code $LASTEXITCODE."
    }
} catch {
    ($_ | Out-String) | Set-Content -LiteralPath $errorLog -Encoding UTF8
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Manium could not start. See startup_error.log in the extracted folder.",
        "Startup failed"
    ) | Out-Null
    exit 1
}
