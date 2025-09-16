# TOKEN BUDGET MANAGEMENT FEATURE PLAN - FINAL IMPLEMENTATION

**Last Updated:** 2025-09-16 by Third Subagent (Unbiased Reviewer)
**Status:** FINALIZED - Ready for Implementation
**Complexity:** MINIMAL - Only essential fixes included

## **CRITICAL DECISION SUMMARY**

After reviewing both subagents' analyses, the final implementation includes ONLY the absolutely necessary changes:

1. **Import Path Fixes** - Essential for runtime (both agents agreed)
2. **Token Delta Tracking** - Essential for accurate counting (simplified approach)
3. **Command Name Parsing** - Essential for budget matching (inline solution)
4. **Basic Visualization** - Keep as planned (already simple)

**REJECTED COMPLEXITY:**
- Thread safety (no concurrent access in current design)
- Complex dataclasses (use simple dicts)
- Platform compatibility checks (match existing code)
- Elaborate error handling (basic try/except sufficient)
- Test structure (get working first)

---

## **Phase 1: Foundational Infrastructure & Configuration (SIMPLIFIED)**

This phase establishes the core data structures, configuration options, and the budget management service that will track token usage.

### **Step 1: Create Project Structure and Data Models**

Create the necessary files and directories for the new budget management feature. This isolates the new logic cleanly.

1.  **Create Directory:** In the `scripts/` directory, create a new folder named `token_budget`.
2.  **Create `__init__.py`:** Inside `scripts/token_budget/`, create an empty `__init__.py` file to make it a Python package.
3.  **Create `models.py`:** Inside `scripts/token_budget/`, create a file named `models.py`.
4.  **Define Data Classes:** In `models.py`, define the following dataclasses to hold budget status information, as outlined in `claude-token-budget-plan.md`:
    ```python
    from typing import Dict, Optional

    # SIMPLIFIED: Use simple dict instead of dataclass
    class CommandBudgetInfo:
        """Tracks the budget status for a single command."""
        def __init__(self, limit: int):
            self.limit = limit
            self.used = 0

        @property
        def remaining(self) -> int:
            return self.limit - self.used

        @property
        def percentage(self) -> float:
            return (self.used / self.limit * 100) if self.limit > 0 else 0

    # NOTE: BudgetStatus dataclass REMOVED - will use simple dict instead
    ```

### **Step 2: Implement the Core `TokenBudgetManager`**

Create the central class responsible for all budget tracking and checking logic.

1.  **Create `budget_manager.py`:** Inside `scripts/token_budget/`, create a file named `budget_manager.py`.
2.  **Implement the Class:** In `budget_manager.py`, implement the `TokenBudgetManager` class. For V1, this will include overall and per-command budget tracking.
    ```python
    from .models import CommandBudgetInfo, BudgetStatus
    from typing import Dict, Optional, List

    class TokenBudgetManager:
        def __init__(self, overall_budget: Optional[int] = None, enforcement_mode: str = "warn"):
            self.overall_budget = overall_budget
            self.enforcement_mode = enforcement_mode
            self.command_budgets: Dict[str, CommandBudgetInfo] = {}
            self.total_usage: int = 0

        def set_command_budget(self, command_name: str, limit: int):
            """Sets the token budget for a specific command."""
            if command_name not in self.command_budgets:
                self.command_budgets[command_name] = CommandBudgetInfo(limit=limit)

        def record_usage(self, command_name: str, tokens: int):
            """Records token usage for a command and updates the overall total."""
            self.total_usage += tokens
            if command_name in self.command_budgets:
                self.command_budgets[command_name].used += tokens

        def check_budget(self, command_name: str, estimated_tokens: int) -> bool:
            """Checks if a command can run based on its budget and the overall budget."""
            # Check overall budget
            if self.overall_budget is not None and (self.total_usage + estimated_tokens) > self.overall_budget:
                return False

            # Check per-command budget
            if command_name in self.command_budgets:
                command_budget = self.command_budgets[command_name]
                if (command_budget.used + estimated_tokens) > command_budget.limit:
                    return False
            
            return True
        
        # Add get_budget_status() method later in visualization phase
    ```

