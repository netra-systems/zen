#!/usr/bin/env python3
"""
GCP Load Balancer Configuration Validator
Validates that all 6 critical requirements are properly configured in Terraform files.

Usage:
    python scripts/validate_load_balancer_config.py
"""

import os
import sys
from pathlib import Path
import re


class LoadBalancerConfigValidator:
    """Validates GCP load balancer configuration against requirements."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.terraform_dir = self.project_root / "terraform-gcp-staging"
        self.load_balancer_tf = self.terraform_dir / "load-balancer.tf"
        self.variables_tf = self.terraform_dir / "variables.tf"
        self.deploy_script = self.project_root / "scripts" / "deploy_to_gcp.py"
        
        self.validation_results = []
    
    def validate_requirement_1(self) -> bool:
        """Requirement 1: Load Balancer Backend Protocol must be HTTPS."""
        print(" SEARCH:  Validating Requirement 1: Backend Protocol HTTPS...")
        
        if not self.load_balancer_tf.exists():
            self.validation_results.append(" FAIL:  load-balancer.tf file not found")
            return False
        
        content = self.load_balancer_tf.read_text()
        
        # Check that all backend services use HTTPS protocol
        backend_services = re.findall(r'resource "google_compute_backend_service".*?protocol\s*=\s*"([^"]+)"', content, re.DOTALL)
        
        if all(protocol == "HTTPS" for protocol in backend_services):
            self.validation_results.append(" PASS:  All backend services use HTTPS protocol")
            return True
        else:
            self.validation_results.append(f" FAIL:  Backend services protocols: {backend_services}")
            return False
    
    def validate_requirement_2(self) -> bool:
        """Requirement 2: WebSocket Support - 3600s timeout and session affinity."""
        print(" SEARCH:  Validating Requirement 2: WebSocket Support...")
        
        content = self.load_balancer_tf.read_text()
        
        # Check timeout configuration
        timeout_configs = re.findall(r'timeout_sec\s*=\s*([^\s\n]+)', content)
        session_affinity_configs = re.findall(r'session_affinity\s*=\s*"([^"]+)"', content)
        cookie_ttl_configs = re.findall(r'affinity_cookie_ttl_sec\s*=\s*([^\s\n]+)', content)
        
        all_checks_pass = True
        
        # Check if using variables (recommended) or hardcoded values
        if any("var.backend_timeout_sec" in timeout for timeout in timeout_configs):
            self.validation_results.append(" PASS:  Timeout configured using variables")
        elif all("3600" in timeout for timeout in timeout_configs):
            self.validation_results.append(" PASS:  Timeout set to 3600 seconds")
        else:
            self.validation_results.append(f" FAIL:  Timeout configurations: {timeout_configs}")
            all_checks_pass = False
        
        if all(affinity == "GENERATED_COOKIE" for affinity in session_affinity_configs):
            self.validation_results.append(" PASS:  Session affinity configured for WebSocket")
        else:
            self.validation_results.append(f" FAIL:  Session affinity configurations: {session_affinity_configs}")
            all_checks_pass = False
            
        if cookie_ttl_configs:
            self.validation_results.append(" PASS:  Cookie TTL configured")
        else:
            self.validation_results.append(" FAIL:  Cookie TTL not configured")
            all_checks_pass = False
        
        return all_checks_pass
    
    def validate_requirement_3(self) -> bool:
        """Requirement 3: Protocol Headers - Preserve X-Forwarded-Proto."""
        print(" SEARCH:  Validating Requirement 3: Protocol Headers...")
        
        content = self.load_balancer_tf.read_text()
        
        # Check for custom request headers
        x_forwarded_proto_headers = re.findall(r'X-Forwarded-Proto:\s*https', content)
        custom_headers = re.findall(r'custom_request_headers', content)
        
        if len(x_forwarded_proto_headers) >= 3 and len(custom_headers) >= 3:
            self.validation_results.append(" PASS:  X-Forwarded-Proto headers configured on all backend services")
            return True
        else:
            self.validation_results.append(f" FAIL:  X-Forwarded-Proto headers found: {len(x_forwarded_proto_headers)}, expected: 3")
            return False
    
    def validate_requirement_4(self) -> bool:
        """Requirement 4: Health Checks use HTTPS protocol with port 443."""
        print(" SEARCH:  Validating Requirement 4: HTTPS Health Checks...")
        
        content = self.load_balancer_tf.read_text()
        
        # Check for HTTPS health checks
        https_health_checks = re.findall(r'https_health_check\s*{', content)
        http_health_checks = re.findall(r'http_health_check\s*{', content)
        port_443_configs = re.findall(r'port\s*=\s*443', content)
        
        if https_health_checks and not http_health_checks and port_443_configs:
            self.validation_results.append(" PASS:  Health checks use HTTPS on port 443")
            return True
        else:
            self.validation_results.append(f" FAIL:  HTTPS health checks: {len(https_health_checks)}, HTTP health checks: {len(http_health_checks)}, Port 443: {len(port_443_configs)}")
            return False
    
    def validate_requirement_5(self) -> bool:
        """Requirement 5: CORS - HTTPS-only origins in staging/production."""
        print(" SEARCH:  Validating Requirement 5: CORS Configuration...")
        
        content = self.load_balancer_tf.read_text()
        
        # Check CORS configuration
        cors_origins = re.findall(r'allow_origins\s*=\s*\[(.*?)\]', content, re.DOTALL)
        websocket_path_rules = re.findall(r'/ws[^"]*', content)
        
        if cors_origins:
            origins_text = cors_origins[0]
            if "https://" in origins_text and "http://" not in origins_text.replace("https://", ""):
                self.validation_results.append(" PASS:  CORS configured with HTTPS-only origins")
                cors_valid = True
            else:
                self.validation_results.append(f" FAIL:  CORS origins may include non-HTTPS: {origins_text[:100]}")
                cors_valid = False
        else:
            self.validation_results.append(" FAIL:  CORS configuration not found")
            cors_valid = False
        
        if websocket_path_rules:
            self.validation_results.append(" PASS:  WebSocket path matchers configured")
            websocket_valid = True
        else:
            self.validation_results.append(" FAIL:  WebSocket path matchers not found")
            websocket_valid = False
        
        return cors_valid and websocket_valid
    
    def validate_requirement_6(self) -> bool:
        """Requirement 6: Cloud Run Ingress "all" with FORCE_HTTPS=true."""
        print(" SEARCH:  Validating Requirement 6: Cloud Run Configuration...")
        
        if not self.deploy_script.exists():
            self.validation_results.append(" FAIL:  deploy_to_gcp.py script not found")
            return False
        
        content = self.deploy_script.read_text()
        
        # Check for FORCE_HTTPS environment variable
        force_https_configs = re.findall(r'FORCE_HTTPS.*?true', content)
        ingress_all_configs = re.findall(r'--ingress.*?all', content)
        gen2_configs = re.findall(r'--execution-environment.*?gen2', content)
        
        all_checks_pass = True
        
        if len(force_https_configs) >= 3:  # Should be in all 3 services
            self.validation_results.append(" PASS:  FORCE_HTTPS=true configured for all services")
        else:
            self.validation_results.append(f" FAIL:  FORCE_HTTPS configurations found: {len(force_https_configs)}, expected: 3")
            all_checks_pass = False
        
        if ingress_all_configs:
            self.validation_results.append(" PASS:  Cloud Run ingress set to 'all'")
        else:
            self.validation_results.append(" FAIL:  Cloud Run ingress 'all' configuration not found")
            all_checks_pass = False
            
        if gen2_configs:
            self.validation_results.append(" PASS:  Generation 2 execution environment configured")
        else:
            self.validation_results.append(" WARNING: [U+FE0F] Generation 2 execution environment not explicitly configured")
        
        return all_checks_pass
    
    def validate_variables(self) -> bool:
        """Validate that required variables are defined."""
        print(" SEARCH:  Validating Variables Configuration...")
        
        if not self.variables_tf.exists():
            self.validation_results.append(" FAIL:  variables.tf file not found")
            return False
        
        content = self.variables_tf.read_text()
        
        required_vars = [
            "backend_timeout_sec",
            "session_affinity_ttl_sec", 
            "force_https_enabled"
        ]
        
        found_vars = []
        for var in required_vars:
            if f'variable "{var}"' in content:
                found_vars.append(var)
        
        if len(found_vars) == len(required_vars):
            self.validation_results.append(" PASS:  All required variables defined")
            return True
        else:
            missing = set(required_vars) - set(found_vars)
            self.validation_results.append(f" FAIL:  Missing variables: {missing}")
            return False
    
    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        print("[U+1F680] GCP Load Balancer Configuration Validator")
        print("=" * 60)
        
        validations = [
            self.validate_requirement_1,
            self.validate_requirement_2,
            self.validate_requirement_3,
            self.validate_requirement_4,
            self.validate_requirement_5,
            self.validate_requirement_6,
            self.validate_variables
        ]
        
        results = []
        for validation in validations:
            try:
                result = validation()
                results.append(result)
            except Exception as e:
                print(f" FAIL:  Validation error: {e}")
                results.append(False)
            print()
        
        # Print summary
        print("[U+1F4CB] VALIDATION SUMMARY")
        print("=" * 60)
        for result in self.validation_results:
            print(f"  {result}")
        
        total_checks = len(results)
        passed_checks = sum(results)
        
        print(f"\n CHART:  OVERALL RESULT: {passed_checks}/{total_checks} checks passed")
        
        if all(results):
            print(" CELEBRATION:  All requirements successfully implemented!")
            return True
        else:
            print(" WARNING: [U+FE0F] Some requirements need attention.")
            return False


def main():
    """Main entry point."""
    validator = LoadBalancerConfigValidator()
    success = validator.run_all_validations()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()