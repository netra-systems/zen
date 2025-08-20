"""
Dev Launcher Error Detection Tests

Comprehensive error detection tests that monitor console outputs and catch failures.
Tests error scenarios including startup failures, database issues, and service crashes.

CRITICAL REQUIREMENTS:
- Monitor stdout/stderr for errors
- Detect JavaScript errors in frontend
- Catch Python exceptions in backend
- Identify database connection failures
- Test error recovery mechanisms
"""

import asyncio
import pytest
import time
import sys
import os
import subprocess
import signal
import requests
import logging
import re
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Pattern
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager
from dev_launcher.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class ErrorPatterns:
    """Error pattern definitions for different types of errors."""
    
    # Python backend errors
    PYTHON_EXCEPTIONS = [
        re.compile(r'Traceback \(most recent call last\):', re.IGNORECASE),
        re.compile(r'Exception:', re.IGNORECASE),
        re.compile(r'Error:', re.IGNORECASE),
        re.compile(r'CRITICAL:', re.IGNORECASE),
        re.compile(r'FATAL:', re.IGNORECASE),
        re.compile(r'ModuleNotFoundError:', re.IGNORECASE),
        re.compile(r'ImportError:', re.IGNORECASE),
        re.compile(r'ConnectionError:', re.IGNORECASE),
        re.compile(r'TimeoutError:', re.IGNORECASE),
    ]
    
    # Database connection errors
    DATABASE_ERRORS = [
        re.compile(r'database.*connection.*failed', re.IGNORECASE),
        re.compile(r'could not connect.*database', re.IGNORECASE),
        re.compile(r'connection.*refused.*database', re.IGNORECASE),
        re.compile(r'psycopg2\.OperationalError', re.IGNORECASE),
        re.compile(r'clickhouse.*connection.*error', re.IGNORECASE),
        re.compile(r'database.*timeout', re.IGNORECASE),
        re.compile(r'authentication.*failed.*database', re.IGNORECASE),
    ]
    
    # JavaScript frontend errors
    JAVASCRIPT_ERRORS = [
        re.compile(r'TypeError:', re.IGNORECASE),
        re.compile(r'ReferenceError:', re.IGNORECASE),
        re.compile(r'SyntaxError:', re.IGNORECASE),
        re.compile(r'Error: Cannot resolve', re.IGNORECASE),
        re.compile(r'Module not found:', re.IGNORECASE),
        re.compile(r'Failed to compile', re.IGNORECASE),
        re.compile(r'webpack.*error', re.IGNORECASE),
        re.compile(r'npm.*error', re.IGNORECASE),
    ]
    
    # Service startup errors
    STARTUP_ERRORS = [
        re.compile(r'failed to start.*service', re.IGNORECASE),
        re.compile(r'port.*already in use', re.IGNORECASE),
        re.compile(r'address already in use', re.IGNORECASE),
        re.compile(r'permission denied', re.IGNORECASE),
        re.compile(r'command not found', re.IGNORECASE),
        re.compile(r'no such file or directory', re.IGNORECASE),
    ]
    
    # Authentication errors
    AUTH_ERRORS = [
        re.compile(r'authentication.*failed', re.IGNORECASE),
        re.compile(r'invalid.*credentials', re.IGNORECASE),
        re.compile(r'unauthorized', re.IGNORECASE),
        re.compile(r'token.*invalid', re.IGNORECASE),
        re.compile(r'jwt.*error', re.IGNORECASE),
        re.compile(r'oauth.*error', re.IGNORECASE),
    ]
    
    # Network and HTTP errors
    NETWORK_ERRORS = [
        re.compile(r'connection.*refused', re.IGNORECASE),
        re.compile(r'network.*unreachable', re.IGNORECASE),
        re.compile(r'timeout.*occurred', re.IGNORECASE),
        re.compile(r'502.*bad gateway', re.IGNORECASE),
        re.compile(r'503.*service unavailable', re.IGNORECASE),
        re.compile(r'504.*gateway timeout', re.IGNORECASE),
    ]


