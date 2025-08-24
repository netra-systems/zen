"""
Frontend service startup management.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

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


class FrontendStarter:
    """
    Handles frontend service startup.
    
    Manages frontend server startup with proper configuration,
    environment setup, and error handling.
    """
    
    def __init__(self, config: LauncherConfig, services_config, 
                 log_manager: LogManager, service_discovery: ServiceDiscovery,
                 use_emoji: bool = True):
        """Initialize frontend starter."""
        self.config = config
        self.services_config = services_config
        self.log_manager = log_manager
        self.service_discovery = service_discovery
        self.use_emoji = use_emoji
        self.frontend_health_info = None
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def start_frontend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the frontend server with proper error handling and environment loading wait."""
        # Wait for environment loading to complete before starting frontend
        self._wait_for_environment_loading()
        
        self._print("🚀", "FRONTEND", "Starting frontend server...")
        startup_params = self._prepare_frontend_startup()
        if not startup_params:
            # Only show detailed errors after environment is fully loaded
            self._handle_frontend_preparation_failure()
            return None, None
        backend_info, port, frontend_path = startup_params
        return self._start_frontend_process(backend_info, port, frontend_path)
    
    def _handle_frontend_preparation_failure(self):
        """Handle frontend preparation failure with appropriate error messages."""
        import os
        from dev_launcher.config import resolve_path
        
        # Only show errors if environment loading is complete
        if os.environ.get('NETRA_SECRETS_LOADING') == 'true':
            logger.debug("Frontend preparation failed during environment loading - deferring error display")
            return
        
        # Check specific failure reasons and provide helpful messages
        backend_info = self.service_discovery.read_backend_info()
        frontend_path = resolve_path("frontend", root=self.config.project_root)
        
        if not backend_info:
            self._print("❌", "ERROR", "Backend service not available - ensure backend is running")
            logger.info("Hint: Start backend service first or check service discovery")
        
        if not frontend_path or not frontend_path.exists():
            self._print("❌", "ERROR", f"Frontend directory not found: {frontend_path}")
            logger.info("Hint: Ensure you're running from the project root directory")
    
    def _prepare_frontend_startup(self) -> Optional[Tuple[Dict, int, Path]]:
        """Prepare frontend startup parameters."""
        backend_info = self._get_backend_info()
        if not backend_info:
            return None
        port = self._determine_frontend_port()
        frontend_path = self._get_frontend_path()
        if not frontend_path:
            return None
        return backend_info, port, frontend_path
    
    def _wait_for_environment_loading(self) -> None:
        """Wait for environment loading to complete to prevent premature error display."""
        import os
        import time
        
        # Check if environment is still being loaded
        max_wait = 5.0  # Maximum wait time in seconds
        wait_interval = 0.1
        waited = 0.0
        
        while os.environ.get('NETRA_SECRETS_LOADING') == 'true' and waited < max_wait:
            time.sleep(wait_interval)
            waited += wait_interval
            
        if waited > 0:
            logger.debug(f"Waited {waited:.1f}s for environment loading to complete")
    
    def _get_backend_info(self) -> Optional[Dict]:
        """Get backend service discovery info with grace period for initialization."""
        backend_info = self.service_discovery.read_backend_info()
        if not backend_info:
            # Don't immediately error - backend may still be starting up
            # This prevents premature error display during system initialization
            logger.debug("Backend service discovery not found - backend may still be initializing")
            return None
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
        # Try to get a port in a preferred range first
        from dev_launcher.utils import find_available_port
        preferred_port = self.config.frontend_port or 3000
        port = find_available_port(preferred_port, (3000, 3010))
        logger.info(f"Allocated frontend port: {port}")
        self.config.frontend_port = port
        return port
    
    def _get_frontend_path(self) -> Optional[Path]:
        """Get frontend path with graceful error handling."""
        frontend_path = resolve_path("frontend", root=self.config.project_root)
        if not frontend_path or not frontend_path.exists():
            # Use debug logging instead of immediate error to prevent premature display
            logger.debug(f"Frontend directory not found at expected path: {frontend_path}")
            return None
        return frontend_path
    
    def _start_frontend_process(self, backend_info: Dict, port: int, 
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
    
    def _create_frontend_env(self, backend_info: Dict, port: int) -> Dict:
        """Create frontend environment variables."""
        service_env_vars = self.services_config.get_all_env_vars()
        env = self._build_frontend_env_base(backend_info, port, service_env_vars)
        self._configure_frontend_reload(env)
        return env
    
    def _build_frontend_env_base(self, backend_info: Dict, port: int, 
                                service_env_vars: Dict) -> Dict:
        """Build frontend environment base."""
        return create_process_env(
            NEXT_PUBLIC_API_URL=backend_info["api_url"],
            NEXT_PUBLIC_WS_URL=backend_info["ws_url"],
            PORT=str(port),
            PYTHONPATH=str(self.config.project_root),
            # Increase Node.js memory limit to 4GB to handle large test suite and development build
            NODE_OPTIONS="--max-old-space-size=4096",
            **service_env_vars,
            **self.config.env_overrides
        )
    
    def _configure_frontend_reload(self, env: Dict):
        """Configure frontend reload settings."""
        if not self.config.frontend_reload:
            self._disable_frontend_reload(env)
        else:
            logger.info("Frontend hot reload: ENABLED")
    
    def _disable_frontend_reload(self, env: Dict):
        """Disable frontend reload."""
        env["WATCHPACK_POLLING"] = "false"
        env["NEXT_DISABLE_FAST_REFRESH"] = "true"
        logger.info("Frontend hot reload: DISABLED")
    
    def _execute_frontend_startup(self, cmd: list, env: Dict, frontend_path: Path, 
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
    
    def _create_and_verify_frontend_process(self, cmd: list, env: Dict, frontend_path: Path, 
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