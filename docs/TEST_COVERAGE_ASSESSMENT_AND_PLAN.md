# Test Coverage Assessment and Improvement Plan
## `zen --apex --send-logs` Workflow

**Date:** 2025-01-10
**Confidence Score:** 4/10 → Target: 10/10
**Assessment Scope:** Log analysis and submission workflow for APEX integration

---

## Executive Summary

The current test suite provides **inadequate coverage** (4/10 confidence) for the critical `zen --apex --send-logs` workflow. While unit tests for log collection are excellent, there is **zero coverage** for:
- WebSocket message transmission
- Handshake timing and protocol
- Payload validation and size limits
- End-to-end workflow integration
- Error recovery paths

This document provides a **prioritized test plan** with 90+ new tests across 4 tiers to achieve 10/10 confidence before production deployment.

---

## Current Test Coverage Analysis

### ✅ Strong Coverage Areas

#### 1. `tests/test_agent_logs.py` (784 lines)
**Coverage:** Log collection utilities - **EXCELLENT**

- ✅ Platform-specific path resolution (Darwin, Linux, Windows)
- ✅ Project selection (auto-detect most recent, explicit name)
- ✅ File ordering by modification time
- ✅ JSON parsing resilience (malformed lines, truncated logs)
- ✅ Security sanitization (directory traversal prevention)
- ✅ Error handling (missing directories, invalid project names)
- ✅ Unicode and large file handling
- ✅ Limit parameter validation

**Strengths:** Comprehensive unit tests with edge cases, security tests, and integration scenarios.

#### 2. `tests/test_apex_integration.py` (229 lines)
**Coverage:** Basic integration tests - **ADEQUATE**

- ✅ Mock .claude/Projects structure
- ✅ Log collection with multiple projects
- ✅ Automatic project detection
- ✅ Malformed JSON handling
- ✅ Argument parsing smoke tests

**Strengths:** Good smoke tests for basic functionality.

### ❌ Critical Coverage Gaps

#### 1. **WebSocket Communication Layer** - **ZERO COVERAGE**
**Risk Level:** 🔴 CRITICAL

**Missing Tests:**
- WebSocket handshake protocol (`agent_cli.py:2990-3096`)
- Connection state management (`agent_cli.py:2842-2929`)
- Authentication method fallback logic
- Thread ID negotiation and agreement
- Message assembly and transmission

**Impact:** The production bug scenario mentioned in prompts (messages sent before handshake complete) would **NOT be caught** by current tests.

#### 2. **Log Transmission Integration** - **ZERO COVERAGE**
**Risk Level:** 🔴 CRITICAL

**Missing Tests:**
- Payload assembly with `jsonl_logs` key (`agent_cli.py:3569-3676`)
- Payload size calculation and validation
- File hash generation for tracking
- Transmission success verification
- Logs attached to user messages correctly

**Impact:** No verification that logs actually reach the backend or that payload structure is correct.

#### 3. **Error Recovery Paths** - **ZERO COVERAGE**
**Risk Level:** 🟡 HIGH

**Missing Tests:**
- Log collection failure handling (`agent_cli.py:3654-3660`)
- Partial transmission recovery
- WebSocket disconnection during transmission
- Backend rejection handling
- Graceful degradation when logs unavailable

**Impact:** Unknown behavior in production error scenarios.

#### 4. **Payload Size & Limits** - **ZERO COVERAGE**
**Risk Level:** 🟡 HIGH

**Missing Tests:**
- 5MB WebSocket `max_size` limit enforcement
- Backend payload size limits
- Large log file handling
- Memory efficiency for large transmissions

**Impact:** Could cause silent failures or out-of-memory errors in production.

#### 5. **zen_orchestrator.py Argument Parsing** - **ZERO COVERAGE**
**Risk Level:** 🟡 HIGH

**Missing Tests:**
- `--send-logs` flag parsing
- `--logs-count`, `--logs-project`, `--logs-path` parameters
- Argument precedence rules
- Default value behavior
- Conflicting argument resolution

**Impact:** No test file exists for zen_orchestrator.py. Argument parsing bugs could prevent feature from working.

