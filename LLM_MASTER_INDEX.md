# 🤖 LLM MASTER INDEX - Netra Apex Navigation Guide

## 🔴 CRITICAL: Cross-System Navigation

**NEW COMPREHENSIVE INDEXES AVAILABLE:**
- [`SPEC/CROSS_SYSTEM_MASTER_INDEX.md`](SPEC/CROSS_SYSTEM_MASTER_INDEX.md) - Complete cross-system navigation with health metrics
- [`SPEC/SYSTEM_INTEGRATION_MAP.xml`](SPEC/SYSTEM_INTEGRATION_MAP.xml) - Detailed integration points and data flows
- [`SPEC/cross_system_context_reference.md`](SPEC/cross_system_context_reference.md) - Complete system context

**USE THESE FIRST** when searching for functionality or making changes.

---

## 📍 COMMONLY CONFUSED FILES & LOCATIONS

### 🏗️ UNIFIED ARCHITECTURE COMPONENTS (Critical Infrastructure)
| Component | Location | Purpose | Key Specs |
|-----------|----------|---------|-----------|
| **Unified Environment** | `/dev_launcher/isolated_environment.py` | Central environment management | [`SPEC/unified_environment_management.xml`](SPEC/unified_environment_management.xml) |
| **Database Connectivity** | `/shared/database/core_database_manager.py` | SSL resolution & driver compatibility | [`SPEC/database_connectivity_architecture.xml`](SPEC/database_connectivity_architecture.xml) |
| **CORS Configuration** | `/shared/cors_config.py` | **Unified CORS configuration for all services** | [`SPEC/cors_configuration.xml`](SPEC/cors_configuration.xml) |
| **Shared Component Library** | `/shared/` | Universal utilities & schemas | [`SPEC/shared_component_architecture.xml`](SPEC/shared_component_architecture.xml) |
| **Test Infrastructure** | `/test_framework/` | Unified test utilities | [`SPEC/test_infrastructure_architecture.xml`](SPEC/test_infrastructure_architecture.xml) |
| **Import Management** | Various scripts | Absolute imports enforcement | [`SPEC/import_management_architecture.xml`](SPEC/import_management_architecture.xml) |
| **Deployment System** | `/scripts/deploy_to_gcp.py` | Official deployment script | [`SPEC/deployment_architecture.xml`](SPEC/deployment_architecture.xml) |
| **Root Folder Organization** | `/` root directory | Clean root structure enforcement | [`SPEC/root_folder_organization.xml`](SPEC/root_folder_organization.xml) |
| **Intelligent Remediation** | `/scripts/intelligent_remediation_orchestrator.py` | Multi-agent Docker remediation | [`SPEC/intelligent_remediation_architecture.xml`](SPEC/intelligent_remediation_architecture.xml) |
| **Claude Log Analyzer** | `/scripts/claude_log_analyzer.py` | Get logs to Claude for analysis | [`SPEC/intelligent_remediation_architecture.xml`](SPEC/intelligent_remediation_architecture.xml) |

### Configuration Files (Unified System - CRITICAL CHANGE)
| File | Location | Purpose | Common Confusion |
|------|----------|---------|------------------|
| **UNIFIED CONFIG** | `/netra_backend/app/core/configuration/` | **NEW: Single source of truth** | Replaces 110+ duplicate config files |
| `config.py` | `/netra_backend/app/config.py` | Main config interface | Use get_config() for all access |
| `base.py` | `/netra_backend/app/core/configuration/base.py` | Core orchestration | Central configuration manager |
| `database.py` | `/netra_backend/app/core/configuration/database.py` | Database configs | All DB settings unified |
| `services.py` | `/netra_backend/app/core/configuration/services.py` | External services | API endpoints, OAuth, etc |
| `secrets.py` | `/netra_backend/app/core/configuration/secrets.py` | Secret management | GCP Secret Manager integration |
| **🔴 CORS CONFIG** | `/shared/cors_config.py` | **UNIFIED CORS for ALL services** | **CRITICAL: Single source for CORS - consolidated from 5 implementations** |

