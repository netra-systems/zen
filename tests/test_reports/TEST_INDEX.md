# Test Index Report

*Generated: 2025-08-18T14:07:11.994214*

## Summary
- **Total Test Modules**: 52
- **Backend Tests**: 26
- **Frontend Tests**: 18
- **E2E Tests**: 8

## Test Levels

| Level | Time | Purpose | Command |
|-------|------|---------|---------|
| **integration** | 3-5min | **DEFAULT** - Feature validation | `python test_runner.py --level integration --no-coverage --fast-fail` |
| **unit** | 1-2min | Component testing | `python test_runner.py --level unit` |
| **smoke** | <30s | Pre-commit validation | `python test_runner.py --level smoke` |
| **agents** | 2-3min | Agent testing | `python test_runner.py --level agents` |
| **critical** | 1-2min | Essential paths | `python test_runner.py --level critical` |
| **real_e2e** | 15-20min | Real LLM testing | `python test_runner.py --level real_e2e --real-llm` |
| **comprehensive** | 30-45min | Full validation | `python test_runner.py --level comprehensive` |

## Test Categories

| Category | Description | Expected | Status |
|----------|-------------|----------|--------|
| **smoke** | Quick smoke tests | 10 | Pending |
| **unit** | Unit tests | 450 | Pending |
| **integration** | Integration tests | 60 | Pending |
| **critical** | Critical path tests | 20 | Pending |
| **agents** | Agent tests | 45 | Pending |
| **websocket** | WebSocket tests | 25 | Pending |
| **database** | Database tests | 35 | Pending |
| **api** | API tests | 50 | Pending |
| **e2e** | End-to-end tests | 20 | Pending |
| **real_services** | Real service tests | 15 | Pending |
| **auth** | Authentication tests | 30 | Pending |
| **corpus** | Corpus management tests | 20 | Pending |
| **synthetic_data** | Synthetic data tests | 25 | Pending |
| **metrics** | Metrics tests | 15 | Pending |
| **frontend** | Frontend tests | 40 | Pending |
| **comprehensive** | Full comprehensive suite | 500 | Pending |

## Test Catalog

### Backend Tests

#### Unit
- test_auth_middleware
- test_websocket_manager
- test_database_operations
- test_llm_client
- test_agent_base
- test_repositories
- test_schemas
- test_core_utilities

#### Integration
- test_auth_flow
- test_websocket_integration
- test_agent_workflow
- test_database_integration
- test_api_endpoints
- test_service_integration

#### Critical
- test_critical_auth
- test_critical_data_flow
- test_critical_agent_execution
- test_critical_websocket

#### Smoke
- test_smoke_health
- test_smoke_database
- test_smoke_auth

#### Agents
- test_triage_agent
- test_data_agent
- test_reporting_agent
- test_analyzer_agent
- test_executor_agent

### Frontend Tests

#### Unit
- ChatInterface.test
- AuthProvider.test
- useWebSocket.test
- apiClient.test

#### Integration
- auth-flow.test
- collaboration-state.test
- tool-lifecycle.test
- comprehensive-integration.test

#### Components
- ChatHistorySection.test
- MessageList.test
- InputArea.test
- SettingsPanel.test

#### Hooks
- usePerformanceMetrics.test
- useAuth.test
- useChat.test

#### Startup
- startup-environment.test
- startup-initialization.test
- startup-system.test

### E2e Tests

#### Cypress
- user-journey.cy
- auth-flow.cy
- chat-interaction.cy

#### Real_llm
- test_real_agent_workflow
- test_real_llm_integration
- test_real_service_integration

#### Mock
- test_mock_e2e_flow
- test_mock_agent_interaction

## Statistics

### By Category
| Category | Count |
|----------|-------|
| unit | 12 |
| integration | 10 |
| critical | 4 |
| smoke | 3 |
| agents | 5 |
| components | 4 |
| hooks | 3 |
| startup | 3 |
| cypress | 3 |
| real_llm | 3 |
| mock | 2 |

### By Component
| Component | Count |
|-----------|-------|
| backend | 26 |
| frontend | 18 |
| e2e | 8 |
