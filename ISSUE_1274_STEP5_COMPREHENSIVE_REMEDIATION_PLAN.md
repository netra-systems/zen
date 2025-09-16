# Issue #1274 - Step 5: Comprehensive Remediation Plan

## Executive Summary

Based on successful SSOT infrastructure validation, this plan systematically migrates **181 remaining deprecated `get_agent_instance_factory()` calls** across **55 files** to the working `create_agent_instance_factory(user_context)` pattern.

### Business Impact Protection
- **$500K+ ARR Golden Path**: 13 critical integration tests require immediate migration
- **Multi-User Production**: 50+ WebSocket integration tests blocking concurrent user support
- **Enterprise Compliance**: User isolation violations prevent SOC2/HIPAA certification

---

## Phase 1: Golden Path Protection (CRITICAL - 13 Files)
*Priority: IMMEDIATE - Business Revenue Protection*

### 1.1 Agent Golden Path Integration Tests
**Business Impact**: Protects $500K+ ARR by ensuring core message processing pipeline stability

```bash
# Files requiring migration (1 occurrence each):
tests/integration/agent_golden_path/test_websocket_event_sequence_integration.py
tests/integration/agent_golden_path/test_multi_user_message_isolation_integration.py
tests/integration/agent_golden_path/test_multi_user_concurrent_message_processing.py
tests/integration/agent_golden_path/test_message_processing_pipeline.py
tests/integration/agent_golden_path/test_message_pipeline_integration.py
tests/integration/agent_golden_path/test_golden_path_performance_integration.py
tests/integration/agent_golden_path/test_agent_websocket_events_comprehensive.py
tests/integration/agent_golden_path/test_agent_response_quality_integration.py
tests/integration/agent_golden_path/test_agent_message_pipeline_end_to_end.py
```

**Migration Pattern for Each File**:
```python
# ❌ DEPRECATED (security vulnerability):
factory = get_agent_instance_factory()

# ✅ SSOT COMPLIANT (enterprise-grade isolation):
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import create_agent_instance_factory

# Create proper user context
user_context = UserExecutionContext(
    user_id="test_user_golden_path",
    thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
    run_id=f"test_run_{uuid.uuid4().hex[:8]}",
    request_id=f"test_req_{uuid.uuid4().hex[:8]}"
)

# Get isolated factory
factory = create_agent_instance_factory(user_context)
```

### 1.2 Core Integration Tests
**Files requiring migration**:
```bash
tests/integration/test_agent_golden_path_messages.py (1 occurrence)
tests/integration/test_agent_execution_business_value.py (1 occurrence)
tests/integration/test_agent_execution_flow_integration.py (1 occurrence)
tests/e2e/test_golden_path_multi_user_concurrent.py (1 occurrence)
```

---

## Phase 2: WebSocket Infrastructure (HIGH - 15 Files)
*Priority: HIGH - Real-time Communication Critical*

### 2.1 WebSocket Integration Tests
**Business Impact**: Enables real-time communication for all user tiers

```bash
# High-priority WebSocket files:
tests/integration/websocket/test_websocket_user_isolation_1116.py (5 occurrences)
tests/integration/test_agent_websocket_integration_comprehensive.py (6 occurrences)
tests/integration/agent_websocket_coordination/test_agent_factory_websocket_bridge_integration.py (3 occurrences)
tests/integration/test_websocket_agent_communication_integration.py (1 occurrence)
tests/integration/test_websocket_agent_message_flow.py (1 occurrence)
```

### 2.2 WebSocket Response Tests
```bash
tests/integration/agent_responses/test_websocket_events_integration.py (1 occurrence)
tests/integration/agent_responses/test_response_quality_integration.py (1 occurrence)
tests/integration/agent_responses/test_agent_state_management_integration.py (1 occurrence)
tests/integration/agent_responses/test_agent_execution_integration.py (1 occurrence)
```

---

## Phase 3: Multi-User & Agent Factory Tests (MEDIUM - 12 Files)
*Priority: MEDIUM - User Isolation Critical*

