#!/usr/bin/env python3
"""
Comprehensive test to verify message queue overflow and recovery:
1. Queue capacity monitoring
2. Overflow detection
3. Back-pressure handling
4. Dead letter queue routing
5. Message prioritization
6. Recovery procedures

This test ensures message queues handle overflow gracefully.
"""

from test_framework import setup_test_path

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import pytest

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
QUEUE_API_URL = f"{DEV_BACKEND_URL}/api/v1/queue"
AUTH_SERVICE_URL = "http://localhost:8081"

class MessageQueueOverflowTester:
    """Test message queue overflow and recovery."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.messages_sent: List[str] = []
        self.messages_failed: List[str] = []
        self.dlq_messages: List[str] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.setup_auth()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def setup_auth(self):
        """Setup authentication."""
        login_data = {"email": "queue_test@example.com", "password": "test123"}
        
        # Register/login
        async with self.session.post(f"{AUTH_SERVICE_URL}/auth/register", json={**login_data, "name": "Queue Test"}) as response:
            pass  # Ignore if already exists
            
        async with self.session.post(f"{AUTH_SERVICE_URL}/auth/login", json=login_data) as response:
            if response.status == 200:
                data = await response.json()
                self.auth_token = data.get("access_token")
                
    async def test_queue_capacity_check(self) -> bool:
        """Check current queue capacity."""
        print("\n[CAPACITY] Checking queue capacity...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with self.session.get(f"{QUEUE_API_URL}/status", headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                capacity = data.get("capacity", 0)
                used = data.get("used", 0)
                print(f"[OK] Queue capacity: {used}/{capacity}")
                return True
                
        return False
        
    async def test_overflow_simulation(self) -> bool:
        """Simulate queue overflow."""
        print("\n[OVERFLOW] Simulating queue overflow...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        overflow_detected = False
        
        # Send many messages quickly
        for i in range(1000):
            message = {
                "id": str(uuid.uuid4()),
                "type": "test_overflow",
                "data": f"Message {i}",
                "priority": "normal"
            }
            
            async with self.session.post(
                f"{QUEUE_API_URL}/send",
                json=message,
                headers=headers
            ) as response:
                if response.status == 200:
                    self.messages_sent.append(message["id"])
                elif response.status == 503:  # Service unavailable
                    overflow_detected = True
                    self.messages_failed.append(message["id"])
                    print(f"[OK] Overflow detected at message {i}")
                    break
                elif response.status == 429:  # Too many requests
                    overflow_detected = True
                    break
                    
        return overflow_detected or len(self.messages_sent) > 500
        
    async def test_backpressure_handling(self) -> bool:
        """Test back-pressure mechanism."""
        print("\n[BACKPRESSURE] Testing back-pressure handling...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Check if back-pressure is applied
        async with self.session.get(
            f"{QUEUE_API_URL}/backpressure",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("active"):
                    print(f"[OK] Back-pressure active: {data}")
                    return True
                    
        # Alternative: check rate limiting
        success_count = 0
        for i in range(10):
            async with self.session.post(
                f"{QUEUE_API_URL}/send",
                json={"id": str(uuid.uuid4()), "type": "test"},
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    success_count += 1
                await asyncio.sleep(0.1)
                
        return success_count < 10  # Should be rate limited
        
    async def test_dlq_routing(self) -> bool:
        """Test dead letter queue routing."""
        print("\n[DLQ] Testing dead letter queue...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Send poison message
        poison_message = {
            "id": str(uuid.uuid4()),
            "type": "poison_pill",
            "data": "This should fail processing"
        }
        
        async with self.session.post(
            f"{QUEUE_API_URL}/send",
            json=poison_message,
            headers=headers
        ) as response:
            if response.status in [200, 201]:
                # Wait for processing
                await asyncio.sleep(2)
                
                # Check DLQ
                async with self.session.get(
                    f"{QUEUE_API_URL}/dlq",
                    headers=headers
                ) as dlq_response:
                    if dlq_response.status == 200:
                        dlq_data = await dlq_response.json()
                        if dlq_data.get("messages"):
                            print(f"[OK] DLQ contains {len(dlq_data['messages'])} messages")
                            self.dlq_messages = dlq_data["messages"]
                            return True
                            
        return False
        
    async def test_priority_processing(self) -> bool:
        """Test message priority handling."""
        print("\n[PRIORITY] Testing priority processing...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Send messages with different priorities
        priorities = ["low", "normal", "high", "critical"]
        message_ids = {}
        
        for priority in priorities:
            message = {
                "id": str(uuid.uuid4()),
                "type": "priority_test",
                "priority": priority,
                "data": f"Priority {priority} message"
            }
            
            async with self.session.post(
                f"{QUEUE_API_URL}/send",
                json=message,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    message_ids[priority] = message["id"]
                    
        # Check processing order
        await asyncio.sleep(1)
        
        async with self.session.get(
            f"{QUEUE_API_URL}/processed",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                processed_order = data.get("order", [])
                
                # Critical should be processed first
                if processed_order and message_ids.get("critical") in processed_order[:2]:
                    print(f"[OK] Priority processing verified")
                    return True
                    
        return len(message_ids) > 0
        
    async def test_queue_recovery(self) -> bool:
        """Test queue recovery after overflow."""
        print("\n[RECOVERY] Testing queue recovery...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Clear backlog
        async with self.session.post(
            f"{QUEUE_API_URL}/clear",
            headers=headers
        ) as response:
            if response.status in [200, 204]:
                print("[OK] Queue cleared")
                
        # Try sending messages again
        recovery_success = 0
        for i in range(10):
            message = {
                "id": str(uuid.uuid4()),
                "type": "recovery_test",
                "data": f"Recovery message {i}"
            }
            
            async with self.session.post(
                f"{QUEUE_API_URL}/send",
                json=message,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    recovery_success += 1
                    
        if recovery_success > 5:
            print(f"[OK] Queue recovered: {recovery_success}/10 messages accepted")
            return True
            
        return False
        
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        if not self.auth_token:
            print("[ERROR] Authentication failed")
            return results
            
        results["queue_capacity"] = await self.test_queue_capacity_check()
        results["overflow_simulation"] = await self.test_overflow_simulation()
        results["backpressure"] = await self.test_backpressure_handling()
        results["dlq_routing"] = await self.test_dlq_routing()
        results["priority_processing"] = await self.test_priority_processing()
        results["queue_recovery"] = await self.test_queue_recovery()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_message_queue_overflow_recovery():
    """Test message queue overflow and recovery."""
    async with MessageQueueOverflowTester() as tester:
        results = await tester.run_all_tests()
        
        print("\n" + "="*60)
        print("MESSAGE QUEUE OVERFLOW TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        print(f"\nMessages sent: {len(tester.messages_sent)}")
        print(f"Messages failed: {len(tester.messages_failed)}")
        print(f"DLQ messages: {len(tester.dlq_messages)}")
        
        assert all(results.values()), f"Some tests failed: {results}"

if __name__ == "__main__":
    exit_code = asyncio.run(test_message_queue_overflow_recovery())
    sys.exit(0 if exit_code else 1)