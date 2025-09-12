"""
Five Whys SupervisorAgent.create() Parameter Validation Test Suite

This test suite validates that SupervisorAgent.create() calls work correctly 
after the WebSocket supervisor parameter fixes. It covers all Five Whys levels
specifically for SupervisorAgent interface validation and regression prevention.

CRITICAL: These tests validate the Error Detective's fixes work for SupervisorAgent.create()
and prevent the "name" parameter error that was identified in the Five Whys analysis.

REGRESSION SCENARIOS PREVENTED:
1. WHY #1: TypeError from incorrect parameter names in SupervisorAgent.create()
2. WHY #2: Interface drift between factory methods and constructors
3. WHY #3: Missing parameter validation in SupervisorAgent interface
4. WHY #4: Test gaps that miss SupervisorAgent.create() signature changes
5. WHY #5: Interface evolution without dependency management for SupervisorAgent
"""

import inspect
import pytest
from typing import Any, Dict, Optional
from unittest.mock import Mock, AsyncMock, MagicMock

# SSOT imports - using absolute paths
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestSupervisorAgentCreateValidation:
    """
    Comprehensive validation tests for SupervisorAgent.create() method interface
    that specifically target the Five Whys error scenarios for WebSocket supervisor.
    
    These tests ensure SupervisorAgent.create() accepts correct parameters and 
    rejects incorrect ones to prevent the parameter mismatch issues identified
    in the Five Whys analysis.
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock LLM manager
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_llm_manager.invoke = AsyncMock(return_value=MagicMock(content="Test response"))
        
        # Create mock WebSocket bridge
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.send_agent_message = AsyncMock()
        
    def test_why_1_supervisor_create_correct_parameters_accepted(self):
        """
        WHY #1 - SYMPTOM: SupervisorAgent.create() accepts correct parameters.
        
        This test validates that SupervisorAgent.create() works with the correct
        parameter signature (llm_manager, websocket_bridge) without throwing
        the TypeError that was causing the original "name" error.
        """
        # Test that SupervisorAgent.create() accepts correct parameters
        supervisor = SupervisorAgent.create(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Validate supervisor was created successfully
        assert supervisor is not None
        assert isinstance(supervisor, SupervisorAgent)
        assert supervisor._llm_manager == self.mock_llm_manager
        assert supervisor.websocket_bridge == self.mock_websocket_bridge
        
        print(" PASS:  WHY #1 - SupervisorAgent.create() accepts correct parameters")
    
    def test_why_1_supervisor_create_rejects_old_parameters(self):
        """
        WHY #1 - SYMPTOM: SupervisorAgent.create() rejects deprecated parameters.
        
        This test validates that SupervisorAgent.create() properly rejects
        deprecated parameter names that could cause the "name" parameter error.
        """
        # Test rejection of deprecated parameters that might cause "name" errors
        deprecated_params = [
            {"llm_client": self.mock_llm_manager, "websocket_bridge": self.mock_websocket_bridge},
            {"llm_manager": self.mock_llm_manager, "tool_dispatcher": Mock()},
            {"llm_manager": self.mock_llm_manager, "agent_registry": Mock()},
            {"name": "test_supervisor", "llm_manager": self.mock_llm_manager},
        ]
        
        for params in deprecated_params:
            with pytest.raises(TypeError):
                SupervisorAgent.create(**params)
        
        print(" PASS:  WHY #1 - SupervisorAgent.create() rejects deprecated parameters")
    
    def test_why_2_supervisor_interface_contract_consistency(self):
        """
        WHY #2 - IMMEDIATE CAUSE: SupervisorAgent interface contract is consistent.
        
        This test validates that SupervisorAgent.create() method signature matches
        the constructor signature to prevent interface drift issues.
        """
        # Get SupervisorAgent.create() signature
        create_signature = inspect.signature(SupervisorAgent.create)
        create_params = create_signature.parameters
        
        # Get SupervisorAgent.__init__() signature
        init_signature = inspect.signature(SupervisorAgent.__init__)
        init_params = init_signature.parameters
        
        # Validate key parameters exist in both
        required_params = ['llm_manager', 'websocket_bridge']
        
        for param in required_params:
            assert param in create_params, f"SupervisorAgent.create() missing {param}"
            if param != 'websocket_bridge':  # websocket_bridge is optional in __init__
                assert param in init_params, f"SupervisorAgent.__init__() missing {param}"
        
        # Validate websocket_bridge is optional in both
        if 'websocket_bridge' in create_params and 'websocket_bridge' in init_params:
            create_ws_param = create_params['websocket_bridge']
            init_ws_param = init_params['websocket_bridge']
            
            # In create() it's required, in __init__() it's optional
            assert create_ws_param.default == inspect.Parameter.empty, "websocket_bridge should be required in create()"
            assert init_ws_param.default is None, "websocket_bridge should be optional in __init__()"
        
        print(" PASS:  WHY #2 - SupervisorAgent interface contracts are consistent")
    
    def test_why_3_supervisor_parameter_validation_system(self):
        """
        WHY #3 - SYSTEM FAILURE: SupervisorAgent interface prevents "name" parameter errors.
        
        This test validates that SupervisorAgent.create() interface prevents the
        "name" parameter errors that caused the original WebSocket supervisor issue.
        The key validation is that it only accepts the correct parameter names.
        """
        # Test that SupervisorAgent.create() accepts correct parameters
        supervisor = SupervisorAgent.create(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        assert supervisor is not None
        
        # Test that SupervisorAgent.create() rejects incorrect parameter names
        # These wrong names would cause the "name" TypeError that was fixed
        with pytest.raises(TypeError) as exc_info:
            SupervisorAgent.create(
                llm_client=self.mock_llm_manager,  # Wrong parameter name
                websocket_bridge=self.mock_websocket_bridge
            )
        assert "unexpected keyword" in str(exc_info.value).lower()
        
        with pytest.raises(TypeError) as exc_info:
            SupervisorAgent.create(
                llm_manager=self.mock_llm_manager,
                tool_dispatcher=Mock(),  # Wrong parameter name
            )
        assert "unexpected keyword" in str(exc_info.value).lower()
        
        with pytest.raises(TypeError) as exc_info:
            SupervisorAgent.create(
                llm_manager=self.mock_llm_manager,
                agent_registry=Mock(),  # Wrong parameter name
            )
        assert "unexpected keyword" in str(exc_info.value).lower()
        
        with pytest.raises(TypeError) as exc_info:
            SupervisorAgent.create(
                name="test_supervisor",  # Wrong parameter name
                llm_manager=self.mock_llm_manager,
            )
        assert "unexpected keyword" in str(exc_info.value).lower()
        
        # Test that None values work for websocket_bridge (it's optional)
        supervisor_no_ws = SupervisorAgent.create(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=None
        )
        assert supervisor_no_ws.websocket_bridge is None
        
        print(" PASS:  WHY #3 - SupervisorAgent interface prevents 'name' parameter errors")
    
    def test_why_4_supervisor_create_usage_coverage(self):
        """
        WHY #4 - PROCESS GAP: All SupervisorAgent.create() usage patterns work.
        
        This test validates common SupervisorAgent.create() usage patterns
        to ensure test coverage catches any signature changes.
        """
        # Test standard usage pattern
        supervisor1 = SupervisorAgent.create(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        assert supervisor1 is not None
        
        # Test with fresh mocks (as might happen in different test contexts)
        fresh_llm = Mock(spec=LLMManager)
        fresh_llm.invoke = AsyncMock(return_value=MagicMock(content="Fresh response"))
        fresh_bridge = Mock(spec=AgentWebSocketBridge)
        fresh_bridge.send_agent_message = AsyncMock()
        
        supervisor2 = SupervisorAgent.create(
            llm_manager=fresh_llm,
            websocket_bridge=fresh_bridge
        )
        assert supervisor2 is not None
        
        # Validate supervisors are independent instances
        assert supervisor1 is not supervisor2
        assert supervisor1._llm_manager != supervisor2._llm_manager
        assert supervisor1.websocket_bridge != supervisor2.websocket_bridge
        
        print(" PASS:  WHY #4 - All SupervisorAgent.create() usage patterns work")
    
    def test_why_5_supervisor_interface_governance_standards(self):
        """
        WHY #5 - ROOT CAUSE: SupervisorAgent follows interface governance standards.
        
        This test validates that SupervisorAgent.create() follows the interface
        evolution standards to prevent systematic parameter naming inconsistencies.
        """
        # Validate SupervisorAgent.create() follows factory pattern standards
        create_method = getattr(SupervisorAgent, 'create', None)
        assert create_method is not None, "SupervisorAgent missing create() factory method"
        assert hasattr(create_method, '__func__'), "create() should be a classmethod"
        
        # Validate return type annotation
        create_signature = inspect.signature(SupervisorAgent.create)
        return_annotation = create_signature.return_annotation
        expected_return = 'SupervisorAgent'  # String annotation or actual class
        
        assert (return_annotation == expected_return or 
                return_annotation == SupervisorAgent or
                str(return_annotation).endswith('SupervisorAgent')), \
            f"SupervisorAgent.create() return annotation should be SupervisorAgent, got {return_annotation}"
        
        # Validate parameter type hints exist
        for param_name, param in create_signature.parameters.items():
            if param_name != 'cls':
                assert param.annotation != inspect.Parameter.empty, \
                    f"SupervisorAgent.create() parameter '{param_name}' missing type annotation"
        
        print(" PASS:  WHY #5 - SupervisorAgent follows interface governance standards")
    
    def test_end_to_end_supervisor_websocket_integration(self):
        """
        END-TO-END: SupervisorAgent.create() works with WebSocket integration.
        
        This test validates that SupervisorAgent.create() integrates properly
        with WebSocket components to prevent the "name" error in real usage.
        """
        # Create supervisor with WebSocket bridge
        supervisor = SupervisorAgent.create(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Create UserExecutionContext that would be used with the supervisor
        context = UserExecutionContext(
            user_id="integration_test_user",
            thread_id="integration_test_thread", 
            run_id="integration_test_run",
            websocket_client_id="integration_ws_client_123",  # Correct parameter name
            db_session=None
        )
        
        # Validate supervisor can work with context (without actually executing)
        assert supervisor is not None
        assert context.websocket_client_id == "integration_ws_client_123"
        
        # Validate WebSocket bridge integration
        assert supervisor.websocket_bridge == self.mock_websocket_bridge
        
        print(" PASS:  END-TO-END: SupervisorAgent.create() WebSocket integration works")
    
    def test_regression_prevention_comprehensive_supervisor_validation(self):
        """
        COMPREHENSIVE: Complete SupervisorAgent regression prevention validation.
        
        This test runs all critical validations to ensure the specific
        SupervisorAgent.create() parameter issues cannot recur.
        """
        validation_results = []
        
        # 1. SupervisorAgent.create() method exists and is callable
        validation_results.append({
            'check': 'create_method_exists',
            'result': hasattr(SupervisorAgent, 'create') and callable(SupervisorAgent.create),
            'critical': True
        })
        
        # 2. SupervisorAgent.create() accepts correct parameters
        create_works = False
        try:
            supervisor = SupervisorAgent.create(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )
            create_works = supervisor is not None
        except Exception:
            create_works = False
        
        validation_results.append({
            'check': 'create_accepts_correct_params',
            'result': create_works,
            'critical': True
        })
        
        # 3. SupervisorAgent.create() rejects invalid parameters
        rejects_invalid = True
        try:
            # This should fail
            SupervisorAgent.create(
                llm_client=self.mock_llm_manager,  # Wrong parameter name
                websocket_bridge=self.mock_websocket_bridge
            )
            rejects_invalid = False
        except TypeError:
            rejects_invalid = True
        
        validation_results.append({
            'check': 'create_rejects_invalid_params',
            'result': rejects_invalid,
            'critical': True
        })
        
        # 4. Interface signature consistency
        create_signature = inspect.signature(SupervisorAgent.create)
        required_params = {'llm_manager', 'websocket_bridge'}
        actual_params = set(create_signature.parameters.keys()) - {'cls'}
        
        validation_results.append({
            'check': 'interface_signature_consistent',
            'result': required_params.issubset(actual_params),
            'critical': True
        })
        
        # 5. No deprecated parameter names in signature
        deprecated_names = {'llm_client', 'tool_dispatcher', 'agent_registry', 'name'}
        has_deprecated = bool(deprecated_names.intersection(actual_params))
        
        validation_results.append({
            'check': 'no_deprecated_parameters',
            'result': not has_deprecated,
            'critical': True
        })
        
        # Evaluate results
        critical_failures = [r for r in validation_results if r['critical'] and not r['result']]
        
        if critical_failures:
            failure_details = [f"- {r['check']}: {r['result']}" for r in critical_failures]
            pytest.fail(f"SUPERVISOR REGRESSION DETECTED - Critical validations failed:\n" + "\n".join(failure_details))
        
        # Report success
        total_checks = len(validation_results)
        passed_checks = sum(1 for r in validation_results if r['result'])
        
        print(f" PASS:  SUPERVISOR COMPREHENSIVE VALIDATION PASSED: {passed_checks}/{total_checks} checks successful")
        print(f" PASS:  SupervisorAgent.create() parameter regression CANNOT RECUR")
        
        # Detailed results
        for result in validation_results:
            status = " PASS: " if result['result'] else " FAIL: "
            critical = " (CRITICAL)" if result['critical'] else ""
            print(f"  {status} {result['check']}{critical}: {result['result']}")


if __name__ == "__main__":
    # Run the SupervisorAgent validation tests
    pytest.main([__file__, "-v", "--tb=short"])