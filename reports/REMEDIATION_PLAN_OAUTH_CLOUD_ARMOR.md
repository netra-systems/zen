# OAuth Cloud Armor Remediation Test Plan

## Executive Summary
This plan ensures the OAuth callback exception rule is working correctly and establishes ongoing monitoring to prevent regression.

## Phase 1: Immediate Validation (Today)

### 1.1 Manual OAuth Flow Testing
**Owner:** Engineering Team  
**Timeline:** Immediate (30 minutes)

```bash
# Test OAuth login flow in staging
1. Open incognito browser
2. Navigate to https://staging.netrasystems.ai
3. Click "Sign in with Google"
4. Complete authentication
5. Verify successful redirect and login

# Verify in logs (no 403s should appear)
python scripts/analyze_cloud_armor_logs.py --oauth --limit 10
```

**Success Criteria:**
- [ ] OAuth login completes successfully
- [ ] No 403 errors in Cloud Armor logs for /auth/callback
- [ ] User session is established correctly

### 1.2 Security Rule Validation
**Owner:** Security Team  
**Timeline:** 1 hour

```bash
# Verify exception rule is active
gcloud compute security-policies rules describe 50 \
  --security-policy=staging-security-policy \
  --project=netra-staging

# Verify SQL injection protection still active for other paths
python scripts/analyze_cloud_armor_logs.py --rule "id942432" --limit 20
```

**Success Criteria:**
- [ ] Exception rule exists at priority 50
- [ ] SQL injection rules still blocking other suspicious requests
- [ ] No unintended security gaps introduced

## Phase 2: Automated Testing (Within 24 hours)

### 2.1 E2E OAuth Test Implementation
**Owner:** QA Team  
**Timeline:** 4 hours

Create automated test: `tests/e2e/test_oauth_cloud_armor.py`

```python
import asyncio
import aiohttp
import pytest
from typing import Dict, Optional
import json
import subprocess
from datetime import datetime, timezone, timedelta

class OAuthCloudArmorTest:
    """Test OAuth flow and Cloud Armor integration."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.base_url = self._get_base_url(environment)
        
    def _get_base_url(self, env: str) -> str:
        urls = {
            "staging": "https://auth.staging.netrasystems.ai",
            "production": "https://auth.netrasystems.ai"
        }
        return urls.get(env, urls["staging"])
    
    async def test_oauth_callback_not_blocked(self):
        """Test that OAuth callback with encoded parameters is not blocked."""
        # Simulate OAuth callback with encoded parameters
        callback_url = f"{self.base_url}/auth/callback"
        params = {
            "state": "test_state_123",
            "code": "4/0AVMBsJtest_code_with_encoded_slash",  # Pattern that triggered block
            "scope": "email profile openid"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(callback_url, params=params, allow_redirects=False) as response:
                # Should not get 403 from Cloud Armor
                assert response.status != 403, f"OAuth callback blocked: {response.status}"
                # May get redirect or other status, but not 403
                return response.status
    
    def check_cloud_armor_logs(self, minutes_back: int = 5) -> Dict:
        """Check Cloud Armor logs for recent blocks."""
        cmd = [
            "python", "scripts/analyze_cloud_armor_logs.py",
            "--oauth", "--limit", "10", "--hours", "1"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse output for 403 errors
        blocked_count = result.stdout.count("Status: 403")
        return {
            "blocked_requests": blocked_count,
            "output": result.stdout
        }
    
    async def test_sql_injection_still_blocked(self):
        """Ensure SQL injection attempts are still blocked on other paths."""
        # Test a path that should still be protected
        test_url = f"{self.base_url}/api/users"
        
        # Actual SQL injection attempt (should be blocked)
        malicious_params = {
            "id": "1' OR '1'='1"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url, params=malicious_params, allow_redirects=False) as response:
                # This SHOULD be blocked
                assert response.status == 403, f"SQL injection not blocked: {response.status}"
                return response.status
    
    async def run_test_suite(self):
        """Run complete test suite."""
        print(f"Testing OAuth Cloud Armor integration in {self.environment}...")
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": self.environment,
            "tests": {}
        }
        
        # Test 1: OAuth callback should work
        try:
            status = await self.test_oauth_callback_not_blocked()
            results["tests"]["oauth_callback"] = {
                "status": "PASSED",
                "http_status": status
            }
            print("✓ OAuth callback test passed")
        except AssertionError as e:
            results["tests"]["oauth_callback"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"✗ OAuth callback test failed: {e}")
        
        # Test 2: Check logs for blocks
        log_check = self.check_cloud_armor_logs()
        results["tests"]["log_check"] = {
            "blocked_requests": log_check["blocked_requests"]
        }
        print(f"  Found {log_check['blocked_requests']} blocked OAuth requests in last hour")
        
        # Test 3: SQL injection should still be blocked
        try:
            status = await self.test_sql_injection_still_blocked()
            results["tests"]["sql_injection_protection"] = {
                "status": "PASSED",
                "http_status": status
            }
            print("✓ SQL injection protection still active")
        except AssertionError as e:
            results["tests"]["sql_injection_protection"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"✗ SQL injection protection test failed: {e}")
        
        # Save results
        with open(f"oauth_test_results_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(results, f, indent=2)
        
        return results

# Test runner
if __name__ == "__main__":
    test = OAuthCloudArmorTest("staging")
    results = asyncio.run(test.run_test_suite())
    
    # Exit with error if any test failed
    if any(t.get("status") == "FAILED" for t in results["tests"].values()):
        exit(1)
```

