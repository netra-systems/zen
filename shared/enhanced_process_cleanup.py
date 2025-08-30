"""
Enhanced process cleanup utilities with comprehensive Windows support.

This module provides robust process cleanup functionality for Windows,
with special handling for Node.js, npm, and related development processes.

Business Value: Platform/Internal - Development Velocity
Prevents developer time loss due to hanging processes and port conflicts.
"""

import atexit
import logging
import os
import psutil
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from typing import List, Optional, Set, Dict, Tuple

logger = logging.getLogger(__name__)


class EnhancedProcessCleanup:
    """
    Enhanced process cleanup utility with comprehensive Windows support.
    
    Features:
    - Process tree termination with psutil for reliability
    - Automatic cleanup registration via atexit
    - Context manager support for scoped cleanup
    - Port-based process discovery and termination
    - Orphaned process detection
    """
    
    # Processes that commonly hang in development/testing
    TARGET_PROCESSES = {
        "node.exe", "node", 
        "npm", "npm.cmd", "npx", "npx.cmd",
        "jest", "jest.js", 
        "webpack", "webpack.exe",
        "next-server", "next-server.exe",
        "python.exe", "python",
        "uvicorn", "gunicorn",
        "pytest", "py.test"
    }
    
    # Common development ports to check
    DEV_PORTS = [3000, 3001, 3002, 8000, 8001, 8080, 5000, 5001]
    
    def __init__(self, auto_register: bool = True):
        """
        Initialize enhanced process cleanup utility.
        
        Args:
            auto_register: Whether to automatically register cleanup on exit
        """
        self.is_windows = sys.platform == "win32"
        self.tracked_processes: Set[int] = set()
        self.cleanup_registered = False
        
        if auto_register:
            self.register_cleanup_handler()
    
    def register_cleanup_handler(self):
        """Register cleanup handler for process exit."""
        if not self.cleanup_registered:
            atexit.register(self._cleanup_on_exit)
            self.cleanup_registered = True
            logger.debug("Process cleanup handler registered")
    
    def track_process(self, process: subprocess.Popen):
        """
        Track a subprocess for cleanup.
        
        Args:
            process: Subprocess to track
        """
        if process and process.pid:
            self.tracked_processes.add(process.pid)
            logger.debug(f"Tracking process {process.pid} for cleanup")
    
    def cleanup_all(self, include_ports: bool = True) -> Dict[str, int]:
        """
        Perform comprehensive cleanup of all hanging processes.
        
        Args:
            include_ports: Whether to clean up processes on dev ports
            
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "tracked_cleaned": 0,
            "orphaned_cleaned": 0,
            "port_cleaned": 0,
            "total_cleaned": 0
        }
        
        # Clean up tracked processes
        stats["tracked_cleaned"] = self._cleanup_tracked_processes()
        
        # Clean up orphaned development processes
        stats["orphaned_cleaned"] = self._cleanup_orphaned_processes()
        
        # Clean up processes on development ports
        if include_ports:
            stats["port_cleaned"] = self._cleanup_port_processes()
        
        stats["total_cleaned"] = sum(stats.values())
        
        if stats["total_cleaned"] > 0:
            logger.info(f"Cleaned up {stats['total_cleaned']} processes "
                       f"(tracked: {stats['tracked_cleaned']}, "
                       f"orphaned: {stats['orphaned_cleaned']}, "
                       f"ports: {stats['port_cleaned']})")
        
        return stats
    
    def cleanup_subprocess(self, process: subprocess.Popen, 
                         timeout: int = 10, force: bool = False) -> bool:
        """
        Clean up a specific subprocess and its children.
        
        Args:
            process: The subprocess to clean up
            timeout: Maximum time to wait for graceful termination
            force: Whether to force kill immediately
            
        Returns:
            True if cleanup was successful
        """
        if not process or process.poll() is not None:
            return True
        
        try:
            # Use psutil for reliable process tree termination
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                
                # Terminate gracefully first (unless force)
                if not force:
                    for child in children:
                        try:
                            child.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    try:
                        parent.terminate()
                        parent.wait(timeout=timeout // 2)
                    except (psutil.TimeoutExpired, psutil.NoSuchProcess):
                        force = True
                
                # Force kill if needed
                if force:
                    for child in children:
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    try:
                        parent.kill()
                        parent.wait(timeout=timeout // 2)
                    except (psutil.TimeoutExpired, psutil.NoSuchProcess):
                        return False
                
                return True
                
            except psutil.NoSuchProcess:
                # Process already terminated
                return True
            except Exception as e:
                logger.debug(f"psutil cleanup failed, falling back: {e}")
                # Fall back to basic subprocess methods
                return self._fallback_cleanup(process, timeout, force)
                
        except Exception as e:
            logger.error(f"Error cleaning up subprocess {process.pid}: {e}")
            return False
    
    def cleanup_port_processes(self, ports: Optional[List[int]] = None) -> int:
        """
        Clean up processes using specific ports.
        
        Args:
            ports: List of ports to check (defaults to DEV_PORTS)
            
        Returns:
            Number of processes cleaned up
        """
        ports = ports or self.DEV_PORTS
        return self._cleanup_port_processes(ports)
    
    @contextmanager
    def cleanup_context(self):
        """
        Context manager for automatic process cleanup.
        
        Usage:
            with cleanup.cleanup_context():
                # Run processes
                pass
            # All tracked processes are cleaned up here
        """
        initial_tracked = self.tracked_processes.copy()
        try:
            yield self
        finally:
            # Clean up any new processes tracked during context
            new_processes = self.tracked_processes - initial_tracked
            for pid in new_processes:
                self._terminate_process_tree(pid)
    
    def _cleanup_tracked_processes(self) -> int:
        """Clean up all tracked processes."""
        cleaned = 0
        for pid in list(self.tracked_processes):
            if self._terminate_process_tree(pid):
                cleaned += 1
                self.tracked_processes.discard(pid)
        return cleaned
    
    def _cleanup_orphaned_processes(self) -> int:
        """Clean up orphaned development processes."""
        cleaned = 0
        current_pid = os.getpid()
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'ppid', 'create_time']):
                try:
                    # Skip current process and system processes
                    if proc.pid == current_pid or proc.pid == 0:
                        continue
                    
                    # Check if it's a target process
                    proc_name = proc.name().lower()
                    if any(target.lower() in proc_name for target in self.TARGET_PROCESSES):
                        # Check if parent is dead (orphaned)
                        try:
                            parent = psutil.Process(proc.ppid())
                            if not parent.is_running():
                                raise psutil.NoSuchProcess(proc.ppid())
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # Parent is dead or inaccessible - this is likely orphaned
                            if self._terminate_process_tree(proc.pid, proc_name):
                                cleaned += 1
                                logger.debug(f"Cleaned orphaned {proc_name} (PID: {proc.pid})")
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.debug(f"Error during orphaned process cleanup: {e}")
        
        return cleaned
    
    def _cleanup_port_processes(self, ports: List[int] = None) -> int:
        """Clean up processes using specific ports."""
        ports = ports or self.DEV_PORTS
        cleaned = 0
        
        for port in ports:
            pids = self._get_pids_using_port(port)
            for pid in pids:
                if pid != os.getpid():  # Don't kill ourselves
                    if self._terminate_process_tree(pid, f"port_{port}"):
                        cleaned += 1
                        logger.debug(f"Cleaned process {pid} using port {port}")
        
        return cleaned
    
    def _get_pids_using_port(self, port: int) -> Set[int]:
        """Get PIDs of processes using a specific port."""
        pids = set()
        
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.pid:
                    pids.add(conn.pid)
        except (psutil.AccessDenied, AttributeError):
            # Fall back to platform-specific methods
            if self.is_windows:
                pids.update(self._get_pids_using_port_windows(port))
            else:
                pids.update(self._get_pids_using_port_unix(port))
        
        return pids
    
    def _get_pids_using_port_windows(self, port: int) -> Set[int]:
        """Windows-specific port to PID lookup."""
        pids = set()
        try:
            result = subprocess.run(
                f"netstat -ano | findstr :{port}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 5:
                        pid_str = parts[-1]
                        if pid_str.isdigit() and pid_str != "0":
                            pids.add(int(pid_str))
        except Exception as e:
            logger.debug(f"Windows port lookup failed: {e}")
        
        return pids
    
    def _get_pids_using_port_unix(self, port: int) -> Set[int]:
        """Unix-specific port to PID lookup."""
        pids = set()
        try:
            result = subprocess.run(
                f"lsof -ti :{port}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                for pid_str in result.stdout.strip().split('\n'):
                    if pid_str.isdigit():
                        pids.add(int(pid_str))
        except Exception as e:
            logger.debug(f"Unix port lookup failed: {e}")
        
        return pids
    
    def _terminate_process_tree(self, pid: int, name: str = "") -> bool:
        """Terminate a process and all its children."""
        try:
            # Use psutil for reliable termination
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # Terminate children first, then parent
            for child in children:
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            try:
                parent.terminate()
                # Give it a moment to terminate
                parent.wait(timeout=2)
            except psutil.TimeoutExpired:
                # Force kill if termination failed
                for child in children:
                    try:
                        child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                parent.kill()
                parent.wait(timeout=1)
            
            return True
            
        except psutil.NoSuchProcess:
            # Already terminated
            return True
        except Exception as e:
            logger.debug(f"Failed to terminate process {pid} ({name}): {e}")
            # Try platform-specific fallback
            return self._terminate_process_fallback(pid)
    
    def _terminate_process_fallback(self, pid: int) -> bool:
        """Platform-specific fallback for process termination."""
        try:
            if self.is_windows:
                # Use taskkill with tree flag
                result = subprocess.run(
                    f"taskkill /F /T /PID {pid}",
                    shell=True,
                    capture_output=True,
                    timeout=3
                )
                return result.returncode == 0
            else:
                # Use kill on Unix
                os.kill(pid, signal.SIGKILL)
                return True
        except Exception:
            return False
    
    def _fallback_cleanup(self, process: subprocess.Popen, 
                         timeout: int, force: bool) -> bool:
        """Fallback cleanup using basic subprocess methods."""
        try:
            if not force:
                process.terminate()
                try:
                    process.wait(timeout=timeout // 2)
                    return True
                except subprocess.TimeoutExpired:
                    pass
            
            # Force kill
            if self.is_windows:
                subprocess.run(
                    f"taskkill /F /T /PID {process.pid}",
                    shell=True,
                    timeout=3
                )
            else:
                process.kill()
            
            try:
                process.wait(timeout=timeout // 2)
                return True
            except subprocess.TimeoutExpired:
                return False
                
        except Exception:
            return False
    
    def _cleanup_on_exit(self):
        """Clean up any hanging processes on exit."""
        try:
            stats = self.cleanup_all()
            if stats["total_cleaned"] > 0:
                logger.info(f"Exit cleanup: removed {stats['total_cleaned']} hanging processes")
        except Exception as e:
            logger.debug(f"Error during exit cleanup: {e}")


# Global instance for convenience
_cleanup_instance: Optional[EnhancedProcessCleanup] = None


def get_cleanup_instance() -> EnhancedProcessCleanup:
    """Get or create the global cleanup instance."""
    global _cleanup_instance
    if _cleanup_instance is None:
        _cleanup_instance = EnhancedProcessCleanup(auto_register=True)
    return _cleanup_instance


def cleanup_hanging_processes() -> Dict[str, int]:
    """Convenience function to clean up all hanging processes."""
    return get_cleanup_instance().cleanup_all()


def cleanup_subprocess(process: subprocess.Popen, timeout: int = 10) -> bool:
    """Convenience function to clean up after a subprocess."""
    return get_cleanup_instance().cleanup_subprocess(process, timeout)


def track_subprocess(process: subprocess.Popen):
    """Track a subprocess for automatic cleanup."""
    get_cleanup_instance().track_process(process)


@contextmanager
def managed_subprocess(*args, **kwargs):
    """
    Context manager for subprocess with automatic cleanup.
    
    Usage:
        with managed_subprocess(['node', 'server.js']) as proc:
            # Use process
            pass
        # Process is automatically cleaned up
    """
    process = None
    try:
        process = subprocess.Popen(*args, **kwargs)
        track_subprocess(process)
        yield process
    finally:
        if process:
            cleanup_subprocess(process)