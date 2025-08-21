"""Concurrent User Login Sessions L3 Integration Tests

Tests simultaneous login operations from multiple users to validate session
management, database connection pooling, and auth service scalability.

Business Value Justification (BVJ):
- Segment: Early/Mid (Multi-user organizations)
- Business Goal: Support organizational onboarding without bottlenecks
- Value Impact: Enable smooth onboarding for 100+ user organizations
- Strategic Impact: Reduces onboarding friction, improving conversion by 15%

Critical Path:
Concurrent login requests -> Auth validation -> Session creation ->
Database writes -> Redis caching -> Response coordination

Mock-Real Spectrum: L3 (Real auth with simulated users)
- Real authentication flow
- Real database connections
- Real session management
- Simulated concurrent users
"""

import pytest
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import random
import hashlib

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.schemas.auth_types import (

# Add project root to path
    LoginRequest, LoginResponse, SessionInfo,
    UserProfile, AuthError, RateLimitError
)
from netra_backend.app.core.config import get_settings
from netra_backend.app.db.redis_manager import get_redis_manager
from netra_backend.app.db.postgres import get_async_db
from clients.auth_client import auth_client
from netra_backend.app.core.monitoring import metrics_collector


@dataclass
class ConcurrentLoginMetrics:
    """Metrics for concurrent login testing"""
    total_attempts: int = 0
    successful_logins: int = 0
    failed_logins: int = 0
    duplicate_sessions: int = 0
    login_times: List[float] = field(default_factory=list)
    session_ids: Set[str] = field(default_factory=set)
    database_connections: List[int] = field(default_factory=list)
    redis_operations: int = 0
    conflict_resolutions: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_logins / self.total_attempts) * 100
    
    @property
    def avg_login_time(self) -> float:
        return sum(self.login_times) / len(self.login_times) if self.login_times else 0.0
    
    @property
    def max_login_time(self) -> float:
        return max(self.login_times) if self.login_times else 0.0


