"""
Stub implementation for ProcessManager to fix broken imports.
Core process management functionality integrated into service coordinators.
"""

import asyncio
import subprocess
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path


class ProcessManager:
    """Stub for backward compatibility - minimal process management."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
    
    async def start_process(self, name: str, command: List[str], 
                           cwd: Optional[Path] = None) -> bool:
        """Start a process."""
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes[name] = process
            return True
        except Exception as e:
            print(f"Failed to start process {name}: {e}", file=sys.stderr)
            return False
    
    async def stop_process(self, name: str) -> bool:
        """Stop a process."""
        if name in self.processes:
            process = self.processes[name]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            del self.processes[name]
            return True
        return False
    
    async def cleanup(self) -> None:
        """Cleanup all processes."""
        for name in list(self.processes.keys()):
            await self.stop_process(name)
    
    def is_running(self, name: str) -> bool:
        """Check if process is running."""
        if name in self.processes:
            return self.processes[name].poll() is None
        return False
    
    def terminate_process(self, name: str, timeout: int = 5) -> bool:
        """Terminate a process gracefully."""
        if name in self.processes:
            process = self.processes[name]
            try:
                process.terminate()
                process.wait(timeout=timeout)
                del self.processes[name]
                return True
            except subprocess.TimeoutExpired:
                return False
            except Exception as e:
                print(f"Failed to terminate process {name}: {e}", file=sys.stderr)
                return False
        return False
    
    def kill_process(self, name: str) -> bool:
        """Force kill a process."""
        if name in self.processes:
            process = self.processes[name]
            try:
                process.kill()
                process.wait(timeout=2)
                del self.processes[name]
                return True
            except Exception as e:
                print(f"Failed to kill process {name}: {e}", file=sys.stderr)
                return False
        return False
    
    def add_process(self, name: str, process: subprocess.Popen) -> None:
        """Add an existing process to management."""
        self.processes[name] = process
    
    async def cleanup_all(self) -> None:
        """Cleanup all processes - alias for cleanup()."""
        await self.cleanup()
    
    async def wait_for_all(self) -> None:
        """Wait for all processes to complete."""
        for name, process in list(self.processes.items()):
            try:
                process.wait()
            except Exception as e:
                print(f"Error waiting for process {name}: {e}", file=sys.stderr)
            finally:
                if name in self.processes:
                    del self.processes[name]