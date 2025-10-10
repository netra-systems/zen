# Test Plan 3: CLI Argument Precedence Testing
**File Under Test:** `zen_orchestrator.py`
**Function Under Test:** `main()` argument parsing and precedence logic
**Lines:** 2381-2537
**Date:** 2025-10-10

## Executive Summary
The `zen_orchestrator.py` CLI argument parsing implements a **complex three-tier precedence system**:
1. **Direct command** (highest) - `zen "/command"`
2. **Config file** (medium) - `zen --config file.json`
3. **Default instances** (lowest) - `zen`

This precedence system is **brittle and bug-prone** due to:
- Multiple argument combinations (50+ possible combinations)
- Cross-cutting concerns (budget settings, workspace detection)
- CLI argument overrides of config file settings
- Conditional logic based on argument presence

## Why This Is Complex and Brittle

### Complexity Factors
1. **Three execution modes** with different behaviors
2. **20+ command-line arguments** with interdependencies
3. **Budget configuration** can come from CLI OR config file
4. **Workspace detection** varies by mode
5. **Session management** arguments only apply to direct commands
6. **Output format** applies to all modes but has different defaults

### Historical Bug Patterns
- Arguments ignored in certain modes
- Precedence rules violated
- Defaults not applied correctly
- Config file settings unexpectedly overridden
- Validation skipped in some paths

### Risk Assessment
- **High Risk:** Mode selection logic (direct command vs config vs default)
- **Medium Risk:** Budget configuration merging
- **Medium Risk:** Workspace detection and inheritance
- **Low Risk:** Output format and logging

## Precedence Rules (Lines 38-42)

```
Priority Hierarchy:
1. Direct command - zen "/command" [HIGHEST]
   └─ Loads budget from config file if --config provided
2. Config file - zen --config file.json [MEDIUM]
   └─ All instance configs and budget from file
3. Default instances - zen [LOWEST]
   └─ Hardcoded default instances

Budget Settings Precedence:
1. CLI arguments (--overall-token-budget, --command-budget) [HIGHEST]
2. Config file budget section [LOWER]

Workspace Precedence:
1. --workspace CLI argument [HIGHEST]
2. Config file workspace [IF in config mode]
3. Auto-detection from project root [LOWEST]
```

## Test Categories

### 1. Mode Selection Tests

#### 1.1 Direct Command Mode Tests
```python
def test_direct_command_mode_basic():
    """Test basic direct command execution"""
    args = ["zen", "/analyze-code"]
    result = parse_and_execute(args)

    assert result.mode == "direct_command"
    assert result.instances[0].command == "/analyze-code"
    assert len(result.instances) == 1

def test_direct_command_mode_with_prompt():
    """Test direct command with raw prompt"""
    args = ["zen", "What are the available commands?"]
    result = parse_and_execute(args)

    assert result.mode == "direct_command"
    assert result.instances[0].command == "What are the available commands?"

def test_direct_command_mode_with_workspace():
    """Test direct command with workspace override"""
    args = ["zen", "/analyze-code", "--workspace", "/custom/path"]
    result = parse_and_execute(args)

    assert result.mode == "direct_command"
    assert result.workspace == Path("/custom/path")

def test_direct_command_mode_with_instance_name():
    """Test direct command with custom instance name"""
    args = ["zen", "/analyze-code", "--instance-name", "my-analyzer"]
    result = parse_and_execute(args)

    assert result.instances[0].name == "my-analyzer"

def test_direct_command_mode_with_session_options():
    """Test direct command with session options"""
    args = [
        "zen", "/debug-issue",
        "--session-id", "debug-123",
        "--clear-history",
        "--compact-history"
    ]
    result = parse_and_execute(args)

    instance = result.instances[0]
    assert instance.session_id == "debug-123"
    assert instance.clear_history is True
    assert instance.compact_history is True

def test_direct_command_mode_loads_budget_from_config():
    """Test that direct command mode loads budget from config file if provided"""
    config_file = create_temp_config({
        "instances": [],
        "budget": {
            "overall_token_budget": 50000,
            "enforcement_mode": "block"
        }
    })

    args = ["zen", "/analyze-code", "--config", str(config_file)]
    result = parse_and_execute(args)

    # Direct command should execute
    assert result.mode == "direct_command"
    assert len(result.instances) == 1

    # Budget from config should be loaded
    assert result.budget_settings.overall_token_budget == 50000
    assert result.budget_settings.enforcement_mode == "block"
```

