"""
E2E tests for WebSocket Business Value Validation - Testing end-to-end business value delivery.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: End-to-end business value validation and user journey completion
- Value Impact: Validates that users successfully complete valuable AI workflows via WebSocket
- Strategic Impact: Critical for revenue validation - proves the system delivers promised business value

These E2E tests validate complete business value delivery workflows: from user problem
to AI-generated business solution with actionable insights, all delivered via WebSocket.

CRITICAL: All E2E tests MUST use authentication as per CLAUDE.md requirements.
"""

import pytest
import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from test_framework.ssot.base import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import WebSocketTestUtility
from shared.isolated_environment import get_env


class TestWebSocketBusinessValueValidationE2E(SSotBaseTestCase):
    """E2E tests for complete business value delivery via WebSocket."""
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated E2E auth helper."""
        env = get_env()
        config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            jwt_secret=env.get("JWT_SECRET", "test-jwt-secret-key-unified-testing-32chars")
        )
        return E2EAuthHelper(config)
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_complete_cost_optimization_business_value_e2e(self, auth_helper, websocket_utility):
        """Test complete cost optimization business value delivery with authentication.
        
        Validates end-to-end value: user business problem  ->  AI analysis  ->  actionable savings recommendations.
        """
        # STEP 1: Authenticate business user (MANDATORY for E2E)
        business_user_auth = await auth_helper.authenticate_test_user(
            email="cfo@businesscorp.com",
            subscription_tier="enterprise"
        )
        
        assert business_user_auth.success is True, f"Authentication failed: {business_user_auth.error}"
        
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=business_user_auth.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket:
            
            # STEP 2: Simulate realistic business scenario
            business_scenario = {
                "type": "start_agent",
                "agent": "cost_optimizer",
                "message": """Our company is spending $45,000/month on cloud infrastructure across AWS, Azure, and GCP. 
                We need to identify immediate cost reduction opportunities while maintaining performance. 
                Priority areas: compute optimization, storage efficiency, and network costs. 
                Target: 20% cost reduction within 90 days.""",
                "business_context": {
                    "company_size": "mid_market",
                    "monthly_cloud_spend": 45000,
                    "reduction_target_percent": 20,
                    "timeline_days": 90,
                    "priority_areas": ["compute", "storage", "network"],
                    "performance_requirements": "maintain_current_performance"
                },
                "user_id": business_user_auth.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send_json(business_scenario)
            
            # STEP 3: Collect complete business value workflow
            business_workflow_events = []
            final_business_result = None
            max_business_analysis_time = 90  # Allow up to 90 seconds for comprehensive analysis
            start_analysis_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_analysis_time) < max_business_analysis_time:
                try:
                    event = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
                    business_workflow_events.append(event)
                    
                    # Check for agent completion with business results
                    if event.get("type") == "agent_completed":
                        final_business_result = event
                        break
                    
                except asyncio.TimeoutError:
                    # Continue waiting - business analysis may take time
                    continue
            
            # STEP 4: Validate business value workflow completion
            assert final_business_result is not None, "Business analysis must complete with actionable results"
            
            event_types = [event.get("type") for event in business_workflow_events]
            
            # Critical business workflow events
            required_business_events = [
                "agent_started",      # Business engagement initiated
                "agent_thinking",     # Business problem analysis
                "tool_executing",     # Data analysis tools
                "tool_completed",     # Analysis results
                "agent_completed"     # Business recommendations ready
            ]
            
            for required_event in required_business_events:
                assert required_event in event_types, f"Critical business event '{required_event}' missing"
            
            # STEP 5: Validate actionable business insights
            business_result = final_business_result.get("data", {}).get("result", {})
            assert business_result, "Must provide concrete business results"
            
            business_result_text = str(business_result).lower()
            
            # Must contain cost savings analysis
            savings_indicators = ["savings", "reduce", "save", "cost reduction", "optimize", "efficiency"]
            savings_content = sum(1 for indicator in savings_indicators if indicator in business_result_text)
            assert savings_content >= 3, f"Must provide substantial cost savings analysis, found {savings_content} indicators"
            
            # Must contain specific monetary values
            monetary_patterns = [
                r'\$[\d,]+',           # Dollar amounts like $5,000
                r'\d+%',               # Percentages like 25%
                r'\d+\s*(?:dollars|usd|per\s+month|monthly)', # Dollar references
                r'save.*\d+',          # Save + number
            ]
            
            monetary_matches = 0
            for pattern in monetary_patterns:
                if re.search(pattern, business_result_text, re.IGNORECASE):
                    monetary_matches += 1
            
            assert monetary_matches >= 2, f"Must provide specific monetary savings amounts, found {monetary_matches} monetary references"
            
            # Must contain actionable recommendations
            action_indicators = [
                "recommend", "action", "implement", "step", "should", "can",
                "optimize", "upgrade", "migrate", "configure", "adjust"
            ]
            action_content = sum(1 for indicator in action_indicators if indicator in business_result_text)
            assert action_content >= 3, f"Must provide actionable recommendations, found {action_content} action indicators"
            
            # STEP 6: Validate business-specific metrics alignment
            # Should address the original business context
            business_context_alignment = [
                "45000" in business_result_text or "45,000" in business_result_text,  # Original spend amount
                "20%" in business_result_text or "twenty percent" in business_result_text,  # Target reduction
                any(area in business_result_text for area in ["compute", "storage", "network"]),  # Priority areas
                "90" in business_result_text or "three month" in business_result_text or "quarter" in business_result_text  # Timeline
            ]
            
            context_matches = sum(1 for match in business_context_alignment if match)
            assert context_matches >= 2, "Analysis must align with original business context and requirements"
            
            # STEP 7: Validate ROI and business impact quantification
            # Should provide quantifiable business impact
            business_impact_indicators = [
                "roi", "return on investment", "payback", "break even",
                "monthly savings", "annual savings", "cost reduction",
                "efficiency gain", "performance impact"
            ]
            
            impact_quantification = sum(1 for indicator in business_impact_indicators if indicator in business_result_text)
            assert impact_quantification >= 2, "Must quantify business impact and ROI"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_end_to_end_user_journey_value_delivery_e2e(self, auth_helper, websocket_utility):
        """Test complete user journey from problem to solution with authentication.
        
        Validates the entire user experience: problem identification  ->  AI assistance  ->  valuable outcome.
        """
        # Authenticate end user (MANDATORY for E2E)
        end_user_auth = await auth_helper.authenticate_test_user(
            email="operations_manager@company.com",
            subscription_tier="mid"
        )
        
        assert end_user_auth.success is True
        
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=end_user_auth.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket:
            
            # STEP 1: User Journey - Problem Discovery Phase
            problem_discovery = {
                "type": "user_message",
                "message": "I've noticed our cloud costs have increased significantly over the past 3 months. Can you help me understand what's driving this increase?",
                "user_context": {
                    "role": "operations_manager",
                    "urgency": "medium",
                    "business_impact": "budget_variance"
                },
                "user_id": end_user_auth.user_id
            }
            
            await websocket.send_json(problem_discovery)
            
            # Collect initial response
            initial_response = None
            try:
                initial_response = await asyncio.wait_for(websocket.receive_json(), timeout=15)
            except asyncio.TimeoutError:
                pass
            
            assert initial_response is not None, "System must respond to user problem identification"
            
            # STEP 2: User Journey - Deep Dive Analysis Request
            followup_analysis = {
                "type": "start_agent",
                "agent": "cost_analyzer",
                "message": "Please analyze the root causes of our cost increase and provide specific recommendations for optimization. Include trend analysis for the past 6 months.",
                "user_id": end_user_auth.user_id,
                "analysis_scope": {
                    "time_period": "6_months",
                    "focus": "cost_drivers",
                    "output_format": "executive_summary"
                }
            }
            
            await websocket.send_json(followup_analysis)
            
            # STEP 3: Track complete user journey workflow
            user_journey_events = []
            journey_completion = None
            journey_max_time = 60
            journey_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - journey_start) < journey_max_time:
                try:
                    event = await asyncio.wait_for(websocket.receive_json(), timeout=8)
                    user_journey_events.append(event)
                    
                    if event.get("type") in ["agent_completed", "analysis_complete"]:
                        journey_completion = event
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
            # STEP 4: Validate user journey completion
            assert journey_completion is not None, "User journey must complete with valuable insights"
            
            # STEP 5: Validate user experience quality
            user_experience_events = [
                "agent_started",       # User sees agent is working
                "agent_thinking",      # User gets progress updates
                "tool_executing",      # User sees analysis happening
                "agent_completed"      # User gets final results
            ]
            
            journey_event_types = [event.get("type") for event in user_journey_events]
            
            for ux_event in user_experience_events:
                assert ux_event in journey_event_types, f"User experience event '{ux_event}' missing from journey"
            
            # STEP 6: Validate solution quality for end user
            final_solution = journey_completion.get("data", {}).get("result", {})
            solution_text = str(final_solution).lower()
            
            # Solution must address user's original problem
            problem_addressing = [
                "cost increase" in solution_text,
                "3 months" in solution_text or "three month" in solution_text or "quarter" in solution_text,
                any(word in solution_text for word in ["cause", "driver", "reason", "factor"]),
                any(word in solution_text for word in ["recommendation", "solution", "action", "optimize"])
            ]
            
            problem_solution_alignment = sum(1 for addressing in problem_addressing if addressing)
            assert problem_solution_alignment >= 3, "Solution must directly address user's original problem"
            
            # STEP 7: Validate actionability for operations manager
            operations_relevance = [
                any(word in solution_text for word in ["operations", "operational", "manage", "monitor"]),
                any(word in solution_text for word in ["implement", "deploy", "configure", "set up"]),
                any(word in solution_text for word in ["track", "measure", "metrics", "kpi"]),
                any(word in solution_text for word in ["team", "resource", "process", "workflow"])
            ]
            
            ops_relevance_score = sum(1 for relevance in operations_relevance if relevance)
            assert ops_relevance_score >= 2, "Solution must be relevant and actionable for operations manager"
            
            # STEP 8: Test user follow-up interaction
            followup_question = {
                "type": "user_message", 
                "message": "This analysis is helpful! Can you prioritize these recommendations by implementation difficulty and impact?",
                "user_id": end_user_auth.user_id,
                "followup_context": True
            }
            
            await websocket.send_json(followup_question)
            
            followup_response = None
            try:
                followup_response = await asyncio.wait_for(websocket.receive_json(), timeout=20)
            except asyncio.TimeoutError:
                pass
            
            # Should handle follow-up questions
            if followup_response:
                followup_content = str(followup_response).lower()
                prioritization_indicators = ["priority", "first", "second", "high", "low", "easy", "difficult", "impact"]
                prioritization_mentioned = sum(1 for indicator in prioritization_indicators if indicator in followup_content)
                
                assert prioritization_mentioned >= 2, "Should provide prioritization guidance for implementation"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_tier_business_value_comparison_e2e(self, auth_helper, websocket_utility):
        """Test business value delivery across different subscription tiers with authentication.
        
        Validates that each tier receives appropriate value while encouraging upgrades.
        """
        # Authenticate users from different tiers
        tier_users = []
        
        tier_configs = [
            {"tier": "free", "email": "free_user@startup.com"},
            {"tier": "early", "email": "early_user@growing.com"}, 
            {"tier": "enterprise", "email": "enterprise_user@bigcorp.com"}
        ]
        
        for config in tier_configs:
            auth_result = await auth_helper.authenticate_test_user(
                email=config["email"],
                subscription_tier=config["tier"]
            )
            assert auth_result.success is True, f"Authentication failed for {config['tier']} tier"
            tier_users.append((config["tier"], auth_result))
        
        # Test business value delivery for each tier
        tier_results = {}
        
        for tier, user_auth in tier_users:
            async with websocket_utility.create_authenticated_websocket_client(
                access_token=user_auth.access_token,
                websocket_url=auth_helper.config.websocket_url
            ) as websocket:
                
                # Same business question for all tiers
                business_question = {
                    "type": "start_agent",
                    "agent": "cost_optimizer",
                    "message": "I need help optimizing our cloud costs. Please analyze our current spend and suggest improvements.",
                    "user_id": user_auth.user_id,
                    "tier_test": True
                }
                
                await websocket.send_json(business_question)
                
                # Collect tier-specific response
                tier_events = []
                tier_completion = None
                tier_max_time = 45
                tier_start = asyncio.get_event_loop().time()
                
                while (asyncio.get_event_loop().time() - tier_start) < tier_max_time:
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=5)
                        tier_events.append(event)
                        
                        if event.get("type") == "agent_completed":
                            tier_completion = event
                            break
                        elif event.get("type") == "subscription_upgrade_required":
                            # Free tier may get upgrade prompts
                            tier_completion = event
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                tier_results[tier] = {
                    "events": tier_events,
                    "completion": tier_completion,
                    "event_types": [e.get("type") for e in tier_events]
                }
        
        # Validate tier-appropriate value delivery
        
        # FREE TIER: Should get basic value with upgrade encouragement
        if "free" in tier_results:
            free_events = tier_results["free"]["event_types"]
            free_completion = tier_results["free"]["completion"]
            
            # Should receive some response (not completely blocked)
            assert free_completion is not None, "Free tier should receive some response"
            
            if free_completion.get("type") == "subscription_upgrade_required":
                # Acceptable - free tier gets upgrade prompt
                upgrade_content = str(free_completion).lower()
                value_preview = any(word in upgrade_content for word in ["preview", "sample", "example", "basic"])
                upgrade_path = any(word in upgrade_content for word in ["upgrade", "premium", "unlock", "full"])
                
                assert value_preview and upgrade_path, "Free tier should get value preview and clear upgrade path"
            else:
                # If full response, should be basic level
                free_result = str(free_completion.get("data", {})).lower()
                # Should be shorter/more basic than enterprise
                assert len(free_result) >= 100, "Free tier should get meaningful basic response"
        
        # EARLY TIER: Should get good value with some premium feature hints
        if "early" in tier_results:
            early_events = tier_results["early"]["event_types"]
            early_completion = tier_results["early"]["completion"]
            
            assert early_completion is not None, "Early tier should receive full response"
            assert early_completion.get("type") == "agent_completed", "Early tier should get complete analysis"
            
            early_result = str(early_completion.get("data", {})).lower()
            assert len(early_result) >= 300, "Early tier should get substantial analysis"
            
            # Should include some advanced features
            early_features = ["optimization", "recommendation", "analysis"]
            early_feature_count = sum(1 for feature in early_features if feature in early_result)
            assert early_feature_count >= 2, "Early tier should get good feature set"
        
        # ENTERPRISE TIER: Should get comprehensive value
        if "enterprise" in tier_results:
            enterprise_events = tier_results["enterprise"]["event_types"]
            enterprise_completion = tier_results["enterprise"]["completion"]
            
            assert enterprise_completion is not None, "Enterprise should receive comprehensive response"
            assert enterprise_completion.get("type") == "agent_completed", "Enterprise should get complete analysis"
            
            enterprise_result = str(enterprise_completion.get("data", {})).lower()
            assert len(enterprise_result) >= 500, "Enterprise should get comprehensive analysis"
            
            # Should include advanced enterprise features
            enterprise_features = [
                "advanced", "comprehensive", "detailed", "custom", "priority",
                "roi", "forecast", "strategic", "enterprise"
            ]
            enterprise_feature_count = sum(1 for feature in enterprise_features if feature in enterprise_result)
            assert enterprise_feature_count >= 3, "Enterprise should get advanced feature set"
        
        # COMPARATIVE VALIDATION: Enterprise should get more value than Early, Early more than Free
        if "enterprise" in tier_results and "early" in tier_results:
            enterprise_content = str(tier_results["enterprise"]["completion"].get("data", {}))
            early_content = str(tier_results["early"]["completion"].get("data", {}))
            
            # Enterprise should get more comprehensive response
            assert len(enterprise_content) >= len(early_content), "Enterprise should get more comprehensive response than Early"
        
        if "early" in tier_results and "free" in tier_results:
            early_content = str(tier_results["early"]["completion"].get("data", {}))
            free_content = str(tier_results["free"]["completion"].get("data", {}))
            
            # Early should get more value than Free
            if tier_results["free"]["completion"].get("type") != "subscription_upgrade_required":
                assert len(early_content) >= len(free_content), "Early should get more value than Free"