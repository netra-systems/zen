"""
TestRepositoryFactory Usage Examples

This module demonstrates proper usage patterns for the TestRepositoryFactory
and provides examples for common testing scenarios.

CRITICAL: These examples show the ONLY approved way to access repositories in tests.
"""

import asyncio
import pytest
from typing import Dict, Any

from test_framework.repositories.test_repository_factory import (
    get_test_repository_factory, 
    get_test_session,
    create_test_repositories,
    check_repository_compliance
)


class TestRepositoryFactoryExamples:
    """
    Example test class demonstrating proper TestRepositoryFactory usage.
    
    These examples serve as both documentation and validation of the factory patterns.
    """
    
    async def test_basic_user_repository_usage(self):
        """
        Example: Basic user repository operations with automatic session management.
        
        This is the standard pattern for all repository-based tests.
        """
        factory = get_test_repository_factory()
        
        # CORRECT: Use managed session with automatic rollback
        async with factory.get_test_session() as session:
            # Create repository through factory (SSOT enforcement)
            user_repo = factory.create_user_repository(session)
            
            # Perform repository operations
            user = await user_repo.create_user(session, {
                "full_name": "Test User",
                "email": "test@example.com",
                "plan_tier": "free"
            })
            
            # Verify creation
            assert user is not None
            assert user.email == "test@example.com"
            
            # Query operations
            found_user = await user_repo.get_by_email(session, "test@example.com")
            assert found_user.id == user.id
            
            # Update operations
            success = await user_repo.update_by_id(user.id, plan_tier="pro")
            assert success is True
            
        # Session automatically rolled back - no data persists
    
    async def test_multiple_repository_usage(self):
        """
        Example: Using multiple repositories in a single test.
        
        Shows how to work with related data across repository boundaries.
        """
        factory = get_test_repository_factory()
        
        async with factory.get_test_session() as session:
            # Create multiple repositories
            user_repo = factory.create_user_repository(session)
            secret_repo = factory.create_secret_repository(session)
            tool_repo = factory.create_tool_usage_repository(session)
            
            # Create test user
            user = await user_repo.create_user(session, {
                "full_name": "Multi Repo Test",
                "email": "multi@example.com"
            })
            
            # Create related secret
            secret = await secret_repo.create(
                user_id=user.id,
                key="API_KEY",
                encrypted_value="encrypted_test_value"
            )
            
            # Create tool usage record
            usage = await tool_repo.create(
                user_id=user.id,
                tool_name="test_tool",
                usage_data={"test": "data"}
            )
            
            # Verify relationships
            user_secrets = await secret_repo.get_user_secrets(user.id)
            assert len(user_secrets) == 1
            assert user_secrets[0].key == "API_KEY"
            
            user_usage = await tool_repo.get_user_usage(user.id)
            assert len(user_usage) == 1
            assert user_usage[0].tool_name == "test_tool"
    
    async def test_auth_service_repositories(self):
        """
        Example: Using auth service repositories with managed sessions.
        
        Shows cross-service repository usage with proper session management.
        """
        factory = get_test_repository_factory()
        
        # Auth repositories use their own context managers
        async with await factory.create_auth_user_repository() as auth_user_repo:
            # Create OAuth user
            user_info = {
                "email": "oauth@example.com",
                "name": "OAuth Test User",
                "provider": "google",
                "id": "google_12345"
            }
            
            oauth_user = await auth_user_repo.create_oauth_user(user_info)
            assert oauth_user.email == "oauth@example.com"
            assert oauth_user.auth_provider == "google"
            
            # Verify user exists
            found_user = await auth_user_repo.get_by_email("oauth@example.com")
            assert found_user.id == oauth_user.id
        
        # Work with auth sessions
        async with await factory.create_auth_session_repository() as auth_session_repo:
            session_info = await auth_session_repo.create_session(
                user_id=oauth_user.id,
                refresh_token="test_token_12345",
                client_info={
                    "ip": "127.0.0.1",
                    "user_agent": "Test Agent"
                }
            )
            
            assert session_info.user_id == oauth_user.id
            assert session_info.is_active is True
    
    async def test_data_factories_usage(self):
        """
        Example: Using test data factories for efficient test setup.
        
        Shows how to use built-in factories for common test scenarios.
        """
        factory = get_test_repository_factory()
        
        async with factory.get_test_session() as session:
            # Get test data factories
            factories = await factory.create_test_data_factories(session)
            
            # Create test users easily
            user1 = await factories["create_user"](
                name="Factory User 1",
                email="factory1@example.com"
            )
            
            user2 = await factories["create_user"](
                name="Factory User 2"
                # Email auto-generated with timestamp
            )
            
            assert user1.full_name == "Factory User 1"
            assert user1.email == "factory1@example.com"
            
            assert user2.full_name == "Factory User 2"
            assert "@example.com" in user2.email
    
    async def test_transaction_rollback_behavior(self):
        """
        Example: Demonstrating automatic transaction rollback.
        
        Shows how the factory ensures test isolation through rollbacks.
        """
        factory = get_test_repository_factory()
        
        # First session: Create data
        async with factory.get_test_session() as session1:
            user_repo = factory.create_user_repository(session1)
            
            user = await user_repo.create_user(session1, {
                "full_name": "Rollback Test",
                "email": "rollback@example.com"
            })
            
            # Data exists within this session
            found_user = await user_repo.get_by_email(session1, "rollback@example.com")
            assert found_user is not None
        
        # Second session: Data should be rolled back
        async with factory.get_test_session() as session2:
            user_repo = factory.create_user_repository(session2)
            
            # Data should not exist (rolled back)
            found_user = await user_repo.get_by_email(session2, "rollback@example.com")
            assert found_user is None
    
    async def test_compliance_checking(self):
        """
        Example: Using compliance checking to detect violations.
        
        Shows how to validate repository usage patterns.
        """
        # Check compliance before test
        initial_report = check_repository_compliance()
        
        factory = get_test_repository_factory()
        
        async with factory.get_test_session() as session:
            user_repo = factory.create_user_repository(session)
            
            # Perform operations
            await user_repo.create_user(session, {
                "full_name": "Compliance Test",
                "email": "compliance@example.com"
            })
        
        # Check compliance after test
        final_report = check_repository_compliance()
        
        # Should be compliant if using factory properly
        assert final_report.is_compliant
        assert len(final_report.violations) == 0
        assert not final_report.direct_access_detected
    
    async def test_error_handling_and_cleanup(self):
        """
        Example: Error handling with automatic cleanup.
        
        Shows how the factory handles errors and ensures resource cleanup.
        """
        factory = get_test_repository_factory()
        
        try:
            async with factory.get_test_session() as session:
                user_repo = factory.create_user_repository(session)
                
                # Create valid user
                user = await user_repo.create_user(session, {
                    "full_name": "Error Test",
                    "email": "error@example.com"
                })
                
                # Simulate error condition
                raise ValueError("Simulated test error")
                
        except ValueError as e:
            # Error expected
            assert str(e) == "Simulated test error"
        
        # Verify cleanup occurred
        async with factory.get_test_session() as session:
            user_repo = factory.create_user_repository(session)
            
            # Data should be rolled back even on error
            found_user = await user_repo.get_by_email(session, "error@example.com")
            assert found_user is None
    
    def test_convenience_functions(self):
        """
        Example: Using convenience functions for simpler syntax.
        
        Shows alternative syntax patterns for common operations.
        """
        async def run_test():
            # Using convenience function
            async with get_test_session() as session:
                # Create all common repositories at once
                repos = await create_test_repositories(session)
                
                # Access repositories by name
                user_repo = repos["user"]
                secret_repo = repos["secret"]
                tool_repo = repos["tool_usage"]
                
                # Use repositories normally
                user = await user_repo.create_user(session, {
                    "full_name": "Convenience Test",
                    "email": "convenience@example.com"
                })
                
                assert user.email == "convenience@example.com"
        
        # Run async test
        asyncio.run(run_test())