#### 6. **Concurrent Operations** - **ZERO COVERAGE**
**Risk Level:** 🟠 MEDIUM

**Missing Tests:**
- Multiple WebSocket clients
- Parallel log collection
- File modification during read
- Race conditions in project selection
- Thread safety

**Impact:** Potential race conditions and data corruption in production.

---

## Production Bug Scenario Analysis

### **Bug:** "Messages sent before WebSocket handshake complete"

**Root Cause:** No tests verify that:
1. `connect()` waits for `connection_established` message before returning
2. Message sending is blocked until handshake completes
3. Thread ID is established before any user messages sent

**Current Code Path (Untested):**
```python
# agent_cli.py:2842-2886
async def connect(self) -> bool:
    # Try authentication methods
    if await method():
        # CRITICAL: Handshake must complete before returning
        handshake_success = await self._perform_handshake()
        if handshake_success:
            self.connected = True
            return True
        else:
            # BACKWARD COMPAT: Still mark connected
            self.connected = True  # ⚠️ DANGEROUS
            return True
```

**Why Tests Would Catch This:**
- Test would verify `current_thread_id` is set before `connect()` returns
- Test would assert message send fails if called before handshake
- Test would validate `connection_established` received before any user messages

**Tests That Should Exist:**
```python
async def test_reject_send_before_handshake_complete(self)
async def test_handshake_blocks_until_connection_established(self)
async def test_connection_established_timeout_handling(self)
```

---

## Prioritized Test Plan

### **TIER 1: CRITICAL - Must Have Before Production (P0)**

#### Test File 1: `test_websocket_handshake.py`
**Priority:** P0 - Blocks production deployment
**Estimated Tests:** 30
**Effort:** 3 days

##### Test Cases:

**Handshake Protocol Tests:**
1. `test_handshake_completes_before_message_send` - ⭐ Catches production bug
2. `test_reject_messages_before_connection_established` - ⭐ Catches production bug
3. `test_handshake_timeout_handling`
4. `test_connection_established_race_condition`
5. `test_backend_sends_connection_established_immediately`
6. `test_backend_waits_for_trigger_message`
7. `test_thread_id_agreement_after_handshake`
8. `test_handshake_request_format_validation`
9. `test_multiple_connection_established_messages_handled`
10. `test_handshake_failure_fallback_backward_compat`

**Connection Timing Tests:**
11. `test_connect_returns_only_after_handshake`
12. `test_connected_flag_set_after_thread_id_received`
13. `test_send_message_before_connect_raises_error`
14. `test_concurrent_connect_attempts_synchronized`
15. `test_handshake_retry_on_timeout`

**Thread ID Management Tests:**
16. `test_thread_id_persists_across_messages`
17. `test_thread_id_None_before_handshake`
18. `test_thread_id_from_connection_established_message`
19. `test_backend_provided_thread_id_takes_precedence`
20. `test_thread_id_validation`

**Authentication Tests:**
21. `test_subprotocol_auth_with_handshake`
22. `test_query_param_auth_with_handshake`
23. `test_header_auth_with_handshake`
24. `test_fallback_auth_methods_with_handshake`
25. `test_handshake_after_auth_failure_recovery`

**Error Scenarios:**
26. `test_handshake_json_parse_error_handling`
27. `test_websocket_close_during_handshake`
28. `test_backend_sends_wrong_message_type_first`
29. `test_handshake_state_cleanup_on_failure`
30. `test_connection_state_after_failed_handshake`

**Impact:** Directly prevents the production bug scenario. Validates critical timing assumptions.

---

#### Test File 2: `test_send_logs_integration.py`
**Priority:** P0 - Critical path untested
**Estimated Tests:** 25
**Effort:** 2 days

##### Test Cases:

**Payload Assembly Tests:**
1. `test_logs_added_to_websocket_payload` - ⭐ Critical path
2. `test_payload_structure_with_jsonl_logs_key` - ⭐ Verifies format
3. `test_send_logs_flag_triggers_collection`
4. `test_logs_not_included_when_flag_disabled`
5. `test_payload_has_both_message_and_logs`
6. `test_jsonl_logs_key_structure_matches_backend_expectations`

