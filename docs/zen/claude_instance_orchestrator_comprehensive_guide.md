# Claude Instance Orchestrator - Comprehensive Guide

## Table of Contents
1. [Overview](#overview)
2. [Installation and Setup](#installation-and-setup)
3. [Core Features](#core-features)
4. [Usage Examples](#usage-examples)
5. [Configuration Reference](#configuration-reference)
6. [Token Budget Management](#token-budget-management)
7. [Advanced Features](#advanced-features)
8. [Output Formats and Monitoring](#output-formats-and-monitoring)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)
11. [Best Practices](#best-practices)

## Overview

The Claude Instance Orchestrator is a powerful Python-based tool for managing and executing multiple Claude Code instances in parallel. It provides comprehensive monitoring, token budget management, real-time output streaming, and flexible configuration options.

### Key Benefits
- **Parallel Execution**: Run multiple Claude Code instances concurrently with configurable startup delays
- **Token Budget Control**: Built-in token budget management with enforcement modes
- **Real-time Monitoring**: Live status reports and output streaming
- **Multi-platform Support**: Enhanced Mac compatibility with automatic executable detection
- **Flexible Configuration**: JSON-based configuration with validation
- **Comprehensive Logging**: Detailed execution logs and result persistence

## Installation and Setup

### Prerequisites
1. **Claude Code CLI**: Required for executing Claude instances
   ```bash
   npm install -g @anthropic/claude-code
   ```

2. **Python 3.7+**: The orchestrator requires Python 3.7 or higher
   ```bash
   # macOS with Homebrew
   brew install python3

   # Ubuntu/Debian
   sudo apt update && sudo apt install python3 python3-pip

   # Verify installation
   python3 --version
   ```

3. **Required Python Libraries**: All dependencies are part of the Python standard library
   - `asyncio`, `json`, `logging`, `subprocess`, `pathlib`, `argparse`, `datetime`, `uuid`

### Directory Structure
```
project/
├── claude_instance_orchestrator.py
├── token_budget/              # Optional token budget package
│   ├── budget_manager.py
│   └── visualization.py
├── .claude/                   # Claude Code workspace
│   └── commands/             # Slash commands directory
└── docs/                     # Documentation
```

## Core Features

### 1. Multi-Instance Management
Execute multiple Claude Code instances simultaneously with intelligent coordination:

```python
# Basic instance configuration
{
  "command": "/createtestsv2 unit",
  "name": "test-creator",
  "description": "Create comprehensive unit tests",
  "permission_mode": "bypassPermissions",
  "output_format": "stream-json"
}
```

### 2. Token Budget Management
Built-in token tracking and budget enforcement:

```bash
# Set overall budget
python3 claude_instance_orchestrator.py --overall-token-budget 100000

# Set per-command budgets
python3 claude_instance_orchestrator.py \
  --command-budget "/createtestsv2=50000" \
  --command-budget "/ssotgardener=30000" \
  --budget-enforcement-mode block
```

### 3. Real-time Output Streaming
Live monitoring with formatted output display:

```
╔═[test-creator]═══════════════╗
║ Starting test creation process...
║ Found 15 source files to analyze
╚═══════════════════════════════╝

🏁 [test-creator] COMPLETED - 45 lines processed, output saved
```

### 4. Flexible Scheduling
Support for delayed execution and scheduled runs:

```bash
# Start in 2 hours
python3 claude_instance_orchestrator.py --start-at "2h"

# Start at specific time
python3 claude_instance_orchestrator.py --start-at "14:30"

# Start tomorrow at 1 AM
python3 claude_instance_orchestrator.py --start-at "1am"
```

## Usage Examples

### Basic Usage

#### 1. Quick Start with Defaults
```bash
# Run with default configuration
python3 claude_instance_orchestrator.py

# Dry run to preview commands
python3 claude_instance_orchestrator.py --dry-run

# Quiet mode (errors only)
python3 claude_instance_orchestrator.py --quiet
```

#### 2. Custom Workspace
```bash
# Specify workspace directory
python3 claude_instance_orchestrator.py --workspace ~/my-project

# Use relative path
python3 claude_instance_orchestrator.py --workspace ./frontend
```

#### 3. Output Control
```bash
# Custom output file
python3 claude_instance_orchestrator.py --output results.json

# Limit console output
python3 claude_instance_orchestrator.py --max-console-lines 10

# Increase line length
python3 claude_instance_orchestrator.py --max-line-length 1000
```

### Advanced Usage

#### 1. Custom Configuration File
Create a configuration file `my-config.json`:

```json
{
  "instances": [
    {
      "name": "frontend-tests",
      "command": "/createtestsv2 frontend unit",
      "description": "Create frontend unit tests",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json",
      "max_tokens_per_command": 25000,
      "pre_commands": ["/clear", "/compact"]
    },
    {
      "name": "backend-integration",
      "command": "/createtestsv2 backend integration",
      "description": "Create backend integration tests",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json",
      "allowed_tools": ["Write", "Edit", "Bash", "Read"],
      "session_id": "backend-session-1"
    },
    {
      "name": "ssot-cleanup",
      "command": "/ssotgardener removing legacy",
      "description": "Clean up legacy code patterns",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json",
      "clear_history": true
    }
  ]
}
```

Run with custom configuration:
```bash
python3 claude_instance_orchestrator.py --config my-config.json
```

#### 2. Token Budget Configuration
```bash
# Comprehensive budget setup
python3 claude_instance_orchestrator.py \
  --config my-config.json \
  --overall-token-budget 200000 \
  --command-budget "/createtestsv2=80000" \
  --command-budget "/ssotgardener=60000" \
  --budget-enforcement-mode warn \
  --status-report-interval 30
```

#### 3. Scheduled Execution
```bash
# Development workflow scheduled for tonight
python3 claude_instance_orchestrator.py \
  --config production-tests.json \
  --start-at "2am" \
  --output overnight-results.json \
  --quiet
```

### Command Discovery and Inspection

#### 1. List Available Commands
```bash
# Show all available slash commands
python3 claude_instance_orchestrator.py --list-commands

# Example output:
# Available Slash Commands:
# ==================================================
# /clear                    - Clear session history
# /compact                  - Compact session history
# /createtestsv2           - Create comprehensive test suites
# /ssotgardener            - SSOT maintenance and cleanup
# /gitcommitgardener       - Git commit management
```

#### 2. Inspect Specific Commands
```bash
# Get detailed information about a command
python3 claude_instance_orchestrator.py --inspect-command /createtestsv2

# Example output:
# Command: /createtestsv2
# ==================================================
# File: /path/to/.claude/commands/createtestsv2.md
# Configuration:
#   description: Create comprehensive test suites
#   category: testing
#   timeout: 300
#   required_tools: ["Write", "Edit", "Read"]
```

## Configuration Reference

### Instance Configuration Options

```json
{
  "command": "string",                    // Required: Slash command to execute
  "name": "string",                      // Optional: Instance identifier (defaults to command)
  "description": "string",               // Optional: Human-readable description
  "allowed_tools": ["string"],           // Optional: List of allowed tool names
  "permission_mode": "string",           // Optional: "bypassPermissions" or "interactive" (default: "bypassPermissions")
  "output_format": "string",             // Optional: "stream-json" or "json" (default: "stream-json")
  "session_id": "string",                // Optional: Session identifier for Claude
  "clear_history": boolean,              // Optional: Clear history before running (default: false)
  "compact_history": boolean,            // Optional: Compact history before running (default: false)
  "pre_commands": ["string"],            // Optional: Commands to run before main command
  "max_tokens_per_command": integer      // Optional: Token budget for this instance
}
```

### Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--workspace` | PATH | current directory | Workspace directory |
| `--output` | PATH | auto-generated | Output file for results |
| `--config` | PATH | none | Custom configuration file |
| `--dry-run` | flag | false | Show commands without executing |
| `--list-commands` | flag | false | List available commands and exit |
| `--inspect-command` | string | none | Inspect specific command and exit |
| `--output-format` | choice | stream-json | Output format (json/stream-json) |
| `--timeout` | integer | 10000 | Timeout per instance (seconds) |
| `--max-console-lines` | integer | 5 | Max lines shown per instance |
| `--quiet` | flag | false | Minimize output to errors only |
| `--startup-delay` | float | 5.0 | Delay between instance launches |
| `--max-line-length` | integer | 800 | Max characters per console line |
| `--status-report-interval` | integer | 5 | Seconds between status reports |
| `--start-at` | string | none | Schedule start time |
| `--overall-token-budget` | integer | none | Global token budget |
| `--command-budget` | string | none | Per-command budget (repeatable) |
| `--budget-enforcement-mode` | choice | warn | Budget enforcement (warn/block) |
| `--disable-budget-visuals` | flag | false | Disable budget visualization |

## Token Budget Management

### Overview
The orchestrator includes sophisticated token budget management with real-time tracking and enforcement.

### Budget Types

#### 1. Overall Budget
Global token limit across all instances:
```bash
python3 claude_instance_orchestrator.py --overall-token-budget 500000
```

#### 2. Per-Command Budgets
Individual limits for specific commands:
```bash
python3 claude_instance_orchestrator.py \
  --command-budget "/createtestsv2=100000" \
  --command-budget "/ssotgardener=75000"
```

#### 3. Per-Instance Budgets
Set in configuration file:
```json
{
  "name": "heavy-task",
  "command": "/complex-operation",
  "max_tokens_per_command": 150000
}
```

### Enforcement Modes

#### Warn Mode (Default)
Logs warnings but continues execution:
```bash
python3 claude_instance_orchestrator.py \
  --budget-enforcement-mode warn \
  --overall-token-budget 100000
```

#### Block Mode
Prevents execution when budget would be exceeded:
```bash
python3 claude_instance_orchestrator.py \
  --budget-enforcement-mode block \
  --overall-token-budget 100000
```

### Token Tracking Features

#### Real-time Monitoring
```
║ TOKEN BUDGET STATUS |
║ Overall: [████████░░] 80% 80K/100K
║ Command Budgets:
║   /createtestsv2      [██████░░░░] 60% 30K/50K
║   /ssotgardener       [████░░░░░░] 40% 20K/50K
```

#### Detailed Token Breakdown
- Input tokens
- Output tokens
- Cache read tokens (separate tracking)
- Cache creation tokens (separate tracking)
- Total cost in USD (when available)

#### Message ID Deduplication
Prevents double-counting tokens from the same Claude response:
```python
# Automatic deduplication based on message IDs
status.processed_message_ids.add(message_id)
```

## Advanced Features

### 1. Delayed Startup
Control instance launch timing to prevent resource conflicts:

```bash
# 2-second delay between instances
python3 claude_instance_orchestrator.py --startup-delay 2.0

# Half-second delay for fast machines
python3 claude_instance_orchestrator.py --startup-delay 0.5
```

### 2. Session Management
Advanced session handling with history control:

```json
{
  "name": "clean-session",
  "command": "/mycommand",
  "session_id": "dedicated-session-1",
  "clear_history": true,
  "compact_history": false,
  "pre_commands": ["/clear", "system message: Focus on testing"]
}
```

### 3. Command Validation
Automatic validation of slash commands against available commands:

```python
# Validates command exists before execution
def validate_command(self, command: str) -> bool:
    available_commands = self.discover_available_commands()
    base_command = command.split()[0]
    return base_command in available_commands
```

### 4. Multi-Platform Executable Detection
Intelligent Claude executable discovery:

```python
# Mac-specific paths
possible_paths = [
    "/opt/homebrew/bin/claude",  # Mac Homebrew ARM
    "/usr/local/bin/claude",     # Mac Homebrew Intel
    "~/.local/bin/claude",       # User local install
    "/usr/bin/claude",           # System install
]
```

### 5. Runtime Budget Enforcement
Dynamic budget checking during execution:

```python
def _check_runtime_budget_violation(self, status, instance_name, base_command):
    # Check budgets during execution
    # Terminate instances if needed in block mode
    if violation_detected and self.budget_manager.enforcement_mode == "block":
        self._terminate_instance(status, instance_name, reason)
```

## Output Formats and Monitoring

### 1. Stream JSON Format (Default)
Real-time streaming with structured JSON output:

```json
{"type": "agent_started", "data": {"instance": "test-creator"}}
{"type": "tool_executing", "data": {"tool": "Write", "file": "test.py"}}
{"type": "token_usage", "data": {"total": 1500, "input": 1000, "output": 500}}
```

### 2. JSON Format
Batch output after completion:

```json
{
  "status": "completed",
  "output": "Full command output...",
  "tokens": {
    "total": 2500,
    "input": 1800,
    "output": 700,
    "cached": 200
  },
  "duration": 45.2
}
```

### 3. Status Reports
Periodic status updates with visual progress:

```
╔═══ STATUS REPORT [14:23:45] ═══╗
║ Total: 3 instances
║ Running: 2, Completed: 1, Failed: 0, Pending: 0
║ Tokens: 15.2K total, 3.1K cached | Median: 5K | Tools: 12
║
║  Status   Name                Duration   Tokens   vs Med   Cache    Tools
║  ──────   ──────────────────  ────────   ──────   ──────   ──────   ─────
║  ✅       test-creator        45.2s      8.5K     +70%     2.1K     5
║  🏃       ssot-gardener       32.1s      4.2K     -16%     800      3
║  🏃       integration-tests   28.5s      2.5K     -50%     200      4
╚═══════════════════════════════════════╝
```

### 4. Result Persistence
Automatic saving of comprehensive results:

```json
{
  "total_instances": 3,
  "completed": 2,
  "failed": 1,
  "instances": {
    "test-creator": {
      "status": "completed",
      "duration": "45.20s",
      "total_tokens": 8500,
      "input_tokens": 6000,
      "output_tokens": 2000,
      "cached_tokens": 500,
      "tool_calls": 5,
      "total_cost_usd": 0.045
    }
  },
  "metadata": {
    "start_datetime": "2024-09-17T14:23:45",
    "generated_filename": "results_20240917_142345_testcreator_ssotgardener.json",
    "token_usage": {
      "total_tokens": 15200,
      "cache_hit_rate": 12.5
    }
  }
}
```

## Troubleshooting

### Common Issues

#### 1. Claude Executable Not Found
```bash
# Check installation
which claude
npm list -g @anthropic/claude-code

# Install if missing
npm install -g @anthropic/claude-code

# Manual path specification (if needed)
export PATH="/opt/homebrew/bin:$PATH"
```

#### 2. Permission Errors
```bash
# Make orchestrator executable
chmod +x claude_instance_orchestrator.py

# Check workspace permissions
ls -la workspace_directory/
```

#### 3. Token Budget Issues
```bash
# Check budget configuration
python3 claude_instance_orchestrator.py --dry-run \
  --overall-token-budget 100000 \
  --command-budget "/createtestsv2=50000"

# Monitor token usage in real-time
python3 claude_instance_orchestrator.py \
  --status-report-interval 10 \
  --max-console-lines 10
```

#### 4. Output Format Problems
```bash
# Force stream-json format
python3 claude_instance_orchestrator.py \
  --output-format stream-json \
  --max-line-length 1000

# Debug with verbose output
python3 claude_instance_orchestrator.py \
  --max-console-lines 20 \
  --status-report-interval 5
```

### Debug Commands

#### Validate Configuration
```bash
# Test configuration without execution
python3 claude_instance_orchestrator.py --config my-config.json --dry-run

# Inspect available commands
python3 claude_instance_orchestrator.py --list-commands

# Check specific command details
python3 claude_instance_orchestrator.py --inspect-command /createtestsv2
```

#### Monitor Performance
```bash
# Detailed monitoring
python3 claude_instance_orchestrator.py \
  --status-report-interval 15 \
  --max-console-lines 15 \
  --startup-delay 1.0
```

## API Reference

### ClaudeInstanceOrchestrator Class

#### Constructor
```python
def __init__(self,
             workspace_dir: Path,
             max_console_lines: int = 5,
             startup_delay: float = 1.0,
             max_line_length: int = 500,
             status_report_interval: int = 30,
             use_cloud_sql: bool = False,
             quiet: bool = False,
             overall_token_budget: Optional[int] = None,
             budget_enforcement_mode: str = "warn",
             enable_budget_visuals: bool = True)
```

#### Key Methods

##### Instance Management
```python
def add_instance(self, config: InstanceConfig)
# Add a new instance configuration

async def run_instance(self, name: str) -> bool
# Run a single instance asynchronously

async def run_all_instances(self, timeout: int = 300) -> Dict[str, bool]
# Run all configured instances with timeout
```

##### Command Discovery
```python
def discover_available_commands(self) -> List[str]
# Discover available slash commands from .claude/commands/

def validate_command(self, command: str) -> bool
# Validate that a slash command exists

def inspect_command(self, command_name: str) -> Dict[str, Any]
# Get detailed information about a command
```

##### Output and Results
```python
def get_status_summary(self) -> Dict
# Get comprehensive status summary

def save_results(self, output_file: Path = None)
# Save results to JSON file

def generate_output_filename(self, base_filename: str = None) -> Path
# Generate timestamped output filename
```

### InstanceConfig Dataclass

```python
@dataclass
class InstanceConfig:
    command: str                                    # Required: slash command
    name: Optional[str] = None                     # Instance name
    description: Optional[str] = None              # Description
    allowed_tools: List[str] = None               # Allowed tool names
    permission_mode: str = "bypassPermissions"          # Permission mode
    output_format: str = "stream-json"            # Output format
    session_id: Optional[str] = None              # Session ID
    clear_history: bool = False                   # Clear history flag
    compact_history: bool = False                 # Compact history flag
    pre_commands: List[str] = None                # Pre-execution commands
    max_tokens_per_command: Optional[int] = None  # Token budget
```

### InstanceStatus Dataclass

```python
@dataclass
class InstanceStatus:
    name: str                                     # Instance name
    pid: Optional[int] = None                     # Process ID
    status: str = "pending"                       # Status (pending/running/completed/failed)
    start_time: Optional[float] = None            # Start timestamp
    end_time: Optional[float] = None             # End timestamp
    output: str = ""                             # Captured output
    error: str = ""                              # Error output
    total_tokens: int = 0                        # Total token usage
    input_tokens: int = 0                        # Input tokens
    output_tokens: int = 0                       # Output tokens
    cached_tokens: int = 0                       # Cached tokens (backward compatibility)
    cache_read_tokens: int = 0                   # Cache read tokens
    cache_creation_tokens: int = 0               # Cache creation tokens
    tool_calls: int = 0                          # Number of tool calls
    total_cost_usd: Optional[float] = None       # Total cost in USD
    processed_message_ids: set = None            # Deduplication tracking
```

## Best Practices

### 1. Configuration Management
- Use descriptive instance names
- Set appropriate token budgets
- Include clear descriptions
- Validate configurations with `--dry-run`

### 2. Resource Management
- Use appropriate startup delays (1-5 seconds)
- Monitor token usage carefully
- Set reasonable timeouts
- Use quiet mode for production runs

### 3. Monitoring and Debugging
- Enable status reports for long-running operations
- Use stream-json format for real-time monitoring
- Save results for post-execution analysis
- Monitor budget usage proactively

### 4. Token Budget Optimization
- Set overall budget with 20% buffer
- Use per-command budgets for expensive operations
- Monitor cache hit rates for optimization
- Use warn mode initially, block mode for production

### 5. Scheduling and Automation
- Use scheduled execution for resource-intensive tasks
- Implement proper error handling
- Save detailed logs for troubleshooting
- Monitor system resources during execution

### Example Production Configuration
```json
{
  "instances": [
    {
      "name": "critical-tests",
      "command": "/createtestsv2 critical e2e",
      "description": "Critical E2E test creation",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json",
      "max_tokens_per_command": 75000,
      "clear_history": true,
      "allowed_tools": ["Write", "Edit", "Bash", "Read"]
    },
    {
      "name": "ssot-maintenance",
      "command": "/ssotgardener removing legacy",
      "description": "SSOT cleanup and maintenance",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json",
      "max_tokens_per_command": 50000,
      "pre_commands": ["/compact"]
    }
  ]
}
```

```bash
# Production run command
python3 claude_instance_orchestrator.py \
  --config production-config.json \
  --overall-token-budget 200000 \
  --budget-enforcement-mode block \
  --startup-delay 3.0 \
  --status-report-interval 60 \
  --output production-results.json \
  --start-at "2am"
```

This comprehensive guide provides complete coverage of the Claude Instance Orchestrator's capabilities, from basic usage to advanced configuration and production deployment patterns.