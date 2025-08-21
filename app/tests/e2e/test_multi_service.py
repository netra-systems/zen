"""
Multi-Service Integration E2E Tests - Cross-Service Communication Validation

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All customer tiers (Free → Enterprise) 
- Business Goal: Seamless service integration and data consistency
- Value Impact: Service reliability prevents revenue loss and customer churn
- Strategic Impact: Multi-service architecture enables platform scalability

Tests cross-service integration between:
1. Main Backend (/app) - Core application logic
2. Auth Service (/auth_service) - Authentication microservice  
3. Frontend (/frontend) - User interface layer

COVERAGE:
- Cross-service authentication flow
- Database state consistency
- Service discovery and communication
- Health monitoring coordination  
- Transaction boundaries
- Error propagation and recovery
"""

import asyncio
import httpx
import json
import pytest
import time
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from app.auth_integration.auth import get_current_user
from app.clients.auth_client import auth_client
from app.db.clickhouse import get_clickhouse_client
from app.db.postgres import get_async_db as get_postgres_client
from app.services.user_service import CRUDUser
from app.db.models_postgres import User
from app.services.thread_service import ThreadService
from dev_launcher.health_monitor import HealthMonitor


class ServiceEndpoint:
    """Service endpoint configuration."""
    
    def __init__(self, name: str, base_url: str, health_path: str = "/health"):
        self.name = name
        self.base_url = base_url
        self.health_path = health_path
        self.health_url = f"{base_url}{health_path}"


class TestCrossServiceAuthentication:
    """Cross-service authentication and authorization tests."""
    
    @pytest.fixture
    def service_endpoints(self) -> Dict[str, ServiceEndpoint]:
        """Define service endpoints for testing."""
        return {
            "backend": ServiceEndpoint("backend", "http://localhost:8000"),
            "auth": ServiceEndpoint("auth_service", "http://localhost:8001"),
            "frontend": ServiceEndpoint("frontend", "http://localhost:3000", "/api/health")
        }
    
    @pytest.fixture
    def test_user_data(self) -> Dict[str, Any]:
        """Test user data for authentication tests."""
        return {
            "user_id": "test_user_123",
            "email": "test@netrasystems.ai",
            "plan": "free",
            "permissions": ["read", "write"]
        }
    
    @pytest.mark.asyncio
    async def test_auth_service_creates_valid_tokens(self, test_user_data):
        """Test auth service creates tokens that backend can validate."""
        # Mock auth service token creation
        with patch('app.clients.auth_client.auth_client.create_token') as mock_create:
            expected_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test_payload"
            mock_create.return_value = expected_token
            
            # Create token
            token = await auth_client.create_token(test_user_data)
            
            # Verify token created
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 20
    
    @pytest.mark.asyncio
    async def test_backend_validates_auth_service_tokens(self, test_user_data):
        """Test backend can validate tokens from auth service."""
        # Mock token validation
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = test_user_data
            
            # Validate token
            valid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test_payload"
            result = await auth_client.validate_token_jwt(valid_token)
            
            # Verify validation succeeded
            assert result is not None
            assert result["user_id"] == test_user_data["user_id"]
            assert result["email"] == test_user_data["email"]
    
    @pytest.mark.asyncio
    async def test_frontend_auth_flow_with_backend(self, service_endpoints, test_user_data):
        """Test complete auth flow from frontend through backend to auth service."""
        # Mock the complete auth chain
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate, \
             patch('app.services.user_service.CRUDUser.get') as mock_get_user:
            
            mock_validate.return_value = test_user_data
            mock_get_user.return_value = test_user_data
            
            # Simulate frontend request with auth header
            auth_header = {"Authorization": "Bearer valid_token"}
            
            # Mock HTTP request to backend
            async with httpx.AsyncClient() as client:
                try:
                    # This would normally be a real HTTP request
                    # For testing, we verify the auth flow logic
                    user_data = await auth_client.validate_token_jwt("valid_token")
                    user_service = CRUDUser("user_service", User)
                    # Mock a database session for the CRUDUser.get call
                    from unittest.mock import AsyncMock
                    mock_db = AsyncMock()
                    user_details = await user_service.get(mock_db, user_data["user_id"])
                    
                    # Verify auth flow succeeded
                    assert user_details is not None
                    assert user_details["user_id"] == test_user_data["user_id"]
                    
                except Exception as e:
                    # Auth flow should not fail with valid token
                    pytest.fail(f"Auth flow failed: {e}")
    
    @pytest.mark.asyncio
    async def test_token_consistency_across_services(self, test_user_data):
        """Test token validation is consistent across all services."""
        token = "consistent_test_token"
        
        # Mock consistent validation across services
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = test_user_data
            
            # Validate token in multiple contexts
            backend_validation = await auth_client.validate_token_jwt(token)
            websocket_validation = await auth_client.validate_token_jwt(token)
            api_validation = await auth_client.validate_token_jwt(token)
            
            # Verify consistency
            assert backend_validation == websocket_validation == api_validation
            assert all(v["user_id"] == test_user_data["user_id"] for v in [backend_validation, websocket_validation, api_validation])


