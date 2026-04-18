#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# scribe installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribecli/main/install.sh | bash
#
# Or with options:
#   curl -fsSL ... | bash -s -- --method git --ui
#
# What it does:
#   1. Checks your OS (macOS or Linux)
#   2. Checks for Python 3.10+, installs if missing
#   3. Checks for yt-dlp and ffmpeg, installs if missing
#   4. Installs anyscribecli via pip (with pipx fallback)
#   5. Tells you to run `scribe ui`
# ──────────────────────────────────────────────────────────────

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────
INSTALL_METHOD="pip"       # pip (from PyPI) or git (from GitHub)
REPO_URL="https://github.com/rishmadaan/anyscribecli.git"
RUN_ONBOARD=false
RUN_UI=false
VERBOSE=false
DRY_RUN=false
USED_PIPX=false

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Helpers ───────────────────────────────────────────────────
info()  { echo -e "${BLUE}${BOLD}==>${NC} $1"; }
ok()    { echo -e "${GREEN}${BOLD}  ✓${NC} $1"; }
warn()  { echo -e "${YELLOW}${BOLD}  !${NC} $1"; }
fail()  { echo -e "${RED}${BOLD}  ✗${NC} $1"; }
die()   { fail "$1"; exit 1; }

command_exists() { command -v "$1" &>/dev/null; }

# ── Parse arguments ───────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --method)       INSTALL_METHOD="$2"; shift 2 ;;
        --repo)         REPO_URL="$2"; shift 2 ;;
        --onboard)      RUN_ONBOARD=true; shift ;;
        --ui)           RUN_UI=true; shift ;;
        --verbose)      VERBOSE=true; shift ;;
        --dry-run)      DRY_RUN=true; shift ;;
        --help|-h)
            echo "scribe installer"
            echo ""
            echo "Usage: curl -fsSL <url>/install.sh | bash -s -- [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --method <pip|git>   Install method (default: pip)"
            echo "                       pip: install from PyPI (default)"
            echo "                       git: install from GitHub repository"
            echo "  --repo <url>         GitHub repo URL (for git method)"
            echo "  --onboard            Run the CLI onboarding wizard after install"
            echo "  --ui                 Launch the web UI after install"
            echo "  --verbose            Show detailed output"
            echo "  --dry-run            Show what would be done without doing it"
            echo "  --help               Show this help"
            exit 0
            ;;
        *) die "Unknown option: $1 (use --help for usage)" ;;
    esac
done

# ── Detect OS ─────────────────────────────────────────────────
detect_os() {
    local os
    os="$(uname -s)"
    case "$os" in
        Darwin) echo "macos" ;;
        Linux)  echo "linux" ;;
        *)      die "Unsupported operating system: $os. scribe supports macOS and Linux." ;;
    esac
}

detect_linux_pkg_manager() {
    if command_exists apt; then echo "apt"
    elif command_exists dnf; then echo "dnf"
    elif command_exists pacman; then echo "pacman"
    else echo "unknown"; fi
}

OS="$(detect_os)"
LINUX_PKG=""
if [[ "$OS" == "linux" ]]; then
    LINUX_PKG="$(detect_linux_pkg_manager)"
fi

echo ""
echo -e "${BOLD}  ┌─────────────────────────────────────┐${NC}"
echo -e "${BOLD}  │       scribe installer               │${NC}"
echo -e "${BOLD}  │  Video → Transcript → Markdown       │${NC}"
echo -e "${BOLD}  └─────────────────────────────────────┘${NC}"
echo ""
info "Detected OS: $OS${LINUX_PKG:+ ($LINUX_PKG)}"

# ── Check / install Homebrew (macOS) ──────────────────────────
install_brew_if_needed() {
    if [[ "$OS" == "macos" ]] && ! command_exists brew; then
        warn "Homebrew not found. It's needed to install dependencies."
        echo "    Install from: https://brew.sh"
        read -rp "    Install Homebrew now? [Y/n] " answer </dev/tty
        answer="${answer:-Y}"
        if [[ "$answer" =~ ^[Yy] ]]; then
            info "Installing Homebrew..."
            if [[ "$DRY_RUN" == true ]]; then
                echo "    [dry-run] Would install Homebrew"
            else
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
        else
            die "Cannot continue without a package manager. Install Homebrew from https://brew.sh and try again."
        fi
    fi
}

