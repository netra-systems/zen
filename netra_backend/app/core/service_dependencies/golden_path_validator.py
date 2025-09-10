"""
Golden Path Validator - Business logic validation for critical user flows.

Validates that service dependencies support the critical business flows
that generate revenue, particularly the "Golden Path" user experience
that represents the core business value of the chat functionality.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from netra_backend.app.logging_config import central_logger
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
    """
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.DEVELOPMENT):
        """Initialize golden path validator."""
        self.logger = central_logger.get_logger(__name__)
        self.environment = environment
        self.requirements = GOLDEN_PATH_REQUIREMENTS
    
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
        """
        self.logger.info("=" * 80)
        self.logger.info("GOLDEN PATH BUSINESS VALIDATION - CHAT FUNCTIONALITY")
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
                    self.logger.info(f"✓ {requirement.requirement_name}: {validation_result['message']}")
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
                            f"❌ CRITICAL: {requirement.requirement_name} - {validation_result['message']}"
                        )
                        self.logger.error(f"   Business Impact: {requirement.business_impact}")
                    else:
                        result.warnings.append(
                            f"{requirement.service_type.value}: {requirement.requirement_name} - "
                            f"{validation_result['message']}"
                        )
                        self.logger.warning(f"⚠️ {requirement.requirement_name}: {validation_result['message']}")
                
            except Exception as e:
                result.requirements_failed += 1
                error_msg = f"Validation exception for {requirement.requirement_name}: {str(e)}"
                
                if requirement.critical:
                    result.overall_success = False
                    result.critical_failures.append(error_msg)
                    result.business_impact_failures.append(requirement.business_impact)
                    self.logger.error(f"❌ CRITICAL EXCEPTION: {error_msg}")
                else:
                    result.warnings.append(error_msg)
                    self.logger.warning(f"⚠️ EXCEPTION: {error_msg}")
        
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
        
        # Dispatch to specific validation function
        if service_type == ServiceType.DATABASE_POSTGRES:
            return await self._validate_postgres_requirements(app, requirement)
        elif service_type == ServiceType.DATABASE_REDIS:
            return await self._validate_redis_requirements(app, requirement)
        elif service_type == ServiceType.AUTH_SERVICE:
            return await self._validate_auth_requirements(app, requirement)
        elif service_type == ServiceType.BACKEND_SERVICE:
            return await self._validate_backend_requirements(app, requirement)
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
        if requirement.validation_function == "validate_user_auth_tables":
            return await self._validate_user_auth_tables(app)
        else:
            return {
                "requirement": requirement.requirement_name,
                "success": False,
                "message": f"Unknown PostgreSQL validation: {requirement.validation_function}",
                "details": {}
            }
    
    async def _validate_user_auth_tables(self, app: Any) -> Dict[str, Any]:
        """Validate that user authentication tables are ready."""
        try:
            if not hasattr(app.state, 'db_session_factory') or app.state.db_session_factory is None:
                return {
                    "requirement": "user_authentication_ready",
                    "success": False,
                    "message": "Database session factory not available",
                    "details": {"db_session_factory": False}
                }
            
            async with app.state.db_session_factory() as session:
                # Check for critical user-related tables
                critical_tables = ['users', 'user_sessions']  # Add actual table names
                table_results = {}
                
                for table_name in critical_tables:
                    try:
                        # Check if table exists and has basic structure
                        result = await session.execute(text(
                            f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
                        ))
                        table_exists = result.scalar() > 0
                        table_results[table_name] = table_exists
                    except Exception:
                        table_results[table_name] = False
                
                # All critical tables must exist
                all_tables_exist = all(table_results.values())
                
                if all_tables_exist:
                    # Check for essential indexes on user tables (if possible)
                    try:
                        index_result = await session.execute(text(
                            """
                            SELECT COUNT(*) as index_count
                            FROM pg_indexes 
                            WHERE tablename IN ('users', 'user_sessions')
                            """
                        ))
                        index_count = index_result.scalar() or 0
                        
                        return {
                            "requirement": "user_authentication_ready",
                            "success": True,
                            "message": f"User auth tables ready with {index_count} indexes",
                            "details": {
                                "tables": table_results,
                                "index_count": index_count,
                                "all_tables_exist": all_tables_exist
                            }
                        }
                    except Exception:
                        # Indexes check failed, but tables exist
                        return {
                            "requirement": "user_authentication_ready",
                            "success": True,
                            "message": "User auth tables exist (index check skipped)",
                            "details": {
                                "tables": table_results,
                                "index_check": "skipped",
                                "all_tables_exist": all_tables_exist
                            }
                        }
                else:
                    missing_tables = [table for table, exists in table_results.items() if not exists]
                    return {
                        "requirement": "user_authentication_ready",
                        "success": False,
                        "message": f"Missing critical user tables: {missing_tables}",
                        "details": {
                            "tables": table_results,
                            "missing_tables": missing_tables
                        }
                    }
                    
        except Exception as e:
            return {
                "requirement": "user_authentication_ready",
                "success": False,
                "message": f"Database validation failed: {str(e)}",
                "details": {"error": str(e)}
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
    
    async def _validate_auth_requirements(
        self,
        app: Any,
        requirement: GoldenPathRequirement
    ) -> Dict[str, Any]:
        """Validate Auth Service business requirements."""
        if requirement.validation_function == "validate_jwt_capabilities":
            return await self._validate_jwt_capabilities(app)
        else:
            return {
                "requirement": requirement.requirement_name,
                "success": False,
                "message": f"Unknown Auth validation: {requirement.validation_function}",
                "details": {}
            }
    
    async def _validate_jwt_capabilities(self, app: Any) -> Dict[str, Any]:
        """Validate JWT token creation and validation capabilities."""
        try:
            # Check for unified JWT validator first (preferred pattern)
            if hasattr(app.state, 'unified_jwt_validator') and app.state.unified_jwt_validator is not None:
                unified_validator = app.state.unified_jwt_validator
                capabilities = {}
                
                # Check for JWT methods on unified validator
                capabilities["create_access_token"] = hasattr(unified_validator, 'create_access_token') and callable(getattr(unified_validator, 'create_access_token'))
                capabilities["verify_token"] = hasattr(unified_validator, 'verify_token') and callable(getattr(unified_validator, 'verify_token'))
                capabilities["create_refresh_token"] = hasattr(unified_validator, 'create_refresh_token') and callable(getattr(unified_validator, 'create_refresh_token'))
                
                jwt_ready = capabilities["create_access_token"] and capabilities["verify_token"]
                
                if jwt_ready:
                    return {
                        "requirement": "jwt_validation_ready",
                        "success": True,
                        "message": "JWT capabilities confirmed via UnifiedJWTValidator",
                        "details": {**capabilities, "validator_type": "unified_jwt_validator"}
                    }
                else:
                    missing_capabilities = [cap for cap, available in capabilities.items() if not available]
                    return {
                        "requirement": "jwt_validation_ready",
                        "success": False,
                        "message": f"UnifiedJWTValidator missing JWT capabilities: {missing_capabilities}",
                        "details": {**capabilities, "validator_type": "unified_jwt_validator"}
                    }
            
            # Check for legacy key manager pattern
            elif hasattr(app.state, 'key_manager') and app.state.key_manager is not None:
                key_manager = app.state.key_manager
                capabilities = {}
                
                # Check for JWT creation capability with callable verification
                capabilities["create_access_token"] = hasattr(key_manager, 'create_access_token') and callable(getattr(key_manager, 'create_access_token', None))
                capabilities["verify_token"] = hasattr(key_manager, 'verify_token') and callable(getattr(key_manager, 'verify_token', None))
                capabilities["create_refresh_token"] = hasattr(key_manager, 'create_refresh_token') and callable(getattr(key_manager, 'create_refresh_token', None))
                
                jwt_ready = capabilities["create_access_token"] and capabilities["verify_token"]
                
                if jwt_ready:
                    return {
                        "requirement": "jwt_validation_ready",
                        "success": True,
                        "message": "JWT capabilities confirmed via key manager",
                        "details": {**capabilities, "validator_type": "key_manager"}
                    }
                else:
                    missing_capabilities = [cap for cap, available in capabilities.items() if not available]
                    return {
                        "requirement": "jwt_validation_ready",
                        "success": False,
                        "message": f"Key manager missing JWT capabilities: {missing_capabilities}",
                        "details": {**capabilities, "validator_type": "key_manager"}
                    }
            
            # No JWT validation capability found
            else:
                return {
                    "requirement": "jwt_validation_ready",
                    "success": False,
                    "message": "Key manager not available for JWT operations",
                    "details": {"key_manager": False, "unified_jwt_validator": False}
                }
                
        except Exception as e:
            return {
                "requirement": "jwt_validation_ready",
                "success": False,
                "message": f"JWT validation failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _validate_backend_requirements(
        self,
        app: Any,
        requirement: GoldenPathRequirement
    ) -> Dict[str, Any]:
        """Validate Backend Service business requirements."""
        if requirement.validation_function == "validate_agent_execution_chain":
            return await self._validate_agent_execution_chain(app)
        else:
            return {
                "requirement": requirement.requirement_name,
                "success": False,
                "message": f"Unknown Backend validation: {requirement.validation_function}",
                "details": {}
            }
    
    async def _validate_agent_execution_chain(self, app: Any) -> Dict[str, Any]:
        """Validate that the complete agent execution chain is operational."""
        try:
            chain_components = {
                "agent_supervisor": False,
                "execution_engine": False,
                "tool_system": False,
                "llm_integration": False,
                "websocket_integration": False
            }
            
            # Check agent supervisor
            if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                chain_components["agent_supervisor"] = True
                supervisor = app.state.agent_supervisor
                
                # Check execution engine
                if hasattr(supervisor, 'engine') or hasattr(supervisor, 'execution_engine'):
                    chain_components["execution_engine"] = True
            
            # Check tool system readiness
            if (hasattr(app.state, 'tool_classes') and app.state.tool_classes) or \
               (hasattr(app.state, 'tool_dispatcher') and app.state.tool_dispatcher):
                chain_components["tool_system"] = True
            
            # Check LLM integration
            if hasattr(app.state, 'llm_manager') and app.state.llm_manager:
                chain_components["llm_integration"] = True
            
            # Check WebSocket integration for agent events
            if hasattr(app.state, 'agent_websocket_bridge') and app.state.agent_websocket_bridge:
                chain_components["websocket_integration"] = True
            
            # Calculate readiness score
            components_ready = sum(chain_components.values())
            total_components = len(chain_components)
            readiness_score = components_ready / total_components
            
            # Agent execution requires most components to be ready
            if readiness_score >= 0.8:  # 4/5 components
                return {
                    "requirement": "agent_execution_ready",
                    "success": True,
                    "message": f"Agent execution chain ready ({components_ready}/{total_components} components)",
                    "details": {
                        "components": chain_components,
                        "readiness_score": readiness_score
                    }
                }
            else:
                missing_components = [comp for comp, ready in chain_components.items() if not ready]
                return {
                    "requirement": "agent_execution_ready",
                    "success": False,
                    "message": f"Agent execution chain incomplete - missing: {missing_components}",
                    "details": {
                        "components": chain_components,
                        "readiness_score": readiness_score,
                        "missing_components": missing_components
                    }
                }
                
        except Exception as e:
            return {
                "requirement": "agent_execution_ready",
                "success": False,
                "message": f"Agent execution validation failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
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
        status_emoji = "✅" if result.overall_success else "❌"
        self.logger.info(f"Overall Business Validation: {status_emoji} {'SUCCESS' if result.overall_success else 'FAILED'}")
        
        # Statistics
        self.logger.info(f"Services Validated: {result.services_validated}")
        self.logger.info(f"Requirements Passed: {result.requirements_passed}")
        self.logger.info(f"Requirements Failed: {result.requirements_failed}")
        
        # Critical failures (business impact)
        if result.business_impact_failures:
            self.logger.error(f"\n🚨 BUSINESS IMPACT FAILURES ({len(result.business_impact_failures)}):")
            for i, impact in enumerate(result.business_impact_failures, 1):
                self.logger.error(f"  {i}. {impact}")
        
        # Critical failures (technical)
        if result.critical_failures:
            self.logger.error(f"\n❌ CRITICAL TECHNICAL FAILURES ({len(result.critical_failures)}):")
            for i, failure in enumerate(result.critical_failures, 1):
                self.logger.error(f"  {i}. {failure}")
        
        # Warnings
        if result.warnings:
            self.logger.warning(f"\n⚠️ WARNINGS ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings, 1):
                self.logger.warning(f"  {i}. {warning}")
        
        if result.overall_success:
            self.logger.info("\n💰 GOLDEN PATH PROTECTED - Chat functionality business value secured!")
        else:
            self.logger.error("\n💸 GOLDEN PATH AT RISK - Chat functionality business value threatened!")
        
        self.logger.info("=" * 80)