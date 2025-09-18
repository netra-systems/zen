# WebSocket SSOT Consolidation Plan - Issue #954

**Status**: Phase 2 - Advanced Consolidation  
**Date**: 2025-09-17  
**Priority**: P0 - Critical Infrastructure  

## Current State Analysis

Based on comprehensive review, the WebSocket SSOT consolidation is 80% complete:

### ✅ COMPLETED (Phase 1)
1. **Primary SSOT Implementation**: `unified_manager.py` is the authoritative implementation
2. **Canonical Import Patterns**: `canonical_import_patterns.py` provides 4 standardized import patterns
3. **Route Consolidation**: `websocket_ssot.py` consolidates 4 competing route implementations 
4. **Factory Pattern**: Advanced factory with user isolation and resource management
5. **Compatibility Layer**: `manager.py` provides backward compatibility with deprecation warnings

### ⚠️ REMAINING WORK (Phase 2)
1. **Circular Dependencies**: Some modules still have circular import patterns
2. **Legacy Module Cleanup**: Remove deprecated implementations not covered by compatibility layer
3. **Import Pattern Enforcement**: Some files still use direct imports instead of canonical patterns
4. **Test Infrastructure**: Update tests to use canonical import patterns

## Phase 2 Consolidation Plan

### Step 1: Fix Circular Dependencies
**Target Files**:
- `websocket_manager.py` imports from `unified_manager.py` 
- `unified_manager.py` components may import back
- Break cycles by using dependency injection

### Step 2: Enforce Canonical Import Patterns
**Action**: Update remaining files to use canonical imports:
```python
# OLD (deprecated)
from netra_backend.app.websocket_core.manager import WebSocketManager

# NEW (canonical)
from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
```

### Step 3: Complete Legacy Cleanup
**Target**: Remove or deprecate files that bypass SSOT:
- Remove direct imports to `unified_manager.py` (use canonical patterns)
- Ensure all WebSocket operations go through canonical entry points

### Step 4: Test Migration
**Action**: Update test files to use canonical patterns:
- Use `get_websocket_manager()` factory function
- Import from `canonical_import_patterns.py`
- Validate SSOT compliance in tests

## Implementation Strategy

### Phase 2A: Critical Path Fixes (Current)
1. ✅ Fix User ID format issues in tests 
2. ✅ Create focused SSOT validation test
3. 🔄 Update factory patterns to prevent circular dependencies
4. ⏳ Run validation tests

### Phase 2B: Complete Consolidation 
1. Update remaining import patterns
2. Remove deprecated direct imports
3. Validate all tests pass with canonical patterns
4. Update documentation and migration guides

## Success Metrics

- All tests use canonical import patterns
- Zero circular dependencies detected
- All WebSocket operations go through SSOT entry points
- Focused SSOT validation test passes 100%
- Migration guide shows 100% pattern consolidation

## Business Impact

- **Revenue Protection**: Maintains $500K+ ARR chat functionality
- **System Stability**: Eliminates SSOT violations causing instabilities  
- **Developer Experience**: Clear import patterns reduce confusion
- **Maintenance**: Single source of truth reduces debugging complexity

## Next Actions

1. Complete factory pattern circular dependency fixes
2. Run comprehensive validation tests
3. Update GitHub issue #954 with progress
4. Plan Phase 2B for complete consolidation