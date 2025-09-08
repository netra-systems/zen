"""
Contract-Driven Development Framework for Factory Pattern Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent systematic parameter mismatch failures
- Value Impact: Eliminates factory interface drift and parameter naming inconsistencies  
- Revenue Impact: Prevents downtime from parameter validation failures across the platform

This module implements the Contract-Driven Development framework identified as the
systematic solution to prevent factory interface parameter mismatches. It provides
automated validation, interface contract enforcement, and breaking change detection.

Root Cause Addressed: "Absence of Contract-Driven Development practices in complex factory architectures"
Key Prevention: Automated interface signature validation and compatibility testing

Architecture:
- InterfaceContract: Defines expected method signatures and parameter names
- ContractValidator: Validates implementations against contracts
- SignatureAnalyzer: Analyzes parameter signatures for inconsistencies
- BreakingChangeDetector: Identifies interface compatibility issues
"""

import inspect
import ast
import logging
from typing import Dict, List, Set, Any, Optional, Type, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import difflib
import json
from datetime import datetime
import hashlib

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class ParameterInfo:
    """Information about a parameter in a method signature."""
    name: str
    annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_required: bool = True
    position: int = 0


@dataclass 
class MethodContract:
    """Contract definition for a method including parameter expectations."""
    method_name: str
    parameters: List[ParameterInfo] = field(default_factory=list)
    return_annotation: Optional[str] = None
    docstring: Optional[str] = None
    is_async: bool = False
    
    def get_parameter_names(self) -> Set[str]:
        """Get set of parameter names for this method."""
        return {param.name for param in self.parameters}
    
    def get_required_parameters(self) -> Set[str]:
        """Get set of required parameter names."""
        return {param.name for param in self.parameters if param.is_required}


@dataclass
class InterfaceContract:
    """Complete interface contract for a class or factory pattern."""
    interface_name: str
    methods: List[MethodContract] = field(default_factory=list)
    class_docstring: Optional[str] = None
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_method_contract(self, method_name: str) -> Optional[MethodContract]:
        """Get contract for a specific method."""
        for method in self.methods:
            if method.method_name == method_name:
                return method
        return None
    
    def get_all_parameter_names(self) -> Set[str]:
        """Get all unique parameter names across all methods."""
        all_params = set()
        for method in self.methods:
            all_params.update(method.get_parameter_names())
        return all_params


@dataclass
class ValidationResult:
    """Result of contract validation."""
    is_valid: bool
    interface_name: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parameter_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    missing_methods: List[str] = field(default_factory=list)
    signature_changes: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False
        
    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.warnings.append(warning)
    
    def add_parameter_mismatch(self, method: str, expected: str, actual: str, position: int) -> None:
        """Add parameter mismatch details."""
        self.parameter_mismatches.append({
            'method': method,
            'expected_param': expected,
            'actual_param': actual,
            'position': position,
            'mismatch_type': 'parameter_name'
        })
        self.add_error(f"Parameter mismatch in {method}: expected '{expected}', got '{actual}' at position {position}")


class SignatureAnalyzer:
    """Analyzes method signatures and extracts parameter information."""
    
    @staticmethod
    def extract_method_contract(func: Callable) -> MethodContract:
        """Extract method contract from a function or method."""
        sig = inspect.signature(func)
        method_name = func.__name__
        
        parameters = []
        for i, (param_name, param) in enumerate(sig.parameters.items()):
            if param_name in ('self', 'cls'):
                continue
                
            param_info = ParameterInfo(
                name=param_name,
                annotation=str(param.annotation) if param.annotation != inspect.Parameter.empty else None,
                default_value=str(param.default) if param.default != inspect.Parameter.empty else None,
                is_required=param.default == inspect.Parameter.empty,
                position=i
            )
            parameters.append(param_info)
        
        return MethodContract(
            method_name=method_name,
            parameters=parameters,
            return_annotation=str(sig.return_annotation) if sig.return_annotation != inspect.Parameter.empty else None,
            docstring=inspect.getdoc(func),
            is_async=inspect.iscoroutinefunction(func)
        )
    
    @staticmethod
    def extract_class_contract(cls: Type) -> InterfaceContract:
        """Extract complete interface contract from a class."""
        contract = InterfaceContract(
            interface_name=cls.__name__,
            class_docstring=inspect.getdoc(cls)
        )
        
        # Extract all public methods (including __init__)
        for name, method in inspect.getmembers(cls, predicate=inspect.ismethod):
            if not name.startswith('_') or name == '__init__':
                method_contract = SignatureAnalyzer.extract_method_contract(method)
                contract.methods.append(method_contract)
        
        # Also check for functions defined in the class (including __init__)
        for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_') or name == '__init__':
                method_contract = SignatureAnalyzer.extract_method_contract(func)
                contract.methods.append(method_contract)
        
        return contract


