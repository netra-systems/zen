# Database Setup Guide for Integration Testing

This guide provides multiple options for setting up database connectivity for integration tests.

## Quick Start (Recommended)

The easiest way to run integration tests with database connectivity:

```bash
# Start Docker Desktop, then:
python tests/unified_test_runner.py --real-services

# This will automatically:
# - Start PostgreSQL containers on port 5434
# - Start Redis containers on port 6381
# - Run tests with real database connections
```

## Current Issues and Fixes

### Problem: `real_postgres_connection` Fixture Not Found

**Root Cause**: Tests require database connectivity but Docker services aren't running.

**Status**: ✅ **FIXED** - Enhanced fixtures now provide clear error messages and guidance.

### Problem: `ConnectionRefusedError [WinError 1225]`

**Root Cause**: Tests trying to connect to database services that aren't available.

**Status**: ✅ **FIXED** - Tests now gracefully skip with helpful messages when database unavailable.

## Setup Options

### Option 1: Docker-based Testing (Recommended)

This is the standard approach used by the unified test runner:

```bash
# Prerequisites
1. Install Docker Desktop for Windows
2. Start Docker Desktop
3. Ensure Docker is accessible from command line

# Run tests
python tests/unified_test_runner.py --real-services --category integration
```

**Database Configuration:**
- PostgreSQL: `localhost:5434` (test_user/test_password/netra_test)
- Redis: `localhost:6381`
- Environment: Isolated test containers

### Option 2: Local Database Setup

If you prefer local PostgreSQL installation:

```bash
# Install PostgreSQL locally
# Configure connection in .env.test:
DB_HOST=localhost
DB_PORT=5432  # Standard PostgreSQL port
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=netra_test

# Set environment
export USE_REAL_SERVICES=true

# Run tests
pytest tests/integration/ -v
```

### Option 3: Skip Database Tests

For development without database dependency:

```bash
# Run tests without real services (will skip database-dependent tests)
pytest tests/integration/ -v

# Or explicitly disable
export USE_REAL_SERVICES=false
pytest tests/integration/ -v
```

## Fixture Behavior

The `real_postgres_connection` fixture now provides intelligent behavior:

### When USE_REAL_SERVICES=false
- ✅ Returns `{"available": False}` - tests skip gracefully
- ✅ No Docker dependency required

### When USE_REAL_SERVICES=true but Docker not running  
- ✅ Returns error with guidance: "Start Docker Desktop and run: python tests/unified_test_runner.py --real-services"
- ✅ Tests skip with clear instructions

### When USE_REAL_SERVICES=true and Docker running
- ✅ Starts test database containers automatically
- ✅ Provides real PostgreSQL connection
- ✅ Cleans up after tests complete

## Test Writing Patterns

### Pattern 1: Using Database Test Helpers

```python
import pytest
from test_framework.database_test_helpers import require_database_or_skip

@pytest.mark.asyncio
async def test_my_database_feature(real_postgres_connection):
    # Gracefully skip if database not available
    require_database_or_skip(real_postgres_connection, "test_my_database_feature")
    
    # Database is available - proceed with test
    async with real_postgres_connection["engine"].begin() as conn:
        result = await conn.execute("SELECT 1")
        assert result.fetchone()[0] == 1
```

### Pattern 2: Using Context Manager

```python
import pytest
from test_framework.database_test_helpers import DatabaseTestContext

@pytest.mark.asyncio
async def test_with_context(real_postgres_connection, database_test_context):
    # Context manager handles availability checking and cleanup
    async with database_test_context(real_postgres_connection, "test_with_context") as db:
        # db is the database session, ready to use
        result = await db.execute("SELECT NOW()")
        assert result.fetchone() is not None
```

### Pattern 3: Conditional Testing

```python
import pytest
from test_framework.database_test_helpers import check_database_availability

def test_conditional_database():
    availability = check_database_availability()
    
    if not availability["docker_running"]:
        pytest.skip("Docker not running - guidance: " + ", ".join(availability["guidance"]))
    
    # Proceed with test...
```

## Troubleshooting

### Issue: "Docker not running or not accessible"
**Solution**: 
1. Install Docker Desktop
2. Start Docker Desktop  
3. Verify with: `docker ps`

### Issue: "Database not ready after 30 attempts"
**Solution**:
1. Stop existing containers: `docker compose down`
2. Restart services: `python tests/unified_test_runner.py --real-services`

### Issue: "Port 5434 already in use"
**Solution**:
1. Find conflicting process: `netstat -ano | findstr :5434`
2. Stop conflicting service or use different port in `.env.test`

### Issue: Import errors in integration tests
**Solution**:
1. Check that modules exist in the expected locations
2. Verify PYTHONPATH includes project root
3. Check for circular import issues

## Environment Variables

Key environment variables for database testing:

```bash
# Enable real services
USE_REAL_SERVICES=true

# Test database configuration
DB_HOST=localhost
DB_PORT=5434
DB_USER=test_user  
DB_PASSWORD=test_password
DB_NAME=netra_test

# Test environment
ENVIRONMENT=test
```

## Success Validation

To verify your setup works:

```bash
# Run the database connectivity test
python test_db_connectivity.py

# Should show:
# Docker Services: OK (if Docker running)
# Database Connectivity: OK (if containers started)

# Run fixture validation
python test_database_fix_validation.py

# Should show:
# [SUCCESS] All database fixes validated!
```

## Integration with Unified Test Runner

The unified test runner automatically handles database setup:

```bash
# Run with real services (starts Docker automatically)
python tests/unified_test_runner.py --real-services

# Run specific integration tests
python tests/unified_test_runner.py --category integration --real-services

# Run with coverage and real services  
python tests/unified_test_runner.py --real-services --category integration --coverage
```

The test runner will:
1. Check if Docker is running
2. Start required containers (PostgreSQL, Redis)
3. Wait for services to be ready
4. Run tests with real database connections
5. Clean up containers after tests complete

---

**Next Steps**: With database connectivity fixed, integration tests should run successfully. The 6 WebSocket integration tests that were failing due to missing `real_postgres_connection` fixture should now pass or skip gracefully with clear guidance.