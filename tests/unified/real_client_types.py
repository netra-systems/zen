"""Real Client Types and Configuration

Core types, enums, and configuration classes for the real client factory.
Separated for architectural compliance with 300-line limit.

Business Value Justification (BVJ):
- Segment: All customer tiers
- Business Goal: Enable reliable E2E testing infrastructure  
- Value Impact: Foundation for production-like testing
- Revenue Impact: Better testing prevents production issues
"""

import ssl
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ConnectionState(Enum):
    """Connection state enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"


@dataclass
class ConnectionMetrics:
    """Connection performance tracking"""
    requests_sent: int = 0
    responses_received: int = 0
    connection_time: Optional[float] = None
    last_error: Optional[str] = None
    retry_count: int = 0


@dataclass
class ClientConfig:
    """Client configuration settings"""
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    pool_size: int = 10
    verify_ssl: bool = False
    
    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context if needed"""
        if not self.verify_ssl:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        return None
    
    def get_retry_delay(self, attempt: int) -> float:
        """Get retry delay with backoff"""
        return self.retry_delay * (attempt + 1)


def create_test_config(timeout: float = 30.0, max_retries: int = 3) -> ClientConfig:
    """Create test configuration with common settings"""
    return ClientConfig(timeout=timeout, max_retries=max_retries, verify_ssl=False)


def create_auth_config() -> ClientConfig:
    """Create auth-specific configuration"""
    return ClientConfig(timeout=15.0, max_retries=2, verify_ssl=False)


def create_backend_config() -> ClientConfig:
    """Create backend-specific configuration"""
    return ClientConfig(timeout=60.0, max_retries=3, pool_size=20, verify_ssl=False)