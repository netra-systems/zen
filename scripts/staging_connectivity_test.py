#!/usr/bin/env python3
"""
Emergency Staging Connectivity Test Script
Issue #1278 Database Connectivity Outage - Phase 1 Diagnostics

CRITICAL: This script provides emergency diagnostics for database connectivity
in the staging environment. Use this to validate fixes during outage response.

Usage:
    python scripts/staging_connectivity_test.py --quick       # Basic checks
    python scripts/staging_connectivity_test.py --full        # Complete diagnostics
    python scripts/staging_connectivity_test.py --env-check   # Environment validation only

REQUIREMENTS:
- Must be run with staging environment variables loaded
- Requires access to staging VPC and Cloud SQL instance
- Uses SSOT database configuration patterns

Business Value: Platform/Internal - Critical incident response
Ensures rapid diagnosis and resolution of database connectivity issues.
"""

import asyncio
import sys
import argparse
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# SSOT imports - required for emergency response
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.config import get_config
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.core.database_timeout_config import get_database_timeout_config

class StagingConnectivityTester:
    """Emergency connectivity tester for Issue #1278 database outage."""

    def __init__(self):
        self.env = IsolatedEnvironment()
        self.results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment_check": {},
            "config_check": {},
            "database_health": {},
            "timeout_validation": {},
            "summary": {}
        }

    def validate_environment_variables(self) -> Dict[str, Any]:
        """Validate required staging environment variables."""
        print("🔍 Phase 1.4: Environment Variable Validation")

        required_vars = [
            "ENVIRONMENT",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "SECRET_KEY",
            "DATABASE_URL"
        ]

        staging_specific_vars = [
            "JWT_SECRET_STAGING",
            "SERVICE_SECRET",
            "CLICKHOUSE_URL",
            "REDIS_REQUIRED"
        ]

        results = {
            "required_vars": {},
            "staging_vars": {},
            "missing_critical": [],
            "status": "unknown"
        }

        # Check required variables
        for var in required_vars:
            value = self.env.get(var)
            if value:
                results["required_vars"][var] = "✅ Present"
                if var in ["SECRET_KEY", "POSTGRES_PASSWORD"]:
                    print(f"  {var}: ***hidden*** ✅")
                else:
                    print(f"  {var}: {value} ✅")
            else:
                results["required_vars"][var] = "❌ MISSING"
                results["missing_critical"].append(var)
                print(f"  {var}: ❌ MISSING - CRITICAL")

        # Check staging-specific variables
        for var in staging_specific_vars:
            value = self.env.get(var)
            if value:
                results["staging_vars"][var] = "✅ Present"
                print(f"  {var}: Present ✅")
            else:
                results["staging_vars"][var] = "⚠️ Missing"
                print(f"  {var}: ⚠️ Missing (staging-specific)")

        # Determine overall status
        if len(results["missing_critical"]) == 0:
            results["status"] = "healthy"
            print("📋 Environment Status: ✅ HEALTHY - All critical variables present")
        else:
            results["status"] = "critical"
            print(f"🚨 Environment Status: ❌ CRITICAL - {len(results['missing_critical'])} missing variables")

        return results

    def validate_timeout_configuration(self) -> Dict[str, Any]:
        """Validate database timeout configuration."""
        print("\n🔍 Phase 1.1: Database Timeout Configuration Check")

        try:
            # Check if we're in staging environment
            env_type = self.env.get("ENVIRONMENT") or "development"
            config = get_database_timeout_config(env_type)

            results = {
                "environment": env_type,
                "timeouts": config,
                "status": "healthy",
                "issues": []
            }

            print(f"  Environment: {env_type}")
            print(f"  Initialization Timeout: {config['initialization_timeout']}s")
            print(f"  Connection Timeout: {config['connection_timeout']}s")
            print(f"  Pool Timeout: {config['pool_timeout']}s")

            # Validate timeout values are reasonable
            if config["initialization_timeout"] < 60:
                results["issues"].append("Initialization timeout may be too low for Cloud SQL")
                results["status"] = "warning"

            if config["connection_timeout"] < 30:
                results["issues"].append("Connection timeout may be too low for VPC")
                results["status"] = "warning"

            if len(results["issues"]) == 0:
                print("📋 Timeout Status: ✅ HEALTHY - All timeouts properly configured")
            else:
                print(f"📋 Timeout Status: ⚠️ WARNING - {len(results['issues'])} potential issues")
                for issue in results["issues"]:
                    print(f"    - {issue}")

            return results

        except Exception as e:
            return {
                "environment": "unknown",
                "error": str(e),
                "status": "error"
            }

    async def test_database_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity and health."""
        print("\n🔍 Phase 1.3: Database Connectivity Test")

        try:
            config = get_config()
            print(f"  Config Type: {type(config).__name__}")

            # Get database URL
            db_url = config.get_database_url()
            if db_url:
                # Hide password in URL for logging
                safe_url = db_url.split('@')[0] + '@***' + db_url.split('@')[1]
                print(f"  Database URL: {safe_url}")
            else:
                print("  Database URL: ❌ NOT CONFIGURED")
                return {"status": "error", "error": "Database URL not configured"}

            # Test health check
            print("  Testing database health...")
            start_time = time.time()

            db_manager = DatabaseManager()
            health_result = await db_manager.health_check()

            duration = time.time() - start_time

            results = {
                "status": health_result.get("status", "unknown"),
                "health_check": health_result,
                "duration_seconds": round(duration, 3),
                "database_url_configured": bool(db_url)
            }

            if health_result.get("status") == "healthy":
                print(f"📋 Database Status: ✅ HEALTHY - Connection successful in {duration:.3f}s")
            else:
                print(f"📋 Database Status: ❌ UNHEALTHY - {health_result}")

            return results

        except Exception as e:
            print(f"📋 Database Status: ❌ ERROR - {type(e).__name__}: {str(e)}")
            return {
                "status": "error",
                "error": f"{type(e).__name__}: {str(e)}"
            }

    def generate_summary(self) -> Dict[str, Any]:
        """Generate emergency response summary."""
        print("\n📊 EMERGENCY RESPONSE SUMMARY")
        print("=" * 50)

        # Determine overall system status
        env_status = self.results["environment_check"].get("status", "unknown")
        db_status = self.results["database_health"].get("status", "unknown")
        timeout_status = self.results["timeout_validation"].get("status", "unknown")

        critical_issues = []
        warnings = []

        # Check for critical issues
        if env_status == "critical":
            missing = self.results["environment_check"].get("missing_critical", [])
            critical_issues.append(f"Missing {len(missing)} critical environment variables")

        if db_status == "error":
            critical_issues.append("Database connectivity failure")

        if timeout_status == "error":
            critical_issues.append("Timeout configuration error")

        # Check for warnings
        if env_status == "warning" or timeout_status == "warning":
            warnings.append("Configuration warnings detected")

        # Determine overall status
        if len(critical_issues) == 0:
            if len(warnings) == 0:
                overall_status = "✅ HEALTHY"
                recommendation = "System appears operational. Proceed with normal operations."
            else:
                overall_status = "⚠️ WARNING"
                recommendation = "System operational but monitor warnings. Consider addressing configuration issues."
        else:
            overall_status = "🚨 CRITICAL"
            recommendation = "EMERGENCY ACTION REQUIRED. Address critical issues immediately."

        summary = {
            "overall_status": overall_status,
            "critical_issues": critical_issues,
            "warnings": warnings,
            "recommendation": recommendation,
            "next_actions": self._get_next_actions(critical_issues, warnings)
        }

        print(f"Overall Status: {overall_status}")
        print(f"Critical Issues: {len(critical_issues)}")
        print(f"Warnings: {len(warnings)}")
        print(f"\n🎯 RECOMMENDATION: {recommendation}")

        if critical_issues:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in critical_issues:
                print(f"  - {issue}")

        if warnings:
            print("\n⚠️ WARNINGS:")
            for warning in warnings:
                print(f"  - {warning}")

        return summary

    def _get_next_actions(self, critical_issues: list, warnings: list) -> list:
        """Determine next actions based on issues found."""
        actions = []

        if any("environment variables" in issue for issue in critical_issues):
            actions.append("Load staging environment variables from config/staging.env")
            actions.append("Verify GCP Secret Manager secrets are accessible")

        if any("Database connectivity" in issue for issue in critical_issues):
            actions.append("Check Cloud SQL instance status in GCP Console")
            actions.append("Verify VPC connector 'staging-connector' is healthy")
            actions.append("Validate Cloud Run service VPC annotations")

        if any("configuration" in issue.lower() for issue in critical_issues):
            actions.append("Review timeout configuration in database_timeout_config.py")
            actions.append("Check for recent configuration changes")

        if len(actions) == 0:
            actions.append("Monitor system health and proceed with Phase 2 testing")

        return actions

    async def run_quick_check(self):
        """Run quick emergency checks (Phase 1)."""
        print("🚨 EMERGENCY CONNECTIVITY CHECK - PHASE 1")
        print("Issue #1278 Database Connectivity Outage")
        print("=" * 60)

        # Phase 1.4: Environment validation
        self.results["environment_check"] = self.validate_environment_variables()

        # Phase 1.1: Timeout configuration
        self.results["timeout_validation"] = self.validate_timeout_configuration()

        # Phase 1.3: Database connectivity (if env allows)
        self.results["database_health"] = await self.test_database_connectivity()

        # Generate summary
        self.results["summary"] = self.generate_summary()

        return self.results

    async def run_full_diagnostics(self):
        """Run complete diagnostic suite."""
        print("🔍 FULL DIAGNOSTIC SUITE - Issue #1278")
        print("=" * 60)

        # Run all checks
        await self.run_quick_check()

        # Additional diagnostics could be added here
        # - VPC connector status check
        # - Cloud SQL instance validation
        # - Redis connectivity test
        # - End-to-end agent pipeline test

        return self.results

async def main():
    parser = argparse.ArgumentParser(
        description="Emergency staging connectivity test for Issue #1278"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick emergency checks only"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run complete diagnostic suite"
    )
    parser.add_argument(
        "--env-check",
        action="store_true",
        help="Environment validation only"
    )
    parser.add_argument(
        "--output",
        help="Save results to JSON file"
    )

    args = parser.parse_args()

    tester = StagingConnectivityTester()

    if args.env_check:
        results = {"environment_check": tester.validate_environment_variables()}
    elif args.full:
        results = await tester.run_full_diagnostics()
    else:
        # Default to quick check
        results = await tester.run_quick_check()

    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📁 Results saved to: {args.output}")

    # Print final status for emergency response
    if "summary" in results:
        print(f"\n🎯 FINAL STATUS: {results['summary']['overall_status']}")
        if results['summary'].get('next_actions'):
            print("\n📋 NEXT ACTIONS:")
            for i, action in enumerate(results['summary']['next_actions'], 1):
                print(f"  {i}. {action}")

if __name__ == "__main__":
    asyncio.run(main())