# Test Plan: Config-Based Multi-Agent Orchestration

**Document Version**: 1.0
**Created**: 2025-10-10
**Owner**: Zen Orchestrator Team
**Status**: Active

---

## Executive Summary

This test plan validates the critical `--config` orchestration feature that enables multi-agent workflows. **If this feature fails for 1 hour, it would severely impact users running production data analysis pipelines, code review automation, and testing workflows.**

### Business Context

The orchestration system (`zen_orchestrator.py`) enables users to execute multiple Claude instances from a configuration file. This powers:

- **Data analysis pipelines**: Sequential workflows (collect → analyze → report → visualize)
- **Parallel code reviews**: Multiple agents analyzing different modules simultaneously
- **Testing automation**: Comprehensive test suite execution with failure analysis
- **Cost-controlled production**: Budget enforcement preventing overruns

**Critical Success Metric**: One failed instance must NEVER block other instances from completing.

---

## Test Categories

### 1. Configuration Loading & Parsing ⚡ CRITICAL

**Business Impact**: If config parsing fails, **entire workflow is blocked**.

#### Test 1.1: Valid Complex Configuration ✓ TIER 1
**File**: `tests/fixtures/valid_complex_config.json`

```json
{
  "instances": [
    {
      "name": "analyzer-1",
      "command": "/analyze-code",
      "description": "Analyzes codebase structure",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json",
      "max_tokens_per_command": 5000,
      "session_id": "analysis-session-1",
      "clear_history": false,
      "compact_history": true,
      "allowed_tools": ["Read", "Grep", "Glob", "Task"],
      "pre_commands": ["/clear", "Set context: Code analysis mode"]
    },
    {
      "name": "analyzer-2",
      "prompt": "What are the security vulnerabilities in this codebase?",
      "description": "Security vulnerability assessment",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json",
      "max_tokens_per_command": 8000,
      "session_id": "security-session-1"
    },
    {
      "name": "reporter",
      "command": "/generate comprehensive report; Include findings from both analyzers",
      "max_tokens_per_command": 12000,
      "session_id": "reporting-session"
    }
  ],
  "budget": {
    "overall_budget": 50000,
    "command_budgets": {
      "/analyze-code": 5000,
      "/generate": 12000
    },
    "command_cost_budgets": {
      "/analyze-code": 0.50
    },
    "budget_type": "mixed",
    "enforcement_mode": "block",
    "disable_visuals": false
  }
}
```

**Expected Results**:
- ✓ All 3 instances load successfully
- ✓ Budget configuration applied: overall=50000, per-command budgets set
- ✓ Session IDs assigned correctly
- ✓ Tool restrictions applied to analyzer-1
- ✓ Pre-commands stored for execution

**Verification Commands**:
```bash
zen --config tests/fixtures/valid_complex_config.json --dry-run
# Should show: "3 instances configured"
# Should display budget settings in output
```

**Code Reference**: `zen_orchestrator.py:2514-2525` (config loading)

---

#### Test 1.2: Malformed JSON ⚠️ TIER 2
**Business Impact**: Poor error handling wastes user debugging time.

**Test Scenarios**:

```json
// Scenario A: Missing comma
{
  "instances": [
    {"name": "test", "command": "/help"}
    {"name": "test2", "command": "/help"}  // ← Missing comma
  ]
}

// Scenario B: Unclosed bracket
{
  "instances": [
    {"name": "test", "command": "/help"
  ]

// Scenario C: Invalid quotes
{
  "instances": [
    {'name': "test", "command": "/help"}  // ← Single quotes
  ]
}
```

**Expected Results**:
- ✓ Clear error message: "JSON parsing error at line X"
- ✓ Exit code: 1
- ✓ No instances launched
- ✓ No hanging processes

**Anti-Pattern**: Silent failure or cryptic Python traceback

---

#### Test 1.3: Missing Required Fields ⚡ TIER 1
**Business Impact**: Prevents wasted execution time on invalid configs.

**Test Scenarios**:

```json
// Scenario A: Missing instances array
{
  "budget": {"overall_budget": 10000}
  // ← Missing "instances" key entirely
}

// Scenario B: Instance with neither command nor prompt
{
  "instances": [
    {
      "name": "broken-instance",
      "description": "This will fail"
      // ← No "command" or "prompt"
    }
  ]
}

// Scenario C: Empty command string
{
  "instances": [
    {
      "name": "empty-cmd",
      "command": "",  // ← Empty string
      "prompt": ""    // ← Both empty
    }
  ]
}
```

