# Cross-System Context Reference
## Netra Apex AI Optimization Platform - Complete System Context

> **Purpose**: This document provides the EXPLICIT cross-system context for the Netra platform, capturing all implicit assumptions, data flows, integration points, and environment-specific behaviors. This is the central reference point for LLM context windows to understand the complete system architecture.

---

## 1. System Architecture Overview

### 1.1 Platform Identity
- **Product**: Netra Apex AI Optimization Platform
- **Business Model**: Enterprise AI workload optimization with multi-agent architecture
- **Value Proposition**: Reduce AI/LLM costs by 30-50% while improving performance through intelligent orchestration
- **Customer Segments**: Free (conversion focus), Early (feature adoption), Mid (expansion), Enterprise (full platform)

### 1.2 Three-Service Architecture
The platform consists of exactly THREE backend services plus frontend:

```
┌─────────────────────────────────────────────────────────────┐
│                     Netra Platform Architecture              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Frontend   │  │   Backend    │  │ Auth Service │      │
│  │  (Next.js)   │  │  (FastAPI)   │  │  (FastAPI)   │      │
│  │              │  │              │  │              │      │
│  │ Port:Dynamic │  │ Port:Dynamic │  │ Port:Dynamic │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│         ┌──────────────────┴──────────────────┐              │
│         │        Shared Infrastructure        │              │
│         │  (Database, Redis, Configuration)   │              │
│         └──────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

#### Service Details:

**1. Main Backend Service (`/netra_backend/app/`)**
- **Port**: Dynamic (discovered via `.service_discovery/` in dev, environment variables in staging/prod)
- **Purpose**: Core business logic, AI orchestration, agent management
- **Technology**: Python 3.11, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL (primary), ClickHouse (analytics), Redis (cache)
- **Key Components**:
  - Agent orchestration system (supervisor, sub-agents)
  - WebSocket real-time communication
  - Thread and message management
  - LLM integration and optimization
  - Cost tracking and analytics

**2. Auth Service (`/auth_service/`)**
- **Port**: Dynamic (discovered via `.service_discovery/` in dev, environment variables in staging/prod)
- **Purpose**: Centralized authentication and authorization
- **Technology**: Python 3.11, FastAPI, JWT
- **Database**: PostgreSQL (separate auth_users table)
- **Key Features**:
  - OAuth 2.0 integration (Google, GitHub)
  - JWT token generation and validation
  - Dev login endpoint for testing
  - Session management (optional Redis)
  - No user registration (OAuth-first design)

**3. Frontend (`/frontend/`)**
- **Port**: Dynamic (discovered via `.service_discovery/` in dev, no static default assumed)
- **Purpose**: Web application UI
- **Technology**: Next.js 15, React 19, TypeScript, TailwindCSS
- **State Management**: Zustand
- **Key Features**:
  - Real-time chat interface
  - WebSocket integration
  - OAuth flow handling
  - Responsive design
  - Dark mode support

---

## 2. Data Flow Architecture

### 2.1 Authentication Flow
```
User → Frontend → Auth Service → Backend
      ↓           ↓              ↓
   OAuth      JWT Token    Token Validation
   Provider   Generation    & User Context
```

**Detailed OAuth Flow**:
1. User clicks login → Frontend redirects to auth.staging.netrasystems.ai/auth/oauth
2. Auth service redirects to OAuth provider (Google/GitHub)
3. Provider redirects back to auth.staging.netrasystems.ai/auth/callback
4. Auth service creates/updates user, generates JWT
5. Auth service redirects to frontend with token in URL
6. Frontend extracts token, stores in localStorage
7. All API calls include Authorization: Bearer <token>

### 2.2 Real-Time Communication Flow
```
Frontend ←WebSocket→ Backend → Agent System
         ↓                    ↓
    JSON Messages        AI Processing
         ↓                    ↓
    UI Updates          Response Stream
```

**WebSocket Message Protocol**:
- Connection: Established on app load, persistent
- Authentication: Token in query params or headers
- Message Format: JSON only, no raw strings
- Types: chat, status, agent_update, error
- Reconnection: Automatic with exponential backoff

### 2.3 AI Processing Pipeline
```
User Message → Backend → Supervisor Agent → Sub-Agents
                ↓              ↓               ↓
            Validation    Classification    Execution
                ↓              ↓               ↓
            Thread DB      Routing         LLM APIs
                ↓              ↓               ↓
            Response ← Agent Results ← Processing
