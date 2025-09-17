#!/usr/bin/env python3
"""Test script to verify current token budget behavior and warnings."""

import os
import sys
from pathlib import Path
import json

# Add current directory to path to import the modules
sys.path.insert(0, str(Path(__file__).parent))

from token_budget.budget_manager import TokenBudgetManager
from token_budget.visualization import render_progress_bar

def test_warning_behavior():
    """Test if warnings appear when token usage crosses budget."""
    print("=" * 60)
    print("TEST 1: Warning behavior when budget is crossed")
    print("=" * 60)

    # Create a budget manager with small budget to trigger warnings
    manager = TokenBudgetManager(overall_budget=100, enforcement_mode="warn")
    manager.set_command_budget("/test", 50)

    print(f"Initial state:")
    print(f"  Overall budget: {manager.overall_budget}")
    print(f"  Total usage: {manager.total_usage}")
    print(f"  Command budgets: {manager.command_budgets}")

    # Test 1: Usage within budget
    print(f"\n--- Recording 30 tokens (within budget) ---")
    manager.record_usage("/test", 30)
    can_run, reason = manager.check_budget("/test", 10)
    print(f"After recording 30 tokens:")
    print(f"  Total usage: {manager.total_usage}")
    print(f"  Command usage: {manager.command_budgets['/test'].used}")
    print(f"  Can run check (10 more tokens): {can_run}, {reason}")

    # Test 2: Usage that exceeds command budget
    print(f"\n--- Recording 30 more tokens (exceeds command budget) ---")
    manager.record_usage("/test", 30)
    can_run, reason = manager.check_budget("/test", 10)
    print(f"After recording 60 tokens total:")
    print(f"  Total usage: {manager.total_usage}")
    print(f"  Command usage: {manager.command_budgets['/test'].used}")
    print(f"  Can run check (10 more tokens): {can_run}, {reason}")

    # Test 3: Usage that exceeds overall budget
    print(f"\n--- Recording 50 more tokens (exceeds overall budget) ---")
    manager.record_usage("/test", 50)
    can_run, reason = manager.check_budget("/test", 10)
    print(f"After recording 110 tokens total:")
    print(f"  Total usage: {manager.total_usage}")
    print(f"  Command usage: {manager.command_budgets['/test'].used}")
    print(f"  Can run check (10 more tokens): {can_run}, {reason}")

def test_visualization():
    """Test the progress bar visualization with different thresholds."""
    print("\n" + "=" * 60)
    print("TEST 2: Progress bar visualization at different usage levels")
    print("=" * 60)

    # Test progress bars at different usage levels
    test_cases = [
        (10, 100, "10% usage - should be green"),
        (50, 100, "50% usage - should be green"),
        (75, 100, "75% usage - should be yellow"),
        (95, 100, "95% usage - should be red"),
        (110, 100, "110% usage - over budget, should be red")
    ]

    for used, total, description in test_cases:
        bar = render_progress_bar(used, total)
        print(f"{description}: {bar}")

def test_runtime_tracking():
    """Test if the system tracks tokens correctly during runtime."""
    print("\n" + "=" * 60)
    print("TEST 3: Runtime token tracking")
    print("=" * 60)

    # Test token parsing logic by simulating the orchestrator
    from claude_instance_orchestrator import InstanceStatus

    status = InstanceStatus("test_instance")

    # Simulate JSON output that would come from Claude
    test_json_lines = [
        '{"usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}}',
        '{"usage": {"input_tokens": 200, "output_tokens": 80, "total_tokens": 280}}',
        '{"type": "tool_use", "name": "example_tool"}'
    ]

    print(f"Initial status:")
    print(f"  Input tokens: {status.input_tokens}")
    print(f"  Output tokens: {status.output_tokens}")
    print(f"  Total tokens: {status.total_tokens}")
    print(f"  Tool calls: {status.tool_calls}")

    # Import the orchestrator to access parsing methods
    from claude_instance_orchestrator import ClaudeInstanceOrchestrator

    # Create a minimal orchestrator just for testing parsing
    workspace = Path.cwd()
    orchestrator = ClaudeInstanceOrchestrator(workspace)

    print(f"\nProcessing JSON lines:")
    for i, line in enumerate(test_json_lines):
        print(f"  Line {i+1}: {line}")
        orchestrator._parse_token_usage(line, status, "test_instance")
        print(f"    After parsing - Total: {status.total_tokens}, Tools: {status.tool_calls}")

def test_budget_warnings_in_orchestrator():
    """Test if the orchestrator shows budget warnings."""
    print("\n" + "=" * 60)
    print("TEST 4: Budget warnings in orchestrator")
    print("=" * 60)

    from claude_instance_orchestrator import ClaudeInstanceOrchestrator, InstanceConfig, InstanceStatus

    workspace = Path.cwd()

    # Create orchestrator with small budget to trigger warnings
    orchestrator = ClaudeInstanceOrchestrator(
        workspace_dir=workspace,
        overall_token_budget=100,
        budget_enforcement_mode="warn",
        enable_budget_visuals=True
    )

    # Set up a command budget
    orchestrator.budget_manager.set_command_budget("/test", 50)

    print(f"Budget manager configuration:")
    print(f"  Overall budget: {orchestrator.budget_manager.overall_budget}")
    print(f"  Enforcement mode: {orchestrator.budget_manager.enforcement_mode}")
    print(f"  Command budgets: {orchestrator.budget_manager.command_budgets}")

    # Simulate token usage that would trigger warnings
    config = InstanceConfig(command="/test", name="test_instance")
    status = InstanceStatus("test_instance")

    # Simulate recording usage that exceeds budget
    print(f"\nSimulating token usage...")

    # Add some initial usage
    status.total_tokens = 60
    status.input_tokens = 40
    status.output_tokens = 20
    orchestrator.budget_manager.record_usage("/test", 60)

    print(f"After recording 60 tokens:")
    print(f"  Total system usage: {orchestrator.budget_manager.total_usage}")
    print(f"  Command usage: {orchestrator.budget_manager.command_budgets['/test'].used}")

    # Test pre-execution budget check
    can_run, reason = orchestrator.budget_manager.check_budget("/test", 50)
    print(f"Pre-execution check for 50 more tokens: {can_run}, {reason}")

if __name__ == "__main__":
    print("Token Budget System Test")
    print("=" * 60)

    try:
        test_warning_behavior()
        test_visualization()
        test_runtime_tracking()
        test_budget_warnings_in_orchestrator()

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print("✅ All tests completed successfully")
        print("📊 The token budget system appears to be functional")
        print("⚠️  Check console output above for warning behavior")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()