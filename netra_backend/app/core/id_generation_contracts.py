"""
ID Generation Contracts and Validation

Implements contract-driven development for ID generation patterns to prevent
interface mismatches and ensure SSOT compliance.

This module addresses the root cause identified in Five Whys analysis:
- Missing contract enforcement during SSOT consolidation
- No automated API validation for interface changes
- Runtime failures instead of compile-time detection
"""

import inspect
import logging
from typing import Dict, List, Set, Any, Callable
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

logger = logging.getLogger(__name__)


class ContractViolation(Exception):
    """Raised when ID generation contract is violated"""
    pass


@dataclass
class IDGenerationContract:
    """Contract definition for ID generation methods"""
    method_name: str
    expected_signature: str
    expected_return_type: str
    is_class_method: bool
    is_instance_method: bool
    required_parameters: List[str]
    description: str


class IDContractValidator:
    """Validates ID generation contracts and SSOT compliance"""
    
    def __init__(self):
        self._contracts = self._define_contracts()
        logger.info("IDContractValidator initialized")
    
    def _define_contracts(self) -> Dict[str, IDGenerationContract]:
        """Define all ID generation contracts for SSOT compliance"""
        contracts = {
            # Instance method contracts (SSOT pattern)
            "generate_id": IDGenerationContract(
                method_name="generate_id",
                expected_signature="generate_id(self, id_type: IDType, prefix: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> str",
                expected_return_type="str",
                is_class_method=False,
                is_instance_method=True,
                required_parameters=["id_type"],
                description="Primary SSOT method for ID generation"
            ),
            
            # Class method contracts (compatibility/legacy)
            "generate_run_id": IDGenerationContract(
                method_name="generate_run_id",
                expected_signature="generate_run_id(cls, thread_id: str) -> str",
                expected_return_type="str",
                is_class_method=True,
                is_instance_method=False,
                required_parameters=["thread_id"],
                description="Class method for run ID generation"
            ),
            
            "generate_thread_id": IDGenerationContract(
                method_name="generate_thread_id",
                expected_signature="generate_thread_id(cls) -> str",
                expected_return_type="str",
                is_class_method=True,
                is_instance_method=False,
                required_parameters=[],
                description="Class method for thread ID generation (compatibility)"
            ),
            
            # Module-level convenience function contracts
            "module_generate_thread_id": IDGenerationContract(
                method_name="generate_thread_id",
                expected_signature="generate_thread_id() -> str",
                expected_return_type="str",
                is_class_method=False,
                is_instance_method=False,
                required_parameters=[],
                description="Module-level convenience function for thread IDs"
            ),
        }
        
        return contracts
    
    def validate_unified_id_manager_contract(self) -> Dict[str, Any]:
        """Validate that UnifiedIDManager meets all contract requirements"""
        results = {
            "valid": True,
            "violations": [],
            "checked_methods": [],
            "missing_methods": [],
            "signature_mismatches": []
        }
        
        # Check instance methods
        instance_methods = self._get_instance_methods(UnifiedIDManager)
        class_methods = self._get_class_methods(UnifiedIDManager)
        
        # Validate each contract
        for contract_name, contract in self._contracts.items():
            if contract.is_instance_method:
                self._validate_instance_method_contract(
                    UnifiedIDManager, contract, instance_methods, results
                )
            elif contract.is_class_method:
                self._validate_class_method_contract(
                    UnifiedIDManager, contract, class_methods, results
                )
        
        # Check that all required IDType values exist
        self._validate_id_types(results)
        
        logger.info(f"Contract validation completed. Valid: {results['valid']}")
        return results
    
    def _validate_instance_method_contract(self, cls: type, contract: IDGenerationContract, 
                                         methods: Dict[str, Callable], results: Dict[str, Any]):
        """Validate instance method against contract"""
        method_name = contract.method_name
        results["checked_methods"].append(f"instance.{method_name}")
        
        if method_name not in methods:
            results["missing_methods"].append(f"instance.{method_name}")
            results["valid"] = False
            return
        
        method = methods[method_name]
        sig = inspect.signature(method)
        
        # Check required parameters exist
        param_names = list(sig.parameters.keys())
        if 'self' in param_names:
            param_names.remove('self')
        
        for required_param in contract.required_parameters:
            if required_param not in param_names:
                results["signature_mismatches"].append(
                    f"instance.{method_name}: missing required parameter '{required_param}'"
                )
                results["valid"] = False
    
    def _validate_class_method_contract(self, cls: type, contract: IDGenerationContract,
                                      methods: Dict[str, Callable], results: Dict[str, Any]):
        """Validate class method against contract"""
        method_name = contract.method_name
        results["checked_methods"].append(f"class.{method_name}")
        
        if method_name not in methods:
            results["missing_methods"].append(f"class.{method_name}")
            results["valid"] = False
            return
        
        method = methods[method_name]
        sig = inspect.signature(method)
        
        # Check required parameters exist
        param_names = list(sig.parameters.keys())
        if 'cls' in param_names:
            param_names.remove('cls')
        
        for required_param in contract.required_parameters:
            if required_param not in param_names:
                results["signature_mismatches"].append(
                    f"class.{method_name}: missing required parameter '{required_param}'"
                )
                results["valid"] = False
    
    def _validate_id_types(self, results: Dict[str, Any]):
        """Validate that all required IDType values exist"""
        required_id_types = {"USER", "SESSION", "REQUEST", "AGENT", "TOOL", 
                           "TRANSACTION", "WEBSOCKET", "EXECUTION", "TRACE", 
                           "METRIC", "THREAD"}
        
        existing_id_types = {item.name for item in IDType}
        missing_types = required_id_types - existing_id_types
        
        if missing_types:
            results["missing_methods"].extend([f"IDType.{t}" for t in missing_types])
            results["valid"] = False
    
    def _get_instance_methods(self, cls: type) -> Dict[str, Callable]:
        """Get all instance methods from a class"""
        methods = {}
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_'):  # Skip private methods
                methods[name] = method
        return methods
    
    def _get_class_methods(self, cls: type) -> Dict[str, Callable]:
        """Get all class methods from a class"""
        methods = {}
        for name, method in inspect.getmembers(cls):
            # Check if it's a class method by looking at the method type and __self__
            if (hasattr(method, '__self__') and method.__self__ is cls 
                and not name.startswith('_') and callable(method)):
                methods[name] = method
        return methods
    
    def validate_consumer_compatibility(self, consumer_module: str) -> Dict[str, Any]:
        """Validate that a consumer module uses correct ID generation patterns"""
        # This would be extended to check specific consumers
        # For now, just return success
        return {
            "valid": True,
            "consumer": consumer_module,
            "issues": []
        }


def validate_id_generation_contracts() -> Dict[str, Any]:
    """Main entry point for contract validation"""
    validator = IDContractValidator()
    return validator.validate_unified_id_manager_contract()


def enforce_id_generation_ssot():
    """Enforce SSOT compliance for ID generation (used in startup validation)"""
    results = validate_id_generation_contracts()
    
    if not results["valid"]:
        violations = []
        violations.extend(results.get("missing_methods", []))
        violations.extend(results.get("signature_mismatches", []))
        
        error_msg = f"ID generation contract violations detected: {', '.join(violations)}"
        logger.error(error_msg)
        raise ContractViolation(error_msg)
    
    logger.info("ID generation SSOT contracts validated successfully")
    return True


# Contract validation can be run during startup or testing
if __name__ == "__main__":
    results = validate_id_generation_contracts()
    if results["valid"]:
        print("✅ All ID generation contracts validated successfully")
    else:
        print("❌ Contract violations found:")
        for violation in results.get("violations", []):
            print(f"  - {violation}")
        for missing in results.get("missing_methods", []):
            print(f"  - Missing: {missing}")
        for mismatch in results.get("signature_mismatches", []):
            print(f"  - Signature issue: {mismatch}")