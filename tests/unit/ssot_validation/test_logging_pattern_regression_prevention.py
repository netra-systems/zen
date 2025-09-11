"""
SSOT LOGGING REGRESSION PREVENTION TEST
=======================================

PURPOSE: Prevent future mixing of logging patterns in Golden Path execution chain.
Provides ongoing protection against SSOT logging violations that could break
correlation tracking for $500K+ ARR customer debugging capabilities.

REGRESSION SCENARIOS COVERED:
1. New files accidentally using legacy logging
2. Existing files reverting to mixed patterns
3. Import statements being modified incorrectly
4. Logger variable naming inconsistencies
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Set

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestLoggingPatternRegressionPrevention(SSotBaseTestCase):
    """
    Prevent future mixing of logging patterns in Golden Path.
    
    Ongoing protection against SSOT violations affecting Golden Path debugging.
    """
    
    def setUp(self):
        super().setUp()
        
        # Define critical Golden Path files that must use SSOT logging
        self.critical_golden_path_files = [
            'netra_backend/app/agents/supervisor/agent_execution_core.py',
            'netra_backend/app/core/agent_execution_tracker.py',
            'netra_backend/app/agents/supervisor/workflow_orchestrator.py',
            'netra_backend/app/agents/supervisor/execution_engine.py',
            'netra_backend/app/websocket_core/unified_manager.py',
            'netra_backend/app/services/agent_websocket_bridge.py'
        ]
        
        # SSOT logging patterns (approved)
        self.ssot_patterns = {
            'import': 'from netra_backend.app.logging_config import central_logger',
            'logger_creation': 'logger = central_logger.get_logger(__name__)',
            'alternative_creation': 'central_logger.get_logger('
        }
        
        # Legacy patterns (forbidden)
        self.legacy_patterns = {
            'import_logging': r'import logging\b',
            'from_logging': r'from logging import',
            'logging_getlogger': r'logging\.getLogger\(',
            'direct_logger_assignment': r'logger = logging\.getLogger\('
        }
        
        self.project_root = Path(__file__).parent.parent.parent.parent
        
    def test_critical_golden_path_files_use_ssot_logging(self):
        """
        Ensures all critical Golden Path files use SSOT central_logger pattern.
        
        REGRESSION PROTECTION: Prevents accidental reversion to legacy logging
        in files that are critical for Golden Path correlation tracking.
        """
        violations = []
        
        for file_path in self.critical_golden_path_files:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                violations.append(f"CRITICAL FILE MISSING: {file_path}")
                continue
                
            file_violations = self._check_file_ssot_compliance(full_path, file_path)
            if file_violations:
                violations.extend(file_violations)
        
        self.assertEqual(
            len(violations), 0,
            f"GOLDEN PATH LOGGING REGRESSION DETECTED: Critical files have SSOT logging violations: "
            f"{violations}. All Golden Path files must use 'central_logger.get_logger()' "
            f"to maintain correlation tracking for $500K+ ARR customer debugging support."
        )
        
        print(f"✅ REGRESSION PROTECTION: All {len(self.critical_golden_path_files)} critical Golden Path files use SSOT logging")
        
    def test_no_new_legacy_logging_introduced(self):
        """
        Scans for any new files in Golden Path areas that might introduce legacy logging.
        
        REGRESSION PROTECTION: Prevents new development from accidentally
        introducing legacy logging patterns in Golden Path areas.
        """
        golden_path_directories = [
            'netra_backend/app/agents',
            'netra_backend/app/core',
            'netra_backend/app/websocket_core',
            'netra_backend/app/services'
        ]
        
        new_legacy_violations = []
        
        for directory in golden_path_directories:
            dir_path = self.project_root / directory
            if not dir_path.exists():
                continue
                
            # Scan all Python files in directory
            for py_file in dir_path.rglob('*.py'):
                if py_file.name.startswith('test_'):
                    continue  # Skip test files
                    
                file_violations = self._check_file_for_legacy_patterns(py_file)
                if file_violations:
                    relative_path = py_file.relative_to(self.project_root)
                    new_legacy_violations.append({
                        'file': str(relative_path),
                        'violations': file_violations
                    })
        
        self.assertEqual(
            len(new_legacy_violations), 0,
            f"NEW LEGACY LOGGING DETECTED: Found files with legacy logging patterns "
            f"in Golden Path directories: {new_legacy_violations}. "
            f"All new Golden Path files must use SSOT central_logger pattern "
            f"to maintain unified correlation tracking."
        )
        
        print("✅ NO NEW LEGACY LOGGING: All Golden Path files use approved SSOT patterns")
        
    def test_import_statement_integrity(self):
        """
        Validates that SSOT logging import statements remain intact and unmodified.
        
        REGRESSION PROTECTION: Prevents accidental modification of critical
        import statements that enable SSOT logging functionality.
        """
        import_violations = []
        
        for file_path in self.critical_golden_path_files:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for correct SSOT import
                has_correct_import = self.ssot_patterns['import'] in content
                
                # Check for incorrect imports
                has_legacy_import = bool(re.search(self.legacy_patterns['import_logging'], content))
                has_from_logging = bool(re.search(self.legacy_patterns['from_logging'], content))
                
                if not has_correct_import:
                    import_violations.append(f"{file_path}: Missing SSOT import '{self.ssot_patterns['import']}'")
                
                if has_legacy_import:
                    import_violations.append(f"{file_path}: Contains legacy 'import logging' pattern")
                
                if has_from_logging:
                    import_violations.append(f"{file_path}: Contains legacy 'from logging import' pattern")
                    
            except Exception as e:
                import_violations.append(f"{file_path}: Could not analyze imports - {e}")
        
        self.assertEqual(
            len(import_violations), 0,
            f"IMPORT STATEMENT REGRESSION: Critical files have incorrect logging imports: "
            f"{import_violations}. All files must import central_logger correctly "
            f"for Golden Path correlation tracking integrity."
        )
        
        print("✅ IMPORT INTEGRITY: All critical files have correct SSOT logging imports")
        
    def test_logger_variable_consistency_maintained(self):
        """
        Ensures consistent logger variable naming across all Golden Path files.
        
        REGRESSION PROTECTION: Prevents inconsistent logger variable naming
        that could break correlation patterns or cause confusion.
        """
        naming_violations = []
        
        for file_path in self.critical_golden_path_files:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for standard logger variable assignment
                has_standard_naming = self.ssot_patterns['logger_creation'] in content
                
                # Check for non-standard logger variable names
                non_standard_patterns = [
                    r'log = central_logger\.get_logger\(',
                    r'_logger = central_logger\.get_logger\(',
                    r'app_logger = central_logger\.get_logger\(',
                    r'module_logger = central_logger\.get_logger\('
                ]
                
                non_standard_found = []
                for pattern in non_standard_patterns:
                    if re.search(pattern, content):
                        non_standard_found.append(pattern)
                
                if not has_standard_naming and 'central_logger.get_logger(' in content:
                    naming_violations.append(f"{file_path}: Uses non-standard logger variable naming (should be 'logger = central_logger.get_logger(__name__)')")
                
                if non_standard_found:
                    naming_violations.append(f"{file_path}: Uses non-standard logger variable names: {non_standard_found}")
                    
            except Exception as e:
                naming_violations.append(f"{file_path}: Could not analyze logger naming - {e}")
        
        self.assertEqual(
            len(naming_violations), 0,
            f"LOGGER NAMING REGRESSION: Inconsistent logger variable naming detected: "
            f"{naming_violations}. All files should use 'logger = central_logger.get_logger(__name__)' "
            f"for consistency in Golden Path correlation tracking."
        )
        
        print("✅ NAMING CONSISTENCY: All critical files use standard logger variable naming")
        
    def test_logging_call_patterns_remain_consistent(self):
        """
        Validates that logging calls use the consistent 'logger.' prefix pattern.
        
        REGRESSION PROTECTION: Prevents mixed logging call patterns that could
        break correlation context or create debugging confusion.
        """
        call_pattern_violations = []
        
        for file_path in self.critical_golden_path_files:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for direct logging module calls (forbidden after SSOT migration)
                direct_logging_calls = re.findall(r'logging\.(info|debug|warning|error|critical)\(', content)
                
                if direct_logging_calls:
                    call_pattern_violations.append(
                        f"{file_path}: Contains direct logging calls: {set(direct_logging_calls)}. "
                        f"Should use 'logger.{'{method}'}()' pattern instead."
                    )
                    
            except Exception as e:
                call_pattern_violations.append(f"{file_path}: Could not analyze logging calls - {e}")
        
        self.assertEqual(
            len(call_pattern_violations), 0,
            f"LOGGING CALL REGRESSION: Inconsistent logging call patterns detected: "
            f"{call_pattern_violations}. All logging should use 'logger.' prefix "
            f"for unified Golden Path correlation tracking."
        )
        
        print("✅ CALL PATTERN CONSISTENCY: All critical files use consistent logging call patterns")
        
    def _check_file_ssot_compliance(self, file_path: Path, relative_path: str) -> List[str]:
        """Check if file complies with SSOT logging requirements."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Must have SSOT import
            if self.ssot_patterns['import'] not in content:
                violations.append(f"{relative_path}: Missing SSOT import")
            
            # Must have proper logger creation
            has_proper_logger = (
                self.ssot_patterns['logger_creation'] in content or
                self.ssot_patterns['alternative_creation'] in content
            )
            if not has_proper_logger:
                violations.append(f"{relative_path}: Missing SSOT logger creation")
            
            # Must not have legacy patterns
            for pattern_name, pattern in self.legacy_patterns.items():
                if re.search(pattern, content):
                    violations.append(f"{relative_path}: Contains legacy pattern '{pattern_name}'")
                    
        except Exception as e:
            violations.append(f"{relative_path}: Analysis error - {e}")
        
        return violations
    
    def _check_file_for_legacy_patterns(self, file_path: Path) -> List[str]:
        """Check if file contains any legacy logging patterns."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern_name, pattern in self.legacy_patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(f"Legacy pattern '{pattern_name}': {matches}")
                    
        except Exception as e:
            violations.append(f"Analysis error: {e}")
        
        return violations


if __name__ == '__main__':
    import unittest
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLoggingPatternRegressionPrevention)
    runner = unittest.TextTestRunner(verbosity=2)
    
    result = runner.run(suite)
    if result.failures or result.errors:
        print("\n🚨 REGRESSION DETECTED: Some logging patterns need attention")
        print("Review failures above and ensure all Golden Path files use SSOT logging")
    else:
        print("\n✅ REGRESSION PROTECTION PASSED: All Golden Path files maintain SSOT logging compliance")