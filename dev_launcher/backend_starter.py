"""
Backend service startup management.
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from dev_launcher.config import LauncherConfig, resolve_path
from dev_launcher.log_streamer import Colors, LogManager, LogStreamer
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.utils import (
    create_process_env,
    create_subprocess,
    get_free_port,
    print_with_emoji,
)

logger = logging.getLogger(__name__)


class BackendStarter:
    """
    Handles backend service startup.
    
    Manages backend server startup with proper configuration,
    environment setup, and error handling.
    """
    
    def __init__(self, config: LauncherConfig, services_config, 
                 log_manager: LogManager, service_discovery: ServiceDiscovery,
                 use_emoji: bool = True):
        """Initialize backend starter."""
        self.config = config
        self.services_config = services_config
        self.log_manager = log_manager
        self.service_discovery = service_discovery
        self.use_emoji = use_emoji
        self.backend_health_info = None
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def start_backend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the backend server."""
        # Build service mode description
        from dev_launcher.service_config import ResourceMode
        service_modes = []
        
        # Check each service mode
        services = [
            ("Redis", self.services_config.redis),
            ("ClickHouse", self.services_config.clickhouse),
            ("PostgreSQL", self.services_config.postgres),
            ("LLM", self.services_config.llm)
        ]
        
        for name, service in services:
            if service.mode == ResourceMode.LOCAL:
                service_modes.append(f"{name}:local")
            elif service.mode == ResourceMode.SHARED:
                service_modes.append(f"{name}:cloud")
            elif service.mode == ResourceMode.DOCKER:
                service_modes.append(f"{name}:docker")
            elif service.mode == ResourceMode.DISABLED:
                service_modes.append(f"{name}:disabled")
        
        mode_str = ", ".join(service_modes) if service_modes else "default configuration"
        self._print("[U+1F680]", "BACKEND", f"Starting backend server ({mode_str})...")
        
        port = self._determine_backend_port()
        server_script = self._find_server_script()
        cmd = self._build_backend_command(port, server_script)
        env = self._create_backend_env(port)
        return self._start_backend_process(cmd, env, port)
    
    def _determine_backend_port(self) -> int:
        """Determine backend port."""
        if self.config.dynamic_ports:
            port = self._allocate_dynamic_backend_port()
        else:
            port = self.config.backend_port or 8000
        self.config.backend_port = port
        return port
    
    def _allocate_dynamic_backend_port(self) -> int:
        """Allocate dynamic backend port."""
        # CRITICAL FIX: Always try port 8000 first for frontend consistency
        from dev_launcher.utils import is_port_available
        
        # Force port 8000 if available
        if is_port_available(8000):
            logger.info(f"Using preferred backend port: 8000")
            return 8000
        
        # Only use dynamic allocation if 8000 is truly unavailable
        from dev_launcher.utils import find_available_port
        port = find_available_port(8001, (8001, 8010))
        logger.warning(f"Port 8000 unavailable, allocated backend port: {port}")
        logger.warning(f"Frontend may fail to connect - port mismatch detected!")
        return port
    
    def _find_server_script(self) -> Optional[Path]:
        """Find appropriate server script."""
        run_server_enhanced = resolve_path("scripts", "run_server_enhanced.py", 
                                         root=self.config.project_root)
        if run_server_enhanced and run_server_enhanced.exists():
            logger.info("Using enhanced server with health monitoring")
            return run_server_enhanced
        return self._find_fallback_server_script()
    
    def _find_fallback_server_script(self) -> Optional[Path]:
        """Find fallback server script."""
        run_server_path = resolve_path("scripts", "run_server.py", 
                                     root=self.config.project_root)
        if run_server_path and run_server_path.exists():
            return run_server_path
        logger.info("Using direct uvicorn launch")
        return None
    
    def _build_backend_command(self, port: int, server_script: Optional[Path]) -> list:
        """Build backend command."""
        if server_script:
            cmd = self._build_script_command(port, server_script)
        else:
            cmd = self._build_uvicorn_command(port)
        self._add_backend_flags(cmd, server_script)
        logger.debug(f"Backend command: {' '.join(cmd)}")
        return cmd
    
    def _build_script_command(self, port: int, server_script: Path) -> list:
        """Build script-based command."""
        return [sys.executable, str(server_script), "--port", str(port)]
    
    def _build_uvicorn_command(self, port: int) -> list:
        """Build uvicorn command."""
        # Windows compatibility: Change to netra_backend directory and use app.main:app
        # This avoids module import issues on Windows
        backend_dir = resolve_path("netra_backend", root=self.config.project_root)
        if backend_dir and backend_dir.exists():
            # Run from within netra_backend directory
            os.chdir(backend_dir)
            return [sys.executable, "-m", "uvicorn", "app.main:app", 
                    "--host", "0.0.0.0", "--port", str(port), 
                    "--log-level", "warning"]
        else:
            # Fallback to original approach
            return [sys.executable, "-m", "uvicorn", "netra_backend.app.main:app", 
                    "--host", "0.0.0.0", "--port", str(port), 
                    "--log-level", "warning"]
    
    def _add_backend_flags(self, cmd: list, server_script: Optional[Path]):
        """Add backend command flags."""
        self._add_reload_flag(cmd, server_script)
        self._add_verbose_flag(cmd, server_script)
    
    def _add_reload_flag(self, cmd: list, server_script: Optional[Path]):
        """Add reload flag."""
        if not self.config.backend_reload:
            self._add_no_reload_flag(cmd, server_script)
        else:
            self._add_enable_reload_flag(cmd, server_script)
    
    def _add_no_reload_flag(self, cmd: list, server_script: Optional[Path]):
        """Add no-reload flag."""
        if server_script:
            cmd.append("--no-reload")
        logger.info("Backend hot reload: DISABLED")
    
    def _add_enable_reload_flag(self, cmd: list, server_script: Optional[Path]):
        """Add enable reload flag."""
        if not server_script:
            cmd.append("--reload")
        logger.info("Backend hot reload: ENABLED (uvicorn native)")
    
    def _add_verbose_flag(self, cmd: list, server_script: Optional[Path]):
        """Add verbose flag."""
        if self.config.verbose and server_script:
            cmd.append("--verbose")
    
    def _create_backend_env(self, port: int) -> dict:
        """Create backend environment variables."""
        service_env_vars = self.services_config.get_all_env_vars()
        
        # Debug logging for mock mode
        if hasattr(self.services_config, 'postgres') and self.services_config.postgres.mode.value == "mock":
            logger.info(f"Backend starting in mock mode - DATABASE_URL: {service_env_vars.get('DATABASE_URL', 'NOT_SET')}")
        
        return create_process_env(
            BACKEND_PORT=str(port),
            PYTHONPATH=str(self.config.project_root),
            ENVIRONMENT="development",
            CORS_ORIGINS="*",
            **service_env_vars,
            **self.config.env_overrides
        )
    
    def _start_backend_process(self, cmd: list, env: dict, port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start backend process."""
        self._prepare_backend_logging()
        try:
            process = create_subprocess(cmd, env=env)
            log_streamer = self._create_backend_log_streamer(process)
            return self._verify_backend_startup(process, port, log_streamer)
        except Exception as e:
            self._handle_backend_startup_exception(e)
            return None, None
    
    def _prepare_backend_logging(self):
        """Prepare backend logging setup."""
        self.config.log_dir.mkdir(exist_ok=True)
    
    def _create_backend_log_streamer(self, process: subprocess.Popen) -> LogStreamer:
        """Create backend log streamer."""
        return self.log_manager.add_streamer("BACKEND", process, Colors.CYAN)
    
    def _verify_backend_startup(self, process: subprocess.Popen, port: int, 
                               log_streamer: LogStreamer) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Verify backend startup with improved readiness logic."""
        # Initial quick check to make sure process didn't crash immediately
        time.sleep(2)
        if process.poll() is not None:
            self._handle_backend_startup_failure(process)
            return None, None
        
        # Wait for backend to fully initialize before health check
        self._print("[U+23F3]", "WAIT", f"Waiting for backend initialization on port {port}...")
        ready, details = self._wait_for_backend_ready(process, port)
        
        if not ready:
            logger.error(f"Backend readiness check failed on port {port}: {details}")
            self._print(" FAIL: ", "ERROR", f"Backend not ready: {details}")
            return None, None
            
        self._finalize_backend_startup(port, process)
        return process, log_streamer
    
    def _wait_for_backend_ready(self, process: subprocess.Popen, port: int) -> Tuple[bool, str]:
        """
        Wait for backend to be ready with comprehensive monitoring.
        
        Combines process monitoring with health checks to prevent false positives
        and false negatives in service readiness detection.
        
        Returns:
            Tuple of (ready, details) where details explains any failure
        """
        max_wait_time = 45  # Increased timeout for backend initialization
        check_interval = 1  # Check every second
        start_time = time.time()
        
        # Phase 1: Wait for process to stabilize (first 5 seconds)
        stabilization_time = 5
        while time.time() - start_time < stabilization_time:
            if process.poll() is not None:
                return False, f"Process crashed during stabilization (exit code: {process.poll()})"
            time.sleep(0.5)
        
        # Phase 2: Wait for port to be available (network listening)
        port_ready = False
        port_wait_time = 15
        while time.time() - start_time < port_wait_time and not port_ready:
            if process.poll() is not None:
                return False, f"Process crashed during port binding (exit code: {process.poll()})"
            
            port_ready = self._check_port_listening(port)
            if not port_ready:
                time.sleep(check_interval)
        
        if not port_ready:
            return False, f"Port {port} not listening after {port_wait_time}s"
        
        # Phase 3: Wait for health endpoint to respond
        from dev_launcher.utils import wait_for_service_with_details
        backend_url = f"http://localhost:{port}/health/"
        health_timeout = max_wait_time - (time.time() - start_time)
        
        if health_timeout <= 0:
            return False, "Timeout during health check phase"
        
        success, details = wait_for_service_with_details(backend_url, timeout=int(health_timeout))
        if success:
            elapsed = time.time() - start_time
            return True, f"Ready in {elapsed:.1f}s"
        else:
            return False, f"Health check failed: {details}"
    
    def _check_port_listening(self, port: int) -> bool:
        """Check if the port is listening for connections."""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception as e:
            logger.debug(f"Port check failed for {port}: {e}")
            return False
    
    def _verify_backend_health(self, port: int) -> bool:
        """Verify backend is responding on the expected port."""
        from dev_launcher.utils import wait_for_service_with_details
        backend_url = f"http://localhost:{port}/health/"
        success, details = wait_for_service_with_details(backend_url, timeout=30)
        if not success:
            logger.debug(f"Backend health check failed on port {port}: {details}")
        return success
    
    def _handle_backend_startup_exception(self, e: Exception):
        """Handle backend startup exception."""
        logger.error(f"Failed to start backend: {e}")
        self._print(" FAIL: ", "ERROR", f"Backend startup failed: {str(e)[:100]}")
    
    def _handle_backend_startup_failure(self, process: subprocess.Popen):
        """Handle backend startup failure with enhanced error capture and recovery."""
        exit_code = process.poll()
        self._print(" FAIL: ", "ERROR", f"Backend failed to start (exit code: {exit_code})")
        
        # Capture detailed error information
        detailed_errors = self._capture_backend_runtime_errors(process, exit_code)
        if detailed_errors:
            self._print("[U+1F4CB]", "DETAILS", "Backend runtime errors:")
            for error in detailed_errors[:5]:  # Show max 5 most relevant errors
                print(f"   ->  {error}")
        
        # Suggest recovery actions based on exit code
        self._suggest_recovery_actions(exit_code)
        
        self._print_backend_troubleshooting()
    
    def _capture_backend_runtime_errors(self, process: subprocess.Popen, exit_code: Optional[int]) -> list:
        """Capture detailed backend runtime errors from process output and logs."""
        errors = []
        
        try:
            # Try to read from stderr if available
            if hasattr(process, 'stderr') and process.stderr:
                stderr_output = process.stderr.read()
                if stderr_output:
                    errors.extend(self._parse_backend_errors(stderr_output.decode('utf-8', errors='ignore')))
        except Exception as e:
            logger.debug(f"Failed to read process stderr: {e}")
        
        # Try to capture errors from backend log files
        try:
            backend_log_path = self.config.log_dir / "backend.log"
            if backend_log_path.exists():
                with open(backend_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read last 100 lines for recent errors
                    lines = f.readlines()
                    recent_logs = ''.join(lines[-100:]) if lines else ""
                    errors.extend(self._parse_backend_errors(recent_logs))
        except Exception as e:
            logger.debug(f"Failed to read backend log file: {e}")
        
        # Check for common backend issues based on exit code
        if exit_code:
            errors.extend(self._diagnose_exit_code_issues(exit_code))
        
        return list(set(errors))  # Remove duplicates
    
    def _parse_backend_errors(self, output: str) -> list:
        """Parse backend errors from output text."""
        errors = []
        lines = output.split('\n')
        
        # Common error patterns in backend startup
        error_patterns = [
            r'ModuleNotFoundError: .+',
            r'ImportError: .+',
            r'FileNotFoundError: .+',
            r'ConnectionError: .+',
            r'DatabaseError: .+',
            r'PermissionError: .+',
            r'AttributeError: .+',
            r'ValueError: .+',
            r'RuntimeError: .+',
            r'OSError: .+',
            r'uvicorn.error: .+',
            r'sqlalchemy.exc.: .+',
            r'asyncpg.exceptions.: .+',
            r'redis.exceptions.: .+',
            r'clickhouse_driver.errors.: .+',
            r'FastAPI.*Error: .+',
            r'Traceback \(most recent call last\):',
            r'Exception: .+',
            r'Error: .+',
            r'CRITICAL: .+',
            r'FATAL: .+',
        ]
        
        import re
        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                for pattern in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # For traceback lines, include some context
                        if 'Traceback' in line and i + 2 < len(lines):
                            context_lines = lines[i:i+3]
                            error_summary = ' | '.join(l.strip() for l in context_lines if l.strip())
                            errors.append(error_summary[:300])
                        else:
                            errors.append(line[:200])  # Truncate very long errors
                        break
        
        return errors[:15]  # Return max 15 errors
    
    def _diagnose_exit_code_issues(self, exit_code: int) -> list:
        """Diagnose issues based on process exit code."""
        issues = []
        
        if exit_code == 1:
            issues.append("General error - check Python syntax and imports")
        elif exit_code == 2:
            issues.append("Misuse of shell command - check command line arguments")
        elif exit_code == 126:
            issues.append("Permission denied - check file permissions")
        elif exit_code == 127:
            issues.append("Command not found - check Python installation and PATH")
        elif exit_code == 130:
            issues.append("Process terminated by Ctrl+C")
        elif exit_code == 139:
            issues.append("Segmentation fault - possible memory corruption")
        elif exit_code and exit_code > 128:
            signal_num = exit_code - 128
            issues.append(f"Process terminated by signal {signal_num}")
        elif exit_code and exit_code != 0:
            issues.append(f"Process exited with code {exit_code}")
            
        return issues
    
    def _suggest_recovery_actions(self, exit_code: Optional[int]):
        """Suggest recovery actions based on exit code and error patterns."""
        if not exit_code:
            return
        
        self._print(" IDEA: ", "RECOVERY", "Suggested recovery actions:")
        
        if exit_code == 1:
            print("   ->  Check Python syntax in backend files")
            print("   ->  Verify all required modules are installed: pip install -r requirements.txt")
            print("   ->  Check environment variables are properly set")
            print("   ->  Review database connection settings")
        elif exit_code == 126:
            print("   ->  Fix file permissions: chmod +x scripts/run_server.py")
            print("   ->  Check if running as appropriate user")
        elif exit_code == 127:
            print("   ->  Verify Python is installed and in PATH")
            print("   ->  Check if uvicorn is installed: pip install uvicorn")
        elif exit_code == 130:
            print("   ->  Process was interrupted - this is usually intentional")
        elif exit_code in [139, 134]:
            print("   ->  Memory issue detected - restart system if problem persists")
            print("   ->  Check for corrupted Python installation")
        else:
            print(f"   ->  Exit code {exit_code} indicates an application-specific error")
            print("   ->  Check backend logs for detailed error information")
            print("   ->  Verify all dependencies are properly installed")
    
    def _print_backend_troubleshooting(self):
        """Print backend troubleshooting tips."""
        print("\nPossible causes:")
        print("  [U+2022] Port already in use (try --dynamic flag)")
        print("  [U+2022] Python dependencies missing (check requirements.txt)")
        print("  [U+2022] Invalid Python syntax in netra_backend/app/main.py")
        print("  [U+2022] Database connection issues (check config)")
    
    def _finalize_backend_startup(self, port: int, process: subprocess.Popen):
        """Finalize backend startup."""
        self.service_discovery.write_backend_info(port)
        self._print(" PASS: ", "OK", f"Backend started on port {port}")
        self._log_backend_urls(port)
        self.backend_health_info = {"port": port, "process": process}
    
    def _log_backend_urls(self, port: int):
        """Log backend URLs."""
        logger.info(f"Backend API URL: http://localhost:{port}")
        logger.info(f"Backend WebSocket URL: ws://localhost:{port}/ws")