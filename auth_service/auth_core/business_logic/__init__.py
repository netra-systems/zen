"""
Business Logic Package - Auth Service

This package contains business logic validators and processors for authentication,
registration, subscription management, and user lifecycle operations.

Following SSOT principles - each business rule has one canonical implementation.
"""

from auth_service.auth_core.business_logic.user_business_logic import (
    UserBusinessLogic,
    UserRegistrationValidator,
    validate_registration,
    user_business_logic,
)

from auth_service.auth_core.business_logic.subscription_business_logic import (
    SubscriptionBusinessLogic,
    subscription_validator,
)

__all__ = [
    "UserBusinessLogic", 
    "UserRegistrationValidator",
    "validate_registration",
    "user_business_logic",
    "SubscriptionBusinessLogic",
    "subscription_validator",
]