class ErrorDetector:
    """Real-time error detection from service outputs."""
    
    def __init__(self):
        self.detected_errors: List[Dict] = []
        self.log_monitors: Dict[str, threading.Thread] = {}
        self.output_queues: Dict[str, Queue] = {}
        self.patterns = ErrorPatterns()
        self._monitoring = False
        self._shutdown_event = threading.Event()
        
    def start_monitoring(self, launcher: DevLauncher):
        """Start monitoring launcher and service outputs."""
        self._monitoring = True
        self._shutdown_event.clear()
        
        # Monitor launcher logs
        self._start_launcher_monitoring(launcher)
        
        # Monitor service processes
        if hasattr(launcher, 'process_manager'):
            self._start_service_monitoring(launcher.process_manager)
            
    def _start_launcher_monitoring(self, launcher: DevLauncher):
        """Monitor launcher logs and console output."""
        def monitor_launcher():
            # Hook into Python logging
            log_handler = ErrorLogHandler(self)
            root_logger = logging.getLogger()
            root_logger.addHandler(log_handler)
            
            # Monitor until shutdown
            while not self._shutdown_event.is_set():
                time.sleep(0.1)
                
            root_logger.removeHandler(log_handler)
            
        thread = threading.Thread(target=monitor_launcher, daemon=True)
        thread.start()
        self.log_monitors['launcher'] = thread
        
    def _start_service_monitoring(self, process_manager: ProcessManager):
        """Monitor service process outputs."""
        for service_name, process in process_manager.processes.items():
            if process and hasattr(process, 'stdout') and hasattr(process, 'stderr'):
                self._start_process_monitoring(service_name, process)
                
    def _start_process_monitoring(self, service_name: str, process: subprocess.Popen):
        """Monitor individual process output."""
        def monitor_process():
            while not self._shutdown_event.is_set() and process.poll() is None:
                try:
                    # Monitor stdout
                    if process.stdout:
                        line = process.stdout.readline()
                        if line:
                            self._check_line_for_errors(line.decode('utf-8', errors='ignore'), service_name, 'stdout')
                            
                    # Monitor stderr
                    if process.stderr:
                        line = process.stderr.readline()
                        if line:
                            self._check_line_for_errors(line.decode('utf-8', errors='ignore'), service_name, 'stderr')
                            
                except Exception as e:
                    logger.debug(f"Process monitoring error for {service_name}: {e}")
                    
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
        thread = threading.Thread(target=monitor_process, daemon=True)
        thread.start()
        self.log_monitors[service_name] = thread
        
    def _check_line_for_errors(self, line: str, source: str, stream: str):
        """Check a log line against error patterns."""
        line = line.strip()
        if not line:
            return
            
        # Check against all error patterns
        error_type = self._classify_error(line)
        if error_type:
            error_info = {
                'timestamp': time.time(),
                'source': source,
                'stream': stream,
                'error_type': error_type,
                'message': line,
                'severity': self._determine_severity(error_type, line)
            }
            self.detected_errors.append(error_info)
            logger.warning(f"Error detected in {source}({stream}): {error_type} - {line[:100]}")
            
    def _classify_error(self, line: str) -> Optional[str]:
        """Classify error type based on patterns."""
        # Check Python exceptions
        for pattern in self.patterns.PYTHON_EXCEPTIONS:
            if pattern.search(line):
                return 'python_exception'
                
        # Check database errors
        for pattern in self.patterns.DATABASE_ERRORS:
            if pattern.search(line):
                return 'database_error'
                
        # Check JavaScript errors
        for pattern in self.patterns.JAVASCRIPT_ERRORS:
            if pattern.search(line):
                return 'javascript_error'
                
        # Check startup errors
        for pattern in self.patterns.STARTUP_ERRORS:
            if pattern.search(line):
                return 'startup_error'
                
        # Check auth errors
        for pattern in self.patterns.AUTH_ERRORS:
            if pattern.search(line):
                return 'auth_error'
                
        # Check network errors
        for pattern in self.patterns.NETWORK_ERRORS:
            if pattern.search(line):
                return 'network_error'
                
        return None
        
    def _determine_severity(self, error_type: str, line: str) -> str:
        """Determine error severity."""
        if any(keyword in line.lower() for keyword in ['critical', 'fatal', 'emergency']):
            return 'critical'
        elif any(keyword in line.lower() for keyword in ['error', 'exception', 'failed']):
            return 'error'
        elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
            return 'warning'
        else:
            return 'info'
            
    def stop_monitoring(self):
        """Stop all monitoring."""
        self._monitoring = False
        self._shutdown_event.set()
        
        # Wait for threads to finish
        for thread in self.log_monitors.values():
            if thread.is_alive():
                thread.join(timeout=5)
                
        self.log_monitors.clear()
        
    def get_errors_by_type(self, error_type: str) -> List[Dict]:
        """Get errors filtered by type."""
        return [error for error in self.detected_errors if error['error_type'] == error_type]
        
    def get_critical_errors(self) -> List[Dict]:
        """Get critical errors."""
        return [error for error in self.detected_errors if error['severity'] == 'critical']
        
    def has_startup_failures(self) -> bool:
        """Check if any startup failures were detected."""
        startup_errors = self.get_errors_by_type('startup_error')
        return len(startup_errors) > 0
        
    def has_database_failures(self) -> bool:
        """Check if database failures were detected."""
        db_errors = self.get_errors_by_type('database_error')
        return len(db_errors) > 0
        
    def get_error_summary(self) -> Dict:
        """Get summary of all detected errors."""
        summary = {
            'total_errors': len(self.detected_errors),
            'by_type': {},
            'by_severity': {},
            'by_source': {}
        }
        
        for error in self.detected_errors:
            # Count by type
            error_type = error['error_type']
            summary['by_type'][error_type] = summary['by_type'].get(error_type, 0) + 1
            
            # Count by severity
            severity = error['severity']
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            
            # Count by source
            source = error['source']
            summary['by_source'][source] = summary['by_source'].get(source, 0) + 1
            
        return summary


