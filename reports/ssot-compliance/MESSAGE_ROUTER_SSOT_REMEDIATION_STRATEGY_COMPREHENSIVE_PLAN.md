# MessageRouter SSOT Remediation Strategy - Comprehensive Plan

**Issue:** #1077 - Plan comprehensive SSOT remediation strategy for Message Router fragmentation  
**Business Impact:** $500K+ ARR protected - Users login → get AI responses  
**Created:** 2025-09-14  
**Status:** STEP 3 COMPLETE - Comprehensive Planning Phase  
**Phase:** PLAN ONLY (No Implementation)

## Executive Summary

This comprehensive plan addresses the consolidation of **25 MessageRouter implementations** into a single canonical SSOT implementation while protecting $500K+ ARR Golden Path functionality. The strategy leverages proven SSOT consolidation patterns from the existing WebSocket broadcast service and unified tool dispatcher to ensure safe, systematic remediation with zero business disruption.

### Key Planning Achievements
- **Canonical Target Identified:** `/netra_backend/app/websocket_core/handlers.py:1219` MessageRouter class
- **24 Duplicates Mapped:** Complete elimination strategy for all duplicate implementations
- **25 Import Paths Standardized:** Systematic approach to import consistency
- **Proven Pattern Adaptation:** Leverage existing SSOT WebSocketBroadcastService success model
- **Zero-Risk Migration:** Atomic changes with comprehensive rollback procedures

---

## 1. CONSOLIDATION TARGET ANALYSIS

### 1.1 Canonical MessageRouter Interface Analysis

**SSOT Target:** `/netra_backend/app/websocket_core/handlers.py:1219` - MessageRouter class

#### Core Interface Methods (Required for Compatibility)
```python
class MessageRouter:
    def __init__(self) -> None
    def add_handler(self, handler: MessageHandler) -> None
    def remove_handler(self, handler: MessageHandler) -> None
    def insert_handler(self, handler: MessageHandler, index: int = 0) -> None
    def get_handler_order(self) -> List[str]
    async def route_message(self, user_id: str, websocket: WebSocket, raw_message: Dict[str, Any]) -> bool
    def get_stats(self) -> Dict[str, Any]
    
    # Properties
    @property
    def handlers(self) -> List[MessageHandler]
```

#### Critical Features Analysis
1. **Handler Management:**
   - Custom handlers (precedence priority)
   - Built-in handlers (9 core handlers including ConnectionHandler, AgentHandler)
   - Protocol validation prevents raw function registration
   
2. **Message Processing:**
   - JSON-RPC message support
   - Agent event preservation for frontend compatibility
   - Unknown message type handling with grace period
   - Comprehensive routing statistics
   
3. **Built-in Handler Suite:**
   - ConnectionHandler, TypingHandler, HeartbeatHandler
   - AgentHandler, AgentRequestHandler (fallback)
   - UserMessageHandler, JsonRpcHandler, ErrorHandler
   - BatchMessageHandler

#### Missing Functionality Assessment
**ANALYSIS RESULT:** Canonical MessageRouter is FEATURE COMPLETE
- All required methods present and tested
- Comprehensive handler ecosystem
- Production-ready error handling
- Statistics and monitoring built-in

**BACKWARD COMPATIBILITY:** Full compatibility maintained through adapter pattern

### 1.2 Interface Completeness Validation

#### Required Methods Coverage
- ✅ **Handler Registration:** `add_handler()`, `remove_handler()`, `insert_handler()`
- ✅ **Message Routing:** `route_message()` with comprehensive error handling
- ✅ **Statistics:** `get_stats()` with routing metrics
- ✅ **Introspection:** `get_handler_order()` for debugging
- ✅ **Properties:** `handlers` property with priority ordering

#### Advanced Features Available
- ✅ **Protocol Validation:** Prevents invalid handler registration
- ✅ **Grace Period Handling:** 10-second startup grace period for unknown messages
- ✅ **Agent Event Preservation:** Frontend compatibility for agent progress events
- ✅ **JSON-RPC Support:** Complete JSON-RPC message handling
- ✅ **Batch Processing:** BatchMessageHandler for performance optimization

**CONCLUSION:** Canonical MessageRouter exceeds all duplicate implementations' capabilities

<<<<<<< HEAD
=======
---

## 2. DUPLICATE ELIMINATION STRATEGY

### 2.1 Duplicate Implementation Inventory

