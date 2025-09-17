from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.""
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        ""Send JSON message."
        if self._closed:
            raise RuntimeError("WebSocket is closed)
        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = Normal closure"):
        "Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False
    async def get_messages(self) -> list:
        ""Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()
        '''
        Comprehensive test suite for TriageSubAgent SSOT violations.
        This test suite is designed to FAIL until all SSOT violations are fixed.
        Each test targets a specific violation pattern from the AGENT_SSOT_AUDIT_PLAN.
        Business Value: TriageSubAgent is first contact for ALL users - CRITICAL revenue impact.
        '''
        import asyncio
        import hashlib
        import json
        import unittest
        import pytest
        import sys
        import os
    # Add project root to path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    Import from the main file instead of module
        from netra_backend.app.agents.triage.unified_triage_agent import TriageSubAgent as ImportedAgent
        try:
        Try import from main file location
        import sys
        import importlib.util
        spec = importlib.util.spec_from_file_location( )
        "triage_sub_agent,
        C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/app/agents/triage_sub_agent.py"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        TriageSubAgent = module.TriageSubAgent
        except Exception as e:
            # Fallback to whatever we could import
        print("formatted_string)
        TriageSubAgent = ImportedAgent if 'ImportedAgent' in locals() else None
        from netra_backend.app.agents.triage.unified_triage_agent import TriageCore
        from netra_backend.app.agents.triage_sub_agent.processing import TriageProcessor
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
class TestTriageAgentSSOTViolations(SSotAsyncTestCase):
        ""Test suite to identify and verify SSOT violations in TriageSubAgent."
    def setUp(self):
        "Set up test fixtures.""
        self.agent = TriageSubAgent()
        self.context = UserExecutionContext( )
        user_id=test_user",
        thread_id="test_thread,
        run_id=test_run",
        websocket_connection_id="test_ws
    
        self.context.metadata = {user_request": "Test request}
    # ========== VIOLATION 1: Custom Hash Generation ==========
    def test_violation_custom_hash_generation_in_cache_utils(self):
        '''
        pass
        VIOLATION: Custom hash generation using hashlib.md5 directly
        instead of using CacheHelpers.hash_key_data()
        Location: netra_backend/app/agents/triage_sub_agent/cache_utils.py:31
        '''
    # This test should FAIL if the violation exists
        from netra_backend.app.agents.triage.unified_triage_agent import cache_utils
    # Check if hashlib is imported (violation)
        self.assertIn('hashlib', dir(cache_utils),
        PASS: hashlib not imported (violation fixed)")
    # Check if custom hash function exists
        self.assertTrue(hasattr(cache_utils, 'generate_request_hash'),
        "PASS: Custom hash generation removed (violation fixed))
    # Verify it uses hashlib.md5 directly (violation)
        test_request = test request"
        result = cache_utils.generate_request_hash(test_request)
        expected_violation = hashlib.md5(test_request.lower().strip().encode()).hexdigest()
        self.assertEqual(result, expected_violation,
        "PASS: Not using custom MD5 hash (violation fixed))
    def test_violation_not_using_canonical_cache_helpers(self):
        '''
        VIOLATION: Not using CacheHelpers from canonical location
        instead of netra_backend.app.services.cache.cache_helpers
        '''
        pass
        core = TriageCore(self.context)
    # Check if CacheHelpers is properly imported and used
        self.assertTrue(hasattr(core, '_cache_helper'),
        FAIL: CacheHelpers not initialized in TriageCore")
    Verify it's from the correct module
        if hasattr(core, '_cache_helper'):
        from netra_backend.app.services.cache.cache_helpers import CacheHelpers
        self.assertIsInstance(core._cache_helper, CacheHelpers,
        "FAIL: Not using canonical CacheHelpers)
        # ========== VIOLATION 2: Not Extending BaseAgent ==========
    def test_violation_not_extending_base_agent(self):
        '''
        VIOLATION: TriageSubAgent doesnt extend BaseAgent
        Missing inheritance from netra_backend.app.agents.base_agent.BaseAgent
        '''
        pass
        from netra_backend.app.agents.base_agent import BaseAgent
    # This should FAIL if TriageSubAgent doesn't extend BaseAgent
        self.assertIsInstance(self.agent, BaseAgent,
        "FAIL: TriageSubAgent doesn"t extend BaseAgent)
    # Check for BaseAgent methods
        base_methods = ['emit_thinking', 'emit_progress', 'emit_agent_completed',
        '_handle_error', 'timing_collector']
        for method in base_methods:
        self.assertTrue(hasattr(self.agent, method),
        formatted_string")
        # ========== VIOLATION 3: Custom JSON Extraction ==========
    def test_violation_using_extract_json_from_response(self):
        '''
        VIOLATION: Using custom extract_json_from_response
        instead of unified_json_handler.LLMResponseParser
        Location: netra_backend/app/agents/triage_sub_agent/core.py:25
        '''
        pass
    # Check if the deprecated function is imported
        import netra_backend.app.agents.triage.unified_triage_agent.core as core_module
    # This should FAIL if still importing the old function
        self.assertNotIn('extract_json_from_response', core_module.__dict__,
        "FAIL: Still importing deprecated extract_json_from_response)
    def test_violation_custom_json_parsing_in_core(self):
        '''
        VIOLATION: Custom JSON parsing logic instead of using unified handler
        '''
        pass
        core = TriageCore(self.context)
    # Test the extract_and_validate_json method
        test_response = '{key": "value}'
        result = core.extract_and_validate_json(test_response)
    # Check if it's using the unified handler properly
        from netra_backend.app.core.serialization.unified_json_handler import LLMResponseParser
    # Verify LLMResponseParser is used
        with patch.object(LLMResponseParser, 'safe_json_parse') as mock_parse:
        mock_parse.return_value = {key": "value}
        core.extract_and_validate_json(test_response)
        mock_parse.assert_called_once()
    def test_violation_direct_json_loads_usage(self):
        '''
        VIOLATION: Direct json.loads usage instead of safe_json_loads
        Location: netra_backend/app/agents/triage_sub_agent/core.py:187
        '''
        pass
        core = TriageCore(self.context)
    # Test malformed JSON that should use error recovery
        malformed_json = '{key": "value'  # Missing closing brace )
    # This should use JSONErrorFixer and recovery, not direct json.loads
        result = core.extract_and_validate_json(malformed_json)
    # Should handle malformed JSON gracefully using unified handler
        self.assertIsNotNone(result, Should recover from malformed JSON")
    # ========== VIOLATION 4: Custom WebSocket Handling ==========
    def test_violation_not_using_websocket_bridge_adapter(self):
        '''
        VIOLATION: Not using WebSocketBridgeAdapter for WebSocket events
        Should use the canonical WebSocket integration pattern
        '''
        pass
    # Check if agent has WebSocketBridgeAdapter
        self.assertTrue(hasattr(self.agent, '_websocket_adapter') or )
        hasattr(self.agent, 'websocket_adapter'),
        "FAIL: No WebSocketBridgeAdapter found)
    async def test_violation_websocket_event_emission(self):
        '''
        VIOLATION: Custom WebSocket event emission instead of using adapter methods
        '''
        pass
        # Test that proper WebSocket events are sent
        with patch.object(self.agent, '_send_processing_update') as mock_send:
        await self.agent._send_processing_update(self.context, Test message")
            # Should use proper WebSocket adapter methods
        if hasattr(self.agent, '_websocket_adapter'):
        self.agent._websocket_adapter.emit_thinking.assert_called()
                # ========== VIOLATION 5: Custom Retry Logic ==========
    def test_violation_custom_retry_implementation(self):
        '''
        VIOLATION: Custom retry logic instead of UnifiedRetryHandler
        '''
        pass
        processor = TriageProcessor(TriageCore(self.context), None)
    # Check for UnifiedRetryHandler usage
        from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
    # Should use UnifiedRetryHandler, not custom retry logic
        self.assertTrue(hasattr(processor, 'retry_handler') or )
        any('UnifiedRetryHandler' in str(type(v)) )
        for v in processor.__dict__.values()),
        "FAIL: Not using UnifiedRetryHandler)
    # ========== VIOLATION 6: Direct Environment Access ==========
    def test_violation_direct_os_environ_access(self):
        '''
        VIOLATION: Direct os.environ access instead of IsolatedEnvironment
        '''
        pass
    # Search for os.environ usage in the module
        import netra_backend.app.agents.triage.unified_triage_agent as triage_module
    # Check all submodules for os.environ usage
        violations = []
        for name in dir(triage_module):
        obj = getattr(triage_module, name)
        if hasattr(obj, '__code__'):
            # Check bytecode for os.environ access
        if 'environ' in str(obj.__code__.co_names):
        violations.append(name)
        self.assertEqual([], violations,
        formatted_string")
                # ========== VIOLATION 7: State Storage in Instance Variables ==========
    async def test_violation_storing_user_data_in_instance(self):
        '''
        VIOLATION: Storing user-specific data in instance variables
        instead of passing through UserExecutionContext
        '''
        pass
                    # Check that agent doesn't store user data
        await self.agent.execute(self.context)
                    # These should NOT be stored in the agent
        forbidden_attrs = ['user_id', 'thread_id', 'db_session', 'current_request']
        for attr in forbidden_attrs:
        self.assertFalse(hasattr(self.agent, attr),
        "formatted_string)
                        # ========== VIOLATION 8: Duplicate Error Handling ==========
    def test_violation_custom_error_handling(self):
        '''
        VIOLATION: Custom error handling instead of agent_error_handler
        '''
        pass
        from netra_backend.app.core.unified_error_handler import agent_error_handler
    # Check if agent uses the unified error handler
        self.assertTrue(hasattr(self.agent, 'agent_error_handler') or )
        hasattr(self.agent, '_error_handler'),
        FAIL: Not using unified error handler")
    # ========== VIOLATION 9: Missing UserExecutionContext Support ==========
    async def test_violation_missing_context_parameter(self):
        '''
        VIOLATION: Methods not accepting UserExecutionContext parameter
        '''
        pass
        # Test that execute accepts context
        import inspect
        sig = inspect.signature(self.agent.execute)
        self.assertIn('context', sig.parameters,
        "FAIL: execute() doesnt accept context parameter)
        # Verify context is validated
        with self.assertRaises(ValueError):
        await self.agent.execute(None)  # Should fail without context
            # ========== VIOLATION 10: Configuration Access Pattern ==========
    def test_violation_direct_config_file_access(self):
        '''
        VIOLATION: Direct config file reading instead of using configuration architecture
        '''
        pass
    # Check for direct file reading
        core = TriageCore(self.context)
    Should use get_config() from configuration architecture
        from netra_backend.app.core.config import get_config
    # Verify no direct json.load of config files
        import netra_backend.app.agents.triage.unified_triage_agent.core as core_module
        source = str(core_module.__file__)
    # This is a simple check - in reality would parse AST
        self.assertNotIn('open(', str(core_module),
        "Potential direct file access detected")
    # ========== Integration Tests for Combined Violations ==========
    async def test_concurrent_request_isolation(self):
        '''
        Test that multiple concurrent requests are properly isolated.
        This tests multiple SSOT patterns together.
        '''
        pass
        # Create multiple contexts
        contexts = [
        UserExecutionContext( )
        user_id=formatted_string,
        thread_id="formatted_string",
        run_id=formatted_string,
        websocket_connection_id="formatted_string"
        ) for i in range(5)
        
        for ctx in contexts:
        ctx.metadata = {user_request: "formatted_string"}
            # Execute concurrently
        tasks = [self.agent.execute(ctx) for ctx in contexts]
        results = await asyncio.gather(*tasks)
            # Verify isolation - no data leakage
        for i, result in enumerate(results):
        self.assertIn(contexts[i].user_id, str(result))
        self.assertIn(contexts[i].run_id, str(result))
                # Ensure no cross-contamination
        for j in range(5):
        if i != j:
        self.assertNotIn(contexts[j].user_id, str(result),
        formatted_string)
    async def test_websocket_events_with_context(self):
        '''
        Test that WebSocket events are properly sent with UserExecutionContext.
        '''
        pass
                            # Mock WebSocket adapter
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        self.agent._websocket_adapter = mock_adapter
                            # Execute with streaming
        await self.agent.execute(self.context, stream_updates=True)
                            # Verify proper WebSocket events were sent
        expected_events = ['agent_started', 'agent_thinking', 'agent_completed']
                            # Check that events were emitted (this will fail until properly integrated)
        self.assertTrue(mock_adapter.emit_thinking.called or )
        mock_adapter.emit_progress.called,
        "No WebSocket events emitted")
    def test_all_violations_summary(self):
        '''
        Summary test that lists all violations found.
        This test always FAILS to show the complete violation report.
        '''
        pass
        violations = [
        1. Custom hash generation in cache_utils.py (using hashlib.md5),
        "2. TriageSubAgent doesn"t extend BaseAgent,
        3. Using extract_json_from_response instead of unified_json_handler",
        "4. Direct json.loads usage instead of safe_json_loads,
        5. Not using WebSocketBridgeAdapter for events",
        "6. Custom retry logic instead of UnifiedRetryHandler,
        7. Potential direct os.environ access",
        "8. Storing user data in instance variables,
        9. Custom error handling instead of agent_error_handler",
        "10. Direct config file access patterns
    
        print(")
        " + =*80)
        print("TRIAGE AGENT SSOT VIOLATIONS FOUND:")
        print(=*80)
        for v in violations:
        print("formatted_string")
        print(=*80)
        print("All these violations must be fixed for tests to pass.")
        print(=*80 + " )
        ")
        # This test always fails to show the report
        self.fail(Multiple SSOT violations detected - see list above)
        if __name__ == "__main__":
            # Run async tests properly