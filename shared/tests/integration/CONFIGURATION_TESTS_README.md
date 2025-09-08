# Configuration Management Integration Tests

## Overview

This directory contains comprehensive integration tests for configuration management and environment isolation, which are critical for deployment stability and configuration correctness. The tests prevent configuration cascade failures that have caused production outages.

## Business Value Justification (BVJ)

- **Segment**: Platform/Internal - System Stability & Deployment Reliability
- **Business Goal**: Prevent configuration cascade failures that cause complete system outages
- **Value Impact**: Configuration errors have caused 100% service outages (SERVICE_SECRET missing, wrong domains)
- **Strategic Impact**: Deployment stability, environment isolation, and configuration correctness are critical for multi-environment reliability

## Test Files

### 1. `test_configuration_management_critical_integration.py`

**Primary Test Suite (15 comprehensive integration tests)**

Tests critical configuration management scenarios:

#### Core Tests:
- `test_isolated_environment_mandatory_usage()` - Validates IsolatedEnvironment enforcement 
- `test_service_secret_missing_cascade_failure_prevention()` - Prevents SERVICE_SECRET cascade failures
- `test_service_id_stability_requirement()` - Validates SERVICE_ID stability 
- `test_frontend_critical_environment_variables_validation()` - Frontend env var validation
- `test_staging_domain_configuration_validation()` - Staging domain correctness
- `test_cors_configuration_validation()` - CORS configuration validation
- `test_discovery_endpoint_localhost_prevention()` - Discovery endpoint validation
- `test_multi_environment_configuration_isolation()` - Environment isolation testing
- `test_configuration_validation_integration()` - SSOT validator integration
- `test_port_discovery_and_allocation()` - Port conflict prevention
- `test_secret_loading_and_masking()` - Secret security validation
- `test_configuration_change_tracking()` - Configuration change auditing
- `test_configuration_validation_error_reporting()` - Error reporting validation
- `test_environment_specific_behavior_validation()` - Environment-specific validation

**Key Features:**
- Real configuration systems integration (NO MOCKS)
- IsolatedEnvironment usage patterns and enforcement
- Critical environment variables from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
- Multi-environment configuration isolation (dev/staging/prod)
- Configuration cascade failure prevention scenarios

### 2. `test_configuration_regression_prevention.py`

**Regression Prevention Test Suite (9 targeted regression tests)**

Tests specific regression scenarios from documented incidents:

#### Incident-Based Tests:
- `test_service_secret_missing_regression_2025_09_05()` - Prevents SERVICE_SECRET outage (2025-09-05)
- `test_service_id_timestamp_suffix_regression_2025_09_07()` - Prevents SERVICE_ID auth failures (2025-09-07)
- `test_frontend_env_vars_missing_regression_2025_09_03()` - Prevents frontend var missing (2025-09-03)
- `test_discovery_endpoint_localhost_regression_2025_09_02()` - Prevents localhost discovery (2025-09-02)
- `test_staging_domain_confusion_regression()` - Prevents domain confusion
- `test_websocket_run_id_missing_regression_2025_09_03()` - Prevents WebSocket message failures
- `test_agent_execution_order_regression_2025_09_05()` - Prevents agent order issues
- `test_comprehensive_regression_detection()` - Multi-issue detection
- `test_configuration_cascade_failure_prevention()` - Cascade failure prevention

**Key Features:**
- Targets exact configuration patterns that caused production outages
- Validates specific error detection and reporting
- Tests cascade failure prevention mechanisms
- Ensures incident patterns never recur

### 3. `run_configuration_tests.py`

**Test Runner Script**

Provides easy execution of the configuration test suite:

```bash
# Run all tests
python shared/tests/integration/run_configuration_tests.py

# Run with verbose output
python shared/tests/integration/run_configuration_tests.py --verbose

# Run specific test pattern
python shared/tests/integration/run_configuration_tests.py --test-pattern "*regression*"

# Validate test structure only
python shared/tests/integration/run_configuration_tests.py --validate-only
```

## Critical Scenarios Tested

### From MISSION_CRITICAL_NAMED_VALUES_INDEX.xml Incident History:

1. **SERVICE_SECRET Missing (2025-09-05)**
   - **Impact**: Complete system outage, 100% authentication failure
   - **Pattern**: Missing SERVICE_SECRET → Auth failure → Circuit breaker open → System unusable
   - **Prevention**: `test_service_secret_missing_cascade_failure_prevention()`

2. **SERVICE_ID Timestamp Suffix (2025-09-07)**
   - **Impact**: Authentication failures every 60 seconds
   - **Pattern**: SERVICE_ID with timestamps → Auth service mismatch → Recurring failures
   - **Prevention**: `test_service_id_stability_requirement()`

3. **Frontend Environment Variables Missing (2025-09-03)**
   - **Impact**: Complete frontend failure, no WebSocket, no auth
   - **Pattern**: Missing NEXT_PUBLIC_* vars → No API calls → No user access
   - **Prevention**: `test_frontend_critical_environment_variables_validation()`

