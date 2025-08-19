"""
Launcher integration module - Phase 6 Final Integration.

Wires up all optimization components and provides step creation methods
for the SmartStartupSequencer. Maintains 300-line limit by separating
integration logic from main orchestrator.
"""

import time
import logging
from typing import List, Dict, Any, Set
from pathlib import Path

from dev_launcher.startup_sequencer import PhaseStep
from dev_launcher.parallel_executor import ParallelExecutor, ParallelTask, TaskType
from dev_launcher.log_buffer import LogBuffer, LogLevel
from dev_launcher.local_secrets import LocalSecretManager
from dev_launcher.quick_health import QuickHealthChecker
from dev_launcher.dependency_checker import AsyncDependencyChecker

logger = logging.getLogger(__name__)


class LauncherIntegration:
    """
    Integration module for all dev launcher optimization components.
    
    Provides step implementations, parallel task creation, and component
    wiring for the optimized startup sequence.
    """
    
    def __init__(self, orchestrator):
        """Initialize with reference to orchestrator."""
        self.orchestrator = orchestrator
        self.launcher = orchestrator.launcher
        self.config = orchestrator.config
        self.cache_manager = orchestrator.cache_manager
        self.parallel_executor = orchestrator.parallel_executor
        self.log_buffer = orchestrator.log_buffer
        self.local_secrets = orchestrator.local_secrets
        self._setup_additional_components()
    
    def _setup_additional_components(self):
        """Setup additional integration components."""
        self.health_checker = QuickHealthChecker()
        self.dep_checker = AsyncDependencyChecker(
            self.config.project_root,
            self.cache_manager.cache_dir
        )
    
    def create_validate_steps(self) -> List[PhaseStep]:
        """Create VALIDATE phase steps with parallel execution."""
        return [
            PhaseStep(
                "hash_check", 
                self._parallel_hash_check, 
                1.0, True, True, "file_hashes"
            ),
            PhaseStep(
                "env_validate", 
                self._validate_environment, 
                1.5, True, True, "env_validation"
            ),
            PhaseStep(
                "port_check", 
                self._check_ports_parallel, 
                0.5, True, True, "port_availability"
            )
        ]
    
    def create_prepare_steps(self) -> List[PhaseStep]:
        """Create PREPARE phase steps with parallel dependency installation."""
        return [
            PhaseStep(
                "install_deps", 
                self._install_dependencies_parallel, 
                3.0, False, True, "dependencies"
            ),
            PhaseStep(
                "run_migrations", 
                self._run_migrations_if_needed, 
                1.5, False, True, "migrations"
            ),
            PhaseStep(
                "warm_cache", 
                self._warm_caches, 
                0.5, False, True, "cache_warming"
            )
        ]
    
    def create_launch_steps(self) -> List[PhaseStep]:
        """Create LAUNCH phase steps with parallel service startup."""
        return [
            PhaseStep(
                "start_services_parallel", 
                self._start_all_services_parallel, 
                4.0, True, False
            ),
            PhaseStep(
                "verify_readiness", 
                self._verify_services_ready, 
                1.0, True, False
            )
        ]
    
    def create_verify_steps(self) -> List[PhaseStep]:
        """Create VERIFY phase steps with quick health checks."""
        return [
            PhaseStep(
                "quick_health", 
                self._quick_health_check, 
                1.0, True, False
            ),
            PhaseStep(
                "update_cache", 
                self._update_success_cache, 
                0.5, False, False
            ),
            PhaseStep(
                "show_summary", 
                self._show_final_summary, 
                1.5, False, False
            )
        ]
    
    def _parallel_hash_check(self) -> bool:
        """Parallel file hash checking."""
        if not self.config.no_cache and self.cache_manager.is_cached_and_valid("file_hashes"):
            self._log_step("Hash check", "Using cached hashes")
            return True
            
        tasks = self._create_hash_check_tasks()
        results = self.parallel_executor.execute_all(timeout=2.0)
        
        success = all(r.success for r in results.values())
        if success and not self.config.no_cache:
            self.cache_manager.cache_result("file_hashes", True)
            self._log_step("Hash check", "Completed parallel hash verification")
        return success
    
    def _create_hash_check_tasks(self) -> List[ParallelTask]:
        """Create parallel hash check tasks."""
        tasks = []
        
        # Backend files
        tasks.append(ParallelTask(
            task_id="backend_hash",
            func=self.cache_manager.has_dependencies_changed,
            args=("backend",),
            task_type=TaskType.IO_BOUND
        ))
        
        # Frontend files
        tasks.append(ParallelTask(
            task_id="frontend_hash", 
            func=self.cache_manager.has_dependencies_changed,
            args=("frontend",),
            task_type=TaskType.IO_BOUND
        ))
        
        # Auth files
        tasks.append(ParallelTask(
            task_id="auth_hash",
            func=self.cache_manager.has_dependencies_changed,
            args=("auth",),
            task_type=TaskType.IO_BOUND
        ))
        
        for task in tasks:
            self.parallel_executor.add_task(task)
            
        return tasks
    
    def _validate_environment(self) -> bool:
        """Validate environment with local secrets."""
        if not self.config.load_secrets:
            self._log_step("Secrets", "Skipped (--no-secrets flag)")
            return True
            
        # Use local secrets by default
        required_keys = self._get_required_secret_keys()
        secrets, validation = self.local_secrets.load_secrets_with_fallback(required_keys)
        
        success = validation.is_valid
        if success:
            self._log_step("Local secrets", f"Loaded {len(secrets)} secrets")
        else:
            self._log_step("Local secrets", f"Missing {len(validation.missing)} keys", LogLevel.WARNING)
            
        return True  # Non-blocking for development
    
    def _get_required_secret_keys(self) -> Set[str]:
        """Get required secret keys."""
        return {
            'GEMINI_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS',
            'LANGFUSE_SECRET_KEY', 'JWT_SECRET', 'FERNET_KEY'
        }
    
    def _check_ports_parallel(self) -> bool:
        """Check port availability in parallel."""
        if not self.config.no_cache and self.cache_manager.is_cached_and_valid("port_availability"):
            return True
            
        ports = [
            ("auth", 8081),
            ("backend", self.config.backend_port or 8000),
            ("frontend", self.config.frontend_port or 3000)
        ]
        
        # Create parallel port check tasks
        for name, port in ports:
            task = ParallelTask(
                task_id=f"port_{name}",
                func=self._is_port_available,
                args=(port,),
                task_type=TaskType.NETWORK_BOUND
            )
            self.parallel_executor.add_task(task)
        
        results = self.parallel_executor.execute_all(timeout=1.0)
        success = all(r.success for r in results.values())
        
        if success and not self.config.no_cache:
            self.cache_manager.cache_result("port_availability", True)
            self._log_step("Port check", "All ports available")
        
        return success
    
    def _is_port_available(self, port: int) -> bool:
        """Check if port is available."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return True
        except OSError:
            return False
    
    def _install_dependencies_parallel(self) -> bool:
        """Install dependencies in parallel."""
        return self.dep_checker.check_and_install_all_parallel()
    
    def _run_migrations_if_needed(self) -> bool:
        """Run migrations if needed."""
        # Check if migrations should be skipped
        if not self.config.no_cache and not self.cache_manager.has_migration_files_changed():
            self._log_step("Migrations", "No changes detected, using cache")
            return True
        
        # Run migrations through the launcher's migration runner
        self._log_step("Migrations", "Checking database schema...")
        success = self.launcher.run_migrations()
        
        if success:
            self._log_step("Migrations", "Database ready")
            # Update cache to avoid re-running on next startup
            if not self.config.no_cache:
                self.cache_manager.cache_result("migrations", True)
        else:
            self._log_step("Migrations", "Migration issues detected", LogLevel.WARNING)
        
        return success
    
    def _warm_caches(self) -> bool:
        """Warm caches for next startup."""
        if not self.config.no_cache:
            # Cache current successful state
            self.cache_manager.mark_successful_startup(time.time())
        return True
    
    def _start_all_services_parallel(self) -> bool:
        """Start all services in parallel."""
        # Create service startup tasks
        tasks = [
            ParallelTask("start_auth", self._start_auth_service, task_type=TaskType.IO_BOUND),
            ParallelTask("start_backend", self._start_backend_service, 
                        dependencies=["start_auth"], task_type=TaskType.IO_BOUND),
            ParallelTask("start_frontend", self._start_frontend_service,
                        dependencies=["start_backend"], task_type=TaskType.IO_BOUND)
        ]
        
        for task in tasks:
            self.parallel_executor.add_task(task)
            
        results = self.parallel_executor.execute_all(timeout=10.0)
        return all(r.success for r in results.values())
    
    def _start_auth_service(self) -> bool:
        """Start auth service."""
        try:
            process, _ = self.launcher.service_startup.start_auth_service()
            if process:
                self.launcher.process_manager.add_process("Auth", process)
                self._log_step("Auth", "Started successfully")
                return True
            return False
        except Exception as e:
            self._log_step("Auth", f"Failed: {e}", LogLevel.ERROR)
            return False
    
    def _start_backend_service(self) -> bool:
        """Start backend service."""
        try:
            process, _ = self.launcher.service_startup.start_backend()
            if process:
                self.launcher.process_manager.add_process("Backend", process)
                self._log_step("Backend", "Started successfully")
                return True
            return False
        except Exception as e:
            self._log_step("Backend", f"Failed: {e}", LogLevel.ERROR)
            return False
    
    def _start_frontend_service(self) -> bool:
        """Start frontend service."""
        try:
            process, _ = self.launcher.service_startup.start_frontend()
            if process:
                self.launcher.process_manager.add_process("Frontend", process)
                self._log_step("Frontend", "Started successfully")
                return True
            return False
        except Exception as e:
            self._log_step("Frontend", f"Failed: {e}", LogLevel.ERROR)
            return False
    
    def _verify_services_ready(self) -> bool:
        """Verify all services are ready."""
        return self.launcher.startup_validator.verify_all_services_ready()
    
    def _quick_health_check(self) -> bool:
        """Quick health check of all services."""
        return self.health_checker.run_quick_checks()
    
    def _update_success_cache(self) -> bool:
        """Update cache with successful startup."""
        self.cache_manager.mark_successful_startup(time.time())
        return True
    
    def _show_final_summary(self) -> bool:
        """Show final startup summary and start health monitoring."""
        # Start health monitoring AFTER services are verified ready (per HEALTH-001)
        self.launcher.register_health_monitoring()
        self.launcher.health_monitor.start()
        
        # Show success summary
        self.launcher.summary_display.show_success_summary()
        return True
    
    def _log_step(self, step_name: str, message: str, level: LogLevel = LogLevel.INFO):
        """Log step with buffering."""
        full_message = f"[{step_name}] {message}"
        self.log_buffer.add_message(full_message, level)
        
        # Show immediately only for silent mode failures or important messages
        if level.value >= LogLevel.ERROR.value or not getattr(self.config, 'silent_mode', False):
            logger.info(full_message)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from all components."""
        return {
            "parallel_executor": self.parallel_executor.get_performance_stats(),
            "cache_stats": self.cache_manager.get_cache_stats(),
            "log_buffer_size": len(self.log_buffer.buffer)
        }