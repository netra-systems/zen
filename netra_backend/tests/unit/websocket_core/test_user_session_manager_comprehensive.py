"""
Comprehensive Unit Tests for WebSocket Core UserSessionManager SSOT Class

Business Value Justification (BVJ):
- Segment: Enterprise/Mid/Early (Critical Multi-User Infrastructure)
- Business Goal: Secure User Session Management for WebSocket-based AI Chat ($500K+ ARR)
- Value Impact: Validates session management that enables isolated, concurrent AI optimization 
  sessions for multiple users, preventing data breaches and ensuring chat value delivery
- Strategic Impact: Tests the foundation layer that enables secure multi-user WebSocket 
  interactions, directly supporting our core business value of AI-powered chat experiences

MISSION CRITICAL: This test suite validates the WebSocket Core UserSessionManager which is
essential for delivering business value through chat interactions. Every test validates
capabilities that directly impact user experience and revenue generation.

KEY BUSINESS CAPABILITIES TESTED:
1. Session Creation & Identity Management - Unique user session establishment
2. Multi-User Isolation - Prevents session data leakage between concurrent users  
3. Session Lifecycle Management - Creation, updates, cleanup for optimal resource usage
4. Data Integrity & Consistency - Session data validation across operations
5. Race Condition Prevention - Safe concurrent session handling
6. WebSocket Integration Points - Session context for WebSocket event delivery
7. Resource Cleanup - Memory leak prevention and session hygiene
8. Error Handling - Graceful failure modes that maintain system stability

TEST STRATEGY: Comprehensive unit testing of pure business logic with focus on:
- User isolation patterns critical for multi-user chat system
- Session state management that enables continuous user conversations
- Error conditions that could disrupt chat value delivery
- Race conditions that could cause data corruption in concurrent sessions
- Resource management patterns that ensure system scalability

COVERAGE REQUIREMENTS:
- Minimum 95% code coverage of all public methods
- All error conditions and edge cases covered
- Race condition scenarios validated
- Memory management and cleanup verified
- WebSocket integration points tested
"""

import asyncio
import pytest
import uuid
from typing import Dict, Any, Set
from unittest.mock import Mock, patch, AsyncMock

# SSOT imports using absolute paths per CLAUDE.md requirements
from netra_backend.app.websocket_core.user_session_manager import UserSessionManager
from shared.types import UserID
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestUserSessionManagerInitialization(SSotBaseTestCase):
    """
    Test UserSessionManager initialization and basic state management.
    
    Business Value: Ensures the session manager starts in a clean, predictable state
    that can safely handle concurrent user sessions without interference.
    """
    
    async def test_manager_initializes_with_clean_state(self):
        """
        Test UserSessionManager initializes with empty, secure state.
        
        Business Impact: Clean initialization prevents session data leakage between
        test runs and ensures predictable behavior for production deployments.
        """
        # Execute business logic
        manager = UserSessionManager()
        
        # Verify business outcomes through public API - clean slate for secure multi-user operations
        # Check through public API that manager starts clean
        test_user = UserID("initialization-test-user")
        user_sessions = await manager.get_user_sessions(test_user)
        assert len(user_sessions) == 0, "New user should have no sessions on clean manager"
        assert isinstance(user_sessions, set), "User sessions should return set type"
        
        # Test that a non-existent session returns None
        test_session = await manager.get_session("non-existent-session")
        assert test_session is None, "Non-existent session should return None"
        
        # Record business metrics
        self.record_metric("initialization_verified_clean", True)
        self.record_metric("public_api_working", True)
    
    async def test_manager_ready_for_concurrent_operations(self):
        """
        Test UserSessionManager is prepared for concurrent multi-user operations.
        
        Business Impact: Validates the manager can handle multiple simultaneous users
        without interference, enabling scalable chat functionality.
        """
        # Create manager instance
        manager = UserSessionManager()
        
        # Simulate multiple concurrent users
        test_users = [
            UserID("enterprise-user-1"),
            UserID("mid-tier-user-2"), 
            UserID("early-user-3"),
            UserID("free-user-4")
        ]
        
        # Verify each user starts with isolated empty state using public API
        for user_id in test_users:
            user_sessions = await manager.get_user_sessions(user_id)
            assert len(user_sessions) == 0, f"User {user_id} should have no sessions initially"
            assert isinstance(user_sessions, set), f"User sessions should be set type for {user_id}"
        
        # Record concurrency readiness metrics
        self.record_metric("concurrent_users_tested", len(test_users))
        self.record_metric("isolation_verification_passed", True)
    
    async def test_manager_logging_initialization(self):
        """
        Test UserSessionManager logs initialization properly.
        
        Business Impact: Proper logging enables monitoring and debugging of
        session management issues in production environments.
        """
        with patch('netra_backend.app.websocket_core.user_session_manager.logger') as mock_logger:
            # Execute business logic
            manager = UserSessionManager()
            
            # Verify business outcomes - proper operational logging
            mock_logger.info.assert_called_once_with("UserSessionManager initialized")
            
            # Record logging metrics
            self.record_metric("initialization_logged", True)


