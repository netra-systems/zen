"""
Mock utilities for test compliance with CLAUDE.md and testing.xml.
All mocks must be justified per testing.xml rule: mock-justification-required.
"""

from functools import wraps
from typing import Callable, Any


def mock_justified(reason: str) -> Callable:
    """
    Decorator to document mock justification per testing.xml requirements.
    A mock without justification is a violation.
    
    Args:
        reason: Explicit justification for why this mock is necessary
    
    Usage:
        @mock_justified("External Stripe API not available in test environment")
        @patch('app.services.payment.stripe_client')
        def test_payment_processing(self, mock_stripe):
            ...
    
        @mock_justified("Database connection would make test non-deterministic")
        @patch('app.models.user.User.save')
        def test_user_creation(self, mock_save):
            ...
    
    Examples of valid justifications:
        - "External API not available in test environment"
        - "Filesystem operations would pollute test environment"
        - "Network calls would make tests non-deterministic"
        - "Third-party service requires paid credentials"
        - "Hardware device not available in CI environment"
    
    Examples of INVALID justifications (use real components instead):
        - "Easier to test with mock" (violates minimal-mocking rule)
        - "Component is complex" (violates real-child-components rule)
        - "Faster with mock" (speed is not a valid reason)
    """
    def decorator(func: Callable) -> Callable:
        # Store justification as function attribute for validation
        func.__mock_justification__ = reason
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return func(*args, **kwargs)
        
        # Preserve the justification on the wrapper
        wrapper.__mock_justification__ = reason
        return wrapper
    
    return decorator


def validate_mock_justification(justification: str) -> bool:
    """
    Validate that a mock justification meets requirements.
    
    Args:
        justification: The justification string to validate
    
    Returns:
        True if justification is valid, False otherwise
    """
    if not justification or len(justification) < 10:
        return False
    
    # List of invalid justification patterns
    invalid_patterns = [
        "easier",
        "faster", 
        "simpler",
        "complex",
        "too hard",
        "convenience",
    ]
    
    justification_lower = justification.lower()
    for pattern in invalid_patterns:
        if pattern in justification_lower:
            return False
    
    # List of valid justification keywords
    valid_keywords = [
        "external",
        "api",
        "network",
        "filesystem",
        "database",
        "hardware",
        "credentials",
        "environment",
        "non-deterministic",
        "third-party",
        "unavailable",
        "ci",
    ]
    
    # Check if at least one valid keyword is present
    return any(keyword in justification_lower for keyword in valid_keywords)