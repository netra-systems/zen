"""
Test End-to-End User Journey Performance E2E

Business Value Justification (BVJ):
- Segment: All customer segments (complete user experience)
- Business Goal: Validate complete user workflows perform acceptably
- Value Impact: E2E performance directly correlates with customer satisfaction
- Strategic Impact: Smooth user journeys enable customer success and retention

CRITICAL REQUIREMENTS:
- Tests complete user journeys from authentication to value delivery
- Validates realistic user workflows with multiple service interactions
- Uses real authentication, databases, LLM calls, WebSocket connections
- MANDATORY: Complete authenticated user journey validation
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


class TestEndToEndUserJourneyPerformanceE2E(BaseE2ETest):
    """Test complete end-to-end user journey performance"""
    
    def setup_method(self):
        """Set up E2E test environment"""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper()
        self.test_prefix = f"journey_{uuid.uuid4().hex[:8]}"
        
        # Service URLs
        self.backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
        self.auth_url = self.env.get("AUTH_URL", "http://localhost:8081")
        self.websocket_url = self.env.get("WEBSOCKET_URL", "ws://localhost:8000/ws")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_complete_user_onboarding_to_value_delivery_journey(self):
        """Test complete user journey from onboarding to receiving value"""
        # Define complete user journey scenarios
        user_journeys = [
            {
                "journey_name": "free_user_trial",
                "user_tier": "free",
                "expected_max_duration": 60.0,
                "steps": ["signup", "profile_setup", "first_agent_request", "view_results"]
            },
            {
                "journey_name": "enterprise_user_full_flow",
                "user_tier": "enterprise", 
                "expected_max_duration": 45.0,
                "steps": ["signup", "profile_setup", "create_project", "agent_optimization", "analytics_review"]
            }
        ]
        
        # Execute user journeys concurrently
        journey_tasks = [
            self._execute_complete_user_journey(journey)
            for journey in user_journeys
        ]
        
        journey_results = await asyncio.gather(*journey_tasks, return_exceptions=True)
        
        # Validate journey results
        successful_journeys = [
            r for r in journey_results 
            if isinstance(r, dict) and r.get("journey_completed", False)
        ]
        
        journey_success_rate = len(successful_journeys) / len(journey_results)
        assert journey_success_rate >= 0.8, f"User journey success rate too low: {journey_success_rate:.2%}"
        
        # Validate performance by tier
        for result in successful_journeys:
            journey_duration = result["total_journey_time"]
            expected_max = next(j["expected_max_duration"] for j in user_journeys if j["journey_name"] == result["journey_name"])
            
            assert journey_duration <= expected_max, \
                f"Journey {result['journey_name']} too slow: {journey_duration:.2f}s (max: {expected_max}s)"
    
    async def _execute_complete_user_journey(self, journey_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete user journey"""
        journey_start_time = time.time()
        step_results = []
        
        try:
            # Step 1: User Signup/Authentication
            step_start = time.time()
            auth_result = await self.auth_helper.create_and_authenticate_user(
                email=f"{journey_config['journey_name']}@example.com",
                tier=journey_config["user_tier"],
                test_prefix=self.test_prefix
            )
            step_end = time.time()
            
            if not auth_result.success:
                return {"journey_completed": False, "error": "Authentication failed"}
            
            step_results.append({
                "step": "signup",
                "duration": step_end - step_start,
                "success": True
            })
            
            user_context = {
                "user_id": auth_result.user_id,
                "access_token": auth_result.access_token,
                "tier": journey_config["user_tier"]
            }
            
            # Execute journey steps
            for step_name in journey_config["steps"][1:]:  # Skip signup (already done)
                step_result = await self._execute_journey_step(step_name, user_context)
                step_results.append(step_result)
                
                if not step_result["success"]:
                    return {
                        "journey_completed": False,
                        "journey_name": journey_config["journey_name"],
                        "failed_step": step_name,
                        "error": step_result.get("error", "Unknown error")
                    }
            
            journey_end_time = time.time()
            total_journey_time = journey_end_time - journey_start_time
            
            return {
                "journey_completed": True,
                "journey_name": journey_config["journey_name"],
                "user_tier": journey_config["user_tier"],
                "total_journey_time": total_journey_time,
                "step_results": step_results,
                "steps_completed": len(step_results)
            }
            
        except Exception as e:
            return {
                "journey_completed": False,
                "journey_name": journey_config["journey_name"],
                "error": str(e)
            }
    
    async def _execute_journey_step(self, step_name: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute individual journey step"""
        step_start = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if step_name == "profile_setup":
                    # Set up user profile
                    response = await client.put(
                        f"{self.backend_url}/api/user/profile",
                        headers={
                            "Authorization": f"Bearer {user_context['access_token']}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "display_name": f"Test User {user_context['user_id'][:8]}",
                            "preferences": {"theme": "light", "notifications": True}
                        }
                    )
                    success = response.status_code in [200, 201]
                
                elif step_name == "create_project":
                    # Create new project
                    response = await client.post(
                        f"{self.backend_url}/api/projects",
                        headers={
                            "Authorization": f"Bearer {user_context['access_token']}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "name": f"Test Project {self.test_prefix}",
                            "description": "Test project for E2E journey",
                            "type": "optimization"
                        }
                    )
                    success = response.status_code in [200, 201]
                
                elif step_name == "first_agent_request" or step_name == "agent_optimization":
                    # Execute agent request
                    agent_type = "triage_agent" if step_name == "first_agent_request" else "cost_optimizer"
                    message = "Help me get started" if step_name == "first_agent_request" else "Optimize my AWS costs"
                    
                    response = await client.post(
                        f"{self.backend_url}/api/agents/execute",
                        headers={
                            "Authorization": f"Bearer {user_context['access_token']}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "agent_type": agent_type,
                            "message": message,
                            "options": {"priority": "normal"}
                        }
                    )
                    success = response.status_code == 200
                
                elif step_name == "view_results" or step_name == "analytics_review":
                    # View user dashboard/results
                    endpoint = "/api/dashboard" if step_name == "view_results" else "/api/analytics/summary"
                    response = await client.get(
                        f"{self.backend_url}{endpoint}",
                        headers={"Authorization": f"Bearer {user_context['access_token']}"}
                    )
                    success = response.status_code == 200
                
                else:
                    success = True  # Default success for unknown steps
                
                step_end = time.time()
                return {
                    "step": step_name,
                    "duration": step_end - step_start,
                    "success": success
                }
                
        except Exception as e:
            step_end = time.time()
            return {
                "step": step_name,
                "duration": step_end - step_start,
                "success": False,
                "error": str(e)
            }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])