"""
Startup Checker

Main orchestrator for startup checks with modular delegation.
Maintains 25-line function limit and coordinating responsibility.
"""

import time
from typing import Dict, Any, List
from fastapi import FastAPI
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.services.apex_optimizer_agent.models import StartupCheckResult
from netra_backend.app.environment_checks import EnvironmentChecker
from netra_backend.app.database_checks import DatabaseChecker
from netra_backend.app.service_checks import ServiceChecker
from netra_backend.app.system_checks import SystemChecker
from netra_backend.app.core.configuration import unified_config_manager


class StartupChecker:
    """Comprehensive startup check orchestrator"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self._initialize_state()
        self._initialize_checkers(app)
    
    def _initialize_state(self) -> None:
        """Initialize checker state"""
        self.results: List[StartupCheckResult] = []
        self.start_time = time.time()
        self.is_staging = self._is_staging_environment()
    
    def _initialize_checkers(self, app: FastAPI) -> None:
        """Initialize all checker instances"""
        logger.debug("Initializing startup checkers...")
        try:
            logger.debug("Creating EnvironmentChecker...")
            self.env_checker = EnvironmentChecker()
            logger.debug("Creating DatabaseChecker...")
            self.db_checker = DatabaseChecker(app)
            logger.debug("Creating ServiceChecker...")
            self.service_checker = ServiceChecker(app)
            logger.debug("Creating SystemChecker...")
            self.system_checker = SystemChecker()
            logger.debug("All checkers initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize startup checkers: {e}")
            raise
        
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all startup checks and return results"""
        checks = self._get_check_functions()
        logger.info(f"Preparing to run {len(checks)} startup checks:")
        for i, check in enumerate(checks, 1):
            logger.info(f"  {i}. {check.__name__}")
        await self._execute_all_checks(checks)
        return self._create_final_report()
    
    def _get_check_functions(self) -> list:
        """Get list of all check functions to execute"""
        core_checks = self._get_core_check_functions()
        service_checks = self._get_service_check_functions()
        return core_checks + service_checks
    
    def _get_core_check_functions(self) -> list:
        """Get core environment and system check functions"""
        return [
            self.env_checker.check_environment_variables,
            self.env_checker.check_configuration,
            self.system_checker.check_file_permissions,
            self.db_checker.check_database_connection,
        ]
    
    def _get_service_check_functions(self) -> list:
        """Get service and resource check functions"""
        service_checks = self._get_external_service_checks()
        system_checks = self._get_system_resource_checks()
        return service_checks + system_checks
    
    def _get_external_service_checks(self) -> list:
        """Get external service check functions"""
        return [
            self.service_checker.check_redis,
            self.service_checker.check_clickhouse,
            self.service_checker.check_llm_providers,
        ]
    
    def _get_system_resource_checks(self) -> list:
        """Get system resource check functions"""
        return [
            self.system_checker.check_memory_and_resources,
            self.system_checker.check_network_connectivity,
            self.db_checker.check_or_create_assistant,
        ]
    
    async def _execute_all_checks(self, checks: list) -> None:
        """Execute all check functions"""
        for check in checks:
            await self._execute_check(check)
    
    async def _execute_check(self, check_func) -> None:
        """Execute individual check with timing"""
        check_name = check_func.__name__
        logger.info(f"Running startup check: {check_name}")
        try:
            start = time.time()
            logger.debug(f"Executing {check_name}...")
            result = await check_func()
            logger.debug(f"Check {check_name} completed successfully: {result.message if result else 'No message'}")
            self._record_check_success(result, start)
            
            # In staging, fail immediately on any check failure
            if self.is_staging and not result.success:
                error_msg = f"Staging startup check failed: {check_name} - {result.message}"
                logger.critical(error_msg)
                raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"Check {check_name} failed with exception: {e}")
            
            # In staging, raise the error immediately for observability
            if self.is_staging:
                error_msg = f"Staging startup check crashed: {check_name} - {str(e)}"
                logger.critical(error_msg)
                raise RuntimeError(error_msg) from e
            
            self._record_check_failure(check_func, e)
    
    def _create_final_report(self) -> Dict[str, Any]:
        """Create final report from all check results"""
        total_duration = (time.time() - self.start_time) * 1000
        failed_critical, failed_non_critical = self._categorize_failures()
        passed_count = len([r for r in self.results if r.success])
        
        # Log detailed summary
        logger.info("=== STARTUP CHECKS SUMMARY ===")
        logger.info(f"Total checks: {len(self.results)}")
        logger.info(f"Passed: {passed_count}")
        logger.info(f"Failed (critical): {len(failed_critical)}")
        logger.info(f"Failed (non-critical): {len(failed_non_critical)}")
        logger.info(f"Total duration: {total_duration:.2f}ms")
        
        # Log individual check results
        for result in self.results:
            status = "PASS" if result.success else ("FAIL-CRITICAL" if result.critical else "FAIL-WARN")
            duration = f"{result.duration_ms:.2f}ms" if hasattr(result, 'duration_ms') and result.duration_ms else "N/A"
            logger.info(f"  {status}: {result.name} ({duration}) - {result.message}")
        
        return self._build_report_dict(total_duration, failed_critical, failed_non_critical, passed_count)
    
    def _is_staging_environment(self) -> bool:
        """Check if running in staging environment"""
        config = unified_config_manager.get_config()
        return config.environment.lower() == "staging" or (hasattr(config, 'k_service') and config.k_service)
    
    def _record_check_success(self, result: StartupCheckResult, start_time: float) -> None:
        """Record successful check result with timing"""
        duration = (time.time() - start_time) * 1000
        result.duration_ms = duration
        self.results.append(result)
    
    def _record_check_failure(self, check_func, error: Exception) -> None:
        """Record failed check result"""
        logger.error(f"Check {check_func.__name__} failed unexpectedly: {error}")
        
        # In staging, ALL failures are critical
        is_critical = self.is_staging
        
        # In non-staging, special handling for assistant check - make it non-critical
        if not self.is_staging and check_func.__name__ == "check_or_create_assistant":
            is_critical = False
            logger.info("Treating assistant check failure as non-critical")
        
        self.results.append(StartupCheckResult(
            name=check_func.__name__, success=False,
            message=f"Unexpected error: {error}", critical=is_critical
        ))
    
    def _categorize_failures(self) -> tuple:
        """Categorize failures into critical and non-critical"""
        failed_critical = [r for r in self.results if not r.success and r.critical]
        failed_non_critical = [r for r in self.results if not r.success and not r.critical]
        return failed_critical, failed_non_critical
    
    def _build_report_dict(self, total_duration: float, failed_critical: list, failed_non_critical: list, passed_count: int) -> Dict[str, Any]:
        """Build final report dictionary"""
        return {
            "success": len(failed_critical) == 0, "total_checks": len(self.results),
            "passed": passed_count, "failed_critical": len(failed_critical),
            "failed_non_critical": len(failed_non_critical), "duration_ms": total_duration,
            "results": self.results, "failures": failed_critical + failed_non_critical
        }