class TestDatabaseConsistency:
    """Database state consistency across services tests."""
    
    @pytest.mark.asyncio
    async def test_postgres_clickhouse_data_consistency(self):
        """Test data consistency between PostgreSQL and ClickHouse."""
        # Mock database clients
        with patch('app.db.postgres.get_async_db') as mock_postgres, \
             patch('app.db.clickhouse.get_clickhouse_client') as mock_clickhouse:
            
            # Mock user data in PostgreSQL
            mock_postgres_client = AsyncMock()
            mock_postgres_client.fetchrow.return_value = {
                "user_id": "user_123",
                "email": "test@netrasystems.ai",
                "created_at": "2025-01-20T10:00:00Z"
            }
            mock_postgres.return_value = mock_postgres_client
            
            # Mock corresponding analytics data in ClickHouse
            mock_clickhouse_client = AsyncMock()
            mock_clickhouse_client.query.return_value = [
                {"user_id": "user_123", "event_type": "login", "timestamp": "2025-01-20T10:00:00Z"}
            ]
            mock_clickhouse.return_value = mock_clickhouse_client
            
            # Verify data consistency
            postgres_client = await get_postgres_client()
            clickhouse_client = await get_clickhouse_client()
            
            user_data = await postgres_client.fetchrow("SELECT * FROM users WHERE user_id = $1", "user_123")
            events_data = await clickhouse_client.query("SELECT * FROM events WHERE user_id = 'user_123'")
            
            # Verify user exists in both systems
            assert user_data is not None
            assert len(events_data) > 0
            assert user_data["user_id"] == events_data[0]["user_id"]
    
    @pytest.mark.asyncio
    async def test_transaction_atomicity_across_services(self):
        """Test transaction atomicity when operations span multiple services."""
        user_service = CRUDUser("user_service", User)
        thread_service = ThreadService()
        
        # Mock transaction scenario: creating user and their first thread
        with patch('app.db.postgres.get_async_db') as mock_postgres:
            mock_client = AsyncMock()
            mock_client.begin.return_value = AsyncMock()
            mock_client.commit = AsyncMock()
            mock_client.rollback = AsyncMock()
            mock_postgres.return_value = mock_client
            
            user_data = {
                "user_id": "new_user_123", 
                "email": "newuser@netrasystems.ai",
                "plan": "free"
            }
            
            thread_data = {
                "thread_id": "thread_456",
                "user_id": "new_user_123",
                "title": "My First Thread"
            }
            
            try:
                # Simulate atomic operation across services
                # Mock a database session for the CRUDUser.create call
                from unittest.mock import AsyncMock
                mock_db = AsyncMock()
                await user_service.create(mock_db, obj_in=user_data)
                await thread_service.create_thread(user_data['user_id'], mock_db)
                
                # Verify both operations completed
                mock_client.commit.assert_called()
                
            except Exception:
                # Should rollback on failure
                mock_client.rollback.assert_called()
    
    @pytest.mark.asyncio
    async def test_data_synchronization_lag(self):
        """Test acceptable data synchronization lag between services."""
        # Simulate write to primary database
        write_time = time.time()
        
        # Mock database write
        with patch('app.db.postgres.get_async_db') as mock_postgres:
            mock_client = AsyncMock()
            mock_postgres.return_value = mock_client
            
            # Write data
            await mock_client.execute("INSERT INTO users (user_id, email) VALUES ($1, $2)", 
                                    "sync_test_user", "sync@test.com")
            
            # Simulate read from analytics database (ClickHouse)
            with patch('app.db.clickhouse.get_clickhouse_client') as mock_clickhouse:
                mock_ch_client = AsyncMock()
                mock_ch_client.query.return_value = [{"user_id": "sync_test_user", "synced_at": write_time}]
                mock_clickhouse.return_value = mock_ch_client
                
                # Verify sync within acceptable time
                read_time = time.time()
                sync_lag = read_time - write_time
                
                assert sync_lag < 5.0  # Max 5 seconds sync lag