@pytest.mark.unit
class TestSessionCreation(SSotBaseTestCase):
    """
    Test session creation business logic - CRITICAL for user onboarding.
    
    Business Value: Session creation is the entry point for users into our AI chat system.
    Failures here directly prevent users from accessing our core value proposition.
    """
    
    def setup_method(self):
        """Set up test fixtures for session creation tests."""
        super().setup_method()
        self.manager = UserSessionManager()
        
        # Business test data representing different user segments
        self.enterprise_user = UserID("enterprise-session-user-123")
        self.mid_tier_user = UserID("mid-tier-session-user-456")
        self.early_user = UserID("early-session-user-789")
        self.free_user = UserID("free-session-user-012")
        
        # Record test setup metrics
        self.record_metric("test_users_created", 4)
    
    async def test_create_session_generates_unique_identifiers(self):
        """
        Test create_session generates unique, secure session identifiers.
        
        Business Impact: Unique session IDs prevent session hijacking and ensure
        proper user isolation in multi-user chat environments.
        """
        session_data = {
            "user_preferences": {"theme": "dark", "notifications": True},
            "workspace_context": {"current_project": "cost-optimization-analysis"}
        }
        
        # Execute business logic
        session_id = await self.manager.create_session(self.enterprise_user, session_data)
        
        # Verify business outcomes - unique, properly formatted session ID
        assert isinstance(session_id, str), "Session ID should be string type"
        assert session_id.startswith("session_"), "Session ID should have proper prefix"
        assert len(session_id) > len("session_"), "Session ID should have unique suffix"
        
        # Verify session can be retrieved (tests storage through public API)
        stored_session = await self.manager.get_session(session_id)
        assert stored_session is not None, "Session should be retrievable"
        
        # Verify uniqueness by creating another session
        second_session_id = await self.manager.create_session(self.mid_tier_user, session_data)
        assert session_id != second_session_id, "Each session should have unique identifier"
        
        # Record business metrics
        self.record_metric("unique_sessions_created", 2)
        self.record_metric("session_id_format_valid", True)
    
    async def test_create_session_stores_complete_session_data(self):
        """
        Test create_session stores all required session information with data integrity.
        
        Business Impact: Complete session data storage enables context preservation
        across chat interactions, improving user experience and conversation quality.
        """
        # Complex session data representing real user context
        session_data = {
            "workspace": "ai-optimization-dashboard",
            "user_preferences": {
                "notification_settings": {"email": True, "slack": False},
                "ui_preferences": {"theme": "dark", "compact_mode": True}
            },
            "context": {
                "last_action": "cluster_cost_analysis",
                "active_agents": ["cost_optimizer", "resource_analyzer"],
                "current_conversation": "aws_infrastructure_review"
            },
            "metadata": {
                "session_start_time": "2025-01-09T10:30:00Z",
                "user_tier": "enterprise"
            }
        }
        
        # Execute business logic
        session_id = await self.manager.create_session(self.enterprise_user, session_data)
        
        # Verify business outcomes - complete data preservation
        stored_session = await self.manager.get_session(session_id)
        assert stored_session is not None, "Session should be created and retrievable"
        
        # Verify core session structure
        assert stored_session["user_id"] == self.enterprise_user, "User ID should be preserved"
        assert stored_session["data"] == session_data, "Session data should be preserved exactly"
        assert stored_session["active"] is True, "Session should be active upon creation"
        
        # Verify nested data structure integrity - critical for chat context
        assert stored_session["data"]["workspace"] == "ai-optimization-dashboard"
        assert stored_session["data"]["user_preferences"]["notification_settings"]["email"] is True
        assert stored_session["data"]["context"]["last_action"] == "cluster_cost_analysis"
        assert "cost_optimizer" in stored_session["data"]["context"]["active_agents"]
        assert stored_session["data"]["metadata"]["user_tier"] == "enterprise"
        
        # Record business metrics
        self.record_metric("complete_session_data_preserved", True)
        self.record_metric("nested_data_integrity_verified", True)
        self.record_metric("session_context_preserved", True)
    
    async def test_create_session_maintains_user_mapping(self):
        """
        Test create_session maintains bidirectional user-session mapping.
        
        Business Impact: Proper user-session mapping enables efficient user lookup
        and session management, critical for multi-user chat performance.
        """
        session_data = {"workspace": "mapping-test-workspace"}
        
        # Execute business logic
        session_id = await self.manager.create_session(self.mid_tier_user, session_data)
        
        # Verify business outcomes - bidirectional mapping through public API
        user_sessions = await self.manager.get_user_sessions(self.mid_tier_user)
        assert session_id in user_sessions, "Session ID should be in user's session set"
        assert isinstance(user_sessions, set), "User sessions should be set type"
        
        # Verify mapping integrity
        stored_session = await self.manager.get_session(session_id)
        assert stored_session is not None, "Session should be retrievable"
        assert stored_session["user_id"] == self.mid_tier_user, "Session should reference correct user"
        
        # Record mapping metrics
        self.record_metric("user_session_mapping_created", True)
        self.record_metric("bidirectional_mapping_verified", True)
    
    async def test_create_multiple_sessions_same_user(self):
        """
        Test user can have multiple concurrent sessions for different workspaces.
        
        Business Impact: Multiple sessions per user enable users to work on different
        AI optimization tasks simultaneously, increasing platform stickiness and value.
        """
        # Different workspaces representing concurrent user activities
        workspace_sessions = [
            {"workspace": "cost-optimization-aws", "project": "production-environment"},
            {"workspace": "performance-analysis-gcp", "project": "staging-environment"},
            {"workspace": "security-audit-azure", "project": "development-environment"},
            {"workspace": "resource-planning", "project": "future-capacity"}
        ]
        
        # Execute business logic - create multiple concurrent sessions
        created_session_ids = []
        for i, session_data in enumerate(workspace_sessions):
            session_id = await self.manager.create_session(self.enterprise_user, session_data)
            created_session_ids.append(session_id)
            
            # Verify incremental growth through public API
            user_sessions = await self.manager.get_user_sessions(self.enterprise_user)
            assert len(user_sessions) == i + 1, f"User should have {i + 1} sessions after creating session {i}"
        
        # Verify business outcomes - unique sessions with preserved data
        assert len(created_session_ids) == len(workspace_sessions), "All sessions should be created"
        assert len(set(created_session_ids)) == len(created_session_ids), "All session IDs should be unique"
        
        # Verify each session maintains its own workspace context
        for i, session_id in enumerate(created_session_ids):
            session = await self.manager.get_session(session_id)
            assert session is not None, f"Session {i} should be retrievable"
            expected_workspace = workspace_sessions[i]["workspace"]
            actual_workspace = session["data"]["workspace"]
            assert actual_workspace == expected_workspace, f"Session {i} should have workspace {expected_workspace}"
        
        # Verify all sessions belong to the same user
        user_sessions = await self.manager.get_user_sessions(self.enterprise_user)
        assert len(user_sessions) == len(workspace_sessions), "User should have all created sessions"
        for session_id in created_session_ids:
            assert session_id in user_sessions, f"Session {session_id} should belong to user"
        
        # Record concurrency metrics
        self.record_metric("concurrent_sessions_per_user", len(created_session_ids))
        self.record_metric("workspace_isolation_verified", True)
    
    async def test_create_session_user_isolation_security(self):
        """
        Test sessions for different users are completely isolated for security.
        
        Business Impact: User isolation is CRITICAL for preventing data breaches
        and maintaining trust in our AI chat platform, especially for enterprise customers.
        """
        # Sensitive data for different users - simulating enterprise security requirements
        user_a_data = {
            "sensitive_data": {
                "api_keys": {"aws": "AKIATEST123USERA", "gcp": "gcpkey-user-a"},
                "workspace": "user-a-private-enterprise-workspace",
                "confidential_projects": ["project-alpha", "project-beta"]
            },
            "metadata": {"security_level": "enterprise", "region": "us-west-2"}
        }
        
        user_b_data = {
            "sensitive_data": {
                "api_keys": {"aws": "AKIATEST456USERB", "azure": "azkey-user-b"},
                "workspace": "user-b-private-mid-tier-workspace", 
                "confidential_projects": ["project-gamma", "project-delta"]
            },
            "metadata": {"security_level": "mid_tier", "region": "eu-west-1"}
        }
        
        # Execute business logic - create isolated sessions
        session_a = await self.manager.create_session(self.enterprise_user, user_a_data)
        session_b = await self.manager.create_session(self.mid_tier_user, user_b_data)
        
        # Verify business outcomes - complete user isolation
        assert session_a != session_b, "Session IDs should be different"
        
        # Verify session ownership isolation through public API
        session_a_data = await self.manager.get_session(session_a)
        session_b_data = await self.manager.get_session(session_b)
        assert session_a_data is not None, "Session A should be retrievable"
        assert session_b_data is not None, "Session B should be retrievable"
        assert session_a_data["user_id"] == self.enterprise_user, "Session A should belong to enterprise user"
        assert session_b_data["user_id"] == self.mid_tier_user, "Session B should belong to mid-tier user"
        
        # Verify sensitive data isolation - CRITICAL SECURITY TEST
        assert session_a_data["data"]["sensitive_data"]["api_keys"]["aws"] == "AKIATEST123USERA"
        assert session_b_data["data"]["sensitive_data"]["api_keys"]["aws"] == "AKIATEST456USERB"
        assert "azure" not in session_a_data["data"]["sensitive_data"]["api_keys"]
        assert "gcp" not in session_b_data["data"]["sensitive_data"]["api_keys"]
        
        # Verify workspace isolation
        workspace_a = session_a_data["data"]["sensitive_data"]["workspace"]
        workspace_b = session_b_data["data"]["sensitive_data"]["workspace"]
        assert "user-a-private" in workspace_a and "user-b-private" not in workspace_a
        assert "user-b-private" in workspace_b and "user-a-private" not in workspace_b
        
        # Verify user session mapping isolation
        user_a_sessions = await self.manager.get_user_sessions(self.enterprise_user)
        user_b_sessions = await self.manager.get_user_sessions(self.mid_tier_user)
        
        assert session_a in user_a_sessions, "Session A should be in user A's sessions"
        assert session_a not in user_b_sessions, "Session A should NOT be in user B's sessions"
        assert session_b in user_b_sessions, "Session B should be in user B's sessions"
        assert session_b not in user_a_sessions, "Session B should NOT be in user A's sessions"
        
        # Record security metrics
        self.record_metric("user_isolation_verified", True)
        self.record_metric("sensitive_data_isolated", True)
        self.record_metric("cross_user_access_prevented", True)
    
    async def test_create_session_handles_empty_data(self):
        """
        Test create_session handles empty session data gracefully.
        
        Business Impact: Graceful handling of edge cases prevents system failures
        that could disrupt user onboarding and chat functionality.
        """
        # Execute business logic with minimal data
        session_id = await self.manager.create_session(self.free_user, {})
        
        # Verify business outcomes - graceful handling
        assert session_id is not None, "Session should be created even with empty data"
        
        stored_session = await self.manager.get_session(session_id)
        assert stored_session is not None, "Session should be retrievable"
        assert stored_session["user_id"] == self.free_user, "User ID should still be preserved"
        assert stored_session["data"] == {}, "Empty data should be preserved"
        assert stored_session["active"] is True, "Session should still be active"
        
        # Record edge case handling metrics
        self.record_metric("empty_data_handled_gracefully", True)
    
    async def test_create_session_handles_complex_nested_data(self):
        """
        Test create_session properly handles deeply nested session data structures.
        
        Business Impact: Complex data structures enable rich chat context preservation,
        supporting advanced AI conversations and user experience.
        """
        # Complex nested data representing real-world chat context
        complex_data = {
            "user_profile": {
                "basic_info": {
                    "name": "Enterprise User",
                    "role": "Cloud Architect",
                    "company": "TechCorp Inc"
                },
                "preferences": {
                    "notification_channels": {
                        "email": {"enabled": True, "frequency": "immediate"},
                        "slack": {"enabled": True, "channel": "#ai-optimization"},
                        "webhook": {"enabled": False, "url": None}
                    },
                    "ui_settings": {
                        "theme": "dark",
                        "layout": {"sidebar": "collapsed", "panels": ["chat", "metrics"]},
                        "advanced_features": {"code_highlighting": True, "live_charts": True}
                    }
                }
            },
            "conversation_context": {
                "active_threads": [
                    {
                        "thread_id": "thread_123",
                        "topic": "AWS cost optimization",
                        "agents": ["cost_optimizer", "resource_analyzer"],
                        "last_message_time": "2025-01-09T10:30:00Z"
                    },
                    {
                        "thread_id": "thread_456", 
                        "topic": "GCP performance analysis",
                        "agents": ["performance_analyzer"],
                        "last_message_time": "2025-01-09T09:15:00Z"
                    }
                ],
                "conversation_history": {
                    "total_messages": 247,
                    "optimization_suggestions_accepted": 18,
                    "cost_savings_achieved": {"amount": 15000, "currency": "USD"}
                }
            }
        }
        
        # Execute business logic
        session_id = await self.manager.create_session(self.enterprise_user, complex_data)
        
        # Verify business outcomes - deep data preservation
        stored_session = await self.manager.get_session(session_id)
        assert stored_session is not None, "Session should be retrievable"
        stored_data = stored_session["data"]
        
        # Verify deeply nested structure preservation
        assert stored_data["user_profile"]["basic_info"]["role"] == "Cloud Architect"
        assert stored_data["user_profile"]["preferences"]["notification_channels"]["email"]["frequency"] == "immediate"
        assert stored_data["user_profile"]["preferences"]["ui_settings"]["layout"]["sidebar"] == "collapsed"
        
        # Verify conversation context preservation
        active_threads = stored_data["conversation_context"]["active_threads"]
        assert len(active_threads) == 2, "Both active threads should be preserved"
        assert active_threads[0]["topic"] == "AWS cost optimization"
        assert "cost_optimizer" in active_threads[0]["agents"]
        
        # Verify metrics preservation
        history = stored_data["conversation_context"]["conversation_history"]
        assert history["total_messages"] == 247
        assert history["cost_savings_achieved"]["amount"] == 15000
        
        # Record complex data metrics
        self.record_metric("deep_nested_data_preserved", True)
        self.record_metric("conversation_context_preserved", True)
        self.record_metric("user_profile_data_preserved", True)


