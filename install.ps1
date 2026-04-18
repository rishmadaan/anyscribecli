# ──────────────────────────────────────────────────────────────
# scribe installer for Windows
#
# Usage (PowerShell):
#   irm https://raw.githubusercontent.com/rishmadaan/anyscribecli/main/install.ps1 | iex
#
# What it does:
#   1. Checks for Python 3.10+, offers to install via winget
#   2. Checks for ffmpeg, offers to install via winget/choco
#   3. Installs yt-dlp via pip
#   4. Installs anyscribecli via pip
#   5. Fixes PATH so `scribe` works from any terminal
#   6. Tells you to run `scribe ui`
# ──────────────────────────────────────────────────────────────

$ErrorActionPreference = 'Stop'

# ── Helpers ───────────────────────────────────────────────────

function Write-Banner {
    Write-Host ""
    Write-Host "  +-------------------------------------+" -ForegroundColor White
    Write-Host "  |       scribe installer               |" -ForegroundColor White
    Write-Host "  |  Video -> Transcript -> Markdown      |" -ForegroundColor White
    Write-Host "  +-------------------------------------+" -ForegroundColor White
    Write-Host ""
}

function Write-Info($msg)    { Write-Host "==> $msg" -ForegroundColor Blue }
function Write-Ok($msg)      { Write-Host "  + $msg" -ForegroundColor Green }
function Write-Warn($msg)    { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Fail($msg)    { Write-Host "  x $msg" -ForegroundColor Red }

function Test-CommandExists($cmd) {
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    # Reload PATH from registry so newly installed tools are found
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"
}

# ── Check Python ──────────────────────────────────────────────

function Test-Python {
    Write-Info "Checking Python..."

    # Windows uses 'python' (not 'python3') when installed from python.org
    foreach ($cmd in @('python', 'python3')) {
        if (Test-CommandExists $cmd) {
            try {
                $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                $parts = $ver.Split('.')
                $major = [int]$parts[0]
                $minor = [int]$parts[1]
                if ($major -ge 3 -and $minor -ge 10) {
                    Write-Ok "Python $ver ($cmd)"
                    $script:PythonCmd = $cmd
                    return
                } else {
                    Write-Warn "Python $ver found, but 3.10+ is required"
                }
            } catch {
                # Not a valid Python
            }
        }
    }

    Write-Warn "Python 3.10+ not found"

    if (Test-CommandExists 'winget') {
        Write-Host "    Install Python 3.12 via winget? [Y/n] " -NoNewline
        $answer = Read-Host
        if ($answer -eq '' -or $answer -match '^[Yy]') {
            Write-Info "Installing Python via winget..."
            winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
            Refresh-Path
            if (Test-CommandExists 'python') {
                $script:PythonCmd = 'python'
                Write-Ok "Python installed"
                return
            }
        }
    }

    Write-Fail "Python 3.10+ is required. Install from https://python.org"
    throw "Python not found"
}

# ── Check ffmpeg ──────────────────────────────────────────────

function Test-Ffmpeg {
    Write-Info "Checking ffmpeg..."

    if ((Test-CommandExists 'ffmpeg') -and (Test-CommandExists 'ffprobe')) {
        Write-Ok "ffmpeg found"
        return
    }

    Write-Warn "ffmpeg not found"

    if (Test-CommandExists 'winget') {
        Write-Host "    Install ffmpeg via winget? [Y/n] " -NoNewline
        $answer = Read-Host
        if ($answer -eq '' -or $answer -match '^[Yy]') {
            Write-Info "Installing ffmpeg via winget..."
            winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
            Refresh-Path
            if (Test-CommandExists 'ffmpeg') {
                Write-Ok "ffmpeg installed"
                return
            }
        }
    }

    if (Test-CommandExists 'choco') {
        Write-Host "    Install ffmpeg via Chocolatey? [Y/n] " -NoNewline
        $answer = Read-Host
        if ($answer -eq '' -or $answer -match '^[Yy]') {
            Write-Info "Installing ffmpeg via Chocolatey..."
            choco install ffmpeg -y
            Refresh-Path
            if (Test-CommandExists 'ffmpeg') {
                Write-Ok "ffmpeg installed"
                return
            }
        }
    }

    Write-Warn "Could not auto-install ffmpeg."
    Write-Host "    Download manually from: https://www.gyan.dev/ffmpeg/builds/"
    Write-Host "    Or install winget/chocolatey and re-run this script."
    Write-Host ""
}

# ── Check yt-dlp ──────────────────────────────────────────────

function Test-YtDlp {
    Write-Info "Checking yt-dlp..."

    try {
        $null = & $script:PythonCmd -m yt_dlp --version 2>$null
        Write-Ok "yt-dlp found"
        return
    } catch {}

    Write-Warn "yt-dlp not found. Installing via pip..."
    & $script:PythonCmd -m pip install --quiet yt-dlp
    Write-Ok "yt-dlp installed"
}

# ── Install scribe ────────────────────────────────────────────

function Install-Scribe {
    Write-Info "Installing scribe..."
    & $script:PythonCmd -m pip install --quiet anyscribecli

    # Verify
    Refresh-Path
    if (Test-CommandExists 'scribe') {
        Write-Ok "scribe installed"
    } else {
        Write-Ok "scribe package installed"
        Fix-Path
    }
}

# ── Fix PATH ──────────────────────────────────────────────────

function Fix-Path {
    Write-Info "Checking PATH..."

    try {
        $scriptsDir = & $script:PythonCmd -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
    } catch {
        Write-Warn "Could not detect Python scripts directory"
        return
    }

    if (-not $scriptsDir) { return }

    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($userPath -and $userPath.Contains($scriptsDir)) {
        Write-Ok "Scripts directory already in PATH"
        return
    }

    Write-Warn "Adding $scriptsDir to your PATH..."
    $newPath = if ($userPath) { "$userPath;$scriptsDir" } else { $scriptsDir }
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    $env:Path = "$env:Path;$scriptsDir"
    Write-Ok "PATH updated (takes effect in new terminals)"
}

# ── Main ──────────────────────────────────────────────────────

$script:PythonCmd = 'python'

Write-Banner

try {
    Test-Python
    Test-Ffmpeg
    Test-YtDlp
    Write-Host ""
    Install-Scribe

    Write-Host ""
    Write-Host "  +-------------------------------------+" -ForegroundColor Green
    Write-Host "  |  scribe is installed!                |" -ForegroundColor Green
    Write-Host "  |                                      |" -ForegroundColor Green
    Write-Host "  |  Next step:                          |" -ForegroundColor Green
    Write-Host "  |    scribe ui                         |" -ForegroundColor Green
    Write-Host "  |                                      |" -ForegroundColor Green
    Write-Host "  |  Opens a dashboard in your browser   |" -ForegroundColor Green
    Write-Host "  |  to set up and start transcribing.   |" -ForegroundColor Green
    Write-Host "  +-------------------------------------+" -ForegroundColor Green
    Write-Host ""

    if (-not (Test-CommandExists 'scribe')) {
        Write-Warn "If 'scribe' is not recognized, use:"
        Write-Host "    $script:PythonCmd -m anyscribecli ui" -ForegroundColor Cyan
        Write-Host ""
    }
} catch {
    Write-Fail "Installation failed: $_"
    Write-Host ""
    Write-Host "  Manual install:" -ForegroundColor Yellow
    Write-Host "    1. Install Python 3.10+ from https://python.org" -ForegroundColor Yellow
    Write-Host "    2. pip install anyscribecli" -ForegroundColor Yellow
    Write-Host "    3. Install ffmpeg from https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