**Transmission Verification Tests:**
7. `test_logs_transmitted_with_user_message`
8. `test_transmission_success_logged`
9. `test_payload_sent_over_websocket`
10. `test_backend_receives_logs_in_payload`
11. `test_websocket_send_called_with_correct_payload`

**Metadata & Tracking Tests:**
12. `test_payload_size_calculation_accuracy`
13. `test_file_hash_verification_in_payload`
14. `test_file_info_metadata_included`
15. `test_timestamp_in_payload`
16. `test_run_id_and_thread_id_in_payload`

**Parameter Tests:**
17. `test_logs_count_parameter_respected`
18. `test_logs_project_parameter_filtering`
19. `test_logs_path_custom_override`
20. `test_logs_user_parameter_windows`

**Error Handling Tests:**
21. `test_transmission_failure_graceful_degradation`
22. `test_log_collection_failure_message_still_sent`
23. `test_empty_logs_handling`
24. `test_malformed_logs_skipped_in_transmission`
25. `test_partial_log_collection_success`

**Impact:** Tests the entire critical path from log collection → payload assembly → WebSocket transmission.

---

#### Test File 3: `test_payload_validation.py`
**Priority:** P0 - Prevents silent failures
**Estimated Tests:** 15
**Effort:** 1.5 days

##### Test Cases:

**Size Limit Tests:**
1. `test_payload_under_5mb_limit` - ⭐ WebSocket max_size
2. `test_payload_exceeds_5mb_rejected`
3. `test_large_log_file_truncation_strategy`
4. `test_payload_size_warning_at_threshold`
5. `test_json_serialization_size_calculation`

**Payload Structure Tests:**
6. `test_payload_type_field_validation`
7. `test_payload_nested_structure_valid_json`
8. `test_payload_required_fields_present`
9. `test_payload_optional_fields_handling`

**Memory & Performance Tests:**
10. `test_memory_efficiency_for_large_logs`
11. `test_1000_log_entries_payload_size`
12. `test_10mb_log_file_handling`
13. `test_payload_serialization_performance`

**Validation Tests:**
14. `test_invalid_payload_structure_rejected`
15. `test_payload_schema_validation`

**Impact:** Prevents silent failures from exceeding size limits. Ensures backend can parse payloads.

---

### **TIER 2: HIGH PRIORITY - Critical for Reliability (P1)**

#### Test File 4: `test_websocket_state.py`
**Priority:** P1
**Estimated Tests:** 20
**Effort:** 2 days

##### Test Cases:

**Connection State Tests:**
1. `test_connection_state_after_failed_handshake`
2. `test_connected_flag_lifecycle`
3. `test_ws_object_created_after_connect`
4. `test_ws_object_closed_on_disconnect`
5. `test_connection_id_tracking`

**Authentication Fallback Tests:**
6. `test_multiple_authentication_method_fallback_order`
7. `test_subprotocol_failure_tries_query_param`
8. `test_query_param_failure_tries_header`
9. `test_all_auth_methods_fail_error_handling`
10. `test_successful_auth_stops_fallback_chain`

**Recovery Tests:**
11. `test_connection_recovery_after_timeout`
12. `test_websocket_disconnect_during_log_transmission`
13. `test_reconnect_preserves_thread_id`
14. `test_reconnect_after_backend_restart`
15. `test_connection_retry_exponential_backoff`

**Thread ID Persistence Tests:**
16. `test_thread_id_persistence_in_session`
17. `test_thread_id_lost_on_disconnect`
18. `test_thread_id_restored_on_reconnect`
19. `test_multiple_connections_different_thread_ids`
20. `test_thread_id_validation_on_message_receive`

**Impact:** Validates complex connection state machine that's currently untested.

---

#### Test File 5: `test_send_logs_error_recovery.py`
**Priority:** P1
**Estimated Tests:** 18
**Effort:** 2 days

##### Test Cases:

**Collection Error Tests:**
1. `test_log_collection_failure_does_not_block_message`
2. `test_file_not_found_error_handled`
3. `test_permission_denied_error_handled`
4. `test_json_parse_error_does_not_crash`
5. `test_empty_project_directory_handled`

