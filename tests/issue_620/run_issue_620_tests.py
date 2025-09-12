#!/usr/bin/env python3
"""Test Runner for Issue #620 SSOT ExecutionEngine Migration Tests.

This script runs the comprehensive test suite for validating the SSOT ExecutionEngine
migration from multiple deprecated implementations to UserExecutionEngine.

Usage:
    python tests/issue_620/run_issue_620_tests.py --phase all
    python tests/issue_620/run_issue_620_tests.py --phase reproduction
    python tests/issue_620/run_issue_620_tests.py --phase golden-path
    python tests/issue_620/run_issue_620_tests.py --phase validation
    python tests/issue_620/run_issue_620_tests.py --phase websocket

Business Impact: Validates $500K+ ARR protection during critical SSOT migration.
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.issue_620.test_utilities import MigrationProgressTracker
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class Issue620TestRunner:
    """Test runner for Issue #620 SSOT migration validation."""
    
    def __init__(self):
        self.progress_tracker = MigrationProgressTracker()
        self.test_phases = {
            "reproduction": {
                "name": "Reproduction Tests (MUST FAIL before migration)",
                "description": "Demonstrate SSOT violations and security issues",
                "tests": [
                    "test_ssot_namespace_conflicts.py",
                    "test_user_context_contamination.py"
                ],
                "expected_before_migration": "FAIL",
                "expected_after_migration": "PASS"
            },
            "golden-path": {
                "name": "Golden Path Protection (MUST ALWAYS PASS)",
                "description": "Protect core business value during migration",
                "tests": [
                    "test_golden_path_protection.py"
                ],
                "expected_before_migration": "PASS",
                "expected_after_migration": "PASS"
            },
            "websocket": {
                "name": "WebSocket Event Integrity (MUST ALWAYS PASS)",
                "description": "Ensure real-time events work during migration",
                "tests": [
                    "test_websocket_event_integrity.py"
                ],
                "expected_before_migration": "PASS",
                "expected_after_migration": "PASS"
            },
            "validation": {
                "name": "Migration Validation (MUST PASS after migration)",
                "description": "Validate successful SSOT consolidation",
                "tests": [
                    "test_ssot_migration_validation.py"
                ],
                "expected_before_migration": "FAIL",
                "expected_after_migration": "PASS"
            }
        }
    
    def run_tests(self, phases: List[str], verbose: bool = False, 
                  fail_fast: bool = False, coverage: bool = False) -> Dict[str, Any]:
        """Run tests for specified phases.
        
        Args:
            phases: List of test phases to run ("all" for all phases)
            verbose: Enable verbose output
            fail_fast: Stop on first failure
            coverage: Generate coverage report
            
        Returns:
            Test results summary
        """
        logger.info("🚀 Starting Issue #620 SSOT ExecutionEngine Migration Test Suite")
        logger.info(f"Test phases: {phases}")
        
        if "all" in phases:
            phases = list(self.test_phases.keys())
        
        results = {
            "phases_run": [],
            "total_tests": 0,
            "total_passed": 0,
            "total_failed": 0,
            "phase_results": {},
            "overall_success": True,
            "migration_status": None
        }
        
        # Run each phase
        for phase in phases:
            if phase not in self.test_phases:
                logger.error(f"Unknown test phase: {phase}")
                continue
                
            logger.info(f"\n📋 Running {self.test_phases[phase]['name']}")
            logger.info(f"   {self.test_phases[phase]['description']}")
            
            phase_result = self._run_phase(phase, verbose, fail_fast, coverage)
            results["phase_results"][phase] = phase_result
            results["phases_run"].append(phase)
            
            # Update totals
            results["total_tests"] += phase_result["tests_run"]
            results["total_passed"] += phase_result["tests_passed"]
            results["total_failed"] += phase_result["tests_failed"]
            
            if not phase_result["success"]:
                results["overall_success"] = False
                
                if fail_fast:
                    logger.error(f"💥 Stopping due to failure in {phase} phase")
                    break
        
        # Get migration status
        results["migration_status"] = self.progress_tracker.get_migration_status()
        
        # Generate summary report
        self._generate_summary_report(results)
        
        return results
    
    def _run_phase(self, phase: str, verbose: bool, fail_fast: bool, coverage: bool) -> Dict[str, Any]:
        """Run a single test phase."""
        phase_info = self.test_phases[phase]
        tests = phase_info["tests"]
        
        phase_result = {
            "phase": phase,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "test_results": [],
            "success": True,
            "duration": 0.0
        }
        
        start_time = time.time()
        
        for test_file in tests:
            logger.info(f"   🧪 Running {test_file}")
            
            test_result = self._run_single_test(test_file, phase, verbose, coverage)
            phase_result["test_results"].append(test_result)
            phase_result["tests_run"] += 1
            
            if test_result["passed"]:
                phase_result["tests_passed"] += 1
                logger.info(f"   ✅ {test_file} - PASSED")
            else:
                phase_result["tests_failed"] += 1
                phase_result["success"] = False
                logger.error(f"   ❌ {test_file} - FAILED")
                
                if fail_fast:
                    break
        
        phase_result["duration"] = time.time() - start_time
        
        # Log phase summary
        self._log_phase_summary(phase, phase_result)
        
        return phase_result
    
    def _run_single_test(self, test_file: str, phase: str, verbose: bool, coverage: bool) -> Dict[str, Any]:
        """Run a single test file."""
        test_path = Path(__file__).parent / test_file
        
        # Build pytest command
        cmd = ["python", "-m", "pytest", str(test_path)]
        
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        cmd.extend(["--tb=short"])
        
        # Add coverage if requested
        if coverage:
            cmd.extend([
                "--cov=netra_backend.app.agents.supervisor",
                "--cov-append"
            ])
        
        # Add non-docker marker to skip docker tests
        cmd.extend(["-m", "not docker"])
        
        test_result = {
            "test_file": test_file,
            "phase": phase,
            "passed": False,
            "duration": 0.0,
            "output": "",
            "error": ""
        }
        
        try:
            start_time = time.time()
            
            # Run the test
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test file
            )
            
            test_result["duration"] = time.time() - start_time
            test_result["passed"] = result.returncode == 0
            test_result["output"] = result.stdout
            test_result["error"] = result.stderr
            
            # Record result with progress tracker
            self.progress_tracker.record_test_result(
                test_name=test_file,
                passed=test_result["passed"],
                test_type=phase,
                details={"duration": test_result["duration"]}
            )
            
        except subprocess.TimeoutExpired:
            test_result["error"] = f"Test {test_file} timed out after 300 seconds"
            test_result["duration"] = 300.0
            logger.error(f"   ⏰ {test_file} - TIMEOUT")
            
        except Exception as e:
            test_result["error"] = f"Failed to run test {test_file}: {e}"
            logger.error(f"   💥 {test_file} - ERROR: {e}")
        
        return test_result
    
    def _log_phase_summary(self, phase: str, phase_result: Dict[str, Any]):
        """Log phase summary."""
        phase_info = self.test_phases[phase]
        
        if phase_result["success"]:
            logger.info(f"   ✅ {phase_info['name']} - ALL TESTS PASSED")
        else:
            logger.error(f"   ❌ {phase_info['name']} - {phase_result['tests_failed']} TESTS FAILED")
        
        logger.info(f"   📊 Tests: {phase_result['tests_passed']}/{phase_result['tests_run']} passed")
        logger.info(f"   ⏱️  Duration: {phase_result['duration']:.2f}s")
        
        # Add phase-specific guidance
        if phase == "reproduction":
            if phase_result["success"]:
                logger.warning("   ⚠️  REPRODUCTION TESTS PASSED - This may indicate migration already complete")
            else:
                logger.info("   ✅ REPRODUCTION TESTS FAILED - This demonstrates the issue exists (expected)")
        
        elif phase == "golden-path":
            if not phase_result["success"]:
                logger.error("   🚨 GOLDEN PATH FAILURE - CRITICAL: Core business value at risk!")
        
        elif phase == "websocket":
            if not phase_result["success"]:
                logger.error("   🚨 WEBSOCKET FAILURE - CRITICAL: Real-time chat experience broken!")
        
        elif phase == "validation":
            if phase_result["success"]:
                logger.info("   ✅ MIGRATION VALIDATION PASSED - SSOT migration successful")
            else:
                logger.warning("   ⚠️  MIGRATION VALIDATION FAILED - Migration incomplete or issues exist")
    
    def _generate_summary_report(self, results: Dict[str, Any]):
        """Generate comprehensive summary report."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 ISSUE #620 SSOT MIGRATION TEST RESULTS SUMMARY")
        logger.info("=" * 80)
        
        # Overall results
        logger.info(f"🎯 Overall Result: {'✅ SUCCESS' if results['overall_success'] else '❌ FAILED'}")
        logger.info(f"📋 Phases Run: {', '.join(results['phases_run'])}")
        logger.info(f"🧪 Total Tests: {results['total_passed']}/{results['total_tests']} passed")
        
        if results['total_failed'] > 0:
            logger.error(f"💥 Failed Tests: {results['total_failed']}")
        
        # Migration status
        migration_status = results["migration_status"]
        logger.info("\n🔄 MIGRATION STATUS:")
        logger.info(f"   SSOT Compliance: {'✅' if migration_status['ssot_compliance'] else '❌'}")
        logger.info(f"   User Isolation: {'✅' if migration_status['user_isolation'] else '❌'}")
        logger.info(f"   WebSocket Integrity: {'✅' if migration_status['websocket_integrity'] else '❌'}")
        logger.info(f"   Golden Path Protected: {'✅' if migration_status['golden_path_protected'] else '❌'}")
        logger.info(f"   Migration Ready: {'✅' if migration_status['migration_ready'] else '❌'}")
        
        # Business impact assessment
        logger.info("\n💰 BUSINESS IMPACT ASSESSMENT:")
        if migration_status['golden_path_protected']:
            logger.info("   ✅ $500K+ ARR PROTECTED - Core chat functionality working")
        else:
            logger.error("   🚨 $500K+ ARR AT RISK - Core chat functionality compromised")
        
        if migration_status['user_isolation']:
            logger.info("   ✅ USER DATA SECURE - No contamination between sessions")
        else:
            logger.error("   🚨 SECURITY VULNERABILITY - User data contamination detected")
        
        if migration_status['websocket_integrity']:
            logger.info("   ✅ REAL-TIME CHAT WORKING - WebSocket events delivered correctly")
        else:
            logger.error("   🚨 CHAT EXPERIENCE DEGRADED - WebSocket event delivery issues")
        
        # Phase-specific results
        logger.info("\n📋 PHASE RESULTS:")
        for phase, phase_result in results["phase_results"].items():
            phase_info = self.test_phases[phase]
            status = "✅ PASS" if phase_result["success"] else "❌ FAIL"
            logger.info(f"   {status} {phase_info['name']}")
            logger.info(f"        Tests: {phase_result['tests_passed']}/{phase_result['tests_run']} passed")
            logger.info(f"        Duration: {phase_result['duration']:.2f}s")
        
        # Recommendations
        logger.info("\n📝 RECOMMENDATIONS:")
        if not migration_status['migration_ready']:
            logger.info("   🔧 Migration not yet complete - address failing tests before proceeding")
        
        if not migration_status['golden_path_protected']:
            logger.error("   🚨 URGENT: Fix golden path tests immediately - business value at risk")
        
        if not migration_status['ssot_compliance']:
            logger.info("   📦 Complete SSOT migration - eliminate remaining duplicate implementations")
        
        if not migration_status['user_isolation']:
            logger.error("   🔒 SECURITY: Fix user isolation issues - data contamination vulnerability")
        
        if not migration_status['websocket_integrity']:
            logger.error("   📡 CHAT: Fix WebSocket event delivery - user experience impact")
        
        logger.info("=" * 80)
    
    def check_migration_state(self) -> str:
        """Check current migration state.
        
        Returns:
            Migration state: "pre-migration", "during-migration", or "post-migration"
        """
        logger.info("🔍 Checking current migration state...")
        
        # Check if UserExecutionEngine is available
        user_execution_engine_available = False
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            user_execution_engine_available = True
            logger.info("   ✅ UserExecutionEngine available")
        except ImportError:
            logger.info("   ❌ UserExecutionEngine not available")
        
        # Check if deprecated ExecutionEngine is available
        execution_engine_available = False
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            execution_engine_available = True
            logger.info("   ✅ ExecutionEngine available")
        except ImportError:
            logger.info("   ❌ ExecutionEngine not available")
        
        # Determine migration state
        if user_execution_engine_available and not execution_engine_available:
            state = "post-migration"
            logger.info("   📊 Migration State: POST-MIGRATION (UserExecutionEngine only)")
        elif user_execution_engine_available and execution_engine_available:
            state = "during-migration"
            logger.info("   📊 Migration State: DURING-MIGRATION (Both implementations)")
        elif not user_execution_engine_available and execution_engine_available:
            state = "pre-migration"
            logger.info("   📊 Migration State: PRE-MIGRATION (ExecutionEngine only)")
        else:
            state = "unknown"
            logger.error("   📊 Migration State: UNKNOWN (No implementations found)")
        
        return state


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Issue #620 SSOT ExecutionEngine Migration Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Phases:
  reproduction    - Tests that MUST FAIL before migration (demonstrate issues)
  golden-path     - Tests that MUST ALWAYS PASS (protect business value)
  websocket      - Tests that MUST ALWAYS PASS (protect real-time chat)
  validation     - Tests that MUST PASS after migration (validate fixes)
  all            - Run all phases

Examples:
  python tests/issue_620/run_issue_620_tests.py --phase all
  python tests/issue_620/run_issue_620_tests.py --phase golden-path --verbose
  python tests/issue_620/run_issue_620_tests.py --phase reproduction validation
        """
    )
    
    parser.add_argument(
        "--phase",
        nargs="+",
        choices=["reproduction", "golden-path", "websocket", "validation", "all"],
        default=["all"],
        help="Test phases to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--check-state",
        action="store_true",
        help="Check migration state only (don't run tests)"
    )
    
    args = parser.parse_args()
    
    runner = Issue620TestRunner()
    
    if args.check_state:
        # Just check migration state
        state = runner.check_migration_state()
        print(f"Migration State: {state}")
        return 0
    
    # Run tests
    results = runner.run_tests(
        phases=args.phase,
        verbose=args.verbose,
        fail_fast=args.fail_fast,
        coverage=args.coverage
    )
    
    # Return appropriate exit code
    return 0 if results["overall_success"] else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)