# Golden Path Phase 2 Test Integration Guide

## Overview

This guide explains how to integrate the Golden Path Phase 2 regression prevention test into the existing test infrastructure and SSOT patterns.

## Integration Points

### 1. Unified Test Runner Integration

The Golden Path Phase 2 tests integrate seamlessly with the existing unified test runner:

```bash
# Run via unified test runner
python tests/unified_test_runner.py --category e2e --pattern golden_path_phase2

# Run as part of staging validation
python tests/unified_test_runner.py --real-services --env staging --pattern golden_path

# Include in mission-critical test suite
python tests/unified_test_runner.py --category critical --pattern golden_path_phase2
```

### 2. Mission Critical Test Suite Integration

Add to mission-critical test execution by updating the test categorization:

**File**: `tests/mission_critical/test_suite_registry.py`
```python
MISSION_CRITICAL_TESTS = [
    # Existing tests...
    "tests.e2e.staging.test_golden_path_phase2_regression_prevention",
]

GOLDEN_PATH_TESTS = [
    "tests.e2e.staging.test_golden_path_phase2_regression_prevention::TestGoldenPathPhase2RegressionPrevention::test_complete_golden_path_user_flow",
]
```

### 3. SSOT Compliance Validation

The tests follow all SSOT patterns established in CLAUDE.md:

- ✅ Inherits from `SSotAsyncTestCase`
- ✅ Uses `shared.isolated_environment` for environment access
- ✅ Follows absolute import patterns from SSOT registry
- ✅ Uses real services (no mocks per CLAUDE.md)
- ✅ Integrates with staging configuration SSOT

### 4. CI/CD Pipeline Integration

#### Pre-Deployment Validation
```yaml
# .github/workflows/staging-deployment.yml
- name: Golden Path Phase 2 Validation
  run: |
    python tests/e2e/staging/run_golden_path_phase2_test.py --full
    if [ $? -ne 0 ]; then
      echo "❌ Golden Path validation failed - blocking deployment"
      exit 1
    fi
```

#### Post-Deployment Verification
```yaml
# .github/workflows/post-deployment-validation.yml
- name: Golden Path Regression Check
  run: |
    sleep 30  # Allow deployment to stabilize
    python tests/e2e/staging/run_golden_path_phase2_test.py --quick
    python tests/e2e/staging/run_golden_path_phase2_test.py --baseline
```

## Test Execution Workflow

### Phase 1: Pre-Migration Baseline

1. **Establish Baseline**
   ```bash
   # Set baseline environment
   export GOLDEN_PATH_PHASE="PRE_MIGRATION"
   export BASELINE_RECORDING="true"
   
   # Run baseline tests
   python tests/e2e/staging/run_golden_path_phase2_test.py --baseline
   ```

2. **Full Validation**
   ```bash
   # Validate current state
   python tests/e2e/staging/run_golden_path_phase2_test.py --full
   
   # Record success metrics
   echo "✅ Phase 1 baseline established"
   ```

### Phase 2: Migration Execution

1. **Pre-Migration Check**
   ```bash
   # Final validation before changes
   python tests/e2e/staging/run_golden_path_phase2_test.py --quick
   ```

2. **Deploy MessageRouter Changes**
   ```bash
   # Deploy SSOT MessageRouter without proxy
   python scripts/deploy_to_gcp.py --project netra-staging --build-local
   ```

3. **Post-Migration Validation**
   ```bash
   # Immediate validation
   python tests/e2e/staging/run_golden_path_phase2_test.py --quick
   
   # Full regression suite
   python tests/e2e/staging/run_golden_path_phase2_test.py --full
   ```

### Phase 3: Success Validation

1. **Performance Comparison**
   ```bash
   # Compare against baseline
   export GOLDEN_PATH_PHASE="POST_MIGRATION"
   python tests/e2e/staging/run_golden_path_phase2_test.py --baseline
   ```

2. **Extended Validation**
   ```bash
   # Run extended validation suite
   python tests/unified_test_runner.py --category e2e --env staging --real-services
   ```

## Environment Configuration

### Required Environment Variables

```bash
# Staging authentication
JWT_SECRET_STAGING=<staging_jwt_secret>
E2E_OAUTH_SIMULATION_KEY=<oauth_simulation_key>

# Test configuration
ENVIRONMENT=staging
GOLDEN_PATH_PHASE2_TEST=true
TEST_USER_ISOLATION=enabled

# Performance tracking
BASELINE_RECORDING=false
GOLDEN_PATH_PHASE=CURRENT
```

### Staging URLs Configuration

The tests use the canonical staging URLs defined in `staging_config.py`:

- Backend: `https://api.staging.netrasystems.ai`
- Auth: `https://auth.staging.netrasystems.ai`
- WebSocket: `wss://api.staging.netrasystems.ai/ws`

## Metrics and Monitoring

### Business Value Metrics

The tests track key business value indicators:

```python
# Response quality assessment
response_quality_score: int  # 0-100 scale
business_value_indicators: List[str]  # Cost, efficiency, etc.

# Performance metrics
connection_time: float  # WebSocket connection latency
first_event_time: float  # Time to first agent event
completion_time: float  # Total agent response time

# User isolation metrics
concurrent_users_supported: int  # Number of concurrent users tested
user_isolation_validated: bool  # Cross-user contamination check
```

### Alert Thresholds

Configure monitoring alerts for:

- Response quality score < 60/100
- Connection time > 10 seconds
- First event time > 20 seconds
- Completion time > 120 seconds
- Any test failures

## Integration with Existing Tests

### Complementary Test Suites

The Golden Path Phase 2 tests complement existing test infrastructure:

1. **WebSocket Tests**: Existing WebSocket tests validate protocol-level functionality
2. **Agent Tests**: Existing agent tests validate individual agent behavior
3. **Golden Path Tests**: These tests validate complete end-to-end user experience

### Test Coverage Matrix

| Test Category | Protocol | Agent Logic | User Experience | Business Value |
|---------------|----------|-------------|-----------------|----------------|
| Unit Tests | ❌ | ✅ | ❌ | ❌ |
| Integration Tests | ✅ | ✅ | ❌ | ❌ |
| Existing E2E Tests | ✅ | ❌ | ✅ | ❌ |
| **Golden Path Phase 2** | ✅ | ✅ | ✅ | ✅ |

## Troubleshooting Common Issues

### Authentication Failures

```bash
# Debug JWT token issues
python tests/e2e/staging/test_golden_path_phase2_regression_prevention.py -k "debug" -v

# Validate staging environment
python -c "from tests.e2e.staging_config import is_staging_available; print(is_staging_available())"
```

### WebSocket Connection Issues

```bash
# Test WebSocket connectivity
python -c "
import asyncio
import websockets
async def test():
    async with websockets.connect('wss://api.staging.netrasystems.ai/ws') as ws:
        print('✅ WebSocket connection successful')
asyncio.run(test())
"
```

### Environment Variable Issues

```bash
# Validate environment setup
python tests/e2e/staging/run_golden_path_phase2_test.py --help
```

## Success Criteria

### Test Passing Requirements

For the Golden Path Phase 2 tests to be considered successful:

- ✅ All 5 test scenarios pass completely
- ✅ WebSocket events delivered in correct sequence  
- ✅ Agent response quality ≥60/100 score
- ✅ Performance within established thresholds
- ✅ User isolation maintained across concurrent sessions
- ✅ Error handling functions correctly

### Business Value Validation

- ✅ AI responses contain actionable insights
- ✅ Business value indicators present in responses
- ✅ User experience quality maintained
- ✅ No regression in chat functionality

### Migration Approval Criteria

The MessageRouter proxy removal can proceed only when:

1. **Pre-Migration**: All Golden Path Phase 2 tests pass
2. **Post-Migration**: All Golden Path Phase 2 tests continue to pass
3. **Performance**: No significant degradation in response times
4. **Quality**: Agent response quality maintained or improved
5. **Isolation**: User isolation remains effective

## Rollback Procedures

If Golden Path Phase 2 tests fail after migration:

1. **IMMEDIATE**: Stop any ongoing deployments
2. **URGENT**: Rollback MessageRouter changes to previous version
3. **VALIDATE**: Re-run Golden Path tests to confirm rollback success
4. **INVESTIGATE**: Analyze failure cause and plan remediation
5. **FIX**: Address issues before attempting migration again

## Support and Maintenance

### Regular Maintenance Tasks

- Update performance thresholds based on infrastructure improvements
- Refresh staging authentication tokens as needed
- Review and update business value indicators
- Validate staging environment configuration

### Contact Information

For questions or issues with Golden Path Phase 2 tests:

- **Primary**: Development team responsible for MessageRouter SSOT migration
- **Secondary**: E2E testing infrastructure team
- **Escalation**: Platform engineering team for critical business impact

## Conclusion

The Golden Path Phase 2 regression prevention test provides comprehensive protection for the core user experience during the critical MessageRouter proxy removal. By integrating with existing test infrastructure while providing unique end-to-end business value validation, it ensures that the 90% of platform value delivered through chat functionality remains protected throughout the SSOT migration process.