class ContractValidator:
    """Validates implementations against interface contracts."""
    
    def __init__(self):
        self.known_contracts: Dict[str, InterfaceContract] = {}
        self.validation_history: List[ValidationResult] = []
    
    def register_contract(self, contract: InterfaceContract) -> None:
        """Register an interface contract for validation."""
        self.known_contracts[contract.interface_name] = contract
        logger.info(f"Registered interface contract: {contract.interface_name}")
    
    def validate_implementation(self, cls: Type, contract_name: Optional[str] = None) -> ValidationResult:
        """Validate a class implementation against its contract."""
        if contract_name is None:
            contract_name = cls.__name__
        
        if contract_name not in self.known_contracts:
            result = ValidationResult(
                is_valid=False,
                interface_name=contract_name
            )
            result.add_error(f"No contract found for {contract_name}")
            return result
        
        expected_contract = self.known_contracts[contract_name]
        actual_contract = SignatureAnalyzer.extract_class_contract(cls)
        
        return self._validate_contracts(expected_contract, actual_contract)
    
    def _validate_contracts(self, expected: InterfaceContract, actual: InterfaceContract) -> ValidationResult:
        """Validate actual contract against expected contract."""
        result = ValidationResult(
            is_valid=True,
            interface_name=expected.interface_name
        )
        
        # Check for missing methods
        expected_methods = {method.method_name for method in expected.methods}
        actual_methods = {method.method_name for method in actual.methods}
        
        missing_methods = expected_methods - actual_methods
        for missing_method in missing_methods:
            result.missing_methods.append(missing_method)
            result.add_error(f"Missing required method: {missing_method}")
        
        # Check method signatures for existing methods
        for expected_method in expected.methods:
            actual_method = actual.get_method_contract(expected_method.method_name)
            if actual_method:
                self._validate_method_signatures(expected_method, actual_method, result)
        
        self.validation_history.append(result)
        return result
    
    def _validate_method_signatures(self, expected: MethodContract, actual: MethodContract, result: ValidationResult) -> None:
        """Validate method signatures match expected contract."""
        method_name = expected.method_name
        
        # Validate async/sync consistency
        if expected.is_async != actual.is_async:
            result.add_error(f"Method {method_name}: async mismatch (expected: {expected.is_async}, actual: {actual.is_async})")
        
        # Validate parameter names and positions - THIS IS THE CRITICAL FIX
        expected_params = expected.parameters
        actual_params = actual.parameters
        
        # Check parameter count
        if len(expected_params) != len(actual_params):
            result.add_warning(f"Method {method_name}: parameter count mismatch (expected: {len(expected_params)}, actual: {len(actual_params)})")
        
        # Check parameter names at each position
        for i, expected_param in enumerate(expected_params):
            if i < len(actual_params):
                actual_param = actual_params[i]
                if expected_param.name != actual_param.name:
                    result.add_parameter_mismatch(
                        method=method_name,
                        expected=expected_param.name,
                        actual=actual_param.name,
                        position=i
                    )
                
                # Check required vs optional mismatch
                if expected_param.is_required != actual_param.is_required:
                    result.add_warning(f"Method {method_name}: parameter '{expected_param.name}' required mismatch")
            else:
                result.add_error(f"Method {method_name}: missing parameter '{expected_param.name}' at position {i}")


