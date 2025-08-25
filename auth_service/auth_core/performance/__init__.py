"""
Auth Service Performance Optimization Package
High-performance authentication with caching, connection pooling, and monitoring
"""

from .startup_optimizer import startup_optimizer
from .metrics import auth_performance_monitor, monitor_auth_performance

__all__ = [
    'startup_optimizer',
    'auth_performance_monitor', 
    'monitor_auth_performance'
]