**Expected Results**:
- ✓ ValidationError raised with specific field name
- ✓ Error message: "Either 'command' or 'prompt' must be provided"
- ✓ Exit before launching any instances
- ✓ Clear indication of which instance is invalid

**Code Reference**: `zen_orchestrator.py:129-143` (InstanceConfig validation)

---

### 2. Multi-Instance Orchestration ⚡⚡⚡ CRITICAL

**Business Impact**: Core orchestration patterns - failure blocks ALL multi-agent workflows.

#### Test 2.1: Sequential Dependency Chain ✓ TIER 1 - HIGHEST PRIORITY
**Business Impact**: **Data analysis pipelines completely break if this fails.**

**Configuration**: `tests/fixtures/sequential_workflow.json`

```json
{
  "instances": [
    {
      "name": "data-collector",
      "command": "/help",
      "description": "Step 1: Collect data",
      "max_tokens_per_command": 2000
    },
    {
      "name": "statistical-analyzer",
      "command": "/help",
      "description": "Step 2: Analyze data",
      "max_tokens_per_command": 4000
    },
    {
      "name": "insight-reporter",
      "command": "/help",
      "description": "Step 3: Generate report",
      "max_tokens_per_command": 6000
    },
    {
      "name": "visualization-specialist",
      "command": "/help",
      "description": "Step 4: Create visualizations",
      "max_tokens_per_command": 3000
    }
  ]
}
```

**Verification Checklist**:
- [ ] Instance 1 starts immediately (delay = 0s)
- [ ] Instance 2 starts after 5s delay (configurable via `--startup-delay`)
- [ ] Instance 3 starts after 10s delay
- [ ] Instance 4 starts after 15s delay
- [ ] Status updates show progression: pending → running → completed
- [ ] Token usage tracked separately per instance
- [ ] Final summary shows all 4 completed with correct token totals
- [ ] No cross-contamination of outputs between instances

**Test Command**:
```bash
zen --config tests/fixtures/sequential_workflow.json \
    --startup-delay 5.0 \
    --status-report-interval 3 \
    --max-console-lines 20
```

**Expected Status Output** (at 12 seconds):
```
Instance Status Report (12s elapsed)
=====================================
data-collector          | ✓ completed | Tokens: 2000 | Time: 8.2s
statistical-analyzer    | ⏳ running  | Tokens: 1200 | Time: 5.1s
insight-reporter        | ⏸ pending   | Tokens: 0    | Time: 0s
visualization-specialist| ⏸ pending   | Tokens: 0    | Time: 0s
```

**Code Reference**: `zen_orchestrator.py:797-863` (`run_all_instances`)

---

#### Test 2.2: Parallel Independent Instances ⚡ TIER 2
**Business Impact**: Code review workflows where multiple reviewers analyze different modules.

**Configuration**: `tests/fixtures/parallel_workflow.json`

```json
{
  "instances": [
    {
      "name": "module-a-reviewer",
      "command": "/help",
      "session_id": "review-a",
      "max_tokens_per_command": 3000
    },
    {
      "name": "module-b-reviewer",
      "command": "/help",
      "session_id": "review-b",
      "max_tokens_per_command": 3000
    },
    {
      "name": "module-c-reviewer",
      "command": "/help",
      "session_id": "review-c",
      "max_tokens_per_command": 3000
    },
    {
      "name": "security-scanner",
      "command": "/help",
      "session_id": "security",
      "max_tokens_per_command": 5000
    },
    {
      "name": "performance-analyzer",
      "command": "/help",
      "session_id": "perf",
      "max_tokens_per_command": 4000
    }
  ]
}
```

**Verification Checklist**:
- [ ] All 5 instances show status="running" within 30 seconds
- [ ] Status report shows 5 concurrent PIDs
- [ ] Each instance has separate session_id (no context leakage)
- [ ] Output files/logs are instance-specific
- [ ] Total token usage = sum of all individual usages
- [ ] All 5 complete successfully without interference

**Test Command**:
```bash
zen --config tests/fixtures/parallel_workflow.json \
    --startup-delay 0.5 \
    --log-level detailed
```

**Expected Behavior**:
- Instance launches stagger by 0.5s each (total launch window: 2.5s)
- All run concurrently after launch
- No blocking between instances

---

