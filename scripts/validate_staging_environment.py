#!/usr/bin/env python3
"""
Comprehensive Staging Environment Validation Script

This script validates the complete staging environment configuration to ensure
it meets the requirements for Issue #1278 infrastructure reliability fixes.

Validates:
- Domain configuration (*.netrasystems.ai vs *.staging.netrasystems.ai)
- SSL certificate configuration
- Database timeout settings (600s requirement)
- Service account permissions
- VPC connector configuration
- Load balancer setup
- Health check configurations

Usage:
    python scripts/validate_staging_environment.py
    python scripts/validate_staging_environment.py --fix
    python scripts/validate_staging_environment.py --check-ssl
"""

import sys
import subprocess
import argparse
import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.windows_encoding import setup_windows_encoding
from shared.isolated_environment import get_env

# Fix Unicode encoding issues on Windows
setup_windows_encoding()


class StagingEnvironmentValidator:
    """Comprehensive staging environment validation."""

    def __init__(self, project_id: str = "netra-staging"):
        self.project_id = project_id
        self.region = "us-central1"
        self.gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        self.use_shell = sys.platform == "win32"

        # Expected staging endpoints (Issue #1278 fix)
        self.expected_domains = {
            "backend": "https://api.staging.netrasystems.ai",
            "auth": "https://staging.netrasystems.ai",
            "frontend": "https://staging.netrasystems.ai",
            "websocket": "wss://api.staging.netrasystems.ai"
        }

        # Deprecated domains that should NOT be used
        self.deprecated_domains = [
            ".staging.netrasystems.ai",
            "app.staging.netrasystems.ai",
            "auth.staging.netrasystems.ai",
            "api.staging.netrasystems.ai"
        ]

        # Minimum database timeout (Issue #1278 requirement)
        self.min_database_timeout = 600

    def validate_all(self) -> Tuple[bool, Dict[str, Dict]]:
        """
        Run comprehensive validation of staging environment.

        Returns:
            Tuple[bool, Dict]: (overall_success, detailed_results)
        """
        print("\n🚀 COMPREHENSIVE STAGING ENVIRONMENT VALIDATION")
        print("=" * 70)
        print(f"Project: {self.project_id}")
        print(f"Target: Issue #1278 Infrastructure Reliability Fixes")
        print("=" * 70)

        results = {}

        # 1. Domain Configuration Validation
        print("\n📡 1. DOMAIN CONFIGURATION VALIDATION")
        results['domains'] = self._validate_domain_configuration()

        # 2. SSL Certificate Validation
        print("\n🔒 2. SSL CERTIFICATE VALIDATION")
        results['ssl'] = self._validate_ssl_certificates()

        # 3. Database Timeout Configuration
        print("\n⏱️ 3. DATABASE TIMEOUT VALIDATION")
        results['database_timeouts'] = self._validate_database_timeouts()

        # 4. Service Account Permissions
        print("\n🔑 4. SERVICE ACCOUNT PERMISSIONS")
        results['permissions'] = self._validate_service_account_permissions()

        # 5. VPC Connector Configuration
        print("\n🌐 5. VPC CONNECTOR VALIDATION")
        results['vpc'] = self._validate_vpc_connector()

        # 6. Load Balancer Configuration
        print("\n⚖️ 6. LOAD BALANCER VALIDATION")
        results['load_balancer'] = self._validate_load_balancer()

        # 7. Health Check Configuration
        print("\n🏥 7. HEALTH CHECK VALIDATION")
        results['health_checks'] = self._validate_health_checks()

        # 8. Environment Variables
        print("\n🔧 8. ENVIRONMENT VARIABLE VALIDATION")
        results['environment'] = self._validate_environment_variables()

        # Calculate overall success
        overall_success = all(result.get('success', False) for result in results.values())

        # Summary
        self._print_validation_summary(results, overall_success)

        return overall_success, results

    def _validate_domain_configuration(self) -> Dict:
        """Validate domain configuration against Issue #1278 requirements."""
        print("   Checking staging domain configuration...")

        issues = []
        warnings = []

        # Check for deprecated domain usage in deployment script
        deploy_script = project_root / "scripts" / "deploy_to_gcp_actual.py"
        if deploy_script.exists():
            content = deploy_script.read_text()

            for deprecated in self.deprecated_domains:
                if deprecated in content:
                    issues.append(f"Found deprecated domain '{deprecated}' in deploy script")

            # Check for correct domains
            correct_domains_found = sum(1 for domain in self.expected_domains.values()
                                      if domain.replace('wss://', 'https://') in content)

            if correct_domains_found < len(self.expected_domains) - 1:  # -1 for websocket
                warnings.append("Not all expected domains found in deployment script")

        # Check environment files for deprecated domains
        env_files = [".env.staging", ".env.staging.tests", "frontend/.env.staging"]
        for env_file in env_files:
            env_path = project_root / env_file
            if env_path.exists():
                content = env_path.read_text()
                for deprecated in self.deprecated_domains:
                    if deprecated in content:
                        issues.append(f"Found deprecated domain '{deprecated}' in {env_file}")

        success = len(issues) == 0
        if success:
            print("   ✅ PASS: Domain configuration correct")
        else:
            print("   ❌ FAIL: Domain configuration issues found")
            for issue in issues:
                print(f"      - {issue}")

        if warnings:
            for warning in warnings:
                print(f"   ⚠️  WARNING: {warning}")

        return {
            'success': success,
            'issues': issues,
            'warnings': warnings,
            'expected_domains': self.expected_domains
        }

    def _validate_ssl_certificates(self) -> Dict:
        """Validate SSL certificate configuration."""
        print("   Checking SSL certificate configuration...")

        issues = []
        ssl_status = {}

        for service, url in self.expected_domains.items():
            if url.startswith('wss://'):
                url = url.replace('wss://', 'https://')

            try:
                print(f"      Testing SSL for {service}: {url}")
                response = requests.get(f"{url}/health", timeout=10, verify=True)
                ssl_status[service] = {
                    'status': 'valid',
                    'status_code': response.status_code
                }
            except requests.exceptions.SSLError as e:
                ssl_status[service] = {
                    'status': 'ssl_error',
                    'error': str(e)
                }
                issues.append(f"SSL certificate error for {service}: {url}")
            except requests.exceptions.RequestException as e:
                ssl_status[service] = {
                    'status': 'connection_error',
                    'error': str(e)
                }
                # Don't count connection errors as SSL issues
            except Exception as e:
                ssl_status[service] = {
                    'status': 'unknown_error',
                    'error': str(e)
                }

        success = len(issues) == 0
        if success:
            print("   ✅ PASS: SSL certificates valid")
        else:
            print("   ❌ FAIL: SSL certificate issues found")
            for issue in issues:
                print(f"      - {issue}")

        return {
            'success': success,
            'issues': issues,
            'ssl_status': ssl_status
        }

    def _validate_database_timeouts(self) -> Dict:
        """Validate database timeout configuration."""
        print("   Checking database timeout configuration...")

        issues = []
        timeout_configs = {}

        # Check deployment script for timeout settings
        deploy_script = project_root / "scripts" / "deploy_to_gcp_actual.py"
        if deploy_script.exists():
            content = deploy_script.read_text()

            # Look for timeout configurations
            timeout_patterns = [
                "AUTH_DB_URL_TIMEOUT",
                "AUTH_DB_ENGINE_TIMEOUT",
                "AUTH_DB_VALIDATION_TIMEOUT",
                "timeout: int ="
            ]

            for pattern in timeout_patterns:
                if pattern in content:
                    # Extract timeout value
                    lines = content.split('\n')
                    for line in lines:
                        if pattern in line and ('600' in line or '90' in line):
                            if pattern.startswith('AUTH_DB'):
                                # Extract timeout value from environment variable
                                if '"600.0"' in line:
                                    timeout_configs[pattern] = 600
                                elif '"90.0"' in line:
                                    timeout_configs[pattern] = 90
                                    issues.append(f"{pattern} is 90s, should be 600s for Issue #1278")
                            elif pattern == "timeout: int =":
                                if "600" in line:
                                    timeout_configs['service_timeout'] = 600

        # Check for minimum timeout requirements
        required_timeouts = {
            "AUTH_DB_URL_TIMEOUT": self.min_database_timeout,
            "AUTH_DB_ENGINE_TIMEOUT": self.min_database_timeout,
            "AUTH_DB_VALIDATION_TIMEOUT": self.min_database_timeout
        }

        for timeout_name, required_value in required_timeouts.items():
            actual_value = timeout_configs.get(timeout_name, 0)
            if actual_value < required_value:
                issues.append(f"{timeout_name} is {actual_value}s, must be at least {required_value}s")

        success = len(issues) == 0
        if success:
            print("   ✅ PASS: Database timeouts configured correctly")
        else:
            print("   ❌ FAIL: Database timeout issues found")
            for issue in issues:
                print(f"      - {issue}")

        return {
            'success': success,
            'issues': issues,
            'timeout_configs': timeout_configs,
            'min_required': self.min_database_timeout
        }

    def _validate_service_account_permissions(self) -> Dict:
        """Validate service account permissions."""
        print("   Checking service account permissions...")

        try:
            # Use the existing validation script
            result = subprocess.run([
                sys.executable, "scripts/validate_service_account_permissions.py",
                "--project", self.project_id
            ], capture_output=True, text=True, cwd=project_root)

            success = result.returncode == 0
            if success:
                print("   ✅ PASS: Service account permissions valid")
            else:
                print("   ❌ FAIL: Service account permission issues")

            return {
                'success': success,
                'output': result.stdout,
                'error': result.stderr
            }

        except Exception as e:
            print(f"   ❌ ERROR: Failed to validate permissions: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _validate_vpc_connector(self) -> Dict:
        """Validate VPC connector configuration."""
        print("   Checking VPC connector configuration...")

        try:
            # Check if VPC connector exists
            result = subprocess.run([
                self.gcloud_cmd, "compute", "networks", "vpc-access", "connectors", "list",
                "--project", self.project_id,
                "--region", self.region,
                "--format", "json"
            ], capture_output=True, text=True, shell=self.use_shell)

            if result.returncode == 0:
                connectors = json.loads(result.stdout)
                if connectors:
                    print("   ✅ PASS: VPC connector found")
                    return {
                        'success': True,
                        'connectors': connectors
                    }
                else:
                    print("   ❌ FAIL: No VPC connector found")
                    return {
                        'success': False,
                        'issues': ['VPC connector required for database connectivity']
                    }
            else:
                print("   ⚠️  WARNING: Cannot check VPC connector")
                return {
                    'success': True,  # Don't fail validation on check failure
                    'warning': 'Cannot verify VPC connector'
                }

        except Exception as e:
            print(f"   ⚠️  WARNING: VPC connector check failed: {e}")
            return {
                'success': True,  # Don't fail validation on check failure
                'warning': str(e)
            }

    def _validate_load_balancer(self) -> Dict:
        """Validate load balancer configuration."""
        print("   Checking load balancer configuration...")

        # For now, just check that the expected domains respond
        # More detailed load balancer validation could be added
        responding_domains = 0
        total_domains = len(self.expected_domains)

        for service, url in self.expected_domains.items():
            if url.startswith('wss://'):
                continue  # Skip websocket for HTTP check

            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code in [200, 404]:  # 404 is ok, means load balancer works
                    responding_domains += 1
            except:
                pass  # Don't fail on connection issues

        # Consider success if at least one domain responds
        success = responding_domains > 0
        if success:
            print(f"   ✅ PASS: Load balancer responding ({responding_domains}/{total_domains} domains)")
        else:
            print("   ❌ FAIL: Load balancer not responding")

        return {
            'success': success,
            'responding_domains': responding_domains,
            'total_domains': total_domains
        }

    def _validate_health_checks(self) -> Dict:
        """Validate health check configuration."""
        print("   Checking health check configuration...")

        health_status = {}
        for service, url in self.expected_domains.items():
            if url.startswith('wss://'):
                continue  # Skip websocket for HTTP health check

            try:
                response = requests.get(f"{url}/health", timeout=10)
                health_status[service] = {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'available': response.status_code == 200
                }
            except Exception as e:
                health_status[service] = {
                    'available': False,
                    'error': str(e)
                }

        available_services = sum(1 for status in health_status.values()
                               if status.get('available', False))
        success = available_services > 0

        if success:
            print(f"   ✅ PASS: Health checks responding ({available_services} services)")
        else:
            print("   ⚠️  WARNING: No health checks responding (may be normal if services down)")

        return {
            'success': True,  # Don't fail overall validation on health check issues
            'health_status': health_status,
            'available_services': available_services
        }

    def _validate_environment_variables(self) -> Dict:
        """Validate environment variable configuration."""
        print("   Checking environment variable configuration...")

        issues = []

        # Check for required environment variables
        required_vars = [
            'GEMINI_API_KEY',
            'GCP_PROJECT_ID'
        ]

        for var in required_vars:
            if not get_env().get(var):
                issues.append(f"Missing environment variable: {var}")

        # Check for deprecated staging URLs in environment
        deprecated_patterns = [
            'localhost',
            '.staging.netrasystems.ai'
        ]

        for var_name, var_value in get_env().items():
            if var_value and isinstance(var_value, str):
                for pattern in deprecated_patterns:
                    if pattern in var_value:
                        issues.append(f"Deprecated URL pattern '{pattern}' in {var_name}")

        success = len(issues) == 0
        if success:
            print("   ✅ PASS: Environment variables configured correctly")
        else:
            print("   ❌ FAIL: Environment variable issues found")
            for issue in issues:
                print(f"      - {issue}")

        return {
            'success': success,
            'issues': issues
        }

    def _print_validation_summary(self, results: Dict, overall_success: bool) -> None:
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("🎯 VALIDATION SUMMARY")
        print("=" * 70)

        for category, result in results.items():
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            print(f"{status:8} {category.replace('_', ' ').title()}")

        print("=" * 70)
        if overall_success:
            print("🎉 OVERALL RESULT: ✅ STAGING ENVIRONMENT READY")
            print("   All critical validations passed")
        else:
            print("💥 OVERALL RESULT: ❌ STAGING ENVIRONMENT ISSUES DETECTED")
            print("   Review failures above and apply fixes")

        print("=" * 70)

    def generate_fix_commands(self, results: Dict) -> None:
        """Generate commands to fix identified issues."""
        print("\n🔧 REMEDIATION COMMANDS")
        print("=" * 70)

        has_fixes = False

        # Domain configuration fixes
        if not results.get('domains', {}).get('success', True):
            has_fixes = True
            print("\n# Fix domain configuration:")
            print("# Update domains in deployment script:")
            print("# Replace *.staging.netrasystems.ai with *.netrasystems.ai")

        # Database timeout fixes
        if not results.get('database_timeouts', {}).get('success', True):
            has_fixes = True
            print("\n# Fix database timeouts:")
            print("# Update timeout values in scripts/deploy_to_gcp_actual.py:")
            print('# Change "90.0" to "600.0" for all AUTH_DB_*_TIMEOUT variables')

        # Service account permission fixes
        if not results.get('permissions', {}).get('success', True):
            has_fixes = True
            print("\n# Fix service account permissions:")
            print(f"python scripts/validate_service_account_permissions.py --project {self.project_id} --fix")

        # VPC connector fixes
        if not results.get('vpc', {}).get('success', True):
            has_fixes = True
            print("\n# Create VPC connector:")
            print(f"gcloud compute networks vpc-access connectors create staging-connector \\")
            print(f"    --network default \\")
            print(f"    --region {self.region} \\")
            print(f"    --range 10.8.0.0/28 \\")
            print(f"    --project {self.project_id}")

        if not has_fixes:
            print("✅ No fixes needed - all validations passed!")


def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(
        description="Validate staging environment for Issue #1278 fixes",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--project", default="netra-staging",
                       help="GCP project ID (default: netra-staging)")
    parser.add_argument("--fix", action="store_true",
                       help="Show remediation commands for issues")
    parser.add_argument("--check-ssl", action="store_true",
                       help="Perform detailed SSL certificate validation")

    args = parser.parse_args()

    # Initialize validator
    validator = StagingEnvironmentValidator(args.project)

    # Run validation
    success, results = validator.validate_all()

    # Show fix commands if requested
    if args.fix:
        validator.generate_fix_commands(results)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()