# 🤖 LLM MASTER INDEX - Netra Apex Navigation Guide
**Last Updated: 2025-09-02**

## 🔴 CRITICAL: Cross-System Navigation

**PRIMARY NAVIGATION INDEXES:**
- [`SPEC/CROSS_SYSTEM_MASTER_INDEX.md`](SPEC/CROSS_SYSTEM_MASTER_INDEX.md) - Complete cross-system navigation with health metrics
- [`SPEC/SYSTEM_INTEGRATION_MAP.xml`](SPEC/SYSTEM_INTEGRATION_MAP.xml) - Detailed integration points and data flows
- [`SPEC/cross_system_context_reference.md`](SPEC/cross_system_context_reference.md) - Complete system context
- **[`reports/archived/USER_CONTEXT_ARCHITECTURE.md`](reports/archived/USER_CONTEXT_ARCHITECTURE.md) - ⭐ CRITICAL: Authoritative Factory-based isolation guide**
- [`MASTER_WIP_STATUS.md`](MASTER_WIP_STATUS.md) - Real-time system health and compliance
- **[`DEFINITION_OF_DONE_CHECKLIST.md`](DEFINITION_OF_DONE_CHECKLIST.md) - MANDATORY checklist for ALL module changes**

**USE THESE FIRST** when searching for functionality or making changes.

---

## 🗺️ QUICK NAVIGATION MAP

### By Task Type
| Task | Go To | Key Files |
|------|-------|-----------|
| **Review changes** | [`DEFINITION_OF_DONE_CHECKLIST.md`](DEFINITION_OF_DONE_CHECKLIST.md) | Module-specific checklists |
| **Fix a bug** | [`SPEC/learnings/index.xml`](SPEC/learnings/index.xml) | Check learnings first |
| **Add new feature** | [`SPEC/core.xml`](SPEC/core.xml) | Architecture patterns |
| **Agent implementation** | [`docs/GOLDEN_AGENT_INDEX.md`](docs/GOLDEN_AGENT_INDEX.md) | **Complete agent patterns & migration** |
| **Fix tests** | [`SPEC/test_infrastructure_ssot.xml`](SPEC/test_infrastructure_ssot.xml) | **SSOT test infrastructure (94.5% compliance)** |
| **Deploy changes** | [`scripts/deploy_to_gcp.py`](scripts/deploy_to_gcp.py) | Official deploy script |
| **Check compliance** | [`scripts/check_architecture_compliance.py`](scripts/check_architecture_compliance.py) | Architecture validator |
| **WebSocket issues** | [`SPEC/learnings/websocket_agent_integration_critical.xml`](SPEC/learnings/websocket_agent_integration_critical.xml) | Critical fixes |
| **Auth problems** | [`SPEC/learnings/auth_race_conditions_critical.xml`](SPEC/learnings/auth_race_conditions_critical.xml) | Auth learnings |
| **Auth SSOT** | [`reports/auth/BACKEND_AUTH_SSOT_AUDIT_20250107.md`](reports/auth/BACKEND_AUTH_SSOT_AUDIT_20250107.md) | JWT SSOT violations audit |
| **Database issues** | [`SPEC/database_connectivity_architecture.xml`](SPEC/database_connectivity_architecture.xml) | DB patterns |
| **Telemetry/Tracing** | [`SPEC/learnings/opentelemetry_otlp_implementation.xml`](SPEC/learnings/opentelemetry_otlp_implementation.xml) | OpenTelemetry implementation |

### By Service
| Service | Main Entry | Config | Tests |
|---------|------------|--------|-------|
| **Backend** | `/netra_backend/app/main.py` | `/netra_backend/app/config.py` | `/netra_backend/tests/` |
| **Auth** | `/auth_service/main.py` | `/auth_service/config.py` | `/auth_service/tests/` |
| **Frontend** | `/frontend/pages/_app.tsx` | `/frontend/.env.*` | `/frontend/__tests__/` |

---

## 🔴 MISSION CRITICAL TEST SUITES

### Core Validation (Run Before Any Deployment)
```bash
# Essential system health checks
python tests/mission_critical/test_websocket_agent_events_suite.py        # WebSocket chat delivery
python tests/mission_critical/test_no_ssot_violations.py                  # SSOT compliance
python tests/mission_critical/test_orchestration_integration.py           # Docker orchestration
python scripts/check_auth_ssot_compliance.py                              # Auth SSOT enforcement
python tests/mission_critical/test_docker_stability_suite.py             # Docker stability
```

### Agent Compliance
```bash
# Agent golden pattern validation  
python tests/mission_critical/test_supervisor_golden_compliance_quick.py  # Supervisor pattern
python tests/mission_critical/test_data_sub_agent_golden_ssot.py         # DataSubAgent SSOT
python tests/mission_critical/test_reporting_agent_golden.py             # Reporting agent
python tests/mission_critical/test_agent_resilience_patterns.py          # Resilience patterns
```

### Infrastructure Stability  
```bash
# Critical infrastructure tests
python tests/mission_critical/test_docker_force_flag_prohibition.py      # Docker safety
python tests/mission_critical/test_isolated_environment_compliance.py    # Environment isolation
python tests/mission_critical/test_websocket_bridge_lifecycle_audit_20250902.py  # WebSocket lifecycle
python tests/mission_critical/test_deterministic_startup_validation.py   # Startup sequence
```

---

## 📍 COMMONLY CONFUSED FILES & LOCATIONS

## 🚨 RECENT CRITICAL UPDATES (2025-09-02)

