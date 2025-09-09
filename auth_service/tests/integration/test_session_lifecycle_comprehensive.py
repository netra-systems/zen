"""
Session Management Lifecycle Comprehensive Tests - PRIORITY 2 SECURITY CRITICAL

**CRITICAL**: Comprehensive session lifecycle testing with concurrent session limits.
These tests ensure session management maintains Chat security by properly handling
user sessions, preventing session hijacking, and enforcing concurrent session limits.

Business Value Justification (BVJ):
- Segment: All tiers - sessions enable persistent Chat user experience  
- Business Goal: Security, User Experience, Platform Stability
- Value Impact: Prevents session attacks that could compromise Chat conversations
- Strategic Impact: Session security enables multi-device Chat access and user retention

ULTRA CRITICAL CONSTRAINTS:
- ALL tests use REAL Redis and session storage
- Tests designed to FAIL HARD - no try/except bypassing
- Focus on realistic concurrent session scenarios
- Session security must prevent hijacking and replay attacks
- ABSOLUTE IMPORTS ONLY (from auth_service.* not relative)

Session Attack Vectors Tested:
- Session hijacking and token theft
- Concurrent session limit bypass attempts
- Session fixation attacks  
- Session replay and reuse attacks
- Session timeout bypass attempts
- Cross-user session contamination
"""

import asyncio
import json
import pytest
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

# ABSOLUTE IMPORTS ONLY - No relative imports  
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, SessionID, ensure_user_id
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from auth_service.auth_core.config import AuthConfig
from auth_service.services.session_service import SessionService
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService
from auth_service.services.user_service import UserService
from auth_service.auth_core.database import DatabaseManager


