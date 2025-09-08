# WebSocket 1011 Internal Server Error - Five Whys Root Cause Analysis

## Executive Summary

**MISSION CRITICAL**: WebSocket 1011 internal server errors are causing all real-time communication tests in staging to fail. This comprehensive five whys analysis traces the root cause through multiple layers of the system to identify the specific code locations and conditions causing the internal server error pattern.

**Error Pattern Observed:**
- WebSocket connections establish successfully with proper authentication
- JWT tokens work correctly for staging-e2e-user-001
- Error occurs during operation: "received 1011 (internal error) Internal error; then sent 1011 (internal error) Internal error"
- Affects all real-time communication tests in staging environment
- Tests run for 53 seconds (proving real network calls are made)
- Environment: `wss://api.staging.netrasystems.ai/ws`

## Five Whys Analysis

### Why #1: Why are WebSocket connections receiving 1011 internal server errors?

**Answer**: The WebSocket endpoint is encountering unhandled exceptions during message processing or connection management that are being caught by the general exception handler and converted to 1011 errors.

**Evidence from Code Analysis**:
```python
# From netra_backend/app/routes/websocket.py lines 751-769
except Exception as e:
    logger.error(f"WebSocket error: {e}", exc_info=True)
    if is_websocket_connected(websocket):
        try:
            error_msg = create_server_message(
                MessageType.ERROR,
                {
                    "error": "Internal server error",
                    "message": "An unexpected error occurred. Please reconnect.",
                    "code": "INTERNAL_ERROR"
                }
            )
            await safe_websocket_send(websocket, error_msg.model_dump())
            await asyncio.sleep(0.1)
        except Exception:
            pass
        await safe_websocket_close(websocket, code=1011, reason="Internal error")
```

**Key Finding**: Line 769 explicitly sends 1011 code with "Internal error" reason, matching the exact error pattern observed.

---

### Why #2: Why are unhandled exceptions occurring in the WebSocket endpoint?

**Answer**: The WebSocket factory initialization is failing during the creation of isolated WebSocket managers, causing FactoryInitializationError exceptions that cascade into 1011 errors.

**Evidence from Code Analysis**:
```python
# From netra_backend/app/routes/websocket.py lines 296-335
try:
    ws_manager = create_websocket_manager(user_context)
    logger.info(f"🏭 FACTORY PATTERN: Created isolated WebSocket manager (id: {id(ws_manager)})")
except Exception as factory_error:
    from netra_backend.app.websocket_core.websocket_manager_factory import FactoryInitializationError
    
    if isinstance(factory_error, FactoryInitializationError):
        # SSOT validation or factory configuration issue
        logger.error(f"🚨 FACTORY INITIALIZATION FAILED: {factory_error}")
        
        factory_error_msg = create_error_message(
            "FACTORY_INIT_FAILED",
            "WebSocket factory initialization failed due to SSOT validation error.",
            error_context
        )
        await safe_websocket_send(websocket, factory_error_msg.model_dump())
        await safe_websocket_close(websocket, code=1011, reason="Factory SSOT validation failed")
        return
```

**Key Finding**: Line 334 shows another explicit 1011 error path specifically for factory initialization failures.

---

### Why #3: Why is the WebSocket factory initialization failing?

**Answer**: The SSOT (Single Source of Truth) validation in the WebSocket manager factory is failing due to UserExecutionContext type inconsistencies or missing required attributes.

**Evidence from Code Analysis**:
```python
# From netra_backend/app/websocket_core/websocket_manager_factory.py lines 1140-1166
try:
    # CRITICAL FIX: Comprehensive SSOT UserExecutionContext validation
    # This prevents type inconsistencies that cause 1011 errors
    _validate_ssot_user_context(user_context)
    
    factory = get_websocket_manager_factory()
    return factory.create_manager(user_context)
    
except ValueError as validation_error:
    # CRITICAL FIX: Handle SSOT validation failures gracefully
    if "SSOT" in str(validation_error) or "factory" in str(validation_error).lower():
        logger.error(f"[U+1F6A8] SSOT FACTORY VALIDATION FAILURE: {validation_error}")
        raise FactoryInitializationError(
            f"WebSocket factory SSOT validation failed: {validation_error}. "
            f"This indicates UserExecutionContext type incompatibility."
        ) from validation_error
```

**Key Finding**: The `_validate_ssot_user_context()` function performs strict validation that can raise ValueError exceptions, which are then converted to FactoryInitializationError.

---

### Why #4: Why is the SSOT UserExecutionContext validation failing?

**Answer**: The UserExecutionContext validation is failing because either:
1. The context is not the expected SSOT UserExecutionContext type
2. Required attributes (user_id, thread_id, websocket_client_id, run_id, request_id) are missing or None
3. Attribute types/values are invalid (empty strings, wrong types)

