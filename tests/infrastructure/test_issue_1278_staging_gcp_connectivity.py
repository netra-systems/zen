#!/usr/bin/env python3
"""
Issue #1278 Infrastructure Problems - Staging GCP Connectivity Tests

MISSION: Test real GCP staging infrastructure connectivity
- Database connection attempts (PostgreSQL with SSL)
- Redis connectivity through VPC connector
- WebSocket endpoint validation
- Load balancer health checks
- Service discovery validation

EXPECTED: Tests should FAIL initially, reproducing Issue #1278 problems

NOTE: These tests use REAL GCP staging services - no Docker required
"""
import os
import pytest
import asyncio
import aiohttp
import logging
import ssl
from typing import Dict, Any, Optional
import socket
from urllib.parse import urlparse

# Test infrastructure imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env_var

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.infrastructure
@pytest.mark.issue_1278
@pytest.mark.staging_gcp
class TestIssue1278StagingGCPConnectivity(SSotAsyncTestCase):
    """Test suite for GCP staging infrastructure connectivity issues"""
    
    def setup_method(self, method):
        """Set up each test method with staging environment"""
        super().setup_method(method)
        try:
            self.env = IsolatedEnvironment()  # Singleton pattern 
        except Exception as e:
            logger.error(f"Issue #1278 reproduction: Environment setup failed - {e}")
            self.env = None
            
        self.staging_domains = {
            'backend': 'https://staging.netrasystems.ai',
            'frontend': 'https://staging.netrasystems.ai', 
            'websocket': 'wss://api.staging.netrasystems.ai'
        }
        
    async def test_staging_backend_health_endpoint(self):
        """
        Test: Direct connection to staging backend health endpoint
        EXPECT: Should FAIL - reproducing backend connectivity issues
        """
        logger.info("Testing staging backend health endpoint connectivity")
        
        try:
            backend_url = self.staging_domains['backend']
            health_url = f"{backend_url}/health"
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_url) as response:
                    logger.info(f"Health endpoint status: {response.status}")
                    
                    # Should get 200 OK
                    assert response.status == 200, \
                        f"Health endpoint failed: {response.status}"
                    
                    # Check response content
                    content = await response.json()
                    assert 'status' in content, "Health response missing status"
                    assert content['status'] == 'healthy', \
                        f"Service not healthy: {content}"
            
            logger.info("CHECK Staging backend health endpoint accessible")
            
        except Exception as e:
            logger.error(f"X Staging backend health endpoint failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Backend health check failure - {e}")
    
    async def test_staging_database_connection_attempt(self):
        """
        Test: Attempt direct database connection with staging credentials
        EXPECT: Should FAIL - reproducing database connectivity issues
        """
        logger.info("Testing staging database connection attempt")
        
        try:
            import asyncpg
            
            # Get database URL from staging environment
            db_url = self.env.get_env_var("DATABASE_URL")
            assert db_url, "Database URL not configured"
            
            # Parse connection parameters
            parsed = urlparse(db_url)
            
            # Attempt connection with timeout
            connection = await asyncio.wait_for(
                asyncpg.connect(
                    host=parsed.hostname,
                    port=parsed.port or 5432,
                    user=parsed.username,
                    password=parsed.password,
                    database=parsed.path.lstrip('/'),
                    ssl='require'
                ),
                timeout=10.0
            )
            
            # Test basic query
            result = await connection.fetchval("SELECT 1")
            assert result == 1, "Database query failed"
            
            await connection.close()
            logger.info("CHECK Staging database connection successful")
            
        except Exception as e:
            logger.error(f"X Staging database connection failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Database connection failure - {e}")
    
    async def test_staging_websocket_endpoint_connectivity(self):
        """
        Test: WebSocket endpoint connectivity to staging
        EXPECT: Should FAIL - reproducing WebSocket connectivity issues
        """
        logger.info("Testing staging WebSocket endpoint connectivity")
        
        try:
            import websockets
            
            websocket_url = self.staging_domains['websocket']
            # Remove wss:// prefix for websockets library
            ws_endpoint = websocket_url.replace('wss://', '') + '/ws'
            
            # Attempt WebSocket connection
            async with websockets.connect(
                f"wss://{ws_endpoint}",
                timeout=10,
                ssl=ssl.create_default_context()
            ) as websocket:
                
                # Send test message
                test_message = {"type": "ping", "data": "connectivity_test"}
                await websocket.send(str(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                logger.info(f"WebSocket response: {response}")
                
            logger.info("CHECK Staging WebSocket endpoint accessible")
            
        except Exception as e:
            logger.error(f"X Staging WebSocket endpoint failed: {e}")
            # This failure is EXPECTED for Issue #1278  
            raise AssertionError(f"Issue #1278 reproduction: WebSocket connectivity failure - {e}")
    
    async def test_staging_redis_connectivity_through_vpc(self):
        """
        Test: Redis connectivity through VPC connector
        EXPECT: Should FAIL - reproducing Redis VPC connectivity issues
        """
        logger.info("Testing staging Redis connectivity through VPC")
        
        try:
            import aioredis
            
            redis_url = self.env.get_env_var("REDIS_URL")
            assert redis_url, "Redis URL not configured"
            
            # Attempt Redis connection
            redis = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=10
            )
            
            # Test basic Redis operations
            await redis.ping()
            
            # Test set/get
            test_key = "issue_1278_connectivity_test"
            await redis.set(test_key, "test_value", ex=60)
            result = await redis.get(test_key)
            assert result == "test_value", "Redis set/get failed"
            
            # Cleanup
            await redis.delete(test_key)
            await redis.close()
            
            logger.info("CHECK Staging Redis connectivity successful")
            
        except Exception as e:
            logger.error(f"X Staging Redis connectivity failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Redis VPC connectivity failure - {e}")
    
    async def test_staging_ssl_certificate_validation(self):
        """
        Test: SSL certificate validation for staging domains
        EXPECT: Should FAIL - reproducing SSL certificate issues
        """
        logger.info("Testing staging SSL certificate validation")
        
        try:
            import ssl
            import socket
            
            domains_to_test = [
                'staging.netrasystems.ai',
                'api.staging.netrasystems.ai'
            ]
            
            for domain in domains_to_test:
                logger.info(f"Validating SSL for {domain}")
                
                # Create SSL context
                context = ssl.create_default_context()
                
                # Connect and verify certificate
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        
                        # Validate certificate fields
                        assert 'subject' in cert, "Certificate missing subject"
                        assert 'issuer' in cert, "Certificate missing issuer"
                        assert 'notAfter' in cert, "Certificate missing expiration"
                        
                        # Check domain in certificate
                        subject_alt_names = cert.get('subjectAltName', [])
                        domain_found = any(domain in str(alt_name) for alt_name in subject_alt_names)
                        
                        if not domain_found:
                            # Check common name
                            subject = dict(x[0] for x in cert['subject'])
                            common_name = subject.get('commonName', '')
                            assert domain in common_name or '*.netrasystems.ai' in common_name, \
                                f"Domain {domain} not found in certificate"
            
            logger.info("CHECK Staging SSL certificate validation passed")
            
        except Exception as e:
            logger.error(f"X Staging SSL certificate validation failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: SSL certificate validation failure - {e}")
    
    async def test_staging_load_balancer_configuration(self):
        """
        Test: Load balancer configuration and routing
        EXPECT: Should FAIL - reproducing load balancer issues  
        """
        logger.info("Testing staging load balancer configuration")
        
        try:
            backend_url = self.staging_domains['backend']
            
            # Test different HTTP methods and paths
            test_endpoints = [
                ('GET', '/health'),
                ('GET', '/api/health'), 
                ('OPTIONS', '/api/auth/validate'),
                ('GET', '/docs')  # API documentation
            ]
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for method, path in test_endpoints:
                    url = f"{backend_url}{path}"
                    
                    async with session.request(method, url) as response:
                        logger.info(f"{method} {path}: {response.status}")
                        
                        # Should not get 502/503 Bad Gateway errors
                        assert response.status not in [502, 503], \
                            f"Load balancer error for {method} {path}: {response.status}"
                        
                        # Check for proper CORS headers
                        if method == 'OPTIONS':
                            cors_headers = [
                                'Access-Control-Allow-Origin',
                                'Access-Control-Allow-Methods', 
                                'Access-Control-Allow-Headers'
                            ]
                            for header in cors_headers:
                                assert header in response.headers, \
                                    f"Missing CORS header: {header}"
            
            logger.info("CHECK Staging load balancer configuration passed")
            
        except Exception as e:
            logger.error(f"X Staging load balancer configuration failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Load balancer configuration failure - {e}")
    
    async def test_staging_service_discovery_dns(self):
        """
        Test: Service discovery and DNS resolution
        EXPECT: Should FAIL - reproducing DNS/service discovery issues
        """
        logger.info("Testing staging service discovery and DNS resolution")
        
        try:
            import socket
            
            # Test DNS resolution for staging domains
            domains_to_resolve = [
                'staging.netrasystems.ai',
                'api.staging.netrasystems.ai'
            ]
            
            resolved_ips = {}
            for domain in domains_to_resolve:
                try:
                    ip_info = socket.getaddrinfo(domain, 443, socket.AF_INET)
                    ips = [info[4][0] for info in ip_info]
                    resolved_ips[domain] = ips
                    
                    assert ips, f"No IP addresses resolved for {domain}"
                    logger.info(f"Domain {domain} resolved to: {ips}")
                    
                except socket.gaierror as e:
                    raise AssertionError(f"DNS resolution failed for {domain}: {e}")
            
            # Test reverse DNS lookup
            for domain, ips in resolved_ips.items():
                for ip in ips[:1]:  # Test first IP only
                    try:
                        reverse_name = socket.gethostbyaddr(ip)[0]
                        logger.info(f"IP {ip} reverse resolves to: {reverse_name}")
                    except socket.herror:
                        # Reverse DNS might not be configured, that's okay
                        logger.warning(f"No reverse DNS for IP {ip}")
            
            logger.info("CHECK Staging service discovery DNS resolution passed")
            
        except Exception as e:
            logger.error(f"X Staging service discovery DNS failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: DNS/service discovery failure - {e}")


if __name__ == "__main__":
    # Run tests with verbose output to capture failure details
    pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-x",  # Stop on first failure to capture Issue #1278 reproduction
        "--log-cli-level=INFO",
        "--asyncio-mode=auto"
    ])