#!/usr/bin/env python3
"""
Infrastructure Health Check Script for Issue #1278
===================================================

Comprehensive validation of all GCP infrastructure components required
for staging environment functionality.

Usage:
    python scripts/infrastructure_health_check_issue_1278.py
    python scripts/infrastructure_health_check_issue_1278.py --fix-mode
    python scripts/infrastructure_health_check_issue_1278.py --report-only
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse

class InfrastructureHealthChecker:
    """Comprehensive infrastructure health checker for Issue #1278."""

    def __init__(self, project_id: str = "netra-staging", region: str = "us-central1"):
        self.project_id = project_id
        self.region = region
        self.validation_results = {}
        self.critical_failures = []
        self.warnings = []

    def run_gcloud_command(self, command: List[str]) -> Tuple[bool, str, str]:
        """Execute gcloud command and return success, stdout, stderr."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out after 60 seconds"
        except Exception as e:
            return False, "", f"Command execution failed: {str(e)}"

    def check_vpc_connector(self) -> Dict[str, any]:
        """Validate VPC connector configuration and status."""
        print("🔍 Checking VPC Connector...")

        connector_name = "staging-connector"
        command = [
            "gcloud", "compute", "networks", "vpc-access", "connectors", "describe",
            connector_name, "--region", self.region, "--project", self.project_id,
            "--format", "json"
        ]

        success, stdout, stderr = self.run_gcloud_command(command)

        if not success:
            self.critical_failures.append(f"VPC connector '{connector_name}' not found")
            return {"status": "MISSING", "details": stderr}

        try:
            connector_info = json.loads(stdout)
            state = connector_info.get("state", "UNKNOWN")
            ip_cidr_range = connector_info.get("ipCidrRange", "")
            min_instances = connector_info.get("minInstances", 0)
            max_instances = connector_info.get("maxInstances", 0)
            network = connector_info.get("network", "").split("/")[-1]

            result = {
                "status": "FOUND",
                "state": state,
                "ip_cidr_range": ip_cidr_range,
                "min_instances": min_instances,
                "max_instances": max_instances,
                "network": network,
                "issues": []
            }

            # Validate configuration
            if state != "READY":
                issue = f"VPC connector state is '{state}', expected 'READY'"
                self.critical_failures.append(issue)
                result["issues"].append(issue)

            if ip_cidr_range != "10.1.0.0/28":
                issue = f"IP CIDR range is '{ip_cidr_range}', expected '10.1.0.0/28'"
                self.warnings.append(issue)
                result["issues"].append(issue)

            if min_instances < 2:
                issue = f"Min instances is {min_instances}, should be at least 2"
                self.warnings.append(issue)
                result["issues"].append(issue)

            if max_instances < 10:
                issue = f"Max instances is {max_instances}, should be at least 10"
                self.warnings.append(issue)
                result["issues"].append(issue)

            if network != "staging-vpc":
                issue = f"Network is '{network}', expected 'staging-vpc'"
                self.critical_failures.append(issue)
                result["issues"].append(issue)

            if not result["issues"]:
                print("   ✅ VPC connector configuration is valid")
            else:
                print(f"   ❌ Found {len(result['issues'])} VPC connector issues")

            return result

        except json.JSONDecodeError:
            self.critical_failures.append("Failed to parse VPC connector information")
            return {"status": "PARSE_ERROR", "details": "Invalid JSON response"}

    def check_cloud_sql_instance(self) -> Dict[str, any]:
        """Validate Cloud SQL instance configuration and connectivity."""
        print("🔍 Checking Cloud SQL Instance...")

        instance_name = "netra-staging-db"
        command = [
            "gcloud", "sql", "instances", "describe", instance_name,
            "--project", self.project_id, "--format", "json"
        ]

        success, stdout, stderr = self.run_gcloud_command(command)

        if not success:
            self.critical_failures.append(f"Cloud SQL instance '{instance_name}' not found")
            return {"status": "MISSING", "details": stderr}

        try:
            instance_info = json.loads(stdout)
            state = instance_info.get("state", "UNKNOWN")
            database_version = instance_info.get("databaseVersion", "")
            tier = instance_info.get("settings", {}).get("tier", "")
            ip_config = instance_info.get("settings", {}).get("ipConfiguration", {})

            result = {
                "status": "FOUND",
                "state": state,
                "database_version": database_version,
                "tier": tier,
                "private_network": ip_config.get("privateNetwork", ""),
                "require_ssl": ip_config.get("requireSsl", False),
                "issues": []
            }

            # Validate instance state
            if state != "RUNNABLE":
                issue = f"Cloud SQL instance state is '{state}', expected 'RUNNABLE'"
                self.critical_failures.append(issue)
                result["issues"].append(issue)

            # Validate network configuration
            if not result["private_network"]:
                issue = "Private network not configured - required for VPC access"
                self.critical_failures.append(issue)
                result["issues"].append(issue)

            if not result["require_ssl"]:
                issue = "SSL not required - security risk"
                self.warnings.append(issue)
                result["issues"].append(issue)

            if not result["issues"]:
                print("   ✅ Cloud SQL instance configuration is valid")
            else:
                print(f"   ❌ Found {len(result['issues'])} Cloud SQL issues")

            return result

        except json.JSONDecodeError:
            self.critical_failures.append("Failed to parse Cloud SQL instance information")
            return {"status": "PARSE_ERROR", "details": "Invalid JSON response"}

    def check_secret_manager_secrets(self) -> Dict[str, any]:
        """Validate all required Secret Manager secrets."""
        print("🔍 Checking Secret Manager Secrets...")

        required_secrets = [
            "database-url",
            "database-direct-url",
            "jwt-secret-staging",
            "redis-url",
            "oauth-client-id",
            "oauth-client-secret",
            "openai-api-key",
            "anthropic-api-key",
            "smtp-password",
            "cors-allowed-origins"
        ]

        result = {
            "status": "CHECKING",
            "secrets": {},
            "missing": [],
            "invalid": [],
            "issues": []
        }

        for secret_name in required_secrets:
            secret_result = self._check_individual_secret(secret_name)
            result["secrets"][secret_name] = secret_result

            if secret_result["status"] == "MISSING":
                result["missing"].append(secret_name)
                self.critical_failures.append(f"Secret '{secret_name}' is missing")
            elif secret_result["status"] == "INVALID":
                result["invalid"].append(secret_name)
                self.critical_failures.append(f"Secret '{secret_name}' has invalid value")

        total_secrets = len(required_secrets)
        valid_secrets = len([s for s in result["secrets"].values() if s["status"] == "VALID"])

        print(f"   📊 Secret validation: {valid_secrets}/{total_secrets} valid")

        if result["missing"]:
            print(f"   ❌ Missing secrets: {', '.join(result['missing'])}")

        if result["invalid"]:
            print(f"   ❌ Invalid secrets: {', '.join(result['invalid'])}")

        if not result["missing"] and not result["invalid"]:
            print("   ✅ All required secrets are valid")
            result["status"] = "VALID"
        else:
            result["status"] = "INVALID"

        return result

    def _check_individual_secret(self, secret_name: str) -> Dict[str, any]:
        """Check individual secret existence and validity."""
        # Check if secret exists
        command = [
            "gcloud", "secrets", "describe", secret_name,
            "--project", self.project_id, "--format", "json"
        ]

        success, stdout, stderr = self.run_gcloud_command(command)

        if not success:
            return {"status": "MISSING", "details": stderr}

        # Get secret value
        command = [
            "gcloud", "secrets", "versions", "access", "latest",
            "--secret", secret_name, "--project", self.project_id
        ]

        success, secret_value, stderr = self.run_gcloud_command(command)

        if not success:
            return {"status": "ACCESS_DENIED", "details": stderr}

        secret_value = secret_value.strip()

        if not secret_value or secret_value == "null":
            return {"status": "INVALID", "details": "Empty or null value"}

        # Validate format for specific secrets
        if secret_name in ["database-url", "database-direct-url"]:
            if not secret_value.startswith("postgresql+asyncpg://"):
                return {"status": "INVALID", "details": "Not a valid PostgreSQL+asyncpg URL"}

        elif secret_name == "jwt-secret-staging":
            if len(secret_value) < 32:
                return {"status": "INVALID", "details": "JWT secret too short (< 32 chars)"}

        elif secret_name == "redis-url":
            if not secret_value.startswith("redis://"):
                return {"status": "INVALID", "details": "Not a valid Redis URL"}

        return {"status": "VALID", "value_length": len(secret_value)}

    def check_cloud_run_services(self) -> Dict[str, any]:
        """Validate Cloud Run services and their VPC configuration."""
        print("🔍 Checking Cloud Run Services...")

        services = ["netra-backend-staging", "auth-staging"]
        result = {
            "status": "CHECKING",
            "services": {},
            "issues": []
        }

        for service_name in services:
            service_result = self._check_individual_service(service_name)
            result["services"][service_name] = service_result

            if service_result["status"] != "VALID":
                result["issues"].extend(service_result.get("issues", []))

        if not result["issues"]:
            print("   ✅ All Cloud Run services are properly configured")
            result["status"] = "VALID"
        else:
            print(f"   ❌ Found {len(result['issues'])} Cloud Run service issues")
            result["status"] = "INVALID"

        return result

    def _check_individual_service(self, service_name: str) -> Dict[str, any]:
        """Check individual Cloud Run service configuration."""
        command = [
            "gcloud", "run", "services", "describe", service_name,
            "--region", self.region, "--project", self.project_id,
            "--format", "json"
        ]

        success, stdout, stderr = self.run_gcloud_command(command)

        if not success:
            issue = f"Cloud Run service '{service_name}' not found"
            self.critical_failures.append(issue)
            return {"status": "MISSING", "details": stderr, "issues": [issue]}

        try:
            service_info = json.loads(stdout)
            annotations = service_info.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})

            vpc_connector = annotations.get("run.googleapis.com/vpc-access-connector", "")
            vpc_egress = annotations.get("run.googleapis.com/vpc-access-egress", "")

            result = {
                "status": "FOUND",
                "vpc_connector": vpc_connector,
                "vpc_egress": vpc_egress,
                "issues": []
            }

            # Validate VPC configuration
            if vpc_connector != "staging-connector":
                issue = f"Service '{service_name}' has incorrect VPC connector: '{vpc_connector}'"
                self.critical_failures.append(issue)
                result["issues"].append(issue)

            if vpc_egress != "all-traffic":
                issue = f"Service '{service_name}' has incorrect VPC egress: '{vpc_egress}'"
                self.critical_failures.append(issue)
                result["issues"].append(issue)

            if not result["issues"]:
                result["status"] = "VALID"
            else:
                result["status"] = "INVALID"

            return result

        except json.JSONDecodeError:
            issue = f"Failed to parse service information for '{service_name}'"
            self.critical_failures.append(issue)
            return {"status": "PARSE_ERROR", "details": "Invalid JSON response", "issues": [issue]}

    def generate_report(self) -> Dict[str, any]:
        """Generate comprehensive infrastructure health report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_id": self.project_id,
            "region": self.region,
            "validation_results": self.validation_results,
            "summary": {
                "critical_failures": len(self.critical_failures),
                "warnings": len(self.warnings),
                "overall_status": "HEALTHY" if not self.critical_failures else "CRITICAL"
            },
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "next_actions": []
        }

        # Generate next actions based on failures
        if self.critical_failures:
            report["next_actions"].append("IMMEDIATE: Fix critical infrastructure failures")
            report["next_actions"].append("ESCALATE: Notify infrastructure team of P0 outage")

        if self.warnings:
            report["next_actions"].append("MEDIUM: Address configuration warnings")

        if not self.critical_failures and not self.warnings:
            report["next_actions"].append("MONITOR: Infrastructure is healthy - focus on application layer")

        return report

    def run_complete_validation(self) -> Dict[str, any]:
        """Run complete infrastructure validation suite."""
        print("🚀 Starting Complete Infrastructure Validation for Issue #1278")
        print("=" * 70)

        # Run all validation checks
        self.validation_results["vpc_connector"] = self.check_vpc_connector()
        self.validation_results["cloud_sql"] = self.check_cloud_sql_instance()
        self.validation_results["secrets"] = self.check_secret_manager_secrets()
        self.validation_results["cloud_run"] = self.check_cloud_run_services()

        # Generate final report
        report = self.generate_report()

        print("\n" + "=" * 70)
        print("📊 INFRASTRUCTURE VALIDATION SUMMARY")
        print("=" * 70)

        print(f"Overall Status: {report['summary']['overall_status']}")
        print(f"Critical Failures: {report['summary']['critical_failures']}")
        print(f"Warnings: {report['summary']['warnings']}")

        if report["critical_failures"]:
            print("\n❌ CRITICAL FAILURES:")
            for failure in report["critical_failures"]:
                print(f"   - {failure}")

        if report["warnings"]:
            print("\n⚠️  WARNINGS:")
            for warning in report["warnings"]:
                print(f"   - {warning}")

        print("\n📋 NEXT ACTIONS:")
        for action in report["next_actions"]:
            print(f"   - {action}")

        return report

def main():
    """Main entry point for infrastructure health check."""
    parser = argparse.ArgumentParser(description="Infrastructure health check for Issue #1278")
    parser.add_argument("--project", default="netra-staging", help="GCP project ID")
    parser.add_argument("--region", default="us-central1", help="GCP region")
    parser.add_argument("--report-only", action="store_true", help="Generate report without fixing")
    parser.add_argument("--fix-mode", action="store_true", help="Attempt to fix issues automatically")

    args = parser.parse_args()

    checker = InfrastructureHealthChecker(args.project, args.region)
    report = checker.run_complete_validation()

    # Save report to file
    report_filename = f"infrastructure_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Report saved to: {report_filename}")

    # Exit with appropriate code
    if report["summary"]["overall_status"] == "CRITICAL":
        print("\n❌ INFRASTRUCTURE VALIDATION FAILED - Critical issues found")
        sys.exit(1)
    else:
        print("\n✅ INFRASTRUCTURE VALIDATION PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()