### Database Files (SSOT Compliant - 2025-08-27)
| File | Location | Purpose | Key Functions |
|------|----------|---------|---------------|
| **🔴 CANONICAL MANAGER** | `/netra_backend/app/db/database_manager.py` | **Single database manager (SSOT)** | DatabaseManager.get_connection_manager() |
| **🔴 CANONICAL CLICKHOUSE** | `/netra_backend/app/db/clickhouse.py` | **Single ClickHouse implementation (SSOT)** | get_clickhouse_client(), ClickHouseService |
| `postgres.py` | `/netra_backend/app/db/postgres.py` | PostgreSQL connection | get_postgres_db() |
| **⚠️ DELETED (SSOT)** | ~~clickhouse_client.py, client_clickhouse.py~~ | **Removed - SSOT violations** | Use canonical clickhouse.py |
| `models_auth.py` | `/netra_backend/app/db/models_auth.py` | Auth database models | User, Team, Session |
| `models_corpus.py` | `/netra_backend/app/db/models_corpus.py` | Corpus database models | CorpusData, CorpusEntry |
| `models_metrics.py` | `/netra_backend/app/db/models_metrics.py` | Metrics database models | MetricsData |
| **🔴 REMOVED (SSOT)** | Multiple locations | **Deleted duplicate managers** | See [`SPEC/learnings/database_manager_ssot_consolidation.xml`](SPEC/learnings/database_manager_ssot_consolidation.xml) |
| **🔴 CLICKHOUSE SSOT** | Remediation complete | **Fixed ClickHouse duplication** | See [`SPEC/learnings/clickhouse_ssot_violation_remediation.xml`](SPEC/learnings/clickhouse_ssot_violation_remediation.xml) |

### Authentication & Security (MANDATORY Shared Auth Integration)
| File | Location | Purpose | Key Components |
|------|----------|---------|----------------|
| **🔴 AUTH INTEGRATION (MANDATORY)** | | | |
| `auth.py` | `/netra_backend/app/auth_integration/auth.py` | **SHARED AUTH SERVICE** | get_current_user(), get_current_user_optional(), validate_token() |
| **OAuth Port Config** | [`SPEC/oauth_port_configuration.xml`](SPEC/oauth_port_configuration.xml) | **OAuth port requirements & setup** | Explains why ports 3000, 8000, 8001, 8081 need authorization |
| **OAuth Environment Config** | [`SPEC/learnings/oauth_client_environment_configuration.xml`](SPEC/learnings/oauth_client_environment_configuration.xml) | Environment-specific OAuth setup | Development, staging, production OAuth isolation |
| **CRITICAL**: ALL authentication throughout ENTIRE system MUST use `/netra_backend/app/auth_integration/`. NO duplicate auth logic allowed. |

### WebSocket Files (Complex Structure) ✅ State Management & Subprotocol Fixed (2025-08-27)
| File | Location | Purpose | Key Functions |
|------|----------|---------|---------------|
| **🔴 CRITICAL FIXES (2025-08-27)** | | | |
| `websocket_state_management.xml` | `/SPEC/learnings/websocket_state_management.xml` | **WebSocket state & subprotocol fix** | ABNORMAL_CLOSURE fix, subprotocol negotiation |
| `test_websocket_state_regression.py` | `/netra_backend/tests/critical/test_websocket_state_regression.py` | **Regression tests for state fix** | State checking, subprotocol validation |
| **🔴 DOCKER CONFIG (CRITICAL)** | | | |
| `websocket_docker_fixes.xml` | `/SPEC/learnings/websocket_docker_fixes.xml` | **Complete Docker fix documentation** | Root causes, solutions, testing |
| `websocket_docker_troubleshooting.md` | `/docs/websocket_docker_troubleshooting.md` | **Docker troubleshooting guide** | Diagnosis, solutions, prevention |
| `test_docker_websocket_fix.py` | `/scripts/test_docker_websocket_fix.py` | **Docker WebSocket validation** | Environment, auth, CORS testing |
| `test_websocket_dev_docker_connection.py` | `/tests/e2e/test_websocket_dev_docker_connection.py` | **E2E Docker WebSocket tests** | Connection, retry, CORS validation |
| **🔴 CORE WEBSOCKET FILES** | | | |
| `websocket.py` | `/netra_backend/app/routes/websocket.py` | **WebSocket endpoints (with subprotocol fix)** | websocket_endpoint() with subprotocol negotiation |
| `websocket_core/auth.py` | `/netra_backend/app/websocket_core/auth.py` | **WebSocket authentication (Docker bypass)** | Development auth bypass, JWT validation |
| `websocket_cors.py` | `/netra_backend/app/core/websocket_cors.py` | **CORS handling (Docker origins)** | Docker service names, bridge network IPs |
| `connection.py` | `/netra_backend/app/websocket/connection.py` | Connection management | ConnectionManager class |
| `quality_message_handler.py` | `/netra_backend/app/services/websocket/quality_message_handler.py` | Message quality handling | QualityMessageHandler |
| `websocket_types.py` | `/netra_backend/app/schemas/websocket_types.py` | WebSocket type definitions | WSMessage, WSResponse |
| `rate_limiter.py` | `/netra_backend/app/websocket/rate_limiter.py` | Rate limiting | RateLimiter class |
| `validation.py` | `/netra_backend/app/websocket/validation.py` | Message validation | validate_message() |

