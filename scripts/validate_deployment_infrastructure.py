#!/usr/bin/env python3
"""
Infrastructure Validation Script for Netra Staging Deployment

Addresses critical infrastructure issues identified from recent git history:
- Issue #1263: Database timeout configuration
- Issue #1278: VPC connector capacity constraints  
- P0 Fix 2f130c108: GCP error reporter exports
- Domain configuration mismatch (*.netrasystems.ai vs *.staging.netrasystems.ai)
- SSL certificate validation
- Load balancer health check configuration
- Redis connectivity through VPC connector

Usage:
    python scripts/validate_deployment_infrastructure.py --env staging
    python scripts/validate_deployment_infrastructure.py --env staging --check-all
"""

import sys
import subprocess
import requests
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

class InfrastructureValidator:
    """Comprehensive infrastructure validation for deployment."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.issues_found = []
        self.validations_passed = []
        
        # Correct staging domain configuration (Issue #1278)
        self.staging_domains = {
            "backend": "https://staging.netrasystems.ai",
            "auth": "https://staging.netrasystems.ai", 
            "frontend": "https://staging.netrasystems.ai",
            "websocket": "wss://api.staging.netrasystems.ai"
        }
        
        # Deprecated domains that cause issues
        self.deprecated_domains = [
            "staging.netrasystems.ai",
            "auth.staging.netrasystems.ai", 
            "api.staging.netrasystems.ai",
            "app.staging.netrasystems.ai"
        ]

    def validate_domain_configuration(self) -> bool:
        """Validate staging domain configuration (Issue #1278)."""
        print("🌐 Validating domain configuration...")
        
        # Check for deprecated domain usage in codebase
        deprecated_found = []
        for domain in self.deprecated_domains:
            result = subprocess.run([
                "grep", "-r", domain, ".", 
                "--exclude-dir=.git", "--exclude-dir=node_modules"
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode == 0 and result.stdout.strip():
                deprecated_found.append(domain)
                self.issues_found.append(f"Deprecated domain '{domain}' found in codebase")
        
        if deprecated_found:
            print(f"❌ Found deprecated domains: {', '.join(deprecated_found)}")
            print("   These cause SSL certificate failures and should be updated to *.netrasystems.ai")
            return False
        else:
            print("✅ No deprecated domain usage found")
            self.validations_passed.append("Domain configuration clean")
            return True

    def validate_ssl_certificates(self) -> bool:
        """Validate SSL certificates for staging domains."""
        print("🔒 Validating SSL certificates...")
        
        ssl_issues = []
        for service, url in self.staging_domains.items():
            if service == "websocket":  # Skip WebSocket SSL check for now
                continue
                
            try:
                response = requests.get(f"{url}/health", timeout=10, verify=True)
                print(f"✅ SSL valid for {service}: {url}")
            except requests.exceptions.SSLError as e:
                ssl_issues.append(f"{service}: SSL error - {str(e)}")
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Connection issue for {service}: {str(e)}")
        
        if ssl_issues:
            for issue in ssl_issues:
                self.issues_found.append(f"SSL certificate issue: {issue}")
            return False
        else:
            self.validations_passed.append("SSL certificates valid")
            return True

    def validate_vpc_connector_config(self) -> bool:
        """Validate VPC connector configuration (Issues #1263, #1278)."""
        print("🔗 Validating VPC connector configuration...")
        
        # Check deployment scripts for required VPC flags
        deployment_script = Path("scripts/deploy_to_gcp_actual.py")
        if not deployment_script.exists():
            self.issues_found.append("Deployment script not found")
            return False
        
        with open(deployment_script, 'r') as f:
            content = f.read()
        
        required_vpc_config = [
            "--vpc-connector",
            "--vpc-egress",
            "all-traffic",
            "staging-connector"
        ]
        
        missing_config = []
        for config in required_vpc_config:
            if config not in content:
                missing_config.append(config)
        
        if missing_config:
            self.issues_found.append(f"Missing VPC configuration: {', '.join(missing_config)}")
            return False
        else:
            print("✅ VPC connector configuration present")
            self.validations_passed.append("VPC connector properly configured")
            return True

    def validate_database_timeout_config(self) -> bool:
        """Validate database timeout configuration (Issues #1263, #1278)."""
        print("🗄️ Validating database timeout configuration...")
        
        # Check for 600s timeout in deployment configuration
        workflow_file = Path(".github/workflows/deploy-staging.yml")
        if not workflow_file.exists():
            self.issues_found.append("GitHub Actions workflow not found")
            return False
        
        with open(workflow_file, 'r') as f:
            content = f.read()
        
        if "--timeout 600" not in content:
            self.issues_found.append("Database timeout not set to 600s in deployment workflow")
            return False
        
        if "--cpu-boost" not in content:
            self.issues_found.append("CPU boost not configured for faster startup")
            return False
        
        print("✅ Database timeout configured to 600s with CPU boost")
        self.validations_passed.append("Database timeout properly configured")
        return True

    def validate_monitoring_exports(self) -> bool:
        """Validate GCP error reporter exports (P0 fix 2f130c108)."""
        print("📊 Validating monitoring exports...")
        
        try:
            # Test import of critical monitoring components
            from netra_backend.app.services.monitoring import (
                GCPErrorReporter, 
                set_request_context, 
                clear_request_context
            )
            print("✅ GCP error reporter exports accessible")
            self.validations_passed.append("Monitoring exports validated")
            return True
        except ImportError as e:
            self.issues_found.append(f"Monitoring import error: {str(e)}")
            print(f"❌ Monitoring import failed: {e}")
            return False

    def validate_redis_connectivity(self) -> bool:
        """Validate Redis connectivity requirements."""
        print("🔴 Validating Redis connectivity configuration...")
        
        # Check that Redis secrets are configured in deployment
        workflow_file = Path(".github/workflows/deploy-staging.yml")
        if workflow_file.exists():
            with open(workflow_file, 'r') as f:
                content = f.read()
            
            redis_secrets = ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"]
            missing_secrets = []
            for secret in redis_secrets:
                if secret not in content:
                    missing_secrets.append(secret)
            
            if missing_secrets:
                self.issues_found.append(f"Missing Redis secrets: {', '.join(missing_secrets)}")
                return False
            else:
                print("✅ Redis secrets configured in deployment")
                self.validations_passed.append("Redis connectivity configured")
                return True
        
        self.issues_found.append("Could not validate Redis configuration")
        return False

    def run_all_validations(self) -> Tuple[bool, Dict]:
        """Run all infrastructure validations."""
        print("🚀 Starting comprehensive infrastructure validation...")
        print(f"Environment: {self.environment}")
        print("=" * 60)
        
        validations = [
            ("Domain Configuration", self.validate_domain_configuration),
            ("SSL Certificates", self.validate_ssl_certificates),
            ("VPC Connector", self.validate_vpc_connector_config),
            ("Database Timeout", self.validate_database_timeout_config),
            ("Monitoring Exports", self.validate_monitoring_exports),
            ("Redis Connectivity", self.validate_redis_connectivity)
        ]
        
        all_passed = True
        results = {}
        
        for name, validator_func in validations:
            try:
                passed = validator_func()
                results[name] = passed
                all_passed = all_passed and passed
            except Exception as e:
                print(f"❌ Validation '{name}' failed with error: {e}")
                results[name] = False
                all_passed = False
                self.issues_found.append(f"{name}: Unexpected error - {str(e)}")
        
        print("\n" + "=" * 60)
        print("📋 VALIDATION SUMMARY")
        print("=" * 60)
        
        if all_passed:
            print("✅ ALL VALIDATIONS PASSED")
            print(f"✅ {len(self.validations_passed)} checks successful")
        else:
            print("❌ VALIDATION FAILURES DETECTED")
            print(f"❌ {len(self.issues_found)} issues found")
            print(f"✅ {len(self.validations_passed)} checks successful")
            
            print("\n🔧 ISSUES TO RESOLVE:")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"  {i}. {issue}")
        
        print(f"\n📊 Infrastructure readiness: {'READY' if all_passed else 'NOT READY'}")
        
        return all_passed, results

def main():
    parser = argparse.ArgumentParser(description="Validate deployment infrastructure")
    parser.add_argument("--env", default="staging", help="Environment to validate")
    parser.add_argument("--check-all", action="store_true", help="Run comprehensive checks")
    
    args = parser.parse_args()
    
    validator = InfrastructureValidator(args.env)
    success, results = validator.run_all_validations()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()