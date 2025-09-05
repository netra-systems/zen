"""
L3 Integration Test: WebSocket Message Compression with Redis

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Efficiency - Reduce bandwidth costs for large messages
- Value Impact: Enables rich content sharing without performance degradation
- Strategic Impact: $60K MRR - Bandwidth optimization for enterprise features

L3 Test: Uses real Redis for message compression/decompression validation.
Compression target: 70%+ reduction for large payloads with <50ms processing time.
"""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import pytest
import asyncio
import json
import time
import gzip
import zlib
import base64
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

import redis.asyncio as redis
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas import User
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

from netra_backend.tests.integration.helpers.redis_l3_helpers import (

    RedisContainer, 

    MockWebSocketForRedis, 

    create_test_message

)

class MessageCompressor:

    """Handle message compression for WebSocket communications."""
    
    def __init__(self):

        self.compression_threshold = 1024  # Compress messages larger than 1KB

        self.compression_methods = {

            "gzip": self._gzip_compress,

            "zlib": self._zlib_compress,

            "none": self._no_compression

        }

        self.decompression_methods = {

            "gzip": self._gzip_decompress,

            "zlib": self._zlib_decompress,

            "none": self._no_decompression

        }
    
    def _gzip_compress(self, data: bytes) -> bytes:

        """Compress data using gzip."""

        return gzip.compress(data)
    
    def _gzip_decompress(self, data: bytes) -> bytes:

        """Decompress gzip data."""

        return gzip.decompress(data)
    
    def _zlib_compress(self, data: bytes) -> bytes:

        """Compress data using zlib."""

        return zlib.compress(data)
    
    def _zlib_decompress(self, data: bytes) -> bytes:

        """Decompress zlib data."""

        return zlib.decompress(data)
    
    def _no_compression(self, data: bytes) -> bytes:

        """No compression."""

        return data
    
    def _no_decompression(self, data: bytes) -> bytes:

        """No decompression."""

        return data
    
    def compress_message(self, message: Dict[str, Any], method: str = "gzip") -> Dict[str, Any]:

        """Compress a message if it exceeds threshold."""

        message_str = json.dumps(message)

        message_bytes = message_str.encode('utf-8')
        
        if len(message_bytes) < self.compression_threshold:

            return message
        
        if method not in self.compression_methods:

            method = "gzip"
        
        start_time = time.time()

        compressed_data = self.compression_methods[method](message_bytes)

        compression_time = time.time() - start_time
        
        compressed_message = {

            "compressed": True,

            "method": method,

            "data": base64.b64encode(compressed_data).decode('utf-8'),

            "original_size": len(message_bytes),

            "compressed_size": len(compressed_data),

            "compression_ratio": len(compressed_data) / len(message_bytes),

            "compression_time": compression_time,

            "metadata": message.get("metadata", {})

        }
        
        return compressed_message
    
    def decompress_message(self, compressed_message: Dict[str, Any]) -> Dict[str, Any]:

        """Decompress a compressed message."""

        if not compressed_message.get("compressed", False):

            return compressed_message
        
        method = compressed_message.get("method", "gzip")

        if method not in self.decompression_methods:

            raise ValueError(f"Unsupported compression method: {method}")
        
        compressed_data = base64.b64decode(compressed_message["data"].encode('utf-8'))
        
        start_time = time.time()

        decompressed_data = self.decompression_methods[method](compressed_data)

        decompression_time = time.time() - start_time
        
        original_message = json.loads(decompressed_data.decode('utf-8'))

        original_message["decompression_time"] = decompression_time
        
        return original_message

