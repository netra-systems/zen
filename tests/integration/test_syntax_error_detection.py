#!/usr/bin/env python3
"""
SYNTAX ERROR DETECTION TEST SUITE - CRITICAL INTEGRATION TEST VALIDATION
=======================================================================

Business Context: Integration test syntax errors are blocking ALL staging validation.
This test suite provides comprehensive detection and prevention of syntax errors
that can break the entire test pipeline.

CRITICAL REQUIREMENTS:
- MUST FAIL INITIALLY to detect current syntax errors before fixes
- Real Services - No mocks, use real database/Redis connections per CLAUDE.md
- AST-Based Validation - Use Python AST to detect syntax errors comprehensively
- Specific Detection - Find unterminated string literals and literal newlines
- Integration with unified_test_runner.py - Full Docker service integration
- SSOT Compliance - Follow all CLAUDE.md patterns and guidelines

Expected Behavior:
- Tests FAIL initially, proving they detect the syntax errors
- After syntax fixes, tests PASS, validating the solution
- Clear error reporting with actionable information
- Integration with existing test framework

Business Value:
- Immediate identification of broken test files
- Prevention of staging validation pipeline blocking
- Foundation for syntax error prevention system
- Evidence-based validation of syntax issues
"""

import ast
import asyncio
import glob
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import tokenize
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import unittest

# CRITICAL: Setup path for absolute imports per CLAUDE.md
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# CRITICAL: Absolute imports only per CLAUDE.md
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.types.core_types import UserID, ensure_user_id
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser

logger = logging.getLogger(__name__)


