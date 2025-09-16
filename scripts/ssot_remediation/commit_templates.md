# SSOT Remediation Atomic Commit Templates

> **Purpose:** Standardized commit templates for SSOT remediation to ensure consistent, reviewable, and rollback-friendly changes.
>
> **Usage:** Copy and modify these templates for each atomic change during SSOT remediation phases.

---

## 🎯 COMMIT TEMPLATE PRINCIPLES

1. **Atomic Changes:** Each commit addresses one specific violation category
2. **Clear Purpose:** Commit message explains WHY the change improves SSOT compliance
3. **Rollback Ready:** Each commit can be safely reverted without breaking dependencies
4. **Business Context:** Links remediation to business value ($500K+ ARR protection)
5. **Validation Ready:** Each commit includes validation approach

---

## 📋 PHASE 2 ATOMIC COMMIT TEMPLATES

### **Template 1: Agent Mock Consolidation**
```
refactor: consolidate Agent mock implementations to SSotMockFactory

**SSOT Compliance Improvement:**
- Replace duplicate MockAgent class definitions with unified SSotMockFactory.create_mock_agent()
- Remove 8+ duplicate Agent mock implementations from test files
- Standardize agent mock creation patterns across test infrastructure
- Add SSotMockFactory imports where needed

**Files Changed:**
- test_framework/ssot/mock_factory.py (enhanced with agent mock creation)
- tests/**/*agent*.py (consolidated mock usage)

**Validation:**
- All agent-related tests continue passing
- Golden Path WebSocket agent events unaffected
- Mock creation patterns now use SSOT factory

**Business Impact:**
- Reduces technical debt in test infrastructure
- Improves test maintainability and consistency
- Protects $500K+ ARR by maintaining stable test coverage

**Related:** Issue #1076 SSOT Compliance - Mock Consolidation Phase

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### **Template 2: Manager Mock Consolidation**
```
refactor: consolidate Manager mock implementations to SSotMockFactory

**SSOT Compliance Improvement:**
- Replace duplicate MockWebSocketManager, MockConnectionManager class definitions
- Use unified SSotMockFactory.create_mock_websocket_manager() for all manager mocks
- Remove 6+ duplicate Manager mock implementations from test files
- Standardize WebSocket manager mock patterns across test infrastructure

**Files Changed:**
- test_framework/ssot/mock_factory.py (enhanced with manager mock creation)
- tests/**/*manager*.py (consolidated mock usage)
- tests/**/*websocket*.py (unified WebSocket mock patterns)

**Validation:**
- All WebSocket-related tests continue passing
- Golden Path WebSocket functionality unaffected
- Manager mock creation patterns now use SSOT factory
- WebSocket compliance tests validate SSOT patterns

**Business Impact:**
- Ensures WebSocket reliability for chat functionality (90% of platform value)
- Improves test infrastructure consistency
- Maintains Golden Path protection during test execution

**Related:** Issue #1076 SSOT Compliance - Manager Mock Consolidation

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### **Template 3: Service Mock Consolidation**
```
refactor: consolidate Service mock implementations to SSotMockFactory

**SSOT Compliance Improvement:**
- Replace duplicate MockAuthService, MockLLMService, MockDatabaseService class definitions
- Use unified SSotMockFactory.create_mock_service() for all service mocks
- Remove 5+ duplicate Service mock implementations from test files
- Standardize service mock patterns across test infrastructure

**Files Changed:**
- test_framework/ssot/mock_factory.py (enhanced with service mock creation)
- tests/**/*service*.py (consolidated mock usage)
- tests/**/*auth*.py, tests/**/*llm*.py, tests/**/*database*.py (unified patterns)

**Validation:**
- All service integration tests continue passing
- Authentication flow tests maintain functionality
- Database connectivity tests preserve behavior
- Service mock creation patterns now use SSOT factory

**Business Impact:**
- Maintains authentication reliability (security critical)
- Preserves database integration stability
- Improves service mock consistency across test suite

**Related:** Issue #1076 SSOT Compliance - Service Mock Consolidation

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### **Template 4: Import Path Standardization**
```
refactor: standardize SSOT import patterns in test framework

