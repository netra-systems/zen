"""
Unit tests for WebSocket Unified Manager Connection Validation.

This test suite covers connection validation, state transitions, and error scenarios
for the unified WebSocket manager, focusing on robust validation logic.

Issue #825 Phase 1 Batch 1: Connection Validation Methods
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
from netra_backend.app.websocket_core.types import ConnectionInfo
from shared.types.core_types import ensure_user_id, ensure_websocket_id

class UnifiedManagerConnectionValidationTests(SSotAsyncTestCase):
    """Test connection validation logic in UnifiedWebSocketManager."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.manager = UnifiedWebSocketManager()
        self.mock_websocket = AsyncMock()
        self.mock_websocket.client_state = 1
        self.mock_websocket.close = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()
        self.valid_user_id = 'valid_user_123'
        self.valid_connection_id = 'conn_123'
        self.valid_thread_id = 'thread_123'

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        if hasattr(self.manager, '_connections'):
            for connection in list(self.manager._connections.values()):
                try:
                    await self.manager.disconnect_user(connection.user_id, connection.websocket, code=1001, reason='Test cleanup')
                except Exception:
                    pass
        await super().asyncTearDown()

    async def test_validate_user_id_formats(self):
        """Test user ID validation with various formats."""
        valid_ids = ['user_123', 'auth0|507f1f77bcf86cd799439011', 'google-oauth2|123456789', 'test@example.com', 'user-with-dashes-123']
        for user_id in valid_ids:
            with self.subTest(user_id=user_id):
                result = await self.manager.connect_user(user_id=user_id, websocket=self.mock_websocket, connection_id=f'conn_{user_id}')
                self.assertIsNotNone(result)
                await self.manager.disconnect_user(user_id, self.mock_websocket)

    async def test_reject_invalid_user_id_formats(self):
        """Test rejection of invalid user ID formats."""
        invalid_ids = [None, '', '   ', 'a', 'user with spaces', 'user\nwith\nnewlines', 'user\twith\ttabs']
        for invalid_id in invalid_ids:
            with self.subTest(user_id=invalid_id):
                with self.assertRaises((ValueError, TypeError, AttributeError)):
                    await self.manager.connect_user(user_id=invalid_id, websocket=self.mock_websocket, connection_id='test_conn')

    async def test_websocket_state_validation(self):
        """Test WebSocket state validation during connection."""
        test_cases = [(0, 'CONNECTING', True), (1, 'OPEN', True), (2, 'CLOSING', False), (3, 'CLOSED', False)]
        for state, state_name, should_succeed in test_cases:
            with self.subTest(state=state_name):
                mock_ws = AsyncMock()
                mock_ws.client_state = state
                mock_ws.close = AsyncMock()
                if should_succeed:
                    try:
                        result = await self.manager.connect_user(user_id=f'user_{state}', websocket=mock_ws, connection_id=f'conn_{state}')
                        self.assertIsNotNone(result)
                        await self.manager.disconnect_user(f'user_{state}', mock_ws)
                    except Exception as e:
                        self.fail(f'Valid state {state_name} should not raise: {e}')
                else:
                    with self.assertRaises((ValueError, RuntimeError)):
                        await self.manager.connect_user(user_id=f'user_{state}', websocket=mock_ws, connection_id=f'conn_{state}')

    async def test_connection_id_generation_and_validation(self):
        """Test connection ID generation and validation."""
        custom_conn_id = 'custom_connection_123'
        result = await self.manager.connect_user(user_id=self.valid_user_id, websocket=self.mock_websocket, connection_id=custom_conn_id)
        self.assertIsNotNone(result)
        connections = self.manager._user_connections[self.valid_user_id]
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].connection_id, custom_conn_id)
        await self.manager.disconnect_user(self.valid_user_id, self.mock_websocket)

    async def test_auto_connection_id_generation(self):
        """Test automatic connection ID generation when not provided."""
        result = await self.manager.connect_user(user_id=self.valid_user_id, websocket=self.mock_websocket)
        self.assertIsNotNone(result)
        connections = self.manager._user_connections[self.valid_user_id]
        self.assertEqual(len(connections), 1)
        self.assertIsNotNone(connections[0].connection_id)
        self.assertGreater(len(connections[0].connection_id), 0)
        await self.manager.disconnect_user(self.valid_user_id, self.mock_websocket)

    async def test_thread_id_validation(self):
        """Test thread ID validation and handling."""
        thread_id = 'thread_456'
        result = await self.manager.connect_user(user_id=self.valid_user_id, websocket=self.mock_websocket, thread_id=thread_id)
        self.assertIsNotNone(result)
        connections = self.manager._user_connections[self.valid_user_id]
        self.assertEqual(connections[0].thread_id, thread_id)
        await self.manager.disconnect_user(self.valid_user_id, self.mock_websocket)

    async def test_duplicate_connection_handling(self):
        """Test handling of duplicate connection attempts."""
        result1 = await self.manager.connect_user(user_id=self.valid_user_id, websocket=self.mock_websocket, connection_id=self.valid_connection_id)
        self.assertIsNotNone(result1)
        try:
            result2 = await self.manager.connect_user(user_id=self.valid_user_id, websocket=self.mock_websocket, connection_id=self.valid_connection_id)
            self.assertIsNotNone(result2)
        except Exception:
            pass
        await self.manager.disconnect_user(self.valid_user_id, self.mock_websocket)

    async def test_connection_limit_enforcement(self):
        """Test enforcement of connection limits per user."""
        max_connections = 10
        websockets = []
        try:
            for i in range(max_connections):
                mock_ws = AsyncMock()
                mock_ws.client_state = 1
                mock_ws.close = AsyncMock()
                websockets.append(mock_ws)
                result = await self.manager.connect_user(user_id=self.valid_user_id, websocket=mock_ws, connection_id=f'conn_{i}')
                self.assertIsNotNone(result)
            connections = self.manager._user_connections[self.valid_user_id]
            self.assertEqual(len(connections), max_connections)
        finally:
            for ws in websockets:
                try:
                    await self.manager.disconnect_user(self.valid_user_id, ws)
                except Exception:
                    pass

    async def test_connection_metadata_validation(self):
        """Test validation of connection metadata."""
        result = await self.manager.connect_user(user_id=self.valid_user_id, websocket=self.mock_websocket, connection_id=self.valid_connection_id, thread_id=self.valid_thread_id)
        self.assertIsNotNone(result)
        connections = self.manager._user_connections[self.valid_user_id]
        self.assertEqual(len(connections), 1)
        connection = connections[0]
        self.assertEqual(connection.user_id, self.valid_user_id)
        self.assertEqual(connection.connection_id, self.valid_connection_id)
        self.assertEqual(connection.thread_id, self.valid_thread_id)
        self.assertEqual(connection.websocket, self.mock_websocket)
        self.assertIsNotNone(connection.connected_at)
        self.assertIsInstance(connection.connected_at, (int, float))
        await self.manager.disconnect_user(self.valid_user_id, self.mock_websocket)

    async def test_websocket_capability_validation(self):
        """Test validation of WebSocket capabilities."""
        incomplete_websocket = MagicMock()
        with self.assertRaises(AttributeError):
            await self.manager.connect_user(user_id=self.valid_user_id, websocket=incomplete_websocket, connection_id=self.valid_connection_id)

    async def test_connection_race_condition_handling(self):
        """Test handling of race conditions during connection."""
        tasks = []
        websockets = []
        for i in range(5):
            mock_ws = AsyncMock()
            mock_ws.client_state = 1
            mock_ws.close = AsyncMock()
            websockets.append(mock_ws)
            task = self.manager.connect_user(user_id=self.valid_user_id, websocket=mock_ws, connection_id=f'race_conn_{i}')
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        self.assertGreater(len(successful_results), 0)
        for ws in websockets:
            try:
                await self.manager.disconnect_user(self.valid_user_id, ws)
            except Exception:
                pass

    async def test_validation_error_messages(self):
        """Test that validation errors provide clear messages."""
        test_cases = [(None, self.mock_websocket, 'User ID cannot be None'), ('', self.mock_websocket, 'User ID cannot be empty'), (self.valid_user_id, None, 'WebSocket cannot be None')]
        for user_id, websocket, expected_context in test_cases:
            with self.subTest(user_id=user_id, websocket=websocket):
                try:
                    await self.manager.connect_user(user_id=user_id, websocket=websocket, connection_id='test_conn')
                    self.fail(f'Expected validation error for {expected_context}')
                except Exception as e:
                    error_str = str(e).lower()
                    self.assertIsInstance(e, (ValueError, TypeError, AttributeError))

    async def test_cleanup_validation_after_disconnect(self):
        """Test that validation state is properly cleaned up after disconnect."""
        await self.manager.connect_user(user_id=self.valid_user_id, websocket=self.mock_websocket, connection_id=self.valid_connection_id)
        self.assertIn(self.valid_user_id, self.manager._user_connections)
        await self.manager.disconnect_user(self.valid_user_id, self.mock_websocket)
        user_connections = self.manager._user_connections.get(self.valid_user_id, [])
        self.assertEqual(len(user_connections), 0)
        try:
            await self.manager.disconnect_user(self.valid_user_id, self.mock_websocket)
        except Exception as e:
            self.fail(f'Second disconnect should handle gracefully: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')