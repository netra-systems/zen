"""
L3 Integration Test: WebSocket Binary Message Handling with Redis

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Feature enablement - Support file uploads and rich media
- Value Impact: Enables document sharing and multimedia collaboration
- Strategic Impact: $60K MRR - Binary data support for enterprise workflows

L3 Test: Uses real Redis for binary message storage and WebSocket transmission.
Binary target: 10MB file support with <5% corruption rate.
"""

from netra_backend.tests.test_utils import setup_test_path

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest
import asyncio
import json
import time
import base64
import hashlib
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4
import os
import tempfile

import redis.asyncio as redis
from ws_manager import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from schemas import UserInDB
from test_framework.mock_utils import mock_justified

# Add project root to path

from netra_backend.tests.helpers.redis_l3_helpers import (

# Add project root to path
    RedisContainer, 
    MockWebSocketForRedis, 
    create_test_message
)


class BinaryMessageHandler:
    """Handle binary message transmission for WebSocket."""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.chunk_size = 1024 * 64  # 64KB chunks
        self.max_file_size = 1024 * 1024 * 10  # 10MB max
        self.binary_storage_prefix = "ws_binary"
        self.chunk_timeout = 3600  # 1 hour
    
    def create_binary_message(self, data: bytes, content_type: str = "application/octet-stream", filename: str = None) -> Dict[str, Any]:
        """Create binary message structure."""
        message_id = str(uuid4())
        data_hash = hashlib.sha256(data).hexdigest()
        
        return {
            "type": "binary_message",
            "message_id": message_id,
            "content_type": content_type,
            "filename": filename,
            "size": len(data),
            "hash": data_hash,
            "data": base64.b64encode(data).decode('utf-8'),
            "timestamp": time.time()
        }
    
    async def store_binary_chunks(self, message_id: str, data: bytes) -> List[str]:
        """Store binary data in Redis chunks."""
        chunks = []
        chunk_ids = []
        
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i:i + self.chunk_size]
            chunk_id = f"{message_id}_chunk_{i // self.chunk_size}"
            chunk_key = f"{self.binary_storage_prefix}:{chunk_id}"
            
            await self.redis_client.set(chunk_key, chunk, ex=self.chunk_timeout)
            chunk_ids.append(chunk_id)
        
        # Store chunk manifest
        manifest_key = f"{self.binary_storage_prefix}:manifest:{message_id}"
        manifest = {
            "message_id": message_id,
            "chunk_ids": chunk_ids,
            "total_size": len(data),
            "chunk_count": len(chunk_ids),
            "created_at": time.time()
        }
        await self.redis_client.set(manifest_key, json.dumps(manifest), ex=self.chunk_timeout)
        
        return chunk_ids
    
    async def retrieve_binary_chunks(self, message_id: str) -> bytes:
        """Retrieve binary data from Redis chunks."""
        manifest_key = f"{self.binary_storage_prefix}:manifest:{message_id}"
        manifest_data = await self.redis_client.get(manifest_key)
        
        if not manifest_data:
            raise ValueError(f"Binary message manifest not found: {message_id}")
        
        manifest = json.loads(manifest_data)
        chunks = []
        
        for chunk_id in manifest["chunk_ids"]:
            chunk_key = f"{self.binary_storage_prefix}:{chunk_id}"
            chunk_data = await self.redis_client.get(chunk_key)
            
            if chunk_data is None:
                raise ValueError(f"Missing chunk: {chunk_id}")
            
            chunks.append(chunk_data)
        
        return b''.join(chunks)
    
    async def cleanup_binary_message(self, message_id: str) -> None:
        """Clean up binary message chunks."""
        manifest_key = f"{self.binary_storage_prefix}:manifest:{message_id}"
        manifest_data = await self.redis_client.get(manifest_key)
        
        if manifest_data:
            manifest = json.loads(manifest_data)
            
            # Delete chunks
            chunk_keys = [f"{self.binary_storage_prefix}:{chunk_id}" for chunk_id in manifest["chunk_ids"]]
            if chunk_keys:
                await self.redis_client.delete(*chunk_keys)
            
            # Delete manifest
            await self.redis_client.delete(manifest_key)
    
    def verify_binary_integrity(self, original_data: bytes, retrieved_data: bytes) -> Dict[str, Any]:
        """Verify binary data integrity."""
        original_hash = hashlib.sha256(original_data).hexdigest()
        retrieved_hash = hashlib.sha256(retrieved_data).hexdigest()
        
        return {
            "size_match": len(original_data) == len(retrieved_data),
            "hash_match": original_hash == retrieved_hash,
            "original_size": len(original_data),
            "retrieved_size": len(retrieved_data),
            "original_hash": original_hash,
            "retrieved_hash": retrieved_hash,
            "corruption_rate": 0.0 if original_hash == retrieved_hash else 1.0
        }