### Infrastructure Changes
| Component | Update | Impact |
|-----------|---------|--------|
| **Resource Monitoring** | Enhanced memory limits and integration | Docker stability improvements |
| **Environment Locking** | Thread-safe environment management | Prevents concurrent test conflicts |
| **Docker Stability** | Comprehensive stability suite with rate limiting | Prevents Docker daemon crashes |
| **SSOT Consolidation** | Unified enums and eliminated duplication | 98%+ compliance achieved |
| **WebSocket Silent Failure Prevention** | Comprehensive monitoring system | 100% silent failure detection |
| **WebSocket Health Monitoring** | Runtime event flow monitoring | Chat reliability improvements |
| **VPC Connector** | Added for GCP Cloud Run | Enables Redis/Cloud SQL connectivity |
| **Agent Orchestration** | New E2E testing framework | Background agent testing support |
| **Staging Config** | Unified staging URLs | Single source of truth for staging |
| **Startup Sequence** | Deterministic initialization | Critical chat service reliability |
| **OpenTelemetry** | Comprehensive distributed tracing | OTLP/Jaeger export with safe opt-in design |

### New Files & Locations
| File | Purpose | Reference |
|------|---------|----------|
| `/test_framework/resource_monitor.py` | Resource usage monitoring and limits | [`test_framework/RESOURCE_MONITOR_DOCUMENTATION.md`](test_framework/RESOURCE_MONITOR_DOCUMENTATION.md) |
| `/test_framework/environment_lock.py` | Thread-safe environment locking | Prevents test conflicts |
| `/test_framework/docker_rate_limiter.py` | Docker API rate limiting | Prevents daemon overload |
| `/test_framework/docker_force_flag_guardian.py` | Prevents dangerous force flags | Docker stability |
| `/netra_backend/app/websocket_core/event_monitor.py` | WebSocket event flow monitoring | [`WEBSOCKET_SILENT_FAILURE_FIXES.md`](WEBSOCKET_SILENT_FAILURE_FIXES.md) |
| `/netra_backend/app/websocket_core/heartbeat_manager.py` | Connection health tracking | [`SPEC/learnings/websocket_silent_failure_prevention_masterclass.xml`](SPEC/learnings/websocket_silent_failure_prevention_masterclass.xml) |
| `/netra_backend/tests/integration/critical_paths/test_websocket_silent_failures.py` | Silent failure prevention tests | 12 comprehensive test cases |
| `/terraform-gcp-staging/vpc-connector.tf` | VPC connector config | [`SPEC/learnings/redis_vpc_connector_requirement.xml`](SPEC/learnings/redis_vpc_connector_requirement.xml) |
| `/tests/e2e/agent_orchestration_fixtures.py` | Agent testing fixtures | E2E agent orchestration |
| `/tests/e2e/helpers/agent/agent_orchestration_runner.py` | Agent test runner | Background agent execution |
| `/netra_backend/app/core/telemetry.py` | OpenTelemetry manager with OTLP export | [`SPEC/learnings/opentelemetry_otlp_implementation.xml`](SPEC/learnings/opentelemetry_otlp_implementation.xml) |
| `/netra_backend/app/core/telemetry_config.py` | Telemetry configuration management | Environment-based OTLP/Jaeger config |
| `/netra_backend/app/middleware/telemetry_middleware.py` | Request tracing middleware | Automatic span creation for HTTP |
| `/netra_backend/tests/core/test_telemetry.py` | Telemetry comprehensive tests | Full coverage for tracing implementation |
| **`/netra_backend/app/services/monitoring/gcp_error_reporter.py`** | **GCP Error Reporting singleton** | **[`docs/GCP_ERROR_REPORTING_ARCHITECTURE.md`](docs/GCP_ERROR_REPORTING_ARCHITECTURE.md)** |
| **`/netra_backend/app/routes/test_gcp_errors.py`** | **GCP error test endpoints** | **Test error reporting in staging** |

---

