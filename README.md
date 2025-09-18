# Zen

Zen runs multiple Code CLI instances for peaceful parallel task execution.

## What is Zen?

Zen allows you to:
- Run multiple headless Claude Code CLI instances simultaneously.
- Calm unified results (status, time, token usage)
- Relax **"5-hour limit reached"** lockout fears with easy token budget limits
- Get more value out of your Claude MAX subscription
with scheduling features. (`--run-at "2am"`) 
- Learn more about how Claude Code uses tools and other inner workings
- Control usage and budget for groups of work or per command

Example portion of status report:
```
╔═══ STATUS REPORT [14:25:10] ═══╗
║ Total: 5 instances
║ Running: 3, Completed: 2, Failed: 0
║ Tokens: 32.1K total | Tools: 15
║ 💰 Cost: $0.0642 total
║
║ TOKEN BUDGET STATUS
║ Overall: [████████████----] 75% 32.1K/43.0K
║
║  Status   Name                    Duration  Tokens
║  ──────── ─────────────────        ───────  ──────
║  ✅        security-reviewer      2m15s     8.5K
║  ✅        performance-analyzer   1m42s     7.2K
║  🏃        architecture-reviewer  1m18s     6.5K
║  🏃        test-coverage-analyst  0m45s     4.8K
║  ⏳        quality-synthesizer    queued    0K
╚════════════════════════════════════════════╝
```
Here you can see we are running 5 instances of claude.
- 2 have completed
- 2 are running
- 1 is scheduled

## Inspiration and background
While developing Netra Apex (commercial product)
our team has been running 100s of parallel claude code instances.
During that process we got annoyed at the "cognitive overhead"
of each having 10s of terminals open per machine and scrolling mountains of text.
Did the `/command` work or not?

What started as a simple way to make that process more peaceful turned into something we believe will be useful to the community.

Further, as usage limits become more restrictive, getting up at odd hours just to feed the beast got old fast. So we added scheduling to run it at pre-defined times.

Surprisingly, the duration that a command ran and it's presumed difficulty, often had little correlation with actual token usage.
"Simple" git operations would sometimes eat 10x as many as complex issue resolution commands.

The market is moving quickly, codex is getting better and other Code CLIs are coming. How effective a code factory is matters. This V1 alpha is just the start of codifying code CLI dev practices and progressing from alchemy to engineering.

For more power, try Zen with Netra Apex for the most effective usage and control of business AI spend.

## Limitations

### Budget Enforcement Behavior

**Important:**

- **Local Monitoring Only**: Budgets defined in `json` configs or command-line flags are tracked locally by Zen.
Zen cannot prevent the underlying CLI from consuming tokens beyond the limit in some cases.
For example if a request is made when it is under budget, that single request may exceed the budget. In `block` mode the *next* request will be stopped.
- **Budget Exceeded Behavior**:
  - `warn` mode: Zen logs warnings but continues execution
  - `block` mode: Zen prevents running new instances or halts in progress commands, depending on the nature of the budget config.
- **Token Counting**: Budget calculations are based on estimates and may not match exact billing from Claude/Codex

### Target Audience and Use Cases

Zen is designed for internal developer productivity and automation workflows and is *not* suitable for all use cases.

It is generally expected that you already familiar with claude code
in order to get the most value out of Zen.

**✅ Supported Use Cases:**
- Internal development workflows and automation
- Parallel execution of development tasks
- CI/CD integration for development teams
- Budget and cost control for Claude

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
# From PyPI
pipx install netra-zen

# For local development (editable mode)
cd zen/
pipx install --editable .

# Verify installation
zen --help
```

### Alternative: pip (Manual PATH Configuration Required)

⚠️ **Warning:** Using pip directly often results in PATH issues. We strongly recommend pipx instead.

```bash
pip install netra-zen

# If 'zen' command not found, you'll need to:
# Option 1: Use Python module directly
python -m zen_orchestrator --help

# Option 2: Manually add to PATH (see Troubleshooting)
```

## Understanding the Model Column in Status Reports

### Model Column Behavior

The **Model** column in Zen's status display shows the **actual model used** by Claude Code for each API response, not necessarily the model you configured in your settings.

**Key Points:**
- **Cost Tracking Value**: Knowing the actual model is critical for accurate cost calculation since different models have vastly different pricing (e.g., Opus costs 5x more than Sonnet)
- **Dynamic Detection**: Zen automatically detects the model from Claude's API responses in real-time

**Example Status Display:**
```
║  Status   Name                Model      Duration  Overall  Tokens   Budget
║  ✅        analyze-code        35sonnet   2m15s     45.2K    2.1K     85% used
║  🏃        optimize-perf       opus4      1m30s     12.8K    800      45% used
```

This transparency helps you understand your actual AI spend and make informed decisions about model usage.


### Step 3: Generate with AI

1. Copy your customized prompt
2. Paste it into ChatGPT, Claude, or your preferred LLM
3. Save the generated JSON as `customer_feedback.json`
4. Run: `zen --config customer_feedback.json`

## Understanding Configuration Structure

Every Zen configuration has the same basic structure:

```json
{
  "// Description": "What this workflow accomplishes",
  "// Use Case": "When to use this configuration",

  "instances": [
    {
      "command": "/command || prompt",
      "permission_mode": "bypassPermissions", // Default
      "output_format": "stream-json", // Default
      "max_tokens_per_command": 12000, // Optional
      "allowed_tools": ["Read", "Write", "Edit", "Task"],  // Optional
      // Other optional features
    }//,
    //{
    //  next instance
    //}
    //... series of instances
  ]
}
```

### Key Configuration Elements

| Element | Purpose | Best Practice |
|---------|---------|---------------|
| `command` | Task specification | Can use existing /commands or any string literal input |
| `max_tokens_per_command` | Token budget | Allocate based on complexity |
| `allowed_tools` | Tool permissions | Grant minimal necessary tools |

For Output Truncation control: `--max-console-lines` and `--max-line-length` parameters, or redirect output to files

### Scheduling

Schedule to run later.
This helps you get the most value out of your claude max subscription.

```bash
# Start in 2 hours
zen --config my_config.json --start-at "2h"

