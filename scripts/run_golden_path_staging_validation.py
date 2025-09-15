#!/usr/bin/env python3
"""
Golden Path Staging Validation Test Runner - Issue #1176
=======================================================

MISSION CRITICAL: Run comprehensive Golden Path validation tests against staging
environment to validate user login → AI responses flow protecting $500K+ ARR.

PURPOSE: 
- Execute complete Golden Path E2E validation test suite
- Validate staging environment health and readiness
- Test all 5 business-critical WebSocket events
- Validate multi-user isolation and performance
- Generate comprehensive validation report

TARGET: Real staging environment at *.staging.netrasystems.ai

USAGE:
    python scripts/run_golden_path_staging_validation.py
    python scripts/run_golden_path_staging_validation.py --report-only
    python scripts/run_golden_path_staging_validation.py --quick-health-check
"""

import asyncio
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test file locations
GOLDEN_PATH_TESTS = [
    "tests/e2e/staging/test_staging_authentication_service_health.py",
    "tests/e2e/staging/test_websocket_events_business_critical_staging.py", 
    "tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py"
]

# Test categories and priorities
TEST_CATEGORIES = {
    "health": {
        "priority": "P0_CRITICAL",
        "description": "Staging environment health and authentication",
        "tests": ["test_staging_authentication_service_health.py"],
        "required_for_golden_path": True
    },
    "websocket_events": {
        "priority": "P0_CRITICAL", 
        "description": "Business-critical WebSocket events validation",
        "tests": ["test_websocket_events_business_critical_staging.py"],
        "required_for_golden_path": True
    },
    "end_to_end": {
        "priority": "P0_CRITICAL",
        "description": "Complete Golden Path user journey validation", 
        "tests": ["test_golden_path_end_to_end_staging_validation.py"],
        "required_for_golden_path": True
    }
}

