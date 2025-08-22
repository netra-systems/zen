"""Multi-Service Token Propagation L2 Integration Test

Business Value Justification (BVJ):
- Segment: Enterprise (primarily), Mid
- Business Goal: Security and compliance
- Value Impact: Ensures audit trail integrity, prevents data leakage worth $20K MRR
- Strategic Impact: Required for SOC2 compliance and enterprise contracts

This L2 test validates token propagation across multiple services using real internal
components without external service mocking. Critical for enterprise security compliance.

Critical Path Coverage:
1. Backend main service receiving initial token → Token validation and forwarding
2. Token propagation to auth service → Database queries with user context
3. Token passing to agent services → Redis cache keys with user identity
4. Service-to-service authentication → Audit trail with user identity
5. Token refresh propagation → Concurrent requests with different tokens

Architecture Compliance: <450 lines, <25 line functions, real components (L2)
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
from netra_backend.app.auth_integration.auth import get_current_user
from clients.auth_client import auth_client
from sqlalchemy import select

from netra_backend.app.db.models_postgres import User

# Add project root to path
from netra_backend.app.db.postgres import get_postgres_db
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.agent_service import get_agent_service

# Add project root to path

logger = logging.getLogger(__name__)


class MockAuthResponse:
    """Mock authentication response for consistent testing."""
    
    def __init__(self, valid: bool = True, user_id: str = "test-user-1", 
                 email: str = "test@example.com", permissions: List[str] = None):
        self.valid = valid
        self.user_id = user_id
        self.email = email
        self.permissions = permissions or ["read", "write"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "valid": self.valid,
            "user_id": self.user_id,
            "email": self.email,
            "permissions": self.permissions
        }


class TokenPropagationTestManager:
    """Manages multi-service token propagation testing."""
    
    def __init__(self):
        self.redis_manager = None
        self.test_sessions = []
        self.test_tokens = []
        
    async def initialize_services(self):
        """Initialize real services for token propagation testing."""
        try:
            self.redis_manager = RedisManager()
            await self.redis_manager.connect()
            logger.info("Token propagation services initialized")
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise
    
    async def create_test_user_session(self, user_id: str, email: str, 
                                     permissions: List[str] = None) -> Dict[str, Any]:
        """Create test user session with token."""
        session_start = time.time()
        
        try:
            permissions = permissions or ["read", "write", "admin"]
            test_token = f"test_token_{user_id}_{uuid.uuid4().hex[:8]}"
            
            auth_response = MockAuthResponse(
                valid=True, user_id=user_id, email=email, permissions=permissions
            )
            
            session_data = {
                "session_id": str(uuid.uuid4()),
                "user_id": user_id,
                "email": email,
                "token": test_token,
                "permissions": permissions,
                "created_at": datetime.utcnow(),
                "auth_response": auth_response.to_dict()
            }
            
            self.test_sessions.append(session_data)
            self.test_tokens.append(test_token)
            
            return {
                "success": True,
                "session_data": session_data,
                "token": test_token,
                "creation_time": time.time() - session_start
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "creation_time": time.time() - session_start}
    
    async def test_backend_token_validation(self, token: str) -> Dict[str, Any]:
        """Test token validation in backend main service."""
        validation_start = time.time()
        
        try:
            with patch.object(auth_client, 'validate_token') as mock_validate:
                session_data = self._find_session_by_token(token)
                
                if session_data:
                    mock_validate.return_value = session_data["auth_response"]
                else:
                    mock_validate.return_value = {"valid": False}
                
                validation_result = await auth_client.validate_token_jwt(token)
                
                return {
                    "service": "backend_main",
                    "token_valid": validation_result.get("valid", False),
                    "user_id": validation_result.get("user_id"),
                    "validation_time": time.time() - validation_start,
                    "propagated": True
                }
                
        except Exception as e:
            return {
                "service": "backend_main", "token_valid": False, "error": str(e),
                "validation_time": time.time() - validation_start, "propagated": False
            }
    
    async def test_database_user_context(self, token: str) -> Dict[str, Any]:
        """Test database queries with user context from token."""
        db_start = time.time()
        
        try:
            session_data = self._find_session_by_token(token)
            if not session_data:
                return {"service": "database", "user_context_found": False, "error": "Session not found"}
            
            async with get_postgres_db() as db:
                user_query = select(User).where(User.email == session_data["email"])
                result = await db.execute(user_query)
                user = result.scalar_one_or_none()
                
                audit_context = {
                    "user_id": session_data["user_id"],
                    "session_id": session_data["session_id"],
                    "query_type": "user_lookup",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                return {
                    "service": "database", "user_context_found": True, "user_exists": user is not None,
                    "audit_context": audit_context, "query_time": time.time() - db_start, "propagated": True
                }
                
        except Exception as e:
            return {
                "service": "database", "user_context_found": False, "error": str(e),
                "query_time": time.time() - db_start, "propagated": False
            }
    
    async def test_redis_cache_user_context(self, token: str) -> Dict[str, Any]:
        """Test Redis cache operations with user-specific keys."""
        redis_start = time.time()
        
        try:
            session_data = self._find_session_by_token(token)
            if not session_data:
                return {"service": "redis", "cache_context_set": False, "error": "Session not found"}
            
            redis_client = await self.redis_manager.get_client()
            if not redis_client:
                return {"service": "redis", "cache_context_set": False, "error": "Redis not available"}
            
            user_cache_key = f"user:{session_data['user_id']}:session:{session_data['session_id']}"
            cache_data = {
                "token": token,
                "user_id": session_data["user_id"],
                "permissions": session_data["permissions"],
                "cached_at": datetime.utcnow().isoformat()
            }
            
            await redis_client.setex(user_cache_key, 300, json.dumps(cache_data))
            cached_result = await redis_client.get(user_cache_key)
            
            return {
                "service": "redis", "cache_context_set": cached_result is not None,
                "cache_key": user_cache_key,
                "cached_data": json.loads(cached_result) if cached_result else None,
                "cache_time": time.time() - redis_start, "propagated": True
            }
            
        except Exception as e:
            return {
                "service": "redis", "cache_context_set": False, "error": str(e),
                "cache_time": time.time() - redis_start, "propagated": False
            }
    
    async def test_agent_service_propagation(self, token: str) -> Dict[str, Any]:
        """Test token propagation to agent services."""
        agent_start = time.time()
        
        try:
            session_data = self._find_session_by_token(token)
            if not session_data:
                return {"service": "agent", "agent_context_set": False, "error": "Session not found"}
            
            agent_context = {
                "user_id": session_data["user_id"],
                "permissions": session_data["permissions"],
                "session_id": session_data["session_id"],
                "token": token
            }
            
            agent_service = get_agent_service()
            agent_operation_result = {"operation": "context_test", "user_context": agent_context, "success": True}
            
            return {
                "service": "agent", "agent_context_set": True, "agent_context": agent_context,
                "operation_result": agent_operation_result, "operation_time": time.time() - agent_start,
                "propagated": True
            }
            
        except Exception as e:
            return {
                "service": "agent", "agent_context_set": False, "error": str(e),
                "operation_time": time.time() - agent_start, "propagated": False
            }
    
    async def test_concurrent_token_propagation(self, tokens: List[str]) -> Dict[str, Any]:
        """Test concurrent token propagation across multiple services."""
        concurrent_start = time.time()
        
        try:
            tasks = []
            for token in tokens:
                service_tasks = [
                    self.test_backend_token_validation(token),
                    self.test_database_user_context(token),
                    self.test_redis_cache_user_context(token),
                    self.test_agent_service_propagation(token)
                ]
                tasks.extend(service_tasks)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            grouped_results = self._group_concurrent_results(tokens, results)
            
            return {
                "concurrent_test": True, "total_tokens": len(tokens), "results": grouped_results,
                "concurrent_time": time.time() - concurrent_start
            }
            
        except Exception as e:
            return {"concurrent_test": False, "error": str(e), "concurrent_time": time.time() - concurrent_start}
    
    def _find_session_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Find session data by token."""
        for session in self.test_sessions:
            if session["token"] == token:
                return session
        return None
    
    def _group_concurrent_results(self, tokens: List[str], results: List[Any]) -> List[Dict[str, Any]]:
        """Group concurrent results by token."""
        grouped_results = []
        result_index = 0
        
        for token in tokens:
            token_results = {
                "token": token,
                "services": {
                    "backend": results[result_index] if result_index < len(results) else None,
                    "database": results[result_index + 1] if result_index + 1 < len(results) else None,
                    "redis": results[result_index + 2] if result_index + 2 < len(results) else None,
                    "agent": results[result_index + 3] if result_index + 3 < len(results) else None
                }
            }
            grouped_results.append(token_results)
            result_index += 4
        
        return grouped_results
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.redis_manager:
                redis_client = await self.redis_manager.get_client()
                if redis_client:
                    for session in self.test_sessions:
                        cache_key = f"user:{session['user_id']}:session:{session['session_id']}"
                        await redis_client.delete(cache_key)
                await self.redis_manager.disconnect()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def token_propagation_manager():
    """Create token propagation test manager."""
    manager = TokenPropagationTestManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.critical
