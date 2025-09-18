#!/usr/bin/env python3
"""
Test to reproduce Issue #1318: Tool needs default overall token budget or proper sub-budget handling

This test reproduces the specific bug where command budgets cannot work without an overall budget.
The TokenBudgetManager is only initialized when overall_token_budget is explicitly provided,
which prevents command-specific budgets from functioning independently.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add zen directory to path
sys.path.insert(0, str(Path(__file__).parent / "zen"))

from zen_orchestrator import ClaudeInstanceOrchestrator


def test_command_budgets_without_overall_budget():
    """
    Test that command budgets should work even when no overall budget is set.

    This test SHOULD FAIL with the current implementation, demonstrating the bug.
    """
    print("=== Testing Issue #1318: Command budgets without overall budget ===")

    # Create a config with ONLY command budgets, no overall budget
    config_data = {
        "instances": [
            {
                "command": "/test",
                "name": "test-instance",
                "description": "Test instance for budget reproduction",
                "allowed_tools": ["Task"],
                "permission_mode": "acceptEdits",
                "output_format": "stream-json"
            }
        ],
        "budget": {
            # NOTE: No overall_budget specified
            "enforcement_mode": "warn",
            "disable_visuals": False,
            "command_budgets": {
                "/test": 5000,
                "/debug": 3000,
                "/analyze": 8000
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_file = Path(f.name)

    try:
        print("Step 1: Loading config with command budgets but NO overall budget...")

        with open(config_file) as f:
            loaded_config = json.load(f)

        budget_config = loaded_config.get("budget", {})
        print(f"Budget config: {budget_config}")

        # Key assertion: overall_budget should be None/missing
        overall_budget = budget_config.get("overall_budget")
        print(f"Overall budget from config: {overall_budget}")
        assert overall_budget is None, f"Expected overall_budget to be None, got {overall_budget}"

        # Command budgets should be present
        command_budgets = budget_config.get("command_budgets", {})
        print(f"Command budgets from config: {command_budgets}")
        assert len(command_budgets) == 3, f"Expected 3 command budgets, got {len(command_budgets)}"

        print("Step 2: Creating orchestrator with NO overall budget...")

        # Try to create orchestrator with command budgets but no overall budget
        try:
            from token_budget.budget_manager import TokenBudgetManager

            # This is the problematic initialization - overall_token_budget is None
            orchestrator = ClaudeInstanceOrchestrator(
                workspace_dir=Path.cwd(),
                overall_token_budget=None,  # This should still allow command budgets to work
                budget_enforcement_mode=budget_config.get("enforcement_mode", "warn"),
                enable_budget_visuals=not budget_config.get("disable_visuals", False)
            )

            print(f"Orchestrator created. Budget manager: {orchestrator.budget_manager}")

            # THE BUG: This will be None because overall_token_budget was None
            if orchestrator.budget_manager is None:
                print("BUG REPRODUCED: budget_manager is None even though command budgets were configured!")
                print("   This prevents command budgets from being set or checked.")
                print(f"   Command budgets that should be available: {list(command_budgets.keys())}")
                return False  # Test fails as expected - this reproduces the bug

            # If we get here, the bug is fixed (budget manager exists)
            print("Budget manager exists, trying to set command budgets...")

            # Try to set command budgets
            for command_name, limit in command_budgets.items():
                try:
                    orchestrator.budget_manager.set_command_budget(command_name, limit)
                    print(f"   Set budget for {command_name}: {limit} tokens")
                except Exception as e:
                    print(f"❌ Failed to set budget for {command_name}: {e}")
                    return False

            # Verify the command budgets were set
            if hasattr(orchestrator.budget_manager, 'command_budgets'):
                actual_budgets = orchestrator.budget_manager.command_budgets
                print(f"✅ Command budgets successfully set: {list(actual_budgets.keys())}")

                # Test that we can check a specific command budget
                if '/test' in actual_budgets:
                    test_budget = actual_budgets['/test']
                    print(f"/test budget details: {test_budget.limit} tokens limit")
                    return True
                else:
                    print("/test budget not found in command_budgets")
                    return False
            else:
                print("budget_manager has no command_budgets attribute")
                return False

        except ImportError:
            print("⚠️  TokenBudgetManager not available, cannot test full integration")
            return False

    finally:
        # Clean up
        config_file.unlink()


def test_expected_behavior_demonstration():
    """
    Demonstrate what the EXPECTED behavior should be when the bug is fixed.
    """
    print("\n=== Expected Behavior (after fix) ===")
    print("When command budgets are configured but no overall budget is set:")
    print("1. TokenBudgetManager should still be initialized")
    print("2. overall_budget should default to unlimited or a high value")
    print("3. Command budgets should work independently")
    print("4. Budget enforcement should only apply to command-specific limits")
    print("5. Budget tracking and reporting should work for command budgets")


if __name__ == "__main__":
    print("Reproducing Issue #1318: Command budgets not working without overall budget")
    print("=" * 80)

    test_result = test_command_budgets_without_overall_budget()

    test_expected_behavior_demonstration()

    print("\n" + "=" * 80)
    if test_result:
        print("TEST PASSED: Bug appears to be fixed! Command budgets work without overall budget.")
        exit(0)
    else:
        print("TEST FAILED: Bug reproduced! Command budgets do not work without overall budget.")
        print("   This confirms Issue #1318 exists and needs to be fixed.")
        exit(1)