#!/usr/bin/env python
"""WEBSOCKET DEPLOYMENT TEST RUNNER

Enhanced test runner with WebSocket deployment validation integration.
Integrates with the unified test runner to provide pre/post deployment validation.

Business Value: Ensures WebSocket deployment fixes are validated before production
Integration: Hooks into CI/CD pipeline for automatic WebSocket regression detection
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
from loguru import logger

# Import WebSocket deployment validation
from tests.websocket_deployment_validation.test_websocket_deployment_suite import (
    WebSocketDeploymentTestSuite,
    WebSocketDeploymentValidator
)

# Import existing test framework components
from test_framework.runner import UnifiedTestRunner as FrameworkRunner
from test_framework.progress_tracker import ProgressTracker, ProgressEvent


class WebSocketDeploymentTestRunner:
    """Enhanced test runner with WebSocket deployment validation."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.env = get_env()
        self.progress_tracker = ProgressTracker()
        
        # WebSocket deployment validation threshold
        self.deployment_threshold = 85  # 85% success rate required for deployment
        
    async def run_pre_deployment_validation(self) -> Dict[str, Any]:
        """Run WebSocket validation before deployment."""
        logger.info("🔍 Running pre-deployment WebSocket validation...")
        
        validation_result = {
            "phase": "pre_deployment",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "status": "pending",
            "results": {}
        }
        
        try:
            # Track progress
            self.progress_tracker.emit_event(ProgressEvent(
                type="websocket_validation_start",
                message="Starting WebSocket pre-deployment validation",
                metadata={"phase": "pre_deployment", "environment": self.environment}
            ))
            
            # Run deployment validation suite
            test_suite = WebSocketDeploymentTestSuite(self.environment)
            results = await test_suite.run_all_validations()
            
            validation_result["results"] = results
            validation_result["success_rate"] = results["summary"]["success_rate"]
            validation_result["deployment_ready"] = results["summary"]["deployment_ready"]
            
            if results["summary"]["deployment_ready"]:
                validation_result["status"] = "passed"
                logger.success(f"✅ Pre-deployment WebSocket validation PASSED ({results['summary']['success_rate']}%)")
            else:
                validation_result["status"] = "failed"
                logger.error(f"❌ Pre-deployment WebSocket validation FAILED ({results['summary']['success_rate']}%)")
                
            self.progress_tracker.emit_event(ProgressEvent(
                type="websocket_validation_complete",
                message=f"WebSocket pre-deployment validation {validation_result['status']}",
                metadata={"success_rate": validation_result["success_rate"]}
            ))
            
        except Exception as e:
            validation_result["status"] = "error"
            validation_result["error"] = str(e)
            logger.error(f"❌ Pre-deployment WebSocket validation error: {e}")
            
            self.progress_tracker.emit_event(ProgressEvent(
                type="websocket_validation_error",
                message=f"WebSocket validation error: {e}",
                metadata={"error": str(e)}
            ))
            
        return validation_result
        
    async def run_post_deployment_validation(self) -> Dict[str, Any]:
        """Run WebSocket validation after deployment."""
        logger.info("🔍 Running post-deployment WebSocket validation...")
        
        validation_result = {
            "phase": "post_deployment", 
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "status": "pending",
            "results": {}
        }
        
        try:
            # Track progress
            self.progress_tracker.emit_event(ProgressEvent(
                type="websocket_validation_start",
                message="Starting WebSocket post-deployment validation",
                metadata={"phase": "post_deployment", "environment": self.environment}
            ))
            
            # Wait brief period for deployment to settle
            await asyncio.sleep(10)
            
            # Run deployment validation suite
            test_suite = WebSocketDeploymentTestSuite(self.environment)
            results = await test_suite.run_all_validations()
            
            validation_result["results"] = results
            validation_result["success_rate"] = results["summary"]["success_rate"]
            validation_result["deployment_healthy"] = results["summary"]["deployment_ready"]
            
            if results["summary"]["deployment_ready"]:
                validation_result["status"] = "passed"
                logger.success(f"✅ Post-deployment WebSocket validation PASSED ({results['summary']['success_rate']}%)")
            else:
                validation_result["status"] = "failed"
                logger.error(f"❌ Post-deployment WebSocket validation FAILED ({results['summary']['success_rate']}%)")
                
            self.progress_tracker.emit_event(ProgressEvent(
                type="websocket_validation_complete",
                message=f"WebSocket post-deployment validation {validation_result['status']}",
                metadata={"success_rate": validation_result["success_rate"]}
            ))
            
        except Exception as e:
            validation_result["status"] = "error"
            validation_result["error"] = str(e)
            logger.error(f"❌ Post-deployment WebSocket validation error: {e}")
            
            self.progress_tracker.emit_event(ProgressEvent(
                type="websocket_validation_error",
                message=f"WebSocket post-deployment validation error: {e}",
                metadata={"error": str(e)}
            ))
            
        return validation_result
        
    async def run_websocket_health_monitoring(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """Run continuous WebSocket health monitoring."""
        logger.info(f"🔍 Running WebSocket health monitoring for {duration_minutes} minutes...")
        
        monitoring_result = {
            "phase": "health_monitoring",
            "duration_minutes": duration_minutes,
            "start_time": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "status": "running",
            "health_checks": []
        }
        
        validator = WebSocketDeploymentValidator(self.environment)
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        healthy_checks = 0
        total_checks = 0
        
        try:
            while time.time() < end_time:
                total_checks += 1
                
                # Run health check
                health_result = await validator.validate_websocket_health_endpoint()
                health_check = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "check_number": total_checks,
                    "status": health_result["status"],
                    "details": health_result.get("details", {})
                }
                
                if health_result["status"] == "passed":
                    healthy_checks += 1
                    health_check["healthy"] = True
                else:
                    health_check["healthy"] = False
                    health_check["error"] = health_result.get("error")
                    
                monitoring_result["health_checks"].append(health_check)
                
                # Log periodic status
                if total_checks % 10 == 0:
                    health_rate = (healthy_checks / total_checks * 100)
                    logger.info(f"📊 WebSocket health monitoring: {health_rate:.1f}% healthy ({healthy_checks}/{total_checks})")
                    
                # Wait before next check (2 minutes between checks)
                await asyncio.sleep(120)
                
        except KeyboardInterrupt:
            logger.info("WebSocket health monitoring stopped by user")
        except Exception as e:
            logger.error(f"WebSocket health monitoring error: {e}")
            monitoring_result["error"] = str(e)
            
        # Final results
        monitoring_result["end_time"] = datetime.utcnow().isoformat()
        monitoring_result["total_checks"] = total_checks
        monitoring_result["healthy_checks"] = healthy_checks
        monitoring_result["health_rate"] = (healthy_checks / total_checks * 100) if total_checks > 0 else 0
        monitoring_result["status"] = "completed"
        
        logger.info(f"📈 WebSocket health monitoring completed: {monitoring_result['health_rate']:.1f}% healthy")
        
        return monitoring_result
        
    async def run_websocket_regression_tests(self) -> Dict[str, Any]:
        """Run WebSocket regression tests to prevent known issues."""
        logger.info("🔍 Running WebSocket regression prevention tests...")
        
        regression_result = {
            "phase": "regression_testing",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "tests": {},
            "summary": {}
        }
        
        try:
            validator = WebSocketDeploymentValidator(self.environment)
            
            # Test known regression scenarios
            regression_tests = {
                "jwt_sync_regression": validator.validate_jwt_synchronization_fix,
                "403_handshake_regression": validator.validate_403_handshake_fix,
                "multi_user_isolation_regression": validator.validate_multi_user_isolation,
                "agent_events_regression": validator.validate_agent_events_business_value
            }
            
            passed_tests = 0
            total_tests = len(regression_tests)
            
            for test_name, test_func in regression_tests.items():
                try:
                    result = await test_func()
                    regression_result["tests"][test_name] = result
                    
                    if result["status"] == "passed":
                        passed_tests += 1
                        logger.success(f"✅ Regression test {test_name} passed")
                    else:
                        logger.error(f"❌ Regression test {test_name} failed: {result.get('error')}")
                        
                except Exception as e:
                    regression_result["tests"][test_name] = {
                        "test": test_name,
                        "status": "error",
                        "error": str(e)
                    }
                    logger.error(f"❌ Regression test {test_name} error: {e}")
                    
            # Summary
            success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            regression_result["summary"] = {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "success_rate": round(success_rate, 1),
                "regression_free": success_rate >= 90  # 90% threshold for regression-free
            }
            
            if regression_result["summary"]["regression_free"]:
                logger.success(f"✅ WebSocket regression tests PASSED: {success_rate}% success rate")
            else:
                logger.error(f"❌ WebSocket regression tests FAILED: {success_rate}% success rate")
                
        except Exception as e:
            regression_result["error"] = str(e)
            regression_result["summary"] = {"regression_free": False}
            logger.error(f"❌ WebSocket regression testing error: {e}")
            
        return regression_result
        
    def should_trigger_rollback(self, post_deployment_result: Dict[str, Any]) -> Tuple[bool, str]:
        """Determine if WebSocket issues should trigger deployment rollback."""
        
        if post_deployment_result.get("status") == "error":
            return True, f"WebSocket deployment validation error: {post_deployment_result.get('error')}"
            
        success_rate = post_deployment_result.get("success_rate", 0)
        
        # Rollback triggers
        if success_rate < 70:
            return True, f"WebSocket success rate too low: {success_rate}% (minimum 70%)"
            
        # Check for critical test failures
        results = post_deployment_result.get("results", {})
        tests = results.get("tests", {})
        
        critical_tests = ["403_handshake_fix", "jwt_synchronization_fix", "agent_events_business_value"]
        
        for test_name in critical_tests:
            test_result = tests.get(test_name, {})
            if test_result.get("status") != "passed":
                return True, f"Critical WebSocket test failed: {test_name} - {test_result.get('error')}"
                
        return False, "WebSocket deployment validation passed"
        
    async def generate_deployment_report(self, 
                                       pre_deployment: Dict[str, Any],
                                       post_deployment: Dict[str, Any],
                                       monitoring: Optional[Dict[str, Any]] = None) -> str:
        """Generate comprehensive WebSocket deployment report."""
        
        report_lines = [
            "# WebSocket Deployment Validation Report",
            f"**Environment:** {self.environment}",
            f"**Timestamp:** {datetime.utcnow().isoformat()}",
            "",
            "## Executive Summary",
            ""
        ]
        
        # Pre-deployment summary
        pre_success = pre_deployment.get("success_rate", 0)
        pre_status = pre_deployment.get("status", "unknown")
        
        report_lines.extend([
            f"### Pre-Deployment Validation",
            f"- **Status:** {pre_status.upper()}",
            f"- **Success Rate:** {pre_success}%",
            f"- **Deployment Ready:** {'✅ Yes' if pre_deployment.get('deployment_ready', False) else '❌ No'}",
            ""
        ])
        
        # Post-deployment summary
        post_success = post_deployment.get("success_rate", 0)
        post_status = post_deployment.get("status", "unknown")
        
        report_lines.extend([
            f"### Post-Deployment Validation",
            f"- **Status:** {post_status.upper()}",
            f"- **Success Rate:** {post_success}%",
            f"- **Deployment Healthy:** {'✅ Yes' if post_deployment.get('deployment_healthy', False) else '❌ No'}",
            ""
        ])
        
        # Rollback recommendation
        should_rollback, rollback_reason = self.should_trigger_rollback(post_deployment)
        
        report_lines.extend([
            f"### Rollback Recommendation",
            f"- **Recommend Rollback:** {'🚨 YES' if should_rollback else '✅ NO'}",
            f"- **Reason:** {rollback_reason}",
            ""
        ])
        
        # Business impact
        if post_success >= 90:
            business_impact = "✅ Minimal impact - Chat functionality stable"
        elif post_success >= 70:
            business_impact = "⚠️  Moderate impact - Some chat issues possible"
        else:
            business_impact = "🚨 High impact - Significant chat functionality issues"
            
        report_lines.extend([
            f"### Business Impact Assessment",
            f"- **Chat Functionality:** {business_impact}",
            f"- **Estimated MRR Impact:** ${self._estimate_mrr_impact(post_success):,}",
            ""
        ])
        
        # Detailed test results
        report_lines.extend([
            "## Detailed Test Results",
            ""
        ])
        
        # Pre-deployment tests
        pre_tests = pre_deployment.get("results", {}).get("tests", {})
        if pre_tests:
            report_lines.append("### Pre-Deployment Tests")
            for test_name, result in pre_tests.items():
                status_emoji = "✅" if result.get("status") == "passed" else "❌"
                report_lines.append(f"- **{test_name}:** {status_emoji} {result.get('status', 'unknown').upper()}")
                if result.get("error"):
                    report_lines.append(f"  - Error: {result['error']}")
            report_lines.append("")
            
        # Post-deployment tests  
        post_tests = post_deployment.get("results", {}).get("tests", {})
        if post_tests:
            report_lines.append("### Post-Deployment Tests")
            for test_name, result in post_tests.items():
                status_emoji = "✅" if result.get("status") == "passed" else "❌"
                report_lines.append(f"- **{test_name}:** {status_emoji} {result.get('status', 'unknown').upper()}")
                if result.get("error"):
                    report_lines.append(f"  - Error: {result['error']}")
            report_lines.append("")
            
        # Health monitoring results
        if monitoring:
            health_rate = monitoring.get("health_rate", 0)
            total_checks = monitoring.get("total_checks", 0)
            
            report_lines.extend([
                "### Health Monitoring",
                f"- **Health Rate:** {health_rate:.1f}%",
                f"- **Total Checks:** {total_checks}",
                f"- **Duration:** {monitoring.get('duration_minutes', 0)} minutes",
                ""
            ])
            
        return "\n".join(report_lines)
        
    def _estimate_mrr_impact(self, success_rate: float) -> int:
        """Estimate MRR impact based on WebSocket success rate."""
        # Base MRR at risk from WebSocket issues (chat functionality)
        base_mrr = 180_000  # $180K monthly chat functionality
        
        if success_rate >= 95:
            return 0  # Minimal impact
        elif success_rate >= 85:
            return int(base_mrr * 0.05)  # 5% impact
        elif success_rate >= 70:
            return int(base_mrr * 0.15)  # 15% impact
        elif success_rate >= 50:
            return int(base_mrr * 0.35)  # 35% impact
        else:
            return int(base_mrr * 0.60)  # 60% impact


