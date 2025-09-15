"""
Test for WebSocket Authentication SSOT Violation: Deprecated Function Usage Detection

BUSINESS IMPACT: $500K+ ARR - WebSocket authentication chaos blocking Golden Path  
ISSUE: #1076 - 124+ usages of deprecated authenticate_websocket_connection() function

This test SHOULD FAIL INITIALLY (detecting deprecated function usage) and PASS AFTER REMEDIATION.

SSOT Gardener Step 2.2: Detect usage of deprecated authenticate_websocket_connection() function.
Expected to find ~124 usages across the codebase that need migration to authenticate_websocket_ssot().

Expected Test Behavior:
- FAILS NOW: Deprecated function usage detected in multiple files
- PASSES AFTER: All usage migrated to authenticate_websocket_ssot()
"""

import os
import re
import unittest
from pathlib import Path
from typing import Dict, List, Set, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestDeprecatedFunctionUsageDetection(SSotAsyncTestCase, unittest.TestCase):
    """
    Mission Critical Test: Deprecated WebSocket Authentication Function Detection
    
    Scans the codebase for usage of deprecated authenticate_websocket_connection() function
    and ensures migration to SSOT authenticate_websocket_ssot() function.
    """
    
    def setUp(self):
        """Set up test environment for deprecated function usage detection."""
        super().setUp()
        self.project_root = r"C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1"
        self.deprecated_function = "authenticate_websocket_connection"
        self.ssot_function = "authenticate_websocket_ssot"
        self.scan_patterns = [
            "**/*.py"
        ]
        self.exclude_patterns = [
            "**/node_modules/**",
            "**/.git/**",
            "**/venv/**",
            "**/__pycache__/**",
            "**/test_deprecated_function_usage_detection.py"  # Exclude this test file
        ]

    @property
    def test_metadata(self) -> Dict[str, Any]:
        """Access test metadata through context."""
        if not hasattr(self, '_test_metadata'):
            self._test_metadata = {}
        return self._test_metadata

    def test_no_deprecated_websocket_auth_function_usage(self):
        """
        CRITICAL TEST: Should FAIL currently - finds deprecated function usage in codebase.
        
        This test scans the entire codebase for authenticate_websocket_connection() usage
        and should FAIL now because ~124 usages exist, and PASS after migration to 
        authenticate_websocket_ssot().
        
        Business Impact: Prevents authentication chaos that blocks Golden Path
        """
        # Scan codebase for deprecated function usage
        usage_report = self._scan_for_deprecated_usage()
        
        # Log detailed findings
        self._log_usage_analysis(usage_report)
        
        # CRITICAL ASSERTION: Should FAIL now (usage found), PASS after migration (no usage)
        self.assertEqual(len(usage_report['files_with_usage']), 0,
                        f"SSOT VIOLATION DETECTED: Found deprecated function usage in "
                        f"{len(usage_report['files_with_usage'])} files "
                        f"({usage_report['total_occurrences']} total occurrences). "
                        f"Files: {list(usage_report['files_with_usage'].keys())[:10]}... "
                        f"All usage must migrate to '{self.ssot_function}()' for SSOT compliance.")
    
    def test_ssot_function_usage_exists(self):
        """
        SUPPORTING TEST: Verify that the SSOT function is being used in the codebase.
        
        This test ensures that authenticate_websocket_ssot() is actually being used,
        indicating proper SSOT migration is in progress or complete.
        """
        # Scan for SSOT function usage
        ssot_usage = self._scan_for_ssot_usage()
        
        self.logger.info(f"SSOT USAGE: Found {ssot_usage['total_occurrences']} usages "
                        f"of '{self.ssot_function}' in {len(ssot_usage['files_with_usage'])} files")
        
        # Log some examples of proper SSOT usage
        for file_path, occurrences in list(ssot_usage['files_with_usage'].items())[:5]:
            self.logger.info(f"SSOT EXAMPLE: {file_path} has {len(occurrences)} usages")
        
        # SSOT function should be used (even if deprecated function still exists)
        # This test passes if ANY usage of SSOT function is found
        self.assertGreater(ssot_usage['total_occurrences'], 0,
                          f"SSOT function '{self.ssot_function}' not found in codebase. "
                          f"This indicates SSOT migration has not begun.")
    
    def test_migration_progress_indicators(self):
        """
        PROGRESS TEST: Check for migration indicators like deprecation warnings.
        
        This test looks for evidence that migration from deprecated to SSOT function
        is in progress, such as deprecation warnings or migration comments.
        """
        migration_indicators = self._scan_for_migration_indicators()
        
        self.logger.info(f"MIGRATION PROGRESS: Found {len(migration_indicators['deprecation_warnings'])} "
                        f"deprecation warnings and {len(migration_indicators['migration_comments'])} "
                        f"migration comments")
        
        # Record migration progress in test metadata
        self.test_metadata.update({
            "migration_deprecation_warnings": len(migration_indicators['deprecation_warnings']),
            "migration_comments": len(migration_indicators['migration_comments']),
            "backward_compatibility_wrappers": len(migration_indicators['compatibility_wrappers'])
        })
        
        # This test is informational - always passes but tracks migration progress
        self.assertTrue(True, "Migration progress indicators scanned successfully")
    
    def test_test_files_deprecated_usage_isolation(self):
        """
        TEST ISOLATION: Check if deprecated usage is mainly in test files vs production code.
        
        This test categorizes deprecated function usage by file type to understand
        if the usage is primarily in tests (lower risk) vs production code (higher risk).
        """
        usage_report = self._scan_for_deprecated_usage()
        
        # Categorize files by type
        categories = self._categorize_files_by_type(usage_report['files_with_usage'])
        
        self.logger.info(f"USAGE CATEGORIZATION:")
        self.logger.info(f"  Production files: {len(categories['production_files'])}")
        self.logger.info(f"  Test files: {len(categories['test_files'])}")
        self.logger.info(f"  Other files: {len(categories['other_files'])}")
        
        # Record categorization in metadata
        self.test_metadata.update({
            "production_files_with_deprecated": len(categories['production_files']),
            "test_files_with_deprecated": len(categories['test_files']),
            "total_production_occurrences": sum(
                len(occurrences) for file_path in categories['production_files']
                for occurrences in [usage_report['files_with_usage'].get(file_path, [])]
            )
        })
        
        # Production files should have zero deprecated usage (critical for business)
        # Test files can have some usage during migration period
        if categories['production_files']:
            # Log specific production files for targeted remediation
            self.logger.warning(f"PRODUCTION FILES WITH DEPRECATED USAGE: {categories['production_files']}")
        
        # This assertion focuses on production code compliance
        self.assertEqual(len(categories['production_files']), 0,
                        f"CRITICAL: Found deprecated function usage in "
                        f"{len(categories['production_files'])} production files. "
                        f"Production code must use SSOT function only: {categories['production_files']}")
    
    def _scan_for_deprecated_usage(self) -> Dict:
        """
        Scan codebase for deprecated function usage.
        
        Returns:
            Dictionary with usage statistics and file locations
        """
        usage_report = {
            'files_with_usage': {},
            'total_occurrences': 0,
            'scan_summary': {}
        }
        
        # Create patterns for comprehensive search
        search_patterns = [
            rf'\b{self.deprecated_function}\s*\(',  # Function call
            rf'from\s+[\w.]+\s+import\s+[^"\n]*{self.deprecated_function}',  # Import
            rf'import\s+[\w.]+\.{self.deprecated_function}',  # Module import
        ]
        
        scanned_files = 0
        
        # Scan Python files in project
        for pattern in self.scan_patterns:
            for file_path in Path(self.project_root).rglob(pattern):
                if self._should_exclude_file(str(file_path)):
                    continue
                
                scanned_files += 1
                occurrences = self._scan_file_for_patterns(str(file_path), search_patterns)
                
                if occurrences:
                    relative_path = str(file_path.relative_to(self.project_root))
                    usage_report['files_with_usage'][relative_path] = occurrences
                    usage_report['total_occurrences'] += len(occurrences)
        
        usage_report['scan_summary'] = {
            'files_scanned': scanned_files,
            'files_with_usage': len(usage_report['files_with_usage'])
        }
        
        return usage_report
    
    def _scan_for_ssot_usage(self) -> Dict:
        """
        Scan codebase for SSOT function usage to verify migration progress.
        
        Returns:
            Dictionary with SSOT usage statistics
        """
        ssot_report = {
            'files_with_usage': {},
            'total_occurrences': 0
        }
        
        # Create patterns for SSOT function search
        search_patterns = [
            rf'\b{self.ssot_function}\s*\(',  # Function call
            rf'from\s+[\w.]+\s+import\s+[^"\n]*{self.ssot_function}',  # Import
        ]
        
        # Scan Python files in project
        for pattern in self.scan_patterns:
            for file_path in Path(self.project_root).rglob(pattern):
                if self._should_exclude_file(str(file_path)):
                    continue
                
                occurrences = self._scan_file_for_patterns(str(file_path), search_patterns)
                
                if occurrences:
                    relative_path = str(file_path.relative_to(self.project_root))
                    ssot_report['files_with_usage'][relative_path] = occurrences
                    ssot_report['total_occurrences'] += len(occurrences)
        
        return ssot_report
    
    def _scan_for_migration_indicators(self) -> Dict:
        """
        Scan for migration progress indicators.
        
        Returns:
            Dictionary with migration indicator statistics
        """
        indicators = {
            'deprecation_warnings': [],
            'migration_comments': [],
            'compatibility_wrappers': []
        }
        
        # Patterns to look for migration indicators
        deprecation_patterns = [
            r'DeprecationWarning',
            r'deprecated.*authenticate_websocket',
            r'MIGRATION REQUIRED',
            r'DEPRECATED:'
        ]
        
        migration_comment_patterns = [
            r'#.*migrate.*authenticate_websocket',
            r'#.*ssot.*auth',
            r'TODO.*authenticate_websocket',
            r'FIXME.*authenticate_websocket'
        ]
        
        compatibility_patterns = [
            r'backward.*compatibility.*authenticate_websocket',
            r'legacy.*authenticate_websocket',
            r'wrapper.*authenticate_websocket'
        ]
        
        # Scan files for indicators
        for pattern in self.scan_patterns:
            for file_path in Path(self.project_root).rglob(pattern):
                if self._should_exclude_file(str(file_path)):
                    continue
                
                relative_path = str(file_path.relative_to(self.project_root))
                
                # Check for deprecation warnings
                deprecation_matches = self._scan_file_for_patterns(str(file_path), deprecation_patterns)
                if deprecation_matches:
                    indicators['deprecation_warnings'].extend([f"{relative_path}:{m['line']}" for m in deprecation_matches])
                
                # Check for migration comments
                migration_matches = self._scan_file_for_patterns(str(file_path), migration_comment_patterns)
                if migration_matches:
                    indicators['migration_comments'].extend([f"{relative_path}:{m['line']}" for m in migration_matches])
                
                # Check for compatibility wrappers
                compatibility_matches = self._scan_file_for_patterns(str(file_path), compatibility_patterns)
                if compatibility_matches:
                    indicators['compatibility_wrappers'].extend([f"{relative_path}:{m['line']}" for m in compatibility_matches])
        
        return indicators
    
    def _scan_file_for_patterns(self, file_path: str, patterns: List[str]) -> List[Dict]:
        """
        Scan a single file for multiple regex patterns.
        
        Args:
            file_path: Path to file to scan
            patterns: List of regex patterns to search for
            
        Returns:
            List of dictionaries with match information
        """
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        for match in re.finditer(pattern, line, re.IGNORECASE):
                            matches.append({
                                'line': line_num,
                                'pattern': pattern,
                                'match': match.group(),
                                'context': line.strip()
                            })
        
        except (IOError, UnicodeDecodeError) as e:
            # Skip files that can't be read
            pass
        
        return matches
    
    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from scanning."""
        for pattern in self.exclude_patterns:
            if Path(file_path).match(pattern):
                return True
        return False
    
    def _categorize_files_by_type(self, files_with_usage: Dict) -> Dict:
        """
        Categorize files by type (production, test, other).
        
        Args:
            files_with_usage: Dictionary of files with deprecated usage
            
        Returns:
            Dictionary categorizing files by type
        """
        categories = {
            'production_files': [],
            'test_files': [],
            'other_files': []
        }
        
        for file_path in files_with_usage.keys():
            file_path_lower = file_path.lower()
            
            if any(test_indicator in file_path_lower for test_indicator in ['test_', '/tests/', '/test/', '_test.py']):
                categories['test_files'].append(file_path)
            elif any(prod_indicator in file_path for prod_indicator in ['netra_backend/app/', 'auth_service/', 'frontend/']):
                categories['production_files'].append(file_path)
            else:
                categories['other_files'].append(file_path)
        
        return categories
    
    def _log_usage_analysis(self, usage_report: Dict):
        """Log detailed analysis of deprecated function usage."""
        self.logger.info(f"DEPRECATED USAGE SCAN COMPLETE:")
        self.logger.info(f"  Files scanned: {usage_report['scan_summary']['files_scanned']}")
        self.logger.info(f"  Files with usage: {usage_report['scan_summary']['files_with_usage']}")
        self.logger.info(f"  Total occurrences: {usage_report['total_occurrences']}")
        
        # Log top files with most usage
        if usage_report['files_with_usage']:
            sorted_files = sorted(
                usage_report['files_with_usage'].items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            
            self.logger.info(f"TOP FILES WITH USAGE:")
            for file_path, occurrences in sorted_files[:10]:
                self.logger.info(f"  {file_path}: {len(occurrences)} occurrences")
                # Log first few occurrences for context
                for occurrence in occurrences[:3]:
                    self.logger.info(f"    Line {occurrence['line']}: {occurrence['context'][:80]}...")
        
        # Record detailed stats in test metadata
        self.test_metadata.update({
            "files_scanned": usage_report['scan_summary']['files_scanned'],
            "files_with_deprecated_usage": usage_report['scan_summary']['files_with_usage'],
            "total_deprecated_occurrences": usage_report['total_occurrences'],
            "scan_timestamp": self.test_start_time
        })


if __name__ == '__main__':
    unittest.main()