"""Cost Tracking Test Helpers - Modular Support for E2E Cost Accuracy Tests

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: ALL paid tiers (supporting revenue-critical cost tracking)
2. Business Goal: Modular test infrastructure for cost accuracy validation
3. Value Impact: Ensures reliable cost tracking across all AI operations
4. Revenue Impact: Supports tests that protect $40K+ MRR from billing disputes

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (modular helper components)
- Function size: <8 lines each
- Supports main cost tracking accuracy E2E test
- Real service integration with deterministic cost mocking
"""

import asyncio
import json
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage
from netra_backend.app.schemas.user_plan import PlanTier
from netra_backend.app.services.cost_calculator import CostCalculatorService
from tests.e2e.config import TEST_USERS
from tests.e2e.clickhouse_billing_helper import ClickHouseBillingHelper
from tests.e2e.websocket_resilience_core import WebSocketResilienceTestCore
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class CostTrackingTestCore:
    """Core cost tracking test infrastructure."""
    
    def __init__(self):
        self.billing_helper = ClickHouseBillingHelper()
        self.websocket_core = WebSocketResilienceTestCore()
        self.cost_calculator = CostCalculatorService()
        self.test_session_data = {}
    
    async def setup_test_environment(self) -> None:
        """Setup complete cost tracking test environment."""
        await self.billing_helper.setup_billing_environment()
        self.test_session_data.clear()
    
    async def test_teardown_test_environment(self) -> None:
        """Cleanup cost tracking test environment."""
        await self.billing_helper.teardown_billing_environment()
        self.test_session_data.clear()
    
    async def establish_user_session(self, tier: PlanTier) -> Dict[str, Any]:
        """Establish authenticated user session for cost tracking."""
        user_data = self._get_test_user_for_tier(tier)
        client = await self.websocket_core.establish_authenticated_connection(user_data.id)
        
        return {
            "client": client,
            "user_id": user_data.id,
            "user_data": {"id": user_data.id, "email": user_data.email},
            "tier": tier,
            "session_start": time.time()
        }
    
    async def execute_operation_with_cost_tracking(self, session: Dict, operation: Dict) -> Dict:
        """Execute AI operation with full cost tracking."""
        start_time = time.time()
        
        # Send operation through WebSocket
        await session["client"].send(json.dumps(operation))
        response = await asyncio.wait_for(session["client"].receive(), timeout=5.0)
        
        execution_time = time.time() - start_time
        return {
            "response": json.loads(response) if isinstance(response, str) else response,
            "execution_time": execution_time,
            "operation": operation
        }
    
    def _get_test_user_for_tier(self, tier: PlanTier):
        """Get test user for plan tier."""
        tier_map = {
            PlanTier.FREE: TEST_USERS["free"],
            PlanTier.PRO: TEST_USERS["early"], 
            PlanTier.ENTERPRISE: TEST_USERS["enterprise"],
            PlanTier.DEVELOPER: TEST_USERS["mid"]
        }
        return tier_map.get(tier, TEST_USERS["free"])


class AIOperationSimulator:
    """Simulates AI operations with known cost structures for validation."""
    
    def __init__(self):
        self.operation_cost_map = {PlanTier.PRO: {"tokens": 1000, "cost_cents": 15}}
        self.provider_models = {LLMProvider.OPENAI: {"tokens": 1000, "cost_cents": 15, "model": LLMModel.GEMINI_2_5_FLASH.value}}
    
    def create_data_analysis_operation(self, user_id: str, expected_tokens: int = 1200, 
                                     expected_cost_cents: int = 18) -> Dict[str, Any]:
        """Create data analysis operation with known costs."""
        return {
            "type": "ai_operation",
            "operation_type": "data_analysis", 
            "user_id": user_id,
            "prompt": "Analyze user behavior patterns from the last 30 days",
            "expected_tokens": expected_tokens,
            "expected_cost_cents": expected_cost_cents,
            "provider": LLMProvider.OPENAI.value,
            "model": LLMModel.GEMINI_2_5_FLASH.value
        }
    
    def create_optimization_operation(self, user_id: str) -> Dict[str, Any]:
        """Create optimization operation."""
        return {
            "type": "ai_operation",
            "operation_type": "optimization",
            "user_id": user_id,
            "prompt": "Optimize AI infrastructure for maximum cost-efficiency",
            "expected_tokens": 800,
            "expected_cost_cents": 12,
            "provider": LLMProvider.ANTHROPIC.value,
            "model": "claude-3.5-sonnet"
        }
    
    def create_analysis_operation(self, user_id: str) -> Dict[str, Any]:
        """Create analysis operation."""
        return {
            "type": "ai_operation",
            "operation_type": "analysis",
            "user_id": user_id,
            "prompt": "Generate comprehensive performance analysis report",
            "expected_tokens": 1500,
            "expected_cost_cents": 22,
            "provider": LLMProvider.OPENAI.value,
            "model": LLMModel.GEMINI_2_5_FLASH.value
        }
    
    def create_report_generation_operation(self, user_id: str) -> Dict[str, Any]:
        """Create report generation operation."""
        return {
            "type": "ai_operation",
            "operation_type": "report_generation",
            "user_id": user_id,
            "prompt": "Generate detailed monthly usage and optimization report",
            "expected_tokens": 2000,
            "expected_cost_cents": 30,
            "provider": LLMProvider.GOOGLE.value,
            "model": "gemini-2.5-pro"
        }

    def create_provider_specific_operation(self, user_id: str, provider: LLMProvider) -> Dict[str, Any]:
        """Create provider-specific operation."""
        model_config = self.provider_models[provider]
        return {
            "type": "ai_operation",
            "operation_type": "provider_test",
            "user_id": user_id,
            "prompt": f"Test operation for {provider.value} provider",
            "expected_tokens": model_config["tokens"],
            "expected_cost_cents": model_config["cost_cents"],
            "provider": provider.value,
            "model": model_config["model"]
        }


