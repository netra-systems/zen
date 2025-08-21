# 🤖 LLM MASTER INDEX - Netra Apex Navigation Guide

## 🔴 CRITICAL: File Location Reference

This index helps LLMs quickly locate and understand the purpose of files in the Netra Apex codebase.
**USE THIS FIRST** when searching for functionality or making changes.

---

## 📍 COMMONLY CONFUSED FILES & LOCATIONS

### Configuration Files (Multiple Similar Names)
| File | Location | Purpose | Common Confusion |
|------|----------|---------|------------------|
| `config.py` | `/app/config.py` | Main FastAPI app config | Often confused with scripts/config_setup_core.py |
| `config_setup_core.py` | `/scripts/config_setup_core.py` | Development setup script | NOT the main config |
| `.env` | `/` (root) | Environment variables | Check here for secrets |
| `settings.json` | `/frontend/settings.json` | Frontend settings | Different from backend config |

### Database Files (Similar Names, Different DBs)
| File | Location | Purpose | Key Functions |
|------|----------|---------|---------------|
| `clickhouse.py` | `/app/db/clickhouse.py` | ClickHouse connection | get_clickhouse_client() |
| `postgres.py` | `/app/db/postgres.py` | PostgreSQL connection | get_postgres_db() |
| `clickhouse_operations.py` | `/app/agents/` | ClickHouse data operations | Agent-specific queries |
| `models_auth.py` | `/app/db/models_auth.py` | Auth database models | User, Team, Session |
| `models_corpus.py` | `/app/db/models_corpus.py` | Corpus database models | CorpusData, CorpusEntry |
| `models_metrics.py` | `/app/db/models_metrics.py` | Metrics database models | MetricsData |

### Authentication & Security (MANDATORY Shared Auth Integration)
| File | Location | Purpose | Key Components |
|------|----------|---------|----------------|
| **🔴 AUTH INTEGRATION (MANDATORY)** | | | |
| `auth.py` | `/app/auth_integration/auth.py` | **SHARED AUTH SERVICE** | get_current_user(), get_current_user_optional(), validate_token() |
| **CRITICAL**: ALL authentication throughout ENTIRE system MUST use `/app/auth_integration/`. NO duplicate auth logic allowed. |
| **AUTH MODULE** | | | |
| `__init__.py` | `/app/auth/__init__.py` | Auth module initialization | Module exports |
| **SECRETS** | | | |
| `secret_manager.py` (app) | `/app/core/secret_manager.py` | Production secrets | get_secret, SecretManager class |
| `secret_manager.py` (dev) | `/dev_launcher/secret_manager.py` | Dev secrets only | Development environment only |

### WebSocket Files (Complex Structure)
| File | Location | Purpose | Key Functions |
|------|----------|---------|---------------|
| `websockets.py` | `/app/routes/websockets.py` | WebSocket endpoints | websocket_endpoint() |
| `connection.py` | `/app/websocket/connection.py` | Connection management | ConnectionManager class |
| `quality_message_handler.py` | `/app/services/websocket/quality_message_handler.py` | Message quality handling | QualityMessageHandler |
| `websocket_types.py` | `/app/schemas/websocket_types.py` | WebSocket type definitions | WSMessage, WSResponse |
| `rate_limiter.py` | `/app/websocket/rate_limiter.py` | Rate limiting | RateLimiter class |
| `validation.py` | `/app/websocket/validation.py` | Message validation | validate_message() |

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
| **APEX Optimizer Agent** | `/app/services/apex_optimizer_agent/` | Multiple tool files | AI optimization agent system |
| - Cost Analysis Tools | `/app/services/apex_optimizer_agent/tools/` | `cost_*.py` | Cost analysis and optimization |
| - Performance Tools | `/app/services/apex_optimizer_agent/tools/` | `performance_*.py`, `latency_*.py` | Performance optimization |
| - Log Analysis Tools | `/app/services/apex_optimizer_agent/tools/` | `log_*.py` | Log analysis and pattern detection |
| - Optimization Tools | `/app/services/apex_optimizer_agent/tools/` | `optimization_*.py`, `optimal_*.py` | Various optimization strategies |
| - KV Cache Tools | `/app/services/apex_optimizer_agent/tools/` | `kv_cache_*.py` | Key-value cache optimization |
| - Supply Tools | `/app/services/apex_optimizer_agent/tools/` | `supply_catalog_search.py` | Supply catalog search |
| - Report Generation | `/app/services/apex_optimizer_agent/tools/` | `final_report_generator.py` | Final optimization reports |

