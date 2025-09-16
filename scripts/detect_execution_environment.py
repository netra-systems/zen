#!/usr/bin/env python3
"""
Detect execution environment and adapt test execution accordingly.

This module provides environment detection for Issue #1176 remediation,
ensuring test execution works across different environments including Claude Code.
"""

import subprocess
import sys
import os
import platform
from typing import Optional, Dict, List

class ExecutionEnvironment:
    """Detect and adapt to different execution environments."""

    def __init__(self):
        self.environment_info = self._gather_environment_info()

    def _gather_environment_info(self) -> Dict[str, any]:
        """Gather comprehensive environment information."""
        return {
            'platform': platform.system(),
            'python_version': sys.version,
            'python_executable': sys.executable,
            'environment_variables': dict(os.environ),
            'working_directory': os.getcwd(),
        }

    def detect_claude_code_environment(self) -> bool:
        """Detect if running in Claude Code environment with restrictions."""
        # Check for Claude Code specific environment indicators
        claude_indicators = [
            os.environ.get('CLAUDE_CODE_SESSION'),
            os.environ.get('ANTHROPIC_ENV'),
            'claude' in str(sys.executable).lower(),
            'anthropic' in str(sys.executable).lower(),
        ]

        # Check process information for Claude Code context
        try:
            import psutil
            current_process = psutil.Process()
            parent_processes = []
            process = current_process
            while process.parent():
                process = process.parent()
                parent_processes.append(process.name().lower())

            process_indicators = any(
                'claude' in name or 'anthropic' in name
                for name in parent_processes
            )
            claude_indicators.append(process_indicators)
        except ImportError:
            pass  # psutil not available, skip process checking

        detected = any(claude_indicators)
        if detected:
            print(f"Claude Code environment detected based on: {[i for i in claude_indicators if i]}")

        return detected

    def get_compatible_python_executable(self) -> str:
        """Get Python executable compatible with current environment."""
        # In Claude Code, prefer python3 due to command restrictions
        if self.detect_claude_code_environment():
            print("Adapting for Claude Code environment...")
            candidates = ['python3', 'python']
        else:
            # In other environments, prefer sys.executable
            candidates = [sys.executable, 'python3', 'python']

        for candidate in candidates:
            if self._test_python_executable(candidate):
                print(f"Selected Python executable: {candidate}")
                return candidate

        # Last resort fallback
        print(f"Warning: No tested Python executable found, using sys.executable: {sys.executable}")
        return sys.executable

    def _test_python_executable(self, executable: str) -> bool:
        """Test if a Python executable is available and working."""
        try:
            result = subprocess.run(
                [executable, '--version'],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                print(f"Tested {executable}: {result.stdout.strip()}")
                return True
            else:
                print(f"Testing {executable} failed with return code: {result.returncode}")
                return False
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f"Testing {executable} failed: {e}")
            return False

    def get_environment_report(self) -> str:
        """Generate comprehensive environment report."""
        report_lines = [
            "EXECUTION ENVIRONMENT REPORT",
            "=" * 50,
            f"Platform: {self.environment_info['platform']}",
            f"Python Version: {self.environment_info['python_version']}",
            f"Python Executable: {self.environment_info['python_executable']}",
            f"Working Directory: {self.environment_info['working_directory']}",
            f"Claude Code Environment: {self.detect_claude_code_environment()}",
            f"Compatible Python: {self.get_compatible_python_executable()}",
            "",
            "Environment Variables:",
        ]

        # Add relevant environment variables
        relevant_vars = [
            'CLAUDE_CODE_SESSION', 'ANTHROPIC_ENV', 'PYTHON_PATH', 'PYTHONPATH',
            'PATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV'
        ]

        for var in relevant_vars:
            value = self.environment_info['environment_variables'].get(var)
            if value:
                report_lines.append(f"  {var}: {value}")

        return "\n".join(report_lines)

def get_compatible_python_executable() -> str:
    """Convenience function to get compatible Python executable."""
    env = ExecutionEnvironment()
    return env.get_compatible_python_executable()

def main():
    """Main function for CLI usage."""
    env = ExecutionEnvironment()
    print(env.get_environment_report())

    # Test the selected Python executable
    python_cmd = env.get_compatible_python_executable()
    print(f"\nTesting selected Python executable: {python_cmd}")

    try:
        result = subprocess.run([python_cmd, '-c', 'import sys; print(f"Python {sys.version} working correctly")'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✓ Success: {result.stdout.strip()}")
        else:
            print(f"✗ Failed: {result.stderr}")
    except Exception as e:
        print(f"✗ Test failed: {e}")

if __name__ == "__main__":
    main()