### 3.1 Multi-User Isolation Tests
```bash
tests/integration/test_multi_user_message_isolation.py (1 occurrence)
tests/integration/test_supervisor_agent_multi_user_isolation.py (4 occurrences)
tests/integration/agent_factory/test_multi_user_chat_isolation_1116.py (7 occurrences)
tests/integration/agents/test_agent_factory_user_isolation_integration.py (3 occurrences)
tests/integration/agents/test_agent_factory_user_isolation_compliance.py (4 occurrences)
```

### 3.2 Agent Factory Tests
```bash
tests/integration/agents/test_issue_1142_golden_path_startup_contamination.py (10 occurrences)
tests/integration/test_supervisor_ssot_system_conflicts.py (2 occurrences)
tests/integration/test_agent_message_error_recovery.py (1 occurrence)
```

---

## Phase 4: Backend Core Infrastructure (MEDIUM - 8 Files)
*Priority: MEDIUM - Core System Stability*

### 4.1 Backend Core Tests
```bash
netra_backend/tests/integration/golden_path/test_agent_factory_real_database_integration.py (1 occurrence)
netra_backend/tests/integration/test_agent_execution_tool_pipeline_integration.py (16 occurrences)
netra_backend/tests/integration/test_agent_execution_pipeline_integration.py (3 occurrences)
netra_backend/tests/integration/startup/test_services_phase_comprehensive.py (2 occurrences)
```

### 4.2 Backend Unit Tests
```bash
netra_backend/tests/unit/agents/supervisor/test_agent_instance_factory_comprehensive.py (7 occurrences)
netra_backend/tests/unit/agents/supervisor/test_factory_pattern_user_isolation.py (2 occurrences)
netra_backend/tests/unit/agents/test_ssot_user_contamination_violations.py (3 occurrences)
netra_backend/tests/unit/agents/test_ssot_factory_singleton_violations.py (6 occurrences)
```

---

## Phase 5: Unit Tests & Production Code (LOW - 7 Files)
*Priority: LOW - Test Infrastructure*

### 5.1 Remaining Unit Tests
```bash
tests/unit/agents/test_ssot_migration_validation_1142.py (3 occurrences)
tests/unit/agents/test_singleton_to_factory_migration_validation.py (4 occurrences)
tests/unit/agents/test_agent_instance_factory_user_isolation.py (11 occurrences)
tests/unit/agents/test_agent_instance_factory_ssot_violations.py (6 occurrences)
tests/unit/agents/test_issue_1142_startup_singleton_contamination.py (19 occurrences)
tests/unit/agents/test_agent_instance_factory_singleton_violations_1116.py (10 occurrences)
tests/unit/test_agent_instance_factory_singleton_vulnerability.py (7 occurrences)
```

### 5.2 Production Code (CRITICAL)
```bash
netra_backend/app/agents/supervisor/agent_instance_factory.py (4 occurrences)
# NOTE: These may be in deprecated function definitions that should be removed
```

---

## Phase 6: Cleanup Operations (CLEANUP)
*Priority: CLEANUP - Repository Hygiene*

### 6.1 Backup File Cleanup
Remove all `.backup` files containing deprecated patterns:
```bash
# Pattern: *.backup_await_fix, *.backup.20250915_*, *.backup.20250914_*
# Total: ~80 backup files identified
```

### 6.2 Example & Documentation
```bash
examples/agent_instance_factory_usage.py (2 occurrences)
scripts/load_test_isolation.py (1 occurrence)
# Update to use new patterns as examples
```

---

## Implementation Strategy

### Step-by-Step Execution Commands

