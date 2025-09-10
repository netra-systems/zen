"""
WebSocket Race Condition Test Runner

Purpose: Comprehensive test runner for all WebSocket race condition reproduction tests
that validate the fixes for $500K+ ARR chat functionality failures.

This script runs the complete suite of race condition tests and provides detailed
analysis of which race conditions are successfully reproduced vs. which indicate
that fixes have been implemented.

Business Value:
- Segment: Platform Infrastructure & Chat Functionality  
- Goal: $500K+ ARR Protection through systematic race condition validation
- Value Impact: Comprehensive validation of WebSocket race condition fixes
- Strategic Impact: Automated detection of race condition regressions
"""

import asyncio
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import subprocess
import json

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class TestSuiteResult:
    """Results from running a race condition test suite."""
    suite_name: str
    test_file: str
    total_tests: int
    passed_tests: int
    failed_tests: int 
    expected_failures: int  # xfail tests that failed as expected
    unexpected_passes: int  # xfail tests that unexpectedly passed
    duration_seconds: float
    race_conditions_detected: int
    race_conditions_fixed: int
    error_details: List[str]


class RaceConditionTestRunner:
    """Comprehensive runner for all WebSocket race condition tests."""

    def __init__(self, verbose: bool = True, fail_fast: bool = False):
        self.verbose = verbose
        self.fail_fast = fail_fast
        self.test_results: List[TestSuiteResult] = []
        
        # Define test suites in order of execution priority
        self.test_suites = [
            {
                "name": "Enhanced Race Condition Reproduction",
                "file": "test_websocket_race_condition_reproduction_enhanced.py",
                "description": "Enhanced reproduction of core race conditions from Five Whys analysis",
                "priority": 1
            },
            {
                "name": "Cloud Run Race Conditions", 
                "file": "test_websocket_cloud_run_race_conditions.py",
                "description": "GCP Cloud Run specific race conditions and infrastructure timing issues",
                "priority": 2
            },
            {
                "name": "WebSocket 1011 Error Race Conditions",
                "file": "test_websocket_1011_error_race_conditions.py", 
                "description": "Specific reproduction of WebSocket 1011 internal server errors",
                "priority": 3
            },
            {
                "name": "Original Race Condition Reproduction",
                "file": "test_websocket_race_condition_reproduction.py",
                "description": "Original race condition reproduction tests for baseline comparison",
                "priority": 4
            }
        ]

    async def run_all_race_condition_tests(self) -> Dict[str, Any]:
        """Run all race condition test suites and analyze results."""
        logger.info("🏁 STARTING COMPREHENSIVE WEBSOCKET RACE CONDITION TEST SUITE")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # Run each test suite
        for suite_info in self.test_suites:
            logger.info(f"\n🧪 Running {suite_info['name']}")
            logger.info(f"📄 Description: {suite_info['description']}")
            logger.info("-" * 60)
            
            try:
                result = await self._run_test_suite(suite_info)
                self.test_results.append(result)
                
                if self.verbose:
                    self._log_suite_results(result)
                
                if self.fail_fast and result.unexpected_passes > 0:
                    logger.warning(f"⚠️ FAIL FAST: {result.unexpected_passes} unexpected passes detected")
                    break
                    
            except Exception as e:
                logger.error(f"❌ Error running {suite_info['name']}: {e}")
                continue
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Generate comprehensive analysis
        analysis = self._analyze_results(total_duration)
        self._log_comprehensive_analysis(analysis)
        
        return analysis

    async def _run_test_suite(self, suite_info: Dict[str, Any]) -> TestSuiteResult:
        """Run a single test suite and parse results."""
        test_file_path = Path(__file__).parent / suite_info["file"]
        
        if not test_file_path.exists():
            logger.warning(f"⚠️ Test file not found: {test_file_path}")
            return TestSuiteResult(
                suite_name=suite_info["name"],
                test_file=suite_info["file"],
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                expected_failures=0,
                unexpected_passes=0,
                duration_seconds=0.0,
                race_conditions_detected=0,
                race_conditions_fixed=0,
                error_details=["Test file not found"]
            )
        
        start_time = time.time()
        
        # Run pytest with JSON report
        cmd = [
            "python", "-m", "pytest",
            str(test_file_path),
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=/tmp/pytest_report.json",
            "-m", "race_condition"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per suite
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse pytest output
            return self._parse_pytest_results(
                suite_info, result, duration
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Test suite {suite_info['name']} timed out after 5 minutes")
            return TestSuiteResult(
                suite_name=suite_info["name"],
                test_file=suite_info["file"],
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                expected_failures=0,
                unexpected_passes=0,
                duration_seconds=300.0,
                race_conditions_detected=0,
                race_conditions_fixed=0,
                error_details=["Test suite timed out"]
            )

    def _parse_pytest_results(self, suite_info: Dict[str, Any], result: subprocess.CompletedProcess, 
                             duration: float) -> TestSuiteResult:
        """Parse pytest output to extract test results."""
        stdout = result.stdout
        stderr = result.stderr
        
        # Extract test counts from pytest output
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        expected_failures = 0  # xfail tests that failed as expected
        unexpected_passes = 0  # xfail tests that unexpectedly passed
        error_details = []
        
        # Parse pytest output for test results
        lines = stdout.split('\n') + stderr.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Count test results
            if "PASSED" in line and "::" in line:
                passed_tests += 1
                total_tests += 1
                
                # Check if this was an xfail that unexpectedly passed
                if "XPASS" in line:
                    unexpected_passes += 1
                    logger.info(f"🎉 RACE CONDITION FIXED: {line}")
                    
            elif "FAILED" in line and "::" in line:
                failed_tests += 1
                total_tests += 1
                
                # Check if this was an expected failure (xfail)
                if "xfail" in line.lower():
                    expected_failures += 1
                    logger.info(f"✅ Expected race condition reproduced: {line}")
                else:
                    error_details.append(line)
                    
            elif "ERROR" in line and "::" in line:
                total_tests += 1
                error_details.append(line)
        
        # Calculate race condition analysis
        race_conditions_detected = expected_failures  # xfail tests that failed as expected
        race_conditions_fixed = unexpected_passes     # xfail tests that unexpectedly passed
        
        return TestSuiteResult(
            suite_name=suite_info["name"],
            test_file=suite_info["file"],
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            expected_failures=expected_failures,
            unexpected_passes=unexpected_passes,
            duration_seconds=duration,
            race_conditions_detected=race_conditions_detected,
            race_conditions_fixed=race_conditions_fixed,
            error_details=error_details
        )

    def _log_suite_results(self, result: TestSuiteResult):
        """Log detailed results for a single test suite."""
        logger.info(f"📊 {result.suite_name} Results:")
        logger.info(f"   Total Tests: {result.total_tests}")
        logger.info(f"   Expected Failures (Race Conditions Detected): {result.expected_failures}")
        logger.info(f"   Unexpected Passes (Race Conditions Fixed): {result.unexpected_passes}")
        logger.info(f"   Regular Passes: {result.passed_tests - result.unexpected_passes}")
        logger.info(f"   Unexpected Failures: {result.failed_tests - result.expected_failures}")
        logger.info(f"   Duration: {result.duration_seconds:.2f}s")
        
        if result.unexpected_passes > 0:
            logger.info(f"🎉 GOOD NEWS: {result.unexpected_passes} race conditions appear to be FIXED!")
            
        if result.race_conditions_detected > 0:
            logger.info(f"⚠️ RACE CONDITIONS: {result.race_conditions_detected} race conditions successfully reproduced")
            
        if result.error_details:
            logger.warning("❌ Unexpected errors:")
            for error in result.error_details[:3]:  # Show first 3 errors
                logger.warning(f"   {error}")
            if len(result.error_details) > 3:
                logger.warning(f"   ... and {len(result.error_details) - 3} more errors")

    def _analyze_results(self, total_duration: float) -> Dict[str, Any]:
        """Analyze all test results and generate comprehensive report."""
        analysis = {
            "summary": {
                "total_duration_seconds": total_duration,
                "total_test_suites": len(self.test_results),
                "total_tests": sum(r.total_tests for r in self.test_results),
                "total_race_conditions_detected": sum(r.race_conditions_detected for r in self.test_results),
                "total_race_conditions_fixed": sum(r.race_conditions_fixed for r in self.test_results),
                "total_unexpected_errors": sum(len(r.error_details) for r in self.test_results)
            },
            "race_condition_status": {
                "reproduced_successfully": sum(r.race_conditions_detected for r in self.test_results),
                "appear_fixed": sum(r.race_conditions_fixed for r in self.test_results),
                "total_identified": sum(r.race_conditions_detected + r.race_conditions_fixed for r in self.test_results)
            },
            "suite_results": [
                {
                    "name": r.suite_name,
                    "file": r.test_file,
                    "race_conditions_detected": r.race_conditions_detected,
                    "race_conditions_fixed": r.race_conditions_fixed,
                    "unexpected_errors": len(r.error_details),
                    "duration": r.duration_seconds
                }
                for r in self.test_results
            ],
            "recommendations": self._generate_recommendations()
        }
        
        return analysis

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        total_detected = sum(r.race_conditions_detected for r in self.test_results)
        total_fixed = sum(r.race_conditions_fixed for r in self.test_results)
        total_errors = sum(len(r.error_details) for r in self.test_results)
        
        if total_fixed > 0:
            recommendations.append(
                f"🎉 EXCELLENT: {total_fixed} race conditions appear to be FIXED! "
                f"Consider updating the corresponding xfail markers to expect success."
            )
            
        if total_detected > 0:
            recommendations.append(
                f"⚠️ ATTENTION: {total_detected} race conditions are still reproducible. "
                f"These need to be addressed to ensure $500K+ ARR chat functionality reliability."
            )
            
        if total_errors > 0:
            recommendations.append(
                f"❌ INVESTIGATION NEEDED: {total_errors} unexpected test errors occurred. "
                f"Review error details to determine if these indicate new issues."
            )
            
        if total_detected == 0 and total_fixed == 0:
            recommendations.append(
                "🔍 REVIEW REQUIRED: No race conditions detected or fixed. "
                "This may indicate test conditions need adjustment or all race conditions are resolved."
            )
            
        # Business impact recommendations
        if total_detected > total_fixed:
            recommendations.append(
                "💼 BUSINESS IMPACT: More race conditions detected than fixed. "
                "Priority should be on implementing Single Coordination State Machine."
            )
        else:
            recommendations.append(
                "💼 BUSINESS POSITIVE: Race condition fixes appear to be progressing well. "
                "Continue validation and monitoring."
            )
            
        return recommendations

    def _log_comprehensive_analysis(self, analysis: Dict[str, Any]):
        """Log comprehensive analysis of all test results."""
        logger.info("\n" + "=" * 80)
        logger.info("🏆 COMPREHENSIVE RACE CONDITION TEST ANALYSIS")
        logger.info("=" * 80)
        
        summary = analysis["summary"]
        logger.info(f"📈 OVERALL RESULTS:")
        logger.info(f"   Total Test Suites: {summary['total_test_suites']}")
        logger.info(f"   Total Tests: {summary['total_tests']}")
        logger.info(f"   Total Duration: {summary['total_duration_seconds']:.2f}s")
        
        status = analysis["race_condition_status"]
        logger.info(f"\n🎯 RACE CONDITION STATUS:")
        logger.info(f"   Successfully Reproduced: {status['reproduced_successfully']}")
        logger.info(f"   Appear Fixed: {status['appear_fixed']}")
        logger.info(f"   Total Race Conditions: {status['total_identified']}")
        
        if status['appear_fixed'] > 0:
            fix_percentage = (status['appear_fixed'] / status['total_identified']) * 100
            logger.info(f"   Fix Progress: {fix_percentage:.1f}% of race conditions appear resolved")
        
        logger.info(f"\n📋 RECOMMENDATIONS:")
        for i, rec in enumerate(analysis["recommendations"], 1):
            logger.info(f"   {i}. {rec}")
        
        logger.info(f"\n📊 DETAILED SUITE BREAKDOWN:")
        for suite in analysis["suite_results"]:
            logger.info(f"   {suite['name']}:")
            logger.info(f"      Race Conditions Detected: {suite['race_conditions_detected']}")
            logger.info(f"      Race Conditions Fixed: {suite['race_conditions_fixed']}")
            logger.info(f"      Unexpected Errors: {suite['unexpected_errors']}")
            logger.info(f"      Duration: {suite['duration']:.2f}s")
        
        # Business impact summary
        logger.info(f"\n💰 BUSINESS IMPACT SUMMARY:")
        if status['reproduced_successfully'] > 0:
            logger.info(f"   🚨 RISK: {status['reproduced_successfully']} race conditions still threaten $500K+ ARR")
        if status['appear_fixed'] > 0:
            logger.info(f"   ✅ PROTECTED: {status['appear_fixed']} race conditions appear resolved")
        
        logger.info("=" * 80)


async def main():
    """Main entry point for race condition test runner."""
    parser = argparse.ArgumentParser(
        description="Comprehensive WebSocket Race Condition Test Runner"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--fail-fast", 
        action="store_true",
        help="Stop on first unexpected pass (indicating race condition fixed)"
    )
    parser.add_argument(
        "--output-json",
        help="Output detailed results to JSON file"
    )
    
    args = parser.parse_args()
    
    # Run comprehensive test suite
    runner = RaceConditionTestRunner(
        verbose=args.verbose,
        fail_fast=args.fail_fast
    )
    
    try:
        analysis = await runner.run_all_race_condition_tests()
        
        # Output JSON if requested
        if args.output_json:
            with open(args.output_json, 'w') as f:
                json.dump(analysis, f, indent=2)
            logger.info(f"📄 Detailed analysis saved to {args.output_json}")
        
        # Exit code based on results
        race_conditions_detected = analysis["race_condition_status"]["reproduced_successfully"]
        unexpected_errors = analysis["summary"]["total_unexpected_errors"]
        
        if unexpected_errors > 0:
            logger.error(f"❌ Exiting with error code due to {unexpected_errors} unexpected errors")
            sys.exit(1)
        elif race_conditions_detected > 0:
            logger.info(f"⚠️ Exiting with warning code: {race_conditions_detected} race conditions detected")
            sys.exit(2)  # Warning exit code
        else:
            logger.info("✅ All race condition tests completed successfully")
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.warning("🛑 Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Unexpected error during test execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())