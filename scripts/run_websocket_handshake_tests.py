#!/usr/bin/env python3
"""
WebSocket Authentication Handshake Test Runner

Business Value Justification:
- Segment: Platform/Internal - Test Execution
- Business Goal: Validate WebSocket handshake fixes maintain $500K+ ARR functionality  
- Value Impact: Automated validation of critical chat infrastructure changes
- Strategic Impact: Prevents regression in Golden Path user flows

USAGE:
This script provides comprehensive test execution for WebSocket handshake issues.
It runs tests in phases to demonstrate the issue, validate fixes, and ensure
business value preservation.

EXECUTION PHASES:
1. Pre-fix validation (tests should FAIL - proving the issue exists)
2. Post-fix validation (tests should PASS - proving the fix works)
3. Business value preservation (ensures Golden Path still works)
4. Performance regression testing (ensures no performance impact)

BUSINESS CONTEXT:
- Chat functionality represents 90% of platform value
- WebSocket authentication enables user → AI interactions
- 1011 errors break the user experience
- Enterprise customers depend on reliable chat
"""

import asyncio
import sys
import os
import subprocess
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@dataclass
class TestPhaseResult:
    """Results from a test execution phase."""
    phase_name: str
    passed: int
    failed: int
    skipped: int
    errors: List[str]
    execution_time: float
    expected_to_pass: bool
    business_impact: str