class BreakingChangeDetector:
    """Detects breaking changes in interface contracts."""
    
    def __init__(self, contracts_dir: Optional[Path] = None):
        self.contracts_dir = contracts_dir or Path("contracts")
        self.contracts_dir.mkdir(exist_ok=True)
        
    def save_contract_baseline(self, contract: InterfaceContract) -> None:
        """Save a contract as the baseline for future comparisons."""
        baseline_file = self.contracts_dir / f"{contract.interface_name}_baseline.json"
        
        contract_data = {
            'interface_name': contract.interface_name,
            'version': contract.version,
            'created_at': contract.created_at.isoformat(),
            'class_docstring': contract.class_docstring,
            'methods': [
                {
                    'method_name': method.method_name,
                    'parameters': [
                        {
                            'name': param.name,
                            'annotation': param.annotation,
                            'default_value': param.default_value,
                            'is_required': param.is_required,
                            'position': param.position
                        } for param in method.parameters
                    ],
                    'return_annotation': method.return_annotation,
                    'is_async': method.is_async,
                    'docstring': method.docstring
                } for method in contract.methods
            ]
        }
        
        with open(baseline_file, 'w') as f:
            json.dump(contract_data, f, indent=2)
        
        logger.info(f"Saved contract baseline for {contract.interface_name}")
    
    def detect_breaking_changes(self, current_contract: InterfaceContract) -> List[str]:
        """Detect breaking changes compared to baseline."""
        baseline_file = self.contracts_dir / f"{current_contract.interface_name}_baseline.json"
        
        if not baseline_file.exists():
            logger.warning(f"No baseline found for {current_contract.interface_name}")
            return []
        
        with open(baseline_file) as f:
            baseline_data = json.load(f)
        
        breaking_changes = []
        
        # Reconstruct baseline contract
        baseline_contract = self._reconstruct_contract(baseline_data)
        
        # Compare contracts
        baseline_methods = {method.method_name: method for method in baseline_contract.methods}
        current_methods = {method.method_name: method for method in current_contract.methods}
        
        # Check for removed methods (breaking)
        removed_methods = set(baseline_methods.keys()) - set(current_methods.keys())
        for method_name in removed_methods:
            breaking_changes.append(f"BREAKING: Method '{method_name}' was removed")
        
        # Check for method signature changes
        for method_name, baseline_method in baseline_methods.items():
            if method_name in current_methods:
                current_method = current_methods[method_name]
                method_changes = self._compare_method_signatures(baseline_method, current_method)
                breaking_changes.extend([f"BREAKING in {method_name}: {change}" for change in method_changes])
        
        return breaking_changes
    
    def _reconstruct_contract(self, contract_data: Dict[str, Any]) -> InterfaceContract:
        """Reconstruct InterfaceContract from JSON data."""
        contract = InterfaceContract(
            interface_name=contract_data['interface_name'],
            version=contract_data['version'],
            class_docstring=contract_data.get('class_docstring'),
            created_at=datetime.fromisoformat(contract_data['created_at'])
        )
        
        for method_data in contract_data['methods']:
            parameters = []
            for param_data in method_data['parameters']:
                param = ParameterInfo(
                    name=param_data['name'],
                    annotation=param_data['annotation'],
                    default_value=param_data['default_value'],
                    is_required=param_data['is_required'],
                    position=param_data['position']
                )
                parameters.append(param)
            
            method = MethodContract(
                method_name=method_data['method_name'],
                parameters=parameters,
                return_annotation=method_data['return_annotation'],
                is_async=method_data['is_async'],
                docstring=method_data['docstring']
            )
            contract.methods.append(method)
        
        return contract
    
    def _compare_method_signatures(self, baseline: MethodContract, current: MethodContract) -> List[str]:
        """Compare method signatures for breaking changes."""
        changes = []
        
        # Check async/sync change (breaking)
        if baseline.is_async != current.is_async:
            changes.append(f"Changed from {'async' if baseline.is_async else 'sync'} to {'async' if current.is_async else 'sync'}")
        
        # Check parameter changes
        baseline_params = {param.name: param for param in baseline.parameters}
        current_params = {param.name: param for param in current.parameters}
        
        # Removed required parameters (breaking)
        removed_required = []
        for param_name, param in baseline_params.items():
            if param_name not in current_params and param.is_required:
                removed_required.append(param_name)
        
        if removed_required:
            changes.append(f"Removed required parameters: {', '.join(removed_required)}")
        
        # Parameter position changes (breaking for positional calls)
        baseline_positions = [(param.name, param.position) for param in baseline.parameters]
        current_positions = [(param.name, param.position) for param in current.parameters if param.name in baseline_params]
        
        for baseline_name, baseline_pos in baseline_positions:
            for current_name, current_pos in current_positions:
                if baseline_name == current_name and baseline_pos != current_pos:
                    changes.append(f"Parameter '{baseline_name}' moved from position {baseline_pos} to {current_pos}")
        
        # Parameter name changes at same position (breaking for positional calls)
        for i, baseline_param in enumerate(baseline.parameters):
            if i < len(current.parameters):
                current_param = current.parameters[i]
                if baseline_param.name != current_param.name:
                    changes.append(f"Parameter name changed at position {i}: '{baseline_param.name}' -> '{current_param.name}'")
        
        return changes