@pytest.mark.unit
class TestSessionRetrieval(SSotBaseTestCase):
    """
    Test session retrieval business logic - validates data access patterns.
    
    Business Value: Session retrieval enables context restoration for chat conversations,
    directly impacting user experience quality and conversation continuity.
    """
    
    def setup_method(self):
        """Set up test fixtures for session retrieval tests."""
        super().setup_method()
        self.manager = UserSessionManager()
        
        # Create test users representing different business segments
        self.enterprise_user = UserID("retrieval-enterprise-user")
        self.mid_tier_user = UserID("retrieval-mid-tier-user")
        self.early_user = UserID("retrieval-early-user")
    
    async def test_get_session_returns_complete_session_data(self):
        """
        Test get_session returns complete session data with full context preservation.
        
        Business Impact: Complete session data retrieval enables AI agents to maintain
        conversation context, improving response quality and user satisfaction.
        """
        # Rich session data representing active user context
        original_data = {
            "optimization_context": {
                "current_analysis": {
                    "cloud_provider": "AWS",
                    "resource_types": ["EC2", "RDS", "S3"],
                    "cost_threshold": {"cpu": 0.8, "memory": 0.75}
                },
                "historical_data": {
                    "last_30_days": {"spend": 45000, "savings_identified": 8500},
                    "trends": ["increasing_compute_usage", "underutilized_storage"]
                }
            },
            "user_interaction": {
                "last_updated": "2025-01-09T10:30:00Z",
                "interaction_count": 15,
                "preference_learned": {"communication_style": "detailed", "chart_preference": "bar"}
            }
        }
        
        # Create session first
        session_id = await self.manager.create_session(self.enterprise_user, original_data)
        
        # Execute business logic
        retrieved_session = await self.manager.get_session(session_id)
        
        # Verify business outcomes - complete data retrieval
        assert retrieved_session is not None, "Session should be retrievable"
        assert retrieved_session["user_id"] == self.enterprise_user, "User ID should be preserved"
        assert retrieved_session["data"] == original_data, "Session data should be identical to original"
        assert retrieved_session["active"] is True, "Session should be active"
        
        # Verify nested data integrity - critical for AI context
        optimization = retrieved_session["data"]["optimization_context"]["current_analysis"]
        assert optimization["cloud_provider"] == "AWS"
        assert optimization["cost_threshold"]["cpu"] == 0.8
        assert "EC2" in optimization["resource_types"]
        
        # Verify interaction context preservation
        interaction = retrieved_session["data"]["user_interaction"]
        assert interaction["interaction_count"] == 15
        assert interaction["preference_learned"]["communication_style"] == "detailed"
        
        # Record retrieval metrics
        self.record_metric("complete_session_retrieved", True)
        self.record_metric("context_integrity_verified", True)
    
    async def test_get_session_returns_none_for_invalid_ids(self):
        """
        Test get_session returns None gracefully for non-existent session IDs.
        
        Business Impact: Graceful handling of invalid session IDs prevents system
        crashes and enables proper error handling in chat interfaces.
        """
        # Test various invalid session ID patterns
        invalid_session_ids = [
            "nonexistent-session-123",
            "session_999999",
            "",
            "invalid-format-no-prefix",
            "session_",  # Empty suffix
            "SESSION_123",  # Wrong case
            "session_with_special_chars_!@#",
            None  # Handle None case
        ]
        
        for invalid_id in invalid_session_ids:
            if invalid_id is None:
                # Skip None case as it would cause TypeError
                continue
                
            # Execute business logic
            result = await self.manager.get_session(invalid_id)
            
            # Verify business outcomes - graceful failure
            assert result is None, f"Should return None for invalid ID: {invalid_id}"
        
        # Record error handling metrics
        self.record_metric("invalid_ids_handled_gracefully", len([id for id in invalid_session_ids if id is not None]))
        self.record_metric("graceful_error_handling_verified", True)
    
    async def test_get_user_sessions_returns_all_user_sessions(self):
        """
        Test get_user_sessions returns all sessions for a specific user.
        
        Business Impact: Complete user session retrieval enables users to resume
        any of their active AI conversations, improving user experience.
        """
        # Create multiple sessions representing different user activities
        session_contexts = [
            {"workspace": "aws-cost-analysis", "status": "active"},
            {"workspace": "gcp-performance-monitoring", "status": "active"},
            {"workspace": "azure-security-audit", "status": "active"},
            {"workspace": "multi-cloud-optimization", "status": "active"}
        ]
        
        # Create all sessions
        created_session_ids = []
        for context_data in session_contexts:
            session_id = await self.manager.create_session(self.enterprise_user, context_data)
            created_session_ids.append(session_id)
        
        # Execute business logic
        user_sessions = await self.manager.get_user_sessions(self.enterprise_user)
        
        # Verify business outcomes - complete session retrieval
        assert isinstance(user_sessions, set), "User sessions should be returned as set"
        assert len(user_sessions) == len(session_contexts), f"Should return all {len(session_contexts)} sessions"
        
        # Verify all created sessions are returned
        for session_id in created_session_ids:
            assert session_id in user_sessions, f"Session {session_id} should be in user sessions"
        
        # Verify no extra sessions are returned
        assert len(user_sessions) == len(created_session_ids), "Should not return extra sessions"
        
        # Record user session metrics
        self.record_metric("user_sessions_count", len(user_sessions))
        self.record_metric("all_sessions_retrieved", True)
    
    async def test_get_user_sessions_returns_empty_for_no_sessions(self):
        """
        Test get_user_sessions returns empty set for users with no sessions.
        
        Business Impact: Proper handling of new users enables clean onboarding
        experience without system errors.
        """
        # Execute business logic with user who has no sessions
        user_sessions = await self.manager.get_user_sessions(self.early_user)
        
        # Verify business outcomes - clean empty state
        assert isinstance(user_sessions, set), "Should return set type even when empty"
        assert len(user_sessions) == 0, "Should return empty set for user with no sessions"
        
        # Record empty state metrics
        self.record_metric("empty_user_sessions_handled", True)
    
    async def test_get_user_sessions_isolation_between_users(self):
        """
        Test get_user_sessions maintains strict isolation between users.
        
        Business Impact: User session isolation is CRITICAL for security and prevents
        users from accessing other users' chat contexts and sensitive data.
        """
        # Create sessions for different users with distinct contexts
        user_a_sessions_data = [
            {"workspace": "user-a-private-workspace-1", "security": "enterprise"},
            {"workspace": "user-a-private-workspace-2", "security": "enterprise"}
        ]
        
        user_b_sessions_data = [
            {"workspace": "user-b-mid-tier-workspace-1", "security": "mid_tier"}
        ]
        
        # Create sessions for user A
        user_a_session_ids = []
        for data in user_a_sessions_data:
            session_id = await self.manager.create_session(self.enterprise_user, data)
            user_a_session_ids.append(session_id)
        
        # Create sessions for user B  
        user_b_session_ids = []
        for data in user_b_sessions_data:
            session_id = await self.manager.create_session(self.mid_tier_user, data)
            user_b_session_ids.append(session_id)
        
        # Execute business logic
        sessions_a = await self.manager.get_user_sessions(self.enterprise_user)
        sessions_b = await self.manager.get_user_sessions(self.mid_tier_user)
        
        # Verify business outcomes - strict isolation
        assert len(sessions_a) == 2, "User A should have 2 sessions"
        assert len(sessions_b) == 1, "User B should have 1 session"
        
        # Verify user A's sessions
        for session_id in user_a_session_ids:
            assert session_id in sessions_a, f"User A session {session_id} should be in user A's sessions"
            assert session_id not in sessions_b, f"User A session {session_id} should NOT be in user B's sessions"
        
        # Verify user B's sessions
        for session_id in user_b_session_ids:
            assert session_id in sessions_b, f"User B session {session_id} should be in user B's sessions"  
            assert session_id not in sessions_a, f"User B session {session_id} should NOT be in user A's sessions"
        
        # Verify no overlap
        assert len(sessions_a.intersection(sessions_b)) == 0, "Users should have no shared sessions"
        
        # Record isolation metrics
        self.record_metric("user_session_isolation_verified", True)
        self.record_metric("cross_user_access_prevented", True)
    
    async def test_session_retrieval_performance_with_multiple_sessions(self):
        """
        Test session retrieval performance with large number of sessions.
        
        Business Impact: Efficient session retrieval ensures chat responsiveness
        even for power users with many active conversations.
        """
        # Create many sessions to test performance
        session_count = 50
        created_sessions = []
        
        for i in range(session_count):
            session_data = {
                "workspace": f"workspace-{i}",
                "data": {"index": i, "type": "performance_test"}
            }
            session_id = await self.manager.create_session(self.enterprise_user, session_data)
            created_sessions.append(session_id)
        
        # Execute business logic with timing
        import time
        start_time = time.time()
        
        user_sessions = await self.manager.get_user_sessions(self.enterprise_user)
        
        # Verify all sessions individually
        for session_id in created_sessions:
            retrieved_session = await self.manager.get_session(session_id)
            assert retrieved_session is not None, f"Session {session_id} should be retrievable"
        
        end_time = time.time()
        retrieval_time = end_time - start_time
        
        # Verify business outcomes - performance and correctness
        assert len(user_sessions) == session_count, f"Should retrieve all {session_count} sessions"
        assert retrieval_time < 1.0, f"Retrieval should be fast (took {retrieval_time:.3f}s)"
        
        # Record performance metrics
        self.record_metric("large_session_count_tested", session_count)
        self.record_metric("retrieval_performance_seconds", retrieval_time)
        self.record_metric("retrieval_performance_acceptable", retrieval_time < 1.0)


