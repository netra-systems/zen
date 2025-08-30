"""
Windows-specific process cleanup utilities.

This module provides robust process cleanup functionality for Windows,
particularly for Node.js processes that tend to hang after tests or dev launcher.

Business Value: Platform/Internal - Development Velocity
Prevents developer time loss due to hanging processes and port conflicts.
"""

import logging
import os
import subprocess
import sys
import time
from typing import List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class WindowsProcessCleanup:
    """
    Windows process cleanup utility with focus on Node.js and related processes.
    
    Handles:
    - Process tree termination using taskkill /T
    - Node.js child process cleanup
    - Port cleanup verification
    - Zombie process detection and cleanup
    """
    
    def __init__(self):
        """Initialize Windows process cleanup utility."""
        self.is_windows = sys.platform == "win32"
        if not self.is_windows:
            logger.warning("WindowsProcessCleanup initialized on non-Windows platform")
    
    def cleanup_node_processes(self, exclude_pids: Optional[Set[int]] = None) -> int:
        """
        Clean up hanging Node.js processes.
        
        Args:
            exclude_pids: Set of PIDs to exclude from cleanup (e.g., current process)
            
        Returns:
            Number of processes cleaned up
        """
        if not self.is_windows:
            return 0
        
        exclude_pids = exclude_pids or set()
        exclude_pids.add(os.getpid())  # Always exclude current process
        
        cleaned_count = 0
        
        # Target processes that commonly hang
        target_processes = [
            "node.exe",
            "npm.cmd",
            "npx.cmd",
            "jest.js",
            "webpack.exe",
            "next-server.exe"
        ]
        
        for process_name in target_processes:
            try:
                pids = self._get_process_pids(process_name)
                for pid in pids:
                    if pid not in exclude_pids:
                        if self._terminate_process_tree(pid, process_name):
                            cleaned_count += 1
                            logger.info(f"Cleaned up {process_name} (PID: {pid})")
            except Exception as e:
                logger.debug(f"Error cleaning {process_name}: {e}")
        
        # Also clean up any orphaned processes using common test/dev ports
        port_cleanup_count = self._cleanup_processes_on_ports([3000, 3001, 8000, 8001])
        cleaned_count += port_cleanup_count
        
        return cleaned_count
    
    def cleanup_after_subprocess(self, process: subprocess.Popen, timeout: int = 10) -> bool:
        """
        Clean up after a subprocess completes or times out.
        
        Args:
            process: The subprocess to clean up
            timeout: Maximum time to wait for graceful termination
            
        Returns:
            True if cleanup was successful
        """
        if not self.is_windows:
            return True
        
        try:
            # First try graceful termination
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=timeout // 2)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    self._force_terminate_process(process.pid)
                    try:
                        process.wait(timeout=timeout // 2)
                    except subprocess.TimeoutExpired:
                        logger.error(f"Failed to terminate process {process.pid}")
                        return False
            
            # Clean up any child processes
            self._cleanup_child_processes(process.pid)
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up subprocess: {e}")
            return False
    
    def _get_process_pids(self, process_name: str) -> List[int]:
        """Get PIDs for processes matching the given name."""
        pids = []
        try:
            # Use WMIC to get process information
            result = subprocess.run(
                f'wmic process where "name like \'%{process_name}%\'" get ProcessId',
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    pid_str = line.strip()
                    if pid_str.isdigit():
                        pids.append(int(pid_str))
        except Exception as e:
            logger.debug(f"Error getting PIDs for {process_name}: {e}")
        
        return pids
    
    def _terminate_process_tree(self, pid: int, process_name: str = "") -> bool:
        """Terminate a process and all its children."""
        try:
            # Use taskkill with tree flag
            result = subprocess.run(
                f"taskkill /F /T /PID {pid}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return True
            elif "not found" in result.stderr.lower():
                # Process already terminated
                return True
            else:
                logger.debug(f"Failed to terminate {process_name or 'process'} (PID: {pid}): {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout terminating process {pid}")
            return False
        except Exception as e:
            logger.debug(f"Error terminating process {pid}: {e}")
            return False
    
    def _force_terminate_process(self, pid: int) -> bool:
        """Force terminate a process using taskkill /F."""
        try:
            result = subprocess.run(
                f"taskkill /F /PID {pid}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=3
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _cleanup_child_processes(self, parent_pid: int) -> int:
        """Clean up any child processes of the given parent PID."""
        cleaned_count = 0
        
        try:
            # Use WMIC to find child processes
            result = subprocess.run(
                f'wmic process where "ParentProcessId={parent_pid}" get ProcessId',
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    pid_str = line.strip()
                    if pid_str.isdigit():
                        child_pid = int(pid_str)
                        if self._terminate_process_tree(child_pid):
                            cleaned_count += 1
                            
        except Exception as e:
            logger.debug(f"Error cleaning child processes: {e}")
        
        return cleaned_count
    
    def _cleanup_processes_on_ports(self, ports: List[int]) -> int:
        """Clean up processes using specific ports."""
        cleaned_count = 0
        
        for port in ports:
            try:
                # Find processes using the port
                result = subprocess.run(
                    f"netstat -ano | findstr :{port}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout:
                    pids_to_clean = set()
                    lines = result.stdout.strip().split('\n')
                    
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            if pid.isdigit() and pid != "0":
                                pids_to_clean.add(int(pid))
                    
                    for pid in pids_to_clean:
                        if pid != os.getpid():  # Don't kill ourselves
                            if self._force_terminate_process(pid):
                                cleaned_count += 1
                                logger.debug(f"Cleaned process {pid} using port {port}")
                                
            except Exception as e:
                logger.debug(f"Error cleaning processes on port {port}: {e}")
        
        return cleaned_count
    
    def register_cleanup_handler(self):
        """Register cleanup handler for process exit."""
        if not self.is_windows:
            return
        
        import atexit
        
        def cleanup_on_exit():
            """Clean up any hanging processes on exit."""
            try:
                count = self.cleanup_node_processes()
                if count > 0:
                    logger.info(f"Cleaned up {count} hanging processes on exit")
            except Exception as e:
                logger.debug(f"Error during exit cleanup: {e}")
        
        atexit.register(cleanup_on_exit)


# Global instance for convenience
_cleanup_instance = None


def get_cleanup_instance() -> WindowsProcessCleanup:
    """Get or create the global cleanup instance."""
    global _cleanup_instance
    if _cleanup_instance is None:
        _cleanup_instance = WindowsProcessCleanup()
    return _cleanup_instance


def cleanup_hanging_node_processes() -> int:
    """Convenience function to clean up hanging Node.js processes."""
    return get_cleanup_instance().cleanup_node_processes()


def cleanup_subprocess(process: subprocess.Popen, timeout: int = 10) -> bool:
    """Convenience function to clean up after a subprocess."""
    return get_cleanup_instance().cleanup_after_subprocess(process, timeout)