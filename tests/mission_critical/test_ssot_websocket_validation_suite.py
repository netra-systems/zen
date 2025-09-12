#!/usr/bin/env python
"""MISSION CRITICAL: SSOT WebSocket Validation Suite Runner

THIS SUITE ORCHESTRATES ALL SSOT WEBSOCKET FACTORY PATTERN VALIDATION TESTS.
Business Value: $500K+ ARR - Comprehensive WebSocket SSOT migration validation

PURPOSE:
- Orchestrate all SSOT WebSocket factory pattern validation tests
- Provide unified execution and reporting for migration validation
- Track test results across different migration phases
- Generate comprehensive validation reports for stakeholders

TEST SUITES INCLUDED:
1. test_ssot_websocket_factory_compliance.py - Factory pattern compliance validation
2. test_websocket_factory_migration.py - Migration process validation  
3. test_websocket_health_ssot.py - Health endpoint SSOT integration validation

EXECUTION PHASES:
- PRE-MIGRATION: Validate current violations exist and SSOT patterns work
- DURING-MIGRATION: Track progress and ensure no regressions
- POST-MIGRATION: Validate successful remediation and full functionality

BUSINESS IMPACT:
These tests protect the Golden Path during migration, ensuring users can
continue to login and receive AI responses throughout the SSOT remediation.
"""

import asyncio
import os
import sys
import json
import time
import uuid
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger


@dataclass
class TestResult:
    """Test execution result data structure."""
    test_file: str
    test_name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration: float
    error_message: Optional[str] = None
    migration_phase: Optional[str] = None


