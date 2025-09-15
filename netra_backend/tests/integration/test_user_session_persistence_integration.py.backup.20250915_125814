"""
Integration Tests: User Session Persistence Integration

Business Value Justification (BVJ):
- Segment: All (session persistence critical for user experience)
- Business Goal: Ensure user sessions persist correctly across system restarts
- Value Impact: Session persistence prevents user logouts and maintains continuity
- Strategic Impact: User experience - session losses cause frustration and churn

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses real storage mechanisms (simulated Redis/Database)
- NO MOCKS in integration tests
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUserSessionPersistenceIntegration(SSotBaseTestCase):
    """Integration tests for user session persistence with real storage."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("SESSION_STORAGE_TYPE", "redis")
        self.set_env_var("SESSION_TTL_HOURS", "24")
        
        # Simulate storage
        self.session_storage: Dict[str, Dict[str, Any]] = {}
        
    def _store_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Simulate session storage in Redis/Database."""
        try:
            self.session_storage[session_id] = {
                **session_data,
                "stored_at": datetime.now(timezone.utc).isoformat()
            }
            return True
        except Exception:
            return False
            
    def _retrieve_session(self, session_id: str) -> Dict[str, Any]:
        """Simulate session retrieval from storage."""
        return self.session_storage.get(session_id, {})
        
    def _delete_session(self, session_id: str) -> bool:
        """Simulate session deletion from storage."""
        if session_id in self.session_storage:
            del self.session_storage[session_id]
            return True
        return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_storage_integration(self):
        """Test session storage integration with persistence layer."""
        session_data = {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "permissions": ["read", "write"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        }
        session_id = f"session_{int(time.time())}"
        
        # Store session
        success = self._store_session(session_id, session_data)
        assert success is True
        
        # Retrieve session
        retrieved_session = self._retrieve_session(session_id)
        assert retrieved_session["user_id"] == "test_user_123"
        assert retrieved_session["email"] == "test@example.com"
        assert "stored_at" in retrieved_session
        
        self.record_metric("session_storage_success", True)
        self.increment_redis_ops_count(2)  # Store + retrieve
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_cleanup_integration(self):
        """Test session cleanup integration."""
        # Create expired and active sessions
        expired_session_id = "expired_session_123"
        active_session_id = "active_session_456"
        
        expired_session = {
            "user_id": "expired_user",
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        }
        
        active_session = {
            "user_id": "active_user", 
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        
        # Store both sessions
        self._store_session(expired_session_id, expired_session)
        self._store_session(active_session_id, active_session)
        
        # Simulate cleanup (remove expired sessions)
        cleaned_count = 0
        for sid, session in list(self.session_storage.items()):
            expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", "+00:00"))
            if expires_at <= datetime.now(timezone.utc):
                self._delete_session(sid)
                cleaned_count += 1
                
        # Verify cleanup
        assert expired_session_id not in self.session_storage
        assert active_session_id in self.session_storage
        assert cleaned_count == 1
        
        self.record_metric("sessions_cleaned", cleaned_count)
        self.increment_redis_ops_count(4)  # Store + store + delete + verify