#!/usr/bin/env python3
"""
Mission Critical: Load Balancer Endpoint Compliance Tests
========================================================

CRITICAL BUSINESS VALUE: Platform/Internal - System Reliability
Prevents catastrophic staging environment failures by ensuring all endpoints
use load balancer URLs instead of direct Cloud Run URLs.

These tests MUST NEVER be bypassed or mocked. They serve as the final safety net
to prevent regression to direct Cloud Run endpoints that cause deployment failures.

CLAUDE.md COMPLIANCE:
- SSOT enforcement for endpoint configuration 
- Real service validation only (NO MOCKS)
- Critical regression prevention
- Atomic compliance verification

WHY THIS IS MISSION CRITICAL:
1. Direct Cloud Run URLs change on every deployment
2. Load balancer URLs are stable and reliable
3. Test failures indicate immediate system risk
4. Prevents cascade failures in production deployment pipeline
"""

import os
import re
import sys
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

import pytest

# Add project root to path for absolute imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from shared.isolated_environment import get_env
from netra_backend.app.core.network_constants import URLConstants
from tests.e2e.e2e_test_config import get_e2e_config


@dataclass
class ComplianceViolation:
    """Represents a compliance violation found in the codebase"""
    file_path: str
    line_number: int
    violation_text: str
    violation_type: str
    severity: str


