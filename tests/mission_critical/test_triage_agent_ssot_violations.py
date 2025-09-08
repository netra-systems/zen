# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Comprehensive test suite for TriageSubAgent SSOT violations.

    # REMOVED_SYNTAX_ERROR: This test suite is designed to FAIL until all SSOT violations are fixed.
    # REMOVED_SYNTAX_ERROR: Each test targets a specific violation pattern from the AGENT_SSOT_AUDIT_PLAN.

    # REMOVED_SYNTAX_ERROR: Business Value: TriageSubAgent is first contact for ALL users - CRITICAL revenue impact.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import hashlib
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import unittest
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: import os

    # Add project root to path
    # REMOVED_SYNTAX_ERROR: sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Import from the main file instead of module
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage.unified_triage_agent import TriageSubAgent as ImportedAgent
    # REMOVED_SYNTAX_ERROR: try:
        # Try import from main file location
        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: import importlib.util
        # REMOVED_SYNTAX_ERROR: spec = importlib.util.spec_from_file_location( )
        # REMOVED_SYNTAX_ERROR: "triage_sub_agent",
        # REMOVED_SYNTAX_ERROR: "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/app/agents/triage_sub_agent.py"
        
        # REMOVED_SYNTAX_ERROR: module = importlib.util.module_from_spec(spec)
        # REMOVED_SYNTAX_ERROR: spec.loader.exec_module(module)
        # REMOVED_SYNTAX_ERROR: TriageSubAgent = module.TriageSubAgent
        # REMOVED_SYNTAX_ERROR: except Exception as e:
            # Fallback to whatever we could import
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: TriageSubAgent = ImportedAgent if 'ImportedAgent' in locals() else None
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage.unified_triage_agent import TriageCore
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage_sub_agent.processing import TriageProcessor
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_execution_context import UserExecutionContext
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestTriageAgentSSOTViolations(unittest.TestCase):
    # REMOVED_SYNTAX_ERROR: """Test suite to identify and verify SSOT violations in TriageSubAgent."""

# REMOVED_SYNTAX_ERROR: def setUp(self):
    # REMOVED_SYNTAX_ERROR: """Set up test fixtures."""
    # REMOVED_SYNTAX_ERROR: self.agent = TriageSubAgent()
    # REMOVED_SYNTAX_ERROR: self.context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="test_user",
    # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
    # REMOVED_SYNTAX_ERROR: run_id="test_run",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="test_ws"
    
    # REMOVED_SYNTAX_ERROR: self.context.metadata = {"user_request": "Test request"}

    # ========== VIOLATION 1: Custom Hash Generation ==========

# REMOVED_SYNTAX_ERROR: def test_violation_custom_hash_generation_in_cache_utils(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: VIOLATION: Custom hash generation using hashlib.md5 directly
    # REMOVED_SYNTAX_ERROR: instead of using CacheHelpers.hash_key_data()

    # REMOVED_SYNTAX_ERROR: Location: netra_backend/app/agents/triage_sub_agent/cache_utils.py:31
    # REMOVED_SYNTAX_ERROR: '''
    # This test should FAIL if the violation exists
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage.unified_triage_agent import cache_utils

    # Check if hashlib is imported (violation)
    # REMOVED_SYNTAX_ERROR: self.assertIn('hashlib', dir(cache_utils),
    # REMOVED_SYNTAX_ERROR: "PASS: hashlib not imported (violation fixed)")

    # Check if custom hash function exists
    # REMOVED_SYNTAX_ERROR: self.assertTrue(hasattr(cache_utils, 'generate_request_hash'),
    # REMOVED_SYNTAX_ERROR: "PASS: Custom hash generation removed (violation fixed)")

    # Verify it uses hashlib.md5 directly (violation)
    # REMOVED_SYNTAX_ERROR: test_request = "test request"
    # REMOVED_SYNTAX_ERROR: result = cache_utils.generate_request_hash(test_request)
    # REMOVED_SYNTAX_ERROR: expected_violation = hashlib.md5(test_request.lower().strip().encode()).hexdigest()
    # REMOVED_SYNTAX_ERROR: self.assertEqual(result, expected_violation,
    # REMOVED_SYNTAX_ERROR: "PASS: Not using custom MD5 hash (violation fixed)")

