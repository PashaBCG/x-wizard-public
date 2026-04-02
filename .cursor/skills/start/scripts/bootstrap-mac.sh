#!/bin/bash
# X-Wizard — macOS prerequisite bootstrap
# Detects and installs Git and Python3 with cascading fallbacks.
# Run: bash .cursor/skills/start/scripts/bootstrap-mac.sh
# Exit: 0 = all prerequisites present, 1 = something still missing

set -euo pipefail

GREEN="\033[92m"
RED="\033[91m"
YELLOW="\033[93m"
CYAN="\033[96m"
RESET="\033[0m"

INSTALLED_SOMETHING=0

status()  { printf "  ${CYAN}[CHECK]${RESET}   %s\n" "$1"; }
ok()      { printf "  ${GREEN}[OK]${RESET}      %s\n" "$1"; }
install() { printf "  ${YELLOW}[INSTALL]${RESET} %s\n" "$1"; }
fail()    { printf "  ${RED}[FAIL]${RESET}    %s\n" "$1"; }

# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------
install_git() {
    # Method 1: Xcode Command Line Tools (preferred — also installs Python3)
    install "Git via Xcode Command Line Tools ..."
    if xcode-select --install 2>/dev/null; then
        echo ""
        echo "  A macOS popup should appear asking to install Command Line Tools."
        echo "  Click 'Install' and wait for it to finish (~2 min)."
        echo "  Press Enter here once the installation is complete."
        read -r
        if command -v git &>/dev/null; then
            INSTALLED_SOMETHING=1
            return 0
        fi
    fi

    # Method 2: Homebrew (if already present)
    if command -v brew &>/dev/null; then
        install "Git via Homebrew ..."
        if brew install git 2>/dev/null; then
            INSTALLED_SOMETHING=1
            return 0
        fi
    fi

    # Method 3: Install Homebrew first, then Git
    install "Homebrew + Git (last resort) ..."
    if /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; then
        # Homebrew may need PATH setup on Apple Silicon
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        if brew install git 2>/dev/null; then
            INSTALLED_SOMETHING=1
            return 0
        fi
    fi

    return 1
}

check_git() {
    status "Git ..."
    if command -v git &>/dev/null; then
        ok "Git $(git --version | awk '{print $3}')"
        return 0
    fi

    if install_git && command -v git &>/dev/null; then
        ok "Git $(git --version | awk '{print $3}')"
        return 0
    fi

    fail "Could not install Git automatically."
    echo "  → Download from https://git-scm.com/download/mac"
    return 1
}

# ---------------------------------------------------------------------------
# Python 3
# ---------------------------------------------------------------------------
install_python() {
    # Method 1: Xcode CLT may have already installed python3 (from Git step).
    #           If not, trigger CLT install again.
    if ! xcode-select -p &>/dev/null; then
        install "Python3 via Xcode Command Line Tools ..."
        xcode-select --install 2>/dev/null || true
        echo "  Click 'Install' in the popup if it appears. Press Enter when done."
        read -r
        if command -v python3 &>/dev/null; then
            INSTALLED_SOMETHING=1
            return 0
        fi
    fi

    # Method 2: Homebrew
    if command -v brew &>/dev/null; then
        install "Python3 via Homebrew ..."
        if brew install python 2>/dev/null; then
            INSTALLED_SOMETHING=1
            return 0
        fi
    fi

    return 1
}

check_python() {
    status "Python3 ..."
    if command -v python3 &>/dev/null; then
        local ver
        ver=$(python3 --version 2>&1 | awk '{print $2}')
        ok "Python $ver"
        return 0
    fi

    if install_python && command -v python3 &>/dev/null; then
        local ver
        ver=$(python3 --version 2>&1 | awk '{print $2}')
        ok "Python $ver"
        return 0
    fi

    fail "Could not install Python3 automatically."
    echo "  → Download from https://www.python.org/downloads/"
    return 1
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo ""
    echo "======================================================"
    echo "  X-Wizard — Prerequisites Bootstrap (macOS)"
    echo "======================================================"
    echo ""

    local git_ok=0
    local py_ok=0

    check_git  && git_ok=1
    check_python && py_ok=1

    echo ""

    if [[ $git_ok -eq 0 || $py_ok -eq 0 ]]; then
        echo "======================================================"
        printf "  ${RED}Some prerequisites could not be installed.${RESET}\n"
        echo "  Install them manually, restart Cursor, and re-run /start."
        echo "======================================================"
        echo ""
        return 1
    fi

    if [[ $INSTALLED_SOMETHING -eq 1 ]]; then
        echo "======================================================"
        printf "  ${GREEN}Prerequisites installed successfully.${RESET}\n"
        echo "  RESTART CURSOR now, then type /start again."
        echo "======================================================"
    else
        echo "======================================================"
        printf "  ${GREEN}All prerequisites already present.${RESET}\n"
        echo "======================================================"
    fi
    echo ""
    return 0
}

main