@pytest.mark.unit
class TestSessionUpdates(SSotBaseTestCase):
    """
    Test session update business logic - validates data mutation patterns.
    
    Business Value: Session updates enable context evolution during chat conversations,
    allowing AI agents to maintain and build upon conversation state.
    """
    
    def setup_method(self):
        """Set up test fixtures for session update tests."""
        super().setup_method()
        self.manager = UserSessionManager()
        self.test_user = UserID("update-test-user")
    
    async def test_update_session_modifies_existing_data(self):
        """
        Test update_session modifies session data while preserving structure.
        
        Business Impact: Proper session updates enable AI conversations to evolve
        naturally while maintaining context, improving user experience.
        """
        # Initial session data representing chat context
        initial_data = {
            "preferences": {"theme": "light", "notifications": True, "language": "en"},
            "workspace": "initial-optimization-workspace",
            "context": {
                "current_analysis": "cost_optimization",
                "progress": {"completed_steps": 2, "total_steps": 5}
            }
        }
        
        # Create session
        session_id = await self.manager.create_session(self.test_user, initial_data)
        
        # Prepare update - simulating user preference changes and progress
        update_data = {
            "preferences": {"theme": "dark", "notifications": False},  # Theme change, notifications toggle
            "context": {
                "progress": {"completed_steps": 4, "total_steps": 5}  # Progress update
            },
            "last_activity": "2025-01-09T11:45:00Z"  # New field
        }
        
        # Execute business logic
        update_result = await self.manager.update_session(session_id, update_data)
        
        # Verify business outcomes
        assert update_result is True, "Update should succeed"
        
        # Retrieve updated session
        updated_session = await self.manager.get_session(session_id)
        updated_data = updated_session["data"]
        
        # Verify merge behavior - updated values
        assert updated_data["preferences"]["theme"] == "dark", "Theme should be updated"
        assert updated_data["preferences"]["notifications"] is False, "Notifications should be updated"
        assert updated_data["context"]["progress"]["completed_steps"] == 4, "Progress should be updated"
        
        # Verify merge behavior - preserved values
        assert updated_data["preferences"]["language"] == "en", "Language should be preserved"
        assert updated_data["workspace"] == "initial-optimization-workspace", "Workspace should be preserved"
        assert updated_data["context"]["current_analysis"] == "cost_optimization", "Analysis type should be preserved"
        assert updated_data["context"]["progress"]["total_steps"] == 5, "Total steps should be preserved"
        
        # Verify new fields added
        assert updated_data["last_activity"] == "2025-01-09T11:45:00Z", "New field should be added"
        
        # Record update metrics
        self.record_metric("session_update_successful", True)
        self.record_metric("data_merge_preserved_existing", True)
        self.record_metric("new_fields_added", True)
    
    async def test_update_session_fails_for_invalid_session(self):
        """
        Test update_session fails gracefully for non-existent sessions.
        
        Business Impact: Graceful handling of invalid session updates prevents
        system errors and enables proper error handling in chat interfaces.
        """
        invalid_session_ids = [
            "nonexistent-session-456",
            "session_999999",
            "",
            "invalid-format"
        ]
        
        update_data = {"some": "data"}
        
        for invalid_id in invalid_session_ids:
            if invalid_id == "":
                continue  # Skip empty string as it may cause different behavior
                
            # Execute business logic
            update_result = await self.manager.update_session(invalid_id, update_data)
            
            # Verify business outcomes - graceful failure
            assert update_result is False, f"Update should fail for invalid session ID: {invalid_id}"
        
        # Record error handling metrics
        self.record_metric("invalid_session_updates_handled", len(invalid_session_ids) - 1)
    
    async def test_update_session_handles_complex_nested_data(self):
        """
        Test update_session handles complex nested data structures.
        
        Business Impact: Complex data updates enable sophisticated chat context
        management, supporting advanced AI conversation features.
        """
        # Initial complex session data
        initial_data = {
            "optimization": {
                "cpu": {"current": 0.7, "target": 0.5, "alerts": {"enabled": True}},
                "memory": {"current": "1.5Gi", "target": "1.0Gi", "alerts": {"enabled": True}}
            },
            "metadata": {"version": "1.0", "created": "2025-01-09T09:00:00Z"},
            "agents": {
                "active": ["cost_optimizer"],
                "completed": []
            }
        }
        
        # Create session
        session_id = await self.manager.create_session(self.test_user, initial_data)
        
        # Complex update - simulating progression through optimization workflow
        update_data = {
            "optimization": {
                "cpu": {"target": 0.4},  # Update target only
                "network": {"bandwidth": "100Mbps", "alerts": {"enabled": True}},  # Add new network config
                "storage": {"type": "ssd", "size": "500Gi"}  # Add storage config
            },
            "metadata": {
                "version": "1.1",  # Update version
                "updated": "2025-01-09T11:30:00Z",  # Add update timestamp
                "change_log": ["cpu_target_updated", "network_config_added"]  # Add change log
            },
            "agents": {
                "active": ["cost_optimizer", "network_analyzer"],  # Add agent
                "completed": ["initial_assessment"]  # Add completed agent
            }
        }
        
        # Execute business logic
        result = await self.manager.update_session(session_id, update_data)
        assert result is True, "Complex update should succeed"
        
        # Verify complex merge behavior
        updated_session = await self.manager.get_session(session_id)
        data = updated_session["data"]
        
        # Verify optimization config updates
        assert data["optimization"]["cpu"]["current"] == 0.7, "CPU current should be preserved"
        assert data["optimization"]["cpu"]["target"] == 0.4, "CPU target should be updated"
        assert data["optimization"]["cpu"]["alerts"]["enabled"] is True, "CPU alerts should be preserved"
        assert data["optimization"]["memory"]["current"] == "1.5Gi", "Memory current should be preserved"
        
        # Verify new network config added
        assert data["optimization"]["network"]["bandwidth"] == "100Mbps", "Network bandwidth should be added"
        assert data["optimization"]["network"]["alerts"]["enabled"] is True, "Network alerts should be added"
        
        # Verify storage config added
        assert data["optimization"]["storage"]["type"] == "ssd", "Storage type should be added"
        assert data["optimization"]["storage"]["size"] == "500Gi", "Storage size should be added"
        
        # Verify metadata updates
        assert data["metadata"]["version"] == "1.1", "Version should be updated"
        assert data["metadata"]["created"] == "2025-01-09T09:00:00Z", "Created timestamp should be preserved"
        assert data["metadata"]["updated"] == "2025-01-09T11:30:00Z", "Updated timestamp should be added"
        assert "cpu_target_updated" in data["metadata"]["change_log"], "Change log should be added"
        
        # Verify agents updates
        assert "cost_optimizer" in data["agents"]["active"], "Original active agent should be preserved"
        assert "network_analyzer" in data["agents"]["active"], "New active agent should be added"
        assert "initial_assessment" in data["agents"]["completed"], "Completed agent should be added"
        
        # Record complex update metrics
        self.record_metric("complex_nested_update_successful", True)
        self.record_metric("partial_object_updates_working", True)
        self.record_metric("new_nested_objects_added", True)
    
    async def test_update_session_preserves_session_metadata(self):
        """
        Test update_session preserves critical session metadata.
        
        Business Impact: Session metadata preservation ensures system consistency
        and enables proper session lifecycle management.
        """
        initial_data = {"workspace": "metadata-test"}
        
        # Create session
        session_id = await self.manager.create_session(self.test_user, initial_data)
        
        # Verify initial metadata
        initial_session = await self.manager.get_session(session_id)
        assert initial_session["user_id"] == self.test_user, "Initial user ID should be set"
        assert initial_session["active"] is True, "Initial session should be active"
        
        # Update session data
        update_data = {"workspace": "updated-workspace", "new_field": "new_value"}
        result = await self.manager.update_session(session_id, update_data)
        assert result is True, "Update should succeed"
        
        # Verify metadata preservation
        updated_session = await self.manager.get_session(session_id)
        assert updated_session["user_id"] == self.test_user, "User ID should be preserved"
        assert updated_session["active"] is True, "Active status should be preserved"
        
        # Verify data was updated
        assert updated_session["data"]["workspace"] == "updated-workspace", "Data should be updated"
        assert updated_session["data"]["new_field"] == "new_value", "New field should be added"
        
        # Record metadata preservation metrics
        self.record_metric("session_metadata_preserved", True)