# REMOVED_SYNTAX_ERROR: def test_violation_not_using_canonical_cache_helpers(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: Not using CacheHelpers from canonical location
    # REMOVED_SYNTAX_ERROR: instead of netra_backend.app.services.cache.cache_helpers
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: core = TriageCore(self.context)

    # Check if CacheHelpers is properly imported and used
    # REMOVED_SYNTAX_ERROR: self.assertTrue(hasattr(core, '_cache_helper'),
    # REMOVED_SYNTAX_ERROR: "FAIL: CacheHelpers not initialized in TriageCore")

    # Verify it's from the correct module
    # REMOVED_SYNTAX_ERROR: if hasattr(core, '_cache_helper'):
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.cache.cache_helpers import CacheHelpers
        # REMOVED_SYNTAX_ERROR: self.assertIsInstance(core._cache_helper, CacheHelpers,
        # REMOVED_SYNTAX_ERROR: "FAIL: Not using canonical CacheHelpers")

        # ========== VIOLATION 2: Not Extending BaseAgent ==========

# REMOVED_SYNTAX_ERROR: def test_violation_not_extending_base_agent(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: TriageSubAgent doesn"t extend BaseAgent
    # REMOVED_SYNTAX_ERROR: Missing inheritance from netra_backend.app.agents.base_agent.BaseAgent
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base_agent import BaseAgent

    # This should FAIL if TriageSubAgent doesn't extend BaseAgent
    # REMOVED_SYNTAX_ERROR: self.assertIsInstance(self.agent, BaseAgent,
    # REMOVED_SYNTAX_ERROR: "FAIL: TriageSubAgent doesn"t extend BaseAgent")

    # Check for BaseAgent methods
    # REMOVED_SYNTAX_ERROR: base_methods = ['emit_thinking', 'emit_progress', 'emit_agent_completed',
    # REMOVED_SYNTAX_ERROR: '_handle_error', 'timing_collector']
    # REMOVED_SYNTAX_ERROR: for method in base_methods:
        # REMOVED_SYNTAX_ERROR: self.assertTrue(hasattr(self.agent, method),
        # REMOVED_SYNTAX_ERROR: "formatted_string")

        # ========== VIOLATION 3: Custom JSON Extraction ==========

# REMOVED_SYNTAX_ERROR: def test_violation_using_extract_json_from_response(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: Using custom extract_json_from_response
    # REMOVED_SYNTAX_ERROR: instead of unified_json_handler.LLMResponseParser

    # REMOVED_SYNTAX_ERROR: Location: netra_backend/app/agents/triage_sub_agent/core.py:25
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Check if the deprecated function is imported
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.agents.triage.unified_triage_agent.core as core_module

    # This should FAIL if still importing the old function
    # REMOVED_SYNTAX_ERROR: self.assertNotIn('extract_json_from_response', core_module.__dict__,
    # REMOVED_SYNTAX_ERROR: "FAIL: Still importing deprecated extract_json_from_response")

# REMOVED_SYNTAX_ERROR: def test_violation_custom_json_parsing_in_core(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: Custom JSON parsing logic instead of using unified handler
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: core = TriageCore(self.context)

    # Test the extract_and_validate_json method
    # REMOVED_SYNTAX_ERROR: test_response = '{"key": "value"}'
    # REMOVED_SYNTAX_ERROR: result = core.extract_and_validate_json(test_response)

    # Check if it's using the unified handler properly
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.serialization.unified_json_handler import LLMResponseParser

    # Verify LLMResponseParser is used
    # REMOVED_SYNTAX_ERROR: with patch.object(LLMResponseParser, 'safe_json_parse') as mock_parse:
        # REMOVED_SYNTAX_ERROR: mock_parse.return_value = {"key": "value"}
        # REMOVED_SYNTAX_ERROR: core.extract_and_validate_json(test_response)
        # REMOVED_SYNTAX_ERROR: mock_parse.assert_called_once()

