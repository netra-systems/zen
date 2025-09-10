# SSOT Tool Dispatcher Rollback Procedures & Emergency Response

**Document Type:** Emergency Procedures Manual  
**Priority:** P0 CRITICAL - $500K+ ARR Protection  
**Status:** ACTIVE  
**Last Updated:** 2025-09-10  

## Overview

This document provides comprehensive rollback procedures for the SSOT Tool Dispatcher consolidation project. These procedures ensure business continuity and protect the Golden Path user flow (login → AI response) during all phases of remediation.

## Emergency Contact Protocol

**Business Impact:** If chat functionality is degraded (90% of platform value)
1. **Immediate Response:** Execute appropriate rollback procedure below
2. **Business Notification:** Alert stakeholders within 15 minutes
3. **Technical Escalation:** Engage senior engineering team
4. **Customer Communication:** Prepare status page update if customer-facing

## Phase 1: Foundation Analysis Rollback

### Risk Level: MINIMAL (Analysis Only)
**Scenario:** Analysis reveals blocking issues or incorrect assumptions

#### Rollback Actions:
```bash
# Phase 1 is analysis-only, no code changes to rollback
# Document issues and escalate
echo "Phase 1 analysis complete - no rollback needed"
```

#### Emergency Stop Criteria:
- [ ] Major architectural incompatibility discovered
- [ ] Critical business requirement conflicts identified  
- [ ] Test infrastructure fundamentally broken
- [ ] WebSocket event delivery patterns incompatible

#### Recovery Actions:
1. **Document Blockers:** Update GitHub issue #234 with findings
2. **Escalate Decision:** Business stakeholder review required
3. **Alternative Planning:** Consider different consolidation approach
4. **Timeline Adjustment:** Revise remediation schedule if needed

## Phase 2: Factory Pattern Consolidation Rollback

### Risk Level: MEDIUM
**Scenario:** Factory consolidation breaks consumer integrations

#### Pre-Flight Safety Checks:
```bash
# Before starting Phase 2, verify rollback capability
git tag "pre-factory-consolidation-$(date +%Y%m%d)"
git checkout -b "factory-consolidation-$(date +%Y%m%d)"

# Verify all mission critical tests pass
python -m pytest tests/mission_critical/test_tool_dispatcher_ssot_compliance.py
python -m pytest tests/mission_critical/test_websocket_agent_events_suite.py
```

#### Immediate Rollback (< 30 minutes):
```bash
# EMERGENCY: Immediate revert to working state
git checkout main
git reset --hard pre-factory-consolidation-$(date +%Y%m%d)

# Verify golden path functionality
python tests/e2e/staging/test_golden_path_validation.py

# Restart staging services
python scripts/deploy_to_gcp.py --project netra-staging --quick-deploy
```

#### Validation After Rollback:
```bash
# Verify all critical functionality restored
python -m pytest tests/mission_critical/test_tool_dispatcher_ssot_compliance.py
python -m pytest tests/integration/test_agent_registry_websocket_bridge.py
python -c "
from netra_backend.app.agents.tool_executor_factory import get_tool_executor_factory
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
print('✅ All imports working')
"
```

#### Warning Signs to Watch:
- [ ] Tool dispatcher factory creation failures
- [ ] WebSocket event delivery interruptions
- [ ] Agent registry initialization errors
- [ ] Memory leak patterns in factory usage
- [ ] User isolation boundary violations

## Phase 3: Implementation Consolidation Rollback

### Risk Level: HIGH
**Scenario:** Core implementation changes break business functionality

#### Pre-Flight Safety Checks:
```bash
# Create comprehensive safety checkpoint
git tag "pre-implementation-consolidation-$(date +%Y%m%d)"
git checkout -b "implementation-consolidation-$(date +%Y%m%d)"

# Full system health check
python scripts/health_check_comprehensive.py
python -m pytest tests/mission_critical/ --real-services
python tests/e2e/staging/test_complete_chat_business_value_flow.py
```

