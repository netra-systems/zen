#!/usr/bin/env python3
"""
Auth URL Pattern Regression Prevention Tests

These tests prevent the reintroduction of incorrect auth service URL patterns
that can cause 404 errors and system failures.

CRITICAL ISSUE REFERENCE: Issue #296 - 404 error on /auth/service/token endpoint
ROOT CAUSE: Typo in post-deployment test using /auth/service/token instead of /auth/service-token
BUSINESS IMPACT: Post-deployment verification failures, potential service downtime detection

PREVENTION STRATEGY: Automated scanning of all code files for incorrect URL patterns
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class AuthUrlPatternValidator:
    """Validates auth service URL patterns across the codebase."""
    
    # Correct URL patterns that should be used
    CORRECT_PATTERNS = {
        "/auth/service-token": "Service token generation endpoint",
        "/auth/validate": "Token validation endpoint", 
        "/auth/login": "User login endpoint",
        "/auth/logout": "User logout endpoint",
        "/auth/refresh": "Token refresh endpoint",
        "/auth/dev/login": "Development login endpoint",
        "/auth/callback": "OAuth callback endpoint",
        "/auth/config": "Auth configuration endpoint",
        "/auth/health": "Auth service health endpoint",
        "/auth/status": "Auth service status endpoint"
    }
    
    # Incorrect patterns that should never be used
    INCORRECT_PATTERNS = {
        "/auth/service/token": "INCORRECT - Should be /auth/service-token",
        "/auth/service/validate": "INCORRECT - Should be /auth/validate",
        "/auth/api/token": "INCORRECT - No /api prefix needed",
        "/api/auth/service-token": "INCORRECT - Should be /auth/service-token",
        "/auth/service_token": "INCORRECT - Should use hyphen not underscore"
    }
    
    def __init__(self):
        self.project_root = project_root
        self.scan_extensions = {'.py', '.ts', '.tsx', '.js', '.jsx', '.md', '.yaml', '.yml', '.json'}
        self.exclude_patterns = {
            '*.pyc', '__pycache__', '.git', 'node_modules', 'venv', '.pytest_cache',
            'dist', 'build', '.next', '.vscode', '.idea'
        }
    
    def get_files_to_scan(self) -> List[Path]:
        """Get all files that should be scanned for URL patterns."""
        files = []
        
        for root, dirs, filenames in os.walk(self.project_root):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not any(
                d.startswith(pattern.replace('*', '')) or d == pattern
                for pattern in self.exclude_patterns
            )]
            
            for filename in filenames:
                filepath = Path(root) / filename
                
                # Check if file extension should be scanned
                if filepath.suffix in self.scan_extensions:
                    files.append(filepath)
        
        return files
    
    def scan_file_for_patterns(self, filepath: Path) -> Dict[str, List[Tuple[int, str]]]:
        """Scan a single file for auth URL patterns."""
        patterns_found = {
            'correct': [],
            'incorrect': []
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            # Skip certain types of files that legitimately contain incorrect patterns for testing
            rel_path = str(filepath.relative_to(self.project_root))
            skip_incorrect_pattern_check = (
                'test_auth_url_pattern_regression_prevention.py' in rel_path or
                'test_service_token_url_patterns.py' in rel_path or
                'ISSUE_296_AUTH_URL_PATTERN_REMEDIATION_PLAN.md' in rel_path or  # Skip remediation docs
                'reports/auth/' in rel_path or  # Skip auth reports/documentation
                'CRITICAL ISSUE REFERENCE' in ''.join(lines[:20]) or  # Skip files documenting the issue
                '# Test incorrect patterns' in ''.join(lines) or
                'INCORRECT PATTERNS' in ''.join(lines) or
                'Issue #296' in ''.join(lines[:10])  # Skip issue documentation
            )
                
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()
                
                # Skip lines that are clearly documentation or comments about incorrect patterns
                is_documentation = any(marker in line_lower for marker in [
                    '# incorrect', '# test incorrect', '# broken', '# should be',
                    'incorrect_patterns', 'incorrect url', 'wrong pattern',
                    'status_code', 'should return 404', 'fails as expected',
                    'comment:', 'note:', 'todo:', 'fixme:'
                ])
                
                # Check for correct patterns
                for pattern, description in self.CORRECT_PATTERNS.items():
                    if pattern in line:
                        patterns_found['correct'].append((line_num, line.strip()))
                
                # Check for incorrect patterns (skip if this file is meant to test them)
                if not skip_incorrect_pattern_check and not is_documentation:
                    for pattern, description in self.INCORRECT_PATTERNS.items():
                        if pattern in line:
                            patterns_found['incorrect'].append((line_num, line.strip()))
                        
        except Exception as e:
            # Skip files that can't be read
            pass
            
        return patterns_found
    
    def scan_all_files(self) -> Dict[str, Dict[str, List[Tuple[int, str]]]]:
        """Scan all files for URL patterns."""
        results = {}
        files = self.get_files_to_scan()
        
        for filepath in files:
            patterns = self.scan_file_for_patterns(filepath)
            if patterns['correct'] or patterns['incorrect']:
                rel_path = str(filepath.relative_to(self.project_root))
                results[rel_path] = patterns
                
        return results


class TestAuthUrlPatternRegression:
    """Test suite to prevent auth URL pattern regression."""
    
    @pytest.fixture
    def validator(self):
        """Fixture providing URL pattern validator."""
        return AuthUrlPatternValidator()
    
    def test_no_incorrect_auth_url_patterns_in_codebase(self, validator):
        """Test that no incorrect auth URL patterns exist in the codebase."""
        results = validator.scan_all_files()
        
        incorrect_usage = {}
        for filepath, patterns in results.items():
            if patterns['incorrect']:
                incorrect_usage[filepath] = patterns['incorrect']
        
        if incorrect_usage:
            error_msg = "\n\nINCORRECT AUTH URL PATTERNS FOUND:\n"
            error_msg += "=" * 50 + "\n"
            
            for filepath, incorrect_patterns in incorrect_usage.items():
                error_msg += f"\nFile: {filepath}\n"
                for line_num, line_content in incorrect_patterns:
                    error_msg += f"  Line {line_num}: {line_content}\n"
                    
                    # Suggest corrections
                    for incorrect, description in validator.INCORRECT_PATTERNS.items():
                        if incorrect in line_content:
                            correct_pattern = None
                            if incorrect == "/auth/service/token":
                                correct_pattern = "/auth/service-token"
                            elif incorrect == "/auth/service/validate":
                                correct_pattern = "/auth/validate"
                            elif incorrect == "/auth/api/token":
                                correct_pattern = "/auth/service-token"
                            elif incorrect == "/api/auth/service-token":
                                correct_pattern = "/auth/service-token"
                            elif incorrect == "/auth/service_token":
                                correct_pattern = "/auth/service-token"
                            
                            if correct_pattern:
                                error_msg += f"    SUGGESTED FIX: Replace '{incorrect}' with '{correct_pattern}'\n"
            
            error_msg += "\n" + "=" * 50
            error_msg += "\nREFERENCE: Issue #296 - Auth service URL pattern consistency"
            error_msg += "\nIMPACT: Incorrect patterns cause 404 errors and deployment verification failures"
            error_msg += "\nACTION: Update the incorrect patterns to use the correct auth service endpoints\n"
            
            pytest.fail(error_msg)
    
    def test_correct_service_token_pattern_usage(self, validator):
        """Test that /auth/service-token is used instead of /auth/service/token."""
        results = validator.scan_all_files()
        
        service_token_usage = []
        incorrect_service_token_usage = []
        
        for filepath, patterns in results.items():
            for line_num, line_content in patterns['correct']:
                if "/auth/service-token" in line_content:
                    service_token_usage.append((filepath, line_num, line_content))
            
            for line_num, line_content in patterns['incorrect']:
                if "/auth/service/token" in line_content:
                    incorrect_service_token_usage.append((filepath, line_num, line_content))
        
        # Should have at least some correct usage (in auth client and tests)
        assert len(service_token_usage) > 0, (
            "Expected to find at least some correct usage of /auth/service-token pattern"
        )
        
        # Should have no incorrect usage
        if incorrect_service_token_usage:
            error_msg = "\nFound incorrect /auth/service/token usage (should be /auth/service-token):\n"
            for filepath, line_num, line_content in incorrect_service_token_usage:
                error_msg += f"  {filepath}:{line_num} - {line_content}\n"
            pytest.fail(error_msg)
    
    def test_auth_client_uses_correct_patterns(self, validator):
        """Test that auth client code uses correct URL patterns."""
        auth_client_files = []
        results = validator.scan_all_files()
        
        for filepath in results.keys():
            if 'auth_client' in filepath.lower() or 'auth_service_client' in filepath.lower():
                auth_client_files.append(filepath)
        
        # Should find auth client files
        assert len(auth_client_files) > 0, "Expected to find auth client files"
        
        for filepath in auth_client_files:
            patterns = results[filepath]
            
            # Auth client should not have any incorrect patterns
            assert not patterns['incorrect'], (
                f"Auth client file {filepath} contains incorrect URL patterns: "
                f"{patterns['incorrect']}"
            )
    
    def test_post_deployment_test_uses_correct_patterns(self, validator):
        """Test that post-deployment test uses correct URL patterns."""
        results = validator.scan_all_files()
        
        post_deployment_files = [
            filepath for filepath in results.keys()
            if 'post_deployment' in filepath.lower()
        ]
        
        if not post_deployment_files:
            pytest.skip("No post-deployment test files found")
        
        for filepath in post_deployment_files:
            patterns = results[filepath]
            
            # Post-deployment tests should not have incorrect patterns
            assert not patterns['incorrect'], (
                f"Post-deployment test {filepath} contains incorrect URL patterns: "
                f"{patterns['incorrect']} - This was the source of Issue #296"
            )
            
            # Should use correct service-token pattern if it mentions service tokens
            file_content = ""
            try:
                with open(validator.project_root / filepath, 'r') as f:
                    file_content = f.read()
            except:
                pass
                
            if 'service' in file_content.lower() and 'token' in file_content.lower():
                # Should have correct pattern somewhere
                has_correct_pattern = any(
                    '/auth/service-token' in line_content
                    for _, line_content in patterns['correct']
                )
                
                assert has_correct_pattern, (
                    f"Post-deployment test {filepath} mentions service tokens but "
                    f"doesn't use the correct /auth/service-token pattern"
                )


class TestAuthUrlPatternDocumentation:
    """Test that URL patterns are properly documented."""
    
    def test_correct_patterns_documented(self):
        """Test that all correct patterns are documented somewhere."""
        validator = AuthUrlPatternValidator()
        results = validator.scan_all_files()
        
        documented_patterns = set()
        
        # Look for patterns in documentation files
        for filepath, patterns in results.items():
            if any(ext in filepath.lower() for ext in ['.md', '.rst', '.txt']):
                for line_num, line_content in patterns['correct']:
                    for pattern in validator.CORRECT_PATTERNS.keys():
                        if pattern in line_content:
                            documented_patterns.add(pattern)
        
        # Critical patterns should be documented
        critical_patterns = {'/auth/service-token', '/auth/validate', '/auth/login'}
        
        for pattern in critical_patterns:
            assert pattern in documented_patterns, (
                f"Critical auth pattern {pattern} should be documented in README or docs"
            )


@pytest.mark.regression
@pytest.mark.auth
def test_auth_url_pattern_regression_suite():
    """Main regression test suite for auth URL patterns."""
    validator = AuthUrlPatternValidator()
    test_class = TestAuthUrlPatternRegression()
    
    # Run core regression tests
    test_class.test_no_incorrect_auth_url_patterns_in_codebase(validator)
    test_class.test_correct_service_token_pattern_usage(validator)
    test_class.test_auth_client_uses_correct_patterns(validator)
    test_class.test_post_deployment_test_uses_correct_patterns(validator)


if __name__ == "__main__":
    # Run as standalone script
    import sys
    
    validator = AuthUrlPatternValidator()
    results = validator.scan_all_files()
    
    print("Auth URL Pattern Analysis")
    print("=" * 50)
    
    incorrect_found = False
    
    for filepath, patterns in results.items():
        if patterns['incorrect']:
            if not incorrect_found:
                print("\n❌ INCORRECT PATTERNS FOUND:")
                incorrect_found = True
            
            print(f"\nFile: {filepath}")
            for line_num, line_content in patterns['incorrect']:
                print(f"  Line {line_num}: {line_content}")
    
    if not incorrect_found:
        print("\n✅ No incorrect auth URL patterns found!")
    
    correct_count = sum(len(p['correct']) for p in results.values())
    incorrect_count = sum(len(p['incorrect']) for p in results.values())
    
    print(f"\nSummary:")
    print(f"  Correct patterns found: {correct_count}")
    print(f"  Incorrect patterns found: {incorrect_count}")
    
    if incorrect_found:
        print(f"\n⚠️  ACTION REQUIRED: Fix incorrect patterns to prevent 404 errors")
        sys.exit(1)
    else:
        print(f"\n✅ All auth URL patterns are correct!")
        sys.exit(0)