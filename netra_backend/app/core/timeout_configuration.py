"""Cloud-Native Timeout Configuration - Single Source of Truth

**BUSINESS CONTEXT**: Priority 3 timeout hierarchy fixes to restore $200K+ MRR business value
by aligning timeouts for cloud-native GCP Cloud Run environment.

**ROOT CAUSE**: WebSocket (3s) → Agent (15s) timeout causing premature failures
**REQUIRED**: Cloud-native timeout hierarchy with 35s WebSocket → 30s Agent coordination
**IMPACT**: $200K+ MRR affected by inconsistent AI processing reliability

**IMPLEMENTATION STRATEGY**:
1. Environment-aware timeout configurations (local vs cloud)
2. Coordinated hierarchy: WebSocket > Agent execution timeouts  
3. SSOT compliance for centralized timeout management
4. GCP Cloud Run optimized values for cold starts and network latency

Business Value Justification (BVJ):
- Segment: Platform/Enterprise 
- Business Goal: System Reliability and Customer Retention
- Value Impact: Prevents $200K+ MRR loss from timeout-related failures
- Revenue Impact: Maintains AI processing reliability for all customer tiers
"""

import os
from typing import Dict, Any
from enum import Enum
from dataclasses import dataclass

from shared.isolated_environment import get_env

class TimeoutEnvironment(Enum):
    """Environment types for timeout configuration."""
    LOCAL_DEVELOPMENT = "local"
    CLOUD_RUN_STAGING = "staging" 
    CLOUD_RUN_PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class TimeoutConfig:
    """Timeout configuration for specific environment."""
    
    # WebSocket timeouts (must be > agent timeouts for hierarchy)
    websocket_connection_timeout: int
    websocket_recv_timeout: int  # Critical for test fixes
    websocket_send_timeout: int
    websocket_heartbeat_timeout: int
    
    # Agent execution timeouts (must be < websocket timeouts)
    agent_execution_timeout: int
    agent_thinking_timeout: int
    agent_tool_timeout: int
    agent_completion_timeout: int
    
    # HTTP client timeouts
    http_request_timeout: int
    http_connection_timeout: int
    
    # Test timeouts 
    test_default_timeout: int
    test_integration_timeout: int
    test_e2e_timeout: int


