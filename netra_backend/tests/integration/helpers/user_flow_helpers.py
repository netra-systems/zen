"""
Shared utilities for user flow integration testing.
Extracted from test_first_time_user_flows_comprehensive.py to comply with size limits.
"""

# Test data generation
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import status
from netra_backend.app.websocket_core.manager import WebSocketManager as WebSocketManager
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
import asyncio
import httpx
import json
import time
import uuid

def generate_test_user_data() -> Dict[str, Any]:

    """Generate standardized test user data"""

    user_id = str(uuid.uuid4())

    timestamp = datetime.now(timezone.utc).isoformat()
    
    return {

        "user_id": user_id,

        "email": f"test_{user_id[:8]}@example.com",

        "username": f"testuser_{user_id[:8]}",

        "password": "TestPassword123!",

        "first_name": "Test",

        "last_name": "User",

        "plan": "free",

        "created_at": timestamp,

        "verified": False,

        "preferences": {

            "notifications": True,

            "theme": "light",

            "language": "en"

        }

    }

def generate_test_api_key_data() -> Dict[str, str]:

    """Generate test API key data"""

    return {

        "key_id": str(uuid.uuid4()),

        "key_name": f"test_key_{int(time.time())}",

        "description": "Test API key for integration testing"

    }

def generate_test_thread_data() -> Dict[str, Any]:

    """Generate test thread data"""

    return {

        "thread_id": str(uuid.uuid4()),

        "title": "Test Thread",

        "description": "Integration test thread",

        "created_at": datetime.now(timezone.utc).isoformat(),

        "status": "active"

    }

# Mock service helpers

class MockAuthService:

    """Mock authentication service for testing"""
    
    def __init__(self):

        self.users = {}

        self.sessions = {}
        
    async def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:

        """Mock user registration"""

        user_id = user_data["user_id"]

        self.users[user_id] = user_data.copy()
        
        return {

            "user_id": user_id,

            "status": "registered",

            "verification_required": True,

            "verification_token": str(uuid.uuid4())

        }
        
    async def verify_email(self, user_id: str, token: str) -> bool:

        """Mock email verification"""

        if user_id in self.users:

            self.users[user_id]["verified"] = True

            return True

        return False
        
    async def authenticate(self, email: str, password: str) -> Optional[Dict[str, Any]]:

        """Mock authentication"""

        for user in self.users.values():

            if user["email"] == email and user["password"] == password:

                session_token = str(uuid.uuid4())

                self.sessions[session_token] = {

                    "user_id": user["user_id"],

                    "created_at": time.time(),

                    "expires_at": time.time() + 3600

                }

                return {

                    "user_id": user["user_id"],

                    "session_token": session_token,

                    "expires_at": self.sessions[session_token]["expires_at"]

                }

        return None

class MockWebSocketManager:

    """Mock WebSocket manager for testing"""
    
    def __init__(self):

        self.connections = {}

        self.messages = []
        
    async def connect(self, user_id: str, websocket) -> bool:

        """Mock WebSocket connection"""

        self.connections[user_id] = {

            "websocket": websocket,

            "connected_at": time.time(),

            "last_ping": time.time()

        }

        return True
        
    async def disconnect(self, user_id: str):

        """Mock WebSocket disconnection"""

        if user_id in self.connections:

            del self.connections[user_id]
            
    async def send_message(self, user_id: str, message: Dict[str, Any]):

        """Mock sending message to user"""

        if user_id in self.connections:

            self.messages.append({

                "user_id": user_id,

                "message": message,

                "timestamp": time.time()

            })

            return True

        return False

class MockUsageService:

    """Mock usage tracking service"""
    
    def __init__(self):

        self.usage_records = defaultdict(list)
        
    async def track_usage(self, user_id: str, action: str, metadata: Dict[str, Any] = None):

        """Track user action"""

        self.usage_records[user_id].append({

            "action": action,

            "metadata": metadata or {},

            "timestamp": time.time()

        })
        
    async def get_usage_summary(self, user_id: str, period: str = "current_month") -> Dict[str, Any]:

        """Get usage summary for user"""

        records = self.usage_records.get(user_id, [])
        
        return {

            "user_id": user_id,

            "period": period,

            "total_actions": len(records),

            "action_counts": {},  # Would calculate actual counts

            "last_activity": max([r["timestamp"] for r in records]) if records else None

        }