#### 1.2 Config File Mode Tests
```python
def test_config_file_mode_basic():
    """Test basic config file execution"""
    config_file = create_temp_config({
        "instances": [
            {"command": "/analyze-code", "name": "analyzer"},
            {"command": "/debug-issue", "name": "debugger"}
        ]
    })

    args = ["zen", "--config", str(config_file)]
    result = parse_and_execute(args)

    assert result.mode == "config_file"
    assert len(result.instances) == 2
    assert result.instances[0].command == "/analyze-code"
    assert result.instances[1].command == "/debug-issue"

def test_config_file_mode_with_budget():
    """Test config file with budget configuration"""
    config_file = create_temp_config({
        "instances": [{"command": "/test"}],
        "budget": {
            "overall_token_budget": 100000,
            "command_budgets": {"/test": 50000},
            "enforcement_mode": "warn"
        }
    })

    args = ["zen", "--config", str(config_file)]
    result = parse_and_execute(args)

    assert result.budget_settings.overall_token_budget == 100000
    assert result.budget_settings.enforcement_mode == "warn"

def test_config_file_mode_with_workspace_override():
    """Test config file with CLI workspace override"""
    config_file = create_temp_config({
        "instances": [{"command": "/test"}]
    })

    args = ["zen", "--config", str(config_file), "--workspace", "/custom"]
    result = parse_and_execute(args)

    assert result.workspace == Path("/custom")

def test_config_file_nonexistent():
    """Test handling of nonexistent config file"""
    args = ["zen", "--config", "/nonexistent/config.json"]

    with pytest.raises(FileNotFoundError):
        parse_and_execute(args)

def test_config_file_malformed_json():
    """Test handling of malformed JSON config"""
    config_file = create_temp_file("{invalid json}")

    args = ["zen", "--config", str(config_file)]

    with pytest.raises(json.JSONDecodeError):
        parse_and_execute(args)

def test_config_file_missing_instances_key():
    """Test config file without required 'instances' key"""
    config_file = create_temp_config({
        "budget": {"overall_token_budget": 10000}
    })

    args = ["zen", "--config", str(config_file)]

    with pytest.raises(KeyError, match="instances"):
        parse_and_execute(args)

def test_config_file_empty_instances():
    """Test config file with empty instances array"""
    config_file = create_temp_config({
        "instances": []
    })

    args = ["zen", "--config", str(config_file)]
    result = parse_and_execute(args)

    assert len(result.instances) == 0
```

#### 1.3 Default Instances Mode Tests
```python
def test_default_instances_mode():
    """Test default instances mode (no command, no config)"""
    args = ["zen"]
    result = parse_and_execute(args)

    assert result.mode == "default_instances"
    assert len(result.instances) > 0  # Should have default instances

def test_default_instances_with_workspace():
    """Test default instances with workspace override"""
    args = ["zen", "--workspace", "/custom"]
    result = parse_and_execute(args)

    assert result.mode == "default_instances"
    assert result.workspace == Path("/custom")

def test_default_instances_with_dry_run():
    """Test default instances in dry-run mode"""
    args = ["zen", "--dry-run"]
    result = parse_and_execute(args)

    assert result.mode == "default_instances"
    assert result.dry_run is True

def test_default_instances_with_output_format():
    """Test default instances with custom output format"""
    args = ["zen", "--output-format", "json"]
    result = parse_and_execute(args)

    # All instances should use specified format
    assert all(inst.output_format == "json" for inst in result.instances)
```

### 2. Precedence Violation Tests

