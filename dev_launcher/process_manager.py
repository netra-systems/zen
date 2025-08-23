"""
Process management for development services.

This module provides robust process management with platform-specific optimizations.
Windows-specific features:
- Enhanced process tree termination with taskkill /F /T
- Process verification using tasklist and netstat
- Proper handling of Node.js child processes
- Port cleanup verification after process termination

Services rely on their native reload capabilities (uvicorn, Next.js).
"""

import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ProcessManager:
    """
    Manages development service processes with enhanced Windows compatibility.
    
    This class handles starting, stopping, and tracking processes
    with platform-specific optimizations:
    
    Windows:
    - Process tree termination with taskkill /F /T
    - Port cleanup verification using netstat
    - Child process tracking for Node.js applications
    
    Unix/Linux/Mac:
    - Process group management
    - Signal-based termination with fallback to SIGKILL
    - Resource cleanup verification
    
    Services use their native reload capabilities instead of auto-restart.
    """
    
    def __init__(self, health_monitor=None):
        """Initialize the process manager with platform detection."""
        self.processes: Dict[str, subprocess.Popen] = {}
        self.process_ports: Dict[str, Set[int]] = {}  # Track ports used by each process
        self.process_info: Dict[str, Dict[str, Any]] = {}  # Track additional process metadata
        self._lock = threading.Lock()
        self.health_monitor = health_monitor
        self.is_windows = sys.platform == "win32"
        self.shutdown_timeout = 10  # Seconds to wait for graceful shutdown
        
        logger.info(f"ProcessManager initialized for {sys.platform}")
        if self.is_windows:
            logger.info("Enhanced Windows process tree management enabled")
    
    def add_process(self, name: str, process: subprocess.Popen, ports: Optional[Set[int]] = None):
        """Add a process to be managed with optional port tracking."""
        with self._lock:
            self.processes[name] = process
            self.process_ports[name] = ports or set()
            self.process_info[name] = {
                'pid': process.pid,
                'start_time': time.time(),
                'name': name,
                'platform': sys.platform
            }
            
            logger.info(f"Added process: {name} (PID: {process.pid})")
            if ports:
                logger.info(f"Process {name} using ports: {sorted(ports)}")
    
    def register_process_port(self, name: str, port: int):
        """Register a port used by a process."""
        with self._lock:
            if name not in self.process_ports:
                self.process_ports[name] = set()
            self.process_ports[name].add(port)
            logger.debug(f"Registered port {port} for process {name}")
    
    def terminate_process(self, name: str, timeout: int = 5) -> bool:
        """Terminate a specific process gracefully."""
        with self._lock:
            if not self._process_exists(name):
                return False
            process = self.processes[name]
            return self._handle_process_termination(process, name, timeout)
    
    def kill_process(self, name: str) -> bool:
        """Force kill a specific process immediately (for emergency situations)."""
        with self._lock:
            if not self._process_exists(name):
                return False
            process = self.processes[name]
            return self._handle_process_force_kill(process, name)
    
    def _handle_process_force_kill(self, process: subprocess.Popen, name: str) -> bool:
        """Handle immediate process force killing."""
        if process.poll() is None:  # Process is still running
            logger.info(f"Force killing {name} (PID: {process.pid})")
            try:
                # Skip graceful termination, go straight to force kill
                self._force_kill_process(process, name)
                # Wait briefly to verify termination
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force kill of {name} may not have completed immediately")
                return self._cleanup_process(name)
            except Exception as e:
                logger.error(f"Failed to force kill {name}: {e}")
                return False
        else:
            # Process already terminated
            return self._cleanup_process(name)
    
    def _handle_process_termination(self, process: subprocess.Popen, name: str, timeout: int = 5) -> bool:
        """Handle process termination logic."""
        if self._is_process_running(process, name):
            if not self._terminate_running_process(process, name, timeout):
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
    
    def _terminate_running_process(self, process: subprocess.Popen, name: str, timeout: int = 5) -> bool:
        """Terminate a running process."""
        try:
            self._send_terminate_signal(process, name)
            self._wait_for_termination(process, name, timeout)
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
        """Enhanced Windows process termination with tree kill and verification."""
        logger.info(f"Terminating Windows process tree for {name} (PID: {process.pid})")
        
        # Step 1: Try graceful termination first for certain processes
        if name.lower() in ['backend', 'frontend']:
            try:
                process.terminate()  # Send SIGTERM equivalent
                if self._wait_for_process_termination(process, timeout=5):
                    logger.info(f"Process {name} terminated gracefully")
                    return
            except Exception as e:
                logger.debug(f"Graceful termination failed for {name}: {e}")
        
        # Step 2: Use taskkill with process tree termination
        result = self._run_taskkill_tree_command(process)
        if result.returncode == 0:
            logger.info(f"Successfully terminated process tree for {name}")
            # Verify termination
            if self._verify_process_termination(process, name):
                return
        else:
            logger.warning(f"taskkill /T failed for {name}: {result.stderr}")
        
        # Step 3: Force kill if tree termination failed
        logger.warning(f"Attempting force kill for {name}")
        self._force_kill_windows_enhanced(process, name)
    
    def _run_taskkill_tree_command(self, process: subprocess.Popen):
        """Run taskkill command with tree termination for Windows process."""
        try:
            return subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                text=True,
                timeout=10  # Add timeout to prevent hanging
            )
        except subprocess.TimeoutExpired:
            logger.error("taskkill command timed out")
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="Timeout"
            )
    
    def _wait_for_process_termination(self, process: subprocess.Popen, timeout: int = 5) -> bool:
        """Wait for process to terminate within timeout."""
        try:
            process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            return False
    
    def _verify_process_termination(self, process: subprocess.Popen, name: str) -> bool:
        """Verify that process has actually terminated on Windows."""
        try:
            # Check using tasklist
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {process.pid}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # If the process is not found, tasklist will show "No tasks running"
                if "No tasks are running" in result.stdout:
                    logger.info(f"Verified: Process {name} (PID: {process.pid}) terminated")
                    return True
                else:
                    logger.warning(f"Process {name} (PID: {process.pid}) still running according to tasklist")
                    return False
            else:
                logger.debug(f"tasklist verification failed: {result.stderr}")
                # If tasklist fails, assume termination succeeded
                return True
                
        except Exception as e:
            logger.debug(f"Process verification error for {name}: {e}")
            return True  # Assume success if verification fails
    
    def _force_kill_windows_enhanced(self, process: subprocess.Popen, name: str):
        """Enhanced force kill for Windows with multiple attempts."""
        attempts = [
            # Attempt 1: Direct PID kill
            ["taskkill", "/F", "/PID", str(process.pid)],
            # Attempt 2: Kill by process name if we can determine it
            ["taskkill", "/F", "/IM", f"python.exe"],  # For Python processes
            ["taskkill", "/F", "/IM", f"node.exe"],    # For Node.js processes
        ]
        
        for i, cmd in enumerate(attempts):
            try:
                if i == 0:  # Direct PID kill
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        logger.info(f"Force kill succeeded for {name}")
                        return
                elif name.lower() == 'frontend' and 'node.exe' in cmd:
                    # Only kill node.exe for frontend processes
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    logger.debug(f"Attempted to kill Node.js processes for {name}")
                elif name.lower() == 'backend' and 'python.exe' in cmd:
                    # Only kill python.exe for backend processes (more targeted)
                    continue  # Skip generic python kill to avoid killing dev launcher
                    
            except Exception as e:
                logger.debug(f"Force kill attempt {i+1} failed for {name}: {e}")
        
        logger.error(f"All force kill attempts failed for {name}")
    def _terminate_unix_process(self, process: subprocess.Popen, name: str):
        """Terminate Unix process using process group."""
        try:
            if sys.platform == "darwin":
                # Mac: try SIGTERM first, then SIGKILL if needed
                os.kill(process.pid, signal.SIGTERM)
            else:
                # Linux: use process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except ProcessLookupError:
            logger.warning(f"Process {name} already terminated")
        except Exception as e:
            logger.error(f"Error terminating {name}: {e}")
    
    def _wait_for_termination(self, process: subprocess.Popen, name: str, timeout: int = 5):
        """Wait for process termination."""
        try:
            process.wait(timeout=timeout)
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
            if sys.platform == "darwin":
                # Mac: use SIGKILL directly
                os.kill(process.pid, signal.SIGKILL)
            else:
                # Linux: kill process group
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except:
                    process.kill()
        except ProcessLookupError:
            pass
    
    def _cleanup_process(self, name: str) -> bool:
        """Cleanup process from manager."""
        del self.processes[name]
        logger.info(f"Process {name} terminated successfully")
        return True
    
    def cleanup_all(self):
        """Clean up all processes with port verification."""
        logger.info("Starting cleanup of all managed processes")
        
        # Collect all ports before cleanup
        all_ports = set()
        for ports in self.process_ports.values():
            all_ports.update(ports)
        
        # Terminate all processes
        terminated_processes = []
        for name, process in list(self.processes.items()):
            if self.terminate_process(name):
                terminated_processes.append(name)
        
        # Verify port cleanup on Windows
        if self.is_windows and all_ports:
            self._verify_port_cleanup(all_ports, terminated_processes)
        
        logger.info(f"Cleanup completed for {len(terminated_processes)} processes")
    
    def _verify_port_cleanup(self, ports: Set[int], process_names: List[str], max_attempts: int = 3):
        """Verify that ports are no longer in use after process termination."""
        if not ports:
            return
            
        logger.info(f"Verifying cleanup of ports: {sorted(ports)}")
        
        for attempt in range(max_attempts):
            time.sleep(1)  # Give processes time to release ports
            
            still_in_use = self._check_ports_in_use(ports)
            if not still_in_use:
                logger.info("All ports successfully released")
                return
            
            logger.warning(f"Attempt {attempt + 1}: Ports still in use: {sorted(still_in_use)}")
            
            if attempt < max_attempts - 1:  # Not the last attempt
                # Try to find and kill processes still using these ports
                self._cleanup_port_processes(still_in_use)
        
        # Final check and warning
        final_check = self._check_ports_in_use(ports)
        if final_check:
            logger.error(f"WARNING: Ports still in use after cleanup: {sorted(final_check)}")
            logger.error("You may need to manually kill processes or restart your system")
            
    def _check_ports_in_use(self, ports: Set[int]) -> Set[int]:
        """Check which ports are still in use using netstat."""
        in_use = set()
        
        if not ports:
            return in_use
        
        try:
            if self.is_windows:
                # Use netstat on Windows
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        for port in ports:
                            # Look for lines containing the port
                            if f":{port} " in line and "LISTENING" in line:
                                in_use.add(port)
                                logger.debug(f"Port {port} still in use: {line.strip()}")
            else:
                # Use lsof on Unix-like systems
                for port in ports:
                    result = subprocess.run(
                        ["lsof", "-i", f":{port}"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        in_use.add(port)
                        
        except Exception as e:
            logger.debug(f"Error checking port usage: {e}")
        
        return in_use
    
    def _cleanup_port_processes(self, ports: Set[int]):
        """Try to cleanup processes still using specific ports."""
        if not self.is_windows:
            return
            
        for port in ports:
            try:
                # Find process using the port
                result = subprocess.run(
                    ["netstat", "-ano", "|", "findstr", f":{port}"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True  # Required for pipe on Windows
                )
                
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "LISTENING" in line:
                            # Extract PID from netstat output
                            parts = line.split()
                            if parts:
                                try:
                                    pid = parts[-1]
                                    logger.info(f"Attempting to kill process {pid} using port {port}")
                                    subprocess.run(
                                        ["taskkill", "/F", "/PID", pid],
                                        capture_output=True,
                                        timeout=5
                                    )
                                except (ValueError, IndexError):
                                    continue
                                    
            except Exception as e:
                logger.debug(f"Error cleaning up port {port}: {e}")
    
    def check_port_available(self, port: int) -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                return result != 0  # Port is available if connection failed
        except Exception:
            return False
    
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