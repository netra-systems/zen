# Staging Rollback Procedures

## Overview
This document outlines comprehensive rollback procedures for the Netra Apex staging environment. These procedures ensure system stability and provide rapid recovery in case of deployment issues.

## Critical Rollback Scenarios

### 1. Request Isolation Failure
**Trigger**: Cross-contamination between user requests detected
**Impact**: CRITICAL - Multiple users affected by single user's failures

```bash
# Immediate rollback
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.staging.yml up -d backend auth
```

**Validation**:
```bash
python scripts/validate_isolation.py --environment staging --quick-check
```

### 2. Database Connection Pool Exhaustion
**Trigger**: Connection pool exhaustion causing cascading failures
**Impact**: HIGH - Service unavailability

```bash
# Restart backend with reduced connection limits
docker-compose -f docker-compose.staging.yml restart backend
# Monitor connection pool usage
docker logs staging_backend_1 | grep "pool_size"
```

### 3. Memory Leak Detection
**Trigger**: Memory usage exceeding 80% threshold consistently
**Impact**: HIGH - System instability

```bash
# Immediate container restart
docker-compose -f docker-compose.staging.yml restart backend auth
# Check memory usage
docker stats staging_backend_1 staging_auth_1
```

### 4. WebSocket Connection Failures
**Trigger**: WebSocket connections failing or hanging
**Impact**: MEDIUM - Chat functionality unavailable

```bash
# Restart backend service
docker-compose -f docker-compose.staging.yml restart backend
# Clear Redis WebSocket sessions
docker exec staging_redis_1 redis-cli flushdb
```

## Rollback Decision Matrix

| Issue Type | Severity | Auto-Rollback | Manual Review Required |
|------------|----------|---------------|------------------------|
| Request Isolation Failure | CRITICAL | Yes | Yes |
| Database Connection Issues | HIGH | Yes | No |
| Memory Leaks | HIGH | Yes | Yes |
| WebSocket Failures | MEDIUM | No | Yes |
| Performance Degradation | MEDIUM | No | Yes |
| Configuration Errors | LOW | No | Yes |

## Automated Rollback Scripts

### Quick Rollback Script
```bash
#!/bin/bash
# scripts/quick_rollback_staging.sh

echo "🚨 EMERGENCY ROLLBACK INITIATED"
echo "Timestamp: $(date)"

# Stop all services
docker-compose -f docker-compose.staging.yml down

# Clean up volumes if needed
read -p "Clean volumes? (y/N): " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker volume prune -f
fi

# Restart with last known good configuration
docker-compose -f docker-compose.staging.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
timeout 300 bash -c '
    while [[ "$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep -c healthy)" -lt 3 ]]; do
        echo "Waiting for health checks..."
        sleep 10
    done
'

echo "✅ Rollback completed"
echo "🔍 Run validation: python scripts/validate_staging_health.py"
```

### Gradual Rollback Script
```bash
#!/bin/bash
# scripts/gradual_rollback_staging.sh

echo "🔄 GRADUAL ROLLBACK INITIATED"

# Rollback services one by one
services=("frontend" "backend" "auth")

for service in "${services[@]}"; do
    echo "Rolling back $service..."
    docker-compose -f docker-compose.staging.yml restart $service
    
    # Wait for health check
    echo "Waiting for $service health check..."
    timeout 60 bash -c "
        while ! docker ps --format 'table {{.Names}}\t{{.Status}}' | grep $service | grep -q healthy; do
            sleep 5
        done
    "
    
    if [ $? -eq 0 ]; then
        echo "✅ $service rollback successful"
    else
        echo "❌ $service rollback failed"
        exit 1
    fi
    
    # Brief pause between services
    sleep 10
done

echo "✅ Gradual rollback completed"
```

## Rollback Validation Procedures

### 1. System Health Check
```bash
# scripts/validate_staging_health.py
python scripts/validate_staging_health.py --comprehensive
```

**Expected Outputs**:
- All services responding to health checks
- Database connections stable
- Redis connectivity confirmed
- WebSocket endpoints functional

### 2. Request Isolation Validation
```bash
# Run isolation test suite
python -m pytest tests/mission_critical/test_complete_request_isolation.py -v
```

**Expected Results**:
- 100% test pass rate
- No cross-contamination detected
- Memory usage stable
- Connection cleanup verified

### 3. Load Testing Validation
```bash
# Run reduced load test
docker-compose -f docker-compose.staging.yml up -d load-tester
docker logs -f staging_load-tester_1
```

**Expected Metrics**:
- >95% success rate
- Average response time <2 seconds
- No error rate spikes
- Memory usage stable

## Monitoring and Alerting During Rollback

### Critical Metrics to Monitor
1. **Response Time**: Should return to <2 seconds within 5 minutes
2. **Error Rate**: Should drop to <1% within 10 minutes  
3. **Memory Usage**: Should stabilize below 70% within 15 minutes
4. **Connection Count**: Should return to normal levels within 5 minutes

