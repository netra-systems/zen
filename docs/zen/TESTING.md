# Claude Instance Orchestrator Tests

> **🏠 [← Service Index](../INDEX.md)** | **📖 [Main Docs](../../docs/index.md)** | **🧪 [Test Runner](../tests/test_runner.py)**

This directory contains comprehensive unit and integration tests for the Netra Orchestrator Client service.

## Test Structure

### Unit Tests

#### `test_claude_instance_orchestrator_unit.py`
Tests the core dataclasses and basic functionality:
- `InstanceConfig` dataclass creation and defaults
- `InstanceStatus` dataclass functionality
- `ClaudeInstanceOrchestrator` initialization
- Start time parsing functions
- Default instance creation

#### `test_claude_instance_orchestrator_commands.py`
Tests command discovery and validation:
- Command discovery from `.claude/commands/` directory
- Command validation (existing vs non-existing commands)
- YAML frontmatter parsing in command files
- Command inspection functionality
- Claude executable command building
- Cross-platform path detection

#### `test_claude_instance_orchestrator_metrics.py`
Tests metrics and token parsing:
- JSON token usage parsing (multiple formats)
- Regex fallback token parsing
- Cost calculation based on token usage
- Status reporting and formatting
- Result serialization and file generation
- Token statistics (median, percentages)

### Integration Tests

#### `test_claude_instance_orchestrator_integration.py`
Tests end-to-end workflow and async execution:
- Complete orchestrator workflow with real file system
- Async subprocess execution (mocked for safety)
- Multiple instance coordination
- Status reporting with real data
- Main function argument parsing
- Error handling and timeout scenarios

## Running Tests

### Run All Tests
```bash
cd tests/scripts
python test_runner.py
```

### Run Specific Test Suite
```bash
cd tests/scripts
python test_runner.py unit          # Unit tests only
python test_runner.py commands      # Command tests only
python test_runner.py metrics       # Metrics tests only
python test_runner.py integration   # Integration tests only
```

### Run Individual Test Files
```bash
cd tests/scripts
python -m pytest test_claude_instance_orchestrator_unit.py -v
python -m pytest test_claude_instance_orchestrator_commands.py -v
python -m pytest test_claude_instance_orchestrator_metrics.py -v
python -m pytest test_claude_instance_orchestrator_integration.py -v
```

### Run Specific Test Methods
```bash
cd tests/scripts
python -m pytest test_claude_instance_orchestrator_unit.py::TestInstanceConfig::test_instance_config_basic_creation -v
python -m pytest test_claude_instance_orchestrator_commands.py::TestCommandDiscovery -v
```

## Test Coverage

The tests cover the following core functions and protect against regression:

### Core Data Structures
- ✅ `InstanceConfig` creation and validation
- ✅ `InstanceStatus` state management
- ✅ Dataclass serialization and defaults

### Command Management
- ✅ Command discovery from file system
- ✅ YAML frontmatter parsing
- ✅ Command validation and inspection
- ✅ Claude executable detection
- ✅ Command line building with all options

### Metrics and Parsing
- ✅ JSON token usage parsing (5+ formats)
- ✅ Regex fallback parsing
- ✅ Cost calculation (Claude 3.5 Sonnet pricing)
- ✅ Token statistics and formatting
- ✅ Status report generation

### Orchestration Workflow
- ✅ Multi-instance management
- ✅ Async execution coordination
- ✅ Staggered startup timing
- ✅ Status monitoring and reporting
- ✅ Result serialization and file output

### Error Handling
- ✅ Invalid command detection
- ✅ Process timeout handling
- ✅ Exception recovery
- ✅ Malformed input handling

## Safety Considerations

All tests are designed to be safe and non-destructive:

- **No Real Claude Execution**: Tests mock subprocess calls to avoid running actual Claude commands
- **Temporary File System**: All file operations use temporary directories that are cleaned up
- **Safe Command Substitution**: When real subprocess execution is needed, safe commands like `echo` are used
- **Isolated Environment**: Tests don't modify global state or system configuration
- **Fast Execution**: Tests use short timeouts and delays to run quickly

## Test Dependencies

- `pytest` - Test framework
- `pytest-asyncio` - For async test support
- Standard library modules: `unittest.mock`, `tempfile`, `pathlib`, `json`

## Adding New Tests

When adding functionality to the orchestrator, add corresponding tests:

1. **Unit tests** for new functions/methods in the appropriate test file
2. **Integration tests** for new workflow features in the integration test file
3. **Mock external dependencies** to keep tests fast and safe
4. **Use temporary directories** for any file system operations
5. **Test both success and failure scenarios**

## Known Limitations

- Tests mock subprocess execution for safety, so actual Claude command execution is not tested
- Cross-platform path detection is tested with mocks rather than real environments
- Database integration tests are not included (would require real database setup)
- Network-dependent features are mocked

The tests provide comprehensive coverage of the orchestrator's core logic while remaining safe, fast, and reliable for continuous integration.