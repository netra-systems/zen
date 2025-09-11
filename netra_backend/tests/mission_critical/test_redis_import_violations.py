"""Mission Critical Test: Redis Import Violations Detection - Issue #226

This test suite detects Redis SSOT import violations and guides developers
toward proper SSOT compliance patterns.

Business Value:
- Prevents configuration cascade failures from inconsistent Redis usage
- Ensures Golden Path chat functionality uses consistent Redis implementation
- Reduces debugging time by enforcing single source of truth

Test Strategy:
- Static analysis of Python files for deprecated import patterns
- Detection of direct RedisManager() instantiation violations
- Validation that all Redis access goes through SSOT singleton
- Clear error messages guiding developers to correct imports

Expected Initial Result: FAIL (59 violations detected)
Expected Final Result: PASS (0 violations after migration)
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set
import pytest
import logging

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestRedisImportViolations(SSotBaseTestCase):
    """Test suite to detect and prevent Redis import violations."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Set up test data and scanning configuration."""
        self.project_root = Path(__file__).parent.parent.parent
        self.logger = logging.getLogger(__name__)
        
        # Deprecated import patterns to detect
        self.deprecated_patterns = [
            # Auth service deprecated imports
            r'from\s+auth_service\.auth_core\.redis_manager\s+import',
            r'import\s+auth_service\.auth_core\.redis_manager',
            
            # Cache deprecated imports  
            r'from\s+.*cache.*redis.*manager\s+import',
            r'from\s+netra_backend\.app\.cache\.redis_cache_manager\s+import',
            
            # Test framework deprecated imports
            r'from\s+test_framework\.redis_test_utils\.test_redis_manager\s+import',
            
            # Direct manager imports (should use singleton)
            r'from\s+.*\.managers\.redis_manager\s+import',
            r'from\s+.*\.db\.redis_manager\s+import',
        ]
        
        # Direct instantiation patterns to detect
        self.instantiation_patterns = [
            r'RedisManager\(\)',
            r'RedisManager\(\s*[^)]*\)',  # With arguments
            r'AuthRedisManager\(\)',
            r'RedisCacheManager\(\)',
            r'RedisTestManager\(\)',
        ]
        
        # Correct SSOT import pattern
        self.correct_import = "from netra_backend.app.redis_manager import redis_manager"
        
        # Files to exclude from scanning (generated, external, etc.)
        self.exclude_patterns = [
            '__pycache__',
            '.pyc',
            'node_modules',
            '.git',
            'venv',
            '.env',
            'migrations/',
        ]

    def test_no_deprecated_redis_imports(self):
        """Test that no files use deprecated Redis import patterns.
        
        This test scans all Python files for deprecated Redis import patterns
        and provides specific guidance on converting to SSOT imports.
        
        Expected Initial Result: FAIL (33+ deprecated import violations)
        Expected Final Result: PASS (0 violations after migration)
        """
        violations = self._scan_for_deprecated_imports()
        
        if violations:
            violation_message = self._format_violation_message(
                violations,
                "Deprecated Redis Import Violations Detected",
                f"Use SSOT import: {self.correct_import}"
            )
            
            # Log violations for debugging
            self.logger.critical(f"Redis import violations detected: {len(violations)} files affected")
            for file_path, line_num, pattern, line_content in violations:
                self.logger.warning(f"Violation in {file_path}:{line_num} - {pattern}")
            
            pytest.fail(violation_message)

    def test_no_direct_redis_manager_instantiation(self):
        """Test that no files directly instantiate RedisManager().
        
        This test detects direct instantiation of Redis manager classes,
        which violates SSOT principle and can cause connection inconsistencies.
        
        Expected Initial Result: FAIL (26+ direct instantiation violations)  
        Expected Final Result: PASS (0 violations after migration)
        """
        violations = self._scan_for_direct_instantiation()
        
        if violations:
            violation_message = self._format_instantiation_violation_message(violations)
            
            # Log violations for debugging
            self.logger.critical(f"Direct RedisManager instantiation violations: {len(violations)} instances")
            for file_path, line_num, pattern, line_content in violations:
                self.logger.warning(f"Direct instantiation in {file_path}:{line_num} - {pattern}")
            
            pytest.fail(violation_message)

    def test_no_multiple_redis_manager_instances(self):
        """Test that Redis manager maintains singleton pattern.
        
        Validates that all Redis access goes through the same singleton instance
        to prevent connection pooling issues and configuration inconsistencies.
        
        Expected Initial Result: PASS (singleton works, imports wrong)
        Expected Final Result: PASS (singleton works, imports correct)
        """
        # Test that the SSOT redis_manager is accessible
        try:
            from netra_backend.app.redis_manager import redis_manager
            assert redis_manager is not None, "SSOT redis_manager should be available"
            
            # Test that multiple imports return same instance
            from netra_backend.app.redis_manager import redis_manager as rm1
            from netra_backend.app.redis_manager import redis_manager as rm2
            
            assert rm1 is rm2, "Multiple imports should return same redis_manager instance"
            assert rm1 is redis_manager, "All redis_manager references should be identical"
            
        except ImportError as e:
            pytest.fail(f"SSOT redis_manager import failed: {e}")

    def test_compliance_progress_tracking(self):
        """Test that tracks compliance progress for issue #226.
        
        This test provides metrics on violation reduction progress
        and ensures we're moving toward zero violations.
        """
        deprecated_violations = self._scan_for_deprecated_imports()
        instantiation_violations = self._scan_for_direct_instantiation()
        
        total_violations = len(deprecated_violations) + len(instantiation_violations)
        
        # Track progress (this will initially fail with 59 violations)
        baseline_violations = 59  # Known violation count from issue analysis
        
        progress_message = (
            f"Redis SSOT Compliance Progress:\n"
            f"  Deprecated Imports: {len(deprecated_violations)}\n"
            f"  Direct Instantiations: {len(instantiation_violations)}\n"
            f"  Total Violations: {total_violations}\n"
            f"  Baseline: {baseline_violations}\n"
            f"  Progress: {baseline_violations - total_violations} violations resolved\n"
        )
        
        self.logger.info(progress_message)
        
        # This assertion will initially fail, providing clear progress tracking
        assert total_violations == 0, (
            f"Redis SSOT migration incomplete. {progress_message}\n"
            f"See issue #226 for migration guidance."
        )

    def _scan_for_deprecated_imports(self) -> List[Tuple[str, int, str, str]]:
        """Scan for deprecated Redis import patterns.
        
        Returns:
            List of (file_path, line_number, pattern_matched, line_content)
        """
        violations = []
        
        for python_file in self._get_python_files():
            violations.extend(self._scan_file_for_patterns(
                python_file, 
                self.deprecated_patterns,
                "deprecated_import"
            ))
        
        return violations

    def _scan_for_direct_instantiation(self) -> List[Tuple[str, int, str, str]]:
        """Scan for direct Redis manager instantiation patterns.
        
        Returns:
            List of (file_path, line_number, pattern_matched, line_content)
        """
        violations = []
        
        for python_file in self._get_python_files():
            violations.extend(self._scan_file_for_patterns(
                python_file,
                self.instantiation_patterns, 
                "direct_instantiation"
            ))
        
        return violations

    def _get_python_files(self) -> List[Path]:
        """Get all Python files to scan, excluding patterns."""
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                pattern in os.path.join(root, d) for pattern in self.exclude_patterns
            )]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    
                    # Skip excluded files
                    if not any(pattern in str(file_path) for pattern in self.exclude_patterns):
                        python_files.append(file_path)
        
        return python_files

    def _scan_file_for_patterns(self, file_path: Path, patterns: List[str], violation_type: str) -> List[Tuple[str, int, str, str]]:
        """Scan a single file for pattern violations.
        
        Args:
            file_path: Path to Python file to scan
            patterns: List of regex patterns to match
            violation_type: Type of violation for reporting
            
        Returns:
            List of (file_path, line_number, pattern_matched, line_content)
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                for pattern in patterns:
                    if re.search(pattern, line_stripped):
                        rel_path = str(file_path.relative_to(self.project_root))
                        violations.append((
                            rel_path,
                            line_num, 
                            pattern,
                            line_stripped
                        ))
                        
        except (IOError, UnicodeDecodeError) as e:
            self.logger.warning(f"Could not scan file {file_path}: {e}")
            
        return violations

    def _format_violation_message(self, violations: List[Tuple[str, int, str, str]], title: str, guidance: str) -> str:
        """Format violation message with clear guidance."""
        message_parts = [
            f"\n{'='*60}",
            f"{title}",
            f"{'='*60}",
            f"\nFound {len(violations)} Redis import violations:\n",
        ]
        
        # Group violations by file for clearer presentation
        violations_by_file = {}
        for file_path, line_num, pattern, line_content in violations:
            if file_path not in violations_by_file:
                violations_by_file[file_path] = []
            violations_by_file[file_path].append((line_num, pattern, line_content))
        
        for file_path, file_violations in sorted(violations_by_file.items()):
            message_parts.append(f"\n📁 {file_path}")
            for line_num, pattern, line_content in file_violations:
                message_parts.append(f"  ❌ Line {line_num}: {line_content}")
                
        message_parts.extend([
            f"\n{'='*60}",
            f"SOLUTION:",
            f"{'='*60}",
            f"{guidance}",
            f"\nExample correct usage:",
            f"  {self.correct_import}",
            f"  # Then use: redis_manager.get(), redis_manager.set(), etc.",
            f"\nSee issue #226 for complete migration guidance.",
            f"{'='*60}\n"
        ])
        
        return "\n".join(message_parts)

    def _format_instantiation_violation_message(self, violations: List[Tuple[str, int, str, str]]) -> str:
        """Format direct instantiation violation message."""
        return self._format_violation_message(
            violations,
            "Direct RedisManager() Instantiation Violations Detected", 
            f"Use singleton: {self.correct_import}"
        )