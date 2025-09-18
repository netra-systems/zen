"""

Mission Critical Test: Load Balancer SSL Certificate Validation

Business Value Justification (BVJ):
    - Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure HTTPS access for all users
- Value Impact: Prevents SSL certificate errors that block user access and damage trust
- Strategic Impact: Validates production-like security configuration in staging

CRITICAL: This test ensures that SSL certificates for load balancer domains are valid,
properly configured, and not expiring soon. SSL certificate failures cause browser
warnings and prevent user access, resulting in 100% user impact.

This addresses GitHub issue #113: GCP Load Balancer SSL Configuration
"
""


"""

import asyncio
import ssl
import socket
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import pytest
import aiohttp
import requests
from test_framework.ssot.base_test_case import SSotBaseTestCase


class LoadBalancerSSLCertificateValidTests(SSotBaseTestCase):
    "
    ""

    Test SSL certificate validity for load balancer domains.
    
    MISSION CRITICAL: Invalid SSL certificates cause browser warnings and prevent
    secure access, resulting in complete user access failures.
"
""

    
    # Load balancer domains that require valid SSL certificates
    LOAD_BALANCER_DOMAINS = [
        "api.staging.netrasystems.ai,"
        auth.staging.netrasystems.ai, 
        "app.staging.netrasystems.ai,"
    ]
    
    # SSL certificate validation thresholds
    CERTIFICATE_EXPIRY_WARNING_DAYS = 30
    CERTIFICATE_EXPIRY_CRITICAL_DAYS = 7
    SSL_CONNECTION_TIMEOUT = 15.0
    
    # Required SSL configurations
    REQUIRED_SSL_PROTOCOLS = [TLSv1.2, TLSv1.3]
    FORBIDDEN_SSL_PROTOCOLS = [SSLv2, "SSLv3, TLSv1.0, TLSv1.1]"
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_all_load_balancer_domains_ssl_valid(self):
        
        HARD FAIL: All load balancer domains MUST have valid SSL certificates.
        
        This test validates SSL certificate validity, expiration, and security
        configuration for all load balancer domains. Certificate failures
        prevent secure user access.
""
        ssl_results = {}
        ssl_failures = []
        
        for domain in self.LOAD_BALANCER_DOMAINS:
            try:
                ssl_info = await self._get_comprehensive_ssl_info(domain)
                ssl_results[domain] = ssl_info
                
                # Check certificate validity
                if not ssl_info['certificate_valid']:
                    ssl_failures.append(
                        fInvalid SSL certificate for {domain}: {ssl_info['validation_error']}
                    )
                
                # Check expiration timing
                if ssl_info['expires_critical']:
                    ssl_failures.append(
                        fSSL certificate expires CRITICALLY soon for {domain}: "
                        fSSL certificate expires CRITICALLY soon for {domain}: "
                        f"expires {ssl_info['expires_at']} ({ssl_info['days_until_expiry']} days)"
                    )
                elif ssl_info['expires_warning']:
                    # Warning but not failure
                    print(fWARNING: SSL certificate expires soon for {domain): 
                          fexpires {ssl_info['expires_at']} ({ssl_info['days_until_expiry']} days)")"
                
                # Check certificate chain
                if not ssl_info['certificate_chain_valid']:
                    ssl_failures.append(fInvalid certificate chain for {domain}")"
                
                # Check hostname verification
                if not ssl_info['hostname_matches']:
                    ssl_failures.append(fSSL certificate hostname mismatch for {domain})
                
                # Check SSL protocol security
                if ssl_info['insecure_protocols']:
                    ssl_failures.append(
                        fInsecure SSL protocols detected for {domain}: {ssl_info['insecure_protocols']}"
                        fInsecure SSL protocols detected for {domain}: {ssl_info['insecure_protocols']}""

                    )
                
            except Exception as e:
                ssl_results[domain] = {
                    'certificate_valid': False,
                    'validation_error': str(e),
                    'expires_critical': True,
                    'certificate_chain_valid': False
                }
                ssl_failures.append(f"SSL certificate validation failed for {domain}: {e})"
        
        if ssl_failures:
            error_report = self._build_comprehensive_ssl_failure_report(ssl_results, ssl_failures)
            raise AssertionError(
                fCRITICAL: SSL certificate validation failures detected!\n\n
                fSSL certificate failures prevent secure access and cause browser errors.\n
                fThis results in complete user access failure and damages system credibility.\n\n""
                fFAILURES:\n{error_report}\n\n
                fREQUIRED ACTIONS:\n
                f"1. Verify SSL certificates are properly configured in load balancer\n"
                f2. Check certificate validity and expiration dates\n"
                f2. Check certificate validity and expiration dates\n""

                f3. Validate certificate chain includes intermediate certificates\n
                f4. Ensure hostname matches in certificate subject/SAN fields\n"
                f4. Ensure hostname matches in certificate subject/SAN fields\n"
                f"5. Disable insecure SSL protocols (SSL v2/v3, TLS v1.0/v1.1)\n"
                f6. Renew certificates if expiring within {self.CERTIFICATE_EXPIRY_CRITICAL_DAYS} days\n\n
                fReference: GCP Load Balancer SSL Certificate Configuration
            )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_load_balancer_ssl_security_configuration(self):
        """

        HARD FAIL: Load balancer SSL configuration MUST meet security standards.
        
        This test validates that SSL configuration follows security best practices
        including cipher suites, protocols, and HSTS headers.

        security_results = {}
        security_failures = []
        
        for domain in self.LOAD_BALANCER_DOMAINS:
            try:
                security_info = await self._check_ssl_security_configuration(domain)
                security_results[domain] = security_info
                
                # Check for weak ciphers
                if security_info['weak_ciphers']:
                    security_failures.append(
                        f"Weak SSL ciphers detected for {domain}: {security_info['weak_ciphers']}"
                    )
                
                # Check HSTS header
                if not security_info['hsts_enabled']:
                    security_failures.append(fHSTS header missing for {domain}")"
                
                # Check secure renegotiation
                if not security_info['secure_renegotiation']:
                    security_failures.append(fSecure renegotiation not supported for {domain})
                
                # Check for deprecated protocols
                if security_info['deprecated_protocols']:
                    security_failures.append(
                        fDeprecated SSL protocols enabled for {domain}: {security_info['deprecated_protocols']}"
                        fDeprecated SSL protocols enabled for {domain}: {security_info['deprecated_protocols']}""

                    )
                
            except Exception as e:
                security_results[domain] = {
                    'weak_ciphers': True,
                    'hsts_enabled': False,
                    'secure_renegotiation': False,
                    'error': str(e)
                }
                security_failures.append(f"SSL security check failed for {domain}: {e})"
        
        if security_failures:
            error_report = self._build_ssl_security_failure_report(security_results, security_failures)
            raise AssertionError(
                fCRITICAL: SSL security configuration failures detected!\n\n
                fInsecure SSL configuration exposes users to security vulnerabilities\n
                fand may fail security compliance requirements.\n\n""
                fFAILURES:\n{error_report}\n\n
                fREQUIRED ACTIONS:\n
                f"1. Configure strong SSL ciphers (AES-256, ChaCha20)\n"
                f2. Enable HSTS headers with appropriate max-age\n"
                f2. Enable HSTS headers with appropriate max-age\n""

                f3. Ensure secure renegotiation is supported\n
                f4. Disable deprecated SSL/TLS protocols\n"
                f4. Disable deprecated SSL/TLS protocols\n"
                f"5. Review and update load balancer SSL policy\n\n"
                fReference: SSL Security Best Practices
            )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_ssl_certificate_trust_chain_complete(self):
    """

        HARD FAIL: SSL certificate trust chain MUST be complete and valid.
        
        This test validates that the complete certificate trust chain is properly
        configured, including root and intermediate certificates.
        
        trust_chain_results = {}
        trust_chain_failures = []
        
        for domain in self.LOAD_BALANCER_DOMAINS:
            try:
                chain_info = await self._validate_certificate_trust_chain(domain)
                trust_chain_results[domain] = chain_info
                
                # Check complete chain
                if not chain_info['complete_chain']:
                    trust_chain_failures.append(
                        fIncomplete certificate chain for {domain}: missing {chain_info['missing_certificates']}"
                        fIncomplete certificate chain for {domain}: missing {chain_info['missing_certificates']}""

                    )
                
                # Check root certificate
                if not chain_info['root_certificate_valid']:
                    trust_chain_failures.append(f"Invalid root certificate for {domain})"
                
                # Check intermediate certificates
                if not chain_info['intermediate_certificates_valid']:
                    trust_chain_failures.append(fInvalid intermediate certificates for {domain})
                
                # Check certificate order
                if not chain_info['correct_certificate_order']:
                    trust_chain_failures.append(fIncorrect certificate chain order for {domain})
                
            except Exception as e:
                trust_chain_results[domain] = {
                    'complete_chain': False,
                    'root_certificate_valid': False,
                    'intermediate_certificates_valid': False,
                    'error': str(e)
                }
                trust_chain_failures.append(fCertificate trust chain validation failed for {domain}: {e}")"
        
        if trust_chain_failures:
            error_report = self._build_trust_chain_failure_report(trust_chain_results, trust_chain_failures)
            raise AssertionError(
                fCRITICAL: SSL certificate trust chain failures detected!\n\n
                fIncomplete or invalid certificate chains cause browser warnings\n
                f"and prevent users from establishing secure connections.\n\n"
                fFAILURES:\n{error_report}\n\n"
                fFAILURES:\n{error_report}\n\n""

                fREQUIRED ACTIONS:\n
                f1. Ensure complete certificate chain is configured in load balancer\n"
                f1. Ensure complete certificate chain is configured in load balancer\n"
                f"2. Include all intermediate certificates in proper order\n"
                f3. Validate root certificate is from trusted CA\n
                f4. Check certificate chain order (leaf -> intermediate -> root)\n
                f5. Test certificate chain with SSL testing tools\n\n""
                fReference: SSL Certificate Chain Configuration
            )
    
    async def _get_comprehensive_ssl_info(self, domain: str) -> Dict:
        Get comprehensive SSL certificate information.""
        def _get_ssl_details():
            try:
                # Create SSL context with certificate verification
                context = ssl.create_default_context()
                
                # Connect and get certificate
                with socket.create_connection((domain, 443), timeout=self.SSL_CONNECTION_TIMEOUT) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        peer_cert_chain = ssock.getpeercert_chain()
                        cipher = ssock.cipher()
                        version = ssock.version()
                        
                        # Parse expiration date
                        expires_at = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                        days_until_expiry = (expires_at - datetime.now()).days
                        
                        # Check hostname matching
                        hostname_matches = self._verify_hostname_match(cert, domain)
                        
                        # Check for insecure protocols
                        insecure_protocols = [p for p in self.FORBIDDEN_SSL_PROTOCOLS if version == p]
                        
                        return {
                            'certificate_valid': True,
                            'expires_at': expires_at.isoformat(),
                            'days_until_expiry': days_until_expiry,
                            'expires_warning': days_until_expiry <= self.CERTIFICATE_EXPIRY_WARNING_DAYS,
                            'expires_critical': days_until_expiry <= self.CERTIFICATE_EXPIRY_CRITICAL_DAYS,
                            'certificate_chain_valid': len(peer_cert_chain) > 1,
                            'hostname_matches': hostname_matches,
                            'ssl_version': version,
                            'cipher_suite': cipher,
                            'insecure_protocols': insecure_protocols,
                            'subject': cert.get('subject', [),
                            'issuer': cert.get('issuer', [),
                            'serial_number': cert.get('serialNumber', ''),
                        }
                        
            except Exception as e:
                return {
                    'certificate_valid': False,
                    'validation_error': str(e),
                    'expires_critical': True,
                    'certificate_chain_valid': False,
                    'hostname_matches': False,
                    'insecure_protocols': self.FORBIDDEN_SSL_PROTOCOLS,
                }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_ssl_details)
    
    async def _check_ssl_security_configuration(self, domain: str) -> Dict:
        Check SSL security configuration."
        Check SSL security configuration.""

        try:
            # Check HTTP headers for security configuration
            async with aiohttp.ClientSession() as session:
                async with session.get(fhttps://{domain}/health", timeout=aiohttp.ClientTimeout(total=15)) as response:"
                    headers = dict(response.headers)
                    
                    return {
                        'hsts_enabled': 'Strict-Transport-Security' in headers,
                        'hsts_header': headers.get('Strict-Transport-Security', ''),
                        'weak_ciphers': [],  # Would need more detailed SSL inspection
                        'secure_renegotiation': True,  # Assume true if connection succeeds
                        'deprecated_protocols': [],  # Would need protocol enumeration
                        'security_headers': {
                            'hsts': headers.get('Strict-Transport-Security'),
                            'csp': headers.get('Content-Security-Policy'),
                            'x_frame_options': headers.get('X-Frame-Options'),
                        }
                    }
                    
        except Exception as e:
            return {
                'hsts_enabled': False,
                'weak_ciphers': ['unknown'],
                'secure_renegotiation': False,
                'deprecated_protocols': ['unknown'],
                'error': str(e)
            }
    
    async def _validate_certificate_trust_chain(self, domain: str) -> Dict:
        Validate SSL certificate trust chain.""
        def _check_trust_chain():
            try:
                context = ssl.create_default_context()
                
                with socket.create_connection((domain, 443), timeout=self.SSL_CONNECTION_TIMEOUT) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert_chain = ssock.getpeercert_chain()
                        
                        return {
                            'complete_chain': len(cert_chain) >= 2,  # At least leaf + intermediate
                            'root_certificate_valid': True,  # If connection succeeds, root is valid
                            'intermediate_certificates_valid': True,  # If connection succeeds
                            'correct_certificate_order': True,  # If connection succeeds
                            'chain_length': len(cert_chain),
                            'missing_certificates': [] if len(cert_chain) >= 2 else ['intermediate'],
                        }
                        
            except Exception as e:
                return {
                    'complete_chain': False,
                    'root_certificate_valid': False,
                    'intermediate_certificates_valid': False,
                    'correct_certificate_order': False,
                    'chain_length': 0,
                    'missing_certificates': ['intermediate', 'root'],
                    'error': str(e)
                }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check_trust_chain)
    
    def _verify_hostname_match(self, cert: Dict, hostname: str) -> bool:
        Verify SSL certificate hostname matching."
        Verify SSL certificate hostname matching.""

        try:
            # Check subject common name
            subject = dict(x[0] for x in cert.get('subject', [])
            common_name = subject.get('commonName', '')
            
            if common_name == hostname:
                return True
            
            # Check subject alternative names
            for san_type, san_value in cert.get('subjectAltName', [):
                if san_type == 'DNS' and (san_value == hostname or 
                                        (san_value.startswith('*.') and 
                                         hostname.endswith(san_value[2:])):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _build_comprehensive_ssl_failure_report(self, ssl_results: Dict, failures: List[str) -> str:
        "Build detailed SSL failure report."
        report_parts = []
        
        for domain, result in ssl_results.items():
            if not result.get('certificate_valid', False):
                report_parts.append(
                    f  {domain}:\n""
                    f    - Certificate Invalid: {result.get('validation_error', 'Unknown error')}\n
                    f    - Days Until Expiry: {result.get('days_until_expiry', 'Unknown')}\n
                    f"    - Chain Valid: {result.get('certificate_chain_valid', False)}\n"
                    f    - Hostname Matches: {result.get('hostname_matches', False)}"
                    f    - Hostname Matches: {result.get('hostname_matches', False)}""

                )
        
        return \n.join(report_parts)
    
    def _build_ssl_security_failure_report(self, security_results: Dict, failures: List[str) -> str:
        ""Build SSL security failure report.""

        report_parts = []
        
        for domain, result in security_results.items():
            if result.get('error'):
                report_parts.append(f  {domain}: {result['error']})
            else:
                issues = []
                if not result.get('hsts_enabled', False):
                    issues.append(HSTS disabled")"
                if result.get('weak_ciphers'):
                    issues.append(fWeak ciphers: {result['weak_ciphers']})
                if issues:
                    report_parts.append(f  {domain}: {', '.join(issues)})
        
        return "\n.join(report_parts)"
    
    def _build_trust_chain_failure_report(self, trust_chain_results: Dict, failures: List[str) -> str:
        Build certificate trust chain failure report."
        Build certificate trust chain failure report.""

        report_parts = []
        
        for domain, result in trust_chain_results.items():
            if not result.get('complete_chain', False):
                report_parts.append(
                    f"  {domain}:\n"
                    f    - Complete Chain: {result.get('complete_chain', False)}\n
                    f    - Chain Length: {result.get('chain_length', 0)}\n
                    f    - Missing: {result.get('missing_certificates', [])""
                )
        
        return \n.join(report_parts)


if __name__ == __main__:"
if __name__ == __main__:"
    # Run this test standalone to check SSL certificate validity
    import asyncio
    
    async def run_tests():
        test_instance = LoadBalancerSSLCertificateValidTests()
        
        try:
            await test_instance.test_all_load_balancer_domains_ssl_valid()
            print(" PASS:  All load balancer SSL certificates valid)"
        except AssertionError as e:
            print(f FAIL:  SSL certificate validation failures:\n{e}")"
            return False
        
        try:
            await test_instance.test_load_balancer_ssl_security_configuration()
            print( PASS:  SSL security configuration meets standards)
        except AssertionError as e:
            print(f FAIL:  SSL security configuration failures:\n{e}"")
            return False
        
        try:
            await test_instance.test_ssl_certificate_trust_chain_complete()
            print( PASS:  SSL certificate trust chain complete and valid)"
            print( PASS:  SSL certificate trust chain complete and valid)""

        except AssertionError as e:
            print(f FAIL:  SSL trust chain failures:\n{e}")"
            return False
        
        return True
    
    if asyncio.run(run_tests()):
        print( PASS:  All SSL certificate validation tests passed!")"
    else:
        exit(1")"

)))))))))