class WebSocketHandshakeTestRunner:
    """
    Comprehensive test runner for WebSocket handshake validation.
    
    This runner executes tests in phases to validate the handshake issue,
    fix implementation, and business value preservation.
    """
    
    def __init__(self):
        self.project_root = project_root
        self.test_plan_path = self.project_root / "test_plans" / "websocket_auth_handshake_comprehensive_test_plan.py"
        self.results = []
        
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """
        Run the complete WebSocket handshake test suite.
        
        Returns:
            Comprehensive results including business impact analysis
        """
        logger.info("🚀 Starting WebSocket Authentication Handshake Test Suite")
        logger.info("=" * 70)
        
        # Test execution phases
        phases = [
            self._run_issue_demonstration_phase(),
            self._run_rfc6455_compliance_phase(), 
            self._run_remediation_validation_phase(),
            self._run_business_value_preservation_phase(),
            self._run_performance_regression_phase()
        ]
        
        # Execute all phases
        for phase_coro in phases:
            try:
                result = await phase_coro
                self.results.append(result)
                self._log_phase_result(result)
            except Exception as e:
                error_result = TestPhaseResult(
                    phase_name=f"Phase execution error",
                    passed=0,
                    failed=1,
                    skipped=0,
                    errors=[str(e)],
                    execution_time=0.0,
                    expected_to_pass=False,
                    business_impact="TEST_EXECUTION_ERROR"
                )
                self.results.append(error_result)
                logger.error(f"Phase execution failed: {e}")
        
        # Generate comprehensive report
        return self._generate_comprehensive_report()
    
    async def _run_issue_demonstration_phase(self) -> TestPhaseResult:
        """
        Phase 1: Demonstrate the WebSocket handshake issue.
        
        These tests should FAIL, proving that the issue exists.
        """
        logger.info("📋 Phase 1: Issue Demonstration (tests should FAIL)")
        
        start_time = time.time()
        
        # Run tests that demonstrate the handshake timing issue
        cmd = [
            "python3", "-m", "pytest",
            str(self.test_plan_path),
            "-k", "test_websocket_handshake_timing_violation_detection or test_rfc6455_subprotocol_negotiation_basic_compliance",
            "-v", "--tb=short",
            "--disable-warnings"
        ]
        
        result = await self._execute_test_command(cmd)
        execution_time = time.time() - start_time
        
        return TestPhaseResult(
            phase_name="Issue Demonstration",
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            errors=result.get("errors", []),
            execution_time=execution_time,
            expected_to_pass=False,  # These tests should FAIL initially
            business_impact="DEMONSTRATES_CRITICAL_ISSUE"
        )
    
    async def _run_rfc6455_compliance_phase(self) -> TestPhaseResult:
        """
        Phase 2: RFC 6455 compliance validation.
        
        These tests validate proper WebSocket subprotocol negotiation.
        """
        logger.info("📋 Phase 2: RFC 6455 Compliance Validation")
        
        start_time = time.time()
        
        cmd = [
            "python3", "-m", "pytest", 
            str(self.test_plan_path),
            "-k", "TestWebSocketSubprotocolNegotiation",
            "-v", "--tb=short",
            "--disable-warnings"
        ]
        
        result = await self._execute_test_command(cmd)
        execution_time = time.time() - start_time
        
        return TestPhaseResult(
            phase_name="RFC 6455 Compliance",
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            errors=result.get("errors", []),
            execution_time=execution_time,
            expected_to_pass=True,  # These should pass with proper implementation
            business_impact="ENSURES_PROTOCOL_COMPLIANCE"
        )
    
    async def _run_remediation_validation_phase(self) -> TestPhaseResult:
        """
        Phase 3: Remediation validation.
        
        These tests should PASS after the handshake fix is implemented.
        """
        logger.info("📋 Phase 3: Remediation Validation (tests should PASS post-fix)")
        
        start_time = time.time()
        
        cmd = [
            "python3", "-m", "pytest",
            str(self.test_plan_path), 
            "-k", "remediation_validation",
            "-v", "--tb=short",
            "--disable-warnings"
        ]
        
        result = await self._execute_test_command(cmd)
        execution_time = time.time() - start_time
        
        return TestPhaseResult(
            phase_name="Remediation Validation",
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            errors=result.get("errors", []),
            execution_time=execution_time,
            expected_to_pass=True,  # These should pass after fix
            business_impact="VALIDATES_FIX_EFFECTIVENESS"
        )
    
    async def _run_business_value_preservation_phase(self) -> TestPhaseResult:
        """
        Phase 4: Business value preservation validation.
        
        These tests ensure the fix doesn't break Golden Path functionality.
        """
        logger.info("📋 Phase 4: Business Value Preservation (Golden Path protection)")
        
        start_time = time.time()
        
        cmd = [
            "python3", "-m", "pytest",
            str(self.test_plan_path),
            "-k", "test_complete_websocket_auth_to_agent_response_flow or test_golden_path_preservation_post_fix",
            "-v", "--tb=short", 
            "--disable-warnings",
            "-m", "mission_critical"
        ]
        
        result = await self._execute_test_command(cmd)
        execution_time = time.time() - start_time
        
        return TestPhaseResult(
            phase_name="Business Value Preservation",
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            errors=result.get("errors", []),
            execution_time=execution_time,
            expected_to_pass=True,  # Critical for business continuity
            business_impact="PROTECTS_500K_ARR_FUNCTIONALITY"
        )
    
    async def _run_performance_regression_phase(self) -> TestPhaseResult:
        """
        Phase 5: Performance regression validation.
        
        These tests ensure the fix doesn't introduce performance issues.
        """
        logger.info("📋 Phase 5: Performance Regression Testing")
        
        start_time = time.time()
        
        cmd = [
            "python3", "-m", "pytest",
            str(self.test_plan_path),
            "-k", "TestWebSocketHandshakePerformance",
            "-v", "--tb=short",
            "--disable-warnings",
            "-m", "performance"
        ]
        
        result = await self._execute_test_command(cmd)
        execution_time = time.time() - start_time
        
        return TestPhaseResult(
            phase_name="Performance Regression",
            passed=result.get("passed", 0),
            failed=result.get("failed", 0), 
            skipped=result.get("skipped", 0),
            errors=result.get("errors", []),
            execution_time=execution_time,
            expected_to_pass=True,  # Performance must be maintained
            business_impact="ENSURES_USER_EXPERIENCE_QUALITY"
        )
    
    async def _execute_test_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Execute a pytest command and parse results."""
        try:
            logger.debug(f"Executing command: {' '.join(cmd)}")
            
            # Execute the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse pytest output
            stdout_text = stdout.decode('utf-8')
            stderr_text = stderr.decode('utf-8')
            
            return self._parse_pytest_output(stdout_text, stderr_text, process.returncode)
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "errors": [f"Test execution error: {str(e)}"],
                "output": "",
                "return_code": -1
            }
    
    def _parse_pytest_output(self, stdout: str, stderr: str, return_code: int) -> Dict[str, Any]:
        """Parse pytest output to extract test results."""
        result = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "output": stdout,
            "stderr": stderr,
            "return_code": return_code
        }
        
        # Parse test results from output
        lines = stdout.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for pytest summary line
            if " passed" in line or " failed" in line or " skipped" in line:
                # Parse counts
                if " passed" in line:
                    try:
                        passed = int(line.split()[0])
                        result["passed"] = passed
                    except (ValueError, IndexError):
                        pass
                
                if " failed" in line:
                    try:
                        # Handle "X failed" or "X failed, Y passed" formats
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "failed" and i > 0:
                                result["failed"] = int(parts[i-1])
                                break
                    except (ValueError, IndexError):
                        pass
                
                if " skipped" in line:
                    try:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "skipped" and i > 0:
                                result["skipped"] = int(parts[i-1])
                                break
                    except (ValueError, IndexError):
                        pass
            
            # Collect error information
            if "FAILED" in line or "ERROR" in line:
                result["errors"].append(line)
        
        # If no tests were parsed from summary, try to count from individual results
        if result["passed"] == 0 and result["failed"] == 0:
            passed_count = stdout.count("PASSED")
            failed_count = stdout.count("FAILED")
            skipped_count = stdout.count("SKIPPED")
            
            result["passed"] = passed_count
            result["failed"] = failed_count
            result["skipped"] = skipped_count
        
        return result
    
    def _log_phase_result(self, result: TestPhaseResult):
        """Log the results of a test phase."""
        status_emoji = "✅" if result.expected_to_pass and result.failed == 0 else "❌" if not result.expected_to_pass and result.passed > 0 else "⚠️"
        
        logger.info(f"{status_emoji} {result.phase_name}: {result.passed} passed, {result.failed} failed, {result.skipped} skipped")
        logger.info(f"   Execution time: {result.execution_time:.2f}s")
        logger.info(f"   Business impact: {result.business_impact}")
        
        if result.errors:
            logger.warning(f"   Errors detected: {len(result.errors)}")
            for error in result.errors[:3]:  # Show first 3 errors
                logger.warning(f"     - {error}")
        
        logger.info("")
    
    def _generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report with business impact analysis."""
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)
        total_time = sum(r.execution_time for r in self.results)
        
        # Business impact analysis
        business_impact_analysis = self._analyze_business_impact()
        
        # Overall assessment
        overall_status = self._calculate_overall_status()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "total_execution_time": total_time,
                "phases_completed": len(self.results)
            },
            "phase_results": [
                {
                    "phase_name": r.phase_name,
                    "passed": r.passed,
                    "failed": r.failed,
                    "skipped": r.skipped,
                    "execution_time": r.execution_time,
                    "expected_to_pass": r.expected_to_pass,
                    "business_impact": r.business_impact,
                    "status": "PASS" if r.expected_to_pass and r.failed == 0 else "EXPECTED_FAIL" if not r.expected_to_pass and r.failed > 0 else "UNEXPECTED_RESULT"
                }
                for r in self.results
            ],
            "business_impact_analysis": business_impact_analysis,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _analyze_business_impact(self) -> Dict[str, Any]:
        """Analyze the business impact of test results."""
        # Find business value preservation phase
        bv_phase = next((r for r in self.results if "Business Value" in r.phase_name), None)
        
        # Calculate chat functionality risk
        chat_functionality_risk = "LOW"
        revenue_at_risk = "< 10%"
        
        if bv_phase:
            if bv_phase.failed > 0:
                chat_functionality_risk = "HIGH"
                revenue_at_risk = "$500K+ ARR"
            elif bv_phase.passed == 0:
                chat_functionality_risk = "CRITICAL"
                revenue_at_risk = "$500K+ ARR"
        
        # Overall business health
        critical_failures = sum(1 for r in self.results if r.business_impact.startswith("PROTECTS") and r.failed > 0)
        
        business_health = "HEALTHY"
        if critical_failures > 0:
            business_health = "AT_RISK"
        elif sum(r.failed for r in self.results) > sum(r.passed for r in self.results):
            business_health = "DEGRADED"
        
        return {
            "chat_functionality_risk": chat_functionality_risk,
            "revenue_at_risk": revenue_at_risk,
            "business_health": business_health,
            "critical_failures": critical_failures,
            "golden_path_status": "PROTECTED" if bv_phase and bv_phase.failed == 0 else "VULNERABLE"
        }
    
    def _calculate_overall_status(self) -> str:
        """Calculate overall test suite status."""
        # Check if this appears to be pre-fix or post-fix execution
        issue_demo_phase = next((r for r in self.results if "Issue Demonstration" in r.phase_name), None)
        remediation_phase = next((r for r in self.results if "Remediation" in r.phase_name), None)
        
        if issue_demo_phase and issue_demo_phase.failed > 0 and not (remediation_phase and remediation_phase.passed > 0):
            return "PRE_FIX_VALIDATION"  # Issue demonstrated, fix not yet implemented
        elif remediation_phase and remediation_phase.passed > 0:
            return "POST_FIX_VALIDATION"  # Fix appears to be working
        else:
            return "INDETERMINATE"
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Check each phase for issues
        for result in self.results:
            if "Issue Demonstration" in result.phase_name and result.failed == 0:
                recommendations.append("⚠️ Issue demonstration tests are not failing - the handshake issue may already be fixed or tests need adjustment")
            
            elif "RFC 6455" in result.phase_name and result.failed > 0:
                recommendations.append("🔧 RFC 6455 compliance issues detected - review subprotocol negotiation implementation")
            
            elif "Remediation" in result.phase_name and result.failed > 0:
                recommendations.append("🚨 Remediation validation failing - handshake fix may not be working correctly")
            
            elif "Business Value" in result.phase_name and result.failed > 0:
                recommendations.append("💰 CRITICAL: Business value preservation failing - Golden Path functionality at risk")
            
            elif "Performance" in result.phase_name and result.failed > 0:
                recommendations.append("⚡ Performance regression detected - optimize handshake implementation")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ All test phases completed successfully - handshake implementation appears correct")
        
        recommendations.extend([
            "📊 Monitor business metrics after deploying handshake fixes",
            "🔍 Validate with real user scenarios in staging environment",
            "📋 Update documentation with new handshake requirements"
        ])
        
        return recommendations


async def main():
    """Main execution function."""
    runner = WebSocketHandshakeTestRunner()
    
    try:
        # Run comprehensive test suite
        report = await runner.run_comprehensive_test_suite()
        
        # Display final report
        logger.info("🎯 FINAL REPORT")
        logger.info("=" * 70)
        logger.info(f"Overall Status: {report['overall_status']}")
        logger.info(f"Tests: {report['summary']['total_passed']} passed, {report['summary']['total_failed']} failed, {report['summary']['total_skipped']} skipped")
        logger.info(f"Execution Time: {report['summary']['total_execution_time']:.2f}s")
        logger.info(f"Business Health: {report['business_impact_analysis']['business_health']}")
        logger.info(f"Revenue Risk: {report['business_impact_analysis']['revenue_at_risk']}")
        
        logger.info("\n📋 RECOMMENDATIONS:")
        for rec in report['recommendations']:
            logger.info(f"  {rec}")
        
        # Save detailed report
        report_path = runner.project_root / "test_results" / f"websocket_handshake_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n📄 Detailed report saved to: {report_path}")
        
        # Exit with appropriate code
        if report['business_impact_analysis']['business_health'] == "HEALTHY":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    # Handle both synchronous and asynchronous execution
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())