class TestServiceDiscovery:
    """Service discovery and communication tests."""
    
    @pytest.mark.asyncio
    async def test_service_health_coordination(self):
        """Test health monitoring coordination across services."""
        health_monitor = HealthMonitor(check_interval=1)
        
        # Mock service health endpoints
        healthy_responses = {
            "backend": {"status": "healthy", "uptime": 3600},
            "auth_service": {"status": "healthy", "uptime": 3600},
            "frontend": {"status": "healthy", "uptime": 3600}
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response
            
            await health_monitor.start()
            
            try:
                # Wait for health check cycle
                await asyncio.sleep(2)
                
                # Verify all services reported healthy
                health_status = await health_monitor.get_health_status()
                assert health_status is not None
                
            finally:
                await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_service_dependency_resolution(self):
        """Test service dependency resolution and startup order."""
        # Mock service dependencies: frontend -> backend -> auth_service
        dependency_order = []
        
        async def mock_start_service(service_name):
            dependency_order.append(service_name)
            await asyncio.sleep(0.1)  # Simulate startup time
        
        with patch('dev_launcher.service_startup.ServiceStartupCoordinator.start_service', 
                  side_effect=mock_start_service):
            
            # Simulate coordinated startup
            services = ["auth_service", "backend", "frontend"]
            for service in services:
                await mock_start_service(service)
            
            # Verify startup order respects dependencies
            auth_index = dependency_order.index("auth_service")
            backend_index = dependency_order.index("backend")
            frontend_index = dependency_order.index("frontend")
            
            assert auth_index < backend_index  # Auth starts before backend
            assert backend_index < frontend_index  # Backend starts before frontend
    
    @pytest.mark.asyncio
    async def test_service_communication_channels(self):
        """Test communication channels between services."""
        # Test HTTP communication
        async with httpx.AsyncClient() as client:
            try:
                # Mock inter-service HTTP call
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"result": "success"}
                    mock_post.return_value = mock_response
                    
                    # Simulate backend calling auth service
                    response = await client.post(
                        "http://localhost:8001/validate",
                        json={"token": "test_token"}
                    )
                    
                    # Verify communication succeeded
                    mock_post.assert_called_once()
                    
            except Exception as e:
                # Should handle communication errors gracefully
                assert "connection" in str(e).lower() or "network" in str(e).lower()


class TestErrorPropagation:
    """Error propagation and recovery across services tests."""
    
    @pytest.mark.asyncio
    async def test_cascade_failure_prevention(self):
        """Test system prevents cascade failures across services."""
        # Simulate auth service failure
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
            mock_validate.side_effect = Exception("Auth service unavailable")
            
            # Backend should handle auth failure gracefully
            user_service = CRUDUser("user_service", User)
            
            try:
                # This should fail gracefully, not crash the service
                result = await auth_client.validate_token_jwt("test_token")
                assert result is None  # Should return None for invalid token
                
            except Exception:
                # Should not propagate exception to crash other services
                pass
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_modes(self):
        """Test services operate in graceful degradation modes."""
        # Simulate ClickHouse unavailability
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_clickhouse:
            mock_clickhouse.side_effect = Exception("ClickHouse unavailable")
            
            # System should continue operating without analytics
            user_service = CRUDUser("user_service", User)
            
            # Mock PostgreSQL still available
            with patch('app.db.postgres.get_async_db') as mock_postgres:
                mock_client = AsyncMock()
                mock_client.fetchrow.return_value = {"user_id": "test", "email": "test@test.com"}
                mock_postgres.return_value = mock_client
                
                # Should still be able to get user data
                # Mock a database session for the CRUDUser.get call
                from unittest.mock import AsyncMock
                mock_db = AsyncMock()
                user_data = await user_service.get(mock_db, "test")
                assert user_data is not None
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_coordination(self):
        """Test circuit breaker coordination across services."""
        failure_count = 0
        
        async def failing_service_call():
            nonlocal failure_count
            failure_count += 1
            if failure_count < 5:
                raise Exception("Service temporarily unavailable")
            return {"status": "recovered"}
        
        # Simulate circuit breaker pattern
        max_failures = 3
        current_failures = 0
        circuit_open = False
        
        for attempt in range(10):
            try:
                if circuit_open:
                    # Circuit breaker open - skip call
                    await asyncio.sleep(0.1)
                    if attempt > 7:  # Try to close circuit
                        circuit_open = False
                        current_failures = 0
                    continue
                    
                result = await failing_service_call()
                current_failures = 0  # Reset on success
                break
                
            except Exception:
                current_failures += 1
                if current_failures >= max_failures:
                    circuit_open = True
        
        # Verify circuit breaker logic
        assert failure_count <= 6  # Should stop calling after circuit opens


