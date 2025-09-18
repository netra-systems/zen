#!/usr/bin/env python3
"""
Comprehensive AgentRegistry SSOT Violation Test Runner (Issue #914)

This script runs all AgentRegistry SSOT violation tests to demonstrate the
critical conflicts blocking Golden Path functionality. These tests are
DESIGNED TO FAIL initially to prove the SSOT violation problem.

Business Value: Protects $500K+ ARR by providing comprehensive evidence that
AgentRegistry SSOT violations prevent users from getting AI responses through
the chat interface due to import conflicts, interface inconsistencies, and
WebSocket event delivery failures.

Usage:
    python tests/unit/issue_863_agent_registry_ssot/run_comprehensive_registry_ssot_tests.py [options]
    
Options:
    --verbose        Show detailed output
    --category NAME  Run specific test category only
    --summary-only   Show only summary results
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class AgentRegistrySSotTestRunner:
    """
    Comprehensive test runner for AgentRegistry SSOT violation tests.
    """
    
    def __init__(self, verbose: bool = False, summary_only: bool = False):
        self.verbose = verbose
        self.summary_only = summary_only
        self.test_dir = Path(__file__).parent
        
        # Test categories and their files
        self.test_categories = {
            "duplication_conflicts": {
                "file": "test_agent_registry_duplication_conflicts.py",
                "description": "Core import and duplication conflicts",
                "critical": True
            },
            "interface_inconsistency": {
                "file": "test_interface_inconsistency_failures.py", 
                "description": "Interface signature and method inconsistencies",
                "critical": True
            },
            "multi_user_isolation": {
                "file": "test_multi_user_isolation_failures.py",
                "description": "Multi-user context contamination and memory leaks",
                "critical": True
            },
            "websocket_event_delivery": {
                "file": "test_websocket_event_delivery_failures.py",
                "description": "WebSocket event delivery failures blocking Golden Path",
                "critical": True
            },
            "production_usage_patterns": {
                "file": "test_production_usage_pattern_conflicts.py",
                "description": "Production code usage pattern conflicts",
                "critical": False
            }
        }

    def run_single_test_file(self, test_file: str) -> Dict[str, Any]:
        """Run a single test file and return results."""
        test_path = self.test_dir / test_file
        
        if not test_path.exists():
            return {
                "success": False,
                "error": f"Test file not found: {test_file}",
                "tests_run": 0,
                "failures": 0,
                "duration": 0
            }
        
        start_time = time.time()
        
        try:
            # Run pytest on the specific file
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_path),
                "-v" if self.verbose else "-q",
                "--tb=short",
                "--no-header",
                "--disable-warnings"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(project_root),
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            output_lines = result.stdout.split('\n')
            error_lines = result.stderr.split('\n')
            
            # Count tests and failures
            tests_run = 0
            failures = 0
            test_results = []
            
            for line in output_lines:
                if "::" in line and ("PASSED" in line or "FAILED" in line):
                    tests_run += 1
                    if "FAILED" in line:
                        failures += 1
                        test_results.append({
                            "name": line.split("::")[1].split()[0],
                            "status": "FAILED"
                        })
                    else:
                        test_results.append({
                            "name": line.split("::")[1].split()[0],
                            "status": "PASSED"
                        })
            
            return {
                "success": result.returncode == 0,
                "tests_run": tests_run,
                "failures": failures,
                "duration": duration,
                "test_results": test_results,
                "stdout": result.stdout if self.verbose else "",
                "stderr": result.stderr if result.stderr else ""
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timed out",
                "tests_run": 0,
                "failures": 0,
                "duration": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tests_run": 0,
                "failures": 0,
                "duration": time.time() - start_time
            }

    def run_all_tests(self, category_filter: str = None) -> Dict[str, Any]:
        """Run all test categories and return comprehensive results."""
        overall_start_time = time.time()
        
        print("🚨 CRITICAL: AgentRegistry SSOT Violation Test Suite")
        print("=" * 60)
        print("PURPOSE: Demonstrate registry conflicts blocking Golden Path")
        print("EXPECTATION: Tests are DESIGNED TO FAIL to prove the problem")
        print("BUSINESS IMPACT: $500K+ ARR chat functionality at risk")
        print("=" * 60)
        print()
        
        results = {
            "categories": {},
            "summary": {
                "total_categories": 0,
                "critical_categories": 0,
                "categories_run": 0,
                "total_tests": 0,
                "total_failures": 0,
                "critical_failures": 0,
                "total_duration": 0,
                "start_time": overall_start_time
            }
        }
        
        # Filter categories if specified
        categories_to_run = self.test_categories
        if category_filter:
            if category_filter in self.test_categories:
                categories_to_run = {category_filter: self.test_categories[category_filter]}
            else:
                print(f"X Unknown category: {category_filter}")
                print(f"Available categories: {', '.join(self.test_categories.keys())}")
                return results
        
        results["summary"]["total_categories"] = len(self.test_categories)
        results["summary"]["critical_categories"] = sum(1 for cat in self.test_categories.values() if cat["critical"])
        results["summary"]["categories_run"] = len(categories_to_run)
        
        # Run each category
        for category_name, category_info in categories_to_run.items():
            print(f"🔍 Running {category_name.replace('_', ' ').title()} Tests...")
            print(f"   Description: {category_info['description']}")
            print(f"   Critical: {'Yes' if category_info['critical'] else 'No'}")
            
            if not self.summary_only:
                print(f"   File: {category_info['file']}")
                print()
            
            # Run the test file
            test_result = self.run_single_test_file(category_info["file"])
            
            # Store results
            results["categories"][category_name] = {
                "info": category_info,
                "result": test_result
            }
            
            # Update summary
            results["summary"]["total_tests"] += test_result.get("tests_run", 0)
            results["summary"]["total_failures"] += test_result.get("failures", 0)
            results["summary"]["total_duration"] += test_result.get("duration", 0)
            
            if category_info["critical"]:
                results["summary"]["critical_failures"] += test_result.get("failures", 0)
            
            # Display results for this category
            if test_result.get("error"):
                print(f"   X ERROR: {test_result['error']}")
            else:
                tests_run = test_result.get("tests_run", 0)
                failures = test_result.get("failures", 0)
                duration = test_result.get("duration", 0)
                
                if failures > 0:
                    print(f"   🚨 FAILURES: {failures}/{tests_run} tests failed (as expected)")
                else:
                    print(f"   CHECK UNEXPECTED: {tests_run} tests passed (SSOT violation not detected)")
                
                print(f"   ⏱️  Duration: {duration:.2f}s")
                
                # Show individual test results if verbose
                if self.verbose and test_result.get("test_results"):
                    for test in test_result["test_results"]:
                        status_icon = "🚨" if test["status"] == "FAILED" else "CHECK"
                        print(f"      {status_icon} {test['name']}: {test['status']}")
                
                # Show output if there are failures and verbose is on
                if failures > 0 and self.verbose and test_result.get("stderr"):
                    print("   📝 Error Details:")
                    for line in test_result["stderr"].split('\n')[:10]:  # First 10 lines
                        if line.strip():
                            print(f"      {line}")
                    if len(test_result["stderr"].split('\n')) > 10:
                        print("      ... (truncated)")
            
            print()
        
        # Final summary
        results["summary"]["total_duration"] = time.time() - overall_start_time
        self._print_final_summary(results)
        
        return results

    def _print_final_summary(self, results: Dict[str, Any]):
        """Print final comprehensive summary."""
        summary = results["summary"]
        
        print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 60)
        
        # Overall statistics
        print(f"Categories Tested: {summary['categories_run']}/{summary['total_categories']}")
        print(f"Critical Categories: {summary['critical_categories']}")
        print(f"Total Tests Run: {summary['total_tests']}")
        print(f"Total Failures: {summary['total_failures']}")
        print(f"Critical Failures: {summary['critical_failures']}")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print()
        
        # Category breakdown
        print("📋 CATEGORY BREAKDOWN:")
        for category_name, category_data in results["categories"].items():
            info = category_data["info"]
            result = category_data["result"]
            
            critical_marker = "🚨 CRITICAL" if info["critical"] else "📝 STANDARD"
            
            if result.get("error"):
                status = f"X ERROR: {result['error']}"
            else:
                tests = result.get("tests_run", 0)
                failures = result.get("failures", 0)
                if failures > 0:
                    status = f"🚨 {failures}/{tests} FAILED (expected)"
                else:
                    status = f"CHECK {tests}/{tests} PASSED (unexpected)"
            
            print(f"  {critical_marker} {category_name.replace('_', ' ').title()}")
            print(f"    Status: {status}")
            print(f"    Duration: {result.get('duration', 0):.2f}s")
            print()
        
        # Business impact assessment
        print("💼 BUSINESS IMPACT ASSESSMENT:")
        if summary["critical_failures"] > 0:
            print("  🚨 CRITICAL SSOT VIOLATIONS DETECTED!")
            print("  💰 $500K+ ARR Golden Path chat functionality AT RISK")
            print("  🚫 Users cannot receive AI responses due to registry conflicts")
            print("  🔧 IMMEDIATE SSOT CONSOLIDATION REQUIRED")
        else:
            print("  CHECK No critical SSOT violations detected")
            print("  💰 $500K+ ARR Golden Path chat functionality PROTECTED")
            print("  CHECK Registry implementations appear consistent")
        print()
        
        # Recommendations
        print("🔧 RECOMMENDATIONS:")
        if summary["critical_failures"] > 0:
            print("  1. 🚨 PRIORITY P0: Consolidate AgentRegistry implementations into single SSOT")
            print("  2. 🔧 Migrate all imports to use advanced registry (supervisor module)")
            print("  3. 🧪 Remove basic registry to prevent future conflicts")
            print("  4. CHECK Verify all 5 WebSocket events work consistently")
            print("  5. 🔐 Test multi-user isolation thoroughly")
        else:
            print("  1. CHECK Continue monitoring for registry consistency")
            print("  2. 📝 Document successful SSOT compliance patterns")
            print("  3. 🧪 Add regression tests to prevent future violations")
        
        print("\n" + "=" * 60)
        print("Issue #914 AgentRegistry SSOT Test Suite Complete")
        print(f"Total execution time: {summary['total_duration']:.2f}s")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run AgentRegistry SSOT violation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_comprehensive_registry_ssot_tests.py
  python run_comprehensive_registry_ssot_tests.py --verbose
  python run_comprehensive_registry_ssot_tests.py --category interface_inconsistency
  python run_comprehensive_registry_ssot_tests.py --summary-only

Categories:
  duplication_conflicts      - Core import and duplication conflicts (CRITICAL)
  interface_inconsistency    - Interface signature mismatches (CRITICAL)  
  multi_user_isolation       - User context contamination (CRITICAL)
  websocket_event_delivery   - WebSocket event failures (CRITICAL)
  production_usage_patterns  - Production usage conflicts (STANDARD)
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed test output and error details"
    )
    
    parser.add_argument(
        "--category", "-c",
        type=str,
        help="Run only the specified test category"
    )
    
    parser.add_argument(
        "--summary-only", "-s",
        action="store_true",
        help="Show only summary results, no detailed output"
    )
    
    args = parser.parse_args()
    
    # Create and run test runner
    runner = AgentRegistrySSotTestRunner(
        verbose=args.verbose,
        summary_only=args.summary_only
    )
    
    try:
        results = runner.run_all_tests(category_filter=args.category)
        
        # Exit with error code if critical failures detected
        if results["summary"]["critical_failures"] > 0:
            sys.exit(1)  # Expected exit code - tests designed to fail
        else:
            sys.exit(0)  # Unexpected - SSOT violations not detected
            
    except KeyboardInterrupt:
        print("\n⏹️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nX Unexpected error running tests: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()