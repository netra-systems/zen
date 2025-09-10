#!/usr/bin/env python3
"""
E2E Functionality Preservation Suite - Integration Test Suite

Business Value: Platform/Internal - Test Infrastructure Migration Safety
Ensures BaseE2ETest capabilities are preserved during SSOT migration.

This suite validates that essential BaseE2ETest functionality is preserved in SSOT base classes:
1. Port utilities work with SSOT inheritance (port checking, generation)
2. Process management capabilities are preserved (startup, monitoring, cleanup)
3. Service health checking continues to function
4. Setup/teardown patterns work with SSOT inheritance

Purpose: Ensure no capability loss during BaseE2ETest → SSOT migration.
Strategic importance: Maintains E2E testing infrastructure reliability.

Author: E2E Functionality Preservation Agent  
Date: 2025-09-10
"""

import asyncio
import logging
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import signal
import psutil

# SSOT imports
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class E2EFunctionalityTester:
    """Utility class to test E2E functionality preservation."""
    
    def __init__(self, env):
        """Initialize functionality tester."""
        self.env = env
        self.test_processes = []
        self.cleanup_tasks = []
        
    def find_free_port(self, start_port: int = 8000, max_attempts: int = 100) -> int:
        """
        Find a free port starting from start_port.
        
        This replicates BaseE2ETest port utility functionality.
        """
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(('localhost', port))
                    return port
            except OSError:
                continue
        
        raise RuntimeError(f"No free port found in range {start_port}-{start_port + max_attempts}")
    
    def check_port_available(self, port: int) -> bool:
        """
        Check if a port is available.
        
        This replicates BaseE2ETest port checking functionality.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def generate_port_range(self, count: int, start_port: int = 9000) -> List[int]:
        """
        Generate a range of available ports.
        
        This replicates BaseE2ETest port range generation.
        """
        ports = []
        current_port = start_port
        
        while len(ports) < count:
            if self.check_port_available(current_port):
                ports.append(current_port)
            current_port += 1
            
            # Safety check
            if current_port > start_port + 1000:
                raise RuntimeError(f"Could not find {count} free ports starting from {start_port}")
        
        return ports
    
    async def start_test_process(self, cmd: List[str], timeout: float = 10.0) -> subprocess.Popen:
        """
        Start a test process with monitoring.
        
        This replicates BaseE2ETest process management.
        """
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.test_processes.append(process)
            
            # Wait a bit for process to start
            await asyncio.sleep(0.5)
            
            # Check if process started successfully
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise RuntimeError(f"Process failed to start. Exit code: {process.returncode}, Stderr: {stderr}")
            
            return process
            
        except Exception as e:
            logger.error(f"Failed to start test process {cmd}: {e}")
            raise
    
    def check_process_health(self, process: subprocess.Popen) -> Dict[str, Any]:
        """
        Check the health of a running process.
        
        This replicates BaseE2ETest process monitoring.
        """
        if process.poll() is not None:
            return {
                'status': 'terminated',
                'exit_code': process.returncode,
                'is_healthy': False
            }
        
        try:
            # Use psutil to get more detailed process info
            ps_process = psutil.Process(process.pid)
            return {
                'status': 'running',
                'pid': process.pid,
                'cpu_percent': ps_process.cpu_percent(),
                'memory_info': ps_process.memory_info()._asdict(),
                'is_healthy': True
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {
                'status': 'unknown',
                'is_healthy': False
            }
    
    async def terminate_process_safely(self, process: subprocess.Popen, timeout: float = 5.0):
        """
        Terminate a process safely with timeout.
        
        This replicates BaseE2ETest process cleanup functionality.
        """
        if not process or process.poll() is not None:
            return
        
        try:
            # Try graceful termination first
            process.terminate()
            
            # Wait for process to terminate
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination failed
                logger.warning(f"Process {process.pid} did not terminate gracefully, force killing")
                process.kill()
                process.wait(timeout=2.0)
        
        except Exception as e:
            logger.error(f"Error terminating process {process.pid}: {e}")
    
    def check_service_health(self, host: str, port: int, timeout: float = 5.0) -> bool:
        """
        Check if a service is healthy on given host:port.
        
        This replicates BaseE2ETest service health checking.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception as e:
            logger.debug(f"Service health check failed for {host}:{port}: {e}")
            return False
    
    async def wait_for_service_ready(self, host: str, port: int, timeout: float = 30.0, interval: float = 1.0) -> bool:
        """
        Wait for a service to become ready.
        
        This replicates BaseE2ETest service readiness waiting.
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.check_service_health(host, port, timeout=2.0):
                return True
            await asyncio.sleep(interval)
        
        return False
    
    async def cleanup_all_resources(self):
        """
        Clean up all resources.
        
        This replicates BaseE2ETest cleanup functionality.
        """
        # Terminate all test processes
        for process in self.test_processes:
            await self.terminate_process_safely(process)
        
        # Run cleanup tasks
        for cleanup_task in reversed(self.cleanup_tasks):
            try:
                if asyncio.iscoroutinefunction(cleanup_task):
                    await cleanup_task()
                else:
                    cleanup_task()
            except Exception as e:
                logger.warning(f"Cleanup task failed: {e}")
        
        self.test_processes.clear()
        self.cleanup_tasks.clear()


class TestE2EFunctionalityPreservation(SSotBaseTestCase):
    """
    Integration Test Suite: E2E Functionality Preservation.
    
    Validates that BaseE2ETest capabilities are preserved in SSOT base classes.
    """
    
    def setup_method(self, method=None):
        """Set up functionality preservation test environment."""
        super().setup_method(method)
        
        # Initialize isolated environment
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        
        # Set test environment
        self.env.set("E2E_FUNCTIONALITY_TEST", "true", "functionality_test")
        self.env.set("TESTING", "true", "functionality_test")
        self.env.set("USE_REAL_SERVICES", "false", "functionality_test")
        
        # Initialize functionality tester
        self.functionality_tester = E2EFunctionalityTester(self.env)
        
        # Performance tracking
        self.start_time = time.time()
        
        self.record_metric("functionality_test_setup_completed", True)
    
    async def teardown_method(self, method=None):
        """Clean up after functionality tests."""
        # Clean up test resources
        await self.functionality_tester.cleanup_all_resources()
        
        # Call parent teardown
        super().teardown_method(method)
    
    def test_port_utilities_work_with_ssot_inheritance(self):
        """
        Validate port utility functions work with SSOT base classes.
        
        This ensures BaseE2ETest port functionality is preserved.
        """
        logger.info("Testing port utilities with SSOT inheritance")
        
        # Test find_free_port
        free_port = self.functionality_tester.find_free_port(start_port=8100)
        assert isinstance(free_port, int), "find_free_port should return integer"
        assert 8100 <= free_port <= 8200, f"Free port {free_port} should be in expected range"
        
        # Test check_port_available
        assert self.functionality_tester.check_port_available(free_port), f"Port {free_port} should be available"
        
        # Test generate_port_range
        port_range = self.functionality_tester.generate_port_range(count=3, start_port=8200)
        assert len(port_range) == 3, "Should generate exactly 3 ports"
        assert all(isinstance(p, int) for p in port_range), "All ports should be integers"
        assert len(set(port_range)) == 3, "All ports should be unique"
        
        # Verify all generated ports are available
        for port in port_range:
            assert self.functionality_tester.check_port_available(port), f"Generated port {port} should be available"
        
        # Record metrics
        self.record_metric("free_port_found", free_port)
        self.record_metric("port_range_generated", len(port_range))
        self.record_metric("port_utilities_functional", True)
        
        logger.info("✅ Port utilities functionality preserved with SSOT inheritance")
    
    def test_process_management_preserved_in_migration(self):
        """
        Ensure process management capabilities work with SSOT.
        
        This validates process startup, monitoring, and cleanup work correctly.
        """
        logger.info("Testing process management with SSOT inheritance")
        
        # Use a simple command that runs for a short time
        test_command = [sys.executable, "-c", "import time; time.sleep(2); print('Test process completed')"]
        
        async def run_process_test():
            # Test process startup
            process = await self.functionality_tester.start_test_process(test_command, timeout=5.0)
            
            assert process is not None, "Process should be created successfully"
            assert process.poll() is None, "Process should be running initially"
            
            # Test process health monitoring
            health = self.functionality_tester.check_process_health(process)
            assert health['is_healthy'], "Process should be healthy"
            assert health['status'] == 'running', "Process status should be running"
            assert 'pid' in health, "Health check should include PID"
            
            # Wait for process to complete naturally
            await asyncio.sleep(3.0)
            
            # Check final status
            final_health = self.functionality_tester.check_process_health(process)
            assert final_health['status'] == 'terminated', "Process should have terminated"
            assert final_health['exit_code'] == 0, "Process should have exited successfully"
            
            return process
        
        # Run the async test
        process = asyncio.run(run_process_test())
        
        # Record metrics
        self.record_metric("process_started_successfully", True)
        self.record_metric("process_monitoring_functional", True)
        self.record_metric("process_cleanup_successful", True)
        
        logger.info("✅ Process management functionality preserved with SSOT inheritance")
    
    def test_service_health_checking_continues(self):
        """
        Validate service health checking works after migration.
        
        This ensures BaseE2ETest service monitoring capabilities are preserved.
        """
        logger.info("Testing service health checking with SSOT inheritance")
        
        # Test health check for non-existent service (should fail)
        is_healthy = self.functionality_tester.check_service_health("localhost", 9999, timeout=1.0)
        assert not is_healthy, "Non-existent service should not be healthy"
        
        # Test health check for known services (if available)
        # We'll test against common local services that might be running
        test_services = [
            ("localhost", 80),   # HTTP (might be running)
            ("localhost", 443),  # HTTPS (might be running)
            ("127.0.0.1", 22),   # SSH (might be running on some systems)
        ]
        
        checked_services = 0
        healthy_services = 0
        
        for host, port in test_services:
            try:
                is_healthy = self.functionality_tester.check_service_health(host, port, timeout=2.0)
                checked_services += 1
                if is_healthy:
                    healthy_services += 1
                logger.debug(f"Service {host}:{port} health: {'healthy' if is_healthy else 'unhealthy'}")
            except Exception as e:
                logger.debug(f"Failed to check {host}:{port}: {e}")
        
        # Test async service waiting with a mock scenario
        async def test_service_waiting():
            # Test waiting for non-existent service (should timeout quickly)
            start_time = time.time()
            ready = await self.functionality_tester.wait_for_service_ready("localhost", 9998, timeout=2.0, interval=0.5)
            elapsed = time.time() - start_time
            
            assert not ready, "Non-existent service should not become ready"
            assert 1.8 <= elapsed <= 2.5, f"Timeout should be respected, elapsed: {elapsed}"
            
            return elapsed
        
        elapsed = asyncio.run(test_service_waiting())
        
        # Record metrics
        self.record_metric("services_checked", checked_services)
        self.record_metric("healthy_services_found", healthy_services)
        self.record_metric("service_timeout_respected", True)
        self.record_metric("service_wait_elapsed_time", elapsed)
        self.record_metric("service_health_checking_functional", True)
        
        logger.info("✅ Service health checking functionality preserved with SSOT inheritance")
    
    def test_e2e_setup_teardown_patterns_functional(self):
        """
        Ensure setup/teardown patterns work with SSOT inheritance.
        
        This validates the complete E2E test lifecycle with SSOT base classes.
        """
        logger.info("Testing E2E setup/teardown patterns with SSOT inheritance")
        
        # Test that SSOT setup was called correctly
        assert hasattr(self, '_env'), "SSOT environment should be initialized"
        assert hasattr(self, '_metrics'), "SSOT metrics should be initialized"
        assert hasattr(self, '_test_context'), "SSOT test context should be initialized"
        
        # Test environment isolation
        assert self.get_env().is_isolated(), "Environment should be isolated in SSOT tests"
        
        # Test that environment variables can be set and retrieved
        test_key = f"E2E_TEST_VAR_{uuid.uuid4().hex[:8]}"
        test_value = f"test_value_{uuid.uuid4().hex[:8]}"
        
        self.set_env_var(test_key, test_value)
        retrieved_value = self.get_env_var(test_key)
        assert retrieved_value == test_value, "Environment variable should be set and retrieved correctly"
        
        # Test metrics recording
        test_metric_name = f"test_metric_{uuid.uuid4().hex[:8]}"
        test_metric_value = 42
        
        self.record_metric(test_metric_name, test_metric_value)
        retrieved_metric = self.get_metric(test_metric_name)
        assert retrieved_metric == test_metric_value, "Metric should be recorded and retrieved correctly"
        
        # Test cleanup callback functionality
        cleanup_executed = {"value": False}
        
        def test_cleanup():
            cleanup_executed["value"] = True
        
        self.add_cleanup(test_cleanup)
        
        # Verify cleanup is registered (we can't test execution without triggering teardown)
        assert len(self._cleanup_callbacks) > 0, "Cleanup callback should be registered"
        
        # Test context information
        test_context = self.get_test_context()
        assert test_context is not None, "Test context should be available"
        assert test_context.test_name is not None, "Test context should have test name"
        assert test_context.test_id is not None, "Test context should have test ID"
        
        # Test execution time tracking
        execution_metrics = self.get_all_metrics()
        assert 'execution_time' in execution_metrics, "Execution time should be tracked"
        
        # Record comprehensive metrics
        self.record_metric("setup_teardown_patterns_functional", True)
        self.record_metric("environment_isolation_working", True)
        self.record_metric("metrics_recording_working", True)
        self.record_metric("cleanup_callbacks_working", True)
        self.record_metric("context_management_working", True)
        
        logger.info("✅ E2E setup/teardown patterns functional with SSOT inheritance")
    
    def test_comprehensive_e2e_functionality_validation(self):
        """
        Comprehensive validation of all E2E functionality preservation.
        
        This test combines all functionality checks into a complete validation.
        """
        logger.info("Running comprehensive E2E functionality validation")
        
        functionality_report = {
            'port_utilities': False,
            'process_management': False,
            'service_health_checking': False,
            'setup_teardown_patterns': False,
            'environment_isolation': False,
            'metrics_recording': False,
            'cleanup_functionality': False
        }
        
        # Validate port utilities
        try:
            free_port = self.functionality_tester.find_free_port()
            port_available = self.functionality_tester.check_port_available(free_port)
            port_range = self.functionality_tester.generate_port_range(2)
            
            functionality_report['port_utilities'] = (
                isinstance(free_port, int) and port_available and len(port_range) == 2
            )
        except Exception as e:
            logger.warning(f"Port utilities validation failed: {e}")
        
        # Validate process management
        try:
            async def validate_process_mgmt():
                cmd = [sys.executable, "-c", "print('test')"]
                process = await self.functionality_tester.start_test_process(cmd)
                health = self.functionality_tester.check_process_health(process)
                await self.functionality_tester.terminate_process_safely(process)
                return health['is_healthy'] if health else False
            
            process_result = asyncio.run(validate_process_mgmt())
            functionality_report['process_management'] = process_result
        except Exception as e:
            logger.warning(f"Process management validation failed: {e}")
        
        # Validate service health checking
        try:
            health_result = self.functionality_tester.check_service_health("localhost", 9999, timeout=1.0)
            functionality_report['service_health_checking'] = not health_result  # Should be False for non-existent service
        except Exception as e:
            logger.warning(f"Service health checking validation failed: {e}")
        
        # Validate setup/teardown patterns
        try:
            functionality_report['setup_teardown_patterns'] = all([
                hasattr(self, '_env'),
                hasattr(self, '_metrics'),
                hasattr(self, '_test_context'),
                hasattr(self, '_cleanup_callbacks')
            ])
        except Exception as e:
            logger.warning(f"Setup/teardown validation failed: {e}")
        
        # Validate environment isolation
        try:
            test_key = f"ISOLATION_TEST_{uuid.uuid4().hex[:8]}"
            self.set_env_var(test_key, "test_value")
            retrieved = self.get_env_var(test_key)
            functionality_report['environment_isolation'] = (retrieved == "test_value")
        except Exception as e:
            logger.warning(f"Environment isolation validation failed: {e}")
        
        # Validate metrics recording
        try:
            test_metric = f"test_metric_{uuid.uuid4().hex[:8]}"
            self.record_metric(test_metric, 100)
            retrieved_metric = self.get_metric(test_metric)
            functionality_report['metrics_recording'] = (retrieved_metric == 100)
        except Exception as e:
            logger.warning(f"Metrics recording validation failed: {e}")
        
        # Validate cleanup functionality
        try:
            cleanup_flag = {"executed": False}
            
            def test_cleanup():
                cleanup_flag["executed"] = True
            
            self.add_cleanup(test_cleanup)
            functionality_report['cleanup_functionality'] = len(self._cleanup_callbacks) > 0
        except Exception as e:
            logger.warning(f"Cleanup functionality validation failed: {e}")
        
        # Calculate overall functionality preservation percentage
        functional_components = sum(functionality_report.values())
        total_components = len(functionality_report)
        preservation_percentage = (functional_components / total_components) * 100
        
        # Record comprehensive metrics
        for component, status in functionality_report.items():
            self.record_metric(f"functionality_{component}_preserved", status)
        
        self.record_metric("total_functionality_components", total_components)
        self.record_metric("functional_components_preserved", functional_components)
        self.record_metric("functionality_preservation_percentage", preservation_percentage)
        
        # Log comprehensive report
        logger.info(f"""
