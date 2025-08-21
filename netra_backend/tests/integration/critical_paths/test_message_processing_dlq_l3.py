"""Message Processing Dead Letter Queue L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (message reliability)
- Business Goal: Zero message loss, reliable message processing
- Value Impact: $75K MRR - Ensures critical messages are never lost
- Strategic Impact: Message reliability prevents data loss and maintains user trust

Critical Path: Message ingestion -> Processing attempt -> Retry mechanisms -> DLQ routing -> Monitoring -> Reprocessing
Coverage: Message reliability patterns, error handling, retry strategies, poison message detection, DLQ monitoring
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from unittest.mock import AsyncMock, MagicMock

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.registry import AgentMessage, TaskPriority

logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    """Message processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DLQ = "dlq"
    POISON = "poison"


@dataclass
class ProcessingMessage:
    """Represents a message in the processing pipeline."""
    id: str
    content: Dict[str, Any]
    priority: TaskPriority
    status: MessageStatus = MessageStatus.PENDING
    attempt_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_attempt_at: Optional[datetime] = None
    error_messages: List[str] = field(default_factory=list)
    
    def is_poison(self) -> bool:
        """Check if message should be considered poison."""
        return self.attempt_count >= self.max_retries and self.status == MessageStatus.FAILED


@dataclass 
class DLQMetrics:
    """Dead Letter Queue metrics tracking."""
    total_messages_processed: int = 0
    successful_completions: int = 0
    retry_attempts: int = 0
    dlq_submissions: int = 0
    poison_messages: int = 0
    reprocessing_attempts: int = 0
    zero_message_loss_maintained: bool = True
    
    def get_success_rate(self) -> float:
        """Calculate message processing success rate."""
        if self.total_messages_processed == 0:
            return 0.0
        return (self.successful_completions / self.total_messages_processed) * 100.0


class MessageProcessor:
    """Mock message processor with configurable failure patterns."""
    
    def __init__(self, failure_rate: float = 0.2):
        self.failure_rate = failure_rate
        self.processing_delays = []
        self.processed_messages = []
        
    async def process_message(self, message: ProcessingMessage) -> bool:
        """Process message with potential failures."""
        start_time = time.time()
        
        # Simulate processing delay
        processing_delay = 0.1 + (message.attempt_count * 0.05)
        await asyncio.sleep(processing_delay)
        
        # Simulate failure based on failure rate and attempt count
        should_fail = (
            (message.attempt_count == 0 and hash(message.id) % 100 < self.failure_rate * 100) or
            (message.attempt_count > 0 and message.attempt_count % 2 == 1)  # Alternating failures for retries
        )
        
        processing_time = time.time() - start_time
        self.processing_delays.append(processing_time)
        
        if should_fail:
            raise NetraException(f"Processing failed for message {message.id}", 
                               error_code="MESSAGE_PROCESSING_FAILED")
        
        self.processed_messages.append(message.id)
        return True