### String Literals Index (Platform Constants)
| File | Location | Purpose | Usage |
|------|----------|---------|-------|
| `string_literals_index.xml` | `/SPEC/string_literals_index.xml` | Master spec for string literals | Defines structure and purpose |
| `string_literals.json` | `/SPEC/generated/string_literals.json` | Generated index of all platform strings | Query for exact values |
| `scan_string_literals.py` | `/scripts/scan_string_literals.py` | Scanner to generate index | Run to update index |
| `query_string_literals.py` | `/scripts/query_string_literals.py` | Query tool for string validation | Use to validate/search literals |

### Agent Files (Multi-Agent System)
| Agent Type | Location | Main File | Purpose |
|------------|----------|-----------|---------|
| **APEX Optimizer Agent** | `/netra_backend/app/services/apex_optimizer_agent/` | Multiple tool files | AI optimization agent system |
| - Cost Analysis Tools | `/netra_backend/app/services/apex_optimizer_agent/tools/` | `cost_*.py` | Cost analysis and optimization |
| - Performance Tools | `/netra_backend/app/services/apex_optimizer_agent/tools/` | `performance_*.py`, `latency_*.py` | Performance optimization |
| - Log Analysis Tools | `/netra_backend/app/services/apex_optimizer_agent/tools/` | `log_*.py` | Log analysis and pattern detection |
| - Optimization Tools | `/netra_backend/app/services/apex_optimizer_agent/tools/` | `optimization_*.py`, `optimal_*.py` | Various optimization strategies |

### Performance Optimization Components (CRITICAL - 2025-08-28)
| Component | Location | Purpose | Key Features |
|-----------|----------|---------|-------------|
| **🔴 EXECUTION ENGINE** | `/netra_backend/app/agents/supervisor/execution_engine.py` | **Parallel pipeline execution** | asyncio.gather() parallelization, automatic fallback to sequential |
| **🔴 CLICKHOUSE ASYNC** | `/netra_backend/app/db/clickhouse_client.py` | **Async-safe database operations** | connect_async(), execute_async(), health_check_async() |
| **🔴 STATE PERSISTENCE** | `/netra_backend/app/services/state_persistence_optimized.py` | **Optimized state management** | Delegation pattern, feature flag controlled |
| **🔴 PIPELINE EXECUTOR** | `/netra_backend/app/agents/supervisor/pipeline_executor.py` | **State batching and optimization** | Feature flag integration, optimized service selection |
| **🔴 FEATURE FLAGS** | `/netra_backend/app/core/isolated_environment.py` | **Performance configuration** | ENABLE_OPTIMIZED_PERSISTENCE, cache size, compression settings |
| **🔴 INTEGRATION TESTS** | `/netra_backend/tests/services/test_optimized_persistence_integration.py` | **Performance optimization testing** | Feature flag testing, delegation pattern validation |
| **Performance Learnings** | [`SPEC/learnings/state_persistence_optimization.xml`](SPEC/learnings/state_persistence_optimization.xml) | **Optimization best practices** | 35-45% performance improvement, async safety patterns |

### Test Files (Unified Testing System)
| Component | Location | Purpose | Documentation |
|-----------|----------|---------|---------------|
| **📖 MAIN TESTING GUIDE** | `/TESTING.md` | **Comprehensive testing documentation** | Start here for all testing |
| **Test Framework** | `/test_framework/` | Enhanced test framework | Core runner and configuration |
| **Test Runner** | `/test_framework/runner.py` | Main test runner | Unified test execution |
| **Test Config** | `/test_framework/test_config.py` | Test configuration | Test levels, environments |

#### Test Locations by Service
| Test Type | Location | Pattern | Run Command |
|-----------|----------|---------|-------------|
| Backend Tests | `/netra_backend/tests/` | `test_*.py` | `python -m test_framework.runner --service backend` |
| Auth Tests | `/auth_service/tests/` | `test_*.py` | `python -m test_framework.runner --service auth` |
| Frontend Tests | `/frontend/__tests__/` | `*.test.tsx` | `python -m test_framework.runner --service frontend` |
| E2E Tests | `/tests/e2e/` | `test_*.py` | `python -m test_framework.runner --level e2e` |

