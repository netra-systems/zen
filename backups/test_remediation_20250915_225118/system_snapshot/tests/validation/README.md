# Issue #1264 Validation Framework

This directory contains comprehensive validation tools for Issue #1264 - Cloud SQL PostgreSQL configuration validation.

## Overview

Issue #1264 involved a critical infrastructure misconfiguration where Cloud SQL was configured as MySQL instead of PostgreSQL, causing 8+ second database connection timeouts and complete staging environment failure.

This validation framework provides:
- **Immediate validation** when the infrastructure fix is applied
- **Continuous monitoring** to detect when the fix is deployed
- **Regression prevention** to ensure the issue never recurs
- **Comprehensive testing** for all related infrastructure components

## Quick Start - Immediate Validation

When the infrastructure team applies the PostgreSQL configuration fix, run this command immediately:

```bash
# Instant validation (no dependencies required)
python scripts/issue_1264_instant_validation.py
```

**Expected Result:**
- **PASS** after infrastructure fix: All tests succeed, connection times < 8s
- **FAIL** before infrastructure fix: Timeouts and connection failures

## Validation Components

### 1. Instant Validation Script
**File**: `scripts/issue_1264_instant_validation.py`

Quick validation script that can be run immediately after the infrastructure fix:
- Tests database connectivity with timeout monitoring
- Validates health endpoint accessibility
- Checks WebSocket connection establishment
- Provides immediate PASS/FAIL result

```bash
python scripts/issue_1264_instant_validation.py
```

### 2. Comprehensive Validation Suite
**File**: `tests/validation/issue_1264_staging_validation_suite.py`

Full pytest-based validation suite with detailed testing:
- Database connectivity validation with timing analysis
- Health endpoint comprehensive testing
- WebSocket connectivity validation
- Golden Path infrastructure readiness
- Complete staging environment health assessment

```bash
# Run individual tests
python -m pytest tests/validation/issue_1264_staging_validation_suite.py::TestIssue1264StagingValidation::test_database_connectivity_validation -v

# Run complete validation suite
python -m pytest tests/validation/issue_1264_staging_validation_suite.py -v

# Run with direct execution
python tests/validation/issue_1264_staging_validation_suite.py
```

### 3. Continuous Monitoring Script
**File**: `scripts/issue_1264_continuous_monitor.py`

Continuous monitoring that detects when the infrastructure fix is applied:
- Monitors staging environment health every 60 seconds
- Automatically detects infrastructure improvements
- Runs full validation when fix is detected
- Provides detailed monitoring logs

```bash
# Start continuous monitoring (default: 60s intervals, 24 hours max)
python scripts/issue_1264_continuous_monitor.py

# Custom monitoring (120s intervals, 12 hours max)
python scripts/issue_1264_continuous_monitor.py --interval 120 --max-checks 360
```

### 4. Regression Prevention
**File**: `docs/remediation/ISSUE_1264_REGRESSION_PREVENTION_GUIDE.md`

Comprehensive guide for preventing Issue #1264 regression:
- Infrastructure validation checks
- Deployment pipeline integration
- Configuration management
- Monitoring and alerting setup
- Documentation requirements

## Usage Scenarios

### Scenario 1: Infrastructure Team Just Applied Fix

```bash
# Step 1: Immediate validation
python scripts/issue_1264_instant_validation.py

# Step 2: If instant validation passes, run comprehensive validation
python tests/validation/issue_1264_staging_validation_suite.py

# Step 3: Review results and confirm resolution
cat issue_1264_instant_validation_results.json
```

### Scenario 2: Waiting for Infrastructure Fix

```bash
# Start continuous monitoring to detect when fix is applied
python scripts/issue_1264_continuous_monitor.py

# Monitor will automatically:
# 1. Detect when fix is applied
# 2. Run comprehensive validation
# 3. Report results
# 4. Save detailed logs
```

### Scenario 3: Regular Regression Testing

```bash
# Add to CI/CD pipeline or run regularly
python -m pytest tests/validation/issue_1264_staging_validation_suite.py::TestIssue1264StagingValidation::test_database_connectivity_validation

# Should always PASS after fix is applied
# Will FAIL if regression occurs
```

## Expected Results

