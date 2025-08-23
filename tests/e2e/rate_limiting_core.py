"""
Rate Limiting Core Module - Supporting classes for E2E rate limiting tests.

ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines (enforced)
- Maximum function size: 8 lines (enforced)
- Single responsibility: Rate limiting test support only
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import redis.asyncio as redis


class RedisManager:
    """Manages Redis operations for rate limiting tests."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.redis_key_prefix = f"rate_limit:user:{user_id}"
    
    async def connect_to_redis(self) -> redis.Redis:
        """Connect to Redis instance."""
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        await redis_client.ping()
        return redis_client
    
    async def verify_rate_limit_counter(self, redis_client: redis.Redis, expected_count: int) -> Dict[str, Any]:
        """Verify Redis counter matches expected value."""
        key = f"{self.redis_key_prefix}:messages"
        current_count = await redis_client.get(key) or "0"
        actual_count = int(current_count)
        assert actual_count == expected_count, f"Expected {expected_count}, got {actual_count}"
        return {"key": key, "count": actual_count}
    
    async def get_rate_limit_status(self, redis_client: redis.Redis) -> Dict[str, Any]:
        """Get current rate limit status from Redis."""
        messages_key = f"{self.redis_key_prefix}:messages"
        
        current_count = int(await redis_client.get(messages_key) or "0")
        ttl = await redis_client.ttl(messages_key)
        
        return {"current_count": current_count, "ttl_seconds": ttl, "limit": 5}
    
    async def wait_for_counter_reset(self, redis_client: redis.Redis) -> Dict[str, Any]:
        """Wait for Redis counter to reset."""
        start_time = time.time()
        while True:
            status = await self.get_rate_limit_status(redis_client)
            if status["current_count"] == 0:
                break
            if time.time() - start_time > 65:  # 5 second buffer
                raise TimeoutError("Rate limit did not reset in time")
            await asyncio.sleep(1)
        
        return {"reset_after_seconds": time.time() - start_time}
    
    async def test_cleanup_test_keys(self, redis_client: redis.Redis) -> None:
        """Clean up test Redis keys."""
        pattern = f"{self.redis_key_prefix}:*"
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)


class MessageSender:
    """Handles message sending and rate limit testing."""
    
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.backend_url = "http://localhost:8000"
        self.messages_sent = 0
    
    async def send_message(self, content: str) -> Dict[str, Any]:
        """Send a single message via HTTP API."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        payload = {"message": content, "timestamp": datetime.now(timezone.utc).isoformat()}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.backend_url}/api/v1/chat/message",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            
            self.messages_sent += 1
            return {"status_code": response.status_code, "response": response.json() if response.status_code < 500 else None}
    
    async def send_multiple_messages(self, count: int, expect_success: bool = True) -> Dict[str, Any]:
        """Send multiple messages and track results."""
        results = []
        for i in range(count):
            try:
                result = await self.send_message(f"Test message {i + 1}")
                results.append(result)
                if expect_success:
                    assert result["status_code"] == 200, f"Message {i+1} failed: {result}"
            except Exception as e:
                if not expect_success and "rate limit" in str(e).lower():
                    results.append({"status_code": 429, "error": str(e)})
                else:
                    raise
        
        return {"messages_sent": len(results), "results": results}
    
    async def send_until_rate_limited(self) -> Dict[str, Any]:
        """Send messages until rate limited."""
        attempt = 0
        while attempt < 10:  # Safety limit
            try:
                result = await self.send_message(f"Rate limit test {attempt + 1}")
                if result["status_code"] == 429:
                    return {"rate_limited_at_attempt": attempt + 1, "result": result}
                attempt += 1
            except Exception as e:
                if "rate limit" in str(e).lower():
                    return {"rate_limited_at_attempt": attempt + 1, "error": str(e)}
                raise
        
        raise AssertionError("Rate limit not reached after 10 attempts")


class UserManager:
    """Manages user creation and plan upgrades."""
    
    def __init__(self):
        self.auth_base_url = "http://localhost:8001"
        self.backend_base_url = "http://localhost:8000"
    
    async def create_free_user(self) -> Dict[str, Any]:
        """Create a free tier user."""
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.auth_base_url}/auth/dev/login")
            assert response.status_code == 200, f"User creation failed: {response.status_code}"
            
            auth_data = response.json()
            return {"access_token": auth_data["access_token"], "user_created": True}
    
    async def create_paid_user(self, plan: str = "pro") -> Dict[str, Any]:
        """Create a paid tier user."""
        async with httpx.AsyncClient() as client:
            # First create user
            auth_response = await client.post(f"{self.auth_base_url}/auth/dev/login")
            assert auth_response.status_code == 200, f"User creation failed: {auth_response.status_code}"
            
            auth_data = auth_response.json()
            access_token = auth_data["access_token"]
            
            # Then upgrade to paid plan
            headers = {"Authorization": f"Bearer {access_token}"}
            upgrade_response = await client.post(
                f"{self.backend_base_url}/api/v1/user/upgrade",
                headers=headers,
                json={"plan": plan}
            )
            
            if upgrade_response.status_code == 200:
                return {"access_token": access_token, "user_created": True, "plan": plan}
            else:
                # Return free user if upgrade fails (for testing)
                return {"access_token": access_token, "user_created": True, "plan": "free"}
    
    async def upgrade_user_plan(self, auth_token: str, plan: str = "pro") -> Dict[str, Any]:
        """Upgrade user to paid tier."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {"plan": plan, "reason": "rate_limit_upgrade"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.backend_base_url}/api/v1/user/upgrade",
                headers=headers,
                json=payload
            )
            assert response.status_code == 200, f"Upgrade failed: {response.status_code}"
            
            return {"upgraded": True, "new_plan": plan}