class CloudNativeTimeoutManager:
    """SSOT manager for cloud-native timeout configurations.
    
    **CRITICAL BUSINESS REQUIREMENT**: Timeout hierarchy must ensure:
    - WebSocket timeouts > Agent execution timeouts (coordination)
    - Cloud Run environments get longer timeouts (cold starts)
    - Local development gets shorter timeouts (fast feedback)
    - Test environments get appropriate timeouts (stability vs speed)
    """
    
    def __init__(self):
        """Initialize timeout manager with environment detection."""
        self._env = get_env()
        self._environment = self._detect_environment()
        self._config_cache = None
        
    def _detect_environment(self) -> TimeoutEnvironment:
        """Detect current environment for timeout configuration."""
        # Always refresh environment to handle dynamic changes during testing
        self._env = get_env()
        
        # PRIORITY 3 FIX: Check direct os.environ first for explicit ENVIRONMENT setting
        # This allows testing to override isolated environment defaults
        direct_env = os.environ.get("ENVIRONMENT")
        if direct_env:
            env_name = direct_env.lower()
        else:
            env_name = self._env.get("ENVIRONMENT", "development").lower()
        
        # Check for testing environment markers (but allow explicit overrides)
        if not direct_env and (self._env.get("PYTEST_CURRENT_TEST") or 
            self._env.get("TESTING") == "true" or 
            env_name == "testing"):
            return TimeoutEnvironment.TESTING
            
        # Check for cloud environments
        if env_name == "staging":
            return TimeoutEnvironment.CLOUD_RUN_STAGING
        elif env_name == "production":
            return TimeoutEnvironment.CLOUD_RUN_PRODUCTION
        elif env_name == "testing":
            return TimeoutEnvironment.TESTING
        else:
            return TimeoutEnvironment.LOCAL_DEVELOPMENT
    
    def get_timeout_config(self) -> TimeoutConfig:
        """Get timeout configuration for current environment.
        
        **CRITICAL HIERARCHY**: WebSocket timeouts > Agent timeouts for coordination
        
        Returns:
            TimeoutConfig: Environment-specific timeout configuration
        """
        # Always re-detect environment for testing flexibility
        current_env = self._detect_environment()
        if self._config_cache is None or current_env != self._environment:
            self._environment = current_env
            self._config_cache = self._create_timeout_config()
            
        return self._config_cache
    
    def _create_timeout_config(self) -> TimeoutConfig:
        """Create timeout configuration for detected environment."""
        
        if self._environment == TimeoutEnvironment.CLOUD_RUN_STAGING:
            return TimeoutConfig(
                # CRITICAL FIX: WebSocket timeouts for Cloud Run staging (35s > 30s agent)
                websocket_connection_timeout=60,  # Connection establishment
                websocket_recv_timeout=35,        # PRIORITY 3 FIX: 3s → 35s
                websocket_send_timeout=30,
                websocket_heartbeat_timeout=90,
                
                # Agent execution timeouts (must be < WebSocket recv timeout)
                agent_execution_timeout=30,       # PRIORITY 3 FIX: 15s → 30s 
                agent_thinking_timeout=25,
                agent_tool_timeout=20,
                agent_completion_timeout=15,
                
                # HTTP timeouts for Cloud Run
                http_request_timeout=30,
                http_connection_timeout=15,
                
                # Test timeouts for staging environment
                test_default_timeout=60,
                test_integration_timeout=90,
                test_e2e_timeout=120
            )
            
        elif self._environment == TimeoutEnvironment.CLOUD_RUN_PRODUCTION:
            return TimeoutConfig(
                # Production WebSocket timeouts (slightly higher for reliability)
                websocket_connection_timeout=90,
                websocket_recv_timeout=45,        # Production: 45s > 40s agent
                websocket_send_timeout=40, 
                websocket_heartbeat_timeout=120,
                
                # Production agent timeouts (must be < WebSocket recv timeout)
                agent_execution_timeout=40,       # Production: longer for complex tasks
                agent_thinking_timeout=35,
                agent_tool_timeout=30,
                agent_completion_timeout=20,
                
                # Production HTTP timeouts
                http_request_timeout=45,
                http_connection_timeout=20,
                
                # Production test timeouts (if tests run in prod)
                test_default_timeout=90,
                test_integration_timeout=150,
                test_e2e_timeout=180
            )
            
        elif self._environment == TimeoutEnvironment.TESTING:
            return TimeoutConfig(
                # Testing WebSocket timeouts (moderate for stability)
                websocket_connection_timeout=30,
                websocket_recv_timeout=15,        # Testing: fast but stable
                websocket_send_timeout=10,
                websocket_heartbeat_timeout=45,
                
                # Testing agent timeouts (must be < WebSocket recv timeout) 
                agent_execution_timeout=10,       # Testing: fast execution
                agent_thinking_timeout=8,
                agent_tool_timeout=5,
                agent_completion_timeout=3,
                
                # Testing HTTP timeouts
                http_request_timeout=15,
                http_connection_timeout=10,
                
                # Test framework timeouts
                test_default_timeout=30,
                test_integration_timeout=45,
                test_e2e_timeout=60
            )
            
        else:  # LOCAL_DEVELOPMENT
            return TimeoutConfig(
                # Local development WebSocket timeouts (fast feedback)
                websocket_connection_timeout=20,
                websocket_recv_timeout=10,        # Local: 10s > 8s agent
                websocket_send_timeout=8,
                websocket_heartbeat_timeout=30,
                
                # Local agent timeouts (must be < WebSocket recv timeout)
                agent_execution_timeout=8,        # Local: fast development cycle
                agent_thinking_timeout=6,
                agent_tool_timeout=4,
                agent_completion_timeout=2,
                
                # Local HTTP timeouts
                http_request_timeout=10,
                http_connection_timeout=5,
                
                # Local test timeouts 
                test_default_timeout=15,
                test_integration_timeout=30,
                test_e2e_timeout=45
            )
    
    def get_websocket_recv_timeout(self) -> int:
        """Get WebSocket recv timeout for current environment.
        
        **CRITICAL FOR TESTS**: This is the timeout value that needs to replace
        hardcoded 3-second timeouts in staging test files.
        
        Returns:
            int: WebSocket recv timeout in seconds
        """
        return self.get_timeout_config().websocket_recv_timeout
    
    def get_agent_execution_timeout(self) -> int:
        """Get agent execution timeout for current environment.
        
        **CRITICAL FOR COORDINATION**: This timeout must be less than WebSocket
        recv timeout to maintain proper timeout hierarchy.
        
        Returns:
            int: Agent execution timeout in seconds
        """
        return self.get_timeout_config().agent_execution_timeout
    
    def get_timeout_hierarchy_info(self) -> Dict[str, Any]:
        """Get timeout hierarchy information for debugging/validation.
        
        Returns:
            Dict[str, Any]: Timeout hierarchy details and validation
        """
        config = self.get_timeout_config()
        
        # Validate hierarchy: WebSocket > Agent
        hierarchy_valid = config.websocket_recv_timeout > config.agent_execution_timeout
        
        return {
            "environment": self._environment.value,
            "websocket_recv_timeout": config.websocket_recv_timeout,
            "agent_execution_timeout": config.agent_execution_timeout,
            "hierarchy_valid": hierarchy_valid,
            "hierarchy_gap": config.websocket_recv_timeout - config.agent_execution_timeout,
            "business_impact": "$200K+ MRR reliability" if hierarchy_valid else "CRITICAL: Hierarchy broken",
            "config": config
        }
    
    def validate_timeout_hierarchy(self) -> bool:
        """Validate that timeout hierarchy is properly configured.
        
        **BUSINESS CRITICAL**: Ensures WebSocket timeouts > Agent timeouts
        to prevent premature timeout failures affecting $200K+ MRR.
        
        Returns:
            bool: True if hierarchy is valid
        """
        config = self.get_timeout_config()
        
        # Primary validation: WebSocket recv > Agent execution
        if config.websocket_recv_timeout <= config.agent_execution_timeout:
            return False
            
        # Secondary validations for complete hierarchy
        validations = [
            config.websocket_connection_timeout > config.agent_execution_timeout,
            config.websocket_send_timeout > config.agent_thinking_timeout,
            config.websocket_heartbeat_timeout > config.agent_completion_timeout,
            config.agent_execution_timeout > config.agent_thinking_timeout,
            config.agent_thinking_timeout > config.agent_tool_timeout,
            config.agent_tool_timeout > config.agent_completion_timeout
        ]
        
        return all(validations)


