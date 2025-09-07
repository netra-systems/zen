# Analytics Backend Integration Plan: Dual-Tracking Architecture

## Executive Summary

This plan outlines the implementation of a dual-tracking analytics system that sends all events to both:
1. **Frontend Services** (Statsig + GTM) - For product analytics and marketing
2. **Backend Analytics** (ClickHouse) - For our own data ownership and analysis

**Key Principle**: "Trust but verify" - We use 3rd party services for convenience but maintain our own analytics database for data sovereignty, compliance, and deep analysis.

## Current State Analysis

### Existing Infrastructure

1. **Frontend Analytics** (Already Implemented):
   - Statsig: Product analytics, A/B testing, feature flags
   - GTM: Marketing analytics, conversion tracking
   - Unified analytics service at `frontend/services/analyticsService.ts`

2. **Backend Infrastructure**:
   - ClickHouse database available and configured
   - Circuit breaker protection for resilience
   - User-isolated caching system
   - Query interceptor for SQL safety
   - Located at `netra_backend/app/db/clickhouse.py`

3. **Missing Piece**: No connection between frontend events and backend ClickHouse storage

## Proposed Architecture

### High-Level Flow

```mermaid
graph LR
    User[User Action] --> UA[useAnalytics Hook]
    UA --> AS[Analytics Service]
    
    AS --> SG[Statsig Client]
    AS --> GTM[GTM dataLayer]
    AS --> BAC[Backend Analytics Client]
    
    BAC --> AQ[Analytics Queue]
    AQ --> Batch[Batch Processor]
    Batch --> API[/api/analytics/events]
    
    API --> Val[Event Validator]
    Val --> CH[ClickHouse Writer]
    CH --> DB[(ClickHouse DB)]
    
    DB --> Dash[Analytics Dashboard]
    DB --> ML[ML/AI Analysis]
    DB --> Audit[Audit Trail]
```

### Component Design

#### 1. Frontend: Enhanced Analytics Service

```typescript
// frontend/services/analyticsService.ts additions
interface BackendAnalyticsConfig {
  enabled: boolean;
  endpoint: string;
  batchSize: number;
  flushInterval: number;
  maxRetries: number;
}

class BackendAnalyticsClient {
  private queue: AnalyticsEvent[] = [];
  private flushTimer?: NodeJS.Timeout;
  
  async trackEvent(event: EnrichedAnalyticsEvent): Promise<void> {
    // Add to queue
    // Trigger flush if batch size reached
    // Handle failures with exponential backoff
  }
}
```

#### 2. Backend: Analytics API Endpoint

```python
# netra_backend/app/routes/analytics.py
@router.post("/api/analytics/events")
async def ingest_analytics_events(
    events: List[AnalyticsEvent],
    current_user: User = Depends(get_current_user),
    clickhouse: ClickHouseDatabase = Depends(get_clickhouse_client)
):
    """Ingest analytics events from frontend."""
    # Validate events
    # Enrich with server-side data
    # Write to ClickHouse
    # Return acknowledgment
```

#### 3. ClickHouse Schema

```sql
CREATE TABLE IF NOT EXISTS analytics.events (
    -- Event identifiers
    event_id UUID DEFAULT generateUUIDv4(),
    event_name String,
    event_timestamp DateTime64(3) DEFAULT now64(3),
    
    -- User context
    user_id String,
    session_id String,
    
    -- Event data
    event_value Nullable(String),
    event_metadata JSON,
    
    -- Message tracking (for chat events)
    message_content Nullable(String),
    message_length Nullable(UInt32),
    thread_id Nullable(String),
    
    -- Technical metadata
    client_timestamp DateTime64(3),
    server_timestamp DateTime64(3) DEFAULT now64(3),
    ip_address IPv6,
    user_agent String,
    
    -- Partitioning and ordering
    date Date DEFAULT toDate(event_timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, event_timestamp);

-- Materialized views for common queries
CREATE MATERIALIZED VIEW analytics.daily_user_events
ENGINE = SummingMergeTree()
PARTITION BY date
ORDER BY (date, user_id, event_name)
AS SELECT
    date,
    user_id,
    event_name,
    count() as event_count,
    uniq(session_id) as session_count
FROM analytics.events
GROUP BY date, user_id, event_name;
```

## Implementation Phases

### Phase 1: Backend Infrastructure (Week 1)

1. **Create Analytics Tables**:
   - Main events table
   - Materialized views for performance
   - Retention policies (GDPR compliance)

2. **Build Ingestion API**:
   - Event validation schemas
   - Batch ingestion endpoint
   - Error handling and monitoring

3. **Security Layer**:
   - Event sanitization
   - PII detection and masking
   - Rate limiting per user

### Phase 2: Frontend Integration (Week 2)

