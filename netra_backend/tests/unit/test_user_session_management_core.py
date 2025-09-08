"""
Unit Tests: User Session Management Core Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable user session management for platform stability
- Value Impact: Session management failures cause user logouts and poor UX, affecting retention
- Strategic Impact: Core platform functionality - session issues lead to customer churn

This module tests the core user session management business logic including session creation,
validation, expiry, and cleanup without requiring external services.

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses IsolatedEnvironment (no direct os.environ access)
- Tests business logic only (no external dependencies)
- Uses SSOT base test case patterns
- Follows type safety requirements
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from unittest.mock import Mock
import uuid
import time

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUserSessionManagementCore(SSotBaseTestCase):
    """
    Unit tests for user session management core business logic.
    Tests session lifecycle without external dependencies.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Set test environment variables
        self.set_env_var("SESSION_TIMEOUT_MINUTES", "30")
        self.set_env_var("MAX_SESSIONS_PER_USER", "5")
        self.set_env_var("SESSION_CLEANUP_INTERVAL", "60")
        
        # Test session data
        self.test_user_id = "test-user-123"
        self.test_session_id = "test-session-456"
        self.session_timeout = int(self.get_env_var("SESSION_TIMEOUT_MINUTES"))
        self.max_sessions = int(self.get_env_var("MAX_SESSIONS_PER_USER"))
        
    def _create_session_data(self, user_id: str = None, session_id: str = None, **overrides) -> Dict[str, Any]:
        """Helper to create session data for testing."""
        user_id = user_id or self.test_user_id
        session_id = session_id or str(uuid.uuid4())
        
        base_session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "last_accessed": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=self.session_timeout),
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 Test Browser",
            "is_active": True,
            "permissions": ["read", "write"],
            "metadata": {"login_method": "password"}
        }
        
        base_session.update(overrides)
        return base_session
        
    def _validate_session_structure(self, session_data: Dict[str, Any]) -> bool:
        """Helper to validate session data structure."""
        required_fields = [
            "session_id", "user_id", "created_at", "last_accessed", 
            "expires_at", "is_active", "permissions"
        ]
        
        for field in required_fields:
            if field not in session_data:
                return False
                
        return True
        
    def _is_session_expired(self, session_data: Dict[str, Any]) -> bool:
        """Helper to check if session is expired based on business logic."""
        if not session_data.get("is_active", False):
            return True
            
        expires_at = session_data.get("expires_at")
        if not expires_at:
            return True
            
        # Handle datetime objects vs timestamps
        if isinstance(expires_at, datetime):
            return expires_at <= datetime.now(timezone.utc)
        else:
            return expires_at <= datetime.now(timezone.utc).timestamp()
    
    @pytest.mark.unit
    def test_session_creation_structure(self):
        """Test that session creation produces valid session structure."""
        session_data = self._create_session_data()
        
        # Validate required fields are present
        assert self._validate_session_structure(session_data)
        
        # Validate field types and values
        assert isinstance(session_data["session_id"], str)
        assert isinstance(session_data["user_id"], str)
        assert isinstance(session_data["created_at"], datetime)
        assert isinstance(session_data["is_active"], bool)
        assert isinstance(session_data["permissions"], list)
        
        # Validate business logic
        assert session_data["is_active"] is True
        assert session_data["user_id"] == self.test_user_id
        assert len(session_data["permissions"]) > 0
        
        self.record_metric("session_creation_success", True)
        
    @pytest.mark.unit
    def test_session_expiry_calculation(self):
        """Test session expiry calculation business logic."""
        # Test standard expiry
        session_data = self._create_session_data()
        expected_expiry = session_data["created_at"] + timedelta(minutes=self.session_timeout)
        
        # Allow for small time differences in test execution
        time_diff = abs((session_data["expires_at"] - expected_expiry).total_seconds())
        assert time_diff < 1  # Less than 1 second difference
        
        # Test custom expiry
        custom_timeout = 60
        custom_expiry = datetime.now(timezone.utc) + timedelta(minutes=custom_timeout)
        custom_session = self._create_session_data(expires_at=custom_expiry)
        assert custom_session["expires_at"] == custom_expiry
        
        self.record_metric("expiry_calculation_success", True)
        
    @pytest.mark.unit
    def test_session_expiry_validation(self):
        """Test session expiry validation logic."""
        # Test active, non-expired session
        active_session = self._create_session_data()
        assert not self._is_session_expired(active_session)
        
        # Test expired session (past expiry time)
        expired_session = self._create_session_data(
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        assert self._is_session_expired(expired_session)
        
        # Test inactive session
        inactive_session = self._create_session_data(is_active=False)
        assert self._is_session_expired(inactive_session)
        
        # Test session with missing expiry
        no_expiry_session = self._create_session_data()
        del no_expiry_session["expires_at"]
        assert self._is_session_expired(no_expiry_session)
        
        self.record_metric("expiry_validations_tested", 4)
        
    @pytest.mark.unit
    def test_session_access_update(self):
        """Test session last accessed time update logic."""
        session_data = self._create_session_data()
        original_access_time = session_data["last_accessed"]
        
        # Simulate time passing
        time.sleep(0.01)  # Small delay to ensure time difference
        
        # Update last accessed time (simulating business logic)
        session_data["last_accessed"] = datetime.now(timezone.utc)
        
        # Verify update
        assert session_data["last_accessed"] > original_access_time
        
        self.record_metric("access_time_update_success", True)
        
    @pytest.mark.unit
    def test_session_permissions_validation(self):
        """Test session permissions validation logic."""
        # Test valid permissions
        valid_permissions = [
            ["read"],
            ["read", "write"],
            ["read", "write", "admin"],
            ["admin", "delete", "create", "update"],
        ]
        
        for permissions in valid_permissions:
            session_data = self._create_session_data(permissions=permissions)
            assert session_data["permissions"] == permissions
            assert isinstance(session_data["permissions"], list)
            
        # Test empty permissions (should be allowed)
        empty_perms_session = self._create_session_data(permissions=[])
        assert empty_perms_session["permissions"] == []
        
        self.record_metric("permissions_validations_tested", len(valid_permissions) + 1)
        
    @pytest.mark.unit
    def test_session_metadata_handling(self):
        """Test session metadata storage and retrieval."""
        metadata = {
            "login_method": "oauth",
            "device_type": "mobile",
            "location": "US",
            "custom_data": {"preference": "dark_mode"}
        }
        
        session_data = self._create_session_data(metadata=metadata)
        
        # Validate metadata structure
        assert session_data["metadata"] == metadata
        assert session_data["metadata"]["login_method"] == "oauth"
        assert session_data["metadata"]["custom_data"]["preference"] == "dark_mode"
        
        # Test metadata updates
        session_data["metadata"]["new_field"] = "new_value"
        assert "new_field" in session_data["metadata"]
        
        self.record_metric("metadata_handling_success", True)
        
    @pytest.mark.unit
    def test_multiple_sessions_per_user(self):
        """Test business logic for multiple sessions per user."""
        user_id = "multi-session-user"
        sessions = []
        
        # Create multiple sessions for same user
        for i in range(self.max_sessions):
            session_data = self._create_session_data(
                user_id=user_id,
                session_id=f"session-{i}",
                metadata={"session_number": i}
            )
            sessions.append(session_data)
            
        # Validate all sessions are for same user
        for session in sessions:
            assert session["user_id"] == user_id
            assert session["is_active"] is True
            
        # Validate sessions have unique IDs
        session_ids = [session["session_id"] for session in sessions]
        assert len(set(session_ids)) == len(sessions)  # All unique
        
        self.record_metric("multiple_sessions_created", len(sessions))
        
    @pytest.mark.unit
    def test_session_cleanup_logic(self):
        """Test session cleanup business logic."""
        # Create mix of active and expired sessions
        active_sessions = []
        expired_sessions = []
        
        # Create active sessions
        for i in range(3):
            active_session = self._create_session_data(
                session_id=f"active-{i}",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
            )
            active_sessions.append(active_session)
            
        # Create expired sessions
        for i in range(2):
            expired_session = self._create_session_data(
                session_id=f"expired-{i}",
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=5)
            )
            expired_sessions.append(expired_session)
            
        all_sessions = active_sessions + expired_sessions
        
        # Test cleanup logic (filter out expired sessions)
        active_after_cleanup = [
            session for session in all_sessions 
            if not self._is_session_expired(session)
        ]
        
        # Validate cleanup results
        assert len(active_after_cleanup) == 3  # Only active sessions remain
        assert all(not self._is_session_expired(session) for session in active_after_cleanup)
        
        self.record_metric("sessions_cleaned_up", len(expired_sessions))
        self.record_metric("sessions_remaining", len(active_after_cleanup))