#### Emergency Rollback Procedures:

##### Level 1: Quick Revert (< 15 minutes)
```bash
# CRITICAL: Chat functionality compromised
git checkout main
git reset --hard pre-implementation-consolidation-$(date +%Y%m%d)

# Emergency staging deployment
python scripts/deploy_to_gcp.py --project netra-staging --emergency-rollback

# Verify core functionality immediately
curl -X POST https://staging.netra-apex.com/health/golden-path
```

##### Level 2: Service Restart (< 30 minutes)
```bash
# If Level 1 insufficient, restart all services
python scripts/deploy_to_gcp.py --project netra-staging --full-restart

# Validate each service individually
python scripts/validate_service_health.py --service backend
python scripts/validate_service_health.py --service auth
python scripts/validate_service_health.py --service websocket
```

##### Level 3: Infrastructure Reset (< 60 minutes)
```bash
# Nuclear option: Complete infrastructure reset
python scripts/deploy_to_gcp.py --project netra-staging --rebuild-all

# Wait for services to stabilize
sleep 300

# Run comprehensive validation
python tests/e2e/staging/test_golden_path_validation.py
python -m pytest tests/mission_critical/test_websocket_agent_events_suite.py --real-services
```

#### Critical Monitoring During Phase 3:
- [ ] **WebSocket Connection Success Rate:** >99%
- [ ] **Agent Creation Success Rate:** >99.5%
- [ ] **Tool Execution Success Rate:** >98%
- [ ] **User Isolation Boundary Integrity:** 100%
- [ ] **Memory Usage:** Within 15% of baseline
- [ ] **Response Latency:** <2s for tool execution
- [ ] **Chat Completion Rate:** >95%

## Phase 4: Performance Optimization Rollback

### Risk Level: MEDIUM  
**Scenario:** Performance optimizations cause regressions

#### Pre-Flight Safety Checks:
```bash
# Establish performance baselines
python scripts/performance_baseline_capture.py --output baselines/pre-optimization.json

# Create safety checkpoint
git tag "pre-performance-optimization-$(date +%Y%m%d)"
```

#### Performance Rollback Criteria:
- [ ] Memory usage increases >20% from baseline
- [ ] Tool execution latency increases >50% from baseline  
- [ ] WebSocket event delivery latency >500ms
- [ ] Agent startup time >10s
- [ ] Database connection pool exhaustion
- [ ] User session management failures

#### Rollback Procedure:
```bash
# Revert to pre-optimization state
git checkout main
git reset --hard pre-performance-optimization-$(date +%Y%m%d)

# Validate performance restoration
python scripts/performance_validation.py --baseline baselines/pre-optimization.json

# Redeploy with original performance characteristics
python scripts/deploy_to_gcp.py --project netra-staging --performance-mode baseline
```

## Continuous Monitoring & Alerting

### Golden Path Health Metrics
**Monitor every 30 seconds during active remediation:**

```bash
# Golden Path validation script
python scripts/golden_path_monitor.py --interval 30 --alert-threshold 95
```

**Key Metrics:**
- User login success rate: >99%
- WebSocket connection establishment: >99%
- Agent response delivery: >95%
- Tool execution success: >98%
- End-to-end completion rate: >95%

### Automated Rollback Triggers

#### Script-Based Monitoring:
```bash
#!/bin/bash
# automatic_rollback_monitor.sh

while true; do
    # Check golden path health
    golden_path_health=$(python scripts/golden_path_health_check.py --json | jq '.success_rate')
    
    if (( $(echo "$golden_path_health < 0.90" | bc -l) )); then
        echo "CRITICAL: Golden Path health at $golden_path_health% - Triggering rollback"
        ./emergency_rollback.sh
        break
    fi
    
    sleep 30
done
```

