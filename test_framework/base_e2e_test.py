"""
Base E2E Test Framework

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide base E2E test functionality for dev launcher testing
- Value Impact: Enables comprehensive end-to-end testing without import errors
- Strategic Impact: Foundation for critical system integration validation

This base class provides:
- Common E2E test setup and teardown
- Process management utilities
- Service health checking
- Cross-platform compatibility helpers
"""

import asyncio
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from shared.isolated_environment import get_env


class BaseE2ETest:
    """Base class for end-to-end tests."""
    
    def setup_method(self):
        """Set up method called before each test method."""
        self.setup_logging()
        self.cleanup_tasks: List[callable] = []
        self.test_processes: List[subprocess.Popen] = []
        self.start_time = time.time()
    
    async def initialize_test_environment(self):
        """Initialize the test environment with minimal setup.
        
        For E2E tests that don't need real services, this provides basic setup.
        Tests requiring real services should override this method.
        """
        self.logger.info("Initializing minimal E2E test environment")
        
        # Basic environment setup without database connections
        # This allows tests to run in 'test' environment without external dependencies
        test_env = {
            "NETRA_TEST_MODE": "true",
            "NETRA_STARTUP_MODE": "minimal", 
            "NETRA_SKIP_SECRETS": "true",
            "ENVIRONMENT": "test"
        }
        
        # Update environment variables for this test
        for key, value in test_env.items():
            os.environ[key] = value
            
        self.logger.info("Minimal E2E test environment initialized")
    
    def teardown_method(self):
        """Tear down method called after each test method."""
        asyncio.run(self.cleanup_resources())
    
    def setup_logging(self):
        """Set up logging for E2E tests."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def cleanup_resources(self):
        """Clean up all resources after test."""
        self.logger.info("Starting E2E test cleanup")
        
        # Terminate all test processes
        for process in self.test_processes:
            await self._terminate_process_safely(process)
        
        # Run all cleanup tasks
        for cleanup_task in self.cleanup_tasks:
            try:
                if asyncio.iscoroutinefunction(cleanup_task):
                    await cleanup_task()
                else:
                    cleanup_task()
            except Exception as e:
                self.logger.error(f"Cleanup task failed: {e}")
        
        self.logger.info("E2E test cleanup completed")
    
    async def _terminate_process_safely(self, process: subprocess.Popen):
        """Terminate a process safely across platforms."""
        if not process or process.poll() is not None:
            return
        
        try:
            if sys.platform == "win32":
                # Windows: use taskkill for process tree termination
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    capture_output=True,
                    text=True
                )
            else:
                # Unix: send SIGTERM to process group
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass  # Process already terminated
            
            # Wait for termination
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                
        except Exception as e:
            self.logger.error(f"Error terminating process {process.pid}: {e}")
    
    def register_process(self, process: subprocess.Popen):
        """Register a process for cleanup."""
        self.test_processes.append(process)
    
    def register_cleanup_task(self, cleanup_task: callable):
        """Register a cleanup task."""
        self.cleanup_tasks.append(cleanup_task)
    
    async def wait_for_condition(self, condition_func: callable, 
                                timeout: float = 30.0, 
                                interval: float = 1.0,
                                description: str = "condition") -> bool:
        """Wait for a condition to be true with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if asyncio.iscoroutinefunction(condition_func):
                    result = await condition_func()
                else:
                    result = condition_func()
                
                if result:
                    return True
            except Exception as e:
                self.logger.debug(f"Condition check failed: {e}")
            
            await asyncio.sleep(interval)
        
        self.logger.error(f"Timeout waiting for {description} after {timeout}s")
        return False
    
    async def is_port_available(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.0)
                result = sock.connect_ex((host, port))
                return result != 0  # Available if connection fails
        except Exception:
            return False
    
    async def is_port_in_use(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a port is currently in use."""
        return not await self.is_port_available(port, host)
    
    async def wait_for_port_open(self, port: int, host: str = "127.0.0.1",
                                timeout: float = 30.0) -> bool:
        """Wait for a port to become available (service starts listening)."""
        return await self.wait_for_condition(
            lambda: self.is_port_in_use(port, host),
            timeout=timeout,
            description=f"port {port} to open"
        )
    
    async def wait_for_port_closed(self, port: int, host: str = "127.0.0.1",
                                  timeout: float = 10.0) -> bool:
        """Wait for a port to become unavailable (service stops)."""
        return await self.wait_for_condition(
            lambda: self.is_port_available(port, host),
            timeout=timeout,
            description=f"port {port} to close"
        )
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since test start."""
        return time.time() - self.start_time
    
    def detect_project_root(self, current_path: Optional[Path] = None) -> Path:
        """Detect project root directory."""
        current = current_path or Path(__file__).parent
        
        while current.parent != current:
            # Look for project markers
            if (current / "netra_backend").exists() and (current / "dev_launcher").exists():
                return current
            current = current.parent
        
        raise RuntimeError(f"Could not detect project root from {current_path or Path(__file__).parent}")
    
    async def run_command_async(self, cmd: List[str], cwd: Optional[Path] = None,
                               env: Optional[Dict[str, str]] = None,
                               timeout: float = 30.0) -> Tuple[int, str, str]:
        """Run a command asynchronously and return (returncode, stdout, stderr)."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd) if cwd else None,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                
                return (
                    process.returncode,
                    stdout_bytes.decode('utf-8', errors='replace'),
                    stderr_bytes.decode('utf-8', errors='replace')
                )
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return (-1, "", "Command timed out")
                
        except Exception as e:
            return (-1, "", f"Command failed: {e}")


class DevLauncherE2ETestMixin:
    """Mixin for dev launcher specific E2E test functionality."""
    
    def get_dev_launcher_command(self, extra_args: List[str] = None) -> List[str]:
        """Get the dev launcher command with standard test arguments."""
        cmd = [sys.executable, "-m", "dev_launcher"]
        
        # Standard test arguments
        standard_args = [
            "--dynamic",
            "--no-browser", 
            "--non-interactive",
            "--minimal",
            "--no-reload",
            "--no-secrets"
        ]
        
        cmd.extend(standard_args)
        
        if extra_args:
            cmd.extend(extra_args)
        
        return cmd
    
    def get_test_environment(self) -> Dict[str, str]:
        """Get standard test environment variables."""
        env_manager = get_env()
        env = env_manager.get_all()
        env.update({
            "NETRA_TEST_MODE": "true",
            "NETRA_STARTUP_MODE": "minimal",
            "NETRA_SKIP_SECRETS": "true"
        })
        return env