#!/usr/bin/env python3
"""
Comprehensive GCP Load Balancer Deployment Validation

This script validates that the GCP load balancer deployment configuration meets all critical requirements
for HTTPS, WebSocket support, protocol headers, health checks, CORS, and Cloud Run ingress settings.

Requirements Validated:
1. Load Balancer Backend Protocol: HTTPS
2. WebSocket Support: 3600s timeout and session affinity
3. Protocol Headers: X-Forwarded-Proto preservation
4. Health Checks: HTTPS protocol on port 443
5. CORS: HTTPS-only origins
6. Cloud Run Ingress: "all" with FORCE_HTTPS=true

Usage:
    python scripts/validate_gcp_deployment.py
    python scripts/validate_gcp_deployment.py --terraform-dir terraform-gcp-staging
    python scripts/validate_gcp_deployment.py --output-json validation_results.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import re
import yaml

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    requirement_id: str
    requirement_name: str
    passed: bool
    details: List[str]
    score: float
    critical: bool = True


@dataclass
class ValidationReport:
    """Complete validation report."""
    overall_passed: bool
    total_score: float
    max_score: float
    compliance_percentage: float
    results: List[ValidationResult]
    timestamp: str
    terraform_dir: str
    summary: str


class GCPDeploymentValidator:
    """Comprehensive validator for GCP load balancer deployment configuration."""
    
    def __init__(self, terraform_dir: str = "terraform-gcp-staging"):
        self.project_root = Path(__file__).parent.parent
        self.terraform_dir = self.project_root / terraform_dir
        self.load_balancer_tf = self.terraform_dir / "load-balancer.tf"
        self.variables_tf = self.terraform_dir / "variables.tf"
        self.main_tf = self.terraform_dir / "main.tf"
        self.cloud_armor_tf = self.terraform_dir / "cloud-armor.tf"
        self.deploy_script = self.project_root / "scripts" / "deploy_to_gcp.py"
        
        # Validation results storage
        self.results: List[ValidationResult] = []
        
        # Requirements configuration
        self.requirements = {
            "req_1": {
                "name": "Backend Protocol HTTPS",
                "score": 20.0,
                "critical": True
            },
            "req_2": {
                "name": "WebSocket Support",
                "score": 20.0,
                "critical": True
            },
            "req_3": {
                "name": "Protocol Headers",
                "score": 15.0,
                "critical": True
            },
            "req_4": {
                "name": "HTTPS Health Checks",
                "score": 15.0,
                "critical": True
            },
            "req_5": {
                "name": "CORS Configuration",
                "score": 15.0,
                "critical": True
            },
            "req_6": {
                "name": "Cloud Run Ingress",
                "score": 15.0,
                "critical": True
            }
        }

    def _read_file_safely(self, file_path: Path) -> Optional[str]:
        """Safely read a file and return its contents."""
        try:
            if not file_path.exists():
                return None
            return file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"[WARN] Error reading {file_path}: {e}")
            return None

    def validate_requirement_1(self) -> ValidationResult:
        """Requirement 1: Load Balancer Backend Protocol must be HTTPS."""
        req_id = "req_1"
        req_name = self.requirements[req_id]["name"]
        details = []
        passed = True
        
        print(f"[VALIDATING] Validating {req_name}...")
        
        content = self._read_file_safely(self.load_balancer_tf)
        if not content:
            details.append("[FAIL] load-balancer.tf file not found or unreadable")
            return ValidationResult(req_id, req_name, False, details, 0.0)
        
        # Extract backend service configurations
        backend_service_pattern = r'resource "google_compute_backend_service" "(\w+)"[^}]*?protocol\s*=\s*"([^"]+)"'
        backend_services = re.findall(backend_service_pattern, content, re.DOTALL)
        
        if not backend_services:
            details.append("[FAIL] No backend services found in configuration")
            passed = False
        else:
            https_count = 0
            for service_name, protocol in backend_services:
                if protocol == "HTTPS":
                    details.append(f"[OK] Backend service '{service_name}' uses HTTPS protocol")
                    https_count += 1
                else:
                    details.append(f"[FAIL] Backend service '{service_name}' uses {protocol} instead of HTTPS")
                    passed = False
            
            if https_count == len(backend_services):
                details.append(f"[OK] All {len(backend_services)} backend services use HTTPS protocol")
            else:
                details.append(f"[FAIL] Only {https_count}/{len(backend_services)} backend services use HTTPS")
                passed = False
        
        # Additional check for load balancing scheme
        external_managed_pattern = r'load_balancing_scheme\s*=\s*"EXTERNAL_MANAGED"'
        external_managed_matches = re.findall(external_managed_pattern, content)
        
        if external_managed_matches:
            details.append(f"[OK] Found {len(external_managed_matches)} EXTERNAL_MANAGED load balancing schemes")
        else:
            details.append("[WARN] No EXTERNAL_MANAGED load balancing scheme found")
        
        score = self.requirements[req_id]["score"] if passed else 0.0
        return ValidationResult(req_id, req_name, passed, details, score)

    def validate_requirement_2(self) -> ValidationResult:
        """Requirement 2: WebSocket Support - 3600s timeout and session affinity."""
        req_id = "req_2"
        req_name = self.requirements[req_id]["name"]
        details = []
        passed = True
        
        print(f"[VALIDATING] Validating {req_name}...")
        
        # Check load balancer configuration
        lb_content = self._read_file_safely(self.load_balancer_tf)
        if not lb_content:
            details.append("[FAIL] load-balancer.tf file not found")
            return ValidationResult(req_id, req_name, False, details, 0.0)
        
        # Check variables configuration
        var_content = self._read_file_safely(self.variables_tf)
        if not var_content:
            details.append("[FAIL] variables.tf file not found")
            return ValidationResult(req_id, req_name, False, details, 0.0)
        
        # Check timeout configuration
        timeout_patterns = [
            r'timeout_sec\s*=\s*var\.backend_timeout_sec',
            r'timeout_sec\s*=\s*3600'
        ]
        
        timeout_found = False
        for pattern in timeout_patterns:
            if re.search(pattern, lb_content):
                timeout_found = True
                details.append("[OK] Backend timeout configured for WebSocket support")
                break
        
        if not timeout_found:
            details.append("[FAIL] Backend timeout not configured for WebSocket (3600s required)")
            passed = False
        
        # Check variable definition
        backend_timeout_var = re.search(r'variable "backend_timeout_sec".*?default\s*=\s*(\d+)', var_content, re.DOTALL)
        if backend_timeout_var:
            timeout_value = int(backend_timeout_var.group(1))
            if timeout_value >= 3600:
                details.append(f"[OK] Backend timeout variable set to {timeout_value} seconds ([?]3600)")
            else:
                details.append(f"[FAIL] Backend timeout variable set to {timeout_value} seconds (<3600)")
                passed = False
        
        # Check session affinity
        session_affinity_configs = re.findall(r'session_affinity\s*=\s*"([^"]+)"', lb_content)
        if all(affinity == "GENERATED_COOKIE" for affinity in session_affinity_configs):
            details.append(f"[OK] Session affinity configured with GENERATED_COOKIE on {len(session_affinity_configs)} services")
        else:
            details.append(f"[FAIL] Session affinity not properly configured: {session_affinity_configs}")
            passed = False
        
        # Check cookie TTL
        cookie_ttl_configs = re.findall(r'affinity_cookie_ttl_sec\s*=\s*([^\s\n,}]+)', lb_content)
        if cookie_ttl_configs:
            details.append(f"[OK] Cookie TTL configured on {len(cookie_ttl_configs)} services")
        else:
            details.append("[FAIL] Cookie TTL not configured")
            passed = False
        
        # Check WebSocket-specific path rules
        websocket_paths = re.findall(r'paths\s*=\s*\[[^\]]*"/ws[^"]*"[^\]]*\]', lb_content, re.DOTALL)
        if websocket_paths:
            details.append("[OK] WebSocket path rules configured")
        else:
            details.append("[WARN] WebSocket-specific path rules not found")
        
        score = self.requirements[req_id]["score"] if passed else 0.0
        return ValidationResult(req_id, req_name, passed, details, score)

    def validate_requirement_3(self) -> ValidationResult:
        """Requirement 3: Protocol Headers - Preserve X-Forwarded-Proto."""
        req_id = "req_3"
        req_name = self.requirements[req_id]["name"]
        details = []
        passed = True
        
        print(f"[VALIDATING] Validating {req_name}...")
        
        content = self._read_file_safely(self.load_balancer_tf)
        if not content:
            details.append("[FAIL] load-balancer.tf file not found")
            return ValidationResult(req_id, req_name, False, details, 0.0)
        
        # Check for custom request headers in backend services
        custom_headers_pattern = r'custom_request_headers\s*=\s*\[(.*?)\]'
        header_blocks = re.findall(custom_headers_pattern, content, re.DOTALL)
        
        x_forwarded_proto_count = 0
        for block in header_blocks:
            if "X-Forwarded-Proto" in block and "https" in block:
                x_forwarded_proto_count += 1
        
        expected_services = len(re.findall(r'resource "google_compute_backend_service"', content))
        
        if x_forwarded_proto_count >= expected_services:
            details.append(f"[OK] X-Forwarded-Proto: https headers configured on all {expected_services} backend services")
        else:
            details.append(f"[FAIL] X-Forwarded-Proto headers found on {x_forwarded_proto_count}/{expected_services} services")
            passed = False
        
        # Check for headers in URL map default route action
        url_map_headers = re.findall(r'request_headers_to_add\s*{[^}]*header_name\s*=\s*"X-Forwarded-Proto"[^}]*header_value\s*=\s*"https"', content, re.DOTALL)
        if url_map_headers:
            details.append(f"[OK] X-Forwarded-Proto headers also configured in URL map ({len(url_map_headers)} instances)")
        
        # Check for WebSocket-specific header additions
        websocket_headers = re.findall(r'X-WebSocket-Upgrade', content)
        if websocket_headers:
            details.append("[OK] WebSocket upgrade headers configured")
        else:
            details.append("[WARN] WebSocket upgrade headers not found")
        
        score = self.requirements[req_id]["score"] if passed else 0.0
        return ValidationResult(req_id, req_name, passed, details, score)

    def validate_requirement_4(self) -> ValidationResult:
        """Requirement 4: Health Checks use HTTPS protocol with port 443."""
        req_id = "req_4"
        req_name = self.requirements[req_id]["name"]
        details = []
        passed = True
        
        print(f"[VALIDATING] Validating {req_name}...")
        
        content = self._read_file_safely(self.load_balancer_tf)
        if not content:
            details.append("[FAIL] load-balancer.tf file not found")
            return ValidationResult(req_id, req_name, False, details, 0.0)
        
        # Check for HTTPS health check resource
        https_health_check_pattern = r'resource "google_compute_health_check" "([^"]+)"[^}]*https_health_check\s*{([^}]*)}'
        https_health_checks = re.findall(https_health_check_pattern, content, re.DOTALL)
        
        if https_health_checks:
            for check_name, check_config in https_health_checks:
                details.append(f"[OK] HTTPS health check '{check_name}' configured")
                
                # Check port configuration
                port_match = re.search(r'port\s*=\s*(\d+)', check_config)
                if port_match:
                    port = int(port_match.group(1))
                    if port == 443:
                        details.append(f"[OK] Health check uses port 443")
                    else:
                        details.append(f"[FAIL] Health check uses port {port} instead of 443")
                        passed = False
                else:
                    details.append("[WARN] Port not explicitly configured in health check")
                
                # Check request path
                path_match = re.search(r'request_path\s*=\s*"([^"]*)"', check_config)
                if path_match:
                    path = path_match.group(1)
                    details.append(f"[OK] Health check path: {path}")
                
        else:
            details.append("[FAIL] No HTTPS health checks found")
            passed = False
        
        # Check for HTTP health checks (should not exist)
        http_health_checks = re.findall(r'http_health_check\s*{', content)
        if http_health_checks:
            details.append(f"[FAIL] Found {len(http_health_checks)} HTTP health checks (should be HTTPS only)")
            passed = False
        else:
            details.append("[OK] No HTTP health checks found (correct)")
        
        # Check health check logging
        log_config_pattern = r'log_config\s*{\s*enable\s*=\s*true\s*}'
        log_configs = re.findall(log_config_pattern, content)
        if log_configs:
            details.append("[OK] Health check logging enabled")
        else:
            details.append("[WARN] Health check logging not explicitly enabled")
        
        score = self.requirements[req_id]["score"] if passed else 0.0
        return ValidationResult(req_id, req_name, passed, details, score)

    def validate_requirement_5(self) -> ValidationResult:
        """Requirement 5: CORS - HTTPS-only origins in staging/production."""
        req_id = "req_5"
        req_name = self.requirements[req_id]["name"]
        details = []
        passed = True
        
        print(f"[VALIDATING] Validating {req_name}...")
        
        content = self._read_file_safely(self.load_balancer_tf)
        if not content:
            details.append("[FAIL] load-balancer.tf file not found")
            return ValidationResult(req_id, req_name, False, details, 0.0)
        
        # Check CORS policy configuration
        cors_policy_pattern = r'cors_policy\s*{(.*?)}'
        cors_policies = re.findall(cors_policy_pattern, content, re.DOTALL)
        
        if not cors_policies:
            details.append("[FAIL] CORS policy not found")
            passed = False
        else:
            for policy in cors_policies:
                # Check allow_origins
                origins_match = re.search(r'allow_origins\s*=\s*\[(.*?)\]', policy, re.DOTALL)
                if origins_match:
                    origins_text = origins_match.group(1)
                    # Extract individual origins
                    origins = re.findall(r'"([^"]+)"', origins_text)
                    
                    https_origins = [o for o in origins if o.startswith('https://')]
                    http_origins = [o for o in origins if o.startswith('http://') and not o.startswith('https://')]
                    localhost_origins = [o for o in origins if 'localhost' in o or '127.0.0.1' in o]
                    
                    details.append(f"[OK] Found {len(origins)} CORS origins")
                    
                    if len(https_origins) == len(origins):
                        details.append(f"[OK] All {len(origins)} origins use HTTPS")
                    else:
                        details.append(f"[FAIL] {len(origins) - len(https_origins)}/{len(origins)} origins are not HTTPS")
                        passed = False
                    
                    if http_origins:
                        details.append(f"[FAIL] Found {len(http_origins)} HTTP origins: {http_origins}")
                        passed = False
                    
                    if localhost_origins:
                        details.append(f"[WARN] Found {len(localhost_origins)} localhost origins (OK for staging): {localhost_origins}")
                
                # Check other CORS settings
                methods_match = re.search(r'allow_methods\s*=\s*\[(.*?)\]', policy, re.DOTALL)
                if methods_match:
                    methods = re.findall(r'"([^"]+)"', methods_match.group(1))
                    required_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
                    if all(method in methods for method in required_methods):
                        details.append(f"[OK] All required HTTP methods allowed")
                    else:
                        details.append(f"[WARN] Some required methods may be missing: {methods}")
                
                # Check credentials support
                if 'allow_credentials = true' in policy:
                    details.append("[OK] CORS credentials enabled")
                else:
                    details.append("[WARN] CORS credentials not explicitly enabled")
        
        # Check WebSocket-specific CORS handling
        websocket_cors_pattern = r'/ws[^"]*'
        websocket_paths = re.findall(websocket_cors_pattern, content)
        if websocket_paths:
            details.append(f"[OK] WebSocket paths configured for CORS handling")
        
        score = self.requirements[req_id]["score"] if passed else 0.0
        return ValidationResult(req_id, req_name, passed, details, score)

    def validate_requirement_6(self) -> ValidationResult:
        """Requirement 6: Cloud Run Ingress 'all' with FORCE_HTTPS=true."""
        req_id = "req_6"
        req_name = self.requirements[req_id]["name"]
        details = []
        passed = True
        
        print(f"[VALIDATING] Validating {req_name}...")
        
        content = self._read_file_safely(self.deploy_script)
        if not content:
            details.append("[FAIL] deploy_to_gcp.py script not found")
            return ValidationResult(req_id, req_name, False, details, 0.0)
        
        # Check FORCE_HTTPS environment variable in service configurations
        service_configs = re.findall(r'ServiceConfig\((.*?)\)', content, re.DOTALL)
        force_https_in_configs = content.count('"FORCE_HTTPS": "true"')
        
        if force_https_in_configs >= 3:  # Should be in all 3 services
            details.append(f"[OK] FORCE_HTTPS=true configured in {force_https_in_configs} service configurations")
        else:
            details.append(f"[FAIL] FORCE_HTTPS=true found in {force_https_in_configs}/3 service configurations")
            passed = False
        
        # Check Cloud Run deployment flags
        ingress_all_pattern = r'--ingress["\s]*all'
        ingress_configs = re.findall(ingress_all_pattern, content)
        
        if ingress_configs:
            details.append("[OK] Cloud Run ingress set to 'all'")
        else:
            details.append("[FAIL] Cloud Run ingress 'all' configuration not found")
            passed = False
        
        # Check for allow-unauthenticated flag
        unauth_pattern = r'--allow-unauthenticated'
        unauth_configs = re.findall(unauth_pattern, content)
        if unauth_configs:
            details.append("[WARN] Services configured with --allow-unauthenticated (staging only)")
        
        # Check execution environment
        gen2_pattern = r'--execution-environment["\s]*gen2'
        gen2_configs = re.findall(gen2_pattern, content)
        if gen2_configs:
            details.append("[OK] Generation 2 execution environment configured")
        else:
            details.append("[WARN] Generation 2 execution environment not found")
        
        # Check for HTTPS enforcement in environment variables
        env_force_https = re.findall(r'FORCE_HTTPS.*?true', content, re.IGNORECASE)
        if len(env_force_https) >= 3:
            details.append(f"[OK] FORCE_HTTPS environment variable set in {len(env_force_https)} locations")
        else:
            details.append(f"[FAIL] FORCE_HTTPS environment variable missing or incorrect")
            passed = False
        
        # Check port configurations
        port_443_configs = content.count('443')
        if port_443_configs > 0:
            details.append(f"[OK] Port 443 references found ({port_443_configs} instances)")
        
        score = self.requirements[req_id]["score"] if passed else 0.0
        return ValidationResult(req_id, req_name, passed, details, score)

    def validate_terraform_syntax(self) -> ValidationResult:
        """Additional validation: Check Terraform syntax and structure."""
        req_id = "terraform_syntax"
        req_name = "Terraform Syntax & Structure"
        details = []
        passed = True
        
        print("[VALIDATING] Validating Terraform syntax and structure...")
        
        # Check for required files
        required_files = [
            self.load_balancer_tf,
            self.variables_tf,
            self.main_tf
        ]
        
        for file_path in required_files:
            if file_path.exists():
                details.append(f"[OK] {file_path.name} exists")
            else:
                details.append(f"[FAIL] {file_path.name} missing")
                passed = False
        
        # Check for proper resource dependencies
        lb_content = self._read_file_safely(self.load_balancer_tf)
        if lb_content:
            depends_on_pattern = r'depends_on\s*=\s*\[(.*?)\]'
            dependencies = re.findall(depends_on_pattern, lb_content, re.DOTALL)
            if dependencies:
                details.append(f"[OK] Found {len(dependencies)} resource dependencies")
            else:
                details.append("[WARN] No explicit resource dependencies found")
        
        # Check for proper variable usage
        var_usage = re.findall(r'var\.(\w+)', lb_content or '')
        if var_usage:
            details.append(f"[OK] Using {len(set(var_usage))} variables in load balancer config")
        
        score = 10.0 if passed else 0.0
        return ValidationResult(req_id, req_name, passed, details, score, critical=False)

    def run_all_validations(self) -> ValidationReport:
        """Run all validation checks and generate a comprehensive report."""
        print("GCP Deployment Configuration Validator")
        print("=" * 70)
        print(f"Terraform Directory: {self.terraform_dir}")
        print(f"Load Balancer Config: {self.load_balancer_tf.name}")
        print("=" * 70)
        
        # Run all validations
        validations = [
            self.validate_requirement_1,
            self.validate_requirement_2,
            self.validate_requirement_3,
            self.validate_requirement_4,
            self.validate_requirement_5,
            self.validate_requirement_6,
            self.validate_terraform_syntax
        ]
        
        self.results = []
        for validation in validations:
            try:
                result = validation()
                self.results.append(result)
                print(f"[RESULT] {result.requirement_name}: {'PASS' if result.passed else 'FAIL'} ({result.score:.1f} points)")
                for detail in result.details:
                    # Remove emoji characters for Windows compatibility
                    clean_detail = detail.replace("[OK]", "[OK]").replace("[FAIL]", "[FAIL]").replace("[WARN]", "[WARN]")
                    print(f"    {clean_detail}")
                print()
            except Exception as e:
                error_result = ValidationResult(
                    f"error_{validation.__name__}",
                    validation.__name__.replace('validate_', '').replace('_', ' ').title(),
                    False,
                    [f"[FAIL] Validation error: {e}"],
                    0.0
                )
                self.results.append(error_result)
                print(f"[FAIL] Error in {validation.__name__}: {e}")
                print()
        
        # Calculate overall scores
        total_score = sum(r.score for r in self.results)
        max_score = sum(self.requirements[req_id]["score"] for req_id in self.requirements) + 10.0  # +10 for syntax check
        compliance_percentage = (total_score / max_score) * 100 if max_score > 0 else 0.0
        
        # Check if all critical requirements pass
        critical_results = [r for r in self.results if r.critical]
        overall_passed = all(r.passed for r in critical_results)
        
        # Generate summary
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        
        if overall_passed and compliance_percentage >= 90:
            summary = "[EXCELLENT] All critical requirements met with high compliance"
        elif overall_passed:
            summary = "[GOOD] All critical requirements met"
        elif compliance_percentage >= 70:
            summary = "[NEEDS ATTENTION] Some critical requirements failing but mostly compliant"
        else:
            summary = "[CRITICAL] Multiple requirements failing, deployment may be unsafe"
        
        # Create report
        report = ValidationReport(
            overall_passed=overall_passed,
            total_score=total_score,
            max_score=max_score,
            compliance_percentage=compliance_percentage,
            results=self.results,
            timestamp=__import__('datetime').datetime.now().isoformat(),
            terraform_dir=str(self.terraform_dir),
            summary=summary
        )
        
        # Print summary
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Overall Result: {passed_count}/{total_count} checks passed")
        print(f"Compliance Score: {total_score:.1f}/{max_score:.1f} ({compliance_percentage:.1f}%)")
        print(f"Assessment: {summary}")
        print()
        
        # Print detailed results
        print("DETAILED RESULTS")
        print("=" * 70)
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            critical_mark = "[CRITICAL]" if result.critical else "[INFO]"
            print(f"{critical_mark} {result.requirement_name}: {status} ({result.score:.1f} points)")
            for detail in result.details:
                clean_detail = detail.replace("[OK]", "[OK]").replace("[FAIL]", "[FAIL]").replace("[WARN]", "[WARN]")
                print(f"    {clean_detail}")
            print()
        
        return report

    def save_report_json(self, report: ValidationReport, output_path: str) -> bool:
        """Save validation report as JSON."""
        try:
            report_dict = asdict(report)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)
            print(f"Report saved to: {output_path}")
            return True
        except Exception as e:
            print(f"[FAIL] Failed to save report: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate GCP load balancer deployment configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--terraform-dir",
        default="terraform-gcp-staging",
        help="Terraform configuration directory (default: terraform-gcp-staging)"
    )
    
    parser.add_argument(
        "--output-json",
        help="Save detailed validation report as JSON to specified path"
    )
    
    parser.add_argument(
        "--min-compliance",
        type=float,
        default=90.0,
        help="Minimum compliance percentage required for success (default: 90.0)"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = GCPDeploymentValidator(args.terraform_dir)
    report = validator.run_all_validations()
    
    # Save JSON report if requested
    if args.output_json:
        validator.save_report_json(report, args.output_json)
    
    # Check compliance threshold
    success = report.overall_passed and report.compliance_percentage >= args.min_compliance
    
    if success:
        print(f"[SUCCESS] Configuration meets all requirements ({report.compliance_percentage:.1f}% compliance)")
    else:
        print(f"[FAILURE] Configuration does not meet requirements ({report.compliance_percentage:.1f}% compliance)")
        print(f"   Required: {args.min_compliance}% minimum compliance")
        print("   Fix the issues above before deploying to production.")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()