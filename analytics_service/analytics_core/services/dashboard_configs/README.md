# Grafana Dashboard Configurations

This directory contains JSON configurations for Grafana dashboards used in the Netra Analytics platform.

## Dashboard Overview

### 1. Executive Overview (`executive_overview.json`)
**Business Focus:** High-level KPIs and system health metrics for leadership
- **Real-time active users** - Current user engagement
- **Total daily events** - Platform usage volume
- **Chat thread activity** - Core feature adoption
- **System health score** - Operational excellence
- **Chat volume trends** - Usage patterns over time
- **Response time distribution** - Performance metrics
- **Feature usage ranking** - Product adoption insights
- **User acquisition funnel** - Growth metrics
- **Error rate monitoring** - Reliability tracking

### 2. Prompt Analytics (`prompt_analytics.json`)
**Business Focus:** AI interaction intelligence for product optimization
- **Prompt volume trends** - AI usage patterns
- **Response time analysis** - Performance insights
- **Follow-up rate tracking** - Conversation depth
- **Token consumption metrics** - Cost analysis
- **Prompt categorization** - Usage pattern analysis
- **Response quality metrics** - AI effectiveness
- **Common prompt patterns** - User intent analysis
- **Model usage distribution** - Resource allocation
- **Prompt-response correlation** - Performance optimization
- **Problem prompt identification** - Quality assurance

### 3. User Behavior (`user_behavior.json`)
**Business Focus:** User journey optimization and engagement analysis
- **User journey flow (Sankey)** - Conversion funnel visualization
- **Daily active users** - Engagement trends
- **Session duration analysis** - User engagement depth
- **User segmentation** - Customer classification
- **Cohort retention analysis** - Customer lifetime value
- **Feature adoption funnel** - Product feature success
- **Activity heatmaps** - Usage pattern timing
- **Journey pattern analysis** - User flow optimization

## Data Sources

All dashboards are configured to use:
- **ClickHouse Analytics** - Primary analytics database
- **Redis Real-time** - Live metrics and caching

## Dashboard Features

### Templating Variables
- **User filters** - Filter by specific users
- **Time period selection** - Flexible time ranges
- **Model filters** - Filter by AI model type
- **Cohort analysis** - User segment analysis

### Alert Integration
- **High error rate alerts** - System reliability
- **Unusual traffic alerts** - Anomaly detection
- **Performance degradation** - Response time issues
- **System health monitoring** - Infrastructure health

### Panel Types Used
- **Time series** - Trend analysis
- **Stat panels** - KPI display
- **Gauge charts** - Health scores
- **Pie charts** - Distribution analysis
- **Tables** - Detailed data views
- **Heatmaps** - Pattern visualization
- **Sankey diagrams** - Flow analysis
- **Scatter plots** - Correlation analysis

## Configuration Details

### Query Pattern Examples

```sql
-- Real-time active users
SELECT count(DISTINCT user_id) as active_users 
FROM frontend_events 
WHERE timestamp >= now() - INTERVAL 5 MINUTE

-- Chat interaction analysis
SELECT 
  toStartOfHour(timestamp) as time,
  count() as chat_messages 
FROM frontend_events 
WHERE event_type = 'chat_interaction' 
  AND timestamp >= now() - INTERVAL 24 HOUR 
GROUP BY time 
ORDER BY time

-- User behavior segmentation
WITH user_activity AS (
  SELECT 
    user_id, 
    count() as total_events,
    countIf(event_type = 'chat_interaction') as chat_events
  FROM frontend_events 
  WHERE timestamp >= now() - INTERVAL 7 DAY 
  GROUP BY user_id
) 
SELECT 
  CASE 
    WHEN chat_events >= 50 THEN 'Power Users'
    WHEN chat_events >= 10 THEN 'Regular Users'
    WHEN chat_events >= 3 THEN 'Casual Users'
    ELSE 'New/Exploring'
  END as segment,
  count() as user_count
FROM user_activity 
GROUP BY segment
```

### Refresh Intervals
- **Executive Overview:** 30 seconds
- **Prompt Analytics:** 1 minute  
- **User Behavior:** 2 minutes

## Business Value Alignment

### Revenue Impact Tracking
- **User engagement metrics** → Retention and expansion
- **Feature adoption rates** → Product-market fit validation
- **Cost per interaction** → Unit economics optimization
- **Error rates and quality** → Customer satisfaction

### Strategic Insights
- **Usage pattern identification** → Product development priorities
- **User journey optimization** → Conversion improvement
- **Performance bottleneck detection** → Infrastructure investment
- **Cohort analysis** → Customer success strategies

## Customization Guide

### Adding New Panels
1. Define business objective
2. Create ClickHouse query
3. Configure visualization type
4. Set appropriate thresholds
5. Add to relevant dashboard

### Query Optimization Tips
- Use materialized views for heavy aggregations
- Leverage ClickHouse's time-based partitioning
- Index frequently filtered columns
- Use SAMPLE for large dataset previews

## Monitoring and Maintenance

### Performance Considerations
- Monitor query execution times
- Optimize slow-running panels
- Use appropriate time ranges
- Implement data retention policies

### Data Quality Checks
- Validate event schema compliance
- Monitor data freshness
- Check for missing events
- Verify aggregation accuracy

## Integration with Analytics Service

These dashboards are automatically provisioned by the `GrafanaService` class:

```python
from analytics_core.services import create_grafana_service

grafana = create_grafana_service()
result = grafana.auto_provision_all()
```

The service handles:
- Datasource configuration
- Dashboard deployment
- Alert rule creation
- Health monitoring