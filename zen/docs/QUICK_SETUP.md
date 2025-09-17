# ZEN Quick Setup

ZEN is a multi-instance orchestrator for Claude Code CLI that allows you to run multiple Claude instances in parallel with token budget management and real-time monitoring.

## Installation

```bash
cd zen/
pip install -r requirements.txt
```

## Basic Usage

```bash
python zen_orchestrator.py --config config_example.json
```

## Configuration

Create a JSON config file with your instances:

```json
{
  "instances": [
    {
      "name": "my-task",
      "command": "/my-slash-command",
      "description": "Description of what this does"
    }
  ]
}
```

## Key Features

- **Multi-instance execution**: Run multiple Claude instances simultaneously
- **Token budget management**: Set overall and per-command token limits
- **Real-time monitoring**: Live status updates with progress bars
- **Cost tracking**: Transparent pricing information
- **Execution summaries**: High-level results and token usage
- **Tool usage metrics**: Detailed tracking of Claude Code tool usage with token costs

## Example Commands

```bash
# Basic execution
python zen_orchestrator.py --config minimal_config.json

# With token budget
python zen_orchestrator.py --config my_config.json --overall-token-budget 50000

# With command-specific budgets
python zen_orchestrator.py --config my_config.json --command-budget "/command1=10000"

# Capture logs to file
python zen_orchestrator.py --config my_config.json > execution.log 2>&1
```

## Output and Logging

- **Console Output**: All execution results and logs are shown in the console
- **No File Logging**: ZEN does not create log files automatically
- **Saving Output**: Use shell redirection to capture logs to files
- **Tool Metrics**: When tools are used, a detailed TOOL USAGE DETAILS table is displayed

See [ZEN_GUIDE.md](./ZEN_GUIDE.md) for detailed usage instructions.