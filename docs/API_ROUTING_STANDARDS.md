# API Routing Standards and Consistency Guide

## Overview
This document defines the routing standards for the Netra API to ensure consistency between implementation and E2E test expectations.

## Routing Mismatch Resolution

### Problem Identified
E2E tests expected endpoints at different paths than the actual implementation:
- Tests expected `/api/messages` but routes were at `/api/chat/messages`
- Tests expected `/api/events` but only `/api/events/stream` existed
- Tests expected `/api/agents/*` which correctly matched actual routes

### Solution Implemented
Created compatibility layer to support both E2E test expectations and logical API organization.

## Current Routing Configuration

### Messages API
- **Root Compatibility**: `/api/messages` → Information and redirect endpoints
- **Actual Implementation**: `/api/chat/messages` → Full message CRUD operations
- **Streaming**: `/api/chat/stream` → Real-time chat streaming

**Router Configuration:**
```python
"messages": (messages_router, "/api/chat", ["messages"])
"messages_root": (messages_root_router, "/api/messages", ["messages-root"])
```

### Agents API
- **Root**: `/api/agents`
- **Execution**: `/api/agents/execute`, `/api/agents/triage`, `/api/agents/data`, `/api/agents/optimization`
- **Control**: `/api/agents/start`, `/api/agents/stop`, `/api/agents/cancel`, `/api/agents/status`
- **Streaming**: `/api/agents/stream`

**Router Configuration:**
```python
"agents_execute": (agents_execute_router, "/api/agents", ["agents"])
```

### Events API  
- **Root**: `/api/events` → Events API information
- **Streaming**: `/api/events/stream` → Server-Sent Events
- **Info**: `/api/events/info` → Stream capabilities

**Router Configuration:**
```python
"events_stream": (events_stream_router, "/api/events", ["events"])
```

## Routing Standards

### 1. E2E Test Compatibility
- All endpoints expected by E2E tests MUST exist
- Root endpoints (e.g., `/api/messages`, `/api/events`) should provide API information
- Compatibility endpoints should redirect or proxy to actual implementations

### 2. Logical API Organization  
- Related functionality should be grouped under logical prefixes
- Chat/messaging functionality under `/api/chat/*`
- Agent operations under `/api/agents/*`
- Event streaming under `/api/events/*`

### 3. Router Naming Convention
- Router variables: `{feature}_router` (e.g., `messages_router`, `agents_execute_router`)
- Router configurations: descriptive names in route configs
- Tags: match the primary functionality (e.g., `["messages"]`, `["agents"]`)

### 4. Endpoint Patterns

#### Root Information Endpoints
```python
@router.get("/")
async def get_{service}_root():
    """Root endpoint providing service information."""
    return {
        "service": "{service}-api",
        "status": "available", 
        "endpoints": {...},
        "features": {...}
    }
```

#### Health Check Endpoints
```python
@router.get("/health")
async def {service}_health():
    """Health check for the service."""
    return {"status": "healthy", "service": "{service}"}
```

#### Authentication Requirements
- All endpoints should use consistent authentication patterns
- Optional authentication for info/health endpoints
- Required authentication for data operations

## File Organization

### Route Files Location
- Main routes: `/netra_backend/app/routes/{feature}.py`
- Compatibility routes: `/netra_backend/app/routes/{feature}_root.py`
- Import configuration: `/netra_backend/app/core/app_factory_route_imports.py`
- Route configuration: `/netra_backend/app/core/app_factory_route_configs.py`

### Route Configuration Pattern
```python
def _get_api_route_configs(modules: dict) -> dict:
    """Get API route configurations."""
    return {
        "feature_main": (modules["feature_router"], "/api/feature/specific", ["feature"]),
        "feature_root": (modules["feature_root_router"], "/api/feature", ["feature-root"]),
    }
```

## Testing Standards

### Route Validation Tests
- Location: `/tests/unit/test_routing_validation.py`
- Validates all expected endpoints exist
- Checks backwards compatibility
- Ensures no 404 errors on critical endpoints

### E2E Test Expectations
Critical endpoints that E2E tests depend on:
- `/api/messages` (compatibility)
- `/api/agents/execute`
- `/api/agents/triage` 
- `/api/agents/data`
- `/api/agents/optimization`
- `/api/events` (compatibility)

## Implementation Checklist

When adding new API endpoints:

- [ ] Define router in appropriate `/routes/{feature}.py` file
- [ ] Add router import to `app_factory_route_imports.py`
- [ ] Configure routing in `app_factory_route_configs.py`
- [ ] Add root endpoint if needed for E2E compatibility
- [ ] Update routing validation tests
- [ ] Document endpoints in this standards file
- [ ] Test with actual E2E test suite

## Migration Guide

### Adding New Routes
1. Create router file: `/routes/new_feature.py`
2. Implement endpoints with consistent patterns
3. Add to route imports and configuration
4. Create root compatibility endpoint if needed
5. Add validation tests
6. Update documentation

### Modifying Existing Routes
1. Check E2E test dependencies first
2. Maintain backwards compatibility
3. Update route configuration if needed
4. Update validation tests
5. Update documentation

## Known Issues Resolved

### Messages Routing Mismatch (FIXED)
- **Issue**: E2E tests expected `/api/messages` but implementation was at `/api/chat/messages`
- **Solution**: Added `messages_root_router` at `/api/messages` for compatibility
- **Status**: ✅ Resolved

### Events Root Endpoint Missing (FIXED)
- **Issue**: E2E tests expected `/api/events` but only `/api/events/stream` existed
- **Solution**: Added root endpoint at `/api/events` providing API information
- **Status**: ✅ Resolved

### Agents Routing (VERIFIED)
- **Issue**: None - correctly implemented at `/api/agents/*`
- **Status**: ✅ Working correctly

## Validation Results

```
Messages routes:
  messages: prefix="/api/chat"
  messages_root: prefix="/api/messages"
Agents routes:
  agents_execute: prefix="/api/agents"  
Events routes:
  events_stream: prefix="/api/events"

Routing validation:
  ✅ /api/messages available: True
  ✅ /api/agents/* available: True  
  ✅ /api/events/* available: True
```

## Future Considerations

1. **API Versioning**: Consider `/v1/api/*` prefixes for future versions
2. **OpenAPI Documentation**: Ensure all routes are properly documented
3. **Performance**: Monitor route resolution performance as API grows
4. **Security**: Implement consistent rate limiting and authentication
5. **Deprecation Strategy**: Plan for deprecating compatibility endpoints

---

*This document should be updated whenever routing changes are made to maintain consistency between implementation and test expectations.*