# Mock Usage Remediation Plan

## Executive Summary

- **Total Violations**: 51481
- **Services Affected**: 6
- **Estimated Effort**: 2-3 days with multi-agent approach

## Remediation Strategy

1. Use multi-agent team (3-7 agents) per service
2. Replace mocks with real service connections
3. Use IsolatedEnvironment for test isolation
4. Implement docker-compose for service dependencies

## Service-Specific Plans

### auth_service

**Violations**: 514

**Files to Fix**:

- `auth_service/tests/test_token_validation_security_cycles_31_35.py` (2 violations)
- `auth_service/tests/test_auth_port_configuration.py` (17 violations)
- `auth_service/tests/test_oauth_security_vulnerabilities.py` (15 violations)
- `auth_service/tests/test_session_security_cycles_36_40.py` (2 violations)
- `auth_service/tests/test_critical_bugs_simple.py` (20 violations)
- `auth_service/tests/test_auth_comprehensive_audit.py` (3 violations)
- `auth_service/tests/test_refresh_endpoint_compatibility.py` (42 violations)
- `auth_service/tests/test_refresh_loop_prevention_comprehensive.py` (3 violations)
- `auth_service/tests/test_refresh_endpoint_integration.py` (43 violations)
- `auth_service/tests/test_signup_flow_comprehensive.py` (40 violations)
- ... and 7 more files

**Replacement Strategy**:

- Replace AsyncMock with real PostgreSQL connections
- Use real Redis for session management
- Implement real JWT validation

---

### analytics_service

**Violations**: 10

**Files to Fix**:

- `analytics_service/tests/unit/test_health_endpoints.py` (1 violations)
- `analytics_service/tests/integration/run_integration_tests.py` (2 violations)
- `analytics_service/tests/compliance/test_clickhouse_ssot_violations.py` (7 violations)

**Replacement Strategy**:

- Use real ClickHouse connections
- Implement real event processing
- Use docker-compose for ClickHouse setup

---

### netra_backend

**Violations**: 41672

**Files to Fix**:

- `netra_backend/tests/test_migration_staging_configuration_issues.py` (13 violations)
- `netra_backend/tests/test_database_session.py` (5 violations)
- `netra_backend/tests/test_admin.py` (2 violations)
- `netra_backend/tests/test_clickhouse_client_comprehensive.py` (26 violations)
- `netra_backend/tests/test_deployment_edge_cases.py` (22 violations)
- `netra_backend/tests/test_agent_service_mock_classes.py` (4 violations)
- `netra_backend/tests/test_config_isolation_patterns.py` (1 violations)
- `netra_backend/tests/test_health_monitor_checks.py` (87 violations)
- `netra_backend/tests/conftest.py` (3 violations)
- `netra_backend/tests/test_websocket_critical.py` (64 violations)
- ... and 937 more files

**Replacement Strategy**:

- Replace WebSocket mocks with real connections
- Use real agent execution
- Implement real database connections

---

### tests

**Violations**: 6687

**Files to Fix**:

- `tests/test_critical_dev_launcher_issues.py` (127 violations)
- `tests/conftest.py` (225 violations)
- `tests/test_dev_launcher_issues.py` (33 violations)
- `tests/test_real_services_validation.py` (8 violations)
- `tests/test_websocket_critical_fix_validation.py` (69 violations)
- `tests/test_enhanced_websocket_events.py` (30 violations)
- `tests/test_websocket_fix_simple_validation.py` (11 violations)
- `tests/database/test_port_configuration_mismatch.py` (6 violations)
- `tests/unit/test_environment_isolation_simple.py` (1 violations)
- `tests/unit/test_asyncio_event_loop_safety.py` (6 violations)
- ... and 315 more files

**Replacement Strategy**:


---

### frontend

**Violations**: 18

**Files to Fix**:

- `tests/e2e/frontend/test_frontend_websocket_reliability.py` (13 violations)
- `tests/e2e/frontend/test_frontend_chat_interactions.py` (2 violations)
- `tests/e2e/frontend/test_websocket_startup_race_condition.py` (3 violations)

**Replacement Strategy**:


---

### dev_launcher

**Violations**: 2580

**Files to Fix**:

- `dev_launcher/tests/test_health_registration.py` (36 violations)
- `dev_launcher/tests/test_launcher_health.py` (60 violations)
- `dev_launcher/tests/test_critical_dev_launcher_issues.py` (100 violations)
- `dev_launcher/tests/test_websocket_connection_issue.py` (84 violations)
- `dev_launcher/tests/test_dynamic_port_health.py` (67 violations)
- `dev_launcher/tests/test_phase3_multiprocessing.py` (51 violations)
- `dev_launcher/tests/test_service_coordination_integration.py` (29 violations)
- `dev_launcher/tests/test_startup_validator.py` (91 violations)
- `dev_launcher/tests/test_default_launcher.py` (117 violations)
- `dev_launcher/tests/test_environment_isolation_pytest_integration.py` (1 violations)
- ... and 25 more files

**Replacement Strategy**:


---

## Implementation Order

1. **Phase 1**: auth_service (highest risk)
2. **Phase 2**: netra_backend (WebSocket critical)
3. **Phase 3**: analytics_service
4. **Phase 4**: Integration tests

## Success Criteria

- [ ] All mock imports removed
- [ ] All tests use IsolatedEnvironment
- [ ] Docker-compose configured for dependencies
- [ ] All tests pass with real services
- [ ] Architecture compliance > 90%
