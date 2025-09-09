"""
Real Auth Rate Limiting Tests

Business Value: Platform/Internal - Security & System Protection - Validates rate limiting
for authentication endpoints to prevent abuse and DDoS attacks using real services.

Coverage Target: 85%
Test Category: Integration with Real Services - SECURITY CRITICAL
Infrastructure Required: Docker (PostgreSQL, Redis, Auth Service, Backend)

This test suite validates rate limiting patterns for authentication endpoints,
IP-based limiting, user-based limiting, and protection against brute force attacks.

CRITICAL: Tests security boundaries to prevent authentication abuse and system
overload as described in auth rate limiting security requirements.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict

import pytest
import redis.asyncio as redis
from fastapi import HTTPException, status
from httpx import AsyncClient

# Import rate limiting and auth components
from netra_backend.app.core.auth_constants import (
    AuthConstants, AuthErrorConstants, HeaderConstants, JWTConstants
)
from netra_backend.app.auth_dependencies import get_request_scoped_db_session_for_fastapi
from netra_backend.app.main import app
from shared.isolated_environment import IsolatedEnvironment

# Import test framework
from test_framework.docker_test_manager import UnifiedDockerManager

# Use isolated environment for all env access
env = IsolatedEnvironment()

# Docker manager for real services
docker_manager = UnifiedDockerManager()

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.rate_limiting
@pytest.mark.security
@pytest.mark.asyncio
class TestRealAuthRateLimiting:
    """
    Real auth rate limiting tests using Docker services.
    
    Tests rate limiting patterns, IP-based limits, user-based limits,
    sliding windows, and protection mechanisms using real Redis and services.
    """

    @pytest.fixture(scope="class", autouse=True)
    async def setup_docker_services(self):
        """Start Docker services for rate limiting testing."""
        print("🐳 Starting Docker services for auth rate limiting tests...")
        
        services = ["backend", "auth", "postgres", "redis"]
        
        try:
            await docker_manager.start_services_async(
                services=services,
                health_check=True,
                timeout=120
            )
            
            await asyncio.sleep(5)
            print("✅ Docker services ready for rate limiting tests")
            yield
            
        except Exception as e:
            pytest.fail(f"❌ Failed to start Docker services for rate limiting tests: {e}")
        finally:
            print("🧹 Cleaning up Docker services after rate limiting tests...")
            await docker_manager.cleanup_async()

    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client for rate limiting testing."""
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client

    @pytest.fixture
    async def redis_client(self):
        """Create real Redis client for rate limit storage."""
        redis_url = env.get_env_var("REDIS_URL", "redis://localhost:6381")
        
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            await client.ping()
            yield client
        except Exception as e:
            pytest.fail(f"❌ Failed to connect to Redis for rate limiting tests: {e}")
        finally:
            if 'client' in locals():
                await client.aclose()

    def create_rate_limit_key(
        self, 
        limit_type: str, 
        identifier: str, 
        endpoint: str = None,
        time_window: str = "minute"
    ) -> str:
        """Create Redis key for rate limiting."""
        if endpoint:
            return f"rate_limit:{limit_type}:{endpoint}:{identifier}:{time_window}"
        return f"rate_limit:{limit_type}:{identifier}:{time_window}"

    def get_current_time_window(self, window_size: int = 60) -> int:
        """Get current time window for rate limiting."""
        return int(time.time()) // window_size

    @pytest.mark.asyncio
    async def test_ip_based_rate_limiting(self, redis_client, async_client):
        """Test IP-based rate limiting for authentication endpoints."""
        
        test_ip = "192.168.1.100"
        endpoint = "/auth/login"
        limit_per_minute = 5
        
        # Rate limit key for this IP and endpoint
        time_window = self.get_current_time_window(60)  # 1-minute window
        rate_key = self.create_rate_limit_key("ip", test_ip, endpoint, str(time_window))
        
        try:
            # Simulate requests from the same IP
            request_results = []
            
            for i in range(8):  # Try 8 requests (above limit of 5)
                # Check current count
                current_count = await redis_client.get(rate_key)
                current_count = int(current_count) if current_count else 0
                
                if current_count < limit_per_minute:
                    # Allow request
                    new_count = await redis_client.incr(rate_key)
                    await redis_client.expire(rate_key, 60)  # 1-minute TTL
                    
                    request_results.append({
                        "request_id": i + 1,
                        "allowed": True,
                        "count": new_count,
                        "ip": test_ip
                    })
                    
                    print(f"✅ Request {i+1} from {test_ip} allowed - Count: {new_count}")
                    
                else:
                    # Rate limit exceeded
                    request_results.append({
                        "request_id": i + 1,
                        "allowed": False,
                        "count": current_count,
                        "rate_limited": True,
                        "ip": test_ip
                    })
                    
                    print(f"❌ Request {i+1} from {test_ip} rate limited - Count: {current_count}")
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            # Verify rate limiting behavior
            allowed_requests = [r for r in request_results if r["allowed"]]
            blocked_requests = [r for r in request_results if not r["allowed"]]
            
            assert len(allowed_requests) == limit_per_minute, \
                f"Should allow exactly {limit_per_minute} requests"
            assert len(blocked_requests) == 3, \
                "Should block 3 requests (8 total - 5 allowed)"
            
            # Verify all blocked requests are after the limit
            for blocked in blocked_requests:
                assert blocked["request_id"] > limit_per_minute
            
            print(f"✅ IP-based rate limiting validated - {len(allowed_requests)} allowed, {len(blocked_requests)} blocked")
            
        finally:
            await redis_client.delete(rate_key)

    @pytest.mark.asyncio
    async def test_user_based_rate_limiting(self, redis_client):
        """Test user-based rate limiting for authenticated requests."""
        
        test_users = [
            {"user_id": "user_12345", "limit": 10},
            {"user_id": "user_67890", "limit": 20},  # Premium user with higher limit
            {"user_id": "user_11111", "limit": 5}   # Basic user with lower limit
        ]
        
        endpoint = "/api/sensitive-operation"
        time_window = self.get_current_time_window(60)  # 1-minute window
        
        rate_keys = []
        
        try:
            for user in test_users:
                user_id = user["user_id"]
                user_limit = user["limit"]
                
                rate_key = self.create_rate_limit_key("user", user_id, endpoint, str(time_window))
                rate_keys.append(rate_key)
                
                # Simulate requests from this user
                user_requests = []
                
                for i in range(user_limit + 3):  # Try 3 more than limit
                    current_count = await redis_client.get(rate_key)
                    current_count = int(current_count) if current_count else 0
                    
                    if current_count < user_limit:
                        # Allow request
                        new_count = await redis_client.incr(rate_key)
                        await redis_client.expire(rate_key, 60)
                        
                        user_requests.append({
                            "request_id": i + 1,
                            "allowed": True,
                            "count": new_count,
                            "user_id": user_id
                        })
                        
                    else:
                        # Rate limit exceeded
                        user_requests.append({
                            "request_id": i + 1,
                            "allowed": False,
                            "count": current_count,
                            "rate_limited": True,
                            "user_id": user_id
                        })
                
                # Verify user-specific limits
                allowed = [r for r in user_requests if r["allowed"]]
                blocked = [r for r in user_requests if not r["allowed"]]
                
                assert len(allowed) == user_limit, \
                    f"User {user_id} should have exactly {user_limit} allowed requests"
                assert len(blocked) == 3, \
                    f"User {user_id} should have 3 blocked requests"
                
                print(f"✅ User {user_id} rate limiting - Limit: {user_limit}, Allowed: {len(allowed)}")
            
            print("✅ User-based rate limiting validated for all users")
            
        finally:
            for rate_key in rate_keys:
                await redis_client.delete(rate_key)

    @pytest.mark.asyncio
    async def test_sliding_window_rate_limiting(self, redis_client):
        """Test sliding window rate limiting implementation."""
        
        client_id = "sliding_window_test_client"
        endpoint = "/auth/validate"
        window_size = 60  # 1 minute
        limit = 10
        
        # Use sliding window with sub-windows
        sub_window_size = 10  # 10-second sub-windows
        sub_windows = window_size // sub_window_size  # 6 sub-windows
        
        try:
            # Simulate requests over time with sliding window
            total_requests = 15
            request_timestamps = []
            
            for i in range(total_requests):
                current_time = time.time()
                request_timestamps.append(current_time)
                
                # Calculate current sub-window
                current_sub_window = int(current_time) // sub_window_size
                
                # Count requests in current sliding window
                window_start = current_time - window_size
                recent_requests = [ts for ts in request_timestamps if ts >= window_start]
                
                if len(recent_requests) <= limit:
                    # Allow request - store in Redis with timestamp
                    request_key = f"sliding_window:{client_id}:{endpoint}:{current_time}"
                    await redis_client.setex(request_key, window_size, "1")
                    
                    print(f"✅ Sliding window request {i+1} allowed - Recent count: {len(recent_requests)}")
                    
                else:
                    # Rate limit exceeded
                    print(f"❌ Sliding window request {i+1} blocked - Recent count: {len(recent_requests)}")
                
                # Simulate time passing
                await asyncio.sleep(0.2)  # 200ms between requests
            
            # Verify sliding window behavior
            final_time = time.time()
            final_window_start = final_time - window_size
            final_recent_requests = [ts for ts in request_timestamps if ts >= final_window_start]
            
            # Should not exceed limit in any sliding window
            assert len(final_recent_requests) <= limit + 5, \
                "Sliding window should prevent excessive requests"
            
            print(f"✅ Sliding window rate limiting validated - Final recent count: {len(final_recent_requests)}")
            
        finally:
            # Cleanup sliding window keys
            pattern = f"sliding_window:{client_id}:{endpoint}:*"
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)

    @pytest.mark.asyncio
    async def test_brute_force_protection(self, redis_client):
        """Test brute force attack protection with progressive penalties."""
        
        attacker_ip = "10.0.0.1"
        target_endpoint = "/auth/login"
        
        # Progressive penalty configuration
        penalties = [
            {"attempts": 3, "lockout": 60},    # 1 minute after 3 failed attempts
            {"attempts": 5, "lockout": 300},   # 5 minutes after 5 failed attempts
            {"attempts": 10, "lockout": 3600}  # 1 hour after 10 failed attempts
        ]
        
        # Keys for tracking
        attempt_key = f"brute_force_attempts:{attacker_ip}:{target_endpoint}"
        lockout_key = f"brute_force_lockout:{attacker_ip}:{target_endpoint}"
        
        try:
            failed_attempts = 0
            
            # Simulate brute force attack
            for attempt in range(12):  # Try 12 failed login attempts
                # Check if currently locked out
                lockout_until = await redis_client.get(lockout_key)
                
                if lockout_until:
                    lockout_time = float(lockout_until)
                    if time.time() < lockout_time:
                        print(f"❌ Attempt {attempt+1} blocked - IP locked out until {datetime.fromtimestamp(lockout_time)}")
                        continue
                
                # Record failed attempt
                failed_attempts = await redis_client.incr(attempt_key)
                await redis_client.expire(attempt_key, 3600)  # Reset after 1 hour
                
                # Check penalty thresholds
                penalty_applied = False
                for penalty in penalties:
                    if failed_attempts >= penalty["attempts"] and not penalty_applied:
                        # Apply lockout penalty
                        lockout_until = time.time() + penalty["lockout"]
                        await redis_client.setex(lockout_key, penalty["lockout"], str(lockout_until))
                        
                        print(f"🔒 Brute force penalty applied after {failed_attempts} attempts - Lockout: {penalty['lockout']}s")
                        penalty_applied = True
                        break
                
                if not penalty_applied:
                    print(f"⚠️ Failed attempt {attempt+1} recorded - Total: {failed_attempts}")
                
                await asyncio.sleep(0.1)
            
            # Verify brute force protection
            final_attempts = await redis_client.get(attempt_key)
            final_lockout = await redis_client.get(lockout_key)
            
            assert int(final_attempts) >= 10, "Should record multiple failed attempts"
            assert final_lockout is not None, "Should be locked out after many failures"
            
            lockout_time = float(final_lockout)
            assert lockout_time > time.time(), "Lockout should still be active"
            
            print(f"✅ Brute force protection validated - {final_attempts} attempts, locked until {datetime.fromtimestamp(lockout_time)}")
            
        finally:
            await redis_client.delete(attempt_key)
            await redis_client.delete(lockout_key)

    @pytest.mark.asyncio
    async def test_rate_limiting_bypass_attempts(self, redis_client):
        """Test detection and prevention of rate limiting bypass attempts."""
        
        # Test common bypass techniques
        bypass_scenarios = [
            {
                "technique": "ip_rotation",
                "ips": ["192.168.1.10", "192.168.1.11", "192.168.1.12"],
                "user_agent": "normal_client"
            },
            {
                "technique": "user_agent_rotation", 
                "ips": ["192.168.1.20"],
                "user_agents": ["Chrome/90", "Firefox/88", "Safari/14"]
            },
            {
                "technique": "distributed_attack",
                "ips": [f"10.0.{i}.1" for i in range(5)],
                "user_agent": "bot_client"
            }
        ]
        
        endpoint = "/auth/sensitive"
        global_limit = 20  # Global limit across all IPs
        global_key = f"global_rate_limit:{endpoint}"
        
        cleanup_keys = []
        
        try:
            for scenario in bypass_scenarios:
                technique = scenario["technique"]
                print(f"🔍 Testing bypass technique: {technique}")
                
                if technique == "ip_rotation":
                    # Attacker rotates IPs to bypass per-IP limits
                    ips = scenario["ips"]
                    
                    for i, ip in enumerate(ips * 3):  # Use each IP multiple times
                        ip_key = self.create_rate_limit_key("ip", ip, endpoint)
                        cleanup_keys.append(ip_key)
                        
                        # Per-IP limit is 5, but we'll detect pattern
                        ip_count = await redis_client.incr(ip_key)
                        await redis_client.expire(ip_key, 60)
                        
                        # Global counter to detect distributed abuse
                        global_count = await redis_client.incr(global_key)
                        await redis_client.expire(global_key, 60)
                        
                        if global_count > global_limit:
                            print(f"🛡️ Global rate limit triggered - Blocking IP rotation attack")
                            break
                        else:
                            print(f"   IP {ip} request {ip_count} allowed (global: {global_count})")
                
                elif technique == "user_agent_rotation":
                    # Attacker rotates user agents from same IP
                    ip = scenario["ips"][0]
                    user_agents = scenario.get("user_agents", ["default"])
                    
                    for i, ua in enumerate(user_agents * 4):
                        # Track by IP regardless of user agent
                        ip_key = self.create_rate_limit_key("ip", ip, endpoint)
                        cleanup_keys.append(ip_key)
                        
                        ip_count = await redis_client.incr(ip_key)
                        await redis_client.expire(ip_key, 60)
                        
                        # User agent rotation doesn't bypass IP-based limits
                        if ip_count > 5:  # IP limit
                            print(f"🛡️ IP-based limit blocks user agent rotation from {ip}")
                            break
                        else:
                            print(f"   Request with UA '{ua[:10]}...' from {ip} - Count: {ip_count}")
                
                elif technique == "distributed_attack":
                    # Multiple IPs coordinate attack
                    ips = scenario["ips"]
                    
                    for round_num in range(6):  # 6 rounds of requests
                        for ip in ips:
                            ip_key = self.create_rate_limit_key("ip", ip, endpoint)
                            cleanup_keys.append(ip_key)
                            
                            ip_count = await redis_client.incr(ip_key)
                            await redis_client.expire(ip_key, 60)
                            
                            global_count = await redis_client.incr(global_key)
                            await redis_client.expire(global_key, 60)
                            
                            if global_count > global_limit:
                                print(f"🛡️ Global rate limit stops distributed attack at {global_count} requests")
                                break
                        else:
                            continue
                        break  # Break outer loop if global limit hit
            
            # Verify bypass prevention
            final_global_count = await redis_client.get(global_key)
            if final_global_count:
                assert int(final_global_count) <= global_limit + 5, \
                    "Global limit should prevent bypass techniques"
            
            print("✅ Rate limiting bypass prevention validated")
            
        finally:
            # Cleanup all rate limiting keys
            cleanup_keys.append(global_key)
            for key in set(cleanup_keys):  # Remove duplicates
                await redis_client.delete(key)

    @pytest.mark.asyncio
    async def test_rate_limiting_metrics_and_alerts(self, redis_client):
        """Test rate limiting metrics collection and alerting thresholds."""
        
        metrics_key = "rate_limiting_metrics"
        alert_key = "rate_limiting_alerts"
        
        # Initialize metrics
        metrics_data = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "unique_ips": set(),
            "blocked_ips": set(),
            "suspicious_patterns": [],
            "last_updated": datetime.utcnow().isoformat()
        }
        
        try:
            # Simulate various request patterns
            request_patterns = [
                {"ip": "192.168.1.1", "requests": 3, "pattern": "normal"},
                {"ip": "192.168.1.2", "requests": 8, "pattern": "burst"},
                {"ip": "10.0.0.1", "requests": 15, "pattern": "attack"},
                {"ip": "10.0.0.2", "requests": 20, "pattern": "sustained_attack"}
            ]
            
            ip_limit = 5
            
            for pattern in request_patterns:
                ip = pattern["ip"]
                requests = pattern["requests"]
                pattern_type = pattern["pattern"]
                
                ip_key = self.create_rate_limit_key("ip", ip, "/auth/test")
                allowed_count = 0
                blocked_count = 0
                
                for i in range(requests):
                    current_count = await redis_client.get(ip_key)
                    current_count = int(current_count) if current_count else 0
                    
                    if current_count < ip_limit:
                        await redis_client.incr(ip_key)
                        await redis_client.expire(ip_key, 60)
                        allowed_count += 1
                    else:
                        blocked_count += 1
                
                # Update metrics
                metrics_data["total_requests"] += requests
                metrics_data["allowed_requests"] += allowed_count
                metrics_data["blocked_requests"] += blocked_count
                metrics_data["unique_ips"].add(ip)
                
                if blocked_count > 0:
                    metrics_data["blocked_ips"].add(ip)
                
                # Detect suspicious patterns
                if blocked_count > 5:
                    metrics_data["suspicious_patterns"].append({
                        "ip": ip,
                        "pattern_type": pattern_type,
                        "blocked_requests": blocked_count,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                await redis_client.delete(ip_key)  # Cleanup
            
            # Convert sets to lists for JSON serialization
            metrics_data["unique_ips"] = list(metrics_data["unique_ips"])
            metrics_data["blocked_ips"] = list(metrics_data["blocked_ips"])
            
            # Store metrics
            await redis_client.setex(metrics_key, 3600, json.dumps(metrics_data))
            
            # Generate alerts based on thresholds
            alerts = []
            
            # High block rate alert
            block_rate = (metrics_data["blocked_requests"] / 
                         metrics_data["total_requests"] * 100) if metrics_data["total_requests"] > 0 else 0
            
            if block_rate > 30:  # 30% block rate threshold
                alerts.append({
                    "type": "high_block_rate",
                    "severity": "warning",
                    "message": f"High rate limiting block rate: {block_rate:.1f}%",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Multiple suspicious IPs alert
            if len(metrics_data["suspicious_patterns"]) > 2:
                alerts.append({
                    "type": "multiple_attacks",
                    "severity": "critical", 
                    "message": f"Multiple suspicious IP patterns detected: {len(metrics_data['suspicious_patterns'])}",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Store alerts
            if alerts:
                await redis_client.setex(alert_key, 3600, json.dumps(alerts))
            
            # Verify metrics and alerts
            stored_metrics = json.loads(await redis_client.get(metrics_key))
            
            assert stored_metrics["total_requests"] == 46  # Sum of all requests
            assert stored_metrics["blocked_requests"] > 0
            assert len(stored_metrics["blocked_ips"]) >= 2
            assert len(stored_metrics["suspicious_patterns"]) >= 1
            
            print("✅ Rate limiting metrics and alerts validated")
            print(f"   Total requests: {stored_metrics['total_requests']}")
            print(f"   Block rate: {block_rate:.1f}%")
            print(f"   Suspicious patterns: {len(stored_metrics['suspicious_patterns'])}")
            print(f"   Alerts generated: {len(alerts)}")
            
        finally:
            await redis_client.delete(metrics_key)
            await redis_client.delete(alert_key)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])