#### 2.1 Direct Command Takes Precedence Over Config
```python
def test_direct_command_overrides_config_instances():
    """Test that direct command ignores config instances"""
    config_file = create_temp_config({
        "instances": [
            {"command": "/config-command", "name": "from-config"}
        ]
    })

    # Direct command should win
    args = ["zen", "/direct-command", "--config", str(config_file)]
    result = parse_and_execute(args)

    assert result.mode == "direct_command"
    assert len(result.instances) == 1
    assert result.instances[0].command == "/direct-command"
    # Config instances should be ignored

def test_direct_command_with_empty_string():
    """Test that empty string is not treated as direct command"""
    args = ["zen", "", "--config", "config.json"]
    result = parse_and_execute(args)

    # Should fall back to config mode
    assert result.mode == "config_file"

def test_direct_command_with_whitespace_only():
    """Test that whitespace-only string is not treated as direct command"""
    args = ["zen", "   ", "--config", "config.json"]
    result = parse_and_execute(args)

    # Should fall back to config mode (or reject)
```

#### 2.2 CLI Arguments Override Config File
```python
def test_cli_budget_overrides_config_budget():
    """Test that CLI budget args override config file"""
    config_file = create_temp_config({
        "instances": [{"command": "/test"}],
        "budget": {
            "overall_token_budget": 50000,
            "enforcement_mode": "warn"
        }
    })

    args = [
        "zen", "--config", str(config_file),
        "--overall-token-budget", "100000",
        "--budget-enforcement-mode", "block"
    ]
    result = parse_and_execute(args)

    # CLI args should win
    assert result.budget_settings.overall_token_budget == 100000
    assert result.budget_settings.enforcement_mode == "block"

def test_cli_partial_budget_override():
    """Test partial budget override (some CLI, some config)"""
    config_file = create_temp_config({
        "instances": [{"command": "/test"}],
        "budget": {
            "overall_token_budget": 50000,
            "enforcement_mode": "warn"
        }
    })

    # Only override token budget, not enforcement mode
    args = [
        "zen", "--config", str(config_file),
        "--overall-token-budget", "100000"
    ]
    result = parse_and_execute(args)

    # CLI overrides token budget
    assert result.budget_settings.overall_token_budget == 100000
    # Config enforcement mode retained
    assert result.budget_settings.enforcement_mode == "warn"

def test_cli_workspace_overrides_config_workspace():
    """Test that CLI workspace overrides config file workspace"""
    config_file = create_temp_config({
        "instances": [{"command": "/test"}],
        "workspace": "/config/workspace"
    })

    args = ["zen", "--config", str(config_file), "--workspace", "/cli/workspace"]
    result = parse_and_execute(args)

    assert result.workspace == Path("/cli/workspace")
```

#### 2.3 Config File Takes Precedence Over Defaults
```python
def test_config_overrides_default_instances():
    """Test that config file overrides default instances"""
    config_file = create_temp_config({
        "instances": [{"command": "/custom-command"}]
    })

    args = ["zen", "--config", str(config_file)]
    result = parse_and_execute(args)

    assert result.mode == "config_file"
    assert len(result.instances) == 1
    assert result.instances[0].command == "/custom-command"
    # Should NOT contain default instances

def test_config_output_format_overrides_cli_default():
    """Test that config instances have their own output format"""
    config_file = create_temp_config({
        "instances": [
            {"command": "/test", "output_format": "json"}
        ]
    })

    args = ["zen", "--config", str(config_file)]
    result = parse_and_execute(args)

    # Instance-specific format should win
    assert result.instances[0].output_format == "json"
```

### 3. Argument Combination Tests

