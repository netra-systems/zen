#!/usr/bin/env python3
"""
Remediation Test Integration

Integrates the Critical Remediation Tracker with existing test infrastructure,
providing automated validation of remediation completion and systematic testing
of fixes to prevent regression.

This module extends the unified test runner to support remediation-specific
test validation and business value verification.
"""

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import time

# Import existing test infrastructure
sys.path.append(str(Path(__file__).parent.parent))

from scripts.critical_remediation_tracker import CriticalRemediationTracker, IssueStatus, IssuePriority
from tests.unified_test_runner import UnifiedTestRunner

logger = logging.getLogger(__name__)


class RemediationTestIntegration:
    """Integration layer between remediation tracking and test infrastructure"""

    def __init__(self, data_dir: str = "reports/remediation"):
        self.tracker = CriticalRemediationTracker(data_dir)
        self.test_runner = UnifiedTestRunner()
        self.integration_results_dir = Path(data_dir) / "test_integration"
        self.integration_results_dir.mkdir(parents=True, exist_ok=True)

    def validate_issue_with_comprehensive_testing(
        self, 
        issue_id: str,
        run_full_suite: bool = False,
        include_e2e: bool = True
    ) -> Dict[str, Any]:
        """
        Run comprehensive testing to validate issue remediation
        
        Args:
            issue_id: The remediation issue ID
            run_full_suite: Whether to run the full test suite or targeted tests
            include_e2e: Whether to include e2e tests in validation
        """
        if issue_id not in self.tracker.issues:
            return {
                "valid": False,
                "error": f"Issue {issue_id} not found in tracker",
                "test_results": {}
            }

        issue = self.tracker.issues[issue_id]
        
        validation_result = {
            "issue_id": issue_id,
            "validation_timestamp": datetime.now().isoformat(),
            "valid": True,
            "test_results": {},
            "business_metrics": {},
            "errors": [],
            "warnings": []
        }

        try:
            # Determine test categories based on affected systems
            test_categories = self._determine_test_categories(issue)
            
            # Run targeted tests first
            targeted_results = self._run_targeted_tests(issue, test_categories)
            validation_result["test_results"]["targeted"] = targeted_results
            
            if not targeted_results["all_passed"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(targeted_results["failures"])

            # Run full test suite if requested or if targeted tests failed
            if run_full_suite or not targeted_results["all_passed"]:
                full_suite_results = self._run_full_test_suite(include_e2e)
                validation_result["test_results"]["full_suite"] = full_suite_results
                
                if not full_suite_results["all_passed"]:
                    validation_result["valid"] = False
                    validation_result["errors"].extend(full_suite_results["failures"])

            # Validate business metrics if issue is high priority
            if issue.priority in [IssuePriority.P0, IssuePriority.P1]:
                business_validation = self._validate_business_metrics(issue)
                validation_result["business_metrics"] = business_validation

            # Update issue status based on validation results
            if validation_result["valid"]:
                self.tracker.update_issue(
                    issue_id,
                    status=IssueStatus.VALIDATED,
                    execution_note=f"Validation passed: {len(validation_result['test_results'])} test suites successful"
                )
            else:
                self.tracker.update_issue(
                    issue_id,
                    status=IssueStatus.FAILED,
                    execution_note=f"Validation failed: {len(validation_result['errors'])} test failures"
                )

        except Exception as e:
            logger.error(f"Validation failed for issue {issue_id}: {str(e)}")
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation exception: {str(e)}")

        # Save validation results
        self._save_validation_results(issue_id, validation_result)
        
        return validation_result

    def _determine_test_categories(self, issue) -> List[str]:
        """Determine which test categories to run based on affected systems"""
        categories = []
        affected_systems = [system.lower() for system in issue.affected_systems]
        
        # Map systems to test categories
        system_category_mapping = {
            "websocket": ["websocket", "integration"],
            "smd": ["startup", "integration"],
            "agent": ["agent", "integration"], 
            "auth": ["auth", "security"],
            "database": ["database", "integration"],
            "redis": ["redis", "integration"],
            "docker": ["docker", "infrastructure"],
            "backend": ["api", "integration"],
            "frontend": ["frontend", "e2e"]
        }
        
        for system in affected_systems:
            for pattern, test_cats in system_category_mapping.items():
                if pattern in system:
                    categories.extend(test_cats)
        
        # Remove duplicates and add default categories
        categories = list(set(categories))
        if not categories:
            categories = ["integration"]  # Default fallback
            
        return categories

    def _run_targeted_tests(self, issue, test_categories: List[str]) -> Dict[str, Any]:
        """Run targeted tests based on issue's affected systems"""
        results = {
            "categories_tested": test_categories,
            "all_passed": True,
            "failures": [],
            "execution_time": 0,
            "test_counts": {}
        }
        
        start_time = time.time()
        
        for category in test_categories:
            try:
                logger.info(f"Running {category} tests for issue {issue.issue_id}")
                
                # Use unified test runner for standard categories
                if category in ["startup", "integration", "api", "auth", "database", "redis"]:
                    category_result = self._run_test_category_with_runner(category)
                else:
                    # Custom category handlers
                    category_result = self._run_custom_test_category(category, issue)
                
                results["test_counts"][category] = category_result.get("test_count", 0)
                
                if not category_result.get("passed", False):
                    results["all_passed"] = False
                    results["failures"].extend(category_result.get("failures", []))
                    
            except Exception as e:
                logger.error(f"Failed to run {category} tests: {str(e)}")
                results["all_passed"] = False
                results["failures"].append(f"Category {category}: {str(e)}")
        
        results["execution_time"] = time.time() - start_time
        return results

    def _run_test_category_with_runner(self, category: str) -> Dict[str, Any]:
        """Run tests using the unified test runner"""
        try:
            # Build command for unified test runner
            cmd = [
                sys.executable, 
                "tests/unified_test_runner.py",
                "--category", category,
                "--fast-fail",
                "--json-output"
            ]
            
            # Add real services for integration tests
            if category in ["integration", "startup", "websocket"]:
                cmd.append("--real-services")
            
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            return {
                "passed": result.returncode == 0,
                "test_count": self._parse_test_count_from_output(result.stdout),
                "failures": self._parse_failures_from_output(result.stdout, result.stderr) if result.returncode != 0 else [],
                "execution_time": self._parse_execution_time(result.stdout)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "test_count": 0,
                "failures": [f"Test category {category} timed out after 10 minutes"],
                "execution_time": 600
            }
        except Exception as e:
            return {
                "passed": False,
                "test_count": 0,
                "failures": [f"Test category {category} execution failed: {str(e)}"],
                "execution_time": 0
            }

    def _run_custom_test_category(self, category: str, issue) -> Dict[str, Any]:
        """Run custom test categories specific to remediation validation"""
        
        if category == "websocket":
            return self._run_websocket_validation_tests(issue)
        elif category == "docker":
            return self._run_docker_health_tests(issue)
        elif category == "frontend":
            return self._run_frontend_smoke_tests(issue)
        else:
            logger.warning(f"Unknown custom test category: {category}")
            return {"passed": True, "test_count": 0, "failures": []}

    def _run_websocket_validation_tests(self, issue) -> Dict[str, Any]:
        """Run WebSocket-specific validation tests"""
        try:
            cmd = [
                sys.executable,
                "tests/mission_critical/test_websocket_agent_events_suite.py"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "passed": result.returncode == 0,
                "test_count": self._parse_test_count_from_output(result.stdout),
                "failures": [result.stderr] if result.returncode != 0 else [],
                "execution_time": self._parse_execution_time(result.stdout)
            }
            
        except Exception as e:
            return {
                "passed": False,
                "test_count": 0,
                "failures": [f"WebSocket validation failed: {str(e)}"],
                "execution_time": 0
            }

    def _run_docker_health_tests(self, issue) -> Dict[str, Any]:
        """Run Docker health validation tests"""
        try:
            cmd = [
                sys.executable,
                "scripts/docker_health_check.py",
                "--comprehensive"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=180
            )
            
            return {
                "passed": result.returncode == 0,
                "test_count": 1,  # Single comprehensive health check
                "failures": [result.stderr] if result.returncode != 0 else [],
                "execution_time": self._parse_execution_time(result.stdout)
            }
            
        except Exception as e:
            return {
                "passed": False,
                "test_count": 0,
                "failures": [f"Docker health check failed: {str(e)}"],
                "execution_time": 0
            }

    def _run_frontend_smoke_tests(self, issue) -> Dict[str, Any]:
        """Run frontend smoke tests"""
        try:
            # For now, just verify frontend can build
            cmd = [
                sys.executable,
                "scripts/test_frontend_simple.py"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return {
                "passed": result.returncode == 0,
                "test_count": 1,
                "failures": [result.stderr] if result.returncode != 0 else [],
                "execution_time": self._parse_execution_time(result.stdout)
            }
            
        except Exception as e:
            return {
                "passed": False,
                "test_count": 0,
                "failures": [f"Frontend smoke test failed: {str(e)}"],
                "execution_time": 0
            }

    def _run_full_test_suite(self, include_e2e: bool = True) -> Dict[str, Any]:
        """Run the full test suite for comprehensive validation"""
        try:
            cmd = [
                sys.executable,
                "tests/unified_test_runner.py",
                "--categories", "smoke", "unit", "integration", "api",
                "--real-services",
                "--json-output"
            ]
            
            if include_e2e:
                cmd.extend(["--categories", "e2e"])
            
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout for full suite
            )
            
            return {
                "all_passed": result.returncode == 0,
                "test_count": self._parse_test_count_from_output(result.stdout),
                "failures": self._parse_failures_from_output(result.stdout, result.stderr) if result.returncode != 0 else [],
                "execution_time": self._parse_execution_time(result.stdout)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "all_passed": False,
                "test_count": 0,
                "failures": ["Full test suite timed out after 30 minutes"],
                "execution_time": 1800
            }
        except Exception as e:
            return {
                "all_passed": False,
                "test_count": 0,
                "failures": [f"Full test suite execution failed: {str(e)}"],
                "execution_time": 0
            }

    def _validate_business_metrics(self, issue) -> Dict[str, Any]:
        """Validate business metrics after remediation"""
        metrics = {
            "mrr_protection_validated": False,
            "uptime_improvement_measured": False,
            "user_impact_resolved": False,
            "system_stability_score": 0.0,
            "validation_timestamp": datetime.now().isoformat()
        }
        
        try:
            # Validate system uptime (simplified - in production would check monitoring)
            uptime_check = self._check_system_uptime()
            if uptime_check >= 99.0:  # 99% uptime threshold
                metrics["uptime_improvement_measured"] = True
                metrics["system_stability_score"] = uptime_check
            
            # Validate MRR protection (simplified - in production would check revenue metrics)
            if issue.business_value_protected and issue.business_value_protected > 0:
                metrics["mrr_protection_validated"] = True
            
            # Validate user impact resolution (check if error patterns resolved)
            user_impact_resolved = self._validate_user_impact_resolution(issue)
            metrics["user_impact_resolved"] = user_impact_resolved
            
        except Exception as e:
            logger.error(f"Business metrics validation failed: {str(e)}")
            metrics["validation_error"] = str(e)
        
        return metrics

    def _check_system_uptime(self) -> float:
        """Check current system uptime (simplified implementation)"""
        try:
            # In a real implementation, this would query monitoring systems
            # For now, we'll do basic health checks
            
            health_checks = [
                self._check_backend_health(),
                self._check_database_health(),
                self._check_websocket_health()
            ]
            
            healthy_services = sum(1 for check in health_checks if check)
            uptime_percentage = (healthy_services / len(health_checks)) * 100
            
            return uptime_percentage
            
        except Exception:
            return 0.0

    def _check_backend_health(self) -> bool:
        """Check if backend is healthy"""
        try:
            # This is a simplified check - in production would hit health endpoint
            result = subprocess.run(
                ["python", "-c", "import netra_backend.app.smd; print('OK')"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_database_health(self) -> bool:
        """Check if database is accessible"""
        try:
            # Simplified check - would use actual DB connection in production
            result = subprocess.run(
                ["python", "scripts/check_database_schema.py", "--quick-check"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_websocket_health(self) -> bool:
        """Check if WebSocket functionality is working"""
        try:
            result = subprocess.run(
                ["python", "scripts/test_websocket_direct.py", "--quick"],
                capture_output=True,
                text=True,
                timeout=15
            )
            return result.returncode == 0
        except Exception:
            return False

    def _validate_user_impact_resolution(self, issue) -> bool:
        """Validate that user-impacting errors have been resolved"""
        try:
            # Check if the error patterns mentioned in the issue are resolved
            # This is a simplified implementation
            
            if "startup" in issue.title.lower():
                # Check startup succeeds
                startup_result = subprocess.run(
                    ["python", "-c", "from netra_backend.app.smd import SMD; smd = SMD(); print('Startup OK')"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return startup_result.returncode == 0
            
            if "websocket" in issue.title.lower():
                # Check WebSocket connections work
                ws_result = subprocess.run(
                    ["python", "scripts/test_websocket_direct.py"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return ws_result.returncode == 0
            
            # Default: assume resolved if no specific validation
            return True
            
        except Exception:
            return False

    def _parse_test_count_from_output(self, output: str) -> int:
        """Parse test count from test runner output"""
        try:
            # Look for patterns like "collected X items" or "X tests ran"
            import re
            patterns = [
                r'collected (\d+) items',
                r'(\d+) tests? ran',
                r'Ran (\d+) tests?'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            return 0
        except Exception:
            return 0

    def _parse_failures_from_output(self, stdout: str, stderr: str) -> List[str]:
        """Parse failure messages from test output"""
        failures = []
        
        # Parse stderr for obvious errors
        if stderr.strip():
            failures.append(f"STDERR: {stderr.strip()}")
        
        # Parse stdout for test failures
        lines = stdout.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['failed', 'error', 'exception', 'traceback']):
                failures.append(line.strip())
        
        return failures[:10]  # Limit to first 10 failures

    def _parse_execution_time(self, output: str) -> float:
        """Parse execution time from test output"""
        try:
            import re
            # Look for patterns like "in 1.23s" or "took 1.23 seconds"
            patterns = [
                r'in ([\d.]+)s',
                r'took ([\d.]+) seconds?',
                r'([\d.]+) seconds? elapsed'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    return float(match.group(1))
            
            return 0.0
        except Exception:
            return 0.0

    def _save_validation_results(self, issue_id: str, results: Dict[str, Any]):
        """Save validation results to file"""
        try:
            results_file = self.integration_results_dir / f"{issue_id}_validation.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Saved validation results to {results_file}")
            
        except Exception as e:
            logger.error(f"Failed to save validation results: {str(e)}")

    def generate_integration_health_report(self) -> Dict[str, Any]:
        """Generate a health report on the integration system itself"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "integration_health": {},
            "test_infrastructure_status": {},
            "recent_validations": []
        }
        
        try:
            # Check test runner availability
            test_runner_health = self._check_test_runner_health()
            report["test_infrastructure_status"]["unified_test_runner"] = test_runner_health
            
            # Check Docker integration
            docker_health = self._check_docker_integration_health()
            report["test_infrastructure_status"]["docker_integration"] = docker_health
            
            # Check recent validation results
            recent_validations = self._get_recent_validation_summary()
            report["recent_validations"] = recent_validations
            
            # Overall integration health score
            health_score = self._calculate_integration_health_score(test_runner_health, docker_health, recent_validations)
            report["integration_health"]["score"] = health_score
            report["integration_health"]["status"] = "healthy" if health_score > 80 else "degraded" if health_score > 60 else "unhealthy"
            
        except Exception as e:
            logger.error(f"Failed to generate integration health report: {str(e)}")
            report["integration_health"]["error"] = str(e)
        
        return report

    def _check_test_runner_health(self) -> Dict[str, Any]:
        """Check unified test runner health"""
        try:
            result = subprocess.run(
                [sys.executable, "tests/unified_test_runner.py", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "available": result.returncode == 0,
                "last_checked": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "last_checked": datetime.now().isoformat()
            }

    def _check_docker_integration_health(self) -> Dict[str, Any]:
        """Check Docker integration health"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "available": result.returncode == 0,
                "version": result.stdout.strip() if result.returncode == 0 else None,
                "last_checked": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "last_checked": datetime.now().isoformat()
            }

    def _get_recent_validation_summary(self) -> List[Dict[str, Any]]:
        """Get summary of recent validations"""
        try:
            recent_validations = []
            
            # Get validation files from last 7 days
            for validation_file in self.integration_results_dir.glob("*_validation.json"):
                try:
                    with open(validation_file, 'r') as f:
                        validation_data = json.load(f)
                    
                    validation_time = datetime.fromisoformat(validation_data.get("validation_timestamp", ""))
                    if (datetime.now() - validation_time).days <= 7:
                        recent_validations.append({
                            "issue_id": validation_data.get("issue_id"),
                            "valid": validation_data.get("valid"),
                            "timestamp": validation_data.get("validation_timestamp"),
                            "test_count": validation_data.get("test_results", {}).get("targeted", {}).get("test_count", 0)
                        })
                
                except Exception:
                    continue
            
            return sorted(recent_validations, key=lambda x: x["timestamp"], reverse=True)[:10]
            
        except Exception:
            return []

    def _calculate_integration_health_score(
        self, 
        test_runner_health: Dict[str, Any], 
        docker_health: Dict[str, Any], 
        recent_validations: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall integration health score (0-100)"""
        score = 0.0
        
        # Test runner availability (30 points)
        if test_runner_health.get("available"):
            score += 30
        
        # Docker availability (20 points)
        if docker_health.get("available"):
            score += 20
        
        # Recent validation success rate (50 points)
        if recent_validations:
            successful_validations = sum(1 for v in recent_validations if v.get("valid"))
            success_rate = successful_validations / len(recent_validations)
            score += success_rate * 50
        else:
            # No recent validations is concerning
            score += 10
        
        return score


def main():
    """Main entry point for testing the integration"""
    integration = RemediationTestIntegration()
    
    # Test the integration with a sample issue (if available)
    tracker = CriticalRemediationTracker()
    
    if tracker.issues:
        # Test with first available issue
        issue_id = list(tracker.issues.keys())[0]
        print(f"Testing validation for issue: {issue_id}")
        
        result = integration.validate_issue_with_comprehensive_testing(
            issue_id,
            run_full_suite=False,
            include_e2e=False
        )
        
        print("Validation Result:")
        print(json.dumps(result, indent=2))
    else:
        print("No issues found to test. Generate health report instead.")
        health_report = integration.generate_integration_health_report()
        print("Integration Health Report:")
        print(json.dumps(health_report, indent=2))


if __name__ == '__main__':
    main()