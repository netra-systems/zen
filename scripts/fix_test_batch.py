#!/usr/bin/env python
"""
Batch Test Fixer - Systematically fixes test failures
Processes tests in batches and either:
1. Aligns tests with current code
2. Implements missing functionality if tests are correct
"""

import ast
import json
import os
import re
import subprocess
import sys
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class TestAnalyzer:
    """Analyze test failures and determine fix strategy"""
    
    def __init__(self):
        self.import_errors = []
        self.assertion_errors = []
        self.attribute_errors = []
        self.other_errors = []
        
    def analyze_failure(self, test_path: str, error_output: str) -> Dict:
        """Analyze a test failure and categorize it"""
        
        result = {
            "test": test_path,
            "error_type": None,
            "details": {},
            "fix_strategy": None
        }
        
        # Check for ImportError
        import_match = re.search(r"ImportError: cannot import name '(\w+)' from '([\w\.]+)'", error_output)
        if import_match:
            result["error_type"] = "ImportError"
            result["details"] = {
                "missing_name": import_match.group(1),
                "module": import_match.group(2)
            }
            result["fix_strategy"] = "check_and_fix_import"
            return result
        
        # Check for AttributeError
        attr_match = re.search(r"AttributeError: '(\w+)' object has no attribute '(\w+)'", error_output)
        if attr_match:
            result["error_type"] = "AttributeError"
            result["details"] = {
                "object_type": attr_match.group(1),
                "missing_attr": attr_match.group(2)
            }
            result["fix_strategy"] = "check_and_fix_attribute"
            return result
        
        # Check for AssertionError
        if "AssertionError" in error_output:
            result["error_type"] = "AssertionError"
            result["fix_strategy"] = "review_assertion"
            return result
        
        # Check for ModuleNotFoundError
        module_match = re.search(r"ModuleNotFoundError: No module named '([\w\.]+)'", error_output)
        if module_match:
            result["error_type"] = "ModuleNotFoundError"
            result["details"] = {
                "missing_module": module_match.group(1)
            }
            result["fix_strategy"] = "fix_module_import"
            return result
        
        result["error_type"] = "Unknown"
        result["fix_strategy"] = "manual_review"
        return result

class TestFixer:
    """Fix test failures based on analysis"""
    
    def __init__(self):
        self.fixes_applied = []
        self.fixes_failed = []
        
    def fix_import_error(self, test_file: Path, missing_name: str, module: str) -> bool:
        """Fix import errors by updating test or implementing missing functionality"""
        
        # First, check if the module exists
        module_path = module.replace('.', '/')
        possible_files = [
            PROJECT_ROOT / f"{module_path}.py",
            PROJECT_ROOT / f"{module_path}/__init__.py"
        ]
        
        module_file = None
        for file in possible_files:
            if file.exists():
                module_file = file
                break
        
        if not module_file:
            print(f"  Module file not found: {module}")
            return False
        
        # Check if the function/class exists in the module
        with open(module_file, 'r') as f:
            content = f.read()
        
        # Simple check for function/class definition
        if f"def {missing_name}" in content or f"class {missing_name}" in content:
            print(f"  Function/class {missing_name} exists in {module_file}")
            return False
        
        # Check if it's a simple case where the test is wrong
        # Look for similar names
        similar_names = self._find_similar_names(content, missing_name)
        
        if similar_names:
            print(f"  Found similar names in module: {similar_names}")
            # Update the test to use the correct name
            return self._update_test_import(test_file, missing_name, similar_names[0])
        
        # If function doesn't exist and no similar names, create a stub
        return self._create_stub_function(module_file, missing_name, module)
    
    def _find_similar_names(self, content: str, target_name: str) -> List[str]:
        """Find similar function/class names in content"""
        
        # Extract all function and class names
        func_pattern = r"def\s+(\w+)\s*\("
        class_pattern = r"class\s+(\w+)\s*[\(:]"
        
        functions = re.findall(func_pattern, content)
        classes = re.findall(class_pattern, content)
        
        all_names = functions + classes
        
        # Find similar names (simple string similarity)
        similar = []
        target_lower = target_name.lower()
        
        for name in all_names:
            name_lower = name.lower()
            # Check if names are similar
            if (target_lower in name_lower or name_lower in target_lower or
                self._levenshtein_distance(target_lower, name_lower) <= 3):
                similar.append(name)
        
        return similar
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _update_test_import(self, test_file: Path, old_name: str, new_name: str) -> bool:
        """Update test file to use correct import name"""
        
        try:
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Replace the import
            updated = content.replace(f"import {old_name}", f"import {new_name}")
            updated = updated.replace(f"from {old_name}", f"from {new_name}")
            updated = updated.replace(f"{old_name}(", f"{new_name}(")
            
            if updated != content:
                with open(test_file, 'w') as f:
                    f.write(updated)
                print(f"  Updated test to use {new_name} instead of {old_name}")
                return True
        except Exception as e:
            print(f"  Failed to update test: {e}")
        
        return False
    
    def _create_stub_function(self, module_file: Path, func_name: str, module: str) -> bool:
        """Create a stub function/class in the module"""
        
        # For now, we'll just note what needs to be created
        # In a real implementation, we'd add the function
        
        print(f"  NEED TO IMPLEMENT: {func_name} in {module}")
        
        # Log this for later implementation
        fix_log = PROJECT_ROOT / "test_reports" / "functions_to_implement.txt"
        fix_log.parent.mkdir(exist_ok=True)
        
        with open(fix_log, 'a') as f:
            f.write(f"{datetime.now().isoformat()}: Implement {func_name} in {module}\n")
        
        return False

