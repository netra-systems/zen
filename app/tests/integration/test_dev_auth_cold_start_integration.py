"""
Dev Environment Auth Cold Start Integration Test

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & Platform Stability
- Value Impact: Prevents developer productivity loss from auth startup failures
- Revenue Impact: Protects $8K development velocity value

Tests auth service initialization from completely cold state in Dev environment,
immediate JWT token generation, backend dependency resolution, and crash recovery.
"""

import asyncio
import time
import pytest
from typing import Dict, Optional, Any
import httpx
import jwt
from datetime import datetime, timedelta

from app.core.configuration.database import DatabaseConfig
from app.core.secret_manager import SecretManager
from app.services.auth.auth_service import AuthService
from app.core.health_check import HealthCheckService
from test_framework.real_service_helper import RealServiceHelper


class DevAuthColdStartIntegrationTest:
    """Integration test for auth service cold start in Dev environment."""
    
    def __init__(self):
        self.auth_service: Optional[AuthService] = None
        self.backend_url = "http://localhost:8000"
        self.auth_url = "http://localhost:8001"
        self.service_helper = RealServiceHelper()
        self.health_service = HealthCheckService()
    
    async def setup(self):
        """Setup test environment with fresh state."""
        # Ensure clean database state
        await self._clean_database_state()
        
        # Clear any cached tokens or sessions
        await self._clear_redis_cache()
        
        # Generate fresh JWT secrets
        await self._generate_fresh_jwt_secrets()
    
    async def teardown(self):
        """Cleanup after tests."""
        if self.auth_service:
            await self.auth_service.shutdown()
        
        await self._restore_original_state()
    
    async def _clean_database_state(self):
        """Clean database to ensure cold start."""
        db_config = DatabaseConfig()
        async with db_config.get_connection() as conn:
            # Clear auth-related tables
            await conn.execute("TRUNCATE TABLE users CASCADE")
            await conn.execute("TRUNCATE TABLE sessions CASCADE")
            await conn.execute("TRUNCATE TABLE refresh_tokens CASCADE")
    
    async def _clear_redis_cache(self):
        """Clear Redis cache for fresh state."""
        import redis.asyncio as redis
        
        redis_client = redis.from_url("redis://localhost:6379")
        await redis_client.flushdb()
        await redis_client.close()
    
    async def _generate_fresh_jwt_secrets(self):
        """Generate new JWT secrets for testing."""
        secret_manager = SecretManager()
        new_secret = secret_manager.generate_secret_key()
        await secret_manager.store_secret("JWT_SECRET_KEY", new_secret)
        await secret_manager.store_secret("JWT_REFRESH_SECRET", new_secret + "_refresh")
    
    async def _restore_original_state(self):
        """Restore original system state after testing."""
        # Restore original JWT secrets if needed
        pass
    
    async def measure_auth_cold_start(self) -> float:
        """Measure time for auth service to start from cold state."""
        start_time = time.time()
        
        # Start auth service
        self.auth_service = await self.service_helper.start_auth_service(
            environment="development",
            cold_start=True
        )
        
        # Wait for service to be fully ready
        max_wait = 30  # seconds
        ready = False
        
        while time.time() - start_time < max_wait:
            try:
                health_status = await self.check_auth_health()
                if health_status.get("status") == "healthy":
                    ready = True
                    break
            except Exception:
                pass  # Service not ready yet
            
            await asyncio.sleep(0.5)
        
        if not ready:
            raise TimeoutError("Auth service failed to start within timeout")
        
        startup_time = time.time() - start_time
        return startup_time
    
    async def check_auth_health(self) -> Dict[str, Any]:
        """Check auth service health status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.auth_url}/health")
            return response.json()
    
    async def request_jwt_token_immediately(self) -> Optional[str]:
        """Request JWT token immediately after startup."""
        token_request = {
            "username": "test_user",
            "password": "test_password",
            "grant_type": "password"
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.auth_url}/auth/token",
                json=token_request
            )
            
            if response.status_code != 200:
                return None
            
            token_generation_time = time.time() - start_time
            
            # Validate token generation time
            assert token_generation_time < 2.0, f"Token generation took {token_generation_time}s"
            
            token_data = response.json()
            return token_data.get("access_token")
    
    async def validate_token_structure(self, token: str):
        """Validate JWT token structure and claims."""
        # Decode token without verification for structure check
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Validate required claims
        required_claims = ["sub", "exp", "iat", "jti"]
        for claim in required_claims:
            assert claim in decoded, f"Missing required claim: {claim}"
        
        # Validate expiration
        exp_time = datetime.fromtimestamp(decoded["exp"])
        assert exp_time > datetime.now(), "Token already expired"
        
        # Validate token is fresh (issued recently)
        iat_time = datetime.fromtimestamp(decoded["iat"])
        time_since_issue = datetime.now() - iat_time
        assert time_since_issue.total_seconds() < 5, "Token not freshly issued"
    
    async def test_backend_auth_dependency(self) -> httpx.Response:
        """Test backend service dependency on auth service."""
        # Attempt authenticated request to backend
        token = await self.request_jwt_token_immediately()
        assert token is not None, "Failed to get auth token"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.backend_url}/api/v1/user/profile",
                headers=headers
            )
            
            return response
    
    async def simulate_auth_service_crash(self):
        """Simulate auth service crash for recovery testing."""
        if self.auth_service:
            # Force stop auth service
            await self.auth_service.force_shutdown()
            
            # Wait for service to be fully down
            await asyncio.sleep(2)
            
            # Verify service is down
            try:
                await self.check_auth_health()
                assert False, "Auth service should be down"
            except httpx.ConnectError:
                pass  # Expected - service is down
    
    async def measure_auth_recovery(self) -> float:
        """Measure time for auth service to recover from crash."""
        recovery_start = time.time()
        
        # Restart auth service
        self.auth_service = await self.service_helper.start_auth_service(
            environment="development",
            cold_start=False  # Not cold start, recovery scenario
        )
        
        # Wait for recovery
        max_recovery_time = 30  # seconds
        recovered = False
        
        while time.time() - recovery_start < max_recovery_time:
            try:
                health_status = await self.check_auth_health()
                if health_status.get("status") == "healthy":
                    # Verify can generate tokens
                    token = await self.request_jwt_token_immediately()
                    if token:
                        recovered = True
                        break
            except Exception:
                pass  # Still recovering
            
            await asyncio.sleep(1)
        
        if not recovered:
            raise TimeoutError("Auth service failed to recover within timeout")
        
        recovery_time = time.time() - recovery_start
        return recovery_time


@pytest.mark.integration
@pytest.mark.requires_real_services
class TestDevAuthColdStartIntegration:
    """Test suite for Dev environment auth cold start."""
    
    @pytest.fixture
    async def test_harness(self):
        """Create test harness for auth cold start testing."""
        harness = DevAuthColdStartIntegrationTest()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    @pytest.mark.asyncio
    async def test_dev_auth_cold_start_integration(self, test_harness):
        """
        Test auth service startup from cold state in Dev environment.
        
        Validates:
        1. Cold start within 10 seconds
        2. Immediate token generation (<2 seconds)
        3. Backend dependency resolution
        4. Recovery from crashes within 15 seconds
        """
        # Phase 1: Cold Start Validation
        auth_startup_time = await test_harness.measure_auth_cold_start()
        assert auth_startup_time < 10.0, f"Auth startup took {auth_startup_time}s (limit: 10s)"
        
        # Phase 2: Immediate Token Generation
        token = await test_harness.request_jwt_token_immediately()
        assert token is not None, "Failed to generate token immediately after startup"
        await test_harness.validate_token_structure(token)
        
        # Phase 3: Backend Dependency Resolution
        backend_response = await test_harness.test_backend_auth_dependency()
        assert backend_response.status_code == 200, \
            f"Backend auth dependency failed: {backend_response.status_code}"
        
        # Phase 4: Recovery Testing
        await test_harness.simulate_auth_service_crash()
        recovery_time = await test_harness.measure_auth_recovery()
        assert recovery_time < 15.0, f"Auth recovery took {recovery_time}s (limit: 15s)"
    
    @pytest.mark.asyncio
    async def test_auth_health_check_cascade(self, test_harness):
        """Test health check cascade from auth to dependent services."""
        # Start auth service
        startup_time = await test_harness.measure_auth_cold_start()
        assert startup_time < 10.0
        
        # Check auth health
        auth_health = await test_harness.check_auth_health()
        assert auth_health["status"] == "healthy"
        assert "database" in auth_health.get("dependencies", {})
        assert "redis" in auth_health.get("dependencies", {})
        
        # Verify backend recognizes auth health
        async with httpx.AsyncClient() as client:
            backend_health = await client.get(f"{test_harness.backend_url}/health")
            backend_health_data = backend_health.json()
            
            assert "auth_service" in backend_health_data.get("dependencies", {})
            assert backend_health_data["dependencies"]["auth_service"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_jwt_secret_rotation_during_cold_start(self, test_harness):
        """Test JWT secret rotation handling during cold start."""
        # Start with first set of secrets
        startup_time = await test_harness.measure_auth_cold_start()
        assert startup_time < 10.0
        
        # Generate token with first secret
        token1 = await test_harness.request_jwt_token_immediately()
        assert token1 is not None
        
        # Rotate JWT secrets
        await test_harness._generate_fresh_jwt_secrets()
        
        # Restart auth service with new secrets
        await test_harness.simulate_auth_service_crash()
        recovery_time = await test_harness.measure_auth_recovery()
        assert recovery_time < 15.0
        
        # Generate token with new secret
        token2 = await test_harness.request_jwt_token_immediately()
        assert token2 is not None
        
        # Tokens should be different due to different secrets
        assert token1 != token2
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_during_startup(self, test_harness):
        """Test handling concurrent requests during auth startup."""
        # Start auth service
        startup_task = asyncio.create_task(
            test_harness.measure_auth_cold_start()
        )
        
        # Wait briefly then send concurrent requests
        await asyncio.sleep(2)
        
        # Send multiple concurrent token requests
        concurrent_requests = []
        for i in range(10):
            request_task = asyncio.create_task(
                test_harness.request_jwt_token_immediately()
            )
            concurrent_requests.append(request_task)
        
        # Wait for startup to complete
        startup_time = await startup_task
        assert startup_time < 10.0
        
        # Collect results from concurrent requests
        results = await asyncio.gather(*concurrent_requests, return_exceptions=True)
        
        # At least some requests should succeed
        successful_tokens = [r for r in results if r and not isinstance(r, Exception)]
        assert len(successful_tokens) > 0, "No concurrent requests succeeded during startup"
        
        # All successful tokens should be valid
        for token in successful_tokens:
            await test_harness.validate_token_structure(token)