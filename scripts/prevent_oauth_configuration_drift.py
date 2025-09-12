#!/usr/bin/env python3
"""
OAuth Configuration Drift Prevention Script

This script helps prevent OAuth configuration drift by:
1. Validating OAuth secrets exist in Secret Manager
2. Checking auth service health  
3. Creating configuration snapshot for drift detection
4. Providing early warning system for configuration changes

Usage:
    python scripts/prevent_oauth_configuration_drift.py --environment staging
    python scripts/prevent_oauth_configuration_drift.py --environment staging --create-snapshot
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from google.cloud import secretmanager
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

import requests


class OAuthConfigurationDriftDetector:
    """Detects and prevents OAuth configuration drift."""
    
    def __init__(self, environment: str):
        self.environment = environment.lower()
        self.project_id = "netra-staging" if environment == "staging" else "netra-production"
        self.timestamp = datetime.now().isoformat()
        self.config_snapshot = {}
        self.issues_found = []
        self.warnings = []
        
        print(f"OAuth Configuration Drift Detector")
        print(f"Environment: {self.environment}")
        print(f"Project: {self.project_id}")
        print(f"Timestamp: {self.timestamp}")
        print("=" * 60)
    
    def check_secret_manager_accessibility(self) -> bool:
        """Check if Secret Manager is accessible."""
        print(f"\n[GSM] Checking Secret Manager accessibility...")
        
        if not GOOGLE_CLOUD_AVAILABLE:
            self.warnings.append("Google Cloud SDK not available - cannot validate Secret Manager")
            print("  [WARNING] Google Cloud SDK not available")
            return False
        
        try:
            # Try to authenticate using gcloud CLI
            result = subprocess.run(
                ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                active_account = result.stdout.strip()
                print(f"  [OK] Active GCP account: {active_account}")
                return True
            else:
                self.warnings.append("No active GCP authentication found")
                print("  [WARNING] No active GCP authentication")
                return False
                
        except subprocess.TimeoutExpired:
            self.warnings.append("GCP authentication check timed out")
            print("  [WARNING] Authentication check timed out")
            return False
        except Exception as e:
            self.warnings.append(f"GCP authentication check failed: {str(e)}")
            print(f"  [WARNING] Authentication check failed: {e}")
            return False
    
    def validate_oauth_secrets_in_gsm(self) -> Dict[str, Optional[str]]:
        """Validate OAuth secrets exist in Google Secret Manager."""
        print(f"\n[SECRETS] Validating OAuth secrets in Secret Manager...")
        
        if not self.check_secret_manager_accessibility():
            return {}
        
        # Expected secrets for staging
        expected_secrets = [
            "google-oauth-client-id-staging",
            "google-oauth-client-secret-staging"
        ] if self.environment == "staging" else [
            "google-client-id-production",
            "google-client-secret-production"
        ]
        
        secrets_status = {}
        
        try:
            client = secretmanager.SecretManagerServiceClient()
            
            for secret_name in expected_secrets:
                try:
                    name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                    response = client.access_secret_version(request={"name": name})
                    secret_value = response.payload.data.decode("UTF-8")
                    
                    # Validate secret value quality
                    if secret_value.startswith("REPLACE_") or len(secret_value) < 10:
                        self.issues_found.append(f"Secret '{secret_name}' appears to be a placeholder or invalid")
                        secrets_status[secret_name] = "PLACEHOLDER"
                        print(f"  [FAIL] {secret_name}: PLACEHOLDER/INVALID")
                    else:
                        secrets_status[secret_name] = "VALID"
                        if "client-id" in secret_name:
                            print(f"  [OK] {secret_name}: {secret_value[:30]}...")
                        else:
                            print(f"  [OK] {secret_name}: [VALID - {len(secret_value)} chars]")
                            
                except Exception as e:
                    self.issues_found.append(f"Cannot access secret '{secret_name}': {str(e)}")
                    secrets_status[secret_name] = "MISSING"
                    print(f"  [FAIL] {secret_name}: {str(e)}")
                    
        except Exception as e:
            self.issues_found.append(f"Secret Manager connection failed: {str(e)}")
            print(f"  [FAIL] Secret Manager connection: {e}")
        
        return secrets_status
    
    def check_auth_service_health(self) -> Dict[str, any]:
        """Check the health of the auth service."""
        print(f"\n[SERVICE] Checking Auth Service health...")
        
        if self.environment == "staging":
            auth_url = "https://netra-auth-service-pnovr5vsba-uc.a.run.app"
        else:
            auth_url = "https://netra-auth-service-production-url"  # Update as needed
        
        health_status = {
            "url": auth_url,
            "status": "UNKNOWN",
            "response_time": None,
            "details": {}
        }
        
        try:
            start_time = time.time()
            response = requests.get(f"{auth_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            health_status["response_time"] = round(response_time, 3)
            
            if response.status_code == 200:
                health_data = response.json()
                health_status["status"] = "HEALTHY"
                health_status["details"] = health_data
                print(f"  [OK] Auth Service: HEALTHY ({response_time:.3f}s)")
                print(f"    Status: {health_data.get('status', 'unknown')}")
                print(f"    Environment: {health_data.get('environment', 'unknown')}")
                print(f"    Database: {health_data.get('database_status', 'unknown')}")
            else:
                health_status["status"] = "UNHEALTHY"
                self.issues_found.append(f"Auth service returned HTTP {response.status_code}")
                print(f"  [FAIL] Auth Service: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            health_status["status"] = "TIMEOUT"
            self.issues_found.append("Auth service health check timed out")
            print("  [FAIL] Auth Service: TIMEOUT")
        except Exception as e:
            health_status["status"] = "ERROR"
            self.issues_found.append(f"Auth service health check failed: {str(e)}")
            print(f"  [FAIL] Auth Service: {e}")
        
        return health_status
    
    def check_cloud_run_revisions(self) -> Dict[str, any]:
        """Check Cloud Run service revisions and traffic allocation."""
        print(f"\n[CLOUDRUN] Checking Cloud Run revisions...")
        
        revision_info = {
            "service": "netra-auth-service",
            "project": self.project_id,
            "region": "us-central1",
            "traffic": {},
            "status": "UNKNOWN"
        }
        
        try:
            # Get traffic allocation
            result = subprocess.run([
                "gcloud", "run", "services", "describe", "netra-auth-service",
                "--project", self.project_id,
                "--region", "us-central1",
                "--format", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                service_info = json.loads(result.stdout)
                traffic = service_info.get("status", {}).get("traffic", [])
                
                for traffic_item in traffic:
                    revision = traffic_item.get("revisionName", "unknown")
                    percent = traffic_item.get("percent", 0)
                    revision_info["traffic"][revision] = percent
                    print(f"  [INFO] {revision}: {percent}% traffic")
                
                revision_info["status"] = "AVAILABLE"
                
                # Check if traffic is concentrated on working revision
                if any(percent == 100 for percent in revision_info["traffic"].values()):
                    print("  [OK] Traffic fully allocated to single revision")
                else:
                    self.warnings.append("Traffic split across multiple revisions")
                    print("  [WARNING] Traffic split detected")
                    
            else:
                revision_info["status"] = "ERROR"
                self.warnings.append(f"Could not retrieve Cloud Run info: {result.stderr}")
                print(f"  [WARNING] Could not retrieve Cloud Run info")
                
        except Exception as e:
            revision_info["status"] = "ERROR"
            self.warnings.append(f"Cloud Run check failed: {str(e)}")
            print(f"  [WARNING] Cloud Run check failed: {e}")
        
        return revision_info
    
    def create_configuration_snapshot(self) -> Dict[str, any]:
        """Create a comprehensive configuration snapshot."""
        print(f"\n[SNAPSHOT] Creating configuration snapshot...")
        
        snapshot = {
            "timestamp": self.timestamp,
            "environment": self.environment,
            "project_id": self.project_id,
            "secret_manager": self.validate_oauth_secrets_in_gsm(),
            "auth_service": self.check_auth_service_health(),
            "cloud_run": self.check_cloud_run_revisions(),
            "issues": self.issues_found,
            "warnings": self.warnings
        }
        
        return snapshot
    
    def save_snapshot(self, snapshot: Dict[str, any], filename: Optional[str] = None) -> str:
        """Save configuration snapshot to file."""
        if not filename:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"oauth_config_snapshot_{self.environment}_{timestamp_str}.json"
        
        snapshot_path = Path(__file__).parent.parent / "config" / "snapshots" / filename
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        print(f"  [SAVED] Configuration snapshot: {snapshot_path}")
        return str(snapshot_path)
    
    def generate_drift_report(self, snapshot: Dict[str, any]) -> str:
        """Generate drift detection report."""
        report_lines = [
            "OAuth Configuration Drift Report",
            f"Environment: {self.environment}",
            f"Timestamp: {self.timestamp}",
            f"Project: {self.project_id}",
            "=" * 60
        ]
        
        # Summary
        total_issues = len(self.issues_found)
        total_warnings = len(self.warnings)
        
        if total_issues == 0 and total_warnings == 0:
            report_lines.extend([
                "",
                "[SUCCESS] No configuration drift detected",
                "All OAuth configuration components are healthy and consistent."
            ])
        else:
            if total_issues > 0:
                report_lines.extend([
                    "",
                    f"[ISSUES] {total_issues} configuration issues found:",
                    "-" * 40
                ])
                for i, issue in enumerate(self.issues_found, 1):
                    report_lines.append(f"{i}. {issue}")
            
            if total_warnings > 0:
                report_lines.extend([
                    "",
                    f"[WARNINGS] {total_warnings} warnings:",
                    "-" * 40
                ])
                for i, warning in enumerate(self.warnings, 1):
                    report_lines.append(f"{i}. {warning}")
        
        # Component status
        report_lines.extend([
            "",
            "Component Status:",
            "-" * 20
        ])
        
        secrets = snapshot.get("secret_manager", {})
        if secrets:
            report_lines.append(f"Secret Manager: {len([s for s in secrets.values() if s == 'VALID'])} valid secrets")
        else:
            report_lines.append("Secret Manager: Not accessible")
        
        auth_status = snapshot.get("auth_service", {}).get("status", "UNKNOWN")
        report_lines.append(f"Auth Service: {auth_status}")
        
        cloudrun_status = snapshot.get("cloud_run", {}).get("status", "UNKNOWN")  
        report_lines.append(f"Cloud Run: {cloudrun_status}")
        
        report_lines.extend([
            "",
            "=" * 60,
            f"Report generated: {self.timestamp}"
        ])
        
        return "\n".join(report_lines)
    
    def run_drift_detection(self, create_snapshot: bool = False) -> Tuple[bool, str]:
        """Run complete configuration drift detection."""
        print(f"[DRIFT] Starting OAuth configuration drift detection...")
        
        try:
            snapshot = self.create_configuration_snapshot()
            
            if create_snapshot:
                self.save_snapshot(snapshot)
            
            report = self.generate_drift_report(snapshot)
            
            # Determine success - no critical issues (warnings are OK)
            success = len(self.issues_found) == 0
            
            return success, report
            
        except Exception as e:
            error_report = f"""