# Start at specific time
zen --config my_config.json --start-at "14:30"

# Start in 30 minutes
zen --config my_config.json --start-at "30m"
```

## Expected questions

### 1. Do I have to use /commands?
- No. You can just put your string query (prompt) and it works the same.
- It does seem to be a best practice though to version controlled `/commands`.

### 2. Does this replace using Claude command directly?
- No. At least not yet fully.
- As we primarily using structured commands, internally we see 80%+ of our usage through Zen.
- Ad hoc questions or validating if a command is working as expected for now is better through Claude directly.

### 3. What does this assume?
- You have claude code installed, authenticated, and configured already.

### 4. How do I know if it's working?
- Each command returns fairly clear overall statuses.
- Budget states etc. are logged.
- You can also see the duration and token usage.
- By default, each command outputs a truncated version of the output to the console.
- You can optionally choose to save a report of all output to .json
- Our usage is heavily integrated with github, we use git issues as the visual output 
and notification system for most work. This means regardless of where Zen is running
you can see the results wherever you access git. This is as easy as adding `gh` instructions (the cli + token assumed to be present) to your commands.

### 5. Data privacy?
At this moment no data is collected. 
Our intent is to add an optional system where non-PII usage data is sent to Netra for exclusively aggregated metadata level use to help make our spend management system better. (So you can get more from your AI spend!)

## 6. What about the UI/UX?
There is a time and a place for wanting to have multiple windows and git trees open.
Zen's intent is the opposite: make running `n` code clis more peaceful.
Why activate your "giga-brain" when you can run one command instead?


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
  zen --config tasks.json > execution.log 2>&1
  ```

## Testing

```bash
cd tests/
python test_runner.py
```

## Basic Usage

### Command Execution
Execute commands directly without config files:
```bash
# Execute a single command directly
zen "/my-existing-claude-command"

# Execute with config (recommended usage pattern)
zen --config /my-config.json

# Execute with custom workspace
zen "/analyze-code" --workspace ~/my-project

# Execute with token budget
zen "/complex-analysis" --overall-token-budget 5000

# Execute with custom instance name
zen "/debug-issue" --instance-name "debug-session"

# Execute with session continuity
zen "/optimize-performance" --session-id "perf-session-1"

# Start in 2 hours
zen --config my_config.json --start-at "2h"

# Start at specific time
zen --config my_config.json --start-at "14:30"

```


### Quick Test
```bash
# List available commands (auto-detects workspace)
zen --list-commands

# Dry run to see what would be executed (auto-detects workspace)
zen --dry-run

# Run with default configuration (uses actual slash commands from workspace)
zen
```

### Workspace Management
```bash
# Auto-detect workspace (looks for project root with .git, .claude, etc.)
zen --dry-run

# Use specific workspace (override auto-detection)
zen --workspace ~/projects/myapp

# With custom timeout
zen --timeout 300 --workspace ~/projects/myapp
```

### Token Budget Control
```bash
# Set overall budget
zen --overall-token-budget 100000

# Set per-command budgets
zen --command-budget "/analyze=50000" --command-budget "/optimize=30000"

# Budget enforcement modes
zen --budget-enforcement-mode block  # Stop when exceeded
zen --budget-enforcement-mode warn   # Warn but continue
```

### Scheduled Execution
```bash
# Start in 2 hours
zen --start-at "2h"

# Start at specific time
zen --start-at "14:30"  # 2:30 PM today
zen --start-at "1am"    # 1 AM tomorrow
```

### Execution Mode Precedence
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

## Other Features

### Parallel Execution Control
```bash
# Control startup delay between instances
zen --startup-delay 30.0  # seconds between launches

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

### Permission denied
```bash
# Make sure scripts are executable
chmod +x $(which zen)
```

### Module not found
```bash
# Reinstall with dependencies
pip install --force-reinstall netra-zen
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

### Known Issues

**Token Budget Accuracy:**
- **Problem**: Budget calculations may not exactly match actual API billing
- **Cause**: Estimates based on local token counting vs. server-side billing
- **Workaround**: Use conservative budget limits and monitor actual usage through provider dashboards

**Configuration File Validation:**
- **Problem**: Limited validation of JSON configuration files
- **Impact**: Invalid configurations may cause runtime errors
- **Workaround**: Use `--dry-run` to validate configurations before execution

**Resource Cleanup:**
- **Problem**: Interrupted executions may leave background processes running
- **Workaround**: Monitor system processes and manually terminate if necessary
- **Planned Fix**: Improved signal handling and cleanup in future versions

## Example Configurations

See the included example files:
- `minimal_config.json` - Basic setup
- `config_example.json` - Standard configuration
- `netra_apex_tool_example.json` - Advanced integration

## Support

- GitHub Issues: https://github.com/netra-systems/zen/issues
- Documentation: https://github.com/netra-systems/zen/wiki