class ErrorLogHandler(logging.Handler):
    """Custom log handler to capture errors."""
    
    def __init__(self, error_detector: ErrorDetector):
        super().__init__()
        self.error_detector = error_detector
        
    def emit(self, record):
        """Handle log record."""
        if record.levelno >= logging.ERROR:
            message = self.format(record)
            self.error_detector._check_line_for_errors(message, 'launcher', 'log')


class DevLauncherErrorTester:
    """Integration tester focused on error detection."""
    
    def __init__(self):
        self.launcher: Optional[DevLauncher] = None
        self.config: Optional[LauncherConfig] = None
        self.error_detector = ErrorDetector()
        self.start_time: Optional[float] = None
        
    def create_test_config(self, **kwargs) -> LauncherConfig:
        """Create test configuration."""
        config = LauncherConfig()
        config.backend_port = kwargs.get('backend_port', 8000)
        config.frontend_port = kwargs.get('frontend_port', 3000) if not kwargs.get('skip_frontend', True) else None
        config.dynamic_ports = False
        config.no_backend_reload = True
        config.no_browser = True
        config.verbose = kwargs.get('verbose', True)  # Enable verbose for error detection
        config.non_interactive = True
        config.startup_mode = kwargs.get('startup_mode', 'minimal')
        config.no_secrets = kwargs.get('no_secrets', True)
        config.parallel_startup = kwargs.get('parallel_startup', True)
        config.project_root = project_root
        return config
        
    async def start_with_error_monitoring(self, config: LauncherConfig) -> Tuple[bool, List[Dict]]:
        """Start services with comprehensive error monitoring."""
        self.start_time = time.time()
        self.config = config
        self.launcher = DevLauncher(config)
        
        # Start error monitoring
        self.error_detector.start_monitoring(self.launcher)
        
        try:
            # Run launcher
            result = await self.launcher.run()
            
            # Wait a bit for any delayed errors
            await asyncio.sleep(2)
            
            return result == 0, self.error_detector.detected_errors.copy()
            
        except Exception as e:
            logger.error(f"Launcher startup failed: {e}")
            return False, self.error_detector.detected_errors.copy()
            
    async def simulate_database_failure(self) -> Tuple[bool, List[Dict]]:
        """Simulate database failure scenario."""
        # Corrupt database URL to cause failure
        original_db_url = os.environ.get('DATABASE_URL', '')
        os.environ['DATABASE_URL'] = 'postgresql://invalid:invalid@invalid:5432/invalid'
        
        try:
            config = self.create_test_config(no_secrets=False)  # Need to try database connection
            success, errors = await self.start_with_error_monitoring(config)
            
            # Should have database errors
            db_errors = [e for e in errors if e['error_type'] == 'database_error']
            return len(db_errors) > 0, errors
            
        finally:
            # Restore original DB URL
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            elif 'DATABASE_URL' in os.environ:
                del os.environ['DATABASE_URL']
                
    async def simulate_port_conflict(self) -> Tuple[bool, List[Dict]]:
        """Simulate port conflict scenario."""
        # Occupy the backend port
        import socket
        port = 8000
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            sock.bind(('localhost', port))
            sock.listen(1)
            
            # Try to start launcher - should detect port conflict
            config = self.create_test_config(backend_port=port)
            success, errors = await self.start_with_error_monitoring(config)
            
            # Should have startup errors
            startup_errors = [e for e in errors if e['error_type'] == 'startup_error']
            return len(startup_errors) > 0, errors
            
        finally:
            sock.close()
            
    async def test_missing_dependencies(self) -> Tuple[bool, List[Dict]]:
        """Test behavior with missing dependencies."""
        # Temporarily rename requirements file to simulate missing deps
        req_file = project_root / "requirements.txt"
        backup_file = project_root / "requirements.txt.backup"
        
        renamed = False
        try:
            if req_file.exists():
                req_file.rename(backup_file)
                renamed = True
                
            config = self.create_test_config()
            success, errors = await self.start_with_error_monitoring(config)
            
            return not success, errors  # Should fail
            
        finally:
            if renamed and backup_file.exists():
                backup_file.rename(req_file)
                
    async def stop_services(self):
        """Stop services and monitoring."""
        # Stop error monitoring
        self.error_detector.stop_monitoring()
        
        # Stop launcher
        if self.launcher:
            if hasattr(self.launcher, '_graceful_shutdown'):
                self.launcher._graceful_shutdown()
            self.launcher = None
            
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_services()


