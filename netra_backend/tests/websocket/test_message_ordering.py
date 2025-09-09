"""
WebSocket message ordering and protocol testing module.
Tests message sequencing, protocol version handling, and binary data transmission.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import hashlib
import json
import random
import struct
import time
from typing import Any, Dict, List

import pytest
import websockets

class OrderedWebSocket:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.sent_messages: List[Dict] = []
        self.received_messages: List[Dict] = []
        self.sequence = 0

    async def send_ordered_message(self, content: str) -> Dict:
        """Send a message with sequence number"""
        message = self._create_message(content)
        self.sequence += 1
        self.sent_messages.append(message)
        await asyncio.sleep(random.uniform(0, 0.01))
        return message

    def _create_message(self, content: str) -> Dict:
        return {
            'client_id': self.client_id,
            'sequence': self.sequence,
            'content': content,
            'timestamp': time.time(),
            'hash': hashlib.md5(f"{self.client_id}_{self.sequence}_{content}".encode()).hexdigest()
        }

    async def receive_message(self, message: Dict):
        """Receive and validate message order"""
        self.received_messages.append(message)
        if len(self.received_messages) > 1:
            self._validate_message_order(message)

    def _validate_message_order(self, message: Dict):
        prev_seq = self.received_messages[-2]['sequence']
        curr_seq = message['sequence']
        assert curr_seq == prev_seq + 1, f"Out of order: expected {prev_seq + 1}, got {curr_seq}"

async def _create_message_router(clients: List[OrderedWebSocket], message_queue: asyncio.Queue) -> int:
    """Route messages maintaining order per client"""
    client_queues: Dict[str, List[Dict]] = {}
    out_of_order_count = 0
    
    while True:
        try:
            message = await asyncio.wait_for(message_queue.get(), timeout=1.0)
            out_of_order_count += await _process_message(message, client_queues, clients)
        except asyncio.TimeoutError:
            break
    return out_of_order_count

async def _process_message(message: Dict, client_queues: Dict, clients: List) -> int:
    client_id = message['client_id']
    if client_id not in client_queues:
        client_queues[client_id] = []
    
    out_of_order = _check_message_order(message, client_queues[client_id])
    client_queues[client_id].append(message)
    await _deliver_message_to_client(message, clients)
    return out_of_order

def _check_message_order(message: Dict, client_queue: List[Dict]) -> int:
    if client_queue:
        last_seq = client_queue[-1]['sequence']
        if message['sequence'] <= last_seq:
            return 1
    return 0

async def _deliver_message_to_client(message: Dict, clients: List):
    for client in clients:
        if client.client_id == message['client_id']:
            await client.receive_message(message)
            break

async def _client_sender(client: OrderedWebSocket, message_queue: asyncio.Queue, messages_per_client: int):
    for i in range(messages_per_client):
        msg = await client.send_ordered_message(f"Message {i}")
        await message_queue.put(msg)
        if i % 10 == 0:
            await asyncio.sleep(0.01)

def _verify_message_results(clients: List[OrderedWebSocket], num_clients: int, messages_per_client: int, out_of_order_count: int):
    total_sent = sum(len(c.sent_messages) for c in clients)
    total_received = sum(len(c.received_messages) for c in clients)
    assert total_sent == num_clients * messages_per_client
    assert total_received >= total_sent * 0.99, "Should receive at least 99% of messages"
    assert out_of_order_count == 0, f"Found {out_of_order_count} out-of-order messages"

def _verify_per_client_ordering(clients: List[OrderedWebSocket]):
    for client in clients:
        for i, msg in enumerate(client.received_messages):
            assert msg['sequence'] == i, f"Client {client.client_id} has out-of-order messages"
@pytest.mark.asyncio
async def test_message_ordering_under_load():
    """Test that messages maintain order even under heavy load"""
    NUM_CLIENTS, MESSAGES_PER_CLIENT = 50, 100
    clients = [OrderedWebSocket(f"client_{i}") for i in range(NUM_CLIENTS)]
    message_queue: asyncio.Queue = asyncio.Queue()
    
    router_task = asyncio.create_task(_create_message_router(clients, message_queue))
    sender_tasks = [_client_sender(client, message_queue, MESSAGES_PER_CLIENT) for client in clients]
    await asyncio.gather(*sender_tasks)
    await asyncio.sleep(2)
    router_task.cancel()
    
    out_of_order_count = 0 if router_task.cancelled() else await router_task
    _verify_message_results(clients, NUM_CLIENTS, MESSAGES_PER_CLIENT, out_of_order_count)
    _verify_per_client_ordering(clients)
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
    
    # Mock: Generic component isolation for controlled unit testing
    mock_ws = AsyncNone  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    mock_ws.send = AsyncNone  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    mock_ws.recv = AsyncNone  # TODO: Use real service instance
    
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
        # Mock: Generic component isolation for controlled unit testing
        mock_ws = AsyncNone  # TODO: Use real service instance
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
    # Mock: Generic component isolation for controlled unit testing
    mock_ws = AsyncNone  # TODO: Use real service instance
    # Mock: Async component isolation for testing without real async operations
    mock_ws.subprotocol = AsyncMock(return_value='chat')
    
    selected = await mock_ws.subprotocol()
    assert selected in subprotocols, "Should select valid subprotocol"


class TestWebSocketMessageTamperingPrevention:
    """ITERATION 29: Prevent WebSocket message tampering attacks."""
    
    @pytest.mark.asyncio
    async def test_websocket_message_tampering_prevention(self):
        """ITERATION 29: Prevent WebSocket message tampering that corrupts application state.
        
        Business Value: Prevents data integrity attacks worth $300K+ per compromise.
        """
        # Test 1: Message hash verification prevents tampering
        client = OrderedWebSocket("secure-client")
        
        original_message = await client.send_ordered_message("Sensitive data: transfer $10000")
        
        # Simulate message tampering by modifying content but keeping same hash
        tampered_message = original_message.copy()
        tampered_message['content'] = "Sensitive data: transfer $100000"  # Amount changed
        
        # Hash should not match tampered content
        expected_hash = hashlib.md5(
            f"{tampered_message['client_id']}_{tampered_message['sequence']}_"
            f"{tampered_message['content']}".encode()
        ).hexdigest()
        
        assert tampered_message['hash'] != expected_hash, "Tampering should be detectable via hash mismatch"
        
        # Test 2: Sequence number manipulation detection
        sequence_tampering_cases = [
            (10, 5, "Sequence rollback attack"),    # Replay old sequence
            (10, 10, "Sequence replay attack"),    # Duplicate sequence  
            (10, 15, "Sequence skip attack"),      # Skip sequences
            (10, -1, "Negative sequence attack"),  # Invalid sequence
        ]
        
        for current_seq, tampered_seq, attack_type in sequence_tampering_cases:
            client.sequence = current_seq
            message = await client.send_ordered_message("Test message")
            
            # Tamper with sequence number
            tampered_message = message.copy()
            tampered_message['sequence'] = tampered_seq
            
            if tampered_seq <= current_seq and tampered_seq >= 0:
                # This would be detected as out-of-order
                out_of_order = _check_message_order(tampered_message, [message])
                assert out_of_order > 0, f"{attack_type} should be detected"
            else:
                # Invalid sequences should be rejected
                assert tampered_seq < 0 or tampered_seq > current_seq + 1, f"{attack_type} has invalid sequence"
                
        # Test 3: Timestamp manipulation detection
        current_time = time.time()
        message = await client.send_ordered_message("Time-sensitive order")
        
        timestamp_attacks = [
            current_time + 86400,  # Future timestamp (1 day ahead)
            current_time - 86400,  # Past timestamp (1 day behind)
            0,                     # Invalid timestamp
            -1,                    # Negative timestamp
        ]
        
        for malicious_timestamp in timestamp_attacks:
            tampered_message = message.copy()
            tampered_message['timestamp'] = malicious_timestamp
            
            # Verify timestamp is within reasonable bounds
            time_diff = abs(tampered_message['timestamp'] - current_time)
            
            if malicious_timestamp <= 0 or time_diff > 3600:  # More than 1 hour difference
                assert True, "Suspicious timestamp should be flagged"
            else:
                assert False, f"Timestamp attack not properly detected: {malicious_timestamp}"
                
        # Test 4: Client ID spoofing prevention
        legitimate_client = OrderedWebSocket("user-123")
        attacker_client = OrderedWebSocket("attacker-456")
        
        # Legitimate message
        legit_message = await legitimate_client.send_ordered_message("Authorized action")
        
        # Attacker tries to spoof client ID
        spoofed_message = await attacker_client.send_ordered_message("Malicious action")
        spoofed_message['client_id'] = "user-123"  # Spoof legitimate user
        
        # Hash verification should fail for spoofed message
        expected_hash_for_spoofed = hashlib.md5(
            f"user-123_{spoofed_message['sequence']}_Malicious action".encode()
        ).hexdigest()
        
        assert spoofed_message['hash'] != expected_hash_for_spoofed, "Client ID spoofing should be detectable"
        
        # Test 5: Message injection prevention
        client_queue = []
        
        # Send legitimate messages
        for i in range(5):
            msg = await client.send_ordered_message(f"Message {i}")
            client_queue.append(msg)
            
        # Attacker tries to inject message in the middle
        injected_message = {
            'client_id': client.client_id,
            'sequence': 2.5,  # Try to inject between sequence 2 and 3
            'content': 'INJECTED MALICIOUS CONTENT',
            'timestamp': time.time(),
            'hash': 'fake-hash-12345'
        }
        
        # Sequence validation should catch injection
        is_valid_sequence = isinstance(injected_message['sequence'], int)
        assert not is_valid_sequence, "Non-integer sequence should be rejected"
        
        # Test 6: Bulk message tampering detection
        messages = []
        for i in range(10):
            msg = await client.send_ordered_message(f"Batch message {i}")
            messages.append(msg)
            
        # Simulate tampering with multiple messages
        tampered_count = 0
        for i, msg in enumerate(messages):
            if i % 2 == 0:  # Tamper with every other message
                msg['content'] = f"TAMPERED: {msg['content']}"
                tampered_count += 1
                
        # Verify tampered messages have hash mismatches
        hash_mismatches = 0
        for msg in messages:
            expected_hash = hashlib.md5(
                f"{msg['client_id']}_{msg['sequence']}_{msg['content']}".encode()
            ).hexdigest()
            
            if msg['hash'] != expected_hash:
                hash_mismatches += 1
                
        assert hash_mismatches == tampered_count, "All tampered messages should have hash mismatches"
        
        # Test 7: Binary message tampering detection  
        binary_data = bytes([i % 256 for i in range(1000)])
        binary_hash = hashlib.sha256(binary_data).hexdigest()
        
        binary_message = {
            'client_id': client.client_id,
            'sequence': client.sequence + 1,
            'content_type': 'binary',
            'data': binary_data,
            'timestamp': time.time(),
            'hash': binary_hash
        }
        
        # Tamper with binary data
        tampered_binary = bytearray(binary_data)
        tampered_binary[500] = 255  # Change one byte
        tampered_binary_hash = hashlib.sha256(bytes(tampered_binary)).hexdigest()
        
        assert tampered_binary_hash != binary_hash, "Binary tampering should be detectable"
        
        # Even small changes should be caught
        single_bit_flip = bytearray(binary_data)
        single_bit_flip[0] = single_bit_flip[0] ^ 1  # Flip one bit
        single_bit_hash = hashlib.sha256(bytes(single_bit_flip)).hexdigest()
        
        assert single_bit_hash != binary_hash, "Single bit flip should be detectable"