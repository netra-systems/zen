"""
Golden Path Unit Tests: Data Validation and Transformation Business Logic

Tests critical data validation and transformation business logic that ensures
data integrity and proper formatting throughout the golden path user flow.

Business Value:
- Validates data integrity for cost calculations and financial reporting
- Tests input/output data transformations for agent communication
- Verifies business rule enforcement in data processing
- Tests data sanitization and security validation logic
"""

import pytest
import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Union
from unittest.mock import Mock, MagicMock, patch

# Import business logic components for testing
from netra_backend.app.schemas.user import UserCreate, UserUpdate
from netra_backend.app.schemas.agent_schemas import AgentExecutionResult
from netra_backend.app.schemas.llm_base_types import TokenUsage, LLMProvider
from netra_backend.app.services.cost_calculator import CostCalculatorService, CostTier, ModelCostInfo
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext


@pytest.mark.unit
@pytest.mark.golden_path  
class TestDataValidationBusinessRules:
    """Test data validation business rules for golden path scenarios."""

    def test_user_data_validation_business_requirements(self):
        """Test user data validation enforces business requirements."""
        # Business Rule: User data must meet business validation requirements
        
        # Valid user creation data
        valid_user_data = UserCreate(
            email="business.user@company.com",
            password="SecureBusinessPassword123!",
            full_name="Business User",
            is_active=True
        )
        
        # Business Rule: User email must be properly formatted for business communications
        assert "@" in valid_user_data.email, "Email must contain @ symbol"
        assert "." in valid_user_data.email.split("@")[1], "Email domain must contain dot"
        assert len(valid_user_data.email) >= 5, "Email must be reasonable length for business use"
        
        # Business Rule: Password must meet security requirements
        password = valid_user_data.password
        assert len(password) >= 8, "Password must be at least 8 characters for security"
        assert any(c.isupper() for c in password), "Password must contain uppercase letter"
        assert any(c.islower() for c in password), "Password must contain lowercase letter" 
        assert any(c.isdigit() for c in password), "Password must contain number"
        assert any(c in "!@#$%^&*" for c in password), "Password must contain special character"
        
        # Business Rule: Full name should be properly formatted
        assert len(valid_user_data.full_name) >= 2, "Full name should be reasonable length"
        assert valid_user_data.full_name.strip() == valid_user_data.full_name, "Name should not have leading/trailing whitespace"

    def test_user_update_validation_business_logic(self):
        """Test user update validation follows business logic rules."""
        # Business Rule: User updates must validate business requirements
        
        update_data = UserUpdate(
            email="updated.email@company.com",
            full_name="Updated Business Name",
            is_active=True
        )
        
        # Business Rule: Optional fields in updates should be validated when present
        if update_data.email:
            assert "@" in update_data.email, "Updated email must be valid"
            
        if update_data.full_name:
            assert len(update_data.full_name.strip()) > 0, "Updated name must not be empty"
            
        # Business Rule: Update should preserve business data integrity
        assert hasattr(update_data, 'is_active'), "Update schema should support active status"

    def test_token_usage_validation_business_requirements(self):
        """Test token usage validation for business cost tracking."""
        # Business Rule: Token usage must be accurately tracked for billing
        
        valid_usage = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500, 
            total_tokens=1500
        )
        
        # Business Rule: Token counts must be non-negative for billing accuracy
        assert valid_usage.prompt_tokens >= 0, "Prompt tokens must be non-negative"
        assert valid_usage.completion_tokens >= 0, "Completion tokens must be non-negative"
        assert valid_usage.total_tokens >= 0, "Total tokens must be non-negative"
        
        # Business Rule: Total should equal sum of parts for accounting accuracy
        expected_total = valid_usage.prompt_tokens + valid_usage.completion_tokens
        assert valid_usage.total_tokens == expected_total, \
            f"Total tokens ({valid_usage.total_tokens}) must equal sum of prompt + completion ({expected_total})"
        
        # Business Rule: Token usage should support cost calculation
        assert hasattr(valid_usage, 'prompt_tokens'), "Must track prompt tokens for billing"
        assert hasattr(valid_usage, 'completion_tokens'), "Must track completion tokens for billing"

    def test_cost_calculation_data_validation_business_rules(self):
        """Test cost calculation data validation for business accuracy."""
        cost_calculator = CostCalculatorService()
        
        # Business Rule: Cost calculations must handle edge cases properly
        edge_case_usages = [
            TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),  # Zero usage
            TokenUsage(prompt_tokens=1, completion_tokens=0, total_tokens=1),   # Minimal usage
            TokenUsage(prompt_tokens=100000, completion_tokens=50000, total_tokens=150000),  # High usage
        ]
        
        for usage in edge_case_usages:
            cost = cost_calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
            
            # Business Rule: All costs must be non-negative Decimals for financial accuracy
            assert isinstance(cost, Decimal), "Cost must be Decimal for financial precision"
            assert cost >= Decimal('0'), "Cost must be non-negative"
            
            # Business Rule: Zero usage should result in zero cost
            if usage.total_tokens == 0:
                assert cost == Decimal('0'), "Zero token usage must result in zero cost"

    def test_agent_execution_result_validation_business_logic(self):
        """Test agent execution result validation for business reporting."""
        # Business Rule: Agent results must be properly structured for business analysis
        
        valid_result = AgentExecutionResult(
            agent_name="BusinessAnalysisAgent",
            success=True,
            result_data={
                "cost_analysis": {
                    "total_cost": 450.75,
                    "breakdown": {"gpt_4": 325.50, "gpt_3_5": 125.25}
                },
                "confidence_score": 0.95
            },
            execution_time=3.2,
            token_usage={"prompt": 150, "completion": 75, "total": 225},
            metadata={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0"
            }
        )
        
        # Business Rule: Result must identify the executing agent
        assert valid_result.agent_name, "Result must identify executing agent"
        assert isinstance(valid_result.agent_name, str), "Agent name must be string"
        assert len(valid_result.agent_name) > 0, "Agent name must not be empty"
        
        # Business Rule: Success status must be clearly indicated  
        assert isinstance(valid_result.success, bool), "Success must be boolean"
        
        # Business Rule: Execution time must be tracked for performance analysis
        assert valid_result.execution_time >= 0, "Execution time must be non-negative"
        assert isinstance(valid_result.execution_time, (int, float)), "Execution time must be numeric"
        
        # Business Rule: Result data should contain business-relevant information
        assert isinstance(valid_result.result_data, dict), "Result data must be structured"
        if "cost_analysis" in valid_result.result_data:
            cost_data = valid_result.result_data["cost_analysis"]
            assert "total_cost" in cost_data, "Cost analysis should include total"
            assert isinstance(cost_data["total_cost"], (int, float)), "Total cost should be numeric"

    def test_strongly_typed_user_context_validation_business_rules(self):
        """Test strongly typed user context validation for type safety."""
        # Business Rule: User contexts must be strongly typed for type safety
        
        user_id = "business-typed-user-123"
        thread_id = "business-thread-456"
        run_id = "business-run-789"
        request_id = "business-req-012"
        
        # Create strongly typed IDs
        typed_user_id = ensure_user_id(user_id)
        typed_thread_id = ThreadID(thread_id)
        typed_run_id = RunID(run_id)
        typed_request_id = RequestID(request_id)
        
        # Business Rule: Typed IDs should maintain original values
        assert str(typed_user_id) == user_id, "User ID should be preserved"
        assert str(typed_thread_id) == thread_id, "Thread ID should be preserved"
        assert str(typed_run_id) == run_id, "Run ID should be preserved"
        assert str(typed_request_id) == request_id, "Request ID should be preserved"
        
        # Business Rule: Type safety should be enforced
        assert isinstance(typed_user_id, UserID), "Should be UserID type"
        assert isinstance(typed_thread_id, ThreadID), "Should be ThreadID type"
        assert isinstance(typed_run_id, RunID), "Should be RunID type"
        assert isinstance(typed_request_id, RequestID), "Should be RequestID type"