### Before Infrastructure Fix (Expected FAILURES)
```
❌ Database Connectivity: Connection timeout after 8+ seconds
❌ Health Endpoint: Service unavailable (backend can't start)
❌ WebSocket Connectivity: Connection refused
❌ Golden Path: Infrastructure not operational

Issue #1264 Status: UNRESOLVED
```

### After Infrastructure Fix (Expected SUCCESS)
```
✓ Database Connectivity: Connected in <2 seconds
✓ Health Endpoint: 200 OK response
✓ WebSocket Connectivity: Connection established
✓ Golden Path: Infrastructure operational

Issue #1264 Status: RESOLVED
```

## File Outputs

### Validation Results Files
- `issue_1264_instant_validation_results.json` - Instant validation results
- `issue_1264_validation_results.json` - Comprehensive validation results
- `issue_1264_monitoring_log.json` - Continuous monitoring log
- `connection_time_monitoring.json` - Connection time analysis

### Log Files
- `issue_1264_monitor.log` - Monitoring script logs
- Test output logs from pytest runs

## Environment Requirements

### Required Environment Variables
```bash
export ENVIRONMENT=staging
```

### Required Dependencies
```bash
# For comprehensive validation
pip install pytest asyncio asyncpg aiohttp websockets

# For instant validation (minimal dependencies)
pip install asyncpg aiohttp websockets
```

### Optional Dependencies
```bash
# For monitoring and alerting
pip install google-cloud-sql prometheus-client
```

## Troubleshooting

### Common Issues

#### 1. "Environment validation failed: Not in staging environment"
```bash
export ENVIRONMENT=staging
python scripts/issue_1264_instant_validation.py
```

#### 2. "Import error: No module named 'asyncpg'"
```bash
pip install asyncpg aiohttp websockets
python scripts/issue_1264_instant_validation.py
```

#### 3. "Database connection failed: No database URL configured"
Ensure staging configuration is properly set up in `netra_backend/app/schemas/config.py`

#### 4. Validation passes but connection time still high
The infrastructure fix may be partially applied. Check:
- Cloud SQL instance is actually PostgreSQL (not MySQL)
- VPC connector is properly configured
- Connection string is correctly formatted

### Debug Commands

```bash
# Check Cloud SQL instance configuration
gcloud sql instances describe staging-shared-postgres --project=netra-staging

# Validate connection string format
python scripts/validate_connection_strings.py

# Monitor connection times
python scripts/connection_time_monitor.py 10  # 10 minute monitoring
```

## Integration with CI/CD

### Pre-Deployment Validation
```yaml
# .github/workflows/pre-deploy.yml
- name: Validate Database Configuration
  run: |
    python scripts/validate_connection_strings.py
    python -m pytest tests/validation/issue_1264_staging_validation_suite.py::TestIssue1264StagingValidation::test_database_connectivity_validation
```

### Post-Deployment Validation
```yaml
# .github/workflows/post-deploy.yml
- name: Comprehensive Infrastructure Validation
  run: |
    python tests/validation/issue_1264_staging_validation_suite.py
```

## Business Impact

### Before Fix Resolution
- **$500K+ ARR Golden Path**: Completely offline
- **Staging Environment**: Non-functional for development/testing
- **Deployment Pipeline**: Blocked due to infrastructure failure
- **Customer Impact**: Unable to deploy fixes or new features

### After Fix Resolution
- **$500K+ ARR Golden Path**: Fully operational
- **Staging Environment**: Reliable for development/testing
- **Deployment Pipeline**: Restored normal operation
- **Customer Impact**: Rapid feature deployment and bug fixes

## Success Criteria

1. **Database Connectivity**: Connection time < 8 seconds (target: < 2 seconds)
2. **Health Endpoint**: Returns 200 OK consistently
3. **WebSocket Connectivity**: Connections establish successfully
4. **Golden Path**: End-to-end infrastructure operational
5. **Zero Regression**: No recurrence of Issue #1264 patterns

## Support

For issues with the validation framework:

1. **Check Environment**: Ensure `ENVIRONMENT=staging` is set
2. **Check Dependencies**: Install required packages
3. **Check Logs**: Review output files for detailed error information
4. **Run Debug Commands**: Use troubleshooting commands above
5. **Escalate**: If validation indicates infrastructure issues, escalate to infrastructure team

---

**Documentation Version**: 1.0
**Last Updated**: 2025-09-15
**Related Issue**: #1264 - Cloud SQL PostgreSQL Configuration Validation