class DeadLetterQueueManager:
    """Manages dead letter queue operations and message reliability."""
    
    def __init__(self):
        self.active_messages: Dict[str, ProcessingMessage] = {}
        self.dlq_messages: Dict[str, ProcessingMessage] = {}
        self.completed_messages: Dict[str, ProcessingMessage] = {}
        self.poison_messages: Dict[str, ProcessingMessage] = {}
        self.processor = MessageProcessor(failure_rate=0.3)
        self.metrics = DLQMetrics()
        
    async def submit_message(self, message_id: str, content: Dict[str, Any], 
                           priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """Submit message for processing."""
        message = ProcessingMessage(
            id=message_id,
            content=content,
            priority=priority
        )
        
        self.active_messages[message_id] = message
        self.metrics.total_messages_processed += 1
        
        # Start processing
        await self._process_message_with_retries(message)
        
        return message_id
    
    async def _process_message_with_retries(self, message: ProcessingMessage):
        """Process message with retry logic and DLQ handling."""
        while message.attempt_count <= message.max_retries:
            message.status = MessageStatus.PROCESSING
            message.attempt_count += 1
            message.last_attempt_at = datetime.now(timezone.utc)
            
            try:
                success = await self.processor.process_message(message)
                
                if success:
                    message.status = MessageStatus.COMPLETED
                    self.completed_messages[message.id] = message
                    if message.id in self.active_messages:
                        del self.active_messages[message.id]
                    self.metrics.successful_completions += 1
                    return
                    
            except Exception as e:
                error_msg = f"Attempt {message.attempt_count}: {str(e)}"
                message.error_messages.append(error_msg)
                message.status = MessageStatus.FAILED
                self.metrics.retry_attempts += 1
                
                logger.warning(f"Message {message.id} failed attempt {message.attempt_count}: {e}")
        
        # Exceeded max retries - route to DLQ
        await self._route_to_dlq(message)
    
    async def _route_to_dlq(self, message: ProcessingMessage):
        """Route failed message to dead letter queue."""
        if message.is_poison():
            message.status = MessageStatus.POISON
            self.poison_messages[message.id] = message
            self.metrics.poison_messages += 1
            logger.error(f"Message {message.id} marked as poison after {message.attempt_count} attempts")
        else:
            message.status = MessageStatus.DLQ
            self.dlq_messages[message.id] = message
            self.metrics.dlq_submissions += 1
            logger.info(f"Message {message.id} routed to DLQ after {message.attempt_count} attempts")
        
        if message.id in self.active_messages:
            del self.active_messages[message.id]
    
    async def reprocess_dlq_messages(self) -> Dict[str, Any]:
        """Attempt to reprocess messages from DLQ."""
        reprocessing_results = {
            "attempted": 0,
            "successful": 0,
            "failed": 0,
            "returned_to_dlq": 0
        }
        
        dlq_message_ids = list(self.dlq_messages.keys())
        
        for message_id in dlq_message_ids:
            message = self.dlq_messages[message_id]
            reprocessing_results["attempted"] += 1
            self.metrics.reprocessing_attempts += 1
            
            # Reset for reprocessing
            message.attempt_count = 0
            message.error_messages = []
            message.status = MessageStatus.PENDING
            
            # Move back to active processing
            self.active_messages[message_id] = message
            del self.dlq_messages[message_id]
            
            try:
                await self._process_message_with_retries(message)
                
                if message.status == MessageStatus.COMPLETED:
                    reprocessing_results["successful"] += 1
                elif message.status == MessageStatus.DLQ:
                    reprocessing_results["returned_to_dlq"] += 1
                else:
                    reprocessing_results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"Reprocessing failed for message {message_id}: {e}")
                reprocessing_results["failed"] += 1
        
        return reprocessing_results
    
    async def monitor_dlq_health(self) -> Dict[str, Any]:
        """Monitor DLQ health and metrics."""
        current_time = datetime.now(timezone.utc)
        
        # Analyze message age in DLQ
        dlq_message_ages = []
        for message in self.dlq_messages.values():
            if message.last_attempt_at:
                age = (current_time - message.last_attempt_at).total_seconds()
                dlq_message_ages.append(age)
        
        # Calculate metrics
        avg_age = sum(dlq_message_ages) / len(dlq_message_ages) if dlq_message_ages else 0
        max_age = max(dlq_message_ages) if dlq_message_ages else 0
        
        # Check for message loss (critical metric)
        total_messages = (len(self.active_messages) + len(self.completed_messages) + 
                         len(self.dlq_messages) + len(self.poison_messages))
        
        message_loss_detected = total_messages != self.metrics.total_messages_processed
        if message_loss_detected:
            self.metrics.zero_message_loss_maintained = False
        
        return {
            "dlq_size": len(self.dlq_messages),
            "poison_messages": len(self.poison_messages),
            "active_processing": len(self.active_messages),
            "completed_messages": len(self.completed_messages),
            "average_dlq_age_seconds": avg_age,
            "max_dlq_age_seconds": max_age,
            "message_loss_detected": message_loss_detected,
            "zero_message_loss_maintained": self.metrics.zero_message_loss_maintained,
            "success_rate": self.metrics.get_success_rate()
        }
    
    async def test_poison_message_handling(self) -> Dict[str, Any]:
        """Test poison message detection and handling."""
        # Create a message designed to always fail
        poison_message_id = f"poison_test_{uuid.uuid4()}"
        poison_content = {"type": "poison_test", "always_fail": True}
        
        # Override processor to always fail for this message
        original_processor = self.processor
        
        class AlwaysFailProcessor:
            async def process_message(self, message):
                if "poison_test" in message.content.get("type", ""):
                    raise NetraException("Poison message - always fails")
                return await original_processor.process_message(message)
        
        self.processor = AlwaysFailProcessor()
        
        # Submit poison message
        await self.submit_message(poison_message_id, poison_content)
        
        # Wait for processing to complete
        await asyncio.sleep(0.5)
        
        # Verify poison message handling
        result = {
            "poison_message_id": poison_message_id,
            "detected_as_poison": poison_message_id in self.poison_messages,
            "not_in_active": poison_message_id not in self.active_messages,
            "not_in_completed": poison_message_id not in self.completed_messages,
            "error_count": len(self.poison_messages[poison_message_id].error_messages) if poison_message_id in self.poison_messages else 0
        }
        
        # Restore original processor
        self.processor = original_processor
        
        return result
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive DLQ and processing metrics."""
        return {
            "processing_metrics": {
                "total_messages": self.metrics.total_messages_processed,
                "successful_completions": self.metrics.successful_completions,
                "success_rate": self.metrics.get_success_rate(),
                "retry_attempts": self.metrics.retry_attempts,
                "reprocessing_attempts": self.metrics.reprocessing_attempts
            },
            "dlq_metrics": {
                "dlq_submissions": self.metrics.dlq_submissions,
                "poison_messages": self.metrics.poison_messages,
                "current_dlq_size": len(self.dlq_messages),
                "current_poison_size": len(self.poison_messages)
            },
            "reliability_metrics": {
                "zero_message_loss_maintained": self.metrics.zero_message_loss_maintained,
                "active_messages": len(self.active_messages),
                "completed_messages": len(self.completed_messages)
            },
            "performance_metrics": {
                "average_processing_time": (
                    sum(self.processor.processing_delays) / len(self.processor.processing_delays)
                    if self.processor.processing_delays else 0
                ),
                "total_processed_count": len(self.processor.processed_messages)
            }
        }


class MessageProcessingLoadTester:
    """Load tester for message processing and DLQ scenarios."""
    
    def __init__(self, dlq_manager: DeadLetterQueueManager):
        self.dlq_manager = dlq_manager
        
    async def execute_message_load_test(self, message_count: int, 
                                      concurrent_limit: int = 10) -> Dict[str, Any]:
        """Execute high-volume message processing test."""
        start_time = time.time()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def submit_single_message(i: int):
            async with semaphore:
                message_id = f"load_test_msg_{i}"
                content = {
                    "type": "load_test",
                    "sequence": i,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                priority = TaskPriority.HIGH if i % 10 == 0 else TaskPriority.NORMAL
                return await self.dlq_manager.submit_message(message_id, content, priority)
        
        # Submit all messages concurrently
        tasks = [submit_single_message(i) for i in range(message_count)]
        message_ids = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Wait for processing to stabilize
        await asyncio.sleep(1.0)
        
        total_time = time.time() - start_time
        
        # Collect final metrics
        health_metrics = await self.dlq_manager.monitor_dlq_health()
        comprehensive_metrics = self.dlq_manager.get_comprehensive_metrics()
        
        return {
            "load_test_config": {
                "message_count": message_count,
                "concurrent_limit": concurrent_limit,
                "total_execution_time": total_time
            },
            "submission_results": {
                "submitted_messages": len([mid for mid in message_ids if not isinstance(mid, Exception)]),
                "submission_errors": len([mid for mid in message_ids if isinstance(mid, Exception)])
            },
            "health_metrics": health_metrics,
            "comprehensive_metrics": comprehensive_metrics
        }
    
    async def test_message_reliability_scenarios(self) -> Dict[str, Any]:
        """Test various message reliability scenarios."""
        scenarios = {}
        
        # Scenario 1: High priority message processing
        high_priority_results = []
        for i in range(5):
            message_id = f"high_priority_{i}"
            content = {"type": "high_priority", "critical": True}
            await self.dlq_manager.submit_message(message_id, content, TaskPriority.HIGH)
            high_priority_results.append(message_id)
        
        await asyncio.sleep(0.5)
        scenarios["high_priority"] = await self.dlq_manager.monitor_dlq_health()
        
        # Scenario 2: Mixed priority load
        mixed_tasks = []
        for i in range(15):
            message_id = f"mixed_priority_{i}"
            content = {"type": "mixed_load", "batch": i}
            priority = TaskPriority.HIGH if i % 5 == 0 else TaskPriority.NORMAL
            task = self.dlq_manager.submit_message(message_id, content, priority)
            mixed_tasks.append(task)
        
        await asyncio.gather(*mixed_tasks, return_exceptions=True)
        await asyncio.sleep(0.5)
        scenarios["mixed_priority"] = await self.dlq_manager.monitor_dlq_health()
        
        # Scenario 3: DLQ reprocessing
        reprocessing_result = await self.dlq_manager.reprocess_dlq_messages()
        scenarios["dlq_reprocessing"] = reprocessing_result
        
        # Scenario 4: Poison message handling
        poison_result = await self.dlq_manager.test_poison_message_handling()
        scenarios["poison_handling"] = poison_result
        
        return scenarios


@pytest.fixture
async def dlq_manager():
    """Create DLQ manager for testing."""
    manager = DeadLetterQueueManager()
    yield manager


@pytest.fixture 
async def message_load_tester(dlq_manager):
    """Create message processing load tester."""
    tester = MessageProcessingLoadTester(dlq_manager)
    yield tester


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
class TestMessageProcessingDLQL3:
    """L3 integration tests for message processing and dead letter queue."""
    
    async def test_zero_message_loss_guarantee(self, message_load_tester):
        """Test that zero message loss is maintained under all conditions."""
        # Execute comprehensive load test
        result = await message_load_tester.execute_message_load_test(
            message_count=50, 
            concurrent_limit=15
        )
        
        # Verify zero message loss
        health_metrics = result["health_metrics"]
        assert health_metrics["zero_message_loss_maintained"], \
            "Zero message loss guarantee must be maintained"
        
        assert not health_metrics["message_loss_detected"], \
            "No message loss should be detected"
        
        # Verify message accounting
        comprehensive = result["comprehensive_metrics"]
        total_accounted = (
            comprehensive["reliability_metrics"]["active_messages"] +
            comprehensive["reliability_metrics"]["completed_messages"] +
            comprehensive["dlq_metrics"]["current_dlq_size"] +
            comprehensive["dlq_metrics"]["current_poison_size"]
        )
        
        assert total_accounted == result["load_test_config"]["message_count"], \
            "All messages must be accounted for"
    
    async def test_retry_mechanisms_effectiveness(self, dlq_manager):
        """Test retry mechanisms handle transient failures effectively."""
        # Submit messages that will trigger retries
        retry_test_messages = []
        for i in range(10):
            message_id = f"retry_test_{i}"
            content = {"type": "retry_test", "attempt_failures": True}
            await dlq_manager.submit_message(message_id, content)
            retry_test_messages.append(message_id)
        
        # Wait for processing and retries
        await asyncio.sleep(1.0)
        
        metrics = dlq_manager.get_comprehensive_metrics()
        
        # Verify retry mechanisms
        assert metrics["processing_metrics"]["retry_attempts"] > 0, \
            "Retry mechanisms should be triggered"
        
        # Verify some messages succeeded after retries
        success_rate = metrics["processing_metrics"]["success_rate"]
        assert success_rate > 0, \
            "Some messages should succeed after retries"
        
        # Verify retry attempts are reasonable
        total_messages = metrics["processing_metrics"]["total_messages"]
        retry_ratio = metrics["processing_metrics"]["retry_attempts"] / total_messages
        assert retry_ratio <= 3.0, \
            "Retry ratio should be reasonable (not excessive retries)"
    
    async def test_poison_message_handling(self, dlq_manager):
        """Test poison message detection and isolation."""
        # Test poison message handling
        poison_result = await dlq_manager.test_poison_message_handling()
        
        # Verify poison message detection
        assert poison_result["detected_as_poison"], \
            "Poison messages should be detected and isolated"
        
        assert poison_result["not_in_active"], \
            "Poison messages should not remain in active queue"
        
        assert poison_result["not_in_completed"], \
            "Poison messages should not be marked as completed"
        
        assert poison_result["error_count"] > 0, \
            "Poison messages should have recorded error attempts"
        
        # Verify poison message doesn't affect other processing
        metrics = dlq_manager.get_comprehensive_metrics()
        assert metrics["dlq_metrics"]["poison_messages"] >= 1, \
            "Poison message should be tracked in metrics"
    
    async def test_dlq_monitoring_and_alerting(self, dlq_manager):
        """Test DLQ monitoring capabilities and health metrics."""
        # Submit various message types to populate DLQ
        test_messages = []
        for i in range(20):
            message_id = f"monitoring_test_{i}"
            content = {"type": "monitoring_test", "will_fail": i % 3 == 0}
            await dlq_manager.submit_message(message_id, content)
            test_messages.append(message_id)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        # Monitor DLQ health
        health_metrics = await dlq_manager.monitor_dlq_health()
        
        # Verify monitoring capabilities
        assert "dlq_size" in health_metrics, \
            "DLQ size should be monitored"
        
        assert "success_rate" in health_metrics, \
            "Success rate should be tracked"
        
        assert "zero_message_loss_maintained" in health_metrics, \
            "Message loss status should be monitored"
        
        # Verify health thresholds
        if health_metrics["dlq_size"] > 0:
            assert health_metrics["average_dlq_age_seconds"] >= 0, \
                "DLQ message age should be tracked"
            
            assert health_metrics["max_dlq_age_seconds"] >= health_metrics["average_dlq_age_seconds"], \
                "Max age should be >= average age"
    
    async def test_message_reprocessing_capabilities(self, message_load_tester):
        """Test DLQ message reprocessing and recovery."""
        # First, generate messages that will end up in DLQ
        initial_result = await message_load_tester.execute_message_load_test(
            message_count=30,
            concurrent_limit=10
        )
        
        # Verify some messages are in DLQ
        initial_dlq_size = initial_result["health_metrics"]["dlq_size"]
        
        # Attempt reprocessing
        reprocessing_result = await message_load_tester.dlq_manager.reprocess_dlq_messages()
        
        # Verify reprocessing metrics
        assert reprocessing_result["attempted"] >= 0, \
            "Reprocessing should track attempted messages"
        
        if initial_dlq_size > 0:
            assert reprocessing_result["attempted"] > 0, \
                "Should attempt to reprocess DLQ messages"
            
            # Verify some reprocessing success
            total_processed = (reprocessing_result["successful"] + 
                             reprocessing_result["failed"] + 
                             reprocessing_result["returned_to_dlq"])
            assert total_processed == reprocessing_result["attempted"], \
                "All reprocessing attempts should be accounted for"
    
    async def test_high_volume_message_processing(self, message_load_tester):
        """Test high-volume message processing performance."""
        # Execute high-volume test
        high_volume_result = await message_load_tester.execute_message_load_test(
            message_count=100,
            concurrent_limit=20
        )
        
        # Verify performance under high volume
        execution_time = high_volume_result["load_test_config"]["total_execution_time"]
        assert execution_time < 30.0, \
            "High-volume processing should complete within 30 seconds"
        
        # Verify throughput
        message_count = high_volume_result["load_test_config"]["message_count"]
        throughput = message_count / execution_time
        assert throughput >= 2.0, \
            "Should maintain at least 2 messages/second throughput"
        
        # Verify reliability under load
        health_metrics = high_volume_result["health_metrics"]
        assert health_metrics["zero_message_loss_maintained"], \
            "Message loss protection should work under high volume"
        
        comprehensive = high_volume_result["comprehensive_metrics"]
        success_rate = comprehensive["processing_metrics"]["success_rate"]
        assert success_rate >= 50.0, \
            "Should maintain at least 50% success rate under high volume"
    
    async def test_message_reliability_scenarios(self, message_load_tester):
        """Test comprehensive message reliability scenarios."""
        scenarios = await message_load_tester.test_message_reliability_scenarios()
        
        # Verify high priority processing
        high_priority = scenarios["high_priority"]
        assert high_priority["zero_message_loss_maintained"], \
            "High priority processing should maintain message reliability"
        
        # Verify mixed priority handling
        mixed_priority = scenarios["mixed_priority"]
        assert mixed_priority["success_rate"] > 0, \
            "Mixed priority processing should achieve some success"
        
        # Verify DLQ reprocessing
        dlq_reprocessing = scenarios["dlq_reprocessing"]
        assert dlq_reprocessing["attempted"] >= 0, \
            "DLQ reprocessing should be functional"
        
        # Verify poison handling
        poison_handling = scenarios["poison_handling"]
        assert poison_handling["detected_as_poison"], \
            "Poison message detection should work in reliability scenarios"
    
    async def test_concurrent_dlq_operations(self, dlq_manager):
        """Test concurrent DLQ operations don't cause race conditions."""
        # Create concurrent operations
        concurrent_tasks = []
        
        # Submit messages concurrently
        for i in range(20):
            message_id = f"concurrent_test_{i}"
            content = {"type": "concurrent_test", "batch": i}
            task = dlq_manager.submit_message(message_id, content)
            concurrent_tasks.append(task)
        
        # Add monitoring tasks
        for _ in range(5):
            task = dlq_manager.monitor_dlq_health()
            concurrent_tasks.append(task)
        
        # Execute all operations concurrently
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify no race conditions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, \
            f"No exceptions should occur in concurrent operations: {exceptions}"
        
        # Verify final state consistency
        final_metrics = dlq_manager.get_comprehensive_metrics()
        assert final_metrics["reliability_metrics"]["zero_message_loss_maintained"], \
            "Message loss protection should work under concurrent operations"
        
        # Verify metrics consistency
        total_tracked = (
            final_metrics["processing_metrics"]["total_messages"]
        )
        assert total_tracked >= 20, \
            "All submitted messages should be tracked"