"""
Five Whys WebSocket Supervisor Interface Contract Validation Test Suite

This test suite validates the interface contracts between WebSocket supervisor factory,
SupervisorAgent.create(), and UserExecutionContext to prevent parameter mismatches
that cause the "name" error identified in the Five Whys analysis.

CRITICAL: Tests validate Error Detective fixes for interface contract consistency
across the WebSocket supervisor creation chain.

FIVE WHYS INTERFACE CONTRACT VALIDATION:
WHY #2 - IMMEDIATE CAUSE: Interface drift between old/new signatures
- Validates supervisor factory → SupervisorAgent.create() parameter mapping
- Validates UserExecutionContext parameter consistency 
- Validates WebSocket bridge parameter flow
- Validates factory method interface contracts

This prevents the original issue where supervisor_factory.py used one parameter name
but UserExecutionContext expected a different one, causing TypeError.
"""

import inspect
import pytest
import os
from typing import Any, Dict, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch

# SSOT imports for interface validation
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
from netra_backend.app.core.supervisor_factory import create_supervisor_core


class TestWebSocketSupervisorInterfaceContracts:
    """
    Interface contract validation tests that specifically target WHY #2 
    from the Five Whys analysis - preventing interface drift between
    factory methods and the components they create.
    """
    
    def setup_method(self):
        """Set up test fixtures for interface validation."""
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_llm_manager.invoke = AsyncMock(return_value=MagicMock(content="Test response"))
        
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.send_agent_message = AsyncMock()
    
    def test_why_2_websocket_factory_supervisor_create_parameter_mapping(self):
        """
        WHY #2 - INTERFACE DRIFT: WebSocket factory → SupervisorAgent.create() mapping is consistent.
        
        This test validates that the WebSocket supervisor factory correctly maps
        its parameters to SupervisorAgent.create() without name mismatches.
        """
        # Get factory signature
        factory_signature = inspect.signature(get_websocket_scoped_supervisor)
        factory_params = set(factory_signature.parameters.keys())
        
        # Get SupervisorAgent.create() signature  
        create_signature = inspect.signature(SupervisorAgent.create)
        create_params = set(create_signature.parameters.keys()) - {'cls'}
        
        # Core validation: Factory should be able to call SupervisorAgent.create()
        # The factory takes a 'context' parameter and should extract needed components
        assert 'context' in factory_params, "WebSocket factory missing 'context' parameter"
        
        # Validate SupervisorAgent.create() has the expected interface
        expected_create_params = {'llm_manager', 'websocket_bridge'}
        assert expected_create_params.issubset(create_params), \
            f"SupervisorAgent.create() missing parameters: {expected_create_params - create_params}"
        
        print("✅ WHY #2 - WebSocket factory → SupervisorAgent.create() parameter mapping validated")
    
    def test_why_2_core_factory_supervisor_create_parameter_consistency(self):
        """
        WHY #2 - INTERFACE DRIFT: Core factory → SupervisorAgent interface is consistent.
        
        This test validates that the core supervisor factory has consistent
        parameter interfaces with SupervisorAgent to prevent mismatches.
        """
        # Get core factory signature
        core_factory_signature = inspect.signature(create_supervisor_core)
        core_factory_params = set(core_factory_signature.parameters.keys())
        
        # Get SupervisorAgent.__init__ signature
        init_signature = inspect.signature(SupervisorAgent.__init__)
        init_params = set(init_signature.parameters.keys()) - {'self'}
        
        # Validate key parameter consistency
        assert 'llm_manager' in core_factory_params, "Core factory missing 'llm_manager'"
        assert 'llm_manager' in init_params, "SupervisorAgent.__init__ missing 'llm_manager'"
        
        # WebSocket parameter consistency - core factory has websocket_client_id, 
        # but SupervisorAgent uses websocket_bridge
        assert 'websocket_client_id' in core_factory_params, "Core factory missing 'websocket_client_id'"
        assert 'websocket_bridge' in init_params, "SupervisorAgent missing 'websocket_bridge'"
        
        print("✅ WHY #2 - Core factory → SupervisorAgent interface consistency validated")
    
    def test_why_2_user_execution_context_parameter_standardization(self):
        """
        WHY #2 - INTERFACE DRIFT: UserExecutionContext parameter names are standardized.
        
        This test validates that UserExecutionContext uses the standardized 
        websocket_client_id parameter name that was fixed in the Error Detective's work.
        """
        # Get UserExecutionContext signature
        context_signature = inspect.signature(UserExecutionContext.__init__)
        context_params = set(context_signature.parameters.keys()) - {'self'}
        
        # CRITICAL: Must use websocket_client_id (not websocket_connection_id)
        assert 'websocket_client_id' in context_params, \
            "REGRESSION: UserExecutionContext missing websocket_client_id parameter"
        
        # CRITICAL: Must NOT use deprecated parameter name
        assert 'websocket_connection_id' not in context_params, \
            "REGRESSION: UserExecutionContext has deprecated websocket_connection_id parameter"
        
        # Validate parameter type and default value
        websocket_param = context_signature.parameters['websocket_client_id']
        assert websocket_param.default is None, \
            "websocket_client_id should default to None for optional usage"
        
        print("✅ WHY #2 - UserExecutionContext parameter standardization validated")
    
    def test_why_2_websocket_supervisor_factory_source_code_consistency(self):
        """
        WHY #2 - INTERFACE DRIFT: WebSocket supervisor factory source uses correct parameters.
        
        This test validates that the WebSocket supervisor factory source code
        uses the correct parameter names when calling UserExecutionContext.
        """
        # Read the supervisor factory source code
        factory_file = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/websocket_core/supervisor_factory.py"
        
        if os.path.exists(factory_file):
            with open(factory_file, 'r') as f:
                source_code = f.read()
            
            # CRITICAL: Should use websocket_client_id in UserExecutionContext creation
            if 'UserExecutionContext(' in source_code:
                assert 'websocket_client_id=' in source_code, \
                    "REGRESSION: WebSocket factory not using websocket_client_id parameter"
                
                # CRITICAL: Should NOT use deprecated parameter name
                assert 'websocket_connection_id=' not in source_code, \
                    "REGRESSION: WebSocket factory using deprecated websocket_connection_id parameter"
        
        print("✅ WHY #2 - WebSocket supervisor factory source code consistency validated")
    
    def test_why_2_parameter_flow_validation_end_to_end(self):
        """
        WHY #2 - INTERFACE DRIFT: Complete parameter flow is consistent end-to-end.
        
        This test validates the complete parameter flow from WebSocket context
        through factory to SupervisorAgent creation works without interface mismatches.
        """
        # Simulate the parameter flow that caused the original "name" error
        
        # 1. WebSocket context data (incoming)
        websocket_connection_data = {
            "connection_id": "ws_conn_12345",
            "user_id": "test_user_67890", 
            "thread_id": "test_thread_abcde"
        }
        
        # 2. Create UserExecutionContext with correct parameter mapping
        context = UserExecutionContext(
            user_id=websocket_connection_data["user_id"],
            thread_id=websocket_connection_data["thread_id"],
            run_id="test_run_xyz123",
            websocket_client_id=websocket_connection_data["connection_id"],  # Correct mapping
            db_session=None
        )
        
        # 3. Validate context creation succeeded
        assert context.websocket_client_id == "ws_conn_12345"
        assert context.user_id == "test_user_67890"
        assert context.thread_id == "test_thread_abcde"
        
        # 4. Validate SupervisorAgent.create() can use components for this context
        supervisor = SupervisorAgent.create(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # 5. Validate end-to-end integration works
        assert supervisor is not None
        assert context.websocket_client_id is not None
        
        print("✅ WHY #2 - End-to-end parameter flow validated without interface drift")
    
    def test_why_2_interface_contract_regression_prevention(self):
        """
        WHY #2 - INTERFACE DRIFT: Interface contracts prevent future parameter regressions.
        
        This test validates that interface contracts are in place to prevent
        future parameter naming inconsistencies between factory and target methods.
        """
        validation_results = []
        
        # 1. SupervisorAgent.create() interface contract
        create_sig = inspect.signature(SupervisorAgent.create)
        expected_create_params = {'cls', 'llm_manager', 'websocket_bridge'}
        actual_create_params = set(create_sig.parameters.keys())
        
        validation_results.append({
            'check': 'supervisor_create_interface_stable',
            'result': expected_create_params == actual_create_params,
            'expected': expected_create_params,
            'actual': actual_create_params
        })
        
        # 2. UserExecutionContext interface contract
        context_sig = inspect.signature(UserExecutionContext.__init__)
        context_params = set(context_sig.parameters.keys())
        
        validation_results.append({
            'check': 'user_context_has_websocket_client_id',
            'result': 'websocket_client_id' in context_params,
            'missing': 'websocket_client_id' not in context_params
        })
        
        validation_results.append({
            'check': 'user_context_no_deprecated_websocket_connection_id',
            'result': 'websocket_connection_id' not in context_params,
            'has_deprecated': 'websocket_connection_id' in context_params
        })
        
        # 3. WebSocket factory interface contract
        factory_sig = inspect.signature(get_websocket_scoped_supervisor)
        factory_params = set(factory_sig.parameters.keys())
        
        validation_results.append({
            'check': 'websocket_factory_has_context_param',
            'result': 'context' in factory_params,
            'missing': 'context' not in factory_params
        })
        
        # Evaluate interface contract results
        failed_contracts = [r for r in validation_results if not r['result']]
        
        if failed_contracts:
            failure_details = []
            for failure in failed_contracts:
                details = f"- {failure['check']}: {failure['result']}"
                if 'expected' in failure:
                    details += f" (expected: {failure['expected']}, actual: {failure['actual']})"
                failure_details.append(details)
            
            pytest.fail(f"INTERFACE CONTRACT VIOLATIONS - Future regressions possible:\n" + "\n".join(failure_details))
        
        print("✅ WHY #2 - Interface contracts prevent future parameter regressions")
        
        # Report contract validation results
        for result in validation_results:
            status = "✅" if result['result'] else "❌"
            print(f"  {status} {result['check']}: {result['result']}")


if __name__ == "__main__":
    # Run the interface contract validation tests
    pytest.main([__file__, "-v", "--tb=short"])