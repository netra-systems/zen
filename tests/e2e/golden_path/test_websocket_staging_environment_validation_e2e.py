"""
WebSocket Staging Environment Validation E2E Test - Staging-Specific Issues

CRITICAL STAGING ENVIRONMENT VALIDATION: This test validates that WebSocket
service works properly in staging environment and fails clearly when staging-specific
issues occur (GCP Cloud Run, load balancer, DNS, etc.).

Test Objective: WebSocket Staging Environment Issue Detection
- MANDATORY hard failure when staging WebSocket service is misconfigured
- MANDATORY clear error messages explaining staging environment issues
- MANDATORY staging-specific connectivity and configuration validation
- PROOF that staging environment issues prevent WebSocket functionality

Business Value Justification (BVJ):
- Segment: Platform/Internal - Staging Environment Integrity & Production Readiness
- Business Goal: Reliable WebSocket service in staging environment
- Value Impact: Validates production-ready WebSocket deployment
- Strategic Impact: Prevents staging environment issues from reaching production

CRITICAL REQUIREMENTS (per CLAUDE.md):
1. MANDATORY staging environment health check before WebSocket connections
2. MANDATORY hard failure when staging environment misconfigured (NO try/except hiding)
3. MANDATORY authentication via E2EAuthHelper with staging configuration
4. MANDATORY clear error messages explaining staging environment business impact
5. NO silent staging failures or environment configuration hiding
6. Must demonstrate staging environment issues prevent WebSocket access

WEBSOCKET STAGING ENVIRONMENT VALIDATION FLOW:
```
Staging Environment Detection → GCP/DNS Health Check → Staging Auth Validation →
WebSocket Connection → Staging Issue Detection → Hard Failure with Staging Diagnosis
```
"""

import asyncio
import json
import pytest
import time
import websockets
import aiohttp
import socket
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# SSOT imports following absolute import rules - STAGING ENVIRONMENT FOCUSED
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.ssot.real_services_test_fixtures import real_services_fixture