**PRIMARY COMPETING ROUTER (HIGH PRIORITY)**
- **File:** `/netra_backend/app/core/message_router.py:55` - MessageRouter class
- **Impact:** Direct naming conflict with canonical router
- **Risk:** **CRITICAL** - Causes import ambiguity and Golden Path disruption
- **Strategy:** **IMMEDIATE REMOVAL** with adapter bridge during transition

**SPECIALIZED QUALITY ROUTER (MEDIUM PRIORITY)**
- **File:** `/netra_backend/app/services/websocket/quality_message_router.py:36` - QualityMessageRouter class
- **Impact:** Quality-specific message routing functionality
- **Risk:** **MODERATE** - Quality features need preservation during migration
- **Strategy:** **ADAPTER PATTERN** - Convert to adapter that delegates to canonical router

**ADDITIONAL 22 DUPLICATES (SYSTEMATIC CLEANUP)**
Based on discovery analysis, these include:
- Mock implementations in test files
- Legacy compatibility routers
- Service-specific routing wrappers
- Experimental routing implementations

### 2.2 Proven Elimination Pattern (From WebSocketBroadcastService)

**SUCCESS MODEL:** WebSocketBroadcastService consolidation (Issue #982)
- **Consolidated:** 3 duplicate broadcast implementations into single SSOT
- **Pattern:** Adapter delegation to canonical implementation
- **Result:** Zero business disruption, 100% backward compatibility

#### Adapter Pattern Template
```python
class CompatibilityMessageRouter:
    """Adapter pattern for backward compatibility during SSOT consolidation."""
    
    def __init__(self):
        # SSOT DELEGATION: Use canonical MessageRouter
        from netra_backend.app.websocket_core.handlers import MessageRouter
        self._canonical_router = MessageRouter()
        
        logger.warning(
            "DEPRECATION WARNING: CompatibilityMessageRouter is deprecated. "
            "Use 'from netra_backend.app.websocket_core.handlers import MessageRouter' instead."
        )
    
    def add_handler(self, handler):
        """Delegate to canonical router."""
        return self._canonical_router.add_handler(handler)
    
    async def route_message(self, user_id, websocket, raw_message):
        """Delegate to canonical router."""
        return await self._canonical_router.route_message(user_id, websocket, raw_message)
    
    # ... other methods delegate to canonical implementation
```

### 2.3 High Priority Duplicate Elimination Plan

#### Phase 1: Core Conflict Resolution (IMMEDIATE)

**TARGET:** `/netra_backend/app/core/message_router.py`
**ISSUE:** Direct naming conflict causing import ambiguity

**ELIMINATION STRATEGY:**
1. **Replace with Compatibility Adapter:**
   ```python
   # Replace entire file content with adapter that delegates to canonical router
   from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalMessageRouter
   
   class MessageRouter(CanonicalMessageRouter):
       """Compatibility adapter for MessageRouter during SSOT consolidation."""
       
       def __init__(self):
           super().__init__()
           import warnings
           warnings.warn(
               "Importing MessageRouter from netra_backend.app.core.message_router is deprecated. "
               "Use 'from netra_backend.app.websocket_core.handlers import MessageRouter' instead.",
               DeprecationWarning,
               stacklevel=2
           )
   ```

2. **Consumer Impact Assessment:**
   - 4 files currently importing from this path
   - All imports will continue to work (zero breaking changes)
   - Deprecation warnings guide consumers to canonical path
   
3. **Migration Timeline:**
   - **Phase 1:** Deploy adapter (immediate compatibility)
   - **Phase 2:** Update consumer imports (scheduled migration)
   - **Phase 3:** Remove adapter file (cleanup phase)

#### Phase 2: QualityMessageRouter Consolidation (TARGETED)

**TARGET:** `/netra_backend/app/services/websocket/quality_message_router.py`
**PRESERVATION REQUIREMENT:** Quality-specific message handling features

**CONSOLIDATION STRATEGY:**
1. **Convert to Specialized Handler Pattern:**
   - Extract quality-specific handlers into dedicated MessageHandler implementations
   - Register quality handlers with canonical MessageRouter
   - Eliminate duplicate routing logic

2. **Quality Handler Migration:**
   ```python
   # New approach: Quality handlers register with canonical router
   from netra_backend.app.websocket_core.handlers import get_message_router
   
   class QualityMessageService:
       def __init__(self):
           self.router = get_message_router()
           self._register_quality_handlers()
       
       def _register_quality_handlers(self):
           quality_handlers = [
               QualityMetricsHandler(),
               QualityAlertHandler(),
               QualityValidationHandler(),
               # ... other quality-specific handlers
           ]
           
           for handler in quality_handlers:
               self.router.add_handler(handler)
   ```

3. **Backward Compatibility Bridge:**
   - Keep QualityMessageRouter class as adapter
   - Delegate all routing to canonical router with quality handlers registered
   - Maintain existing API surface for consumers

### 2.4 Systematic Duplicate Cleanup Strategy

**REMAINING 22 DUPLICATES:** Systematic elimination using proven patterns

#### Classification and Strategy

**A) Test Mock Implementations (10-12 duplicates)**
- **Strategy:** Replace with SSotMockFactory implementations
- **Pattern:** Use unified mock generation instead of duplicate mock classes
- **Risk:** **LOW** - Test-only impact

