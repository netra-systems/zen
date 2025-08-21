# Netra Apex Migration Plan
## Transitioning from Current Prototype to Production Platform

---

## Current State Analysis

### Existing Codebase Assets
```
✅ Strong Foundation:
- Multi-agent system (supervisor, triage, data agents)
- WebSocket infrastructure
- Basic authentication
- PostgreSQL + ClickHouse setup
- Frontend with Next.js
- Test framework

⚠️ Gaps for Production:
- No billing/payment system
- No usage tracking/limits
- No optimization engine
- No validation workbench
- Limited monitoring
- No infrastructure optimization
```

### Migration Strategy
**Approach**: Incremental migration with parallel development
**Timeline**: 8 weeks synchronized with implementation plan
**Risk**: Minimal - enhance existing, don't replace

---

## Week 1-2: Foundation Enhancement

### Team 1: Gateway Migration
```python
# CURRENT: app/routes/agents.py
@router.post("/agent/run")
async def run_agent(request: AgentRequest):
    # Basic agent execution
    
# MIGRATE TO: app/gateway/core/proxy_server.py
class ProxyServer:
    async def handle_request(self, request: Request):
        # Enhanced with optimization pipeline
        # Backward compatible with existing agents
```

**Migration Steps**:
1. Create new `app/gateway/` module structure
2. Wrap existing routes with gateway logic
3. Add provider abstraction layer
4. Maintain backward compatibility

### Team 2: Add Optimization Layer
```python
# NEW: app/services/optimization/
optimization_engine.py  # New optimization pipeline
cache_service.py       # Semantic caching
compression_service.py # Prompt compression

# Integration point with existing system:
# Modify app/agents/supervisor/supervisor.py
class Supervisor:
    def __init__(self):
        self.optimization = OptimizationEngine()  # Add
    
    async def process_request(self, request):
        # Existing logic
        optimized = await self.optimization.optimize(request)  # Add
        # Continue with existing flow
```

### Team 3: Billing Foundation
```python
# NEW: app/services/billing/
usage_tracker.py      # Track all API calls
tier_enforcer.py      # Implement limits
payment_service.py    # Stripe integration

# Integration with existing auth:
# Modify app/auth/auth_dependencies.py
async def get_current_user(...):
    user = # existing logic
    user.usage = await UsageTracker.get_usage(user.id)  # Add
    user.tier = await TierService.get_tier(user.id)     # Add
    return user
```

### Team 4: Enhance Data Pipeline
```sql
-- Modify existing ClickHouse schema
ALTER TABLE events ADD COLUMN cost Decimal(10,4);
ALTER TABLE events ADD COLUMN tokens_used UInt32;
ALTER TABLE events ADD COLUMN optimization_type String;

-- New tables for metrics
CREATE TABLE usage_metrics (...);
CREATE TABLE billing_events (...);
```

### Team 5: Frontend Dashboard
```typescript
// Enhance existing frontend/app/dashboard/
// ADD new components:
components/metrics/ValueDashboard.tsx
components/billing/SubscriptionManager.tsx
components/onboarding/TrialActivation.tsx

// Modify existing layout to include new sections
```

---

## Week 3-4: Revenue Engine Integration

### Critical Path Items

#### 1. Payment Processing
```python
# app/routes/billing.py (NEW)
@router.post("/checkout/session")
async def create_checkout_session(tier: Tier, user: User):
    # Stripe checkout integration
    
@router.post("/webhook/stripe")
async def handle_stripe_webhook(event: StripeEvent):
    # Handle payment events
```

#### 2. Usage Enforcement
```python
# app/middleware/usage_limiter.py (NEW)
class UsageLimiter(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        user = await get_current_user(request)
        if await self.exceeds_limit(user):
            return JSONResponse(
                status_code=429,
                content={"upgrade_url": "/billing/upgrade"}
            )
        return await call_next(request)
```

#### 3. Trial System
```python
# Modify app/db/models_user.py
class User(Base):
    # Existing fields
    trial_started_at = Column(DateTime)  # Add
    trial_ends_at = Column(DateTime)     # Add
    subscription_tier = Column(String)   # Add
    stripe_customer_id = Column(String)  # Add
```

---

## Week 5-6: Advanced Features

### Infrastructure Optimization Integration

#### 1. Telemetry Expansion
```python
# app/services/telemetry/cloud_monitor.py (NEW)
class CloudMonitor:
    async def ingest_aws_metrics(self):
        # CloudWatch integration
    
    async def ingest_k8s_metrics(self):
        # Kubernetes metrics
```

#### 2. IaC Generation
```python
# app/services/iac/terraform_generator.py (NEW)
class TerraformGenerator:
    def analyze_waste(self, metrics: CloudMetrics):
        # Identify optimization opportunities
    
    def generate_terraform(self, optimizations: List[Optimization]):
        # Create optimized Terraform
```

### Validation Workbench

#### 1. Sandbox Management
```python
# app/services/validation/sandbox.py (NEW)
class SandboxManager:
    async def provision_environment(self):
        # Spin up test infrastructure
    
    async def deploy_terraform(self, config: str):
        # Deploy and test
```

#### 2. BVM Integration
```python
# app/services/billing/bvm_meter.py (NEW)
class BVMeter:
    def track_validation_minutes(self, validation: Validation):
        # Track compute usage for billing
```

---

## Week 7-8: Production Readiness

### Performance Optimization

#### 1. Database Optimization
```sql
-- Add indexes for performance
CREATE INDEX idx_user_timestamp ON llm_requests(user_id, timestamp);
CREATE INDEX idx_cache_embedding ON cache_entries(embedding);

-- Create materialized views
CREATE MATERIALIZED VIEW user_savings_daily AS
SELECT user_id, date, sum(savings) as total_savings
FROM optimizations
GROUP BY user_id, date;
```