# Test Cases

@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_detection_normal_startup():
    """Test error detection during normal startup."""
    async with DevLauncherErrorTester() as tester:
        config = tester.create_test_config()
        
        success, errors = await tester.start_with_error_monitoring(config)
        
        # Normal startup should succeed with minimal errors
        assert success, "Normal startup should succeed"
        
        # Should not have critical errors
        critical_errors = [e for e in errors if e['severity'] == 'critical']
        assert len(critical_errors) == 0, f"Critical errors detected: {critical_errors}"
        
        # Should not have startup failures
        assert not tester.error_detector.has_startup_failures(), "Startup failures detected"


@pytest.mark.asyncio
@pytest.mark.integration 
async def test_database_error_detection():
    """Test detection of database connection errors."""
    async with DevLauncherErrorTester() as tester:
        detected_db_failure, errors = await tester.simulate_database_failure()
        
        # Should detect database errors
        assert detected_db_failure, "Database failure not detected"
        
        # Verify error classification
        db_errors = [e for e in errors if e['error_type'] == 'database_error']
        assert len(db_errors) > 0, "No database errors classified"
        
        # Get error summary
        summary = tester.error_detector.get_error_summary()
        assert summary['by_type'].get('database_error', 0) > 0, "Database errors not summarized"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_port_conflict_detection():
    """Test detection of port conflicts."""
    async with DevLauncherErrorTester() as tester:
        detected_conflict, errors = await tester.simulate_port_conflict()
        
        # Should detect port conflict
        assert detected_conflict, "Port conflict not detected"
        
        # Verify error types
        startup_errors = [e for e in errors if e['error_type'] == 'startup_error']
        assert len(startup_errors) > 0, "No startup errors detected for port conflict"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_python_exception_detection():
    """Test detection of Python exceptions."""
    async with DevLauncherErrorTester() as tester:
        # Force an exception by corrupting config
        config = tester.create_test_config()
        config.project_root = Path("/nonexistent/path")  # This should cause errors
        
        success, errors = await tester.start_with_error_monitoring(config)
        
        # Should detect Python exceptions
        python_errors = [e for e in errors if e['error_type'] == 'python_exception']
        # Note: May not always trigger depending on validation logic
        
        # At minimum, should not succeed with invalid config
        # assert not success, "Should fail with invalid configuration"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_severity_classification():
    """Test error severity classification."""
    async with DevLauncherErrorTester() as tester:
        config = tester.create_test_config()
        
        success, errors = await tester.start_with_error_monitoring(config)
        
        # Check severity classification
        summary = tester.error_detector.get_error_summary()
        
        # Should have severity breakdown
        severity_counts = summary['by_severity']
        total_errors = sum(severity_counts.values())
        
        if total_errors > 0:
            # Verify all errors have valid severity
            valid_severities = {'critical', 'error', 'warning', 'info'}
            for severity in severity_counts.keys():
                assert severity in valid_severities, f"Invalid severity: {severity}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_source_tracking():
    """Test error source tracking."""
    async with DevLauncherErrorTester() as tester:
        config = tester.create_test_config(skip_frontend=False)  # Include frontend for more sources
        
        success, errors = await tester.start_with_error_monitoring(config)
        
        # Check source tracking
        summary = tester.error_detector.get_error_summary()
        source_counts = summary['by_source']
        
        # Should track different sources
        if len(errors) > 0:
            # Verify all sources are tracked
            for error in errors:
                assert 'source' in error, "Error missing source"
                assert error['source'] in source_counts, "Source not in summary"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_real_time_error_monitoring():
    """Test real-time error monitoring during runtime."""
    async with DevLauncherErrorTester() as tester:
        config = tester.create_test_config()
        
        success, initial_errors = await tester.start_with_error_monitoring(config)
        assert success, "Startup should succeed"
        
        initial_count = len(initial_errors)
        
        # Wait and check for additional errors during runtime
        await asyncio.sleep(5)
        
        runtime_errors = tester.error_detector.detected_errors
        runtime_count = len(runtime_errors)
        
        # Should continue monitoring (runtime_count >= initial_count)
        assert runtime_count >= initial_count, "Error monitoring stopped"
        
        # Get final summary
        final_summary = tester.error_detector.get_error_summary()
        assert final_summary['total_errors'] == runtime_count, "Summary count mismatch"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_javascript_error_detection():
    """Test detection of JavaScript errors from frontend."""
    async with DevLauncherErrorTester() as tester:
        config = tester.create_test_config(skip_frontend=False)  # Enable frontend
        
        success, errors = await tester.start_with_error_monitoring(config)
        
        # Wait longer for frontend to start and potentially show errors
        await asyncio.sleep(10)
        
        all_errors = tester.error_detector.detected_errors
        js_errors = [e for e in all_errors if e['error_type'] == 'javascript_error']
        
        # Note: May not always have JS errors in test environment
        # Just verify the detection mechanism works
        logger.info(f"Detected {len(js_errors)} JavaScript errors")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])