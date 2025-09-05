# GCP Staging Critical Remediation Plan - September 5, 2025

## Executive Summary

**CRITICAL SYSTEM OUTAGE - IMMEDIATE ACTION REQUIRED**

The GCP staging environment is experiencing a complete cascade failure preventing all user access and functionality. This remediation plan addresses the immediate crisis and implements long-term prevention measures.

**Current Status:** 🚨 **DEFCON 1** - Complete system failure
**Recovery Time Objective:** 30 minutes for basic functionality
**Recovery Point Objective:** No data loss (configuration issue)

---

## Phase 1: Emergency Recovery (0-30 Minutes)

### 🚨 CRITICAL STEP 1: Restore SERVICE_SECRET Configuration

**Immediate Action:**
```bash
# 1. Check current GCP Secret Manager
gcloud secrets list --project=netra-staging --filter="SERVICE_SECRET"

# 2. If missing, create SERVICE_SECRET
# Note: Replace [ACTUAL_SECRET] with real value from secure storage
gcloud secrets create SERVICE_SECRET \
  --project=netra-staging \
  --data="[ACTUAL_SECRET_VALUE]"

# 3. Update Cloud Run service to use the secret
gcloud run services update netra-backend-staging \
  --project=netra-staging \
  --region=us-central1 \
  --update-env-vars=SERVICE_SECRET=[ACTUAL_SECRET_VALUE]

# 4. Verify deployment
gcloud run services describe netra-backend-staging \
  --project=netra-staging \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env[?(@.name=='SERVICE_SECRET')].value)"
```

**Expected Result:** SERVICE_SECRET environment variable present in service

### 🚨 CRITICAL STEP 2: Force Service Restart

**Purpose:** Reset circuit breaker state and reinitialize auth connections

```bash
# Force new revision deployment to restart service
gcloud run services update netra-backend-staging \
  --project=netra-staging \
  --region=us-central1 \
  --set-env-vars="FORCE_RESTART=$(date +%s)"

# Monitor deployment
gcloud run services describe netra-backend-staging \
  --project=netra-staging \
  --region=us-central1 \
  --format="value(status.conditions[0].message)"
```

**Expected Result:** New service revision deployed and running

### 🚨 CRITICAL STEP 3: Verify Auth Service Connectivity

**Test Inter-Service Authentication:**
```bash
# Check auth service status
gcloud run services describe netra-auth-service-pnovr5vsba-uc \
  --project=netra-staging \
  --region=us-central1 \
  --format="value(status.url,status.conditions[0].status)"

# Test auth endpoint directly
curl -I https://netra-auth-service-pnovr5vsba-uc.a.run.app/health

# Monitor backend logs for successful auth connection
gcloud logging read --project=netra-staging \
  --filter="resource.labels.service_name=netra-backend-staging AND textPayload:(auth_client)" \
  --limit=10 \
  --format="value(timestamp,textPayload)"
```

**Expected Result:** Auth service responding, backend logs show successful connection

---

## Phase 2: System Validation (30-60 Minutes)

### 🔍 STEP 4: Complete Configuration Audit

**Verify All Critical Environment Variables:**
```bash
# Create comprehensive configuration check script
cat > check_staging_config.sh << 'EOF'
#!/bin/bash
echo "🔍 GCP Staging Configuration Audit"
echo "=================================="

# Check backend service
echo "Backend Service Configuration:"
gcloud run services describe netra-backend-staging \
  --project=netra-staging \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env[].name)" | sort

# Verify critical variables
echo -e "\nCritical Variables Check:"
for var in SERVICE_SECRET JWT_SECRET_KEY DATABASE_URL REDIS_URL ENVIRONMENT; do
  result=$(gcloud run services describe netra-backend-staging \
    --project=netra-staging \
    --region=us-central1 \
    --format="value(spec.template.spec.containers[0].env[?(@.name=='$var')].name)")
  if [ -n "$result" ]; then
    echo "✅ $var: Present"
  else
    echo "❌ $var: MISSING"
  fi
done

# Check auth service
echo -e "\nAuth Service Configuration:"
gcloud run services describe netra-auth-service-pnovr5vsba-uc \
  --project=netra-staging \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env[].name)" | sort
EOF

chmod +x check_staging_config.sh
./check_staging_config.sh
```

