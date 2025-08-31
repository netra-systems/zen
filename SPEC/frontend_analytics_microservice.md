# Frontend Analytics and Event Capture Microservice

## Executive Summary

A comprehensive analytics microservice that extends GTM capabilities to capture, process, and analyze frontend user events, providing actionable insights on AI optimization platform usage, user behavior patterns, and product engagement metrics.

**Business Value:**
- **Segments:** Early, Mid, Enterprise
- **Goal:** Customer Insights, Product Optimization, Retention
- **Impact:** Deep visibility into user behavior and AI usage patterns
- **Revenue Impact:** 20% reduction in churn, 15% increase in feature adoption

## Event Taxonomy

### User Interaction Events

#### chat_interaction
- `thread_id` (string, required): Unique chat thread identifier
- `message_id` (string, required): Individual message identifier  
- `message_type` (enum, required): user_prompt | ai_response | system_message
- `prompt_text` (string): User's prompt text (sanitized)
- `prompt_length` (integer, required): Character count of prompt
- `response_length` (integer): Character count of AI response
- `response_time_ms` (float): Time to receive response
- `model_used` (string): AI model identifier
- `tokens_consumed` (integer): Token count for request
- `is_follow_up` (boolean, required): Whether this is a follow-up question

#### thread_lifecycle
- `thread_id` (string, required)
- `action` (enum, required): created | continued | completed | abandoned
- `message_count` (integer): Total messages in thread
- `duration_seconds` (float): Thread duration

#### feature_usage
- `feature_name` (string, required): Feature identifier
- `action` (string, required): Specific action taken
- `success` (boolean, required): Whether action succeeded
- `error_code` (string): Error code if failed
- `duration_ms` (float): Action duration

### Survey and Feedback Events

#### survey_response
- `survey_id` (string, required): Survey campaign identifier
- `question_id` (string, required): Individual question identifier
- `question_type` (enum, required): pain_perception | magic_wand | spending | planning
- `response_value` (string): Response text or value
- `response_scale` (integer): Numeric scale response (1-10)
- `ai_spend_last_month` (float): Reported AI spending
- `ai_spend_next_quarter` (float): Planned AI spending

#### feedback_submission
- `feedback_type` (enum, required): nps | csat | feature_request | bug_report
- `score` (integer): Numeric score if applicable
- `comment` (string): Free text feedback
- `context_thread_id` (string): Related thread if applicable

### Technical Events

#### performance_metric
- `metric_type` (enum, required): page_load | api_call | websocket | render
- `duration_ms` (float, required): Operation duration
- `success` (boolean, required): Whether operation succeeded
- `error_details` (string): Error information if failed

#### error_tracking
- `error_type` (string, required): Error classification
- `error_message` (string, required): Error message
- `stack_trace` (string): Stack trace if available
- `user_impact` (enum, required): critical | high | medium | low

## Data Architecture

### ClickHouse Tables

#### frontend_events
```sql
CREATE TABLE IF NOT EXISTS frontend_events (
  event_id UUID DEFAULT generateUUIDv4(),
  timestamp DateTime64(3) DEFAULT now(),
  user_id String,
  session_id String,
  event_type String,
  event_category String,
  event_action String,
  event_label String,
  event_value Float64,
  
  -- Event-specific properties as JSON
  properties String, -- JSON string with event-specific data
  
  -- User context
  user_agent String,
  ip_address String, -- Hashed for privacy
  country_code String,
  
  -- Page context  
  page_path String,
  page_title String,
  referrer String,
  
  -- Technical metadata
  gtm_container_id String,
  environment String,
  app_version String,
  
  -- Computed fields
  date Date DEFAULT toDate(timestamp),
  hour UInt8 DEFAULT toHour(timestamp)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, timestamp, event_id)
TTL timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;
```

#### user_analytics_summary (Materialized View)
```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS user_analytics_summary
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, date)
AS SELECT
  user_id,
  toDate(timestamp) as date,
  count() as total_events,
  countIf(event_type = 'chat_interaction') as chat_interactions,
  countIf(event_type = 'thread_lifecycle' AND event_action = 'created') as threads_created,
  countIf(event_type = 'feature_usage') as feature_interactions,
  sumIf(event_value, event_type = 'chat_interaction') as total_tokens_consumed,
  avgIf(event_value, event_type = 'performance_metric') as avg_response_time
FROM frontend_events
GROUP BY user_id, date;
```

#### prompt_analytics
```sql
CREATE TABLE IF NOT EXISTS prompt_analytics (
  prompt_id UUID DEFAULT generateUUIDv4(),
  timestamp DateTime64(3) DEFAULT now(),
  user_id String,
  thread_id String,
  
  -- Prompt details
  prompt_hash String, -- Hash for deduplication
  prompt_category String, -- ML-classified category
  prompt_intent String, -- Detected user intent
  prompt_complexity_score Float32,
  
  -- Response metrics
  response_quality_score Float32,
  response_relevance_score Float32,
  follow_up_generated Boolean,
  
  -- Usage patterns
  is_repeat_question Boolean,
  similar_prompts Array(String), -- IDs of similar prompts
  
  -- Cost tracking
  estimated_cost_cents Float32,
  actual_cost_cents Float32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, timestamp, prompt_id)
TTL timestamp + INTERVAL 180 DAY;
```

### Redis Structures

- **user_session_cache** (Hash, TTL: 3600s): Active user session data for real-time personalization
- **event_rate_limiter** (Sorted Set, TTL: 60s): Rate limiting for event ingestion per user
- **real_time_metrics** (Time Series, TTL: 86400s): Real-time metrics for dashboard updates
- **hot_prompts_cache** (List, TTL: 1800s): Recently popular prompts for trend analysis

