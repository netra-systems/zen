"""
Startup Phase Validation System

Addresses WHY #5 from Five Whys Analysis:
- Implements contract-driven development during system startup
- Provides phase-by-phase validation of component initialization
- Enforces dependency order and contract compliance
- Prevents runtime failures through early validation

This system integrates with smd.py to validate contracts at each startup phase:
1. INITIALIZATION - Basic component creation
2. CONFIGURATION - Component setup and wiring  
3. INTEGRATION - Cross-component dependencies
4. READINESS - Full system operational validation

CRITICAL: This prevents the exact architectural integration failures identified
in the WebSocket bridge Five Whys analysis.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time

from netra_backend.app.core.app_state_contracts import (
    AppStateContractValidator,
    ContractPhase,
    AppStateContractViolation,
    enforce_app_state_contracts
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class StartupValidationError(Exception):
    """Raised when startup phase validation fails"""
    pass


class PhaseTransitionError(Exception):
    """Raised when attempting invalid phase transition"""
    pass


@dataclass
class PhaseValidationResult:
    """Result of phase validation"""
    phase: ContractPhase
    success: bool
    duration_seconds: float
    components_validated: int
    errors: List[str]
    warnings: List[str]
    business_impact: List[str]


class StartupPhaseValidator:
    """
    Validates system startup phases and enforces contract compliance
    
    This class orchestrates the validation of each startup phase to ensure
    all components are properly initialized before dependent components.
    """
    
    def __init__(self):
        self.contract_validator = AppStateContractValidator()
        self.current_phase = None
        self.completed_phases = []
        self.validation_history = []
        
    async def validate_phase(self, app_state: Any, 
                           target_phase: ContractPhase,
                           skip_enforcement: bool = False) -> PhaseValidationResult:
        """
        Validate specific startup phase with comprehensive service dependency logging
        
        Args:
            app_state: FastAPI app.state object
            target_phase: Phase to validate
            skip_enforcement: If True, log errors but don't raise exceptions
        
        Returns:
            Phase validation results
        """
        start_time = time.time()
        logger.info(f"🔍 STARTUP PHASE VALIDATION: Starting {target_phase.value} validation")
        
        # Log service dependencies for this phase
        await self._log_phase_service_dependencies(target_phase, app_state)
        
        try:
            # Validate contracts for this phase
            contract_results = self.contract_validator.validate_app_state_contracts(
                app_state, target_phase
            )
            
            # Create phase result
            duration = time.time() - start_time
            phase_result = PhaseValidationResult(
                phase=target_phase,
                success=contract_results["valid"],
                duration_seconds=duration,
                components_validated=contract_results["total_contracts"],
                errors=contract_results["critical_errors"],
                warnings=contract_results["warnings"],
                business_impact=[
                    impact["impact"] for impact in contract_results.get("business_impact", [])
                ]
            )
            
            # Store validation result
            self.validation_history.append(phase_result)
            
            if phase_result.success:
                logger.info(f"✅ STARTUP PHASE SUCCESS: {target_phase.value} validation passed "
                          f"({contract_results['passed_contracts']}/{contract_results['total_contracts']} "
                          f"contracts validated in {duration:.2f}s)")
                
                # Log successful service integrations
                await self._log_successful_service_integrations(target_phase, app_state)
                
                self.current_phase = target_phase
                if target_phase not in self.completed_phases:
                    self.completed_phases.append(target_phase)
                    
            else:
                logger.critical(f"🚨 STARTUP PHASE FAILURE: {target_phase.value} validation failed "
                               f"({len(phase_result.errors)} critical errors)")
                
                # Log detailed service integration failures
                await self._log_service_integration_failures(target_phase, phase_result.errors, app_state)
                
                for error in phase_result.errors:
                    logger.error(f"   - {error}")
                
                # Handle enforcement
                if not skip_enforcement:
                    error_message = (
                        f"Startup phase {target_phase.value} validation failed:\n" +
                        "\n".join([f"  - {error}" for error in phase_result.errors])
                    )
                    raise StartupValidationError(error_message)
            
            return phase_result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.critical(f"🚨 STARTUP PHASE EXCEPTION: {target_phase.value} validation exception "
                           f"(duration: {duration:.2f}s, exception: {type(e).__name__}: {e})")
            
            # Log service integration context for exception
            await self._log_exception_service_context(target_phase, e, app_state)
            
            # Create error result
            phase_result = PhaseValidationResult(
                phase=target_phase,
                success=False,
                duration_seconds=duration,
                components_validated=0,
                errors=[str(e)],
                warnings=[],
                business_impact=["Critical startup failure - system may not function properly"]
            )
            
            self.validation_history.append(phase_result)
            
            if not skip_enforcement:
                raise StartupValidationError(f"Phase {target_phase.value} validation failed: {e}")
            
            return phase_result
    
    async def _log_phase_service_dependencies(self, phase: ContractPhase, app_state: Any) -> None:
        """Log service dependencies for the current startup phase."""
        phase_services = self._get_phase_required_services(phase)
        available_services = self._get_available_services(app_state)
        missing_services = [svc for svc in phase_services if svc not in available_services]
        
        logger.info(
            f"🔍 PHASE SERVICE DEPENDENCIES: {phase.value} phase "
            f"(required_services: {phase_services}, "
            f"available_services: {list(available_services.keys())}, "
            f"missing_services: {missing_services})"
        )
        
        if missing_services:
            logger.warning(
                f"⚠️ MISSING SERVICES: {phase.value} phase missing required services "
                f"(missing: {missing_services}, "
                f"impact: Phase may fail or operate with reduced functionality)"
            )
    
    async def _log_successful_service_integrations(self, phase: ContractPhase, app_state: Any) -> None:
        """Log successful service integrations for the phase."""
        available_services = self._get_available_services(app_state)
        phase_services = self._get_phase_required_services(phase)
        working_services = [svc for svc in phase_services if svc in available_services]
        
        if working_services:
            logger.info(
                f"✅ SERVICE INTEGRATIONS: {phase.value} phase service integrations successful "
                f"(working_services: {working_services}, "
                f"golden_path_status: {'enabled' if 'websocket_manager' in working_services else 'limited'})"
            )
    
    async def _log_service_integration_failures(self, phase: ContractPhase, errors: List[str], app_state: Any) -> None:
        """Log detailed service integration failures."""
        available_services = self._get_available_services(app_state)
        phase_services = self._get_phase_required_services(phase)
        failed_services = [svc for svc in phase_services if svc not in available_services]
        
        # Analyze failure patterns
        failure_patterns = self._analyze_failure_patterns(errors, failed_services)
        golden_path_impact = self._assess_golden_path_impact_from_failures(failed_services)
        
        logger.critical(
            f"🚨 SERVICE INTEGRATION FAILURES: {phase.value} phase integration failures "
            f"(failed_services: {failed_services}, "
            f"failure_patterns: {failure_patterns}, "
            f"golden_path_impact: {golden_path_impact}, "
            f"total_errors: {len(errors)})"
        )
        
        # Log specific service failure context
        for service in failed_services:
            service_errors = [err for err in errors if service in err.lower()]
            logger.critical(
                f"🚨 SERVICE FAILURE DETAIL: {service} service failed "
                f"(related_errors: {len(service_errors)}, "
                f"phase: {phase.value}, "
                f"impact: Service unavailable for {phase.value} operations)"
            )
    
    async def _log_exception_service_context(self, phase: ContractPhase, exception: Exception, app_state: Any) -> None:
        """Log service context when an exception occurs during phase validation."""
        available_services = self._get_available_services(app_state)
        phase_services = self._get_phase_required_services(phase)
        
        logger.critical(
            f"🚨 SERVICE EXCEPTION CONTEXT: {phase.value} phase exception occurred "
            f"(exception_type: {type(exception).__name__}, "
            f"exception_message: {str(exception)}, "
            f"available_services: {list(available_services.keys())}, "
            f"required_services: {phase_services}, "
            f"service_status: {self._get_service_health_summary(available_services)})"
        )
    
    def _get_phase_required_services(self, phase: ContractPhase) -> List[str]:
        """Get list of services required for a specific startup phase."""
        phase_service_map = {
            ContractPhase.INITIALIZATION: ["database", "redis"],
            ContractPhase.CONFIGURATION: ["database", "redis", "auth_service"],
            ContractPhase.INTEGRATION: ["database", "redis", "auth_service", "websocket_manager"],
            ContractPhase.READINESS: ["database", "redis", "auth_service", "websocket_manager", "supervisor_service"]
        }
        return phase_service_map.get(phase, [])
    
    def _get_available_services(self, app_state: Any) -> Dict[str, Any]:
        """Get dictionary of available services from app state."""
        services = {}
        
        # Check for common service attributes in app state
        service_attributes = [
            "database_manager", "redis_client", "auth_service",
            "websocket_manager", "websocket_connection_pool", 
            "supervisor_service", "agent_registry"
        ]
        
        for attr in service_attributes:
            if hasattr(app_state, attr):
                service_value = getattr(app_state, attr)
                if service_value is not None:
                    services[attr] = service_value
        
        return services
    
    def _analyze_failure_patterns(self, errors: List[str], failed_services: List[str]) -> Dict[str, int]:
        """Analyze patterns in failure messages."""
        patterns = {
            "connection_errors": 0,
            "timeout_errors": 0,
            "auth_errors": 0,
            "config_errors": 0,
            "dependency_errors": 0
        }
        
        for error in errors:
            error_lower = error.lower()
            if any(term in error_lower for term in ["connection", "connect", "refused"]):
                patterns["connection_errors"] += 1
            if any(term in error_lower for term in ["timeout", "timed out"]):
                patterns["timeout_errors"] += 1
            if any(term in error_lower for term in ["auth", "token", "permission"]):
                patterns["auth_errors"] += 1
            if any(term in error_lower for term in ["config", "configuration", "setting"]):
                patterns["config_errors"] += 1
            if any(term in error_lower for term in ["dependency", "depends", "require"]):
                patterns["dependency_errors"] += 1
        
        return {k: v for k, v in patterns.items() if v > 0}
    
    def _assess_golden_path_impact_from_failures(self, failed_services: List[str]) -> str:
        """Assess Golden Path impact from failed services."""
        critical_for_golden_path = ["websocket_manager", "auth_service", "supervisor_service"]
        important_for_golden_path = ["database", "redis"]
        
        critical_failures = [svc for svc in failed_services if svc in critical_for_golden_path]
        important_failures = [svc for svc in failed_services if svc in important_for_golden_path]
        
        if critical_failures:
            return f"CRITICAL - Golden Path blocked by {critical_failures}"
        elif important_failures:
            return f"HIGH - Golden Path may be degraded by {important_failures}"
        elif failed_services:
            return f"MEDIUM - Some functionality may be limited"
        else:
            return "LOW - No critical impact expected"
    
    def _get_service_health_summary(self, available_services: Dict[str, Any]) -> str:
        """Get summary of service health status."""
        total_services = len(available_services)
        healthy_services = sum(1 for svc in available_services.values() if svc is not None)
        
        if total_services == 0:
            return "no_services_registered"
        elif healthy_services == total_services:
            return f"all_healthy ({healthy_services}/{total_services})"
        else:
            return f"partial_health ({healthy_services}/{total_services})"
    
    async def validate_startup_sequence(self, app_state: Any, 
                                      target_phase: ContractPhase = ContractPhase.READINESS,
                                      skip_enforcement: bool = False) -> Dict[str, Any]:
        """
        Validate complete startup sequence up to target phase
        
        This ensures all phases are validated in proper order.
        """
        logger.info(f"🚀 Starting startup sequence validation to {target_phase.value}")
        
        # Define phase order
        phase_order = [
            ContractPhase.INITIALIZATION,
            ContractPhase.CONFIGURATION,
            ContractPhase.INTEGRATION,
            ContractPhase.READINESS
        ]
        
        # Find target phase index
        try:
            target_index = phase_order.index(target_phase)
            phases_to_validate = phase_order[:target_index + 1]
        except ValueError:
            raise ValueError(f"Invalid target phase: {target_phase}")
        
        # Validate each phase in order
        sequence_results = {
            "success": True,
            "target_phase": target_phase.value,
            "phases_validated": [],
            "total_duration": 0.0,
            "total_components": 0,
            "total_errors": 0,
            "critical_failures": []
        }
        
        for phase in phases_to_validate:
            try:
                phase_result = await self.validate_phase(app_state, phase, skip_enforcement)
                
                # Add to sequence results
                sequence_results["phases_validated"].append({
                    "phase": phase.value,
                    "success": phase_result.success,
                    "duration": phase_result.duration_seconds,
                    "components": phase_result.components_validated,
                    "errors": len(phase_result.errors),
                    "warnings": len(phase_result.warnings)
                })
                
                sequence_results["total_duration"] += phase_result.duration_seconds
                sequence_results["total_components"] += phase_result.components_validated
                sequence_results["total_errors"] += len(phase_result.errors)
                
                if not phase_result.success:
                    sequence_results["success"] = False
                    sequence_results["critical_failures"].extend(phase_result.errors)
                
            except Exception as e:
                sequence_results["success"] = False
                sequence_results["critical_failures"].append(f"Phase {phase.value}: {e}")
                
                if not skip_enforcement:
                    raise
        
        # Generate summary
        if sequence_results["success"]:
            logger.info(f"🎉 Startup sequence validation complete: "
                       f"All phases passed ({sequence_results['total_duration']:.2f}s)")
        else:
            logger.error(f"💥 Startup sequence validation failed: "
                        f"{len(sequence_results['critical_failures'])} critical failures")
        
        return sequence_results
    
    def get_validation_report(self) -> str:
        """Generate comprehensive validation report"""
        
        if not self.validation_history:
            return "No validation history available"
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("STARTUP PHASE VALIDATION REPORT")
        report_lines.append("=" * 60)
        
        # Overall status
        total_validations = len(self.validation_history)
        successful_validations = sum(1 for result in self.validation_history if result.success)
        overall_success = successful_validations == total_validations
        
        status = "✅ PASSED" if overall_success else "❌ FAILED"
        report_lines.append(f"Overall Status: {status}")
        report_lines.append(f"Validations: {successful_validations}/{total_validations} successful")
        report_lines.append(f"Current Phase: {self.current_phase.value if self.current_phase else 'Not started'}")
        report_lines.append("")
        
        # Phase details
        report_lines.append("PHASE VALIDATION DETAILS:")
        report_lines.append("-" * 40)
        
        for result in self.validation_history:
            status_icon = "✅" if result.success else "❌"
            report_lines.append(f"{status_icon} {result.phase.value}")
            report_lines.append(f"   Duration: {result.duration_seconds:.2f}s")
            report_lines.append(f"   Components: {result.components_validated}")
            
            if result.errors:
                report_lines.append("   Errors:")
                for error in result.errors:
                    report_lines.append(f"     - {error}")
            
            if result.warnings:
                report_lines.append("   Warnings:")
                for warning in result.warnings:
                    report_lines.append(f"     - {warning}")
            
            if result.business_impact:
                report_lines.append("   Business Impact:")
                for impact in result.business_impact:
                    report_lines.append(f"     - {impact}")
            
            report_lines.append("")
        
        # Completed phases summary
        report_lines.append("COMPLETED PHASES:")
        report_lines.append("-" * 40)
        for phase in self.completed_phases:
            report_lines.append(f"✅ {phase.value}")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)


# Global validator instance for use in startup
_startup_validator = None


def get_startup_validator() -> StartupPhaseValidator:
    """Get global startup validator instance"""
    global _startup_validator
    if _startup_validator is None:
        _startup_validator = StartupPhaseValidator()
    return _startup_validator


async def validate_startup_phase(app_state: Any, 
                                phase: ContractPhase,
                                skip_enforcement: bool = False) -> PhaseValidationResult:
    """
    Convenient function for validating single startup phase
    
    This is the main integration point for smd.py
    """
    validator = get_startup_validator()
    return await validator.validate_phase(app_state, phase, skip_enforcement)


async def enforce_startup_phase_contracts(app_state: Any, 
                                        phase: ContractPhase) -> bool:
    """
    Enforce startup phase contracts - raises exception on failure
    
    This is the "fail fast" mechanism for startup validation.
    """
    logger.info(f"🛡️  Enforcing startup phase contracts: {phase.value}")
    
    try:
        result = await validate_startup_phase(app_state, phase, skip_enforcement=False)
        if result.success:
            logger.info(f"✅ Phase {phase.value} contracts enforced successfully")
            return True
        else:
            # This should not happen since skip_enforcement=False
            logger.error(f"❌ Phase {phase.value} contract enforcement failed unexpectedly")
            return False
            
    except Exception as e:
        logger.error(f"💥 Phase {phase.value} contract enforcement failed: {e}")
        raise StartupValidationError(f"Startup phase {phase.value} contract enforcement failed: {e}")


def create_startup_validation_hooks() -> Dict[str, Callable]:
    """
    Create validation hooks for integration with smd.py
    
    Returns dictionary of validation functions for each startup phase.
    """
    
    async def validate_initialization_phase(app_state):
        """Hook for initialization phase validation"""
        return await validate_startup_phase(app_state, ContractPhase.INITIALIZATION)
    
    async def validate_configuration_phase(app_state):
        """Hook for configuration phase validation"""
        return await validate_startup_phase(app_state, ContractPhase.CONFIGURATION)
    
    async def validate_integration_phase(app_state):
        """Hook for integration phase validation"""
        return await validate_startup_phase(app_state, ContractPhase.INTEGRATION)
    
    async def validate_readiness_phase(app_state):
        """Hook for readiness phase validation"""
        return await validate_startup_phase(app_state, ContractPhase.READINESS)
    
    return {
        "initialization": validate_initialization_phase,
        "configuration": validate_configuration_phase, 
        "integration": validate_integration_phase,
        "readiness": validate_readiness_phase
    }


# Integration point for comprehensive startup validation
async def validate_complete_startup_sequence(app_state: Any, 
                                           enforce_contracts: bool = True) -> Dict[str, Any]:
    """
    Validate complete startup sequence with all phases
    
    This function provides comprehensive startup validation and is the
    recommended approach for production systems.
    """
    validator = get_startup_validator()
    
    try:
        results = await validator.validate_startup_sequence(
            app_state, 
            ContractPhase.READINESS,
            skip_enforcement=not enforce_contracts
        )
        
        if results["success"]:
            logger.info("🎉 Complete startup sequence validation passed")
        else:
            logger.error("💥 Complete startup sequence validation failed")
            
            if enforce_contracts:
                error_message = (
                    "Startup sequence validation failed:\n" +
                    "\n".join([f"  - {failure}" for failure in results["critical_failures"]])
                )
                raise StartupValidationError(error_message)
        
        return results
        
    except Exception as e:
        logger.error(f"Startup sequence validation exception: {e}")
        if enforce_contracts:
            raise
        return {
            "success": False,
            "error": str(e),
            "critical_failures": [str(e)]
        }


if __name__ == "__main__":
    """
    Standalone execution for testing startup validation
    """
    
    async def test_startup_validation():
        """Test startup validation with mock app state"""
        
        # Create mock app state for testing
        class MockAppState:
            def __init__(self):
                self.websocket_connection_pool = None
                self.agent_websocket_bridge = None
                self.execution_engine_factory = None
        
        print("🧪 Testing startup phase validation...")
        
        # Test with empty app state (should fail)
        mock_app_state = MockAppState()
        
        validator = StartupPhaseValidator()
        
        try:
            # Test individual phase validation
            result = await validator.validate_phase(
                mock_app_state, 
                ContractPhase.INITIALIZATION,
                skip_enforcement=True  # Don't raise exceptions for testing
            )
            
            print(f"Phase validation result: {result.success}")
            if not result.success:
                print("Expected failures (empty app state):")
                for error in result.errors:
                    print(f"  - {error}")
            
            # Test complete sequence validation
            sequence_results = await validator.validate_startup_sequence(
                mock_app_state,
                ContractPhase.READINESS,
                skip_enforcement=True
            )
            
            print(f"\nSequence validation: {sequence_results['success']}")
            print(f"Total failures: {len(sequence_results['critical_failures'])}")
            
            # Generate report
            report = validator.get_validation_report()
            print(f"\n{report}")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Run test
    asyncio.run(test_startup_validation())