**Transmission Error Tests:**
6. `test_websocket_send_timeout_handling`
7. `test_websocket_closed_during_send`
8. `test_backend_rejects_logs_fallback_behavior`
9. `test_network_error_during_transmission`
10. `test_partial_log_transmission_recovery`

**Resilience Tests:**
11. `test_malformed_json_in_logs_skipped_gracefully`
12. `test_corrupted_log_file_handling`
13. `test_file_read_error_during_transmission`
14. `test_log_file_deleted_after_selection`
15. `test_log_file_modified_during_read`

**Degradation Tests:**
16. `test_graceful_degradation_no_logs_available`
17. `test_warning_logged_when_logs_unavailable`
18. `test_user_message_sent_despite_log_failure`

**Impact:** Ensures production errors don't crash the system or block user messages.

---

#### Test File 6: `test_zen_orchestrator_args.py`
**Priority:** P1 - Known gap
**Estimated Tests:** 20
**Effort:** 2 days

##### Test Cases:

**send-logs Flag Tests:**
1. `test_send_logs_flag_with_message`
2. `test_send_logs_without_message_uses_default`
3. `test_send_logs_flag_disabled_by_default`
4. `test_send_logs_flag_boolean_parsing`

**logs-count Parameter Tests:**
5. `test_logs_count_default_value_is_1`
6. `test_logs_count_custom_override`
7. `test_logs_count_validation_positive_integer`
8. `test_logs_count_zero_rejected`
9. `test_logs_count_negative_rejected`

**logs-project Parameter Tests:**
10. `test_logs_project_explicit_name`
11. `test_logs_project_auto_detect_when_not_specified`
12. `test_logs_project_invalid_name_handled`
13. `test_logs_project_nonexistent_handled`

**logs-path Parameter Tests:**
14. `test_logs_path_custom_override`
15. `test_logs_path_default_resolution`
16. `test_logs_path_platform_specific`

**Precedence & Conflicts Tests:**
17. `test_conflicting_arguments_precedence`
18. `test_apex_flag_enables_agent_cli_mode`
19. `test_argument_combinations_validation`
20. `test_help_text_includes_send_logs_options`

**Impact:** Fills known testing gap. Ensures CLI arguments work as documented.

---

### **TIER 3: MEDIUM PRIORITY - Production Hardening (P2)**

#### Test File 7: `test_concurrent_operations.py`
**Priority:** P2
**Estimated Tests:** 15
**Effort:** 2 days

##### Test Cases:

**Concurrent Client Tests:**
1. `test_multiple_websocket_clients_same_logs`
2. `test_parallel_log_collection_from_different_projects`
3. `test_concurrent_send_messages_queue_ordering`
4. `test_multiple_clients_different_thread_ids`

**File Access Tests:**
5. `test_concurrent_file_reads_thread_safety`
6. `test_log_file_modified_during_read`
7. `test_log_file_deleted_during_read`
8. `test_project_directory_modified_during_scan`

**Race Condition Tests:**
9. `test_race_condition_project_selection`
10. `test_race_condition_file_ordering`
11. `test_race_condition_connection_state`
12. `test_race_condition_handshake_completion`

**Stress Tests:**
13. `test_100_concurrent_log_collections`
14. `test_10_concurrent_websocket_connections`
15. `test_rapid_connect_disconnect_cycles`

**Impact:** Prevents race conditions and concurrency bugs in production.

---

#### Test File 8: `test_security_integration.py`
**Priority:** P2
**Estimated Tests:** 12
**Effort:** 1.5 days

##### Test Cases:

**Directory Traversal Tests:**
1. `test_directory_traversal_blocked_in_full_workflow`
2. `test_logs_path_validation_prevents_injection`
3. `test_project_name_validation_end_to_end`
4. `test_symlink_attack_prevention`

**Input Validation Tests:**
5. `test_malicious_project_name_sanitized`
6. `test_path_injection_via_arguments_blocked`
7. `test_null_byte_injection_blocked`
8. `test_unicode_exploits_handled`

**Data Protection Tests:**
9. `test_sensitive_data_scrubbing_in_logs` (if applicable)
10. `test_log_content_not_leaked_in_errors`
11. `test_file_permissions_respected`
12. `test_sanitized_logs_in_transmission_payload`