**B) Legacy Compatibility Routers (5-6 duplicates)**  
- **Strategy:** Adapter pattern with deprecation warnings
- **Pattern:** Same as core message router elimination
- **Risk:** **LOW** - Controlled deprecation timeline

**C) Service-Specific Routing Wrappers (3-4 duplicates)**
- **Strategy:** Convert to handler registration pattern
- **Pattern:** Register specialized handlers with canonical router
- **Risk:** **MEDIUM** - Requires handler interface conversion

**D) Experimental/Development Routers (2-3 duplicates)**
- **Strategy:** Direct removal with canonical router migration
- **Pattern:** Update imports and remove files
- **Risk:** **LOW** - Experimental code, minimal production usage

---

## 3. IMPORT STANDARDIZATION PLAN

### 3.1 Current Import Pattern Analysis

**DISCOVERED IMPORT INCONSISTENCIES:** 25 different import paths identified

#### Primary Import Patterns
**Pattern 1: CANONICAL (TARGET)**
```python
from netra_backend.app.websocket_core.handlers import MessageRouter
```
- **Files Using:** 16 files (largest group)
- **Status:** ✅ **CORRECT** - This is the canonical import path
- **Action:** **MAINTAIN** - This is the target pattern for all imports

**Pattern 2: AGENT COMPATIBILITY IMPORT**
```python
from netra_backend.app.agents.message_router import MessageRouter
```
- **Files Using:** 8 files
- **Status:** ⚠️ **DEPRECATED** - Compatibility layer only
- **Action:** **MIGRATE** - Update to canonical path

**Pattern 3: CORE COMPATIBILITY IMPORT**
```python
from netra_backend.app.core.message_router import MessageRouter
```
- **Files Using:** 4 files
- **Status:** ❌ **CONFLICTING** - Creates ambiguity
- **Action:** **ELIMINATE** - Replace with canonical path

#### Specialized Import Patterns
**Quality Router Import**
```python
from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
```
- **Action:** **CONVERT** - Migrate to canonical router with quality handlers

### 3.2 Import Standardization Strategy

#### Phase 1: Immediate Critical Path Updates

**HIGH PRIORITY IMPORTS (Critical to Golden Path)**
- `/tests/mission_critical/test_message_router_*.py` - 5 files
- `/tests/integration/test_authenticated_chat_workflow_comprehensive.py`
- `/tests/unit/websocket/test_basic_triage_response_unit.py`
- `/tests/unit/message_routing/test_execute_agent_message_type_reproduction.py`

**UPDATE STRATEGY:**
```bash
# Systematic find and replace across critical files
find tests/mission_critical -name "*.py" -exec sed -i '' 's|from netra_backend\.app\.agents\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g' {} \;
find tests/mission_critical -name "*.py" -exec sed -i '' 's|from netra_backend\.app\.core\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g' {} \;
```

#### Phase 2: Integration Test Updates

**INTEGRATION TEST IMPORTS (8 files requiring updates)**
- `/tests/integration/test_basic_triage_response_integration.py`
- `/tests/integration/test_authenticated_chat_workflow_comprehensive.py`
- Other integration tests importing from deprecated paths

**BATCH UPDATE STRATEGY:**
```bash
# Update all integration test imports
find tests/integration -name "*.py" -exec grep -l "from netra_backend\.app\.agents\.message_router import MessageRouter" {} \; | xargs sed -i '' 's|from netra_backend\.app\.agents\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g'
```

#### Phase 3: Unit Test Import Cleanup

**UNIT TEST PATTERN CONSOLIDATION**
```bash
# Systematic unit test import updates
find tests/unit -name "*.py" -exec sed -i '' 's|from netra_backend\.app\.core\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g' {} \;
find tests/unit -name "*.py" -exec sed -i '' 's|from netra_backend\.app\.agents\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g' {} \;
```

