# Token Budget System - Technical Implementation Guide

> **Purpose:** Technical reference for maintainers and developers
> **Focus:** Implementation details, code patterns, and integration mechanics
> **Last Updated:** 2025-09-16

## 1. Implementation Architecture

### 1.1 Module Structure

```python
# File: scripts/token_budget/models.py
# Lines: 18 | Complexity: LOW | Dependencies: None

class CommandBudgetInfo:
    """
    Simple container for command budget tracking.
    No @dataclass to avoid import complexity.
    """
    def __init__(self, limit: int):
        self.limit = limit      # Maximum tokens allowed
        self.used = 0          # Tokens consumed so far

    @property
    def remaining(self) -> int:
        return self.limit - self.used

    @property
    def percentage(self) -> float:
        return (self.used / self.limit * 100) if self.limit > 0 else 0
```

### 1.2 Core Manager Implementation

```python
# File: scripts/token_budget/budget_manager.py
# Lines: 38 | Complexity: MEDIUM | Dependencies: models.py

class TokenBudgetManager:
    """
    Central budget management with two-tier tracking:
    1. Overall session budget (global limit)
    2. Per-command budgets (individual limits)
    """

    def __init__(self, overall_budget: Optional[int] = None,
                 enforcement_mode: str = "warn"):
        self.overall_budget = overall_budget
        self.enforcement_mode = enforcement_mode
        self.command_budgets: Dict[str, CommandBudgetInfo] = {}
        self.total_usage: int = 0  # Cumulative across all commands

    def check_budget(self, command_name: str, estimated_tokens: int) -> bool:
        """
        Two-level validation:
        1. Check global budget won't be exceeded
        2. Check command-specific budget won't be exceeded
        Returns False if either would be violated.
        """
        # Global check
        if self.overall_budget is not None:
            if (self.total_usage + estimated_tokens) > self.overall_budget:
                return False

        # Command-specific check
        if command_name in self.command_budgets:
            command_budget = self.command_budgets[command_name]
            if (command_budget.used + estimated_tokens) > command_budget.limit:
                return False

        return True
```

### 1.3 Visualization Component

```python
# File: scripts/token_budget/visualization.py
# Lines: 21 | Complexity: LOW | Dependencies: None

def render_progress_bar(used: int, total: int, width: int = 20) -> str:
    """
    ASCII progress bar with ANSI color codes.

    Visual states:
    - Green:  [████████░░░░░░░░░░░░] < 70%
    - Yellow: [██████████████░░░░░░] 70-90%
    - Red:    [██████████████████░░] > 90%
    """
    if total == 0:
        return "[NO BUDGET SET]"

    percentage = min(used / total, 1.0)
    filled_width = int(percentage * width)

    # Unicode box drawing for smooth appearance
    bar = '█' * filled_width + '░' * (width - filled_width)

    # ANSI escape sequences for terminal colors
    color_map = {
        'green': '\033[92m',   # < 70%
        'yellow': '\033[93m',  # 70-90%
        'red': '\033[91m',     # > 90%
        'reset': '\033[0m'
    }

    if percentage > 0.9:
        color = color_map['red']
    elif percentage > 0.7:
        color = color_map['yellow']
    else:
        color = color_map['green']

    return f"[{color}{bar}{color_map['reset']}] {percentage:.0%}"
```

---

## 2. Orchestrator Integration

### 2.1 Import Path Resolution

```python
# File: claude-instance-orchestrator.py
# Lines: 37-40

# Critical: Add parent directory to Python path for local imports
# This ensures token_budget package is discoverable
sys.path.insert(0, str(Path(__file__).parent))

# Now safe to import
from token_budget.budget_manager import TokenBudgetManager
from token_budget.visualization import render_progress_bar
```

**Why sys.path manipulation?**
- Package lives alongside orchestrator script
- Not installed as proper Python package
- Avoids complex package installation requirements

### 2.2 Manager Initialization