### 2.2 Integration with CI/CD
**Owner:** DevOps Team  
**Timeline:** 2 hours

Add to `.github/workflows/staging-deploy.yml`:

```yaml
- name: Test OAuth Flow Post-Deployment
  run: |
    python tests/e2e/test_oauth_cloud_armor.py
  env:
    ENVIRONMENT: staging

- name: Check Cloud Armor Blocks
  run: |
    python scripts/analyze_cloud_armor_logs.py --summary --limit 100
    
- name: Validate Security Rules
  run: |
    gcloud compute security-policies rules list \
      --security-policy=staging-security-policy \
      --project=netra-staging \
      --format="table(priority,action,description)"
```

## Phase 3: Monitoring Setup (Within 48 hours)

### 3.1 Alert Configuration
**Owner:** SRE Team  
**Timeline:** 2 hours

Create Cloud Monitoring alert:

```yaml
# monitoring/oauth_403_alert.yaml
displayName: "OAuth Callback 403 Errors"
conditions:
  - displayName: "OAuth endpoint blocked"
    conditionThreshold:
      filter: |
        resource.type="http_load_balancer"
        jsonPayload.statusDetails="denied_by_security_policy"
        httpRequest.path="/auth/callback"
      comparison: COMPARISON_GT
      thresholdValue: 5
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE

notificationChannels:
  - projects/netra-staging/notificationChannels/[CHANNEL_ID]

documentation:
  content: |
    OAuth callbacks are being blocked by Cloud Armor.
    
    Immediate Actions:
    1. Run: python scripts/analyze_cloud_armor_logs.py --oauth
    2. Check security policy priority 50 rule
    3. If legitimate traffic blocked, follow CLOUD_ARMOR_TROUBLESHOOTING.md
```

### 3.2 Dashboard Creation
**Owner:** Platform Team  
**Timeline:** 3 hours

```python
# scripts/create_oauth_monitoring_dashboard.py
from google.cloud import monitoring_dashboard_v1
import json

def create_oauth_dashboard(project_id: str):
    """Create monitoring dashboard for OAuth and Cloud Armor."""
    
    dashboard_config = {
        "displayName": "OAuth Cloud Armor Monitoring",
        "mosaicLayout": {
            "columns": 12,
            "tiles": [
                {
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "OAuth Callback 403 Errors (Last 24h)",
                        "xyChart": {
                            "dataSets": [{
                                "timeSeriesQuery": {
                                    "timeSeriesFilter": {
                                        "filter": 'resource.type="http_load_balancer" '
                                                 'jsonPayload.statusDetails="denied_by_security_policy" '
                                                 'httpRequest.path="/auth/callback"'
                                    }
                                }
                            }]
                        }
                    }
                },
                {
                    "xPos": 6,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Successful OAuth Logins",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": 'resource.type="http_load_balancer" '
                                             'httpRequest.path="/auth/callback" '
                                             'httpRequest.status=200'
                                }
                            }
                        }
                    }
                },
                {
                    "yPos": 4,
                    "width": 12,
                    "height": 4,
                    "widget": {
                        "title": "Top Blocked OWASP Rules",
                        "pieChart": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": 'resource.type="http_load_balancer" '
                                             'jsonPayload.enforcedSecurityPolicy.preconfiguredExprIds!=""'
                                }
                            }
                        }
                    }
                }
            ]
        }
    }
    
    client = monitoring_dashboard_v1.DashboardsServiceClient()
    project_name = f"projects/{project_id}"
    
    dashboard = client.create_dashboard(
        parent=project_name,
        dashboard=dashboard_config
    )
    
    print(f"Dashboard created: {dashboard.name}")
    return dashboard

if __name__ == "__main__":
    create_oauth_dashboard("netra-staging")
```

