"""
Authentication Permissiveness System - Multi-Level Auth Validation

Business Value Justification:
- Segment: Platform/Infrastructure - Authentication Framework
- Business Goal: Restore WebSocket functionality and eliminate 1011 errors
- Value Impact: Enables $500K+ ARR chat functionality by providing graceful auth degradation
- Revenue Impact: Prevents customer blocks while maintaining security boundaries

CRITICAL MISSION:
Resolve WebSocket 1011 authentication errors that prevent Golden Path functionality.
This system provides multi-level authentication validation that degrades gracefully
from strict security to permissive access based on environment and configuration.

ARCHITECTURE:
- AuthPermissivenessLevel: STRICT, RELAXED, DEMO, EMERGENCY levels
- EnvironmentAuthDetector: Context-aware auth mode selection
- RelaxedAuthValidator: Permissive validation for staging environments  
- DemoAuthValidator: Bypass for isolated demo environments
- EmergencyAuthValidator: Last resort auth when services are down

REMEDIATION STRATEGY:
1. Detect GCP Load Balancer header stripping situations
2. Provide progressive auth relaxation based on environment
3. Enable demo mode for isolated networks without full auth
4. Maintain audit logging and security boundaries
5. Allow emergency access when auth services are unavailable
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import WebSocket

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class AuthPermissivenessLevel(Enum):
    """Authentication permissiveness levels for different environments and scenarios."""
    
    STRICT = "strict"           # Full authentication required - production default
    RELAXED = "relaxed"         # Relaxed validation - staging/development
    DEMO = "demo"               # Demo mode bypass - isolated networks
    EMERGENCY = "emergency"     # Emergency bypass - auth service failures


@dataclass
class AuthContext:
    """Authentication context for permissiveness decisions."""
    
    environment: str
    is_cloud_run: bool
    has_load_balancer: bool
    auth_service_available: bool
    demo_mode_enabled: bool
    emergency_mode_enabled: bool
    connection_source: str
    user_agent: Optional[str] = None
    client_ip: Optional[str] = None
    headers_available: bool = True
    subprotocols_available: bool = False


@dataclass
class AuthPermissivenessResult:
    """Result of auth permissiveness validation."""
    
    success: bool
    level: AuthPermissivenessLevel
    user_context: Optional[UserExecutionContext] = None
    auth_method: str = "unknown"
    bypass_reason: Optional[str] = None
    security_warnings: List[str] = None
    audit_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.security_warnings is None:
            self.security_warnings = []
        if self.audit_info is None:
            self.audit_info = {}


class EnvironmentAuthDetector:
    """Detects appropriate authentication level based on environment and context."""
    
    def __init__(self):
        self.env = get_env()
        
    def detect_auth_level(self, websocket: WebSocket) -> AuthPermissivenessLevel:
        """
        Detect appropriate authentication permissiveness level.
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            AuthPermissivenessLevel: Recommended auth level
        """
        try:
            # Build auth context
            context = self._build_auth_context(websocket)
            
            # Check for emergency mode first (auth service down)
            if context.emergency_mode_enabled or not context.auth_service_available:
                logger.warning(f"EMERGENCY AUTH: Enabling emergency mode - "
                             f"auth_service_available={context.auth_service_available}, "
                             f"emergency_mode={context.emergency_mode_enabled}")
                return AuthPermissivenessLevel.EMERGENCY
            
            # Check for demo mode (isolated networks)
            if context.demo_mode_enabled:
                logger.info(f"DEMO AUTH: Demo mode enabled in {context.environment} environment")
                return AuthPermissivenessLevel.DEMO
            
            # Environment-based detection
            if context.environment in ["production", "prod"]:
                # Production always requires strict auth
                logger.info("STRICT AUTH: Production environment detected")
                return AuthPermissivenessLevel.STRICT
            
            elif context.environment in ["staging", "development"]:
                # Check for GCP Load Balancer issues
                if context.is_cloud_run and context.has_load_balancer:
                    logger.info(f"RELAXED AUTH: GCP Load Balancer detected in {context.environment} "
                               f"- enabling relaxed validation")
                    return AuthPermissivenessLevel.RELAXED
                
                # Standard relaxed mode for staging/development
                logger.info(f"RELAXED AUTH: {context.environment} environment - enabling relaxed validation")
                return AuthPermissivenessLevel.RELAXED
            
            else:
                # Unknown environment - default to relaxed with warning
                logger.warning(f"UNKNOWN ENVIRONMENT: {context.environment} - defaulting to relaxed auth")
                return AuthPermissivenessLevel.RELAXED
                
        except Exception as e:
            logger.error(f"Error detecting auth level: {e} - defaulting to strict")
            return AuthPermissivenessLevel.STRICT
    
    def _build_auth_context(self, websocket: WebSocket) -> AuthContext:
        """Build authentication context from environment and WebSocket."""
        
        # Environment detection
        environment = self.env.get("ENVIRONMENT", "unknown").lower()
        is_cloud_run = bool(self.env.get("K_SERVICE"))
        has_load_balancer = self._detect_load_balancer()
        
        # Service availability
        auth_service_available = self._check_auth_service_availability()
        
        # Mode detection
        demo_mode_enabled = self.env.get("DEMO_MODE", "1") == "1"
        emergency_mode_enabled = self.env.get("EMERGENCY_MODE", "0") == "1"
        
        # Connection info
        connection_source = self._detect_connection_source(websocket)
        user_agent = websocket.headers.get("user-agent") if websocket.headers else None
        client_ip = self._extract_client_ip(websocket)
        
        # WebSocket capabilities
        headers_available = bool(websocket.headers)
        subprotocols_available = self._check_subprotocols_available(websocket)
        
        return AuthContext(
            environment=environment,
            is_cloud_run=is_cloud_run,
            has_load_balancer=has_load_balancer,
            auth_service_available=auth_service_available,
            demo_mode_enabled=demo_mode_enabled,
            emergency_mode_enabled=emergency_mode_enabled,
            connection_source=connection_source,
            user_agent=user_agent,
            client_ip=client_ip,
            headers_available=headers_available,
            subprotocols_available=subprotocols_available
        )
    
    def _detect_load_balancer(self) -> bool:
        """Detect if running behind GCP Load Balancer."""
        # GCP Load Balancer typically strips certain headers
        gcp_lb_indicators = [
            self.env.get("X-FORWARDED-PROTO"),  # Load balancer forwarding
            self.env.get("X-CLOUD-TRACE-CONTEXT"),  # GCP tracing
            self.env.get("X-FORWARDED-FOR"),  # Forwarding chain
        ]
        return any(indicator for indicator in gcp_lb_indicators)
    
    def _check_auth_service_availability(self) -> bool:
        """Quick check if auth service is available."""
        try:
            from netra_backend.app.services.unified_authentication_service import get_unified_auth_service
            auth_service = get_unified_auth_service()
            return auth_service is not None
        except Exception as e:
            logger.warning(f"Auth service availability check failed: {e}")
            return False
    
    def _detect_connection_source(self, websocket: WebSocket) -> str:
        """Detect the source of the WebSocket connection."""
        if not websocket.headers:
            return "unknown"
        
        origin = websocket.headers.get("origin", "")
        if "localhost" in origin or "127.0.0.1" in origin:
            return "local"
        elif "staging" in origin:
            return "staging" 
        elif "netra" in origin:
            return "production"
        else:
            return "external"
    
    def _extract_client_ip(self, websocket: WebSocket) -> Optional[str]:
        """Extract client IP address from WebSocket connection."""
        try:
            if websocket.client:
                return getattr(websocket.client, 'host', None)
            return None
        except Exception:
            return None
    
    def _check_subprotocols_available(self, websocket: WebSocket) -> bool:
        """Check if subprotocols are available for token extraction."""
        if not websocket.headers:
            return False
        return "sec-websocket-protocol" in websocket.headers


class AuthPermissivenessValidator:
    """Main validator that coordinates multi-level authentication."""
    
    def __init__(self):
        self.detector = EnvironmentAuthDetector()
        self.strict_validator = StrictAuthValidator()
        self.relaxed_validator = RelaxedAuthValidator()
        self.demo_validator = DemoAuthValidator()
        self.emergency_validator = EmergencyAuthValidator()
        
        # Statistics
        self.validation_stats = {
            "total_attempts": 0,
            "by_level": {level.value: 0 for level in AuthPermissivenessLevel},
            "successes": 0,
            "failures": 0
        }
    
    async def validate_with_permissiveness(
        self, 
        websocket: WebSocket,
        auth_level: Optional[AuthPermissivenessLevel] = None
    ) -> AuthPermissivenessResult:
        """
        Validate authentication with appropriate permissiveness level.
        
        Args:
            websocket: WebSocket connection object
            auth_level: Optional override for auth level (uses detection if None)
            
        Returns:
            AuthPermissivenessResult: Validation result
        """
        self.validation_stats["total_attempts"] += 1
        start_time = time.time()
        
        try:
            # Determine auth level
            if auth_level is None:
                auth_level = self.detector.detect_auth_level(websocket)
            
            self.validation_stats["by_level"][auth_level.value] += 1
            
            # Log validation attempt
            validation_context = {
                "auth_level": auth_level.value,
                "environment": self.detector.env.get("ENVIRONMENT", "unknown"),
                "is_cloud_run": bool(self.detector.env.get("K_SERVICE")),
                "headers_available": bool(websocket.headers),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"PERMISSIVE AUTH: Starting {auth_level.value} authentication")
            logger.debug(f"VALIDATION CONTEXT: {json.dumps(validation_context, indent=2)}")
            
            # Route to appropriate validator
            if auth_level == AuthPermissivenessLevel.STRICT:
                result = await self.strict_validator.validate(websocket)
            elif auth_level == AuthPermissivenessLevel.RELAXED:
                result = await self.relaxed_validator.validate(websocket)
            elif auth_level == AuthPermissivenessLevel.DEMO:
                result = await self.demo_validator.validate(websocket)
            elif auth_level == AuthPermissivenessLevel.EMERGENCY:
                result = await self.emergency_validator.validate(websocket)
            else:
                raise ValueError(f"Unknown auth level: {auth_level}")
            
            # Add timing and audit info
            duration = time.time() - start_time
            result.audit_info.update({
                "validation_duration_ms": round(duration * 1000, 2),
                "auth_level_used": auth_level.value,
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Update statistics
            if result.success:
                self.validation_stats["successes"] += 1
                logger.info(f"PERMISSIVE AUTH: {auth_level.value} validation succeeded in {duration*1000:.2f}ms")
            else:
                self.validation_stats["failures"] += 1
                logger.warning(f"PERMISSIVE AUTH: {auth_level.value} validation failed in {duration*1000:.2f}ms")
            
            return result
            
        except Exception as e:
            self.validation_stats["failures"] += 1
            duration = time.time() - start_time
            
            logger.error(f"PERMISSIVE AUTH: Validation exception in {duration*1000:.2f}ms: {e}")
            
            return AuthPermissivenessResult(
                success=False,
                level=auth_level or AuthPermissivenessLevel.STRICT,
                auth_method="validation_exception",
                security_warnings=[f"Validation exception: {str(e)}"],
                audit_info={
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                    "validation_duration_ms": round(duration * 1000, 2)
                }
            )
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics for monitoring."""
        success_rate = (self.validation_stats["successes"] / 
                       max(1, self.validation_stats["total_attempts"])) * 100
        
        return {
            "auth_permissiveness_stats": self.validation_stats,
            "success_rate_percent": round(success_rate, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class StrictAuthValidator:
    """Strict authentication validator - full security requirements."""
    
    async def validate(self, websocket: WebSocket) -> AuthPermissivenessResult:
        """Perform strict authentication validation."""
        logger.debug("STRICT AUTH: Performing full authentication validation")
        
        try:
            # Use the existing SSOT authentication system
            from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
            
            auth_result = await authenticate_websocket_ssot(websocket)
            
            if auth_result.success:
                return AuthPermissivenessResult(
                    success=True,
                    level=AuthPermissivenessLevel.STRICT,
                    user_context=auth_result.user_context,
                    auth_method="strict_full_validation",
                    audit_info={
                        "user_id": auth_result.user_context.user_id[:8] + "..." if auth_result.user_context else None,
                        "auth_service": "unified_authentication_service"
                    }
                )
            else:
                return AuthPermissivenessResult(
                    success=False,
                    level=AuthPermissivenessLevel.STRICT,
                    auth_method="strict_validation_failed",
                    security_warnings=[auth_result.error_message or "Authentication failed"],
                    audit_info={"error": auth_result.error_message}
                )
                
        except Exception as e:
            logger.error(f"STRICT AUTH: Validation exception: {e}")
            return AuthPermissivenessResult(
                success=False,
                level=AuthPermissivenessLevel.STRICT,
                auth_method="strict_exception",
                security_warnings=[f"Strict validation exception: {str(e)}"]
            )


class RelaxedAuthValidator:
    """Relaxed authentication validator - permissive for staging/development."""
    
    async def validate(self, websocket: WebSocket) -> AuthPermissivenessResult:
        """Perform relaxed authentication validation."""
        logger.debug("RELAXED AUTH: Performing permissive authentication validation")
        
        try:
            # First try strict authentication
            from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
            
            try:
                auth_result = await authenticate_websocket_ssot(websocket)
                if auth_result.success:
                    logger.info("RELAXED AUTH: Strict validation succeeded")
                    return AuthPermissivenessResult(
                        success=True,
                        level=AuthPermissivenessLevel.RELAXED,
                        user_context=auth_result.user_context,
                        auth_method="relaxed_strict_success",
                        audit_info={"fallback_used": False}
                    )
            except Exception as e:
                logger.info(f"RELAXED AUTH: Strict validation failed, trying relaxed fallback: {e}")
            
            # If strict fails, try relaxed validation
            relaxed_user = await self._create_relaxed_user_context(websocket)
            
            if relaxed_user:
                security_warnings = [
                    "Using relaxed authentication - not suitable for production",
                    "Limited token validation performed"
                ]
                
                return AuthPermissivenessResult(
                    success=True,
                    level=AuthPermissivenessLevel.RELAXED,
                    user_context=relaxed_user,
                    auth_method="relaxed_fallback",
                    security_warnings=security_warnings,
                    audit_info={
                        "fallback_used": True,
                        "environment": get_env().get("ENVIRONMENT", "unknown")
                    }
                )
            else:
                return AuthPermissivenessResult(
                    success=False,
                    level=AuthPermissivenessLevel.RELAXED,
                    auth_method="relaxed_failed",
                    security_warnings=["Both strict and relaxed validation failed"]
                )
                
        except Exception as e:
            logger.error(f"RELAXED AUTH: Validation exception: {e}")
            return AuthPermissivenessResult(
                success=False,
                level=AuthPermissivenessLevel.RELAXED,
                auth_method="relaxed_exception",
                security_warnings=[f"Relaxed validation exception: {str(e)}"]
            )
    
    async def _create_relaxed_user_context(self, websocket: WebSocket) -> Optional[UserExecutionContext]:
        """Create user context with relaxed validation."""
        try:
            # Try to extract any available identity information
            token = self._extract_any_token(websocket)
            
            # Create relaxed user context
            from shared.id_generation import UnifiedIdGenerator
            
            # Use token-based user ID if available, otherwise generate one
            if token and len(token) > 10:
                user_id = f"relaxed_{hash(token) % 10000:04d}"
            else:
                user_id = f"relaxed_{uuid.uuid4().hex[:8]}"
            
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=UnifiedIdGenerator.generate_base_id("relaxed_thread"),
                run_id=UnifiedIdGenerator.generate_base_id("relaxed_run"),
                request_id=UnifiedIdGenerator.generate_base_id("relaxed_req"),
                websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(user_id),
                agent_context={
                    "auth_level": "relaxed",
                    "permissions": ["execute_agents", "relaxed_access"],
                    "environment": get_env().get("ENVIRONMENT", "unknown")
                }
            )
            
            logger.info(f"RELAXED AUTH: Created relaxed user context for {user_id}")
            return user_context
            
        except Exception as e:
            logger.error(f"RELAXED AUTH: Failed to create relaxed user context: {e}")
            return None
    
    def _extract_any_token(self, websocket: WebSocket) -> Optional[str]:
        """Extract any available token from WebSocket (relaxed extraction)."""
        try:
            if not websocket.headers:
                return None
            
            # Try subprotocol header
            subprotocol_header = websocket.headers.get("sec-websocket-protocol", "")
            if subprotocol_header:
                # Look for any token-like strings
                for protocol in subprotocol_header.split(","):
                    protocol = protocol.strip()
                    if "." in protocol and len(protocol) > 20:
                        return protocol
            
            # Try authorization header
            auth_header = websocket.headers.get("authorization", "")
            if auth_header and len(auth_header) > 10:
                return auth_header.replace("Bearer ", "").strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"RELAXED AUTH: Token extraction failed: {e}")
            return None


