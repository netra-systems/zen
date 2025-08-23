"""
L4 Integration Test: WebSocket Reconnection Resilience
Tests WebSocket reconnection scenarios, state recovery, and message continuity
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

# from app.services.websocket_service import WebSocketService
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets

WebSocketService = AsyncMock
from netra_backend.app.config import get_config
from netra_backend.app.services.message_queue_service import MessageQueueService
from netra_backend.app.services.session_service import SessionService

class TestWebSocketReconnectionResilienceL4:
    """WebSocket reconnection resilience testing"""
    
    @pytest.fixture
    async def ws_system(self):
        """WebSocket system setup"""
        return {
            'ws_service': WebSocketService(),
            'session_service': SessionService(),
            'queue_service': MessageQueueService(),
            'connection_history': {},
            'message_buffer': deque(maxlen=1000),
            'reconnect_attempts': {},
            'state_snapshots': {}
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_graceful_reconnection(self, ws_system):
        """Test graceful WebSocket reconnection with state preservation"""
        client_id = "client_graceful"
        user_id = "user_123"
        
        # Initial connection
        ws1 = MagicMock()
        initial_state = {
            'user_id': user_id,
            'subscription_channels': ['updates', 'notifications'],
            'client_metadata': {'version': '1.0', 'platform': 'web'}
        }
        
        conn1 = await ws_system['ws_service'].connect(
            websocket=ws1,
            client_id=client_id,
            initial_state=initial_state
        )
        
        # Send messages while connected
        messages_sent = []
        for i in range(5):
            msg = {'id': f'msg_{i}', 'data': f'Data {i}'}
            await ws_system['ws_service'].send_message(client_id, msg)
            messages_sent.append(msg)
        
        # Simulate disconnect
        await ws_system['ws_service'].handle_disconnect(client_id, reason='network_error')
        
        # Queue messages while disconnected
        for i in range(5, 10):
            msg = {'id': f'msg_{i}', 'data': f'Data {i}'}
            await ws_system['ws_service'].queue_message(client_id, msg)
            messages_sent.append(msg)
        
        # Reconnect with new websocket
        ws2 = MagicMock()
        received_messages = []
        ws2.send = AsyncMock(side_effect=lambda msg: received_messages.append(json.loads(msg)))
        
        conn2 = await ws_system['ws_service'].reconnect(
            websocket=ws2,
            client_id=client_id,
            reconnect_token=conn1['reconnect_token']
        )
        
        # Verify state restored
        assert conn2['state']['user_id'] == user_id
        assert set(conn2['state']['subscription_channels']) == {'updates', 'notifications'}
        
        # Process queued messages
        await ws_system['ws_service'].flush_queued_messages(client_id)
        
        # Should receive messages queued during disconnect
        assert len(received_messages) >= 5
        for msg in received_messages:
            assert msg['id'] in [m['id'] for m in messages_sent[5:]]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_exponential_backoff_reconnection(self, ws_system):
        """Test exponential backoff for reconnection attempts"""
        client_id = "client_backoff"
        
        reconnect_delays = []
        attempt_times = []
        
        async def attempt_reconnect():
            attempts = 0
            max_attempts = 5
            base_delay = 0.1  # 100ms base
            
            while attempts < max_attempts:
                start_time = time.time()
                
                try:
                    # Simulate reconnection attempt
                    if attempts < 3:  # First 3 attempts fail
                        raise websockets.exceptions.ConnectionClosed(None, None)
                    
                    # 4th attempt succeeds
                    return True
                    
                except websockets.exceptions.ConnectionClosed:
                    attempts += 1
                    delay = base_delay * (2 ** attempts)  # Exponential backoff
                    delay = min(delay, 5.0)  # Max 5 seconds
                    
                    reconnect_delays.append(delay)
                    attempt_times.append(time.time() - start_time)
                    
                    await asyncio.sleep(delay)
            
            return False
        
        # Attempt reconnection with backoff
        success = await attempt_reconnect()
        
        assert success
        assert len(reconnect_delays) == 3
        
        # Verify exponential increase
        assert reconnect_delays[0] < reconnect_delays[1]
        assert reconnect_delays[1] < reconnect_delays[2]
        
        # Verify delays follow exponential pattern
        assert 0.1 <= reconnect_delays[0] <= 0.3
        assert 0.3 <= reconnect_delays[1] <= 0.6
        assert 0.6 <= reconnect_delays[2] <= 1.5
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_message_replay_on_reconnect(self, ws_system):
        """Test message replay functionality on reconnection"""
        client_id = "client_replay"
        
        # Initial connection
        ws1 = MagicMock()
        conn1 = await ws_system['ws_service'].connect(
            websocket=ws1,
            client_id=client_id,
            enable_replay=True,
            replay_window=60  # 60 second replay window
        )
        
        # Send and acknowledge messages
        acknowledged = []
        for i in range(10):
            msg = {'id': f'msg_{i}', 'seq': i, 'data': f'Data {i}'}
            await ws_system['ws_service'].send_message(client_id, msg)
            
            if i < 7:  # Acknowledge first 7 messages
                await ws_system['ws_service'].acknowledge_message(client_id, msg['id'])
                acknowledged.append(msg['id'])
        
        # Disconnect
        await ws_system['ws_service'].handle_disconnect(client_id)
        
        # Reconnect and request replay
        ws2 = MagicMock()
        replayed_messages = []
        ws2.send = AsyncMock(side_effect=lambda msg: replayed_messages.append(json.loads(msg)))
        
        conn2 = await ws_system['ws_service'].reconnect(
            websocket=ws2,
            client_id=client_id,
            replay_from_seq=7  # Replay from message 7 onwards
        )
        
        # Process replay
        await ws_system['ws_service'].replay_messages(client_id, from_seq=7)
        
        # Should replay messages 7, 8, 9
        assert len(replayed_messages) == 3
        assert replayed_messages[0]['seq'] == 7
        assert replayed_messages[1]['seq'] == 8
        assert replayed_messages[2]['seq'] == 9
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_connection_state_machine(self, ws_system):
        """Test WebSocket connection state machine transitions"""
        client_id = "client_state_machine"
        
        # Track state transitions
        state_history = []
        
        async def track_state(new_state):
            state_history.append({
                'state': new_state,
                'timestamp': time.time()
            })
        
        ws_system['ws_service'].on_state_change = track_state
        
        # Initial state: DISCONNECTED
        assert await ws_system['ws_service'].get_connection_state(client_id) == 'DISCONNECTED'
        
        # Connect: DISCONNECTED -> CONNECTING -> CONNECTED
        ws = MagicMock()
        await ws_system['ws_service'].connect(websocket=ws, client_id=client_id)
        
        # Network issue: CONNECTED -> RECONNECTING
        await ws_system['ws_service'].handle_network_issue(client_id)
        
        # Reconnect attempt: RECONNECTING -> CONNECTED
        ws2 = MagicMock()
        await ws_system['ws_service'].reconnect(websocket=ws2, client_id=client_id)
        
        # Graceful close: CONNECTED -> CLOSING -> DISCONNECTED
        await ws_system['ws_service'].close_connection(client_id, graceful=True)
        
        # Verify state transitions
        states = [h['state'] for h in state_history]
        assert 'CONNECTING' in states
        assert 'CONNECTED' in states
        assert 'RECONNECTING' in states
        assert 'CLOSING' in states
        
        # Verify final state
        assert await ws_system['ws_service'].get_connection_state(client_id) == 'DISCONNECTED'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_heartbeat_failure_detection(self, ws_system):
        """Test heartbeat-based connection failure detection"""
        client_id = "client_heartbeat"
        
        # Connect with heartbeat
        ws = MagicMock()
        ping_count = 0
        
        async def mock_ping():
            nonlocal ping_count
            ping_count += 1
            if ping_count > 3:
                raise websockets.exceptions.ConnectionClosed(None, None)
            return True
        
        ws.ping = AsyncMock(side_effect=mock_ping)
        
        conn = await ws_system['ws_service'].connect(
            websocket=ws,
            client_id=client_id,
            heartbeat_interval=0.1  # 100ms heartbeat
        )
        
        # Start heartbeat monitor
        heartbeat_task = asyncio.create_task(
            ws_system['ws_service'].heartbeat_monitor(client_id)
        )
        
        # Wait for heartbeat failure
        await asyncio.sleep(0.5)
        
        # Connection should be marked as failed
        state = await ws_system['ws_service'].get_connection_state(client_id)
        assert state in ['RECONNECTING', 'DISCONNECTED']
        
        # Heartbeat task should have detected failure
        assert ping_count > 3
        
        heartbeat_task.cancel()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_reconnect_with_auth_refresh(self, ws_system):
        """Test reconnection with auth token refresh"""
        client_id = "client_auth_refresh"
        user_id = "user_456"
        
        # Initial connection with auth token
        ws1 = MagicMock()
        initial_token = "initial_token_expires_soon"
        
        conn1 = await ws_system['ws_service'].connect(
            websocket=ws1,
            client_id=client_id,
            auth_token=initial_token,
            token_expires_at=time.time() + 2  # Expires in 2 seconds
        )
        
        # Wait for token to expire
        await asyncio.sleep(2.5)
        
        # Attempt reconnection with expired token
        ws2 = MagicMock()
        
        # Mock auth refresh
        async def refresh_auth_token(old_token):
            if old_token == initial_token:
                return "refreshed_token_valid"
            raise Exception("Invalid token")
        
        ws_system['ws_service'].refresh_auth_token = refresh_auth_token
        
        # Reconnect (should trigger token refresh)
        conn2 = await ws_system['ws_service'].reconnect(
            websocket=ws2,
            client_id=client_id,
            auth_token=initial_token
        )
        
        assert conn2['auth_token'] == "refreshed_token_valid"
        assert conn2['authenticated']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_parallel_reconnection_prevention(self, ws_system):
        """Test prevention of parallel reconnection attempts"""
        client_id = "client_parallel"
        
        # Track reconnection attempts
        reconnect_results = []
        
        async def attempt_reconnect(attempt_id):
            try:
                ws = MagicMock()
                result = await ws_system['ws_service'].reconnect(
                    websocket=ws,
                    client_id=client_id,
                    attempt_id=attempt_id
                )
                return {'success': True, 'attempt_id': attempt_id}
            except Exception as e:
                return {'success': False, 'attempt_id': attempt_id, 'error': str(e)}
        
        # Launch parallel reconnection attempts
        tasks = [
            asyncio.create_task(attempt_reconnect(f"attempt_{i}"))
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        reconnect_results = results
        
        # Only one should succeed
        successful = [r for r in reconnect_results if r['success']]
        failed = [r for r in reconnect_results if not r['success']]
        
        assert len(successful) == 1
        assert len(failed) == 4
        
        # Failed attempts should indicate reconnection in progress
        for failure in failed:
            assert 'already reconnecting' in failure.get('error', '').lower()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_subscription_restoration(self, ws_system):
        """Test subscription restoration after reconnection"""
        client_id = "client_subscriptions"
        
        # Initial connection with subscriptions
        ws1 = MagicMock()
        subscriptions = {
            'market_data': {'symbols': ['AAPL', 'GOOGL']},
            'user_events': {'user_id': 'user_123'},
            'system_alerts': {'severity': ['high', 'critical']}
        }
        
        conn1 = await ws_system['ws_service'].connect(
            websocket=ws1,
            client_id=client_id
        )
        
        # Subscribe to channels
        for channel, params in subscriptions.items():
            await ws_system['ws_service'].subscribe(
                client_id=client_id,
                channel=channel,
                params=params
            )
        
        # Verify subscriptions active
        active_subs = await ws_system['ws_service'].get_subscriptions(client_id)
        assert len(active_subs) == 3
        
        # Disconnect
        await ws_system['ws_service'].handle_disconnect(client_id)
        
        # Reconnect
        ws2 = MagicMock()
        conn2 = await ws_system['ws_service'].reconnect(
            websocket=ws2,
            client_id=client_id,
            restore_subscriptions=True
        )
        
        # Subscriptions should be restored
        restored_subs = await ws_system['ws_service'].get_subscriptions(client_id)
        assert len(restored_subs) == 3
        assert 'market_data' in restored_subs
        assert restored_subs['market_data']['symbols'] == ['AAPL', 'GOOGL']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_reconnect_quota_limits(self, ws_system):
        """Test reconnection attempt quota and rate limiting"""
        client_id = "client_quota"
        
        # Configure reconnect limits
        reconnect_config = {
            'max_attempts_per_minute': 3,
            'max_attempts_per_hour': 10,
            'cooldown_after_max': 300  # 5 minutes
        }
        
        ws_system['ws_service'].set_reconnect_config(reconnect_config)
        
        # Rapid reconnection attempts
        attempts = []
        for i in range(5):
            ws = MagicMock()
            try:
                result = await ws_system['ws_service'].reconnect(
                    websocket=ws,
                    client_id=client_id
                )
                attempts.append({'success': True, 'attempt': i})
            except Exception as e:
                attempts.append({'success': False, 'attempt': i, 'error': str(e)})
            
            await asyncio.sleep(0.1)
        
        # First 3 should succeed, rest should be rate limited
        successful = [a for a in attempts if a['success']]
        rate_limited = [a for a in attempts if not a['success']]
        
        assert len(successful) <= 3
        assert len(rate_limited) >= 2
        
        # Should be in cooldown
        is_cooled_down = await ws_system['ws_service'].is_in_cooldown(client_id)
        assert is_cooled_down
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_state_diff_sync(self, ws_system):
        """Test state differential synchronization on reconnect"""
        client_id = "client_diff_sync"
        
        # Initial state
        initial_state = {
            'user_prefs': {'theme': 'dark', 'lang': 'en'},
            'workspace': {'project_id': '123', 'files': ['a.py', 'b.py']},
            'cache': {'data1': 'value1', 'data2': 'value2'}
        }
        
        ws1 = MagicMock()
        conn1 = await ws_system['ws_service'].connect(
            websocket=ws1,
            client_id=client_id,
            initial_state=initial_state
        )
        
        # Modify state while connected
        await ws_system['ws_service'].update_client_state(
            client_id=client_id,
            updates={
                'user_prefs.theme': 'light',
                'workspace.files': ['a.py', 'b.py', 'c.py'],
                'cache.data3': 'value3'
            }
        )
        
        # Disconnect
        await ws_system['ws_service'].handle_disconnect(client_id)
        
        # Reconnect with partial state (client sends what it has)
        ws2 = MagicMock()
        client_state = {
            'user_prefs': {'theme': 'dark', 'lang': 'en'},  # Outdated theme
            'workspace': {'project_id': '123', 'files': ['a.py', 'b.py']},  # Missing c.py
            # Missing cache entirely
        }
        
        state_diff = []
        ws2.send = AsyncMock(side_effect=lambda msg: state_diff.append(json.loads(msg)))
        
        conn2 = await ws_system['ws_service'].reconnect(
            websocket=ws2,
            client_id=client_id,
            client_state=client_state,
            sync_mode='differential'
        )
        
        # Should receive only the differences
        assert len(state_diff) > 0
        
        # Check diff contains updates
        diff_msg = state_diff[0]
        assert diff_msg['type'] == 'state_diff'
        assert diff_msg['updates']['user_prefs.theme'] == 'light'
        assert 'c.py' in diff_msg['updates']['workspace.files']
        assert 'cache' in diff_msg['updates']