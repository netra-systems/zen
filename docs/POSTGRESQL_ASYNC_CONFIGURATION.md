# PostgreSQL Async Configuration - Central Documentation

## Executive Summary
This document establishes the **single source of truth** for PostgreSQL async configuration across the Netra platform. All services MUST use async-native drivers (asyncpg) exclusively. No synchronous patterns (psycopg2) are permitted in production code.

## Current Issues Identified

### 1. Mixed Sync/Async Patterns
- **Backend Service**: Uses BOTH sync (psycopg2) and async (asyncpg) patterns
- **Auth Service**: Partially async but with sync fallbacks
- **Database Scripts**: All using sync psycopg2
- **Dev Launcher**: Mixed patterns with sync fallbacks

### 2. Inconsistent Connection Management
- Multiple connection managers with different patterns
- No unified approach to pooling
- Different error handling strategies
- Cloud SQL connector not implemented

### 3. Legacy Code
- 151 files still importing/using sync patterns
- Database scripts using raw psycopg2
- Migration tools using sync connections
- Test fixtures with mixed patterns

## Canonical Async-Only Configuration

### Core Dependencies
```txt
# requirements.txt - REMOVE psycopg2-binary
sqlalchemy>=2.0.0
asyncpg>=0.29.0
cloud-sql-python-connector[asyncpg]>=1.7.0
# For local development/testing only
aiosqlite>=0.19.0
```

### Local Development Configuration

```python
# netra_backend/app/db/postgres_async.py
"""PostgreSQL Async-Only Connection Manager"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import text

class AsyncPostgresManager:
    """Async-only PostgreSQL connection manager"""
    
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker | None = None
        self._initialized = False
    
    async def initialize_local(self):
        """Initialize for local development with Docker PostgreSQL"""
        if self._initialized:
            return
        
        # Local Docker PostgreSQL URL
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:password@localhost:5432/netra"
        )
        
        # Create async engine with proper pooling for local dev
        self.engine = create_async_engine(
            database_url,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            poolclass=AsyncAdaptedQueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=60,
            pool_recycle=3600,
            pool_pre_ping=True,
            pool_reset_on_return="rollback",
        )
        
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        self._initialized = True
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session"""
        if not self._initialized:
            await self.initialize_local()
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    async def close(self):
        """Close all connections"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False

# Global instance
async_db = AsyncPostgresManager()

# FastAPI dependency
async def get_db_session():
    """Dependency for FastAPI routes"""
    async with async_db.get_session() as session:
        yield session
```

### Cloud Run Configuration

```python
# netra_backend/app/db/postgres_cloud.py
"""PostgreSQL Cloud Run Configuration with Cloud SQL Connector"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from google.cloud.sql.connector import Connector
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

class CloudSQLManager:
    """Cloud SQL async connection manager for Cloud Run"""
    
    def __init__(self):
        self.connector = Connector()
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker | None = None
        self._initialized = False
    
    async def initialize_cloud_run(self):
        """Initialize for Cloud Run with Cloud SQL"""
        if self._initialized:
            return
        
        # Cloud SQL configuration from environment
        db_user = os.environ["DB_USER"]
        db_pass = os.environ["DB_PASS"]
        db_name = os.environ["DB_NAME"]
        instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]
        
        # Create connection function for Cloud SQL
        def getconn():
            return self.connector.connect(
                instance_connection_name,
                "asyncpg",
                user=db_user,
                password=db_pass,
                db=db_name,
            )
        
        # Create async engine with NullPool for serverless
        self.engine = create_async_engine(
            "postgresql+asyncpg://",
            creator=getconn,
            echo=False,
            poolclass=NullPool,  # Required for Cloud Run
        )
        
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        self._initialized = True
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session"""
        if not self._initialized:
            await self.initialize_cloud_run()
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close all connections"""
        if self.engine:
            await self.engine.dispose()
        self.connector.close()
        self._initialized = False

# Global instance
cloud_db = CloudSQLManager()

# FastAPI dependency
async def get_cloud_db_session():
    """Dependency for FastAPI routes in Cloud Run"""
    async with cloud_db.get_session() as session:
        yield session
```

### Unified Configuration Manager

