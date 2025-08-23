"""
Service mock implementations.
Reusable mock classes for various services.
"""

from unittest.mock import AsyncMock, MagicMock
from typing import Any, Dict, List, Optional


class MockClickHouseService:
    """Mock ClickHouse service for testing"""
    
    def __init__(self):
        self.queries_executed = []
        self.data_inserted = []
        
    async def execute(self, query: str) -> List[Dict[str, Any]]:
        """Mock execute query"""
        self.queries_executed.append(query)
        return []
    
    async def insert(self, table: str, data: List[Dict[str, Any]]) -> bool:
        """Mock insert data"""
        self.data_inserted.append({"table": table, "data": data})
        return True
    
    async def close(self):
        """Mock close connection"""
        pass


class MockRedisService:
    """Mock Redis service for testing"""
    
    def __init__(self):
        self.data = {}
        self.operations = []
        
    async def get(self, key: str) -> Optional[str]:
        """Mock get value"""
        self.operations.append(("get", key))
        return self.data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock set value"""
        self.operations.append(("set", key, value, ex))
        self.data[key] = value
        return True
    
    async def delete(self, key: str) -> bool:
        """Mock delete key"""
        self.operations.append(("delete", key))
        if key in self.data:
            del self.data[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Mock key exists check"""
        self.operations.append(("exists", key))
        return key in self.data
    
    async def ping(self) -> bool:
        """Mock ping"""
        return True


class MockLLMService:
    """Mock LLM service for testing"""
    
    def __init__(self):
        self.requests = []
        self.responses = []
        self.default_response = {
            "content": "Mock LLM response",
            "model": "mock-model",
            "tokens_used": 10,
            "cost": 0.001
        }
        
    def set_response(self, response: Dict[str, Any]):
        """Set the response for next request"""
        self.responses.append(response)
        
    async def generate_response(
        self, 
        prompt: str, 
        model: str = "default",
        **kwargs
    ) -> Dict[str, Any]:
        """Mock generate response"""
        self.requests.append({
            "prompt": prompt,
            "model": model,
            "kwargs": kwargs
        })
        
        if self.responses:
            return self.responses.pop(0)
        return self.default_response.copy()
    
    async def analyze_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock optimization analysis"""
        return {
            "optimization_suggestions": ["Mock suggestion"],
            "confidence": 0.85,
            "potential_savings": 1000
        }


class MockAgentService:
    """Mock agent service for testing"""
    
    def __init__(self):
        self.messages_processed = []
        self.agents = {}
        self.next_agent_id = 1
        
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Mock process message"""
        self.messages_processed.append(message)
        return {
            "response": f"Processed: {message.get('content', 'no content')}",
            "metadata": {"agent_id": f"agent_{self.next_agent_id}"},
            "status": "completed"
        }
    
    async def start_agent(self, agent_config: Dict[str, Any]) -> Dict[str, str]:
        """Mock start agent"""
        agent_id = f"agent_{self.next_agent_id}"
        self.next_agent_id += 1
        self.agents[agent_id] = {
            "status": "running",
            "config": agent_config
        }
        return {"agent_id": agent_id}
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Mock stop agent"""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "stopped"
            return True
        return False
    
    def get_agent_status(self, agent_id: str) -> str:
        """Mock get agent status"""
        if agent_id in self.agents:
            return self.agents[agent_id]["status"]
        return "not_found"


class MockWebSocketBroadcaster:
    """Mock WebSocket broadcaster for testing"""
    
    def __init__(self):
        self.broadcasts = []
        self.rooms = {}
        
    async def join_room(self, connection_id: str, room: str):
        """Mock join room"""
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(connection_id)
        
    async def leave_room(self, connection_id: str, room: str):
        """Mock leave room"""
        if room in self.rooms:
            self.rooms[room].discard(connection_id)
            
    async def leave_all_rooms(self, connection_id: str):
        """Mock leave all rooms"""
        for room in self.rooms.values():
            room.discard(connection_id)
            
    async def broadcast_to_room(self, room: str, message: Dict[str, Any]):
        """Mock broadcast to room"""
        self.broadcasts.append({
            "room": room,
            "message": message,
            "recipients": list(self.rooms.get(room, []))
        })


class MockNotificationService:
    """Mock notification service for testing"""
    
    def __init__(self):
        self.sent_notifications = []
        
    async def send_email(
        self, 
        to: str, 
        subject: str, 
        body: str,
        template: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock send email"""
        notification = {
            "type": "email",
            "to": to,
            "subject": subject,
            "body": body,
            "template": template,
            "sent": True,
            "message_id": f"email_{len(self.sent_notifications) + 1}"
        }
        self.sent_notifications.append(notification)
        return notification
    
    async def send_sms(self, to: str, message: str) -> Dict[str, Any]:
        """Mock send SMS"""
        notification = {
            "type": "sms",
            "to": to,
            "message": message,
            "sent": True,
            "message_id": f"sms_{len(self.sent_notifications) + 1}"
        }
        self.sent_notifications.append(notification)
        return notification
    
    async def send_push_notification(
        self, 
        user_id: str, 
        title: str, 
        body: str
    ) -> Dict[str, Any]:
        """Mock send push notification"""
        notification = {
            "type": "push",
            "user_id": user_id,
            "title": title,
            "body": body,
            "sent": True
        }
        self.sent_notifications.append(notification)
        return notification


