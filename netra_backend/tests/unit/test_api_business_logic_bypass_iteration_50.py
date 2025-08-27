import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timedelta
from netra_backend.app.core.business_logic_validator import BusinessLogicValidator
from netra_backend.app.core.workflow_enforcer import WorkflowEnforcer
from netra_backend.app.core.constraint_validator import ConstraintValidator


class TestAPIBusinessLogicBypass:
    """Test API business logic bypass prevention - Iteration 50
    
    Business Value: Prevents $175K/month losses from business logic exploitation
    Protects against workflow manipulation and constraint bypass
    """

    @pytest.fixture
    def business_validator(self):
        return BusinessLogicValidator()

    @pytest.fixture
    def workflow_enforcer(self):
        return WorkflowEnforcer()

    @pytest.fixture
    def constraint_validator(self):
        return ConstraintValidator()

    @pytest.mark.asyncio
    async def test_financial_transaction_limits_enforcement(self, business_validator):
        """Test enforcement of financial transaction limits"""
        user_account = {
            "user_id": 123,
            "account_type": "standard",
            "daily_limit": Decimal("10000.00"),
            "current_daily_usage": Decimal("8500.00")
        }
        
        # Transaction within remaining limit should succeed
        valid_transaction = {
            "amount": Decimal("1000.00"),
            "type": "transfer",
            "timestamp": datetime.now()
        }
        
        validation_result = await business_validator.validate_transaction_limits(
            user_account, valid_transaction
        )
        assert validation_result["valid"] is True
        
        # Transaction exceeding limit should be blocked
        excessive_transaction = {
            "amount": Decimal("2000.00"),  # Would exceed daily limit
            "type": "transfer",
            "timestamp": datetime.now()
        }
        
        with pytest.raises(ValueError, match="Daily transaction limit exceeded"):
            await business_validator.validate_transaction_limits(
                user_account, excessive_transaction
            )

    @pytest.mark.asyncio
    async def test_workflow_state_manipulation_prevention(self, workflow_enforcer):
        """Test prevention of workflow state manipulation"""
        loan_application = {
            "application_id": "LOAN123",
            "current_state": "pending_review",
            "applicant_id": 456,
            "amount": Decimal("50000.00")
        }
        
        # Valid state transition should succeed
        valid_transition = await workflow_enforcer.transition_state(
            loan_application, 
            from_state="pending_review",
            to_state="under_review",
            actor_role="loan_officer"
        )
        assert valid_transition["success"] is True
        
        # Invalid state skip should be prevented
        with pytest.raises(ValueError, match="Invalid state transition"):
            await workflow_enforcer.transition_state(
                loan_application,
                from_state="pending_review",
                to_state="approved",  # Skipping intermediate states
                actor_role="customer"
            )

    @pytest.mark.asyncio
    async def test_price_manipulation_prevention(self, business_validator):
        """Test prevention of price manipulation attacks"""
        product = {
            "product_id": "PROD789",
            "base_price": Decimal("100.00"),
            "discount_rules": {
                "max_discount_percent": 20,
                "bulk_threshold": 10,
                "bulk_discount_percent": 15
            }
        }
        
        # Valid discount should be accepted
        valid_order = {
            "product_id": "PROD789",
            "quantity": 5,
            "requested_price": Decimal("85.00"),  # 15% discount
            "discount_code": "SAVE15"
        }
        
        price_validation = await business_validator.validate_pricing(
            product, valid_order
        )
        assert price_validation["valid"] is True
        
        # Excessive discount should be rejected
        manipulated_order = {
            "product_id": "PROD789",
            "quantity": 1,
            "requested_price": Decimal("10.00"),  # 90% discount (invalid)
            "discount_code": "HACKED50"
        }
        
        with pytest.raises(ValueError, match="Invalid discount amount"):
            await business_validator.validate_pricing(product, manipulated_order)

    @pytest.mark.asyncio
    async def test_inventory_constraint_bypass_prevention(self, constraint_validator):
        """Test prevention of inventory constraint bypass"""
        inventory_item = {
            "item_id": "ITEM456",
            "available_quantity": 5,
            "reserved_quantity": 2,
            "max_per_customer": 2
        }
        
        # Valid purchase should succeed
        valid_purchase = {
            "customer_id": 789,
            "item_id": "ITEM456",
            "requested_quantity": 2
        }
        
        constraint_check = await constraint_validator.validate_inventory_constraints(
            inventory_item, valid_purchase
        )
        assert constraint_check["valid"] is True
        
        # Over-purchase attempt should be blocked
        excessive_purchase = {
            "customer_id": 789,
            "item_id": "ITEM456",
            "requested_quantity": 10  # Exceeds available quantity
        }
        
        with pytest.raises(ValueError, match="Insufficient inventory"):
            await constraint_validator.validate_inventory_constraints(
                inventory_item, excessive_purchase
            )

    @pytest.mark.asyncio
    async def test_subscription_tier_privilege_enforcement(self, business_validator):
        """Test enforcement of subscription tier privileges"""
        user_subscription = {
            "user_id": 123,
            "tier": "basic",
            "features": ["feature_a", "feature_b"],
            "api_calls_limit": 1000,
            "current_api_calls": 950
        }
        
        # Basic tier accessing basic feature should succeed
        basic_access = await business_validator.validate_feature_access(
            user_subscription, "feature_a"
        )
        assert basic_access["allowed"] is True
        
        # Basic tier accessing premium feature should be blocked
        with pytest.raises(ValueError, match="Feature requires premium subscription"):
            await business_validator.validate_feature_access(
                user_subscription, "premium_feature_x"
            )
        
        # API limit near exhaustion should trigger warning
        api_validation = await business_validator.validate_api_usage(
            user_subscription
        )
        assert api_validation["warning"] == "approaching_limit"

    @pytest.mark.asyncio
    async def test_temporal_constraint_enforcement(self, constraint_validator):
        """Test enforcement of temporal business constraints"""
        promotion = {
            "promo_id": "BLACK_FRIDAY",
            "start_date": datetime(2024, 11, 29, 0, 0, 0),
            "end_date": datetime(2024, 11, 30, 23, 59, 59),
            "max_uses": 1000,
            "current_uses": 850
        }
        
        # Valid time should allow promotion
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 11, 29, 12, 0, 0)
            
            temporal_validation = await constraint_validator.validate_temporal_constraints(
                promotion, "apply_promotion"
            )
            assert temporal_validation["valid"] is True
        
        # Outside promotion window should be blocked
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 12, 1, 0, 0, 0)
            
            with pytest.raises(ValueError, match="Promotion period has ended"):
                await constraint_validator.validate_temporal_constraints(
                    promotion, "apply_promotion"
                )

    @pytest.mark.asyncio
    async def test_multi_step_process_integrity(self, workflow_enforcer):
        """Test integrity of multi-step business processes"""
        order_process = {
            "order_id": "ORD789",
            "steps": [
                {"step": "validate_payment", "status": "completed"},
                {"step": "reserve_inventory", "status": "completed"},
                {"step": "process_shipment", "status": "pending"}
            ],
            "current_step": "process_shipment"
        }
        
        # Valid next step should succeed
        step_validation = await workflow_enforcer.validate_process_step(
            order_process, "process_shipment"
        )
        assert step_validation["valid"] is True
        
        # Skipping steps should be prevented
        with pytest.raises(ValueError, match="Prerequisites not met"):
            await workflow_enforcer.validate_process_step(
                order_process, "deliver_order"  # Skipping shipment processing
            )

    @pytest.mark.asyncio
    async def test_resource_allocation_limits(self, business_validator):
        """Test enforcement of resource allocation limits"""
        compute_resources = {
            "user_id": 456,
            "allocated_cpu": 4.0,  # cores
            "allocated_memory": 8.0,  # GB
            "max_cpu": 8.0,
            "max_memory": 16.0
        }
        
        # Valid resource request should succeed
        resource_request = {
            "additional_cpu": 2.0,
            "additional_memory": 4.0
        }
        
        allocation_validation = await business_validator.validate_resource_allocation(
            compute_resources, resource_request
        )
        assert allocation_validation["valid"] is True
        
        # Excessive resource request should be blocked
        excessive_request = {
            "additional_cpu": 10.0,  # Would exceed limit
            "additional_memory": 20.0  # Would exceed limit
        }
        
        with pytest.raises(ValueError, match="Resource allocation exceeds limits"):
            await business_validator.validate_resource_allocation(
                compute_resources, excessive_request
            )

    @pytest.mark.asyncio
    async def test_business_rule_consistency_validation(self, business_validator):
        """Test validation of business rule consistency"""
        conflicting_rules = {
            "rule_set_id": "PROMO_RULES_123",
            "rules": [
                {"rule_id": 1, "condition": "user_tier == 'premium'", "action": "apply_discount", "value": 20},
                {"rule_id": 2, "condition": "order_amount > 1000", "action": "apply_discount", "value": 15},
                {"rule_id": 3, "condition": "user_tier == 'premium' AND order_amount > 1000", "action": "apply_discount", "value": 10}  # Conflict!
            ]
        }
        
        user_context = {
            "user_id": 789,
            "user_tier": "premium",
            "order_amount": 1500
        }
        
        # Should detect conflicting rules and resolve appropriately
        rule_resolution = await business_validator.resolve_business_rules(
            conflicting_rules, user_context
        )
        
        assert "conflict_detected" in rule_resolution
        assert rule_resolution["applied_rule"]["value"] == 20  # Highest discount should win
        assert rule_resolution["resolution_strategy"] == "max_benefit_to_customer"

    @pytest.mark.asyncio
    async def test_audit_trail_integrity_for_critical_operations(self, workflow_enforcer):
        """Test audit trail integrity for critical business operations"""
        critical_operation = {
            "operation_id": "CRIT_OP_456",
            "operation_type": "financial_adjustment",
            "amount": Decimal("10000.00"),
            "initiator_id": 123,
            "requires_audit": True
        }
        
        # Critical operation should create immutable audit trail
        execution_result = await workflow_enforcer.execute_critical_operation(
            critical_operation
        )
        
        assert execution_result["executed"] is True
        assert "audit_hash" in execution_result
        assert execution_result["audit_trail_complete"] is True
        
        # Audit trail should be tamper-evident
        audit_verification = await workflow_enforcer.verify_audit_integrity(
            execution_result["operation_id"]
        )
        
        assert audit_verification["integrity_verified"] is True
        assert "hash_chain_valid" in audit_verification
        assert audit_verification["hash_chain_valid"] is True
