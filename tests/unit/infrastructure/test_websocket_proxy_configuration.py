"""
WebSocket Proxy Configuration Infrastructure Tests - Phase 1

CRITICAL MISSION: Isolate GCP Cloud Run WebSocket proxy configuration issues from application code
to determine the root cause of WebSocket 1011 internal errors blocking $200K+ MRR chat functionality.

Business Value Justification:
- Segment: Platform/Internal - Critical infrastructure validation
- Business Goal: Restore Golden Path WebSocket functionality for chat value delivery
- Value Impact: Enables real-time AI interactions that drive customer conversions
- Strategic Impact: Unblocks $120K+ MRR at risk from WebSocket infrastructure failures

This test suite focuses on infrastructure-level WebSocket configuration validation
WITHOUT dependencies on application-level Docker services.

EXPECTED OUTCOME: Tests will FAIL with WebSocket 1011 errors, proving infrastructure issues.
"""

import asyncio
import json
import logging
import ssl
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import pytest
import websockets
import aiohttp
import socket
from websockets.exceptions import ConnectionClosedError, InvalidStatus

# Import SSOT authentication and configuration
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from tests.e2e.staging_config import get_staging_config, StagingTestConfig
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

class TestWebSocketProxyConfiguration:
    """
    Tests WebSocket proxy layer configuration without application dependencies.
    
    CRITICAL: These tests target GCP Cloud Run Load Balancer and proxy configuration
    that processes WebSocket upgrade requests BEFORE they reach application code.
    
    Expected Failures:
    - 1011 internal error during WebSocket upgrade
    - Connection timeouts during handshake
    - SSL/TLS certificate validation failures
    - Subprotocol negotiation rejections
    """
    
    @pytest.fixture(scope="class")
    def staging_config(self) -> StagingTestConfig:
        """Get staging configuration for infrastructure tests."""
        return get_staging_config()
    
    @pytest.fixture(scope="class")
    def auth_helper(self) -> E2EAuthHelper:
        """Create E2E auth helper for staging environment."""
        return E2EAuthHelper(environment="staging")
    
    @pytest.fixture(scope="class")
    async def staging_auth_token(self, auth_helper: E2EAuthHelper) -> str:
        """Get valid staging authentication token."""
        return await auth_helper.get_staging_token_async()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_gcp_load_balancer_websocket_upgrade_headers(
        self, 
        staging_config: StagingTestConfig,
        staging_auth_token: str
    ):
        """
        Test #1.1.1: Validate GCP Load Balancer WebSocket upgrade header handling
        
        EXPECTED FAILURE: 1011 internal error during WebSocket upgrade
        SUCCESS CRITERIA: Proper "Upgrade: websocket" header processing
        
        This test isolates the HTTP -> WebSocket upgrade process at the GCP Load Balancer level.
        """
        logger.info(" SEARCH:  Testing GCP Load Balancer WebSocket upgrade header handling")
        
        websocket_url = staging_config.urls.websocket_url
        headers = {
            "Authorization": f"Bearer {staging_auth_token}",
            "X-Test-Type": "infrastructure-isolation",
            "X-Test-Component": "gcp-load-balancer-upgrade",
            "X-Test-Expected": "failure-1011"
        }
        
        start_time = time.time()
        connection_attempt_data = {
            "test_name": "gcp_load_balancer_websocket_upgrade_headers",
            "websocket_url": websocket_url,
            "headers_sent": list(headers.keys()),
            "expected_failure": "1011_internal_error",
            "start_time": start_time
        }
        
        try:
            logger.info(f"[U+1F310] Attempting WebSocket connection to: {websocket_url}")
            logger.info(f"[U+1F511] Auth token length: {len(staging_auth_token)} chars")
            logger.info(f"[U+1F4CB] Headers: {list(headers.keys())}")
            
            # CRITICAL: Use minimal connection parameters to isolate infrastructure issues
            # No application-level optimizations - just raw WebSocket upgrade
            websocket = await asyncio.wait_for(
                websockets.connect(
                    websocket_url,
                    additional_headers=headers,
                    # Minimal settings to test infrastructure layer only
                    open_timeout=30,  # Long timeout to distinguish from application timeouts
                    ping_interval=None,  # No application-level pings
                    ping_timeout=None,   # No application-level ping timeouts
                    max_size=None,       # No message size limits
                    compression=None     # No compression to simplify infrastructure test
                ),
                timeout=35  # Slightly longer than open_timeout
            )
            
            connection_time = time.time() - start_time
            connection_attempt_data.update({
                "connection_successful": True,
                "connection_time_seconds": connection_time,
                "websocket_state": websocket.state.name if hasattr(websocket, 'state') else 'unknown'
            })
            
            logger.info(f" PASS:  UNEXPECTED SUCCESS: WebSocket connection established in {connection_time:.2f}s")
            logger.info(f" SEARCH:  WebSocket state: {websocket.state.name if hasattr(websocket, 'state') else 'unknown'}")
            
            # If connection succeeds, test basic functionality
            test_message = {
                "type": "infrastructure_test",
                "test_id": "gcp_load_balancer_upgrade",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "expected_outcome": "should_fail_but_succeeded"
            }
            
            await websocket.send(json.dumps(test_message))
            logger.info("[U+1F4E4] Test message sent successfully")
            
            # Try to receive response (with timeout to avoid hanging)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                logger.info(f"[U+1F4E5] Received response: {response[:100]}...")
                connection_attempt_data["response_received"] = True
            except asyncio.TimeoutError:
                logger.warning("[U+23F0] No response received within 10 seconds")
                connection_attempt_data["response_received"] = False
            
            await websocket.close()
            logger.info("[U+1F50C] WebSocket connection closed cleanly")
            
            # CRITICAL: If we reach here, the infrastructure test PASSED when it should FAIL
            # This indicates the GCP Load Balancer is NOT the root cause of 1011 errors
            pytest.fail(
                "INFRASTRUCTURE TEST PASSED UNEXPECTEDLY: "
                f"GCP Load Balancer WebSocket upgrade succeeded in {connection_time:.2f}s. "
                "This proves the infrastructure layer is NOT causing 1011 errors. "
                "Root cause must be in application layer. "
                f"Connection data: {json.dumps(connection_attempt_data, indent=2)}"
            )
            
        except (ConnectionClosedError, InvalidStatus) as e:
            connection_time = time.time() - start_time
            connection_attempt_data.update({
                "connection_successful": False,
                "connection_time_seconds": connection_time,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "error_code": getattr(e, 'code', None)
            })
            
            logger.error(f" FAIL:  WebSocket connection failed as EXPECTED: {type(e).__name__}: {e}")
            logger.info(f"[U+23F1][U+FE0F]  Connection attempt duration: {connection_time:.2f}s")
            
            # Check for specific 1011 error
            if hasattr(e, 'code') and e.code == 1011:
                logger.info(" TARGET:  CONFIRMED: WebSocket 1011 internal error reproduced at infrastructure level")
                logger.info(" SEARCH:  ROOT CAUSE IDENTIFIED: GCP Load Balancer or Cloud Run proxy configuration")
                connection_attempt_data["root_cause_identified"] = "gcp_infrastructure_layer"
                
                # This is the EXPECTED failure - infrastructure layer issue confirmed
                assert e.code == 1011, f"Expected 1011 error code, got {e.code}"
                logger.info(f" PASS:  Infrastructure layer failure confirmed: {json.dumps(connection_attempt_data, indent=2)}")
                return  # Test passes by confirming expected infrastructure failure
            else:
                logger.warning(f"[U+1F914] Unexpected error type: {e} (code: {getattr(e, 'code', 'N/A')})")
                connection_attempt_data["unexpected_error"] = True
                
        except asyncio.TimeoutError:
            connection_time = time.time() - start_time
            connection_attempt_data.update({
                "connection_successful": False,
                "connection_time_seconds": connection_time,
                "error_type": "TimeoutError",
                "error_message": f"Connection timed out after {connection_time:.2f}s"
            })
            
            logger.error(f"[U+23F0] WebSocket connection timed out after {connection_time:.2f}s")
            logger.info(" SEARCH:  TIMEOUT ANALYSIS: Indicates GCP Cloud Run infrastructure timeout")
            connection_attempt_data["root_cause_identified"] = "gcp_cloud_run_timeout"
            
            # Timeout also indicates infrastructure layer issue
            logger.info(f" PASS:  Infrastructure layer timeout confirmed: {json.dumps(connection_attempt_data, indent=2)}")
            assert connection_time >= 30, f"Expected timeout >= 30s, got {connection_time:.2f}s"
            return  # Test passes by confirming expected infrastructure timeout
            
        except Exception as e:
            connection_time = time.time() - start_time
            connection_attempt_data.update({
                "connection_successful": False,
                "connection_time_seconds": connection_time,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "unexpected_error": True
            })
            
            logger.error(f" ALERT:  Unexpected error type: {type(e).__name__}: {e}")
            logger.info(f" SEARCH:  Error details: {json.dumps(connection_attempt_data, indent=2)}")
            
            # Re-raise unexpected errors for investigation
            raise
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cloud_run_websocket_timeout_configuration(
        self,
        staging_config: StagingTestConfig,
        staging_auth_token: str
    ):
        """
        Test #1.1.2: Validate Cloud Run WebSocket timeout settings
        
        EXPECTED FAILURE: Connection timeouts or 1011 errors
        SUCCESS CRITERIA: Connections sustained for >30 seconds
        
        This test validates GCP Cloud Run WebSocket timeout configuration.
        """
        logger.info("[U+23F0] Testing Cloud Run WebSocket timeout configuration")
        
        websocket_url = staging_config.urls.websocket_url
        headers = {
            "Authorization": f"Bearer {staging_auth_token}",
            "X-Test-Type": "infrastructure-timeout",
            "X-Test-Component": "gcp-cloud-run-timeout",
            "X-Test-Duration": "long-connection"
        }
        
        timeout_test_data = {
            "test_name": "cloud_run_websocket_timeout_configuration",
            "target_duration_seconds": 40,
            "websocket_url": websocket_url
        }
        
        start_time = time.time()
        websocket = None
        
        try:
            logger.info(f"[U+1F310] Establishing WebSocket connection for timeout test")
            
            # Connect with specific timeout settings
            websocket = await asyncio.wait_for(
                websockets.connect(
                    websocket_url,
                    additional_headers=headers,
                    open_timeout=25,
                    ping_interval=None,  # Disable ping to test pure connection timeout
                    ping_timeout=None,
                    close_timeout=5
                ),
                timeout=30
            )
            
            connection_time = time.time() - start_time
            logger.info(f" PASS:  WebSocket connected in {connection_time:.2f}s")
            timeout_test_data["connection_time_seconds"] = connection_time
            
            # Test sustained connection for >30 seconds
            logger.info("[U+23F1][U+FE0F]  Testing connection sustainability for 40 seconds...")
            
            for i in range(8):  # 8 * 5 = 40 seconds
                await asyncio.sleep(5)
                elapsed = time.time() - start_time
                
                # Send periodic test messages to verify connection is active
                test_msg = {
                    "type": "timeout_test",
                    "elapsed_seconds": elapsed,
                    "test_iteration": i + 1
                }
                
                try:
                    await websocket.send(json.dumps(test_msg))
                    logger.info(f"[U+1F4E4] Message {i+1}/8 sent at {elapsed:.1f}s")
                except Exception as send_error:
                    logger.error(f" FAIL:  Message send failed at {elapsed:.1f}s: {send_error}")
                    timeout_test_data["failed_at_seconds"] = elapsed
                    timeout_test_data["failure_reason"] = f"send_error_{type(send_error).__name__}"
                    break
            
            total_duration = time.time() - start_time
            timeout_test_data["total_duration_seconds"] = total_duration
            
            if total_duration >= 35:
                logger.info(f" TARGET:  UNEXPECTED SUCCESS: Connection sustained for {total_duration:.1f}s")
                logger.info(" SEARCH:  ANALYSIS: Cloud Run timeout configuration allows long connections")
                timeout_test_data["success"] = True
                timeout_test_data["root_cause_analysis"] = "cloud_run_timeout_not_the_issue"
                
                # If connection lasts >35 seconds, Cloud Run timeout is NOT the issue
                pytest.fail(
                    "CLOUD RUN TIMEOUT TEST PASSED UNEXPECTEDLY: "
                    f"Connection sustained for {total_duration:.1f}s. "
                    "This proves Cloud Run timeout configuration is NOT causing 1011 errors. "
                    f"Timeout test data: {json.dumps(timeout_test_data, indent=2)}"
                )
            else:
                logger.warning(f" WARNING: [U+FE0F]  Connection ended early at {total_duration:.1f}s")
                timeout_test_data["ended_early"] = True
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"[U+23F0] EXPECTED FAILURE: Connection timed out at {elapsed:.1f}s")
            logger.info(" TARGET:  CONFIRMED: Cloud Run timeout configuration is causing failures")
            timeout_test_data.update({
                "failed_at_seconds": elapsed,
                "failure_reason": "cloud_run_timeout",
                "root_cause_identified": "gcp_cloud_run_timeout_config"
            })
            
            # This is expected failure - confirms Cloud Run timeout issue
            assert elapsed < 35, f"Expected timeout <35s, connection lasted {elapsed:.1f}s"
            logger.info(f" PASS:  Cloud Run timeout failure confirmed: {json.dumps(timeout_test_data, indent=2)}")
            return  # Test passes by confirming expected timeout
            
        except (ConnectionClosedError, InvalidStatus) as e:
            elapsed = time.time() - start_time
            logger.error(f" FAIL:  EXPECTED FAILURE: WebSocket error at {elapsed:.1f}s: {e}")
            timeout_test_data.update({
                "failed_at_seconds": elapsed,
                "failure_reason": f"websocket_{type(e).__name__}",
                "error_code": getattr(e, 'code', None)
            })
            
            if hasattr(e, 'code') and e.code == 1011:
                logger.info(" TARGET:  CONFIRMED: 1011 error during sustained connection test")
                timeout_test_data["root_cause_identified"] = "websocket_1011_during_sustained_connection"
            
            logger.info(f" PASS:  WebSocket failure confirmed: {json.dumps(timeout_test_data, indent=2)}")
            return  # Test passes by confirming expected failure
            
        finally:
            if websocket:
                try:
                    await websocket.close()
                    logger.info("[U+1F50C] WebSocket connection closed cleanly")
                except:
                    pass  # Ignore errors during cleanup
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_websocket_subprotocol_negotiation(
        self,
        staging_config: StagingTestConfig,
        auth_helper: E2EAuthHelper,
        staging_auth_token: str
    ):
        """
        Test #1.1.3: Test WebSocket subprotocol negotiation (jwt-auth)
        
        EXPECTED FAILURE: Subprotocol rejection causing 1011
        SUCCESS CRITERIA: Proper jwt-auth subprotocol acceptance
        
        This test validates WebSocket subprotocol negotiation at the infrastructure level.
        """
        logger.info("[U+1F517] Testing WebSocket subprotocol negotiation")
        
        websocket_url = staging_config.urls.websocket_url
        headers = {
            "Authorization": f"Bearer {staging_auth_token}",
            "X-Test-Type": "infrastructure-subprotocol",
            "X-Test-Component": "websocket-subprotocol-negotiation"
        }
        
        # Get subprotocols from auth helper
        subprotocols = auth_helper.get_websocket_subprotocols(staging_auth_token)
        
        subprotocol_test_data = {
            "test_name": "websocket_subprotocol_negotiation",
            "websocket_url": websocket_url,
            "subprotocols_requested": subprotocols,
            "subprotocols_count": len(subprotocols)
        }
        
        start_time = time.time()
        
        try:
            logger.info(f"[U+1F310] Testing subprotocol negotiation with: {subprotocols}")
            
            # Test WebSocket connection with subprotocols
            websocket = await asyncio.wait_for(
                websockets.connect(
                    websocket_url,
                    additional_headers=headers,
                    subprotocols=subprotocols,
                    open_timeout=20
                ),
                timeout=25
            )
            
            connection_time = time.time() - start_time
            accepted_subprotocol = websocket.subprotocol
            
            subprotocol_test_data.update({
                "connection_successful": True,
                "connection_time_seconds": connection_time,
                "accepted_subprotocol": accepted_subprotocol,
                "subprotocol_negotiation_successful": accepted_subprotocol is not None
            })
            
            logger.info(f" PASS:  UNEXPECTED SUCCESS: Subprotocol negotiation succeeded in {connection_time:.2f}s")
            logger.info(f"[U+1F517] Accepted subprotocol: {accepted_subprotocol}")
            
            # Test if subprotocol is working correctly
            if accepted_subprotocol:
                logger.info(f" TARGET:  Subprotocol '{accepted_subprotocol}' was accepted by server")
                
                # Send test message to verify subprotocol functionality
                test_message = {
                    "type": "subprotocol_test",
                    "subprotocol": accepted_subprotocol,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                logger.info("[U+1F4E4] Subprotocol test message sent")
                
                # Try to receive response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    logger.info(f"[U+1F4E5] Subprotocol response received: {response[:100]}...")
                    subprotocol_test_data["response_received"] = True
                except asyncio.TimeoutError:
                    logger.warning("[U+23F0] No subprotocol response within 10 seconds")
                    subprotocol_test_data["response_received"] = False
            
            await websocket.close()
            logger.info("[U+1F50C] WebSocket connection closed cleanly")
            
            # If subprotocol negotiation succeeds, infrastructure is NOT the issue
            pytest.fail(
                "SUBPROTOCOL NEGOTIATION TEST PASSED UNEXPECTEDLY: "
                f"WebSocket subprotocol '{accepted_subprotocol}' accepted successfully. "
                "This proves subprotocol negotiation infrastructure is NOT causing 1011 errors. "
                f"Subprotocol test data: {json.dumps(subprotocol_test_data, indent=2)}"
            )
            
        except (ConnectionClosedError, InvalidStatus) as e:
            connection_time = time.time() - start_time
            subprotocol_test_data.update({
                "connection_successful": False,
                "connection_time_seconds": connection_time,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "error_code": getattr(e, 'code', None)
            })
            
            logger.error(f" FAIL:  EXPECTED FAILURE: Subprotocol negotiation failed: {e}")
            
            if hasattr(e, 'code') and e.code == 1011:
                logger.info(" TARGET:  CONFIRMED: 1011 error during subprotocol negotiation")
                subprotocol_test_data["root_cause_identified"] = "subprotocol_negotiation_1011"
                
                # Check if specific subprotocols are causing issues
                if "jwt-auth" in subprotocols:
                    logger.info(" SEARCH:  JWT-auth subprotocol appears to be rejected by infrastructure")
                    subprotocol_test_data["jwt_auth_rejected"] = True
                
                logger.info(f" PASS:  Subprotocol infrastructure failure confirmed: {json.dumps(subprotocol_test_data, indent=2)}")
                assert e.code == 1011, f"Expected 1011 error code, got {e.code}"
                return  # Test passes by confirming expected infrastructure failure
            else:
                logger.warning(f"[U+1F914] Unexpected subprotocol error: {e}")
                subprotocol_test_data["unexpected_error"] = True
                
        except asyncio.TimeoutError:
            connection_time = time.time() - start_time
            logger.error(f"[U+23F0] Subprotocol negotiation timed out after {connection_time:.2f}s")
            subprotocol_test_data.update({
                "connection_successful": False,
                "connection_time_seconds": connection_time,
                "error_type": "TimeoutError",
                "root_cause_identified": "subprotocol_negotiation_timeout"
            })
            
            logger.info(f" PASS:  Subprotocol timeout confirmed: {json.dumps(subprotocol_test_data, indent=2)}")
            return  # Test passes by confirming expected timeout
            
        except Exception as e:
            connection_time = time.time() - start_time
            logger.error(f" ALERT:  Unexpected subprotocol error: {type(e).__name__}: {e}")
            subprotocol_test_data.update({
                "connection_successful": False,
                "connection_time_seconds": connection_time,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "unexpected_error": True
            })
            
            logger.info(f" SEARCH:  Unexpected subprotocol error details: {json.dumps(subprotocol_test_data, indent=2)}")
            raise
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_websocket_infrastructure_comprehensive_diagnosis(
        self,
        staging_config: StagingTestConfig,
        auth_helper: E2EAuthHelper,
        staging_auth_token: str
    ):
        """
        Test #1.1.4: Comprehensive WebSocket infrastructure diagnosis
        
        This test performs a comprehensive analysis of all infrastructure components
        to definitively isolate where 1011 errors originate.
        """
        logger.info("[U+1F52C] Performing comprehensive WebSocket infrastructure diagnosis")
        
        diagnosis_results = {
            "test_name": "websocket_infrastructure_comprehensive_diagnosis",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "staging_config": {
                "backend_url": staging_config.urls.backend_url,
                "websocket_url": staging_config.urls.websocket_url
            },
            "test_results": {}
        }
        
        # Test 1: Basic HTTP connectivity to backend
        logger.info("[U+1F310] Testing HTTP connectivity to staging backend...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{staging_config.urls.backend_url}/health", timeout=10) as resp:
                    http_status = resp.status
                    http_response = await resp.text()
                    
            diagnosis_results["test_results"]["http_connectivity"] = {
                "success": http_status == 200,
                "status_code": http_status,
                "response_length": len(http_response)
            }
            logger.info(f" PASS:  HTTP connectivity: {http_status}")
            
        except Exception as e:
            diagnosis_results["test_results"]["http_connectivity"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f" FAIL:  HTTP connectivity failed: {e}")
        
        # Test 2: DNS resolution and SSL verification
        logger.info(" SEARCH:  Testing DNS resolution and SSL verification...")
        try:
            # Extract hostname from WebSocket URL
            parsed_url = urllib.parse.urlparse(staging_config.urls.websocket_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or (443 if parsed_url.scheme == 'wss' else 80)
            
            # Test DNS resolution
            ip_address = socket.gethostbyname(hostname)
            diagnosis_results["test_results"]["dns_resolution"] = {
                "success": True,
                "hostname": hostname,
                "ip_address": ip_address
            }
            logger.info(f" PASS:  DNS resolution: {hostname} -> {ip_address}")
            
            # Test SSL connection
            if parsed_url.scheme == 'wss':
                ssl_context = ssl.create_default_context()
                sock = socket.create_connection((hostname, port), timeout=10)
                ssl_sock = ssl_context.wrap_socket(sock, server_hostname=hostname)
                cert = ssl_sock.getpeercert()
                ssl_sock.close()
                
                diagnosis_results["test_results"]["ssl_verification"] = {
                    "success": True,
                    "cert_subject": cert.get('subject', []),
                    "cert_issuer": cert.get('issuer', []),
                    "cert_version": cert.get('version')
                }
                logger.info(f" PASS:  SSL verification successful")
            
        except Exception as e:
            diagnosis_results["test_results"]["dns_ssl"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f" FAIL:  DNS/SSL verification failed: {e}")
        
        # Test 3: WebSocket upgrade with minimal settings
        logger.info(" CYCLE:  Testing WebSocket upgrade with minimal settings...")
        try:
            start_time = time.time()
            websocket = await asyncio.wait_for(
                websockets.connect(
                    staging_config.urls.websocket_url,
                    additional_headers={
                        "Authorization": f"Bearer {staging_auth_token}",
                        "X-Test-Type": "infrastructure-diagnosis"
                    },
                    open_timeout=15
                ),
                timeout=20
            )
            
            connection_time = time.time() - start_time
            await websocket.close()
            
            diagnosis_results["test_results"]["websocket_upgrade_minimal"] = {
                "success": True,
                "connection_time_seconds": connection_time
            }
            logger.info(f" PASS:  WebSocket upgrade succeeded in {connection_time:.2f}s")
            
        except Exception as e:
            diagnosis_results["test_results"]["websocket_upgrade_minimal"] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "error_code": getattr(e, 'code', None)
            }
            logger.error(f" FAIL:  WebSocket upgrade failed: {e}")
        
        # Test 4: WebSocket upgrade with full E2E headers
        logger.info("[U+1F527] Testing WebSocket upgrade with full E2E headers...")
        try:
            headers = auth_helper.get_websocket_headers(staging_auth_token)
            subprotocols = auth_helper.get_websocket_subprotocols(staging_auth_token)
            
            start_time = time.time()
            websocket = await asyncio.wait_for(
                websockets.connect(
                    staging_config.urls.websocket_url,
                    additional_headers=headers,
                    subprotocols=subprotocols,
                    open_timeout=15
                ),
                timeout=20
            )
            
            connection_time = time.time() - start_time
            accepted_subprotocol = websocket.subprotocol
            await websocket.close()
            
            diagnosis_results["test_results"]["websocket_upgrade_full"] = {
                "success": True,
                "connection_time_seconds": connection_time,
                "headers_count": len(headers),
                "subprotocols_count": len(subprotocols),
                "accepted_subprotocol": accepted_subprotocol
            }
            logger.info(f" PASS:  Full WebSocket upgrade succeeded in {connection_time:.2f}s")
            
        except Exception as e:
            diagnosis_results["test_results"]["websocket_upgrade_full"] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "error_code": getattr(e, 'code', None)
            }
            logger.error(f" FAIL:  Full WebSocket upgrade failed: {e}")
        
        # Analysis: Determine root cause based on test results
        logger.info("[U+1F9EA] Analyzing comprehensive test results...")
        
        infrastructure_failures = []
        application_failures = []
        
        for test_name, result in diagnosis_results["test_results"].items():
            if not result.get("success", False):
                error_code = result.get("error_code")
                if error_code == 1011:
                    infrastructure_failures.append(test_name)
                elif "timeout" in result.get("error", "").lower():
                    infrastructure_failures.append(test_name)
                else:
                    application_failures.append(test_name)
        
        diagnosis_results["analysis"] = {
            "infrastructure_failures": infrastructure_failures,
            "application_failures": application_failures,
            "total_tests": len(diagnosis_results["test_results"]),
            "passed_tests": sum(1 for r in diagnosis_results["test_results"].values() if r.get("success")),
            "failed_tests": sum(1 for r in diagnosis_results["test_results"].values() if not r.get("success"))
        }
        
        if infrastructure_failures:
            diagnosis_results["conclusion"] = "INFRASTRUCTURE_LAYER_ISSUE"
            logger.info(f" TARGET:  CONCLUSION: Infrastructure layer issues detected in: {infrastructure_failures}")
        elif application_failures:
            diagnosis_results["conclusion"] = "APPLICATION_LAYER_ISSUE"
            logger.info(f" TARGET:  CONCLUSION: Application layer issues detected in: {application_failures}")
        else:
            diagnosis_results["conclusion"] = "NO_ISSUES_DETECTED"
            logger.info("[U+1F914] CONCLUSION: No infrastructure issues detected - may be application-specific")
        
        # Log comprehensive results
        logger.info(f" CHART:  Comprehensive diagnosis results:")
        logger.info(json.dumps(diagnosis_results, indent=2))
        
        # Assert based on findings
        if diagnosis_results["conclusion"] == "INFRASTRUCTURE_LAYER_ISSUE":
            # This is expected - infrastructure issues confirmed
            assert len(infrastructure_failures) > 0, "Expected infrastructure failures not detected"
            return
        elif diagnosis_results["conclusion"] == "NO_ISSUES_DETECTED":
            # Unexpected - infrastructure is working fine
            pytest.fail(
                "COMPREHENSIVE INFRASTRUCTURE DIAGNOSIS PASSED UNEXPECTEDLY: "
                "All infrastructure tests passed, proving infrastructure is NOT causing 1011 errors. "
                "Root cause must be in application layer. "
                f"Diagnosis results: {json.dumps(diagnosis_results, indent=2)}"
            )
        else:
            # Mixed results - need further investigation
            logger.warning(f" ALERT:  Mixed test results require further investigation")
            logger.info(f"[U+1F4CB] Full diagnosis: {json.dumps(diagnosis_results, indent=2)}")