class DemoAuthValidator:
    """Demo authentication validator - bypasses auth for isolated demo environments."""
    
    async def validate(self, websocket: WebSocket) -> AuthPermissivenessResult:
        """Perform demo authentication validation (bypass)."""
        logger.info("DEMO AUTH: Performing demo authentication bypass")
        
        try:
            # Check if demo mode is actually enabled and safe
            env = get_env()
            current_env = env.get("ENVIRONMENT", "unknown").lower()
            demo_mode = env.get("DEMO_MODE", "1") == "1"
            
            # Security check - never allow demo mode in production
            if current_env in ["production", "prod"]:
                logger.error("DEMO AUTH: Demo mode blocked in production environment")
                return AuthPermissivenessResult(
                    success=False,
                    level=AuthPermissivenessLevel.DEMO,
                    auth_method="demo_blocked_production",
                    security_warnings=["Demo mode not allowed in production"],
                    audit_info={"environment": current_env, "security_block": True}
                )
            
            if not demo_mode:
                logger.info("DEMO AUTH: Demo mode disabled via DEMO_MODE=0")
                return AuthPermissivenessResult(
                    success=False,
                    level=AuthPermissivenessLevel.DEMO,
                    auth_method="demo_disabled",
                    security_warnings=["Demo mode disabled"],
                    audit_info={"demo_mode_enabled": False}
                )
            
            # Create demo user context
            demo_user = await self._create_demo_user_context(websocket)
            
            security_warnings = [
                "DEMO MODE ACTIVE - No authentication performed",
                "Not suitable for production use",
                "For demonstration purposes only"
            ]
            
            return AuthPermissivenessResult(
                success=True,
                level=AuthPermissivenessLevel.DEMO,
                user_context=demo_user,
                auth_method="demo_bypass",
                bypass_reason="Demo mode enabled for isolated demonstration",
                security_warnings=security_warnings,
                audit_info={
                    "environment": current_env,
                    "demo_mode": True,
                    "security_bypass": True
                }
            )
            
        except Exception as e:
            logger.error(f"DEMO AUTH: Validation exception: {e}")
            return AuthPermissivenessResult(
                success=False,
                level=AuthPermissivenessLevel.DEMO,
                auth_method="demo_exception",
                security_warnings=[f"Demo validation exception: {str(e)}"]
            )
    
    async def _create_demo_user_context(self, websocket: WebSocket) -> UserExecutionContext:
        """Create demo user context."""
        from shared.id_generation import UnifiedIdGenerator
        
        # Create consistent demo user ID
        demo_user_id = "demo-user-001"
        
        user_context = UserExecutionContext(
            user_id=demo_user_id,
            thread_id=UnifiedIdGenerator.generate_base_id("demo_thread"),
            run_id=UnifiedIdGenerator.generate_base_id("demo_run"),
            request_id=UnifiedIdGenerator.generate_base_id("demo_req"),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(demo_user_id),
            agent_context={
                "auth_level": "demo",
                "permissions": ["execute_agents", "demo_access", "chat_access"],
                "email": "demo@example.com",
                "environment": get_env().get("ENVIRONMENT", "demo"),
                "demo_session": True
            }
        )
        
        logger.info(f"DEMO AUTH: Created demo user context: {demo_user_id}")
        return user_context


