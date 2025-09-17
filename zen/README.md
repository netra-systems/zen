# Netra Orchestrator Client

> **🏠 [← Return to Main Documentation](../docs/index.md)** | **📋 [View All Commands](../docs/COMMAND_INDEX.md)** | **📖 [Service Index](INDEX.md)**

A standalone service for orchestrating multiple Claude Code instances with advanced scheduling, monitoring, and metrics collection capabilities.

## Overview

The Netra Orchestrator Client allows you to:
- Run multiple Claude Code instances in parallel
- Schedule executions with flexible timing options
- Monitor real-time progress with status reports
- Collect comprehensive metrics and token usage data
- Save results to CloudSQL for analysis
- Handle complex slash command orchestration

## Quick Start

```bash
# Basic usage with default configuration
python claude_instance_orchestrator.py --workspace ~/my-project

# Schedule execution for later
python claude_instance_orchestrator.py --start-at "2h" --workspace ~/my-project

# Custom configuration
python claude_instance_orchestrator.py --config config_example.json --workspace ~/my-project

# CloudSQL integration
python claude_instance_orchestrator.py --use-cloud-sql --workspace ~/my-project
```

## Features

### Parallel Instance Management
- Launch multiple Claude Code instances with configurable delays
- Real-time status monitoring and progress reporting
- Automatic failure handling and timeout management

### Flexible Scheduling
- Immediate execution or scheduled start times
- Support for relative timing (2h, 30m) and absolute times (14:30, 1am)
- Countdown displays for long wait periods

### Comprehensive Metrics
- Token usage tracking (input, output, cached)
- Tool execution monitoring
- Performance analytics and duration tracking
- Cache hit rate calculations

### CloudSQL Integration
- Optional NetraOptimizer database integration
- Execution record persistence
- Batch tracking for analysis
- Cost calculation based on token usage

## Directory Structure

```
netra_orchestrator_client/
├── claude_instance_orchestrator.py    # Main orchestrator service
├── config_example.json               # Configuration template
├── README.md                         # This file
├── docs/                             # Documentation
│   ├── TESTING.md                   # Test execution guide
│   ├── claude_instance_orchestrator_enhancement_plan.md
│   ├── claude_instance_orchestrator_token_budget_codex_plan.md
│   ├── claude_orchestrator_deployment_strategy_plan.md
│   ├── README_orchestrator.md
│   ├── claude_orchestrator_modernization_summary.md
│   └── universal_cli_orchestrator_enhancement_plan.md
└── tests/                           # Test suite
    ├── test_runner.py              # Test runner script
    ├── test_claude_instance_orchestrator_commands.py
    ├── test_claude_instance_orchestrator_integration.py
    ├── test_claude_instance_orchestrator_metrics.py
    └── test_claude_instance_orchestrator_unit.py
```

## Testing

Run the complete test suite:
```bash
cd tests/
python test_runner.py
```

Run specific test categories:
```bash
python test_runner.py unit
python test_runner.py integration
python test_runner.py commands
python test_runner.py metrics
```

## Configuration

See `config_example.json` for configuration options and `docs/` for detailed documentation.

## Dependencies

- Python 3.8+
- Claude Code CLI
- Optional: NetraOptimizer for CloudSQL integration

## Service Independence

This service is designed to be completely independent from the main Netra backend and can be deployed separately. It communicates with Claude Code instances through the standard CLI interface.