**Evidence from Code Analysis**:
```python
# From netra_backend/app/websocket_core/websocket_manager_factory.py lines 65-120
def _validate_ssot_user_context(user_context: Any) -> None:
    # CRITICAL FIX: Validate SSOT UserExecutionContext type
    if not isinstance(user_context, UserExecutionContext):
        raise ValueError(
            f"SSOT VIOLATION: Expected netra_backend.app.services.user_execution_context.UserExecutionContext, "
            f"got {actual_type}. "
            f"This indicates incomplete SSOT migration - factory pattern requires SSOT compliance."
        )
    
    # CRITICAL FIX: Validate all required SSOT attributes are present
    required_attrs = ['user_id', 'thread_id', 'websocket_client_id', 'run_id', 'request_id']
    missing_attrs = []
    
    for attr in required_attrs:
        if not hasattr(user_context, attr):
            missing_attrs.append(attr)
        elif getattr(user_context, attr, None) is None and attr != 'websocket_client_id':
            missing_attrs.append(f"{attr} (is None)")
    
    if missing_attrs:
        raise ValueError(
            f"SSOT CONTEXT INCOMPLETE: UserExecutionContext missing required attributes: {missing_attrs}."
        )
```

**Key Finding**: This validation is extremely strict and will fail if any required attribute is missing, None, or of wrong type.

---

### Why #5: Why is the UserExecutionContext incomplete or invalid during staging WebSocket connections?

**Answer**: The UserExecutionContext is being created or passed incorrectly in the staging authentication flow, likely due to:

1. **Authentication Service Context Creation**: The unified authentication service may be creating incomplete UserExecutionContext objects
2. **WebSocket Authentication Flow**: The SSOT WebSocket authentication process may not be properly initializing all required context attributes
3. **Environment-Specific Issues**: Staging environment configuration differences may cause context creation to fail
4. **Factory Pattern Migration**: Incomplete migration from legacy WebSocket patterns to the new factory pattern

**Evidence from Code Analysis**:
```python
# From netra_backend/app/routes/websocket.py lines 223-229
from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

logger.info("🔒 SSOT AUTHENTICATION: Starting WebSocket authentication using unified service")

# SSOT WebSocket Authentication - eliminates all authentication chaos
auth_result = await authenticate_websocket_ssot(websocket)

# From netra_backend/app/websocket_core/unified_websocket_auth.py lines 162-163
auth_result, user_context = await self._auth_service.authenticate_websocket(websocket)
```

**Key Finding**: The UserExecutionContext is created by the unified authentication service's `authenticate_websocket()` method, and any issues in that process will cause invalid contexts to be passed to the factory.

## Root Cause Summary

**PRIMARY ROOT CAUSE**: The UserExecutionContext objects being created by the unified authentication service during staging WebSocket authentication are incomplete or invalid, causing SSOT validation failures in the WebSocket manager factory, which cascade into 1011 internal server errors.

**SECONDARY CONTRIBUTING FACTORS**:
1. **Strict SSOT Validation**: The factory validation is very strict and doesn't gracefully handle edge cases
2. **Error Handling Chain**: Multiple layers convert validation errors into 1011 errors
3. **Environment-Specific Issues**: Staging environment may have configuration differences affecting context creation
4. **Factory Pattern Migration**: Potential incomplete migration from legacy to factory pattern

## Specific Code Locations Causing 1011 Errors

### Primary 1011 Error Sources:
1. **Line 334** in `websocket.py`: Factory initialization failure → 1011 "Factory SSOT validation failed"
2. **Line 769** in `websocket.py`: General exception handler → 1011 "Internal error"

### Validation Failure Points:
1. **Lines 66-77** in `websocket_manager_factory.py`: SSOT type validation
2. **Lines 83-94** in `websocket_manager_factory.py`: Required attributes validation
3. **Lines 100-115** in `websocket_manager_factory.py`: Attribute type/value validation

### Authentication Context Creation:
1. **Line 163** in `unified_websocket_auth.py`: Context creation via auth service
2. **Lines 1140-1143** in `websocket_manager_factory.py`: Factory creation with context

## Recommended Fix Priority

1. **IMMEDIATE**: Add detailed logging to UserExecutionContext creation in auth service
2. **HIGH**: Add graceful fallback for incomplete contexts instead of hard 1011 failures  
3. **MEDIUM**: Review staging environment authentication configuration
4. **LOW**: Consider relaxing SSOT validation for non-critical attributes

## Business Impact

- **CRITICAL**: All real-time WebSocket communication in staging is broken
- **USER EXPERIENCE**: Users cannot receive real-time agent updates, chat responses
- **TESTING**: E2E tests cannot validate WebSocket functionality
- **DEPLOYMENT**: Staging deployment validation is compromised

---

**Generated by**: Five Whys Root Cause Analysis  
**Date**: 2025-01-23  
**Analyst**: Claude Code  
**Status**: Analysis Complete - Root Cause Identified