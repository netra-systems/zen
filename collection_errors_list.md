# Collection Errors List

**Generated:** 2025-09-10  
**Purpose:** Tests that cannot be collected due to import/syntax errors  

## Collection Errors (Infrastructure Issues)

These test files cannot be collected and executed due to missing modules, import errors, or configuration issues:

### Missing Module Errors
1. `tests/unit/services/test_state_cache_manager_redis_integration_unit.py`
   - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.services.state_cache_manager'`
   - **Fix Required:** Create the missing state_cache_manager module

2. `tests/unit/test_state_cache_manager_redis_integration_unit.py`
   - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.services.state_cache_manager'`
   - **Fix Required:** Create the missing state_cache_manager module

### Import Item Errors
3. `tests/unit/services/test_websocket_bridge_factory_ssot_validation.py`
   - **Error:** `ImportError: cannot import name 'WebSocketEvent' from 'netra_backend.app.services.websocket_bridge_factory'`
   - **Fix Required:** Add WebSocketEvent class to websocket_bridge_factory module

### Missing Factory Module Errors
4. `tests/unit/services/websocket/test_quality_message_router_comprehensive.py`
   - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
   - **Fix Required:** Create websocket_manager_factory module

5. `tests/unit/test_message_routing_core.py`
   - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
   - **Fix Required:** Create websocket_manager_factory module

6. `tests/unit/test_websocket_bridge.py`
   - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
   - **Fix Required:** Create websocket_manager_factory module

7. `tests/unit/test_websocket_error_validation_comprehensive.py`
   - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
   - **Fix Required:** Create websocket_manager_factory module

8. `tests/unit/test_websocket_events.py`
   - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
   - **Fix Required:** Create websocket_manager_factory module

9. `tests/unit/test_websocket_manager_factory.py`
   - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
   - **Fix Required:** Create websocket_manager_factory module

10. `tests/unit/tool_dispatcher/test_tool_dispatcher_user_isolation.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

11. `tests/unit/websocket/test_manager_factory_business_logic.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

12. `tests/unit/websocket/test_websocket_event_user_isolation.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

13. `tests/unit/websocket/test_websocket_id_migration_uuid_exposure.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

14. `tests/unit/websocket_core/test_isolated_websocket_manager_comprehensive.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

15. `tests/unit/websocket_core/test_websocket_connection_management_unit.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

16. `tests/unit/websocket_core/test_websocket_manager_factory_comprehensive.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

17. `tests/unit/websocket_core/test_websocket_manager_factory_security_comprehensive.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

18. `tests/unit/websocket_core/test_websocket_manager_factory_ssot_validation.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

19. `tests/unit/websocket_core/test_websocket_manager_race_conditions.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

20. `tests/unit/websocket_core/test_websocket_security_focused.py`
    - **Error:** `ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'`
    - **Fix Required:** Create websocket_manager_factory module

### Auth Service Collection Errors
21. `auth_service/tests/unit/test_database_connection_comprehensive.py`
    - **Error:** `fixture 'real_postgres_connection' not found`
    - **Fix Required:** Add real_postgres_connection fixture to auth service test configuration

## Summary

- **Total Collection Errors:** 21 test files
- **Missing Modules:** 2 modules (`state_cache_manager`, `websocket_manager_factory`)
- **Missing Classes:** 1 class (`WebSocketEvent`)
- **Missing Fixtures:** 1 fixture (`real_postgres_connection`)

## Impact

- **Affected Tests:** ~21 test files cannot be collected
- **Missing Coverage:** WebSocket infrastructure and state management
- **Business Impact:** Core functionality tests are blocked from running

## Priority Fixes

1. **High Priority:** Create `websocket_manager_factory` module (affects 18 tests)
2. **Medium Priority:** Create `state_cache_manager` module (affects 2 tests)
3. **Low Priority:** Add `WebSocketEvent` class (affects 1 test)
4. **Low Priority:** Fix auth service fixture (affects 1 test)

---

*This list should be addressed to enable full test suite execution and improve test coverage visibility.*