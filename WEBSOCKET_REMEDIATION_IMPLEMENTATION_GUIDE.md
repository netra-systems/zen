# WebSocket Authentication Remediation Implementation Guide

**Execution Priority**: P0 - Critical Production Fix  
**Business Impact**: Protects $500K+ ARR by restoring WebSocket authentication reliability
**Technical Goal**: Fix RFC 6455 handshake timing violations while preserving all business functionality

## Quick Reference Implementation Steps

### Phase 1: JWT Validation Fix (IMMEDIATE - 2 hours)

#### File: `netra_backend/app/websocket_core/unified_jwt_protocol_handler.py`
**Lines to Modify**: 92-118 in `_extract_from_subprotocol_value` method

**Current Code (BROKEN)**:
```python
if len(encoded_token) < 10:
    raise ValueError(f"JWT token too short in subprotocol: {protocol}")
```

**Fixed Code (GRACEFUL)**:
```python
# CRITICAL FIX: Handle empty token gracefully
if not encoded_token.strip():
    logger.warning(f"Empty JWT token in subprotocol: {protocol}")
    return None  # Return None instead of raising ValueError

# Validate minimum token length AFTER checking for empty
if len(encoded_token) < 10:
    logger.warning(f"JWT token too short in subprotocol: {protocol}")
    return None  # Return None for short tokens rather than failing
```

#### Exact Implementation:
```python
@staticmethod
def _extract_from_subprotocol_value(subprotocol_value: str) -> Optional[str]:
    """
    Extract JWT from subprotocol header value directly.
    
    ISSUE #280 FIX: Enhanced to handle empty/malformed tokens gracefully
    instead of raising ValueError which breaks WebSocket handshake.
    """
    if not subprotocol_value or not subprotocol_value.strip():
        return None
        
    # Split comma-separated subprotocols
    subprotocols = [p.strip() for p in subprotocol_value.split(",")]
    
    for protocol in subprotocols:
        if protocol.startswith("jwt."):
            encoded_token = protocol[4:]  # Remove "jwt." prefix
            
            # CRITICAL FIX: Handle empty token gracefully
            if not encoded_token.strip():
                logger.warning(f"Empty JWT token in subprotocol: {protocol}")
                continue  # Try next protocol instead of failing
            
            # Validate minimum token length AFTER checking for empty
            if len(encoded_token) < 10:
                logger.warning(f"JWT token too short in subprotocol: {protocol}")
                continue  # Try next protocol instead of failing
            
            # Try to decode as base64url first (standard frontend implementation)
            jwt_token = UnifiedJWTProtocolHandler._decode_base64url_token(encoded_token)
            if jwt_token:
                logger.debug("Extracted base64url-decoded JWT from subprotocol value")
                return jwt_token
            
            # If base64url decode fails, treat as raw token (direct format)
            if UnifiedJWTProtocolHandler._is_valid_jwt_format(encoded_token):
                logger.debug("Extracted raw JWT from subprotocol value")
                return encoded_token
            else:
                logger.warning(f"Invalid JWT format in subprotocol: {protocol}")
                continue  # Try next protocol instead of failing
                
    return None
```

### Phase 2: Handshake Timing Fix (CRITICAL - 6 hours)

#### File: `netra_backend/app/routes/websocket_ssot.py`
**Method to Modify**: `_handle_main_mode` (lines 318-458)

#### Step 1: Add Pre-Handshake Authentication Method
**Add after line 316 (before `_handle_main_mode` method)**:

