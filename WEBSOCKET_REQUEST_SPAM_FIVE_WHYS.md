# WebSocket Request Spamming - Five Whys Analysis

## Problem Statement
The frontend starts spamming requests when logged in, particularly around token refresh operations, causing a cascade of WebSocket reconnection attempts.

## Five Whys Analysis

### 1st Why: Why is the frontend spamming requests?
**Answer**: The WebSocket is repeatedly attempting to reconnect after authentication errors, triggering rapid token refresh attempts.

**Evidence**: 
```
Error: Token refresh attempted too soon - preventing auth loop
    at o.refreshToken (3102-2462532a25652e2b.js:1:54231)
    at n.attemptTokenRefreshAndReconnect (9879-a6b462bb8c88a950.js:1:25112)
    at n.handleAuthError (9879-a6b462bb8c88a950.js:1:25009)
    at ws.onclose
```

### 2nd Why: Why is the WebSocket repeatedly attempting to reconnect?
**Answer**: The WebSocket connection is closing with authentication errors (code 1008 or similar), which triggers `handleAuthError()`, which then calls `attemptTokenRefreshAndReconnect()`.

**Evidence from code**:
```typescript
// webSocketService.ts
private handleAuthError(error: any): void {
    // ...
    if (!isSecurityViolation && this.options.refreshToken) {
      this.attemptTokenRefreshAndReconnect();
    }
}
```

### 3rd Why: Why is the WebSocket closing with authentication errors?
**Answer**: The token refresh is failing due to our new loop protection (2-second minimum interval), which throws an error, causing the WebSocket to interpret this as an auth failure and attempt another reconnect.

**Evidence**:
```typescript
// auth-service-client.ts
if (timeSinceLastRefresh < this.MIN_REFRESH_INTERVAL_MS) {
    throw new Error('Token refresh attempted too soon - preventing auth loop');
}
```

### 4th Why: Why does a failed token refresh trigger another immediate reconnect attempt?
**Answer**: The WebSocket service doesn't have proper backoff or coordination with the auth loop protection. When `attemptTokenRefreshAndReconnect()` fails, it doesn't increase the reconnect delay or check if we're already in a refresh cycle.

**Evidence from code**:
```typescript
// webSocketService.ts
private async attemptTokenRefreshAndReconnect(): Promise<void> {
    try {
      const newToken = await this.options.refreshToken!(); // This throws immediately
      // ...
    } catch (error) {
      // No backoff or delay handling here
      logger.error('Token refresh failed during auth error recovery', error as Error);
    }
}
```

### 5th Why: Why doesn't the WebSocket service coordinate with auth loop protection?
**Answer**: The auth loop protection was added independently to prevent refresh loops, but the WebSocket service wasn't updated to handle the new error type or coordinate its reconnection attempts with the auth service's refresh cooldown.

**Root Cause**: **Lack of coordination between WebSocket reconnection logic and auth refresh loop protection mechanisms.**

## Cascade Effect

1. WebSocket connects successfully with valid token
2. Token expires or WebSocket closes for network reasons
3. WebSocket `onclose` handler detects auth-related closure
4. Calls `handleAuthError()` → `attemptTokenRefreshAndReconnect()`
5. Token refresh throws "attempted too soon" error (our loop protection)
6. WebSocket interprets this as auth failure
7. Triggers another reconnection attempt immediately
8. Goes back to step 4, creating a rapid loop

## The Fix Required

### 1. Immediate Fix - Add Coordination
```typescript
// webSocketService.ts
private lastRefreshAttempt = 0;
private readonly MIN_REFRESH_INTERVAL = 2000;

private async attemptTokenRefreshAndReconnect(): Promise<void> {
    const now = Date.now();
    const timeSinceLastRefresh = now - this.lastRefreshAttempt;
    
    // Respect the auth service's cooldown
    if (timeSinceLastRefresh < this.MIN_REFRESH_INTERVAL) {
        const waitTime = this.MIN_REFRESH_INTERVAL - timeSinceLastRefresh;
        logger.debug(`Waiting ${waitTime}ms before token refresh attempt`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    this.lastRefreshAttempt = Date.now();
    
    try {
        const newToken = await this.options.refreshToken!();
        // ... rest of reconnection logic
    } catch (error) {
        if (error.message?.includes('preventing auth loop')) {
            // This is our loop protection - wait longer before retry
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
            logger.warn('Auth loop protection triggered, increasing reconnect delay');
        }
        // ... handle other errors
    }
}
```

### 2. Better Error Handling
- Distinguish between different types of auth errors
- Handle "too soon" errors differently from actual auth failures
- Implement exponential backoff for reconnection attempts

### 3. Shared State Management
- Create a shared auth state manager that both WebSocket and auth services use
- Track refresh attempts globally, not per-service
- Coordinate cooldown periods across all services

## Impact Analysis

### Current Impact:
- Rapid API calls consuming resources
- Browser console spam with errors
- Potential rate limiting from backend
- Poor user experience with connection instability
- Increased server load from constant reconnection attempts

### After Fix:
- Coordinated refresh attempts with proper cooldowns
- Clean error handling without console spam
- Stable WebSocket connections
- Better resource utilization
- Improved user experience

## Lessons Learned

1. **System Integration**: When adding protection mechanisms (like loop detection), all dependent systems must be updated to handle the new behavior
2. **Error Propagation**: Different error types need different handling strategies - not all errors should trigger the same recovery mechanism
3. **Coordination**: Services that interact with shared resources (like auth tokens) need coordinated retry strategies
4. **Testing**: Need integration tests that specifically test the interaction between WebSocket reconnection and auth refresh
5. **Monitoring**: Should add metrics to track refresh attempt frequency and WebSocket reconnection rates

## Critical Update (2025-01-03)

**IMPORTANT**: This issue was part of a larger architectural problem that was fully exposed when auth started working correctly.

### Connection Loop Root Cause Discovered
After fixing this auth refresh coordination issue, a more severe bug was discovered: the WebSocketProvider had **duplicate React effects** that would trigger simultaneous connection attempts whenever auth state changed. This created connection loops that were previously masked by broken auth.

### Related Documentation:
- **Root Cause Analysis**: `/WEBSOCKET_CONNECTION_LOOP_ROOT_CAUSE.md`
- **Complete Fix Report**: `/WEBSOCKET_CONNECTION_LOOP_COMPLETE_ANALYSIS.md`
- **SPEC Learning**: `/SPEC/learnings/websocket_connection_loop_ssot_fix.xml`

### Key Insight:
The request spamming fixed here was a symptom of deeper architectural issues. The real problem was lack of Single Source of Truth (SSOT) for WebSocket connection management in the React layer. When auth worked correctly, it triggered multiple effects that created connection loops.

### Current Status:
✅ **FULLY RESOLVED** - Both the auth coordination AND the underlying connection loop issues have been fixed through:
1. This fix: Auth refresh coordination with cooldown periods
2. SSOT fix: Consolidated React effects in WebSocketProvider
3. Connection deduplication in WebSocketService