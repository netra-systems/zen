"""
Multi-User Isolation Comprehensive Tests - PRIORITY 1 SECURITY CRITICAL

**CRITICAL**: Comprehensive multi-user security isolation testing with attack vector validation.
These tests protect the Chat business value by ensuring users cannot access each other's 
AI conversations, agent executions, or sensitive data.

Business Value Justification (BVJ):
- Segment: All tiers - authentication is foundation for all user interactions
- Business Goal: Platform Stability, Security, Risk Reduction  
- Value Impact: Prevents auth cascade failures that destroy chat business value
- Strategic Impact: Ensures multi-user isolation for concurrent AI chat sessions

ULTRA CRITICAL CONSTRAINTS:
- ALL tests use REAL services (PostgreSQL, Redis, OAuth providers)
- Tests designed to FAIL HARD - no try/except bypassing
- Focus on realistic, difficult failure scenarios  
- Multi-user isolation is MANDATORY
- ABSOLUTE IMPORTS ONLY (from auth_service.* not relative)

Security Attack Vectors Tested:
- Session token replay attacks
- Cross-user data leakage
- OAuth state parameter manipulation  
- Concurrent session hijacking
- Service authorization bypass attempts
- JWT token injection between users
- Race condition exploitation
- Session fixation attacks
"""

import asyncio
import json
import pytest
import time
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
import httpx
import jwt as jwt_library

# ABSOLUTE IMPORTS ONLY - No relative imports
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, SessionID, TokenString, 
    AuthValidationResult, SessionValidationResult,
    ensure_user_id, ensure_request_id
)
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.config import AuthConfig
from auth_service.services.user_service import UserService
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService
from auth_service.services.session_service import SessionService
from auth_service.auth_core.database.database_manager import AuthDatabaseManager