```python
# File: claude-instance-orchestrator.py
# Lines: 124-127

# Conditional initialization - only create if needed
self.budget_manager = TokenBudgetManager(
    overall_budget=overall_token_budget,
    enforcement_mode=budget_enforcement_mode
) if overall_token_budget or budget_enforcement_mode != "warn" else None

# Separate flag for visual display control
self.enable_budget_visuals = enable_budget_visuals
```

**Design Decision:** Manager is None when not needed, avoiding unnecessary overhead.

### 2.3 Delta Token Tracking

```python
# File: claude-instance-orchestrator.py
# Lines: 95, 821-829

# In InstanceStatus dataclass:
_last_known_total_tokens: int = 0  # Track last known state

# In _update_budget_tracking method:
def _update_budget_tracking(self, status: InstanceStatus, instance_name: str):
    """
    Critical: Track DELTA tokens, not cumulative.
    Streaming updates give us cumulative totals.
    """
    if self.budget_manager and status.total_tokens > status._last_known_total_tokens:
        # Calculate the delta
        new_tokens = status.total_tokens - status._last_known_total_tokens

        # Extract base command for budget key matching
        command = self.instances[instance_name].command
        base_command = command.split()[0] if command else command

        # Record only the delta
        self.budget_manager.record_usage(base_command, new_tokens)

        # Update tracking point
        status._last_known_total_tokens = status.total_tokens
```

**Why Delta Tracking?**
- Claude's streaming output provides cumulative totals
- Each update includes all tokens from session start
- Without delta tracking, we'd count tokens multiple times

### 2.4 Pre-execution Budget Validation

```python
# File: claude-instance-orchestrator.py
# Lines: 309-322

# Before launching instance, check budget
if self.budget_manager:
    # V1: Simple estimation strategy
    estimated_tokens = config.max_tokens_per_command or 1000

    # Critical: Extract base command for budget matching
    base_command = config.command.split()[0] if config.command else config.command

    if not self.budget_manager.check_budget(base_command, estimated_tokens):
        message = f"Budget exceeded for instance {name}. Skipping."

        if self.budget_manager.enforcement_mode == "block":
            # Hard stop - prevent execution
            logger.error(f"BLOCK MODE: {message}")
            status.status = "failed"
            status.error = "Blocked by budget limit"
            return False  # Don't launch instance
        else:  # warn mode
            # Log but continue
            logger.warning(message)
```

**Base Command Extraction:**
- Input: `/test --real-services --category integration`
- Extracted: `/test`
- Ensures budgets apply regardless of arguments

---

## 3. CLI Integration

### 3.1 Argument Definition

```python
# File: claude-instance-orchestrator.py
# Lines: 1463-1470

# Overall session budget
parser.add_argument(
    "--overall-token-budget",
    type=int,
    default=None,
    help="Global token budget for the entire session."
)

# Per-command budgets (repeatable)
parser.add_argument(
    "--command-budget",
    action='append',  # Allows multiple uses
    help="Per-command budget in format: '/command_name=limit'. Can be used multiple times."
)

# Enforcement strategy
parser.add_argument(
    "--budget-enforcement-mode",
    choices=["warn", "block"],
    default="warn",
    help="Action to take when a budget is exceeded: 'warn' (log and continue) or 'block' (prevent new instances)."
)

# Visual control
parser.add_argument(
    "--disable-budget-visuals",
    action="store_true",
    help="Disable budget visualization in status reports"
)
```

### 3.2 Command Budget Parsing

```python
# File: claude-instance-orchestrator.py
# Lines: 1512-1520

# Process per-command budgets after orchestrator creation
if orchestrator.budget_manager and args.command_budget:
    for budget_str in args.command_budget:
        try:
            # Expected format: "/command=1000"
            command_name, limit = budget_str.split('=', 1)

            # Strip whitespace and set budget
            orchestrator.budget_manager.set_command_budget(
                command_name.strip(),
                int(limit)
            )

            logger.info(f"Set budget for {command_name.strip()} to {limit} tokens.")

        except ValueError:
            # Handle malformed input gracefully
            logger.error(f"Invalid format for --command-budget: '{budget_str}'. Use '/command=limit'.")
```

