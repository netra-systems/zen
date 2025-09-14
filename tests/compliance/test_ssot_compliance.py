
"""
SSOT Compliance Validation Test
==============================
Validates that test infrastructure follows SSOT patterns
"""

import unittest
from pathlib import Path
import sys
import re

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class SSotComplianceTest(unittest.TestCase):
    """Validates SSOT compliance across test infrastructure"""
    
    def test_ssot_base_classes_usage(self):
        """Test that tests use SSOT base classes"""
        test_files = list(PROJECT_ROOT.rglob("*test*.py"))
        
        non_compliant_files = []
        for file_path in test_files[:20]:  # Sample check
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check if using unittest.TestCase without SSOT
                if 'unittest.TestCase' in content and 'SSot' not in content:
                    non_compliant_files.append(str(file_path))
                    
            except Exception:
                continue
        
        self.assertLess(
            len(non_compliant_files), 5,
            f"Found {len(non_compliant_files)} files not using SSOT base classes: {non_compliant_files[:3]}"
        )
    
    def test_unified_setup_methods(self):
        """Test that setup methods are standardized"""
        test_files = list(PROJECT_ROOT.rglob("*test*.py"))
        
        conflicting_files = []
        for file_path in test_files[:20]:  # Sample check
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check for setUp vs setup_method conflicts
                if 'def setUp(' in content and 'def setup_method(' in content:
                    conflicting_files.append(str(file_path))
                    
            except Exception:
                continue
        
        self.assertEqual(
            len(conflicting_files), 0,
            f"Found {len(conflicting_files)} files with setup method conflicts: {conflicting_files}"
        )
    
    def test_golden_path_context_requirements(self):
        """Test that golden path tests have proper context"""
        golden_path_files = []
        for test_dir in [PROJECT_ROOT / "tests", PROJECT_ROOT / "netra_backend" / "tests"]:
            if test_dir.exists():
                golden_path_files.extend(test_dir.rglob("*golden_path*.py"))
        
        missing_context = []
        for file_path in golden_path_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                if 'UserExecutionContext' not in content:
                    missing_context.append(str(file_path))
                    
            except Exception:
                continue
        
        self.assertLess(
            len(missing_context), 2,
            f"Golden path files missing UserExecutionContext: {missing_context}"
        )

if __name__ == '__main__':
    unittest.main()