### Test Files (Multiple Test Types)
| Test Type | Location | Pattern | Run Command |
|-----------|----------|---------|-------------|
| Unit Tests | `/app/tests/unit/` | `test_*.py` | `python -m test_framework.test_runner --level unit` |
| E2E Tests | `/app/tests/e2e/` | `test_e2e_*.py` | `python -m test_framework.test_runner --level e2e` |
| Real Agent Tests | `/app/tests/` | `test_real_agent_services.py` | Direct test file |
| Frontend Tests | `/frontend/__tests__/` | `*.test.tsx` | `npm test` |

### Bad Test Detection System
| Component | Location | Purpose | Key Functions |
|-----------|----------|---------|---------------|
| **Detector** | `/test_framework/bad_test_detector.py` | Core detection engine | BadTestDetector class, tracks failures |
| **Pytest Plugin** | `/test_framework/pytest_bad_test_plugin.py` | Pytest integration | Automatic test outcome recording |
| **Reporter CLI** | `/test_framework/bad_test_reporter.py` | View/manage reports | `python -m test_framework.bad_test_reporter` |
| **Data Storage** | `/test_reports/bad_tests.json` | Persistent failure history | JSON format with test statistics |
| **Integration** | `/scripts/test_backend.py` | Backend test runner | `--no-bad-test-detection` flag |

#### Bad Test Detection Commands
```bash
# View bad test report
python -m test_framework.bad_test_reporter

# View summary only
python -m test_framework.bad_test_reporter --summary

# View specific test history
python -m test_framework.bad_test_reporter --test "test_name"

# Reset bad test data
python -m test_framework.bad_test_reporter --reset

# Disable detection for a run
python scripts/test_backend.py --no-bad-test-detection
```

---

## 🗂️ MAIN ENTRY POINTS

### Backend Entry Points
- **Main App**: `/app/main.py` - FastAPI application entry
- **Dev Launcher**: `/scripts/dev_launcher.py` - Development server starter
- **Test Runner**: `/test_framework/test_runner.py` - Test execution entry (run with `python -m test_framework.test_runner`)

### Deployment Entry Points
- **Enhanced Deploy**: `/organized_root/deployment_configs/deploy_staging_enhanced.py` - Modular deployment orchestrator
- **Standard Deploy**: `/organized_root/deployment_configs/deploy_staging.py` - Standard deployment script
- **Setup Auth**: `/organized_root/deployment_configs/setup_staging_auth.py` - GCP authentication setup

### Frontend Entry Points
- **Next.js App**: `/frontend/app/page.tsx` - Main page component
- **Layout**: `/frontend/app/layout.tsx` - App layout wrapper
- **Package.json**: `/frontend/package.json` - Frontend dependencies & scripts

---

## 📦 SCHEMA & TYPE DEFINITIONS

### Backend Schemas (`/app/schemas/`)
| Category | Files | Purpose |
|----------|-------|---------|
| Analysis | `Analysis.py` | Analysis data types |
| Events | `Event.py` | Event data structures |
| Logs | `Log.py` | Log data types |
| Patterns | `Pattern.py` | Pattern detection types |
| Performance | `Performance.py` | Performance metrics types |
| Policy | `Policy.py` | Policy configuration types |
| Requests | `Request.py` | Request data types |
| Runs | `Run.py` | Run execution types |

### Frontend Types (`/frontend/types/`)
| File | Purpose |
|------|---------|
| `index.ts` | Main type exports |
| `websocket.ts` | WebSocket types |
| `auth.ts` | Authentication types |
| `admin.ts` | Admin panel types |
| `chat.ts` | Chat interface types |

---

## 🔧 UTILITY & HELPER FILES

### Core Utilities (`/app/core/`)
| File | Purpose | Key Functions |
|------|---------|---------------|
| `exceptions_base.py` | Base exception classes | NetraException |
| `exceptions_auth.py` | Auth exceptions | AuthenticationError |
| `exceptions_db.py` | Database exceptions | DatabaseError |
| `interfaces_base.py` | Base interfaces | BaseInterface |
| `interfaces_agent.py` | Agent interfaces | AgentInterface |
| `system_health_monitor.py` | System monitoring | HealthMonitor class |
| `fallback_coordinator.py` | Fallback handling | FallbackCoordinator |

