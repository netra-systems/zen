"""Message Queue Agent Database Flow Critical Path Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (async processing capabilities)
- Business Goal: Reliable async message processing
- Value Impact: Protects $8K MRR from async processing failures
- Strategic Impact: Enables scalable agent operations and high throughput

Critical Path: Message enqueue -> Agent processing -> Database operations -> Result persistence
Coverage: Message queue integration, async processing, database consistency, error recovery
"""

import pytest
import asyncio
import time
import logging
import json
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.message_queue import MessageQueueService
from app.agents.supervisor_consolidated import SupervisorAgent
from app.services.database.connection_manager import DatabaseConnectionManager
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class MessageQueueFlowManager:
    """Manages message queue to agent to database flow testing."""
    
    def __init__(self):
        self.message_queue = None
        self.supervisor_agent = None
        self.db_manager = None
        self.redis_service = None
        self.processed_messages = []
        self.database_operations = []
        
    async def initialize_services(self):
        """Initialize message queue flow services."""
        self.message_queue = MessageQueueService()
        await self.message_queue.initialize()
        
        self.supervisor_agent = SupervisorAgent()
        await self.supervisor_agent.initialize()
        
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.redis_service = RedisService()
        await self.redis_service.connect()
    
    async def enqueue_message(self, message_type: str, payload: Dict[str, Any], 
                            priority: int = 1) -> Dict[str, Any]:
        """Enqueue message for processing."""
        start_time = time.time()
        
        message = {
            "id": f"msg_{int(time.time())}_{len(self.processed_messages)}",
            "type": message_type,
            "payload": payload,
            "priority": priority,
            "timestamp": time.time(),
            "retry_count": 0
        }
        
        result = await self.message_queue.enqueue(message)
        
        return {
            "message": message,
            "enqueue_result": result,
            "enqueue_time": time.time() - start_time
        }
    
    async def process_message_with_agent(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process message through agent pipeline."""
        start_time = time.time()
        
        try:
            # Agent processes the message
            processing_result = await self.supervisor_agent.process_message(
                message["type"], message["payload"]
            )
            
            # Record processing
            processing_record = {
                "message_id": message["id"],
                "processing_result": processing_result,
                "processing_time": time.time() - start_time,
                "success": processing_result.get("success", False)
            }
            
            self.processed_messages.append(processing_record)
            return processing_record
            
        except Exception as e:
            return {
                "message_id": message["id"],
                "error": str(e),
                "processing_time": time.time() - start_time,
                "success": False
            }
    
    async def persist_result_to_database(self, processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Persist processing result to database."""
        start_time = time.time()
        
        try:
            # Get database connection
            conn = await self.db_manager.get_connection()
            
            # Insert processing result
            insert_query = """
                INSERT INTO message_processing_log 
                (message_id, processing_result, processing_time, success, timestamp)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """
            
            result = await conn.fetchrow(
                insert_query,
                processing_result["message_id"],
                json.dumps(processing_result["processing_result"]),
                processing_result["processing_time"],
                processing_result["success"],
                time.time()
            )
            
            await self.db_manager.return_connection(conn)
            
            db_operation = {
                "message_id": processing_result["message_id"],
                "db_id": result["id"],
                "db_operation_time": time.time() - start_time,
                "success": True
            }
            
            self.database_operations.append(db_operation)
            return db_operation
            
        except Exception as e:
            return {
                "message_id": processing_result["message_id"],
                "error": str(e),
                "db_operation_time": time.time() - start_time,
                "success": False
            }
    
    async def complete_message_flow(self, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Complete end-to-end message flow."""
        flow_start = time.time()
        
        # Step 1: Enqueue message
        enqueue_result = await self.enqueue_message(message_type, payload)
        
        # Step 2: Process with agent
        processing_result = await self.process_message_with_agent(enqueue_result["message"])
        
        # Step 3: Persist to database
        db_result = await self.persist_result_to_database(processing_result)
        
        return {
            "total_flow_time": time.time() - flow_start,
            "enqueue_result": enqueue_result,
            "processing_result": processing_result,
            "db_result": db_result,
            "overall_success": all([
                enqueue_result["enqueue_result"].get("success", False),
                processing_result["success"],
                db_result["success"]
            ])
        }
    
    async def cleanup(self):
        """Clean up message queue flow resources."""
        # Clear test data from database
        try:
            conn = await self.db_manager.get_connection()
            for op in self.database_operations:
                if op["success"]:
                    await conn.execute(
                        "DELETE FROM message_processing_log WHERE id = $1",
                        op["db_id"]
                    )
            await self.db_manager.return_connection(conn)
        except Exception:
            pass
        
        if self.message_queue:
            await self.message_queue.shutdown()
        if self.supervisor_agent:
            await self.supervisor_agent.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()
        if self.redis_service:
            await self.redis_service.disconnect()


@pytest.fixture
async def message_flow_manager():
    """Create message queue flow manager for testing."""
    manager = MessageQueueFlowManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_single_message_queue_to_database_flow(message_flow_manager):
    """Test single message flow from queue to database."""
    manager = message_flow_manager
    
    # Test complete flow
    flow_result = await manager.complete_message_flow(
        "user_action",
        {"action": "create_thread", "user_id": "test_user", "thread_name": "Test Thread"}
    )
    
    assert flow_result["overall_success"] is True
    assert flow_result["total_flow_time"] < 3.0
    
    # Verify each step
    assert flow_result["enqueue_result"]["enqueue_result"]["success"] is True
    assert flow_result["processing_result"]["success"] is True
    assert flow_result["db_result"]["success"] is True
    
    # Verify timing
    assert flow_result["enqueue_result"]["enqueue_time"] < 0.1
    assert flow_result["processing_result"]["processing_time"] < 2.0
    assert flow_result["db_result"]["db_operation_time"] < 0.5


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_message_processing_error_recovery(message_flow_manager):
    """Test error recovery in message processing pipeline."""
    manager = message_flow_manager
    
    # Test with invalid message payload
    flow_result = await manager.complete_message_flow(
        "invalid_action",
        {"invalid": "payload"}
    )
    
    # Message should be enqueued successfully
    assert flow_result["enqueue_result"]["enqueue_result"]["success"] is True
    
    # Processing or database operation should handle error gracefully
    assert "error" in flow_result["processing_result"] or "error" in flow_result["db_result"]


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_message_queue_database_consistency(message_flow_manager):
    """Test database consistency across message processing."""
    manager = message_flow_manager
    
    # Process multiple related messages
    related_messages = [
        {"message_type": "user_action", "payload": {"action": "create_thread", "user_id": "consistency_user"}},
        {"message_type": "user_action", "payload": {"action": "update_thread", "user_id": "consistency_user", "thread_id": "thread_1"}},
        {"message_type": "user_action", "payload": {"action": "delete_thread", "user_id": "consistency_user", "thread_id": "thread_1"}}
    ]
    
    flow_results = []
    for msg_config in related_messages:
        result = await manager.complete_message_flow(
            msg_config["message_type"],
            msg_config["payload"]
        )
        flow_results.append(result)
        await asyncio.sleep(0.1)  # Small delay between operations
    
    # Verify all operations were logged consistently
    successful_operations = [r for r in flow_results if r["overall_success"]]
    assert len(successful_operations) >= 2  # At least 2 should succeed
    
    # Verify database operations completed
    db_operations = [r["db_result"] for r in flow_results if r["db_result"]["success"]]
    assert len(db_operations) >= 2