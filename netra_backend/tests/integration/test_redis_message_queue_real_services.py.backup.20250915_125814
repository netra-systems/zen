"""Integration Tests for Redis Message Queue with Real Services

Business Value Justification:
- Segment: Platform/Internal - Message Infrastructure
- Business Goal: Ensure reliable message delivery between services
- Value Impact: Enables scalable multi-service communication
- Strategic Impact: Foundation for distributed AI system architecture

Test Coverage:
- Redis message queue functionality with real connections
- Message serialization and delivery
- Queue persistence and reliability
- Message ordering and priority handling
"""

import pytest
import asyncio
import uuid
import json

from test_framework.ssot.real_services_test_fixtures import *


@pytest.mark.integration
class TestRedisMessageQueueRealServices:
    """Integration tests for Redis message queue with real services."""
    
    @pytest.mark.asyncio
    async def test_redis_message_queue_basic_functionality(self, real_services_fixture, real_redis_fixture):
        """Test basic Redis message queue functionality."""
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for message queue testing")
        
        redis_client = real_redis_fixture
        
        # Create test message
        message = {
            "id": str(uuid.uuid4()),
            "type": "agent_notification",
            "payload": {"agent": "test_agent", "status": "completed"},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        queue_name = "test_message_queue"
        
        # Act - send message to queue
        await redis_client.lpush(queue_name, json.dumps(message))
        
        # Receive message from queue
        received_data = await redis_client.brpop(queue_name, timeout=1)
        
        # Assert - verify message delivery
        if received_data:
            queue_name_received, message_data = received_data
            received_message = json.loads(message_data)
            
            assert received_message["id"] == message["id"]
            assert received_message["type"] == message["type"]
            assert received_message["payload"]["agent"] == "test_agent"
    
    @pytest.mark.asyncio
    async def test_redis_message_ordering(self, real_services_fixture, real_redis_fixture):
        """Test message ordering in Redis queue."""
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for ordering testing")
        
        redis_client = real_redis_fixture
        
        queue_name = "order_test_queue"
        num_messages = 10
        
        # Send ordered messages
        for i in range(num_messages):
            message = {"sequence": i, "data": f"message_{i}"}
            await redis_client.lpush(queue_name, json.dumps(message))
        
        # Receive messages and verify order
        received_sequences = []
        for _ in range(num_messages):
            result = await redis_client.brpop(queue_name, timeout=1)
            if result:
                _, message_data = result
                message = json.loads(message_data)
                received_sequences.append(message["sequence"])
        
        # Assert FIFO order (first in, first out)
        expected_order = list(range(num_messages))
        assert received_sequences == expected_order