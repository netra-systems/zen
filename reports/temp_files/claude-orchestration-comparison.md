# Claude Code Orchestration Tools Comparison

This document compares two Python scripts designed to manage Claude Code instances and explains their different use cases, configurations, and permission settings.

## Overview

| Script | Purpose | Execution Model | Best For |
|--------|---------|----------------|----------|
| `claude-instance-orchestrator.py` | Execute Claude Code slash commands | Async headless automation | CI/CD, batch operations |
| `claude_terminal_launcher.py` | Launch Claude terminal sessions | Terminal session management | Interactive development |

---

## claude-instance-orchestrator.py

### Purpose
Automated execution of Claude Code slash commands in headless mode with structured reporting.

### Key Features
- **Slash Command Discovery**: Automatically finds available commands in `.claude/commands/`
- **Async Execution**: Runs multiple instances concurrently using `asyncio`
- **Command Validation**: Validates commands exist before execution
- **Structured Output**: JSON results with execution status and timing
- **Built-in Configurations**: Predefined setups for common tasks

### Default Configuration (Updated)
```python
[
    InstanceConfig(
        name="test_creator",
        command="/createtestsv2",
        description="Run unit tests with real services",
        allowed_tools=["Bash", "Read", "Write", "Glob", "Grep"],
        permission_mode="bypassPermissions"
    ),
    InstanceConfig(
        name="ssot",
        command="/ssotgardener",
        description="Deploy to GCP staging environment",
        allowed_tools=["Bash", "Read", "Write", "WebFetch"],
        permission_mode="bypassPermissions"
    )
]
```

### Usage Examples
```bash
# List available slash commands
python scripts/claude-instance-orchestrator.py --list-commands

# Inspect a specific command
python scripts/claude-instance-orchestrator.py --inspect-command "/createtestsv2"

# Dry run to see what would be executed
python scripts/claude-instance-orchestrator.py --dry-run

# Run with custom config
python scripts/claude-instance-orchestrator.py --config custom_config.json

# Run with custom output location
python scripts/claude-instance-orchestrator.py --output results.json
```

### Permission Modes
- `"bypassPermissions"` - Automatically accept all edit operations
- `"ask"` - Prompt for confirmation on edits
- `"denyEdits"` - Deny all edit operations

---

## claude_terminal_launcher.py

### Purpose
Launch and manage multiple Claude terminal sessions with cross-platform support.

### Key Features
- **Cross-Platform**: Supports Windows Terminal, PowerShell, cmd, macOS Terminal, Linux terminals
- **Process Monitoring**: Tracks terminal status and handles auto-restart
- **Headless Mode**: Can run without GUI terminals
- **Daemon Mode**: Background operation with PID file management
- **Flexible Configuration**: JSON-based terminal configurations

### Default Configuration
```json
{
  "terminals": [
    {
      "name": "Main Development",
      "args": ["--project", "netra-apex"],
      "working_dir": null
    },
    {
      "name": "Testing Terminal",
      "args": ["--project", "netra-apex", "--context", "testing"],
      "working_dir": null
    },
    {
      "name": "Debugging Session",
      "args": ["--project", "netra-apex", "--context", "debug"],
      "working_dir": null
    }
  ],
  "terminal_type": "auto",
  "delay_between_launches": 1.0,
  "headless_options": {
    "log_output": true,
    "log_level": "INFO",
    "auto_restart": false,
    "restart_delay": 30,
    "max_restarts": 3
  }
}
```

### Usage Examples
```bash
# Generate default configuration
python claude_terminal_launcher.py --generate-config

# Launch all terminals
python claude_terminal_launcher.py

# Use custom configuration
python claude_terminal_launcher.py --config my_config.json

# Run in headless mode
python claude_terminal_launcher.py --headless

# Run as daemon
python claude_terminal_launcher.py --daemon

# Force specific terminal type
python claude_terminal_launcher.py --terminal-type wt

# List active terminals
python claude_terminal_launcher.py --list
```

---

## Allowing All Permissions

### For claude-instance-orchestrator.py

#### Method 1: Full Tool Access in Configuration
```python
InstanceConfig(
    name="unrestricted_instance",
    command="/your-command",
    description="Instance with full permissions",
    allowed_tools=[
        "Bash", "Read", "Write", "Edit", "MultiEdit", "Glob", "Grep",
        "WebFetch", "WebSearch", "Task", "TodoWrite", "NotebookEdit",
        "ExitPlanMode", "BashOutput", "KillShell"
    ],
    permission_mode="bypassPermissions"
)
```