### GCP Deployment Modules (`/organized_root/deployment_configs/`)
| Module | Location | Purpose | Key Components |
|--------|----------|---------|----------------|
| **Core Modules** | `/core/` | Deployment orchestration | |
| `deployment_orchestrator.py` | `/core/` | Main deployment coordinator | DeploymentOrchestrator, DeploymentConfig |
| `docker_image_manager.py` | `/core/` | Docker build & push | DockerImageManager, DockerImage |
| `cloud_run_deployer.py` | `/core/` | Cloud Run deployments | CloudRunDeployer, CloudRunService |
| `health_checker.py` | `/core/` | Service health validation | HealthChecker, HealthStatus |
| **Monitoring Modules** | `/monitoring/` | Real-time monitoring | |
| `real_time_monitor.py` | `/monitoring/` | Live log streaming | RealTimeMonitor, DeploymentMetrics |
| `error_analyzer.py` | `/monitoring/` | Error categorization | ErrorAnalyzer, ErrorCategory |
| `log_correlator.py` | `/monitoring/` | Cross-service correlation | LogCorrelator, CorrelatedEvent |
| `memory_recovery_strategies.py` | Memory management | Recovery strategies |

### Scripts (`/scripts/`)
| Script | Purpose | When to Use |
|--------|---------|-------------|
| `check_architecture_compliance.py` | Check 450-line & 25-line limits | Before commits, CI/CD |
| `dev_launcher.py` | Development launcher | Start dev environment |
| `test_runner.py` | Test runner | Run tests |

### Architecture Compliance System (`/scripts/compliance/`)
| Module | Purpose | Key Features |
|--------|---------|-------------|
| `__init__.py` | Package initialization | Module exports |
| `core.py` | Core data structures | Violation, ComplianceResults, ComplianceConfig |
| `orchestrator.py` | Compliance orchestration | ArchitectureEnforcer class |
| `reporter.py` | Report generation (273 lines) | ComplianceReporter class |
| `reporter_stats.py` | Statistics calculation (61 lines) | StatisticsCalculator class |
| `reporter_utils.py` | Reporting utilities (47 lines) | ReporterUtils, sorting, limits |
| `cli.py` | CLI argument handling | CLIHandler, OutputHandler |
| `file_checker.py` | File size validation | Checks 450-line limit |
| `function_checker.py` | Function complexity | Checks 25-line limit |
| `type_checker.py` | Duplicate type detection | Single source of truth |
| `stub_checker.py` | Test stub detection | No stubs in production |

---

## 🎯 BUSINESS-CRITICAL FILES

### Revenue & Monetization
- **To Be Implemented** - Business-critical revenue tracking
- Monitor `/app/services/` for future billing modules
- Check `/app/routes/` for pricing endpoints when added

---

## 📋 SPECIFICATION FILES (`/SPEC/`)

### 🔴 CRITICAL Priority Specs (ALWAYS Check First)
| Spec | Purpose | When to Use |
|------|---------|-------------|
| **`type_safety.xml`** | Type safety, SSOT enforcement | BEFORE any code changes |
| **`conventions.xml`** | 300/8 rule, coding standards | BEFORE generating code |
| **`code_changes.xml`** | Change checklist protocol | BEFORE making changes |
| **`learnings/index.xml`** | Index of all past issues & solutions | ALWAYS check first |
| **`anti_regression.xml`** | System stability requirements | Before commits |
| **`no_test_stubs.xml`** | Production test purity | When writing tests |
| **`ai_factory_patterns.xml`** | Multi-agent workflows | Complex coding tasks |

