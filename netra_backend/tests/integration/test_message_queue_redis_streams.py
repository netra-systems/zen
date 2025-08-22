"""L3 Integration Test: Message Queue Processing with Redis Streams

Business Value Justification (BVJ):
- Segment: All tiers (reliable async processing is universal)
- Business Goal: Ensures reliable async message processing for critical workflows
- Value Impact: Guarantees message delivery, processing order, and fault tolerance
- Strategic Impact: Protects $75K MRR by ensuring reliable async operations and preventing message loss

L3 Test: Real Redis Streams with producer/consumer patterns, acknowledgments,
retries, dead letter queue, and stream processing validation.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest
import redis.asyncio as redis
from logging_config import central_logger

from netra_backend.app.redis_manager import RedisManager

from netra_backend.tests.integration.helpers.redis_l3_helpers import (
    RedisContainer,
    verify_redis_connection,
)

logger = central_logger.get_logger(__name__)

@dataclass
class StreamMessage:
    """Represents a message in Redis Stream."""
    id: str
    stream_name: str
    data: Dict[str, Any]
    timestamp: float
    processed: bool = False
    acknowledged: bool = False
    retry_count: int = 0
    consumer_group: Optional[str] = None
    consumer_id: Optional[str] = None

@dataclass
class StreamProcessingStats:
    """Statistics for stream processing operations."""
    messages_produced: int = 0
    messages_consumed: int = 0
    messages_acknowledged: int = 0
    messages_retried: int = 0
    messages_failed: int = 0
    dead_letter_messages: int = 0
    processing_errors: int = 0
    consumer_groups_created: int = 0
    streams_created: int = 0

class MessageQueueRedisStreamsManager:
    """Manages message queue testing with Redis Streams."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.streams = set()
        self.consumer_groups = set()
        self.test_messages = []
        self.stats = StreamProcessingStats()
        self.stream_configs = {
            "high_priority": {"max_len": 1000, "retry_limit": 3},
            "medium_priority": {"max_len": 5000, "retry_limit": 5},
            "low_priority": {"max_len": 10000, "retry_limit": 2},
            "dead_letter": {"max_len": 1000, "retry_limit": 0}
        }
    
    async def test_producer_consumer_patterns(self, message_count: int) -> Dict[str, Any]:
        """Test basic producer-consumer patterns with Redis Streams."""
        pattern_results = {
            "streams_tested": 0,
            "messages_produced": 0,
            "messages_consumed": 0,
            "pattern_success_rate": 0,
            "production_failures": 0,
            "consumption_failures": 0
        }
        
        for stream_type, config in self.stream_configs.items():
            if stream_type == "dead_letter":  # Skip dead letter for basic testing
                continue
            
            stream_name = f"test_stream_{stream_type}_{uuid.uuid4().hex[:8]}"
            consumer_group = f"group_{stream_type}"
            consumer_id = f"consumer_{stream_type}_1"
            
            try:
                # Create consumer group
                await self._create_consumer_group(stream_name, consumer_group)
                
                # Produce messages
                produced_messages = await self._produce_messages(
                    stream_name, message_count // len(self.stream_configs), stream_type
                )
                pattern_results["messages_produced"] += produced_messages
                
                # Consume messages
                consumed_messages = await self._consume_messages(
                    stream_name, consumer_group, consumer_id, produced_messages
                )
                pattern_results["messages_consumed"] += consumed_messages
                
                pattern_results["streams_tested"] += 1
                
            except Exception as e:
                logger.error(f"Producer-consumer pattern failed for {stream_type}: {e}")
                if "produce" in str(e).lower():
                    pattern_results["production_failures"] += 1
                else:
                    pattern_results["consumption_failures"] += 1
        
        # Calculate success rate
        if pattern_results["messages_produced"] > 0:
            pattern_results["pattern_success_rate"] = (
                pattern_results["messages_consumed"] / pattern_results["messages_produced"] * 100
            )
        
        return pattern_results
    
    async def test_acknowledgment_mechanisms(self, ack_test_count: int) -> Dict[str, Any]:
        """Test message acknowledgment mechanisms in Redis Streams."""
        ack_results = {
            "messages_for_ack": 0,
            "successful_acks": 0,
            "failed_acks": 0,
            "pending_messages": 0,
            "ack_success_rate": 0,
            "ack_processing_time": []
        }
        
        stream_name = f"ack_test_stream_{uuid.uuid4().hex[:8]}"
        consumer_group = "ack_test_group"
        consumer_id = "ack_consumer_1"
        
        # Create consumer group and produce test messages
        await self._create_consumer_group(stream_name, consumer_group)
        produced_count = await self._produce_messages(stream_name, ack_test_count, "acknowledgment_test")
        
        # Consume messages for acknowledgment testing
        consumed_messages = await self._consume_messages_for_ack_test(
            stream_name, consumer_group, consumer_id, produced_count
        )
        
        ack_results["messages_for_ack"] = len(consumed_messages)
        
        # Test acknowledgments
        for message in consumed_messages:
            ack_start = time.time()
            
            try:
                # Acknowledge message
                ack_count = await self.redis_client.xack(
                    stream_name, consumer_group, message["id"]
                )
                
                ack_time = time.time() - ack_start
                ack_results["ack_processing_time"].append(ack_time)
                
                if ack_count > 0:
                    ack_results["successful_acks"] += 1
                    self.stats.messages_acknowledged += 1
                else:
                    ack_results["failed_acks"] += 1
                
            except Exception as e:
                logger.error(f"Acknowledgment failed for message {message['id']}: {e}")
                ack_results["failed_acks"] += 1
        
        # Check for pending messages
        try:
            pending_info = await self.redis_client.xpending(stream_name, consumer_group)
            ack_results["pending_messages"] = pending_info.get("pending", 0)
        except Exception as e:
            logger.warning(f"Failed to get pending messages: {e}")
        
        # Calculate metrics
        if ack_results["messages_for_ack"] > 0:
            ack_results["ack_success_rate"] = (
                ack_results["successful_acks"] / ack_results["messages_for_ack"] * 100
            )
        
        if ack_results["ack_processing_time"]:
            ack_results["avg_ack_time"] = sum(ack_results["ack_processing_time"]) / len(ack_results["ack_processing_time"])
            ack_results["max_ack_time"] = max(ack_results["ack_processing_time"])
        
        return ack_results
    
    async def test_retry_mechanisms(self, retry_test_count: int) -> Dict[str, Any]:
        """Test message retry mechanisms and failure handling."""
        retry_results = {
            "messages_for_retry": 0,
            "retry_attempts": 0,
            "successful_retries": 0,
            "max_retries_reached": 0,
            "retry_success_rate": 0,
            "retry_processing_times": []
        }
        
        stream_name = f"retry_test_stream_{uuid.uuid4().hex[:8]}"
        consumer_group = "retry_test_group"
        consumer_id = "retry_consumer_1"
        
        # Create consumer group and produce messages
        await self._create_consumer_group(stream_name, consumer_group)
        produced_count = await self._produce_messages(stream_name, retry_test_count, "retry_test")
        
        retry_results["messages_for_retry"] = produced_count
        
        # Simulate message processing with failures and retries
        max_retries = 3
        
        for attempt in range(max_retries + 1):
            retry_start = time.time()
            
            # Read messages
            try:
                messages = await self.redis_client.xreadgroup(
                    consumer_group, consumer_id,
                    {stream_name: ">"},
                    count=retry_test_count,
                    block=100
                )
                
                if messages:
                    stream_messages = messages[0][1]  # Get messages from first stream
                    
                    for msg_id, fields in stream_messages:
                        retry_results["retry_attempts"] += 1
                        
                        # Simulate processing with failure rate
                        success = await self._simulate_message_processing(msg_id, fields, attempt)
                        
                        if success:
                            # Acknowledge successful processing
                            await self.redis_client.xack(stream_name, consumer_group, msg_id)
                            retry_results["successful_retries"] += 1
                            self.stats.messages_acknowledged += 1
                        else:
                            # Message will be retried
                            self.stats.messages_retried += 1
                            
                            if attempt >= max_retries:
                                retry_results["max_retries_reached"] += 1
                                # Move to dead letter queue
                                await self._move_to_dead_letter_queue(stream_name, msg_id, fields)
                
                retry_time = time.time() - retry_start
                retry_results["retry_processing_times"].append(retry_time)
                
            except Exception as e:
                logger.error(f"Retry attempt {attempt} failed: {e}")
                self.stats.processing_errors += 1
        
        # Calculate retry metrics
        if retry_results["retry_attempts"] > 0:
            retry_results["retry_success_rate"] = (
                retry_results["successful_retries"] / retry_results["retry_attempts"] * 100
            )
        
        if retry_results["retry_processing_times"]:
            retry_results["avg_retry_time"] = sum(retry_results["retry_processing_times"]) / len(retry_results["retry_processing_times"])
        
        return retry_results
    
    async def test_dead_letter_queue_handling(self, dlq_test_count: int) -> Dict[str, Any]:
        """Test dead letter queue handling for failed messages."""
        dlq_results = {
            "messages_sent_to_dlq": 0,
            "dlq_messages_retrieved": 0,
            "dlq_processing_successful": 0,
            "dlq_storage_verified": 0,
            "dlq_success_rate": 0
        }
        
        main_stream = f"main_stream_{uuid.uuid4().hex[:8]}"
        dlq_stream = f"dead_letter_queue_{uuid.uuid4().hex[:8]}"
        consumer_group = "dlq_test_group"
        consumer_id = "dlq_consumer_1"
        
        # Create consumer groups
        await self._create_consumer_group(main_stream, consumer_group)
        await self._create_consumer_group(dlq_stream, f"{consumer_group}_dlq")
        
        # Produce messages that will fail processing
        failed_message_data = []
        
        for i in range(dlq_test_count):
            message_data = {
                "id": f"dlq_test_{i}",
                "type": "failing_message",
                "data": f"test_data_{i}",
                "will_fail": True,
                "attempt_count": 0
            }
            
            msg_id = await self.redis_client.xadd(main_stream, message_data)
            failed_message_data.append((msg_id, message_data))
            self.stats.messages_produced += 1
        
        # Process messages with failures to trigger DLQ
        for msg_id, msg_data in failed_message_data:
            try:
                # Simulate failed processing
                await self._simulate_failed_processing(main_stream, consumer_group, msg_id, msg_data)
                
                # Move to dead letter queue
                await self._move_to_dead_letter_queue(dlq_stream, msg_id, msg_data)
                dlq_results["messages_sent_to_dlq"] += 1
                self.stats.dead_letter_messages += 1
                
            except Exception as e:
                logger.error(f"DLQ processing failed for message {msg_id}: {e}")
        
        # Verify DLQ storage and retrieval
        try:
            dlq_messages = await self.redis_client.xread({dlq_stream: "0-0"}, count=dlq_test_count)
            
            if dlq_messages:
                retrieved_messages = dlq_messages[0][1]
                dlq_results["dlq_messages_retrieved"] = len(retrieved_messages)
                
                # Verify message integrity in DLQ
                for msg_id, fields in retrieved_messages:
                    if fields.get("type") == "failing_message":
                        dlq_results["dlq_storage_verified"] += 1
                    
                    # Attempt DLQ processing (manual intervention simulation)
                    dlq_success = await self._process_dlq_message(msg_id, fields)
                    if dlq_success:
                        dlq_results["dlq_processing_successful"] += 1
        
        except Exception as e:
            logger.error(f"DLQ verification failed: {e}")
        
        # Calculate DLQ metrics
        if dlq_results["messages_sent_to_dlq"] > 0:
            dlq_results["dlq_success_rate"] = (
                dlq_results["dlq_storage_verified"] / dlq_results["messages_sent_to_dlq"] * 100
            )
        
        return dlq_results
    
    async def test_stream_concurrent_processing(self, concurrent_count: int) -> Dict[str, Any]:
        """Test concurrent stream processing with multiple consumers."""
        concurrent_results = {
            "consumers_tested": 0,
            "total_messages_processed": 0,
            "concurrent_processing_success": 0,
            "consumer_coordination_accurate": 0,
            "message_distribution_fair": 0,
            "processing_conflicts": 0
        }
        
        stream_name = f"concurrent_stream_{uuid.uuid4().hex[:8]}"
        consumer_group = "concurrent_group"
        
        # Create consumer group
        await self._create_consumer_group(stream_name, consumer_group)
        
        # Produce messages for concurrent processing
        message_count = concurrent_count * 10
        produced_count = await self._produce_messages(stream_name, message_count, "concurrent_test")
        
        # Create concurrent consumer tasks
        consumer_tasks = []
        
        for i in range(concurrent_count):
            consumer_id = f"concurrent_consumer_{i}"
            task = self._concurrent_consumer_worker(
                stream_name, consumer_group, consumer_id, i
            )
            consumer_tasks.append(task)
        
        # Run concurrent consumers
        consumer_results = await asyncio.gather(*consumer_tasks, return_exceptions=True)
        
        # Analyze concurrent processing results
        total_processed = 0
        successful_consumers = 0
        processing_conflicts = 0
        consumer_message_counts = []
        
        for i, result in enumerate(consumer_results):
            if isinstance(result, Exception):
                logger.error(f"Concurrent consumer {i} failed: {result}")
                continue
            
            concurrent_results["consumers_tested"] += 1
            total_processed += result["messages_processed"]
            consumer_message_counts.append(result["messages_processed"])
            
            if result["processing_successful"]:
                successful_consumers += 1
            
            processing_conflicts += result["conflicts_detected"]
        
        concurrent_results["total_messages_processed"] = total_processed
        concurrent_results["concurrent_processing_success"] = successful_consumers
        concurrent_results["processing_conflicts"] = processing_conflicts
        
        # Check message distribution fairness
        if consumer_message_counts:
            avg_messages = sum(consumer_message_counts) / len(consumer_message_counts)
            fair_distribution = all(
                abs(count - avg_messages) <= avg_messages * 0.3  # 30% tolerance
                for count in consumer_message_counts
            )
            
            if fair_distribution:
                concurrent_results["message_distribution_fair"] = 1
        
        # Check consumer coordination accuracy
        if total_processed <= produced_count:  # No double processing
            concurrent_results["consumer_coordination_accurate"] = 1
        
        # Calculate success rates
        if concurrent_results["consumers_tested"] > 0:
            concurrent_results["consumer_success_rate"] = (
                concurrent_results["concurrent_processing_success"] / concurrent_results["consumers_tested"] * 100
            )
        
        return concurrent_results
    
    async def _create_consumer_group(self, stream_name: str, group_name: str) -> bool:
        """Create consumer group for stream."""
        try:
            await self.redis_client.xgroup_create(
                stream_name, group_name, id="0", mkstream=True
            )
            self.consumer_groups.add(f"{stream_name}:{group_name}")
            self.streams.add(stream_name)
            self.stats.consumer_groups_created += 1
            self.stats.streams_created += 1
            return True
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                return True  # Group already exists
            logger.error(f"Failed to create consumer group {group_name}: {e}")
            return False
    
    async def _produce_messages(self, stream_name: str, count: int, message_type: str) -> int:
        """Produce messages to stream."""
        produced = 0
        
        for i in range(count):
            try:
                message_data = {
                    "id": f"{message_type}_{i}_{uuid.uuid4().hex[:8]}",
                    "type": message_type,
                    "data": json.dumps({"index": i, "timestamp": time.time()}),
                    "priority": "high" if i % 5 == 0 else "normal",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                msg_id = await self.redis_client.xadd(stream_name, message_data)
                
                stream_message = StreamMessage(
                    id=msg_id,
                    stream_name=stream_name,
                    data=message_data,
                    timestamp=time.time()
                )
                
                self.test_messages.append(stream_message)
                produced += 1
                self.stats.messages_produced += 1
                
            except Exception as e:
                logger.error(f"Failed to produce message {i}: {e}")
        
        return produced
    
    async def _consume_messages(self, stream_name: str, group_name: str, consumer_id: str, expected_count: int) -> int:
        """Consume messages from stream."""
        consumed = 0
        
        try:
            messages = await self.redis_client.xreadgroup(
                group_name, consumer_id,
                {stream_name: ">"},
                count=expected_count,
                block=1000
            )
            
            if messages:
                stream_messages = messages[0][1]
                consumed = len(stream_messages)
                self.stats.messages_consumed += consumed
                
                # Acknowledge all messages
                for msg_id, fields in stream_messages:
                    await self.redis_client.xack(stream_name, group_name, msg_id)
                    self.stats.messages_acknowledged += 1
        
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")
        
        return consumed
    
    async def _consume_messages_for_ack_test(self, stream_name: str, group_name: str, consumer_id: str, count: int) -> List[Dict]:
        """Consume messages specifically for acknowledgment testing."""
        consumed_messages = []
        
        try:
            messages = await self.redis_client.xreadgroup(
                group_name, consumer_id,
                {stream_name: ">"},
                count=count,
                block=1000
            )
            
            if messages:
                stream_messages = messages[0][1]
                
                for msg_id, fields in stream_messages:
                    consumed_messages.append({
                        "id": msg_id,
                        "fields": fields
                    })
                
                self.stats.messages_consumed += len(consumed_messages)
        
        except Exception as e:
            logger.error(f"Failed to consume messages for ack test: {e}")
        
        return consumed_messages
    
    async def _simulate_message_processing(self, msg_id: str, fields: Dict, attempt: int) -> bool:
        """Simulate message processing with configurable failure rate."""
        # Simulate processing time
        await asyncio.sleep(0.01)
        
        # Simulate failure rate that decreases with retries
        failure_rate = max(0.3 - (attempt * 0.1), 0.1)
        
        import random
        success = random.random() > failure_rate
        
        if not success:
            self.stats.processing_errors += 1
        
        return success
    
    async def _simulate_failed_processing(self, stream_name: str, group_name: str, msg_id: str, msg_data: Dict):
        """Simulate failed message processing."""
        # Simulate processing failure
        await asyncio.sleep(0.005)
        self.stats.messages_failed += 1
        
        # Don't acknowledge the message (simulates failure)
        logger.debug(f"Simulated processing failure for message {msg_id}")
    
    async def _move_to_dead_letter_queue(self, dlq_stream: str, msg_id: str, msg_data: Dict):
        """Move failed message to dead letter queue."""
        try:
            dlq_data = {
                "original_id": msg_id,
                "original_data": json.dumps(msg_data),
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "reason": "max_retries_exceeded",
                "type": "dead_letter"
            }
            
            await self.redis_client.xadd(dlq_stream, dlq_data)
            self.stats.dead_letter_messages += 1
            
        except Exception as e:
            logger.error(f"Failed to move message to DLQ: {e}")
    
    async def _process_dlq_message(self, msg_id: str, fields: Dict) -> bool:
        """Process message from dead letter queue."""
        try:
            # Simulate manual DLQ processing
            await asyncio.sleep(0.02)
            
            # For testing, assume 80% success rate for DLQ processing
            import random
            success = random.random() > 0.2
            
            return success
            
        except Exception as e:
            logger.error(f"DLQ message processing failed: {e}")
            return False
    
    async def _concurrent_consumer_worker(self, stream_name: str, group_name: str, consumer_id: str, worker_index: int) -> Dict[str, Any]:
        """Worker function for concurrent consumer testing."""
        worker_result = {
            "worker_index": worker_index,
            "messages_processed": 0,
            "processing_successful": True,
            "conflicts_detected": 0,
            "processing_time": 0
        }
        
        start_time = time.time()
        
        try:
            # Process messages for a limited time
            end_time = start_time + 5  # 5 seconds of processing
            
            while time.time() < end_time:
                messages = await self.redis_client.xreadgroup(
                    group_name, consumer_id,
                    {stream_name: ">"},
                    count=5,
                    block=100
                )
                
                if messages:
                    stream_messages = messages[0][1]
                    
                    for msg_id, fields in stream_messages:
                        # Simulate processing
                        await asyncio.sleep(0.01)
                        
                        # Acknowledge message
                        ack_count = await self.redis_client.xack(stream_name, group_name, msg_id)
                        
                        if ack_count > 0:
                            worker_result["messages_processed"] += 1
                        else:
                            worker_result["conflicts_detected"] += 1
                
                # Brief pause between reads
                await asyncio.sleep(0.05)
        
        except Exception as e:
            logger.error(f"Concurrent worker {worker_index} failed: {e}")
            worker_result["processing_successful"] = False
        
        worker_result["processing_time"] = time.time() - start_time
        return worker_result
    
    async def cleanup(self):
        """Clean up streams, consumer groups, and test data."""
        try:
            # Clean up consumer groups
            for group_info in self.consumer_groups:
                try:
                    stream_name, group_name = group_info.split(":", 1)
                    await self.redis_client.xgroup_destroy(stream_name, group_name)
                except Exception:
                    pass
            
            # Clean up streams
            for stream_name in self.streams:
                try:
                    await self.redis_client.delete(stream_name)
                except Exception:
                    pass
            
            self.streams.clear()
            self.consumer_groups.clear()
            self.test_messages.clear()
            
            logger.info("Message queue streams cleanup completed")
            
        except Exception as e:
            logger.error(f"Message queue cleanup failed: {e}")
    
    def get_stream_processing_summary(self) -> Dict[str, Any]:
        """Get comprehensive stream processing summary."""
        return {
            "processing_stats": {
                "messages_produced": self.stats.messages_produced,
                "messages_consumed": self.stats.messages_consumed,
                "messages_acknowledged": self.stats.messages_acknowledged,
                "messages_retried": self.stats.messages_retried,
                "messages_failed": self.stats.messages_failed,
                "dead_letter_messages": self.stats.dead_letter_messages,
                "processing_errors": self.stats.processing_errors
            },
            "infrastructure_stats": {
                "streams_created": self.stats.streams_created,
                "consumer_groups_created": self.stats.consumer_groups_created,
                "test_messages_tracked": len(self.test_messages)
            },
            "reliability_metrics": {
                "message_success_rate": (self.stats.messages_acknowledged / self.stats.messages_consumed * 100) if self.stats.messages_consumed > 0 else 0,
                "retry_effectiveness": (self.stats.messages_acknowledged / (self.stats.messages_acknowledged + self.stats.messages_failed) * 100) if (self.stats.messages_acknowledged + self.stats.messages_failed) > 0 else 0,
                "dead_letter_rate": (self.stats.dead_letter_messages / self.stats.messages_produced * 100) if self.stats.messages_produced > 0 else 0
            }
        }

@pytest.mark.L3
@pytest.mark.integration
class TestMessageQueueRedisStreamsL3:
    """L3 integration tests for message queue processing with Redis Streams."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container for streams testing."""
        container = RedisContainer(port=6385)
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client for streams."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        yield client
        await client.close()
    
    @pytest.fixture
    async def streams_manager(self, redis_client):
        """Create message queue streams manager."""
        manager = MessageQueueRedisStreamsManager(redis_client)
        yield manager
        await manager.cleanup()
    
    async def test_producer_consumer_basic_patterns(self, streams_manager):
        """Test basic producer-consumer patterns with Redis Streams."""
        results = await streams_manager.test_producer_consumer_patterns(60)
        
        # Verify stream creation and processing
        assert results["streams_tested"] >= 3, f"Insufficient streams tested: {results['streams_tested']}"
        assert results["messages_produced"] >= 45, f"Insufficient messages produced: {results['messages_produced']}"
        
        # Verify consumption efficiency
        assert results["pattern_success_rate"] >= 90.0, f"Pattern success rate too low: {results['pattern_success_rate']:.1f}%"
        assert results["messages_consumed"] >= 40, f"Insufficient messages consumed: {results['messages_consumed']}"
        
        # Verify minimal failures
        assert results["production_failures"] <= 1, f"Too many production failures: {results['production_failures']}"
        assert results["consumption_failures"] <= 1, f"Too many consumption failures: {results['consumption_failures']}"
        
        logger.info(f"Producer-consumer patterns test completed: {results}")
    
    async def test_acknowledgment_mechanism_validation(self, streams_manager):
        """Test message acknowledgment mechanisms in Redis Streams."""
        results = await streams_manager.test_acknowledgment_mechanisms(25)
        
        # Verify acknowledgment processing
        assert results["messages_for_ack"] >= 20, f"Insufficient messages for ack: {results['messages_for_ack']}"
        assert results["ack_success_rate"] >= 95.0, f"Ack success rate too low: {results['ack_success_rate']:.1f}%"
        
        # Verify acknowledgment performance
        assert results["successful_acks"] >= 20, f"Too few successful acks: {results['successful_acks']}"
        assert results["failed_acks"] <= 2, f"Too many failed acks: {results['failed_acks']}"
        
        # Verify acknowledgment timing
        if "avg_ack_time" in results:
            assert results["avg_ack_time"] < 0.1, f"Average ack time too slow: {results['avg_ack_time']:.3f}s"
        
        # Verify minimal pending messages
        assert results["pending_messages"] <= 3, f"Too many pending messages: {results['pending_messages']}"
        
        logger.info(f"Acknowledgment mechanism test completed: {results}")
    
    async def test_retry_mechanism_resilience(self, streams_manager):
        """Test message retry mechanisms and failure handling."""
        results = await streams_manager.test_retry_mechanisms(20)
        
        # Verify retry processing
        assert results["messages_for_retry"] >= 18, f"Insufficient messages for retry: {results['messages_for_retry']}"
        assert results["retry_attempts"] >= 20, f"Insufficient retry attempts: {results['retry_attempts']}"
        
        # Verify retry effectiveness
        assert results["retry_success_rate"] >= 70.0, f"Retry success rate too low: {results['retry_success_rate']:.1f}%"
        assert results["successful_retries"] >= 15, f"Too few successful retries: {results['successful_retries']}"
        
        # Verify max retry handling
        assert results["max_retries_reached"] >= 3, "Should have some messages reaching max retries"
        
        # Verify retry performance
        if "avg_retry_time" in results:
            assert results["avg_retry_time"] < 2.0, f"Average retry time too slow: {results['avg_retry_time']:.2f}s"
        
        logger.info(f"Retry mechanism test completed: {results}")
    
    async def test_dead_letter_queue_functionality(self, streams_manager):
        """Test dead letter queue handling for failed messages."""
        results = await streams_manager.test_dead_letter_queue_handling(15)
        
        # Verify DLQ message handling
        assert results["messages_sent_to_dlq"] >= 12, f"Insufficient messages sent to DLQ: {results['messages_sent_to_dlq']}"
        assert results["dlq_messages_retrieved"] >= 12, f"Insufficient DLQ messages retrieved: {results['dlq_messages_retrieved']}"
        
        # Verify DLQ storage integrity
        assert results["dlq_success_rate"] >= 90.0, f"DLQ success rate too low: {results['dlq_success_rate']:.1f}%"
        assert results["dlq_storage_verified"] >= 12, f"Too few DLQ messages verified: {results['dlq_storage_verified']}"
        
        # Verify DLQ processing capability
        assert results["dlq_processing_successful"] >= 8, f"Too few DLQ processing successes: {results['dlq_processing_successful']}"
        
        logger.info(f"Dead letter queue test completed: {results}")
    
    async def test_concurrent_stream_processing(self, streams_manager):
        """Test concurrent stream processing with multiple consumers."""
        results = await streams_manager.test_stream_concurrent_processing(8)
        
        # Verify concurrent consumer performance
        assert results["consumers_tested"] >= 6, f"Insufficient consumers tested: {results['consumers_tested']}"
        assert results["consumer_success_rate"] >= 85.0, f"Consumer success rate too low: {results['consumer_success_rate']:.1f}%"
        
        # Verify concurrent processing efficiency
        assert results["total_messages_processed"] >= 50, f"Insufficient messages processed: {results['total_messages_processed']}"
        assert results["concurrent_processing_success"] >= 6, f"Too few successful concurrent processors: {results['concurrent_processing_success']}"
        
        # Verify coordination and fairness
        assert results["consumer_coordination_accurate"] == 1, "Consumer coordination not accurate"
        assert results["message_distribution_fair"] == 1, "Message distribution not fair"
        
        # Verify minimal conflicts
        assert results["processing_conflicts"] <= 5, f"Too many processing conflicts: {results['processing_conflicts']}"
        
        logger.info(f"Concurrent stream processing test completed: {results}")
    
    async def test_stream_processing_performance_comprehensive(self, streams_manager):
        """Test comprehensive stream processing performance."""
        start_time = time.time()
        
        # Run comprehensive stream processing tests
        await asyncio.gather(
            streams_manager.test_producer_consumer_patterns(30),
            streams_manager.test_acknowledgment_mechanisms(15),
            streams_manager.test_retry_mechanisms(12)
        )
        
        total_time = time.time() - start_time
        
        # Get comprehensive summary
        summary = streams_manager.get_stream_processing_summary()
        
        # Verify performance
        assert total_time < 45.0, f"Stream processing tests took too long: {total_time:.2f}s"
        
        # Verify comprehensive processing stats
        processing_stats = summary["processing_stats"]
        assert processing_stats["messages_produced"] >= 40, "Insufficient total messages produced"
        assert processing_stats["messages_consumed"] >= 35, "Insufficient total messages consumed"
        assert processing_stats["messages_acknowledged"] >= 30, "Insufficient total messages acknowledged"
        
        # Verify reliability metrics
        reliability_metrics = summary["reliability_metrics"]
        assert reliability_metrics["message_success_rate"] >= 85.0, f"Message success rate too low: {reliability_metrics['message_success_rate']:.1f}%"
        assert reliability_metrics["retry_effectiveness"] >= 70.0, f"Retry effectiveness too low: {reliability_metrics['retry_effectiveness']:.1f}%"
        
        # Verify infrastructure creation
        infra_stats = summary["infrastructure_stats"]
        assert infra_stats["streams_created"] >= 3, "Insufficient streams created"
        assert infra_stats["consumer_groups_created"] >= 3, "Insufficient consumer groups created"
        
        logger.info(f"Comprehensive stream processing test completed in {total_time:.2f}s: {summary}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])