### Alerting Thresholds Post-Rollback
```yaml
# Alert if these thresholds aren't met within specified timeframes
post_rollback_alerts:
  - metric: response_time_p95
    threshold: 3.0
    timeframe: 300s
  
  - metric: error_rate
    threshold: 0.02
    timeframe: 600s
  
  - metric: memory_usage_percent
    threshold: 75
    timeframe: 900s
  
  - metric: active_connections
    threshold: 200
    timeframe: 300s
```

## Data Integrity Verification

### Database State Verification
```sql
-- Check for orphaned records after rollback
SELECT 
    COUNT(*) as active_sessions,
    COUNT(DISTINCT user_id) as unique_users
FROM user_sessions 
WHERE created_at > NOW() - INTERVAL '1 hour';

-- Verify no corrupted agent states
SELECT agent_type, state, COUNT(*) 
FROM agent_executions 
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY agent_type, state;
```

### Redis State Verification
```bash
# Check Redis key patterns
docker exec staging_redis_1 redis-cli --scan --pattern "*:user:*" | wc -l
docker exec staging_redis_1 redis-cli --scan --pattern "*:session:*" | wc -l
```

## Communication Procedures

### Internal Team Notification
```bash
# Send rollback notification
curl -X POST $SLACK_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🚨 STAGING ROLLBACK COMPLETED",
    "attachments": [{
      "color": "warning",
      "fields": [
        {"title": "Environment", "value": "staging", "short": true},
        {"title": "Rollback Type", "value": "'$ROLLBACK_TYPE'", "short": true},
        {"title": "Timestamp", "value": "'$(date)'", "short": false}
      ]
    }]
  }'
```

### Stakeholder Notification Template
```
Subject: [STAGING] Emergency Rollback Completed - Action Required

Team,

A rollback has been performed on the staging environment due to [ISSUE_DESCRIPTION].

Rollback Details:
- Timestamp: [TIMESTAMP]
- Reason: [ROLLBACK_REASON]
- Services Affected: [SERVICES_LIST]
- Data Impact: [NONE/MINIMAL/MODERATE]

Current Status:
✅ System Health: Restored
✅ Request Isolation: Validated
✅ Performance: Within Normal Range
⏳ Full Validation: In Progress

Next Steps:
1. Complete validation testing (ETA: 30 minutes)
2. Root cause analysis (ETA: 2 hours)
3. Fix deployment plan (ETA: 4 hours)

Production Impact: None (staging only)

Contact: [ONCALL_ENGINEER] for questions
```

## Post-Rollback Analysis

### Required Documentation
1. **Incident Timeline**: Exact timestamps of detection, rollback initiation, and completion
2. **Root Cause Analysis**: Technical analysis of what caused the rollback
3. **Impact Assessment**: Systems and features affected
4. **Prevention Plan**: Changes to prevent similar issues

### Incident Report Template
```markdown
# Staging Rollback Incident Report

## Summary
- **Date**: [DATE]
- **Duration**: [START_TIME] - [END_TIME]
- **Severity**: [CRITICAL/HIGH/MEDIUM/LOW]
- **Root Cause**: [DESCRIPTION]

## Timeline
- [HH:MM] Issue first detected
- [HH:MM] Rollback decision made
- [HH:MM] Rollback initiated
- [HH:MM] Services restored
- [HH:MM] Validation completed

## Impact
- **Services Affected**: [LIST]
- **Data Loss**: [NONE/MINIMAL/DESCRIPTION]
- **User Impact**: [NONE - STAGING ONLY]

## Root Cause Analysis
[DETAILED TECHNICAL ANALYSIS]

## Resolution
[STEPS TAKEN TO RESOLVE]

## Prevention Measures
[CHANGES TO PREVENT RECURRENCE]

## Lessons Learned
[KEY TAKEAWAYS]
```

## Testing Rollback Procedures

### Monthly Rollback Drill
```bash
# Schedule monthly rollback testing
# scripts/rollback_drill.sh
echo "🎯 Starting Monthly Rollback Drill"
echo "This will test our rollback procedures without affecting production"

# Simulate a failure condition
echo "Simulating failure condition..."

# Execute rollback
./scripts/quick_rollback_staging.sh

# Validate rollback success
./scripts/validate_staging_health.py

# Document results
echo "📝 Rollback drill completed at $(date)" >> rollback_drill_log.txt
```

## Emergency Contacts

### On-Call Escalation
1. **Primary**: DevOps Engineer (24/7)
2. **Secondary**: Lead Backend Engineer  
3. **Escalation**: Engineering Manager
4. **Final**: CTO

### Emergency Procedures
- **Slack Channel**: #staging-incidents
- **Emergency Phone**: [REDACTED]
- **Incident Management**: [TOOL_URL]

---

**Note**: These procedures should be tested monthly and updated based on lessons learned from each rollback scenario. All team members should be familiar with these procedures and have access to necessary credentials and tools.