class GoldenPathValidationRunner:
    """Run and manage Golden Path validation tests against staging."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = {
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "total_duration": None,
            "overall_success": False,
            "staging_environment": "https://*.staging.netrasystems.ai",
            "test_results": {},
            "summary": {},
            "recommendations": []
        }
        
    async def run_health_check_only(self) -> Dict[str, Any]:
        """Run quick health check of staging environment."""
        print("🏥 Running Golden Path Staging Health Check...")
        print("=" * 60)
        
        health_test = "tests/e2e/staging/test_staging_authentication_service_health.py"
        
        # Run specific health tests
        health_methods = [
            "test_staging_auth_service_health_comprehensive",
            "test_staging_backend_api_service_health", 
            "test_staging_websocket_service_basic_connectivity",
            "test_staging_environment_readiness_summary"
        ]
        
        health_results = {}
        
        for method in health_methods:
            print(f"\n🔍 Testing: {method}")
            
            result = await self._run_single_test(health_test, method)
            health_results[method] = result
            
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"   {status} - {result.get('duration', 0):.1f}s")
            
            if not result["success"]:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Generate health summary
        passed_tests = sum(1 for r in health_results.values() if r["success"])
        total_tests = len(health_results)
        health_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📊 Health Check Summary:")
        print(f"   Health Score: {health_score:.1f}% ({passed_tests}/{total_tests} tests passed)")
        print(f"   Staging Ready: {'✅ YES' if health_score >= 90 else '❌ NO'}")
        
        return {
            "health_score": health_score,
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "staging_ready": health_score >= 90,
            "test_results": health_results
        }
    
    async def run_complete_validation(self) -> Dict[str, Any]:
        """Run complete Golden Path validation test suite."""
        print("🚀 Starting Golden Path Staging Validation")
        print("=" * 60)
        print(f"Target Environment: {self.results['staging_environment']}")
        print(f"Start Time: {self.results['start_time']}")
        print()
        
        start_time = time.time()
        
        # Run tests by category
        for category_name, category_info in TEST_CATEGORIES.items():
            print(f"\n📋 Running {category_info['priority']} - {category_info['description']}")
            print("-" * 50)
            
            category_results = {}
            
            for test_file in category_info["tests"]:
                test_path = f"tests/e2e/staging/{test_file}"
                print(f"\n🧪 Testing: {test_file}")
                
                # Run all test methods in the file
                result = await self._run_test_file(test_path)
                category_results[test_file] = result
                
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                print(f"   {status} - {result['passed']}/{result['total']} tests passed ({result['duration']:.1f}s)")
                
                if not result["success"]:
                    print(f"   ⚠️  Failed tests: {result.get('failed_tests', [])}")
            
            self.results["test_results"][category_name] = category_results
        
        # Calculate final results
        end_time = time.time()
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_duration"] = end_time - start_time
        
        # Generate summary
        await self._generate_summary()
        
        return self.results
    
    async def _run_test_file(self, test_path: str) -> Dict[str, Any]:
        """Run all tests in a test file."""
        result = {
            "success": False,
            "total": 0,
            "passed": 0,
            "failed": 0,
            "failed_tests": [],
            "duration": 0,
            "output": "",
            "error": None
        }
        
        try:
            start_time = time.time()
            
            # Run pytest on the test file
            cmd = [
                sys.executable, "-m", "pytest",
                test_path,
                "-v",
                "--tb=short",
                "--disable-warnings",
                "--maxfail=10"  # Don't stop on first failure
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            stdout, _ = await process.communicate()
            output = stdout.decode('utf-8')
            
            result["duration"] = time.time() - start_time
            result["output"] = output
            
            # Parse pytest output
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                
                # Look for test results
                if " PASSED " in line:
                    result["passed"] += 1
                elif " FAILED " in line:
                    result["failed"] += 1
                    # Extract test name
                    if "::" in line:
                        test_name = line.split("::")[-1].split()[0]
                        result["failed_tests"].append(test_name)
                
                # Look for summary line
                if "failed" in line and "passed" in line and "in" in line:
                    # Parse summary like: "2 failed, 3 passed in 5.2s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "failed,":
                            result["failed"] = int(parts[i-1])
                        elif part == "passed":
                            result["passed"] = int(parts[i-1])
            
            result["total"] = result["passed"] + result["failed"]
            result["success"] = (result["failed"] == 0 and result["passed"] > 0)
            
            if process.returncode != 0 and result["passed"] == 0:
                result["error"] = f"Test execution failed with return code {process.returncode}"
            
        except Exception as e:
            result["error"] = f"Exception running tests: {str(e)}"
            result["duration"] = time.time() - start_time
        
        return result
    
    async def _run_single_test(self, test_path: str, test_method: str) -> Dict[str, Any]:
        """Run a single test method."""
        result = {
            "success": False,
            "duration": 0,
            "output": "",
            "error": None
        }
        
        try:
            start_time = time.time()
            
            # Run specific test method
            cmd = [
                sys.executable, "-m", "pytest",
                f"{test_path}::{test_method}",
                "-v",
                "--tb=short",
                "--disable-warnings"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            stdout, _ = await process.communicate()
            output = stdout.decode('utf-8')
            
            result["duration"] = time.time() - start_time
            result["output"] = output
            result["success"] = (process.returncode == 0)
            
            if process.returncode != 0:
                result["error"] = f"Test failed with return code {process.returncode}"
        
        except Exception as e:
            result["error"] = f"Exception running test: {str(e)}"
            result["duration"] = time.time() - start_time
        
        return result
    
    async def _generate_summary(self):
        """Generate comprehensive validation summary."""
        summary = {
            "total_categories": len(TEST_CATEGORIES),
            "passed_categories": 0,
            "failed_categories": 0,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "golden_path_ready": False,
            "blocking_issues": [],
            "performance_warnings": []
        }
        
        # Analyze results by category
        for category_name, category_results in self.results["test_results"].items():
            category_passed = True
            category_total = 0
            category_passed_count = 0
            
            for test_file, test_result in category_results.items():
                category_total += test_result["total"]
                category_passed_count += test_result["passed"]
                
                if not test_result["success"]:
                    category_passed = False
                    
                    # Add blocking issues
                    for failed_test in test_result.get("failed_tests", []):
                        summary["blocking_issues"].append(
                            f"{category_name}: {failed_test} failed"
                        )
                
                # Check for performance warnings
                if test_result["duration"] > 60.0:
                    summary["performance_warnings"].append(
                        f"{test_file} took {test_result['duration']:.1f}s (slow)"
                    )
            
            summary["total_tests"] += category_total
            summary["passed_tests"] += category_passed_count
            summary["failed_tests"] += (category_total - category_passed_count)
            
            if category_passed:
                summary["passed_categories"] += 1
            else:
                summary["failed_categories"] += 1
        
        # Determine Golden Path readiness
        critical_categories_passed = summary["passed_categories"]
        total_critical_categories = len([
            cat for cat in TEST_CATEGORIES.values() 
            if cat.get("required_for_golden_path", False)
        ])
        
        summary["golden_path_ready"] = (
            critical_categories_passed >= total_critical_categories and
            len(summary["blocking_issues"]) == 0
        )
        
        # Calculate success rate
        if summary["total_tests"] > 0:
            success_rate = (summary["passed_tests"] / summary["total_tests"]) * 100
            summary["success_rate"] = success_rate
        else:
            summary["success_rate"] = 0
        
        # Set overall success
        self.results["overall_success"] = summary["golden_path_ready"]
        self.results["summary"] = summary
        
        # Generate recommendations
        self._generate_recommendations()
    
    def _generate_recommendations(self):
        """Generate recommendations based on test results."""
        recommendations = []
        summary = self.results["summary"]
        
        if not summary["golden_path_ready"]:
            recommendations.append(
                "🚨 CRITICAL: Golden Path not ready for production deployment"
            )
            
            if summary["blocking_issues"]:
                recommendations.append(
                    f"🔧 Fix {len(summary['blocking_issues'])} blocking issues before deployment"
                )
                
                for issue in summary["blocking_issues"][:5]:  # Show first 5
                    recommendations.append(f"   - {issue}")
        
        if summary["success_rate"] < 90:
            recommendations.append(
                f"📈 Improve test success rate from {summary['success_rate']:.1f}% to >90%"
            )
        
        if summary["performance_warnings"]:
            recommendations.append(
                "⚡ Address performance warnings for better user experience"
            )
        
        if summary["golden_path_ready"]:
            recommendations.append(
                "✅ Golden Path validated - Ready for production deployment"
            )
            recommendations.append(
                "🚀 All critical Golden Path functionality working on staging"
            )
        
        self.results["recommendations"] = recommendations
    
    def print_final_report(self):
        """Print comprehensive final validation report."""
        print("\n" + "=" * 80)
        print("🏆 GOLDEN PATH STAGING VALIDATION FINAL REPORT")
        print("=" * 80)
        
        summary = self.results["summary"]
        
        print(f"\n📊 Summary:")
        print(f"   Golden Path Ready: {'✅ YES' if summary['golden_path_ready'] else '❌ NO'}")
        print(f"   Success Rate: {summary.get('success_rate', 0):.1f}%")
        print(f"   Tests Passed: {summary['passed_tests']}/{summary['total_tests']}")
        print(f"   Categories Passed: {summary['passed_categories']}/{summary['total_categories']}")
        print(f"   Total Duration: {self.results.get('total_duration', 0):.1f}s")
        
        if summary["blocking_issues"]:
            print(f"\n🚨 Blocking Issues ({len(summary['blocking_issues'])}):")
            for issue in summary["blocking_issues"]:
                print(f"   • {issue}")
        
        if summary["performance_warnings"]:
            print(f"\n⚡ Performance Warnings ({len(summary['performance_warnings'])}):")
            for warning in summary["performance_warnings"]:
                print(f"   • {warning}")
        
        print(f"\n💡 Recommendations:")
        for rec in self.results["recommendations"]:
            print(f"   {rec}")
        
        print(f"\n📁 Full Results: {self._save_report()}")
        print("=" * 80)
        
        return summary["golden_path_ready"]
    
    def _save_report(self) -> str:
        """Save detailed report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.project_root / f"golden_path_staging_validation_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        return str(report_file)