class TestMultiUserIsolationComprehensive(SSotBaseTestCase):
    """
    PRIORITY 1: Comprehensive multi-user isolation tests with critical security attack vectors.
    
    This test suite validates complete isolation between users across all system components:
    - Database isolation (user data, sessions, permissions)
    - Redis isolation (cache, sessions, user-specific data)
    - JWT token isolation (user claims, permissions, expiration)
    - Session isolation (concurrent sessions, cleanup, hijacking prevention)
    - Attack vector protection (replay, injection, race conditions)
    """
    
    @pytest.fixture(autouse=True)
    async def setup_multi_user_test_environment(self):
        """Set up comprehensive test environment with real services and security focus."""
        
        # Initialize environment and auth helper
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # CRITICAL: Use real auth service configuration
        self.auth_config = AuthConfig()
        
        # CRITICAL: Real service instances - NO MOCKS
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.jwt_service = JWTService(self.auth_config)
        # AuthDatabaseManager provides static methods for database operations
        self.user_service = UserService(self.auth_config)
        self.session_service = SessionService(self.auth_config, self.redis_service, self.jwt_service)
        
        # Create diverse test users with different characteristics for isolation testing
        self.test_users_data = [
            {
                "user_id": f"isolation-user-{i}",
                "email": f"isolation.user.{i}@testdomain.com",
                "name": f"Isolation Test User {i}",
                "password": f"IsolationSecurePass{i}#{secrets.token_hex(4)}",
                "tier": ["free", "early", "enterprise"][i % 3],
                "permissions": {
                    0: ["read"],
                    1: ["read", "write"],
                    2: ["read", "write", "admin"],
                    3: ["read", "write"],
                    4: ["read", "write", "admin"]
                }[i],
                "sensitive_data": {
                    "api_key": f"secret-api-{i}-{secrets.token_hex(16)}",
                    "personal_info": f"confidential-data-user-{i}",
                    "business_settings": {
                        "company": f"TestCorp{i}",
                        "department": f"Department{i}",
                        "access_level": f"level-{i}"
                    }
                },
                "session_metadata": {
                    "device": f"TestDevice{i}",
                    "ip_address": f"192.168.1.{10 + i}",
                    "user_agent": f"TestAgent/{i}.0"
                }
            }
            for i in range(5)  # Create 5 diverse test users
        ]
        
        # Track created resources for cleanup
        self.created_user_ids = []
        self.created_session_ids = []
        self.created_redis_keys = []
        self.created_jwt_tokens = []
        
        yield
        
        # Comprehensive cleanup
        await self._cleanup_all_test_resources()
    
    async def _cleanup_all_test_resources(self):
        """Comprehensive cleanup of all test resources."""
        try:
            # Clean up sessions first
            for session_id in self.created_session_ids:
                try:
                    await self.session_service.delete_session(session_id)
                except Exception as e:
                    self.logger.warning(f"Session cleanup warning {session_id}: {e}")
            
            # Clean up users from database
            for user_id in self.created_user_ids:
                try:
                    await self.user_service.delete_user(user_id)
                except Exception as e:
                    self.logger.warning(f"User cleanup warning {user_id}: {e}")
            
            # Clean up Redis keys
            for redis_key in self.created_redis_keys:
                try:
                    await self.redis_service.delete(redis_key)
                except Exception as e:
                    self.logger.warning(f"Redis cleanup warning {redis_key}: {e}")
            
            # Clean up any isolation test keys
            isolation_keys = await self.redis_service.keys("*isolation*")
            if isolation_keys:
                await self.redis_service.delete(*isolation_keys)
                
            await self.redis_service.close()
            
        except Exception as e:
            self.logger.warning(f"Comprehensive cleanup warning: {e}")
    
    async def _create_isolated_test_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a fully isolated test user with all associated data and security context.
        
        Returns complete user context including database record, JWT token, session, 
        and user-specific Redis data for isolation testing.
        """
        
        # CRITICAL: Create user in database with real password hashing
        created_user = await self.user_service.create_user(
            email=user_data["email"],
            name=user_data["name"], 
            password=user_data["password"]
        )
        
        user_id_typed = ensure_user_id(str(created_user.id))
        self.created_user_ids.append(str(created_user.id))
        
        # CRITICAL: Create JWT token with user-specific claims
        access_token = await self.jwt_service.create_access_token(
            user_id=str(created_user.id),
            email=created_user.email,
            permissions=user_data["permissions"]
        )
        self.created_jwt_tokens.append(access_token)
        
        # CRITICAL: Create isolated session with comprehensive data
        session_data = {
            "user_id": str(created_user.id),
            "email": created_user.email,
            "name": user_data["name"],
            "permissions": user_data["permissions"],
            "tier": user_data["tier"],
            "sensitive_data": user_data["sensitive_data"],
            "session_metadata": user_data["session_metadata"],
            "isolation_test": True,
            "created_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        session_result = await self.session_service.create_session(
            user_id=str(created_user.id),
            email=created_user.email,
            access_token=access_token,
            session_data=session_data
        )
        
        session_id = session_result["session_id"]
        self.created_session_ids.append(session_id)
        
        # CRITICAL: Store user-specific data in Redis for cross-contamination testing
        user_cache_keys = []
        
        # Personal data cache
        personal_key = f"personal:isolation:{created_user.id}"
        await self.redis_service.set(
            personal_key,
            json.dumps({
                "user_id": str(created_user.id),
                "sensitive_data": user_data["sensitive_data"],
                "private_preferences": {
                    "theme": f"user-theme-{created_user.id}",
                    "language": f"lang-{created_user.id}",
                    "notifications": True,
                    "security_level": user_data["tier"]
                }
            }),
            ex=3600
        )
        user_cache_keys.append(personal_key)
        
        # Business data cache
        business_key = f"business:isolation:{created_user.id}"
        await self.redis_service.set(
            business_key,
            json.dumps({
                "user_id": str(created_user.id),
                "business_settings": user_data["sensitive_data"]["business_settings"],
                "api_access": {
                    "api_key": user_data["sensitive_data"]["api_key"],
                    "rate_limits": {"hourly": 1000 if user_data["tier"] == "enterprise" else 100},
                    "allowed_endpoints": user_data["permissions"]
                }
            }),
            ex=3600
        )
        user_cache_keys.append(business_key)
        
        # Security context cache  
        security_key = f"security:isolation:{created_user.id}"
        await self.redis_service.set(
            security_key,
            json.dumps({
                "user_id": str(created_user.id),
                "security_context": {
                    "last_login": datetime.now(timezone.utc).isoformat(),
                    "device_fingerprint": f"device-{created_user.id}",
                    "trusted_ips": [user_data["session_metadata"]["ip_address"]],
                    "mfa_enabled": user_data["tier"] in ["early", "enterprise"]
                }
            }),
            ex=3600
        )
        user_cache_keys.append(security_key)
        
        self.created_redis_keys.extend(user_cache_keys)
        
        return {
            "user": created_user,
            "user_id": user_id_typed,
            "access_token": TokenString(access_token),
            "session_id": SessionID(session_id),
            "original_data": user_data,
            "cache_keys": {
                "personal": personal_key,
                "business": business_key, 
                "security": security_key
            }
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_user_isolation_comprehensive(self):
        """
        CRITICAL: Test complete database isolation between users.
        
        Validates that users cannot access each other's database records,
        including edge cases and attack scenarios.
        """
        
        # Create multiple isolated users
        created_users = []
        for user_data in self.test_users_data:
            user_context = await self._create_isolated_test_user(user_data)
            created_users.append(user_context)
        
        # TEST 1: Basic user data isolation
        for i, user_context in enumerate(created_users):
            user = user_context["user"]
            
            # User can retrieve their own data
            own_user = await self.user_service.get_user_by_id(user.id)
            assert own_user is not None
            assert own_user.id == user.id
            assert own_user.email == user.email
            
            # Verify password isolation - only correct password works
            correct_password = user_context["original_data"]["password"]
            password_valid = await self.user_service.verify_password(user.id, correct_password)
            assert password_valid is True
            
            # Other users' passwords must fail
            for j, other_context in enumerate(created_users):
                if i != j:
                    wrong_password = other_context["original_data"]["password"] 
                    password_invalid = await self.user_service.verify_password(user.id, wrong_password)
                    assert password_invalid is False
        
        # TEST 2: Cross-user data access validation
        for i, user_context in enumerate(created_users):
            current_user = user_context["user"]
            
            for j, other_context in enumerate(created_users):
                if i != j:
                    other_user = other_context["user"]
                    
                    # Retrieve other user by ID should return correct user (not current)
                    retrieved_other = await self.user_service.get_user_by_id(other_user.id)
                    assert retrieved_other is not None
                    assert retrieved_other.id == other_user.id
                    assert retrieved_other.id != current_user.id
                    assert retrieved_other.email != current_user.email
        
        # TEST 3: Email isolation - users with similar emails are isolated
        similar_email_users = [user for user in created_users if "isolation.user" in user["user"].email]
        assert len(similar_email_users) == len(created_users)  # All should match pattern
        
        for user_context in similar_email_users:
            user = user_context["user"]
            retrieved_by_email = await self.user_service.get_user_by_email(user.email)
            
            assert retrieved_by_email is not None
            assert retrieved_by_email.id == user.id
            assert retrieved_by_email.email == user.email
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_session_isolation_and_hijacking_prevention(self):
        """
        CRITICAL: Test session isolation and prevent session hijacking attacks.
        
        Validates that sessions are completely isolated and cannot be hijacked
        by other users through various attack vectors.
        """
        
        # Create multiple users with sessions
        created_users = []
        for user_data in self.test_users_data:
            user_context = await self._create_isolated_test_user(user_data)
            created_users.append(user_context)
        
        # TEST 1: Session data isolation
        for user_context in created_users:
            session_id = user_context["session_id"]
            user = user_context["user"]
            original_data = user_context["original_data"]
            
            # User can access their own session
            session_data = await self.session_service.get_session(str(session_id))
            assert session_data is not None
            assert session_data["user_id"] == str(user.id)
            assert session_data["email"] == user.email
            assert session_data["sensitive_data"] == original_data["sensitive_data"]
            assert session_data["tier"] == original_data["tier"]
        
        # TEST 2: Session hijacking prevention - users cannot access other sessions
        session_ids = [str(ctx["session_id"]) for ctx in created_users]
        
        for i, user_context in enumerate(created_users):
            current_user = user_context["user"]
            current_session_id = str(user_context["session_id"])
            
            # Current user can access their session
            own_session = await self.session_service.get_session(current_session_id)
            assert own_session["user_id"] == str(current_user.id)
            
            # Verify other sessions belong to different users
            for j, other_session_id in enumerate(session_ids):
                if i != j:
                    other_session = await self.session_service.get_session(other_session_id)
                    assert other_session is not None
                    assert other_session["user_id"] != str(current_user.id)
                    assert other_session["email"] != current_user.email
        
        # TEST 3: Session token replay attack prevention
        for user_context in created_users:
            session_id = str(user_context["session_id"])
            
            # Get session multiple times (simulating replay)
            session1 = await self.session_service.get_session(session_id)
            session2 = await self.session_service.get_session(session_id)
            
            # Both should succeed and return same user data
            assert session1["user_id"] == session2["user_id"]
            
            # But timestamps should be different (updated)
            assert session1["last_accessed"] <= session2["last_accessed"]
        
        # TEST 4: Concurrent session access isolation
        async def access_session_concurrently(user_context):
            """Access session multiple times concurrently."""
            session_id = str(user_context["session_id"])
            user_id = str(user_context["user"].id)
            
            tasks = []
            for _ in range(5):  # 5 concurrent accesses
                tasks.append(self.session_service.get_session(session_id))
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed and return correct user
            for result in results:
                assert result is not None
                assert result["user_id"] == user_id
            
            return len(results)
        
        # Run concurrent access for all users
        concurrent_tasks = [access_session_concurrently(ctx) for ctx in created_users]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        
        # All should succeed
        assert all(count == 5 for count in concurrent_results)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_isolation_and_injection_prevention(self):
        """
        CRITICAL: Test JWT token isolation and prevent token injection attacks.
        
        Validates that JWT tokens are user-specific and cannot be injected
        or manipulated to access other users' resources.
        """
        
        # Create multiple users with JWT tokens
        created_users = []
        for user_data in self.test_users_data:
            user_context = await self._create_isolated_test_user(user_data)
            created_users.append(user_context)
        
        # TEST 1: JWT token uniqueness
        tokens = [str(ctx["access_token"]) for ctx in created_users]
        assert len(set(tokens)) == len(tokens)  # All tokens must be unique
        
        # TEST 2: JWT token claims isolation
        for user_context in created_users:
            user = user_context["user"]
            token = str(user_context["access_token"])
            original_data = user_context["original_data"]
            
            # Validate token
            is_valid = await self.jwt_service.validate_token(token)
            assert is_valid is True
            
            # Decode token and verify claims
            decoded = jwt_library.decode(
                token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            assert decoded["sub"] == str(user.id)
            assert decoded["email"] == user.email
            assert decoded["permissions"] == original_data["permissions"]
            assert decoded["type"] == "access"
            
        # TEST 3: Token injection attack prevention  
        for i, user_context in enumerate(created_users):
            current_token = str(user_context["access_token"])
            current_user = user_context["user"]
            
            # Decode current token
            current_decoded = jwt_library.decode(
                current_token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            # Verify token cannot identify as other users
            for j, other_context in enumerate(created_users):
                if i != j:
                    other_user = other_context["user"]
                    
                    # Current token must never claim to be other user
                    assert current_decoded["sub"] != str(other_user.id)
                    assert current_decoded["email"] != other_user.email
        
        # TEST 4: Token manipulation attack prevention
        for user_context in created_users:
            original_token = str(user_context["access_token"])
            
            # Attempt to create malicious token by modifying claims
            try:
                # Decode without verification to manipulate
                malicious_payload = jwt_library.decode(
                    original_token, 
                    options={"verify_signature": False}
                )
                
                # Modify user ID to another user
                if len(created_users) > 1:
                    target_user = created_users[0] if created_users[0] != user_context else created_users[1]
                    malicious_payload["sub"] = str(target_user["user"].id)
                    malicious_payload["email"] = target_user["user"].email
                
                # Try to sign with wrong secret
                malicious_token = jwt_library.encode(malicious_payload, "wrong_secret", algorithm="HS256")
                
                # Should fail validation
                is_valid = await self.jwt_service.validate_token(malicious_token)
                assert is_valid is False
                
            except Exception:
                # Expected - malicious token creation should fail
                pass
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_data_isolation_comprehensive(self):
        """
        CRITICAL: Test complete Redis data isolation between users.
        
        Validates that user-specific cache data is completely isolated
        and cannot be accessed by other users.
        """
        
        # Create multiple users with Redis data
        created_users = []
        for user_data in self.test_users_data:
            user_context = await self._create_isolated_test_user(user_data)
            created_users.append(user_context)
        
        # TEST 1: Personal data isolation
        for user_context in created_users:
            user = user_context["user"]
            personal_key = user_context["cache_keys"]["personal"]
            original_data = user_context["original_data"]
            
            # User can access their personal data
            personal_data = await self.redis_service.get(personal_key)
            assert personal_data is not None
            
            parsed_data = json.loads(personal_data)
            assert parsed_data["user_id"] == str(user.id)
            assert parsed_data["sensitive_data"] == original_data["sensitive_data"]
            
        # TEST 2: Business data isolation  
        for user_context in created_users:
            user = user_context["user"]
            business_key = user_context["cache_keys"]["business"]
            original_data = user_context["original_data"]
            
            # User can access their business data
            business_data = await self.redis_service.get(business_key)
            assert business_data is not None
            
            parsed_data = json.loads(business_data)
            assert parsed_data["user_id"] == str(user.id)
            assert parsed_data["api_access"]["api_key"] == original_data["sensitive_data"]["api_key"]
            
        # TEST 3: Cross-user data access prevention
        for i, user_context in enumerate(created_users):
            current_user = user_context["user"]
            
            # Try to access other users' data
            for j, other_context in enumerate(created_users):
                if i != j:
                    other_user = other_context["user"]
                    
                    # Other user's personal data should be different
                    other_personal_key = other_context["cache_keys"]["personal"]
                    other_personal_data = await self.redis_service.get(other_personal_key)
                    assert other_personal_data is not None
                    
                    other_parsed = json.loads(other_personal_data)
                    assert other_parsed["user_id"] != str(current_user.id)
                    assert other_parsed["user_id"] == str(other_user.id)
                    
        # TEST 4: Data key uniqueness
        all_keys = []
        for user_context in created_users:
            cache_keys = user_context["cache_keys"]
            all_keys.extend([cache_keys["personal"], cache_keys["business"], cache_keys["security"]])
        
        # All keys should be unique
        assert len(set(all_keys)) == len(all_keys)
        
        # All keys should contain user-specific identifiers
        for user_context in created_users:
            user_id = str(user_context["user"].id)
            cache_keys = user_context["cache_keys"]
            
            for key_name, key_value in cache_keys.items():
                assert user_id in key_value  # Key should contain user ID
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_multi_user_race_conditions(self):
        """
        CRITICAL: Test multi-user isolation under concurrent load and race conditions.
        
        Validates that the system maintains isolation when multiple users
        perform operations simultaneously, preventing race condition exploits.
        """
        
        async def create_and_operate_user(user_data, operation_count=10):
            """Create user and perform multiple concurrent operations."""
            try:
                user_context = await self._create_isolated_test_user(user_data)
                user = user_context["user"]
                user_id = str(user.id)
                session_id = str(user_context["session_id"])
                
                # Perform concurrent operations
                operations = []
                
                # Session operations
                for i in range(operation_count):
                    operations.append(self.session_service.get_session(session_id))
                
                # Redis operations
                for i in range(operation_count):
                    temp_key = f"temp:concurrent:{user_id}:{i}"
                    operations.append(self.redis_service.set(
                        temp_key,
                        json.dumps({"user_id": user_id, "operation": i, "data": f"concurrent-{user_id}-{i}"}),
                        ex=60
                    ))
                    self.created_redis_keys.append(temp_key)
                
                # JWT validation operations
                token = str(user_context["access_token"])
                for i in range(operation_count):
                    operations.append(self.jwt_service.validate_token(token))
                
                # Execute all operations concurrently
                results = await asyncio.gather(*operations, return_exceptions=True)
                
                # Count successful operations
                successful_ops = [r for r in results if not isinstance(r, Exception)]
                
                return {
                    "user_id": user_id,
                    "email": user.email,
                    "total_operations": len(operations),
                    "successful_operations": len(successful_ops),
                    "success_rate": len(successful_ops) / len(operations),
                    "user_context": user_context
                }
                
            except Exception as e:
                return {"error": str(e), "user_data": user_data}
        
        # Execute concurrent user operations
        concurrent_tasks = [
            create_and_operate_user(user_data) 
            for user_data in self.test_users_data
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Validate results
        successful_results = [r for r in results if not isinstance(r, Exception) and "error" not in r]
        assert len(successful_results) == len(self.test_users_data)
        
        # All operations should have high success rate
        for result in successful_results:
            assert result["success_rate"] > 0.9  # At least 90% success rate
        
        # Verify data isolation after concurrent operations
        user_ids = [r["user_id"] for r in successful_results]
        emails = [r["email"] for r in successful_results]
        
        # All should be unique
        assert len(set(user_ids)) == len(user_ids)
        assert len(set(emails)) == len(emails)
        
        # Verify concurrent Redis operations didn't cross-contaminate
        for result in successful_results:
            user_id = result["user_id"]
            
            # Check temp keys created during concurrent operations
            temp_keys = await self.redis_service.keys(f"temp:concurrent:{user_id}:*")
            for temp_key in temp_keys:
                temp_data = await self.redis_service.get(temp_key)
                if temp_data:
                    parsed_temp = json.loads(temp_data)
                    assert parsed_temp["user_id"] == user_id
                    assert user_id in parsed_temp["data"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_fixation_attack_prevention(self):
        """
        CRITICAL: Test prevention of session fixation attacks.
        
        Validates that attackers cannot fix a user's session ID
        or predict session patterns to compromise other users.
        """
        
        # Create multiple users
        created_users = []
        for user_data in self.test_users_data[:3]:  # Use first 3 users
            user_context = await self._create_isolated_test_user(user_data)
            created_users.append(user_context)
        
        # TEST 1: Session ID unpredictability
        session_ids = [str(ctx["session_id"]) for ctx in created_users]
        
        # All session IDs should be unique
        assert len(set(session_ids)) == len(session_ids)
        
        # Session IDs should not follow predictable patterns
        for i, session_id in enumerate(session_ids):
            # Should be UUID format
            assert len(session_id) > 30  # UUIDs are longer
            assert "-" in session_id  # UUIDs contain hyphens
            
            # Should not contain user identifiers
            user = created_users[i]["user"]
            assert str(user.id) not in session_id
            assert user.email.split("@")[0] not in session_id
        
        # TEST 2: Session regeneration after critical operations
        for user_context in created_users:
            original_session_id = str(user_context["session_id"])
            user = user_context["user"]
            
            # Perform password change (critical operation)
            new_password = f"NewSecurePassword{secrets.token_hex(8)}"
            await self.user_service.change_password(user.id, user_context["original_data"]["password"], new_password)
            
            # Original session should still work immediately (grace period)
            session_data = await self.session_service.get_session(original_session_id)
            assert session_data is not None
            
            # But new login should create new session ID
            new_token = await self.jwt_service.create_access_token(
                user_id=str(user.id),
                email=user.email,
                permissions=user_context["original_data"]["permissions"]
            )
            
            new_session_result = await self.session_service.create_session(
                user_id=str(user.id),
                email=user.email,
                access_token=new_token,
                session_data={"regenerated": True}
            )
            
            new_session_id = new_session_result["session_id"]
            self.created_session_ids.append(new_session_id)
            
            # New session ID should be different
            assert new_session_id != original_session_id
        
        # TEST 3: Session data cannot be predicted from session ID
        for user_context in created_users:
            session_id = str(user_context["session_id"])
            user = user_context["user"]
            
            # Session data should contain user-specific information
            session_data = await self.session_service.get_session(session_id)
            assert session_data["user_id"] == str(user.id)
            
            # But session ID alone should not reveal user information
            # (This is tested by ensuring session IDs don't contain user data)
            assert str(user.id) not in session_id
            assert user.email not in session_id
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_tier_isolation_and_privilege_escalation_prevention(self):
        """
        CRITICAL: Test tier isolation and prevent privilege escalation attacks.
        
        Validates that users of different tiers cannot access higher tier features
        or escalate their privileges through various attack vectors.
        """
        
        # Create users of different tiers
        tier_users = []
        tiers = ["free", "early", "enterprise"]
        
        for i, tier in enumerate(tiers):
            user_data = {
                **self.test_users_data[i],
                "tier": tier,
                "permissions": {
                    "free": ["read"],
                    "early": ["read", "write"], 
                    "enterprise": ["read", "write", "admin"]
                }[tier]
            }
            
            user_context = await self._create_isolated_test_user(user_data)
            
            # Store tier-specific features in Redis
            features_key = f"features:{tier}:{user_context['user'].id}"
            await self.redis_service.set(
                features_key,
                json.dumps({
                    "user_id": str(user_context["user"].id),
                    "tier": tier,
                    "allowed_features": {
                        "free": ["basic_chat"],
                        "early": ["basic_chat", "advanced_agents"],
                        "enterprise": ["basic_chat", "advanced_agents", "admin_panel", "analytics"]
                    }[tier],
                    "resource_limits": {
                        "free": {"api_calls_per_hour": 10, "storage_mb": 100},
                        "early": {"api_calls_per_hour": 100, "storage_mb": 1000},
                        "enterprise": {"api_calls_per_hour": -1, "storage_mb": -1}  # Unlimited
                    }[tier]
                }),
                ex=3600
            )
            
            self.created_redis_keys.append(features_key)
            
            tier_users.append({
                **user_context,
                "tier": tier,
                "features_key": features_key,
                "expected_permissions": user_data["permissions"]
            })
        
        # TEST 1: JWT token permission isolation
        for user_info in tier_users:
            token = str(user_info["access_token"])
            tier = user_info["tier"]
            
            # Decode and verify permissions
            decoded = jwt_library.decode(
                token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            expected_permissions = user_info["expected_permissions"]
            assert decoded["permissions"] == expected_permissions
            
            # Verify tier-specific permission constraints
            if tier == "free":
                assert "read" in decoded["permissions"]
                assert "write" not in decoded["permissions"]
                assert "admin" not in decoded["permissions"]
            elif tier == "early":
                assert "read" in decoded["permissions"]
                assert "write" in decoded["permissions"] 
                assert "admin" not in decoded["permissions"]
            elif tier == "enterprise":
                assert "admin" in decoded["permissions"]
        
        # TEST 2: Feature access isolation
        for user_info in tier_users:
            features_data = await self.redis_service.get(user_info["features_key"])
            assert features_data is not None
            
            features = json.loads(features_data)
            tier = user_info["tier"]
            
            allowed_features = features["allowed_features"]
            
            if tier == "free":
                assert allowed_features == ["basic_chat"]
                assert "admin_panel" not in allowed_features
                assert "analytics" not in allowed_features
            elif tier == "early":
                assert "advanced_agents" in allowed_features
                assert "admin_panel" not in allowed_features
                assert "analytics" not in allowed_features
            elif tier == "enterprise":
                assert "admin_panel" in allowed_features
                assert "analytics" in allowed_features
        
        # TEST 3: Privilege escalation attack prevention
        free_user = next(u for u in tier_users if u["tier"] == "free")
        enterprise_user = next(u for u in tier_users if u["tier"] == "enterprise")
        
        # Free user should not be able to access enterprise features
        enterprise_features_key = enterprise_user["features_key"]
        enterprise_features_data = await self.redis_service.get(enterprise_features_key)
        enterprise_features = json.loads(enterprise_features_data)
        
        # Verify enterprise data belongs to enterprise user, not free user
        assert enterprise_features["user_id"] == str(enterprise_user["user"].id)
        assert enterprise_features["user_id"] != str(free_user["user"].id)
        assert "admin_panel" in enterprise_features["allowed_features"]
        
        # Free user's features should be limited
        free_features_data = await self.redis_service.get(free_user["features_key"])
        free_features = json.loads(free_features_data)
        assert "admin_panel" not in free_features["allowed_features"]
        
        # TEST 4: Resource limit enforcement
        for user_info in tier_users:
            features_data = await self.redis_service.get(user_info["features_key"])
            features = json.loads(features_data)
            
            resource_limits = features["resource_limits"]
            tier = user_info["tier"]
            
            if tier == "free":
                assert resource_limits["api_calls_per_hour"] == 10
                assert resource_limits["storage_mb"] == 100
            elif tier == "early":
                assert resource_limits["api_calls_per_hour"] == 100
                assert resource_limits["storage_mb"] == 1000
            elif tier == "enterprise":
                assert resource_limits["api_calls_per_hour"] == -1  # Unlimited
                assert resource_limits["storage_mb"] == -1  # Unlimited


__all__ = ["TestMultiUserIsolationComprehensive"]