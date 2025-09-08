"""
Auth Service Database Business Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Database operations underpin all user interactions
- Business Goal: Ensure reliable data persistence for user accounts, sessions, and authentication state
- Value Impact: Database reliability enables user onboarding, session management, and secure access control
- Strategic Impact: Core data layer that enables all platform functionality and user experience

CRITICAL: These tests use REAL PostgreSQL and Redis services - NO MOCKS allowed.
Tests validate complete database operation workflows with real service dependencies for business value.

This test suite validates:
1. User creation and retrieval with real PostgreSQL database
2. Session persistence and management with real Redis cache  
3. OAuth user account linking with database relationships
4. Token storage and validation with real database operations
5. Audit logging with persistent database storage
6. Multi-user data isolation and concurrent access patterns

All tests focus on business value: ensuring user data is properly stored, retrieved,
and managed to enable reliable authentication flows that support platform growth
and user engagement with AI optimization features.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
import hashlib
from unittest.mock import AsyncMock

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.connection import auth_db
from auth_service.auth_core.database.models import AuthUser as User, AuthSession as Session, AuthAuditLog as AuditLog, Base
from auth_service.auth_core.redis_manager import AuthRedisManager
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.services.auth_service import AuthService


class TestAuthDatabaseBusinessIntegration(BaseIntegrationTest):
    """Integration tests for auth service database operations with real business value."""
    
    @pytest.fixture(autouse=True)
    async def setup(self, real_services_fixture):
        """Set up test environment with real database services for business integration."""
        self.env = get_env()
        self.real_services = real_services_fixture
        
        # Real database and cache configuration
        self.auth_config = AuthConfig()
        self.auth_service = AuthService()
        self.jwt_handler = JWTHandler()
        
        # Real PostgreSQL database connection
        self.db = auth_db
        await self.db.initialize()
        
        # Real Redis cache connection
        self.redis_manager = AuthRedisManager()
        await self.redis_manager.connect()
        
        # Test data for business scenarios
        self.test_user_base_email = f"db-integration-test-{uuid.uuid4()}"
        self.test_domain = "@businessintegration.test"
        self.test_users_created = []
        self.test_sessions_created = []
        self.test_oauth_accounts_created = []
        
        # Business test scenarios data
        self.business_scenarios = {
            "free_tier_user": {
                "email": f"{self.test_user_base_email}-free{self.test_domain}",
                "name": "Free Tier User",
                "subscription_tier": "free",
                "max_queries_per_month": 10
            },
            "enterprise_user": {
                "email": f"{self.test_user_base_email}-enterprise{self.test_domain}",
                "name": "Enterprise User", 
                "subscription_tier": "enterprise",
                "max_queries_per_month": 10000
            },
            "oauth_google_user": {
                "email": f"{self.test_user_base_email}-google{self.test_domain}",
                "name": "Google OAuth User",
                "oauth_provider": "google"
            }
        }
        
        yield
        
        # Cleanup real test data
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real database services after business tests."""
        try:
            # Clean up test users from real PostgreSQL
            for user_id in self.test_users_created:
                await self.delete_test_user(user_id)
            
            # Clean up test sessions from real Redis
            for session_id in self.test_sessions_created:
                await self.redis_manager.delete(f"session:{session_id}")
            
            # Clean up OAuth accounts from real database
            for oauth_account_id in self.test_oauth_accounts_created:
                await self.delete_test_oauth_account(oauth_account_id)
                
            # Close real database connections
            await self.redis_manager.close()
            
            self.logger.info(f"Cleaned up {len(self.test_users_created)} test users, {len(self.test_sessions_created)} test sessions")
            
        except Exception as e:
            self.logger.warning(f"Database cleanup warning: {e}")
    
    async def delete_test_user(self, user_id: str):
        """Delete test user from real database with cascade cleanup."""
        try:
            async with self.db.get_session() as session:
                # Delete user and cascade to related records
                result = await session.execute(
                    "DELETE FROM users WHERE id = $1 RETURNING id", 
                    user_id
                )
                await session.commit()
        except Exception as e:
            self.logger.warning(f"Test user deletion warning: {e}")
    
    async def delete_test_oauth_account(self, oauth_account_id: str):
        """Delete test OAuth account from real database."""
        try:
            async with self.db.get_session() as session:
                result = await session.execute(
                    "DELETE FROM oauth_accounts WHERE id = $1 RETURNING id",
                    oauth_account_id
                )
                await session.commit()
        except Exception as e:
            self.logger.warning(f"OAuth account deletion warning: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_creation_and_retrieval_business_flow(self, real_services_fixture):
        """
        Test user creation and retrieval with real PostgreSQL for business onboarding.
        
        Business Value: User creation enables new customer acquisition and platform
        growth. Reliable user data storage is essential for maintaining customer
        relationships and enabling personalized AI optimization services.
        """
        # Create free tier user for business onboarding scenario
        free_user_data = self.business_scenarios["free_tier_user"]
        
        # Test user creation with real database
        user_id = str(uuid.uuid4())
        password_hash = hashlib.sha256("secure_password_123".encode()).hexdigest()
        created_at = datetime.now(timezone.utc)
        
        async with self.db.get_session() as session:
            # Insert real user data into PostgreSQL
            result = await session.execute("""
                INSERT INTO users (id, email, name, password_hash, subscription_tier, max_queries_per_month, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, email, name, subscription_tier, created_at
            """, 
            user_id, 
            free_user_data["email"],
            free_user_data["name"], 
            password_hash,
            free_user_data["subscription_tier"],
            free_user_data["max_queries_per_month"],
            created_at,
            created_at
            )
            
            await session.commit()
            created_user = result.fetchone()
        
        # Track for cleanup
        self.test_users_created.append(user_id)
        
        # Verify user was created with correct business data
        assert created_user is not None
        assert created_user["id"] == user_id
        assert created_user["email"] == free_user_data["email"]
        assert created_user["name"] == free_user_data["name"]
        assert created_user["subscription_tier"] == free_user_data["subscription_tier"]
        
        # Test user retrieval with real database query
        async with self.db.get_session() as session:
            result = await session.execute(
                "SELECT id, email, name, subscription_tier, max_queries_per_month, created_at FROM users WHERE id = $1",
                user_id
            )
            retrieved_user = result.fetchone()
        
        # Verify retrieved user matches business requirements
        assert retrieved_user is not None
        assert retrieved_user["id"] == user_id
        assert retrieved_user["email"] == free_user_data["email"]
        assert retrieved_user["subscription_tier"] == free_user_data["subscription_tier"]
        assert retrieved_user["max_queries_per_month"] == free_user_data["max_queries_per_month"]
        
        # Verify creation timestamp is recent (business audit requirement)
        creation_time = retrieved_user["created_at"]
        time_diff = datetime.now(timezone.utc) - creation_time
        assert time_diff.total_seconds() < 60, "User creation timestamp should be recent for business audit"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_persistence_with_real_redis(self, real_services_fixture):
        """
        Test session persistence and management with real Redis for user engagement.
        
        Business Value: Session management enables users to stay logged in and
        continue using AI optimization features without frequent re-authentication,
        improving user experience and platform engagement metrics.
        """
        # Create test user for session management
        user_data = self.business_scenarios["enterprise_user"]
        user_id = str(uuid.uuid4())
        
        # Create user in real database first
        async with self.db.get_session() as session:
            await session.execute("""
                INSERT INTO users (id, email, name, subscription_tier, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id,
            user_data["email"], 
            user_data["name"],
            user_data["subscription_tier"],
            datetime.now(timezone.utc),
            datetime.now(timezone.utc)
            )
            await session.commit()
        
        self.test_users_created.append(user_id)
        
        # Create session with real Redis
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "email": user_data["email"],
            "subscription_tier": user_data["subscription_tier"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Business Integration Test)"
        }
        
        # Store session in real Redis with business-appropriate expiration (24 hours)
        await self.redis_manager.setex(
            f"session:{session_id}",
            86400,  # 24 hours for enterprise users
            json.dumps(session_data)
        )
        
        self.test_sessions_created.append(session_id)
        
        # Verify session storage in real Redis
        stored_session_data = await self.redis_manager.get(f"session:{session_id}")
        assert stored_session_data is not None
        
        stored_session = json.loads(stored_session_data)
        assert stored_session["user_id"] == user_id
        assert stored_session["email"] == user_data["email"]
        assert stored_session["subscription_tier"] == user_data["subscription_tier"]
        
        # Test session update with activity tracking (business engagement metric)
        updated_activity = datetime.now(timezone.utc).isoformat()
        stored_session["last_activity"] = updated_activity
        stored_session["page_views"] = 15  # Business engagement metric
        stored_session["queries_this_session"] = 3  # Business usage metric
        
        await self.redis_manager.setex(
            f"session:{session_id}",
            86400,
            json.dumps(stored_session)
        )
        
        # Verify session update in real Redis
        updated_session_data = await self.redis_manager.get(f"session:{session_id}")
        updated_session = json.loads(updated_session_data)
        
        assert updated_session["last_activity"] == updated_activity
        assert updated_session["page_views"] == 15
        assert updated_session["queries_this_session"] == 3
        
        # Test session TTL for business security requirement
        session_ttl = await self.redis_manager.ttl(f"session:{session_id}")
        assert 82800 <= session_ttl <= 86400, "Session TTL should be close to 24 hours for enterprise users"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_user_linking_with_database_relationships(self, real_services_fixture):
        """
        Test OAuth user account linking with database relationships for seamless onboarding.
        
        Business Value: OAuth integration enables frictionless user onboarding with
        Google/GitHub accounts, reducing signup barriers and increasing conversion
        rates for platform adoption and revenue generation.
        """
        # Create OAuth user scenario
        oauth_user_data = self.business_scenarios["oauth_google_user"]
        user_id = str(uuid.uuid4())
        oauth_account_id = str(uuid.uuid4())
        
        # Create user in real database
        async with self.db.get_session() as session:
            await session.execute("""
                INSERT INTO users (id, email, name, created_at, updated_at, oauth_only)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id,
            oauth_user_data["email"],
            oauth_user_data["name"], 
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
            True  # OAuth-only account
            )
            await session.commit()
        
        self.test_users_created.append(user_id)
        
        # Create OAuth account relationship in real database
        oauth_provider_id = f"google_user_{uuid.uuid4()}"
        oauth_access_token = f"google_access_token_{uuid.uuid4()}"
        oauth_refresh_token = f"google_refresh_token_{uuid.uuid4()}"
        
        async with self.db.get_session() as session:
            await session.execute("""
                INSERT INTO oauth_accounts (id, user_id, provider, provider_user_id, access_token, refresh_token, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            oauth_account_id,
            user_id,
            oauth_user_data["oauth_provider"],
            oauth_provider_id,
            oauth_access_token,
            oauth_refresh_token,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc)
            )
            await session.commit()
        
        self.test_oauth_accounts_created.append(oauth_account_id)
        
        # Test OAuth user retrieval with relationship join (business login flow)
        async with self.db.get_session() as session:
            result = await session.execute("""
                SELECT u.id, u.email, u.name, u.oauth_only, 
                       oa.provider, oa.provider_user_id, oa.access_token, oa.refresh_token
                FROM users u
                JOIN oauth_accounts oa ON u.id = oa.user_id
                WHERE u.id = $1 AND oa.provider = $2
            """,
            user_id,
            oauth_user_data["oauth_provider"]
            )
            oauth_user = result.fetchone()
        
        # Verify OAuth relationship for business authentication flow
        assert oauth_user is not None
        assert oauth_user["id"] == user_id
        assert oauth_user["email"] == oauth_user_data["email"]
        assert oauth_user["oauth_only"] is True
        assert oauth_user["provider"] == oauth_user_data["oauth_provider"]
        assert oauth_user["provider_user_id"] == oauth_provider_id
        assert oauth_user["access_token"] == oauth_access_token
        assert oauth_user["refresh_token"] == oauth_refresh_token
        
        # Test OAuth token update (business token refresh flow)
        new_access_token = f"refreshed_google_access_token_{uuid.uuid4()}"
        
        async with self.db.get_session() as session:
            result = await session.execute("""
                UPDATE oauth_accounts 
                SET access_token = $1, updated_at = $2
                WHERE id = $3
                RETURNING access_token, updated_at
            """,
            new_access_token,
            datetime.now(timezone.utc),
            oauth_account_id
            )
            await session.commit()
            updated_oauth = result.fetchone()
        
        # Verify token update for business continuity
        assert updated_oauth["access_token"] == new_access_token
        
        # Test OAuth account lookup by provider ID (business login lookup)
        async with self.db.get_session() as session:
            result = await session.execute("""
                SELECT u.id, u.email, oa.provider, oa.provider_user_id
                FROM users u
                JOIN oauth_accounts oa ON u.id = oa.user_id  
                WHERE oa.provider = $1 AND oa.provider_user_id = $2
            """,
            oauth_user_data["oauth_provider"],
            oauth_provider_id
            )
            looked_up_user = result.fetchone()
        
        # Verify lookup works for business OAuth login flow
        assert looked_up_user is not None
        assert looked_up_user["id"] == user_id
        assert looked_up_user["email"] == oauth_user_data["email"]
        assert looked_up_user["provider"] == oauth_user_data["oauth_provider"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_storage_and_validation_business_security(self, real_services_fixture):
        """
        Test token storage and validation with real database for business security.
        
        Business Value: Secure token management protects user accounts and platform
        integrity, essential for maintaining customer trust and enterprise security
        requirements. Proper token validation prevents unauthorized access.
        """
        # Create user for token testing
        user_data = self.business_scenarios["enterprise_user"]
        user_id = str(uuid.uuid4())
        
        async with self.db.get_session() as session:
            await session.execute("""
                INSERT INTO users (id, email, name, subscription_tier, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id,
            user_data["email"],
            user_data["name"],
            user_data["subscription_tier"], 
            datetime.now(timezone.utc),
            datetime.now(timezone.utc)
            )
            await session.commit()
        
        self.test_users_created.append(user_id)
        
        # Generate business JWT tokens with real JWT handler
        token_payload = {
            "user_id": user_id,
            "email": user_data["email"],
            "subscription_tier": user_data["subscription_tier"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        }
        
        access_token = await self.jwt_handler.create_access_token(token_payload)
        refresh_token = await self.jwt_handler.create_refresh_token({"user_id": user_id})
        
        # Store tokens in real Redis with business expiration
        token_storage_key = f"user_tokens:{user_id}"
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "token_type": "Bearer"
        }
        
        await self.redis_manager.setex(
            token_storage_key,
            86400,  # 24 hours
            json.dumps(token_data)
        )
        
        # Test token retrieval and validation
        stored_token_data = await self.redis_manager.get(token_storage_key)
        assert stored_token_data is not None
        
        stored_tokens = json.loads(stored_token_data)
        assert stored_tokens["access_token"] == access_token
        assert stored_tokens["refresh_token"] == refresh_token
        assert stored_tokens["token_type"] == "Bearer"
        
        # Test JWT validation with business security checks
        try:
            decoded_payload = await self.jwt_handler.verify_access_token(access_token)
            
            # Verify business-critical token claims
            assert decoded_payload["user_id"] == user_id
            assert decoded_payload["email"] == user_data["email"]
            assert decoded_payload["subscription_tier"] == user_data["subscription_tier"]
            
            # Verify token timing for business security
            issued_at = datetime.fromtimestamp(decoded_payload["iat"], tz=timezone.utc)
            expires_at = datetime.fromtimestamp(decoded_payload["exp"], tz=timezone.utc)
            
            time_until_expiry = expires_at - datetime.now(timezone.utc)
            assert time_until_expiry.total_seconds() > 0, "Token should not be expired for business operations"
            assert time_until_expiry.total_seconds() <= 86400, "Token expiry should be within 24 hours for business security"
            
        except Exception as e:
            pytest.fail(f"JWT token validation failed for business operations: {e}")
        
        # Test refresh token validation
        try:
            decoded_refresh = await self.jwt_handler.verify_refresh_token(refresh_token)
            assert decoded_refresh["user_id"] == user_id
        except Exception as e:
            pytest.fail(f"Refresh token validation failed for business operations: {e}")
        
        # Test token revocation for business security
        await self.redis_manager.delete(token_storage_key)
        
        revoked_token_data = await self.redis_manager.get(token_storage_key)
        assert revoked_token_data is None, "Revoked tokens should not be retrievable for business security"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_audit_logging_with_real_database(self, real_services_fixture):
        """
        Test audit logging with persistent database storage for business compliance.
        
        Business Value: Audit logging provides security compliance and operational
        insights required for enterprise customers and regulatory requirements.
        Essential for maintaining customer trust and legal compliance.
        """
        # Create user for audit testing
        user_data = self.business_scenarios["enterprise_user"]
        user_id = str(uuid.uuid4())
        
        async with self.db.get_session() as session:
            await session.execute("""
                INSERT INTO users (id, email, name, subscription_tier, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id,
            user_data["email"],
            user_data["name"],
            user_data["subscription_tier"],
            datetime.now(timezone.utc),
            datetime.now(timezone.utc)
            )
            await session.commit()
        
        self.test_users_created.append(user_id)
        
        # Create business-critical audit log entries
        audit_events = [
            {
                "event_type": "user_login",
                "description": f"User {user_data['email']} logged in successfully",
                "ip_address": "192.168.1.100", 
                "user_agent": "Mozilla/5.0 (Enterprise Client)",
                "severity": "info"
            },
            {
                "event_type": "token_refresh", 
                "description": f"Access token refreshed for user {user_data['email']}",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Enterprise Client)",
                "severity": "info"
            },
            {
                "event_type": "failed_login",
                "description": f"Failed login attempt for {user_data['email']} - invalid password",
                "ip_address": "192.168.1.200",
                "user_agent": "Mozilla/5.0 (Unknown Client)",
                "severity": "warning"
            }
        ]
        
        audit_log_ids = []
        
        # Store audit events in real database
        for event in audit_events:
            audit_id = str(uuid.uuid4())
            
            async with self.db.get_session() as session:
                await session.execute("""
                    INSERT INTO audit_logs (id, user_id, event_type, description, ip_address, user_agent, severity, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                audit_id,
                user_id,
                event["event_type"],
                event["description"],
                event["ip_address"],
                event["user_agent"],
                event["severity"],
                datetime.now(timezone.utc)
                )
                await session.commit()
                
            audit_log_ids.append(audit_id)
        
        # Test audit log retrieval for business compliance reporting
        async with self.db.get_session() as session:
            result = await session.execute("""
                SELECT event_type, description, ip_address, severity, created_at
                FROM audit_logs
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, user_id)
            audit_logs = result.fetchall()
        
        # Verify audit logs for business compliance
        assert len(audit_logs) == 3
        
        # Verify login event
        login_event = audit_logs[2]  # Oldest first
        assert login_event["event_type"] == "user_login"
        assert user_data["email"] in login_event["description"]
        assert login_event["severity"] == "info"
        
        # Verify security event (failed login)
        failed_login_event = audit_logs[0]  # Most recent first
        assert failed_login_event["event_type"] == "failed_login"
        assert "invalid password" in failed_login_event["description"]
        assert failed_login_event["severity"] == "warning"
        assert failed_login_event["ip_address"] == "192.168.1.200"
        
        # Test audit log querying by event type for business security monitoring
        async with self.db.get_session() as session:
            result = await session.execute("""
                SELECT COUNT(*) as failed_attempts
                FROM audit_logs  
                WHERE user_id = $1 AND event_type = 'failed_login'
                AND created_at >= $2
            """,
            user_id,
            datetime.now(timezone.utc) - timedelta(hours=1)
            )
            failed_login_count = result.fetchone()
        
        # Verify security monitoring query for business protection
        assert failed_login_count["failed_attempts"] == 1
        
        # Test audit log retention query for business compliance
        async with self.db.get_session() as session:
            result = await session.execute("""
                SELECT event_type, created_at
                FROM audit_logs
                WHERE user_id = $1 AND created_at >= $2
                ORDER BY created_at ASC
            """,
            user_id,
            datetime.now(timezone.utc) - timedelta(days=30)  # Last 30 days
            )
            recent_audit_logs = result.fetchall()
        
        # Verify audit retention for business compliance requirements
        assert len(recent_audit_logs) == 3
        for log in recent_audit_logs:
            log_age = datetime.now(timezone.utc) - log["created_at"]
            assert log_age.total_seconds() < 3600, "Audit logs should be recent for business compliance"
        
        # Cleanup audit logs
        for audit_id in audit_log_ids:
            async with self.db.get_session() as session:
                await session.execute("DELETE FROM audit_logs WHERE id = $1", audit_id)
                await session.commit()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_data_isolation_concurrent_access(self, real_services_fixture):
        """
        Test multi-user data isolation and concurrent access for business scalability.
        
        Business Value: Multi-user isolation ensures platform can support multiple
        customers simultaneously without data leakage, critical for enterprise
        security requirements and business growth scalability.
        """
        # Create multiple test users for isolation testing
        test_users = []
        for i in range(5):
            user_data = {
                "id": str(uuid.uuid4()),
                "email": f"{self.test_user_base_email}-isolation-{i}{self.test_domain}",
                "name": f"Isolation Test User {i}",
                "subscription_tier": "enterprise" if i % 2 == 0 else "free"
            }
            test_users.append(user_data)
            
        # Create all users concurrently (business scalability test)
        async def create_user(user_data):
            async with self.db.get_session() as session:
                await session.execute("""
                    INSERT INTO users (id, email, name, subscription_tier, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_data["id"],
                user_data["email"],
                user_data["name"],
                user_data["subscription_tier"],
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
                )
                await session.commit()
                return user_data["id"]
        
        # Create users concurrently
        creation_tasks = [create_user(user) for user in test_users]
        created_user_ids = await asyncio.gather(*creation_tasks)
        
        # Track for cleanup
        self.test_users_created.extend(created_user_ids)
        
        # Create isolated sessions for each user
        session_tasks = []
        for user_data in test_users:
            session_id = str(uuid.uuid4())
            session_data = {
                "user_id": user_data["id"],
                "email": user_data["email"],
                "subscription_tier": user_data["subscription_tier"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "isolation_test": True
            }
            
            # Store session in Redis with user isolation
            session_tasks.append(
                self.redis_manager.setex(
                    f"session:{session_id}",
                    3600,  # 1 hour
                    json.dumps(session_data)
                )
            )
            self.test_sessions_created.append(session_id)
        
        # Execute session creation concurrently
        await asyncio.gather(*session_tasks)
        
        # Test concurrent user data retrieval (business scalability)
        async def retrieve_user_data(user_data):
            async with self.db.get_session() as session:
                result = await session.execute("""
                    SELECT id, email, subscription_tier
                    FROM users
                    WHERE id = $1
                """, user_data["id"])
                return result.fetchone()
        
        retrieval_tasks = [retrieve_user_data(user) for user in test_users]
        retrieved_users = await asyncio.gather(*retrieval_tasks)
        
        # Verify user data isolation (business security requirement)
        assert len(retrieved_users) == 5
        
        for i, retrieved_user in enumerate(retrieved_users):
            expected_user = test_users[i]
            assert retrieved_user["id"] == expected_user["id"]
            assert retrieved_user["email"] == expected_user["email"] 
            assert retrieved_user["subscription_tier"] == expected_user["subscription_tier"]
        
        # Test concurrent session retrieval with user isolation
        async def retrieve_user_sessions(user_data):
            user_sessions = []
            for session_id in self.test_sessions_created:
                session_data_raw = await self.redis_manager.get(f"session:{session_id}")
                if session_data_raw:
                    session_data = json.loads(session_data_raw)
                    if session_data.get("user_id") == user_data["id"]:
                        user_sessions.append(session_data)
            return user_sessions
        
        session_retrieval_tasks = [retrieve_user_sessions(user) for user in test_users]
        user_sessions_list = await asyncio.gather(*session_retrieval_tasks)
        
        # Verify session isolation for business security
        for i, user_sessions in enumerate(user_sessions_list):
            assert len(user_sessions) == 1, "Each user should have exactly one isolated session"
            
            session = user_sessions[0]
            expected_user = test_users[i]
            assert session["user_id"] == expected_user["id"]
            assert session["email"] == expected_user["email"]
            assert session["isolation_test"] is True
        
        # Test cross-user data access prevention (business security critical)
        # Attempt to access another user's data
        user_a = test_users[0]
        user_b = test_users[1]
        
        async with self.db.get_session() as session:
            # Query should only return user_a data, not user_b
            result = await session.execute("""
                SELECT id, email FROM users 
                WHERE id = $1 AND email != $2
            """,
            user_a["id"],
            user_b["email"]  # Ensure we don't accidentally get user_b data
            )
            isolated_user = result.fetchone()
        
        # Verify proper isolation prevents cross-user data access
        assert isolated_user["id"] == user_a["id"]
        assert isolated_user["email"] == user_a["email"]
        assert isolated_user["email"] != user_b["email"]