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
        """
        Initialize the development launcher.
        
        Args:
            config: Launcher configuration
        """
        self.config = config
        self.use_emoji = check_emoji_support()
        
        # Load or create service configuration
        # Use interactive=False when running in CI/automation or with --non-interactive
        import sys
        interactive = sys.stdin.isatty() and not config.non_interactive
        self.services_config = load_or_create_config(interactive=interactive)
        
        # Managers
        self.health_monitor = HealthMonitor(check_interval=30)
        self.process_manager = ProcessManager(health_monitor=self.health_monitor)
        self.log_manager = LogManager()
        self.service_discovery = ServiceDiscovery(config.project_root)
        self.secret_loader = SecretLoader(
            project_id=config.project_id,
            verbose=config.verbose,
            project_root=config.project_root
        )
        
        # Health check info (registered after startup verification)
        self.backend_health_info = None
        self.frontend_health_info = None
        
        # Setup logging
        setup_logging(config.verbose)
        
        if config.verbose:
            logger.info(f"Project root: {config.project_root}")
            logger.info(f"Log directory: {config.log_dir}")
            logger.info(f"Service configuration loaded:")
            logger.info(f"  Redis: {self.services_config.redis.mode.value}")
            logger.info(f"  ClickHouse: {self.services_config.clickhouse.mode.value}")
            logger.info(f"  PostgreSQL: {self.services_config.postgres.mode.value}")
            logger.info(f"  LLM: {self.services_config.llm.mode.value}")
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def check_environment(self) -> bool:
        """
        Check if the environment is ready for launch.
        
        Returns:
            True if environment is ready
        """
        self._print("🔍", "CHECK", "Checking environment...")
        
        # Check dependencies
        deps = check_dependencies()
        missing_deps = []
        
        if not deps.get('uvicorn', False):
            missing_deps.append('uvicorn (pip install uvicorn)')
        if not deps.get('fastapi', False):
            missing_deps.append('fastapi (pip install fastapi)')
        if not deps.get('node', False):
            missing_deps.append('Node.js (visit nodejs.org)')
        if not deps.get('npm', False):
            missing_deps.append('npm (comes with Node.js)')
        
        if missing_deps:
            self._print("❌", "ERROR", "Missing required dependencies:")
            for dep in missing_deps:
                print(f"     • {dep}")
            print("\nInstall the missing dependencies and try again.")
            return False
        
        # Check project structure
        structure = check_project_structure(self.config.project_root)
        missing_structure = []
        
        if not structure.get('backend', False):
            missing_structure.append('Backend directory (app/) not found')
        if not structure.get('frontend', False):
            missing_structure.append('Frontend directory (frontend/) not found')
        if not structure.get('frontend_deps', False):
            missing_structure.append('Frontend dependencies not installed (run: cd frontend && npm install)')
        
        if missing_structure:
            self._print("❌", "ERROR", "Invalid project structure:")
            for issue in missing_structure:
                print(f"     • {issue}")
            print(f"\nMake sure you're running from the project root: {self.config.project_root}")
            return False
        
        self._print("✅", "OK", "Environment check passed")
        return True
    
    def load_secrets(self) -> bool:
        """
        Load secrets if configured.
        
        Returns:
            True if secrets loaded successfully or not needed
        """
        if not self.config.load_secrets:
            self._print("🔒", "SECRETS", "Secret loading disabled (--no-secrets flag)")
            return True
        
        self._print("🔐", "SECRETS", "Starting enhanced environment variable loading...")
        result = self.secret_loader.load_all_secrets()
        
        if self.config.verbose:
            self._show_env_var_debug_info()
        
        return result
    
    def register_health_monitoring(self):
        """Register health monitoring after services are verified ready."""
        self._print("💚", "HEALTH", "Registering health monitoring...")
        
        # Register backend health monitoring
        if self.backend_health_info:
            backend_url = f"http://localhost:{self.backend_health_info['port']}/health/live"
            self.health_monitor.register_service(
                "Backend",
                health_check=create_url_health_check(backend_url),
                recovery_action=lambda: logger.error("Backend needs restart - please restart the launcher"),
                max_failures=5
            )
            logger.info("Backend health monitoring registered")
        
        # Register frontend health monitoring
        if self.frontend_health_info:
            self.health_monitor.register_service(
                "Frontend",
                health_check=create_process_health_check(self.frontend_health_info['process']),
                recovery_action=lambda: logger.error("Frontend needs restart - please restart the launcher"),
                max_failures=5
            )
            logger.info("Frontend health monitoring registered")
    
    def start_backend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """
        Start the backend server.
        
        Returns:
            Tuple of (process, log_streamer)
        """
        self._print("🚀", "BACKEND", "Starting backend server...")
        
        # Determine port
        if self.config.dynamic_ports:
            port = get_free_port()
            logger.info(f"Allocated backend port: {port}")
        else:
            port = self.config.backend_port or 8000
        
        # Store port for later use
        self.config.backend_port = port
        
        # Find run_server script
        run_server_enhanced = resolve_path("scripts", "run_server_enhanced.py", root=self.config.project_root)
        run_server_path = resolve_path("scripts", "run_server.py", root=self.config.project_root)
        
        server_script = None
        if run_server_enhanced and run_server_enhanced.exists():
            server_script = run_server_enhanced
            logger.info("Using enhanced server with health monitoring")
        elif run_server_path and run_server_path.exists():
            server_script = run_server_path
        else:
            # Fallback to direct uvicorn
            logger.info("Using direct uvicorn launch")
        
        # Build command
        if server_script:
            cmd = [
                sys.executable,
                str(server_script),
                "--port", str(port)
            ]
        else:
            # Direct uvicorn launch
            cmd = [
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", str(port)
            ]
        
        # Add reload flag - use uvicorn's native reload
        if not self.config.backend_reload:
            if server_script:
                cmd.append("--no-reload")
            logger.info("Backend hot reload: DISABLED")
        else:
            if not server_script:
                cmd.append("--reload")
            logger.info("Backend hot reload: ENABLED (uvicorn native)")
        
        # Add verbose flag if requested
        if self.config.verbose and server_script:
            cmd.append("--verbose")
        
        logger.debug(f"Backend command: {' '.join(cmd)}")
        
        # Create environment with service configuration
        service_env_vars = self.services_config.get_all_env_vars()
        env = create_process_env(
            BACKEND_PORT=str(port),
            PYTHONPATH=str(self.config.project_root),
            **service_env_vars,  # Add service configuration
            **self.config.env_overrides
        )
        
        
        # Create log file
        self.config.log_dir.mkdir(exist_ok=True)
        log_file = self.config.log_dir / f"backend_{time.strftime('%Y%m%d_%H%M%S')}.log"
        
        try:
            # Start process
            process = create_subprocess(cmd, env=env)
            
            # Create log streamer
            log_streamer = self.log_manager.add_streamer(
                "BACKEND",
                process,
                Colors.CYAN
            )
            
            # Wait a moment for the server to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                # Get error output if available
                error_output = ""
                try:
                    if process.stderr:
                        error_output = process.stderr.read().decode('utf-8', errors='ignore')
                except:
                    pass
                
                self._print("❌", "ERROR", "Backend failed to start")
                if error_output:
                    print("\nError details:")
                    print(error_output[:500])  # First 500 chars of error
                print("\nPossible causes:")
                print("  • Port already in use (try --dynamic flag)")
                print("  • Python dependencies missing (check requirements.txt)")
                print("  • Invalid Python syntax in app/main.py")
                print("  • Database connection issues (check config)")
                return None, None
            
            # Write service discovery info
            self.service_discovery.write_backend_info(port)
            
            self._print("✅", "OK", f"Backend started on port {port}")
            logger.info(f"Backend API URL: http://localhost:{port}")
            logger.info(f"Backend WebSocket URL: ws://localhost:{port}/ws")
            logger.info(f"Backend log file: {log_file}")
            
            # Store health check info for later registration (after startup verification)
            self.backend_health_info = {
                "port": port,
                "process": process
            }
            
            return process, log_streamer
            
        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            self._print("❌", "ERROR", f"Backend startup failed: {str(e)[:100]}")
            return None, None
    
    def start_frontend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """
        Start the frontend server.
        
        Returns:
            Tuple of (process, log_streamer)
        """
        self._print("🚀", "FRONTEND", "Starting frontend server...")
        
        # Read backend info from service discovery
        backend_info = self.service_discovery.read_backend_info()
        if not backend_info:
            self._print("❌", "ERROR", "Backend service discovery not found")
            return None, None
        
        # Determine port
        if self.config.dynamic_ports:
            port = get_free_port()
            logger.info(f"Allocated frontend port: {port}")
            self.config.frontend_port = port
        else:
            port = self.config.frontend_port
        
        # Build command
        frontend_path = resolve_path("frontend", root=self.config.project_root)
        if not frontend_path or not frontend_path.exists():
            self._print("❌", "ERROR", "Frontend directory not found")
            return None, None
        
        # Check for start script
        start_script = frontend_path / "scripts" / "start_with_discovery.js"
        
        # Determine npm command
        if self.config.use_turbopack:
            npm_command = "dev"  # Uses turbopack by default
            logger.info("Using Turbopack (experimental)")
        else:
            npm_command = "dev"
            logger.info("Using standard Next.js")
        
        # Build command
        if start_script.exists():
            cmd = ["node", "scripts/start_with_discovery.js", npm_command]
        else:
            if sys.platform == "win32":
                cmd = ["npm.cmd", "run", npm_command]
            else:
                cmd = ["npm", "run", npm_command]
        
        logger.debug(f"Frontend command: {' '.join(cmd)}")
        logger.debug(f"Frontend working directory: {frontend_path}")
        
        # Create environment with service configuration
        service_env_vars = self.services_config.get_all_env_vars()
        env = create_process_env(
            NEXT_PUBLIC_API_URL=backend_info["api_url"],
            NEXT_PUBLIC_WS_URL=backend_info["ws_url"],
            PORT=str(port),
            PYTHONPATH=str(self.config.project_root),
            **service_env_vars,  # Add service configuration
            **self.config.env_overrides
        )
        
        # Disable hot reload if requested
        if not self.config.frontend_reload:
            env["WATCHPACK_POLLING"] = "false"
            env["NEXT_DISABLE_FAST_REFRESH"] = "true"
            logger.info("Frontend hot reload: DISABLED")
        else:
            logger.info("Frontend hot reload: ENABLED")
        
        # Create log file
        self.config.log_dir.mkdir(exist_ok=True)
        log_file = self.config.log_dir / f"frontend_{time.strftime('%Y%m%d_%H%M%S')}.log"
        
        try:
            # Start process
            process = create_subprocess(cmd, cwd=frontend_path, env=env)
            
            # Create log streamer
            log_streamer = self.log_manager.add_streamer(
                "FRONTEND",
                process,
                Colors.MAGENTA
            )
            
            # Wait for frontend to initialize
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is not None:
                # Get error output if available
                error_output = ""
                try:
                    if process.stderr:
                        error_output = process.stderr.read().decode('utf-8', errors='ignore')
                except:
                    pass
                
                self._print("❌", "ERROR", "Frontend failed to start")
                if error_output:
                    print("\nError details:")
                    print(error_output[:500])  # First 500 chars of error
                print("\nPossible causes:")
                print("  • Port already in use (try --dynamic flag)")
                print("  • Node modules not installed (run: cd frontend && npm install)")
                print("  • Invalid Next.js configuration")
                print("  • TypeScript compilation errors")
                return None, None
            
            self._print("✅", "OK", f"Frontend started on port {port}")
            logger.info(f"Frontend URL: http://localhost:{port}")
            logger.info(f"Frontend log file: {log_file}")
            
            # Write frontend info to service discovery
            self.service_discovery.write_frontend_info(port)
            
            # Store health check info for later registration (after startup verification)
            self.frontend_health_info = {
                "port": port,
                "process": process
            }
            
            return process, log_streamer
            
        except Exception as e:
            logger.error(f"Failed to start frontend: {e}")
            self._print("❌", "ERROR", f"Frontend startup failed: {str(e)[:100]}")
            return None, None
    
    def run(self) -> int:
        """
        Run the development environment.
        
        Returns:
            Exit code (0 for success)
        """
        print("=" * 60)
        self._print("🚀", "LAUNCH", "Netra AI Development Environment")
        print("=" * 60)
        
        # Show configuration
        self._show_configuration()
        
        # Check environment
        if not self.check_environment():
            return 1
        
        # Load secrets
        if not self.load_secrets():
            self._print("⚠️", "WARN", "Failed to load some secrets")
            print("\nNote: The application may not work correctly without secrets.")
            print("To skip secret loading, use: --no-secrets")
            print("To configure secrets, see: docs/GOOGLE_SECRET_MANAGER_SETUP.md")
        
        # Clear old service discovery
        self.service_discovery.clear_all()
        
        # Start backend with native reload support
        backend_process, backend_streamer = self.start_backend()
        if not backend_process:
            self._print("❌", "ERROR", "Failed to start backend")
            return 1
        self.process_manager.add_process("Backend", backend_process)
        
        # Wait for backend to be ready
        backend_info = self.service_discovery.read_backend_info()
        backend_healthy = False
        if backend_info:
            self._print("⏳", "WAIT", "Waiting for backend to be ready...")
            # Check /health/ready instead of /health/live for full readiness
            backend_ready_url = f"{backend_info['api_url']}/health/ready"
            if wait_for_service(backend_ready_url, timeout=30):
                self._print("✅", "OK", "Backend is ready")
                
                # Also verify auth config endpoint is accessible
                auth_config_url = f"{backend_info['api_url']}/api/auth/config"
                self._print("⏳", "WAIT", "Verifying auth system...")
                if wait_for_service(auth_config_url, timeout=10):
                    self._print("✅", "OK", "Auth system is ready")
                    backend_healthy = True
                else:
                    self._print("⚠️", "WARN", "Auth config check timed out")
            else:
                self._print("❌", "ERROR", "Backend failed to start - check database connection")
                self._print("ℹ️", "INFO", "Common issues:")
                self._print("", "", "  • DATABASE_URL may have special characters that need encoding")
                self._print("", "", "  • PostgreSQL container may not be running (check: docker ps)")
                self._print("", "", "  • Database credentials may be incorrect")
                self._print("", "", "  • Run: cd terraform-dev-postgres && terraform apply")
                self.process_manager.cleanup_all()
                return 1
        
        # Only start frontend if backend is healthy
        if not backend_healthy:
            self._print("❌", "ERROR", "Cannot start frontend - backend is not healthy")
            self.process_manager.cleanup_all()
            return 1
        
        # Start frontend with native reload support (Next.js)
        frontend_process, frontend_streamer = self.start_frontend()
        if not frontend_process:
            self._print("❌", "ERROR", "Failed to start frontend")
            self.process_manager.cleanup_all()
            return 1
        self.process_manager.add_process("Frontend", frontend_process)
        
        # Wait for frontend to be ready
        self._print("⏳", "WAIT", "Waiting for frontend to be ready...")
        frontend_url = f"http://localhost:{self.config.frontend_port}"
        
        # Give Next.js more time to compile initially
        logger.info("Allowing Next.js to compile...")
        time.sleep(5)
        
        if wait_for_service(frontend_url, timeout=90):
            self._print("✅", "OK", "Frontend is ready")
            
            # Additional delay to ensure frontend is fully initialized
            time.sleep(2)
            
            # Open browser if configured
            if not self.config.no_browser:
                self._print("🌐", "BROWSER", f"Opening browser at {frontend_url}")
                open_browser(frontend_url)
        else:
            self._print("⚠️", "WARN", "Frontend readiness check timed out")
        
        # Show success summary
        self._show_success_summary()
        
        # Register health monitoring AFTER services are verified ready
        self.register_health_monitoring()
        
        # Start health monitoring
        self.health_monitor.start()
        
        # Wait for processes
        try:
            self.process_manager.wait_for_all()
        except KeyboardInterrupt:
            self._print("\n🔄", "INTERRUPT", "Received interrupt signal")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self._print("❌", "ERROR", f"Unexpected error: {str(e)[:100]}")
        
        # Cleanup
        self.health_monitor.stop()
        self.process_manager.cleanup_all()
        self.log_manager.stop_all()
        
        # Check if any services failed
        if not self.health_monitor.all_healthy():
            self._print("⚠️", "WARN", "Some services were unhealthy during execution")
            return 1
        
        return 0
    
    def _show_configuration(self):
        """Show configuration summary."""
        self._print("📝", "CONFIG", "Configuration:")
        print(f"  • Dynamic ports: {'YES' if self.config.dynamic_ports else 'NO'}")
        print(f"  • Backend hot reload: {'YES (uvicorn native)' if self.config.backend_reload else 'NO'}")
        print(f"  • Frontend hot reload: YES (Next.js native)")
        print(f"  • Real-time logging: YES")
        print(f"  • Turbopack: {'YES' if self.config.use_turbopack else 'NO'}")
        print(f"  • Secret loading: {'YES' if self.config.load_secrets else 'NO'}")
        print(f"  • Verbose output: {'YES' if self.config.verbose else 'NO'}")
        print()
    
    def _show_env_var_debug_info(self):
        """Show debug information about environment variables."""
        print("\n" + "=" * 60)
        print("🔍 ENVIRONMENT VARIABLE DEBUG INFO")
        print("=" * 60)
        
        # Check for key environment files
        env_files = [
            (".env", "Base configuration"),
            (".env.development", "Development overrides"),
            (".env.development.local", "Terraform-generated"),
        ]
        
        print("\n📁 Environment Files Status:")
        for filename, description in env_files:
            filepath = self.config.project_root / filename
            if filepath.exists():
                size = filepath.stat().st_size
                print(f"  ✅ {filename:25} - {description} ({size} bytes)")
            else:
                print(f"  ❌ {filename:25} - {description} (not found)")
        
        # Show key environment variables (masked)
        print("\n🔑 Key Environment Variables (current state):")
        important_vars = [
            "GOOGLE_CLIENT_ID",
            "GEMINI_API_KEY",
            "CLICKHOUSE_HOST",
            "DATABASE_URL",
            "REDIS_HOST",
            "JWT_SECRET_KEY",
            "ENVIRONMENT",
        ]
        
        for var in important_vars:
            value = os.environ.get(var)
            if value:
                if len(value) > 10:
                    masked = value[:3] + "***" + value[-3:]
                else:
                    masked = "***"
                print(f"  {var:30} = {masked}")
            else:
                print(f"  {var:30} = <not set>")
        
        print("=" * 60)
    
    def _show_success_summary(self):
        """Show success summary."""
        print("\n" + "=" * 60)
        self._print("✨", "SUCCESS", "Development environment is running!")
        print("=" * 60)
        
        backend_info = self.service_discovery.read_backend_info()
        if backend_info:
            self._print("🔧", "BACKEND", "")
            print(f"  API: {backend_info['api_url']}")
            print(f"  WebSocket: {backend_info['ws_url']}")
            print(f"  Logs: Real-time streaming (cyan)")
        
        self._print("🌐", "FRONTEND", "")
        print(f"  URL: http://localhost:{self.config.frontend_port}")
        print(f"  Logs: Real-time streaming (magenta)")
        
        print("\n📝 ENVIRONMENT FILES:")
        print("  Priority (highest to lowest):")
        print("  1. OS Environment Variables")
        print("  2. .env.development.local (Terraform)")
        print("  3. .env.development (local overrides)")
        print("  4. .env (base configuration)")
        print("  5. Google Secret Manager")
        print("  6. Static defaults")
        
        print("\n[COMMANDS]:")
        print("  Press Ctrl+C to stop all services")
        print("  Logs are streamed in real-time with color coding")
        print(f"  Log files saved in: {self.config.log_dir}")
        print("-" * 60 + "\n")