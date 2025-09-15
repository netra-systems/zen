# GCP-active-dev | P2 | WebSocket Manager SSOT violations detected in staging logs

## Impact
SSOT (Single Source of Truth) architecture violations in WebSocket Manager implementations creating code fragmentation and maintenance complexity. While not immediately business-blocking, this technical debt increases development velocity risks and future golden path stability.

## Current Behavior
Production logs show multiple WebSocket Manager class definitions violating SSOT principles:

```
SSOT WARNING: Found other WebSocket Manager classes: [
  'netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager',
  'netra_backend.app.websocket_core.websocket_manager.WebSocketManagerFactory',
  'netra_backend.app.websocket_core.websocket_manager.WebSocketManagerMode',
  'netra_backend.app.websocket_core.websocket_manager.WebSocketManagerProtocol',
  'netra_backend.app.websocket_core.websocket_manager._UnifiedWebSocketManagerImplementation',
  'netra_backend.app.websocket_core.types.WebSocketManagerMode',
  'netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager',
  'netra_backend.app.websocket_core.unified_manager.WebSocketManagerMode',
  'netra_backend.app.websocket_core.unified_manager._UnifiedWebSocketManagerImplementation',
  'netra_backend.app.websocket_core.protocols.WebSocketManagerProtocol',
  'netra_backend.app.websocket_core.protocols.WebSocketManagerProtocolValidator'
]
```

**Count:** 11 different WebSocket Manager classes detected in single service
**Module:** netra_backend.app.websocket_core.manager
**Function:** __init__
**Line:** 45

## Expected Behavior
Single canonical WebSocket Manager implementation following SSOT architecture principles:
- One primary WebSocket Manager class
- Clear interface definition
- Consolidated implementation
- No duplicate or fragmented classes

## Reproduction Steps
1. Deploy staging environment with current codebase
2. Monitor application startup logs
3. Observe SSOT violation warnings during WebSocket Manager initialization
4. Count multiple WebSocket Manager class instantiations

## Technical Details
- **File:** `netra_backend/app/websocket_core/manager.py:45`
- **Error:** `SSOT Violation: Found 11 different WebSocket Manager classes. Expected single source of truth.`
- **Environment:** staging
- **Timestamp:** 2025-09-15T20:03:01.202598+00:00
- **Count:** 12+ occurrences in last hour
- **Log Severity:** WARNING

## Root Cause Analysis
Based on log patterns and codebase analysis:

1. **Import Fragmentation:** Multiple import paths leading to duplicate class loading
2. **Factory Pattern Duplication:** WebSocketManagerFactory implementations scattered across modules
3. **Interface Proliferation:** Protocol and mode classes duplicated instead of consolidated
4. **Legacy Migration:** Incomplete consolidation from previous WebSocket refactoring

## Business Risk Assessment
- **Priority:** P2 (Medium) - Not immediately blocking but increasing technical debt
- **Development Velocity:** Slower feature development due to unclear WebSocket interfaces
- **Future Stability:** Risk of WebSocket inconsistencies affecting golden path
- **Code Maintenance:** Increased complexity for WebSocket-related bug fixes

## Proposed Resolution Strategy

### Phase 1: Consolidation Analysis (2-4 hours)
1. **Audit all WebSocket Manager implementations**
   - Map all 11 detected classes
   - Identify canonical implementation
   - Document dependencies and usage patterns

2. **Create consolidation plan**
   - Define single WebSocket Manager interface
   - Plan import path standardization
   - Identify safe removal candidates

### Phase 2: SSOT Implementation (4-6 hours)
1. **Establish canonical WebSocket Manager**
   ```python
   # netra_backend/app/websocket_core/manager.py
   class CanonicalWebSocketManager:
       """Single source of truth for WebSocket management"""
   ```

2. **Update import paths**
   - Standardize all WebSocket Manager imports
   - Remove duplicate implementations
   - Update factory patterns

3. **Validation testing**
   - Ensure WebSocket functionality preserved
   - Verify golden path integration
   - Test staging deployment

## Related Issues
This appears related to broader SSOT migration efforts documented in:
- Issue #960 (WebSocket SSOT consolidation)
- Issue #1182 (WebSocket Manager consolidation)
- Various SSOT remediation plans in repository

## Monitoring and Validation
Success criteria:
- SSOT violation warnings eliminated from logs
- Single WebSocket Manager class in staging startup
- Golden path WebSocket functionality preserved
- Code complexity metrics improved

---
🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>