## Phase 4: Regular Testing Cadence

### 4.1 Daily Automated Tests
**Schedule:** Every 6 hours via cron/GitHub Actions

```yaml
# .github/workflows/oauth-health-check.yml
name: OAuth Health Check

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:  # Manual trigger

jobs:
  test-oauth:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install aiohttp pytest
      
      - name: Run OAuth tests
        run: |
          python tests/e2e/test_oauth_cloud_armor.py
      
      - name: Check for 403 errors
        run: |
          python scripts/analyze_cloud_armor_logs.py --oauth --limit 20
      
      - name: Alert on failure
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          status: failure
          text: 'OAuth Cloud Armor test failed!'
```

### 4.2 Weekly Security Review
**Owner:** Security Team  
**Schedule:** Every Monday 10 AM

Checklist:
- [ ] Review Cloud Armor blocked requests summary
- [ ] Check for new false positive patterns
- [ ] Validate all exception rules still necessary
- [ ] Review any manual rule changes
- [ uncomfortable with

```bash
# Weekly review script
python scripts/analyze_cloud_armor_logs.py --summary --limit 1000 --hours 168
```

## Phase 5: Documentation and Training

### 5.1 Runbook Creation
**Owner:** Platform Team  
**Timeline:** 1 day

Create `runbooks/oauth-403-response.md`:

```markdown
# OAuth 403 Error Response Runbook

## Alert: OAuth Callbacks Being Blocked

### Immediate Actions (< 5 minutes)

1. **Verify the issue**
   ```bash
   python scripts/analyze_cloud_armor_logs.py --oauth --limit 10
   ```

2. **Check exception rule status**
   ```bash
   gcloud compute security-policies rules describe 50 \
     --security-policy=staging-security-policy \
     --project=netra-staging
   ```

3. **Emergency mitigation** (if needed)
   ```bash
   # Temporarily increase exception priority
   gcloud compute security-policies rules update 50 \
     --security-policy=staging-security-policy \
     --priority=1 \
     --project=netra-staging
   ```

### Investigation (< 30 minutes)

1. Analyze pattern of blocks
2. Check for recent changes to security policy
3. Verify OAuth provider hasn't changed format
4. Review recent deployments

### Resolution

1. Update exception rule if pattern changed
2. Test OAuth flow manually
3. Run automated tests
4. Document changes
```

### 5.2 Team Training
**Owner:** Engineering Lead  
**Timeline:** 1 week

Training sessions:
- [ ] Cloud Armor basics and rule priorities
- [ ] Using the log analysis tool
- [ ] Debugging 403 errors
- [ ] Creating and testing exception rules

## Success Metrics

### Week 1 Targets
- Zero OAuth 403 errors in staging
- Automated tests running every 6 hours
- Alert configured and tested

### Month 1 Targets
- < 1% false positive rate for legitimate traffic
- < 5 minute mean time to detect (MTTD)
- < 30 minute mean time to resolve (MTTR)

### Ongoing Targets
- 99.9% OAuth availability
- Zero security incidents from exceptions
- Quarterly security rule review completed

## Rollback Plan

If the exception rule causes security concerns:

```bash
# Remove exception rule
gcloud compute security-policies rules delete 50 \
  --security-policy=staging-security-policy \
  --project=netra-staging

# Or update to more restrictive
gcloud compute security-policies rules update 50 \
  --expression="request.path == '/auth/callback' && request.method == 'GET'" \
  --project=netra-staging
```

## Sign-offs

- [ ] Engineering: ___________________ Date: ________
- [ ] Security: _____________________ Date: ________
- [ ] SRE: _________________________ Date: ________
- [ ] Product: ______________________ Date: ________

## Appendix

### Related Documents
- `SPEC/cloud_armor_security.xml`
- `docs/CLOUD_ARMOR_TROUBLESHOOTING.md`
- `scripts/analyze_cloud_armor_logs.py`

### Contact Points
- Security Team: security@netrasystems.ai
- Platform Team: platform@netrasystems.ai
- On-call: Use PagerDuty

### Change Log
- 2025-08-27: Initial plan created
- 2025-08-27: Exception rule added at priority 50