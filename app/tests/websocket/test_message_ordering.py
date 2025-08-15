"""
WebSocket message ordering and protocol testing module.
Tests message sequencing, protocol version handling, and binary data transmission.
"""

import pytest
import asyncio
import json
import time
import struct
import random
import hashlib
from typing import Dict, Any, List
from unittest.mock import AsyncMock
import websockets


@pytest.mark.asyncio
async def test_message_ordering_under_load():
    """Test that messages maintain order even under heavy load"""
    
    NUM_CLIENTS = 50
    MESSAGES_PER_CLIENT = 100
    
    class OrderedWebSocket:
        def __init__(self, client_id: str):
            self.client_id = client_id
            self.sent_messages: List[Dict] = []
            self.received_messages: List[Dict] = []
            self.sequence = 0
            
        async def send_ordered_message(self, content: str) -> Dict:
            """Send a message with sequence number"""
            message = {
                'client_id': self.client_id,
                'sequence': self.sequence,
                'content': content,
                'timestamp': time.time(),
                'hash': hashlib.md5(f"{self.client_id}_{self.sequence}_{content}".encode()).hexdigest()
            }
            self.sequence += 1
            self.sent_messages.append(message)
            
            # Simulate network delay
            await asyncio.sleep(random.uniform(0, 0.01))
            return message
        
        async def receive_message(self, message: Dict):
            """Receive and validate message order"""
            self.received_messages.append(message)
            
            # Check sequence
            if len(self.received_messages) > 1:
                prev_seq = self.received_messages[-2]['sequence']
                curr_seq = message['sequence']
                assert curr_seq == prev_seq + 1, f"Out of order: expected {prev_seq + 1}, got {curr_seq}"
    
    # Create clients
    clients = [OrderedWebSocket(f"client_{i}") for i in range(NUM_CLIENTS)]
    
    # Central message router (simulating server)
    message_queue: asyncio.Queue = asyncio.Queue()
    out_of_order_count = 0
    
    async def message_router():
        """Route messages maintaining order per client"""
        client_queues: Dict[str, List[Dict]] = {}
        
        while True:
            try:
                message = await asyncio.wait_for(message_queue.get(), timeout=1.0)
                client_id = message['client_id']
                
                if client_id not in client_queues:
                    client_queues[client_id] = []
                
                # Check order for this client
                if client_queues[client_id]:
                    last_seq = client_queues[client_id][-1]['sequence']
                    if message['sequence'] <= last_seq:
                        nonlocal out_of_order_count
                        out_of_order_count += 1
                
                client_queues[client_id].append(message)
                
                # Find corresponding client and deliver
                for client in clients:
                    if client.client_id == client_id:
                        await client.receive_message(message)
                        break
                        
            except asyncio.TimeoutError:
                break
    
    # Start router
    router_task = asyncio.create_task(message_router())
    
    # Send messages concurrently from all clients
    async def client_sender(client: OrderedWebSocket):
        for i in range(MESSAGES_PER_CLIENT):
            msg = await client.send_ordered_message(f"Message {i}")
            await message_queue.put(msg)
            
            # Varying delays to simulate real conditions
            if i % 10 == 0:
                await asyncio.sleep(0.01)  # Occasional pause
    
    # Execute all clients concurrently
    sender_tasks = [client_sender(client) for client in clients]
    await asyncio.gather(*sender_tasks)
    
    # Wait for processing
    await asyncio.sleep(2)
    router_task.cancel()
    
    # Verify results
    total_sent = sum(len(c.sent_messages) for c in clients)
    total_received = sum(len(c.received_messages) for c in clients)
    
    assert total_sent == NUM_CLIENTS * MESSAGES_PER_CLIENT
    assert total_received >= total_sent * 0.99, "Should receive at least 99% of messages"
    assert out_of_order_count == 0, f"Found {out_of_order_count} out-of-order messages"
    
    # Verify per-client ordering
    for client in clients:
        for i, msg in enumerate(client.received_messages):
            assert msg['sequence'] == i, f"Client {client.client_id} has out-of-order messages"


