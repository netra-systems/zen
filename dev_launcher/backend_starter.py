"""
Backend service startup management.
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

from dev_launcher.config import LauncherConfig, resolve_path
from dev_launcher.log_streamer import LogStreamer, LogManager, Colors
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.utils import (
    get_free_port, create_process_env, create_subprocess, print_with_emoji
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
            elif service.mode == ResourceMode.MOCK:
                service_modes.append(f"{name}:mock")
        
        mode_str = ", ".join(service_modes) if service_modes else "default configuration"
        self._print("🚀", "BACKEND", f"Starting backend server ({mode_str})...")
        
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
        # Try to get a port in a preferred range first
        from dev_launcher.utils import find_available_port
        preferred_port = 8000
        port = find_available_port(preferred_port, (8000, 8010))
        logger.info(f"Allocated backend port: {port}")
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
        return [sys.executable, "-m", "uvicorn", "app.main:app", 
                "--host", "0.0.0.0", "--port", str(port)]
    
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
        """Verify backend startup."""
        time.sleep(2)
        if process.poll() is not None:
            self._handle_backend_startup_failure(process)
            return None, None
        
        # Verify backend is actually responding on the expected port
        if not self._verify_backend_health(port):
            logger.error(f"Backend process started but not responding on port {port}")
            self._print("❌", "ERROR", f"Backend not responding on port {port}")
            return None, None
            
        self._finalize_backend_startup(port, process)
        return process, log_streamer
    
    def _verify_backend_health(self, port: int) -> bool:
        """Verify backend is responding on the expected port."""
        from dev_launcher.utils import wait_for_service_with_details
        backend_url = f"http://localhost:{port}/health"
        success, details = wait_for_service_with_details(backend_url, timeout=30)
        if not success:
            logger.debug(f"Backend health check failed on port {port}: {details}")
        return success
    
    def _handle_backend_startup_exception(self, e: Exception):
        """Handle backend startup exception."""
        logger.error(f"Failed to start backend: {e}")
        self._print("❌", "ERROR", f"Backend startup failed: {str(e)[:100]}")
    
    def _handle_backend_startup_failure(self, process: subprocess.Popen):
        """Handle backend startup failure."""
        self._print("❌", "ERROR", "Backend failed to start")
        self._print_backend_troubleshooting()
    
    def _print_backend_troubleshooting(self):
        """Print backend troubleshooting tips."""
        print("\nPossible causes:")
        print("  • Port already in use (try --dynamic flag)")
        print("  • Python dependencies missing (check requirements.txt)")
        print("  • Invalid Python syntax in app/main.py")
        print("  • Database connection issues (check config)")
    
    def _finalize_backend_startup(self, port: int, process: subprocess.Popen):
        """Finalize backend startup."""
        self.service_discovery.write_backend_info(port)
        self._print("✅", "OK", f"Backend started on port {port}")
        self._log_backend_urls(port)
        self.backend_health_info = {"port": port, "process": process}
    
    def _log_backend_urls(self, port: int):
        """Log backend URLs."""
        logger.info(f"Backend API URL: http://localhost:{port}")
        logger.info(f"Backend WebSocket URL: ws://localhost:{port}/ws")