### 📚 Knowledge Base & Learnings (`/SPEC/learnings/`)
| Category | File | Critical Takeaways |
|----------|------|-------------------|
| **Index** | `index.xml` | Master retrieval map for all learnings |
| **Authentication** | `auth.xml`, `jwt_secret_configuration.xml` | Shared auth service integration |
| **WebSocket** | `websocket_message_paradox.xml`, `websocket_*.xml` | Async handling, error patterns |
| **Configuration** | `configuration_secrets.xml`, `environment_*.xml` | Unified config system |
| **Testing** | `testing.xml`, `e2e_testing.xml`, `bad_test_detection.xml` | TDD workflows, real vs mock |
| **Database** | `database_asyncio.xml`, `database_*.xml` | Async patterns, connections |
| **Frontend** | `frontend.xml`, `react-content-handling.xml` | Zustand patterns, React |
| **Deployment** | `deployment_staging.xml` | Cloud Run, staging |
| **Startup** | `startup.xml`, `startup_optimization.xml` | Initialization order |
| **Compliance** | `architectural_compliance.xml`, `compliance_improvements.xml` | 300/8 enforcement |

### 🏗️ Architecture & System Design
| Spec | Purpose | Key Requirements |
|------|---------|-----------------|
| **`architecture.xml`** | System architecture | Component relationships |
| **`system_boundaries.xml`** | Boundary definitions | Module separation |
| **`independent_services.xml`** | Microservice independence | 100% isolation requirement |
| **`growth_control.xml`** | Healthy growth patterns | Composition over monoliths |
| **`directory_structure.xml`** | File organization | Standard layout |

### 🔧 Core Infrastructure
| Domain | Specs | Purpose |
|--------|-------|---------|
| **Databases** | `clickhouse.xml`, `postgres.xml`, `database.xml` | Database patterns |
| **WebSocket** | `websockets.xml`, `websocket_*.xml` | Real-time communication |
| **Authentication** | `auth_*.xml`, `shared_auth_integration.xml`, `PRODUCTION_SECRETS_ISOLATION.xml` | Auth & secrets |
| **Testing** | `testing.xml`, `enhanced_testing.xml`, `coverage_requirements.xml` | Test standards |
| **CI/CD** | `github_actions.xml`, `cicd_testing.xml` | Pipeline configuration |
| **Deployment** | `deployment.xml`, `staging_*.xml`, `terraform_gcp.xml` | Deployment configs |

### 🤖 Agent System Specifications
| Spec | Purpose | Components |
|------|---------|------------|
| **`agent_architecture.xml`** | Agent system design | Base patterns |
| **`subagents.xml`** | SubAgent definitions | Agent types |
| **`agent_tracking.xml`** | Agent monitoring | Tracking patterns |
| **`agent_testing.xml`** | Agent test patterns | Testing agents |
| **`supervisor_observability.xml`** | Supervisor monitoring | Observability |
| **`TRIAGE_SUB_AGENT_SPEC.xml`** | Triage agent spec | Specific agent |
| **`supply_researcher_agent.xml`** | Supply agent spec | Research agent |
| **`github_code_analysis_agent.xml`** | GitHub analysis | Code analysis |
| **`data_sub_agent_enhancement.xml`** | Data agent improvements | Enhancements |

### 🎨 UI/UX Specifications
| Spec | Purpose | Focus Area |
|------|---------|------------|
| **`ui_ux_master.xml`** | Master UI/UX guide | Overall design |
| **`ui_ux_chat_architecture.xml`** | Chat interface | Chat design |
| **`ui_ux_websocket.xml`** | WebSocket UI | Real-time UI |
| **`ui_ux_visual_design.xml`** | Visual design | Look & feel |
| **`ui_ux_developer_tools.xml`** | Dev tools UI | Developer UX |
| **`ui_ux_response_card.xml`** | Response cards | UI components |
| **`ui_ux_thread_state_management.xml`** | Thread state | State management |
| **`ui_ux_fluid_updates.xml`** | Fluid updates | Smooth UX |
| **`unified_chat_ui_ux.xml`** | Unified chat | Complete chat UX |
| **`admin_unified_experience.xml`** | Admin panel | Admin interface |

### 🧪 Testing & Quality
| Spec | Purpose | Coverage |
|------|---------|----------|
| **`testing.xml`** | Core testing standards | All tests |
| **`enhanced_testing.xml`** | Advanced patterns | Complex testing |
| **`coverage_requirements.xml`** | Coverage targets | Minimum coverage |
| **`e2e-testing-spec.xml`** | E2E test patterns | End-to-end |
| **`e2e-agent-workflows-unified.xml`** | Agent E2E tests | Agent testing |
| **`failing_test_management.xml`** | Test failure handling | Failure patterns |
| **`missing_tests.xml`** | Test gap analysis | Coverage gaps |
| **`startup_coverage.xml`** | Startup test coverage | Initialization |
| **`local_actions_testing.xml`** | Local test patterns | Local testing |
| **`frontend_testing_*.xml`** | Frontend test specs | React testing |

