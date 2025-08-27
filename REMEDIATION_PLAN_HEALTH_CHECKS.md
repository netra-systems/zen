# Health Check Configuration Remediation Plan

## Executive Summary
Critical port mismatch issue causing frontend health check failures in development. Staging has separate architectural issues with disabled health checks for Cloud Run services.

## Issues Identified

### Development Environment
1. **Port 8004 Mismatch**: Frontend attempts to proxy to backend on port 8004, but backend runs on port 8000
2. **Service Discovery Failure**: Dynamic port allocation inconsistent with static configuration
3. **Proxy Architecture Flaw**: Frontend unnecessarily proxying health checks to backend

### Staging Environment  
1. **Disabled Health Checks**: Load balancer health checks disabled for serverless NEGs
2. **Port Inconsistency**: Load balancer checks port 8080, services run on 8888/3000
3. **No Monitoring**: Health endpoints exist but aren't actively monitored

## Remediation Steps

### Phase 1: Immediate Fixes (Day 1)

#### Development Environment
1. **Fix Port Assignment in dev_launcher**
   - File: `dev_launcher/backend_starter.py`
   - Action: Force static port 8000, remove dynamic allocation
   - Validation: Ensure `BACKEND_PORT=8000` always set
   
2. **Update Frontend Configuration**
   - File: `frontend/lib/unified-api-config.ts`
   - Action: Hardcode development backend to `http://localhost:8000`
   - Remove reliance on dynamic service discovery for port

3. **Remove Health Proxy Rules**
   - File: `frontend/next.config.ts`
   - Action: Remove `/health/*` proxy rewrites
   - Frontend should use its own health endpoints

#### Staging Environment
1. **Enable Health Check Monitoring**
   - Add external monitoring for health endpoints
   - Monitor: `https://api.staging.netrasystems.ai/health`
   - Monitor: `https://app.staging.netrasystems.ai/api/health`

### Phase 2: Configuration Cleanup (Day 2-3)

1. **Implement Single Source of Truth**
   ```python
   # Create: config/ports.py
   PORTS = {
       'backend': 8000,
       'frontend': 3000,
       'auth': 8081,
       'redis': 6379,
       'postgres': 5432
   }
   ```

2. **Update All References**
   - `dev_launcher/config.py`: Use `PORTS['backend']`
   - `netra_backend/app/core/network_constants.py`: Import from config
   - `frontend/next.config.ts`: Read from environment variable
   - All test configurations: Use centralized config

3. **Add Port Validation**
   ```python
   # dev_launcher/validators.py
   def validate_port_configuration():
       backend_port = os.environ.get('BACKEND_PORT')
       api_url = os.environ.get('NEXT_PUBLIC_API_URL')
       if f":{backend_port}" not in api_url:
           raise ConfigurationError(f"Port mismatch: {backend_port} vs {api_url}")
   ```

### Phase 3: Architecture Improvements (Week 1)

1. **Separate Health Check Ownership**
   - Frontend: `/api/health` checks Node.js, memory, build status
   - Backend: `/health` checks database, Redis, LLM connections
   - Auth: `/health` checks OAuth config, session store

2. **Implement Health Check Aggregator**
   ```typescript
   // frontend/lib/health-aggregator.ts
   async function checkSystemHealth() {
     const results = await Promise.allSettled([
       fetch('/api/health'),  // Frontend health
       fetch(`${API_URL}/health`),  // Backend health
       fetch(`${AUTH_URL}/health`)  // Auth health
     ]);
     return aggregateResults(results);
   }
   ```

3. **Fix Staging Load Balancer**
   ```terraform
   # terraform-gcp-staging/load-balancer.tf
   resource "google_compute_health_check" "serverless" {
     name = "serverless-health-check"
     
     http_health_check {
       port = 8888  # Match actual service port
       request_path = "/health"
     }
   }
   ```

### Phase 4: Testing & Validation (Week 1-2)

1. **Add Integration Tests**
   ```python
   # tests/integration/test_health_checks.py
   def test_frontend_can_reach_backend():
       frontend_config = get_frontend_config()
       backend_url = frontend_config['api_url']
       response = requests.get(f"{backend_url}/health")
       assert response.status_code == 200
   ```

2. **Add Startup Validation**
   ```python
   # dev_launcher/health_validator.py
   def validate_all_services_healthy():
       services = {
           'backend': 'http://localhost:8000/health',
           'frontend': 'http://localhost:3000/api/health',
           'auth': 'http://localhost:8081/health'
       }
       for name, url in services.items():
           if not check_health(url):
               raise StartupError(f"{name} health check failed at {url}")
   ```

3. **Monitor in Production**
   - Set up alerts for health endpoint failures
   - Track response times for health checks
   - Monitor proxy error rates

## Success Criteria

### Development
- [ ] No "Failed to proxy" errors in logs
- [ ] All services consistently use correct ports
- [ ] Health checks return 200 within 500ms
- [ ] Frontend health check independent of backend

### Staging  
- [ ] Load balancer health checks enabled and passing
- [ ] All three services respond to health checks
- [ ] No 404 errors for health endpoints
- [ ] Health check monitoring dashboard available

## Rollback Plan

If issues persist after remediation:

1. **Development**: Revert to hardcoded ports everywhere, disable service discovery
2. **Staging**: Implement custom health check endpoint that aggregates all services
3. **Emergency**: Deploy health check bypass flag for critical deployments

## Timeline

- **Day 1**: Immediate fixes deployed to development
- **Day 2-3**: Configuration cleanup and SSOT implementation  
- **Week 1**: Architecture improvements and staging fixes
- **Week 2**: Full testing and validation complete

## Monitoring & Alerts

Set up monitoring for:
- Health endpoint response times > 1s
- Health endpoint failures (non-200 responses)
- Port mismatch errors in logs
- Proxy connection refused errors

## Documentation Updates

Update these documents post-remediation:
- `SPEC/health_check_architecture.xml`
- `docs/deployment/health-checks.md`
- `LLM_MASTER_INDEX.md` - Add health check section
- `CLAUDE.md` - Add health check verification to checklist

## Risk Assessment

**High Risk**:
- Port mismatch causes complete API failure in development
- Disabled health checks in staging can cause traffic to unhealthy instances

**Medium Risk**:
- Health check timeouts during high load
- Cascading failures if health aggregation implemented incorrectly

**Low Risk**:
- Minor performance impact from separate health endpoints

## Post-Implementation Review

After implementation, conduct review to verify:
1. All environments use consistent port configuration
2. Health checks respond correctly in all environments
3. No regression in existing functionality
4. Improved mean time to detection (MTTD) for service failures

---

**Priority**: CRITICAL  
**Estimated Effort**: 3-5 days  
**Business Impact**: High - affects development velocity and staging reliability