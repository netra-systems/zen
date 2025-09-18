from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
"""Response Persistence and Recovery Integration Test

env = get_env()
Business Value Justification (BVJ):
- Segment: Enterprise ($20K MRR protection)
- Business Goal: Data Integrity and Disaster Recovery
- Value Impact: Protects against data loss and ensures business continuity
- Revenue Impact: Prevents $20K MRR churn from data loss incidents, ensures enterprise SLA compliance

Test Overview:
Validates response saving to database and recovery after failures, including transaction"""
Tests both PostgreSQL and ClickHouse persistence where applicable."""

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import pytest

        # Set testing environment before imports

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.db.models_postgres import Assistant, Message, Run, Thread
from netra_backend.app.db.postgres import get_postgres_db
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.quality_gate.quality_gate_models import ( )
ContentType,
QualityLevel,
ValidationResult)
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

logger = central_logger.get_logger(__name__)

"""
"""Mock justification decorator per SPEC/testing.xml"""
def decorator(func):
func._mock_justification = reason
return func
return decorator


@pytest.mark.e2e"""
        """Integration test for response persistence and recovery mechanisms"""
        pass

        @pytest.fixture"""
        """Create mocked ClickHouse client for testing"""
    # Mock: Generic component isolation for controlled unit testing
        client_mock = AsyncNone  # TODO: Use real service instead of Mock
    # Mock: Generic component isolation for controlled unit testing
        client_mock.execute = AsyncNone  # TODO: Use real service instead of Mock
    # Mock: Async component isolation for testing without real async operations
        client_mock.fetch = AsyncMock(return_value=[])
    # Mock: Generic component isolation for controlled unit testing
        client_mock.close = AsyncNone  # TODO: Use real service instead of Mock
        await asyncio.sleep(0)
        return client_mock

        @pytest.fixture"""
        """Create real PostgreSQL session for integration testing"""
        pass
        async with get_postgres_db() as session:
        yield session

        @pytest.fixture"""
        """Create quality service for response validation"""
        await asyncio.sleep(0)
        return QualityGateService()

        @pytest.fixture
        @pytest.mark.e2e"""
        """Create test thread for message persistence"""
        pass"""
        id="formatted_string",
        created_at=int(datetime.now(UTC).timestamp())
        
        postgres_session.add(thread)
        await postgres_session.commit()
        await asyncio.sleep(0)
        return thread

        @pytest.fixture
        @pytest.mark.e2e
    async def test_assistant(self, postgres_session):
        """Create test assistant for message persistence""""""
        id="formatted_string",
        created_at=int(datetime.now(UTC).timestamp()),
        model=LLMModel.GEMINI_2_5_FLASH.value,
        name="Test Assistant"
            
        postgres_session.add(assistant)
        await postgres_session.commit()
        await asyncio.sleep(0)
        return assistant

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_message_persistence_transaction_integrity(self, postgres_session, test_thread, test_assistant):
"""Test message persistence maintains transaction integrity"""
pass
test_responses = [ )"""
"content": "GPU optimization: 24GB -> 16GB (33% reduction). Latency: 200ms -> 125ms (37.5% improvement).",
"role": "assistant",
"metadata": {"test_type": "transaction_integrity", "quality_validated": True}
},
{ )
"content": "Database query performance: 850ms -> 180ms (78.8% improvement) using B-tree indexing.",
"role": "assistant",
"metadata": {"test_type": "transaction_integrity", "quality_validated": True}
                
                

persisted_messages = []

                # Test atomic transaction for multiple message persistence
try:
async with postgres_session.begin():
for i, response in enumerate(test_responses):
message = Message( )
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role=response["role"],
content=[{"type": "text", "text": response["content"]}],
metadata_=response["metadata"]
                            
postgres_session.add(message)
persisted_messages.append(message)

                            # Commit should persist all messages atomically
await postgres_session.commit()

except Exception as e:
await postgres_session.rollback()
pytest.fail("formatted_string")

                                # Verify all messages were persisted
stmt = select(Message).where(Message.thread_id == test_thread.id)
result = await postgres_session.execute(stmt)
saved_messages = result.scalars().all()

assert len(saved_messages) == len(test_responses)

                                # Verify content integrity
for saved_msg in saved_messages:
assert saved_msg.content[0]["text"] in [r["content"] for r in test_responses]
assert saved_msg.metadata_["test_type"] == "transaction_integrity"
assert saved_msg.metadata_["quality_validated"] == True

logger.info("formatted_string")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_response_persistence_rollback_scenario(self, postgres_session, test_thread, test_assistant):
"""Test response persistence handles rollback scenarios correctly"""
valid_response = {"content": "Memory allocation optimized: 32GB -> 20GB (37.5% reduction).",, "role": "assistant",, "metadata": {"test_type": "rollback_scenario"}}
                                        # Simulate transaction that should rollback
