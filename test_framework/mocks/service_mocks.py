"""
Service mock implementations.
Reusable mock classes for various services.
"""

import asyncio
import time
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


# Quality Gate Service Mock Setup Helpers
def setup_redis_mock_with_error():
    """Setup Redis mock to simulate errors"""
    from unittest.mock import AsyncMock
    mock_redis = AsyncMock()
    mock_redis.get_list.side_effect = Exception("Redis connection failed")
    return mock_redis


def setup_redis_mock_with_large_cache():
    """Setup Redis mock with large cache list"""
    from unittest.mock import AsyncMock
    mock_redis = AsyncMock()
    mock_redis.get_list.return_value = [f"hash{i}" for i in range(100)]
    return mock_redis


def setup_quality_service_with_redis_error():
    """Create quality service with Redis error simulation"""
    # This function will be used by specific Quality Gate tests
    # Import locally to avoid circular dependencies
    mock_redis = setup_redis_mock_with_error()
    return {"redis_manager": mock_redis, "error_mode": True}


def setup_quality_service_with_large_cache():
    """Create quality service with large cache simulation"""
    # This function will be used by specific Quality Gate tests
    # Import locally to avoid circular dependencies
    mock_redis = setup_redis_mock_with_large_cache()
    return {"redis_manager": mock_redis, "large_cache": True}


def setup_validation_error_patch(quality_service):
    """Setup patch for validation error testing"""
    from unittest.mock import patch
    return patch.object(
        quality_service.metrics_calculator,
        'calculate_metrics',
        side_effect=ValueError("Calculation error")
    )


def setup_threshold_error_patch(quality_service):
    """Setup patch for threshold checking error"""
    from unittest.mock import patch
    return patch.object(
        quality_service.validator,
        'check_thresholds',
        side_effect=KeyError("Missing threshold")
    )


def setup_slow_validation_mock():
    """Setup mock for slow validation testing"""
    import asyncio
    
    async def slow_validate(content: str, content_type=None, context=None):
        await asyncio.sleep(0.1)
        return {
            "passed": True,
            "metrics": {},
            "validation_time": 0.1
        }
    return slow_validate


def create_metrics_storage_error(quality_service):
    """Create error condition for metrics storage"""
    quality_service.metrics_history = None


class MockServiceDependency:
    """
    Standardized mock service dependency for testing service initialization.
    
    This provides a consistent interface for all service mocking, including:
    - Proper initialization lifecycle 
    - Health checking
    - Startup timing simulation
    - Error injection for failure testing
    
    Used by service container tests to ensure proper initialization patterns.
    """
    
    def __init__(self, name: str, startup_delay: float = 0.1):
        self.name = name
        self.startup_delay = startup_delay
        self.initialized = False
        self.started = False
        self.healthy = False
        self.initialization_time = None
        self._startup_error = None
    
    async def initialize(self) -> bool:
        """Initialize the service dependency."""
        if self._startup_error:
            raise self._startup_error
        
        start_time = time.time()
        await asyncio.sleep(self.startup_delay)
        self.initialized = True
        self.initialization_time = time.time() - start_time
        return True
    
    async def start(self) -> bool:
        """Start the service dependency."""
        if not self.initialized:
            raise RuntimeError(f"{self.name} not initialized before start")
        
        if self._startup_error:
            raise self._startup_error
        
        self.started = True
        self.healthy = True
        return True
    
    async def stop(self) -> bool:
        """Stop the service dependency.""" 
        self.started = False
        self.healthy = False
        return True
    
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.healthy and self.started
    
    def set_startup_error(self, error: Exception):
        """Set error to be raised during startup."""
        self._startup_error = error