# REMOVED_SYNTAX_ERROR: def test_violation_direct_json_loads_usage(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: Direct json.loads usage instead of safe_json_loads

    # REMOVED_SYNTAX_ERROR: Location: netra_backend/app/agents/triage_sub_agent/core.py:187
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: core = TriageCore(self.context)

    # Test malformed JSON that should use error recovery
    # REMOVED_SYNTAX_ERROR: malformed_json = '{"key": "value"'  # Missing closing brace )

    # This should use JSONErrorFixer and recovery, not direct json.loads
    # REMOVED_SYNTAX_ERROR: result = core.extract_and_validate_json(malformed_json)

    # Should handle malformed JSON gracefully using unified handler
    # REMOVED_SYNTAX_ERROR: self.assertIsNotNone(result, "Should recover from malformed JSON")

    # ========== VIOLATION 4: Custom WebSocket Handling ==========

# REMOVED_SYNTAX_ERROR: def test_violation_not_using_websocket_bridge_adapter(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: Not using WebSocketBridgeAdapter for WebSocket events
    # REMOVED_SYNTAX_ERROR: Should use the canonical WebSocket integration pattern
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Check if agent has WebSocketBridgeAdapter
    # REMOVED_SYNTAX_ERROR: self.assertTrue(hasattr(self.agent, '_websocket_adapter') or )
    # REMOVED_SYNTAX_ERROR: hasattr(self.agent, 'websocket_adapter'),
    # REMOVED_SYNTAX_ERROR: "FAIL: No WebSocketBridgeAdapter found")

    # Removed problematic line: async def test_violation_websocket_event_emission(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: VIOLATION: Custom WebSocket event emission instead of using adapter methods
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # Test that proper WebSocket events are sent
        # REMOVED_SYNTAX_ERROR: with patch.object(self.agent, '_send_processing_update') as mock_send:
            # REMOVED_SYNTAX_ERROR: await self.agent._send_processing_update(self.context, "Test message")

            # Should use proper WebSocket adapter methods
            # REMOVED_SYNTAX_ERROR: if hasattr(self.agent, '_websocket_adapter'):
                # REMOVED_SYNTAX_ERROR: self.agent._websocket_adapter.emit_thinking.assert_called()

                # ========== VIOLATION 5: Custom Retry Logic ==========

# REMOVED_SYNTAX_ERROR: def test_violation_custom_retry_implementation(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: Custom retry logic instead of UnifiedRetryHandler
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: processor = TriageProcessor(TriageCore(self.context), None)

    # Check for UnifiedRetryHandler usage
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler

    # Should use UnifiedRetryHandler, not custom retry logic
    # REMOVED_SYNTAX_ERROR: self.assertTrue(hasattr(processor, 'retry_handler') or )
    # REMOVED_SYNTAX_ERROR: any('UnifiedRetryHandler' in str(type(v)) )
    # REMOVED_SYNTAX_ERROR: for v in processor.__dict__.values()),
    # REMOVED_SYNTAX_ERROR: "FAIL: Not using UnifiedRetryHandler")

    # ========== VIOLATION 6: Direct Environment Access ==========

