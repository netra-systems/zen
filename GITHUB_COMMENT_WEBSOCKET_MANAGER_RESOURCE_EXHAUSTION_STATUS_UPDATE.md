# WebSocket Manager Resource Exhaustion - Test Plan Update

**Date:** 2025-09-15
**Session:** agent-session-20250915-164538
**Issue:** WebSocket Manager Resource Exhaustion Emergency Cleanup Failure

## 📋 TEST PLAN CREATED

### Test Strategy Summary

Created comprehensive test plan for reproducing and validating the WebSocket manager resource exhaustion emergency cleanup failure. The plan follows CLAUDE.md testing best practices with real services focus.

#### **Key Test Categories Planned:**

1. **Unit Tests** - Emergency cleanup logic validation
   - Target File: `netra_backend/tests/websocket_core/test_websocket_manager_factory_emergency_cleanup.py`
   - Focus: Zombie manager detection, conservative vs enhanced cleanup comparison
   - Expected: FAIL initially (proves bug exists), PASS after fix

2. **Integration Tests** - Resource limit scenarios with real components
   - Target File: `netra_backend/tests/integration/test_websocket_resource_exhaustion_scenarios.py`
   - Focus: 20-manager limit scenarios, multi-user resource competition
   - Expected: Demonstrates real-world resource exhaustion patterns

3. **Performance Tests** - Cleanup latency and effectiveness validation
   - Target File: `tests/performance/test_websocket_cleanup_performance.py`
   - Focus: 500ms cleanup SLA, memory recovery validation
   - Expected: Establishes performance baselines and requirements

#### **Critical Test Scenarios:**

✅ **Resource Exhaustion Reproduction**
- Create 20 WebSocket managers for single user
- Include zombie managers (appear active, actually stuck)
- Trigger emergency cleanup when limit reached
- Verify cleanup fails to free sufficient managers
- Confirm user cannot create new connections

✅ **Zombie Manager Detection**
- Simulate managers with dead/stuck connections
- Test functional validation during cleanup
- Verify health checks identify non-responsive managers
- Validate force cleanup removes problematic managers

✅ **Multi-User Resource Competition**
- Multiple users hitting resource limits simultaneously
- Validate user isolation during emergency cleanup
- Ensure one user's resource exhaustion doesn't affect others
- Test concurrent cleanup operations

#### **Success Metrics Defined:**

- **Zombie Detection Rate**: ≥80% of zombie managers identified
- **Resource Recovery**: ≥60% of zombie resources freed during emergency cleanup
- **Performance SLA**: Cleanup operations complete within 500ms
- **User Experience**: No permanent connection blocking
- **Memory Efficiency**: ≥80% expected memory freed from removed managers

#### **Business Value Justification:**

- **Segment**: Enterprise/Mid/Early (All tiers affected)
- **Goal**: Retention/Stability - Prevent churn from chat outages
- **Value Impact**: Chat functionality delivers 90% of platform value
- **Revenue Impact**: $500K+ ARR directly at risk from resource exhaustion

---

## 🚀 NEXT STEPS

**Immediate Actions:**
1. Execute test plan creation (Step 4)
2. Run tests to confirm they fail (proving bug exists)
3. Implement enhanced emergency cleanup algorithm
4. Validate fix with comprehensive test execution
5. Deploy to staging with enhanced monitoring

**Critical Priority**: This issue blocks the Golden Path mission - users cannot login and get AI responses due to WebSocket connection failures.

---

**Technical Reference**: `C:\GitHub\netra-apex\netra_backend\app\websocket_core\websocket_manager_factory.py` Lines 1716-1724 (emergency cleanup logic - TOO CONSERVATIVE)