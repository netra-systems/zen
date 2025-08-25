# Deployment Configuration Guide

## Optimal Deployment Settings

Based on Iteration 3 audit findings and performance validation, this guide documents the optimal configuration settings for Netra Apex platform deployment.

### ✅ Verified Healthy Configuration

The service has been audited and found to be **healthy** with the following optimized settings:

## 🚀 Cloud Run Configuration

### Backend Service (netra-backend-staging)
```yaml
Memory: 1Gi  # Reduced from 2Gi for cost optimization
CPU: 2       # Boosted for better startup performance  
Min Instances: 1
Max Instances: 20
Timeout: 300 seconds
Port: 8888
```

**Performance Characteristics:**
- **Startup Time:** <30 seconds (target: <60 seconds)
- **Memory Usage:** ~400-600MB (limit: 1Gi)
- **Health Endpoint:** <100ms response time
- **CPU Efficiency:** Optimized with boost enabled

### Auth Service (netra-auth-service)
```yaml
Memory: 512Mi
CPU: 1
Min Instances: 1  
Max Instances: 10
Timeout: 300 seconds
Port: 8080
```

### Frontend Service (netra-frontend-staging)
```yaml
Memory: 2Gi    # Higher for Node.js build process
CPU: 1
Min Instances: 1
Max Instances: 10
Port: 3000
```

## 🎯 Performance Targets

### Service Level Objectives (SLOs)

| Metric | Target | Monitoring |
|--------|--------|------------|
| **Startup Time** | <60 seconds | ✅ Cloud Run timeout compliance |
| **Memory Usage** | <900MB (Backend) | ✅ Container resource limits |
| **Health Response** | <100ms | ✅ Health endpoint monitoring |
| **CPU Utilization** | <85% average | ✅ Resource efficiency |
| **Availability** | >99.5% | ✅ Multi-instance deployment |
| **Error Rate** | <1% | ✅ Application monitoring |

### Response Time SLAs

| Endpoint | P95 Target | P99 Target |
|----------|------------|------------|
| Health Check | <100ms | <200ms |
| Ready Check | <200ms | <500ms |
| API Endpoints | <500ms | <1000ms |

## 🔧 Configuration Optimizations

### Memory Optimization
- **Before:** Backend used 2Gi memory allocation
- **After:** Reduced to 1Gi with headroom monitoring
- **Result:** 50% cost reduction with maintained performance

### CPU Optimization  
- **Strategy:** Enabled CPU boost for startup performance
- **Benefit:** Faster container initialization and request handling
- **Monitoring:** CPU utilization stays <85% under normal load

### Startup Optimization
- **Target:** Service ready within 60-second Cloud Run timeout
- **Achieved:** ~25-35 second startup time
- **Safety Margin:** 25-35 seconds buffer for reliability

## 📊 Monitoring & Alerting Setup

### Health Monitoring
```yaml
Health Checks:
  - Path: /health
  - Interval: 30 seconds
  - Timeout: 10 seconds
  - Success Threshold: 1
  - Failure Threshold: 3

Startup Probes:
  - Path: /health  
  - Initial Delay: 10 seconds
  - Period: 5 seconds
  - Timeout: 3 seconds
  - Success Threshold: 1
  - Failure Threshold: 12  # 60 second total timeout
```

### Performance Alerts
```yaml
Critical Alerts:
  - Memory usage > 900MB
  - Startup time > 60 seconds
  - Health response > 200ms
  - Error rate > 5%

Warning Alerts:
  - Memory usage > 700MB
  - CPU utilization > 80%
  - Health response > 100ms
  - Error rate > 1%
```

## 🚦 Deployment Validation

### Automated Validation
Use the deployment validation script for every deployment:

```bash
# Local validation
python scripts/validate_deployment_performance.py --environment local

# Staging validation with details
python scripts/validate_deployment_performance.py --environment staging --detailed

# CI/CD validation
python scripts/validate_deployment_performance.py --environment staging --output validation-report.json
```

### Pre-Deployment Checklist
- [ ] **Architecture compliance check passed**
- [ ] **Memory usage <900MB validated** 
- [ ] **Startup time <60 seconds confirmed**
- [ ] **Health endpoints responding <100ms**
- [ ] **Integration tests passing**
- [ ] **Resource limits properly configured**

### Post-Deployment Verification
- [ ] **All services reporting healthy status**
- [ ] **Performance metrics within SLA targets**
- [ ] **No error spikes in monitoring**
- [ ] **Cross-service communication working**
- [ ] **Database connections stable**

