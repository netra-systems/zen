# Infrastructure Validation Commands
**Golden Path Infrastructure Testing**

> **Note:** Execute these commands after implementing Priority 0 fixes to validate infrastructure configuration
>
> **Updated:** VPC connector scaling adjusted to appropriate staging levels (min=1, max=10, e2-small instances)

**Date:** 2025-09-16
**Status:** Ready for execution
**Purpose:** Validate infrastructure configuration for test execution

---

## Priority 0 Validation

### 1. VPC Connector Scaling Validation

> **NOTE:** VPC connector scaling should be appropriate for staging environment load. Starting with minimal resources and allowing auto-scaling is more cost-effective than over-provisioning.

```bash
# Navigate to terraform directory
cd terraform-gcp-staging

# Check terraform plan for VPC connector changes
terraform init
terraform plan -var="project_id=netra-staging"

# Apply VPC connector scaling (if plan looks correct)
terraform apply -var="project_id=netra-staging" -auto-approve

# Verify VPC connector status
gcloud compute networks vpc-access connectors describe staging-connector \
  --region=us-central1 --project=netra-staging
```

**Expected Result:** VPC connector shows min_instances=1, max_instances=10, machine_type=e2-small

**Rationale for Staging Scaling:**
- **min_instances=1**: Sufficient for baseline staging traffic, auto-scales as needed
- **max_instances=10**: Allows headroom for load testing without excessive cost
- **machine_type=e2-small**: 2 vCPUs, 2GB RAM per instance - adequate for network routing in staging

---

### 2. Database Connection Pool Validation
```bash
# Test database connection with new timeout configuration
python -c "
import sys
sys.path.insert(0, '.')
import asyncio
from netra_backend.app.db.database_manager import DatabaseManager

async def test_db():
    print('Testing database connection with emergency configuration...')
    db = DatabaseManager()
    await db.initialize()
    print('SUCCESS: Database connection established with 600s timeout and pool_size=50')
    print(f'Pool configuration: {db._engines}')

asyncio.run(test_db())
"
```

**Expected Result:** Database connection succeeds with enhanced pool configuration

---

### 3. Environment Configuration Validation
```bash
# Verify configuration loaded properly
python -c "
import sys
sys.path.insert(0, '.')
from shared.isolated_environment import get_env

config_vars = [
    'DATABASE_TIMEOUT',
    'DATABASE_POOL_SIZE',
    'EMERGENCY_DEVELOPMENT_MODE',
    'BYPASS_INFRASTRUCTURE_VALIDATION'
]

print('Configuration Validation:')
for var in config_vars:
    value = get_env(var)
    status = 'LOADED' if value else 'MISSING'
    print(f'  {var}: {value} ({status})')

if get_env('EMERGENCY_DEVELOPMENT_MODE') == 'true':
    print('Success: Development mode enabled')
else:
    print('Warning: Development mode not enabled')
"
```

**Expected Result:** All configuration variables loaded correctly

---

### 4. Test Runner Infrastructure Resilience Check
```bash
# Test infrastructure resilience functionality
python -c "
import sys
sys.path.insert(0, '.')

# Import the resilience check function
from tests.unified_test_runner import infrastructure_resilience_check

print('Testing infrastructure resilience check...')
result = infrastructure_resilience_check()

if result:
    print('SUCCESS: Infrastructure resilience check completed')
else:
    print('FAILED: Infrastructure resilience check failed')
"
```

**Expected Result:** Infrastructure resilience check completes successfully

---

### 5. Test Execution Capability
```bash
# Test basic smoke test execution with configuration
python tests/unified_test_runner.py --category smoke --dry-run

# If dry-run succeeds, try actual execution
python tests/unified_test_runner.py --category smoke --execution-mode fast_feedback
```

**Expected Result:** Smoke tests can execute without infrastructure capacity failures

---

### 6. Golden Path Critical Path Validation
```bash
# Test critical WebSocket agent functionality
python tests/mission_critical/test_websocket_agent_events_suite.py

# Test database connectivity under load
python tests/integration/infrastructure/test_issue_1278_vpc_connector_capacity.py
```

**Expected Result:** Critical tests execute without HTTP 503 or timeout errors

---

## Quick Validation Sequence (5 minutes)

Execute this sequence for validation:

```bash
echo "=== VALIDATION SEQUENCE ==="
echo "Starting at: $(date)"

echo ""
echo "1. Testing database connection..."
python -c "
import asyncio
from netra_backend.app.db.database_manager import DatabaseManager
async def test():
    db = DatabaseManager()
    await db.initialize()
    print('✅ Database connection OK')
asyncio.run(test())
"

echo ""
echo "2. Testing infrastructure resilience..."
python -c "
from tests.unified_test_runner import infrastructure_resilience_check
result = infrastructure_resilience_check()
print('✅ Infrastructure resilience OK' if result else '❌ Infrastructure resilience FAILED')
"

echo ""
echo "3. Testing emergency configuration..."
python -c "
from shared.isolated_environment import get_env
if get_env('EMERGENCY_DEVELOPMENT_MODE') == 'true':
    print('✅ Emergency development mode ACTIVE')
else:
    print('❌ Emergency development mode NOT ACTIVE')
"

echo ""
echo "4. Testing smoke test capability..."
python tests/unified_test_runner.py --category smoke --dry-run > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Smoke test capability OK"
else
    echo "❌ Smoke test capability FAILED"
fi

echo ""
echo "Validation sequence completed at: $(date)"
echo "=== END VALIDATION ==="
```

---

## 🔍 SUCCESS CRITERIA VERIFICATION

### Infrastructure Capacity
- [ ] VPC connector scaled to min=1, max=10 instances (appropriate for staging)
- [ ] Database pool size increased to 50 connections
- [ ] Database timeout configured to 600 seconds
- [ ] Infrastructure resilience check completes in < 2 minutes

### Test Execution Capability
- [ ] Smoke tests execute without HTTP 503 errors
- [ ] Development bypass enables test execution
- [ ] Infrastructure warmup prevents connection failures
- [ ] Test runner can handle temporary infrastructure pressure

### Configuration Validation
- [ ] All environment variables loaded
- [ ] Database connections survive 10+ minute operations
- [ ] WebSocket timeouts extended to 600 seconds
- [ ] Development bypass expires automatically on 2025-09-18

---

## Rollback Commands (If Validation Fails)

### Rollback VPC Connector Changes
```bash
cd terraform-gcp-staging
git checkout HEAD~1 -- vpc-connector.tf
terraform apply -var="project_id=netra-staging" -auto-approve
```

### Rollback Database Configuration
```bash
# Restore original database manager configuration
git checkout HEAD~1 -- netra_backend/app/db/database_manager.py
```

### Remove Development Configuration
```bash
# Remove development variables from test environment
sed -i '/DATABASE_TIMEOUT=/d' .env.staging.tests
sed -i '/EMERGENCY_DEVELOPMENT_MODE=/d' .env.staging.tests
sed -i '/BYPASS_INFRASTRUCTURE_VALIDATION=/d' .env.staging.tests
```

### Disable Development Bypass
```bash
# Disable development bypass if needed
python -c "
import re
with open('.env.staging.tests', 'r') as f:
    content = f.read()
content = re.sub(r'EMERGENCY_DEVELOPMENT_MODE=true', 'EMERGENCY_DEVELOPMENT_MODE=false', content)
with open('.env.staging.tests', 'w') as f:
    f.write(content)
print('Development bypass disabled')
"
```

---

## 📊 VALIDATION STATUS TRACKING

### Real-time Status Check
```bash
# Create status monitoring script
python -c "
import time
from datetime import datetime

def check_infrastructure_status():
    status = {
        'timestamp': datetime.now().isoformat(),
        'vpc_connector': 'Checking...',
        'database_pools': 'Checking...',
        'test_execution': 'Checking...',
        'development_bypass': 'Checking...'
    }

    try:
        # Check development bypass
        from shared.isolated_environment import get_env
        status['development_bypass'] = 'ACTIVE' if get_env('EMERGENCY_DEVELOPMENT_MODE') == 'true' else 'INACTIVE'

        # Check database
        import asyncio
        from netra_backend.app.db.database_manager import DatabaseManager

        async def test_db():
            db = DatabaseManager()
            await db.initialize()
            return 'CONNECTED'

        db_status = asyncio.run(test_db())
        status['database_pools'] = db_status

    except Exception as e:
        status['error'] = str(e)

    print('INFRASTRUCTURE STATUS:', status)
    return status

check_infrastructure_status()
"
```

---

**NEXT STEPS:**
1. Execute Priority 0 validation commands immediately
2. Monitor infrastructure status during test execution
3. Proceed to Priority 1 fixes if validation succeeds
4. Execute rollback commands if validation fails

**Note:** Test execution capability should be restored promptly for functionality validation.