@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketMessageCompressionL3:

    """L3 integration tests for WebSocket message compression."""
    
    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for compression testing."""

        container = RedisContainer(port=6387)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    
    @pytest.fixture

    async def redis_client(self, redis_container):

        """Create Redis client for compressed message storage."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=False)  # Binary mode for compression

        yield client

        await client.close()
    
    @pytest.fixture

    async def websocket_manager(self, redis_container):

        """Create WebSocket manager for compression testing."""

        _, redis_url = redis_container
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('netra_backend.app.websocket_manager.redis_manager') as mock_redis_mgr:

            test_redis_mgr = RedisManager()

            test_redis_mgr.enabled = True

            test_redis_mgr.redis_client = redis.Redis.from_url(redis_url, decode_responses=False)

            mock_redis_mgr.return_value = test_redis_mgr

            mock_redis_mgr.get_client.return_value = test_redis_mgr.redis_client
            
            manager = WebSocketManager()

            yield manager
            
            await test_redis_mgr.redis_client.close()
    
    @pytest.fixture

    def message_compressor(self):

        """Create message compressor instance."""

        return MessageCompressor()
    
    @pytest.fixture

    def test_users(self):

        """Create test users for compression testing."""

        return [

            User(

                id=f"compress_user_{i}",

                email=f"compressuser{i}@example.com", 

                username=f"compressuser{i}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(3)

        ]
    
    def create_large_message(self, size_kb: int = 5) -> Dict[str, Any]:

        """Create a large message for compression testing."""

        large_content = "x" * (size_kb * 1024)  # Create content of specified size
        
        return create_test_message(

            "large_message",

            "system",

            {

                "large_content": large_content,

                "metadata": {

                    "size_kb": size_kb,

                    "created_at": time.time(),

                    "test_data": {f"field_{i}": f"value_{i}" for i in range(100)}

                }

            }

        )
    
    @pytest.mark.asyncio
    async def test_basic_message_compression(self, message_compressor):

        """Test basic message compression and decompression."""
        # Create large message

        large_message = self.create_large_message(5)  # 5KB message

        original_size = len(json.dumps(large_message).encode('utf-8'))
        
        # Compress message

        compressed_message = message_compressor.compress_message(large_message, "gzip")
        
        # Verify compression

        assert compressed_message["compressed"] is True

        assert compressed_message["method"] == "gzip"

        assert compressed_message["original_size"] == original_size

        assert compressed_message["compressed_size"] < original_size

        assert compressed_message["compression_ratio"] < 1.0

        assert compressed_message["compression_time"] < 0.1  # Should be fast
        
        # Test compression ratio

        compression_ratio = compressed_message["compression_ratio"]

        assert compression_ratio < 0.3  # At least 70% compression for repetitive data
        
        # Decompress message

        decompressed_message = message_compressor.decompress_message(compressed_message)
        
        # Verify decompression

        assert decompressed_message["type"] == large_message["type"]

        assert decompressed_message["data"]["large_content"] == large_message["data"]["large_content"]

        assert decompressed_message["decompression_time"] < 0.1  # Should be fast
    
    @pytest.mark.asyncio
    async def test_compression_methods_comparison(self, message_compressor):

        """Test different compression methods."""

        large_message = self.create_large_message(10)  # 10KB message

        methods = ["gzip", "zlib"]

        compression_results = {}
        
        for method in methods:
            # Compress with each method

            compressed = message_compressor.compress_message(large_message, method)
            
            # Store results

            compression_results[method] = {

                "compression_ratio": compressed["compression_ratio"],

                "compression_time": compressed["compression_time"],

                "compressed_size": compressed["compressed_size"]

            }
            
            # Verify decompression works

            decompressed = message_compressor.decompress_message(compressed)

            assert decompressed["type"] == large_message["type"]
        
        # Compare compression efficiency

        gzip_ratio = compression_results["gzip"]["compression_ratio"]

        zlib_ratio = compression_results["zlib"]["compression_ratio"]
        
        # Both should achieve good compression

        assert gzip_ratio < 0.5  # At least 50% compression

        assert zlib_ratio < 0.5  # At least 50% compression
        
        # Performance should be reasonable

        assert compression_results["gzip"]["compression_time"] < 0.2

        assert compression_results["zlib"]["compression_time"] < 0.2
    
    @pytest.mark.asyncio
    async def test_compression_threshold_handling(self, message_compressor):

        """Test compression threshold behavior."""
        # Small message (below threshold)

        small_message = create_test_message("small", "system", {"content": "small"})

        compressed_small = message_compressor.compress_message(small_message)
        
        # Should not be compressed

        assert "compressed" not in compressed_small or compressed_small.get("compressed") is False

        assert compressed_small == small_message
        
        # Large message (above threshold)

        large_message = self.create_large_message(2)  # 2KB message

        compressed_large = message_compressor.compress_message(large_message)
        
        # Should be compressed

        assert compressed_large["compressed"] is True

        assert compressed_large["original_size"] > message_compressor.compression_threshold
    
    @pytest.mark.asyncio
    async def test_compressed_message_redis_storage(self, redis_client, message_compressor, test_users):

        """Test storing and retrieving compressed messages in Redis."""

        user = test_users[0]

        large_message = self.create_large_message(8)  # 8KB message
        
        # Compress message

        compressed_message = message_compressor.compress_message(large_message, "gzip")
        
        # Store in Redis

        message_key = f"compressed_message:{user.id}:{uuid4()}"

        compressed_data = json.dumps(compressed_message).encode('utf-8')

        await redis_client.set(message_key, compressed_data, ex=3600)
        
        # Retrieve from Redis

        stored_data = await redis_client.get(message_key)

        retrieved_message = json.loads(stored_data.decode('utf-8'))
        
        # Verify retrieval

        assert retrieved_message["compressed"] is True

        assert retrieved_message["method"] == "gzip"

        assert retrieved_message["original_size"] == compressed_message["original_size"]
        
        # Decompress retrieved message

        decompressed = message_compressor.decompress_message(retrieved_message)
        
        # Verify content integrity

        assert decompressed["data"]["large_content"] == large_message["data"]["large_content"]
        
        # Cleanup

        await redis_client.delete(message_key)
    
    @pytest.mark.asyncio
    async def test_websocket_compression_integration(self, websocket_manager, redis_client, message_compressor, test_users):

        """Test compression integration with WebSocket messaging."""

        user = test_users[0]

        websocket = MockWebSocketForRedis(user.id)
        
        # Connect user

        connection_info = await websocket_manager.connect_user(user.id, websocket)

        assert connection_info is not None
        
        # Create large message

        large_message = self.create_large_message(6)  # 6KB message
        
        # Compress message

        compressed_message = message_compressor.compress_message(large_message, "gzip")
        
        # Send compressed message through WebSocket system

        channel = f"user:{user.id}"

        message_data = json.dumps(compressed_message).encode('utf-8')
        
        # Store and publish compressed message

        message_id = str(uuid4())

        storage_key = f"ws_compressed:{message_id}"

        await redis_client.set(storage_key, message_data, ex=600)
        
        # Publish notification of compressed message

        notification = {

            "type": "compressed_message",

            "message_id": message_id,

            "storage_key": storage_key,

            "compression_info": {

                "method": compressed_message["method"],

                "compression_ratio": compressed_message["compression_ratio"]

            }

        }
        
        await redis_client.publish(channel, json.dumps(notification))
        
        # Simulate receiving and decompressing

        stored_compressed = await redis_client.get(storage_key)

        retrieved_compressed = json.loads(stored_compressed.decode('utf-8'))
        
        # Decompress and verify

        final_message = message_compressor.decompress_message(retrieved_compressed)

        assert final_message["data"]["large_content"] == large_message["data"]["large_content"]
        
        # Cleanup

        await websocket_manager.disconnect_user(user.id, websocket)

        await redis_client.delete(storage_key)
    
    @pytest.mark.asyncio
    async def test_compression_performance_under_load(self, message_compressor):

        """Test compression performance with multiple concurrent operations."""

        message_count = 50

        message_size_kb = 5
        
        # Create multiple large messages

        messages = [self.create_large_message(message_size_kb) for _ in range(message_count)]
        
        # Compress all messages concurrently

        compression_start = time.time()

        compression_tasks = []
        
        for message in messages:
            # Use asyncio to simulate concurrent compression

            task = asyncio.create_task(asyncio.to_thread(

                message_compressor.compress_message, message, "gzip"

            ))

            compression_tasks.append(task)
        
        compressed_messages = await asyncio.gather(*compression_tasks)

        compression_time = time.time() - compression_start
        
        # Verify compression results

        successful_compressions = 0

        total_compression_ratio = 0
        
        for compressed in compressed_messages:

            if compressed.get("compressed", False):

                successful_compressions += 1

                total_compression_ratio += compressed["compression_ratio"]
        
        avg_compression_ratio = total_compression_ratio / successful_compressions
        
        # Performance assertions

        assert compression_time < 5.0  # All compressions within 5 seconds

        assert successful_compressions >= message_count * 0.95  # 95% success rate

        assert avg_compression_ratio < 0.4  # Average 60%+ compression
        
        # Test decompression performance

        decompression_start = time.time()

        decompression_tasks = []
        
        for compressed in compressed_messages:

            if compressed.get("compressed", False):

                task = asyncio.create_task(asyncio.to_thread(

                    message_compressor.decompress_message, compressed

                ))

                decompression_tasks.append(task)
        
        decompressed_messages = await asyncio.gather(*decompression_tasks, return_exceptions=True)

        decompression_time = time.time() - decompression_start
        
        successful_decompressions = sum(1 for msg in decompressed_messages 

                                      if not isinstance(msg, Exception))
        
        # Decompression performance assertions

        assert decompression_time < 3.0  # Decompression should be faster

        assert successful_decompressions >= len(decompression_tasks) * 0.95  # 95% success rate
    
    @pytest.mark.asyncio
    async def test_compression_bandwidth_savings(self, redis_client, message_compressor, test_users):

        """Test bandwidth savings from message compression."""

        user = test_users[0]

        test_scenarios = [

            {"size_kb": 2, "expected_savings": 0.3},   # Small files

            {"size_kb": 10, "expected_savings": 0.7},  # Medium files  

            {"size_kb": 50, "expected_savings": 0.8}   # Large files

        ]
        
        total_original_size = 0

        total_compressed_size = 0

        bandwidth_savings = []
        
        for scenario in test_scenarios:
            # Create message of specified size

            large_message = self.create_large_message(scenario["size_kb"])

            original_data = json.dumps(large_message).encode('utf-8')

            original_size = len(original_data)
            
            # Compress message

            compressed_message = message_compressor.compress_message(large_message, "gzip")

            compressed_data = json.dumps(compressed_message).encode('utf-8')

            compressed_size = len(compressed_data)
            
            # Calculate savings

            savings_ratio = 1 - (compressed_size / original_size)

            bandwidth_savings.append(savings_ratio)
            
            total_original_size += original_size

            total_compressed_size += compressed_size
            
            # Store both versions in Redis for comparison

            original_key = f"original:{user.id}:{scenario['size_kb']}kb"

            compressed_key = f"compressed:{user.id}:{scenario['size_kb']}kb"
            
            await redis_client.set(original_key, original_data, ex=300)

            await redis_client.set(compressed_key, compressed_data, ex=300)
            
            # Verify expected savings threshold

            assert savings_ratio >= scenario["expected_savings"]
            
            # Cleanup

            await redis_client.delete(original_key, compressed_key)
        
        # Overall bandwidth savings

        overall_savings = 1 - (total_compressed_size / total_original_size)

        avg_savings = sum(bandwidth_savings) / len(bandwidth_savings)
        
        # Business value assertions

        assert overall_savings >= 0.6  # At least 60% bandwidth savings

        assert avg_savings >= 0.6      # Consistent savings across scenarios

        assert min(bandwidth_savings) >= 0.3  # Even small files save 30%

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])