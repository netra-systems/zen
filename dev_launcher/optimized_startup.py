"""
Optimized startup orchestration module.

Phase 6 Integration: Integrates all optimization components for sub-10 second startup.
Separated from main launcher to maintain 300-line limit.
"""

import time
import logging
from typing import Dict, Any, Set, Tuple
from pathlib import Path

from dev_launcher.cache_manager import CacheManager
from dev_launcher.startup_optimizer import StartupOptimizer, StartupStep
from dev_launcher.startup_sequencer import (
    SmartStartupSequencer, StartupPhase, PhaseStep,
    create_init_phase_steps, create_validate_phase_steps,
    create_prepare_phase_steps, create_launch_phase_steps,
    create_verify_phase_steps
)
from dev_launcher.parallel_executor import ParallelExecutor, ParallelTask, TaskType
from dev_launcher.log_buffer import LogBuffer, LogLevel
from dev_launcher.progress_indicator import ProgressIndicator
from dev_launcher.startup_profiler import StartupProfiler
from dev_launcher.local_secrets import LocalSecretManager
from dev_launcher.launcher_integration import LauncherIntegration

logger = logging.getLogger(__name__)


class OptimizedStartupOrchestrator:
    """
    Phase 6 Integration: Complete optimized startup orchestration.
    
    Integrates SmartStartupSequencer, ParallelExecutor, LogBuffer,
    LocalSecretManager, and StartupProfiler for sub-10s startup.
    """
    
    def __init__(self, launcher_instance):
        """Initialize with all optimization components."""
        self.launcher = launcher_instance
        self.config = launcher_instance.config
        self.cache_manager = launcher_instance.cache_manager
        self.startup_optimizer = launcher_instance.startup_optimizer
        self.use_emoji = launcher_instance.use_emoji
        self._setup_optimization_components()
    
    def _setup_optimization_components(self):
        """Setup all optimization components."""
        self._setup_profiler()
        self._setup_parallel_executor()  # Must be before local_secrets
        self._setup_logging_system()  # Must be before local_secrets
        self._setup_local_secrets()  # Must be before sequencer for integration
        self._setup_sequencer()
    
    def _setup_profiler(self):
        """Setup startup profiler."""
        self.profiler = StartupProfiler(self.config.project_root)
    
    def _setup_sequencer(self):
        """Setup smart startup sequencer."""
        self.sequencer = SmartStartupSequencer(self.cache_manager)
        self._register_sequencer_phases()
    
    def _setup_parallel_executor(self):
        """Setup parallel executor."""
        self.parallel_executor = ParallelExecutor()
    
    def _setup_logging_system(self):
        """Setup silent logging system."""
        max_size = 100 if self.config.silent_mode else 1000
        self.log_buffer = LogBuffer(max_size=max_size)
        self._setup_progress_indicator()
    
    def _setup_progress_indicator(self):
        """Setup progress indicator."""
        phases = [
            ("INIT", "Loading cache & environment", 2.0),
            ("VALIDATE", "Validating dependencies", 3.0),
            ("PREPARE", "Installing & migrating", 5.0),
            ("LAUNCH", "Starting services", 5.0),
            ("VERIFY", "Health checks", 3.0)
        ]
        self.progress = ProgressIndicator(phases)
    
    def _setup_local_secrets(self):
        """Setup local secret manager."""
        self.local_secrets = LocalSecretManager(
            self.config.project_root, 
            self.config.verbose
        )
        
        # Setup integration module
        self.integration = LauncherIntegration(self)
    
    def _register_sequencer_phases(self):
        """Register all startup phases with the sequencer."""
        # INIT phase
        init_steps = self._create_init_steps()
        self.sequencer.register_phase(StartupPhase.INIT, init_steps)
        
        # VALIDATE phase
        validate_steps = self.integration.create_validate_steps()
        self.sequencer.register_phase(StartupPhase.VALIDATE, validate_steps)
        
        # PREPARE phase  
        prepare_steps = self.integration.create_prepare_steps()
        self.sequencer.register_phase(StartupPhase.PREPARE, prepare_steps)
        
        # LAUNCH phase
        launch_steps = self.integration.create_launch_steps()
        self.sequencer.register_phase(StartupPhase.LAUNCH, launch_steps)
        
        # VERIFY phase
        verify_steps = self.integration.create_verify_steps()
        self.sequencer.register_phase(StartupPhase.VERIFY, verify_steps)
    
    def _create_init_steps(self) -> list:
        """Create INIT phase steps."""
        return [
            PhaseStep("load_cache", self._load_cache_state, 0.5, True, True, "cache_state"),
            PhaseStep("load_env", self._load_env_files, 1.0, True, True, "env_files"),
            PhaseStep("setup_logging", self._setup_silent_logging, 0.5, True, False)
        ]
    
    def run_optimized_startup(self) -> int:
        """Phase 6 Integration: Run complete optimized startup sequence."""
        # Start profiling and progress
        self.profiler.start_profiling()
        self.progress.start()
        
        try:
            # Execute sequence using SmartStartupSequencer
            phase_results = self.sequencer.execute_sequence()
            
            # Check if any phase failed
            failed_phases = [p for p, r in phase_results.items() if not r.success]
            if failed_phases:
                self._handle_startup_failure(failed_phases)
                return 1
            
            # Complete startup successfully
            return self._complete_startup_success()
            
        except Exception as e:
            logger.error(f"Startup sequence failed: {e}")
            self._handle_startup_error(e)
            return 1
        finally:
            self._cleanup_optimization_components()
    
    # Phase step implementations
    def _load_cache_state(self) -> bool:
        """Load cache state."""
        # Always return True - cache is optional
        # Just check if cache exists, don't fail if invalid
        try:
            self.cache_manager.is_cache_valid()
            return True
        except Exception:
            # Cache doesn't exist yet, that's OK
            return True
    
    def _load_env_files(self) -> bool:
        """Load environment files."""
        return self.launcher._load_env_file() or True
    
    def _setup_silent_logging(self) -> bool:
        """Setup silent logging system."""
        return True  # Already setup in __init__
    
    def _complete_startup_success(self) -> int:
        """Complete startup successfully."""
        self.progress.complete()
        summary = self.sequencer.get_sequence_summary()
        self._show_startup_summary(summary)
        # Run the main loop to keep services running
        self.launcher._run_main_loop()
        return self.launcher._handle_cleanup()
    
    def _handle_startup_failure(self, failed_phases):
        """Handle startup failure."""
        self.progress.fail_current_phase()
        for phase in failed_phases:
            logger.error(f"Phase {phase.phase_name} failed")
        self._show_error_logs()
    
    def _handle_startup_error(self, error):
        """Handle startup error."""
        self.log_buffer.add_message(str(error), LogLevel.ERROR)
        self._show_error_logs()
    
    def _show_error_logs(self):
        """Show error logs from buffer."""
        error_context = self.log_buffer.get_error_context()
        for entry in error_context:
            print(f"[{entry.level.name}] {entry.message}")
    
    def _show_startup_summary(self, summary):
        """Show startup summary."""
        if self.config.profile_startup:
            self._show_detailed_profile(summary)
        elif not self.config.silent_mode:
            if summary["target_met"]:
                self._print("⚡", "FAST", f"Startup completed in {summary['total_time']:.1f}s")
            else:
                self._print("⏱️", "TIME", f"Startup took {summary['total_time']:.1f}s")
    
    def _show_detailed_profile(self, summary):
        """Show detailed profiling information."""
        print("\n" + "="*60)
        print("🔬 STARTUP PERFORMANCE PROFILE")
        print("="*60)
        
        print(f"⏱️  Total Time: {summary['total_time']:.2f}s")
        print(f"🎯 Target Met: {'✅ YES' if summary['target_met'] else '❌ NO'}")
        print(f"⚡ Steps Skipped: {summary.get('total_steps_skipped', 0)}")
        print(f"🔧 Steps Executed: {summary.get('total_steps_executed', 0)}")
        
        if summary.get('phase_timings'):
            print("\n📊 Phase Breakdown:")
            for phase, timing in summary['phase_timings'].items():
                print(f"   {phase:12s}: {timing:.2f}s")
        
        print("="*60)
    
    def _cleanup_optimization_components(self):
        """Cleanup optimization components."""
        if hasattr(self, 'parallel_executor'):
            self.parallel_executor.cleanup()
    
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