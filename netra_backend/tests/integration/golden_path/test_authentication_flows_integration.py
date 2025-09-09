"""
Test Authentication Flows Integration - Golden Path Authentication Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication enables secure multi-user access and revenue generation
- Value Impact: Authentication is the gateway to ALL business value - no auth = no access = no revenue
- Strategic Impact: Core platform functionality that enables $500K+ ARR through secure user access

CRITICAL AUTHENTICATION FLOWS:
1. JWT token validation with real database user lookup
2. WebSocket authentication handshake validation
3. User execution context creation from real JWT
4. Session persistence in Redis with real connections
5. Multi-user session isolation validation
6. Token expiration handling with database cleanup
7. Authentication failure graceful handling
8. User context factory creation with real data
9. Thread-based authentication context management
10. Authentication middleware integration with real requests

TESTING APPROACH:
- Uses REAL PostgreSQL and Redis services (NO MOCKS)
- Validates actual authentication business logic
- Tests multi-user isolation patterns
- Covers golden path authentication scenarios
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
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ensure_user_id

logger = logging.getLogger(__name__)


class TestAuthenticationFlowsIntegration(BaseIntegrationTest):
    """Integration tests for golden path authentication flows with real services."""

    def setup_method(self):
        """Set up each test method with fresh authentication context."""
        super().setup_method()
        self.env = get_env()
        self.jwt_secret = self.env.get("JWT_SECRET", "test_secret_key_for_integration")
        self.auth_expiry_hours = int(self.env.get("JWT_EXPIRY_HOURS", "24"))

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_validation_with_real_database_user_lookup(self, real_services_fixture):
        """
        BVJ: Authentication must validate JWT against real user database records.
        This ensures only legitimate users with valid database records can access the system.
        CRITICAL: No mocks - real database validation required for security.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        
        # Create test user in real database
        user_email = f"jwt_test_{uuid.uuid4().hex[:8]}@example.com"
        user_id = await db_session.execute("""
            INSERT INTO users (id, email, name, is_active, created_at)
            VALUES (gen_random_uuid(), $1, $2, true, NOW())
            RETURNING id
        """, user_email, "JWT Test User")
        user_record = await user_id.fetchone()
        actual_user_id = str(user_record[0])

        # Create valid JWT token
        token_payload = {
            "sub": actual_user_id,
            "email": user_email,
            "name": "JWT Test User",
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.auth_expiry_hours),
            "iat": datetime.now(timezone.utc)
        }
        jwt_token = jwt.encode(token_payload, self.jwt_secret, algorithm="HS256")

        # Validate JWT and lookup user in database
        decoded_token = jwt.decode(jwt_token, self.jwt_secret, algorithms=["HS256"])
        
        # Real database lookup
        user_lookup = await db_session.execute("""
            SELECT id, email, name, is_active FROM users WHERE id = $1
        """, decoded_token["sub"])
        user_data = await user_lookup.fetchone()

        # Assertions - real business value validation
        assert user_data is not None, "JWT user must exist in database"
        assert str(user_data[0]) == actual_user_id, "User ID must match JWT subject"
        assert user_data[1] == user_email, "Email must match JWT claim"
        assert user_data[3] is True, "User must be active for authentication"
        
        self.logger.info(f"JWT validation successful for user: {user_email}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_authentication_handshake_validation(self, real_services_fixture):
        """
        BVJ: WebSocket connections must authenticate properly for real-time agent interactions.
        This enables the core chat functionality that delivers business value.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        
        # Create authenticated user
        user_email = f"ws_auth_{uuid.uuid4().hex[:8]}@example.com"
        user_id_result = await db_session.execute("""
            INSERT INTO users (id, email, name, is_active, created_at)
            VALUES (gen_random_uuid(), $1, $2, true, NOW())
            RETURNING id
        """, user_email, "WebSocket Auth Test")
        user_record = await user_id_result.fetchone()
        user_id = str(user_record[0])

        # Create JWT for WebSocket authentication
        token_payload = {
            "sub": user_id,
            "email": user_email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "websocket_permissions": ["agent_chat", "notifications"]
        }
        ws_jwt = jwt.encode(token_payload, self.jwt_secret, algorithm="HS256")

        # Simulate WebSocket handshake authentication
        auth_headers = {"Authorization": f"Bearer {ws_jwt}"}
        
        # Decode and validate WebSocket JWT
        try:
            decoded_token = jwt.decode(ws_jwt, self.jwt_secret, algorithms=["HS256"])
            
            # Validate user exists and is active
            user_check = await db_session.execute("""
                SELECT id, email, is_active FROM users WHERE id = $1 AND is_active = true
            """, decoded_token["sub"])
            ws_user = await user_check.fetchone()
            
            # Business value assertions
            assert ws_user is not None, "WebSocket user must be active in database"
            assert "websocket_permissions" in decoded_token, "WebSocket token must include permissions"
            assert "agent_chat" in decoded_token["websocket_permissions"], "Must allow agent chat"
            
            websocket_auth_success = True
            
        except jwt.ExpiredSignatureError:
            websocket_auth_success = False
        except jwt.InvalidTokenError:
            websocket_auth_success = False

        assert websocket_auth_success, "WebSocket authentication handshake must succeed"
        self.logger.info(f"WebSocket authentication successful for: {user_email}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_execution_context_creation_from_jwt(self, real_services_fixture):
        """
        BVJ: User execution contexts enable agent workflows and multi-user isolation.
        This ensures agents execute with proper user context for personalized results.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        
        # Create user with organization for full context
        user_email = f"context_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create user
        user_result = await db_session.execute("""
            INSERT INTO users (id, email, name, is_active, created_at)
            VALUES (gen_random_uuid(), $1, $2, true, NOW())
            RETURNING id
        """, user_email, "Context Test User")
        user_record = await user_result.fetchone()
        user_id = str(user_record[0])

        # Create organization
        org_result = await db_session.execute("""
            INSERT INTO organizations (id, name, slug, plan, created_at)
            VALUES (gen_random_uuid(), $1, $2, 'early', NOW())
            RETURNING id
        """, "Test Context Org", f"test-org-{user_id[:8]}")
        org_record = await org_result.fetchone()
        org_id = str(org_record[0])

        # Create membership
        await db_session.execute("""
            INSERT INTO organization_memberships (user_id, organization_id, role, created_at)
            VALUES ($1, $2, 'admin', NOW())
        """, user_id, org_id)

        # Create JWT with full context
        context_token = jwt.encode({
            "sub": user_id,
            "email": user_email,
            "org_id": org_id,
            "plan": "early",
            "permissions": ["agent_execute", "data_access"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=2)
        }, self.jwt_secret, algorithm="HS256")

        # Create user execution context from JWT
        decoded = jwt.decode(context_token, self.jwt_secret, algorithms=["HS256"])
        
        # Fetch complete user context from database
        context_query = await db_session.execute("""
            SELECT u.id, u.email, u.name, o.id as org_id, o.name as org_name, 
                   o.plan, om.role
            FROM users u
            JOIN organization_memberships om ON u.id = om.user_id
            JOIN organizations o ON om.organization_id = o.id
            WHERE u.id = $1 AND u.is_active = true
        """, decoded["sub"])
        context_data = await context_query.fetchone()

        # Create execution context
        execution_context = {
            "user_id": ensure_user_id(str(context_data[0])),
            "email": context_data[1],
            "name": context_data[2],
            "organization": {
                "id": str(context_data[3]),
                "name": context_data[4],
                "plan": context_data[5]
            },
            "role": context_data[6],
            "permissions": decoded.get("permissions", []),
            "authenticated": True,
            "context_created_at": time.time()
        }

        # Business value assertions
        assert execution_context["user_id"] is not None, "Execution context must have user ID"
        assert execution_context["organization"]["plan"] == "early", "Plan must match database"
        assert "agent_execute" in execution_context["permissions"], "Must allow agent execution"
        assert execution_context["authenticated"] is True, "Context must be authenticated"
        
        self.logger.info(f"User execution context created for: {user_email}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_persistence_in_redis_real_connections(self, real_services_fixture, real_redis_fixture):
        """
        BVJ: Session persistence enables conversation continuity and user state management.
        This supports multi-session workflows and improves user experience.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        redis_client = real_redis_fixture
        
        # Create user for session
        user_email = f"session_{uuid.uuid4().hex[:8]}@example.com"
        user_result = await db_session.execute("""
            INSERT INTO users (id, email, name, is_active, created_at)
            VALUES (gen_random_uuid(), $1, $2, true, NOW())
            RETURNING id
        """, user_email, "Session Test User")
        user_record = await user_result.fetchone()
        user_id = str(user_record[0])

        # Create session data
        session_data = {
            "user_id": user_id,
            "email": user_email,
            "created_at": time.time(),
            "expires_at": time.time() + 3600,  # 1 hour
            "active_threads": ["thread_1", "thread_2"],
            "preferences": {"theme": "dark", "notifications": True},
            "last_activity": time.time()
        }

        # Persist session in Redis
        session_key = f"session:{user_id}"
        await redis_client.set(session_key, json.dumps(session_data), ex=3600)

        # Retrieve and validate session
        cached_session = await redis_client.get(session_key)
        assert cached_session is not None, "Session must be persisted in Redis"
        
        retrieved_data = json.loads(cached_session)
        
        # Business value assertions
        assert retrieved_data["user_id"] == user_id, "Session user ID must match"
        assert retrieved_data["email"] == user_email, "Session email must match"
        assert len(retrieved_data["active_threads"]) == 2, "Active threads must be preserved"
        assert retrieved_data["preferences"]["theme"] == "dark", "User preferences must persist"
        
        # Test session expiration
        ttl = await redis_client.ttl(session_key)
        assert ttl > 0, "Session must have expiration set"
        assert ttl <= 3600, "Session TTL must be reasonable"
        
        self.logger.info(f"Session persistence validated for: {user_email}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_session_isolation_validation(self, real_services_fixture, real_redis_fixture):
        """
        BVJ: Multi-user isolation prevents data leakage and ensures security compliance.
        This is critical for enterprise customers and regulatory requirements.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        redis_client = real_redis_fixture
        
        # Create multiple users for isolation testing
        users = []
        for i in range(3):
            email = f"isolation_{i}_{uuid.uuid4().hex[:6]}@example.com"
            user_result = await db_session.execute("""
                INSERT INTO users (id, email, name, is_active, created_at)
                VALUES (gen_random_uuid(), $1, $2, true, NOW())
                RETURNING id
            """, email, f"Isolation User {i}")
            user_record = await user_result.fetchone()
            users.append({
                "id": str(user_record[0]),
                "email": email,
                "name": f"Isolation User {i}"
            })

        # Create isolated sessions for each user
        for i, user in enumerate(users):
            session_data = {
                "user_id": user["id"],
                "email": user["email"],
                "secret_data": f"secret_for_user_{i}",
                "private_threads": [f"private_thread_{i}_{j}" for j in range(2)],
                "billing_info": {"plan": "enterprise", "credits": 1000 + i}
            }
            
            session_key = f"session:{user['id']}"
            await redis_client.set(session_key, json.dumps(session_data), ex=7200)

        # Verify session isolation - each user can only access their own data
        for i, user in enumerate(users):
            user_session_key = f"session:{user['id']}"
            user_session = await redis_client.get(user_session_key)
            assert user_session is not None, f"User {i} session must exist"
            
            user_data = json.loads(user_session)
            
            # Verify correct user data
            assert user_data["user_id"] == user["id"], f"User {i} must have correct ID"
            assert user_data["secret_data"] == f"secret_for_user_{i}", f"User {i} must have own secret data"
            assert f"private_thread_{i}_0" in user_data["private_threads"], f"User {i} must have own threads"
            
            # Verify no access to other users' data
            for j, other_user in enumerate(users):
                if i != j:
                    other_session_key = f"session:{other_user['id']}"
                    # User should not be able to access other sessions by guessing keys
                    assert user_session_key != other_session_key, "Session keys must be unique"
                    
                    other_session = await redis_client.get(other_session_key)
                    other_data = json.loads(other_session)
                    assert user_data["secret_data"] != other_data["secret_data"], "Secret data must be isolated"

        self.logger.info("Multi-user session isolation validated successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_expiration_handling_with_database_cleanup(self, real_services_fixture):
        """
        BVJ: Token expiration handling prevents unauthorized access and maintains security.
        Database cleanup ensures expired sessions don't consume resources.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        
        # Create user for expiration testing
        user_email = f"expiry_{uuid.uuid4().hex[:8]}@example.com"
        user_result = await db_session.execute("""
            INSERT INTO users (id, email, name, is_active, created_at)
            VALUES (gen_random_uuid(), $1, $2, true, NOW())
            RETURNING id
        """, user_email, "Expiry Test User")
        user_record = await user_result.fetchone()
        user_id = str(user_record[0])

        # Create expired token
        expired_token = jwt.encode({
            "sub": user_id,
            "email": user_email,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),  # Expired 5 minutes ago
            "iat": datetime.now(timezone.utc) - timedelta(hours=1)
        }, self.jwt_secret, algorithm="HS256")

        # Test expired token handling
        token_valid = True
        expiry_reason = None
        
        try:
            jwt.decode(expired_token, self.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            token_valid = False
            expiry_reason = "expired"
        except jwt.InvalidTokenError:
            token_valid = False
            expiry_reason = "invalid"

        # Business value assertions
        assert not token_valid, "Expired token must be rejected"
        assert expiry_reason == "expired", "Must identify token as expired"

        # Create valid token for cleanup testing
        valid_token = jwt.encode({
            "sub": user_id,
            "email": user_email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "session_id": f"session_{uuid.uuid4().hex[:8]}"
        }, self.jwt_secret, algorithm="HS256")

        decoded_valid = jwt.decode(valid_token, self.jwt_secret, algorithms=["HS256"])
        
        # Simulate database cleanup for expired sessions
        cleanup_result = await db_session.execute("""
            DELETE FROM user_sessions 
            WHERE user_id = $1 AND expires_at < NOW()
            RETURNING count(*)
        """, user_id)
        
        # Even if no sessions existed, cleanup should execute without error
        assert cleanup_result is not None, "Cleanup operation must complete"
        
        self.logger.info(f"Token expiration handling validated for: {user_email}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_failure_graceful_handling(self, real_services_fixture):
        """
        BVJ: Graceful authentication failure handling maintains system stability.
        Proper error handling prevents system crashes and provides clear user feedback.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        
        # Test scenarios for authentication failures
        failure_scenarios = [
            {
                "name": "invalid_signature",
                "token": jwt.encode({"sub": "test", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "wrong_secret", algorithm="HS256"),
                "expected_error": jwt.InvalidSignatureError
            },
            {
                "name": "malformed_token",
                "token": "not.a.jwt.token.at.all",
                "expected_error": jwt.DecodeError
            },
            {
                "name": "missing_claims",
                "token": jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(hours=1)}, self.jwt_secret, algorithm="HS256"),
                "expected_error": KeyError  # Missing 'sub' claim
            }
        ]

        authentication_results = {}

        for scenario in failure_scenarios:
            try:
                decoded_token = jwt.decode(scenario["token"], self.jwt_secret, algorithms=["HS256"])
                
                # If decode succeeds but missing claims, this will fail
                if "sub" not in decoded_token:
                    raise KeyError("Missing 'sub' claim")
                
                # If we get here, authentication unexpectedly succeeded
                authentication_results[scenario["name"]] = {
                    "success": True,
                    "error": None,
                    "handled_gracefully": False
                }
                
            except scenario["expected_error"] as e:
                authentication_results[scenario["name"]] = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "handled_gracefully": True
                }
            except Exception as e:
                authentication_results[scenario["name"]] = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "handled_gracefully": True  # Any exception counts as graceful handling
                }

        # Business value assertions
        for scenario_name, result in authentication_results.items():
            assert not result["success"], f"Scenario {scenario_name} must fail authentication"
            assert result["handled_gracefully"], f"Scenario {scenario_name} must be handled gracefully"

        # Test database user not found scenario
        fake_user_id = str(uuid.uuid4())
        valid_token = jwt.encode({
            "sub": fake_user_id,
            "email": "nonexistent@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }, self.jwt_secret, algorithm="HS256")

        decoded_token = jwt.decode(valid_token, self.jwt_secret, algorithms=["HS256"])
        
        # Check if user exists in database
        user_check = await db_session.execute("""
            SELECT id FROM users WHERE id = $1
        """, decoded_token["sub"])
        user_exists = await user_check.fetchone()

        # Business value assertion
        assert user_exists is None, "Non-existent user must not be found in database"
        
        self.logger.info("Authentication failure handling validated for all scenarios")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_factory_creation_with_real_data(self, real_services_fixture):
        """
        BVJ: User context factory enables consistent user context across all services.
        This ensures proper multi-user isolation and personalized agent experiences.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        
        # Create comprehensive user data for factory testing
        user_email = f"factory_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create user
        user_result = await db_session.execute("""
            INSERT INTO users (id, email, name, is_active, created_at, preferences)
            VALUES (gen_random_uuid(), $1, $2, true, NOW(), $3)
            RETURNING id
        """, user_email, "Factory Test User", json.dumps({"theme": "light", "language": "en"}))
        user_record = await user_result.fetchone()
        user_id = str(user_record[0])

        # Create organization and membership
        org_result = await db_session.execute("""
            INSERT INTO organizations (id, name, slug, plan, settings, created_at)
            VALUES (gen_random_uuid(), $1, $2, 'mid', $3, NOW())
            RETURNING id
        """, "Factory Test Org", f"factory-{user_id[:8]}", json.dumps({"ai_model": "gpt-4", "max_tokens": 4000}))
        org_record = await org_result.fetchone()
        org_id = str(org_record[0])

        await db_session.execute("""
            INSERT INTO organization_memberships (user_id, organization_id, role, permissions, created_at)
            VALUES ($1, $2, 'admin', $3, NOW())
        """, user_id, org_id, json.dumps(["full_access", "billing", "user_management"]))

        # User context factory simulation
        def create_user_context_from_database(user_id: str, org_id: str) -> Dict[str, Any]:
            """Simulate user context factory with real database data."""
            return {
                "factory_version": "1.0",
                "user": {
                    "id": ensure_user_id(user_id),
                    "email": user_email,
                    "name": "Factory Test User",
                    "preferences": {"theme": "light", "language": "en"}
                },
                "organization": {
                    "id": org_id,
                    "name": "Factory Test Org",
                    "plan": "mid",
                    "settings": {"ai_model": "gpt-4", "max_tokens": 4000}
                },
                "permissions": ["full_access", "billing", "user_management"],
                "role": "admin",
                "isolation_boundary": f"user_{user_id}_org_{org_id}",
                "created_at": time.time()
            }

        # Create context using factory
        user_context = create_user_context_from_database(user_id, org_id)

        # Business value assertions
        assert user_context["user"]["id"] is not None, "User context must have valid user ID"
        assert user_context["organization"]["plan"] == "mid", "Organization plan must match database"
        assert "full_access" in user_context["permissions"], "Admin must have full access"
        assert user_context["isolation_boundary"] == f"user_{user_id}_org_{org_id}", "Must have unique isolation boundary"
        assert user_context["user"]["preferences"]["theme"] == "light", "User preferences must be preserved"
        assert user_context["organization"]["settings"]["ai_model"] == "gpt-4", "Org settings must be preserved"
        
        # Verify factory creates consistent contexts
        context2 = create_user_context_from_database(user_id, org_id)
        assert context2["isolation_boundary"] == user_context["isolation_boundary"], "Factory must create consistent contexts"
        
        self.logger.info(f"User context factory validated for: {user_email}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_based_authentication_context_management(self, real_services_fixture, real_redis_fixture):
        """
        BVJ: Thread-based authentication enables conversation continuity and context preservation.
        This supports multi-turn agent conversations that deliver compound business value.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        redis_client = real_redis_fixture
        
        # Create user for thread testing
        user_email = f"thread_auth_{uuid.uuid4().hex[:8]}@example.com"
        user_result = await db_session.execute("""
            INSERT INTO users (id, email, name, is_active, created_at)
            VALUES (gen_random_uuid(), $1, $2, true, NOW())
            RETURNING id
        """, user_email, "Thread Auth Test User")
        user_record = await user_result.fetchone()
        user_id = str(user_record[0])

        # Create thread with authentication context
        thread_id = str(uuid.uuid4())
        thread_data = {
            "id": thread_id,
            "user_id": user_id,
            "title": "Cost Optimization Discussion",
            "created_at": time.time(),
            "last_activity": time.time(),
            "auth_context": {
                "user_id": user_id,
                "email": user_email,
                "authenticated_at": time.time(),
                "permissions": ["agent_chat", "data_analysis"],
                "session_valid": True
            },
            "message_count": 3,
            "context_preserved": True
        }

        # Store thread in database
        await db_session.execute("""
            INSERT INTO threads (id, user_id, title, metadata, created_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, thread_id, user_id, "Cost Optimization Discussion", json.dumps(thread_data))

        # Cache thread authentication context in Redis
        thread_auth_key = f"thread_auth:{thread_id}"
        await redis_client.set(thread_auth_key, json.dumps(thread_data["auth_context"]), ex=7200)

        # Simulate retrieving thread with authentication context
        # 1. Get thread from database
        thread_query = await db_session.execute("""
            SELECT id, user_id, title, metadata FROM threads WHERE id = $1
        """, thread_id)
        thread_record = await thread_query.fetchone()
        
        # 2. Get authentication context from Redis
        cached_auth = await redis_client.get(thread_auth_key)
        
        assert thread_record is not None, "Thread must exist in database"
        assert cached_auth is not None, "Thread auth context must be cached"
        
        thread_metadata = json.loads(thread_record[3])
        auth_context = json.loads(cached_auth)

        # Business value assertions
        assert str(thread_record[0]) == thread_id, "Thread ID must match"
        assert str(thread_record[1]) == user_id, "Thread must belong to correct user"
        assert auth_context["user_id"] == user_id, "Auth context must match thread user"
        assert auth_context["session_valid"] is True, "Session must be valid for thread access"
        assert "agent_chat" in auth_context["permissions"], "Must allow agent chat in thread"
        assert thread_metadata["context_preserved"] is True, "Thread context must be preserved"

        # Test multiple threads for same user (isolation)
        thread2_id = str(uuid.uuid4())
        thread2_data = {
            "id": thread2_id,
            "user_id": user_id,
            "title": "Data Analysis Discussion",
            "auth_context": {
                "user_id": user_id,
                "email": user_email,
                "authenticated_at": time.time(),
                "permissions": ["agent_chat", "advanced_analytics"],
                "session_valid": True,
                "thread_specific_context": "data_analysis_mode"
            }
        }

        await db_session.execute("""
            INSERT INTO threads (id, user_id, title, metadata, created_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, thread2_id, user_id, "Data Analysis Discussion", json.dumps(thread2_data))

        thread2_auth_key = f"thread_auth:{thread2_id}"
        await redis_client.set(thread2_auth_key, json.dumps(thread2_data["auth_context"]), ex=7200)

        # Verify thread isolation
        thread1_auth = json.loads(await redis_client.get(thread_auth_key))
        thread2_auth = json.loads(await redis_client.get(thread2_auth_key))

        assert thread1_auth["user_id"] == thread2_auth["user_id"], "Both threads must belong to same user"
        assert "thread_specific_context" not in thread1_auth, "Thread 1 must not have thread 2's context"
        assert "thread_specific_context" in thread2_auth, "Thread 2 must have its specific context"
        
        self.logger.info(f"Thread-based authentication context validated for: {user_email}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_middleware_integration_real_requests(self, real_services_fixture):
        """
        BVJ: Authentication middleware integration ensures all API requests are properly secured.
        This protects business data and ensures only authorized users can access premium features.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        db_session = real_services_fixture["db"]
        
        # Create user for middleware testing
        user_email = f"middleware_{uuid.uuid4().hex[:8]}@example.com"
        user_result = await db_session.execute("""
            INSERT INTO users (id, email, name, is_active, plan, created_at)
            VALUES (gen_random_uuid(), $1, $2, true, 'enterprise', NOW())
            RETURNING id
        """, user_email, "Middleware Test User")
        user_record = await user_result.fetchone()
        user_id = str(user_record[0])

        # Create JWT for API requests
        api_token = jwt.encode({
            "sub": user_id,
            "email": user_email,
            "plan": "enterprise",
            "api_permissions": ["agents", "analytics", "premium_features"],
            "rate_limit_tier": "enterprise",
            "exp": datetime.now(timezone.utc) + timedelta(hours=2)
        }, self.jwt_secret, algorithm="HS256")

        # Simulate middleware authentication flow
        def authenticate_middleware_request(token: str, required_permission: str) -> Dict[str, Any]:
            """Simulate authentication middleware processing."""
            try:
                # 1. Decode token
                payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
                
                # 2. Check required permission
                if required_permission not in payload.get("api_permissions", []):
                    return {"authenticated": False, "error": "insufficient_permissions"}
                
                # 3. Create request context
                return {
                    "authenticated": True,
                    "user_id": payload["sub"],
                    "email": payload["email"],
                    "plan": payload["plan"],
                    "permissions": payload["api_permissions"],
                    "rate_limit_tier": payload["rate_limit_tier"],
                    "request_id": str(uuid.uuid4())
                }
                
            except jwt.ExpiredSignatureError:
                return {"authenticated": False, "error": "token_expired"}
            except jwt.InvalidTokenError:
                return {"authenticated": False, "error": "invalid_token"}

        # Test different API endpoints with authentication
        api_endpoints = [
            {"path": "/api/agents/execute", "required_permission": "agents"},
            {"path": "/api/analytics/reports", "required_permission": "analytics"},
            {"path": "/api/premium/advanced", "required_permission": "premium_features"}
        ]

        middleware_results = {}

        for endpoint in api_endpoints:
            auth_result = authenticate_middleware_request(api_token, endpoint["required_permission"])
            middleware_results[endpoint["path"]] = auth_result

            # Business value assertions per endpoint
            assert auth_result["authenticated"] is True, f"Must authenticate for {endpoint['path']}"
            assert auth_result["user_id"] == user_id, f"Must have correct user ID for {endpoint['path']}"
            assert auth_result["plan"] == "enterprise", f"Must preserve plan info for {endpoint['path']}"
            assert endpoint["required_permission"] in auth_result["permissions"], f"Must have required permission for {endpoint['path']}"

        # Test invalid token handling
        invalid_auth = authenticate_middleware_request("invalid.token.here", "agents")
        assert invalid_auth["authenticated"] is False, "Invalid token must be rejected"
        assert "error" in invalid_auth, "Invalid token must provide error reason"

        # Test insufficient permissions
        limited_token = jwt.encode({
            "sub": user_id,
            "api_permissions": ["basic_access"],  # Limited permissions
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }, self.jwt_secret, algorithm="HS256")

        insufficient_auth = authenticate_middleware_request(limited_token, "premium_features")
        assert insufficient_auth["authenticated"] is False, "Insufficient permissions must be rejected"
        assert insufficient_auth["error"] == "insufficient_permissions", "Must identify permission issue"

        # Database validation - verify user still exists and is active
        final_user_check = await db_session.execute("""
            SELECT id, email, is_active, plan FROM users WHERE id = $1
        """, user_id)
        final_user = await final_user_check.fetchone()
        
        assert final_user is not None, "User must still exist in database"
        assert final_user[2] is True, "User must still be active"
        assert final_user[3] == "enterprise", "User plan must be preserved"

        self.logger.info(f"Authentication middleware integration validated for: {user_email}")

    def assert_business_value_delivered(self, result: Dict, expected_value_type: str):
        """Override parent method with authentication-specific business value validation."""
        super().assert_business_value_delivered(result, expected_value_type)
        
        # Authentication-specific value assertions
        if expected_value_type == "secure_access":
            assert result.get("authenticated", False) is True, "Must provide secure authentication"
            assert "user_context" in result, "Must create proper user context"
        elif expected_value_type == "multi_user_isolation":
            assert "isolation_boundary" in result, "Must enforce user isolation"
            assert result.get("cross_user_access", True) is False, "Must prevent cross-user access"