# Examples of INCORRECT usage (for documentation purposes)

class AntiPatternExamples:
    """
    Examples of INCORRECT repository usage patterns.
    
    These patterns will trigger compliance violations and should be avoided.
    """
    
    def test_direct_sqlalchemy_usage_WRONG(self):
        """
         FAIL:  WRONG: Direct SQLAlchemy usage bypasses SSOT principles.
        
        This pattern is detected and flagged by compliance checking.
        """
        # This would trigger a compliance violation:
        # from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        # 
        # engine = create_async_engine("postgresql://...")
        # session = AsyncSession(engine)
        # 
        # # Direct query execution
        # result = await session.execute(text("SELECT * FROM users"))
        
        pass  # Example only - don't actually implement
    
    def test_unmanaged_session_WRONG(self):
        """
         FAIL:  WRONG: Creating repositories without factory management.
        
        This bypasses session tracking and transaction management.
        """
        # This would trigger a compliance violation:
        # from netra_backend.app.db.repositories.user_repository import UserRepository
        # 
        # # Direct repository instantiation without factory
        # user_repo = UserRepository()  # No session management
        # user = await user_repo.create(...)  # Will fail or leak resources
        
        pass  # Example only - don't actually implement
    
    def test_session_without_context_manager_WRONG(self):
        """
         FAIL:  WRONG: Using sessions without proper context management.
        
        This can lead to resource leaks and transaction issues.
        """
        # This would trigger a compliance violation:
        # factory = get_test_repository_factory()
        # session = await factory._get_session()  # Direct access
        # 
        # # Use session without context manager
        # user_repo = factory.create_user_repository(session)
        # # Session never properly closed
        
        pass  # Example only - don't actually implement