[CRITICAL] OAuth Configuration Drift Detection FAILED

Environment: {self.environment}
Error: {str(e)}

This indicates a critical system configuration issue.
Manual investigation required.
"""
            return False, error_report


def main():
    """Main entry point for OAuth configuration drift prevention."""
    parser = argparse.ArgumentParser(description="Prevent OAuth configuration drift")
    parser.add_argument(
        "--environment",
        choices=["staging", "production"],
        required=True,
        help="Target environment"
    )
    parser.add_argument(
        "--create-snapshot",
        action="store_true",
        help="Save configuration snapshot to file"
    )
    parser.add_argument(
        "--output-report",
        help="Output file for drift report"
    )
    
    args = parser.parse_args()
    
    # Run drift detection
    detector = OAuthConfigurationDriftDetector(args.environment)
    success, report = detector.run_drift_detection(create_snapshot=args.create_snapshot)
    
    # Print report
    print("\n" + report)
    
    # Save report if requested
    if args.output_report:
        with open(args.output_report, 'w') as f:
            f.write(report)
        print(f"\n[SAVED] Report saved to: {args.output_report}")
    
    # Exit based on results
    if success:
        print(f"\n[SUCCESS] OAuth configuration drift detection PASSED")
        print("No critical configuration drift detected.")
        sys.exit(0)
    else:
        print(f"\n[FAILURE] OAuth configuration drift detection FAILED")
        print("Critical configuration issues found - manual review required.")
        sys.exit(1)


if __name__ == "__main__":
    main()