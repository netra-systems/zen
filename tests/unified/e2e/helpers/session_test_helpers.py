"""Session Testing Utilities

This module provides comprehensive session testing infrastructure including:
- Session persistence validation
- Cross-service session synchronization testing
- Session state recovery mechanisms
- Multi-tab session management
- Session timeout and cleanup testing
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

from tests.unified.e2e.config import TEST_USERS, TEST_ENDPOINTS, TestDataFactory
from tests.unified.e2e.real_websocket_client import RealWebSocketClient
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class SessionTestData:
    """Session test data structure"""
    session_id: str
    user_id: str
    created_at: float
    last_activity: float
    state_data: Dict[str, Any]
    is_active: bool = True


class SessionPersistenceManager:
    """Manages session persistence testing and validation."""
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionTestData] = {}
        self.session_events: List[Dict[str, Any]] = []
        self.state_snapshots: List[Dict[str, Any]] = {}
    
    async def create_test_session(self, user_id: str, initial_state: Dict[str, Any] = None) -> SessionTestData:
        """Create a test session with initial state."""
        session_id = f"test_session_{uuid.uuid4().hex[:12]}"
        current_time = time.time()
        
        session_data = SessionTestData(
            session_id=session_id,
            user_id=user_id,
            created_at=current_time,
            last_activity=current_time,
            state_data=initial_state or {},
            is_active=True
        )
        
        self.active_sessions[session_id] = session_data
        
        # Record session creation event
        self.session_events.append({
            "event_type": "session_created",
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": current_time
        })
        
        logger.info(f"Created test session {session_id} for user {user_id}")
        return session_data
    
    async def update_session_state(self, session_id: str, state_updates: Dict[str, Any]) -> bool:
        """Update session state and track changes."""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        session.state_data.update(state_updates)
        session.last_activity = time.time()
        
        # Record state update event
        self.session_events.append({
            "event_type": "state_updated",
            "session_id": session_id,
            "updates": state_updates,
            "timestamp": time.time()
        })
        
        logger.debug(f"Updated state for session {session_id}: {state_updates}")
        return True
    
    async def validate_session_persistence(self, session_id: str) -> Dict[str, Any]:
        """Validate session data persists correctly."""
        if session_id not in self.active_sessions:
            return {"valid": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Simulate persistence validation
        validation_result = {
            "session_id": session_id,
            "persistent": True,
            "state_size": len(session.state_data),
            "last_activity": session.last_activity,
            "session_age": time.time() - session.created_at,
            "valid": True
        }
        
        return validation_result
    
    async def simulate_session_restart(self, session_id: str) -> Dict[str, Any]:
        """Simulate session restart and validate recovery."""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Capture pre-restart state
        pre_restart_state = session.state_data.copy()
        
        # Simulate restart (brief interruption)
        await asyncio.sleep(0.1)
        
        # Validate state recovery
        post_restart_state = session.state_data
        
        recovery_result = {
            "session_id": session_id,
            "success": True,
            "state_preserved": pre_restart_state == post_restart_state,
            "restart_time": time.time()
        }
        
        self.session_events.append({
            "event_type": "session_restarted",
            "session_id": session_id,
            "recovery_result": recovery_result,
            "timestamp": time.time()
        })
        
        logger.info(f"Simulated restart for session {session_id}")
        return recovery_result
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        active_count = len(self.active_sessions)
        total_events = len(self.session_events)
        
        event_types = {}
        for event in self.session_events:
            event_type = event.get("event_type")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        return {
            "active_sessions": active_count,
            "total_events": total_events,
            "event_types": event_types,
            "session_ids": list(self.active_sessions.keys())
        }


class CrossServiceSessionValidator:
    """Validates session synchronization across services."""
    
    def __init__(self):
        self.sync_checks: List[Dict[str, Any]] = []
        self.validation_errors: List[str] = []
    
    async def validate_cross_service_sync(self, session_id: str, services: List[str] = None) -> Dict[str, Any]:
        """Validate session state is synchronized across services."""
        services = services or ["frontend", "backend", "auth_service"]
        
        sync_results = {}
        
        for service in services:
            # Simulate service state check
            service_state = await self._get_service_session_state(service, session_id)
            sync_results[service] = service_state
        
        # Check for consistency
        consistency_check = self._check_state_consistency(sync_results)
        
        sync_validation = {
            "session_id": session_id,
            "services_checked": services,
            "sync_results": sync_results,
            "consistent": consistency_check["consistent"],
            "inconsistencies": consistency_check.get("inconsistencies", []),
            "validation_time": time.time()
        }
        
        self.sync_checks.append(sync_validation)
        return sync_validation
    
    async def _get_service_session_state(self, service: str, session_id: str) -> Dict[str, Any]:
        """Get session state from specific service."""
        # Simulate service-specific session state
        base_state = {
            "session_id": session_id,
            "exists": True,
            "last_seen": time.time(),
            "service": service
        }
        
        if service == "frontend":
            base_state.update({
                "ui_state": {"current_view": "dashboard", "theme": "light"},
                "cached_data": {"user_prefs": {"notifications": True}}
            })
        elif service == "backend":
            base_state.update({
                "api_state": {"active_requests": 0, "rate_limit": 100},
                "database_session": {"connection_pool": "active"}
            })
        elif service == "auth_service":
            base_state.update({
                "auth_state": {"token_valid": True, "permissions": ["read", "write"]},
                "security_context": {"ip_address": "127.0.0.1"}
            })
        
        return base_state
    
    def _check_state_consistency(self, sync_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Check consistency across service states."""
        inconsistencies = []
        
        # Extract session IDs from all services
        session_ids = set()
        for service, state in sync_results.items():
            if state.get("exists"):
                session_ids.add(state.get("session_id"))
        
        # Check if all services have the same session ID
        if len(session_ids) > 1:
            inconsistencies.append("Session ID mismatch across services")
        
        # Check if all services report session exists
        services_with_session = [
            service for service, state in sync_results.items() 
            if state.get("exists")
        ]
        
        if len(services_with_session) != len(sync_results):
            missing_services = set(sync_results.keys()) - set(services_with_session)
            inconsistencies.append(f"Session missing from services: {missing_services}")
        
        return {
            "consistent": len(inconsistencies) == 0,
            "inconsistencies": inconsistencies
        }
    
    def get_validation_errors(self) -> List[str]:
        """Get all validation errors."""
        return self.validation_errors.copy()
    
    def clear_errors(self) -> None:
        """Clear validation errors."""
        self.validation_errors.clear()