# ============================================================================
# CLI INTEGRATION
# ============================================================================

async def main():
    """Main CLI for WebSocket deployment test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Deployment Test Runner")
    parser.add_argument("--environment", default="staging", choices=["staging", "production", "development"])
    parser.add_argument("--phase", choices=["pre", "post", "monitoring", "regression", "full"], 
                       default="full", help="Validation phase to run")
    parser.add_argument("--monitoring-duration", type=int, default=30, help="Health monitoring duration in minutes")
    parser.add_argument("--output-dir", help="Directory to save results")
    
    args = parser.parse_args()
    
    runner = WebSocketDeploymentTestRunner(args.environment)
    
    # Create output directory if specified
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        
    results = {}
    
    try:
        if args.phase in ["pre", "full"]:
            logger.info("Running pre-deployment WebSocket validation...")
            results["pre_deployment"] = await runner.run_pre_deployment_validation()
            
        if args.phase in ["post", "full"]:
            logger.info("Running post-deployment WebSocket validation...")
            results["post_deployment"] = await runner.run_post_deployment_validation()
            
        if args.phase in ["regression", "full"]:
            logger.info("Running WebSocket regression tests...")
            results["regression"] = await runner.run_websocket_regression_tests()
            
        if args.phase == "monitoring":
            logger.info(f"Running WebSocket health monitoring for {args.monitoring_duration} minutes...")
            results["monitoring"] = await runner.run_websocket_health_monitoring(args.monitoring_duration)
            
        # Generate report if we have both pre and post results
        if "pre_deployment" in results and "post_deployment" in results:
            report = await runner.generate_deployment_report(
                results["pre_deployment"],
                results["post_deployment"],
                results.get("monitoring")
            )
            
            if args.output_dir:
                report_file = os.path.join(args.output_dir, "websocket_deployment_report.md")
                with open(report_file, 'w') as f:
                    f.write(report)
                logger.info(f"Deployment report saved to {report_file}")
            else:
                print("\n" + "="*80)
                print(report)
                print("="*80)
                
        # Save results JSON
        if args.output_dir:
            results_file = os.path.join(args.output_dir, "websocket_deployment_results.json")
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {results_file}")
            
        # Exit with appropriate code
        overall_success = all(
            result.get("status") in ["passed", "completed"] or result.get("success_rate", 0) >= 85
            for result in results.values()
        )
        
        if overall_success:
            logger.success("WebSocket deployment validation completed successfully")
            sys.exit(0)
        else:
            logger.error("WebSocket deployment validation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("WebSocket deployment validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"WebSocket deployment validation error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())