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
from dev_launcher.database_connector import DatabaseConnector

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
        self.database_connector = DatabaseConnector(self.use_emoji)
    
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
        
        # Stop database monitoring and cleanup connections
        if hasattr(self, 'database_connector'):
            asyncio.run(self.database_connector.stop_health_monitoring())
        
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
            StartupStep("database_check", self._check_database_step, ["environment_check"], True, 15, True, "database_check"),
            StartupStep("migration_check", self._check_migrations_step, ["database_check"], True, 15, True, "migration_check"),
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
    
    def _check_database_step(self) -> bool:
        """Database connectivity check step for optimizer."""
        # For cache purposes, always return False to force database validation
        return False
    
    def _check_migrations_step(self) -> bool:
        """Migration check step for optimizer."""
        return not self.cache_manager.has_migration_files_changed()
    
    async def _validate_databases(self) -> bool:
        """Validate database connections before service startup."""
        try:
            return await self.database_connector.validate_all_connections()
        except Exception as e:
            logger.error(f"Database validation failed: {e}")
            self._print("❌", "DATABASE", f"Validation error: {str(e)}")
            return False
    
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
        """Register health monitoring after services are verified ready.
        
        Per SPEC: This registration happens but monitoring doesn't start until
        all services are confirmed ready and grace periods have elapsed.
        """
        self.health_helper.register_all_services(
            self.service_startup.backend_health_info,
            self.service_startup.frontend_health_info,
            self.service_startup.auth_health_info
        )
    
    async def run(self) -> int:
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
            return await self._run_services()
        except CriticalError as e:
            # Handle critical errors
            critical_handler.exit_on_critical(e)
            return e.get_exit_code()
        except Exception as e:
            logger.error(f"Unexpected error during startup: {e}")
            return 1
    
    
    async def _run_services(self) -> int:
        """Run all services following SPEC startup sequence steps 1-13."""
        self._clear_service_discovery()
        
        try:
            # Follow SPEC service_startup_sequence steps 1-13
            success = await self._execute_spec_startup_sequence()
            
            if not success:
                self._print("❌", "ERROR", "Failed to start services")
                return 1
            
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
    
    async def _execute_spec_startup_sequence(self) -> bool:
        """Execute SPEC startup sequence steps 1-13.
        
        Per SPEC/dev_launcher.xml service_startup_sequence:
        Steps 1-12: Service startup and readiness verification
        Step 13: ONLY NOW start health monitoring
        """
        try:
            # Steps 1-5: Cache, environment, secrets, database validation, migrations
            self._print("🔄", "STEP 1-2", "Checking cache and environment...")
            # (Already done in pre-checks)
            
            self._print("🔄", "STEP 3", "Loading secrets...")
            # (Already done in pre-checks)
            
            self._print("🔄", "STEP 4", "Validating database connections...")
            if not await self._validate_databases():
                self._print("❌", "ERROR", "Database validation failed")
                return False
            
            self._print("🔄", "STEP 5", "Checking and running migrations...")
            if not self.run_migrations():
                self._print("❌", "ERROR", "Migration check failed")
                return False
            
            # Step 6-7: Start backend and auth processes
            self._print("🔄", "STEP 6-7", "Starting backend and auth services...")
            backend_result = self.service_startup.start_backend()
            auth_result = self.service_startup.start_auth_service()
            
            if not backend_result[0] or not auth_result[0]:
                self._print("❌", "ERROR", "Failed to start backend or auth service")
                return False
            
            # Register processes
            self.process_manager.add_process("Backend", backend_result[0])
            self.process_manager.add_process("Auth", auth_result[0])
            
            # Step 8: Wait for backend readiness (/health/ready)
            self._print("🔄", "STEP 8", "Waiting for backend readiness...")
            if not self._wait_for_backend_readiness():
                self._print("❌", "ERROR", "Backend readiness check failed")
                return False
            
            # Step 9: Verify auth system (/api/auth/config)
            self._print("🔄", "STEP 9", "Verifying auth system...")
            if not self._verify_auth_system():
                self._print("❌", "ERROR", "Auth system verification failed")
                return False
            
            # Step 10: Start frontend process
            self._print("🔄", "STEP 10", "Starting frontend service...")
            frontend_result = self.service_startup.start_frontend()
            
            if not frontend_result[0]:
                self._print("❌", "ERROR", "Failed to start frontend service")
                return False
            
            self.process_manager.add_process("Frontend", frontend_result[0])
            
            # Step 11: Wait for frontend readiness
            self._print("🔄", "STEP 11", "Waiting for frontend readiness...")
            if not self._wait_for_frontend_readiness():
                self._print("❌", "ERROR", "Frontend readiness check failed")
                return False
            
            # Step 12: Cache successful startup state
            self._print("🔄", "STEP 12", "Caching successful startup state...")
            self.cache_manager.mark_successful_startup(time.time() - self.startup_time)
            
            # Step 13: ONLY NOW start health monitoring
            self._print("🔄", "STEP 13", "Starting health monitoring...")
            self._start_health_monitoring_after_readiness()
            
            # Start database health monitoring
            await self.database_connector.start_health_monitoring()
            
            return True
            
        except Exception as e:
            logger.error(f"Startup sequence failed: {e}")
            return False
    
    def _wait_for_backend_readiness(self, timeout: int = 30) -> bool:
        """Wait for backend /health/ready endpoint per SPEC step 8."""
        import requests
        start_time = time.time()
        backend_port = self.config.backend_port or 8000
        ready_url = f"http://localhost:{backend_port}/health/ready"
        
        while (time.time() - start_time) < timeout:
            try:
                response = requests.get(ready_url, timeout=5)
                if response.status_code == 200:
                    self._print("✅", "READY", "Backend is ready")
                    # Mark service as ready in health monitor
                    self.health_monitor.mark_service_ready("Backend")
                    return True
            except Exception as e:
                logger.debug(f"Backend readiness check: {e}")
            
            time.sleep(1)
        
        return False
    
    def _verify_auth_system(self, timeout: int = 15) -> bool:
        """Verify auth system /api/auth/config per SPEC step 9."""
        import requests
        start_time = time.time()
        auth_port = 8081  # Auth service port
        auth_config_url = f"http://localhost:{auth_port}/api/auth/config"
        
        while (time.time() - start_time) < timeout:
            try:
                response = requests.get(auth_config_url, timeout=5)
                if response.status_code in [200, 404]:  # 404 is acceptable
                    self._print("✅", "READY", "Auth system verified")
                    # Mark service as ready in health monitor
                    self.health_monitor.mark_service_ready("Auth")
                    return True
            except Exception as e:
                logger.debug(f"Auth verification: {e}")
            
            time.sleep(1)
        
        return False
    
    def _wait_for_frontend_readiness(self, timeout: int = 90) -> bool:
        """Wait for frontend readiness per SPEC step 11 (90s grace period)."""
        import requests
        start_time = time.time()
        frontend_port = self.config.frontend_port or 3000
        frontend_url = f"http://localhost:{frontend_port}"
        
        while (time.time() - start_time) < timeout:
            try:
                response = requests.get(frontend_url, timeout=5)
                if response.status_code in [200, 404]:  # Frontend can return 404
                    self._print("✅", "READY", "Frontend is ready")
                    # Mark service as ready in health monitor
                    self.health_monitor.mark_service_ready("Frontend")
                    return True
            except Exception as e:
                logger.debug(f"Frontend readiness check: {e}")
            
            time.sleep(2)  # Longer interval for frontend
        
        return False
    
    def _start_health_monitoring_after_readiness(self):
        """Start health monitoring only after all services are ready per SPEC step 13.
        
        Per SPEC HEALTH-001: Health monitoring MUST NOT start immediately after service launch.
        Only AFTER startup verification should health monitoring begin.
        """
        # Register health monitoring for all services
        self.register_health_monitoring()
        
        # Start the health monitor thread (but monitoring is disabled)
        self.health_monitor.start()
        
        # Enable monitoring only after all services are confirmed ready
        if self.health_monitor.all_services_ready():
            self.health_monitor.enable_monitoring()
            self._print("✅", "MONITORING", "Health monitoring enabled")
        else:
            self._print("⚠️", "WARNING", "Not all services ready - health monitoring delayed")
    
    
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