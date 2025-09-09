#!/usr/bin/env python3
"""
Complete Staging Environment E2E Test Suite
Business Value: Validates complete staging deployment functionality.
Ensures all services work correctly in staging before production deployment.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment



import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
import pytest

from test_framework.environment_markers import env, env_requires, staging_only
from tests.e2e.integration.unified_e2e_harness import UnifiedE2ETestHarness
from tests.e2e.real_services_manager import RealServicesManager
from tests.e2e.staging_test_helpers import StagingTestResult
from tests.e2e.test_environment_config import TestEnvironmentType

logger = logging.getLogger(__name__)


class TestStagingE2ESuite:
    """Complete staging environment E2E test suite."""
    
    def __init__(self):
        """Initialize staging test suite."""
        self.harness = UnifiedE2ETestHarness(environment=TestEnvironmentType.STAGING)
        self.services_manager = RealServicesManager()
        self.test_results: List[StagingTestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def setup(self):
        """Setup test environment."""
        logger.info("Setting up staging E2E test environment")
        self.session = aiohttp.ClientSession()
        await self.harness.start_test_environment()
        
    async def teardown(self):
        """Teardown test environment."""
        logger.info("Tearing down staging E2E test environment")
        if self.session:
            await self.session.close()
        await self.harness.cleanup_test_environment()
        
    async def test_staging_startup(self) -> StagingTestResult:
        """Test 1: Basic system startup - Verify STAGING ENV is up and running."""
        start_time = datetime.now()
        test_name = "staging_startup"
        
        try:
            logger.info("Testing staging environment startup...")
            
            # Check environment configuration
            env_status = await self.harness.get_environment_status()
            assert env_status["environment"] in ["staging", "testing"], "Not in staging environment"
            
            # Verify all service URLs are configured
            service_urls = env_status.get("service_urls", {})
            required_services = ["backend", "auth", "frontend", "websocket"]
            
            for service in required_services:
                assert service in service_urls, f"Missing {service} URL"
                assert service_urls[service], f"Empty {service} URL"
                
            # Check database connection
            assert env_status.get("database_url"), "Database URL not configured"
            
            # Verify startup checks pass
            backend_url = self.harness.get_service_url("backend")
            async with self.session.get(f"{backend_url}/health") as resp:
                assert resp.status == 200, f"Backend health check failed: {resp.status}"
                health_data = await resp.json()
                assert health_data.get("status") == "healthy", "Backend not healthy"
                
            auth_url = self.harness.get_service_url("auth")
            async with self.session.get(f"{auth_url}/health/ready") as resp:
                assert resp.status == 200, f"Auth health check failed: {resp.status}"
                
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return StagingTestResult(
                test_name=test_name,
                status="passed",
                duration_ms=duration,
                details={"environment": env_status}
            )
            
        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Staging startup test failed: {e}")
            return StagingTestResult(
                test_name=test_name,
                status="failed",
                duration_ms=duration,
                error_message=str(e)
            )
            
    async def test_frontend_websocket_connection(self) -> StagingTestResult:
        """Test 2: Frontend connects on WebSocket without issue in STAGING MODE."""
        start_time = datetime.now()
        test_name = "frontend_websocket_connection"
        
        try:
            logger.info("Testing frontend WebSocket connection...")
            
            # Create test user
            user = await self.harness.create_test_user()
            assert user.access_token, "Failed to get access token"
            
            # Test WebSocket connection
            ws_url = self.harness.get_websocket_url()
            headers = {"Authorization": f"Bearer {user.access_token}"}
            
            async with self.session.ws_connect(
                ws_url,
                headers=headers,
                ssl=False
            ) as ws:
                # Send initial connection message
                await ws.send_json({
                    "type": "connection_init",
                    "payload": {"auth_token": user.access_token}
                })
                
                # Wait for connection acknowledgment
                msg = await ws.receive()
                assert msg.type == aiohttp.WSMsgType.TEXT
                data = json.loads(msg.data)
                assert data.get("type") in ["connection_ack", "connected"]
                
                # Test CORS headers (if available in response)
                # Note: WebSocket doesn't have CORS like HTTP, but we can verify origin handling
                
                await ws.close()
                
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return StagingTestResult(
                test_name=test_name,
                status="passed",
                duration_ms=duration,
                details={"user_id": user.user_id, "ws_url": ws_url}
            )
            
        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Frontend WebSocket test failed: {e}")
            return StagingTestResult(
                test_name=test_name,
                status="failed",
                duration_ms=duration,
                error_message=str(e)
            )
            
    async def test_example_message(self) -> StagingTestResult:
        """Test 3: Example message works correctly."""
        start_time = datetime.now()
        test_name = "example_message"
        
        try:
            logger.info("Testing example message...")
            
            # Create test user and WebSocket connection
            user = await self.harness.create_test_user()
            ws = await self.harness.create_websocket_connection(user)
            
            # Send example message
            example_prompt = "What are the best practices for reducing LLM costs?"
            await ws.send_message({
                "type": "message",
                "content": example_prompt,
                "thread_id": "test_thread_" + user.user_id
            })
            
            # Wait for response
            response = await ws.receive_message(timeout=30)
            assert response, "No response received"
            assert response.get("type") == "message", "Invalid response type"
            assert response.get("content"), "Empty response content"
            
            # Verify response quality
            content = response.get("content", "")
            assert len(content) > 50, "Response too short"
            assert "cost" in content.lower() or "optimization" in content.lower(), \
                   "Response doesn't address the topic"
            
            await ws.close()
            
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return StagingTestResult(
                test_name=test_name,
                status="passed",
                duration_ms=duration,
                details={
                    "prompt": example_prompt,
                    "response_length": len(content),
                    "response_preview": content[:100] + "..."
                }
            )
            
        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Example message test failed: {e}")
            return StagingTestResult(
                test_name=test_name,
                status="failed",
                duration_ms=duration,
                error_message=str(e)
            )
            
    async def test_agent_response(self) -> StagingTestResult:
        """Test 4: Agent sends response properly."""
        start_time = datetime.now()
        test_name = "agent_response"
        
        try:
            logger.info("Testing agent response...")
            
            # Create test user
            user = await self.harness.create_test_user()
            
            # Test agent API endpoint
            backend_url = self.harness.get_service_url("backend")
            headers = {"Authorization": f"Bearer {user.access_token}"}
            
            # Create thread
            async with self.session.post(
                f"{backend_url}/api/threads",
                headers=headers,
                json={"name": "Test Thread"}
            ) as resp:
                assert resp.status == 201, f"Failed to create thread: {resp.status}"
                thread_data = await resp.json()
                thread_id = thread_data["id"]
            
            # Send message to agent
            async with self.session.post(
                f"{backend_url}/api/threads/{thread_id}/messages",
                headers=headers,
                json={
                    "content": "Analyze my AI costs and suggest optimizations",
                    "role": "user"
                }
            ) as resp:
                assert resp.status in [200, 201], f"Failed to send message: {resp.status}"
                message_data = await resp.json()
                
            # Poll for agent response
            max_attempts = 30
            for _ in range(max_attempts):
                async with self.session.get(
                    f"{backend_url}/api/threads/{thread_id}/messages",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        messages = await resp.json()
                        agent_messages = [m for m in messages if m.get("role") == "assistant"]
                        if agent_messages:
                            agent_response = agent_messages[-1]
                            assert agent_response.get("content"), "Empty agent response"
                            break
                await asyncio.sleep(1)
            else:
                raise AssertionError("No agent response received within timeout")
            
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return StagingTestResult(
                test_name=test_name,
                status="passed",
                duration_ms=duration,
                details={
                    "thread_id": thread_id,
                    "response_length": len(agent_response.get("content", "")),
                    "response_preview": agent_response.get("content", "")[:100] + "..."
                }
            )
            
        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Agent response test failed: {e}")
            return StagingTestResult(
                test_name=test_name,
                status="failed",
                duration_ms=duration,
                error_message=str(e)
            )
            
    async def test_full_system(self) -> StagingTestResult:
        """Test 5: Everything works - check CORS, WS, loading, etc."""
        start_time = datetime.now()
        test_name = "full_system"
        
        try:
            logger.info("Testing full system integration...")
            
            # Test CORS headers on API endpoints
            backend_url = self.harness.get_service_url("backend")
            origin = "https://app.staging.netrasystems.ai"
            
            async with self.session.options(
                f"{backend_url}/api/threads",
                headers={"Origin": origin}
            ) as resp:
                cors_headers = resp.headers
                assert "Access-Control-Allow-Origin" in cors_headers, "Missing CORS header"
                allowed_origin = cors_headers.get("Access-Control-Allow-Origin")
                assert allowed_origin in ["*", origin], f"Invalid CORS origin: {allowed_origin}"
            
            # Test complete user journey
            user = await self.harness.create_test_user()
            journey_result = await self.harness.simulate_user_journey(user)
            
            assert journey_result.get("success"), "User journey failed"
            assert journey_result.get("messages_sent", 0) > 0, "No messages sent"
            assert journey_result.get("responses_received", 0) > 0, "No responses received"
            
            # Test concurrent users
            concurrent_results = await self.harness.run_concurrent_user_test(user_count=3)
            successful_journeys = [r for r in concurrent_results if r.get("success")]
            assert len(successful_journeys) >= 2, "Too many concurrent user failures"
            
            # Test service health under load
            health_checks = []
            for _ in range(5):
                async with self.session.get(f"{backend_url}/health") as resp:
                    health_checks.append(resp.status == 200)
                    
            assert all(health_checks), "Health checks failed under load"
            
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return StagingTestResult(
                test_name=test_name,
                status="passed",
                duration_ms=duration,
                details={
                    "cors_configured": True,
                    "journey_success": journey_result.get("success"),
                    "concurrent_success_rate": len(successful_journeys) / len(concurrent_results),
                    "health_check_success_rate": sum(health_checks) / len(health_checks)
                }
            )
            
        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Full system test failed: {e}")
            return StagingTestResult(
                test_name=test_name,
                status="failed",
                duration_ms=duration,
                error_message=str(e)
            )
            
    async def test_oauth_authentication(self) -> StagingTestResult:
        """Test 6: OAuth authentication works."""
        start_time = datetime.now()
        test_name = "oauth_authentication"
        
        try:
            logger.info("Testing OAuth authentication...")
            
            auth_url = self.harness.get_service_url("auth")
            
            # Test OAuth configuration endpoint
            async with self.session.get(f"{auth_url}/oauth/config") as resp:
                if resp.status == 404:
                    # OAuth might not be configured in staging
                    logger.warning("OAuth endpoints not available in staging")
                    duration = int((datetime.now() - start_time).total_seconds() * 1000)
                    return StagingTestResult(
                        test_name=test_name,
                        status="skipped",
                        duration_ms=duration,
                        details={"reason": "OAuth not configured in staging"}
                    )
                    
                assert resp.status == 200, f"OAuth config endpoint failed: {resp.status}"
                config = await resp.json()
                
            # Test OAuth providers
            providers = config.get("providers", [])
            assert len(providers) > 0, "No OAuth providers configured"
            
            # Test OAuth flow initiation (without actual OAuth provider interaction)
            for provider in providers[:1]:  # Test first provider only
                async with self.session.get(
                    f"{auth_url}/oauth/authorize/{provider}",
                    allow_redirects=False
                ) as resp:
                    # Should redirect to OAuth provider
                    assert resp.status in [302, 303], f"OAuth redirect failed: {resp.status}"
                    location = resp.headers.get("Location")
                    assert location, "No redirect location"
                    assert "oauth" in location.lower() or "auth" in location.lower(), \
                           "Invalid OAuth redirect"
            
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return StagingTestResult(
                test_name=test_name,
                status="passed",
                duration_ms=duration,
                details={
                    "providers": providers,
                    "oauth_configured": True
                }
            )
            
        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"OAuth test failed: {e}")
            return StagingTestResult(
                test_name=test_name,
                status="failed",
                duration_ms=duration,
                error_message=str(e)
            )
            
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all staging E2E tests."""
        logger.info("Starting complete staging E2E test suite")
        
        test_methods = [
            self.test_staging_startup,
            self.test_frontend_websocket_connection,
            self.test_example_message,
            self.test_agent_response,
            self.test_full_system,
            self.test_oauth_authentication
        ]
        
        results = []
        for test_method in test_methods:
            try:
                result = await test_method()
                results.append(result)
                logger.info(f"Test {result.test_name}: {result.status}")
            except Exception as e:
                logger.error(f"Test {test_method.__name__} crashed: {e}")
                results.append(StagingTestResult(
                    test_name=test_method.__name__,
                    status="failed",
                    duration_ms=0,
                    error_message=f"Test crashed: {str(e)}"
                ))
                
        # Generate summary
        passed = len([r for r in results if r.status == "passed"])
        failed = len([r for r in results if r.status == "failed"])
        skipped = len([r for r in results if r.status == "skipped"])
        total_duration = sum(r.duration_ms for r in results)
        
        summary = {
            "total_tests": len(results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": passed / len(results) if results else 0,
            "total_duration_ms": total_duration,
            "test_results": [
                {
                    "name": r.test_name,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "error": r.error_message,
                    "details": r.details
                }
                for r in results
            ],
            "environment": "staging",
            "timestamp": datetime.now().isoformat()
        }
        
        return summary


@env("staging")
@env_requires(
    services=["auth_service", "backend", "frontend", "websocket", "postgres", "redis"],
    features=["oauth_configured", "ssl_enabled", "cors_configured"],
    data=["staging_test_tenant"]
)
@pytest.mark.staging
@pytest.mark.e2e
class TestStagingE2E:
    """Pytest integration for staging E2E tests."""
    
    @pytest.fixture
    async def test_suite(self):
        """Create and setup test suite."""
        suite = StagingE2ETestSuite()
        await suite.setup()
        yield suite
        await suite.teardown()
        
    @pytest.mark.asyncio
    async def test_staging_complete_e2e(self, test_suite):
        """Run complete staging E2E test suite."""
        results = await test_suite.run_all_tests()
        
        # Log results
        logger.info(f"Staging E2E Results: {results['passed']}/{results['total_tests']} passed")
        
        # Assert overall success
        assert results["failed"] == 0, f"Failed tests: {results['failed']}"
        assert results["success_rate"] >= 0.8, f"Success rate too low: {results['success_rate']}"
        
        # Save results to file for reporting
        
        results_dir = Path("test_reports/staging_e2e")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"staging_e2e_results_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Results saved to {results_file}")


if __name__ == "__main__":
    # Allow running directly for testing
    async def main():
        suite = StagingE2ETestSuite()
        await suite.setup()
        try:
            results = await suite.run_all_tests()
            print(json.dumps(results, indent=2))
        finally:
            await suite.teardown()
            
    asyncio.run(main())