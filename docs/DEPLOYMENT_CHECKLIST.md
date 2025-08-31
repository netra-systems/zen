# Deployment Checklist - Mission Critical

## 🚨 CRITICAL: WebSocket Agent Events

**MUST PASS BEFORE ANY DEPLOYMENT**

### Pre-Deployment Requirements

#### 1. WebSocket Event Integration Tests
```bash
# MANDATORY - Run these tests before EVERY deployment
python -m pytest tests/mission_critical/test_final_validation.py -v
python -m pytest tests/mission_critical/test_websocket_agent_events_suite.py::TestRegressionPrevention -v
```

**Expected Output:**
- ✅ All 5 tests in `test_final_validation.py` MUST pass
- ✅ All regression prevention tests MUST pass
- ✅ Tool dispatcher enhancement MUST be verified

#### 2. Critical Event Verification
The following events MUST be sent during agent execution:
- `agent_started` - User sees processing began
- `agent_thinking` - Real-time reasoning visibility
- `tool_executing` - Tool usage transparency
- `tool_completed` - Tool results display
- `agent_completed` - User knows when done

#### 3. Integration Points Check
Verify these files have NOT been modified without running tests:
- `netra_backend/app/agents/supervisor/agent_registry.py` - Line 126-141 (set_websocket_manager)
- `netra_backend/app/agents/enhanced_tool_execution.py` - Enhancement function
- `netra_backend/app/agents/supervisor/websocket_notifier.py` - Event methods

### Automated Deployment Checks

#### Run Full Mission Critical Suite
```bash
# Complete mission critical validation
python -m pytest tests/mission_critical/ -v --tb=short

# Quick validation (< 2 seconds)
python -m pytest tests/mission_critical/test_final_validation.py -v
```

#### Performance Benchmarks
```bash
# Verify WebSocket throughput (must be > 500 events/sec)
python -m pytest tests/mission_critical/test_websocket_events_advanced.py::TestPerformanceBenchmarks::test_high_frequency_event_throughput -v
```

### Manual Verification Steps

1. **Local Testing**
   ```bash
   # Start development environment
   python dev_launcher/launcher.py
   
   # Send test message through chat UI
   # Verify in browser console:
   # - WebSocket events are received
   # - agent_started appears first
   # - agent_completed appears last
   ```

2. **Staging Verification**
   - Deploy to staging first
   - Open browser developer tools
   - Send chat message
   - Monitor Network > WS tab
   - Verify all 5 critical events appear

### Rollback Criteria

**IMMEDIATELY ROLLBACK IF:**
- ❌ Any mission critical test fails
- ❌ WebSocket events not appearing in frontend
- ❌ Tool execution events missing
- ❌ Chat UI appears "frozen" (no real-time updates)

### Post-Deployment Monitoring

Monitor these metrics in production:
- WebSocket event count per minute
- Missing event type alerts
- Tool event pairing (executing/completed ratio)
- Agent completion rate

### Related Documentation

- [WebSocket Integration Learning](SPEC/learnings/websocket_agent_integration_critical.xml)
- [Mission Critical Tests](tests/mission_critical/README.md)
- [CLAUDE.md Requirements](CLAUDE.md#6-mission-critical-websocket-agent-events)

---

## Standard Deployment Checklist

### 1. Pre-Deployment Tests
```bash
# Run unified test suite
python scripts/unified_test_runner.py --categories smoke unit integration api --real-llm --env staging

# Architecture compliance
python scripts/check_architecture_compliance.py
```

### 2. Environment Configuration
- [ ] Verify `.env` files for target environment
- [ ] Check SERVICE_SECRET and SERVICE_ID are set
- [ ] Validate OAuth redirect URIs match deployment URL
- [ ] Confirm JWT_SECRET_KEY is consistent across services

### 3. Database Migrations
```bash
# Check for pending migrations
alembic current
alembic check

# Apply migrations if needed
alembic upgrade head
```

### 4. Docker & Dependencies
```bash
# Build containers
docker-compose build

# Verify all services start
docker-compose up -d
docker-compose ps
```

### 5. Deployment Execution
```bash
# Deploy to GCP
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Verify deployment
gcloud run services list
```

### 6. Post-Deployment Validation
- [ ] Health check endpoints responding
- [ ] Authentication flow working
- [ ] WebSocket connections establishing
- [ ] Agent execution completing
- [ ] Metrics being collected

### 7. Monitoring Setup
- [ ] Prometheus metrics accessible
- [ ] Grafana dashboards loading
- [ ] Error alerting configured
- [ ] SLO tracking enabled

## Emergency Contacts

- **Critical Issues**: Check SPEC/learnings/index.xml first
- **WebSocket Problems**: See websocket_agent_integration_critical.xml
- **Rollback Instructions**: Use previous Cloud Run revision

## Version History

- **2025-08-30**: Added mission critical WebSocket checks
- **2025-08-23**: Initial deployment checklist created