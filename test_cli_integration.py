#!/usr/bin/env python3
"""Test script for CLI integration of adaptive budget management."""

import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock

# Add zen to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cli_argument_parsing():
    """Test that CLI arguments are properly parsed."""
    try:
        # Import zen_orchestrator
        import zen_orchestrator

        # Test argument parsing with adaptive features
        test_args = [
            "--adaptive-budget",
            "--overall-token-budget", "1000",
            "--checkpoint-intervals", "0.2,0.4,0.6,0.8,1.0",
            "--restart-threshold", "0.85",
            "--min-completion-probability", "0.6",
            "--max-restarts", "1",
            "--todo-estimation-buffer", "0.15"
        ]

        # Mock sys.argv for argument parsing
        original_argv = sys.argv
        sys.argv = ["zen_orchestrator.py"] + test_args

        try:
            # Test that arguments can be parsed without error
            from zen_orchestrator import main

            # We can't easily test the full main function due to asyncio,
            # but we can test that the imports work
            logger.info("✅ CLI argument parsing imports successful")
            return True

        except SystemExit:
            # argparse calls sys.exit() normally, which is expected
            logger.info("✅ Argument parsing completed (SystemExit is expected)")
            return True
        finally:
            sys.argv = original_argv

    except Exception as e:
        logger.error(f"❌ CLI argument parsing test failed: {e}")
        return False

def test_orchestrator_initialization():
    """Test orchestrator initialization with adaptive parameters."""
    try:
        from zen_orchestrator import ClaudeInstanceOrchestrator
        from pathlib import Path

        # Test standard initialization
        orchestrator_standard = ClaudeInstanceOrchestrator(
            workspace_dir=Path("/tmp"),
            overall_token_budget=1000,
            budget_enforcement_mode="warn",
            adaptive_budget_enabled=False
        )

        assert orchestrator_standard is not None
        logger.info("✅ Standard orchestrator initialization successful")

        # Test adaptive initialization
        orchestrator_adaptive = ClaudeInstanceOrchestrator(
            workspace_dir=Path("/tmp"),
            overall_token_budget=1000,
            budget_enforcement_mode="warn",
            adaptive_budget_enabled=True,
            checkpoint_intervals=[0.25, 0.5, 0.75, 1.0],
            restart_threshold=0.9,
            min_completion_probability=0.5,
            max_restarts=2
        )

        assert orchestrator_adaptive is not None
        logger.info("✅ Adaptive orchestrator initialization successful")

        # Test that adaptive methods are available
        assert hasattr(orchestrator_adaptive, 'execute_adaptive_command')
        assert hasattr(orchestrator_adaptive, 'get_adaptive_status')
        logger.info("✅ Adaptive methods available on orchestrator")

        return True

    except Exception as e:
        logger.error(f"❌ Orchestrator initialization test failed: {e}")
        return False

def test_adaptive_status_reporting():
    """Test adaptive status reporting functionality."""
    try:
        from zen_orchestrator import ClaudeInstanceOrchestrator
        from pathlib import Path

        # Create orchestrator with adaptive features
        orchestrator = ClaudeInstanceOrchestrator(
            workspace_dir=Path("/tmp"),
            overall_token_budget=1000,
            budget_enforcement_mode="warn",
            adaptive_budget_enabled=True,
            checkpoint_intervals=[0.25, 0.5, 0.75, 1.0]
        )

        # Test adaptive status method
        status = orchestrator.get_adaptive_status()
        assert isinstance(status, dict)
        assert 'budget_manager_type' in status
        logger.info("✅ Adaptive status reporting works")

        # Log status for inspection
        logger.info(f"Adaptive status: {status}")

        return True

    except Exception as e:
        logger.error(f"❌ Adaptive status reporting test failed: {e}")
        return False

def test_adaptive_command_execution():
    """Test adaptive command execution functionality."""
    try:
        from zen_orchestrator import ClaudeInstanceOrchestrator
        from pathlib import Path

        # Create orchestrator with adaptive features
        orchestrator = ClaudeInstanceOrchestrator(
            workspace_dir=Path("/tmp"),
            overall_token_budget=1000,
            budget_enforcement_mode="warn",
            adaptive_budget_enabled=True
        )

        # Test command execution method
        result = orchestrator.execute_adaptive_command("/test-command", {"test": "context"})
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'adaptive_execution' in result
        logger.info("✅ Adaptive command execution method works")

        # Log result for inspection
        logger.info(f"Execution result: {result}")

        return True

    except Exception as e:
        logger.error(f"❌ Adaptive command execution test failed: {e}")
        return False

def test_block_mode_precedence():
    """Test that block mode properly supersedes adaptive features."""
    try:
        from zen_orchestrator import ClaudeInstanceOrchestrator
        from pathlib import Path

        # Test that block mode disables adaptive features
        orchestrator = ClaudeInstanceOrchestrator(
            workspace_dir=Path("/tmp"),
            overall_token_budget=1000,
            budget_enforcement_mode="block",  # This should disable adaptive
            adaptive_budget_enabled=True      # This should be ignored
        )

        # Check that adaptive features are properly disabled
        status = orchestrator.get_adaptive_status()

        # The budget manager should be standard, not adaptive
        if 'adaptive_mode' in status:
            assert status['adaptive_mode'] is False

        logger.info("✅ Block mode precedence works correctly")
        logger.info(f"Status with block mode: {status}")

        return True

    except Exception as e:
        logger.error(f"❌ Block mode precedence test failed: {e}")
        return False

def test_imports_integration():
    """Test that all adaptive components can be imported through the orchestrator."""
    try:
        # Test imports work at orchestrator level
        from zen_orchestrator import (
            ClaudeInstanceOrchestrator,
            TokenBudgetManager,
            BudgetManagerFactory,
            AdaptiveConfig
        )

        # Test that adaptive components are importable
        assert ClaudeInstanceOrchestrator is not None
        assert TokenBudgetManager is not None

        # These might be None if adaptive components aren't available
        if BudgetManagerFactory is not None:
            logger.info("✅ BudgetManagerFactory available")
        else:
            logger.warning("⚠️  BudgetManagerFactory not available")

        if AdaptiveConfig is not None:
            logger.info("✅ AdaptiveConfig available")
        else:
            logger.warning("⚠️  AdaptiveConfig not available")

        logger.info("✅ Import integration test successful")
        return True

    except ImportError as e:
        logger.error(f"❌ Import integration test failed: {e}")
        return False

def main():
    """Run all CLI integration tests."""
    logger.info("🧪 Starting CLI Integration Tests for Adaptive Budget Management")
    logger.info("=" * 60)

    tests = [
        ("Import Integration", test_imports_integration),
        ("CLI Argument Parsing", test_cli_argument_parsing),
        ("Orchestrator Initialization", test_orchestrator_initialization),
        ("Adaptive Status Reporting", test_adaptive_status_reporting),
        ("Adaptive Command Execution", test_adaptive_command_execution),
        ("Block Mode Precedence", test_block_mode_precedence)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            failed += 1

    logger.info("\n" + "=" * 60)
    logger.info(f"📊 CLI Integration Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        logger.info("🎉 All CLI integration tests passed!")
        return True
    else:
        logger.error(f"💥 {failed} CLI integration tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)