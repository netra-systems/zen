"""Auth Token Refresh During High Load L3 Integration Tests

Tests token refresh mechanism under high concurrent load conditions to ensure
the auth service can handle enterprise-scale token refresh operations without
degradation or race conditions.

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (High concurrent user sessions)
- Business Goal: Support 10K+ concurrent users without auth failures
- Value Impact: Prevents auth bottlenecks that could lose $100K+ MRR
- Strategic Impact: Enterprise readiness and scalability confidence

Critical Path:
Multiple concurrent token refresh -> Rate limiting -> Queue management ->
Token validation -> Session update -> Response coordination

Mock-Real Spectrum: L3 (Real auth service with simulated load)
- Real JWT processing
- Real Redis session store
- Real rate limiting
- Simulated concurrent users
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import random
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from netra_backend.app.clients.auth_client import auth_client

from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.config import get_settings
from netra_backend.app.monitoring.metrics_collector import MetricsCollector
from netra_backend.app.db.redis_manager import get_redis_manager

from netra_backend.app.schemas.auth_types import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    SessionInfo,
    Token,
    TokenData,
)

@dataclass
class LoadTestMetrics:
    """Metrics for load testing analysis"""
    total_requests: int = 0
    successful_refreshes: int = 0
    failed_refreshes: int = 0
    rate_limited: int = 0
    response_times: List[float] = field(default_factory=list)
    error_types: Dict[str, int] = field(default_factory=dict)
    concurrent_peak: int = 0
    memory_usage_mb: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_refreshes / self.total_requests) * 100
    
    @property
    def avg_response_time(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def p95_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]

class TestAuthTokenRefreshHighLoad:
    """Test suite for auth token refresh under high load"""
    
    @pytest.fixture
    async def load_generator(self):
        """Generate concurrent refresh requests"""
        settings = get_settings()
        
        async def generate_user_tokens(count: int) -> List[Dict[str, str]]:
            """Generate initial tokens for test users"""
            tokens = []
            for i in range(count):
                user_data = {
                    "user_id": f"test_user_{i}",
                    "email": f"user{i}@test.com",
                    "exp": int(time.time()) + 300  # 5 min expiry
                }
                access_token = jwt.encode(
                    user_data,
                    settings.jwt_secret_key,
                    algorithm="HS256"
                )
                refresh_token = jwt.encode(
                    {"user_id": user_data["user_id"], "type": "refresh"},
                    settings.jwt_secret_key,
                    algorithm="HS256"
                )
                tokens.append({
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user_id": user_data["user_id"]
                })
            return tokens
        
        return generate_user_tokens
    
    @pytest.fixture
    async def metrics_tracker(self):
        """Track load test metrics"""
        return LoadTestMetrics()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_concurrent_token_refresh_1000_users(
        self, load_generator, metrics_tracker
    ):
        """Test 1000 concurrent token refresh operations"""
        # Generate initial tokens
        user_count = 1000
        tokens = await load_generator(user_count)
        metrics_tracker.total_requests = user_count
        
        # Create refresh tasks
        async def refresh_token(token_data: Dict[str, str]) -> Optional[RefreshResponse]:
            """Single token refresh operation"""
            start_time = time.time()
            try:
                response = await auth_client.refresh_token(
                    RefreshRequest(refresh_token=token_data["refresh_token"])
                )
                elapsed = time.time() - start_time
                metrics_tracker.response_times.append(elapsed)
                metrics_tracker.successful_refreshes += 1
                return response
            except Exception as e:
                elapsed = time.time() - start_time
                metrics_tracker.response_times.append(elapsed)
                metrics_tracker.failed_refreshes += 1
                error_type = type(e).__name__
                metrics_tracker.error_types[error_type] = \
                    metrics_tracker.error_types.get(error_type, 0) + 1
                if "rate_limit" in str(e).lower():
                    metrics_tracker.rate_limited += 1
                return None
        
        # Execute concurrent refreshes
        tasks = [refresh_token(token) for token in tokens]
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Validate results
        assert metrics_tracker.success_rate >= 95.0, \
            f"Success rate {metrics_tracker.success_rate}% below 95% threshold"
        
        assert metrics_tracker.avg_response_time < 1.0, \
            f"Average response time {metrics_tracker.avg_response_time}s exceeds 1s"
        
        assert metrics_tracker.p95_response_time < 2.0, \
            f"P95 response time {metrics_tracker.p95_response_time}s exceeds 2s"
        
        # Check for memory leaks
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        assert memory_mb < 500, f"Memory usage {memory_mb}MB exceeds 500MB limit"
        
        print(f"Load test completed: {metrics_tracker.success_rate:.2f}% success rate")
        print(f"Avg response time: {metrics_tracker.avg_response_time:.3f}s")
        print(f"P95 response time: {metrics_tracker.p95_response_time:.3f}s")
        print(f"Total time: {total_time:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_sustained_refresh_load_pattern(
        self, load_generator, metrics_tracker
    ):
        """Test sustained refresh load with realistic patterns"""
        # Simulate realistic refresh pattern over 3 minutes
        duration_seconds = 180
        base_users = 100
        peak_users = 500
        
        async def generate_refresh_wave(user_count: int, wave_id: int):
            """Generate a wave of refresh requests"""
            tokens = await load_generator(user_count)
            tasks = []
            
            for token in tokens:
                # Add jitter to simulate real-world timing
                delay = random.uniform(0, 2)
                
                async def delayed_refresh(t, d):
                    await asyncio.sleep(d)
                    try:
                        return await auth_client.refresh_token(
                            RefreshRequest(refresh_token=t["refresh_token"])
                        )
                    except Exception as e:
                        return None
                
                tasks.append(delayed_refresh(token, delay))
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # Generate waves with varying intensity
        waves = []
        for i in range(10):
            # Simulate traffic spikes
            if i % 3 == 0:
                user_count = peak_users
            else:
                user_count = base_users + random.randint(-20, 50)
            
            waves.append(generate_refresh_wave(user_count, i))
            await asyncio.sleep(duration_seconds / 10)
        
        results = await asyncio.gather(*waves, return_exceptions=True)
        
        # Validate no circuit breaker trips
        redis_manager = get_redis_manager()
        circuit_state = await redis_manager.get("auth_circuit_breaker_state")
        assert circuit_state != "OPEN", "Circuit breaker tripped during sustained load"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_token_refresh_race_conditions(self, load_generator):
        """Test for race conditions in concurrent refresh of same token"""
        # Generate single user token
        tokens = await load_generator(1)
        token_data = tokens[0]
        
        # Attempt to refresh the same token concurrently
        concurrent_refreshes = 50
        
        async def refresh_same_token():
            try:
                return await auth_client.refresh_token(
                    RefreshRequest(refresh_token=token_data["refresh_token"])
                )
            except Exception as e:
                return e
        
        tasks = [refresh_same_token() for _ in range(concurrent_refreshes)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful refreshes
        successful = [r for r in results if isinstance(r, RefreshResponse)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        # Exactly one refresh should succeed (token should be invalidated after first use)
        assert len(successful) == 1, \
            f"Expected 1 successful refresh, got {len(successful)}"
        
        # Verify all failures are due to invalid token
        for failure in failed:
            assert "invalid" in str(failure).lower() or "expired" in str(failure).lower(), \
                f"Unexpected error: {failure}"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_refresh_with_memory_pressure(self, load_generator, metrics_tracker):
        """Test token refresh under memory pressure conditions"""
        import gc
        
        # Force garbage collection
        gc.collect()
        
        # Monitor memory during test
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Generate high volume of tokens
        user_count = 2000
        tokens = await load_generator(user_count)
        
        # Track memory during refreshes
        memory_samples = []
        
        async def refresh_with_monitoring(token_data):
            result = await auth_client.refresh_token(
                RefreshRequest(refresh_token=token_data["refresh_token"])
            )
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            return result
        
        # Execute refreshes in batches to stress memory
        batch_size = 200
        for i in range(0, user_count, batch_size):
            batch = tokens[i:i+batch_size]
            tasks = [refresh_with_monitoring(t) for t in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Force garbage collection between batches
            gc.collect()
            await asyncio.sleep(0.5)
        
        # Verify memory didn't grow excessively
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        assert memory_growth < 100, \
            f"Excessive memory growth: {memory_growth}MB"
        
        # Check for memory leak pattern
        if len(memory_samples) > 10:
            first_half_avg = statistics.mean(memory_samples[:len(memory_samples)//2])
            second_half_avg = statistics.mean(memory_samples[len(memory_samples)//2:])
            leak_indicator = second_half_avg - first_half_avg
            
            assert leak_indicator < 50, \
                f"Potential memory leak detected: {leak_indicator}MB growth"