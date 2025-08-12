#!/usr/bin/env python
"""
Improved Test Runner with Better Parallelization and Organization
"""

import os
import sys
import json
import time
import subprocess
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class ImprovedTestRunner:
    """Enhanced test runner with better parallelization and organization"""
    
    def __init__(self):
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Determine optimal worker count
        self.cpu_count = multiprocessing.cpu_count()
        self.optimal_workers = min(self.cpu_count - 1, 8)  # Leave one CPU free
        
        self.test_groups = {
            "backend": {
                "unit": [],
                "integration": [],
                "service": [],
                "api": [],
                "database": [],
                "agent": [],
                "websocket": [],
                "auth": [],
                "llm": [],
                "other": []
            },
            "frontend": {
                "component": [],
                "hook": [],
                "service": [],
                "store": [],
                "auth": [],
                "websocket": [],
                "utility": [],
                "other": []
            }
        }
        
        self.results = {
            "passed": [],
            "failed": [],
            "skipped": [],
            "errors": [],
            "timeouts": []
        }
        
    def discover_backend_tests(self) -> List[str]:
        """Discover all backend test files"""
        test_files = []
        test_dir = PROJECT_ROOT / "app" / "tests"
        
        if test_dir.exists():
            for test_file in test_dir.rglob("test_*.py"):
                test_files.append(str(test_file.relative_to(PROJECT_ROOT)))
        
        return test_files
    
    def discover_frontend_tests(self) -> List[str]:
        """Discover all frontend test files"""
        test_files = []
        frontend_dir = PROJECT_ROOT / "frontend"
        
        # Look for test files
        for pattern in ["**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts", "**/*.spec.tsx"]:
            for test_file in frontend_dir.glob(pattern):
                test_files.append(str(test_file.relative_to(PROJECT_ROOT)))
        
        return test_files
    
    def categorize_backend_test(self, test_file: str) -> str:
        """Categorize backend test based on file path"""
        file_lower = test_file.lower()
        
        if "unit" in file_lower:
            return "unit"
        elif "integration" in file_lower:
            return "integration"
        elif "service" in file_lower:
            return "service"
        elif "route" in file_lower or "api" in file_lower:
            return "api"
        elif "database" in file_lower or "repository" in file_lower:
            return "database"
        elif "agent" in file_lower:
            return "agent"
        elif "websocket" in file_lower or "ws_" in file_lower:
            return "websocket"
        elif "auth" in file_lower or "security" in file_lower:
            return "auth"
        elif "llm" in file_lower:
            return "llm"
        else:
            return "other"
    
    def categorize_frontend_test(self, test_file: str) -> str:
        """Categorize frontend test based on file path"""
        file_lower = test_file.lower()
        
        if "component" in file_lower:
            return "component"
        elif "hook" in file_lower:
            return "hook"
        elif "service" in file_lower or "api" in file_lower:
            return "service"
        elif "store" in file_lower:
            return "store"
        elif "auth" in file_lower:
            return "auth"
        elif "websocket" in file_lower or "ws" in file_lower:
            return "websocket"
        elif "util" in file_lower or "helper" in file_lower:
            return "utility"
        else:
            return "other"
    
    def organize_tests(self):
        """Organize tests into categories"""
        print("Discovering and organizing tests...")
        
        # Discover backend tests
        backend_tests = self.discover_backend_tests()
        for test_file in backend_tests:
            category = self.categorize_backend_test(test_file)
            self.test_groups["backend"][category].append(test_file)
        
        # Discover frontend tests
        frontend_tests = self.discover_frontend_tests()
        for test_file in frontend_tests:
            category = self.categorize_frontend_test(test_file)
            self.test_groups["frontend"][category].append(test_file)
        
        # Print summary
        print("\nTest Organization Summary:")
        print("="*50)
        
        total_backend = sum(len(tests) for tests in self.test_groups["backend"].values())
        print(f"Backend Tests: {total_backend}")
        for category, tests in self.test_groups["backend"].items():
            if tests:
                print(f"  {category}: {len(tests)}")
        
        total_frontend = sum(len(tests) for tests in self.test_groups["frontend"].values())
        print(f"\nFrontend Tests: {total_frontend}")
        for category, tests in self.test_groups["frontend"].items():
            if tests:
                print(f"  {category}: {len(tests)}")
        
        print(f"\nTotal Tests: {total_backend + total_frontend}")
        print("="*50)
    
    def run_backend_test_group(self, category: str, test_files: List[str], 
                              timeout: int = 60) -> Dict:
        """Run a group of backend tests"""
        if not test_files:
            return {"category": category, "passed": 0, "failed": 0, "errors": 0}
        
        print(f"\nRunning backend {category} tests ({len(test_files)} files)...")
        
        results = {"category": category, "passed": 0, "failed": 0, "errors": 0, "failures": []}
        
        # Run tests with parallelization based on category
        parallel = self.optimal_workers if category != "database" else 1  # Database tests run sequentially
        
        cmd = [
            sys.executable, "-m", "pytest",
            "--tb=short",
            "--no-header",
            "-q",
            f"-n={parallel}" if parallel > 1 else "",
            "--timeout", str(timeout)
        ] + test_files
        
        # Filter out empty string from cmd
        cmd = [c for c in cmd if c]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=timeout * len(test_files),
                encoding='utf-8',
                errors='replace'
            )
            
            # Parse results
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'passed' in line:
                    try:
                        results["passed"] += int(line.split()[0])
                    except:
                        pass
                elif 'failed' in line:
                    try:
                        results["failed"] += int(line.split()[0])
                    except:
                        pass
                elif 'error' in line:
                    try:
                        results["errors"] += int(line.split()[0])
                    except:
                        pass
                elif 'FAILED' in line:
                    results["failures"].append(line)
            
            print(f"  Completed: {results['passed']} passed, {results['failed']} failed, {results['errors']} errors")
            
        except subprocess.TimeoutExpired:
            print(f"  Timeout for {category} tests")
            results["errors"] += len(test_files)
        except Exception as e:
            print(f"  Error running {category} tests: {e}")
            results["errors"] += len(test_files)
        
        return results
    
    def run_frontend_test_group(self, category: str, test_files: List[str],
                               timeout: int = 60) -> Dict:
        """Run a group of frontend tests"""
        if not test_files:
            return {"category": category, "passed": 0, "failed": 0, "errors": 0}
        
        print(f"\nRunning frontend {category} tests ({len(test_files)} files)...")
        
        results = {"category": category, "passed": 0, "failed": 0, "errors": 0, "failures": []}
        
        # Create temporary test list file
        test_list_file = self.reports_dir / f"frontend_{category}_tests.txt"
        with open(test_list_file, 'w') as f:
            for test_file in test_files:
                # Convert to relative path from frontend dir
                rel_path = Path(test_file).relative_to("frontend")
                f.write(str(rel_path) + '\n')
        
        try:
            # Run Jest with specific test files
            cmd = [
                "npm", "test", "--",
                "--listTests",
                "--findRelatedTests",
                str(test_list_file),
                "--maxWorkers", str(self.optimal_workers),
                "--no-coverage",
                "--json",
                "--outputFile", f"test-results-{category}.json"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT / "frontend",
                capture_output=True,
                text=True,
                timeout=timeout * len(test_files),
                encoding='utf-8',
                errors='replace'
            )
            
            # Parse JSON results if available
            results_file = PROJECT_ROOT / "frontend" / f"test-results-{category}.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    test_results = json.load(f)
                    
                    if "numPassedTests" in test_results:
                        results["passed"] = test_results["numPassedTests"]
                    if "numFailedTests" in test_results:
                        results["failed"] = test_results["numFailedTests"]
                    
                    # Extract failures
                    for suite in test_results.get("testResults", []):
                        for assertion in suite.get("assertionResults", []):
                            if assertion["status"] == "failed":
                                results["failures"].append(f"{suite['name']}::{assertion['title']}")
                
                # Clean up
                results_file.unlink()
            
            print(f"  Completed: {results['passed']} passed, {results['failed']} failed")
            
        except subprocess.TimeoutExpired:
            print(f"  Timeout for {category} tests")
            results["errors"] += len(test_files)
        except Exception as e:
            print(f"  Error running {category} tests: {e}")
            results["errors"] += len(test_files)
        finally:
            # Clean up test list file
            if test_list_file.exists():
                test_list_file.unlink()
        
        return results
    
    def run_parallel_test_groups(self, component: str):
        """Run test groups in parallel with proper organization"""
        print(f"\n{'='*60}")
        print(f"RUNNING {component.upper()} TESTS IN PARALLEL")
        print(f"Using {self.optimal_workers} workers")
        print(f"{'='*60}")
        
        all_results = []
        
        # Determine which groups to run in parallel
        test_groups = self.test_groups[component]
        
        # Group by priority - some groups should run sequentially
        sequential_groups = ["database", "auth"]  # These often have conflicts
        parallel_groups = [g for g in test_groups if g not in sequential_groups]
        
        # Run parallel groups
        with ThreadPoolExecutor(max_workers=self.optimal_workers) as executor:
            futures = {}
            
            for category, tests in test_groups.items():
                if tests and category in parallel_groups:
                    if component == "backend":
                        future = executor.submit(self.run_backend_test_group, category, tests)
                    else:
                        future = executor.submit(self.run_frontend_test_group, category, tests)
                    futures[future] = category
            
            for future in as_completed(futures):
                category = futures[future]
                try:
                    result = future.result()
                    all_results.append(result)
                except Exception as e:
                    print(f"Error running {category} tests: {e}")
        
        # Run sequential groups
        for category in sequential_groups:
            if test_groups[category]:
                print(f"\nRunning {category} tests sequentially...")
                if component == "backend":
                    result = self.run_backend_test_group(category, test_groups[category])
                else:
                    result = self.run_frontend_test_group(category, test_groups[category])
                all_results.append(result)
        
        return all_results
    
    def generate_comprehensive_report(self, backend_results: List[Dict], 
                                     frontend_results: List[Dict]):
        """Generate comprehensive test report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"comprehensive_report_{timestamp}.md"
        
        # Calculate totals
        backend_totals = {"passed": 0, "failed": 0, "errors": 0}
        frontend_totals = {"passed": 0, "failed": 0, "errors": 0}
        all_failures = []
        
        for result in backend_results:
            backend_totals["passed"] += result["passed"]
            backend_totals["failed"] += result["failed"]
            backend_totals["errors"] += result["errors"]
            for failure in result.get("failures", []):
                all_failures.append({"component": "backend", "category": result["category"], "failure": failure})
        
        for result in frontend_results:
            frontend_totals["passed"] += result["passed"]
            frontend_totals["failed"] += result["failed"]
            frontend_totals["errors"] += result["errors"]
            for failure in result.get("failures", []):
                all_failures.append({"component": "frontend", "category": result["category"], "failure": failure})
        
        with open(report_file, 'w') as f:
            f.write("# Comprehensive Test Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**CPU Count:** {self.cpu_count}\n")
            f.write(f"**Workers Used:** {self.optimal_workers}\n\n")
            
            f.write("## Summary\n\n")
            
            total_tests = sum(backend_totals.values()) + sum(frontend_totals.values())
            total_passed = backend_totals["passed"] + frontend_totals["passed"]
            total_failed = backend_totals["failed"] + frontend_totals["failed"]
            total_errors = backend_totals["errors"] + frontend_totals["errors"]
            
            f.write(f"**Total Tests:** {total_tests}\n")
            f.write(f"- Passed: {total_passed}\n")
            f.write(f"- Failed: {total_failed}\n")
            f.write(f"- Errors: {total_errors}\n\n")
            
            f.write("### Backend Results\n\n")
            f.write(f"- Total: {sum(backend_totals.values())}\n")
            f.write(f"- Passed: {backend_totals['passed']}\n")
            f.write(f"- Failed: {backend_totals['failed']}\n")
            f.write(f"- Errors: {backend_totals['errors']}\n\n")
            
            f.write("| Category | Passed | Failed | Errors |\n")
            f.write("|----------|--------|--------|--------|\n")
            for result in backend_results:
                f.write(f"| {result['category']} | {result['passed']} | {result['failed']} | {result['errors']} |\n")
            
            f.write("\n### Frontend Results\n\n")
            f.write(f"- Total: {sum(frontend_totals.values())}\n")
            f.write(f"- Passed: {frontend_totals['passed']}\n")
            f.write(f"- Failed: {frontend_totals['failed']}\n")
            f.write(f"- Errors: {frontend_totals['errors']}\n\n")
            
            f.write("| Category | Passed | Failed | Errors |\n")
            f.write("|----------|--------|--------|--------|\n")
            for result in frontend_results:
                f.write(f"| {result['category']} | {result['passed']} | {result['failed']} | {result['errors']} |\n")
            
            f.write("\n## All Failures\n\n")
            
            # Group failures by category
            failures_by_category = {}
            for failure_info in all_failures:
                key = f"{failure_info['component']}/{failure_info['category']}"
                if key not in failures_by_category:
                    failures_by_category[key] = []
                failures_by_category[key].append(failure_info['failure'])
            
            for category, failures in sorted(failures_by_category.items()):
                f.write(f"\n### {category}\n\n")
                for i, failure in enumerate(failures[:50], 1):  # Limit to 50 per category
                    f.write(f"{i}. {failure}\n")
                if len(failures) > 50:
                    f.write(f"... and {len(failures) - 50} more\n")
        
        print(f"\nReport saved to: {report_file}")
        
        # Save JSON version for processing
        json_file = self.reports_dir / f"comprehensive_report_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "backend_results": backend_results,
                "frontend_results": frontend_results,
                "failures": all_failures,
                "totals": {
                    "backend": backend_totals,
                    "frontend": frontend_totals,
                    "overall": {
                        "passed": total_passed,
                        "failed": total_failed,
                        "errors": total_errors
                    }
                }
            }, f, indent=2)
        
        print(f"JSON report saved to: {json_file}")
        
        return all_failures[:200]  # Return top 200 failures for processing
    
    def run_comprehensive_tests(self):
        """Run comprehensive test suite with improved organization"""
        start_time = time.time()
        
        # Organize tests
        self.organize_tests()
        
        # Run backend tests in parallel groups
        backend_results = self.run_parallel_test_groups("backend")
        
        # Run frontend tests in parallel groups
        frontend_results = self.run_parallel_test_groups("frontend")
        
        # Generate report
        top_failures = self.generate_comprehensive_report(backend_results, frontend_results)
        
        duration = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"COMPREHENSIVE TEST RUN COMPLETED")
        print(f"Duration: {duration:.2f} seconds")
        print(f"{'='*60}")
        
        return top_failures

def main():
    runner = ImprovedTestRunner()
    top_failures = runner.run_comprehensive_tests()
    
    # Save top failures for processing
    with open(runner.reports_dir / "top_200_failures.json", 'w') as f:
        json.dump(top_failures, f, indent=2)
    
    print(f"\nTop 200 failures saved for processing")

if __name__ == "__main__":
    main()