
WEBSOCKET MANAGER IMPORT MIGRATION GUIDE - Phase 1

CANONICAL IMPORTS (Use these):
✅ from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
✅ from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
✅ from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

DEPRECATED IMPORTS (Being phased out):
⚠️  from netra_backend.app.websocket_core.manager import WebSocketManager
⚠️  from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
⚠️  from netra_backend.app.websocket_core import get_websocket_manager
⚠️  from netra_backend.app.websocket_core.websocket_manager_factory import ...

MIGRATION STEPS:
1. Replace deprecated imports with canonical imports
2. Test thoroughly after each change
3. Run mission critical tests to validate Golden Path
4. Compatibility shims will show deprecation warnings but won't break

PHASE 1 TIMELINE:
- Week 1: Critical routes and supervisor files
- Week 2: High priority websocket_core and services
- Week 3: Integration and E2E tests  
- Week 4: Unit tests and utilities

SUPPORT:
- Compatibility shims prevent breaking changes during transition
- All deprecated paths still work but show warnings
- Rollback available if any issues occur
