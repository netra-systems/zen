# MASTER SYSTEM CONTEXT - Netra Apex AI Optimization Platform

## Executive Summary

Netra Apex is an enterprise AI optimization platform that delivers 10-40% cost reduction through intelligent multi-agent analysis. The system is built as a unified, coherent platform with six independent microservices communicating through well-defined APIs.

**Core Business Value:**
- **Target Market:** AI/LLM spending companies ($1K-$100K+/month AI spend)
- **Value Proposition:** 5:1 ROI (save $5 for every $1 spent on Netra)
- **Payback Period:** < 30 days
- **Time to Value:** 24 hours to 7 days depending on tier

## System Architecture Overview

### The Six Core Services

1. **Main Backend (netra_backend)** - Port 8000
   - Core business logic and AI orchestration
   - Multi-agent system coordination
   - WebSocket real-time communication
   - Database: PostgreSQL, Redis, ClickHouse

2. **Auth Service (auth_service)** - Port 8081
   - Centralized authentication/authorization
   - OAuth provider integration
   - JWT token management
   - Database: PostgreSQL (isolated auth_users table)

3. **Frontend (frontend)** - Port 3000
   - Next.js React application
   - Real-time WebSocket UI
   - OAuth flow handling
   - TypeScript with strict typing

4. **Dev Launcher (dev_launcher)**
   - Development environment orchestration
   - IsolatedEnvironment management
   - Service discovery coordination
   - Dynamic port allocation

5. **Shared Infrastructure (shared)**
   - Database connectivity (CoreDatabaseManager)
   - CORS configuration (unified)
   - Common schemas and utilities
   - SSL parameter resolution

6. **Test Framework (test_framework)**
   - Unified test runner
   - Service-specific test organization
   - Real service testing (no mocks in prod)
   - Coverage reporting

### Critical Architectural Principles

#### 1. Single Source of Truth (SSOT)
- **MANDATORY:** Each concept has ONE canonical implementation per service
- **Example:** `/netra_backend/app/db/clickhouse.py` is the ONLY ClickHouse interface
- **Violations:** Immediate technical debt, 4x maintenance burden
- **Enforcement:** Pre-commit hooks, architecture compliance checks

#### 2. Service Independence
- **CRITICAL:** Services MUST be 100% independent
- **No cross-service imports allowed** (auth_service cannot import from netra_backend)
- **Communication only through APIs**
- **Each service maintains its own environment configuration**

#### 3. Unified Environment Management
- **ALL environment access through IsolatedEnvironment**
- **Direct os.environ access FORBIDDEN**
- **Complete isolation in dev/test**
- **Thread-safe with source tracking**

## Critical Business Flows

### 1. User Authentication Flow (OAuth)
```
User → Frontend → Auth Service → OAuth Provider → Auth Service → JWT → Frontend → Backend
```
**Critical Points:**
- OAuth redirect URIs MUST point to auth service, NOT frontend
- JWT_SECRET_KEY (not JWT_SECRET) synchronized across services
- Development mode: Auto-login with exponential backoff
- Token persistence handled by frontend

### 2. AI Optimization Request Flow (Adaptive Workflow)
```
User Request → Triage Agent → Data Sufficiency Check → Workflow Selection:
  - Sufficient: Full pipeline (Triage → Optimization → Data → Actions → Reporting)
  - Partial: Modified pipeline (includes Data Helper)
  - Insufficient: Data Helper only
```
**Key Innovation:** Dynamic workflow based on data availability prevents wasted processing

### 3. WebSocket Real-time Communication
```
Frontend ←→ WebSocket → Backend → Agent System → Progress Updates → Frontend
```
**Critical Requirements:**
- Message routing by run_id (NEVER broadcast to all users)
- Subprotocol negotiation required
- Authentication bypass in development
- CORS handling for Docker networks

### 4. Database Persistence (3-Tier Architecture)
```
Tier 1 (Redis) → Tier 2 (PostgreSQL) → Tier 3 (ClickHouse)
```
**Performance Targets:**
- Redis: < 50ms writes, < 20ms reads
- PostgreSQL: < 500ms checkpoints
- ClickHouse: < 2s batch migrations
- Failover: < 5s total recovery

## Configuration Management

### Environment Detection Hierarchy
1. **Development:** Local databases, no SSL, dynamic ports
2. **Test:** Memory databases, isolated environment
3. **Staging:** Cloud SQL, SSL required, OAuth enabled
4. **Production:** Multi-region, auto-scaling, full monitoring