#### Method 2: Wildcard Access (if supported)
```python
InstanceConfig(
    name="all_permissions",
    command="/your-command",
    description="Instance with all permissions",
    allowed_tools=["*"],  # May not be supported - check Claude Code docs
    permission_mode="bypassPermissions"
)
```

#### Method 3: No Tool Restrictions
```python
InstanceConfig(
    name="no_restrictions",
    command="/your-command",
    description="Instance with no tool restrictions",
    allowed_tools=[],  # Empty list may mean no restrictions
    permission_mode="bypassPermissions"
)
```

### For claude_terminal_launcher.py

Terminal launcher doesn't directly control Claude Code permissions - it just launches terminals. Permissions are controlled by:

1. **Claude Code CLI arguments**: Add permission flags to terminal args
```json
{
  "name": "Unrestricted Terminal",
  "args": ["--project", "netra-apex", "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch,Task"],
  "working_dir": null
}
```

2. **Global Claude Code settings**: Configure in Claude Code's global settings
3. **Per-session configuration**: Use Claude Code's interactive permission settings

### Claude Code Permission Flags
When launching Claude Code directly, you can use:
```bash
# Allow specific tools
claude --allowedTools="Bash,Read,Write,Edit,Glob,Grep,WebFetch"

# Set permission mode
claude --permission-mode="bypassPermissions"

# Combine both
claude --allowedTools="Bash,Read,Write,Edit" --permission-mode="bypassPermissions"
```

---

## Use Case Recommendations

### Use claude-instance-orchestrator.py for:
- ✅ **Automated Testing**: Running test suites via slash commands
- ✅ **CI/CD Pipelines**: Automated deployment and compliance checks
- ✅ **Batch Operations**: Processing multiple tasks concurrently
- ✅ **Structured Reporting**: Need JSON output for further processing
- ✅ **Headless Automation**: Server environments without GUI

### Use claude_terminal_launcher.py for:
- ✅ **Interactive Development**: Multiple live coding sessions
- ✅ **Debugging Workflows**: Separate terminals for different contexts
- ✅ **Long-Running Sessions**: Persistent Claude instances with monitoring
- ✅ **Cross-Platform Development**: Need platform-specific terminal integration
- ✅ **Process Management**: Auto-restart and daemon capabilities

---

## Security Considerations

### Permission Best Practices
1. **Principle of Least Privilege**: Only grant tools actually needed
2. **Environment Separation**: Different permission sets for dev/staging/prod
3. **Audit Logging**: Monitor tool usage in production environments
4. **Review Slash Commands**: Inspect command files before granting broad permissions

### Risk Assessment by Tool
- **Low Risk**: `Read`, `Glob`, `Grep` - Read-only operations
- **Medium Risk**: `Write`, `Edit` - File modifications
- **High Risk**: `Bash`, `WebFetch` - System execution and external access
- **Critical Risk**: `Task` - Can spawn other agents with their own permissions

---

## Troubleshooting

### Common Issues

#### claude-instance-orchestrator.py
- **Command Not Found**: Use `--list-commands` to see available slash commands
- **Permission Denied**: Check `allowed_tools` and `permission_mode` settings
- **Async Failures**: Check individual instance logs in output JSON

#### claude_terminal_launcher.py
- **Terminal Not Opening**: Verify terminal type detection with `--terminal-type auto`
- **Process Not Starting**: Check working directory and Claude Code installation
- **Log Files Missing**: Ensure script has write permissions to `claude_logs/` directory

### Debug Commands
```bash
# Check Claude Code installation
claude --version

# Verify workspace has .claude directory
ls -la .claude/commands/

# Test basic Claude Code functionality
claude --help
```

---

## Integration Examples

### CI/CD Pipeline (GitHub Actions)
```yaml
- name: Run Claude Code Tests
  run: |
    python scripts/claude-instance-orchestrator.py \
      --config ci_config.json \
      --output test_results.json
```

### Development Setup Script
```bash
#!/bin/bash
# Start development environment
python claude_terminal_launcher.py --config dev_config.json --headless &
echo "Claude development environment started"
```

This documentation provides comprehensive guidance for using both Claude orchestration tools effectively while maintaining proper security practices.