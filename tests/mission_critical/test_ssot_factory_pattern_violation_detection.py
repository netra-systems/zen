"""
SSOT Factory Pattern Violation Detection Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent SSOT violations that break multi-user isolation
- Value Impact: Catch direct instantiation that bypasses factory pattern and causes user context bleeding
- Strategic Impact: $500K+ ARR depends on reliable user isolation in chat functionality

CRITICAL: These tests are designed to FAIL when factory pattern is bypassed,
and PASS when proper StateManagerFactory usage is enforced.

Related Issue: GitHub #207 - SSOT violation in test_type_ssot_thread_state_manager_coordination.py:49
Target Violation: Direct UnifiedStateManager() instantiation bypassing StateManagerFactory

PURPOSE: Detect and prevent SSOT violations that compromise user isolation.
"""

import pytest
import ast
import os
import re
import unittest
from pathlib import Path
from typing import List, Dict, Any, Set


class TestSSotFactoryPatternViolationDetection(unittest.TestCase):
    """Tests that detect SSOT factory pattern violations in codebase."""
    
    def __init__(self, *args, **kwargs):
        """Initialize test with repo root path."""
        super().__init__(*args, **kwargs)
        self.repo_root = Path("/Users/anthony/Desktop/netra-apex")
        self.known_violations = {
            # Known violation from GitHub issue #207
            "/tests/integration/type_ssot/test_type_ssot_thread_state_manager_coordination.py": [49]
        }
    
    @pytest.mark.mission_critical
    def test_detect_direct_unified_state_manager_instantiation(self):
        """
        Test that detects direct UnifiedStateManager() instantiation violations.
        
        CRITICAL: This test should FAIL before fix (catches violation),
        PASS after fix (validates remediation).
        
        Known violation: Line 49 in test_type_ssot_thread_state_manager_coordination.py
        """
        violations = self._scan_for_direct_instantiation_violations()
        
        # Log detected violations for analysis
        for file_path, line_numbers in violations.items():
            for line_num in line_numbers:
                print(f"VIOLATION DETECTED: {file_path}:{line_num} - Direct UnifiedStateManager instantiation")
        
        # CRITICAL: This assertion should FAIL with current known violation
        # After fix, this should PASS (no violations found)
        assert len(violations) == 0, (
            f"SSOT Violation: Found {len(violations)} files with direct UnifiedStateManager() instantiation. "
            f"Use StateManagerFactory.get_global_manager() or StateManagerFactory.get_user_manager(user_id) instead. "
            f"Violations: {dict(violations)}"
        )
    
    @pytest.mark.mission_critical
    def test_validate_factory_pattern_enforcement_in_tests(self):
        """
        Test that validates proper factory pattern usage in test files.
        
        CRITICAL: Ensures ALL test files use StateManagerFactory for user isolation.
        """
        test_files = self._get_test_files_using_unified_state_manager()
        violations = []
        
        for test_file in test_files:
            if self._file_has_direct_instantiation(test_file):
                violations.append(test_file)
        
        # Log violations for debugging
        for violation in violations:
            print(f"TEST VIOLATION: {violation} uses direct UnifiedStateManager() instantiation")
        
        # This should FAIL with current violation, PASS after fix
        assert len(violations) == 0, (
            f"Test files must use StateManagerFactory pattern for user isolation. "
            f"Found {len(violations)} test files with violations: {violations}"
        )
    
    @pytest.mark.mission_critical
    def test_ssot_compliance_user_isolation_validation(self):
        """
        Test that validates SSOT compliance for user isolation via factory pattern.
        
        CRITICAL: Ensures factory pattern creates isolated instances per user.
        """
        # Import required classes
        try:
            from netra_backend.app.core.managers.unified_state_manager import (
                StateManagerFactory, UnifiedStateManager
            )
        except ImportError:
            pytest.skip("UnifiedStateManager not available")
        
        # Test factory creates different instances for different users
        user1_manager = StateManagerFactory.get_user_manager("test_user_1")
        user2_manager = StateManagerFactory.get_user_manager("test_user_2")
        global_manager = StateManagerFactory.get_global_manager()
        
        # Validate instances are different (proper isolation)
        assert user1_manager is not user2_manager, (
            "Different users must get different state manager instances"
        )
        assert user1_manager is not global_manager, (
            "User manager must be different from global manager"
        )
        assert user2_manager is not global_manager, (
            "User manager must be different from global manager"
        )
        
        # Validate user IDs are set correctly
        assert user1_manager.user_id == "test_user_1", (
            "User manager must have correct user_id"
        )
        assert user2_manager.user_id == "test_user_2", (
            "User manager must have correct user_id"
        )
        assert global_manager.user_id is None, (
            "Global manager must have no user_id"
        )
        
        # Test state isolation
        user1_manager.set("test_key", "user1_value")
        user2_manager.set("test_key", "user2_value")
        global_manager.set("test_key", "global_value")
        
        # Validate values are isolated
        assert user1_manager.get("test_key") == "user1_value"
        assert user2_manager.get("test_key") == "user2_value"
        assert global_manager.get("test_key") == "global_value"
    
    @pytest.mark.mission_critical
    async def test_factory_pattern_with_real_services_integration(self, real_services_fixture):
        """
        Test factory pattern compliance with real services integration.
        
        CRITICAL: Validates factory pattern works correctly with real database and cache.
        """
        # Import required classes
        try:
            from netra_backend.app.core.managers.unified_state_manager import StateManagerFactory
        except ImportError:
            pytest.skip("StateManagerFactory not available")
        
        # Get real services
        redis_client = real_services_fixture.get('redis')
        if not redis_client:
            pytest.skip("Real Redis service not available")
        
        # Test with different users using factory pattern
        user1_manager = StateManagerFactory.get_user_manager("real_test_user_1")
        user2_manager = StateManagerFactory.get_user_manager("real_test_user_2")
        
        # Set values that will be stored in real Redis
        await user1_manager.set_async("real_test_key", {"user": "user1", "data": "sensitive_data_1"})
        await user2_manager.set_async("real_test_key", {"user": "user2", "data": "sensitive_data_2"})
        
        # Validate isolation with real services
        user1_data = await user1_manager.get_async("real_test_key")
        user2_data = await user2_manager.get_async("real_test_key")
        
        assert user1_data["user"] == "user1", "User 1 must only see their own data"
        assert user2_data["user"] == "user2", "User 2 must only see their own data"
        assert user1_data["data"] != user2_data["data"], "User data must be isolated"
        
        # Cleanup
        await user1_manager.delete_async("real_test_key")
        await user2_manager.delete_async("real_test_key")
    
    def _scan_for_direct_instantiation_violations(self) -> Dict[str, List[int]]:
        """
        Scan codebase for direct UnifiedStateManager() instantiation violations.
        
        Returns:
            Dict mapping file paths to line numbers with violations
        """
        violations = {}
        
        # Scan Python files for direct instantiation pattern
        for file_path in self._get_python_files():
            line_numbers = self._find_direct_instantiation_lines(file_path)
            if line_numbers:
                # Convert to relative path for reporting
                relative_path = str(file_path.relative_to(self.repo_root))
                violations[relative_path] = line_numbers
        
        return violations
    
    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the repository."""
        python_files = []
        
        # Search in key directories
        search_dirs = [
            self.repo_root / "netra_backend",
            self.repo_root / "tests",
            self.repo_root / "auth_service",
            self.repo_root / "shared"
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                python_files.extend(search_dir.rglob("*.py"))
        
        return python_files
    
    def _find_direct_instantiation_lines(self, file_path: Path) -> List[int]:
        """
        Find line numbers with direct UnifiedStateManager() instantiation.
        
        Args:
            file_path: Path to Python file to scan
            
        Returns:
            List of line numbers with violations
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Look for direct instantiation pattern
                if self._is_direct_instantiation_line(line):
                    violations.append(line_num)
        
        except (IOError, UnicodeDecodeError):
            # Skip files that can't be read
            pass
        
        return violations
    
    def _is_direct_instantiation_line(self, line: str) -> bool:
        """
        Check if line contains direct UnifiedStateManager instantiation.
        
        Args:
            line: Line of code to check
            
        Returns:
            True if line contains violation
        """
        # Remove comments and strings to avoid false positives
        line = re.sub(r'#.*$', '', line)  # Remove comments
        line = re.sub(r'""".*?"""', '', line, flags=re.DOTALL)  # Remove docstrings
        line = re.sub(r"'''.*?'''", '', line, flags=re.DOTALL)  # Remove docstrings
        line = re.sub(r'"[^"]*"', '', line)  # Remove double-quoted strings
        line = re.sub(r"'[^']*'", '', line)  # Remove single-quoted strings
        
        # Look for direct instantiation patterns
        patterns = [
            r'\bUnifiedStateManager\s*\(\s*\)',  # UnifiedStateManager()
            r'\bstate_manager\s*=\s*UnifiedStateManager\s*\(',  # assignment
            r'\breturn\s+UnifiedStateManager\s*\(',  # return statement
        ]
        
        for pattern in patterns:
            if re.search(pattern, line):
                return True
        
        return False
    
    def _get_test_files_using_unified_state_manager(self) -> List[Path]:
        """Get test files that import or use UnifiedStateManager."""
        test_files = []
        
        test_dirs = [
            self.repo_root / "tests",
            self.repo_root / "netra_backend" / "tests"
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                for test_file in test_dir.rglob("*.py"):
                    if self._file_uses_unified_state_manager(test_file):
                        test_files.append(test_file)
        
        return test_files
    
    def _file_uses_unified_state_manager(self, file_path: Path) -> bool:
        """Check if file imports or uses UnifiedStateManager."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for imports or usage
            patterns = [
                r'from.*unified_state_manager.*import.*UnifiedStateManager',
                r'import.*unified_state_manager',
                r'\bUnifiedStateManager\b'
            ]
            
            for pattern in patterns:
                if re.search(pattern, content):
                    return True
            
            return False
        
        except (IOError, UnicodeDecodeError):
            return False
    
    def _file_has_direct_instantiation(self, file_path: Path) -> bool:
        """Check if file has direct UnifiedStateManager instantiation."""
        line_numbers = self._find_direct_instantiation_lines(file_path)
        return len(line_numbers) > 0


class TestSSotFactoryPatternRegressionPrevention(unittest.TestCase):
    """Tests that prevent regression of factory pattern violations."""
    
    def __init__(self, *args, **kwargs):
        """Initialize test with repo root path."""
        super().__init__(*args, **kwargs)
        self.repo_root = Path("/Users/anthony/Desktop/netra-apex")
    
    @pytest.mark.mission_critical
    def test_prevent_direct_instantiation_in_new_code(self):
        """
        Test that prevents new direct instantiation violations from being introduced.
        
        CRITICAL: This is a regression prevention test that should always PASS
        after the initial violation is fixed.
        """
        # Import check - this should work without direct instantiation
        try:
            from netra_backend.app.core.managers.unified_state_manager import (
                StateManagerFactory,
                get_state_manager  # Convenience function that uses factory
            )
        except ImportError:
            pytest.skip("UnifiedStateManager module not available")
        
        # Test that convenience functions use factory pattern
        global_manager = get_state_manager()  # Should use factory
        user_manager = get_state_manager("test_user")  # Should use factory
        
        # Validate they are proper instances
        assert hasattr(global_manager, 'user_id'), "Manager must have user_id attribute"
        assert hasattr(user_manager, 'user_id'), "Manager must have user_id attribute"
        assert global_manager.user_id is None, "Global manager should have no user_id"
        assert user_manager.user_id == "test_user", "User manager should have correct user_id"
    
    @pytest.mark.mission_critical
    def test_factory_pattern_documentation_compliance(self):
        """
        Test that validates factory pattern is properly documented and enforced.
        
        CRITICAL: Ensures factory pattern requirements are clear for developers.
        """
        # Check that StateManagerFactory exists and has required methods
        try:
            from netra_backend.app.core.managers.unified_state_manager import StateManagerFactory
        except ImportError:
            pytest.fail("StateManagerFactory must be available for SSOT compliance")
        
        # Validate required factory methods exist
        required_methods = [
            'get_global_manager',
            'get_user_manager',
            'shutdown_all_managers',
            'get_manager_count'
        ]
        
        for method_name in required_methods:
            assert hasattr(StateManagerFactory, method_name), (
                f"StateManagerFactory must have {method_name} method for SSOT compliance"
            )
            assert callable(getattr(StateManagerFactory, method_name)), (
                f"StateManagerFactory.{method_name} must be callable"
            )
        
        # Test factory methods work correctly
        global_manager = StateManagerFactory.get_global_manager()
        user_manager = StateManagerFactory.get_user_manager("compliance_test_user")
        
        assert global_manager is not None, "Factory must create global manager"
        assert user_manager is not None, "Factory must create user manager"
        assert global_manager is not user_manager, "Factory must create different instances"
    
    @pytest.mark.mission_critical
    def test_known_violation_specific_detection(self):
        """
        Test that specifically detects the known violation in GitHub issue #207.
        
        CRITICAL: This test targets the exact file and line number from the issue.
        """
        violation_file = self.repo_root / "tests/integration/type_ssot/test_type_ssot_thread_state_manager_coordination.py"
        violation_line = 49
        
        if not violation_file.exists():
            pytest.skip(f"Target violation file does not exist: {violation_file}")
        
        # Read the specific line
        try:
            with open(violation_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if len(lines) < violation_line:
                pytest.skip(f"File does not have line {violation_line}")
            
            target_line = lines[violation_line - 1]  # Convert to 0-based index
            
            # Check if the line contains direct instantiation
            has_violation = self._is_direct_instantiation_line(target_line)
            
            # Log the line for debugging
            print(f"Checking line {violation_line}: {target_line.strip()}")
            print(f"Contains violation: {has_violation}")
            
            # This should FAIL before fix (violation exists), PASS after fix (violation removed)
            assert not has_violation, (
                f"Line {violation_line} in {violation_file} contains direct UnifiedStateManager() instantiation. "
                f"Use StateManagerFactory.get_global_manager() or StateManagerFactory.get_user_manager(user_id) instead. "
                f"Line content: {target_line.strip()}"
            )
        
        except (IOError, UnicodeDecodeError) as e:
            pytest.fail(f"Could not read violation file: {e}")
    
    def _is_direct_instantiation_line(self, line: str) -> bool:
        """
        Check if line contains direct UnifiedStateManager instantiation.
        
        Args:
            line: Line of code to check
            
        Returns:
            True if line contains violation
        """
        # Remove comments and strings to avoid false positives
        line = re.sub(r'#.*$', '', line)  # Remove comments
        line = re.sub(r'""".*?"""', '', line, flags=re.DOTALL)  # Remove docstrings
        line = re.sub(r"'''.*?'''", '', line, flags=re.DOTALL)  # Remove docstrings
        line = re.sub(r'"[^"]*"', '', line)  # Remove double-quoted strings
        line = re.sub(r"'[^']*'", '', line)  # Remove single-quoted strings
        
        # Look for direct instantiation patterns
        patterns = [
            r'\bUnifiedStateManager\s*\(\s*\)',  # UnifiedStateManager()
            r'\bstate_manager\s*=\s*UnifiedStateManager\s*\(',  # assignment
            r'\breturn\s+UnifiedStateManager\s*\(',  # return statement
        ]
        
        for pattern in patterns:
            if re.search(pattern, line):
                return True
        
        return False