**Expected Result:** All critical environment variables present

### 🔍 STEP 5: End-to-End Functionality Test

**Test Critical Endpoints:**
```bash
# Create E2E test script
cat > test_staging_e2e.sh << 'EOF'
#!/bin/bash
echo "🧪 End-to-End Staging Test"
echo "========================="

BACKEND_URL="https://api.staging.netrasystems.ai"
AUTH_URL="https://auth.staging.netrasystems.ai"

# Test backend health
echo "1. Testing backend health..."
backend_health=$(curl -s -o /dev/null -w "%{http_code}" $BACKEND_URL/health)
if [ "$backend_health" = "200" ]; then
  echo "✅ Backend health: OK"
else
  echo "❌ Backend health: $backend_health"
fi

# Test auth health
echo "2. Testing auth service..."
auth_health=$(curl -s -o /dev/null -w "%{http_code}" $AUTH_URL/health)
if [ "$auth_health" = "200" ]; then
  echo "✅ Auth health: OK"
else
  echo "❌ Auth health: $auth_health"
fi

# Test service discovery
echo "3. Testing service discovery..."
discovery=$(curl -s -o /dev/null -w "%{http_code}" $BACKEND_URL/api/discovery)
if [ "$discovery" = "200" ]; then
  echo "✅ Service discovery: OK"
else
  echo "❌ Service discovery: $discovery"
fi

# Test OAuth configuration
echo "4. Testing OAuth configuration..."
oauth_config=$(curl -s -o /dev/null -w "%{http_code}" $AUTH_URL/api/auth/config)
if [ "$oauth_config" = "200" ]; then
  echo "✅ OAuth config: OK"
else
  echo "❌ OAuth config: $oauth_config"
fi

echo -e "\nTest Summary Complete"
EOF

chmod +x test_staging_e2e.sh
./test_staging_e2e.sh
```

**Expected Result:** All endpoints returning 200 status codes

---

## Phase 3: Long-term Prevention (1-4 Hours)

### 🛡️ STEP 6: Implement Configuration Validation

