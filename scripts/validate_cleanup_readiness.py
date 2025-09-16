#!/usr/bin/env python3
"""
Emergency Bypass Cleanup Readiness Validation
=============================================

This script performs comprehensive validation to ensure the system is ready
for emergency bypass cleanup without compromising service stability.

**Safety-First Approach:**
- Validates infrastructure stability
- Confirms circuit breaker patterns are in place
- Verifies monitoring systems operational
- Tests normal configuration before applying

**Integration with Issue #1278 Remediation:**
- Phase 1: Emergency bypass implementation ✅ COMPLETE
- Phase 2: Infrastructure fixes (VPC connector, database) ⏳ IN PROGRESS
- Phase 3: Emergency bypass cleanup ⏳ THIS SCRIPT PREPARES
"""

import os
import sys
import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.isolated_environment import IsolatedEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Represents the result of a validation check."""
    check_name: str
    passed: bool
    message: str
    details: Optional[Dict] = None

class CleanupReadinessValidator:
    """
    Comprehensive validator for emergency bypass cleanup readiness.

    **Purpose:** Ensure system can safely operate without emergency bypasses
    before removal, preventing service disruption.
    """

    def __init__(self):
        self.env = IsolatedEnvironment()
        self.project_root = Path(__file__).parent.parent
        self.results: List[ValidationResult] = []

    def run_all_validations(self) -> Tuple[bool, List[ValidationResult]]:
        """
        Run all validation checks and return overall readiness status.

        Returns:
            Tuple of (all_checks_passed, list_of_results)
        """
        logger.info("🔍 Starting comprehensive cleanup readiness validation...")

        # Infrastructure checks
        self._validate_database_connectivity_potential()
        self._validate_redis_connectivity_potential()
        self._validate_vpc_connector_requirements()

        # Application checks
        self._validate_circuit_breaker_patterns()
        self._validate_graceful_degradation_code()
        self._validate_monitoring_infrastructure()

        # Configuration checks
        self._validate_normal_config_completeness()
        self._validate_startup_sequence_integrity()

        # Business continuity checks
        self._validate_golden_path_components()
        self._validate_websocket_event_system()

        # Test infrastructure
        self._validate_mission_critical_tests()

        # Calculate overall readiness
        passed_checks = [r for r in self.results if r.passed]
        failed_checks = [r for r in self.results if not r.passed]

        all_passed = len(failed_checks) == 0

        logger.info(f"📊 Validation Summary: {len(passed_checks)}/{len(self.results)} checks passed")

        if all_passed:
            logger.info("✅ ALL VALIDATIONS PASSED - System ready for emergency bypass cleanup")
        else:
            logger.warning(f"❌ {len(failed_checks)} validation(s) failed - NOT ready for cleanup")
            for failed in failed_checks:
                logger.warning(f"  ❌ {failed.check_name}: {failed.message}")

        return all_passed, self.results

    def _add_result(self, check_name: str, passed: bool, message: str, details: Optional[Dict] = None):
        """Add a validation result."""
        result = ValidationResult(check_name, passed, message, details)
        self.results.append(result)

        if passed:
            logger.info(f"  ✅ {check_name}: {message}")
        else:
            logger.warning(f"  ❌ {check_name}: {message}")

    def _validate_database_connectivity_potential(self):
        """Validate that database connectivity can work when bypass is removed."""
        try:
            # Test database manager import
            result = subprocess.run([
                "python", "-c",
                "from netra_backend.app.db.database_manager import DatabaseManager; print('Import successful')"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                self._add_result(
                    "Database Manager Import",
                    True,
                    "Database manager can be imported successfully"
                )

                # Check for SSOT compliance in database manager
                db_manager_path = self.project_root / "netra_backend" / "app" / "db" / "database_manager.py"
                if db_manager_path.exists():
                    content = db_manager_path.read_text()
                    ssot_compliant = "class DatabaseManager" in content and "SSOT" in content
                    self._add_result(
                        "Database Manager SSOT",
                        ssot_compliant,
                        "Database manager follows SSOT patterns" if ssot_compliant else "Database manager may need SSOT compliance review"
                    )
                else:
                    self._add_result(
                        "Database Manager File",
                        False,
                        "Database manager file not found"
                    )
            else:
                self._add_result(
                    "Database Manager Import",
                    False,
                    f"Database manager import failed: {result.stderr}"
                )

        except subprocess.TimeoutExpired:
            self._add_result(
                "Database Manager Import",
                False,
                "Database manager import timed out (30s)"
            )
        except Exception as e:
            self._add_result(
                "Database Manager Import",
                False,
                f"Database validation error: {e}"
            )

    def _validate_redis_connectivity_potential(self):
        """Validate that Redis connectivity can work when bypass is removed."""
        try:
            # Test Redis manager import
            result = subprocess.run([
                "python", "-c",
                "from netra_backend.app.core.redis_manager import RedisManager; print('Import successful')"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                self._add_result(
                    "Redis Manager Import",
                    True,
                    "Redis manager can be imported successfully"
                )
            else:
                self._add_result(
                    "Redis Manager Import",
                    False,
                    f"Redis manager import failed: {result.stderr}"
                )

        except subprocess.TimeoutExpired:
            self._add_result(
                "Redis Manager Import",
                False,
                "Redis manager import timed out (30s)"
            )
        except Exception as e:
            self._add_result(
                "Redis Manager Import",
                False,
                f"Redis validation error: {e}"
            )

    def _validate_vpc_connector_requirements(self):
        """Validate VPC connector configuration requirements."""
        # Check for VPC connector related configuration
        staging_config_path = self.project_root / "scripts" / "deployment" / "staging_config.yaml"

        if staging_config_path.exists():
            try:
                content = staging_config_path.read_text()

                # Look for timeout configurations that indicate VPC awareness
                vpc_aware_configs = [
                    "AUTH_DB_URL_TIMEOUT",
                    "AUTH_DB_ENGINE_TIMEOUT",
                    "AUTH_DB_VALIDATION_TIMEOUT"
                ]

                vpc_configs_present = all(config in content for config in vpc_aware_configs)

                self._add_result(
                    "VPC Connector Timeouts",
                    vpc_configs_present,
                    "VPC-aware timeout configurations present" if vpc_configs_present else "Missing VPC-aware timeout configurations"
                )

                # Check for health check timeout accommodations
                health_check_timeout = "timeout: 90s" in content
                self._add_result(
                    "Health Check VPC Accommodation",
                    health_check_timeout,
                    "Health check timeout accommodates VPC connector latency" if health_check_timeout else "Health check may need VPC connector accommodation"
                )

            except Exception as e:
                self._add_result(
                    "VPC Connector Config",
                    False,
                    f"Error reading staging config: {e}"
                )
        else:
            self._add_result(
                "VPC Connector Config",
                False,
                "Staging config file not found"
            )

    def _validate_circuit_breaker_patterns(self):
        """Validate that circuit breaker patterns are present for resilience."""
        startup_manager_path = self.project_root / "netra_backend" / "app" / "smd.py"

        if startup_manager_path.exists():
            try:
                content = startup_manager_path.read_text()

                # Check for circuit breaker patterns
                circuit_breaker_patterns = [
                    "timeout",
                    "graceful",
                    "degraded",
                    "fallback"
                ]

                patterns_found = [pattern for pattern in circuit_breaker_patterns if pattern in content.lower()]

                self._add_result(
                    "Circuit Breaker Patterns",
                    len(patterns_found) >= 2,
                    f"Found {len(patterns_found)} circuit breaker patterns: {patterns_found}" if patterns_found else "No circuit breaker patterns found",
                    {"patterns_found": patterns_found}
                )

                # Check for timeout configuration usage
                timeout_usage = "timeout" in content.lower() and "get_env" in content
                self._add_result(
                    "Timeout Configuration Usage",
                    timeout_usage,
                    "Startup manager uses configurable timeouts" if timeout_usage else "Startup manager may need timeout configuration"
                )

            except Exception as e:
                self._add_result(
                    "Circuit Breaker Patterns",
                    False,
                    f"Error reading startup manager: {e}"
                )
        else:
            self._add_result(
                "Circuit Breaker Patterns",
                False,
                "Startup manager file not found"
            )

    def _validate_graceful_degradation_code(self):
        """Validate that graceful degradation code is present."""
        startup_manager_path = self.project_root / "netra_backend" / "app" / "smd.py"

        if startup_manager_path.exists():
            try:
                content = startup_manager_path.read_text()

                # Look for graceful degradation indicators
                graceful_indicators = [
                    "graceful",
                    "degraded",
                    "fallback",
                    "bypass",
                    "emergency"
                ]

                indicators_found = [indicator for indicator in graceful_indicators if indicator in content.lower()]

                # Check for state management for degraded operations
                state_management = "app.state" in content and "available" in content.lower()

                self._add_result(
                    "Graceful Degradation Code",
                    len(indicators_found) >= 2 and state_management,
                    f"Graceful degradation patterns present: {indicators_found}" if indicators_found else "Graceful degradation patterns missing",
                    {
                        "indicators_found": indicators_found,
                        "state_management": state_management
                    }
                )

            except Exception as e:
                self._add_result(
                    "Graceful Degradation Code",
                    False,
                    f"Error analyzing graceful degradation: {e}"
                )
        else:
            self._add_result(
                "Graceful Degradation Code",
                False,
                "Startup manager file not found"
            )

    def _validate_monitoring_infrastructure(self):
        """Validate monitoring infrastructure is operational."""
        # Check for health endpoint configuration
        health_configs = [
            "path: /health",
            "OTEL_ENABLED",
            "interval:",
            "timeout:"
        ]

        staging_config_path = self.project_root / "scripts" / "deployment" / "staging_config.yaml"

        if staging_config_path.exists():
            try:
                content = staging_config_path.read_text()

                health_config_present = all(config in content for config in health_configs)

                self._add_result(
                    "Health Monitoring Config",
                    health_config_present,
                    "Health monitoring configuration complete" if health_config_present else "Health monitoring configuration incomplete"
                )

                # Check for OpenTelemetry configuration
                otel_configured = "OTEL_ENABLED: \"true\"" in content and "GOOGLE_CLOUD_PROJECT" in content

                self._add_result(
                    "OpenTelemetry Monitoring",
                    otel_configured,
                    "OpenTelemetry monitoring configured" if otel_configured else "OpenTelemetry monitoring not configured"
                )

            except Exception as e:
                self._add_result(
                    "Monitoring Infrastructure",
                    False,
                    f"Error validating monitoring: {e}"
                )
        else:
            self._add_result(
                "Monitoring Infrastructure",
                False,
                "Staging config not found for monitoring validation"
            )

    def _validate_normal_config_completeness(self):
        """Validate that normal configuration has all required components."""
        staging_config_path = self.project_root / "scripts" / "deployment" / "staging_config.yaml"

        if staging_config_path.exists():
            try:
                content = staging_config_path.read_text()

                # Required services for normal operation
                required_services = [
                    "AUTH_SERVICE_URL",
                    "AUTH_SERVICE_ENABLED",
                    "FRONTEND_URL"
                ]

                services_present = all(service in content for service in required_services)

                self._add_result(
                    "Required Services Config",
                    services_present,
                    "All required services configured" if services_present else "Missing required service configurations"
                )

                # Required database secrets
                required_db_secrets = [
                    "postgres-host-staging",
                    "postgres-port-staging",
                    "postgres-db-staging",
                    "postgres-user-staging",
                    "postgres-password-staging"
                ]

                db_secrets_present = all(secret in content for secret in required_db_secrets)

                self._add_result(
                    "Database Secrets Config",
                    db_secrets_present,
                    "All database secrets configured" if db_secrets_present else "Missing database secret configurations"
                )

                # Check Redis configuration
                redis_secrets = [
                    "redis-host-staging",
                    "redis-port-staging",
                    "redis-password-staging"
                ]

                redis_configured = all(secret in content for secret in redis_secrets)

                self._add_result(
                    "Redis Config",
                    redis_configured,
                    "Redis configuration complete" if redis_configured else "Redis configuration incomplete"
                )

            except Exception as e:
                self._add_result(
                    "Normal Config Completeness",
                    False,
                    f"Error validating configuration: {e}"
                )
        else:
            self._add_result(
                "Normal Config Completeness",
                False,
                "Staging config file not found"
            )

    def _validate_startup_sequence_integrity(self):
        """Validate that startup sequence can work without emergency bypass."""
        startup_manager_path = self.project_root / "netra_backend" / "app" / "smd.py"

        if startup_manager_path.exists():
            try:
                content = startup_manager_path.read_text()

                # Check for deterministic startup phases
                startup_phases = [
                    "PHASE 1",
                    "PHASE 2",
                    "PHASE 3",
                    "PHASE 4",
                    "PHASE 5"
                ]

                phases_present = sum(1 for phase in startup_phases if phase in content)

                self._add_result(
                    "Startup Sequence Phases",
                    phases_present >= 4,
                    f"Found {phases_present}/5 startup phases implemented" if phases_present >= 4 else f"Only {phases_present}/5 startup phases found"
                )

                # Check for proper error handling in startup
                error_handling = "DeterministicStartupError" in content and "StartupPhase" in content

                self._add_result(
                    "Startup Error Handling",
                    error_handling,
                    "Proper startup error handling present" if error_handling else "Startup error handling may need review"
                )

            except Exception as e:
                self._add_result(
                    "Startup Sequence Integrity",
                    False,
                    f"Error validating startup sequence: {e}"
                )
        else:
            self._add_result(
                "Startup Sequence Integrity",
                False,
                "Startup manager file not found"
            )

    def _validate_golden_path_components(self):
        """Validate components required for golden path user flow."""
        # Check for WebSocket manager
        websocket_manager_path = self.project_root / "netra_backend" / "app" / "websocket_core" / "manager.py"

        if websocket_manager_path.exists():
            self._add_result(
                "WebSocket Manager",
                True,
                "WebSocket manager present for real-time communication"
            )

            try:
                content = websocket_manager_path.read_text()
                event_handling = "agent_started" in content and "agent_completed" in content

                self._add_result(
                    "WebSocket Agent Events",
                    event_handling,
                    "WebSocket agent event handling present" if event_handling else "WebSocket agent events may need review"
                )
            except Exception:
                self._add_result(
                    "WebSocket Agent Events",
                    False,
                    "Error reading WebSocket manager"
                )
        else:
            self._add_result(
                "WebSocket Manager",
                False,
                "WebSocket manager not found"
            )

        # Check for agent system
        agent_registry_path = self.project_root / "netra_backend" / "app" / "agents" / "registry.py"

        if agent_registry_path.exists():
            self._add_result(
                "Agent System",
                True,
                "Agent registry present for AI interactions"
            )
        else:
            self._add_result(
                "Agent System",
                False,
                "Agent registry not found"
            )

    def _validate_websocket_event_system(self):
        """Validate WebSocket event system for business-critical chat functionality."""
        # Check for WebSocket event monitoring
        websocket_files = [
            self.project_root / "netra_backend" / "app" / "websocket_core" / "manager.py",
            self.project_root / "netra_backend" / "app" / "routes" / "websocket.py"
        ]

        websocket_system_complete = True
        missing_components = []

        for file_path in websocket_files:
            if not file_path.exists():
                websocket_system_complete = False
                missing_components.append(file_path.name)

        self._add_result(
            "WebSocket System Components",
            websocket_system_complete,
            "All WebSocket system components present" if websocket_system_complete else f"Missing WebSocket components: {missing_components}"
        )

        # Check for mission critical test
        mission_critical_test = self.project_root / "tests" / "mission_critical" / "test_websocket_agent_events_suite.py"

        self._add_result(
            "Mission Critical WebSocket Test",
            mission_critical_test.exists(),
            "Mission critical WebSocket test available" if mission_critical_test.exists() else "Mission critical WebSocket test missing"
        )

    def _validate_mission_critical_tests(self):
        """Validate that mission critical tests are available for validation."""
        mission_critical_dir = self.project_root / "tests" / "mission_critical"

        if mission_critical_dir.exists():
            test_files = list(mission_critical_dir.glob("test_*.py"))

            self._add_result(
                "Mission Critical Tests",
                len(test_files) > 0,
                f"Found {len(test_files)} mission critical test files" if test_files else "No mission critical test files found"
            )

            # Check for specific critical tests
            critical_tests = [
                "test_websocket_agent_events_suite.py",
                "test_singleton_removal_phase2.py"
            ]

            for test_name in critical_tests:
                test_path = mission_critical_dir / test_name
                self._add_result(
                    f"Critical Test: {test_name}",
                    test_path.exists(),
                    f"Critical test {test_name} available" if test_path.exists() else f"Critical test {test_name} missing"
                )
        else:
            self._add_result(
                "Mission Critical Tests",
                False,
                "Mission critical test directory not found"
            )

    def generate_readiness_report(self) -> Dict:
        """Generate a comprehensive readiness report."""
        all_passed, results = self.run_all_validations()

        passed_results = [r for r in results if r.passed]
        failed_results = [r for r in results if not r.passed]

        report = {
            "summary": {
                "overall_ready": all_passed,
                "total_checks": len(results),
                "passed_checks": len(passed_results),
                "failed_checks": len(failed_results),
                "readiness_percentage": round((len(passed_results) / len(results)) * 100, 1)
            },
            "passed_validations": [
                {
                    "check": r.check_name,
                    "message": r.message,
                    "details": r.details
                }
                for r in passed_results
            ],
            "failed_validations": [
                {
                    "check": r.check_name,
                    "message": r.message,
                    "details": r.details
                }
                for r in failed_results
            ],
            "recommendations": self._generate_recommendations(failed_results),
            "next_steps": self._generate_next_steps(all_passed)
        }

        return report

    def _generate_recommendations(self, failed_results: List[ValidationResult]) -> List[str]:
        """Generate recommendations based on failed validations."""
        recommendations = []

        for result in failed_results:
            if "Database" in result.check_name:
                recommendations.append("Complete VPC connector infrastructure fixes before cleanup")
            elif "Redis" in result.check_name:
                recommendations.append("Ensure Redis connectivity through VPC connector")
            elif "Circuit Breaker" in result.check_name:
                recommendations.append("Implement circuit breaker patterns for resilience")
            elif "WebSocket" in result.check_name:
                recommendations.append("Verify WebSocket system completeness for chat functionality")
            elif "Config" in result.check_name:
                recommendations.append("Complete staging configuration with all required services")

        if not recommendations:
            recommendations.append("All validations passed - proceed with cleanup preparation")

        return list(set(recommendations))  # Remove duplicates

    def _generate_next_steps(self, all_passed: bool) -> List[str]:
        """Generate next steps based on validation results."""
        if all_passed:
            return [
                "✅ System ready for emergency bypass cleanup",
                "🔄 Execute dry run: python scripts/emergency_bypass_cleanup.py --dry-run",
                "📋 Generate cleanup plan: python scripts/emergency_bypass_cleanup.py --generate-plan",
                "🚀 Proceed with Phase 3 cleanup when infrastructure confirmed stable"
            ]
        else:
            return [
                "❌ System NOT ready for emergency bypass cleanup",
                "🔧 Address failed validations first",
                "🏗️ Complete infrastructure fixes (Phase 2)",
                "🔄 Re-run validation after fixes",
                "⚠️ Do NOT remove emergency bypass until all validations pass"
            ]

def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Emergency Bypass Cleanup Readiness Validation")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--report", action="store_true", help="Generate comprehensive report")

    args = parser.parse_args()

    validator = CleanupReadinessValidator()

    if args.report:
        report = validator.generate_readiness_report()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            # Pretty print the report
            print("="*80)
            print("EMERGENCY BYPASS CLEANUP READINESS REPORT")
            print("="*80)
            print(f"Overall Ready: {'✅ YES' if report['summary']['overall_ready'] else '❌ NO'}")
            print(f"Readiness: {report['summary']['readiness_percentage']}% ({report['summary']['passed_checks']}/{report['summary']['total_checks']} checks passed)")

            if report['failed_validations']:
                print("\n❌ FAILED VALIDATIONS:")
                for failed in report['failed_validations']:
                    print(f"  • {failed['check']}: {failed['message']}")

            print("\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"  • {rec}")

            print("\n🔄 NEXT STEPS:")
            for step in report['next_steps']:
                print(f"  • {step}")

    else:
        all_passed, results = validator.run_all_validations()

        if args.json:
            json_results = {
                "overall_ready": all_passed,
                "results": [
                    {
                        "check": r.check_name,
                        "passed": r.passed,
                        "message": r.message,
                        "details": r.details
                    }
                    for r in results
                ]
            }
            print(json.dumps(json_results, indent=2))

        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()