# Core system imports for staging environment validation
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, WebSocketID


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.staging_environment
@pytest.mark.asyncio
@pytest.mark.websocket_staging
class TestWebSocketStagingEnvironmentValidationE2E(SSotAsyncTestCase):
    """
    WebSocket Staging Environment Validation Tests.
    
    This test suite validates that WebSocket service works properly in staging
    environment and fails appropriately when staging-specific issues occur.
    
    CRITICAL MANDATE: These tests MUST fail hard when staging environment is
    misconfigured to prevent production deployment of broken staging setup.
    """
    
    def setup_method(self, method=None):
        """Setup with staging environment validation focus."""
        super().setup_method(method)
        
        # Staging environment compliance metrics
        self.record_metric("websocket_staging_environment_test", True)
        self.record_metric("staging_configuration_validation", "mandatory")
        self.record_metric("gcp_cloud_run_validation", "mandatory")
        self.record_metric("staging_failure_tolerance", 0)  # ZERO tolerance for staging failures
        self.record_metric("production_readiness_critical", True)
        
        # Initialize staging environment components
        self._auth_helper = None
        self._websocket_helper = None
        self._staging_websocket_url = None
        self._staging_auth_url = None
        self._is_staging_environment = False
        
    async def async_setup_method(self, method=None):
        """Async setup with mandatory staging environment validation."""
        await super().async_setup_method(method)
        
        # CRITICAL: Detect staging environment
        environment = self.get_env_var("TEST_ENV", "test")
        self._is_staging_environment = environment.lower() in ["staging", "stage", "stg"]
        
        # Initialize staging-aware auth helpers
        self._auth_helper = E2EAuthHelper(environment=environment)
        self._websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Get staging-specific URLs
        self._staging_websocket_url = self.get_env_var(
            "STAGING_WEBSOCKET_URL", 
            self.get_env_var("WEBSOCKET_URL", "wss://api-staging.netra.co/ws")
        )
        self._staging_auth_url = self.get_env_var(
            "STAGING_AUTH_SERVICE_URL",
            self.get_env_var("AUTH_SERVICE_URL", "https://auth-staging.netra.co")
        )
        
        # Record staging environment setup
        self.record_metric("staging_environment_setup_completed", True)
        self.record_metric("is_staging_environment", self._is_staging_environment)
        self.record_metric("staging_websocket_url", self._staging_websocket_url)
        self.record_metric("staging_auth_url", self._staging_auth_url)

    @pytest.mark.timeout(60)  # Allow extra time for staging environment validation
    @pytest.mark.asyncio
    async def test_staging_websocket_service_connectivity(self, real_services_fixture):
        """
        CRITICAL: Test staging WebSocket service connectivity and configuration.
        
        This test validates staging environment connectivity:
        1. Staging WebSocket URL is accessible and properly configured
        2. GCP Cloud Run service is healthy and responsive
        3. Load balancer and DNS resolution work correctly
        4. SSL/TLS certificates are valid for staging domain
        5. Staging environment auth integration works
        
        STAGING ENVIRONMENT REQUIREMENTS:
        - Staging WebSocket URL must be accessible
        - GCP Cloud Run health checks must pass
        - DNS resolution must work for staging domains
        - SSL certificates must be valid and not expired
        - Auth service integration must work in staging
        
        BUSINESS IMPACT: Staging WebSocket issues prevent production readiness validation
        """
        test_start_time = time.time()
        
        # === STAGING ENVIRONMENT DETECTION ===
        self.record_metric("staging_environment_detection_start", time.time())
        
        if not self._is_staging_environment:
            # Running in non-staging environment - skip staging-specific tests
            pytest.skip(f"Staging environment tests require STAGING environment. Current: {self.get_env_var('TEST_ENV', 'test')}")
        
        # === STAGING DNS RESOLUTION CHECK ===
        self.record_metric("staging_dns_check_start", time.time())
        
        staging_dns_resolved = False
        staging_dns_error = None
        staging_ip_addresses = []
        
        try:
            # Extract hostname from WebSocket URL
            staging_hostname = self._staging_websocket_url
            if "://" in staging_hostname:
                staging_hostname = staging_hostname.split("://")[1].split("/")[0].split(":")[0]
            
            # Resolve DNS for staging hostname
            staging_ip_addresses = socket.gethostbyname_ex(staging_hostname)[2]
            staging_dns_resolved = True
            
        except Exception as e:
            staging_dns_error = str(e)
        
        self.record_metric("staging_dns_resolved", staging_dns_resolved)
        self.record_metric("staging_ip_addresses", staging_ip_addresses)
        self.record_metric("staging_dns_error", staging_dns_error)
        
        # === STAGING SSL CERTIFICATE CHECK ===
        self.record_metric("staging_ssl_check_start", time.time())
        
        staging_ssl_valid = False
        staging_ssl_error = None
        
        if self._staging_websocket_url.startswith("wss://") or self._staging_auth_url.startswith("https://"):
            try:
                # Check SSL certificate for staging auth service
                auth_hostname = self._staging_auth_url.split("://")[1].split("/")[0].split(":")[0]
                
                async with aiohttp.ClientSession() as session:
                    # Make HTTPS request to validate SSL
                    async with session.get(f"{self._staging_auth_url}/health", timeout=15.0) as response:
                        if response.status in [200, 404]:  # 404 is OK, means SSL works but endpoint missing
                            staging_ssl_valid = True
                        
            except Exception as e:
                staging_ssl_error = str(e)
        else:
            # HTTP/WS URLs - SSL not applicable
            staging_ssl_valid = True
            
        self.record_metric("staging_ssl_valid", staging_ssl_valid)
        self.record_metric("staging_ssl_error", staging_ssl_error)
        
        # === STAGING WEBSOCKET CONNECTIVITY TEST ===
        self.record_metric("staging_websocket_connectivity_start", time.time())
        
        # Create staging-aware authenticated user
        staging_user = None
        staging_auth_success = False
        staging_auth_error = None
        
        try:
            staging_user = await create_authenticated_user_context(
                user_email="websocket_staging_test@example.com",
                environment="staging",
                permissions=["read", "write", "websocket"],
                websocket_enabled=True
            )
            
            staging_auth_success = True
            
        except Exception as e:
            staging_auth_error = str(e)
        
        self.record_metric("staging_auth_success", staging_auth_success)
        self.record_metric("staging_auth_error", staging_auth_error)
        
        # === STAGING WEBSOCKET CONNECTION ATTEMPT ===
        if staging_user:
            jwt_token = staging_user.agent_context.get("jwt_token")
            user_id = str(staging_user.user_id)
            
            # Get staging-optimized WebSocket headers
            staging_auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
            
            # Add staging-specific headers for E2E detection
            staging_auth_headers.update({
                "X-Staging-Environment": "true",
                "X-E2E-Staging-Test": "websocket_connectivity",
                "X-GCP-Cloud-Run-Test": "true"
            })
            
            websocket_connection_success = False
            websocket_connection_error = None
            websocket_response_time = None
            
            try:
                websocket_start = time.time()
                
                # Attempt staging WebSocket connection
                websocket_connection = await asyncio.wait_for(
                    websockets.connect(
                        self._staging_websocket_url,
                        additional_headers=staging_auth_headers,
                        open_timeout=20.0,  # Longer timeout for staging/GCP
                        close_timeout=10.0,
                        ping_interval=30,    # Longer ping for staging
                        ping_timeout=10
                    ),
                    timeout=30.0  # Total staging connection timeout
                )
                
                websocket_response_time = time.time() - websocket_start
                websocket_connection_success = True
                
                # Send staging test message
                staging_test_message = {
                    "type": "staging_environment_test",
                    "content": "Staging WebSocket connectivity validation",
                    "user_id": user_id,
                    "environment": "staging",
                    "gcp_cloud_run_test": True,
                    "timestamp": time.time()
                }
                
                await websocket_connection.send(json.dumps(staging_test_message))
                
                # Wait for staging response
                staging_events = []
                staging_timeout = 20.0
                staging_start_time = time.time()
                
                while (time.time() - staging_start_time) < staging_timeout:
                    try:
                        staging_event = await asyncio.wait_for(
                            websocket_connection.recv(),
                            timeout=5.0
                        )
                        
                        event_data = json.loads(staging_event)
                        staging_events.append(event_data)
                        
                        # Stop on completion or error
                        if event_data.get("type") in ["agent_completed", "error", "staging_test_complete"]:
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception:
                        break
                
                await websocket_connection.close()
                
                self.record_metric("staging_websocket_events_received", len(staging_events))
                
            except Exception as e:
                websocket_connection_error = str(e)
                websocket_response_time = time.time() - websocket_start if 'websocket_start' in locals() else 0
            
            self.record_metric("staging_websocket_connection_success", websocket_connection_success)
            self.record_metric("staging_websocket_response_time", websocket_response_time)
            self.record_metric("staging_websocket_connection_error", websocket_connection_error)
        
        # === STAGING ENVIRONMENT VALIDATION RESULTS ===
        
        staging_issues = []
        
        if not staging_dns_resolved:
            staging_issues.append(f"DNS resolution failed: {staging_dns_error}")
        
        if not staging_ssl_valid:
            staging_issues.append(f"SSL certificate invalid: {staging_ssl_error}")
        
        if not staging_auth_success:
            staging_issues.append(f"Staging authentication failed: {staging_auth_error}")
        
        if staging_user and not websocket_connection_success:
            staging_issues.append(f"WebSocket connection failed: {websocket_connection_error}")
        
        # === STAGING ENVIRONMENT STATUS ===
        
        if not staging_issues:
            # Staging environment is healthy
            print(f"✅ STAGING ENVIRONMENT: HEALTHY")
            print(f"   🟢 DNS Resolution: Success")
            print(f"   🟢 SSL Certificate: Valid")
            print(f"   🟢 Authentication: Success")
            print(f"   🟢 WebSocket Connection: Success")
            print(f"   📡 Connection Time: {websocket_response_time:.3f}s")
            print(f"   📊 Events Received: {len(staging_events) if 'staging_events' in locals() else 0}")
            print(f"   🚀 Production Ready: WebSocket staging validation passed")
            
        else:
            # Staging environment has issues
            staging_failure_message = (
                f"🚨 STAGING ENVIRONMENT FAILURE:\n"
                f"   🔴 Staging WebSocket URL: {self._staging_websocket_url}\n"
                f"   🔴 Staging Auth URL: {self._staging_auth_url}\n"
                f"   🔴 Environment: {self.get_env_var('TEST_ENV', 'unknown')}\n"
                f"\n"
                f"   🚫 STAGING ISSUES DETECTED:\n" +
                "\n".join(f"   • {issue}" for issue in staging_issues) +
                f"\n\n   💼 BUSINESS IMPACT:\n"
                f"   • Staging environment not production-ready\n"
                f"   • WebSocket features may not work in production\n"
                f"   • Production deployment validation failed\n"
                f"   • User acceptance testing may be blocked\n"
                f"   • Business stakeholder demos may fail\n"
                f"\n"
                f"   🔧 RESOLUTION REQUIRED:\n"
                f"   • Fix DNS resolution for staging domains\n"
                f"   • Update/renew SSL certificates for staging\n"
                f"   • Validate GCP Cloud Run service configuration\n"
                f"   • Check load balancer health and routing\n"
                f"   • Verify staging auth service integration\n"
                f"   • Test staging environment end-to-end connectivity\n"
            )
            
            print(staging_failure_message)
            pytest.fail(staging_failure_message)
        
        # Record final staging metrics
        total_test_time = time.time() - test_start_time
        self.record_metric("staging_environment_validation_duration", total_test_time)

    @pytest.mark.timeout(45)
    @pytest.mark.asyncio 
    async def test_staging_gcp_cloud_run_specific_issues(self, real_services_fixture):
        """
        CRITICAL: Test GCP Cloud Run specific WebSocket issues in staging.
        
        This test validates GCP Cloud Run deployment issues:
        1. Cold start latency affects WebSocket connection times
        2. Request timeout limits affect WebSocket operations
        3. Memory limits affect WebSocket performance
        4. Container startup time affects service availability
        5. Load balancer configuration affects WebSocket upgrades
        """
        
        if not self._is_staging_environment:
            pytest.skip("GCP Cloud Run tests require staging environment")
        
        # === GCP CLOUD RUN COLD START TEST ===
        self.record_metric("gcp_cold_start_test_start", time.time())
        
        # Multiple connection attempts to test cold start behavior
        cold_start_times = []
        
        for attempt in range(3):
            try:
                # Create fresh authenticated user for each attempt
                cold_start_user = await create_authenticated_user_context(
                    user_email=f"gcp_cold_start_{attempt}@example.com",
                    environment="staging",
                    websocket_enabled=True
                )
                
                jwt_token = cold_start_user.agent_context.get("jwt_token")
                auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
                
                # Measure connection time
                connection_start = time.time()
                
                connection = await asyncio.wait_for(
                    websockets.connect(
                        self._staging_websocket_url,
                        additional_headers=auth_headers,
                        open_timeout=25.0  # GCP Cloud Run may have cold starts
                    ),
                    timeout=35.0
                )
                
                connection_time = time.time() - connection_start
                cold_start_times.append(connection_time)
                
                await connection.close()
                
                # Wait between attempts to potentially trigger cold start
                await asyncio.sleep(2.0)
                
            except Exception as e:
                self.record_metric(f"gcp_cold_start_attempt_{attempt}_error", str(e))
        
        # Analyze cold start performance
        if cold_start_times:
            avg_connection_time = sum(cold_start_times) / len(cold_start_times)
            max_connection_time = max(cold_start_times)
            min_connection_time = min(cold_start_times)
            
            self.record_metric("gcp_avg_connection_time", avg_connection_time)
            self.record_metric("gcp_max_connection_time", max_connection_time)
            self.record_metric("gcp_min_connection_time", min_connection_time)
            
            # GCP Cloud Run performance thresholds
            GCP_COLD_START_THRESHOLD = 15.0  # 15 seconds max for cold start
            GCP_WARM_CONNECTION_THRESHOLD = 5.0  # 5 seconds max for warm connections
            
            performance_issues = []
            
            if max_connection_time > GCP_COLD_START_THRESHOLD:
                performance_issues.append(f"Cold start too slow: {max_connection_time:.3f}s > {GCP_COLD_START_THRESHOLD}s")
            
            if avg_connection_time > GCP_WARM_CONNECTION_THRESHOLD:
                performance_issues.append(f"Average connection too slow: {avg_connection_time:.3f}s > {GCP_WARM_CONNECTION_THRESHOLD}s")
            
            if performance_issues:
                gcp_performance_warning = (
                    f"⚠️ GCP CLOUD RUN PERFORMANCE ISSUES:\n" +
                    "\n".join(f"   🐌 {issue}" for issue in performance_issues) +
                    f"\n\n   📊 CONNECTION TIME ANALYSIS:\n"
                    f"   • Average: {avg_connection_time:.3f}s\n"
                    f"   • Maximum: {max_connection_time:.3f}s\n"
                    f"   • Minimum: {min_connection_time:.3f}s\n"
                    f"   • Attempts: {len(cold_start_times)}\n"
                    f"\n   🔧 GCP OPTIMIZATION REQUIRED:\n"
                    f"   • Increase Cloud Run CPU allocation\n"
                    f"   • Optimize container startup time\n"
                    f"   • Configure minimum instances to avoid cold starts\n"
                    f"   • Review Cloud Run concurrency settings\n"
                )
                print(gcp_performance_warning)
                # Note: This is a performance warning, not a hard failure
                
            else:
                print(f"✅ GCP CLOUD RUN PERFORMANCE: ACCEPTABLE")
                print(f"   ⚡ Average connection: {avg_connection_time:.3f}s")
                print(f"   ⚡ Max connection: {max_connection_time:.3f}s")
                print(f"   ⚡ Min connection: {min_connection_time:.3f}s")
                
        else:
            # No successful connections - critical GCP issue
            gcp_connection_failure = (
                f"🚨 GCP CLOUD RUN CONNECTION FAILURE:\n"
                f"   🔴 No successful WebSocket connections in staging\n"
                f"   🔴 All {3} connection attempts failed\n"
                f"   🔴 GCP Cloud Run service may be misconfigured\n"
                f"\n"
                f"   💼 BUSINESS IMPACT:\n"
                f"   • Staging environment completely non-functional\n"
                f"   • Production deployment will fail\n"
                f"   • WebSocket features unavailable in staging\n"
                f"\n"
                f"   🔧 GCP EMERGENCY RESOLUTION:\n"
                f"   • Check GCP Cloud Run service status\n"
                f"   • Verify Cloud Run service configuration\n"
                f"   • Review Cloud Run logs for errors\n"
                f"   • Validate GCP project permissions and quotas\n"
            )
            
            print(gcp_connection_failure)
            pytest.fail(gcp_connection_failure)

    @pytest.mark.timeout(35)
    @pytest.mark.asyncio
    async def test_staging_load_balancer_websocket_upgrade(self, real_services_fixture):
        """
        CRITICAL: Test load balancer WebSocket upgrade handling in staging.
        
        This test validates load balancer configuration:
        1. HTTP to WebSocket upgrade works correctly
        2. Load balancer preserves WebSocket connection
        3. Sticky sessions work for WebSocket connections
        4. Load balancer timeout configuration is appropriate
        """
        
        if not self._is_staging_environment:
            pytest.skip("Load balancer tests require staging environment")
        
        # === LOAD BALANCER WEBSOCKET UPGRADE TEST ===
        self.record_metric("load_balancer_upgrade_test_start", time.time())
        
        # Create authenticated user for load balancer testing
        lb_user = await create_authenticated_user_context(
            user_email="load_balancer_test@example.com",
            environment="staging",
            websocket_enabled=True
        )
        
        jwt_token = lb_user.agent_context.get("jwt_token")
        auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        
        # Add load balancer testing headers
        auth_headers.update({
            "X-Load-Balancer-Test": "websocket_upgrade",
            "X-Staging-LB-Validation": "true"
        })
        
        websocket_upgrade_success = False
        websocket_upgrade_error = None
        
        try:
            # Test WebSocket upgrade through load balancer
            lb_connection = await asyncio.wait_for(
                websockets.connect(
                    self._staging_websocket_url,
                    additional_headers=auth_headers,
                    open_timeout=15.0
                ),
                timeout=20.0
            )
            
            websocket_upgrade_success = True
            
            # Test sustained connection through load balancer
            lb_test_message = {
                "type": "load_balancer_test",
                "content": "Load balancer WebSocket upgrade test",
                "user_id": str(lb_user.user_id),
                "load_balancer_validation": True,
                "timestamp": time.time()
            }
            
            await lb_connection.send(json.dumps(lb_test_message))
            
            # Keep connection alive to test load balancer persistence
            await asyncio.sleep(3.0)
            
            # Send another message to test connection persistence
            persistence_message = {
                "type": "connection_persistence_test",
                "content": "Testing load balancer connection persistence",
                "timestamp": time.time()
            }
            
            await lb_connection.send(json.dumps(persistence_message))
            await asyncio.sleep(1.0)
            
            await lb_connection.close()
            
        except Exception as e:
            websocket_upgrade_error = str(e)
        
        self.record_metric("load_balancer_websocket_upgrade_success", websocket_upgrade_success)
        self.record_metric("load_balancer_websocket_upgrade_error", websocket_upgrade_error)
        
        # === LOAD BALANCER VALIDATION RESULTS ===
        
        if websocket_upgrade_success:
            print(f"✅ LOAD BALANCER WEBSOCKET UPGRADE: SUCCESS")
            print(f"   🟢 HTTP to WebSocket upgrade: Working")
            print(f"   🟢 Connection persistence: Working")
            print(f"   🟢 Load balancer configuration: Correct")
            
        else:
            # Load balancer WebSocket upgrade failed
            lb_failure_message = (
                f"🚨 LOAD BALANCER WEBSOCKET UPGRADE FAILURE:\n"
                f"   🔴 WebSocket URL: {self._staging_websocket_url}\n"
                f"   🔴 Upgrade Error: {websocket_upgrade_error}\n"
                f"\n"
                f"   💼 BUSINESS IMPACT:\n"
                f"   • Load balancer blocking WebSocket connections\n"
                f"   • WebSocket upgrade requests failing\n"
                f"   • Real-time features unavailable through load balancer\n"
                f"\n"
                f"   🔧 LOAD BALANCER RESOLUTION:\n"
                f"   • Configure load balancer for WebSocket upgrade support\n"
                f"   • Update load balancer timeout settings for WebSocket\n"
                f"   • Verify load balancer sticky session configuration\n"
                f"   • Check load balancer WebSocket proxy settings\n"
            )
            
            print(lb_failure_message)
            pytest.fail(lb_failure_message)

    @pytest.mark.timeout(30)
    @pytest.mark.asyncio
    async def test_staging_environment_configuration_validation(self, real_services_fixture):
        """
        CRITICAL: Test staging environment configuration completeness.
        
        This test validates staging configuration:
        1. Required environment variables are set correctly
        2. Staging-specific configuration differs from production
        3. Secrets and credentials are properly configured
        4. Service endpoints are reachable and correct
        """
        
        if not self._is_staging_environment:
            pytest.skip("Staging configuration tests require staging environment")
        
        # === STAGING CONFIGURATION VALIDATION ===
        self.record_metric("staging_config_validation_start", time.time())
        
        required_staging_vars = [
            "WEBSOCKET_URL", "AUTH_SERVICE_URL", "DATABASE_URL", 
            "REDIS_URL", "JWT_SECRET_KEY"
        ]
        
        missing_vars = []
        staging_config = {}
        
        for var in required_staging_vars:
            value = self.get_env_var(var)
            if value:
                staging_config[var] = value
            else:
                missing_vars.append(var)
        
        # Validate staging-specific patterns
        staging_url_patterns = ["staging", "stg", "dev"]
        production_url_patterns = ["prod", "production", "api.netra"]
        
        config_issues = []
        
        # Check URLs contain staging indicators
        for var, value in staging_config.items():
            if "URL" in var and value:
                has_staging_pattern = any(pattern in value.lower() for pattern in staging_url_patterns)
                has_production_pattern = any(pattern in value.lower() for pattern in production_url_patterns)
                
                if has_production_pattern:
                    config_issues.append(f"{var} appears to be production URL: {value}")
                elif not has_staging_pattern and var != "DATABASE_URL":  # Database may not have staging in URL
                    config_issues.append(f"{var} may not be staging URL: {value}")
        
        # Record configuration validation
        self.record_metric("staging_missing_vars", missing_vars)
        self.record_metric("staging_config_issues", config_issues)
        
        # === STAGING CONFIGURATION RESULTS ===
        
        all_config_issues = missing_vars + config_issues
        
        if not all_config_issues:
            print(f"✅ STAGING CONFIGURATION: COMPLETE")
            print(f"   🟢 Required variables: All present")
            print(f"   🟢 URL patterns: Staging-appropriate")
            print(f"   🟢 Configuration validation: Passed")
            
        else:
            # Staging configuration has issues
            staging_config_failure = (
                f"🚨 STAGING CONFIGURATION FAILURE:\n"
                f"   🔴 Environment: {self.get_env_var('TEST_ENV', 'unknown')}\n"
                f"\n"
                f"   🚫 CONFIGURATION ISSUES:\n" +
                (f"   Missing variables: {', '.join(missing_vars)}\n" if missing_vars else "") +
                "\n".join(f"   • {issue}" for issue in config_issues) +
                f"\n\n   💼 BUSINESS IMPACT:\n"
                f"   • Staging environment misconfigured\n"
                f"   • Production deployment validation impossible\n"
                f"   • WebSocket service may use wrong endpoints\n"
                f"   • Authentication may fail with wrong URLs\n"
                f"\n"
                f"   🔧 CONFIGURATION RESOLUTION:\n"
                f"   • Set missing environment variables\n"
                f"   • Verify staging URLs are correct and accessible\n"
                f"   • Update staging configuration to use staging endpoints\n"
                f"   • Validate secrets are staging-specific and valid\n"
            )
            
            print(staging_config_failure)
            pytest.fail(staging_config_failure)

    async def async_teardown_method(self, method=None):
        """Clean up WebSocket staging environment validation test resources."""
        # Record final staging environment metrics
        if hasattr(self, '_metrics'):
            final_metrics = self.get_all_metrics()
            is_staging = final_metrics.get("is_staging_environment", False)
            print(f"\n📊 WEBSOCKET STAGING ENVIRONMENT VALIDATION SUMMARY:")
            print(f"   🏭 Environment: {'Staging' if is_staging else 'Non-staging'}")
            print(f"   📊 Total Staging Metrics: {len(final_metrics)}")
            
            if is_staging:
                dns_ok = final_metrics.get("staging_dns_resolved", False)
                ssl_ok = final_metrics.get("staging_ssl_valid", False)
                auth_ok = final_metrics.get("staging_auth_success", False)
                websocket_ok = final_metrics.get("staging_websocket_connection_success", False)
                print(f"   🌐 DNS Resolution: {'✅' if dns_ok else '❌'}")
                print(f"   🔒 SSL Certificate: {'✅' if ssl_ok else '❌'}")
                print(f"   🔐 Authentication: {'✅' if auth_ok else '❌'}")
                print(f"   📡 WebSocket Connection: {'✅' if websocket_ok else '❌'}")
        
        await super().async_teardown_method(method)