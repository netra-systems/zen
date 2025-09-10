# SSOT-regression-AgentRegistry-interface-violation.md

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/215
**Status:** In Progress - Discovery Complete
**Priority:** CRITICAL - Golden Path Blocker

## Issue Summary
AgentRegistry interface violation between child and parent class causing WebSocket handshake race conditions that block Golden Path user flow (login → AI responses).

## Technical Details
- **File:** `netra_backend/app/agents/supervisor/agent_registry.py:263`
- **Class:** `class AgentRegistry(UniversalAgentRegistry)`
- **Method:** `set_websocket_manager()` (lines 631-675)
- **Violation:** Liskov Substitution Principle - passing WebSocketManager objects to parent expecting AgentWebSocketBridge objects

## Business Impact
- **Revenue Risk:** $500K+ ARR dependency on chat functionality
- **User Experience:** 5 business-critical WebSocket events fail to deliver
- **System Stability:** Race conditions in Cloud Run environments

## Discovery Phase Complete ✅
- [x] Identified critical SSOT violation in AgentRegistry
- [x] Created GitHub issue #215
- [x] Documented interface contract violation
- [x] Assessed Golden Path impact

## Next Steps
1. DISCOVER AND PLAN TEST phase
2. EXECUTE THE TEST PLAN phase  
3. PLAN REMEDIATION OF SSOT phase
4. EXECUTE THE REMEDIATION SSOT PLAN phase
5. ENTER TEST FIX LOOP phase
6. PR AND CLOSURE phase

## Progress Log
- **2025-01-09:** Discovery complete, identified interface violation as root cause