"""
App State Contract-Driven Development Framework

Addresses WHY #5 from Five Whys Analysis:
- Root cause: Lack of contract-driven development culture
- Solution: Implement systematic validation of component dependencies
- Prevention: Contract-first development patterns with compliance checking

This module implements contract validation for FastAPI app.state dependencies
to prevent architectural integration failures like the WebSocket bridge issue.

Extends the pattern from id_generation_contracts.py to provide:
1. App state dependency contracts
2. Startup phase validation
3. Automated contract enforcement
4. Clear error messages for troubleshooting
"""

import inspect
import logging
from typing import Dict, List, Set, Any, Type, Optional, Union
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import sys

# Import types for contract validation
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.core.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class AppStateContractViolation(Exception):
    """Raised when app state contract is violated"""
    pass


class ContractPhase(Enum):
    """Phases of system startup where contracts are validated"""
    INITIALIZATION = "initialization"
    CONFIGURATION = "configuration"
    INTEGRATION = "integration"
    READINESS = "readiness"


@dataclass
class AppStateContract:
    """Contract definition for app state components"""
    component_name: str
    component_type: Type
    required_phase: ContractPhase
    dependencies: List[str]
    validation_method: Optional[str] = None
    description: str = ""
    business_value: str = ""


@dataclass
class ValidationResult:
    """Result of contract validation"""
    valid: bool
    component_name: str
    errors: List[str]
    warnings: List[str]
    phase: ContractPhase


class AppStateValidator(ABC):
    """Abstract base for app state component validators"""
    
    @abstractmethod
    def validate(self, app_state: Any) -> ValidationResult:
        """Validate component meets contract requirements"""
        pass


class WebSocketBridgeValidator(AppStateValidator):
    """Validates AgentWebSocketBridge meets contract requirements"""
    
    def validate(self, app_state: Any) -> ValidationResult:
        errors = []
        warnings = []
        
        # Check component exists
        if not hasattr(app_state, 'agent_websocket_bridge'):
            errors.append("Missing agent_websocket_bridge in app.state")
        else:
            bridge = app_state.agent_websocket_bridge
            
            # Check component is not None
            if bridge is None:
                errors.append("agent_websocket_bridge is None")
            elif not isinstance(bridge, AgentWebSocketBridge):
                errors.append(f"agent_websocket_bridge wrong type: expected {AgentWebSocketBridge}, got {type(bridge)}")
            else:
                # Validate bridge has required components
                if not hasattr(bridge, '_connection_pool') or bridge._connection_pool is None:
                    errors.append("AgentWebSocketBridge missing connection_pool")
                
                # Check if bridge has necessary methods
                required_methods = ['emit_event', 'broadcast_event', 'add_connection']
                for method in required_methods:
                    if not hasattr(bridge, method):
                        warnings.append(f"AgentWebSocketBridge missing expected method: {method}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            component_name="agent_websocket_bridge",
            errors=errors,
            warnings=warnings,
            phase=ContractPhase.CONFIGURATION
        )


class ExecutionEngineFactoryValidator(AppStateValidator):
    """Validates ExecutionEngineFactory meets contract requirements"""
    
    def validate(self, app_state: Any) -> ValidationResult:
        errors = []
        warnings = []
        
        # Check component exists
        if not hasattr(app_state, 'execution_engine_factory'):
            errors.append("Missing execution_engine_factory in app.state")
        else:
            factory = app_state.execution_engine_factory
            
            # Check component is not None
            if factory is None:
                errors.append("execution_engine_factory is None")
            elif not isinstance(factory, ExecutionEngineFactory):
                errors.append(f"execution_engine_factory wrong type: expected {ExecutionEngineFactory}, got {type(factory)}")
            else:
                # Validate factory has websocket_bridge (prevents original bug)
                if not hasattr(factory, '_websocket_bridge') or factory._websocket_bridge is None:
                    errors.append("ExecutionEngineFactory missing _websocket_bridge (CRITICAL: prevents WebSocket events)")
                
                # Validate factory can create engines
                if not hasattr(factory, 'create_for_user'):
                    errors.append("ExecutionEngineFactory missing create_for_user method")
        
        return ValidationResult(
            valid=len(errors) == 0,
            component_name="execution_engine_factory",
            errors=errors,
            warnings=warnings,
            phase=ContractPhase.INTEGRATION
        )


