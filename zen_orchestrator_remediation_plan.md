# Issue #1318 Remediation Plan: Command Budgets Without Overall Budget

## Problem Summary
The TokenBudgetManager is only initialized when `overall_token_budget` is explicitly provided, preventing command-specific budgets from functioning independently. This breaks the use case where users want command-level budget control without setting an overall budget limit.

## Root Cause
In `zen_orchestrator.py` line 159:
```python
if TokenBudgetManager and overall_token_budget is not None:
    self.budget_manager = TokenBudgetManager(...)
else:
    self.budget_manager = None
```

The condition `overall_token_budget is not None` prevents initialization when only command budgets are configured.

## Test Verification
✅ **Bug Reproduced**: Created `test_issue_1318_reproduction.py` which confirms:
- Config with only command budgets (no overall_budget) loads correctly
- Orchestrator sets `budget_manager = None` despite command budgets being configured
- Command budgets cannot be set or enforced without the manager

## Proposed Solution

### 1. Enhanced Initialization Logic
Change the initialization condition to:
```python
# Initialize budget manager if ANY budget settings are provided
has_overall_budget = overall_token_budget is not None
has_command_budgets = bool(command_budgets_from_config)  # Need to check config
needs_budget_manager = has_overall_budget or has_command_budgets

if TokenBudgetManager and needs_budget_manager:
    self.budget_manager = TokenBudgetManager(
        overall_budget=overall_token_budget,  # Can be None
        enforcement_mode=budget_enforcement_mode
    )
else:
    self.budget_manager = None
```

### 2. Default Overall Budget Behavior
When `overall_budget=None` in TokenBudgetManager:
- ✅ Already supported by TokenBudgetManager constructor
- ✅ `check_budget()` method properly skips overall budget check when None
- ✅ Command-specific budgets work independently

### 3. Configuration Detection
Need to detect command budgets from config earlier in the initialization process:
```python
# Early detection of command budgets from config
config_command_budgets = {}
if config_file_path and os.path.exists(config_file_path):
    with open(config_file_path) as f:
        config = json.load(f)
        config_command_budgets = config.get("budget", {}).get("command_budgets", {})
```

## Implementation Steps

### Step 1: Update Orchestrator Initialization
Modify `zen_orchestrator.py` lines 158-166:
- Add early config file detection for command budgets
- Change initialization condition to check for ANY budget features
- Preserve existing overall_budget=None support

### Step 2: Update Command Budget Loading
The existing command budget loading code (lines 2074-2102) will work without changes since it already checks for `orchestrator.budget_manager` existence.

### Step 3: Comprehensive Testing
- ✅ Test with only overall budget (existing behavior)
- ✅ Test with only command budgets (new behavior)
- ✅ Test with both overall and command budgets (existing behavior)
- ✅ Test with no budgets (existing behavior)

## Risk Assessment

### Low Risk Changes
- TokenBudgetManager already supports `overall_budget=None`
- Command budget setting logic already checks for manager existence
- No breaking changes to existing API

### Validation Required
- Ensure config file parsing happens before budget manager initialization
- Verify CLI command budgets still override config command budgets
- Confirm budget reporting works with None overall budget

## Expected Outcome
After fix:
1. ✅ Command budgets work without overall budget
2. ✅ Overall budget still works as before
3. ✅ Mixed scenarios (both types) work as before
4. ✅ Budget enforcement applies to command limits when overall is None
5. ✅ Budget reporting shows unlimited overall with specific command limits

## Test Success Criteria
When `test_issue_1318_reproduction.py` is run after the fix:
- Should create TokenBudgetManager even with overall_budget=None
- Should successfully set command budgets
- Should report command budget limits correctly
- Should show "TEST PASSED" instead of "TEST FAILED"