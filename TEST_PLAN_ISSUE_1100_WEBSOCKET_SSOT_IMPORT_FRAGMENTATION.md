# Test Plan: Issue #1100 WebSocket SSOT Import Fragmentation

**Created:** 2025-09-14  
**Priority:** P1 (Reclassified from P0)  
**Business Impact:** Import fragmentation cleanup protecting $500K+ ARR WebSocket infrastructure  
**Target Completion:** 4-7 hours estimated effort

## 🎯 Executive Summary

This test plan validates the elimination of deprecated `websocket_manager_factory` imports across 25+ files and ensures proper SSOT consolidation for WebSocket management. Tests are designed to **FAIL initially** with current dual pattern code and **PASS after** SSOT import migration.

**Key Requirements:**
- Validate elimination of deprecated imports in 25+ identified files
- Ensure consistent WebSocket event structure (fixing current 3 test failures)
- Protect Golden Path WebSocket functionality during migration
- Use real services (no mocks) per claude.md requirements

## 📊 Current System State Analysis

### Working Components ✅
- WebSocket connections establish successfully to staging
- Mission critical tests show 92.9% pass rate (39/42 tests)
- Golden Path user flow operational
- Basic event delivery functional

### Issues Requiring Testing ⚠️
- **Import Fragmentation:** 25+ files using deprecated `websocket_manager_factory` imports
- **Event Structure Failures:** 3/42 mission critical tests failing on event validation
- **SSOT Violations:** Multiple WebSocket manager implementations active simultaneously
- **Race Conditions:** Factory compatibility layer creating conflicts

### Files Requiring Import Migration (Priority Order)
1. `netra_backend/app/agents/supervisor/agent_instance_factory.py` - Agent execution core
2. `netra_backend/app/agents/tool_executor_factory.py` - Tool execution pipeline  
3. `netra_backend/app/services/agent_websocket_bridge.py` - WebSocket-Agent integration
4. `netra_backend/app/websocket_core/migration_adapter.py` - Migration compatibility
5. `netra_backend/app/core/supervisor_factory.py` - Supervisor instantiation
6. 20+ additional files identified in project scan

## 🧪 Test Categories and Strategy

### 1. Unit Tests - Import Pattern Detection (Should FAIL initially)
**Purpose:** Validate elimination of deprecated import patterns  
**Infrastructure:** None required  
**Execution:** Fast feedback, no Docker required

### 2. Integration Tests - SSOT Compliance Validation  
**Purpose:** Ensure single WebSocket manager pattern consistency  
**Infrastructure:** Local services (PostgreSQL, Redis)  
**Execution:** Real services validation

### 3. E2E Tests - Golden Path Event Validation
**Purpose:** Protect business value during import migration  
**Infrastructure:** Full staging environment (no Docker locally)  
**Execution:** Real WebSocket connections, real agents

## 📋 Detailed Test Plan

### Phase 1: Import Pattern Detection Tests (Unit)

#### Test File: `/tests/unit/websocket_ssot/test_issue_1100_deprecated_import_elimination.py`

**Purpose:** Detect and validate elimination of deprecated imports across 25+ files

```python
"""
Test Deprecated Import Pattern Elimination - Issue #1100

Business Value Justification (BVJ):
- Segment: Platform/Internal Infrastructure
- Business Goal: Eliminate SSOT violations threatening WebSocket reliability
- Value Impact: Prevents race conditions affecting $500K+ ARR chat functionality
- Strategic Impact: Ensures long-term maintainability of WebSocket infrastructure
"""

class TestDeprecatedImportElimination:
    """Test elimination of deprecated websocket_manager_factory imports."""
    
    def test_no_deprecated_websocket_factory_imports_in_production_code(self):
        """SHOULD FAIL: Detect deprecated websocket_manager_factory imports in production files."""
        # This test should FAIL initially with current fragmented imports
        # PASS after: All imports migrated to SSOT patterns
    
    def test_agent_factory_files_use_ssot_imports(self):
        """SHOULD FAIL: Validate agent factory files use SSOT WebSocket imports."""
        # Target files: agent_instance_factory.py, tool_executor_factory.py
    
    def test_websocket_bridge_uses_canonical_import(self):
        """SHOULD FAIL: Validate agent_websocket_bridge uses canonical imports."""
        # Target: netra_backend/app/services/agent_websocket_bridge.py
    
    def test_migration_adapter_elimination(self):
        """SHOULD FAIL: Validate migration_adapter.py removed or uses SSOT."""
        # Target: netra_backend/app/websocket_core/migration_adapter.py
```

#### Test File: `/tests/unit/websocket_ssot/test_issue_1100_ssot_compliance_validation.py`

**Purpose:** Validate SSOT compliance patterns and single implementation usage

