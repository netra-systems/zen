#!/usr/bin/env python3
"""
Podman Quick Start Script

Automated setup and configuration for using Podman with Netra tests.

Usage:
    python scripts/podman_quick_start.py [--install] [--start] [--test]
"""

import sys
import os
import subprocess
import platform
import argparse
import time
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class PodmanQuickStart:
    """Quick start utility for Podman setup."""
    
    def __init__(self):
        self.os_type = platform.system()
        self.is_windows = self.os_type == "Windows"
        self.is_macos = self.os_type == "Darwin"
        self.is_linux = self.os_type == "Linux"
    
    def run_command(self, cmd: list, check: bool = True) -> Tuple[int, str, str]:
        """Run a command and return result."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                timeout=60
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except FileNotFoundError:
            return 1, "", f"Command not found: {cmd[0]}"
    
    def check_podman_installed(self) -> bool:
        """Check if Podman is installed."""
        returncode, stdout, _ = self.run_command(["podman", "--version"], check=False)
        if returncode == 0:
            print(f"[OK] Podman is installed: {stdout.strip()}")
            return True
        else:
            print("[X] Podman is not installed")
            return False
    
    def check_podman_compose_installed(self) -> bool:
        """Check if podman-compose is installed."""
        returncode, stdout, _ = self.run_command(["podman-compose", "--version"], check=False)
        if returncode == 0:
            print(f"[OK] podman-compose is installed: {stdout.strip()}")
            return True
        else:
            print("[X] podman-compose is not installed")
            return False
    
    def install_podman_compose(self) -> bool:
        """Install podman-compose using pip."""
        print("\nInstalling podman-compose...")
        
        returncode, stdout, stderr = self.run_command([
            sys.executable, "-m", "pip", "install", "podman-compose"
        ])
        
        if returncode == 0:
            print("[OK] podman-compose installed successfully")
            return True
        else:
            print(f"[X] Failed to install podman-compose: {stderr}")
            return False
    
    def check_podman_machine(self) -> Optional[str]:
        """Check Podman machine status (Windows/macOS only)."""
        if self.is_linux:
            return "running"  # No machine needed on Linux
        
        returncode, stdout, _ = self.run_command(["podman", "machine", "list", "--format", "json"], check=False)
        
        if returncode != 0:
            return None
        
        try:
            import json
            machines = json.loads(stdout)
            
            if not machines:
                return None
            
            # Find default or first machine
            for machine in machines:
                if machine.get("Running", False):
                    return "running"
                elif machine.get("Name"):
                    return "stopped"
            
            return "stopped" if machines else None
            
        except:
            return None
    
    def init_podman_machine(self) -> bool:
        """Initialize Podman machine (Windows/macOS)."""
        if self.is_linux:
            return True
        
        print("\nInitializing Podman machine...")
        
        # Set appropriate resources based on platform
        cpus = "4"
        memory = "8192"  # 8GB
        
        returncode, stdout, stderr = self.run_command([
            "podman", "machine", "init",
            "--cpus", cpus,
            "--memory", memory,
            "--disk-size", "100"  # 100GB disk
        ], check=False)
        
        if returncode == 0 or "already exists" in stderr:
            print("[OK] Podman machine initialized")
            return True
        else:
            print(f"[X] Failed to initialize machine: {stderr}")
            return False
    
    def start_podman_machine(self) -> bool:
        """Start Podman machine (Windows/macOS)."""
        if self.is_linux:
            return True
        
        print("\nStarting Podman machine...")
        
        returncode, stdout, stderr = self.run_command([
            "podman", "machine", "start"
        ], check=False)
        
        if returncode == 0 or "already running" in stderr:
            print("[OK] Podman machine started")
            
            # Wait for machine to be ready
            print("Waiting for machine to be ready...")
            time.sleep(5)
            
            # Verify connection
            returncode, _, _ = self.run_command(["podman", "info"], check=False)
            if returncode == 0:
                print("[OK] Podman machine is ready")
                return True
            else:
                print("[X] Podman machine started but not responding")
                return False
        else:
            print(f"[X] Failed to start machine: {stderr}")
            return False
    
    def create_env_file(self) -> bool:
        """Create or update .env file with Podman settings."""
        env_file = Path(__file__).parent.parent / ".env"
        
        # Read existing env file if it exists
        existing_lines = []
        podman_configured = False
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith("CONTAINER_RUNTIME="):
                        existing_lines.append("CONTAINER_RUNTIME=podman\n")
                        podman_configured = True
                    else:
                        existing_lines.append(line)
        
        # Add Podman configuration if not present
        if not podman_configured:
            existing_lines.append("\n# Container Runtime Configuration\n")
            existing_lines.append("CONTAINER_RUNTIME=podman\n")
            existing_lines.append("PODMAN_ROOTLESS=true\n")
            existing_lines.append("PODMAN_USE_PODS=true\n")
        
        # Write back
        with open(env_file, 'w') as f:
            f.writelines(existing_lines)
        
        print(f"[OK] Updated .env file: {env_file}")
        return True
    
    def run_test_container(self) -> bool:
        """Run a test container to verify setup."""
        print("\nTesting Podman with a simple container...")
        
        container_name = "podman-test-hello"
        
        # Remove if exists
        self.run_command(["podman", "rm", "-f", container_name], check=False)
        
        # Run hello-world container
        returncode, stdout, stderr = self.run_command([
            "podman", "run", "--name", container_name,
            "docker.io/library/hello-world"
        ])
        
        if returncode == 0:
            print("[OK] Test container ran successfully")
            
            # Clean up
            self.run_command(["podman", "rm", container_name], check=False)
            return True
        else:
            print(f"[X] Test container failed: {stderr}")
            return False
    
    def print_next_steps(self):
        """Print next steps for the user."""
        print("\n" + "="*60)
        print("Next Steps")
        print("="*60)
        print("""