---

## 4. Status Report Integration

### 4.1 Budget Visualization in Reports

```python
# File: claude-instance-orchestrator.py
# Lines: 750-766

# In print_status_report method
if self.budget_manager and self.enable_budget_visuals:
    bm = self.budget_manager

    # Overall budget display
    overall_budget = bm.overall_budget or 0
    overall_bar = render_progress_bar(bm.total_usage, overall_budget)
    used_formatted = self._format_tokens(bm.total_usage)
    total_formatted = self._format_tokens(overall_budget)

    print(f"║ BUDGET STATUS")
    print(f"║ Overall: {overall_bar} {used_formatted}/{total_formatted}")

    # Command-specific budgets
    if bm.command_budgets:
        print(f"║ Command Budgets:")
        for name, budget_info in bm.command_budgets.items():
            bar = render_progress_bar(budget_info.used, budget_info.limit)
            print(f"║   {name:<30} {bar}")
```

### 4.2 Token Formatting Helper

```python
def _format_tokens(self, count: int) -> str:
    """Format token counts with K/M suffixes."""
    if count >= 1_000_000:
        return f"{count/1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count/1_000:.1f}K"
    else:
        return str(count)
```

---

## 5. Critical Implementation Patterns

### 5.1 Lazy Initialization Pattern

```python
# Only create manager if budget features are used
self.budget_manager = TokenBudgetManager(...) if overall_token_budget else None

# All usage sites check for None
if self.budget_manager:
    # Perform budget operations
```

**Benefits:**
- Zero overhead when feature not used
- Clean feature flag behavior
- Simplifies testing (can run without budgets)

### 5.2 Command Normalization Pattern

```python
# Always extract base command for consistency
base_command = config.command.split()[0] if config.command else config.command

# Use normalized command as budget key
self.budget_manager.check_budget(base_command, estimated_tokens)
self.budget_manager.record_usage(base_command, new_tokens)
```

**Benefits:**
- Budget rules work regardless of arguments
- Consistent tracking across command variations
- Simple string matching logic

### 5.3 Delta Tracking Pattern

```python
# Track last known state per instance
_last_known_total_tokens: int = 0

# Calculate and record only the difference
if status.total_tokens > status._last_known_total_tokens:
    delta = status.total_tokens - status._last_known_total_tokens
    record_usage(delta)  # Not cumulative total
    status._last_known_total_tokens = status.total_tokens
```

**Benefits:**
- Accurate token accounting
- Works with streaming updates
- No double-counting

---

## 6. Testing Strategy

### 6.1 Manual Test Commands

```bash
# Test import resolution
python3 -c "from scripts.token_budget.budget_manager import TokenBudgetManager; print('Import successful')"

# Test CLI parsing
python3 scripts/claude-instance-orchestrator.py --help | grep -A10 "token-budget"

# Test budget initialization
python3 scripts/claude-instance-orchestrator.py \
    --dry-run \
    --overall-token-budget 5000 \
    --command-budget "/test=1000" 2>&1 | grep "Set budget"

# Test visualization
python3 -c "
from scripts.token_budget.visualization import render_progress_bar
print(render_progress_bar(500, 1000))  # Should show 50% green
print(render_progress_bar(800, 1000))  # Should show 80% yellow
print(render_progress_bar(950, 1000))  # Should show 95% red
"
```

### 6.2 Integration Test Points

1. **Argument Parsing**
   - Verify `args.overall_token_budget` populated
   - Verify `args.command_budget` list created
   - Test malformed budget strings handled

2. **Manager Creation**
   - Confirm manager is None without budget args
   - Confirm manager created with budget args
   - Verify enforcement mode propagated

3. **Budget Enforcement**
   - Test warn mode logs but continues
   - Test block mode prevents execution
   - Verify pre-execution check called

4. **Token Tracking**
   - Confirm delta calculation correct
   - Verify base command extraction
   - Test cumulative tracking accurate

---

## 7. Common Integration Issues