```

---

## 3. Environment-Specific Configurations

### 3.1 Development Environment
**Launch**: `python scripts/dev_launcher.py`

**Characteristics**:
- **Service Discovery**: Dynamic ports via JSON files in `.service_discovery/`
  - Frontend: Finds available port (search begins at configurable start point)
  - Backend: Finds available port (search begins at configurable start point)
  - Auth Service: Finds available port (search begins at configurable start point)
  - Ports written to `.service_discovery/{service}_config.json`
- **Database**: Local PostgreSQL (port configured in environment variables)
- **Redis**: Local Redis (port configured in environment variables)
- **ClickHouse**: Docker container (port configured in environment variables)
- **Authentication**: Dev login available at /auth/dev/login
- **LLM Mode**: Mock mode available for testing
- **Hot Reload**: All services support hot reload
- **CORS**: Dynamically configured to allow discovered service ports
- **SSL**: Not required
- **Environment Isolation**: Uses IsolatedEnvironment class
- **Secrets**: Loaded from `.env` file

**Critical Assumptions**:
- All services run on same machine
- Ports are dynamically allocated (no hardcoded assumptions)
- Service discovery via `.service_discovery/` directory
- No SSL/TLS requirements
- Mock LLM responses acceptable
- Database migrations run automatically
- Test data seeded on startup

**Dynamic Port Discovery Example**:
```python
# Dev launcher finds available ports
def find_available_port(start_port: int) -> int:
    """Find next available port starting from start_port"""
    import socket
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available ports found starting from {start_port}")

# Service discovery files
# .service_discovery/frontend_config.json
{
    "host": "localhost",
    "port": 3001,  # Dynamically discovered
    "url": "http://localhost:3001"
}

# Services read discovery files at startup
import json
def get_backend_url():
    with open('.service_discovery/backend_config.json') as f:
        config = json.load(f)
    return config['url']  # No hardcoded ports!
```

### 3.2 Staging Environment
**Deploy**: `python scripts/deploy_to_gcp.py --project netra-staging --build-local`

**Infrastructure** (Google Cloud Platform):
- **Project**: netra-staging
- **Region**: us-central1
- **Services**: Cloud Run (auto-scaling)
- **Database**: Cloud SQL PostgreSQL with Unix socket
- **Redis**: Memorystore
- **SSL**: Required for all connections
- **Domains**:
  - Frontend: staging.netrasystems.ai
  - Backend API: api.staging.netrasystems.ai
  - Auth Service: auth.staging.netrasystems.ai

**Critical Configurations**:
- **DATABASE_URL**: Must use Unix socket format: `postgresql://user:pass@/db?host=/cloudsql/project:region:instance`
- **SSL Parameters**: REMOVED for Unix socket connections (handled at socket level)
- **USE_OAUTH_PROXY**: Must be "true" for backend to validate tokens
- **CORS Origins**: Must include all staging domains
- **Gunicorn**: Uses uvicorn workers for async support
- **Traffic Management**: Manual update required after deployment

**Secret Management** (GCP Secret Manager):
- JWT_SECRET_KEY (64+ characters, synchronized)
- #removed-legacy(Unix socket format)
- REDIS_URL
- CLICKHOUSE_HOST (NOT localhost)
- OAUTH_GOOGLE_CLIENT_ID_STAGING (OAuth Google credentials for staging)
- OAUTH_GOOGLE_CLIENT_SECRET_STAGING (OAuth Google secret for staging)
- OAUTH_GITHUB_CLIENT_ID_STAGING (OAuth GitHub credentials for staging)
- OAUTH_GITHUB_CLIENT_SECRET_STAGING (OAuth GitHub secret for staging)

**OAuth Environment Variable Naming Convention**:
- **Runtime Variables (_ENV suffix)**: `OAUTH_GOOGLE_CLIENT_ID_ENV`, `OAUTH_GOOGLE_CLIENT_SECRET_ENV`
  - Used in application code where credentials are loaded from current environment
  - Tests use these to load environment-specific credentials
- **Deployment Variables (_{ENVIRONMENT} suffix)**: `OAUTH_GOOGLE_CLIENT_ID_STAGING`, `OAUTH_GOOGLE_CLIENT_ID_PROD`
  - Used in deployment configs and secret management
  - Allows multiple environment credentials to coexist
- **General OAuth Config (no suffix)**: `OAUTH_HMAC_SECRET`, `OAUTH_STATE_TTL_SECONDS`
  - Non-credential OAuth configuration values
- See: `SPEC/learnings/oauth_environment_naming_convention.xml` for complete details

### 3.3 Production Environment
**Deploy**: `python scripts/deploy_to_gcp.py --project netra-production --run-checks`

**Additional Requirements**:
- Multi-region deployment
- Auto-scaling with traffic management
- Full monitoring and alerting
- Automatic rollback on high error rates
- Certificate pinning
- DDoS protection
- Backup strategies

---

