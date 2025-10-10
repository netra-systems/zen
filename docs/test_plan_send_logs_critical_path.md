# Test Plan: `zen --apex --send-logs` - Critical Path Validation

**Document Version**: 1.0
**Date**: 2025-10-10
**Status**: Active
**Owner**: QA/Engineering

---

## Executive Summary

This document defines the comprehensive test plan for Zen's **core feature**: the `--send-logs` functionality that collects Claude Code usage logs and transmits them for optimization analysis. This represents the primary business value proposition: "Free more claude usage through optimization."

**Business Context**: A failure in this workflow means the core product value is broken, resulting in 100% revenue risk for this feature.

---

## Table of Contents

1. [Workflow Overview](#workflow-overview)
2. [Critical Success Criteria](#critical-success-criteria)
3. [Test Execution Matrix](#test-execution-matrix)
4. [Test Scenarios](#test-scenarios)
5. [Validation Checklist](#validation-checklist)
6. [Failure Impact Analysis](#failure-impact-analysis)
7. [Code References](#code-references)

---

## Workflow Overview

### End-to-End Flow

```
User Command
    ↓
zen --apex --send-logs
    ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Log Collection (agent_logs.py)                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Resolve platform-specific .claude/Projects path          │
│ 2. Find most recent project (or use --logs-project)         │
│ 3. Collect JSONL files (limit by --logs-count, default: 1)  │
│ 4. Parse JSON entries, skip malformed lines                 │
│ 5. Calculate file hashes and metadata                       │
│ 6. Return (logs, files_read, file_info)                     │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Payload Construction (agent_cli.py)                │
├─────────────────────────────────────────────────────────────┤
│ 1. Create base payload with type, run_id, thread_id         │
│ 2. Attach logs to payload["payload"]["jsonl_logs"]          │
│ 3. Calculate payload size (bytes → KB → MB)                 │
│ 4. Generate transmission proof banner with:                 │
│    - Total entries count                                    │
│    - Files read count                                       │
│    - File hashes                                            │
│    - First/last log timestamps                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: Transmission (agent_cli.py)                        │
├─────────────────────────────────────────────────────────────┤
│ 1. Send payload via WebSocket                               │
│ 2. Display transmission proof                               │
│ 3. Wait for backend agent response (timeout: 300s)          │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: Backend Processing (not tested in this plan)       │
├─────────────────────────────────────────────────────────────┤
│ 1. claude_code_optimizer agent receives logs                │
│ 2. Analyzes for optimization opportunities                  │
│ 3. Returns structured recommendations                       │
└─────────────────────────────────────────────────────────────┘
    ↓
Optimization Results Displayed to User
```

---

## Critical Success Criteria

### Criterion 1: Log Collection Accuracy & Security 🔒

**Priority**: P0 - CRITICAL
**Revenue Impact if Failed**: 100%

#### Success Definition

- ✅ Correctly identifies most recent project directory by modification time
- ✅ Reads exact number of log files specified by `--logs-count` (default: 1)
- ✅ Parses all valid JSONL entries, skips malformed JSON gracefully without crashing
- ✅ **Security**: Blocks directory traversal attacks (e.g., `../../etc/passwd`)
- ✅ Handles missing directories/files without crashing, returns None gracefully
- ✅ Supports direct file paths (`.jsonl` files) in addition to directory paths
- ✅ Unicode content (emoji, non-ASCII) parsed correctly

#### Test Coverage

```python
# Unit Tests (tests/test_agent_logs.py)
test_collect_recent_logs_basic                      # Line 401
test_collect_recent_logs_most_recent_project        # Line 441
test_collect_recent_logs_mixed_valid_invalid_json   # Line 587
test_sanitize_project_name_rejects_parent_dir_traversal  # Line 131
test_scenario_security_traversal_blocked            # Line 760
test_collect_jsonl_files_unicode_content            # Line 376
```

#### Validation Points

**File**: `scripts/agent_logs.py`

- **Lines 212-327**: `collect_recent_logs()` - Main entry point
- **Lines 68-96**: `_sanitize_project_name()` - Security validation
- **Lines 131-209**: `_collect_jsonl_files()` - JSONL parsing with error resilience
- **Lines 29-65**: `_resolve_projects_root()` - Platform path resolution

#### Test Commands

```bash
# Happy path - default behavior
zen --apex --send-logs

# Custom project
zen --apex --send-logs --logs-project "my-project-name"

# Custom directory path
zen --apex --send-logs --logs-path "/path/to/.claude/Projects"

# Direct file path
zen --apex --send-logs --logs-path "/Users/user/.claude/Projects/proj/session.jsonl"

# Security test - should fail gracefully
zen --apex --send-logs --logs-project "../../etc/passwd"
```

#### Expected Behavior

**Success Case**:
```
============================================================
📤 SENDING LOGS TO OPTIMIZER
============================================================
  Total Entries: 781
  Files Read: 1
  Payload Size: 5.52 MB
  ...
```

**Security Violation**:
```
Warning: --send-logs enabled but no logs found
```

**No Logs Found**:
```
Warning: --send-logs enabled but no logs found
```

---

### Criterion 2: Payload Structure Integrity 📦

**Priority**: P0 - CRITICAL
**Revenue Impact if Failed**: 100%

#### Success Definition

- ✅ Payload contains `payload.jsonl_logs` key with array of log entries
- ✅ Logs maintain original JSONL structure (not corrupted during serialization)
- ✅ Metadata included: file info (name, hash, entry count) for verification
- ✅ Payload size calculated correctly (accurate byte count with proper KB/MB formatting)
- ✅ First/last log timestamps extracted and displayed for transmission proof

#### Payload Structure Specification

```python
# Expected WebSocket payload structure
{
  "type": "user_message",
  "payload": {
    "content": "analyze these logs",           # User message or default
    "run_id": "cli_20251008_113255_25048",    # Unique run identifier
    "thread_id": "cli_thread_f887c58e7759",   # Thread identifier
    "timestamp": "2025-10-10T12:34:56.789",   # ISO format
    "client_environment": "staging",          # Optional
    "jsonl_logs": [                           # ← CRITICAL KEY
      {
        "timestamp": "2025-10-03T18:26:02.089Z",
        "type": "agent_started",
        "payload": {...}
      },
      {
        "timestamp": "2025-10-03T19:31:21.876Z",
        "type": "agent_completed",
        "payload": {...}
      }
      // ... more log entries
    ]
  }
}
```

#### Validation Points

**File**: `scripts/agent_cli.py`

- **Lines 3569-3580**: Log collection and attachment logic
- **Line 3583**: `payload["payload"]["jsonl_logs"] = logs` - Critical assignment
- **Lines 3585-3647**: Payload size calculation and banner generation
- **Lines 3669-3676**: Transmission proof validation
- **Lines 3739-3744**: Payload proof for JSON mode

#### Test Commands

```bash
# Enable payload proof file for verification
export ZEN_SAVE_PAYLOAD_PROOF=1
zen --apex --send-logs

# Verify payload structure
cat /tmp/zen_payload_proof_*.json
```

#### Expected Behavior

```python
# Payload proof output
{
  "run_id": "cli_20251008_113255_25048",
  "payload": {
    "message": "analyze these logs",
    "jsonl_logs": {
      "count": 781,
      "sample_first": {
        "timestamp": "2025-10-03T18:26:02.089Z",
        "type": "agent_started"
      },
      "sample_last": {
        "timestamp": "2025-10-03T19:31:21.876Z",
        "type": "agent_completed"
      }
    }
  }
}
```

---

### Criterion 3: Transmission Proof & Observability 📊

**Priority**: P1 - HIGH
**Revenue Impact if Failed**: 60% (trust loss)

#### Success Definition

- ✅ Pre-transmission banner displays:
  - Total entries count (exact number)
  - Files read count (should match --logs-count)
  - Payload size (formatted: bytes for <1KB, KB for <1MB, MB for ≥1MB)
  - File details with hashes (8-char SHA256 prefix)
- ✅ Transmission proof message after send:
  - "✓ TRANSMISSION PROOF: Payload contains X JSONL log entries"
  - First log entry timestamp
  - Last log entry timestamp
- ✅ Warning if `--send-logs` enabled but no logs found
- ✅ Non-blocking error handling: log collection failure doesn't prevent message sending

#### Validation Points

**File**: `scripts/agent_cli.py`

- **Lines 3604-3647**: Pre-transmission banner construction
- **Lines 3669-3676**: Transmission proof logging
- **Lines 3649-3660**: Error handling and warnings

#### Expected Output

```
============================================================
📤 SENDING LOGS TO OPTIMIZER
============================================================
  Total Entries: 781
  Files Read: 1
  Payload Size: 5.52 MB

  Files:
    • 7ac6d7ac-abc3-4903-a482-.....jsonl (hash: 908dbc51, 781 entries)

  Payload Confirmation:
    ✓ 'jsonl_logs' key added to payload
    ✓ First log entry timestamp: 2025-10-03T18:26:02.089Z
    ✓ Last log entry timestamp: 2025-10-03T19:31:21.876Z
============================================================

[11:32:55.191] [DEBUG] ✓ TRANSMISSION PROOF: Payload contains 781 JSONL log entries in 'jsonl_logs' key
```

#### Test Scenarios

1. **Normal transmission**: Verify all fields present and accurate
2. **No logs found**: Verify warning message displays
3. **Collection failure**: Verify error message displays, transmission continues
4. **Large payload**: Verify size formatting (MB display for >1MB)

---

### Criterion 4: Multi-Environment Compatibility 🖥️

**Priority**: P0 - CRITICAL
**Revenue Impact if Failed**: 40% (market loss - Windows users)

#### Success Definition

- ✅ **macOS**: Resolves `~/.claude/Projects` correctly
- ✅ **Windows**: Handles `C:\Users\<username>\.claude\Projects` with USERPROFILE
- ✅ **Linux**: Resolves `~/.claude/Projects` correctly
- ✅ Custom paths via `--logs-path` work on all platforms
- ✅ Direct file paths (`.jsonl` file) supported on all platforms
- ✅ Path separators handled correctly (forward slash vs backslash)

#### Platform-Specific Path Resolution

| Platform | Default Path | Environment Variable |
|----------|--------------|---------------------|
| **macOS** | `~/.claude/Projects` | `HOME` |
| **Linux** | `~/.claude/Projects` | `HOME` |
| **Windows** | `C:\Users\<user>\.claude\Projects` | `USERPROFILE` or `USERNAME` |

#### Validation Points

**File**: `scripts/agent_logs.py`

- **Lines 29-65**: `_resolve_projects_root()` - Platform-specific path resolution
- **Lines 19-26**: `_get_default_user()` - Windows username resolution
- **Lines 239-293**: Direct file path support

#### Test Coverage

```python
# Unit Tests (tests/test_agent_logs.py)
test_resolve_projects_root_macos                    # Line 64
test_resolve_projects_root_linux                    # Line 70
test_resolve_projects_root_windows_with_username    # Line 76
test_resolve_projects_root_windows_with_userprofile # Line 81
test_scenario_cross_platform_paths                  # Line 748
```

#### Test Commands

```bash
# macOS/Linux
zen --apex --send-logs
# Should resolve: /Users/<user>/.claude/Projects or /home/<user>/.claude/Projects

# Windows (PowerShell)
zen --apex --send-logs
# Should resolve: C:\Users\<user>\.claude\Projects

# Custom path (all platforms)
zen --apex --send-logs --logs-path "/custom/path/to/Projects"

# Direct file (all platforms)
zen --apex --send-logs --logs-path "/full/path/to/session.jsonl"
```

---

### Criterion 5: End-to-End Success - Optimization Response Received 🎯

**Priority**: P0 - CRITICAL
**Revenue Impact if Failed**: 100% (core business value)

#### Success Definition

- ✅ Logs successfully transmitted via WebSocket
- ✅ Backend `claude_code_optimizer` agent receives logs
- ✅ Agent processes logs and returns optimization recommendations
- ✅ Response includes structured data:
  - `optimizations` array with individual issues
  - Each optimization contains: `issue`, `evidence`, `token_waste`, `fix`, `priority`
  - `summary` with `total_issues`, `estimated_savings`, `top_priority`
- ✅ Total time < 300s (WebSocket timeout increased in agent_cli.py)
- ✅ User receives actionable recommendations

#### Expected Event Sequence

```
[Time] [Event Type]          [Description]
────────────────────────────────────────────────────────────────
11:32:55  WebSocket connected    Connection established
11:33:01  thread_created         Thread initialized
11:33:02  agent_started          netra-assistant started
11:33:06  agent_started          MessageHandler started
11:33:14  agent_started          claude_code_optimizer started
11:33:23  agent_thinking         "Preparing optimization prompt"
11:34:27  agent_completed        claude_code_optimizer completed
          Final Result           Optimization recommendations displayed
```

#### Expected Response Structure

```json
{
  "status": "done",
  "result": {
    "optimizations": [
      {
        "issue": "Repeated Full File Read",
        "evidence": "The file `api/src/routes/user.js` was read in its entirety using `cat` twice...",
        "token_waste": "High (~2.5k tokens)",
        "fix": "The model should use targeted tools like `grep` or `read_lines`...",
        "ideal_prompt": "The user profile page isn't loading...",
        "priority": "high"
      },
      {
        "issue": "Excessive Context Gathering",
        "evidence": "The `cat` command was used on two large files...",
        "token_waste": "High (~4k tokens)",
        "fix": "Use more precise tools to gather context...",
        "ideal_prompt": "The `findUser` function in `api/src/db/utils.js`...",
        "priority": "high"
      },
      {
        "issue": "Inefficient Project-Wide Search",
        "evidence": "A recursive grep (`grep -r \"findUser\" .`) was used...",
        "token_waste": "Medium (~500 tokens)",
        "fix": "Use targeted search in known directories...",
        "ideal_prompt": "The `findUser` function, defined in the `api/src/db/` directory...",
        "priority": "low"
      }
    ],
    "summary": {
      "total_issues": 3,
      "estimated_savings": "~7k tokens",
      "top_priority": "Avoid repeated full file reads..."
    }
  },
  "message": "Claude Code optimization analysis complete"
}
```

#### Validation Points

1. **WebSocket Connection**: Successful connection to staging/production backend
2. **Event Flow**: All expected events received in correct order
3. **Response Structure**: JSON response matches expected schema
4. **Actionable Output**: Each optimization includes concrete fix suggestions
5. **Performance**: Total execution time < 300s

#### Test Commands

```bash
# Full end-to-end test
zen --apex --send-logs

# With specific project
zen --apex --send-logs --logs-project "my-claude-project"

# With custom message
zen --apex --send-logs --message "analyze for token waste"

# Verify timeout handling
zen --apex --send-logs --wait 300
```

---

## Test Execution Matrix

| Test Scenario | Collection | Payload | Transmission | Platform | E2E | Priority |
|--------------|:----------:|:-------:|:------------:|:--------:|:---:|:--------:|
| **Happy Path Tests** |
| Default (most recent project) | ✅ | ✅ | ✅ | macOS | ✅ | P0 |
| Custom project name | ✅ | ✅ | ✅ | macOS | ✅ | P0 |
| Custom directory path | ✅ | ✅ | ✅ | macOS | ✅ | P0 |
| Direct file path | ✅ | ✅ | ✅ | macOS | ✅ | P1 |
| Multiple files (--logs-count 2) | ✅ | ✅ | ✅ | macOS | ✅ | P1 |
| Large payload (>1MB) | ✅ | ✅ | ✅ | macOS | ⚠️ | P1 |
| **Error Handling Tests** |
| Malformed JSON resilience | ✅ | ✅ | - | - | - | P0 |
| Empty project directory | ✅ | ✅ | ✅ | - | - | P1 |
| No logs found warning | ✅ | ✅ | ✅ | - | - | P1 |
| Nonexistent project | ✅ | ✅ | ✅ | - | - | P1 |
| Collection failure (permissions) | ✅ | ✅ | ✅ | - | - | P2 |
| **Security Tests** |
| Directory traversal (`../../etc/passwd`) | ✅ | - | - | - | - | P0 |
| Null byte injection | ✅ | - | - | - | - | P0 |
| Path separator injection | ✅ | - | - | - | - | P0 |
| **Platform Tests** |
| macOS default path | ✅ | ✅ | ✅ | macOS | ✅ | P0 |
| Linux default path | ✅ | ✅ | ✅ | Linux | ✅ | P0 |
| Windows USERPROFILE | ✅ | ✅ | ✅ | Windows | ✅ | P0 |
| Windows USERNAME fallback | ✅ | - | - | Windows | - | P1 |
| Cross-platform custom paths | ✅ | ✅ | ✅ | All | ✅ | P1 |
| **Performance Tests** |
| 1 file, <100 entries | ✅ | ✅ | ✅ | - | ✅ | P1 |
| 1 file, 500-1000 entries | ✅ | ✅ | ✅ | - | ✅ | P0 |
| 1 file, >1000 entries | ✅ | ✅ | ✅ | - | ⚠️ | P1 |
| Payload <1MB (recommended) | ✅ | ✅ | ✅ | - | ✅ | P0 |
| Payload 1-5MB | ✅ | ✅ | ✅ | - | ⚠️ | P1 |
| Payload >5MB | ✅ | ✅ | ⚠️ | - | ❌ | P2 |

**Legend**:
- ✅ Must Pass
- ⚠️ Warning Expected (acceptable degradation)
- ❌ Expected Failure (document limitation)
- `-` Not Applicable
- **Priority**: P0=Critical, P1=High, P2=Medium

---

## Test Scenarios

### Scenario 1: Default Behavior (Happy Path)

**Objective**: Verify basic functionality with no custom flags

**Command**:
```bash
zen --apex --send-logs
```

**Pre-conditions**:
- `.claude/Projects` directory exists
- At least one project with `.jsonl` files exists
- User authenticated to staging/production backend

**Expected Behavior**:
1. Auto-detects platform (macOS/Windows/Linux)
2. Resolves default `.claude/Projects` path
3. Finds most recent project by modification time
4. Reads 1 log file (default `--logs-count`)
5. Displays transmission banner with accurate metadata
6. Sends payload via WebSocket
7. Receives optimization recommendations

**Validation**:
- [ ] Log collection completes without errors
- [ ] Transmission banner shows correct file count (1)
- [ ] Payload size calculated accurately
- [ ] Transmission proof displays
- [ ] Backend agent responds with optimizations
- [ ] Total time < 300s

---

### Scenario 2: Custom Project Selection

**Objective**: Verify explicit project name targeting

**Command**:
```bash
zen --apex --send-logs --logs-project "my-specific-project"
```

**Pre-conditions**:
- `.claude/Projects/my-specific-project` directory exists
- Project contains `.jsonl` files

**Expected Behavior**:
1. Skips auto-detection of most recent project
2. Targets specified project directory
3. Sanitizes project name (security check)
4. Collects logs from specified project only

**Validation**:
- [ ] Correct project directory used (not most recent)
- [ ] Transmission banner shows project name
- [ ] Security: rejects `../../` patterns
- [ ] File info shows correct project files

---

### Scenario 3: Direct File Path

**Objective**: Verify single file targeting

**Command**:
```bash
zen --apex --send-logs --logs-path "/Users/user/.claude/Projects/proj/session-123.jsonl"
```

**Pre-conditions**:
- Specified `.jsonl` file exists and is readable

**Expected Behavior**:
1. Detects `--logs-path` is a file (not directory)
2. Reads single file directly
3. Skips project discovery logic
4. Files read count = 1

**Validation**:
- [ ] Only specified file processed
- [ ] File hash matches file content
- [ ] Entry count matches file line count
- [ ] Transmission banner shows single file

---

### Scenario 4: Multiple Files

**Objective**: Verify `--logs-count` parameter

**Command**:
```bash
zen --apex --send-logs --logs-count 3
```

**Pre-conditions**:
- Most recent project has ≥3 `.jsonl` files

**Expected Behavior**:
1. Reads 3 most recent files (by modification time)
2. Aggregates entries from all files
3. Files read count = 3
4. Total entries = sum of all file entries

**Validation**:
- [ ] Exactly 3 files processed
- [ ] Files ordered by modification time (newest first)
- [ ] All entries from all 3 files included
- [ ] Transmission banner lists all 3 files with hashes

**Note**: Per README.md, recommend `--logs-count 1` for optimal analysis.

---

### Scenario 5: Malformed JSON Resilience

**Objective**: Verify error handling for corrupted log files

**Test Setup**:
Create test file with mixed valid/invalid JSON:
```jsonl
{"valid": "entry1"}
{invalid json here
{"valid": "entry2"}
not json at all
{"valid": "entry3"}
```

**Expected Behavior**:
1. Parser skips malformed lines silently
2. Continues processing remaining file
3. Collects only valid entries (3 entries)
4. Logs debug warnings for malformed lines (not displayed to user)

**Validation**:
- [ ] No crash or exception
- [ ] Only valid entries collected
- [ ] Entry count matches valid lines
- [ ] Transmission continues successfully

---

### Scenario 6: No Logs Found

**Objective**: Verify graceful handling when no logs exist

**Test Cases**:
1. Empty project directory
2. Nonexistent project name
3. No `.jsonl` files in project

**Expected Behavior**:
```
Warning: --send-logs enabled but no logs found
```

**Validation**:
- [ ] Warning message displays
- [ ] Message sending continues (without logs)
- [ ] No crash or exception
- [ ] Payload contains no `jsonl_logs` key

---

### Scenario 7: Directory Traversal Attack

**Objective**: Verify security against malicious input

**Command**:
```bash
zen --apex --send-logs --logs-project "../../etc/passwd"
```

**Expected Behavior**:
1. `_sanitize_project_name()` detects `..` pattern
2. Returns `None` from `collect_recent_logs()`
3. Displays warning: "no logs found"
4. Does NOT access `/etc/passwd`

**Validation**:
- [ ] Security check triggers
- [ ] No file access outside `.claude/Projects`
- [ ] Warning message displays
- [ ] System files remain protected

---

### Scenario 8: Cross-Platform Path Resolution

**Objective**: Verify platform-specific path handling

**Test Matrix**:

| Platform | Test Command | Expected Path |
|----------|-------------|---------------|
| macOS | `zen --apex --send-logs` | `/Users/<user>/.claude/Projects` |
| Linux | `zen --apex --send-logs` | `/home/<user>/.claude/Projects` |
| Windows | `zen --apex --send-logs` | `C:\Users\<user>\.claude\Projects` |
| All | `zen --apex --send-logs --logs-path "/custom"` | `/custom` (or `\custom` on Windows) |

**Validation**:
- [ ] Correct platform detected
- [ ] Path separators handled correctly (/ vs \)
- [ ] Environment variables resolved (HOME, USERPROFILE)
- [ ] Custom paths override platform defaults

---

### Scenario 9: Large Payload Handling

**Objective**: Verify behavior with payloads >1MB

**Test Setup**:
Create or use session log with >1000 entries

**Expected Behavior**:
1. Payload size displays in MB format (e.g., "5.52 MB")
2. Transmission may take longer (monitor timeout)
3. Backend may respond slower or with warnings

**Validation**:
- [ ] Size calculation accurate
- [ ] MB formatting displays correctly
- [ ] WebSocket timeout sufficient (300s)
- [ ] Backend processing completes or provides feedback

**Note**: Per README.md, recommend payloads <1MB for optimal results.

---

### Scenario 10: End-to-End Integration Test

**Objective**: Verify complete workflow from collection to optimization

**Command**:
```bash
zen --apex --send-logs --env staging
```

**Expected Event Sequence** (with timestamps):
```
[T+0s]   SUCCESS: WebSocket connected successfully!
[T+1s]   📤 SENDING LOGS TO OPTIMIZER (banner displays)
[T+2s]   ✓ TRANSMISSION PROOF: Payload contains X entries
[T+3s]   SUCCESS: Message sent with run_id: cli_...
[T+4s]   ⏳ Waiting 300 seconds for events...
[T+5s]   [CONN] Connected as: e2e-staging-2d677771
[T+6s]   [EVENT] thread_created
[T+7s]   🧠 Agent: netra-assistant started
[T+8s]   🧠 Agent: MessageHandler started
[T+15s]  🧠 Agent: claude_code_optimizer started
[T+20s]  💭 Thinking: Preparing optimization prompt
[T+90s]  🧠 Agent Completed: claude_code_optimizer
[T+91s]  ╭─── Final Agent Result - Optimization Pointers ───╮
         │ {                                                 │
         │   "status": "done",                               │
         │   "result": {                                     │
         │     "optimizations": [...]                        │
         │   }                                               │
         │ }                                                 │
         ╰───────────────────────────────────────────────────╯
```

**Validation Checklist**:
- [ ] WebSocket connection successful
- [ ] Transmission banner displays
- [ ] Transmission proof confirms log attachment
- [ ] All expected events received in order
- [ ] `claude_code_optimizer` agent starts
- [ ] Agent completes with `status: "done"`
- [ ] Response contains `optimizations` array
- [ ] Each optimization has required fields:
  - [ ] `issue` (string)
  - [ ] `evidence` (string)
  - [ ] `token_waste` (string)
  - [ ] `fix` (string)
  - [ ] `priority` ("high", "medium", "low")
- [ ] Summary includes:
  - [ ] `total_issues` (number)
  - [ ] `estimated_savings` (string)
  - [ ] `top_priority` (string)
- [ ] Total execution time < 300s

---

## Validation Checklist

### Pre-Flight Checks

Before running any test:

- [ ] Claude Code CLI installed and authenticated
- [ ] Zen package installed (`pip show netra-zen` succeeds)
- [ ] `.claude/Projects` directory exists with test data
- [ ] Python version ≥ 3.8
- [ ] Required dependencies installed (`requirements.txt`)

### Per-Test Validation

For each test scenario:

**Phase 1: Log Collection**
- [ ] No exceptions during collection
- [ ] Correct number of files read (matches `--logs-count`)
- [ ] File hashes calculated (8-char SHA256 prefix)
- [ ] Entry count matches actual log lines
- [ ] Malformed JSON skipped gracefully

**Phase 2: Payload Construction**
- [ ] `payload["payload"]["jsonl_logs"]` key exists
- [ ] `jsonl_logs` is an array
- [ ] Log entries maintain original structure
- [ ] Payload size calculated accurately
- [ ] Size formatting correct (bytes/KB/MB)

**Phase 3: Transmission**
- [ ] Transmission banner displays
- [ ] All banner fields populated correctly
- [ ] Transmission proof displays after send
- [ ] WebSocket connection successful
- [ ] Message sent with run_id

**Phase 4: Backend Response**
- [ ] `claude_code_optimizer` agent starts
- [ ] Agent completes (not timeout)
- [ ] Response structure matches schema
- [ ] Optimizations are actionable

### Post-Test Validation

After test completion:

- [ ] No lingering processes (`ps aux | grep zen`)
- [ ] No temp files left behind (if `ZEN_SAVE_PAYLOAD_PROOF` used)
- [ ] Logs reviewed for errors/warnings
- [ ] Performance metrics within acceptable range

---

## Failure Impact Analysis

| Criterion | Failure Symptom | User Impact | Business Impact | Revenue Risk |
|-----------|----------------|-------------|-----------------|--------------|
| **1. Log Collection** | No logs sent to backend | No optimization received | Core feature broken | **100%** |
| **2. Payload Structure** | Backend can't parse logs | No optimization received | Core feature broken | **100%** |
| **3. Transmission Proof** | User doubts logs were sent | Trust loss, support burden | Reputation damage | **60%** |
| **4. Platform Compatibility** | Windows users can't use feature | Market segmentation | Lost market share | **40%** |
| **5. E2E Optimization** | No recommendations returned | No value delivered | Promise unfulfilled | **100%** |

### Severity Definitions

- **P0 (Critical)**: Core feature broken, blocks all users, revenue impact >75%
- **P1 (High)**: Major functionality degraded, affects subset of users, revenue impact 25-75%
- **P2 (Medium)**: Minor functionality affected, workaround available, revenue impact <25%

### Escalation Path

1. **P0 Failure**: Immediate escalation to engineering lead + product owner
2. **P1 Failure**: Report within 4 hours, fix within 1 business day
3. **P2 Failure**: Report within 1 business day, fix in next sprint

---

## Code References

### Primary Implementation Files

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/agent_logs.py` | 1-328 | Log collection, parsing, security |
| `scripts/agent_cli.py` | 3569-3660 | Payload construction, transmission |
| `tests/test_agent_logs.py` | 1-784 | Unit test suite |

### Key Functions

#### Log Collection

```python
# scripts/agent_logs.py

def collect_recent_logs(
    limit: int = 1,
    project_name: Optional[str] = None,
    base_path: Optional[str] = None,
    username: Optional[str] = None,
    platform_name: Optional[str] = None
) -> Optional[tuple[List[Dict[str, Any]], int, List[Dict[str, str]]]]:
    """
    Main entry point for log collection.

    Returns:
        (logs, files_read, file_info) or None if no logs found
    """
    # Lines 212-327
```

```python
def _sanitize_project_name(project_name: str) -> str:
    """
    Security: prevent directory traversal attacks.

    Raises:
        ValueError: If dangerous patterns detected
    """
    # Lines 68-96
```

```python
def _collect_jsonl_files(project_path: Path, limit: int) -> tuple[List[Dict], int, List[Dict]]:
    """
    Parse JSONL files, skip malformed JSON gracefully.

    Returns:
        (all_logs, files_read, file_info)
    """
    # Lines 131-209
```

#### Payload Construction

```python
# scripts/agent_cli.py

async def send_message(self, message: str, thread_id: str) -> bool:
    """
    Construct payload and send via WebSocket.

    Key section: Lines 3569-3660
    """
    # Attach logs if --send-logs is enabled
    if self.send_logs:
        result = collect_recent_logs(...)
        if result:
            logs, files_read, file_info = result
            payload["payload"]["jsonl_logs"] = logs  # Line 3583
```

### Configuration

```python
# Default configuration values
DEFAULT_LOGS_COUNT = 1          # Recommended for optimal analysis
DEFAULT_LOGS_PATH = None        # Auto-detect platform
DEFAULT_LOGS_PROJECT = None     # Use most recent
WEBSOCKET_TIMEOUT = 300         # Increased for long-running optimizer
```

### Documentation

- **User Guide**: `README.md` lines 14-58 (Log Collection Options)
- **Example Output**: `README.md` lines 56-183 (Full session output)
- **Architecture**: `docs/apex_integration_test_plan.md`
- **CLI Design**: `docs/zen_agent_cli_parallel_plan.md`

---

## Appendix: Test Data Setup

### Creating Test Log Files

```bash
# Create test project structure
mkdir -p ~/.claude/Projects/test-project-1
mkdir -p ~/.claude/Projects/test-project-2

# Create valid log file
cat > ~/.claude/Projects/test-project-1/session-1.jsonl <<'EOF'
{"timestamp":"2025-10-10T10:00:00Z","type":"agent_started","payload":{"agent":"test"}}
{"timestamp":"2025-10-10T10:01:00Z","type":"tool_use","payload":{"tool":"Read","file":"test.py"}}
{"timestamp":"2025-10-10T10:02:00Z","type":"agent_completed","payload":{"status":"success"}}
EOF

# Create file with malformed JSON
cat > ~/.claude/Projects/test-project-1/session-2.jsonl <<'EOF'
{"timestamp":"2025-10-10T11:00:00Z","type":"agent_started"}
{invalid json here
{"timestamp":"2025-10-10T11:01:00Z","type":"agent_completed"}
EOF

# Make test-project-2 most recent
touch ~/.claude/Projects/test-project-2
sleep 1
cat > ~/.claude/Projects/test-project-2/session-latest.jsonl <<'EOF'
{"timestamp":"2025-10-10T12:00:00Z","type":"agent_started","payload":{"agent":"latest"}}
EOF
```

### Running Unit Tests

```bash
# Full test suite
cd /Users/rindhujajohnson/Netra/GitHub/zen
python -m pytest tests/test_agent_logs.py -v

# Specific test class
pytest tests/test_agent_logs.py::TestCollectRecentLogs -v

# Single test
pytest tests/test_agent_logs.py::TestCollectRecentLogs::test_collect_recent_logs_basic -v

# With coverage
pytest tests/test_agent_logs.py --cov=scripts.agent_logs --cov-report=html
```

### Manual Integration Test

```bash
# 1. Verify Claude Code authentication
claude auth status

# 2. Run with verbose output
zen --apex --send-logs --env staging

# 3. Monitor WebSocket events
# Look for:
# - "SUCCESS: WebSocket connected"
# - "📤 SENDING LOGS TO OPTIMIZER"
# - "✓ TRANSMISSION PROOF"
# - "🧠 Agent: claude_code_optimizer started"
# - "Final Agent Result"

# 4. Verify payload proof (optional)
export ZEN_SAVE_PAYLOAD_PROOF=1
zen --apex --send-logs
ls -lh /tmp/zen_payload_proof_*.json
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-10 | QA/Engineering | Initial release |

---

## Related Documents

- `README.md` - User-facing documentation
- `docs/apex_integration_test_plan.md` - Backend integration testing
- `tests/test_agent_logs.py` - Automated test suite
- `.temp/APEX_INTEGRATION.md` - Implementation notes