### 🏗️ UNIFIED ARCHITECTURE COMPONENTS (Critical Infrastructure)
| Component | Location | Purpose | Key Specs |
|-----------|----------|---------|-----------|
| **Unified Environment** | `/dev_launcher/isolated_environment.py` | Central environment management | [`SPEC/unified_environment_management.xml`](SPEC/unified_environment_management.xml) |
| **OpenTelemetry** | `/netra_backend/app/core/telemetry.py` | Distributed tracing with OTLP export | [`SPEC/learnings/opentelemetry_otlp_implementation.xml`](SPEC/learnings/opentelemetry_otlp_implementation.xml) |
| **Database Connectivity** | `/shared/database/core_database_manager.py` | SSL resolution & driver compatibility | [`SPEC/database_connectivity_architecture.xml`](SPEC/database_connectivity_architecture.xml) |
| **CORS Configuration** | `/shared/cors_config.py` | **Unified CORS configuration for all services** | [`SPEC/cors_configuration.xml`](SPEC/cors_configuration.xml) |
| **Shared Component Library** | `/shared/` | Universal utilities & schemas | [`SPEC/shared_component_architecture.xml`](SPEC/shared_component_architecture.xml) |
| **Test Infrastructure** | `/test_framework/` | Unified test utilities with resource monitoring | [`SPEC/test_infrastructure_architecture.xml`](SPEC/test_infrastructure_architecture.xml) |
| **Test Runner Real Services** | `/test_framework/service_availability.py` | Real service validation | [`SPEC/test_runner_real_services.xml`](SPEC/test_runner_real_services.xml) |
| **Test Execution Tracker** | `/scripts/test_execution_tracker.py` | Test history & metrics tracking | [`SPEC/learnings/test_system_improvements.xml`](SPEC/learnings/test_system_improvements.xml) |
| **Test Dashboard** | `/scripts/test_dashboard.py` | Interactive test health monitoring | [`SPEC/learnings/test_system_improvements.xml`](SPEC/learnings/test_system_improvements.xml) |
| **Docker Manual Control** | `/scripts/docker_manual.py` | Manual Docker operations using UnifiedDockerManager | [`docs/docker_orchestration.md`](docs/docker_orchestration.md) |
| **Test Collection Auditor** | `/scripts/test_collection_audit.py` | Test collection health analysis | [`SPEC/learnings/test_collection_optimization.xml`](SPEC/learnings/test_collection_optimization.xml) |
| **Import Management** | Various scripts | Absolute imports enforcement | [`SPEC/import_management_architecture.xml`](SPEC/import_management_architecture.xml) |
| **Deployment System** | `/scripts/deploy_to_gcp.py` | Official deployment script | [`SPEC/deployment_architecture.xml`](SPEC/deployment_architecture.xml) |
| **Root Folder Organization** | `/` root directory | Clean root structure enforcement | [`SPEC/root_folder_organization.xml`](SPEC/root_folder_organization.xml) |
| **Intelligent Remediation** | `/scripts/intelligent_remediation_orchestrator.py` | Multi-agent Docker remediation | [`SPEC/intelligent_remediation_architecture.xml`](SPEC/intelligent_remediation_architecture.xml) |
| **Claude Log Analyzer** | `/scripts/claude_log_analyzer.py` | Get logs to Claude for analysis | [`SPEC/intelligent_remediation_architecture.xml`](SPEC/intelligent_remediation_architecture.xml) |
| **🔴 Docker Hot Reload** | `/docker-compose.override.yml` | **10x faster development** | [`SPEC/docker_hot_reload.xml`](SPEC/docker_hot_reload.xml) |
| **🔴 Adaptive Workflow** | `/netra_backend/app/agents/supervisor/workflow_orchestrator.py` | **Dynamic workflow based on data sufficiency** | [`SPEC/supervisor_adaptive_workflow.xml`](SPEC/supervisor_adaptive_workflow.xml) |
| **🔴 Test Criticality Analysis** | `/docs/TEST_CRITICALITY_ANALYSIS.md` | **Top 100 critical tests protecting $10M+ revenue** | [`SPEC/learnings/test_criticality_analysis.xml`](SPEC/learnings/test_criticality_analysis.xml) |
| **🔴 VPC Connector** | `/terraform-gcp-staging/vpc-connector.tf` | **Required for Cloud Run Redis/SQL access** | [`SPEC/learnings/redis_vpc_connector_requirement.xml`](SPEC/learnings/redis_vpc_connector_requirement.xml) |

### Configuration Files (Unified System - CRITICAL CHANGE)
| File | Location | Purpose | Common Confusion |
|------|----------|---------|------------------|
| **UNIFIED CONFIG** | `/netra_backend/app/core/configuration/` | **NEW: Single source of truth** | Replaces 110+ duplicate config files |
| `config.py` | `/netra_backend/app/config.py` | Main config interface | Use get_config() for all access |
| `base.py` | `/netra_backend/app/core/configuration/base.py` | Core orchestration | Central configuration manager |
| `database.py` | `/netra_backend/app/core/configuration/database.py` | Database configs | All DB settings unified |
| `services.py` | `/netra_backend/app/core/configuration/services.py` | External services | API endpoints, OAuth, etc |
| `secrets.py` | `/netra_backend/app/core/configuration/secrets.py` | Secret management | GCP Secret Manager integration |
| **🔴 JWT CONFIG STANDARD** | `/SPEC/jwt_configuration_standard.xml` | **JWT_SECRET_KEY configuration** | **CRITICAL: Use JWT_SECRET_KEY only - JWT_SECRET is deprecated** |
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
| **🔴 AUTH INITIALIZATION FIX** | | **CRITICAL CHAT FIX** | |
| `auth/context.tsx` | `/frontend/auth/context.tsx` | **Fixed race condition** | Lines 237-274: Unconditional token decode |
| `auth-validation.ts` | `/frontend/lib/auth-validation.ts` | **Auth state validation** | validateAuthState(), monitorAuthState() |
| `AuthGuard.tsx` | `/frontend/components/AuthGuard.tsx` | **Route protection** | Proper user state checking |
| **Auth Race Conditions** | [`SPEC/learnings/auth_race_conditions_critical.xml`](SPEC/learnings/auth_race_conditions_critical.xml) | **Critical auth learnings** | CHAT IS KING - 90% value delivery |
| **Auth Complete Learnings** | [`SPEC/learnings/auth_initialization_complete_learnings.md`](SPEC/learnings/auth_initialization_complete_learnings.md) | **Full cross-references** | All auth fixes documented |
| **OAuth Port Config** | [`SPEC/oauth_port_configuration.xml`](SPEC/oauth_port_configuration.xml) | **OAuth port requirements & setup** | Explains why ports 3000, 8000, 8001, 8081 need authorization |
| **OAuth Environment Config** | [`SPEC/learnings/oauth_client_environment_configuration.xml`](SPEC/learnings/oauth_client_environment_configuration.xml) | Environment-specific OAuth setup | Development, staging, production OAuth isolation |
| **CRITICAL**: ALL authentication throughout ENTIRE system MUST use `/netra_backend/app/auth_integration/`. NO duplicate auth logic allowed. |
| **CRITICAL**: Frontend auth MUST always decode tokens to set user state. Test page refresh scenarios! |

