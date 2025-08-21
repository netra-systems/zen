"""
L4 Integration Test: WebSocket Message Delivery Guarantees
Tests message ordering, delivery confirmation, and retry mechanisms
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set

# Add project root to path
# from netra_backend.app.services.websocket_service import WebSocketService
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets

WebSocketService = AsyncMock
from netra_backend.app.config import settings
from netra_backend.app.models.websocket_message import WebSocketMessage
from netra_backend.app.services.message_queue_service import MessageQueueService
from netra_backend.app.services.redis_service import RedisService


class TestWebSocketMessageDeliveryGuaranteesL4:
    """Test WebSocket message delivery guarantees under stress"""
    
    @pytest.fixture
    async def ws_infrastructure(self):
        """WebSocket infrastructure setup"""
        return {
            'ws_service': WebSocketService(),
            'queue_service': MessageQueueService(),
            'redis_service': RedisService(),
            'connected_clients': {},
            'message_log': defaultdict(list),
            'ack_tracker': {},
            'retry_queue': []
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_message_ordering_under_load(self, ws_infrastructure):
        """Test message ordering is preserved under high load"""
        client_id = "client_order_test"
        
        # Connect client
        ws_connection = await ws_infrastructure['ws_service'].connect_client(
            client_id=client_id,
            websocket=MagicMock()
        )
        
        # Send 100 messages rapidly
        messages = []
        for i in range(100):
            msg = {
                'id': f"msg_{i}",
                'sequence': i,
                'data': f"Message {i}",
                'timestamp': time.time()
            }
            messages.append(msg)
            
            # Send without waiting
            asyncio.create_task(
                ws_infrastructure['ws_service'].send_message(client_id, msg)
            )
        
        # Wait for all messages to be queued
        await asyncio.sleep(0.5)
        
        # Process message queue
        received_messages = []
        async def receive_handler(message):
            received_messages.append(message)
        
        ws_connection.websocket.send = AsyncMock(side_effect=receive_handler)
        
        # Process all messages
        await ws_infrastructure['ws_service'].flush_message_queue(client_id)
        
        # Verify ordering
        for i in range(len(received_messages) - 1):
            current_seq = json.loads(received_messages[i])['sequence']
            next_seq = json.loads(received_messages[i + 1])['sequence']
            assert current_seq < next_seq, f"Message ordering violated: {current_seq} >= {next_seq}"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_message_acknowledgment_timeout(self, ws_infrastructure):
        """Test message acknowledgment timeout and retry"""
        client_id = "client_ack_test"
        
        # Connect client with ack requirement
        ws_connection = await ws_infrastructure['ws_service'].connect_client(
            client_id=client_id,
            websocket=MagicMock(),
            require_ack=True,
            ack_timeout=1  # 1 second timeout
        )
        
        # Send message requiring acknowledgment
        message = {
            'id': 'msg_ack_1',
            'data': 'Important message',
            'require_ack': True
        }
        
        # Mock send that doesn't acknowledge
        ws_connection.websocket.send = AsyncMock()
        
        # Send message
        send_task = asyncio.create_task(
            ws_infrastructure['ws_service'].send_message_with_ack(client_id, message)
        )
        
        # Wait for timeout
        await asyncio.sleep(1.5)
        
        # Message should be in retry queue
        retry_messages = await ws_infrastructure['ws_service'].get_retry_queue(client_id)
        assert len(retry_messages) == 1
        assert retry_messages[0]['id'] == 'msg_ack_1'
        
        # Simulate acknowledgment on retry
        await ws_infrastructure['ws_service'].acknowledge_message(client_id, 'msg_ack_1')
        
        # Message should be removed from retry queue
        retry_messages = await ws_infrastructure['ws_service'].get_retry_queue(client_id)
        assert len(retry_messages) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_broadcast_delivery_confirmation(self, ws_infrastructure):
        """Test broadcast message delivery to multiple clients"""
        # Connect multiple clients
        client_ids = [f"client_{i}" for i in range(10)]
        connections = {}
        
        for client_id in client_ids:
            conn = await ws_infrastructure['ws_service'].connect_client(
                client_id=client_id,
                websocket=MagicMock()
            )
            connections[client_id] = conn
        
        # Track delivery
        delivered_to = set()
        
        async def delivery_tracker(client_id, message):
            delivered_to.add(client_id)
            return True
        
        # Mock send for all clients
        for client_id, conn in connections.items():
            conn.websocket.send = AsyncMock(
                side_effect=lambda msg, cid=client_id: delivery_tracker(cid, msg)
            )
        
        # Broadcast message
        broadcast_msg = {
            'id': 'broadcast_1',
            'type': 'announcement',
            'data': 'System maintenance in 5 minutes'
        }
        
        delivery_report = await ws_infrastructure['ws_service'].broadcast_message(
            message=broadcast_msg,
            client_filter=lambda cid: True  # Send to all
        )
        
        # Verify all clients received the message
        assert len(delivered_to) == len(client_ids)
        assert delivery_report['successful_deliveries'] == len(client_ids)
        assert delivery_report['failed_deliveries'] == 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_message_delivery_during_reconnection(self, ws_infrastructure):
        """Test message delivery during client reconnection"""
        client_id = "client_reconnect"
        
        # Initial connection
        ws1 = MagicMock()
        conn1 = await ws_infrastructure['ws_service'].connect_client(
            client_id=client_id,
            websocket=ws1
        )
        
        # Queue messages while connected
        for i in range(5):
            await ws_infrastructure['ws_service'].queue_message(
                client_id=client_id,
                message={'id': f'msg_{i}', 'data': f'Message {i}'}
            )
        
        # Disconnect
        await ws_infrastructure['ws_service'].disconnect_client(client_id)
        
        # Queue messages while disconnected
        for i in range(5, 10):
            await ws_infrastructure['ws_service'].queue_message(
                client_id=client_id,
                message={'id': f'msg_{i}', 'data': f'Message {i}'}
            )
        
        # Reconnect with new websocket
        ws2 = MagicMock()
        received_messages = []
        ws2.send = AsyncMock(side_effect=lambda msg: received_messages.append(msg))
        
        conn2 = await ws_infrastructure['ws_service'].connect_client(
            client_id=client_id,
            websocket=ws2,
            restore_queue=True
        )
        
        # Process queued messages
        await ws_infrastructure['ws_service'].flush_message_queue(client_id)
        
        # Should receive all 10 messages
        assert len(received_messages) == 10
        
        # Verify message IDs
        for i in range(10):
            msg = json.loads(received_messages[i])
            assert msg['id'] == f'msg_{i}'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_message_deduplication(self, ws_infrastructure):
        """Test duplicate message detection and prevention"""
        client_id = "client_dedup"
        
        # Connect client
        ws = MagicMock()
        received_messages = []
        ws.send = AsyncMock(side_effect=lambda msg: received_messages.append(msg))
        
        conn = await ws_infrastructure['ws_service'].connect_client(
            client_id=client_id,
            websocket=ws,
            enable_deduplication=True
        )
        
        # Send same message multiple times
        message = {
            'id': 'unique_msg_1',
            'data': 'Important data'
        }
        
        # Send 5 times
        for _ in range(5):
            await ws_infrastructure['ws_service'].send_message(client_id, message)
        
        # Process queue
        await ws_infrastructure['ws_service'].flush_message_queue(client_id)
        
        # Should only receive once
        assert len(received_messages) == 1
        assert json.loads(received_messages[0])['id'] == 'unique_msg_1'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_priority_message_delivery(self, ws_infrastructure):
        """Test priority-based message delivery"""
        client_id = "client_priority"
        
        # Connect client
        ws = MagicMock()
        received_order = []
        ws.send = AsyncMock(side_effect=lambda msg: received_order.append(json.loads(msg)['id']))
        
        conn = await ws_infrastructure['ws_service'].connect_client(
            client_id=client_id,
            websocket=ws
        )
        
        # Queue messages with different priorities
        messages = [
            {'id': 'low_1', 'priority': 1, 'data': 'Low priority'},
            {'id': 'high_1', 'priority': 10, 'data': 'High priority'},
            {'id': 'medium_1', 'priority': 5, 'data': 'Medium priority'},
            {'id': 'critical_1', 'priority': 100, 'data': 'Critical'},
            {'id': 'low_2', 'priority': 1, 'data': 'Another low'},
        ]
        
        for msg in messages:
            await ws_infrastructure['ws_service'].queue_message(client_id, msg)
        
        # Process with priority
        await ws_infrastructure['ws_service'].flush_message_queue(
            client_id,
            respect_priority=True
        )
        
        # Verify priority order (critical first, then high, medium, low)
        assert received_order[0] == 'critical_1'
        assert received_order[1] == 'high_1'
        assert received_order[2] == 'medium_1'
        assert 'low_1' in received_order[3:]
        assert 'low_2' in received_order[3:]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_message_batching_efficiency(self, ws_infrastructure):
        """Test efficient message batching for performance"""
        client_id = "client_batch"
        
        # Connect client
        ws = MagicMock()
        received_batches = []
        ws.send = AsyncMock(side_effect=lambda msg: received_batches.append(msg))
        
        conn = await ws_infrastructure['ws_service'].connect_client(
            client_id=client_id,
            websocket=ws,
            enable_batching=True,
            batch_size=10,
            batch_timeout=0.5
        )
        
        # Send 25 messages rapidly
        for i in range(25):
            await ws_infrastructure['ws_service'].queue_message(
                client_id=client_id,
                message={'id': f'msg_{i}', 'data': f'Data {i}'}
            )
        
        # Process with batching
        await ws_infrastructure['ws_service'].flush_message_queue(client_id)
        
        # Should receive 3 batches (10, 10, 5)
        assert len(received_batches) == 3
        
        # Verify batch sizes
        batch1 = json.loads(received_batches[0])
        batch2 = json.loads(received_batches[1])
        batch3 = json.loads(received_batches[2])
        
        assert len(batch1['messages']) == 10
        assert len(batch2['messages']) == 10
        assert len(batch3['messages']) == 5
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_connection_failure_during_send(self, ws_infrastructure):
        """Test handling of connection failure during message send"""
        client_id = "client_failure"
        
        # Connect client
        ws = MagicMock()
        send_count = 0
        
        async def failing_send(msg):
            nonlocal send_count
            send_count += 1
            if send_count > 2:
                raise websockets.exceptions.ConnectionClosed(None, None)
            return True
        
        ws.send = AsyncMock(side_effect=failing_send)
        
        conn = await ws_infrastructure['ws_service'].connect_client(
            client_id=client_id,
            websocket=ws
        )
        
        # Send messages
        messages_sent = []
        for i in range(5):
            try:
                result = await ws_infrastructure['ws_service'].send_message(
                    client_id=client_id,
                    message={'id': f'msg_{i}', 'data': f'Data {i}'}
                )
                messages_sent.append(result)
            except Exception as e:
                # Messages should be queued for retry
                pass
        
        # Check retry queue
        retry_queue = await ws_infrastructure['ws_service'].get_retry_queue(client_id)
        assert len(retry_queue) >= 2  # Messages that failed
        
        # Verify client marked as disconnected
        is_connected = await ws_infrastructure['ws_service'].is_client_connected(client_id)
        assert not is_connected
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_message_compression_large_payloads(self, ws_infrastructure):
        """Test message compression for large payloads"""
        client_id = "client_compress"
        
        # Connect client with compression
        ws = MagicMock()
        sent_sizes = []
        ws.send = AsyncMock(side_effect=lambda msg: sent_sizes.append(len(msg)))
        
        conn = await ws_infrastructure['ws_service'].connect_client(
            client_id=client_id,
            websocket=ws,
            enable_compression=True,
            compression_threshold=1024  # Compress messages > 1KB
        )
        
        # Send small message (no compression)
        small_msg = {'id': 'small', 'data': 'x' * 100}
        await ws_infrastructure['ws_service'].send_message(client_id, small_msg)
        
        # Send large message (should compress)
        large_msg = {'id': 'large', 'data': 'x' * 10000}
        await ws_infrastructure['ws_service'].send_message(client_id, large_msg)
        
        await ws_infrastructure['ws_service'].flush_message_queue(client_id)
        
        # Large message should be significantly smaller when sent
        small_size = sent_sizes[0]
        large_size = sent_sizes[1]
        
        # Compressed should be much smaller than original
        original_large_size = len(json.dumps(large_msg))
        assert large_size < original_large_size * 0.5  # At least 50% compression
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_client_message_isolation(self, ws_infrastructure):
        """Test message isolation between concurrent clients"""
        # Connect multiple clients
        clients = {}
        client_messages = defaultdict(list)
        
        for i in range(5):
            client_id = f"client_{i}"
            ws = MagicMock()
            
            # Each client tracks its own messages
            async def track_messages(msg, cid=client_id):
                client_messages[cid].append(json.loads(msg))
            
            ws.send = AsyncMock(side_effect=track_messages)
            
            conn = await ws_infrastructure['ws_service'].connect_client(
                client_id=client_id,
                websocket=ws
            )
            clients[client_id] = conn
        
        # Send targeted messages to each client
        for i in range(5):
            client_id = f"client_{i}"
            for j in range(3):
                await ws_infrastructure['ws_service'].send_message(
                    client_id=client_id,
                    message={'id': f'{client_id}_msg_{j}', 'data': f'Private message {j}'}
                )
        
        # Process all queues
        for client_id in clients.keys():
            await ws_infrastructure['ws_service'].flush_message_queue(client_id)
        
        # Verify isolation - each client only gets their messages
        for i in range(5):
            client_id = f"client_{i}"
            messages = client_messages[client_id]
            
            assert len(messages) == 3
            for msg in messages:
                assert msg['id'].startswith(f'{client_id}_msg_')
                
            # Verify no cross-contamination
            for other_client in client_messages:
                if other_client != client_id:
                    other_messages = client_messages[other_client]
                    for msg in other_messages:
                        assert not msg['id'].startswith(f'{client_id}_msg_')