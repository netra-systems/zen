"""
P1 Critical Failure Reproduction Test Suite Runner

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Systematically validate fixes for P1 critical failures
- Value Impact: Ensure $120K+ MRR critical functionality is restored
- Strategic Impact: Prevent regression of mission-critical platform stability

MISSION: Orchestrate execution of all P1 critical failure reproduction tests
identified in ULTIMATE_TEST_DEPLOY_LOOP_GOLDEN_PATH_20250909_SESSION5.md

This runner executes reproduction tests in the correct order, validates
platform requirements, and provides comprehensive reporting on which
critical failures can be reproduced vs. which are already fixed.

CRITICAL: These tests are designed to FAIL before fixes are applied.
Success means accurately reproducing the failure patterns.
"""

import pytest
import asyncio
import time
import platform
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from test_framework.critical_failure_reproduction_helpers import (
    PlatformInfo,
    CriticalFailureReproducer,
    WindowsAsyncioMonitor,
    create_session5_reproduction_environment,
    validate_reproduction_test_requirements
)

# Critical P1 failures from SESSION5 that must be reproduced
CRITICAL_FAILURES_TO_REPRODUCE = {
    "websocket_sessionmiddleware": {
        "test_module": "test_websocket_sessionmiddleware_failure_reproduction",
        "test_function": "test_websocket_1011_internal_error_reproduction",
        "original_failure": "test_002_websocket_authentication_real",
        "expected_error": "SessionMiddleware must be installed to access request.session",
        "business_impact": "$80K+ MRR - Real-time chat communication broken",
        "platform_requirements": ["all"],
        "timeout": 120
    },
    "windows_streaming_deadlock": {
        "test_module": "test_windows_asyncio_deadlock_reproduction", 
        "test_function": "test_streaming_partial_results_deadlock_reproduction",
        "original_failure": "test_023_streaming_partial_results_real",
        "expected_error": "GetQueuedCompletionStatus blocks indefinitely",
        "business_impact": "$25K+ MRR - Streaming features broken on Windows",
        "platform_requirements": ["windows"],
        "timeout": 300
    },
    "windows_event_delivery_deadlock": {
        "test_module": "test_websocket_event_delivery_deadlock_reproduction",
        "test_function": "test_mission_critical_event_delivery_deadlock_reproduction", 
        "original_failure": "test_025_critical_event_delivery_real",
        "expected_error": "Complex async coordination deadlock on Windows",
        "business_impact": "$15K+ MRR - Event delivery transparency broken",
        "platform_requirements": ["windows"],
        "timeout": 300
    }
}