### WebSocket Files (Complex Structure) ✅ State Management & Agent Integration Fixed (2025-08-31) + Silent Failure Prevention (2025-09-01)
| File | Location | Purpose | Key Functions |
|------|----------|---------|---------------|
| **🔴 CRITICAL FIXES (2025-08-27)** | | | |
| `websocket_state_management.xml` | `/SPEC/learnings/websocket_state_management.xml` | **WebSocket state & subprotocol fix** | ABNORMAL_CLOSURE fix, subprotocol negotiation |
| `test_websocket_state_regression.py` | `/netra_backend/tests/critical/test_websocket_state_regression.py` | **Regression tests for state fix** | State checking, subprotocol validation |
| **🔴 SILENT FAILURE PREVENTION (2025-09-01)** | | | |
| `websocket_silent_failure_prevention_masterclass.xml` | `/SPEC/learnings/websocket_silent_failure_prevention_masterclass.xml` | **Comprehensive silent failure prevention guide** | Complete prevention strategies, monitoring patterns |
| `websocket_silent_failures.xml` | `/SPEC/learnings/websocket_silent_failures.xml` | **Silent failure detection and mitigation** | Failure modes, detection methods, fixes |
| `WEBSOCKET_SILENT_FAILURE_FIXES.md` | `/WEBSOCKET_SILENT_FAILURE_FIXES.md` | **Implementation report for fixes** | 5 critical failure points addressed |
| **🔴 DOCKER CONFIG (CRITICAL)** | | | |
| `websocket_docker_fixes.xml` | `/SPEC/learnings/websocket_docker_fixes.xml` | **Complete Docker fix documentation** | Root causes, solutions, testing |
| `websocket_docker_troubleshooting.md` | `/docs/websocket_docker_troubleshooting.md` | **Docker troubleshooting guide** | Diagnosis, solutions, prevention |
| `test_docker_websocket_fix.py` | `/scripts/test_docker_websocket_fix.py` | **Docker WebSocket validation** | Environment, auth, CORS testing |
| `test_websocket_dev_docker_connection.py` | `/tests/e2e/test_websocket_dev_docker_connection.py` | **E2E Docker WebSocket tests** | Connection, retry, CORS validation |
| **🔴 RUN_ID HANDLING FIX (2025-08-29)** | | | |
| `websocket_run_id_issue.xml` | `/SPEC/learnings/websocket_run_id_issue.xml` | **Run ID vs User ID fix** | Proper message routing, logging levels |
| `websocket-messaging-guide.md` | `/docs/websocket-messaging-guide.md` | **WebSocket messaging best practices** | ID types, routing, troubleshooting |
| `test_websocket_run_id_handling.py` | `/netra_backend/tests/unit/test_websocket_run_id_handling.py` | **Unit tests for run_id handling** | ID detection, logging verification |
| `test_agent_websocket_communication.py` | `/netra_backend/tests/integration/test_agent_websocket_communication.py` | **Integration tests for agent WebSocket** | Context routing, error handling |
| **🔴 CORE WEBSOCKET FILES** | | | |
| `websocket.py` | `/netra_backend/app/routes/websocket.py` | **WebSocket endpoints (with subprotocol fix)** | websocket_endpoint() with subprotocol negotiation |
| `manager.py` | `/netra_backend/app/websocket_core/manager.py` | **WebSocket manager (with run_id fix)** | send_to_user(), send_to_thread() with proper ID handling |
| `websocket_core/auth.py` | `/netra_backend/app/websocket_core/auth.py` | **WebSocket authentication (Docker bypass)** | Development OAUTH SIMULATION, JWT validation |
| **🔴 MONITORING & HEALTH (NEW 2025-09-01)** | | | |
| `event_monitor.py` | `/netra_backend/app/websocket_core/event_monitor.py` | **Runtime event flow monitoring** | ChatEventMonitor, silent failure detection |
| `heartbeat_manager.py` | `/netra_backend/app/websocket_core/heartbeat_manager.py` | **Connection health tracking** | Ping/pong health checks, zombie detection |
| `test_websocket_silent_failures.py` | `/netra_backend/tests/integration/critical_paths/test_websocket_silent_failures.py` | **Silent failure prevention tests** | 12 comprehensive test cases |
| `test_websocket_heartbeat_monitoring.py` | `/netra_backend/tests/integration/critical_paths/test_websocket_heartbeat_monitoring.py` | **Heartbeat system tests** | Connection health validation |
| **🔴 AGENT INTEGRATION** | | | |
| `websocket_agent_integration_critical.xml` | `/SPEC/learnings/websocket_agent_integration_critical.xml` | **Critical agent-WebSocket integration** | MUST send events or chat breaks |
| `test_websocket_agent_events_suite.py` | `/tests/mission_critical/test_websocket_agent_events_suite.py` | **Mission critical WebSocket tests** | Validates all required events |
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

