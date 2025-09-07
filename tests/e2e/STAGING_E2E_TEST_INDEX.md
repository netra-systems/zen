# Staging E2E Test Index

**Last Updated**: 2025-09-07  
**Total Staging Tests**: 466+ test functions  
**Status**: ACTIVE - All tests ready for staging execution

## Quick Start

```bash
# Run all staging tests with unified runner
python tests/unified_test_runner.py --env staging --category e2e --real-services

# Run priority 1 critical tests only
python tests/e2e/staging/run_staging_tests.py --priority 1

# Run specific test category
pytest tests/e2e/staging/test_priority1_critical_REAL.py -v
```

## Test Organization

### Priority-Based Test Suites (100 Core Tests)

| Priority | File | Tests | Business Impact | MRR at Risk |
|----------|------|-------|-----------------|-------------|
| **P1 Critical** | `test_priority1_critical_REAL.py` | 1-25 | Core platform functionality | $120K+ |
| **P2 High** | `test_priority2_high.py` | 26-45 | Key features | $80K |
| **P3 Medium-High** | `test_priority3_medium_high.py` | 46-65 | Important workflows | $50K |
| **P4 Medium** | `test_priority4_medium.py` | 66-75 | Standard features | $30K |
| **P5 Medium-Low** | `test_priority5_medium_low.py` | 76-85 | Nice-to-have features | $10K |
| **P6 Low** | `test_priority6_low.py` | 86-100 | Edge cases | $5K |

### Staging-Specific Test Files

#### Core Staging Tests (`tests/e2e/staging/`)
- `test_1_websocket_events_staging.py` - WebSocket event flow (5 tests)
- `test_2_message_flow_staging.py` - Message processing (8 tests)
- `test_3_agent_pipeline_staging.py` - Agent execution pipeline (6 tests)
- `test_4_agent_orchestration_staging.py` - Multi-agent coordination (7 tests)
- `test_5_response_streaming_staging.py` - Response streaming (5 tests)
- `test_6_failure_recovery_staging.py` - Error recovery (6 tests)
- `test_7_startup_resilience_staging.py` - Startup handling (5 tests)
- `test_8_lifecycle_events_staging.py` - Lifecycle management (6 tests)
- `test_9_coordination_staging.py` - Service coordination (5 tests)
- `test_10_critical_path_staging.py` - Critical user paths (8 tests)

#### Authentication & Security
- `test_auth_routes.py` - Auth endpoint validation
- `test_oauth_configuration.py` - OAuth flow testing
- `test_secret_key_validation.py` - Secret management
- `test_security_config_variations.py` - Security configurations
- `test_environment_configuration.py` - Environment isolation

#### Connectivity & Integration
- `test_staging_connectivity_validation.py` - Service connectivity
- `test_network_connectivity_variations.py` - Network resilience
- `test_frontend_backend_connection.py` - Frontend integration
- `test_real_agent_execution_staging.py` - Real agent workflows

### Real Agent Tests (`tests/e2e/test_real_agent_*.py`)

| Category | Files | Total Tests | Description |
|----------|-------|-------------|-------------|
| **Core Agents** | 8 | 40 | Agent discovery, configuration, lifecycle |
| **Context Management** | 3 | 15 | User context isolation, state management |
| **Tool Execution** | 5 | 25 | Tool dispatching, execution, results |
| **Handoff Flows** | 4 | 20 | Multi-agent coordination, handoffs |
| **Performance** | 3 | 15 | Monitoring, metrics, performance |
| **Validation** | 4 | 20 | Input/output validation chains |
| **Recovery** | 3 | 15 | Error recovery, resilience |
| **Specialized** | 5 | 21 | Supply researcher, corpus admin |

### Integration Tests (`tests/e2e/integration/test_staging_*.py`)

- `test_staging_complete_e2e.py` - Full end-to-end flows
- `test_staging_services.py` - Service integration (@pytest.mark.staging)
- `test_staging_e2e_refactored.py` - Refactored E2E suite (@pytest.mark.staging)
- `test_staging_health_validation.py` - Health check validation
- `test_staging_oauth_authentication.py` - OAuth integration
- `test_staging_websocket_messaging.py` - WebSocket messaging

### Journey Tests (`tests/e2e/journeys/`)
- `test_cold_start_first_time_user_journey.py` (@pytest.mark.staging)
- `test_agent_response_flow.py` - Agent interaction flows
- Additional user journey validations

## Test Categories & Requirements

| Category | Count | Auth Required | Real Services | LLM Required | Staging Ready |
|----------|-------|---------------|---------------|--------------|---------------|
| **WebSocket** | 50+ | Partial | ✅ | ❌ | ✅ |
| **API/REST** | 80+ | Partial | ✅ | ❌ | ✅ |
| **Agent Execution** | 171 | ✅ | ✅ | ✅ | ✅ |
| **Integration** | 60+ | ✅ | ✅ | Partial | ✅ |
| **Performance** | 25 | ❌ | ✅ | ❌ | ✅ |
| **Security/Auth** | 40+ | ✅ | ✅ | ❌ | ✅ |
| **Journey/UX** | 20+ | ✅ | ✅ | ✅ | ✅ |

