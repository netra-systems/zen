from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Netra AI Platform - Quick Start Development Script
Python equivalent of start_dev.bat

This script starts both backend and frontend with optimal settings,
handling virtual environment activation and proper error handling.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


# Colors for terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'


def print_colored(message: str, color: str = Colors.ENDC):
    """Print colored output to terminal."""
    print(f"{color}{message}{Colors.ENDC}")


def run_command(cmd: List[str], check: bool = True, capture_output: bool = False, 
                env: Optional[dict] = None, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        # Merge environment variables
        final_env = os.environ.copy()
        if env:
            final_env.update(env)
            
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            env=final_env,
            cwd=cwd
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e


def check_virtual_environment() -> bool:
    """Check if virtual environment exists."""
    venv_path = Path("venv")
    
    if sys.platform == "win32":
        activate_script = venv_path / "Scripts" / "activate.bat"
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        activate_script = venv_path / "bin" / "activate"
        python_exe = venv_path / "bin" / "python"
    
    return venv_path.exists() and activate_script.exists() and python_exe.exists()


def get_venv_python() -> str:
    """Get the path to the virtual environment Python executable."""
    if sys.platform == "win32":
        return str(Path("venv") / "Scripts" / "python.exe")
    else:
        return str(Path("venv") / "bin" / "python")


def start_development_environment(dynamic: bool = True, no_backend_reload: bool = True, 
                                load_secrets: bool = True, extra_args: List[str] = None) -> int:
    """Start the development environment with dev_launcher.py."""
    if extra_args is None:
        extra_args = []
    
    print_colored("Starting Backend and Frontend servers...", Colors.CYAN)
    print_colored("  - Dynamic port allocation (avoids conflicts)", Colors.YELLOW)
    print_colored("  - No backend reload (30-50% faster)", Colors.YELLOW)
    print_colored("  - Automatic secret loading", Colors.YELLOW)
    print("")
    
    # Get the virtual environment Python
    python_cmd = get_venv_python()
    
    # Build command
    cmd = [python_cmd, "scripts/dev_launcher.py"]
    
    if dynamic:
        cmd.append("--dynamic")
    if no_backend_reload:
        cmd.append("--no-backend-reload")
    if load_secrets:
        cmd.append("--load-secrets")
    
    # Add any extra arguments
    cmd.extend(extra_args)
    
    try:
        result = run_command(cmd, check=False)
        return result.returncode
    except Exception as e:
        print("")
        print_colored("ERROR: Failed to start development environment", Colors.RED)
        print_colored(f"Error details: {e}", Colors.RED)
        print_colored("Please check the error messages above", Colors.RED)
        print("")
        return 1


def main():
    """Main function to start the development environment."""
    parser = argparse.ArgumentParser(
        description="Netra AI Platform - Quick Start Development Script"
    )
    
    parser.add_argument(
        "--no-dynamic",
        action="store_true",
        help="Disable dynamic port allocation"
    )
    
    parser.add_argument(
        "--enable-backend-reload",
        action="store_true",
        help="Enable backend reload (slower but useful for debugging)"
    )
    
    parser.add_argument(
        "--no-load-secrets",
        action="store_true",
        help="Don't automatically load secrets"
    )
    
    # Parse known args and capture unknown ones
    args, unknown_args = parser.parse_known_args()
    
    print("")
    print_colored("=" * 47, Colors.BLUE)
    print_colored("    Netra AI Development Environment", Colors.BLUE)
    print_colored("=" * 47, Colors.BLUE)
    print("")
    
    # Change to project root directory (script directory)
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if virtual environment exists
    if not check_virtual_environment():
        print_colored("ERROR: Virtual environment not found!", Colors.RED)
        print_colored("Please run: python scripts/setup.py", Colors.YELLOW)
        print("")
        return 1
    
    # Activate virtual environment message
    print_colored("Activating virtual environment...", Colors.CYAN)
    
    # Start the development environment
    exit_code = start_development_environment(
        dynamic=not args.no_dynamic,
        no_backend_reload=not args.enable_backend_reload,
        load_secrets=not args.no_load_secrets,
        extra_args=unknown_args
    )
    
    if exit_code != 0:
        print("")
        print_colored("ERROR: Failed to start development environment", Colors.RED)
        print_colored("Please check the error messages above", Colors.RED)
        print("")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
