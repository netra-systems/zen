#!/usr/bin/env python3
"""
Focused Test Import Error Scanner
Scans only app/tests directory for import errors and generates a comprehensive report.
"""

import json
import sys
import os
import importlib.util
import traceback
from pathlib import Path
from typing import Dict, List, Any
import ast


class FocusedImportErrorScanner:
    """Scans test files for import errors and generates detailed reports."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.app_tests_path = self.base_path / "app" / "tests"
        self.results = {
            "summary": {
                "total_files_scanned": 0,
                "files_with_errors": 0,
                "total_import_errors": 0,
                "scan_timestamp": None,
                "scan_directory": str(self.app_tests_path)
            },
            "import_errors": [],
            "error_categories": {
                "module_not_found": [],
                "import_error": [],  
                "syntax_error": [],
                "circular_import": [],
                "other": []
            },
            "missing_modules": set(),
            "problematic_imports": {}
        }
    
    def extract_imports_from_ast(self, file_path: Path) -> List[str]:
        """Extract import statements from file using AST parsing."""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        
        except Exception as e:
            # Skip AST parsing errors for now
            pass
            
        return imports
    
    def test_import_by_execution(self, file_path: Path) -> Dict[str, Any]:
        """Test import by attempting to execute the file."""
        error_info = None
        
        try:
            # Add necessary directories to Python path
            paths_to_add = [
                str(self.base_path),
                str(self.base_path / "app"),
                str(file_path.parent),
            ]
            
            for path in paths_to_add:
                if path not in sys.path:
                    sys.path.insert(0, path)
            
            # Try to load the module
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[file_path.stem] = module
                spec.loader.exec_module(module)
                
        except ModuleNotFoundError as e:
            error_info = {
                "error_type": "ModuleNotFoundError",
                "error_message": str(e),
                "missing_module": e.name if hasattr(e, 'name') else "unknown",
                "traceback_lines": traceback.format_exc().split('\n')[:10]  # Limit traceback
            }
            
        except ImportError as e:
            error_info = {
                "error_type": "ImportError", 
                "error_message": str(e),
                "traceback_lines": traceback.format_exc().split('\n')[:10]
            }
            
        except SyntaxError as e:
            error_info = {
                "error_type": "SyntaxError",
                "error_message": str(e),
                "line": e.lineno,
                "traceback_lines": traceback.format_exc().split('\n')[:10]
            }
            
        except Exception as e:
            # Check if it's a circular import
            if "circular import" in str(e).lower():
                error_info = {
                    "error_type": "CircularImportError",
                    "error_message": str(e),
                    "traceback_lines": traceback.format_exc().split('\n')[:10]
                }
            else:
                error_info = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback_lines": traceback.format_exc().split('\n')[:10]
                }
        
        return error_info
    
    def categorize_error(self, error_info: Dict[str, Any]) -> str:
        """Categorize the error type."""
        error_type = error_info.get("error_type", "").lower()
        
        if "modulenotfounderror" in error_type:
            return "module_not_found"
        elif "importerror" in error_type:
            return "import_error"  
        elif "syntaxerror" in error_type:
            return "syntax_error"
        elif "circular" in error_type:
            return "circular_import"
        else:
            return "other"
    
    def scan_test_file(self, file_path: Path) -> Dict[str, Any]:
        """Scan a single test file for import errors."""
        file_result = {
            "file_path": str(file_path.relative_to(self.base_path)),
            "absolute_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "imports_found": [],
            "import_error": None,
            "has_error": False
        }
        
        # Extract imports using AST
        file_result["imports_found"] = self.extract_imports_from_ast(file_path)
        
        # Test actual import execution
        error_info = self.test_import_by_execution(file_path)
        
        if error_info:
            file_result["import_error"] = error_info
            file_result["has_error"] = True
            
            # Track missing modules
            if error_info["error_type"] == "ModuleNotFoundError":
                missing_module = error_info.get("missing_module", "unknown")
                self.results["missing_modules"].add(missing_module)
            
            # Update problematic imports
            for imp in file_result["imports_found"]:
                if imp not in self.results["problematic_imports"]:
                    self.results["problematic_imports"][imp] = []
                self.results["problematic_imports"][imp].append(str(file_path))
        
        return file_result
    
    def find_test_files(self) -> List[Path]:
        """Find all test files in app/tests directory."""
        test_files = []
        
        if not self.app_tests_path.exists():
            print(f"ERROR: app/tests directory not found at {self.app_tests_path}")
            return []
        
        # Search for test_*.py files only in app/tests
        for file_path in self.app_tests_path.rglob("test_*.py"):
            if "__pycache__" not in str(file_path):
                test_files.append(file_path)
        
        return sorted(test_files)
    
    def scan_all_tests(self) -> Dict[str, Any]:
        """Scan all test files and generate comprehensive report."""
        from datetime import datetime
        
        print("Starting focused test import error scan...")
        print(f"Scanning directory: {self.app_tests_path}")
        
        # Find all test files
        test_files = self.find_test_files()
        print(f"Found {len(test_files)} test files to scan")
        
        if not test_files:
            print("No test files found!")
            return self.results
        
        # Update summary
        self.results["summary"]["total_files_scanned"] = len(test_files)
        self.results["summary"]["scan_timestamp"] = datetime.now().isoformat()
        
        # Scan each file
        files_with_errors = 0
        total_errors = 0
        
        for i, file_path in enumerate(test_files, 1):
            if i % 50 == 0:  # Progress indicator
                print(f"Progress: {i}/{len(test_files)} files scanned")
            
            try:
                file_result = self.scan_test_file(file_path)
                
                if file_result["has_error"]:
                    files_with_errors += 1
                    total_errors += 1
                    
                    # Add to import errors list
                    self.results["import_errors"].append(file_result)
                    
                    # Categorize error
                    error_info = file_result["import_error"]
                    category = self.categorize_error(error_info)
                    self.results["error_categories"][category].append(file_result)
                    
                    print(f"ERROR in {file_path.name}: {error_info['error_type']} - {error_info['error_message'][:100]}...")
                    
            except Exception as e:
                print(f"SCAN FAILED for {file_path.name}: {e}")
                total_errors += 1
        
        # Update final summary
        self.results["summary"]["files_with_errors"] = files_with_errors
        self.results["summary"]["total_import_errors"] = total_errors
        
        # Convert sets to lists for JSON serialization
        self.results["missing_modules"] = sorted(list(self.results["missing_modules"]))
        
        print(f"\nScan completed:")
        print(f"   • Total files scanned: {len(test_files)}")
        print(f"   • Files with errors: {files_with_errors}")
        print(f"   • Total import errors: {total_errors}")
        
        return self.results
    
    def save_report(self, output_file: str = "test_import_errors_report.json"):
        """Save the scan results to JSON file."""
        output_path = self.base_path / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"Report saved to: {output_path}")
        return output_path
    
    def print_summary_report(self):
        """Print a human-readable summary of findings."""
        print("\n" + "="*80)
        print("TEST IMPORT ERRORS SUMMARY REPORT")
        print("="*80)
        
        summary = self.results["summary"]
        print(f"Scan Directory: {summary['scan_directory']}")
        print(f"Scan Statistics:")
        print(f"   • Total files scanned: {summary['total_files_scanned']}")
        print(f"   • Files with errors: {summary['files_with_errors']}")
        print(f"   • Total import errors: {summary['total_import_errors']}")
        if summary['total_files_scanned'] > 0:
            print(f"   • Error rate: {summary['files_with_errors']/summary['total_files_scanned']*100:.1f}%")
        
        print(f"\nError Categories:")
        categories = self.results["error_categories"]
        for category, errors in categories.items():
            if errors:
                print(f"   • {category.replace('_', ' ').title()}: {len(errors)} files")
        
        print(f"\nTop 15 Missing Modules:")
        missing_modules = self.results["missing_modules"]
        for i, module in enumerate(missing_modules[:15], 1):
            print(f"   {i:2d}. {module}")
        
        if len(missing_modules) > 15:
            print(f"   ... and {len(missing_modules) - 15} more")
        
        print(f"\nSample Import Errors (First 10):")
        for i, error in enumerate(self.results["import_errors"][:10], 1):
            print(f"   {i}. {error['file_path']}")
            print(f"      ERROR: {error['import_error']['error_type']} - {error['import_error']['error_message'][:80]}...")
        
        if len(self.results["import_errors"]) > 10:
            print(f"   ... and {len(self.results['import_errors']) - 10} more errors")


def main():
    """Main function to run the import error scanner."""
    base_path = Path(__file__).parent
    
    print("Focused Test Import Error Scanner")
    print("="*50)
    print("Task: Scan app/tests directory for import errors")
    print("Output: Comprehensive JSON report of all import issues")
    print("")
    
    # Initialize scanner
    scanner = FocusedImportErrorScanner(str(base_path))
    
    # Scan all tests
    results = scanner.scan_all_tests()
    
    # Save detailed JSON report
    report_path = scanner.save_report()
    
    # Print human-readable summary
    scanner.print_summary_report()
    
    print(f"\nFocused import error scan completed!")
    print(f"Full report available at: {report_path}")
    
    return results


if __name__ == "__main__":
    main()