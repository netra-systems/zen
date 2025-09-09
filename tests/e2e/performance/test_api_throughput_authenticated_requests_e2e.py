"""
Test API Throughput Authenticated Requests E2E

Business Value Justification (BVJ):
- Segment: All customer segments (API performance foundation)
- Business Goal: Ensure API can handle realistic request volumes
- Value Impact: API performance directly affects user experience
- Strategic Impact: High-performance API enables competitive advantage

CRITICAL REQUIREMENTS:
- Tests complete E2E API flows with authenticated requests
- Validates API throughput under realistic load patterns
- Uses real authentication tokens and rate limiting
- MANDATORY: All API calls MUST use proper authentication
"""

import pytest
import asyncio
import httpx
import time
import uuid
from typing import Dict, List, Optional, Any

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.base_e2e_test import BaseE2ETest
from shared.isolated_environment import get_env


class TestAPIThroughputAuthenticatedRequestsE2E(BaseE2ETest):
    """Test API throughput with authenticated requests"""
    
    def setup_method(self):
        """Set up E2E test environment"""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper()
        self.test_prefix = f"api_throughput_{uuid.uuid4().hex[:8]}"
        self.backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_authenticated_api_endpoint_throughput(self):
        """Test API endpoint throughput with authenticated users"""
        concurrent_users = 15
        requests_per_user = 8
        
        # Create authenticated users
        authenticated_users = []
        for i in range(concurrent_users):
            tier = ["free", "mid", "enterprise"][i % 3]
            auth_result = await self.auth_helper.create_and_authenticate_user(
                email=f"api_user_{i}@example.com",
                tier=tier,
                test_prefix=self.test_prefix
            )
            
            if auth_result.success:
                authenticated_users.append({
                    "user_id": auth_result.user_id,
                    "tier": tier,
                    "access_token": auth_result.access_token
                })
        
        assert len(authenticated_users) >= concurrent_users * 0.8
        
        # Test different API endpoints
        api_endpoints = [
            {"path": "/api/health", "method": "GET", "expected_status": 200},
            {"path": "/api/user/profile", "method": "GET", "expected_status": 200},
            {"path": "/api/projects", "method": "GET", "expected_status": 200}
        ]
        
        for endpoint in api_endpoints:
            print(f"Testing endpoint: {endpoint['path']}")
            
            # Execute concurrent requests to this endpoint
            request_tasks = []
            for user in authenticated_users:
                for req_num in range(requests_per_user):
                    task = self._make_authenticated_request(
                        user=user,
                        endpoint=endpoint,
                        request_id=f"{user['user_id']}_{req_num}"
                    )
                    request_tasks.append(task)
            
            start_time = time.time()
            request_results = await asyncio.gather(*request_tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successful_requests = [
                r for r in request_results 
                if isinstance(r, dict) and r.get("success", False)
            ]
            
            success_rate = len(successful_requests) / len(request_results)
            total_duration = end_time - start_time
            throughput = len(successful_requests) / total_duration
            
            # Validate API performance
            assert success_rate >= 0.80, f"API success rate too low for {endpoint['path']}: {success_rate:.2%}"
            assert throughput >= 10, f"API throughput too low for {endpoint['path']}: {throughput:.2f} req/s"
            
            # Response time validation
            response_times = [r["response_time"] for r in successful_requests if "response_time" in r]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                assert avg_response_time < 2.0, f"Average response time too high: {avg_response_time:.2f}s"
    
    async def _make_authenticated_request(self, user: Dict[str, Any], endpoint: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Make authenticated API request"""
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=endpoint["method"],
                    url=f"{self.backend_url}{endpoint['path']}",
                    headers={
                        "Authorization": f"Bearer {user['access_token']}",
                        "X-Test-ID": self.test_prefix
                    }
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                return {
                    "success": response.status_code == endpoint["expected_status"],
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "user_tier": user["tier"],
                    "request_id": request_id
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])