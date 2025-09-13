"""
Message Idempotency Tests for Rapid Succession.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: Data Integrity
- Value Impact: Prevents duplicate processing and data corruption
- Strategic/Revenue Impact: Critical for billing accuracy and user trust
"""

import asyncio
import json
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
class TestMessageIdempotency:
    """Test idempotency enforcement for rapid messages."""
    
    async def test_duplicate_message_detection(self, user_token, message_validator, test_config):
        """Test that duplicate messages are properly detected."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Send same message multiple times
            message_id = str(uuid.uuid4())
            duplicate_message = {
                "message_id": message_id,
                "user_id": user_id,
                "content": "Duplicate test message",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Send the same message 3 times rapidly
            tasks = []
            for _ in range(3):
                task = sender._send_single_message(duplicate_message)
                tasks.append(task)
                
            results = await asyncio.gather(*tasks)
            
            # Should only process once, reject duplicates
            successful_results = [r for r in results if r.success]
            assert len(successful_results) <= 1, "Duplicate messages were processed"
            
        finally:
            await sender.disconnect()
    
    async def test_burst_idempotency(self, user_token, message_validator, test_config):
        """Test idempotency during message bursts."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Send burst and check for duplicates
            result = await sender.send_message_burst(user_id, 10, burst_delay=0.001)
            
            # Check for duplicate responses
            duplicates = message_validator.check_duplicate_responses(user_id)
            assert len(duplicates) == 0, f"Found duplicate responses: {duplicates}"
            
        finally:
            await sender.disconnect()
    
    async def test_retry_idempotency(self, user_token, message_validator, test_config):
        """Test that retries don't create duplicates."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Simulate retry scenario
            original_message = {
                "message_id": str(uuid.uuid4()),
                "user_id": user_id,
                "content": "Retry test message",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_count": 0
            }
            
            # Send original
            result1 = await sender._send_single_message(original_message)
            
            # Send "retry" with same ID
            retry_message = original_message.copy()
            retry_message["retry_count"] = 1
            result2 = await sender._send_single_message(retry_message)
            
            # Only one should succeed
            successful_count = sum(1 for r in [result1, result2] if r.success)
            assert successful_count <= 1, "Retry was processed as new message"
            
        finally:
            await sender.disconnect()
    
    async def test_concurrent_idempotency(self, user_token, message_validator, test_config):
        """Test idempotency with concurrent senders."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Create multiple senders
        senders = []
        for _ in range(3):
            sender = RapidMessageSender(test_config["websocket_url"], user_token)
            assert await sender.connect()
            senders.append(sender)
        
        try:
            # All senders send the same message concurrently
            message_id = str(uuid.uuid4())
            shared_message = {
                "message_id": message_id,
                "user_id": user_id,
                "content": "Concurrent duplicate test",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            tasks = []
            for sender in senders:
                task = sender._send_single_message(shared_message)
                tasks.append(task)
                
            results = await asyncio.gather(*tasks)
            
            # Only one should succeed
            successful_count = sum(1 for r in results if r.success)
            assert successful_count <= 1, "Concurrent duplicates were processed"
            
        finally:
            for sender in senders:
                await sender.disconnect()