#### Test 2.3: Mixed Sequential + Parallel ⚡ TIER 2
**Business Impact**: Testing workflows (parallel test execution → sequential analysis).

**Configuration**: `tests/fixtures/mixed_workflow.json`

```json
{
  "instances": [
    {
      "name": "unit-tests",
      "command": "/help",
      "description": "Stage 1: Parallel testing",
      "max_tokens_per_command": 5000
    },
    {
      "name": "integration-tests",
      "command": "/help",
      "description": "Stage 1: Parallel testing",
      "max_tokens_per_command": 8000
    },
    {
      "name": "failure-analyzer",
      "command": "/help",
      "description": "Stage 2: Sequential analysis",
      "max_tokens_per_command": 10000
    },
    {
      "name": "coverage-analyst",
      "command": "/help",
      "description": "Stage 2: Sequential analysis",
      "max_tokens_per_command": 6000
    }
  ]
}
```

**Expected Behavior**:
- Instances 1-2 (Stage 1) run in parallel
- Instances 3-4 (Stage 2) wait for Stage 1 completion
- Status report shows stage transitions clearly

**Limitation Note**: Current implementation uses `startup_delay` for staggered starts, not true dependency management. Future enhancement: explicit `depends_on` field.

---

### 3. Status Reporting ⚡ CRITICAL

**Business Impact**: If status reporting fails, **users can't monitor progress or diagnose issues**.

#### Test 3.1: Real-Time Status Updates ✓ TIER 2

**Test Setup**:
```bash
zen --config tests/fixtures/long_running_workflow.json \
    --status-report-interval 5 \
    --max-console-lines 30
```

**Verification Checklist**:
- [ ] Status updates appear every 5 seconds (±1s tolerance)
- [ ] Each update shows: name, status, PID, tokens used, elapsed time
- [ ] Progress indicators match actual instance state
- [ ] Token counts increment correctly between updates
- [ ] Console output respects `max-console-lines` limit

**Expected Console Output Format**:
```
╔═══════════════════════════════════════════════════════════════╗
║  ZEN Orchestrator - Instance Status (15s elapsed)             ║
╚═══════════════════════════════════════════════════════════════╝

Name                | Status      | PID    | Tokens  | Time   | Progress
--------------------|-------------|--------|---------|--------|----------
data-collector      | ✓ completed | 12345  | 2,450   | 8.2s   | ████████
analyzer            | ⏳ running  | 12346  | 1,823   | 5.1s   | ████░░░░
reporter            | ⏸ pending   | -      | 0       | -      | ░░░░░░░░

Overall: 4,273 / 15,000 tokens used (28.5%)
Budget: ████░░░░░░░░░░░░ $0.42 / $5.00
```

**Code Reference**: `zen_orchestrator.py:232-234` (status reporting interval)

---

#### Test 3.2: Status After Failures ⚡ TIER 1

**Configuration**: `tests/fixtures/failure_scenario.json`

```json
{
  "instances": [
    {
      "name": "successful-instance",
      "command": "/help",
      "max_tokens_per_command": 3000
    },
    {
      "name": "failing-instance",
      "command": "/this-command-does-not-exist",
      "max_tokens_per_command": 2000
    },
    {
      "name": "another-success",
      "command": "/help",
      "max_tokens_per_command": 4000
    }
  ]
}
```

**Expected Results**:
- ✓ Instance 1: status="completed", no error
- ✓ Instance 2: status="failed", error message populated
- ✓ Instance 3: status="completed" (not affected by Instance 2 failure)
- ✓ Final summary distinguishes success vs failure counts
- ✓ Exit code reflects failure (non-zero)

**Final Summary Format**:
```
╔═══════════════════════════════════════════════════════════════╗
║  Orchestration Complete - Results                             ║
╚═══════════════════════════════════════════════════════════════╝

✓ Successful: 2/3 instances
✗ Failed: 1/3 instances

Failed Instances:
- failing-instance: Command not found: /this-command-does-not-exist

Total Tokens: 7,000
Total Cost: $0.70
Total Time: 45.3s
```

**Code Reference**: `zen_orchestrator.py:842-863` (error handling in `run_all_instances`)

---

#### Test 3.3: Status with Timeout ⚡ TIER 2

**Test Command**:
```bash
# Create instance that runs longer than timeout
zen --config tests/fixtures/timeout_test.json \
    --startup-delay 2.0
```

**Config**: Instance with long-running command, timeout set to 10s