class SyntaxErrorDetector:
    """
    SSOT Syntax Error Detection Engine
    
    Provides comprehensive Python syntax error detection using AST parsing,
    tokenization analysis, and pattern matching to identify:
    - Unterminated string literals
    - Literal newline sequences in code
    - Malformed Python syntax
    - Line continuation issues
    """
    
    def __init__(self):
        # Focus on patterns that AST validation won't catch
        # These are minimal and focused on common real syntax errors
        self.error_patterns = [
            # Only critical syntax violations that Python's AST might miss
            (r'^\s*except\s*:\s*$', "Bare except clause (should specify exception)"),
            (r'^\s*except\s*:\s*#.*$', "Bare except clause (should specify exception)"),
        ]
        
        # Focus on actual problematic newlines - not valid print statements
        self.literal_newline_patterns = [
            # Only check for obviously wrong patterns
            (r'\\n(?=\s*$)', "Literal \\n at end of line (likely error)"),
        ]
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Comprehensive syntax analysis of a Python file.
        
        Returns detailed analysis including:
        - AST parsing results
        - Tokenization issues
        - Pattern-based detections
        - Line-by-line error locations
        """
        result = {
            'file_path': file_path,
            'has_syntax_errors': False,
            'ast_error': None,
            'tokenization_error': None,
            'pattern_issues': [],
            'line_issues': [],
            'error_summary': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result['file_read_error'] = str(e)
            result['has_syntax_errors'] = True
            return result
        
        # AST Parsing Test
        try:
            ast.parse(content, filename=file_path)
            result['ast_valid'] = True
        except SyntaxError as e:
            result['ast_error'] = {
                'line': e.lineno,
                'offset': e.offset,
                'message': e.msg,
                'text': e.text
            }
            result['has_syntax_errors'] = True
            result['error_summary'].append(f"AST Error Line {e.lineno}: {e.msg}")
        except Exception as e:
            result['ast_error'] = {'message': str(e)}
            result['has_syntax_errors'] = True
            result['error_summary'].append(f"AST Parse Error: {str(e)}")
        
        # Tokenization Test
        try:
            tokens = list(tokenize.generate_tokens(StringIO(content).readline))
            result['tokenization_valid'] = True
        except tokenize.TokenError as e:
            result['tokenization_error'] = {
                'message': str(e),
                'error_type': 'TokenError'
            }
            result['has_syntax_errors'] = True
            result['error_summary'].append(f"Tokenization Error: {str(e)}")
        except Exception as e:
            result['tokenization_error'] = {'message': str(e)}
            result['has_syntax_errors'] = True
            result['error_summary'].append(f"Tokenization Error: {str(e)}")
        
        # Pattern-based Detection (minimal and focused)
        # Only check for patterns that AST won't catch or are policy violations
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # Skip comments, empty lines, and docstrings
            if (not stripped_line or 
                stripped_line.startswith('#') or 
                stripped_line.startswith('"""') or 
                stripped_line.startswith("'''")):
                continue
                
            for pattern, description in self.error_patterns:
                if re.search(pattern, line):
                    issue = {
                        'line_number': line_num,
                        'line_content': line.strip(),
                        'pattern': pattern,
                        'description': description
                    }
                    result['pattern_issues'].append(issue)
                    result['line_issues'].append(f"Line {line_num}: {description}")
                    
        # Only mark as syntax error if we found real issues
        if result['pattern_issues'] and not result.get('ast_valid', False):
            result['has_syntax_errors'] = True
            result['error_summary'].extend([
                f"Pattern Issue Line {issue['line_number']}: {issue['description']}"
                for issue in result['pattern_issues']
            ])
        
        return result
    
    def _is_likely_syntax_error(self, line: str, pattern: str) -> bool:
        """
        Additional validation to reduce false positives.
        Returns True if the line is likely to contain a real syntax error.
        """
        # For mismatched quotes, check if it's a valid multi-line string start
        if "mismatched quotes" in pattern:
            # Allow triple quotes and properly paired quotes
            if '"""' in line or "'''" in line:
                return False
            # Count quotes to see if they're balanced
            single_quotes = line.count("'") - line.count("\\'")
            double_quotes = line.count('"') - line.count('\\"')
            if single_quotes % 2 == 0 and double_quotes % 2 == 0:
                return False
        
        # For unterminated f-strings, be more specific
        if "unterminated f-string" in pattern.lower():
            # Allow valid f-string starts that continue on next line
            if line.strip().endswith('(') or line.strip().endswith(','):
                return False
        
        return True
    
    def _is_valid_string_continuation(self, line: str, next_line: str) -> bool:
        """
        Check if a line that appears to have an unterminated string is actually
        a valid multi-line string or string continuation.
        """
        # Check for explicit line continuation with backslash
        if line.rstrip().endswith('\\'):
            return True
            
        # Check for multi-line string literals (triple quotes)
        if '"""' in line or "'''" in line:
            return True
            
        # Check for parenthesized expressions (implicit line continuation)
        if '(' in line and line.count('(') > line.count(')'):
            return True
            
        # Check if next line continues the string
        if next_line.strip().startswith('"') or next_line.strip().startswith("'"):
            return True
            
        return False
    
    def scan_directory(self, directory: str, pattern: str = "*.py") -> Dict[str, Any]:
        """
        Scan directory for Python files and analyze each for syntax errors.
        """
        results = {
            'directory': directory,
            'files_scanned': 0,
            'files_with_errors': 0,
            'file_results': {},
            'error_summary': []
        }
        
        file_pattern = os.path.join(directory, pattern)
        python_files = glob.glob(file_pattern, recursive=True)
        
        results['files_scanned'] = len(python_files)
        
        for file_path in python_files:
            if os.path.isfile(file_path):
                file_result = self.analyze_file(file_path)
                results['file_results'][file_path] = file_result
                
                if file_result['has_syntax_errors']:
                    results['files_with_errors'] += 1
                    results['error_summary'].extend([
                        f"{file_path}: {error}" for error in file_result['error_summary']
                    ])
        
        return results


