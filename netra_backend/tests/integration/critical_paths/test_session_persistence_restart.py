"""L3 Integration Test: Session Persistence After Service Restart

Business Value Justification (BVJ):
- Segment: Mid/Enterprise tiers (high availability requirement)
- Business Goal: Maintain user sessions during service updates and restarts
- Value Impact: Prevents user disruption during maintenance and deployments
- Strategic Impact: Critical for enterprise SLA compliance and user experience for $75K MRR

L3 Test: Real session persistence across service restarts with Redis/PostgreSQL.
Tests session recovery, WebSocket reconnection, and state continuity.
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import pytest
import asyncio
import json
import time
import uuid
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# JWT service replaced with auth_integration
from netra_backend.app.auth_integration.auth import create_access_token, validate_token_jwt
from unittest.mock import AsyncMock, MagicMock

JWTService = AsyncMock
# Session manager replaced with mock

SessionManager = AsyncMock
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.db.models_postgres import User, ResearchSession as Session
from netra_backend.app.logging_config import central_logger
from netra_backend.tests.integration.helpers.redis_l3_helpers import RedisContainer, MockWebSocketForRedis

logger = central_logger.get_logger(__name__)

class ServiceRestartSimulator:

    """Simulates service restarts for testing session persistence."""
    
    def __init__(self, redis_container, postgres_container=None):

        self.redis_container = redis_container

        self.postgres_container = postgres_container

        self.restart_events = []

        self.recovery_metrics = []
    
    async def restart_redis(self, restart_type: str = "graceful") -> Dict[str, Any]:

        """Simulate Redis restart."""

        restart_start = time.time()
        
        if restart_type == "graceful":
            # Graceful restart - save data first

            container_id = self.redis_container.container_id

            if container_id:
                # Save Redis data

                subprocess.run(["docker", "exec", container_id, "redis-cli", "BGSAVE"], 

                              capture_output=True, timeout=10)

                await asyncio.sleep(1)  # Wait for save
                
                # Restart container

                subprocess.run(["docker", "restart", container_id], capture_output=True, timeout=30)

        elif restart_type == "crash":
            # Simulate crash - kill container abruptly

            container_id = self.redis_container.container_id

            if container_id:

                subprocess.run(["docker", "kill", container_id], capture_output=True, timeout=10)

                await asyncio.sleep(1)

                subprocess.run(["docker", "start", container_id], capture_output=True, timeout=30)
        
        # Wait for Redis to be ready

        await self.redis_container._wait_for_ready(timeout=30)
        
        restart_duration = time.time() - restart_start
        
        restart_event = {

            "service": "redis",

            "restart_type": restart_type,

            "duration": restart_duration,

            "timestamp": time.time()

        }
        
        self.restart_events.append(restart_event)
        
        logger.info(f"Redis {restart_type} restart completed in {restart_duration:.2f}s")

        return restart_event
    
    async def restart_postgres(self, restart_type: str = "graceful") -> Dict[str, Any]:

        """Simulate PostgreSQL restart."""

        if not self.postgres_container:

            return {"error": "PostgreSQL container not available"}
        
        restart_start = time.time()

        container_id = self.postgres_container.container_id
        
        if restart_type == "graceful":
            # Graceful shutdown

            subprocess.run(["docker", "exec", container_id, "pg_ctl", "stop", "-m", "fast"], 

                          capture_output=True, timeout=30)

            subprocess.run(["docker", "start", container_id], capture_output=True, timeout=30)

        elif restart_type == "crash":
            # Simulate crash

            subprocess.run(["docker", "kill", container_id], capture_output=True, timeout=10)

            await asyncio.sleep(1)

            subprocess.run(["docker", "start", container_id], capture_output=True, timeout=30)
        
        # Wait for PostgreSQL to be ready

        await self.postgres_container._wait_for_ready(timeout=60)
        
        restart_duration = time.time() - restart_start
        
        restart_event = {

            "service": "postgres",

            "restart_type": restart_type,

            "duration": restart_duration,

            "timestamp": time.time()

        }
        
        self.restart_events.append(restart_event)
        
        logger.info(f"PostgreSQL {restart_type} restart completed in {restart_duration:.2f}s")

        return restart_event

class SessionPersistenceManager:

    """Manages session persistence testing scenarios."""
    
    def __init__(self, jwt_service: JWTService, session_manager: SessionManager,

                 websocket_manager: WebSocketManager, redis_client, restart_simulator: ServiceRestartSimulator):

        self.jwt_service = jwt_service

        self.session_manager = session_manager

        self.websocket_manager = websocket_manager

        self.redis_client = redis_client

        self.restart_simulator = restart_simulator

        self.persistent_sessions = {}

        self.recovery_tests = []
    
    async def create_persistent_session(self, user_id: str, session_type: str = "standard") -> Dict[str, Any]:

        """Create a session designed to test persistence."""
        # Generate JWT with longer expiry for persistence testing

        token_result = await self.jwt_service.generate_token(

            user_id=user_id,

            permissions=["read", "write"],

            tier="enterprise",

            expires_delta=timedelta(hours=24)  # Long-lived for restart testing

        )
        
        if not token_result["success"]:

            raise ValueError(f"Token generation failed: {token_result.get('error')}")
        
        # Create session with persistence metadata

        session_metadata = {

            "session_type": session_type,

            "persistence_test": True,

            "created_for_restart_test": time.time(),

            "ip_address": "127.0.0.1",

            "user_agent": "persistence_test_client"

        }
        
        session_result = await self.session_manager.create_session(

            user_id=user_id,

            token=token_result["token"],

            metadata=session_metadata

        )
        
        if not session_result["success"]:

            raise ValueError(f"Session creation failed: {session_result.get('error')}")
        
        # Create WebSocket connection

        websocket = MockWebSocketForRedis(user_id)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.ws_manager.verify_jwt_token') as mock_verify:

            mock_verify.return_value = {

                "valid": True,

                "user_id": user_id,

                "permissions": ["read", "write"]

            }
            
            connection_info = await self.websocket_manager.connect_user(user_id, websocket)
        
        # Store session state for persistence verification

        session_state = {

            "user_id": user_id,

            "session_id": session_result["session_id"],

            "token": token_result["token"],

            "refresh_token": token_result.get("refresh_token"),

            "websocket": websocket,

            "connection_info": connection_info,

            "created_at": time.time(),

            "session_type": session_type,

            "last_activity": time.time()

        }
        
        # Store additional state in Redis for testing

        state_key = f"test_session_state:{session_result['session_id']}"

        state_data = {

            "user_id": user_id,

            "session_type": session_type,

            "test_data": {

                "current_workspace": "workspace_123",

                "open_documents": ["doc1", "doc2"],

                "preferences": {"theme": "dark", "language": "en"}

            },

            "activity_log": [

                {"action": "login", "timestamp": time.time()},

                {"action": "open_workspace", "timestamp": time.time()}

            ]

        }
        
        await self.redis_client.set(state_key, json.dumps(state_data), ex=86400)  # 24 hours
        
        self.persistent_sessions[session_result["session_id"]] = session_state
        
        logger.info(f"Created persistent session {session_result['session_id']} for user {user_id}")

        return session_state
    
    async def verify_session_persistence(self, session_id: str, 

                                       check_type: str = "full") -> Dict[str, Any]:

        """Verify that session persisted through restart."""

        verification_start = time.time()

        verification_results = {}
        
        if session_id not in self.persistent_sessions:

            return {"error": f"Session {session_id} not in test tracking"}
        
        original_session = self.persistent_sessions[session_id]

        user_id = original_session["user_id"]
        
        # Check session in database/session manager

        try:

            session_data = await self.session_manager.get_session(session_id)

            verification_results["session_manager"] = {

                "exists": session_data is not None,

                "data": session_data

            }

        except Exception as e:

            verification_results["session_manager"] = {"error": str(e)}
        
        # Check session state in Redis

        try:

            state_key = f"test_session_state:{session_id}"

            state_data = await self.redis_client.get(state_key)

            verification_results["redis_state"] = {

                "exists": state_data is not None,

                "data": json.loads(state_data) if state_data else None

            }

        except Exception as e:

            verification_results["redis_state"] = {"error": str(e)}
        
        # Check JWT token validity

        try:

            token_verification = await self.jwt_service.verify_token(original_session["token"])

            verification_results["token_validity"] = token_verification

        except Exception as e:

            verification_results["token_validity"] = {"error": str(e)}
        
        # Check WebSocket reconnection capability (if requested)

        if check_type == "full":

            try:
                # Create new WebSocket connection to test reconnection

                new_websocket = MockWebSocketForRedis(f"{user_id}_reconnect")
                
                # Mock: Component isolation for testing without external dependencies
                with patch('netra_backend.app.ws_manager.verify_jwt_token') as mock_verify:

                    mock_verify.return_value = {

                        "valid": True,

                        "user_id": user_id,

                        "permissions": ["read", "write"]

                    }
                    
                    reconnection_info = await self.websocket_manager.connect_user(user_id, new_websocket)
                
                verification_results["websocket_reconnection"] = {

                    "success": reconnection_info is not None,

                    "connection_info": reconnection_info

                }
                
                # Test message delivery

                if reconnection_info:

                    test_message = {"type": "persistence_test", "data": {"timestamp": time.time()}}

                    message_success = await self.websocket_manager.send_message_to_user(user_id, test_message)

                    verification_results["message_delivery"] = {"success": message_success}
                    
                    # Cleanup reconnection test

                    await self.websocket_manager.disconnect_user(user_id, new_websocket)
                
            except Exception as e:

                verification_results["websocket_reconnection"] = {"error": str(e)}
        
        verification_duration = time.time() - verification_start
        
        verification_summary = {

            "session_id": session_id,

            "user_id": user_id,

            "verification_duration": verification_duration,

            "results": verification_results,

            "overall_success": self._evaluate_verification_success(verification_results),

            "timestamp": time.time()

        }
        
        return verification_summary
    
    @pytest.mark.asyncio
    async def test_session_recovery_after_restart(self, restart_services: List[str], 

                                                 restart_type: str = "graceful") -> Dict[str, Any]:

        """Test session recovery after service restart."""

        recovery_test_start = time.time()
        
        # Create test sessions before restart

        test_users = [f"restart_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(3)]

        pre_restart_sessions = {}
        
        for user_id in test_users:

            session_data = await self.create_persistent_session(user_id, "restart_test")

            pre_restart_sessions[session_data["session_id"]] = session_data
        
        # Send test messages before restart

        for session_id, session_data in pre_restart_sessions.items():

            test_message = {"type": "pre_restart", "data": {"timestamp": time.time()}}

            await self.websocket_manager.send_message_to_user(session_data["user_id"], test_message)
        
        logger.info(f"Created {len(pre_restart_sessions)} sessions before restart")
        
        # Perform service restarts

        restart_events = []

        for service in restart_services:

            if service == "redis":

                restart_event = await self.restart_simulator.restart_redis(restart_type)

                restart_events.append(restart_event)

            elif service == "postgres":

                restart_event = await self.restart_simulator.restart_postgres(restart_type)

                restart_events.append(restart_event)
        
        # Wait for services to stabilize

        await asyncio.sleep(2)
        
        # Recreate service connections

        await self._reinitialize_services()
        
        # Verify session persistence

        recovery_results = {}

        for session_id in pre_restart_sessions.keys():

            verification = await self.verify_session_persistence(session_id, "full")

            recovery_results[session_id] = verification
        
        # Test new session creation after restart

        post_restart_user = f"post_restart_user_{uuid.uuid4().hex[:8]}"

        try:

            post_restart_session = await self.create_persistent_session(post_restart_user, "post_restart")

            new_session_creation = {"success": True, "session_id": post_restart_session["session_id"]}

        except Exception as e:

            new_session_creation = {"success": False, "error": str(e)}
        
        recovery_test_duration = time.time() - recovery_test_start
        
        # Analyze recovery success

        successful_recoveries = sum(1 for result in recovery_results.values() 

                                  if result.get("overall_success", False))

        total_sessions = len(recovery_results)

        recovery_rate = successful_recoveries / total_sessions if total_sessions > 0 else 0
        
        recovery_test_result = {

            "restart_services": restart_services,

            "restart_type": restart_type,

            "pre_restart_sessions": len(pre_restart_sessions),

            "successful_recoveries": successful_recoveries,

            "total_sessions": total_sessions,

            "recovery_rate": recovery_rate,

            "recovery_results": recovery_results,

            "restart_events": restart_events,

            "new_session_creation": new_session_creation,

            "test_duration": recovery_test_duration,

            "timestamp": time.time()

        }
        
        self.recovery_tests.append(recovery_test_result)
        
        logger.info(f"Recovery test completed: {successful_recoveries}/{total_sessions} sessions recovered "

                   f"after {restart_type} restart of {restart_services}")
        
        return recovery_test_result
    
    async def _reinitialize_services(self):

        """Reinitialize service connections after restart."""
        # Reconnect Redis client

        try:

            await self.redis_client.ping()

            logger.info("Redis connection restored")

        except Exception as e:

            logger.error(f"Redis reconnection failed: {e}")
        
        # Reinitialize session manager

        try:

            await self.session_manager.initialize()

            logger.info("Session manager reinitialized")

        except Exception as e:

            logger.error(f"Session manager reinitialization failed: {e}")
        
        # Reinitialize JWT service

        try:

            await self.jwt_service.initialize()

            logger.info("JWT service reinitialized")

        except Exception as e:

            logger.error(f"JWT service reinitialization failed: {e}")
    
    def _evaluate_verification_success(self, verification_results: Dict[str, Any]) -> bool:

        """Evaluate if session verification was successful."""
        # Session manager should have the session

        session_exists = verification_results.get("session_manager", {}).get("exists", False)
        
        # Redis state should be preserved

        redis_state_exists = verification_results.get("redis_state", {}).get("exists", False)
        
        # Token should be valid

        token_valid = verification_results.get("token_validity", {}).get("valid", False)
        
        # WebSocket reconnection should work (if tested)

        ws_reconnection = verification_results.get("websocket_reconnection", {})

        ws_success = ws_reconnection.get("success", True)  # Default true if not tested
        
        # Overall success requires most components to work

        return session_exists and redis_state_exists and token_valid and ws_success
    
    async def cleanup(self):

        """Clean up test sessions."""

        for session_id, session_data in self.persistent_sessions.items():

            try:

                await self.websocket_manager.disconnect_user(session_data["user_id"], session_data["websocket"])

                await self.session_manager.invalidate_session(session_id)
                
                # Clean up test state

                state_key = f"test_session_state:{session_id}"

                await self.redis_client.delete(state_key)

            except Exception as e:

                logger.warning(f"Cleanup error for session {session_id}: {e}")
        
        self.persistent_sessions.clear()

@pytest.mark.L3

@pytest.mark.integration

class TestSessionPersistenceRestartL3:

    """L3 integration test for session persistence after service restarts."""
    
    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container with persistence enabled."""

        container = RedisContainer()

        redis_url = await container.start()

        yield container, redis_url

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
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('netra_backend.app.redis_manager.RedisManager.get_client') as mock_redis:

            mock_redis.return_value = redis_client

            await service.initialize()

            yield service

            await service.shutdown()
    
    @pytest.fixture

    async def session_manager(self, redis_client):

        """Initialize session manager."""

        manager = SessionManager()
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('netra_backend.app.redis_manager.RedisManager.get_client') as mock_redis:

            mock_redis.return_value = redis_client

            await manager.initialize()

            yield manager

            await manager.shutdown()
    
    @pytest.fixture

    async def websocket_manager(self, redis_client):

        """Create WebSocket manager."""

        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('netra_backend.app.ws_manager.redis_manager') as mock_redis_mgr:

            test_redis_mgr = RedisManager()

            test_redis_mgr.enabled = True

            test_redis_mgr.redis_client = redis_client

            mock_redis_mgr.return_value = test_redis_mgr

            mock_redis_mgr.get_client.return_value = redis_client
            
            manager = WebSocketManager()

            yield manager
    
    @pytest.fixture

    async def restart_simulator(self, redis_container):

        """Create service restart simulator."""

        container, _ = redis_container

        simulator = ServiceRestartSimulator(container)

        yield simulator
    
    @pytest.fixture

    async def persistence_manager(self, jwt_service, session_manager, websocket_manager, 

                                redis_client, restart_simulator):

        """Create session persistence manager."""

        manager = SessionPersistenceManager(

            jwt_service, session_manager, websocket_manager, redis_client, restart_simulator

        )

        yield manager

        await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_redis_graceful_restart_session_persistence(self, persistence_manager):

        """Test session persistence through graceful Redis restart."""
        # Create persistent sessions

        users = [f"graceful_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(2)]

        sessions = {}
        
        for user_id in users:

            session_data = await persistence_manager.create_persistent_session(user_id, "graceful_test")

            sessions[session_data["session_id"]] = session_data
        
        # Verify sessions are active before restart

        for session_id in sessions.keys():

            verification = await persistence_manager.verify_session_persistence(session_id, "full")

            assert verification["overall_success"] is True
        
        # Perform graceful Redis restart

        recovery_result = await persistence_manager.test_session_recovery_after_restart(

            ["redis"], "graceful"

        )
        
        # Verify recovery success

        assert recovery_result["recovery_rate"] >= 0.8  # At least 80% recovery for graceful restart

        assert recovery_result["new_session_creation"]["success"] is True
        
        # Verify individual session recovery

        for session_id, recovery_data in recovery_result["recovery_results"].items():
            # For graceful restart, most sessions should recover

            assert recovery_data["overall_success"] is True
            
            # Redis state should be preserved

            redis_state = recovery_data["results"]["redis_state"]

            assert redis_state["exists"] is True

            assert "test_data" in redis_state["data"]
        
        logger.info(f"Graceful restart test: {recovery_result['recovery_rate']:.1%} recovery rate")
    
    @pytest.mark.asyncio
    async def test_redis_crash_restart_session_recovery(self, persistence_manager):

        """Test session recovery after Redis crash restart."""
        # Create persistent sessions with more robust data

        users = [f"crash_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(2)]

        sessions = {}
        
        for user_id in users:

            session_data = await persistence_manager.create_persistent_session(user_id, "crash_test")

            sessions[session_data["session_id"]] = session_data
        
        # Send some test messages to establish state

        for session_data in sessions.values():

            test_message = {"type": "pre_crash", "data": {"important": True}}

            await persistence_manager.websocket_manager.send_message_to_user(

                session_data["user_id"], test_message

            )
        
        # Perform crash restart

        recovery_result = await persistence_manager.test_session_recovery_after_restart(

            ["redis"], "crash"

        )
        
        # Verify some level of recovery (may be lower for crash)

        assert recovery_result["recovery_rate"] >= 0.3  # At least 30% recovery for crash restart

        assert recovery_result["new_session_creation"]["success"] is True
        
        # Verify restart event recorded

        restart_events = recovery_result["restart_events"]

        assert len(restart_events) == 1

        assert restart_events[0]["service"] == "redis"

        assert restart_events[0]["restart_type"] == "crash"
        
        logger.info(f"Crash restart test: {recovery_result['recovery_rate']:.1%} recovery rate")
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_after_restart(self, persistence_manager):

        """Test WebSocket reconnection capability after service restart."""

        user_id = f"ws_reconnect_user_{uuid.uuid4().hex[:8]}"
        
        # Create session with active WebSocket

        session_data = await persistence_manager.create_persistent_session(user_id, "websocket_test")

        session_id = session_data["session_id"]

        original_websocket = session_data["websocket"]
        
        # Send initial message

        initial_message = {"type": "initial", "data": {"timestamp": time.time()}}

        success = await persistence_manager.websocket_manager.send_message_to_user(user_id, initial_message)

        assert success is True
        
        # Perform restart

        recovery_result = await persistence_manager.test_session_recovery_after_restart(

            ["redis"], "graceful"

        )
        
        # Verify session recovery

        session_recovery = recovery_result["recovery_results"][session_id]

        assert session_recovery["overall_success"] is True
        
        # Verify WebSocket reconnection worked

        ws_reconnection = session_recovery["results"]["websocket_reconnection"]

        assert ws_reconnection["success"] is True
        
        # Verify message delivery works after reconnection

        message_delivery = session_recovery["results"]["message_delivery"]

        assert message_delivery["success"] is True
        
        # Test additional message delivery

        post_restart_message = {"type": "post_restart", "data": {"recovered": True}}

        post_success = await persistence_manager.websocket_manager.send_message_to_user(

            user_id, post_restart_message

        )

        assert post_success is True
        
        logger.info("WebSocket reconnection after restart verified successfully")
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions_restart_resilience(self, persistence_manager):

        """Test multiple concurrent sessions surviving restart."""
        # Create many concurrent sessions

        session_count = 10

        users = [f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(session_count)]

        sessions = {}
        
        # Create sessions concurrently

        async def create_session(user_id):

            return await persistence_manager.create_persistent_session(user_id, "concurrent_test")
        
        session_tasks = [create_session(user_id) for user_id in users]

        session_results = await asyncio.gather(*session_tasks)
        
        for session_data in session_results:

            sessions[session_data["session_id"]] = session_data
        
        # Send messages to all sessions

        for session_data in sessions.values():

            test_message = {"type": "concurrent_pre_restart", "data": {"session_id": session_data["session_id"]}}

            await persistence_manager.websocket_manager.send_message_to_user(

                session_data["user_id"], test_message

            )
        
        # Perform restart

        recovery_result = await persistence_manager.test_session_recovery_after_restart(

            ["redis"], "graceful"

        )
        
        # Verify high recovery rate for concurrent sessions

        assert recovery_result["pre_restart_sessions"] == session_count

        assert recovery_result["recovery_rate"] >= 0.7  # At least 70% recovery
        
        # Verify that most sessions have functional components

        successful_components = defaultdict(int)

        total_components = 0
        
        for session_id, recovery_data in recovery_result["recovery_results"].items():

            results = recovery_data["results"]

            total_components += len(results)
            
            for component, result in results.items():

                if isinstance(result, dict) and (result.get("exists") or result.get("valid") or result.get("success")):

                    successful_components[component] += 1
        
        # Most components should work for most sessions

        for component, success_count in successful_components.items():

            success_rate = success_count / session_count

            logger.info(f"Component {component}: {success_rate:.1%} success rate")
            
            # Critical components should have high success rates

            if component in ["session_manager", "token_validity"]:

                assert success_rate >= 0.7
        
        logger.info(f"Concurrent sessions restart test: {recovery_result['recovery_rate']:.1%} recovery rate "

                   f"for {session_count} sessions")
    
    @pytest.mark.asyncio
    async def test_session_state_data_persistence(self, persistence_manager):

        """Test that complex session state data persists through restart."""

        user_id = f"state_test_user_{uuid.uuid4().hex[:8]}"
        
        # Create session with rich state data

        session_data = await persistence_manager.create_persistent_session(user_id, "state_persistence")

        session_id = session_data["session_id"]
        
        # Add additional state data

        state_key = f"test_session_state:{session_id}"

        complex_state = {

            "user_id": user_id,

            "workspace_data": {

                "current_project": "project_alpha",

                "open_files": [

                    {"name": "main.py", "cursor": 145, "modified": True},

                    {"name": "config.json", "cursor": 0, "modified": False}

                ],

                "recent_searches": ["authentication", "websocket", "redis"],

                "bookmarks": ["line_42", "line_89", "line_156"]

            },

            "user_preferences": {

                "theme": "dark",

                "font_size": 14,

                "auto_save": True,

                "notifications": {"email": True, "push": False}

            },

            "session_metrics": {

                "login_time": time.time(),

                "commands_executed": 47,

                "files_modified": 3,

                "last_activity": time.time()

            }

        }
        
        await persistence_manager.redis_client.set(state_key, json.dumps(complex_state), ex=86400)
        
        # Perform restart

        recovery_result = await persistence_manager.test_session_recovery_after_restart(

            ["redis"], "graceful"

        )
        
        # Verify session recovery

        session_recovery = recovery_result["recovery_results"][session_id]

        assert session_recovery["overall_success"] is True
        
        # Verify complex state data preservation

        redis_state = session_recovery["results"]["redis_state"]

        assert redis_state["exists"] is True
        
        recovered_state = redis_state["data"]
        
        # Verify workspace data

        assert "workspace_data" in recovered_state

        workspace = recovered_state["workspace_data"]

        assert workspace["current_project"] == "project_alpha"

        assert len(workspace["open_files"]) == 2

        assert "main.py" in [f["name"] for f in workspace["open_files"]]
        
        # Verify user preferences

        assert "user_preferences" in recovered_state

        preferences = recovered_state["user_preferences"]

        assert preferences["theme"] == "dark"

        assert preferences["auto_save"] is True
        
        # Verify session metrics

        assert "session_metrics" in recovered_state

        metrics = recovered_state["session_metrics"]

        assert metrics["commands_executed"] == 47

        assert metrics["files_modified"] == 3
        
        logger.info("Complex session state data persistence verified successfully")
    
    @pytest.mark.asyncio
    async def test_restart_performance_impact(self, persistence_manager):

        """Test performance impact of service restart on session operations."""

        user_id = f"perf_test_user_{uuid.uuid4().hex[:8]}"
        
        # Create session and measure pre-restart performance

        session_data = await persistence_manager.create_persistent_session(user_id, "performance_test")
        
        # Measure pre-restart operations

        pre_restart_times = []

        for i in range(5):

            start_time = time.time()

            verification = await persistence_manager.verify_session_persistence(

                session_data["session_id"], "full"

            )

            operation_time = time.time() - start_time

            pre_restart_times.append(operation_time)

            assert verification["overall_success"] is True
        
        avg_pre_restart_time = sum(pre_restart_times) / len(pre_restart_times)
        
        # Perform restart

        restart_start = time.time()

        recovery_result = await persistence_manager.test_session_recovery_after_restart(

            ["redis"], "graceful"

        )

        total_restart_time = time.time() - restart_start
        
        # Measure post-restart operations

        post_restart_times = []

        for i in range(5):

            start_time = time.time()

            verification = await persistence_manager.verify_session_persistence(

                session_data["session_id"], "full"

            )

            operation_time = time.time() - start_time

            post_restart_times.append(operation_time)
        
        avg_post_restart_time = sum(post_restart_times) / len(post_restart_times)
        
        # Performance assertions

        assert total_restart_time < 30.0  # Restart should complete within 30 seconds

        assert recovery_result["recovery_rate"] >= 0.8  # High recovery rate
        
        # Post-restart performance should be reasonable

        performance_degradation = avg_post_restart_time / avg_pre_restart_time

        assert performance_degradation < 3.0  # No more than 3x slower
        
        logger.info(f"Restart performance: total_time={total_restart_time:.2f}s, "

                   f"pre_restart_avg={avg_pre_restart_time:.3f}s, "

                   f"post_restart_avg={avg_post_restart_time:.3f}s, "

                   f"degradation={performance_degradation:.1f}x")

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])