**Expected Behavior**:
- [ ] Instance runs for ~10 seconds
- [ ] Status changes to "failed" at timeout
- [ ] Error message: "Timeout after 10s"
- [ ] Process is killed (no zombie processes)
- [ ] Other instances continue unaffected

**Verification**:
```bash
# After orchestration completes, check for zombies
ps aux | grep defunct
# Should return empty (no zombie processes)
```

**Code Reference**: `zen_orchestrator.py:844-850` (timeout handling)

---

### 4. Budget Management ⚡⚡ CRITICAL

**Business Impact**: Prevents **cost overruns** in production or **blocks workflows** incorrectly.

#### Test 4.1: Overall Budget Enforcement (Block Mode) ✓ TIER 1

**Configuration**: `tests/fixtures/budget_block_test.json`

```json
{
  "budget": {
    "overall_budget": 10000,
    "enforcement_mode": "block"
  },
  "instances": [
    {
      "name": "instance-1",
      "command": "/help",
      "max_tokens_per_command": 6000
    },
    {
      "name": "instance-2",
      "command": "/help",
      "max_tokens_per_command": 6000
    },
    {
      "name": "instance-3",
      "command": "/help",
      "max_tokens_per_command": 3000
    }
  ]
}
```

**Expected Results**:
- ✓ Instance 1: Executes, uses ~6000 tokens
- ✓ Instance 2: **BLOCKED** with error "Budget exceeded"
- ✓ Instance 3: **BLOCKED** (budget already exceeded)
- ✓ Status shows instances 2-3 as "failed" with budget error
- ✓ No actual execution of instances 2-3 (pre-flight check)

**Console Output**:
```
🚫 BLOCK MODE: Budget exceeded for instance instance-2: Estimated 6000 tokens would exceed overall budget of 10000 (currently at 6000). Skipping.
🚫 BLOCK MODE: Budget exceeded for instance instance-3: Overall budget exceeded. Skipping.
```

**Code Reference**: `zen_orchestrator.py:460-498` (pre-execution budget check)

---

#### Test 4.2: Per-Command Budget Tracking ✓ TIER 2

**Configuration**: `tests/fixtures/per_command_budget.json`

```json
{
  "budget": {
    "command_budgets": {
      "/analyze-code": 10000
    }
  },
  "instances": [
    {
      "name": "analysis-1",
      "command": "/analyze-code",
      "max_tokens_per_command": 4000
    },
    {
      "name": "analysis-2",
      "command": "/analyze-code",
      "max_tokens_per_command": 4000
    },
    {
      "name": "analysis-3",
      "command": "/analyze-code",
      "max_tokens_per_command": 4000
    }
  ]
}
```

**Expected Behavior**:
- Instance 1 executes (4000 tokens used)
- Instance 2 executes (8000 total used)
- Instance 3 **BLOCKED** (would exceed 10000 command budget)

**Verification**: Aggregated tracking per command, not per instance.

**Code Reference**: `zen_orchestrator.py:2598-2622` (command budget loading)

---

#### Test 4.3: Cost Budget (USD) vs Token Budget ⚡ TIER 2

**Configuration**: `tests/fixtures/cost_budget_test.json`

```json
{
  "budget": {
    "overall_cost_budget": 5.0,
    "budget_type": "cost",
    "enforcement_mode": "block"
  },
  "instances": [
    {
      "name": "expensive-task-1",
      "command": "/help",
      "max_tokens_per_command": 20000
    },
    {
      "name": "expensive-task-2",
      "command": "/help",
      "max_tokens_per_command": 20000
    }
  ]
}
```

**Expected Results**:
- ✓ Tracks USD spend instead of tokens
- ✓ Blocks when $5.00 exceeded
- ✓ Status report shows cost: "$3.45 / $5.00"

**Cost Calculation** (using Claude Sonnet 4 pricing):
- Input tokens: $3 per 1M tokens
- Output tokens: $15 per 1M tokens
- Cache read: $0.30 per 1M tokens

**Code Reference**: `zen_orchestrator.py:595-638` (cost calculation)

---

### 5. Error Handling & Recovery ⚡⚡⚡ CRITICAL

**Business Impact**: Determines if **partial failures cascade** to kill entire workflow.

#### Test 5.1: Single Instance Failure in Multi-Agent Workflow ✓ TIER 1 - HIGHEST PRIORITY

**This is THE most critical test.** If this fails, the orchestration system is fundamentally broken.