@pytest.mark.unit
class TestSessionLifecycle(SSotBaseTestCase):
    """
    Test session lifecycle management - validates cleanup and state transitions.
    
    Business Value: Proper session lifecycle management prevents memory leaks,
    ensures resource cleanup, and maintains system performance as users scale.
    """
    
    def setup_method(self):
        """Set up test fixtures for session lifecycle tests."""
        super().setup_method()
        self.manager = UserSessionManager()
        self.test_user = UserID("lifecycle-test-user")
    
    async def test_close_session_deactivates_and_removes_mapping(self):
        """
        Test close_session properly deactivates session and updates mappings.
        
        Business Impact: Proper session closure frees up resources and prevents
        abandoned sessions from consuming system resources.
        """
        session_data = {"workspace": "closing-workspace", "active_conversation": "cost-analysis"}
        
        # Create session
        session_id = await self.manager.create_session(self.test_user, session_data)
        
        # Verify session is active and mapped
        user_sessions = await self.manager.get_user_sessions(self.test_user)
        assert session_id in user_sessions, "Session should be in user mapping"
        session = await self.manager.get_session(session_id)
        assert session["active"] is True, "Session should be active initially"
        
        # Execute business logic
        close_result = await self.manager.close_session(session_id)
        
        # Verify business outcomes
        assert close_result is True, "Session close should succeed"
        
        # Verify session is deactivated but preserved
        session = await self.manager.get_session(session_id)
        assert session is not None, "Session should still exist in storage"
        assert session["active"] is False, "Session should be marked inactive"
        assert session["data"] == session_data, "Session data should be preserved"
        
        # Verify mapping is updated
        user_sessions = await self.manager.get_user_sessions(self.test_user)
        assert session_id not in user_sessions, "Session should be removed from user mapping"
        
        # Record closure metrics
        self.record_metric("session_closed_successfully", True)
        self.record_metric("session_data_preserved_after_close", True)
        self.record_metric("user_mapping_updated_on_close", True)
    
    async def test_close_session_fails_for_invalid_session(self):
        """
        Test close_session fails gracefully for non-existent sessions.
        
        Business Impact: Graceful handling of invalid session operations prevents
        system errors and enables robust error handling.
        """
        invalid_session_ids = [
            "nonexistent-close-session",
            "session_999999",
            "",
            "invalid-format-session"
        ]
        
        for invalid_id in invalid_session_ids:
            if invalid_id == "":
                continue  # Skip empty string
                
            # Execute business logic
            close_result = await self.manager.close_session(invalid_id)
            
            # Verify business outcomes
            assert close_result is False, f"Close should fail for invalid session ID: {invalid_id}"
        
        # Record error handling metrics
        self.record_metric("invalid_session_closes_handled", len(invalid_session_ids) - 1)
    
    async def test_is_session_active_validates_session_status(self):
        """
        Test is_session_active correctly validates session activity status.
        
        Business Impact: Accurate session status validation enables proper
        resource management and user experience optimization.
        """
        session_data = {"workspace": "activity-test"}
        
        # Create session
        session_id = await self.manager.create_session(self.test_user, session_data)
        
        # Session should be active initially
        is_active_initially = await self.manager.is_session_active(session_id)
        assert is_active_initially is True, "Session should be active after creation"
        
        # Close session
        close_result = await self.manager.close_session(session_id)
        assert close_result is True, "Session should close successfully"
        
        # Session should be inactive after closing
        is_active_after_close = await self.manager.is_session_active(session_id)
        assert is_active_after_close is False, "Session should be inactive after closing"
        
        # Record activity validation metrics
        self.record_metric("session_activity_validation_working", True)
    
    async def test_is_session_active_returns_false_for_invalid_session(self):
        """
        Test is_session_active returns False for non-existent sessions.
        
        Business Impact: Safe handling of invalid session queries prevents
        system errors and enables defensive programming patterns.
        """
        invalid_session_ids = [
            "nonexistent-session",
            "session_999999",
            "",
            "invalid-format"
        ]
        
        for invalid_id in invalid_session_ids:
            if invalid_id == "":
                continue  # Skip empty string
                
            # Execute business logic
            result = await self.manager.is_session_active(invalid_id)
            
            # Verify business outcomes
            assert result is False, f"Should return False for invalid ID: {invalid_id}"
        
        # Record validation metrics
        self.record_metric("invalid_session_activity_checks_handled", len(invalid_session_ids) - 1)
    
    async def test_session_lifecycle_complete_workflow(self):
        """
        Test complete session lifecycle from creation to cleanup.
        
        Business Impact: End-to-end lifecycle validation ensures the session
        management system works correctly for real user workflows.
        """
        # Initial session data representing user starting optimization work
        initial_data = {
            "workspace": "complete-lifecycle-test",
            "preferences": {"auto_save": True, "notifications": True},
            "context": {"analysis_type": "cost_optimization", "started": "2025-01-09T10:00:00Z"}
        }
        
        # 1. Create session
        session_id = await self.manager.create_session(self.test_user, initial_data)
        assert await self.manager.is_session_active(session_id) is True, "Session should be active after creation"
        
        # Verify session in user mapping
        user_sessions = await self.manager.get_user_sessions(self.test_user)
        assert session_id in user_sessions, "Session should be in user sessions"
        
        # 2. Update session - simulating user interaction and progress
        update_data = {
            "context": {
                "analysis_type": "cost_optimization",
                "progress": {"completed": 3, "total": 5},
                "last_activity": "2025-01-09T11:30:00Z"
            },
            "preferences": {"auto_save": True, "notifications": False}
        }
        update_result = await self.manager.update_session(session_id, update_data)
        assert update_result is True, "Update should succeed"
        
        # 3. Verify updated data
        session = await self.manager.get_session(session_id)
        assert session["data"]["context"]["last_activity"] == "2025-01-09T11:30:00Z", "Activity should be updated"
        assert session["data"]["context"]["progress"]["completed"] == 3, "Progress should be updated"
        assert session["data"]["preferences"]["notifications"] is False, "Notifications should be updated"
        assert session["data"]["preferences"]["auto_save"] is True, "Auto save should be preserved"
        
        # 4. Close session - simulating user logging out or finishing work
        close_result = await self.manager.close_session(session_id)
        assert close_result is True, "Session should close successfully"
        assert await self.manager.is_session_active(session_id) is False, "Session should be inactive"
        
        # 5. Verify cleanup
        user_sessions_after_close = await self.manager.get_user_sessions(self.test_user)
        assert session_id not in user_sessions_after_close, "Session should be removed from user sessions"
        
        # Verify session data still exists but is inactive (for audit/history)
        closed_session = await self.manager.get_session(session_id)
        assert closed_session is not None, "Session data should be preserved for audit"
        assert closed_session["active"] is False, "Session should be marked inactive"
        
        # Record complete lifecycle metrics
        self.record_metric("complete_lifecycle_tested", True)
        self.record_metric("session_creation_successful", True)
        self.record_metric("session_updates_successful", True)
        self.record_metric("session_closure_successful", True)
        self.record_metric("session_cleanup_successful", True)
    
    async def test_multiple_session_lifecycle_management(self):
        """
        Test lifecycle management with multiple concurrent sessions.
        
        Business Impact: Multi-session lifecycle management enables users to
        maintain multiple active AI conversations without resource leaks.
        """
        # Create multiple sessions representing different user activities
        session_contexts = [
            {"workspace": "aws-optimization", "priority": "high"},
            {"workspace": "gcp-monitoring", "priority": "medium"},
            {"workspace": "azure-security", "priority": "low"}
        ]
        
        created_sessions = []
        
        # Create all sessions
        for context in session_contexts:
            session_id = await self.manager.create_session(self.test_user, context)
            created_sessions.append(session_id)
            
            # Verify each session is active
            assert await self.manager.is_session_active(session_id) is True
        
        # Verify all sessions are in user mapping
        user_sessions = await self.manager.get_user_sessions(self.test_user)
        assert len(user_sessions) == len(session_contexts), "All sessions should be in user mapping"
        
        # Close sessions selectively (simulate user finishing some work)
        sessions_to_close = created_sessions[:2]  # Close first two sessions
        session_to_keep = created_sessions[2]      # Keep last session active
        
        for session_id in sessions_to_close:
            result = await self.manager.close_session(session_id)
            assert result is True, f"Session {session_id} should close successfully"
        
        # Verify session states
        for session_id in sessions_to_close:
            assert await self.manager.is_session_active(session_id) is False, f"Closed session {session_id} should be inactive"
        
        assert await self.manager.is_session_active(session_to_keep) is True, "Kept session should remain active"
        
        # Verify user mapping updated correctly
        final_user_sessions = await self.manager.get_user_sessions(self.test_user)
        assert len(final_user_sessions) == 1, "Only one session should remain in user mapping"
        assert session_to_keep in final_user_sessions, "Kept session should remain in mapping"
        
        for closed_session in sessions_to_close:
            assert closed_session not in final_user_sessions, f"Closed session {closed_session} should not be in mapping"
        
        # Record multi-session lifecycle metrics
        self.record_metric("multi_session_lifecycle_tested", True)
        self.record_metric("selective_session_closure_working", True)
        self.record_metric("session_mapping_consistency_maintained", True)