class WebSocketConnectionPoolValidator(AppStateValidator):
    """Validates WebSocketConnectionPool meets contract requirements"""
    
    def validate(self, app_state: Any) -> ValidationResult:
        errors = []
        warnings = []
        
        # Check component exists  
        if not hasattr(app_state, 'websocket_connection_pool'):
            errors.append("Missing websocket_connection_pool in app.state")
        else:
            pool = app_state.websocket_connection_pool
            
            # Check component is not None
            if pool is None:
                errors.append("websocket_connection_pool is None")
            elif not isinstance(pool, WebSocketConnectionPool):
                errors.append(f"websocket_connection_pool wrong type: expected {WebSocketConnectionPool}, got {type(pool)}")
            else:
                # Validate pool has connection management capabilities
                required_methods = ['add_connection', 'remove_connection', 'get_connections']
                for method in required_methods:
                    if not hasattr(pool, method):
                        warnings.append(f"WebSocketConnectionPool missing expected method: {method}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            component_name="websocket_connection_pool", 
            errors=errors,
            warnings=warnings,
            phase=ContractPhase.INITIALIZATION
        )


class AppStateContractValidator:
    """
    Main validator for app state contracts
    
    Implements contract-driven development by validating that all required
    components are properly initialized and integrated during system startup.
    """
    
    def __init__(self):
        self._contracts = self._define_contracts()
        self._validators = self._create_validators()
        logger.info("AppStateContractValidator initialized")
    
    def _define_contracts(self) -> Dict[str, AppStateContract]:
        """Define all app state contracts for system startup validation"""
        
        contracts = {
            "websocket_connection_pool": AppStateContract(
                component_name="websocket_connection_pool",
                component_type=WebSocketConnectionPool,
                required_phase=ContractPhase.INITIALIZATION,
                dependencies=[],
                description="WebSocket connection management pool",
                business_value="Enables real-time user communication"
            ),
            
            "agent_websocket_bridge": AppStateContract(
                component_name="agent_websocket_bridge",
                component_type=AgentWebSocketBridge,
                required_phase=ContractPhase.CONFIGURATION,
                dependencies=["websocket_connection_pool"],
                description="Bridge between agent execution and WebSocket events",
                business_value="Delivers real-time agent reasoning to users (90% of platform value)"
            ),
            
            "execution_engine_factory": AppStateContract(
                component_name="execution_engine_factory",
                component_type=ExecutionEngineFactory,
                required_phase=ContractPhase.INTEGRATION,
                dependencies=["agent_websocket_bridge"],
                description="Factory for creating user-scoped execution engines",
                business_value="Enables agent execution with WebSocket event delivery"
            ),
            
            "llm_manager": AppStateContract(
                component_name="llm_manager",
                component_type=LLMManager,
                required_phase=ContractPhase.CONFIGURATION,
                dependencies=[],
                description="LLM connection and request management",
                business_value="Core AI capabilities for agent reasoning"
            )
        }
        
        return contracts
    
    def _create_validators(self) -> Dict[str, AppStateValidator]:
        """Create validator instances for each component"""
        return {
            "websocket_connection_pool": WebSocketConnectionPoolValidator(),
            "agent_websocket_bridge": WebSocketBridgeValidator(),
            "execution_engine_factory": ExecutionEngineFactoryValidator()
            # Add more validators as needed
        }
    
    def validate_app_state_contracts(self, app_state: Any, 
                                   phase: ContractPhase = ContractPhase.READINESS) -> Dict[str, Any]:
        """
        Validate all app state contracts for specified phase
        
        Args:
            app_state: FastAPI app.state object to validate
            phase: Which startup phase to validate contracts for
        
        Returns:
            Comprehensive validation results
        """
        
        results = {
            "valid": True,
            "phase": phase.value,
            "total_contracts": 0,
            "passed_contracts": 0,
            "failed_contracts": 0,
            "component_results": {},
            "critical_errors": [],
            "warnings": [],
            "business_impact": []
        }
        
        # Get contracts to validate for this phase
        phase_contracts = {
            name: contract for name, contract in self._contracts.items()
            if contract.required_phase.value <= phase.value or phase == ContractPhase.READINESS
        }
        
        results["total_contracts"] = len(phase_contracts)
        
        # Validate each contract
        for contract_name, contract in phase_contracts.items():
            validator = self._validators.get(contract_name)
            
            if validator:
                # Run validation
                validation_result = validator.validate(app_state)
                results["component_results"][contract_name] = {
                    "valid": validation_result.valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "business_value": contract.business_value,
                    "description": contract.description
                }
                
                if validation_result.valid:
                    results["passed_contracts"] += 1
                else:
                    results["failed_contracts"] += 1
                    results["valid"] = False
                    
                    # Add to critical errors
                    for error in validation_result.errors:
                        results["critical_errors"].append(f"{contract_name}: {error}")
                    
                    # Add business impact assessment
                    if contract.business_value:
                        results["business_impact"].append({
                            "component": contract_name,
                            "impact": contract.business_value,
                            "severity": "HIGH" if "90% of platform value" in contract.business_value else "MEDIUM"
                        })
                
                # Add warnings
                results["warnings"].extend([
                    f"{contract_name}: {warning}" for warning in validation_result.warnings
                ])
                
            else:
                # No validator available - this is a framework issue
                results["warnings"].append(f"No validator available for {contract_name}")
        
        # Log results
        if results["valid"]:
            logger.info(f"✅ App state contracts validated: {results['passed_contracts']}/{results['total_contracts']} passed")
        else:
            logger.error(f"❌ App state contract violations: {results['failed_contracts']}/{results['total_contracts']} failed")
            for error in results["critical_errors"]:
                logger.error(f"   - {error}")
        
        return results
    
    def validate_dependency_order(self, app_state: Any) -> Dict[str, Any]:
        """
        Validate that components are initialized in proper dependency order
        
        This prevents issues where a component is created before its dependencies.
        """
        
        results = {
            "valid": True,
            "dependency_violations": [],
            "initialization_order": []
        }
        
        # Check each component's dependencies
        for contract_name, contract in self._contracts.items():
            # Check if component exists
            if hasattr(app_state, contract.component_name) and getattr(app_state, contract.component_name) is not None:
                results["initialization_order"].append(contract_name)
                
                # Check if all dependencies exist
                for dependency in contract.dependencies:
                    if not hasattr(app_state, dependency) or getattr(app_state, dependency) is None:
                        violation = f"{contract_name} initialized before dependency {dependency}"
                        results["dependency_violations"].append(violation)
                        results["valid"] = False
        
        if not results["valid"]:
            logger.error("❌ Dependency order violations detected:")
            for violation in results["dependency_violations"]:
                logger.error(f"   - {violation}")
        
        return results
    
    def enforce_startup_contracts(self, app_state: Any, phase: ContractPhase) -> bool:
        """
        Enforce contracts during startup - raises exception if violations found
        
        This is the "fail fast" mechanism that prevents runtime failures.
        """
        
        # Validate contracts
        results = self.validate_app_state_contracts(app_state, phase)
        
        if not results["valid"]:
            # Create detailed error message
            error_details = []
            error_details.append(f"App state contract violations in {phase.value} phase:")
            
            for error in results["critical_errors"]:
                error_details.append(f"  - {error}")
            
            if results["business_impact"]:
                error_details.append("\nBusiness Impact:")
                for impact in results["business_impact"]:
                    error_details.append(f"  - {impact['component']}: {impact['impact']} (Severity: {impact['severity']})")
            
            error_details.append(f"\nTroubleshooting: Check system startup sequence in smd.py")
            error_details.append("Ensure all components are properly initialized before creating dependent components.")
            
            error_message = "\n".join(error_details)
            logger.error(error_message)
            
            raise AppStateContractViolation(error_message)
        
        # Also validate dependency order
        dep_results = self.validate_dependency_order(app_state)
        if not dep_results["valid"]:
            error_message = f"Dependency order violations: {dep_results['dependency_violations']}"
            logger.error(error_message)
            raise AppStateContractViolation(error_message)
        
        logger.info(f"✅ App state contracts enforced successfully for {phase.value} phase")
        return True