1. Run tests with Podman:
   python tests/unified_test_runner.py --real-services

2. Start services manually:
   podman-compose up -d

3. View running containers:
   podman ps

4. Stop services:
   podman-compose down

5. For more information:
   See docs/PODMAN_TESTING_GUIDE.md
""")
    
    def run_setup(self, install: bool = False, start: bool = False, test: bool = False) -> bool:
        """Run the setup process."""
        print("="*60)
        print("Podman Quick Start")
        print("="*60)
        print(f"Platform: {self.os_type}")
        print()
        
        success = True
        
        # Check if Podman is installed
        if not self.check_podman_installed():
            if self.is_windows:
                print("\nPlease install Podman Desktop from:")
                print("https://podman-desktop.io/downloads")
            elif self.is_macos:
                print("\nInstall Podman with: brew install podman")
            else:
                print("\nInstall Podman with your package manager:")
                print("  Ubuntu/Debian: sudo apt-get install podman")
                print("  Fedora/RHEL: sudo dnf install podman")
            return False
        
        # Check/install podman-compose
        if not self.check_podman_compose_installed():
            if install:
                success &= self.install_podman_compose()
            else:
                print("\nRun with --install to install podman-compose")
                success = False
        
        # Check/start Podman machine (Windows/macOS)
        if not self.is_linux:
            machine_status = self.check_podman_machine()
            
            if machine_status is None:
                print("\n[X] No Podman machine found")
                if start:
                    success &= self.init_podman_machine()
                    success &= self.start_podman_machine()
                else:
                    print("Run with --start to initialize Podman machine")
                    success = False
            elif machine_status == "stopped":
                print("\n[X] Podman machine is stopped")
                if start:
                    success &= self.start_podman_machine()
                else:
                    print("Run with --start to start Podman machine")
                    success = False
            else:
                print("[OK] Podman machine is running")
        
        # Create/update .env file
        if success:
            success &= self.create_env_file()
        
        # Run test container
        if success and test:
            success &= self.run_test_container()
        
        # Print summary
        if success:
            print("\n[OK] Podman is ready for use!")
            self.print_next_steps()
        else:
            print("\n[X] Setup incomplete. Please address the issues above.")
        
        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Podman quick start and setup utility"
    )
    parser.add_argument(
        "--install", "-i",
        action="store_true",
        help="Install missing components (podman-compose)"
    )
    parser.add_argument(
        "--start", "-s",
        action="store_true",
        help="Start Podman machine if needed"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Run test container to verify setup"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all setup steps (install, start, test)"
    )
    
    args = parser.parse_args()
    
    # If --all, enable everything
    if args.all:
        args.install = True
        args.start = True
        args.test = True
    
    # Run setup
    quickstart = PodmanQuickStart()
    success = quickstart.run_setup(
        install=args.install,
        start=args.start,
        test=args.test
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()