class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Factory Pattern Isolation Security Tests

        This test suite verifies that the new factory patterns prevent critical
        multi-user data leakage vulnerabilities that were present in the singleton
        implementations.

        Tests:
        1. WebSocket Manager isolation
        2. Agent WebSocket Bridge isolation
        3. LLM Manager conversation isolation
        4. UserExecutionContext validation
        5. Cache isolation between users

        Business Value Justification (BVJ):
        - Segment: ALL (Free  ->  Enterprise)
        - Business Goal: Prevent catastrophic security breaches
        - Value Impact: Ensures user data privacy and system integrity
        - Revenue Impact: Prevents trust loss and potential lawsuits from data breaches
        '''

        import asyncio
        import pytest
        from datetime import datetime
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.websocket_core.websocket_manager_factory import ( )
        create_websocket_manager,
        WebSocketManagerFactory
            
        from netra_backend.app.services.agent_websocket_bridge import ( )
        create_agent_websocket_bridge,
        AgentWebSocketBridge
            
        from netra_backend.app.llm.llm_manager import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        create_llm_manager,
        LLMManager
            


class TestFactoryPatternIsolation:
        """Test that factory patterns provide proper multi-user isolation."""

        @pytest.fixture
    def user_context_1(self):
        """Create user context for user 1."""
        return UserExecutionContext( )
        user_id="user_1_test",
        thread_id="thread_1",
        run_id="run_1",
        request_id="req_1",
        websocket_connection_id="conn_1"
    

        @pytest.fixture
    def user_context_2(self):
        """Create user context for user 2."""
        pass
        return UserExecutionContext( )
        user_id="user_2_test",
        thread_id="thread_2",
        run_id="run_2",
        request_id="req_2",
        websocket_connection_id="conn_2"
    

    async def test_websocket_manager_isolation(self, user_context_1, user_context_2):
        """Test that WebSocket managers are properly isolated between users."""
        # Create isolated managers for two different users
        manager_1 = create_websocket_manager(user_context_1)
        manager_2 = create_websocket_manager(user_context_2)

        # Verify they are different instances
        assert manager_1 is not manager_2
        assert id(manager_1) != id(manager_2)

        # Verify they have different user contexts
        assert manager_1.user_context.user_id == "user_1_test"
        assert manager_2.user_context.user_id == "user_2_test"

        # Create mock WebSocket connections
        websocket_1 = Magic        websocket_2 = Magic
        from netra_backend.app.websocket_core.websocket_manager import WebSocketConnection

        conn_1 = WebSocketConnection( )
        connection_id="conn_1",
        user_id="user_1_test",
        websocket=websocket_1,
        connected_at=datetime.now()
        

        conn_2 = WebSocketConnection( )
        connection_id="conn_2",
        user_id="user_2_test",
        websocket=websocket_2,
        connected_at=datetime.now()
        

        # Add connections to respective managers
        await manager_1.add_connection(conn_1)
        await manager_2.add_connection(conn_2)

        # Verify isolation: manager 1 should not see manager 2's connections
        user_1_connections = manager_1.get_user_connections()
        user_2_connections = manager_2.get_user_connections()

        assert "conn_1" in user_1_connections
        assert "conn_2" not in user_1_connections
        assert "conn_2" in user_2_connections
        assert "conn_1" not in user_2_connections

        # Test message isolation
        websocket_1.websocket = TestWebSocketConnection()

        message_1 = {"type": "test", "data": "user_1_secret"}
        message_2 = {"type": "test", "data": "user_2_secret"}

        await manager_1.send_to_user(message_1)
        await manager_2.send_to_user(message_2)

        # Verify each user only received their own message
        websocket_1.send_json.assert_called_once_with(message_1)
        websocket_2.send_json.assert_called_once_with(message_2)

        # Clean up
        await manager_1.cleanup_all_connections()
        await manager_2.cleanup_all_connections()

    async def test_agent_websocket_bridge_isolation(self, user_context_1, user_context_2):
        """Test that Agent WebSocket Bridges are properly isolated."""
        pass
            # Create isolated bridges for two different users
        bridge_1 = create_agent_websocket_bridge(user_context_1)
        bridge_2 = create_agent_websocket_bridge(user_context_2)

            # Verify they are different instances
        assert bridge_1 is not bridge_2
        assert id(bridge_1) != id(bridge_2)

            # Create user emitters (async method)
        emitter_1 = await bridge_1.create_user_emitter(user_context_1)
        emitter_2 = await bridge_2.create_user_emitter(user_context_2)

            # Verify emitters are isolated
        assert emitter_1 is not emitter_2
            # Emitters should have different internal state (check websocket manager)
        assert hasattr(emitter_1, '_websocket_manager')
        assert hasattr(emitter_2, '_websocket_manager')

            # Test that bridges maintain separate state
        bridge_1._test_state = "bridge_1_data"
        bridge_2._test_state = "bridge_2_data"

        assert getattr(bridge_1, '_test_state', None) == "bridge_1_data"
        assert getattr(bridge_2, '_test_state', None) == "bridge_2_data"

    async def test_llm_manager_cache_isolation(self, user_context_1, user_context_2):
        """Test that LLM Manager caches are properly isolated between users."""
                # Create isolated managers for two different users
        manager_1 = create_llm_manager(user_context_1)
        manager_2 = create_llm_manager(user_context_2)

                # Verify they are different instances with different caches
        assert manager_1 is not manager_2
        assert id(manager_1) != id(manager_2)
        assert manager_1._cache is not manager_2._cache

                # Verify user context isolation
        assert manager_1._user_context.user_id == "user_1_test"
        assert manager_2._user_context.user_id == "user_2_test"

                # Mock the LLM request to await asyncio.sleep(0)
        return different responses per user
    async def mock_llm_request_1(prompt, config):
        await asyncio.sleep(0)
        return "User 1 response"

    async def mock_llm_request_2(prompt, config):
        await asyncio.sleep(0)
        return "User 2 response"

        manager_1._make_llm_request = mock_llm_request_1
        manager_2._make_llm_request = mock_llm_request_2

    # Initialize managers
        await manager_1.initialize()
        await manager_2.initialize()

    # Same prompt should cache differently for each user
        prompt = "What is the weather?"

        response_1 = await manager_1.ask_llm(prompt, use_cache=True)
        response_2 = await manager_2.ask_llm(prompt, use_cache=True)

    # Verify responses are different (user-specific)
        assert response_1 == "User 1 response"
        assert response_2 == "User 2 response"

    # Verify cache keys are user-scoped
        cache_key_1 = manager_1._get_cache_key(prompt, "default")
        cache_key_2 = manager_2._get_cache_key(prompt, "default")

        assert cache_key_1 != cache_key_2
        assert "user_1_test" in cache_key_1
        assert "user_2_test" in cache_key_2

    # Verify caches are truly isolated
        assert cache_key_1 in manager_1._cache
        assert cache_key_2 not in manager_1._cache
        assert cache_key_2 in manager_2._cache
        assert cache_key_1 not in manager_2._cache

    # Test cache hits are user-specific
        response_1_cached = await manager_1.ask_llm(prompt, use_cache=True)
        response_2_cached = await manager_2.ask_llm(prompt, use_cache=True)

        assert response_1_cached == "User 1 response"
        assert response_2_cached == "User 2 response"

    def test_user_execution_context_validation(self):
        """Test that UserExecutionContext enforces proper validation."""
        pass
    # Valid context should work
        valid_context = UserExecutionContext( )
        user_id="valid_user",
        thread_id="valid_thread",
        run_id="valid_run",
        request_id="valid_request"
    
        assert valid_context.user_id == "valid_user"

    # Invalid user_id should raise ValueError
        with pytest.raises(ValueError, match="cannot be the string 'None'"):
        UserExecutionContext( )
        user_id="None",  # Invalid placeholder
        thread_id="thread",
        run_id="run",
        request_id="request"
        

        with pytest.raises(ValueError, match="cannot be 'registry'"):
        UserExecutionContext( )
        user_id="user",
        thread_id="thread",
        run_id="registry",  # Invalid placeholder
        request_id="request"
            

        with pytest.raises((ValueError, TypeError)):
        UserExecutionContext( )
        user_id=None,  # Invalid None
        thread_id="thread",
        run_id="run",
        request_id="request"
                

    async def test_factory_vs_singleton_security_comparison(self, user_context_1, user_context_2):
        """Test that factory patterns are more secure than singletons."""
                    # Test WebSocket Manager factory pattern
        factory_manager_1 = create_websocket_manager(user_context_1)
        factory_manager_2 = create_websocket_manager(user_context_2)

                    # Factory pattern: Different instances for different users
        assert factory_manager_1 is not factory_manager_2
        assert factory_manager_1.user_context.user_id != factory_manager_2.user_context.user_id

                    # Test deprecated singleton pattern behavior
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

        with pytest.warns():  # Any warning is fine
        singleton_manager_1 = get_websocket_manager()
        singleton_manager_2 = get_websocket_manager()

                    # Singleton pattern: Returns new instances (after our fix)
                    # but no user context isolation
        assert singleton_manager_1 is not singleton_manager_2  # Fixed: no longer shared
        assert not hasattr(singleton_manager_1, 'user_context')  # No isolation

    async def test_concurrent_user_operations(self, user_context_1, user_context_2):
        """Test that concurrent operations by different users remain isolated."""
        pass
                        # Create managers for concurrent operations
        manager_1 = create_llm_manager(user_context_1)
        manager_2 = create_llm_manager(user_context_2)

        await manager_1.initialize()
        await manager_2.initialize()

                        # Mock different responses for each user
    async def mock_request_1(prompt, config):
        pass
        await asyncio.sleep(0.1)  # Simulate async operation
        await asyncio.sleep(0)
        return "formatted_string"

    async def mock_request_2(prompt, config):
        pass
        await asyncio.sleep(0.1)  # Simulate async operation
        await asyncio.sleep(0)
        return "formatted_string"

        manager_1._make_llm_request = mock_request_1
        manager_2._make_llm_request = mock_request_2

    # Concurrent operations with the same prompt
        prompts = ["Question 1", "Question 2", "Question 3"]

    # Run concurrent operations
        tasks_1 = [manager_1.ask_llm(prompt, use_cache=True) for prompt in prompts]
        tasks_2 = [manager_2.ask_llm(prompt, use_cache=True) for prompt in prompts]

        results_1 = await asyncio.gather(*tasks_1)
        results_2 = await asyncio.gather(*tasks_2)

    # Verify results are user-specific
        for i, prompt in enumerate(prompts):
        assert results_1[i] == "formatted_string"
        assert results_2[i] == "formatted_string"

        # Verify caches are isolated
        assert len(manager_1._cache) == 3
        assert len(manager_2._cache) == 3

        # Check cache keys are user-specific
        for prompt in prompts:
        key_1 = manager_1._get_cache_key(prompt, "default")
        key_2 = manager_2._get_cache_key(prompt, "default")
        assert key_1 != key_2
        assert key_1 in manager_1._cache
        assert key_2 in manager_2._cache


class TestDeprecatedSingletonBehavior:
        """Test that deprecated singleton functions provide warnings and basic safety."""

    async def test_websocket_manager_singleton_warning(self):
        """Test that deprecated WebSocket manager function shows warnings."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

        with pytest.warns():  # Any warning is fine
        manager = get_websocket_manager()
        assert manager is not None

    async def test_agent_bridge_singleton_warning(self):
        """Test that deprecated Agent Bridge function shows warnings."""
        pass
        from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge

        with pytest.warns(DeprecationWarning):
        bridge = await get_agent_websocket_bridge()
        assert bridge is not None

    async def test_llm_manager_singleton_warning(self):
        """Test that deprecated LLM Manager function shows warnings."""
        from netra_backend.app.llm.llm_manager import get_llm_manager

        with pytest.warns(DeprecationWarning):
        manager = await get_llm_manager()
        assert manager is not None


        if __name__ == "__main__":
        pytest.main([__file__, "-v"])
        pass