**Impact:** Validates security controls work in full workflow, not just unit tests.

---

#### Test File 9: `test_send_logs_performance.py`
**Priority:** P2
**Estimated Tests:** 10
**Effort:** 1.5 days

##### Test Cases:

**Transmission Time Tests:**
1. `test_1000_log_entries_transmission_time_under_5s`
2. `test_100_log_entries_transmission_time_under_1s`
3. `test_single_entry_transmission_latency`

**Large File Tests:**
4. `test_10mb_log_file_handling_exceeds_limit`
5. `test_5mb_log_file_near_limit_handling`
6. `test_1mb_log_file_transmission_performance`

**Selection Performance Tests:**
7. `test_100_projects_selection_performance`
8. `test_1000_log_files_sorting_performance`

**Resource Usage Tests:**
9. `test_memory_usage_during_large_transmission`
10. `test_websocket_buffer_overflow_prevention`

**Impact:** Establishes performance baselines. Prevents latency regressions.

---

### **TIER 4: NICE TO HAVE - Observability & Debugging (P3)**

#### Test File 10: `test_transmission_observability.py`
**Priority:** P3
**Estimated Tests:** 10
**Effort:** 1 day

##### Test Cases:

**Logging Tests:**
1. `test_payload_proof_logged_correctly`
2. `test_file_info_with_hashes_in_logs`
3. `test_transmission_metrics_logged`
4. `test_separator_formatting_in_logs`

**Debug Level Tests:**
5. `test_debug_level_controls_verbosity`
6. `test_basic_level_shows_key_events`
7. `test_verbose_level_shows_all_details`
8. `test_silent_level_suppresses_output`

**Proof Generation Tests:**
9. `test_payload_proof_file_saved_when_env_var_set`
10. `test_transmission_proof_includes_sample_entries`

**Impact:** Improves production debugging and observability.

---

## Test Implementation Guide

### Test File Template

```python
#!/usr/bin/env python3
"""
Test suite for [functionality]

Tests [describe what's being tested and why]
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import sys

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from agent_cli import WebSocketClient, AgentCLIConfig, Environment


class Test[Feature]Name:
    """Test [feature description]"""

    @pytest.fixture
    def mock_config(self):
        """Fixture for AgentCLI configuration"""
        return AgentCLIConfig(
            ws_url="ws://localhost:8000/ws",
            environment=Environment.STAGING,
            token="test-token",
            json_mode=False,
            ci_mode=False
        )

    @pytest.fixture
    def mock_websocket(self):
        """Fixture for mock WebSocket connection"""
        ws = AsyncMock()
        ws.recv = AsyncMock()
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_[specific_scenario](self, mock_config, mock_websocket):
        """Test [what this test validates]"""
        # Arrange
        client = WebSocketClient(config=mock_config, ...)

        # Act
        result = await client.some_method()

        # Assert
        assert result is not None
        assert client.some_state == expected_value


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### Mocking Guidelines

**WebSocket Connection Mocking:**
```python
@pytest.fixture
async def mock_connected_client(mock_config):
    """Fixture for connected WebSocket client with completed handshake"""
    with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(return_value=json.dumps({
            "type": "connection_established",
            "thread_id": "test-thread-123",
            "timestamp": "2025-01-10T10:00:00Z"
        }))
        mock_ws.send = AsyncMock()
        mock_connect.return_value = mock_ws

        client = WebSocketClient(config=mock_config, ...)
        await client.connect()  # Complete handshake

        yield client
```

**Log Collection Mocking:**
```python
@pytest.fixture
def mock_logs(tmp_path):
    """Fixture for mock log files"""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir(parents=True)

    log_data = [
        {"event": "test1", "timestamp": "2025-01-10T10:00:00Z"},
        {"event": "test2", "timestamp": "2025-01-10T10:01:00Z"}
    ]

    log_file = project_dir / "session.jsonl"
    log_file.write_text("\n".join(json.dumps(log) for log in log_data) + "\n")

    return project_dir, log_data