### 7.1 Import Errors

**Problem:** `ModuleNotFoundError: No module named 'token_budget'`

**Solution:**
```python
# Ensure this line exists before imports
sys.path.insert(0, str(Path(__file__).parent))
```

### 7.2 Budget Not Enforcing

**Problem:** Commands execute despite exceeding budget

**Checklist:**
1. Verify `--budget-enforcement-mode block` is set
2. Confirm budget manager initialized (not None)
3. Check base command extraction matches budget key
4. Verify `check_budget()` return value is honored

### 7.3 Token Counts Wrong

**Problem:** Token usage seems inflated or inaccurate

**Debug Steps:**
```python
# Add logging to delta tracking
logger.debug(f"Token update: total={status.total_tokens}, last={status._last_known_total_tokens}, delta={new_tokens}")
```

---

## 8. Performance Considerations

### 8.1 Memory Usage

- Each `CommandBudgetInfo`: ~48 bytes
- Budget manager overhead: ~200 bytes + dict overhead
- 100 commands tracked: ~5KB total memory

**Verdict:** Negligible memory impact

### 8.2 CPU Usage

- Budget check: O(1) dictionary lookup
- Delta calculation: Simple arithmetic
- Progress bar rendering: ~100 CPU cycles

**Verdict:** Negligible CPU impact

### 8.3 I/O Impact

- No file I/O required
- No network calls
- Terminal output only during status reports

**Verdict:** Zero I/O overhead

---

## 9. Future Enhancement Paths

### 9.1 Token Prediction (V2)

```python
# Potential enhancement
def estimate_tokens_for_command(command: str, history_db: Database) -> int:
    """Use historical data to predict token usage."""
    similar_runs = history_db.query_similar_commands(command)
    return percentile(similar_runs.token_usage, 75)  # 75th percentile
```

### 9.2 Budget Profiles (V2)

```yaml
# budget-profiles.yaml
profiles:
  testing:
    overall: 5000
    commands:
      /test: 2000
      /analyze: 1000

  production:
    overall: 50000
    commands:
      /deploy: 10000
      /monitor: 5000
```

### 9.3 Dynamic Adjustment (V3)

```python
class AdaptiveBudgetManager(TokenBudgetManager):
    """Auto-adjust budgets based on usage patterns."""

    def auto_adjust(self, history: List[ExecutionRecord]):
        """Dynamically adjust limits based on historical usage."""
        for command in self.command_budgets:
            recent_usage = self.get_recent_usage(command, history)
            suggested_limit = self.calculate_optimal_limit(recent_usage)
            self.adjust_limit(command, suggested_limit)
```

---

## 10. Code Maintenance Guidelines

### 10.1 Adding New Features

1. **Keep it simple** - Avoid complex abstractions
2. **Test imports first** - Ensure path resolution works
3. **Document delta logic** - Token tracking is critical
4. **Preserve lazy init** - Don't create manager unnecessarily

### 10.2 Debugging Checklist

```python
# Add debug logging at key points
logger.debug(f"Budget manager initialized: {self.budget_manager is not None}")
logger.debug(f"Checking budget for {base_command}: {estimated_tokens} tokens")
logger.debug(f"Token delta: {new_tokens} (total: {status.total_tokens})")
logger.debug(f"Budget state: {self.budget_manager.total_usage}/{self.budget_manager.overall_budget}")
```

### 10.3 Testing Changes

```bash
# Always test these scenarios
1. No budget arguments (manager should be None)
2. Overall budget only
3. Command budgets only
4. Combined budgets
5. Warn mode (default)
6. Block mode
7. Visual display
8. Malformed input handling
```

---

## Conclusion

The Token Budget System demonstrates how effective simplicity can be:
- **78 lines** of core implementation code
- **~15 lines** of integration changes
- **Zero** external dependencies
- **Full** functionality delivery

The implementation prioritizes maintainability and clarity over complex abstractions, resulting in a system that is easy to understand, modify, and extend.

---

*Technical implementation guide compiled from working code analysis and integration patterns.*