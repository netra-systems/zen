"""
Main launcher class for the development environment.
"""

import os
import sys
import time
import json
import hashlib
import logging
import threading
import signal
import atexit
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future

from dev_launcher.config import LauncherConfig
from dev_launcher.environment_checker import EnvironmentChecker
from dev_launcher.secret_loader import SecretLoader
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.service_startup import ServiceStartupCoordinator
from dev_launcher.process_manager import ProcessManager
from dev_launcher.log_streamer import LogManager, setup_logging
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.summary_display import SummaryDisplay
from dev_launcher.utils import check_emoji_support, print_with_emoji
from dev_launcher.health_registration import HealthRegistrationHelper
from dev_launcher.startup_validator import StartupValidator
from dev_launcher.cache_manager import CacheManager
from dev_launcher.startup_optimizer import StartupOptimizer, StartupStep
from dev_launcher.log_filter import LogFilter, StartupMode, StartupProgressTracker
from dev_launcher.critical_error_handler import critical_handler, CriticalError
from dev_launcher.migration_runner import MigrationRunner

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
        self._shutting_down = False
        self._load_env_file()  # Load .env file first
        self._setup_startup_mode()  # Setup startup mode and filtering
        self._setup_new_cache_system()  # Setup new cache and optimizer
        self._setup_managers()
        self._setup_components()
        self._setup_helpers()
        self._setup_logging()
        self._setup_signal_handlers()
        self.startup_time = time.time()
    
    def _setup_startup_mode(self):
        """Setup startup mode and filtering."""
        # Get mode from config or environment
        mode_str = getattr(self.config, 'startup_mode', None)
        if not mode_str:
            mode_str = os.environ.get("NETRA_STARTUP_MODE", "minimal")
        
        # Set startup mode
        try:
            self.startup_mode = StartupMode(mode_str.lower())
        except ValueError:
            self.startup_mode = StartupMode.MINIMAL
        
        # Create log filter and progress tracker
        self.log_filter = LogFilter(self.startup_mode)
        self.progress_tracker = StartupProgressTracker(self.startup_mode)
        
        # Override verbose if in minimal mode
        if self.startup_mode == StartupMode.MINIMAL and self.config.verbose:
            self.config.verbose = False
    
    def _setup_managers(self):
        """Setup manager instances."""
        self.health_monitor = HealthMonitor(check_interval=30)
        self.process_manager = ProcessManager(health_monitor=self.health_monitor)
        self.log_manager = LogManager()
        self.service_discovery = ServiceDiscovery(self.config.project_root)
    
    def _setup_components(self):
        """Setup component instances."""
        self.environment_checker = EnvironmentChecker(self.config.project_root, self.use_emoji)
        self.config.set_emoji_support(self.use_emoji)
        self.secret_loader = self._create_secret_loader()
        self.service_startup = self._create_service_startup()
        self.summary_display = SummaryDisplay(self.config, self.service_discovery, self.use_emoji)
    
    def _setup_helpers(self):
        """Setup helper instances."""
        self.health_helper = HealthRegistrationHelper(self.health_monitor, self.use_emoji)
        self.startup_validator = StartupValidator(self.use_emoji)
        self.migration_runner = MigrationRunner(self.config.project_root, self.use_emoji)
    
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
            self.config, self.config.services_config,
            self.log_manager, self.service_discovery, self.use_emoji)
    
    def _load_env_file(self):
        """Load .env file into os.environ."""
        env_file = self.config.project_root / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip('"\'').strip()
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
    
    def _setup_logging(self):
        """Setup logging and show verbose configuration."""
        setup_logging(self.config.verbose)
        self.config.log_verbose_config()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        if sys.platform == "win32":
            # Windows signal handling
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGBREAK, self._signal_handler)
        else:
            # Unix signal handling  
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Register cleanup on exit
        atexit.register(self._ensure_cleanup)
        logger.info("Signal handlers registered for graceful shutdown")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        if self._shutting_down:
            return  # Already shutting down
        
        self._shutting_down = True
        signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
        self._print("\n🛑", "SHUTDOWN", f"Received {signal_name}, shutting down gracefully...")
        self._graceful_shutdown()
        sys.exit(0)
    
    def _ensure_cleanup(self):
        """Ensure cleanup is performed on exit."""
        if not self._shutting_down:
            self._shutting_down = True
            self._graceful_shutdown()
    
    def _graceful_shutdown(self):
        """Perform graceful shutdown of all services."""
        # Only print if we're actually shutting down services
        if hasattr(self, 'process_manager') and self.process_manager.processes:
            self._print("🔄", "CLEANUP", "Starting graceful shutdown...")
        else:
            return  # Nothing to shutdown
        
        # Stop health monitoring first
        if hasattr(self, 'health_monitor'):
            self.health_monitor.stop()
        
        # Cleanup all processes with proper termination
        if hasattr(self, 'process_manager'):
            self._terminate_all_services()
        
        # Stop log streamers
        if hasattr(self, 'log_manager'):
            self.log_manager.stop_all()
        
        # Cleanup optimizers
        if hasattr(self, 'startup_optimizer'):
            self.startup_optimizer.cleanup()
        
        # Verify ports are freed
        self._verify_ports_freed()
        
        # Only print completion if we actually shut down services
        if hasattr(self, 'process_manager') and self.process_manager.processes:
            self._print("✅", "SHUTDOWN", "Graceful shutdown complete")
    
    def _terminate_all_services(self):
        """Terminate all services in proper order."""
        services_order = ["Frontend", "Backend", "Auth"]
        
        for service_name in services_order:
            if self.process_manager.is_running(service_name):
                self._print("🛑", "STOP", f"Stopping {service_name} service...")
                if self.process_manager.terminate_process(service_name):
                    self._print("✅", "STOPPED", f"{service_name} terminated")
                else:
                    self._print("⚠️", "WARN", f"{service_name} termination failed")
        
        # Final cleanup of any remaining processes
        self.process_manager.cleanup_all()
    
    def _verify_ports_freed(self):
        """Verify that service ports are freed."""
        ports_to_check = [
            (8081, "Auth"),
            (self.config.backend_port or 8000, "Backend"),
            (self.config.frontend_port or 3000, "Frontend")
        ]
        
        for port, service in ports_to_check:
            if self._is_port_in_use(port):
                self._print("⚠️", "PORT", f"Port {port} ({service}) may still be in use")
                self._force_free_port(port)
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return False
            except:
                return True
    
    def _force_free_port(self, port: int):
        """Force free a port cross-platform."""
        if sys.platform == "win32":
            try:
                import subprocess
                result = subprocess.run(
                    f"netstat -ano | findstr :{port}",
                    shell=True, capture_output=True, text=True
                )
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            if pid.isdigit():
                                subprocess.run(f"taskkill //F //PID {pid}", shell=True)
                                self._print("✅", "PORT", f"Freed port {port}")
            except Exception as e:
                logger.error(f"Failed to free port {port}: {e}")
        elif sys.platform == "darwin":
            try:
                import subprocess
                result = subprocess.run(
                    f"lsof -ti :{port}",
                    shell=True, capture_output=True, text=True
                )
                if result.stdout:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.isdigit():
                            subprocess.run(f"kill -9 {pid}", shell=True)
                            self._print("✅", "PORT", f"Freed port {port}")
            except Exception as e:
                logger.error(f"Failed to free port {port}: {e}")
    
    def _setup_new_cache_system(self):
        """Setup new cache and optimization system."""
        self.cache_manager = CacheManager(self.config.project_root)
        self.startup_optimizer = StartupOptimizer(self.cache_manager)
        self.parallel_enabled = getattr(self.config, 'parallel_startup', True)
        self._register_optimization_steps()
    
    def _register_optimization_steps(self):
        """Register startup optimization steps."""
        steps = [
            StartupStep("environment_check", self._check_environment_step, [], True, 10, True, "env_check"),
            StartupStep("migration_check", self._check_migrations_step, ["environment_check"], True, 15, True, "migration_check"),
            StartupStep("backend_deps", self._check_backend_deps, [], True, 20, False, "backend_deps"),
            StartupStep("auth_deps", self._check_auth_deps, [], True, 20, False, "auth_deps"),
            StartupStep("frontend_deps", self._check_frontend_deps, ["backend_deps"], True, 30, False, "frontend_deps"),
        ]
        self.startup_optimizer.register_steps(steps)
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def check_environment(self) -> bool:
        """Check if environment is ready for launch."""
        if not self.cache_manager.has_environment_changed():
            self._print("✅", "CACHE", "Environment unchanged, skipping checks")
            return True
        result = self.environment_checker.check_environment()
        # Check for critical environment variables
        self._check_critical_env_vars()
        return result
    
    def _check_critical_env_vars(self):
        """Check critical environment variables."""
        critical_vars = [
            "DATABASE_URL",
            "JWT_SECRET_KEY"
        ]
        for var in critical_vars:
            value = os.environ.get(var)
            if not value:
                critical_handler.check_env_var(var, value)
    
    def _check_environment_step(self) -> bool:
        """Environment check step for optimizer."""
        return self.environment_checker.check_environment()
    
    def _check_migrations_step(self) -> bool:
        """Migration check step for optimizer."""
        return not self.cache_manager.has_migration_files_changed()
    
    def run_migrations(self, env: Optional[Dict] = None) -> bool:
        """Run database migrations if needed."""
        return self.migration_runner.check_and_run_migrations(env)
    
    def _check_backend_deps(self) -> bool:
        """Backend dependencies check step."""
        return not self.cache_manager.has_dependencies_changed("backend")
    
    def _check_auth_deps(self) -> bool:
        """Auth dependencies check step."""
        return not self.cache_manager.has_dependencies_changed("auth")
    
    def _check_frontend_deps(self) -> bool:
        """Frontend dependencies check step."""
        return not self.cache_manager.has_dependencies_changed("frontend")
    
    
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
            self.config.show_env_var_debug_info()
        return result
    
    def register_health_monitoring(self):
        """Register health monitoring after services are verified ready."""
        self.health_helper.register_all_services(
            self.service_startup.backend_health_info,
            self.service_startup.frontend_health_info,
            self.service_startup.auth_health_info
        )
    
    def run(self) -> int:
        """Run the development environment."""
        try:
            if not self.config.silent_mode:
                self._print_startup_banner()
                self.config.show_configuration()
            
            # Start timing
            self.startup_optimizer.start_timing()
            
            # Run pre-checks
            if not self._run_pre_checks():
                return 1
            
            # Run services
            return self._run_services()
        except CriticalError as e:
            # Handle critical errors
            critical_handler.exit_on_critical(e)
            return e.get_exit_code()
        except Exception as e:
            logger.error(f"Unexpected error during startup: {e}")
            return 1
    
    
    def _run_services(self) -> int:
        """Run all services."""
        self._clear_service_discovery()
        
        try:
            # Start services using the unified service startup coordinator
            success = self.service_startup.start_all_services(
                self.process_manager,
                self.health_monitor,
                parallel=self.parallel_enabled
            )
            
            if not success:
                self._print("❌", "ERROR", "Failed to start services")
                return 1
            
            # Register health monitoring
            self.register_health_monitoring()
            
            # Start health monitoring
            self.health_monitor.start()
            
            # Show summary
            self.summary_display.show_success_summary()
            
            # Monitor services
            self._monitor_services()
            return 0
            
        except KeyboardInterrupt:
            self._print("\n🛑", "SHUTDOWN", "Interrupted by user")
            return 0
        except Exception as e:
            logger.error(f"Service startup failed: {e}")
            return 1
    
    
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
    
    def _monitor_services(self):
        """Monitor running services."""
        try:
            # Wait for all processes
            self.process_manager.wait_for_all()
        except KeyboardInterrupt:
            self._print("\n🛑", "SHUTDOWN", "Interrupted by user")
        except Exception as e:
            logger.error(f"Service monitoring error: {e}")
            self._print("❌", "ERROR", f"Service monitoring failed: {str(e)[:100]}")
    
    def _run_main_loop(self):
        """Run main service loop."""
        # Note: Health monitoring is now started in launcher_integration._show_final_summary
        # after services are verified ready (per HEALTH-001)
        self._execute_process_loop()
    
    def _execute_process_loop(self):
        """Execute main process loop."""
        try:
            self.process_manager.wait_for_all()
        except KeyboardInterrupt:
            if not self._shutting_down:
                self._print("\n🔄", "INTERRUPT", "Received interrupt signal")
                self._shutting_down = True
        except Exception as e:
            self._handle_main_loop_exception(e)
    
    def _handle_main_loop_exception(self, e: Exception):
        """Handle main loop exception."""
        logger.error(f"Unexpected error: {e}")
        self._print("❌", "ERROR", f"Unexpected error: {str(e)[:100]}")
    
    def _handle_cleanup(self) -> int:
        """Handle cleanup and return exit code."""
        if self._shutting_down:
            return 0  # Already handled by graceful shutdown
        
        # Prevent duplicate cleanup from atexit handler
        self._shutting_down = True
        
        # Show startup time and optimization report
        elapsed = time.time() - self.startup_time
        self._print("⏱️", "TIME", f"Total startup time: {elapsed:.1f}s")
        
        # Show optimization report
        if self.config.verbose:
            timing_report = self.startup_optimizer.get_timing_report()
            self._print("📊", "PERF", f"Target met: {timing_report['target_met']}")
            if timing_report['cached_steps']:
                self._print("⚡", "CACHE", f"Cached steps: {len(timing_report['cached_steps'])}")
        
        # Save successful run to cache
        self.cache_manager.mark_successful_startup(elapsed)
        
        # Perform graceful shutdown if needed
        if hasattr(self, 'process_manager') and self.process_manager.processes:
            self._graceful_shutdown()
        
        if not self.health_monitor.all_healthy():
            self._print("⚠️", "WARN", "Some services were unhealthy during execution")
            return 1
        return 0