```python
@dataclass
class PreHandshakeAuthResult:
    """Result of pre-handshake authentication and subprotocol negotiation."""
    success: bool
    user_context: Optional[UserExecutionContext] = None
    error: Optional[str] = None
    negotiated_subprotocol: Optional[str] = None

async def _pre_handshake_authentication(
    self, 
    websocket: WebSocket, 
    preliminary_connection_id: str
) -> PreHandshakeAuthResult:
    """
    CRITICAL FIX: Perform authentication BEFORE WebSocket handshake completion.
    
    This method implements RFC 6455 compliant subprotocol negotiation
    with integrated JWT authentication, fixing the handshake timing violation.
    """
    try:
        # Step 1: Extract and validate subprotocol header
        subprotocol_header = websocket.headers.get("sec-websocket-protocol", "")
        logger.debug(f"Pre-handshake: subprotocol header = '{subprotocol_header}'")
        
        # Step 2: Parse client-requested subprotocols  
        client_protocols = []
        if subprotocol_header:
            client_protocols = [p.strip() for p in subprotocol_header.split(",")]
            logger.debug(f"Pre-handshake: client requested subprotocols = {client_protocols}")
        
        # Step 3: Extract JWT if present in subprotocol (graceful failure handling)
        jwt_token = None
        jwt_extracted = False
        if subprotocol_header:
            try:
                from netra_backend.app.websocket_core.unified_jwt_protocol_handler import extract_jwt_from_subprotocol
                jwt_token = extract_jwt_from_subprotocol(subprotocol_header)
                if jwt_token:
                    jwt_extracted = True
                    logger.debug("Pre-handshake: JWT successfully extracted from subprotocol")
            except Exception as jwt_error:
                logger.warning(f"Pre-handshake: JWT extraction failed (non-fatal): {jwt_error}")
                # Continue without JWT - may be in Authorization header
        
        # Step 4: Authenticate using extracted JWT or headers
        try:
            auth_result = await authenticate_websocket_ssot(
                websocket, 
                preliminary_connection_id=preliminary_connection_id
            )
        except Exception as auth_error:
            logger.error(f"Pre-handshake: Authentication failed: {auth_error}")
            return PreHandshakeAuthResult(
                success=False,
                error=f"Authentication error: {str(auth_error)}"
            )
        
        if not auth_result.success:
            logger.error(f"Pre-handshake: Authentication failed: {auth_result.error_message}")
            return PreHandshakeAuthResult(
                success=False,
                error=auth_result.error_message
            )
        
        # Step 5: Negotiate appropriate subprotocol response (RFC 6455 compliant)
        accepted_protocol = None
        if client_protocols:
            try:
                from netra_backend.app.websocket_core.unified_jwt_protocol_handler import negotiate_websocket_subprotocol
                accepted_protocol = negotiate_websocket_subprotocol(client_protocols)
                logger.debug(f"Pre-handshake: negotiated subprotocol = '{accepted_protocol}'")
            except Exception as negotiation_error:
                logger.warning(f"Pre-handshake: Subprotocol negotiation failed (non-fatal): {negotiation_error}")
                # Continue without subprotocol
        
        logger.info(f"Pre-handshake: Authentication successful for user {auth_result.user_context.user_id[:8]}...")
        return PreHandshakeAuthResult(
            success=True,
            user_context=auth_result.user_context,
            negotiated_subprotocol=accepted_protocol
        )
        
    except Exception as e:
        logger.error(f"Pre-handshake: Critical error during authentication: {e}", exc_info=True)
        return PreHandshakeAuthResult(
            success=False,
            error=f"Pre-handshake authentication failed: {str(e)}"
        )
```

#### Step 2: Modify Main Mode Handler  
**Replace lines 390-414 in `_handle_main_mode` method**:

**Current Code (BROKEN TIMING)**:
```python
# Step 1: Negotiate subprotocol and accept WebSocket connection (RFC 6455 compliance)
accepted_subprotocol = self._negotiate_websocket_subprotocol(websocket)
if accepted_subprotocol:
    logger.info(f"[MAIN MODE] Accepting WebSocket with subprotocol: {accepted_subprotocol}")
    await websocket.accept(subprotocol=accepted_subprotocol)
else:
    logger.debug("[MAIN MODE] Accepting WebSocket without subprotocol")
    await websocket.accept()

# Step 2: SSOT Authentication (preserves full auth pipeline)
auth_result = await authenticate_websocket_ssot(
    websocket, 
    preliminary_connection_id=preliminary_connection_id
)
```

