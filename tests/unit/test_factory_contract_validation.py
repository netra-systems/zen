"""
Unit Tests for Factory Contract Validation Framework

These tests ensure the contract validation framework correctly identifies
parameter mismatches and interface violations in factory patterns.
"""

import pytest
import inspect
from typing import Dict, Any, Optional
from unittest.mock import Mock

from shared.lifecycle.contract_validation_framework import (
    ParameterInfo,
    MethodContract,
    InterfaceContract,
    ValidationResult,
    SignatureAnalyzer,
    ContractValidator,
    BreakingChangeDetector,
    FactoryContractRegistry,
    get_contract_registry,
    validate_factory_interface,
    check_parameter_compatibility
)


class TestParameterMismatchDetection:
    """Test suite specifically for parameter mismatch detection."""
    
    def test_parameter_name_mismatch_detection(self):
        """Test detection of parameter name mismatches."""
        
        # Create a mock class with parameter mismatch (the actual bug scenario)
        class MockUserExecutionContext:
            def __init__(self, user_id: str, thread_id: str, run_id: str, websocket_connection_id: Optional[str] = None):
                pass
        
        # The expected contract uses websocket_client_id
        expected_contract = InterfaceContract(interface_name="MockUserExecutionContext")
        constructor_contract = MethodContract(
            method_name="__init__",
            parameters=[
                ParameterInfo("user_id", is_required=True, position=0),
                ParameterInfo("thread_id", is_required=True, position=1), 
                ParameterInfo("run_id", is_required=True, position=2),
                ParameterInfo("websocket_client_id", is_required=False, position=3),  # Expected name
            ]
        )
        expected_contract.methods.append(constructor_contract)
        
        validator = ContractValidator()
        validator.register_contract(expected_contract)
        
        # Validate the mock implementation
        result = validator.validate_implementation(MockUserExecutionContext, "MockUserExecutionContext")
        
        # Should detect the parameter mismatch
        assert not result.is_valid
        assert len(result.parameter_mismatches) == 1
        
        mismatch = result.parameter_mismatches[0]
        assert mismatch['method'] == '__init__'
        assert mismatch['expected_param'] == 'websocket_client_id'
        assert mismatch['actual_param'] == 'websocket_connection_id'
        assert mismatch['position'] == 3
    
    def test_parameter_position_validation(self):
        """Test validation of parameter positions."""
        
        def expected_function(user_id: str, websocket_client_id: str, thread_id: str):
            pass
        
        def actual_function(user_id: str, thread_id: str, websocket_client_id: str):
            pass
        
        issues = check_parameter_compatibility(expected_function, actual_function)
        
        # Should detect position mismatches
        assert len(issues) > 0
        assert any("position" in issue for issue in issues)
    
    def test_missing_required_parameter(self):
        """Test detection of missing required parameters."""
        
        class ExpectedInterface:
            def create_manager(self, user_context, websocket_client_id: str):
                pass
        
        class ActualImplementation:
            def create_manager(self, user_context):  # Missing websocket_client_id
                pass
        
        expected_contract = SignatureAnalyzer.extract_class_contract(ExpectedInterface)
        actual_contract = SignatureAnalyzer.extract_class_contract(ActualImplementation)
        
        validator = ContractValidator()
        result = validator._validate_contracts(expected_contract, actual_contract)
        
        assert not result.is_valid
        assert any("websocket_client_id" in error for error in result.errors)
    
    def test_async_sync_mismatch(self):
        """Test detection of async/sync mismatches."""
        
        class ExpectedInterface:
            async def create_manager(self, user_context):
                pass
        
        class ActualImplementation:
            def create_manager(self, user_context):  # Not async
                pass
        
        expected_contract = SignatureAnalyzer.extract_class_contract(ExpectedInterface)
        actual_contract = SignatureAnalyzer.extract_class_contract(ActualImplementation)
        
        validator = ContractValidator()
        result = validator._validate_contracts(expected_contract, actual_contract)
        
        assert not result.is_valid
        assert any("async mismatch" in error for error in result.errors)