class MockConfigurationManager:
    """
    Standardized mock configuration manager for testing.
    
    This provides consistent configuration patterns across all tests:
    - Proper initialization with initialize() method (required for service containers)
    - Environment-specific configuration loading
    - Configuration validation patterns
    - Loaded state tracking
    
    Key fix: Has initialize() method that calls load_configuration() to set loaded=True
    This ensures compatibility with service container initialization patterns.
    """
    
    def __init__(self):
        self.loaded = False
        self.config = {}
        self.load_errors = []
        self.validation_errors = []
    
    async def initialize(self) -> bool:
        """
        Initialize the configuration manager by loading configuration.
        
        This method is required for service container compatibility.
        It ensures that the 'loaded' flag is properly set to True.
        """
        await self.load_configuration()
        return True
    
    async def load_configuration(self, config_paths: List[str] = None) -> Dict[str, Any]:
        """Load configuration with environment-specific overrides."""
        await asyncio.sleep(0.05)  # Simulate loading time
        
        # Default test configuration following SSOT patterns
        self.config = {
            "SERVICE_NAME": "test_service",
            "ENVIRONMENT": "test", 
            "DATABASE_URL": "postgresql://test:test@localhost:5434/test_db",
            "AUTH_SERVICE_URL": "http://localhost:8081",
            "REDIS_URL": "redis://localhost:6381",
            "LOG_LEVEL": "INFO",
            "DEBUG": "true",
            "SECRET_KEY": "test_secret_key_for_initialization",
            "JWT_SECRET_KEY": "test_jwt_secret_key_for_initialization"
        }
        
        # Environment-specific configuration overrides
        if config_paths:
            for path in config_paths:
                if "staging" in path:
                    self.config.update({
                        "ENVIRONMENT": "staging",
                        "DEBUG": "false"
                    })
                elif "production" in path:
                    self.config.update({
                        "ENVIRONMENT": "production", 
                        "DEBUG": "false"
                    })
        
        self.loaded = True
        return self.config.copy()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration against requirements."""
        errors = []
        
        required_keys = ["SERVICE_NAME", "DATABASE_URL", "SECRET_KEY"]
        for key in required_keys:
            if key not in self.config:
                errors.append(f"Missing required configuration: {key}")
        
        # Check for insecure configurations
        if self.config.get("DEBUG") == "true" and self.config.get("ENVIRONMENT") == "production":
            errors.append("Debug mode should not be enabled in production")
        
        self.validation_errors = errors
        return errors


class MockServiceContainer:
    """
    Standardized mock dependency injection container.
    
    This provides consistent service container patterns:
    - Singleton and factory service registration
    - Proper initialization order tracking
    - Service lifecycle management
    - Consistent service retrieval patterns
    
    Compatible with the fixed MockConfigurationManager that has initialize() method.
    """
    
    def __init__(self):
        self.services = {}
        self.singletons = {}
        self.factories = {}
        self.initialization_order = []
    
    def register_singleton(self, service_type: str, instance: Any):
        """Register singleton service."""
        self.singletons[service_type] = instance
    
    def register_factory(self, service_type: str, factory: callable):
        """Register service factory."""
        self.factories[service_type] = factory
    
    async def get_service(self, service_type: str) -> Any:
        """Get service instance."""
        if service_type in self.singletons:
            return self.singletons[service_type]
        elif service_type in self.factories:
            if service_type not in self.services:
                self.services[service_type] = await self.factories[service_type]()
            return self.services[service_type]
        else:
            raise ValueError(f"Service {service_type} not registered")
    
    async def initialize_all_services(self):
        """
        Initialize all registered services in proper order.
        
        This method looks for services with initialize() method and calls them.
        The MockConfigurationManager now has this method, fixing the original issue.
        """
        # Initialize singletons first
        for service_type, instance in self.singletons.items():
            if hasattr(instance, 'initialize'):
                await instance.initialize()
                self.initialization_order.append(service_type)
        
        # Initialize factory-created services
        for service_type in self.factories.keys():
            service = await self.get_service(service_type)
            if hasattr(service, 'initialize'):
                await service.initialize()
                self.initialization_order.append(service_type)