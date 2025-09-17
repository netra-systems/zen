# Zen User Guide

Zen runs multiple Code CLI instances for peaceful parallel task execution.

## What is Zen?

Zen allows you to:
- Run multiple Claude Code CLI instances simultaneously (Codex support coming soon)
- Calm results (status, time, token usage)
- Relax token fears with easy token budget limits

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