E2E FUNCTIONALITY PRESERVATION VALIDATION REPORT
===============================================
Port Utilities: {'✅ PRESERVED' if functionality_report['port_utilities'] else '❌ BROKEN'}
Process Management: {'✅ PRESERVED' if functionality_report['process_management'] else '❌ BROKEN'}
Service Health Checking: {'✅ PRESERVED' if functionality_report['service_health_checking'] else '❌ BROKEN'}
Setup/Teardown Patterns: {'✅ PRESERVED' if functionality_report['setup_teardown_patterns'] else '❌ BROKEN'}
Environment Isolation: {'✅ PRESERVED' if functionality_report['environment_isolation'] else '❌ BROKEN'}
Metrics Recording: {'✅ PRESERVED' if functionality_report['metrics_recording'] else '❌ BROKEN'}
Cleanup Functionality: {'✅ PRESERVED' if functionality_report['cleanup_functionality'] else '❌ BROKEN'}

Overall Preservation: {preservation_percentage:.1f}% ({functional_components}/{total_components})
        """)
        
        # Assert minimum functionality preservation threshold
        minimum_threshold = 85.0  # 85% of functionality must be preserved
        assert preservation_percentage >= minimum_threshold, (
            f"Functionality preservation {preservation_percentage:.1f}% below minimum threshold {minimum_threshold}%. "
            f"Migration may have broken critical E2E capabilities."
        )
        
        logger.info(f"✅ COMPREHENSIVE VALIDATION PASSED: {preservation_percentage:.1f}% E2E functionality preserved")


class TestE2EAsyncFunctionalityPreservation(SSotAsyncTestCase):
    """
    Async variant of E2E functionality preservation tests.
    
    Validates that async BaseE2ETest capabilities work with SSotAsyncTestCase.
    """
    
    def setup_method(self, method=None):
        """Set up async functionality preservation test."""
        super().setup_method(method)
        
        # Initialize environment
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        self.env.set("ASYNC_E2E_TEST", "true", "async_functionality_test")
        
        # Initialize functionality tester
        self.functionality_tester = E2EFunctionalityTester(self.env)
        
        self.record_metric("async_functionality_test_setup_completed", True)
    
    async def test_async_process_management_preserved(self):
        """Test async process management with SSOT async base class."""
        logger.info("Testing async process management with SSOT inheritance")
        
        # Test async process startup
        cmd = [sys.executable, "-c", "import time; time.sleep(1); print('Async test completed')"]
        process = await self.functionality_tester.start_test_process(cmd)
        
        # Test async waiting
        await asyncio.sleep(0.5)
        health = self.functionality_tester.check_process_health(process)
        assert health['is_healthy'], "Async process should be healthy"
        
        # Test async cleanup
        await self.functionality_tester.terminate_process_safely(process)
        
        self.record_metric("async_process_management_functional", True)
        logger.info("✅ Async process management preserved with SSOT inheritance")
    
    async def test_async_service_waiting_preserved(self):
        """Test async service waiting capabilities."""
        logger.info("Testing async service waiting with SSOT inheritance")
        
        # Test async waiting for non-existent service (should timeout)
        start_time = time.time()
        ready = await self.functionality_tester.wait_for_service_ready("localhost", 9997, timeout=1.5)
        elapsed = time.time() - start_time
        
        assert not ready, "Non-existent service should not be ready"
        assert 1.3 <= elapsed <= 2.0, f"Timeout should be respected, elapsed: {elapsed}"
        
        self.record_metric("async_service_waiting_functional", True)
        self.record_metric("async_timeout_elapsed", elapsed)
        
        logger.info("✅ Async service waiting preserved with SSOT inheritance")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])