### 📊 Monitoring & Observability
| Spec | Purpose | Systems |
|------|---------|---------|
| **`gcp_observability.xml`** | GCP monitoring | Cloud monitoring |
| **`supervisor_observability.xml`** | Supervisor metrics | Agent monitoring |
| **`compliance_reporting.xml`** | Compliance tracking | Architecture compliance |
| **`test_reporting.xml`** | Test result reporting | Test metrics |
| **`ai_factory_status_report.xml`** | AI factory status | Factory metrics |

### 🔐 Security & Configuration
| Spec | Purpose | Scope |
|------|---------|-------|
| **`security.xml`** | Security requirements | All services |
| **`PRODUCTION_SECRETS_ISOLATION.xml`** | Secret management | Production secrets |
| **`auth_environment_isolation.xml`** | Auth isolation | Environment separation |
| **`environment_loading.xml`** | Environment config | Config loading |
| **`unified_configuration_management.xml`** | Config management | Unified config |
| **`tool_auth_system.xml`** | Tool authentication | Tool access |
| **`feature_flags.xml`** | Feature toggles | Feature management |

### 🚀 Deployment & Infrastructure
| Spec | Purpose | Environment |
|------|---------|-------------|
| **`deployment.xml`** | Deployment patterns | All environments |
| **`staging_environment.xml`** | Staging setup | Staging env |
| **`staging_workflow.xml`** | Staging processes | Staging workflow |
| **`terraform_gcp.xml`** | Terraform configs | GCP infrastructure |
| **`cloud-run-*.xml`** | Cloud Run specs | GCP Cloud Run |
| **`dev_launcher*.xml`** | Dev environment | Local development |
| **`local_deployment.xml`** | Local deploy | Local setup |

### 💡 AI Development Patterns
| Spec | Purpose | Usage |
|------|---------|-------|
| **`ai_factory_patterns.xml`** | AI factory workflows | Multi-agent patterns |
| **`ai-dev-productivity.xml`** | AI productivity | Development efficiency |
| **`ai_slop_prevention_*.xml`** | Prevent AI slop | Quality control |
| **`context_optimization.xml`** | Context efficiency | Token optimization |
| **`corpus_generation.xml`** | Corpus creation | Data generation |
| **`synthetic_data_generation.xml`** | Synthetic data | Test data |

### 🔄 Business & Operations
| Spec | Purpose | Focus |
|------|---------|-------|
| **`app_business_value.xml`** | Business value tracking | Value metrics |
| **`business_value_test_coverage.xml`** | Value-based testing | Test prioritization |
| **`master_wip_index.xml`** | WIP tracking | Work in progress |
| **`master_orchestration.xml`** | Orchestration patterns | System coordination |
| **`team_updates.xml`** | Team communication | Updates & status |

### 🔌 Integrations
| Spec | Purpose | Integration |
|------|---------|-------------|
| **`mcp.xml`, `mcp_*.xml`** | MCP integration | Model Context Protocol |
| **`lark_github_integration.xml`** | Lark/GitHub | External integrations |
| **`api_routes.xml`** | API definitions | Route specifications |

### 📝 Documentation & Examples
| Spec | Purpose | Content |
|------|---------|---------|
| **`doc_overall.xml`** | Documentation guide | Doc standards |
| **`documentation_maintenance.xml`** | Doc maintenance | Keeping docs updated |
| **`exampleNetraPrompts.xml`** | Example prompts | Usage examples |
| **`instructions.xml`** | General instructions | Guidelines |

### 🔍 String Literals & Constants
| Spec | Purpose | Usage |
|------|---------|-------|
| **`string_literals_index.xml`** | String literal system | Constant management |
| **`/SPEC/generated/string_literals.json`** | Generated index | 35,000+ constants |

### 📁 Archived & Historical
| Directory | Purpose | Contents |
|-----------|---------|----------|
| **`/SPEC/archived_implementations/`** | Deprecated patterns | Old implementations |
| **`/SPEC/history/`** | Historical records | Past changes & reviews |

