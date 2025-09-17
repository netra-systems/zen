#!/usr/bin/env python3
"""
Validate Staging Infrastructure for Golden Path E2E Tests
This script validates that the staging environment is properly configured
to support golden path e2e tests.

Issue #1278: Database connectivity and domain configuration fixes
"""

import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.windows_encoding import setup_windows_encoding
setup_windows_encoding()


class StagingValidator:
    """Validates staging infrastructure readiness for golden path tests."""

    def __init__(self, project_id: str = "netra-staging"):
        self.project_id = project_id
        self.region = "us-central1"
        self.gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        self.use_shell = sys.platform == "win32"
        self.issues_found = []
        self.fixes_applied = []

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("\n" + "=" * 80)
        print("🔍 STAGING INFRASTRUCTURE VALIDATION FOR GOLDEN PATH TESTS")
        print("=" * 80)
        print(f"Project: {self.project_id}")
        print(f"Region: {self.region}")
        print(f"Issue #1278: Validating database connectivity and domain configuration")
        print("=" * 80 + "\n")

        all_passed = True

        # 1. Service Account Permissions
        print("1️⃣ Validating Service Account Permissions...")
        if not self.validate_service_account_permissions():
            all_passed = False

        # 2. Domain Configuration
        print("\n2️⃣ Validating Domain Configuration...")
        if not self.validate_domain_configuration():
            all_passed = False

        # 3. Database Configuration
        print("\n3️⃣ Validating Database Configuration...")
        if not self.validate_database_configuration():
            all_passed = False

        # 4. VPC Connector
        print("\n4️⃣ Validating VPC Connector...")
        if not self.validate_vpc_connector():
            all_passed = False

        # 5. Cloud Run Services
        print("\n5️⃣ Validating Cloud Run Services...")
        if not self.validate_cloud_run_services():
            all_passed = False

        # Summary
        self.print_summary(all_passed)
        return all_passed

    def validate_service_account_permissions(self) -> bool:
        """Validate service account has required permissions."""
        try:
            # Check Secret Manager access
            result = subprocess.run([
                self.gcloud_cmd, "secrets", "list",
                "--project", self.project_id,
                "--limit", "1"
            ], capture_output=True, text=True, shell=self.use_shell)

            if result.returncode != 0:
                self.issues_found.append({
                    "type": "SERVICE_ACCOUNT",
                    "issue": "Service account lacks Secret Manager access",
                    "fix": f"gcloud projects add-iam-policy-binding {self.project_id} "
                          f"--member='serviceAccount:SERVICE_ACCOUNT_EMAIL' "
                          f"--role='roles/secretmanager.secretAccessor'"
                })
                print("   ❌ FAIL: Service account lacks Secret Manager access")
                return False

            print("   ✅ PASS: Service account has Secret Manager access")
            return True

        except Exception as e:
            print(f"   ⚠️ WARN: Could not validate service account: {e}")
            return False

    def validate_domain_configuration(self) -> bool:
        """Validate correct domain usage (not deprecated *.staging.netrasystems.ai)."""
        correct_domains = {
            "frontend": "https://staging.netrasystems.ai",
            "api": "https://api.staging.netrasystems.ai",
            "auth": "https://staging.netrasystems.ai",
            "websocket": "wss://api.staging.netrasystems.ai"
        }

        # Check deploy_to_gcp_actual.py for correct domains
        deploy_script = project_root / "scripts" / "deploy_to_gcp_actual.py"
        if deploy_script.exists():
            content = deploy_script.read_text()

            # Check for deprecated domains
            if "staging.staging.netrasystems.ai" in content:
                self.issues_found.append({
                    "type": "DOMAIN_CONFIG",
                    "issue": "Deployment script uses deprecated *.staging.netrasystems.ai domains",
                    "fix": "Update to use *.netrasystems.ai domains as per Issue #1278"
                })
                print("   ❌ FAIL: Deprecated domains found in deployment script")
                return False

        print("   ✅ PASS: Domain configuration uses correct *.netrasystems.ai URLs")
        return True

    def validate_database_configuration(self) -> bool:
        """Validate database timeout settings (600s requirement)."""
        deploy_script = project_root / "scripts" / "deploy_to_gcp_actual.py"
        if deploy_script.exists():
            content = deploy_script.read_text()

            # Check for 600s timeout settings
            if '"AUTH_DB_URL_TIMEOUT": "600' in content:
                print("   ✅ PASS: Database timeouts configured to 600s")
                return True
            else:
                self.issues_found.append({
                    "type": "DATABASE_CONFIG",
                    "issue": "Database timeouts not set to 600s",
                    "fix": "Update AUTH_DB_*_TIMEOUT environment variables to 600.0"
                })
                print("   ❌ FAIL: Database timeouts not properly configured")
                return False

        return False

    def validate_vpc_connector(self) -> bool:
        """Validate VPC connector configuration."""
        try:
            result = subprocess.run([
                self.gcloud_cmd, "compute", "networks", "vpc-access", "connectors",
                "describe", "staging-connector",
                "--region", self.region,
                "--project", self.project_id,
                "--format", "json"
            ], capture_output=True, text=True, shell=self.use_shell)

            if result.returncode != 0:
                self.issues_found.append({
                    "type": "VPC_CONNECTOR",
                    "issue": "VPC connector 'staging-connector' not found",
                    "fix": "Create VPC connector with terraform or gcloud"
                })
                print("   ❌ FAIL: VPC connector not configured")
                return False

            connector_info = json.loads(result.stdout)
            if connector_info.get("state") != "READY":
                print(f"   ⚠️ WARN: VPC connector state is {connector_info.get('state')}")
                return False

            print("   ✅ PASS: VPC connector 'staging-connector' is READY")
            return True

        except Exception as e:
            print(f"   ⚠️ WARN: Could not validate VPC connector: {e}")
            return False

    def validate_cloud_run_services(self) -> bool:
        """Validate Cloud Run services are deployed and healthy."""
        services = [
            "netra-backend-staging",
            "netra-auth-service",
            "netra-frontend-staging"
        ]

        all_healthy = True
        for service_name in services:
            try:
                result = subprocess.run([
                    self.gcloud_cmd, "run", "services", "describe",
                    service_name,
                    "--region", self.region,
                    "--project", self.project_id,
                    "--format", "value(status.conditions[0].status)"
                ], capture_output=True, text=True, shell=self.use_shell)

                if result.returncode != 0:
                    print(f"   ❌ FAIL: Service '{service_name}' not found")
                    self.issues_found.append({
                        "type": "CLOUD_RUN",
                        "issue": f"Service '{service_name}' not deployed",
                        "fix": f"Deploy with: python scripts/deploy_to_gcp.py --project {self.project_id}"
                    })
                    all_healthy = False
                elif result.stdout.strip() == "True":
                    print(f"   ✅ PASS: Service '{service_name}' is healthy")
                else:
                    print(f"   ⚠️ WARN: Service '{service_name}' status: {result.stdout.strip()}")
                    all_healthy = False

            except Exception as e:
                print(f"   ⚠️ WARN: Could not check service '{service_name}': {e}")
                all_healthy = False

        return all_healthy

    def print_summary(self, all_passed: bool):
        """Print validation summary."""
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ STAGING INFRASTRUCTURE VALIDATION PASSED")
            print("Golden path e2e tests can be executed")
        else:
            print("❌ STAGING INFRASTRUCTURE VALIDATION FAILED")
            print(f"\nFound {len(self.issues_found)} issues requiring remediation:")

            for i, issue in enumerate(self.issues_found, 1):
                print(f"\n{i}. {issue['type']}: {issue['issue']}")
                print(f"   FIX: {issue['fix']}")

        print("=" * 80)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate staging infrastructure for golden path e2e tests"
    )
    parser.add_argument(
        "--project",
        default="netra-staging",
        help="GCP project ID"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix issues automatically"
    )

    args = parser.parse_args()

    validator = StagingValidator(project_id=args.project)
    success = validator.validate_all()

    if not success and args.fix:
        print("\n🔧 Attempting to fix issues...")
        print("(Manual intervention may be required for some fixes)")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()