#!/usr/bin/env python3
"""Simple test script for adaptive budget management implementation."""

import sys
from pathlib import Path
import logging

# Add token_budget to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported."""
    try:
        from token_budget.adaptive_models import (
            AdaptiveConfig, TodoItem, TodoCategory, ExecutionState,
            ExecutionResult, TrendAnalysis
        )
        from token_budget.adaptive_controller import AdaptiveBudgetController
        from token_budget.proactive_planner import ProactivePlanner
        from token_budget.quarter_manager import QuarterManager
        from token_budget.safe_restart import SafeRestartManager
        from token_budget.trend_analyzer import BudgetTrendAnalyzer
        from token_budget.integration import BudgetManagerFactory, AdaptiveIntegration

        logger.info("✅ All imports successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False

def test_adaptive_config():
    """Test AdaptiveConfig creation and validation."""
    try:
        from token_budget.adaptive_models import AdaptiveConfig

        # Test default config
        config = AdaptiveConfig()
        assert config.enabled is True
        assert config.min_completion_probability == 0.5
        assert config.checkpoint_intervals == [0.25, 0.5, 0.75, 1.0]

        # Test custom config
        custom_config = AdaptiveConfig(
            restart_threshold=0.8,
            max_restarts=3,
            checkpoint_intervals=[0.2, 0.4, 0.6, 0.8, 1.0]
        )
        assert custom_config.restart_threshold == 0.8
        assert custom_config.max_restarts == 3
        assert len(custom_config.checkpoint_intervals) == 5

        logger.info("✅ AdaptiveConfig tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ AdaptiveConfig test failed: {e}")
        return False

def test_proactive_planner():
    """Test ProactivePlanner functionality."""
    try:
        from token_budget.proactive_planner import ProactivePlanner
        from token_budget.adaptive_models import AdaptiveConfig, TodoCategory

        planner = ProactivePlanner()

        # Test command parsing
        execution_plan = planner.create_execution_plan(
            "/analyze-code",
            {"workspace": "/tmp/test"},
            1000
        )

        assert len(execution_plan.todos) > 0
        assert execution_plan.total_estimated_budget > 0
        assert len(execution_plan.quarter_distribution) == 4

        # Verify todos have required properties
        for todo in execution_plan.todos:
            assert todo.todo_id
            assert todo.description
            assert isinstance(todo.category, TodoCategory)
            assert todo.estimated_tokens > 0

        logger.info("✅ ProactivePlanner tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ ProactivePlanner test failed: {e}")
        return False

def test_quarter_manager():
    """Test QuarterManager functionality."""
    try:
        from token_budget.quarter_manager import QuarterManager

        manager = QuarterManager(1000)

        # Test quarter initialization
        assert len(manager.quarter_plans) == 4
        for i in range(1, 5):
            plan = manager.get_quarter_plan(i)
            assert plan is not None
            assert plan.allocated_budget > 0

        # Test budget calculations
        remaining = manager.get_total_remaining_budget()
        assert remaining > 0

        # Test statistics
        stats = manager.get_quarter_statistics()
        assert len(stats) == 4

        logger.info("✅ QuarterManager tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ QuarterManager test failed: {e}")
        return False

def test_safe_restart_manager():
    """Test SafeRestartManager functionality."""
    try:
        from token_budget.safe_restart import SafeRestartManager
        from token_budget.adaptive_models import TodoItem, TodoCategory

        manager = SafeRestartManager()

        # Create some test todos
        todos = [
            TodoItem(
                todo_id="1",
                description="Search code",
                category=TodoCategory.SEARCH,
                estimated_tokens=100
            ),
            TodoItem(
                todo_id="2",
                description="Analyze results",
                category=TodoCategory.ANALYZE,
                estimated_tokens=200
            )
        ]

        # Test restart plan creation
        restart_plan = manager.create_precomputed_restart_plan(todos)
        assert restart_plan is not None
        assert len(restart_plan.planned_points) > 0

        # Test validation
        has_guaranteed = manager.validate_restart_plan_has_guaranteed_points()
        assert has_guaranteed is True

        logger.info("✅ SafeRestartManager tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ SafeRestartManager test failed: {e}")
        return False

def test_adaptive_controller():
    """Test AdaptiveBudgetController functionality."""
    try:
        from token_budget.adaptive_controller import AdaptiveBudgetController
        from token_budget.adaptive_models import AdaptiveConfig

        # Create controller
        controller = AdaptiveBudgetController(
            total_budget=1000,
            adaptive_mode=True,
            enforcement_mode="warn"
        )

        assert controller.total_budget == 1000
        assert controller.adaptive_mode is True
        assert controller.enforcement_mode == "warn"

        # Test configuration validation
        issues = controller.validate_configuration()
        logger.info(f"Configuration issues: {issues}")

        # Test statistics
        stats = controller.get_execution_statistics()
        assert 'total_budget' in stats
        assert 'adaptive_mode' in stats

        logger.info("✅ AdaptiveBudgetController tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ AdaptiveBudgetController test failed: {e}")
        return False

def test_integration():
    """Test integration utilities."""
    try:
        from token_budget.integration import BudgetManagerFactory, AdaptiveIntegration
        from token_budget.adaptive_controller import AdaptiveBudgetController
        from token_budget.budget_manager import TokenBudgetManager

        # Test factory - standard manager
        standard_manager = BudgetManagerFactory.create_budget_manager(
            overall_budget=500,
            enforcement_mode="warn",
            adaptive_enabled=False
        )
        assert isinstance(standard_manager, TokenBudgetManager)
        assert not isinstance(standard_manager, AdaptiveBudgetController)

        # Test factory - adaptive manager
        adaptive_manager = BudgetManagerFactory.create_budget_manager(
            overall_budget=1000,
            enforcement_mode="warn",
            adaptive_enabled=True
        )
        assert isinstance(adaptive_manager, AdaptiveBudgetController)

        # Test integration wrapper
        integration = AdaptiveIntegration(adaptive_manager)
        assert integration.is_adaptive is True

        # Test execution (simplified)
        status = integration.get_budget_status()
        assert 'total_budget' in status

        logger.info("✅ Integration tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False

def test_block_mode_precedence():
    """Test that block mode properly supersedes adaptive features."""
    try:
        from token_budget.integration import BudgetManagerFactory
        from token_budget.budget_manager import TokenBudgetManager

        # Test block mode disables adaptive
        manager = BudgetManagerFactory.create_budget_manager(
            overall_budget=1000,
            enforcement_mode="block",
            adaptive_enabled=True  # Should be ignored
        )

        # Should create standard manager, not adaptive
        assert isinstance(manager, TokenBudgetManager)
        assert manager.enforcement_mode == "block"

        logger.info("✅ Block mode precedence tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ Block mode precedence test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    logger.info("🧪 Starting Adaptive Budget Management Tests")
    logger.info("=" * 50)

    tests = [
        ("Import Tests", test_imports),
        ("AdaptiveConfig Tests", test_adaptive_config),
        ("ProactivePlanner Tests", test_proactive_planner),
        ("QuarterManager Tests", test_quarter_manager),
        ("SafeRestartManager Tests", test_safe_restart_manager),
        ("AdaptiveBudgetController Tests", test_adaptive_controller),
        ("Integration Tests", test_integration),
        ("Block Mode Precedence Tests", test_block_mode_precedence)
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

    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error(f"💥 {failed} tests failed!")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)