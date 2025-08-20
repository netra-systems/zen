"""
GCP Integration Module for Cloud Run Testing.

This module provides interfaces and implementations for interacting with Google Cloud Platform
services including Cloud Logging, Secret Manager, and Cloud Run.
"""

from .log_reader import GCPLogReader, LogEntry, LogFilter
from .health_monitor import GCPHealthMonitor, ServiceHealth
from .deployment_validator import GCPDeploymentValidator, DeploymentStatus
from .secret_manager import GCPSecretManager
from .auth_handler import GCPAuthHandler, AuthenticationError

__all__ = [
    'GCPLogReader',
    'LogEntry',
    'LogFilter',
    'GCPHealthMonitor',
    'ServiceHealth',
    'GCPDeploymentValidator',
    'DeploymentStatus',
    'GCPSecretManager',
    'GCPAuthHandler',
    'AuthenticationError'
]