### **Step 3: Update `InstanceConfig` with Budget Fields**

Modify the existing `InstanceConfig` in the main orchestrator script to support per-command budget settings.

1.  **Modify `claude-instance-orchestrator.py`:** Open this file.
2.  **Update `InstanceConfig` Dataclass:** Add the `max_tokens_per_command` field as specified in `claude-token-budget-plan.md`.
    ```python
    # In claude-instance-orchestrator.py
    @dataclass
    class InstanceConfig:
        command: str
        name: Optional[str] = None
        # ... existing fields ...
        max_tokens_per_command: Optional[int] = None # Add this line
        pre_commands: List[str] = None
    ```

### **Step 4: Add Global Budget Settings to the Orchestrator**

Modify the orchestrator's main class to accept global budget configurations.

1.  **Modify `ClaudeInstanceOrchestrator.__init__`:** In the same file, update the `__init__` method to accept global budget settings and initialize the `TokenBudgetManager`.
    ```python
    # In claude-instance-orchestrator.py
    # CRITICAL FIX: Use proper import path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from token_budget.budget_manager import TokenBudgetManager

    class ClaudeInstanceOrchestrator:
        def __init__(self, ...,
                     overall_token_budget: Optional[int] = None,
                     budget_enforcement_mode: str = "warn", # Add this
                     enable_budget_visuals: bool = True): # Add this
            # ... existing fields ...
            self.budget_manager = TokenBudgetManager(
                overall_budget=overall_token_budget,
                enforcement_mode=budget_enforcement_mode
            ) if overall_token_budget or budget_enforcement_mode != "warn" else None
            self.enable_budget_visuals = enable_budget_visuals
    ```

### **Step 5: Integrate CLI Arguments for Budget Control**

Allow users to configure budgets directly from the command line.

1.  **Modify `main()` function:** In `claude-instance-orchestrator.py`, find the `main` function and the `argparse.ArgumentParser` section.
2.  **Add New Arguments:** Add arguments for overall budget, per-command budgets, and enforcement mode.
    ```python
    # In main() function
    parser.add_argument("--overall-token-budget", type=int, default=None,
                       help="Global token budget for the entire session.")
    parser.add_argument("--command-budget", action='append',
                       help="Per-command budget in format: '/command_name=limit'. Can be used multiple times.")
    parser.add_argument("--budget-enforcement-mode", choices=["warn", "block"], default="warn",
                       help="Action to take when a budget is exceeded: 'warn' (log and continue) or 'block' (prevent new instances).")
    # SIMPLIFIED: Single flag instead of complex boolean action
    parser.add_argument("--disable-budget-visuals", action="store_true",
                       help="Disable budget visualization in status reports")

    # Pass these args when creating the orchestrator instance
    orchestrator = ClaudeInstanceOrchestrator(
        ...,
        overall_token_budget=args.overall_token_budget,
        budget_enforcement_mode=args.budget_enforcement_mode,
        enable_budget_visuals=not args.disable_budget_visuals
    )
    ```
3.  **Process CLI Budgets:** After creating the orchestrator, process the per-command budgets and configure the manager.
    ```python
    # In main(), after orchestrator is created and before running
    if orchestrator.budget_manager and args.command_budget:
        for budget_str in args.command_budget:
            try:
                command_name, limit = budget_str.split('=', 1)
                orchestrator.budget_manager.set_command_budget(command_name.strip(), int(limit))
                logger.info(f"Set budget for {command_name.strip()} to {limit} tokens.")
            except ValueError:
                logger.error(f"Invalid format for --command-budget: '{budget_str}'. Use '/command=limit'.")
    ```

-----

## **Phase 2: Core Logic & Enforcement (ESSENTIAL FIXES ONLY)**

This phase integrates the budget manager into the orchestrator's execution flow to enforce limits.

