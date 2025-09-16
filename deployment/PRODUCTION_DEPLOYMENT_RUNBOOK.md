# Production Deployment Runbook: Request Isolation Features
## Zero-Downtime Rollout Operations Guide

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Deployment Commands Reference](#deployment-commands-reference)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Rollback Procedures](#rollback-procedures)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Post-Deployment Tasks](#post-deployment-tasks)
8. [Emergency Contacts](#emergency-contacts)

---

## Executive Summary

This runbook provides step-by-step instructions for deploying request isolation features to production with zero downtime. The deployment uses a 5-stage canary rollout with comprehensive monitoring and instant rollback capabilities.

**Business Impact**: Eliminates cascade failures, ensures 99.9% uptime, enables robust concurrent execution.

**Deployment Owner**: Platform Engineering Team
**Approval Required**: Engineering Manager + DevOps Lead
**Estimated Duration**: 7 days (can be accelerated based on metrics)

---

## Pre-Deployment Checklist

### ✅ Infrastructure Readiness

#### Redis Cluster (Feature Flags Backend)
```bash
# Verify Redis is operational
python scripts/verify_redis_cluster.py --environment production
```
**Expected Result**: All Redis nodes healthy, feature flags system operational

#### Database Connectivity
```bash
# Test all database connections
python scripts/test_database_connections.py --environment production
```
**Expected Result**: PostgreSQL and ClickHouse connections successful

#### Monitoring Systems
```bash
# Verify monitoring stack
python scripts/verify_monitoring_stack.py --environment production
```
**Expected Result**: Prometheus, Grafana, alerting systems operational

### ✅ Code Quality Gates

#### Mission Critical Tests
```bash
# Run WebSocket agent event tests
python tests/mission_critical/test_websocket_agent_events_suite.py
```
**Expected Result**: All WebSocket events functioning correctly

#### Request Isolation Tests
```bash
# Run isolation validation tests
python tests/mission_critical/test_isolation_validation.py
```
**Expected Result**: 100% isolation score, zero cascade failures

#### Architecture Compliance
```bash
# Verify architecture compliance
python scripts/check_architecture_compliance.py
```
**Expected Result**: No compliance violations detected

### ✅ Security Validation

#### Secrets Verification
```bash
# Validate all production secrets
python scripts/validate_secrets.py --environment production --project netra-production
```
**Expected Result**: All required secrets present and valid

#### OAuth Configuration
```bash
# Verify OAuth setup
python scripts/validate_oauth_deployment.py --environment production
```
**Expected Result**: OAuth configuration valid for production URLs

### ✅ Team Readiness

#### On-Call Rotation
- [ ] Primary on-call engineer identified
- [ ] Secondary on-call engineer available
- [ ] DevOps team notified
- [ ] Engineering manager available

#### Communication Channels
- [ ] Slack #production-deployments channel active
- [ ] PagerDuty integration verified
- [ ] Email distribution list updated
- [ ] War room bridge ready (if needed)

---

## Deployment Commands Reference

### Stage 1: Deploy with Features OFF (0% Traffic)

**Duration**: 2 hours
**Objective**: Deploy code to production with feature flags disabled

#### Step 1.1: Deploy Backend Service
```bash
# Deploy backend with isolation features OFF
python scripts/deploy_to_gcp.py \
    --project netra-production \
    --service backend \
    --build-local \
    --run-checks

# Verify deployment
gcloud run services describe netra-backend-production \
    --region us-central1 --format="value(status.url)"
```

#### Step 1.2: Deploy Auth Service  
```bash
# Deploy auth service with isolation features OFF
python scripts/deploy_to_gcp.py \
    --project netra-production \
    --service auth \
    --build-local \
    --run-checks

# Verify deployment
gcloud run services describe netra-auth-service-production \
    --region us-central1 --format="value(status.url)"
```

#### Step 1.3: Initialize Feature Flags
```bash
# Initialize all feature flags in OFF state
python scripts/production_rollout_control.py init \
    --environment production

# Verify all flags are OFF
python scripts/production_rollout_control.py status \
    --environment production --detailed
```

#### Step 1.4: Smoke Tests
```bash
# Run production smoke tests
python tests/unified_test_runner.py \
    --category smoke \
    --env production \
    --no-coverage

# Expected result: All smoke tests pass, no feature flags active
```

#### Stage 1 Success Criteria
- ✅ All services deployed successfully
- ✅ Health checks returning 200 OK
- ✅ Feature flags confirm 0% rollout
- ✅ Legacy code paths functioning normally
- ✅ No performance regression detected

#### Stage 1 Rollback (if needed)
```bash
# Emergency rollback to previous revision
python scripts/automated_rollback.py emergency \
    --reason "Stage 1 deployment failure" \
    --triggered-by "deployment_team"
```

### Stage 2: Internal Users Only (Team Testing)

**Duration**: 24 hours  
**Objective**: Enable isolation features for Netra team members only

#### Step 2.1: Enable Internal-Only Mode
```bash
# Enable for internal users (@netrasystems.ai, @netrasystems.ai)
python scripts/production_rollout_control.py update-all-stages \
    --stage internal \
    --updated-by "deployment_team"

# Verify rollout stage
python scripts/production_rollout_control.py status --detailed
```

#### Step 2.2: Start Monitoring
```bash
# Start real-time monitoring for internal stage
python scripts/production_monitoring.py start \
    --stage internal \
    --alert-threshold isolation_score:100 \
    --alert-threshold error_rate:0.001
```

#### Step 2.3: Team Testing Protocol

**Testing Checklist for Internal Users**:
1. **Concurrent Testing**: 3+ team members use chat simultaneously
2. **Failure Injection**: Force failures in one user's session
3. **WebSocket Validation**: Verify real-time events work correctly
4. **Load Testing**: Multiple agents running concurrently
5. **Cross-Service Testing**: Auth + Backend integration

#### Step 2.4: Continuous Validation
```bash
# Manual validation every 4 hours
python scripts/validate_isolation_production.py \
    --environment production \
    --users internal

# Check isolation score
python scripts/production_monitoring.py metrics --detailed
```

#### Stage 2 Success Criteria (24 hours)
- ✅ Zero cascade failures detected
- ✅ All WebSocket events functioning
- ✅ Request isolation score = 100%
- ✅ No user impact reports
- ✅ Resource cleanup functioning properly

#### Stage 2 Rollback Triggers
- Isolation score drops below 100%
- Any cascade failure detected
- WebSocket events not firing
- Team reports functional issues
- Resource leak detection

### Stage 3: Canary Deployment (10% Traffic)

**Duration**: 48 hours
**Objective**: Validate isolation features with 10% of production traffic

#### Step 3.1: Update to Canary Stage
```bash
# Update to 10% rollout
python scripts/production_rollout_control.py update-all-stages \
    --stage canary \
    --updated-by "deployment_team"

# Verify rollout percentage
python scripts/production_rollout_control.py status --detailed
```

#### Step 3.2: Enhanced Monitoring
```bash
# Start canary monitoring with A/B comparison
python scripts/production_monitoring.py start \
    --stage canary \
    --comparison-mode \
    --alert-threshold isolation_score:99.5 \
    --alert-threshold error_rate:0.01 \
    --alert-threshold response_time_p95:+10%
```

#### Step 3.3: Configure Production Alerts
```bash
# Configure all alert channels
python scripts/configure_production_alerts.py \
    --stage canary \
    --slack-webhook $SLACK_PROD_WEBHOOK \
    --pagerduty-key $PAGERDUTY_INTEGRATION_KEY \
    --email-recipients "engineering@netrasystems.ai,devops@netrasystems.ai"
```

#### Stage 3 Monitoring Requirements (48 hours)

| Metric | Threshold | Action |
|--------|-----------|---------|
| Isolation Score | ≥ 99.5% | Continue |
| Error Rate Differential | ≤ 1% | Continue |
| Response Time P95 | ≤ +10% | Continue |
| User Complaints | 0 | Continue |
| Cascade Failures | 0 | Continue |

#### Stage 3 Success Criteria
- ✅ 10% traffic handled without issues
- ✅ A/B testing shows no negative impact
- ✅ All monitoring thresholds met
- ✅ Zero cascade failures detected
- ✅ User experience maintained

#### Stage 3 Rollback Triggers
- Error rate increases > 1%
- Response time degradation > 10%
- Any cascade failure detected
- User reports of system issues
- Isolation score drops below 99.5%

### Stage 4: Staged Deployment (50% Traffic)

**Duration**: 48 hours
**Objective**: Scale isolation features to 50% of production traffic

#### Step 4.1: Scale to 50% Traffic
```bash
# Scale to 50% traffic
python scripts/production_rollout_control.py update-all-stages \
    --stage staged \
    --updated-by "deployment_team"

# Monitor resource usage
python scripts/production_monitoring.py resource-usage \
    --stage staged
```

#### Step 4.2: Load Testing at Scale
```bash
# Automated load testing
python scripts/production_load_test.py \
    --concurrent-users 100 \
    --duration 3600 \
    --mixed-traffic \
    --monitor-isolation
```

#### Stage 4 Success Criteria (48 hours)
- ✅ 50% traffic handling without issues
- ✅ Resource usage within normal parameters
- ✅ Business metrics unchanged or improved
- ✅ Zero system stability incidents
- ✅ User satisfaction maintained

### Stage 5: Full Deployment (100% Traffic)

**Duration**: Ongoing
**Objective**: Complete rollout to all production traffic

#### Step 5.1: Enable for All Users
```bash
# Enable for all users
python scripts/production_rollout_control.py update-all-stages \
    --stage full \
    --updated-by "deployment_team"

# Final verification
python scripts/production_rollout_control.py verify-full-deployment
```

#### Step 5.2: Post-Deployment Validation
```bash
# Comprehensive health check
python scripts/production_health_check.py \
    --full-deployment \
    --isolation-features \
    --duration 3600

# Legacy code removal verification
python scripts/verify_legacy_removal.py --production
```

#### Step 5.3: Performance Benchmarking
```bash
# Performance comparison report
python scripts/generate_performance_report.py \
    --before-after-comparison \
    --environment production \
    --email-report
```

---

## Monitoring and Alerting

### Real-Time Dashboards

#### Primary Dashboard URLs
- **Isolation Score Dashboard**: `https://grafana.netrasystems.ai/d/isolation-score`
- **Request Independence Monitor**: `https://grafana.netrasystems.ai/d/request-isolation`
- **WebSocket Health**: `https://grafana.netrasystems.ai/d/websocket-events`
- **Business Metrics**: `https://grafana.netrasystems.ai/d/business-kpis`

#### Key Metrics to Monitor

| Metric | Normal Range | Warning Threshold | Critical Threshold |
|--------|--------------|-------------------|-------------------|
| Isolation Score | 100% | < 99.5% | < 95% |
| Error Rate | 0-0.1% | > 0.5% | > 1% |
| Response Time P95 | Baseline | +10% | +20% |
| Cascade Failures | 0 | 1 | 3+ |
| WebSocket Events | 100% delivery | < 99% | < 95% |

### Alert Levels

#### P0 - Production Down (PagerDuty + Immediate Response)
- System isolation score drops below 95%
- Cascade failures detected (any)
- Error rate increases above 5%
- All WebSocket events stopped

#### P1 - Performance Degradation (PagerDuty + 15min Response)
- Isolation score below 99%
- Error rate above 1%
- Response time increase > 20%
- Resource utilization > 90%

#### P2 - Warning Indicators (Slack + Email)
- Isolation score below 99.5%
- Error rate above 0.5%
- Response time increase > 10%
- Circuit breakers triggered

### Monitoring Commands

#### Check Current Status
```bash
# Get overall system status
python scripts/production_monitoring.py metrics --detailed

# Check specific isolation score
python scripts/production_rollout_control.py status --environment production
```

#### Generate Reports
```bash
# Daily monitoring report
python scripts/production_monitoring.py daily-report \
    --email-recipients "team@netrasystems.ai"

# Isolation score trend analysis
python scripts/analyze_isolation_trends.py \
    --environment production \
    --duration 24h
```

---

## Rollback Procedures

### Emergency Rollback (< 5 minutes)

**Use Case**: Critical system failures, cascade failures detected

#### Instant Feature Flag Disable
```bash
# EMERGENCY: Disable all isolation features immediately
python scripts/automated_rollback.py emergency \
    --reason "CASCADE_FAILURES_DETECTED" \
    --triggered-by "incident_response"
```

#### Service Rollback (if needed)
```bash
# Rollback to previous Cloud Run revision
python scripts/automated_rollback.py emergency \
    --reason "CRITICAL_SYSTEM_FAILURE" \
    --triggered-by "incident_response"

# Verify rollback completed
python scripts/automated_rollback.py verify-rollback
```

### Gradual Rollback (10-30 minutes)

**Use Case**: Performance issues, non-critical problems

#### Stage-by-Stage Rollback
```bash
# Reduce traffic gradually
python scripts/production_rollout_control.py update-all-stages \
    --stage staged \
    --reason "Performance issues detected" \
    --updated-by "incident_response"

# Continue reducing if needed
python scripts/production_rollout_control.py update-all-stages \
    --stage canary \
    --reason "Continued issues"

# Full disable if required
python scripts/production_rollout_control.py update-all-stages \
    --stage off \
    --reason "Complete rollback required"
```

### Rollback Verification

#### Verify Rollback Completed
```bash
# Comprehensive rollback verification
python scripts/automated_rollback.py verify-rollback

# Check system health post-rollback
python scripts/production_health_check.py \
    --post-rollback \
    --verify-legacy-paths
```

#### Expected Rollback Results
- ✅ All feature flags disabled (0% rollout)
- ✅ All services healthy and responding
- ✅ Legacy code paths functioning normally
- ✅ No performance degradation
- ✅ User experience restored

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Feature Flags Not Disabling
**Symptoms**: Flags show as disabled but features still active
**Solution**:
```bash
# Check Redis connectivity
python scripts/verify_redis_cluster.py --environment production

# Force flag refresh
python scripts/production_rollout_control.py emergency-disable \
    --reason "Flag disable verification" \
    --updated-by "troubleshooting"

# Verify application cache clear
python scripts/clear_application_caches.py --environment production
```

#### Issue: WebSocket Events Not Firing
**Symptoms**: Chat interface not updating, missing real-time events
**Solution**:
```bash
# Check WebSocket health
python scripts/test_websocket_connectivity.py --environment production

# Verify event handler registration
python scripts/debug_websocket_handlers.py --environment production

# Restart WebSocket service if needed
python scripts/restart_websocket_service.py --environment production
```

#### Issue: Cascade Failures Detected
**Symptoms**: Isolation score dropping, multiple user requests failing
**Solution**:
```bash
# IMMEDIATE: Emergency rollback
python scripts/automated_rollback.py emergency \
    --reason "CASCADE_FAILURES_DETECTED" \
    --triggered-by "troubleshooting"

# Analyze contamination events
python scripts/analyze_contamination_events.py \
    --environment production \
    --last-hour

# Generate contamination report
python scripts/generate_contamination_report.py \
    --environment production \
    --detailed
```

#### Issue: Performance Degradation
**Symptoms**: Response times increased, user complaints
**Solution**:
```bash
# Check resource utilization
python scripts/check_resource_usage.py --environment production

# Analyze performance bottlenecks
python scripts/analyze_performance_bottlenecks.py \
    --environment production

# Consider gradual rollback
python scripts/production_rollout_control.py update-all-stages \
    --stage canary \
    --reason "Performance investigation"
```

#### Issue: Database Connection Issues
**Symptoms**: Database errors, session isolation failures
**Solution**:
```bash
# Test database connectivity
python scripts/test_database_connections.py --environment production

# Check connection pool status
python scripts/check_db_connection_pools.py --environment production

# Verify session isolation
python scripts/test_db_session_isolation.py --environment production
```

### Debug Commands

#### System Health Check
```bash
# Comprehensive system check
python scripts/production_health_check.py \
    --comprehensive \
    --isolation-features \
    --generate-report
```

#### Isolation Analysis
```bash
# Analyze request isolation effectiveness
python scripts/analyze_request_isolation.py \
    --environment production \
    --duration 1h \
    --detailed-report
```

#### Performance Analysis
```bash
# Performance impact analysis
python scripts/analyze_performance_impact.py \
    --environment production \
    --compare-baseline \
    --generate-report
```

---

## Post-Deployment Tasks

### Week 1: Monitoring and Validation

#### Daily Tasks
```bash
# Daily isolation score report
python scripts/production_monitoring.py daily-report \
    --email-recipients "engineering@netrasystems.ai"

# Performance baseline update
python scripts/update_performance_baseline.py \
    --environment production

# User feedback collection
python scripts/collect_user_feedback.py \
    --environment production \
    --isolation-features
```

#### Weekly Tasks
```bash
# Weekly performance analysis
python scripts/production_weekly_analysis.py \
    --isolation-metrics \
    --trend-analysis \
    --email-report

# System stability report
python scripts/generate_stability_report.py \
    --environment production \
    --week-over-week
```

### Week 2-4: Optimization

#### Performance Tuning
```bash
# Optimize based on metrics
python scripts/optimize_isolation_performance.py \
    --environment production \
    --based-on-metrics

# Resource usage optimization
python scripts/optimize_resource_usage.py \
    --environment production \
    --isolation-features
```

#### Monitoring Threshold Adjustment
```bash
# Adjust monitoring thresholds based on actual performance
python scripts/adjust_monitoring_thresholds.py \
    --environment production \
    --based-on-history \
    --last-30-days
```

### Month 2: Legacy Cleanup

#### Code Cleanup
```bash
# Remove all singleton patterns
python scripts/remove_legacy_singletons.py \
    --environment production \
    --verify-removal

# Clean up legacy code paths
python scripts/clean_legacy_code.py \
    --environment production \
    --isolation-migration

# Update architecture documentation
python scripts/update_architecture_docs.py \
    --isolation-features \
    --production-deployment
```

#### Team Training
```bash
# Generate training materials
python scripts/generate_training_materials.py \
    --isolation-patterns \
    --production-lessons

# Schedule team training sessions
# (Manual task - schedule with team leads)
```

---

## Emergency Contacts

### Primary On-Call
- **Primary**: Platform Engineering Lead
- **Secondary**: DevOps Engineer
- **Escalation**: Engineering Manager

### Contact Methods
- **Slack**: #production-emergency
- **PagerDuty**: Integration key configured
- **Phone**: Emergency contact list in company directory

### Escalation Matrix

#### Level 1: On-Call Engineer (0-15 minutes)
- Isolation score drops below 99%
- Performance degradation detected
- Non-critical feature issues

#### Level 2: Engineering Lead (15-30 minutes)
- Isolation score drops below 95%
- Cascade failures detected
- Multiple user reports

#### Level 3: Engineering Manager (30-60 minutes)
- System-wide failures
- Customer-facing issues
- Media attention required

### Emergency Procedures

#### War Room Setup
1. Create Slack channel: #incident-YYYYMMDD-HHMM
2. Bridge line: Use company emergency bridge
3. Incident commander: On-call engineer or escalated lead
4. Communication lead: Designated team member for updates

#### Communication Templates

**Initial Alert**:
```
🚨 PRODUCTION INCIDENT: Request Isolation Rollout
Severity: [P0/P1/P2]
Impact: [Description of user impact]
ETA for resolution: [Estimated time]
Incident Commander: [Name]
Updates every: [Frequency]
```

**Resolution Update**:
```
✅ RESOLVED: Request Isolation Incident
Duration: [Total time]
Root Cause: [Brief description]
Actions Taken: [Summary of resolution steps]
Follow-up: [Post-incident review scheduled]
```

---

## Appendix

### Quick Reference Commands

#### Status Checks
```bash
# Overall system status
python scripts/production_rollout_control.py status --environment production

# Current isolation score
python scripts/production_monitoring.py metrics

# Feature flag status
python scripts/production_rollout_control.py status --detailed
```

#### Emergency Actions
```bash
# Emergency disable all features
python scripts/automated_rollback.py emergency \
    --reason "EMERGENCY" --triggered-by "incident_response"

# Emergency rollback all services
python scripts/automated_rollback.py emergency \
    --reason "CRITICAL_FAILURE" --triggered-by "incident_response"

# Verify rollback completed
python scripts/automated_rollback.py verify-rollback
```

#### Health Checks
```bash
# System health
python scripts/production_health_check.py --isolation-features

# Service health
python scripts/check_service_health.py --all-services --environment production

# Database health
python scripts/test_database_connections.py --environment production
```

### File Locations

#### Scripts Directory
- **Rollout Control**: `/scripts/production_rollout_control.py`
- **Monitoring**: `/scripts/production_monitoring.py`
- **Automated Rollback**: `/scripts/automated_rollback.py`
- **Health Checks**: `/scripts/production_health_check.py`

#### Configuration Files
- **Feature Flags**: Redis-backed, no local files
- **Monitoring Config**: `/deployment/monitoring_config.yaml`
- **Alert Rules**: `/deployment/alert_rules.yaml`

#### Log Locations
- **Application Logs**: Cloud Logging (GCP)
- **Monitoring Logs**: `/var/log/production_monitoring/`
- **Rollout Audit**: Redis keys `rollback_audit:production:*`

---

## Document Information

**Document Version**: 1.0
**Last Updated**: 2025-01-14
**Next Review**: 2025-02-14
**Owner**: Platform Engineering Team
**Approvers**: Engineering Manager, DevOps Lead

This runbook is a living document and should be updated based on operational experience and lessons learned from actual deployments.