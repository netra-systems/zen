# Netra Apex - Monitoring & Observability Guide

## Overview

Netra Apex implements comprehensive observability following the principle: "We cannot optimize what we do not measure." This guide covers monitoring setup, performance benchmarks, SLA compliance, and operational procedures.

## Table of Contents

- [The Three Pillars of Observability](#the-three-pillars-of-observability)
- [Service Level Objectives (SLOs)](#service-level-objectives-slos)
- [Performance Benchmarks](#performance-benchmarks)
- [Business Metrics Monitoring](#business-metrics-monitoring)
- [Monitoring Stack Setup](#monitoring-stack-setup)
- [Alerting & Incident Response](#alerting--incident-response)
- [Troubleshooting Playbooks](#troubleshooting-playbooks)
- [Operational Procedures](#operational-procedures)

## The Three Pillars of Observability

### 1. Structured Logging

**Log Levels & Format:**
```json
{
  "timestamp": "2024-01-20T15:30:45.123Z",
  "level": "INFO",
  "service": "netra-backend",
  "component": "agent_service",
  "trace_id": "abc123-def456-ghi789",
  "user_id": "user_12345",
  "thread_id": "thread_67890",
  "message": "Agent execution completed successfully",
  "duration_ms": 1250,
  "metadata": {
    "agent_name": "TriageSubAgent",
    "optimization_type": "cost_reduction",
    "savings_amount": 125.50
  }
}
```

**Log Categories:**
- **Business Events**: Customer savings, optimization completions, tier upgrades
- **System Events**: Service starts, database connections, health checks
- **Security Events**: Authentication failures, rate limiting, suspicious activity
- **Performance Events**: Slow queries, high CPU, memory warnings
- **Error Events**: Exceptions, timeouts, validation failures

### 2. Metrics Collection (Prometheus)

**Business Metrics:**
```prometheus
# Customer savings metrics
netra_customer_savings_total{user_id="12345", tier="enterprise"} 15420.50
netra_optimization_completions_total{type="cost_reduction"} 1245
netra_tier_conversions_total{from="free", to="early"} 23

# System performance metrics
netra_http_request_duration_seconds{method="POST", endpoint="/api/agent/execute"} 1.25
netra_websocket_connections_active 145
netra_agent_execution_duration_seconds{agent="TriageSubAgent"} 2.8

# Infrastructure metrics
netra_database_connections_active{database="postgres"} 15
netra_database_query_duration_seconds{query_type="select"} 0.05
netra_memory_usage_bytes{service="backend"} 524288000
```

**Key Metric Categories:**
- **Business KPIs**: Savings, ROI, conversions, churn
- **Application Performance**: Response times, throughput, error rates
- **Infrastructure**: CPU, memory, disk, network
- **Database**: Connection pools, query performance, locks
- **Security**: Authentication rates, failed attempts, rate limits

### 3. Distributed Tracing (OpenTelemetry)

**Trace Flow Example:**
```
Customer Request → API Gateway → Auth Service → Agent Service → LLM Provider
     ↓              ↓              ↓              ↓              ↓
   trace_id      trace_id       trace_id       trace_id       trace_id
     +span         +span          +span          +span          +span
```

**Critical Trace Points:**
- User request entry
- Authentication validation
- Agent execution phases
- Database queries
- External API calls (LLM providers)
- WebSocket message handling

## Service Level Objectives (SLOs)

### Customer-Facing SLAs

| Service | SLO Target | Error Budget | Measurement |
|---------|------------|--------------|-------------|
| **API Availability** | 99.9% | 43 min/month | HTTP 200 responses |
| **API Response Time (p99)** | < 2000ms | 5% above threshold | Request duration |
| **WebSocket Connection** | < 500ms | 1% connection failures | Connection latency |
| **Agent Response Time** | < 30s | 2% timeout rate | End-to-end execution |
| **Data Accuracy** | > 99.5% | 0.5% error rate | Calculation validation |
| **Savings Calculation** | 100% | 0 failures | Business logic errors |

### Internal SLIs (Service Level Indicators)

```yaml
# SLI Configuration
slis:
  api_availability:
    query: sum(rate(http_requests_total{status!~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
    target: 0.999
    
  api_latency_p99:
    query: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
    target: 2.0
    
  agent_success_rate:
    query: sum(rate(netra_agent_completions_total{status="success"}[5m])) / sum(rate(netra_agent_completions_total[5m]))
    target: 0.98
    
  database_performance:
    query: histogram_quantile(0.95, rate(netra_database_query_duration_seconds_bucket[5m]))
    target: 0.1
```

### Error Budget Management

**Error Budget Calculation:**
```python
# Error budget tracking
error_budget_remaining = (slo_target - current_sli) / (1 - slo_target)

# Example: 99.9% SLO with 99.85% current availability
# error_budget_remaining = (0.999 - 0.9985) / (1 - 0.999) = -0.5 / 0.001 = -500%
# This indicates SLO breach - stop feature development, focus on stability
```

**Error Budget Policies:**
- **100% - 50%**: Normal feature development
- **50% - 25%**: Caution - review changes carefully
- **25% - 0%**: Reduce deployment frequency, focus on reliability
- **< 0%**: STOP feature development, incident response mode

## Performance Benchmarks

### System Performance Baselines

**Backend Performance (per instance):**
- **Throughput**: 1000 req/sec sustained
- **Latency**: p50 < 200ms, p95 < 1s, p99 < 2s
- **Memory**: < 2GB under normal load
- **CPU**: < 70% utilization

**Database Performance:**
- **Query Response**: p95 < 100ms
- **Connection Pool**: < 80% utilization
- **Lock Wait Time**: < 50ms average

**Agent Performance:**
- **Simple Queries**: < 5 seconds
- **Complex Optimization**: < 30 seconds
- **Parallel Execution**: 10+ concurrent agents

### Load Testing Benchmarks

```bash
# Performance testing commands
# API Load Test (1000 concurrent users)
locust -f tests/performance/api_load_test.py --host https://api.yourdomain.com -u 1000 -r 100 -t 5m

# WebSocket Load Test
python tests/performance/websocket_load_test.py --connections 500 --duration 300

# Database Load Test
python tests/performance/database_load_test.py --queries-per-second 5000 --duration 600

# Agent Load Test
python tests/performance/agent_load_test.py --concurrent-agents 50 --execution-time 30
```

**Expected Results:**
- **API**: 99% success rate at 1000 RPS
- **WebSockets**: 500 concurrent connections with < 1% drops
- **Database**: 5000 QPS with < 100ms p95 latency
- **Agents**: 50 concurrent executions with < 5% timeouts

## Business Metrics Monitoring

### Revenue & ROI Tracking

**Key Business Metrics:**
```prometheus
# Customer value metrics
netra_customer_lifetime_value{tier="enterprise"} 50000.00
netra_monthly_recurring_revenue{tier="early"} 125000.00
netra_churn_rate{tier="free"} 0.15

# Savings and optimization metrics
netra_customer_savings_monthly{user_id="12345"} 2850.75
netra_platform_roi{customer="acme_corp"} 4.2
netra_optimization_adoption_rate 0.87

# Conversion metrics
netra_free_to_paid_conversion_rate 0.12
netra_tier_upgrade_rate{from="early", to="mid"} 0.08
netra_feature_usage_rate{feature="bulk_optimization"} 0.65
```

### Business Intelligence Dashboards

**Executive Dashboard:**
- Total customer savings (monthly, quarterly, yearly)
- Revenue growth by tier
- Customer acquisition cost vs. lifetime value
- Platform adoption metrics

**Operations Dashboard:**
- System reliability metrics
- Cost per customer served
- Resource utilization efficiency
- Incident response metrics

### Cost Tracking & Optimization

```python
# Cost monitoring example
@monitor_cost
def calculate_customer_savings(user_id: str, optimization_data: dict):
    """Calculate and track customer savings with cost monitoring."""
    start_time = time.time()
    
    # Business logic for savings calculation
    savings = perform_optimization_analysis(optimization_data)
    
    # Track business metrics
    metrics.histogram('netra_savings_calculation_duration', 
                     time.time() - start_time,
                     tags={'user_id': user_id})
    
    metrics.gauge('netra_customer_savings_total', savings.total_amount,
                 tags={'user_id': user_id, 'tier': user.tier})
    
    return savings
```

## Monitoring Stack Setup

### 1. Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "netra_alerting_rules.yml"
  - "business_alerting_rules.yml"

scrape_configs:
  - job_name: 'netra-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'netra-frontend'
    static_configs:
      - targets: ['frontend:3000']
    metrics_path: /api/metrics

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres_exporter:9187']

  - job_name: 'clickhouse'
    static_configs:
      - targets: ['clickhouse_exporter:9116']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis_exporter:9121']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 2. Grafana Dashboard Configuration

**Dashboard Categories:**

1. **Business Overview**
   ```json
   {
     "dashboard": {
       "title": "Netra Business Metrics",
       "panels": [
         {
           "title": "Total Customer Savings",
           "type": "stat",
           "targets": [{"expr": "sum(netra_customer_savings_total)"}]
         },
         {
           "title": "Monthly Recurring Revenue",
           "type": "graph",
           "targets": [{"expr": "sum by (tier) (netra_monthly_recurring_revenue)"}]
         }
       ]
     }
   }
   ```

2. **System Performance**
   ```json
   {
     "dashboard": {
       "title": "Netra System Performance",
       "panels": [
         {
           "title": "API Response Times",
           "type": "graph",
           "targets": [
             {"expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"},
             {"expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))"}
           ]
         }
       ]
     }
   }
   ```

### 3. Log Aggregation (ELK Stack)

```yaml
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "netra-backend" {
    json {
      source => "message"
    }
    
    if [level] == "ERROR" {
      mutate {
        add_tag => ["error", "needs_attention"]
      }
    }
    
    if [component] == "agent_service" and [metadata][savings_amount] {
      mutate {
        add_field => { "business_impact" => "%{[metadata][savings_amount]}" }
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "netra-logs-%{+YYYY.MM.dd}"
  }
}
```

## Alerting & Incident Response

### Critical Alert Rules

```yaml
# netra_alerting_rules.yml
groups:
  - name: business_critical
    rules:
      - alert: SavingsCalculationFailure
        expr: rate(netra_savings_calculation_errors[5m]) > 0
        for: 1m
        labels:
          severity: critical
          team: business
        annotations:
          summary: "Business metric calculation failures detected"
          description: "Savings calculations are failing - immediate revenue impact"
          runbook: "https://docs.netra.com/runbooks/savings-calculation-failure"
          
      - alert: CustomerTierDowngrade
        expr: increase(netra_tier_downgrades_total[1h]) > 2
        for: 5m
        labels:
          severity: warning
          team: business
        annotations:
          summary: "Multiple customer tier downgrades detected"

  - name: system_reliability
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "High error rate detected"
          
      - alert: SLOBreach
        expr: (rate(http_requests_total{status!~"5.."}[5m]) / rate(http_requests_total[5m])) < 0.999
        for: 10m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "SLO breach - availability below 99.9%"
          
      - alert: AgentTimeouts
        expr: rate(netra_agent_timeouts_total[5m]) / rate(netra_agent_executions_total[5m]) > 0.02
        for: 5m
        labels:
          severity: warning
          team: agents
        annotations:
          summary: "High agent timeout rate"

  - name: infrastructure
    rules:
      - alert: DatabaseConnectionPool
        expr: netra_database_connections_active / netra_database_connections_max > 0.8
        for: 2m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "Database connection pool near capacity"
          
      - alert: HighMemoryUsage
        expr: netra_memory_usage_bytes / netra_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "High memory usage detected"
```

### Incident Response Procedures

#### Severity Levels

**P1 - Critical (< 15 min response)**
- Business metric calculation failures
- Customer-facing service down
- Data loss or corruption
- Security breach

**P2 - High (< 1 hour response)**
- Performance degradation affecting SLAs
- Non-critical service failures
- Significant error rate increases

**P3 - Medium (< 4 hours response)**
- Minor performance issues
- Single component failures with redundancy
- Non-customer-facing issues

#### Response Procedures

1. **Immediate Response (P1)**
   ```bash
   # Check system status
   curl https://api.yourdomain.com/health/ready
   
   # Check recent deployments
   kubectl get deployments -o wide
   
   # Review recent alerts
   curl http://prometheus:9090/api/alerts
   
   # Check error logs
   kubectl logs -l app=netra-backend --since=10m | grep ERROR
   ```

2. **Escalation Matrix**
   - **Platform Issues**: Platform team → DevOps → CTO
   - **Business Metrics**: Business team → Product → CEO
   - **Security**: Security team → CISO → Legal
   - **Customer Impact**: Support → Customer Success → VP Sales

### On-Call Procedures

```yaml
# PagerDuty integration
routing_rules:
  - match:
      severity: critical
    receiver: critical-oncall
    
  - match:
      team: business
    receiver: business-oncall
    
  - match:
      team: platform
    receiver: platform-oncall

receivers:
  - name: critical-oncall
    pagerduty_configs:
      - service_key: <critical-service-key>
        description: "{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}"
        
  - name: slack-notifications
    slack_configs:
      - api_url: <slack-webhook>
        channel: '#netra-alerts'
        text: "Alert: {{ .CommonAnnotations.summary }}"
```

## Troubleshooting Playbooks

### 1. High API Latency

**Symptoms:**
- p99 response time > 2000ms
- Customer complaints about slow responses
- Agent timeouts increasing

**Investigation Steps:**
```bash
# 1. Check current latency
curl "http://prometheus:9090/api/query?query=histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))"

# 2. Identify slow endpoints
curl "http://prometheus:9090/api/query?query=topk(5, histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{endpoint!~'/health.*'}[5m])))"

# 3. Check database performance
psql -h postgres -c "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# 4. Review application logs
kubectl logs -l app=netra-backend --since=15m | grep -E "(SLOW|WARNING|ERROR)"

# 5. Check resource utilization
kubectl top pods -l app=netra-backend
```

**Common Fixes:**
- Scale up backend instances: `kubectl scale deployment netra-backend --replicas=5`
- Optimize database queries: Review and add indexes
- Clear caches: `kubectl exec redis -- redis-cli FLUSHALL`
- Restart services: `kubectl rollout restart deployment netra-backend`

### 2. Database Connection Issues

**Symptoms:**
- Connection pool exhaustion
- "too many connections" errors
- High database CPU usage

**Investigation Steps:**
```bash
# 1. Check active connections
psql -h postgres -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';"

# 2. Check connection pool status
curl http://backend:8000/health/dependencies | jq '.database'

# 3. Identify long-running queries
psql -h postgres -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"

# 4. Check for deadlocks
psql -h postgres -c "SELECT * FROM pg_stat_database_conflicts WHERE confl_deadlock > 0;"
```

**Resolution Steps:**
```bash
# 1. Kill long-running queries
psql -h postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND now() - state_change > interval '10 minutes';"

# 2. Increase connection limits (temporary)
psql -h postgres -c "ALTER SYSTEM SET max_connections = 300; SELECT pg_reload_conf();"

# 3. Restart application to reset connection pools
kubectl rollout restart deployment netra-backend

# 4. Scale database if needed
# (For managed database, increase instance size)
```

### 3. Agent Execution Failures

**Symptoms:**
- Agent timeouts increasing
- LLM API errors
- Business metric calculation failures

**Investigation Steps:**
```bash
# 1. Check agent success rate
curl "http://prometheus:9090/api/query?query=rate(netra_agent_failures_total[5m])"

# 2. Review agent logs
kubectl logs -l app=netra-backend --since=15m | grep "agent_service"

# 3. Check LLM provider status
curl -H "Authorization: Bearer $GEMINI_API_KEY" https://generativelanguage.googleapis.com/models

# 4. Verify external connectivity
kubectl exec -it netra-backend-pod -- curl -I https://api.openai.com

# 5. Check agent queue backlog
curl http://backend:8000/api/agent/queue-status
```

**Resolution Steps:**
```bash
# 1. Restart agent service
kubectl rollout restart deployment netra-backend

# 2. Switch to backup LLM provider
kubectl set env deployment/netra-backend FALLBACK_LLM_ENABLED=true

# 3. Clear agent queue if backed up
curl -X POST http://backend:8000/api/admin/clear-agent-queue

# 4. Scale agent workers
kubectl set env deployment/netra-backend AGENT_WORKER_COUNT=10
```

## Operational Procedures

### Daily Operations Checklist

**Morning Health Check (9:00 AM):**
```bash
#!/bin/bash
# daily-health-check.sh

echo "🏥 Daily Netra Health Check - $(date)"

# 1. System availability
echo "1. Checking system availability..."
curl -f https://api.yourdomain.com/health || echo "❌ API DOWN"

# 2. SLA compliance
echo "2. Checking SLA compliance..."
python scripts/check_sla_compliance.py --period 24h

# 3. Business metrics
echo "3. Checking business metrics..."
python scripts/business_metrics_report.py --period yesterday

# 4. Error budget status
echo "4. Checking error budget..."
python scripts/error_budget_status.py

# 5. Recent alerts summary
echo "5. Recent alerts summary..."
curl -s "http://prometheus:9090/api/alerts" | jq '.data.alerts[].labels.alertname' | sort | uniq -c

# 6. Database health
echo "6. Database health check..."
python scripts/database_health_check.py

echo "✅ Daily health check completed"
```

**Weekly Operations Review:**
- Review SLA performance vs targets
- Analyze cost trends and optimization opportunities
- Review incident post-mortems
- Update monitoring dashboards based on new requirements
- Capacity planning based on usage trends

### Maintenance Procedures

**Monthly Maintenance:**
```bash
#!/bin/bash
# monthly-maintenance.sh

# 1. Database optimization
echo "🛠️ Running database maintenance..."
psql -h postgres -c "VACUUM ANALYZE;"
psql -h postgres -c "REINDEX DATABASE netra_prod;"

# 2. Clean old logs
echo "🧹 Cleaning old logs..."
kubectl delete pods -l app=netra-backend --field-selector=status.phase=Succeeded
find /logs -name "*.log" -mtime +30 -delete

# 3. Update monitoring rules
echo "📊 Updating monitoring rules..."
kubectl apply -f monitoring/prometheus-rules.yml

# 4. Security updates
echo "🔒 Checking for security updates..."
docker image pull netra/backend:latest
docker image pull netra/frontend:latest

# 5. Backup verification
echo "💾 Verifying backups..."
python scripts/verify_backups.py --period 1month

echo "✅ Monthly maintenance completed"
```

**Quarterly Reviews:**
- Comprehensive performance analysis
- Business metrics deep dive
- Security audit
- Disaster recovery testing
- Capacity planning for next quarter
- SLA target review and adjustment

### Monitoring Best Practices

1. **Golden Signals Focus**
   - **Latency**: How long requests take
   - **Traffic**: Demand on the system
   - **Errors**: Rate of failed requests
   - **Saturation**: Resource utilization

2. **Business Metrics Integration**
   - Monitor business KPIs alongside technical metrics
   - Alert on business impact, not just technical issues
   - Correlate system performance with business outcomes

3. **Actionable Alerting**
   - Every alert must have a clear action
   - Reduce alert fatigue with proper thresholds
   - Include runbook links in all alerts

4. **Continuous Improvement**
   - Regular review of alert effectiveness
   - Update dashboards based on operational needs
   - Incorporate lessons learned from incidents

---

**Monitoring Philosophy**: "We cannot optimize what we do not measure. Every system component is observable by design, with comprehensive logging, metrics, and tracing to ensure optimal customer value delivery."

**Last Updated**: December 2025  
**Document Version**: 1.2  
**Monitoring Status**: Three Pillars Operational - Full Observability Active  
**SLA Compliance**: 99.95% availability achieved  

## Current Monitoring Health (2025-12-09)

- **Structured Logging**: ✅ JSON format with trace correlation operational
- **Metrics Collection**: ✅ Prometheus + Grafana dashboards active
- **Distributed Tracing**: ✅ OpenTelemetry integration functional
- **Business Metrics**: ✅ $500K+ ARR tracking with real-time dashboards
- **Alert System**: ✅ Actionable alerts with runbook integration
- **SLO Monitoring**: ✅ Error budgets tracked, 99.95% uptime maintained

**Related Documentation:**
- [Production Deployment Guide](../deployment/PRODUCTION_DEPLOYMENT.md)
- [Architecture Documentation](../architecture/ARCHITECTURE.md)
- [Business Metrics Guide](../business/REVENUE_TRACKING.md)
- [Troubleshooting Procedures](../deployment/STAGING_TROUBLESHOOTING.md)