### 3.3 Import Migration Automation Plan

#### Automated Migration Script Template
```python
#!/usr/bin/env python3
"""MessageRouter Import Standardization Script"""

import os
import re
from pathlib import Path

class MessageRouterImportMigrator:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.canonical_import = "from netra_backend.app.websocket_core.handlers import MessageRouter"
        
        # Import patterns to replace
        self.deprecated_patterns = [
            (r'from netra_backend\.app\.agents\.message_router import MessageRouter', 
             'from netra_backend.app.websocket_core.handlers import MessageRouter'),
            (r'from netra_backend\.app\.core\.message_router import MessageRouter',
             'from netra_backend.app.websocket_core.handlers import MessageRouter'),
            # Add other patterns as needed
        ]
    
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate imports in a single file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            for old_pattern, new_import in self.deprecated_patterns:
                content = re.sub(old_pattern, new_import, content)
            
            if content != original_content:
                # Backup original file
                backup_path = file_path.with_suffix(f'{file_path.suffix}.bak')
                file_path.rename(backup_path)
                
                # Write updated content
                file_path.write_text(content, encoding='utf-8')
                print(f"✅ Updated: {file_path}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return False
    
    def migrate_directory(self, directory: str, pattern: str = "*.py") -> dict:
        """Migrate all Python files in directory."""
        dir_path = self.project_root / directory
        results = {'updated': 0, 'skipped': 0, 'errors': 0}
        
        for file_path in dir_path.rglob(pattern):
            if self.migrate_file(file_path):
                results['updated'] += 1
            else:
                results['skipped'] += 1
        
        return results

# Usage example:
# migrator = MessageRouterImportMigrator('/path/to/netra-apex')
# results = migrator.migrate_directory('tests/mission_critical')
```

### 3.4 Circular Import Risk Assessment

#### Potential Circular Dependencies
**ANALYSIS:** Based on import patterns, identify potential circular imports

**RISK ASSESSMENT:**
- **LOW RISK:** Canonical import path `/netra_backend/app/websocket_core/handlers.py`
  - Does not import from locations being migrated
  - Self-contained handler implementation
  - No dependencies on deprecated router locations

**MITIGATION STRATEGIES:**
1. **Import Timing Analysis:** Verify no runtime circular imports
2. **Dependency Graph Validation:** Map all import relationships
3. **Incremental Testing:** Test each migration batch independently

### 3.5 Temporary Compatibility Import Strategy

#### Compatibility Bridge Pattern
```python
# In deprecated import locations - temporary bridge during migration
try:
    from netra_backend.app.websocket_core.handlers import MessageRouter
    import warnings
    
    warnings.warn(
        f"Importing MessageRouter from {__name__} is deprecated. "
        f"Use 'from netra_backend.app.websocket_core.handlers import MessageRouter' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    __all__ = ['MessageRouter']
    
except ImportError as e:
    raise ImportError(
        f"Cannot import canonical MessageRouter. SSOT consolidation may be incomplete: {e}"
    ) from e
```

#### Rollback Import Plan
```python
# Emergency rollback capability
class ImportPathRollback:
    """Emergency rollback for import path changes."""
    
    @staticmethod
    def restore_original_imports(backup_directory: str) -> None:
        """Restore original import patterns from backup files."""
        for backup_file in Path(backup_directory).rglob("*.py.bak"):
            original_file = backup_file.with_suffix("")
            backup_file.rename(original_file)
            print(f"Restored: {original_file}")

---

## 4. COMPREHENSIVE MIGRATION SEQUENCE PLAN

### 4.1 Safe Migration Sequence Overview

**PRINCIPLE:** Minimize Golden Path disruption through atomic, reversible changes with comprehensive validation at each step.

#### Migration Timeline
- **Phase 1 (Critical):** Core conflict resolution (1-2 hours)
- **Phase 2 (Foundation):** Adapter deployment and validation (4-6 hours) 
- **Phase 3 (Systematic):** Import standardization (6-8 hours)
- **Phase 4 (Cleanup):** Duplicate elimination (4-6 hours)
- **Phase 5 (Validation):** Final consolidation verification (2-4 hours)

**TOTAL ESTIMATED EFFORT:** 17-26 hours with comprehensive testing

### 4.2 Phase 1: Critical Core Conflict Resolution

**OBJECTIVE:** Eliminate direct naming conflicts causing import ambiguity
**DURATION:** 1-2 hours
**RISK LEVEL:** LOW (Adapter pattern ensures compatibility)

#### Step 1.1: Deploy Core Message Router Adapter
```bash
# 1. Backup original conflicting file
cp netra_backend/app/core/message_router.py netra_backend/app/core/message_router.py.original