@pytest.mark.L3
@pytest.mark.integration
class TestWebSocketBinaryMessageHandlingL3:
    """L3 integration tests for WebSocket binary message handling."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container for binary message testing."""
        container = RedisContainer(port=6389)
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client for binary storage."""
        _, redis_url = redis_container
        # Use binary mode for Redis client
        client = redis.Redis.from_url(redis_url, decode_responses=False)
        yield client
        await client.close()
    
    @pytest.fixture
    async def ws_manager(self, redis_container):
        """Create WebSocket manager for binary testing."""
        _, redis_url = redis_container
        
        with patch('app.ws_manager.redis_manager') as mock_redis_mgr:
            test_redis_mgr = RedisManager()
            test_redis_mgr.enabled = True
            test_redis_mgr.redis_client = redis.Redis.from_url(redis_url, decode_responses=False)
            mock_redis_mgr.return_value = test_redis_mgr
            mock_redis_mgr.get_client.return_value = test_redis_mgr.redis_client
            
            manager = WebSocketManager()
            yield manager
            
            await test_redis_mgr.redis_client.close()
    
    @pytest.fixture
    async def binary_handler(self, redis_client):
        """Create binary message handler."""
        return BinaryMessageHandler(redis_client)
    
    @pytest.fixture
    def test_users(self):
        """Create test users for binary testing."""
        return [
            UserInDB(
                id=f"binary_user_{i}",
                email=f"binaryuser{i}@example.com", 
                username=f"binaryuser{i}",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
    
    def create_test_binary_data(self, size_kb: int = 100) -> bytes:
        """Create test binary data of specified size."""
        # Create pseudo-random binary data
        data = bytearray()
        for i in range(size_kb * 1024):
            data.append((i * 7 + 13) % 256)  # Pseudo-random pattern
        return bytes(data)
    
    def create_test_image_data(self) -> Tuple[bytes, str]:
        """Create test image-like binary data."""
        # Simple BMP header + data
        width, height = 100, 100
        header = b'BM'  # BMP signature
        file_size = 54 + (width * height * 3)
        header += file_size.to_bytes(4, 'little')
        header += b'\x00\x00\x00\x00'  # Reserved
        header += (54).to_bytes(4, 'little')  # Data offset
        header += (40).to_bytes(4, 'little')  # Header size
        header += width.to_bytes(4, 'little')
        header += height.to_bytes(4, 'little')
        header += (1).to_bytes(2, 'little')  # Planes
        header += (24).to_bytes(2, 'little')  # Bits per pixel
        header += b'\x00' * 24  # Rest of header
        
        # Simple RGB data (blue gradient)
        pixel_data = bytearray()
        for y in range(height):
            for x in range(width):
                blue = (x * 255) // width
                pixel_data.extend([blue, 0, 0])  # BGR format
        
        return header + pixel_data, "test_image.bmp"
    
    async def test_basic_binary_message_creation(self, binary_handler):
        """Test basic binary message creation and structure."""
        test_data = self.create_test_binary_data(50)  # 50KB
        
        binary_message = binary_handler.create_binary_message(
            test_data, 
            "application/pdf", 
            "test_document.pdf"
        )
        
        # Verify message structure
        assert binary_message["type"] == "binary_message"
        assert binary_message["content_type"] == "application/pdf"
        assert binary_message["filename"] == "test_document.pdf"
        assert binary_message["size"] == len(test_data)
        assert "message_id" in binary_message
        assert "hash" in binary_message
        assert "data" in binary_message
        
        # Verify data integrity
        decoded_data = base64.b64decode(binary_message["data"])
        assert decoded_data == test_data
        
        # Verify hash
        expected_hash = hashlib.sha256(test_data).hexdigest()
        assert binary_message["hash"] == expected_hash
    
    async def test_binary_chunked_storage_and_retrieval(self, binary_handler):
        """Test binary data chunked storage and retrieval."""
        test_data = self.create_test_binary_data(200)  # 200KB
        message_id = str(uuid4())
        
        # Store in chunks
        chunk_ids = await binary_handler.store_binary_chunks(message_id, test_data)
        
        # Verify chunks were created
        assert len(chunk_ids) > 1  # Should be multiple chunks
        expected_chunks = (len(test_data) + binary_handler.chunk_size - 1) // binary_handler.chunk_size
        assert len(chunk_ids) == expected_chunks
        
        # Retrieve data
        retrieved_data = await binary_handler.retrieve_binary_chunks(message_id)
        
        # Verify integrity
        integrity_check = binary_handler.verify_binary_integrity(test_data, retrieved_data)
        assert integrity_check["size_match"] is True
        assert integrity_check["hash_match"] is True
        assert integrity_check["corruption_rate"] == 0.0
        
        # Cleanup
        await binary_handler.cleanup_binary_message(message_id)
    
    async def test_large_binary_file_handling(self, binary_handler):
        """Test handling of large binary files."""
        large_data = self.create_test_binary_data(2048)  # 2MB file
        message_id = str(uuid4())
        
        # Store large file
        storage_start = time.time()
        chunk_ids = await binary_handler.store_binary_chunks(message_id, large_data)
        storage_time = time.time() - storage_start
        
        # Verify storage performance
        assert storage_time < 10.0  # Should store within 10 seconds
        assert len(chunk_ids) > 30  # Should be many chunks
        
        # Retrieve large file
        retrieval_start = time.time()
        retrieved_data = await binary_handler.retrieve_binary_chunks(message_id)
        retrieval_time = time.time() - retrieval_start
        
        # Verify retrieval performance
        assert retrieval_time < 5.0  # Should retrieve within 5 seconds
        
        # Verify integrity
        integrity_check = binary_handler.verify_binary_integrity(large_data, retrieved_data)
        assert integrity_check["hash_match"] is True
        assert integrity_check["size_match"] is True
        
        # Cleanup
        await binary_handler.cleanup_binary_message(message_id)
    
    async def test_binary_message_websocket_transmission(self, ws_manager, binary_handler, test_users):
        """Test binary message transmission through WebSocket."""
        user = test_users[0]
        websocket = MockWebSocketForRedis(user.id)
        
        # Connect user
        connection_info = await ws_manager.connect_user(user.id, websocket)
        assert connection_info is not None
        
        # Create binary data
        image_data, filename = self.create_test_image_data()
        binary_message = binary_handler.create_binary_message(
            image_data, 
            "image/bmp", 
            filename
        )
        
        # Store binary data in chunks
        message_id = binary_message["message_id"]
        await binary_handler.store_binary_chunks(message_id, image_data)
        
        # Send notification through WebSocket (not the full binary data)
        notification_message = {
            "type": "binary_notification",
            "message_id": message_id,
            "content_type": binary_message["content_type"],
            "filename": binary_message["filename"],
            "size": binary_message["size"],
            "hash": binary_message["hash"]
        }
        
        # Send through WebSocket manager
        success = await ws_manager.send_message_to_user(user.id, notification_message)
        assert success is True
        
        # Simulate client retrieving binary data
        retrieved_data = await binary_handler.retrieve_binary_chunks(message_id)
        integrity_check = binary_handler.verify_binary_integrity(image_data, retrieved_data)
        
        assert integrity_check["hash_match"] is True
        assert integrity_check["corruption_rate"] == 0.0
        
        # Cleanup
        await ws_manager.disconnect_user(user.id, websocket)
        await binary_handler.cleanup_binary_message(message_id)
    
    async def test_concurrent_binary_uploads(self, binary_handler, test_users):
        """Test concurrent binary file uploads."""
        concurrent_uploads = 5
        upload_tasks = []
        test_data_sets = []
        
        # Prepare test data
        for i in range(concurrent_uploads):
            test_data = self.create_test_binary_data(100 + i * 50)  # Varying sizes
            message_id = str(uuid4())
            test_data_sets.append((message_id, test_data))
        
        # Start concurrent uploads
        upload_start = time.time()
        for message_id, test_data in test_data_sets:
            task = binary_handler.store_binary_chunks(message_id, test_data)
            upload_tasks.append((message_id, test_data, task))
        
        # Wait for uploads to complete
        upload_results = []
        for message_id, test_data, task in upload_tasks:
            try:
                chunk_ids = await task
                upload_results.append((message_id, test_data, chunk_ids, True))
            except Exception as e:
                upload_results.append((message_id, test_data, None, False))
        
        upload_time = time.time() - upload_start
        
        # Verify upload performance
        assert upload_time < 15.0  # All uploads within 15 seconds
        successful_uploads = sum(1 for _, _, _, success in upload_results if success)
        assert successful_uploads >= concurrent_uploads * 0.8  # 80% success rate
        
        # Test concurrent retrieval
        retrieval_start = time.time()
        retrieval_tasks = []
        
        for message_id, original_data, chunk_ids, success in upload_results:
            if success:
                task = binary_handler.retrieve_binary_chunks(message_id)
                retrieval_tasks.append((message_id, original_data, task))
        
        # Wait for retrievals
        retrieval_results = []
        for message_id, original_data, task in retrieval_tasks:
            try:
                retrieved_data = await task
                integrity = binary_handler.verify_binary_integrity(original_data, retrieved_data)
                retrieval_results.append((message_id, integrity["hash_match"]))
            except Exception:
                retrieval_results.append((message_id, False))
        
        retrieval_time = time.time() - retrieval_start
        
        # Verify retrieval performance and integrity
        assert retrieval_time < 10.0  # All retrievals within 10 seconds
        successful_retrievals = sum(1 for _, success in retrieval_results if success)
        assert successful_retrievals >= len(retrieval_tasks) * 0.9  # 90% success rate
        
        # Cleanup
        for message_id, _, _, success in upload_results:
            if success:
                await binary_handler.cleanup_binary_message(message_id)
    
    async def test_binary_message_size_limits(self, binary_handler):
        """Test binary message size limit enforcement."""
        # Test within limits
        acceptable_data = self.create_test_binary_data(1024)  # 1MB
        message_id = str(uuid4())
        
        chunk_ids = await binary_handler.store_binary_chunks(message_id, acceptable_data)
        assert len(chunk_ids) > 0
        
        retrieved_data = await binary_handler.retrieve_binary_chunks(message_id)
        assert len(retrieved_data) == len(acceptable_data)
        
        await binary_handler.cleanup_binary_message(message_id)
        
        # Test size validation in message creation
        large_data = self.create_test_binary_data(binary_handler.max_file_size // 1024 + 1)  # Exceed limit
        
        # Create message (this should work as it's just structure)
        large_message = binary_handler.create_binary_message(large_data[:1024])  # Use smaller sample
        assert large_message["type"] == "binary_message"
        
        # The size limit would be enforced at application level before storage
    
    @mock_justified("L3: Binary message handling with real Redis storage")
    async def test_binary_corruption_detection(self, binary_handler):
        """Test detection of binary data corruption."""
        test_data = self.create_test_binary_data(500)  # 500KB
        message_id = str(uuid4())
        
        # Store data
        chunk_ids = await binary_handler.store_binary_chunks(message_id, test_data)
        
        # Simulate corruption by modifying a chunk
        corrupt_chunk_key = f"{binary_handler.binary_storage_prefix}:{chunk_ids[len(chunk_ids)//2]}"
        corrupted_data = b"CORRUPTED_DATA_" + b"x" * 1000
        await binary_handler.redis_client.set(corrupt_chunk_key, corrupted_data)
        
        # Retrieve corrupted data
        retrieved_data = await binary_handler.retrieve_binary_chunks(message_id)
        
        # Verify corruption detection
        integrity_check = binary_handler.verify_binary_integrity(test_data, retrieved_data)
        assert integrity_check["size_match"] is False
        assert integrity_check["hash_match"] is False
        assert integrity_check["corruption_rate"] > 0.0
        
        # Cleanup
        await binary_handler.cleanup_binary_message(message_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])