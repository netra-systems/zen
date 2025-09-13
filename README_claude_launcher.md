# Claude Terminal Launcher

A comprehensive Python program that launches multiple Claude terminals with specific arguments, supporting both GUI and headless modes.

## Features

### Multi-Platform Support
- **Windows**: Windows Terminal (wt), PowerShell, Command Prompt
- **macOS**: Terminal app
- **Linux**: GNOME Terminal
- **Headless**: Background processes with logging

### Operating Modes

#### GUI Mode (Default)
Launches Claude in visible terminal windows:
```bash
python claude_terminal_launcher.py
```

#### Headless Mode
Runs Claude processes in the background without GUI:
```bash
# Headless with interactive monitoring
python claude_terminal_launcher.py --headless

# Full daemon mode (background with PID file)
python claude_terminal_launcher.py --daemon

# Force headless terminal type
python claude_terminal_launcher.py --terminal-type headless
```

### Key Capabilities

- **Process Monitoring**: Track running sessions with PID, runtime, restart counts
- **Auto-Restart**: Configurable automatic restart on process failure
- **Comprehensive Logging**: All output captured to timestamped log files
- **Signal Handling**: Graceful shutdown on SIGTERM/SIGINT
- **Configuration Management**: JSON-based configuration with defaults
- **Cross-Platform Detection**: Automatic terminal type detection

## Usage Examples

### Basic Usage
```bash
# Generate configuration file
python claude_terminal_launcher.py --generate-config

# Launch with default config
python claude_terminal_launcher.py

# Launch in headless mode
python claude_terminal_launcher.py --headless

# Run as background daemon
python claude_terminal_launcher.py --daemon

# List active sessions
python claude_terminal_launcher.py --list
```

### Custom Configuration
```bash
# Use custom config file
python claude_terminal_launcher.py --config my_setup.json

# Force specific terminal type
python claude_terminal_launcher.py --terminal-type wt
```

## Configuration

The `claude_terminals_config.json` file contains:

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

### Configuration Options

- **terminals**: Array of terminal configurations
  - `name`: Display name for the session
  - `args`: Arguments to pass to Claude
  - `working_dir`: Working directory (null = current directory)

- **terminal_type**: `auto`, `headless`, `wt`, `powershell`, `cmd`, `terminal_mac`, `gnome-terminal`
- **delay_between_launches**: Seconds between launching each terminal
- **headless_options**: Configuration for headless mode
  - `log_output`: Enable output logging
  - `log_level`: Logging level (DEBUG, INFO, WARNING, ERROR)
  - `auto_restart`: Automatically restart failed processes
  - `restart_delay`: Seconds to wait before restart
  - `max_restarts`: Maximum restart attempts

## Headless Mode Features

### Process Management
- **Background Execution**: Processes run without GUI terminals
- **Process Monitoring**: Monitor threads track each process
- **Automatic Restart**: Configurable restart on failure
- **Signal Handling**: Graceful shutdown on system signals

### Logging System
- **Timestamped Logs**: Each session gets unique log files
- **Process Logs**: Separate log files for each Claude instance
- **Launcher Logs**: Main launcher activity logging
- **Log Directory**: All logs stored in `claude_logs/` directory

### Daemon Mode
```bash
python claude_terminal_launcher.py --daemon
```

Features:
- **PID File**: Creates `claude_launcher.pid` for process management
- **Signal Handling**: SIGTERM and SIGINT for graceful shutdown
- **Background Operation**: Runs completely in background
- **Log Monitoring**: Check logs for status and activity

### Monitoring and Management

```bash
# Check running processes
python claude_terminal_launcher.py --list

# Example output for headless sessions:
# 1. Main Development: Running (headless)
#    Args: --project netra-apex
#    Working Dir: /path/to/project
#    Log File: claude_logs/Main_Development_20231213_143022.log
#    PID: 12345
#    Restarts: 0
#    Runtime: 0:15:32
```

### Log Files

- **Launcher Logs**: `claude_logs/launcher_YYYYMMDD_HHMMSS.log`
- **Session Logs**: `claude_logs/SessionName_YYYYMMDD_HHMMSS.log`
- **Restart Logs**: `claude_logs/SessionName_YYYYMMDD_HHMMSS_restart1.log`

## Advanced Usage

### Server/CI Environment
Perfect for server deployments or CI/CD environments:

```bash
# Start as daemon
python claude_terminal_launcher.py --daemon

# Monitor via logs
tail -f claude_logs/*.log

# Stop daemon
kill $(cat claude_launcher.pid)
```

### Development Environment
Ideal for development workflows with multiple contexts:

```bash
# GUI mode for interactive development
python claude_terminal_launcher.py

# Headless mode for background tasks
python claude_terminal_launcher.py --headless --config background_tasks.json
```

## Requirements

- Python 3.6+
- Claude CLI installed and accessible
- Platform-specific terminal applications (for GUI mode)

## Error Handling

- **Process Failures**: Automatic logging and optional restart
- **Configuration Errors**: Falls back to default configuration
- **Signal Handling**: Graceful cleanup on interruption
- **Resource Management**: Proper cleanup of all spawned processes

## Platform-Specific Notes

### Windows
- Prefers Windows Terminal if available
- Falls back to PowerShell or Command Prompt
- Supports process groups for proper cleanup

### macOS
- Uses AppleScript to launch Terminal windows
- Supports working directory specification

### Linux
- Uses GNOME Terminal by default
- Supports other terminal emulators via configuration

This launcher provides a robust solution for managing multiple Claude sessions across different environments and use cases.