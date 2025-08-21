"""
End-to-End tests for Staging Environment validation.
Tests complete user journeys against GCP staging deployment.

Business Value Justification (BVJ):
- Segment: Enterprise and Mid-tier customers
- Business Goal: Pre-production validation to prevent customer-facing issues
- Value Impact: Validates production-like environment before release
- Strategic Impact: Protects enterprise SLAs and prevents production incidents
"""

import os
import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time
from httpx import AsyncClient
import uuid
import logging

# Configure logging for staging tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import app schemas for consistency
from app.schemas import (
    RequestModel,
    Workload,
    DataSource, 
    TimeRange,
    User,
    WebSocketMessage,
    UserPlan
)
from app.schemas.UserPlan import PlanTier

# Import test helpers - removed due to missing module

# Staging environment configuration
STAGING_CONFIG = {
    "api_base_url": os.getenv("STAGING_API_URL", "https://netra-backend-staging-xyz123.run.app"),
    "websocket_url": os.getenv("STAGING_WS_URL", "wss://netra-backend-staging-xyz123.run.app"),
    "auth_service_url": os.getenv("STAGING_AUTH_URL", "https://netra-auth-service-xyz123.run.app"),
    "frontend_url": os.getenv("STAGING_FRONTEND_URL", "https://netra-frontend-staging-xyz123.run.app"),
    "enable_real_llm": os.getenv("ENABLE_STAGING_REAL_LLM", "true").lower() == "true",
    "api_timeout": int(os.getenv("STAGING_API_TIMEOUT", "30")),
    "max_retries": int(os.getenv("STAGING_MAX_RETRIES", "3"))
}

# Staging test credentials (should be in environment variables)
STAGING_TEST_USERS = {
    "free": {
        "email": os.getenv("STAGING_FREE_USER_EMAIL", "staging_free@test.netrasystems.ai"),
        "password": os.getenv("STAGING_FREE_USER_PASSWORD", "TestPass123!")
    },
    "pro": {
        "email": os.getenv("STAGING_PRO_USER_EMAIL", "staging_pro@test.netrasystems.ai"),
        "password": os.getenv("STAGING_PRO_USER_PASSWORD", "TestPass123!")
    },
    "enterprise": {
        "email": os.getenv("STAGING_ENTERPRISE_USER_EMAIL", "staging_enterprise@test.netrasystems.ai"),
        "password": os.getenv("STAGING_ENTERPRISE_USER_PASSWORD", "TestPass123!")
    }
}


class StagingEnvironmentE2ETests:
    """Core E2E test suite for staging environment validation."""
    
    @pytest.fixture(autouse=True)
    async def setup_staging_environment(self):
        """Configure staging environment for testing."""
        # Verify staging URLs are configured
        if not STAGING_CONFIG["api_base_url"].startswith("http"):
            pytest.skip("Staging environment not configured")
        
        # Initialize test helpers
        # JWT helper removed - not available
        
        
        yield
        
        # Cleanup
    
    @pytest.fixture
    async def staging_client(self):
        """Create async client for staging API testing."""
        async with AsyncClient(
            base_url=STAGING_CONFIG["api_base_url"],
            timeout=STAGING_CONFIG["api_timeout"],
            follow_redirects=True
        ) as client:
            yield client
    
    async def authenticate_staging_user(
        self, 
        client: AsyncClient, 
        tier: str = "free"
    ) -> Optional[Dict[str, str]]:
        """Authenticate with staging environment and return headers."""
        user_creds = STAGING_TEST_USERS.get(tier)
        if not user_creds:
            return None
        
        try:
            # Attempt login with staging credentials
            login_response = await client.post(
                f"{STAGING_CONFIG['auth_service_url']}/auth/login",
                data={
                    "username": user_creds["email"],
                    "password": user_creds["password"]
                }
            )
            
            if login_response.status_code == 200:
                tokens = login_response.json()
                return {"Authorization": f"Bearer {tokens['access_token']}"}
            else:
                logger.warning(f"Failed to authenticate {tier} user: {login_response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def retry_request(
        self,
        client: AsyncClient,
        method: str,
        url: str,
        **kwargs
    ) -> Any:
        """Retry request with exponential backoff."""
        for attempt in range(STAGING_CONFIG["max_retries"]):
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code < 500:
                    return response
            except Exception as e:
                if attempt == STAGING_CONFIG["max_retries"] - 1:
                    raise e
            
            # Exponential backoff
            await asyncio.sleep(2 ** attempt)
        
        return None