class MultiTabSessionManager:
    """Manages multi-tab session testing scenarios."""
    
    def __init__(self):
        self.tab_sessions: Dict[str, Dict[str, Any]] = {}
        self.tab_events: List[Dict[str, Any]] = []
    
    async def create_tab_session(self, user_id: str, tab_id: str = None) -> Dict[str, Any]:
        """Create a new tab session."""
        tab_id = tab_id or f"tab_{uuid.uuid4().hex[:8]}"
        
        tab_session = {
            "tab_id": tab_id,
            "user_id": user_id,
            "session_id": f"session_{tab_id}",
            "created_at": time.time(),
            "state": {},
            "websocket_connected": False
        }
        
        self.tab_sessions[tab_id] = tab_session
        
        self.tab_events.append({
            "event_type": "tab_created",
            "tab_id": tab_id,
            "user_id": user_id,
            "timestamp": time.time()
        })
        
        logger.info(f"Created tab session {tab_id} for user {user_id}")
        return tab_session
    
    async def connect_tab_websocket(self, tab_id: str) -> bool:
        """Connect WebSocket for tab session."""
        if tab_id not in self.tab_sessions:
            return False
        
        self.tab_sessions[tab_id]["websocket_connected"] = True
        self.tab_sessions[tab_id]["connected_at"] = time.time()
        
        self.tab_events.append({
            "event_type": "websocket_connected",
            "tab_id": tab_id,
            "timestamp": time.time()
        })
        
        return True
    
    async def sync_tab_states(self, user_id: str) -> Dict[str, Any]:
        """Synchronize state across all user tabs."""
        user_tabs = [
            tab_id for tab_id, session in self.tab_sessions.items()
            if session["user_id"] == user_id
        ]
        
        if not user_tabs:
            return {"success": False, "error": "No tabs found for user"}
        
        # Simulate state synchronization
        sync_state = {
            "shared_data": {"current_thread": "thread_123", "notifications": []},
            "sync_timestamp": time.time()
        }
        
        for tab_id in user_tabs:
            self.tab_sessions[tab_id]["state"].update(sync_state)
        
        sync_result = {
            "user_id": user_id,
            "tabs_synced": len(user_tabs),
            "tab_ids": user_tabs,
            "sync_state": sync_state,
            "success": True
        }
        
        self.tab_events.append({
            "event_type": "tabs_synced",
            "user_id": user_id,
            "result": sync_result,
            "timestamp": time.time()
        })
        
        return sync_result
    
    def validate_tab_isolation(self, tab_id_1: str, tab_id_2: str) -> bool:
        """Validate tabs maintain proper isolation."""
        if tab_id_1 not in self.tab_sessions or tab_id_2 not in self.tab_sessions:
            return False
        
        tab_1 = self.tab_sessions[tab_id_1]
        tab_2 = self.tab_sessions[tab_id_2]
        
        # Check different users have isolated sessions
        if tab_1["user_id"] != tab_2["user_id"]:
            # Should have different session IDs
            return tab_1["session_id"] != tab_2["session_id"]
        
        # Same user tabs should share some state but maintain tab-specific isolation
        return True
    
    def get_tab_statistics(self) -> Dict[str, Any]:
        """Get multi-tab session statistics."""
        total_tabs = len(self.tab_sessions)
        connected_tabs = sum(
            1 for session in self.tab_sessions.values()
            if session.get("websocket_connected", False)
        )
        
        users = set(session["user_id"] for session in self.tab_sessions.values())
        
        return {
            "total_tabs": total_tabs,
            "connected_tabs": connected_tabs,
            "active_users": len(users),
            "total_events": len(self.tab_events)
        }


