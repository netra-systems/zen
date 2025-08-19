"""
Legacy service running methods.

Contains the old sequential and parallel service startup methods
to maintain backwards compatibility while keeping main launcher under 300 lines.
"""

import time
import logging
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, Future

logger = logging.getLogger(__name__)


class LegacyServiceRunner:
    """
    Contains legacy service startup methods for backwards compatibility.
    
    These methods provide the original sequential and parallel startup
    logic for cases where the optimized startup isn't used.
    """
    
    def __init__(self, launcher_instance):
        """Initialize with reference to main launcher instance."""
        self.launcher = launcher_instance
        self.config = launcher_instance.config
        self.use_emoji = launcher_instance.use_emoji
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.service_futures = {}
    
    def run_services_sequential(self) -> int:
        """Run services sequentially (original behavior)."""
        auth_result = self._start_and_verify_auth()
        if auth_result != 0:
            return auth_result
        backend_result = self._start_and_verify_backend()
        if backend_result != 0:
            return backend_result
        return self._start_and_run_services()
    
    def run_services_parallel(self) -> int:
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
            self.launcher.process_manager.cleanup_all()
            return 1
        
        if not backend_started:
            self._print("❌", "ERROR", "Backend failed to start")
            self.launcher.process_manager.cleanup_all()
            return 1
        
        # Now start frontend (it needs backend info)
        frontend_started = self._start_frontend_parallel()
        if not frontend_started:
            self._print("❌", "ERROR", "Frontend failed to start")
            self.launcher.process_manager.cleanup_all()
            return 1
        
        # Verify all services ready
        if not self._verify_all_services_ready():
            return 1
        
        self.launcher._run_main_loop()
        return self.launcher._handle_cleanup()
    
    def _start_auth_parallel(self) -> bool:
        """Start auth service in parallel."""
        try:
            process, streamer = self.launcher.service_startup.start_auth_service()
            if process:
                self.launcher.process_manager.add_process("Auth", process)
                return True
        except:
            pass
        return False
    
    def _start_backend_parallel(self) -> bool:
        """Start backend in parallel."""
        try:
            process, streamer = self.launcher.service_startup.start_backend()
            if process:
                self.launcher.process_manager.add_process("Backend", process)
                return True
        except Exception as e:
            logger.error(f"Backend start failed: {e}")
        return False
    
    def _start_frontend_parallel(self) -> bool:
        """Start frontend in parallel."""
        try:
            process, streamer = self.launcher.service_startup.start_frontend()
            if process:
                self.launcher.process_manager.add_process("Frontend", process)
                return True
        except Exception as e:
            logger.error(f"Frontend start failed: {e}")
        return False
    
    def _verify_all_services_ready(self) -> bool:
        """Verify all services are ready."""
        max_wait = 30
        start = time.time()
        
        while time.time() - start < max_wait:
            backend_info = self.launcher.service_discovery.read_backend_info()
            if backend_info:
                if self.launcher.startup_validator.verify_backend_ready(backend_info):
                    self._wait_for_frontend_ready()
                    return True
            time.sleep(1)
        
        self._print("❌", "ERROR", "Services failed to become ready")
        return False
    
    def _start_and_verify_auth(self) -> int:
        """Start and verify auth service."""
        auth_process, auth_streamer = self.launcher.service_startup.start_auth_service()
        if not auth_process:
            # Auth service is optional if disabled in config
            auth_config = self.launcher.config_manager.services_config.auth_service
            if auth_config.get_config().get("enabled", True):
                self._print("⚠️", "WARN", "Auth service failed to start but is enabled")
                return 1
            else:
                self._print("ℹ️", "INFO", "Auth service is disabled, skipping")
                return 0
        self.launcher.process_manager.add_process("Auth", auth_process)
        return self._verify_auth_readiness()
    
    def _verify_auth_readiness(self) -> int:
        """Verify auth service readiness."""
        auth_info = self.launcher.service_discovery.read_auth_info()
        if not auth_info:
            self._print("⚠️", "WARN", "Auth service info not found")
            return 0  # Continue anyway as auth is optional
        self._print("✅", "AUTH", f"Auth service ready at {auth_info.get('url')}")
        return 0
    
    def _start_and_verify_backend(self) -> int:
        """Start and verify backend."""
        backend_process, backend_streamer = self.launcher.service_startup.start_backend()
        if not backend_process:
            self._print("❌", "ERROR", "Failed to start backend")
            return 1
        self.launcher.process_manager.add_process("Backend", backend_process)
        return self._verify_backend_readiness()
    
    def _verify_backend_readiness(self) -> int:
        """Verify backend readiness."""
        backend_info = self.launcher.service_discovery.read_backend_info()
        if not backend_info:
            return 1
        return self._validate_backend_health(backend_info)
    
    def _validate_backend_health(self, backend_info: dict) -> int:
        """Validate backend health status."""
        if not self.launcher.startup_validator.verify_backend_ready(backend_info):
            self._handle_backend_failure()
            return 1
        return 0
    
    def _handle_backend_failure(self):
        """Handle backend failure."""
        self._print("❌", "ERROR", "Backend failed to start - check database connection")
        self.launcher.process_manager.cleanup_all()
    
    def _start_and_run_services(self) -> int:
        """Start and run all services."""
        frontend_result = self._start_and_verify_frontend()
        if frontend_result != 0:
            return frontend_result
        self.launcher._run_main_loop()
        return self.launcher._handle_cleanup()
    
    def _start_and_verify_frontend(self) -> int:
        """Start and verify frontend."""
        frontend_process, frontend_streamer = self.launcher.service_startup.start_frontend()
        if not frontend_process:
            return self._handle_frontend_failure()
        self.launcher.process_manager.add_process("Frontend", frontend_process)
        self._wait_for_frontend_ready()
        return 0
    
    def _handle_frontend_failure(self) -> int:
        """Handle frontend startup failure."""
        self._print("❌", "ERROR", "Failed to start frontend")
        self.launcher.process_manager.cleanup_all()
        return 1
    
    def _wait_for_frontend_ready(self):
        """Wait for frontend to be ready."""
        self.launcher.startup_validator.verify_frontend_ready(
            self.config.frontend_port,
            self.config.no_browser
        )
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        from dev_launcher.utils import print_with_emoji
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def cleanup(self):
        """Cleanup resources."""
        self.executor.shutdown(wait=False)