class TestUserExecutionContextValidation:
    """Test validation of UserExecutionContext specifically."""
    
    def test_user_execution_context_contract_validation(self):
        """Test UserExecutionContext contract validation."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        registry = get_contract_registry()
        result = registry.validate_user_execution_context(UserExecutionContext)
        
        # Should validate successfully with correct parameter names
        if not result.is_valid:
            # Print details for debugging
            for error in result.errors:
                print(f"Validation error: {error}")
            for mismatch in result.parameter_mismatches:
                print(f"Parameter mismatch: {mismatch}")
        
        assert result.is_valid, f"UserExecutionContext validation failed: {result.errors}"
    
    def test_websocket_client_id_parameter_present(self):
        """Test that UserExecutionContext has websocket_client_id parameter."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        sig = inspect.signature(UserExecutionContext.__init__)
        param_names = list(sig.parameters.keys())
        
        assert 'websocket_client_id' in param_names, f"websocket_client_id not found in parameters: {param_names}"
        assert 'websocket_connection_id' not in param_names, f"Legacy websocket_connection_id found in parameters: {param_names}"
    
    def test_user_execution_context_creation_with_correct_parameter(self):
        """Test UserExecutionContext creation with correct parameter name."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Should work with websocket_client_id - use non-placeholder values
        context = UserExecutionContext(
            user_id="usr_12345678901234567890",
            thread_id="thrd_12345678901234567890",
            run_id="run_12345678901234567890",
            websocket_client_id="ws_client_12345678901234567890"
        )
        
        assert context.websocket_client_id == "ws_client_12345678901234567890"
    
    def test_user_execution_context_backward_compatibility(self):
        """Test UserExecutionContext backward compatibility properties."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        context = UserExecutionContext(
            user_id="usr_12345678901234567890",
            thread_id="thrd_12345678901234567890", 
            run_id="run_12345678901234567890",
            websocket_client_id="ws_client_12345678901234567890"
        )
        
        # Should provide backward compatibility property
        assert hasattr(context, 'websocket_connection_id')
        assert context.websocket_connection_id == context.websocket_client_id