**Fixed Code (CORRECT TIMING)**:
```python
# Step 1: CRITICAL FIX - Pre-Accept Authentication (RFC 6455 compliant timing)
pre_auth_result = await self._pre_handshake_authentication(websocket, preliminary_connection_id)

if not pre_auth_result.success:
    logger.error(f"[MAIN MODE] Pre-handshake authentication failed: {pre_auth_result.error}")
    # Close connection with proper WebSocket close code BEFORE accepting
    await websocket.close(code=1008, reason="Authentication failed")
    return

user_context = pre_auth_result.user_context
accepted_subprotocol = pre_auth_result.negotiated_subprotocol

# Step 2: Accept WebSocket with authenticated subprotocol (FIXED TIMING)
if accepted_subprotocol:
    logger.info(f"[MAIN MODE] Accepting authenticated WebSocket with subprotocol: {accepted_subprotocol}")
    await websocket.accept(subprotocol=accepted_subprotocol)
else:
    logger.debug("[MAIN MODE] Accepting authenticated WebSocket without subprotocol")
    await websocket.accept()
```

#### Step 3: Update User Context Assignment
**Replace line 413-414**:

**Current Code**:
```python
user_context = auth_result.user_context
user_id = getattr(auth_result.user_context, 'user_id', None) if auth_result.success else None
```

**Fixed Code**:
```python
# user_context already assigned from pre_auth_result above
user_id = user_context.user_id if user_context else None
```

### Phase 3: Apply Same Pattern to All WebSocket Modes (2 hours)

#### Factory Mode Fix
**File**: `netra_backend/app/routes/websocket_ssot.py`  
**Method**: `_handle_factory_mode` (lines 460-546)

**Replace lines 492-500**:
```python
# Step 2: Negotiate subprotocol and accept connection after authentication (RFC 6455 compliance)
accepted_subprotocol = self._negotiate_websocket_subprotocol(websocket)
if accepted_subprotocol:
    logger.info(f"[FACTORY MODE] Accepting WebSocket with subprotocol: {accepted_subprotocol}")
    await websocket.accept(subprotocol=accepted_subprotocol)
else:
    logger.debug("[FACTORY MODE] Accepting WebSocket without subprotocol")
    await websocket.accept()
```

**With**:
```python
# Step 2: Pre-handshake authentication for factory mode
pre_auth_result = await self._pre_handshake_authentication(websocket, f"factory_{connection_id}")

if not pre_auth_result.success:
    logger.error(f"[FACTORY MODE] Pre-handshake authentication failed: {pre_auth_result.error}")
    await websocket.close(code=1008, reason="Factory authentication failed")
    return

# Update user_context from pre-auth result
user_context = pre_auth_result.user_context
accepted_subprotocol = pre_auth_result.negotiated_subprotocol

# Accept with negotiated subprotocol
if accepted_subprotocol:
    logger.info(f"[FACTORY MODE] Accepting authenticated WebSocket with subprotocol: {accepted_subprotocol}")
    await websocket.accept(subprotocol=accepted_subprotocol)
else:
    logger.debug("[FACTORY MODE] Accepting authenticated WebSocket without subprotocol")
    await websocket.accept()
```

#### Isolated Mode Fix  
**Method**: `_handle_isolated_mode` (lines 548-636)

**Replace lines 566-580**:
```python
# Step 1: Negotiate subprotocol and accept connection (RFC 6455 compliance)
accepted_subprotocol = self._negotiate_websocket_subprotocol(websocket)
if accepted_subprotocol:
    logger.info(f"[ISOLATED MODE] Accepting WebSocket with subprotocol: {accepted_subprotocol}")
    await websocket.accept(subprotocol=accepted_subprotocol)
else:
    logger.debug("[ISOLATED MODE] Accepting WebSocket without subprotocol")
    await websocket.accept()

# Step 2: SSOT Authentication with audit logging
auth_result = await authenticate_websocket_ssot(websocket)
if not auth_result.success:
    logger.error(f"[ISOLATED MODE] Authentication failed: {auth_result.error}")
    await safe_websocket_close(websocket, 1008, "Authentication failed")
    return
```

