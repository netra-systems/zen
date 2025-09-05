#!/usr/bin/env python3
"""
Test Podman Setup and Functionality

This script validates that Podman is properly configured and can run
the Netra test infrastructure.

Usage:
    python scripts/test_podman_setup.py [--verbose]
"""

import sys
import os
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_framework.container_runtime import (
    detect_container_runtime,
    ContainerRuntime,
    is_podman,
    get_runtime_type
)
from test_framework.unified_container_manager import (
    UnifiedContainerManager,
    ContainerManagerMode
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PodmanTestSuite:
    """Test suite for validating Podman functionality."""
    
    def __init__(self, verbose: bool = False):
        """Initialize test suite."""
        self.verbose = verbose
        self.test_results: List[Tuple[str, bool, str]] = []
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "✓" if passed else "✗"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"
        
        print(f"{color}[{status}]{reset} {test_name}")
        if message and (not passed or self.verbose):
            print(f"    {message}")
        
        self.test_results.append((test_name, passed, message))
    
    def test_podman_installation(self) -> bool:
        """Test if Podman is installed and accessible."""
        try:
            runtime_info = detect_container_runtime()
            
            if runtime_info.runtime == ContainerRuntime.PODMAN:
                self.log_result(
                    "Podman Installation",
                    True,
                    f"Podman {runtime_info.version} detected"
                )
                return True
            elif runtime_info.runtime == ContainerRuntime.DOCKER:
                self.log_result(
                    "Podman Installation",
                    False,
                    "Docker detected but Podman not found. Please install Podman Desktop."
                )
                return False
            else:
                self.log_result(
                    "Podman Installation",
                    False,
                    "No container runtime detected"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Podman Installation",
                False,
                f"Error detecting runtime: {e}"
            )
            return False
    
    def test_podman_compose(self) -> bool:
        """Test if podman-compose is available."""
        try:
            import subprocess
            result = subprocess.run(
                ["podman-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.log_result(
                    "Podman Compose",
                    True,
                    f"podman-compose available: {version}"
                )
                return True
            else:
                self.log_result(
                    "Podman Compose",
                    False,
                    "podman-compose not found. Install with: pip install podman-compose"
                )
                return False
                
        except FileNotFoundError:
            self.log_result(
                "Podman Compose",
                False,
                "podman-compose not installed. Install with: pip install podman-compose"
            )
            return False
        except Exception as e:
            self.log_result(
                "Podman Compose",
                False,
                f"Error checking podman-compose: {e}"
            )
            return False
    
    def test_podman_machine_status(self) -> bool:
        """Test if Podman machine is running (Windows/macOS)."""
        import platform
        
        # Only needed on Windows and macOS
        if platform.system() == "Linux":
            self.log_result(
                "Podman Machine",
                True,
                "Not required on Linux"
            )
            return True
        
        try:
            import subprocess
            result = subprocess.run(
                ["podman", "machine", "list", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                import json
                machines = json.loads(result.stdout)
                
                if not machines:
                    self.log_result(
                        "Podman Machine",
                        False,
                        "No Podman machine found. Run: podman machine init && podman machine start"
                    )
                    return False
                
                # Check if any machine is running
                running = any(m.get("Running", False) for m in machines)
                if running:
                    self.log_result(
                        "Podman Machine",
                        True,
                        "Podman machine is running"
                    )
                    return True
                else:
                    self.log_result(
                        "Podman Machine",
                        False,
                        "Podman machine exists but not running. Run: podman machine start"
                    )
                    return False
            else:
                self.log_result(
                    "Podman Machine",
                    False,
                    f"Failed to check machine status: {result.stderr}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Podman Machine",
                False,
                f"Error checking Podman machine: {e}"
            )
            return False
    
    def test_compose_file_exists(self) -> bool:
        """Test if podman-compose.yml exists."""
        compose_file = Path(__file__).parent.parent / "podman-compose.yml"
        
        if compose_file.exists():
            self.log_result(
                "Compose File",
                True,
                f"Found: {compose_file}"
            )
            return True
        else:
            self.log_result(
                "Compose File",
                False,
                f"Not found: {compose_file}"
            )
            return False
    
    async def test_container_manager_init(self) -> bool:
        """Test if UnifiedContainerManager can initialize with Podman."""
        try:
            manager = UnifiedContainerManager(
                environment="test",
                mode=ContainerManagerMode.PODMAN,
                use_alpine=True
            )
            
            runtime_info = manager.get_runtime_info()
            
            if runtime_info["runtime"] == "podman":
                self.log_result(
                    "Container Manager",
                    True,
                    f"Initialized with Podman {runtime_info['version']}"
                )
                return True
            else:
                self.log_result(
                    "Container Manager",
                    False,
                    f"Unexpected runtime: {runtime_info['runtime']}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Container Manager",
                False,
                f"Failed to initialize: {e}"
            )
            return False
    
    async def test_basic_container_operations(self) -> bool:
        """Test basic container operations with a simple Redis container."""
        try:
            import subprocess
            import time
            
            container_name = "podman-test-redis"
            
            # Clean up any existing container
            subprocess.run(
                ["podman", "rm", "-f", container_name],
                capture_output=True,
                timeout=10
            )
            
            # Start Redis container
            result = subprocess.run(
                [
                    "podman", "run", "-d",
                    "--name", container_name,
                    "-p", "6379:6379",
                    "docker.io/redis:7-alpine"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.log_result(
                    "Container Operations",
                    False,
                    f"Failed to start container: {result.stderr}"
                )
                return False
            
            # Wait for container to be ready
            time.sleep(3)
            
            # Check if container is running
            ps_result = subprocess.run(
                ["podman", "ps", "--filter", f"name={container_name}", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if ps_result.returncode == 0:
                import json
                containers = json.loads(ps_result.stdout)
                if containers:
                    # Clean up
                    subprocess.run(
                        ["podman", "rm", "-f", container_name],
                        capture_output=True,
                        timeout=10
                    )
                    
                    self.log_result(
                        "Container Operations",
                        True,
                        "Successfully started and stopped test container"
                    )
                    return True
            
            self.log_result(
                "Container Operations",
                False,
                "Container not found after starting"
            )
            return False
            
        except Exception as e:
            self.log_result(
                "Container Operations",
                False,
                f"Error during container operations: {e}"
            )
            
            # Clean up
            try:
                subprocess.run(
                    ["podman", "rm", "-f", container_name],
                    capture_output=True,
                    timeout=10
                )
            except:
                pass
            
            return False
    
    def test_rootless_mode(self) -> bool:
        """Test if Podman is running in rootless mode."""
        try:
            import subprocess
            import json
            
            result = subprocess.run(
                ["podman", "info", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                is_rootless = info.get("host", {}).get("rootless", False)
                
                self.log_result(
                    "Rootless Mode",
                    True,
                    f"Rootless: {is_rootless} (recommended: True)"
                )
                return True
            else:
                self.log_result(
                    "Rootless Mode",
                    False,
                    "Failed to get Podman info"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Rootless Mode",
                False,
                f"Error checking rootless mode: {e}"
            )
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all tests in sequence."""
        print("\n" + "="*60)
        print("Podman Setup Validation")
        print("="*60 + "\n")
        
        # Run tests
        tests_passed = True
        
        # Basic installation tests
        tests_passed &= self.test_podman_installation()
        
        # Only continue if Podman is installed
        if is_podman():
            tests_passed &= self.test_podman_compose()
            tests_passed &= self.test_podman_machine_status()
            tests_passed &= self.test_compose_file_exists()
            tests_passed &= await self.test_container_manager_init()
            tests_passed &= await self.test_basic_container_operations()
            tests_passed &= self.test_rootless_mode()
        
        # Print summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        
        passed = sum(1 for _, p, _ in self.test_results if p)
        failed = sum(1 for _, p, _ in self.test_results if not p)
        
        print(f"\nTotal: {len(self.test_results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if tests_passed:
            print("\n✓ All tests passed! Podman is ready for use.")
        else:
            print("\n✗ Some tests failed. Please address the issues above.")
            print("\nFor detailed setup instructions, see: docs/PODMAN_TESTING_GUIDE.md")
        
        return tests_passed


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Podman setup and functionality"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Run test suite
    suite = PodmanTestSuite(verbose=args.verbose)
    success = await suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())