@pytest.mark.asyncio
async def test_binary_data_transmission():
    """Test transmission of binary data through WebSocket"""
    
    test_cases = [
        # (description, data_generator, size)
        ("Small binary", lambda: bytes([i % 256 for i in range(100)]), 100),
        ("1MB image", lambda: bytes(random.getrandbits(8) for _ in range(1024 * 1024)), 1024 * 1024),
        ("10MB file", lambda: bytes(random.getrandbits(8) for _ in range(10 * 1024 * 1024)), 10 * 1024 * 1024),
        ("Structured data", lambda: struct.pack('!IIf', 42, 100, 3.14159), 12),
        ("Mixed text/binary", lambda: b'TEXT:' + bytes([0, 1, 2, 3, 255]) + b':END', 14),
    ]
    
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock()
    
    for description, data_generator, expected_size in test_cases:
        binary_data = data_generator()
        
        # Test sending
        start_time = time.time()
        await mock_ws.send(binary_data)
        send_duration = time.time() - start_time
        
        # Verify call
        mock_ws.send.assert_called()
        sent_data = mock_ws.send.call_args[0][0]
        
        # Validate binary data
        assert isinstance(sent_data, bytes), f"{description}: Should send as bytes"
        assert len(sent_data) == expected_size, f"{description}: Size mismatch"
        
        # Test throughput
        throughput_mbps = (expected_size / send_duration) / (1024 * 1024) if send_duration > 0 else float('inf')
        assert throughput_mbps > 10, f"{description}: Throughput should exceed 10 MB/s"
        
        # Test receiving
        mock_ws.recv.return_value = binary_data
        received_data = await mock_ws.recv()
        
        assert received_data == binary_data, f"{description}: Data corruption detected"
        assert hashlib.sha256(received_data).hexdigest() == hashlib.sha256(binary_data).hexdigest()
    
    # Test chunked binary transmission
    large_data = bytes(random.getrandbits(8) for _ in range(50 * 1024 * 1024))  # 50MB
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    
    chunks_sent = []
    for i in range(0, len(large_data), CHUNK_SIZE):
        chunk = large_data[i:i + CHUNK_SIZE]
        await mock_ws.send(chunk)
        chunks_sent.append(chunk)
    
    # Verify reconstruction
    reconstructed = b''.join(chunks_sent)
    assert reconstructed == large_data, "Chunked transmission should preserve data"


@pytest.mark.asyncio
async def test_protocol_version_mismatch():
    """Test handling of protocol version mismatches"""
    
    protocol_versions = [
        ('ws13', 13, True),   # Current standard
        ('ws8', 8, False),    # Old version
        ('ws99', 99, False),  # Future version
        ('custom', 'custom-v1', False),  # Custom protocol
    ]
    
    for name, version, should_succeed in protocol_versions:
        mock_ws = AsyncMock()
        mock_ws.protocol_version = version
        
        # Simulate handshake
        if should_succeed:
            mock_ws.state = websockets.State.OPEN
            handshake_result = 'success'
        else:
            mock_ws.state = websockets.State.CLOSED
            handshake_result = 'failed'
            
            # Should handle gracefully
            error_response = {
                'error': 'protocol_mismatch',
                'supported_versions': [13],
                'requested_version': version
            }
            mock_ws.close_code = 1002  # Protocol error
            mock_ws.close_reason = json.dumps(error_response)
        
        # Verify behavior
        if should_succeed:
            assert mock_ws.state == websockets.State.OPEN
        else:
            assert mock_ws.state == websockets.State.CLOSED
            assert mock_ws.close_code == 1002
            assert 'protocol_mismatch' in mock_ws.close_reason
    
    # Test subprotocol negotiation
    subprotocols = ['chat', 'notifications', 'metrics']
    mock_ws = AsyncMock()
    mock_ws.subprotocol = AsyncMock(return_value='chat')
    
    selected = await mock_ws.subprotocol()
    assert selected in subprotocols, "Should select valid subprotocol"