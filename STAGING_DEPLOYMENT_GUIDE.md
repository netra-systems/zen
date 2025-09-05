# Staging Deployment Guide

## Overview
This guide provides comprehensive instructions for deploying the Netra Apex platform to staging environment with complete request isolation validation.

## Prerequisites

### 1. Authentication Setup
```bash
# Authenticate with Google Cloud
gcloud auth login

# Set the staging project
gcloud config set project netra-staging

# Verify authentication
gcloud auth list
```

### 2. Required Environment Variables
```bash
# LLM API Keys
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GEMINI_API_KEY="your-gemini-api-key"

# OAuth Credentials for Staging
export GOOGLE_STAGING_CLIENT_ID="your-staging-oauth-client-id"
export GOOGLE_STAGING_CLIENT_SECRET="your-staging-oauth-client-secret"
```

### 3. Local Dependencies
```bash
# Install required Python packages
pip install pyyaml requests aiohttp psutil asyncpg

# Ensure Docker is running
docker --version
docker-compose --version
```

## Deployment Steps

### Phase 1: Pre-Deployment Validation

#### 1.1 Architecture Compliance Check
```bash
# Validate architecture compliance
python scripts/check_architecture_compliance.py

# Expected: All checks pass
```

#### 1.2 Local Isolation Testing
```bash
# Run request isolation tests locally (optional - requires full backend setup)
python -m pytest tests/mission_critical/test_complete_request_isolation.py -v

# Expected: 100% pass rate
```

#### 1.3 Configuration Validation
```bash
# Validate staging configuration
python scripts/validate_staging_urls.py --environment staging --check

# Expected: No localhost URLs in staging config
```

### Phase 2: GCP Deployment

#### 2.1 Deploy to GCP Staging
```bash
# Deploy with local build (recommended - 5x faster)
python scripts/deploy_to_gcp.py \
    --project netra-staging \
    --build-local \
    --run-checks

# Alternative: Cloud Build (slower but no local resources needed)
python scripts/deploy_to_gcp.py \
    --project netra-staging \
    --run-checks
```

#### 2.2 Verify Deployment
```bash
# Check all services are deployed and healthy
gcloud run services list --platform managed --region us-central1

# Expected output:
# SERVICE                    REGION        URL                                          LAST DEPLOYED BY  LAST DEPLOYED AT
# netra-backend-staging     us-central1   https://netra-backend-staging-xxx.run.app   you@company.com   2024-XX-XX
# netra-auth-service        us-central1   https://netra-auth-service-xxx.run.app      you@company.com   2024-XX-XX  
# netra-frontend-staging    us-central1   https://netra-frontend-staging-xxx.run.app  you@company.com   2024-XX-XX
```

### Phase 3: Staging Validation

#### 3.1 Health Check Validation
```bash
# Run comprehensive health checks
python scripts/validate_staging_health.py --comprehensive

# Expected: All services healthy, 100% success rate
```

#### 3.2 Request Isolation Testing
```bash
# Test request isolation with 100+ concurrent users
# This simulates the critical isolation requirements
python scripts/load_testing/run_load_test.py

# Expected metrics:
# - Success rate: >95%
# - Average response time: <2 seconds
# - No cross-contamination between users
# - Memory usage stable
```

#### 3.3 Authentication Flow Testing  
```bash
# Test OAuth authentication flows
curl -I "https://netra-auth-service-xxx.run.app/auth/google"

# Expected: 302 redirect to Google OAuth
```

### Phase 4: Extended Validation (24-Hour Monitoring)

#### 4.1 Monitor Key Metrics
Monitor the following metrics for 24 hours:

**Service Health Metrics:**
- Response time P95 < 2 seconds
- Error rate < 1%
- Availability > 99.9%

**Request Isolation Metrics:**
- Memory usage per request contained
- No shared state between requests
- Agent cleanup functioning
- Database connection pool stable

**System Resource Metrics:**
- CPU usage < 70%
- Memory usage < 80%
- Database connections < 80% of pool
- No memory leaks detected

#### 4.2 Automated Monitoring Setup
```bash
# Set up monitoring dashboards (if available)
gcloud monitoring dashboards create --config-from-file=monitoring/staging-dashboard.json

# Set up alerting policies
gcloud alpha monitoring policies create --policy-from-file=monitoring/staging-alerts.yaml
```

#### 4.3 Stress Testing Schedule
```bash
# Schedule periodic load tests every 6 hours
# Test 1: 09:00 UTC - 50 concurrent users for 1 hour
# Test 2: 15:00 UTC - 100 concurrent users for 1 hour  
# Test 3: 21:00 UTC - 150 concurrent users for 1 hour
# Test 4: 03:00 UTC - Random failure injection test
```

## Deployment Validation Checklist

### Critical Success Criteria ✅