## 4. Critical Integration Points

### 4.1 Service-to-Service Communication

**Backend → Auth Service**:
- **Endpoint**: POST /auth/validate
- **Purpose**: Validate JWT tokens
- **Request**: `{"token": "jwt_token"}`
- **Response**: `{"valid": true, "user_id": "uuid", "permissions": []}`
- **Frequency**: Every authenticated request
- **Caching**: 5-minute TTL in Redis

**Frontend → Backend**:
- **REST API**: /api/* endpoints
- **WebSocket**: /ws for real-time
- **Authentication**: Bearer token in headers
- **Error Handling**: Circuit breaker pattern
- **Retry Logic**: 3 attempts with exponential backoff

### 4.2 Database Connectivity Architecture

**Critical Issue**: Driver Incompatibility
- **Problem**: asyncpg uses `ssl=` while psycopg2 uses `sslmode=`
- **Solution**: CoreDatabaseManager.resolve_ssl_parameter_conflicts()
- **Implementation**:
  ```python
  # For asyncpg connections
  url = url.replace('sslmode=', 'ssl=')
  
  # For Unix sockets - REMOVE all SSL params
  if '/cloudsql/' in url:
      url = re.sub(r'[?&]ssl(mode)?=[^&]*', '', url)
  ```

**Connection Strategies by Environment**:
- **Development**: TCP without SSL
- **Staging**: Unix socket without SSL parameters
- **Production**: Unix socket preferred, TCP+SSL fallback

### 4.3 Configuration Management

**Unified Configuration System**:
- **Single Source**: IsolatedEnvironment class
- **Location**: `dev_launcher/isolated_environment.py`
- **Features**:
  - Complete isolation in dev/test
  - Source tracking for debugging
  - Thread-safe with RLock
  - Subprocess environment management
- **FORBIDDEN**: Direct os.environ access outside unified config

---

## 5. System Boundaries and Constraints

### 5.1 Hard Limits
- **File Size**: 450 lines maximum (tests: 1000 lines)
- **Function Size**: 25 lines maximum
- **Cyclomatic Complexity**: < 10
- **Import Structure**: Absolute imports ONLY (no relative imports)
- **Service Independence**: 100% - no cross-service imports

### 5.2 Architectural Rules
- **Single Source of Truth**: Every concept exists ONCE per service
- **Atomic Operations**: All changes must be complete
- **No Legacy Code**: Delete all old implementations
- **No Localhost in Staging/Prod**: Use proper service discovery
- **WebSocket JSON Only**: No string messages

---

## 6. Common Failure Patterns and Solutions

### 6.1 Staging Deployment Failures
**Symptoms**: Health checks fail, 503 errors
**Root Causes**:
1. SSL parameter conflicts between drivers
2. Missing required secrets
3. Localhost references in configuration
4. Traffic not routed to new revision

**Solution Checklist**:
1. Run `resolve_ssl_parameter_conflicts()` on all DB URLs
2. Verify all secrets in Secret Manager
3. Run EnvironmentConfigurationValidator
4. Execute `gcloud run services update-traffic --to-latest`

### 6.2 WebSocket Connection Issues
**Symptoms**: Connection drops, messages not received
**Root Causes**:
1. Authentication token missing/expired
2. CORS configuration mismatch
3. JSON parsing errors
4. Database session handling in WebSocket

**Solutions**:
- Include token in connection params
- Configure CORS for WebSocket origins
- Validate JSON structure
- Create new DB session per message

### 6.3 Import Errors
**Symptoms**: ModuleNotFoundError, ImportError
**Root Causes**:
1. Relative imports (FORBIDDEN)
2. Missing setup_test_path() in tests
3. Moved modules without updating imports

**Solution**:
- Use absolute imports: `from netra_backend.app.services import ...`
- Add setup_test_path() at test file top
- Run import validation scripts

---

## 7. Testing Infrastructure

### 7.1 Test Levels
- **Unit**: Component isolation (mock external deps)
- **Integration**: Service integration (real databases)
- **E2E**: Full system flow (all services)
- **Agents**: AI agent testing (real LLMs)

### 7.2 Test Commands
```bash
# Quick feedback (default)
python unified_test_runner.py --level integration --no-coverage --fast-fail

# Agent changes
python unified_test_runner.py --level agents --real-llm

# Pre-release with staging
python unified_test_runner.py --level e2e --real-llm --env staging
```

### 7.3 Test Organization
- Backend tests: `/netra_backend/tests/`
- Auth tests: `/auth_service/tests/`
- Frontend tests: Component-level `.test.tsx` files
- E2E tests: `/tests/e2e/`
- Test framework: `/test_framework/`

---

## 8. Deployment Pipeline

### 8.1 Pre-Deployment Checklist
- [ ] Architecture compliance verified
- [ ] String literals indexed
- [ ] Tests passing (integration minimum)
- [ ] Secrets validated in target environment
- [ ] No localhost references
- [ ] Database migrations completed

### 8.2 Deployment Process
1. **Build** (prefer local): `--build-local` flag
2. **Push** to Artifact Registry
3. **Deploy** to Cloud Run
4. **Health Check** validation
5. **Traffic Update**: Manual step required!
6. **Monitor** error rates for rollback

### 8.3 Rollback Strategy
- **Automatic**: Error rate > 10% for 5 minutes
- **Manual**: `gcloud run services update-traffic SERVICE --to-revisions=PREVIOUS=100`

---

## 9. Business Context

### 9.1 Revenue Model
- **Free Tier**: Conversion to paid (primary goal)
- **Early/Mid Tiers**: Usage-based pricing
- **Enterprise**: Custom contracts with SLAs

### 9.2 Value Metrics
- AI cost reduction: 30-50% target
- Processing speed improvement: 2-3x
- Developer time saved: 20 hours/week
- System uptime: 99.9% SLA

### 9.3 Critical Features
- Real-time AI optimization
- Multi-agent orchestration
- Cost tracking and analytics
- WebSocket streaming responses
- OAuth authentication
- Enterprise security

---

## 10. Platform Evolution Status

### 10.1 Current State (2025-08-24)
- **Maturity**: Beta/Early Access
- **Services**: 3 backend + 1 frontend
- **Test Coverage**: 85% functional
- **Deployment**: GCP staging operational
- **Authentication**: OAuth-first implemented
- **Real-time**: WebSocket operational

### 10.2 Recent Major Achievements
- Staging deployment 100% success rate
- 2660+ tests restored and passing
- Environment management unified
- SSL parameter conflicts resolved
- OAuth flow fully operational
- WebSocket architecture consolidated

### 10.3 Known Technical Debt
- Some files exceed 450-line limit
- Circuit breaker needs refinement
- Monitoring system incomplete
- Documentation gaps in agent system
- Performance optimization pending

---

## 11. Quick Reference

### Critical Files and Locations
```
# Configuration
/dev_launcher/isolated_environment.py - Environment management
/netra_backend/app/config.py - Unified configuration
/shared/database/core_database_manager.py - DB connectivity

# Deployment
/scripts/deploy_to_gcp.py - GCP deployment
/scripts/dev_launcher.py - Local development
/unified_test_runner.py - Test execution

# Services
/netra_backend/app/main.py - Backend entry
/auth_service/auth_core/main.py - Auth entry
/frontend/pages/_app.tsx - Frontend entry

# Specifications
/SPEC/core.xml - Core architecture
/SPEC/learnings/index.xml - Historical learnings
/CLAUDE.md - AI agent instructions
```

### Essential Commands
```bash
# Development
python scripts/dev_launcher.py

# Testing
python unified_test_runner.py --level integration --fast-fail

# Deployment
python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks

# Compliance
python scripts/check_architecture_compliance.py
```

### Service URLs by Environment
| Service | Development | Staging | Production |
|---------|------------|---------|------------|
| Frontend | http://localhost:{dynamic_port} | https://staging.netrasystems.ai | https://app.netrasystems.ai |
| Backend | http://localhost:{dynamic_port} | https://api.staging.netrasystems.ai | https://api.netrasystems.ai |
| Auth | http://localhost:{dynamic_port} | https://auth.staging.netrasystems.ai | https://auth.netrasystems.ai |

**Note**: In development, ports are dynamically discovered at startup. Check `.service_discovery/` directory for actual ports.

---

## 12. Meta-Information

**Document Status**: Living document, updated with each major system change
**Last Updated**: 2025-08-24
**Version**: 1.0
**Maintainer**: Principal Engineering Team
**Review Cycle**: Weekly during active development

**Related Documents**:
- [`SPEC/core.xml`](../core.xml) - Core system architecture
- [`SPEC/deployment_architecture.xml`](../deployment_architecture.xml) - Deployment details
- [`SPEC/database_connectivity_architecture.xml`](../database_connectivity_architecture.xml) - Database patterns
- [`SPEC/unified_environment_management.xml`](../unified_environment_management.xml) - Environment config
- [`SPEC/learnings/index.xml`](../learnings/index.xml) - Historical learnings
- [`CLAUDE.md`](../../CLAUDE.md) - AI agent instructions
- [`LLM_MASTER_INDEX.md`](../../LLM_MASTER_INDEX.md) - File navigation index

---

**END OF CROSS-SYSTEM CONTEXT REFERENCE**