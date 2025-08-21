#!/usr/bin/env python
"""
Frontend Test Validation Script
Validates that frontend tests can run and identifies any setup issues.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
TESTS_DIR = FRONTEND_DIR / "__tests__"


class FrontendTestValidator:
    """Validates frontend test setup and execution."""
    
    def __init__(self):
        self.issues = []
        self.test_categories = {}
        self.test_files = []
        self.missing_imports = set()
        
    def validate(self) -> Tuple[bool, Dict]:
        """Run all validation checks."""
        print("=" * 60)
        print("FRONTEND TEST VALIDATION")
        print("=" * 60)
        
        # Check 1: Verify test directory exists
        if not TESTS_DIR.exists():
            self.issues.append(f"Test directory not found: {TESTS_DIR}")
            return False, self._generate_report()
        
        # Check 2: Count test files by category
        self._discover_test_files()
        
        # Check 3: Verify Jest configuration
        self._check_jest_config()
        
        # Check 4: Check for common import issues
        self._check_imports()
        
        # Check 5: Try running a simple test
        self._test_execution()
        
        # Generate report
        report = self._generate_report()
        success = len(self.issues) == 0
        
        return success, report
    
    def _discover_test_files(self):
        """Discover all test files and categorize them."""
        print("\n[1/5] Discovering test files...")
        
        for root, dirs, files in os.walk(TESTS_DIR):
            # Get category from directory structure
            rel_path = Path(root).relative_to(TESTS_DIR)
            category = str(rel_path).replace(os.sep, "/")
            if category == ".":
                category = "root"
            
            # Count test files in this category
            test_files = [f for f in files if f.endswith(('.test.tsx', '.test.ts', '.test.jsx', '.test.js'))]
            if test_files:
                if category not in self.test_categories:
                    self.test_categories[category] = []
                self.test_categories[category].extend(test_files)
                self.test_files.extend([Path(root) / f for f in test_files])
        
        total_files = sum(len(files) for files in self.test_categories.values())
        print(f"  [OK] Found {total_files} test files across {len(self.test_categories)} categories")
        
        # Show top categories
        sorted_categories = sorted(self.test_categories.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for category, files in sorted_categories:
            print(f"    - {category}: {len(files)} files")
    
    def _check_jest_config(self):
        """Check Jest configuration files."""
        print("\n[2/5] Checking Jest configuration...")
        
        config_files = [
            "jest.config.js",
            "jest.config.cjs",
            "jest.config.unified.cjs",
            "jest.config.json"
        ]
        
        found_configs = []
        for config in config_files:
            config_path = FRONTEND_DIR / config
            if config_path.exists():
                found_configs.append(config)
        
        if not found_configs:
            self.issues.append("No Jest configuration file found")
            print("  [FAIL] No Jest configuration found")
        else:
            print(f"  [OK] Found Jest configs: {', '.join(found_configs)}")
    
    def _check_imports(self):
        """Check for common import issues in test files."""
        print("\n[3/5] Checking for import issues...")
        
        # Sample a few test files to check imports
        sample_files = self.test_files[:10] if len(self.test_files) > 10 else self.test_files
        
        common_imports = {
            "../test-utils": "Common test utilities",
            "../setup/websocket-test-utils": "WebSocket test utilities",
            "./test-utils": "Local test utilities",
            "@testing-library/react": "React Testing Library",
            "jest-websocket-mock": "WebSocket mocking library"
        }
        
        import_issues = []
        for test_file in sample_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for import_path, description in common_imports.items():
                    if f"from '{import_path}'" in content or f'from "{import_path}"' in content:
                        # Check if the imported file exists
                        if import_path.startswith('.'):
                            resolved_path = (test_file.parent / import_path.replace('/', os.sep)).resolve()
                            # Try with different extensions
                            exists = False
                            for ext in ['.ts', '.tsx', '.js', '.jsx', '']:
                                check_path = Path(str(resolved_path) + ext)
                                if check_path.exists() or check_path.is_dir():
                                    exists = True
                                    break
                            
                            if not exists:
                                self.missing_imports.add(import_path)
                                import_issues.append(f"{test_file.name}: Missing {description}")
            except Exception as e:
                pass
        
        if self.missing_imports:
            print(f"  [WARN] Found {len(self.missing_imports)} missing imports")
            for imp in list(self.missing_imports)[:3]:
                print(f"    - {imp}")
        else:
            print("  [OK] No import issues detected in sample")
    
    def _test_execution(self):
        """Try to run a simple test command."""
        print("\n[4/5] Testing execution capability...")
        
        try:
            # Save current directory
            original_dir = os.getcwd()
            
            # Change to frontend directory first
            os.chdir(FRONTEND_DIR)
            
            # Try to list tests
            result = subprocess.run(
                "npm test -- --listTests",
                capture_output=True,
                text=True,
                timeout=30,
                shell=True  # Use shell on Windows for npm
            )
            
            # Restore original directory
            os.chdir(original_dir)
            
            if result.returncode == 0:
                # Count listed tests
                test_count = len([line for line in result.stdout.split('\n') if line.strip().endswith('.tsx') or line.strip().endswith('.ts')])
                print(f"  [OK] Jest can list {test_count} test files")
            else:
                self.issues.append("Jest cannot list tests")
                print("  [FAIL] Jest cannot list tests")
                if "Cannot find module" in result.stderr:
                    print("    Issue: Module resolution errors")
        except subprocess.TimeoutExpired:
            self.issues.append("Test listing timed out")
            print("  [FAIL] Test listing timed out")
        except Exception as e:
            self.issues.append(f"Test execution error: {e}")
            print(f"  [FAIL] Error: {e}")
    
    def _generate_report(self) -> Dict:
        """Generate validation report."""
        return {
            "valid": len(self.issues) == 0,
            "issues": self.issues,
            "stats": {
                "total_test_files": len(self.test_files),
                "categories": len(self.test_categories),
                "category_breakdown": {k: len(v) for k, v in self.test_categories.items()},
                "missing_imports": list(self.missing_imports)
            },
            "recommendations": self._get_recommendations()
        }
    
    def _get_recommendations(self) -> List[str]:
        """Get recommendations based on issues found."""
        recommendations = []
        
        if self.missing_imports:
            recommendations.append("Fix missing test utility imports")
            recommendations.append("Run: python scripts/fix_frontend_test_imports.py")
        
        if "Jest cannot list tests" in self.issues:
            recommendations.append("Fix Jest configuration issues")
            recommendations.append("Check jest.config.unified.cjs setup")
        
        if not self.test_files:
            recommendations.append("No test files found - check test directory structure")
        
        return recommendations


def main():
    """Main entry point."""
    validator = FrontendTestValidator()
    success, report = validator.validate()
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    if success:
        print("[OK] Frontend tests are properly configured")
        print(f"  - {report['stats']['total_test_files']} test files found")
        print(f"  - {report['stats']['categories']} test categories")
    else:
        print("[FAIL] Frontend test setup has issues:")
        for issue in report['issues']:
            print(f"  - {issue}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  -> {rec}")
    
    # Save report
    report_file = PROJECT_ROOT / "test_reports" / "frontend_validation.json"
    report_file.parent.mkdir(exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to: {report_file}")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())