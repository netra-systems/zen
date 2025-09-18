# Zen User Guide

Zen runs multiple Code CLI instances for peaceful parallel task execution.

## What is Zen?

Zen allows you to:
- Run multiple Claude Code CLI instances simultaneously (Codex support coming soon)
- Calm results (status, time, token usage)
- Relax **"5-hour limit reached"** lockout fears with easy token budget limits
- Get more value out of your Claude MAX subscription
with scheduling features. (`--run-at "2am"`) 

## Inspiration and background
While developing Netra Apex (commerical product)
our team has been running 100s of parrallel claude code instances.
During that process we got annoyed at the "cognitive overhead"
of each having 10s of terminals open per machine and scrolling mountains of text.
Did the `/command` work or not?

What started as a simple way to make that process more peaceful turned into something we believe will be useful to the community.

Further, as usage limits become more restrictive, getting up at odd hours just to feed the beast got old fast. So we added scheduling to run it at pre-defined times.

Surprisingly, the duration that a command ran and it's presumed difficulty, often had little correlation with actual token usage.
"Simple" git operations would sometimes eat 10x as many as complex issue resolution commands.

The market is moving quickly, codex is getting better and other Code CLIs are coming. How effective a code factory is matters. This V1 alpha is just the start of codifying code CLI dev practices and progressing from alchemy to engineering.

Commercial users who wish to may seemlessly use Zen with Netra Apex (Commercial Product) for the most effective usage and control of business AI spend.

## Limitations

### Budget Enforcement Behavior

**Important:** Zen's budget constraints are client-side only and not enforced server-side by Claude Code or other CLI tools.

- **Local Monitoring Only**: Budgets defined in `zen.yaml` or command-line flags are tracked locally by Zen but cannot prevent the underlying CLI from consuming tokens beyond the limit
- **Team Usage**: When multiple team members use Zen, each instance tracks its own budget independently - there is no shared budget enforcement across users
- **Budget Exceeded Behavior**:
  - `warn` mode: Zen logs warnings but continues execution
  - `block` mode: Zen prevents launching new instances but cannot stop running instances mid-execution
- **Token Counting**: Budget calculations are based on estimates and may not match exact billing from Claude/OpenAI

### Target Audience and Use Cases

**Zen is designed for internal developer productivity and is not suitable for all use cases:**

**✅ Supported Use Cases:**
- Internal development workflows and automation
- Parallel execution of development tasks
- Managing multiple Claude Code instances for team productivity
- Development environment orchestration
- CI/CD integration for development teams

**❌ Not Recommended For:**
- External integration or customer-facing applications
- Production systems requiring guaranteed uptime
- Mission-critical deployments without fallback mechanisms
- Real-time applications requiring sub-second response times
- Applications requiring strict budget enforcement at the API level

### System Limitations

**Conversation History Management:**
- No persistent conversation history across Zen restarts
- Each Claude Code instance maintains its own isolated context
- No cross-instance memory or shared context between parallel executions

**State Persistence:**
- Zen does not persist execution state between sessions
- Interrupted executions cannot be resumed from checkpoints
- No automatic recovery from partial completions

**Parallel Execution Constraints:**
- Limited by system resources (CPU, memory, network bandwidth)
- No built-in load balancing or resource allocation
- Concurrent API rate limits apply to all instances collectively
- Startup delays between instances may be necessary to avoid rate limiting

**Error Handling Limitations:**
- Individual instance failures do not automatically retry
- No circuit breaker pattern for cascading failures
- Limited error aggregation across multiple instances
- Debugging parallel execution can be complex due to interleaved output

### Known Issues