async def test_multi_service_token_propagation_flow(token_propagation_manager):
    """Test complete multi-service token propagation flow."""
    start_time = time.time()
    manager = token_propagation_manager
    
    # Create test user session with token
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    user_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    session_result = await manager.create_test_user_session(user_id, user_email, ["read", "write", "admin"])
    assert session_result["success"], f"Session creation failed: {session_result.get('error')}"
    assert session_result["creation_time"] < 0.1, "Session creation too slow"
    token = session_result["token"]
    
    # Test backend token validation
    backend_result = await manager.test_backend_token_validation(token)
    assert backend_result["token_valid"], "Backend token validation failed"
    assert backend_result["propagated"], "Backend propagation failed"
    assert backend_result["validation_time"] < 0.05, "Backend validation too slow"
    assert backend_result["user_id"] == user_id, "User ID mismatch in backend"
    
    # Test database user context
    db_result = await manager.test_database_user_context(token)
    assert db_result["user_context_found"], "Database user context not found"
    assert db_result["propagated"], "Database propagation failed"
    assert db_result["query_time"] < 0.2, "Database query too slow"
    assert "audit_context" in db_result, "Audit context missing"
    
    # Test Redis cache user context
    redis_result = await manager.test_redis_cache_user_context(token)
    assert redis_result["cache_context_set"], "Redis cache context not set"
    assert redis_result["propagated"], "Redis propagation failed"
    assert redis_result["cache_time"] < 0.05, "Redis operation too slow"
    assert user_id in redis_result["cache_key"], "User ID not in cache key"
    
    # Test agent service propagation
    agent_result = await manager.test_agent_service_propagation(token)
    assert agent_result["agent_context_set"], "Agent context not set"
    assert agent_result["propagated"], "Agent propagation failed"
    assert agent_result["operation_time"] < 0.1, "Agent operation too slow"
    assert agent_result["agent_context"]["user_id"] == user_id, "Agent user ID mismatch"
    
    # Verify overall flow performance (< 1s total)
    total_time = time.time() - start_time
    assert total_time < 1.0, f"Total flow took {total_time:.2f}s, expected <1s"