class RateLimitFlowValidator:
    """Validates rate limiting flow steps."""
    
    def __init__(self):
        self.validation_results = []
    
    def validate_normal_usage(self, results: Dict[str, Any]) -> None:
        """Validate normal message usage within limits."""
        assert results["messages_sent"] == 5, f"Expected 5 messages, got {results['messages_sent']}"
        assert results["redis_counter"] == 5, f"Redis counter mismatch: {results['redis_counter']}"
        self.validation_results.append("normal_usage_valid")
    
    def validate_rate_limiting(self, results: Dict[str, Any]) -> None:
        """Validate rate limiting enforcement."""
        assert results["rate_limited"] is True, "Rate limit not enforced"
        assert results["attempt"] == 1, "Should be rate limited immediately"
        self.validation_results.append("rate_limiting_valid")
    
    def validate_reset_functionality(self, results: Dict[str, Any]) -> None:
        """Validate rate limit reset."""
        assert results["reset_completed"] is True, "Rate limit did not reset"
        assert results["wait_time"] < 65, f"Reset took too long: {results['wait_time']}s"
        self.validation_results.append("reset_valid")
    
    def validate_post_reset_usage(self, results: Dict[str, Any]) -> None:
        """Validate usage after reset."""
        assert results["message_sent"] is True, "Could not send after reset"
        assert results["redis_counter"] == 1, "Counter not reset properly"
        self.validation_results.append("post_reset_valid")
    
    def validate_upgrade_success(self, results: Dict[str, Any]) -> None:
        """Validate successful plan upgrade."""
        assert results["upgraded"] is True, "Upgrade failed"
        assert results["new_plan"] == "pro", "Plan upgrade incorrect"
        self.validation_results.append("upgrade_valid")
    
    def validate_unlimited_usage(self, results: Dict[str, Any]) -> None:
        """Validate unlimited usage after upgrade."""
        assert results["unlimited_verified"] is True, "Unlimited usage not verified"
        assert results["messages_sent"] == 10, "Not enough messages sent for verification"
        self.validation_results.append("unlimited_valid")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validations."""
        return {
            "total_validations": len(self.validation_results),
            "validations": self.validation_results,
            "all_passed": len(self.validation_results) == 6
        }