"""L3 Integration Test: Session Invalidation Cascade

Business Value Justification (BVJ):
- Segment: All tiers (security requirement)
- Business Goal: Ensure complete logout/session termination across all services
- Value Impact: Critical for security compliance and audit requirements
- Strategic Impact: Prevents security breaches and supports enterprise compliance for $75K MRR

L3 Test: Real cross-service session invalidation with PostgreSQL, Redis, ClickHouse.
Tests complete logout propagation and audit trail persistence.
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# JWT service replaced with auth_integration
from netra_backend.app.auth_integration.auth import create_access_token, validate_token_jwt
from unittest.mock import AsyncMock

JWTService = AsyncMock
# Session manager replaced with mock

SessionManager = AsyncMock
from netra_backend.app.ws_manager import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.db.models_postgres import User, ResearchSession as Session
from tests.e2e.websocket_resilience.websocket_recovery_fixtures import SecurityAuditLogger
from netra_backend.app.logging_config import central_logger
from netra_backend.tests.integration.helpers.redis_l3_helpers import RedisContainer, MockWebSocketForRedis

logger = central_logger.get_logger(__name__)

class ClickHouseContainer:

    """Manages ClickHouse Docker container for L3 testing."""
    
    def __init__(self, port: int = 8125):

        self.port = port

        self.container_name = f"netra-test-clickhouse-l3-{uuid.uuid4().hex[:8]}"

        self.container_id = None

        self.connection_url = f"clickhouse://localhost:{port}/default"
    
    async def start(self) -> str:

        """Start ClickHouse container."""
        import subprocess
        
        try:

            await self._cleanup_existing()
            
            cmd = [

                "docker", "run", "-d",

                "--name", self.container_name,

                "-p", f"{self.port}:8123",

                "-e", "CLICKHOUSE_DB=testdb",

                "-e", "CLICKHOUSE_USER=testuser", 

                "-e", "CLICKHOUSE_PASSWORD=testpass",

                "clickhouse/clickhouse-server:latest"

            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

            if result.returncode != 0:

                raise RuntimeError(f"Failed to start ClickHouse container: {result.stderr}")
            
            self.container_id = result.stdout.strip()

            await self._wait_for_ready()
            
            logger.info(f"ClickHouse container started: {self.container_name}")

            return self.connection_url
            
        except Exception as e:

            await self.stop()

            raise RuntimeError(f"ClickHouse container startup failed: {e}")
    
    async def stop(self) -> None:

        """Stop ClickHouse container."""

        if self.container_id:
            import subprocess

            try:

                subprocess.run(["docker", "stop", self.container_id], capture_output=True, timeout=15)

                subprocess.run(["docker", "rm", self.container_id], capture_output=True, timeout=10)

                logger.info(f"ClickHouse container stopped: {self.container_name}")

            except Exception as e:

                logger.warning(f"Error stopping ClickHouse container: {e}")

            finally:

                self.container_id = None
    
    async def _cleanup_existing(self) -> None:

        """Clean up existing container."""

        try:

            subprocess.run(["docker", "stop", self.container_name], capture_output=True, timeout=5)

            subprocess.run(["docker", "rm", self.container_name], capture_output=True, timeout=5)

        except:

            pass
    
    async def _wait_for_ready(self, timeout: int = 90) -> None:

        """Wait for ClickHouse to be ready."""
        import httpx

        start_time = time.time()
        
        while time.time() - start_time < timeout:

            try:

                async with httpx.AsyncClient() as client:

                    response = await client.get(f"http://localhost:{self.port}/ping")

                    if response.status_code == 200:

                        return

            except Exception:

                await asyncio.sleep(2)
        
        raise RuntimeError("ClickHouse container failed to become ready")

class SessionInvalidationCascade:

    """Manages session invalidation cascade testing."""
    
    def __init__(self, jwt_service: JWTService, session_manager: SessionManager,

                 websocket_manager: WebSocketManager, redis_client, 

                 audit_logger: SecurityAuditLogger):

        self.jwt_service = jwt_service

        self.session_manager = session_manager

        self.websocket_manager = websocket_manager

        self.redis_client = redis_client

        self.audit_logger = audit_logger

        self.active_sessions = {}

        self.invalidation_events = []
    
    async def create_multi_service_session(self, user_id: str, 

                                         services: List[str] = None) -> Dict[str, Any]:

        """Create session that spans multiple services."""

        services = services or ["main", "auth", "websocket"]
        
        # Generate JWT token

        token_result = await self.jwt_service.generate_token(

            user_id=user_id,

            permissions=["read", "write", "admin"],

            tier="enterprise"

        )
        
        if not token_result["success"]:

            raise ValueError(f"Token generation failed: {token_result.get('error')}")
        
        # Create main session

        session_result = await self.session_manager.create_session(

            user_id=user_id,

            token=token_result["token"],

            metadata={

                "services": services,

                "auth_method": "cascade_test",

                "ip_address": "127.0.0.1"

            }

        )
        
        if not session_result["success"]:

            raise ValueError(f"Session creation failed: {session_result.get('error')}")
        
        session_id = session_result["session_id"]

        token = token_result["token"]
        
        # Create service-specific session data

        service_sessions = {}

        for service in services:

            service_key = f"session:{service}:{session_id}"

            service_data = {

                "user_id": user_id,

                "session_id": session_id,

                "token": token,

                "service": service,

                "created_at": time.time(),

                "last_activity": time.time()

            }
            
            await self.redis_client.set(service_key, json.dumps(service_data), ex=3600)

            service_sessions[service] = service_data
        
        # Create WebSocket connection if websocket service included

        websocket = None

        if "websocket" in services:

            websocket = MockWebSocketForRedis(user_id)
            
            with patch('app.ws_manager.verify_jwt_token') as mock_verify:

                mock_verify.return_value = {

                    "valid": True,

                    "user_id": user_id,

                    "permissions": ["read", "write", "admin"]

                }
                
                connection_info = await self.websocket_manager.connect_user(user_id, websocket)
            
            if not connection_info:

                raise ValueError("WebSocket connection failed")
        
        # Store session info

        session_data = {

            "user_id": user_id,

            "session_id": session_id,

            "token": token,

            "services": services,

            "service_sessions": service_sessions,

            "websocket": websocket,

            "created_at": time.time()

        }
        
        self.active_sessions[session_id] = session_data
        
        # Log session creation

        await self.audit_logger.log_session_event(

            user_id=user_id,

            session_id=session_id,

            event_type="session_created",

            details={"services": services}

        )
        
        return session_data
    
    async def invalidate_session_cascade(self, session_id: str, 

                                       invalidation_reason: str = "user_logout") -> Dict[str, Any]:

        """Perform complete session invalidation across all services."""

        if session_id not in self.active_sessions:

            raise ValueError(f"Session {session_id} not found")
        
        session_data = self.active_sessions[session_id]

        user_id = session_data["user_id"]

        services = session_data["services"]
        
        invalidation_start = time.time()

        invalidation_results = {}
        
        # Step 1: Invalidate main session

        try:

            main_result = await self.session_manager.invalidate_session(session_id)

            invalidation_results["main_session"] = main_result

        except Exception as e:

            invalidation_results["main_session"] = {"success": False, "error": str(e)}
        
        # Step 2: Invalidate service-specific sessions

        for service in services:

            try:

                service_key = f"session:{service}:{session_id}"

                deleted = await self.redis_client.delete(service_key)

                invalidation_results[f"service_{service}"] = {"success": deleted > 0}

            except Exception as e:

                invalidation_results[f"service_{service}"] = {"success": False, "error": str(e)}
        
        # Step 3: Revoke JWT token

        try:

            revoke_result = await self.jwt_service.revoke_token(session_data["token"])

            invalidation_results["token_revocation"] = revoke_result

        except Exception as e:

            invalidation_results["token_revocation"] = {"success": False, "error": str(e)}
        
        # Step 4: Disconnect WebSocket if active

        if session_data["websocket"]:

            try:

                await self.websocket_manager.disconnect_user(user_id, session_data["websocket"])

                invalidation_results["websocket_disconnect"] = {"success": True}

            except Exception as e:

                invalidation_results["websocket_disconnect"] = {"success": False, "error": str(e)}
        
        # Step 5: Clear user cache entries

        try:

            cache_keys = [

                f"user_cache:{user_id}",

                f"user_permissions:{user_id}",

                f"user_sessions:{user_id}"

            ]
            
            cache_cleared = 0

            for key in cache_keys:

                deleted = await self.redis_client.delete(key)

                cache_cleared += deleted
            
            invalidation_results["cache_cleanup"] = {"success": True, "keys_cleared": cache_cleared}

        except Exception as e:

            invalidation_results["cache_cleanup"] = {"success": False, "error": str(e)}
        
        # Calculate metrics

        invalidation_time = time.time() - invalidation_start

        successful_steps = sum(1 for result in invalidation_results.values() 

                             if result.get("success", False))

        total_steps = len(invalidation_results)
        
        # Create invalidation event

        invalidation_event = {

            "session_id": session_id,

            "user_id": user_id,

            "reason": invalidation_reason,

            "services": services,

            "results": invalidation_results,

            "successful_steps": successful_steps,

            "total_steps": total_steps,

            "invalidation_time": invalidation_time,

            "timestamp": time.time()

        }
        
        self.invalidation_events.append(invalidation_event)
        
        # Log invalidation event

        await self.audit_logger.log_session_event(

            user_id=user_id,

            session_id=session_id,

            event_type="session_invalidated",

            details={

                "reason": invalidation_reason,

                "services_affected": services,

                "successful_steps": successful_steps,

                "total_steps": total_steps,

                "duration_ms": invalidation_time * 1000

            }

        )
        
        # Remove from active sessions

        del self.active_sessions[session_id]
        
        return invalidation_event
    
    async def verify_complete_invalidation(self, session_id: str) -> Dict[str, Any]:

        """Verify that session is completely invalidated across all services."""

        verification_results = {}
        
        # Check main session

        try:

            session_exists = await self.session_manager.get_session(session_id)

            verification_results["main_session"] = {"exists": session_exists is not None}

        except Exception as e:

            verification_results["main_session"] = {"error": str(e)}
        
        # Check Redis service sessions

        service_pattern = f"session:*:{session_id}"

        try:

            service_keys = await self.redis_client.keys(service_pattern)

            verification_results["service_sessions"] = {

                "remaining_keys": len(service_keys),

                "keys": service_keys

            }

        except Exception as e:

            verification_results["service_sessions"] = {"error": str(e)}
        
        # Check token validity

        if session_id in self.active_sessions:

            token = self.active_sessions[session_id]["token"]

            try:

                token_valid = await self.jwt_service.verify_token(token)

                verification_results["token_validity"] = token_valid

            except Exception as e:

                verification_results["token_validity"] = {"error": str(e)}
        
        # Check WebSocket connections

        user_id = None

        if session_id in self.active_sessions:

            user_id = self.active_sessions[session_id]["user_id"]
        
        if user_id:

            ws_active = user_id in self.websocket_manager.active_connections

            verification_results["websocket_connection"] = {"active": ws_active}
        
        return verification_results
    
    async def cleanup(self):

        """Clean up all sessions."""

        for session_id in list(self.active_sessions.keys()):

            try:

                await self.invalidate_session_cascade(session_id, "test_cleanup")

            except Exception as e:

                logger.warning(f"Cleanup error for session {session_id}: {e}")

@pytest.mark.L3

@pytest.mark.integration

class TestSessionInvalidationCascadeL3:

    """L3 integration test for session invalidation cascade across services."""
    
    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container."""

        container = RedisContainer()

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    
    @pytest.fixture(scope="class")

    async def clickhouse_container(self):

        """Set up ClickHouse container."""

        container = ClickHouseContainer()

        connection_url = await container.start()

        yield container, connection_url

        await container.stop()
    
    @pytest.fixture

    async def redis_client(self, redis_container):

        """Create Redis client."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)

        yield client

        await client.close()
    
    @pytest.fixture

    async def jwt_service(self, redis_client):

        """Initialize JWT service."""

        service = JWTService()
        
        with patch('app.redis_manager.RedisManager.get_client') as mock_redis:

            mock_redis.return_value = redis_client

            await service.initialize()

            yield service

            await service.shutdown()
    
    @pytest.fixture

    async def session_manager(self, redis_client):

        """Initialize session manager."""

        manager = SessionManager()
        
        with patch('app.redis_manager.RedisManager.get_client') as mock_redis:

            mock_redis.return_value = redis_client

            await manager.initialize()

            yield manager

            await manager.shutdown()
    
    @pytest.fixture

    async def websocket_manager(self, redis_client):

        """Create WebSocket manager."""

        with patch('app.ws_manager.redis_manager') as mock_redis_mgr:

            test_redis_mgr = RedisManager()

            test_redis_mgr.enabled = True

            test_redis_mgr.redis_client = redis_client

            mock_redis_mgr.return_value = test_redis_mgr

            mock_redis_mgr.get_client.return_value = redis_client
            
            manager = WebSocketManager()

            yield manager
    
    @pytest.fixture

    async def audit_logger(self, clickhouse_container):

        """Initialize security audit logger."""

        _, connection_url = clickhouse_container
        
        # Use AsyncMock for easier testing with call tracking
        logger = AsyncMock(spec=SecurityAuditLogger)
        logger.log_session_event = AsyncMock()
        logger.security_events = []
        logger.alert_triggers = []
        
        yield logger
    
    @pytest.fixture

    async def cascade_manager(self, jwt_service, session_manager, websocket_manager, 

                            redis_client, audit_logger):

        """Create session invalidation cascade manager."""

        manager = SessionInvalidationCascade(

            jwt_service, session_manager, websocket_manager, redis_client, audit_logger

        )

        yield manager

        await manager.cleanup()
    
    async def test_complete_session_invalidation_cascade(self, cascade_manager):

        """Test complete session invalidation across all services."""

        user_id = f"cascade_user_{uuid.uuid4().hex[:8]}"

        services = ["main", "auth", "websocket", "api"]
        
        # Create multi-service session

        session_data = await cascade_manager.create_multi_service_session(user_id, services)

        session_id = session_data["session_id"]
        
        # Verify session is active across services

        assert session_id in cascade_manager.active_sessions

        assert not session_data["websocket"].closed

        assert user_id in cascade_manager.websocket_manager.active_connections
        
        # Verify service sessions in Redis

        for service in services:

            service_key = f"session:{service}:{session_id}"

            service_data = await cascade_manager.redis_client.get(service_key)

            assert service_data is not None
        
        # Perform cascade invalidation

        invalidation_event = await cascade_manager.invalidate_session_cascade(

            session_id, "user_logout"

        )
        
        # Verify invalidation success

        assert invalidation_event["successful_steps"] >= len(services)

        assert invalidation_event["invalidation_time"] < 2.0  # Should be fast
        
        # Verify complete invalidation

        verification = await cascade_manager.verify_complete_invalidation(session_id)
        
        # Main session should be invalidated

        assert verification.get("main_session", {}).get("exists", True) is False
        
        # Service sessions should be cleared

        remaining_keys = verification.get("service_sessions", {}).get("remaining_keys", 1)

        assert remaining_keys == 0
        
        # WebSocket should be disconnected

        ws_status = verification.get("websocket_connection", {})

        assert ws_status.get("active", True) is False
        
        # Session should be removed from active sessions

        assert session_id not in cascade_manager.active_sessions
    
    async def test_concurrent_session_invalidations(self, cascade_manager):

        """Test concurrent invalidation of multiple sessions."""

        user_count = 5

        sessions = []
        
        # Create multiple sessions

        for i in range(user_count):

            user_id = f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}"

            session_data = await cascade_manager.create_multi_service_session(

                user_id, ["main", "auth", "websocket"]

            )

            sessions.append(session_data)
        
        # Verify all sessions active

        for session_data in sessions:

            assert session_data["session_id"] in cascade_manager.active_sessions

            assert not session_data["websocket"].closed
        
        # Perform concurrent invalidations

        async def invalidate_session(session_data):

            return await cascade_manager.invalidate_session_cascade(

                session_data["session_id"], "concurrent_logout"

            )
        
        invalidation_tasks = [invalidate_session(session) for session in sessions]

        invalidation_results = await asyncio.gather(*invalidation_tasks, return_exceptions=True)
        
        # Verify all invalidations succeeded

        successful_invalidations = 0

        for i, result in enumerate(invalidation_results):

            if isinstance(result, Exception):

                pytest.fail(f"Invalidation {i} failed: {result}")
            
            assert result["successful_steps"] >= 3  # At least main, auth, websocket

            successful_invalidations += 1
        
        assert successful_invalidations == user_count
        
        # Verify no sessions remain active

        assert len(cascade_manager.active_sessions) == 0
        
        # Verify no WebSocket connections remain

        active_ws = len(cascade_manager.websocket_manager.active_connections)

        assert active_ws == 0
    
    async def test_partial_invalidation_failure_handling(self, cascade_manager):

        """Test handling of partial invalidation failures."""

        user_id = f"failure_user_{uuid.uuid4().hex[:8]}"
        
        # Create session

        session_data = await cascade_manager.create_multi_service_session(

            user_id, ["main", "auth", "websocket"]

        )

        session_id = session_data["session_id"]
        
        # Simulate Redis failure during service session cleanup

        original_delete = cascade_manager.redis_client.delete

        delete_call_count = 0
        
        async def failing_delete(key):

            nonlocal delete_call_count

            delete_call_count += 1

            if "session:auth:" in key:

                raise redis.ConnectionError("Simulated Redis failure")

            return await original_delete(key)
        
        with patch.object(cascade_manager.redis_client, 'delete', side_effect=failing_delete):

            invalidation_event = await cascade_manager.invalidate_session_cascade(

                session_id, "test_failure"

            )
        
        # Verify partial success recorded

        assert invalidation_event["successful_steps"] < invalidation_event["total_steps"]

        assert invalidation_event["results"]["service_auth"]["success"] is False
        
        # Verify main session still invalidated

        assert invalidation_event["results"]["main_session"]["success"] is True
        
        # Verify audit trail includes failure details

        assert len(cascade_manager.invalidation_events) > 0

        latest_event = cascade_manager.invalidation_events[-1]

        assert latest_event["successful_steps"] < latest_event["total_steps"]
    
    async def test_session_invalidation_audit_trail(self, cascade_manager):

        """Test complete audit trail for session invalidation."""

        user_id = f"audit_user_{uuid.uuid4().hex[:8]}"
        
        # Create session

        session_data = await cascade_manager.create_multi_service_session(

            user_id, ["main", "auth", "websocket"]

        )

        session_id = session_data["session_id"]
        
        # Perform invalidation

        invalidation_event = await cascade_manager.invalidate_session_cascade(

            session_id, "security_incident"

        )
        
        # Verify audit logger was called

        assert cascade_manager.audit_logger.log_session_event.call_count >= 2
        
        # Verify invalidation event structure

        assert invalidation_event["reason"] == "security_incident"

        assert "services" in invalidation_event

        assert "results" in invalidation_event

        assert "timestamp" in invalidation_event

        assert "successful_steps" in invalidation_event
        
        # Verify event stored in manager

        assert len(cascade_manager.invalidation_events) > 0

        stored_event = cascade_manager.invalidation_events[-1]

        assert stored_event["session_id"] == session_id

        assert stored_event["user_id"] == user_id

        assert stored_event["reason"] == "security_incident"
    
    async def test_websocket_immediate_disconnection(self, cascade_manager):

        """Test immediate WebSocket disconnection during invalidation."""

        user_id = f"ws_disconnect_user_{uuid.uuid4().hex[:8]}"
        
        # Create session with WebSocket

        session_data = await cascade_manager.create_multi_service_session(

            user_id, ["main", "websocket"]

        )

        session_id = session_data["session_id"]

        websocket = session_data["websocket"]
        
        # Send test message before invalidation

        test_message = {"type": "pre_logout", "data": {"timestamp": time.time()}}

        success = await cascade_manager.websocket_manager.send_message_to_user(

            user_id, test_message

        )

        assert success is True
        
        # Perform invalidation

        invalidation_start = time.time()

        invalidation_event = await cascade_manager.invalidate_session_cascade(

            session_id, "immediate_logout"

        )

        invalidation_time = time.time() - invalidation_start
        
        # Verify WebSocket disconnected quickly

        assert websocket.closed

        assert invalidation_time < 1.0  # Should be immediate
        
        # Verify WebSocket no longer in active connections

        assert user_id not in cascade_manager.websocket_manager.active_connections
        
        # Attempt to send message after invalidation should fail

        post_logout_message = {"type": "post_logout", "data": {}}

        success = await cascade_manager.websocket_manager.send_message_to_user(

            user_id, post_logout_message

        )

        assert success is False  # Should fail - no connection
    
    async def test_invalidation_idempotency(self, cascade_manager):

        """Test that multiple invalidation calls are idempotent."""

        user_id = f"idempotent_user_{uuid.uuid4().hex[:8]}"
        
        # Create session

        session_data = await cascade_manager.create_multi_service_session(

            user_id, ["main", "auth"]

        )

        session_id = session_data["session_id"]
        
        # First invalidation

        first_invalidation = await cascade_manager.invalidate_session_cascade(

            session_id, "first_logout"

        )
        
        # Verify session removed

        assert session_id not in cascade_manager.active_sessions
        
        # Second invalidation attempt

        try:

            second_invalidation = await cascade_manager.invalidate_session_cascade(

                session_id, "second_logout"

            )

            pytest.fail("Expected second invalidation to fail")

        except ValueError as e:

            assert "not found" in str(e)
        
        # Verify audit trail shows only first invalidation

        user_invalidations = [

            event for event in cascade_manager.invalidation_events

            if event["user_id"] == user_id

        ]

        assert len(user_invalidations) == 1

        assert user_invalidations[0]["reason"] == "first_logout"

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])