**Configuration**: `tests/fixtures/partial_failure.json`

```json
{
  "instances": [
    {
      "name": "step-1-success",
      "command": "/help",
      "max_tokens_per_command": 2000
    },
    {
      "name": "step-2-success",
      "command": "/help",
      "max_tokens_per_command": 3000
    },
    {
      "name": "step-3-FAILURE",
      "command": "/nonexistent-slash-command",
      "max_tokens_per_command": 2000
    },
    {
      "name": "step-4-success",
      "command": "/help",
      "max_tokens_per_command": 4000
    },
    {
      "name": "step-5-success",
      "command": "/help",
      "max_tokens_per_command": 3000
    }
  ]
}
```

**Expected Results**:
- ✓ Step 1: status="completed", tokens=~2000
- ✓ Step 2: status="completed", tokens=~3000
- ✗ Step 3: status="failed", error="Command not found"
- ✓ Step 4: status="completed", tokens=~4000 **(CRITICAL - must not be blocked)**
- ✓ Step 5: status="completed", tokens=~3000 **(CRITICAL - must not be blocked)**

**Success Criteria**:
```
Final Results: 4 succeeded, 1 failed
Total Tokens: ~12,000 (excluding failed instance)
Exit Code: Non-zero (indicates partial failure)
```

**Anti-Pattern**: If step 3 failure prevents steps 4-5 from executing, **this is a catastrophic bug**.

**Code Reference**: `zen_orchestrator.py:582-587` (exception handling in `run_instance`)

---

#### Test 5.2: Workspace Permission Issues ⚡ TIER 2

**Test Scenarios**:

```bash
# Scenario A: Non-existent workspace
zen --config valid_config.json --workspace /nonexistent/path

# Scenario B: Unreadable workspace
mkdir /tmp/unreadable
chmod 000 /tmp/unreadable
zen --config valid_config.json --workspace /tmp/unreadable

# Scenario C: Workspace is a file, not directory
touch /tmp/not_a_dir
zen --config valid_config.json --workspace /tmp/not_a_dir
```

**Expected Results**:
- ✓ Early validation error (before launching instances)
- ✓ Clear error message specifying the issue
- ✓ Exit code: 1
- ✓ No hanging processes or partial executions

**Code Reference**: `zen_orchestrator.py:2479-2493` (workspace validation)

---

#### Test 5.3: Claude CLI Not Found ⚡ TIER 2

**Test Setup**:
```bash
# Temporarily hide claude binary from PATH
export PATH="/usr/bin:/bin"  # Minimal PATH
zen --config valid_config.json
```

**Expected Results**:
- ✓ Error message: "Claude CLI not found in PATH"
- ✓ Clear installation instructions
- ✓ Exit code: 1
- ✓ No hanging processes

**Alternative Test**: Use `which claude` to verify before orchestration starts.

---

### 6. Advanced Configuration Features 🟡 MEDIUM PRIORITY

#### Test 6.1: Session Management Across Instances ✓ TIER 3

**Configuration**: `tests/fixtures/session_sharing.json`

```json
{
  "instances": [
    {
      "name": "context-setter",
      "command": "/help",
      "session_id": "shared-session",
      "max_tokens_per_command": 2000
    },
    {
      "name": "context-user",
      "command": "/help",
      "session_id": "shared-session",
      "max_tokens_per_command": 3000
    }
  ]
}
```

**Expected Behavior**: Instances share session context.

**Verification**: Check if second instance can reference first instance's context.

**Code Reference**: `zen_orchestrator.py:116-128` (InstanceConfig with session_id)

---

#### Test 6.2: Pre-Commands Execution ✓ TIER 3

**Configuration**:
```json
{
  "instances": [
    {
      "name": "analyzer",
      "command": "/analyze-code",
      "pre_commands": [
        "/clear",
        "Set context: I am analyzing a Python codebase for security issues"
      ],
      "max_tokens_per_command": 5000
    }
  ]
}
```

**Expected Behavior**: Pre-commands execute before main command.

**Verification**: Check command execution order in logs.

**Code Reference**: `zen_orchestrator.py:126` (pre_commands field)

---

#### Test 6.3: Tool Restrictions ✓ TIER 3

**Configuration**:
```json
{
  "instances": [
    {
      "name": "restricted-agent",
      "command": "/help",
      "allowed_tools": ["Read", "Grep"],
      "max_tokens_per_command": 3000
    }
  ]
}
```

