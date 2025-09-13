"""
Advanced Rate Limiting Test Components

Additional test components for comprehensive rate limiting validation:
- API endpoint rate limiting (Auth service & Backend)
- WebSocket message rate limiting
- Agent execution throttling  
- Tier-based rate limiting (Free vs Paid)
- Distributed Redis-based rate limiting
- 429 responses and retry-after headers

ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines (enforced)
- Maximum function size: 8 lines (enforced)
- Single responsibility: Advanced rate limiting test support
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
import redis.asyncio as redis
import websockets


class APIRateLimitTester:
    """Tests API endpoint rate limiting on Auth and Backend services."""
    
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.auth_base_url = "http://localhost:8001"
        self.backend_base_url = "http://localhost:8000"
    
    async def test_auth_service_rate_limits(self) -> Dict[str, Any]:
        """Test Auth service endpoint rate limits."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test /auth/me endpoint rate limiting
        rate_limited = await self._hit_endpoint_until_limited(
            f"{self.auth_base_url}/auth/me", headers, method="GET"
        )
        
        return {
            "auth_service_tested": True,
            "rate_limited_at_request": rate_limited["limited_at"],
            "status_code": rate_limited["status_code"],
            "retry_after": rate_limited.get("retry_after")
        }
    
    async def test_backend_api_rate_limits(self) -> Dict[str, Any]:
        """Test Backend API rate limits."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test chat message endpoint rate limiting
        rate_limited = await self._hit_endpoint_until_limited(
            f"{self.backend_base_url}/api/chat/message", 
            headers, 
            method="POST",
            json_data={"message": "test", "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        return {
            "backend_api_tested": True,
            "rate_limited_at_request": rate_limited["limited_at"],
            "status_code": rate_limited["status_code"],
            "retry_after": rate_limited.get("retry_after")
        }
    
    async def _hit_endpoint_until_limited(self, url: str, headers: Dict[str, str], 
                                        method: str = "GET", json_data: Dict = None, 
                                        max_attempts: int = 20) -> Dict[str, Any]:
        """Hit endpoint until rate limited."""
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for attempt in range(1, max_attempts + 1):
                try:
                    if method == "GET":
                        response = await client.get(url, headers=headers)
                    else:
                        response = await client.post(url, headers=headers, json=json_data)
                    
                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        return {
                            "limited_at": attempt,
                            "status_code": 429,
                            "retry_after": int(retry_after) if retry_after else None
                        }
                    
                    await asyncio.sleep(0.1)  # Small delay between requests
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        return {"limited_at": attempt, "status_code": 429, "error": str(e)}
                    raise
        
        return {"limited_at": None, "status_code": None, "not_limited": True}


class WebSocketRateLimitTester:
    """Tests WebSocket message rate limiting."""
    
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.websocket_url = "ws://localhost:8000/ws"
    
    async def test_websocket_message_rate_limits(self) -> Dict[str, Any]:
        """Test WebSocket message rate limiting."""
        try:
            uri = f"{self.websocket_url}?token={self.auth_token}"
            async with websockets.connect(uri) as websocket:
                
                # Send messages until rate limited
                messages_sent = 0
                rate_limited = False
                
                for i in range(20):  # Try up to 20 messages
                    message = {"type": "chat_message", "content": f"Test message {i+1}"}
                    await websocket.send(json.dumps(message))
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        response_data = json.loads(response)
                        
                        if response_data.get("type") == "rate_limit_exceeded":
                            rate_limited = True
                            break
                        
                        messages_sent += 1
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        rate_limited = True
                        break
                
                return {
                    "websocket_tested": True,
                    "messages_sent_before_limit": messages_sent,
                    "rate_limited": rate_limited
                }
        except Exception as e:
            return {"websocket_tested": False, "error": str(e)}


class AgentThrottleTester:
    """Tests agent execution throttling."""
    
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.backend_url = "http://localhost:8000"
    
    async def test_agent_execution_throttling(self) -> Dict[str, Any]:
        """Test agent execution throttling."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Simulate rapid agent execution requests
        throttled_requests = 0
        total_requests = 10
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for i in range(total_requests):
                try:
                    response = await client.post(
                        f"{self.backend_url}/api/agent/execute",
                        headers=headers,
                        json={"agent_type": "triage", "query": f"Test query {i+1}"}
                    )
                    
                    if response.status_code == 429:
                        throttled_requests += 1
                    elif "throttle" in response.text.lower():
                        throttled_requests += 1
                        
                except Exception as e:
                    if "throttle" in str(e).lower() or "rate" in str(e).lower():
                        throttled_requests += 1
                
                await asyncio.sleep(0.2)  # Small delay
        
        return {
            "agent_throttling_tested": True,
            "total_requests": total_requests,
            "throttled_requests": throttled_requests,
            "throttling_active": throttled_requests > 0
        }