### Critical Configuration Points
- **Database URLs:** Automatic SSL parameter resolution (ssl= vs sslmode=)
- **Unix Sockets:** Remove ALL SSL parameters for /cloudsql/ connections
- **Service Discovery:** JSON files in development, fixed domains in deployment
- **Secret Management:** GCP Secret Manager in staging/production

## Authentication & Security

### Mandatory Patterns
```python
# EVERY protected route MUST use:
from netra_backend.app.auth_integration.auth import get_current_user

@router.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"user": user.email}
```

### Security Boundaries
- **Service Isolation:** Complete code separation
- **Database Isolation:** Table/schema level separation
- **Redis Namespacing:** Service-specific key prefixes
- **CORS:** Unified configuration, no wildcards with credentials

## Testing Philosophy

### Test Hierarchy (Priority Order)
1. **E2E Tests** - Real services, real databases, real LLMs
2. **Integration Tests** - Component boundaries
3. **Unit Tests** - Isolated functions

### Critical Testing Rules
- **MOCKS FORBIDDEN** in development/staging/production
- **Real services required** for all E2E tests
- **Absolute imports only** (no relative imports)
- **Service boundaries respected** (tests stay within service)

## Deployment Strategy

### Pre-deployment Validation
1. Validate all secrets exist
2. Test database connectivity with SSL resolution
3. Verify no localhost references
4. Check service dependencies
5. Run architecture compliance

### Deployment Commands
```bash
# Staging (fast)
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Production (with checks)
python scripts/deploy_to_gcp.py --project netra-production --run-checks
```

## Common Pitfalls & Critical Learnings

### 1. WebSocket Routing Regression
**CATASTROPHIC:** Broadcasting agent updates to all users (privacy violation)
**Solution:** Always route by run_id, maintain run_id_connections mapping

### 2. OAuth Service Independence Violation
**CATASTROPHIC:** Auth service importing from netra_backend causes complete auth failure
**Solution:** Maintain 100% service independence, no cross-imports

### 3. ClickHouse SSOT Violations
**ISSUE:** Four duplicate implementations (834+ lines duplicate code)
**Solution:** Single canonical implementation at `/netra_backend/app/db/clickhouse.py`

### 4. Database SSL Parameter Conflicts
**ISSUE:** asyncpg uses ssl=, psycopg2 uses sslmode=
**Solution:** CoreDatabaseManager.resolve_ssl_parameter_conflicts()

### 5. Dev Auto-login Dependencies
**ISSUE:** Token initialization requires processing whether storedToken === currentToken
**Solution:** Process tokens regardless, use exponential backoff for backend delays

## Business Metrics & Monitoring

### Key Performance Indicators
- **System Availability:** 99.9% uptime target
- **Response Time:** < 100ms for critical paths
- **Cost Reduction:** 10-40% customer AI spend reduction
- **Time to Value:** < 7 days maximum

### Monitoring Points
- WebSocket connection health
- Agent execution performance
- Database failover events
- OAuth success rates
- API endpoint latencies

## Development Workflow

### Quick Start
```bash
# Docker (Recommended)
docker-compose -f docker-compose.dev.yml up -d

# Local Development
python scripts/dev_launcher.py

# Run Tests
python unified_test_runner.py --level integration --fast-fail

# Check Compliance
python scripts/check_architecture_compliance.py
```

### Critical Development Rules
1. **Read CLAUDE.md first** - Principal engineering philosophy
2. **Check learnings/index.xml** before starting work
3. **Validate string literals** to prevent hallucination
4. **Use TodoWrite** for task tracking
5. **Atomic commits only** - complete, reviewable units

## System Health Status (Current)

### Architecture Compliance
- **Module Size:** 500 lines max
- **Function Size:** 25 lines max
- **Import Compliance:** 48.21% (target 100%)
- **Test Coverage:** 51.4% (target 97%)
- **Service Independence:** 85% (target 100%)

### Known Critical Issues
- Zero coverage on security validators
- 193 cross-service import violations
- 93 duplicate type definitions
- Test discovery issues (only 2 tests collectible)

## Future Considerations

### Scaling Points
- Agent system horizontal scaling
- Database sharding strategy
- CDN integration for frontend
- Multi-region deployment

### Technical Debt Priority
1. Fix import violations (100% compliance)
2. Increase test coverage (97% target)
3. Consolidate duplicate types
4. Implement contract testing

---

**Document Purpose:** This master context provides the essential understanding of how the Netra Apex system operates as a unified whole. It captures the critical relationships, assumptions, business expectations, and key architectural decisions that take significant time to discover through code exploration.

**Last Updated:** 2025-08-30
**Version:** 1.0.0