rollback_occurred = False
try:
async with postgres_session.begin():
                                                # Add valid message first
message1 = Message( )
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role=valid_response["role"],
content=[{"type": "text", "text": valid_response["content"]}],
metadata_=valid_response["metadata"]
                                                
postgres_session.add(message1)

                                                # Force an error to trigger rollback
raise SQLAlchemyError("Simulated database error for rollback test")

except SQLAlchemyError as e:
await postgres_session.rollback()
logger.info("formatted_string")

                                                    # Verify rollback worked - no messages should be persisted
assert rollback_occurred == True

stmt = select(Message).where(Message.thread_id == test_thread.id)
result = await postgres_session.execute(stmt)
saved_messages = result.scalars().all()

assert len(saved_messages) == 0, "Rollback should have prevented message persistence"

                                                    # Now verify normal transaction works after rollback
try:
message2 = Message( )
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role=valid_response["role"],
content=[{"type": "text", "text": valid_response["content"]}],
metadata_={"test_type": "post_rollback_recovery"}
                                                        
postgres_session.add(message2)
await postgres_session.commit()

                                                        # Verify recovery works
stmt = select(Message).where(Message.thread_id == test_thread.id)
result = await postgres_session.execute(stmt)
recovered_messages = result.scalars().all()

assert len(recovered_messages) == 1
assert recovered_messages[0].metadata_["test_type"] == "post_rollback_recovery"

except Exception as e:
pytest.fail("formatted_string")

logger.info("Rollback scenario and recovery validation completed")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_crash_recovery_and_data_consistency(self, postgres_session, test_thread, test_assistant):
"""Test crash recovery maintains data consistency"""
pass
                                                                # Simulate partial state before crash
pre_crash_messages = [ )"""
"content": "GPU cluster optimization: 52% -> 89% utilization (+37pp).",
"role": "assistant",
"metadata": {"test_type": "crash_recovery", "status": "pre_crash"}
                                                                
                                                                

                                                                # Persist pre-crash data
for msg_data in pre_crash_messages:
message = Message( )
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role=msg_data["role"],
content=[{"type": "text", "text": msg_data["content"]}],
metadata_=msg_data["metadata"]
                                                                    
postgres_session.add(message)

await postgres_session.commit()

                                                                    # Simulate crash scenario - session is lost, new session created
                                                                    # Verify data consistency after "crash"
async with get_postgres_db() as new_session:
                                                                        # Check data integrity after crash
stmt = select(Message).where(Message.thread_id == test_thread.id)
result = await new_session.execute(stmt)
recovered_messages = result.scalars().all()

assert len(recovered_messages) == len(pre_crash_messages)

for recovered_msg in recovered_messages:
assert recovered_msg.metadata_["status"] == "pre_crash"
assert recovered_msg.content[0]["text"] in [m["content"] for m in pre_crash_messages]

                                                                            # Test post-crash recovery - add new message
post_crash_message = Message( )
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role="assistant",
content=[{"type": "text", "text": "Memory optimization: 24GB -> 16GB post-crash recovery."}],
metadata_={"test_type": "crash_recovery", "status": "post_crash"}
                                                                            
new_session.add(post_crash_message)
await new_session.commit()

                                                                            # Verify complete data consistency
stmt = select(Message).where(Message.thread_id == test_thread.id)
result = await new_session.execute(stmt)
all_messages = result.scalars().all()

assert len(all_messages) == 2  # Pre-crash + post-crash

statuses = [msg.metadata_["status"] for msg in all_messages]
assert "pre_crash" in statuses
assert "post_crash" in statuses

logger.info("Crash recovery and data consistency validation completed")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_concurrent_persistence_consistency(self, postgres_session, test_thread, test_assistant):
"""Test concurrent response persistence maintains consistency""""""
"formatted_string"
for i in range(10)
                                                                                

                                                                                # Create concurrent persistence tasks