### 🛠️ Development Tools & Utilities
| Spec | Purpose | Tools |
|------|---------|-------|
| **`build_bot.xml`** | Build automation | Build patterns |
| **`coding-agent.xml`** | Coding agent spec | Agent coding |
| **`error_handling_principles.xml`** | Error handling | Error patterns |
| **`selfchecks.xml`** | Self-check patterns | Validation |

### 📊 Data & State Management
| Spec | Purpose | Scope |
|------|---------|-------|
| **`data.xml`** | Data patterns | Data handling |
| **`core.xml`** | Core patterns | Fundamental patterns |
| **`types.xml`** | Type definitions | Type system |
| **`swimlane.xml`** | Process flows | Workflow lanes |
| **`Status.xml`** | Status tracking | System status |

### Critical Update Reminders
- **ALWAYS** check `learnings/index.xml` before any task
- **NEVER** violate the 300/8 rule from `conventions.xml`
- **MANDATORY** shared auth integration per `shared_auth_integration.xml`
- **VALIDATE** string literals using the index system
- **ENFORCE** type safety per `type_safety.xml`

---

## 🚨 COMMON PITFALLS & SOLUTIONS

### Issue: "Can't find config file"
- **Check**: `/app/config.py` for app config
- **NOT**: `/scripts/config_setup_core.py` (setup script)

### Issue: "Database connection error"
- **ClickHouse**: Check `/app/db/clickhouse.py`
- **PostgreSQL**: Check `/app/db/postgres.py`
- **Env vars**: Check `.env` file

### Issue: "Authentication not working"
- **Routes**: `/app/routes/auth/auth.py`
- **Logic**: `/app/auth/auth.py`
- **Models**: `/app/db/models_auth.py`

### Issue: "WebSocket connection issues"
- **Endpoint**: `/app/routes/websockets.py`
- **Manager**: `/app/websocket/connection.py`
- **Types**: `/app/schemas/websocket_types.py`

### Issue: "Tests failing"
- **Runner**: `/test_framework/test_runner.py` (use `python -m test_framework.test_runner`)
- **Unit tests**: `/app/tests/unit/`
- **E2E tests**: `/app/tests/e2e/`

---

## 🔍 QUICK SEARCH PATTERNS

### Finding functionality:
1. Check this index first
2. Use `Grep` for specific function names
3. Check `/SPEC/learnings/` for past solutions
4. Look in `/app/services/` for business logic
5. Check `/app/routes/` for API endpoints

### Making changes:
1. Read relevant spec files first
2. Check for existing implementations
3. Follow 450-line module limit
4. Run tests before and after
5. Update specs if learning something new

---

## 📝 NOTES FOR LLMs

- **ALWAYS** check this index before searching
- **NEVER** confuse `/app/config.py` with `/scripts/config_setup_core.py`
- **ALWAYS** check `/SPEC/learnings/` for past issues
- **Files over 300 lines** must be split into modules
- **Functions over 8 lines** must be split into smaller functions
- **Type safety** is the #1 priority - check `type_safety.xml`

---

## 🆕 NEW MODULES & SERVICES

### Apex Optimizer Agent (`/app/services/apex_optimizer_agent/`)
A comprehensive AI optimization agent system with 30+ specialized tools:

#### Core Files
- `config_form.py` - Configuration forms
- `models.py` - Agent data models
- `tool_builder.py` - Tool construction utilities
- `dev_utils.py` - Development utilities

#### Tool Categories (in `/tools/`)
1. **Cost Optimization**
   - `cost_analyzer.py`, `cost_estimator.py`, `cost_driver_identifier.py`
   - `cost_impact_simulator.py`, `cost_reduction_quality_preservation.py`
   - `cost_simulation_for_increased_usage.py`

2. **Performance Analysis**
   - `performance_predictor.py`, `performance_gains_simulator.py`
   - `function_performance_analyzer.py`, `latency_analyzer.py`
   - `latency_bottleneck_identifier.py`, `tool_latency_optimization.py`

3. **Log Processing**
   - `log_fetcher.py`, `log_analyzer.py`, `log_pattern_identifier.py`
   - `log_enricher_and_clusterer.py`

4. **Optimization Strategies**
   - `optimization_proposer.py`, `optimization_method_researcher.py`
   - `optimized_implementation_proposer.py`, `optimal_policy_proposer.py`
   - `advanced_optimization_for_core_function.py`
   - `multi_objective_optimization.py`

