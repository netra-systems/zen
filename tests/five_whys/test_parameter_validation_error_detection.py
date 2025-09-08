"""
Five Whys Parameter Validation Error Detection Test Suite

This test suite validates WHY #3 - Missing interface validation that allowed
parameter mismatches to reach runtime and cause the WebSocket supervisor "name" error.

CRITICAL: Tests validate Error Detective fixes for parameter validation that
catches interface violations early, before they cause execution failures.

WHY #3 - SYSTEM FAILURE: Missing interface validation
- Tests parameter validation catches wrong types early
- Tests parameter validation catches wrong names early  
- Tests parameter validation provides clear error messages
- Tests validation prevents silent failures and parameter name confusion
- Tests interface governance validation integration

This prevents parameter errors from reaching the WebSocket supervisor creation
stage where they would cause unclear "name" TypeErrors.
"""

import inspect
import pytest
from typing import Any, Dict, Optional, Union
from unittest.mock import Mock, AsyncMock, MagicMock

# SSOT imports for validation testing
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError


class TestParameterValidationErrorDetection:
    """
    Parameter validation error detection tests that specifically target WHY #3
    from the Five Whys analysis - missing validation that would catch parameter
    errors before they cause confusing runtime failures.
    """
    
    def setup_method(self):
        """Set up test fixtures for validation testing."""
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_llm_manager.invoke = AsyncMock(return_value=MagicMock(content="Test response"))
        
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.send_agent_message = AsyncMock()
    
    def test_why_3_supervisor_create_parameter_type_validation(self):
        """
        WHY #3 - MISSING VALIDATION: SupervisorAgent.create() validates parameter types early.
        
        This test ensures parameter type validation catches invalid types before
        they can cause confusing errors during WebSocket supervisor creation.
        """
        # Test invalid llm_manager type validation
        invalid_llm_types = [
            None,
            "invalid_string_llm", 
            123,
            [],
            {},
            MagicMock()  # Generic mock without proper spec
        ]
        
        for invalid_llm in invalid_llm_types:
            with pytest.raises((TypeError, ValueError, AttributeError)) as exc_info:
                SupervisorAgent.create(
                    llm_manager=invalid_llm,
                    websocket_bridge=self.mock_websocket_bridge
                )
            
            # Validate error message gives clear indication of the problem
            error_msg = str(exc_info.value).lower()
            assert any(term in error_msg for term in ['llm', 'manager', 'type', 'invalid']), \
                f"Error message should indicate LLM manager type issue: {exc_info.value}"
        
        # Test invalid websocket_bridge type validation
        invalid_bridge_types = [
            None,
            "invalid_string_bridge",
            456,
            [],
            {},
            MagicMock()  # Generic mock without proper spec
        ]
        
        for invalid_bridge in invalid_bridge_types:
            with pytest.raises((TypeError, ValueError, AttributeError)) as exc_info:
                SupervisorAgent.create(
                    llm_manager=self.mock_llm_manager,
                    websocket_bridge=invalid_bridge
                )
            
            # Validate error message indicates the validation failure
            error_msg = str(exc_info.value).lower()
            assert any(term in error_msg for term in ['websocket', 'bridge', 'type', 'invalid']), \
                f"Error message should indicate WebSocket bridge type issue: {exc_info.value}"
        
        print("✅ WHY #3 - SupervisorAgent.create() parameter type validation catches errors early")
    
    def test_why_3_user_execution_context_parameter_validation(self):
        """
        WHY #3 - MISSING VALIDATION: UserExecutionContext validates parameters comprehensively.
        
        This test ensures UserExecutionContext validation catches parameter
        issues that could cause the "name" error downstream.
        """
        # Test required parameter validation
        required_params = ['user_id', 'thread_id', 'run_id']
        
        for missing_param in required_params:
            base_params = {
                'user_id': 'test_user',
                'thread_id': 'test_thread', 
                'run_id': 'test_run',
                'websocket_client_id': 'test_ws_client',
                'db_session': None
            }
            
            # Remove the required parameter or set to invalid value
            invalid_values = [None, '', '   ', 123, [], {}]
            
            for invalid_value in invalid_values:
                test_params = base_params.copy()
                test_params[missing_param] = invalid_value
                
                with pytest.raises((InvalidContextError, TypeError, ValueError)) as exc_info:
                    UserExecutionContext(**test_params)
                
                # Validate error message indicates which parameter failed
                error_msg = str(exc_info.value).lower()
                assert missing_param.lower() in error_msg, \
                    f"Error message should mention {missing_param}: {exc_info.value}"
        
        print("✅ WHY #3 - UserExecutionContext parameter validation prevents invalid contexts")
    
    def test_why_3_websocket_parameter_name_validation(self):
        """
        WHY #3 - MISSING VALIDATION: WebSocket parameter name validation is strict.
        
        This test ensures that deprecated websocket parameter names are caught
        early with clear error messages, preventing the "name" error confusion.
        """
        # Test that deprecated websocket_connection_id is rejected clearly
        with pytest.raises(TypeError) as exc_info:
            UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread", 
                run_id="test_run",
                websocket_connection_id="deprecated_param_value",  # Deprecated name
                db_session=None
            )
        
        # Validate error message clearly indicates the parameter name issue
        error_msg = str(exc_info.value)
        assert "websocket_connection_id" in error_msg, \
            "Error should mention deprecated parameter name"
        assert "unexpected keyword" in error_msg.lower(), \
            "Error should indicate unexpected keyword argument"
        
        # Test that correct websocket_client_id is accepted
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run", 
            websocket_client_id="correct_param_value",  # Correct name
            db_session=None
        )
        
        assert context.websocket_client_id == "correct_param_value"
        
        print("✅ WHY #3 - WebSocket parameter name validation prevents deprecated usage")
    
    def test_why_3_factory_parameter_validation_integration(self):
        """
        WHY #3 - MISSING VALIDATION: Factory parameter validation integrates properly.
        
        This test validates that parameter validation works throughout the
        factory chain to prevent parameter issues in WebSocket supervisor creation.
        """
        # Test that SupervisorAgent creation validates parameters before use
        
        # Create supervisor with valid parameters
        supervisor = SupervisorAgent.create(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Validate supervisor initialization worked
        assert supervisor is not None
        assert supervisor._llm_manager == self.mock_llm_manager
        assert supervisor.websocket_bridge == self.mock_websocket_bridge
        
        # Test that supervisor components are properly validated
        assert hasattr(supervisor, '_llm_manager'), "Supervisor missing LLM manager component"
        assert hasattr(supervisor, 'websocket_bridge'), "Supervisor missing WebSocket bridge component"
        
        # Test factory method signature validation
        create_signature = inspect.signature(SupervisorAgent.create)
        required_create_params = ['llm_manager', 'websocket_bridge']
        
        for param_name in required_create_params:
            assert param_name in create_signature.parameters, \
                f"SupervisorAgent.create() missing required parameter: {param_name}"
        
        print("✅ WHY #3 - Factory parameter validation integration prevents cascading failures")
    
    def test_why_3_error_message_clarity_validation(self):
        """
        WHY #3 - MISSING VALIDATION: Error messages clearly indicate parameter issues.
        
        This test validates that when parameter validation fails, the error
        messages are clear enough to prevent the confusion that led to the "name" error.
        """
        # Test SupervisorAgent.create() error message clarity
        try:
            SupervisorAgent.create(
                invalid_param="should_fail",
                websocket_bridge=self.mock_websocket_bridge
            )
            pytest.fail("Should have raised TypeError for invalid parameter")
        except TypeError as e:
            error_msg = str(e).lower()
            assert "unexpected keyword" in error_msg or "invalid_param" in error_msg, \
                f"Error message should clearly indicate parameter issue: {e}"
        
        # Test UserExecutionContext error message clarity
        try:
            UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run",
                invalid_websocket_param="should_fail",  # Invalid parameter
                db_session=None
            )
            pytest.fail("Should have raised TypeError for invalid websocket parameter")
        except TypeError as e:
            error_msg = str(e).lower()
            assert "unexpected keyword" in error_msg or "invalid_websocket_param" in error_msg, \
                f"Error message should clearly indicate websocket parameter issue: {e}"
        
        # Test missing required parameter error clarity
        try:
            UserExecutionContext(
                user_id="test_user",
                # Missing thread_id - should fail clearly
                run_id="test_run",
                db_session=None
            )
            pytest.fail("Should have raised error for missing required parameter")
        except (TypeError, InvalidContextError) as e:
            error_msg = str(e).lower()
            assert "thread_id" in error_msg or "required" in error_msg, \
                f"Error message should indicate missing required parameter: {e}"
        
        print("✅ WHY #3 - Error messages provide clear indication of parameter validation failures")
    
    def test_why_3_validation_prevents_silent_failures(self):
        """
        WHY #3 - MISSING VALIDATION: Validation prevents silent parameter failures.
        
        This test ensures that parameter validation fails fast and loud,
        preventing silent failures that could lead to confusing downstream errors.
        """
        # Test that all parameter validation failures are explicit (not silent)
        
        validation_scenarios = [
            # SupervisorAgent.create() scenarios
            {
                'function': SupervisorAgent.create,
                'params': {'llm_manager': None, 'websocket_bridge': self.mock_websocket_bridge},
                'expected_error': (TypeError, ValueError, AttributeError),
                'description': 'SupervisorAgent.create() with None llm_manager'
            },
            {
                'function': SupervisorAgent.create,
                'params': {'llm_manager': self.mock_llm_manager, 'websocket_bridge': None},
                'expected_error': (TypeError, ValueError, AttributeError),
                'description': 'SupervisorAgent.create() with None websocket_bridge'
            },
            # UserExecutionContext scenarios  
            {
                'function': UserExecutionContext,
                'params': {'user_id': None, 'thread_id': 'test', 'run_id': 'test', 'db_session': None},
                'expected_error': (InvalidContextError, TypeError, ValueError),
                'description': 'UserExecutionContext with None user_id'
            },
            {
                'function': UserExecutionContext,
                'params': {'user_id': '', 'thread_id': 'test', 'run_id': 'test', 'db_session': None},
                'expected_error': (InvalidContextError, TypeError, ValueError),
                'description': 'UserExecutionContext with empty user_id'
            }
        ]
        
        for scenario in validation_scenarios:
            with pytest.raises(scenario['expected_error']) as exc_info:
                scenario['function'](**scenario['params'])
            
            # Validate that the error is explicit and not silent
            assert exc_info.value is not None, f"Error should not be None for: {scenario['description']}"
            error_msg = str(exc_info.value)
            assert len(error_msg) > 0, f"Error message should not be empty for: {scenario['description']}"
            
            print(f"  ✅ {scenario['description']}: {type(exc_info.value).__name__}: {error_msg[:100]}...")
        
        print("✅ WHY #3 - Validation prevents all silent parameter failures")
    
    def test_why_3_comprehensive_validation_integration(self):
        """
        WHY #3 - MISSING VALIDATION: Comprehensive validation integration prevents system failures.
        
        This test validates that the complete validation system integration
        prevents parameter issues from causing system-level failures like the "name" error.
        """
        validation_results = []
        
        # 1. SupervisorAgent.create() validation coverage
        supervisor_validation_works = True
        try:
            SupervisorAgent.create(llm_manager="invalid", websocket_bridge="invalid")
            supervisor_validation_works = False
        except (TypeError, ValueError, AttributeError):
            supervisor_validation_works = True
        
        validation_results.append({
            'check': 'supervisor_create_validation_active',
            'result': supervisor_validation_works,
            'critical': True
        })
        
        # 2. UserExecutionContext validation coverage
        context_validation_works = True
        try:
            UserExecutionContext(user_id=None, thread_id=None, run_id=None, db_session=None)
            context_validation_works = False
        except (InvalidContextError, TypeError, ValueError):
            context_validation_works = True
        
        validation_results.append({
            'check': 'user_context_validation_active',
            'result': context_validation_works,
            'critical': True
        })
        
        # 3. Parameter name validation coverage
        param_name_validation_works = True
        try:
            UserExecutionContext(
                user_id="test", thread_id="test", run_id="test",
                websocket_connection_id="deprecated",  # Should fail
                db_session=None
            )
            param_name_validation_works = False
        except TypeError:
            param_name_validation_works = True
        
        validation_results.append({
            'check': 'parameter_name_validation_active',
            'result': param_name_validation_works,
            'critical': True
        })
        
        # 4. Type validation coverage
        type_validation_works = True
        try:
            SupervisorAgent.create(llm_manager=123, websocket_bridge=456)
            type_validation_works = False
        except (TypeError, ValueError, AttributeError):
            type_validation_works = True
        
        validation_results.append({
            'check': 'type_validation_active',
            'result': type_validation_works,
            'critical': True
        })
        
        # Evaluate comprehensive validation results
        critical_failures = [r for r in validation_results if r['critical'] and not r['result']]
        
        if critical_failures:
            failure_details = [f"- {r['check']}: {r['result']}" for r in critical_failures]
            pytest.fail(f"VALIDATION SYSTEM FAILURES - Parameter issues may cause system failures:\n" + "\n".join(failure_details))
        
        print("✅ WHY #3 - Comprehensive validation integration prevents system-level parameter failures")
        
        # Report validation coverage
        for result in validation_results:
            status = "✅" if result['result'] else "❌"
            critical = " (CRITICAL)" if result['critical'] else ""
            print(f"  {status} {result['check']}{critical}: {result['result']}")


if __name__ == "__main__":
    # Run the parameter validation error detection tests
    pytest.main([__file__, "-v", "--tb=short"])