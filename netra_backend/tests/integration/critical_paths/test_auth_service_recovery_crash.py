"""Auth Service Recovery After Crash L3 Integration Tests

Tests auth service resilience and recovery mechanisms after unexpected crashes,
ensuring session continuity, state recovery, and graceful degradation.

Business Value Justification (BVJ):
- Segment: ALL (Critical infrastructure for all tiers)
- Business Goal: Maintain 99.9% auth availability even during failures
- Value Impact: Prevents complete platform outage and $200K+ MRR loss
- Strategic Impact: Enterprise trust through demonstrated resilience

Critical Path:
Auth crash -> Detection -> Circuit breaker -> Fallback auth ->
State recovery -> Session restoration -> Service resumption

Mock-Real Spectrum: L3 (Real service with controlled failures)
- Real auth service processes
- Real state persistence
- Real circuit breakers
- Controlled crash simulation
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import os
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import psutil
import pytest
from clients.auth_client import auth_client

from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.config import get_settings
from netra_backend.app.core.monitoring import metrics_collector
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.db.redis_manager import get_redis_manager

from netra_backend.app.schemas.auth_types import (
    HealthResponse,
    LoginRequest,
    LoginResponse,
    ServiceStatus,
    SessionInfo,
    Token,
)

@dataclass
class RecoveryMetrics:
    """Metrics for crash recovery testing"""
    crash_time: Optional[float] = None
    detection_time: Optional[float] = None
    recovery_start_time: Optional[float] = None
    recovery_complete_time: Optional[float] = None
    requests_during_outage: int = 0
    requests_failed: int = 0
    requests_fallback: int = 0
    sessions_preserved: int = 0
    sessions_lost: int = 0
    state_corruption: bool = False
    
    @property
    def detection_latency(self) -> float:
        if self.crash_time and self.detection_time:
            return self.detection_time - self.crash_time
        return 0.0
    
    @property
    def recovery_time(self) -> float:
        if self.recovery_start_time and self.recovery_complete_time:
            return self.recovery_complete_time - self.recovery_start_time
        return 0.0
    
    @property
    def total_downtime(self) -> float:
        if self.crash_time and self.recovery_complete_time:
            return self.recovery_complete_time - self.crash_time
        return 0.0

class TestAuthServiceRecoveryCrash:
    """Test suite for auth service crash recovery"""
    
    @pytest.fixture
    async def auth_process_manager(self):
        """Manage auth service process for crash testing"""
        settings = get_settings()
        
        class ProcessManager:
            def __init__(self):
                self.process = None
                self.port = settings.auth_service_port
            
            async def start(self):
                """Start auth service process"""
                import subprocess
                self.process = subprocess.Popen(
                    ["python", "-m", "auth_service.main"],
                    env={**os.environ, "PORT": str(self.port)}
                )
                # Wait for service to be ready
                await self._wait_for_health()
            
            async def crash(self):
                """Simulate sudden crash"""
                if self.process:
                    self.process.kill()
                    self.process = None
            
            async def graceful_shutdown(self):
                """Simulate graceful shutdown"""
                if self.process:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                    self.process = None
            
            async def is_running(self) -> bool:
                """Check if process is running"""
                if not self.process:
                    return False
                return self.process.poll() is None
            
            async def _wait_for_health(self, timeout: int = 30):
                """Wait for service to be healthy"""
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        response = await auth_client.health_check()
                        if response.status == "healthy":
                            return True
                    except:
                        pass
                    await asyncio.sleep(0.5)
                raise TimeoutError("Auth service failed to start")
        
        manager = ProcessManager()
        yield manager
        
        # Cleanup
        if manager.process:
            manager.process.terminate()
    
    @pytest.fixture
    async def session_tracker(self):
        """Track sessions before and after crash"""
        redis_manager = get_redis_manager()
        
        async def snapshot_sessions() -> Dict[str, Any]:
            """Take snapshot of current sessions"""
            sessions = await redis_manager.keys("session:*")
            snapshot = {}
            for session_key in sessions:
                data = await redis_manager.get(session_key)
                snapshot[session_key] = data
            return snapshot
        
        async def compare_sessions(before: Dict, after: Dict) -> Tuple[int, int]:
            """Compare session snapshots"""
            preserved = len(set(before.keys()) & set(after.keys()))
            lost = len(set(before.keys()) - set(after.keys()))
            return preserved, lost
        
        return {
            "snapshot": snapshot_sessions,
            "compare": compare_sessions
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_auth_crash_detection_and_recovery(
        self, auth_process_manager, session_tracker
    ):
        """Test crash detection and automatic recovery"""
        metrics = RecoveryMetrics()
        
        # Start auth service
        await auth_process_manager.start()
        
        # Create active sessions
        test_users = []
        for i in range(10):
            response = await auth_client.login(
                LoginRequest(
                    email=f"user{i}@test.com",
                    password=f"password{i}"
                )
            )
            test_users.append(response)
        
        # Take session snapshot
        sessions_before = await session_tracker["snapshot"]()
        
        # Simulate crash
        metrics.crash_time = time.time()
        await auth_process_manager.crash()
        
        # Monitor for detection
        detected = False
        while not detected and time.time() - metrics.crash_time < 10:
            try:
                await auth_client.health_check()
            except Exception:
                metrics.detection_time = time.time()
                detected = True
                break
            await asyncio.sleep(0.1)
        
        assert detected, "Crash not detected within 10 seconds"
        assert metrics.detection_latency < 2.0, \
            f"Detection took {metrics.detection_latency}s (expected < 2s)"
        
        # Start recovery
        metrics.recovery_start_time = time.time()
        await auth_process_manager.start()
        metrics.recovery_complete_time = time.time()
        
        # Verify recovery
        health = await auth_client.health_check()
        assert health.status == "healthy", "Service not healthy after recovery"
        
        # Check session preservation
        sessions_after = await session_tracker["snapshot"]()
        preserved, lost = await session_tracker["compare"](
            sessions_before, sessions_after
        )
        metrics.sessions_preserved = preserved
        metrics.sessions_lost = lost
        
        # Sessions should be preserved (Redis persistence)
        assert metrics.sessions_preserved >= len(test_users) * 0.9, \
            f"Only {metrics.sessions_preserved}/{len(test_users)} sessions preserved"
        
        assert metrics.total_downtime < 30, \
            f"Total downtime {metrics.total_downtime}s exceeds 30s limit"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_requests_during_crash_fallback(
        self, auth_process_manager
    ):
        """Test request handling during auth service outage"""
        metrics = RecoveryMetrics()
        
        # Start service
        await auth_process_manager.start()
        
        # Create baseline session
        baseline_response = await auth_client.login(
            LoginRequest(email="baseline@test.com", password="password")
        )
        baseline_token = baseline_response.access_token
        
        # Crash service
        await auth_process_manager.crash()
        metrics.crash_time = time.time()
        
        # Attempt requests during outage
        outage_results = []
        
        async def request_during_outage(request_type: str):
            metrics.requests_during_outage += 1
            try:
                if request_type == "login":
                    result = await auth_client.login(
                        LoginRequest(email="test@test.com", password="password")
                    )
                elif request_type == "validate":
                    result = await auth_client.validate_token_jwt(baseline_token)
                elif request_type == "refresh":
                    result = await auth_client.refresh_token(baseline_token)
                
                # Check if fallback was used
                if hasattr(result, "_fallback"):
                    metrics.requests_fallback += 1
                return ("success", result)
            except Exception as e:
                metrics.requests_failed += 1
                return ("failed", str(e))
        
        # Send various request types
        tasks = []
        for _ in range(5):
            tasks.append(request_during_outage("login"))
            tasks.append(request_during_outage("validate"))
            tasks.append(request_during_outage("refresh"))
        
        outage_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        fallback_used = metrics.requests_fallback > 0
        complete_failures = metrics.requests_failed == metrics.requests_during_outage
        
        # Should use fallback or queue, not fail completely
        assert not complete_failures, \
            "All requests failed - no fallback mechanism"
        
        # If fallback exists, verify it worked
        if fallback_used:
            assert metrics.requests_fallback >= metrics.requests_during_outage * 0.5, \
                "Fallback not consistently available"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_state_consistency_after_recovery(
        self, auth_process_manager
    ):
        """Test that auth state remains consistent after crash recovery"""
        # Start service
        await auth_process_manager.start()
        
        # Create complex state
        users = []
        sessions = []
        tokens = []
        
        for i in range(20):
            # Create user with session
            response = await auth_client.login(
                LoginRequest(
                    email=f"user{i}@test.com",
                    password=f"password{i}"
                )
            )
            users.append({"email": f"user{i}@test.com", "id": response.user_id})
            sessions.append(response.session_id)
            tokens.append(response.access_token)
            
            # Add user to groups
            if i % 3 == 0:
                await auth_client.add_to_group(response.user_id, "admin")
            if i % 2 == 0:
                await auth_client.add_to_group(response.user_id, "premium")
        
        # Take state snapshot
        redis_manager = get_redis_manager()
        state_before = {
            "sessions": await redis_manager.keys("session:*"),
            "tokens": await redis_manager.keys("token:*"),
            "groups": await redis_manager.keys("group:*"),
            "users": await redis_manager.keys("user:*")
        }
        
        # Crash and recover
        await auth_process_manager.crash()
        await asyncio.sleep(2)
        await auth_process_manager.start()
        
        # Verify state consistency
        state_after = {
            "sessions": await redis_manager.keys("session:*"),
            "tokens": await redis_manager.keys("token:*"),
            "groups": await redis_manager.keys("group:*"),
            "users": await redis_manager.keys("user:*")
        }
        
        # Critical state should be preserved
        assert len(state_after["sessions"]) >= len(state_before["sessions"]) * 0.95, \
            "Session state corrupted"
        
        assert len(state_after["users"]) == len(state_before["users"]), \
            "User state corrupted"
        
        # Verify tokens still work
        valid_tokens = 0
        for token in tokens[:5]:  # Test sample
            try:
                result = await auth_client.validate_token_jwt(token)
                if result.valid:
                    valid_tokens += 1
            except:
                pass
        
        assert valid_tokens >= 4, \
            f"Only {valid_tokens}/5 tokens still valid after recovery"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_circuit_breaker_during_crash(
        self, auth_process_manager
    ):
        """Test circuit breaker behavior during auth crash"""
        settings = get_settings()
        
        # Start service
        await auth_process_manager.start()
        
        # Initialize circuit breaker monitoring
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5,
            expected_exception=Exception
        )
        
        # Crash service
        await auth_process_manager.crash()
        
        # Track circuit breaker state changes
        state_changes = []
        
        async def monitored_request():
            try:
                state_before = circuit_breaker.state
                result = await circuit_breaker.call(
                    auth_client.health_check
                )
                state_after = circuit_breaker.state
                
                if state_before != state_after:
                    state_changes.append((state_before, state_after, time.time()))
                
                return result
            except Exception as e:
                state_after = circuit_breaker.state
                if state_before != state_after:
                    state_changes.append((state_before, state_after, time.time()))
                raise
        
        # Send requests to trigger circuit breaker
        for i in range(10):
            try:
                await monitored_request()
            except:
                pass
            await asyncio.sleep(0.5)
        
        # Verify circuit breaker opened
        assert circuit_breaker.state == "OPEN", \
            "Circuit breaker didn't open during outage"
        
        # Verify state transitions
        assert len(state_changes) >= 2, \
            "Circuit breaker didn't transition states"
        
        # Start recovery
        await auth_process_manager.start()
        
        # Wait for circuit breaker recovery
        await asyncio.sleep(settings.circuit_breaker_recovery_timeout)
        
        # Verify circuit breaker closed after recovery
        try:
            await monitored_request()
            assert circuit_breaker.state == "CLOSED", \
                "Circuit breaker didn't close after recovery"
        except:
            pytest.fail("Circuit breaker still open after recovery")
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_graceful_vs_crash_recovery_comparison(
        self, auth_process_manager, session_tracker
    ):
        """Compare graceful shutdown vs crash recovery"""
        
        # Test graceful shutdown
        await auth_process_manager.start()
        
        # Create sessions
        for i in range(10):
            await auth_client.login(
                LoginRequest(
                    email=f"graceful{i}@test.com",
                    password=f"password{i}"
                )
            )
        
        graceful_before = await session_tracker["snapshot"]()
        
        graceful_start = time.time()
        await auth_process_manager.graceful_shutdown()
        await auth_process_manager.start()
        graceful_time = time.time() - graceful_start
        
        graceful_after = await session_tracker["snapshot"]()
        graceful_preserved, _ = await session_tracker["compare"](
            graceful_before, graceful_after
        )
        
        # Test crash recovery
        await auth_process_manager.start()
        
        # Create sessions
        for i in range(10):
            await auth_client.login(
                LoginRequest(
                    email=f"crash{i}@test.com",
                    password=f"password{i}"
                )
            )
        
        crash_before = await session_tracker["snapshot"]()
        
        crash_start = time.time()
        await auth_process_manager.crash()
        await auth_process_manager.start()
        crash_time = time.time() - crash_start
        
        crash_after = await session_tracker["snapshot"]()
        crash_preserved, _ = await session_tracker["compare"](
            crash_before, crash_after
        )
        
        # Compare results
        assert graceful_preserved >= crash_preserved, \
            "Graceful shutdown should preserve more sessions"
        
        assert graceful_time < crash_time, \
            "Graceful shutdown should be faster than crash recovery"
        
        # Both should preserve most sessions
        assert crash_preserved >= 8, \
            f"Crash recovery only preserved {crash_preserved}/10 sessions"
        
        assert graceful_preserved >= 9, \
            f"Graceful shutdown only preserved {graceful_preserved}/10 sessions"