5. **Cache Management**
   - `kv_cache_finder.py`, `kv_cache_optimization_audit.py`

6. **Policy & Simulation**
   - `policy_proposer.py`, `policy_simulator.py`
   - `quality_impact_simulator.py`, `rate_limit_impact_simulator.py`
   - `new_model_effectiveness_analysis.py`

7. **System Analysis**
   - `system_inspector.py`, `code_analyzer.py`
   - `evaluation_criteria_definer.py`, `future_usage_modeler.py`

8. **Supply & Dispatch**
   - `supply_catalog_search.py`, `tool_dispatcher.py`

9. **Reporting**
   - `final_report_generator.py`, `finish.py`

### Database Services (`/app/services/database/`)
- `reference_repository.py` - Reference data management
- `thread_repository.py` - Thread management
- `run_repository.py` - Run execution management
- `message_repository.py` - Message handling

### Other Services (`/app/services/`)
- `clickhouse_service.py` - ClickHouse operations
- `dev_bypass_service.py` - Development bypass utilities
- `job_store.py` - Job management
- `key_manager.py` - Key management service
- `tool_registry.py` - Tool registration
- `generation_worker.py` - Generation worker service
- `state/persistence.py` - State persistence

### Data Modules (`/app/data/`)
- `content_corpus.py` - Content corpus management
- `synthetic/content_generator.py` - Synthetic content generation
- `synthetic/default_synthetic_config.py` - Default synthetic configs

### MCP Integration (`/app/netra_mcp/`)
- `run_server.py` - MCP server runner

---

## 🔥 TOP 50 STABLE CONCEPTS - Context Window Optimization

### Core Infrastructure (Most Referenced)
| Concept | Primary Location | Import | Frequency | Notes |
|---------|-----------------|--------|-----------|-------|
| **Logging** | `/app/logging_config.py` | `from app.logging_config import central_logger` | 495 | EVERY module uses this |
| **Config** | `/app/config.py` | `from app.config import settings` | 41 | App-wide settings |
| **WebSocket Manager** | `/app/ws_manager.py` | `from app.ws_manager import ws_manager` | 55 | WebSocket state management |
| **Redis Manager** | `/app/redis_manager.py` | `from app.redis_manager import redis_manager` | 49 | Cache & pub/sub |

### Type System & Schemas (Critical for Type Safety)
| Concept | Primary Location | Import | Used For |
|---------|-----------------|--------|----------|
| **Schemas** | `/app/schemas/` | `from app.schemas import *` | 90+ | All data models |
| **Shared Types** | `/app/schemas/shared_types.py` | `from app.schemas.shared_types import ToolResult, ErrorContext` | Type definitions |
| **Core Enums** | `/app/schemas/core_enums.py` | `from app.schemas.core_enums import ErrorCategory, ToolStatus` | Enum constants |
| **Registry** | `/app/schemas/registry.py` | `from app.schemas.registry import WebSocketMessage` | Message types |
| **Metrics** | `/app/schemas/Metrics.py` | `from app.schemas.Metrics import MetricData` | Metrics types |

### Database Layer (Stable Core)
| Concept | Primary Location | Import | Purpose |
|---------|-----------------|--------|---------|
| **PostgreSQL Models** | `/app/db/models_postgres.py` | `from app.db.models_postgres import User, Team` | 73 uses |
| **ClickHouse Client** | `/app/db/clickhouse.py` | `from app.db.clickhouse import get_clickhouse_client` | 27 uses |
| **PostgreSQL Session** | `/app/db/postgres.py` | `from app.db.postgres import get_postgres_db` | 26 uses |
| **Query Fixer** | `/app/db/clickhouse_query_fixer.py` | `from app.db.clickhouse_query_fixer import fix_query` | ClickHouse fixes |

### Exception Hierarchy (Stable)
| Concept | Primary Location | Import | Coverage |
|---------|-----------------|--------|----------|
| **Base Exceptions** | `/app/core/exceptions_base.py` | `from app.core.exceptions_base import NetraException` | 66 uses |
| **Service Exceptions** | `/app/core/exceptions_service.py` | `from app.core.exceptions_service import ServiceError` | Service errors |
| **Auth Exceptions** | `/app/core/exceptions_auth.py` | `from app.core.exceptions_auth import AuthenticationError` | Auth errors |
| **Error Codes** | `/app/core/error_codes.py` | `from app.core.error_codes import ErrorSeverity` | 42 uses |

