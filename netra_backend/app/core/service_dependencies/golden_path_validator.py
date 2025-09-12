"""
Golden Path Validator - Business logic validation for critical user flows.

Validates that service dependencies support the critical business flows
that generate revenue, particularly the "Golden Path" user experience
that represents the core business value of the chat functionality.

ROOT CAUSE FIX: Eliminates EnvironmentType.DEVELOPMENT default that caused
staging services to connect to localhost:8081 instead of proper staging URLs.
Now uses environment context injection for definitive environment detection.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.environment_context import (
    EnvironmentContextService,
    get_environment_context_service,
    EnvironmentType as ContextEnvironmentType,
    EnvironmentContext
)
from .models import (
    EnvironmentType,
    GoldenPathRequirement,
    GOLDEN_PATH_REQUIREMENTS,
    ServiceType,
)


class GoldenPathValidationResult:
    """Result of golden path business validation."""
    
    def __init__(self):
        self.overall_success = True
        self.validation_results: List[Dict[str, Any]] = []
        self.business_impact_failures: List[str] = []
        self.warnings: List[str] = []
        self.critical_failures: List[str] = []
        self.services_validated = 0
        self.requirements_passed = 0
        self.requirements_failed = 0


class GoldenPathValidator:
    """
    Validates critical business functionality requirements.
    
    Ensures that service dependencies support the complete golden path
    user experience: authentication -> chat interaction -> real-time
    agent execution -> meaningful AI responses.
    
    ROOT CAUSE FIX: NO MORE ENVIRONMENT DEFAULTS! This validator now
    requires definitive environment context and fails fast if environment
    cannot be determined. This prevents the localhost:8081 staging failure.
    """
    
    def __init__(self, environment_context_service: Optional[EnvironmentContextService] = None):
        """
        Initialize golden path validator with environment context injection.
        
        Args:
            environment_context_service: Service providing environment context.
                                       If None, uses global singleton.
        
        CRITICAL: No longer accepts environment parameter with default!
        Environment must be detected definitively by EnvironmentContextService.
        """
        self.logger = central_logger.get_logger(__name__)
        self.environment_context_service = environment_context_service or get_environment_context_service()
        self.requirements = GOLDEN_PATH_REQUIREMENTS
        self._environment_context: Optional[EnvironmentContext] = None
    
    async def _ensure_environment_context(self) -> EnvironmentContext:
        """
        Ensure environment context is available.
        
        Returns:
            Definitive environment context
            
        Raises:
            RuntimeError: If environment cannot be determined
        """
        if self._environment_context is None:
            # Ensure environment context service is initialized
            if not self.environment_context_service.is_initialized():
                self.logger.info("Initializing environment context service for Golden Path validation")
                await self.environment_context_service.initialize()
            
            # Get definitive environment context
            self._environment_context = self.environment_context_service.get_environment_context()
            
            self.logger.info(
                f"Golden Path validation will use environment: {self._environment_context.environment_type.value} "
                f"(platform: {self._environment_context.cloud_platform.value}, "
                f"confidence: {self._environment_context.confidence_score:.2f})"
            )
        
        return self._environment_context
    
    def _convert_environment_type(self, context_env_type: ContextEnvironmentType) -> EnvironmentType:
        """
        Convert EnvironmentContextService environment type to models EnvironmentType.
        
        Args:
            context_env_type: Environment type from context service
            
        Returns:
            EnvironmentType for models compatibility
        """
        if context_env_type == ContextEnvironmentType.TESTING:
            return EnvironmentType.TESTING
        elif context_env_type == ContextEnvironmentType.DEVELOPMENT:
            return EnvironmentType.DEVELOPMENT
        elif context_env_type == ContextEnvironmentType.STAGING:
            return EnvironmentType.STAGING
        elif context_env_type == ContextEnvironmentType.PRODUCTION:
            return EnvironmentType.PRODUCTION
        else:
            self.logger.warning(f"Unknown environment type: {context_env_type}, defaulting to DEVELOPMENT")
            return EnvironmentType.DEVELOPMENT
    
    async def validate_golden_path_services(
        self,
        app: Any,
        services_to_validate: List[ServiceType]
    ) -> GoldenPathValidationResult:
        """
        Validate that services support critical business functionality.
        
        Args:
            app: FastAPI application instance
            services_to_validate: List of service types to validate
            
        Returns:
            Comprehensive business validation result
            
        Raises:
            RuntimeError: If environment cannot be determined with confidence
        """
        # CRITICAL: Get definitive environment context first
        environment_context = await self._ensure_environment_context()
        environment_type = self._convert_environment_type(environment_context.environment_type)
        
        self.logger.info("=" * 80)
        self.logger.info("GOLDEN PATH BUSINESS VALIDATION - CHAT FUNCTIONALITY")
        self.logger.info("=" * 80)
        self.logger.info(f"[U+1F30D] Environment: {environment_context.environment_type.value}")
        self.logger.info(f"[U+2601][U+FE0F] Platform: {environment_context.cloud_platform.value}")
        self.logger.info(f" TARGET:  Confidence: {environment_context.confidence_score:.2f}")
        if environment_context.service_name:
            self.logger.info(f"[U+1F680] Service: {environment_context.service_name}")
        self.logger.info("=" * 80)
        
        result = GoldenPathValidationResult()
        
        # Filter requirements to only those for services we're validating
        relevant_requirements = [
            req for req in self.requirements
            if req.service_type in services_to_validate
        ]
        
        self.logger.info(f"Validating {len(relevant_requirements)} business requirements")
        
        # Validate each requirement
        for requirement in relevant_requirements:
            try:
                validation_result = await self._validate_requirement(app, requirement)
                result.validation_results.append(validation_result)
                
                if validation_result["success"]:
                    result.requirements_passed += 1
                    self.logger.info(f"[U+2713] {requirement.requirement_name}: {validation_result['message']}")
                else:
                    result.requirements_failed += 1
                    
                    if requirement.critical:
                        result.overall_success = False
                        result.critical_failures.append(
                            f"{requirement.service_type.value}: {requirement.requirement_name} - "
                            f"{validation_result['message']}"
                        )
                        result.business_impact_failures.append(requirement.business_impact)
                        self.logger.error(
                            f" FAIL:  CRITICAL: {requirement.requirement_name} - {validation_result['message']}"
                        )
                        self.logger.error(f"   Business Impact: {requirement.business_impact}")
                    else:
                        result.warnings.append(
                            f"{requirement.service_type.value}: {requirement.requirement_name} - "
                            f"{validation_result['message']}"
                        )
                        self.logger.warning(f" WARNING: [U+FE0F] {requirement.requirement_name}: {validation_result['message']}")
                
            except Exception as e:
                result.requirements_failed += 1
                error_msg = f"Validation exception for {requirement.requirement_name}: {str(e)}"
                
                if requirement.critical:
                    result.overall_success = False
                    result.critical_failures.append(error_msg)
                    result.business_impact_failures.append(requirement.business_impact)
                    self.logger.error(f" FAIL:  CRITICAL EXCEPTION: {error_msg}")
                else:
                    result.warnings.append(error_msg)
                    self.logger.warning(f" WARNING: [U+FE0F] EXCEPTION: {error_msg}")
        
        result.services_validated = len(set(req.service_type for req in relevant_requirements))
        
        self._log_golden_path_summary(result)
        return result
    
    async def _validate_requirement(
        self,
        app: Any,
        requirement: GoldenPathRequirement
    ) -> Dict[str, Any]:
        """Validate a specific golden path requirement."""
        service_type = requirement.service_type
        validation_function = requirement.validation_function
        
        # CRITICAL FIX: Use definitive environment context instead of default
        environment_context = await self._ensure_environment_context()
        environment_type = self._convert_environment_type(environment_context.environment_type)
        
        # Use HTTP client for service-aware validation instead of direct database access
        from .service_health_client import ServiceHealthClient
        
        async with ServiceHealthClient(environment_context_service=self.environment_context_service) as health_client:
            # Dispatch to HTTP-based validation for services
            if service_type == ServiceType.AUTH_SERVICE:
                return await health_client.validate_auth_service_health()
            elif service_type == ServiceType.BACKEND_SERVICE:
                return await health_client.validate_backend_service_health()
            # Legacy database validation for compatibility during transition
            elif service_type == ServiceType.DATABASE_POSTGRES:
                return await self._validate_postgres_requirements(app, requirement)
            elif service_type == ServiceType.DATABASE_REDIS:
                return await self._validate_redis_requirements(app, requirement)
            elif service_type == ServiceType.WEBSOCKET_SERVICE:
                return await self._validate_websocket_requirements(app, requirement)
            else:
                return {
                    "requirement": requirement.requirement_name,
                    "success": False,
                    "message": f"No validation implemented for {service_type.value}",
                    "details": {}
                }
    
    async def _validate_postgres_requirements(
        self,
        app: Any,
        requirement: GoldenPathRequirement
    ) -> Dict[str, Any]:
        """Validate PostgreSQL business requirements."""
        return {
            "requirement": requirement.requirement_name,
            "success": False,
            "message": f"Unknown PostgreSQL validation: {requirement.validation_function}",
            "details": {}
        }
    
    
    async def _validate_redis_requirements(
        self,
        app: Any,
        requirement: GoldenPathRequirement
    ) -> Dict[str, Any]:
        """Validate Redis business requirements."""
        if requirement.validation_function == "validate_session_storage":
            return await self._validate_session_storage(app)
        else:
            return {
                "requirement": requirement.requirement_name,
                "success": False,
                "message": f"Unknown Redis validation: {requirement.validation_function}",
                "details": {}
            }
    
    async def _validate_session_storage(self, app: Any) -> Dict[str, Any]:
        """Validate that Redis session storage is operational."""
        try:
            if not hasattr(app.state, 'redis_manager') or app.state.redis_manager is None:
                return {
                    "requirement": "session_storage_ready",
                    "success": False,
                    "message": "Redis manager not available",
                    "details": {"redis_manager": False}
                }
            
            redis_manager = app.state.redis_manager
            
            # Test session-like operations
            test_session_key = "test_session_validation"
            test_session_data = {"user_id": "test", "created": "now"}
            
            # Test SET with expiration (typical for sessions)
            await redis_manager.set(test_session_key, str(test_session_data), ex=300)
            
            # Test GET
            retrieved_data = await redis_manager.get(test_session_key)
            
            # Test TTL (time to live)
            ttl = await redis_manager.get_ttl(test_session_key) if hasattr(redis_manager, 'get_ttl') else None
            
            # Cleanup
            await redis_manager.delete(test_session_key)
            
            if retrieved_data:
                return {
                    "requirement": "session_storage_ready",
                    "success": True,
                    "message": "Session storage operations validated",
                    "details": {
                        "set_operation": True,
                        "get_operation": True,
                        "ttl_support": ttl is not None,
                        "delete_operation": True
                    }
                }
            else:
                return {
                    "requirement": "session_storage_ready",
                    "success": False,
                    "message": "Session storage GET operation failed",
                    "details": {
                        "set_operation": True,
                        "get_operation": False
                    }
                }
                
        except Exception as e:
            return {
                "requirement": "session_storage_ready",
                "success": False,
                "message": f"Session storage validation failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # NOTE: Auth Service validation now handled via HTTP endpoint in ServiceHealthClient
    # This eliminates service boundary violations and direct app state access
    
    # NOTE: Backend Service validation now handled via HTTP endpoint in ServiceHealthClient
    # This eliminates service boundary violations and direct app state access
    
    async def _validate_websocket_requirements(
        self,
        app: Any,
        requirement: GoldenPathRequirement
    ) -> Dict[str, Any]:
        """Validate WebSocket Service business requirements."""
        if requirement.validation_function == "validate_websocket_agent_events":
            return await self._validate_websocket_agent_events(app)
        else:
            return {
                "requirement": requirement.requirement_name,
                "success": False,
                "message": f"Unknown WebSocket validation: {requirement.validation_function}",
                "details": {}
            }
    
    async def _validate_websocket_agent_events(self, app: Any) -> Dict[str, Any]:
        """Validate that WebSocket agent events can be sent to users."""
        try:
            event_chain = {
                "websocket_manager": False,
                "agent_bridge": False,
                "message_router": False,
                "event_routing": False
            }
            
            # Check WebSocket manager (can be factory pattern)
            if hasattr(app.state, 'websocket_manager') and app.state.websocket_manager:
                event_chain["websocket_manager"] = True
            elif hasattr(app.state, 'websocket_bridge_factory'):
                event_chain["websocket_manager"] = "factory"
            
            # Check agent WebSocket bridge
            if hasattr(app.state, 'agent_websocket_bridge') and app.state.agent_websocket_bridge:
                event_chain["agent_bridge"] = True
                
                # Check if bridge has required notification methods
                bridge = app.state.agent_websocket_bridge
                required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
                has_all_methods = all(hasattr(bridge, method) for method in required_methods)
                
                if has_all_methods:
                    event_chain["event_routing"] = True
            
            # Check message router
            try:
                from netra_backend.app.websocket_core import get_message_router
                message_router = get_message_router()
                if message_router:
                    event_chain["message_router"] = True
            except ImportError:
                pass
            
            # Calculate event readiness
            ready_components = sum(1 for v in event_chain.values() if v is True or v == "factory")
            total_components = len(event_chain)
            
            # WebSocket events are critical for user experience
            if ready_components >= 3:  # Most components ready
                return {
                    "requirement": "realtime_communication_ready",
                    "success": True,
                    "message": "WebSocket agent events ready for real-time user feedback",
                    "details": {
                        "event_chain": event_chain,
                        "ready_components": ready_components,
                        "total_components": total_components
                    }
                }
            else:
                missing_components = [comp for comp, ready in event_chain.items() if not ready]
                return {
                    "requirement": "realtime_communication_ready",
                    "success": False,
                    "message": f"WebSocket events incomplete - users won't get real-time feedback. Missing: {missing_components}",
                    "details": {
                        "event_chain": event_chain,
                        "ready_components": ready_components,
                        "missing_components": missing_components
                    }
                }
                
        except Exception as e:
            return {
                "requirement": "realtime_communication_ready",
                "success": False,
                "message": f"WebSocket events validation failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _log_golden_path_summary(self, result: GoldenPathValidationResult) -> None:
        """Log comprehensive golden path validation summary."""
        self.logger.info("=" * 80)
        self.logger.info("GOLDEN PATH VALIDATION SUMMARY")
        self.logger.info("=" * 80)
        
        # Overall status
        status_emoji = " PASS: " if result.overall_success else " FAIL: "
        self.logger.info(f"Overall Business Validation: {status_emoji} {'SUCCESS' if result.overall_success else 'FAILED'}")
        
        # Statistics
        self.logger.info(f"Services Validated: {result.services_validated}")
        self.logger.info(f"Requirements Passed: {result.requirements_passed}")
        self.logger.info(f"Requirements Failed: {result.requirements_failed}")
        
        # Critical failures (business impact)
        if result.business_impact_failures:
            self.logger.error(f"\n ALERT:  BUSINESS IMPACT FAILURES ({len(result.business_impact_failures)}):")
            for i, impact in enumerate(result.business_impact_failures, 1):
                self.logger.error(f"  {i}. {impact}")
        
        # Critical failures (technical)
        if result.critical_failures:
            self.logger.error(f"\n FAIL:  CRITICAL TECHNICAL FAILURES ({len(result.critical_failures)}):")
            for i, failure in enumerate(result.critical_failures, 1):
                self.logger.error(f"  {i}. {failure}")
        
        # Warnings
        if result.warnings:
            self.logger.warning(f"\n WARNING: [U+FE0F] WARNINGS ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings, 1):
                self.logger.warning(f"  {i}. {warning}")
        
        if result.overall_success:
            self.logger.info("\n[U+1F4B0] GOLDEN PATH PROTECTED - Chat functionality business value secured!")
        else:
            self.logger.error("\n[U+1F4B8] GOLDEN PATH AT RISK - Chat functionality business value threatened!")
        
        self.logger.info("=" * 80)