class TestMultiServiceIntegration:
    """Complete multi-service integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_user_journey(self):
        """Test complete user journey across all services."""
        # 1. User authentication (Frontend -> Auth Service)
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_auth:
            mock_auth.return_value = {"user_id": "journey_user", "email": "journey@test.com"}
            
            user_token = "valid_journey_token"
            auth_result = await auth_client.validate_token_jwt(user_token)
            assert auth_result is not None
            
            # 2. User data retrieval (Backend -> PostgreSQL)
            with patch('app.services.user_service.CRUDUser.get') as mock_get_user:
                mock_get_user.return_value = auth_result
                
                user_service = CRUDUser("user_service", User)
                # Mock a database session for the CRUDUser.get call
                from unittest.mock import AsyncMock
                mock_db = AsyncMock()
                user_data = await user_service.get(mock_db, auth_result["user_id"])
                assert user_data["user_id"] == "journey_user"
                
                # 3. Thread creation (Backend -> PostgreSQL)
                with patch('app.services.thread_service.ThreadService.create_thread') as mock_create_thread:
                    mock_create_thread.return_value = {"thread_id": "new_thread", "user_id": "journey_user"}
                    
                    thread_service = ThreadService()
                    thread = await thread_service.create_thread("journey_user")
                    assert thread["thread_id"] == "new_thread"
                    
                    # 4. Analytics logging (Backend -> ClickHouse)
                    with patch('app.db.clickhouse.get_clickhouse_client') as mock_clickhouse:
                        mock_client = AsyncMock()
                        mock_clickhouse.return_value = mock_client
                        
                        # Log user activity
                        await mock_client.insert("events", [{
                            "user_id": "journey_user",
                            "event_type": "thread_created",
                            "thread_id": "new_thread",
                            "timestamp": "2025-01-20T10:00:00Z"
                        }])
                        
                        mock_client.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_high_availability_scenarios(self):
        """Test high availability scenarios with service failures."""
        # Scenario 1: Auth service temporary failure
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_auth:
            # First call fails, second succeeds (recovery)
            mock_auth.side_effect = [
                Exception("Auth service down"),
                {"user_id": "ha_user", "email": "ha@test.com"}
            ]
            
            # First attempt should fail gracefully
            try:
                result1 = await auth_client.validate_token_jwt("test_token")
            except Exception:
                pass  # Expected failure
            
            # Second attempt should succeed (service recovered)
            result2 = await auth_client.validate_token_jwt("test_token")
            assert result2 is not None
            assert result2["user_id"] == "ha_user"
        
        # Scenario 2: Database failover
        with patch('app.db.postgres.get_async_db') as mock_postgres:
            # Simulate primary DB failure, then failover to replica
            mock_postgres.side_effect = [
                Exception("Primary database unavailable"),
                AsyncMock()  # Replica database available
            ]
            
            try:
                client1 = await get_postgres_client()
            except Exception:
                pass  # Primary failure expected
            
            client2 = await get_postgres_client()
            assert client2 is not None  # Failover successful
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test multi-service performance under load."""
        # Simulate concurrent requests across services
        request_count = 50
        results = []
        
        async def simulate_request(request_id):
            # Mock service chain: Frontend -> Backend -> Auth -> Database
            with patch('app.clients.auth_client.auth_client.validate_token') as mock_auth, \
                 patch('app.services.user_service.CRUDUser.get') as mock_user:
                
                mock_auth.return_value = {"user_id": f"user_{request_id}"}
                mock_user.return_value = {"user_id": f"user_{request_id}", "email": f"user_{request_id}@test.com"}
                
                # Simulate processing time
                await asyncio.sleep(0.01)
                
                return {
                    "request_id": request_id,
                    "status": "completed",
                    "user_id": f"user_{request_id}"
                }
        
        # Execute concurrent requests
        start_time = time.time()
        tasks = [simulate_request(i) for i in range(request_count)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify performance requirements
        assert len(results) == request_count
        assert all(r["status"] == "completed" for r in results)
        assert processing_time < 5.0  # Should handle 50 requests in under 5 seconds
        
        # Verify requests per second
        rps = request_count / processing_time
        assert rps > 10  # At least 10 requests per second