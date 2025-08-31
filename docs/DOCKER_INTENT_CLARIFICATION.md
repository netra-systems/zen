# Docker Configuration Intent Clarification

## Executive Summary

This document clarifies the intent and purpose of each Docker configuration in the Netra platform. **The DEFAULT is to launch the "dev" context for local development.**

## Key Findings

### 1. Current Docker Configuration Bloat

The project has accumulated multiple Docker configurations with overlapping purposes:
- **8 docker-compose files** (many redundant)
- **13 Dockerfiles** in `/docker/` directory
- **4 additional Dockerfiles** in `/deployment/docker/`
- Multiple launcher scripts with similar functionality

### 2. Intent Clarification

## Primary Docker Configurations (Keep These)

### DEFAULT: Development Context
**Command:** `docker-compose --profile dev up`
- **Purpose:** Local development with hot reload
- **Primary File:** `docker-compose.yml` with `dev` profile
- **Services:** PostgreSQL, Redis, ClickHouse, Auth, Backend, Frontend
- **Features:** Volume mounts for code, hot reload enabled, debug logging

### Testing Context
**Command:** `docker-compose --profile test up`
- **Purpose:** Run integration/e2e tests
- **Primary File:** `docker-compose.yml` with `test` profile
- **Services:** Ephemeral test databases (no persistent volumes)
- **Features:** Isolated test environment, fast teardown

### Production Build Context
**Files:** `/docker/*.Dockerfile` (without .development suffix)
- **Purpose:** Production-ready images with multi-stage builds
- **Features:** Non-root user, minimal size, no dev dependencies

## Docker Files by Directory

### `/docker/` - Local Development & CI
```
backend.Dockerfile              - Production build (multi-stage, optimized)
backend.development.Dockerfile - Dev with hot reload
auth.Dockerfile                - Production build
auth.development.Dockerfile    - Dev with hot reload
frontend.Dockerfile            - Production build
frontend.development.Dockerfile - Dev with hot reload
*.test.Dockerfile              - Test environment configs
```

### `/deployment/docker/` - Cloud Deployments
```
*.gcp.Dockerfile - GCP Cloud Run optimized builds
*.prod.Dockerfile - Production deployment builds
```

## Redundant/Deprecated Files (Consider Removing)

1. **docker-compose.dev.yml** - Redundant with main docker-compose.yml dev profile
2. **docker-compose.windows.yml** - Platform-specific, should be handled by main config
3. **docker-compose.minimal.yml** - Unclear purpose, overlaps with profiles
4. **docker-compose.optimized.yml** - Should be the default, not separate
5. **docker-compose.dev-minimal.yml** - Confusing naming, use profiles instead
6. **analytics.*.Dockerfile** - Analytics service appears removed from architecture

## Recommended Simplification

### 1. Consolidate to Single docker-compose.yml
```yaml
# Use profiles for different contexts
profiles:
  - dev (DEFAULT)
  - test
  - minimal (postgres + redis only)
```

### 2. Standardize Dockerfile Naming
```
/docker/
  [service].dev.Dockerfile    # Development
  [service].prod.Dockerfile   # Production
  [service].test.Dockerfile   # Testing
```

### 3. Single Launcher Script
```bash
# Default launches dev context
python scripts/docker_launcher.py          # Starts dev profile
python scripts/docker_launcher.py --test   # Starts test profile
python scripts/docker_launcher.py --build  # Rebuilds images
```

## Environment-Specific Intents

### Development (DEFAULT)
- **Intent:** Rapid local development
- **Command:** `docker-compose --profile dev up` or `python scripts/docker_launcher.py`
- **Volumes:** Code mounted for hot reload
- **Ports:** 3000 (frontend), 8000 (backend), 8081 (auth)
- **Data:** Persistent volumes for databases

### Testing
- **Intent:** Isolated test execution
- **Command:** `docker-compose --profile test up`
- **Volumes:** No code mounts (uses baked images)
- **Ports:** Alternative ports to avoid conflicts
- **Data:** Ephemeral (no persistent volumes)

### Staging/Production
- **Intent:** Cloud deployment
- **Command:** `python scripts/deploy_to_gcp.py`
- **Images:** Optimized multi-stage builds
- **Security:** Non-root users, minimal attack surface

## Action Items

1. **Remove redundant docker-compose files** - Consolidate into single file with profiles
2. **Clean up unused Dockerfiles** - Remove analytics service files
3. **Update documentation** - Ensure README reflects simplified structure
4. **Set dev as DEFAULT** - Make development the default profile
5. **Simplify launcher scripts** - Single entry point with clear flags

## THE ONLY TWO VALID PATHS

### Option 1: Development Environment (DEFAULT)
```bash
# Start development environment - THIS IS THE DEFAULT
docker-compose up

# Stop development environment
docker-compose down
```

### Option 2: Test Environment
```bash
# Start test environment (ephemeral, for running tests)
docker-compose --profile test up

# Stop test environment
docker-compose down
```

### DEPRECATED - DO NOT USE
```bash
# DO NOT USE THESE:
docker-compose -f docker-compose.dev.yml up     # Creates duplicate images
docker-compose -f docker-compose.minimal.yml up # Redundant
docker-compose -f docker-compose.windows.yml up # Platform-specific, unnecessary
```

**CRITICAL:** Only use the main `docker-compose.yml` file with either:
1. No profile (launches dev by default)
2. `--profile test` (launches test environment)

## Resource Limits

Current configuration properly implements:
- Memory limits per service (256MB - 1GB)
- CPU limits (0.1 - 0.4 cores)
- Maximum 10 named volumes (currently using 5)
- Health checks with appropriate intervals

## Conclusion

The Docker configuration has grown organically with significant redundancy. The primary intent should be:
1. **DEFAULT = Development context** for daily work
2. **Test profile** for CI/testing
3. **Production builds** for deployment

All other variations should be removed or consolidated into these three primary contexts.