# ── Generic install helper ────────────────────────────────────
install_package() {
    local name="$1"
    local brew_pkg="$2"
    local apt_pkg="$3"
    local pip_pkg="${4:-}"

    if [[ "$OS" == "macos" ]]; then
        if command_exists brew; then
            info "Installing $name via Homebrew..."
            if [[ "$DRY_RUN" == true ]]; then
                echo "    [dry-run] brew install $brew_pkg"
            else
                brew install "$brew_pkg"
            fi
            return
        fi
    elif [[ "$OS" == "linux" ]]; then
        case "$LINUX_PKG" in
            apt)
                info "Installing $name via apt..."
                if [[ "$DRY_RUN" == true ]]; then
                    echo "    [dry-run] sudo apt install -y $apt_pkg"
                else
                    sudo apt update -qq && sudo apt install -y "$apt_pkg"
                fi
                return
                ;;
            dnf)
                info "Installing $name via dnf..."
                if [[ "$DRY_RUN" == true ]]; then
                    echo "    [dry-run] sudo dnf install -y $apt_pkg"
                else
                    sudo dnf install -y "$apt_pkg"
                fi
                return
                ;;
            pacman)
                info "Installing $name via pacman..."
                if [[ "$DRY_RUN" == true ]]; then
                    echo "    [dry-run] sudo pacman -S --noconfirm $apt_pkg"
                else
                    sudo pacman -S --noconfirm "$apt_pkg"
                fi
                return
                ;;
        esac
    fi

    # Fallback to pip if available
    if [[ -n "$pip_pkg" ]] && command_exists pip3; then
        info "Installing $name via pip..."
        if [[ "$DRY_RUN" == true ]]; then
            echo "    [dry-run] pip3 install $pip_pkg"
        else
            pip3 install "$pip_pkg"
        fi
        return
    fi

    fail "Could not auto-install $name. Please install it manually."
    return 1
}

# ── Check Python ──────────────────────────────────────────────
check_python() {
    info "Checking Python..."

    if command_exists python3; then
        local version
        version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
        local major minor
        major="$(echo "$version" | cut -d. -f1)"
        minor="$(echo "$version" | cut -d. -f2)"

        if [[ "$major" -ge 3 ]] && [[ "$minor" -ge 10 ]]; then
            ok "Python $version"
            return 0
        else
            warn "Python $version found, but 3.10+ is required"
        fi
    else
        warn "Python 3 not found"
    fi

    read -rp "    Install Python? [Y/n] " answer </dev/tty
    answer="${answer:-Y}"
    if [[ "$answer" =~ ^[Yy] ]]; then
        install_package "Python" "python@3.12" "python3" ""
    else
        die "Python 3.10+ is required. Install from https://python.org and try again."
    fi
}

# ── Check yt-dlp ──────────────────────────────────────────────
check_ytdlp() {
    info "Checking yt-dlp..."

    if command_exists yt-dlp; then
        ok "yt-dlp $(yt-dlp --version 2>/dev/null || echo '(version unknown)')"
        return 0
    fi

    warn "yt-dlp not found"
    read -rp "    Install yt-dlp? [Y/n] " answer </dev/tty
    answer="${answer:-Y}"
    if [[ "$answer" =~ ^[Yy] ]]; then
        install_package "yt-dlp" "yt-dlp" "yt-dlp" "yt-dlp"
    else
        die "yt-dlp is required for downloading videos."
    fi
}

# ── Check ffmpeg ──────────────────────────────────────────────
check_ffmpeg() {
    info "Checking ffmpeg..."

    if command_exists ffmpeg && command_exists ffprobe; then
        ok "ffmpeg $(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}' || echo '(version unknown)')"
        return 0
    fi

    warn "ffmpeg not found"
    read -rp "    Install ffmpeg? [Y/n] " answer </dev/tty
    answer="${answer:-Y}"
    if [[ "$answer" =~ ^[Yy] ]]; then
        install_package "ffmpeg" "ffmpeg" "ffmpeg" ""
    else
        die "ffmpeg is required for audio processing."
    fi
}

