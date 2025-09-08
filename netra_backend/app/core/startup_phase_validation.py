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

import logging
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

logger = logging.getLogger(__name__)


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
        Validate specific startup phase
        
        Args:
            app_state: FastAPI app.state object
            target_phase: Phase to validate
            skip_enforcement: If True, log errors but don't raise exceptions
        
        Returns:
            Phase validation results
        """
        start_time = time.time()
        logger.info(f"🔍 Validating startup phase: {target_phase.value}")
        
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
                logger.info(f"✅ Phase {target_phase.value} validation passed: "
                          f"{contract_results['passed_contracts']}/{contract_results['total_contracts']} "
                          f"contracts validated in {duration:.2f}s")
                
                self.current_phase = target_phase
                if target_phase not in self.completed_phases:
                    self.completed_phases.append(target_phase)
                    
            else:
                logger.error(f"❌ Phase {target_phase.value} validation failed: "
                           f"{len(phase_result.errors)} critical errors")
                
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
            logger.error(f"💥 Phase {target_phase.value} validation exception: {e}")
            
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