async def main():
    """Main entry point for Golden Path staging validation."""
    parser = argparse.ArgumentParser(
        description="Golden Path Staging Validation - Issue #1176",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_golden_path_staging_validation.py
  python scripts/run_golden_path_staging_validation.py --quick-health-check  
  python scripts/run_golden_path_staging_validation.py --report-only
        """
    )
    
    parser.add_argument(
        "--quick-health-check",
        action="store_true",
        help="Run only staging environment health checks"
    )
    
    parser.add_argument(
        "--report-only",
        action="store_true", 
        help="Generate report from existing results (no test execution)"
    )
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = GoldenPathValidationRunner(project_root)
    
    try:
        if args.report_only:
            print("📊 Generating report from previous run...")
            # Load most recent results if available
            runner.print_final_report()
            
        elif args.quick_health_check:
            print("🏥 Running quick staging health check...")
            health_results = await runner.run_health_check_only()
            
            if health_results["staging_ready"]:
                print("\n✅ Staging environment is ready for Golden Path validation!")
                sys.exit(0)
            else:
                print("\n❌ Staging environment has issues - fix before Golden Path validation")
                sys.exit(1)
                
        else:
            print("🚀 Running complete Golden Path validation...")
            await runner.run_complete_validation()
            
            # Print final report and determine exit code
            golden_path_ready = runner.print_final_report()
            
            if golden_path_ready:
                print("\n🎉 SUCCESS: Golden Path validated on staging!")
                sys.exit(0)
            else:
                print("\n💥 FAILURE: Golden Path validation failed - see report for details")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Validation interrupted by user")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure we're in the correct directory
    os.chdir(project_root)
    
    # Run the validation
    asyncio.run(main())