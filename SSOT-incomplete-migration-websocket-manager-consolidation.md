# SSOT-incomplete-migration-websocket-manager-consolidation

## Issue Summary
WebSocket Manager SSOT Consolidation Required - Three different manager implementations violate SSOT

## GitHub Issue
- Issue: To be created
- Link: Pending

## Current Status
- **Priority:** HIGH - $500K+ ARR risk
- **Phase:** Step 0 - Discovery Complete

## SSOT Violations Found

### 1. WebSocket Manager Triplication
**Files:**
- `/netra_backend/app/websocket_core/manager.py` - Compatibility layer
- `/netra_backend/app/websocket_core/unified_manager.py` - Core implementation  
- `/netra_backend/app/websocket_core/websocket_manager.py` - SSOT facade

**Issue:** Three different manager files exist when there should be ONE

### 2. Import Path Fragmentation
- Over 1,700+ files contain WebSocket manager references
- Multiple import paths for same class
- Compatibility shims required

## Test Discovery
- Existing tests to protect: TBD
- New tests needed: TBD

## Remediation Plan
1. Consolidate to single WebSocketManager class
2. Remove compatibility layers
3. Update all import paths
4. Ensure backward compatibility during transition

## Progress Log
- 2025-09-17: Initial SSOT audit complete
- 2025-09-17: Critical violations identified