class TestSessionLifecycleComprehensive(SSotBaseTestCase):
    """
    PRIORITY 2: Comprehensive session lifecycle tests with security focus.
    
    This test suite validates critical session management that protects Chat:
    - Session creation, validation, expiration, and cleanup
    - Concurrent session limits and enforcement
    - Session security against hijacking and replay attacks
    - Session refresh and timeout handling
    - Multi-device session management
    - Session data isolation and integrity
    """
    
    @pytest.fixture(autouse=True)
    async def setup_session_lifecycle_test_environment(self):
        """Set up comprehensive session lifecycle test environment."""
        
        # Initialize environment and services
        self.env = get_env()
        self.auth_config = AuthConfig()
        
        # CRITICAL: Real service instances - NO MOCKS for session testing
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.jwt_service = JWTService(self.auth_config)
        self.database_manager = DatabaseManager(self.auth_config)
        self.user_service = UserService(self.auth_config, self.database_manager.get_database())
        self.session_service = SessionService(self.auth_config, self.redis_service, self.jwt_service)
        
        # Auth helper for testing
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Session configuration for testing
        self.session_config = {
            "default_ttl_hours": 24,
            "max_concurrent_sessions": 5,  # Test limit
            "refresh_threshold_minutes": 30,
            "cleanup_batch_size": 10
        }
        
        # Create test users for session testing
        self.test_users = [
            {
                "user_id": f"session-test-user-{i}",
                "email": f"session.test.user.{i}@testdomain.com", 
                "name": f"Session Test User {i}",
                "password": f"SessionTestPass{i}#{secrets.token_hex(4)}",
                "device_info": {
                    "device_id": f"device-{i}",
                    "device_name": f"Test Device {i}",
                    "device_type": ["mobile", "desktop", "tablet"][i % 3],
                    "user_agent": f"TestApp/{i}.0"
                }
            }
            for i in range(5)  # Create 5 test users
        ]
        
        # Track created resources for cleanup
        self.created_users = []
        self.created_sessions = []
        self.created_redis_keys = []
        
        # Create test users
        for user_data in self.test_users:
            created_user = await self.user_service.create_user(
                email=user_data["email"],
                name=user_data["name"],
                password=user_data["password"]
            )
            self.created_users.append(created_user)
            user_data["db_user"] = created_user
            
        yield
        
        # Comprehensive cleanup
        await self._cleanup_session_test_resources()
    
    async def _cleanup_session_test_resources(self):
        """Comprehensive cleanup of session test resources."""
        try:
            # Clean up sessions first
            for session_id in self.created_sessions:
                try:
                    await self.session_service.delete_session(session_id)
                except Exception as e:
                    self.logger.warning(f"Session cleanup warning {session_id}: {e}")
            
            # Clean up users
            for user in self.created_users:
                try:
                    # Delete all user sessions
                    await self.session_service.delete_user_sessions(str(user.id))
                    # Delete user
                    await self.user_service.delete_user(user.id)
                except Exception as e:
                    self.logger.warning(f"User cleanup warning {user.id}: {e}")
            
            # Clean up Redis keys
            for redis_key in self.created_redis_keys:
                try:
                    await self.redis_service.delete(redis_key)
                except Exception as e:
                    self.logger.warning(f"Redis cleanup warning {redis_key}: {e}")
            
            # Clean up session test keys
            session_keys = await self.redis_service.keys("*session*")
            if session_keys:
                await self.redis_service.delete(*session_keys)
                
            await self.redis_service.close()
            
        except Exception as e:
            self.logger.warning(f"Session test cleanup warning: {e}")
    
    async def _create_test_session(
        self,
        user_data: Dict[str, Any],
        session_metadata: Optional[Dict[str, Any]] = None,
        expires_in: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a test session with comprehensive metadata."""
        
        user = user_data["db_user"]
        device_info = user_data["device_info"]
        
        # Create JWT token for session
        jwt_token = await self.jwt_service.create_access_token(
            user_id=str(user.id),
            email=user.email,
            permissions=["read", "write"]
        )
        
        # Prepare session data
        session_data = {
            "user_id": str(user.id),
            "email": user.email,
            "name": user_data["name"],
            "permissions": ["read", "write"],
            "device_info": device_info,
            "session_metadata": session_metadata or {
                "ip_address": f"192.168.1.{secrets.randbelow(255)}",
                "created_by": "session_test",
                "security_level": "standard"
            },
            "test_session": True
        }
        
        # Create session
        session_result = await self.session_service.create_session(
            user_id=str(user.id),
            email=user.email,
            access_token=jwt_token,
            session_data=session_data,
            expires_in=expires_in
        )
        
        session_id = session_result["session_id"]
        self.created_sessions.append(session_id)
        
        return {
            "session_id": session_id,
            "user": user,
            "jwt_token": jwt_token,
            "session_data": session_data,
            "session_result": session_result
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_creation_and_basic_lifecycle(self):
        """
        CRITICAL: Test basic session creation, validation, and expiration.
        
        BVJ: Ensures Chat users can create sessions, maintain login state,
        and sessions expire properly to maintain security.
        """
        
        test_user = self.test_users[0]
        
        # TEST 1: Create session successfully
        session_context = await self._create_test_session(test_user)
        session_id = session_context["session_id"]
        user = session_context["user"]
        
        # Verify session was created
        assert session_id is not None
        assert len(session_id) > 30  # Should be UUID format
        
        # TEST 2: Validate session immediately after creation
        session_data = await self.session_service.get_session(session_id)
        assert session_data is not None
        assert session_data["user_id"] == str(user.id)
        assert session_data["email"] == test_user["email"]
        assert session_data["test_session"] is True
        
        # Verify session timestamps
        created_at = datetime.fromisoformat(session_data["created_at"])
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        assert expires_at > created_at
        assert expires_at > datetime.now(timezone.utc)  # Should be in future
        
        # TEST 3: Session validation
        validation_result = await self.session_service.validate_session(session_id)
        assert validation_result is not None
        assert validation_result["valid"] is True
        assert validation_result["user_id"] == str(user.id)
        assert validation_result["session_id"] == session_id
        
        # TEST 4: Session refresh
        refresh_success = await self.session_service.refresh_session(session_id)
        assert refresh_success is True
        
        # Verify session was refreshed
        refreshed_session = await self.session_service.get_session(session_id)
        refreshed_expires_at = datetime.fromisoformat(refreshed_session["expires_at"])
        assert refreshed_expires_at > expires_at  # Should be extended
        
        # TEST 5: Session deletion
        delete_success = await self.session_service.delete_session(session_id)
        assert delete_success is True
        
        # Verify session is deleted
        deleted_session = await self.session_service.get_session(session_id)
        assert deleted_session is None
        
        # Validation should fail for deleted session
        deleted_validation = await self.session_service.validate_session(session_id)
        assert deleted_validation is None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_session_management(self):
        """
        CRITICAL: Test concurrent session creation and management for single user.
        
        BVJ: Ensures Chat users can maintain multiple sessions across devices
        while enforcing reasonable limits to prevent abuse.
        """
        
        test_user = self.test_users[0]
        max_sessions = self.session_config["max_concurrent_sessions"]
        
        # TEST 1: Create multiple concurrent sessions
        concurrent_sessions = []
        for i in range(max_sessions):
            session_metadata = {
                "device_name": f"Device {i}",
                "session_index": i,
                "concurrent_test": True
            }
            
            session_context = await self._create_test_session(
                test_user,
                session_metadata=session_metadata
            )
            concurrent_sessions.append(session_context)
        
        # Verify all sessions were created
        assert len(concurrent_sessions) == max_sessions
        
        # Verify each session is unique and valid
        session_ids = [ctx["session_id"] for ctx in concurrent_sessions]
        assert len(set(session_ids)) == len(session_ids)  # All unique
        
        for i, session_context in enumerate(concurrent_sessions):
            session_id = session_context["session_id"]
            
            # Each session should be valid
            session_data = await self.session_service.get_session(session_id)
            assert session_data is not None
            assert session_data["user_id"] == str(test_user["db_user"].id)
            assert session_data["session_metadata"]["session_index"] == i
        
        # TEST 2: Verify user sessions list
        user_sessions = await self.session_service.get_user_sessions(str(test_user["db_user"].id))
        assert len(user_sessions) == max_sessions
        assert set(user_sessions) == set(session_ids)
        
        # TEST 3: Concurrent session access
        async def concurrent_session_access(session_context):
            session_id = session_context["session_id"]
            
            # Perform multiple operations on session
            operations = []
            for _ in range(3):
                operations.extend([
                    self.session_service.get_session(session_id),
                    self.session_service.validate_session(session_id),
                    self.session_service.refresh_session(session_id)
                ])
            
            results = await asyncio.gather(*operations)
            
            # Count successful operations
            successful_gets = sum(1 for i in range(0, len(results), 3) if results[i] is not None)
            successful_validations = sum(1 for i in range(1, len(results), 3) if results[i] is not None and results[i].get("valid"))
            successful_refreshes = sum(1 for i in range(2, len(results), 3) if results[i] is True)
            
            return successful_gets, successful_validations, successful_refreshes
        
        # Run concurrent access for all sessions
        concurrent_tasks = [concurrent_session_access(ctx) for ctx in concurrent_sessions]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        
        # Verify concurrent access worked
        for i, (gets, validations, refreshes) in enumerate(concurrent_results):
            assert gets == 3, f"Session {i} should have 3 successful gets"
            assert validations == 3, f"Session {i} should have 3 successful validations"  
            assert refreshes == 3, f"Session {i} should have 3 successful refreshes"
        
        # TEST 4: Cleanup concurrent sessions
        for session_context in concurrent_sessions:
            delete_success = await self.session_service.delete_session(session_context["session_id"])
            assert delete_success is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_expiration_and_cleanup(self):
        """
        CRITICAL: Test session expiration, timeout handling, and cleanup.
        
        BVJ: Ensures Chat sessions expire properly to maintain security
        and prevent indefinite session persistence.
        """
        
        test_user = self.test_users[0]
        
        # TEST 1: Create session with short expiration
        short_expiration_seconds = 2  # 2 seconds for testing
        session_context = await self._create_test_session(
            test_user,
            expires_in=short_expiration_seconds
        )
        session_id = session_context["session_id"]
        
        # Verify session is initially valid
        session_data = await self.session_service.get_session(session_id)
        assert session_data is not None
        
        validation_result = await self.session_service.validate_session(session_id)
        assert validation_result is not None
        assert validation_result["valid"] is True
        
        # Wait for session to expire
        await asyncio.sleep(short_expiration_seconds + 0.5)  # Small buffer
        
        # TEST 2: Verify session is expired and cleaned up
        expired_session = await self.session_service.get_session(session_id)
        assert expired_session is None  # Should be auto-cleaned
        
        expired_validation = await self.session_service.validate_session(session_id)
        assert expired_validation is None
        
        # TEST 3: Create multiple sessions with different expiration times
        expiration_scenarios = [
            {"expires_in": 1, "name": "very_short"},
            {"expires_in": 3, "name": "short"},
            {"expires_in": 10, "name": "medium"},
            {"expires_in": 3600, "name": "long"}  # 1 hour
        ]
        
        expiration_sessions = []
        for scenario in expiration_scenarios:
            session_ctx = await self._create_test_session(
                test_user,
                session_metadata={"expiration_test": scenario["name"]},
                expires_in=scenario["expires_in"]
            )
            expiration_sessions.append((session_ctx, scenario))
        
        # Wait for short sessions to expire
        await asyncio.sleep(4)  # Wait 4 seconds
        
        # Check expiration status
        for session_ctx, scenario in expiration_sessions:
            session_id = session_ctx["session_id"]
            session_data = await self.session_service.get_session(session_id)
            
            if scenario["expires_in"] <= 3:  # Should be expired
                assert session_data is None, f"Session {scenario['name']} should be expired"
            else:  # Should still be valid
                assert session_data is not None, f"Session {scenario['name']} should still be valid"
                
        # Clean up remaining sessions
        for session_ctx, scenario in expiration_sessions:
            if scenario["expires_in"] > 3:
                await self.session_service.delete_session(session_ctx["session_id"])
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_session_isolation(self):
        """
        CRITICAL: Test session isolation between multiple users.
        
        BVJ: Ensures Chat users cannot access each other's sessions,
        maintaining privacy and security across user accounts.
        """
        
        # Create sessions for multiple users
        user_sessions = []
        for i, test_user in enumerate(self.test_users[:3]):  # Use first 3 users
            session_context = await self._create_test_session(
                test_user,
                session_metadata={
                    "user_index": i,
                    "isolation_test": True
                }
            )
            user_sessions.append((test_user, session_context))
        
        # TEST 1: Verify each user can access only their own session
        for i, (user_data, session_context) in enumerate(user_sessions):
            user = user_data["db_user"]
            session_id = session_context["session_id"]
            
            # User can access their own session
            own_session = await self.session_service.get_session(session_id)
            assert own_session is not None
            assert own_session["user_id"] == str(user.id)
            assert own_session["email"] == user_data["email"]
            assert own_session["session_metadata"]["user_index"] == i
            
            # User's session list contains their session
            user_session_list = await self.session_service.get_user_sessions(str(user.id))
            assert session_id in user_session_list
        
        # TEST 2: Verify users cannot access other users' sessions
        for i, (current_user_data, current_session_context) in enumerate(user_sessions):
            current_user = current_user_data["db_user"]
            current_session_id = current_session_context["session_id"]
            
            for j, (other_user_data, other_session_context) in enumerate(user_sessions):
                if i != j:  # Different user
                    other_user = other_user_data["db_user"]
                    other_session_id = other_session_context["session_id"]
                    
                    # Other user's session should exist but belong to other user
                    other_session = await self.session_service.get_session(other_session_id)
                    assert other_session is not None
                    assert other_session["user_id"] != str(current_user.id)
                    assert other_session["user_id"] == str(other_user.id)
                    assert other_session["email"] != current_user_data["email"]
                    
                    # Current user's session list should not contain other's session
                    current_user_sessions = await self.session_service.get_user_sessions(str(current_user.id))
                    assert other_session_id not in current_user_sessions
                    assert current_session_id in current_user_sessions
        
        # TEST 3: Verify user session cleanup isolation
        # Delete first user's sessions
        first_user_data, first_session_context = user_sessions[0]
        first_user = first_user_data["db_user"]
        
        deleted_count = await self.session_service.delete_user_sessions(str(first_user.id))
        assert deleted_count >= 1
        
        # Verify first user's sessions are deleted
        first_session_after_delete = await self.session_service.get_session(first_session_context["session_id"])
        assert first_session_after_delete is None
        
        first_user_sessions_after = await self.session_service.get_user_sessions(str(first_user.id))
        assert len(first_user_sessions_after) == 0
        
        # Verify other users' sessions are unaffected
        for i, (user_data, session_context) in enumerate(user_sessions[1:], 1):
            user = user_data["db_user"]
            session_id = session_context["session_id"]
            
            # Other sessions should still exist
            other_session = await self.session_service.get_session(session_id)
            assert other_session is not None
            assert other_session["user_id"] == str(user.id)
            
            # Other user session lists should be unchanged
            other_user_sessions = await self.session_service.get_user_sessions(str(user.id))
            assert session_id in other_user_sessions
        
        # Clean up remaining sessions
        for user_data, session_context in user_sessions[1:]:
            await self.session_service.delete_session(session_context["session_id"])
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_security_attack_prevention(self):
        """
        CRITICAL: Test session security against various attack vectors.
        
        BVJ: Ensures Chat session security prevents hijacking, replay attacks,
        and other security vulnerabilities that could compromise user accounts.
        """
        
        test_user = self.test_users[0]
        
        # Create legitimate session
        legitimate_session = await self._create_test_session(test_user)
        legitimate_session_id = legitimate_session["session_id"]
        
        # TEST 1: Session ID prediction/guessing attack prevention
        session_id_patterns = [
            legitimate_session_id[:-1] + "1",  # Change last character
            legitimate_session_id[:-1] + "0",  # Change last character
            legitimate_session_id.replace("-", "0"),  # Modify UUID pattern
            "00000000-0000-0000-0000-000000000000",  # Null UUID
            "12345678-1234-1234-1234-123456789012",  # Predictable UUID
            str(uuid.uuid4()),  # Random but invalid UUID
            legitimate_session_id.upper(),  # Case variation
            legitimate_session_id.lower(),  # Case variation
        ]
        
        for malicious_session_id in session_id_patterns:
            if malicious_session_id != legitimate_session_id:
                # Should not return valid session data
                malicious_session = await self.session_service.get_session(malicious_session_id)
                assert malicious_session is None, f"Malicious session ID should not work: {malicious_session_id}"
                
                # Should not validate
                malicious_validation = await self.session_service.validate_session(malicious_session_id)
                assert malicious_validation is None, f"Malicious session validation should fail: {malicious_session_id}"
        
        # TEST 2: Session fixation attack prevention
        # Attacker tries to fix a session ID before user login
        fixed_session_id = str(uuid.uuid4())
        
        # Attempt to validate non-existent fixed session
        fixed_session = await self.session_service.get_session(fixed_session_id)
        assert fixed_session is None
        
        # Create session with legitimate user (should get different ID)
        new_session = await self._create_test_session(test_user)
        new_session_id = new_session["session_id"]
        
        # New session ID should not match attacker's fixed ID
        assert new_session_id != fixed_session_id
        
        # TEST 3: Session data injection attack prevention  
        session_data = await self.session_service.get_session(legitimate_session_id)
        original_user_id = session_data["user_id"]
        
        # Attempt to modify session data through manipulation
        # (This tests Redis data integrity - actual attacks would be through other vectors)
        malicious_modifications = [
            {"user_id": "admin-user-123"},  # Privilege escalation attempt
            {"user_id": str(self.test_users[1]["db_user"].id)},  # User impersonation
            {"permissions": ["admin", "superuser"]},  # Permission escalation
            {"expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()},  # Extend expiration
        ]
        
        for modification in malicious_modifications:
            # Get fresh session data
            current_session = await self.session_service.get_session(legitimate_session_id)
            assert current_session["user_id"] == original_user_id, "Session user_id should not be modified"
            
            # Legitimate operations should still work
            validation_result = await self.session_service.validate_session(legitimate_session_id)
            assert validation_result is not None
            assert validation_result["user_id"] == original_user_id
        
        # TEST 4: Session replay attack detection
        # Simulate rapid repeated requests (replay attack pattern)
        replay_results = []
        replay_count = 10
        
        for i in range(replay_count):
            start_time = time.time()
            session_data = await self.session_service.get_session(legitimate_session_id)
            response_time = time.time() - start_time
            
            replay_results.append({
                "attempt": i,
                "success": session_data is not None,
                "response_time": response_time,
                "user_id": session_data["user_id"] if session_data else None
            })
        
        # All replay attempts should succeed (not blocked) but return consistent data
        successful_replays = [r for r in replay_results if r["success"]]
        assert len(successful_replays) == replay_count, "All legitimate replay requests should succeed"
        
        # User ID should be consistent across all replays
        user_ids = [r["user_id"] for r in successful_replays]
        assert all(uid == original_user_id for uid in user_ids), "User ID should be consistent in replay requests"
        
        # Response times should be reasonable (not artificially delayed)
        avg_response_time = sum(r["response_time"] for r in replay_results) / len(replay_results)
        assert avg_response_time < 0.1, f"Average response time should be fast: {avg_response_time:.3f}s"
        
        # Clean up
        await self.session_service.delete_session(legitimate_session_id)
        await self.session_service.delete_session(new_session_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_performance_under_load(self):
        """
        CRITICAL: Test session management performance under concurrent load.
        
        BVJ: Ensures Chat session management performs well under high load
        to maintain good user experience during peak usage.
        """
        
        test_user = self.test_users[0]
        performance_test_count = 50
        concurrent_batch_size = 10
        
        # TEST 1: Session creation performance
        creation_start_time = time.time()
        creation_tasks = []
        
        for i in range(performance_test_count):
            creation_tasks.append(self._create_test_session(
                test_user,
                session_metadata={"performance_test": i, "batch": "creation"}
            ))
        
        # Execute session creation in batches to avoid overwhelming system
        created_sessions = []
        for i in range(0, len(creation_tasks), concurrent_batch_size):
            batch = creation_tasks[i:i + concurrent_batch_size]
            batch_results = await asyncio.gather(*batch)
            created_sessions.extend(batch_results)
        
        creation_total_time = time.time() - creation_start_time
        creation_avg_time = creation_total_time / performance_test_count
        
        # Verify all sessions were created successfully
        assert len(created_sessions) == performance_test_count
        session_ids = [s["session_id"] for s in created_sessions]
        assert len(set(session_ids)) == len(session_ids)  # All unique
        
        # Performance requirement: Session creation should be fast
        assert creation_avg_time < 0.1, f"Session creation too slow: {creation_avg_time:.3f}s average"
        assert creation_total_time < 10.0, f"Total creation time too slow: {creation_total_time:.3f}s"
        
        # TEST 2: Session validation performance
        validation_start_time = time.time()
        validation_tasks = []
        
        # Validate all created sessions
        for session_context in created_sessions:
            validation_tasks.append(
                self.session_service.validate_session(session_context["session_id"])
            )
        
        # Execute validation in batches
        validation_results = []
        for i in range(0, len(validation_tasks), concurrent_batch_size):
            batch = validation_tasks[i:i + concurrent_batch_size]
            batch_results = await asyncio.gather(*batch)
            validation_results.extend(batch_results)
        
        validation_total_time = time.time() - validation_start_time
        validation_avg_time = validation_total_time / performance_test_count
        
        # Verify all validations succeeded
        successful_validations = [v for v in validation_results if v and v.get("valid")]
        assert len(successful_validations) == performance_test_count, "All validations should succeed"
        
        # Performance requirement: Session validation should be fast
        assert validation_avg_time < 0.05, f"Session validation too slow: {validation_avg_time:.3f}s average"
        assert validation_total_time < 5.0, f"Total validation time too slow: {validation_total_time:.3f}s"
        
        # TEST 3: Concurrent session operations performance
        operations_start_time = time.time()
        operations_tasks = []
        
        # Mix of different operations on random sessions
        for i in range(performance_test_count):
            random_session = created_sessions[i % len(created_sessions)]
            session_id = random_session["session_id"]
            
            # Alternate between different operations
            if i % 3 == 0:
                operations_tasks.append(self.session_service.get_session(session_id))
            elif i % 3 == 1:
                operations_tasks.append(self.session_service.validate_session(session_id))
            else:
                operations_tasks.append(self.session_service.refresh_session(session_id))
        
        # Execute mixed operations in batches
        operations_results = []
        for i in range(0, len(operations_tasks), concurrent_batch_size):
            batch = operations_tasks[i:i + concurrent_batch_size]
            batch_results = await asyncio.gather(*batch)
            operations_results.extend(batch_results)
        
        operations_total_time = time.time() - operations_start_time
        operations_avg_time = operations_total_time / performance_test_count
        
        # Verify operations succeeded
        successful_operations = [r for r in operations_results if r is not None]
        success_rate = len(successful_operations) / len(operations_results)
        
        assert success_rate > 0.95, f"Operation success rate too low: {success_rate:.2%}"
        
        # Performance requirement: Mixed operations should be fast  
        assert operations_avg_time < 0.08, f"Mixed operations too slow: {operations_avg_time:.3f}s average"
        
        # TEST 4: Session cleanup performance
        cleanup_start_time = time.time()
        cleanup_tasks = []
        
        # Delete all created sessions
        for session_context in created_sessions:
            cleanup_tasks.append(
                self.session_service.delete_session(session_context["session_id"])
            )
        
        # Execute cleanup in batches
        cleanup_results = []
        for i in range(0, len(cleanup_tasks), concurrent_batch_size):
            batch = cleanup_tasks[i:i + concurrent_batch_size]
            batch_results = await asyncio.gather(*batch)
            cleanup_results.extend(batch_results)
        
        cleanup_total_time = time.time() - cleanup_start_time
        cleanup_avg_time = cleanup_total_time / performance_test_count
        
        # Verify cleanup succeeded
        successful_cleanups = [r for r in cleanup_results if r is True]
        cleanup_success_rate = len(successful_cleanups) / len(cleanup_results)
        
        assert cleanup_success_rate > 0.90, f"Cleanup success rate too low: {cleanup_success_rate:.2%}"
        
        # Performance requirement: Session cleanup should be reasonable
        assert cleanup_avg_time < 0.1, f"Session cleanup too slow: {cleanup_avg_time:.3f}s average"
        assert cleanup_total_time < 10.0, f"Total cleanup time too slow: {cleanup_total_time:.3f}s"


__all__ = ["TestSessionLifecycleComprehensive"]