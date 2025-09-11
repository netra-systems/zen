"""
Test Framework Decorators Package

This package provides test decorators that wrap pytest markers for clear
test configuration and dependency declaration.

Usage:
    from test_framework.decorators import requires_real_database, requires_real_redis
    
    @requires_real_database
    @requires_real_redis
    async def test_database_and_redis():
        # Test code
        pass
"""

from test_framework.decorators.test_decorators import (
    requires_real_database,
    requires_real_redis,
    requires_real_services,
    requires_docker,
    requires_websocket,
    mission_critical,
    race_condition_test,
    experimental_test,
    feature_flag,
    requires_feature,
    tdd_test
)

# Re-export all decorators
__all__ = [
    'requires_real_database',
    'requires_real_redis',
    'requires_real_services', 
    'requires_docker',
    'requires_websocket',
    'mission_critical',
    'race_condition_test',
    'experimental_test',
    'feature_flag',
    'requires_feature',
    'tdd_test'
]