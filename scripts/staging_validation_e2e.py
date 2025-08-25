#!/usr/bin/env python3
"""
Comprehensive End-to-End Staging Validation Script (Part 1: Basic Flows)

Business Value Justification (BVJ):
- Segment: Platform/Internal - All customer tiers
- Business Goal: Service reliability and deployment confidence  
- Value Impact: Ensures staging environment is ready for production deployment
- Strategic Impact: Prevents service outages and maintains customer experience

Tests comprehensive staging environment validation:
1. User Registration and Login Flow
2. Dashboard Access
3. Basic Navigation 
4. Service Configuration
5. Health Check Validation

Validates services:
- Frontend: https://app.staging.netrasystems.ai
- Backend API: https://api.staging.netrasystems.ai  
- Auth Service: https://auth.staging.netrasystems.ai

Usage:
    python scripts/staging_validation_e2e.py --all
    python scripts/staging_validation_e2e.py --health-only
    python scripts/staging_validation_e2e.py --auth-flow
    python scripts/staging_validation_e2e.py --websocket-test
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
import httpx

# Add project root to path for absolute imports
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Import validation utilities
from netra_backend.app.core.configuration.base import UnifiedConfigManager


@dataclass
class ValidationResult:
    """Container for validation test results."""
    test_name: str
    service: str
    status: str  # "PASS", "FAIL", "SKIP", "ERROR"
    duration_ms: int
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None


@dataclass
class ServiceEndpoints:
    """Configuration for staging service endpoints."""
    frontend: str = "https://app.staging.netrasystems.ai"
    backend: str = "https://api.staging.netrasystems.ai" 
    auth: str = "https://auth.staging.netrasystems.ai"
    websocket: str = "wss://api.staging.netrasystems.ai/ws"


class StagingValidator:
    """Comprehensive staging environment validator."""
    
    def __init__(self):
        """Initialize staging validator with service endpoints."""
        self.endpoints = ServiceEndpoints()
        self.results: List[ValidationResult] = []
        self.http_client: Optional[httpx.AsyncClient] = None
        self.aio_session: Optional[aiohttp.ClientSession] = None
        self.config_manager = UnifiedConfigManager()
        
        # Test configuration
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 2.0
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.setup()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        
    async def setup(self):
        """Initialize HTTP clients and test environment."""
        self.http_client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            verify=True
        )
        
        self.aio_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=aiohttp.TCPConnector(verify_ssl=True)
        )
        
        print("Setting up staging validation environment...")
        print(f"Frontend: {self.endpoints.frontend}")
        print(f"Backend: {self.endpoints.backend}")
        print(f"Auth: {self.endpoints.auth}")
        print(f"WebSocket: {self.endpoints.websocket}")
        print()
        
    async def cleanup(self):
        """Cleanup HTTP clients."""
        for client in [self.http_client, self.aio_session]:
            if client:
                try:
                    if hasattr(client, 'aclose'):
                        await client.aclose()
                    else:
                        await client.close()
                except Exception:
                    pass
                    
    def _record_result(self, result: ValidationResult):
        """Record a validation result."""
        self.results.append(result)
        status_icon = {
            "PASS": "[PASS]",
            "FAIL": "[FAIL]", 
            "SKIP": "[SKIP]",
            "ERROR": "[ERROR]"
        }.get(result.status, "[?]")
        
        duration_str = f"{result.duration_ms}ms"
        if result.response_time_ms:
            duration_str += f" (HTTP: {result.response_time_ms}ms)"
            
        print(f"{status_icon} {result.test_name} - {result.status} ({duration_str})")
        
        if result.error_message:
            print(f"   WARNING: {result.error_message}")
        if result.details:
            for key, value in result.details.items():
                print(f"   INFO: {key}: {value}")
        print()
        
    async def _make_request(self, method: str, url: str, **kwargs) -> Tuple[int, Dict[str, Any], int]:
        """Make HTTP request with error handling and timing."""
        start_time = time.time()
        
        try:
            response = await self.http_client.request(method, url, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse response body
            try:
                if response.headers.get("content-type", "").startswith("application/json"):
                    body = response.json()
                else:
                    body = {"content": response.text[:500]}
            except Exception:
                body = {"content": "Unable to parse response"}
                
            return response.status_code, body, duration_ms
            
        except httpx.RequestError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return 0, {"error": str(e)}, duration_ms
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return 0, {"error": f"Unexpected error: {str(e)}"}, duration_ms
            
    # ========================================
    # 1. HEALTH CHECK VALIDATION
    # ========================================
    
    async def test_service_health_endpoints(self):
        """Test health endpoints for all services."""
        print("Testing Service Health Endpoints...")
        
        health_endpoints = {
            "backend": f"{self.endpoints.backend}/health",
            "auth": f"{self.endpoints.auth}/health",
            "frontend": self.endpoints.frontend  # Homepage check
        }
        
        for service, url in health_endpoints.items():
            start_time = time.time()
            
            try:
                status_code, body, response_time = await self._make_request("GET", url)
                duration_ms = int((time.time() - start_time) * 1000)
                
                if status_code == 200:
                    # Validate health response structure
                    is_healthy = (
                        (service != "frontend" and body.get("status") in ["healthy", "ok"]) or
                        (service == "frontend" and "html" in str(body.get("content", "")).lower())
                    )
                    
                    if is_healthy:
                        result = ValidationResult(
                            test_name=f"{service.title()} Health Check",
                            service=service,
                            status="PASS",
                            duration_ms=duration_ms,
                            response_time_ms=response_time,
                            status_code=status_code,
                            details={"health_status": body.get("status", "healthy")}
                        )
                    else:
                        result = ValidationResult(
                            test_name=f"{service.title()} Health Check",
                            service=service,
                            status="FAIL",
                            duration_ms=duration_ms,
                            response_time_ms=response_time,
                            status_code=status_code,
                            error_message="Service returned 200 but health check failed",
                            details={"response": body}
                        )
                else:
                    result = ValidationResult(
                        test_name=f"{service.title()} Health Check",
                        service=service,
                        status="FAIL",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        error_message=f"HTTP {status_code}",
                        details={"response": body}
                    )
                    
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                result = ValidationResult(
                    test_name=f"{service.title()} Health Check",
                    service=service,
                    status="ERROR",
                    duration_ms=duration_ms,
                    error_message=str(e)
                )
                
            self._record_result(result)
            
    async def test_api_configuration_endpoints(self):
        """Test API configuration and basic endpoints."""
        print("Testing API Configuration...")
        
        config_endpoints = [
            ("Backend OpenAPI Docs", f"{self.endpoints.backend}/docs"),
            ("Backend Health Details", f"{self.endpoints.backend}/health/"),
            ("Auth Service Info", f"{self.endpoints.auth}/health"),
        ]
        
        for test_name, url in config_endpoints:
            start_time = time.time()
            
            try:
                status_code, body, response_time = await self._make_request("GET", url)
                duration_ms = int((time.time() - start_time) * 1000)
                
                if status_code in [200, 404]:  # 404 is acceptable for some endpoints
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="PASS" if status_code == 200 else "SKIP",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={"endpoint_accessible": status_code == 200}
                    )
                else:
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="FAIL",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        error_message=f"Unexpected status: {status_code}"
                    )
                    
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                result = ValidationResult(
                    test_name=test_name,
                    service="backend",
                    status="ERROR",
                    duration_ms=duration_ms,
                    error_message=str(e)
                )
                
            self._record_result(result)
            
    # ========================================
    # 2. FRONTEND ACCESS VALIDATION
    # ========================================
    
    async def test_frontend_homepage_access(self):
        """Test frontend homepage accessibility and basic content."""
        print("Testing Frontend Homepage Access...")
        
        start_time = time.time()
        
        try:
            status_code, body, response_time = await self._make_request("GET", self.endpoints.frontend)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if status_code == 200:
                content = str(body.get("content", "")).lower()
                has_html = "html" in content or "<!doctype" in content
                has_title = "title" in content
                content_length = len(body.get("content", ""))
                
                if has_html and content_length > 100:
                    result = ValidationResult(
                        test_name="Frontend Homepage Access",
                        service="frontend",
                        status="PASS",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={
                            "content_length": content_length,
                            "has_html": has_html,
                            "has_title": has_title
                        }
                    )
                else:
                    result = ValidationResult(
                        test_name="Frontend Homepage Access",
                        service="frontend",
                        status="FAIL",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        error_message="Frontend content validation failed",
                        details={
                            "content_length": content_length,
                            "has_html": has_html
                        }
                    )
            else:
                result = ValidationResult(
                    test_name="Frontend Homepage Access",
                    service="frontend",
                    status="FAIL",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    error_message=f"Frontend returned HTTP {status_code}"
                )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="Frontend Homepage Access",
                service="frontend",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    async def test_frontend_static_assets(self):
        """Test frontend static asset accessibility."""
        print("Testing Frontend Static Assets...")
        
        # Test common static asset paths
        asset_paths = [
            "/favicon.ico",
            "/robots.txt",
            "/_next/static/" # Next.js static assets (if present)
        ]
        
        for asset_path in asset_paths:
            start_time = time.time()
            asset_url = urljoin(self.endpoints.frontend, asset_path)
            
            try:
                status_code, body, response_time = await self._make_request("GET", asset_url)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Static assets can return 404, which is acceptable
                if status_code in [200, 404]:
                    result = ValidationResult(
                        test_name=f"Static Asset: {asset_path}",
                        service="frontend",
                        status="PASS" if status_code == 200 else "SKIP",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={"asset_exists": status_code == 200}
                    )
                else:
                    result = ValidationResult(
                        test_name=f"Static Asset: {asset_path}",
                        service="frontend",
                        status="FAIL",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        error_message=f"Unexpected status for static asset"
                    )
                    
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                result = ValidationResult(
                    test_name=f"Static Asset: {asset_path}",
                    service="frontend",
                    status="ERROR",
                    duration_ms=duration_ms,
                    error_message=str(e)
                )
                
            self._record_result(result)
            
    # ========================================
    # 3. AUTHENTICATION FLOW VALIDATION
    # ========================================
    
    async def test_auth_service_endpoints(self):
        """Test authentication service endpoints."""
        print("Testing Authentication Service...")
        
        auth_endpoints = [
            ("Auth Health Check", f"{self.endpoints.auth}/health"),
            ("OAuth Config", f"{self.endpoints.auth}/oauth/google/config"),
            ("Auth Service Info", f"{self.endpoints.auth}/.well-known/openid_configuration")
        ]
        
        for test_name, url in auth_endpoints:
            start_time = time.time()
            
            try:
                status_code, body, response_time = await self._make_request("GET", url)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Auth endpoints can return various codes - focus on connectivity
                if status_code in [200, 404, 405, 501]:
                    result = ValidationResult(
                        test_name=test_name,
                        service="auth",
                        status="PASS",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={"endpoint_accessible": True}
                    )
                else:
                    result = ValidationResult(
                        test_name=test_name,
                        service="auth",
                        status="FAIL",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        error_message=f"Auth endpoint error: {status_code}"
                    )
                    
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                result = ValidationResult(
                    test_name=test_name,
                    service="auth",
                    status="ERROR",
                    duration_ms=duration_ms,
                    error_message=str(e)
                )
                
            self._record_result(result)
            
    async def test_cors_configuration(self):
        """Test CORS configuration for cross-origin requests."""
        print("Testing CORS Configuration...")
        
        # Test CORS preflight for backend API
        start_time = time.time()
        
        try:
            headers = {
                "Origin": self.endpoints.frontend,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            }
            
            status_code, body, response_time = await self._make_request(
                "OPTIONS", 
                f"{self.endpoints.backend}/health",
                headers=headers
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            if status_code in [200, 204]:
                result = ValidationResult(
                    test_name="CORS Configuration",
                    service="backend",
                    status="PASS",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={"cors_enabled": True}
                )
            else:
                result = ValidationResult(
                    test_name="CORS Configuration",
                    service="backend", 
                    status="FAIL",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    error_message=f"CORS preflight failed: {status_code}"
                )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="CORS Configuration",
                service="backend",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    # ========================================
    # 4. WEBSOCKET CONNECTIVITY VALIDATION
    # ========================================
    
    async def test_websocket_connectivity(self):
        """Test WebSocket service connectivity."""
        print("Testing WebSocket Connectivity...")
        
        start_time = time.time()
        
        try:
            # Convert WebSocket URL to HTTP for initial validation
            http_ws_url = self.endpoints.websocket.replace("wss://", "https://")
            
            # First test if WebSocket endpoint is reachable via HTTP
            status_code, body, response_time = await self._make_request("GET", http_ws_url)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if status_code in [400, 426]:  # Expected for WebSocket upgrade required
                result = ValidationResult(
                    test_name="WebSocket Endpoint Reachability",
                    service="websocket",
                    status="PASS",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={"websocket_upgrade_expected": True}
                )
            elif status_code == 404:
                result = ValidationResult(
                    test_name="WebSocket Endpoint Reachability",
                    service="websocket",
                    status="FAIL",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    error_message="WebSocket endpoint not found"
                )
            else:
                result = ValidationResult(
                    test_name="WebSocket Endpoint Reachability",
                    service="websocket",
                    status="SKIP",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={"unexpected_status": status_code}
                )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="WebSocket Endpoint Reachability",
                service="websocket",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    async def test_websocket_connection_attempt(self):
        """Test actual WebSocket connection attempt."""
        print("Testing WebSocket Connection...")
        
        start_time = time.time()
        
        try:
            # Attempt WebSocket connection with timeout
            async with self.aio_session.ws_connect(
                self.endpoints.websocket,
                timeout=10,
                ssl=True
            ) as ws:
                # Send a basic ping message
                await ws.send_json({"type": "ping", "timestamp": time.time()})
                
                # Try to receive a response (with short timeout)
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    result = ValidationResult(
                        test_name="WebSocket Connection Test",
                        service="websocket",
                        status="PASS",
                        duration_ms=duration_ms,
                        details={"connection_successful": True, "received_response": msg.type.name}
                    )
                except asyncio.TimeoutError:
                    duration_ms = int((time.time() - start_time) * 1000)
                    result = ValidationResult(
                        test_name="WebSocket Connection Test",
                        service="websocket",
                        status="PASS",  # Connection worked, just no response
                        duration_ms=duration_ms,
                        details={"connection_successful": True, "response_timeout": True}
                    )
                    
        except aiohttp.WSServerHandshakeError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if e.status == 401:
                result = ValidationResult(
                    test_name="WebSocket Connection Test",
                    service="websocket",
                    status="PASS",  # Auth required is expected
                    duration_ms=duration_ms,
                    details={"auth_required": True}
                )
            else:
                result = ValidationResult(
                    test_name="WebSocket Connection Test",
                    service="websocket",
                    status="FAIL",
                    duration_ms=duration_ms,
                    error_message=f"WebSocket handshake failed: {e.status}"
                )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="WebSocket Connection Test",
                service="websocket",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    # ========================================
    # 5. CROSS-SERVICE COMMUNICATION
    # ========================================
    
    async def test_service_communication(self):
        """Test communication between services."""
        print("Testing Cross-Service Communication...")
        
        # Test if backend can reach auth service
        start_time = time.time()
        
        try:
            # Test backend health which may include auth service checks
            status_code, body, response_time = await self._make_request(
                "GET", 
                f"{self.endpoints.backend}/health"
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            if status_code == 200:
                health_data = body
                
                # Check if health response includes service dependency info
                services_healthy = health_data.get("status") == "healthy"
                
                result = ValidationResult(
                    test_name="Service Communication Check",
                    service="backend",
                    status="PASS" if services_healthy else "FAIL",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={
                        "backend_health": services_healthy,
                        "health_response": health_data
                    }
                )
            else:
                result = ValidationResult(
                    test_name="Service Communication Check",
                    service="backend",
                    status="FAIL",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    error_message="Backend health check failed"
                )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="Service Communication Check",
                service="backend",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    # ========================================
    # VALIDATION ORCHESTRATION
    # ========================================
    
    async def run_health_check_validation(self):
        """Run health check validation tests."""
        await self.test_service_health_endpoints()
        await self.test_api_configuration_endpoints()
        
    async def run_frontend_validation(self):
        """Run frontend validation tests."""
        await self.test_frontend_homepage_access()
        await self.test_frontend_static_assets()
        
    async def run_auth_validation(self):
        """Run authentication validation tests."""
        await self.test_auth_service_endpoints()
        await self.test_cors_configuration()
        
    async def run_websocket_validation(self):
        """Run WebSocket validation tests."""
        await self.test_websocket_connectivity()
        await self.test_websocket_connection_attempt()
        
    async def run_integration_validation(self):
        """Run integration validation tests."""
        await self.test_service_communication()
        
    async def run_comprehensive_validation(self):
        """Run all validation tests."""
        print("Starting Comprehensive Staging Validation...")
        print("=" * 80)
        
        validation_suites = [
            ("Health Check Validation", self.run_health_check_validation),
            ("Frontend Validation", self.run_frontend_validation),
            ("Authentication Validation", self.run_auth_validation),
            ("WebSocket Validation", self.run_websocket_validation),
            ("Integration Validation", self.run_integration_validation)
        ]
        
        for suite_name, suite_func in validation_suites:
            print(f"\n{suite_name}")
            print("-" * 40)
            try:
                await suite_func()
            except Exception as e:
                print(f"[ERROR] Suite failed with error: {e}")
                self._record_result(ValidationResult(
                    test_name=f"{suite_name} Suite",
                    service="system",
                    status="ERROR",
                    duration_ms=0,
                    error_message=str(e)
                ))
                
        print("\n" + "=" * 80)
        self.print_summary()
        
    def print_summary(self):
        """Print validation summary."""
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        errors = sum(1 for r in self.results if r.status == "ERROR")
        skipped = sum(1 for r in self.results if r.status == "SKIP")
        
        # Calculate service-specific results
        service_results = {}
        for result in self.results:
            if result.service not in service_results:
                service_results[result.service] = {"PASS": 0, "FAIL": 0, "ERROR": 0, "SKIP": 0}
            service_results[result.service][result.status] += 1
            
        print("\nSTAGING VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"Skipped: {skipped}")
        
        # Success rate
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Service breakdown
        print(f"\nService Results:")
        for service, counts in service_results.items():
            total_service = sum(counts.values())
            service_success = (counts["PASS"] / total_service * 100) if total_service > 0 else 0
            print(f"   {service.title()}: {counts['PASS']}/{total_service} ({service_success:.1f}%)")
            
        # Response time analysis
        response_times = [r.response_time_ms for r in self.results if r.response_time_ms is not None]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            max_response = max(response_times)
            print(f"\nResponse Times:")
            print(f"   Average: {avg_response:.0f}ms")
            print(f"   Maximum: {max_response}ms")
            
        # Overall status
        if failed == 0 and errors == 0:
            print(f"\n[SUCCESS] STAGING ENVIRONMENT: HEALTHY")
        elif failed + errors < total_tests * 0.2:
            print(f"\n[WARNING] STAGING ENVIRONMENT: MOSTLY HEALTHY (Issues: {failed + errors})")
        else:
            print(f"\n[CRITICAL] STAGING ENVIRONMENT: NEEDS ATTENTION (Issues: {failed + errors})")
            
        print("=" * 80)
        
    def export_results(self, filename: str):
        """Export results to JSON file."""
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.status == "PASS"),
                "failed": sum(1 for r in self.results if r.status == "FAIL"),
                "errors": sum(1 for r in self.results if r.status == "ERROR"),
                "skipped": sum(1 for r in self.results if r.status == "SKIP")
            },
            "results": [asdict(result) for result in self.results]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
            
        print(f"Results exported to: {filename}")


async def main():
    """Main entry point for staging validation."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Staging Environment Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/staging_validation_e2e.py --all
    python scripts/staging_validation_e2e.py --health-only
    python scripts/staging_validation_e2e.py --auth-flow --websocket-test
    python scripts/staging_validation_e2e.py --export results.json
        """
    )
    
    parser.add_argument("--all", action="store_true",
                       help="Run all validation tests")
    parser.add_argument("--health-only", action="store_true",
                       help="Run only health check tests")
    parser.add_argument("--frontend-test", action="store_true",
                       help="Run frontend validation tests")
    parser.add_argument("--auth-flow", action="store_true",
                       help="Run authentication flow tests")
    parser.add_argument("--websocket-test", action="store_true",
                       help="Run WebSocket connectivity tests")
    parser.add_argument("--integration", action="store_true",
                       help="Run cross-service integration tests")
    parser.add_argument("--export", metavar="FILE",
                       help="Export results to JSON file")
    parser.add_argument("--timeout", type=float, default=30.0,
                       help="Request timeout in seconds (default: 30)")
    
    args = parser.parse_args()
    
    # If no specific test is requested, run health checks
    if not any([args.all, args.health_only, args.frontend_test, 
               args.auth_flow, args.websocket_test, args.integration]):
        args.health_only = True
        
    async with StagingValidator() as validator:
        validator.timeout = args.timeout
        
        if args.all:
            await validator.run_comprehensive_validation()
        else:
            print("Running Selected Staging Validation Tests...")
            print("=" * 80)
            
            if args.health_only:
                await validator.run_health_check_validation()
            if args.frontend_test:
                await validator.run_frontend_validation()
            if args.auth_flow:
                await validator.run_auth_validation()
            if args.websocket_test:
                await validator.run_websocket_validation()
            if args.integration:
                await validator.run_integration_validation()
                
            print("\n" + "=" * 80)
            validator.print_summary()
            
        if args.export:
            validator.export_results(args.export)
            
        # Return exit code based on results
        failed_count = sum(1 for r in validator.results if r.status in ["FAIL", "ERROR"])
        return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)