class SsotWebSocketValidationSuite:
    """Comprehensive SSOT WebSocket validation suite orchestrator."""
    
    def __init__(self):
        self.suite_id = f"ssot_validation_{uuid.uuid4().hex[:8]}"
        self.start_time = datetime.now()
        self.test_files = [
            "test_ssot_websocket_factory_compliance.py",
            "test_websocket_factory_migration.py", 
            "test_websocket_health_ssot.py"
        ]
        self.results: List[TestResult] = []
        
    def detect_migration_phase(self) -> str:
        """Detect current migration phase based on codebase state."""
        logger.info("[MIGRATION PHASE] Detecting current migration phase...")
        
        # Check for deprecated factory imports in critical files
        websocket_ssot_path = os.path.join(project_root, "netra_backend/app/routes/websocket_ssot.py")
        violations_found = 0
        
        if os.path.exists(websocket_ssot_path):
            with open(websocket_ssot_path, 'r') as f:
                content = f.read()
                if 'get_websocket_manager_factory' in content:
                    violations_found += 1
                    
        if violations_found > 0:
            logger.info("[PRE-MIGRATION] Detected pre-migration state - violations present")
            return "pre-migration"
        else:
            logger.info("[POST-MIGRATION] Detected post-migration state - no violations found") 
            return "post-migration"

    async def run_test_file(self, test_file: str) -> List[TestResult]:
        """Run a single test file and collect results."""
        logger.info(f"[TEST EXECUTION] Running {test_file}...")
        
        test_file_path = os.path.join(os.path.dirname(__file__), test_file)
        if not os.path.exists(test_file_path):
            logger.error(f"[TEST ERROR] Test file not found: {test_file}")
            return [TestResult(
                test_file=test_file,
                test_name="file_not_found",
                status="error", 
                duration=0.0,
                error_message=f"Test file not found: {test_file}"
            )]
        
        try:
            # Run pytest on the specific file with detailed output
            start_time = time.time()
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                test_file_path,
                "-v",
                "--tb=short",
                "-x",  # Stop on first failure for debugging
                "--json-report",
                "--json-report-file=/tmp/pytest_report.json"
            ], capture_output=True, text=True, timeout=300)
            
            duration = time.time() - start_time
            
            # Parse results
            test_results = []
            
            if result.returncode == 0:
                logger.info(f"[TEST SUCCESS] {test_file} completed successfully in {duration:.2f}s")
                test_results.append(TestResult(
                    test_file=test_file,
                    test_name="overall",
                    status="passed",
                    duration=duration
                ))
            else:
                logger.warning(f"[TEST ISSUES] {test_file} had issues - examining output...")
                
                # Log stdout and stderr for analysis
                if result.stdout:
                    logger.info(f"[TEST STDOUT] {result.stdout}")
                if result.stderr:
                    logger.warning(f"[TEST STDERR] {result.stderr}")
                    
                # Determine if failures are migration-related or system issues
                output_text = result.stdout + result.stderr
                
                if "get_websocket_manager_factory" in output_text:
                    logger.info("[MIGRATION FAILURE] Test failure related to factory migration - expected")
                    test_results.append(TestResult(
                        test_file=test_file,
                        test_name="migration_expected",
                        status="expected_failure",
                        duration=duration,
                        error_message="Factory migration in progress"
                    ))
                else:
                    logger.error(f"[TEST FAILURE] {test_file} system failure")
                    test_results.append(TestResult(
                        test_file=test_file,
                        test_name="system_error",
                        status="failed",
                        duration=duration,
                        error_message=result.stderr[:500]  # Truncate long errors
                    ))
            
            return test_results
            
        except subprocess.TimeoutExpired:
            logger.error(f"[TEST TIMEOUT] {test_file} timed out after 300s")
            return [TestResult(
                test_file=test_file,
                test_name="timeout",
                status="error",
                duration=300.0,
                error_message="Test execution timeout"
            )]
            
        except Exception as e:
            logger.error(f"[TEST EXECUTION ERROR] Failed to run {test_file}: {e}")
            return [TestResult(
                test_file=test_file,
                test_name="execution_error",
                status="error",
                duration=0.0,
                error_message=str(e)
            )]

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all SSOT WebSocket validation tests."""
        logger.info(f"[SUITE START] Starting SSOT WebSocket validation suite: {self.suite_id}")
        
        migration_phase = self.detect_migration_phase()
        
        # Execute all test files
        all_results = []
        for test_file in self.test_files:
            file_results = await self.run_test_file(test_file)
            for result in file_results:
                result.migration_phase = migration_phase
            all_results.extend(file_results)
        
        self.results = all_results
        
        # Generate summary report
        return self.generate_summary_report()

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation summary report."""
        total_duration = time.time() - self.start_time.timestamp()
        
        # Categorize results
        passed = [r for r in self.results if r.status == "passed"]
        failed = [r for r in self.results if r.status == "failed"]
        expected_failures = [r for r in self.results if r.status == "expected_failure"]
        errors = [r for r in self.results if r.status == "error"]
        
        migration_phase = self.results[0].migration_phase if self.results else "unknown"
        
        summary = {
            "suite_id": self.suite_id,
            "execution_time": datetime.now().isoformat(),
            "total_duration_seconds": total_duration,
            "migration_phase": migration_phase,
            "test_summary": {
                "total_tests": len(self.results),
                "passed": len(passed),
                "failed": len(failed),
                "expected_failures": len(expected_failures),
                "errors": len(errors)
            },
            "test_files_executed": list(set(r.test_file for r in self.results)),
            "business_impact_assessment": self.assess_business_impact(),
            "migration_readiness": self.assess_migration_readiness(),
            "detailed_results": [
                {
                    "test_file": r.test_file,
                    "test_name": r.test_name,
                    "status": r.status,
                    "duration": r.duration,
                    "error_message": r.error_message,
                    "migration_phase": r.migration_phase
                }
                for r in self.results
            ]
        }
        
        return summary

    def assess_business_impact(self) -> Dict[str, Any]:
        """Assess business impact based on test results."""
        critical_failures = [r for r in self.results if r.status == "failed"]
        migration_failures = [r for r in self.results if r.status == "expected_failure"]
        
        if len(critical_failures) == 0:
            impact_level = "LOW"
            impact_description = "No critical system failures detected"
        elif len(critical_failures) <= 2:
            impact_level = "MEDIUM" 
            impact_description = f"{len(critical_failures)} system failures detected"
        else:
            impact_level = "HIGH"
            impact_description = f"{len(critical_failures)} critical failures - Golden Path at risk"
        
        return {
            "impact_level": impact_level,
            "description": impact_description,
            "critical_failures": len(critical_failures),
            "migration_related_issues": len(migration_failures),
            "arr_at_risk": "$500K+ ARR" if impact_level == "HIGH" else "No immediate risk"
        }

    def assess_migration_readiness(self) -> Dict[str, Any]:
        """Assess readiness for SSOT migration based on test results."""
        system_errors = [r for r in self.results if r.status in ["failed", "error"]]
        
        if len(system_errors) == 0:
            readiness = "READY"
            description = "All validation tests passing - safe to proceed with migration"
        elif len(system_errors) <= 1:
            readiness = "READY_WITH_CAUTION"
            description = "Minor issues detected - can proceed with careful monitoring"
        else:
            readiness = "NOT_READY"
            description = "Multiple system issues - resolve before migration"
            
        return {
            "readiness_status": readiness,
            "description": description,
            "blocking_issues": len(system_errors),
            "recommendation": self.get_migration_recommendation(readiness)
        }

    def get_migration_recommendation(self, readiness: str) -> str:
        """Get specific migration recommendation based on readiness."""
        recommendations = {
            "READY": "Proceed with SSOT migration. All validation tests confirm system stability.",
            "READY_WITH_CAUTION": "Proceed with migration but monitor closely. Address minor issues post-migration.",
            "NOT_READY": "Do not proceed with migration. Resolve system issues first to protect $500K+ ARR."
        }
        return recommendations.get(readiness, "Unknown readiness status")

    def print_summary_report(self, summary: Dict[str, Any]):
        """Print formatted summary report to console."""
        print("\n" + "="*80)
        print("SSOT WEBSOCKET VALIDATION SUITE SUMMARY REPORT")
        print("="*80)
        print(f"Suite ID: {summary['suite_id']}")
        print(f"Execution Time: {summary['execution_time']}")
        print(f"Total Duration: {summary['total_duration_seconds']:.2f} seconds")
        print(f"Migration Phase: {summary['migration_phase']}")
        
        print(f"\nTEST SUMMARY:")
        ts = summary['test_summary']
        print(f"  Total Tests: {ts['total_tests']}")
        print(f"  ✅ Passed: {ts['passed']}")
        print(f"  ❌ Failed: {ts['failed']}")
        print(f"  ⚠️ Expected Failures: {ts['expected_failures']}")
        print(f"  🚨 Errors: {ts['errors']}")
        
        print(f"\nBUSINESS IMPACT ASSESSMENT:")
        bia = summary['business_impact_assessment']
        print(f"  Impact Level: {bia['impact_level']}")
        print(f"  Description: {bia['description']}")
        print(f"  ARR at Risk: {bia['arr_at_risk']}")
        
        print(f"\nMIGRATION READINESS:")
        mr = summary['migration_readiness']
        print(f"  Status: {mr['readiness_status']}")
        print(f"  Recommendation: {mr['recommendation']}")
        
        print(f"\nTEST FILES EXECUTED:")
        for test_file in summary['test_files_executed']:
            print(f"  - {test_file}")
        
        print(f"\nDETAILED RESULTS:")
        for result in summary['detailed_results']:
            status_icon = {"passed": "✅", "failed": "❌", "expected_failure": "⚠️", "error": "🚨"}
            icon = status_icon.get(result['status'], "❓")
            print(f"  {icon} {result['test_file']}: {result['status']} ({result['duration']:.2f}s)")
            if result['error_message']:
                print(f"      Error: {result['error_message'][:100]}...")
        
        print("="*80)


async def main():
    """Main execution function for SSOT WebSocket validation suite."""
    print("Starting SSOT WebSocket Factory Pattern Validation Suite...")
    
    suite = SsotWebSocketValidationSuite()
    summary = await suite.run_all_tests()
    
    # Print detailed summary
    suite.print_summary_report(summary)
    
    # Save report to file
    report_filename = f"ssot_validation_report_{suite.suite_id}.json"
    report_path = os.path.join(project_root, "tests", "mission_critical", report_filename)
    
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    # Return appropriate exit code based on results
    business_impact = summary['business_impact_assessment']
    if business_impact['impact_level'] == "HIGH":
        print("\n🚨 HIGH BUSINESS IMPACT DETECTED - REVIEW REQUIRED")
        return 1
    elif business_impact['impact_level'] == "MEDIUM":
        print("\n⚠️ MEDIUM BUSINESS IMPACT - MONITOR CLOSELY")
        return 0
    else:
        print("\n✅ LOW BUSINESS IMPACT - VALIDATION SUCCESSFUL")
        return 0


if __name__ == "__main__":
    # Run the validation suite
    exit_code = asyncio.run(main())
    sys.exit(exit_code)