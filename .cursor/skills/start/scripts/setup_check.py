"""
X-Wizard setup checker — run by the /start skill automatically.
Detects OS, checks Python version, installs requirements.txt packages.
No manual terminal steps needed from the user.

Usage: python .cursor/skills/start/scripts/setup_check.py
Exit: 0 = success, 1 = Python version too old, 2 = pip install failed
"""

import platform
import subprocess
import sys
from pathlib import Path


MIN_PYTHON = (3, 9)
REQUIREMENTS = Path(__file__).resolve().parents[3] / "requirements.txt"

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check_os() -> str:
    os_name = platform.system()
    if os_name == "Darwin":
        return "Mac"
    elif os_name == "Windows":
        return "Windows"
    return os_name


def check_git() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True, text=True, check=True,
        )
        version = result.stdout.strip().replace("git version ", "")
        return True, version
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "not found"


def check_python() -> tuple[bool, str]:
    version = sys.version_info
    label = f"{version.major}.{version.minor}.{version.micro}"
    ok = version >= MIN_PYTHON
    return ok, label


def install_packages(os_name: str) -> tuple[bool, str]:
    if not REQUIREMENTS.exists():
        return False, f"requirements.txt not found at {REQUIREMENTS}"

    pip_cmd = "pip3" if os_name == "Mac" else "pip"

    packages_to_skip = []
    if os_name == "Mac":
        packages_to_skip = ["pywin32"]

    lines = REQUIREMENTS.read_text().splitlines()
    packages = [
        line.split("#")[0].strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]
    packages = [p for p in packages if p and p not in packages_to_skip]

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + packages,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def main() -> int:
    print()
    print("=" * 52)
    print("  X-Wizard — Setup Check")
    print("=" * 52)

    os_name = check_os()
    print(f"\n  System:  {os_name} ({platform.version()[:40]})")

    git_ok, git_label = check_git()
    if git_ok:
        print(f"  Git:     {GREEN}✓ {git_label}{RESET}")
    else:
        print(f"  Git:     {YELLOW}✗ {git_label} (run bootstrap script to install){RESET}")

    py_ok, py_label = check_python()
    if py_ok:
        print(f"  Python:  {GREEN}✓ {py_label}{RESET}")
    else:
        req = ".".join(str(x) for x in MIN_PYTHON)
        print(f"  Python:  {RED}✗ {py_label} (need ≥ {req}){RESET}")
        print()
        if os_name == "Windows":
            print(f"  {YELLOW}→ Open Microsoft Store → search 'Python 3.13' → Get → Install{RESET}")
        else:
            print(f"  {YELLOW}→ Download from python.org/downloads and run the installer{RESET}")
        print()
        return 1

    print(f"\n  Installing packages from requirements.txt...")
    pkg_ok, msg = install_packages(os_name)
    if pkg_ok:
        print(f"  Packages: {GREEN}✓ All installed{RESET}")
    else:
        print(f"  Packages: {RED}✗ Install failed{RESET}")
        print()
        print(f"  Error details:")
        for line in msg.splitlines()[-10:]:
            print(f"    {line}")
        print()
        pip_cmd = "pip3" if os_name == "Mac" else "pip"
        print(f"  {YELLOW}→ Try running manually: {pip_cmd} install -r requirements.txt{RESET}")
        print()
        return 2

    print()
    print("=" * 52)
    print(f"  {GREEN}All checks passed. X-Wizard is ready.{RESET}")
    print("=" * 52)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