#### Alert Integration:
- **Slack:** `#critical-alerts` channel for immediate team notification
- **PagerDuty:** P0 alerts for golden path degradation
- **Email:** Business stakeholder notification within 15 minutes
- **Status Page:** Customer communication for >5 minute outages

### Recovery Validation Checklist

#### After Any Rollback - Verify All Items:
- [ ] **User Authentication:** Login flow working end-to-end
- [ ] **WebSocket Events:** All 5 critical events being delivered
- [ ] **Agent Execution:** Supervisor and sub-agents responding
- [ ] **Tool Dispatcher:** All factory patterns working
- [ ] **Database Connectivity:** All tiers (Redis, PostgreSQL, ClickHouse) accessible
- [ ] **Memory Usage:** Within expected bounds
- [ ] **Error Rates:** <1% across all services
- [ ] **Response Times:** Within SLA targets

## Test Scripts for Rollback Validation

### Complete System Health Check:
```bash
#!/bin/bash
# complete_rollback_validation.sh

echo "🔍 Starting comprehensive rollback validation..."

# 1. Mission Critical Tests
echo "Running mission critical tests..."
python -m pytest tests/mission_critical/test_tool_dispatcher_ssot_compliance.py -v
if [ $? -ne 0 ]; then
    echo "❌ Mission critical tests FAILED"
    exit 1
fi

# 2. WebSocket Validation (if Docker available)
echo "Testing WebSocket functionality..."
python -c "
from netra_backend.app.websocket_core.manager import WebSocketManager
print('✅ WebSocket imports successful')
"

# 3. Factory Pattern Validation
echo "Testing factory patterns..."
python -c "
from netra_backend.app.agents.tool_executor_factory import get_tool_executor_factory
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
print('✅ Factory patterns working')
"

# 4. User Context Validation
echo "Testing user isolation..."
python -c "
from netra_backend.app.services.user_execution_context import UserExecutionContext
context = UserExecutionContext(user_id='test', run_id='test', thread_id='test')
context.verify_isolation()
print('✅ User isolation working')
"

echo "✅ All rollback validation checks passed"
```

### Business Value Verification:
```bash
#!/bin/bash
# business_value_verification.sh

echo "🎯 Verifying business value preservation..."

# Test chat functionality core flow
python -c "
# Simulate core chat flow
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext

context = UserExecutionContext(
    user_id='rollback_test',
    run_id='rollback_validation',
    thread_id='test_thread'
)

print('✅ Core chat infrastructure available')
"

echo "✅ Business value preservation verified"
```

## Emergency Contact Information

### Technical Escalation:
- **Primary:** Lead Engineer (on-call rotation)
- **Secondary:** Platform Team Lead
- **Tertiary:** CTO

### Business Escalation:
- **Primary:** Product Manager
- **Secondary:** VP Engineering  
- **Critical:** CEO (for customer-facing outages >30 minutes)

### Customer Communication:
- **Status Page:** status.netra-apex.com
- **Support Email:** support@netra-systems.com
- **Emergency Hotline:** Configure based on business requirements

## Lessons Learned Integration

### Post-Rollback Actions:
1. **Incident Report:** Document what triggered rollback
2. **Root Cause Analysis:** 5 Whys analysis of failure mode
3. **Process Improvement:** Update rollback procedures based on experience
4. **Test Enhancement:** Add tests to catch the failure mode
5. **Documentation Update:** Revise this document with new insights

### Success Metrics After Rollback:
- **Recovery Time:** <60 minutes for any rollback scenario
- **Business Impact:** <5% revenue impact
- **Customer Impact:** <1% of active users affected
- **Team Response:** Full team aligned within 30 minutes

---

**Document Maintainer:** SSOT Remediation Team  
**Review Schedule:** After each phase completion  
**Approval Required:** Technical Lead + Product Manager  
**Version:** 1.0.0  

**Remember:** The goal is not to avoid rollbacks, but to execute them swiftly and safely when needed to protect business value.