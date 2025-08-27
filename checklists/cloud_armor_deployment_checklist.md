# Cloud Armor Pre/Post Deployment Checklist

## Pre-Deployment Checklist

### 🔍 Before ANY Cloud Armor Changes

#### 1. Current State Analysis (5 min)
- [ ] Run baseline analysis of current blocks
  ```bash
  python scripts/analyze_cloud_armor_logs.py --summary --limit 100
  ```
- [ ] Document current OAuth success rate
  ```bash
  python scripts/analyze_cloud_armor_logs.py --oauth --limit 50
  ```
- [ ] Export current security policy
  ```bash
  gcloud compute security-policies export staging-security-policy \
    --file-name=security-policy-backup-$(date +%Y%m%d).yaml \
    --project=netra-staging
  ```

#### 2. Change Planning (10 min)
- [ ] Document the specific issue being addressed
- [ ] Identify the rule causing false positives (rule ID: ____________)
- [ ] Review proposed exception rule syntax
- [ ] Verify exception rule priority (must be < blocking rule priority)
- [ ] Consider security implications of exception

#### 3. Testing Plan (5 min)
- [ ] Identify test cases for legitimate traffic
- [ ] Identify test cases that should remain blocked
- [ ] Prepare rollback command
- [ ] Notify team of upcoming change

### 📝 Change Implementation

#### 1. Staging Deployment
- [ ] Apply change to staging first
  ```bash
  gcloud compute security-policies rules create [PRIORITY] \
    --security-policy=staging-security-policy \
    --action=[ACTION] \
    --expression="[EXPRESSION]" \
    --description="[DESCRIPTION]" \
    --project=netra-staging
  ```
- [ ] Document the exact command used: ________________________________
- [ ] Record rule priority number: ___________
- [ ] Screenshot the confirmation

#### 2. Immediate Validation (5 min)
- [ ] Verify rule was created
  ```bash
  gcloud compute security-policies rules describe [PRIORITY] \
    --security-policy=staging-security-policy \
    --project=netra-staging
  ```
- [ ] Test the specific flow that was blocked
- [ ] Check that other security remains active

## Post-Deployment Checklist

### ✅ Within 5 Minutes

#### 1. Functional Testing
- [ ] Test OAuth login flow manually
  - [ ] Open incognito browser
  - [ ] Navigate to staging site
  - [ ] Complete Google sign-in
  - [ ] Verify successful redirect
- [ ] Run automated OAuth test
  ```bash
  python tests/e2e/test_oauth_cloud_armor.py staging
  ```

#### 2. Security Validation
- [ ] Verify SQL injection still blocked on other paths
  ```bash
  curl "https://api.staging.netrasystems.ai/api/test?id=1'+OR+'1'='1"
  # Should return 403
  ```
- [ ] Check no new security gaps introduced

#### 3. Log Analysis
- [ ] Check for any new 403 errors
  ```bash
  python scripts/analyze_cloud_armor_logs.py --denied --limit 20
  ```
- [ ] Verify OAuth callbacks working
  ```bash
  python scripts/analyze_cloud_armor_logs.py --oauth --limit 10
  ```
- [ ] No unexpected blocked patterns

### 📊 Within 30 Minutes

#### 1. Metrics Verification
- [ ] OAuth success rate back to normal (> 95%)
- [ ] No increase in other 403 errors
- [ ] API latency unchanged
- [ ] No new error patterns in application logs

#### 2. Extended Testing
- [ ] Test from different browsers
  - [ ] Chrome
  - [ ] Firefox
  - [ ] Safari
  - [ ] Edge
- [ ] Test from different network locations (VPN)
- [ ] Test mobile OAuth flow if applicable

#### 3. Documentation
- [ ] Update SPEC/cloud_armor_security.xml
- [ ] Update team documentation
- [ ] Create incident report if this was fixing an outage
- [ ] Update runbook with any new learnings

### 📈 Within 24 Hours

#### 1. Monitoring Setup
- [ ] Verify monitoring alerts configured
  ```yaml
  Alert: OAuth 403 rate > 5% 
  Action: Page on-call
  ```
- [ ] Dashboard shows OAuth metrics
- [ ] Log aggregation capturing patterns

#### 2. Performance Analysis
- [ ] Compare before/after metrics
  - [ ] Total 403 errors: Before _____ After _____
  - [ ] OAuth success: Before _____ After _____
  - [ ] False positive rate: Before _____ After _____
- [ ] Identify any unexpected changes

#### 3. Team Communication
- [ ] Send summary to team
  ```
  Subject: Cloud Armor Update - OAuth Exception Rule Added
  
  Issue: [Brief description]
  Solution: [What was implemented]
  Impact: [Current status]
  Testing: [Results]
  ```
- [ ] Update status page if applicable
- [ ] Close related tickets

## Rollback Procedure

### 🚨 If Issues Detected

#### Immediate Rollback (< 2 min)
```bash
# Remove the exception rule
gcloud compute security-policies rules delete [PRIORITY] \
  --security-policy=staging-security-policy \
  --project=netra-staging \
  --quiet

# OR restore from backup
gcloud compute security-policies import staging-security-policy \
  --file-name=security-policy-backup-[DATE].yaml \
  --project=netra-staging
```

#### Rollback Verification
- [ ] Confirm rule removed
- [ ] Test that original behavior restored
- [ ] Document why rollback was needed
- [ ] Plan alternative approach

## Production Deployment

### 🎯 Only After Staging Success

#### Prerequisites (All must be checked)
- [ ] Staging running successfully for 24+ hours
- [ ] Zero OAuth failures in staging
- [ ] Security review completed
- [ ] Rollback plan tested in staging
- [ ] Team notified of maintenance window

#### Production Steps
1. [ ] Create backup of production policy
2. [ ] Apply same rule to production
3. [ ] Run immediate validation
4. [ ] Monitor for 1 hour
5. [ ] Send completion report

## Quick Reference Commands

```bash
# View current rules
gcloud compute security-policies rules list \
  --security-policy=staging-security-policy \
  --project=netra-staging

# Check recent blocks
python scripts/analyze_cloud_armor_logs.py --denied --limit 50

# Test OAuth flow
python tests/e2e/test_oauth_cloud_armor.py staging

# Emergency allow all (DO NOT USE IN PRODUCTION)
gcloud compute security-policies rules create 1 \
  --security-policy=staging-security-policy \
  --action=allow \
  --expression="true" \
  --description="EMERGENCY: Temporary allow all" \
  --project=netra-staging
```

## Sign-off Requirements

### Staging Deployment
- [ ] Engineer: _________________ Date: ________
- [ ] Verified by: ______________ Date: ________

### Production Deployment
- [ ] Engineer: _________________ Date: ________
- [ ] Security: _________________ Date: ________
- [ ] SRE: _____________________ Date: ________

## Notes Section

_Use this space to document any specific observations, issues, or learnings:_

_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

---
Last Updated: 2025-08-27
Version: 1.0