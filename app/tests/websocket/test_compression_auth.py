"""
WebSocket compression and authentication testing module.
Tests compression algorithms, authentication expiry handling, and security features.
"""

import pytest
import asyncio
import json
import time
import uuid
import zlib
import random
from typing import Dict, Any, List
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_websocket_compression():
    """Test WebSocket compression with permessage-deflate extension"""
    
    # Test data that compresses well
    compressible_data = json.dumps({
        'repeated_field': 'A' * 1000,
        'array': [i % 10 for i in range(1000)],
        'nested': {'level1': {'level2': {'level3': 'value' * 100}}}
    })
    
    # Test compression ratios
    original_size = len(compressible_data.encode())
    compressed = zlib.compress(compressible_data.encode())
    compressed_size = len(compressed)
    compression_ratio = original_size / compressed_size
    
    assert compression_ratio > 5, f"Should achieve >5x compression, got {compression_ratio:.2f}x"
    
    # Simulate WebSocket with compression
    class CompressedWebSocket:
        def __init__(self, enable_compression=True):
            self.enable_compression = enable_compression
            self.bytes_sent = 0
            self.bytes_sent_raw = 0
            
        async def send(self, data: str):
            raw_bytes = data.encode()
            self.bytes_sent_raw += len(raw_bytes)
            
            if self.enable_compression:
                compressed = zlib.compress(raw_bytes)
                self.bytes_sent += len(compressed)
                return compressed
            else:
                self.bytes_sent += len(raw_bytes)
                return raw_bytes
        
        async def recv(self, data: bytes) -> str:
            if self.enable_compression:
                decompressed = zlib.decompress(data)
                return decompressed.decode()
            else:
                return data.decode()
    
    # Test with and without compression
    ws_compressed = CompressedWebSocket(enable_compression=True)
    ws_uncompressed = CompressedWebSocket(enable_compression=False)
    
    # Send multiple messages
    messages = [compressible_data] * 100
    
    for msg in messages:
        await ws_compressed.send(msg)
        await ws_uncompressed.send(msg)
    
    # Compare bandwidth usage
    compression_savings = 1 - (ws_compressed.bytes_sent / ws_uncompressed.bytes_sent)
    assert compression_savings > 0.7, f"Should save >70% bandwidth, saved {compression_savings:.1%}"
    
    # Test compression with different data types
    test_payloads = [
        # Already compressed data (shouldn't compress well)
        bytes(random.getrandbits(8) for _ in range(1000)),
        # Highly repetitive data (should compress very well)
        b'0' * 10000,
        # JSON with repeated structure
        json.dumps([{'id': i, 'type': 'event', 'status': 'active'} for i in range(100)]).encode(),
    ]
    
    for payload in test_payloads:
        original = len(payload)
        compressed = len(zlib.compress(payload))
        ratio = original / compressed if compressed > 0 else float('inf')
        
        # Different expectations based on data type
        if payload == b'0' * 10000:
            assert ratio > 100, "Highly repetitive data should compress >100x"
        elif isinstance(payload, bytes) and len(set(payload)) > 200:
            assert ratio < 1.5, "Random data shouldn't compress well"