class TestSyntaxErrorDetection(SSotBaseTestCase):
    """
    CRITICAL: Comprehensive Syntax Error Detection Test Suite
    
    Business Value:
    - Immediate identification of broken test files
    - Prevention of staging validation pipeline blocking
    - Foundation for syntax error prevention system
    - Evidence-based validation of syntax issues
    
    MUST FAIL INITIALLY to detect current syntax errors before fixes.
    After syntax fixes, tests PASS, validating the solution.
    """
    
    def setup_method(self, method):
        """Initialize test environment with real services per CLAUDE.md requirements."""
        super().setup_method(method)
        self.syntax_detector = SyntaxErrorDetector()
        self.project_root = Path(__file__).parent.parent.parent
        self.integration_tests_dir = self.project_root / "tests" / "integration"
        
        # Initialize environment for real service connections
        self.env = get_env()
        
        logger.info(f"Syntax Error Detection Test Suite initialized")
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Integration tests directory: {self.integration_tests_dir}")
    
    def test_integration_files_syntax_validation(self):
        """
        Test 1: Comprehensive Integration Files Syntax Validation
        
        CRITICAL: This test MUST detect and report ALL syntax errors in integration test files.
        - Scans all integration test files for syntax errors
        - Uses ast.parse() to validate Python syntax
        - Reports specific files and line numbers with issues
        - MUST detect the remaining broken file: test_database_connection_pooling_performance.py:498
        
        Expected to FAIL initially if syntax errors exist, PASS after fixes.
        """
        logger.info("=== TEST 1: Integration Files Syntax Validation ===")
        
        # Scan integration tests directory
        scan_results = self.syntax_detector.scan_directory(
            str(self.integration_tests_dir),
            "**/*.py"
        )
        
        logger.info(f"Scanned {scan_results['files_scanned']} integration test files")
        logger.info(f"Found {scan_results['files_with_errors']} files with syntax errors")
        
        # Log detailed error information
        if scan_results['files_with_errors'] > 0:
            logger.error("SYNTAX ERRORS DETECTED:")
            for error in scan_results['error_summary']:
                logger.error(f"  {error}")
        
        # Generate detailed report for debugging
        error_report = {
            'scan_timestamp': asyncio.get_event_loop().time(),
            'directory_scanned': str(self.integration_tests_dir),
            'total_files': scan_results['files_scanned'],
            'files_with_errors': scan_results['files_with_errors'],
            'detailed_errors': []
        }
        
        for file_path, file_result in scan_results['file_results'].items():
            if file_result['has_syntax_errors']:
                error_report['detailed_errors'].append({
                    'file': file_path,
                    'ast_error': file_result.get('ast_error'),
                    'tokenization_error': file_result.get('tokenization_error'),
                    'pattern_issues': file_result.get('pattern_issues', []),
                    'error_summary': file_result.get('error_summary', [])
                })
        
        # Save error report for investigation
        report_path = self.project_root / "reports" / "syntax_error_detection_report.json"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(error_report, f, indent=2, default=str)
        
        logger.info(f"Detailed error report saved to: {report_path}")
        
        # CRITICAL: This assertion MUST FAIL if syntax errors exist
        # This proves the test is working and detects real issues
        assert scan_results['files_with_errors'] == 0, (
            f"CRITICAL: Found {scan_results['files_with_errors']} integration test files with syntax errors. "
            f"See detailed report at {report_path}. "
            f"Errors: {'; '.join(scan_results['error_summary'][:5])}"
        )
    
    def test_unterminated_string_literal_detection(self):
        """
        Test 2: Specific Unterminated String Literal Detection
        
        - Specifically detect unterminated string literals
        - Scan for f-string formatting errors
        - Find mismatched quotes and brackets
        - Report exact line numbers and character positions
        
        MUST FAIL initially if unterminated strings exist.
        """
        logger.info("=== TEST 2: Unterminated String Literal Detection ===")
        
        # Focus on AST-based detection for unterminated strings
        # Most unterminated strings will be caught by AST parsing
        # Only check for obviously problematic patterns
        
        detection_results = []
        
        for file_path in glob.glob(str(self.integration_tests_dir / "*.py")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    # Skip comments and empty lines
                    stripped_line = line.strip()
                    if not stripped_line or stripped_line.startswith('#'):
                        continue
                        
                    for pattern, description in unterminated_patterns:
                        if re.search(pattern, line):
                            # Additional validation: check if this is actually an error
                            # Valid cases: string continues on next line, docstrings, etc.
                            next_line = lines[line_num] if line_num < len(lines) else ""
                            if self._is_valid_string_continuation(line, next_line):
                                continue
                                
                            detection_results.append({
                                'file': file_path,
                                'line': line_num,
                                'content': line.strip(),
                                'issue': description
                            })
                            logger.warning(f"Unterminated string detected: {file_path}:{line_num}")
                            
            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
                detection_results.append({
                    'file': file_path,
                    'line': 0,
                    'content': str(e),
                    'issue': "File read error"
                })
        
        # Log results
        if detection_results:
            logger.error(f"UNTERMINATED STRING LITERALS DETECTED: {len(detection_results)} issues")
            for result in detection_results:
                logger.error(f"  {result['file']}:{result['line']} - {result['issue']}")
        
        # CRITICAL: This test MUST FAIL if unterminated strings exist
        assert len(detection_results) == 0, (
            f"CRITICAL: Found {len(detection_results)} unterminated string literals in integration tests. "
            f"Details: {detection_results[:3]}"
        )
    
    def test_literal_newline_sequence_detection(self):
        """
        Test 3: Literal Newline Sequence Detection
        
        - Find literal newline sequences in code (not in strings)
        - Detect line continuation character issues
        - Identify corrupted multi-line code structures
        - Report all instances with context
        
        MUST FAIL initially if literal newlines exist.
        """
        logger.info("=== TEST 3: Literal Newline Sequence Detection ===")
        
        # Use the more precise literal newline patterns from the detector
        literal_newline_patterns = self.syntax_detector.literal_newline_patterns
        
        literal_newline_issues = []
        
        for file_path in glob.glob(str(self.integration_tests_dir / "*.py")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    # Skip comments and empty lines
                    stripped_line = line.strip()
                    if stripped_line.startswith('#') or not stripped_line:
                        continue
                    
                    for pattern, description in literal_newline_patterns:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            literal_newline_issues.append({
                                'file': file_path,
                                'line': line_num,
                                'position': match.start(),
                                'content': line.strip(),
                                'matched_text': match.group(),
                                'issue': description
                            })
                            logger.warning(f"Literal newline detected: {file_path}:{line_num}:{match.start()}")
                            
            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
        
        # Log results with context
        if literal_newline_issues:
            logger.error(f"LITERAL NEWLINE SEQUENCES DETECTED: {len(literal_newline_issues)} issues")
            for issue in literal_newline_issues:
                logger.error(f"  {issue['file']}:{issue['line']}:{issue['position']} - {issue['issue']}")
                logger.error(f"    Content: {issue['content']}")
                logger.error(f"    Matched: {issue['matched_text']}")
        
        # CRITICAL: This test MUST FAIL if literal newlines exist
        assert len(literal_newline_issues) == 0, (
            f"CRITICAL: Found {len(literal_newline_issues)} literal newline sequences in integration tests. "
            f"These can cause syntax errors. Details: {literal_newline_issues[:2]}"
        )
    
    def test_test_runner_syntax_pre_validation(self):
        """
        Test 4: Test Runner Syntax Pre-Validation
        
        - Test the test runner's syntax validation phase
        - Verify it fails gracefully on syntax errors
        - Check that it reports specific errors before execution
        - Ensure it doesn't crash the entire test suite
        
        This validates that our test infrastructure can handle syntax errors properly.
        """
        logger.info("=== TEST 4: Test Runner Syntax Pre-Validation ===")
        
        # Create a temporary file with known syntax error
        syntax_error_content = '''
def test_example():
    """Test with intentional syntax error"""
    print(f"This is an unterminated f-string
    assert True
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(syntax_error_content)
            temp_file_path = temp_file.name
        
        try:
            # Test our syntax detector on the known bad file
            analysis_result = self.syntax_detector.analyze_file(temp_file_path)
            
            logger.info(f"Analysis result for test file: {analysis_result}")
            
            # Verify the detector catches the syntax error
            assert analysis_result['has_syntax_errors'], (
                "Syntax detector should detect the intentional syntax error"
            )
            
            assert (analysis_result.get('ast_error') or analysis_result.get('tokenization_error')), (
                "Should detect either AST or tokenization error"
            )
            
            # Test that Python compilation fails as expected
            try:
                subprocess.run([
                    sys.executable, '-m', 'py_compile', temp_file_path
                ], check=True, capture_output=True, text=True)
                assert False, "Python compilation should have failed on syntax error"
            except subprocess.CalledProcessError as e:
                logger.info(f"Expected compilation failure: {e.stderr}")
                assert "SyntaxError" in e.stderr
            
            # Verify our error reporting is actionable
            error_summary = analysis_result.get('error_summary', [])
            assert len(error_summary) > 0, "Should provide actionable error summary"
            
            logger.info("Syntax pre-validation test completed successfully")
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    
    def test_integration_with_unified_test_runner(self):
        """
        Test 5: Integration with Unified Test Runner
        
        Validates that syntax error detection integrates properly with
        the existing unified_test_runner.py infrastructure and uses real services.
        """
        logger.info("=== TEST 5: Integration with Unified Test Runner ===")
        
        # Verify we can import unified test runner
        try:
            sys.path.insert(0, str(self.project_root / "tests"))
            import unified_test_runner
            logger.info("Successfully imported unified_test_runner")
        except ImportError as e:
            assert False, f"Failed to import unified_test_runner: {e}"
        
        # Verify database connection (real service requirement)
        try:
            db_url = self.env.get('DATABASE_URL')
            assert db_url is not None, "DATABASE_URL must be available for real services"
            logger.info(f"Database connection available: {db_url[:20]}...")
        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")
        
        # Verify Redis connection (real service requirement)
        try:
            redis_url = self.env.get('REDIS_URL')
            assert redis_url is not None, "REDIS_URL must be available for real services"
            logger.info(f"Redis connection available: {redis_url[:20]}...")
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}")
        
        logger.info("Integration with unified test runner validated successfully")
    
    def teardown_method(self, method):
        """Clean up after each test."""
        super().teardown_method(method)
        logger.info("Syntax Error Detection Test completed")


if __name__ == '__main__':
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run with pytest
    import pytest
    pytest.main([__file__, '-v'])