# SSOT Gardener Progress: WebSocket Import Inconsistencies

**Issue:** SSOT-incomplete-migration-websocket-import-inconsistencies  
**GitHub Link:** https://github.com/netra-systems/netra-apex/issues/212  
**Priority:** CRITICAL - Blocks Golden Path Reliability  
**Business Impact:** $500K+ ARR chat functionality at risk  

## SSOT Violation Summary

**CRITICAL #1: Import Path Inconsistencies**
- **Files Affected:** 593+ files import UnifiedWebSocketManager inconsistently
- **Root Cause:** Multiple import patterns bypass SSOT canonical imports
- **Business Risk:** Integration failures and unpredictable production behavior

### Evidence
```python
# VIOLATION: Multiple import sources for same functionality
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager  
from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory
```

**CRITICAL #2: Factory Pattern SSOT Violation**
- **Security Risk:** Multi-user data leakage potential from singleton patterns
- **Files:** `/netra_backend/app/websocket_core/websocket_manager_factory.py:783`

### Evidence
```python
# FOUND: Legacy singleton usage still present
from netra_backend.app.websocket_core import get_websocket_manager
manager = get_websocket_manager()  # 🚨 SECURITY VIOLATION
```

## Remediation Plan (Phase 1 - URGENT)

### 1. Import Standardization Campaign
- [ ] Run codebase-wide replacement of direct manager imports
- [ ] Update all files to use canonical imports: `from netra_backend.app.websocket_core.canonical_imports import`
- [ ] Validate no import bypasses SSOT validation

### 2. Factory Pattern Enforcement  
- [ ] Audit all `get_websocket_manager()` singleton usage
- [ ] Replace with factory pattern: `create_websocket_manager(user_context)`
- [ ] Ensure user isolation for multi-tenant security

## Test Plan
- [ ] Create failing tests that reproduce SSOT violations
- [ ] Validate import consistency across 593+ affected files
- [ ] Test WebSocket factory pattern prevents singleton usage
- [ ] Ensure Golden Path (login → AI responses) remains stable

## Status Log
- **2025-09-10 Initial:** SSOT audit completed, critical violations identified
- **Next:** Create GitHub issue and begin test discovery

## Success Metrics
- Reduce WebSocket import violations from 593 files to <50 files
- Achieve 95%+ SSOT compliance for WebSocket components
- Maintain Golden Path stability throughout remediation