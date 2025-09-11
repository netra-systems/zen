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
from typing import Optional

from shared.isolated_environment import get_env

class TimeoutTier(Enum):
    """Customer tiers for timeout configuration."""
    FREE = "free"
    EARLY = "early"
    MID = "mid"
    ENTERPRISE = "enterprise"
    PLATFORM = "platform"

class TimeoutEnvironment(Enum):
    """Environment types for timeout configuration."""
    LOCAL_DEVELOPMENT = "local"
    CLOUD_RUN_STAGING = "staging" 
    CLOUD_RUN_PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class TimeoutConfig:
    """Timeout configuration for specific environment and tier."""
    
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
    
    # Streaming timeouts (for enterprise tier) - moved after required fields
    streaming_timeout: Optional[int] = None
    streaming_phase_timeout: Optional[int] = None
    
    # Customer tier information
    tier: Optional[TimeoutTier] = None


class CloudNativeTimeoutManager:
    """SSOT manager for cloud-native timeout configurations.
    
    **CRITICAL BUSINESS REQUIREMENT**: Timeout hierarchy must ensure:
    - WebSocket timeouts > Agent execution timeouts (coordination)
    - Cloud Run environments get longer timeouts (cold starts)
    - Local development gets shorter timeouts (fast feedback)
    - Test environments get appropriate timeouts (stability vs speed)
    - Enterprise tier gets extended timeouts (300s streaming capability)
    """
    
    def __init__(self, default_tier: Optional[TimeoutTier] = None):
        """Initialize timeout manager with environment detection and tier support."""
        self._env = get_env()
        self._environment = self._detect_environment()
        self._default_tier = default_tier or TimeoutTier.FREE
        self._config_cache = {}
        self._tier_config_cache = {}
        
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
    
    def get_timeout_config(self, tier: Optional[TimeoutTier] = None) -> TimeoutConfig:
        """Get timeout configuration for current environment and customer tier.
        
        **CRITICAL HIERARCHY**: WebSocket timeouts > Agent timeouts for coordination
        **ENTERPRISE SUPPORT**: Tier-based timeout selection for streaming capabilities
        
        Args:
            tier: Customer tier for timeout selection (defaults to FREE)
        
        Returns:
            TimeoutConfig: Environment and tier-specific timeout configuration
        """
        # Always re-detect environment for testing flexibility
        current_env = self._detect_environment()
        selected_tier = tier or self._default_tier
        
        cache_key = (current_env, selected_tier)
        
        if cache_key not in self._tier_config_cache or current_env != self._environment:
            self._environment = current_env
            self._tier_config_cache[cache_key] = self._create_timeout_config(selected_tier)
            
        return self._tier_config_cache[cache_key]
    
    def _create_timeout_config(self, tier: TimeoutTier = TimeoutTier.FREE) -> TimeoutConfig:
        """Create timeout configuration for detected environment and customer tier.
        
        Args:
            tier: Customer tier for timeout selection
            
        Returns:
            TimeoutConfig: Configured timeouts for environment and tier
        """
        
        if self._environment == TimeoutEnvironment.CLOUD_RUN_STAGING:
            base_config = self._get_base_staging_config(tier)
            return self._apply_tier_enhancements(base_config, tier)
            
        elif self._environment == TimeoutEnvironment.CLOUD_RUN_PRODUCTION:
            base_config = self._get_base_production_config(tier)
            return self._apply_tier_enhancements(base_config, tier)
            
        elif self._environment == TimeoutEnvironment.TESTING:
            base_config = self._get_base_testing_config(tier)
            return self._apply_tier_enhancements(base_config, tier)
            
        else:  # LOCAL_DEVELOPMENT
            base_config = self._get_base_development_config(tier)
            return self._apply_tier_enhancements(base_config, tier)
    
    def _get_base_staging_config(self, tier: TimeoutTier) -> TimeoutConfig:
        """Get base staging configuration."""
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
            test_e2e_timeout=120,
            
            tier=tier
        )
    
    def _get_base_production_config(self, tier: TimeoutTier) -> TimeoutConfig:
        """Get base production configuration."""
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
            test_e2e_timeout=180,
            
            tier=tier
        )
    
    def _get_base_testing_config(self, tier: TimeoutTier) -> TimeoutConfig:
        """Get base testing configuration."""
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
            test_e2e_timeout=60,
            
            tier=tier
        )
    
    def _get_base_development_config(self, tier: TimeoutTier) -> TimeoutConfig:
        """Get base development configuration."""
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
            test_e2e_timeout=45,
            
            tier=tier
        )
    
    def _apply_tier_enhancements(self, base_config: TimeoutConfig, tier: TimeoutTier) -> TimeoutConfig:
        """Apply tier-specific enhancements to base configuration.
        
        **ENTERPRISE STREAMING**: Implements progressive timeout phases for enterprise customers:
        - Phase 1: 60s (initial response)
        - Phase 2: 120s (deeper analysis)
        - Phase 3: 180s (complex processing)
        - Phase 4: 240s (comprehensive research)
        - Phase 5: 300s (maximum enterprise capability)
        
        Args:
            base_config: Base timeout configuration
            tier: Customer tier for enhancements
            
        Returns:
            TimeoutConfig: Enhanced configuration with tier-specific features
        """
        if tier == TimeoutTier.ENTERPRISE:
            # Enterprise tier gets extended streaming capabilities
            return TimeoutConfig(
                # Enterprise WebSocket timeouts (MUST be > agent timeouts for hierarchy)
                websocket_connection_timeout=base_config.websocket_connection_timeout + 90,  # Extended
                websocket_recv_timeout=360,         # CRITICAL: Must be > 300s agent timeout
                websocket_send_timeout=base_config.websocket_send_timeout + 30,
                websocket_heartbeat_timeout=base_config.websocket_heartbeat_timeout + 120,
                
                # Enterprise agent execution timeouts (300s maximum capability)
                agent_execution_timeout=300,        # Enterprise: 300s streaming capability
                agent_thinking_timeout=min(base_config.agent_thinking_timeout * 2, 60),
                agent_tool_timeout=min(base_config.agent_tool_timeout * 2, 90),
                agent_completion_timeout=min(base_config.agent_completion_timeout * 2, 30),
                
                # Enterprise streaming configuration
                streaming_timeout=300,              # Maximum streaming duration
                streaming_phase_timeout=60,         # Per-phase timeout (5 phases)
                
                # Enterprise HTTP timeouts (extended)
                http_request_timeout=base_config.http_request_timeout + 30,
                http_connection_timeout=base_config.http_connection_timeout + 10,
                
                # Test timeouts (unchanged for enterprise)
                test_default_timeout=base_config.test_default_timeout,
                test_integration_timeout=base_config.test_integration_timeout,
                test_e2e_timeout=base_config.test_e2e_timeout,
                
                tier=tier
            )
        
        elif tier == TimeoutTier.PLATFORM:
            # Platform tier gets moderate enhancements
            return TimeoutConfig(
                # Platform WebSocket timeouts (MUST be > agent timeouts for hierarchy)
                websocket_connection_timeout=base_config.websocket_connection_timeout + 50,  # Extended
                websocket_recv_timeout=150,         # CRITICAL: Must be > 120s agent timeout
                websocket_send_timeout=base_config.websocket_send_timeout + 20,
                websocket_heartbeat_timeout=base_config.websocket_heartbeat_timeout + 60,
                
                # Platform agent execution timeouts (120s capability)
                agent_execution_timeout=120,        # Platform: 120s for complex tasks
                agent_thinking_timeout=min(base_config.agent_thinking_timeout + 15, 45),
                agent_tool_timeout=min(base_config.agent_tool_timeout + 15, 60),
                agent_completion_timeout=min(base_config.agent_completion_timeout + 10, 20),
                
                # Platform streaming configuration
                streaming_timeout=120,              # Moderate streaming capability
                streaming_phase_timeout=30,         # Per-phase timeout (4 phases)
                
                # Platform HTTP timeouts
                http_request_timeout=base_config.http_request_timeout + 15,
                http_connection_timeout=base_config.http_connection_timeout + 5,
                
                # Test timeouts (unchanged for platform)
                test_default_timeout=base_config.test_default_timeout,
                test_integration_timeout=base_config.test_integration_timeout,
                test_e2e_timeout=base_config.test_e2e_timeout,
                
                tier=tier
            )
        
        elif tier == TimeoutTier.MID:
            # Mid tier gets small enhancements
            return TimeoutConfig(
                # Mid WebSocket timeouts (MUST be > agent timeouts for hierarchy)
                websocket_connection_timeout=base_config.websocket_connection_timeout + 30,  # Extended
                websocket_recv_timeout=90,          # CRITICAL: Must be > 60s agent timeout
                websocket_send_timeout=base_config.websocket_send_timeout + 10,
                websocket_heartbeat_timeout=base_config.websocket_heartbeat_timeout + 30,
                
                # Mid agent execution timeouts (60s capability)
                agent_execution_timeout=60,         # Mid: 60s for moderate tasks
                agent_thinking_timeout=min(base_config.agent_thinking_timeout + 5, 30),
                agent_tool_timeout=min(base_config.agent_tool_timeout + 10, 35),
                agent_completion_timeout=min(base_config.agent_completion_timeout + 5, 15),
                
                # Mid streaming configuration
                streaming_timeout=60,               # Basic streaming capability
                streaming_phase_timeout=20,         # Per-phase timeout (3 phases)
                
                # Mid HTTP timeouts
                http_request_timeout=base_config.http_request_timeout + 10,
                http_connection_timeout=base_config.http_connection_timeout + 3,
                
                # Test timeouts (unchanged for mid)
                test_default_timeout=base_config.test_default_timeout,
                test_integration_timeout=base_config.test_integration_timeout,
                test_e2e_timeout=base_config.test_e2e_timeout,
                
                tier=tier
            )
        
        else:  # FREE, EARLY tiers use base configuration
            # Set tier information but no enhancements
            base_config.tier = tier
            return base_config
    
    def get_streaming_timeout(self, tier: Optional[TimeoutTier] = None) -> int:
        """Get streaming timeout for customer tier.
        
        **ENTERPRISE STREAMING**: Returns tier-appropriate streaming timeout:
        - Enterprise: 300s (5-minute streaming capability)
        - Platform: 120s (2-minute streaming capability)  
        - Mid: 60s (1-minute streaming capability)
        - Early/Free: Uses agent_execution_timeout
        
        Args:
            tier: Customer tier for timeout selection
            
        Returns:
            int: Streaming timeout in seconds
        """
        config = self.get_timeout_config(tier)
        return config.streaming_timeout or config.agent_execution_timeout
    
    def get_streaming_phase_timeout(self, tier: Optional[TimeoutTier] = None) -> int:
        """Get per-phase streaming timeout for progressive execution.
        
        **PROGRESSIVE PHASES**: Enterprise tier supports 5 progressive phases:
        - Phase 1: Initial response (60s)
        - Phase 2: Deeper analysis (60s) 
        - Phase 3: Complex processing (60s)
        - Phase 4: Comprehensive research (60s)
        - Phase 5: Final synthesis (60s)
        
        Args:
            tier: Customer tier for timeout selection
            
        Returns:
            int: Per-phase timeout in seconds
        """
        config = self.get_timeout_config(tier)
        return config.streaming_phase_timeout or (config.agent_execution_timeout // 3)
    
    def get_websocket_recv_timeout(self) -> int:
        """Get WebSocket recv timeout for current environment.
        
        **CRITICAL FOR TESTS**: This is the timeout value that needs to replace
        hardcoded 3-second timeouts in staging test files.
        
        Returns:
            int: WebSocket recv timeout in seconds
        """
        return self.get_timeout_config().websocket_recv_timeout
    
    def get_agent_execution_timeout(self, tier: Optional[TimeoutTier] = None) -> int:
        """Get agent execution timeout for current environment and customer tier.
        
        **CRITICAL FOR COORDINATION**: This timeout must be less than WebSocket
        recv timeout to maintain proper timeout hierarchy.
        **ENTERPRISE STREAMING**: Enterprise tier supports extended execution times
        
        Args:
            tier: Customer tier for timeout selection
        
        Returns:
            int: Agent execution timeout in seconds (up to 300s for enterprise)
        """
        return self.get_timeout_config(tier).agent_execution_timeout
    
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
def get_websocket_recv_timeout(tier: Optional[TimeoutTier] = None) -> int:
    """Get WebSocket recv timeout for current environment and customer tier.
    
    **PRIMARY USE CASE**: Replace hardcoded 3-second timeouts in test files.
    **ENTERPRISE SUPPORT**: Tier-based timeout selection for streaming
    
    Args:
        tier: Customer tier for timeout selection
    
    Returns:
        int: WebSocket recv timeout in seconds (varies by env and tier)
    """
    return _get_timeout_manager().get_timeout_config(tier).websocket_recv_timeout

def get_agent_execution_timeout(tier: Optional[TimeoutTier] = None) -> int:
    """Get agent execution timeout for current environment and customer tier.
    
    **PRIMARY USE CASE**: Ensure agent timeouts coordinate with WebSocket timeouts.
    **ENTERPRISE STREAMING**: Up to 300s for enterprise tier
    
    Args:
        tier: Customer tier for timeout selection
    
    Returns:
        int: Agent execution timeout in seconds (up to 300s for enterprise)
    """
    return _get_timeout_manager().get_agent_execution_timeout(tier)

def get_timeout_config(tier: Optional[TimeoutTier] = None) -> TimeoutConfig:
    """Get complete timeout configuration for current environment and customer tier.
    
    **TIER SUPPORT**: Customer tier determines available streaming capabilities
    
    Args:
        tier: Customer tier for timeout selection
    
    Returns:
        TimeoutConfig: Complete timeout configuration with tier enhancements
    """
    return _get_timeout_manager().get_timeout_config(tier)

def get_streaming_timeout(tier: Optional[TimeoutTier] = None) -> int:
    """Get streaming timeout for customer tier.
    
    **ENTERPRISE STREAMING**: Tier-appropriate streaming timeout capability
    
    Args:
        tier: Customer tier for timeout selection
        
    Returns:
        int: Streaming timeout in seconds (up to 300s for enterprise)
    """
    return _get_timeout_manager().get_streaming_timeout(tier)

def get_streaming_phase_timeout(tier: Optional[TimeoutTier] = None) -> int:
    """Get per-phase streaming timeout for progressive execution.
    
    **PROGRESSIVE PHASES**: Enterprise tier supports 5 progressive phases
    
    Args:
        tier: Customer tier for timeout selection
        
    Returns:
        int: Per-phase timeout in seconds
    """
    return _get_timeout_manager().get_streaming_phase_timeout(tier)

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
    "TimeoutTier",
    "TimeoutEnvironment",
    "TimeoutConfig", 
    "CloudNativeTimeoutManager",
    "timeout_manager",
    "get_websocket_recv_timeout",
    "get_agent_execution_timeout", 
    "get_timeout_config",
    "get_streaming_timeout",
    "get_streaming_phase_timeout",
    "validate_timeout_hierarchy",
    "get_timeout_hierarchy_info"
]