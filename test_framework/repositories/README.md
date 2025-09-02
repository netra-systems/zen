# TestRepositoryFactory - SSOT Database Access

The TestRepositoryFactory enforces Single Source of Truth (SSOT) principles for all test database access, providing type-safe repository creation, automatic session management, and compliance checking.

## Quick Start

```python
from test_framework.repositories import TestRepositoryFactory

async def test_user_operations():
    factory = TestRepositoryFactory.get_instance()
    
    # CORRECT: Use managed session with automatic rollback
    async with factory.get_test_session() as session:
        # Create repository through factory (SSOT enforcement)
        user_repo = factory.create_user_repository(session)
        
        # Perform operations
        user = await user_repo.create_user(session, {
            "full_name": "Test User",
            "email": "test@example.com"
        })
        
        # Session automatically rolled back after test
```

## Features

- **SSOT Enforcement**: Single factory for all test repository access
- **Type-Safe Creation**: Factory methods for all repository types
- **Automatic Session Management**: Context managers with cleanup
- **Transaction Rollback**: Automatic rollback after each test
- **Compliance Checking**: Detect repository pattern violations
- **Real Database Testing**: No mocks - real PostgreSQL containers
- **Cross-Service Support**: Backend and auth service repositories

## Repository Types Supported

### Backend Repositories
- `UserRepository` - User management operations
- `SecretRepository` - User secrets and API keys
- `ToolUsageRepository` - Tool usage logging

### Auth Service Repositories  
- `AuthUserRepository` - OAuth and local user authentication
- `AuthSessionRepository` - Session management
- `AuthAuditRepository` - Audit logging

## Core Usage Patterns

### 1. Basic Repository Operations

```python
async def test_basic_operations():
    factory = TestRepositoryFactory.get_instance()
    
    async with factory.get_test_session() as session:
        user_repo = factory.create_user_repository(session)
        
        # Create
        user = await user_repo.create_user(session, {
            "full_name": "Test User",
            "email": "test@example.com",
            "plan_tier": "free"
        })
        
        # Read
        found_user = await user_repo.get_by_email(session, "test@example.com")
        
        # Update
        success = await user_repo.update_by_id(user.id, plan_tier="pro")
        
        # Query
        active_users = await user_repo.get_active_users(session)
```

### 2. Multiple Repository Usage

```python
async def test_related_data():
    factory = TestRepositoryFactory.get_instance()
    
    async with factory.get_test_session() as session:
        user_repo = factory.create_user_repository(session)
        secret_repo = factory.create_secret_repository(session)
        
        # Create user
        user = await user_repo.create_user(session, {
            "full_name": "Multi Test",
            "email": "multi@example.com"
        })
        
        # Create related secret
        secret = await secret_repo.create(
            user_id=user.id,
            key="API_KEY",
            encrypted_value="encrypted_value"
        )
        
        # Query relationships
        user_secrets = await secret_repo.get_user_secrets(user.id)
        assert len(user_secrets) == 1
```

### 3. Auth Service Repositories

```python
async def test_auth_operations():
    factory = TestRepositoryFactory.get_instance()
    
    # Auth repositories use context managers
    async with await factory.create_auth_user_repository() as auth_repo:
        oauth_user = await auth_repo.create_oauth_user({
            "email": "oauth@example.com",
            "name": "OAuth User",
            "provider": "google",
            "id": "google_123"
        })
    
    async with await factory.create_auth_session_repository() as session_repo:
        session = await session_repo.create_session(
            user_id=oauth_user.id,
            refresh_token="token_123",
            client_info={"ip": "127.0.0.1"}
        )
```

### 4. Test Data Factories

```python
async def test_with_factories():
    factory = TestRepositoryFactory.get_instance()
    
    async with factory.get_test_session() as session:
        factories = await factory.create_test_data_factories(session)
        
        # Easy user creation
        user1 = await factories["create_user"](
            name="Factory User",
            email="factory@example.com"
        )
        
        # Auto-generated email
        user2 = await factories["create_user"]()
```

### 5. Convenience Functions