### LLM Integration (Core Functionality)
| Concept | Primary Location | Import | Purpose |
|---------|-----------------|--------|---------|
| **LLM Manager** | `/app/llm/llm_manager.py` | `from app.llm.llm_manager import LLMManager` | 87 uses |
| **Observability** | `/app/llm/observability.py` | `from app.llm.observability import log_agent_*` | LLM tracking |
| **LLM Operations** | `/app/llm/llm_operations.py` | `from app.llm.llm_operations import *` | LLM ops |

### Agent System (Complex but Stable)
| Concept | Primary Location | Import | Purpose |
|---------|-----------------|--------|---------|
| **Agent State** | `/app/agents/state.py` | `from app.agents.state import DeepAgentState` | 114 uses |
| **Tool Dispatcher** | `/app/agents/tool_dispatcher.py` | `from app.agents.tool_dispatcher import ToolDispatcher` | 49 uses |
| **Supervisor** | `/app/agents/supervisor_consolidated.py` | `from app.agents.supervisor_consolidated import SupervisorAgent` | 32 uses |
| **Base Agent** | `/app/agents/base.py` | `from app.agents.base import BaseSubAgent` | 21 uses |
| **Error Handler** | `/app/agents/error_handler.py` | `from app.agents.error_handler import global_error_handler` | Agent errors |

### Core Services (Business Logic)
| Concept | Primary Location | Import | Purpose |
|---------|-----------------|--------|---------|
| **Quality Gate** | `/app/services/quality_gate_service.py` | 60 uses | Quality checks |
| **Context Service** | `/app/services/context.py` | 39 uses | Context management |
| **Synthetic Data** | `/app/services/synthetic_data_service.py` | 32 uses | Data generation |
| **Agent Service** | `/app/services/agent_service.py` | 26 uses | Agent orchestration |
| **State Persistence** | `/app/services/state_persistence_service.py` | 22 uses | State storage |
| **Corpus Service** | `/app/services/corpus_service.py` | 22 uses | Corpus management |
| **Thread Service** | `/app/services/thread_service.py` | 17 uses | Thread management |
| **Tool Permissions** | `/app/services/tool_permission_service.py` | 14 uses | Access control |
| **Quality Monitoring** | `/app/services/quality_monitoring_service.py` | 13 uses | Quality metrics |

### Reliability & Recovery
| Concept | Primary Location | Import | Purpose |
|---------|-----------------|--------|---------|
| **Circuit Breaker** | `/app/core/circuit_breaker.py` | 19 uses | Fault tolerance |
| **Error Recovery** | `/app/core/error_recovery.py` | 28 uses | Recovery strategies |
| **Reliability** | `/app/core/reliability.py` | 14 uses | System reliability |

### Authentication (MANDATORY Shared)
| Concept | Primary Location | Import | Purpose |
|---------|-----------------|--------|---------|
| **Auth Integration** | `/app/auth_integration/auth.py` | `from app.auth_integration.auth import get_current_user` | 14 uses |
| **Dependencies** | `/app/dependencies.py` | 16 uses | Dependency injection |

### Utilities
| Concept | Primary Location | Import | Purpose |
|---------|-----------------|--------|---------|
| **JSON Parsing** | `/app/core/json_parsing_utils.py` | 15 uses | Safe JSON parsing |

### Quick Reference Patterns
```python
# Most common import pattern
from app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

# Database session pattern
from app.db.postgres import get_postgres_db
async with get_postgres_db() as db:
    # operations

# Error handling pattern
from app.core.exceptions_base import NetraException
raise NetraException("message", error_code="CODE")

# Type-safe schema pattern
from app.schemas import RequestModel, ResponseModel

# Agent state pattern
from app.agents.state import DeepAgentState
state = DeepAgentState(...)
```

### Performance Tips
1. **Import only what you need** - e.g use `from app.schemas import {specific exact thing needed}`
2. **Use TYPE_CHECKING** for circular imports - `if TYPE_CHECKING: from app.x import Y`
3. **Cache heavy imports** - Store LLMManager, connections as module variables
4. **Lazy load optional features** - Import inside functions if rarely used

---

Last Updated: 2025-08-20