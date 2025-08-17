"""
Main launcher class for the development environment.
"""

import os
import sys
import time
import logging
from typing import Optional

from dev_launcher.config import LauncherConfig
from dev_launcher.environment_checker import EnvironmentChecker
from dev_launcher.config_manager import ConfigManager
from dev_launcher.secret_loader import SecretLoader
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.service_startup import ServiceStartupCoordinator
from dev_launcher.process_manager import ProcessManager
from dev_launcher.log_streamer import LogManager, setup_logging
from dev_launcher.health_monitor import HealthMonitor, create_url_health_check, create_process_health_check
from dev_launcher.summary_display import SummaryDisplay
from dev_launcher.utils import check_emoji_support, print_with_emoji, wait_for_service, open_browser

logger = logging.getLogger(__name__)


class DevLauncher:
    """
    Unified development environment launcher.
    
    Orchestrates startup and management of all development
    services including backend, frontend, and supporting infrastructure.
    """
    
    def __init__(self, config: LauncherConfig):
        """Initialize the development launcher."""
        self.config = config
        self.use_emoji = check_emoji_support()
        self._setup_managers()
        self._setup_components()
        self._setup_logging()
    
    def _setup_managers(self):
        """Setup manager instances."""
        self.health_monitor = HealthMonitor(check_interval=30)
        self.process_manager = ProcessManager(health_monitor=self.health_monitor)
        self.log_manager = LogManager()
        self.service_discovery = ServiceDiscovery(self.config.project_root)
    
    def _setup_components(self):
        """Setup component instances."""
        self.environment_checker = EnvironmentChecker(self.config.project_root, self.use_emoji)
        self.config_manager = ConfigManager(self.config, self.use_emoji)
        self.secret_loader = self._create_secret_loader()
        self.service_startup = self._create_service_startup()
        self.summary_display = SummaryDisplay(self.config, self.service_discovery, self.use_emoji)
    
    def _create_secret_loader(self) -> SecretLoader:
        """Create secret loader instance."""
        return SecretLoader(
            project_id=self.config.project_id,
            verbose=self.config.verbose,
            project_root=self.config.project_root
        )
    
    def _create_service_startup(self) -> ServiceStartupCoordinator:
        """Create service startup coordinator."""
        return ServiceStartupCoordinator(
            self.config, 
            self.config_manager.services_config,
            self.log_manager,
            self.service_discovery,
            self.use_emoji
        )
    
    def _setup_logging(self):
        """Setup logging and show verbose configuration."""
        setup_logging(self.config.verbose)
        self.config_manager.log_verbose_config()
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def check_environment(self) -> bool:
        """Check if environment is ready for launch."""
        return self.environment_checker.check_environment()
    
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
            self.config_manager.show_env_var_debug_info()
        return result
    
    def register_health_monitoring(self):
        """Register health monitoring after services are verified ready."""
        self._print("💚", "HEALTH", "Registering health monitoring...")
        self._register_backend_health()
        self._register_frontend_health()
    
    def _register_backend_health(self):
        """Register backend health monitoring."""
        if not self.service_startup.backend_health_info:
            return
        backend_url = f"http://localhost:{self.service_startup.backend_health_info['port']}/health/live"
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
        if not self.service_startup.frontend_health_info:
            return
        self._register_frontend_service()
        logger.info("Frontend health monitoring registered")
    
    def _register_frontend_service(self):
        """Register frontend service with health monitor."""
        self.health_monitor.register_service(
            "Frontend",
            health_check=create_process_health_check(self.service_startup.frontend_health_info['process']),
            recovery_action=lambda: logger.error("Frontend needs restart - please restart the launcher"),
            max_failures=5
        )
    
    def run(self) -> int:
        """Run the development environment."""
        self._print_startup_banner()
        self.config_manager.show_configuration()
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
        print("\nNote: The application may not work correctly without secrets.")
        print("To skip secret loading, use: --no-secrets")
    
    def _clear_service_discovery(self):
        """Clear old service discovery."""
        self.service_discovery.clear_all()
    
    def _start_and_verify_backend(self) -> int:
        """Start and verify backend."""
        backend_process, backend_streamer = self.service_startup.start_backend()
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
        self.process_manager.cleanup_all()
    
    def _start_and_run_services(self) -> int:
        """Start and run all services."""
        frontend_result = self._start_and_verify_frontend()
        if frontend_result != 0:
            return frontend_result
        self._run_main_loop()
        return self._handle_cleanup()
    
    def _start_and_verify_frontend(self) -> int:
        """Start and verify frontend."""
        frontend_process, frontend_streamer = self.service_startup.start_frontend()
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
        self.summary_display.show_success_summary()
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
            self._print("⚠️", "WARN", "Some services were unhealthy during execution")
            return 1
        return 0