"""
User journey test data and scenarios for comprehensive flow testing.
Provides realistic test data for different user segments and use cases.

BVJ (Business Value Justification):
1. Segment: All tiers (Free  ->  Early  ->  Mid  ->  Enterprise)
2. Business Goal: Ensure realistic testing scenarios
3. Value Impact: Validates real user workflows and edge cases
4. Strategic Impact: Protects conversion funnel integrity
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


class UserTestData:
    """Test data generators for different user segments."""
    
    @staticmethod
    def generate_user_data(segment: str = "free") -> Dict[str, Any]:
        """Generate unique test user data for specific segment."""
        timestamp = int(time.time() * 1000)
        base_data = {
            "email": f"test-{segment}-{timestamp}@netratest.com",
            "password": "TestPass123!Secure",
            "full_name": f"Test {segment.title()} User",
            "accept_terms": True
        }
        
        if segment == "enterprise":
            base_data.update({
                "company": "Enterprise Corp Ltd",
                "role": "AI Engineering Director",
                "team_size": "50-100",
                "monthly_ai_spend": 25000
            })
        elif segment == "mid":
            base_data.update({
                "company": "Mid-Size Tech Co",
                "role": "Senior AI Engineer",
                "team_size": "10-25",
                "monthly_ai_spend": 5000
            })
        elif segment == "early":
            base_data.update({
                "company": "Startup Inc",
                "role": "AI Engineer",
                "team_size": "5-10",
                "monthly_ai_spend": 1000
            })
        else:  # free
            base_data.update({
                "company": "Personal Project",
                "role": "Developer",
                "team_size": "1-2",
                "monthly_ai_spend": 100
            })
        
        return base_data

class UserJourneyScenarios:
    """Pre-defined user journey scenarios for testing."""
    
    FREE_TIER_ONBOARDING = {
        "user_messages": [
            "I want to optimize my AI costs by 20% without losing quality",
            "Can you analyze my current OpenAI usage?",
            "What are the best alternatives to GPT-4?",
            "How much could I save by switching models?"
        ],
        "expected_features": [
            "basic_chat",
            "usage_tracking",
            "simple_analytics",
            "basic_export"
        ],
        "blocked_features": [
            "advanced_analytics",
            "enterprise_tools",
            "bulk_operations",
            "priority_support"
        ]
    }
    
    EARLY_TIER_CONVERSION = {
        "user_messages": [
            "I need more detailed cost analysis",
            "Can you help optimize our model selection strategy?",
            "Show me advanced performance metrics",
            "I want to export detailed usage reports"
        ],
        "upgrade_triggers": [
            "daily_limit_reached",
            "advanced_feature_needed",
            "export_limitation"
        ],
        "conversion_value": 29.0  # Monthly plan price
    }
    
    MID_TIER_EXPANSION = {
        "user_messages": [
            "Analyze cost trends across our entire team",
            "Set up automated optimization recommendations",
            "Compare performance across different models",
            "Generate executive summary reports"
        ],
        "team_features": [
            "team_analytics",
            "shared_workspaces",
            "role_based_access",
            "bulk_analysis"
        ],
        "expansion_value": 99.0  # Mid-tier plan price
    }
    
    ENTERPRISE_REQUIREMENTS = {
        "user_messages": [
            "Integrate with our existing ML pipeline",
            "Set up organization-wide cost monitoring",
            "Configure custom optimization rules",
            "Enable audit logging and compliance reporting"
        ],
        "enterprise_features": [
            "custom_integrations",
            "sso_saml",
            "audit_logging",
            "compliance_reporting",
            "dedicated_support",
            "custom_models"
        ],
        "contract_value": 999.0  # Enterprise plan price
    }

class OptimizationTestScenarios:
    """Real-world optimization scenarios for testing."""
    
    COST_REDUCTION_REQUEST = {
        "type": "cost_optimization",
        "context": {
            "current_monthly_cost": 5000,
            "target_reduction_percentage": 20,
            "quality_threshold": 0.95,
            "models_in_use": [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value],
            "daily_requests": 10000,
            "average_tokens_per_request": 500
        },
        "urgency": "normal",
        "detailed_analysis": True
    }
    
    PERFORMANCE_OPTIMIZATION = {
        "type": "performance_optimization",
        "context": {
            "current_latency_p95": 2500,
            "target_latency_p95": 1500,
            "quality_threshold": 0.9,
            "peak_requests_per_second": 100,
            "average_context_length": 2000
        },
        "urgency": "high",
        "detailed_analysis": True
    }
    
    MODEL_MIGRATION = {
        "type": "model_migration",
        "context": {
            "from_model": LLMModel.GEMINI_2_5_FLASH.value,
            "to_model": LLMModel.GEMINI_2_5_FLASH.value,
            "migration_timeline": "30_days",
            "risk_tolerance": "low",
            "test_percentage": 5
        },
        "urgency": "normal",
        "detailed_analysis": True
    }

class ErrorScenarios:
    """Error scenarios for testing resilience."""
    
    VALIDATION_ERRORS = [
        {"content": "", "thread_id": "invalid-uuid"},  # Empty content
        {"content": "Test", "thread_id": "not-a-uuid"},  # Invalid UUID
        {"content": None, "thread_id": str(uuid.uuid4())},  # Null content
    ]
    
    RATE_LIMIT_SCENARIOS = [
        {"requests_per_minute": 120, "plan": "free", "should_limit": True},
        {"requests_per_minute": 500, "plan": "pro", "should_limit": False},
        {"requests_per_minute": 2000, "plan": "enterprise", "should_limit": False},
    ]
    
    SERVICE_FAILURES = [
        {"service": "llm_manager", "error": "LLM service unavailable"},
        {"service": "database", "error": "Database connection timeout"},
        {"service": "redis", "error": "Cache service unavailable"},
        {"service": "billing", "error": "Payment service temporarily down"},
    ]

class WebSocketTestScenarios:
    """WebSocket-specific test scenarios."""
    
    CONNECTION_LIFECYCLE = [
        {"action": "connect", "expected": "connection_established"},
        {"action": "ping", "expected": "pong"},
        {"action": "send_message", "expected": "message_acknowledged"},
        {"action": "disconnect", "expected": "connection_closed"},
        {"action": "reconnect", "expected": "session_restored"},
    ]
    
    CONCURRENT_CONNECTIONS = {
        "max_connections_free": 2,
        "max_connections_pro": 10,
        "max_connections_enterprise": 50,
        "test_scenarios": [
            {"connections": 5, "plan": "free", "should_succeed": False},
            {"connections": 15, "plan": "pro", "should_succeed": False},
            {"connections": 25, "plan": "enterprise", "should_succeed": True},
        ]
    }

class ProviderIntegrationData:
    """Provider integration test data."""
    
    OPENAI_CONNECTION = {
        "api_key": "sk-test-1234567890abcdef",
        "organization_id": "org-test123",
        "expected_models": [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "text-embedding-ada-002"]
    }
    
    ANTHROPIC_CONNECTION = {
        "api_key": "sk-ant-test-key-123",
        "expected_models": [LLMModel.GEMINI_2_5_FLASH.value, "claude-3-haiku"]
    }
    
    OAUTH_PROVIDERS = {
        "google": {
            "mock_user_info": {
                "id": "google_123456",
                "email": "testuser@gmail.com",
                "name": "Test User",
                "picture": "https://example.com/photo.jpg",
                "verified_email": True
            }
        },
        "github": {
            "mock_user_info": {
                "id": 789012,
                "login": "testuser",
                "email": "testuser@github.com",
                "name": "Test GitHub User",
                "avatar_url": "https://avatars.githubusercontent.com/u/789012"
            }
        }
    }

class BillingTestData:
    """Billing and subscription test data."""
    
    PLAN_CONFIGURATIONS = {
        "free": {
            "price": 0,
            "daily_message_limit": 50,
            "concurrent_sessions": 2,
            "export_retention_days": 7,
            "support_level": "community"
        },
        "early": {
            "price": 29,
            "daily_message_limit": 500,
            "concurrent_sessions": 5,
            "export_retention_days": 30,
            "support_level": "email"
        },
        "pro": {
            "price": 99,
            "daily_message_limit": 2000,
            "concurrent_sessions": 10,
            "export_retention_days": 90,
            "support_level": "priority"
        },
        "enterprise": {
            "price": 999,
            "daily_message_limit": "unlimited",
            "concurrent_sessions": 50,
            "export_retention_days": 365,
            "support_level": "dedicated"
        }
    }
    
    PAYMENT_TEST_TOKENS = {
        "valid_visa": "tok_test_visa_4242",
        "valid_mastercard": "tok_test_mastercard_5555",
        "declined_card": "tok_test_declined_card",
        "insufficient_funds": "tok_test_insufficient_funds"
    }

class AnalyticsTestData:
    """Analytics and reporting test data."""
    
    USAGE_PATTERNS = {
        "light_user": {
            "daily_messages": 5,
            "avg_tokens_per_message": 200,
            "session_duration_minutes": 15
        },
        "moderate_user": {
            "daily_messages": 25,
            "avg_tokens_per_message": 400,
            "session_duration_minutes": 45
        },
        "heavy_user": {
            "daily_messages": 100,
            "avg_tokens_per_message": 800,
            "session_duration_minutes": 120
        }
    }
    
    EXPORT_FORMATS = [
        {"format": "csv", "max_rows_free": 1000},
        {"format": "json", "max_rows_free": 1000},
        {"format": "excel", "min_plan": "pro"},
        {"format": "api", "min_plan": "enterprise"}
    ]