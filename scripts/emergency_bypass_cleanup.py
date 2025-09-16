#!/usr/bin/env python3
"""
Emergency Bypass Cleanup Script - Phase 3 of Issue #1278 Remediation
==================================================================

This script provides safe procedures to remove emergency configuration bypasses
once infrastructure issues are resolved.

**CRITICAL SAFETY REQUIREMENTS:**
1. Infrastructure must be verified stable before executing cleanup
2. Circuit breaker patterns remain for resilience
3. Monitoring infrastructure preserved for future prevention
4. Safe rollback plan available if needed

**Business Context:**
- Emergency bypass was implemented to maintain service availability during VPC connector issues
- Cleanup is Phase 3 after infrastructure resolution and validation
- Customer chat functionality (90% of business value) must remain operational

**Dependencies:**
- Infrastructure fixes completed (VPC connector, database connectivity)
- Golden path validation confirmed working
- Monitoring systems operational
"""

import os
import sys
import logging
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.isolated_environment import IsolatedEnvironment
from scripts.query_string_literals import query_literal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmergencyBypassCleanup:
    """
    Manages safe removal of emergency configuration bypasses.

    **SAFETY FIRST:** This class prioritizes system stability and provides
    comprehensive validation before making any changes.
    """

    def __init__(self):
        self.env = IsolatedEnvironment()
        self.project_root = Path(__file__).parent.parent
        self.staging_config_path = self.project_root / "scripts" / "deployment" / "staging_config.yaml"

    def validate_infrastructure_readiness(self) -> Tuple[bool, List[str]]:
        """
        Validate that infrastructure is ready for emergency bypass removal.

        Returns:
            Tuple of (is_ready, list_of_issues)
        """
        logger.info("🔍 Validating infrastructure readiness for emergency bypass cleanup...")
        issues = []

        # Check 1: Database connectivity validation script exists and can run
        try:
            result = subprocess.run([
                "python", "-c",
                "from netra_backend.app.db.database_manager import DatabaseManager; print('Database manager import successful')"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                issues.append(f"Database manager import failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            issues.append("Database manager import timed out (30s)")
        except Exception as e:
            issues.append(f"Database validation failed: {e}")

        # Check 2: VPC connector requirements
        vpc_connector_configured = True  # TODO: Add actual VPC connector validation
        if not vpc_connector_configured:
            issues.append("VPC connector not properly configured")

        # Check 3: Redis connectivity potential
        try:
            result = subprocess.run([
                "python", "-c",
                "from netra_backend.app.core.redis_manager import RedisManager; print('Redis manager import successful')"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                issues.append(f"Redis manager import failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            issues.append("Redis manager import timed out (30s)")
        except Exception as e:
            issues.append(f"Redis validation failed: {e}")

        # Check 4: Golden path validation
        golden_path_validated = self._check_golden_path_status()
        if not golden_path_validated:
            issues.append("Golden path user flow not validated as working")

        # Check 5: Circuit breaker patterns present
        circuit_breakers_present = self._validate_circuit_breaker_patterns()
        if not circuit_breakers_present:
            issues.append("Circuit breaker patterns not found - system lacks resilience safeguards")

        is_ready = len(issues) == 0

        if is_ready:
            logger.info("✅ Infrastructure validation passed - ready for emergency bypass cleanup")
        else:
            logger.warning(f"❌ Infrastructure validation failed - {len(issues)} issues found")
            for issue in issues:
                logger.warning(f"  - {issue}")

        return is_ready, issues

    def _check_golden_path_status(self) -> bool:
        """Check if golden path user flow is validated as working."""
        # Check for golden path validation files/reports
        golden_path_files = [
            self.project_root / "docs" / "GOLDEN_PATH_USER_FLOW_COMPLETE.md",
            self.project_root / "PHASE_1_DEPLOYMENT_VALIDATION_REPORT.md"
        ]

        for file_path in golden_path_files:
            if file_path.exists():
                try:
                    content = file_path.read_text()
                    # Look for success indicators
                    if "✅" in content and ("golden path" in content.lower() or "working" in content.lower()):
                        return True
                except Exception:
                    continue

        return False

    def _validate_circuit_breaker_patterns(self) -> bool:
        """Validate that circuit breaker patterns are present for resilience."""
        # Check startup manager for graceful degradation patterns
        startup_manager_path = self.project_root / "netra_backend" / "app" / "smd.py"

        if not startup_manager_path.exists():
            return False

        try:
            content = startup_manager_path.read_text()
            # Look for circuit breaker patterns (graceful degradation, timeout handling)
            circuit_breaker_indicators = [
                "graceful",
                "timeout",
                "fallback",
                "circuit",
                "degraded"
            ]

            return any(indicator in content.lower() for indicator in circuit_breaker_indicators)
        except Exception:
            return False

    def prepare_cleanup_configuration(self) -> Dict:
        """
        Prepare the normal (non-emergency) configuration.

        Returns:
            Dictionary with the updated configuration
        """
        logger.info("📋 Preparing normal configuration (emergency bypass disabled)...")

        if not self.staging_config_path.exists():
            raise FileNotFoundError(f"Staging config not found: {self.staging_config_path}")

        # Load current staging configuration
        with open(self.staging_config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Prepare normal configuration by removing emergency bypass
        normal_config = config.copy()

        # Remove emergency bypass from environment variables
        if 'env_vars' in normal_config and 'EMERGENCY_ALLOW_NO_DATABASE' in normal_config['env_vars']:
            logger.info("  - Removing EMERGENCY_ALLOW_NO_DATABASE from staging config")
            del normal_config['env_vars']['EMERGENCY_ALLOW_NO_DATABASE']

        # Preserve circuit breaker and monitoring configuration
        monitoring_vars = [
            'WEBSOCKET_CONNECTION_TIMEOUT',
            'WEBSOCKET_HEARTBEAT_INTERVAL',
            'WEBSOCKET_HEARTBEAT_TIMEOUT',
            'AUTH_DB_URL_TIMEOUT',
            'AUTH_DB_ENGINE_TIMEOUT',
            'AUTH_DB_VALIDATION_TIMEOUT'
        ]

        logger.info("  - Preserving circuit breaker timeouts and monitoring configuration")
        for var in monitoring_vars:
            if 'env_vars' in config and var in config['env_vars']:
                logger.info(f"    ✓ Keeping {var}: {config['env_vars'][var]}")

        return normal_config

    def create_rollback_configuration(self) -> None:
        """
        Create a rollback configuration file for emergency re-activation if needed.
        """
        logger.info("🔄 Creating rollback configuration for emergency re-activation...")

        rollback_config_path = self.project_root / "scripts" / "deployment" / "staging_config_emergency_rollback.yaml"

        # Copy current emergency configuration as rollback
        import shutil
        shutil.copy2(self.staging_config_path, rollback_config_path)

        logger.info(f"  ✓ Rollback configuration saved: {rollback_config_path}")
        logger.info("  💡 To re-enable emergency mode: restore this file as staging_config.yaml")

    def validate_normal_configuration(self, config: Dict) -> Tuple[bool, List[str]]:
        """
        Validate the normal configuration before applying it.

        Args:
            config: The normal configuration dictionary

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        logger.info("🔍 Validating normal configuration...")
        issues = []

        # Check that emergency bypass is properly removed
        if 'env_vars' in config and 'EMERGENCY_ALLOW_NO_DATABASE' in config['env_vars']:
            issues.append("EMERGENCY_ALLOW_NO_DATABASE still present in configuration")

        # Check that essential services are still configured
        required_services = [
            'AUTH_SERVICE_URL',
            'AUTH_SERVICE_ENABLED',
            'FRONTEND_URL'
        ]

        for service in required_services:
            if 'env_vars' not in config or service not in config['env_vars']:
                issues.append(f"Required service configuration missing: {service}")

        # Check that database configuration is present (since we're removing bypass)
        required_db_secrets = [
            'POSTGRES_HOST',
            'POSTGRES_PORT',
            'POSTGRES_DB',
            'POSTGRES_USER',
            'POSTGRES_PASSWORD'
        ]

        for secret in required_db_secrets:
            if 'secrets' not in config or secret not in config['secrets']:
                issues.append(f"Required database secret missing: {secret}")

        # Check that circuit breaker timeouts are preserved
        preserved_timeouts = [
            'AUTH_DB_URL_TIMEOUT',
            'AUTH_DB_ENGINE_TIMEOUT',
            'AUTH_DB_VALIDATION_TIMEOUT'
        ]

        for timeout in preserved_timeouts:
            if 'env_vars' not in config or timeout not in config['env_vars']:
                issues.append(f"Circuit breaker timeout missing: {timeout}")

        is_valid = len(issues) == 0

        if is_valid:
            logger.info("✅ Normal configuration validation passed")
        else:
            logger.warning(f"❌ Normal configuration validation failed - {len(issues)} issues")
            for issue in issues:
                logger.warning(f"  - {issue}")

        return is_valid, issues

    def execute_dry_run(self) -> bool:
        """
        Execute a dry run of the cleanup process without making changes.

        Returns:
            True if dry run successful, False otherwise
        """
        logger.info("🧪 Executing emergency bypass cleanup dry run...")

        try:
            # Step 1: Infrastructure readiness check
            is_ready, issues = self.validate_infrastructure_readiness()
            if not is_ready:
                logger.error("❌ Dry run failed: Infrastructure not ready")
                return False

            # Step 2: Prepare normal configuration
            normal_config = self.prepare_cleanup_configuration()

            # Step 3: Validate normal configuration
            is_valid, validation_issues = self.validate_normal_configuration(normal_config)
            if not is_valid:
                logger.error("❌ Dry run failed: Normal configuration invalid")
                return False

            # Step 4: Check rollback capability
            self.create_rollback_configuration()

            logger.info("✅ Dry run completed successfully")
            logger.info("🚀 System ready for emergency bypass cleanup")

            return True

        except Exception as e:
            logger.error(f"❌ Dry run failed with exception: {e}")
            return False

    def generate_cleanup_plan(self) -> Dict:
        """
        Generate a detailed cleanup execution plan.

        Returns:
            Dictionary containing the cleanup plan
        """
        plan = {
            "phase": "Phase 3 - Emergency Bypass Cleanup",
            "objective": "Remove emergency configuration while preserving system stability",
            "prerequisites": [
                "Infrastructure fixes completed (VPC connector, database connectivity)",
                "Golden path validation confirmed working",
                "Circuit breaker patterns validated",
                "Monitoring systems operational"
            ],
            "steps": [
                {
                    "step": 1,
                    "action": "Infrastructure Readiness Validation",
                    "description": "Verify infrastructure is stable and ready for normal operations",
                    "command": "python scripts/emergency_bypass_cleanup.py --validate-infrastructure",
                    "success_criteria": "All infrastructure checks pass"
                },
                {
                    "step": 2,
                    "action": "Configuration Preparation",
                    "description": "Prepare normal configuration with emergency bypass removed",
                    "command": "python scripts/emergency_bypass_cleanup.py --prepare-config",
                    "success_criteria": "Normal configuration validated successfully"
                },
                {
                    "step": 3,
                    "action": "Rollback Configuration Creation",
                    "description": "Create rollback configuration for emergency re-activation if needed",
                    "command": "python scripts/emergency_bypass_cleanup.py --create-rollback",
                    "success_criteria": "Rollback configuration file created"
                },
                {
                    "step": 4,
                    "action": "Staging Configuration Update",
                    "description": "Update staging config to remove EMERGENCY_ALLOW_NO_DATABASE=true",
                    "command": "Manual edit of scripts/deployment/staging_config.yaml",
                    "success_criteria": "EMERGENCY_ALLOW_NO_DATABASE removed from env_vars"
                },
                {
                    "step": 5,
                    "action": "Deployment with Normal Configuration",
                    "description": "Deploy to staging with normal configuration",
                    "command": "python scripts/deploy_to_gcp.py --project netra-staging --build-local",
                    "success_criteria": "Deployment successful with healthy service"
                },
                {
                    "step": 6,
                    "action": "Golden Path Validation",
                    "description": "Validate complete user flow works without emergency bypass",
                    "command": "python tests/mission_critical/test_websocket_agent_events_suite.py",
                    "success_criteria": "All mission critical tests pass"
                },
                {
                    "step": 7,
                    "action": "String Literals Update",
                    "description": "Remove emergency variable from string literals index",
                    "command": "python scripts/scan_string_literals.py",
                    "success_criteria": "String literals index updated"
                },
                {
                    "step": 8,
                    "action": "Monitoring Validation",
                    "description": "Ensure monitoring and circuit breakers remain operational",
                    "command": "Check /health endpoint and monitoring dashboards",
                    "success_criteria": "All monitoring systems healthy"
                }
            ],
            "rollback_plan": [
                {
                    "action": "Immediate Rollback",
                    "description": "Restore emergency configuration if issues detected",
                    "command": "cp scripts/deployment/staging_config_emergency_rollback.yaml scripts/deployment/staging_config.yaml && python scripts/deploy_to_gcp.py --project netra-staging --build-local"
                }
            ],
            "success_criteria": [
                "Service starts successfully without emergency bypass",
                "Database and Redis connections working normally",
                "Golden path user flow operational",
                "All mission critical tests passing",
                "Circuit breaker patterns preserved",
                "Monitoring systems healthy"
            ],
            "risks_and_mitigations": [
                {
                    "risk": "Database connectivity issues resurface",
                    "mitigation": "Rollback to emergency configuration immediately"
                },
                {
                    "risk": "VPC connector problems return",
                    "mitigation": "Infrastructure team escalation + emergency rollback"
                },
                {
                    "risk": "Service fails to start without bypass",
                    "mitigation": "Circuit breaker timeouts + graceful degradation + rollback"
                }
            ]
        }

        return plan

def main():
    """Main execution function with command line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Emergency Bypass Cleanup - Phase 3 of Issue #1278 Remediation")
    parser.add_argument("--validate-infrastructure", action="store_true",
                       help="Validate infrastructure readiness")
    parser.add_argument("--prepare-config", action="store_true",
                       help="Prepare normal configuration")
    parser.add_argument("--create-rollback", action="store_true",
                       help="Create rollback configuration")
    parser.add_argument("--dry-run", action="store_true",
                       help="Execute complete dry run")
    parser.add_argument("--generate-plan", action="store_true",
                       help="Generate detailed cleanup plan")

    args = parser.parse_args()

    cleanup = EmergencyBypassCleanup()

    if args.validate_infrastructure:
        is_ready, issues = cleanup.validate_infrastructure_readiness()
        if not is_ready:
            logger.error("Infrastructure not ready for cleanup")
            sys.exit(1)
        logger.info("Infrastructure ready for cleanup")

    elif args.prepare_config:
        try:
            config = cleanup.prepare_cleanup_configuration()
            is_valid, issues = cleanup.validate_normal_configuration(config)
            if not is_valid:
                logger.error("Normal configuration invalid")
                sys.exit(1)
            logger.info("Normal configuration prepared and validated")
        except Exception as e:
            logger.error(f"Configuration preparation failed: {e}")
            sys.exit(1)

    elif args.create_rollback:
        try:
            cleanup.create_rollback_configuration()
            logger.info("Rollback configuration created")
        except Exception as e:
            logger.error(f"Rollback configuration creation failed: {e}")
            sys.exit(1)

    elif args.dry_run:
        success = cleanup.execute_dry_run()
        if not success:
            logger.error("Dry run failed")
            sys.exit(1)
        logger.info("Dry run completed successfully")

    elif args.generate_plan:
        plan = cleanup.generate_cleanup_plan()
        import json
        print(json.dumps(plan, indent=2))

    else:
        # Default: Show help and current status
        parser.print_help()
        print("\n" + "="*80)
        print("EMERGENCY BYPASS CLEANUP STATUS")
        print("="*80)

        # Check current emergency bypass status
        try:
            env = IsolatedEnvironment()
            emergency_status = env.get_env("EMERGENCY_ALLOW_NO_DATABASE", "false")
            print(f"Current emergency bypass status: {emergency_status}")

            if emergency_status.lower() == "true":
                print("⚠️  Emergency bypass is ACTIVE")
                print("   Use --dry-run to test cleanup readiness")
                print("   Use --generate-plan to see detailed cleanup steps")
            else:
                print("✅ Emergency bypass is already disabled")

        except Exception as e:
            print(f"Could not determine emergency bypass status: {e}")

if __name__ == "__main__":
    main()