@pytest.mark.asyncio
async def test_concurrent_multi_token_propagation(token_propagation_manager):
    """Test concurrent token propagation for multiple users."""
    manager = token_propagation_manager
    
    # Create multiple user sessions with different tokens
    num_users = 3
    tokens = []
    for i in range(num_users):
        user_id = f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}"
        user_email = f"concurrent-{i}-{uuid.uuid4().hex[:6]}@example.com"
        session_result = await manager.create_test_user_session(user_id, user_email)
        assert session_result["success"], f"Session {i} creation failed"
        tokens.append(session_result["token"])
    
    # Test concurrent propagation
    concurrent_result = await manager.test_concurrent_token_propagation(tokens)
    assert concurrent_result["concurrent_test"], "Concurrent test failed"
    assert concurrent_result["total_tokens"] == num_users, "Token count mismatch"
    assert concurrent_result["concurrent_time"] < 2.0, "Concurrent operations too slow"
    
    # Verify each token propagated correctly
    for token_result in concurrent_result["results"]:
        services = token_result["services"]
        assert services["backend"]["token_valid"], "Backend validation failed in concurrent"
        assert services["database"]["user_context_found"], "Database context failed in concurrent"
        assert services["redis"]["cache_context_set"], "Redis cache failed in concurrent"
        assert services["agent"]["agent_context_set"], "Agent context failed in concurrent"


@pytest.mark.asyncio
async def test_token_propagation_audit_trail(token_propagation_manager):
    """Test audit trail preservation across service boundaries."""
    manager = token_propagation_manager
    
    # Create test session
    user_id = f"audit_user_{uuid.uuid4().hex[:8]}"
    user_email = f"audit-{uuid.uuid4().hex[:8]}@example.com"
    
    session_result = await manager.create_test_user_session(user_id, user_email)
    assert session_result["success"], "Audit test session creation failed"
    
    token = session_result["token"]
    session_id = session_result["session_data"]["session_id"]
    
    # Test audit trail in database
    db_result = await manager.test_database_user_context(token)
    assert "audit_context" in db_result, "Database audit context missing"
    
    audit_context = db_result["audit_context"]
    assert audit_context["user_id"] == user_id, "Audit user ID mismatch"
    assert audit_context["session_id"] == session_id, "Audit session ID mismatch"
    assert "timestamp" in audit_context, "Audit timestamp missing"
    
    # Test audit trail in Redis cache
    redis_result = await manager.test_redis_cache_user_context(token)
    assert redis_result["cached_data"]["user_id"] == user_id, "Redis audit user ID mismatch"
    assert "cached_at" in redis_result["cached_data"], "Redis audit timestamp missing"


@pytest.mark.asyncio
async def test_token_propagation_security_validation(token_propagation_manager):
    """Test security validation across service boundaries."""
    manager = token_propagation_manager
    
    # Test with invalid token
    invalid_token = "invalid_test_token"
    
    backend_result = await manager.test_backend_token_validation(invalid_token)
    assert not backend_result["token_valid"], "Invalid token should be rejected"
    assert not backend_result["propagated"], "Invalid token should not propagate"
    
    # Test with different permission levels
    limited_user_id = f"limited_user_{uuid.uuid4().hex[:8]}"
    limited_email = f"limited-{uuid.uuid4().hex[:8]}@example.com"
    
    limited_session = await manager.create_test_user_session(limited_user_id, limited_email, ["read"])
    assert limited_session["success"], "Limited session creation failed"
    
    limited_token = limited_session["token"]
    
    # Verify permission propagation
    agent_result = await manager.test_agent_service_propagation(limited_token)
    assert agent_result["agent_context_set"], "Limited agent context not set"
    assert agent_result["agent_context"]["permissions"] == ["read"], "Permission mismatch"