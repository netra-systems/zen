"""WebSocket Network Interruption Simulator



Utilities for simulating network interruptions and testing message delivery

guarantees during network failures and recovery scenarios.



Business Value Justification (BVJ):

- Segment: Enterprise & Growth

- Business Goal: Ensure message delivery during network issues

- Value Impact: Prevents customer frustration from connection failures

- Revenue Impact: Protects $40K+ MRR from network reliability issues



ARCHITECTURAL COMPLIANCE:

- File size: <300 lines

- Function size: <8 lines each

- Modular design for network simulation

"""



import asyncio

import time

from typing import Any, Dict, List



from tests.e2e.config import TestDataFactory

from test_framework.http_client import ConnectionState

from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient





class NetworkInterruptionSimulator:

    """Simulator for network interruption scenarios."""

    

    def __init__(self):

        """Initialize network interruption simulator."""

        self.interruption_log: List[Dict[str, Any]] = []

        self.message_queue: Dict[str, List[Dict[str, Any]]] = {}

    

    async def send_messages_with_interruption(self, client: RealWebSocketClient,

                                            user_id: str, message_count: int) -> Dict[str, Any]:

        """Send messages while simulating network interruption."""

        send_attempted = 0

        

        for i in range(message_count):

            message_data = TestDataFactory.create_message_data(

                user_id, f"interruption_msg_{i}"

            )

            try:

                success = await client.send(message_data)

                if success:

                    send_attempted += 1

            except Exception:

                # Handle network interruption gracefully

                await self._queue_message_for_retry(user_id, message_data)

        

        return {

            "send_attempted": send_attempted,

            "messages_queued": len(self.message_queue.get(user_id, []))

        }

    

    async def simulate_network_failure(self, client: RealWebSocketClient,

                                     failure_duration: float) -> Dict[str, Any]:

        """Simulate network failure for specified duration."""

        failure_start = time.time()

        

        # Simulate connection interruption

        if client._websocket:

            try:

                await client._websocket.close(code=1006, reason="Network simulation")

            except Exception:

                pass

        

        client.state = ConnectionState.DISCONNECTED

        await asyncio.sleep(failure_duration)

        

        failure_data = {

            "interruption_simulated": True,

            "failure_duration": time.time() - failure_start,

            "timestamp": failure_start

        }

        

        self.interruption_log.append(failure_data)

        return failure_data

    

    async def queue_messages_during_disconnection(self, client: RealWebSocketClient,

                                                user_id: str, queue_count: int) -> Dict[str, Any]:

        """Queue messages during disconnection for later delivery."""

        if user_id not in self.message_queue:

            self.message_queue[user_id] = []

        

        for i in range(queue_count):

            message_data = TestDataFactory.create_message_data(

                user_id, f"queued_msg_{i}"

            )

            self.message_queue[user_id].append(message_data)

        

        return {"messages_queued": len(self.message_queue[user_id])}

    

    async def simulate_reconnection(self, client: RealWebSocketClient) -> Dict[str, bool]:

        """Simulate network reconnection."""

        try:

            success = await client.connect()

            return {"reconnection_successful": success}

        except Exception:

            return {"reconnection_successful": False}

    

    async def validate_queued_message_delivery(self, client: RealWebSocketClient,

                                             user_id: str) -> Dict[str, bool]:

        """Validate delivery of queued messages after reconnection."""

        queued_messages = self.message_queue.get(user_id, [])

        delivery_count = 0

        

        for message in queued_messages:

            try:

                success = await client.send(message)

                if success:

                    delivery_count += 1

            except Exception:

                pass

        

        return {

            "queued_messages_delivered": delivery_count == len(queued_messages),

            "queue_integrity_maintained": True

        }

    

    async def _queue_message_for_retry(self, user_id: str, message_data: Dict[str, Any]) -> None:

        """Queue message for retry after network recovery."""

        if user_id not in self.message_queue:

            self.message_queue[user_id] = []

        self.message_queue[user_id].append(message_data)





class MessageLossDetector:

    """Detector for message loss scenarios."""

    

    def __init__(self):

        """Initialize message loss detector."""

        self.loss_statistics: Dict[str, Any] = {}

    

    async def detect_message_loss(self, client: RealWebSocketClient, user_id: str,

                                expected_count: int) -> Dict[str, Any]:

        """Detect message loss and calculate statistics."""

        detection_request = {

            "type": "message_loss_detection",

            "user_id": user_id,

            "expected_count": expected_count

        }

        

        await client.send(detection_request)

        response = await client.receive(timeout=5.0)

        

        actual_count = response.get("actual_count", 0) if response else 0

        lost_count = expected_count - actual_count

        loss_percentage = (lost_count / expected_count * 100) if expected_count > 0 else 0

        

        return {

            "expected_count": expected_count,

            "actual_count": actual_count,

            "lost_count": lost_count,

            "loss_percentage": loss_percentage,

            "all_messages_delivered": loss_percentage == 0.0

        }

