# Deployment Verification Checklist

## Pre-Deployment Checks

### 1. Code Quality Gates
- [ ] All tests passing locally
  ```bash
  python tests/unified_test_runner.py --categories smoke unit integration --real-services
  ```
- [ ] Mission critical tests passing
  ```bash
  python tests/mission_critical/test_websocket_agent_events_suite.py
  ```
- [ ] Architecture compliance check
  ```bash
  python scripts/check_architecture_compliance.py
  ```
- [ ] Auth SSOT compliance
  ```bash
  python scripts/check_auth_ssot_compliance.py
  ```

### 2. Configuration Verification
- [ ] Check MISSION_CRITICAL_NAMED_VALUES_INDEX.xml reviewed
- [ ] SERVICE_ID = "netra-backend" (no timestamps)
- [ ] Environment variables set correctly:
  - [ ] NEXT_PUBLIC_API_URL
  - [ ] NEXT_PUBLIC_WS_URL  
  - [ ] NEXT_PUBLIC_AUTH_URL
  - [ ] NEXT_PUBLIC_ENVIRONMENT
- [ ] OAuth credentials present for target environment
- [ ] JWT secret configured and stable
- [ ] Database URLs correct for environment
- [ ] Redis URLs correct for environment

### 3. Docker Images
- [ ] Backend image builds successfully
- [ ] Auth service image builds successfully
- [ ] Frontend image builds successfully
- [ ] All images tagged correctly
- [ ] Resource limits set appropriately

## Deployment Process

### 4. Staging Deployment
- [ ] Deploy to staging first
  ```bash
  python scripts/deploy_to_gcp.py --project netra-staging --build-local
  ```
- [ ] Check deployment logs for errors
- [ ] Verify all services started successfully
- [ ] Check GCP Cloud Run console for service status

### 5. Staging Validation
- [ ] Frontend loads without errors
- [ ] Login/OAuth flow works
- [ ] Create new user account successfully
- [ ] Run test agent conversation
- [ ] Verify WebSocket events received:
  - [ ] agent_started
  - [ ] agent_thinking
  - [ ] tool_executing
  - [ ] tool_completed
  - [ ] agent_completed
- [ ] Check multi-user isolation (2+ users simultaneously)
- [ ] Verify no cross-user data leakage

### 6. Health Checks
- [ ] Backend health endpoint responding
  ```bash
  curl https://api.staging.netrasystems.ai/health
  ```
- [ ] Auth service health endpoint responding
  ```bash
  curl https://auth.staging.netrasystems.ai/health
  ```
- [ ] WebSocket connection establishes
- [ ] Database connections stable
- [ ] Redis connections stable

### 7. Performance Validation
- [ ] Page load time < 3 seconds
- [ ] Agent response time < 5 seconds for simple queries
- [ ] WebSocket latency < 100ms
- [ ] No memory leaks observed
- [ ] CPU usage stable

## Production Deployment

### 8. Pre-Production Final Checks
- [ ] Staging validated for at least 24 hours
- [ ] No critical bugs in staging
- [ ] Rollback plan documented
- [ ] Team notified of deployment window
- [ ] Database backup completed

### 9. Production Deployment
- [ ] Deploy to production
  ```bash
  python scripts/deploy_to_gcp.py --project netra-production --build-local
  ```
- [ ] Monitor deployment logs
- [ ] Verify zero-downtime deployment
- [ ] Check service health immediately

### 10. Production Validation
- [ ] All staging validation steps repeated
- [ ] Monitor error rates for 30 minutes
- [ ] Check user reports/feedback
- [ ] Verify billing/metering working
- [ ] Confirm analytics tracking

## Post-Deployment

### 11. Monitoring Setup
- [ ] Error alerts configured
- [ ] Performance alerts configured
- [ ] Uptime monitoring active
- [ ] Log aggregation working
- [ ] Metrics dashboards updated

### 12. Documentation Updates
- [ ] Deployment notes added to changelog
- [ ] Known issues documented
- [ ] Runbook updated if needed
- [ ] Team briefed on changes

## Rollback Criteria

Immediate rollback if any of these occur:
- [ ] Authentication completely broken
- [ ] WebSocket events not firing
- [ ] Database connection failures
- [ ] Error rate > 5% of requests
- [ ] Response time > 10x normal
- [ ] Memory usage growing unbounded
- [ ] User data corruption detected

## Rollback Procedure

1. **Immediate Actions**:
   ```bash
   # Revert to previous Cloud Run revision
   gcloud run services update-traffic backend --to-revisions=PREVIOUS_REVISION=100
   gcloud run services update-traffic auth-service --to-revisions=PREVIOUS_REVISION=100
   gcloud run services update-traffic frontend --to-revisions=PREVIOUS_REVISION=100
   ```

2. **Verification**:
   - [ ] Services responding normally
   - [ ] Error rates returning to baseline
   - [ ] Users able to access system

3. **Investigation**:
   - [ ] Capture logs from failed deployment
   - [ ] Document root cause
   - [ ] Create fix in development
   - [ ] Add regression test

## Environment-Specific URLs

### Staging
- Frontend: https://staging.netrasystems.ai
- Backend API: https://api.staging.netrasystems.ai
- Auth Service: https://auth.staging.netrasystems.ai
- WebSocket: wss://api.staging.netrasystems.ai

### Production
- Frontend: https://netrasystems.ai
- Backend API: https://api.netrasystems.ai
- Auth Service: https://auth.netrasystems.ai
- WebSocket: wss://api.netrasystems.ai

## Critical Files to Check

Before any deployment, verify these files:
1. `scripts/deploy_to_gcp.py` - Deployment configuration
2. `frontend/.env.staging` / `frontend/.env.production` - Frontend env
3. `netra_backend/app/core/configuration/services.py` - Service config
4. `auth_service/auth_core/configuration.py` - Auth config
5. `docker-compose.yml` - Local development setup
6. `SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml` - Critical values

## Emergency Contacts

- On-call Engineer: [Rotation Schedule]
- Infrastructure Team: [Contact]
- Database Admin: [Contact]
- Security Team: [Contact]

## Deployment Sign-off

- [ ] Pre-deployment checks completed
- [ ] Staging validation completed
- [ ] Production deployment completed
- [ ] Post-deployment monitoring active
- [ ] Team notified of successful deployment

Deployed by: _______________
Date/Time: _______________
Version: _______________
Notes: _______________