async def persist_response(content: str, index: int) -> str:
"""Persist single response with potential concurrency"""
pass
async with get_postgres_db() as session:"""
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role="assistant",
content=[{"type": "text", "text": content}],
metadata_={"test_type": "concurrent_persistence", "index": index}
        
session.add(message)
await session.commit()
await asyncio.sleep(0)
return message.id

        # Execute concurrent persistence
start_time = datetime.now(UTC)
persistence_tasks = [ )
persist_response(content, i)
for i, content in enumerate(concurrent_responses)
        

persisted_ids = await asyncio.gather(*persistence_tasks)
end_time = datetime.now(UTC)

        # Verify all concurrent operations succeeded
assert len(persisted_ids) == len(concurrent_responses)
assert all(isinstance(msg_id, str) for msg_id in persisted_ids)

        # Verify data consistency after concurrent operations
stmt = select(Message).where(Message.thread_id == test_thread.id)
result = await postgres_session.execute(stmt)
all_messages = result.scalars().all()

        # Filter only concurrent persistence test messages
concurrent_messages = [ )
msg for msg in all_messages
if msg.metadata_ and msg.metadata_.get("test_type") == "concurrent_persistence"
        

assert len(concurrent_messages) == len(concurrent_responses)

        # Verify no data corruption
indices = [msg.metadata_["index"] for msg in concurrent_messages]
assert set(indices) == set(range(len(concurrent_responses)))

        # Verify performance under concurrency
total_time = (end_time - start_time).total_seconds()
assert total_time < 5.0  # Should complete within reasonable time

logger.info("formatted_string")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_response_quality_persistence_integration(self, postgres_session, test_thread, test_assistant, quality_service):
"""Test integration of response quality validation with persistence"""
quality_test_responses = [ )"""
"content": "GPU memory: 24GB -> 16GB (33% reduction). Inference latency: 200ms -> 125ms (37.5% improvement). Cost: $2,400/month savings.",
"expected_quality": "high",
"should_persist": True
},
{ )
"content": "Performance was improved through optimization techniques.",
"expected_quality": "low",
"should_persist": False
            
            

quality_integration_results = []

for response in quality_test_responses:
                # Validate quality first
quality_result = await quality_service.validate_content(content=response["content"],, content_type=ContentType.OPTIMIZATION,, context={"test_type": "quality_persistence_integration"})
                # Persist based on quality validation
if quality_result.passed and response["should_persist"]:
message = Message( )
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role="assistant",
content=[{"type": "text", "text": response["content"]}],
metadata_={"test_type": "quality_persistence_integration",, "quality_score": quality_result.metrics.overall_score,, "quality_level": quality_result.metrics.quality_level.value,, "quality_validated": True}
postgres_session.add(message)
await postgres_session.commit()

quality_integration_results.append({ ))
"content_preview": response["content"][:50] + "...",
"quality_passed": quality_result.passed,
"persisted": True,
"quality_score": quality_result.metrics.overall_score
                    
else:
quality_integration_results.append({ ))
"content_preview": response["content"][:50] + "...",
"quality_passed": quality_result.passed,
"persisted": False,
"quality_score": quality_result.metrics.overall_score
                        

                        # Verify quality-persistence integration
stmt = select(Message).where(Message.thread_id == test_thread.id)
result = await postgres_session.execute(stmt)
persisted_messages = result.scalars().all()

                        # Filter quality integration test messages
quality_messages = [ )
msg for msg in persisted_messages
if msg.metadata_ and msg.metadata_.get("test_type") == "quality_persistence_integration"
                        

                        # Verify only high-quality responses were persisted
assert len(quality_messages) == 1  # Only the high-quality response
assert quality_messages[0].metadata_["quality_validated"] == True
assert quality_messages[0].metadata_["quality_score"] > 0.5

logger.info("formatted_string")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_multi_database_persistence_consistency(self, postgres_session, clickhouse_client):
"""Test consistency across PostgreSQL and ClickHouse persistence""""""
multi_db_test_data = {"message_id": "formatted_string",, "thread_id": "formatted_string",, "content": "Database optimization: Query time 850ms -> 180ms (78.8% improvement)",, "timestamp": datetime.now(UTC),, "metadata": {"test_type": "multi_db_consistency"}}
                            # Persist to PostgreSQL (transactional data)
postgres_success = False
try:
                                # Note: Using dummy thread/assistant for this test
message = Message( )
id=multi_db_test_data["message_id"],
created_at=int(multi_db_test_data["timestamp"].timestamp()),
thread_id=multi_db_test_data["thread_id"],
assistant_id="test_assistant_id",
role="assistant",
content=[{"type": "text", "text": multi_db_test_data["content"]}],
metadata_=multi_db_test_data["metadata"]
                                
postgres_session.add(message)
await postgres_session.commit()
except Exception as e:
logger.warning("formatted_string")

                                    # Persist to ClickHouse (analytical data)
clickhouse_success = False
try:
                                        # Mock ClickHouse insertion
await clickhouse_client.execute( )
"INSERT INTO message_analytics VALUES",
[{ ))
"message_id": multi_db_test_data["message_id"],
"thread_id": multi_db_test_data["thread_id"],
"content_length": len(multi_db_test_data["content"]),
"timestamp": multi_db_test_data["timestamp"],
"content_type": "optimization"
                                        
                                        
clickhouse_success = True
except Exception as e:
logger.warning("formatted_string")

                                            # Verify consistency check (both should succeed or fail together)
if postgres_success and clickhouse_success:
                                                # Verify PostgreSQL data
stmt = select(Message).where(Message.id == multi_db_test_data["message_id"])
result = await postgres_session.execute(stmt)
pg_message = result.scalar_one_or_none()

assert pg_message is not None
assert pg_message.content[0]["text"] == multi_db_test_data["content"]

                                                # Verify ClickHouse data (mocked)
clickhouse_client.execute.assert_called()

logger.info("Multi-database persistence consistency validated")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_persistence_performance_under_load(self, postgres_session, test_thread, test_assistant):
"""Test persistence performance under high load conditions""""""
"formatted_string"
for i in range(50)  # Moderate load for testing
                                                    

                                                    # Execute load test