def main():
    """
    Run example usage patterns.
    
    This function demonstrates all the key patterns for using TestRepositoryFactory.
    """
    print("TestRepositoryFactory Usage Examples")
    print("=" * 45)
    
    async def run_examples():
        examples = TestRepositoryFactoryExamples()
        
        print("Running basic user repository example...")
        await examples.test_basic_user_repository_usage()
        print(" PASS:  Basic usage example completed")
        
        print("Running multiple repository example...")
        await examples.test_multiple_repository_usage()
        print(" PASS:  Multiple repository example completed")
        
        print("Running auth service example...")
        await examples.test_auth_service_repositories()
        print(" PASS:  Auth service example completed")
        
        print("Running data factories example...")
        await examples.test_data_factories_usage()
        print(" PASS:  Data factories example completed")
        
        print("Running transaction rollback example...")
        await examples.test_transaction_rollback_behavior()
        print(" PASS:  Transaction rollback example completed")
        
        print("Running compliance checking example...")
        await examples.test_compliance_checking()
        print(" PASS:  Compliance checking example completed")
        
        print("Running error handling example...")
        await examples.test_error_handling_and_cleanup()
        print(" PASS:  Error handling example completed")
        
        print("Running convenience functions example...")
        examples.test_convenience_functions()
        print(" PASS:  Convenience functions example completed")
        
        # Generate compliance report
        print("\nGenerating compliance report...")
        factory = get_test_repository_factory()
        report = factory.generate_compliance_report()
        print(report)
        
        # Cleanup resources
        print("\nCleaning up resources...")
        await factory.cleanup_resources()
        print(" PASS:  Cleanup completed")
    
    # Run all examples
    asyncio.run(run_examples())
    
    print("\n CELEBRATION:  All examples completed successfully!")
    print("\nKey takeaways:")
    print("1. Always use factory.get_test_session() for session management")
    print("2. Create repositories through factory methods only")
    print("3. Use context managers for automatic cleanup")
    print("4. Run compliance checks to detect violations")
    print("5. Leverage data factories for efficient test setup")


if __name__ == "__main__":
    main()