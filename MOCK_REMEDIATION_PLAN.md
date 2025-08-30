# Mock Usage Remediation Plan

## Executive Summary

- **Total Violations**: 16165
- **Services Affected**: 6
- **Estimated Effort**: 2-3 days with multi-agent approach

## Remediation Strategy

1. Use multi-agent team (3-7 agents) per service
2. Replace mocks with real service connections
3. Use IsolatedEnvironment for test isolation
4. Implement docker-compose for service dependencies

## Service-Specific Plans

### auth_service

**Violations**: 222

**Files to Fix**:

- `auth_service/tests/test_auth_comprehensive.py` (10 violations)
- `auth_service/tests/conftest.py` (2 violations)
- `auth_service/tests/test_token_validation_security_cycles_31_35.py` (2 violations)
- `auth_service/tests/test_auth_port_configuration.py` (3 violations)
- `auth_service/tests/test_critical_bugs.py` (14 violations)
- `auth_service/tests/test_oauth_security_vulnerabilities.py` (4 violations)
- `auth_service/tests/test_session_security_cycles_36_40.py` (2 violations)
- `auth_service/tests/test_critical_bugs_simple.py` (6 violations)
- `auth_service/tests/test_redis_staging_fixes.py` (8 violations)
- `auth_service/tests/test_auth_comprehensive_audit.py` (3 violations)
- ... and 13 more files

**Replacement Strategy**:

- Replace AsyncMock with real PostgreSQL connections
- Use real Redis for session management
- Implement real JWT validation

---

### analytics_service

**Violations**: 163

**Files to Fix**:

- `analytics_service/tests/unit/test_isolated_environment.py` (2 violations)
- `analytics_service/tests/unit/test_event_processor.py` (10 violations)
- `analytics_service/tests/unit/test_config.py` (8 violations)
- `analytics_service/tests/unit/test_health_endpoints.py` (120 violations)
- `analytics_service/tests/unit/test_main.py` (20 violations)
- `analytics_service/tests/unit/test_event_ingestion.py` (3 violations)

**Replacement Strategy**:

- Use real ClickHouse connections
- Implement real event processing
- Use docker-compose for ClickHouse setup

---

### netra_backend

**Violations**: 13385

**Files to Fix**:

- `netra_backend/tests/test_migration_staging_configuration_issues.py` (4 violations)
- `netra_backend/tests/test_database_session.py` (5 violations)
- `netra_backend/tests/test_admin.py` (2 violations)
- `netra_backend/tests/test_clickhouse_client_comprehensive.py` (7 violations)
- `netra_backend/tests/test_deployment_edge_cases.py` (8 violations)
- `netra_backend/tests/test_agent_service_mock_classes.py` (4 violations)
- `netra_backend/tests/test_health_monitor_checks.py` (20 violations)
- `netra_backend/tests/conftest.py` (3 violations)
- `netra_backend/tests/test_websocket_critical.py` (18 violations)
- `netra_backend/tests/test_chat_content_validation.py` (59 violations)
- ... and 1062 more files

**Replacement Strategy**:

- Replace WebSocket mocks with real connections
- Use real agent execution
- Implement real database connections

---

### tests

**Violations**: 1637

**Files to Fix**:

- `tests/test_critical_dev_launcher_issues.py` (42 violations)
- `tests/conftest.py` (51 violations)
- `tests/test_dev_launcher_issues.py` (10 violations)
- `tests/database/test_port_configuration_mismatch.py` (2 violations)
- `tests/unit/test_environment_isolation_simple.py` (1 violations)
- `tests/unit/test_asyncio_event_loop_safety.py` (4 violations)
- `tests/unit/test_unified_env_loading.py` (3 violations)
- `tests/unit/test_api_versioning_fix.py` (13 violations)
- `tests/unit/test_environment_isolation_thread_safety.py` (1 violations)
- `tests/unit/test_jwt_asyncio_safety.py` (3 violations)
- ... and 230 more files

**Replacement Strategy**:


---

### frontend

**Violations**: 5

**Files to Fix**:

- `tests/e2e/frontend/test_frontend_chat_interactions.py` (2 violations)
- `tests/e2e/frontend/test_websocket_startup_race_condition.py` (3 violations)

**Replacement Strategy**:


---

### dev_launcher

**Violations**: 753

**Files to Fix**:

- `dev_launcher/tests/test_health_registration.py` (9 violations)
- `dev_launcher/tests/test_launcher_health.py` (17 violations)
- `dev_launcher/tests/test_critical_dev_launcher_issues.py` (34 violations)
- `dev_launcher/tests/test_websocket_connection_issue.py` (21 violations)
- `dev_launcher/tests/test_dynamic_port_health.py` (16 violations)
- `dev_launcher/tests/test_phase3_multiprocessing.py` (19 violations)
- `dev_launcher/tests/test_service_coordination_integration.py` (9 violations)
- `dev_launcher/tests/test_startup_validator.py` (40 violations)
- `dev_launcher/tests/test_default_launcher.py` (46 violations)
- `dev_launcher/tests/test_environment_isolation_pytest_integration.py` (1 violations)
- ... and 24 more files

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
