"""
Main launcher class for the development environment.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Any
import logging

from .config import LauncherConfig, resolve_path
from .process_manager import ProcessManager
from .log_streamer import LogStreamer, LogManager, Colors, setup_logging
from .secret_manager import SecretLoader, ServiceDiscovery
from .service_config import ServicesConfiguration, load_or_create_config, ResourceMode
from .health_monitor import HealthMonitor, create_url_health_check, create_process_health_check
from .utils import (
    check_emoji_support,
    print_with_emoji,
    get_free_port,
    wait_for_service,
    open_browser,
    check_dependencies,
    check_project_structure,
    create_process_env,
    create_subprocess,
)

logger = logging.getLogger(__name__)


class DevLauncher:
    """
    Unified development environment launcher.
    
    This class orchestrates the startup and management of all development
    services including backend, frontend, and supporting infrastructure.
    """
    
    def __init__(self, config: LauncherConfig):
        """Initialize the development launcher."""
        self._setup_basic_config(config)
        self._setup_managers()
        self._setup_logging_and_verbose()
    
    def _setup_basic_config(self, config: LauncherConfig):
        """Setup basic configuration and service config."""
        self.config = config
        self.use_emoji = check_emoji_support()
        self._setup_service_config(config)
        self._setup_health_info()
    
    def _setup_service_config(self, config: LauncherConfig):
        """Setup service configuration."""
        import sys
        interactive = sys.stdin.isatty() and not config.non_interactive
        self.services_config = load_or_create_config(interactive=interactive)
    
    def _setup_health_info(self):
        """Setup health info variables."""
        self.backend_health_info = None
        self.frontend_health_info = None
    
    def _setup_managers(self):
        """Setup all manager instances."""
        self.health_monitor = HealthMonitor(check_interval=30)
        self.process_manager = ProcessManager(health_monitor=self.health_monitor)
        self.log_manager = LogManager()
        self.service_discovery = ServiceDiscovery(self.config.project_root)
        self._setup_secret_loader()
    
    def _setup_secret_loader(self):
        """Setup secret loader with configuration."""
        self.secret_loader = SecretLoader(
            project_id=self.config.project_id,
            verbose=self.config.verbose,
            project_root=self.config.project_root
        )
    
    def _setup_logging_and_verbose(self):
        """Setup logging and show verbose configuration."""
        setup_logging(self.config.verbose)
        if self.config.verbose:
            self._log_verbose_config()
    
    def _log_verbose_config(self):
        """Log verbose configuration information."""
        logger.info(f"Project root: {self.config.project_root}")
        logger.info(f"Log directory: {self.config.log_dir}")
        self._log_service_config()
    
    def _log_service_config(self):
        """Log service configuration details."""
        logger.info("Service configuration loaded:")
        self._log_redis_config()
        self._log_clickhouse_config()
        self._log_postgres_config()
        self._log_llm_config()
    
    def _log_redis_config(self):
        """Log Redis configuration."""
        logger.info(f"  Redis: {self.services_config.redis.mode.value}")
    
    def _log_clickhouse_config(self):
        """Log ClickHouse configuration."""
        logger.info(f"  ClickHouse: {self.services_config.clickhouse.mode.value}")
    
    def _log_postgres_config(self):
        """Log PostgreSQL configuration."""
        logger.info(f"  PostgreSQL: {self.services_config.postgres.mode.value}")
    
    def _log_llm_config(self):
        """Log LLM configuration."""
        logger.info(f"  LLM: {self.services_config.llm.mode.value}")
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def check_environment(self) -> bool:
        """Check if the environment is ready for launch."""
        self._print("🔍", "CHECK", "Checking environment...")
        if not self._check_dependencies():
            return False
        if not self._check_project_structure():
            return False
        self._print("✅", "OK", "Environment check passed")
        return True
    
    def _check_dependencies(self) -> bool:
        """Check required dependencies."""
        deps = check_dependencies()
        missing_deps = self._get_missing_deps(deps)
        if missing_deps:
            self._print_missing_deps(missing_deps)
            return False
        return True
    
    def _get_missing_deps(self, deps: dict) -> list:
        """Get list of missing dependencies."""
        missing = []
        self._check_uvicorn_dep(deps, missing)
        self._check_fastapi_dep(deps, missing)
        self._check_node_dep(deps, missing)
        self._check_npm_dep(deps, missing)
        return missing
    
    def _check_uvicorn_dep(self, deps: dict, missing: list):
        """Check uvicorn dependency."""
        if not deps.get('uvicorn', False):
            missing.append('uvicorn (pip install uvicorn)')
    
    def _check_fastapi_dep(self, deps: dict, missing: list):
        """Check fastapi dependency."""
        if not deps.get('fastapi', False):
            missing.append('fastapi (pip install fastapi)')
    
    def _check_node_dep(self, deps: dict, missing: list):
        """Check Node.js dependency."""
        if not deps.get('node', False):
            missing.append('Node.js (visit nodejs.org)')
    
    def _check_npm_dep(self, deps: dict, missing: list):
        """Check npm dependency."""
        if not deps.get('npm', False):
            missing.append('npm (comes with Node.js)')
    
    def _print_missing_deps(self, missing_deps: list):
        """Print missing dependencies error."""
        self._print("❌", "ERROR", "Missing required dependencies:")
        for dep in missing_deps:
            print(f"     • {dep}")
        print("\nInstall the missing dependencies and try again.")
    
    def _check_project_structure(self) -> bool:
        """Check project structure."""
        structure = check_project_structure(self.config.project_root)
        missing_structure = self._get_missing_structure(structure)
        if missing_structure:
            self._print_missing_structure(missing_structure)
            return False
        return True
    
    def _get_missing_structure(self, structure: dict) -> list:
        """Get list of missing structure elements."""
        missing = []
        self._check_backend_structure(structure, missing)
        self._check_frontend_structure(structure, missing)
        self._check_frontend_deps_structure(structure, missing)
        return missing
    
    def _check_backend_structure(self, structure: dict, missing: list):
        """Check backend structure."""
        if not structure.get('backend', False):
            missing.append('Backend directory (app/) not found')
    
    def _check_frontend_structure(self, structure: dict, missing: list):
        """Check frontend structure."""
        if not structure.get('frontend', False):
            missing.append('Frontend directory (frontend/) not found')
    
    def _check_frontend_deps_structure(self, structure: dict, missing: list):
        """Check frontend dependencies structure."""
        if not structure.get('frontend_deps', False):
            missing.append('Frontend dependencies not installed (run: cd frontend && npm install)')
    
    def _print_missing_structure(self, missing_structure: list):
        """Print missing structure error."""
        self._print("❌", "ERROR", "Invalid project structure:")
        for issue in missing_structure:
            print(f"     • {issue}")
        print(f"\nMake sure you're running from the project root: {self.config.project_root}")
    
    def load_secrets(self) -> bool:
        """Load secrets if configured."""
        if not self.config.load_secrets:
            self._print("🔒", "SECRETS", "Secret loading disabled (--no-secrets flag)")
            return True
        return self._load_secrets_with_debug()
    
    def _load_secrets_with_debug(self) -> bool:
        """Load secrets with debug information."""
        self._print("🔐", "SECRETS", "Starting enhanced environment variable loading...")
        result = self.secret_loader.load_all_secrets()
        if self.config.verbose:
            self._show_env_var_debug_info()
        return result
    
    def register_health_monitoring(self):
        """Register health monitoring after services are verified ready."""
        self._print("💚", "HEALTH", "Registering health monitoring...")
        self._register_backend_health()
        self._register_frontend_health()
    
    def _register_backend_health(self):
        """Register backend health monitoring."""
        if not self.backend_health_info:
            return
        backend_url = f"http://localhost:{self.backend_health_info['port']}/health/live"
        self._register_backend_service(backend_url)
        logger.info("Backend health monitoring registered")
    
    def _register_backend_service(self, backend_url: str):
        """Register backend service with health monitor."""
        self.health_monitor.register_service(
            "Backend",
            health_check=create_url_health_check(backend_url),
            recovery_action=lambda: logger.error("Backend needs restart - please restart the launcher"),
            max_failures=5
        )
    
    def _register_frontend_health(self):
        """Register frontend health monitoring."""
        if not self.frontend_health_info:
            return
        self._register_frontend_service()
        logger.info("Frontend health monitoring registered")
    
    def _register_frontend_service(self):
        """Register frontend service with health monitor."""
        self.health_monitor.register_service(
            "Frontend",
            health_check=create_process_health_check(self.frontend_health_info['process']),
            recovery_action=lambda: logger.error("Frontend needs restart - please restart the launcher"),
            max_failures=5
        )
    
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
        run_server_enhanced = resolve_path("scripts", "run_server_enhanced.py", root=self.config.project_root)
        if run_server_enhanced and run_server_enhanced.exists():
            logger.info("Using enhanced server with health monitoring")
            return run_server_enhanced
        return self._find_fallback_server_script()
    
    def _find_fallback_server_script(self) -> Optional[Path]:
        """Find fallback server script."""
        run_server_path = resolve_path("scripts", "run_server.py", root=self.config.project_root)
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
        return [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)]
    
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
            **service_env_vars,
            **self.config.env_overrides
        )
    
    def _start_backend_process(self, cmd: list, env: dict, port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start backend process."""
        self.config.log_dir.mkdir(exist_ok=True)
        log_file = self._create_backend_log_file()
        try:
            process = create_subprocess(cmd, env=env)
            log_streamer = self._create_backend_log_streamer(process)
            return self._verify_backend_startup(process, port, log_streamer)
        except Exception as e:
            self._handle_backend_startup_exception(e)
            return None, None
    
    def _create_backend_log_file(self) -> Path:
        """Create backend log file."""
        return self.config.log_dir / f"backend_{time.strftime('%Y%m%d_%H%M%S')}.log"
    
    def _create_backend_log_streamer(self, process: subprocess.Popen) -> LogStreamer:
        """Create backend log streamer."""
        return self.log_manager.add_streamer("BACKEND", process, Colors.CYAN)
    
    def _verify_backend_startup(self, process: subprocess.Popen, port: int, log_streamer: LogStreamer) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
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
        error_output = self._get_process_error_output(process)
        self._print("❌", "ERROR", "Backend failed to start")
        if error_output:
            self._print_error_details(error_output)
        self._print_backend_troubleshooting()
    
    def _print_error_details(self, error_output: str):
        """Print error details."""
        print("\nError details:")
        print(error_output[:500])
    
    def _get_process_error_output(self, process: subprocess.Popen) -> str:
        """Get process error output."""
        try:
            if process.stderr:
                return process.stderr.read().decode('utf-8', errors='ignore')
        except:
            pass
        return ""
    
    def _print_backend_troubleshooting(self):
        """Print backend troubleshooting tips."""
        print("\nPossible causes:")
        self._print_port_issue()
        self._print_dependency_issue()
        self._print_syntax_issue()
        self._print_database_issue()
    
    def _print_port_issue(self):
        """Print port issue."""
        print("  • Port already in use (try --dynamic flag)")
    
    def _print_dependency_issue(self):
        """Print dependency issue."""
        print("  • Python dependencies missing (check requirements.txt)")
    
    def _print_syntax_issue(self):
        """Print syntax issue."""
        print("  • Invalid Python syntax in app/main.py")
    
    def _print_database_issue(self):
        """Print database issue."""
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
        backend_info = self._get_backend_info()
        if not backend_info:
            return None, None
        port = self._determine_frontend_port()
        frontend_path = self._get_frontend_path()
        if not frontend_path:
            return None, None
        return self._start_frontend_process(backend_info, port, frontend_path)
    
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
    
    def _start_frontend_process(self, backend_info: dict, port: int, frontend_path: Path) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
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
    
    def _build_frontend_env_base(self, backend_info: dict, port: int, service_env_vars: dict) -> dict:
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
    
    def _execute_frontend_startup(self, cmd: list, env: dict, frontend_path: Path, port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Execute frontend startup."""
        logger.debug(f"Frontend command: {' '.join(cmd)}")
        logger.debug(f"Frontend working directory: {frontend_path}")
        self.config.log_dir.mkdir(exist_ok=True)
        try:
            process = create_subprocess(cmd, cwd=frontend_path, env=env)
            log_streamer = self._create_frontend_log_streamer(process)
            return self._verify_frontend_startup(process, port, log_streamer)
        except Exception as e:
            self._handle_frontend_startup_exception(e)
            return None, None
    
    def _handle_frontend_startup_exception(self, e: Exception):
        """Handle frontend startup exception."""
        logger.error(f"Failed to start frontend: {e}")
        self._print("❌", "ERROR", f"Frontend startup failed: {str(e)[:100]}")
    
    def _create_frontend_log_streamer(self, process: subprocess.Popen) -> LogStreamer:
        """Create frontend log streamer."""
        return self.log_manager.add_streamer("FRONTEND", process, Colors.MAGENTA)
    
    def _verify_frontend_startup(self, process: subprocess.Popen, port: int, log_streamer: LogStreamer) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Verify frontend startup."""
        time.sleep(3)
        if process.poll() is not None:
            self._handle_frontend_startup_failure(process)
            return None, None
        self._finalize_frontend_startup(port, process)
        return process, log_streamer
    
    def _handle_frontend_startup_failure(self, process: subprocess.Popen):
        """Handle frontend startup failure."""
        error_output = self._get_process_error_output(process)
        self._print("❌", "ERROR", "Frontend failed to start")
        if error_output:
            self._print_error_details(error_output)
        self._print_frontend_troubleshooting()
    
    def _print_frontend_troubleshooting(self):
        """Print frontend troubleshooting tips."""
        print("\nPossible causes:")
        self._print_port_issue()
        self._print_frontend_dep_issue()
        self._print_nextjs_config_issue()
        self._print_typescript_issue()
    
    def _print_frontend_dep_issue(self):
        """Print frontend dependency issue."""
        print("  • Node modules not installed (run: cd frontend && npm install)")
    
    def _print_nextjs_config_issue(self):
        """Print Next.js config issue."""
        print("  • Invalid Next.js configuration")
    
    def _print_typescript_issue(self):
        """Print TypeScript issue."""
        print("  • TypeScript compilation errors")
    
    def _finalize_frontend_startup(self, port: int, process: subprocess.Popen):
        """Finalize frontend startup."""
        self._print("✅", "OK", f"Frontend started on port {port}")
        logger.info(f"Frontend URL: http://localhost:{port}")
        self.service_discovery.write_frontend_info(port)
        self.frontend_health_info = {"port": port, "process": process}
    
    def run(self) -> int:
        """Run the development environment."""
        self._print_startup_banner()
        self._show_configuration()
        if not self._run_pre_checks():
            return 1
        self._clear_service_discovery()
        backend_result = self._start_and_verify_backend()
        if backend_result != 0:
            return backend_result
        return self._start_and_run_services()
    
    def _print_startup_banner(self):
        """Print startup banner."""
        print("=" * 60)
        self._print("🚀", "LAUNCH", "Netra AI Development Environment")
        print("=" * 60)
    
    def _run_pre_checks(self) -> bool:
        """Run pre-launch checks."""
        if not self.check_environment():
            return False
        return self._handle_secret_loading()
    
    def _handle_secret_loading(self) -> bool:
        """Handle secret loading with warnings."""
        if not self.load_secrets():
            self._print_secret_loading_warning()
        return True
    
    def _print_secret_loading_warning(self):
        """Print secret loading warning."""
        self._print("⚠️", "WARN", "Failed to load some secrets")
        self._print_secret_warning_details()
    
    def _print_secret_warning_details(self):
        """Print secret warning details."""
        print("\nNote: The application may not work correctly without secrets.")
        print("To skip secret loading, use: --no-secrets")
        print("To configure secrets, see: docs/GOOGLE_SECRET_MANAGER_SETUP.md")
    
    def _clear_service_discovery(self):
        """Clear old service discovery."""
        self.service_discovery.clear_all()
    
    def _start_and_verify_backend(self) -> int:
        """Start and verify backend."""
        backend_process, backend_streamer = self.start_backend()
        if not backend_process:
            self._print("❌", "ERROR", "Failed to start backend")
            return 1
        self.process_manager.add_process("Backend", backend_process)
        return self._verify_backend_readiness()
    
    def _verify_backend_readiness(self) -> int:
        """Verify backend readiness."""
        backend_info = self.service_discovery.read_backend_info()
        if not backend_info:
            return 1
        backend_healthy = self._check_backend_health(backend_info)
        if not backend_healthy:
            self._handle_backend_failure()
            return 1
        return 0
    
    def _check_backend_health(self, backend_info: dict) -> bool:
        """Check backend health."""
        self._print("⏳", "WAIT", "Waiting for backend to be ready...")
        backend_ready_url = f"{backend_info['api_url']}/health/ready"
        if not wait_for_service(backend_ready_url, timeout=30):
            return False
        self._print("✅", "OK", "Backend is ready")
        return self._verify_auth_system(backend_info)
    
    def _verify_auth_system(self, backend_info: dict) -> bool:
        """Verify auth system."""
        auth_config_url = f"{backend_info['api_url']}/api/auth/config"
        self._print("⏳", "WAIT", "Verifying auth system...")
        if wait_for_service(auth_config_url, timeout=10):
            self._print("✅", "OK", "Auth system is ready")
            return True
        self._print("⚠️", "WARN", "Auth config check timed out")
        return False
    
    def _handle_backend_failure(self):
        """Handle backend failure."""
        self._print("❌", "ERROR", "Backend failed to start - check database connection")
        self._print_backend_failure_info()
        self.process_manager.cleanup_all()
    
    def _print_backend_failure_info(self):
        """Print backend failure information."""
        self._print("ℹ️", "INFO", "Common issues:")
        self._print_database_url_issue()
        self._print_postgres_container_issue()
        self._print_database_credentials_issue()
        self._print_terraform_issue()
    
    def _print_database_url_issue(self):
        """Print database URL issue."""
        self._print("", "", "  • DATABASE_URL may have special characters that need encoding")
    
    def _print_postgres_container_issue(self):
        """Print PostgreSQL container issue."""
        self._print("", "", "  • PostgreSQL container may not be running (check: docker ps)")
    
    def _print_database_credentials_issue(self):
        """Print database credentials issue."""
        self._print("", "", "  • Database credentials may be incorrect")
    
    def _print_terraform_issue(self):
        """Print Terraform issue."""
        self._print("", "", "  • Run: cd terraform-dev-postgres && terraform apply")
    
    def _start_and_run_services(self) -> int:
        """Start and run all services."""
        frontend_result = self._start_and_verify_frontend()
        if frontend_result != 0:
            return frontend_result
        self._run_main_loop()
        return self._handle_cleanup()
    
    def _start_and_verify_frontend(self) -> int:
        """Start and verify frontend."""
        frontend_process, frontend_streamer = self.start_frontend()
        if not frontend_process:
            self._print("❌", "ERROR", "Failed to start frontend")
            self.process_manager.cleanup_all()
            return 1
        self.process_manager.add_process("Frontend", frontend_process)
        self._wait_for_frontend_ready()
        return 0
    
    def _wait_for_frontend_ready(self):
        """Wait for frontend to be ready."""
        self._print("⏳", "WAIT", "Waiting for frontend to be ready...")
        frontend_url = f"http://localhost:{self.config.frontend_port}"
        self._allow_nextjs_compile()
        self._check_frontend_service(frontend_url)
    
    def _allow_nextjs_compile(self):
        """Allow Next.js to compile."""
        logger.info("Allowing Next.js to compile...")
        time.sleep(5)
    
    def _check_frontend_service(self, frontend_url: str):
        """Check frontend service."""
        if wait_for_service(frontend_url, timeout=90):
            self._print("✅", "OK", "Frontend is ready")
            self._handle_browser_opening(frontend_url)
        else:
            self._print("⚠️", "WARN", "Frontend readiness check timed out")
    
    def _handle_browser_opening(self, frontend_url: str):
        """Handle browser opening."""
        time.sleep(2)
        if not self.config.no_browser:
            self._print("🌐", "BROWSER", f"Opening browser at {frontend_url}")
            open_browser(frontend_url)
    
    def _run_main_loop(self):
        """Run main service loop."""
        self._show_success_summary()
        self.register_health_monitoring()
        self.health_monitor.start()
        self._execute_process_loop()
    
    def _execute_process_loop(self):
        """Execute main process loop."""
        try:
            self.process_manager.wait_for_all()
        except KeyboardInterrupt:
            self._print("\n🔄", "INTERRUPT", "Received interrupt signal")
        except Exception as e:
            self._handle_main_loop_exception(e)
    
    def _handle_main_loop_exception(self, e: Exception):
        """Handle main loop exception."""
        logger.error(f"Unexpected error: {e}")
        self._print("❌", "ERROR", f"Unexpected error: {str(e)[:100]}")
    
    def _handle_cleanup(self) -> int:
        """Handle cleanup and return exit code."""
        self.health_monitor.stop()
        self.process_manager.cleanup_all()
        self.log_manager.stop_all()
        if not self.health_monitor.all_healthy():
            self._print_unhealthy_services_warning()
            return 1
        return 0
    
    def _print_unhealthy_services_warning(self):
        """Print unhealthy services warning."""
        self._print("⚠️", "WARN", "Some services were unhealthy during execution")
    
    def _show_configuration(self):
        """Show configuration summary."""
        self._print("📝", "CONFIG", "Configuration:")
        self._print_config_options()
    
    def _print_config_options(self):
        """Print configuration options."""
        self._print_dynamic_ports_config()
        self._print_backend_reload_config()
        self._print_frontend_reload_config()
        self._print_logging_config()
        self._print_turbopack_config()
        self._print_secrets_config()
        self._print_verbose_config()
        print()
    
    def _print_dynamic_ports_config(self):
        """Print dynamic ports configuration."""
        print(f"  • Dynamic ports: {'YES' if self.config.dynamic_ports else 'NO'}")
    
    def _print_backend_reload_config(self):
        """Print backend reload configuration."""
        print(f"  • Backend hot reload: {'YES (uvicorn native)' if self.config.backend_reload else 'NO'}")
    
    def _print_frontend_reload_config(self):
        """Print frontend reload configuration."""
        print(f"  • Frontend hot reload: YES (Next.js native)")
    
    def _print_logging_config(self):
        """Print logging configuration."""
        print(f"  • Real-time logging: YES")
    
    def _print_turbopack_config(self):
        """Print Turbopack configuration."""
        print(f"  • Turbopack: {'YES' if self.config.use_turbopack else 'NO'}")
    
    def _print_secrets_config(self):
        """Print secrets configuration."""
        print(f"  • Secret loading: {'YES' if self.config.load_secrets else 'NO'}")
    
    def _print_verbose_config(self):
        """Print verbose configuration."""
        print(f"  • Verbose output: {'YES' if self.config.verbose else 'NO'}")
    
    def _show_env_var_debug_info(self):
        """Show debug information about environment variables."""
        print("\n" + "=" * 60)
        print("🔍 ENVIRONMENT VARIABLE DEBUG INFO")
        print("=" * 60)
        self._show_env_files_status()
        self._show_key_env_vars()
        print("=" * 60)
    
    def _show_env_files_status(self):
        """Show environment files status."""
        env_files = self._get_env_files_list()
        print("\n📁 Environment Files Status:")
        for filename, description in env_files:
            self._show_env_file_status(filename, description)
    
    def _get_env_files_list(self) -> list:
        """Get list of environment files."""
        return [
            (".env", "Base configuration"),
            (".env.development", "Development overrides"),
            (".env.development.local", "Terraform-generated"),
        ]
    
    def _show_env_file_status(self, filename: str, description: str):
        """Show individual environment file status."""
        filepath = self.config.project_root / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✅ {filename:25} - {description} ({size} bytes)")
        else:
            print(f"  ❌ {filename:25} - {description} (not found)")
    
    def _show_key_env_vars(self):
        """Show key environment variables."""
        print("\n🔑 Key Environment Variables (current state):")
        important_vars = self._get_important_env_vars()
        for var in important_vars:
            self._show_env_var_status(var)
    
    def _get_important_env_vars(self) -> list:
        """Get list of important environment variables."""
        return [
            "GOOGLE_CLIENT_ID", "GEMINI_API_KEY", "CLICKHOUSE_HOST",
            "DATABASE_URL", "REDIS_HOST", "JWT_SECRET_KEY", "ENVIRONMENT"
        ]
    
    def _show_env_var_status(self, var: str):
        """Show individual environment variable status."""
        value = os.environ.get(var)
        if value:
            masked = self._mask_env_var_value(value)
            print(f"  {var:30} = {masked}")
        else:
            print(f"  {var:30} = <not set>")
    
    def _mask_env_var_value(self, value: str) -> str:
        """Mask environment variable value."""
        if len(value) > 10:
            return value[:3] + "***" + value[-3:]
        return "***"
    
    def _show_success_summary(self):
        """Show success summary."""
        print("\n" + "=" * 60)
        self._print("✨", "SUCCESS", "Development environment is running!")
        print("=" * 60)
        self._show_backend_summary()
        self._show_frontend_summary()
        self._show_environment_files_info()
        self._show_commands_info()
    
    def _show_backend_summary(self):
        """Show backend summary."""
        backend_info = self.service_discovery.read_backend_info()
        if backend_info:
            self._print("🔧", "BACKEND", "")
            self._print_backend_urls(backend_info)
    
    def _print_backend_urls(self, backend_info: dict):
        """Print backend URLs."""
        print(f"  API: {backend_info['api_url']}")
        print(f"  WebSocket: {backend_info['ws_url']}")
        print(f"  Logs: Real-time streaming (cyan)")
    
    def _show_frontend_summary(self):
        """Show frontend summary."""
        self._print("🌐", "FRONTEND", "")
        print(f"  URL: http://localhost:{self.config.frontend_port}")
        print(f"  Logs: Real-time streaming (magenta)")
    
    def _show_environment_files_info(self):
        """Show environment files priority information."""
        print("\n📝 ENVIRONMENT FILES:")
        print("  Priority (highest to lowest):")
        self._print_env_priority_list()
    
    def _print_env_priority_list(self):
        """Print environment priority list."""
        print("  1. OS Environment Variables")
        print("  2. .env.development.local (Terraform)")
        print("  3. .env.development (local overrides)")
        print("  4. .env (base configuration)")
        print("  5. Google Secret Manager")
        print("  6. Static defaults")
    
    def _show_commands_info(self):
        """Show commands information."""
        print("\n[COMMANDS]:")
        print("  Press Ctrl+C to stop all services")
        print("  Logs are streamed in real-time with color coding")
        print(f"  Log files saved in: {self.config.log_dir}")
        print("-" * 60 + "\n")