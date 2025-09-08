"""
ClickHouse Billing Integration Helper - E2E Billing Record Testing

DEPRECATED: This file uses mocks which are FORBIDDEN per CLAUDE.md.
Use real service implementations in test_agent_billing_flow_simplified.py instead.

CLAUDE.md states: "MOCKS are FORBIDDEN in e2e tests" and "mocks = abomination"
All e2e tests must use real services for business value validation.

BVJ (Business Value Justification):
1. Segment: ALL paid tiers (revenue tracking critical)  
2. Business Goal: Ensure accurate usage-based billing for agent operations
3. Value Impact: Protects revenue integrity - billing errors = customer trust loss
4. Revenue Impact: Each billing error costs $100-1000/month per customer

MIGRATION: Use RealAgentBillingTestCore in test_agent_billing_flow_simplified.py
"""
import time
import uuid
from typing import Any, Dict, List, Optional

from netra_backend.app.schemas.user_plan import PlanTier
# Import IsolatedEnvironment per CLAUDE.md requirements - SSOT unified access
from test_framework.environment_isolation import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


class MockClickHouseBillingClient:
    """Mock ClickHouse client for billing record testing."""
    
    def __init__(self):
        self.billing_records = {}
        self.usage_records = {}
        self.connected = False
    
    async def connect(self) -> bool:
        """Simulate ClickHouse connection."""
        self.connected = True
        return True
    
    async def disconnect(self) -> None:
        """Simulate ClickHouse disconnection."""
        self.connected = False
    
    async def insert_billing_record(self, record: Dict[str, Any]) -> bool:
        """Insert billing record into mock ClickHouse."""
        if not self.connected:
            raise ConnectionError("ClickHouse not connected")
        
        record_id = record.get("id", str(uuid.uuid4()))
        record["inserted_at"] = time.time()
        self.billing_records[record_id] = record
        return True
    
    async def query_user_billing(self, user_id: str, 
                               start_date: Optional[float] = None) -> List[Dict]:
        """Query billing records for a user."""
        if not self.connected:
            raise ConnectionError("ClickHouse not connected")
        
        user_records = []
        for record in self.billing_records.values():
            if record["user_id"] == user_id:
                if start_date is None or record["created_at"] >= start_date:
                    user_records.append(record)
        
        return sorted(user_records, key=lambda x: x["created_at"], reverse=True)
    
    async def insert_usage_record(self, record: Dict[str, Any]) -> bool:
        """Insert usage record for billing analytics."""
        if not self.connected:
            raise ConnectionError("ClickHouse not connected")
        
        record_id = str(uuid.uuid4())
        record["id"] = record_id
        record["inserted_at"] = time.time()
        self.usage_records[record_id] = record
        return True
    
    def get_total_records(self) -> Dict[str, int]:
        """Get record counts for validation."""
        return {
            "billing_records": len(self.billing_records),
            "usage_records": len(self.usage_records)
        }


class BillingRecordValidator:
    """Validates billing record integrity and completeness."""
    
    def __init__(self):
        self.required_fields = [
            "id", "user_id", "payment_id", "amount_cents", 
            "tier", "status", "created_at"
        ]
        self.validation_results = {}
    
    def validate_billing_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate billing record structure and data integrity."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        for field in self.required_fields:
            if field not in record:
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["valid"] = False
        
        # Validate data types and values
        if "amount_cents" in record:
            if not isinstance(record["amount_cents"], int) or record["amount_cents"] < 0:
                validation_result["errors"].append("amount_cents must be positive integer")
                validation_result["valid"] = False
        
        # Validate tier
        if "tier" in record:
            valid_tiers = [tier.value for tier in PlanTier]
            if record["tier"] not in valid_tiers:
                validation_result["errors"].append(f"Invalid tier: {record['tier']}")
                validation_result["valid"] = False
        
        # Validate status
        if "status" in record:
            valid_statuses = ["pending", "completed", "failed", "refunded"]
            if record["status"] not in valid_statuses:
                validation_result["errors"].append(f"Invalid status: {record['status']}")
                validation_result["valid"] = False
        
        return validation_result
    
    def validate_payment_billing_consistency(self, payment_data: Dict, 
                                           billing_record: Dict) -> Dict[str, Any]:
        """Validate consistency between payment and billing data."""
        consistency_result = {
            "consistent": True,
            "mismatches": []
        }
        
        # Check amount consistency
        payment_amount = payment_data.get("amount_cents", payment_data.get("amount", 0))
        billing_amount = billing_record.get("amount_cents")
        if payment_amount != billing_amount:
            consistency_result["mismatches"].append(
                f"Amount mismatch: payment={payment_amount}, "
                f"billing={billing_amount}"
            )
            consistency_result["consistent"] = False
        
        # Check payment ID consistency
        if payment_data.get("id") != billing_record.get("payment_id"):
            consistency_result["mismatches"].append(
                f"Payment ID mismatch: payment={payment_data.get('id')}, "
                f"billing={billing_record.get('payment_id')}"
            )
            consistency_result["consistent"] = False
        
        return consistency_result


