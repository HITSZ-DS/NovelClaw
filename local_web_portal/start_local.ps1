param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8010,
  [switch]$Reload
)

$ErrorActionPreference = "Stop"

Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

function Get-PythonCommand {
  if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
      $pythonVersion = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
      if (Test-SupportedPythonVersion $pythonVersion) {
        return @("python")
      }
    } catch {
      # Fall through to py launcher probing.
    }
  }

  if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($minor in (18..10)) {
      $candidate = "3.$minor"
      cmd /c "py -$candidate -c ""import sys"" >nul 2>nul"
      if ($LASTEXITCODE -eq 0) {
        return @("py", "-$candidate")
      }
    }
  }
  throw "Python is not installed. Install Python 3.10 or newer first."
}

function Test-SupportedPythonVersion {
  param(
    [string]$VersionText
  )
  if (-not $VersionText) {
    return $false
  }
  $parts = $VersionText.Split(".")
  if ($parts.Length -lt 2) {
    return $false
  }
  $major = 0
  $minor = 0
  if (-not [int]::TryParse($parts[0], [ref]$major)) {
    return $false
  }
  if (-not [int]::TryParse($parts[1], [ref]$minor)) {
    return $false
  }
  return ($major -eq 3 -and $minor -ge 10)
}

function Invoke-Python {
  param(
    [string[]]$BaseCommand,
    [string[]]$Arguments
  )
  $prefixArgs = @()
  if ($BaseCommand.Length -gt 1) {
    $prefixArgs = $BaseCommand[1..($BaseCommand.Length - 1)]
  }
  & $BaseCommand[0] @prefixArgs @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Python command failed: $($Arguments -join ' ')"
  }
}

$bootstrapPython = @(Get-PythonCommand)
$bootstrapPrefixArgs = @()
if ($bootstrapPython.Length -gt 1) {
  $bootstrapPrefixArgs = $bootstrapPython[1..($bootstrapPython.Length - 1)]
}
$versionRaw = (& $bootstrapPython[0] @bootstrapPrefixArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if (-not $versionRaw) {
  throw "Failed to detect Python version."
}

if (-not (Test-SupportedPythonVersion $versionRaw)) {
  throw "Unsupported Python version: $versionRaw. Use Python 3.10 or newer to start the web portal."
}

$venvMissing = -not (Test-Path ".venv\Scripts\python.exe")
if (-not $venvMissing) {
  $existingVenvVersion = (& .\.venv\Scripts\python.exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
  if (-not (Test-SupportedPythonVersion $existingVenvVersion)) {
    Write-Host "[setup] Existing .venv uses unsupported Python $existingVenvVersion. Recreating ..."
    Remove-Item -Recurse -Force ".venv"
    $venvMissing = $true
  }
}

if ($venvMissing) {
  Write-Host "[setup] Creating .venv with Python $versionRaw ..."
  Invoke-Python -BaseCommand $bootstrapPython -Arguments @("-m", "venv", ".venv")
}

$venvPython = Resolve-Path ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  throw "Virtual environment bootstrap failed: .venv\\Scripts\\python.exe not found."
}

$venvVersion = (& $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if (-not (Test-SupportedPythonVersion $venvVersion)) {
  throw "The project virtual environment uses Python $venvVersion. Recreate .venv with Python 3.10 or newer."
}

$env:EMBEDDING_MODEL = "none"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[setup] Installing runtime dependencies ..."
& $venvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
  throw "Failed to upgrade pip/setuptools/wheel."
}
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
  throw "Failed to install root requirements."
}
& $venvPython -m pip install -r local_web_portal\requirements.txt
if ($LASTEXITCODE -ne 0) {
  throw "Failed to install web portal requirements."
}

Write-Host "[check] Verifying FastAPI app import ..."
& $venvPython -c "import importlib; m = importlib.import_module('local_web_portal.app.main'); assert getattr(m, 'app', None) is not None"
if ($LASTEXITCODE -ne 0) {
  throw "FastAPI app import failed. Check your environment and dependencies."
}

$uvicornArgs = @(
  "-m", "uvicorn",
  "local_web_portal.app.main:app",
  "--host", $BindHost,
  "--port", [string]$Port
)
if ($Reload.IsPresent) {
  $uvicornArgs += "--reload"
}

Write-Host "[run] Starting web portal on http://${BindHost}:$Port"
& $venvPython @uvicornArgs