#### 3.1 Direct Command + Session Options
```python
@pytest.mark.parametrize("session_options", [
    ({"--session-id": "test-123"}),
    ({"--clear-history": True}),
    ({"--compact-history": True}),
    ({"--session-id": "test", "--clear-history": True}),
    ({"--session-id": "test", "--compact-history": True}),
    ({"--clear-history": True, "--compact-history": True}),
    ({"--session-id": "test", "--clear-history": True, "--compact-history": True}),
])
def test_direct_command_session_combinations(session_options):
    """Test all combinations of session-related options"""
    args = ["zen", "/test-command"]

    for key, value in session_options.items():
        if isinstance(value, bool) and value:
            args.append(key)
        else:
            args.extend([key, str(value)])

    result = parse_and_execute(args)

    instance = result.instances[0]
    if "--session-id" in session_options:
        assert instance.session_id == session_options["--session-id"]
    if "--clear-history" in session_options:
        assert instance.clear_history is True
    if "--compact-history" in session_options:
        assert instance.compact_history is True
```

#### 3.2 Budget Argument Combinations
```python
@pytest.mark.parametrize("budget_args", [
    # Token-based budgets
    ({"--overall-token-budget": 100000}),
    ({"--command-budget": ["/cmd1=5000", "/cmd2=10000"]}),
    ({"--overall-token-budget": 100000, "--command-budget": ["/cmd=5000"]}),

    # Cost-based budgets
    ({"--overall-cost-budget": 10.50}),
    ({"--command-cost-budget": ["/cmd1=2.50", "/cmd2=5.00"]}),
    ({"--overall-cost-budget": 10.0, "--command-cost-budget": ["/cmd=2.0"]}),

    # Mixed budgets
    ({
        "--overall-token-budget": 100000,
        "--overall-cost-budget": 10.0,
        "--budget-parameter-type": "mixed"
    }),

    # Enforcement modes
    ({"--overall-token-budget": 100000, "--budget-enforcement-mode": "warn"}),
    ({"--overall-token-budget": 100000, "--budget-enforcement-mode": "block"}),

    # Visual preferences
    ({"--overall-token-budget": 100000, "--disable-budget-visuals": True}),
])
def test_budget_argument_combinations(budget_args):
    """Test all valid combinations of budget arguments"""
    args = ["zen", "/test-command"]

    for key, value in budget_args.items():
        if isinstance(value, bool) and value:
            args.append(key)
        elif isinstance(value, list):
            for item in value:
                args.extend([key, item])
        else:
            args.extend([key, str(value)])

    result = parse_and_execute(args)

    # Verify budget settings applied
    if "--overall-token-budget" in budget_args:
        assert result.budget_settings.overall_token_budget == budget_args["--overall-token-budget"]
    if "--overall-cost-budget" in budget_args:
        assert result.budget_settings.overall_cost_budget == budget_args["--overall-cost-budget"]
```

#### 3.3 Output and Logging Combinations
```python
@pytest.mark.parametrize("output_args", [
    ({"--output-format": "json"}),
    ({"--output-format": "stream-json"}),
    ({"--quiet": True}),
    ({"--verbose": True}),
    ({"--log-level": "silent"}),
    ({"--log-level": "concise"}),
    ({"--log-level": "detailed"}),
    ({"--output-format": "json", "--quiet": True}),
    ({"--output-format": "stream-json", "--verbose": True}),
])
def test_output_logging_combinations(output_args):
    """Test combinations of output format and logging options"""
    args = ["zen", "/test"]

    for key, value in output_args.items():
        if isinstance(value, bool) and value:
            args.append(key)
        else:
            args.extend([key, str(value)])

    result = parse_and_execute(args)

    if "--output-format" in output_args:
        assert result.instances[0].output_format == output_args["--output-format"]
    if "--quiet" in output_args:
        assert result.log_level == LogLevel.SILENT
    elif "--verbose" in output_args:
        assert result.log_level == LogLevel.DETAILED
    elif "--log-level" in output_args:
        expected_level = LogLevel[output_args["--log-level"].upper()]
        assert result.log_level == expected_level
```

