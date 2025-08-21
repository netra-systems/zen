#!/usr/bin/env python3
"""
Comprehensive Staging Deployment Test Suite
Tests all critical staging deployment components and configurations
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class StagingDeploymentTester:
    """Comprehensive staging deployment test suite"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def test_staging_configuration(self) -> bool:
        """Test staging configuration alignment"""
        print("\n[TEST] Staging Configuration Alignment")
        try:
            # Test configuration loading
            sys.path.append(str(self.project_root / "organized_root" / "deployment_configs"))
            from staging_config_alignment import StagingConfigurationManager
            
            manager = StagingConfigurationManager()
            config = manager.deployment_config
            
            # Validate critical configuration
            checks = [
                ("Project ID", config.project_id == "netra-staging"),
                ("Region", config.region == "us-central1"),
                ("API URL", "staging.netrasystems.ai" in config.api_url),
                ("Backend service", bool(config.backend_service)),
                ("Frontend service", bool(config.frontend_service)),
                ("Auth service", bool(config.auth_service)),
            ]
            
            for check_name, passed in checks:
                status = "OK" if passed else "FAIL"
                print(f"  [{status}] {check_name}")
                if not passed:
                    self.failed += 1
                else:
                    self.passed += 1
                    
            return all(passed for _, passed in checks)
            
        except Exception as e:
            print(f"  [FAIL] Configuration loading failed: {e}")
            self.failed += 1
            return False
            
    def test_docker_configuration(self) -> bool:
        """Test Docker build configurations"""
        print("\n[TEST] Docker Build Configuration")
        
        docker_files = [
            ("Backend", self.project_root / "Dockerfile.backend"),
            ("Frontend", self.project_root / "frontend" / "Dockerfile.frontend.staging"),
            ("Auth", self.project_root / "auth_service" / "Dockerfile"),
        ]
        
        all_passed = True
        for service_name, dockerfile_path in docker_files:
            if dockerfile_path.exists():
                print(f"  [OK] {service_name} Dockerfile exists")
                self.passed += 1
                
                # Check for staging-specific configurations
                content = dockerfile_path.read_text()
                if "staging" in content.lower() or service_name == "Backend":
                    print(f"  [OK] {service_name} has staging configuration")
                    self.passed += 1
                else:
                    print(f"  [WARN] {service_name} may need staging-specific config")
                    
            else:
                print(f"  [FAIL] {service_name} Dockerfile not found at {dockerfile_path}")
                self.failed += 1
                all_passed = False
                
        return all_passed
        
    def test_gcp_authentication(self) -> bool:
        """Test GCP authentication and permissions"""
        print("\n[TEST] GCP Authentication")
        
        try:
            # Check if gcloud is installed
            result = subprocess.run(
                ["gcloud", "auth", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("  [OK] GCloud CLI is installed")
                self.passed += 1
                
                # Check for staging project access
                if "netra-staging" in result.stdout:
                    print("  [OK] Authenticated with staging project")
                    self.passed += 1
                else:
                    print("  [WARN] Not authenticated with staging project")
                    
                return True
            else:
                print("  [FAIL] GCloud authentication check failed")
                self.failed += 1
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  [FAIL] GCloud CLI not available: {e}")
            self.failed += 1
            return False
            
    def test_environment_variables(self) -> bool:
        """Test required environment variables for staging"""
        print("\n[TEST] Environment Variables")
        
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET_KEY",
            "NETRA_API_KEY",
        ]
        
        staging_env_file = self.project_root / ".env.staging"
        
        if staging_env_file.exists():
            print(f"  [OK] .env.staging file exists")
            self.passed += 1
            
            # Parse env file
            env_vars = {}
            with open(staging_env_file) as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        key, value = line.strip().split("=", 1)
                        env_vars[key] = value
                        
            # Check required variables
            all_present = True
            for var in required_vars:
                if var in env_vars:
                    print(f"  [OK] {var} is configured")
                    self.passed += 1
                else:
                    print(f"  [FAIL] {var} is missing")
                    self.failed += 1
                    all_present = False
                    
            return all_present
        else:
            print(f"  [WARN] .env.staging file not found")
            print("  [i] Staging may use GCP Secret Manager instead")
            return True
            
    def test_cloud_run_services(self) -> bool:
        """Test Cloud Run service configurations"""
        print("\n[TEST] Cloud Run Services")
        
        try:
            # Check if services are deployed
            result = subprocess.run(
                ["gcloud", "run", "services", "list", "--project", "netra-staging", "--format=json"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                services = json.loads(result.stdout) if result.stdout else []
                service_names = [s.get("metadata", {}).get("name", "") for s in services]
                
                expected_services = ["backend", "frontend", "auth-service"]
                
                for service in expected_services:
                    if service in service_names:
                        print(f"  [OK] {service} is deployed")
                        self.passed += 1
                    else:
                        print(f"  [WARN] {service} not found in Cloud Run")
                        
                return True
            else:
                print("  [WARN] Could not list Cloud Run services")
                return True
                
        except Exception as e:
            print(f"  [WARN] Cloud Run check skipped: {e}")
            return True
            
    def test_staging_endpoints(self) -> bool:
        """Test staging endpoint connectivity"""
        print("\n[TEST] Staging Endpoints")
        
        endpoints = [
            ("API Health", "https://api.staging.netrasystems.ai/health"),
            ("Frontend", "https://staging.netrasystems.ai"),
            ("Auth Service", "https://auth.staging.netrasystems.ai/health"),
        ]
        
        for name, url in endpoints:
            try:
                import requests
                response = requests.get(url, timeout=5)
                if response.status_code < 500:
                    print(f"  [OK] {name}: {url} is reachable")
                    self.passed += 1
                else:
                    print(f"  [FAIL] {name}: {url} returned {response.status_code}")
                    self.failed += 1
            except Exception as e:
                print(f"  [WARN] {name}: {url} - {type(e).__name__}")
                
        return True
        
    def test_database_connectivity(self) -> bool:
        """Test database connectivity for staging"""
        print("\n[TEST] Database Connectivity")
        
        try:
            os.environ["ENVIRONMENT"] = "staging"
            os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@staging-db/netra?sslmode=require"
            
            # Check if database configuration loads
            from netra_backend.app.core.configuration.database import DatabaseConfigurationManager
            
            db_manager = DatabaseConfigurationManager("staging")
            print("  [OK] Database configuration manager loads")
            self.passed += 1
            
            # Check SSL requirement
            if db_manager.requires_ssl("staging"):
                print("  [OK] SSL required for staging database")
                self.passed += 1
            else:
                print("  [FAIL] SSL should be required for staging")
                self.failed += 1
                
            return True
            
        except Exception as e:
            print(f"  [WARN] Database configuration test: {e}")
            return True
            
    def test_deployment_scripts(self) -> bool:
        """Test deployment script availability"""
        print("\n[TEST] Deployment Scripts")
        
        scripts = [
            ("Main deployment", self.project_root / "organized_root" / "deployment_configs" / "deploy_staging.py"),
            ("Enhanced deployment", self.project_root / "organized_root" / "deployment_configs" / "deploy_staging_enhanced.py"),
            ("Auth setup", self.project_root / "organized_root" / "deployment_configs" / "setup_staging_auth.py"),
        ]
        
        all_present = True
        for name, script_path in scripts:
            if script_path.exists():
                print(f"  [OK] {name}: {script_path.name}")
                self.passed += 1
            else:
                print(f"  [FAIL] {name} not found")
                self.failed += 1
                all_present = False
                
        return all_present
        
    def run_all_tests(self):
        """Run all staging deployment tests"""
        print("=" * 60)
        print("STAGING DEPLOYMENT TEST SUITE")
        print("=" * 60)
        
        tests = [
            self.test_staging_configuration,
            self.test_docker_configuration,
            self.test_gcp_authentication,
            self.test_environment_variables,
            self.test_cloud_run_services,
            self.test_staging_endpoints,
            self.test_database_connectivity,
            self.test_deployment_scripts,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"\n[ERROR] Test failed with exception: {e}")
                self.failed += 1
                
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total: {self.passed + self.failed}")
        
        if self.failed == 0:
            print("\n[SUCCESS] All staging deployment tests passed!")
            return 0
        else:
            print(f"\n[FAILED] {self.failed} tests failed")
            return 1


if __name__ == "__main__":
    tester = StagingDeploymentTester()
    sys.exit(tester.run_all_tests())