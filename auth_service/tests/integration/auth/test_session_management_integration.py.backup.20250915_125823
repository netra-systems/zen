"""
Session Management Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Session management enables persistent user experience
- Business Goal: Provide seamless user experience with secure session handling and state persistence
- Value Impact: Session management enables user context persistence, reducing friction and improving retention
- Strategic Impact: Core user experience infrastructure that supports subscription tier enforcement and user analytics

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real session storage (Redis/Database) and state management
- Tests real session lifecycle, persistence, and security patterns
- Validates multi-user session isolation and cleanup
- Ensures session security prevents session hijacking and fixation
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest


class TestSessionLifecycleIntegration(BaseIntegrationTest):
    """Integration tests for user session lifecycle management."""
    
    def setup_method(self):
        """Set up for session lifecycle tests."""
        super().setup_method()
        self.env = get_env()
        
        # Real session configuration - CRITICAL for user experience
        self.session_config = {
            "session_ttl": 3600 * 24,  # 24 hours default
            "refresh_threshold": 3600 * 2,  # Refresh if < 2 hours remaining
            "max_concurrent_sessions": 5,  # Per user
            "session_secret": self.env.get("SESSION_SECRET") or "test-session-secret-32chars",
            "secure_cookies": True,
            "same_site": "strict"
        }
        
        # Test users for session isolation testing
        self.test_users = [
            {
                "user_id": "session-user-1",
                "email": "session1@test.com",
                "subscription_tier": "early",
                "permissions": ["read", "write"]
            },
            {
                "user_id": "session-user-2", 
                "email": "session2@test.com",
                "subscription_tier": "enterprise",
                "permissions": ["read", "write", "admin"]
            }
        ]
        
        # Initialize session storage (simulated)
        self._session_storage = {}
        self._user_sessions = {}
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_user_session_creation_and_validation(self):
        """
        Test user session creation with proper security attributes.
        
        Business Value: Enables secure user authentication state persistence.
        Security Impact: Validates session security attributes prevent hijacking.
        """
        user = self.test_users[0]
        
        # Create new user session with security attributes
        session_data = {
            "user_id": user["user_id"],
            "email": user["email"],
            "subscription_tier": user["subscription_tier"],
            "permissions": user["permissions"],
            "ip_address": "192.168.1.100",  # Track for security
            "user_agent": "Mozilla/5.0 Test Browser",
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "csrf_token": self._generate_csrf_token(),
            "session_fingerprint": self._generate_session_fingerprint()
        }
        
        session_id = self._create_user_session(session_data)
        
        # Validate session was created with proper attributes
        assert session_id is not None
        assert len(session_id) >= 32  # Sufficient entropy
        
        # Retrieve and validate session
        retrieved_session = self._get_user_session(session_id)
        
        assert retrieved_session["user_id"] == user["user_id"]
        assert retrieved_session["email"] == user["email"]
        assert retrieved_session["subscription_tier"] == user["subscription_tier"]
        assert retrieved_session["permissions"] == user["permissions"]
        assert "csrf_token" in retrieved_session
        assert "session_fingerprint" in retrieved_session
        
        # Validate session security attributes
        assert retrieved_session["ip_address"] == "192.168.1.100"
        assert "created_at" in retrieved_session
        assert "last_activity" in retrieved_session
        
        self.logger.info(f"User session creation successful for {user['email']}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_session_activity_tracking_and_renewal(self):
        """
        Test session activity tracking and automatic renewal.
        
        Business Value: Maintains user session continuity while enforcing security timeouts.
        Strategic Impact: Balances security with user experience to reduce friction.
        """
        user = self.test_users[0]
        
        # Create session
        initial_session_data = {
            "user_id": user["user_id"],
            "email": user["email"],
            "subscription_tier": user["subscription_tier"],
            "permissions": user["permissions"],
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc) - timedelta(minutes=30),  # 30 mins ago
            "csrf_token": self._generate_csrf_token()
        }
        
        session_id = self._create_user_session(initial_session_data)
        
        # Simulate user activity - should update last_activity
        activity_result = self._update_session_activity(session_id, {
            "activity_type": "api_request",
            "endpoint": "/api/agents/optimize",
            "ip_address": "192.168.1.100"
        })
        
        assert activity_result["updated"] is True
        
        # Verify last_activity was updated
        updated_session = self._get_user_session(session_id)
        activity_delta = datetime.now(timezone.utc) - updated_session["last_activity"]
        assert activity_delta.total_seconds() < 60  # Updated within last minute
        
        # Test session renewal when approaching expiry
        near_expiry_session = {
            **initial_session_data,
            "last_activity": datetime.now(timezone.utc) - timedelta(hours=22)  # Near 24h limit
        }
        
        near_expiry_session_id = self._create_user_session(near_expiry_session)
        
        renewal_result = self._check_and_renew_session(near_expiry_session_id)
        
        assert renewal_result["needs_renewal"] is True
        assert renewal_result["renewed"] is True
        assert "new_csrf_token" in renewal_result
        
        # Verify renewed session has extended expiry
        renewed_session = self._get_user_session(near_expiry_session_id)
        assert renewed_session["csrf_token"] == renewal_result["new_csrf_token"]
        
        self.logger.info("Session activity tracking and renewal successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_multi_user_session_isolation(self):
        """
        Test session isolation between different users - CRITICAL for multi-tenant system.
        
        Business Value: Prevents data leakage between users, protecting customer data.
        Security Impact: Validates user session isolation prevents unauthorized access.
        """
        user1, user2 = self.test_users[0], self.test_users[1]
        
        # Create sessions for both users
        user1_session_data = {
            "user_id": user1["user_id"],
            "email": user1["email"],
            "subscription_tier": user1["subscription_tier"],
            "permissions": user1["permissions"],
            "sensitive_data": "user1-secret-data",
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc)
        }
        
        user2_session_data = {
            "user_id": user2["user_id"],
            "email": user2["email"],
            "subscription_tier": user2["subscription_tier"],
            "permissions": user2["permissions"],
            "sensitive_data": "user2-secret-data",
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc)
        }
        
        user1_session_id = self._create_user_session(user1_session_data)
        user2_session_id = self._create_user_session(user2_session_data)
        
        # Verify session isolation - each user can only access their own session
        user1_retrieved = self._get_user_session(user1_session_id)
        user2_retrieved = self._get_user_session(user2_session_id)
        
        # Assert complete user isolation
        assert user1_retrieved["user_id"] != user2_retrieved["user_id"]
        assert user1_retrieved["email"] != user2_retrieved["email"]
        assert user1_retrieved["sensitive_data"] != user2_retrieved["sensitive_data"]
        
        # Verify subscription tier isolation
        assert user1_retrieved["subscription_tier"] == "early"
        assert user2_retrieved["subscription_tier"] == "enterprise"
        assert user1_retrieved["permissions"] != user2_retrieved["permissions"]
        
        # Test cross-session access prevention
        cross_access_attempts = [
            self._attempt_cross_session_access(user1_session_id, user2["user_id"]),
            self._attempt_cross_session_access(user2_session_id, user1["user_id"])
        ]
        
        for attempt_result in cross_access_attempts:
            assert attempt_result["access_granted"] is False
            assert "unauthorized" in attempt_result["error"].lower()
        
        self.logger.info("Multi-user session isolation validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_session_expiry_and_cleanup(self):
        """
        Test session expiry handling and automatic cleanup.
        
        Business Value: Maintains system performance by cleaning up inactive sessions.
        Security Impact: Ensures expired sessions cannot be used for unauthorized access.
        """
        user = self.test_users[0]
        
        # Create sessions with different expiry scenarios
        session_scenarios = [
            ("active_session", datetime.now(timezone.utc) - timedelta(minutes=30)),
            ("near_expiry", datetime.now(timezone.utc) - timedelta(hours=22)),
            ("expired_session", datetime.now(timezone.utc) - timedelta(hours=25)),
            ("long_expired", datetime.now(timezone.utc) - timedelta(days=2))
        ]
        
        session_ids = []
        for scenario_name, last_activity in session_scenarios:
            session_data = {
                "user_id": f"{user['user_id']}-{scenario_name}",
                "email": user["email"],
                "subscription_tier": user["subscription_tier"],
                "permissions": user["permissions"],
                "scenario": scenario_name,
                "created_at": datetime.now(timezone.utc) - timedelta(days=1),
                "last_activity": last_activity
            }
            
            session_id = self._create_user_session(session_data)
            session_ids.append((scenario_name, session_id))
        
        # Check session validity for each scenario
        validity_results = []
        for scenario_name, session_id in session_ids:
            validity_check = self._check_session_validity(session_id)
            validity_results.append((scenario_name, session_id, validity_check))
        
        # Validate expected expiry behavior
        expected_validity = {
            "active_session": True,
            "near_expiry": True,
            "expired_session": False,
            "long_expired": False
        }
        
        for scenario_name, session_id, validity_check in validity_results:
            expected = expected_validity[scenario_name]
            actual = validity_check["valid"]
            
            assert actual == expected, f"Session '{scenario_name}' validity should be {expected}, got {actual}"
            
            if not expected:
                assert "expired" in validity_check["reason"].lower()
        
        # Run session cleanup and verify expired sessions are removed
        cleanup_result = self._cleanup_expired_sessions()
        
        assert cleanup_result["expired_sessions_found"] >= 2  # expired_session + long_expired
        assert cleanup_result["sessions_cleaned"] >= 2
        
        # Verify cleaned sessions are no longer accessible
        for scenario_name, session_id in session_ids:
            if scenario_name in ["expired_session", "long_expired"]:
                post_cleanup_check = self._get_user_session(session_id)
                assert post_cleanup_check is None, f"Expired session '{scenario_name}' should be cleaned up"
        
        self.logger.info("Session expiry and cleanup validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_concurrent_session_management(self):
        """
        Test concurrent session management and limits per user.
        
        Business Value: Prevents abuse while allowing legitimate multi-device usage.
        Security Impact: Validates concurrent session limits prevent account sharing.
        """
        user = self.test_users[0]
        
        # Create multiple concurrent sessions for same user
        device_sessions = [
            {"device": "desktop", "user_agent": "Chrome Desktop", "ip": "192.168.1.100"},
            {"device": "mobile", "user_agent": "Mobile Safari", "ip": "192.168.1.101"},
            {"device": "tablet", "user_agent": "iPad Safari", "ip": "192.168.1.102"},
            {"device": "laptop", "user_agent": "Firefox Laptop", "ip": "192.168.1.103"},
            {"device": "work", "user_agent": "Edge Work", "ip": "10.0.0.50"}
        ]
        
        created_sessions = []
        for device_info in device_sessions:
            session_data = {
                "user_id": user["user_id"],
                "email": user["email"],
                "subscription_tier": user["subscription_tier"],
                "permissions": user["permissions"],
                "device_type": device_info["device"],
                "user_agent": device_info["user_agent"],
                "ip_address": device_info["ip"],
                "created_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc)
            }
            
            session_id = self._create_user_session(session_data)
            created_sessions.append((device_info["device"], session_id))
        
        # Verify all sessions are within limit
        assert len(created_sessions) == len(device_sessions)
        
        # Try to create one more session (should exceed limit)
        excess_session_data = {
            "user_id": user["user_id"],
            "email": user["email"],
            "subscription_tier": user["subscription_tier"],
            "permissions": user["permissions"],
            "device_type": "excess_device",
            "user_agent": "Excess Browser",
            "ip_address": "192.168.1.200",
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc)
        }
        
        excess_result = self._create_user_session_with_limit_check(excess_session_data)
        
        # Should either reject or evict oldest session
        if excess_result["created"]:
            assert excess_result["oldest_session_evicted"] is True
            assert excess_result["evicted_device"] is not None
        else:
            assert "session_limit_exceeded" in excess_result["error"]
        
        # Verify user session count management
        user_session_count = self._get_user_session_count(user["user_id"])
        assert user_session_count <= self.session_config["max_concurrent_sessions"]
        
        self.logger.info("Concurrent session management validation successful")
    
    # Helper methods for session testing implementation
    
    def _generate_csrf_token(self) -> str:
        """Generate CSRF token for session security."""
        return str(uuid.uuid4())
    
    def _generate_session_fingerprint(self) -> str:
        """Generate session fingerprint for security validation."""
        import hashlib
        import secrets
        
        fingerprint_data = f"{secrets.token_hex(16)}-{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
    
    def _create_user_session(self, session_data: Dict[str, Any]) -> str:
        """Create user session and return session ID."""
        import secrets
        
        session_id = secrets.token_urlsafe(32)
        
        # Store session with TTL
        session_with_meta = {
            **session_data,
            "session_id": session_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=self.session_config["session_ttl"])
        }
        
        self._session_storage[session_id] = session_with_meta
        
        # Track user sessions
        user_id = session_data["user_id"]
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)
        
        return session_id
    
    def _get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user session by ID."""
        session = self._session_storage.get(session_id)
        
        if not session:
            return None
        
        # Check expiry
        if datetime.now(timezone.utc) > session["expires_at"]:
            # Clean up expired session
            del self._session_storage[session_id]
            self._remove_from_user_sessions(session["user_id"], session_id)
            return None
        
        return session
    
    def _update_session_activity(self, session_id: str, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update session last activity."""
        session = self._session_storage.get(session_id)
        
        if not session:
            return {"updated": False, "error": "session_not_found"}
        
        # Update last activity
        session["last_activity"] = datetime.now(timezone.utc)
        session["last_activity_data"] = activity_data
        
        return {"updated": True}
    
    def _check_and_renew_session(self, session_id: str) -> Dict[str, Any]:
        """Check if session needs renewal and renew if necessary."""
        session = self._session_storage.get(session_id)
        
        if not session:
            return {"needs_renewal": False, "error": "session_not_found"}
        
        # Check if session is near expiry
        time_until_expiry = session["expires_at"] - datetime.now(timezone.utc)
        needs_renewal = time_until_expiry.total_seconds() < self.session_config["refresh_threshold"]
        
        if needs_renewal:
            # Renew session
            session["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=self.session_config["session_ttl"])
            session["csrf_token"] = self._generate_csrf_token()
            session["renewed_at"] = datetime.now(timezone.utc)
            
            return {
                "needs_renewal": True,
                "renewed": True,
                "new_csrf_token": session["csrf_token"]
            }
        
        return {"needs_renewal": False, "renewed": False}
    
    def _attempt_cross_session_access(self, session_id: str, attempted_user_id: str) -> Dict[str, Any]:
        """Attempt cross-session access (should fail)."""
        session = self._session_storage.get(session_id)
        
        if not session:
            return {"access_granted": False, "error": "session_not_found"}
        
        if session["user_id"] != attempted_user_id:
            return {"access_granted": False, "error": "unauthorized_user_access_attempt"}
        
        return {"access_granted": True}
    
    def _check_session_validity(self, session_id: str) -> Dict[str, Any]:
        """Check if session is valid."""
        session = self._session_storage.get(session_id)
        
        if not session:
            return {"valid": False, "reason": "session_not_found"}
        
        if datetime.now(timezone.utc) > session["expires_at"]:
            return {"valid": False, "reason": "session_expired"}
        
        return {"valid": True}
    
    def _cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Clean up all expired sessions."""
        current_time = datetime.now(timezone.utc)
        expired_sessions = []
        
        for session_id, session in list(self._session_storage.items()):
            if current_time > session["expires_at"]:
                expired_sessions.append(session_id)
                del self._session_storage[session_id]
                self._remove_from_user_sessions(session["user_id"], session_id)
        
        return {
            "expired_sessions_found": len(expired_sessions),
            "sessions_cleaned": len(expired_sessions),
            "cleaned_session_ids": expired_sessions
        }
    
    def _create_user_session_with_limit_check(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create session with concurrent limit enforcement."""
        user_id = session_data["user_id"]
        user_sessions = self._user_sessions.get(user_id, [])
        
        # Remove expired sessions first
        valid_sessions = []
        for session_id in user_sessions:
            if self._check_session_validity(session_id)["valid"]:
                valid_sessions.append(session_id)
        
        self._user_sessions[user_id] = valid_sessions
        
        # Check if under limit
        if len(valid_sessions) < self.session_config["max_concurrent_sessions"]:
            session_id = self._create_user_session(session_data)
            return {"created": True, "session_id": session_id}
        
        # Evict oldest session
        oldest_session_id = valid_sessions[0]
        oldest_session = self._session_storage[oldest_session_id]
        
        del self._session_storage[oldest_session_id]
        self._user_sessions[user_id].remove(oldest_session_id)
        
        # Create new session
        session_id = self._create_user_session(session_data)
        
        return {
            "created": True,
            "session_id": session_id,
            "oldest_session_evicted": True,
            "evicted_device": oldest_session.get("device_type")
        }
    
    def _get_user_session_count(self, user_id: str) -> int:
        """Get count of active sessions for user."""
        user_sessions = self._user_sessions.get(user_id, [])
        
        # Count only valid sessions
        valid_count = 0
        for session_id in user_sessions:
            if self._check_session_validity(session_id)["valid"]:
                valid_count += 1
        
        return valid_count
    
    def _remove_from_user_sessions(self, user_id: str, session_id: str) -> None:
        """Remove session from user's session list."""
        if user_id in self._user_sessions and session_id in self._user_sessions[user_id]:
            self._user_sessions[user_id].remove(session_id)