# Test execution helpers

async def simulate_user_journey(steps: List[Dict[str, Any]], 

                              mock_services: Dict[str, Any]) -> Dict[str, Any]:

    """Simulate complete user journey through multiple steps"""

    results = {

        "steps_completed": 0,

        "steps_total": len(steps),

        "success": True,

        "errors": [],

        "step_results": []

    }
    
    user_context = {}
    
    for i, step in enumerate(steps):

        try:

            step_result = await execute_journey_step(step, user_context, mock_services)

            results["step_results"].append(step_result)
            
            if step_result.get("success", False):

                results["steps_completed"] += 1
                # Update context with step results

                user_context.update(step_result.get("context", {}))

            else:

                results["success"] = False

                results["errors"].append(f"Step {i+1} failed: {step_result.get('error', 'Unknown')}")

                break
                
        except Exception as e:

            results["success"] = False

            results["errors"].append(f"Step {i+1} exception: {str(e)}")

            break
    
    return results

async def execute_journey_step(step: Dict[str, Any], 

                             context: Dict[str, Any],

                             services: Dict[str, Any]) -> Dict[str, Any]:

    """Execute individual step of user journey"""

    step_type = step.get("type")

    step_data = step.get("data", {})
    
    if step_type == "register":

        return await _execute_registration_step(step_data, context, services)

    elif step_type == "verify_email":

        return await _execute_verification_step(step_data, context, services)

    elif step_type == "login":

        return await _execute_login_step(step_data, context, services)

    elif step_type == "create_thread":

        return await _execute_thread_creation_step(step_data, context, services)

    else:

        return {"success": False, "error": f"Unknown step type: {step_type}"}

async def _execute_registration_step(data: Dict[str, Any], 

                                   context: Dict[str, Any],

                                   services: Dict[str, Any]) -> Dict[str, Any]:

    """Execute user registration step"""

    auth_service = services.get("auth_service")

    if not auth_service:

        return {"success": False, "error": "Auth service not available"}
        
    user_data = data.get("user_data") or generate_test_user_data()
    
    try:

        result = await auth_service.register_user(user_data)

        return {

            "success": True,

            "context": {

                "user_id": result["user_id"],

                "verification_token": result.get("verification_token"),

                "user_data": user_data

            }

        }

    except Exception as e:

        return {"success": False, "error": str(e)}

async def _execute_verification_step(data: Dict[str, Any],

                                   context: Dict[str, Any], 

                                   services: Dict[str, Any]) -> Dict[str, Any]:

    """Execute email verification step"""

    auth_service = services.get("auth_service")

    user_id = context.get("user_id")

    token = context.get("verification_token")
    
    if not all([auth_service, user_id, token]):

        return {"success": False, "error": "Missing verification data"}
        
    try:

        verified = await auth_service.verify_email(user_id, token)

        return {

            "success": verified,

            "context": {"verified": verified}

        }

    except Exception as e:

        return {"success": False, "error": str(e)}

async def _execute_login_step(data: Dict[str, Any],

                            context: Dict[str, Any],

                            services: Dict[str, Any]) -> Dict[str, Any]:

    """Execute user login step"""

    auth_service = services.get("auth_service")

    user_data = context.get("user_data", {})
    
    email = user_data.get("email")

    password = user_data.get("password")
    
    if not all([auth_service, email, password]):

        return {"success": False, "error": "Missing login credentials"}
        
    try:

        session = await auth_service.authenticate(email, password)

        return {

            "success": session is not None,

            "context": {"session": session} if session else {}

        }

    except Exception as e:

        return {"success": False, "error": str(e)}

async def _execute_thread_creation_step(data: Dict[str, Any],

                                      context: Dict[str, Any],

                                      services: Dict[str, Any]) -> Dict[str, Any]:

    """Execute thread creation step"""
    # Implementation would depend on actual thread service

    thread_data = data.get("thread_data") or generate_test_thread_data()
    
    return {

        "success": True,

        "context": {"thread": thread_data}

    }

