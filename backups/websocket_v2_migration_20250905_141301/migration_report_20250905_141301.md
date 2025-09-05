# WebSocket v2 Critical Services Migration Report

## Summary

**Migration Date:** 2025-09-05 14:13:01
**Duration:** 0:00:00.092540
**Mode:** DRY RUN

### Statistics
- **Total Services Analyzed:** 17
- **Services with Deprecated Usage:** 17
- **Services Successfully Migrated:** 17
- **Services Failed Migration:** 0
- **Success Rate:** 100.0%

**Backup Directory:** backups\websocket_v2_migration_20250905_141301

## Detailed Service Analysis

### websocket\quality_metrics_handler.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 15: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Consider adding user_context parameter to constructor

**Status:** Will be migrated in live run

### memory_startup_integration.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 147: `websocket_manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Consider adding user_context parameter to constructor
- ⚠️ Threading/async usage detected - verify user context propagation

**Status:** Will be migrated in live run

### websocket\quality_report_handler.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 16: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Consider adding user_context parameter to constructor

**Status:** Will be migrated in live run

### agent_service_factory.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 14: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 4/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required

**Status:** Will be migrated in live run

### websocket\quality_manager.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 26: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Consider adding user_context parameter to constructor

**Status:** Will be migrated in live run

### websocket\message_handler.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 23: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Message handlers typically receive context in handle_* methods
- 💡 Consider adding user_context parameter to constructor

**Status:** Will be migrated in live run

### websocket\quality_validation_handler.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 16: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 4/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Consider adding user_context parameter to constructor

**Status:** Will be migrated in live run

### generation_job_manager.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 25: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required

**Status:** Will be migrated in live run

### agent_service_core.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 190: `websocket_manager = get_websocket_manager()`
- Line 195: `websocket_manager = get_websocket_manager()`
- Line 343: `websocket_manager = get_websocket_manager()`
- Line 370: `websocket_manager = get_websocket_manager()`
- Line 394: `websocket_manager = get_websocket_manager()`

**User Context Sources:**
- Line 21: from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ High usage count (5 calls) - requires careful review
- ⚠️ Threading/async usage detected - verify user context propagation

**Status:** Will be migrated in live run

### message_handler_utils.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 7: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 4/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Message handlers typically receive context in handle_* methods

**Status:** Will be migrated in live run

### thread_service.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 24: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 🎯 Service emits WebSocket events - ensure isolated manager is used

**Status:** Will be migrated in live run

### websocket\quality_message_router.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 30: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Consider adding user_context parameter to constructor

**Status:** Will be migrated in live run

### websocket\message_queue.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 374: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Consider adding user_context parameter to constructor
- ⚠️ Threading/async usage detected - verify user context propagation

**Status:** Will be migrated in live run

### websocket\quality_alert_handler.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 15: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Consider adding user_context parameter to constructor

**Status:** Will be migrated in live run

### message_handler_base.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 13: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Message handlers typically receive context in handle_* methods

**Status:** Will be migrated in live run

### websocket_event_router.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core.unified_manager import get_websocket_manager`
- `from netra_backend.app.websocket_core.unified_manager import get_websocket_manager`

**Deprecated Calls:**
- Line 343: `websocket_manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required
- 💡 Consider adding user_context parameter to constructor
- 🎯 Service emits WebSocket events - ensure isolated manager is used

**Status:** Will be migrated in live run

### corpus\clickhouse_operations.py

**Status:** ⚠️ Needs Migration

**Deprecated Imports:**
- `from netra_backend.app.websocket_core import get_websocket_manager`
- `from netra_backend.app.websocket_core import get_websocket_manager`

**Deprecated Calls:**
- Line 36: `manager = get_websocket_manager()`

**⚠️ No User Context Found - Manual intervention required**

**Complexity Score:** 5/5

**Migration Notes:**
- ⚠️ No UserExecutionContext found - manual context creation required

**Status:** Will be migrated in live run

