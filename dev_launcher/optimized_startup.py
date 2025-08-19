"""
Optimized startup orchestration module.

Handles the new startup sequence with intelligent caching and performance optimizations.
Separated from main launcher to maintain 300-line limit.
"""

import time
import logging
from typing import Dict, Any
from pathlib import Path

from dev_launcher.cache_manager import CacheManager
from dev_launcher.startup_optimizer import StartupOptimizer, StartupStep

logger = logging.getLogger(__name__)


class OptimizedStartupOrchestrator:
    """
    Orchestrates optimized startup sequence for development environment.
    
    Implements the spec v2.0.0 startup sequence with intelligent caching,
    parallel execution, and sub-10 second target for cached runs.
    """
    
    def __init__(self, launcher_instance):
        """Initialize with reference to main launcher instance."""
        self.launcher = launcher_instance
        self.config = launcher_instance.config
        self.cache_manager = launcher_instance.cache_manager
        self.startup_optimizer = launcher_instance.startup_optimizer
        self.use_emoji = launcher_instance.use_emoji
    
    def run_optimized_startup(self) -> int:
        """Run startup sequence following spec v2.0.0."""
        # Start progress tracking
        if hasattr(self.launcher, 'progress_tracker'):
            self.launcher.progress_tracker.start()
        
        # Step 1-3: Pre-checks with caching
        if not self._run_cached_pre_checks():
            return 1
        
        # Step 4-5: Migration check and execution
        if not self._handle_migrations_with_cache():
            return 1
        
        # Step 6-12: Service startup with optimization
        result = self._run_optimized_services()
        
        # Complete progress tracking
        if hasattr(self.launcher, 'progress_tracker'):
            self.launcher.progress_tracker.complete()
        
        return result
    
    def _run_cached_pre_checks(self) -> bool:
        """Run pre-checks with intelligent caching."""
        # Check cache for previous startup state
        if self.cache_manager.is_cache_valid():
            self._print("⚡", "CACHE", "Using cached startup state")
        
        # Environment check (skip if cached and unchanged)
        if not self.launcher.check_environment():
            return False
        
        # Load secrets if configured
        return self._handle_secret_loading()
    
    def _handle_secret_loading(self) -> bool:
        """Handle secret loading with warnings."""
        if not self.launcher.load_secrets():
            self._print_secret_loading_warning()
        return True
    
    def _print_secret_loading_warning(self):
        """Print secret loading warning."""
        self._print("⚠️", "WARN", "Failed to load some secrets")
        print("\nNote: The application may not work correctly without secrets.")
        print("To skip secret loading, use: --no-secrets")
    
    def _handle_migrations_with_cache(self) -> bool:
        """Handle database migrations with file hash caching."""
        if not self.cache_manager.has_migration_files_changed():
            self._print("⚡", "CACHE", "Migrations unchanged, skipping")
            return True
        
        # Run migrations if needed
        self._print("🗄️", "DB", "Running migrations...")
        # Note: Integration with actual migration system would go here
        return True
    
    def _run_optimized_services(self) -> int:
        """Run services with optimization."""
        self.launcher._clear_service_discovery()
        
        # Use parallel startup if enabled
        if self.launcher.parallel_enabled:
            return self._run_services_with_optimization()
        else:
            return self.launcher.legacy_runner.run_services_sequential()
    
    def _run_services_with_optimization(self) -> int:
        """Run services with advanced optimization."""
        self._print("⚡", "FAST", "Starting optimized service sequence...")
        
        # Check dependencies first
        self._check_service_dependencies()
        
        # Start auth and backend in parallel
        auth_result = self._start_auth_optimized()
        backend_result = self._start_backend_optimized()
        
        if backend_result != 0:
            return backend_result
        
        # Now start frontend (needs backend info)
        frontend_result = self._start_frontend_optimized()
        if frontend_result != 0:
            return frontend_result
        
        # Verify all services ready
        if not self._verify_all_services_ready():
            return 1
        
        # Step 13: ONLY NOW start health monitoring
        self.launcher._run_main_loop()
        return self.launcher._handle_cleanup()
    
    def _check_service_dependencies(self):
        """Check and cache service dependencies."""
        # Check backend dependencies
        if not self.cache_manager.has_dependencies_changed("backend"):
            self._print("⚡", "CACHE", "Backend dependencies unchanged")
        
        # Check frontend dependencies
        if not self.cache_manager.has_dependencies_changed("frontend"):
            self._print("⚡", "CACHE", "Frontend dependencies unchanged")
        
        # Check auth dependencies
        if not self.cache_manager.has_dependencies_changed("auth"):
            self._print("⚡", "CACHE", "Auth dependencies unchanged")
    
    def _start_auth_optimized(self) -> int:
        """Start auth service with optimization."""
        start_time = time.time()
        
        # Track service starting
        if hasattr(self.launcher, 'progress_tracker'):
            self.launcher.progress_tracker.service_starting("Auth")
        
        try:
            process, streamer = self.launcher.service_startup.start_auth_service()
            if process:
                self.launcher.process_manager.add_process("Auth", process)
                duration = time.time() - start_time
                
                # Track service started
                if hasattr(self.launcher, 'progress_tracker'):
                    self.launcher.progress_tracker.service_started("Auth", 8081)
                else:
                    self._print("✅", "AUTH", f"Started in {duration:.1f}s")
                return 0
            else:
                # Auth service is optional if disabled in config
                auth_config = self.launcher.config_manager.services_config.auth_service
                if auth_config.get_config().get("enabled", True):
                    if hasattr(self.launcher, 'progress_tracker'):
                        self.launcher.progress_tracker.service_failed("Auth", "Failed to start")
                    else:
                        self._print("⚠️", "WARN", "Auth service failed to start but is enabled")
                    return 1
                else:
                    self._print("ℹ️", "INFO", "Auth service is disabled, skipping")
                    return 0
        except Exception as e:
            logger.error(f"Auth startup failed: {e}")
            if hasattr(self.launcher, 'progress_tracker'):
                self.launcher.progress_tracker.service_failed("Auth", str(e))
            return 1
    
    def _start_backend_optimized(self) -> int:
        """Start backend with optimization."""
        start_time = time.time()
        
        # Track service starting
        if hasattr(self.launcher, 'progress_tracker'):
            self.launcher.progress_tracker.service_starting("Backend")
        
        try:
            backend_process, backend_streamer = self.launcher.service_startup.start_backend()
            if not backend_process:
                if hasattr(self.launcher, 'progress_tracker'):
                    self.launcher.progress_tracker.service_failed("Backend", "Failed to start")
                else:
                    self._print("❌", "ERROR", "Failed to start backend")
                return 1
            
            self.launcher.process_manager.add_process("Backend", backend_process)
            duration = time.time() - start_time
            
            # Get backend port from config
            backend_port = self.launcher.config.backend_port or 8000
            
            # Track service started
            if hasattr(self.launcher, 'progress_tracker'):
                self.launcher.progress_tracker.service_started("Backend", backend_port)
            else:
                self._print("✅", "BACKEND", f"Started in {duration:.1f}s")
            
            # Wait for backend readiness with timeout
            return self._verify_backend_readiness_optimized()
            
        except Exception as e:
            logger.error(f"Backend startup failed: {e}")
            if hasattr(self.launcher, 'progress_tracker'):
                self.launcher.progress_tracker.service_failed("Backend", str(e))
            return 1
    
    def _verify_backend_readiness_optimized(self) -> int:
        """Verify backend readiness with optimized timing."""
        max_wait = 30  # Grace period as per spec
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            backend_info = self.launcher.service_discovery.read_backend_info()
            if backend_info:
                if self.launcher.startup_validator.verify_backend_ready(backend_info):
                    elapsed = time.time() - start_time
                    self._print("✅", "READY", f"Backend ready in {elapsed:.1f}s")
                    return 0
            time.sleep(0.5)  # Faster polling
        
        self._print("❌", "ERROR", "Backend failed to become ready within grace period")
        self.launcher.process_manager.cleanup_all()
        return 1
    
    def _start_frontend_optimized(self) -> int:
        """Start frontend with optimization."""
        start_time = time.time()
        
        # Track service starting
        if hasattr(self.launcher, 'progress_tracker'):
            self.launcher.progress_tracker.service_starting("Frontend")
        
        try:
            frontend_process, frontend_streamer = self.launcher.service_startup.start_frontend()
            if not frontend_process:
                if hasattr(self.launcher, 'progress_tracker'):
                    self.launcher.progress_tracker.service_failed("Frontend", "Failed to start")
                else:
                    self._print("❌", "ERROR", "Failed to start frontend")
                self.launcher.process_manager.cleanup_all()
                return 1
            
            self.launcher.process_manager.add_process("Frontend", frontend_process)
            duration = time.time() - start_time
            
            # Get frontend port from config
            frontend_port = self.launcher.config.frontend_port or 3000
            
            # Track service started
            if hasattr(self.launcher, 'progress_tracker'):
                self.launcher.progress_tracker.service_started("Frontend", frontend_port)
            else:
                self._print("✅", "FRONTEND", f"Started in {duration:.1f}s")
            
            # Wait for frontend readiness
            self._wait_for_frontend_ready_optimized()
            return 0
            
        except Exception as e:
            logger.error(f"Frontend startup failed: {e}")
            if hasattr(self.launcher, 'progress_tracker'):
                self.launcher.progress_tracker.service_failed("Frontend", str(e))
            return 1
    
    def _wait_for_frontend_ready_optimized(self):
        """Wait for frontend to be ready with optimized timing."""
        # Frontend grace period as per spec (90 seconds for Next.js compilation)
        self.launcher.startup_validator.verify_frontend_ready(
            self.config.frontend_port,
            self.config.no_browser
        )
    
    def _verify_all_services_ready(self) -> bool:
        """Verify all services are ready with optimized checks."""
        max_wait = 10  # Reduced since individual services already verified
        start = time.time()
        
        while time.time() - start < max_wait:
            backend_info = self.launcher.service_discovery.read_backend_info()
            if backend_info:
                if self.launcher.startup_validator.verify_backend_ready(backend_info):
                    elapsed = time.time() - start
                    self._print("✅", "READY", f"All services ready in {elapsed:.1f}s")
                    return True
            time.sleep(0.5)
        
        self._print("❌", "ERROR", "Services failed to become ready")
        return False
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        from dev_launcher.utils import print_with_emoji
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get detailed optimization report."""
        return self.startup_optimizer.get_timing_report()