class TestConcurrentUserLoginSessions:
    """Test suite for concurrent user login sessions"""
    
    @pytest.fixture
    async def user_generator(self):
        """Generate test users with credentials"""
        def generate_users(count: int) -> List[Dict[str, str]]:
            users = []
            for i in range(count):
                user_id = str(uuid.uuid4())
                email = f"user_{i}_{user_id[:8]}@test.com"
                password = hashlib.sha256(f"password_{i}".encode()).hexdigest()
                users.append({
                    "user_id": user_id,
                    "email": email,
                    "password": password,
                    "username": f"user_{i}"
                })
            return users
        return generate_users
    
    @pytest.fixture
    async def session_monitor(self):
        """Monitor active sessions during tests"""
        redis_manager = get_redis_manager()
        
        async def get_active_sessions() -> int:
            sessions = await redis_manager.keys("session:*")
            return len(sessions)
        
        async def cleanup_sessions():
            sessions = await redis_manager.keys("session:test_*")
            if sessions:
                await redis_manager.delete(*sessions)
        
        return {
            "get_active": get_active_sessions,
            "cleanup": cleanup_sessions
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_concurrent_login_100_users(
        self, user_generator, session_monitor
    ):
        """Test 100 users logging in simultaneously"""
        metrics = ConcurrentLoginMetrics()
        users = user_generator(100)
        metrics.total_attempts = len(users)
        
        # Pre-register users in database
        async with get_async_db() as db:
            for user in users:
                await db.execute(
                    """
                    INSERT INTO users (id, email, password_hash, username)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (email) DO NOTHING
                    """,
                    user["user_id"], user["email"], user["password"], user["username"]
                )
            await db.commit()
        
        # Define concurrent login function
        async def perform_login(user: Dict[str, str]) -> Optional[LoginResponse]:
            start_time = time.time()
            try:
                response = await auth_client.login(
                    LoginRequest(
                        email=user["email"],
                        password=user["password"]
                    )
                )
                elapsed = time.time() - start_time
                metrics.login_times.append(elapsed)
                metrics.successful_logins += 1
                
                if response.session_id:
                    if response.session_id in metrics.session_ids:
                        metrics.duplicate_sessions += 1
                    metrics.session_ids.add(response.session_id)
                
                return response
            except Exception as e:
                elapsed = time.time() - start_time
                metrics.login_times.append(elapsed)
                metrics.failed_logins += 1
                return None
        
        # Execute concurrent logins
        initial_sessions = await session_monitor["get_active"]()
        
        tasks = [perform_login(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_sessions = await session_monitor["get_active"]()
        
        # Validate results
        assert metrics.success_rate >= 98.0, \
            f"Login success rate {metrics.success_rate}% below 98% threshold"
        
        assert metrics.duplicate_sessions == 0, \
            f"Found {metrics.duplicate_sessions} duplicate session IDs"
        
        assert metrics.avg_login_time < 2.0, \
            f"Average login time {metrics.avg_login_time}s exceeds 2s"
        
        assert metrics.max_login_time < 5.0, \
            f"Max login time {metrics.max_login_time}s exceeds 5s"
        
        # Verify session creation
        sessions_created = final_sessions - initial_sessions
        assert sessions_created >= metrics.successful_logins * 0.95, \
            f"Only {sessions_created} sessions created for {metrics.successful_logins} logins"
        
        # Cleanup
        await session_monitor["cleanup"]()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_login_session_isolation(self, user_generator):
        """Test that concurrent logins maintain session isolation"""
        users = user_generator(50)
        
        # Track session data for verification
        session_data = {}
        
        async def login_and_verify(user: Dict[str, str]) -> Dict[str, Any]:
            # Login
            response = await auth_client.login(
                LoginRequest(
                    email=user["email"],
                    password=user["password"]
                )
            )
            
            # Store session info
            session_info = {
                "user_id": user["user_id"],
                "session_id": response.session_id,
                "token": response.access_token
            }
            
            # Verify session data
            redis_manager = get_redis_manager()
            session_key = f"session:{response.session_id}"
            stored_data = await redis_manager.get(session_key)
            
            assert stored_data is not None, f"Session {response.session_id} not found"
            
            # Verify user context
            user_context = await auth_client.get_user_context(response.access_token)
            assert user_context.email == user["email"], \
                f"Session isolation breach: got {user_context.email}, expected {user['email']}"
            
            return session_info
        
        # Execute concurrent logins with verification
        tasks = [login_and_verify(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no session crosstalk
        successful_results = [r for r in results if isinstance(r, dict)]
        session_ids = [r["session_id"] for r in successful_results]
        unique_sessions = set(session_ids)
        
        assert len(session_ids) == len(unique_sessions), \
            "Session ID collision detected"
        
        # Verify each session maintains correct user context
        for result in successful_results:
            redis_manager = get_redis_manager()
            session_data = await redis_manager.get(f"session:{result['session_id']}")
            assert result["user_id"] in str(session_data), \
                "Session data doesn't match user"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_database_connection_pool_saturation(
        self, user_generator
    ):
        """Test behavior when database connection pool is saturated"""
        settings = get_settings()
        max_connections = settings.database_pool_size
        
        # Generate more users than connection pool size
        users = user_generator(max_connections * 2)
        
        connection_errors = []
        successful_logins = []
        
        async def login_with_monitoring(user: Dict[str, str]):
            try:
                # Add delay to increase connection hold time
                response = await auth_client.login(
                    LoginRequest(
                        email=user["email"],
                        password=user["password"]
                    )
                )
                # Simulate additional database operations
                await asyncio.sleep(0.5)
                successful_logins.append(response)
                return response
            except Exception as e:
                if "connection" in str(e).lower() or "pool" in str(e).lower():
                    connection_errors.append(e)
                raise
        
        # Execute logins to saturate pool
        tasks = [login_with_monitoring(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # System should queue requests, not fail
        assert len(connection_errors) == 0, \
            f"Connection pool errors: {len(connection_errors)}"
        
        # All logins should eventually succeed
        assert len(successful_logins) >= len(users) * 0.95, \
            f"Only {len(successful_logins)}/{len(users)} logins succeeded"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_simultaneous_multi_device_login(self, user_generator):
        """Test same user logging in from multiple devices simultaneously"""
        user = user_generator(1)[0]
        device_count = 5
        
        device_sessions = []
        
        async def login_from_device(device_id: str):
            response = await auth_client.login(
                LoginRequest(
                    email=user["email"],
                    password=user["password"],
                    device_id=device_id,
                    device_name=f"Device_{device_id}"
                )
            )
            return {
                "device_id": device_id,
                "session_id": response.session_id,
                "token": response.access_token
            }
        
        # Simultaneous login from multiple devices
        tasks = [login_from_device(f"device_{i}") for i in range(device_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_logins = [r for r in results if isinstance(r, dict)]
        
        # All devices should get separate sessions
        assert len(successful_logins) == device_count, \
            f"Expected {device_count} sessions, got {len(successful_logins)}"
        
        session_ids = [r["session_id"] for r in successful_logins]
        assert len(set(session_ids)) == device_count, \
            "Devices should have unique sessions"
        
        # Verify all sessions are active
        redis_manager = get_redis_manager()
        for session in successful_logins:
            session_data = await redis_manager.get(f"session:{session['session_id']}")
            assert session_data is not None, \
                f"Session {session['session_id']} not found"
            assert session["device_id"] in str(session_data), \
                "Device ID not stored in session"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_login_race_condition_handling(self, user_generator):
        """Test handling of race conditions during login"""
        users = user_generator(20)
        
        # Track race conditions
        race_conditions_handled = []
        
        async def login_with_race_detection(user: Dict[str, str], delay: float):
            await asyncio.sleep(delay)
            
            start_time = time.time()
            try:
                # Attempt login
                response = await auth_client.login(
                    LoginRequest(
                        email=user["email"],
                        password=user["password"]
                    )
                )
                
                # Check for session conflicts
                redis_manager = get_redis_manager()
                session_lock = await redis_manager.get(f"login_lock:{user['email']}")
                if session_lock:
                    race_conditions_handled.append(user["email"])
                
                return response
            except Exception as e:
                if "conflict" in str(e).lower() or "race" in str(e).lower():
                    race_conditions_handled.append(user["email"])
                raise
        
        # Create deliberate race conditions
        tasks = []
        for user in users:
            # Launch 3 concurrent login attempts per user
            for i in range(3):
                delay = random.uniform(0, 0.1)  # Small random delay
                tasks.append(login_with_race_detection(user, delay))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful logins per user
        successful_by_user = {}
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                user_idx = i // 3
                user_email = users[user_idx]["email"]
                successful_by_user[user_email] = \
                    successful_by_user.get(user_email, 0) + 1
        
        # Each user should have exactly 1 successful login
        # (system should prevent duplicate sessions)
        for user_email, count in successful_by_user.items():
            assert count <= 1, \
                f"User {user_email} has {count} concurrent sessions (expected max 1)"