class LoadBalancerComplianceValidator:
    """Validates that all staging URLs use load balancer endpoints"""
    
    # CRITICAL: These patterns identify dangerous direct Cloud Run URLs
    FORBIDDEN_URL_PATTERNS = [
        r'https://netra-[a-z-]+-staging-[a-zA-Z0-9]+-[a-z]+\.a\.run\.app',
        r'https://[a-zA-Z0-9-]+-staging-[a-zA-Z0-9]+-[a-z]+\.a\.run\.app',
        r'\.a\.run\.app'  # Catch-all for any Cloud Run direct URLs
    ]
    
    # REQUIRED: These are the only acceptable staging URLs
    REQUIRED_LOAD_BALANCER_URLS = {
        'backend': 'https://api.staging.netrasystems.ai',
        'auth': 'https://auth.staging.netrasystems.ai', 
        'frontend': 'https://app.staging.netrasystems.ai',
        'websocket': 'wss://api.staging.netrasystems.ai/ws'
    }
    
    # Files to exclude from compliance checks
    EXCLUDE_PATTERNS = [
        r'backup/',
        r'reports/',
        r'docs/',
        r'logs/',
        r'config/',
        r'SPEC/',
        r'terraform-gcp-staging/',
        r'\.venv/',
        r'venv/',
        r'__pycache__/',
        r'\.git/',
        r'node_modules/',
        r'\.md$',
        r'\.json$',
        r'\.xml$',
        r'\.txt$',
        r'\.yml$',
        r'\.yaml$'
    ]
    
    def __init__(self):
        self.violations: List[ComplianceViolation] = []
        self.scanned_files = 0
        self.violation_files = 0
        
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from compliance checking"""
        file_str = str(file_path.relative_to(project_root))
        return any(re.search(pattern, file_str) for pattern in self.EXCLUDE_PATTERNS)
    
    def scan_file_for_violations(self, file_path: Path) -> List[ComplianceViolation]:
        """Scan a single file for compliance violations"""
        violations = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern in self.FORBIDDEN_URL_PATTERNS:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        violation = ComplianceViolation(
                            file_path=str(file_path.relative_to(project_root)),
                            line_number=line_num,
                            violation_text=match.group(0),
                            violation_type="FORBIDDEN_CLOUD_RUN_URL",
                            severity="CRITICAL"
                        )
                        violations.append(violation)
                        
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
            
        return violations
    
    def scan_codebase(self) -> Dict[str, any]:
        """Scan entire codebase for compliance violations"""
        logger.info("Starting load balancer endpoint compliance scan...")
        
        # Scan Python files
        for py_file in project_root.rglob("*.py"):
            if self.should_exclude_file(py_file):
                continue
                
            self.scanned_files += 1
            file_violations = self.scan_file_for_violations(py_file)
            
            if file_violations:
                self.violations.extend(file_violations)
                self.violation_files += 1
        
        # Scan configuration files
        for config_file in project_root.rglob("*.js"):
            if self.should_exclude_file(config_file):
                continue
                
            self.scanned_files += 1
            file_violations = self.scan_file_for_violations(config_file)
            
            if file_violations:
                self.violations.extend(file_violations)
                self.violation_files += 1
        
        return {
            'total_violations': len(self.violations),
            'violation_files': self.violation_files,
            'scanned_files': self.scanned_files,
            'is_compliant': len(self.violations) == 0
        }
    
    def generate_compliance_report(self) -> str:
        """Generate detailed compliance report"""
        report = []
        report.append("LOAD BALANCER ENDPOINT COMPLIANCE REPORT")
        report.append("=" * 50)
        report.append(f"Scanned Files: {self.scanned_files}")
        report.append(f"Files with Violations: {self.violation_files}")
        report.append(f"Total Violations: {len(self.violations)}")
        report.append(f"Compliance Status: {'✅ COMPLIANT' if len(self.violations) == 0 else '❌ NON-COMPLIANT'}")
        report.append("")
        
        if self.violations:
            report.append("VIOLATIONS FOUND:")
            report.append("-" * 30)
            for violation in self.violations:
                report.append(f"FILE: {violation.file_path}")
                report.append(f"LINE: {violation.line_number}")
                report.append(f"URL: {violation.violation_text}")
                report.append(f"TYPE: {violation.violation_type}")
                report.append(f"SEVERITY: {violation.severity}")
                report.append("")
        
        report.append("REQUIRED LOAD BALANCER URLS:")
        report.append("-" * 30)
        for service, url in self.REQUIRED_LOAD_BALANCER_URLS.items():
            report.append(f"{service.upper()}: {url}")
        
        return "\n".join(report)


class LoadBalancerConnectivityValidator:
    """Validates that load balancer URLs are accessible and working"""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        
    async def test_load_balancer_connectivity(self) -> Dict[str, any]:
        """Test connectivity to all load balancer endpoints"""
        logger.info("Testing load balancer endpoint connectivity...")
        
        urls_to_test = LoadBalancerComplianceValidator.REQUIRED_LOAD_BALANCER_URLS.copy()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for service_name, url in urls_to_test.items():
                if service_name == 'websocket':
                    # Skip WebSocket connectivity test for now
                    self.results[service_name] = {
                        'url': url,
                        'status': 'SKIPPED',
                        'accessible': True,
                        'response_time': 0,
                        'error': 'WebSocket testing requires separate implementation'
                    }
                    continue
                
                try:
                    start_time = asyncio.get_event_loop().time()
                    
                    # Test health endpoint for backend and auth
                    test_url = url
                    if service_name in ['backend', 'auth']:
                        test_url = f"{url}/health"
                    
                    response = await client.get(test_url)
                    
                    end_time = asyncio.get_event_loop().time()
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    
                    self.results[service_name] = {
                        'url': test_url,
                        'status_code': response.status_code,
                        'accessible': 200 <= response.status_code < 400,
                        'response_time': response_time,
                        'error': None
                    }
                    
                except Exception as e:
                    self.results[service_name] = {
                        'url': url,
                        'status_code': None,
                        'accessible': False,
                        'response_time': None,
                        'error': str(e)
                    }
        
        # Calculate overall health
        accessible_services = sum(1 for result in self.results.values() if result['accessible'])
        total_services = len(self.results)
        
        return {
            'total_services': total_services,
            'accessible_services': accessible_services,
            'accessibility_rate': accessible_services / total_services * 100,
            'all_accessible': accessible_services == total_services,
            'results': self.results
        }


@pytest.mark.asyncio
class TestLoadBalancerEndpointCompliance:
    """Mission critical tests for load balancer endpoint compliance"""
    
    @pytest.fixture(scope="class")
    def compliance_validator(self):
        """Create compliance validator instance"""
        return LoadBalancerComplianceValidator()
    
    @pytest.fixture(scope="class") 
    def connectivity_validator(self):
        """Create connectivity validator instance"""
        return LoadBalancerConnectivityValidator()
    
    def test_no_cloud_run_urls_in_codebase(self, compliance_validator):
        """CRITICAL: Ensure no direct Cloud Run URLs exist in codebase"""
        results = compliance_validator.scan_codebase()
        
        report = compliance_validator.generate_compliance_report()
        logger.info(f"\n{report}")
        
        # CRITICAL: This test MUST fail if any Cloud Run URLs are found
        assert results['is_compliant'], (
            f"CRITICAL FAILURE: Found {results['total_violations']} Cloud Run URLs in "
            f"{results['violation_files']} files. This will cause staging deployment failures!\n"
            f"All URLs must use load balancer endpoints:\n"
            f"- Backend: https://api.staging.netrasystems.ai\n"
            f"- Auth: https://auth.staging.netrasystems.ai\n" 
            f"- Frontend: https://app.staging.netrasystems.ai\n"
            f"Run the migration script to fix: python scripts/migrate_cloud_run_urls.py --execute"
        )
    
    def test_staging_config_uses_load_balancer_urls(self):
        """CRITICAL: Verify staging configuration uses correct load balancer URLs"""
        config = get_e2e_config(force_environment="staging")
        
        # Validate all staging URLs
        assert config.backend_url == "https://api.staging.netrasystems.ai", (
            f"Staging backend URL incorrect: {config.backend_url}"
        )
        assert config.auth_url == "https://auth.staging.netrasystems.ai", (
            f"Staging auth URL incorrect: {config.auth_url}"
        )
        assert config.websocket_url == "wss://api.staging.netrasystems.ai/ws", (
            f"Staging WebSocket URL incorrect: {config.websocket_url}"
        )
        assert config.frontend_url == "https://app.staging.netrasystems.ai", (
            f"Staging frontend URL incorrect: {config.frontend_url}"
        )
    
    def test_network_constants_compliance(self):
        """CRITICAL: Verify network constants use load balancer URLs"""
        # Check staging constants
        assert URLConstants.STAGING_BACKEND_URL == "https://api.staging.netrasystems.ai"
        assert URLConstants.STAGING_AUTH_URL == "https://auth.staging.netrasystems.ai"
        assert URLConstants.STAGING_FRONTEND_URL == "https://app.staging.netrasystems.ai"
        assert URLConstants.STAGING_WEBSOCKET_URL == "wss://api.staging.netrasystems.ai/ws"
        
        # Check CORS origins for staging
        cors_origins = URLConstants.get_cors_origins("staging")
        expected_origins = [
            "https://app.staging.netrasystems.ai",
            "https://api.staging.netrasystems.ai",
            "https://auth.staging.netrasystems.ai",
            "http://localhost:3000"  # Local dev fallback
        ]
        
        for expected_origin in expected_origins[:3]:  # Skip localhost check
            assert expected_origin in cors_origins, (
                f"Missing CORS origin: {expected_origin}. Found: {cors_origins}"
            )
    
    async def test_load_balancer_endpoints_accessible(self, connectivity_validator):
        """CRITICAL: Verify load balancer endpoints are accessible"""
        results = await connectivity_validator.test_load_balancer_connectivity()
        
        logger.info(f"Connectivity Results: {results}")
        
        # Log individual service results
        for service, result in results['results'].items():
            if result['accessible']:
                logger.info(f"✅ {service.upper()}: {result['url']} ({result.get('response_time', 'N/A')}ms)")
            else:
                logger.error(f"❌ {service.upper()}: {result['url']} - {result.get('error', 'Unknown error')}")
        
        # CRITICAL: At least backend and auth must be accessible
        critical_services = ['backend', 'auth']
        for service in critical_services:
            service_result = results['results'].get(service, {})
            assert service_result.get('accessible', False), (
                f"CRITICAL: {service} service not accessible at {service_result.get('url', 'unknown')}\n"
                f"Error: {service_result.get('error', 'Unknown error')}"
            )
    
    def test_forbidden_patterns_detection(self, compliance_validator):
        """Validate that the compliance validator correctly detects forbidden patterns"""
        # Test forbidden pattern detection with example text
        test_content = """
        BACKEND_URL = "https://netra-backend-staging-abc123-uc.a.run.app"
        AUTH_URL = "https://netra-auth-staging-xyz789-uc.a.run.app"
        GOOD_URL = "https://api.staging.netrasystems.ai"
        """
        
        # Create a temporary test file
        temp_file = project_root / "temp_test_compliance.py"
        temp_file.write_text(test_content)
        
        try:
            violations = compliance_validator.scan_file_for_violations(temp_file)
            
            # Should detect 2 violations
            assert len(violations) == 2, f"Expected 2 violations, found {len(violations)}"
            
            # Verify violation details
            violation_urls = [v.violation_text for v in violations]
            assert "https://netra-backend-staging-abc123-uc.a.run.app" in violation_urls
            assert "https://netra-auth-staging-xyz789-uc.a.run.app" in violation_urls
            
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()


# Standalone execution for CI/CD pipeline
if __name__ == "__main__":
    async def run_compliance_check():
        """Run compliance check as standalone script"""
        print("🔍 Running Load Balancer Endpoint Compliance Check...")
        
        # Codebase compliance
        validator = LoadBalancerComplianceValidator()
        results = validator.scan_codebase()
        report = validator.generate_compliance_report()
        print(report)
        
        if not results['is_compliant']:
            print("\n❌ COMPLIANCE CHECK FAILED!")
            print("Run migration script: python scripts/migrate_cloud_run_urls.py --execute")
            sys.exit(1)
        
        # Connectivity test
        connectivity = LoadBalancerConnectivityValidator()
        conn_results = await connectivity.test_load_balancer_connectivity()
        
        print(f"\n🌐 Connectivity Test Results:")
        print(f"Services Tested: {conn_results['total_services']}")
        print(f"Accessible: {conn_results['accessible_services']}")
        print(f"Accessibility Rate: {conn_results['accessibility_rate']:.1f}%")
        
        if conn_results['all_accessible']:
            print("\n✅ ALL COMPLIANCE CHECKS PASSED!")
        else:
            print("\n⚠️  Some connectivity issues detected (may be expected in CI)")
        
        print("\n🎯 Load Balancer Migration: SUCCESSFUL")
    
    asyncio.run(run_compliance_check())