# Zen Orchestrator - Quick Start Guide

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

### 1. Quick Test
```bash
# List available commands
zen --list-commands

# Dry run to see what would be executed
zen --dry-run

# Run with default configuration
zen
```

### 2. Custom Configuration
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

### 3. Workspace Management
```bash
# Use specific workspace
zen --workspace ~/projects/myapp

# With custom timeout
zen --timeout 300 --workspace ~/projects/myapp
```

### 4. Token Budget Control
```bash
# Set overall budget
zen --overall-token-budget 100000

# Set per-command budgets
zen --command-budget "/analyze=50000" --command-budget "/optimize=30000"

# Budget enforcement modes
zen --budget-enforcement-mode block  # Stop when exceeded
zen --budget-enforcement-mode warn   # Warn but continue
```

### 5. Scheduled Execution
```bash
# Start in 2 hours
zen --start-at "2h"

# Start at specific time
zen --start-at "14:30"  # 2:30 PM today
zen --start-at "1am"    # 1 AM tomorrow
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
```bash
# If using pip installation
pip show zen-orchestrator

# If using pipx
pipx ensurepath

# Add to PATH manually
export PATH="$HOME/.local/bin:$PATH"
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
- Email: anthony.chaudhary@netrasystems.ai