# X-Wizard — Windows prerequisite bootstrap
# Detects and installs Git and Python with cascading fallbacks.
# Run: powershell -ExecutionPolicy Bypass -File .cursor/skills/start/scripts/bootstrap-win.ps1
# Exit: 0 = all prerequisites present, 1 = something still missing

$ErrorActionPreference = "Continue"
$InstalledSomething = $false

function Write-Status  { param($msg) Write-Host "  [CHECK]   $msg" -ForegroundColor Cyan }
function Write-Ok      { param($msg) Write-Host "  [OK]      $msg" -ForegroundColor Green }
function Write-Install { param($msg) Write-Host "  [INSTALL] $msg" -ForegroundColor Yellow }
function Write-Fail    { param($msg) Write-Host "  [FAIL]    $msg" -ForegroundColor Red }

# Refresh PATH from registry so newly installed tools are found without restarting
function Refresh-PathFromRegistry {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path    = "$machinePath;$userPath"
}

# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------
function Install-GitTool {
    # Method 1: winget (built-in on Win10 1809+ / Win11)
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Install "Git via winget ..."
        try {
            winget install --id Git.Git -e --source winget `
                --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
            Refresh-PathFromRegistry
            if (Get-Command git -ErrorAction SilentlyContinue) {
                $script:InstalledSomething = $true
                return $true
            }
        } catch { }
    }

    # Method 2: Chocolatey (if installed)
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Install "Git via Chocolatey ..."
        try {
            choco install git -y 2>&1 | Out-Null
            Refresh-PathFromRegistry
            if (Get-Command git -ErrorAction SilentlyContinue) {
                $script:InstalledSomething = $true
                return $true
            }
        } catch { }
    }

    # Method 3: Direct download + silent install (works on any Windows with PowerShell)
    Write-Install "Git via direct download (silent install) ..."
    try {
        $release = Invoke-RestMethod "https://api.github.com/repos/git-for-windows/git/releases/latest"
        $asset   = $release.assets | Where-Object { $_.name -match "64-bit\.exe$" } | Select-Object -First 1
        if ($asset) {
            $installer = "$env:TEMP\git-installer.exe"
            Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $installer -UseBasicParsing
            Start-Process $installer -ArgumentList `
                '/VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS' `
                -Wait
            Remove-Item $installer -ErrorAction SilentlyContinue
            Refresh-PathFromRegistry
            if (Get-Command git -ErrorAction SilentlyContinue) {
                $script:InstalledSomething = $true
                return $true
            }
        }
    } catch {
        Write-Fail "Direct download failed: $_"
    }

    return $false
}

function Check-GitTool {
    Write-Status "Git ..."
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $ver = (git --version) -replace "git version ",""
        Write-Ok "Git $ver"
        return $true
    }

    if (Install-GitTool) {
        Refresh-PathFromRegistry
        if (Get-Command git -ErrorAction SilentlyContinue) {
            $ver = (git --version) -replace "git version ",""
            Write-Ok "Git $ver"
            return $true
        }
    }

    Write-Fail "Could not install Git automatically."
    Write-Host "  -> Download from https://git-scm.com/download/win" -ForegroundColor Yellow
    return $false
}

# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------
function Install-PythonTool {
    # Method 1: winget
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Install "Python via winget ..."
        try {
            winget install --id Python.Python.3.13 -e --source winget `
                --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
            Refresh-PathFromRegistry
            if (Get-Command python -ErrorAction SilentlyContinue) {
                $script:InstalledSomething = $true
                return $true
            }
        } catch { }
    }

    # Method 2: Microsoft Store link
    Write-Install "Python via Microsoft Store ..."
    try {
        Start-Process "ms-windows-store://pdp/?ProductId=9PNRBTZXMB4Z"
        Write-Host ""
        Write-Host "  The Microsoft Store should open to Python 3.13."
        Write-Host "  Click 'Get' or 'Install', wait for it to finish,"
        Write-Host "  then press Enter here to continue."
        Read-Host
        Refresh-PathFromRegistry
        if (Get-Command python -ErrorAction SilentlyContinue) {
            $script:InstalledSomething = $true
            return $true
        }
    } catch { }

    # Method 3: Direct download + silent install
    Write-Install "Python via direct download (silent install) ..."
    try {
        $pyUrl = "https://www.python.org/ftp/python/3.13.2/python-3.13.2-amd64.exe"
        $installer = "$env:TEMP\python-installer.exe"
        Invoke-WebRequest -Uri $pyUrl -OutFile $installer -UseBasicParsing
        Start-Process $installer -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1' -Wait
        Remove-Item $installer -ErrorAction SilentlyContinue
        Refresh-PathFromRegistry
        if (Get-Command python -ErrorAction SilentlyContinue) {
            $script:InstalledSomething = $true
            return $true
        }
    } catch {
        Write-Fail "Direct download failed: $_"
    }

    return $false
}

function Check-PythonTool {
    Write-Status "Python ..."
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $ver = (python --version 2>&1) -replace "Python ",""
        Write-Ok "Python $ver"
        return $true
    }

    if (Install-PythonTool) {
        Refresh-PathFromRegistry
        if (Get-Command python -ErrorAction SilentlyContinue) {
            $ver = (python --version 2>&1) -replace "Python ",""
            Write-Ok "Python $ver"
            return $true
        }
    }

    Write-Fail "Could not install Python automatically."
    Write-Host "  -> Open Microsoft Store and search 'Python 3.13', or" -ForegroundColor Yellow
    Write-Host "  -> Download from https://www.python.org/downloads/" -ForegroundColor Yellow
    return $false
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
function Main {
    Write-Host ""
    Write-Host "======================================================"
    Write-Host "  X-Wizard — Prerequisites Bootstrap (Windows)"
    Write-Host "======================================================"
    Write-Host ""

    $gitOk = Check-GitTool
    $pyOk  = Check-PythonTool

    Write-Host ""

    if (-not $gitOk -or -not $pyOk) {
        Write-Host "======================================================"
        Write-Host "  Some prerequisites could not be installed." -ForegroundColor Red
        Write-Host "  Install them manually, restart Cursor, and re-run /start."
        Write-Host "======================================================"
        Write-Host ""
        exit 1
    }

    if ($InstalledSomething) {
        Write-Host "======================================================"
        Write-Host "  Prerequisites installed successfully." -ForegroundColor Green
        Write-Host "  RESTART CURSOR now, then type /start again."
        Write-Host "======================================================"
    } else {
        Write-Host "======================================================"
        Write-Host "  All prerequisites already present." -ForegroundColor Green
        Write-Host "======================================================"
    }
    Write-Host ""
    exit 0
}

Main