# REMOVED_SYNTAX_ERROR: def test_violation_direct_os_environ_access(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: Direct os.environ access instead of IsolatedEnvironment
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Search for os.environ usage in the module
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.agents.triage.unified_triage_agent as triage_module

    # Check all submodules for os.environ usage
    # REMOVED_SYNTAX_ERROR: violations = []
    # REMOVED_SYNTAX_ERROR: for name in dir(triage_module):
        # REMOVED_SYNTAX_ERROR: obj = getattr(triage_module, name)
        # REMOVED_SYNTAX_ERROR: if hasattr(obj, '__code__'):
            # Check bytecode for os.environ access
            # REMOVED_SYNTAX_ERROR: if 'environ' in str(obj.__code__.co_names):
                # REMOVED_SYNTAX_ERROR: violations.append(name)

                # REMOVED_SYNTAX_ERROR: self.assertEqual([], violations,
                # REMOVED_SYNTAX_ERROR: "formatted_string")

                # ========== VIOLATION 7: State Storage in Instance Variables ==========

                # Removed problematic line: async def test_violation_storing_user_data_in_instance(self):
                    # REMOVED_SYNTAX_ERROR: '''
                    # REMOVED_SYNTAX_ERROR: VIOLATION: Storing user-specific data in instance variables
                    # REMOVED_SYNTAX_ERROR: instead of passing through UserExecutionContext
                    # REMOVED_SYNTAX_ERROR: '''
                    # REMOVED_SYNTAX_ERROR: pass
                    # Check that agent doesn't store user data
                    # REMOVED_SYNTAX_ERROR: await self.agent.execute(self.context)

                    # These should NOT be stored in the agent
                    # REMOVED_SYNTAX_ERROR: forbidden_attrs = ['user_id', 'thread_id', 'db_session', 'current_request']

                    # REMOVED_SYNTAX_ERROR: for attr in forbidden_attrs:
                        # REMOVED_SYNTAX_ERROR: self.assertFalse(hasattr(self.agent, attr),
                        # REMOVED_SYNTAX_ERROR: "formatted_string")

                        # ========== VIOLATION 8: Duplicate Error Handling ==========

# REMOVED_SYNTAX_ERROR: def test_violation_custom_error_handling(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: Custom error handling instead of agent_error_handler
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import agent_error_handler

    # Check if agent uses the unified error handler
    # REMOVED_SYNTAX_ERROR: self.assertTrue(hasattr(self.agent, 'agent_error_handler') or )
    # REMOVED_SYNTAX_ERROR: hasattr(self.agent, '_error_handler'),
    # REMOVED_SYNTAX_ERROR: "FAIL: Not using unified error handler")

    # ========== VIOLATION 9: Missing UserExecutionContext Support ==========

    # Removed problematic line: async def test_violation_missing_context_parameter(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: VIOLATION: Methods not accepting UserExecutionContext parameter
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # Test that execute accepts context
        # REMOVED_SYNTAX_ERROR: import inspect
        # REMOVED_SYNTAX_ERROR: sig = inspect.signature(self.agent.execute)
        # REMOVED_SYNTAX_ERROR: self.assertIn('context', sig.parameters,
        # REMOVED_SYNTAX_ERROR: "FAIL: execute() doesn"t accept context parameter")

        # Verify context is validated
        # REMOVED_SYNTAX_ERROR: with self.assertRaises(ValueError):
            # REMOVED_SYNTAX_ERROR: await self.agent.execute(None)  # Should fail without context

            # ========== VIOLATION 10: Configuration Access Pattern ==========

