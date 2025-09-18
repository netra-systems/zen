#!/usr/bin/env python3
"""
Tests for Dollar-based Budget Support Enhancement (Issue #1347)

These tests validate the dollar-based budget functionality before and after implementation.
Initially these tests should FAIL to prove the feature doesn't exist yet.
After implementation, they should PASS to validate the feature works correctly.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from token_budget.budget_manager import TokenBudgetManager
    from token_transparency import ClaudePricingEngine, TokenUsageData
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    TokenBudgetManager = None
    ClaudePricingEngine = None


class TestDollarBudgetEnhancement(unittest.TestCase):
    """Test suite for dollar-based budget support enhancement"""

    def setUp(self):
        """Set up test fixtures"""
        if TokenBudgetManager is None or ClaudePricingEngine is None:
            self.skipTest("Required modules not available")

        # Create a cost-based budget manager for testing cost features
        self.budget_manager = TokenBudgetManager(overall_cost_budget=10.0)
        self.pricing_engine = ClaudePricingEngine()

    def test_dollar_budget_initialization_now_works(self):
        """Test that dollar budget initialization now works (should PASS after implementation)"""
        # These should now work since we implemented the feature
        try:
            manager = TokenBudgetManager(overall_cost_budget=10.0)
            self.assertEqual(manager.overall_budget, 10.0)
            self.assertTrue(manager.is_cost_budget)
        except Exception as e:
            self.fail(f"Dollar budget initialization should now work: {e}")

    def test_cost_budget_setting_now_works(self):
        """Test that cost-based command budget setting now works (should PASS after implementation)"""
        try:
            self.budget_manager.set_command_cost_budget("/test_command", 5.0)
            self.assertIn("/test_command", self.budget_manager.command_budgets)
            self.assertEqual(self.budget_manager.command_budgets["/test_command"].limit, 5.0)
        except Exception as e:
            self.fail(f"Cost budget setting should now work: {e}")

    def test_cost_budget_checking_now_works(self):
        """Test that cost budget checking now works (should PASS after implementation)"""
        try:
            self.budget_manager.set_command_cost_budget("/test_command", 5.0)
            can_run, reason = self.budget_manager.check_cost_budget("/test_command", 2.0)
            self.assertTrue(can_run)
            self.assertEqual(reason, "Within cost budget limits")
        except Exception as e:
            self.fail(f"Cost budget checking should now work: {e}")

    def test_token_to_cost_conversion_now_works(self):
        """Test that token to cost conversion now works (should PASS after implementation)"""
        try:
            cost = self.budget_manager.convert_tokens_to_cost(1000, "claude-3-5-sonnet")
            self.assertIsInstance(cost, float)
            self.assertGreater(cost, 0)
        except Exception as e:
            self.fail(f"Token to cost conversion should now work: {e}")

    def test_cost_to_token_conversion_now_works(self):
        """Test that cost to token conversion now works (should PASS after implementation)"""
        try:
            tokens = self.budget_manager.convert_cost_to_tokens(0.01, "claude-3-5-sonnet")
            self.assertIsInstance(tokens, int)
            self.assertGreater(tokens, 0)
        except Exception as e:
            self.fail(f"Cost to token conversion should now work: {e}")

    def test_budget_type_property_now_works(self):
        """Test that budget type property now works (should PASS after implementation)"""
        try:
            budget_type = self.budget_manager.budget_type
            self.assertIsNotNone(budget_type)
            # Should be cost type since we initialized with cost budget
            from token_budget.models import BudgetType
            self.assertEqual(budget_type, BudgetType.COST)
        except Exception as e:
            self.fail(f"Budget type property should now work: {e}")

    def test_mixed_budget_mode_now_works(self):
        """Test that mixed budget mode now works (should PASS after implementation)"""
        try:
            self.budget_manager.set_budget_parameter_type("mixed")
            from token_budget.models import BudgetType
            self.assertEqual(self.budget_manager.budget_type, BudgetType.MIXED)
        except Exception as e:
            self.fail(f"Mixed budget mode should now work: {e}")


class TestDollarBudgetImplementation(unittest.TestCase):
    """Test suite for dollar-based budget implementation (should PASS after implementation)"""

    def setUp(self):
        """Set up test fixtures"""
        if TokenBudgetManager is None or ClaudePricingEngine is None:
            self.skipTest("Required modules not available")

        self.budget_manager = TokenBudgetManager(overall_cost_budget=10.0)
        self.pricing_engine = ClaudePricingEngine()

    def test_dollar_budget_creation(self):
        """Test that dollar budget creation works correctly"""
        # Test creation with cost budget
        manager = TokenBudgetManager(overall_cost_budget=25.5)

        self.assertEqual(manager.overall_budget, 25.5)
        self.assertTrue(manager.is_cost_budget)
        self.assertFalse(manager.is_token_budget)
        self.assertIsNotNone(manager.pricing_engine)

    def test_cost_budget_setting_and_checking(self):
        """Test that cost budget setting and checking works"""
        # Set cost budget for a command
        self.budget_manager.set_command_cost_budget("/analyze", 5.0)

        # Verify budget was set
        self.assertIn("/analyze", self.budget_manager.command_budgets)
        budget_info = self.budget_manager.command_budgets["/analyze"]
        self.assertEqual(budget_info.limit, 5.0)
        self.assertTrue(budget_info.is_cost_budget)

        # Test cost budget checking
        can_run, reason = self.budget_manager.check_cost_budget("/analyze", 3.0)
        self.assertTrue(can_run)
        self.assertEqual(reason, "Within cost budget limits")

        # Test exceeding budget
        can_run, reason = self.budget_manager.check_cost_budget("/analyze", 6.0)
        self.assertFalse(can_run)
        self.assertIn("cost budget exceeded", reason)

    def test_cost_conversion_functionality(self):
        """Test token to cost and cost to token conversion"""
        # Test token to cost conversion
        cost = self.budget_manager.convert_tokens_to_cost(1000, "claude-3-5-sonnet")
        self.assertIsInstance(cost, float)
        self.assertGreater(cost, 0)

        # Test cost to token conversion
        tokens = self.budget_manager.convert_cost_to_tokens(0.01, "claude-3-5-sonnet")
        self.assertIsInstance(tokens, int)
        self.assertGreater(tokens, 0)

        # Test round-trip consistency (approximately)
        original_cost = 0.005
        converted_tokens = self.budget_manager.convert_cost_to_tokens(original_cost)
        back_to_cost = self.budget_manager.convert_tokens_to_cost(converted_tokens)
        # Should be approximately equal (within 20% due to estimation)
        self.assertLess(abs(back_to_cost - original_cost) / original_cost, 0.2)

    def test_budget_type_management(self):
        """Test budget type property and setting"""
        # Test initial type
        self.assertEqual(self.budget_manager.budget_type.value, "cost")

        # Test setting budget type
        from token_budget.models import BudgetType
        self.budget_manager.set_budget_parameter_type("mixed")
        self.assertEqual(self.budget_manager.budget_type, BudgetType.MIXED)

        # Test string-based setting
        self.budget_manager.set_budget_parameter_type("tokens")
        self.assertEqual(self.budget_manager.budget_type, BudgetType.TOKENS)

    def test_cost_usage_recording(self):
        """Test cost usage recording functionality"""
        # Set command budget
        self.budget_manager.set_command_cost_budget("/test", 3.0)

        # Record some cost usage
        self.budget_manager.record_cost_usage("/test", 1.5)

        # Check usage was recorded
        self.assertEqual(self.budget_manager.total_usage, 1.5)
        self.assertEqual(self.budget_manager.command_budgets["/test"].used, 1.5)
        self.assertEqual(self.budget_manager.command_budgets["/test"].remaining, 1.5)

    def test_backward_compatibility_with_tokens(self):
        """Test that token budgets still work alongside cost budgets"""
        # Create a manager that supports both
        mixed_manager = TokenBudgetManager(overall_budget=5000, budget_type="mixed")

        # Set both token and cost budgets
        mixed_manager.set_command_budget("/token_cmd", 1000)  # Token budget
        mixed_manager.set_command_cost_budget("/cost_cmd", 2.0)  # Cost budget

        # Verify both types were set
        token_budget = mixed_manager.command_budgets["/token_cmd"]
        cost_budget = mixed_manager.command_budgets["/cost_cmd"]

        self.assertTrue(token_budget.is_token_budget)
        self.assertEqual(token_budget.limit, 1000)

        self.assertTrue(cost_budget.is_cost_budget)
        self.assertEqual(cost_budget.limit, 2.0)

    def test_command_budget_formatting(self):
        """Test budget info formatting methods"""
        from token_budget.models import CommandBudgetInfo, BudgetType

        # Test cost budget formatting
        cost_budget = CommandBudgetInfo(5.50, 2.25, BudgetType.COST)
        self.assertEqual(cost_budget.format_limit(), "$5.5000")
        self.assertEqual(cost_budget.format_used(), "$2.2500")
        self.assertEqual(cost_budget.format_remaining(), "$3.2500")

        # Test token budget formatting
        token_budget = CommandBudgetInfo(1000, 750, BudgetType.TOKENS)
        self.assertEqual(token_budget.format_limit(), "1000 tokens")
        self.assertEqual(token_budget.format_used(), "750 tokens")
        self.assertEqual(token_budget.format_remaining(), "250 tokens")


class TestCLIDollarBudgetSupport(unittest.TestCase):
    """Test suite for CLI dollar budget argument support (Issue #1347)"""

    def setUp(self):
        """Set up test fixtures"""
        # These tests will validate that zen_orchestrator doesn't yet support dollar budgets
        pass

    def test_zen_orchestrator_has_cost_budget_args(self):
        """Test that zen_orchestrator.py now has cost budget arguments (should PASS after implementation)"""
        # Read zen_orchestrator.py and check if cost budget arguments exist
        zen_orchestrator_path = Path(__file__).parent.parent / "zen_orchestrator.py"

        with open(zen_orchestrator_path, 'r') as f:
            content = f.read()

        # These arguments should NOW exist after implementation
        cost_budget_args = [
            "--overall-cost-budget",
            "--command-cost-budget",
            "--budget-parameter-type"
        ]

        for arg in cost_budget_args:
            with self.subTest(arg=arg):
                # Should now find these arguments in the file
                self.assertIn(arg, content, f"Cost budget argument {arg} should now exist in zen_orchestrator.py")

    def test_import_statements_ready_for_enhancement(self):
        """Test that required imports are available for dollar budget implementation"""
        # Verify ClaudePricingEngine is available for integration
        try:
            from token_transparency import ClaudePricingEngine
            self.assertTrue(True, "ClaudePricingEngine import available")
        except ImportError:
            self.fail("ClaudePricingEngine not available - required for dollar budget implementation")

    def test_token_budget_manager_exists(self):
        """Test that TokenBudgetManager exists and is ready for enhancement"""
        try:
            from token_budget.budget_manager import TokenBudgetManager
            manager = TokenBudgetManager()
            self.assertTrue(hasattr(manager, 'overall_budget'), "TokenBudgetManager has overall_budget attribute")
            self.assertTrue(hasattr(manager, 'command_budgets'), "TokenBudgetManager has command_budgets attribute")
        except ImportError:
            self.fail("TokenBudgetManager not available - required for enhancement")


if __name__ == "__main__":
    # Run the failing tests to prove the feature doesn't exist yet
    unittest.main(verbosity=2)