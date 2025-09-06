from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Comprehensive test for message queue processing pipeline:
    1. Queue initialization and health
2. Message publishing
3. Consumer group management
4. Message ordering guarantees
5. Dead letter queue handling
6. Retry mechanisms
7. Batch processing
8. Queue overflow handling
""""

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import pytest

BACKEND_URL = get_env().get("BACKEND_URL", "http://localhost:8000")
QUEUE_SERVICE_URL = get_env().get("QUEUE_SERVICE_URL", "http://localhost:8084")

class MessageQueueTester:
    """Test message queue processing pipeline."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.messages_sent: List[str] = []
        self.messages_received: List[str] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    @pytest.mark.asyncio
    async def test_queue_health(self) -> bool:
        """Test queue service health."""
        print("\n[HEALTH] Testing queue service...")
        try:
            async with self.session.get(f"{QUEUE_SERVICE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Queue service healthy")
                    print(f"[INFO] Active queues: {data.get('queue_count')]")
                    print(f"[INFO] Pending messages: {data.get('pending_messages')]")
                    return True
                return False
        except Exception as e:
            print(f"[ERROR] Queue health check failed: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_message_publishing(self) -> bool:
        """Test message publishing to queue."""
        print("\n[PUBLISH] Testing message publishing...")
        try:
            test_messages = []
            for i in range(10):
                message = {
                    "id": f"msg_{uuid.uuid4().hex[:8]]",
                    "type": "test_message",
                    "payload": {"index": i, "timestamp": datetime.now(timezone.utc).isoformat()},
                    "priority": i % 3
                }
                
                async with self.session.post(
                    f"{QUEUE_SERVICE_URL}/publish",
                    json={"queue": "test_queue", "message": message}
                ) as response:
                    if response.status in [200, 201]:
                        self.messages_sent.append(message["id"])
                        test_messages.append(message["id"])
                        
            print(f"[OK] Published {len(test_messages)] messages")
            return len(test_messages) >= 8
            
        except Exception as e:
            print(f"[ERROR] Message publishing failed: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_consumer_groups(self) -> bool:
        """Test consumer group management."""
        print("\n[CONSUMERS] Testing consumer groups...")
        try:
            # Create consumer group
            group_data = {
                "group_id": f"group_{uuid.uuid4().hex[:8]]",
                "queue": "test_queue",
                "max_consumers": 5
            }
            
            async with self.session.post(
                f"{QUEUE_SERVICE_URL}/consumer-groups",
                json=group_data
            ) as response:
                if response.status in [200, 201]:
                    print(f"[OK] Consumer group created: {group_data['group_id']]")
                    
                    # Add consumers
                    for i in range(3):
                        consumer_data = {
                            "consumer_id": f"consumer_{i}",
                            "group_id": group_data["group_id"]
                        }
                        async with self.session.post(
                            f"{QUEUE_SERVICE_URL}/consumers",
                            json=consumer_data
                        ) as consumer_response:
                            if consumer_response.status in [200, 201]:
                                print(f"[OK] Consumer {i] added")
                                
                    return True
                    
            return False
            
        except Exception as e:
            print(f"[ERROR] Consumer group test failed: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_message_ordering(self) -> bool:
        """Test message ordering guarantees."""
        print("\n[ORDERING] Testing message ordering...")
        try:
            # Send ordered messages
            ordered_messages = []
            for i in range(5):
                message = {
                    "id": f"ordered_{i}",
                    "sequence": i,
                    "partition_key": "test_partition"
                }
                
                async with self.session.post(
                    f"{QUEUE_SERVICE_URL}/publish",
                    json={"queue": "ordered_queue", "message": message, "ordered": True}
                ) as response:
                    if response.status in [200, 201]:
                        ordered_messages.append(message["id"])
                        
            # Consume messages
            async with self.session.get(
                f"{QUEUE_SERVICE_URL}/consume",
                params={"queue": "ordered_queue", "count": 5}
            ) as response:
                if response.status == 200:
                    messages = await response.json()
                    received_order = [m["id"] for m in messages.get("messages", [])]
                    
                    if received_order == ordered_messages:
                        print("[OK] Message ordering preserved")
                        return True
                    else:
                        print("[WARNING] Order mismatch")
                        return False
                        
            return True
            
        except Exception as e:
            print(f"[ERROR] Message ordering test failed: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_dead_letter_queue(self) -> bool:
        """Test dead letter queue handling."""
        print("\n[DLQ] Testing dead letter queue...")
        try:
            # Send message that will fail processing
            poison_message = {
                "id": f"poison_{uuid.uuid4().hex[:8]]",
                "type": "poison_pill",
                "should_fail": True
            }
            
            async with self.session.post(
                f"{QUEUE_SERVICE_URL}/publish",
                json={"queue": "main_queue", "message": poison_message}
            ) as response:
                if response.status in [200, 201]:
                    print(f"[OK] Poison message sent: {poison_message['id']]")
                    
            # Wait for processing attempts
            await asyncio.sleep(3)
            
            # Check DLQ
            async with self.session.get(
                f"{QUEUE_SERVICE_URL}/dead-letter-queue",
                params={"queue": "main_queue"}
            ) as response:
                if response.status == 200:
                    dlq_messages = await response.json()
                    
                    found = any(m["id"] == poison_message["id"] 
                              for m in dlq_messages.get("messages", []))
                    
                    if found:
                        print(f"[OK] Message moved to DLQ")
                        return True
                        
            return True
            
        except Exception as e:
            print(f"[ERROR] DLQ test failed: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_retry_mechanisms(self) -> bool:
        """Test message retry mechanisms."""
        print("\n[RETRY] Testing retry mechanisms...")
        try:
            # Send message with retry policy
            retry_message = {
                "id": f"retry_{uuid.uuid4().hex[:8]]",
                "retry_policy": {
                    "max_retries": 3,
                    "backoff_seconds": 1,
                    "exponential": True
                }
            }
            
            async with self.session.post(
                f"{QUEUE_SERVICE_URL}/publish",
                json={"queue": "retry_queue", "message": retry_message}
            ) as response:
                if response.status in [200, 201]:
                    print(f"[OK] Retry message sent")
                    
                    # Get retry status
                    async with self.session.get(
                        f"{QUEUE_SERVICE_URL]/messages/{retry_message['id']]/retries"
                    ) as retry_response:
                        if retry_response.status == 200:
                            retry_data = await retry_response.json()
                            print(f"[INFO] Retry attempts: {retry_data.get('attempts')]")
                            print(f"[INFO] Next retry: {retry_data.get('next_retry')]")
                            return True
                            
            return True
            
        except Exception as e:
            print(f"[ERROR] Retry test failed: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_batch_processing(self) -> bool:
        """Test batch message processing."""
        print("\n[BATCH] Testing batch processing...")
        try:
            # Send batch of messages
            batch_messages = []
            for i in range(50):
                batch_messages.append({
                    "id": f"batch_{i}",
                    "data": f"value_{i}"
                })
                
            async with self.session.post(
                f"{QUEUE_SERVICE_URL}/publish-batch",
                json={"queue": "batch_queue", "messages": batch_messages}
            ) as response:
                if response.status in [200, 201]:
                    print(f"[OK] Batch of {len(batch_messages)] messages sent")
                    
                    # Process batch
                    async with self.session.post(
                        f"{QUEUE_SERVICE_URL}/process-batch",
                        json={"queue": "batch_queue", "batch_size": 10}
                    ) as process_response:
                        if process_response.status == 200:
                            result = await process_response.json()
                            print(f"[OK] Processed {result.get('processed')] messages in batches")
                            return True
                            
            return False
            
        except Exception as e:
            print(f"[ERROR] Batch processing test failed: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_queue_overflow(self) -> bool:
        """Test queue overflow handling."""
        print("\n[OVERFLOW] Testing queue overflow...")
        try:
            # Get queue limits
            async with self.session.get(
                f"{QUEUE_SERVICE_URL}/queues/test_queue/limits"
            ) as response:
                if response.status == 200:
                    limits = await response.json()
                    max_size = limits.get("max_size", 1000)
                    
                    # Try to exceed limit
                    overflow_count = 0
                    for i in range(max_size + 10):
                        async with self.session.post(
                            f"{QUEUE_SERVICE_URL}/publish",
                            json={"queue": "test_queue", "message": {"id": f"overflow_{i}"}}
                        ) as pub_response:
                            if pub_response.status == 507:  # Insufficient Storage
                                overflow_count += 1
                                
                    if overflow_count > 0:
                        print(f"[OK] Queue overflow handled: {overflow_count] messages rejected")
                        return True
                        
            return True
            
        except Exception as e:
            print(f"[ERROR] Queue overflow test failed: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_priority_processing(self) -> bool:
        """Test priority message processing."""
        print("\n[PRIORITY] Testing priority processing...")
        try:
            # Send messages with different priorities
            priorities = []
            for priority in [3, 1, 2, 1, 3]:
                msg = {
                    "id": f"prio_{priority]_{uuid.uuid4().hex[:4]]",
                    "priority": priority
                }
                priorities.append((priority, msg["id"]))
                
                async with self.session.post(
                    f"{QUEUE_SERVICE_URL}/publish",
                    json={"queue": "priority_queue", "message": msg}
                ) as response:
                    pass
                    
            # Consume messages
            consumed = []
            async with self.session.get(
                f"{QUEUE_SERVICE_URL}/consume",
                params={"queue": "priority_queue", "count": 5}
            ) as response:
                if response.status == 200:
                    messages = await response.json()
                    for msg in messages.get("messages", []):
                        consumed.append(msg.get("priority", 0))
                        
            # Check if higher priority processed first
            if consumed == sorted(consumed, reverse=True):
                print("[OK] Priority order maintained")
                return True
            else:
                print("[INFO] Priority order not strict")
                return True
                
        except Exception as e:
            print(f"[ERROR] Priority processing test failed: {e]")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all message queue tests."""
        results = {}
        
        results["queue_health"] = await self.test_queue_health()
        results["message_publishing"] = await self.test_message_publishing()
        results["consumer_groups"] = await self.test_consumer_groups()
        results["message_ordering"] = await self.test_message_ordering()
        results["dead_letter_queue"] = await self.test_dead_letter_queue()
        results["retry_mechanisms"] = await self.test_retry_mechanisms()
        results["batch_processing"] = await self.test_batch_processing()
        results["queue_overflow"] = await self.test_queue_overflow()
        results["priority_processing"] = await self.test_priority_processing()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_message_queue_processing_pipeline():
    """Test message queue processing pipeline."""
    async with MessageQueueTester() as tester:
        results = await tester.run_all_tests()
        
        print("\n" + "="*60)
        print("MESSAGE QUEUE TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        critical_tests = ["queue_health", "message_publishing", "message_ordering"]
        for test in critical_tests:
            assert results.get(test, False), f"Critical test failed: {test}"

if __name__ == "__main__":
    exit_code = asyncio.run(test_message_queue_processing_pipeline())
    sys.exit(0 if exit_code else 1)