```python
class TestSSotComplianceValidation:
    """Test SSOT compliance for WebSocket manager implementations."""
    
    def test_single_websocket_manager_implementation_active(self):
        """SHOULD FAIL: Ensure only one WebSocket manager implementation active."""
        # This test should FAIL with current dual pattern code
        # PASS after: Factory elimination complete
    
    def test_websocket_manager_import_path_consistency(self):
        """SHOULD FAIL: Validate consistent import paths across all modules."""
        # Check for consistent use of canonical import paths
    
    def test_no_factory_pattern_in_websocket_instantiation(self):
        """SHOULD FAIL: Ensure no factory pattern usage for WebSocket creation."""
        # Validate direct WebSocketManager instantiation
```

### Phase 2: Integration Tests - WebSocket Manager Consistency

#### Test File: `/tests/integration/websocket_ssot/test_issue_1100_websocket_manager_integration.py`

**Purpose:** Validate WebSocket manager instantiation consistency with real services

```python
"""
Test WebSocket Manager Integration Consistency - Issue #1100

Uses real PostgreSQL and Redis services to validate WebSocket manager behavior
consistency across different instantiation patterns.
"""

class TestWebSocketManagerIntegration:
    """Test WebSocket manager integration with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_consistent_behavior(self, real_services_fixture):
        """SHOULD FAIL: Validate consistent WebSocket manager behavior across patterns."""
        # This test should FAIL if multiple implementations create inconsistencies
        # PASS after: Single SSOT implementation ensures consistency
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_ssot_integration(self, real_services_fixture):
        """SHOULD FAIL: Test agent WebSocket bridge uses SSOT WebSocket manager."""
        # Validate AgentWebSocketBridge integration consistency
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_structure_consistency(self, real_services_fixture):
        """SHOULD FAIL: Fix current event structure validation failures."""
        # Address the 3/42 mission critical test failures
        # Validate all 5 required events: agent_started, agent_thinking, 
        # tool_executing, tool_completed, agent_completed
```

### Phase 3: E2E Tests - Golden Path Protection

#### Test File: `/tests/e2e/websocket_ssot/test_issue_1100_golden_path_protection.py`

**Purpose:** Protect Golden Path WebSocket functionality during SSOT migration

```python
"""
Test Golden Path WebSocket Protection - Issue #1100

Business Value: Protect $500K+ ARR WebSocket functionality during import migration.
Uses staging environment for complete end-to-end validation.
"""

class TestGoldenPathWebSocketProtection:
    """Test Golden Path WebSocket functionality protection."""
    
    @pytest.mark.e2e
    @pytest.mark.staging_required
    async def test_golden_path_websocket_events_during_migration(self, staging_services):
        """SHOULD PASS: Golden Path WebSocket events continue working during migration."""
        # This test should PASS throughout migration process
        # Validates business continuity during import updates
    
    @pytest.mark.e2e
    @pytest.mark.staging_required
    async def test_agent_execution_websocket_integration_ssot(self, staging_services):
        """SHOULD FAIL then PASS: Agent execution WebSocket integration via SSOT."""
        # FAIL: With fragmented imports causing inconsistencies
        # PASS: After SSOT consolidation ensures reliable integration
    
    @pytest.mark.e2e
    @pytest.mark.staging_required
    async def test_multi_user_websocket_isolation_post_migration(self, staging_services):
        """SHOULD FAIL then PASS: Multi-user WebSocket isolation after SSOT migration."""
        # FAIL: If factory patterns cause user isolation violations
        # PASS: After SSOT ensures proper user context isolation
```

### Phase 4: Mission Critical Validation

#### Test File: `/tests/mission_critical/test_issue_1100_websocket_ssot_mission_critical.py`

**Purpose:** Mission critical validation of WebSocket SSOT consolidation

```python
"""
Mission Critical WebSocket SSOT Validation - Issue #1100

CRITICAL: These tests MUST pass before deployment.
Validates business-critical WebSocket functionality protection.
"""

class TestWebSocketSSotMissionCritical:
    """Mission critical WebSocket SSOT validation."""
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_all_websocket_events_sent_post_ssot_migration(self):
        """MUST PASS: All 5 WebSocket events sent after SSOT migration."""
        # This test MUST pass or deployment is blocked
        # Validates: agent_started, agent_thinking, tool_executing, 
        #           tool_completed, agent_completed
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip  
    async def test_websocket_manager_ssot_violation_detection(self):
        """MUST PASS: No SSOT violations detected in WebSocket management."""
        # Ensures single source of truth compliance
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_business_value_protection_during_migration(self):
        """MUST PASS: Business value protected during import migration."""
        # Chat functionality continues operating during migration
```

## 🔧 Test Implementation Details

### Test Infrastructure Requirements

#### Real Services Configuration
```python
# test_framework/real_services_test_fixtures.py
# Uses existing SSOT test infrastructure per claude.md requirements

from test_framework.real_services_test_fixtures import (
    real_services_fixture,  # Full real services stack
    real_db_fixture,        # PostgreSQL only
    real_redis_fixture,     # Redis only
)

# Staging environment for E2E tests
from test_framework.staging_environment_fixtures import (
    staging_services_fixture,  # Real staging environment
    staging_websocket_client,  # Staging WebSocket client
)
```

