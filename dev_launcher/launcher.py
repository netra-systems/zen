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
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future

from dev_launcher.config import LauncherConfig
from dev_launcher.environment_checker import EnvironmentChecker
from dev_launcher.config_manager import ConfigManager
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
        self._load_env_file()  # Load .env file first
        self._setup_cache()  # Setup caching for optimizations
        self._setup_parallel_executor()  # Setup parallel execution
        self._setup_managers()
        self._setup_components()
        self._setup_helpers()
        self._setup_logging()
        self.startup_time = time.time()
    
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
    
    def _setup_helpers(self):
        """Setup helper instances."""
        self.health_helper = HealthRegistrationHelper(self.health_monitor, self.use_emoji)
        self.startup_validator = StartupValidator(self.use_emoji)
    
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
            self.config, self.config_manager.services_config,
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
        self.config_manager.log_verbose_config()
    
    def _setup_cache(self):
        """Setup startup cache for optimizations."""
        self.cache_dir = self.config.project_root / ".dev_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "startup_cache.json"
        self.cache_data = self._load_cache_data()
    
    def _load_cache_data(self) -> dict:
        """Load cache data from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache_data(self):
        """Save cache data to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache_data, f, indent=2)
        except:
            pass
    
    def _setup_parallel_executor(self):
        """Setup thread pool for parallel execution."""
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.service_futures = {}
        self.parallel_enabled = getattr(self.config, 'parallel_startup', True)
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def check_environment(self) -> bool:
        """Check if environment is ready for launch."""
        # Use cache to skip if unchanged
        env_hash = self._get_environment_hash()
        if not self._has_changed('env_hash', env_hash):
            self._print("✅", "CACHE", "Environment unchanged, skipping checks")
            return True
        return self.environment_checker.check_environment()
    
    def _get_environment_hash(self) -> str:
        """Get hash of current environment."""
        env_data = {
            'python': sys.version,
            'platform': sys.platform,
            'root': str(self.config.project_root),
            'paths': [str(p) for p in [self.config.project_root / 'app',
                                       self.config.project_root / 'frontend']]
        }
        return hashlib.md5(json.dumps(env_data, sort_keys=True).encode()).hexdigest()
    
    def _has_changed(self, key: str, value: str) -> bool:
        """Check if value has changed since last run."""
        old_value = self.cache_data.get(key)
        changed = old_value != value
        if changed:
            self.cache_data[key] = value
            self._save_cache_data()
        return changed
    
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
        self.health_helper.register_all_services(
            self.service_startup.backend_health_info,
            self.service_startup.frontend_health_info,
            self.service_startup.auth_health_info
        )
    
    def run(self) -> int:
        """Run the development environment."""
        self._print_startup_banner()
        self.config_manager.show_configuration()
        if not self._run_pre_checks():
            return 1
        return self._run_services()
    
    def _run_services(self) -> int:
        """Run all services."""
        self._clear_service_discovery()
        
        # Use parallel startup if enabled
        if self.parallel_enabled:
            return self._run_services_parallel()
        else:
            return self._run_services_sequential()
    
    def _run_services_sequential(self) -> int:
        """Run services sequentially (original behavior)."""
        auth_result = self._start_and_verify_auth()
        if auth_result != 0:
            return auth_result
        backend_result = self._start_and_verify_backend()
        if backend_result != 0:
            return backend_result
        return self._start_and_run_services()
    
    def _run_services_parallel(self) -> int:
        """Run services in parallel for faster startup."""
        self._print("⚡", "FAST", "Starting services in parallel...")
        
        # Start auth and backend in parallel
        auth_future = self.executor.submit(self._start_auth_parallel)
        backend_future = self.executor.submit(self._start_backend_parallel)
        
        # Wait for backend to start before frontend (needs backend port)
        try:
            backend_started = backend_future.result(timeout=30)
            auth_started = auth_future.result(timeout=30)
        except Exception as e:
            logger.error(f"Service startup failed: {e}")
            self.process_manager.cleanup_all()
            return 1
        
        if not backend_started:
            self._print("❌", "ERROR", "Backend failed to start")
            self.process_manager.cleanup_all()
            return 1
        
        # Now start frontend (it needs backend info)
        frontend_started = self._start_frontend_parallel()
        if not frontend_started:
            self._print("❌", "ERROR", "Frontend failed to start")
            self.process_manager.cleanup_all()
            return 1
        
        # Verify all services ready
        if not self._verify_all_services_ready():
            return 1
        
        self._run_main_loop()
        return self._handle_cleanup()
    
    def _start_auth_parallel(self) -> bool:
        """Start auth service in parallel."""
        try:
            process, streamer = self.service_startup.start_auth_service()
            if process:
                self.process_manager.add_process("Auth", process)
                return True
        except:
            pass
        return False
    
    def _start_backend_parallel(self) -> bool:
        """Start backend in parallel."""
        try:
            process, streamer = self.service_startup.start_backend()
            if process:
                self.process_manager.add_process("Backend", process)
                return True
        except Exception as e:
            logger.error(f"Backend start failed: {e}")
        return False
    
    def _start_frontend_parallel(self) -> bool:
        """Start frontend in parallel."""
        try:
            process, streamer = self.service_startup.start_frontend()
            if process:
                self.process_manager.add_process("Frontend", process)
                return True
        except Exception as e:
            logger.error(f"Frontend start failed: {e}")
        return False
    
    def _verify_all_services_ready(self) -> bool:
        """Verify all services are ready."""
        max_wait = 30
        start = time.time()
        
        while time.time() - start < max_wait:
            backend_info = self.service_discovery.read_backend_info()
            if backend_info:
                if self.startup_validator.verify_backend_ready(backend_info):
                    self._wait_for_frontend_ready()
                    return True
            time.sleep(1)
        
        self._print("❌", "ERROR", "Services failed to become ready")
        return False
    
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
    
    def _start_and_verify_auth(self) -> int:
        """Start and verify auth service."""
        auth_process, auth_streamer = self.service_startup.start_auth_service()
        if not auth_process:
            # Auth service is optional if disabled in config
            auth_config = self.config_manager.services_config.auth_service
            if auth_config.get_config().get("enabled", True):
                self._print("⚠️", "WARN", "Auth service failed to start but is enabled")
                return 1
            else:
                self._print("ℹ️", "INFO", "Auth service is disabled, skipping")
                return 0
        self.process_manager.add_process("Auth", auth_process)
        return self._verify_auth_readiness()
    
    def _verify_auth_readiness(self) -> int:
        """Verify auth service readiness."""
        auth_info = self.service_discovery.read_auth_info()
        if not auth_info:
            self._print("⚠️", "WARN", "Auth service info not found")
            return 0  # Continue anyway as auth is optional
        self._print("✅", "AUTH", f"Auth service ready at {auth_info.get('url')}")
        return 0
    
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
        return self._validate_backend_health(backend_info)
    
    def _validate_backend_health(self, backend_info: dict) -> int:
        """Validate backend health status."""
        if not self.startup_validator.verify_backend_ready(backend_info):
            self._handle_backend_failure()
            return 1
        return 0
    
    
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
            return self._handle_frontend_failure()
        self.process_manager.add_process("Frontend", frontend_process)
        self._wait_for_frontend_ready()
        return 0
    
    def _handle_frontend_failure(self) -> int:
        """Handle frontend startup failure."""
        self._print("❌", "ERROR", "Failed to start frontend")
        self.process_manager.cleanup_all()
        return 1
    
    def _wait_for_frontend_ready(self):
        """Wait for frontend to be ready."""
        self.startup_validator.verify_frontend_ready(
            self.config.frontend_port,
            self.config.no_browser
        )
    
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
        # Show startup time
        elapsed = time.time() - self.startup_time
        self._print("⏱️", "TIME", f"Total startup time: {elapsed:.1f}s")
        
        # Save successful run to cache
        self.cache_data['last_run'] = datetime.now().isoformat()
        self._save_cache_data()
        
        # Cleanup
        self.health_monitor.stop()
        self.process_manager.cleanup_all()
        self.log_manager.stop_all()
        self.executor.shutdown(wait=False)
        
        if not self.health_monitor.all_healthy():
            self._print("⚠️", "WARN", "Some services were unhealthy during execution")
            return 1
        return 0