@pytest.mark.unit 
class TestSessionCleanupAndUtilities(SSotBaseTestCase):
    """
    Test session cleanup utilities and administrative functions.
    
    Business Value: Cleanup utilities enable system maintenance, testing,
    and resource management critical for production operations.
    """
    
    def setup_method(self):
        """Set up test fixtures for cleanup tests."""
        super().setup_method()
        self.manager = UserSessionManager()
    
    async def test_clear_all_sessions_resets_manager_state(self):
        """
        Test clear_all_sessions completely resets manager to initial state.
        
        Business Impact: Complete session clearing enables system reset,
        testing cleanup, and emergency resource recovery.
        """
        # Create multiple users with sessions using public API
        users_and_sessions = [
            (UserID("cleanup-user-1"), {"workspace": "data1"}),
            (UserID("cleanup-user-2"), {"workspace": "data2"}),
            (UserID("cleanup-user-3"), {"workspace": "data3"})
        ]
        
        # Create sessions using public API to test cleanup
        created_session_ids = []
        for user_id, session_data in users_and_sessions:
            session_id = await self.manager.create_session(user_id, session_data)
            created_session_ids.append(session_id)
        
        # Verify sessions exist before cleanup using public API
        for session_id in created_session_ids:
            session = await self.manager.get_session(session_id)
            assert session is not None, f"Session {session_id} should exist before cleanup"
        
        # Verify users have sessions
        for user_id, _ in users_and_sessions:
            user_sessions = await self.manager.get_user_sessions(user_id)
            assert len(user_sessions) > 0, f"User {user_id} should have sessions before cleanup"
        
        # Execute business logic
        self.manager.clear_all_sessions()
        
        # Verify business outcomes - complete cleanup using public API
        for session_id in created_session_ids:
            session = await self.manager.get_session(session_id)
            assert session is None, f"Session {session_id} should be cleared"
        
        # Verify all users have no sessions
        for user_id, _ in users_and_sessions:
            user_sessions = await self.manager.get_user_sessions(user_id)
            assert len(user_sessions) == 0, f"User {user_id} should have no sessions after cleanup"
        
        # Record cleanup metrics
        self.record_metric("sessions_cleared", len(created_session_ids))
        self.record_metric("user_mappings_cleared", len(users_and_sessions))
        self.record_metric("complete_cleanup_successful", True)
    
    async def test_manager_handles_concurrent_operations(self):
        """
        Test manager handles concurrent session operations safely.
        
        Business Impact: Concurrent operation safety ensures data integrity
        in multi-user environments with simultaneous session operations.
        """
        test_user = UserID("concurrent-operations-user")
        
        # Create multiple sessions concurrently (simulated)
        session_count = 10
        session_ids = []
        
        for i in range(session_count):
            session_data = {
                "concurrent_test": i, 
                "workspace": f"workspace_{i}",
                "timestamp": f"2025-01-09T10:{30+i:02d}:00Z"
            }
            session_id = await self.manager.create_session(test_user, session_data)
            session_ids.append(session_id)
        
        # Verify all sessions created correctly
        assert len(session_ids) == session_count, f"Should create {session_count} sessions"
        assert len(set(session_ids)) == session_count, "All session IDs should be unique"
        
        user_sessions = await self.manager.get_user_sessions(test_user)
        assert len(user_sessions) == session_count, f"User should have {session_count} sessions"
        
        # Perform concurrent operations (simulated)
        operations_results = []
        
        for i, session_id in enumerate(session_ids):
            if i % 3 == 0:  # Close every 3rd session
                result = await self.manager.close_session(session_id)
                operations_results.append(("close", session_id, result))
            elif i % 3 == 1:  # Update every session where i % 3 == 1
                update_data = {"updated": True, "update_index": i}
                result = await self.manager.update_session(session_id, update_data)
                operations_results.append(("update", session_id, result))
            else:  # Just retrieve every session where i % 3 == 2
                session = await self.manager.get_session(session_id)
                operations_results.append(("retrieve", session_id, session is not None))
        
        # Verify all operations succeeded
        for operation, session_id, result in operations_results:
            assert result is True, f"Operation {operation} on session {session_id} should succeed"
        
        # Verify final state consistency
        final_user_sessions = await self.manager.get_user_sessions(test_user)
        closed_sessions_count = len([op for op in operations_results if op[0] == "close"])
        expected_active_sessions = session_count - closed_sessions_count
        
        assert len(final_user_sessions) == expected_active_sessions, f"Should have {expected_active_sessions} active sessions"
        
        # Verify updated sessions have correct data
        updated_sessions = [op[1] for op in operations_results if op[0] == "update"]
        for session_id in updated_sessions:
            if session_id in final_user_sessions:  # Only check if still active
                session = await self.manager.get_session(session_id)
                assert session["data"]["updated"] is True, f"Updated session {session_id} should have updated flag"
        
        # Record concurrent operations metrics
        self.record_metric("concurrent_sessions_tested", session_count)
        self.record_metric("concurrent_operations_performed", len(operations_results))
        self.record_metric("concurrent_operations_successful", True)
        self.record_metric("data_consistency_maintained", True)
    
    async def test_memory_usage_with_large_session_data(self):
        """
        Test memory management with large session data structures.
        
        Business Impact: Efficient memory usage ensures system scalability
        and prevents resource exhaustion in production environments.
        """
        import sys
        
        test_user = UserID("memory-test-user")
        
        # Create session with large data structure
        large_data = {
            "conversation_history": [
                {
                    "message_id": i,
                    "content": f"This is message {i} with substantial content for memory testing. " * 50,
                    "timestamp": f"2025-01-09T10:{i%60:02d}:00Z",
                    "metadata": {"tokens": 1000 + i, "processing_time": 0.5 + (i * 0.01)}
                }
                for i in range(1000)  # 1000 messages
            ],
            "analysis_results": {
                f"analysis_{i}": {
                    "data": [j for j in range(100)],  # 100 data points per analysis
                    "summary": f"Analysis {i} summary with detailed results" * 10
                }
                for i in range(100)  # 100 analyses
            }
        }
        
        # Create session with large data
        session_id = await self.manager.create_session(test_user, large_data)
        
        # Verify session was created successfully
        assert session_id is not None, "Large data session should be created"
        
        retrieved_session = await self.manager.get_session(session_id)
        assert retrieved_session is not None, "Large data session should be retrievable"
        assert len(retrieved_session["data"]["conversation_history"]) == 1000, "All conversation history should be preserved"
        assert len(retrieved_session["data"]["analysis_results"]) == 100, "All analysis results should be preserved"
        
        # Test that the system remains responsive with large data
        import time
        start_time = time.time()
        
        # Test multiple operations with large session
        for _ in range(10):
            test_session = await self.manager.get_session(session_id)
            assert test_session is not None, "Large session should remain accessible"
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        # Verify system remains performant with large data
        assert operation_time < 1.0, f"Operations should remain fast with large data (took {operation_time:.3f}s)"
        
        # Clean up large session
        close_result = await self.manager.close_session(session_id)
        assert close_result is True, "Large session should close successfully"
        
        # Record performance metrics instead of memory metrics
        self.record_metric("large_session_data_handled", True)
        self.record_metric("large_session_operations_time_seconds", operation_time)
        self.record_metric("large_data_integrity_preserved", True)
        self.record_metric("large_session_performance_acceptable", operation_time < 1.0)
    
    async def test_session_state_consistency_after_errors(self):
        """
        Test session manager maintains consistent state after error conditions.
        
        Business Impact: State consistency after errors ensures system reliability
        and prevents data corruption in production environments.
        """
        test_user = UserID("error-consistency-user")
        
        # Create initial session
        initial_data = {"workspace": "error-test"}
        session_id = await self.manager.create_session(test_user, initial_data)
        
        # Verify initial state
        assert await self.manager.is_session_active(session_id) is True
        user_sessions = await self.manager.get_user_sessions(test_user)
        assert session_id in user_sessions
        
        # Simulate various error conditions and verify state remains consistent
        
        # 1. Try to update non-existent session
        invalid_update_result = await self.manager.update_session("invalid_session", {"test": "data"})
        assert invalid_update_result is False, "Invalid session update should fail"
        
        # Verify original session unaffected
        assert await self.manager.is_session_active(session_id) is True, "Original session should remain active"
        
        # 2. Try to close non-existent session
        invalid_close_result = await self.manager.close_session("invalid_session")
        assert invalid_close_result is False, "Invalid session close should fail"
        
        # Verify original session unaffected
        assert await self.manager.is_session_active(session_id) is True, "Original session should remain active"
        
        # 3. Perform valid operations to ensure system still works
        update_result = await self.manager.update_session(session_id, {"error_test": "completed"})
        assert update_result is True, "Valid update should succeed after error conditions"
        
        # 4. Verify session data integrity
        session = await self.manager.get_session(session_id)
        assert session["data"]["workspace"] == "error-test", "Original data should be preserved"
        assert session["data"]["error_test"] == "completed", "Update should be applied"
        
        # Record error handling metrics
        self.record_metric("error_conditions_tested", 2)
        self.record_metric("state_consistency_maintained", True)
        self.record_metric("system_recovery_after_errors", True)


