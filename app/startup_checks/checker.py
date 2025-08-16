"""
Startup Checker

Main orchestrator for startup checks with modular delegation.
Maintains 8-line function limit and coordinating responsibility.
"""

import os
import time
from typing import Dict, Any, List
from fastapi import FastAPI
from app.logging_config import central_logger as logger
from .models import StartupCheckResult
from .environment_checks import EnvironmentChecker
from .database_checks import DatabaseChecker
from .service_checks import ServiceChecker
from .system_checks import SystemChecker


class StartupChecker:
    """Comprehensive startup check orchestrator"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.results: List[StartupCheckResult] = []
        self.start_time = time.time()
        self.is_staging = self._is_staging_environment()
        
        self.env_checker = EnvironmentChecker()
        self.db_checker = DatabaseChecker(app)
        self.service_checker = ServiceChecker(app)
        self.system_checker = SystemChecker()
        
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all startup checks and return results"""
        checks = [
            self.env_checker.check_environment_variables,
            self.env_checker.check_configuration,
            self.system_checker.check_file_permissions,
            self.db_checker.check_database_connection,
            self.service_checker.check_redis,
            self.service_checker.check_clickhouse,
            self.service_checker.check_llm_providers,
            self.system_checker.check_memory_and_resources,
            self.system_checker.check_network_connectivity,
            self.db_checker.check_or_create_assistant,
        ]
        
        for check in checks:
            await self._execute_check(check)
        
        return self._create_final_report()
    
    async def _execute_check(self, check_func) -> None:
        """Execute individual check with timing"""
        try:
            start = time.time()
            result = await check_func()
            self._record_check_success(result, start)
        except Exception as e:
            self._record_check_failure(check_func, e)
    
    def _create_final_report(self) -> Dict[str, Any]:
        """Create final report from all check results"""
        total_duration = (time.time() - self.start_time) * 1000
        failed_critical, failed_non_critical = self._categorize_failures()
        passed_count = len([r for r in self.results if r.success])
        return self._build_report_dict(total_duration, failed_critical, failed_non_critical, passed_count)
    
    def _is_staging_environment(self) -> bool:
        """Check if running in staging environment"""
        environment = os.getenv("ENVIRONMENT", "development").lower()
        return environment == "staging" or bool(os.getenv("K_SERVICE"))
    
    def _record_check_success(self, result: StartupCheckResult, start_time: float) -> None:
        """Record successful check result with timing"""
        duration = (time.time() - start_time) * 1000
        result.duration_ms = duration
        self.results.append(result)
    
    def _record_check_failure(self, check_func, error: Exception) -> None:
        """Record failed check result"""
        logger.error(f"Check {check_func.__name__} failed unexpectedly: {error}")
        self.results.append(StartupCheckResult(
            name=check_func.__name__, success=False,
            message=f"Unexpected error: {error}", critical=not self.is_staging
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
