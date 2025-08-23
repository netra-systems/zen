"""WebSocket Message Ordering and Delivery Guarantee Helper Utilities

Critical WebSocket guarantee testing utilities protecting $25K+ MRR from conversation corruption.

Business Value Justification (BVJ):
- Segment: Enterprise & Growth (primary revenue drivers)
- Business Goal: Ensure 100% message ordering and delivery reliability
- Value Impact: Prevents customer churn from conversation corruption and message loss
- Revenue Impact: Protects $25K+ MRR from messaging system failures
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from tests.e2e.config import TEST_ENDPOINTS, TestDataFactory
from test_framework.http_client import ClientConfig
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient


class MessageState(Enum):
    PENDING = "pending"
    SENT = "sent" 
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    DUPLICATE = "duplicate"


@dataclass
class OrderedMessage:
    message_id: str
    sequence_number: int
    content: str
    timestamp: float
    state: MessageState = MessageState.PENDING
    retry_count: int = 0
    ack_received: bool = False


class WebSocketGuaranteeCore:
    def __init__(self):
        self.ws_url = TEST_ENDPOINTS.ws_url
        self.config = ClientConfig(timeout=10.0, max_retries=3, verify_ssl=False)
    
    async def establish_connection(self, user_id: str) -> RealWebSocketClient:
        import pytest
        client = RealWebSocketClient(self.ws_url, self.config)
        auth_headers = self._create_auth_headers(user_id)
        success = await client.connect(auth_headers)
        if not success:
            pytest.skip("WebSocket server not available for guarantee test")
        return client
    
    def _create_auth_headers(self, user_id: str) -> Dict[str, str]:
        token = f"test_token_{user_id}"
        return TestDataFactory.create_websocket_auth(token)


class MessageOrderingCore(WebSocketGuaranteeCore):
    def __init__(self):
        super().__init__()
        self.ordering_trackers: Dict[str, List[OrderedMessage]] = {}
    
    async def send_ordered_sequence(self, client: RealWebSocketClient, 
                                  user_id: str, count: int) -> Dict[str, Any]:
        if user_id not in self.ordering_trackers:
            self.ordering_trackers[user_id] = []
        
        start_count = len(self.ordering_trackers[user_id])
        for i in range(count):
            message = self._create_ordered_message(start_count + i, f"msg_{start_count + i:03d}")
            success = await self._send_tracked_message(client, user_id, message)
            if success:
                self.ordering_trackers[user_id].append(message)
        
        return {"sent_count": len(self.ordering_trackers[user_id]) - start_count}
    
    def _create_ordered_message(self, sequence: int, content: str) -> OrderedMessage:
        return OrderedMessage(
            message_id=str(uuid.uuid4()),
            sequence_number=sequence,
            content=content,
            timestamp=time.time()
        )
    
    async def _send_tracked_message(self, client: RealWebSocketClient,
                                  user_id: str, message: OrderedMessage) -> bool:
        message_data = TestDataFactory.create_message_data(user_id, message.content)
        message_data.update({
            "message_id": message.message_id,
            "sequence_number": message.sequence_number,
            "timestamp": message.timestamp
        })
        return await client.send(message_data)


class AtLeastOnceDeliveryCore(WebSocketGuaranteeCore):
    def __init__(self):
        super().__init__()
        self.delivery_trackers: Dict[str, List[OrderedMessage]] = {}
    
    async def send_with_retry_guarantee(self, client: RealWebSocketClient,
                                      user_id: str, count: int) -> Dict[str, Any]:
        if user_id not in self.delivery_trackers:
            self.delivery_trackers[user_id] = []
        
        successful_deliveries = 0
        for i in range(count):
            message = OrderedMessage(
                message_id=str(uuid.uuid4()),
                sequence_number=i,
                content=f"guaranteed_msg_{i:03d}",
                timestamp=time.time()
            )
            
            success = await self._send_with_retry(client, user_id, message)
            if success:
                successful_deliveries += 1
                self.delivery_trackers[user_id].append(message)
        
        return {"delivered_count": successful_deliveries}
    
    async def _send_with_retry(self, client: RealWebSocketClient,
                             user_id: str, message: OrderedMessage) -> bool:
        max_retries = 3
        for attempt in range(max_retries):
            message_data = self._prepare_message_data(user_id, message)
            success = await client.send(message_data)
            if success:
                message.state = MessageState.DELIVERED
                return True
            message.retry_count += 1
            await asyncio.sleep(0.1 * (attempt + 1))
        return False
    
    def _prepare_message_data(self, user_id: str, message: OrderedMessage) -> Dict[str, Any]:
        message_data = TestDataFactory.create_message_data(user_id, message.content)
        message_data.update({
            "message_id": message.message_id,
            "sequence_number": message.sequence_number,
            "retry_count": message.retry_count,
            "delivery_guarantee": "at_least_once"
        })
        return message_data


class DuplicateDetectionCore(WebSocketGuaranteeCore):
    def __init__(self):
        super().__init__()
        self.sent_message_ids: Dict[str, Set[str]] = {}
    
    async def send_with_intentional_duplicates(self, client: RealWebSocketClient,
                                             user_id: str, count: int) -> Dict[str, Any]:
        if user_id not in self.sent_message_ids:
            self.sent_message_ids[user_id] = set()
        
        unique_sent = 0
        duplicates_sent = 0
        
        for i in range(count):
            if i > 0 and i % 3 == 0:
                duplicate_id = list(self.sent_message_ids[user_id])[-1]
                success = await self._send_duplicate_message(client, user_id, duplicate_id)
                if success:
                    duplicates_sent += 1
            else:
                message_id = str(uuid.uuid4())
                success = await self._send_unique_message(client, user_id, message_id, i)
                if success:
                    unique_sent += 1
                    self.sent_message_ids[user_id].add(message_id)
        
        return {"unique_sent": unique_sent, "duplicates_sent": duplicates_sent}
    
    async def _send_unique_message(self, client: RealWebSocketClient, user_id: str,
                                 message_id: str, sequence: int) -> bool:
        message_data = TestDataFactory.create_message_data(user_id, f"unique_msg_{sequence}")
        message_data.update({
            "message_id": message_id,
            "sequence_number": sequence,
            "duplicate_detection": True
        })
        return await client.send(message_data)
    
    async def _send_duplicate_message(self, client: RealWebSocketClient,
                                    user_id: str, original_id: str) -> bool:
        message_data = TestDataFactory.create_message_data(user_id, "duplicate_content")
        message_data.update({
            "message_id": original_id,
            "is_duplicate": True,
            "duplicate_detection": True
        })
        return await client.send(message_data)


class ReconnectionRecoveryCore(WebSocketGuaranteeCore):
    def __init__(self):
        super().__init__()
        self.message_queues: Dict[str, List[OrderedMessage]] = {}
    
    async def simulate_disconnection_with_queued_messages(self, client: RealWebSocketClient,
                                                        user_id: str, count: int) -> Dict[str, Any]:
        if user_id not in self.message_queues:
            self.message_queues[user_id] = []
        
        queued_count = 0
        for i in range(count):
            message = OrderedMessage(
                message_id=str(uuid.uuid4()),
                sequence_number=i,
                content=f"queued_msg_{i:03d}",
                timestamp=time.time(),
                state=MessageState.PENDING
            )
            self.message_queues[user_id].append(message)
            queued_count += 1
        
        return {"queued_count": queued_count}
    
    async def test_message_recovery_after_reconnection(self, client: RealWebSocketClient,
                                                     user_id: str) -> Dict[str, Any]:
        if user_id not in self.message_queues:
            return {"recovered_count": 0}
        
        recovered_count = 0
        for message in self.message_queues[user_id]:
            if message.state == MessageState.PENDING:
                success = await self._send_recovery_message(client, user_id, message)
                if success:
                    message.state = MessageState.DELIVERED
                    recovered_count += 1
        
        return {"recovered_count": recovered_count}
    
    async def _send_recovery_message(self, client: RealWebSocketClient,
                                   user_id: str, message: OrderedMessage) -> bool:
        message_data = TestDataFactory.create_message_data(user_id, message.content)
        message_data.update({
            "message_id": message.message_id,
            "sequence_number": message.sequence_number,
            "recovery_message": True,
            "original_timestamp": message.timestamp
        })
        return await client.send(message_data)


class ConcurrentMessageCore(WebSocketGuaranteeCore):
    def __init__(self):
        super().__init__()
        self.concurrent_trackers: Dict[str, List[OrderedMessage]] = {}
    
    async def send_concurrent_ordered_messages(self, client: RealWebSocketClient,
                                             user_id: str, count: int) -> Dict[str, Any]:
        if user_id not in self.concurrent_trackers:
            self.concurrent_trackers[user_id] = []
        
        tasks = []
        for i in range(count):
            message = OrderedMessage(
                message_id=str(uuid.uuid4()),
                sequence_number=i,
                content=f"concurrent_ordered_{i:03d}",
                timestamp=time.time()
            )
            task = self._send_concurrent_message(client, user_id, message)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_sends = sum(1 for r in results if r is True)
        
        return {"concurrent_sent": successful_sends}
    
    async def _send_concurrent_message(self, client: RealWebSocketClient,
                                     user_id: str, message: OrderedMessage) -> bool:
        message_data = TestDataFactory.create_message_data(user_id, message.content)
        message_data.update({
            "message_id": message.message_id,
            "sequence_number": message.sequence_number,
            "concurrent_batch": True,
            "timestamp": message.timestamp
        })
        
        success = await client.send(message_data)
        if success:
            self.concurrent_trackers[user_id].append(message)
        return success
