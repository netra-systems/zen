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
    
    def __init__(self):
        """Initialize the process manager."""
        self.processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
    
    def add_process(self, name: str, process: subprocess.Popen):
        """
        Add a process to be managed.
        
        Args:
            name: Name of the service
            process: The subprocess.Popen instance
        """
        with self._lock:
            self.processes[name] = process
            logger.info(f"Added process: {name} (PID: {process.pid})")
    
    def terminate_process(self, name: str) -> bool:
        """
        Terminate a specific process.
        
        Args:
            name: Name of the service to terminate
            
        Returns:
            True if process was terminated
        """
        with self._lock:
            if name not in self.processes:
                logger.warning(f"Process {name} not found in manager")
                return False
            
            process = self.processes[name]
            
            if process.poll() is None:
                # Process is still running
                logger.info(f"Terminating {name} (PID: {process.pid})")
                
                try:
                    if sys.platform == "win32":
                        # Windows: Use taskkill for tree termination
                        result = subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode != 0:
                            logger.warning(f"taskkill failed for {name}: {result.stderr}")
                    else:
                        # Unix: Use process group termination
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        except ProcessLookupError:
                            logger.warning(f"Process {name} already terminated")
                        except Exception as e:
                            logger.error(f"Error terminating {name}: {e}")
                    
                    # Wait for termination
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Process {name} did not terminate gracefully, forcing...")
                        # Force kill if still running
                        if sys.platform == "win32":
                            subprocess.run(
                                ["taskkill", "/F", "/PID", str(process.pid)],
                                capture_output=True
                            )
                        else:
                            try:
                                process.kill()
                            except ProcessLookupError:
                                pass
                except Exception as e:
                    logger.error(f"Failed to terminate {name}: {e}")
                    return False
            
            del self.processes[name]
            logger.info(f"Process {name} terminated successfully")
            return True
    
    def cleanup_all(self):
        """Clean up all processes."""
        # Stop all processes
        for name, process in list(self.processes.items()):
            self.terminate_process(name)
    
    def wait_for_all(self):
        """
        Wait for all processes to complete.
        
        This blocks until all processes have exited.
        """
        failed_processes = []
        
        while self.processes:
            # Check each process
            for name, process in list(self.processes.items()):
                if process.poll() is not None:
                    # Process has exited
                    exit_code = process.returncode
                    
                    if exit_code != 0:
                        logger.error(f"Process {name} exited with error code {exit_code}")
                        failed_processes.append((name, exit_code))
                        
                        # Provide helpful error messages based on exit code
                        if exit_code == 1:
                            logger.info(f"  → {name} encountered a general error")
                        elif exit_code == 2:
                            logger.info(f"  → {name} had a configuration error")
                        elif exit_code == 3:
                            logger.info(f"  → {name} had dependency issues")
                        elif exit_code < 0:
                            logger.info(f"  → {name} was terminated by signal {-exit_code}")
                    else:
                        logger.info(f"Process {name} exited normally")
                    
                    with self._lock:
                        if name in self.processes:
                            del self.processes[name]
            
            # If all critical processes have failed, exit early
            if failed_processes and not self.processes:
                logger.error("All processes have terminated. Check the logs for details.")
                break
            
            # Small delay to avoid busy waiting
            time.sleep(1)
    
    def get_process(self, name: str) -> Optional[subprocess.Popen]:
        """
        Get a specific process.
        
        Args:
            name: Name of the service
            
        Returns:
            The process if found, None otherwise
        """
        return self.processes.get(name)
    
    def is_running(self, name: str) -> bool:
        """
        Check if a process is running.
        
        Args:
            name: Name of the service
            
        Returns:
            True if process is running
        """
        process = self.processes.get(name)
        return process is not None and process.poll() is None
    
    def get_all_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all processes.
        
        Returns:
            Dictionary with process statistics
        """
        stats = {
            'processes': []
        }
        
        # Regular processes
        for name, process in self.processes.items():
            stats['processes'].append({
                'name': name,
                'pid': process.pid,
                'is_running': process.poll() is None
            })
        
        return stats
    
    def get_running_count(self) -> int:
        """
        Get count of running processes.
        
        Returns:
            Number of running processes
        """
        count = 0
        for process in self.processes.values():
            if process.poll() is None:
                count += 1
        return count
    
    def get_process_names(self) -> List[str]:
        """
        Get list of process names.
        
        Returns:
            List of service names
        """
        return list(self.processes.keys())