```python
from test_framework.repositories import (
    get_test_session,
    create_test_repositories
)

async def test_convenience():
    # Simplified session access
    async with get_test_session() as session:
        # Create all common repositories
        repos = await create_test_repositories(session)
        
        user = await repos["user"].create_user(session, {
            "full_name": "Convenience Test",
            "email": "convenience@example.com"
        })
```

## Database Configuration

The factory automatically configures database connections based on environment variables:

### Backend Database
- `TEST_DATABASE_URL` - Direct test database URL
- `POSTGRES_HOST` - Database host (default: localhost)
- `POSTGRES_PORT` - Database port (default: 5434 for tests)
- `POSTGRES_USER` - Database user (default: postgres)
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_DB` - Database name (default: netra_test)

### Auth Database
- `AUTH_TEST_DATABASE_URL` - Direct auth database URL
- `AUTH_POSTGRES_*` - Auth-specific overrides

## Transaction Management

### Automatic Rollback (Default)
```python
# Default behavior - all changes rolled back
async with factory.get_test_session() as session:
    user_repo = factory.create_user_repository(session)
    user = await user_repo.create_user(session, {...})
    # User is automatically rolled back
```

### Commit Mode (Special Cases)
```python
# Disable rollback for setup/teardown
async with factory.get_test_session(rollback=False) as session:
    user_repo = factory.create_user_repository(session)
    user = await user_repo.create_user(session, {...})
    # User is committed to database
```

## Compliance Checking

### Automatic Violation Detection
```python
from test_framework.repositories import check_repository_compliance

def test_compliance():
    # Perform repository operations...
    
    # Check for violations
    report = check_repository_compliance()
    assert report.is_compliant
    assert len(report.violations) == 0
```

### Pre-commit Hook
```bash
# Add to .git/hooks/pre-commit
python scripts/check_repository_compliance.py
```

### Manual Compliance Check
```bash
# Check specific files
python scripts/check_repository_compliance.py --files test_user.py

# Check with auto-fix
python scripts/check_repository_compliance.py --fix

# Verbose output
python scripts/check_repository_compliance.py --verbose
```

## Error Handling

The factory automatically handles errors and ensures cleanup:

```python
async def test_error_handling():
    factory = TestRepositoryFactory.get_instance()
    
    try:
        async with factory.get_test_session() as session:
            user_repo = factory.create_user_repository(session)
            
            user = await user_repo.create_user(session, {...})
            
            # Simulate error
            raise ValueError("Test error")
    except ValueError:
        pass  # Error expected
    
    # Verify rollback occurred
    async with factory.get_test_session() as session:
        user_repo = factory.create_user_repository(session)
        # User should not exist due to rollback
        found_user = await user_repo.get_by_email(session, "test@example.com")
        assert found_user is None
```

## Best Practices

### ✅ DO

1. **Always use the factory**: Create repositories only through factory methods
2. **Use context managers**: Always use `async with` for session management
3. **Test isolation**: Let transactions roll back by default
4. **Check compliance**: Run compliance checks in CI/CD
5. **Real databases**: Use real PostgreSQL containers, not mocks

### ❌ DON'T

1. **Direct SQLAlchemy**: Never use `create_async_engine`, `AsyncSession` directly in tests
2. **Direct instantiation**: Never use `UserRepository()` directly in tests  
3. **Session leaks**: Never create sessions outside the factory
4. **Skip rollback**: Don't disable rollback unless absolutely necessary
5. **Mock databases**: Don't use SQLite or mocks for integration tests

## Migration Guide

### Before (WRONG)
```python
# ❌ Old pattern - violates SSOT
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from netra_backend.app.db.repositories.user_repository import UserRepository

async def test_user_old():
    engine = create_async_engine("postgresql://...")
    session = AsyncSession(engine)
    
    user_repo = UserRepository()  # Direct instantiation
    user = await user_repo.create(session, {...})  # Manual session passing
    
    await session.close()  # Manual cleanup
```

### After (CORRECT)  
```python
# ✅ New pattern - follows SSOT
from test_framework.repositories import TestRepositoryFactory

