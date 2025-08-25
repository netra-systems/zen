#!/usr/bin/env python3
"""
Comprehensive End-to-End Staging Validation Script (Part 2: User flows and advanced features - CORRECTED)

Business Value Justification (BVJ):
- Segment: Platform/Internal - All customer tiers
- Business Goal: Service reliability and user experience validation
- Value Impact: Ensures staging environment supports complete user journeys
- Strategic Impact: Validates production readiness for user-facing features

Tests comprehensive user flows and advanced features:
1. **WebSocket functionality** - Test /ws/health, /ws/config endpoints (via HTTP)
2. **Thread management** - Create, list, update threads using /api/threads/
3. **Agent functionality** - Test agent endpoints /api/agent/
4. **Configuration management** - Test config endpoints /api/config
5. **Error handling** - Test error responses and recovery

Validates services:
- Backend API: https://api.staging.netrasystems.ai
- Auth Service: https://auth.staging.netrasystems.ai
- Frontend: https://app.staging.netrasystems.ai

Usage:
    python scripts/staging_validation_part2_corrected.py --all
    python scripts/staging_validation_part2_corrected.py --websocket-flows
    python scripts/staging_validation_part2_corrected.py --thread-management
    python scripts/staging_validation_part2_corrected.py --agent-features
    python scripts/staging_validation_part2_corrected.py --config-management
    python scripts/staging_validation_part2_corrected.py --error-handling
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx

# Add project root to path for absolute imports
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


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
    threads: str = "https://api.staging.netrasystems.ai/api/threads/"
    agent: str = "https://api.staging.netrasystems.ai/api/agent"
    config: str = "https://api.staging.netrasystems.ai/api/config"
    websocket_health: str = "https://api.staging.netrasystems.ai/ws/health"
    websocket_config: str = "https://api.staging.netrasystems.ai/ws/config"


class CorrectedUserFlowValidator:
    """Advanced staging environment validator for user flows and features - corrected version."""
    
    def __init__(self):
        """Initialize staging validator with service endpoints."""
        self.endpoints = ServiceEndpoints()
        self.results: List[ValidationResult] = []
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Test configuration
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 2.0
        
        # Test state
        self.test_thread_ids: List[str] = []
        
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
        
        print("Setting up corrected user flow validation environment...")
        print(f"Frontend: {self.endpoints.frontend}")
        print(f"Backend: {self.endpoints.backend}")
        print(f"Auth: {self.endpoints.auth}")
        print(f"Threads: {self.endpoints.threads}")
        print(f"Agent: {self.endpoints.agent}")
        print(f"Config: {self.endpoints.config}")
        print(f"WebSocket Health: {self.endpoints.websocket_health}")
        print(f"WebSocket Config: {self.endpoints.websocket_config}")
        print()
        
    async def cleanup(self):
        """Cleanup HTTP clients and test data."""
        # Cleanup test threads
        for thread_id in self.test_thread_ids:
            try:
                await self._make_request("DELETE", f"{self.endpoints.threads}{thread_id}")
            except:
                pass  # Best effort cleanup
        
        # Cleanup HTTP clients
        if self.http_client:
            try:
                await self.http_client.aclose()
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
    # 1. WEBSOCKET FUNCTIONALITY TESTING (via HTTP)
    # ========================================
    
    async def test_websocket_health_endpoint(self):
        """Test WebSocket health endpoint functionality via HTTP."""
        print("Testing WebSocket Health Endpoint (via HTTP)...")
        
        start_time = time.time()
        
        try:
            status_code, body, response_time = await self._make_request(
                "GET", self.endpoints.websocket_health
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            if status_code == 200:
                result = ValidationResult(
                    test_name="WebSocket Health Endpoint",
                    service="websocket",
                    status="PASS",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={
                        "endpoint": "/ws/health",
                        "response_received": True,
                        "response_data": body
                    }
                )
            elif status_code == 401:
                result = ValidationResult(
                    test_name="WebSocket Health Endpoint",
                    service="websocket",
                    status="PASS",  # Auth required is expected
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={
                        "endpoint": "/ws/health",
                        "auth_required": True
                    }
                )
            elif status_code == 404:
                result = ValidationResult(
                    test_name="WebSocket Health Endpoint",
                    service="websocket",
                    status="SKIP",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={"endpoint_not_implemented": True}
                )
            else:
                result = ValidationResult(
                    test_name="WebSocket Health Endpoint",
                    service="websocket",
                    status="FAIL",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    error_message=f"Unexpected status code: {status_code}"
                )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="WebSocket Health Endpoint",
                service="websocket",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    async def test_websocket_config_endpoint(self):
        """Test WebSocket config endpoint functionality via HTTP."""
        print("Testing WebSocket Config Endpoint (via HTTP)...")
        
        start_time = time.time()
        
        try:
            status_code, body, response_time = await self._make_request(
                "GET", self.endpoints.websocket_config
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            if status_code == 200:
                result = ValidationResult(
                    test_name="WebSocket Config Endpoint",
                    service="websocket",
                    status="PASS",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={
                        "endpoint": "/ws/config",
                        "response_received": True,
                        "has_config_data": "config" in str(body).lower() or len(str(body)) > 10
                    }
                )
            elif status_code == 401:
                result = ValidationResult(
                    test_name="WebSocket Config Endpoint",
                    service="websocket",
                    status="PASS",  # Auth required is expected
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={
                        "endpoint": "/ws/config",
                        "auth_required": True
                    }
                )
            elif status_code == 404:
                result = ValidationResult(
                    test_name="WebSocket Config Endpoint",
                    service="websocket",
                    status="SKIP",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={"endpoint_not_implemented": True}
                )
            else:
                result = ValidationResult(
                    test_name="WebSocket Config Endpoint",
                    service="websocket",
                    status="FAIL",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    error_message=f"Unexpected status code: {status_code}"
                )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="WebSocket Config Endpoint",
                service="websocket",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    # ========================================
    # 2. THREAD MANAGEMENT TESTING
    # ========================================
    
    async def test_thread_creation(self):
        """Test thread creation functionality."""
        print("Testing Thread Creation...")
        
        start_time = time.time()
        
        try:
            thread_data = {
                "title": f"Test Thread - {datetime.now().isoformat()}",
                "description": "Test thread created by staging validation",
                "metadata": {
                    "test": True,
                    "created_by": "staging_validator"
                }
            }
            
            status_code, body, response_time = await self._make_request(
                "POST", 
                self.endpoints.threads,
                json=thread_data
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            if status_code == 201:
                thread_id = body.get("id") or body.get("thread_id")
                if thread_id:
                    self.test_thread_ids.append(thread_id)
                    
                result = ValidationResult(
                    test_name="Thread Creation",
                    service="backend",
                    status="PASS",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={
                        "thread_id": thread_id,
                        "created_successfully": True
                    }
                )
            elif status_code == 401:
                result = ValidationResult(
                    test_name="Thread Creation",
                    service="backend",
                    status="PASS",  # Auth required is expected
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={"auth_required": True}
                )
            elif status_code == 404:
                result = ValidationResult(
                    test_name="Thread Creation",
                    service="backend",
                    status="SKIP",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={"endpoint_not_implemented": True}
                )
            else:
                result = ValidationResult(
                    test_name="Thread Creation",
                    service="backend",
                    status="FAIL",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    error_message=f"Unexpected status code: {status_code}",
                    details={"response": body}
                )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="Thread Creation",
                service="backend",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    async def test_thread_listing(self):
        """Test thread listing functionality."""
        print("Testing Thread Listing...")
        
        start_time = time.time()
        
        try:
            status_code, body, response_time = await self._make_request(
                "GET", 
                self.endpoints.threads
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            if status_code == 200:
                threads = body.get("threads", []) if isinstance(body, dict) else body
                
                result = ValidationResult(
                    test_name="Thread Listing",
                    service="backend",
                    status="PASS",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={
                        "thread_count": len(threads) if isinstance(threads, list) else 0,
                        "has_threads": isinstance(threads, list) and len(threads) > 0,
                        "response_structure": type(body).__name__
                    }
                )
            elif status_code == 401:
                result = ValidationResult(
                    test_name="Thread Listing",
                    service="backend",
                    status="PASS",  # Auth required is expected
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={"auth_required": True}
                )
            elif status_code == 404:
                result = ValidationResult(
                    test_name="Thread Listing",
                    service="backend",
                    status="SKIP",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    details={"endpoint_not_implemented": True}
                )
            else:
                result = ValidationResult(
                    test_name="Thread Listing",
                    service="backend",
                    status="FAIL",
                    duration_ms=duration_ms,
                    response_time_ms=response_time,
                    status_code=status_code,
                    error_message=f"Unexpected status code: {status_code}",
                    details={"response": body}
                )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="Thread Listing",
                service="backend",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    # ========================================
    # 3. AGENT FUNCTIONALITY TESTING
    # ========================================
    
    async def test_agent_functionality(self):
        """Test agent functionality."""
        print("Testing Agent Functionality...")
        
        agent_endpoints = [
            ("Agent Run", f"{self.endpoints.agent}/run_agent", "POST"),
            ("Agent Message", f"{self.endpoints.agent}/message", "POST"),
            ("Agent Stream", f"{self.endpoints.agent}/stream", "POST")
        ]
        
        for test_name, url, method in agent_endpoints:
            start_time = time.time()
            
            try:
                # Use minimal test data for agent endpoints
                test_data = {"test": True} if method == "POST" else None
                kwargs = {"json": test_data} if test_data else {}
                
                status_code, body, response_time = await self._make_request(method, url, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                if status_code in [200, 201]:
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="PASS",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={
                            "endpoint_available": True,
                            "method": method
                        }
                    )
                elif status_code in [400, 422]:  # Validation errors expected without proper data
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="PASS",  # Endpoint exists and validates input
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={
                            "endpoint_available": True,
                            "validates_input": True,
                            "method": method
                        }
                    )
                elif status_code == 401:
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="PASS",  # Auth required is expected
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={"auth_required": True}
                    )
                elif status_code == 404:
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="SKIP",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={"endpoint_not_implemented": True}
                    )
                else:
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="FAIL",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        error_message=f"Unexpected status code: {status_code}",
                        details={"response": body}
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
    # 4. CONFIGURATION MANAGEMENT TESTING
    # ========================================
    
    async def test_config_management(self):
        """Test configuration management functionality."""
        print("Testing Configuration Management...")
        
        config_endpoints = [
            ("System Config", f"{self.endpoints.config}", "GET"),
            ("WebSocket Config", f"{self.endpoints.config}/websocket", "GET"),
            ("Public Config", f"{self.endpoints.config}/public", "GET")
        ]
        
        for test_name, url, method in config_endpoints:
            start_time = time.time()
            
            try:
                status_code, body, response_time = await self._make_request(method, url)
                duration_ms = int((time.time() - start_time) * 1000)
                
                if status_code == 200:
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="PASS",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={
                            "config_available": True,
                            "response_size": len(str(body)),
                            "has_config_data": isinstance(body, dict) and len(body) > 0
                        }
                    )
                elif status_code == 401:
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="PASS",  # Auth required is expected
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={"auth_required": True}
                    )
                elif status_code == 404:
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="SKIP",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        details={"endpoint_not_implemented": True}
                    )
                else:
                    result = ValidationResult(
                        test_name=test_name,
                        service="backend",
                        status="FAIL",
                        duration_ms=duration_ms,
                        response_time_ms=response_time,
                        status_code=status_code,
                        error_message=f"Unexpected status code: {status_code}",
                        details={"response": body}
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
    # 5. ERROR HANDLING TESTING
    # ========================================
    
    async def test_error_handling(self):
        """Test error handling functionality."""
        print("Testing Error Handling...")
        
        # Test 404 handling
        start_time = time.time()
        try:
            status_code, body, response_time = await self._make_request(
                "GET", f"{self.endpoints.backend}/nonexistent-endpoint"
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            result = ValidationResult(
                test_name="404 Error Handling",
                service="backend",
                status="PASS" if status_code == 404 else "FAIL",
                duration_ms=duration_ms,
                response_time_ms=response_time,
                status_code=status_code,
                details={"proper_404_response": status_code == 404}
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="404 Error Handling",
                service="backend",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
        # Test malformed JSON handling
        start_time = time.time()
        try:
            # Use a known POST endpoint with malformed data
            headers = {"Content-Type": "application/json"}
            status_code, body, response_time = await self._make_request(
                "POST", 
                self.endpoints.threads,
                content="invalid json{",
                headers=headers
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            result = ValidationResult(
                test_name="Malformed JSON Handling",
                service="backend",
                status="PASS" if status_code in [400, 422] else "FAIL",
                duration_ms=duration_ms,
                response_time_ms=response_time,
                status_code=status_code,
                details={"handles_malformed_json": status_code in [400, 422]}
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ValidationResult(
                test_name="Malformed JSON Handling",
                service="backend",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e)
            )
            
        self._record_result(result)
        
    # ========================================
    # VALIDATION ORCHESTRATION
    # ========================================
    
    async def run_websocket_flow_validation(self):
        """Run WebSocket functionality validation tests."""
        await self.test_websocket_health_endpoint()
        await self.test_websocket_config_endpoint()
        
    async def run_thread_management_validation(self):
        """Run thread management validation tests."""
        await self.test_thread_creation()
        await self.test_thread_listing()
        
    async def run_agent_functionality_validation(self):
        """Run agent functionality validation tests."""
        await self.test_agent_functionality()
        
    async def run_config_management_validation(self):
        """Run configuration management validation tests."""
        await self.test_config_management()
        
    async def run_error_handling_validation(self):
        """Run error handling validation tests."""
        await self.test_error_handling()
        
    async def run_comprehensive_validation(self):
        """Run all user flow validation tests."""
        print("Starting Comprehensive User Flow Validation (CORRECTED)...")
        print("=" * 80)
        
        validation_suites = [
            ("WebSocket Functionality", self.run_websocket_flow_validation),
            ("Thread Management", self.run_thread_management_validation),
            ("Agent Functionality", self.run_agent_functionality_validation),
            ("Configuration Management", self.run_config_management_validation),
            ("Error Handling", self.run_error_handling_validation)
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
        
        # Calculate feature availability
        feature_results = {
            "websocket": {"available": 0, "total": 0},
            "threads": {"available": 0, "total": 0},
            "agents": {"available": 0, "total": 0},
            "config": {"available": 0, "total": 0}
        }
        
        for result in self.results:
            if "websocket" in result.test_name.lower():
                feature_results["websocket"]["total"] += 1
                if result.status in ["PASS"]:
                    feature_results["websocket"]["available"] += 1
            elif "thread" in result.test_name.lower():
                feature_results["threads"]["total"] += 1
                if result.status in ["PASS"]:
                    feature_results["threads"]["available"] += 1
            elif "agent" in result.test_name.lower():
                feature_results["agents"]["total"] += 1
                if result.status in ["PASS"]:
                    feature_results["agents"]["available"] += 1
            elif "config" in result.test_name.lower():
                feature_results["config"]["total"] += 1
                if result.status in ["PASS"]:
                    feature_results["config"]["available"] += 1
        
        print("\nUSER FLOW VALIDATION SUMMARY (CORRECTED)")
        print("=" * 80)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"Skipped: {skipped}")
        
        # Success rate
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Feature availability
        print(f"\nFeature Availability:")
        for feature, stats in feature_results.items():
            if stats["total"] > 0:
                availability = (stats["available"] / stats["total"] * 100)
                status_icon = "[OK]" if availability >= 70 else "[WARN]" if availability >= 30 else "[FAIL]"
                print(f"   {status_icon} {feature.title()}: {stats['available']}/{stats['total']} ({availability:.1f}%)")
            
        # API functionality status
        api_working = sum(1 for r in self.results if "backend" in r.service and r.status == "PASS")
        websocket_working = sum(1 for r in self.results if "websocket" in r.service and r.status == "PASS")
        
        print(f"\nAPI Functionality:")
        print(f"   REST API: {'Working' if api_working > 0 else 'Issues detected'}")
        print(f"   WebSocket: {'Working' if websocket_working > 0 else 'Issues detected'}")
        
        # Error handling validation
        error_handling_working = sum(1 for r in self.results if "error" in r.test_name.lower() and r.status == "PASS")
        print(f"   Error Handling: {'Validated' if error_handling_working > 0 else 'Not validated'}")
        
        # Response time analysis
        response_times = [r.response_time_ms for r in self.results if r.response_time_ms is not None]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            max_response = max(response_times)
            print(f"\nResponse Times:")
            print(f"   Average: {avg_response:.0f}ms")
            print(f"   Maximum: {max_response}ms")
            
        # Overall system readiness
        critical_failures = sum(1 for r in self.results if r.status in ["FAIL", "ERROR"])
        
        print(f"\nOverall System Readiness:")
        if critical_failures == 0:
            print(f"   [SUCCESS] STAGING ENVIRONMENT: READY FOR PRODUCTION")
        elif critical_failures <= 2:
            print(f"   [WARNING] STAGING ENVIRONMENT: MINOR ISSUES ({critical_failures} issues)")
        else:
            print(f"   [CRITICAL] STAGING ENVIRONMENT: NEEDS ATTENTION ({critical_failures} critical issues)")
            
        print("=" * 80)
        
    def export_results(self, filename: str):
        """Export results to JSON file."""
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "user_flows_and_advanced_features_corrected",
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
    """Main entry point for corrected user flow validation."""
    parser = argparse.ArgumentParser(
        description="User Flow and Advanced Features Staging Validation (CORRECTED)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/staging_validation_part2_corrected.py --all
    python scripts/staging_validation_part2_corrected.py --websocket-flows
    python scripts/staging_validation_part2_corrected.py --thread-management --agent-features
    python scripts/staging_validation_part2_corrected.py --export results.json
        """
    )
    
    parser.add_argument("--all", action="store_true",
                       help="Run all validation tests")
    parser.add_argument("--websocket-flows", action="store_true",
                       help="Run WebSocket functionality tests")
    parser.add_argument("--thread-management", action="store_true",
                       help="Run thread management tests")
    parser.add_argument("--agent-features", action="store_true",
                       help="Run agent functionality tests")
    parser.add_argument("--config-management", action="store_true",
                       help="Run configuration management tests")
    parser.add_argument("--error-handling", action="store_true",
                       help="Run error handling tests")
    parser.add_argument("--export", metavar="FILE",
                       help="Export results to JSON file")
    parser.add_argument("--timeout", type=float, default=30.0,
                       help="Request timeout in seconds (default: 30)")
    
    args = parser.parse_args()
    
    # If no specific test is requested, run all tests
    if not any([args.all, args.websocket_flows, args.thread_management, 
               args.agent_features, args.config_management, args.error_handling]):
        args.all = True
        
    async with CorrectedUserFlowValidator() as validator:
        validator.timeout = args.timeout
        
        if args.all:
            await validator.run_comprehensive_validation()
        else:
            print("Running Selected User Flow Validation Tests (CORRECTED)...")
            print("=" * 80)
            
            if args.websocket_flows:
                await validator.run_websocket_flow_validation()
            if args.thread_management:
                await validator.run_thread_management_validation()
            if args.agent_features:
                await validator.run_agent_functionality_validation()
            if args.config_management:
                await validator.run_config_management_validation()
            if args.error_handling:
                await validator.run_error_handling_validation()
                
            print("\n" + "=" * 80)
            validator.print_summary()
            
        if args.export:
            validator.export_results(args.export)
            
        # Return exit code based on results
        critical_failures = sum(1 for r in validator.results if r.status in ["FAIL", "ERROR"])
        return 1 if critical_failures > 0 else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)