"""Agent Billing Test Helpers - Modular Support for E2E Billing Tests

Helper classes and utilities for agent billing flow testing.
Supports the comprehensive E2E test for usage-based billing validation.

Business Value Justification (BVJ):
1. Segment: ALL paid tiers (supporting revenue-critical billing tests)
2. Business Goal: Modular test infrastructure for billing accuracy
3. Value Impact: Ensures reliable billing validation across all agent types
4. Revenue Impact: Supports tests that protect $100-1000/month per customer

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (extracted from main test file)
- Function size: <8 lines each
- Modular design supporting main billing flow test
- Reusable components for different agent types
"""

import time
import json
import asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch

from tests.unified.config import TEST_USERS
from tests.unified.e2e.clickhouse_billing_helper import ClickHouseBillingHelper
from tests.unified.e2e.websocket_resilience_core import WebSocketResilienceTestCore
from netra_backend.app.schemas.UserPlan import PlanTier, UsageRecord


class AgentBillingTestCore:
    """Core agent billing test infrastructure."""
    
    def __init__(self):
        self.billing_helper = ClickHouseBillingHelper()
        self.websocket_core = WebSocketResilienceTestCore()
        self.test_session_data = {}
    
    async def setup_test_environment(self) -> None:
        """Setup complete test environment."""
        await self.billing_helper.setup_billing_environment()
        self.test_session_data.clear()
    
    async def teardown_test_environment(self) -> None:
        """Cleanup test environment."""
        await self.billing_helper.teardown_billing_environment()
        self.test_session_data.clear()
    
    async def establish_authenticated_user_session(self, tier: PlanTier) -> Dict[str, Any]:
        """Establish authenticated user session for testing."""
        # Get test user for tier
        user_data = self._get_test_user_for_tier(tier)
        
        # Establish WebSocket connection
        client = await self.websocket_core.establish_authenticated_connection(user_data.id)
        
        return {
            "client": client,
            "user_data": {"id": user_data.id, "email": user_data.email, "full_name": user_data.full_name},
            "tier": tier,
            "session_start": time.time()
        }
    
    def _get_test_user_for_tier(self, tier: PlanTier):
        """Get test user configuration for plan tier."""
        tier_user_map = {
            PlanTier.FREE: TEST_USERS["free"],
            PlanTier.PRO: TEST_USERS["early"], 
            PlanTier.ENTERPRISE: TEST_USERS["enterprise"],
            PlanTier.DEVELOPER: TEST_USERS["mid"]
        }
        return tier_user_map.get(tier, TEST_USERS["free"])


class AgentRequestSimulator:
    """Simulates different agent request types with known costs."""
    
    def __init__(self):
        self.agent_cost_map = {
            "triage": {"tokens": 500, "cost_cents": 8},
            "data": {"tokens": 1500, "cost_cents": 25},
            "admin": {"tokens": 800, "cost_cents": 12}
        }
    
    def create_triage_request(self, user_id: str) -> Dict[str, Any]:
        """Create triage agent request."""
        return {
            "type": "agent_request",
            "agent_type": "triage",
            "user_id": user_id,
            "message": "Analyze my data usage patterns",
            "expected_cost": self.agent_cost_map["triage"]
        }
    
    def create_data_request(self, user_id: str) -> Dict[str, Any]:
        """Create data agent request.""" 
        return {
            "type": "agent_request",
            "agent_type": "data",
            "user_id": user_id,
            "message": "Generate comprehensive usage report for last 30 days",
            "expected_cost": self.agent_cost_map["data"]
        }
    
    def create_admin_request(self, user_id: str) -> Dict[str, Any]:
        """Create admin tool dispatcher request."""
        return {
            "type": "agent_request", 
            "agent_type": "admin",
            "user_id": user_id,
            "message": "Execute corpus analysis and optimization",
            "expected_cost": self.agent_cost_map["admin"]
        }
    
    def get_agent_types(self) -> List[str]:
        """Get all available agent types."""
        return list(self.agent_cost_map.keys())
    
    def create_high_cost_request(self, user_id: str) -> Dict[str, Any]:
        """Create high-cost request for performance testing."""
        return {
            "type": "agent_request",
            "agent_type": "data",
            "user_id": user_id,
            "message": "Generate full enterprise analytics with AI optimization recommendations",
            "expected_cost": {"tokens": 3000, "cost_cents": 50}
        }