# Global timeout manager instance (SSOT) - lazy initialization for environment flexibility
_timeout_manager = None

def _get_timeout_manager() -> CloudNativeTimeoutManager:
    """Get or create timeout manager instance with current environment detection."""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = CloudNativeTimeoutManager()
    return _timeout_manager

# Convenience functions for easy access
def get_websocket_recv_timeout() -> int:
    """Get WebSocket recv timeout for current environment.
    
    **PRIMARY USE CASE**: Replace hardcoded 3-second timeouts in test files.
    
    Returns:
        int: WebSocket recv timeout in seconds (35s for staging, varies by env)
    """
    return _get_timeout_manager().get_websocket_recv_timeout()

def get_agent_execution_timeout() -> int:
    """Get agent execution timeout for current environment.
    
    **PRIMARY USE CASE**: Ensure agent timeouts coordinate with WebSocket timeouts.
    
    Returns:
        int: Agent execution timeout in seconds (30s for staging, varies by env)
    """
    return _get_timeout_manager().get_agent_execution_timeout()

def get_timeout_config() -> TimeoutConfig:
    """Get complete timeout configuration for current environment.
    
    Returns:
        TimeoutConfig: Complete timeout configuration
    """
    return _get_timeout_manager().get_timeout_config()

def validate_timeout_hierarchy() -> bool:
    """Validate timeout hierarchy for business reliability.
    
    **BUSINESS CRITICAL**: Prevents $200K+ MRR loss from timeout coordination issues.
    
    Returns:
        bool: True if timeout hierarchy is properly configured
    """
    return _get_timeout_manager().validate_timeout_hierarchy()

def get_timeout_hierarchy_info() -> Dict[str, Any]:
    """Get timeout hierarchy information for debugging.
    
    Returns:
        Dict[str, Any]: Complete hierarchy information and validation status
    """
    return _get_timeout_manager().get_timeout_hierarchy_info()

def reset_timeout_manager() -> None:
    """Reset timeout manager for testing purposes."""
    global _timeout_manager
    _timeout_manager = None

# Maintain backward compatibility
timeout_manager = _get_timeout_manager()

# Export all public interfaces
__all__ = [
    "TimeoutEnvironment",
    "TimeoutConfig", 
    "CloudNativeTimeoutManager",
    "timeout_manager",
    "get_websocket_recv_timeout",
    "get_agent_execution_timeout", 
    "get_timeout_config",
    "validate_timeout_hierarchy",
    "get_timeout_hierarchy_info"
]