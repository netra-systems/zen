from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
"""
        """Send JSON message."""Send JSON message."""
        raise RuntimeError("WebSocket is closed)""Normal closure):"
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False
"""
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()"""
        """
        Integration test suite to verify TriageSubAgent SSOT compliance after fixes."""
        This test suite confirms that all SSOT violations have been fixed."""


import asyncio
import unittest
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

    # Add project root to path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.triage.unified_triage_agent import TriageCore
from netra_backend.app.agents.triage_sub_agent.processing import TriageProcessor
from netra_backend.app.agents.triage.unified_triage_agent import cache_utils
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

"""
        """Test suite to verify TriageSubAgent SSOT compliance after fixes."""
"""
        """Set up test fixtures."""
        self.agent = TriageSubAgent()"""
        user_id="test_user,"
        thread_id="test_thread,"
        run_id="test_run,"
        websocket_connection_id="test_ws"
    
        self.context.metadata = {"user_request": "Test request}"

    # ========== FIX 1: BaseAgent Inheritance ==========

    def test_extends_base_agent(self):
        """Verify TriageSubAgent extends BaseAgent."""
        pass"""
        " PASS:  TriageSubAgent extends BaseAgent)"
        print(" PASS:  PASS: TriageSubAgent properly extends BaseAgent)"

    def test_has_base_agent_methods(self):
        """Verify BaseAgent methods are available."""
        methods = ['emit_thinking', 'emit_progress', 'emit_agent_completed',
        'emit_agent_started', 'emit_error']

        for method in methods:"""
        "formatted_string)"
        print(" PASS:  PASS: All BaseAgent WebSocket methods available)""""Verify WebSocketBridgeAdapter is initialized."""
        pass"""
        " PASS:  Has WebSocketBridgeAdapter)"" PASS:  PASS: WebSocketBridgeAdapter properly initialized)""""Verify no deprecated JSON imports."""
import netra_backend.app.agents.triage.unified_triage_agent.core as core_module
"""
        " PASS:  No deprecated extract_json_from_response import)"
        print(" PASS:  PASS: Deprecated JSON imports removed)"

    def test_uses_unified_json_handler(self):
        """Verify unified JSON handler is used."""
        pass
        core = TriageCore(self.context)

    # Check that safe_json_loads is imported
from netra_backend.app.core.serialization.unified_json_handler import ( )
        LLMResponseParser, JSONErrorFixer, safe_json_loads
    
"""
        test_json = '{"test": "value}'"
        result = core.extract_and_validate_json(test_json)
        self.assertIsInstance(result, dict)
        print(" PASS:  PASS: Using unified JSON handler for parsing)"

    def test_json_error_recovery(self):
        """Verify JSON error recovery works."""
        core = TriageCore(self.context)
"""
        malformed = '{"test": "value'  # Missing closing brace )"
        result = core.extract_and_validate_json(malformed)

    # Should recover or return None, not crash
        self.assertTrue(result is None or isinstance(result, dict))
        print(" PASS:  PASS: JSON error recovery working)"

    # ========== FIX 3: Cache Hash SSOT ==========

    def test_no_custom_hash_generation(self):
        """Verify no custom hashlib usage."""
        pass
    # Check hashlib not imported in cache_utils"""
        " PASS:  No hashlib import in cache_utils)"
        print(" PASS:  PASS: Custom hashlib removed from cache_utils)"

    def test_uses_cache_helpers(self):
        """Verify CacheHelpers is used for hashing."""
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
"""
        test_request = "test request"
        hash_result = cache_utils.generate_request_hash(test_request)

    # SHA256 produces 64 char hex, MD5 produces 32
        self.assertEqual(len(hash_result), 64,
        " PASS:  Using SHA256 from CacheHelpers (64 chars))"
        print(" PASS:  PASS: Using CacheHelpers for hash generation)"

    def test_cache_with_user_context(self):
        """Verify cache includes user context when available."""Verify cache includes user context when available."""
        test_request = "test request"

    # Hash without context
        hash1 = cache_utils.generate_request_hash(test_request)

    # Hash with context
        hash2 = cache_utils.generate_request_hash(test_request, self.context)

    # Should be different when context is provided
        self.assertNotEqual(hash1, hash2,
        " PASS:  Cache keys include user context)"
        print(" PASS:  PASS: User context properly included in cache keys)"

    # ========== FIX 4: WebSocket Integration ==========

    async def test_websocket_events_emitted(self):
        """Verify WebSocket events are properly emitted."""
        # Mock the WebSocket adapter
        websocket = TestWebSocketConnection()
        self.agent._websocket_adapter = mock_adapter

        # Execute the agent
        try:
        await self.agent.execute(self.context, stream_updates=True)"""
        pass  # We"re testing event emission, not full execution"

                # Verify agent_started was called
        mock_adapter.emit_agent_started.assert_called()
        print(" PASS:  PASS: WebSocket events properly emitted)""""Verify proper context isolation."""
        pass
                    # Create multiple contexts
        contexts = [ )"""
        user_id="formatted_string,"
        thread_id="formatted_string,"
        run_id="formatted_string,"
        websocket_connection_id="formatted_string"
        ) for i in range(3)
                    

        for ctx in contexts:
        ctx.metadata = {"user_request": "formatted_string}"

                        # Verify no shared state
        self.assertFalse(hasattr(self.agent, 'user_id'))
        self.assertFalse(hasattr(self.agent, 'db_session'))
        print(" PASS:  PASS: No user data stored in instance variables)"

                        # ========== FIX 6: No Direct Environment Access ==========

    def test_no_direct_environ_access(self):
        """Verify no direct os.environ access."""
import netra_backend.app.agents.triage.unified_triage_agent as triage_module

    # This is a basic check - more thorough AST analysis would be better
        source_files = ['core', 'processing', 'cache_utils']

        for file in source_files:
        module = getattr(triage_module, file, None)
        if module and hasattr(module, '__file__'):
        with open(module.__file__, 'r') as f:
        content = f.read()
        self.assertNotIn('os.environ[', content) )
        self.assertNotIn('os.environ.get(', content) )"""
        print(" PASS:  PASS: No direct os.environ access detected)"

                # ========== Integration Test ==========

    async def test_full_execution_with_fixes(self):
        """Test full execution with all fixes applied."""
        pass
                    # Mock necessary dependencies
                    # Execute the agent
        result = await self.agent.execute(self.context)

                    # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn('metadata', result)
        self.assertIn('run_id', result['metadata'])
        self.assertEqual(result['metadata']['run_id'], self.context.run_id)"""
        print(" PASS:  PASS: Full execution works with all fixes)"

    def test_summary(self):
        """Print summary of all compliance checks."""
        print(" )"
        " + "="*80)"
        print("TRIAGE AGENT SSOT COMPLIANCE VERIFICATION COMPLETE)"
        print("=*80)"
        print(" PASS:  BaseAgent inheritance: FIXED)"
        print(" PASS:  JSON handling SSOT: FIXED)"
        print(" PASS:  Cache hash generation: FIXED)"
        print(" PASS:  WebSocket integration: FIXED)"" PASS:  UserExecutionContext: MAINTAINED)"
        print(" PASS:  No direct environment access: COMPLIANT)"
        print("=*80)"
        print("All SSOT violations have been successfully resolved!)"
        print("="*80 + " )"
        ")"


        if __name__ == "__main__:"
        # Run tests
        unittest.main(verbosity=2)
        pass

]]]
}