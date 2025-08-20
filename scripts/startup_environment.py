#!/usr/bin/env python
"""
Startup Environment Manager
Handles environment setup and dependency validation
"""

import sys
import os
import subprocess
import psutil
from datetime import datetime
from typing import List, Tuple, Dict, Any


class StartupEnvironment:
    """Manages environment setup and dependency validation"""
    
    def __init__(self, args):
        self.args = args
        self.environment_data = {}
    
    def setup_environment(self) -> Dict[str, Any]:
        """Setup test environment and return environment data"""
        self._print_header()
        self._record_environment_info()
        self._create_directories()
        self._set_environment_variables()
        self._print_completion()
        return self.environment_data
    
    def _print_header(self):
        """Print startup header"""
        print("\n" + "="*60)
        print("SYSTEM STARTUP TEST RUNNER")
        print("="*60)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test mode: {self.args.mode}")
        print(f"Verbose: {self.args.verbose}")
    
    def _record_environment_info(self):
        """Record environment information"""
        self.environment_data = {
            "python_version": sys.version,
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total / (1024**3),
            "test_mode": self.args.mode
        }
    
    def _create_directories(self):
        """Create required test directories"""
        os.makedirs("reports/system-startup", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
    
    def _set_environment_variables(self):
        """Set test environment variables"""
        os.environ["TESTING"] = "1"
        os.environ["LOG_LEVEL"] = "DEBUG" if self.args.verbose else "INFO"
    
    def _print_completion(self):
        """Print environment setup completion"""
        print("\nEnvironment setup complete")


class DependencyChecker:
    """Handles dependency validation"""
    
    def __init__(self, args):
        self.args = args
    
    def check_all_dependencies(self) -> List[Tuple[str, bool, str]]:
        """Check all required dependencies"""
        checks = self._setup_check_header()
        checks = self._check_python_version(checks)
        checks = self._check_nodejs(checks)
        checks = self._check_npm(checks)
        checks = self._check_redis(checks)
        checks = self._check_postgresql(checks)
        self._validate_and_display_results(checks)
        return checks
    
    def _setup_check_header(self) -> List[Tuple[str, bool, str]]:
        """Setup dependency check header"""
        print("\n" + "-"*40)
        print("Checking Dependencies")
        print("-"*40)
        return []
    
    def _check_python_version(self, checks: List) -> List:
        """Check Python version requirement"""
        python_version = sys.version_info
        passed = python_version >= (3, 8)
        version_str = f"{python_version.major}.{python_version.minor}"
        checks.append(("Python 3.8+", passed, version_str))
        return checks
    
    def _check_nodejs(self, checks: List) -> List:
        """Check Node.js availability"""
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            checks.append(("Node.js", True, result.stdout.strip()))
        except FileNotFoundError:
            checks.append(("Node.js", False, "Not installed"))
        return checks
    
    def _check_npm(self, checks: List) -> List:
        """Check npm availability"""
        try:
            # Use shell=True on Windows to properly resolve npm.cmd
            import platform
            shell_needed = platform.system() == "Windows"
            result = subprocess.run(["npm", "--version"], capture_output=True, text=True, shell=shell_needed)
            if result.returncode == 0:
                checks.append(("npm", True, result.stdout.strip()))
            else:
                checks.append(("npm", False, "Command failed"))
        except (FileNotFoundError, OSError):
            checks.append(("npm", False, "Not installed"))
        return checks
    
    def _check_redis(self, checks: List) -> List:
        """Check Redis availability if not minimal mode"""
        if self.args.mode == "minimal":
            return checks
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
            r.ping()
            checks.append(("Redis", True, "Connected"))
        except:
            checks.append(("Redis", False, "Not available"))
        return checks
    
    def _check_postgresql(self, checks: List) -> List:
        """Check PostgreSQL driver if not minimal mode"""
        if self.args.mode == "minimal":
            return checks
        try:
            import psycopg2
            checks.append(("PostgreSQL driver", True, "Available"))
        except ImportError:
            checks.append(("PostgreSQL driver", False, "Not installed"))
        return checks
    
    def _validate_and_display_results(self, checks: List):
        """Validate and display dependency check results"""
        all_passed = self._display_results(checks)
        self._handle_failures(all_passed)
    
    def _display_results(self, checks: List) -> bool:
        """Display dependency check results"""
        all_passed = True
        for name, passed, version in checks:
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} {name:20} {version}")
            if not passed and name not in ["Redis", "PostgreSQL driver"]:
                all_passed = False
        return all_passed
    
    def _handle_failures(self, all_passed: bool):
        """Handle dependency check failures"""
        if not all_passed:
            print("\n[WARNING] Some required dependencies are missing!")
            if not self.args.force:
                print("Use --force to continue anyway")
                sys.exit(1)
        else:
            print("\n[OK] All dependencies satisfied")


class ProcessManager:
    """Manages process lifecycle during testing"""
    
    def __init__(self):
        self.processes = []
    
    def register_process(self, process):
        """Register a process for lifecycle management"""
        self.processes.append(process)
    
    def cleanup_all(self):
        """Cleanup all registered processes"""
        for process in self.processes:
            self._cleanup_single_process(process)
        self.processes.clear()
    
    def _cleanup_single_process(self, process):
        """Cleanup a single process"""
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
    
    def remove_test_artifacts(self):
        """Remove test database and artifacts"""
        test_db = "test_e2e.db"
        if os.path.exists(test_db):
            os.remove(test_db)
            print(f"Removed test database: {test_db}")