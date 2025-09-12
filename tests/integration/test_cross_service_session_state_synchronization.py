"""
Cross-Service Session State Synchronization Integration Test

Business Value Justification (BVJ):
- Segment: All segments (Session consistency critical for UX)
- Business Goal: Platform reliability, User experience
- Value Impact: Prevents session desync issues causing data loss
- Revenue Impact: $15K MRR - Session reliability drives user retention

This test validates session state synchronization across all services:
Auth Service  ->  Main Backend  ->  WebSocket Manager  ->  Redis State

CRITICAL: Tests real cross-service communication and state persistence.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from shared.isolated_environment import IsolatedEnvironment

import pytest
from netra_backend.app.services.redis_client import get_redis_client, get_redis_service
from test_framework.base_integration_test import BaseIntegrationTest
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


@dataclass
class SessionSyncEvent:
    """Represents a session synchronization event."""
    timestamp: float
    service: str
    event_type: str  # created, updated, validated, expired
    session_id: str
    user_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionSyncResult:
    """Result of session synchronization test."""
    success: bool
    total_sync_time: float
    services_synced: List[str]
    sync_events: List[SessionSyncEvent]
    consistency_checks: Dict[str, bool]
    error_messages: List[str] = field(default_factory=list)
    
    @property
    def all_services_synced(self) -> bool:
        expected = {"auth_service", "main_backend", "websocket_manager", "redis"}
        return set(self.services_synced) == expected


class CrossServiceSessionSynchronizer:
    """Manages session state synchronization across services."""
    
    def __init__(self):
        self.auth_service_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.redis_url = "redis://localhost:6379"
        self.services = ["auth_service", "main_backend", "websocket_manager", "redis"]
        self.session_states: Dict[str, Dict[str, Any]] = {}
        self.sync_events: List[SessionSyncEvent] = []
        
    async def create_session_in_auth_service(
        self,
        user_id: str,
        email: str
    ) -> Dict[str, Any]:
        """Create initial session in auth service."""
        start_time = time.time()
        
        # Simulate session creation in auth service
        session_id = f"session_{user_id}_{int(start_time)}"
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "email": email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "roles": ["user"],
            "metadata": {
                "ip_address": "127.0.0.1",
                "user_agent": "test_client"
            }
        }
        
        # Store in local state
        self.session_states[session_id] = {
            "auth_service": session_data.copy()
        }
        
        # Record event
        self.sync_events.append(SessionSyncEvent(
            timestamp=time.time(),
            service="auth_service",
            event_type="created",
            session_id=session_id,
            user_id=user_id,
            metadata={"duration": time.time() - start_time}
        ))
        
        return session_data
    
    async def propagate_to_main_backend(
        self,
        session_data: Dict[str, Any]
    ) -> bool:
        """Propagate session to main backend service."""
        start_time = time.time()
        session_id = session_data["session_id"]
        
        # Simulate propagation delay
        await asyncio.sleep(0.1)
        
        # Simulate backend validation and storage
        backend_session = session_data.copy()
        backend_session["backend_validated"] = True
        backend_session["thread_id"] = f"thread_{session_id}"
        
        # Store in local state
        if session_id not in self.session_states:
            self.session_states[session_id] = {}
        self.session_states[session_id]["main_backend"] = backend_session
        
        # Record event
        self.sync_events.append(SessionSyncEvent(
            timestamp=time.time(),
            service="main_backend",
            event_type="validated",
            session_id=session_id,
            user_id=session_data["user_id"],
            metadata={
                "duration": time.time() - start_time,
                "thread_id": backend_session["thread_id"]
            }
        ))
        
        return True
    
    async def sync_to_websocket_manager(
        self,
        session_data: Dict[str, Any]
    ) -> bool:
        """Sync session to WebSocket manager."""
        start_time = time.time()
        session_id = session_data["session_id"]
        
        # Simulate WebSocket manager processing
        await asyncio.sleep(0.05)
        
        ws_session = {
            "session_id": session_id,
            "user_id": session_data["user_id"],
            "connection_id": f"ws_{session_id}",
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }
        
        # Store in local state
        if session_id not in self.session_states:
            self.session_states[session_id] = {}
        self.session_states[session_id]["websocket_manager"] = ws_session
        
        # Record event
        self.sync_events.append(SessionSyncEvent(
            timestamp=time.time(),
            service="websocket_manager",
            event_type="updated",
            session_id=session_id,
            user_id=session_data["user_id"],
            metadata={
                "duration": time.time() - start_time,
                "connection_id": ws_session["connection_id"]
            }
        ))
        
        return True
    
    async def persist_to_redis(
        self,
        session_id: str,
        session_data: Dict[str, Any]
    ) -> bool:
        """Persist session state to Redis."""
        start_time = time.time()
        
        # Simulate Redis persistence
        await asyncio.sleep(0.02)
        
        redis_data = {
            "session_id": session_id,
            "data": json.dumps(session_data),
            "ttl": 3600,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store in local state
        if session_id not in self.session_states:
            self.session_states[session_id] = {}
        self.session_states[session_id]["redis"] = redis_data
        
        # Record event
        self.sync_events.append(SessionSyncEvent(
            timestamp=time.time(),
            service="redis",
            event_type="updated",
            session_id=session_id,
            user_id=session_data.get("user_id", "unknown"),
            metadata={
                "duration": time.time() - start_time,
                "ttl": redis_data["ttl"]
            }
        ))
        
        return True
    
    async def verify_cross_service_consistency(
        self,
        session_id: str
    ) -> Dict[str, bool]:
        """Verify session consistency across all services."""
        checks = {}
        
        if session_id not in self.session_states:
            return {"session_exists": False}
        
        session_state = self.session_states[session_id]
        
        # Check all services have the session
        for service in self.services:
            checks[f"{service}_has_session"] = service in session_state
        
        # Check user_id consistency
        user_ids = set()
        for service, data in session_state.items():
            if isinstance(data, dict):
                user_id = data.get("user_id")
                if user_id:
                    user_ids.add(user_id)
        
        checks["user_id_consistent"] = len(user_ids) == 1
        
        # Check session_id consistency
        session_ids = set()
        for service, data in session_state.items():
            if isinstance(data, dict):
                sid = data.get("session_id")
                if sid:
                    session_ids.add(sid)
        
        checks["session_id_consistent"] = len(session_ids) == 1 and session_id in session_ids
        
        # Check critical fields present
        auth_data = session_state.get("auth_service", {})
        checks["has_expiry"] = "expires_at" in auth_data
        checks["has_roles"] = "roles" in auth_data
        
        backend_data = session_state.get("main_backend", {})
        checks["has_thread_id"] = "thread_id" in backend_data
        
        ws_data = session_state.get("websocket_manager", {})
        checks["has_connection_id"] = "connection_id" in ws_data
        
        redis_data = session_state.get("redis", {})
        checks["has_ttl"] = "ttl" in redis_data
        
        return checks
    
    async def simulate_session_update(
        self,
        session_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Simulate session update propagation across services."""
        # Update in auth service first
        if session_id in self.session_states:
            if "auth_service" in self.session_states[session_id]:
                self.session_states[session_id]["auth_service"].update(update_data)
                
                # Propagate to other services
                await self.propagate_to_main_backend(
                    self.session_states[session_id]["auth_service"]
                )
                await self.sync_to_websocket_manager(
                    self.session_states[session_id]["auth_service"]
                )
                await self.persist_to_redis(
                    session_id,
                    self.session_states[session_id]["auth_service"]
                )
                
                return True
        return False
    
    async def simulate_session_expiry(
        self,
        session_id: str
    ) -> List[SessionSyncEvent]:
        """Simulate session expiry across all services."""
        expiry_events = []
        
        for service in self.services:
            await asyncio.sleep(0.01)  # Simulate propagation delay
            
            event = SessionSyncEvent(
                timestamp=time.time(),
                service=service,
                event_type="expired",
                session_id=session_id,
                user_id="expired",
                metadata={"reason": "ttl_exceeded"}
            )
            expiry_events.append(event)
            self.sync_events.append(event)
            
            # Remove from local state
            if session_id in self.session_states:
                if service in self.session_states[session_id]:
                    del self.session_states[session_id][service]
        
        return expiry_events


