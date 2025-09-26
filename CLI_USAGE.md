# Adaptive Budget Management CLI Usage

This document provides comprehensive examples of how to use the new adaptive budget management features through the zen orchestrator command line interface.

## Basic CLI Usage

### Enable Adaptive Budget Management

```bash
# Basic adaptive budget management
zen "/analyze-code" --adaptive-budget --overall-token-budget 1000

# With cost-based budgeting
zen "/debug-issue" --adaptive-budget --overall-cost-budget 5.00

# Enable with custom enforcement mode (must be "warn" for adaptive)
zen "/optimize-performance" --adaptive-budget --overall-token-budget 1500 --budget-enforcement-mode warn
```

### Checkpoint Configuration

```bash
# Standard quarter checkpoints (default: 25%, 50%, 75%, 100%)
zen "/analyze-code" --adaptive-budget --overall-token-budget 1000

# Custom checkpoint intervals for more frequent monitoring
zen "/debug-issue" --adaptive-budget --overall-token-budget 1500 \
    --checkpoint-intervals 0.2,0.4,0.6,0.8,1.0

# Fewer checkpoints for simpler monitoring
zen "/generate-docs" --adaptive-budget --overall-token-budget 800 \
    --checkpoint-intervals 0.5,1.0
```

### Restart Configuration

```bash
# Conservative restart settings (higher thresholds)
zen "/critical-analysis" --adaptive-budget --overall-token-budget 2000 \
    --restart-threshold 0.8 \
    --min-completion-probability 0.7 \
    --max-restarts 1

# Aggressive restart settings (lower thresholds, more attempts)
zen "/experimental-task" --adaptive-budget --overall-token-budget 1000 \
    --restart-threshold 0.95 \
    --min-completion-probability 0.4 \
    --max-restarts 3

# Disable restarts (adaptive monitoring only)
zen "/simple-task" --adaptive-budget --overall-token-budget 500 \
    --max-restarts 0
```

### Advanced Configuration

```bash
# Full configuration example
zen "/complex-analysis" --adaptive-budget \
    --overall-token-budget 2000 \
    --checkpoint-intervals 0.25,0.5,0.75,1.0 \
    --restart-threshold 0.85 \
    --min-completion-probability 0.6 \
    --max-restarts 2 \
    --todo-estimation-buffer 0.15 \
    --quarter-buffer 0.08

# Disable learning and context preservation (not recommended)
zen "/quick-test" --adaptive-budget --overall-token-budget 500 \
    --disable-learning \
    --disable-context-preservation
```

## Command Examples by Use Case

### Code Analysis Tasks

```bash
# Comprehensive code analysis with adaptive management
zen "/analyze-code" --adaptive-budget \
    --overall-token-budget 1500 \
    --checkpoint-intervals 0.25,0.5,0.75,1.0 \
    --restart-threshold 0.8 \
    --min-completion-probability 0.7

# Performance-focused analysis with frequent checkpoints
zen "/optimize-performance" --adaptive-budget \
    --overall-token-budget 2000 \
    --checkpoint-intervals 0.2,0.4,0.6,0.8,1.0 \
    --todo-estimation-buffer 0.2
```

### Debugging Tasks

```bash
# Debug with context preservation and learning
zen "/debug-issue" --adaptive-budget \
    --overall-token-budget 1000 \
    --restart-threshold 0.9 \
    --min-completion-probability 0.5 \
    --max-restarts 2

# Critical debugging with conservative settings
zen "/debug-production" --adaptive-budget \
    --overall-cost-budget 3.00 \
    --restart-threshold 0.75 \
    --min-completion-probability 0.8 \
    --max-restarts 1
```

### Testing and Validation

```bash
# Test suite execution with adaptive management
zen "/run-tests" --adaptive-budget \
    --overall-token-budget 800 \
    --checkpoint-intervals 0.3,0.6,1.0 \
    --restart-threshold 0.85

# Test creation with generous buffers
zen "/create-tests" --adaptive-budget \
    --overall-token-budget 1200 \
    --todo-estimation-buffer 0.25 \
    --quarter-buffer 0.1
```

### Documentation Generation

```bash
# Documentation with cost-based budgeting
zen "/generate-docs" --adaptive-budget \
    --overall-cost-budget 2.50 \
    --checkpoint-intervals 0.4,0.8,1.0 \
    --min-completion-probability 0.6

# API documentation with learning enabled
zen "/document-api" --adaptive-budget \
    --overall-token-budget 1000 \
    --restart-threshold 0.9 \
    --todo-estimation-buffer 0.15
```

## Configuration Combinations

### Conservative (High Reliability)

```bash
zen "/production-task" --adaptive-budget \
    --overall-token-budget 1500 \
    --restart-threshold 0.7 \
    --min-completion-probability 0.8 \
    --max-restarts 1 \
    --checkpoint-intervals 0.25,0.5,0.75,1.0
```

### Balanced (Recommended Default)

```bash
zen "/standard-task" --adaptive-budget \
    --overall-token-budget 1000 \
    --restart-threshold 0.85 \
    --min-completion-probability 0.6 \
    --max-restarts 2 \
    --checkpoint-intervals 0.25,0.5,0.75,1.0
```

### Aggressive (Maximum Efficiency)

```bash
zen "/experimental-task" --adaptive-budget \
    --overall-token-budget 1000 \
    --restart-threshold 0.95 \
    --min-completion-probability 0.4 \
    --max-restarts 3 \
    --checkpoint-intervals 0.2,0.4,0.6,0.8,1.0
```