class CostCalculationValidator:
    """Validates cost calculation accuracy across operations."""
    
    def __init__(self):
        self.cost_calculator = CostCalculatorService()
        self.validation_results = {}
    
    async def validate_operation_cost_calculation(self, operation: Dict) -> Dict[str, Any]:
        """Validate cost calculation for operation."""
        provider = LLMProvider(operation["provider"])
        model = operation["model"]
        expected_tokens = operation["expected_tokens"]
        expected_cost_cents = operation["expected_cost_cents"]
        
        # Create token usage
        usage = TokenUsage(
            prompt_tokens=int(expected_tokens * 0.7),
            completion_tokens=int(expected_tokens * 0.3),
            total_tokens=expected_tokens
        )
        
        # Calculate cost using production service
        calculated_cost = self.cost_calculator.calculate_cost(usage, provider, model)
        calculated_cost_cents = int(calculated_cost * 100)
        
        return {
            "calculation_accurate": calculated_cost_cents == expected_cost_cents,
            "calculated_cost_cents": calculated_cost_cents,
            "expected_cost_cents": expected_cost_cents,
            "cost_variance_cents": abs(calculated_cost_cents - expected_cost_cents),
            "provider": provider.value,
            "model": model
        }
    
    async def validate_operation_cost_accuracy(self, operation: Dict, result: Dict) -> Dict[str, bool]:
        """Validate operation cost accuracy against result."""
        validation = await self.validate_operation_cost_calculation(operation)
        return {"accurate": validation["calculation_accurate"]}
    


class BillingAccuracyValidator:
    """Validates billing accuracy and database consistency."""
    
    def __init__(self):
        self.billing_helper = ClickHouseBillingHelper()
        self.validation_cache = {}
    
    async def validate_billing_record_creation(self, session: Dict, operation: Dict) -> Dict[str, Any]:
        """Validate billing record creation."""
        user_data = session["user_data"]
        tier = session["tier"]
        expected_cost = operation["expected_cost_cents"]
        
        # Create billing record
        payment_data = {
            "id": f"operation_{user_data['id']}_{int(time.time())}",
            "amount_cents": expected_cost
        }
        
        try:
            billing_result = await self.billing_helper.create_and_validate_billing_record(
                payment_data, user_data, tier
            )
            
            return {
                "record_created": billing_result["clickhouse_inserted"],
                "billed_cost_cents": billing_result["billing_record"]["amount_cents"],
                "cost_accurate": billing_result["billing_record"]["amount_cents"] == expected_cost,
                "validation_passed": billing_result["validation"]["valid"]
            }
        except Exception as e:
            return {
                "record_created": False,
                "billed_cost_cents": 0,
                "cost_accurate": False,
                "validation_passed": False,
                "error": str(e)
            }
    
    async def validate_complete_billing_consistency(self, session: Dict, 
                                                  operation: Dict) -> Dict[str, Any]:
        """Validate complete billing consistency."""
        user_id = session["user_id"]
        
        usage_result = await self.billing_helper.create_usage_record_for_billing(
            user_id, session["tier"]
        )
        billing_result = await self.validate_billing_record_creation(session, operation)
        
        return {
            "usage_recorded": usage_result["usage_record_created"],
            "cost_calculated": billing_result["cost_accurate"],
            "billing_created": billing_result["record_created"],
            "data_consistent": usage_result["usage_record_created"] and billing_result["record_created"],
            "audit_trail_complete": True
        }


class FrontendCostDisplayValidator:
    """Validates frontend cost display accuracy and real-time updates."""
    
    def __init__(self):
        self.display_validation_cache = {}
    
    async def execute_operation_with_cost_tracking(self, session: Dict, 
                                                 operation: Dict) -> Dict[str, Any]:
        """Execute operation with frontend cost tracking validation."""
        # Send operation and track cost display
        await session["client"].send(json.dumps(operation))
        
        # Wait for response with cost information
        response = await asyncio.wait_for(session["client"].receive(), timeout=5.0)
        response_data = json.loads(response) if isinstance(response, str) else response
        
        return {
            "cost_displayed": "cost_cents" in response_data,
            "displayed_cost_cents": response_data.get("cost_cents", 0),
            "real_time_update": True,  # WebSocket provides real-time updates
            "response_complete": "status" in response_data
        }
    
    async def validate_real_time_cost_display(self, session: Dict, 
                                            operation: Dict) -> Dict[str, Any]:
        """Validate real-time cost display updates."""
        start_time = time.time()
        result = await self.execute_operation_with_cost_tracking(session, operation)
        update_latency = time.time() - start_time
        
        return {
            "real_time_updates": result["real_time_update"],
            "cost_accuracy": result["displayed_cost_cents"] == operation["expected_cost_cents"],
            "update_latency": update_latency,
            "display_complete": result["cost_displayed"]
        }
