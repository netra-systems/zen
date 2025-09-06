# WebSocket Connection Race Condition Fix Plan

## Problem Summary
GCP Staging WebSocket connections fail with "No WebSocket connections found for user" error due to race conditions between connection establishment and message sending, particularly during Cloud Run cold starts.

## Fix Implementation Plan

### Phase 1: Add Connection Retry Logic to UnifiedWebSocketManager
**File:** `netra_backend/app/websocket_core/unified_manager.py`

#### Changes Required:
1. Add retry configuration constants
2. Implement retry logic in `send_to_user()` method  
3. Add connection readiness check method
4. Implement message queueing for pending connections

```python
# Configuration constants (add at class level)
CONNECTION_RETRY_MAX_ATTEMPTS = 5
CONNECTION_RETRY_DELAY = 0.5  # seconds
CONNECTION_RETRY_BACKOFF = 1.5  # exponential backoff multiplier
STAGING_EXTRA_RETRIES = 3  # Additional retries for staging/production
```

### Phase 2: Startup Sequence Connection Verification
**File:** `netra_backend/app/startup_module.py`

#### Changes Required:
1. Add WebSocket readiness check after Phase 3
2. Implement connection wait for critical environments
3. Add diagnostic logging for connection state

### Phase 3: WebSocket Route Connection Confirmation  
**File:** `netra_backend/app/routes/websocket_routes.py`

#### Changes Required:
1. Send connection confirmation after registration
2. Process queued messages after connection established
3. Add connection health check endpoint

### Phase 4: Message Recovery Enhancement
**Files:** Multiple WebSocket-related files

#### Changes Required:
1. Enhance message recovery queue mechanism
2. Add automatic retry for recovered messages
3. Implement message priority for critical events

## Implementation Steps

### Step 1: Update UnifiedWebSocketManager with Retry Logic
```python
async def send_to_user_with_retry(self, user_id: str, message: Dict[str, Any]) -> bool:
    """Send message with connection retry logic."""
    # Determine retry attempts based on environment
    max_retries = self.CONNECTION_RETRY_MAX_ATTEMPTS
    if self._is_staging_or_production():
        max_retries += self.STAGING_EXTRA_RETRIES
    
    delay = self.CONNECTION_RETRY_DELAY
    
    for attempt in range(max_retries):
        connection_ids = self.get_user_connections(user_id)
        
        if connection_ids:
            # Connection found, proceed with sending
            return await self._send_to_connections(user_id, connection_ids, message)
        
        if attempt < max_retries - 1:
            # Log retry attempt
            logger.warning(
                f"No connections for user {user_id}, attempt {attempt+1}/{max_retries}. "
                f"Waiting {delay}s before retry..."
            )
            await asyncio.sleep(delay)
            delay *= self.CONNECTION_RETRY_BACKOFF  # Exponential backoff
        else:
            # Final attempt failed
            logger.critical(
                f"CRITICAL ERROR: No WebSocket connections found for user {user_id} "
                f"after {max_retries} attempts. Message type: {message.get('type', 'unknown')}"
            )
            await self._store_failed_message(user_id, message, "no_connections_after_retry")
            return False
    
    return False
```

### Step 2: Add Connection Readiness Verification
```python
async def wait_for_user_connection(self, user_id: str, timeout: float = 10.0) -> bool:
    """Wait for user connection to be established."""
    start_time = asyncio.get_event_loop().time()
    check_interval = 0.1
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        if self.get_user_connections(user_id):
            logger.info(f"Connection established for user {user_id}")
            return True
        await asyncio.sleep(check_interval)
    
    logger.error(f"Timeout waiting for connection for user {user_id}")
    return False
```

### Step 3: Enhance Startup Module
```python
async def _ensure_websocket_connections_ready(app):
    """Ensure WebSocket system is ready to accept connections."""
    if not hasattr(app.state, 'websocket_manager'):
        raise RuntimeError("WebSocket manager not initialized")
    
    manager = app.state.websocket_manager
    
    # In staging/production, verify the manager is fully operational
    if app.state.settings.environment in ['STAGING', 'PRODUCTION']:
        # Perform health check
        if not await manager.health_check():
            raise RuntimeError("WebSocket manager health check failed")
        
        logger.info("WebSocket manager verified and ready for connections")
    
    return True
```

### Step 4: Update WebSocket Route
```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str = None):
    """Enhanced WebSocket endpoint with connection confirmation."""
    await websocket.accept()
    
    try:
        # Register connection
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.utcnow()
        )
        
        await manager.add_connection(connection)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "connection_id": connection.connection_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "ready"
        })
        
        # Process any queued messages for this user
        await manager.process_queued_messages(user_id)
        
        # Keep connection alive
        while True:
            data = await websocket.receive_json()
            # Process incoming messages
            await process_message(user_id, data)
            
    except WebSocketDisconnect:
        await manager.remove_connection(connection.connection_id)
```

## Testing Strategy

### Unit Tests
1. Test retry logic with various failure scenarios
2. Test exponential backoff calculation
3. Test message queueing and recovery
4. Test connection readiness checks

### Integration Tests  
1. Test full connection establishment flow
2. Test message delivery with retries
3. Test staging-specific timing scenarios
4. Test recovery from connection failures

### E2E Tests
1. Test complete user flow from app open to message receipt
2. Test Cloud Run cold start scenarios
3. Test load balancer WebSocket upgrade timing
4. Test multi-user concurrent connections

## Rollout Plan

### Stage 1: Development Environment
- Implement retry logic in UnifiedWebSocketManager
- Add comprehensive logging
- Run existing test suite

### Stage 2: Staging Environment  
- Deploy with enhanced retry settings
- Monitor connection success rates
- Validate Cloud Run cold start handling

### Stage 3: Production
- Gradual rollout with feature flag
- Monitor metrics closely
- Ready to rollback if issues arise

## Monitoring & Alerts

### Key Metrics
- `websocket.connection.attempts` - Number of retry attempts
- `websocket.connection.success_rate` - Percentage of successful connections
- `websocket.message.delivery_rate` - Message delivery success rate
- `websocket.connection.time` - Time to establish connection (p50, p95, p99)

### Alerts
- Connection success rate < 99%
- Message delivery rate < 99.5%  
- Connection time p99 > 5 seconds
- Retry attempts p95 > 2

## Rollback Plan
If issues arise:
1. Disable retry logic via feature flag
2. Revert to previous version
3. Analyze logs and metrics
4. Fix issues in development
5. Re-deploy with fixes

## Success Criteria
- Zero "No WebSocket connections found" errors in staging
- Connection success rate > 99.9%
- Message delivery rate > 99.95%
- No increase in connection establishment time p50
- Successful handling of Cloud Run cold starts

## Timeline
- Day 1: Implement retry logic and tests
- Day 2: Deploy to development and test
- Day 3: Deploy to staging with monitoring
- Day 4-5: Monitor staging metrics
- Day 6: Production deployment decision

## Risk Assessment
- **Low Risk:** Retry logic is additive, doesn't break existing flow
- **Medium Risk:** Potential for increased latency during retries
- **Mitigation:** Configurable retry settings, comprehensive monitoring