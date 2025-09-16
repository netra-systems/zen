"""
NetraOptimizer - The Claude Code Optimization Engine

A centralized, instrumented client for all Claude Code interactions,
ensuring every execution is automatically measured and optimized.

Now with Google CloudSQL integration for enterprise-grade tracking.
"""

__version__ = "0.2.0"  # Updated for CloudSQL integration

from .client import NetraOptimizerClient
from .database.client import DatabaseClient
from .cloud_config import cloud_config

__all__ = ["NetraOptimizerClient", "DatabaseClient", "cloud_config"]