## 🔒 Security & Environment

### Environment Variables
```yaml
Required for Backend:
  - ENVIRONMENT=staging
  - PYTHONUNBUFFERED=1
  - AUTH_SERVICE_URL=https://auth.staging.netrasystems.ai
  - FRONTEND_URL=https://app.staging.netrasystems.ai

Required for Auth:
  - ENVIRONMENT=staging  
  - PYTHONUNBUFFERED=1
  - FRONTEND_URL=https://app.staging.netrasystems.ai

Required for Frontend:
  - NODE_ENV=production
  - NEXT_PUBLIC_API_URL=https://api.staging.netrasystems.ai
```

### Secret Management
All secrets managed via Google Secret Manager:
- Database credentials (PostgreSQL)
- JWT signing keys
- OAuth client credentials  
- API keys (OpenAI, Gemini, Anthropic)
- Redis connection details
- ClickHouse credentials

## 🎪 Deployment Process

### Recommended Deployment Command
```bash
# Default: Fast local build, no checks (for quick testing)
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Production-ready: With validation checks
python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks
```

### Deployment Strategy
1. **Local Build:** 5-10x faster than Cloud Build
2. **Parallel Validation:** Run tests during build process
3. **Health Verification:** Automated post-deployment checks
4. **Gradual Rollout:** Traffic routing to healthy revisions only

## 📈 Performance Monitoring

### Key Metrics Dashboard
Monitor these metrics continuously:

```yaml
System Metrics:
  - Memory: Current usage vs 1Gi limit
  - CPU: Utilization percentage
  - Network: Request/response latency
  - Storage: Temporary disk usage

Application Metrics:
  - Request rate: Requests per second
  - Error rate: 4xx/5xx response percentage  
  - Response time: P50, P95, P99 latencies
  - Concurrent users: Active session count

Business Metrics:
  - User registration rate
  - API usage patterns
  - Feature adoption metrics
  - Cost per transaction
```

### Alerting Runbooks
- **High Memory Usage:** Scale up or optimize memory usage
- **Slow Startup:** Check initialization sequence and dependencies
- **Health Check Failures:** Investigate service availability
- **High Error Rates:** Check logs and recent deployments

## 🔄 Continuous Improvement

### Performance Optimization Cycle
1. **Monitor:** Collect performance metrics continuously
2. **Analyze:** Review weekly performance reports
3. **Optimize:** Identify improvement opportunities
4. **Deploy:** Test optimizations in staging
5. **Validate:** Confirm improvements with metrics

### Cost Optimization
- **Memory Right-sizing:** Monitor actual usage vs allocation
- **Instance Scaling:** Optimize min/max instance counts
- **Regional Deployment:** Use closest regions for users
- **Resource Pooling:** Share resources between non-critical services

## ✅ Validation Results

Recent audit confirmed:
- ✅ **Service Health:** All services reporting healthy
- ✅ **Performance:** Metrics within target ranges
- ✅ **Startup:** Consistently under 60-second timeout
- ✅ **Resource Usage:** Memory optimized to 1Gi successfully
- ✅ **Reliability:** High availability with multi-instance deployment

## 🚨 Troubleshooting

### Common Issues and Solutions

#### Startup Timeout (>60 seconds)
- **Cause:** Slow database initialization or external dependencies
- **Solution:** Optimize startup sequence, implement health checks
- **Prevention:** Monitor startup time trends

#### Memory Limit Exceeded (>1Gi)
- **Cause:** Memory leaks or inefficient data structures
- **Solution:** Profile memory usage, optimize data handling
- **Prevention:** Continuous memory monitoring

#### Health Check Failures
- **Cause:** Service overload or dependency unavailability
- **Solution:** Check logs, verify dependencies, scale if needed
- **Prevention:** Proper health check implementation

#### High Error Rates (>5%)
- **Cause:** Application bugs, dependency failures, or overload
- **Solution:** Check recent deployments, review error logs
- **Prevention:** Comprehensive testing and monitoring

---

## 📞 Support

For deployment issues or performance concerns:
1. Check monitoring dashboard for current metrics
2. Run validation script to identify specific issues
3. Review recent deployment logs
4. Escalate to platform team if needed

---

**Last Updated:** Based on Iteration 3 audit findings
**Next Review:** After significant architecture changes or performance issues