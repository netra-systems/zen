# Dollar-based Budget Support - Usage Examples

This document demonstrates the new dollar-based budget functionality added in Issue #1347.

## Overview

The Zen Orchestrator now supports both token-based and cost-based budgets, allowing you to set spending limits in USD instead of just tokens. This is particularly useful for:

- Setting realistic spending limits based on budget constraints
- Understanding the actual cost implications of AI operations
- Converting between tokens and costs for different models

## New CLI Arguments

### Cost Budget Arguments

- `--overall-cost-budget AMOUNT`: Set overall session cost budget in USD
- `--command-cost-budget /command=AMOUNT`: Set per-command cost budget in USD
- `--budget-parameter-type {tokens,cost,mixed}`: Choose budget type

## Usage Examples

### 1. Basic Cost Budget

Set a $10 overall budget for the session:

```bash
python zen_orchestrator.py --overall-cost-budget 10.00 --dry-run
```

### 2. Per-Command Cost Budgets

Set different cost budgets for different commands:

```bash
python zen_orchestrator.py \
    --overall-cost-budget 25.00 \
    --command-cost-budget "/analyze=5.00" \
    --command-cost-budget "/debug=10.00" \
    --command-cost-budget "/optimize=8.00" \
    --dry-run
```

### 3. Mixed Budget Mode

Combine token budgets and cost budgets:

```bash
python zen_orchestrator.py \
    --overall-cost-budget 15.00 \
    --command-budget "/legacy=2000" \
    --command-cost-budget "/modern=5.00" \
    --budget-parameter-type mixed \
    --dry-run
```

### 4. Cost Budget with Enforcement

Set strict cost budget with blocking enforcement:

```bash
python zen_orchestrator.py \
    --overall-cost-budget 20.00 \
    --budget-enforcement-mode block \
    --command-cost-budget "/analyze=8.00" \
    --dry-run
```

## Backward Compatibility

All existing token budget functionality continues to work exactly as before:

```bash
# Traditional token budgets still work
python zen_orchestrator.py \
    --overall-token-budget 5000 \
    --command-budget "/analyze=1000" \
    --budget-enforcement-mode warn \
    --dry-run
```

## Budget Display

The system automatically formats budgets appropriately:

- Token budgets: `"5,000 tokens"`, `"1.2K tokens"`
- Cost budgets: `"$5.0000"`, `"$12.50"`

## Cost Calculations

The system uses the integrated Claude Pricing Engine to:

1. **Convert tokens to cost**: Estimates cost based on Claude's official pricing
2. **Convert cost to tokens**: Estimates token limit for a given cost budget
3. **Track actual usage**: Records real costs when available from API responses

## Implementation Details

### Token-to-Cost Estimation

When setting cost budgets, the system estimates costs using:
- 60% input tokens, 40% output tokens (typical ratio)
- Current Claude pricing rates
- Model-specific pricing (defaults to claude-3-5-sonnet)

### Cost-to-Token Estimation

When converting cost limits to token estimates:
- Uses average of input/output pricing for the model
- Provides approximate token limits for cost budgets
- Helps with capacity planning

## Error Handling

The system provides clear error messages for:
- Invalid budget formats
- Missing pricing engine
- Budget exceeded scenarios
- Configuration conflicts

## Configuration File Support

Cost budgets can also be configured in JSON files:

```json
{
  "budget": {
    "overall_cost_budget": 25.0,
    "budget_type": "cost",
    "command_cost_budgets": {
      "/analyze": 10.0,
      "/optimize": 8.0,
      "/debug": 5.0
    }
  },
  "instances": [...]
}
```