**Create Pre-deployment Validation:**
```bash
# Create comprehensive deployment validation script
cat > scripts/validate_gcp_deployment.py << 'EOF'
#!/usr/bin/env python3
"""
GCP Deployment Configuration Validator
Prevents configuration regressions by validating all critical values
"""

import subprocess
import sys
import json
from typing import Dict, List, Optional

class GCPConfigValidator:
    """Validates GCP staging deployment configuration"""
    
    CRITICAL_BACKEND_VARS = [
        'SERVICE_SECRET',
        'JWT_SECRET_KEY', 
        'DATABASE_URL',
        'REDIS_URL',
        'ENVIRONMENT'
    ]
    
    CRITICAL_AUTH_VARS = [
        'JWT_SECRET_KEY',
        'GOOGLE_OAUTH_CLIENT_ID_STAGING',
        'GOOGLE_OAUTH_CLIENT_SECRET_STAGING'
    ]
    
    def __init__(self, project: str = "netra-staging"):
        self.project = project
        self.errors = []
        self.warnings = []
    
    def validate_service_config(self, service_name: str, required_vars: List[str]) -> bool:
        """Validate environment variables for a service"""
        print(f"🔍 Validating {service_name} configuration...")
        
        try:
            # Get service configuration
            cmd = [
                'gcloud', 'run', 'services', 'describe', service_name,
                '--project', self.project,
                '--region', 'us-central1',
                '--format', 'json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            config = json.loads(result.stdout)
            
            # Extract environment variables
            containers = config.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
            if not containers:
                self.errors.append(f"{service_name}: No containers found")
                return False
            
            env_vars = {env.get('name'): env.get('value') for env in containers[0].get('env', [])}
            
            # Check required variables
            missing_vars = []
            for var in required_vars:
                if var not in env_vars:
                    missing_vars.append(var)
                elif not env_vars[var]:
                    missing_vars.append(f"{var} (empty)")
            
            if missing_vars:
                self.errors.append(f"{service_name}: Missing critical vars: {', '.join(missing_vars)}")
                return False
            
            print(f"✅ {service_name}: All critical variables present")
            return True
            
        except subprocess.CalledProcessError as e:
            self.errors.append(f"{service_name}: Failed to get configuration: {e}")
            return False
        except Exception as e:
            self.errors.append(f"{service_name}: Validation error: {e}")
            return False
    
    def test_service_connectivity(self) -> bool:
        """Test inter-service connectivity"""
        print("🔗 Testing service connectivity...")
        
        # Test endpoints
        endpoints = {
            'backend': 'https://api.staging.netrasystems.ai/health',
            'auth': 'https://auth.staging.netrasystems.ai/health'
        }
        
        all_healthy = True
        for service, url in endpoints.items():
            try:
                result = subprocess.run([
                    'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', url
                ], capture_output=True, text=True, timeout=10)
                
                if result.stdout.strip() == '200':
                    print(f"✅ {service}: Healthy")
                else:
                    self.errors.append(f"{service}: Unhealthy (HTTP {result.stdout.strip()})")
                    all_healthy = False
                    
            except subprocess.TimeoutExpired:
                self.errors.append(f"{service}: Timeout")
                all_healthy = False
            except Exception as e:
                self.errors.append(f"{service}: Connection error: {e}")
                all_healthy = False
        
        return all_healthy
    
    def validate_all(self) -> bool:
        """Run complete validation suite"""
        print("🚀 Starting GCP Staging Deployment Validation")
        print("=" * 50)
        
        # Validate backend configuration
        backend_valid = self.validate_service_config(
            'netra-backend-staging', 
            self.CRITICAL_BACKEND_VARS
        )
        
        # Validate auth configuration  
        auth_valid = self.validate_service_config(
            'netra-auth-service-pnovr5vsba-uc',
            self.CRITICAL_AUTH_VARS
        )
        
        # Test connectivity
        connectivity_valid = self.test_service_connectivity()
        
        # Report results
        print("\n📊 Validation Results")
        print("=" * 30)
        
        if self.errors:
            print("❌ CRITICAL ERRORS:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("⚠️ WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        all_valid = backend_valid and auth_valid and connectivity_valid
        
        if all_valid:
            print("✅ ALL VALIDATIONS PASSED - Deployment is safe")
        else:
            print("❌ VALIDATION FAILED - DO NOT DEPLOY")
        
        return all_valid

if __name__ == "__main__":
    validator = GCPConfigValidator()
    success = validator.validate_all()
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/validate_gcp_deployment.py

# Run validation
python3 scripts/validate_gcp_deployment.py
```

### 🛡️ STEP 7: Create Configuration Monitoring

**Implement Real-time Configuration Monitoring:**
```bash
# Create monitoring alert for critical configuration
cat > monitoring/gcp_staging_config_monitor.py << 'EOF'
#!/usr/bin/env python3
"""
Real-time GCP staging configuration monitor
Alerts when critical configuration is missing or incorrect
"""

import time
import subprocess
import json
from datetime import datetime
from typing import Dict, List

class ConfigMonitor:
    """Monitor GCP staging configuration health"""
    
    def __init__(self):
        self.last_check = None
        self.alert_cooldown = 300  # 5 minutes
        self.last_alert = None
    
    def check_service_secret(self) -> bool:
        """Check if SERVICE_SECRET is properly configured"""
        try:
            cmd = [
                'gcloud', 'run', 'services', 'describe', 'netra-backend-staging',
                '--project', 'netra-staging',
                '--region', 'us-central1',
                '--format', 'value(spec.template.spec.containers[0].env[?(@.name=="SERVICE_SECRET")].name)'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return bool(result.stdout.strip())
        except:
            return False
    
    def send_alert(self, message: str):
        """Send critical alert"""
        timestamp = datetime.now().isoformat()
        alert_message = f"🚨 GCP STAGING CRITICAL: {message} - {timestamp}"
        
        # Log to console (extend with actual alerting system)
        print(alert_message)
        
        # Could extend with:
        # - Slack webhooks
        # - Email notifications
        # - PagerDuty integration
        
        self.last_alert = datetime.now()
    
    def monitor_loop(self):
        """Main monitoring loop"""
        print("🔍 Starting GCP staging configuration monitor...")
        
        while True:
            try:
                self.last_check = datetime.now()
                
                # Check SERVICE_SECRET
                if not self.check_service_secret():
                    if (not self.last_alert or 
                        (datetime.now() - self.last_alert).seconds > self.alert_cooldown):
                        self.send_alert("SERVICE_SECRET missing from netra-backend-staging")
                else:
                    print(f"✅ Configuration healthy - {self.last_check.strftime('%H:%M:%S')}")
                
                # Sleep for 1 minute
                time.sleep(60)
                
            except KeyboardInterrupt:
                print("Monitor stopped by user")
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    monitor = ConfigMonitor()
    monitor.monitor_loop()
EOF

chmod +x monitoring/gcp_staging_config_monitor.py
```