**SSOT Compliance Improvement:**
- Replace try/except import fallback patterns with direct SSOT imports
- Use canonical import paths for WebSocket, Agent, and Auth components
- Remove legacy import compatibility patterns that bypass SSOT architecture
- Ensure consistent SSOT import usage across test infrastructure

**Import Standardizations:**
- WebSocket: Use `from netra_backend.app.websocket_core.unified_manager import get_websocket_manager`
- Agents: Use `from netra_backend.app.agents.registry import get_agent_registry`
- Auth: Use `from netra_backend.app.auth_integration.auth import get_auth_service`

**Files Changed:**
- tests/**/*.py (standardized import patterns)
- test_framework/**/*.py (removed fallback imports)

**Validation:**
- All tests maintain functionality with direct SSOT imports
- No test failures due to import changes
- Import patterns now align with SSOT architecture
- Faster test execution due to eliminated import error handling

**Business Impact:**
- Improves test reliability by removing import uncertainty
- Faster test execution supports rapid development cycle
- Ensures test infrastructure follows production SSOT patterns

**Related:** Issue #1076 SSOT Compliance - Import Standardization

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### **Template 5: Environment Access Standardization**
```
refactor: replace os.environ with IsolatedEnvironment in test framework

**SSOT Compliance Improvement:**
- Replace all os.environ.get() calls with IsolatedEnvironment().get()
- Replace all os.getenv() calls with unified environment access pattern
- Add IsolatedEnvironment imports to test framework modules
- Ensure consistent SSOT environment management across test infrastructure

**Environment Access Standardizations:**
- `os.environ.get("VAR")` → `IsolatedEnvironment().get("VAR")`
- `os.getenv("VAR", default)` → `IsolatedEnvironment().get("VAR", default)`
- Direct `os.environ["VAR"]` → `IsolatedEnvironment().get("VAR")`

**Files Changed:**
- test_framework/**/*.py (unified environment access)
- tests/**/*.py (standardized environment variable usage)

**Validation:**
- All tests maintain functionality with IsolatedEnvironment
- Environment variable access patterns now use SSOT approach
- Test isolation improved through consistent environment management
- No test failures due to environment access changes

**Business Impact:**
- Improves test isolation and reliability
- Ensures test environment management follows production patterns
- Reduces environment-related test flakiness
- Supports consistent configuration across test execution

**Related:** Issue #1076 SSOT Compliance - Environment Access Standardization

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 🔧 COMMIT WORKFLOW TEMPLATE

### **Pre-Commit Validation Script**
```bash
#!/bin/bash
# Pre-commit validation for SSOT remediation changes

echo "🔍 Running pre-commit SSOT validation..."

# 1. Validate Golden Path still works
echo "⏳ Validating Golden Path functionality..."
python tests/mission_critical/test_websocket_agent_events_suite.py || {
    echo "❌ COMMIT BLOCKED: Golden Path WebSocket events failing"
    exit 1
}

# 2. Check SSOT compliance score
echo "⏳ Checking SSOT compliance score..."
python scripts/check_architecture_compliance.py | grep "Compliance Score" || {
    echo "❌ COMMIT BLOCKED: Cannot determine compliance score"
    exit 1
}

# 3. Verify production systems unaffected
echo "⏳ Verifying production system integrity..."
python scripts/check_architecture_compliance.py --production-only | grep "100.0% compliant" || {
    echo "❌ COMMIT BLOCKED: Production system compliance affected"
    exit 1
}

# 4. Quick test infrastructure health check
echo "⏳ Running critical test health check..."
python tests/unified_test_runner.py --categories mission_critical --fast-fail --timeout 120 || {
    echo "❌ COMMIT BLOCKED: Mission critical tests failing"
    exit 1
}

