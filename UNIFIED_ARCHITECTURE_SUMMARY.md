# Unified Architecture Summary - Netra Apex Platform
**Last Updated: 2025-08-24**

## Executive Summary
The Netra Apex AI Optimization Platform is a unified, coherent system built on three independent microservices (Backend, Auth, Frontend) with centralized infrastructure components for environment management, database connectivity, testing, and deployment.

## 🏗️ Core Architecture Principles

### 1. System Coherence
- **Unified System**: All components work in harmony while maintaining service independence
- **Single Source of Truth**: Every concept exists exactly ONCE within each service
- **Atomic Operations**: All changes must be complete - no partial implementations
- **Environment Isolation**: Complete separation between dev, staging, and production

### 2. Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend Service                        │
│                    Next.js App (Port 3000)                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
        REST API & WebSocket Communication
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Backend Service                         │
│                  FastAPI App (Port 8000)                     │
│         [WebSocket Handler] [Agent System] [APIs]            │
└─────────────────────────────────────────────────────────────┘
                              ↓
              Auth Validation (REST API)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       Auth Service                           │
│                   Auth API (Port 8080)                       │
│                  [JWT Manager] [OAuth]                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        Data Layer                            │
│         [PostgreSQL] [ClickHouse] [Redis]                    │
└─────────────────────────────────────────────────────────────┘
```

## 🔑 Critical Infrastructure Components

### 1. Environment Management (IsolatedEnvironment)
**Location**: `dev_launcher/isolated_environment.py`
**Specification**: `SPEC/unified_environment_management.xml`

#### Key Features:
- **Complete Isolation**: Development and test environments use internal dictionary, not os.environ
- **Source Tracking**: Every environment modification tracked to its source
- **Thread Safety**: RLock protection for concurrent access
- **Subprocess Support**: `get_subprocess_env()` for isolated subprocess launches

#### Usage Pattern:
```python
from dev_launcher.isolated_environment import get_env

env = get_env()
env.enable_isolation()  # For development/testing
database_url = env.get("DATABASE_URL")
env.set("KEY", "value", "component_name")  # With source tracking
```

**CRITICAL**: Direct `os.environ` access is FORBIDDEN outside the unified config module.

### 2. Database Connectivity (CoreDatabaseManager)
**Location**: `shared/database/core_database_manager.py`
**Specification**: `SPEC/database_connectivity_architecture.xml`

#### Key Features:
- **SSL Parameter Resolution**: Automatic conversion between asyncpg (ssl=) and psycopg2 (sslmode=)
- **Cloud SQL Support**: Unix socket handling with automatic SSL parameter removal
- **Driver Compatibility**: Transparent handling of sync/async driver differences
- **Environment Awareness**: Different strategies for dev/staging/production

#### SSL Resolution Rules:
1. **asyncpg**: Convert `sslmode=require` → `ssl=require`
2. **psycopg2**: Convert `ssl=require` → `sslmode=require`
3. **Unix sockets** (/cloudsql/): Remove ALL SSL parameters
4. **Alembic migrations**: Use sync driver URLs only

### 3. Import Management (Zero Tolerance)
**Specification**: `SPEC/import_management_architecture.xml`

#### Absolute Imports ONLY:
```python
# CORRECT - Absolute imports
from netra_backend.app.services.user_service import UserService
from auth_service.auth_core.models import User
from test_framework.fixtures import create_test_user

