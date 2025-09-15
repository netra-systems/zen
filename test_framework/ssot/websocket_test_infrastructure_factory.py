"""
Single Source of Truth (SSOT) WebSocket Test Infrastructure Factory

This module provides the unified WebSocketTestInfrastructureFactory that serves as the
central factory for creating ALL WebSocket test infrastructure components across
the entire test suite. It orchestrates the creation and configuration of all
WebSocket testing utilities in a coordinated and consistent manner.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Provides centralized factory for creating WebSocket test infrastructure components
that support $500K+ ARR chat functionality through comprehensive and reliable testing.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for WebSocket test infrastructure creation.
ALL WebSocket test infrastructure must be created through this factory for SSOT compliance.
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union, Tuple
from datetime import datetime

# Import SSOT environment management
from shared.isolated_environment import get_env

# Import all WebSocket test infrastructure components
from .websocket import WebSocketTestUtility, WebSocketTestClient
from .websocket_auth_helper import WebSocketAuthHelper, WebSocketAuthConfig, TestUserContext
from .websocket_bridge_test_helper import WebSocketBridgeTestHelper, BridgeTestConfig, AgentExecutionContext
from .communication_metrics_collector import CommunicationMetricsCollector, MetricType, PerformanceMetrics

logger = logging.getLogger(__name__)


@dataclass
class InfrastructureConfig:
    """Configuration for WebSocket test infrastructure."""
    factory_id: str
    mock_mode: bool = True
    enable_metrics_collection: bool = True
    enable_authentication: bool = True
    enable_agent_bridge: bool = True
    default_timeout: float = 30.0
    max_concurrent_clients: int = 10
    environment_isolation: bool = True
    
    @classmethod
    def from_environment(cls, env=None) -> 'InfrastructureConfig':
        """Create infrastructure config from environment variables."""
        env = env or get_env()
        
        factory_id = f"wsinfra_{uuid.uuid4().hex[:8]}"
        
        return cls(
            factory_id=factory_id,
            mock_mode=env.get("WEBSOCKET_INFRASTRUCTURE_MOCK_MODE", "true").lower() == "true",
            enable_metrics_collection=env.get("WEBSOCKET_ENABLE_METRICS", "true").lower() == "true",
            enable_authentication=env.get("WEBSOCKET_ENABLE_AUTH", "true").lower() == "true",
            enable_agent_bridge=env.get("WEBSOCKET_ENABLE_BRIDGE", "true").lower() == "true",
            default_timeout=float(env.get("WEBSOCKET_DEFAULT_TIMEOUT", "30.0")),
            max_concurrent_clients=int(env.get("WEBSOCKET_MAX_CLIENTS", "10")),
            environment_isolation=env.get("WEBSOCKET_ENV_ISOLATION", "true").lower() == "true"
        )


@dataclass
class TestInfrastructure:
    """Complete WebSocket test infrastructure bundle."""
    factory_id: str
    websocket_utility: WebSocketTestUtility
    auth_helper: Optional[WebSocketAuthHelper]
    bridge_helper: Optional[WebSocketBridgeTestHelper]  
    metrics_collector: Optional[CommunicationMetricsCollector]
    config: InfrastructureConfig
    created_at: datetime
    
    async def cleanup(self):
        """Clean up all infrastructure components."""
        cleanup_tasks = []
        
        if self.auth_helper:
            cleanup_tasks.append(self.auth_helper.cleanup())
        
        if self.bridge_helper:
            cleanup_tasks.append(self.bridge_helper.cleanup())
            
        if self.metrics_collector:
            cleanup_tasks.append(self.metrics_collector.cleanup())
            
        if self.websocket_utility:
            cleanup_tasks.append(self.websocket_utility.cleanup())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        logger.debug(f"Test infrastructure cleanup completed [{self.factory_id}]")


class WebSocketTestInfrastructureFactory:
    """
    Single Source of Truth (SSOT) WebSocket test infrastructure factory.
    
    This factory provides centralized creation and management of all WebSocket
    test infrastructure components, ensuring consistent configuration and
    coordinated lifecycle management across the entire test suite.
    
    Components Created:
    - WebSocketTestUtility: Core WebSocket testing functionality
    - WebSocketAuthHelper: Authentication and user context testing
    - WebSocketBridgeTestHelper: Agent-WebSocket integration testing
    - CommunicationMetricsCollector: Performance and metrics tracking
    - Coordinated test environments with proper isolation
    
    Features:
    - SSOT compliance with unified component creation
    - Environment-aware configuration management
    - Automatic component coordination and dependency injection
    - Lifecycle management for all created infrastructure
    - Performance monitoring and metrics collection
    - Multi-user testing support with proper isolation
    - Business-critical Golden Path testing support
    
    Usage:
        # Create complete infrastructure
        async with WebSocketTestInfrastructureFactory() as factory:
            infrastructure = await factory.create_websocket_test_infrastructure()
            
        # Create specific components
        auth_helper = await factory.create_auth_helper()
        bridge_helper = await factory.create_websocket_bridge()
        metrics_collector = await factory.create_communication_metrics()
    """
    
    def __init__(self, config: Optional[InfrastructureConfig] = None, env=None):
        """
        Initialize WebSocket test infrastructure factory.
        
        Args:
            config: Optional infrastructure configuration
            env: Optional environment manager instance
        """
        self.env = env or get_env()
        self.config = config or InfrastructureConfig.from_environment(self.env)
        self.factory_id = self.config.factory_id
        
        # Component tracking
        self.created_infrastructures: Dict[str, TestInfrastructure] = {}
        self.created_auth_helpers: Dict[str, WebSocketAuthHelper] = {}
        self.created_bridge_helpers: Dict[str, WebSocketBridgeTestHelper] = {}
        self.created_metrics_collectors: Dict[str, CommunicationMetricsCollector] = {}
        self.created_websocket_utilities: Dict[str, WebSocketTestUtility] = {}
        
        # Factory state
        self.is_initialized = False
        
        logger.debug(f"WebSocketTestInfrastructureFactory initialized [{self.factory_id}] (mock_mode={self.config.mock_mode})")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup_all()
    
    async def initialize(self):
        """Initialize the infrastructure factory."""
        if self.is_initialized:
            return
        
        try:
            # Verify environment configuration
            await self._verify_environment_config()
            
            # Initialize factory-level resources
            await self._initialize_factory_resources()
            
            self.is_initialized = True
            logger.info(f"WebSocketTestInfrastructureFactory initialized [{self.factory_id}]")
            
        except Exception as e:
            logger.error(f"Infrastructure factory initialization failed: {e}")
            raise
    
    async def _verify_environment_config(self):
        """Verify environment configuration for WebSocket testing."""
        # Check required environment variables are available
        required_env_check = [
            ("WEBSOCKET_TEST_URL", "WebSocket test server URL"),
            ("JWT_SECRET_KEY", "JWT secret for authentication testing")
        ]
        
        for env_var, description in required_env_check:
            if not self.env.get(env_var):
                logger.warning(f"Environment variable {env_var} not set - {description} may use defaults")
    
    async def _initialize_factory_resources(self):
        """Initialize factory-level resources."""
        # Placeholder for factory-level initialization
        # Could include shared connection pools, configuration caching, etc.
        pass
    
    async def create_websocket_test_infrastructure(self, 
                                                 infrastructure_id: Optional[str] = None,
                                                 custom_config: Optional[Dict[str, Any]] = None) -> TestInfrastructure:
        """
        Create a complete WebSocket test infrastructure with all components.
        
        Args:
            infrastructure_id: Optional infrastructure identifier
            custom_config: Optional custom configuration overrides
            
        Returns:
            TestInfrastructure with all configured components
        """
        if not self.is_initialized:
            await self.initialize()
        
        infrastructure_id = infrastructure_id or f"infra_{uuid.uuid4().hex[:8]}"
        
        # Apply custom configuration if provided
        effective_config = self.config
        if custom_config:
            # Create new config with custom overrides
            config_dict = {
                "factory_id": effective_config.factory_id,
                "mock_mode": custom_config.get("mock_mode", effective_config.mock_mode),
                "enable_metrics_collection": custom_config.get("enable_metrics_collection", effective_config.enable_metrics_collection),
                "enable_authentication": custom_config.get("enable_authentication", effective_config.enable_authentication),
                "enable_agent_bridge": custom_config.get("enable_agent_bridge", effective_config.enable_agent_bridge),
                "default_timeout": custom_config.get("default_timeout", effective_config.default_timeout),
                "max_concurrent_clients": custom_config.get("max_concurrent_clients", effective_config.max_concurrent_clients),
                "environment_isolation": custom_config.get("environment_isolation", effective_config.environment_isolation)
            }
            effective_config = InfrastructureConfig(**config_dict)
        
        logger.info(f"Creating complete WebSocket test infrastructure [{infrastructure_id}]")
        
        try:
            # Create WebSocket utility (core component)
            websocket_utility = await self._create_websocket_utility(infrastructure_id)
            
            # Create optional components based on configuration
            auth_helper = None
            if effective_config.enable_authentication:
                auth_helper = await self._create_auth_helper(infrastructure_id)
            
            bridge_helper = None
            if effective_config.enable_agent_bridge:
                bridge_helper = await self._create_bridge_helper(infrastructure_id)
            
            metrics_collector = None
            if effective_config.enable_metrics_collection:
                metrics_collector = await self._create_metrics_collector(infrastructure_id)
            
            # Create infrastructure bundle
            infrastructure = TestInfrastructure(
                factory_id=self.factory_id,
                websocket_utility=websocket_utility,
                auth_helper=auth_helper,
                bridge_helper=bridge_helper,
                metrics_collector=metrics_collector,
                config=effective_config,
                created_at=datetime.now()
            )
            
            # Store infrastructure for lifecycle management
            self.created_infrastructures[infrastructure_id] = infrastructure
            
            logger.info(f"Complete WebSocket test infrastructure created [{infrastructure_id}] with {len([c for c in [auth_helper, bridge_helper, metrics_collector] if c])} optional components")
            
            return infrastructure
            
        except Exception as e:
            logger.error(f"Failed to create WebSocket test infrastructure [{infrastructure_id}]: {e}")
            raise
    
    async def _create_websocket_utility(self, component_id: str) -> WebSocketTestUtility:
        """Create WebSocket test utility with factory configuration."""
        utility = WebSocketTestUtility(env=self.env)
        await utility.initialize()
        
        self.created_websocket_utilities[component_id] = utility
        logger.debug(f"Created WebSocketTestUtility [{component_id}]")
        return utility
    
    async def _create_auth_helper(self, component_id: str) -> WebSocketAuthHelper:
        """Create WebSocket authentication helper with factory configuration."""
        auth_config = WebSocketAuthConfig.from_environment(self.env)
        auth_config.mock_mode = self.config.mock_mode
        
        auth_helper = WebSocketAuthHelper(config=auth_config, env=self.env)
        await auth_helper.initialize()
        
        self.created_auth_helpers[component_id] = auth_helper
        logger.debug(f"Created WebSocketAuthHelper [{component_id}]")
        return auth_helper
    
    async def _create_bridge_helper(self, component_id: str) -> WebSocketBridgeTestHelper:
        """Create WebSocket bridge helper with factory configuration."""
        bridge_config = BridgeTestConfig.from_environment(self.env)
        bridge_config.mock_mode = self.config.mock_mode
        
        bridge_helper = WebSocketBridgeTestHelper(config=bridge_config, env=self.env)
        await bridge_helper.initialize()
        
        self.created_bridge_helpers[component_id] = bridge_helper
        logger.debug(f"Created WebSocketBridgeTestHelper [{component_id}]")
        return bridge_helper
    
    async def _create_metrics_collector(self, component_id: str) -> CommunicationMetricsCollector:
        """Create communication metrics collector with factory configuration."""
        metrics_config = {
            "max_metrics_buffer": 10000,
            "sampling_interval": 1.0,
            "enable_real_time_monitoring": True,
            "export_metrics": False  # Don't auto-export in test mode
        }
        
        metrics_collector = CommunicationMetricsCollector(config=metrics_config, env=self.env)
        await metrics_collector.initialize()
        
        self.created_metrics_collectors[component_id] = metrics_collector
        logger.debug(f"Created CommunicationMetricsCollector [{component_id}]")
        return metrics_collector
    
    # Public factory methods for individual components
    
    async def create_auth_helper(self, helper_id: Optional[str] = None,
                               custom_auth_config: Optional[WebSocketAuthConfig] = None) -> WebSocketAuthHelper:
        """
        Create a WebSocket authentication helper.
        
        Args:
            helper_id: Optional helper identifier
            custom_auth_config: Optional custom authentication configuration
            
        Returns:
            WebSocketAuthHelper instance
        """
        if not self.is_initialized:
            await self.initialize()
        
        helper_id = helper_id or f"auth_{uuid.uuid4().hex[:8]}"
        
        auth_config = custom_auth_config or WebSocketAuthConfig.from_environment(self.env)
        auth_config.mock_mode = self.config.mock_mode
        
        auth_helper = WebSocketAuthHelper(config=auth_config, env=self.env)
        await auth_helper.initialize()
        
        self.created_auth_helpers[helper_id] = auth_helper
        
        logger.debug(f"Created standalone WebSocketAuthHelper [{helper_id}]")
        return auth_helper
    
    async def create_websocket_bridge(self, bridge_id: Optional[str] = None,
                                    custom_bridge_config: Optional[BridgeTestConfig] = None) -> WebSocketBridgeTestHelper:
        """
        Create a WebSocket bridge test helper for agent integration.
        
        Args:
            bridge_id: Optional bridge identifier
            custom_bridge_config: Optional custom bridge configuration
            
        Returns:
            WebSocketBridgeTestHelper instance
        """
        if not self.is_initialized:
            await self.initialize()
        
        bridge_id = bridge_id or f"bridge_{uuid.uuid4().hex[:8]}"
        
        bridge_config = custom_bridge_config or BridgeTestConfig.from_environment(self.env)
        bridge_config.mock_mode = self.config.mock_mode
        
        bridge_helper = WebSocketBridgeTestHelper(config=bridge_config, env=self.env)
        await bridge_helper.initialize()
        
        self.created_bridge_helpers[bridge_id] = bridge_helper
        
        logger.debug(f"Created standalone WebSocketBridgeTestHelper [{bridge_id}]")
        return bridge_helper
    
    async def create_communication_metrics(self, metrics_id: Optional[str] = None,
                                         custom_config: Optional[Dict[str, Any]] = None) -> CommunicationMetricsCollector:
        """
        Create a communication metrics collector for performance tracking.
        
        Args:
            metrics_id: Optional metrics collector identifier
            custom_config: Optional custom metrics configuration
            
        Returns:
            CommunicationMetricsCollector instance
        """
        if not self.is_initialized:
            await self.initialize()
        
        metrics_id = metrics_id or f"metrics_{uuid.uuid4().hex[:8]}"
        
        metrics_config = custom_config or {
            "max_metrics_buffer": 10000,
            "sampling_interval": 1.0,
            "enable_real_time_monitoring": True,
            "export_metrics": False
        }
        
        metrics_collector = CommunicationMetricsCollector(config=metrics_config, env=self.env)
        await metrics_collector.initialize()
        
        self.created_metrics_collectors[metrics_id] = metrics_collector
        
        logger.debug(f"Created standalone CommunicationMetricsCollector [{metrics_id}]")
        return metrics_collector
    
    async def create_test_infrastructure_with_user_isolation(self, user_count: int) -> Tuple[TestInfrastructure, List[TestUserContext]]:
        """
        Create test infrastructure with multiple isolated user contexts.
        
        Args:
            user_count: Number of isolated user contexts to create
            
        Returns:
            Tuple of (TestInfrastructure, List of TestUserContext)
        """
        if not self.is_initialized:
            await self.initialize()
        
        # Create infrastructure with authentication enabled
        infrastructure_config = {"enable_authentication": True, "enable_metrics_collection": True}
        infrastructure = await self.create_websocket_test_infrastructure(custom_config=infrastructure_config)
        
        if not infrastructure.auth_helper:
            raise RuntimeError("Authentication helper not available in infrastructure")
        
        # Create isolated user contexts
        user_contexts = await infrastructure.auth_helper.create_multi_user_contexts(user_count)
        
        logger.info(f"Created test infrastructure with {user_count} isolated user contexts")
        return infrastructure, user_contexts
    
    @asynccontextmanager
    async def infrastructure_context(self, infrastructure_config: Optional[Dict[str, Any]] = None) -> AsyncGenerator[TestInfrastructure, None]:
        """
        Context manager for WebSocket test infrastructure with automatic cleanup.
        
        Args:
            infrastructure_config: Optional infrastructure configuration
            
        Yields:
            TestInfrastructure instance
        """
        infrastructure = await self.create_websocket_test_infrastructure(custom_config=infrastructure_config)
        
        try:
            yield infrastructure
        finally:
            await infrastructure.cleanup()
    
    # Business-critical testing support methods
    
    async def create_golden_path_test_infrastructure(self) -> TestInfrastructure:
        """
        Create infrastructure specifically configured for Golden Path testing.
        
        Golden Path testing requires:
        - Full authentication support
        - Agent-WebSocket bridge functionality  
        - Comprehensive metrics collection
        - Multi-user isolation capabilities
        
        Returns:
            TestInfrastructure configured for Golden Path testing
        """
        golden_path_config = {
            "enable_authentication": True,
            "enable_agent_bridge": True,
            "enable_metrics_collection": True,
            "environment_isolation": True,
            "default_timeout": 60.0,  # Extended timeout for Golden Path
            "max_concurrent_clients": 5   # Conservative limit for Golden Path reliability
        }
        
        infrastructure = await self.create_websocket_test_infrastructure(
            infrastructure_id="golden_path_infrastructure",
            custom_config=golden_path_config
        )
        
        logger.info("Created Golden Path test infrastructure with full capabilities")
        return infrastructure
    
    async def validate_infrastructure_integration(self, infrastructure: TestInfrastructure) -> Dict[str, Any]:
        """
        Validate that infrastructure components are properly integrated.
        
        Args:
            infrastructure: Infrastructure to validate
            
        Returns:
            Validation results
        """
        results = {
            "infrastructure_id": infrastructure.factory_id,
            "components_validated": 0,
            "integration_tests_passed": 0,
            "integration_tests_failed": 0,
            "validation_errors": []
        }
        
        try:
            # Validate WebSocket utility
            if infrastructure.websocket_utility:
                status = infrastructure.websocket_utility.get_connection_status()
                if status:
                    results["components_validated"] += 1
                    results["integration_tests_passed"] += 1
                
            # Validate auth helper integration
            if infrastructure.auth_helper:
                auth_status = infrastructure.auth_helper.get_auth_status()
                if auth_status and auth_status.get("active_users") >= 0:
                    results["components_validated"] += 1
                    results["integration_tests_passed"] += 1
                
            # Validate bridge helper integration
            if infrastructure.bridge_helper:
                bridge_status = infrastructure.bridge_helper.get_bridge_status()
                if bridge_status and bridge_status.get("active_bridges") >= 0:
                    results["components_validated"] += 1
                    results["integration_tests_passed"] += 1
                
            # Validate metrics collector integration
            if infrastructure.metrics_collector:
                collector_status = infrastructure.metrics_collector.get_collector_status()
                if collector_status and collector_status.get("total_metrics") >= 0:
                    results["components_validated"] += 1
                    results["integration_tests_passed"] += 1
            
            logger.info(f"Infrastructure validation completed: {results['integration_tests_passed']}/{results['components_validated']} components validated")
            
        except Exception as e:
            results["validation_errors"].append(str(e))
            results["integration_tests_failed"] += 1
            logger.error(f"Infrastructure validation error: {e}")
        
        return results
    
    # Factory lifecycle management
    
    async def cleanup_infrastructure(self, infrastructure_id: str):
        """
        Clean up a specific infrastructure instance.
        
        Args:
            infrastructure_id: Infrastructure ID to clean up
        """
        if infrastructure_id in self.created_infrastructures:
            infrastructure = self.created_infrastructures[infrastructure_id]
            await infrastructure.cleanup()
            del self.created_infrastructures[infrastructure_id]
            logger.debug(f"Cleaned up infrastructure [{infrastructure_id}]")
    
    async def cleanup_all(self):
        """Clean up all created infrastructure components."""
        try:
            # Clean up all infrastructures
            cleanup_tasks = []
            for infrastructure in self.created_infrastructures.values():
                cleanup_tasks.append(infrastructure.cleanup())
            
            # Clean up standalone components
            for auth_helper in self.created_auth_helpers.values():
                cleanup_tasks.append(auth_helper.cleanup())
            
            for bridge_helper in self.created_bridge_helpers.values():
                cleanup_tasks.append(bridge_helper.cleanup())
            
            for metrics_collector in self.created_metrics_collectors.values():
                cleanup_tasks.append(metrics_collector.cleanup())
                
            for websocket_utility in self.created_websocket_utilities.values():
                cleanup_tasks.append(websocket_utility.cleanup())
            
            # Execute all cleanup tasks
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Clear all tracking
            self.created_infrastructures.clear()
            self.created_auth_helpers.clear()
            self.created_bridge_helpers.clear()
            self.created_metrics_collectors.clear()
            self.created_websocket_utilities.clear()
            
            logger.info(f"WebSocketTestInfrastructureFactory cleanup completed [{self.factory_id}]")
            
        except Exception as e:
            logger.error(f"Infrastructure factory cleanup failed: {e}")
    
    # Utility methods for test assertions
    
    def get_factory_status(self) -> Dict[str, Any]:
        """Get factory status and created component counts."""
        return {
            "factory_id": self.factory_id,
            "is_initialized": self.is_initialized,
            "config": {
                "mock_mode": self.config.mock_mode,
                "enable_metrics_collection": self.config.enable_metrics_collection,
                "enable_authentication": self.config.enable_authentication,
                "enable_agent_bridge": self.config.enable_agent_bridge,
                "default_timeout": self.config.default_timeout,
                "max_concurrent_clients": self.config.max_concurrent_clients
            },
            "created_components": {
                "infrastructures": len(self.created_infrastructures),
                "auth_helpers": len(self.created_auth_helpers),
                "bridge_helpers": len(self.created_bridge_helpers),
                "metrics_collectors": len(self.created_metrics_collectors),
                "websocket_utilities": len(self.created_websocket_utilities)
            }
        }
    
    def get_infrastructure(self, infrastructure_id: str) -> Optional[TestInfrastructure]:
        """Get infrastructure by ID."""
        return self.created_infrastructures.get(infrastructure_id)


# Export WebSocketTestInfrastructureFactory
__all__ = [
    'WebSocketTestInfrastructureFactory',
    'InfrastructureConfig',
    'TestInfrastructure'
]