"""
Startup Fixes Validator - Comprehensive validation for startup fixes
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.services.startup_fixes_integration import startup_fixes, FixStatus

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation levels for startup fixes."""
    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"
    CRITICAL_ONLY = "critical_only"


@dataclass
class ValidationResult:
    """Result of startup fixes validation."""
    success: bool
    total_fixes: int
    successful_fixes: int
    failed_fixes: int
    skipped_fixes: int
    critical_failures: List[str]
    warnings: List[str]
    details: Dict[str, Any]
    duration: float


class StartupFixesValidator:
    """Validates that all startup fixes are properly applied."""
    
    def __init__(self):
        self.critical_fixes = {
            "environment_fixes",
            "background_task_timeout", 
            "redis_fallback"
        }
        self.optional_fixes = {
            "port_conflict_resolution",
            "database_transaction"
        }
    
    async def validate_all_fixes_applied(
        self, 
        level: ValidationLevel = ValidationLevel.COMPREHENSIVE,
        timeout: float = 30.0
    ) -> ValidationResult:
        """
        Validate that all startup fixes are properly applied.
        
        Args:
            level: Level of validation to perform
            timeout: Maximum time to wait for validation
            
        Returns:
            ValidationResult with detailed status
        """
        start_time = time.time()
        
        try:
            # Run the comprehensive verification
            logger.info(f"Starting startup fixes validation (level: {level.value})")
            
            verification_result = await asyncio.wait_for(
                startup_fixes.run_comprehensive_verification(),
                timeout=timeout
            )
            
            # Analyze the results
            analysis = self._analyze_verification_results(verification_result, level)
            
            duration = time.time() - start_time
            
            result = ValidationResult(
                success=analysis["success"],
                total_fixes=verification_result.get("total_fixes", 0),
                successful_fixes=len(verification_result.get("successful_fixes", [])),
                failed_fixes=len(verification_result.get("failed_fixes", [])),
                skipped_fixes=len(verification_result.get("skipped_fixes", [])),
                critical_failures=analysis["critical_failures"],
                warnings=analysis["warnings"],
                details=verification_result,
                duration=duration
            )
            
            # Log validation summary
            self._log_validation_summary(result)
            
            return result
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"Startup fixes validation timed out after {timeout}s")
            
            return ValidationResult(
                success=False,
                total_fixes=0,
                successful_fixes=0,
                failed_fixes=5,  # Assume all failed if we timeout
                skipped_fixes=0,
                critical_failures=["validation_timeout"],
                warnings=[f"Validation timed out after {timeout}s"],
                details={"error": "Validation timeout"},
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Startup fixes validation failed with exception: {e}", exc_info=True)
            
            return ValidationResult(
                success=False,
                total_fixes=0,
                successful_fixes=0,
                failed_fixes=5,
                skipped_fixes=0,
                critical_failures=["validation_exception"],
                warnings=[f"Validation failed with exception: {e}"],
                details={"error": str(e)},
                duration=duration
            )
    
    def _analyze_verification_results(
        self, 
        verification_result: Dict[str, Any], 
        level: ValidationLevel
    ) -> Dict[str, Any]:
        """Analyze verification results and determine success/failure."""
        successful_fixes = set(verification_result.get("successful_fixes", []))
        failed_fixes = set(verification_result.get("failed_fixes", []))
        skipped_fixes = set(verification_result.get("skipped_fixes", []))
        
        critical_failures = []
        warnings = []
        
        # Check critical fixes
        for critical_fix in self.critical_fixes:
            if critical_fix in failed_fixes:
                critical_failures.append(f"Critical fix '{critical_fix}' failed")
            elif critical_fix in skipped_fixes:
                if level == ValidationLevel.CRITICAL_ONLY:
                    critical_failures.append(f"Critical fix '{critical_fix}' was skipped")
                else:
                    warnings.append(f"Critical fix '{critical_fix}' was skipped")
            elif critical_fix not in successful_fixes:
                warnings.append(f"Critical fix '{critical_fix}' status unknown")
        
        # Check optional fixes (warnings only)
        if level == ValidationLevel.COMPREHENSIVE:
            for optional_fix in self.optional_fixes:
                if optional_fix in failed_fixes:
                    warnings.append(f"Optional fix '{optional_fix}' failed")
                elif optional_fix in skipped_fixes:
                    warnings.append(f"Optional fix '{optional_fix}' was skipped")
        
        # Determine overall success
        success = (
            len(critical_failures) == 0 and
            (level != ValidationLevel.COMPREHENSIVE or len(failed_fixes) == 0)
        )
        
        return {
            "success": success,
            "critical_failures": critical_failures,
            "warnings": warnings
        }
    
    def _log_validation_summary(self, result: ValidationResult) -> None:
        """Log detailed validation summary."""
        status = " PASS:  PASSED" if result.success else " FAIL:  FAILED"
        logger.info(f"Startup Fixes Validation {status}")
        logger.info(f"  Duration: {result.duration:.2f}s")
        logger.info(f"  Total Fixes: {result.total_fixes}/5")
        logger.info(f"  Successful: {result.successful_fixes}")
        logger.info(f"  Failed: {result.failed_fixes}")
        logger.info(f"  Skipped: {result.skipped_fixes}")
        
        if result.critical_failures:
            logger.error("Critical Failures:")
            for failure in result.critical_failures:
                logger.error(f"  - {failure}")
        
        if result.warnings:
            logger.warning("Warnings:")
            for warning in result.warnings:
                logger.warning(f"  - {warning}")
    
    async def wait_for_fixes_completion(
        self, 
        max_wait_time: float = 60.0,
        check_interval: float = 2.0,
        min_required_fixes: int = 5
    ) -> ValidationResult:
        """
        Wait for startup fixes to complete with periodic checking.
        
        Args:
            max_wait_time: Maximum time to wait for completion
            check_interval: How often to check for completion
            min_required_fixes: Minimum number of fixes that must succeed
            
        Returns:
            ValidationResult when fixes complete or timeout
        """
        start_time = time.time()
        last_result = None
        
        logger.info(f"Waiting for startup fixes completion (max {max_wait_time}s)")
        
        while time.time() - start_time < max_wait_time:
            try:
                result = await self.validate_all_fixes_applied(
                    level=ValidationLevel.BASIC,
                    timeout=5.0  # Short timeout for periodic checks
                )
                
                last_result = result
                
                # Check if we have enough successful fixes
                if result.successful_fixes >= min_required_fixes:
                    logger.info(f"Startup fixes completion successful ({result.successful_fixes}/{min_required_fixes}+ fixes)")
                    return result
                
                # Log progress
                logger.debug(f"Startup fixes progress: {result.successful_fixes}/5 successful")
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.warning(f"Error checking startup fixes completion: {e}")
                await asyncio.sleep(check_interval)
        
        # Timeout reached
        logger.warning(f"Startup fixes completion timed out after {max_wait_time}s")
        
        if last_result:
            last_result.warnings.append(f"Completion check timed out after {max_wait_time}s")
            return last_result
        
        return ValidationResult(
            success=False,
            total_fixes=0,
            successful_fixes=0,
            failed_fixes=5,
            skipped_fixes=0,
            critical_failures=["completion_timeout"],
            warnings=[f"Completion check timed out after {max_wait_time}s"],
            details={"error": "Completion timeout"},
            duration=time.time() - start_time
        )
    
    async def diagnose_failing_fixes(self) -> Dict[str, Any]:
        """
        Diagnose which fixes are failing and why.
        
        Returns:
            Dictionary with diagnostic information
        """
        logger.info("Diagnosing failing startup fixes...")
        
        try:
            # Get the latest verification results
            verification_result = await startup_fixes.run_comprehensive_verification()
            
            diagnosis = {
                "timestamp": time.time(),
                "fix_diagnoses": {},
                "common_issues": [],
                "recommended_actions": []
            }
            
            # Analyze each fix
            fix_details = verification_result.get("fix_details", {})
            
            for fix_name, details in fix_details.items():
                status = details.get("status")
                error = details.get("error")
                dependencies_met = details.get("dependencies_met", True)
                
                fix_diagnosis = {
                    "status": status,
                    "error": error,
                    "dependencies_met": dependencies_met,
                    "likely_causes": [],
                    "recommended_fixes": []
                }
                
                # Determine likely causes and fixes
                if status in ["failed", "error"]:
                    if not dependencies_met:
                        fix_diagnosis["likely_causes"].append("Missing dependencies")
                        fix_diagnosis["recommended_fixes"].append("Check if required services are available")
                    
                    if error and "import" in error.lower():
                        fix_diagnosis["likely_causes"].append("Module import failure")
                        fix_diagnosis["recommended_fixes"].append("Verify module installation and paths")
                    
                    if error and "timeout" in error.lower():
                        fix_diagnosis["likely_causes"].append("Operation timeout")
                        fix_diagnosis["recommended_fixes"].append("Check service responsiveness")
                
                elif status == "skipped":
                    fix_diagnosis["likely_causes"].append("Dependencies not available")
                    fix_diagnosis["recommended_fixes"].append("Enable or install required dependencies")
                
                diagnosis["fix_diagnoses"][fix_name] = fix_diagnosis
            
            # Identify common issues
            failed_count = len(verification_result.get("failed_fixes", []))
            if failed_count >= 3:
                diagnosis["common_issues"].append("Multiple fixes failing - possible system-wide issue")
                diagnosis["recommended_actions"].append("Check system health and service availability")
            
            skipped_count = len(verification_result.get("skipped_fixes", []))
            if skipped_count >= 2:
                diagnosis["common_issues"].append("Multiple fixes skipped - missing dependencies")
                diagnosis["recommended_actions"].append("Review dependency installation and configuration")
            
            return diagnosis
            
        except Exception as e:
            logger.error(f"Error diagnosing startup fixes: {e}", exc_info=True)
            return {
                "timestamp": time.time(),
                "error": str(e),
                "recommended_actions": ["Check logs for detailed error information"]
            }


# Global validator instance
startup_fixes_validator = StartupFixesValidator()


# Convenience functions
async def validate_startup_fixes(
    level: ValidationLevel = ValidationLevel.COMPREHENSIVE
) -> ValidationResult:
    """Validate all startup fixes are applied."""
    return await startup_fixes_validator.validate_all_fixes_applied(level)


async def wait_for_startup_fixes_completion(max_wait_time: float = 60.0) -> ValidationResult:
    """Wait for startup fixes to complete."""
    return await startup_fixes_validator.wait_for_fixes_completion(max_wait_time)


async def diagnose_startup_fixes() -> Dict[str, Any]:
    """Diagnose failing startup fixes."""
    return await startup_fixes_validator.diagnose_failing_fixes()