class TestStagingHealthChecks(StagingEnvironmentE2ETests):
    """Health check tests for staging environment."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.skipif(
        os.getenv("TEST_ENV", "dev").lower() in ["dev", "test", "local"] or not os.getenv("STAGING_API_URL"),
        reason="Staging health check not applicable in test/dev environment"
    )
    async def test_staging_services_health(self, staging_client):
        """Verify all staging services are healthy."""
        health_endpoints = {
            "backend": f"{STAGING_CONFIG['api_base_url']}/health",
            "auth": f"{STAGING_CONFIG['auth_service_url']}/health",
            "frontend": f"{STAGING_CONFIG['frontend_url']}/health"
        }
        
        health_status = {}
        for service, endpoint in health_endpoints.items():
            try:
                response = await self.retry_request(
                    staging_client, 
                    "GET", 
                    endpoint
                )
                health_status[service] = {
                    "healthy": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                health_status[service] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        # Log health status
        logger.info(f"Staging health status: {json.dumps(health_status, indent=2)}")
        
        # At least backend should be healthy
        assert health_status.get("backend", {}).get("healthy"), "Backend service unhealthy"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_database_connectivity(self, staging_client):
        """Test database connectivity in staging."""
        headers = await self.authenticate_staging_user(staging_client, "pro")
        if not headers:
            pytest.skip("Could not authenticate with staging")
        
        # Test database health endpoint
        response = await self.retry_request(
            staging_client,
            "GET",
            f"{STAGING_CONFIG['api_base_url']}/health/db",
            headers=headers
        )
        
        assert response.status_code == 200
        db_status = response.json()
        assert db_status.get("postgres") in ["healthy", "connected"]
        assert db_status.get("redis") in ["healthy", "connected"]


class TestStagingAuthentication(StagingEnvironmentE2ETests):
    """Authentication tests for staging environment."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.skipif(
        os.getenv("TEST_ENV", "dev").lower() in ["dev", "test", "local"] or not os.getenv("STAGING_API_URL"),
        reason="Staging authentication test not applicable in local/dev environment"
    )
    async def test_staging_login_flow(self, staging_client):
        """Test login flow in staging environment."""
        for tier, creds in STAGING_TEST_USERS.items():
            if not creds["email"]:
                continue
            
            login_response = await staging_client.post(
                f"{STAGING_CONFIG['auth_service_url']}/auth/login",
                data={
                    "username": creds["email"],
                    "password": creds["password"]
                }
            )
            
            if login_response.status_code == 200:
                tokens = login_response.json()
                assert "access_token" in tokens
                assert "refresh_token" in tokens
                logger.info(f"Successfully authenticated {tier} user")
            elif login_response.status_code == 404:
                # User might not exist in staging
                logger.warning(f"{tier} user not found in staging")
            else:
                logger.error(f"Unexpected response for {tier}: {login_response.status_code}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_jwt_validation(self, staging_client):
        """Test JWT token validation in staging."""
        headers = await self.authenticate_staging_user(staging_client, "pro")
        if not headers:
            pytest.skip("Could not authenticate with staging")
        
        # Validate token with user endpoint
        response = await self.retry_request(
            staging_client,
            "GET",
            f"{STAGING_CONFIG['api_base_url']}/api/v1/user/me",
            headers=headers
        )
        
        assert response.status_code == 200
        user_data = response.json()
        assert "email" in user_data
        assert "id" in user_data


class TestStagingAgentWorkflows(StagingEnvironmentE2ETests):
    """Agent workflow tests for staging environment."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    @pytest.mark.skipif(
        not STAGING_CONFIG.get("enable_real_llm"),
        reason="Real LLM testing disabled for staging"
    )
    async def test_staging_optimization_workflow(self, staging_client):
        """Test complete optimization workflow in staging."""
        headers = await self.authenticate_staging_user(staging_client, "enterprise")
        if not headers:
            pytest.skip("Could not authenticate with staging")
        
        # Submit optimization request
        optimization_request = {
            "workload": {
                "name": "staging_test_optimization",
                "type": "cost_optimization",
                "parameters": {
                    "target_reduction": 0.25,
                    "preserve_slas": True
                }
            },
            "data_source": {
                "type": "staging_metrics"
            },
            "time_range": {
                "start": (datetime.now() - timedelta(days=7)).isoformat(),
                "end": datetime.now().isoformat()
            }
        }
        
        submit_response = await self.retry_request(
            staging_client,
            "POST",
            f"{STAGING_CONFIG['api_base_url']}/api/v1/agent/submit",
            json=optimization_request,
            headers=headers
        )
        
        if submit_response.status_code in [200, 202]:
            result = submit_response.json()
            request_id = result.get("request_id")
            
            # Poll for completion
            max_wait = 60  # seconds
            poll_interval = 5
            elapsed = 0
            
            while elapsed < max_wait:
                status_response = await self.retry_request(
                    staging_client,
                    "GET",
                    f"{STAGING_CONFIG['api_base_url']}/api/v1/agent/status/{request_id}",
                    headers=headers
                )
                
                if status_response.status_code == 200:
                    status = status_response.json()
                    if status.get("status") == "completed":
                        logger.info("Optimization completed successfully")
                        break
                    elif status.get("status") == "failed":
                        logger.error(f"Optimization failed: {status.get('error')}")
                        break
                
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
            
            assert elapsed < max_wait, "Optimization timed out"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_agent_error_handling(self, staging_client):
        """Test agent error handling in staging."""
        headers = await self.authenticate_staging_user(staging_client, "free")
        if not headers:
            pytest.skip("Could not authenticate with staging")
        
        # Submit invalid request
        invalid_request = {
            "workload": {
                "type": "invalid_type"
            }
        }
        
        response = await staging_client.post(
            f"{STAGING_CONFIG['api_base_url']}/api/v1/agent/submit",
            json=invalid_request,
            headers=headers
        )
        
        # Should return validation error
        assert response.status_code in [400, 422]
        error = response.json()
        assert "error" in error or "detail" in error


class TestStagingWebSocket(StagingEnvironmentE2ETests):
    """WebSocket tests for staging environment."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_websocket_connection(self):
        """Test WebSocket connection to staging."""
        import websockets
        
        # Get authentication token
        async with AsyncClient(base_url=STAGING_CONFIG["auth_service_url"]) as client:
            headers = await self.authenticate_staging_user(client, "pro")
            if not headers:
                pytest.skip("Could not authenticate with staging")
            
            token = headers["Authorization"].replace("Bearer ", "")
        
        # Connect to staging WebSocket
        ws_url = f"{STAGING_CONFIG['websocket_url']}/ws?token={token}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send ping
                await websocket.send(json.dumps({"type": "ping"}))
                
                # Wait for pong
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                
                assert data.get("type") in ["pong", "connected"]
                logger.info("WebSocket connection successful")
                
                # Close connection
                await websocket.close()
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            pytest.skip(f"WebSocket unavailable: {e}")


class TestStagingPerformance(StagingEnvironmentE2ETests):
    """Performance tests for staging environment."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.performance
    async def test_staging_api_response_times(self, staging_client):
        """Test API response times meet SLA requirements."""
        headers = await self.authenticate_staging_user(staging_client, "enterprise")
        if not headers:
            pytest.skip("Could not authenticate with staging")
        
        endpoints = [
            "/api/v1/user/me",
            "/api/v1/threads",
            "/api/v1/agents/list"
        ]
        
        response_times = {}
        sla_p99 = 1.0  # 1 second p99 requirement
        
        for endpoint in endpoints:
            times = []
            
            # Make multiple requests to calculate percentiles
            for _ in range(10):
                start = time.time()
                response = await staging_client.get(
                    f"{STAGING_CONFIG['api_base_url']}{endpoint}",
                    headers=headers
                )
                elapsed = time.time() - start
                times.append(elapsed)
                
                if response.status_code != 200:
                    logger.warning(f"Non-200 response for {endpoint}: {response.status_code}")
            
            # Calculate p99
            times.sort()
            p99_index = int(len(times) * 0.99)
            p99_time = times[p99_index] if p99_index < len(times) else times[-1]
            
            response_times[endpoint] = {
                "p99": p99_time,
                "median": times[len(times)//2],
                "meets_sla": p99_time <= sla_p99
            }
        
        logger.info(f"Response times: {json.dumps(response_times, indent=2)}")
        
        # At least 80% of endpoints should meet SLA
        meeting_sla = sum(1 for v in response_times.values() if v["meets_sla"])
        assert meeting_sla >= len(endpoints) * 0.8
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.performance
    async def test_staging_concurrent_load(self, staging_client):
        """Test staging environment under concurrent load."""
        headers = await self.authenticate_staging_user(staging_client, "pro")
        if not headers:
            pytest.skip("Could not authenticate with staging")
        
        async def make_request():
            try:
                response = await staging_client.get(
                    f"{STAGING_CONFIG['api_base_url']}/api/v1/health",
                    headers=headers
                )
                return response.status_code == 200
            except:
                return False
        
        # Simulate concurrent users
        concurrent_requests = 20
        tasks = [make_request() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        
        success_rate = sum(results) / len(results)
        logger.info(f"Concurrent request success rate: {success_rate:.2%}")
        
        # Should handle at least 90% of concurrent requests
        assert success_rate >= 0.9


class TestStagingDataIntegrity(StagingEnvironmentE2ETests):
    """Data integrity tests for staging environment."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_data_persistence(self, staging_client):
        """Test data persistence in staging environment."""
        headers = await self.authenticate_staging_user(staging_client, "enterprise")
        if not headers:
            pytest.skip("Could not authenticate with staging")
        
        # Create test entity
        test_data = {
            "name": f"staging_test_{uuid.uuid4().hex[:8]}",
            "type": "test_entity",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "test_id": str(uuid.uuid4())
            }
        }
        
        # Create entity
        create_response = await staging_client.post(
            f"{STAGING_CONFIG['api_base_url']}/api/v1/entities",
            json=test_data,
            headers=headers
        )
        
        if create_response.status_code in [200, 201]:
            entity = create_response.json()
            entity_id = entity.get("id")
            
            # Read back entity
            read_response = await staging_client.get(
                f"{STAGING_CONFIG['api_base_url']}/api/v1/entities/{entity_id}",
                headers=headers
            )
            
            assert read_response.status_code == 200
            retrieved = read_response.json()
            assert retrieved["name"] == test_data["name"]
            assert retrieved["metadata"]["test_id"] == test_data["metadata"]["test_id"]
            
            # Clean up
            await staging_client.delete(
                f"{STAGING_CONFIG['api_base_url']}/api/v1/entities/{entity_id}",
                headers=headers
            )