**With**:
```python
# Step 1: Pre-handshake authentication for isolated mode  
pre_auth_result = await self._pre_handshake_authentication(websocket, f"isolated_{connection_id}")

if not pre_auth_result.success:
    logger.error(f"[ISOLATED MODE] Pre-handshake authentication failed: {pre_auth_result.error}")
    await websocket.close(code=1008, reason="Isolated authentication failed")
    return

user_context_from_auth = pre_auth_result.user_context
accepted_subprotocol = pre_auth_result.negotiated_subprotocol

# Accept connection with authenticated subprotocol
if accepted_subprotocol:
    logger.info(f"[ISOLATED MODE] Accepting authenticated WebSocket with subprotocol: {accepted_subprotocol}")
    await websocket.accept(subprotocol=accepted_subprotocol)
else:
    logger.debug("[ISOLATED MODE] Accepting authenticated WebSocket without subprotocol")
    await websocket.accept()
```

## Critical Implementation Notes

### Don't Break These Requirements:
1. **All 5 Critical WebSocket Events**: `agent_started`, `agent_thinking`, `tool_executing`, `tool_completed`, `agent_completed`
2. **Golden Path Integration**: Complete login → AI responses flow 
3. **User Isolation**: Factory and isolated patterns maintain security
4. **Cloud Run Compatibility**: GCP readiness validation preserved
5. **Backward Compatibility**: Legacy mode continues working

### Required Imports to Add:
```python
# Add to imports at top of websocket_ssot.py
from dataclasses import dataclass
from netra_backend.app.services.user_execution_context import UserExecutionContext
```

## Testing Strategy

### Phase 1 Testing (JWT Validation):
```bash
# Test the specific failing case
python -c "
from netra_backend.app.websocket_core.unified_jwt_protocol_handler import extract_jwt_from_subprotocol
try:
    result = extract_jwt_from_subprotocol('jwt.')
    print(f'Result: {result}')  # Should be None, not ValueError
except Exception as e:
    print(f'Error: {e}')  # Should not happen anymore
"
```

### Phase 2 Testing (Handshake Timing):
```bash
# Test pre-accept authentication
python tests/mission_critical/test_websocket_agent_events_suite.py

# Test Golden Path preservation  
python -m pytest tests/e2e/test_golden_path_websocket_flow.py -v
```

### Full Integration Testing:
```bash
# Test all modes work correctly
python -m pytest tests/integration/websocket/ -v

# Test business functionality preserved
python tests/mission_critical/test_websocket_agent_events_suite.py
```

## Success Validation

### Technical Success Criteria:
- [ ] JWT extraction returns `None` for empty tokens (no ValueError)
- [ ] Authentication occurs BEFORE `websocket.accept()` in all modes
- [ ] Subprotocol negotiation follows RFC 6455 specification
- [ ] All WebSocket modes (main, factory, isolated, legacy) work correctly

### Business Success Criteria:  
- [ ] Golden Path tests pass: Users login → get AI responses
- [ ] All 5 critical WebSocket events fire correctly
- [ ] Agent orchestration continues working
- [ ] No regression in chat functionality
- [ ] WebSocket connection success rate maintained

## Rollback Plan

If any issues occur during implementation:

### Phase 1 Rollback (JWT Validation):
```python
# Revert to original error-raising behavior
if len(encoded_token) < 10:
    raise ValueError(f"JWT token too short in subprotocol: {protocol}")
```

### Phase 2 Rollback (Handshake Timing):
```python  
# Move authentication back to post-accept
await websocket.accept(subprotocol=accepted_subprotocol)
auth_result = await authenticate_websocket_ssot(websocket, ...)
```

### Emergency Rollback:
- Revert entire `websocket_ssot.py` file to previous version
- Deploy immediately if business functionality breaks
- Investigate issues in development environment

## Implementation Timeline

| Phase | Duration | Actions |
|-------|----------|---------|
| **Phase 1** | 2 hours | JWT validation fix + testing |
| **Phase 2** | 6 hours | Handshake timing fix + testing |  
| **Phase 3** | 2 hours | Apply to all modes + full testing |
| **Validation** | 2 hours | Golden Path + business logic testing |
| **Total** | 12 hours | Complete remediation with validation |

This implementation guide provides the exact code changes needed to fix the RFC 6455 handshake timing violations while preserving all $500K+ ARR business functionality.