# FORBIDDEN - Relative imports
from ..services.user_service import UserService  # NEVER
from .models import User  # NEVER
```

#### Enforcement:
- Pre-commit hooks prevent relative imports
- CI/CD pipelines fail on detection
- `python scripts/fix_all_import_issues.py --absolute-only` for fixing

### 4. Test Infrastructure
**Entry Point**: `unified_test_runner.py`
**Specification**: `SPEC/test_infrastructure_architecture.xml`

#### Test Organization:
- **Backend Tests**: `netra_backend/tests/`
- **Auth Tests**: `auth_service/tests/`
- **Frontend Tests**: `frontend/__tests__/`
- **E2E Tests**: `tests/e2e/`
- **Test Framework**: `test_framework/` (shared utilities)

#### Critical Requirements:
1. **Absolute imports only** (no relative imports)
2. **setup_test_path()** before project imports
3. **@pytest.mark.asyncio** for ALL async tests
4. **Service boundaries** strictly enforced
5. **Environment isolation** for all tests

### 5. Deployment Architecture
**Script**: `scripts/deploy_to_gcp.py` (ONLY official script)
**Specification**: `SPEC/deployment_architecture.xml`

#### Environments:
| Environment | Command | Characteristics |
|-------------|---------|-----------------|
| **Development** | `python scripts/dev_launcher.py` | Local, hot-reload, isolated env |
| **Staging** | `python scripts/deploy_to_gcp.py --project netra-staging --build-local` | Cloud Run, SSL, OAuth |
| **Production** | `python scripts/deploy_to_gcp.py --project netra-production --run-checks` | Multi-region, auto-scale |

## 🔄 Inter-Service Communication

### Communication Patterns:
1. **REST APIs**: Synchronous service-to-service HTTP calls
2. **WebSocket**: Real-time bidirectional communication
3. **Shared Interfaces**: Common types in `/shared/` directory
4. **Message Queue**: Async communication (future)

### Forbidden Patterns:
- ❌ Direct database sharing between services
- ❌ Cross-service code imports
- ❌ Shared state without synchronization
- ❌ Bypassing service APIs

## 📊 Critical Learnings & Patterns

### 1. Configuration Management
- **Unified config system** at `netra_backend.app.config`
- **110+ duplicate config files** have been REMOVED
- **Hot reload** via `CONFIG_HOT_RELOAD=true`
- **GCP Secret Manager** for staging/production

### 2. WebSocket Consolidation
- **Single implementation** per functionality
- **8 duplicate implementations** consolidated to 1
- **Composition over duplication**
- **Backward compatibility aliases** for migration

### 3. Authentication Integration
- **Shared auth service** is MANDATORY
- **OAuth-first** with dev login fallback
- **JWT validation** via POST `/auth/validate`
- **Separate auth_users table** with ID sync

### 4. Database Patterns
- **Lazy initialization** for health checks
- **SSL parameter conflicts** resolved automatically
- **Cloud SQL Unix sockets** without SSL parameters
- **Alembic migrations** use sync drivers only

### 5. Testing Best Practices
- **Real services over mocks** for E2E tests
- **Test-Driven Correction (TDC)** for bug fixes
- **Failing test first** to validate understanding
- **Service boundary respect** in test organization

## 🚨 Common Pitfalls & Solutions

### Import Errors
**Problem**: ModuleNotFoundError in tests
**Solution**: Use absolute imports with `setup_test_path()`

### Database Connection Failures
**Problem**: SSL parameter incompatibility
**Solution**: Use CoreDatabaseManager for automatic resolution

### Environment Pollution
**Problem**: Test environment affects system environment
**Solution**: Enable IsolatedEnvironment isolation mode

### WebSocket Duplications
**Problem**: Multiple implementations of same functionality
**Solution**: Extend existing with options, not new variants

### Auth Service Integration
**Problem**: Direct user creation attempts
**Solution**: Use OAuth flow or dev login endpoint

## 📋 Compliance Checklist

### Before ANY Code Change:
1. ✅ Check `SPEC/learnings/index.xml` for related patterns
2. ✅ Validate string literals with query tool
3. ✅ Use absolute imports exclusively
4. ✅ Respect service boundaries
5. ✅ Update tests atomically with code
6. ✅ Use IsolatedEnvironment for env access
7. ✅ Run compliance check script
8. ✅ Ensure atomic, complete changes

### Quality Standards:
- 450 lines per file maximum
- 25 lines per function maximum
- Type hints required
- No secrets in code
- Input validation required

## 🔗 Key Specifications Reference

### Critical Specs (ALWAYS check):
- `SPEC/core.xml` - Core system architecture (v3.0)
- `SPEC/unified_environment_management.xml` - Environment isolation
- `SPEC/database_connectivity_architecture.xml` - Database patterns
- `SPEC/test_infrastructure_architecture.xml` - Testing organization
- `SPEC/import_management_architecture.xml` - Import rules
- `SPEC/deployment_architecture.xml` - Deployment pipeline

### Domain Specs:
- **Testing**: `testing.xml`, `coverage_requirements.xml`
- **Database**: `clickhouse.xml`, `postgres.xml`
- **WebSocket**: `websockets.xml`, `websocket_communication.xml`
- **Security**: `security.xml`, `PRODUCTION_SECRETS_ISOLATION.xml`
- **Learnings**: `learnings/index.xml` (ALWAYS check first)

## 🚀 Quick Start Commands

### Development:
```bash
# Start development environment
python scripts/dev_launcher.py

# Run tests (fast feedback)
python unified_test_runner.py --level integration --no-coverage --fast-fail

# Fix import issues
python scripts/fix_all_import_issues.py --absolute-only

# Check architecture compliance
python scripts/check_architecture_compliance.py
```

### Deployment:
```bash
# Deploy to staging (fast)
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Deploy to production (with checks)
python scripts/deploy_to_gcp.py --project netra-production --run-checks
```

## 📈 Architecture Evolution

### Current State (v3.0):
- Three-service architecture
- Unified infrastructure components
- Comprehensive testing framework
- Multi-environment deployment

### Near Term:
- Distributed tracing (OpenTelemetry)
- Service mesh for communication
- Advanced circuit breakers
- Enhanced observability

### Future:
- Event-driven architecture
- CQRS for read/write separation
- Multi-region deployment
- Event sourcing

---

**Remember**: 
- Every concept exists ONCE per service
- All changes must be atomic and complete
- Respect service boundaries always
- Check learnings before any task
- Use unified infrastructure components