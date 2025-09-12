"""
Mission Critical Test: Staging Domains Resolve Correctly

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure staging infrastructure accessibility
- Value Impact: Prevents DNS resolution failures that block all user access
- Strategic Impact: Validates production-like domain resolution for staging environment

CRITICAL: This test ensures that all *.staging.netrasystems.ai domains resolve correctly
and are accessible from the test environment. DNS resolution failures cause complete
system inaccessibility for all user segments.

This addresses GitHub issue #113: GCP Load Balancer DNS Configuration
"""

import asyncio
import socket
import ssl
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pytest
import aiohttp
import dns.resolver
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestStagingDomainsResolveCorrectly(SSotBaseTestCase):
    """
    Test that all staging domains resolve correctly and are accessible.
    
    MISSION CRITICAL: DNS resolution failures prevent ALL users from accessing
    the staging environment, blocking development and testing workflows.
    """
    
    # Critical staging domains that MUST resolve
    CRITICAL_STAGING_DOMAINS = [
        "api.staging.netrasystems.ai",
        "auth.staging.netrasystems.ai", 
        "app.staging.netrasystems.ai",
    ]
    
    # Maximum acceptable DNS resolution time (seconds)
    MAX_DNS_RESOLUTION_TIME = 5.0
    
    # Maximum acceptable HTTP response time (seconds)
    MAX_HTTP_RESPONSE_TIME = 30.0
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_all_staging_domains_resolve_dns(self):
        """
        HARD FAIL: All staging domains MUST resolve via DNS.
        
        This test validates that DNS resolution works for all critical staging domains.
        DNS resolution failure means complete inaccessibility for users.
        """
        dns_results = {}
        dns_failures = []
        
        for domain in self.CRITICAL_STAGING_DOMAINS:
            try:
                start_time = time.time()
                ip_addresses = await self._resolve_domain_async(domain)
                resolution_time = time.time() - start_time
                
                dns_results[domain] = {
                    'ip_addresses': ip_addresses,
                    'resolution_time': resolution_time,
                    'success': True
                }
                
                # Validate resolution time
                if resolution_time > self.MAX_DNS_RESOLUTION_TIME:
                    dns_failures.append(
                        f"DNS resolution too slow for {domain}: {resolution_time:.2f}s > {self.MAX_DNS_RESOLUTION_TIME}s"
                    )
                
                # Validate we got IP addresses
                if not ip_addresses:
                    dns_failures.append(f"No IP addresses resolved for {domain}")
                    
            except Exception as e:
                dns_results[domain] = {
                    'ip_addresses': [],
                    'resolution_time': None,
                    'success': False,
                    'error': str(e)
                }
                dns_failures.append(f"DNS resolution failed for {domain}: {e}")
        
        if dns_failures:
            error_report = self._build_dns_failure_report(dns_results, dns_failures)
            raise AssertionError(
                f"CRITICAL: DNS resolution failures detected!\n\n"
                f"DNS resolution failures prevent ALL users from accessing staging.\n"
                f"This is a complete system outage condition.\n\n"
                f"FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Verify DNS records are configured for *.staging.netrasystems.ai\n"
                f"2. Check load balancer DNS configuration in GCP\n"
                f"3. Validate domain propagation across DNS servers\n"
                f"4. Ensure load balancer has proper external IP allocation\n\n"
                f"Reference: GCP Load Balancer DNS Configuration"
            )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_all_staging_domains_accessible_https(self):
        """
        HARD FAIL: All staging domains MUST be accessible via HTTPS.
        
        This test validates that HTTPS connections work to all staging domains.
        HTTPS accessibility failures mean users cannot access the application.
        """
        https_results = {}
        https_failures = []
        
        timeout = aiohttp.ClientTimeout(total=self.MAX_HTTP_RESPONSE_TIME)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for domain in self.CRITICAL_STAGING_DOMAINS:
                url = f"https://{domain}/health"
                
                try:
                    start_time = time.time()
                    async with session.get(url) as response:
                        response_time = time.time() - start_time
                        
                        https_results[domain] = {
                            'status_code': response.status,
                            'response_time': response_time,
                            'success': 200 <= response.status < 500,  # 4xx is OK, 5xx is not
                            'headers': dict(response.headers),
                        }
                        
                        # 5xx errors indicate infrastructure problems
                        if response.status >= 500:
                            https_failures.append(
                                f"Server error for {domain}: HTTP {response.status}"
                            )
                        
                        # Very slow responses indicate infrastructure problems
                        if response_time > self.MAX_HTTP_RESPONSE_TIME:
                            https_failures.append(
                                f"Response too slow for {domain}: {response_time:.2f}s > {self.MAX_HTTP_RESPONSE_TIME}s"
                            )
                            
                except asyncio.TimeoutError:
                    https_results[domain] = {
                        'status_code': None,
                        'response_time': None,
                        'success': False,
                        'error': 'Timeout'
                    }
                    https_failures.append(f"Timeout connecting to {domain}")
                    
                except Exception as e:
                    https_results[domain] = {
                        'status_code': None,
                        'response_time': None,
                        'success': False,
                        'error': str(e)
                    }
                    https_failures.append(f"Connection failed to {domain}: {e}")
        
        if https_failures:
            error_report = self._build_https_failure_report(https_results, https_failures)
            raise AssertionError(
                f"CRITICAL: HTTPS accessibility failures detected!\n\n"
                f"HTTPS accessibility failures prevent users from accessing staging applications.\n"
                f"This indicates load balancer or service configuration problems.\n\n"
                f"FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Check load balancer health and routing configuration\n"
                f"2. Verify backend services are healthy and responding\n"
                f"3. Validate SSL certificate configuration\n"
                f"4. Check firewall and security group settings\n"
                f"5. Review load balancer timeout settings\n\n"
                f"Reference: Load Balancer Routing Validation"
            )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_staging_domains_ssl_certificates_valid(self):
        """
        HARD FAIL: All staging domains MUST have valid SSL certificates.
        
        This test validates SSL certificate validity for all staging domains.
        Invalid SSL certificates prevent secure access and cause browser errors.
        """
        ssl_results = {}
        ssl_failures = []
        
        for domain in self.CRITICAL_STAGING_DOMAINS:
            try:
                ssl_info = await self._get_ssl_certificate_info(domain)
                ssl_results[domain] = ssl_info
                
                # Check certificate validity
                if not ssl_info['valid']:
                    ssl_failures.append(f"Invalid SSL certificate for {domain}: {ssl_info['error']}")
                
                # Check expiration
                if ssl_info['expires_soon']:
                    ssl_failures.append(
                        f"SSL certificate expires soon for {domain}: expires {ssl_info['expires_at']}"
                    )
                
                # Check certificate chain
                if not ssl_info['chain_valid']:
                    ssl_failures.append(f"Invalid certificate chain for {domain}")
                    
            except Exception as e:
                ssl_results[domain] = {
                    'valid': False,
                    'error': str(e),
                    'expires_soon': True,
                    'chain_valid': False
                }
                ssl_failures.append(f"SSL certificate check failed for {domain}: {e}")
        
        if ssl_failures:
            error_report = self._build_ssl_failure_report(ssl_results, ssl_failures)
            raise AssertionError(
                f"CRITICAL: SSL certificate failures detected!\n\n"
                f"SSL certificate failures prevent secure access and cause browser warnings.\n"
                f"This blocks user access and damages system credibility.\n\n"
                f"FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Check SSL certificate configuration in load balancer\n"
                f"2. Verify certificate validity and expiration dates\n"
                f"3. Validate certificate chain and intermediate certificates\n"
                f"4. Update or renew certificates as needed\n"
                f"5. Test SSL configuration with SSL testing tools\n\n"
                f"Reference: Load Balancer SSL Certificate Configuration"
            )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    def test_staging_domains_match_expected_patterns(self):
        """
        HARD FAIL: Staging domains MUST follow expected naming patterns.
        
        This test validates that staging domains follow the expected
        *.staging.netrasystems.ai pattern and are properly configured.
        """
        pattern_failures = []
        expected_pattern = r"^[a-z]+\.staging\.netrasystems\.ai$"
        
        for domain in self.CRITICAL_STAGING_DOMAINS:
            import re
            if not re.match(expected_pattern, domain):
                pattern_failures.append(
                    f"Domain {domain} does not match expected pattern: {expected_pattern}"
                )
        
        # Check for required subdomains
        required_subdomains = {'api', 'auth', 'app'}
        actual_subdomains = set()
        
        for domain in self.CRITICAL_STAGING_DOMAINS:
            subdomain = domain.split('.')[0]
            actual_subdomains.add(subdomain)
        
        missing_subdomains = required_subdomains - actual_subdomains
        if missing_subdomains:
            pattern_failures.append(
                f"Missing required subdomains: {missing_subdomains}"
            )
        
        if pattern_failures:
            raise AssertionError(
                f"CRITICAL: Staging domain pattern violations!\n\n"
                f"Staging domains must follow *.staging.netrasystems.ai pattern\n"
                f"to ensure consistent DNS resolution and load balancer routing.\n\n"
                f"VIOLATIONS:\n" + "\n".join(f"  - {failure}" for failure in pattern_failures) + "\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Update domain configuration to use proper patterns\n"
                f"2. Ensure all required subdomains are configured\n"
                f"3. Update DNS records to match expected patterns\n"
                f"4. Validate load balancer routing for correct domains\n"
            )
    
    async def _resolve_domain_async(self, domain: str) -> List[str]:
        """Resolve domain to IP addresses asynchronously."""
        def _resolve():
            try:
                result = socket.getaddrinfo(domain, None)
                return list(set(info[4][0] for info in result))
            except Exception as e:
                raise e
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _resolve)
    
    async def _get_ssl_certificate_info(self, domain: str) -> Dict:
        """Get SSL certificate information for a domain."""
        def _get_cert_info():
            try:
                context = ssl.create_default_context()
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        
                        # Parse expiration date
                        expires_at = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                        expires_soon = expires_at < datetime.now() + timedelta(days=30)
                        
                        return {
                            'valid': True,
                            'expires_at': expires_at.isoformat(),
                            'expires_soon': expires_soon,
                            'chain_valid': True,  # If we got here, chain is valid
                            'subject': cert.get('subject', []),
                            'issuer': cert.get('issuer', []),
                        }
            except Exception as e:
                return {
                    'valid': False,
                    'error': str(e),
                    'expires_soon': True,
                    'chain_valid': False,
                }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_cert_info)
    
    def _build_dns_failure_report(self, dns_results: Dict, failures: List[str]) -> str:
        """Build detailed DNS failure report."""
        report_parts = []
        
        for domain, result in dns_results.items():
            if not result['success']:
                report_parts.append(f"  {domain}: {result.get('error', 'Unknown error')}")
            elif result['resolution_time'] and result['resolution_time'] > self.MAX_DNS_RESOLUTION_TIME:
                report_parts.append(
                    f"  {domain}: DNS resolution too slow ({result['resolution_time']:.2f}s)"
                )
        
        return "\n".join(report_parts)
    
    def _build_https_failure_report(self, https_results: Dict, failures: List[str]) -> str:
        """Build detailed HTTPS failure report."""
        report_parts = []
        
        for domain, result in https_results.items():
            if not result['success']:
                if result.get('error'):
                    report_parts.append(f"  {domain}: {result['error']}")
                elif result.get('status_code'):
                    report_parts.append(f"  {domain}: HTTP {result['status_code']}")
                else:
                    report_parts.append(f"  {domain}: Unknown HTTPS failure")
        
        return "\n".join(report_parts)
    
    def _build_ssl_failure_report(self, ssl_results: Dict, failures: List[str]) -> str:
        """Build detailed SSL failure report."""
        report_parts = []
        
        for domain, result in ssl_results.items():
            if not result['valid']:
                report_parts.append(f"  {domain}: {result.get('error', 'Invalid certificate')}")
            elif result['expires_soon']:
                report_parts.append(f"  {domain}: Certificate expires soon")
        
        return "\n".join(report_parts)


