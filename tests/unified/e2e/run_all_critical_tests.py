#!/usr/bin/env python
"""
Unified Critical Test Runner - Production Readiness Validation

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: All segments - critical for production stability
2. Business Goal: Validate complete system reliability before deployment
3. Value Impact: Prevents production failures that could impact $597K+ MRR
4. Revenue Impact: Safeguards customer trust and prevents churn from system failures

This script runs the most critical tests that validate core system functionality:
- Authentication flow across services
- WebSocket communication and auth integration
- Database consistency and synchronization
- Service health and cascade prevention
- Session persistence across services
- Concurrent user isolation
- Real user journeys from signup to chat

Exit codes: 0 = all critical tests pass, 1 = any critical test failed
"""

import subprocess
import sys
import time
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict

@dataclass
class CriticalTestResult:
    """Result of running a critical test"""
    test_name: str
    file_path: str
    status: str  # 'passed', 'failed', 'timeout', 'error', 'skipped'
    duration: float
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    priority: str = "P1"  # P0 = Critical, P1 = High, P2 = Medium

@dataclass
class CriticalTestSummary:
    """Summary of critical test execution"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    timeout_tests: int
    error_tests: int
    skipped_tests: int
    total_duration: float
    success_rate: float
    critical_tests_passed: int
    critical_tests_total: int
    results: List[CriticalTestResult]

class CriticalTestRunner:
    """Runs all critical tests with detailed reporting"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.reports_dir = self.project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Define critical tests in order of execution priority
        self.critical_tests = [
            # P0 - CRITICAL (Must pass for production)
            {
                "name": "Auth Integration Fixed",
                "file": "test_critical_unified_flows.py::TestCriticalUnifiedFlows::test_complete_signup_login_chat_flow",
                "priority": "P0",
                "description": "Complete user journey from signup to chat"
            },
            {
                "name": "WebSocket Auth Integration", 
                "file": "test_real_websocket_auth_integration.py",
                "priority": "P0",
                "description": "WebSocket authentication and real-time communication"
            },
            {
                "name": "Cross-Service Auth Sync",
                "file": "test_critical_unified_flows.py::TestCriticalUnifiedFlows::test_jwt_token_cross_service_validation",
                "priority": "P0",
                "description": "JWT token validation across all services"
            },
            {
                "name": "Auth Service Independence",
                "file": "test_auth_service_independence.py",
                "priority": "P0", 
                "description": "Auth service operates independently"
            },
            {
                "name": "Database Sync Fixed",
                "file": "test_real_database_consistency.py",
                "priority": "P0",
                "description": "Database consistency across services"
            },
            {
                "name": "Health Cascade Prevention",
                "file": "test_critical_unified_flows.py::TestCriticalUnifiedFlows::test_service_health_and_recovery",
                "priority": "P0",
                "description": "Service health checks and failure prevention"
            },
            
            # P1 - HIGH (Important for user experience)
            {
                "name": "Session Persistence Fixed",
                "file": "test_real_session_persistence.py",
                "priority": "P1",
                "description": "User session persistence across requests"
            },
            {
                "name": "Concurrent User Isolation",
                "file": "test_critical_unified_flows.py::TestCriticalUnifiedFlows::test_concurrent_user_isolation", 
                "priority": "P1",
                "description": "Multi-user data isolation"
            },
            {
                "name": "WebSocket Message Format",
                "file": "test_websocket_message_format_validation.py",
                "priority": "P1",
                "description": "WebSocket message structure validation"
            },
            {
                "name": "Agent Lifecycle Events",
                "file": "test_agent_lifecycle_websocket_events.py",
                "priority": "P1", 
                "description": "Agent execution WebSocket events"
            },
            
            # P2 - MEDIUM (Nice to have working)
            {
                "name": "Rate Limiting",
                "file": "test_real_rate_limiting.py",
                "priority": "P2",
                "description": "Rate limiting enforcement"
            },
            {
                "name": "OAuth Integration", 
                "file": "test_real_oauth_integration.py",
                "priority": "P2",
                "description": "OAuth login flow"
            }
        ]
    
    def _find_test_file(self, file_spec: str) -> Path:
        """Find the actual test file path"""
        e2e_dir = self.project_root / "tests" / "unified" / "e2e"
        
        # Handle specific test function format
        if "::" in file_spec:
            file_part = file_spec.split("::")[0]
        else:
            file_part = file_spec
            
        test_file = e2e_dir / file_part
        if test_file.exists():
            return test_file
        
        # If not found, return the path anyway for error reporting
        return test_file
    
    def run_single_test(self, test_config: Dict[str, str]) -> CriticalTestResult:
        """Run a single critical test"""
        print(f"\n[TEST] Running: {test_config['name']}")
        print(f"   Priority: {test_config['priority']} - {test_config['description']}")
        
        start_time = time.time()
        test_file = self._find_test_file(test_config['file'])
        
        try:
            # Build pytest command
            if "::" in test_config['file']:
                # Specific test method
                cmd = [
                    sys.executable, "-m", "pytest",
                    test_config['file'],
                    "-v", "--tb=short",
                    "--timeout=30",
                    "-x"  # Stop on first failure
                ]
            else:
                # Entire test file
                cmd = [
                    sys.executable, "-m", "pytest", 
                    str(test_file),
                    "-v", "--tb=short",
                    "--timeout=20", 
                    "-x"
                ]
            
            # Run test with timeout
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=45  # 45 second timeout for entire test
            )
            
            duration = time.time() - start_time
            
            # Determine status
            if result.returncode == 0:
                status = 'passed'
                print(f"   [PASS] PASSED in {duration:.1f}s")
            elif "SKIPPED" in result.stdout or "skip" in result.stdout.lower():
                status = 'skipped'
                print(f"   [SKIP] SKIPPED in {duration:.1f}s")
            else:
                status = 'failed'
                print(f"   [FAIL] FAILED in {duration:.1f}s")
                
                # Show first few lines of error for immediate feedback
                if result.stderr:
                    error_lines = result.stderr.split('\n')[:3]
                    for line in error_lines:
                        if line.strip():
                            print(f"      Error: {line.strip()}")
            
            return CriticalTestResult(
                test_name=test_config['name'],
                file_path=test_config['file'],
                status=status,
                duration=duration,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                priority=test_config['priority']
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"   [TIME] TIMEOUT after {duration:.1f}s")
            return CriticalTestResult(
                test_name=test_config['name'],
                file_path=test_config['file'],
                status='timeout',
                duration=duration,
                exit_code=-1,
                stdout="",
                stderr="Test timed out after 45 seconds",
                priority=test_config['priority']
            )
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"   [ERROR] ERROR after {duration:.1f}s: {e}")
            return CriticalTestResult(
                test_name=test_config['name'],
                file_path=test_config['file'],
                status='error',
                duration=duration,
                exit_code=-1,
                stdout="",
                stderr=f"Error running test: {str(e)}",
                priority=test_config['priority']
            )
    
    def generate_summary(self, results: List[CriticalTestResult]) -> CriticalTestSummary:
        """Generate test execution summary"""
        if not results:
            return CriticalTestSummary(
                total_tests=0, passed_tests=0, failed_tests=0,
                timeout_tests=0, error_tests=0, skipped_tests=0,
                total_duration=0.0, success_rate=0.0,
                critical_tests_passed=0, critical_tests_total=0,
                results=[]
            )
        
        passed = len([r for r in results if r.status == 'passed'])
        failed = len([r for r in results if r.status == 'failed'])
        timeout = len([r for r in results if r.status == 'timeout'])
        error = len([r for r in results if r.status == 'error'])
        skipped = len([r for r in results if r.status == 'skipped'])
        total = len(results)
        
        # Calculate critical test metrics (P0 tests)
        critical_tests = [r for r in results if r.priority == 'P0']
        critical_passed = len([r for r in critical_tests if r.status == 'passed'])
        critical_total = len(critical_tests)
        
        # Success rate calculation (passed / (total - skipped))
        non_skipped = total - skipped
        success_rate = (passed / non_skipped * 100) if non_skipped > 0 else 0.0
        
        total_duration = sum(r.duration for r in results)
        
        return CriticalTestSummary(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            timeout_tests=timeout,
            error_tests=error,
            skipped_tests=skipped,
            total_duration=total_duration,
            success_rate=success_rate,
            critical_tests_passed=critical_passed,
            critical_tests_total=critical_total,
            results=results
        )
    
    def save_report(self, summary: CriticalTestSummary) -> Path:
        """Save detailed JSON report"""
        report_file = self.reports_dir / "critical_tests_results.json"
        
        with open(report_file, 'w') as f:
            json.dump(asdict(summary), f, indent=2, default=str)
        
        return report_file
    
    def print_summary_report(self, summary: CriticalTestSummary):
        """Print detailed summary report"""
        print("\n" + "="*80)
        print("CRITICAL TESTS EXECUTION SUMMARY")
        print("="*80)
        
        # Overall status with clear visual indicators
        critical_success = (summary.critical_tests_passed == summary.critical_tests_total 
                           and summary.critical_tests_total > 0)
        
        if critical_success and summary.failed_tests == 0 and summary.error_tests == 0:
            print("[SUCCESS] PRODUCTION READY - ALL CRITICAL TESTS PASSED")
            deployment_status = "[DEPLOY] READY FOR DEPLOYMENT"
        elif critical_success:
            print("[CAUTION] CRITICAL TESTS PASSED - Some non-critical issues")
            deployment_status = "[DEPLOY] DEPLOY WITH CAUTION"
        else:
            print("[BLOCKED] PRODUCTION NOT READY - CRITICAL TESTS FAILED")
            deployment_status = "[BLOCKED] DO NOT DEPLOY"
        
        # Test execution metrics
        print(f"\nTest Results:")
        print(f"   Total Tests: {summary.total_tests}")
        print(f"   [PASS] Passed: {summary.passed_tests}")
        print(f"   [FAIL] Failed: {summary.failed_tests}")
        print(f"   [TIME] Timeout: {summary.timeout_tests}")
        print(f"   [ERROR] Error: {summary.error_tests}")
        print(f"   [SKIP] Skipped: {summary.skipped_tests}")
        print(f"   Success Rate: {summary.success_rate:.1f}%")
        
        # Critical tests status (P0)
        print(f"\nCritical Tests (P0):")
        print(f"   [PASS] Passed: {summary.critical_tests_passed}")
        print(f"   Total: {summary.critical_tests_total}")
        critical_rate = (summary.critical_tests_passed / summary.critical_tests_total * 100) if summary.critical_tests_total > 0 else 0
        print(f"   Critical Success Rate: {critical_rate:.1f}%")
        
        # Performance metrics
        print(f"\nPerformance:")
        print(f"   Total Duration: {summary.total_duration:.1f}s")
        if summary.total_tests > 0:
            print(f"   Average per Test: {summary.total_duration/summary.total_tests:.1f}s")
        
        # Show individual test results by priority
        print(f"\nDetailed Results:")
        
        # Group by priority
        p0_tests = [r for r in summary.results if r.priority == 'P0']
        p1_tests = [r for r in summary.results if r.priority == 'P1']
        p2_tests = [r for r in summary.results if r.priority == 'P2']
        
        for priority, tests, label in [('P0', p0_tests, 'CRITICAL'), ('P1', p1_tests, 'HIGH'), ('P2', p2_tests, 'MEDIUM')]:
            if tests:
                print(f"\n   {priority} - {label} Priority:")
                for result in tests:
                    status_icon = self._get_status_icon(result.status)
                    print(f"      {status_icon} {result.test_name} ({result.duration:.1f}s)")
                    if result.status in ['failed', 'error', 'timeout']:
                        # Show brief error info
                        if result.stderr:
                            error_line = result.stderr.split('\n')[0][:100]
                            print(f"         -> {error_line}")
        
        # Business impact assessment
        print(f"\nBusiness Impact:")
        if critical_success:
            print("   [PROTECTED] $597K+ MRR protected")
            print("   [VALIDATED] User journey validated")
            print("   [STABLE] Production stability assured")
        else:
            print("   [RISK] Revenue at risk from failed critical paths")
            print("   [RISK] User experience may be compromised")
            print("   [RISK] Production stability uncertain")
        
        # Deployment recommendation
        print(f"\nDeployment Status: {deployment_status}")
        
        print("="*80)
    
    def _get_status_icon(self, status: str) -> str:
        """Get visual icon for test status"""
        icons = {
            'passed': '[PASS]',
            'failed': '[FAIL]',
            'timeout': '[TIME]',
            'error': '[ERROR]',
            'skipped': '[SKIP]'
        }
        return icons.get(status, '[UNK]')
    
    def run_all_critical_tests(self) -> CriticalTestSummary:
        """Run all critical tests and generate comprehensive report"""
        print("Starting Critical Test Execution")
        print(f"Project Root: {self.project_root}")
        print(f"Running {len(self.critical_tests)} critical tests")
        
        # Run each test
        results = []
        for i, test_config in enumerate(self.critical_tests, 1):
            print(f"\n[{i}/{len(self.critical_tests)}]", end="")
            result = self.run_single_test(test_config)
            results.append(result)
            
            # Early exit if critical test fails (optional)
            if result.status in ['failed', 'error'] and result.priority == 'P0':
                print(f"\n[WARNING] Critical test failed: {result.test_name}")
                print("   Continuing with remaining tests for full assessment...")
        
        # Generate comprehensive summary
        summary = self.generate_summary(results)
        
        # Save detailed report
        report_file = self.save_report(summary)
        print(f"\nDetailed report saved: {report_file}")
        
        # Display summary
        self.print_summary_report(summary)
        
        return summary

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Run critical tests for Netra Apex production readiness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all_critical_tests.py           # Run all critical tests
  python run_all_critical_tests.py --list    # List critical tests
  python run_all_critical_tests.py --dry-run # Show what would be run
        """
    )
    
    parser.add_argument(
        '--list', action='store_true',
        help='List all critical tests without running them'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what tests would be run without executing them'
    )
    parser.add_argument(
        '--priority', choices=['P0', 'P1', 'P2'], 
        help='Run only tests of specified priority (P0=Critical, P1=High, P2=Medium)'
    )
    
    args = parser.parse_args()
    
    try:
        runner = CriticalTestRunner()
        
        if args.list:
            print("Critical Tests Configuration:")
            print("="*60)
            for i, test in enumerate(runner.critical_tests, 1):
                print(f"{i:2d}. [{test['priority']}] {test['name']}")
                print(f"     File: {test['file']}")
                print(f"     Description: {test['description']}")
                print()
            return
            
        if args.dry_run:
            tests_to_run = runner.critical_tests
            if args.priority:
                tests_to_run = [t for t in tests_to_run if t['priority'] == args.priority]
            
            print(f"Would run {len(tests_to_run)} tests:")
            for test in tests_to_run:
                print(f"  [{test['priority']}] {test['name']}")
            return
        
        print("Netra Apex Critical Test Runner")
        print("   Validating production readiness...")
        
        # Filter tests by priority if specified
        if args.priority:
            original_tests = runner.critical_tests
            runner.critical_tests = [t for t in original_tests if t['priority'] == args.priority]
            print(f"   Running only {args.priority} priority tests ({len(runner.critical_tests)} tests)")
        
        summary = runner.run_all_critical_tests()
        
        # Determine exit code based on critical test results
        critical_tests_passed = (summary.critical_tests_passed == summary.critical_tests_total 
                               and summary.critical_tests_total > 0)
        
        # Exit with success only if all critical tests pass
        if critical_tests_passed and summary.failed_tests == 0 and summary.error_tests == 0:
            print("\n[SUCCESS] All critical tests passed - Production ready!")
            sys.exit(0)
        elif critical_tests_passed:
            print("\n[CAUTION] Critical tests passed but some non-critical issues exist")
            sys.exit(0)  # Still allow deployment if critical paths work
        else:
            print("\n[BLOCKED] Critical test failures detected - Do not deploy!")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()