### Agent Files (Multi-Agent System) - UPDATED 2025-08-29
| Agent Type | Location | Main File | Purpose |
|------------|----------|-----------|---------|
| **🔴 Supervisor Agent** | `/netra_backend/app/agents/` | `supervisor_agent_modern.py` | **Central orchestrator with adaptive workflow based on data sufficiency** |
| **🔴 Data Helper Agent** | `/netra_backend/app/agents/` | `data_helper_agent.py` | **NEW: Data requirement analysis for insufficient data scenarios** |
| **Agent System Prompts** | `/netra_backend/app/agents/prompts/` | `supervisor_prompts.py`, `*_prompts.py` | **System prompts integrated into all agent templates** |
| **Workflow Orchestrator** | `/netra_backend/app/agents/supervisor/` | `workflow_orchestrator.py` | **Adaptive workflow: sufficient → full, partial → with data_helper, insufficient → data_helper only** |
| **Data Helper Tool** | `/netra_backend/app/tools/` | `data_helper.py` | **Generates comprehensive data request prompts** |
| **Triage Agent** | `/netra_backend/app/agents/` | `triage_agent.py` | **Enhanced with data_sufficiency assessment** |
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
| **🔴 3-TIER PERSISTENCE** | [`docs/3tier_persistence_architecture.md`](docs/3tier_persistence_architecture.md) | **Enterprise persistence architecture** | Redis → PostgreSQL → ClickHouse failover chain |
| **🔴 PIPELINE EXECUTOR** | `/netra_backend/app/agents/supervisor/pipeline_executor.py` | **State batching and optimization** | Feature flag integration, optimized service selection |
| **🔴 FEATURE FLAGS** | `/netra_backend/app/core/isolated_environment.py` | **Performance configuration** | ENABLE_OPTIMIZED_PERSISTENCE, cache size, compression settings |
| **🔴 INTEGRATION TESTS** | `/netra_backend/tests/services/test_optimized_persistence_integration.py` | **Performance optimization testing** | Feature flag testing, delegation pattern validation |
| **3-Tier Integration Tests** | `/tests/integration/test_3tier_persistence_integration.py` | **3-tier persistence validation** | Failover chain, consistency, 24-hour lifecycle |
| **Performance Learnings** | [`SPEC/learnings/state_persistence_optimization.xml`](SPEC/learnings/state_persistence_optimization.xml) | **Optimization best practices** | 35-45% performance improvement, async safety patterns |
| **Persistence Documentation** | [`docs/optimized_state_persistence.md`](docs/optimized_state_persistence.md) | **Optimization feature guide** | Configuration, monitoring, troubleshooting |

### Go to Symbol & Code Navigation (NEW - 2025-08-28)
| Component | Location | Purpose | Key Features |
|-----------|----------|---------|-------------|
| **🔴 SYMBOL EXTRACTOR** | `/netra_backend/app/services/corpus/symbol_extractor.py` | **Core symbol extraction engine** | Python AST parsing, JavaScript/TypeScript regex extraction, 8 symbol types |
| **🔴 SEARCH OPERATIONS** | `/netra_backend/app/services/corpus/search_operations.py` | **Symbol search and ranking** | Relevance scoring, document symbol extraction, corpus integration |
| **🔴 API ENDPOINTS** | `/netra_backend/app/routes/corpus.py` (lines 285-400) | **RESTful symbol search** | GET/POST symbol search, document symbol extraction, type filtering |
| **🔴 COMPREHENSIVE TESTS** | `/netra_backend/tests/services/test_symbol_extractor.py` | **Symbol extraction testing** | Multi-language support, nested structures, error handling |
| **Symbol Types Supported** | All extractors | **Language-specific symbols** | Python: class/function/method/variable, JS/TS: interface/type/enum/const, Arrow functions |
| **Business Value** | Enterprise/Mid segments | **Development velocity** | 60-80% reduction in context switching, IDE-like navigation |

