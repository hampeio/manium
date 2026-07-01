param(
    [string]$OutputRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) "dist"),
    [string]$StagingRoot = "",
    [switch]$IncludeApiKeys
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$name = "manium_portable_api_$stamp"
$zip = Join-Path $OutputRoot "$name.zip"

if (-not $StagingRoot) {
    $preferredDrive = Get-PSDrive -Name D -ErrorAction SilentlyContinue
    $StagingRoot = if ($preferredDrive) { "D:\manium-portable-build" } else { Join-Path $env:TEMP "manium-portable-build" }
}
$stage = Join-Path $StagingRoot $name

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
New-Item -ItemType Directory -Force -Path $StagingRoot | Out-Null
if (Test-Path -LiteralPath $stage) {
    [System.IO.Directory]::Delete("\\?\$stage", $true)
}

try {
    New-Item -ItemType Directory -Force -Path $stage | Out-Null

    foreach ($item in @("backend", "electron", "scripts")) {
        Copy-Item -LiteralPath (Join-Path $root $item) -Destination $stage -Recurse -Force
    }
    foreach ($item in @(
        "package.json", "package-lock.json", "prompt_overrides.json",
        "requirements.txt", "requirements-backend.txt",
        "README.md", "ARCHITECTURE.md", "WORKFLOW_TUTORIAL.md"
    )) {
        $source = Join-Path $root $item
        if (Test-Path -LiteralPath $source) {
            Copy-Item -LiteralPath $source -Destination $stage -Force
        }
    }

    # Runtime package: no historical projects, tests, caches, logs, or local report artifacts.
    foreach ($relative in @("backend\tests", "scripts\build_portable.ps1")) {
        $path = Join-Path $stage $relative
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $stage "generated_projects") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $stage "config") | Out-Null

    $envSource = if ($IncludeApiKeys) { Join-Path $root ".env" } else { Join-Path $root ".env.example" }
    if (-not (Test-Path -LiteralPath $envSource)) {
        throw "Configuration source not found: $envSource"
    }
    Copy-Item -LiteralPath $envSource -Destination (Join-Path $stage ".env") -Force
    Copy-Item -LiteralPath (Join-Path $root ".env.example") -Destination $stage -Force
    if ($IncludeApiKeys -and (Test-Path -LiteralPath (Join-Path $root "config\provider_profiles.json"))) {
        Copy-Item -LiteralPath (Join-Path $root "config\provider_profiles.json") -Destination (Join-Path $stage "config") -Force
    }

    # Electron executable only; npm caches and development dependencies are excluded.
    $electronSource = Join-Path $root "node_modules\electron\dist"
    if (-not (Test-Path -LiteralPath (Join-Path $electronSource "electron.exe"))) {
        throw "Electron runtime not found: $electronSource"
    }
    $electronTarget = Join-Path $stage "node_modules\electron"
    New-Item -ItemType Directory -Force -Path $electronTarget | Out-Null
    Copy-Item -LiteralPath $electronSource -Destination $electronTarget -Recurse -Force

    # Relocatable Python + installed Manim/backend dependencies.
    $runtime = Join-Path $stage "runtime\python"
    New-Item -ItemType Directory -Force -Path $runtime | Out-Null
    $venvConfig = Get-Content (Join-Path $root ".venv\pyvenv.cfg")
    $basePythonExe = ($venvConfig | Where-Object { $_ -like "executable = *" } | Select-Object -First 1) -replace "^executable = ", ""
    if (-not (Test-Path -LiteralPath $basePythonExe)) {
        throw "Base Python runtime not found: $basePythonExe"
    }
    $basePythonRoot = Split-Path -Parent $basePythonExe
    Copy-Item -Path (Join-Path $basePythonRoot "*") -Destination $runtime -Recurse -Force
    Copy-Item -Path (Join-Path $root ".venv\Lib\site-packages\*") -Destination (Join-Path $runtime "Lib\site-packages") -Recurse -Force
    Copy-Item -Path (Join-Path $root ".venv\Scripts\*") -Destination (Join-Path $runtime "Scripts") -Recurse -Force

    Get-ChildItem -LiteralPath $stage -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $stage -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in @(".pyc", ".pyo") } |
        Remove-Item -Force

    @(
        "@echo off",
        "set `"APP_ROOT=%~dp0`"",
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"%APP_ROOT%scripts\portable_launcher.ps1`"",
        "if errorlevel 1 (",
        "  echo Startup failed. See startup_error.log in this folder.",
        "  pause",
        ")"
    ) | Set-Content -LiteralPath (Join-Path $stage "Start-Manium.cmd") -Encoding ASCII

    @(
        "Manium Portable API Edition",
        "",
        "1. Extract the complete ZIP archive.",
        "2. Double-click Start-Manium.cmd.",
        "3. Python, Node.js, Electron, and Manim are bundled.",
        "4. generated_projects starts empty; no historical/test projects are included.",
        "",
        "API configuration is loaded from .env and can be changed in the app.",
        $(if ($IncludeApiKeys) { "PRIVATE BUILD: .env contains the current API credentials. Do not share this archive." } else { "Enter API credentials before first generation." })
    ) | Set-Content -LiteralPath (Join-Path $stage "README_PORTABLE.txt") -Encoding UTF8

    $manifest = @{
        name = $name
        built_at = (Get-Date).ToString("o")
        api_credentials_included = [bool]$IncludeApiKeys
        historical_projects_included = $false
        tests_included = $false
    } | ConvertTo-Json
    $manifest | Set-Content -LiteralPath (Join-Path $stage "portable_manifest.json") -Encoding UTF8

    Push-Location $StagingRoot
    try {
        & tar.exe -a -cf $zip $name
        if ($LASTEXITCODE -ne 0) {
            throw "tar.exe failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
    Write-Output $zip
} finally {
    if (Test-Path -LiteralPath $stage) {
        [System.IO.Directory]::Delete("\\?\$stage", $true)
    }
}