async def test_user_new():
    factory = TestRepositoryFactory.get_instance()
    
    async with factory.get_test_session() as session:
        user_repo = factory.create_user_repository(session)
        user = await user_repo.create_user(session, {...})
        # Automatic cleanup and rollback
```

## Troubleshooting

### Common Issues

1. **"Session required" error**
   ```python
   # Fix: Always pass session to repository methods
   user_repo = factory.create_user_repository(session)  # Pass session
   ```

2. **Database connection errors**
   ```bash
   # Check database is running
   docker ps | grep postgres
   
   # Check environment variables
   echo $POSTGRES_HOST $POSTGRES_PORT
   ```

3. **Compliance violations**
   ```bash
   # Run compliance check with fixes
   python scripts/check_repository_compliance.py --fix --verbose
   ```

4. **Import errors**
   ```python
   # Correct import
   from test_framework.repositories import TestRepositoryFactory
   ```

### Performance Optimization

1. **Reuse factory instance**
   ```python
   # Good - reuse singleton
   factory = TestRepositoryFactory.get_instance()
   ```

2. **Batch operations in single session**
   ```python
   async with factory.get_test_session() as session:
       # Multiple operations in one session
       user1 = await user_repo.create_user(session, {...})
       user2 = await user_repo.create_user(session, {...})
   ```

3. **Use data factories for setup**
   ```python
   factories = await factory.create_test_data_factories(session)
   users = [await factories["create_user"]() for _ in range(10)]
   ```

## Integration with Testing Frameworks

### pytest
```python
import pytest
from test_framework.repositories import TestRepositoryFactory

@pytest.fixture
async def repository_factory():
    factory = TestRepositoryFactory.get_instance()
    yield factory
    await factory.cleanup_resources()

async def test_with_fixture(repository_factory):
    async with repository_factory.get_test_session() as session:
        user_repo = repository_factory.create_user_repository(session)
        # Test logic...
```

### unittest
```python
import unittest
import asyncio
from test_framework.repositories import TestRepositoryFactory

class TestWithFactory(unittest.TestCase):
    def setUp(self):
        self.factory = TestRepositoryFactory.get_instance()
    
    def tearDown(self):
        asyncio.run(self.factory.cleanup_resources())
    
    def test_user_operations(self):
        async def run_test():
            async with self.factory.get_test_session() as session:
                user_repo = self.factory.create_user_repository(session)
                # Test logic...
        
        asyncio.run(run_test())
```

## Architecture Decision Record (ADR)

### Why TestRepositoryFactory?

1. **SSOT Enforcement**: Prevents multiple patterns for database access
2. **Resource Management**: Automatic cleanup prevents connection leaks
3. **Test Isolation**: Rollback ensures tests don't affect each other
4. **Type Safety**: Factory methods provide type hints and validation
5. **Compliance**: Automated checking prevents pattern violations
6. **Real Testing**: Uses actual databases, not mocks

### Design Principles

1. **Single Responsibility**: Factory only handles repository creation
2. **Dependency Injection**: Repositories receive managed sessions
3. **Context Management**: Automatic resource cleanup
4. **Fail Fast**: Compliance violations caught early
5. **Zero Configuration**: Smart defaults with override capability

## Contributing

When adding new repository types:

1. Add factory method to `TestRepositoryFactory`
2. Update compliance checker patterns
3. Add integration tests
4. Update documentation
5. Run compliance checks

Example:
```python
# Add to TestRepositoryFactory
def create_new_repository(self, session: AsyncSession) -> NewRepository:
    if session is None:
        raise RepositoryComplianceError(
            "Session required. Use: async with factory.get_test_session() as session"
        )
    self._validate_session_compliance(session)
    return NewRepository(session)
```

## Support

For issues or questions:
1. Check this documentation
2. Run compliance checker with `--verbose`
3. Check integration tests for examples
4. Review violation messages for guidance

The TestRepositoryFactory ensures reliable, consistent, and maintainable database testing across the entire Netra platform.