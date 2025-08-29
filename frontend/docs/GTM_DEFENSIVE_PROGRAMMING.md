# GTM Defensive Programming Guide

## Overview
This guide documents defensive programming patterns for Google Tag Manager (GTM) integration to prevent runtime errors from undefined property access.

## Problem Statement
GTM's internal scripts (loaded from Google's servers) may attempt to access properties on event data that don't exist, leading to errors like:
```
Uncaught TypeError: Cannot read properties of undefined (reading 'message_id')
```

## Solution Architecture

### Data Sanitization Layer
All data pushed to GTM must pass through a sanitization layer that:
1. Replaces undefined/null values with safe defaults
2. Ensures expected properties exist
3. Recursively sanitizes nested objects
4. Maintains data integrity while preventing errors

### Implementation Details

#### Sanitization Function
```typescript
const sanitizeDataForGTM = (data: Record<string, any>): Record<string, any> => {
  const sanitized: Record<string, any> = {};
  
  for (const [key, value] of Object.entries(data)) {
    if (value === undefined || value === null) {
      sanitized[key] = '';
    } else if (typeof value === 'object' && !Array.isArray(value)) {
      sanitized[key] = sanitizeDataForGTM(value);
    } else if (Array.isArray(value)) {
      sanitized[key] = value.map(item => 
        typeof item === 'object' && item !== null ? sanitizeDataForGTM(item) : item ?? ''
      );
    } else {
      sanitized[key] = value;
    }
  }
  
  return sanitized;
};
```

#### Required Properties for Common Events

##### Message Events
- `message_id`: Always required, generate if not provided
- `thread_id`: Default to 'no-thread' if undefined
- `user_id`: Default to 'anonymous' if undefined
- `session_id`: Default to 'no-session' if undefined

##### Authentication Events
- `user_id`: Required for tracking user journey
- `auth_method`: Should specify the authentication type
- `is_new_user`: Boolean flag for user segmentation

##### Engagement Events
- `event_category`: Must be 'engagement'
- `event_action`: Describes the specific action
- `timestamp`: ISO string timestamp

## Best Practices

### 1. Always Provide Defaults
```typescript
// Bad
events.trackEngagement('message_sent', {
  thread_id: threadId, // Could be undefined
  message_length: messageLength // Could be undefined
});

// Good
events.trackEngagement('message_sent', {
  thread_id: threadId || 'no-thread',
  message_length: messageLength || 0,
  message_id: messageId || `msg-${Date.now()}`
});
```

### 2. Type Safety with TypeScript
```typescript
interface EngagementEventData extends DataLayerEvent {
  thread_id?: string;
  message_id?: string; // Make GTM-required fields explicit
  message_length?: number;
}
```

### 3. Circuit Breaker Pattern
Use the GTM Circuit Breaker to prevent event flooding and infinite loops:
```typescript
const circuitBreaker = getGTMCircuitBreaker();
if (!circuitBreaker.canSendEvent(eventKey)) {
  return; // Skip event if circuit is open
}
```

### 4. Error Boundaries
Wrap GTM operations in try-catch blocks:
```typescript
try {
  window.dataLayer.push(sanitizedData);
} catch (error) {
  logger.error('GTM push failed', error);
  // Continue execution - don't let GTM errors break the app
}
```

## Testing Strategy

### Unit Tests
- Test sanitization with various data types
- Verify undefined/null handling
- Test nested object sanitization
- Validate array processing

### Integration Tests
- Test event tracking with missing properties
- Verify circuit breaker behavior
- Test error recovery
- Validate GTM script loading

### E2E Tests
- Monitor browser console for GTM errors
- Verify events reach GTM container
- Test with production GTM configuration
- Validate data layer state

## Common Pitfalls

### 1. Assuming Properties Exist
```typescript
// Dangerous - GTM might access event.data.message.id
pushEvent({ event: 'message', data: userData });

// Safe - Ensure all nested properties are defined
pushEvent(sanitizeDataForGTM({ 
  event: 'message', 
  data: userData || {} 
}));
```

### 2. Not Handling Script Load Failures
```typescript
// Always check if GTM is loaded
if (!window.dataLayer) {
  console.warn('GTM not loaded, skipping event');
  return;
}
```

### 3. Forgetting Message IDs
Message-related events MUST include a message_id to prevent GTM errors:
```typescript
const messageEvent = {
  event: 'message_sent',
  message_id: messageId || `msg-${Date.now()}`, // Always provide
  // ... other properties
};
```

## Monitoring and Debugging

### Development Mode
- Enable GTM debug mode: `debug: true`
- Monitor console for warnings/errors
- Use GTM Preview mode
- Check dataLayer state in browser console

### Production Monitoring
- Track GTM error events
- Monitor circuit breaker trips
- Log sanitization operations
- Alert on high error rates

## Related Documentation
- [GTM Testing Procedures](./GTM_TESTING_PROCEDURES.md)
- [GTM QA Strategy](./GTM_QA_STRATEGY_SUMMARY.md)
- [GTM QA Validation Checklist](./GTM_QA_VALIDATION_CHECKLIST.md)
- [Learnings: GTM Undefined Access](../../SPEC/learnings/gtm_undefined_access.xml)

## Version History
- v1.0.0 (2025-08-29): Initial defensive programming patterns
- Added comprehensive sanitization layer
- Implemented message_id requirements
- Created testing guidelines