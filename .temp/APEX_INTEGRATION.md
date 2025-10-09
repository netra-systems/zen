# Zen Apex Agent CLI Integration

## Overview

The `zen --apex` integration enables seamless access to the agent CLI functionality through the Zen orchestrator, designed for GCP deployment with proper package distribution support.

## Implementation

### Architecture

```
zen --apex <args>
    ↓
zen_orchestrator.py (--apex detection)
    ↓
subprocess: python -m scripts.agent_cli <filtered_args>
    ↓
agent_cli.py (with shared module from GCP PYTHONPATH)
    ↓
WebSocket → Backend (with optional JSONL logs)
```

### Key Features

1. **No Hardcoded Paths**: Uses `python -m scripts.agent_cli` for package compatibility
2. **Log Forwarding**: Collects recent JSONL logs from `.claude/Projects`
3. **Platform-Aware**: Supports macOS, Windows, Linux path resolution
4. **Security**: Directory traversal prevention, input sanitization
5. **Graceful Degradation**: Log collection failures don't block message sending

## Usage

### Basic Agent Interaction
```bash
zen --apex --message "your prompt" --env staging
```

### With Log Forwarding (Recommended - Single Log)
```bash
zen --apex --message "analyze these logs" --send-logs
```

### Custom Log Location
```bash
zen --apex --send-logs --logs-project my-project --logs-path /custom/path
```

### Advanced: Multiple Logs (Use with Caution)
```bash
zen --apex \
  --message "prompt" \
  --send-logs \
  --logs-count 2 \
  --logs-project specific-project \
  --logs-path /path/to/logs \
  --logs-user username
```

## New CLI Arguments

### Apex Mode
- `--apex`, `-a`: Enable apex agent CLI mode

### Log Forwarding
- `--send-logs`, `--logs`: Attach recent JSONL logs to message payload
- `--logs-count N`: Number of log files to collect (default: 1, recommended for best results)
- `--logs-project NAME`: Specific project to collect logs from
- `--logs-path PATH`: Custom path to `.claude/Projects` directory
- `--logs-user USERNAME`: Windows username for path resolution

**Best Practice:** Use 1 log file at a time (default) with payloads under 1MB for optimal analysis accuracy.

## Files Added/Modified

### Created
- `scripts/agent_logs.py` - Log collection helper
- `scripts/__init__.py` - Package initialization
- `scripts/__main__.py` - Module entry point
- `tests/test_agent_logs.py` - Unit tests (66 tests, 94% coverage)
- `docs/apex_integration_test_plan.md` - Detailed testing guide

### Modified
- `zen_orchestrator.py`:
  - Line 2445-2446: Added `--apex/-a` argument
  - Line 2960-2975: Apex delegation logic
- `scripts/agent_cli.py`:
  - Line 5152: Added `main(argv)` parameter
  - Line 5454-5490: Log-forwarding arguments
  - Line 2595-2614: WebSocketClient log config
  - Line 3731-3748: AgentCLI log config
  - Line 2996-3026: Log attachment in send_message()
- `pyproject.toml`:
  - Line 64: Added `scripts` to packages list

## Deployment Requirements

### GCP Environment
- `shared` module is vendored in the zen repo (no external dependency required)
- E2E_OAUTH_SIMULATION_KEY configured for authentication
- Backend services running and accessible
- Optional: Set `APEX_BACKEND_PATH` environment variable for advanced backend features

### Local Development
- The vendored `shared/` module is included in the zen repository
- No external netra-apex dependency required for basic agent_cli functionality
- Optional: Set `APEX_BACKEND_PATH` environment variable for advanced features: `export APEX_BACKEND_PATH=/path/to/netra-apex`
- Install agent_cli dependencies: `pip install websockets aiohttp rich pyjwt psutil pyyaml pydantic email-validator`

### Package Installation
```bash
pip install netra-zen
# or for development
pip install -e .
```

## Testing

### Unit Tests
```bash
pytest tests/test_agent_logs.py -v
# Expected: 66 tests pass, 94% coverage
```

### Integration Testing
Requires GCP backend deployment with shared module:
```bash
zen --apex --help  # Should show agent_cli help
zen --apex --message "test" --env staging
```

## Security Features

1. **Path Sanitization**: Prevents directory traversal attacks
2. **Input Validation**: Project names, file counts validated
3. **Error Handling**: Graceful failures with user feedback
4. **No Data Exposure**: Logs collected only when explicitly requested

## Platform Support

### macOS/Linux
Default path: `~/.claude/Projects/<project>/`

### Windows
Default path: `C:\Users\<username>\.claude\Projects\<project>\`

Override with `--logs-user` for custom username.

## Troubleshooting

### "ModuleNotFoundError: No module named 'shared'"
- **Cause**: Missing GCP backend environment
- **Solution**: Deploy to GCP where shared module is available via PYTHONPATH

### "No logs found"
- **Cause**: `.claude/Projects` directory doesn't exist or is empty
- **Solution**: Verify directory structure or use `--logs-path` to specify location

### "zen --apex --help" shows zen help instead of agent_cli help
- **Cause**: Package not installed correctly
- **Solution**: Run `pip install -e .` to reinstall in development mode

## API Reference

### collect_recent_logs()

```python
from scripts.agent_logs import collect_recent_logs

logs = collect_recent_logs(
    limit=5,                    # Max number of log files
    project_name=None,          # Specific project or None for most recent
    base_path=None,             # Override .claude/Projects path
    username=None,              # Windows username
    platform_name=None          # Platform override for testing
)
# Returns: List[Dict[str, Any]] or None
```

## Compliance

- ✅ No hardcoded local paths
- ✅ Package-friendly structure
- ✅ GCP deployment ready
- ✅ Comprehensive test coverage
- ✅ Security best practices
- ✅ Cross-platform support

## Version

Implemented in netra-zen v1.0.5+

## See Also

- [Detailed Test Plan](docs/apex_integration_test_plan.md)
- [Master Implementation Plan](docs/zen_agent_cli_parallel_plan.md)
- [Agent CLI Documentation](scripts/agent_cli.py)
