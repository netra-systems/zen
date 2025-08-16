#!/usr/bin/env python3
"""
Command execution utilities for code review system.
Handles shell commands with timeout and error handling.
"""

import subprocess
from typing import Tuple
from pathlib import Path

from .core import ReviewConfig


class CommandRunner:
    """Executes shell commands for review operations"""
    
    def __init__(self, config: ReviewConfig):
        self.config = config
        self.project_root = config.project_root
    
    def run(self, cmd: str, cwd: str = None, timeout: int = None) -> Tuple[bool, str]:
        """Run a shell command and return success status and output"""
        actual_timeout = timeout or self.config.timeout_default
        actual_cwd = cwd or self.project_root
        try:
            result = self._execute_command(cmd, actual_cwd, actual_timeout)
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {actual_timeout} seconds"
        except Exception as e:
            return False, str(e)
    
    def _execute_command(self, cmd: str, cwd: Path, timeout: int):
        """Execute the subprocess command"""
        return subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=cwd, timeout=timeout
        )
    
    def run_with_extended_timeout(self, cmd: str, cwd: str = None) -> Tuple[bool, str]:
        """Run command with extended timeout"""
        return self.run(cmd, cwd, self.config.timeout_extended)
    
    def check_file_exists(self, file_path: str) -> bool:
        """Check if a file exists relative to project root"""
        full_path = self.project_root / file_path
        return full_path.exists()
    
    def check_directory_exists(self, dir_path: str) -> bool:
        """Check if a directory exists relative to project root"""
        full_path = self.project_root / dir_path
        return full_path.exists() and full_path.is_dir()
    
    def get_file_size(self, file_path: str) -> str:
        """Get file size using du command"""
        success, output = self.run(f"du -sh {file_path}")
        if success and output:
            return output.split()[0]
        return "unknown"
    
    def grep_search(self, pattern: str, path: str, include_filter: str = None,
                   max_results: int = 10) -> Tuple[bool, str]:
        """Run grep search with optional filters"""
        cmd = f"grep -r"
        if include_filter:
            cmd += f" --include='{include_filter}'"
        cmd += f" '{pattern}' {path}"
        if max_results:
            cmd += f" | head -{max_results}"
        return self.run(cmd)