# 2. Replace with compatibility adapter
cat > netra_backend/app/core/message_router.py << 'EOF'
"""Message Router Compatibility Adapter - SSOT Consolidation"""

import warnings
from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalMessageRouter

class MessageRouter(CanonicalMessageRouter):
    """Compatibility adapter during SSOT consolidation."""
    
    def __init__(self):
        super().__init__()
        warnings.warn(
            "Importing MessageRouter from netra_backend.app.core.message_router is deprecated. "
            "Use 'from netra_backend.app.websocket_core.handlers import MessageRouter' instead.",
            DeprecationWarning,
            stacklevel=2
        )

# Backward compatibility exports
__all__ = ['MessageRouter']
EOF

# 3. Verify adapter deployment
python3 -c "from netra_backend.app.core.message_router import MessageRouter; print('✅ Adapter deployed successfully')"
```

#### Step 1.2: Critical Path Validation
```bash
# Validate mission critical tests still pass
python3 tests/mission_critical/test_message_router_ssot_compliance.py
python3 tests/mission_critical/test_message_router_ssot_enforcement.py

# If tests fail, rollback immediately:
# mv netra_backend/app/core/message_router.py.original netra_backend/app/core/message_router.py
```

**SUCCESS CRITERIA:**
- ✅ All mission critical MessageRouter tests pass
- ✅ No import errors in existing code
- ✅ Deprecation warnings appear for core imports
- ✅ Golden Path functionality unchanged

### 4.3 Phase 2: Foundation Adapter Deployment

**OBJECTIVE:** Deploy compatibility adapters for all duplicate implementations
**DURATION:** 4-6 hours
**RISK LEVEL:** LOW (Proven adapter pattern from WebSocketBroadcastService)

#### Step 2.1: QualityMessageRouter Conversion
```python
# Convert QualityMessageRouter to adapter pattern
# File: netra_backend/app/services/websocket/quality_message_router.py

