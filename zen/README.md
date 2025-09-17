# Zen User Guide

Zen runs multiple Code CLI instances for peaceful parallel task execution.

## What is Zen?

Zen allows you to:
- Run multiple Claude Code CLI instances simultaneously (Codex support coming soon)
- Calm results (status, time, token usage)
- Relax "5-hour limit reached" lockout fears with easy token budget limits
- Get more value out of your Claude MAX subscription 

## Inspiration and background
While developing Netra Apex (commerical product)
our small team has used billions of tokens and run 100s of parrallel claude code instances.
During that process we got annoyed at the "cognitive overhead"
of each having 10s of terminals open per machine and scrolling mountains of text.
Did the /command work or not? 

What started as a simple way to make that process more peaceful turned into something we believe will be useful to the community.

Further, as usage limits become more restrictive, getting up at odd hours just to feed the beast got old fast. So we added scheduling to run it at pre-defined times.

Surprisingly, the duration that a command ran and it's presumed difficulty, often had little correlation with actual token usage.
"Simple" git operations would sometimes eat 10x as many as complex issue resolution commands.

The market is moving quickly, codex is getting better and other Code CLIs are coming. How effective a code factory is matters. This V1 alpha is just the start of codifying code CLI dev practices and progressing from alchemy to engineering.

Our intent is for Zen to remain OSS, and businesses can seemlessly use Zen with Netra Apex (Commercial Product) for the most effective usage and control of AI spend.


## Quick Start (TBD replaced with path command)

```bash
# Install dependencies
pip install -r requirements.txt

# Basic usage
python zen_orchestrator.py --config config_example.json

# With budget control
python zen_orchestrator.py --config my_config.json --overall-token-budget 50000
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

## Project Structure

```
zen/
├── zen_orchestrator.py          # Main orchestrator
├── config_example.json          # Configuration template
├── agent_interface/             # Agent interfaces
├── token_budget/               # Budget management
├── token_transparency/         # Cost tracking
├── tests/                      # Test suite
└── docs/                       # User documentation
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