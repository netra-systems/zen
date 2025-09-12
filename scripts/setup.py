#!/usr/bin/env python3
"""
Netra AI Platform - Quick Setup
One-command setup for developers
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Quick setup entry point"""
    _show_setup_banner()
    if not _confirm_setup():
        return
    _validate_installer_exists()
    _execute_installer()

def _show_setup_banner():
    """Display setup banner and requirements."""
    print("\n[U+1F680] Netra AI Platform - Quick Setup\n")
    print("This will install and configure your development environment.")
    print("Please ensure you have Python 3.9+ and Node.js 18+ installed.\n")

def _confirm_setup() -> bool:
    """Confirm user wants to proceed with setup."""
    response = input("Continue with setup? (y/n): ")
    if response.lower() != 'y':
        print("Setup cancelled.")
        return False
    return True

def _validate_installer_exists():
    """Validate that the installer script exists."""
    installer_path = Path(__file__).parent / "install_dev_env.py"
    if not installer_path.exists():
        _print_installer_error()
        sys.exit(1)

def _print_installer_error():
    """Print installer not found error."""
    print("Error: install_dev_env.py not found!")
    print("Please ensure you're running this from the project root directory.")

def _execute_installer():
    """Execute the installer script."""
    installer_path = Path(__file__).parent / "install_dev_env.py"
    try:
        subprocess.run([sys.executable, str(installer_path)], check=True)
    except subprocess.CalledProcessError:
        _print_setup_error()
        sys.exit(1)
    except KeyboardInterrupt:
        _print_interrupted_error()
        sys.exit(1)

def _print_setup_error():
    """Print setup error message."""
    print("\n WARNING: [U+FE0F]  Setup encountered some issues.")
    print("Please check the output above and resolve any errors.")

def _print_interrupted_error():
    """Print setup interrupted message."""
    print("\n WARNING: [U+FE0F]  Setup interrupted.")

if __name__ == "__main__":
    main()