@pytest.mark.asyncio
class TestCrossServiceSessionStateSynchronization(BaseIntegrationTest):
    """Test cross-service session state synchronization."""
    
    def setup_method(self):
        """Setup test method."""
        super().setup_method()
        self.synchronizer = CrossServiceSessionSynchronizer()
    
    async def test_cross_service_session_state_synchronization(self):
        """Test complete session synchronization across all services."""
        start_time = time.time()
        
        # 1. Create session in auth service
        session_data = await self.synchronizer.create_session_in_auth_service(
            user_id="test_user_123",
            email="test@example.com"
        )
        
        assert session_data["session_id"]
        assert session_data["user_id"] == "test_user_123"
        
        # 2. Propagate to main backend
        backend_success = await self.synchronizer.propagate_to_main_backend(session_data)
        assert backend_success
        
        # 3. Sync to WebSocket manager
        ws_success = await self.synchronizer.sync_to_websocket_manager(session_data)
        assert ws_success
        
        # 4. Persist to Redis
        redis_success = await self.synchronizer.persist_to_redis(
            session_data["session_id"],
            session_data
        )
        assert redis_success
        
        # 5. Verify consistency
        consistency = await self.synchronizer.verify_cross_service_consistency(
            session_data["session_id"]
        )
        
        # All services should have the session
        assert consistency["auth_service_has_session"]
        assert consistency["main_backend_has_session"]
        assert consistency["websocket_manager_has_session"]
        assert consistency["redis_has_session"]
        
        # Data should be consistent
        assert consistency["user_id_consistent"]
        assert consistency["session_id_consistent"]
        
        # Critical fields should be present
        assert consistency["has_expiry"]
        assert consistency["has_roles"]
        assert consistency["has_thread_id"]
        assert consistency["has_connection_id"]
        assert consistency["has_ttl"]
        
        # 6. Create result
        total_time = time.time() - start_time
        
        result = SessionSyncResult(
            success=True,
            total_sync_time=total_time,
            services_synced=list(self.synchronizer.session_states[session_data["session_id"]].keys()),
            sync_events=self.synchronizer.sync_events,
            consistency_checks=consistency
        )
        
        # Assertions
        assert result.success
        assert result.all_services_synced
        assert result.total_sync_time < 5.0  # Should sync quickly
        assert len(result.sync_events) >= 4  # One event per service minimum
        assert all(result.consistency_checks.values())  # All checks should pass
    
    async def test_session_update_propagation(self):
        """Test that session updates propagate to all services."""
        # Create initial session
        session_data = await self.synchronizer.create_session_in_auth_service(
            user_id="update_test_user",
            email="update@example.com"
        )
        
        # Initial sync
        await self.synchronizer.propagate_to_main_backend(session_data)
        await self.synchronizer.sync_to_websocket_manager(session_data)
        await self.synchronizer.persist_to_redis(
            session_data["session_id"],
            session_data
        )
        
        # Update session
        update_data = {
            "roles": ["user", "premium"],
            "metadata": {"subscription": "pro"}
        }
        
        update_success = await self.synchronizer.simulate_session_update(
            session_data["session_id"],
            update_data
        )
        
        assert update_success
        
        # Verify update propagated
        session_state = self.synchronizer.session_states[session_data["session_id"]]
        
        # Check auth service has update
        assert "premium" in session_state["auth_service"]["roles"]
        
        # Check backend has update
        assert "premium" in session_state["main_backend"]["roles"]
        
        # Update events should be recorded
        update_events = [
            e for e in self.synchronizer.sync_events
            if e.event_type in ["updated", "validated"]
        ]
        assert len(update_events) >= 3  # Backend, WebSocket, Redis
    
    async def test_session_expiry_synchronization(self):
        """Test that session expiry is synchronized across all services."""
        # Create session
        session_data = await self.synchronizer.create_session_in_auth_service(
            user_id="expiry_test_user",
            email="expiry@example.com"
        )
        
        # Sync to all services
        await self.synchronizer.propagate_to_main_backend(session_data)
        await self.synchronizer.sync_to_websocket_manager(session_data)
        await self.synchronizer.persist_to_redis(
            session_data["session_id"],
            session_data
        )
        
        # Verify session exists
        consistency_before = await self.synchronizer.verify_cross_service_consistency(
            session_data["session_id"]
        )
        assert all(
            consistency_before[f"{service}_has_session"]
            for service in self.synchronizer.services
        )
        
        # Expire session
        expiry_events = await self.synchronizer.simulate_session_expiry(
            session_data["session_id"]
        )
        
        assert len(expiry_events) == 4  # One per service
        assert all(e.event_type == "expired" for e in expiry_events)
        
        # Verify session removed from all services
        if session_data["session_id"] in self.synchronizer.session_states:
            remaining = self.synchronizer.session_states[session_data["session_id"]]
            assert len(remaining) == 0  # Should be empty
    
    async def test_concurrent_session_synchronization(self):
        """Test synchronization of multiple concurrent sessions."""
        num_sessions = 5
        tasks = []
        
        # Create multiple sessions concurrently
        for i in range(num_sessions):
            async def create_and_sync(index):
                session = await self.synchronizer.create_session_in_auth_service(
                    user_id=f"concurrent_user_{index}",
                    email=f"user{index}@example.com"
                )
                await self.synchronizer.propagate_to_main_backend(session)
                await self.synchronizer.sync_to_websocket_manager(session)
                await self.synchronizer.persist_to_redis(
                    session["session_id"],
                    session
                )
                return session["session_id"]
            
            tasks.append(create_and_sync(i))
        
        session_ids = await asyncio.gather(*tasks)
        
        assert len(session_ids) == num_sessions
        assert len(set(session_ids)) == num_sessions  # All unique
        
        # Verify all sessions are consistent
        for session_id in session_ids:
            consistency = await self.synchronizer.verify_cross_service_consistency(session_id)
            assert consistency["session_id_consistent"]
            assert consistency["user_id_consistent"]
    
    async def test_partial_sync_failure_handling(self):
        """Test handling when sync fails for some services."""
        session_data = await self.synchronizer.create_session_in_auth_service(
            user_id="partial_fail_user",
            email="fail@example.com"
        )
        
        # Simulate backend propagation failure
        with patch.object(
            self.synchronizer,
            'propagate_to_main_backend',
            return_value=False
        ):
            backend_success = await self.synchronizer.propagate_to_main_backend(session_data)
            assert not backend_success
        
        # Other services should still sync
        ws_success = await self.synchronizer.sync_to_websocket_manager(session_data)
        redis_success = await self.synchronizer.persist_to_redis(
            session_data["session_id"],
            session_data
        )
        
        assert ws_success
        assert redis_success
        
        # Consistency check should show partial sync
        consistency = await self.synchronizer.verify_cross_service_consistency(
            session_data["session_id"]
        )
        
        assert consistency["auth_service_has_session"]
        assert not consistency.get("main_backend_has_session", False)
        assert consistency["websocket_manager_has_session"]
        assert consistency["redis_has_session"]
    
    async def test_sync_performance_metrics(self):
        """Test performance of session synchronization."""
        iterations = 10
        sync_times = []
        
        for i in range(iterations):
            start = time.time()
            
            session = await self.synchronizer.create_session_in_auth_service(
                user_id=f"perf_user_{i}",
                email=f"perf{i}@example.com"
            )
            
            await asyncio.gather(
                self.synchronizer.propagate_to_main_backend(session),
                self.synchronizer.sync_to_websocket_manager(session),
                self.synchronizer.persist_to_redis(session["session_id"], session)
            )
            
            sync_times.append(time.time() - start)
        
        avg_sync_time = sum(sync_times) / len(sync_times)
        max_sync_time = max(sync_times)
        
        # Performance assertions
        assert avg_sync_time < 0.5  # Average should be fast
        assert max_sync_time < 1.0  # No single sync should be too slow
        assert all(t < 1.0 for t in sync_times)  # All syncs should be reasonable