**Windows Permission Issues (Issue #1320):**
- **Problem**: Commands may fail with "This command requires approval" on Windows
- **Workaround**: Zen automatically enables `bypassPermissions` mode on Windows
- **Status**: Partially resolved, see [Issue #1320 Documentation](../docs/issues/ISSUE_1320_ZEN_PERMISSION_ERROR_FIX.md)

**Output Truncation:**
- **Problem**: Long outputs may be truncated in console display
- **Workaround**: Use `--max-console-lines` and `--max-line-length` parameters, or redirect output to files
- **Impact**: Full execution logs are preserved but may not be visible in real-time

**Token Budget Accuracy:**
- **Problem**: Budget calculations may not exactly match actual API billing
- **Cause**: Estimates based on local token counting vs. server-side billing
- **Workaround**: Use conservative budget limits and monitor actual usage through provider dashboards

**Scheduling Precision:**
- **Problem**: `--start-at` timing may have minor delays (±30 seconds)
- **Cause**: System scheduling overhead and startup time variations
- **Workaround**: Account for potential delays in time-sensitive workflows

**Configuration File Validation:**
- **Problem**: Limited validation of JSON configuration files
- **Impact**: Invalid configurations may cause runtime errors
- **Workaround**: Use `--dry-run` to validate configurations before execution

**Resource Cleanup:**
- **Problem**: Interrupted executions may leave background processes running
- **Workaround**: Monitor system processes and manually terminate if necessary
- **Planned Fix**: Improved signal handling and cleanup in future versions

## Installation

### Default Method: pipx (Recommended for ALL Users)

Pipx automatically handles PATH configuration and creates an isolated environment, preventing dependency conflicts.

#### Step 1: Install pipx
```bash
# Windows
pip install --user pipx
python -m pipx ensurepath

# macOS
brew install pipx
pipx ensurepath

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install pipx
pipx ensurepath

# Linux (Other)
pip install --user pipx
pipx ensurepath
```

**Note:** Restart your terminal after running `pipx ensurepath`

#### Step 2: Install zen
```bash
# From PyPI (when published)
pipx install zen-orchestrator

# For local development (editable mode)
cd zen/
pipx install --editable .

# Verify installation
zen --help
```

### Alternative: pip (Manual PATH Configuration Required)

⚠️ **Warning:** Using pip directly often results in PATH issues. We strongly recommend pipx instead.

```bash
pip install zen-orchestrator

# If 'zen' command not found, you'll need to:
# Option 1: Use Python module directly
python -m zen_orchestrator --help

# Option 2: Manually add to PATH (see Troubleshooting)
```

## Understanding the Model Column in Status Reports

### Model Column Behavior

The **Model** column in Zen's status display shows the **actual model used** by Claude Code for each API response, not necessarily the model you configured in your settings.

**Key Points:**
- **Intentional Design**: This column reflects reality - what model Claude actually used to process your request
- **Cost Tracking Value**: Knowing the actual model is critical for accurate cost calculation since different models have vastly different pricing (e.g., Opus costs 5x more than Sonnet)
- **Dynamic Detection**: Zen automatically detects the model from Claude's API responses in real-time
- **Fallback Behavior**: If model detection fails, it defaults to "claude-3-5-sonnet" for cost calculations

**Why This Matters:**
- Your configuration might specify Opus, but Claude might use Sonnet for simpler tasks
- Accurate cost tracking requires knowing the actual model used, not just your preference
- Budget management and token usage calculations depend on correct model identification

**Example Status Display:**
```
║  Status   Name                Model      Duration  Overall  Tokens   Budget
║  ✅        analyze-code        35sonnet   2m15s     45.2K    2.1K     85% used
║  🏃        optimize-perf       opus4      1m30s     12.8K    800      45% used
```

This transparency helps you understand your actual AI spend and make informed decisions about model usage.

## Expected questions

### 1. Do I have to use /commands?
No. You can just put your string query (prompt) and it works the same.
It does seem to be a best practice though to version controlled `/commands`.

### 2. Does this replace using Claude command directly?
No. At least not yet fully.
As we primarily using structured commands, internally we see 80%+ of our usage through Zen.
Ad hoc questions or validating if a command is working as expected for now is better through Claude directly.

### 3. What does this assume?
- You have claude code installed, authenticated, and configured already.

## Known Issues and Solutions

### Windows Permission Errors (Issue #1320)
**Problem:** Commands may fail with "This command requires approval" on Windows.

**Solution:** Zen now automatically detects Windows and uses `bypassPermissions` mode. If you still experience issues, see [Issue #1320 Documentation](../docs/issues/ISSUE_1320_ZEN_PERMISSION_ERROR_FIX.md).

### Platform-Specific Behavior
Zen automatically adjusts permission modes based on your platform:
- **Windows**: Uses `bypassPermissions` to avoid approval prompts
- **Mac/Linux**: Uses standard `bypassPermissions` mode

For more details, see [Cross-Platform Compatibility](docs/CROSS_PLATFORM_COMPATIBILITY.md).
- All existing config stays the same unless expressly defined in Zen.
- - e.g. if your have your model set to Opus and don't change it per command in Zen, then all
Claude Zen instances use Opus.

### 4. How do I know if it's working?
- Each command returns fairly clear overall statuses.
- Budget states etc. are logged.
- You can also see the duration and token usage.
- By default, each command outputs a truncated version of the output to the console.
- You can optionaly choose to save a report of all output to .json
- Our usage is heavily integrated with github, we use git issues as the visual output 
and notification system for most work. This means regardless of where Zen is running
you can see the results wherever you access git. This is as easy as adding `gh` instructions (the cli + token assumed to be present) to your commands.

### 5. Data privacy?
At this moment no data is collected. Our intent is to add an optional system where non-PII usage data is sent to Netra for exclusively aggregated metadata level use to help make our spend management system better. (So you can get more from your AI spend!)

## 6. What about the UI/UX?
There is a time and a place for wanting to have multiple windows and git trees open.
Zen's intent is the opposite: make running `n` code clis more peaceful.
Why activate your "giga-brain" when you can run one command instead?


## Configuration

Create a JSON file with your tasks:

```json
{
  "instances": [
    {
      "name": "task-1",
      "command": "/my-command",
      "description": "What this task does"
    }
  ]
}
```

## Documentation

- [Quick Setup](docs/QUICK_SETUP.md) - Get started in minutes
- [User Guide](docs/ZEN_GUIDE.md) - Comprehensive usage guide
- [Examples](docs/EXAMPLES.md) - Common workflows and patterns
- [Pricing Strategy](docs/pricing_strategy.md) - Token calculation and cost transparency
- [Changelog](docs/changelog.md) - Version history and changes

## Zen --help
```zen --help```
yields:
```
usage: zen [-h] [--workspace WORKSPACE] [--config CONFIG] [--dry-run] [--list-commands] [--inspect-command INSPECT_COMMAND]
           [--output-format {json,stream-json}] [--timeout TIMEOUT] [--max-console-lines MAX_CONSOLE_LINES] [--quiet]
           [--startup-delay STARTUP_DELAY] [--max-line-length MAX_LINE_LENGTH] [--status-report-interval STATUS_REPORT_INTERVAL]
           [--start-at START_AT] [--use-cloud-sql] [--overall-token-budget OVERALL_TOKEN_BUDGET] [--command-budget COMMAND_BUDGET]
           [--budget-enforcement-mode {warn,block}] [--disable-budget-visuals]

Claude Code Instance Orchestrator

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Workspace directory (default: current directory)
  --config CONFIG       Custom instance configuration file
  --dry-run             Show commands without running
  --list-commands       List all available slash commands and exit
  --inspect-command INSPECT_COMMAND
                        Inspect a specific slash command and exit
  --output-format {json,stream-json}
                        Output format for Claude instances (default: stream-json)
  --timeout TIMEOUT     Timeout in seconds for each instance (default: 10000)
  --max-console-lines MAX_CONSOLE_LINES
                        Maximum recent lines to show per instance on console (default: 5)
  --quiet               Minimize console output, show only errors and final summaries
  --startup-delay STARTUP_DELAY
                        Delay in seconds between launching each instance (default: 5.0)
  --max-line-length MAX_LINE_LENGTH
                        Maximum characters per line in console output (default: 500)
  --status-report-interval STATUS_REPORT_INTERVAL
                        Seconds between rolling status reports (default: 5)
  --start-at START_AT   Schedule orchestration to start at specific time. Examples: '2h' (2 hours from now), '30m' (30 minutes),
                        '14:30' (2:30 PM today), '1am' (1 AM today/tomorrow)
  --use-cloud-sql       Save metrics to CloudSQL database (NetraOptimizer integration)
  --overall-token-budget OVERALL_TOKEN_BUDGET
                        Global token budget for the entire session.
  --command-budget COMMAND_BUDGET
                        Per-command budget in format: '/command_name=limit'. Can be used multiple times.
  --budget-enforcement-mode {warn,block}
                        Action to take when a budget is exceeded: 'warn' (log and continue) or 'block' (prevent new instances).
  --disable-budget-visuals
                        Disable budget visualization in status reports

```

## Requirements

- Python 3.8+
- Claude Code CLI
- Dependencies in requirements.txt

## Logging and Output

- **Console Output**: All logs and execution results are displayed in the console
- **No File Logging**: ZEN does not write logs to files by default
- **Capturing Output**: To save execution logs, use output redirection:
  ```bash
  python zen_orchestrator.py --config tasks.json > execution.log 2>&1
  ```

## Testing

```bash
cd tests/
python test_runner.py
```

## License

See [LICENSE](../LICENSE) in the project root.

## Quickstart
# Quick Start Guide

## Installation Methods

### 1. Via pip (Recommended)
```bash
pip install zen-orchestrator
```

### 2. Via pipx (for isolated installation)
```bash
pipx install zen-orchestrator
```

### 3. Via Homebrew (macOS/Linux)
```bash
brew tap netra-systems/tools
brew install zen
```

### 4. Via Docker
```bash
docker pull netrasystems/zen:latest
docker run --rm netrasystems/zen --help
```

### 5. From source
```bash
git clone https://github.com/netra-systems/zen.git
cd zen
pip install -e .
```

## Basic Usage

### 1. Direct Command Execution (NEW)
Execute commands directly without config files:
```bash
# Execute a single command directly
zen "/help"

# Execute with custom workspace
zen "/analyze-code" --workspace ~/my-project

# Execute with custom instance name
zen "/debug-issue" --instance-name "debug-session"

# Execute with session continuity
zen "/optimize-performance" --session-id "perf-session-1"

# Execute with history management
zen "/generate-docs" --clear-history --compact-history

# Execute with token budget
zen "/complex-analysis" --overall-token-budget 5000
```

**Direct Command Features:**
- **No Config Required**: Skip JSON file creation for simple tasks
- **Custom Options**: Set instance name, description, session ID
- **History Control**: Clear or compact history before execution
- **Budget Integration**: Works with all existing budget features

### 2. Quick Test
```bash
# List available commands
zen --list-commands

# Dry run to see what would be executed
zen --dry-run

# Run with default configuration
zen
```

### 3. Custom Configuration
Create a `config.json` file:
```json
{
  "instances": [
    {
      "name": "analyzer",
      "prompt": "Analyze the codebase and provide insights"
    },
    {
      "name": "optimizer",
      "prompt": "Optimize the performance bottlenecks"
    }
  ]
}
```

Run with configuration:
```bash
zen --config config.json
```

### 4. Workspace Management
```bash
# Use specific workspace
zen --workspace ~/projects/myapp

# With custom timeout
zen --timeout 300 --workspace ~/projects/myapp
```

### 5. Token Budget Control
```bash
# Set overall budget
zen --overall-token-budget 100000

# Set per-command budgets
zen --command-budget "/analyze=50000" --command-budget "/optimize=30000"

# Budget enforcement modes
zen --budget-enforcement-mode block  # Stop when exceeded
zen --budget-enforcement-mode warn   # Warn but continue
```

### 6. Scheduled Execution
```bash
# Start in 2 hours
zen --start-at "2h"

# Start at specific time
zen --start-at "14:30"  # 2:30 PM today
zen --start-at "1am"    # 1 AM tomorrow
```

### 7. Execution Mode Precedence
Zen supports three execution modes with clear precedence rules:

1. **Direct Command** (Highest Priority)
   ```bash
   zen "/analyze-code"  # Executes direct command
   ```

2. **Config File** (Medium Priority)
   ```bash
   zen --config my-config.json  # Uses config file
   ```

3. **Default Instances** (Lowest Priority)
   ```bash
   zen  # Uses built-in default commands
   ```

**Mixed Usage:**
```bash
# Direct command overrides config file
zen "/direct-cmd" --config my-config.json  # Executes /direct-cmd, ignores config

# Config file overrides defaults
zen --config my-config.json  # Uses config, ignores defaults
```

## Advanced Features

### Parallel Execution Control
```bash
# Control startup delay between instances
zen --startup-delay 2.0  # 2 seconds between launches

# Limit console output
zen --max-console-lines 10
zen --max-line-length 200
```

### Output Formats
```bash
# JSON output
zen --output-format json

# Stream JSON (default)
zen --output-format stream-json
```

### Quiet Mode
```bash
# Minimal output - only errors and summary
zen --quiet
```

### Status Reporting
```bash
# Change status report interval
zen --status-report-interval 30  # Every 30 seconds
```

## Integration with Claude Code

Zen works seamlessly with Claude Code workspaces:

1. Navigate to your Claude Code project:
```bash
cd ~/projects/my-claude-project
```

2. Run Zen to orchestrate multiple instances:
```bash
zen --config zen-config.json
```

3. Monitor the execution:
- Real-time status updates
- Token usage tracking
- Progress visualization

## Environment Variables

```bash
# Set default workspace
export ZEN_WORKSPACE="~/projects"

# Set default config
export ZEN_CONFIG="~/configs/zen-default.json"

# Enable debug logging
export ZEN_DEBUG="true"
```

## Troubleshooting

### Command not found

#### If using pipx (recommended):
```bash
# Ensure PATH is configured
pipx ensurepath

# Restart terminal, then verify
zen --version
```

#### If using pip (not recommended):
```bash
# Find where pip installed zen
pip show zen-orchestrator

# Use Python module directly (always works)
python -m zen_orchestrator --help

# Or manually add to PATH:
# Windows: Add %APPDATA%\Python\Python3X\Scripts to PATH
# macOS/Linux: Add ~/.local/bin to PATH
export PATH="$HOME/.local/bin:$PATH"  # Add to ~/.bashrc or ~/.zshrc
```

### Permission denied
```bash
# Make sure scripts are executable
chmod +x $(which zen)
```

### Module not found
```bash
# Reinstall with dependencies
pip install --force-reinstall zen-orchestrator
```

## Getting Help

```bash
# Show help
zen --help

# Inspect specific command
zen --inspect-command /analyze

# Visit documentation
# https://github.com/netra-systems/zen
```

## Example Configurations

See the included example files:
- `minimal_config.json` - Basic setup
- `config_example.json` - Standard configuration
- `netra_apex_tool_example.json` - Advanced integration

## Support

- GitHub Issues: https://github.com/netra-systems/zen/issues
- Documentation: https://github.com/netra-systems/zen/wiki