"""E2E WebSocket Message Delivery Guarantees Test - CRITICAL Revenue Protection

E2E tests for WebSocket message delivery guarantees under concurrent load and network failures.
MUST achieve 0% message loss to protect $40K+ MRR from messaging system failures.

Business Value Justification (BVJ):
1. Segment: Enterprise & Growth (primary revenue drivers)
2. Business Goal: Ensure 100% message delivery reliability
3. Value Impact: Prevents customer churn from lost messages/communication failures
4. Revenue Impact: Protects $40K+ MRR from messaging reliability issues

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (modular design with helper utilities)
- Function size: <8 lines each
- Real WebSocket connections, no mocking
- <5 seconds per test execution
- 0% message loss requirement enforced
"""

import asyncio
import time
from typing import Dict, Any, List
import pytest
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.config import TEST_USERS
from tests.e2e.websocket_message_guarantee_helpers import (
    MessageDeliveryGuaranteeCore, ConcurrentMessageSender, OrderingValidator, NetworkInterruptionSimulator, MessageLossDetector, AcknowledmentTracker,
    MessageDeliveryGuaranteeCore,
    ConcurrentMessageSender,
    OrderingValidator,
    NetworkInterruptionSimulator,
    MessageLossDetector,
    AcknowledmentTracker
)

@pytest.mark.asyncio
@pytest.mark.e2e
class TestConcurrentMessageDeliveryGuarantees:
    """Test #5.1: Concurrent Message Delivery with Ordering."""
    
    @pytest.fixture
    def delivery_core(self):
        """Initialize message delivery test core."""
        return MessageDeliveryGuaranteeCore()
    
    @pytest.fixture
    def concurrent_sender(self):
        """Initialize concurrent message sender."""
        return ConcurrentMessageSender()
    
    @pytest.fixture
    def ordering_validator(self):
        """Initialize message ordering validator."""
        return OrderingValidator()
    
    @pytest.mark.e2e
    async def test_concurrent_100_messages_zero_loss(self, delivery_core:
                                                   concurrent_sender, ordering_validator):
        """Test 100 concurrent messages with 0% loss guarantee."""
        user_id = TEST_USERS["enterprise"].id
        message_count = 100
        
        try:
            client = await delivery_core.establish_connection(user_id)
            send_result = await concurrent_sender.send_concurrent_messages(
                client, user_id, message_count
            )
            assert send_result["messages_sent"] == message_count
            
            loss_result = await concurrent_sender.validate_zero_message_loss(
                client, user_id, message_count
            )
            assert loss_result["messages_received"] == message_count
            assert loss_result["loss_percentage"] == 0.0
            
            ordering_result = await ordering_validator.validate_message_ordering(
                client, user_id
            )
            assert ordering_result["ordering_preserved"]
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise
    
    @pytest.mark.e2e
    async def test_ordering_preservation_under_load(self, delivery_core, ordering_validator):
        """Test message ordering preservation under concurrent load."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await delivery_core.establish_connection(user_id)
            batch_results = await ordering_validator.send_sequential_batches(
                client, user_id, batch_count=5, batch_size=20
            )
            assert batch_results["batches_sent"] == 5
            
            global_ordering = await ordering_validator.validate_global_ordering(
                client, user_id
            )
            assert global_ordering["globally_ordered"]
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

@pytest.mark.asyncio
@pytest.mark.e2e
class TestNetworkInterruptionResilience:
    """Test #5.2: Network Interruption Handling."""
    
    @pytest.fixture
    def delivery_core(self):
        """Initialize message delivery test core."""
        return MessageDeliveryGuaranteeCore()
    
    @pytest.fixture
    def interruption_simulator(self):
        """Initialize network interruption simulator."""
        return NetworkInterruptionSimulator()
    
    @pytest.fixture
    def loss_detector(self):
        """Initialize message loss detector."""
        return MessageLossDetector()
    
    @pytest.mark.e2e
    async def test_message_delivery_during_network_interruption(self, delivery_core:
                                                              interruption_simulator, loss_detector):
        """Test message delivery guarantee during network interruptions."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await delivery_core.establish_connection(user_id)
            send_task = asyncio.create_task(
                interruption_simulator.send_messages_with_interruption(
                    client, user_id, message_count=50
                )
            )
            
            interruption_result = await interruption_simulator.simulate_network_failure(
                client, failure_duration=2.0
            )
            assert interruption_result["interruption_simulated"]
            
            send_result = await send_task
            assert send_result["send_attempted"] == 50
            
            loss_result = await loss_detector.detect_message_loss(
                client, user_id, expected_count=50
            )
            assert loss_result["loss_percentage"] == 0.0
            assert loss_result["all_messages_delivered"]
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise
    
    @pytest.mark.e2e
    async def test_recovery_and_message_queue_integrity(self, delivery_core:
                                                      interruption_simulator):
        """Test message queue integrity after network recovery."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await delivery_core.establish_connection(user_id)
            queue_result = await interruption_simulator.queue_messages_during_disconnection(
                client, user_id, queue_count=25
            )
            assert queue_result["messages_queued"] == 25
            
            reconnect_result = await interruption_simulator.simulate_reconnection(client)
            assert reconnect_result["reconnection_successful"]
            
            delivery_result = await interruption_simulator.validate_queued_message_delivery(
                client, user_id
            )
            assert delivery_result["queued_messages_delivered"]
            assert delivery_result["queue_integrity_maintained"]
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

