#!/usr/bin/env python3
"""Test actual warning behavior in the orchestrator."""

import sys
from pathlib import Path
import logging

# Setup logging to see warnings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent))

from claude_instance_orchestrator import ClaudeInstanceOrchestrator, InstanceConfig, InstanceStatus

def test_pre_execution_warnings():
    """Test pre-execution budget warnings."""
    print("=" * 80)
    print("TESTING PRE-EXECUTION BUDGET WARNINGS")
    print("=" * 80)

    workspace = Path.cwd()

    # Create orchestrator with small budget
    orchestrator = ClaudeInstanceOrchestrator(
        workspace_dir=workspace,
        overall_token_budget=50,  # Very small budget
        budget_enforcement_mode="warn",
        enable_budget_visuals=True,
        quiet=False
    )

    # Set command budget
    orchestrator.budget_manager.set_command_budget("/test", 30)

    # Create instance config
    config = InstanceConfig(
        command="/test arg1 arg2",
        name="test_instance",
        max_tokens_per_command=25  # Estimated tokens
    )

    orchestrator.add_instance(config)

    print(f"Budget setup:")
    print(f"  Overall budget: {orchestrator.budget_manager.overall_budget}")
    print(f"  Command budget for /test: {orchestrator.budget_manager.command_budgets['/test'].limit}")
    print(f"  Estimated tokens for this instance: {config.max_tokens_per_command}")

    # Simulate some usage to get close to budget
    print(f"\n--- Recording 40 tokens to approach budget limit ---")
    orchestrator.budget_manager.record_usage("/test", 40)

    print(f"Current usage:")
    print(f"  Total usage: {orchestrator.budget_manager.total_usage}")
    print(f"  Command usage: {orchestrator.budget_manager.command_budgets['/test'].used}")

    # Now test the pre-execution check (this should trigger warnings)
    print(f"\n--- Testing pre-execution check ---")

    # Manually call the pre-execution budget check logic
    base_command = config.command.split()[0]
    estimated_tokens = config.max_tokens_per_command or 1000

    print(f"Checking budget for command: '{base_command}' with {estimated_tokens} estimated tokens")

    can_run, reason = orchestrator.budget_manager.check_budget(base_command, estimated_tokens)

    print(f"Budget check result: can_run={can_run}, reason='{reason}'")

    if not can_run:
        if orchestrator.budget_manager.enforcement_mode == "warn":
            message = f"Budget exceeded for instance {config.name}: {reason}. Skipping."
            print(f"⚠️  WARN MODE would show: {message}")
        elif orchestrator.budget_manager.enforcement_mode == "block":
            message = f"Budget exceeded for instance {config.name}: {reason}. Skipping."
            print(f"🚫 BLOCK MODE would show: {message}")

def test_runtime_warnings():
    """Test runtime budget warnings during token usage updates."""
    print("\n" + "=" * 80)
    print("TESTING RUNTIME BUDGET WARNINGS")
    print("=" * 80)

    workspace = Path.cwd()

    # Create orchestrator with small budget
    orchestrator = ClaudeInstanceOrchestrator(
        workspace_dir=workspace,
        overall_token_budget=100,
        budget_enforcement_mode="warn",
        enable_budget_visuals=True,
        quiet=False
    )

    orchestrator.budget_manager.set_command_budget("/test", 60)

    # Create instance
    config = InstanceConfig(command="/test", name="test_instance")
    orchestrator.add_instance(config)
    status = InstanceStatus("test_instance")

    print(f"Testing runtime warning when tokens exceed budget...")
    print(f"Initial state: total_usage={orchestrator.budget_manager.total_usage}")

    # Simulate token usage that gradually exceeds budget
    test_scenarios = [
        (30, "First batch - within budget"),
        (40, "Second batch - exceeds command budget"),
        (50, "Third batch - exceeds overall budget")
    ]

    for tokens, description in test_scenarios:
        print(f"\n--- {description}: Adding {tokens} tokens ---")

        # Simulate the update budget tracking logic
        current_billable_tokens = status.total_tokens + status.cached_tokens + tokens
        status.total_tokens += tokens

        if current_billable_tokens > status._last_known_total_tokens:
            new_tokens = current_billable_tokens - status._last_known_total_tokens
            base_command = "/test"

            # Record the usage
            orchestrator.budget_manager.record_usage(base_command, new_tokens)
            status._last_known_total_tokens = current_billable_tokens

            print(f"  Recorded {new_tokens} new tokens")
            print(f"  Total system usage: {orchestrator.budget_manager.total_usage}")
            print(f"  Command usage: {orchestrator.budget_manager.command_budgets['/test'].used}")

            # Check for runtime budget violation
            violation_detected = False
            violation_reason = ""

            # Check overall budget
            if (orchestrator.budget_manager.overall_budget is not None and
                orchestrator.budget_manager.total_usage > orchestrator.budget_manager.overall_budget):
                violation_detected = True
                violation_reason = f"Overall budget exceeded: {orchestrator.budget_manager.total_usage}/{orchestrator.budget_manager.overall_budget} tokens"

            # Check command budget (only if overall budget check didn't fail)
            elif (base_command in orchestrator.budget_manager.command_budgets):
                command_budget = orchestrator.budget_manager.command_budgets[base_command]
                if command_budget.used > command_budget.limit:
                    violation_detected = True
                    violation_reason = f"Command '{base_command}' budget exceeded: {command_budget.used}/{command_budget.limit} tokens"

            if violation_detected:
                message = f"Runtime budget violation for test_instance: {violation_reason}"
                if orchestrator.budget_manager.enforcement_mode == "block":
                    print(f"  🚫 RUNTIME TERMINATION would show: {message}")
                else:  # warn mode
                    print(f"  ⚠️  RUNTIME WARNING would show: {message}")
            else:
                print(f"  ✅ No budget violation detected")

def test_yellow_warning_symbols():
    """Test if yellow warning symbols are actually displayed."""
    print("\n" + "=" * 80)
    print("TESTING YELLOW WARNING SYMBOLS IN PROGRESS BARS")
    print("=" * 80)

    from token_budget.visualization import render_progress_bar

    # Test different usage levels to see color coding
    test_cases = [
        (65, 100, "65% usage (should be green)"),
        (75, 100, "75% usage (should be yellow)"),
        (85, 100, "85% usage (should be yellow)"),
        (95, 100, "95% usage (should be red)"),
    ]

    print("Progress bar colors:")
    for used, total, description in test_cases:
        bar = render_progress_bar(used, total)
        # Check the color codes in the string
        if '\033[93m' in bar:
            symbol = "🟡 YELLOW"
        elif '\033[91m' in bar:
            symbol = "🔴 RED"
        elif '\033[92m' in bar:
            symbol = "🟢 GREEN"
        else:
            symbol = "❓ NO COLOR"

        print(f"  {description}: {bar} {symbol}")

if __name__ == "__main__":
    print("COMPREHENSIVE WARNING SYSTEM TEST")
    print("Testing user's specific complaints:")
    print("1. No warning when token usage crossed budget")
    print("2. Tokens parameter remaining 0 for tasks")
    print("3. Missing yellow symbols for budget warnings")
    print("4. Want model names and tool usage tables")

    test_pre_execution_warnings()
    test_runtime_warnings()
    test_yellow_warning_symbols()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)