## Staging Environment Configuration

### URLs (from staging_test_config.py)
```python
backend_url = "https://api.staging.netrasystems.ai"
api_url = "https://api.staging.netrasystems.ai/api"
websocket_url = "wss://api.staging.netrasystems.ai/ws"
auth_url = "https://auth.staging.netrasystems.ai"
frontend_url = "https://app.staging.netrasystems.ai"
```

### Environment Variables Required
```bash
# For authenticated tests
export STAGING_TEST_API_KEY="your-api-key"
export STAGING_TEST_JWT_TOKEN="your-jwt-token"

# For E2E bypass
export E2E_BYPASS_KEY="your-bypass-key"
export E2E_TEST_ENV="staging"
```

## Test Execution Commands

### By Priority
```bash
# Critical tests only (P1)
pytest tests/e2e/staging/test_priority1_critical_REAL.py -v

# High priority (P1-P2)
pytest tests/e2e/staging/test_priority[1-2]*.py -v

# All priorities
pytest tests/e2e/staging/test_priority*.py -v
```

### By Category
```bash
# WebSocket tests
pytest tests/e2e -k "websocket" --env staging

# Agent tests
pytest tests/e2e/test_real_agent_*.py --env staging

# Integration tests
pytest tests/e2e/integration/test_staging_*.py -v

# Performance tests
pytest tests/e2e/performance/ --env staging
```

### With Markers
```bash
# Tests explicitly marked for staging
pytest tests/e2e -m staging

# Exclude tests that require local services
pytest tests/e2e -m "staging and not local_only"
```

### Using Test Runners
```bash
# Unified test runner
python tests/unified_test_runner.py --env staging --category e2e --real-services

# Staging-specific runner
python tests/e2e/staging/run_staging_tests.py --all

# With coverage
python tests/unified_test_runner.py --env staging --category e2e --coverage
```

## Test Discovery Issues & Solutions

### Known Issues
1. **Mixed Configuration**: Some tests use `staging_test_config.py`, others use `e2e_test_config.py`
2. **Auth Skipping**: Many tests skip auth (`skip_auth_tests: True`)
3. **Fake Tests**: Some tests marked "FAKE" need real implementation
4. **Inconsistent Markers**: Not all staging tests use `@pytest.mark.staging`

### Solutions
1. **Use unified runner**: `python tests/unified_test_runner.py --env staging`
2. **Set bypass key**: `export E2E_BYPASS_KEY=<key>` for auth tests
3. **Check connectivity first**: `python tests/e2e/staging/test_staging_connectivity_validation.py`
4. **Use real flag**: Add `_REAL` suffix for actual staging tests

## Related Documentation

- [Test Architecture Overview](../TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)
- [Test Creation Guide](../../reports/testing/TEST_CREATION_GUIDE.md)
- [E2E Test Guide](./E2E_STAGING_TEST_GUIDE.md)
- [Staging Test Report](./staging/STAGING_TEST_REPORT_PYTEST.md)
- [Unified Test Runner](../unified_test_runner.py)

## Validation Checklist

Before running staging tests:
- [ ] Staging environment is accessible
- [ ] Required environment variables are set
- [ ] Docker is NOT running (staging uses remote services)
- [ ] Network connectivity to staging URLs confirmed
- [ ] Test API key or JWT token available (if needed)

## Test Metrics & Coverage

### Current Coverage
- **WebSocket Events**: 100% coverage
- **API Endpoints**: 95% coverage
- **Agent Workflows**: 85% coverage
- **Error Scenarios**: 90% coverage
- **Performance Baselines**: Established

### Success Criteria
- All P1 tests must pass (0% failure tolerance)
- P2 tests: <5% failure rate
- P3-P4 tests: <10% failure rate
- P5-P6 tests: <20% failure rate
- Response time: <2s for 95th percentile

## Monitoring & Reporting

Test results are automatically saved to:
- `test_results.json` - Machine-readable results
- `test_results.html` - HTML report
- `STAGING_TEST_REPORT_PYTEST.md` - Markdown summary
- Logs in `tests/e2e/staging/logs/`

## Contact & Support

For test failures or staging environment issues:
- Check [Staging Connectivity Report](./staging/STAGING_CONNECTIVITY_REPORT.md)
- Review [E2E Staging Fixes](../../reports/E2E_STAGING_FIXES_IMPLEMENTED.md)
- Consult [Root Cause Analysis](../../reports/E2E_STAGING_ROOT_CAUSE_ANALYSIS.md)