**Expected Behavior**: Instance respects tool restrictions.

**Verification**: Attempt to use disallowed tool (e.g., Write), verify rejection.

**Code Reference**: `zen_orchestrator.py:120` (allowed_tools field)

---

## Priority Test Execution Order

### Phase 1: Foundation (Must Pass - Block Release)
**Run these first - if any fail, stop and fix immediately.**

1. ✅ Test 1.1: Valid Complex Configuration
2. ✅ Test 2.1: Sequential Dependency Chain
3. ✅ Test 5.1: Single Instance Failure Isolation
4. ✅ Test 3.2: Status After Failures

**Estimated Time**: 15 minutes
**Success Criteria**: 100% pass rate required

---

### Phase 2: Critical Features (High Priority)
**Run after Phase 1 passes.**

5. ✅ Test 4.1: Budget Enforcement (Block Mode)
6. ✅ Test 2.2: Parallel Independent Instances
7. ✅ Test 1.3: Missing Required Fields
8. ✅ Test 3.1: Real-Time Status Updates

**Estimated Time**: 20 minutes
**Success Criteria**: 100% pass rate required

---

### Phase 3: Robustness (Medium Priority)
**Run before release candidate.**

9. ✅ Test 1.2: Malformed JSON
10. ✅ Test 4.2: Per-Command Budget Tracking
11. ✅ Test 5.2: Workspace Permission Issues
12. ✅ Test 3.3: Status with Timeout

**Estimated Time**: 15 minutes
**Success Criteria**: 90%+ pass rate acceptable

---

### Phase 4: Advanced Features (Nice to Have)
**Run for comprehensive coverage.**

13. ✅ Test 2.3: Mixed Sequential + Parallel
14. ✅ Test 4.3: Cost Budget vs Token Budget
15. ✅ Test 6.1: Session Management
16. ✅ Test 6.2: Pre-Commands Execution

**Estimated Time**: 20 minutes
**Success Criteria**: 80%+ pass rate acceptable

---

## Implementation Guide

### Quick Start: Create Test File

```python
#!/usr/bin/env python3
"""
tests/test_config_orchestration.py

Critical integration tests for config-based orchestration.
Run with: python -m pytest tests/test_config_orchestration.py -v
"""

import unittest
import tempfile
import json
from pathlib import Path
import subprocess
import sys

class TestConfigOrchestrationCritical(unittest.TestCase):
    """Phase 1: Foundation tests - must pass before release"""

    def setUp(self):
        self.zen_dir = Path(__file__).parent.parent
        self.zen_script = self.zen_dir / "zen_orchestrator.py"
        self.fixtures_dir = self.zen_dir / "tests" / "fixtures"
        self.fixtures_dir.mkdir(exist_ok=True)

    def run_zen(self, config_file, extra_args=None):
        """Helper to run zen with config file"""
        cmd = [sys.executable, str(self.zen_script), "--config", str(config_file)]
        if extra_args:
            cmd.extend(extra_args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result

    def test_sequential_dependency_chain(self):
        """TIER 1: Sequential workflows must execute in order"""
        config = {
            "instances": [
                {"name": "step-1", "command": "/help", "max_tokens_per_command": 1000},
                {"name": "step-2", "command": "/help", "max_tokens_per_command": 2000},
                {"name": "step-3", "command": "/help", "max_tokens_per_command": 3000}
            ]
        }

        config_file = self.fixtures_dir / "sequential_test.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)

        result = self.run_zen(config_file, ["--startup-delay", "2.0"])

        # Verify all instances completed
        self.assertEqual(result.returncode, 0, "All instances should succeed")
        self.assertIn("step-1", result.stdout)
        self.assertIn("step-2", result.stdout)
        self.assertIn("step-3", result.stdout)

    def test_single_instance_failure_isolation(self):
        """TIER 1: One bad agent shouldn't kill entire workflow"""
        config = {
            "instances": [
                {"name": "good-1", "command": "/help"},
                {"name": "bad", "command": "/nonexistent"},
                {"name": "good-2", "command": "/help"}
            ]
        }

        config_file = self.fixtures_dir / "partial_failure_test.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)

        result = self.run_zen(config_file)

        # Should show partial success
        self.assertNotEqual(result.returncode, 0, "Should exit with error code")

        output = result.stdout + result.stderr
        # Verify good instances completed
        self.assertIn("good-1", output)
        self.assertIn("good-2", output)
        # Verify bad instance failed
        self.assertIn("bad", output)
        self.assertIn("failed", output.lower())

if __name__ == '__main__':
    unittest.main(verbosity=2)
```