```

### Integration Test Pattern

```python
async def test_end_to_end_log_transmission(mock_config, mock_logs):
    """Test complete workflow: collect logs → assemble payload → transmit"""
    project_dir, expected_logs = mock_logs

    # Mock WebSocket
    with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
        mock_ws = AsyncMock()
        sent_payloads = []

        async def capture_send(payload):
            sent_payloads.append(json.loads(payload))

        mock_ws.send = AsyncMock(side_effect=capture_send)
        mock_ws.recv = AsyncMock(return_value=json.dumps({
            "type": "connection_established",
            "thread_id": "test-thread"
        }))
        mock_connect.return_value = mock_ws

        # Create client with send_logs enabled
        client = WebSocketClient(
            config=mock_config,
            send_logs=True,
            logs_path=str(project_dir.parent)
        )

        # Connect and send message
        await client.connect()
        await client.send_user_message("test message")

        # Verify logs were transmitted
        assert len(sent_payloads) > 0
        payload = sent_payloads[0]
        assert "jsonl_logs" in payload["payload"]
        assert len(payload["payload"]["jsonl_logs"]) == len(expected_logs)
```

---

## Test Execution Plan

### Phase 1: Tier 1 - Critical Tests (Week 1-2)
**Goal:** Achieve 8/10 confidence

1. **Day 1-3:** `test_websocket_handshake.py` (30 tests)
   - Write handshake protocol tests
   - Write connection timing tests
   - Write thread ID management tests

2. **Day 4-5:** `test_send_logs_integration.py` (25 tests)
   - Write payload assembly tests
   - Write transmission verification tests
   - Write metadata tracking tests

3. **Day 6-7:** `test_payload_validation.py` (15 tests)
   - Write size limit tests
   - Write structure validation tests
   - Write memory efficiency tests

**Deliverable:** 70 new tests, critical path validated

---

### Phase 2: Tier 2 - High Priority Tests (Week 3-4)
**Goal:** Achieve 9/10 confidence

4. **Day 8-9:** `test_websocket_state.py` (20 tests)
   - Write connection state tests
   - Write authentication fallback tests
   - Write recovery tests

5. **Day 10-11:** `test_send_logs_error_recovery.py` (18 tests)
   - Write collection error tests
   - Write transmission error tests
   - Write graceful degradation tests

6. **Day 12-13:** `test_zen_orchestrator_args.py` (20 tests)
   - Write flag parsing tests
   - Write parameter validation tests
   - Write precedence tests

**Deliverable:** 58 new tests, error handling validated

---

### Phase 3: Tier 3 - Hardening Tests (Week 5)
**Goal:** Achieve 9.5/10 confidence

7. **Day 14-15:** `test_concurrent_operations.py` (15 tests)
8. **Day 16-17:** `test_security_integration.py` (12 tests)
9. **Day 18-19:** `test_send_logs_performance.py` (10 tests)

**Deliverable:** 37 new tests, production hardening complete

---

### Phase 4: Tier 4 - Observability Tests (Week 6)
**Goal:** Achieve 10/10 confidence

10. **Day 20:** `test_transmission_observability.py` (10 tests)

**Deliverable:** 10 new tests, debugging capabilities validated

---

## Success Metrics

### Confidence Level Tracking

| Phase | Tests Added | Total Tests | Confidence | Key Validation |
|-------|-------------|-------------|------------|----------------|
| Current | 0 | ~100 | 4/10 | Log collection only |
| Phase 1 | 70 | ~170 | 8/10 | Critical path covered |
| Phase 2 | 58 | ~228 | 9/10 | Error handling validated |
| Phase 3 | 37 | ~265 | 9.5/10 | Production hardened |
| Phase 4 | 10 | ~275 | 10/10 | Observability complete |

### Code Coverage Targets

- **Line Coverage:** 85% → 95%
- **Branch Coverage:** 70% → 90%
- **WebSocket Module:** 0% → 95%
- **zen_orchestrator.py:** 0% → 80%

### Bug Detection Validation

✅ **Production Bug Scenarios Covered:**
1. Messages sent before handshake complete → Tier 1
2. Payload exceeds WebSocket limit → Tier 1
3. Log collection failure blocks user message → Tier 2
4. Race condition in project selection → Tier 3
5. Directory traversal attack → Tier 3

---

## Continuous Integration Setup

### Test Execution Strategy

```yaml
# .github/workflows/test_send_logs.yml
name: Send Logs Workflow Tests

