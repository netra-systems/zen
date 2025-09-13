"""

Sequential Message Processing Tests for Rapid Succession.



Business Value Justification (BVJ):

- Segment: Enterprise/Mid

- Business Goal: Platform Stability

- Value Impact: Ensures proper message ordering during rapid succession

- Strategic/Revenue Impact: Critical for enterprise customer retention

"""



import asyncio

import uuid

from datetime import datetime, timezone

from shared.isolated_environment import IsolatedEnvironment



import pytest



from tests.e2e.fixtures.rapid_message_fixtures import (

    MessageSequenceEntry,

    message_validator,

    test_config,

    user_token,

)

from tests.e2e.utils.rapid_message_sender import RapidMessageSender





@pytest.mark.asyncio

@pytest.mark.e2e

class TestSequentialMessageProcessing:

    """Test sequential processing of rapid messages."""

    

    async def test_basic_sequence_ordering(self, user_token, message_validator, test_config):

        """Test that messages maintain proper sequential order."""

        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        sender = RapidMessageSender(test_config["websocket_url"], user_token)

        

        # Connect and send burst

        assert await sender.connect()

        

        try:

            result = await sender.send_message_burst(user_id, 5, burst_delay=0.01)

            

            # Validate sequence

            violations = message_validator.validate_sequence_order(user_id)

            assert len(violations) == 0, f"Sequence violations: {violations}"

            assert result.successful_sends >= 4  # Allow 1 failure

            

        finally:

            await sender.disconnect()

    

    async def test_high_frequency_ordering(self, user_token, message_validator, test_config):

        """Test ordering with very high frequency messages."""

        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        sender = RapidMessageSender(test_config["websocket_url"], user_token)

        

        assert await sender.connect()

        

        try:

            # Send 20 messages with minimal delay

            result = await sender.send_message_burst(user_id, 20, burst_delay=0.001)

            

            # Should maintain order even at high frequency

            violations = message_validator.validate_sequence_order(user_id)

            assert len(violations) <= 2, f"Too many sequence violations: {violations}"

            assert result.successful_sends >= 18  # Allow 2 failures

            

        finally:

            await sender.disconnect()

    

    async def test_concurrent_user_ordering(self, user_token, message_validator, test_config):

        """Test that multiple users don't interfere with each other's ordering."""

        users = [f"test_user_{uuid.uuid4().hex[:8]}" for _ in range(3)]

        sender = RapidMessageSender(test_config["websocket_url"], user_token)

        

        assert await sender.connect()

        

        try:

            # Send concurrent bursts for different users

            tasks = []

            for user_id in users:

                task = sender.send_message_burst(user_id, 10, burst_delay=0.005)

                tasks.append(task)

                

            results = await asyncio.gather(*tasks)

            

            # Each user should maintain their own ordering

            for i, user_id in enumerate(users):

                violations = message_validator.validate_sequence_order(user_id)

                assert len(violations) <= 1, f"User {user_id} violations: {violations}"

                assert results[i].successful_sends >= 8

                

        finally:

            await sender.disconnect()

    

    async def test_processing_time_consistency(self, user_token, message_validator, test_config):

        """Test that processing times remain consistent during bursts."""

        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        sender = RapidMessageSender(test_config["websocket_url"], user_token)

        

        assert await sender.connect()

        

        try:

            result = await sender.send_message_burst(user_id, 15, burst_delay=0.01)

            

            # Check processing time variance

            if result.processing_times:

                avg_time = sum(result.processing_times) / len(result.processing_times)

                max_time = max(result.processing_times)

                

                # Processing time shouldn't vary too much

                assert max_time <= avg_time * 3, "Processing time variance too high"

                assert avg_time <= 2.0, "Average processing time too slow"

                

        finally:

            await sender.disconnect()