### **Step 6: Implement Pre-Execution Budget Validation**

Before an instance is run, check if it has sufficient budget.

1.  **Modify `run_instance`:** In `claude-instance-orchestrator.py`, update this method.
2.  **Add Budget Check:** At the beginning of `run_instance`, add a call to the `budget_manager`. For V1, we'll use a placeholder for `estimated_tokens`. A more advanced version would predict this.
    ```python
    # In ClaudeInstanceOrchestrator.run_instance
    async def run_instance(self, name: str) -> bool:
        config = self.instances[name]
        status = self.statuses[name]

        # --- PRE-EXECUTION BUDGET CHECK ---
        if self.budget_manager:
            # V1: Use a simple placeholder or the configured max. Future versions can predict.
            estimated_tokens = config.max_tokens_per_command or 1000 # Default estimate
            # CRITICAL: Use base command for budget checking
            base_command = config.command.split()[0] if config.command else config.command
            if not self.budget_manager.check_budget(base_command, estimated_tokens):
                message = f"Budget exceeded for instance {name}. Skipping."
                if self.budget_manager.enforcement_mode == "block":
                    logger.error(f"BLOCK MODE: {message}")
                    status.status = "failed"
                    status.error = "Blocked by budget limit"
                    return False
                else: # warn mode
                    logger.warning(f"WARN MODE: {message}")
        
        # ... rest of the run_instance method ...
    ```

### **Step 7: Integrate Real-time Token Usage Tracking**

Hook into the existing token parsing logic to feed real-time usage data into the `TokenBudgetManager`.

1.  **Modify `_parse_token_usage`:** In `claude-instance-orchestrator.py`, find the method that parses token usage from the output stream.
2.  **Call `record_usage`:** After parsing tokens from a line of output, record the newly parsed tokens. To avoid double-counting, track the last known token count for the instance and record the difference.
    ```python
    # CRITICAL FIX: Add delta tracking to InstanceStatus
    @dataclass
    class InstanceStatus:
        #... existing fields ...
        _last_known_total_tokens: int = 0 # Add this single field

    # SIMPLIFIED FIX: Pass instance name directly to avoid complex lookups
    def _parse_token_usage(self, line: str, status: InstanceStatus, instance_name: str):
        # ... existing parsing logic ...
        # After status.total_tokens is updated:
        if self.budget_manager and status.total_tokens > status._last_known_total_tokens:
            new_tokens = status.total_tokens - status._last_known_total_tokens
            # CRITICAL: Extract base command without arguments
            command = self.instances[instance_name].command
            base_command = command.split()[0] if command else command
            self.budget_manager.record_usage(base_command, new_tokens)
            status._last_known_total_tokens = status.total_tokens
    ```

-----

## **Phase 3: Visualization & User Feedback (KEEP SIMPLE)**

This phase implements the visual feedback (ASCII progress bars) to keep the user informed of the budget status.

### **Step 8: Create the Visualization Module**

Create a dedicated function or class to generate ASCII progress bars.

1.  **Create `visualization.py`:** Inside `scripts/token_budget/`, create a new file `visualization.py`.
2.  **Implement Renderer:** Add a function to render a progress bar.
    ```python
    # in scripts/token_budget/visualization.py
    def render_progress_bar(used: int, total: int, width: int = 20) -> str:
        """Renders an ASCII progress bar."""
        if total == 0:
            return "[NO BUDGET SET]"
        
        percentage = min(used / total, 1.0)
        filled_width = int(percentage * width)
        
        bar = '█' * filled_width + '░' * (width - filled_width)
        
        # Color coding (ANSI escape codes)
        color_start = '\033[92m' # Green
        if percentage > 0.9:
            color_start = '\033[91m' # Red
        elif percentage > 0.7:
            color_start = '\033[93m' # Yellow
        color_end = '\033[0m' # Reset
        
        return f"[{color_start}{bar}{color_end}] {percentage:.0%}"
    ```

### **Step 9: Enhance Status Reports with Budget Visuals**

