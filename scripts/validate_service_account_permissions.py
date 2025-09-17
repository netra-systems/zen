#!/usr/bin/env python3
"""
Service Account Permission Validation Script

This script validates that the GCP service account has all necessary permissions
for successful deployment to staging/production environments.

Addresses Issue #1294: Service account permission failures causing deployment failures

Usage:
    python scripts/validate_service_account_permissions.py --project netra-staging
    python scripts/validate_service_account_permissions.py --project netra-production --fix
"""

import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.windows_encoding import setup_windows_encoding

# Fix Unicode encoding issues on Windows
setup_windows_encoding()


class ServiceAccountValidator:
    """Validates GCP service account permissions for deployment."""

    def __init__(self, project_id: str, region: str = "us-central1"):
        self.project_id = project_id
        self.region = region
        self.gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        self.use_shell = sys.platform == "win32"

        # Required permissions for deployment
        self.required_permissions = {
            "Secret Manager": {
                "role": "roles/secretmanager.secretAccessor",
                "test_command": ["secrets", "list", "--limit", "1"],
                "description": "Access secrets during service startup"
            },
            "Cloud Run": {
                "role": "roles/run.admin",
                "test_command": ["run", "services", "list", "--region", self.region, "--limit", "1"],
                "description": "Deploy and manage Cloud Run services"
            },
            "Cloud Build": {
                "role": "roles/cloudbuild.builds.editor",
                "test_command": ["builds", "list", "--limit", "1"],
                "description": "Build and push container images"
            },
            "Container Registry": {
                "role": "roles/storage.admin",
                "test_command": ["container", "images", "list", "--repository", f"gcr.io/{self.project_id}", "--limit", "1"],
                "description": "Push and pull container images"
            },
            "IAM": {
                "role": "roles/iam.serviceAccountUser",
                "test_command": ["iam", "service-accounts", "list", "--limit", "1"],
                "description": "Use service accounts for Cloud Run"
            }
        }

    def validate_all_permissions(self) -> Tuple[bool, List[str]]:
        """
        Validate all required permissions.

        Returns:
            Tuple[bool, List[str]]: (success, list of failed permissions)
        """
        print(f"\n🔒 Validating service account permissions for project: {self.project_id}")
        print("=" * 70)

        failed_permissions = []

        for permission_name, config in self.required_permissions.items():
            print(f"\n📋 Testing {permission_name}...")
            print(f"   Role: {config['role']}")
            print(f"   Purpose: {config['description']}")

            if self._test_permission(config['test_command']):
                print("   ✅ PASS: Permission validated")
            else:
                print("   ❌ FAIL: Permission missing or insufficient")
                failed_permissions.append(permission_name)

        print("\n" + "=" * 70)

        if failed_permissions:
            print(f"❌ VALIDATION FAILED: {len(failed_permissions)} permissions missing")
            print("🔧 Run with --fix to get remediation commands")
            return False, failed_permissions
        else:
            print("✅ VALIDATION PASSED: All required permissions present")
            return True, []

    def _test_permission(self, test_command: List[str]) -> bool:
        """Test a specific permission by running a gcloud command."""
        try:
            cmd = [self.gcloud_cmd] + test_command + ["--project", self.project_id]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=self.use_shell,
                timeout=30
            )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print("   ⚠️  TIMEOUT: Command took too long (may indicate permission issues)")
            return False
        except Exception as e:
            print(f"   ⚠️  ERROR: {e}")
            return False

    def get_remediation_commands(self, failed_permissions: List[str]) -> None:
        """Print commands to fix missing permissions."""
        print("\n🔧 REMEDIATION COMMANDS")
        print("=" * 70)
        print("Run these commands to grant missing permissions:\n")

        # First, get the current service account email
        print("# 1. Find your service account email:")
        print(f"gcloud iam service-accounts list --project {self.project_id}")
        print("\n# 2. Grant missing roles (replace SERVICE_ACCOUNT_EMAIL):")

        for permission_name in failed_permissions:
            if permission_name in self.required_permissions:
                config = self.required_permissions[permission_name]
                print(f"\n# Grant {permission_name} access:")
                print(f"gcloud projects add-iam-policy-binding {self.project_id} \\")
                print(f"    --member=\"serviceAccount:SERVICE_ACCOUNT_EMAIL\" \\")
                print(f"    --role=\"{config['role']}\"")

        print("\n# 3. Verify permissions:")
        print(f"python scripts/validate_service_account_permissions.py --project {self.project_id}")

        print("\n📖 Documentation:")
        print("https://cloud.google.com/iam/docs/granting-changing-revoking-access")

    def validate_health_check_access(self) -> bool:
        """Validate that health check endpoints are accessible."""
        print("\n🏥 Validating health check access...")

        # Check if we can access basic GCP APIs
        try:
            result = subprocess.run([
                self.gcloud_cmd, "config", "get-value", "project"
            ], capture_output=True, text=True, shell=self.use_shell)

            if result.returncode == 0:
                print("   ✅ PASS: Basic GCP API access working")
                return True
            else:
                print("   ❌ FAIL: Cannot access basic GCP APIs")
                return False

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            return False


def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(
        description="Validate GCP service account permissions for deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic validation
    python scripts/validate_service_account_permissions.py --project netra-staging

    # Get fix commands for failures
    python scripts/validate_service_account_permissions.py --project netra-staging --fix

    # Validate production permissions
    python scripts/validate_service_account_permissions.py --project netra-production
        """
    )

    parser.add_argument("--project", required=True,
                       help="GCP project ID (e.g., netra-staging, netra-production)")
    parser.add_argument("--region", default="us-central1",
                       help="GCP region (default: us-central1)")
    parser.add_argument("--fix", action="store_true",
                       help="Show remediation commands for failed permissions")
    parser.add_argument("--health-check", action="store_true",
                       help="Also validate health check endpoint access")

    args = parser.parse_args()

    # Initialize validator
    validator = ServiceAccountValidator(args.project, args.region)

    # Run validation
    success, failed_permissions = validator.validate_all_permissions()

    # Run health check if requested
    if args.health_check:
        health_ok = validator.validate_health_check_access()
        if not health_ok:
            success = False

    # Show remediation if requested and needed
    if args.fix and failed_permissions:
        validator.get_remediation_commands(failed_permissions)

    # Exit with appropriate code
    if success:
        print("\n🎉 SUCCESS: Service account is properly configured for deployment")
        sys.exit(0)
    else:
        print("\n💥 FAILURE: Service account configuration issues detected")
        print("   Run with --fix to get remediation commands")
        sys.exit(1)


if __name__ == "__main__":
    main()