# ── Install scribe ───────────────────────────────────────────
install_scribe() {
    info "Installing scribe..."

    local pip_cmd="anyscribecli"
    if [[ "$INSTALL_METHOD" == "git" ]]; then
        pip_cmd="git+${REPO_URL}"
    elif [[ "$INSTALL_METHOD" != "pip" ]]; then
        die "Unknown install method: $INSTALL_METHOD (use 'pip' or 'git')"
    fi

    if [[ "$DRY_RUN" == true ]]; then
        echo "    [dry-run] pip3 install $pip_cmd"
    else
        # Try pip first; fall back to pipx if externally-managed-environment
        local pip_output
        if pip_output=$(pip3 install "$pip_cmd" 2>&1); then
            : # Success
        elif echo "$pip_output" | grep -qi "externally-managed"; then
            warn "System Python is externally managed. Using pipx instead..."
            if ! command_exists pipx; then
                info "Installing pipx..."
                case "$LINUX_PKG" in
                    apt)    sudo apt install -y pipx ;;
                    dnf)    sudo dnf install -y pipx ;;
                    pacman) sudo pacman -S --noconfirm python-pipx ;;
                    *)      pip3 install --user pipx ;;
                esac
            fi
            pipx install "$pip_cmd"
            pipx ensurepath 2>/dev/null || true
            USED_PIPX=true
        else
            # Some other pip error
            echo "$pip_output" >&2
            die "pip install failed. See error above."
        fi
    fi

    # Verify
    if command_exists scribe; then
        ok "scribe $(scribe --version 2>/dev/null | awk '{print $2}' || echo 'installed')"
    elif [[ "$USED_PIPX" == true ]]; then
        warn "scribe installed via pipx. Restart your terminal or run: pipx ensurepath"
    else
        warn "scribe installed but not found in PATH."
        echo "    Try adding this to your shell profile:"
        echo ""
        if [[ "$OS" == "macos" ]]; then
            echo "      export PATH=\"\$HOME/Library/Python/3.12/bin:\$PATH\""
        else
            echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
        fi
        echo ""
        echo "    Then restart your terminal and run: scribe --version"
    fi
}

# ── Run post-install action (opt-in) ─────────────────────────
run_post_install() {
    local cmd=""
    if command_exists scribe; then
        cmd="scribe"
    else
        cmd="python3 -m anyscribecli"
    fi

    if [[ "$RUN_UI" == true ]]; then
        echo ""
        info "Launching web UI..."
        echo ""
        if [[ "$DRY_RUN" == true ]]; then
            echo "    [dry-run] $cmd ui"
        else
            $cmd ui
        fi
    elif [[ "$RUN_ONBOARD" == true ]]; then
        echo ""
        info "Starting onboarding wizard..."
        echo ""
        if [[ "$DRY_RUN" == true ]]; then
            echo "    [dry-run] $cmd onboard --skip-deps"
        else
            $cmd onboard --skip-deps
        fi
    fi
}

# ── Main ──────────────────────────────────────────────────────
main() {
    if [[ "$OS" == "macos" ]]; then
        install_brew_if_needed
    fi

    echo ""
    check_python
    check_ytdlp
    check_ffmpeg

    echo ""
    install_scribe

    run_post_install

    echo ""
    if [[ "$RUN_ONBOARD" == true ]] || [[ "$RUN_UI" == true ]]; then
        echo -e "${GREEN}${BOLD}  ┌─────────────────────────────────────┐${NC}"
        echo -e "${GREEN}${BOLD}  │  scribe is ready!                   │${NC}"
        echo -e "${GREEN}${BOLD}  │                                     │${NC}"
        echo -e "${GREEN}${BOLD}  │  scribe ui          web dashboard   │${NC}"
        echo -e "${GREEN}${BOLD}  │  scribe \"<url>\"     transcribe now  │${NC}"
        echo -e "${GREEN}${BOLD}  └─────────────────────────────────────┘${NC}"
    else
        echo -e "${GREEN}${BOLD}  ┌─────────────────────────────────────┐${NC}"
        echo -e "${GREEN}${BOLD}  │  scribe is installed!               │${NC}"
        echo -e "${GREEN}${BOLD}  │                                     │${NC}"
        echo -e "${GREEN}${BOLD}  │  Next step:                         │${NC}"
        echo -e "${GREEN}${BOLD}  │    scribe ui                        │${NC}"
        echo -e "${GREEN}${BOLD}  │                                     │${NC}"
        echo -e "${GREEN}${BOLD}  │  Opens a dashboard in your browser  │${NC}"
        echo -e "${GREEN}${BOLD}  │  to set up and start transcribing.  │${NC}"
        echo -e "${GREEN}${BOLD}  └─────────────────────────────────────┘${NC}"
        if [[ "$USED_PIPX" == true ]]; then
            echo ""
            warn "Installed via pipx — if 'scribe' is not found, restart your terminal"
            echo "    or run: pipx ensurepath"
        fi
    fi
    echo ""
}

main
