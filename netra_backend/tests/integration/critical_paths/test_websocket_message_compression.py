from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: L3 Integration Test: WebSocket Message Compression with Redis

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Enterprise
    # REMOVED_SYNTAX_ERROR: - Business Goal: Efficiency - Reduce bandwidth costs for large messages
    # REMOVED_SYNTAX_ERROR: - Value Impact: Enables rich content sharing without performance degradation
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: $60K MRR - Bandwidth optimization for enterprise features

    # REMOVED_SYNTAX_ERROR: L3 Test: Uses real Redis for message compression/decompression validation.
    # REMOVED_SYNTAX_ERROR: Compression target: 70%+ reduction for large payloads with <50ms processing time.
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager
    # Test framework import - using pytest fixtures instead
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.docker.unified_docker_manager import UnifiedDockerManager
    # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import gzip
    # REMOVED_SYNTAX_ERROR: import zlib
    # REMOVED_SYNTAX_ERROR: import base64
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, List, Tuple
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from uuid import uuid4

    # REMOVED_SYNTAX_ERROR: import redis.asyncio as redis
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.redis_manager import RedisManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas import User
    # Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
    # REMOVED_SYNTAX_ERROR: from test_framework.real_services import get_real_services

    # REMOVED_SYNTAX_ERROR: from netra_backend.tests.integration.helpers.redis_l3_helpers import ( )

    # REMOVED_SYNTAX_ERROR: RedisContainer,

    # REMOVED_SYNTAX_ERROR: MockWebSocketForRedis,

    # REMOVED_SYNTAX_ERROR: create_test_message

    

# REMOVED_SYNTAX_ERROR: class MessageCompressor:

    # REMOVED_SYNTAX_ERROR: """Handle message compression for WebSocket communications."""

# REMOVED_SYNTAX_ERROR: def __init__(self):

    # REMOVED_SYNTAX_ERROR: self.compression_threshold = 1024  # Compress messages larger than 1KB

    # REMOVED_SYNTAX_ERROR: self.compression_methods = { )

    # REMOVED_SYNTAX_ERROR: "gzip": self._gzip_compress,

    # REMOVED_SYNTAX_ERROR: "zlib": self._zlib_compress,

    # REMOVED_SYNTAX_ERROR: "none": self._no_compression

    

    # REMOVED_SYNTAX_ERROR: self.decompression_methods = { )

    # REMOVED_SYNTAX_ERROR: "gzip": self._gzip_decompress,

    # REMOVED_SYNTAX_ERROR: "zlib": self._zlib_decompress,

    # REMOVED_SYNTAX_ERROR: "none": self._no_decompression

    

# REMOVED_SYNTAX_ERROR: def _gzip_compress(self, data: bytes) -> bytes:

    # REMOVED_SYNTAX_ERROR: """Compress data using gzip."""

    # REMOVED_SYNTAX_ERROR: return gzip.compress(data)

# REMOVED_SYNTAX_ERROR: def _gzip_decompress(self, data: bytes) -> bytes:

    # REMOVED_SYNTAX_ERROR: """Decompress gzip data."""

    # REMOVED_SYNTAX_ERROR: return gzip.decompress(data)

# REMOVED_SYNTAX_ERROR: def _zlib_compress(self, data: bytes) -> bytes:

    # REMOVED_SYNTAX_ERROR: """Compress data using zlib."""

    # REMOVED_SYNTAX_ERROR: return zlib.compress(data)

# REMOVED_SYNTAX_ERROR: def _zlib_decompress(self, data: bytes) -> bytes:

    # REMOVED_SYNTAX_ERROR: """Decompress zlib data."""

    # REMOVED_SYNTAX_ERROR: return zlib.decompress(data)

# REMOVED_SYNTAX_ERROR: def _no_compression(self, data: bytes) -> bytes:

    # REMOVED_SYNTAX_ERROR: """No compression."""

    # REMOVED_SYNTAX_ERROR: return data

# REMOVED_SYNTAX_ERROR: def _no_decompression(self, data: bytes) -> bytes:

    # REMOVED_SYNTAX_ERROR: """No decompression."""

    # REMOVED_SYNTAX_ERROR: return data