### Google Tag Manager (GTM) Integration
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| **GTM Provider** | `/frontend/providers/GTMProvider.tsx` | Core GTM integration component | ✅ OPERATIONAL |
| **GTM Hooks** | `/frontend/hooks/useGTM.ts` | Event tracking hooks | ✅ Implemented |
| **GTM Spec** | `/SPEC/google_tag_manager.xml` | GTM specification & requirements | ✅ Updated |
| **GTM Learnings** | `/SPEC/learnings/gtm_implementation.xml` | Implementation learnings & fixes | ✅ Documented |
| **GTM Test Script** | `/scripts/test_gtm_loading.py` | Automated GTM verification | ✅ Working |
| **GTM Audit Report** | `/GTM_AUDIT_REPORT.md` | Comprehensive audit documentation | ✅ Complete |
| **Container ID** | `GTM-WKP28PNQ` | Universal container across all envs | ✅ Configured |

#### Critical Security Tests (New Implementation - Cycle 1)
| Test File | Location | Purpose | Protection Value |
|-----------|----------|---------|------------------|
| **🔴 Auth Backend Desynchronization** | `/tests/e2e/test_auth_backend_desynchronization.py` | **P0 CRITICAL** - Cross-service transaction rollback vulnerability | **9.4M Protection** |

#### Critical Startup Tests (New Implementation - Cycle 2)
| Test File | Location | Purpose | Protection Value |
|-----------|----------|---------|------------------|
| **🔴 Configuration Drift Detection** | `/netra_backend/tests/startup/test_configuration_drift_detection.py` | **P0 CRITICAL** - SSL parameter cascade failure detection | **9.4M Protection** |

---

## 🎯 UNIFIED SYSTEM ARCHITECTURE

### Core Architecture Principles
The Netra Apex platform operates as a **unified, coherent system** with three independent microservices that communicate through well-defined APIs.

### Service Architecture
```
┌────────────────────────────────────────────────────────────────────┐
│                     NETRA PLATFORM ARCHITECTURE                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐       │
│  │   Frontend   │────▶│   Backend    │────▶│ Auth Service │       │
│  │  (Next.js)   │◀────│  (FastAPI)   │◀────│  (FastAPI)   │       │
│  │              │     │              │     │              │       │
│  │ Port:Dynamic │     │ Port:Dynamic │     │ Port:Dynamic │       │
│  └──────────────┘     └──────────────┘     └──────────────┘       │
│         │                    │                    │                 │
│         └────────────────────┼────────────────────┘                 │
│                              ▼                                      │
│         ┌────────────────────────────────────────┐                  │
│         │        Shared Infrastructure           │                  │
│         │  PostgreSQL │ Redis │ ClickHouse      │                  │
│         └────────────────────────────────────────┘                  │
└────────────────────────────────────────────────────────────────────┘
```

### Service Details
1. **Main Backend** (`/netra_backend/app/`) - Core business logic, AI orchestration
2. **Auth Service** (`/auth_service/`) - Centralized authentication and authorization
3. **Frontend** (`/frontend/`) - Web application UI

---

## 📈 System Health Status (2025-08-27)

### Recent Critical Fixes
| Date | Issue | Fix | Impact |
|------|-------|-----|--------|
| 2025-08-27 | WebSocket ABNORMAL_CLOSURE (1006) | Fixed state checking & subprotocol negotiation | Chat UI now working |
| 2025-08-27 | WebSocket Docker connectivity | Authentication bypass & CORS for dev | Docker development functional |

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| **Test Coverage** | 51.4% | 97% | 🔴 Critical |
| **Config Compliance** | 89% | 100% | 🟡 High |
| **Import Compliance** | 48.21% | 100% | 🔴 Critical |
| **Service Independence** | 85% | 100% | 🟡 High |

### Critical Issues
- **Zero Coverage**: Security validators, agent systems
- **Import Violations**: 193 cross-service, widespread relative imports
- **Type Duplications**: 93 duplicate definitions
- **Test Discovery**: Only 2 tests collectible

---

## 🚀 Quick Start Commands

### Development
```bash
# Start Development Environment
python scripts/dev_launcher.py

# Run Quick Tests
python unified_test_runner.py --level integration --no-coverage --fast-fail

# Check Compliance
python scripts/check_architecture_compliance.py
```