async def setup_test_infrastructure() -> Dict[str, Any]:

    """Setup test infrastructure for integration tests"""

    infrastructure = {

        "auth_service": MockAuthService(),

        "websocket_service": MagicMock(),

        "database": MagicMock(),

        "cache": MagicMock(),

        "started_at": datetime.now(timezone.utc)

    }
    
    # Initialize services

    await asyncio.sleep(0.1)  # Simulate initialization
    
    return infrastructure

async def teardown_test_infrastructure(infrastructure: Dict[str, Any]) -> None:

    """Teardown test infrastructure after tests"""
    # Cleanup resources

    await asyncio.sleep(0.1)  # Simulate cleanup
    
    # Log test duration

    if "started_at" in infrastructure:

        duration = (datetime.now(timezone.utc) - infrastructure["started_at"]).total_seconds()

        print(f"Test infrastructure ran for {duration:.2f} seconds")


class DatabaseTestHelpers:
    """Helper class for database operations in tests."""
    
    def __init__(self):
        self.test_data = {}
        self.transactions = []
    
    async def setup_test_database(self, db_session: AsyncSession):
        """Setup test database with sample data."""
        # Mock database setup
        self.test_data["users"] = []
        self.test_data["transactions"] = []
        return True
    
    async def cleanup_test_database(self, db_session: AsyncSession):
        """Clean up test database after tests."""
        # Mock database cleanup
        self.test_data.clear()
        self.transactions.clear()
        return True
    
    async def create_test_transaction(self, user_id: str, amount: float, transaction_type: str = "payment"):
        """Create a test transaction record."""
        transaction = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "amount": amount,
            "type": transaction_type,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.transactions.append(transaction)
        return transaction
    
    async def verify_transaction_integrity(self, transaction_id: str) -> bool:
        """Verify transaction data integrity."""
        for transaction in self.transactions:
            if transaction["id"] == transaction_id:
                return transaction["status"] == "completed"
        return False


class MiscTestHelpers:
    """Miscellaneous helper utilities for testing."""
    
    def __init__(self):
        self.test_context = {}
    
    def generate_test_id(self, prefix: str = "test") -> str:
        """Generate a unique test ID."""
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    
    def create_mock_request_data(self, **kwargs) -> Dict[str, Any]:
        """Create mock HTTP request data."""
        base_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": self.generate_test_id("req"),
            "user_agent": "TestClient/1.0"
        }
        base_data.update(kwargs)
        return base_data
    
    def validate_response_structure(self, response: Dict[str, Any], expected_fields: List[str]) -> bool:
        """Validate that response contains expected fields."""
        return all(field in response for field in expected_fields)
    
    async def simulate_delay(self, seconds: float = 0.1):
        """Simulate processing delay in tests."""
        await asyncio.sleep(seconds)


class RevenueTestHelpers:
    """Helper class for revenue-related testing operations."""
    
    def __init__(self):
        self.revenue_records = []
        self.subscription_data = {}
    
    async def create_test_subscription(self, user_id: str, plan: str = "free", status: str = "active"):
        """Create a test subscription record."""
        subscription = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "plan": plan,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "billing_period": "monthly" if plan != "free" else None,
            "amount": 0 if plan == "free" else 29.99
        }
        self.subscription_data[user_id] = subscription
        return subscription
    
    async def record_revenue_event(self, user_id: str, event_type: str, amount: float):
        """Record a revenue event for testing."""
        event = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "event_type": event_type,  # e.g., "subscription", "upgrade", "usage"
            "amount": amount,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        self.revenue_records.append(event)
        return event
    
    async def calculate_test_revenue(self, user_id: str, period_days: int = 30) -> float:
        """Calculate total revenue for a user within a period."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
        total_revenue = 0.0
        
        for record in self.revenue_records:
            if (record["user_id"] == user_id and 
                datetime.fromisoformat(record["recorded_at"]) > cutoff_date):
                total_revenue += record["amount"]
        
        return total_revenue
    
    def get_subscription_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription status for a user."""
        return self.subscription_data.get(user_id)