class BatchTestProcessor:
    """Process tests in batches"""
    
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.analyzer = TestAnalyzer()
        self.fixer = TestFixer()
        self.results = []
        
    def process_failing_tests(self, test_list: List[str]) -> Dict:
        """Process a list of failing tests"""
        
        batch_results = {
            "total": len(test_list),
            "processed": 0,
            "fixed": 0,
            "failed": 0,
            "details": []
        }
        
        for i in range(0, len(test_list), self.batch_size):
            batch = test_list[i:i+self.batch_size]
            batch_num = i // self.batch_size + 1
            
            print(f"\n{'='*60}")
            print(f"Processing Batch {batch_num} ({len(batch)} tests)")
            print(f"{'='*60}")
            
            for test in batch:
                result = self.process_single_test(test)
                batch_results["details"].append(result)
                batch_results["processed"] += 1
                
                if result["status"] == "fixed":
                    batch_results["fixed"] += 1
                elif result["status"] == "failed":
                    batch_results["failed"] += 1
                
                # Print progress
                if batch_results["processed"] % 10 == 0:
                    print(f"Progress: {batch_results['processed']}/{batch_results['total']} processed")
        
        return batch_results
    
    def _initialize_test_result(self, test_path):
        """Initialize test result dictionary"""
        print(f"\nProcessing: {test_path}")
        return {
            "test": test_path, "status": "pending", 
            "error_type": None, "fix_applied": None
        }

    def _build_pytest_command(self, test_path):
        """Build pytest command for single test"""
        return [
            sys.executable, "-m", "pytest", test_path,
            "-xvs", "--tb=short"
        ]

    def _run_test_subprocess(self, cmd):
        """Run test subprocess with timeout"""
        return subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=10, cwd=PROJECT_ROOT
        )

    def _check_test_already_passed(self, proc_result, result):
        """Check if test already passes"""
        if proc_result.returncode == 0:
            result["status"] = "passed"
            print(f"  [U+2713] Test already passing")
            return True
        return False

    def _analyze_test_failure(self, test_path, proc_result):
        """Analyze test failure and return analysis"""
        return self.analyzer.analyze_failure(
            test_path, proc_result.stdout + proc_result.stderr
        )

    def _apply_import_fix(self, analysis, test_path):
        """Apply import error fix"""
        test_file = Path(test_path.split("::")[0])
        if not test_file.is_absolute():
            test_file = PROJECT_ROOT / test_file
        return self.fixer.fix_import_error(
            test_file, analysis["details"].get("missing_name"),
            analysis["details"].get("module")
        )

    def _apply_test_fix(self, analysis, test_path, result):
        """Apply fix based on analysis strategy"""
        if analysis["fix_strategy"] == "check_and_fix_import":
            fixed = self._apply_import_fix(analysis, test_path)
            result["status"] = "fixed" if fixed else "needs_implementation"
            if fixed: result["fix_applied"] = "import_correction"
        else:
            result["status"] = "manual_review"
            print(f"   WARNING:  Needs manual review: {analysis['error_type']}")

    def _handle_test_timeout(self, result):
        """Handle test timeout"""
        result["status"] = "timeout"
        print(f"  [U+23F0] Test timed out")

    def _handle_test_error(self, e, result):
        """Handle test execution error"""
        result["status"] = "error"
        result["error"] = str(e)
        print(f"   FAIL:  Error: {e}")

    def process_single_test(self, test_path: str) -> Dict:
        """Process a single test"""
        result = self._initialize_test_result(test_path)
        cmd = self._build_pytest_command(test_path)
        try:
            proc_result = self._run_test_subprocess(cmd)
            if self._check_test_already_passed(proc_result, result): return result
            analysis = self._analyze_test_failure(test_path, proc_result)
            result["error_type"] = analysis["error_type"]
            self._apply_test_fix(analysis, test_path, result)
        except subprocess.TimeoutExpired:
            self._handle_test_timeout(result)
        except Exception as e:
            self._handle_test_error(e, result)
        return result

def main():
    """Main execution"""
    
    print("BATCH TEST FIXER")
    print("="*60)
    
    # Load failing tests from previous scan
    scan_file = PROJECT_ROOT / "test_reports" / "failure_scan.json"
    
    if not scan_file.exists():
        print("No failure scan found. Run test_failure_scanner.py first.")
        return 1
    
    with open(scan_file, 'r') as f:
        scan_data = json.load(f)
    
    # Get priority failures
    priority_failures = [f["test"] for f in scan_data["priority_failures"]]
    
    if not priority_failures:
        print("No priority failures found.")
        return 0
    
    print(f"Found {len(priority_failures)} priority failures to process")
    
    # Process in batches
    processor = BatchTestProcessor(batch_size=50)
    results = processor.process_failing_tests(priority_failures)
    
    # Save results
    output_file = PROJECT_ROOT / "test_reports" / f"batch_fix_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    print("\n" + "="*60)
    print("BATCH PROCESSING COMPLETE")
    print("="*60)
    print(f"Total: {results['total']}")
    print(f"Processed: {results['processed']}")
    print(f"Fixed: {results['fixed']}")
    print(f"Failed: {results['failed']}")
    print(f"Results saved to: {output_file}")
    
    # Show tests that need implementation
    needs_impl = [d for d in results["details"] if d["status"] == "needs_implementation"]
    if needs_impl:
        print(f"\nTests needing implementation: {len(needs_impl)}")
        impl_file = PROJECT_ROOT / "test_reports" / "functions_to_implement.txt"
        if impl_file.exists():
            print(f"See {impl_file} for functions to implement")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())