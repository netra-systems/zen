# Database Architecture Fix Implementation Prompt

## Context
We have identified recurring database connection failures in GCP staging caused by URL format incompatibilities between synchronous (psycopg2) and asynchronous (asyncpg) database drivers. The root cause and architectural learnings have been documented.

## Reference Documents
1. **Root Cause Analysis**: `DATABASE_SETUP_ISSUE_ROOT_CAUSE.md`
2. **Architecture Learnings**: `DATABASE_ARCHITECTURE_LEARNINGS.md`

## Implementation Task

### Objective
Implement a unified `DatabaseManager` class that cleanly separates synchronous and asynchronous database access, eliminating URL format conflicts.

### Required Implementation

Create a new file `netra_backend/app/db/database_manager.py` with the following structure:

```python
class DatabaseManager:
    @staticmethod
    def get_migration_url_sync_format() -> str:
        """Get sync URL for migrations (psycopg2/pg8000)"""
        base_url = get_base_database_url()
        return f"{base_url}?sslmode=require"  # Sync format
    
    @staticmethod  
    def get_application_url_async() -> str:
        """Get async URL for application (asyncpg)"""
        base_url = get_base_database_url()
        return f"postgresql+asyncpg://{base_url}?ssl=require"  # Async format
```

ALWAYS refer to sync functions with sync in name of function
and async with async in name of function for complete clarity


### Detailed Requirements