---

## Phase 4: Integration Testing (2-4 Hours)

### 🧪 STEP 8: Comprehensive Integration Tests

**Run Complete Test Suite:**
```bash
# Test WebSocket connectivity
python tests/mission_critical/test_websocket_agent_events_suite.py

# Test agent execution flow
python tests/integration/test_agent_orchestration_flow.py

# Test authentication flow
python tests/integration/test_oauth_token_flow.py

# Verify no regressions
python tests/unified_test_runner.py --category integration --env staging
```

### 🧪 STEP 9: Load Testing and Monitoring

**Stress Test Recovered System:**
```bash
# Create basic load test
cat > test_staging_load.py << 'EOF'
#!/usr/bin/env python3
"""Basic load test for staging recovery validation"""

import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def test_endpoint(session, url):
    """Test single endpoint"""
    try:
        async with session.get(url) as response:
            return response.status == 200
    except:
        return False

async def load_test():
    """Run load test against staging"""
    endpoints = [
        "https://api.staging.netrasystems.ai/health",
        "https://api.staging.netrasystems.ai/api/discovery",
        "https://auth.staging.netrasystems.ai/health",
        "https://auth.staging.netrasystems.ai/api/auth/config"
    ]
    
    async with aiohttp.ClientSession() as session:
        # Test 100 concurrent requests
        tasks = []
        for _ in range(25):  # 25 iterations
            for endpoint in endpoints:
                tasks.append(test_endpoint(session, endpoint))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        success_count = sum(results)
        total_requests = len(results)
        duration = end_time - start_time
        
        print(f"Load Test Results:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {total_requests - success_count}")
        print(f"  Success Rate: {success_count/total_requests*100:.1f}%")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Requests/sec: {total_requests/duration:.1f}")
        
        if success_count / total_requests >= 0.95:
            print("✅ Load test PASSED")
            return True
        else:
            print("❌ Load test FAILED - success rate too low")
            return False

if __name__ == "__main__":
    asyncio.run(load_test())
EOF

python3 test_staging_load.py
```

---

## Phase 5: Documentation and Prevention

### 📚 STEP 10: Update Configuration Documentation

**Update MISSION_CRITICAL_NAMED_VALUES_INDEX:**
```xml
<!-- Add to SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml -->
<environment_variables>
  <variable name="SERVICE_SECRET" type="env_var" criticality="ULTRA_CRITICAL">
    <description>Inter-service authentication secret for backend-to-auth communication</description>
    <cascade_impact>Without this: Complete authentication failure, circuit breaker open, 100% user lockout</cascade_impact>
    <required_by>
      <service>netra-backend-staging</service>
      <service>netra-backend-production</service>
    </required_by>
    <incident_history>
      <incident date="2025-09-05" severity="CRITICAL">
        <description>Missing SERVICE_SECRET caused complete staging outage</description>
        <duration>Multiple hours</duration>
        <impact>100% user authentication failure</impact>
      </incident>
    </incident_history>
  </variable>
</environment_variables>
```