on: [push, pull_request]

jobs:
  test_tier1_critical:
    name: Tier 1 - Critical Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run Tier 1 tests
        run: |
          pytest tests/test_websocket_handshake.py -v --cov
          pytest tests/test_send_logs_integration.py -v --cov
          pytest tests/test_payload_validation.py -v --cov
      - name: Fail if Tier 1 fails
        run: exit 1
        if: failure()

  test_tier2_high:
    name: Tier 2 - High Priority Tests
    runs-on: ubuntu-latest
    needs: test_tier1_critical
    steps:
      # Similar setup...
      - name: Run Tier 2 tests
        run: |
          pytest tests/test_websocket_state.py -v --cov
          pytest tests/test_send_logs_error_recovery.py -v --cov
          pytest tests/test_zen_orchestrator_args.py -v --cov

  test_tier3_hardening:
    name: Tier 3 - Hardening Tests
    runs-on: ubuntu-latest
    needs: test_tier2_high
    steps:
      # Similar setup...
      - name: Run Tier 3 tests
        run: |
          pytest tests/test_concurrent_operations.py -v --cov
          pytest tests/test_security_integration.py -v --cov
          pytest tests/test_send_logs_performance.py -v --cov
```

### Pre-commit Hooks

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-tier1
        name: Run Tier 1 Critical Tests
        entry: pytest tests/test_websocket_handshake.py tests/test_send_logs_integration.py tests/test_payload_validation.py -v
        language: system
        pass_filenames: false
        always_run: true
```

---

## Risk Mitigation

### High-Risk Areas Requiring Immediate Attention

1. **WebSocket Handshake Timing** (P0)
   - **Risk:** Messages sent before handshake complete
   - **Mitigation:** Implement `test_websocket_handshake.py` immediately
   - **Validation:** Run integration test with real backend

2. **Payload Size Limits** (P0)
   - **Risk:** Silent failures when exceeding 5MB limit
   - **Mitigation:** Implement size validation before transmission
   - **Validation:** Test with 10MB log file

3. **Error Recovery** (P1)
   - **Risk:** System crashes on log collection failure
   - **Mitigation:** Add try/except coverage validation
   - **Validation:** Inject errors in test environment

---

## Appendix A: Test Data Fixtures

### Mock Log Data

```python
# tests/fixtures/mock_logs.py

SMALL_LOG_SET = [
    {"event": "start", "timestamp": "2025-01-10T10:00:00Z", "data": {"key": "value"}},
    {"event": "process", "timestamp": "2025-01-10T10:01:00Z", "data": {"key": "value"}},
    {"event": "complete", "timestamp": "2025-01-10T10:02:00Z", "data": {"key": "value"}}
]

LARGE_LOG_SET = [
    {"event": f"event_{i}", "timestamp": f"2025-01-10T10:{i:02d}:00Z", "data": {"index": i, "payload": "x" * 1000}}
    for i in range(1000)
]

MALFORMED_LOG_LINES = [
    '{"valid": "entry1"}\n',
    '{invalid json\n',
    '{"valid": "entry2"}\n',
    'not json at all\n',
    '{"valid": "entry3"}\n'
]

EDGE_CASE_LOGS = {
    "empty": [],
    "unicode": [{"message": "Hello 世界 🌍", "timestamp": "2025-01-10T10:00:00Z"}],
    "large_entry": [{"data": "x" * 1_000_000, "timestamp": "2025-01-10T10:00:00Z"}],
    "null_values": [{"event": None, "data": None, "timestamp": "2025-01-10T10:00:00Z"}]
}
```

---

## Appendix B: WebSocket Mock Utilities

