"""
Process management for development services.

This module provides simple process management without auto-restart.
Services rely on their native reload capabilities (uvicorn, Next.js).
"""

import os
import sys
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ProcessManager:
    """
    Manages development service processes.
    
    This class handles starting, stopping, and tracking processes
    without auto-restart functionality. Services use their native
    reload capabilities instead.
    """
    
    def __init__(self, health_monitor=None):
        """Initialize the process manager."""
        self.processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
        self.health_monitor = health_monitor
    
    def add_process(self, name: str, process: subprocess.Popen):
        """Add a process to be managed."""
        with self._lock:
            self.processes[name] = process
            logger.info(f"Added process: {name} (PID: {process.pid})")
    
    def terminate_process(self, name: str) -> bool:
        """Terminate a specific process."""
        with self._lock:
            if not self._process_exists(name):
                return False
            process = self.processes[name]
            return self._handle_process_termination(process, name)
    
    def _handle_process_termination(self, process: subprocess.Popen, name: str) -> bool:
        """Handle process termination logic."""
        if self._is_process_running(process, name):
            if not self._terminate_running_process(process, name):
                return False
        return self._cleanup_process(name)
    
    def _process_exists(self, name: str) -> bool:
        """Check if process exists in manager."""
        if name not in self.processes:
            logger.warning(f"Process {name} not found in manager")
            return False
        return True
    
    def _is_process_running(self, process: subprocess.Popen, name: str) -> bool:
        """Check if process is still running."""
        if process.poll() is None:
            logger.info(f"Terminating {name} (PID: {process.pid})")
            return True
        return False
    
    def _terminate_running_process(self, process: subprocess.Popen, name: str) -> bool:
        """Terminate a running process."""
        try:
            self._send_terminate_signal(process, name)
            self._wait_for_termination(process, name)
            return True
        except Exception as e:
            logger.error(f"Failed to terminate {name}: {e}")
            return False
    
    def _send_terminate_signal(self, process: subprocess.Popen, name: str):
        """Send terminate signal to process."""
        if sys.platform == "win32":
            self._terminate_windows_process(process, name)
        else:
            self._terminate_unix_process(process, name)
    
    def _terminate_windows_process(self, process: subprocess.Popen, name: str):
        """Terminate Windows process using taskkill."""
        result = self._run_taskkill_command(process)
        if result.returncode != 0:
            logger.warning(f"taskkill failed for {name}: {result.stderr}")
    
    def _run_taskkill_command(self, process: subprocess.Popen):
        """Run taskkill command for Windows process."""
        return subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            text=True
        )
    
    def _terminate_unix_process(self, process: subprocess.Popen, name: str):
        """Terminate Unix process using process group."""
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except ProcessLookupError:
            logger.warning(f"Process {name} already terminated")
        except Exception as e:
            logger.error(f"Error terminating {name}: {e}")
    
    def _wait_for_termination(self, process: subprocess.Popen, name: str):
        """Wait for process termination."""
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._handle_termination_timeout(process, name)
    
    def _handle_termination_timeout(self, process: subprocess.Popen, name: str):
        """Handle process termination timeout."""
        logger.warning(f"Process {name} did not terminate gracefully, forcing...")
        self._force_kill_process(process, name)
    
    def _force_kill_process(self, process: subprocess.Popen, name: str):
        """Force kill a process."""
        if sys.platform == "win32":
            self._force_kill_windows(process)
        else:
            self._force_kill_unix(process)
    
    def _force_kill_windows(self, process: subprocess.Popen):
        """Force kill Windows process."""
        subprocess.run(
            ["taskkill", "/F", "/PID", str(process.pid)],
            capture_output=True
        )
    
    def _force_kill_unix(self, process: subprocess.Popen):
        """Force kill Unix process."""
        try:
            process.kill()
        except ProcessLookupError:
            pass
    
    def _cleanup_process(self, name: str) -> bool:
        """Cleanup process from manager."""
        del self.processes[name]
        logger.info(f"Process {name} terminated successfully")
        return True
    
    def cleanup_all(self):
        """Clean up all processes."""
        for name, process in list(self.processes.items()):
            self.terminate_process(name)
    
    def wait_for_all(self):
        """Wait for all processes to complete."""
        failed_processes = []
        while self.processes:
            self._check_running_processes(failed_processes)
            if self._should_exit_early(failed_processes):
                break
            time.sleep(1)
    
    def _check_running_processes(self, failed_processes: list):
        """Check all running processes."""
        for name, process in list(self.processes.items()):
            if process.poll() is not None:
                self._handle_exited_process(name, process, failed_processes)
    
    def _handle_exited_process(self, name: str, process: subprocess.Popen, failed_processes: list):
        """Handle a process that has exited."""
        exit_code = process.returncode
        if exit_code != 0:
            self._handle_failed_process(name, exit_code, failed_processes)
        else:
            logger.info(f"Process {name} exited normally")
        self._unregister_from_health_monitor(name)
        self._remove_from_processes(name)
    
    def _handle_failed_process(self, name: str, exit_code: int, failed_processes: list):
        """Handle a failed process."""
        logger.error(f"Process {name} exited with error code {exit_code}")
        failed_processes.append((name, exit_code))
        self._log_exit_code_meaning(name, exit_code)
    
    def _log_exit_code_meaning(self, name: str, exit_code: int):
        """Log exit code meaning."""
        if exit_code == 1:
            logger.info(f"  → {name} encountered a general error")
        elif exit_code == 2:
            logger.info(f"  → {name} had a configuration error")
        elif exit_code == 3:
            logger.info(f"  → {name} had dependency issues")
        elif exit_code < 0:
            logger.info(f"  → {name} was terminated by signal {-exit_code}")
    
    def _unregister_from_health_monitor(self, name: str):
        """Unregister process from health monitoring."""
        if self.health_monitor:
            self.health_monitor.unregister_service(name)
    
    def _remove_from_processes(self, name: str):
        """Remove process from manager."""
        with self._lock:
            if name in self.processes:
                del self.processes[name]
    
    def _should_exit_early(self, failed_processes: list) -> bool:
        """Check if should exit early."""
        if failed_processes and not self.processes:
            self._log_all_processes_terminated()
            return True
        return False
    
    def _log_all_processes_terminated(self):
        """Log message when all processes terminated."""
        logger.error("All processes have terminated. Check the logs for details.")
    
    def get_process(self, name: str) -> Optional[subprocess.Popen]:
        """Get a specific process."""
        return self.processes.get(name)
    
    def is_running(self, name: str) -> bool:
        """Check if a process is running."""
        process = self.processes.get(name)
        return process is not None and process.poll() is None
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all processes."""
        stats = {'processes': []}
        self._collect_process_stats(stats)
        return stats
    
    def _collect_process_stats(self, stats: dict):
        """Collect statistics for all processes."""
        for name, process in self.processes.items():
            process_info = self._create_process_info(name, process)
            stats['processes'].append(process_info)
    
    def _create_process_info(self, name: str, process: subprocess.Popen) -> dict:
        """Create process information dictionary."""
        return {
            'name': name,
            'pid': process.pid,
            'is_running': process.poll() is None
        }
    
    def get_running_count(self) -> int:
        """Get count of running processes."""
        count = 0
        for process in self.processes.values():
            if process.poll() is None:
                count += 1
        return count
    
    def get_process_names(self) -> List[str]:
        """Get list of process names."""
        return list(self.processes.keys())