#### 3.4 Scheduling Options
```python
@pytest.mark.parametrize("schedule_arg", [
    "2h",      # 2 hours from now
    "30m",     # 30 minutes from now
    "1am",     # 1 AM today or tomorrow
    "14:30",   # 2:30 PM today or tomorrow
    "10:30pm", # 10:30 PM today or tomorrow
])
def test_scheduling_argument_formats(schedule_arg):
    """Test various scheduling time formats"""
    args = ["zen", "/test", "--start-at", schedule_arg]
    result = parse_and_execute(args)

    assert result.scheduled_start is not None
    # Verify scheduled time is in the future
    assert result.scheduled_start > datetime.now()
```

### 4. Validation Tests

#### 4.1 Mutually Exclusive Arguments
```python
def test_quiet_and_verbose_mutually_exclusive():
    """Test that --quiet and --verbose cannot both be specified"""
    args = ["zen", "/test", "--quiet", "--verbose"]

    with pytest.raises(argparse.ArgumentError):
        parse_and_execute(args)

def test_log_level_and_quiet_conflict():
    """Test that --log-level and --quiet are mutually exclusive"""
    args = ["zen", "/test", "--log-level", "detailed", "--quiet"]

    # Either should raise error or last one wins
    result = parse_and_execute(args)
    # Implementation-dependent behavior

def test_direct_command_and_list_commands():
    """Test that direct command with --list-commands should prefer listing"""
    args = ["zen", "/test", "--list-commands"]
    result = parse_and_execute(args)

    # Should list commands, not execute
    assert result.action == "list_commands"
```

#### 4.2 Required Argument Combinations
```python
def test_command_budget_without_overall_budget():
    """Test --command-budget without --overall-token-budget"""
    args = ["zen", "/test", "--command-budget", "/test=5000"]
    result = parse_and_execute(args)

    # Should be allowed (command budget can exist independently)

def test_command_cost_budget_requires_cost_budget_type():
    """Test that --command-cost-budget requires correct budget type"""
    args = [
        "zen", "/test",
        "--command-cost-budget", "/test=2.0",
        "--budget-parameter-type", "tokens"  # Wrong type
    ]

    # May warn or reject depending on implementation
    result = parse_and_execute(args)
```

#### 4.3 Invalid Argument Values
```python
def test_invalid_timeout_value():
    """Test invalid timeout value"""
    args = ["zen", "/test", "--timeout", "-100"]

    with pytest.raises(ValueError):
        parse_and_execute(args)

def test_invalid_startup_delay():
    """Test invalid startup delay"""
    args = ["zen", "/test", "--startup-delay", "-1.0"]

    with pytest.raises(ValueError):
        parse_and_execute(args)

def test_invalid_output_format():
    """Test invalid output format"""
    args = ["zen", "/test", "--output-format", "invalid"]

    with pytest.raises(argparse.ArgumentTypeError):
        parse_and_execute(args)

def test_invalid_budget_enforcement_mode():
    """Test invalid budget enforcement mode"""
    args = ["zen", "/test", "--budget-enforcement-mode", "invalid"]

    with pytest.raises(argparse.ArgumentTypeError):
        parse_and_execute(args)

def test_invalid_schedule_format():
    """Test invalid --start-at format"""
    args = ["zen", "/test", "--start-at", "invalid"]

    with pytest.raises(ValueError):
        parse_and_execute(args)
```

### 5. Edge Cases

#### 5.1 Empty and Whitespace Arguments
```python
def test_empty_command_string():
    """Test empty string as command"""
    args = ["zen", ""]

    # Should reject or fall back to default mode
    result = parse_and_execute(args)
    assert result.mode != "direct_command"

def test_whitespace_only_command():
    """Test whitespace-only command"""
    args = ["zen", "   \t\n   "]

    # Should reject or normalize
    result = parse_and_execute(args)

def test_empty_instance_name():
    """Test empty instance name"""
    args = ["zen", "/test", "--instance-name", ""]

    # Should use default name
    result = parse_and_execute(args)
    assert result.instances[0].name != ""

def test_empty_session_id():
    """Test empty session ID"""
    args = ["zen", "/test", "--session-id", ""]

    # Should accept (empty session ID may be valid)
    result = parse_and_execute(args)
```