def validate_app_state_contracts(app_state: Any, 
                               phase: ContractPhase = ContractPhase.READINESS) -> Dict[str, Any]:
    """
    Main entry point for app state contract validation
    
    Args:
        app_state: FastAPI app.state object
        phase: Which startup phase to validate
    
    Returns:
        Validation results
    """
    validator = AppStateContractValidator()
    return validator.validate_app_state_contracts(app_state, phase)


def enforce_app_state_contracts(app_state: Any, phase: ContractPhase) -> bool:
    """
    Main entry point for contract enforcement (raises exception on violations)
    
    Use this during system startup to fail fast if contracts are violated.
    
    Args:
        app_state: FastAPI app.state object
        phase: Which startup phase to enforce
    
    Returns:
        True if all contracts valid
    
    Raises:
        AppStateContractViolation: If any contract violations found
    """
    validator = AppStateContractValidator()
    return validator.enforce_startup_contracts(app_state, phase)


def create_app_state_contract_report(app_state: Any) -> str:
    """
    Generate comprehensive app state contract compliance report
    
    Returns human-readable report of contract status for debugging/monitoring.
    """
    validator = AppStateContractValidator()
    results = validator.validate_app_state_contracts(app_state, ContractPhase.READINESS)
    
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("APP STATE CONTRACT COMPLIANCE REPORT")
    report_lines.append("=" * 60)
    
    # Overall status
    status = "✅ PASSED" if results["valid"] else "❌ FAILED"
    report_lines.append(f"Overall Status: {status}")
    report_lines.append(f"Contracts: {results['passed_contracts']}/{results['total_contracts']} passed")
    report_lines.append("")
    
    # Component details
    report_lines.append("COMPONENT DETAILS:")
    report_lines.append("-" * 40)
    
    for component_name, component_result in results["component_results"].items():
        status_icon = "✅" if component_result["valid"] else "❌"
        report_lines.append(f"{status_icon} {component_name}")
        report_lines.append(f"   Description: {component_result['description']}")
        report_lines.append(f"   Business Value: {component_result['business_value']}")
        
        if component_result["errors"]:
            report_lines.append("   Errors:")
            for error in component_result["errors"]:
                report_lines.append(f"     - {error}")
        
        if component_result["warnings"]:
            report_lines.append("   Warnings:")
            for warning in component_result["warnings"]:
                report_lines.append(f"     - {warning}")
        
        report_lines.append("")
    
    # Business impact
    if results["business_impact"]:
        report_lines.append("BUSINESS IMPACT ASSESSMENT:")
        report_lines.append("-" * 40)
        for impact in results["business_impact"]:
            report_lines.append(f"⚠️  {impact['component']} ({impact['severity']} severity)")
            report_lines.append(f"   Impact: {impact['impact']}")
            report_lines.append("")
    
    # Recommendations
    if not results["valid"]:
        report_lines.append("RECOMMENDED ACTIONS:")
        report_lines.append("-" * 40)
        report_lines.append("1. Check system startup sequence in smd.py")
        report_lines.append("2. Ensure components initialized in dependency order")
        report_lines.append("3. Validate component configuration parameters")
        report_lines.append("4. Review component constructor requirements")
        report_lines.append("")
    
    report_lines.append("=" * 60)
    
    return "\n".join(report_lines)


