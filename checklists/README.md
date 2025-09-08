# Netra Operations Checklists & Runbooks

## 📋 Purpose
This directory contains critical checklists and runbooks for operating, maintaining, and troubleshooting the Netra Apex platform. These documents are designed to prevent common mistakes and provide quick recovery procedures.

## 🚨 Most Critical Documents

1. **[COMMON_MISTAKES_RUNBOOK.md](./COMMON_MISTAKES_RUNBOOK.md)** - Top 10 mistakes that break everything
2. **[MASTER_CLASS_VERIFICATION_CHECKLIST.md](./MASTER_CLASS_VERIFICATION_CHECKLIST.md)** - Critical classes to always verify
3. **[WEBSOCKET_EVENT_VERIFICATION_CHECKLIST.md](./WEBSOCKET_EVENT_VERIFICATION_CHECKLIST.md)** - Ensuring chat value delivery

## 📚 Complete Document Index

### Verification Checklists
- **[MASTER_CLASS_VERIFICATION_CHECKLIST.md](./MASTER_CLASS_VERIFICATION_CHECKLIST.md)**
  - Ultra-critical classes that must be checked
  - Per-module verification procedures
  - Red flags to investigate immediately
  
- **[DEPLOYMENT_VERIFICATION_CHECKLIST.md](./DEPLOYMENT_VERIFICATION_CHECKLIST.md)**
  - Pre-deployment quality gates
  - Staging validation steps
  - Production deployment procedures
  - Rollback criteria and procedures
  
- **[WEBSOCKET_EVENT_VERIFICATION_CHECKLIST.md](./WEBSOCKET_EVENT_VERIFICATION_CHECKLIST.md)**
  - 5 critical events for chat business value
  - Integration points to verify
  - Performance requirements
  - Multi-user isolation testing

### Operational Runbooks
- **[COMMON_MISTAKES_RUNBOOK.md](./COMMON_MISTAKES_RUNBOOK.md)**
  - Top 10 most common breaking mistakes
  - Race condition patterns to avoid
  - Emergency recovery procedures
  - Prevention strategies
  
- **[CONFIGURATION_VALIDATION_RUNBOOK.md](./CONFIGURATION_VALIDATION_RUNBOOK.md)**
  - Configuration hierarchy and validation
  - Service-specific configuration checks
  - Common configuration issues and fixes
  - Secret management validation
  
- **[TEST_FAILURE_DIAGNOSIS_RUNBOOK.md](./TEST_FAILURE_DIAGNOSIS_RUNBOOK.md)**
  - Test failure diagnosis flow
  - Common test failure patterns
  - Service-specific diagnosis procedures
  - Debug output analysis techniques

## 🔥 Quick Reference - Most Common Issues

### Issue: Authentication Fails Every Minute
**File**: [COMMON_MISTAKES_RUNBOOK.md](./COMMON_MISTAKES_RUNBOOK.md#1-service_id-with-timestamps)
**Quick Fix**: SERVICE_ID must be "netra-backend" (no timestamps)

### Issue: Chat Appears Frozen
**File**: [WEBSOCKET_EVENT_VERIFICATION_CHECKLIST.md](./WEBSOCKET_EVENT_VERIFICATION_CHECKLIST.md)
**Quick Fix**: Run `python tests/mission_critical/test_websocket_agent_events_suite.py`

### Issue: E2E Tests Show 0.00s Execution
**File**: [TEST_FAILURE_DIAGNOSIS_RUNBOOK.md](./TEST_FAILURE_DIAGNOSIS_RUNBOOK.md#1-e2e-test-shows-000s-execution)
**Quick Fix**: Remove mocks, use --real-services flag

### Issue: Staging Using Production Resources
**File**: [CONFIGURATION_VALIDATION_RUNBOOK.md](./CONFIGURATION_VALIDATION_RUNBOOK.md#issue-2-wrong-environment-urls)
**Quick Fix**: Check environment isolation in .env files

### Issue: User A Sees User B's Data
**File**: [COMMON_MISTAKES_RUNBOOK.md](./COMMON_MISTAKES_RUNBOOK.md#5-shared-state-between-users)
**Quick Fix**: Use factory pattern for user-specific instances

## 🎯 Usage Guidelines

### For Daily Development
1. Review [MASTER_CLASS_VERIFICATION_CHECKLIST.md](./MASTER_CLASS_VERIFICATION_CHECKLIST.md) before modifying critical classes
2. Check [COMMON_MISTAKES_RUNBOOK.md](./COMMON_MISTAKES_RUNBOOK.md) when something breaks
3. Use [TEST_FAILURE_DIAGNOSIS_RUNBOOK.md](./TEST_FAILURE_DIAGNOSIS_RUNBOOK.md) when tests fail

### For Deployments
1. Complete [DEPLOYMENT_VERIFICATION_CHECKLIST.md](./DEPLOYMENT_VERIFICATION_CHECKLIST.md) step by step
2. Validate configuration with [CONFIGURATION_VALIDATION_RUNBOOK.md](./CONFIGURATION_VALIDATION_RUNBOOK.md)
3. Verify WebSocket events with [WEBSOCKET_EVENT_VERIFICATION_CHECKLIST.md](./WEBSOCKET_EVENT_VERIFICATION_CHECKLIST.md)

### For Troubleshooting
1. Start with symptoms in [COMMON_MISTAKES_RUNBOOK.md](./COMMON_MISTAKES_RUNBOOK.md)
2. Follow diagnosis procedures in relevant runbook
3. Apply emergency recovery procedures if needed
4. Document new issues for future reference

## 📊 Key Metrics to Monitor

- **WebSocket Events**: All 5 critical events firing (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- **Authentication**: SERVICE_ID stability, JWT consistency
- **Configuration**: Environment isolation, no config leakage
- **Tests**: No 0.00s execution times, real services used
- **Multi-user**: Complete isolation between users

## 🔗 Related Documentation

- **[SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml](../SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml)** - Critical values that cause cascade failures
- **[CLAUDE.md](../CLAUDE.md)** - Core development principles and guidelines
- **[reports/DEFINITION_OF_DONE_CHECKLIST.md](../reports/DEFINITION_OF_DONE_CHECKLIST.md)** - Module-specific completion criteria
- **[docs/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md](../docs/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)** - Test infrastructure guide

## ⚡ Emergency Commands

```bash
# Quick system health check
python scripts/check_auth_ssot_compliance.py
python tests/mission_critical/test_websocket_agent_events_suite.py

# Start all services
python tests/unified_test_runner.py --real-services --keep-alive

# Force WebSocket reinitialization
python -c "
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
import asyncio
asyncio.run(AgentWebSocketBridge.get_instance().ensure_integration(force_reinit=True))
"

# Validate all configurations
python scripts/check_architecture_compliance.py --config-only
```

## 📝 Maintenance Notes

These documents should be updated when:
- New critical classes are added
- Common failure patterns emerge
- Configuration structure changes
- Deployment procedures evolve
- New test categories are introduced

Last Updated: 2025-09-07
Maintained By: Engineering Team