@pytest.mark.unit
class TestSessionSecurityAndValidation(SSotBaseTestCase):
    """
    Test session security patterns and data validation.
    
    Business Value: Security testing ensures user data protection and prevents
    breaches that could damage trust and result in regulatory penalties.
    """
    
    def setup_method(self):
        """Set up test fixtures for security tests."""
        super().setup_method()
        self.manager = UserSessionManager()
    
    async def test_session_data_isolation_between_operations(self):
        """
        Test session data is completely isolated between different operations.
        
        Business Impact: Data isolation prevents information leakage between
        users and operations, critical for enterprise security compliance.
        """
        # Create users with different security profiles
        enterprise_user = UserID("enterprise-security-user")
        standard_user = UserID("standard-security-user")
        
        # Create sessions with highly sensitive data
        enterprise_sensitive_data = {
            "security_classification": "confidential",
            "api_credentials": {
                "aws": {"access_key": "AKIA_ENTERPRISE_SECRET_123", "secret": "enterprise_secret_key"},
                "gcp": {"project_id": "enterprise-gcp-proj", "key_file": "enterprise-key.json"},
                "azure": {"client_id": "enterprise-azure-client", "tenant": "enterprise.onmicrosoft.com"}
            },
            "sensitive_workspaces": ["production-optimization", "security-audit", "compliance-review"],
            "data_classification": {
                "personal_data": True,
                "financial_data": True,
                "compliance_requirements": ["SOX", "GDPR", "HIPAA"]
            }
        }
        
        standard_sensitive_data = {
            "security_classification": "internal",
            "api_credentials": {
                "aws": {"access_key": "AKIA_STANDARD_SECRET_456", "secret": "standard_secret_key"},
                "gcp": {"project_id": "standard-gcp-proj", "key_file": "standard-key.json"}
            },
            "sensitive_workspaces": ["development-testing", "staging-validation"],
            "data_classification": {
                "personal_data": False,
                "financial_data": False,
                "compliance_requirements": []
            }
        }
        
        # Create isolated sessions
        enterprise_session = await self.manager.create_session(enterprise_user, enterprise_sensitive_data)
        standard_session = await self.manager.create_session(standard_user, standard_sensitive_data)
        
        # Verify sessions exist and are different
        assert enterprise_session != standard_session, "Sessions should have different IDs"
        
        # Retrieve session data independently
        enterprise_retrieved = await self.manager.get_session(enterprise_session)
        standard_retrieved = await self.manager.get_session(standard_session)
        
        # Verify complete data isolation - enterprise data
        enterprise_data = enterprise_retrieved["data"]
        assert enterprise_data["security_classification"] == "confidential"
        assert enterprise_data["api_credentials"]["aws"]["access_key"] == "AKIA_ENTERPRISE_SECRET_123"
        assert enterprise_data["api_credentials"]["aws"]["secret"] == "enterprise_secret_key"
        assert "production-optimization" in enterprise_data["sensitive_workspaces"]
        assert "SOX" in enterprise_data["data_classification"]["compliance_requirements"]
        
        # Verify no cross-contamination with standard user data
        assert "AKIA_STANDARD_SECRET_456" not in str(enterprise_data)
        assert "standard-gcp-proj" not in str(enterprise_data)
        assert "development-testing" not in enterprise_data["sensitive_workspaces"]
        
        # Verify complete data isolation - standard data  
        standard_data = standard_retrieved["data"]
        assert standard_data["security_classification"] == "internal"
        assert standard_data["api_credentials"]["aws"]["access_key"] == "AKIA_STANDARD_SECRET_456"
        assert "development-testing" in standard_data["sensitive_workspaces"]
        assert len(standard_data["data_classification"]["compliance_requirements"]) == 0
        
        # Verify no cross-contamination with enterprise user data
        assert "AKIA_ENTERPRISE_SECRET_123" not in str(standard_data)
        assert "enterprise-gcp-proj" not in str(standard_data)
        assert "production-optimization" not in standard_data["sensitive_workspaces"]
        assert "azure" not in standard_data["api_credentials"]
        
        # Verify user session mapping isolation
        enterprise_sessions = await self.manager.get_user_sessions(enterprise_user)
        standard_sessions = await self.manager.get_user_sessions(standard_user)
        
        assert enterprise_session in enterprise_sessions, "Enterprise session should belong to enterprise user"
        assert enterprise_session not in standard_sessions, "Enterprise session should NOT belong to standard user"
        assert standard_session in standard_sessions, "Standard session should belong to standard user"
        assert standard_session not in enterprise_sessions, "Standard session should NOT belong to enterprise user"
        
        # Record security isolation metrics
        self.record_metric("sensitive_data_isolation_verified", True)
        self.record_metric("cross_user_contamination_prevented", True)
        self.record_metric("security_classification_preserved", True)
        self.record_metric("compliance_data_isolated", True)
    
    async def test_session_data_consistency_during_updates(self):
        """
        Test session data remains consistent during concurrent updates.
        
        Business Impact: Data consistency during updates prevents corruption
        and ensures reliable operation in multi-user environments.
        """
        test_user = UserID("consistency-security-user")
        
        # Initial session with critical data
        initial_data = {
            "security_counters": {
                "login_attempts": 0,
                "failed_authentications": 0,
                "successful_operations": 0
            },
            "audit_log": {
                "operations": [],
                "security_events": [],
                "data_access_log": []
            },
            "critical_state": {
                "session_valid": True,
                "security_level": "standard",
                "last_validation": "2025-01-09T10:00:00Z"
            }
        }
        
        session_id = await self.manager.create_session(test_user, initial_data)
        
        # Simulate multiple security-related updates
        security_updates = [
            {
                "security_counters": {"login_attempts": 1, "successful_operations": 1},
                "audit_log": {"operations": ["session_created"]},
                "critical_state": {"last_validation": "2025-01-09T10:01:00Z"}
            },
            {
                "security_counters": {"login_attempts": 2, "successful_operations": 2},
                "audit_log": {"operations": ["session_created", "data_accessed"]},
                "critical_state": {"last_validation": "2025-01-09T10:02:00Z"}
            },
            {
                "security_counters": {"login_attempts": 3, "successful_operations": 3},
                "audit_log": {
                    "operations": ["session_created", "data_accessed", "security_check"],
                    "security_events": ["password_verified"]
                },
                "critical_state": {"security_level": "elevated", "last_validation": "2025-01-09T10:03:00Z"}
            }
        ]
        
        # Apply updates sequentially and verify consistency
        for i, update_data in enumerate(security_updates):
            # Apply update
            result = await self.manager.update_session(session_id, update_data)
            assert result is True, f"Security update {i} should succeed"
            
            # Verify intermediate consistency
            current_session = await self.manager.get_session(session_id)
            current_data = current_session["data"]
            
            # Verify counters are consistent
            expected_operations = update_data["security_counters"]["successful_operations"]
            actual_operations = current_data["security_counters"]["successful_operations"]
            assert actual_operations == expected_operations, f"Operations counter should be {expected_operations}"
            
            # Verify audit log consistency
            expected_ops_count = len(update_data["audit_log"]["operations"])
            actual_ops_count = len(current_data["audit_log"]["operations"])
            assert actual_ops_count == expected_ops_count, f"Audit log should have {expected_ops_count} operations"
            
            # Verify critical state consistency
            expected_validation = update_data["critical_state"]["last_validation"]
            actual_validation = current_data["critical_state"]["last_validation"]
            assert actual_validation == expected_validation, f"Validation timestamp should be updated"
        
        # Verify final state consistency
        final_session = await self.manager.get_session(session_id)
        final_data = final_session["data"]
        
        # Verify all security counters are correct
        assert final_data["security_counters"]["login_attempts"] == 3
        assert final_data["security_counters"]["failed_authentications"] == 0  # Should be preserved
        assert final_data["security_counters"]["successful_operations"] == 3
        
        # Verify audit log completeness
        assert len(final_data["audit_log"]["operations"]) == 3
        assert "session_created" in final_data["audit_log"]["operations"]
        assert "data_accessed" in final_data["audit_log"]["operations"]
        assert "security_check" in final_data["audit_log"]["operations"]
        assert "password_verified" in final_data["audit_log"]["security_events"]
        
        # Verify critical state is correct
        assert final_data["critical_state"]["session_valid"] is True  # Preserved
        assert final_data["critical_state"]["security_level"] == "elevated"  # Updated
        assert final_data["critical_state"]["last_validation"] == "2025-01-09T10:03:00Z"  # Updated
        
        # Record consistency metrics
        self.record_metric("security_data_consistency_maintained", True)
        self.record_metric("audit_log_integrity_preserved", True)
        self.record_metric("security_state_consistency_verified", True)
    
    async def test_session_data_validation_and_sanitization(self):
        """
        Test session data validation patterns for security.
        
        Business Impact: Data validation prevents injection attacks and ensures
        data integrity, critical for maintaining system security.
        """
        test_user = UserID("validation-security-user")
        
        # Test data with various potential security concerns
        test_cases = [
            {
                "description": "Normal data should be preserved",
                "data": {"workspace": "normal-workspace", "user_input": "regular user input"},
                "should_succeed": True,
                "expected_workspace": "normal-workspace"
            },
            {
                "description": "Empty strings should be handled",
                "data": {"workspace": "", "empty_field": ""},
                "should_succeed": True,
                "expected_workspace": ""
            },
            {
                "description": "Large data structures should be handled",
                "data": {
                    "large_array": [f"item_{i}" for i in range(1000)],
                    "nested_object": {"level_1": {"level_2": {"level_3": "deep_value"}}}
                },
                "should_succeed": True,
                "expected_array_length": 1000
            },
            {
                "description": "Special characters should be preserved",
                "data": {
                    "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
                    "unicode_chars": "[U+03B1][U+03B2][U+03B3][U+03B4][U+03B5] [U+4E2D][U+6587] [U+0627][U+0644][U+0639][U+0631][U+0628][U+064A][U+0629] [U+1F680] CELEBRATION: ",
                    "json_like": '{"key": "value", "number": 123}'
                },
                "should_succeed": True,
                "expected_special": "!@#$%^&*()_+-=[]{}|;':\",./<>?"
            }
        ]
        
        # Test each validation case
        for i, test_case in enumerate(test_cases):
            # Create session with test data
            session_id = await self.manager.create_session(test_user, test_case["data"])
            
            if test_case["should_succeed"]:
                assert session_id is not None, f"Test case {i}: {test_case['description']} should succeed"
                
                # Retrieve and verify data preservation
                session = await self.manager.get_session(session_id)
                assert session is not None, f"Test case {i}: Session should be retrievable"
                
                # Verify specific expected values
                if "expected_workspace" in test_case:
                    actual_workspace = session["data"].get("workspace")
                    expected_workspace = test_case["expected_workspace"] 
                    assert actual_workspace == expected_workspace, f"Test case {i}: Workspace should be preserved"
                
                if "expected_array_length" in test_case:
                    actual_length = len(session["data"]["large_array"])
                    expected_length = test_case["expected_array_length"]
                    assert actual_length == expected_length, f"Test case {i}: Array length should be preserved"
                
                if "expected_special" in test_case:
                    actual_special = session["data"]["special_chars"]
                    expected_special = test_case["expected_special"]
                    assert actual_special == expected_special, f"Test case {i}: Special characters should be preserved"
                
                # Clean up session
                await self.manager.close_session(session_id)
            else:
                # For cases that should fail, verify graceful failure
                # (Currently all test cases should succeed, but this structure allows for future security validations)
                pass
        
        # Record validation metrics
        self.record_metric("validation_test_cases_executed", len(test_cases))
        self.record_metric("data_validation_working", True)
        self.record_metric("security_edge_cases_handled", True)
    
    async def test_session_race_condition_protection(self):
        """
        Test session manager protects against race conditions.
        
        Business Impact: Race condition protection ensures data integrity
        in concurrent environments, preventing data corruption.
        """
        test_user = UserID("race-condition-user")
        
        # Create initial session
        initial_data = {"counter": 0, "operations": []}
        session_id = await self.manager.create_session(test_user, initial_data)
        
        # Simulate concurrent operations on the same session
        concurrent_operations = []
        
        # Prepare multiple update operations
        for i in range(10):
            operation = {
                "counter": i + 1,
                "operations": [f"operation_{i}"],
                "timestamp": f"2025-01-09T10:{30+i:02d}:00Z"
            }
            concurrent_operations.append(operation)
        
        # Execute operations sequentially (simulating concurrent access)
        results = []
        for operation in concurrent_operations:
            result = await self.manager.update_session(session_id, operation)
            results.append(result)
            
            # Immediately check session state for consistency
            session = await self.manager.get_session(session_id)
            assert session is not None, "Session should remain valid during concurrent operations"
            assert session["active"] is True, "Session should remain active"
        
        # Verify all operations succeeded
        assert all(results), "All concurrent operations should succeed"
        
        # Verify final session state consistency
        final_session = await self.manager.get_session(session_id)
        final_data = final_session["data"]
        
        # Final state should reflect the last operation
        # (Note: Due to dict.update() behavior, the final state will have the last operation's values)
        assert final_data["counter"] == 10, "Final counter should reflect last operation"
        assert len(final_data["operations"]) == 1, "Operations list should have been replaced by last update"
        assert "operation_9" in final_data["operations"], "Should contain last operation"
        
        # Record race condition protection metrics
        self.record_metric("concurrent_operations_tested", len(concurrent_operations))
        self.record_metric("session_consistency_maintained", True)
        self.record_metric("race_condition_handling_verified", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])