#### Phase 1: Golden Path Migration
```bash
# 1. Create migration script
cat > migrate_golden_path.py << 'EOF'
import os
import re

def migrate_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Add required imports if not present
    if 'from netra_backend.app.services.user_execution_context import UserExecutionContext' not in content:
        # Add import after existing imports
        import_pattern = r'(from netra_backend\.app\..*?\n)'
        if re.search(import_pattern, content):
            content = re.sub(
                r'(from netra_backend\.app\..*?\n)',
                r'\1from netra_backend.app.services.user_execution_context import UserExecutionContext\n',
                content, count=1
            )

    if 'from netra_backend.app.agents.supervisor.agent_instance_factory import create_agent_instance_factory' not in content:
        content = re.sub(
            r'(from netra_backend\.app\.services\.user_execution_context import UserExecutionContext\n)',
            r'\1from netra_backend.app.agents.supervisor.agent_instance_factory import create_agent_instance_factory\n',
            content
        )

    # Replace deprecated calls with SSOT pattern
    # Pattern 1: Simple assignment
    content = re.sub(
        r'(\s+)factory = get_agent_instance_factory\(\)',
        r'''\1# Create proper user context for isolation
\1user_context = UserExecutionContext(
\1    user_id="test_user_golden_path",
\1    thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
\1    run_id=f"test_run_{uuid.uuid4().hex[:8]}",
\1    request_id=f"test_req_{uuid.uuid4().hex[:8]}"
\1)
\1factory = create_agent_instance_factory(user_context)''',
        content
    )

    # Add uuid import if needed
    if 'import uuid' not in content and 'uuid.uuid4()' in content:
        content = re.sub(r'(import .*?\n)', r'\1import uuid\n', content, count=1)

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"Migrated: {filepath}")

# Golden Path files
golden_path_files = [
    "tests/integration/agent_golden_path/test_websocket_event_sequence_integration.py",
    "tests/integration/agent_golden_path/test_multi_user_message_isolation_integration.py",
    "tests/integration/agent_golden_path/test_multi_user_concurrent_message_processing.py",
    "tests/integration/agent_golden_path/test_message_processing_pipeline.py",
    "tests/integration/agent_golden_path/test_message_pipeline_integration.py",
    "tests/integration/agent_golden_path/test_golden_path_performance_integration.py",
    "tests/integration/agent_golden_path/test_agent_websocket_events_comprehensive.py",
    "tests/integration/agent_golden_path/test_agent_response_quality_integration.py",
    "tests/integration/agent_golden_path/test_agent_message_pipeline_end_to_end.py",
    "tests/integration/test_agent_golden_path_messages.py",
    "tests/integration/test_agent_execution_business_value.py",
    "tests/integration/test_agent_execution_flow_integration.py",
    "tests/e2e/test_golden_path_multi_user_concurrent.py"
]

for filepath in golden_path_files:
    if os.path.exists(filepath):
        migrate_file(filepath)
EOF

python migrate_golden_path.py
```

#### Phase 2: WebSocket Migration
```bash
# Similar script for WebSocket files
# Focus on files with multiple occurrences first
```

#### Phase 3: Validation After Each Phase
```bash
# After each phase, run validation
pytest tests/integration/agent_golden_path/ -v --tb=short
pytest tests/integration/test_agent_golden_path_messages.py -v
pytest tests/integration/test_agent_execution_business_value.py -v
```

### Advanced Migration Patterns

#### Pattern 1: Simple Assignment
```python
# Before:
factory = get_agent_instance_factory()

# After:
user_context = UserExecutionContext(
    user_id="test_user_context",
    thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
    run_id=f"test_run_{uuid.uuid4().hex[:8]}",
    request_id=f"test_req_{uuid.uuid4().hex[:8]}"
)
factory = create_agent_instance_factory(user_context)
```

#### Pattern 2: In Test Setup
```python
# Before:
def setup_method(self):
    self.factory = get_agent_instance_factory()

# After:
def setup_method(self):
    self.user_context = UserExecutionContext(
        user_id=f"test_user_{self.__class__.__name__}",
        thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
        run_id=f"test_run_{uuid.uuid4().hex[:8]}",
        request_id=f"test_req_{uuid.uuid4().hex[:8]}"
    )
    self.factory = create_agent_instance_factory(self.user_context)
```

