# Claude Test Continuation Guide - Token Management Strategies

## How to Keep Claude Working Through All Test Fixes

This guide provides keywords and strategies to prevent Claude from stopping prematurely when fixing multiple test failures.

## Keywords and Prompts for Better Token Management

### 1. Explicit Continuation Commands
- `"Continue fixing ALL remaining test failures"`
- `"Keep going until ALL tests pass"`
- `"Don't stop - fix the next failing test"`
- `"Continue with the remaining failures"`

### 2. Batching Strategy
- `"Fix tests in batches of 5, then report progress"`
- `"Group similar test failures and fix them together"`
- `"Fix all TypeErrors first, then move to the next category"`

### 3. Progress Tracking Prompts
- `"Show me a count of fixed vs remaining tests after each batch"`
- `"Mark each test as complete and continue"`
- `"Update the todo list and continue with the next item"`

## Best Practices for Long Test Sessions

### Use TodoWrite Tool Effectively
```python
# Example prompt structure:
"Create a todo list of ALL failing tests, then work through them systematically marking each as complete"
```

### Request Focused Output
- `"Fix the tests but skip explanations - just show the fixes"`
- `"Minimal output - just the essential changes"`
- `"Code only - no commentary"`

### Token-Saving Commands
- `"Continue from test #X"`
- `"Resume from the last completed test"`
- `"Pick up where you left off"`

## Sample Workflow Prompt

### Fast-Fail Testing Strategy (Recommended)
```
"Run tests with --fast-fail flag to stop on first failure. Fix that test, 
then run again with --fast-fail. Repeat until no failures. 
Keep a todo list tracking each fix. Minimal output - just show the fixes."
```

### Batch Processing Strategy (For Known Multiple Failures)
```
"Run the tests with --fast-fail, fix the failure, verify it passes, 
then continue to next failure. Create a todo list and work through 
systematically. After fixing 5 tests, run full suite to check progress. 
Continue until all tests pass. Use minimal output."
```

### Full Discovery Strategy (When You Need Overview)
```
"First run ALL tests without --fast-fail to discover all failures, 
create a todo list grouped by error type, then switch to --fast-fail mode 
and fix them one by one. Mark each complete and continue automatically 
until all tests pass."
```

## Recovery Phrases When Claude Stops

- `"You stopped at test X of Y - continue with the remaining tests"`
- `"Resume fixing - there are still N tests failing"`
- `"Keep going - we're not done yet"`

## Key Principles

1. **Be Explicit** - Always specify "ALL" tests and "continue until complete"
2. **Use Todo Lists** - Leverage TodoWrite tool for systematic progress tracking
3. **Batch Processing** - Group similar fixes to optimize token usage
4. **Minimal Output** - Request code-only responses to save tokens
5. **Clear Continuation** - Use explicit continuation commands when Claude stops

## Example Session Structure

1. Initial command: `"Run tests and create todo list of all failures"`
2. Work command: `"Fix all tests in batches of 5, minimal output"`
3. If stopped: `"Continue with remaining X tests"`
4. Verification: `"Run tests again to confirm all pass"`

---
*Generated: 2025-08-29*
*Purpose: Guide for maintaining Claude's focus during extended test-fixing sessions*