class MockPaymentService:
    """Mock payment service for testing"""
    
    def __init__(self):
        self.transactions = []
        self.subscriptions = {}
        self.next_transaction_id = 1
        self.next_subscription_id = 1
        
    async def process_payment(
        self,
        amount: float,
        currency: str = "USD",
        payment_method: str = "card"
    ) -> Dict[str, Any]:
        """Mock process payment"""
        transaction = {
            "transaction_id": f"txn_{self.next_transaction_id}",
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "success": True,
            "status": "completed"
        }
        self.next_transaction_id += 1
        self.transactions.append(transaction)
        return transaction
    
    async def create_subscription(
        self,
        user_id: str,
        plan: str,
        amount: float
    ) -> Dict[str, Any]:
        """Mock create subscription"""
        subscription = {
            "subscription_id": f"sub_{self.next_subscription_id}",
            "user_id": user_id,
            "plan": plan,
            "amount": amount,
            "status": "active",
            "next_billing_date": "2025-02-01"
        }
        self.next_subscription_id += 1
        self.subscriptions[subscription["subscription_id"]] = subscription
        return subscription
    
    async def cancel_subscription(self, subscription_id: str) -> Dict[str, bool]:
        """Mock cancel subscription"""
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id]["status"] = "cancelled"
            return {"cancelled": True}
        return {"cancelled": False}


class MockHealthCheckService:
    """Mock health check service for testing"""
    
    def __init__(self):
        self.health_status = "healthy"
        self.checks = {}
        
    def set_health_status(self, status: str):
        """Set overall health status"""
        self.health_status = status
        
    def set_check_status(self, check_name: str, status: str):
        """Set individual check status"""
        self.checks[check_name] = status
        
    async def check_database(self) -> Dict[str, str]:
        """Mock database health check"""
        return {"status": self.checks.get("database", "healthy")}
    
    async def check_redis(self) -> Dict[str, str]:
        """Mock Redis health check"""
        return {"status": self.checks.get("redis", "healthy")}
    
    async def check_external_apis(self) -> Dict[str, str]:
        """Mock external APIs health check"""
        return {"status": self.checks.get("external_apis", "healthy")}
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Mock overall health check"""
        return {
            "status": self.health_status,
            "checks": {
                "database": self.checks.get("database", "healthy"),
                "redis": self.checks.get("redis", "healthy"),
                "external_apis": self.checks.get("external_apis", "healthy")
            }
        }