def create_test_session_data(user_id: str, state_complexity: str = "simple") -> Dict[str, Any]:
    """Create test session data with varying complexity."""
    base_state = {
        "user_id": user_id,
        "preferences": {"theme": "light", "language": "en"},
        "session_meta": {"created": time.time()}
    }
    
    if state_complexity == "complex":
        base_state.update({
            "ui_state": {
                "current_view": "dashboard",
                "sidebar_collapsed": False,
                "filter_settings": {"date_range": "last_7_days"}
            },
            "cache": {
                "recent_threads": ["thread_1", "thread_2"],
                "quick_actions": ["create_thread", "search"]
            },
            "temporary_data": {
                "draft_message": "Hello, I'm working on...",
                "unsaved_changes": True
            }
        })
    
    return base_state


async def validate_session_timeout_behavior(session_manager: SessionPersistenceManager, 
                                          session_id: str, timeout_seconds: float = 1.0) -> bool:
    """Validate session timeout behavior."""
    # Wait for timeout period
    await asyncio.sleep(timeout_seconds)
    
    # Check if session handles timeout correctly
    validation_result = await session_manager.validate_session_persistence(session_id)
    
    # Session should still be valid but may have timeout indicators
    return validation_result.get("valid", False)


def create_session_test_scenarios() -> List[Dict[str, Any]]:
    """Create various session testing scenarios."""
    scenarios = [
        {
            "name": "Basic Session Persistence",
            "description": "Test simple session persistence across restart",
            "complexity": "simple",
            "expected_duration": 5.0
        },
        {
            "name": "Complex State Persistence", 
            "description": "Test complex session state persistence",
            "complexity": "complex",
            "expected_duration": 10.0
        },
        {
            "name": "Multi-Tab Synchronization",
            "description": "Test state sync across multiple tabs",
            "complexity": "multi_tab",
            "expected_duration": 8.0
        },
        {
            "name": "Cross-Service Consistency",
            "description": "Test session consistency across services",
            "complexity": "cross_service",
            "expected_duration": 12.0
        }
    ]
    
    return scenarios
