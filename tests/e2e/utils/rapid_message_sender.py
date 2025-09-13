"""

Rapid message sender utility for E2E testing.



Business Value Justification (BVJ):

- Segment: All Segments  

- Business Goal: Test Infrastructure

- Value Impact: Provides consistent message sending for load testing

- Strategic/Revenue Impact: Enables performance testing of message handling

"""



import asyncio

import json

import logging

import time

import uuid

from dataclasses import dataclass

from datetime import datetime, timezone

from typing import Dict, List, Optional, Tuple



import websockets



from tests.e2e.fixtures.rapid_message_fixtures import (

    MessageBurstResult,

    MessageSequenceEntry,

)



logger = logging.getLogger(__name__)



@dataclass

class MessageSendResult:

    """Result of sending a single message."""

    message_id: str

    success: bool

    send_time: float

    response_time: Optional[float] = None

    error: Optional[str] = None



class RapidMessageSender:

    """Sends rapid succession of messages for testing."""

    

    def __init__(self, websocket_url: str, token: str):

        self.websocket_url = websocket_url

        self.token = token

        self.connection = None

        self.send_results: List[MessageSendResult] = []

        self.response_handlers = {}

        

    async def connect(self) -> bool:

        """Establish WebSocket connection."""

        try:

            self.connection = await websockets.connect(

                self.websocket_url,

                additional_headers={"Authorization": f"Bearer {self.token}"}

            )

            return True

        except Exception as e:

            logger.error(f"Failed to connect: {e}")

            return False

            

    async def disconnect(self):

        """Close WebSocket connection."""

        if self.connection:

            await self.connection.close()

            self.connection = None

            

    async def send_message_burst(self, user_id: str, message_count: int, 

                               burst_delay: float = 0.001) -> MessageBurstResult:

        """Send a burst of rapid messages."""

        burst_id = str(uuid.uuid4())

        start_time = time.time()

        

        # Prepare messages

        messages = []

        for i in range(message_count):

            message = {

                "message_id": str(uuid.uuid4()),

                "user_id": user_id,

                "content": f"Rapid message {i+1}/{message_count}",

                "sequence_num": i + 1,

                "timestamp": datetime.now(timezone.utc).isoformat(),

                "burst_id": burst_id

            }

            messages.append(message)

            

        # Send messages with minimal delay

        send_tasks = []

        for message in messages:

            if burst_delay > 0:

                await asyncio.sleep(burst_delay)

            send_tasks.append(self._send_single_message(message))

            

        # Wait for all sends to complete

        results = await asyncio.gather(*send_tasks, return_exceptions=True)

        

        # Calculate metrics

        successful_sends = sum(1 for r in results if isinstance(r, MessageSendResult) and r.success)

        processing_times = [r.response_time for r in results 

                          if isinstance(r, MessageSendResult) and r.response_time]

        

        burst_duration = time.time() - start_time

        

        return MessageBurstResult(

            burst_id=burst_id,

            total_messages=message_count,

            successful_sends=successful_sends,

            processing_times=processing_times,

            sequence_violations=[],  # To be populated by validator

            duplicate_responses=[],  # To be populated by validator

            state_inconsistencies=[],  # To be populated by validator

            burst_duration=burst_duration

        )

        

    async def _send_single_message(self, message: Dict) -> MessageSendResult:

        """Send a single message and track result."""

        message_id = message["message_id"]

        send_time = time.time()

        

        try:

            if not self.connection:

                return MessageSendResult(

                    message_id=message_id,

                    success=False,

                    send_time=send_time,

                    error="No connection"

                )

                

            await self.connection.send(json.dumps(message))

            

            # Wait for response with timeout

            try:

                response = await asyncio.wait_for(

                    self.connection.recv(), 

                    timeout=5.0

                )

                response_time = time.time()

                

                return MessageSendResult(

                    message_id=message_id,

                    success=True,

                    send_time=send_time,

                    response_time=response_time - send_time

                )

                

            except asyncio.TimeoutError:

                return MessageSendResult(

                    message_id=message_id,

                    success=False,

                    send_time=send_time,

                    error="Response timeout"

                )

                

        except Exception as e:

            return MessageSendResult(

                message_id=message_id,

                success=False,

                send_time=send_time,

                error=str(e)

            )

            

    async def send_concurrent_bursts(self, user_id: str, burst_count: int, 

                                   messages_per_burst: int) -> List[MessageBurstResult]:

        """Send multiple concurrent message bursts."""

        burst_tasks = []

        

        for i in range(burst_count):

            task = self.send_message_burst(

                f"{user_id}_burst_{i}", 

                messages_per_burst

            )

            burst_tasks.append(task)

            

        return await asyncio.gather(*burst_tasks)