### Deployment
```bash
# Deploy to Staging (Fast)
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Deploy to Production (With Checks)
python scripts/deploy_to_gcp.py --project netra-production --run-checks
```

### Docker Configuration & Service Management
**IMPORTANT: Two distinct Docker configuration sets exist**
- **Development:** `/docker/*.development.Dockerfile` - Local dev with hot-reload
- **Production/GCP:** `/deployment/docker/*.gcp.Dockerfile` - Optimized for Cloud Run
- **Index:** [`docs/DOCKER_CONFIGURATION_INDEX.md`](docs/DOCKER_CONFIGURATION_INDEX.md) - Complete Docker configuration mapping

#### 🐳 Docker Service Management (Selective Service Control)
- **Service Guide:** [`docs/docker-services-guide.md`](docs/docker-services-guide.md) - Complete guide for selective service management
- **Service Manager:** `/scripts/docker_services.py` - CLI tool for selective service control
- **Docker Launcher:** `/scripts/docker_dev_launcher.py` - Full development environment launcher
- **Docker Compose:** `/docker-compose.dev.yml` - Development compose with profile support

#### Quick Docker Commands
```bash
# Refresh/Restart Netra backend only
python scripts/docker_services.py restart netra

# Start just Netra backend (with dependencies)
python scripts/docker_services.py start netra

# Start everything
python scripts/docker_services.py start full

# View Netra logs
python scripts/docker_services.py logs netra

# Stop all services
python scripts/docker_services.py stop
```

---

## 📚 Essential Documentation

### Primary References
- [`CLAUDE.md`](CLAUDE.md) - AI agent instructions and principles
- [`SPEC/CROSS_SYSTEM_MASTER_INDEX.md`](SPEC/CROSS_SYSTEM_MASTER_INDEX.md) - Complete cross-system navigation
- [`SPEC/SYSTEM_INTEGRATION_MAP.xml`](SPEC/SYSTEM_INTEGRATION_MAP.xml) - Integration points and flows
- [`SPEC/cross_system_context_reference.md`](SPEC/cross_system_context_reference.md) - System context
- [`MASTER_WIP_STATUS.md`](MASTER_WIP_STATUS.md) - Compliance tracking

### Specification Library
- [`SPEC/learnings/index.xml`](SPEC/learnings/index.xml) - Historical learnings
- [`SPEC/core.xml`](SPEC/core.xml) - Core architecture
- [`SPEC/unified_environment_management.xml`](SPEC/unified_environment_management.xml) - Environment management
- [`SPEC/database_connectivity_architecture.xml`](SPEC/database_connectivity_architecture.xml) - Database patterns
- [`SPEC/cors_configuration.xml`](SPEC/cors_configuration.xml) - **UNIFIED CORS architecture (consolidated 5→1)**
- [`SPEC/import_management_architecture.xml`](SPEC/import_management_architecture.xml) - Import rules

### Infrastructure & Deployment Specs
- [`SPEC/unified_staging_configuration.xml`](SPEC/unified_staging_configuration.xml) - **UNIFIED staging config (Redis, LLM, deployment)**
- [`SPEC/gcp_deployment.xml`](SPEC/gcp_deployment.xml) - GCP staging deployment guidelines
- [`SPEC/deployment_architecture.xml`](SPEC/deployment_architecture.xml) - Deployment architecture patterns
- [`SPEC/redis_staging_configuration.xml`](SPEC/redis_staging_configuration.xml) - **Redis endpoint configuration (10.107.0.3)**
- [`SPEC/llm_configuration_architecture.xml`](SPEC/llm_configuration_architecture.xml) - **LLM centralized config (GEMINI_2_5_FLASH default)**

---

## 🎯 Action Items

### Immediate (Week 1)
1. Fix import violations - 100% compliance
2. Address zero-coverage security files - 25% coverage
3. Stabilize test runner - Full discovery

### Short-term (Month 1)
1. Consolidate 93 duplicate types
2. Improve coverage to 75%
3. Complete auth migration

### Long-term (Quarter 1)
1. Achieve 97% coverage
2. Implement contract testing
3. Deploy monitoring dashboards

---

**For complete cross-system navigation and detailed integration maps, refer to:**
- [`SPEC/CROSS_SYSTEM_MASTER_INDEX.md`](SPEC/CROSS_SYSTEM_MASTER_INDEX.md)
- [`SPEC/SYSTEM_INTEGRATION_MAP.xml`](SPEC/SYSTEM_INTEGRATION_MAP.xml)