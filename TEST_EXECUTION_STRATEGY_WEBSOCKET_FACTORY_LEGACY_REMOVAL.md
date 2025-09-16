# Test Execution Strategy: WebSocket Factory Legacy Removal (Issue #1098)

**Created**: 2025-09-15 | **Priority**: P0 MISSION CRITICAL
**Scope**: 655 files, 2,615 SSOT violations, 1,001 lines legacy code removal
**Business Impact**: $500K+ ARR Golden Path protection

## Executive Summary

This document provides the execution strategy for testing WebSocket Manager Factory legacy removal. The strategy follows the **"Failing Tests First"** approach to prove violations exist, then validate SSOT migration success.

**CRITICAL UNDERSTANDING**: All tests must initially **FAIL** to demonstrate current violations, then **PASS** after remediation to prove SSOT migration success.

## Test Execution Phases

### Phase 1: Violation Detection (Tests Must FAIL)

**Purpose**: Prove that 2,615 SSOT violations exist across 655 files
**Expected Result**: All tests FAIL with clear violation messages

#### Command Sequence:

```bash
# 1. Run unit tests to prove violations exist
echo "Phase 1: Running unit tests to detect SSOT violations..."
python tests/unified_test_runner.py \
    --category unit \
    --pattern "*websocket_factory_legacy*" \
    --expect-failures \
    --verbose

# Expected Result: ALL TESTS FAIL
# - test_factory_import_violations.py: FAIL (2,615 violations found)
# - test_ssot_manager_usage.py: FAIL (multiple manager types detected)
# - test_websocket_events_ssot.py: FAIL (factory event delivery detected)

# 2. Run integration tests with real services
echo "Phase 1: Running integration tests with real services..."
python tests/unified_test_runner.py \
    --category integration \
    --pattern "*websocket_ssot*" \
    --real-services \
    --expect-failures \
    --verbose

# Expected Result: ALL TESTS FAIL
# - test_real_websocket_ssot_integration.py: FAIL (factory patterns in real services)

# 3. Run E2E staging tests (if staging available)
echo "Phase 1: Running E2E staging tests..."
python tests/unified_test_runner.py \
    --category e2e \
    --pattern "*staging*ssot*" \
    --env staging \
    --expect-failures \
    --verbose

# Expected Result: ALL TESTS FAIL
# - test_staging_golden_path_ssot.py: FAIL (factory patterns in staging)
```

#### Validation Criteria (Phase 1):

- ✅ **ALL TESTS FAIL** with specific violation messages
- ✅ **2,615 import violations** detected and reported
- ✅ **655 files** with violations identified
- ✅ **Factory patterns** detected in real services
- ✅ **Non-SSOT event delivery** detected

### Phase 2: SSOT Migration Implementation

**Purpose**: Remove factory legacy and implement SSOT patterns
**Duration**: 1-2 weeks

#### Migration Steps:

1. **File Removal**:
   ```bash
   # Remove the 1,001-line legacy factory file
   rm netra_backend/app/websocket_core/websocket_manager_factory.py
   ```

2. **Import Migration** (655 files):
   ```bash
   # Run systematic import replacement
   python scripts/websocket_import_migration_tool.py \
       --source-pattern "websocket_manager_factory" \
       --target-pattern "canonical_imports" \
       --dry-run

   # Apply changes after review
   python scripts/websocket_import_migration_tool.py \
       --source-pattern "websocket_manager_factory" \
       --target-pattern "canonical_imports" \
       --apply
   ```

3. **Manager Consolidation**:
   ```bash
   # Consolidate all managers to use UnifiedWebSocketManager
   python scripts/websocket_manager_consolidation.py \
       --target-manager "UnifiedWebSocketManager" \
       --remove-duplicates
   ```

4. **Event Delivery Migration**:
   ```bash
   # Migrate event delivery to SSOT patterns
   python scripts/websocket_event_delivery_migration.py \
       --ssot-delivery-patterns
   ```

### Phase 3: Validation Tests (Tests Must PASS)

**Purpose**: Prove SSOT migration successful
**Expected Result**: All tests PASS

#### Command Sequence:

```bash
# 1. Run unit tests to validate SSOT compliance
echo "Phase 3: Validating SSOT compliance with unit tests..."
python tests/unified_test_runner.py \
    --category unit \
    --pattern "*websocket_factory_legacy*" \
    --verbose

# Expected Result: ALL TESTS PASS
# - test_factory_import_violations.py: PASS (0 violations found)
# - test_ssot_manager_usage.py: PASS (single SSOT manager only)
# - test_websocket_events_ssot.py: PASS (SSOT event delivery confirmed)

# 2. Run integration tests with real services
echo "Phase 3: Validating real services SSOT compliance..."
python tests/unified_test_runner.py \
    --category integration \
    --pattern "*websocket_ssot*" \
    --real-services \
    --verbose

# Expected Result: ALL TESTS PASS
# - test_real_websocket_ssot_integration.py: PASS (real services use SSOT)

# 3. Run E2E staging tests
echo "Phase 3: Validating staging Golden Path with SSOT..."
python tests/unified_test_runner.py \
    --category e2e \
    --pattern "*staging*ssot*" \
    --env staging \
    --verbose

# Expected Result: ALL TESTS PASS
# - test_staging_golden_path_ssot.py: PASS (Golden Path uses SSOT)

# 4. Run complete test suite to ensure no regressions
echo "Phase 3: Running complete test suite..."
python tests/unified_test_runner.py \
    --categories unit integration e2e \
    --real-services \
    --env staging

# Expected Result: ALL TESTS PASS (no regressions)
```