if __name__ == "__main__":
    # Run this test standalone to check staging domain resolution
    import asyncio
    
    async def run_tests():
        test_instance = TestStagingDomainsResolveCorrectly()
        
        try:
            await test_instance.test_all_staging_domains_resolve_dns()
            print(" PASS:  All staging domains resolve correctly via DNS")
        except AssertionError as e:
            print(f" FAIL:  DNS resolution failures:\n{e}")
            return False
        
        try:
            await test_instance.test_all_staging_domains_accessible_https()
            print(" PASS:  All staging domains accessible via HTTPS")
        except AssertionError as e:
            print(f" FAIL:  HTTPS accessibility failures:\n{e}")
            return False
        
        try:
            await test_instance.test_staging_domains_ssl_certificates_valid()
            print(" PASS:  All staging domain SSL certificates valid")
        except AssertionError as e:
            print(f" FAIL:  SSL certificate failures:\n{e}")
            return False
        
        try:
            test_instance.test_staging_domains_match_expected_patterns()
            print(" PASS:  All staging domains follow expected patterns")
        except AssertionError as e:
            print(f" FAIL:  Domain pattern violations:\n{e}")
            return False
        
        return True
    
    if asyncio.run(run_tests()):
        print(" PASS:  All staging domain resolution tests passed!")
    else:
        exit(1)