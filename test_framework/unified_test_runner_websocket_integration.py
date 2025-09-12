#!/usr/bin/env python
"""UNIFIED TEST RUNNER - WEBSOCKET DEPLOYMENT INTEGRATION

Extends the unified test runner with comprehensive WebSocket deployment validation.
Provides pre/post deployment hooks for WebSocket testing and monitoring.

Business Value: Ensures $180K+ MRR chat functionality remains stable after deployments
Integration: Seamlessly hooks into existing unified test runner workflow
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
from loguru import logger

# Import WebSocket deployment validation components
from test_framework.websocket_deployment_runner import WebSocketDeploymentTestRunner
from test_framework.websocket_monitoring_integration import WebSocketHealthMonitor, WebSocketAlertManager


class WebSocketTestRunnerIntegration:
    """Integration layer for WebSocket testing within unified test runner."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.deployment_runner = WebSocketDeploymentTestRunner(environment)
        self.health_monitor = WebSocketHealthMonitor(environment)
        self.alert_manager = WebSocketAlertManager(environment)
        self.env = get_env()
        
    def should_run_websocket_validation(self, args: argparse.Namespace) -> bool:
        """Determine if WebSocket validation should be run based on test arguments."""
        
        # Always run for staging/production environments
        if args.env in ["staging", "production"]:
            return True
            
        # Run if websocket category is specified
        if hasattr(args, 'category') and args.category == "websocket":
            return True
            
        if hasattr(args, 'categories') and args.categories and "websocket" in args.categories:
            return True
            
        # Run if e2e tests are being executed (they depend on WebSocket)
        if hasattr(args, 'category') and args.category == "e2e":
            return True
            
        if hasattr(args, 'categories') and args.categories and "e2e" in args.categories:
            return True
            
        # Run if explicit WebSocket validation flag is set
        if hasattr(args, 'websocket_validation') and args.websocket_validation:
            return True
            
        # Run if real services are being used (indicates integration testing)
        if hasattr(args, 'real_services') and args.real_services:
            return True
            
        return False
        
    async def run_pre_deployment_websocket_validation(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Run WebSocket validation before main test execution."""
        logger.info(" SEARCH:  Running pre-deployment WebSocket validation...")
        
        try:
            validation_result = await self.deployment_runner.run_pre_deployment_validation()
            
            # Log results
            if validation_result.get("deployment_ready", False):
                logger.success(f" PASS:  Pre-deployment WebSocket validation PASSED ({validation_result.get('success_rate', 0)}%)")
            else:
                logger.error(f" FAIL:  Pre-deployment WebSocket validation FAILED ({validation_result.get('success_rate', 0)}%)")
                
                # If critical WebSocket issues, consider failing early
                if validation_result.get("success_rate", 0) < 70:
                    logger.error("[U+1F6AB] WebSocket validation failure rate too high - consider stopping test execution")
                    
            return validation_result
            
        except Exception as e:
            logger.error(f"Pre-deployment WebSocket validation error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "deployment_ready": False,
                "success_rate": 0.0
            }
            
    async def run_post_deployment_websocket_validation(self, args: argparse.Namespace, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Run WebSocket validation after main test execution."""
        logger.info(" SEARCH:  Running post-deployment WebSocket validation...")
        
        try:
            validation_result = await self.deployment_runner.run_post_deployment_validation()
            
            # Analyze results in context of main test results
            main_test_success = test_results.get("success", False)
            websocket_validation_success = validation_result.get("deployment_healthy", False)
            
            # Combine insights
            if main_test_success and websocket_validation_success:
                logger.success(" PASS:  Both main tests and WebSocket validation PASSED - deployment looks healthy")
            elif main_test_success and not websocket_validation_success:
                logger.warning(" WARNING: [U+FE0F] Main tests passed but WebSocket validation FAILED - potential chat functionality issues")
            elif not main_test_success and websocket_validation_success:
                logger.warning(" WARNING: [U+FE0F] Main tests failed but WebSocket validation PASSED - non-WebSocket issues detected")
            else:
                logger.error(" FAIL:  Both main tests and WebSocket validation FAILED - deployment has serious issues")
                
            return validation_result
            
        except Exception as e:
            logger.error(f"Post-deployment WebSocket validation error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "deployment_healthy": False,
                "success_rate": 0.0
            }
            
    async def run_websocket_regression_check(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Run WebSocket regression tests to prevent known issues."""
        logger.info(" SEARCH:  Running WebSocket regression prevention tests...")
        
        try:
            regression_result = await self.deployment_runner.run_websocket_regression_tests()
            
            if regression_result.get("summary", {}).get("regression_free", False):
                logger.success(" PASS:  WebSocket regression tests PASSED - no known issues detected")
            else:
                logger.error(" FAIL:  WebSocket regression tests FAILED - known issues detected")
                
                # List specific regressions
                failed_tests = [
                    test_name for test_name, result in regression_result.get("tests", {}).items()
                    if result.get("status") != "passed"
                ]
                
                if failed_tests:
                    logger.error(f"   Failed regression tests: {', '.join(failed_tests)}")
                    
            return regression_result
            
        except Exception as e:
            logger.error(f"WebSocket regression check error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "regression_free": False
            }
            
    def create_websocket_deployment_report(self, 
                                         pre_deployment: Optional[Dict[str, Any]],
                                         post_deployment: Optional[Dict[str, Any]], 
                                         regression_check: Optional[Dict[str, Any]],
                                         main_test_results: Dict[str, Any]) -> str:
        """Create comprehensive WebSocket deployment report."""
        
        report_lines = [
            "# WebSocket Deployment Validation Report",
            f"**Generated:** {datetime.utcnow().isoformat()}",
            f"**Environment:** {self.environment}",
            "",
            "## Executive Summary",
            ""
        ]
        
        # Overall status
        overall_success = True
        issues = []
        
        if pre_deployment:
            if not pre_deployment.get("deployment_ready", False):
                overall_success = False
                issues.append(f"Pre-deployment validation failed ({pre_deployment.get('success_rate', 0)}%)")
                
        if post_deployment:
            if not post_deployment.get("deployment_healthy", False):
                overall_success = False
                issues.append(f"Post-deployment validation failed ({post_deployment.get('success_rate', 0)}%)")
                
        if regression_check:
            if not regression_check.get("summary", {}).get("regression_free", False):
                overall_success = False
                issues.append("Regression tests detected known issues")
                
        # Main test results integration
        main_success = main_test_results.get("success", False)
        if not main_success:
            overall_success = False
            issues.append(f"Main test suite failed ({main_test_results.get('failed_tests', 'unknown')} failures)")
            
        # Status summary
        if overall_success:
            report_lines.extend([
                "###  PASS:  DEPLOYMENT VALIDATION PASSED",
                "- All WebSocket functionality is operational",
                "- Chat business value ($180K+ MRR) is protected",
                "- No critical issues detected",
                ""
            ])
        else:
            report_lines.extend([
                "###  FAIL:  DEPLOYMENT VALIDATION FAILED",
                f"- {len(issues)} critical issues detected:",
            ])
            for issue in issues:
                report_lines.append(f"  - {issue}")
            report_lines.extend([
                "- **RECOMMENDATION: Consider deployment rollback**",
                ""
            ])
            
        # Detailed results
        if pre_deployment:
            success_rate = pre_deployment.get("success_rate", 0)
            report_lines.extend([
                "## Pre-Deployment Validation",
                f"- **Success Rate:** {success_rate}%",
                f"- **Status:** {'PASSED' if pre_deployment.get('deployment_ready') else 'FAILED'}",
                f"- **Tests Run:** {len(pre_deployment.get('results', {}).get('tests', {}))}"
            ])
            
            # Failed tests
            failed_tests = {
                name: result for name, result in pre_deployment.get("results", {}).get("tests", {}).items()
                if result.get("status") != "passed"
            }
            if failed_tests:
                report_lines.append("- **Failed Tests:**")
                for test_name, result in failed_tests.items():
                    report_lines.append(f"  - {test_name}: {result.get('error', 'Unknown error')}")
            report_lines.append("")
            
        if post_deployment:
            success_rate = post_deployment.get("success_rate", 0)
            report_lines.extend([
                "## Post-Deployment Validation", 
                f"- **Success Rate:** {success_rate}%",
                f"- **Status:** {'PASSED' if post_deployment.get('deployment_healthy') else 'FAILED'}",
                f"- **Tests Run:** {len(post_deployment.get('results', {}).get('tests', {}))}"
            ])
            
            # Failed tests
            failed_tests = {
                name: result for name, result in post_deployment.get("results", {}).get("tests", {}).items()
                if result.get("status") != "passed"
            }
            if failed_tests:
                report_lines.append("- **Failed Tests:**")
                for test_name, result in failed_tests.items():
                    report_lines.append(f"  - {test_name}: {result.get('error', 'Unknown error')}")
            report_lines.append("")
            
        if regression_check:
            regression_free = regression_check.get("summary", {}).get("regression_free", False)
            total_tests = regression_check.get("summary", {}).get("total_tests", 0)
            passed_tests = regression_check.get("summary", {}).get("passed", 0)
            
            report_lines.extend([
                "## Regression Prevention Tests",
                f"- **Status:** {'PASSED' if regression_free else 'FAILED'}",
                f"- **Tests Passed:** {passed_tests}/{total_tests}",
            ])
            
            failed_regressions = {
                name: result for name, result in regression_check.get("tests", {}).items()
                if result.get("status") != "passed"
            }
            if failed_regressions:
                report_lines.append("- **Detected Regressions:**")
                for test_name, result in failed_regressions.items():
                    report_lines.append(f"  - {test_name}: {result.get('error', 'Regression detected')}")
            report_lines.append("")
            
        # Business impact assessment
        if post_deployment:
            success_rate = post_deployment.get("success_rate", 0)
            mrr_impact = self._estimate_mrr_impact(success_rate)
            
            report_lines.extend([
                "## Business Impact Assessment",
                f"- **Chat Functionality Status:** {self._get_business_impact_status(success_rate)}",
                f"- **Estimated MRR at Risk:** ${mrr_impact:,}",
                f"- **User Impact:** {self._get_user_impact_description(success_rate)}",
                ""
            ])
            
        # Recommendations
        report_lines.extend([
            "## Recommendations",
            ""
        ])
        
        if overall_success:
            report_lines.extend([
                " PASS:  **Deployment approved** - WebSocket functionality is healthy",
                "- Monitor WebSocket health metrics for next 2 hours",
                "- Continue with planned deployment rollout",
                ""
            ])
        else:
            should_rollback, rollback_reason = self._should_recommend_rollback(
                pre_deployment, post_deployment, regression_check
            )
            
            if should_rollback:
                report_lines.extend([
                    " ALERT:  **IMMEDIATE ROLLBACK RECOMMENDED**",
                    f"- Reason: {rollback_reason}",
                    "- Stop deployment rollout immediately",
                    "- Investigate root cause before retry",
                    ""
                ])
            else:
                report_lines.extend([
                    " WARNING: [U+FE0F] **DEPLOYMENT MONITORING REQUIRED**",
                    "- Continue deployment with increased monitoring",
                    "- Prepare rollback plan if issues escalate", 
                    "- Monitor business metrics closely",
                    ""
                ])
                
        return "\n".join(report_lines)
        
    def _estimate_mrr_impact(self, success_rate: float) -> int:
        """Estimate MRR impact based on WebSocket success rate."""
        base_mrr = 180_000  # $180K monthly chat functionality
        
        if success_rate >= 95:
            return 0
        elif success_rate >= 85:
            return int(base_mrr * 0.05)  # 5% impact
        elif success_rate >= 70:
            return int(base_mrr * 0.15)  # 15% impact
        elif success_rate >= 50:
            return int(base_mrr * 0.35)  # 35% impact
        else:
            return int(base_mrr * 0.60)  # 60% impact
            
    def _get_business_impact_status(self, success_rate: float) -> str:
        """Get business impact status description."""
        if success_rate >= 95:
            return " PASS:  Excellent - Full functionality"
        elif success_rate >= 85:
            return " PASS:  Good - Minor issues possible"
        elif success_rate >= 70:
            return " WARNING: [U+FE0F] Degraded - Moderate impact"
        elif success_rate >= 50:
            return " ALERT:  Poor - Significant impact"
        else:
            return " ALERT:  Critical - Major functionality loss"
            
    def _get_user_impact_description(self, success_rate: float) -> str:
        """Get user impact description."""
        if success_rate >= 95:
            return "Minimal - Users experience reliable chat"
        elif success_rate >= 85:
            return "Low - Occasional connection issues"
        elif success_rate >= 70:
            return "Moderate - Noticeable chat disruptions"
        elif success_rate >= 50:
            return "High - Frequent chat failures"
        else:
            return "Severe - Chat largely non-functional"
            
    def _should_recommend_rollback(self, 
                                 pre_deployment: Optional[Dict[str, Any]],
                                 post_deployment: Optional[Dict[str, Any]], 
                                 regression_check: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        """Determine if rollback should be recommended."""
        
        # Critical failure in post-deployment
        if post_deployment and post_deployment.get("success_rate", 0) < 50:
            return True, f"Post-deployment success rate critically low ({post_deployment.get('success_rate', 0)}%)"
            
        # Multiple critical regressions
        if regression_check:
            failed_regressions = len([
                result for result in regression_check.get("tests", {}).values()
                if result.get("status") != "passed"
            ])
            if failed_regressions >= 3:
                return True, f"Multiple critical regressions detected ({failed_regressions})"
                
        # Auth/handshake failures
        if post_deployment:
            tests = post_deployment.get("results", {}).get("tests", {})
            critical_failures = [
                "403_handshake_fix", "jwt_synchronization_fix", "agent_events_business_value"
            ]
            
            for critical_test in critical_failures:
                if critical_test in tests and tests[critical_test].get("status") != "passed":
                    return True, f"Critical test {critical_test} failed: {tests[critical_test].get('error')}"
                    
        return False, "Issues present but below rollback threshold"


def add_websocket_arguments(parser: argparse.ArgumentParser) -> None:
    """Add WebSocket-specific arguments to the unified test runner parser."""
    
    websocket_group = parser.add_argument_group('WebSocket Deployment Validation')
    
    websocket_group.add_argument(
        '--websocket-validation', 
        action='store_true',
        help='Force WebSocket deployment validation regardless of test category'
    )
    
    websocket_group.add_argument(
        '--websocket-pre-only',
        action='store_true', 
        help='Run only pre-deployment WebSocket validation'
    )
    
    websocket_group.add_argument(
        '--websocket-post-only',
        action='store_true',
        help='Run only post-deployment WebSocket validation'
    )
    
    websocket_group.add_argument(
        '--websocket-monitoring',
        type=int,
        metavar='MINUTES',
        help='Run continuous WebSocket health monitoring for specified minutes'
    )
    
    websocket_group.add_argument(
        '--websocket-report',
        type=str,
        metavar='FILE',
        help='Save WebSocket deployment report to file'
    )
    
    websocket_group.add_argument(
        '--skip-websocket-validation',
        action='store_true',
        help='Skip WebSocket validation even for e2e/staging tests'
    )


async def execute_websocket_validation_mode(args: argparse.Namespace) -> int:
    """Execute WebSocket-only validation mode."""
    
    integration = WebSocketTestRunnerIntegration(args.env)
    
    results = {}
    
    try:
        if args.websocket_pre_only:
            logger.info("Running WebSocket pre-deployment validation only...")
            results["pre_deployment"] = await integration.run_pre_deployment_websocket_validation(args)
            
        elif args.websocket_post_only:
            logger.info("Running WebSocket post-deployment validation only...")
            results["post_deployment"] = await integration.run_post_deployment_websocket_validation(args, {})
            
        elif args.websocket_monitoring:
            logger.info(f"Running WebSocket health monitoring for {args.websocket_monitoring} minutes...")
            monitoring_result = await integration.health_monitor.run_monitoring_cycle(args.websocket_monitoring)
            results["monitoring"] = monitoring_result
            
        else:
            # Run full validation suite
            logger.info("Running complete WebSocket deployment validation suite...")
            
            # Pre-deployment validation
            results["pre_deployment"] = await integration.run_pre_deployment_websocket_validation(args)
            
            # Post-deployment validation (simulating deployment occurred)
            results["post_deployment"] = await integration.run_post_deployment_websocket_validation(args, {"success": True})
            
            # Regression check
            results["regression_check"] = await integration.run_websocket_regression_check(args)
            
        # Generate report
        if args.websocket_report:
            report = integration.create_websocket_deployment_report(
                results.get("pre_deployment"),
                results.get("post_deployment"),
                results.get("regression_check"),
                {"success": True}  # Mock main test results
            )
            
            with open(args.websocket_report, 'w') as f:
                f.write(report)
            logger.info(f"WebSocket deployment report saved to {args.websocket_report}")
            
        # Determine exit code
        success = True
        
        if "pre_deployment" in results and not results["pre_deployment"].get("deployment_ready", False):
            success = False
            
        if "post_deployment" in results and not results["post_deployment"].get("deployment_healthy", False):
            success = False
            
        if "regression_check" in results and not results["regression_check"].get("summary", {}).get("regression_free", False):
            success = False
            
        if "monitoring" in results:
            monitoring_healthy = results["monitoring"].get("summary", {}).get("monitoring_healthy", False)
            if not monitoring_healthy:
                success = False
                
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"WebSocket validation mode error: {e}")
        return 1


def integrate_with_main_test_execution(runner_instance, args: argparse.Namespace) -> Dict[str, Any]:
    """Integrate WebSocket validation with main test runner execution."""
    
    # This function would be called from within the main UnifiedTestRunner
    # to add WebSocket validation hooks
    
    integration = WebSocketTestRunnerIntegration(args.env)
    
    # Check if WebSocket validation should run
    if not integration.should_run_websocket_validation(args):
        return {"websocket_validation_skipped": True}
        
    if hasattr(args, 'skip_websocket_validation') and args.skip_websocket_validation:
        return {"websocket_validation_skipped": True}
        
    logger.info("WebSocket deployment validation integrated with test execution")
    
    # Return integration hooks that the main runner can use
    return {
        "websocket_integration": integration,
        "websocket_validation_enabled": True,
        "pre_test_hook": integration.run_pre_deployment_websocket_validation,
        "post_test_hook": integration.run_post_deployment_websocket_validation,
        "regression_hook": integration.run_websocket_regression_check
    }


# ============================================================================
# CLI INTEGRATION ENTRY POINT
# ============================================================================

def main():
    """CLI entry point for standalone WebSocket validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Deployment Validation")
    parser.add_argument("--env", default="staging", choices=["staging", "production", "development"])
    
    # Add WebSocket-specific arguments
    add_websocket_arguments(parser)
    
    args = parser.parse_args()
    
    # Check if any WebSocket-specific mode was requested
    websocket_mode_requested = any([
        args.websocket_pre_only,
        args.websocket_post_only,
        args.websocket_monitoring,
        args.websocket_validation
    ])
    
    if websocket_mode_requested:
        # Run WebSocket validation mode
        exit_code = asyncio.run(execute_websocket_validation_mode(args))
        sys.exit(exit_code)
    else:
        print("Use --websocket-validation, --websocket-pre-only, --websocket-post-only, or --websocket-monitoring")
        print("Or integrate with unified test runner using --websocket-validation flag")
        sys.exit(1)


if __name__ == "__main__":
    main()