### 📚 STEP 11: Create Incident Response Playbook

**Document Recovery Procedures:**
```markdown
# GCP Staging Service Secret Incident Response Playbook

## Symptoms
- Continuous "Circuit breaker is open" errors in logs
- "Service Secret configured: False" messages
- All API endpoints returning authentication errors
- No users can log in or access system

## Immediate Response (< 5 minutes)
1. Check SERVICE_SECRET presence:
   ```bash
   gcloud run services describe netra-backend-staging \
     --project=netra-staging --region=us-central1 \
     --format="value(spec.template.spec.containers[0].env[?(@.name=='SERVICE_SECRET')].name)"
   ```

2. If missing, deploy immediately:
   ```bash
   gcloud run services update netra-backend-staging \
     --project=netra-staging --region=us-central1 \
     --set-env-vars="SERVICE_SECRET=[VALUE_FROM_SECRET_MANAGER]"
   ```

3. Monitor recovery:
   ```bash
   gcloud logging read --project=netra-staging \
     --filter="resource.labels.service_name=netra-backend-staging" \
     --limit=20 --format="value(textPayload)"
   ```

## Validation (< 10 minutes)
- Run: `python3 scripts/validate_gcp_deployment.py`
- Test: `curl -I https://api.staging.netrasystems.ai/health`
- Verify: No circuit breaker errors in logs

## Post-incident (< 30 minutes)
- Document root cause
- Update monitoring alerts
- Review deployment process
- Conduct blameless retrospective
```

---

## Success Criteria

### ✅ Phase 1 Success (Emergency Recovery)
- [ ] SERVICE_SECRET environment variable present
- [ ] Backend service restarted successfully  
- [ ] No "Circuit breaker is open" errors in logs
- [ ] Auth service responding to health checks

### ✅ Phase 2 Success (System Validation)
- [ ] All critical environment variables present
- [ ] Backend health endpoint returns 200
- [ ] Auth service health endpoint returns 200
- [ ] Service discovery endpoint returns 200
- [ ] OAuth configuration endpoint returns 200

### ✅ Phase 3 Success (Prevention)
- [ ] Pre-deployment validation script created
- [ ] Configuration monitoring implemented
- [ ] Critical environment variables documented
- [ ] Alert system configured

### ✅ Phase 4 Success (Testing)
- [ ] Integration test suite passes
- [ ] WebSocket functionality verified
- [ ] Load test shows >95% success rate
- [ ] No regressions detected

### ✅ Phase 5 Success (Documentation)
- [ ] MISSION_CRITICAL_NAMED_VALUES_INDEX updated
- [ ] Incident response playbook created
- [ ] Configuration dependency map updated
- [ ] Team notified of new procedures

---

## Monitoring and Alerting

### Real-time Monitoring
1. **SERVICE_SECRET presence check** - Every minute
2. **Circuit breaker state monitoring** - Every 30 seconds  
3. **Inter-service auth success rate** - Continuous
4. **Critical endpoint health** - Every minute

### Alert Thresholds
- **CRITICAL:** SERVICE_SECRET missing
- **CRITICAL:** Circuit breaker open >30 seconds
- **CRITICAL:** Auth success rate <90%
- **WARNING:** Any critical environment variable changed
- **INFO:** New deployment detected

---

## Timeline Summary

| Phase | Duration | Priority | Dependencies |
|-------|----------|----------|--------------|
| 1. Emergency Recovery | 0-30 min | CRITICAL | GCP access, secret values |
| 2. System Validation | 30-60 min | HIGH | Phase 1 complete |
| 3. Prevention | 1-4 hours | HIGH | Validation passing |
| 4. Integration Testing | 2-4 hours | MEDIUM | System stable |
| 5. Documentation | 2-4 hours | MEDIUM | All phases complete |

**Total Recovery Time: 30 minutes to basic functionality**  
**Total Hardening Time: 4-6 hours for complete prevention**

---

**This remediation plan addresses both the immediate crisis and long-term prevention. Execute Phase 1 immediately to restore service, then proceed through subsequent phases to prevent recurrence.**