#### Test Execution Commands
```bash
# Unit Tests - Fast feedback on import patterns
python tests/unified_test_runner.py --category unit --pattern "*issue_1100*"

# Integration Tests - Real services validation  
python tests/unified_test_runner.py --category integration --pattern "*issue_1100*" --real-services

# E2E Tests - Staging environment validation
python tests/unified_test_runner.py --category e2e --pattern "*issue_1100*" --staging

# Mission Critical - Complete validation
python tests/mission_critical/test_issue_1100_websocket_ssot_mission_critical.py
```

### Expected Test Progression

#### Phase 1: Pre-Migration (Tests Should FAIL)
- ❌ `test_no_deprecated_websocket_factory_imports_in_production_code` - Detects 25+ deprecated imports
- ❌ `test_single_websocket_manager_implementation_active` - Multiple implementations detected
- ❌ `test_websocket_event_structure_consistency` - Event structure validation failures
- ❌ `test_agent_execution_websocket_integration_ssot` - Inconsistent integration patterns

#### Phase 2: During Migration (Mixed Results)
- ⚠️ Gradual improvement as imports updated file by file
- 🔄 Mission critical tests continue passing (business continuity)
- 📊 Progress tracking via test pass/fail ratios

#### Phase 3: Post-Migration (Tests Should PASS)
- ✅ All deprecated import detection tests pass
- ✅ SSOT compliance validation tests pass  
- ✅ Event structure consistency validated
- ✅ Mission critical tests maintain 100% pass rate

## 📈 Success Metrics and Validation

### Test Success Criteria
1. **Import Pattern Tests:** 100% pass rate after migration (currently failing)
2. **SSOT Compliance Tests:** Single implementation validation passes
3. **Event Structure Tests:** Fixes current 3/42 mission critical test failures  
4. **Golden Path Tests:** Maintains business functionality during migration
5. **Mission Critical Suite:** 100% pass rate maintained throughout

### Business Value Validation
- **WebSocket Connections:** Continue establishing successfully
- **Event Delivery:** All 5 required events delivered consistently  
- **User Isolation:** Multi-user WebSocket functionality preserved
- **Performance:** No regression in WebSocket response times
- **Stability:** No increase in connection drop rates

### Technical Debt Elimination
- **Import Fragmentation:** 25+ deprecated imports eliminated
- **SSOT Violations:** Single WebSocket manager implementation
- **Code Maintenance:** Simplified import patterns across codebase
- **Documentation:** Updated patterns reflect SSOT architecture

## 🎯 Risk Mitigation

### Business Continuity Protection
- Golden Path tests ensure WebSocket functionality during migration
- Incremental migration allows rollback at any stage
- Mission critical tests validate no regression in core functionality
- Staging environment validation before production deployment

### Technical Risk Management
- Real service testing catches integration issues early
- Event structure validation prevents runtime failures  
- User isolation testing prevents security vulnerabilities
- Performance monitoring detects regressions immediately

## 📋 Action Items for Test Implementation

### Immediate (Day 1)
1. ✅ Create test plan document (current task)
2. 🔄 Implement Phase 1 unit tests for import pattern detection
3. 🔄 Create Phase 2 integration tests for SSOT compliance
4. 📋 Set up test execution infrastructure

### Short Term (Days 2-3)
1. 📋 Implement Phase 3 E2E tests for Golden Path protection
2. 📋 Create Phase 4 mission critical validation tests
3. 📋 Execute initial test runs to confirm failure states
4. 📋 Document test execution results and failure patterns

### Migration Support (Days 4-7)
1. 📋 Execute tests continuously during import migration
2. 📋 Track progress via test pass/fail ratios
3. 📋 Validate business continuity throughout process
4. 📋 Execute final validation and issue closure

## 📖 References and Documentation

### Claude.md Compliance
- Tests use real services (no mocks) per requirements
- Follow SSOT test infrastructure patterns
- Use existing unified test runner framework
- Implement proper business value justification

### Related Issues and Documentation
- Issue #824: WebSocket Manager SSOT Consolidation (parent issue)
- Issue #989: WebSocket Factory Deprecation (related)
- `reports/testing/TEST_CREATION_GUIDE.md` - Test methodology
- `tests/unified_test_runner.py` - Execution framework
- `MASTER_WIP_STATUS.md` - System status context

### Business Context
- Golden Path user flow protection priority
- $500K+ ARR WebSocket infrastructure dependency
- P1 priority for technical debt elimination
- 4-7 hour estimated completion timeline

---

**Test Plan Status:** ✅ **READY FOR IMPLEMENTATION**  
**Next Action:** Begin Phase 1 unit test implementation for import pattern detection  
**Success Measure:** All tests fail initially, pass after SSOT migration complete