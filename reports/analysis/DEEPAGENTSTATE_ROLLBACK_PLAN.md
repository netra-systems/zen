# DeepAgentState SSOT Migration - Emergency Rollback Plan

> **Issue**: #871 | **Priority**: P0 CRITICAL | **Golden Path Protection**: $500K+ ARR
>
> **Purpose**: Emergency procedures for rolling back DeepAgentState SSOT migration if critical issues arise

## Rollback Decision Matrix

### When to Execute Rollback

| Severity | Condition | Rollback Level | Max Time to Execute |
|----------|-----------|----------------|-------------------|
| **CRITICAL** | Golden Path down, WebSocket events failing | Level 3: Complete System | **< 5 minutes** |
| **HIGH** | Runtime errors, agent execution failures | Level 2: Phase Rollback | **< 15 minutes** |
| **MEDIUM** | Test failures, import errors | Level 1: File Rollback | **< 30 minutes** |
| **LOW** | Performance degradation, warnings | Continue with fixes | Monitor & document |

### Critical Trigger Conditions

**IMMEDIATE ROLLBACK REQUIRED**:
- ❌ WebSocket events stop delivering to users
- ❌ Agent execution throws AttributeError exceptions
- ❌ User data isolation compromised
- ❌ Mission critical tests failing > 10%
- ❌ Production deployment failures

## Level 1: Single File Rollback

**Use Case**: Specific file migration causes isolated issues

### Procedure
```bash
# 1. Identify problematic file
PROBLEM_FILE="netra_backend/app/agents/[specific_file].py"

# 2. Quick rollback to previous commit
git checkout HEAD~1 -- "$PROBLEM_FILE"

# 3. Immediate validation
python -c "import sys; sys.path.append('.'); from netra_backend.app.agents.[module] import *; print('✅ Import restored')"

# 4. Golden Path validation
python tests/mission_critical/test_websocket_agent_events_suite.py

# 5. Commit rollback if successful
git add "$PROBLEM_FILE"
git commit -m "rollback: restore $PROBLEM_FILE to deprecated DeepAgentState import

- Emergency rollback due to migration issue
- Restores functionality while investigation continues
- Temporary measure pending issue resolution

Issue: #871 DeepAgentState SSOT Migration"
```

### Validation Checklist
- [ ] File imports successfully
- [ ] WebSocket events still working
- [ ] No runtime AttributeError exceptions
- [ ] Mission critical tests pass

## Level 2: Phase Rollback

**Use Case**: Migration phase causes systemic issues

### Procedure
```bash
# 1. Identify pre-phase commit (set during migration)
PRE_PHASE_COMMIT=$(git log --oneline --grep="checkpoint: pre-phase" -n 1 | cut -d' ' -f1)

# 2. Rollback to pre-phase state
git reset --hard "$PRE_PHASE_COMMIT"

# 3. Force push if already deployed (DANGEROUS - only in emergency)
# git push origin develop-long-lived --force

# 4. Immediate system validation
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/unified_test_runner.py --category mission_critical --fast-fail

# 5. Deployment rollback if needed
python scripts/deploy_to_gcp.py --project netra-staging --rollback
```

### Phase-Specific Rollback Points

**Phase 1 Rollback** (Pre-migration validation):
```bash
git checkout $(git log --oneline --grep="checkpoint: pre-migration setup" -n 1 | cut -d' ' -f1)
```

**Phase 2 Rollback** (SSOT interface enhancement):
```bash
git checkout $(git log --oneline --grep="checkpoint: pre-interface-enhancement" -n 1 | cut -d' ' -f1)
```

**Phase 3 Rollback** (Production file migration):
```bash
git checkout $(git log --oneline --grep="checkpoint: pre-production-migration" -n 1 | cut -d' ' -f1)
```

## Level 3: Complete System Restore

**Use Case**: Critical Golden Path failure, immediate business impact

### Emergency Procedure (< 5 minutes)
```bash
# 1. IMMEDIATE: Rollback to last known good state
LAST_GOOD_COMMIT="[commit_hash_before_migration_start]"
git checkout "$LAST_GOOD_COMMIT"

# 2. Emergency validation (must complete in < 2 minutes)
python tests/mission_critical/test_websocket_agent_events_suite.py --fast-fail

# 3. If validation passes, force deployment rollback
python scripts/deploy_to_gcp.py --project netra-staging --rollback --emergency

# 4. Create emergency branch for investigation
git checkout -b emergency-rollback-$(date +%Y%m%d-%H%M%S)
git push origin emergency-rollback-$(date +%Y%m%d-%H%M%S)

# 5. Notify team
echo "🚨 EMERGENCY ROLLBACK EXECUTED - DeepAgentState migration caused Golden Path failure"
```

### Post-Rollback Immediate Actions
1. **Validate Golden Path**: Ensure user chat functionality restored
2. **Monitor Systems**: Watch for any residual issues
3. **Document Incident**: Record exact failure mode and timing
4. **Team Notification**: Inform all stakeholders of rollback

## Rollback Validation Procedures

### Level 1 Validation (File-Level)
```bash
# Import validation
python -c "from netra_backend.app.agents.state import DeepAgentState; print('✅ Deprecated import working')"

# WebSocket event validation
python tests/mission_critical/test_websocket_agent_events_suite.py --test-single-event

# No runtime errors
python -c "
from netra_backend.app.agents.state import DeepAgentState
state = DeepAgentState()
print(f'✅ thread_id property: {state.thread_id}')
"
```

### Level 2 Validation (Phase-Level)
```bash
# Full mission critical suite
python tests/mission_critical/test_websocket_agent_events_suite.py

# Integration test sample
python tests/unified_test_runner.py --category integration --sample 10

# SSOT compliance (should show violations again)
python scripts/check_deepagentstate_ssot_compliance.py
```