- [ ] **All services deployed successfully** (backend, auth, frontend)
- [ ] **Health endpoints responding** (200 OK within 2 seconds)
- [ ] **Request isolation validated** (100+ concurrent users, >95% success rate)
- [ ] **Authentication flows working** (OAuth login/logout functional)
- [ ] **Database connectivity confirmed** (PostgreSQL, Redis, ClickHouse)
- [ ] **WebSocket connections stable** (real-time features working)
- [ ] **No memory leaks detected** (24-hour memory usage stable)
- [ ] **Error rates within limits** (<1% error rate sustained)
- [ ] **Performance within SLA** (P95 response time <2 seconds)

### Security Validation ✅

- [ ] **HTTPS enforced** (all HTTP requests redirect to HTTPS)
- [ ] **Authentication required** (no unauthenticated access to protected routes)
- [ ] **CORS configured correctly** (frontend can access backend/auth)
- [ ] **Secrets properly managed** (no secrets in logs or responses)
- [ ] **Rate limiting functional** (prevents abuse)
- [ ] **Input validation working** (malformed requests rejected)

### Business Logic Validation ✅

- [ ] **Agent execution isolated** (user A's failure doesn't affect user B)
- [ ] **Chat functionality working** (WebSocket events firing correctly)
- [ ] **Session management stable** (login/logout/refresh working)
- [ ] **Database transactions atomic** (no partial state corruption)
- [ ] **File upload/download working** (if applicable)
- [ ] **API documentation accessible** (if applicable)

## Rollback Procedures

### When to Rollback
- Critical services unhealthy for >5 minutes
- Error rate >5% sustained for >10 minutes  
- Request isolation failures detected
- Memory leaks causing resource exhaustion
- Authentication completely broken

### Rollback Commands
```bash
# Immediate rollback to previous working version
python scripts/deploy_to_gcp.py --project netra-staging --rollback

# Or manual service-by-service rollback
gcloud run services update netra-backend-staging --image gcr.io/netra-staging/netra-backend-staging:previous
gcloud run services update netra-auth-service --image gcr.io/netra-staging/netra-auth-service:previous
gcloud run services update netra-frontend-staging --image gcr.io/netra-staging/netra-frontend-staging:previous
```

### Post-Rollback Validation
```bash
# Verify rollback successful
python scripts/validate_staging_health.py --quick-check

# Check specific isolation functionality
python scripts/test_request_isolation.py --quick
```

## Monitoring and Alerting

### Key Dashboards
- **Service Health**: Response times, error rates, availability
- **Request Isolation**: Memory usage per request, connection counts
- **System Resources**: CPU, memory, disk usage
- **User Experience**: Frontend load times, WebSocket connection success

### Alert Thresholds
```yaml
alerts:
  - name: "High Error Rate"
    condition: "error_rate > 2%"
    duration: "5 minutes"
    severity: "CRITICAL"
  
  - name: "Slow Response Time"
    condition: "response_time_p95 > 3 seconds"
    duration: "10 minutes"
    severity: "WARNING"
  
  - name: "Memory Leak Detected"
    condition: "memory_usage_trend > 5% per hour"
    duration: "30 minutes"
    severity: "CRITICAL"
  
  - name: "Request Isolation Failure"
    condition: "isolation_test_success_rate < 90%"
    duration: "1 minute"
    severity: "CRITICAL"
```

## Known Issues and Mitigations

### Issue 1: Cold Start Delays
**Problem**: First request to each service takes 10-30 seconds
**Mitigation**: Configure minimum instances = 1 for critical services
**Detection**: Monitor P95 response time spikes

### Issue 2: Database Connection Pool Exhaustion  
**Problem**: High concurrent load exhausts connection pools
**Mitigation**: Proper connection pool sizing and timeout configuration
**Detection**: Database connection errors in logs

### Issue 3: WebSocket Connection Drops
**Problem**: Load balancer timeouts cause WebSocket disconnections
**Mitigation**: Heartbeat implementation and reconnection logic
**Detection**: WebSocket error rate monitoring

### Issue 4: Memory Leaks in Agent Execution
**Problem**: Agent instances not properly cleaned up after execution
**Mitigation**: Explicit cleanup in agent lifecycle management
**Detection**: Memory usage trending upward over time

## Success Metrics

### Deployment Success
- **Deployment Duration**: <30 minutes total
- **Zero Downtime**: No service interruption during deployment
- **Rollback Time**: <5 minutes if needed

### Operational Success (24 Hours)
- **Availability**: >99.9%
- **Response Time**: P95 <2 seconds
- **Error Rate**: <1%
- **Memory Stability**: <5% variance from baseline

### Request Isolation Success
- **Concurrent User Support**: 150+ users simultaneously
- **Failure Isolation**: 100% (no cross-user failures)
- **Resource Cleanup**: 100% (no leaked resources)
- **State Isolation**: 100% (no shared state)

## Next Steps After Successful Staging

1. **Document Lessons Learned**: Update this guide with any issues encountered
2. **Update Production Deployment**: Apply staging learnings to production config
3. **Schedule Production Deployment**: Plan production deployment with 48-hour notice
4. **Prepare Production Rollback**: Ensure production rollback procedures tested
5. **Team Training**: Brief team on new deployment and rollback procedures

---

**Note**: This deployment is for staging validation only. Do not use staging credentials or URLs in production. All secrets and configurations should be environment-specific.