## GTM Integration

### Custom Tag: NetraAnalyticsTag
```javascript
// Custom JavaScript tag for enhanced event capture
(function() {
  window.netraAnalytics = window.netraAnalytics || {};
  
  // Enhanced event push function
  window.netraAnalytics.push = function(eventData) {
    // Enrich with session context
    eventData.session_id = window.netraAnalytics.sessionId || generateSessionId();
    eventData.timestamp = new Date().toISOString();
    
    // Push to dataLayer for GTM
    window.dataLayer.push({
      event: 'netra_analytics_event',
      ...eventData
    });
    
    // Also send to analytics service
    sendToAnalyticsService(eventData);
  };
  
  // Auto-capture chat interactions
  document.addEventListener('netra_chat_message', function(e) {
    window.netraAnalytics.push({
      event_type: 'chat_interaction',
      ...e.detail
    });
  });
})();
```

## API Endpoints

### POST /api/analytics/events
Ingest events from frontend
- **Rate Limit:** 1000 events per minute per user
- **Request Schema:**
```json
{
  "events": [
    {
      "event_type": "string",
      "timestamp": "ISO8601",
      "properties": {}
    }
  ],
  "context": {
    "user_id": "string",
    "session_id": "string",
    "page_path": "string"
  }
}
```

### GET /api/analytics/reports/user-activity
Get user activity summary
- `user_id` (string, optional)
- `start_date` (date, required)
- `end_date` (date, required)
- `granularity` (enum): hour | day | week | month

### GET /api/analytics/reports/prompts
Analyze prompt patterns and trends
- `category` (string, optional)
- `min_frequency` (integer, default: 5)
- `time_range` (enum): 1h | 24h | 7d | 30d

## Analytics Reports

### User Engagement Dashboard
**Real-time user engagement metrics**
- Active users (5-minute window)
- Active chat sessions
- Average AI response time
- Error rate percentage

### Prompt Intelligence Report
**Analysis of user prompts and AI interactions**
- Most frequently asked questions
- Follow-up question rate
- Prompt category distribution
- Prompt complexity trends

### User Journey Analysis
**Track user progression through the platform**
- **Onboarding Funnel:** Sign up → First chat → Feature discovery → Regular usage
- **Value Realization Funnel:** First interaction → Complex query → Cost savings identified
- Weekly cohort retention and engagement analysis

### AI Spend Analytics
**Track and analyze AI spending patterns**
- Total AI spend across users
- Average spend per active user
- Cost per successful outcome
- Projected spend based on usage trends

## Grafana Dashboards

### Executive Overview
- Active Users (Real-time)
- Chat Volume (24h)
- Top Features by Usage
- System Health Score

### Prompt Analytics
- Common Terms Word Cloud
- Usage Patterns Heatmap
- Follow-up Question Rate
- Unanswered Questions Table

### User Behavior
- User Journey Sankey Diagram
- Cohort Retention Graph
- User Segments Pie Chart
- Average Session Duration

## Privacy Compliance


### Retention Policies
- Event data: 90 days
- Aggregated metrics: 2 years
- User identifiers: Until account deletion


## Implementation Plan

### Phase 1: Foundation (1 week)
- Set up analytics microservice structure
- Create ClickHouse tables and Redis structures
- Implement basic event ingestion API
- Extend GTM configuration

### Phase 2: Integration (1 week)
- Integrate with frontend event capture
- Implement event processing pipeline
- Create materialized views for analytics
- Set up Grafana datasources

### Phase 3: Analytics (2 weeks)
- Build Grafana dashboards
- Implement report generation APIs
- Create prompt intelligence analysis
- Set up alerting rules

### Phase 4: Optimization (1 week)
- Performance tuning and caching
- Implement advanced analytics features
- Add survey and feedback capture
- Complete privacy compliance features

## Testing Strategy

### Event Capture
- Verify all event types are captured correctly
- Test rate limiting and throttling
- Validate event enrichment logic

### Data Processing
- Test event processing pipeline
- Verify data storage in ClickHouse
- Test Redis caching mechanisms

### Analytics
- Validate report generation accuracy
- Test materialized view updates
- Verify dashboard data freshness

### Performance
- Load test with 10,000 events/second
- Test query performance on large datasets
- Verify real-time update latency < 1s

## Monitoring

### Key Metrics
- `event_ingestion_rate`: Events processed per second
- `processing_latency`: Time from event capture to storage
- `query_performance`: P95 query response time
- `storage_usage`: ClickHouse and Redis storage consumption
- `api_availability`: Uptime percentage of analytics API

### Health Checks
- ClickHouse connectivity verification
- Redis connectivity verification
- GTM tag firing verification
- Data freshness check (latest event timestamp)

## Configuration

### Environment Variables
```bash
ANALYTICS_SERVICE_PORT=8090
CLICKHOUSE_ANALYTICS_URL=clickhouse://localhost:8123/analytics
REDIS_ANALYTICS_URL=redis://localhost:6379/2
GRAFANA_API_URL=TBD
EVENT_BATCH_SIZE=100
EVENT_FLUSH_INTERVAL_MS=5000
MAX_EVENTS_PER_USER_PER_MINUTE=1000
```

## Dependencies

- GTM Provider: EXISTING Frontend GTM integration
- ClickHouse: EXISTING Time-series data storage
- Redis: EXISTING Real-time caching
- Grafana: Visualization and dashboards
- Auth Service: EXISTING User authentication and identification