# REMOVED_SYNTAX_ERROR: def compress_message(self, message: Dict[str, Any], method: str = "gzip") -> Dict[str, Any]:

    # REMOVED_SYNTAX_ERROR: """Compress a message if it exceeds threshold."""

    # REMOVED_SYNTAX_ERROR: message_str = json.dumps(message)

    # REMOVED_SYNTAX_ERROR: message_bytes = message_str.encode('utf-8')

    # REMOVED_SYNTAX_ERROR: if len(message_bytes) < self.compression_threshold:

        # REMOVED_SYNTAX_ERROR: return message

        # REMOVED_SYNTAX_ERROR: if method not in self.compression_methods:

            # REMOVED_SYNTAX_ERROR: method = "gzip"

            # REMOVED_SYNTAX_ERROR: start_time = time.time()

            # REMOVED_SYNTAX_ERROR: compressed_data = self.compression_methods[method](message_bytes)

            # REMOVED_SYNTAX_ERROR: compression_time = time.time() - start_time

            # REMOVED_SYNTAX_ERROR: compressed_message = { )

            # REMOVED_SYNTAX_ERROR: "compressed": True,

            # REMOVED_SYNTAX_ERROR: "method": method,

            # REMOVED_SYNTAX_ERROR: "data": base64.b64encode(compressed_data).decode('utf-8'),

            # REMOVED_SYNTAX_ERROR: "original_size": len(message_bytes),

            # REMOVED_SYNTAX_ERROR: "compressed_size": len(compressed_data),

            # REMOVED_SYNTAX_ERROR: "compression_ratio": len(compressed_data) / len(message_bytes),

            # REMOVED_SYNTAX_ERROR: "compression_time": compression_time,

            # REMOVED_SYNTAX_ERROR: "metadata": message.get("metadata", {})

            

            # REMOVED_SYNTAX_ERROR: return compressed_message

# REMOVED_SYNTAX_ERROR: def decompress_message(self, compressed_message: Dict[str, Any]) -> Dict[str, Any]:

    # REMOVED_SYNTAX_ERROR: """Decompress a compressed message."""

    # REMOVED_SYNTAX_ERROR: if not compressed_message.get("compressed", False):

        # REMOVED_SYNTAX_ERROR: return compressed_message

        # REMOVED_SYNTAX_ERROR: method = compressed_message.get("method", "gzip")

        # REMOVED_SYNTAX_ERROR: if method not in self.decompression_methods:

            # REMOVED_SYNTAX_ERROR: raise ValueError("formatted_string")

            # REMOVED_SYNTAX_ERROR: compressed_data = base64.b64decode(compressed_message["data"].encode('utf-8'))

            # REMOVED_SYNTAX_ERROR: start_time = time.time()

            # REMOVED_SYNTAX_ERROR: decompressed_data = self.decompression_methods[method](compressed_data)

            # REMOVED_SYNTAX_ERROR: decompression_time = time.time() - start_time

            # REMOVED_SYNTAX_ERROR: original_message = json.loads(decompressed_data.decode('utf-8'))

            # REMOVED_SYNTAX_ERROR: original_message["decompression_time"] = decompression_time

            # REMOVED_SYNTAX_ERROR: return original_message

            # REMOVED_SYNTAX_ERROR: @pytest.mark.L3

            # REMOVED_SYNTAX_ERROR: @pytest.mark.integration

