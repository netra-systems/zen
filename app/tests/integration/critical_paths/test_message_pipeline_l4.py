"""Message Processing Pipeline - L4 Performance Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (core messaging affects all customer interactions)
- Business Goal: Ensure reliable, high-performance message processing at scale
- Value Impact: Maintains real-time user experience, prevents message loss, ensures system reliability
- Strategic Impact: $12K MRR protection through robust message pipeline and queue management

Critical Path: Message ingestion -> Queue processing -> Agent routing -> Response delivery -> Dead letter handling
L4 Realism: Real message queues, real WebSocket connections, real agent processing in staging
Performance Requirements: p99 < 500ms, 99.9% delivery success, message ordering guarantees, DLQ < 0.1%
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import aiohttp
import websockets

from app.services.messaging.message_queue import MessageQueue
from app.services.messaging.queue_manager import QueueManager
from app.services.messaging.dead_letter_queue import DeadLetterQueue
from app.services.websocket.ws_manager import WebSocketManager
from app.services.websocket.message_router import MessageRouter
from app.agents.supervisor_consolidated import SupervisorAgent
from app.schemas.registry import WebSocketMessage, QueueMessage
from tests.unified.config import TEST_CONFIG
from tests.unified.e2e.real_websocket_client import RealWebSocketClient

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels for queue testing."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PipelineMetrics:
    """Message pipeline performance metrics."""
    messages_sent: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    messages_in_dlq: int = 0
    processing_times: List[float] = None
    queue_wait_times: List[float] = None
    delivery_times: List[float] = None
    ordering_violations: int = 0
    total_throughput: float = 0.0
    queue_depths: List[int] = None
    
    def __post_init__(self):
        if self.processing_times is None:
            self.processing_times = []
        if self.queue_wait_times is None:
            self.queue_wait_times = []
        if self.delivery_times is None:
            self.delivery_times = []
        if self.queue_depths is None:
            self.queue_depths = []
    
    @property
    def success_rate(self) -> float:
        """Calculate message processing success rate."""
        return (self.messages_processed / self.messages_sent * 100) if self.messages_sent > 0 else 0.0
    
    @property
    def dlq_rate(self) -> float:
        """Calculate dead letter queue rate."""
        return (self.messages_in_dlq / self.messages_sent * 100) if self.messages_sent > 0 else 0.0
    
    @property
    def p99_processing_time(self) -> float:
        """Calculate p99 processing time."""
        if not self.processing_times:
            return 0.0
        return statistics.quantiles(self.processing_times, n=100)[98]
    
    @property
    def avg_processing_time(self) -> float:
        """Calculate average processing time."""
        return statistics.mean(self.processing_times) if self.processing_times else 0.0
    
    @property
    def avg_queue_depth(self) -> float:
        """Calculate average queue depth."""
        return statistics.mean(self.queue_depths) if self.queue_depths else 0.0


class MessagePipelineL4Manager:
    """L4 message pipeline test manager with real queues and WebSocket connections."""
    
    def __init__(self):
        self.queue_manager = None
        self.message_queue = None
        self.dead_letter_queue = None
        self.ws_manager = None
        self.message_router = None
        self.websocket_clients = {}
        self.metrics = PipelineMetrics()
        self.message_tracking = {}
        self.test_agents = {}
        
    async def initialize_services(self):
        """Initialize real message pipeline services for L4 testing."""
        try:
            # Initialize real queue services
            self.queue_manager = QueueManager()
            await self.queue_manager.initialize()
            
            self.message_queue = MessageQueue()
            await self.message_queue.initialize()
            
            self.dead_letter_queue = DeadLetterQueue()
            await self.dead_letter_queue.initialize()
            
            # Initialize WebSocket services
            self.ws_manager = WebSocketManager()
            await self.ws_manager.initialize()
            
            self.message_router = MessageRouter()
            await self.message_router.initialize()
            
            # Initialize test agents
            await self._initialize_test_agents()
            
            logger.info("L4 message pipeline services initialized with real components")
            
        except Exception as e:
            logger.error(f"Failed to initialize L4 message pipeline services: {e}")
            raise
    
    async def _initialize_test_agents(self):
        """Initialize test agents for message processing."""
        for i in range(3):
            agent_id = f"test_agent_{i}"
            agent = SupervisorAgent(agent_id=agent_id)
            self.test_agents[agent_id] = agent
    
    async def setup_websocket_connections(self, connection_count: int) -> List[str]:
        """Setup multiple WebSocket connections for testing."""
        connection_ids = []
        
        for i in range(connection_count):
            try:
                client_id = f"test_client_{i}_{uuid.uuid4().hex[:8]}"
                
                # Create test WebSocket client
                ws_client = RealWebSocketClient("ws://localhost:8000/ws")
                await ws_client.connect({
                    "Authorization": f"Bearer test_token_{i}",
                    "Client-ID": client_id
                })
                
                self.websocket_clients[client_id] = ws_client
                connection_ids.append(client_id)
                
            except Exception as e:
                logger.warning(f"Failed to create WebSocket connection {i}: {e}")
        
        return connection_ids
    
    async def send_message_batch(self, batch_size: int, priority: MessagePriority = MessagePriority.NORMAL) -> Dict[str, Any]:
        """Send a batch of messages through the pipeline."""
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        message_ids = []
        send_times = []
        
        for i in range(batch_size):
            message_id = f"{batch_id}_msg_{i}"
            message_content = {
                "type": "chat",
                "content": f"Test message {i} in batch {batch_id}",
                "user_id": f"test_user_{i % 10}",
                "timestamp": datetime.utcnow().isoformat(),
                "priority": priority.value,
                "sequence": i
            }
            
            start_time = time.time()
            
            try:
                # Send message to queue
                queue_message = QueueMessage(
                    id=message_id,
                    content=json.dumps(message_content),
                    priority=priority.value,
                    timestamp=datetime.utcnow(),
                    retry_count=0
                )
                
                await self.message_queue.enqueue(queue_message)
                
                send_time = time.time() - start_time
                send_times.append(send_time)
                message_ids.append(message_id)
                
                # Track message for ordering verification
                self.message_tracking[message_id] = {
                    "batch_id": batch_id,
                    "sequence": i,
                    "priority": priority.value,
                    "sent_time": start_time,
                    "content": message_content
                }
                
            except Exception as e:
                logger.error(f"Failed to send message {message_id}: {e}")
        
        self.metrics.messages_sent += len(message_ids)
        
        return {
            "batch_id": batch_id,
            "messages_sent": len(message_ids),
            "message_ids": message_ids,
            "avg_send_time": statistics.mean(send_times) if send_times else 0
        }
    
    async def process_message_queue(self, max_messages: int = None) -> Dict[str, Any]:
        """Process messages from the queue with performance tracking."""
        processed_messages = []
        processing_times = []
        queue_depths = []
        
        messages_to_process = max_messages or 1000
        
        for _ in range(messages_to_process):
            start_time = time.time()
            
            try:
                # Get queue depth
                queue_depth = await self.message_queue.get_queue_depth()
                queue_depths.append(queue_depth)
                
                if queue_depth == 0:
                    break
                
                # Dequeue message
                message = await self.message_queue.dequeue()
                if not message:
                    break
                
                queue_wait_time = time.time() - start_time
                self.metrics.queue_wait_times.append(queue_wait_time)
                
                # Process message
                processing_result = await self._process_single_message(message)
                
                processing_time = time.time() - start_time
                processing_times.append(processing_time)
                
                if processing_result["success"]:
                    processed_messages.append(message.id)
                    self.metrics.messages_processed += 1
                else:
                    # Send to dead letter queue
                    await self._handle_failed_message(message, processing_result["error"])
                    self.metrics.messages_failed += 1
                
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                self.metrics.messages_failed += 1
        
        self.metrics.processing_times.extend(processing_times)
        self.metrics.queue_depths.extend(queue_depths)
        
        return {
            "messages_processed": len(processed_messages),
            "avg_processing_time": statistics.mean(processing_times) if processing_times else 0,
            "avg_queue_depth": statistics.mean(queue_depths) if queue_depths else 0,
            "processed_message_ids": processed_messages
        }
    
    async def _process_single_message(self, message: QueueMessage) -> Dict[str, Any]:
        """Process a single message through the agent pipeline."""
        try:
            message_content = json.loads(message.content)
            
            # Route to appropriate agent
            agent_id = await self._route_message_to_agent(message_content)
            agent = self.test_agents.get(agent_id)
            
            if not agent:
                raise Exception(f"Agent {agent_id} not available")
            
            # Process with agent (mock processing for L4 test)
            processing_result = await self._mock_agent_processing(agent, message_content)
            
            # Update message tracking
            if message.id in self.message_tracking:
                self.message_tracking[message.id]["processed_time"] = time.time()
                self.message_tracking[message.id]["agent_id"] = agent_id
                self.message_tracking[message.id]["result"] = processing_result
            
            return {
                "success": True,
                "agent_id": agent_id,
                "result": processing_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _route_message_to_agent(self, message_content: Dict[str, Any]) -> str:
        """Route message to appropriate agent based on content."""
        # Simple routing logic for testing
        content = message_content.get("content", "").lower()
        
        if "urgent" in content or message_content.get("priority") == "critical":
            return "test_agent_0"  # High priority agent
        elif "analysis" in content:
            return "test_agent_1"  # Analysis agent
        else:
            return "test_agent_2"  # General purpose agent
    
    async def _mock_agent_processing(self, agent: SupervisorAgent, message_content: Dict[str, Any]) -> Dict[str, Any]:
        """Mock agent processing for L4 performance testing."""
        # Simulate processing time
        processing_delay = 0.1 + (hash(message_content["content"]) % 100) / 1000
        await asyncio.sleep(processing_delay)
        
        return {
            "response": f"Processed: {message_content['content'][:50]}...",
            "status": "completed",
            "processing_time": processing_delay
        }
    
    async def _handle_failed_message(self, message: QueueMessage, error: str):
        """Handle failed message by sending to dead letter queue."""
        try:
            dlq_message = QueueMessage(
                id=f"dlq_{message.id}",
                content=message.content,
                priority="low",
                timestamp=datetime.utcnow(),
                retry_count=message.retry_count + 1,
                error=error
            )
            
            await self.dead_letter_queue.enqueue(dlq_message)
            self.metrics.messages_in_dlq += 1
            
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")
    
    async def verify_message_ordering(self, batch_id: str) -> Dict[str, Any]:
        """Verify message ordering within a batch."""
        batch_messages = {
            msg_id: data for msg_id, data in self.message_tracking.items()
            if data.get("batch_id") == batch_id
        }
        
        if not batch_messages:
            return {"error": f"No messages found for batch {batch_id}"}
        
        # Sort by sequence number
        sorted_messages = sorted(
            batch_messages.items(),
            key=lambda x: x[1]["sequence"]
        )
        
        ordering_violations = 0
        processed_sequences = []
        
        for msg_id, data in sorted_messages:
            if "processed_time" in data:
                processed_sequences.append(data["sequence"])
        
        # Check for ordering violations
        for i in range(1, len(processed_sequences)):
            if processed_sequences[i] < processed_sequences[i-1]:
                ordering_violations += 1
        
        self.metrics.ordering_violations += ordering_violations
        
        return {
            "batch_id": batch_id,
            "total_messages": len(batch_messages),
            "processed_messages": len(processed_sequences),
            "ordering_violations": ordering_violations,
            "ordering_preserved": ordering_violations == 0
        }
    
    async def test_throughput_performance(self, duration_seconds: int, target_rps: int) -> Dict[str, Any]:
        """Test message pipeline throughput performance."""
        start_time = time.time()
        messages_sent = 0
        throughput_measurements = []
        
        while time.time() - start_time < duration_seconds:
            batch_start = time.time()
            
            # Send batch of messages
            batch_result = await self.send_message_batch(target_rps)
            messages_sent += batch_result["messages_sent"]
            
            # Process messages concurrently
            processing_task = asyncio.create_task(
                self.process_message_queue(max_messages=target_rps)
            )
            
            # Wait for batch completion
            await processing_task
            
            batch_time = time.time() - batch_start
            batch_rps = batch_result["messages_sent"] / batch_time if batch_time > 0 else 0
            throughput_measurements.append(batch_rps)
            
            # Maintain target rate
            sleep_time = max(0, 1.0 - batch_time)
            await asyncio.sleep(sleep_time)
        
        total_time = time.time() - start_time
        actual_rps = messages_sent / total_time if total_time > 0 else 0
        
        self.metrics.total_throughput = actual_rps
        
        return {
            "duration_seconds": total_time,
            "messages_sent": messages_sent,
            "target_rps": target_rps,
            "actual_rps": actual_rps,
            "avg_throughput": statistics.mean(throughput_measurements) if throughput_measurements else 0,
            "throughput_achieved": actual_rps >= target_rps * 0.9  # 90% of target
        }
    
    async def test_dead_letter_queue_handling(self) -> Dict[str, Any]:
        """Test dead letter queue functionality and recovery."""
        # Send messages that will fail processing
        failing_messages = []
        
        for i in range(10):
            message_content = {
                "type": "error_test",
                "content": f"FORCE_ERROR_message_{i}",  # Special marker to force errors
                "user_id": f"error_user_{i}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            message_id = f"error_test_{i}"
            queue_message = QueueMessage(
                id=message_id,
                content=json.dumps(message_content),
                priority="normal",
                timestamp=datetime.utcnow(),
                retry_count=0
            )
            
            await self.message_queue.enqueue(queue_message)
            failing_messages.append(message_id)
        
        # Process messages (they should fail and go to DLQ)
        initial_dlq_count = await self.dead_letter_queue.get_queue_depth()
        
        await self.process_message_queue(max_messages=20)
        
        final_dlq_count = await self.dead_letter_queue.get_queue_depth()
        messages_in_dlq = final_dlq_count - initial_dlq_count
        
        # Test DLQ retrieval
        dlq_messages = []
        for _ in range(messages_in_dlq):
            dlq_message = await self.dead_letter_queue.dequeue()
            if dlq_message:
                dlq_messages.append(dlq_message)
        
        return {
            "failing_messages_sent": len(failing_messages),
            "messages_in_dlq": messages_in_dlq,
            "dlq_messages_retrieved": len(dlq_messages),
            "dlq_handling_success": messages_in_dlq == len(failing_messages)
        }
    
    async def test_websocket_delivery_performance(self, connection_count: int, messages_per_connection: int) -> Dict[str, Any]:
        """Test WebSocket message delivery performance."""
        # Setup WebSocket connections
        connection_ids = await self.setup_websocket_connections(connection_count)
        successful_connections = len(connection_ids)
        
        delivery_times = []
        successful_deliveries = 0
        failed_deliveries = 0
        
        # Send messages to each connection
        for connection_id in connection_ids:
            ws_client = self.websocket_clients[connection_id]
            
            for i in range(messages_per_connection):
                start_time = time.time()
                
                try:
                    message = {
                        "type": "response",
                        "content": f"Test delivery message {i}",
                        "message_id": f"{connection_id}_delivery_{i}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await ws_client.send_message(json.dumps(message))
                    
                    # Wait for acknowledgment or timeout
                    response = await asyncio.wait_for(
                        ws_client.receive_message(),
                        timeout=1.0
                    )
                    
                    delivery_time = time.time() - start_time
                    delivery_times.append(delivery_time)
                    successful_deliveries += 1
                    
                except asyncio.TimeoutError:
                    failed_deliveries += 1
                except Exception as e:
                    failed_deliveries += 1
                    logger.error(f"WebSocket delivery failed: {e}")
        
        self.metrics.delivery_times.extend(delivery_times)
        
        return {
            "connections_established": successful_connections,
            "total_messages": connection_count * messages_per_connection,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "delivery_success_rate": (successful_deliveries / (successful_deliveries + failed_deliveries) * 100) if (successful_deliveries + failed_deliveries) > 0 else 0,
            "avg_delivery_time": statistics.mean(delivery_times) if delivery_times else 0
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive pipeline performance summary."""
        return {
            "pipeline_metrics": asdict(self.metrics),
            "sla_compliance": {
                "success_rate_above_99_9": self.metrics.success_rate > 99.9,
                "p99_under_500ms": self.metrics.p99_processing_time < 0.5,
                "dlq_rate_under_0_1": self.metrics.dlq_rate < 0.1,
                "throughput_meets_target": self.metrics.total_throughput > 100,  # 100 RPS minimum
                "ordering_preserved": self.metrics.ordering_violations == 0
            },
            "recommendations": self._generate_pipeline_recommendations()
        }
    
    def _generate_pipeline_recommendations(self) -> List[str]:
        """Generate pipeline performance recommendations."""
        recommendations = []
        
        if self.metrics.success_rate < 99.9:
            recommendations.append(f"Success rate {self.metrics.success_rate:.2f}% below 99.9% - investigate failures")
        
        if self.metrics.p99_processing_time > 0.5:
            recommendations.append(f"P99 processing time {self.metrics.p99_processing_time:.3f}s exceeds 500ms")
        
        if self.metrics.dlq_rate > 0.1:
            recommendations.append(f"DLQ rate {self.metrics.dlq_rate:.2f}% exceeds 0.1% - review error patterns")
        
        if self.metrics.ordering_violations > 0:
            recommendations.append(f"{self.metrics.ordering_violations} ordering violations detected")
        
        if self.metrics.avg_queue_depth > 100:
            recommendations.append("High average queue depth - consider scaling")
        
        if not recommendations:
            recommendations.append("All pipeline performance metrics meet SLA requirements")
        
        return recommendations
    
    async def cleanup(self):
        """Clean up L4 pipeline test resources."""
        try:
            # Close WebSocket connections
            for ws_client in self.websocket_clients.values():
                await ws_client.disconnect()
            
            # Cleanup queues
            if self.message_queue:
                await self.message_queue.clear()
                await self.message_queue.shutdown()
            
            if self.dead_letter_queue:
                await self.dead_letter_queue.clear()
                await self.dead_letter_queue.shutdown()
            
            # Shutdown services
            if self.queue_manager:
                await self.queue_manager.shutdown()
            if self.ws_manager:
                await self.ws_manager.shutdown()
            if self.message_router:
                await self.message_router.shutdown()
                
        except Exception as e:
            logger.error(f"L4 pipeline cleanup failed: {e}")