### Test Files (SSOT UNIFIED TESTING SYSTEM - CRITICAL MISSION COMPLETE) ✅
| Component | Location | Purpose | Documentation |
|-----------|----------|---------|---------------|
| **🎯 SSOT COMPLIANCE: 94.5/100** | | **ALL P0 VIOLATIONS RESOLVED** | |
| **📖 MAIN TESTING GUIDE** | `/TESTING.md` | **Comprehensive testing documentation** | Start here for all testing |
| **🔴 SSOT TEST RUNNER** | `/tests/unified_test_runner.py` | **SINGLE SOURCE OF TRUTH for test execution** | [`SPEC/test_infrastructure_ssot.xml`](SPEC/test_infrastructure_ssot.xml) |
| **🔴 SSOT BASE TEST CASE** | `/test_framework/ssot/base_test_case.py` | **CANONICAL BaseTestCase - ALL tests inherit from this** | Eliminated 6,096+ duplicate implementations |
| **🔴 SSOT MOCK FACTORY** | `/test_framework/ssot/mock_factory.py` | **SINGLE mock generator - NO duplicate mocks allowed** | Eliminated 20+ MockAgent implementations |
| **🔴 SSOT DATABASE UTILITY** | `/test_framework/ssot/database_test_utility.py` | **UNIFIED database testing** | Transaction isolation, real DB integration |
| **🔴 SSOT WEBSOCKET UTILITY** | `/test_framework/ssot/websocket_test_utility.py` | **UNIFIED WebSocket testing** | Event validation, connection management |
| **🔴 SSOT DOCKER UTILITY** | `/test_framework/ssot/docker_test_utility.py` | **UNIFIED Docker orchestration** | [`test_framework/unified_docker_manager.py`](test_framework/unified_docker_manager.py) |
| **🔴 UNIFIED DOCKER MANAGER** | `/test_framework/unified_docker_manager.py` | **ONLY Docker manager allowed** | Automatic conflict resolution, health monitoring |
| **🔴 SSOT COMPLIANCE TESTS** | `/tests/mission_critical/test_ssot_compliance_suite.py` | **Validates SSOT violations** | Continuous compliance monitoring |
| **🔴 MOCK POLICY ENFORCEMENT** | `/tests/mission_critical/test_mock_policy_violations.py` | **Enforces MOCKS ARE FORBIDDEN policy** | Integration/E2E must use real services |
| **🔴 SSOT FRAMEWORK TESTS** | `/test_framework/tests/test_ssot_framework.py` | **Tests SSOT infrastructure itself** | Validates BaseTestCase, MockFactory, etc. |
| **Test Discovery** | `/test_framework/test_discovery.py` | Test discovery and analysis | Coverage gaps, untested modules |
| **Service Availability** | `/test_framework/service_availability.py` | Service availability checker | Hard failures when real services unavailable |
| **LLM Config Manager** | `/test_framework/llm_config_manager.py` | Single source of truth for LLM config | Replaces multiple duplicate systems |
| **PyTest Config** | `/pyproject.toml` | Optimized pytest configuration | Collection optimization, markers |
| **🔴 SSOT ARCHITECTURE SPEC** | [`SPEC/test_infrastructure_ssot.xml`](SPEC/test_infrastructure_ssot.xml) | **Complete SSOT architecture documentation** | Canonical test infrastructure patterns |
| **🔴 SSOT VIOLATIONS RESOLVED** | [`TEST_INFRASTRUCTURE_SSOT_VIOLATIONS_REPORT.md`](TEST_INFRASTRUCTURE_SSOT_VIOLATIONS_REPORT.md) | **Resolution of ALL critical violations** | 94.5/100 compliance achieved |
| **🔴 SSOT COMPLIANCE REPORT** | [`TEST_INFRASTRUCTURE_COMPLIANCE_REPORT_FINAL.md`](TEST_INFRASTRUCTURE_COMPLIANCE_REPORT_FINAL.md) | **Final status: MISSION COMPLETE** | Comprehensive compliance metrics |
| **🔴 SSOT MIGRATION GUIDE** | [`SSOT_MIGRATION_GUIDE.md`](SSOT_MIGRATION_GUIDE.md) | **Developer migration instructions** | Complete patterns and examples |

#### Test Locations by Service
| Test Type | Location | Pattern | Run Command |
|-----------|----------|---------|-------------|
| Backend Tests | `/netra_backend/tests/` | `test_*.py` | `python -m test_framework.runner --service backend` |
| Auth Tests | `/auth_service/tests/` | `test_*.py` | `python -m test_framework.runner --service auth` |
| Frontend Tests | `/frontend/__tests__/` | `*.test.tsx` | `python -m test_framework.runner --service frontend` |
| E2E Tests | `/tests/e2e/` | `test_*.py` | `python -m test_framework.runner --level e2e` |

### Docker Infrastructure Management (NEW - 2025-09-01)
| Component | Location | Purpose | Key Features |
|-----------|----------|---------|-------------|
| **🔴 CENTRALIZED MANAGER** | `/test_framework/centralized_docker_manager.py` | **Primary Docker coordination system** | Rate limiting, locking, restart storm prevention |
| **🔴 COMPOSE MANAGER** | `/test_framework/docker_compose_manager.py` | **Docker Compose lifecycle** | Service health checks, port discovery, validation |
| **🔴 PARALLEL TEST SUPPORT** | UnifiedDockerManager | **10+ parallel test runners** | File-based locking, shared/dedicated environments |
| **🔴 MEMORY OPTIMIZATION** | Service memory limits | **50% memory reduction** | 6GB → 3GB total, production image support |
| **Unified Test Integration** | `/tests/unified_test_runner.py` | **Integrated Docker management** | --docker-production, --docker-dedicated flags |
| **Cleanup Script** | `/scripts/docker_cleanup.py` | **Enhanced cleanup coordination** | Respects active environments, age-based cleanup |
| **Parallel Testing Verification** | `/scripts/test_parallel_docker_manager.py` | **Conflict detection testing** | Validates no conflicts with multiple runners |
| **Docker State Management** | Lock files in TEMP/LOCK_DIR | **Cross-platform coordination** | Windows/Unix compatible locking |
| **Rate Limiting System** | 30s cooldown, max 3 attempts | **Restart storm prevention** | Circuit breaker pattern |
| **Environment Types** | Shared/Dedicated/Production | **Resource optimization** | Balances efficiency vs isolation |

#### Docker Command-Line Interface
| Flag | Purpose | Use Case |
|------|---------|----------|
| `--docker-dedicated` | Use dedicated environment | E2E tests requiring isolation |
| `--docker-production` | Use production-optimized images | Memory-constrained environments |
| `--docker-no-cleanup` | Skip cleanup | Debugging Docker issues |
| `--docker-force-restart` | Override rate limiting | Emergency restart scenarios |
| `--docker-stats` | Show Docker statistics | Performance monitoring |
| `--cleanup-old-environments` | Clean stale environments | Maintenance operations |

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

## 📈 System Health Status (2025-08-31)

### Recent Critical Fixes
| Date | Issue | Fix | Impact |
|------|-------|-----|--------|
| 2025-08-31 | VPC Connector missing | Added terraform config for Cloud Run | Staging Redis/SQL connectivity |
| 2025-08-30 | Agent orchestration testing | New E2E framework for agents | Background agent validation |
| 2025-08-29 | Startup sequence non-deterministic | Implemented deterministic init | Chat service reliability |
| 2025-08-27 | WebSocket ABNORMAL_CLOSURE (1006) | Fixed state checking & subprotocol | Chat UI now working |
| 2025-08-27 | WebSocket Docker connectivity | Authentication bypass & CORS | Docker development functional |

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| **Test Coverage** | ~52% | 97% | 🔴 Critical |
| **Architecture Compliance** | 87.5% | 100% | 🟡 High |
| **Import Compliance** | ~50% | 100% | 🔴 Critical |
| **Service Independence** | 85% | 100% | 🟡 High |
| **WebSocket Events** | 100% | 100% | ✅ Fixed |