### Level 3 Validation (System-Level)
```bash
# Complete Golden Path validation
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_no_ssot_violations.py --expect-violations

# Full integration suite (time-limited)
timeout 300 python tests/unified_test_runner.py --category integration --real-services

# Production readiness check
python scripts/pre_deployment_audit.py --critical-only
```

## Data Integrity & State Management

### User Session Handling During Rollback

**CRITICAL**: Active user sessions may be affected during rollback

#### Session Safety Procedures
```bash
# 1. Check for active WebSocket connections
python scripts/check_active_websocket_sessions.py

# 2. Graceful session termination if needed
python scripts/gracefully_terminate_websocket_sessions.py --reason "emergency_maintenance"

# 3. Session restoration after rollback
python scripts/validate_websocket_session_restoration.py
```

#### Database State Consistency
```bash
# Verify DeepAgentState database records are consistent
python scripts/validate_agent_state_database_consistency.py --check-all

# Clean up any orphaned state records
python scripts/cleanup_orphaned_agent_states.py --dry-run
```

## Communication & Incident Response

### Stakeholder Communication Templates

#### Level 1 Rollback (Internal)
```
Subject: DeepAgentState Migration - File Rollback Executed

Issue: Migration of [filename] caused [specific issue]
Action: Rolled back single file to maintain system stability
Impact: Minimal, Golden Path functionality preserved
Next Steps: Investigation and fix in progress

Technical Details:
- File: [filename]
- Commit: [rollback_commit]
- Issue: #871
```

#### Level 2 Rollback (Team)
```
Subject: 🔄 DeepAgentState Migration Phase Rollback

Issue: Migration phase [X] caused systemic issues
Action: Complete phase rollback to [commit_hash]
Impact: Migration progress reset, system stability restored
Golden Path: ✅ Validated functional

Next Steps:
1. Root cause analysis
2. Fix migration approach
3. Re-attempt with enhanced validation
```

#### Level 3 Rollback (Executive)
```
Subject: 🚨 CRITICAL: Emergency System Rollback - Golden Path Restored

BUSINESS IMPACT: DeepAgentState migration caused Golden Path failure
ACTION TAKEN: Complete system rollback executed in <5 minutes
CURRENT STATUS: $500K+ ARR chat functionality restored and validated

Customer Impact: [Duration] minutes of degraded chat experience
Resolution: System fully operational, monitoring ongoing
Investigation: Full post-mortem to follow

Next Steps:
1. Enhanced testing before next attempt
2. Risk assessment review
3. Migration strategy revision
```

## Post-Rollback Investigation

### Immediate Analysis Requirements

1. **Failure Mode Documentation**
   - Exact error messages and stack traces
   - Timing of failure (which migration step)
   - Affected systems and user impact

2. **Root Cause Analysis**
   - Why did the issue occur?
   - What validation missed the problem?
   - How can detection be improved?

3. **Migration Strategy Review**
   - Was the approach correct?
   - Are additional safeguards needed?
   - Should migration order change?

### Investigation Checklist
- [ ] Document exact failure mode and timing
- [ ] Collect all error logs and stack traces
- [ ] Identify root cause (interface, dependency, validation)
- [ ] Assess impact on Golden Path and users
- [ ] Review migration strategy for gaps
- [ ] Plan enhanced approach for next attempt
- [ ] Update rollback procedures based on experience

## Prevention & Learning

### Enhanced Validation for Next Attempt

Based on rollback experience, add:

1. **Pre-Migration Validation**
   - Comprehensive interface compatibility testing
   - Full Golden Path simulation
   - Load testing with real user patterns

2. **Migration Monitoring**
   - Real-time Golden Path health checks
   - Automated rollback triggers
   - Progress checkpoints every 5 changes

3. **Validation Enhancement**
   - Extended WebSocket event testing
   - Multi-user isolation verification
   - Production workload simulation

### Rollback Plan Updates

After each rollback execution:
- [ ] Document what worked well
- [ ] Identify process improvements
- [ ] Update rollback time estimates
- [ ] Enhance automation where possible
- [ ] Review communication effectiveness

## Recovery Timeline Expectations

| Rollback Level | Detection Time | Execution Time | Validation Time | Total Recovery |
|---------------|---------------|----------------|-----------------|----------------|
| **Level 1** | 1-5 minutes | 2-3 minutes | 5-10 minutes | **< 15 minutes** |
| **Level 2** | 2-10 minutes | 5-10 minutes | 10-15 minutes | **< 30 minutes** |
| **Level 3** | 1-5 minutes | 2-5 minutes | 3-5 minutes | **< 10 minutes** |

**Note**: Level 3 is fastest because it uses known-good state with minimal validation required.

## Success Metrics Post-Rollback

### Immediate Validation (< 5 minutes)
- [ ] ✅ Golden Path WebSocket events functional
- [ ] ✅ No runtime AttributeError exceptions
- [ ] ✅ User chat functionality restored
- [ ] ✅ Mission critical tests passing

### Short-term Validation (< 30 minutes)
- [ ] ✅ All affected systems operational
- [ ] ✅ Database consistency verified
- [ ] ✅ No user data integrity issues
- [ ] ✅ Integration tests passing

### Long-term Monitoring (24-48 hours)
- [ ] ✅ System performance normal
- [ ] ✅ No recurring issues
- [ ] ✅ User satisfaction maintained
- [ ] ✅ Development velocity unaffected

---

**CRITICAL REMINDER**: This rollback plan prioritizes Golden Path protection and $500K+ ARR preservation above migration progress. Better to have a working system with SSOT violations than a broken system without them.