start_time = datetime.now(UTC)

async def batch_persist(batch_responses: List[str]) -> int:
"""Persist batch of responses"""
pass
batch_count = 0
async with get_postgres_db() as session:
for content in batch_responses:"""
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role="assistant",
content=[{"type": "text", "text": content}],
metadata_={"test_type": "load_test", "batch": True}
            
session.add(message)
batch_count += 1
await session.commit()
await asyncio.sleep(0)
return batch_count

            # Process in batches for better performance
batch_size = 10
batch_tasks = []
for i in range(0, len(load_test_responses), batch_size):
batch = load_test_responses[i:i + batch_size]
batch_tasks.append(batch_persist(batch))

batch_results = await asyncio.gather(*batch_tasks)
end_time = datetime.now(UTC)

                # Verify load test results
total_persisted = sum(batch_results)
total_time = (end_time - start_time).total_seconds()

assert total_persisted == len(load_test_responses)
assert total_time < 10.0  # Should handle load efficiently

                # Verify data integrity under load
stmt = select(Message).where(Message.thread_id == test_thread.id)
result = await postgres_session.execute(stmt)
all_messages = result.scalars().all()

load_test_messages = [ )
msg for msg in all_messages
if msg.metadata_ and msg.metadata_.get("test_type") == "load_test"
                

assert len(load_test_messages) == len(load_test_responses)

logger.info("formatted_string")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_data_recovery_after_partial_failure(self, postgres_session, test_thread, test_assistant):
"""Test data recovery mechanisms after partial system failures"""
                    # Create baseline data"""
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role="assistant",
content=[{"type": "text", "text": "Baseline: GPU optimization 45% improvement."}],
metadata_={"test_type": "recovery_test", "status": "baseline"}
                    
postgres_session.add(baseline_message)
await postgres_session.commit()

                    # Simulate partial failure scenario
recovery_test_data = [ )
{"content": "Recovery test 1: Memory optimization successful.", "should_fail": False},
{"content": "Recovery test 2: Database optimization failed.", "should_fail": True},
{"content": "Recovery test 3: Post-failure recovery successful.", "should_fail": False}
                    

recovery_results = []
for test_data in recovery_test_data:
try:
if test_data["should_fail"]:
                                # Simulate failure
raise Exception("Simulated partial failure")

                                # Normal persistence
message = Message( )
id="formatted_string",
created_at=int(datetime.now(UTC).timestamp()),
thread_id=test_thread.id,
assistant_id=test_assistant.id,
role="assistant",
content=[{"type": "text", "text": test_data["content"]}],
metadata_={"test_type": "recovery_test", "status": "recovered"}
                                
postgres_session.add(message)
await postgres_session.commit()

recovery_results.append({"content": test_data["content"], "persisted": True})

except Exception as e:
                                    # Handle failure gracefully
await postgres_session.rollback()
recovery_results.append({"content": test_data["content"], "persisted": False, "error": str(e)})

                                    # Verify recovery behavior
successful_recoveries = sum(1 for r in recovery_results if r["persisted"])
failed_operations = sum(1 for r in recovery_results if not r["persisted"])

assert successful_recoveries == 2  # 2 should succeed
assert failed_operations == 1      # 1 should fail

                                    # Verify system can continue after partial failures
stmt = select(Message).where(Message.thread_id == test_thread.id)
result = await postgres_session.execute(stmt)
all_messages = result.scalars().all()

recovery_messages = [ )
msg for msg in all_messages
if msg.metadata_ and msg.metadata_.get("test_type") == "recovery_test"
                                    

                                    # Should have baseline + 2 successful recoveries
assert len(recovery_messages) == 3

logger.info("formatted_string")

class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
"""
        """Use real service instance."""
    # TODO: Initialize real service
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
"""
        """Send JSON message."""
        pass"""
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
"""
        """Get all sent messages."""
        pass
        await asyncio.sleep(0)
        return self.messages_sent.copy()"""