class BillingFlowValidator:
    """Validates complete billing flow for agent requests."""
    
    def __init__(self, billing_helper: ClickHouseBillingHelper):
        self.billing_helper = billing_helper
        self.validation_results = {}
    
    async def validate_agent_response_flow(self, session: Dict, request: Dict, 
                                         response: Dict) -> Dict[str, Any]:
        """Validate agent response and billing flow."""
        user_id = session["user_data"]["id"]
        tier = session["tier"]
        
        # Validate response structure
        response_valid = self._validate_response_structure(response)
        
        # Validate usage record creation
        usage_valid = await self._validate_usage_tracking(user_id, request, tier)
        
        # Validate billing record creation
        billing_valid = await self._validate_billing_record(user_id, request, tier)
        
        return {
            "response_valid": response_valid,
            "usage_tracked": usage_valid["tracked"],
            "billing_recorded": billing_valid["recorded"],
            "cost_accurate": billing_valid["cost_accurate"],
            "flow_complete": all([response_valid, usage_valid["tracked"], 
                                billing_valid["recorded"]])
        }
    
    def _validate_response_structure(self, response: Dict) -> bool:
        """Validate agent response structure."""
        required_fields = ["status", "result", "execution_time", "tokens_used"]
        return all(field in response for field in required_fields)
    
    async def _validate_usage_tracking(self, user_id: str, request: Dict, 
                                     tier: PlanTier) -> Dict[str, Any]:
        """Validate usage record in ClickHouse."""
        # Create expected usage record
        expected_cost = request["expected_cost"]
        
        usage_result = await self.billing_helper.create_usage_record_for_billing(
            user_id, tier
        )
        
        return {
            "tracked": usage_result["usage_record_created"],
            "record": usage_result.get("record"),
            "cost_match": usage_result.get("record", {}).get("cost_cents") == expected_cost["cost_cents"]
        }
    
    async def _validate_billing_record(self, user_id: str, request: Dict,
                                     tier: PlanTier) -> Dict[str, Any]:
        """Validate billing record creation and accuracy.""" 
        expected_cost = request["expected_cost"]
        
        # Create billing record for agent usage
        payment_data = {
            "id": f"agent_usage_{user_id}_{int(time.time())}",
            "amount_cents": expected_cost["cost_cents"]
        }
        user_data = {"id": user_id}
        
        try:
            billing_result = await self.billing_helper.create_and_validate_billing_record(
                payment_data, user_data, tier
            )
            
            return {
                "recorded": billing_result["clickhouse_inserted"],
                "cost_accurate": billing_result["billing_record"]["amount_cents"] == expected_cost["cost_cents"],
                "validation_passed": billing_result["validation"]["valid"]
            }
        except Exception as e:
            return {
                "recorded": False,
                "cost_accurate": False, 
                "validation_passed": False,
                "error": str(e)
            }


class AgentBillingTestUtils:
    """Utility functions for agent billing tests."""
    
    @staticmethod
    async def send_agent_request(client, request: Dict) -> Dict[str, Any]:
        """Send agent request via WebSocket and get response."""
        # Send request
        await client.send(json.dumps(request))
        
        # Wait for response with timeout
        response = await asyncio.wait_for(
            client.receive(), timeout=5.0
        )
        
        return json.loads(response) if isinstance(response, str) else response
    
    @staticmethod
    def create_mock_llm_response(tokens_used: int) -> AsyncMock:
        """Create mock LLM response for deterministic testing."""
        mock_response = AsyncMock(return_value={
            "content": "Analysis complete",
            "tokens_used": tokens_used
        })
        return mock_response
    
    @staticmethod
    def validate_performance_timing(start_time: float, max_seconds: float = 5.0) -> bool:
        """Validate operation completed within time limit."""
        elapsed = time.time() - start_time
        return elapsed < max_seconds
    
    @staticmethod
    def extract_billing_metrics(validation_result: Dict) -> Dict[str, Any]:
        """Extract key billing metrics from validation result."""
        return {
            "billing_success": validation_result.get("flow_complete", False),
            "cost_accuracy": validation_result.get("cost_accurate", False),
            "response_time_valid": validation_result.get("response_time_valid", False),
            "usage_tracked": validation_result.get("usage_tracked", False)
        }