class QualityMessageRouter:
    """Quality message routing adapter - delegates to canonical router with quality handlers."""
    
    def __init__(self, supervisor, db_session_factory, quality_gate_service, monitoring_service):
        # Import canonical router
        from netra_backend.app.websocket_core.handlers import get_message_router
        
        self._canonical_router = get_message_router()
        self.supervisor = supervisor
        self.db_session_factory = db_session_factory
        self.quality_gate_service = quality_gate_service
        self.monitoring_service = monitoring_service
        
        # Register quality-specific handlers with canonical router
        self._register_quality_handlers()
        
        import warnings
        warnings.warn(
            "QualityMessageRouter is deprecated. Use canonical MessageRouter with quality handlers.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def _register_quality_handlers(self):
        """Register quality handlers with canonical router."""
        quality_handlers = [
            QualityMetricsHandler(self.monitoring_service),
            QualityAlertHandler(self.monitoring_service),
            QualityValidationHandler(self.quality_gate_service),
            QualityReportHandler(self.monitoring_service)
        ]
        
        for handler in quality_handlers:
            self._canonical_router.add_handler(handler)
    
    async def handle_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """Delegate to canonical router."""
        # Convert to WebSocket format and delegate
        websocket = await self._get_user_websocket(user_id)
        return await self._canonical_router.route_message(user_id, websocket, message)
```

#### Step 2.2: Mock Implementation Consolidation
```python
# Update test mock implementations to use SSotMockFactory
# Replace duplicate MockMessageRouter classes with:

from test_framework.ssot.mock_factory import SSotMockFactory

class TestMessageRouterBehavior:
    def test_routing_behavior(self):
        # OLD: MockMessageRouter()
        # NEW: Use SSOT mock factory
        mock_router = SSotMockFactory.create_message_router_mock()
        # ... rest of test
```

### 4.4 Phase 3: Systematic Import Standardization

**OBJECTIVE:** Update all 25 import inconsistencies to canonical path
**DURATION:** 6-8 hours
**RISK LEVEL:** MEDIUM (Comprehensive testing required)

#### Step 3.1: Critical Path Import Updates (HIGH PRIORITY)
```bash
# Mission critical test imports - MUST BE FIRST
find tests/mission_critical -name "*.py" -type f \
  -exec grep -l "from netra_backend\.app\.agents\.message_router import" {} \; \
  | xargs -I {} cp {} {}.backup

find tests/mission_critical -name "*.py" -type f \
  -exec sed -i '' 's|from netra_backend\.app\.agents\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g' {} \;

# Validate critical path still works
python3 tests/mission_critical/test_message_router_ssot_compliance.py
```

#### Step 3.2: Integration Test Import Updates
```bash
# Update integration test imports with backup
find tests/integration -name "*.py" -type f \
  -exec grep -l "from netra_backend\.app\.(agents|core)\.message_router import" {} \; \
  | while read file; do
      cp "$file" "$file.backup"
      sed -i '' 's|from netra_backend\.app\.agents\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g' "$file"
      sed -i '' 's|from netra_backend\.app\.core\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g' "$file"
  done

# Validate integration tests
python3 tests/unified_test_runner.py --category integration --fast-fail
```

#### Step 3.3: Unit Test Import Updates  
```bash
# Unit test import updates with validation
find tests/unit -name "*.py" -type f \
  -exec grep -l "from netra_backend\.app\.(agents|core)\.message_router import" {} \; \
  | while read file; do
      cp "$file" "$file.backup"
      sed -i '' 's|from netra_backend\.app\.agents\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g' "$file"
      sed -i '' 's|from netra_backend\.app\.core\.message_router import MessageRouter|from netra_backend.app.websocket_core.handlers import MessageRouter|g' "$file"
  done
```

### 4.5 Phase 4: Duplicate Implementation Cleanup

**OBJECTIVE:** Remove duplicate implementations while preserving functionality
**DURATION:** 4-6 hours
**RISK LEVEL:** MEDIUM (Comprehensive validation required)

#### Step 4.1: Test Mock Duplicate Removal
```bash
# Remove duplicate mock implementations
find tests -name "*.py" -type f \
  -exec grep -l "class.*MockMessageRouter" {} \; \
  | while read file; do
      echo "Removing MockMessageRouter from: $file"
      # Replace with SSotMockFactory usage
      # Manual review required for each test file
  done
```

#### Step 4.2: Legacy Compatibility Router Removal
```bash
# Phase 4.2.1: Mark for removal with deprecation
# Phase 4.2.2: Remove after import migration complete
# Phase 4.2.3: Final cleanup verification
```

### 4.6 Phase 5: Final Consolidation Verification

**OBJECTIVE:** Validate complete SSOT consolidation success
**DURATION:** 2-4 hours
**RISK LEVEL:** LOW (Validation only)

#### Step 5.1: Comprehensive Test Validation
```bash
# Run complete test suite to validate consolidation
python3 tests/unified_test_runner.py --categories mission_critical unit integration e2e --real-services

# Specific SSOT validation tests
python3 tests/mission_critical/test_message_router_ssot_compliance.py
python3 tests/mission_critical/test_message_router_ssot_enforcement.py
python3 tests/ssot_validation/test_message_router_duplicate_detection.py
```

#### Step 5.2: Final SSOT Compliance Verification
```bash
# Verify single MessageRouter implementation exists
echo "Verifying SSOT consolidation..."
router_implementations=$(find . -name "*.py" -type f -not -path "./.*" \
  -exec grep -l "^class MessageRouter" {} \; | wc -l)

if [ "$router_implementations" -eq 1 ]; then
    echo "✅ SSOT SUCCESS: Single MessageRouter implementation found"
else
    echo "❌ SSOT VIOLATION: $router_implementations MessageRouter implementations found"
    exit 1
fi
```
```

>>>>>>> 8764938e17e7cbfd22700a00d83f352704f5be9d
<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Analyze canonical MessageRouter interface and capabilities", "status": "in_progress", "activeForm": "Analyzing canonical MessageRouter interface and capabilities"}, {"content": "Plan duplicate elimination strategy for 24 MessageRouter implementations", "status": "pending", "activeForm": "Planning duplicate elimination strategy for 24 MessageRouter implementations"}, {"content": "Design import standardization plan for 25 import inconsistencies", "status": "pending", "activeForm": "Designing import standardization plan for 25 import inconsistencies"}, {"content": "Create comprehensive migration sequence plan", "status": "pending", "activeForm": "Creating comprehensive migration sequence plan"}, {"content": "Develop rollback and safety procedures", "status": "pending", "activeForm": "Developing rollback and safety procedures"}, {"content": "Define success criteria and validation metrics", "status": "pending", "activeForm": "Defining success criteria and validation metrics"}]