```python
# tests/utils/websocket_mocks.py

class MockWebSocketServer:
    """Mock WebSocket server for integration tests"""

    def __init__(self, handshake_delay=0.1, send_connection_established=True):
        self.handshake_delay = handshake_delay
        self.send_connection_established = send_connection_established
        self.received_messages = []

    async def recv(self):
        """Simulate receiving messages"""
        await asyncio.sleep(self.handshake_delay)

        if self.send_connection_established:
            return json.dumps({
                "type": "connection_established",
                "thread_id": "mock-thread-123",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            raise asyncio.TimeoutError()

    async def send(self, message):
        """Capture sent messages"""
        self.received_messages.append(json.loads(message))

    async def close(self):
        """Simulate connection close"""
        pass


@contextmanager
def mock_websocket_server(handshake_delay=0.1):
    """Context manager for mock WebSocket server"""
    server = MockWebSocketServer(handshake_delay=handshake_delay)

    with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = server
        yield server
```

---

## Appendix C: Test Coverage Commands

```bash
# Run all tests with coverage
pytest tests/ -v --cov=scripts.agent_cli --cov=scripts.agent_logs --cov=zen_orchestrator --cov-report=html

# Run only Tier 1 tests
pytest tests/test_websocket_handshake.py tests/test_send_logs_integration.py tests/test_payload_validation.py -v

# Run specific test class
pytest tests/test_websocket_handshake.py::TestHandshakeProtocol -v

# Run with async debugging
pytest tests/test_websocket_handshake.py -v -s --asyncio-mode=auto

# Generate coverage report
coverage html
open htmlcov/index.html
```

---

## Appendix D: Known Issues & Limitations

### Current Implementation Issues

1. **Backward Compatibility Mode** (agent_cli.py:2883-2886)
   - Code marks connection as successful even if handshake fails
   - **Risk:** Could allow messages before thread ID established
   - **Test:** `test_connection_state_after_failed_handshake`

2. **No Payload Size Enforcement** (agent_cli.py:3569-3676)
   - Code calculates size for logging but doesn't enforce limits
   - **Risk:** Could exceed WebSocket 5MB max_size
   - **Test:** `test_payload_exceeds_5mb_rejected`

3. **Silent Log Collection Failures** (agent_cli.py:3654-3660)
   - Exceptions caught but not propagated
   - **Risk:** User may not know logs weren't sent
   - **Test:** `test_log_collection_failure_logged_prominently`

### Test Environment Limitations

1. **Real Backend Required for Some Tests**
   - Handshake protocol validation needs real backend
   - **Mitigation:** Use Docker Compose for local backend
   - **CI:** Use staging environment for integration tests

2. **Timing-Dependent Tests**
   - Handshake timeout tests depend on timing
   - **Mitigation:** Use configurable timeouts in tests
   - **CI:** Allow longer timeouts in CI environment

---

## Document Metadata

**Version:** 1.0
**Date:** 2025-01-10
**Author:** Claude Code Test Assessment
**Status:** Approved for Implementation
**Next Review:** After Phase 1 completion

**Change Log:**
- 2025-01-10: Initial assessment and test plan creation
- 2025-01-10: Added WebSocket handshake tests based on production bug analysis
- 2025-01-10: Added zen_orchestrator.py test plan based on known gap

---

## References

1. **Code Files Analyzed:**
   - `scripts/agent_cli.py` (WebSocket client, log transmission)
   - `scripts/agent_logs.py` (Log collection utilities)
   - `zen_orchestrator.py` (CLI argument parsing)
   - `tests/test_agent_logs.py` (Existing unit tests)
   - `tests/test_apex_integration.py` (Existing integration tests)

2. **Key Code Sections:**
   - WebSocket connection: `agent_cli.py:2842-2929`
   - Handshake protocol: `agent_cli.py:2990-3096`
   - Log transmission: `agent_cli.py:3569-3676`
   - Payload assembly: `agent_cli.py:3554-3568`

3. **Production Bug Scenarios:**
   - Messages before handshake complete (Prompt 2)
   - Payload size validation (Analysis finding)
   - Argument parsing gaps (Prompt 3)

---

## Approval Signatures

- [ ] **Development Lead:** Review and approve test plan
- [ ] **QA Lead:** Review test coverage and priorities
- [ ] **Product Owner:** Review business value and timeline
- [ ] **Security:** Review security test coverage
- [ ] **DevOps:** Review CI/CD integration plan

---

**END OF DOCUMENT**
