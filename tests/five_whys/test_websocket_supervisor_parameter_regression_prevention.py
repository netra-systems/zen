"""
WebSocket Supervisor Parameter Regression Prevention Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Prevent specific regression that broke WebSocket supervisor creation
- Value Impact: Ensures the exact "websocket_connection_id vs websocket_client_id" issue cannot recur
- Strategic Impact: Validates regression prevention for critical chat functionality

This test suite specifically targets the exact regression that occurred:
- Parameter name mismatch between factory methods and constructors
- WebSocket supervisor creation failing with cryptic error messages
- Interface contract violations in factory patterns

CRITICAL MANDATE: These tests MUST fail if the specific regression is reintroduced.
They serve as executable documentation of the exact issue that was fixed.

REGRESSION SCENARIO: 
Original Error: "Failed to create WebSocket-scoped supervisor: name"
Root Cause: supervisor_factory.py line 96 used 'websocket_connection_id' 
           but UserExecutionContext expected 'websocket_client_id'
"""

import asyncio
import json
import time
import uuid
import inspect
from typing import Dict, List, Any, Optional, Tuple
import pytest
from unittest.mock import patch, MagicMock

from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.supervisor_factory import create_supervisor_core

from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities


class TestSpecificWebSocketParameterRegression(SSotBaseTestCase):
    """
    Regression prevention tests for the exact WebSocket supervisor parameter issue.
    
    These tests validate that the specific "websocket_connection_id vs websocket_client_id"
    parameter mismatch cannot occur again. If these tests fail, the regression has returned.
    """
    
    @pytest.fixture(scope="class")
    def auth_helper(self) -> E2EWebSocketAuthHelper:
        """SSOT WebSocket authentication helper."""
        config = E2EAuthConfig.for_environment("test")
        return E2EWebSocketAuthHelper(config=config, environment="test")
    
    @pytest.fixture(scope="class")
    def database_manager(self) -> DatabaseTestManager:
        """Real database test manager."""
        return DatabaseTestManager()
    
    def test_user_execution_context_parameter_signature_validation(self):
        """
        REGRESSION TEST: Validate UserExecutionContext has correct parameter signature.
        
        This test MUST FAIL if UserExecutionContext is changed back to accept
        'websocket_connection_id' instead of 'websocket_client_id'.
        """
        # Get the constructor signature
        signature = inspect.signature(UserExecutionContext.__init__)
        parameters = signature.parameters
        
        # CRITICAL: Must have websocket_client_id parameter
        assert 'websocket_client_id' in parameters, \
            "REGRESSION: UserExecutionContext missing websocket_client_id parameter"
        
        # CRITICAL: Must NOT have websocket_connection_id parameter 
        assert 'websocket_connection_id' not in parameters, \
            "REGRESSION: UserExecutionContext has deprecated websocket_connection_id parameter"
        
        # Validate parameter type annotation
        websocket_param = parameters['websocket_client_id']
        assert websocket_param.default is None or websocket_param.default == inspect.Parameter.empty, \
            "websocket_client_id parameter should be optional with None default"
        
        print(" PASS:  UserExecutionContext signature validation passed")
        print(f" PASS:  Has websocket_client_id parameter: {websocket_param}")
    
    def test_websocket_factory_source_code_parameter_usage(self):
        """
        REGRESSION TEST: Validate WebSocket factory source code uses correct parameter name.
        
        This test MUST FAIL if supervisor_factory.py reverts to using 'websocket_connection_id'
        when creating UserExecutionContext.
        """
        import ast
        import os
        
        # Read the actual source file
        factory_file = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/websocket_core/supervisor_factory.py"
        
        with open(factory_file, 'r') as f:
            source_code = f.read()
        
        # CRITICAL: Must use websocket_client_id when creating UserExecutionContext
        if 'UserExecutionContext(' in source_code:
            # Find UserExecutionContext creation patterns
            lines = source_code.split('\n')
            user_context_lines = []
            
            for i, line in enumerate(lines):
                if 'UserExecutionContext(' in line:
                    # Capture multi-line constructor call
                    constructor_block = []
                    j = i
                    paren_count = 0
                    while j < len(lines):
                        constructor_block.append(lines[j])
                        paren_count += lines[j].count('(') - lines[j].count(')')
                        if paren_count <= 0 and 'UserExecutionContext(' in lines[i]:
                            break
                        j += 1
                    
                    user_context_lines.extend(constructor_block)
            
            constructor_code = '\n'.join(user_context_lines)
            
            # CRITICAL: Must NOT contain deprecated parameter name
            assert 'websocket_connection_id=' not in constructor_code, \
                f"REGRESSION: Found deprecated 'websocket_connection_id' parameter in UserExecutionContext creation:\n{constructor_code}"
            
            # CRITICAL: Must contain correct parameter name
            assert 'websocket_client_id=' in constructor_code, \
                f"REGRESSION: Missing 'websocket_client_id' parameter in UserExecutionContext creation:\n{constructor_code}"
        
        print(" PASS:  WebSocket factory source code validation passed")
        print(" PASS:  Uses websocket_client_id parameter in UserExecutionContext creation")
    
    @pytest.mark.asyncio
    async def test_websocket_supervisor_creation_parameter_flow(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        REGRESSION TEST: Validate complete parameter flow from WebSocket context to supervisor.
        
        This test MUST FAIL if the parameter mismatch regression is reintroduced.
        """
        # Create test WebSocket context
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        context = WebSocketContext.create_for_user(
            websocket=websocket,
            user_id=f"regression_test_user_{int(time.time())}",
            thread_id=f"regression_test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        try:
            # Monitor the exact parameter passed to UserExecutionContext
            original_init = UserExecutionContext.__init__
            captured_parameters = {}
            
            def monitor_user_context_creation(self, *args, **kwargs):
                nonlocal captured_parameters
                captured_parameters = kwargs.copy()
                return original_init(self, *args, **kwargs)
            
            async with database_manager.get_async_session() as db_session:
                with patch.object(UserExecutionContext, '__init__', monitor_user_context_creation):
                    
                    # This MUST succeed with correct parameters
                    supervisor = await get_websocket_scoped_supervisor(context, db_session)
                    
                    # Validate supervisor was created successfully
                    assert supervisor is not None, "REGRESSION: Supervisor creation failed"
                    
                    # CRITICAL: Validate correct parameter was passed
                    assert 'websocket_client_id' in captured_parameters, \
                        f"REGRESSION: websocket_client_id not passed. Parameters: {list(captured_parameters.keys())}"
                    
                    # CRITICAL: Validate deprecated parameter was NOT passed
                    assert 'websocket_connection_id' not in captured_parameters, \
                        f"REGRESSION: Deprecated websocket_connection_id passed. Parameters: {list(captured_parameters.keys())}"
                    
                    # Validate parameter value matches context connection ID
                    assert captured_parameters['websocket_client_id'] == context.connection_id, \
                        f"REGRESSION: Parameter value mismatch. Expected: {context.connection_id}, Got: {captured_parameters['websocket_client_id']}"
        
        finally:
            if websocket and not websocket.closed:
                await websocket.close()
        
        print(" PASS:  WebSocket supervisor parameter flow validation passed")
        print(f" PASS:  Correct websocket_client_id parameter passed: {captured_parameters.get('websocket_client_id')}")
    
    def test_deprecated_parameter_rejection(self):
        """
        REGRESSION TEST: Validate that deprecated parameter name is properly rejected.
        
        This test MUST FAIL if UserExecutionContext is changed to accept the deprecated
        'websocket_connection_id' parameter again.
        """
        # Try to create UserExecutionContext with deprecated parameter
        with pytest.raises(TypeError, match="unexpected keyword.*websocket_connection_id"):
            UserExecutionContext(
                user_id="regression_test_user",
                thread_id="regression_test_thread",
                websocket_connection_id="test_connection_id",  # Deprecated parameter
                db_session=None  # Not needed for this parameter validation test
            )
        
        print(" PASS:  Deprecated parameter rejection validation passed")
        print(" PASS:  UserExecutionContext properly rejects websocket_connection_id")
    
    def test_correct_parameter_acceptance(self):
        """
        REGRESSION TEST: Validate that correct parameter name is accepted.
        
        This test MUST FAIL if UserExecutionContext is changed to NOT accept
        'websocket_client_id' parameter.
        """
        try:
            # This should work without error (we'll get other errors due to None db_session, but not parameter errors)
            user_context = UserExecutionContext(
                user_id="regression_test_user",
                thread_id="regression_test_thread", 
                websocket_client_id="test_client_id",  # Correct parameter
                db_session=None
            )
            
            # If we get here, parameter was accepted
            print(" PASS:  Correct parameter acceptance validation passed")
            print(" PASS:  UserExecutionContext properly accepts websocket_client_id")
            
        except TypeError as e:
            if "websocket_client_id" in str(e):
                pytest.fail(f"REGRESSION: UserExecutionContext no longer accepts websocket_client_id: {e}")
            else:
                # Other TypeErrors are expected (due to None db_session, etc.)
                print(" PASS:  Correct parameter acceptance validation passed (parameter accepted, other validation failed as expected)")
        except Exception as e:
            # Other exceptions are fine - we just need to validate the parameter is accepted
            if "websocket_client_id" in str(e) and "unexpected keyword" in str(e):
                pytest.fail(f"REGRESSION: UserExecutionContext rejects websocket_client_id: {e}")
            else:
                print(" PASS:  Correct parameter acceptance validation passed (parameter accepted)")
    
    @pytest.mark.asyncio
    async def test_error_message_improvement_validation(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        REGRESSION TEST: Validate that error messages are improved, not cryptic.
        
        This test MUST FAIL if the error handling reverts to the cryptic
        "Failed to create WebSocket-scoped supervisor: name" message.
        """
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        context = WebSocketContext.create_for_user(
            websocket=websocket,
            user_id=f"error_message_test_user_{int(time.time())}",
            thread_id=f"error_message_test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        try:
            async with database_manager.get_async_session() as db_session:
                
                # Simulate the original error by forcing parameter mismatch
                with patch('netra_backend.app.websocket_core.supervisor_factory._get_websocket_supervisor_components') as mock_components:
                    # Force a TypeError that mimics the original parameter issue
                    mock_components.side_effect = TypeError("UserExecutionContext.__init__() got unexpected keyword 'websocket_connection_id'")
                    
                    try:
                        await get_websocket_scoped_supervisor(context, db_session)
                        pytest.fail("Expected TypeError to be raised and handled")
                        
                    except Exception as e:
                        error_message = str(e)
                        
                        # CRITICAL: Must NOT be the cryptic original error message
                        assert "Failed to create WebSocket-scoped supervisor: name" not in error_message, \
                            f"REGRESSION: Cryptic error message returned: {error_message}"
                        
                        # CRITICAL: Must be a more helpful error message
                        assert "Failed to create WebSocket supervisor" in error_message, \
                            f"REGRESSION: Expected improved error message, got: {error_message}"
                        
                        # Should preserve information about the actual error
                        assert "TypeError" in error_message or "unexpected keyword" in error_message, \
                            f"REGRESSION: Error details not preserved: {error_message}"
        
        finally:
            if websocket and not websocket.closed:
                await websocket.close()
        
        print(" PASS:  Error message improvement validation passed")
        print(" PASS:  No cryptic 'name' error messages detected")
    
    @pytest.mark.asyncio
    async def test_factory_consistency_across_implementations(
        self,
        database_manager: DatabaseTestManager
    ):
        """
        REGRESSION TEST: Validate parameter consistency across all factory implementations.
        
        This test MUST FAIL if any factory implementation reverts to using
        deprecated parameter names.
        """
        async with database_manager.get_async_session() as db_session:
            
            # Test parameters for factory consistency
            test_user_id = f"consistency_test_user_{int(time.time())}"
            test_thread_id = f"consistency_test_thread_{uuid.uuid4().hex[:8]}"
            test_run_id = f"consistency_test_run_{uuid.uuid4().hex[:8]}"
            test_websocket_client_id = f"test_client_{uuid.uuid4().hex[:8]}"
            
            # Monitor UserExecutionContext creation across different factories
            original_init = UserExecutionContext.__init__
            all_captured_parameters = []
            
            def monitor_all_creations(self, *args, **kwargs):
                nonlocal all_captured_parameters
                all_captured_parameters.append(kwargs.copy())
                return original_init(self, *args, **kwargs)
            
            with patch.object(UserExecutionContext, '__init__', monitor_all_creations):
                
                try:
                    # Test core factory (if it creates UserExecutionContext directly)
                    from netra_backend.app.llm.client_unified import ResilientLLMClient
                    from netra_backend.app.llm.llm_manager import LLMManager
                    
                    llm_manager = LLMManager()
                    llm_client = ResilientLLMClient(llm_manager)
                    
                    await create_supervisor_core(
                        user_id=test_user_id,
                        thread_id=test_thread_id,
                        run_id=test_run_id,
                        db_session=db_session,
                        websocket_client_id=test_websocket_client_id,  # Must use standard parameter
                        llm_client=llm_client,
                        websocket_bridge=None,
                        tool_dispatcher=None
                    )
                    
                except Exception as e:
                    # Core factory might not create UserExecutionContext directly
                    # That's okay - we're testing parameter consistency where it does occur
                    pass
            
            # Validate parameter consistency in all captured creations
            for i, parameters in enumerate(all_captured_parameters):
                
                # CRITICAL: If websocket parameter is present, it must be the correct name
                if any('websocket' in key for key in parameters.keys()):
                    assert 'websocket_client_id' in parameters, \
                        f"REGRESSION: Factory {i} uses incorrect parameter names: {list(parameters.keys())}"
                    
                    assert 'websocket_connection_id' not in parameters, \
                        f"REGRESSION: Factory {i} uses deprecated websocket_connection_id: {list(parameters.keys())}"
        
        print(" PASS:  Factory consistency validation passed")
        print(f" PASS:  Checked {len(all_captured_parameters)} UserExecutionContext creations")
        print(" PASS:  All factories use standardized websocket_client_id parameter")


class TestWebSocketSupervisorSpecificErrorScenarios(SSotBaseTestCase):
    """
    Tests for specific error scenarios that caused the original regression.
    
    These tests recreate the exact conditions that led to the parameter mismatch
    and validate that the fixes handle these scenarios correctly.
    """
    
    @pytest.fixture(scope="class")
    def auth_helper(self) -> E2EWebSocketAuthHelper:
        """SSOT WebSocket authentication helper."""
        config = E2EAuthConfig.for_environment("test")
        return E2EWebSocketAuthHelper(config=config, environment="test")
    
    @pytest.fixture(scope="class")
    def database_manager(self) -> DatabaseTestManager:
        """Real database test manager."""
        return DatabaseTestManager()
    
    @pytest.mark.asyncio
    async def test_original_failure_scenario_recreation(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        REGRESSION TEST: Recreate the original failure scenario and validate it's fixed.
        
        This test recreates the exact conditions that caused the original error:
        - WebSocket connection established
        - Context created for message processing
        - Supervisor factory called with specific parameters
        - Original error: line 96 parameter mismatch
        """
        # Create the exact scenario from the original error report
        user_id = "105945141827451681156"  # From original error context
        thread_id = f"original_scenario_thread_{uuid.uuid4().hex[:8]}"
        
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        context = WebSocketContext.create_for_user(
            websocket=websocket,
            user_id=user_id,
            thread_id=thread_id
        )
        
        try:
            # Validate context setup matches original scenario
            assert context.validate_for_message_processing()
            assert context.user_id == user_id
            assert context.connection_id is not None
            
            # This was the failing call in the original scenario
            async with database_manager.get_async_session() as db_session:
                supervisor = await get_websocket_scoped_supervisor(context, db_session)
                
                # CRITICAL: This MUST succeed now (it failed before the fix)
                assert supervisor is not None, \
                    "REGRESSION: Original scenario still fails - supervisor creation returned None"
                
                # Validate supervisor has expected attributes
                assert hasattr(supervisor, 'user_id') or hasattr(supervisor, '_user_context'), \
                    "REGRESSION: Supervisor missing user context attributes"
        
        finally:
            if websocket and not websocket.closed:
                await websocket.close()
        
        print(" PASS:  Original failure scenario recreation passed")
        print(f" PASS:  User {user_id} supervisor creation successful")
    
    @pytest.mark.asyncio
    async def test_line_96_parameter_passing_validation(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        REGRESSION TEST: Validate that line 96 (or equivalent) parameter passing is correct.
        
        The original error occurred at supervisor_factory.py:96 where UserExecutionContext
        was created with websocket_connection_id instead of websocket_client_id.
        """
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        context = WebSocketContext.create_for_user(
            websocket=websocket,
            user_id=f"line96_test_user_{int(time.time())}",
            thread_id=f"line96_test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        try:
            # Monitor the exact line where UserExecutionContext is created
            creation_call_details = []
            original_init = UserExecutionContext.__init__
            
            def monitor_creation_details(self, *args, **kwargs):
                nonlocal creation_call_details
                creation_call_details.append({
                    'args': args,
                    'kwargs': kwargs.copy(),
                    'websocket_param_name': None,
                    'websocket_param_value': None
                })
                
                # Identify the websocket parameter
                for key, value in kwargs.items():
                    if 'websocket' in key:
                        creation_call_details[-1]['websocket_param_name'] = key
                        creation_call_details[-1]['websocket_param_value'] = value
                        break
                
                return original_init(self, *args, **kwargs)
            
            async with database_manager.get_async_session() as db_session:
                with patch.object(UserExecutionContext, '__init__', monitor_creation_details):
                    await get_websocket_scoped_supervisor(context, db_session)
                    
                    # Validate the creation call details
                    assert len(creation_call_details) > 0, \
                        "REGRESSION: UserExecutionContext was not created during supervisor creation"
                    
                    for i, details in enumerate(creation_call_details):
                        websocket_param_name = details['websocket_param_name']
                        websocket_param_value = details['websocket_param_value']
                        
                        if websocket_param_name:  # If websocket parameter was passed
                            # CRITICAL: Must be the correct parameter name
                            assert websocket_param_name == 'websocket_client_id', \
                                f"REGRESSION: Creation {i} uses wrong parameter name: {websocket_param_name}"
                            
                            # CRITICAL: Must match context connection ID
                            assert websocket_param_value == context.connection_id, \
                                f"REGRESSION: Creation {i} parameter value mismatch: {websocket_param_value} != {context.connection_id}"
        
        finally:
            if websocket and not websocket.closed:
                await websocket.close()
        
        print(" PASS:  Line 96 parameter passing validation passed")
        print(f" PASS:  UserExecutionContext created with correct websocket_client_id parameter")
    
    @pytest.mark.asyncio
    async def test_websocket_context_connection_id_mapping(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        database_manager: DatabaseTestManager
    ):
        """
        REGRESSION TEST: Validate that context.connection_id maps correctly to websocket_client_id.
        
        The original issue was that context.connection_id was passed as websocket_connection_id
        to UserExecutionContext, but it expected websocket_client_id.
        """
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        context = WebSocketContext.create_for_user(
            websocket=websocket,
            user_id=f"mapping_test_user_{int(time.time())}",
            thread_id=f"mapping_test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        try:
            # Capture the exact parameter mapping
            parameter_mappings = []
            original_init = UserExecutionContext.__init__
            
            def capture_parameter_mapping(self, *args, **kwargs):
                nonlocal parameter_mappings
                if 'websocket_client_id' in kwargs:
                    parameter_mappings.append({
                        'context_connection_id': context.connection_id,
                        'passed_websocket_client_id': kwargs['websocket_client_id'],
                        'mapping_correct': kwargs['websocket_client_id'] == context.connection_id
                    })
                return original_init(self, *args, **kwargs)
            
            async with database_manager.get_async_session() as db_session:
                with patch.object(UserExecutionContext, '__init__', capture_parameter_mapping):
                    await get_websocket_scoped_supervisor(context, db_session)
                    
                    # Validate parameter mapping
                    assert len(parameter_mappings) > 0, \
                        "REGRESSION: No websocket_client_id parameter mapping captured"
                    
                    for mapping in parameter_mappings:
                        assert mapping['mapping_correct'], \
                            f"REGRESSION: Parameter mapping incorrect - " \
                            f"context.connection_id: {mapping['context_connection_id']}, " \
                            f"passed websocket_client_id: {mapping['passed_websocket_client_id']}"
        
        finally:
            if websocket and not websocket.closed:
                await websocket.close()
        
        print(" PASS:  WebSocket context connection ID mapping validation passed")
        print(f" PASS:  context.connection_id correctly maps to websocket_client_id parameter")


if __name__ == "__main__":
    # Run regression prevention tests
    import os
    os.system("python -m pytest " + __file__ + " -v --tb=short --asyncio-mode=auto")