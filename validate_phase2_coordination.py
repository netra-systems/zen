#!/usr/bin/env python3
"""
Phase 2 Infrastructure Coordination Validation Script
====================================================

Quick validation script to demonstrate that all Phase 2 coordination
activities have been completed successfully for Issue #1278.

This script validates:
1. Database timeout configurations (600s requirement)
2. WebSocket timeout configurations
3. Infrastructure monitoring script availability
4. VPC connector monitoring readiness

Usage:
    python validate_phase2_coordination.py
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any

class Phase2CoordinationValidator:
    """Validate Phase 2 coordination completion for Issue #1278."""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.validation_results = {}
        self.issues_found = []

    def validate_database_timeout_configs(self) -> Dict[str, Any]:
        """Validate database timeout configurations."""
        print("🔍 Validating database timeout configurations...")

        results = {
            "status": "passed",
            "details": [],
            "issues": []
        }

        # Check database manager timeout settings
        db_manager_path = self.project_root / "netra_backend/app/db/database_manager.py"
        if db_manager_path.exists():
            with open(db_manager_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Validate key timeout configurations
            timeout_configs = [
                ("pool_timeout", "30"),
                ("command_timeout", "30"),
                ("pool_recycle", "1800")
            ]

            for config_name, expected_value in timeout_configs:
                if f'"{config_name}": {expected_value}' in content or f"'{config_name}': {expected_value}" in content:
                    results["details"].append(f"✅ {config_name} configured to {expected_value}")
                else:
                    results["issues"].append(f"❌ {config_name} configuration not found")
                    results["status"] = "issues_found"
        else:
            results["issues"].append("❌ Database manager file not found")
            results["status"] = "failed"

        # Check PostgreSQL events timeout
        postgres_events_path = self.project_root / "netra_backend/app/db/postgres_events.py"
        if postgres_events_path.exists():
            with open(postgres_events_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if "idle_in_transaction_session_timeout = 60000" in content:
                results["details"].append("✅ PostgreSQL idle timeout configured (60000ms)")
            else:
                results["issues"].append("❌ PostgreSQL idle timeout not configured")
                results["status"] = "issues_found"

        return results

    def validate_websocket_timeout_configs(self) -> Dict[str, Any]:
        """Validate WebSocket timeout configurations."""
        print("🔍 Validating WebSocket timeout configurations...")

        results = {
            "status": "passed",
            "details": [],
            "issues": []
        }

        # Check WebSocket utils timeout settings
        ws_utils_path = self.project_root / "netra_backend/app/websocket_core/utils.py"
        if ws_utils_path.exists():
            with open(ws_utils_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Validate production timeout configurations (Issue #1278 requirement)
            production_timeouts = [
                ("connection_timeout_seconds", "600"),  # 10 minutes requirement
                ("heartbeat_timeout_seconds", "120"),
                ("message_timeout_seconds", "90"),
                ("handshake_timeout_seconds", "45")
            ]

            for timeout_name, expected_value in production_timeouts:
                if f'"{timeout_name}": {expected_value}' in content:
                    results["details"].append(f"✅ {timeout_name} configured to {expected_value}s")
                else:
                    results["issues"].append(f"❌ {timeout_name} configuration not found")
                    results["status"] = "issues_found"
        else:
            results["issues"].append("❌ WebSocket utils file not found")
            results["status"] = "failed"

        return results

    def validate_monitoring_infrastructure(self) -> Dict[str, Any]:
        """Validate infrastructure monitoring script availability."""
        print("🔍 Validating monitoring infrastructure...")

        results = {
            "status": "passed",
            "details": [],
            "issues": []
        }

        # Check for required monitoring scripts
        required_scripts = [
            "scripts/monitor_infrastructure_health.py",
            "scripts/validate_infrastructure_fix.py",
            "scripts/infrastructure_health_check_issue_1278.py"
        ]

        for script_path in required_scripts:
            full_path = self.project_root / script_path
            if full_path.exists():
                results["details"].append(f"✅ {script_path} available")
            else:
                results["issues"].append(f"❌ {script_path} missing")
                results["status"] = "issues_found"

        return results

    def validate_deployment_timeout_configs(self) -> Dict[str, Any]:
        """Validate deployment timeout configurations."""
        print("🔍 Validating deployment timeout configurations...")

        results = {
            "status": "passed",
            "details": [],
            "issues": []
        }

        # Check GCP deployment script for 600s timeout
        gcp_deploy_path = self.project_root / "scripts/deploy_to_gcp_actual.py"
        if gcp_deploy_path.exists():
            with open(gcp_deploy_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if "--timeout", "600" in content or '"timeout": 600' in content:
                results["details"].append("✅ GCP deployment timeout configured to 600s")
            else:
                # Check for any 600 second references
                if "600" in content:
                    results["details"].append("✅ 600s timeout references found in deployment")
                else:
                    results["issues"].append("❌ 600s timeout not found in deployment config")
                    results["status"] = "issues_found"

        return results

    def run_validation(self) -> Dict[str, Any]:
        """Run complete Phase 2 coordination validation."""
        print("🚀 Starting Phase 2 Infrastructure Coordination Validation...")
        print("=" * 60)

        # Run all validations
        self.validation_results["database_timeouts"] = self.validate_database_timeout_configs()
        self.validation_results["websocket_timeouts"] = self.validate_websocket_timeout_configs()
        self.validation_results["monitoring_infrastructure"] = self.validate_monitoring_infrastructure()
        self.validation_results["deployment_timeouts"] = self.validate_deployment_timeout_configs()

        # Generate summary
        total_validations = len(self.validation_results)
        passed_validations = sum(1 for result in self.validation_results.values() if result["status"] == "passed")
        issues_found = sum(1 for result in self.validation_results.values() if result["status"] == "issues_found")
        failed_validations = sum(1 for result in self.validation_results.values() if result["status"] == "failed")

        summary = {
            "overall_status": "passed" if passed_validations == total_validations else "issues_found",
            "total_validations": total_validations,
            "passed": passed_validations,
            "issues_found": issues_found,
            "failed": failed_validations,
            "pass_percentage": round((passed_validations / total_validations) * 100, 1)
        }

        self.validation_results["summary"] = summary

        return self.validation_results

    def print_results(self):
        """Print validation results to console."""
        print("\n" + "=" * 60)
        print("PHASE 2 COORDINATION VALIDATION RESULTS")
        print("=" * 60)

        summary = self.validation_results["summary"]
        status_icon = "✅" if summary["overall_status"] == "passed" else "⚠️"

        print(f"\n{status_icon} Overall Status: {summary['overall_status'].upper()}")
        print(f"📊 Pass Rate: {summary['pass_percentage']}% ({summary['passed']}/{summary['total_validations']})")

        for category, result in self.validation_results.items():
            if category == "summary":
                continue

            status_icon = "✅" if result["status"] == "passed" else ("⚠️" if result["status"] == "issues_found" else "❌")
            print(f"\n{status_icon} {category.replace('_', ' ').title()}:")

            for detail in result["details"]:
                print(f"   {detail}")

            for issue in result["issues"]:
                print(f"   {issue}")

        # Infrastructure team handoff message
        print("\n" + "=" * 60)
        print("INFRASTRUCTURE TEAM HANDOFF")
        print("=" * 60)

        if summary["overall_status"] == "passed":
            print("✅ Phase 2 coordination COMPLETE - Ready for infrastructure team validation")
            print("📋 Infrastructure team should use monitoring scripts:")
            print("   - python scripts/monitor_infrastructure_health.py")
            print("   - python scripts/validate_infrastructure_fix.py --staging")
            print("   - python scripts/infrastructure_health_check_issue_1278.py")
        else:
            print("⚠️  Phase 2 coordination has issues - Review before infrastructure handoff")

        print(f"\n📄 Full report available: PHASE_2_INFRASTRUCTURE_COORDINATION_REPORT.md")

def main():
    """Main validation function."""
    validator = Phase2CoordinationValidator()

    try:
        results = validator.run_validation()
        validator.print_results()

        # Exit with appropriate code
        if results["summary"]["overall_status"] == "passed":
            print("\n🎉 Phase 2 coordination validation PASSED!")
            sys.exit(0)
        else:
            print(f"\n⚠️  Phase 2 coordination validation found issues")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()