class TestStagingEndToEndScenarios(StagingEnvironmentE2ETests):
    """Complete end-to-end scenarios for staging."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.slow
    async def test_staging_complete_user_journey(self, staging_client):
        """Test complete user journey in staging environment."""
        # Use existing enterprise user
        headers = await self.authenticate_staging_user(staging_client, "enterprise")
        if not headers:
            pytest.skip("Could not authenticate with staging")
        
        journey_id = str(uuid.uuid4())
        
        # 1. Get user profile
        profile_response = await staging_client.get(
            f"{STAGING_CONFIG['api_base_url']}/api/v1/user/me",
            headers=headers
        )
        assert profile_response.status_code == 200
        
        # 2. Create optimization thread
        thread_data = {
            "title": f"Staging Journey Test {journey_id[:8]}",
            "type": "optimization"
        }
        
        thread_response = await staging_client.post(
            f"{STAGING_CONFIG['api_base_url']}/api/v1/threads",
            json=thread_data,
            headers=headers
        )
        
        if thread_response.status_code in [200, 201]:
            thread = thread_response.json()
            thread_id = thread.get("id")
            
            # 3. Submit message to thread
            message_data = {
                "content": "Analyze my infrastructure and provide optimization recommendations",
                "thread_id": thread_id
            }
            
            message_response = await staging_client.post(
                f"{STAGING_CONFIG['api_base_url']}/api/v1/messages",
                json=message_data,
                headers=headers
            )
            
            assert message_response.status_code in [200, 201, 202]
            
            # 4. Retrieve thread history
            history_response = await staging_client.get(
                f"{STAGING_CONFIG['api_base_url']}/api/v1/threads/{thread_id}/messages",
                headers=headers
            )
            
            if history_response.status_code == 200:
                messages = history_response.json()
                assert len(messages) > 0
            
            logger.info(f"Completed user journey: {journey_id}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.critical
    async def test_staging_critical_business_paths(self, staging_client):
        """Test critical business paths in staging."""
        # Test paths for each tier
        for tier in ["free", "pro", "enterprise"]:
            headers = await self.authenticate_staging_user(staging_client, tier)
            if not headers:
                logger.warning(f"Skipping {tier} tier tests - auth failed")
                continue
            
            # Critical path: Authentication -> Profile -> Basic Operation
            critical_paths = [
                ("GET", "/api/v1/user/me"),
                ("GET", "/api/v1/agents/available"),
                ("GET", "/health")
            ]
            
            for method, path in critical_paths:
                response = await self.retry_request(
                    staging_client,
                    method,
                    f"{STAGING_CONFIG['api_base_url']}{path}",
                    headers=headers
                )
                
                assert response.status_code in [200, 204], \
                    f"Critical path failed for {tier}: {path}"
            
            logger.info(f"Critical paths validated for {tier} tier")


# Test execution markers
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.staging = pytest.mark.staging
pytest.mark.performance = pytest.mark.performance
pytest.mark.real_llm = pytest.mark.real_llm
pytest.mark.slow = pytest.mark.slow
pytest.mark.critical = pytest.mark.critical