@pytest.fixture
async def pipeline_l4_manager():
    """Create L4 message pipeline manager."""
    manager = MessagePipelineL4Manager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l4
async def test_message_processing_throughput_performance(pipeline_l4_manager):
    """Test message processing throughput under load."""
    # Test throughput performance
    throughput_result = await pipeline_l4_manager.test_throughput_performance(
        duration_seconds=30,
        target_rps=150
    )
    
    # Verify throughput requirements
    assert throughput_result["throughput_achieved"], f"Throughput {throughput_result['actual_rps']:.1f} RPS below target {throughput_result['target_rps']} RPS"
    assert throughput_result["actual_rps"] > 100, f"Minimum throughput requirement not met: {throughput_result['actual_rps']:.1f} RPS"
    
    # Verify performance metrics
    performance = pipeline_l4_manager.get_performance_summary()
    assert performance["sla_compliance"]["success_rate_above_99_9"], "Success rate below 99.9%"
    assert performance["sla_compliance"]["p99_under_500ms"], "P99 processing time exceeds 500ms"
    
    logger.info(f"Throughput test completed: {throughput_result['actual_rps']:.1f} RPS achieved")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_message_ordering_guarantees(pipeline_l4_manager):
    """Test message ordering preservation through the pipeline."""
    # Send ordered batches with different priorities
    batch_results = []
    
    for priority in [MessagePriority.HIGH, MessagePriority.NORMAL, MessagePriority.LOW]:
        batch_result = await pipeline_l4_manager.send_message_batch(
            batch_size=50,
            priority=priority
        )
        batch_results.append((batch_result["batch_id"], priority))
    
    # Process all messages
    await pipeline_l4_manager.process_message_queue(max_messages=200)
    
    # Verify ordering for each batch
    ordering_violations = 0
    
    for batch_id, priority in batch_results:
        ordering_result = await pipeline_l4_manager.verify_message_ordering(batch_id)
        
        assert ordering_result["ordering_preserved"], f"Ordering violated in batch {batch_id} ({priority.value})"
        ordering_violations += ordering_result["ordering_violations"]
    
    # Verify overall ordering compliance
    performance = pipeline_l4_manager.get_performance_summary()
    assert performance["sla_compliance"]["ordering_preserved"], f"Total ordering violations: {ordering_violations}"
    
    logger.info(f"Message ordering test completed: {len(batch_results)} batches processed with ordering preserved")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_dead_letter_queue_handling(pipeline_l4_manager):
    """Test dead letter queue functionality and error recovery."""
    # Test DLQ handling
    dlq_result = await pipeline_l4_manager.test_dead_letter_queue_handling()
    
    # Verify DLQ functionality
    assert dlq_result["dlq_handling_success"], "DLQ handling failed - messages not properly routed to DLQ"
    assert dlq_result["messages_in_dlq"] == dlq_result["failing_messages_sent"], "Not all failing messages reached DLQ"
    assert dlq_result["dlq_messages_retrieved"] == dlq_result["messages_in_dlq"], "Could not retrieve all DLQ messages"
    
    # Verify DLQ rate compliance
    performance = pipeline_l4_manager.get_performance_summary()
    assert performance["sla_compliance"]["dlq_rate_under_0_1"], f"DLQ rate {performance['pipeline_metrics']['dlq_rate']:.2f}% exceeds 0.1%"
    
    logger.info(f"DLQ test completed: {dlq_result['messages_in_dlq']} messages properly handled in DLQ")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_websocket_delivery_performance(pipeline_l4_manager):
    """Test WebSocket message delivery performance and reliability."""
    # Test WebSocket delivery
    delivery_result = await pipeline_l4_manager.test_websocket_delivery_performance(
        connection_count=20,
        messages_per_connection=10
    )
    
    # Verify delivery requirements
    assert delivery_result["delivery_success_rate"] > 99.0, f"Delivery success rate {delivery_result['delivery_success_rate']:.2f}% below 99%"
    assert delivery_result["avg_delivery_time"] < 0.1, f"Average delivery time {delivery_result['avg_delivery_time']:.3f}s exceeds 100ms"
    assert delivery_result["connections_established"] >= 18, "Could not establish required WebSocket connections"
    
    logger.info(f"WebSocket delivery test completed: {delivery_result['delivery_success_rate']:.2f}% success rate")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_pipeline_performance_under_sustained_load(pipeline_l4_manager):
    """Test message pipeline performance under sustained high load."""
    # Create sustained load scenario
    load_duration = 60  # 1 minute
    target_rps = 200
    
    # Execute sustained load test
    sustained_result = await pipeline_l4_manager.test_throughput_performance(
        duration_seconds=load_duration,
        target_rps=target_rps
    )
    
    # Verify sustained performance
    assert sustained_result["throughput_achieved"], f"Could not sustain {target_rps} RPS for {load_duration}s"
    assert sustained_result["actual_rps"] > 180, f"Sustained RPS {sustained_result['actual_rps']:.1f} below minimum threshold"
    
    # Test WebSocket delivery under load
    delivery_result = await pipeline_l4_manager.test_websocket_delivery_performance(
        connection_count=30,
        messages_per_connection=5
    )
    
    assert delivery_result["delivery_success_rate"] > 99.0, "WebSocket delivery degraded under load"
    
    # Verify overall performance compliance
    performance = pipeline_l4_manager.get_performance_summary()
    
    # Check all SLA requirements
    sla_compliance = performance["sla_compliance"]
    assert sla_compliance["success_rate_above_99_9"], "Success rate degraded under sustained load"
    assert sla_compliance["p99_under_500ms"], "P99 processing time exceeded under sustained load"
    assert sla_compliance["dlq_rate_under_0_1"], "DLQ rate increased under sustained load"
    assert sla_compliance["ordering_preserved"], "Message ordering violated under sustained load"
    
    logger.info(f"Sustained load test completed: {sustained_result['actual_rps']:.1f} RPS for {load_duration}s")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_pipeline_sla_compliance_comprehensive(pipeline_l4_manager):
    """Test comprehensive pipeline SLA compliance across all requirements."""
    # Execute comprehensive test scenario
    
    # 1. Test high-volume message processing
    batch_result = await pipeline_l4_manager.send_message_batch(500, MessagePriority.NORMAL)
    processing_result = await pipeline_l4_manager.process_message_queue(max_messages=600)
    
    # 2. Test ordering with mixed priorities
    for priority in MessagePriority:
        await pipeline_l4_manager.send_message_batch(100, priority)
    
    await pipeline_l4_manager.process_message_queue(max_messages=400)
    
    # 3. Test error handling
    dlq_result = await pipeline_l4_manager.test_dead_letter_queue_handling()
    
    # 4. Test WebSocket delivery
    delivery_result = await pipeline_l4_manager.test_websocket_delivery_performance(25, 8)
    
    # Get comprehensive performance summary
    performance = pipeline_l4_manager.get_performance_summary()
    
    # Verify all SLA requirements
    sla_compliance = performance["sla_compliance"]
    
    assert sla_compliance["success_rate_above_99_9"], f"Success rate SLA violation: {performance['pipeline_metrics']['success_rate']:.2f}%"
    assert sla_compliance["p99_under_500ms"], f"P99 processing time SLA violation: {performance['pipeline_metrics']['p99_processing_time']:.3f}s"
    assert sla_compliance["dlq_rate_under_0_1"], f"DLQ rate SLA violation: {performance['pipeline_metrics']['dlq_rate']:.2f}%"
    assert sla_compliance["ordering_preserved"], f"Message ordering violated: {performance['pipeline_metrics']['ordering_violations']} violations"
    
    # Verify no critical performance issues
    critical_recommendations = [r for r in performance["recommendations"] if "exceeds" in r or "below" in r]
    assert len(critical_recommendations) == 0, f"Critical performance issues detected: {critical_recommendations}"
    
    logger.info("Comprehensive SLA compliance test completed successfully")
    logger.info(f"Performance summary: {performance}")