# Contract validation can be run during startup, testing, or monitoring
if __name__ == "__main__":
    """
    Standalone execution for testing and development
    """
    
    # Create mock app state for testing
    class MockAppState:
        def __init__(self):
            # Simulate properly configured app state
            from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            
            self.websocket_connection_pool = WebSocketConnectionPool()
            self.agent_websocket_bridge = AgentWebSocketBridge(connection_pool=self.websocket_connection_pool)
            self.execution_engine_factory = ExecutionEngineFactory(websocket_bridge=self.agent_websocket_bridge)
    
    # Test with properly configured state
    print("Testing with properly configured app state...")
    mock_app_state = MockAppState()
    
    try:
        results = validate_app_state_contracts(mock_app_state, ContractPhase.READINESS)
        print(f"✅ Validation Results: {results['passed_contracts']}/{results['total_contracts']} passed")
        
        # Generate report
        report = create_app_state_contract_report(mock_app_state)
        print("\n" + report)
        
    except Exception as e:
        print(f"❌ Contract validation error: {e}")
    
    # Test with broken state (missing components)
    print("\n" + "="*60)
    print("Testing with broken app state (missing components)...")
    
    class BrokenAppState:
        def __init__(self):
            # Simulate broken app state - missing critical components
            pass
    
    broken_app_state = BrokenAppState()
    
    try:
        results = validate_app_state_contracts(broken_app_state, ContractPhase.READINESS) 
        print(f"Results: {results['passed_contracts']}/{results['total_contracts']} passed")
        
        if not results["valid"]:
            print("\nCritical Errors:")
            for error in results["critical_errors"]:
                print(f"  - {error}")
        
    except Exception as e:
        print(f"❌ Contract validation error (expected): {e}")