```python
# netra_backend/app/db/postgres_unified.py
"""Unified PostgreSQL Async Configuration"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

class UnifiedPostgresDB:
    """Unified async PostgreSQL manager that auto-detects environment"""
    
    def __init__(self):
        self.is_cloud_run = os.getenv("K_SERVICE") is not None
        self.manager = None
    
    async def initialize(self):
        """Initialize appropriate manager based on environment"""
        if self.is_cloud_run:
            from .postgres_cloud import cloud_db
            self.manager = cloud_db
            await self.manager.initialize_cloud_run()
        else:
            from .postgres_async import async_db
            self.manager = async_db
            await self.manager.initialize_local()
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session from appropriate manager"""
        if not self.manager:
            await self.initialize()
        
        async with self.manager.get_session() as session:
            yield session
    
    async def close(self):
        """Close connections"""
        if self.manager:
            await self.manager.close()

# Global unified instance
unified_db = UnifiedPostgresDB()

# Single FastAPI dependency for all environments
async def get_db():
    """Universal database session dependency"""
    async with unified_db.get_session() as session:
        yield session
```

## Migration Plan

### Phase 1: Backend Service (Week 1)
1. Create new async-only modules above
2. Update all routes to use async sessions
3. Remove sync Database class from postgres_core.py
4. Update all imports to use unified_db
5. Remove psycopg2-binary from requirements.txt

### Phase 2: Auth Service (Week 1)
1. Implement same pattern as backend
2. Remove all sync fallbacks
3. Ensure Cloud SQL connector integration
4. Update all database operations to async

### Phase 3: Database Scripts (Week 2)
1. Convert all database scripts to async
2. Use asyncio.run() for script execution
3. Remove all psycopg2 imports
4. Update migration tools to use async

### Phase 4: Testing & Cleanup (Week 2)
1. Update all test fixtures to async
2. Remove legacy connection managers
3. Delete all sync database code
4. Verify Cloud Run deployment

## Testing Strategy

### Local Testing
```python
# test_local_connection.py
import asyncio
from netra_backend.app.db.postgres_unified import unified_db

async def test_local():
    """Test local PostgreSQL connection"""
    await unified_db.initialize()
    
    async with unified_db.get_session() as session:
        result = await session.execute("SELECT 1")
        assert result.scalar_one() == 1
    
    await unified_db.close()

if __name__ == "__main__":
    asyncio.run(test_local())
```

### Cloud Run Testing
```bash
# Set Cloud Run environment variables
export K_SERVICE=test-service
export DB_USER=myuser
export DB_PASS=mypass
export DB_NAME=mydb
export INSTANCE_CONNECTION_NAME=project:region:instance

# Run test
python test_cloud_connection.py
```

## Environment Variables

### Local Development
```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/netra
SQL_ECHO=false
```

### Cloud Run Production
```env
K_SERVICE=netra-backend
DB_USER=netra-user
DB_PASS=<secure-password>
DB_NAME=netra-production
INSTANCE_CONNECTION_NAME=netra-project:us-central1:netra-postgres
```

## Common Issues & Solutions

### Issue 1: SSL/sslmode Parameters
**Problem**: asyncpg doesn't understand `sslmode` parameter
**Solution**: Convert `sslmode=` to `ssl=` or remove for Unix sockets

### Issue 2: Connection Pool Exhaustion
**Problem**: Running out of connections in Cloud Run
**Solution**: Use NullPool for serverless environments

### Issue 3: Mixed Sync/Async in Tests
**Problem**: Tests failing due to mixed patterns
**Solution**: Use async fixtures exclusively with pytest-asyncio

### Issue 4: Migration Tool Compatibility
**Problem**: Alembic needs sync connections
**Solution**: Create temporary sync engine only for migrations

## Performance Optimizations

### Connection Pooling
- **Local**: AsyncAdaptedQueuePool with size=10, overflow=20
- **Cloud Run**: NullPool (no pooling, serverless optimized)
- **Staging**: Same as production configuration

### Query Optimization
- Always use `pool_pre_ping=True` for resilience
- Set `pool_recycle=3600` to refresh connections hourly
- Use `pool_reset_on_return="rollback"` for safety

### Monitoring
- Track pool metrics in local development
- Use Cloud SQL insights for production
- Monitor connection count and latency

## Compliance Checklist

- [ ] All sync imports removed (no psycopg2)
- [ ] All database operations use async/await
- [ ] Cloud SQL connector integrated for Cloud Run
- [ ] NullPool used for serverless environments
- [ ] Connection resilience implemented (pre-ping, recycle)
- [ ] Unified configuration for all environments
- [ ] Tests updated to async patterns
- [ ] Documentation updated
- [ ] Legacy code removed
- [ ] Performance metrics baselined

## References
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Cloud SQL Python Connector](https://github.com/GoogleCloudPlatform/cloud-sql-python-connector)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/tips/sql)