@pytest.mark.asyncio
@pytest.mark.e2e
class TestAcknowledmentAndTrackingSystem:
    """Test #5.3: Message Acknowledgment System."""
    
    @pytest.fixture
    def delivery_core(self):
        """Initialize message delivery test core."""
        return MessageDeliveryGuaranteeCore()
    
    @pytest.fixture
    def ack_tracker(self):
        """Initialize acknowledgment tracker."""
        return AcknowledmentTracker()
    
    @pytest.mark.e2e
    async def test_acknowledgment_tracking_system(self, delivery_core, ack_tracker):
        """Test comprehensive acknowledgment tracking."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await delivery_core.establish_connection(user_id)
            ack_result = await ack_tracker.send_messages_with_ack_tracking(
                client, user_id, message_count=30
            )
            assert ack_result["messages_sent"] == 30
            assert ack_result["ack_tracking_enabled"]
            
            validation_result = await ack_tracker.validate_all_acknowledgments(
                client, user_id
            )
            assert validation_result["all_acks_received"]
            assert validation_result["ack_response_time"] < 3.0
            
            timeout_result = await ack_tracker.test_acknowledgment_timeout_handling(
                client, user_id
            )
            assert timeout_result["timeout_handling_working"]
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise
    
    @pytest.mark.e2e
    async def test_performance_under_load(self, delivery_core, ack_tracker):
        """Test acknowledgment performance under concurrent load."""
        start_time = time.time()
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await delivery_core.establish_connection(user_id)
            performance_result = await ack_tracker.test_high_volume_ack_performance(
                client, user_id, message_count=100
            )
            
            total_time = time.time() - start_time
            assert total_time < 5.0, f"Performance test took {total_time:.2f}s"
            assert performance_result["high_volume_handled"]
            assert performance_result["ack_performance_acceptable"]
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

@pytest.mark.asyncio 
@pytest.mark.e2e
class TestEndToEndMessageGuarantees:
    """Test #5.4: Complete End-to-End Message Delivery Guarantees."""
    
    @pytest.fixture
    def delivery_core(self):
        """Initialize message delivery test core."""
        return MessageDeliveryGuaranteeCore()
    
    @pytest.mark.e2e
    async def test_complete_delivery_guarantee_scenario(self, delivery_core):
        """Test complete message delivery guarantee scenario."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await delivery_core.establish_connection(user_id)
            complete_result = await delivery_core.execute_complete_guarantee_test(
                client, user_id
            )
            
            assert complete_result["concurrent_load_handled"]
            assert complete_result["network_interruption_handled"]
            assert complete_result["zero_message_loss_achieved"]
            assert complete_result["ordering_preserved"]
            assert complete_result["acknowledgments_tracked"]
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise
