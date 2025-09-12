# WebSocket Protocol Deployment Test Execution Guide

## Overview

This guide provides comprehensive instructions for executing the two priority WebSocket protocol deployment tests that validate the resolution of Issue #463 (WebSocket 1011 Internal Errors).

**Tests Implemented:**
1. `test_websocket_protocol_format_deployment_validation` (Priority 0)
2. `test_staging_source_protocol_format_synchronization` (Priority 1)

**Business Impact:** These tests protect $500K+ ARR Golden Path functionality by validating WebSocket protocol format consistency.

## Test Files Location

```bash
# Priority 0 Test
tests/critical/test_websocket_protocol_format_deployment_validation.py

# Priority 1 Test  
tests/critical/test_staging_source_protocol_format_synchronization.py
```

## Test Execution Commands

### Method 1: Direct Python Execution (Recommended for Development)

```bash
# Change to project root
cd C:\GitHub\netra-apex

# Execute Priority 0 Test (Protocol Format Validation)
python -m pytest tests/critical/test_websocket_protocol_format_deployment_validation.py -v -s

# Execute Priority 1 Test (Staging Synchronization)
python -m pytest tests/critical/test_staging_source_protocol_format_synchronization.py -v -s

# Execute both tests together
python -m pytest tests/critical/test_websocket_protocol_format_deployment_validation.py tests/critical/test_staging_source_protocol_format_synchronization.py -v -s
```

### Method 2: Using Test Categories

```bash
# Execute all critical WebSocket protocol tests
python -m pytest -m "websocket_protocol" -v -s

# Execute all deployment validation tests
python -m pytest -m "deployment_validation" -v -s

# Execute all staging validation tests
python -m pytest -m "staging_validation" -v -s
```

### Method 3: Using Unified Test Runner (Alternative)

```bash
# Run with critical category (includes our tests)
python tests/unified_test_runner.py --categories websocket --verbose

# Note: Unified test runner may have different discovery patterns
```

## Test Execution Parameters

### Essential Parameters

```bash
# Verbose output (shows detailed test execution)
-v or --verbose

# Show print statements and logs
-s or --capture=no

# Run specific test method
-k "test_websocket_protocol_format_deployment_validation"

# Stop on first failure
-x or --exitfirst

# Show local variables in tracebacks
-l or --showlocals
```

### Environment Configuration

```bash
# Set environment for staging validation
export ENVIRONMENT=staging
export GCP_PROJECT=netra-staging

# Set environment for local development
export ENVIRONMENT=development
export E2E_TESTING=1
```

## Expected Test Behavior

### Priority 0 Test: Protocol Format Deployment Validation

**EXPECTED BEHAVIOR:**
- **PASS**: When protocol format validation works correctly
- **Test Scenarios**: 4 scenarios including correct/incorrect format validation
- **Success Criteria**: Backend properly validates protocol format

```bash
# Example successful execution
$ python -m pytest tests/critical/test_websocket_protocol_format_deployment_validation.py -v -s

============================= test session starts =============================
tests/critical/test_websocket_protocol_format_deployment_validation.py::TestWebSocketProtocolFormatDeploymentValidation::test_websocket_protocol_format_deployment_validation PASSED [100%]
```

### Priority 1 Test: Staging Source Protocol Synchronization

**EXPECTED BEHAVIOR:**
- **PASS**: When staging frontend/backend protocols are synchronized  
- **Test Scenarios**: 4+ scenarios including synchronization validation
- **Success Criteria**: Protocol synchronization detection works properly

```bash
# Example successful execution
$ python -m pytest tests/critical/test_staging_source_protocol_format_synchronization.py -v -s

============================= test session starts =============================
tests/critical/test_staging_source_protocol_format_synchronization.py::TestStagingSourceProtocolFormatSynchronization::test_staging_source_protocol_format_synchronization PASSED [100%]
```

## Test Failure/Success Patterns

### Understanding Test Results

#### ✅ PASS Conditions (These indicate proper functioning):

1. **Protocol Format Validation Working**
   - Backend correctly accepts valid protocol format: `['jwt-auth', 'jwt.${token}']`
   - Backend correctly rejects invalid formats
   - No 1011 errors with correct protocol

2. **Staging Synchronization Maintained**
   - Frontend and backend use identical protocol format
   - Synchronization detection works correctly
   - No deployment drift detected

#### ❌ FAIL Conditions (These indicate issues):

1. **Protocol Format Issues**
   - Backend accepts invalid protocol formats  
   - Backend rejects valid protocol formats incorrectly
   - 1011 errors with correct protocol format

2. **Staging Synchronization Problems**  
   - Frontend/backend protocol formats differ
   - Deployment sources cause protocol drift
   - Synchronization detection not working

### Log Analysis

**Look for these log messages:**

```bash
# Success indicators
" PASS:  Backend correctly validates protocol format"
" SUCCESS:  Staging frontend/backend protocols synchronized" 
" PASS:  Protocol synchronization validation detects mismatches"

# Warning indicators  
" FAIL:  Protocol validation failed"
" MISMATCH:  Frontend: [...], Backend: [...]"
" WARNING:  Required services unavailable"
```

## Troubleshooting Common Issues

### Import Errors

```bash
# If you see import errors, ensure you're in project root
cd C:\GitHub\netra-apex

# Validate imports manually
python -c "from test_framework.ssot.base_test_case import SSotAsyncTestCase; print('Import OK')"
```

### WebSocket Connection Issues

```bash
# For staging environment testing, ensure credentials
export ENVIRONMENT=staging

# For local testing, ensure services are running
# Check if backend is available at localhost:8000
curl http://localhost:8000/health
```

### Test Collection Issues

```bash
# If tests aren't discovered, validate manually
python -c "
import tests.critical.test_websocket_protocol_format_deployment_validation as test1
print('Test 1 imported successfully')
import tests.critical.test_staging_source_protocol_format_synchronization as test2  
print('Test 2 imported successfully')
"
```

## Integration with CI/CD

### GitHub Actions

```yaml
# Add to GitHub Actions workflow
- name: Run WebSocket Protocol Deployment Tests
  run: |
    python -m pytest tests/critical/test_websocket_protocol_format_deployment_validation.py -v
    python -m pytest tests/critical/test_staging_source_protocol_format_synchronization.py -v
```

### Pre-Deployment Validation

```bash
# Run before deployment to validate protocol format
python -m pytest -m "websocket_protocol and deployment_validation" -v --tb=short

# Run staging validation after deployment
ENVIRONMENT=staging python -m pytest -m "staging_validation" -v
```

## Test Maintenance

### When to Update Tests

1. **WebSocket Protocol Changes**: Update expected protocol format
2. **Deployment Pipeline Changes**: Update deployment source simulation  
3. **Staging Environment Changes**: Update staging URL/credentials
4. **New Error Patterns**: Add new validation scenarios

### Adding New Scenarios

```python
# Add to existing test methods:
await self._test_protocol_format_scenario(
    scenario_name="new_scenario_name",
    protocol=['custom', 'format'],
    token=test_token,
    should_succeed=False
)
```

## Performance Considerations

### Test Execution Time

- **Priority 0 Test**: ~30-60 seconds (includes WebSocket connections)
- **Priority 1 Test**: ~45-90 seconds (includes staging validation)
- **Total Runtime**: ~2-3 minutes for both tests

### Resource Usage

- **Network**: Tests make real WebSocket connections
- **Memory**: ~50-100MB additional during execution  
- **Dependencies**: Requires `websockets` library

## Security Considerations

### Test Tokens

Tests use hardcoded test JWT tokens that are safe for testing:
```
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNjM3MjQwMDAwLCJleHAiOjE2MzcyNDM2MDB9.signature
```

### Staging Environment

When running against staging:
- Tests only validate protocol format, not authentication
- No production data access
- Read-only validation operations

## Contact and Support

For issues with these tests:

1. **Protocol Format Issues**: Check WebSocket handler implementation
2. **Staging Connection Issues**: Verify GCP staging deployment status  
3. **Import/Discovery Issues**: Validate SSOT compliance
4. **Test Logic Issues**: Review test implementation and expected behaviors

## Summary

These tests provide comprehensive validation of WebSocket protocol format consistency during deployments, protecting the $500K+ ARR Golden Path functionality. They should be run:

- **Before deployments** to validate protocol format
- **After deployments** to verify staging synchronization  
- **During troubleshooting** of WebSocket 1011 errors
- **As part of CI/CD** for continuous validation

The tests are designed to PASS when the system works correctly and provide detailed diagnostics when issues are detected.