echo "✅ Pre-commit validation passed - safe to commit"
```

### **Post-Commit Validation Script**
```bash
#!/bin/bash
# Post-commit validation for SSOT remediation changes

echo "🔍 Running post-commit SSOT validation..."

# Run comprehensive validation
python scripts/ssot_remediation/validation_suite.py phase2 golden_path compliance_score production_integrity

if [ $? -eq 0 ]; then
    echo "✅ Post-commit validation passed"
else
    echo "❌ Post-commit validation failed - consider rollback"
    echo "💡 Rollback command: git reset --hard HEAD~1"
    exit 1
fi
```

---

## 📊 CHANGE IMPACT GROUPINGS

### **Group 1: Mock Infrastructure Changes (Low Risk)**
- **Files:** `test_framework/ssot/mock_factory.py`, test files with mock classes
- **Risk Level:** LOW - Test infrastructure only
- **Dependencies:** None (self-contained)
- **Rollback Impact:** Minimal - only affects test mock creation

### **Group 2: Import Pattern Changes (Low Risk)**
- **Files:** Test files with import statements
- **Risk Level:** LOW - Import path standardization only
- **Dependencies:** Group 1 (mock factory should be enhanced first)
- **Rollback Impact:** Minimal - reverts to try/except import patterns

### **Group 3: Environment Access Changes (Low Risk)**
- **Files:** `test_framework/**/*.py`, test configuration files
- **Risk Level:** LOW - Environment access standardization only
- **Dependencies:** None (independent change)
- **Rollback Impact:** Minimal - reverts to direct os.environ access

### **Group 4: Validation and Documentation (Minimal Risk)**
- **Files:** Documentation, validation scripts, reports
- **Risk Level:** MINIMAL - No production code impact
- **Dependencies:** All other groups (validates their changes)
- **Rollback Impact:** None - documentation and tooling only

---

## 🚨 EMERGENCY ROLLBACK PROCEDURES

### **Single Commit Rollback**
```bash
# Rollback last commit if validation fails
git reset --hard HEAD~1

# Verify Golden Path still works
python tests/mission_critical/test_websocket_agent_events_suite.py

# Check compliance score returned to baseline
python scripts/check_architecture_compliance.py
```

### **Full Phase Rollback**
```bash
# Rollback entire Phase 2 if major issues detected
git log --oneline -10  # Find the last commit before Phase 2

# Reset to pre-Phase 2 state (replace COMMIT_HASH with actual hash)
git reset --hard COMMIT_HASH

# Validate rollback successful
python scripts/ssot_remediation/validation_suite.py phase1
```

### **Rollback Decision Matrix**
- **Golden Path Failure:** IMMEDIATE ROLLBACK (CRITICAL)
- **Compliance Score Decrease:** INVESTIGATE → ROLLBACK if severe
- **Production Violation Detected:** IMMEDIATE ROLLBACK (CRITICAL)
- **Test Infrastructure Issues:** INVESTIGATE → ROLLBACK if blocking development

---

## ✅ COMMIT VALIDATION CHECKLIST

Before each commit:
- [ ] Pre-commit validation script passes
- [ ] Golden Path WebSocket events working
- [ ] Production systems maintain 100% compliance
- [ ] Compliance score improved or maintained
- [ ] No new test failures introduced
- [ ] Commit message follows template format
- [ ] Changes are atomic and focused
- [ ] Rollback procedure identified

After each commit:
- [ ] Post-commit validation script passes
- [ ] Document compliance score change
- [ ] Update remediation progress tracking
- [ ] Verify next atomic change is safe to proceed

---

**Usage Instructions:**
1. Copy appropriate template for your atomic change
2. Customize file paths and specific details
3. Run pre-commit validation script
4. Make commit with standardized message
5. Run post-commit validation
6. Update progress tracking