class ClickHouseBillingHelper:
    """Helper for ClickHouse billing integration testing."""
    
    def __init__(self):
        self.client = MockClickHouseBillingClient()
        self.validator = BillingRecordValidator()
        self.test_session_records = []
    
    async def setup_billing_environment(self) -> None:
        """Setup billing test environment."""
        await self.client.connect()
        self.test_session_records.clear()
    
    async def teardown_billing_environment(self) -> None:
        """Cleanup billing test environment."""
        await self.client.disconnect()
        self.test_session_records.clear()
    
    async def create_and_validate_billing_record(self, payment_data: Dict, 
                                                user_data: Dict, 
                                                tier: PlanTier) -> Dict[str, Any]:
        """Create billing record and validate its integrity."""
        # Ensure ClickHouse is connected
        if not self.client.connected:
            await self.client.connect()
            
        # Create billing record
        billing_record = {
            "id": str(uuid.uuid4()),
            "user_id": user_data["id"],
            "payment_id": payment_data["id"],
            "amount_cents": payment_data.get("amount_cents", payment_data.get("amount", 0)),
            "tier": tier.value,
            "status": "completed",
            "created_at": time.time(),
            "billing_period_start": time.time(),
            "billing_period_end": time.time() + (30 * 24 * 3600),  # 30 days
            "payment_method": "test_card",
            "currency": "USD"
        }
        
        # Validate record structure
        validation_result = self.validator.validate_billing_record(billing_record)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid billing record: {validation_result['errors']}")
        
        # Validate payment-billing consistency
        consistency_result = self.validator.validate_payment_billing_consistency(
            payment_data, billing_record
        )
        if not consistency_result["consistent"]:
            raise ValueError(f"Payment-billing inconsistency: {consistency_result['mismatches']}")
        
        # Insert into ClickHouse
        await self.client.insert_billing_record(billing_record)
        self.test_session_records.append(billing_record["id"])
        
        return {
            "billing_record": billing_record,
            "validation": validation_result,
            "consistency": consistency_result,
            "clickhouse_inserted": True
        }
    
    async def verify_billing_record_retrieval(self, user_id: str) -> Dict[str, Any]:
        """Verify billing records can be retrieved correctly."""
        # Ensure ClickHouse is connected
        if not self.client.connected:
            await self.client.connect()
            
        # Query billing records
        records = await self.client.query_user_billing(user_id)
        
        # Verify records exist
        if not records:
            return {"retrieved": False, "error": "No billing records found"}
        
        # Verify record integrity
        for record in records:
            validation = self.validator.validate_billing_record(record)
            if not validation["valid"]:
                return {
                    "retrieved": True,
                    "integrity_valid": False,
                    "errors": validation["errors"]
                }
        
        return {
            "retrieved": True,
            "record_count": len(records),
            "integrity_valid": True,
            "latest_record": records[0] if records else None
        }
    
    async def create_usage_record_for_billing(self, user_id: str, 
                                            tier: PlanTier) -> Dict[str, Any]:
        """Create usage record for billing analytics."""
        # Ensure ClickHouse is connected
        if not self.client.connected:
            await self.client.connect()
            
        usage_record = {
            "user_id": user_id,
            "tool_name": "test_agent_execution",
            "category": "ai_optimization",
            "execution_time_ms": 1500,
            "tokens_used": 1000,
            "cost_cents": 15,
            "status": "completed",
            "plan_tier": tier.value,
            "created_at": time.time()
        }
        
        # Insert usage record
        await self.client.insert_usage_record(usage_record)
        
        return {
            "usage_record_created": True,
            "record": usage_record
        }
    
    def get_test_session_summary(self) -> Dict[str, Any]:
        """Get summary of test session billing activity."""
        total_records = self.client.get_total_records()
        
        return {
            "session_billing_records": len(self.test_session_records),
            "total_billing_records": total_records["billing_records"],
            "total_usage_records": total_records["usage_records"],
            "clickhouse_connected": self.client.connected
        }