1. **Implement `get_base_database_url()` function**:
   - Extract DATABASE_URL from environment/configuration
   - Strip any existing driver prefixes (postgresql://, postgresql+asyncpg://, etc.)
   - Remove any SSL-related parameters (sslmode=, ssl=)
   - Return clean base URL in format: `user:password@host:port/database`

2. **Add URL validation methods**:
   - `validate_base_url()`: Ensure no driver-specific elements remain
   - `validate_migration_url_sync_format()`: Confirm sync driver compatibility
   - `validate_application_url()`: Confirm async driver compatibility

3. **Implement connection factory methods**:
   - `create_migration_engine()`: Return sync SQLAlchemy engine for Alembic
   - `create_application_engine()`: Return async SQLAlchemy engine for FastAPI
   - `get_migration_session()`: Return sync session for migrations
   - `get_application_session()`: Return async session for app runtime

4. **Add environment-specific logic**:
   - Detect if running in Cloud SQL environment (check for K_SERVICE, INSTANCE_CONNECTION_NAME)
   - Handle Cloud SQL Unix socket connections (remove SSL parameters entirely)
   - Support local development (may not need SSL)

5. **Include comprehensive error handling**:
   - Catch and clearly report URL format mismatches
   - Detect if wrong driver is being used with wrong URL format
   - Provide helpful error messages with correction suggestions

### Migration Updates Required

1. **Update `netra_backend/app/alembic/env.py`**:
   - Import and use `DatabaseManager.get_migration_url()`
   - Remove manual URL conversion logic (lines 56-72)
   - Ensure using sync driver (psycopg2 or pg8000)

2. **Update `netra_backend/app/db/postgres_core.py`**:
   - Import and use `DatabaseManager.get_application_url()`
   - Remove redundant URL conversion functions (lines 163-233)
   - Keep the validation check but reference DatabaseManager

3. **Update `netra_backend/app/db/postgres_async.py`**:
   - Use `DatabaseManager.get_application_url()`
   - Remove local URL conversion logic (lines 49-62)

4. **Update `netra_backend/app/db/postgres_cloud.py`**:
   - Integrate with DatabaseManager for consistency
   - Ensure Cloud SQL specific logic is preserved

### Testing Requirements

Create `netra_backend/tests/unit/db/test_database_manager.py` with:

1. **URL Conversion Tests**:
   ```python
   def test_url_conversions():
       """Test all URL format conversions"""
       test_cases = [
           ("postgresql://u:p@h/d?sslmode=require", "migration", "postgresql://u:p@h/d?sslmode=require"),
           ("postgresql://u:p@h/d?sslmode=require", "application", "postgresql+asyncpg://u:p@h/d?ssl=require"),
           ("postgresql+asyncpg://u:p@h/d?ssl=require", "migration", "postgresql://u:p@h/d?sslmode=require"),
       ]
   ```

2. **Environment Detection Tests**:
   - Test Cloud SQL detection
   - Test local development detection
   - Test staging/production detection

3. **Error Handling Tests**:
   - Test invalid URL formats
   - Test driver mismatches
   - Test missing configuration

4. **Integration Tests**:
   - Test actual database connections with both sync and async engines
   - Verify migrations can run with migration URL
   - Verify application can connect with application URL

### Deployment Validation

1. **Update GCP Secret Manager**:
   - Ensure DATABASE_URL has no driver-specific elements
   - Store as: `postgresql://user:password@/database?host=/cloudsql/project:region:instance`
   - NO sslmode or ssl parameters

2. **Add startup validation**:
   ```python
   async def validate_database_configuration():
       """Validate database configuration on startup"""
       try:
           # Test migration URL (sync)
           migration_url = DatabaseManager.get_migration_url()
           # Validate format but don't connect
           
           # Test application URL (async)  
           app_url = DatabaseManager.get_application_url()
           # Actually test connection
           
           logger.info("Database configuration validated successfully")
       except Exception as e:
           logger.error(f"Database configuration invalid: {e}")
           raise
   ```

3. **Add health check endpoint**:
   - Include URL format validation
   - Report which driver is in use
   - Show connection pool status

### Success Criteria

1. **No more "sslmode" errors** in GCP staging logs
2. **Migrations run successfully** with sync driver
3. **Application connects successfully** with async driver
4. **Single source of truth** for database URL management
5. **Clear error messages** when configuration is wrong
6. **All existing tests pass** after refactoring
7. **New tests provide 100% coverage** of DatabaseManager

### Important Notes

- **DO NOT** try to make migrations async - they should remain synchronous
- **DO NOT** mix sync and async patterns in the same module
- **DO** maintain clear separation between migration and application database access
- **DO** preserve all existing Cloud SQL specific logic
- **DO** ensure backward compatibility during transition

### Rollout Plan

1. **Phase 1**: Implement DatabaseManager with tests
2. **Phase 2**: Update migration system to use DatabaseManager
3. **Phase 3**: Update application database initialization
4. **Phase 4**: Deploy to staging and validate
5. **Phase 5**: Update documentation and remove old code

### Reference Implementation Pattern

The DatabaseManager should follow this pattern:

```python
import os
import re
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

class DatabaseManager:
    """Unified database URL management for sync and async access"""
    
    @staticmethod
    def get_base_database_url() -> str:
        """Get clean base URL without driver-specific elements"""
        url = os.getenv("DATABASE_URL", "")
        
        # Remove driver prefix
        if "://" in url:
            url = url.split("://", 1)[1]
        
        # Remove SSL parameters
        url = re.sub(r'[?&](sslmode|ssl)=[^&]*', '', url)
        
        return url
    
    @staticmethod
    def get_migration_url() -> str:
        """Get sync URL for migrations (psycopg2/pg8000)"""
        base_url = DatabaseManager.get_base_database_url()
        
        # Cloud SQL Unix socket doesn't need SSL params
        if "/cloudsql/" in base_url:
            return f"postgresql://{base_url}"
        
        return f"postgresql://{base_url}?sslmode=require"
    
    @staticmethod
    def get_application_url() -> str:
        """Get async URL for application (asyncpg)"""
        base_url = DatabaseManager.get_base_database_url()
        
        # Cloud SQL Unix socket doesn't need SSL params
        if "/cloudsql/" in base_url:
            return f"postgresql+asyncpg://{base_url}"
        
        return f"postgresql+asyncpg://{base_url}?ssl=require"
```

This implementation ensures clean separation of concerns and eliminates URL format conflicts.