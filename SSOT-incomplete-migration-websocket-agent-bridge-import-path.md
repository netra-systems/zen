# SSOT Incomplete Migration: WebSocket Agent Bridge Import Path

**Issue #360:** https://github.com/netra-systems/netra-apex/issues/360
**Priority:** P0 CRITICAL - Golden Path Blocker
**Impact:** $500K+ ARR at risk - blocks user login → AI response flow

## Problem Summary

WebSocket agent bridge imports are using incorrect legacy paths that don't exist, preventing Golden Path functionality.

**BROKEN PATH:**
```python
from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge  # ❌
```

**CORRECT SSOT PATH:**
```python
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge  # ✅
```

## Critical Files Requiring Fix

1. `tests/integration/websocket_agent_bridge/test_websocket_ssot_agent_integration.py:26`
2. `tests/e2e/staging/test_gcp_staging_websocket_agent_bridge_fix.py:47`
3. Additional files to be identified in discovery phase

## Process Status

- [x] **Step 0:** SSOT Audit Complete - Critical violation identified
- [ ] **Step 1:** Discover and Plan Tests
- [ ] **Step 2:** Execute Test Plan (20% new SSOT tests)
- [ ] **Step 3:** Plan SSOT Remediation
- [ ] **Step 4:** Execute Remediation
- [ ] **Step 5:** Test Fix Loop
- [ ] **Step 6:** PR and Closure

## Business Impact

This fix enables the core chat functionality that delivers 90% of platform value. Without it:
- Users cannot receive AI responses
- WebSocket agent communication fails
- Golden Path user flow is broken

## Next Actions

1. Comprehensive test discovery for WebSocket agent bridge functionality
2. Plan test coverage for import path corrections
3. Execute systematic import path updates