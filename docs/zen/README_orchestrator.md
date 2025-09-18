# Claude Code Instance Orchestrator

Multi-platform orchestrator for running multiple Claude Code instances in parallel with enhanced Mac compatibility.

## Features

- **Mac-friendly**: Auto-detects Claude executable in Homebrew paths
- **Parallel execution**: Run multiple Claude instances concurrently
- **Real-time streaming**: Stream JSON output from all instances
- **Command validation**: Validates slash commands against available commands
- **Flexible configuration**: Use default instances or custom JSON config
- **Comprehensive logging**: Detailed execution logs and results

## Installation Requirements

1. **Claude Code**: Install Claude Code CLI
   ```bash
   npm install -g @anthropic/claude-code
   ```

2. **Python 3.7+**: Required for the orchestrator
   ```bash
   # macOS (with Homebrew)
   brew install python3
   
   # Verify installation
   python3 --version
   ```

## Usage

### Quick Start (Default Configuration)
```bash
# Run with default instances
python3 scripts/claude_instance_orchestrator.py

# Dry run to see commands without executing
python3 scripts/claude_instance_orchestrator.py --dry-run

# Use the convenient wrapper script
./claude-orchestrator --dry-run
```

### List Available Commands
```bash
python3 scripts/claude_instance_orchestrator.py --list-commands
./claude-orchestrator --list-commands
```

### Custom Configuration
```bash
# Use custom config file
python3 scripts/claude_instance_orchestrator.py --config my-config.json

# Specify different workspace
python3 scripts/claude_instance_orchestrator.py --workspace ~/my-project
```

## Configuration

### Example Configuration File
See `scripts/claude-orchestrator-config-example.json`:

```json
{
  "instances": [
    {
      "name": "test-creator",
      "command": "/createtestsv2 unit", 
      "description": "Create unit tests for the project",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json"
    },
    {
      "name": "ssot-gardener",
      "command": "/ssotgardener",
      "description": "SSOT maintenance and cleanup", 
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json"
    }
  ]
}
```

### Configuration Options

- **name**: Unique identifier for the instance
- **command**: Slash command to execute (e.g., `/createtestsv2 unit`)
- **description**: Human-readable description
- **permission_mode**: `bypassPermissions` (auto-accept) or `interactive` (prompt)
- **output_format**: `stream-json` (real-time) or `json` (batch)
- **allowed_tools**: Optional list of allowed tool names
- **session_id**: Optional session identifier
- **clear_history**: Clear history before running (boolean)
- **compact_history**: Compact history before running (boolean)
- **pre_commands**: List of commands to run before main command

## Mac-Specific Features

The orchestrator includes Mac-specific enhancements:

1. **Auto-detection**: Searches common Homebrew paths:
   - `/opt/homebrew/bin/claude` (ARM Macs)
   - `/usr/local/bin/claude` (Intel Macs) 
   - `~/.local/bin/claude` (User install)

2. **PATH Enhancement**: Automatically adds Mac paths to environment

3. **Directory Handling**: Supports tilde expansion (`~/project`)

4. **Error Messages**: Mac-specific installation guidance

## Command Line Options

```
--workspace PATH        Workspace directory (default: current directory)
--output PATH          Output file for results (auto-generated if not specified)
--config PATH          Custom instance configuration file
--dry-run              Show commands without executing
--list-commands        List available slash commands and exit
--inspect-command CMD  Inspect specific slash command and exit
--output-format FORMAT Output format: json or stream-json (default: stream-json)
--timeout SECONDS      Timeout per instance (default: 300)
```

## Output

### Real-time Output
With `--output-format=stream-json`, you'll see real-time output:
```
[instance-name] STDOUT: {"type": "agent_started", "data": {...}}
[instance-name] STDOUT: {"type": "tool_executing", "data": {...}}
```

### Results File
Results are automatically saved to a timestamped JSON file:
```
claude_instances_results_20250913_123456_testcreator_ssotgardener.json
```

Contains:
- Execution summary (completed/failed counts)
- Individual instance results
- Timing information
- Full output capture

## Troubleshooting

### Claude Not Found
```bash
# Check if Claude is installed
which claude
npm list -g @anthropic/claude-code

# Install if missing
npm install -g @anthropic/claude-code
```

### Permission Issues
```bash
# Make scripts executable
chmod +x scripts/claude_instance_orchestrator.py
chmod +x claude-orchestrator
```

### Python Issues
```bash
# Check Python version
python3 --version

# Install required packages (all standard library)
# No additional packages needed
```

## Examples

### Development Workflow
```bash
# Create tests, run SSOT gardener, and run integration tests
./claude-orchestrator --config scripts/claude-orchestrator-config-example.json

# Quick test creation only
python3 scripts/claude_instance_orchestrator.py --config - <<EOF
{
  "instances": [
    {
      "name": "quick-test",
      "command": "/createtestsv2 unit", 
      "description": "Quick test creation",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json"
    }
  ]
}
EOF
```

### Debugging
```bash
# Dry run to debug commands
./claude-orchestrator --dry-run --config my-config.json

# Inspect specific commands
./claude-orchestrator --inspect-command /createtestsv2
```