4. **Discovery Endpoint Localhost URLs (2025-09-02)**
   - **Impact**: Frontend unable to connect to services
   - **Pattern**: Localhost URLs in staging → Service unreachable → Connection failures
   - **Prevention**: `test_discovery_endpoint_localhost_prevention()`

5. **Wrong Staging Subdomain Usage**
   - **Impact**: API calls fail, WebSocket connections fail
   - **Pattern**: staging.netrasystems.ai vs api.staging.netrasystems.ai confusion
   - **Prevention**: `test_staging_domain_configuration_validation()`

## Supporting Infrastructure

### Enhanced Test Framework Components:

1. **IsolatedTestHelper** (`test_framework/ssot/isolated_test_helper.py`)
   - Manages isolated environment contexts for testing
   - Prevents test pollution and configuration leakage
   - Supports multiple concurrent isolated contexts

2. **EnvironmentValidator** (`shared/isolated_environment.py`)
   - Extended with configuration validation methods
   - Validates critical service variables
   - Checks for known regression patterns
   - Provides detailed error reporting with remediation guidance

3. **TestConfigurationValidator** (`test_framework/ssot/configuration_validator.py`)
   - SSOT configuration validation patterns
   - Service-specific configuration requirements
   - Port allocation and conflict detection
   - Environment isolation validation

## Usage Patterns

### Running Tests Locally

```bash
# Standard integration test execution
python tests/unified_test_runner.py --category integration --real-services

# Configuration-specific tests  
python shared/tests/integration/run_configuration_tests.py

# Regression tests only
python shared/tests/integration/run_configuration_tests.py --test-pattern "*regression*"
```

### CI/CD Integration

These tests should be run in CI/CD pipelines before deployment to prevent configuration regressions:

```bash
# Pre-deployment validation
python shared/tests/integration/run_configuration_tests.py --validate-only

# Full configuration validation
python shared/tests/integration/run_configuration_tests.py
```

### Test Environment Requirements

- IsolatedEnvironment system properly configured
- Test framework dependencies available
- No circular import issues with logging
- Proper Python path setup for shared modules

## Test Architecture

### Isolation Patterns

All tests use the IsolatedEnvironment pattern to ensure:
- No cross-test pollution
- Environment variable isolation 
- Multi-user context separation
- Clean test state management

### Real Systems Integration

Following TEST_CREATION_GUIDE.md patterns:
- Real configuration systems (NO MOCKS in integration tests)
- Real IsolatedEnvironment usage
- Real configuration validation
- Real error detection and reporting

### SSOT Compliance

Tests follow SSOT (Single Source of Truth) patterns:
- Use shared configuration validators
- Import from test_framework/ssot/ modules
- Follow established test categorization
- Use proper Business Value Justification (BVJ) documentation

## Error Detection and Prevention

### Cascade Failure Prevention

The tests prevent configuration cascade failures by validating:
- Critical environment variables are present
- Service discovery endpoints are correct for environment
- Domain configurations match environment expectations
- Authentication configuration is stable and complete
- Frontend environment variables enable proper connectivity

### Regression Detection

Each regression test targets a specific incident pattern:
- Exact configuration scenarios that caused outages
- Specific error messages and detection patterns
- Cascade failure sequences that lead to system-wide failures
- Environment-specific configuration requirements

## Maintenance

### Adding New Tests

When adding configuration tests:

1. Follow the existing pattern in `test_configuration_management_critical_integration.py`
2. Use IsolatedTestHelper for environment isolation
3. Include Business Value Justification (BVJ) in docstrings
4. Target real configuration integration behavior
5. Add regression tests for new incidents in `test_configuration_regression_prevention.py`

### Updating for New Incidents

When configuration incidents occur:

1. Document the incident in MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
2. Create a specific regression test targeting the exact failure pattern
3. Validate the test catches the configuration issue
4. Ensure the test prevents recurrence

## Integration with Broader Test Suite

These configuration integration tests complement:
- Unit tests for individual configuration components
- E2E tests for full deployment validation
- Staging environment validation tests
- Mission critical WebSocket event tests

The configuration tests serve as a critical layer preventing deployment failures that could cause system-wide outages.

## Test Summary

**Total Tests Created**: 24 comprehensive integration tests
- **Main Test Suite**: 15 tests covering critical configuration management
- **Regression Prevention Suite**: 9 tests targeting specific historical incidents

**Key Areas Covered**:
- IsolatedEnvironment enforcement and usage validation
- Critical environment variables from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
- Configuration cascade failure prevention scenarios  
- Service configuration discovery and validation
- Multi-environment configuration isolation (dev/staging/prod)
- Configuration regression prevention for documented incidents
- Real configuration loading and validation systems
- CORS and domain configuration validation
- Secret loading, masking, and security validation
- Configuration change tracking and auditing
- Port discovery and allocation conflict prevention

**Business Value Delivered**:
- Prevents configuration cascade failures that have caused complete production outages
- Validates critical environment variables that prevent authentication failures
- Ensures proper environment isolation for multi-user system reliability
- Tests specific regression scenarios from documented production incidents
- Provides comprehensive error detection and reporting validation
- Enables safe configuration changes and deployments across environments