class AuthenticatedWebSocket:
    def __init__(self, token: str, token_lifetime: int = 3600):
        self.token = token
        self.token_expires_at = time.time() + token_lifetime
        self.authenticated = True
        self.connection_alive = True
        self.messages_sent = 0
        self.reauthentication_attempts = 0

    def is_token_valid(self) -> bool:
        return time.time() < self.token_expires_at

    async def send_message(self, message: str) -> Dict:
        if not self.is_token_valid():
            return self._create_expired_token_response()
        return self._create_success_response()

    def _create_expired_token_response(self) -> Dict:
        self.authenticated = False
        return {
            'error': 'token_expired',
            'code': 401,
            'message': 'Authentication token has expired'
        }

    def _create_success_response(self) -> Dict:
        self.messages_sent += 1
        return {
            'success': True,
            'message_id': self.messages_sent,
            'timestamp': time.time()
        }

    async def refresh_token(self, new_token: str) -> bool:
        """Attempt to refresh authentication without closing connection"""
        self.reauthentication_attempts += 1
        if new_token and len(new_token) > 10:
            return self._apply_new_token(new_token)
        return False

    def _apply_new_token(self, new_token: str) -> bool:
        self.token = new_token
        self.token_expires_at = time.time() + 3600
        self.authenticated = True
        return True

    async def handle_auth_expiry(self) -> str:
        """Handle token expiry gracefully"""
        if not self.is_token_valid():
            return await self._attempt_reauthentication()
        return 'still_valid'

    async def _attempt_reauthentication(self) -> str:
        new_token = f"refreshed_token_{uuid.uuid4()}"
        success = await self.refresh_token(new_token)
        if success:
            return 'reauthenticated'
        self.connection_alive = False
        return 'connection_closed'


class GracePeriodWebSocket(AuthenticatedWebSocket):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grace_period = 30
        self.in_grace_period = False

    async def send_message(self, message: str) -> Dict:
        if not self.is_token_valid():
            return await self._handle_expired_token_with_grace()
        return await super().send_message(message)

    async def _handle_expired_token_with_grace(self) -> Dict:
        if not self.in_grace_period:
            return self._start_grace_period()
        elif time.time() < self.grace_expires_at:
            return self._create_grace_period_warning()
        return {'error': 'grace_period_expired', 'code': 401}

    def _start_grace_period(self) -> Dict:
        self.in_grace_period = True
        self.grace_expires_at = time.time() + self.grace_period
        return {
            'warning': 'token_expiring',
            'grace_period_seconds': self.grace_period,
            'action_required': 'refresh_token'
        }

    def _create_grace_period_warning(self) -> Dict:
        return {
            'warning': 'in_grace_period',
            'expires_in': int(self.grace_expires_at - time.time())
        }


@pytest.mark.asyncio
async def test_authentication_expiry_during_connection():
    """Test handling of authentication expiry while connection is active"""
    await _test_immediate_expiry()
    await _test_refresh_mechanism()
    await _test_longer_session()
    await _test_grace_period_handling()


async def _test_immediate_expiry():
    ws_short = AuthenticatedWebSocket('short_token', token_lifetime=1)
    await asyncio.sleep(1.1)
    result = await ws_short.send_message('test')
    assert result['error'] == 'token_expired'
    assert not ws_short.is_token_valid()


async def _test_refresh_mechanism():
    ws_short = AuthenticatedWebSocket('short_token', token_lifetime=1)
    await asyncio.sleep(1.1)
    reauth_result = await ws_short.handle_auth_expiry()
    assert reauth_result == 'reauthenticated'
    assert ws_short.authenticated
    assert ws_short.reauthentication_attempts == 1


async def _test_longer_session():
    ws_long = AuthenticatedWebSocket('long_token', token_lifetime=2)
    message_results = await _send_messages_over_time(ws_long)
    _verify_message_results(message_results)


async def _send_messages_over_time(ws_long) -> List[Dict]:
    message_results = []
    for i in range(5):
        result = await ws_long.send_message(f'Message {i}')
        message_results.append(result)
        await asyncio.sleep(0.5)
    return message_results


def _verify_message_results(message_results: List[Dict]):
    expired_messages = [r for r in message_results if 'error' in r]
    successful_messages = [r for r in message_results if 'success' in r]
    assert len(expired_messages) > 0, "Should have some expired messages"
    assert len(successful_messages) > 0, "Should have some successful messages"


async def _test_grace_period_handling():
    ws_grace = GracePeriodWebSocket('grace_token', token_lifetime=1)
    await asyncio.sleep(1.1)
    result1 = await ws_grace.send_message('test1')
    assert result1['warning'] == 'token_expiring'
    assert ws_grace.in_grace_period
    result2 = await ws_grace.send_message('test2')
    assert result2['warning'] == 'in_grace_period'
    assert result2['expires_in'] > 0