## Block Mode Override

**Important**: Block enforcement mode automatically disables adaptive features:

```bash
# This will use standard budget management (adaptive disabled)
zen "/critical-task" --adaptive-budget \
    --overall-token-budget 1000 \
    --budget-enforcement-mode block

# Warning will be logged: "Block enforcement mode supersedes adaptive budget management"
```

## Monitoring and Status

### Check Adaptive Status

```bash
# Run with adaptive features and check status
zen "/analyze-code" --adaptive-budget --overall-token-budget 1000 --dry-run

# This will show:
# 🚀 ADAPTIVE BUDGET MANAGER initialized with 1000 tokens budget
#    Checkpoints: [0.25, 0.5, 0.75, 1.0]
#    Restart threshold: 0.9, Min completion prob: 0.5
```

### Budget Visuals

```bash
# Enable budget visualization (default)
zen "/analyze-code" --adaptive-budget --overall-token-budget 1000

# Disable budget visuals for cleaner output
zen "/analyze-code" --adaptive-budget --overall-token-budget 1000 --disable-budget-visuals
```

## Error Handling and Fallbacks

### Graceful Fallback

When adaptive features are not available or fail, the system gracefully falls back to standard budget management:

```bash
# Even if adaptive components fail, standard budgeting continues
zen "/analyze-code" --adaptive-budget --overall-token-budget 1000

# Will log: "🔶 Adaptive budget requested but not available, falling back to standard budget management"
```

### Configuration Validation

The system validates configurations and provides helpful warnings:

```bash
# Invalid checkpoint intervals
zen "/test" --adaptive-budget --checkpoint-intervals "invalid,format"
# Warning: "Invalid checkpoint intervals: invalid,format, using defaults"

# Incompatible settings
zen "/test" --adaptive-budget --budget-enforcement-mode block
# Warning: "Block enforcement mode supersedes adaptive budget management"
```

## Complete Examples

### Development Workflow

```bash
# Code analysis with learning
zen "/analyze-code" --adaptive-budget \
    --overall-token-budget 1500 \
    --checkpoint-intervals 0.25,0.5,0.75,1.0 \
    --restart-threshold 0.85 \
    --min-completion-probability 0.6 \
    --workspace ~/my-project

# Debug issues with context preservation
zen "/debug-issue" --adaptive-budget \
    --overall-token-budget 1000 \
    --restart-threshold 0.8 \
    --max-restarts 2 \
    --workspace ~/my-project

# Run tests with monitoring
zen "/run-tests" --adaptive-budget \
    --overall-token-budget 800 \
    --checkpoint-intervals 0.5,1.0 \
    --workspace ~/my-project
```

### Production Analysis

```bash
# Conservative production analysis
zen "/analyze-performance" --adaptive-budget \
    --overall-cost-budget 5.00 \
    --restart-threshold 0.75 \
    --min-completion-probability 0.8 \
    --max-restarts 1 \
    --budget-enforcement-mode warn \
    --workspace ~/production-app
```

### Research and Exploration

```bash
# Exploratory analysis with aggressive settings
zen "/explore-codebase" --adaptive-budget \
    --overall-token-budget 2500 \
    --checkpoint-intervals 0.2,0.4,0.6,0.8,1.0 \
    --restart-threshold 0.9 \
    --min-completion-probability 0.4 \
    --max-restarts 3 \
    --todo-estimation-buffer 0.2
```

## Best Practices

### 1. Start Conservative
Begin with higher completion probability thresholds and fewer restarts:
```bash
--min-completion-probability 0.7 --max-restarts 1
```

### 2. Use Appropriate Budgets
- Simple tasks: 500-1000 tokens
- Complex analysis: 1500-2500 tokens
- Cost-based: $1-5 depending on scope

### 3. Monitor Checkpoints
Use more frequent checkpoints for critical tasks:
```bash
--checkpoint-intervals 0.2,0.4,0.6,0.8,1.0
```

### 4. Leverage Learning
Keep learning enabled unless you have specific reasons to disable it:
```bash
# Default behavior (recommended)
--adaptive-budget

# Only disable if needed
--adaptive-budget --disable-learning
```

### 5. Respect Block Mode
Never combine adaptive features with block enforcement:
```bash
# ✅ Correct
--adaptive-budget --budget-enforcement-mode warn

# ❌ Incorrect (adaptive will be disabled)
--adaptive-budget --budget-enforcement-mode block
```

## Troubleshooting

### Common Issues

1. **Adaptive features not working**
   - Check that `--budget-enforcement-mode` is set to `"warn"` (not `"block"`)
   - Ensure you have a budget specified (`--overall-token-budget` or `--overall-cost-budget`)

2. **Too many restarts**
   - Increase `--min-completion-probability` to be more conservative
   - Reduce `--max-restarts`

3. **Not enough monitoring**
   - Add more checkpoint intervals: `--checkpoint-intervals 0.2,0.4,0.6,0.8,1.0`
   - Enable detailed logging: `--log-level detailed`

4. **Budget estimation issues**
   - Increase estimation buffer: `--todo-estimation-buffer 0.2`
   - Increase quarter buffer: `--quarter-buffer 0.1`

The adaptive budget management system is designed to be robust and provide intelligent execution with automatic optimization. Start with the recommended defaults and adjust based on your specific needs and observations.