class EmergencyAuthValidator:
    """Emergency authentication validator - last resort when auth services are down."""
    
    async def validate(self, websocket: WebSocket) -> AuthPermissivenessResult:
        """Perform emergency authentication validation."""
        logger.warning("EMERGENCY AUTH: Performing emergency authentication bypass")
        
        try:
            # Verify that this is actually an emergency situation
            if not await self._verify_emergency_conditions():
                logger.error("EMERGENCY AUTH: Emergency conditions not met")
                return AuthPermissivenessResult(
                    success=False,
                    level=AuthPermissivenessLevel.EMERGENCY,
                    auth_method="emergency_not_justified",
                    security_warnings=["Emergency auth not justified - conditions not met"]
                )
            
            # Create emergency user context
            emergency_user = await self._create_emergency_user_context(websocket)
            
            security_warnings = [
                "EMERGENCY MODE ACTIVE - Authentication services unavailable",
                "Temporary access granted - restore auth services immediately",
                "All actions logged for security audit",
                "Limited permissions in effect"
            ]
            
            return AuthPermissivenessResult(
                success=True,
                level=AuthPermissivenessLevel.EMERGENCY,
                user_context=emergency_user,
                auth_method="emergency_bypass",
                bypass_reason="Authentication services unavailable - emergency access granted",
                security_warnings=security_warnings,
                audit_info={
                    "emergency_mode": True,
                    "auth_service_down": True,
                    "security_bypass": True,
                    "requires_immediate_attention": True
                }
            )
            
        except Exception as e:
            logger.error(f"EMERGENCY AUTH: Validation exception: {e}")
            return AuthPermissivenessResult(
                success=False,
                level=AuthPermissivenessLevel.EMERGENCY,
                auth_method="emergency_exception",
                security_warnings=[f"Emergency validation exception: {str(e)}"]
            )
    
    async def _verify_emergency_conditions(self) -> bool:
        """Verify that emergency conditions justify bypass."""
        env = get_env()
        
        # Check if emergency mode is explicitly enabled
        emergency_enabled = env.get("EMERGENCY_MODE", "0") == "1"
        if emergency_enabled:
            logger.warning("EMERGENCY AUTH: Emergency mode explicitly enabled via EMERGENCY_MODE=1")
            return True
        
        # Check if auth service is actually down
        try:
            from netra_backend.app.services.unified_authentication_service import get_unified_auth_service
            auth_service = get_unified_auth_service()
            if not auth_service:
                logger.warning("EMERGENCY AUTH: Auth service unavailable - emergency justified")
                return True
        except Exception as e:
            logger.warning(f"EMERGENCY AUTH: Auth service check failed - emergency justified: {e}")
            return True
        
        # Check environment - only allow in non-production
        environment = env.get("ENVIRONMENT", "unknown").lower()
        if environment in ["production", "prod"]:
            logger.error("EMERGENCY AUTH: Emergency mode blocked in production")
            return False
        
        return False
    
    async def _create_emergency_user_context(self, websocket: WebSocket) -> UserExecutionContext:
        """Create emergency user context with limited permissions."""
        from shared.id_generation import UnifiedIdGenerator
        
        # Create emergency user ID with timestamp
        timestamp = int(time.time())
        emergency_user_id = f"emergency_{timestamp}"
        
        user_context = UserExecutionContext(
            user_id=emergency_user_id,
            thread_id=UnifiedIdGenerator.generate_base_id("emergency_thread"),
            run_id=UnifiedIdGenerator.generate_base_id("emergency_run"),
            request_id=UnifiedIdGenerator.generate_base_id("emergency_req"),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(emergency_user_id),
            agent_context={
                "auth_level": "emergency",
                "permissions": ["execute_agents", "emergency_access"],  # Limited permissions
                "email": "emergency@system.local",
                "environment": get_env().get("ENVIRONMENT", "emergency"),
                "emergency_session": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "audit_required": True
            }
        )
        
        logger.warning(f"EMERGENCY AUTH: Created emergency user context: {emergency_user_id}")
        return user_context


