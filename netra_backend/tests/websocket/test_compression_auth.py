"""
WebSocket compression and authentication testing module.
Tests compression algorithms, authentication expiry handling, and security features.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
import random
import time
import uuid
import zlib
from typing import Any, Dict, List

import pytest

def _create_compressible_test_data() -> str:
    """Create test data that compresses well"""
    return json.dumps({
        'repeated_field': 'A' * 1000,
        'array': [i % 10 for i in range(1000)],
        'nested': {'level1': {'level2': {'level3': 'value' * 100}}}
    })

def _verify_compression_ratio(data: str) -> None:
    """Verify compression achieves expected ratio"""
    original_size = len(data.encode())
    compressed = zlib.compress(data.encode())
    compressed_size = len(compressed)
    compression_ratio = original_size / compressed_size
    assert compression_ratio > 5, f"Should achieve >5x compression, got {compression_ratio:.2f}x"

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

async def _send_test_messages(ws_compressed: CompressedWebSocket, ws_uncompressed: CompressedWebSocket, data: str) -> None:
    """Send test messages to both compressed and uncompressed websockets"""
    messages = [data] * 100
    for msg in messages:
        await ws_compressed.send(msg)
        await ws_uncompressed.send(msg)

def _verify_bandwidth_savings(ws_compressed: CompressedWebSocket, ws_uncompressed: CompressedWebSocket) -> None:
    """Verify bandwidth savings meet expectations"""
    compression_savings = 1 - (ws_compressed.bytes_sent / ws_uncompressed.bytes_sent)
    assert compression_savings > 0.7, f"Should save >70% bandwidth, saved {compression_savings:.1%}"

def _create_test_payloads() -> List[bytes]:
    """Create different types of test payloads"""
    return [
        bytes(random.getrandbits(8) for _ in range(1000)),
        b'0' * 10000,
        json.dumps([{'id': i, 'type': 'event', 'status': 'active'} for i in range(100)]).encode(),
    ]

def _verify_payload_compression(payload: bytes) -> None:
    """Verify payload compression ratios"""
    original = len(payload)
    compressed = len(zlib.compress(payload))
    ratio = original / compressed if compressed > 0 else float('inf')
    if payload == b'0' * 10000:
        assert ratio > 100, "Highly repetitive data should compress >100x"
    elif isinstance(payload, bytes) and len(set(payload)) > 200:
        assert ratio < 1.5, "Random data shouldn't compress well"

@pytest.mark.asyncio
async def test_websocket_compression():
    """Test WebSocket compression with permessage-deflate extension"""
    compressible_data = _create_compressible_test_data()
    _verify_compression_ratio(compressible_data)
    ws_compressed = CompressedWebSocket(enable_compression=True)
    ws_uncompressed = CompressedWebSocket(enable_compression=False)
    await _send_test_messages(ws_compressed, ws_uncompressed, compressible_data)
    _verify_bandwidth_savings(ws_compressed, ws_uncompressed)
    test_payloads = _create_test_payloads()
    for payload in test_payloads:
        _verify_payload_compression(payload)

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