1. **Enhance Analytics Service**:
   - Add `BackendAnalyticsClient` class
   - Implement event queuing and batching
   - Add retry logic with circuit breaker

2. **Configuration Management**:
   - Feature flags for gradual rollout
   - Environment-specific endpoints
   - Adjustable batch sizes

3. **Error Handling**:
   - Graceful degradation if backend unavailable
   - Local storage for offline events
   - Telemetry for monitoring

### Phase 3: Monitoring & Optimization (Week 3)

1. **Observability**:
   - Analytics pipeline dashboard
   - Event ingestion metrics
   - Data quality monitors

2. **Performance Optimization**:
   - Compression for event batches
   - Connection pooling
   - Query optimization

3. **Testing**:
   - End-to-end integration tests
   - Load testing for scale
   - Data consistency validation

## Security & Privacy Considerations

### Data Handling

1. **Message Content Security**:
   ```typescript
   // Sensitive data detection
   const sanitizeMessageContent = (content: string): string => {
     // Detect and mask: SSNs, credit cards, API keys, etc.
     // Configurable rules per environment
     return sanitizedContent;
   };
   ```

2. **User Consent**:
   - Honor user privacy settings
   - Provide data export/deletion APIs
   - Implement retention policies

3. **Access Control**:
   - Role-based access to analytics data
   - Audit trail for data access
   - Encryption at rest and in transit

### Compliance

1. **GDPR/CCPA**:
   - User right to deletion
   - Data portability
   - Consent management

2. **SOC2**:
   - Audit logging
   - Access controls
   - Data retention policies

## Benefits of Dual Tracking

1. **Data Ownership**:
   - Complete control over analytics data
   - No vendor lock-in
   - Custom analysis possibilities

2. **Advanced Analytics**:
   - Complex queries across all data
   - ML/AI on conversation patterns
   - Cost optimization insights

3. **Reliability**:
   - Backup if 3rd party services fail
   - Historical data preservation
   - Cross-validation of metrics

4. **Business Intelligence**:
   - Custom dashboards
   - Real-time alerting
   - Predictive analytics

## Migration Strategy

### Gradual Rollout

1. **Stage 1: Shadow Mode** (No user impact)
   - Send 1% of events to backend
   - Monitor performance and accuracy
   - Fix any issues

2. **Stage 2: Partial Traffic** (Low risk)
   - Increase to 10% of events
   - Compare with Statsig/GTM data
   - Optimize performance

3. **Stage 3: Full Traffic** (Production ready)
   - Send 100% of events
   - Enable advanced features
   - Deprecate any legacy tracking

### Rollback Plan

- Feature flag to disable backend tracking instantly
- Queue drainage to prevent data loss
- Monitoring alerts for issues

## Success Metrics

1. **Technical Metrics**:
   - Event ingestion latency < 500ms (p95)
   - Zero data loss (99.99% delivery)
   - < 0.1% impact on frontend performance

2. **Business Metrics**:
   - 100% event coverage vs Statsig/GTM
   - New insights discovered from data
   - Reduced analytics costs over time

3. **Quality Metrics**:
   - Data accuracy validation
   - Schema compliance rate
   - Error rate < 0.01%

## Next Steps

1. **Immediate Actions**:
   - Review and approve this plan
   - Allocate engineering resources
   - Set up ClickHouse development environment

2. **Week 1 Deliverables**:
   - Analytics schema deployed
   - Basic ingestion API working
   - Security measures in place

3. **Success Criteria**:
   - First event successfully stored in ClickHouse
   - End-to-end test passing
   - Performance benchmarks met

## Appendix: Example Implementation

### Frontend Event Enhancement

```typescript
// Before sending to backend, enrich events
const enrichEventForBackend = (event: AnalyticsEvent): EnrichedAnalyticsEvent => {
  return {
    ...event,
    client_timestamp: new Date().toISOString(),
    session_id: getSessionId(),
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight
    },
    // Include message content for chat events
    message_content: event.metadata?.message_content,
    // Add any other backend-specific fields
  };
};
```

### Backend Event Processing

```python
async def process_analytics_events(
    events: List[AnalyticsEvent],
    user_id: str,
    request: Request
) -> None:
    """Process and store analytics events."""
    
    # Enrich with server-side data
    enriched_events = []
    for event in events:
        enriched = {
            **event.dict(),
            "user_id": user_id,
            "server_timestamp": datetime.utcnow(),
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
        }
        
        # Sanitize sensitive data
        if enriched.get("message_content"):
            enriched["message_content"] = sanitize_message_content(
                enriched["message_content"]
            )
        
        enriched_events.append(enriched)
    
    # Batch insert to ClickHouse
    await clickhouse_client.insert_events(enriched_events)
```

---

**Document Status**: Ready for Review  
**Author**: Analytics Architecture Team  
**Date**: 2024-01-26  
**Version**: 1.0