---

## Test Fixtures Directory Structure

```
tests/fixtures/
├── valid_complex_config.json          # Test 1.1
├── malformed_json/
│   ├── missing_comma.json             # Test 1.2A
│   ├── unclosed_bracket.json          # Test 1.2B
│   └── invalid_quotes.json            # Test 1.2C
├── missing_fields/
│   ├── no_instances.json              # Test 1.3A
│   ├── no_command_or_prompt.json      # Test 1.3B
│   └── empty_commands.json            # Test 1.3C
├── sequential_workflow.json           # Test 2.1
├── parallel_workflow.json             # Test 2.2
├── mixed_workflow.json                # Test 2.3
├── failure_scenario.json              # Test 3.2
├── budget_block_test.json             # Test 4.1
├── per_command_budget.json            # Test 4.2
├── cost_budget_test.json              # Test 4.3
├── partial_failure.json               # Test 5.1
└── session_sharing.json               # Test 6.1
```

---

## Monitoring & Alerting

### Production Health Checks

**SLA Targets**:
- Config load time: < 100ms for files < 1MB
- Instance startup: < 5s per instance
- Status update frequency: Every 5-10s
- Failure isolation: 100% (one failure never blocks others)

### Alert Triggers

```yaml
alerts:
  - name: config_parsing_failure_rate
    condition: error_rate > 1%
    severity: critical

  - name: orchestration_timeout
    condition: instance_runtime > 300s
    severity: warning

  - name: budget_enforcement_failure
    condition: actual_tokens > budget * 1.1
    severity: critical

  - name: status_reporting_gap
    condition: time_since_last_update > 30s
    severity: warning
```

---

## Coverage Analysis

### Current Test Coverage Gaps

Based on code analysis of `zen_orchestrator.py`, these critical paths are **currently untested**:

| Line Range | Function | Business Impact | Test Coverage |
|-----------|----------|-----------------|---------------|
| 2514-2525 | Config budget loading | HIGH | ❌ No tests |
| 797-863 | `run_all_instances()` timeout | HIGH | ❌ No tests |
| 451-587 | Instance execution with budget checks | CRITICAL | ❌ No tests |
| 2656-2683 | Auto-budget from `max_tokens_per_command` | MEDIUM | ❌ No tests |
| 840-850 | Timeout handling & cleanup | HIGH | ❌ No tests |

**Recommendation**: Prioritize tests for lines 451-587 and 797-863 (core orchestration).

---

## Success Metrics

### Definition of Done

This test plan is complete when:

- ✅ All Phase 1 tests pass (100% required)
- ✅ All Phase 2 tests pass (100% required)
- ✅ 90%+ of Phase 3 tests pass
- ✅ Test execution time < 70 minutes (total)
- ✅ Code coverage > 80% for orchestration functions
- ✅ Zero flaky tests (consistent results across 10 runs)

### Release Criteria

**Block release if**:
- Any Tier 1 test fails
- Test 5.1 (failure isolation) fails
- Test 2.1 (sequential chain) fails
- Budget enforcement tests (4.1) fail

**Can release with warnings if**:
- Phase 4 tests have < 80% pass rate (log as tech debt)
- Performance targets missed by < 20%

---

## Appendix: Real-World Failure Scenarios

### Scenario 1: Production Data Pipeline Failure
**Date**: 2024-12-15 (hypothetical)
**Impact**: 4-hour outage for data analysis workflows
**Root Cause**: Bug in line 858 - exception in one instance killed entire orchestration
**Lesson**: Need comprehensive tests for Test 5.1 (failure isolation)

### Scenario 2: Budget Overrun
**Date**: 2025-01-20 (hypothetical)
**Impact**: $500 unexpected API costs
**Root Cause**: Budget enforcement not applied in config file mode
**Lesson**: Need tests for Test 4.1 (budget enforcement)

---

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-10 | Initial test plan created | Zen Team |

---

## References

- **Source Code**: `zen_orchestrator.py:211-2700`
- **Example Configs**: `examples/data_analysis.json`, `examples/testing_workflow.json`
- **Existing Tests**: `tests/test_cli_integration.py`
- **Budget Feature Tests**: `docs/TEST_PLAN_BUDGET_FEATURES.md`
