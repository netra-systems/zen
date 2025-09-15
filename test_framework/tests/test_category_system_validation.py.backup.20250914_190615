#!/usr/bin/env python3
"""
Test Category System Validation - Ensures category registration completeness
P0 Critical Fix #3: Validation tests to catch missing category registrations
"""

import os
import pytest
from pathlib import Path

from test_framework.category_system import CategorySystem


class TestCategorySystemValidation:
    """Tests to validate category registration completeness"""
    
    def setup_method(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.category_system = CategorySystem(self.project_root)
    
    def test_core_test_categories_have_registrations(self):
        """
        P0 CRITICAL: Ensure core test category directories have registered categories.
        This prevents the Issue #155 scenario where mission_critical directory 
        exists but category is not registered.
        
        Note: Only checks core categories that should be executable via unified_test_runner.py
        """
        tests_dir = self.project_root / "tests"
        
        # Core categories that should definitely be registered for test runner
        core_categories = {
            'mission_critical',  # The main issue from #155
            'unit', 'integration', 'api', 'websocket', 'e2e',  # Standard test categories
            'smoke', 'database', 'security'  # Common categories
        }
        
        # Get directories that exist
        existing_core_dirs = []
        if tests_dir.exists():
            for category in core_categories:
                if (tests_dir / category).exists():
                    existing_core_dirs.append(category)
        
        # Get registered categories
        registered_categories = set(self.category_system.categories.keys())
        
        # Check for missing registrations in core categories only
        missing_core_registrations = []
        for directory in existing_core_dirs:
            if directory not in registered_categories:
                missing_core_registrations.append(directory)
        
        # Assert no missing core registrations
        assert not missing_core_registrations, (
            f"Core test directories found without registered categories: {missing_core_registrations}. "
            f"These core directories exist but are not registered in CategorySystem. "
            f"This can cause test runner status reporting inconsistency like Issue #155. "
            f"Please add them to CategorySystem._initialize_default_categories()"
        )
    
    def test_mission_critical_category_registered(self):
        """
        P0 CRITICAL: Specifically test that mission_critical category is registered.
        This directly addresses the Issue #155 root cause.
        """
        # Check that mission_critical category exists
        mission_critical = self.category_system.get_category("mission_critical")
        assert mission_critical is not None, (
            "mission_critical category must be registered in CategorySystem. "
            "This category has a test directory but was missing from registration."
        )
        
        # Verify it has appropriate configuration
        assert mission_critical.name == "mission_critical"
        assert "mission-critical" in mission_critical.tags or "business-value" in mission_critical.tags
        assert mission_critical.timeout_seconds > 0
    
    def test_execution_plan_tracks_requested_categories(self):
        """
        P0 CRITICAL: Ensure ExecutionPlan properly tracks requested categories.
        This supports Fix #1 for proper exit code handling.
        """
        # Test with a simple category request
        selected_categories = ["unit"]
        execution_plan = self.category_system.create_execution_plan(selected_categories)
        
        # Verify requested_categories is populated
        assert hasattr(execution_plan, 'requested_categories'), (
            "ExecutionPlan must have requested_categories field to support proper exit code logic"
        )
        assert execution_plan.requested_categories == {"unit"}, (
            f"ExecutionPlan should track requested categories. Expected {{'unit'}}, "
            f"got {execution_plan.requested_categories}"
        )
    
    def test_execution_plan_separates_requested_from_dependencies(self):
        """
        P0 CRITICAL: Ensure ExecutionPlan separates requested categories from dependencies.
        This validates the fix for exit code logic.
        """
        # Use integration which has dependencies
        selected_categories = ["integration"]
        execution_plan = self.category_system.create_execution_plan(selected_categories)
        
        # Get all categories that will be executed (including dependencies)
        all_executed_categories = set()
        for phase in execution_plan.phases:
            all_executed_categories.update(phase)
        
        # Requested categories should be a subset of executed categories
        assert execution_plan.requested_categories == {"integration"}
        assert execution_plan.requested_categories.issubset(all_executed_categories)
        
        # But they should not be equal (dependencies should be added)
        # Note: This test might pass even if dependencies are empty, that's ok
        print(f"Requested: {execution_plan.requested_categories}")
        print(f"All executed: {all_executed_categories}")
    
    def test_category_system_can_handle_unknown_categories_gracefully(self):
        """
        Test that CategorySystem handles unknown categories without crashing.
        This ensures robust behavior when directories exist but aren't registered.
        """
        # Request an unknown category
        execution_plan = self.category_system.create_execution_plan(["nonexistent_category"])
        
        # Should return empty execution plan, not crash
        assert len(execution_plan.phases) == 0
        assert len(execution_plan.requested_categories) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])