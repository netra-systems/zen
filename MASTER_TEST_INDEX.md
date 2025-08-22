# Master Testing Index
## Netra Apex AI Optimization Platform

> **Last Updated:** 2025-08-21
> **Total Test Files:** 900+
> **Test Frameworks:** pytest, jest, cypress
> **Coverage Target:** 80%

## Quick Navigation

- [Test Organization](#test-organization)
- [Service-Specific Tests](#service-specific-tests)
- [Test Categories](#test-categories)
- [Test Runners & Commands](#test-runners--commands)
- [Critical Test Paths](#critical-test-paths)
- [Coverage Reports](#coverage-reports)
- [Recently Deleted Tests](#recently-deleted-tests)

## Test Organization

### Primary Test Locations

```
/auth_service/tests/          # Auth service tests
/netra_backend/tests/         # Main backend tests
/frontend/__tests__/          # Frontend tests (369 test files)
/frontend/cypress/            # Frontend E2E tests
/dev_launcher/tests/          # Development launcher tests
/legacy_integration_tests/    # Legacy integration tests
/test_framework/              # Test framework utilities
/tests/                       # Cross-service tests (DELETED)
```

## Service-Specific Tests

### 1. Auth Service (`/auth_service/tests/`)
**Total Files:** 35+

#### Core Authentication
- `test_auth_token_generation.py` - Token generation logic
- `test_auth_token_security.py` - Security validations
- `test_auth_token_validation.py` - Token validation
- `test_security.py` - Security features
- `test_session_management.py` - Session handling
- `test_session_cleanup.py` - Session cleanup

#### OAuth Integration
- `integration/test_auth_oauth_errors.py` - OAuth error handling
- `integration/test_auth_oauth_google.py` - Google OAuth
- `integration/test_oauth_flows_*.py` - OAuth flow tests

#### Infrastructure
- `config/test_env.py` - Environment configuration
- `config/test_settings.py` - Settings validation
- `database/test_config.py` - Database configuration
- `test_cloud_sql_url.py` - Cloud SQL connections

### 2. Main Backend (`/netra_backend/tests/`)
**Total Files:** 500+

#### Agent System Tests (`agents/`)
**SubAgent Tests:**
- `test_supervisor_*.py` (15 files) - Supervisor agent
- `test_triage_*.py` (10 files) - Triage agent
- `test_data_sub_agent_*.py` (6 files) - Data sub-agent
- `test_supply_researcher_*.py` (12 files) - Supply researcher
- `test_error_handler_*.py` (5 files) - Error handler
- `test_tool_dispatcher_*.py` (4 files) - Tool dispatcher

**LLM Agent Tests:**
- `test_llm_agent_*.py` (10 files) - Core LLM functionality
- `test_agent_e2e_critical_*.py` (5 files) - Critical E2E paths
- `test_production_tool*.py` - Production tools
- `test_mcp_integration.py` - MCP integration

#### ClickHouse Tests (`clickhouse/`)
**Total:** 40+ files
- `test_clickhouse_connection.py` - Connection management
- `test_clickhouse_performance.py` - Performance metrics
- `test_clickhouse_array_operations.py` - Array operations
- `test_corpus_*.py` (7 files) - Corpus management
- `test_realistic_*.py` (3 files) - Realistic data tests
- `test_llm_metrics_aggregation.py` - Metrics aggregation
- `test_time_series_analysis.py` - Time series analysis

#### Core Infrastructure (`core/`)
**Total:** 70+ files
- `test_async_*.py` (20 files) - Async utilities
- `test_data_validation_*.py` (6 files) - Data validation
- `test_reliability_mechanisms.py` - Reliability patterns
- `test_circuit_breaker.py` - Circuit breaker pattern
- `test_health_*.py` (3 files) - Health checking
- `test_error_*.py` (3 files) - Error handling
- `test_fallback_*.py` (2 files) - Fallback mechanisms

#### Critical Tests (`critical/`)
**Total:** 25+ files
- `test_websocket_*.py` (12 files) - WebSocket critical paths
- `test_auth_*.py` (3 files) - Auth critical paths
- `test_startup_*.py` - Startup validation
- `test_staging_integration_flow.py` - Staging environment

#### E2E Tests (`e2e/`)
**Total:** 80+ files
- `first_time_user/test_*.py` (6 files) - User journey tests
- `test_agent_*.py` (5 files) - Agent workflows
- `test_multi_constraint_*.py` (7 files) - Constraint optimization
- `test_latency_optimization_*.py` (2 files) - Performance
- `test_model_*.py` (4 files) - Model effectiveness
- `test_websocket_*.py` (4 files) - WebSocket integration

#### Integration Tests (`integration/`)
**Total:** 100+ files
- `critical_paths/test_*.py` (DELETED - 40 files)
- `coordination/test_*.py` (3 files) - Service coordination
- `security/test_*.py` (11 files) - Security integration
- `startup/test_*.py` (8 files) - Startup sequences
- `websocket/test_*.py` (15 files) - WebSocket integration

#### Service Tests (`services/`)
**Total:** 60+ files
- `test_agent_service_*.py` (DELETED - 5 files)
- `test_clickhouse_*.py` (DELETED - 5 files)
- `test_generation_service_*.py` (10 files) - Generation service
- `test_orchestration_*.py` (4 files) - Orchestration
- `test_thread_service_*.py` (3 files) - Thread management
- `test_websocket_*.py` (5 files) - WebSocket service

### 3. Frontend Tests (`/frontend/__tests__/`)
**Total Files:** 369+ test files
**Status:** ACTIVE - Comprehensive test coverage across all frontend components

#### Test Categories by Directory

##### Accessibility Tests (`a11y/`) - 14 files
- Component accessibility tests
- Form accessibility validation
- Navigation keyboard/screen reader tests
- WCAG compliance validation

##### Authentication Tests (`auth/`) - 14 files
- `auth-login.test.ts` - Login flow
- `auth-logout.test.ts` - Logout flow
- `auth-security.test.ts` - Security features
- `auth-session-detection.test.tsx` - Session management
- `auth-token-refresh-auto.test.tsx` - Token refresh
- `context.auth-operations.test.tsx` - Auth context operations
- `login-to-chat-advanced.test.tsx` - Auth to chat flow
- `logout-state-cleanup-complete.test.tsx` - State cleanup

##### Chat Tests (`chat/`) - 20 files
- `chat-authentication.test.tsx` - Chat auth integration
- `chatUIUX-*.test.tsx` - UI/UX components
- `message-content-*.test.tsx` - Message handling
- `message-exchange.test.tsx` - Message flow
- `thread-management.test.tsx` - Thread operations
- `keyboard-shortcuts.test.tsx` - Keyboard navigation
- `mcp-components.test.tsx` - MCP integration

##### Component Tests (`components/`) - 79 files
**Subdirectories:**
- `auth/` - Auth components
- `chat/` - Chat interface components
- `ChatHistorySection/` - History components
- `ChatSidebar/` - Sidebar components
- `MessageInput/` - Input components
- `ThreadList/` - Thread list components
- `ui/` - UI library components

##### Critical Path Tests (`critical/`) - 10 files
- `auth-flow/` - Critical auth flows
- `chat-functionality/` - Core chat features
- `chat-init/` - Chat initialization
- `first-load/` - First load performance
- `start-button/` - User onboarding

##### Integration Tests (`integration/`) - 141 files
**Major subdirectories:**
- `comprehensive/` - Full integration suites
  - `components/` - Component integration
  - `helpers/` - Test helpers
  - `performance-benchmarks/` - Performance tests
  - `utils/` - Integration utilities
- `advanced-integration/` - Advanced scenarios
- `critical/` - Critical integration paths
- Core integration test files:
  - `auth-flow-integration.test.tsx`
  - `logout-websocket.test.tsx`
  - `websocket-auth-integration.test.tsx`
  - `websocket-connection.test.tsx`

##### Other Test Categories
- `app/` - App-level tests
- `basic-chat/` - Basic chat functionality
- `cross-browser/` - Browser compatibility
- `e2e/` - End-to-end tests
- `first-time-user/` - User onboarding
- `helpers/` - Test helpers
- `hooks/` - React hooks tests
- `imports/` - Import validation
- `lib/` - Library tests
- `mobile/` - Mobile responsiveness
- `mocks/` - Mock utilities
- `performance/` - Performance tests
- `services/` - Service layer tests
- `setup/` - Test setup utilities
- `shared/` - Shared test utilities
- `startup/` - Startup validation
- `store/` - State management tests
- `system/` - System-level tests
- `types/` - TypeScript type tests
- `unified_system/` - Unified system tests
- `utils/` - Utility tests
- `visual/` - Visual regression tests

#### Cypress E2E Tests (`/frontend/cypress/`)
- `/frontend/cypress/e2e/` - Cypress E2E test specs
- `/frontend/cypress/fixtures/` - Test fixtures
- `/frontend/cypress/support/` - Test support files

### 4. Development Launcher (`/dev_launcher/tests/`)
**Total:** 18 files
- `test_launcher*.py` (6 files) - Launcher core
- `test_startup_*.py` (2 files) - Startup validation
- `test_health_*.py` (2 files) - Health checks
- `test_path_*.py` (2 files) - Path resolution

### 5. Legacy Integration Tests (`/legacy_integration_tests/`)
**Total:** 15 files
- `test_auth_flow_comprehensive_l3.py` - Auth flows
- `test_agent_orchestration_l3.py` - Agent orchestration
- `test_websocket_*.py` (3 files) - WebSocket legacy
- `test_e2e_*.py` (2 files) - E2E environments

## Test Categories

### Level 1: Unit Tests
- **Location:** `*/unit/`, individual test files
- **Pattern:** `test_<module>_<function>.py`
- **Focus:** Single function/class validation
- **Mock Usage:** Heavy mocking allowed

### Level 2: Integration Tests
- **Location:** `*/integration/`
- **Pattern:** `test_<service>_integration.py`
- **Focus:** Service interactions
- **Mock Usage:** Minimal mocking

### Level 3: Critical Path Tests
- **Location:** `*/critical/`, `*/critical_paths/`
- **Pattern:** `test_<feature>_critical.py`
- **Focus:** Business-critical flows
- **Mock Usage:** Real services preferred

### Level 4: E2E Tests
- **Location:** `*/e2e/`
- **Pattern:** `test_<workflow>_e2e.py`
- **Focus:** Complete user journeys
- **Mock Usage:** No mocking, real services

### Level 5: Performance Tests
- **Location:** Various, marked with `_performance`
- **Pattern:** `test_<feature>_performance.py`
- **Focus:** Latency, throughput, resource usage

## Test Runners & Commands

### Unified Test Runner
```bash
# Default (fast feedback)
python unified_test_runner.py --level integration --no-coverage --fast-fail

# Agent changes
python unified_test_runner.py --level agents --real-llm

# Pre-release (with staging)
python unified_test_runner.py --level integration --real-llm --env staging

# Specific service
python unified_test_runner.py --service auth
python unified_test_runner.py --service backend
python unified_test_runner.py --service frontend
```

### Service-Specific Commands
```bash
# Auth Service
cd auth_service && pytest tests/ -v

# Backend
cd netra_backend && pytest tests/ -v

# Frontend (Jest)
cd frontend && npm test
cd frontend && npm run test:coverage

# Frontend (Cypress)
cd frontend && npm run cypress:run

# Dev Launcher
cd dev_launcher && pytest tests/ -v
```

### Coverage Commands
```bash
# Generate coverage report
python unified_test_runner.py --coverage

# View coverage
python -m test_framework.coverage_report

# Check coverage requirements
python scripts/check_test_coverage.py
```

## Critical Test Paths

### 1. Authentication Flow
- `auth_service/tests/test_auth_token_*.py`
- `netra_backend/tests/critical/test_auth_*.py`
- `netra_backend/tests/e2e/first_time_user/test_real_critical_user_journey_e2e.py`

### 2. WebSocket Communication
- `netra_backend/tests/critical/test_websocket_*.py`
- `netra_backend/tests/integration/websocket/test_*.py`
- `netra_backend/tests/e2e/test_websocket_*.py`

### 3. Agent Orchestration
- `netra_backend/tests/agents/test_supervisor_*.py`
- `netra_backend/tests/agents/test_agent_e2e_critical_*.py`
- `netra_backend/tests/e2e/test_agent_orchestration_e2e.py`

### 4. Data Pipeline
- `netra_backend/tests/clickhouse/test_*.py`
- `netra_backend/tests/agents/test_data_sub_agent_*.py`
- `netra_backend/tests/services/test_generation_service_*.py`

### 5. System Startup
- `dev_launcher/tests/test_startup_*.py`
- `netra_backend/tests/critical/test_startup_*.py`
- `netra_backend/tests/integration/startup/test_*.py`

## Coverage Reports

### Current Coverage Status
```
Auth Service:      75% coverage
Backend Core:      82% coverage
Agent System:      78% coverage
WebSocket:         85% coverage
ClickHouse:        70% coverage
Frontend:          Jest coverage available
```

### Coverage Files
- `/test_reports/coverage/` - HTML coverage reports
- `/test_reports/coverage.xml` - XML coverage data
- `/.coverage` - Coverage database

### Coverage Requirements
- **Target:** 80% overall
- **Critical Paths:** 95% required
- **New Code:** 90% required

## Recently Deleted Tests

### Backend Tests (Deleted 2025-08-21)
- Integration critical paths (40 files)
- Service orchestration tests
- ClickHouse test helpers
- Agent service fixtures

### Cross-Service Tests (Deleted 2025-08-21)
- E2E WebSocket resilience
- Unified WebSocket tests
- Integration startup tests

## Test Framework Files

### Core Framework (`/test_framework/`)
- `test_runner.py` - Main test runner
- `test_index_manager.py` - Test indexing
- `test_index_report.py` - Index reporting
- `test_selector.py` - Test selection logic
- `coverage_analyzer.py` - Coverage analysis

### Test Utilities
- `/netra_backend/tests/helpers/` - Backend test helpers
- `/netra_backend/tests/fixtures/` - Test fixtures
- `/auth_service/tests/utils/` - Auth test utilities
- `/auth_service/tests/factories/` - Test factories

### Configuration Files
- `pytest.ini` - Pytest configuration
- `pytest.skip` - Tests to skip
- `.coveragerc` - Coverage configuration
- `cypress.config.ts` - Cypress configuration

## Test Patterns & Best Practices

### Naming Conventions
- **Unit:** `test_<module>_<function>.py`
- **Integration:** `test_<service>_integration.py`
- **E2E:** `test_<workflow>_e2e.py`
- **Critical:** `test_<feature>_critical.py`
- **Performance:** `test_<feature>_performance.py`

### Test Structure
```python
# Standard test structure
def test_<descriptive_name>():
    # Arrange
    # Act
    # Assert
    
# Async test structure
async def test_<descriptive_name>():
    # Arrange
    # Act
    # Assert
```

### Mock vs Real
- **Unit Tests:** Mock external dependencies
- **Integration:** Use test databases/services
- **E2E:** Use real services (dev/staging)
- **Critical:** Always use real services

## Maintenance & Updates

### Adding New Tests
1. Choose appropriate location based on service
2. Follow naming conventions
3. Update this index
4. Run coverage check
5. Ensure CI passes

### Removing Tests
1. Document reason for removal
2. Update this index
3. Check coverage impact
4. Archive if needed

### Test Health Monitoring
- Check `/test_reports/` for latest results
- Monitor CI/CD pipeline status
- Review coverage trends
- Track flaky tests

## Quick Reference

### Most Important Test Files
1. `netra_backend/tests/critical/test_websocket_execution_engine.py`
2. `netra_backend/tests/agents/test_supervisor_consolidated_core.py`
3. `auth_service/tests/test_auth_token_validation.py`
4. `netra_backend/tests/e2e/test_real_agent_orchestration_e2e.py`
5. `netra_backend/tests/clickhouse/test_clickhouse_connection.py`

### Frequently Run Test Suites
```bash
# Quick smoke test
pytest -m smoke --fast-fail

# Agent system
pytest netra_backend/tests/agents/ -v

# WebSocket critical
pytest netra_backend/tests/critical/test_websocket*.py

# Auth flow
pytest auth_service/tests/test_auth*.py

# E2E user journey
pytest netra_backend/tests/e2e/first_time_user/
```

## Contact & Support

**Test Framework Issues:** See `/test_framework/README.md`
**Coverage Questions:** Check `/SPEC/coverage_requirements.xml`
**CI/CD Issues:** See `/.github/workflows/`
**Test Documentation:** `/SPEC/testing.xml`

---

*This index is maintained as part of the Netra Apex testing infrastructure. Update after significant test changes.*