#### 2. Caching Layer
```python
# app/core/cache.py (ENHANCE)
class CacheManager:
    def __init__(self):
        self.redis = Redis()  # L1 Cache
        self.clickhouse = ClickHouse()  # L2 Cache
        
    async def get_or_compute(self, key: str, compute_fn):
        # Multi-tier caching strategy
```

### Monitoring & Alerting

#### 1. Metrics Collection
```python
# app/monitoring/metrics.py (NEW)
from prometheus_client import Counter, Histogram

request_count = Counter('apex_requests_total', 'Total requests')
request_duration = Histogram('apex_request_duration_seconds', 'Request duration')
optimization_savings = Counter('apex_savings_total', 'Total savings generated')
```

#### 2. Health Checks
```python
# app/routes/health.py (ENHANCE)
@router.get("/health/detailed")
async def detailed_health():
    return {
        "gateway": await check_gateway(),
        "database": await check_database(),
        "cache": await check_cache(),
        "providers": await check_providers(),
        "billing": await check_billing()
    }
```

---

## Data Migration Strategy

### User Data Migration
```python
# scripts/migrate_users.py
async def migrate_users():
    # 1. Add new fields with defaults
    await db.execute("""
        ALTER TABLE users 
        ADD COLUMN tier VARCHAR DEFAULT 'free',
        ADD COLUMN usage_limit INTEGER DEFAULT 3
    """)
    
    # 2. Backfill trial dates for existing users
    await db.execute("""
        UPDATE users 
        SET trial_started_at = created_at,
            trial_ends_at = created_at + INTERVAL '7 days'
        WHERE trial_started_at IS NULL
    """)
```

### Historical Data Processing
```python
# scripts/process_historical.py
async def process_historical_logs():
    # 1. Read existing logs
    logs = await clickhouse.query("SELECT * FROM events")
    
    # 2. Enrich with cost data
    for log in logs:
        log.cost = calculate_cost(log)
        log.tokens = count_tokens(log)
    
    # 3. Write enriched data
    await clickhouse.insert("events_enriched", logs)
```

---

## Rollback Strategy

### Feature Flags
```python
# app/config.py
FEATURE_FLAGS = {
    "optimization_enabled": True,
    "billing_enabled": False,  # Enable gradually
    "validation_workbench": False,  # Enable when ready
    "new_dashboard": True,
    "legacy_routes": True  # Keep old routes active
}

# Usage in code
if FEATURE_FLAGS["optimization_enabled"]:
    response = await optimization_engine.optimize(request)
else:
    response = request  # Pass through
```

### Database Rollback
```sql
-- Rollback migrations if needed
-- Keep backward compatibility
ALTER TABLE users RENAME COLUMN tier TO tier_backup;
ALTER TABLE users ADD COLUMN tier VARCHAR DEFAULT 'free';

-- Can restore old data if needed
UPDATE users SET tier = tier_backup WHERE tier_backup IS NOT NULL;
```

---

## Testing During Migration

### Parallel Testing
```python
# tests/migration/compatibility_test.py
async def test_backward_compatibility():
    # Test old endpoints still work
    response = await client.post("/agent/run", json=old_format)
    assert response.status_code == 200
    
    # Test new endpoints
    response = await client.post("/gateway/optimize", json=new_format)
    assert response.status_code == 200
```

### Load Testing
```python
# tests/migration/load_test.py
async def test_migration_performance():
    # Ensure no performance degradation
    old_latency = await measure_latency("/agent/run")
    new_latency = await measure_latency("/gateway/optimize")
    
    assert new_latency <= old_latency * 1.1  # Allow 10% overhead
```

---

## Team Coordination During Migration

### Daily Sync Points
```
Morning (9 AM):
- Team leads sync on migration progress
- Identify blocking issues
- Coordinate shared resources

Evening (5 PM):
- Integration testing
- Resolve conflicts
- Plan next day
```

### Migration Checklist

#### Week 1-2 Checklist
- [ ] Gateway wrapper implemented
- [ ] Optimization engine integrated
- [ ] Usage tracking operational
- [ ] Database schema updated
- [ ] Frontend dashboard live

#### Week 3-4 Checklist
- [ ] Payment processing live
- [ ] Trial system active
- [ ] Usage limits enforced
- [ ] ROI dashboard complete

#### Week 5-6 Checklist
- [ ] Infrastructure telemetry ingesting
- [ ] IaC generation working
- [ ] Validation sandbox operational
- [ ] BVM billing implemented

#### Week 7-8 Checklist
- [ ] Performance optimized
- [ ] Monitoring complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Production deployment ready

---

## Risk Mitigation

### High-Risk Areas
1. **Payment Integration**: Test thoroughly in staging
2. **Data Migration**: Backup before any changes
3. **Performance**: Monitor closely during rollout
4. **User Experience**: A/B test new features

### Contingency Plans
1. **Feature Flags**: Disable problematic features instantly
2. **Rollback Scripts**: Prepared and tested
3. **Hotfix Process**: 30-minute response time
4. **Customer Communication**: Templates ready

---

## Success Metrics

### Technical Metrics
- Zero downtime during migration
- No data loss
- <10% performance degradation
- 100% backward compatibility

### Business Metrics
- User engagement maintained
- First payment within Week 4
- 10+ trials activated by Week 6
- No increase in support tickets

---

## Post-Migration Cleanup

### Week 9-10 Tasks
1. Remove legacy code paths
2. Optimize database queries
3. Archive old data
4. Update documentation
5. Conduct retrospective

---

*Migration Plan Version: 1.0*
*Created: 2025-08-17*
*Status: READY FOR EXECUTION*
*Risk Level: MEDIUM (with mitigations)*