Integrate the progress bars and budget data into the periodic status report.

1.  **Update `TokenBudgetManager`:** Add a `get_budget_status` method to compile all current budget data.
2.  **Modify `_print_status_report`:** In `claude-instance-orchestrator.py`, update the status report method to display the new budget section.
    ```python
    # In ClaudeInstanceOrchestrator._print_status_report
    # CRITICAL FIX: Use correct import path
    from token_budget.visualization import render_progress_bar

    async def _print_status_report(self, final: bool = False):
        # ... existing header logic ...

        # --- ADD BUDGET STATUS SECTION ---
        if self.budget_manager and self.enable_budget_visuals:
            bm = self.budget_manager
            overall_budget = bm.overall_budget or 0
            overall_bar = render_progress_bar(bm.total_usage, overall_budget)
            used_formatted = self._format_tokens(bm.total_usage)
            total_formatted = self._format_tokens(overall_budget)

            print(f"║")
            print(f"╠═══ TOKEN BUDGET STATUS ═══╣")
            print(f"║ Overall: {overall_bar} {used_formatted}/{total_formatted}")

            if bm.command_budgets:
                print(f"║ Command Budgets:")
                for name, budget_info in bm.command_budgets.items():
                    bar = render_progress_bar(budget_info.used, budget_info.limit)
                    print(f"║   {name:<30} {bar}")
            print(f"║")

        # ... rest of the existing report ...
    ```

-----

## **Phase 4: Minimal Validation (SIMPLIFIED)**

This final phase ensures the new feature is reliable, robust, and well-documented.

### **Step 10: Manual Validation Only (MVP)**

**SIMPLIFIED:** Skip formal test structure for MVP. Focus on manual testing:

1.  **Basic Smoke Test:** Run with `--overall-token-budget 10000` and verify tracking
2.  **Command Budget Test:** Use `--command-budget "/test=5000"` and verify limits
3.  **Visual Test:** Ensure progress bars display correctly
4.  **Warning Test:** Verify warn mode logs but doesn't block

**Note:** Formal test structure can be added AFTER basic functionality is proven.

### **Step 11: Basic Error Handling Only**

**SIMPLIFIED:** Only essential error handling:

1.  **CLI Parsing:** Existing try-except for ValueError is sufficient
2.  **Zero Division:** Already handled in percentage calculations
3.  **Skip Additional Logging:** Use existing logger, no extra complexity

### **Step 12: Minimal Documentation**

**SIMPLIFIED:** Just add usage examples to CLI help text. Skip README updates for MVP.

---

## **FINAL IMPLEMENTATION CHECKLIST**

### Essential Changes (MUST DO):
- [ ] Fix import paths with sys.path manipulation (3 lines)
- [ ] Add `_last_known_total_tokens` to InstanceStatus (1 line)
- [ ] Extract base command in budget checking (2 lines)
- [ ] Pass instance_name to _parse_token_usage (modify signature)
- [ ] Use single `--disable-budget-visuals` flag

### Optional (SKIP FOR MVP):
- ❌ Thread safety (not needed)
- ❌ Complex BudgetStatus dataclass (use dict)
- ❌ Platform compatibility checks
- ❌ Formal test structure
- ❌ Negative number validation
- ❌ Elaborate error handling

### Total Lines Changed: ~10-15 lines

---

## **IMPLEMENTATION NOTES**

1. **Start Small:** Get basic tracking working first
2. **Test Manually:** Verify with real orchestrator runs
3. **Iterate:** Add complexity ONLY if problems arise
4. **KISS Principle:** Every line should have clear, immediate value

Update the project's documentation to reflect the new capabilities.

1.  **Update `README.md`:** Add a new section explaining the token budget feature, its purpose, and how to use it.
2.  **Update CLI Help Text:** Ensure the help text for the new arguments is clear and provides examples (e.g., `'/mycommand=5000'`).
3.  **Update `claude-instance-orchestrator.py` Docstring:** Add usage examples for the new budget flags to the docstring at the top of the file.