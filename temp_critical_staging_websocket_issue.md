# 🚨 CRITICAL: Staging WebSocket Infrastructure Complete Breakdown - Mission Critical Test Failures

## 🔥 Business Impact
**CRITICAL PRODUCTION BLOCKER**: Core chat functionality ($500K+ ARR) completely non-operational in staging environment. Mission-critical tests consistently failing, indicating staging WebSocket infrastructure breakdown that will affect production deployment reliability.

## 📊 Problem Summary
**Test File**: `tests/mission_critical/test_staging_websocket_agent_events.py`
**WebSocket URL**: `wss://api.staging.netrasystems.ai/ws`
**Primary Symptoms**:
- Tests timing out after 2+ minutes during collection/execution
- "Infrastructure Status: UNAVAILABLE" messages
- Complete breakdown of agent event pipeline in staging
- Comment in test file: "ANY FAILURE HERE INDICATES STAGING WEBSOCKET ISSUES THAT WILL AFFECT PRODUCTION"

## 🔍 Evidence Found

### 1. Domain Configuration Mismatch (CRITICAL)
**Current staging configuration uses incorrect domains**:
- **CURRENT**: `api.staging.netrasystems.ai` (test configuration)
- **REQUIRED**: `api-staging.netrasystems.ai` (with hyphen per CLAUDE.md)

**Files affected**:
- `tests/e2e/staging_config.py` - Lines 27-35 show wrong URLs
- `test_framework/staging_websocket_test_helper.py` - Using wrong config

### 2. Infrastructure Issues Documentation
**Recent audit findings show multiple infrastructure problems**:
- VPC networking configuration issues preventing Cloud SQL access
- Backend health endpoint timeouts documented in audit files
- WebSocket race conditions and bridge issues in recent documentation
- SSL certificate failures for incorrect domain patterns

### 3. Mission Critical Test Breakdown
**Test suite designed to validate $500K+ ARR functionality is failing**:
```python
# From test_staging_websocket_agent_events.py line 15:
# ANY FAILURE HERE INDICATES STAGING WEBSOCKET ISSUES THAT WILL AFFECT PRODUCTION.
```

**Required WebSocket events not being delivered**:
- `agent_started` - User sees agent began processing
- `agent_thinking` - Real-time reasoning visibility
- `tool_executing` - Tool usage transparency
- `tool_completed` - Tool results display
- `agent_completed` - User knows response is ready

## 🛠 Root Cause Analysis

### Primary Issues:
1. **Domain Configuration Error**: Tests connecting to `api.staging.netrasystems.ai` instead of correct `api-staging.netrasystems.ai`
2. **SSL Certificate Mismatch**: Incorrect domain pattern causing SSL validation failures
3. **VPC Networking**: Infrastructure configuration preventing proper service communication
4. **Load Balancer Configuration**: Health checks not configured for extended Cloud Run startup times

### Infrastructure Dependencies:
- VPC Connector: `staging-connector` with all-traffic egress
- Database Timeout: 600s (addresses previous Issues #1263, #1278)
- SSL Certificates: Must be valid for `*.netrasystems.ai` domains
- Load Balancer: Health checks configured for extended startup times

## 📋 Immediate Action Items

### 🔥 P0 - Critical (Must Fix Immediately)
- [ ] **Fix Domain Configuration**: Update all staging config files to use correct `api-staging.netrasystems.ai` domain
- [ ] **SSL Certificate Validation**: Ensure certificates are valid for hyphenated domain pattern
- [ ] **VPC Networking Audit**: Verify staging-connector configuration for WebSocket traffic
- [ ] **Load Balancer Health Checks**: Configure proper timeouts for Cloud Run cold starts

### 🚨 P1 - High Priority
- [ ] **Mission Critical Test Validation**: Run `python tests/mission_critical/test_staging_websocket_agent_events.py` until passing
- [ ] **WebSocket Event Pipeline**: Verify all 5 required events are being delivered
- [ ] **Staging Infrastructure Health**: Validate complete staging deployment pipeline
- [ ] **Golden Path Restoration**: Ensure complete user login → AI response flow works

### 📊 P2 - Monitoring & Prevention
- [ ] **Automated Health Checks**: Implement continuous staging WebSocket monitoring
- [ ] **Golden Path Alerts**: Alert on any staging chat functionality degradation
- [ ] **Infrastructure Validation**: Add pre-deployment staging validation gates

## 📁 Key Files to Review/Fix

### Configuration Files:
- `tests/e2e/staging_config.py` - **WRONG DOMAINS**
- `test_framework/staging_websocket_test_helper.py`
- `.env.staging.tests` - Domain configuration
- `dockerfiles/frontend.staging.alpine.Dockerfile` - Environment variables

### Infrastructure Files:
- `terraform-gcp-staging/vpc-connector.tf`
- `.github/workflows/deploy-staging.yml` - VPC connector configuration
- Domain SSL certificate configuration

### Test Files:
- `tests/mission_critical/test_staging_websocket_agent_events.py` - **CRITICAL TEST**
- `test_framework/staging_websocket_test_helper.py`

## 🔧 Fix Implementation Strategy

### Step 1: Domain Configuration Fix
```bash
# Update staging configuration files to use correct domains:
# FROM: api.staging.netrasystems.ai
# TO:   api-staging.netrasystems.ai

# Files to update:
# - tests/e2e/staging_config.py
# - .env.staging.tests
# - dockerfiles/frontend.staging.alpine.Dockerfile
```

### Step 2: Infrastructure Validation
```bash
# Verify VPC connector and SSL certificates:
gcloud compute networks vpc-access connectors describe staging-connector --region=us-central1
gcloud run services describe netra-backend-staging --region=us-central1
```

### Step 3: Mission Critical Test Validation
```bash
# Must pass before any production deployment:
python tests/mission_critical/test_staging_websocket_agent_events.py -v
```

## 🎯 Success Criteria

### Immediate Success (within 24 hours):
- [ ] Mission critical staging WebSocket tests passing consistently
- [ ] All 5 required WebSocket events delivered in staging
- [ ] Staging health endpoints returning 200 OK
- [ ] Golden Path user flow operational in staging

### Long-term Success (within 1 week):
- [ ] Zero staging WebSocket infrastructure failures
- [ ] Automated monitoring preventing future breakdowns
- [ ] Production deployment confidence restored
- [ ] $500K+ ARR chat functionality reliability assured

## 🚨 Critical Dependencies

**CANNOT DEPLOY TO PRODUCTION** until:
1. Staging WebSocket infrastructure fully operational
2. Mission critical tests passing consistently
3. All 5 WebSocket events validated in staging
4. Golden Path user flow working end-to-end

**Business Risk**: Without staging validation, production deployments risk breaking $500K+ ARR chat functionality for all users.

---

**Labels**: `critical`, `staging`, `websocket`, `infrastructure`, `golden-path`, `mission-critical`, `p0`
**Assignee**: Infrastructure Team
**Milestone**: Staging Infrastructure Recovery
**Priority**: 🔥 P0 - Production Blocker

**Created by**: Automated Infrastructure Monitoring
**Documentation**: See CLAUDE.md sections on staging domain configuration and WebSocket infrastructure requirements