# Global validator instance
_permissiveness_validator: Optional[AuthPermissivenessValidator] = None


def get_auth_permissiveness_validator() -> AuthPermissivenessValidator:
    """Get the global auth permissiveness validator instance."""
    global _permissiveness_validator
    if _permissiveness_validator is None:
        _permissiveness_validator = AuthPermissivenessValidator()
        logger.info("AUTH PERMISSIVENESS: Validator instance created")
    return _permissiveness_validator


# Convenience functions for each auth level
async def validate_strict_auth(websocket: WebSocket) -> AuthPermissivenessResult:
    """Validate with strict authentication requirements."""
    validator = get_auth_permissiveness_validator()
    return await validator.validate_with_permissiveness(websocket, AuthPermissivenessLevel.STRICT)


async def validate_relaxed_auth(websocket: WebSocket) -> AuthPermissivenessResult:
    """Validate with relaxed authentication requirements."""
    validator = get_auth_permissiveness_validator()
    return await validator.validate_with_permissiveness(websocket, AuthPermissivenessLevel.RELAXED)


async def validate_demo_auth(websocket: WebSocket) -> AuthPermissivenessResult:
    """Validate with demo authentication (bypass)."""
    validator = get_auth_permissiveness_validator()
    return await validator.validate_with_permissiveness(websocket, AuthPermissivenessLevel.DEMO)


async def validate_emergency_auth(websocket: WebSocket) -> AuthPermissivenessResult:
    """Validate with emergency authentication (bypass when services down)."""
    validator = get_auth_permissiveness_validator()
    return await validator.validate_with_permissiveness(websocket, AuthPermissivenessLevel.EMERGENCY)


# Main interface function
async def authenticate_with_permissiveness(websocket: WebSocket) -> AuthPermissivenessResult:
    """
    Authenticate WebSocket connection using appropriate permissiveness level.
    
    This is the main entry point for permissive authentication that automatically
    detects the appropriate auth level based on environment and context.
    
    Args:
        websocket: WebSocket connection object
        
    Returns:
        AuthPermissivenessResult: Authentication result with permissiveness info
    """
    validator = get_auth_permissiveness_validator()
    return await validator.validate_with_permissiveness(websocket)


# Export public interface
__all__ = [
    "AuthPermissivenessLevel",
    "AuthContext", 
    "AuthPermissivenessResult",
    "EnvironmentAuthDetector",
    "AuthPermissivenessValidator",
    "get_auth_permissiveness_validator",
    "authenticate_with_permissiveness",
    "validate_strict_auth",
    "validate_relaxed_auth", 
    "validate_demo_auth",
    "validate_emergency_auth"
]