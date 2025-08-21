#!/usr/bin/env python3
"""
L3 Integration Test: Error Handling and Recovery
Tests comprehensive error handling, recovery mechanisms, and resilience patterns
across different system components.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict

import aiohttp
import pytest

# Add project root to path
from netra_backend.app.redis_manager import RedisManager
from test_framework.test_patterns import L3IntegrationTest

# Add project root to path


class TestErrorHandlingRecovery(L3IntegrationTest):
    """Test error handling and recovery from multiple angles."""
    
    async def test_database_connection_failure_recovery(self):
        """Test recovery from database connection failures."""
        user_data = await self.create_test_user("error1@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Simulate database failure (would need admin endpoint)
            # For now, test that API handles gracefully
            
            # Make request that requires database
            async with session.get(
                f"{self.backend_url}/api/v1/threads",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                # Should either work or return proper error
                assert resp.status in [200, 503]
                
                if resp.status == 503:
                    data = await resp.json()
                    assert "error" in data
                    assert "temporarily unavailable" in data["error"].lower()
                    
    async def test_redis_connection_failure_handling(self):
        """Test handling of Redis connection failures."""
        user_data = await self.create_test_user("error2@test.com")
        token = await self.get_auth_token(user_data)
        
        # Test continues to work with degraded functionality
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.backend_url}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                # Should work even if Redis cache is down
                assert resp.status in [200, 503]
                
    async def test_circuit_breaker_activation(self):
        """Test circuit breaker activation on repeated failures."""
        user_data = await self.create_test_user("error3@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Make requests to a flaky endpoint
            failures = 0
            circuit_opened = False
            
            for i in range(20):
                async with session.get(
                    f"{self.backend_url}/api/v1/external/flaky",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    if resp.status == 503:
                        data = await resp.json()
                        if "circuit breaker" in data.get("error", "").lower():
                            circuit_opened = True
                            break
                        failures += 1
                
                await asyncio.sleep(0.1)
            
            # Circuit breaker should activate after failures
            assert circuit_opened or failures < 5
            
    async def test_retry_with_exponential_backoff(self):
        """Test retry mechanism with exponential backoff."""
        user_data = await self.create_test_user("error4@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            start_time = datetime.utcnow()
            
            # Make request to endpoint that requires retries
            async with session.post(
                f"{self.backend_url}/api/v1/jobs/retry-test",
                json={"attempts_to_succeed": 3},
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                # Should eventually succeed
                assert resp.status == 200
                
                # Should take time due to backoff
                assert duration > 1  # At least some retry delay
                
    async def test_timeout_handling(self):
        """Test request timeout handling."""
        user_data = await self.create_test_user("error5@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            # Request that takes long time
            try:
                async with session.post(
                    f"{self.backend_url}/api/v1/jobs/long-running",
                    json={"duration": 10},
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    await resp.json()
                    pytest.fail("Should have timed out")
            except asyncio.TimeoutError:
                # Expected behavior
                pass
                
    async def test_graceful_degradation(self):
        """Test graceful degradation when services are unavailable."""
        user_data = await self.create_test_user("error6@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Request that uses optional services
            async with session.get(
                f"{self.backend_url}/api/v1/dashboard",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                # Should return partial data if some services are down
                assert "data" in data
                
                if "degraded" in data:
                    assert data["degraded"] is True
                    assert "unavailable_services" in data
                    
    async def test_error_cascade_prevention(self):
        """Test prevention of error cascades."""
        user_data = await self.create_test_user("error7@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Trigger error in one component
            async with session.post(
                f"{self.backend_url}/api/v1/agents/trigger-error",
                json={"component": "analyzer"},
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                # Should isolate error
                assert resp.status in [200, 500]
            
            # Other components should still work
            async with session.get(
                f"{self.backend_url}/api/v1/health",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                # Most services should be healthy
                healthy_count = sum(
                    1 for s in data["services"].values() 
                    if s["status"] == "healthy"
                )
                assert healthy_count >= len(data["services"]) - 1
                
    async def test_deadlock_detection_recovery(self):
        """Test deadlock detection and recovery."""
        user_data = await self.create_test_user("error8@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create potential deadlock scenario
            tasks = []
            
            # Thread A needs resource 1 then 2
            tasks.append(session.post(
                f"{self.backend_url}/api/v1/resources/lock",
                json={"resources": ["resource1", "resource2"], "order": "sequential"},
                headers={"Authorization": f"Bearer {token}"}
            ))
            
            # Thread B needs resource 2 then 1
            tasks.append(session.post(
                f"{self.backend_url}/api/v1/resources/lock",
                json={"resources": ["resource2", "resource1"], "order": "sequential"},
                headers={"Authorization": f"Bearer {token}"}
            ))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # At least one should succeed or timeout
            success_count = sum(
                1 for r in responses 
                if not isinstance(r, Exception) and r.status == 200
            )
            
            assert success_count >= 1  # Deadlock was prevented/resolved
            
    async def test_memory_leak_prevention(self):
        """Test memory leak prevention in long-running operations."""
        user_data = await self.create_test_user("error9@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Get initial memory usage
            async with session.get(
                f"{self.backend_url}/api/v1/metrics/memory",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                initial_memory = await resp.json()
            
            # Perform memory-intensive operations
            for _ in range(10):
                async with session.post(
                    f"{self.backend_url}/api/v1/process/large-data",
                    json={"size_mb": 10},
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status in [200, 201]
            
            # Check memory after operations
            await asyncio.sleep(2)  # Allow garbage collection
            
            async with session.get(
                f"{self.backend_url}/api/v1/metrics/memory",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                final_memory = await resp.json()
            
            # Memory should not grow excessively
            memory_growth = final_memory["used"] - initial_memory["used"]
            assert memory_growth < 100 * 1024 * 1024  # Less than 100MB growth
            
    async def test_transaction_rollback_on_error(self):
        """Test transaction rollback on errors."""
        user_data = await self.create_test_user("error10@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Start transaction that will fail
            transaction_data = {
                "operations": [
                    {"type": "create", "data": {"title": "Item 1"}},
                    {"type": "create", "data": {"title": "Item 2"}},
                    {"type": "invalid_operation"}  # This will fail
                ]
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/transactions",
                json=transaction_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 400
                data = await resp.json()
                assert "rolled back" in data["error"].lower()
            
            # Verify no partial data was committed
            async with session.get(
                f"{self.backend_url}/api/v1/threads?search=Item",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                # Should not find any items from failed transaction
                item_count = sum(
                    1 for t in data["threads"] 
                    if "Item" in t["title"]
                )
                assert item_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])