### Critical Issues
- **Test Parsing Errors**: 30+ test files with syntax errors
- **Import Violations**: 236 violations in real system, 15K+ in tests
- **Type Duplications**: Multiple duplicate definitions remain
- **WebSocket Integration**: Must maintain event flow for chat

---

## 🚀 Quick Start Commands

### Mission Critical Testing
```bash
# CRITICAL: Run before ANY WebSocket/Agent changes
python tests/mission_critical/test_websocket_agent_events_suite.py

# Check architecture compliance
python scripts/check_architecture_compliance.py

# Pre-deployment audit
python scripts/pre_deployment_audit.py
```

### Development
```bash
# 🔴 RECOMMENDED: Docker with Hot Reload (10x faster iteration)
docker-compose -f docker-compose.dev.yml up backend auth  # Hot reload enabled by default
python scripts/test_hot_reload.py  # Verify hot reload is working

# Alternative: Python-based launcher
python scripts/dev_launcher.py

# Run Quick Tests
python tests/unified_test_runner.py --level integration --no-coverage --fast-fail

# Check Compliance
python scripts/check_architecture_compliance.py
```

**Hot Reload Details:** See [`docs/docker-hot-reload-guide.md`](docs/docker-hot-reload-guide.md)

### Go to Symbol API Usage
```bash
# Search for symbols in code
curl -X GET "http://localhost:8000/api/corpus/symbols/search?q=UserService&symbol_type=class&limit=20"

# Get symbols from specific document
curl -X GET "http://localhost:8000/api/corpus/main/document/doc123/symbols"
```

### Deployment
```bash
# Deploy to Staging (WITH VPC CONNECTOR)
python scripts/deploy_to_gcp.py --project netra-staging --build-local
# NOTE: Requires VPC connector 'netra-connector' for Redis/SQL access

# Deploy to Production (With Checks)
python scripts/deploy_to_gcp.py --project netra-production --run-checks
```

### Docker Configuration & Service Management

#### 🔴 DUAL ENVIRONMENT SYSTEM (NEW - 2025-08-29)
**We now maintain TWO separate Docker environments that run simultaneously:**
- **TEST Environment (Port 8001):** Automated testing with real services (no mocks)
- **DEV Environment (Port 8000):** Local development with hot reload

**Quick Reference:**
- **Master Control:** `python scripts/docker_env_manager.py status` - Check both environments
- **Quick Start:** `python scripts/docker_env_manager.py start both` - Launch both environments
- **Documentation:** [`reports/docker/DOCKER_ENVIRONMENTS.md`](reports/docker/DOCKER_ENVIRONMENTS.md) - Quick reference guide
- **Complete Guide:** [`docs/docker-dual-environment-setup.md`](docs/docker-dual-environment-setup.md) - Full documentation

#### 🐳 Environment-Specific Launchers
- **TEST Launcher:** `/scripts/launch_test_env.py` - TEST environment for automated testing
- **DEV Launcher:** `/scripts/launch_dev_env.py` - DEV environment with hot reload
- **Master Manager:** `/scripts/docker_env_manager.py` - Control both environments

#### Docker Files & Configuration
- **TEST Compose:** `/docker-compose.test.yml` - TEST environment stack
- **DEV Compose:** `/docker-compose.dev.yml` - DEV environment stack  
- **Hot Reload:** `/docker-compose.override.yml` - DEV hot reload configuration
- **TEST Config:** `/.env.test` - TEST environment variables (ports 5433, 6380, 8124, 8001, 8082, 3001)
- **DEV Config:** `/.env.dev` - DEV environment variables (ports 5432, 6379, 8123, 8000, 8081, 3000)
- **Dockerfiles:** `/docker/*.test.Dockerfile` (TEST), `/docker/*.development.Dockerfile` (DEV)

#### Quick Docker Commands
```bash
# Check status of both environments
python scripts/docker_env_manager.py status

# Start both TEST and DEV environments
python scripts/docker_env_manager.py start both

# Start DEV only with hot reload
python scripts/launch_dev_env.py -d --open

# Start TEST only for automated testing  
python scripts/launch_test_env.py

# Stop all environments
python scripts/docker_env_manager.py stop all

# Start everything
python scripts/docker_services.py start full

# View Netra logs
python scripts/docker_services.py logs netra

# Stop all services
python scripts/docker_services.py stop
```

---

## 🔴 MISSION CRITICAL: Must Know Before Coding

### WebSocket Agent Event Requirements
**CRITICAL: The chat UI depends on these WebSocket events. Removing ANY will break user experience.**

Required events that MUST be sent:
1. `agent_started` - User sees agent began
2. `agent_thinking` - Real-time reasoning 
3. `tool_executing` - Tool transparency
4. `tool_completed` - Tool results
5. `agent_completed` - Completion signal

