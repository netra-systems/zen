"""

WebSocket Stability Tests for Rapid Message Bursts.



Business Value Justification (BVJ):

- Segment: All Segments

- Business Goal: Connection Reliability  

- Value Impact: Maintains stable connections during high message frequency

- Strategic/Revenue Impact: Prevents disconnections that lose customer data

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

class TestWebSocketStability:

    """Test WebSocket connection stability during message bursts."""

    

    @pytest.mark.websocket

    async def test_connection_stability_during_burst(self, user_token, message_validator, test_config):

        """Test that WebSocket connection remains stable during rapid messages."""

        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        sender = RapidMessageSender(test_config["websocket_url"], user_token)

        

        assert await sender.connect()

        

        try:

            # Send sustained bursts

            for batch in range(10):

                result = await sender.send_message_burst(

                    f"{user_id}_batch_{batch}", 

                    15, 

                    burst_delay=0.005

                )

                

                # Connection should remain stable

                assert result.successful_sends >= 12, f"Batch {batch} had too many failures"

                

                # Brief pause between batches

                await asyncio.sleep(0.05)

            

            # Connection should still be active

            assert sender.connection and not sender.connection.closed

            

        finally:

            await sender.disconnect()

    

    @pytest.mark.websocket

    async def test_concurrent_connection_stability(self, user_token, message_validator, test_config):

        """Test stability with multiple concurrent connections."""

        user_base = f"test_user_{uuid.uuid4().hex[:8]}"

        

        # Create multiple concurrent senders

        senders = []

        for i in range(5):

            sender = RapidMessageSender(test_config["websocket_url"], user_token)

            assert await sender.connect()

            senders.append(sender)

        

        try:

            # All senders send bursts concurrently

            tasks = []

            for i, sender in enumerate(senders):

                task = sender.send_message_burst(

                    f"{user_base}_connection_{i}", 

                    20, 

                    burst_delay=0.002

                )

                tasks.append(task)

                

            results = await asyncio.gather(*tasks)

            

            # All connections should remain stable

            for i, result in enumerate(results):

                assert result.successful_sends >= 16, f"Connection {i} unstable"

                assert senders[i].connection and not senders[i].connection.closed

                

        finally:

            for sender in senders:

                await sender.disconnect()

    

    @pytest.mark.websocket

    async def test_error_handling_during_bursts(self, user_token, message_validator, test_config):

        """Test error handling doesn't destabilize connection."""

        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        sender = RapidMessageSender(test_config["websocket_url"], user_token)

        

        assert await sender.connect()

        

        try:

            # Send burst with some invalid messages

            valid_result = await sender.send_message_burst(user_id, 10, burst_delay=0.01)

            

            # Send invalid message

            invalid_message = {

                "invalid_field": "test",

                "malformed": True

            }

            await sender._send_single_message(invalid_message)

            

            # Connection should recover and continue working

            await asyncio.sleep(0.1)

            recovery_result = await sender.send_message_burst(

                f"{user_id}_recovery", 

                10, 

                burst_delay=0.01

            )

            

            # Should recover gracefully

            assert recovery_result.successful_sends >= 8, "Poor recovery after error"

            assert sender.connection and not sender.connection.closed

            

        finally:

            await sender.disconnect()

    

    @pytest.mark.websocket

    async def test_prolonged_burst_endurance(self, user_token, message_validator, test_config):

        """Test connection endurance during prolonged message activity."""

        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        sender = RapidMessageSender(test_config["websocket_url"], user_token)

        

        assert await sender.connect()

        

        try:

            # Sustained activity for extended period

            total_successful = 0

            batch_count = 20

            

            for batch in range(batch_count):

                result = await sender.send_message_burst(

                    f"{user_id}_endurance_{batch}", 

                    10, 

                    burst_delay=0.01

                )

                

                total_successful += result.successful_sends

                

                # Very brief pause

                await asyncio.sleep(0.02)

            

            # Should maintain good performance throughout

            expected_total = batch_count * 10

            success_rate = total_successful / expected_total

            assert success_rate >= 0.85, f"Endurance test success rate: {success_rate}"

            

            # Connection should still be healthy

            assert sender.connection and not sender.connection.closed

            

        finally:

            await sender.disconnect()

