"""L3 Integration Test: Multi-Service Auth Token Propagation

Business Value Justification (BVJ):
- Segment: Mid segment
- Business Goal: Cross-service authentication reliability
- Value Impact: $15K MRR - Token propagation failures break cross-service authentication
- Strategic Impact: Ensures JWT tokens are correctly shared between backend, auth-service, and WebSocket

L3 Test: Real multi-service auth token propagation with containerized services.
Tests JWT token generation, Redis storage, cross-service validation, and WebSocket authentication.
"""

# Test framework import - using pytest fixtures instead

import sys
from pathlib import Path

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from netra_backend.app.logging_config import central_logger

from netra_backend.tests.integration.helpers.redis_l3_helpers import RedisContainer
from netra_backend.tests.integration.helpers.multi_service_auth_helpers import (

    PostgreSQLContainer, AuthServiceSimulator, 
    BackendServiceSimulator, WebSocketServiceSimulator
)

logger = central_logger.get_logger(__name__)

class MultiServiceAuthManager:
    """Manages multi-service authentication testing scenarios."""
    
    def __init__(self, auth_service: AuthServiceSimulator, redis_client, postgres_session):
        self.auth_service = auth_service
        self.redis_client = redis_client
        self.postgres_session = postgres_session
        self.backend_simulator = BackendServiceSimulator(redis_client)
        self.websocket_simulator = WebSocketServiceSimulator(redis_client)
        self.test_tokens = {}
        self.service_interactions = []
    
    async def generate_token_via_auth_service(self, user_id: str, 
                                            credentials: Dict[str, str]) -> Dict[str, Any]:
        """Generate JWT token through auth service."""
        try:
            # Use auth service simulator
            result = await self.auth_service.generate_token(user_id, credentials)
            
            if result.get("success"):
                token = result["token"]
                self.test_tokens[user_id] = token
                
                self.service_interactions.append({
                    "service": "auth_service",
                    "action": "generate_token",
                    "user_id": user_id,
                    "success": True,
                    "timestamp": time.time()
                })
                
                return {"success": True, "token": token, "user_id": user_id}
            else:
                return {"success": False, "error": result.get("error", "Unknown error")}
                    
        except Exception as e:
            self.service_interactions.append({
                "service": "auth_service",
                "action": "generate_token",
                "user_id": user_id,
                "success": False,
                "error": str(e),
                "timestamp": time.time()
            })
            return {"success": False, "error": f"Auth service error: {str(e)}"}
    
    async def validate_token_across_services(self, token: str) -> Dict[str, Any]:
        """Validate token across all services."""
        validation_results = {
            "token": token,
            "backend_validation": None,
            "websocket_authentication": None,
            "redis_storage": None,
            "overall_success": False
        }
        
        try:
            # Test 1: Backend service validation
            backend_result = await self.backend_simulator.validate_token_from_redis(token)
            validation_results["backend_validation"] = backend_result
            
            self.service_interactions.append({
                "service": "backend",
                "action": "validate_token",
                "token": token,
                "success": backend_result["valid"],
                "timestamp": time.time()
            })
            
            # Test 2: WebSocket service authentication
            ws_result = await self.websocket_simulator.authenticate_websocket(token)
            validation_results["websocket_authentication"] = ws_result
            
            self.service_interactions.append({
                "service": "websocket",
                "action": "authenticate",
                "token": token,
                "success": ws_result["authenticated"],
                "timestamp": time.time()
            })
            
            # Test 3: Direct Redis storage check
            redis_check = await self._verify_token_in_redis(token)
            validation_results["redis_storage"] = redis_check
            
            # Overall success
            validation_results["overall_success"] = (
                backend_result["valid"] and 
                ws_result["authenticated"] and 
                redis_check["exists"]
            )
            
            return validation_results
            
        except Exception as e:
            validation_results["error"] = str(e)
            return validation_results
    
    async def test_token_invalidation_propagation(self, token: str) -> Dict[str, Any]:
        """Test token invalidation across all services."""
        try:
            # Invalidate token in Redis
            token_key = f"jwt_token:{token}"
            await self.redis_client.delete(token_key)
            
            self.service_interactions.append({
                "service": "redis",
                "action": "invalidate_token",
                "token": token,
                "success": True,
                "timestamp": time.time()
            })
            
            # Wait briefly for propagation
            await asyncio.sleep(0.1)
            
            # Test that all services now reject the token
            backend_validation = await self.backend_simulator.validate_token_from_redis(token)
            ws_auth = await self.websocket_simulator.authenticate_websocket(token)
            redis_check = await self._verify_token_in_redis(token)
            
            invalidation_success = (
                not backend_validation["valid"] and
                not ws_auth["authenticated"] and
                not redis_check["exists"]
            )
            
            return {
                "invalidation_success": invalidation_success,
                "backend_rejects": not backend_validation["valid"],
                "websocket_rejects": not ws_auth["authenticated"],
                "redis_cleared": not redis_check["exists"],
                "backend_result": backend_validation,
                "websocket_result": ws_auth,
                "redis_result": redis_check
            }
            
        except Exception as e:
            return {"invalidation_success": False, "error": str(e)}
    
    async def test_concurrent_token_access(self, token: str, concurrent_requests: int = 10) -> Dict[str, Any]:
        """Test concurrent token access across services."""
        try:
            # Create concurrent validation tasks
            backend_tasks = [
                self.backend_simulator.validate_token_from_redis(token)
                for _ in range(concurrent_requests)
            ]
            
            ws_tasks = [
                self.websocket_simulator.authenticate_websocket(token)
                for _ in range(concurrent_requests)
            ]
            
            # Execute concurrently
            start_time = time.time()
            backend_results = await asyncio.gather(*backend_tasks, return_exceptions=True)
            ws_results = await asyncio.gather(*ws_tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            backend_successes = sum(1 for r in backend_results 
                                  if not isinstance(r, Exception) and r.get("valid"))
            ws_successes = sum(1 for r in ws_results 
                             if not isinstance(r, Exception) and r.get("authenticated"))
            
            return {
                "concurrent_requests": concurrent_requests,
                "backend_successes": backend_successes,
                "websocket_successes": ws_successes,
                "total_duration": end_time - start_time,
                "avg_response_time": (end_time - start_time) / (concurrent_requests * 2),
                "all_backend_succeeded": backend_successes == concurrent_requests,
                "all_websocket_succeeded": ws_successes == concurrent_requests,
                "backend_results": backend_results,
                "websocket_results": ws_results
            }
            
        except Exception as e:
            return {"concurrent_test_success": False, "error": str(e)}
    
    async def _verify_token_in_redis(self, token: str) -> Dict[str, Any]:
        """Verify token exists in Redis."""
        try:
            token_key = f"jwt_token:{token}"
            token_data = await self.redis_client.get(token_key)
            
            if token_data:
                return {"exists": True, "data": json.loads(token_data)}
            else:
                return {"exists": False, "data": None}
                
        except Exception as e:
            return {"exists": False, "error": str(e)}

@pytest.mark.L3
@pytest.mark.integration
class TestMultiServiceAuthTokenPropagationL3:
    """L3 integration test for multi-service authentication token propagation."""
    
    @pytest.fixture
    async def postgres_container(self):
        """Set up PostgreSQL container."""
        container = PostgreSQLContainer()
        database_url = await container.start()
        yield container, database_url
        await container.stop()
    
    @pytest.fixture
    async def redis_container(self):
        """Set up Redis container."""
        container = RedisContainer()
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def auth_service_simulator(self, redis_client):
        """Set up auth service simulator."""
        simulator = AuthServiceSimulator(redis_client)
        service_url = await simulator.start()
        yield simulator, service_url
        await simulator.stop()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        yield client
        await client.close()
    
    @pytest.fixture
    async def postgres_session(self, postgres_container):
        """Create PostgreSQL session."""
        _, database_url = postgres_container
        
        engine = create_async_engine(database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        session = async_session()
        yield session
        await session.close()
        await engine.dispose()
    
    @pytest.fixture
    async def auth_manager(self, auth_service_simulator, redis_client, postgres_session):
        """Create multi-service auth manager."""
        simulator, _ = auth_service_simulator
        manager = MultiServiceAuthManager(simulator, redis_client, postgres_session)
        yield manager
    
    async def test_jwt_token_generation_and_storage(self, auth_manager, redis_client):
        """Test JWT token generation through auth service and Redis storage."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        token_result = await auth_manager.generate_token_via_auth_service(user_id, {"password": "test"})
        assert token_result["success"] is True
        token_data = await redis_client.get(f"jwt_token:{token_result['token']}")
        assert json.loads(token_data)["user_id"] == user_id
        logger.info(f"Token generated successfully for user {user_id}")
    
    async def test_cross_service_token_validation(self, auth_manager):
        """Test token validation across backend and WebSocket services."""
        user_id = f"validation_user_{uuid.uuid4().hex[:8]}"
        token_result = await auth_manager.generate_token_via_auth_service(user_id, {"password": "test"})
        validation_results = await auth_manager.validate_token_across_services(token_result["token"])
        assert validation_results["overall_success"] is True
        assert validation_results["backend_validation"]["valid"] is True
        logger.info(f"Cross-service validation successful")
    
    async def test_token_invalidation_propagation(self, auth_manager):
        """Test token invalidation propagates to all services."""
        user_id = f"invalidation_user_{uuid.uuid4().hex[:8]}"
        token_result = await auth_manager.generate_token_via_auth_service(user_id, {"password": "test"})
        initial_validation = await auth_manager.validate_token_across_services(token_result["token"])
        assert initial_validation["overall_success"] is True
        invalidation_result = await auth_manager.test_token_invalidation_propagation(token_result["token"])
        assert invalidation_result["invalidation_success"] is True
    
    async def test_concurrent_token_access_across_services(self, auth_manager):
        """Test concurrent token access from multiple services."""
        user_id = f"concurrent_user_{uuid.uuid4().hex[:8]}"
        token_result = await auth_manager.generate_token_via_auth_service(user_id, {"password": "test"})
        concurrent_result = await auth_manager.test_concurrent_token_access(token_result["token"], 8)
        assert concurrent_result["all_backend_succeeded"] is True
        assert concurrent_result["all_websocket_succeeded"] is True
        assert concurrent_result["total_duration"] < 5.0
    
    async def test_websocket_message_flow_with_auth(self, auth_manager):
        """Test WebSocket message flow with authenticated token."""
        user_id = f"websocket_user_{uuid.uuid4().hex[:8]}"
        token_result = await auth_manager.generate_token_via_auth_service(user_id, {"password": "test"})
        ws_auth = await auth_manager.websocket_simulator.authenticate_websocket(token_result["token"])
        assert ws_auth["authenticated"] is True
        success = await auth_manager.websocket_simulator.send_message_to_user(user_id, {"type": "test"})
        assert success is True and len(ws_auth["websocket"].messages) > 0
    
    async def test_service_interaction_tracking(self, auth_manager):
        """Test tracking of interactions across services."""
        user_id = f"tracking_user_{uuid.uuid4().hex[:8]}"
        token_result = await auth_manager.generate_token_via_auth_service(user_id, {"password": "test"})
        await auth_manager.validate_token_across_services(token_result["token"])
        await auth_manager.test_token_invalidation_propagation(token_result["token"])
        interactions = auth_manager.service_interactions
        assert len(interactions) >= 4 and len({i["service"] for i in interactions}) >= 3
    
    async def test_token_expiry_handling_across_services(self, auth_manager, redis_client):
        """Test token expiry handling across all services."""
        user_id = f"expiry_user_{uuid.uuid4().hex[:8]}"
        token_result = await auth_manager.generate_token_via_auth_service(user_id, {"password": "test"})
        expired_data = {"user_id": user_id, "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
        await redis_client.set(f"jwt_token:{token_result['token']}", json.dumps(expired_data), ex=3600)
        validation_results = await auth_manager.validate_token_across_services(token_result["token"])
        assert validation_results["overall_success"] is False

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])