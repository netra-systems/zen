"""
Queue Overflow and Backpressure Tests for Rapid Messages.

Business Value Justification (BVJ):
- Segment: Enterprise 
- Business Goal: System Stability
- Value Impact: Prevents system overload during traffic spikes
- Strategic/Revenue Impact: Maintains service availability under load
"""

import asyncio
import uuid
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.fixtures.rapid_message_fixtures import (
    message_validator,
    test_config,
    user_token,
)
from tests.e2e.utils.rapid_message_sender import RapidMessageSender


@pytest.mark.asyncio
@pytest.mark.e2e  
class QueueOverflowBackpressureTests:
    """Test queue overflow handling and backpressure mechanisms."""
    
    async def test_high_volume_burst_handling(self, user_token, message_validator, test_config):
        """Test system handling of very high volume message bursts."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Send large burst to test queue limits
            result = await sender.send_message_burst(user_id, 100, burst_delay=0.001)
            
            # System should handle gracefully
            assert result.successful_sends >= 80, "Too many messages dropped"
            assert result.burst_duration <= 30.0, "Processing took too long"
            
        finally:
            await sender.disconnect()
    
    async def test_backpressure_response(self, user_token, message_validator, test_config):
        """Test that system applies backpressure when overloaded."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Send sustained load
            results = []
            for batch in range(5):
                result = await sender.send_message_burst(
                    f"{user_id}_batch_{batch}", 
                    20, 
                    burst_delay=0.001
                )
                results.append(result)
                await asyncio.sleep(0.1)  # Brief pause between batches
            
            # Later batches should show signs of backpressure
            first_batch_avg = sum(results[0].processing_times) / len(results[0].processing_times) if results[0].processing_times else 0
            last_batch_avg = sum(results[-1].processing_times) / len(results[-1].processing_times) if results[-1].processing_times else 0
            
            # Processing should slow down under sustained load
            if first_batch_avg > 0 and last_batch_avg > 0:
                assert last_batch_avg >= first_batch_avg, "No backpressure detected"
            
        finally:
            await sender.disconnect()
    
    async def test_queue_overflow_graceful_degradation(self, user_token, message_validator, test_config):
        """Test graceful degradation when message queue overflows."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Send extreme burst to force overflow
            result = await sender.send_message_burst(user_id, 200, burst_delay=0.0001)
            
            # Should handle overflow gracefully
            success_rate = result.successful_sends / result.total_messages
            assert success_rate >= 0.5, "Success rate too low during overflow"
            
            # No sequence violations in successful messages
            violations = message_validator.validate_sequence_order(user_id)
            assert len(violations) <= 5, "Too many sequence violations during overflow"
            
        finally:
            await sender.disconnect()
    
    async def test_recovery_after_overflow(self, user_token, message_validator, test_config):
        """Test system recovery after queue overflow."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Cause overflow
            overflow_result = await sender.send_message_burst(user_id, 150, burst_delay=0.0001)
            
            # Wait for recovery
            await asyncio.sleep(2.0)
            
            # Send normal burst
            recovery_result = await sender.send_message_burst(
                f"{user_id}_recovery", 
                10, 
                burst_delay=0.01
            )
            
            # Should recover to normal performance
            assert recovery_result.successful_sends >= 9, "Poor recovery after overflow"
            
            if recovery_result.processing_times:
                avg_recovery_time = sum(recovery_result.processing_times) / len(recovery_result.processing_times)
                assert avg_recovery_time <= 1.0, "Recovery performance degraded"
            
        finally:
            await sender.disconnect()
