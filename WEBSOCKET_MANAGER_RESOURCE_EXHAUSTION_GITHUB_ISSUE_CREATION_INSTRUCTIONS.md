# GitHub Issue Creation Instructions - WebSocket Manager Resource Exhaustion

## STEP 1: CREATE NEW GITHUB ISSUE

### **Issue Title:**
```
🚨 CRITICAL P0: WebSocket Manager Resource Exhaustion Emergency Cleanup Failure
```

### **Issue Labels to Add:**
- `P0`
- `critical`
- `websocket`
- `resource-exhaustion`
- `emergency-cleanup`
- `actively-being-worked-on`
- `agent-session-20250915-174500`

### **Issue Body:**
Copy the complete content from: `GITHUB_ISSUE_WEBSOCKET_MANAGER_RESOURCE_EXHAUSTION_EMERGENCY_CLEANUP_FAILURE.md`

## STEP 2: ADD INITIAL COMMENT

### **Five Whys Analysis Status Update**

**Agent Session**: `agent-session-20250915-174500`
**Date**: 2025-09-15 17:45:00
**Status**: CRITICAL P0 ANALYSIS COMPLETE

### **Current Audit Findings**

From staging auto-solve loop documentation and GCP logs analysis:

#### **Critical Error Pattern Identified**
```
HARD LIMIT: User 105945141827451681156 still over limit after cleanup (20/20)
[ERROR] UNEXPECTED FACTORY ERROR: User 105945141827451681156 has reached the maximum number of WebSocket managers (20). Emergency cleanup attempted but limit still exceeded.
```

#### **Five Whys Root Cause Analysis Results**

**Why #1**: User hitting 20 WebSocket manager limit?
→ WebSocket connections created faster than cleanup rate

**Why #2**: Emergency cleanup failing to free managers?
→ Cleanup criteria too conservative - misses zombie managers

**Why #3**: Zombie managers not detected?
→ No functional validation - assumes "active" = functional

**Why #4**: No aggressive cleanup for resource exhaustion?
→ Missing secondary cleanup strategies for critical scenarios

**Why #5**: No fallback when emergency cleanup fails?
→ Lacks force-cleanup mechanisms for stuck managers

### **Critical Business Impact Assessment**

- **Revenue at Risk**: $500K+ ARR (Chat = 90% of platform value)
- **User Impact**: Complete chat functionality offline for affected users
- **Affected User ID**: 105945141827451681156
- **Service Status**: WebSocket factory initialization completely failing

### **Error Locations in Code**

**Primary File**: `netra_backend/app/websocket_core/websocket_manager_factory.py`
- **Line 1833**: Factory error when limit exceeded after cleanup
- **Line 1415**: Hard limit check logic
- **Line 1397**: Resource limit detection
- **Lines 1716-1724**: Emergency cleanup logic (TOO CONSERVATIVE)

### **Conservative Cleanup Problem Analysis**

Current cleanup only removes managers meeting ALL these overly restrictive criteria:
```python
# PROBLEM: Too conservative - misses zombie managers
if not manager or not manager._is_active:
    cleanup_keys.append(key)  # Only clearly dead
elif manager._metrics.last_activity and manager._metrics.last_activity < cutoff_time:
    cleanup_keys.append(key)  # Only inactive
elif created_time and created_time < cutoff_time and len(manager._connections) == 0:
    cleanup_keys.append(key)  # Only connectionless
```

### **Missing Critical Scenarios**

1. **Stuck Managers**: Appear active but connections are zombie/dead
2. **Resource Exhaustion**: All 20 managers "active" but non-functional
3. **Connection State Mismatch**: Ghost connections never properly closed
4. **Race Conditions**: Managers in inconsistent states during high concurrency

### **Remediation Strategy Phases**

#### **Phase 1: Enhanced Emergency Cleanup (CRITICAL)**
- Functional validation of manager capabilities
- Connection health checks for zombie detection
- Force cleanup of oldest managers regardless of activity
- Aggressive mode when resource exhaustion detected

#### **Phase 2: Manager Health Validation (HIGH)**
- Connection responsiveness testing (ping existing connections)
- Resource utilization validation
- State consistency verification

#### **Phase 3: Graceful Degradation (MEDIUM)**
- Temporary limit increase (25 managers for 60s during emergencies)
- Connection queuing until resources available
- User notification system for resource constraints

### **Immediate Actions Required**

1. **Deploy Emergency Fix**: Implement aggressive cleanup mode
2. **Monitor GCP Logs**: Track cleanup success/failure rates
3. **Test Golden Path**: Validate chat functionality restored
4. **Update Monitoring**: Add alerts for cleanup failures

### **References**

- **Staging Audit**: `audit/staging/auto-solve-loop/iteration-3-next-critical-issue.md`
- **GCP Log Analysis**: Last hour logs showing repeated cleanup failures
- **Business Priority**: CLAUDE.md - Chat = 90% platform value
- **User Context**: USER_CONTEXT_ARCHITECTURE.md - Factory isolation patterns

---

**AGENT SESSION TRACKING**: This issue is actively being worked on by agent session `agent-session-20250915-174500` with comprehensive Five Whys analysis complete and remediation strategy defined.

**CRITICAL MISSION ALIGNMENT**: This directly blocks the Golden Path mission - users must be able to login and get AI responses back.

## STEP 3: REFERENCE EXISTING ISSUES

Check if this relates to or should reference:
- Issue #108 (if it exists and is related to WebSocket issues)
- Any other open WebSocket resource management issues
- Previous emergency cleanup failure reports

## STEP 4: ASSIGN PRIORITY AND TRACKING

- **Priority**: P0 (Critical - blocks core business functionality)
- **Milestone**: Current sprint (immediate resolution required)
- **Assignee**: Technical lead responsible for WebSocket infrastructure
- **Project**: Add to critical infrastructure board

## Commands to Execute

```bash
# Create the issue (adjust as needed based on your GitHub setup)
gh issue create --title "🚨 CRITICAL P0: WebSocket Manager Resource Exhaustion Emergency Cleanup Failure" --body-file GITHUB_ISSUE_WEBSOCKET_MANAGER_RESOURCE_EXHAUSTION_EMERGENCY_CLEANUP_FAILURE.md --label "P0,critical,websocket,resource-exhaustion,emergency-cleanup,actively-being-worked-on,agent-session-20250915-174500"

# Add initial status comment
gh issue comment [ISSUE_NUMBER] --body-file [PATH_TO_COMMENT_FILE]
```

**RETURN**: The exact issue number created and comment ID for tracking purposes.