#### 5.2 Special Characters in Arguments
```python
def test_command_with_special_characters():
    """Test command with special characters"""
    args = ["zen", "/test-command_123"]
    result = parse_and_execute(args)

    assert result.instances[0].command == "/test-command_123"

def test_prompt_with_quotes():
    """Test prompt with quotes"""
    args = ["zen", 'What is "hello world"?']
    result = parse_and_execute(args)

    assert '"hello world"' in result.instances[0].command

def test_path_with_spaces():
    """Test workspace path with spaces"""
    args = ["zen", "/test", "--workspace", "/path with spaces/project"]
    result = parse_and_execute(args)

    assert result.workspace == Path("/path with spaces/project")

def test_unicode_in_command():
    """Test Unicode characters in command"""
    args = ["zen", "测试命令 with émojis 🎉"]
    result = parse_and_execute(args)

    assert "测试命令" in result.instances[0].command
```

#### 5.3 Very Long Arguments
```python
def test_very_long_command():
    """Test command with very long text"""
    long_command = "Analyze " + "x" * 10000
    args = ["zen", long_command]

    result = parse_and_execute(args)
    assert result.instances[0].command == long_command

def test_very_long_config_path():
    """Test very long config file path"""
    long_path = "/" + "/".join(["dir"] * 100) + "/config.json"
    args = ["zen", "--config", long_path]

    # Should handle gracefully (likely FileNotFoundError)
    with pytest.raises(FileNotFoundError):
        parse_and_execute(args)

def test_many_command_budgets():
    """Test many --command-budget arguments"""
    args = ["zen", "/test"]
    for i in range(100):
        args.extend(["--command-budget", f"/cmd{i}={i * 1000}"])

    result = parse_and_execute(args)
    # Should handle all budgets
```

### 6. Integration Tests

#### 6.1 Real-World Workflows
```python
def test_workflow_simple_direct_command():
    """Test typical simple direct command usage"""
    args = ["zen", "/analyze-code"]
    result = parse_and_execute(args)

    assert result.mode == "direct_command"
    assert len(result.instances) == 1

def test_workflow_direct_command_with_budget():
    """Test direct command with budget control"""
    args = [
        "zen", "/expensive-operation",
        "--overall-token-budget", "50000",
        "--budget-enforcement-mode", "block"
    ]
    result = parse_and_execute(args)

    assert result.mode == "direct_command"
    assert result.budget_settings.overall_token_budget == 50000

def test_workflow_config_with_multiple_instances():
    """Test config file with multiple instances"""
    config_file = create_temp_config({
        "instances": [
            {"command": "/analyze", "name": "analyzer"},
            {"command": "/test", "name": "tester"},
            {"command": "/deploy", "name": "deployer"}
        ],
        "budget": {"overall_token_budget": 200000}
    })

    args = ["zen", "--config", str(config_file)]
    result = parse_and_execute(args)

    assert len(result.instances) == 3

def test_workflow_scheduled_execution():
    """Test scheduled execution workflow"""
    args = ["zen", "/nightly-analysis", "--start-at", "1am"]
    result = parse_and_execute(args)

    assert result.scheduled_start is not None
    # Should not execute immediately
```

#### 6.2 Error Recovery
```python
def test_config_file_error_recovery():
    """Test graceful handling of config file errors"""
    # Nonexistent file
    args1 = ["zen", "--config", "/nonexistent.json"]
    with pytest.raises(FileNotFoundError):
        parse_and_execute(args1)

    # Malformed JSON
    bad_config = create_temp_file("{bad json")
    args2 = ["zen", "--config", str(bad_config)]
    with pytest.raises(json.JSONDecodeError):
        parse_and_execute(args2)

def test_argument_parsing_error_recovery():
    """Test handling of argument parsing errors"""
    # Unknown argument
    args = ["zen", "/test", "--unknown-arg"]
    with pytest.raises(SystemExit):
        parse_and_execute(args)
```

