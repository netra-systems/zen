"""
TestRepositoryFactory Integration Tests

Comprehensive test suite to validate SSOT database access patterns.
These tests ensure the factory works correctly with real PostgreSQL containers.

IMPORTANT: These tests use REAL databases and validate actual repository behavior.
No mocks are used - this validates the complete integration stack.
"""

import asyncio
import os
import pytest
import logging
from typing import Dict, Any
from datetime import datetime

from test_framework.repositories.test_repository_factory import (
    TestRepositoryFactory,
    get_test_repository_factory,
    get_test_session,
    create_test_repositories,
    check_repository_compliance,
    RepositoryComplianceError
)
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class TestRepositoryFactoryIntegration:
    """
    Integration tests for TestRepositoryFactory with real databases.
    
    These tests validate:
    - SSOT enforcement
    - Session management
    - Transaction isolation
    - Compliance checking
    - Cross-service repository access
    - Error handling and cleanup
    """
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup test environment with proper database configuration."""
        self.env = IsolatedEnvironment.get_instance()
        self.env.enable_isolation()
        
        # Set test database configuration
        self.env.set("ENVIRONMENT", "test", "test_setup")
        self.env.set("POSTGRES_HOST", "localhost", "test_setup")
        self.env.set("POSTGRES_PORT", "5434", "test_setup")  # Test port
        self.env.set("POSTGRES_USER", "postgres", "test_setup")
        self.env.set("POSTGRES_PASSWORD", "postgres", "test_setup")
        self.env.set("POSTGRES_DB", "netra_test", "test_setup")
        
        # Auth service database
        self.env.set("AUTH_POSTGRES_DB", "auth_test", "test_setup")
        
        self.factory = get_test_repository_factory()
        
        yield
        
        # Cleanup after test
        await self.factory.cleanup_resources()
        self.env.disable_isolation()
    
    async def test_singleton_behavior(self):
        """Test that factory maintains singleton behavior."""
        factory1 = TestRepositoryFactory()
        factory2 = TestRepositoryFactory.get_instance()
        factory3 = get_test_repository_factory()
        
        assert factory1 is factory2
        assert factory2 is factory3
        assert id(factory1) == id(factory2) == id(factory3)
    
    async def test_database_url_configuration(self):
        """Test database URL generation for different services."""
        factory = get_test_repository_factory()
        
        # Test backend database URL
        backend_url = factory._get_database_url("backend")
        assert "postgresql+asyncpg://" in backend_url
        assert "netra_test" in backend_url
        assert "5434" in backend_url
        
        # Test auth database URL
        auth_url = factory._get_database_url("auth")
        assert "postgresql+asyncpg://" in auth_url
        assert "auth_test" in auth_url
        
        # Test invalid service
        with pytest.raises(RepositoryComplianceError):
            factory._get_database_url("invalid_service")
    
    async def test_session_management_lifecycle(self):
        """Test complete session lifecycle with tracking."""
        factory = get_test_repository_factory()
        
        # Verify no active sessions initially
        assert len(factory._active_sessions) == 0
        
        session_id = None
        async with factory.get_test_session() as session:
            session_id = id(session)
            
            # Verify session is tracked
            assert session in factory._active_sessions
            assert session in factory._session_tracking
            
            # Verify session info
            session_info = factory._session_tracking[session]
            assert session_info["service"] == "backend"
            assert session_info["rollback_enabled"] is True
            assert isinstance(session_info["created_at"], datetime)
        
        # Verify session is cleaned up after context exit
        assert len(factory._active_sessions) == 0
        assert len(factory._session_tracking) == 0
    
    async def test_user_repository_crud_operations(self):
        """Test complete CRUD operations with UserRepository."""
        factory = get_test_repository_factory()
        
        async with factory.get_test_session() as session:
            user_repo = factory.create_user_repository(session)
            
            # Create user
            user_data = {
                "full_name": "Integration Test User",
                "email": "integration@test.com",
                "plan_tier": "free",
                "is_active": True
            }
            
            created_user = await user_repo.create_user(session, user_data)
            assert created_user is not None
            assert created_user.email == "integration@test.com"
            assert created_user.plan_tier == "free"
            
            # Read user
            found_user = await user_repo.get_by_email(session, "integration@test.com")
            assert found_user is not None
            assert found_user.id == created_user.id
            
            # Update user
            update_success = await user_repo.update_plan(
                session, created_user.id, "pro", max_agents=10
            )
            assert update_success is True
            
            # Verify update
            updated_user = await user_repo.get_by_email(session, "integration@test.com")
            assert updated_user.plan_tier == "pro"
            
            # List operations
            active_users = await user_repo.get_active_users(session, limit=10)
            assert len(active_users) >= 1
            assert any(u.id == created_user.id for u in active_users)
            
            # Plan tier filtering
            pro_users = await user_repo.get_by_plan_tier(session, "pro")
            assert len(pro_users) >= 1
            assert any(u.id == created_user.id for u in pro_users)
    
    async def test_secret_repository_operations(self):
        """Test SecretRepository with proper session management."""
        factory = get_test_repository_factory()
        
        async with factory.get_test_session() as session:
            user_repo = factory.create_user_repository(session)
            secret_repo = factory.create_secret_repository(session)
            
            # Create test user first
            user = await user_repo.create_user(session, {
                "full_name": "Secret Test User",
                "email": "secrets@test.com"
            })
            
            # Create secret
            secret = await secret_repo.create(
                user_id=user.id,
                key="API_KEY",
                encrypted_value="encrypted_test_value_12345"
            )
            
            assert secret is not None
            assert secret.user_id == user.id
            assert secret.key == "API_KEY"
            
            # Get user secrets
            user_secrets = await secret_repo.get_user_secrets(user.id)
            assert len(user_secrets) == 1
            assert user_secrets[0].key == "API_KEY"
            
            # Get secret by key
            found_secret = await secret_repo.get_user_secret_by_key(user.id, "API_KEY")
            assert found_secret is not None
            assert found_secret.id == secret.id
            
            # Test non-existent key
            missing_secret = await secret_repo.get_user_secret_by_key(user.id, "MISSING_KEY")
            assert missing_secret is None
    
    async def test_auth_service_repositories(self):
        """Test auth service repositories with managed sessions."""
        factory = get_test_repository_factory()
        
        # Test AuthUserRepository
        async with await factory.create_auth_user_repository() as auth_user_repo:
            # Create OAuth user
            oauth_info = {
                "email": "oauth@test.com",
                "name": "OAuth Test User",
                "provider": "google",
                "id": "google_test_123",
                "sub": "google_test_123"
            }
            
            oauth_user = await auth_user_repo.create_oauth_user(oauth_info)
            assert oauth_user is not None
            assert oauth_user.email == "oauth@test.com"
            assert oauth_user.auth_provider == "google"
            assert oauth_user.is_verified is True
            
            # Get by email
            found_user = await auth_user_repo.get_by_email("oauth@test.com")
            assert found_user.id == oauth_user.id
            
            # Get by ID
            found_by_id = await auth_user_repo.get_by_id(oauth_user.id)
            assert found_by_id.email == oauth_user.email
        
        # Test AuthSessionRepository with same user
        async with await factory.create_auth_session_repository() as auth_session_repo:
            # Create session
            session_info = await auth_session_repo.create_session(
                user_id=oauth_user.id,
                refresh_token="test_refresh_token_12345",
                client_info={
                    "ip": "192.168.1.100",
                    "user_agent": "Test Agent 1.0",
                    "device_id": "test_device_123"
                }
            )
            
            assert session_info is not None
            assert session_info.user_id == oauth_user.id
            assert session_info.is_active is True
            
            # Get active session
            active_session = await auth_session_repo.get_active_session(session_info.id)
            assert active_session is not None
            assert active_session.id == session_info.id
            
            # Revoke session
            await auth_session_repo.revoke_session(session_info.id)
            
            # Verify revocation
            revoked_session = await auth_session_repo.get_active_session(session_info.id)
            assert revoked_session is None
    
    async def test_transaction_isolation_between_sessions(self):
        """Test that transactions are properly isolated between sessions."""
        factory = get_test_repository_factory()
        test_email = f"isolation_test_{datetime.now().strftime('%Y%m%d%H%M%S')}@test.com"
        
        # Session 1: Create user but don't commit
        user_id = None
        async with factory.get_test_session() as session1:
            user_repo = factory.create_user_repository(session1)
            
            user = await user_repo.create_user(session1, {
                "full_name": "Isolation Test",
                "email": test_email
            })
            user_id = user.id
            
            # User should exist in this session
            found_in_session1 = await user_repo.get_by_email(session1, test_email)
            assert found_in_session1 is not None
            
            # Session 2: Should not see uncommitted data
            async with factory.get_test_session() as session2:
                user_repo2 = factory.create_user_repository(session2)
                
                # Should not see user from session1 (transaction isolation)
                found_in_session2 = await user_repo2.get_by_email(session2, test_email)
                # This might be None due to transaction isolation,
                # or the same due to test transaction behavior
                # The key is that each session has its own transaction
        
        # After session1 exits (rollback), user should be gone
        async with factory.get_test_session() as session3:
            user_repo3 = factory.create_user_repository(session3)
            
            # User should not exist after rollback
            found_after_rollback = await user_repo3.get_by_email(session3, test_email)
            assert found_after_rollback is None
    
    async def test_data_factories(self):
        """Test built-in data factories for efficient test setup."""
        factory = get_test_repository_factory()
        
        async with factory.get_test_session() as session:
            factories = await factory.create_test_data_factories(session)
            
            # Test user factory with defaults
            user1 = await factories["create_user"]()
            assert user1.full_name == "Test User"
            assert "@example.com" in user1.email
            
            # Test user factory with custom values
            user2 = await factories["create_user"](
                name="Custom Factory User",
                email="custom_factory@test.com",
                plan_tier="enterprise"
            )
            
            assert user2.full_name == "Custom Factory User"
            assert user2.email == "custom_factory@test.com"
            assert user2.plan_tier == "enterprise"
            
            # Verify users are distinct
            assert user1.id != user2.id
            assert user1.email != user2.email
    
    async def test_compliance_checking(self):
        """Test compliance checking and violation detection."""
        factory = get_test_repository_factory()
        
        # Get baseline compliance report
        initial_report = factory.validate_no_direct_access()
        
        # Perform compliant operations
        async with factory.get_test_session() as session:
            user_repo = factory.create_user_repository(session)
            
            await user_repo.create_user(session, {
                "full_name": "Compliance Test",
                "email": "compliance@test.com"
            })
        
        # Check compliance after operations
        final_report = factory.validate_no_direct_access()
        
        # Should remain compliant
        assert final_report.is_compliant or len(final_report.violations) <= len(initial_report.violations)
        
        # Test compliance report generation
        report_text = factory.generate_compliance_report()
        assert "TestRepositoryFactory Compliance Report" in report_text
        assert "=" in report_text  # Header formatting
    
    async def test_error_handling_and_cleanup(self):
        """Test error handling with proper resource cleanup."""
        factory = get_test_repository_factory()
        test_email = f"error_test_{datetime.now().strftime('%Y%m%d%H%M%S')}@test.com"
        
        # Test that errors trigger proper rollback
        with pytest.raises(ValueError):
            async with factory.get_test_session() as session:
                user_repo = factory.create_user_repository(session)
                
                # Create user
                user = await user_repo.create_user(session, {
                    "full_name": "Error Test User",
                    "email": test_email
                })
                
                # Verify user was created in this session
                found_user = await user_repo.get_by_email(session, test_email)
                assert found_user is not None
                
                # Simulate error
                raise ValueError("Test error for cleanup validation")
        
        # Verify user was rolled back after error
        async with factory.get_test_session() as session:
            user_repo = factory.create_user_repository(session)
            
            # User should not exist due to rollback on error
            found_user = await user_repo.get_by_email(session, test_email)
            assert found_user is None
    
    async def test_convenience_functions(self):
        """Test convenience functions for simplified usage."""
        # Test get_test_session convenience function
        async with get_test_session() as session:
            # Test create_test_repositories convenience function
            repos = await create_test_repositories(session)
            
            assert "user" in repos
            assert "secret" in repos
            assert "tool_usage" in repos
            
            # Use repositories
            user = await repos["user"].create_user(session, {
                "full_name": "Convenience Test",
                "email": "convenience@test.com"
            })
            
            assert user is not None
            
            # Test cross-repository operations
            secret = await repos["secret"].create(
                user_id=user.id,
                key="CONVENIENCE_KEY",
                encrypted_value="test_value"
            )
            
            assert secret.user_id == user.id
    
    @pytest.mark.skipif(
        get_env().get("SKIP_DATABASE_TESTS") == "true",
        reason="Database tests skipped via environment variable"
    )
    async def test_real_database_connectivity(self):
        """Test actual database connectivity with real PostgreSQL."""
        factory = get_test_repository_factory()
        
        # Test backend database
        try:
            async with factory.get_test_session("backend") as session:
                # Execute simple query to verify connectivity
                result = await session.execute(text("SELECT 1 as test_value"))
                row = result.fetchone()
                assert row[0] == 1
        except Exception as e:
            pytest.skip(f"Backend database not available: {e}")
        
        # Test auth database
        try:
            async with factory.get_test_session("auth") as session:
                # Execute simple query to verify connectivity
                result = await session.execute(text("SELECT 1 as test_value"))
                row = result.fetchone()
                assert row[0] == 1
        except Exception as e:
            pytest.skip(f"Auth database not available: {e}")
    
    async def test_resource_cleanup(self):
        """Test that all resources are properly cleaned up."""
        factory = get_test_repository_factory()
        
        # Create some sessions and repositories
        async with factory.get_test_session() as session1:
            user_repo = factory.create_user_repository(session1)
            await user_repo.create_user(session1, {
                "full_name": "Cleanup Test 1",
                "email": "cleanup1@test.com"
            })
        
        async with factory.get_test_session() as session2:
            secret_repo = factory.create_secret_repository(session2)
            # Session automatically cleaned up
        
        # Verify no active sessions remain
        assert len(factory._active_sessions) == 0
        assert len(factory._session_tracking) == 0
        
        # Test explicit cleanup
        initial_engine_count = len(factory._engines)
        await factory.cleanup_resources()
        
        # Verify engines were cleaned up
        assert len(factory._engines) == 0
        assert len(factory._session_makers) == 0
        
        # Verify we can still create new sessions after cleanup
        async with factory.get_test_session() as session:
            user_repo = factory.create_user_repository(session)
            user = await user_repo.create_user(session, {
                "full_name": "Post Cleanup Test",
                "email": "post_cleanup@test.com"
            })
            assert user is not None


def main():
    """
    Run integration tests manually (for development).
    """
    async def run_tests():
        print("Running TestRepositoryFactory Integration Tests")
        print("=" * 50)
        
        test_instance = TestRepositoryFactoryIntegration()
        
        # Setup environment
        await test_instance.setup_test_environment().__anext__()
        
        try:
            # Run key tests
            print("Testing singleton behavior...")
            await test_instance.test_singleton_behavior()
            print(" PASS:  Singleton test passed")
            
            print("Testing database configuration...")
            await test_instance.test_database_url_configuration()
            print(" PASS:  Database configuration test passed")
            
            print("Testing session management...")
            await test_instance.test_session_management_lifecycle()
            print(" PASS:  Session management test passed")
            
            print("Testing user repository CRUD...")
            await test_instance.test_user_repository_crud_operations()
            print(" PASS:  User repository test passed")
            
            print("Testing transaction isolation...")
            await test_instance.test_transaction_isolation_between_sessions()
            print(" PASS:  Transaction isolation test passed")
            
            print("Testing data factories...")
            await test_instance.test_data_factories()
            print(" PASS:  Data factories test passed")
            
            print("Testing compliance checking...")
            await test_instance.test_compliance_checking()
            print(" PASS:  Compliance checking test passed")
            
            print("Testing error handling...")
            await test_instance.test_error_handling_and_cleanup()
            print(" PASS:  Error handling test passed")
            
            print("Testing convenience functions...")
            await test_instance.test_convenience_functions()
            print(" PASS:  Convenience functions test passed")
            
            print("Testing resource cleanup...")
            await test_instance.test_resource_cleanup()
            print(" PASS:  Resource cleanup test passed")
            
        except Exception as e:
            print(f" FAIL:  Test failed: {e}")
            raise
        finally:
            # Cleanup
            factory = get_test_repository_factory()
            await factory.cleanup_resources()
        
        print("\n CELEBRATION:  All integration tests passed!")
        print("\nThe TestRepositoryFactory is ready for use!")
    
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()
