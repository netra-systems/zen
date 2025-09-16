"""
L3 Redis Testing Helpers
Helper classes and utilities for Redis container management in L3 tests.
"""

import asyncio
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import redis.asyncio as redis
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class RedisContainer:
    """Manages a real Redis Docker container for L3 testing."""
    
    def __init__(self, port: int = 6381):
        """Initialize Redis container configuration."""
        self.port = port
        self.container_name = f"netra-test-redis-l3-{uuid.uuid4().hex[:8]}"
        self.container_id = None
        self.redis_url = f"redis://localhost:{port}/0"
    
    async def start(self) -> str:
        """Start Redis container and return connection URL."""
        try:
            await self._cleanup_existing()
            
            cmd = [
                "docker", "run", "-d",
                "--name", self.container_name,
                "-p", f"{self.port}:6379",
                "redis:7-alpine",
                "redis-server", "--appendonly", "yes"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to start Redis container: {result.stderr}")
            
            self.container_id = result.stdout.strip()
            await self._wait_for_ready()
            
            logger.info(f"Redis container started: {self.container_name}")
            return self.redis_url
            
        except Exception as e:
            await self.stop()
            raise RuntimeError(f"Redis container startup failed: {e}")
    
    async def stop(self) -> None:
        """Stop and remove Redis container."""
        if self.container_id:
            try:
                subprocess.run(["docker", "stop", self.container_id], capture_output=True, timeout=10)
                subprocess.run(["docker", "rm", self.container_id], capture_output=True, timeout=10)
                logger.info(f"Redis container stopped: {self.container_name}")
            except Exception as e:
                logger.warning(f"Error stopping Redis container: {e}")
            finally:
                self.container_id = None
    
    async def _cleanup_existing(self) -> None:
        """Clean up any existing container with same name."""
        try:
            subprocess.run(["docker", "stop", self.container_name], capture_output=True, timeout=5)
            subprocess.run(["docker", "rm", self.container_name], capture_output=True, timeout=5)
        except:
            pass
    
    async def _wait_for_ready(self, timeout: int = 30) -> None:
        """Wait for Redis to be ready to accept connections."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                client = redis.Redis.from_url(self.redis_url)
                await client.ping()
                await client.close()
                return
            except Exception:
                await asyncio.sleep(0.5)
        
        raise RuntimeError("Redis container failed to become ready")

class MockWebSocketForRedis:
    """Mock WebSocket that tracks messages for Redis pub/sub testing."""
    
    def __init__(self, user_id: str):
        """Initialize mock WebSocket."""
        self.user_id = user_id
        self.messages: List[Dict[str, Any]] = []
        self.client_state = WebSocketState.CONNECTED
        self.closed = False
        
    async def accept(self) -> None:
        """Mock WebSocket accept."""
        pass
    
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Track sent JSON messages."""
        if not self.closed:
            self.messages.append(data)
            logger.debug(f"WebSocket {self.user_id} received: {data}")
    
    async def send_text(self, data: str) -> None:
        """Track sent text messages."""
        if not self.closed:
            try:
                message = json.loads(data)
                self.messages.append(message)
            except json.JSONDecodeError:
                self.messages.append({"text": data})
    
    async def close(self, code: int = 1000, reason: str = "Normal closure") -> None:
        """Mock WebSocket close."""
        self.closed = True
        self.client_state = WebSocketState.DISCONNECTED

def create_test_message(message_type: str, user_id: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create standardized test message."""
    return {
        "type": message_type,
        "data": data or {"user_id": user_id, "content": f"Test message for {user_id}"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def verify_redis_connection(redis_url: str) -> bool:
    """Verify Redis connection is working."""
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        await client.close()
        return True
    except Exception as e:
        logger.error(f"Redis connection verification failed: {e}")
        return False

async def setup_pubsub_channels(pubsub_client, channels: List[str]) -> None:
    """Setup Redis pub/sub channel subscriptions."""
    await pubsub_client.subscribe(*channels)
    logger.info(f"Subscribed to channels: {channels}")

async def wait_for_message(pubsub_client, timeout: float = 1.0) -> Dict[str, Any]:
    """Wait for and return Redis pub/sub message."""
    message = await pubsub_client.get_message(timeout=timeout)
    if message and message['type'] == 'message':
        return json.loads(message['data'])
    return None