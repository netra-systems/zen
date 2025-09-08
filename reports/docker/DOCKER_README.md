# Docker Configuration - THE ONLY TWO PATHS

## CRITICAL: Use ONLY these docker-compose files

There are **ONLY TWO VALID OPTIONS** for running Docker:

## Option 1: Development Environment (DEFAULT)
```bash
# Start development - THIS IS THE DEFAULT
docker-compose up

# Stop development
docker-compose down
```

This starts:
- `dev-postgres` - PostgreSQL database
- `dev-redis` - Redis cache  
- `dev-clickhouse` - ClickHouse analytics
- `dev-auth` - Authentication service
- `dev-backend` - Backend API
- `dev-frontend` - Frontend application

## Option 2: Test Environment

Two ways to run tests:

### 2a. Basic Test Environment (from main docker-compose.yml)
```bash
# Start test environment with profile
docker-compose --profile test up

# Stop test environment
docker-compose down
```

### 2b. Optimized Test Environment (for CI/automated testing)
```bash
# Start optimized test environment with tmpfs (ultra-fast, ephemeral)
docker-compose -f docker-compose.test.yml up

# Stop test environment
docker-compose -f docker-compose.test.yml down
```

**Note:** `docker-compose.test.yml` has performance optimizations (tmpfs, fsync=off) for faster test execution. Used by test runners and CI.

## DELETED FILES (No Longer Exist)

These files were deleted because they created duplicate images:

- ❌ ~~`docker-compose.dev.yml`~~ - DELETED (created images without -dev suffix)
- ❌ ~~`docker-compose.minimal.yml`~~ - DELETED (redundant)
- ❌ ~~`docker-compose.windows.yml`~~ - DELETED (unnecessary)
- ❌ ~~`docker-compose.optimized.yml`~~ - DELETED (should be default)
- ❌ ~~`docker-compose.dev-minimal.yml`~~ - DELETED (confusing)

## Image Naming Convention

Correct image names (from main docker-compose.yml):
- ✅ `netra-dev-auth`
- ✅ `netra-dev-backend`  
- ✅ `netra-dev-frontend`
- ✅ `netra-test-auth`
- ✅ `netra-test-backend`
- ✅ `netra-test-frontend`

Incorrect duplicate images (from deprecated files):
- ❌ `netra-core-generation-1-auth`
- ❌ `netra-core-generation-1-backend`
- ❌ `netra-core-generation-1-frontend`
- ❌ `netra-core-generation-1-analytics`

## Clean Up Duplicate Images

If you have duplicate images, clean them:

```bash
# Stop all containers
docker-compose down

# Remove duplicate images
docker rmi netra-core-generation-1-auth
docker rmi netra-core-generation-1-backend
docker rmi netra-core-generation-1-frontend
docker rmi netra-core-generation-1-analytics

# Or remove all unused images
docker image prune -a
```

## Summary

**USE ONLY:** `docker-compose.yml`
- Default (no flags) = Development
- `--profile test` = Test environment

**NEVER USE:** Any other docker-compose.*.yml files