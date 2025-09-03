# GCP Error Reporting Architecture

## Overview

This document describes the comprehensive GCP Error Reporting integration implemented for the Netra Apex platform, ensuring critical errors are properly surfaced in GCP Cloud Run's error reporting dashboard while maintaining local error handling capabilities.

## Business Value Justification (BVJ)

- **Segment:** Platform/Internal
- **Business Goal:** Platform Stability, Risk Reduction
- **Value Impact:** Dramatically improves incident response time and system reliability by providing real-time visibility into production errors
- **Strategic Impact:** Reduces MTTR (Mean Time To Resolution) from hours to minutes, enabling proactive issue resolution before customer impact

## Architecture Components

### 1. Core GCP Error Reporter Module

**Location:** `/netra_backend/app/services/monitoring/gcp_error_reporter.py`

#### Key Features:
- **Singleton Pattern:** Ensures centralized error reporting across the application
- **Automatic Environment Detection:** Uses `K_SERVICE` environment variable to detect Cloud Run
- **Rate Limiting:** Prevents error flooding (100 errors/minute maximum)
- **Context Preservation:** Maintains user, trace, and HTTP request context
- **Global Exception Handlers:** Catches both synchronous and asynchronous unhandled exceptions
- **Middleware Integration:** Seamlessly integrates with FastAPI request lifecycle

#### Implementation Details:
```python
class GCPErrorReporter:
    """
    Singleton error reporter with:
    - Auto-initialization in GCP environments
    - Graceful fallback to logging
    - Rate limiting protection
    - Context management
    """
```

### 2. Enhanced Exception Framework

**Location:** `/netra_backend/app/core/exceptions_base.py`

#### Automatic Reporting:
- `NetraException` base class enhanced with `report_to_gcp` parameter
- HIGH and CRITICAL severity exceptions auto-report on creation
- Full context preservation including trace IDs and error details

#### Exception Hierarchy:
```
NetraException (Base)
├── ValidationError
├── AuthenticationError
├── WebSocketError (HIGH severity → auto-reports)
├── DatabaseConnectionError (CRITICAL → auto-reports)
└── SystemCriticalError (CRITICAL → auto-reports)
```

### 3. Decorator Pattern for Critical Functions

**Location:** Available via `from netra_backend.app.services.monitoring.gcp_error_reporter import gcp_reportable`

#### Usage:
```python
@gcp_reportable(severity=Severity.ERROR, reraise=True)
async def critical_operation():
    """Function automatically reports exceptions to GCP"""
    pass
```

#### Features:
- Configurable severity levels
- Optional exception re-raising
- Context capture (function name, parameters)
- Async and sync function support

### 4. FastAPI Integration

**Location:** `/netra_backend/app/core/app_factory.py`

#### Integration Points:
1. **Global Exception Handlers:** Installed during app initialization
2. **Middleware:** `GCPErrorReportingMiddleware` for request context
3. **WebSocket Support:** Special handling for WebSocket connections
4. **Graceful Degradation:** Falls back to logging if GCP unavailable

### 5. WebSocket Error Reporting

**Location:** `/netra_backend/app/routes/websocket.py`

#### Enhanced Features:
- `@gcp_reportable` decorator on main WebSocket endpoint
- Request context establishment for WebSocket connections
- Proper context cleanup on disconnect
- Error categorization by WebSocket event type

## Error Flow Diagram

```mermaid
flowchart TD
    A[Application Error Occurs] --> B{Error Type?}
    
    B -->|Unhandled Exception| C[Global Exception Handler]
    B -->|HIGH/CRITICAL NetraException| D[Auto-Report on Creation]
    B -->|Decorated Function| E[@gcp_reportable Captures]
    B -->|Manual Report| F[report_exception() Called]
    
    C --> G[GCPErrorReporter]
    D --> G
    E --> G
    F --> G
    
    G --> H{GCP Available?}
    H -->|Yes| I[Report to GCP Error Reporting]
    H -->|No| J[Fallback to Local Logging]
    
    I --> K[GCP Console Dashboard]
    J --> L[Application Logs]
    
    G --> M{Rate Limit Check}
    M -->|Under Limit| N[Process Error]
    M -->|Over Limit| O[Skip Reporting]
```

## Configuration

### Environment Variables
```bash
# Automatic detection in GCP Cloud Run
K_SERVICE=<service-name>  # Set automatically by Cloud Run

# Optional configuration
GCP_PROJECT_ID=netra-staging  # Override project ID
GCP_ERROR_REPORTING_ENABLED=true  # Force enable/disable
```

### Service Account Requirements
- Role: `roles/errorreporting.writer`
- Automatically provided in Cloud Run environment

## Testing Infrastructure

### Test Endpoints

**Location:** `/netra_backend/app/routes/test_gcp_errors.py`

Available at `/test/gcp-errors/` in staging/development:

1. **`/test/gcp-errors/unhandled`** - Triggers unhandled exception
2. **`/test/gcp-errors/handled`** - Demonstrates handled error reporting
3. **`/test/gcp-errors/decorated`** - Tests @gcp_reportable decorator
4. **`/test/gcp-errors/cascading`** - Tests error propagation
5. **`/test/gcp-errors/verify`** - Checks reporter setup status

### Verification Process
```bash
# Test in staging
curl https://staging.netra-apex.com/test/gcp-errors/verify

# Trigger test error
curl https://staging.netra-apex.com/test/gcp-errors/unhandled

# Check GCP Console
# Navigate to: Error Reporting → Select time range → View errors
```

## Cross-References

### Related Documentation
- [`/USER_CONTEXT_ARCHITECTURE.md`](../USER_CONTEXT_ARCHITECTURE.md) - User isolation and context management
- [`/docs/configuration_architecture.md`](./configuration_architecture.md) - Environment configuration patterns
- [`/WEBSOCKET_MODERNIZATION_REPORT.md`](../WEBSOCKET_MODERNIZATION_REPORT.md) - WebSocket error handling
- [`/docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md`](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md) - Agent error propagation

### Related Specifications
- [`/SPEC/learnings/websocket_agent_integration_critical.xml`](../SPEC/learnings/websocket_agent_integration_critical.xml) - WebSocket error patterns
- [`/SPEC/core.xml`](../SPEC/core.xml) - Core error handling principles
- [`/SPEC/unified_environment_management.xml`](../SPEC/unified_environment_management.xml) - Environment detection

## Implementation Checklist

### Initial Setup ✅
- [x] Create GCPErrorReporter singleton
- [x] Implement automatic GCP environment detection
- [x] Add rate limiting protection
- [x] Create @gcp_reportable decorator

### Exception Framework ✅
- [x] Enhance NetraException with report_to_gcp
- [x] Add severity-based auto-reporting
- [x] Preserve full error context

### FastAPI Integration ✅
- [x] Install global exception handlers
- [x] Add GCP middleware
- [x] Handle async exceptions
- [x] Support WebSocket errors

### Testing ✅
- [x] Create test endpoints
- [x] Add verification endpoint
- [x] Test in staging environment
- [x] Verify GCP Console visibility

## Best Practices

### When to Report to GCP

**Always Report:**
- Unhandled exceptions
- Database connection failures
- Authentication/authorization errors
- Critical business logic failures
- WebSocket connection errors
- Agent execution failures

**Don't Report:**
- User input validation errors
- Expected business rule violations
- Rate limit violations
- Gracefully handled retries

### Error Context

Always include:
- User ID (if available)
- Trace ID
- Request method and path
- Relevant business context
- Stack trace

### Error Messages

```python
# Good: Specific and actionable
raise DatabaseConnectionError(
    "PostgreSQL connection failed after 3 retries",
    details={"host": "localhost", "port": 5432, "attempts": 3}
)

# Bad: Generic and unhelpful
raise Exception("Database error")
```

## Monitoring and Alerting

### GCP Console Access
1. Navigate to [GCP Console](https://console.cloud.google.com)
2. Select project (netra-staging/netra-production)
3. Go to Error Reporting
4. Filter by service, time range, or error type

### Key Metrics
- Error rate per minute
- Error distribution by type
- User impact (affected user count)
- Error trends over time

### Alert Configuration
Configure alerts in GCP for:
- Error rate > 10/minute
- New error types
- Critical severity errors
- Specific error patterns

## Troubleshooting

### Common Issues

1. **Errors not appearing in GCP:**
   - Check K_SERVICE environment variable
   - Verify service account permissions
   - Check rate limiting (100/minute max)
   - Confirm GCP libraries installed

2. **Too many errors reported:**
   - Adjust severity thresholds
   - Use rate limiting
   - Filter expected errors

3. **Missing context:**
   - Ensure middleware is installed
   - Check context propagation in async code
   - Verify trace ID generation

## Future Enhancements

### Planned Improvements
1. **Error Grouping:** Custom fingerprinting for better error grouping
2. **User Impact Analysis:** Track affected user segments
3. **Error Recovery:** Automatic retry and recovery mechanisms
4. **Performance Impact:** Correlate errors with performance metrics
5. **Custom Dashboards:** Business-specific error dashboards

### Integration Opportunities
1. **Slack/Discord Notifications:** Real-time critical error alerts
2. **JIRA Integration:** Automatic ticket creation for critical errors
3. **Grafana Dashboards:** Unified monitoring dashboard
4. **PagerDuty Integration:** On-call engineer alerting

## Conclusion

The GCP Error Reporting integration provides comprehensive error visibility while maintaining application performance and reliability. The system automatically detects and reports critical errors, preserves full context, and provides actionable insights for rapid issue resolution.

This architecture aligns with our core principle of "Platform Stability" and directly supports our business goal of maintaining high availability and reliability for enterprise customers.