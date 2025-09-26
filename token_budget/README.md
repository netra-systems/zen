# Adaptive Budget Management System

This implementation adds adaptive budget management capabilities to the zen package, providing intelligent token/cost usage tracking with automatic task re-evaluation and redistribution across budget quarters.

## Overview

The Adaptive Budget Management system extends the existing `TokenBudgetManager` with sophisticated features for:

- **Proactive Planning**: Creates detailed todo lists before command execution
- **Quarter-based Distribution**: Divides budget into manageable quarters (25% each)
- **Safe Restart Points**: Identifies logical breakpoints to avoid work duplication
- **Dynamic Rebalancing**: Redistributes budget based on actual usage trends
- **Context Preservation**: Maintains execution context across restarts

## Architecture

### Core Components

1. **AdaptiveBudgetController** - Main orchestrator extending TokenBudgetManager
2. **ProactivePlanner** - Creates execution plans with todo breakdown
3. **QuarterManager** - Manages budget distribution across quarters
4. **SafeRestartManager** - Identifies restart points and preserves context
5. **BudgetTrendAnalyzer** - Analyzes usage patterns and predicts completion probability

### Key Features

#### Checkpoint-Based Evaluation
- Evaluates at configurable intervals (default: 25%, 50%, 75%, 100%)
- Triggers rebalancing based on actual vs estimated usage
- Considers restart only when completion probability < 50%

#### Safe Restart System
- Pre-computes safe restart points before execution
- Preserves context and lessons learned
- Prevents work duplication and state corruption

#### Block Mode Precedence
- **Critical**: Block enforcement mode supersedes all adaptive features
- Adaptive features only work with "warn" mode
- Graceful fallback to standard budget management

## Usage

### Basic Usage

```python
from token_budget import AdaptiveBudgetController

# Create adaptive controller
controller = AdaptiveBudgetController(
    total_budget=1000,
    adaptive_mode=True,
    enforcement_mode="warn",
    checkpoint_intervals=[0.25, 0.5, 0.75, 1.0]
)

# Execute command with adaptive management
result = controller.execute_adaptive_command("/analyze-code", {"focus": "performance"})
```

### Integration with Zen Orchestrator

```python
from token_budget.integration import BudgetManagerFactory, create_zen_orchestrator_integration

# Create with adaptive features
config, integration = create_zen_orchestrator_integration(
    workspace_dir=Path("/workspace"),
    overall_budget=2000,
    enforcement_mode="warn",
    adaptive_enabled=True,
    restart_threshold=0.85,
    min_completion_probability=0.6
)

# Execute commands
result = integration.execute_command("/debug-issue", {"error_log": "app.log"})
```

### Configuration Options

```python
from token_budget import AdaptiveConfig

config = AdaptiveConfig(
    enabled=True,
    min_completion_probability=0.5,
    restart_threshold=0.9,
    checkpoint_intervals=[0.25, 0.5, 0.75, 1.0],
    max_restarts=2,
    context_preservation=True,
    learn_from_mistakes=True,
    safe_restart_only=True
)
```

## CLI Integration

```bash
# Enable adaptive budget management
zen "/analyze-code" --adaptive-budget --total-budget 1000

# Custom checkpoint intervals
zen "/debug-issue" --adaptive-budget --checkpoint-intervals 0.25,0.5,0.75,1.0

# Set completion probability threshold
zen "/optimize" --adaptive-budget --min-completion-prob 0.4 --restart-threshold 0.85

# Block mode supersedes adaptive (adaptive disabled)
zen "/critical-task" --adaptive-budget --enforcement-mode block
```

## Implementation Details

### Execution Flow

1. **Pre-execution Setup**
   - Create proactive execution plan with todos
   - Generate safe restart points
   - Distribute todos across quarters

2. **Checkpoint Monitoring**
   - Monitor usage at quarter boundaries
   - Analyze trends and update estimates
   - Redistribute remaining todos if needed

3. **Restart Decision**
   - Only when completion probability < 50% AND usage > threshold
   - Find best available safe restart point
   - Capture context and lessons learned

4. **Fresh Session**
   - Apply lessons to optimize remaining work
   - Preserve completed work to avoid duplication
   - Execute with improved estimates

### Safe Restart Points

Automatically identified after:
- Read-only operations (search, analyze, research)
- Tool operations with clean completion
- Before destructive operations (write, modify, deploy)
- At dependency boundaries

### Context Preservation

Captures and preserves:
- Completed todo results
- Tool usage efficiency patterns
- Estimation accuracy lessons
- Search results and analysis findings
- Successful approach patterns

## Testing

Run the test suite to validate implementation:

```bash
python3 test_adaptive_budget.py
```

Expected output:
```
🧪 Starting Adaptive Budget Management Tests
📊 Test Results: 8 passed, 0 failed
🎉 All tests passed!
```

## Configuration Validation

The system validates configuration and provides warnings:

- Block mode incompatibility with adaptive features
- Invalid checkpoint intervals
- Missing budget specifications
- Quarter allocation issues

## Monitoring and Statistics

Get comprehensive execution statistics:

```python
stats = controller.get_execution_statistics()
print(stats)
```

Returns:
- Budget usage percentage
- Quarter statistics
- Restart history
- Trend analysis summary
- Configuration validation results

## Backward Compatibility

- Existing TokenBudgetManager functionality unchanged
- Graceful fallback when adaptive features unavailable
- No breaking changes to existing APIs
- Optional adaptive features with explicit enablement

## Files Added

- `adaptive_models.py` - Core data models
- `adaptive_controller.py` - Main adaptive controller
- `proactive_planner.py` - Todo planning and breakdown
- `quarter_manager.py` - Budget quarter management
- `safe_restart.py` - Safe restart point management
- `trend_analyzer.py` - Usage trend analysis
- `integration.py` - Integration utilities
- `test_adaptive_budget.py` - Comprehensive test suite

The implementation follows the detailed specification in `ADAPTIVE_BUDGET_STRATEGY.md` and provides a robust foundation for intelligent budget management in the zen package.