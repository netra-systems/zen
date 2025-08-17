"""
Service startup coordination for development launcher.
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from dev_launcher.config import LauncherConfig, resolve_path
from dev_launcher.log_streamer import LogStreamer, LogManager, Colors
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.utils import (
    get_free_port, wait_for_service, create_process_env, 
    create_subprocess, print_with_emoji
)

logger = logging.getLogger(__name__)


class ServiceStartupCoordinator:
    """
    Coordinates startup of development services.
    
    Handles backend, frontend, and auth service startup with
    proper error handling and service discovery.
    """
    
    def __init__(self, config: LauncherConfig, services_config, 
                 log_manager: LogManager, service_discovery: ServiceDiscovery,
                 use_emoji: bool = True):
        """Initialize service startup coordinator."""
        self.config = config
        self.services_config = services_config
        self.log_manager = log_manager
        self.service_discovery = service_discovery
        self.use_emoji = use_emoji
        self.backend_health_info = None
        self.frontend_health_info = None
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def start_backend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the backend server."""
        self._print("🚀", "BACKEND", "Starting backend server...")
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
        port = get_free_port()
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
        self._finalize_backend_startup(port, process)
        return process, log_streamer
    
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
    
    def start_frontend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the frontend server."""
        self._print("🚀", "FRONTEND", "Starting frontend server...")
        startup_params = self._prepare_frontend_startup()
        if not startup_params:
            return None, None
        backend_info, port, frontend_path = startup_params
        return self._start_frontend_process(backend_info, port, frontend_path)
    
    def _prepare_frontend_startup(self) -> Optional[Tuple[dict, int, Path]]:
        """Prepare frontend startup parameters."""
        backend_info = self._get_backend_info()
        if not backend_info:
            return None
        port = self._determine_frontend_port()
        frontend_path = self._get_frontend_path()
        if not frontend_path:
            return None
        return backend_info, port, frontend_path
    
    def _get_backend_info(self) -> Optional[dict]:
        """Get backend service discovery info."""
        backend_info = self.service_discovery.read_backend_info()
        if not backend_info:
            self._print("❌", "ERROR", "Backend service discovery not found")
        return backend_info
    
    def _determine_frontend_port(self) -> int:
        """Determine frontend port."""
        if self.config.dynamic_ports:
            port = self._allocate_dynamic_frontend_port()
        else:
            port = self.config.frontend_port
        return port
    
    def _allocate_dynamic_frontend_port(self) -> int:
        """Allocate dynamic frontend port."""
        port = get_free_port()
        logger.info(f"Allocated frontend port: {port}")
        self.config.frontend_port = port
        return port
    
    def _get_frontend_path(self) -> Optional[Path]:
        """Get frontend path."""
        frontend_path = resolve_path("frontend", root=self.config.project_root)
        if not frontend_path or not frontend_path.exists():
            self._print("❌", "ERROR", "Frontend directory not found")
            return None
        return frontend_path
    
    def _start_frontend_process(self, backend_info: dict, port: int, 
                               frontend_path: Path) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start frontend process."""
        cmd = self._build_frontend_command(frontend_path)
        env = self._create_frontend_env(backend_info, port)
        return self._execute_frontend_startup(cmd, env, frontend_path, port)
    
    def _build_frontend_command(self, frontend_path: Path) -> list:
        """Build frontend command."""
        start_script = frontend_path / "scripts" / "start_with_discovery.js"
        npm_command = self._get_npm_command()
        if start_script.exists():
            return ["node", "scripts/start_with_discovery.js", npm_command]
        return self._get_npm_run_command(npm_command)
    
    def _get_npm_command(self) -> str:
        """Get npm command based on configuration."""
        if self.config.use_turbopack:
            logger.info("Using Turbopack (experimental)")
        else:
            logger.info("Using standard Next.js")
        return "dev"
    
    def _get_npm_run_command(self, npm_command: str) -> list:
        """Get npm run command."""
        if sys.platform == "win32":
            return ["npm.cmd", "run", npm_command]
        return ["npm", "run", npm_command]
    
    def _create_frontend_env(self, backend_info: dict, port: int) -> dict:
        """Create frontend environment variables."""
        service_env_vars = self.services_config.get_all_env_vars()
        env = self._build_frontend_env_base(backend_info, port, service_env_vars)
        self._configure_frontend_reload(env)
        return env
    
    def _build_frontend_env_base(self, backend_info: dict, port: int, 
                                service_env_vars: dict) -> dict:
        """Build frontend environment base."""
        return create_process_env(
            NEXT_PUBLIC_API_URL=backend_info["api_url"],
            NEXT_PUBLIC_WS_URL=backend_info["ws_url"],
            PORT=str(port),
            PYTHONPATH=str(self.config.project_root),
            **service_env_vars,
            **self.config.env_overrides
        )
    
    def _configure_frontend_reload(self, env: dict):
        """Configure frontend reload settings."""
        if not self.config.frontend_reload:
            self._disable_frontend_reload(env)
        else:
            logger.info("Frontend hot reload: ENABLED")
    
    def _disable_frontend_reload(self, env: dict):
        """Disable frontend reload."""
        env["WATCHPACK_POLLING"] = "false"
        env["NEXT_DISABLE_FAST_REFRESH"] = "true"
        logger.info("Frontend hot reload: DISABLED")
    
    def _execute_frontend_startup(self, cmd: list, env: dict, frontend_path: Path, 
                                 port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Execute frontend startup."""
        self._log_frontend_startup_info(cmd, frontend_path)
        self._prepare_frontend_logging()
        try:
            return self._create_and_verify_frontend_process(cmd, env, frontend_path, port)
        except Exception as e:
            self._handle_frontend_startup_exception(e)
            return None, None
    
    def _log_frontend_startup_info(self, cmd: list, frontend_path: Path):
        """Log frontend startup information."""
        logger.debug(f"Frontend command: {' '.join(cmd)}")
        logger.debug(f"Frontend working directory: {frontend_path}")
    
    def _prepare_frontend_logging(self):
        """Prepare frontend logging setup."""
        self.config.log_dir.mkdir(exist_ok=True)
    
    def _create_and_verify_frontend_process(self, cmd: list, env: dict, frontend_path: Path, 
                                           port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Create and verify frontend process."""
        process = create_subprocess(cmd, cwd=frontend_path, env=env)
        log_streamer = self._create_frontend_log_streamer(process)
        return self._verify_frontend_startup(process, port, log_streamer)
    
    def _handle_frontend_startup_exception(self, e: Exception):
        """Handle frontend startup exception."""
        logger.error(f"Failed to start frontend: {e}")
        self._print("❌", "ERROR", f"Frontend startup failed: {str(e)[:100]}")
    
    def _create_frontend_log_streamer(self, process: subprocess.Popen) -> LogStreamer:
        """Create frontend log streamer."""
        return self.log_manager.add_streamer("FRONTEND", process, Colors.MAGENTA)
    
    def _verify_frontend_startup(self, process: subprocess.Popen, port: int, 
                                log_streamer: LogStreamer) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Verify frontend startup."""
        time.sleep(3)
        if process.poll() is not None:
            self._handle_frontend_startup_failure(process)
            return None, None
        self._finalize_frontend_startup(port, process)
        return process, log_streamer
    
    def _handle_frontend_startup_failure(self, process: subprocess.Popen):
        """Handle frontend startup failure."""
        self._print("❌", "ERROR", "Frontend failed to start")
        self._print_frontend_troubleshooting()
    
    def _print_frontend_troubleshooting(self):
        """Print frontend troubleshooting tips."""
        print("\nPossible causes:")
        print("  • Port already in use (try --dynamic flag)")
        print("  • Node modules not installed (run: cd frontend && npm install)")
        print("  • Invalid Next.js configuration")
        print("  • TypeScript compilation errors")
    
    def _finalize_frontend_startup(self, port: int, process: subprocess.Popen):
        """Finalize frontend startup."""
        self._print("✅", "OK", f"Frontend started on port {port}")
        logger.info(f"Frontend URL: http://localhost:{port}")
        self.service_discovery.write_frontend_info(port)
        self.frontend_health_info = {"port": port, "process": process}