#### Pattern 3: Multiple Users (Isolation Tests)
```python
# Before:
factory1 = get_agent_instance_factory()
factory2 = get_agent_instance_factory()

# After:
user1_context = UserExecutionContext(
    user_id="isolation_user_1",
    thread_id=f"user1_thread_{uuid.uuid4().hex[:8]}",
    run_id=f"user1_run_{uuid.uuid4().hex[:8]}",
    request_id=f"user1_req_{uuid.uuid4().hex[:8]}"
)
user2_context = UserExecutionContext(
    user_id="isolation_user_2",
    thread_id=f"user2_thread_{uuid.uuid4().hex[:8]}",
    run_id=f"user2_run_{uuid.uuid4().hex[:8]}",
    request_id=f"user2_req_{uuid.uuid4().hex[:8]}"
)
factory1 = create_agent_instance_factory(user1_context)
factory2 = create_agent_instance_factory(user2_context)
```

---

## Risk Mitigation

### 1. Incremental Testing
- Migrate and test each phase separately
- Run full test suite after each phase
- Monitor for any regression in existing functionality

### 2. Rollback Strategy
- Create git branch for each phase
- Keep backup files until migration is validated
- Document any test failures and resolutions

### 3. Edge Case Handling
```python
# Handle cases where UserExecutionContext might not be available
try:
    # Preferred SSOT pattern
    factory = create_agent_instance_factory(user_context)
except NameError:
    # Fallback for legacy tests (temporary)
    user_context = UserExecutionContext(
        user_id="fallback_user",
        thread_id=f"fallback_thread_{uuid.uuid4().hex[:8]}",
        run_id=f"fallback_run_{uuid.uuid4().hex[:8]}",
        request_id=f"fallback_req_{uuid.uuid4().hex[:8]}"
    )
    factory = create_agent_instance_factory(user_context)
```

---

## Success Criteria

### Phase Completion Validation
1. **Zero deprecated calls remaining**: `grep -r "get_agent_instance_factory()" --include="*.py" .` returns no results
2. **All tests passing**: Full pytest suite passes without failures
3. **Golden Path protected**: All golden path integration tests pass
4. **User isolation validated**: Multi-user tests demonstrate proper isolation

### Business Value Delivered
- ✅ $500K+ ARR Golden Path fully protected
- ✅ Multi-user production deployment unblocked
- ✅ Enterprise compliance requirements met
- ✅ User isolation vulnerabilities eliminated

---

## Execution Timeline

| Phase | Duration | Files | Priority | Business Impact |
|-------|----------|-------|----------|-----------------|
| Phase 1 | 2-3 hours | 13 files | CRITICAL | $500K+ ARR Protection |
| Phase 2 | 3-4 hours | 15 files | HIGH | Real-time Communication |
| Phase 3 | 2-3 hours | 12 files | MEDIUM | User Isolation |
| Phase 4 | 4-5 hours | 8 files | MEDIUM | Core Stability |
| Phase 5 | 2-3 hours | 7 files | LOW | Test Infrastructure |
| Phase 6 | 1-2 hours | Cleanup | CLEANUP | Repository Hygiene |

**Total Estimated Time**: 14-20 hours
**Business Risk Window**: Minimized by phased approach with immediate Golden Path protection

---

## Monitoring & Validation

### Real-time Validation Commands
```bash
# Check progress
echo "Remaining deprecated calls:"
grep -r "get_agent_instance_factory()" --include="*.py" . | wc -l

# Validate SSOT usage
echo "SSOT pattern usage:"
grep -r "create_agent_instance_factory(" --include="*.py" . | wc -l

# Test golden path
pytest tests/integration/agent_golden_path/ -x --tb=short

# Test user isolation
pytest tests/integration/test_supervisor_agent_multi_user_isolation.py -v
```

This comprehensive plan systematically addresses all 181 deprecated calls while prioritizing business-critical components and maintaining system stability throughout the migration process.