class TestFactoryPatternValidation:
    """Test validation of factory patterns."""
    
    def test_websocket_manager_factory_validation(self):
        """Test WebSocketManagerFactory interface validation."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            result = validate_factory_interface(WebSocketManagerFactory)
            
            # Print any issues for debugging
            if not result.is_valid:
                for error in result.errors:
                    print(f"Factory validation error: {error}")
                for warning in result.warnings:
                    print(f"Factory validation warning: {warning}")
            
            # Factory should validate successfully
            assert result.is_valid or len(result.errors) == 0  # Allow warnings but not errors
            
        except ImportError:
            pytest.skip("WebSocketManagerFactory not available")
    
    def test_supervisor_factory_validation(self):
        """Test supervisor factory function validation."""
        try:
            from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
            
            # Check signature
            sig = inspect.signature(get_websocket_scoped_supervisor)
            param_names = list(sig.parameters.keys())
            
            # Should not have websocket_connection_id as parameter (it takes context)
            assert 'websocket_connection_id' not in param_names
            
        except ImportError:
            pytest.skip("Supervisor factory not available")


class TestBreakingChangeDetection:
    """Test breaking change detection."""
    
    def test_parameter_name_change_detection(self):
        """Test detection of parameter name changes."""
        
        class OriginalInterface:
            def create_manager(self, user_context, websocket_connection_id: str):
                pass
        
        class ModifiedInterface:
            def create_manager(self, user_context, websocket_client_id: str):  # Parameter renamed
                pass
        
        detector = BreakingChangeDetector()
        
        # Save baseline
        original_contract = SignatureAnalyzer.extract_class_contract(OriginalInterface)
        original_contract.interface_name = "TestInterface"
        detector.save_contract_baseline(original_contract)
        
        # Check for changes
        modified_contract = SignatureAnalyzer.extract_class_contract(ModifiedInterface)
        modified_contract.interface_name = "TestInterface"
        
        changes = detector.detect_breaking_changes(modified_contract)
        
        # Should detect parameter name change
        assert len(changes) > 0
        assert any("Parameter name changed" in change for change in changes)
    
    def test_removed_required_parameter_detection(self):
        """Test detection of removed required parameters."""
        
        class OriginalInterface:
            def create_manager(self, user_context, required_param: str):
                pass
        
        class ModifiedInterface:
            def create_manager(self, user_context):  # Required parameter removed
                pass
        
        detector = BreakingChangeDetector()
        
        # Save baseline
        original_contract = SignatureAnalyzer.extract_class_contract(OriginalInterface)  
        original_contract.interface_name = "TestInterface"
        detector.save_contract_baseline(original_contract)
        
        # Check for changes
        modified_contract = SignatureAnalyzer.extract_class_contract(ModifiedInterface)
        modified_contract.interface_name = "TestInterface"
        
        changes = detector.detect_breaking_changes(modified_contract)
        
        # Should detect removed required parameter
        assert len(changes) > 0
        assert any("Removed required parameters" in change for change in changes)


class TestSignatureAnalyzer:
    """Test signature analysis functionality."""
    
    def test_extract_method_contract(self):
        """Test extraction of method contracts."""
        
        def test_function(param1: str, param2: int = 42, param3: Optional[str] = None):
            """Test function docstring."""
            pass
        
        contract = SignatureAnalyzer.extract_method_contract(test_function)
        
        assert contract.method_name == "test_function"
        assert contract.docstring == "Test function docstring."
        assert len(contract.parameters) == 3
        
        # Check parameter details
        param1 = contract.parameters[0]
        assert param1.name == "param1"
        assert param1.is_required == True
        assert param1.position == 0
        
        param2 = contract.parameters[1]
        assert param2.name == "param2"
        assert param2.is_required == False
        assert param2.default_value == "42"
        
        param3 = contract.parameters[2]
        assert param3.name == "param3"
        assert param3.is_required == False
    
    def test_extract_class_contract(self):
        """Test extraction of class contracts."""
        
        class TestClass:
            """Test class docstring."""
            
            def public_method(self, param1: str):
                """Public method."""
                pass
            
            def _private_method(self, param1: str):
                """Private method."""
                pass
        
        contract = SignatureAnalyzer.extract_class_contract(TestClass)
        
        assert contract.interface_name == "TestClass"
        assert contract.class_docstring == "Test class docstring."
        
        # Should only include public methods
        method_names = {method.method_name for method in contract.methods}
        assert "public_method" in method_names
        assert "_private_method" not in method_names


class TestContractRegistry:
    """Test contract registry functionality."""
    
    def test_factory_contract_registry_initialization(self):
        """Test factory contract registry initializes correctly."""
        
        registry = FactoryContractRegistry()
        
        # Should have core contracts registered
        assert "UserExecutionContext" in registry.validator.known_contracts
        assert "WebSocketManagerFactory" in registry.validator.known_contracts
    
    def test_validate_factory_pattern(self):
        """Test factory pattern validation through registry."""
        
        class TestFactory:
            def create_manager(self, user_context):
                pass
        
        registry = FactoryContractRegistry()
        result = registry.validate_factory_pattern(TestFactory)
        
        # Should return a validation result
        assert isinstance(result, ValidationResult)
        assert result.interface_name == "TestFactory"


def test_integration_validation_script():
    """Integration test for the validation script."""
    import subprocess
    import sys
    from pathlib import Path
    
    # Test the validation script can run
    script_path = Path(__file__).parent.parent.parent / "scripts" / "validate_factory_contracts.py"
    
    if script_path.exists():
        try:
            result = subprocess.run([
                sys.executable, str(script_path), "--specific-tests"
            ], capture_output=True, text=True, timeout=30)
            
            # Script should run without crashing
            assert result.returncode in [0, 1]  # Allow validation failures
            
            # Should produce output
            assert len(result.stdout) > 0 or len(result.stderr) > 0
            
        except subprocess.TimeoutExpired:
            pytest.fail("Validation script timed out")
        except Exception as e:
            pytest.fail(f"Failed to run validation script: {e}")
    else:
        pytest.skip("Validation script not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])