**CRITICAL: Silent Failure Prevention System (NEW - 2025-09-01)**
The system now has comprehensive safeguards against silent failures:
- **Startup Verification:** WebSocket functionality tested before accepting traffic
- **Event Monitoring:** Runtime monitoring detects and alerts on anomalies
- **Health Checking:** Active connection health monitoring with ping/pong
- **Confirmation System:** Critical events require delivery confirmation
- **Fallback Logging:** All failures logged at CRITICAL level

**Before ANY changes to agent/WebSocket code:**
```bash
python tests/mission_critical/test_websocket_agent_events_suite.py
python netra_backend/tests/integration/critical_paths/test_websocket_silent_failures.py
```

### Critical Integration Points
| System | Files | Impact if Broken |
|--------|-------|------------------|
| WebSocket Manager | `/netra_backend/app/websocket_core/manager.py` | No chat messages |
| Agent Registry | `/netra_backend/app/agents/registry.py` | No agent events |
| Tool Dispatcher | `/netra_backend/app/tools/enhanced_dispatcher.py` | No tool feedback |
| Execution Engine | `/netra_backend/app/agents/supervisor/execution_engine.py` | No agent execution |

---

## 📚 Essential Documentation

### Primary References
- [`CLAUDE.md`](CLAUDE.md) - AI agent instructions and principles
- **[`DEFINITION_OF_DONE_CHECKLIST.md`](DEFINITION_OF_DONE_CHECKLIST.md) - Module review checklists (MANDATORY)**
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

### Test System & Quality (SSOT INFRASTRUCTURE - MISSION COMPLETE 2025-09-02) ✅
- **🎯 SSOT COMPLIANCE: 94.5/100** | **ALL P0 VIOLATIONS RESOLVED** | **SPACECRAFT READY FOR LAUNCH**
- **🔴 SSOT TEST INFRASTRUCTURE SPEC** | [`SPEC/test_infrastructure_ssot.xml`](SPEC/test_infrastructure_ssot.xml) | **CANONICAL test architecture (94.5% compliance)**
- **🔴 SSOT VIOLATIONS RESOLVED** | [`TEST_INFRASTRUCTURE_SSOT_VIOLATIONS_REPORT.md`](TEST_INFRASTRUCTURE_SSOT_VIOLATIONS_REPORT.md) | **Complete resolution documentation**
- **🔴 SSOT COMPLIANCE REPORT** | [`TEST_INFRASTRUCTURE_COMPLIANCE_REPORT_FINAL.md`](TEST_INFRASTRUCTURE_COMPLIANCE_REPORT_FINAL.md) | **Final mission status report**
- **🔴 SSOT MIGRATION GUIDE** | [`SSOT_MIGRATION_GUIDE.md`](SSOT_MIGRATION_GUIDE.md) | **Developer migration instructions**
- **🔴 SSOT TEST RUNNER** | `/tests/unified_test_runner.py` | **SINGLE SOURCE OF TRUTH for test execution**
- **🔴 TEST EXECUTION TRACKER** | `/scripts/test_execution_tracker.py` | Test history, flaky detection, prioritization
- **🔴 TEST DASHBOARD** | `/scripts/test_dashboard.py` | Interactive metrics, HTML reports, recommendations  
- **🔴 PRE-DEPLOYMENT AUDIT** | `/scripts/pre_deployment_audit.py` | **Catch LLM coding errors before deploy**
- [`SPEC/pre_deployment_audit.xml`](SPEC/pre_deployment_audit.xml) - **Pre-deployment audit specification**
- [`SPEC/learnings/test_system_improvements.xml`](SPEC/learnings/test_system_improvements.xml) - **E2E fix & test tracking learnings**
- [`SPEC/test_infrastructure_architecture.xml`](SPEC/test_infrastructure_architecture.xml) - Legacy test architecture patterns
- [`reports/audit/E2E_TEST_BLOCKING_AUDIT.md`](reports/audit/E2E_TEST_BLOCKING_AUDIT.md) - E2E test issues documentation

---

## 🎯 Action Items

### Immediate (Critical)
1. Fix 30+ test file syntax errors blocking test discovery
2. Maintain WebSocket agent event flow (run mission critical tests)
3. Fix import violations - 236 in real system

### Short-term (Week 1)
1. Restore test suite functionality
2. Improve architecture compliance to 95%
3. Document VPC connector requirements

### Long-term (Quarter 1)
1. Achieve 97% coverage
2. Implement contract testing
3. Deploy monitoring dashboards

---

## 🔍 Search Patterns & Common Queries

### Finding Code
```bash
# Find all implementations of a function
python scripts/query_string_literals.py search "function_name"

# Find WebSocket event handlers
grep -r "agent_started\|agent_thinking\|tool_executing" netra_backend/

# Find configuration keys
python scripts/query_string_literals.py validate "CONFIG_KEY"
```

### Common File Patterns
| Pattern | Purpose | Example |
|---------|---------|---------|
| `*_prompts.py` | Agent prompts | `supervisor_prompts.py` |
| `test_*_suite.py` | Test suites | `test_websocket_agent_events_suite.py` |
| `*_manager.py` | Service managers | `database_manager.py` |
| `*_config.py` | Configuration files | `cors_config.py` |

---

**For complete cross-system navigation and detailed integration maps, refer to:**
- [`SPEC/CROSS_SYSTEM_MASTER_INDEX.md`](SPEC/CROSS_SYSTEM_MASTER_INDEX.md) - Complete navigation
- [`SPEC/SYSTEM_INTEGRATION_MAP.xml`](SPEC/SYSTEM_INTEGRATION_MAP.xml) - Integration points
- [`MASTER_WIP_STATUS.md`](MASTER_WIP_STATUS.md) - Current system health