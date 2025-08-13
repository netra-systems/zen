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
                return False
            
            process = self.processes[name]
            
            if process.poll() is None:
                # Process is still running
                logger.info(f"Terminating {name} (PID: {process.pid})")
                
                if sys.platform == "win32":
                    # Windows: Use taskkill for tree termination
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        capture_output=True
                    )
                else:
                    # Unix: Use process group termination
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                
                # Wait for termination
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
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
            
            del self.processes[name]
            logger.info(f"Process {name} terminated")
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
        while self.processes:
            # Check each process
            for name, process in list(self.processes.items()):
                if process.poll() is not None:
                    # Process has exited
                    logger.info(f"Process {name} exited with code {process.returncode}")
                    with self._lock:
                        if name in self.processes:
                            del self.processes[name]
            
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