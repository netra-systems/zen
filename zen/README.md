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

Our intent is for Zen to remain OSS.
Commercial users who wish to may seemlessly use Zen with Netra Apex (Commercial Product) for the most effective usage and control of business AI spend.

## Expected questions

1. Do I have to use /commands?
No. You can just put your string query (prompt) and it works the same.
It does seem to be a best practice though to version controlled `/commands`.

2. Does this replace using Claude command directly?
No. At least not yet fully.
As we primarily using structured commands, internally we see 80%+ of our usage through Zen.
Ad hoc questions or validating if a command is working as expected for now is better through Claude directly.

3. What does this assume?
- You have claude code installed, authenticated, and configured already.
- All existing config stays the same unless expressly defined in Zen.
- - e.g. if your have your model set to Opus and don't change it per command in Zen, then all
Claude Zen instances use Opus.

4. How do I know if it's working?
- Each command returns fairly clear overall statuses.
- Budget states etc. are logged.
- You can also see the duration and token usage.
- By default, each command outputs a truncated version of the output to the console.
- You can optionaly choose to save a report of all output to .json
- Our usage is heavily integrated with github, we use git issues as the visual output 
and notification system for most work. This means regardless of where Zen is running
you can see the results wherever you access git. This is as easy as adding `gh` instructions (the cli + token assumed to be present) to your commands.

5. Data privacy?
At this moment no data is collected. Our intent is to add an optional system where non-PII usage data is sent to Netra for exclusively aggregated metadata level use to help make our spend management system better. (So you can get more from your AI spend!)

6. What about the UI/UX?
There is a time and a place for wanting to have multiple windows and git trees open.
Zen's intent is the opposite: make running `n` code clis more peaceful.
Why activate your "giga-brain" when you can run one command instead?

## Quick Start (TBD replaced with path command)

```bash
# Install dependencies
pip install -r requirements.txt

# Basic usage
zen --config config_example.json

# With budget control
zen --config my_config.json --overall-token-budget 50000
```

## Key Features

- **Parallel Execution**: Run multiple Claude instances simultaneously
- **Budget Management**: Token limits with cost tracking
- **Real-time Monitoring**: Live status updates with progress visualization
- **Execution Summary**: High-level results and token usage overview
- **Tool Usage Tracking**: Detailed metrics for Claude Code tool usage with token costs

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
`zen --help`
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