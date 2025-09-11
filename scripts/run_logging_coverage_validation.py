#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging Coverage Validation Runner
==================================

Validates all Priority 1 logging gap remediation fixes for Golden Path protection.

Business Impact: Protects $500K+ ARR by ensuring DevOps teams have immediate visibility 
into critical failures affecting user chat functionality.

CRITICAL LOGGING REMEDIATION VALIDATION:
1. Agent Execution Failures - ENHANCED logging with rich error context
2. JWT Authentication Failures - NEW comprehensive test coverage
3. Database Connection Failures - VALIDATED existing comprehensive logging

Usage:
    python run_logging_coverage_validation.py
    python run_logging_coverage_validation.py --detailed
    python run_logging_coverage_validation.py --ci-mode
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import json
import os

# Fix Windows console encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class LoggingCoverageValidator:
    """Validates all logging coverage improvements for Golden Path protection."""
    
    def __init__(self, detailed=False, ci_mode=False):
        self.detailed = detailed
        self.ci_mode = ci_mode
        self.results = {}
        self.start_time = datetime.now()
        
    def run_test_suite(self, test_path, suite_name):
        """Run a specific test suite and capture results."""
        print(f"\n{'='*60}")
        print(f"🔍 VALIDATING: {suite_name}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(test_path), 
                "-v", 
                "--tb=short" if not self.detailed else "--tb=long"
            ], capture_output=True, text=True, timeout=300)
            
            self.results[suite_name] = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "passed": result.returncode == 0
            }
            
            if result.returncode == 0:
                print(f"✅ {suite_name}: PASSED")
                if self.detailed:
                    print(f"Output:\n{result.stdout}")
            else:
                print(f"❌ {suite_name}: FAILED")
                print(f"Error Output:\n{result.stderr}")
                if self.detailed:
                    print(f"Full Output:\n{result.stdout}")
                    
        except subprocess.TimeoutExpired:
            print(f"⏰ {suite_name}: TIMEOUT (5 minutes)")
            self.results[suite_name] = {
                "return_code": -1,
                "stdout": "",
                "stderr": "Test suite timed out after 5 minutes",
                "passed": False
            }
        except Exception as e:
            print(f"💥 {suite_name}: EXCEPTION - {str(e)}")
            self.results[suite_name] = {
                "return_code": -2,
                "stdout": "",
                "stderr": f"Exception: {str(e)}",
                "passed": False
            }
    
    def validate_logging_coverage(self):
        """Run comprehensive logging coverage validation."""
        print("🚨 CRITICAL BUSINESS MISSION: Golden Path Logging Coverage Validation")
        print("📊 Business Impact: Protecting $500K+ ARR through DevOps visibility")
        print(f"⏰ Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test suites in order of business priority
        test_suites = [
            {
                "path": "tests/logging_coverage/test_authentication_failure_logging.py",
                "name": "JWT Authentication Failure Logging",
                "priority": "P0 - CRITICAL",
                "business_impact": "Prevents user login failures from going undiagnosed"
            },
            {
                "path": "tests/logging_coverage/test_service_dependency_failure_logging.py", 
                "name": "Database Connection Failure Logging",
                "priority": "P0 - CRITICAL",
                "business_impact": "Ensures data persistence failures are immediately visible"
            },
            {
                "path": "netra_backend/tests/integration/test_agent_execution_logging.py",
                "name": "Agent Execution Failure Logging", 
                "priority": "P0 - CRITICAL",
                "business_impact": "Agent failures block 90% of platform value (chat)"
            }
        ]
        
        for suite in test_suites:
            print(f"\n📋 {suite['name']}")
            print(f"🎯 Priority: {suite['priority']}")  
            print(f"💼 Business Impact: {suite['business_impact']}")
            
            test_path = Path(suite['path'])
            if test_path.exists():
                self.run_test_suite(test_path, suite['name'])
            else:
                print(f"⚠️  Test file not found: {test_path}")
                self.results[suite['name']] = {
                    "return_code": -3,
                    "stdout": "",
                    "stderr": f"Test file not found: {test_path}",
                    "passed": False
                }
    
    def generate_report(self):
        """Generate comprehensive validation report."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        passed_count = sum(1 for r in self.results.values() if r['passed'])
        total_count = len(self.results)
        pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0
        
        print(f"\n{'='*80}")
        print("📊 LOGGING COVERAGE VALIDATION REPORT")
        print(f"{'='*80}")
        print(f"⏰ Duration: {duration.total_seconds():.2f} seconds")
        print(f"📈 Pass Rate: {pass_rate:.1f}% ({passed_count}/{total_count})")
        
        if pass_rate >= 100:
            print("🎉 STATUS: GOLDEN PATH FULLY PROTECTED")
            print("✅ All critical logging gaps have been remediated")
            print("🛡️  DevOps teams have complete visibility into failures")
        elif pass_rate >= 67:
            print("⚠️  STATUS: PARTIAL PROTECTION - IMMEDIATE ACTION REQUIRED")
            print("🔧 Some critical logging gaps remain")
        else:
            print("🚨 STATUS: CRITICAL GAPS REMAIN - BUSINESS AT RISK")
            print("💥 $500K+ ARR Golden Path inadequately protected")
        
        print(f"\n📋 DETAILED RESULTS:")
        for suite_name, result in self.results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"  {status} {suite_name}")
            if not result['passed'] and not self.ci_mode:
                print(f"    Error: {result['stderr'][:200]}...")
        
        # Business value analysis
        print(f"\n💼 BUSINESS VALUE ANALYSIS:")
        critical_failures = [name for name, result in self.results.items() if not result['passed']]
        
        if not critical_failures:
            print("✅ All critical business workflows protected")
            print("✅ User authentication failures will be immediately visible")
            print("✅ Database connection issues will trigger alerts")
            print("✅ Agent execution failures will be comprehensively logged")
        else:
            print(f"🚨 {len(critical_failures)} critical gaps remain:")
            for failure in critical_failures:
                print(f"   - {failure}")
            print("⚠️  Business risk: DevOps teams may miss critical failures")
            print("⚠️  Customer impact: Silent failures affecting user experience")
        
        # CI/CD integration
        if self.ci_mode:
            report_data = {
                "timestamp": end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "pass_rate": pass_rate,
                "passed_count": passed_count,
                "total_count": total_count,
                "critical_failures": critical_failures,
                "business_protected": len(critical_failures) == 0
            }
            
            with open("logging_coverage_validation_report.json", "w") as f:
                json.dump(report_data, f, indent=2)
            
            print(f"\n📄 Report saved: logging_coverage_validation_report.json")
        
        return pass_rate >= 100
    
    def run_validation(self):
        """Execute complete logging coverage validation."""
        try:
            self.validate_logging_coverage()
            success = self.generate_report()
            return 0 if success else 1
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Validation interrupted by user")
            return 2
        except Exception as e:
            print(f"\n💥 Validation failed with exception: {str(e)}")
            return 3


def main():
    """Main entry point for logging coverage validation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate Priority 1 logging gap remediation for Golden Path protection"
    )
    parser.add_argument(
        "--detailed", 
        action="store_true",
        help="Show detailed test output"
    )
    parser.add_argument(
        "--ci-mode",
        action="store_true", 
        help="CI/CD mode - generate JSON report and minimize output"
    )
    
    args = parser.parse_args()
    
    validator = LoggingCoverageValidator(
        detailed=args.detailed,
        ci_mode=args.ci_mode
    )
    
    exit_code = validator.run_validation()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()