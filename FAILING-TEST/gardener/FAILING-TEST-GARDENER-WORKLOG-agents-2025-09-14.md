# Failing Test Gardener Worklog - Agents Focus - 2025-09-14

## Test Focus: Agent Tests
**Created:** 2025-09-14  
**Scope:** Agent-related unit, integration, and E2E tests  
**Goal:** Identify and catalog failing agent tests for GitHub issue creation/updates  

## Discovered Issues

### Test Execution Log

#### 1. Mission Critical WebSocket Agent Events Suite - 3 FAILURES
**File:** `tests/mission_critical/test_websocket_agent_events_suite.py`  
**Run Time:** 2025-09-14 06:43:28  
**Status:** 39 collected, 36 passed, 3 FAILED  

**Failures:**
1. **`test_agent_started_event_structure`**
   - **Error:** `AssertionError: agent_started event structure validation failed`
   - **Issue:** Event structure validation fails for agent_started events
   - **Severity:** P1 - High (breaks core chat functionality)
   - **Category:** failing-test-regression-high

2. **`test_tool_executing_event_structure`** 
   - **Error:** `AssertionError: tool_executing missing tool_name`
   - **Issue:** tool_executing events are missing required `tool_name` field
   - **Severity:** P1 - High (breaks tool transparency for users)
   - **Category:** failing-test-regression-high

3. **`test_tool_completed_event_structure`**
   - **Error:** `AssertionError: tool_completed missing results`
   - **Issue:** tool_completed events are missing required `results` field
   - **Severity:** P1 - High (breaks tool results display)
   - **Category:** failing-test-regression-high

**Context:** These are mission critical tests protecting $500K+ ARR chat functionality. All failures relate to WebSocket event structure validation which is essential for real-time user experience.