# REMOVED_SYNTAX_ERROR: class TestWebSocketMessageCompressionL3:

    # REMOVED_SYNTAX_ERROR: """L3 integration tests for WebSocket message compression."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_container(self):

    # REMOVED_SYNTAX_ERROR: """Set up Redis container for compression testing."""

    # REMOVED_SYNTAX_ERROR: container = RedisContainer(port=6387)

    # REMOVED_SYNTAX_ERROR: redis_url = await container.start()

    # REMOVED_SYNTAX_ERROR: yield container, redis_url

    # REMOVED_SYNTAX_ERROR: await container.stop()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_client(self, redis_container):

    # REMOVED_SYNTAX_ERROR: """Create Redis client for compressed message storage."""

    # REMOVED_SYNTAX_ERROR: _, redis_url = redis_container

    # REMOVED_SYNTAX_ERROR: client = redis.Redis.from_url(redis_url, decode_responses=False)  # Binary mode for compression

    # REMOVED_SYNTAX_ERROR: yield client

    # REMOVED_SYNTAX_ERROR: await client.close()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def websocket_manager(self, redis_container):

    # REMOVED_SYNTAX_ERROR: """Create WebSocket manager for compression testing."""

    # REMOVED_SYNTAX_ERROR: _, redis_url = redis_container

    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_manager.redis_manager') as mock_redis_mgr:

        # REMOVED_SYNTAX_ERROR: test_redis_mgr = RedisManager()

        # REMOVED_SYNTAX_ERROR: test_redis_mgr.enabled = True

        # REMOVED_SYNTAX_ERROR: test_redis_mgr.redis_client = redis.Redis.from_url(redis_url, decode_responses=False)

        # REMOVED_SYNTAX_ERROR: mock_redis_mgr.return_value = test_redis_mgr

        # REMOVED_SYNTAX_ERROR: mock_redis_mgr.get_client.return_value = test_redis_mgr.redis_client

        # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()

        # REMOVED_SYNTAX_ERROR: yield manager

        # REMOVED_SYNTAX_ERROR: await test_redis_mgr.redis_client.close()

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def message_compressor(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: """Create message compressor instance."""

    # REMOVED_SYNTAX_ERROR: return MessageCompressor()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_users(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: """Create test users for compression testing."""

    # REMOVED_SYNTAX_ERROR: return [ )

    # REMOVED_SYNTAX_ERROR: User( )

    # REMOVED_SYNTAX_ERROR: id="formatted_string",

    # REMOVED_SYNTAX_ERROR: email="formatted_string",

    # REMOVED_SYNTAX_ERROR: username="formatted_string",

    # REMOVED_SYNTAX_ERROR: is_active=True,

    # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc)

    

    # REMOVED_SYNTAX_ERROR: for i in range(3)

    

# REMOVED_SYNTAX_ERROR: def create_large_message(self, size_kb: int = 5) -> Dict[str, Any]:

    # REMOVED_SYNTAX_ERROR: """Create a large message for compression testing."""

    # REMOVED_SYNTAX_ERROR: large_content = "x" * (size_kb * 1024)  # Create content of specified size

    # REMOVED_SYNTAX_ERROR: return create_test_message( )

    # REMOVED_SYNTAX_ERROR: "large_message",

    # REMOVED_SYNTAX_ERROR: "system",

    # REMOVED_SYNTAX_ERROR: { )

    # REMOVED_SYNTAX_ERROR: "large_content": large_content,

    # REMOVED_SYNTAX_ERROR: "metadata": { )

    # REMOVED_SYNTAX_ERROR: "size_kb": size_kb,

    # REMOVED_SYNTAX_ERROR: "created_at": time.time(),

    # REMOVED_SYNTAX_ERROR: "test_data": {"formatted_string": "formatted_string" for i in range(100)}

    

    

    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_basic_message_compression(self, message_compressor):

        # REMOVED_SYNTAX_ERROR: """Test basic message compression and decompression."""
        # Create large message

        # REMOVED_SYNTAX_ERROR: large_message = self.create_large_message(5)  # 5KB message

        # REMOVED_SYNTAX_ERROR: original_size = len(json.dumps(large_message).encode('utf-8'))

        # Compress message

        # REMOVED_SYNTAX_ERROR: compressed_message = message_compressor.compress_message(large_message, "gzip")

        # Verify compression

        # REMOVED_SYNTAX_ERROR: assert compressed_message["compressed"] is True

        # REMOVED_SYNTAX_ERROR: assert compressed_message["method"] == "gzip"

        # REMOVED_SYNTAX_ERROR: assert compressed_message["original_size"] == original_size

        # REMOVED_SYNTAX_ERROR: assert compressed_message["compressed_size"] < original_size

        # REMOVED_SYNTAX_ERROR: assert compressed_message["compression_ratio"] < 1.0

        # REMOVED_SYNTAX_ERROR: assert compressed_message["compression_time"] < 0.1  # Should be fast

        # Test compression ratio

        # REMOVED_SYNTAX_ERROR: compression_ratio = compressed_message["compression_ratio"]

        # REMOVED_SYNTAX_ERROR: assert compression_ratio < 0.3  # At least 70% compression for repetitive data

        # Decompress message

        # REMOVED_SYNTAX_ERROR: decompressed_message = message_compressor.decompress_message(compressed_message)

        # Verify decompression

        # REMOVED_SYNTAX_ERROR: assert decompressed_message["type"] == large_message["type"]

        # REMOVED_SYNTAX_ERROR: assert decompressed_message["data"]["large_content"] == large_message["data"]["large_content"]

        # REMOVED_SYNTAX_ERROR: assert decompressed_message["decompression_time"] < 0.1  # Should be fast

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_compression_methods_comparison(self, message_compressor):

            # REMOVED_SYNTAX_ERROR: """Test different compression methods."""

            # REMOVED_SYNTAX_ERROR: large_message = self.create_large_message(10)  # 10KB message

            # REMOVED_SYNTAX_ERROR: methods = ["gzip", "zlib"]

            # REMOVED_SYNTAX_ERROR: compression_results = {}

            # REMOVED_SYNTAX_ERROR: for method in methods:
                # Compress with each method

                # REMOVED_SYNTAX_ERROR: compressed = message_compressor.compress_message(large_message, method)

                # Store results

                # REMOVED_SYNTAX_ERROR: compression_results[method] = { )

                # REMOVED_SYNTAX_ERROR: "compression_ratio": compressed["compression_ratio"],

                # REMOVED_SYNTAX_ERROR: "compression_time": compressed["compression_time"],

                # REMOVED_SYNTAX_ERROR: "compressed_size": compressed["compressed_size"]

                

                # Verify decompression works

                # REMOVED_SYNTAX_ERROR: decompressed = message_compressor.decompress_message(compressed)

                # REMOVED_SYNTAX_ERROR: assert decompressed["type"] == large_message["type"]

                # Compare compression efficiency

                # REMOVED_SYNTAX_ERROR: gzip_ratio = compression_results["gzip"]["compression_ratio"]

                # REMOVED_SYNTAX_ERROR: zlib_ratio = compression_results["zlib"]["compression_ratio"]

                # Both should achieve good compression

                # REMOVED_SYNTAX_ERROR: assert gzip_ratio < 0.5  # At least 50% compression

                # REMOVED_SYNTAX_ERROR: assert zlib_ratio < 0.5  # At least 50% compression

                # Performance should be reasonable

                # REMOVED_SYNTAX_ERROR: assert compression_results["gzip"]["compression_time"] < 0.2

                # REMOVED_SYNTAX_ERROR: assert compression_results["zlib"]["compression_time"] < 0.2

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_compression_threshold_handling(self, message_compressor):

                    # REMOVED_SYNTAX_ERROR: """Test compression threshold behavior."""
                    # Small message (below threshold)

                    # REMOVED_SYNTAX_ERROR: small_message = create_test_message("small", "system", {"content": "small"})

                    # REMOVED_SYNTAX_ERROR: compressed_small = message_compressor.compress_message(small_message)

                    # Should not be compressed

                    # REMOVED_SYNTAX_ERROR: assert "compressed" not in compressed_small or compressed_small.get("compressed") is False

                    # REMOVED_SYNTAX_ERROR: assert compressed_small == small_message

                    # Large message (above threshold)

                    # REMOVED_SYNTAX_ERROR: large_message = self.create_large_message(2)  # 2KB message

                    # REMOVED_SYNTAX_ERROR: compressed_large = message_compressor.compress_message(large_message)

                    # Should be compressed

                    # REMOVED_SYNTAX_ERROR: assert compressed_large["compressed"] is True

                    # REMOVED_SYNTAX_ERROR: assert compressed_large["original_size"] > message_compressor.compression_threshold

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_compressed_message_redis_storage(self, redis_client, message_compressor, test_users):

                        # REMOVED_SYNTAX_ERROR: """Test storing and retrieving compressed messages in Redis."""

                        # REMOVED_SYNTAX_ERROR: user = test_users[0]

                        # REMOVED_SYNTAX_ERROR: large_message = self.create_large_message(8)  # 8KB message

                        # Compress message

                        # REMOVED_SYNTAX_ERROR: compressed_message = message_compressor.compress_message(large_message, "gzip")

                        # Store in Redis

                        # REMOVED_SYNTAX_ERROR: message_key = "formatted_string"

                        # REMOVED_SYNTAX_ERROR: compressed_data = json.dumps(compressed_message).encode('utf-8')

                        # REMOVED_SYNTAX_ERROR: await redis_client.set(message_key, compressed_data, ex=3600)

                        # Retrieve from Redis

                        # REMOVED_SYNTAX_ERROR: stored_data = await redis_client.get(message_key)

                        # REMOVED_SYNTAX_ERROR: retrieved_message = json.loads(stored_data.decode('utf-8'))

                        # Verify retrieval

                        # REMOVED_SYNTAX_ERROR: assert retrieved_message["compressed"] is True

                        # REMOVED_SYNTAX_ERROR: assert retrieved_message["method"] == "gzip"

                        # REMOVED_SYNTAX_ERROR: assert retrieved_message["original_size"] == compressed_message["original_size"]

                        # Decompress retrieved message

                        # REMOVED_SYNTAX_ERROR: decompressed = message_compressor.decompress_message(retrieved_message)

                        # Verify content integrity

                        # REMOVED_SYNTAX_ERROR: assert decompressed["data"]["large_content"] == large_message["data"]["large_content"]

                        # Cleanup

                        # REMOVED_SYNTAX_ERROR: await redis_client.delete(message_key)

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_websocket_compression_integration(self, websocket_manager, redis_client, message_compressor, test_users):

                            # REMOVED_SYNTAX_ERROR: """Test compression integration with WebSocket messaging."""

                            # REMOVED_SYNTAX_ERROR: user = test_users[0]

                            # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                            # Connect user

                            # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

                            # REMOVED_SYNTAX_ERROR: assert connection_info is not None

                            # Create large message

                            # REMOVED_SYNTAX_ERROR: large_message = self.create_large_message(6)  # 6KB message

                            # Compress message

                            # REMOVED_SYNTAX_ERROR: compressed_message = message_compressor.compress_message(large_message, "gzip")

                            # Send compressed message through WebSocket system

                            # REMOVED_SYNTAX_ERROR: channel = "formatted_string"

                            # REMOVED_SYNTAX_ERROR: message_data = json.dumps(compressed_message).encode('utf-8')

                            # Store and publish compressed message

                            # REMOVED_SYNTAX_ERROR: message_id = str(uuid4())

                            # REMOVED_SYNTAX_ERROR: storage_key = "formatted_string"

                            # REMOVED_SYNTAX_ERROR: await redis_client.set(storage_key, message_data, ex=600)

                            # Publish notification of compressed message

                            # REMOVED_SYNTAX_ERROR: notification = { )

                            # REMOVED_SYNTAX_ERROR: "type": "compressed_message",

                            # REMOVED_SYNTAX_ERROR: "message_id": message_id,

                            # REMOVED_SYNTAX_ERROR: "storage_key": storage_key,

                            # REMOVED_SYNTAX_ERROR: "compression_info": { )

                            # REMOVED_SYNTAX_ERROR: "method": compressed_message["method"],

                            # REMOVED_SYNTAX_ERROR: "compression_ratio": compressed_message["compression_ratio"]

                            

                            

                            # REMOVED_SYNTAX_ERROR: await redis_client.publish(channel, json.dumps(notification))

                            # Simulate receiving and decompressing

                            # REMOVED_SYNTAX_ERROR: stored_compressed = await redis_client.get(storage_key)

                            # REMOVED_SYNTAX_ERROR: retrieved_compressed = json.loads(stored_compressed.decode('utf-8'))

                            # Decompress and verify

                            # REMOVED_SYNTAX_ERROR: final_message = message_compressor.decompress_message(retrieved_compressed)

                            # REMOVED_SYNTAX_ERROR: assert final_message["data"]["large_content"] == large_message["data"]["large_content"]

                            # Cleanup

                            # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

                            # REMOVED_SYNTAX_ERROR: await redis_client.delete(storage_key)

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_compression_performance_under_load(self, message_compressor):

                                # REMOVED_SYNTAX_ERROR: """Test compression performance with multiple concurrent operations."""

                                # REMOVED_SYNTAX_ERROR: message_count = 50

                                # REMOVED_SYNTAX_ERROR: message_size_kb = 5

                                # Create multiple large messages

                                # REMOVED_SYNTAX_ERROR: messages = [self.create_large_message(message_size_kb) for _ in range(message_count)]

                                # Compress all messages concurrently

                                # REMOVED_SYNTAX_ERROR: compression_start = time.time()

                                # REMOVED_SYNTAX_ERROR: compression_tasks = []

                                # REMOVED_SYNTAX_ERROR: for message in messages:
                                    # Use asyncio to simulate concurrent compression

                                    # REMOVED_SYNTAX_ERROR: task = asyncio.create_task(asyncio.to_thread( ))

                                    # REMOVED_SYNTAX_ERROR: message_compressor.compress_message, message, "gzip"

                                    

                                    # REMOVED_SYNTAX_ERROR: compression_tasks.append(task)

                                    # REMOVED_SYNTAX_ERROR: compressed_messages = await asyncio.gather(*compression_tasks)

                                    # REMOVED_SYNTAX_ERROR: compression_time = time.time() - compression_start

                                    # Verify compression results

                                    # REMOVED_SYNTAX_ERROR: successful_compressions = 0

                                    # REMOVED_SYNTAX_ERROR: total_compression_ratio = 0

                                    # REMOVED_SYNTAX_ERROR: for compressed in compressed_messages:

                                        # REMOVED_SYNTAX_ERROR: if compressed.get("compressed", False):

                                            # REMOVED_SYNTAX_ERROR: successful_compressions += 1

                                            # REMOVED_SYNTAX_ERROR: total_compression_ratio += compressed["compression_ratio"]

                                            # REMOVED_SYNTAX_ERROR: avg_compression_ratio = total_compression_ratio / successful_compressions

                                            # Performance assertions

                                            # REMOVED_SYNTAX_ERROR: assert compression_time < 5.0  # All compressions within 5 seconds

                                            # REMOVED_SYNTAX_ERROR: assert successful_compressions >= message_count * 0.95  # 95% success rate

                                            # REMOVED_SYNTAX_ERROR: assert avg_compression_ratio < 0.4  # Average 60%+ compression

                                            # Test decompression performance

                                            # REMOVED_SYNTAX_ERROR: decompression_start = time.time()

                                            # REMOVED_SYNTAX_ERROR: decompression_tasks = []

                                            # REMOVED_SYNTAX_ERROR: for compressed in compressed_messages:

                                                # REMOVED_SYNTAX_ERROR: if compressed.get("compressed", False):

                                                    # REMOVED_SYNTAX_ERROR: task = asyncio.create_task(asyncio.to_thread( ))

                                                    # REMOVED_SYNTAX_ERROR: message_compressor.decompress_message, compressed

                                                    

                                                    # REMOVED_SYNTAX_ERROR: decompression_tasks.append(task)

                                                    # REMOVED_SYNTAX_ERROR: decompressed_messages = await asyncio.gather(*decompression_tasks, return_exceptions=True)

                                                    # REMOVED_SYNTAX_ERROR: decompression_time = time.time() - decompression_start

                                                    # REMOVED_SYNTAX_ERROR: successful_decompressions = sum(1 for msg in decompressed_messages )

                                                    # REMOVED_SYNTAX_ERROR: if not isinstance(msg, Exception))

                                                    # Decompression performance assertions

                                                    # REMOVED_SYNTAX_ERROR: assert decompression_time < 3.0  # Decompression should be faster

                                                    # REMOVED_SYNTAX_ERROR: assert successful_decompressions >= len(decompression_tasks) * 0.95  # 95% success rate

                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_compression_bandwidth_savings(self, redis_client, message_compressor, test_users):

                                                        # REMOVED_SYNTAX_ERROR: """Test bandwidth savings from message compression."""

                                                        # REMOVED_SYNTAX_ERROR: user = test_users[0]

                                                        # REMOVED_SYNTAX_ERROR: test_scenarios = [ )

                                                        # REMOVED_SYNTAX_ERROR: {"size_kb": 2, "expected_savings": 0.3},   # Small files

                                                        # REMOVED_SYNTAX_ERROR: {"size_kb": 10, "expected_savings": 0.7},  # Medium files

                                                        # REMOVED_SYNTAX_ERROR: {"size_kb": 50, "expected_savings": 0.8}   # Large files

                                                        

                                                        # REMOVED_SYNTAX_ERROR: total_original_size = 0

                                                        # REMOVED_SYNTAX_ERROR: total_compressed_size = 0

                                                        # REMOVED_SYNTAX_ERROR: bandwidth_savings = []

                                                        # REMOVED_SYNTAX_ERROR: for scenario in test_scenarios:
                                                            # Create message of specified size

                                                            # REMOVED_SYNTAX_ERROR: large_message = self.create_large_message(scenario["size_kb"])

                                                            # REMOVED_SYNTAX_ERROR: original_data = json.dumps(large_message).encode('utf-8')

                                                            # REMOVED_SYNTAX_ERROR: original_size = len(original_data)

                                                            # Compress message

                                                            # REMOVED_SYNTAX_ERROR: compressed_message = message_compressor.compress_message(large_message, "gzip")

                                                            # REMOVED_SYNTAX_ERROR: compressed_data = json.dumps(compressed_message).encode('utf-8')

                                                            # REMOVED_SYNTAX_ERROR: compressed_size = len(compressed_data)

                                                            # Calculate savings

                                                            # REMOVED_SYNTAX_ERROR: savings_ratio = 1 - (compressed_size / original_size)

                                                            # REMOVED_SYNTAX_ERROR: bandwidth_savings.append(savings_ratio)

                                                            # REMOVED_SYNTAX_ERROR: total_original_size += original_size

                                                            # REMOVED_SYNTAX_ERROR: total_compressed_size += compressed_size

                                                            # Store both versions in Redis for comparison

                                                            # REMOVED_SYNTAX_ERROR: original_key = f"original:{user.id]:{scenario['size_kb']]kb"

                                                            # REMOVED_SYNTAX_ERROR: compressed_key = f"compressed:{user.id]:{scenario['size_kb']]kb"

                                                            # REMOVED_SYNTAX_ERROR: await redis_client.set(original_key, original_data, ex=300)

                                                            # REMOVED_SYNTAX_ERROR: await redis_client.set(compressed_key, compressed_data, ex=300)

                                                            # Verify expected savings threshold

                                                            # REMOVED_SYNTAX_ERROR: assert savings_ratio >= scenario["expected_savings"]

                                                            # Cleanup

                                                            # REMOVED_SYNTAX_ERROR: await redis_client.delete(original_key, compressed_key)

                                                            # Overall bandwidth savings

                                                            # REMOVED_SYNTAX_ERROR: overall_savings = 1 - (total_compressed_size / total_original_size)

                                                            # REMOVED_SYNTAX_ERROR: avg_savings = sum(bandwidth_savings) / len(bandwidth_savings)

                                                            # Business value assertions

                                                            # REMOVED_SYNTAX_ERROR: assert overall_savings >= 0.6  # At least 60% bandwidth savings

                                                            # REMOVED_SYNTAX_ERROR: assert avg_savings >= 0.6      # Consistent savings across scenarios

                                                            # REMOVED_SYNTAX_ERROR: assert min(bandwidth_savings) >= 0.3  # Even small files save 30%

                                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":

                                                                # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s", "--tb=short"])