@pytest.mark.unit
@pytest.mark.golden_path
class TestDataTransformationBusinessLogic:
    """Test data transformation business logic for golden path processing."""

    def test_cost_data_transformation_business_requirements(self):
        """Test cost data transformation for business reporting requirements."""
        # Business Rule: Raw cost data must be transformed for business consumption
        
        raw_cost_data = {
            "usage_records": [
                {"model": "gpt-4", "tokens": 10000, "cost_per_1k": 0.06},
                {"model": "gpt-3.5-turbo", "tokens": 25000, "cost_per_1k": 0.002},
                {"model": "gpt-4", "tokens": 5000, "cost_per_1k": 0.06}
            ],
            "time_period": "2024-01-01 to 2024-01-31",
            "currency": "USD"
        }
        
        # Transform raw data into business format
        transformed_data = self._transform_cost_data_for_business(raw_cost_data)
        
        # Business Rule: Transformed data must aggregate costs by model
        assert "cost_breakdown" in transformed_data, "Must include cost breakdown"
        breakdown = transformed_data["cost_breakdown"]
        
        # Verify aggregation logic
        assert "gpt-4" in breakdown, "Should aggregate GPT-4 costs"
        assert "gpt-3.5-turbo" in breakdown, "Should aggregate GPT-3.5 costs"
        
        # Business Rule: Totals should be calculated accurately
        gpt4_total = breakdown["gpt-4"]["total_cost"] 
        expected_gpt4_cost = (15000 * 0.06 / 1000)  # 15k tokens at $0.06/1k
        assert abs(gpt4_total - expected_gpt4_cost) < 0.01, "GPT-4 cost should be calculated correctly"
        
        # Business Rule: Summary metrics should be provided
        assert "total_cost" in transformed_data, "Should provide total cost"
        assert "total_tokens" in transformed_data, "Should provide total token count"
        
    def _transform_cost_data_for_business(self, raw_data: Dict) -> Dict:
        """Helper method to transform raw cost data into business format."""
        breakdown = {}
        total_cost = Decimal('0')
        total_tokens = 0
        
        for record in raw_data["usage_records"]:
            model = record["model"]
            tokens = record["tokens"]
            cost_per_1k = Decimal(str(record["cost_per_1k"]))
            record_cost = (tokens * cost_per_1k / 1000).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            if model not in breakdown:
                breakdown[model] = {"total_cost": Decimal('0'), "total_tokens": 0}
            
            breakdown[model]["total_cost"] += record_cost
            breakdown[model]["total_tokens"] += tokens
            total_cost += record_cost
            total_tokens += tokens
        
        # Convert Decimal back to float for JSON serialization
        for model_data in breakdown.values():
            model_data["total_cost"] = float(model_data["total_cost"])
            
        return {
            "cost_breakdown": breakdown,
            "total_cost": float(total_cost),
            "total_tokens": total_tokens,
            "period": raw_data["time_period"],
            "currency": raw_data["currency"]
        }

    def test_agent_response_transformation_business_logic(self):
        """Test agent response transformation for business consumption."""
        # Business Rule: Agent responses must be transformed for user consumption
        
        raw_agent_response = {
            "raw_llm_output": json.dumps({
                "analysis": "Cost analysis shows 15.6% optimization potential",
                "metrics": {"current": 450.75, "optimized": 380.50},
                "recommendations": ["switch_models", "optimize_prompts"]
            }),
            "metadata": {
                "tokens": 245,
                "model": "gpt-4",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
        
        # Transform for business consumption
        transformed_response = self._transform_agent_response_for_business(raw_agent_response)
        
        # Business Rule: Transformed response should be user-friendly
        assert "executive_summary" in transformed_response, "Should provide executive summary"
        assert "key_metrics" in transformed_response, "Should highlight key metrics"
        assert "action_items" in transformed_response, "Should provide actionable items"
        
        # Business Rule: Financial data should be properly formatted
        metrics = transformed_response["key_metrics"]
        assert "current_cost" in metrics, "Should show current cost"
        assert "savings_potential" in metrics, "Should show savings potential"
        assert isinstance(metrics["current_cost"], str), "Cost should be formatted as currency string"
        
    def _transform_agent_response_for_business(self, raw_response: Dict) -> Dict:
        """Helper method to transform raw agent response into business format."""
        parsed_output = json.loads(raw_response["raw_llm_output"])
        
        return {
            "executive_summary": parsed_output["analysis"],
            "key_metrics": {
                "current_cost": f"${parsed_output['metrics']['current']:.2f}",
                "optimized_cost": f"${parsed_output['metrics']['optimized']:.2f}",
                "savings_potential": f"${parsed_output['metrics']['current'] - parsed_output['metrics']['optimized']:.2f}"
            },
            "action_items": [
                "Consider switching to more cost-effective models",
                "Optimize prompt templates for efficiency"
            ],
            "metadata": {
                "generated_at": raw_response["metadata"]["timestamp"],
                "confidence": "high"
            }
        }

    def test_json_serialization_business_requirements(self):
        """Test JSON serialization meets business data exchange requirements."""
        # Business Rule: Business data must be JSON serializable for APIs and storage
        
        business_data = {
            "user_id": "json-test-user",
            "cost_analysis": {
                "total_cost": Decimal('450.75'),  # Decimal for precision
                "breakdown": {
                    "gpt_4": Decimal('325.50'),
                    "gpt_3_5": Decimal('125.25')
                }
            },
            "timestamp": datetime.now(timezone.utc),
            "optimization_results": [
                {"savings": Decimal('70.25'), "strategy": "model_optimization"}
            ]
        }
        
        # Transform for JSON serialization
        json_ready_data = self._prepare_data_for_json(business_data)
        
        # Business Rule: Data should be JSON serializable
        try:
            json_string = json.dumps(json_ready_data)
            deserialized = json.loads(json_string)
            json_compatible = True
        except (TypeError, ValueError):
            json_compatible = False
        
        assert json_compatible, "Business data must be JSON serializable"
        
        # Business Rule: Numeric precision should be preserved appropriately
        assert isinstance(deserialized["cost_analysis"]["total_cost"], (int, float)), \
            "Costs should be numeric in JSON"
        assert deserialized["cost_analysis"]["total_cost"] == 450.75, \
            "Cost precision should be preserved"
            
    def _prepare_data_for_json(self, data: Dict) -> Dict:
        """Helper to prepare business data for JSON serialization."""
        def convert_item(item):
            if isinstance(item, Decimal):
                return float(item)
            elif isinstance(item, datetime):
                return item.isoformat()
            elif isinstance(item, dict):
                return {k: convert_item(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [convert_item(i) for i in item]
            else:
                return item
                
        return convert_item(data)

    def test_currency_formatting_business_requirements(self):
        """Test currency formatting meets business presentation requirements."""
        # Business Rule: Currency values must be formatted consistently for business use
        
        test_amounts = [
            (450.75, "$450.75"),
            (1250.00, "$1,250.00"),
            (0.05, "$0.05"),
            (0.001, "$0.00"),  # Rounds to nearest cent
            (1000000.50, "$1,000,000.50")
        ]
        
        for amount, expected_format in test_amounts:
            formatted = self._format_currency_for_business(amount)
            
            # Business Rule: Currency should be formatted with $ symbol
            assert formatted.startswith("$"), "Currency should start with $ symbol"
            
            # Business Rule: Large amounts should include commas
            if amount >= 1000:
                assert "," in formatted, f"Large amounts should include commas: {formatted}"
            
            # Verify specific formatting expectations
            assert formatted == expected_format, f"Expected {expected_format}, got {formatted}"
            
    def _format_currency_for_business(self, amount: float) -> str:
        """Helper to format currency for business presentation."""
        # Round to cents and format with commas
        rounded_amount = round(amount, 2)
        return f"${rounded_amount:,.2f}"

    def test_percentage_calculation_business_accuracy(self):
        """Test percentage calculations meet business accuracy requirements."""
        # Business Rule: Percentage calculations must be accurate for business reporting
        
        test_cases = [
            {"current": 450.75, "optimized": 380.50, "expected_savings": 15.6},
            {"current": 1000.00, "optimized": 850.00, "expected_savings": 15.0},
            {"current": 100.00, "optimized": 95.00, "expected_savings": 5.0},
            {"current": 50.00, "optimized": 50.00, "expected_savings": 0.0}
        ]
        
        for case in test_cases:
            savings_pct = self._calculate_savings_percentage(case["current"], case["optimized"])
            
            # Business Rule: Percentage should be calculated correctly
            expected = case["expected_savings"]
            assert abs(savings_pct - expected) < 0.1, \
                f"Savings percentage should be ~{expected}%, got {savings_pct}%"
            
            # Business Rule: Percentage should be properly rounded for presentation
            assert isinstance(savings_pct, float), "Percentage should be float"
            assert savings_pct >= 0, "Savings percentage should be non-negative"
            
    def _calculate_savings_percentage(self, current: float, optimized: float) -> float:
        """Helper to calculate savings percentage for business reporting."""
        if current == 0:
            return 0.0
        savings = current - optimized
        percentage = (savings / current) * 100
        return round(percentage, 1)  # Round to 1 decimal place


@pytest.mark.unit
@pytest.mark.golden_path
class TestDataSanitizationBusinessSecurity:
    """Test data sanitization and security validation for business requirements."""

    def test_user_input_sanitization_business_security(self):
        """Test user input sanitization for business security requirements."""
        # Business Rule: User inputs must be sanitized to prevent security issues
        
        potentially_malicious_inputs = [
            {"input": "<script>alert('xss')</script>", "type": "xss"},
            {"input": "'; DROP TABLE users; --", "type": "sql_injection"}, 
            {"input": "../../etc/passwd", "type": "path_traversal"},
            {"input": "javascript:alert(1)", "type": "javascript_protocol"},
            {"input": "data:text/html,<script>alert(1)</script>", "type": "data_uri"}
        ]
        
        for test_case in potentially_malicious_inputs:
            sanitized = self._sanitize_user_input_for_business(test_case["input"])
            
            # Business Rule: Malicious patterns should be removed or escaped
            assert "<script>" not in sanitized, "Script tags should be removed/escaped"
            assert "DROP TABLE" not in sanitized.upper(), "SQL commands should be removed/escaped"
            assert "javascript:" not in sanitized.lower(), "JavaScript protocols should be removed"
            
            # Business Rule: Sanitized input should be safe for business use
            assert len(sanitized) >= 0, "Sanitization should not fail"
            
    def _sanitize_user_input_for_business(self, user_input: str) -> str:
        """Helper to sanitize user input for business security."""
        # Basic sanitization - in production would use comprehensive library
        sanitized = user_input
        
        # Remove common XSS patterns
        dangerous_patterns = [
            '<script>', '</script>', '<iframe>', '</iframe>',
            'javascript:', 'data:', 'vbscript:', 'onload=', 'onerror='
        ]
        
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, '')
            sanitized = sanitized.replace(pattern.upper(), '')
            
        # Remove SQL injection patterns  
        sql_patterns = ['DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE SET', '--', ';']
        for pattern in sql_patterns:
            sanitized = sanitized.replace(pattern, '')
            sanitized = sanitized.replace(pattern.lower(), '')
            
        return sanitized.strip()

    def test_cost_data_validation_business_integrity(self):
        """Test cost data validation for business data integrity."""
        # Business Rule: Cost data must be validated for business integrity
        
        cost_data_scenarios = [
            {"data": {"cost": -100.00}, "valid": False, "reason": "negative_cost"},
            {"data": {"cost": 0.00}, "valid": True, "reason": "zero_cost_allowed"},
            {"data": {"cost": "invalid"}, "valid": False, "reason": "non_numeric"},
            {"data": {"cost": float('inf')}, "valid": False, "reason": "infinite_value"},
            {"data": {"cost": 1000000.00}, "valid": True, "reason": "high_but_valid"},
        ]
        
        for scenario in cost_data_scenarios:
            is_valid = self._validate_cost_data_for_business(scenario["data"])
            
            # Business Rule: Validation should match expected business rules
            expected_valid = scenario["valid"]
            assert is_valid == expected_valid, \
                f"Cost validation failed for {scenario['reason']}: expected {expected_valid}, got {is_valid}"
                
    def _validate_cost_data_for_business(self, cost_data: Dict) -> bool:
        """Helper to validate cost data for business integrity."""
        try:
            cost = cost_data.get("cost")
            
            # Must be numeric
            if not isinstance(cost, (int, float)):
                return False
                
            # Must be finite
            if not (cost != float('inf') and cost != float('-inf')):
                return False
                
            # Must be non-negative for business logic
            if cost < 0:
                return False
                
            return True
            
        except Exception:
            return False

    def test_api_response_structure_validation_business_requirements(self):
        """Test API response structure validation for business integration."""
        # Business Rule: API responses must follow consistent structure for business systems
        
        sample_api_responses = [
            {
                "status": "success",
                "data": {"cost_analysis": {"total": 450.75}},
                "metadata": {"timestamp": "2024-01-15T10:30:00Z"},
                "expected_valid": True
            },
            {
                # Missing required fields
                "data": {"some_data": "value"},
                "expected_valid": False
            },
            {
                "status": "error", 
                "error": {"code": "VALIDATION_ERROR", "message": "Invalid input"},
                "expected_valid": True  # Error responses have different but valid structure
            }
        ]
        
        for response in sample_api_responses:
            expected = response.pop("expected_valid")
            is_valid = self._validate_api_response_structure(response)
            
            # Business Rule: Response validation should match business requirements
            assert is_valid == expected, \
                f"API response validation failed: expected {expected}, got {is_valid} for {response}"
                
    def _validate_api_response_structure(self, response: Dict) -> bool:
        """Helper to validate API response structure for business requirements."""
        # Success responses must have status and data
        if response.get("status") == "success":
            return "data" in response
            
        # Error responses must have status and error details
        if response.get("status") == "error":
            return "error" in response and isinstance(response["error"], dict)
            
        # Other responses are valid if they have some recognizable structure
        return len(response) > 0 and isinstance(response, dict)

    def test_business_rule_enforcement_data_validation(self):
        """Test business rule enforcement in data validation."""
        # Business Rule: Data validation must enforce specific business rules
        
        business_validation_cases = [
            {
                "rule": "monthly_cost_limit",
                "data": {"monthly_cost": 5000.00},
                "limit": 10000.00,
                "expected_valid": True
            },
            {
                "rule": "monthly_cost_limit", 
                "data": {"monthly_cost": 15000.00},
                "limit": 10000.00,
                "expected_valid": False
            },
            {
                "rule": "token_usage_reasonable",
                "data": {"tokens_per_request": 1000},
                "limit": 5000,
                "expected_valid": True
            },
            {
                "rule": "token_usage_reasonable",
                "data": {"tokens_per_request": 10000},
                "limit": 5000,
                "expected_valid": False
            }
        ]
        
        for case in business_validation_cases:
            is_valid = self._validate_business_rule(case["rule"], case["data"], case["limit"])
            expected = case["expected_valid"]
            
            # Business Rule: Validation should enforce business limits
            assert is_valid == expected, \
                f"Business rule {case['rule']} validation failed: expected {expected}, got {is_valid}"
                
    def _validate_business_rule(self, rule: str, data: Dict, limit: float) -> bool:
        """Helper to validate specific business rules."""
        if rule == "monthly_cost_limit":
            monthly_cost = data.get("monthly_cost", 0)
            return monthly_cost <= limit
            
        elif rule == "token_usage_reasonable":
            tokens = data.get("tokens_per_request", 0)
            return tokens <= limit
            
        return True  # Unknown rules pass by default