## Comprehensive Test Matrix

### Mode × Arguments Matrix
```
Test all combinations of:
- Modes: [direct_command, config_file, default_instances]
- Arguments:
  - workspace: [None, custom]
  - budget: [None, token, cost, mixed]
  - session: [None, with_id, with_options]
  - output: [json, stream-json]
  - logging: [silent, concise, detailed]
  - scheduling: [None, relative, absolute]
  - dry_run: [True, False]

Total combinations: 3 × 2 × 4 × 3 × 2 × 3 × 3 × 2 = 864 tests

Strategy: Use pytest.mark.parametrize to generate all combinations
```

## Test Implementation Strategy

### Test Organization
```
tests/
├── test_zen_orchestrator_modes.py           # Mode selection
├── test_zen_orchestrator_precedence.py      # Precedence rules
├── test_zen_orchestrator_arguments.py       # Individual arguments
├── test_zen_orchestrator_combinations.py    # Argument combinations
├── test_zen_orchestrator_validation.py      # Validation and errors
└── test_zen_orchestrator_integration.py     # End-to-end workflows
```

### Fixtures
```python
@pytest.fixture
def temp_config():
    """Create temporary config file"""
    def _create(config_dict):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_dict, f)
            return Path(f.name)
    return _create

@pytest.fixture
def mock_workspace(tmp_path):
    """Create mock workspace directory"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".claude").mkdir()
    return workspace
```

### Test Helpers
```python
def parse_and_execute(args: List[str]) -> ExecutionResult:
    """Helper to parse arguments and execute orchestrator"""
    with patch('sys.argv', args):
        return asyncio.run(main())

def assert_precedence(
    mode: str,
    instances: List[InstanceConfig],
    budget: Optional[Dict],
    workspace: Optional[Path]
):
    """Assert that precedence rules are correctly applied"""
    # Validation logic
```

## Success Criteria

### Functional Requirements
- ✅ All three modes work correctly
- ✅ Precedence rules enforced in all scenarios
- ✅ CLI arguments override config file settings
- ✅ All argument combinations handled gracefully
- ✅ Validation catches invalid inputs

### Coverage Requirements
- ✅ Line coverage: >95% for argument parsing logic
- ✅ Branch coverage: >90% for all conditional paths
- ✅ All precedence rules tested
- ✅ All argument combinations tested

### Quality Requirements
- ✅ No crashes on invalid input
- ✅ Clear error messages for user errors
- ✅ Backward compatibility maintained
- ✅ Performance: Argument parsing <100ms

## Risk Assessment

### High-Risk Areas
1. **Mode selection logic** (lines 2498-2529)
   - Direct command detection
   - Config file vs default fallback
   - Mitigation: Test all mode combinations

2. **Budget configuration merging** (lines 2531-2537)
   - CLI vs config file precedence
   - Partial overrides
   - Mitigation: Test all budget combinations

3. **Workspace detection** (lines 2486-2495)
   - Auto-detection vs CLI override
   - Invalid paths
   - Mitigation: Test all workspace scenarios

### Medium-Risk Areas
1. Session option application (only for direct commands)
2. Output format inheritance
3. Logging level precedence

### Low-Risk Areas
1. Dry-run flag
2. Status report interval
3. Max console lines

## Recommended Implementation Steps

1. **Phase 1:** Mode selection tests (HIGH PRIORITY)
2. **Phase 2:** Precedence rule tests (HIGH PRIORITY)
3. **Phase 3:** Argument validation tests (MEDIUM PRIORITY)
4. **Phase 4:** Combination tests (MEDIUM PRIORITY)
5. **Phase 5:** Integration tests (LOW PRIORITY)

## Conclusion

The CLI argument precedence system in `zen_orchestrator.py` is **complex and brittle** with **50+ possible argument combinations** and **three distinct execution modes**. Comprehensive testing of all precedence rules and argument combinations is **essential** to prevent regression bugs. The test matrix approach with parameterized tests provides systematic coverage of this complex logic.