#### Validation Criteria (Phase 3):

- ✅ **ALL TESTS PASS** without errors
- ✅ **0 import violations** detected
- ✅ **Single SSOT manager** implementation only
- ✅ **SSOT event delivery** confirmed
- ✅ **Golden Path operational** on staging
- ✅ **No regressions** in existing functionality

## Test File Locations

### Unit Tests:
```
/c/netra-apex/tests/unit/websocket_factory_legacy/
├── test_factory_import_violations.py
├── test_ssot_manager_usage.py
├── test_websocket_events_ssot.py
└── __init__.py
```

### Integration Tests:
```
/c/netra-apex/tests/integration/websocket_ssot/
├── test_real_websocket_ssot_integration.py
└── __init__.py
```

### E2E Tests:
```
/c/netra-apex/tests/e2e/staging/
├── test_staging_golden_path_ssot.py
└── __init__.py
```

## Monitoring and Alerts

### Continuous Testing:

```bash
# Set up automated test execution
# 1. Pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "Running WebSocket SSOT validation tests..."
python tests/unified_test_runner.py \
    --category unit \
    --pattern "*websocket_factory_legacy*" \
    --fast-fail
EOF

# 2. CI/CD pipeline validation
cat > .github/workflows/websocket-ssot-validation.yml << 'EOF'
name: WebSocket SSOT Validation
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run SSOT validation tests
        run: |
          python tests/unified_test_runner.py \
            --categories unit integration \
            --pattern "*websocket*ssot*" \
            --real-services
EOF
```

### Business Impact Monitoring:

```bash
# Golden Path availability monitoring
python scripts/golden_path_health_check.py \
    --staging-url "https://staging.netrasystems.ai" \
    --check-websocket-events \
    --alert-on-failure

# WebSocket event delivery monitoring
python scripts/websocket_event_monitoring.py \
    --events "agent_started,agent_thinking,tool_executing,tool_completed,agent_completed" \
    --environment staging \
    --alert-threshold 95%
```

## Risk Mitigation

### Rollback Plan:

```bash
# If migration fails, rollback procedure:
echo "Initiating rollback..."

# 1. Restore factory file from backup
cp backups/websocket_manager_factory.py.backup \
   netra_backend/app/websocket_core/websocket_manager_factory.py

# 2. Restore import patterns
python scripts/rollback_import_migration.py \
    --restore-factory-imports \
    --backup-date $(date +%Y%m%d)

# 3. Validate rollback success
python tests/unified_test_runner.py \
    --category integration \
    --pattern "*websocket*" \
    --real-services

echo "Rollback complete. System restored to previous state."
```

### Pre-Migration Backup:

```bash
# Create comprehensive backup before migration
echo "Creating pre-migration backup..."

# 1. Backup all affected files
tar -czf backups/websocket_factory_migration_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    netra_backend/app/websocket_core/ \
    netra_backend/app/agents/ \
    netra_backend/app/services/ \
    tests/

# 2. Document current state
python scripts/document_current_websocket_state.py \
    --output backups/websocket_state_pre_migration.json

# 3. Export current test results
python tests/unified_test_runner.py \
    --category all \
    --export-results backups/test_results_pre_migration.json
```

## Success Metrics

### Technical Metrics:
- **Import Violations**: 2,615 → 0
- **Files Affected**: 655 → 0 violations
- **Legacy Code Lines**: 1,001 → 0 (file removed)
- **Manager Types**: Multiple → 1 (UnifiedWebSocketManager)
- **Event Delivery**: Factory → SSOT patterns

### Business Metrics:
- **Golden Path Availability**: Maintained at 99%+
- **WebSocket Event Delivery**: 100% (all 5 events)
- **Multi-User Isolation**: Verified working
- **Chat Functionality**: 90% of platform value protected
- **Revenue Protection**: $500K+ ARR maintained

### Performance Metrics:
- **WebSocket Connection Time**: < 2 seconds
- **Event Delivery Latency**: < 500ms
- **Memory Usage**: No increase from SSOT consolidation
- **CPU Usage**: No degradation

## Timeline

### Week 1: Violation Detection
- **Day 1-2**: Create and run failing tests
- **Day 3-4**: Document all violations found
- **Day 5**: Validate test coverage complete

### Week 2: SSOT Migration
- **Day 1-2**: Remove factory file and update imports
- **Day 3-4**: Consolidate manager implementations
- **Day 5**: Migrate event delivery patterns

### Week 3: Validation
- **Day 1-2**: Run validation tests and fix issues
- **Day 3-4**: Deploy to staging and validate Golden Path
- **Day 5**: Complete documentation and monitoring

## Conclusion

This test execution strategy ensures systematic validation of WebSocket Manager Factory legacy removal while protecting critical business functionality. The **"Failing Tests First"** approach provides concrete proof of violations and successful remediation.

**Key Success Factors**:
1. **All tests FAIL initially** (proving violations exist)
2. **Systematic SSOT migration** (removing 2,615 violations)
3. **All tests PASS finally** (proving migration success)
4. **Golden Path remains operational** (protecting $500K+ ARR)

**Next Steps**:
1. Execute Phase 1 to prove violations exist
2. Implement SSOT migration systematically
3. Execute Phase 3 to validate success
4. Monitor Golden Path continuously