class FactoryContractRegistry:
    """Registry for factory pattern contracts."""
    
    def __init__(self):
        self.validator = ContractValidator()
        self.breaking_change_detector = BreakingChangeDetector()
        self._register_core_contracts()
    
    def _register_core_contracts(self) -> None:
        """Register core factory pattern contracts."""
        
        # UserExecutionContext contract - critical for factory creation
        user_execution_context_contract = InterfaceContract(
            interface_name="UserExecutionContext",
            version="1.0"
        )
        
        # Constructor contract - this is where the parameter mismatch occurred
        constructor_contract = MethodContract(
            method_name="__init__",
            parameters=[
                ParameterInfo("user_id", annotation="str", is_required=True, position=0),
                ParameterInfo("thread_id", annotation="str", is_required=True, position=1),
                ParameterInfo("run_id", annotation="str", is_required=True, position=2),
                ParameterInfo("request_id", annotation="str", is_required=False, position=3),
                ParameterInfo("db_session", annotation="Optional[AsyncSession]", is_required=False, position=4),
                ParameterInfo("websocket_client_id", annotation="Optional[str]", is_required=False, position=5),  # CRITICAL: This is the correct name
                ParameterInfo("created_at", annotation="datetime", is_required=False, position=6),
                ParameterInfo("agent_context", annotation="Dict[str, Any]", is_required=False, position=7),
                ParameterInfo("audit_metadata", annotation="Dict[str, Any]", is_required=False, position=8),
                ParameterInfo("operation_depth", annotation="int", is_required=False, position=9),
                ParameterInfo("parent_request_id", annotation="Optional[str]", is_required=False, position=10),
            ]
        )
        user_execution_context_contract.methods.append(constructor_contract)
        
        # Factory method contracts
        websocket_manager_factory_contract = InterfaceContract(
            interface_name="WebSocketManagerFactory",
            version="1.0"
        )
        
        create_manager_contract = MethodContract(
            method_name="create_manager",
            parameters=[
                ParameterInfo("user_context", annotation="UserExecutionContext", is_required=True, position=0)
            ]
        )
        websocket_manager_factory_contract.methods.append(create_manager_contract)
        
        # Register contracts
        self.validator.register_contract(user_execution_context_contract)
        self.validator.register_contract(websocket_manager_factory_contract)
        
        logger.info("Registered core factory pattern contracts")
    
    def validate_factory_pattern(self, factory_class: Type) -> ValidationResult:
        """Validate a factory class against registered contracts."""
        return self.validator.validate_implementation(factory_class)
    
    def validate_user_execution_context(self, context_class: Type) -> ValidationResult:
        """Validate UserExecutionContext implementation."""
        return self.validator.validate_implementation(context_class, "UserExecutionContext")
    
    def check_for_breaking_changes(self, interface_name: str, current_implementation: Type) -> List[str]:
        """Check for breaking changes in an interface."""
        current_contract = SignatureAnalyzer.extract_class_contract(current_implementation)
        current_contract.interface_name = interface_name
        
        return self.breaking_change_detector.detect_breaking_changes(current_contract)
    
    def save_baseline_contracts(self, implementations: Dict[str, Type]) -> None:
        """Save baseline contracts for multiple implementations."""
        for interface_name, impl_class in implementations.items():
            contract = SignatureAnalyzer.extract_class_contract(impl_class)
            contract.interface_name = interface_name
            self.breaking_change_detector.save_contract_baseline(contract)


# Global registry instance
_contract_registry: Optional[FactoryContractRegistry] = None


def get_contract_registry() -> FactoryContractRegistry:
    """Get the global factory contract registry."""
    global _contract_registry
    if _contract_registry is None:
        _contract_registry = FactoryContractRegistry()
    return _contract_registry


def validate_factory_interface(factory_class: Type, interface_name: Optional[str] = None) -> ValidationResult:
    """
    Validate a factory class interface against its contract.
    
    This is the main validation function that should be used in tests and CI/CD.
    
    Args:
        factory_class: Factory class to validate
        interface_name: Optional interface name (defaults to class name)
        
    Returns:
        ValidationResult with detailed validation information
    """
    registry = get_contract_registry()
    
    if interface_name:
        return registry.validator.validate_implementation(factory_class, interface_name)
    else:
        return registry.validate_factory_pattern(factory_class)


def check_parameter_compatibility(method1: Callable, method2: Callable) -> List[str]:
    """
    Check parameter compatibility between two methods.
    
    This function specifically checks for parameter name and position mismatches
    that could cause the type of error we saw in the supervisor factory.
    
    Args:
        method1: First method (expected interface)
        method2: Second method (actual implementation)
        
    Returns:
        List of compatibility issues
    """
    contract1 = SignatureAnalyzer.extract_method_contract(method1)
    contract2 = SignatureAnalyzer.extract_method_contract(method2)
    
    issues = []
    
    # Check parameter count
    if len(contract1.parameters) != len(contract2.parameters):
        issues.append(f"Parameter count mismatch: {len(contract1.parameters)} vs {len(contract2.parameters)}")
    
    # Check parameter names and positions
    for i, param1 in enumerate(contract1.parameters):
        if i < len(contract2.parameters):
            param2 = contract2.parameters[i]
            if param1.name != param2.name:
                issues.append(f"Parameter name mismatch at position {i}: '{param1.name}' vs '{param2.name}'")
    
    return issues


__all__ = [
    "ParameterInfo",
    "MethodContract", 
    "InterfaceContract",
    "ValidationResult",
    "SignatureAnalyzer",
    "ContractValidator",
    "BreakingChangeDetector",
    "FactoryContractRegistry",
    "get_contract_registry",
    "validate_factory_interface",
    "check_parameter_compatibility"
]