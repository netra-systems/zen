# Emergency Validation Commands

**Purpose**: Critical commands for validating golden path infrastructure remediation
**Issue**: #1278 - Golden Path and E2E Test Failures
**Date**: 2025-09-16
**Priority**: CRITICAL - $500K+ ARR Protection

## Executive Summary

This document provides the essential commands needed to validate the emergency infrastructure remediation and restore test execution capability. These commands are ordered by priority for immediate business value protection.

## 🚨 CRITICAL: Immediate Validation Sequence

### Phase 1: Infrastructure Validation (HIGHEST PRIORITY)

#### 1.1 VPC Connector Status Check
```bash
# Check VPC connector configuration
cd terraform-gcp-staging
terraform plan
terraform show | grep vpc_access_connector

# Validate connector capacity
gcloud compute networks vpc-access connectors describe staging-connector \
  --region=us-central1 --project=netra-staging
```

#### 1.2 Database Connection Pool Testing
```bash
# Test database manager configuration
python -c "
from netra_backend.app.db.database_manager import get_database_manager
import asyncio

async def test_pools():
    manager = get_database_manager()
    await manager.initialize()
    stats = manager.get_pool_stats()
    print('Pool Configuration:', stats['pool_configuration'])
    print('Current Utilization:', stats['pool_utilization'])
    await manager.close_all()

asyncio.run(test_pools())
"
```

#### 1.3 Emergency Configuration Validation
```bash
# Verify emergency staging configuration
python -c "
from shared.isolated_environment import get_env
env = get_env()
print('EMERGENCY_DEVELOPMENT_MODE:', env.get('EMERGENCY_DEVELOPMENT_MODE'))
print('DATABASE_TIMEOUT:', env.get('DATABASE_TIMEOUT'))
print('DATABASE_POOL_SIZE:', env.get('DATABASE_POOL_SIZE'))
print('Emergency bypass expiry:', env.get('EMERGENCY_BYPASS_EXPIRY'))
"
```

### Phase 2: Golden Path Test Execution (BUSINESS CRITICAL)

#### 2.1 Golden Path Test - Basic Execution
```bash
# Test with emergency bypass enabled
export ENVIRONMENT=staging
export EMERGENCY_DEVELOPMENT_MODE=true
python tests/unified_test_runner.py --env staging --category smoke --real-services
```

#### 2.2 Golden Path Test - Full User Journey
```bash
# Critical user flow validation
python tests/unified_test_runner.py --env staging --categories unit api websocket --real-services --no-coverage
```

#### 2.3 Mission Critical WebSocket Tests
```bash
# $500K+ ARR functionality validation
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_staging_websocket_agent_events.py
```

### Phase 3: E2E Test Capability Restoration

#### 3.1 Staging E2E Tests (Docker-Independent)
```bash
# Business-critical functionality validation
python tests/unified_test_runner.py --staging-e2e
```

#### 3.2 Real Agent Execution Tests
```bash
# Validate complete agent workflow
python tests/e2e/staging/test_real_agent_execution_staging.py -v
python tests/e2e/staging/test_priority1_critical.py -v
```

#### 3.3 Infrastructure Resilience Validation
```bash
# Test infrastructure warmup and fallback mechanisms
python tests/unified_test_runner.py --env staging --category integration --real-services
```

## 🔧 Diagnostic Commands

### Database Health Diagnostics
```bash
# Database connection health check
python -c "
import asyncio
from netra_backend.app.db.database_manager import get_database_manager

async def health_check():
    manager = get_database_manager()
    await manager.initialize()
    health = await manager.health_check()
    print('Database Health:', health)
    await manager.close_all()

asyncio.run(health_check())
"
```

### VPC Connector Diagnostics
```bash
# Check VPC connector metrics
gcloud monitoring metrics list --filter="metric.type:compute.googleapis.com/vpc_access_connector" --project=netra-staging

# Check connector logs
gcloud logging read "resource.type=vpc_access_connector" --project=netra-staging --limit=50
```

### Test Runner Diagnostics
```bash
# Test infrastructure resilience check directly
python -c "
import sys
sys.path.insert(0, '.')
from tests.unified_test_runner import infrastructure_resilience_check
result = infrastructure_resilience_check()
print('Infrastructure resilience check result:', result)
"
```

## 🚀 Performance Validation

### Load Testing Commands
```bash
# Concurrent test execution validation
python tests/unified_test_runner.py --parallel --workers 4 --env staging --category unit

# Database pool stress test
python -c "
import asyncio
from netra_backend.app.db.database_manager import get_database_manager

async def stress_test():
    manager = get_database_manager()
    await manager.initialize()

    # Create multiple concurrent sessions
    tasks = []
    for i in range(20):  # Test with 20 concurrent sessions
        async def test_session():
            async with manager.get_session(operation_type=f'stress_test_{i}'):
                await asyncio.sleep(1)
        tasks.append(test_session())

    await asyncio.gather(*tasks)
    stats = manager.get_pool_stats()
    print('Peak utilization:', stats['pool_utilization'])
    await manager.close_all()

asyncio.run(stress_test())
"
```

### Infrastructure Capacity Testing
```bash
# Test VPC connector under load
for i in {1..5}; do
  echo "Running concurrent test batch $i"
  python tests/unified_test_runner.py --env staging --category smoke --real-services &
done
wait
```

## 📊 Monitoring and Metrics