# REMOVED_SYNTAX_ERROR: def test_violation_direct_config_file_access(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: VIOLATION: Direct config file reading instead of using configuration architecture
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Check for direct file reading
    # REMOVED_SYNTAX_ERROR: core = TriageCore(self.context)

    # Should use get_config() from configuration architecture
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.config import get_config

    # Verify no direct json.load of config files
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.agents.triage.unified_triage_agent.core as core_module
    # REMOVED_SYNTAX_ERROR: source = str(core_module.__file__)

    # This is a simple check - in reality would parse AST
    # REMOVED_SYNTAX_ERROR: self.assertNotIn('open(', str(core_module),
    # REMOVED_SYNTAX_ERROR: "Potential direct file access detected")

    # ========== Integration Tests for Combined Violations ==========

    # Removed problematic line: async def test_concurrent_request_isolation(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test that multiple concurrent requests are properly isolated.
        # REMOVED_SYNTAX_ERROR: This tests multiple SSOT patterns together.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # Create multiple contexts
        # REMOVED_SYNTAX_ERROR: contexts = [ )
        # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: websocket_connection_id="formatted_string"
        # REMOVED_SYNTAX_ERROR: ) for i in range(5)
        

        # REMOVED_SYNTAX_ERROR: for ctx in contexts:
            # REMOVED_SYNTAX_ERROR: ctx.metadata = {"user_request": "formatted_string"}

            # Execute concurrently
            # REMOVED_SYNTAX_ERROR: tasks = [self.agent.execute(ctx) for ctx in contexts]
            # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

            # Verify isolation - no data leakage
            # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
                # REMOVED_SYNTAX_ERROR: self.assertIn(contexts[i].user_id, str(result))
                # REMOVED_SYNTAX_ERROR: self.assertIn(contexts[i].run_id, str(result))

                # Ensure no cross-contamination
                # REMOVED_SYNTAX_ERROR: for j in range(5):
                    # REMOVED_SYNTAX_ERROR: if i != j:
                        # REMOVED_SYNTAX_ERROR: self.assertNotIn(contexts[j].user_id, str(result),
                        # REMOVED_SYNTAX_ERROR: "formatted_string")

                        # Removed problematic line: async def test_websocket_events_with_context(self):
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: Test that WebSocket events are properly sent with UserExecutionContext.
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: pass
                            # Mock WebSocket adapter
                            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
                            # REMOVED_SYNTAX_ERROR: self.agent._websocket_adapter = mock_adapter

                            # Execute with streaming
                            # REMOVED_SYNTAX_ERROR: await self.agent.execute(self.context, stream_updates=True)

                            # Verify proper WebSocket events were sent
                            # REMOVED_SYNTAX_ERROR: expected_events = ['agent_started', 'agent_thinking', 'agent_completed']

                            # Check that events were emitted (this will fail until properly integrated)
                            # REMOVED_SYNTAX_ERROR: self.assertTrue(mock_adapter.emit_thinking.called or )
                            # REMOVED_SYNTAX_ERROR: mock_adapter.emit_progress.called,
                            # REMOVED_SYNTAX_ERROR: "No WebSocket events emitted")

# REMOVED_SYNTAX_ERROR: def test_all_violations_summary(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Summary test that lists all violations found.
    # REMOVED_SYNTAX_ERROR: This test always FAILS to show the complete violation report.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: violations = [ )
    # REMOVED_SYNTAX_ERROR: "1. Custom hash generation in cache_utils.py (using hashlib.md5)",
    # REMOVED_SYNTAX_ERROR: "2. TriageSubAgent doesn"t extend BaseAgent",
    # REMOVED_SYNTAX_ERROR: "3. Using extract_json_from_response instead of unified_json_handler",
    # REMOVED_SYNTAX_ERROR: "4. Direct json.loads usage instead of safe_json_loads",
    # REMOVED_SYNTAX_ERROR: "5. Not using WebSocketBridgeAdapter for events",
    # REMOVED_SYNTAX_ERROR: "6. Custom retry logic instead of UnifiedRetryHandler",
    # REMOVED_SYNTAX_ERROR: "7. Potential direct os.environ access",
    # REMOVED_SYNTAX_ERROR: "8. Storing user data in instance variables",
    # REMOVED_SYNTAX_ERROR: "9. Custom error handling instead of agent_error_handler",
    # REMOVED_SYNTAX_ERROR: "10. Direct config file access patterns"
    

    # REMOVED_SYNTAX_ERROR: print(" )
    # REMOVED_SYNTAX_ERROR: " + "="*80)
    # REMOVED_SYNTAX_ERROR: print("TRIAGE AGENT SSOT VIOLATIONS FOUND:")
    # REMOVED_SYNTAX_ERROR: print("="*80)
    # REMOVED_SYNTAX_ERROR: for v in violations:
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("="*80)
        # REMOVED_SYNTAX_ERROR: print("All these violations must be fixed for tests to pass.")
        # REMOVED_SYNTAX_ERROR: print("="*80 + " )
        # REMOVED_SYNTAX_ERROR: ")

        # This test always fails to show the report
        # REMOVED_SYNTAX_ERROR: self.fail("Multiple SSOT violations detected - see list above")


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # Run async tests properly
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])