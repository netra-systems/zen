# E2E Test Scan Report
Generated: 2025-08-29T10:24:28.231743

## Summary
- Files with issues: 485
- Total issues found: 888
- Total fixes applied: 429

## Issues Found
- class_without_test_prefix: 225
- function_without_test_prefix: 98
- missing_imports: 4
- missing_markers: 23
- mock_usage_in_e2e: 93
- no_test_functions: 445

## Fixes Applied
### Class Names Fixed
- tests\e2e\test_agent_context_accumulation.py
- tests\e2e\test_agent_lifecycle_websocket_events.py
- tests\e2e\test_agent_orchestration.py
- tests\e2e\test_agent_responses_comprehensive_e2e.py
- tests\e2e\test_agent_startup_coverage_validation.py
- ... and 164 more

### Markers Added
- tests\e2e\test_auth_flow_comprehensive.py
- tests\e2e\test_auth_refresh_flow.py
- tests\e2e\test_auth_service_port_configuration_consistency.py
- tests\e2e\test_complete_system_health_validation.py
- tests\e2e\test_complete_system_startup_health_validation.py
- ... and 49 more

### Mocks Removed
- tests\e2e\test_agent_billing_flow.py
- tests\e2e\test_agent_circuit_breaker_e2e.py
- tests\e2e\test_agent_collaboration_real.py
- tests\e2e\test_agent_context_accumulation.py
- tests\e2e\test_agent_context_isolation_integration.py
- ... and 201 more

## Remaining Issues
- Files without test functions: 445