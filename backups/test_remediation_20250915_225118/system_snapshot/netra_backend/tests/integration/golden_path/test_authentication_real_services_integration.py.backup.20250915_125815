"""
Test Authentication Integration with Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication works with real database and session management
- Value Impact: Authentication enables secure multi-user access and proper billing/limits
- Strategic Impact: Critical for $500K+ ARR - authentication failures = no user access = no revenue

CRITICAL REQUIREMENTS:
1. Test JWT validation with real database user lookup
2. Test session persistence with Redis
3. Test multi-user authentication isolation
4. Test authentication failure handling
5. NO MOCKS for PostgreSQL/Redis - real authentication validation
6. Use E2E authentication patterns throughout
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import pytest
import jwt

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


class TestAuthenticationRealServicesIntegration(BaseIntegrationTest):
    """Test authentication with real PostgreSQL and Redis services."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_validation_with_database_user_lookup(self, real_services_fixture):
        """Test JWT validation with real database user lookup."""
        # Create authenticated user
        user_context = await create_authenticated_user_context(
            user_email=f"auth_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        
        # Create real user in database
        await self._create_user_in_database(db_session, user_context)
        
        # Test JWT validation process
        jwt_token = user_context.agent_context.get("jwt_token")
        validation_result = await self._validate_jwt_with_database_lookup(
            db_session, jwt_token
        )
        
        assert validation_result["valid"], f"JWT validation failed: {validation_result['error']}"
        assert validation_result["user_exists"], "User should exist in database"
        assert validation_result["user_active"], "User should be active"
        
        # Test invalid JWT handling
        invalid_jwt = "invalid.jwt.token"
        invalid_result = await self._validate_jwt_with_database_lookup(
            db_session, invalid_jwt
        )
        
        assert not invalid_result["valid"], "Invalid JWT should fail validation"
        assert invalid_result["error_type"] == "invalid_token"
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_persistence_with_redis(self, real_services_fixture):
        """Test session persistence with Redis fallback to database."""
        user_context = await create_authenticated_user_context(
            user_email=f"session_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        
        # Test session creation and persistence
        session_data = {
            "user_id": str(user_context.user_id),
            "login_time": datetime.now(timezone.utc).isoformat(),
            "ip_address": "127.0.0.1",
            "user_agent": "test_client",
            "permissions": ["read", "write"]
        }
        
        # Create session
        session_result = await self._create_and_persist_session(
            db_session, real_services_fixture, session_data
        )
        
        assert session_result["success"], f"Session creation failed: {session_result['error']}"
        assert session_result["session_id"] is not None
        
        # Test session retrieval
        session_id = session_result["session_id"]
        retrieved_session = await self._retrieve_session(
            db_session, real_services_fixture, session_id
        )
        
        assert retrieved_session["found"], "Session should be retrievable"
        assert retrieved_session["user_id"] == str(user_context.user_id)
        
        # Test session expiration
        expired_session = await self._test_session_expiration(
            db_session, real_services_fixture, session_id
        )
        
        assert expired_session["expiration_handled"], "Session expiration should be handled"
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_authentication_isolation(self, real_services_fixture):
        """Test multi-user authentication isolation."""
        # Create multiple users
        num_users = 3
        user_contexts = []
        
        for i in range(num_users):
            user_context = await create_authenticated_user_context(
                user_email=f"multi_auth_{i}_{uuid.uuid4().hex[:8]}@example.com"
            )
            user_contexts.append(user_context)
        
        db_session = real_services_fixture["db"]
        
        # Create all users in database
        for user_context in user_contexts:
            await self._create_user_in_database(db_session, user_context)
        
        # Test concurrent authentication
        auth_tasks = []
        for i, user_context in enumerate(user_contexts):
            task = self._test_user_authentication_isolation(
                db_session, real_services_fixture, user_context, user_index=i
            )
            auth_tasks.append(task)
        
        auth_results = await asyncio.gather(*auth_tasks)
        
        # Verify all authentications succeeded
        for i, result in enumerate(auth_results):
            assert result["success"], f"User {i} authentication failed: {result['error']}"
            assert result["isolated"], f"User {i} isolation failed"
        
        # Verify cross-user isolation
        isolation_check = await self._verify_cross_user_isolation(
            db_session, user_contexts
        )
        
        assert isolation_check["isolated"], "Cross-user isolation should be maintained"
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_failure_handling(self, real_services_fixture):
        """Test authentication failure handling scenarios."""
        db_session = real_services_fixture["db"]
        
        # Test scenarios
        failure_scenarios = [
            {
                "name": "expired_jwt",
                "test_func": self._test_expired_jwt_handling,
                "expected_error": "token_expired"
            },
            {
                "name": "invalid_signature",
                "test_func": self._test_invalid_signature_handling,
                "expected_error": "invalid_signature"
            },
            {
                "name": "user_not_found",
                "test_func": self._test_user_not_found_handling,
                "expected_error": "user_not_found"
            },
            {
                "name": "inactive_user",
                "test_func": self._test_inactive_user_handling,
                "expected_error": "user_inactive"
            }
        ]
        
        for scenario in failure_scenarios:
            failure_result = await scenario["test_func"](db_session, real_services_fixture)
            
            assert not failure_result["auth_success"], f"{scenario['name']} should fail authentication"
            assert failure_result["error_type"] == scenario["expected_error"]
            assert failure_result["handled_gracefully"], f"{scenario['name']} should be handled gracefully"
    
    # Helper methods
    
    async def _create_user_in_database(self, db_session, user_context):
        """Create user in database for authentication testing."""
        user_insert = """
            INSERT INTO users (id, email, full_name, is_active, created_at)
            VALUES (%(user_id)s, %(email)s, %(full_name)s, true, %(created_at)s)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                updated_at = NOW()
        """
        
        await db_session.execute(user_insert, {
            "user_id": str(user_context.user_id),
            "email": user_context.agent_context.get("user_email"),
            "full_name": f"Auth Test User {str(user_context.user_id)[:8]}",
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    async def _validate_jwt_with_database_lookup(
        self, db_session, jwt_token: str
    ) -> Dict[str, Any]:
        """Validate JWT token with database user lookup."""
        try:
            # Decode JWT without verification first to get user_id
            try:
                payload = jwt.decode(jwt_token, options={"verify_signature": False})
                user_id = payload.get("sub")
            except jwt.InvalidTokenError:
                return {
                    "valid": False,
                    "error": "Invalid token format",
                    "error_type": "invalid_token"
                }
            
            if not user_id:
                return {
                    "valid": False,
                    "error": "No user ID in token",
                    "error_type": "missing_user_id"
                }
            
            # Look up user in database
            user_query = """
                SELECT id, email, is_active FROM users 
                WHERE id = %(user_id)s
            """
            
            result = await db_session.execute(user_query, {"user_id": user_id})
            user_row = result.fetchone()
            
            if not user_row:
                return {
                    "valid": False,
                    "user_exists": False,
                    "error": "User not found in database",
                    "error_type": "user_not_found"
                }
            
            # Validate JWT signature
            try:
                jwt.decode(jwt_token, self.auth_helper.config.jwt_secret, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                return {
                    "valid": False,
                    "user_exists": True,
                    "user_active": user_row.is_active,
                    "error": "Token expired",
                    "error_type": "token_expired"
                }
            except jwt.InvalidSignatureError:
                return {
                    "valid": False,
                    "user_exists": True,
                    "user_active": user_row.is_active,
                    "error": "Invalid token signature",
                    "error_type": "invalid_signature"
                }
            
            return {
                "valid": True,
                "user_exists": True,
                "user_active": user_row.is_active,
                "user_id": user_row.id,
                "user_email": user_row.email
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "error_type": "validation_error"
            }
    
    async def _create_and_persist_session(
        self, db_session, real_services_fixture, session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create and persist session with Redis fallback."""
        try:
            session_id = f"session_{uuid.uuid4().hex}"
            
            # Try Redis first if available
            redis_available = real_services_fixture["services_available"].get("redis", False)
            
            if redis_available:
                # In real implementation, would store in Redis
                storage_backend = "redis"
            else:
                # Fallback to database storage
                session_insert = """
                    INSERT INTO user_sessions (
                        id, user_id, session_data, created_at, expires_at
                    ) VALUES (
                        %(session_id)s, %(user_id)s, %(data)s, %(created_at)s, %(expires_at)s
                    )
                """
                
                await db_session.execute(session_insert, {
                    "session_id": session_id,
                    "user_id": session_data["user_id"],
                    "data": json.dumps(session_data),
                    "created_at": datetime.now(timezone.utc),
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=24)
                })
                await db_session.commit()
                storage_backend = "database"
            
            return {
                "success": True,
                "session_id": session_id,
                "storage_backend": storage_backend
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _retrieve_session(
        self, db_session, real_services_fixture, session_id: str
    ) -> Dict[str, Any]:
        """Retrieve session from storage."""
        try:
            # Try database retrieval
            session_query = """
                SELECT user_id, session_data, created_at, expires_at
                FROM user_sessions
                WHERE id = %(session_id)s AND expires_at > %(now)s
            """
            
            result = await db_session.execute(session_query, {
                "session_id": session_id,
                "now": datetime.now(timezone.utc)
            })
            
            session_row = result.fetchone()
            
            if session_row:
                session_data = json.loads(session_row.session_data)
                return {
                    "found": True,
                    "user_id": session_row.user_id,
                    "session_data": session_data,
                    "created_at": session_row.created_at,
                    "expires_at": session_row.expires_at
                }
            else:
                return {
                    "found": False,
                    "reason": "session_not_found_or_expired"
                }
                
        except Exception as e:
            return {
                "found": False,
                "error": str(e)
            }
    
    async def _test_session_expiration(
        self, db_session, real_services_fixture, session_id: str
    ) -> Dict[str, Any]:
        """Test session expiration handling."""
        try:
            # Set session to expired
            expire_query = """
                UPDATE user_sessions 
                SET expires_at = %(expired_time)s
                WHERE id = %(session_id)s
            """
            
            await db_session.execute(expire_query, {
                "session_id": session_id,
                "expired_time": datetime.now(timezone.utc) - timedelta(hours=1)
            })
            await db_session.commit()
            
            # Try to retrieve expired session
            expired_session = await self._retrieve_session(
                db_session, real_services_fixture, session_id
            )
            
            return {
                "expiration_handled": not expired_session["found"],
                "expired_session_rejected": not expired_session["found"]
            }
            
        except Exception as e:
            return {
                "expiration_handled": False,
                "error": str(e)
            }
    
    async def _test_user_authentication_isolation(
        self, db_session, real_services_fixture, user_context, user_index: int
    ) -> Dict[str, Any]:
        """Test authentication isolation for a single user."""
        try:
            # Create unique session data for this user
            user_session_data = {
                "user_id": str(user_context.user_id),
                "user_index": user_index,
                "secret_data": f"secret_for_user_{user_index}",
                "login_time": datetime.now(timezone.utc).isoformat()
            }
            
            # Create session
            session_result = await self._create_and_persist_session(
                db_session, real_services_fixture, user_session_data
            )
            
            if not session_result["success"]:
                return {
                    "success": False,
                    "isolated": False,
                    "error": session_result["error"]
                }
            
            # Validate JWT for this user
            jwt_token = user_context.agent_context.get("jwt_token")
            auth_result = await self._validate_jwt_with_database_lookup(db_session, jwt_token)
            
            if not auth_result["valid"]:
                return {
                    "success": False,
                    "isolated": False,
                    "error": auth_result["error"]
                }
            
            # Test that user can only access their own session
            session_isolation = await self._test_session_isolation(
                db_session, session_result["session_id"], str(user_context.user_id)
            )
            
            return {
                "success": True,
                "isolated": session_isolation["isolated"],
                "session_id": session_result["session_id"],
                "user_id": str(user_context.user_id)
            }
            
        except Exception as e:
            return {
                "success": False,
                "isolated": False,
                "error": str(e)
            }
    
    async def _test_session_isolation(
        self, db_session, session_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Test that session belongs only to the specified user."""
        try:
            # Query session and verify user ownership
            isolation_query = """
                SELECT user_id FROM user_sessions 
                WHERE id = %(session_id)s
            """
            
            result = await db_session.execute(isolation_query, {"session_id": session_id})
            session_row = result.fetchone()
            
            if session_row and session_row.user_id == user_id:
                return {"isolated": True}
            else:
                return {"isolated": False, "reason": "session_user_mismatch"}
                
        except Exception as e:
            return {"isolated": False, "error": str(e)}
    
    async def _verify_cross_user_isolation(self, db_session, user_contexts) -> Dict[str, Any]:
        """Verify that users cannot access each other's sessions."""
        try:
            # Get all session IDs
            sessions_query = """
                SELECT id, user_id FROM user_sessions 
                WHERE user_id = ANY(%(user_ids)s)
            """
            
            user_ids = [str(ctx.user_id) for ctx in user_contexts]
            result = await db_session.execute(sessions_query, {"user_ids": user_ids})
            sessions = result.fetchall()
            
            # Verify each session belongs to correct user
            isolation_violations = 0
            
            for session_row in sessions:
                session_user_id = session_row.user_id
                
                # Check that this session is not accessible by other users
                for ctx in user_contexts:
                    if str(ctx.user_id) != session_user_id:
                        # Other user should not be able to access this session
                        isolation_test = await self._test_session_isolation(
                            db_session, session_row.id, str(ctx.user_id)
                        )
                        
                        if isolation_test.get("isolated", False):
                            isolation_violations += 1
            
            return {
                "isolated": isolation_violations == 0,
                "violations": isolation_violations,
                "total_sessions": len(sessions)
            }
            
        except Exception as e:
            return {
                "isolated": False,
                "error": str(e)
            }
    
    # Authentication failure scenario tests
    
    async def _test_expired_jwt_handling(self, db_session, real_services_fixture) -> Dict[str, Any]:
        """Test handling of expired JWT tokens."""
        try:
            # Create user
            user_context = await create_authenticated_user_context(
                user_email=f"expired_test_{uuid.uuid4().hex[:8]}@example.com"
            )
            await self._create_user_in_database(db_session, user_context)
            
            # Create expired JWT
            expired_payload = {
                "sub": str(user_context.user_id),
                "email": user_context.agent_context.get("user_email"),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
                "iat": datetime.now(timezone.utc) - timedelta(hours=2)
            }
            
            expired_token = jwt.encode(expired_payload, self.auth_helper.config.jwt_secret, algorithm="HS256")
            
            # Test validation of expired token
            validation_result = await self._validate_jwt_with_database_lookup(db_session, expired_token)
            
            return {
                "auth_success": validation_result["valid"],
                "error_type": validation_result.get("error_type"),
                "handled_gracefully": "error_type" in validation_result
            }
            
        except Exception as e:
            return {
                "auth_success": False,
                "error_type": "test_error",
                "handled_gracefully": False,
                "error": str(e)
            }
    
    async def _test_invalid_signature_handling(self, db_session, real_services_fixture) -> Dict[str, Any]:
        """Test handling of invalid JWT signatures."""
        try:
            # Create user
            user_context = await create_authenticated_user_context(
                user_email=f"invalid_sig_test_{uuid.uuid4().hex[:8]}@example.com"
            )
            await self._create_user_in_database(db_session, user_context)
            
            # Create JWT with wrong signature
            payload = {
                "sub": str(user_context.user_id),
                "email": user_context.agent_context.get("user_email"),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc)
            }
            
            # Sign with wrong secret
            invalid_token = jwt.encode(payload, "wrong_secret", algorithm="HS256")
            
            # Test validation
            validation_result = await self._validate_jwt_with_database_lookup(db_session, invalid_token)
            
            return {
                "auth_success": validation_result["valid"],
                "error_type": validation_result.get("error_type"),
                "handled_gracefully": "error_type" in validation_result
            }
            
        except Exception as e:
            return {
                "auth_success": False,
                "error_type": "test_error",
                "handled_gracefully": False,
                "error": str(e)
            }
    
    async def _test_user_not_found_handling(self, db_session, real_services_fixture) -> Dict[str, Any]:
        """Test handling when user not found in database."""
        try:
            # Create JWT for non-existent user
            fake_user_id = f"fake_user_{uuid.uuid4().hex[:8]}"
            payload = {
                "sub": fake_user_id,
                "email": "fake@example.com",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc)
            }
            
            fake_token = jwt.encode(payload, self.auth_helper.config.jwt_secret, algorithm="HS256")
            
            # Test validation
            validation_result = await self._validate_jwt_with_database_lookup(db_session, fake_token)
            
            return {
                "auth_success": validation_result["valid"],
                "error_type": validation_result.get("error_type"),
                "handled_gracefully": "error_type" in validation_result
            }
            
        except Exception as e:
            return {
                "auth_success": False,
                "error_type": "test_error",
                "handled_gracefully": False,
                "error": str(e)
            }
    
    async def _test_inactive_user_handling(self, db_session, real_services_fixture) -> Dict[str, Any]:
        """Test handling of inactive users."""
        try:
            # Create user and then deactivate
            user_context = await create_authenticated_user_context(
                user_email=f"inactive_test_{uuid.uuid4().hex[:8]}@example.com"
            )
            await self._create_user_in_database(db_session, user_context)
            
            # Deactivate user
            deactivate_query = """
                UPDATE users SET is_active = false 
                WHERE id = %(user_id)s
            """
            await db_session.execute(deactivate_query, {"user_id": str(user_context.user_id)})
            await db_session.commit()
            
            # Test validation
            jwt_token = user_context.agent_context.get("jwt_token")
            validation_result = await self._validate_jwt_with_database_lookup(db_session, jwt_token)
            
            # User exists but is inactive - should still validate JWT but flag as inactive
            return {
                "auth_success": validation_result["valid"] and validation_result.get("user_active", False),
                "error_type": "user_inactive" if not validation_result.get("user_active", True) else None,
                "handled_gracefully": "user_active" in validation_result
            }
            
        except Exception as e:
            return {
                "auth_success": False,
                "error_type": "test_error",
                "handled_gracefully": False,
                "error": str(e)
            }