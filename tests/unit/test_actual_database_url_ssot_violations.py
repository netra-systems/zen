"""Real SSOT violation detection for Issue #799."""

import pytest
import os
import ast
from pathlib import Path
from typing import List, Dict, Tuple


pytestmark = [
    pytest.mark.unit,
    pytest.mark.ssot_compliance,
]


class DatabaseURLViolationDetector:
    """Detect actual SSOT violations in database URL construction."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations: List[Dict[str, str]] = []
        
    def scan_for_violations(self) -> List[Dict[str, str]]:
        """Scan business logic files for SSOT violations."""
        # Only scan actual business logic, not test files
        business_logic_paths = [
            "netra_backend/app",
            "auth_service",  
            "shared",
        ]
        
        for path_str in business_logic_paths:
            path = self.project_root / path_str
            if path.exists():
                self._scan_directory(path, exclude_tests=True)
                
        return self.violations
        
    def _scan_directory(self, directory: Path, exclude_tests: bool = True):
        """Recursively scan directory for Python files."""
        for file_path in directory.rglob("*.py"):
            # Skip test files if excluding tests
            if exclude_tests and ("test_" in file_path.name or "/tests/" in str(file_path)):
                continue
                
            self._scan_file(file_path)
            
    def _scan_file(self, file_path: Path):
        """Scan individual file for SSOT violations."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for direct string formatting patterns
            violations = []
            
            # Pattern 1: f-string database URL construction
            if 'f"postgresql://' in content:
                violations.append({
                    'file': str(file_path),
                    'type': 'f_string_construction',
                    'pattern': 'f"postgresql://',
                    'description': 'Manual f-string database URL construction'
                })
                
            # Pattern 2: Direct string formatting 
            if '"postgresql://{}:{}@{}:{}/{}"' in content:
                violations.append({
                    'file': str(file_path),
                    'type': 'format_string_construction',
                    'pattern': '"postgresql://{}:{}@{}:{}/{}"',
                    'description': 'Manual format string database URL construction'
                })
                
            # Pattern 3: Hardcoded database URLs
            import re
            hardcoded_pattern = r'"postgresql://[^"]*@[^"]*:[0-9]+/[^"]*"'
            hardcoded_matches = re.findall(hardcoded_pattern, content)
            for match in hardcoded_matches:
                violations.append({
                    'file': str(file_path),
                    'type': 'hardcoded_url',
                    'pattern': match,
                    'description': 'Hardcoded database URL'
                })
                
            self.violations.extend(violations)
            
        except Exception as e:
            # Skip files we can't read
            pass


@pytest.mark.unit
class ActualDatabaseURLSSOTViolationsTests:
    """Test for real SSOT violations in the codebase."""
    
    def test_detect_actual_ssot_violations(self):
        """Detect actual SSOT violations in business logic files."""
        # This test should FAIL initially, showing real violations exist
        
        project_root = Path(__file__).parent.parent.parent
        detector = DatabaseURLViolationDetector(project_root)
        violations = detector.scan_for_violations()
        
        # Filter violations to focus on the most critical ones
        critical_violations = [
            v for v in violations 
            if v['type'] in ['f_string_construction', 'format_string_construction']
            and 'test' not in v['file'].lower()  # Exclude test files
        ]
        
        print(f"\nFound {len(violations)} total violations, {len(critical_violations)} critical")
        
        if critical_violations:
            print("\n=== CRITICAL SSOT VIOLATIONS ===")
            for violation in critical_violations:
                print(f"File: {violation['file']}")
                print(f"Type: {violation['type']}")
                print(f"Pattern: {violation['pattern']}")
                print(f"Description: {violation['description']}")
                print()
                
        # This assertion should FAIL, showing violations exist  
        assert len(critical_violations) == 0, f"Found {len(critical_violations)} critical SSOT violations in business logic"
        
    def test_specific_known_violations(self):
        """Test for specific known SSOT violations found in Issue #799."""
        # These are the exact violations we found in our analysis
        
        # Issue #799 Step 2 findings:
        known_violations = [
            {
                'file': 'netra_backend/app/schemas/config.py',
                'line': 722,
                'pattern': 'f"postgresql://{user}:{password}@{host}:{port}/{database}"',
                'type': 'manual_construction'
            },
            {
                'file': 'shared/database_url_builder.py', 
                'line': 500,
                'pattern': 'f"postgresql://{user}:{password}@{host}:{port}/{db}"',
                'type': 'manual_construction_in_ssot_file'
            }
        ]
        
        project_root = Path(__file__).parent.parent.parent
        violations_found = []
        
        for violation in known_violations:
            file_path = project_root / violation['file']
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    # Check if the violation still exists
                    if violation['line'] <= len(lines):
                        line_content = lines[violation['line'] - 1].strip()
                        if violation['pattern'] in line_content:
                            violations_found.append({
                                'file': violation['file'],
                                'line': violation['line'],
                                'content': line_content,
                                'type': violation['type']
                            })
                except Exception:
                    pass  # Skip files we can't read
                    
        if violations_found:
            print("\n=== SPECIFIC KNOWN VIOLATIONS FOUND ===")
            for violation in violations_found:
                print(f"File: {violation['file']}:{violation['line']}")
                print(f"Type: {violation['type']}")
                print(f"Code: {violation['content']}")
                print()
                
        # This should FAIL initially, proving the violations exist
        assert len(violations_found) == 0, f"Found {len(violations_found)} specific SSOT violations that need remediation"
        
    def test_database_url_builder_usage_validation(self):
        """Test that DatabaseURLBuilder is being used correctly where it should be."""
        # This test should PASS - proving correct usage exists
        
        project_root = Path(__file__).parent.parent.parent
        
        # Files that should be using DatabaseURLBuilder
        expected_usage_files = [
            "shared/database_url_builder.py",  # The SSOT itself
        ]
        
        usage_found = []
        
        for file_rel_path in expected_usage_files:
            file_path = project_root / file_rel_path
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if 'class DatabaseURLBuilder' in content:
                        usage_found.append({
                            'file': file_rel_path,
                            'type': 'ssot_definition',
                            'methods': []
                        })
                        
                        # Check for expected methods
                        expected_methods = ['get_url_for_environment', 'validate', 'get_safe_log_message']
                        for method in expected_methods:
                            if f'def {method}' in content:
                                usage_found[-1]['methods'].append(method)
                                
                except Exception:
                    pass
                    
        print(f"\n=== CORRECT SSOT USAGE FOUND ===")
        for usage in usage_found:
            print(f"File: {usage['file']}")
            print(f"Type: {usage['type']}")
            print(f"Methods: {usage['methods']}")
            print()
            
        # This should PASS - proving the SSOT infrastructure exists
        assert len(usage_found) > 0, "DatabaseURLBuilder SSOT infrastructure not found"
        
        # Verify essential methods exist
        all_methods = []
        for usage in usage_found:
            all_methods.extend(usage['methods'])
            
        essential_methods = ['get_url_for_environment', 'validate', 'get_safe_log_message']
        for method in essential_methods:
            assert method in all_methods, f"Essential SSOT method {method} not found in DatabaseURLBuilder"