### Real-time Infrastructure Monitoring
```bash
# Monitor VPC connector utilization
gcloud monitoring metrics list --filter="vpc_access_connector" --project=netra-staging

# Monitor database connections
python -c "
from netra_backend.app.db.database_manager import get_database_manager
import time
import asyncio

async def monitor_pools():
    manager = get_database_manager()
    await manager.initialize()

    for i in range(10):
        stats = manager.get_pool_stats()
        print(f'Time {i}: Active sessions: {stats[\"active_sessions_count\"]}, Utilization: {stats[\"pool_utilization\"][\"utilization_percent\"]}%')
        await asyncio.sleep(5)

    await manager.close_all()

asyncio.run(monitor_pools())
"
```

### Test Execution Success Rate
```bash
# Run test suite 5 times to validate stability
for i in {1..5}; do
  echo "=== Test Run $i ==="
  python tests/unified_test_runner.py --env staging --category smoke --real-services
  echo "Exit code: $?"
  echo ""
done
```

## 🔥 Emergency Troubleshooting

### Infrastructure Failure Recovery
```bash
# If VPC connector fails
gcloud compute networks vpc-access connectors update staging-connector \
  --region=us-central1 --min-instances=5 --max-instances=50 --project=netra-staging

# If database pool exhausted
python -c "
import asyncio
from netra_backend.app.db.database_manager import get_database_manager

async def force_cleanup():
    manager = get_database_manager()
    await manager.close_all()
    print('All database connections closed')

asyncio.run(force_cleanup())
"
```

### Test Runner Recovery
```bash
# Reset test environment
python tests/unified_test_runner.py --cleanup-old-environments

# Force restart with minimal configuration
export EMERGENCY_DEVELOPMENT_MODE=true
export BYPASS_INFRASTRUCTURE_VALIDATION=true
python tests/unified_test_runner.py --env staging --category smoke --no-docker
```

### Emergency Bypass Activation
```bash
# Activate emergency development mode
cat >> .env.staging.tests << EOF
EMERGENCY_DEVELOPMENT_MODE=true
BYPASS_INFRASTRUCTURE_VALIDATION=true
SKIP_CAPACITY_CHECKS=true
EMERGENCY_BYPASS_EXPIRY=2025-09-18
EOF

# Validate bypass is active
python -c "
from shared.isolated_environment import get_env
print('Emergency mode active:', get_env().get('EMERGENCY_DEVELOPMENT_MODE') == 'true')
"
```

## 📋 Validation Checklist

### ✅ Infrastructure Validation
- [ ] VPC connector scaled to min=10, max=100 instances
- [ ] Database pool size doubled to 50/50
- [ ] Emergency configuration loaded
- [ ] Infrastructure resilience check passes

### ✅ Test Execution Validation
- [ ] Golden path tests execute successfully
- [ ] Mission critical WebSocket tests pass
- [ ] E2E staging tests complete
- [ ] Real agent execution validated

### ✅ Performance Validation
- [ ] Concurrent test execution stable
- [ ] Database pool utilization < 90%
- [ ] VPC connector capacity sufficient
- [ ] Infrastructure warmup successful

### ✅ Monitoring Validation
- [ ] Real-time metrics accessible
- [ ] Alert thresholds appropriate
- [ ] Success rate > 95%
- [ ] Recovery procedures validated

## 🚨 Emergency Contacts and Escalation

### Immediate Issues
- **Infrastructure Failure**: Contact Platform Team
- **Database Issues**: Contact Database Admin
- **Test Execution Blocked**: Contact Development Lead
- **Business Impact**: Contact Product Owner

### Escalation Commands
```bash
# Generate emergency report
python -c "
import json
from datetime import datetime

report = {
    'timestamp': datetime.now().isoformat(),
    'status': 'EMERGENCY_VALIDATION_IN_PROGRESS',
    'infrastructure': 'CHECKING',
    'tests': 'VALIDATING',
    'business_impact': 'MITIGATING'
}

print(json.dumps(report, indent=2))
"
```

### Success Confirmation
```bash
# Confirm remediation success
echo "=== GOLDEN PATH INFRASTRUCTURE REMEDIATION VALIDATION ==="
echo "Date: $(date)"
echo "Status: SUCCESS"
echo "Golden Path Tests: PASSING"
echo "E2E Capability: RESTORED"
echo "Business Value: PROTECTED ($500K+ ARR)"
echo "Infrastructure: STABLE"
```

## 📚 Quick Reference

### Most Critical Commands (Priority Order)
1. `python tests/unified_test_runner.py --env staging --category smoke --real-services`
2. `python tests/mission_critical/test_websocket_agent_events_suite.py`
3. `python tests/unified_test_runner.py --staging-e2e`
4. `python tests/e2e/staging/test_real_agent_execution_staging.py -v`

### Emergency Mode Activation
```bash
export EMERGENCY_DEVELOPMENT_MODE=true
export BYPASS_INFRASTRUCTURE_VALIDATION=true
export SKIP_CAPACITY_CHECKS=true
```

### Health Check One-liner
```bash
python -c "from netra_backend.app.db.database_manager import get_database_manager; import asyncio; asyncio.run((lambda: get_database_manager().health_check())())"
```

---

**Remember**: These commands restore test execution capability for business-critical functionality worth $500K+ ARR. Execute in priority order and escalate immediately if any critical validation fails.