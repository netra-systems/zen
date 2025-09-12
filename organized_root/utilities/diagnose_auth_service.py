#!/usr/bin/env python3
"""
Auth Service Diagnostic Tool
Diagnoses and fixes common auth service deployment issues
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests


class AuthServiceDiagnostic:
    """Comprehensive diagnostic tool for auth service issues"""
    
    def __init__(self, project_id: str = "netra-staging", region: str = "us-central1"):
        self.project_id = project_id
        self.region = region
        self.service_name = "netra-auth-service"
        self.issues_found = []
        self.fixes_applied = []
        
    def run_command(self, cmd: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """Execute command and return result"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def check_gcp_auth(self) -> bool:
        """Verify GCP authentication"""
        print(" SEARCH:  Checking GCP authentication...")
        returncode, stdout, stderr = self.run_command(["gcloud", "auth", "print-access-token"])
        
        if returncode != 0:
            self.issues_found.append("GCP authentication not configured")
            print("   FAIL:  Not authenticated with GCP")
            return False
        
        print("   PASS:  GCP authentication valid")
        return True
    
    def check_service_status(self) -> Dict:
        """Check Cloud Run service status"""
        print("\n SEARCH:  Checking Cloud Run service status...")
        
        cmd = [
            "gcloud", "run", "services", "describe",
            self.service_name,
            f"--region={self.region}",
            f"--project={self.project_id}",
            "--format=json"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd)
        
        if returncode != 0:
            self.issues_found.append("Service not found or inaccessible")
            print(f"   FAIL:  Service {self.service_name} not found")
            return {}
        
        try:
            service_info = json.loads(stdout)
            status = service_info.get("status", {})
            
            # Check service URL
            url = status.get("url", "")
            if url:
                print(f"   PASS:  Service URL: {url}")
            else:
                print("   WARNING: [U+FE0F]  No service URL found")
                self.issues_found.append("Service URL not available")
            
            # Check latest revision
            latest_revision = status.get("latestCreatedRevisionName", "")
            if latest_revision:
                print(f"   PASS:  Latest revision: {latest_revision}")
            
            # Check traffic allocation
            traffic = status.get("traffic", [])
            if traffic:
                print(f"   PASS:  Traffic allocation configured")
            
            return service_info
            
        except json.JSONDecodeError:
            self.issues_found.append("Failed to parse service info")
            print("   FAIL:  Failed to parse service information")
            return {}
    
    def check_recent_logs(self) -> List[str]:
        """Check recent error logs"""
        print("\n SEARCH:  Checking recent error logs...")
        
        # Get logs from last 30 minutes
        timestamp = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat() + "Z"
        
        cmd = [
            "gcloud", "logging", "read",
            f'resource.type="cloud_run_revision" AND '
            f'resource.labels.service_name="{self.service_name}" AND '
            f'severity>=ERROR AND '
            f'timestamp>="{timestamp}"',
            "--limit=10",
            f"--project={self.project_id}",
            "--format=json"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd)
        
        errors = []
        if returncode == 0 and stdout:
            try:
                logs = json.loads(stdout)
                for log in logs:
                    payload = log.get("textPayload", "") or log.get("jsonPayload", {})
                    if payload:
                        errors.append(str(payload))
                        
                if errors:
                    print(f"   WARNING: [U+FE0F]  Found {len(errors)} recent errors:")
                    for i, error in enumerate(errors[:3], 1):
                        # Truncate long errors
                        if len(error) > 200:
                            error = error[:200] + "..."
                        print(f"     {i}. {error}")
                    
                    # Analyze common error patterns
                    self.analyze_error_patterns(errors)
                else:
                    print("   PASS:  No recent errors found")
                    
            except json.JSONDecodeError:
                print("   WARNING: [U+FE0F]  Failed to parse logs")
        else:
            print("  [U+2139][U+FE0F]  No logs available or access denied")
        
        return errors
    
    def analyze_error_patterns(self, errors: List[str]):
        """Analyze common error patterns and suggest fixes"""
        print("\n   CHART:  Error pattern analysis:")
        
        patterns = {
            "ModuleNotFoundError.*auth_core": "Module import issue - auth_core not in Python path",
            "redis.*Connection.*refused": "Redis connection issue - Redis disabled in staging",
            "Cloud SQL.*denied": "Database permission issue",
            "JWT.*secret": "JWT secret not configured",
            "Google.*OAuth": "OAuth credentials issue"
        }
        
        import re
        for pattern, description in patterns.items():
            matching_errors = [e for e in errors if re.search(pattern, e, re.IGNORECASE)]
            if matching_errors:
                print(f"      WARNING: [U+FE0F]  {description} ({len(matching_errors)} occurrences)")
                self.issues_found.append(description)
    
    def check_secrets(self) -> bool:
        """Check if required secrets are configured"""
        print("\n SEARCH:  Checking secret configuration...")
        
        required_secrets = [
            "database-url-staging",
            "jwt-secret-staging", 
            "google-client-id-staging",
            "google-client-secret-staging"
        ]
        
        all_present = True
        for secret in required_secrets:
            cmd = [
                "gcloud", "secrets", "describe", secret,
                f"--project={self.project_id}"
            ]
            
            returncode, _, _ = self.run_command(cmd)
            
            if returncode == 0:
                print(f"   PASS:  Secret configured: {secret}")
            else:
                print(f"   FAIL:  Secret missing: {secret}")
                self.issues_found.append(f"Secret not configured: {secret}")
                all_present = False
        
        return all_present
    
    def check_cloud_sql(self) -> bool:
        """Check Cloud SQL connectivity"""
        print("\n SEARCH:  Checking Cloud SQL configuration...")
        
        instance_name = "staging-shared-postgres"
        
        cmd = [
            "gcloud", "sql", "instances", "describe",
            instance_name,
            f"--project={self.project_id}",
            "--format=json"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd)
        
        if returncode != 0:
            print(f"   FAIL:  Cloud SQL instance {instance_name} not found")
            self.issues_found.append("Cloud SQL instance not accessible")
            return False
        
        try:
            instance_info = json.loads(stdout)
            
            # Check instance state
            state = instance_info.get("state", "")
            if state == "RUNNABLE":
                print(f"   PASS:  Cloud SQL instance is running")
            else:
                print(f"   WARNING: [U+FE0F]  Cloud SQL instance state: {state}")
                self.issues_found.append(f"Cloud SQL not in RUNNABLE state: {state}")
            
            # Check authorized networks
            settings = instance_info.get("settings", {})
            ip_config = settings.get("ipConfiguration", {})
            authorized_networks = ip_config.get("authorizedNetworks", [])
            
            if authorized_networks:
                print(f"   PASS:  Authorized networks configured: {len(authorized_networks)}")
            
            return state == "RUNNABLE"
            
        except json.JSONDecodeError:
            print("   FAIL:  Failed to parse instance info")
            return False
    
    def test_health_endpoint(self, service_info: Dict) -> bool:
        """Test the health endpoint"""
        print("\n SEARCH:  Testing health endpoint...")
        
        url = service_info.get("status", {}).get("url", "")
        if not url:
            print("   WARNING: [U+FE0F]  No service URL available")
            return False
        
        health_url = f"{url}/health"
        
        try:
            response = requests.get(health_url, timeout=10)
            
            if response.status_code == 200:
                print(f"   PASS:  Health check passed: {response.json()}")
                return True
            else:
                print(f"   FAIL:  Health check failed: HTTP {response.status_code}")
                self.issues_found.append(f"Health endpoint returned {response.status_code}")
                return False
                
        except requests.RequestException as e:
            print(f"   FAIL:  Health check failed: {e}")
            self.issues_found.append(f"Health endpoint unreachable: {str(e)}")
            return False
    
    def suggest_fixes(self):
        """Suggest fixes based on issues found"""
        print("\n[U+1F4CB] Diagnostic Summary:")
        
        if not self.issues_found:
            print("   PASS:  No issues detected! Auth service appears healthy.")
            return
        
        print(f"   WARNING: [U+FE0F]  Found {len(self.issues_found)} issue(s):")
        for i, issue in enumerate(self.issues_found, 1):
            print(f"     {i}. {issue}")
        
        print("\n IDEA:  Recommended fixes:")
        
        fix_map = {
            "Module import issue": [
                "1. Rebuild with correct PYTHONPATH: ./deploy-auth-service-fix.ps1",
                "2. Verify auth.gcp.Dockerfile copies auth_core directory"
            ],
            "Redis connection issue": [
                "This is expected in staging - Redis is disabled by design",
                "No action needed"
            ],
            "Database permission": [
                "1. Check Cloud SQL IAM permissions",
                "2. Verify #removed-legacysecret is correct",
                "3. Run: ./fix-cloud-sql-permissions.ps1"
            ],
            "JWT secret": [
                "1. Create JWT secret: gcloud secrets create jwt-secret-staging --data-file=-",
                "2. Redeploy service to pick up secret"
            ],
            "OAuth credentials": [
                "1. Verify Google OAuth credentials in GCP Console",
                "2. Update secrets: google-client-id-staging, google-client-secret-staging"
            ]
        }
        
        for issue in self.issues_found:
            for pattern, fixes in fix_map.items():
                if pattern.lower() in issue.lower():
                    print(f"\n  For '{issue}':")
                    for fix in fixes:
                        print(f"     [U+2022] {fix}")
                    break
    
    def run_diagnostic(self):
        """Run complete diagnostic"""
        print("=" * 60)
        print("      AUTH SERVICE DIAGNOSTIC TOOL")
        print("=" * 60)
        print(f"Project: {self.project_id}")
        print(f"Region: {self.region}")
        print(f"Service: {self.service_name}")
        print("=" * 60)
        
        # Run checks
        if not self.check_gcp_auth():
            print("\n FAIL:  Cannot proceed without GCP authentication")
            print("Run: gcloud auth login")
            return
        
        service_info = self.check_service_status()
        self.check_secrets()
        self.check_cloud_sql()
        self.check_recent_logs()
        
        if service_info:
            self.test_health_endpoint(service_info)
        
        # Provide recommendations
        self.suggest_fixes()
        
        print("\n" + "=" * 60)
        print("Diagnostic complete!")
        
        if self.issues_found:
            print(f"Status:  WARNING: [U+FE0F]  {len(self.issues_found)} issue(s) found")
        else:
            print("Status:  PASS:  Service appears healthy")
        
        print("=" * 60)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auth Service Diagnostic Tool")
    parser.add_argument("--project", default="netra-staging", help="GCP project ID")
    parser.add_argument("--region", default="us-central1", help="Cloud Run region")
    
    args = parser.parse_args()
    
    diagnostic = AuthServiceDiagnostic(args.project, args.region)
    diagnostic.run_diagnostic()


if __name__ == "__main__":
    main()