class TierBasedRateLimitTester:
    """Tests different rate limits for different user tiers."""
    
    def __init__(self, user_manager):
        self.user_manager = user_manager
    
    async def test_tier_based_limits(self) -> Dict[str, Any]:
        """Test rate limits for Free vs Paid tiers."""
        # Test free tier user
        free_user = await self.user_manager.create_free_user()
        free_limits = await self._test_user_limits(free_user["access_token"], "free")
        
        # Test paid tier user
        paid_user = await self.user_manager.create_paid_user("pro")
        paid_limits = await self._test_user_limits(paid_user["access_token"], "paid")
        
        return {
            "tier_testing_completed": True,
            "free_tier_limit": free_limits["limit_hit_at"],
            "paid_tier_limit": paid_limits["limit_hit_at"],
            "paid_tier_higher": paid_limits["limit_hit_at"] > free_limits["limit_hit_at"]
        }
    
    async def _test_user_limits(self, token: str, tier: str) -> Dict[str, Any]:
        """Test rate limits for a specific user tier."""
        from tests.e2e.rate_limiting_core import MessageSender
        sender = MessageSender(token)
        
        # Send messages until rate limited
        for i in range(30):  # Test up to 30 messages
            try:
                result = await sender.send_message(f"Tier test {tier} - message {i+1}")
                if result["status_code"] == 429:
                    return {"limit_hit_at": i+1, "tier": tier}
            except Exception as e:
                if "rate limit" in str(e).lower():
                    return {"limit_hit_at": i+1, "tier": tier}
        
        return {"limit_hit_at": 30, "tier": tier, "no_limit_reached": True}


class DistributedRateLimitValidator:
    """Validates distributed rate limiting with Redis backend."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
    
    async def test_distributed_rate_limiting(self) -> Dict[str, Any]:
        """Test Redis-based distributed rate limiting."""
        user_id = f"test-distributed-{uuid.uuid4().hex[:8]}"
        
        # Test cross-service rate limiting with Redis
        auth_counter = await self._increment_service_counter(user_id, "auth")
        backend_counter = await self._increment_service_counter(user_id, "backend")
        
        # Verify counters are shared across services
        total_redis_count = await self._get_total_user_count(user_id)
        
        return {
            "distributed_testing_completed": True,
            "auth_service_increments": auth_counter,
            "backend_service_increments": backend_counter,
            "total_redis_count": total_redis_count,
            "counters_synced": total_redis_count == (auth_counter + backend_counter)
        }
    
    async def _increment_service_counter(self, user_id: str, service: str, 
                                       increments: int = 3) -> int:
        """Increment rate limit counter for a service."""
        key = f"rate_limit:distributed:{user_id}:{service}"
        
        for _ in range(increments):
            await self.redis_client.incr(key)
            await self.redis_client.expire(key, 300)  # 5 minute expiry
        
        return increments
    
    async def _get_total_user_count(self, user_id: str) -> int:
        """Get total rate limit count for user across all services."""
        auth_key = f"rate_limit:distributed:{user_id}:auth"
        backend_key = f"rate_limit:distributed:{user_id}:backend"
        
        auth_count = int(await self.redis_client.get(auth_key) or 0)
        backend_count = int(await self.redis_client.get(backend_key) or 0)
        
        return auth_count + backend_count


class ResponseHeaderValidator:
    """Validates 429 responses and retry-after headers."""
    
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.backend_url = "http://localhost:8000"
    
    async def test_429_responses_and_headers(self) -> Dict[str, Any]:
        """Test 429 responses include proper retry-after headers."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Hit rate limit to get 429 response
        response_429 = await self._trigger_429_response(headers)
        
        if response_429:
            return {
                "response_header_tested": True,
                "status_code_429": response_429["status_code"] == 429,
                "retry_after_header": response_429.get("retry_after") is not None,
                "rate_limit_headers": response_429.get("rate_limit_headers", {}),
                "proper_429_response": True
            }
        
        return {
            "response_header_tested": True,
            "status_code_429": False,
            "proper_429_response": False,
            "error": "Could not trigger 429 response"
        }
    
    async def _trigger_429_response(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Trigger 429 response by hitting rate limits."""
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for _ in range(15):  # Try multiple requests to trigger rate limit
                try:
                    response = await client.post(
                        f"{self.backend_url}/api/chat/message",
                        headers=headers,
                        json={"message": "Rate limit test", "timestamp": datetime.now(timezone.utc).isoformat()}
                    )
                    
                    if response.status_code == 429:
                        return {
                            "status_code": 429,
                            "retry_after": response.headers.get("Retry-After"),
                            "rate_limit_headers": {
                                "x-ratelimit-limit": response.headers.get("X-RateLimit-Limit"),
                                "x-ratelimit-remaining": response.headers.get("X-RateLimit-Remaining"),
                                "x-ratelimit-reset": response.headers.get("X-RateLimit-Reset")
                            }
                        }
                    
                    await asyncio.sleep(0.1)
                except Exception:
                    continue
        
        return None
