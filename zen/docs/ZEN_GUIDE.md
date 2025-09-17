# Zen User Guide

Zen orchestrates multiple Claude Code CLI instances for parallel task execution.

## What is Zen?

Zen allows you to:
- Run multiple Claude instances simultaneously
- Monitor token usage and costs in real-time
- Set budget limits to control spending
- View execution summaries and results

## Benefits

- **Parallel Execution**: Complete multiple tasks simultaneously
- **Budget Control**: Prevent runaway costs with token limits
- **Transparency**: Real-time visibility into token usage and costs
- **Summary Reports**: High-level execution results and token analytics

## Configuration Options

### Instance Configuration
```json
{
  "name": "instance-name",
  "command": "/slash-command",
  "description": "What this instance does",
  "output_format": "stream-json"
}
```

### Budget Management
- `--overall-token-budget`: Total token limit across all instances
- `--command-budget`: Per-command token limits
- `--budget-enforcement-mode`: "warn" or "block" on budget violations

### Output Options
- `--verbose`: Enable detailed logging
- `--timeout`: Set per-instance timeout
- `--quiet`: Minimize console output

## Examples

### Basic Multi-Task Execution
```bash
python zen_orchestrator.py --config tasks.json
```

### With Budget Controls
```bash
python zen_orchestrator.py \
  --config tasks.json \
  --overall-token-budget 100000 \
  --budget-enforcement-mode block \
  --command-budget "/analyze=20000,/refactor=30000"
```

### Automated Workflow
```bash
python zen_orchestrator.py \
  --config workflow.json \
  --timeout 600
```

## Output Format

ZEN provides real-time status reports and execution summaries including:
- Token usage statistics
- Cost breakdown
- Execution duration
- Success/failure status
- Output previews
- Tool usage details table (when tools are detected)

### Logging and Output

- **Console Output**: All logs and results are displayed in the console
- **No File Logging**: ZEN does not write logs to files by default
- **Capturing Logs**: To save logs, use output redirection:
  ```bash
  python zen_orchestrator.py --config tasks.json > zen_run.log 2>&1
  ```
- **Tool Metrics**: When Claude Code instances use tools, a detailed TOOL USAGE DETAILS table shows:
  - Tool names and usage counts
  - Token costs per tool
  - Total tool-related token consumption

## Need Detailed Analytics?

ZEN provides execution summaries only. For comprehensive token usage analytics, historical data, and advanced reporting features, consider upgrading to **Netra Apex**.

📧 Contact: hello@netrasystems.ai
🌐 Learn more: https://netrasystems.ai/

See [EXAMPLES.md](./EXAMPLES.md) for more use cases.