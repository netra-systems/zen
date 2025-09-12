"""Cloud-Native Timeout Configuration - Single Source of Truth

**BUSINESS CONTEXT**: Priority 3 timeout hierarchy fixes to restore $200K+ MRR business value
by aligning timeouts for cloud-native GCP Cloud Run environment.

**ROOT CAUSE**: WebSocket (3s)  ->  Agent (15s) timeout causing premature failures
**REQUIRED**: Cloud-native timeout hierarchy with 35s WebSocket  ->  30s Agent coordination
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
import logging
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
        """Initialize timeout manager with environment detection and tier support.
        
        **Issue #586 Enhancement**: Comprehensive startup logging for environment detection debugging.
        """
        logger = logging.getLogger(__name__)
        
        self._env = get_env()
        self._environment = self._detect_environment()
        self._default_tier = default_tier or TimeoutTier.FREE
        self._config_cache = {}
        self._tier_config_cache = {}
        
        # **Issue #586**: Log comprehensive startup information for debugging
        self._log_startup_environment_info(logger)
        
    def _detect_environment(self) -> TimeoutEnvironment:
        """Detect current environment for timeout configuration.
        
        **Issue #586 Fix**: Enhanced GCP environment detection using multiple markers
        to ensure staging environment is properly recognized for timeout configuration.
        """
        # Always refresh environment to handle dynamic changes during testing
        self._env = get_env()
        
        logger = logging.getLogger(__name__)
        
        # **Issue #586 Enhancement**: Multi-marker GCP environment detection
        gcp_markers = self._detect_gcp_environment_markers()
        
        # PRIORITY 3 FIX: Check direct os.environ first for explicit ENVIRONMENT setting
        # This allows testing to override isolated environment defaults
        direct_env = os.environ.get("ENVIRONMENT")
        if direct_env:
            env_name = direct_env.lower()
        else:
            env_name = self._env.get("ENVIRONMENT", "development").lower()
        
        # Log environment detection process for debugging
        logger.info(f"Environment detection - Direct: {direct_env}, Env name: {env_name}, "
                   f"GCP markers: {gcp_markers}")
        
        # **Issue #586**: Enhanced GCP Cloud Run detection
        if gcp_markers['is_gcp_cloud_run']:
            # Prioritize explicit environment setting, then use project ID as confirmation/fallback
            if env_name == "staging" and (gcp_markers['project_id'] is None or 'staging' in gcp_markers['project_id']):
                logger.info(f"Detected GCP Cloud Run STAGING environment - Env: {env_name}, Project: {gcp_markers['project_id']}, "
                           f"Service: {gcp_markers['service_name']}")
                return TimeoutEnvironment.CLOUD_RUN_STAGING
            elif env_name == "production" and (gcp_markers['project_id'] is None or 'production' in gcp_markers['project_id']):
                logger.info(f"Detected GCP Cloud Run PRODUCTION environment - Env: {env_name}, Project: {gcp_markers['project_id']}, "
                           f"Service: {gcp_markers['service_name']}")
                return TimeoutEnvironment.CLOUD_RUN_PRODUCTION
            elif gcp_markers['project_id'] == 'netra-staging':
                logger.info(f"Detected GCP Cloud Run STAGING environment via project ID - Project: {gcp_markers['project_id']}, "
                           f"Service: {gcp_markers['service_name']}")
                return TimeoutEnvironment.CLOUD_RUN_STAGING
            elif gcp_markers['project_id'] == 'netra-production':
                logger.info(f"Detected GCP Cloud Run PRODUCTION environment via project ID - Project: {gcp_markers['project_id']}, "
                           f"Service: {gcp_markers['service_name']}")
                return TimeoutEnvironment.CLOUD_RUN_PRODUCTION
            else:
                # GCP detected but environment unclear - use project ID as fallback
                if 'staging' in (gcp_markers['project_id'] or ''):
                    logger.warning(f"GCP staging detected via project ID fallback: {gcp_markers['project_id']}")
                    return TimeoutEnvironment.CLOUD_RUN_STAGING
                elif 'production' in (gcp_markers['project_id'] or ''):
                    logger.warning(f"GCP production detected via project ID fallback: {gcp_markers['project_id']}")
                    return TimeoutEnvironment.CLOUD_RUN_PRODUCTION
                else:
                    # Unknown GCP environment - default to staging for safer timeouts
                    logger.warning(f"Unknown GCP environment detected, defaulting to staging. "
                                 f"Project: {gcp_markers['project_id']}, Service: {gcp_markers['service_name']}")
                    return TimeoutEnvironment.CLOUD_RUN_STAGING
        
        # Check for testing environment markers (but allow explicit overrides)
        if not direct_env and (self._env.get("PYTEST_CURRENT_TEST") or 
            self._env.get("TESTING") == "true" or 
            env_name == "testing"):
            logger.info("Detected TESTING environment")
            return TimeoutEnvironment.TESTING
            
        # Check for cloud environments via environment name
        if env_name == "staging":
            logger.info("Detected STAGING environment via environment name")
            return TimeoutEnvironment.CLOUD_RUN_STAGING
        elif env_name == "production":
            logger.info("Detected PRODUCTION environment via environment name")
            return TimeoutEnvironment.CLOUD_RUN_PRODUCTION
        elif env_name == "testing":
            logger.info("Detected TESTING environment via environment name")
            return TimeoutEnvironment.TESTING
        else:
            logger.info(f"Detected LOCAL_DEVELOPMENT environment (default) - env_name: {env_name}")
            return TimeoutEnvironment.LOCAL_DEVELOPMENT
    
    def _detect_gcp_environment_markers(self) -> Dict[str, Any]:
        """Detect GCP Cloud Run environment using multiple markers.
        
        **Issue #586 Solution**: Implements redundant detection with multiple GCP markers
        to ensure reliable environment detection even when some markers are missing.
        
        Returns:
            Dict containing GCP environment detection results
        """
        # GCP Cloud Run environment markers
        k_service = self._env.get("K_SERVICE") or os.environ.get("K_SERVICE")
        k_revision = self._env.get("K_REVISION") or os.environ.get("K_REVISION")
        k_configuration = self._env.get("K_CONFIGURATION") or os.environ.get("K_CONFIGURATION")
        
        # GCP project identification
        gcp_project_id = (self._env.get("GCP_PROJECT_ID") or 
                         os.environ.get("GCP_PROJECT_ID") or
                         self._env.get("GOOGLE_CLOUD_PROJECT") or 
                         os.environ.get("GOOGLE_CLOUD_PROJECT"))
        
        # Additional GCP markers
        cloud_run_service = (self._env.get("CLOUD_RUN_SERVICE") or 
                           os.environ.get("CLOUD_RUN_SERVICE"))
        gae_env = self._env.get("GAE_ENV") or os.environ.get("GAE_ENV")
        function_name = self._env.get("FUNCTION_NAME") or os.environ.get("FUNCTION_NAME")
        
        # Cloud Run detection logic
        is_cloud_run = bool(k_service)  # K_SERVICE is the primary Cloud Run marker
        is_gae = bool(gae_env)
        is_cloud_function = bool(function_name)
        
        # Determine if we're in GCP (any GCP service)
        is_gcp = is_cloud_run or is_gae or is_cloud_function or bool(gcp_project_id)
        
        # Specifically detect Cloud Run (which is what we care about for Issue #586)
        is_gcp_cloud_run = is_cloud_run
        
        markers = {
            'is_gcp': is_gcp,
            'is_gcp_cloud_run': is_gcp_cloud_run,
            'is_gae': is_gae,
            'is_cloud_function': is_cloud_function,
            'project_id': gcp_project_id,
            'service_name': k_service or cloud_run_service,
            'revision': k_revision,
            'configuration': k_configuration,
            'markers_detected': {
                'K_SERVICE': bool(k_service),
                'K_REVISION': bool(k_revision),
                'GCP_PROJECT_ID': bool(gcp_project_id),
                'CLOUD_RUN_SERVICE': bool(cloud_run_service),
                'GAE_ENV': bool(gae_env),
                'FUNCTION_NAME': bool(function_name)
            }
        }
        
        return markers
    
    def _calculate_cold_start_buffer(self, environment: str, gcp_markers: Dict[str, Any]) -> float:
        """Calculate cold start buffer for Cloud Run deployments.
        
        **Issue #586 Solution**: Implements cold start buffer calculations for GCP Cloud Run
        to prevent timeout failures during service startup and cold start conditions.
        
        Args:
            environment: Environment name (staging, production, development)
            gcp_markers: GCP environment markers from _detect_gcp_environment_markers()
            
        Returns:
            float: Cold start buffer in seconds
        """
        if not gcp_markers.get('is_gcp_cloud_run'):
            return 0.0  # No buffer needed for non-Cloud Run environments
        
        # Base cold start buffers by environment
        base_buffers = {
            'staging': 3.0,     # Staging cold start overhead
            'production': 5.0,  # Production cold start overhead (more conservative)
            'development': 2.0  # Local development with Cloud Run
        }
        
        base_buffer = base_buffers.get(environment.lower(), 2.0)
        
        # Additional buffer for complex services
        service_name = gcp_markers.get('service_name', '').lower()
        if 'backend' in service_name:
            base_buffer += 1.0  # Backend services need more time for initialization
        
        # Additional buffer for high-tier services requiring longer startup
        project_id = gcp_markers.get('project_id', '').lower()
        if 'production' in project_id:
            base_buffer += 1.0  # Production gets extra safety buffer
        
        logger = logging.getLogger(__name__)
        logger.debug(f"Cold start buffer calculated: {base_buffer}s for {environment} "
                    f"(service: {service_name}, project: {project_id})")
        
        return base_buffer
    
    def _log_startup_environment_info(self, logger: logging.Logger) -> None:
        """Log comprehensive environment detection information at startup.
        
        **Issue #586**: Provides detailed logging to debug environment detection issues
        and validate that the correct timeout configuration is being used.
        """
        try:
            # Get current environment detection results
            gcp_markers = self._detect_gcp_environment_markers()
            config = self.get_timeout_config()
            
            logger.info("=" * 80)
            logger.info("CloudNativeTimeoutManager - Issue #586 Enhanced Environment Detection")
            logger.info("=" * 80)
            
            # Environment Detection Summary
            logger.info(f"🌍 DETECTED ENVIRONMENT: {self._environment.value}")
            logger.info(f"🎯 DEFAULT TIER: {self._default_tier.value}")
            logger.info(f"⏱️  WEBSOCKET RECV TIMEOUT: {config.websocket_recv_timeout}s")
            logger.info(f"🤖 AGENT EXECUTION TIMEOUT: {config.agent_execution_timeout}s")
            
            # GCP Environment Markers
            logger.info(f"☁️  GCP CLOUD RUN DETECTED: {gcp_markers['is_gcp_cloud_run']}")
            if gcp_markers['is_gcp_cloud_run']:
                logger.info(f"   📋 Project ID: {gcp_markers['project_id']}")
                logger.info(f"   🏷️  Service Name: {gcp_markers['service_name']}")
                logger.info(f"   📝 Revision: {gcp_markers['revision']}")
            
            # Environment Variables Summary
            direct_env = os.environ.get("ENVIRONMENT")
            isolated_env = self._env.get("ENVIRONMENT", "not_set")
            logger.info(f"🔧 ENVIRONMENT (direct): {direct_env}")
            logger.info(f"🔧 ENVIRONMENT (isolated): {isolated_env}")
            
            # Marker Detection Details
            logger.info("🔍 GCP MARKER DETECTION:")
            for marker, detected in gcp_markers['markers_detected'].items():
                status = "✅" if detected else "❌"
                logger.info(f"   {status} {marker}: {detected}")
            
            # Timeout Hierarchy Validation
            hierarchy_valid = config.websocket_recv_timeout > config.agent_execution_timeout
            hierarchy_status = "✅ VALID" if hierarchy_valid else "❌ BROKEN"
            gap = config.websocket_recv_timeout - config.agent_execution_timeout
            logger.info(f"⚖️  TIMEOUT HIERARCHY: {hierarchy_status} (gap: {gap}s)")
            
            # Business Impact Assessment
            if hierarchy_valid:
                logger.info("💰 BUSINESS IMPACT: $200K+ MRR protected with valid timeout hierarchy")
            else:
                logger.error("💰 BUSINESS IMPACT: CRITICAL - Timeout hierarchy broken, $200K+ MRR at risk")
            
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Failed to log startup environment info: {e}", exc_info=True)
    
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
        """Get base staging configuration with Issue #586 cold start buffer integration."""
        # Calculate cold start buffer for Cloud Run staging environment
        gcp_markers = self._detect_gcp_environment_markers()
        cold_start_buffer = self._calculate_cold_start_buffer('staging', gcp_markers)
        
        # Base timeouts with cold start buffer applied
        base_websocket_recv = 15.0  # Issue #586 remedy: 15s base timeout
        base_agent_execution = 12.0  # Must be < WebSocket recv timeout
        
        # Apply cold start buffer
        websocket_recv_with_buffer = base_websocket_recv + cold_start_buffer
        agent_execution_with_buffer = base_agent_execution + cold_start_buffer
        
        return TimeoutConfig(
            # ISSUE #586 FIX: WebSocket timeouts with cold start buffer for Cloud Run staging
            websocket_connection_timeout=60,                      # Connection establishment with buffer
            websocket_recv_timeout=int(websocket_recv_with_buffer),  # 15s base + cold start buffer
            websocket_send_timeout=12 + int(cold_start_buffer),   # Send timeout with buffer
            websocket_heartbeat_timeout=90,                       # Heartbeat remains high
            
            # Agent execution timeouts (must be < WebSocket recv timeout) with cold start buffer
            agent_execution_timeout=int(agent_execution_with_buffer),  # 12s base + cold start buffer
            agent_thinking_timeout=10 + int(cold_start_buffer),   # Thinking with buffer
            agent_tool_timeout=8 + int(cold_start_buffer),        # Tool execution with buffer
            agent_completion_timeout=6 + int(cold_start_buffer),  # Completion with buffer
            
            # HTTP timeouts for Cloud Run with cold start consideration
            http_request_timeout=30,
            http_connection_timeout=15,
            
            # Test timeouts for staging environment - Issue #586 optimized
            test_default_timeout=30 + int(cold_start_buffer),     # INCREASED for Cloud Run tests
            test_integration_timeout=45 + int(cold_start_buffer),
            test_e2e_timeout=60 + int(cold_start_buffer),
            
            tier=tier
        )
    
    def _get_base_production_config(self, tier: TimeoutTier) -> TimeoutConfig:
        """Get base production configuration with Issue #586 cold start buffer integration."""
        # Calculate cold start buffer for Cloud Run production environment
        gcp_markers = self._detect_gcp_environment_markers()
        cold_start_buffer = self._calculate_cold_start_buffer('production', gcp_markers)
        
        # Base timeouts with conservative production values
        base_websocket_recv = 30.0  # Production base timeout
        base_agent_execution = 25.0  # Must be < WebSocket recv timeout
        
        # Apply cold start buffer
        websocket_recv_with_buffer = base_websocket_recv + cold_start_buffer
        agent_execution_with_buffer = base_agent_execution + cold_start_buffer
        
        return TimeoutConfig(
            # ISSUE #586 FIX: Production WebSocket timeouts with cold start buffer
            websocket_connection_timeout=90,                      # Conservative connection timeout
            websocket_recv_timeout=int(websocket_recv_with_buffer),  # 30s base + cold start buffer
            websocket_send_timeout=25 + int(cold_start_buffer),   # Send timeout with buffer
            websocket_heartbeat_timeout=120,                      # Long heartbeat for stability
            
            # Production agent timeouts (must be < WebSocket recv timeout) with cold start buffer
            agent_execution_timeout=int(agent_execution_with_buffer),  # 25s base + cold start buffer
            agent_thinking_timeout=20 + int(cold_start_buffer),   # Thinking with buffer
            agent_tool_timeout=18 + int(cold_start_buffer),       # Tool execution with buffer
            agent_completion_timeout=15 + int(cold_start_buffer), # Completion with buffer
            
            # Production HTTP timeouts
            http_request_timeout=45,
            http_connection_timeout=20,
            
            # Production test timeouts (if tests run in prod) with cold start buffer
            test_default_timeout=90 + int(cold_start_buffer),
            test_integration_timeout=150 + int(cold_start_buffer),
            test_e2e_timeout=180 + int(cold_start_buffer),
            
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
        
        **Issue #586 Enhancement**: Includes comprehensive environment detection information
        for debugging environment detection issues.
        
        Returns:
            Dict[str, Any]: Timeout hierarchy details and validation with enhanced diagnostics
        """
        config = self.get_timeout_config()
        gcp_markers = self._detect_gcp_environment_markers()
        
        # Validate hierarchy: WebSocket > Agent
        hierarchy_valid = config.websocket_recv_timeout > config.agent_execution_timeout
        
        # Environment detection diagnostics
        direct_env = os.environ.get("ENVIRONMENT")
        isolated_env = self._env.get("ENVIRONMENT", "not_set")
        
        return {
            "environment": self._environment.value,
            "websocket_recv_timeout": config.websocket_recv_timeout,
            "agent_execution_timeout": config.agent_execution_timeout,
            "hierarchy_valid": hierarchy_valid,
            "hierarchy_gap": config.websocket_recv_timeout - config.agent_execution_timeout,
            "business_impact": "$200K+ MRR reliability" if hierarchy_valid else "CRITICAL: Hierarchy broken",
            "config": config,
            # Issue #586 enhanced diagnostics
            "environment_detection": {
                "detected_environment": self._environment.value,
                "environment_sources": {
                    "direct": direct_env,
                    "isolated": isolated_env
                },
                "gcp_detection": {
                    "is_gcp_cloud_run": gcp_markers['is_gcp_cloud_run'],
                    "project_id": gcp_markers['project_id'],
                    "service_name": gcp_markers['service_name'],
                    "markers_detected": gcp_markers['markers_detected']
                }
            },
            "tier_info": {
                "default_tier": self._default_tier.value,
                "config_tier": config.tier.value if config.tier else None,
                "streaming_timeout": config.streaming_timeout,
                "streaming_phase_timeout": config.streaming_phase_timeout
            }
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
    
    **Issue #586**: Includes enhanced environment detection diagnostics.
    
    Returns:
        Dict[str, Any]: Complete hierarchy information and validation status
    """
    return _get_timeout_manager().get_timeout_hierarchy_info()

def get_environment_detection_info() -> Dict[str, Any]:
    """Get detailed environment detection information for Issue #586 debugging.
    
    **Issue #586 Solution**: Provides comprehensive environment detection diagnostics
    to help debug and validate GCP environment detection.
    
    Returns:
        Dict[str, Any]: Complete environment detection diagnostics
    """
    manager = _get_timeout_manager()
    gcp_markers = manager._detect_gcp_environment_markers()
    
    return {
        "detected_environment": manager._environment.value,
        "environment_sources": {
            "direct": os.environ.get("ENVIRONMENT"),
            "isolated": manager._env.get("ENVIRONMENT", "not_set")
        },
        "gcp_markers": gcp_markers,
        "timeout_values": {
            "websocket_recv_timeout": manager.get_websocket_recv_timeout(),
            "agent_execution_timeout": manager.get_agent_execution_timeout()
        },
        "hierarchy_validation": manager.validate_timeout_hierarchy()
    }

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
    "get_timeout_hierarchy_info",
    "get_environment_detection_info"  # Issue #586
]