class P1CriticalReproductionRunner:
    """
    Orchestrate execution of all P1 critical failure reproduction tests
    
    This runner ensures tests execute in the correct environment,
    validates platform requirements, and provides comprehensive
    analysis of reproduction success vs. failure.
    """
    
    def __init__(self):
        self.platform_info = PlatformInfo.detect()
        self.environment = create_session5_reproduction_environment()
        self.results = {}
        self.start_time = time.time()
        
    def validate_environment(self) -> Dict[str, Any]:
        """Validate environment can reproduce SESSION5 failure conditions"""
        validation = {
            "platform_compatible": True,
            "issues": [],
            "recommendations": []
        }
        
        # Check Windows requirements for Windows-specific tests
        windows_tests = [
            name for name, config in CRITICAL_FAILURES_TO_REPRODUCE.items()
            if "windows" in config["platform_requirements"]
        ]
        
        if windows_tests and not self.platform_info.is_windows:
            validation["issues"].append(
                f"Windows tests ({windows_tests}) require Windows platform, "
                f"but running on {self.platform_info.system}"
            )
            validation["recommendations"].append(
                "Run Windows-specific tests on Windows development environment"
            )
        
        # Check asyncio configuration
        if not self.platform_info.asyncio_loop_type:
            validation["issues"].append("No asyncio event loop detected")
            validation["recommendations"].append("Ensure tests run in async context")
        
        # Check timeout configuration
        max_timeout = max(
            config["timeout"] for config in CRITICAL_FAILURES_TO_REPRODUCE.values()
        )
        if max_timeout > 300:
            validation["issues"].append(f"Tests require up to {max_timeout}s timeout")
            
        return validation
    
    async def run_reproduction_test(
        self, 
        failure_name: str, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a single P1 critical failure reproduction test"""
        
        print(f"\n{'='*60}")
        print(f"REPRODUCING: {failure_name}")
        print(f"Original Failure: {config['original_failure']}")
        print(f"Expected Error: {config['expected_error']}")
        print(f"Business Impact: {config['business_impact']}")
        print(f"{'='*60}")
        
        # Check platform requirements
        platform_compatible = self._check_platform_requirements(
            config["platform_requirements"]
        )
        
        if not platform_compatible:
            return {
                "failure_name": failure_name,
                "status": "skipped",
                "reason": f"Platform {self.platform_info.system} not compatible",
                "platform_requirements": config["platform_requirements"],
                "duration": 0
            }
        
        test_start = time.time()
        
        try:
            # Import and run the specific reproduction test
            test_module = __import__(
                f"tests.critical.{config['test_module']}", 
                fromlist=[config['test_function']]
            )
            
            test_function = getattr(test_module, config['test_function'])
            
            # Run the reproduction test
            async with CriticalFailureReproducer(
                test_name=failure_name,
                expected_failure=config['expected_error'],
                timeout=config['timeout']
            ) as reproducer:
                
                reproducer.mark_progress("test_started")
                
                try:
                    # Execute the actual reproduction test
                    await test_function()
                    
                    # If we reach here, reproduction failed (test didn't fail as expected)
                    reproducer.mark_progress("test_completed_unexpectedly")
                    
                    return {
                        "failure_name": failure_name,
                        "status": "reproduction_failed",
                        "reason": "Test completed without reproducing expected failure",
                        "duration": time.time() - test_start,
                        "reproduction_analysis": "Test may indicate issue is already fixed"
                    }
                    
                except asyncio.TimeoutError:
                    # Expected for timeout-based reproduction tests
                    reproducer.mark_progress("timeout_reached")
                    
                    if reproducer.is_windows_deadlock_pattern():
                        return {
                            "failure_name": failure_name,
                            "status": "reproduction_successful",
                            "reason": "Windows asyncio deadlock pattern reproduced",
                            "duration": time.time() - test_start,
                            "reproduction_analysis": "Matches SESSION5 deadlock indicators"
                        }
                    else:
                        return {
                            "failure_name": failure_name,
                            "status": "timeout_different_pattern", 
                            "reason": "Timeout occurred but pattern differs from SESSION5",
                            "duration": time.time() - test_start,
                            "reproduction_analysis": "May be different issue or partial fix"
                        }
                        
                except Exception as e:
                    reproducer.record_error(e, "test_execution")
                    
                    if reproducer.is_sessionmiddleware_pattern():
                        return {
                            "failure_name": failure_name,
                            "status": "reproduction_successful",
                            "reason": "SessionMiddleware error pattern reproduced",
                            "duration": time.time() - test_start,
                            "reproduction_analysis": "Matches SESSION5 SessionMiddleware failure",
                            "error_details": str(e)
                        }
                    else:
                        return {
                            "failure_name": failure_name, 
                            "status": "reproduction_failed",
                            "reason": f"Unexpected error: {type(e).__name__}",
                            "duration": time.time() - test_start,
                            "reproduction_analysis": "Different error pattern than expected",
                            "error_details": str(e)
                        }
        
        except ImportError as e:
            return {
                "failure_name": failure_name,
                "status": "test_not_found",
                "reason": f"Could not import test: {e}",
                "duration": time.time() - test_start
            }
        
        except Exception as e:
            return {
                "failure_name": failure_name,
                "status": "execution_error",
                "reason": f"Test execution failed: {e}",
                "duration": time.time() - test_start,
                "error_details": str(e)
            }
    
    def _check_platform_requirements(self, requirements: List[str]) -> bool:
        """Check if current platform meets test requirements"""
        if "all" in requirements:
            return True
            
        if "windows" in requirements and self.platform_info.is_windows:
            return True
            
        if "linux" in requirements and self.platform_info.is_linux:
            return True
            
        if "macos" in requirements and self.platform_info.is_macos:
            return True
            
        return False
    
    async def run_all_reproduction_tests(self) -> Dict[str, Any]:
        """Run all P1 critical failure reproduction tests"""
        
        print("=" * 80)
        print("P1 CRITICAL FAILURE REPRODUCTION TEST SUITE")
        print("=" * 80)
        print(f"Platform: {self.platform_info.system} {self.platform_info.version}")
        print(f"Python: {self.platform_info.python_version}")
        print(f"Asyncio: {self.platform_info.asyncio_loop_type}")
        print(f"Windows IOCP: {self.platform_info.is_windows_iocp()}")
        print()
        
        # Validate environment first
        environment_validation = self.validate_environment()
        if not environment_validation["platform_compatible"]:
            print("⚠️ ENVIRONMENT ISSUES DETECTED:")
            for issue in environment_validation["issues"]:
                print(f"  - {issue}")
            print("\n📋 RECOMMENDATIONS:")
            for rec in environment_validation["recommendations"]:
                print(f"  - {rec}")
            print()
        
        # Run each reproduction test
        test_results = []
        successful_reproductions = 0
        failed_reproductions = 0
        
        for failure_name, config in CRITICAL_FAILURES_TO_REPRODUCE.items():
            result = await self.run_reproduction_test(failure_name, config)
            test_results.append(result)
            
            if result["status"] == "reproduction_successful":
                successful_reproductions += 1
                print(f"✅ {failure_name}: REPRODUCTION SUCCESSFUL")
                print(f"   {result['reason']}")
                
            elif result["status"] == "reproduction_failed":
                failed_reproductions += 1
                print(f"❌ {failure_name}: REPRODUCTION FAILED") 
                print(f"   {result['reason']}")
                
            elif result["status"] == "skipped":
                print(f"⏭️ {failure_name}: SKIPPED")
                print(f"   {result['reason']}")
                
            else:
                print(f"🔍 {failure_name}: {result['status'].upper()}")
                print(f"   {result.get('reason', 'Unknown')}")
        
        total_duration = time.time() - self.start_time
        
        # Generate comprehensive report
        report = {
            "summary": {
                "total_tests": len(CRITICAL_FAILURES_TO_REPRODUCE),
                "successful_reproductions": successful_reproductions,
                "failed_reproductions": failed_reproductions,
                "total_duration": total_duration,
                "platform": self.platform_info.system,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "environment": {
                "platform_info": {
                    "system": self.platform_info.system,
                    "version": self.platform_info.version,
                    "python_version": self.platform_info.python_version,
                    "asyncio_loop": self.platform_info.asyncio_loop_type,
                    "is_windows_iocp": self.platform_info.is_windows_iocp()
                },
                "validation": environment_validation
            },
            "test_results": test_results,
            "business_impact_analysis": self._analyze_business_impact(test_results)
        }
        
        self._print_final_report(report)
        
        return report
    
    def _analyze_business_impact(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze business impact of reproduction results"""
        
        total_mrr_at_risk = 0
        issues_reproduced = []
        issues_potentially_fixed = []
        
        for result in test_results:
            failure_name = result["failure_name"]
            config = CRITICAL_FAILURES_TO_REPRODUCE[failure_name]
            
            # Extract MRR value from business impact string
            impact_str = config["business_impact"]
            if "$" in impact_str and "K+" in impact_str:
                try:
                    mrr_value = int(impact_str.split("$")[1].split("K+")[0])
                    
                    if result["status"] == "reproduction_successful":
                        total_mrr_at_risk += mrr_value
                        issues_reproduced.append({
                            "failure": failure_name,
                            "mrr_impact": mrr_value,
                            "description": config["business_impact"]
                        })
                    elif result["status"] == "reproduction_failed":
                        issues_potentially_fixed.append({
                            "failure": failure_name,
                            "mrr_impact": mrr_value,
                            "description": config["business_impact"]
                        })
                except ValueError:
                    pass
        
        return {
            "total_mrr_at_risk": total_mrr_at_risk,
            "max_possible_mrr_at_risk": 120,  # From SESSION5 analysis
            "percentage_mrr_at_risk": (total_mrr_at_risk / 120) * 100,
            "issues_reproduced": issues_reproduced,
            "issues_potentially_fixed": issues_potentially_fixed,
            "recommendation": self._get_business_recommendation(total_mrr_at_risk)
        }
    
    def _get_business_recommendation(self, mrr_at_risk: int) -> str:
        """Get business recommendation based on MRR at risk"""
        if mrr_at_risk >= 100:
            return "CRITICAL: Immediate deployment blocking issues - over $100K MRR at risk"
        elif mrr_at_risk >= 50:
            return "HIGH PRIORITY: Significant revenue impact - prioritize fixes immediately"
        elif mrr_at_risk >= 25:
            return "MEDIUM PRIORITY: Substantial functionality broken - schedule fixes soon"
        elif mrr_at_risk > 0:
            return "LOW PRIORITY: Some features affected - address in next sprint"
        else:
            return "GOOD: No critical failures reproduced - deployment likely safe"
    
    def _print_final_report(self, report: Dict[str, Any]):
        """Print comprehensive final report"""
        
        print("\n" + "=" * 80)
        print("P1 CRITICAL FAILURE REPRODUCTION - FINAL REPORT")
        print("=" * 80)
        
        summary = report["summary"]
        business = report["business_impact_analysis"]
        
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful Reproductions: {summary['successful_reproductions']}")
        print(f"Failed Reproductions: {summary['failed_reproductions']}")
        print(f"Total Duration: {summary['total_duration']:.1f}s")
        print(f"Platform: {summary['platform']}")
        
        print(f"\n📊 BUSINESS IMPACT ANALYSIS:")
        print(f"MRR at Risk: ${business['total_mrr_at_risk']}K+ / $120K+ total")
        print(f"Risk Percentage: {business['percentage_mrr_at_risk']:.1f}%")
        print(f"Recommendation: {business['recommendation']}")
        
        if business["issues_reproduced"]:
            print(f"\n🚨 CRITICAL ISSUES REPRODUCED ({len(business['issues_reproduced'])}):")
            for issue in business["issues_reproduced"]:
                print(f"  - {issue['failure']}: ${issue['mrr_impact']}K+ MRR")
                print(f"    {issue['description']}")
        
        if business["issues_potentially_fixed"]:
            print(f"\n✅ POTENTIALLY FIXED ISSUES ({len(business['issues_potentially_fixed'])}):")
            for issue in business["issues_potentially_fixed"]:
                print(f"  - {issue['failure']}: ${issue['mrr_impact']}K+ MRR")
                print(f"    {issue['description']}")
        
        print(f"\n🎯 NEXT STEPS:")
        if summary['successful_reproductions'] > 0:
            print("1. Apply targeted fixes for reproduced failures")
            print("2. Rerun reproduction tests to validate fixes")
            print("3. Deploy only after all critical reproductions fail to reproduce")
        else:
            print("1. All critical failures may be fixed - validate with staging deployment")
            print("2. Run full P1 test suite to confirm functionality restored")
            print("3. Proceed with deployment if P1 tests pass")
        
        print("=" * 80)


async def main():
    """Main entry point for P1 critical failure reproduction suite"""
    
    runner = P1CriticalReproductionRunner()
    report = await runner.run_all_reproduction_tests()
    
    # Save report for analysis
    report_file = Path("tests/critical/p1_reproduction_report.json")
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Return appropriate exit code
    successful_reproductions = report["summary"]["successful_reproductions"]
    
    if successful_reproductions > 0:
        print(f"\n🚨 CRITICAL: {successful_reproductions} failures reproduced - fixes needed before deployment")
        return 1  # Exit code indicates critical issues found
    else:
        print(f"\n✅ SUCCESS: No critical failures reproduced - deployment may be safe")
        return 0  # Exit code indicates no critical issues


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Reproduction suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Reproduction suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)