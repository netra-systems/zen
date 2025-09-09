"""Agent Execution Validator - SSOT for agent execution validation and business logic.

This module provides comprehensive validation for agent execution requests,
including business rule validation, security sanitization, and audit trail creation.

Business Value Justification:
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Revenue Protection and Security
- Value Impact: Validates $500K+ ARR agent execution workflows with proper tier enforcement
- Strategic Impact: Ensures secure, compliant agent execution across all customer segments

SSOT Principle: This is the canonical implementation for agent execution validation.
All agent execution flows must go through this validator for consistency and security.
"""

import re
import hashlib
import html
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid
from dataclasses import dataclass

# SSOT Imports - Absolute imports as per CLAUDE.md
from shared.types.core_types import UserID, ensure_user_id
from shared.types.agent_types import AgentExecutionRequest, AgentExecutionResult, AgentValidationResult
from shared.types.execution_types import StronglyTypedUserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# =============================================================================
# Business Rule Configuration - SSOT for tier-based limits
# =============================================================================

@dataclass
class TierConfiguration:
    """Configuration for user tier limits and capabilities."""
    daily_execution_limit: int
    concurrent_execution_limit: int
    memory_limit_mb: int
    timeout_seconds: int
    priority_level: int
    allowed_agents: List[str]
    premium_features: List[str]


# SSOT tier configurations - centralized business rules
TIER_CONFIGURATIONS = {
    "free": TierConfiguration(
        daily_execution_limit=10,
        concurrent_execution_limit=1,
        memory_limit_mb=256,
        timeout_seconds=30,
        priority_level=1,
        allowed_agents=["basic_analysis", "simple_optimization"],
        premium_features=[]
    ),
    "early": TierConfiguration(
        daily_execution_limit=100,
        concurrent_execution_limit=3,
        memory_limit_mb=512,
        timeout_seconds=60,
        priority_level=3,
        allowed_agents=["basic_analysis", "advanced_analysis", "data_optimization", "database_optimization"],
        premium_features=["advanced_optimization", "multi_table_analysis"]
    ),
    "enterprise": TierConfiguration(
        daily_execution_limit=1000,
        concurrent_execution_limit=10,
        memory_limit_mb=2048,
        timeout_seconds=300,
        priority_level=5,
        allowed_agents=["*"],  # All agents allowed
        premium_features=["ai_powered_optimization", "custom_agents", "priority_execution"]
    )
}

# Security patterns for input sanitization
DANGEROUS_PATTERNS = [
    r'(?i)(drop|delete|truncate)\s+table',
    r'(?i)select\s+.*\s+from\s+.*\s+where.*[\'"];',
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'\$\([^)]*\)',  # Command injection patterns
    r'rm\s+-rf',
    r'eval\s*\(',
    r'exec\s*\(',
]


# =============================================================================
# Agent Execution Validator - Main validation class
# =============================================================================

class AgentExecutionValidator:
    """Comprehensive validator for agent execution requests and business logic.
    
    This class implements all validation, security, and business rule enforcement
    for agent execution across the platform. It serves as the SSOT for:
    - Request validation and sanitization
    - Business rule enforcement by user tier
    - Security checks and audit trail creation
    - Result structure validation
    """
    
    def __init__(self):
        """Initialize validator with configuration."""
        self.tier_configs = TIER_CONFIGURATIONS
        self.dangerous_patterns = [re.compile(pattern) for pattern in DANGEROUS_PATTERNS]
    
    # =========================================================================
    # Core Validation Methods
    # =========================================================================
    
    def validate_execution_request(self, execution_request: AgentExecutionRequest) -> AgentValidationResult:
        """Validate complete agent execution request with business rules.
        
        Args:
            execution_request: The agent execution request to validate
            
        Returns:
            AgentValidationResult: Detailed validation result
        """
        try:
            # Initialize validation result
            result = AgentValidationResult(
                is_valid=True,
                user_id=execution_request.user_id,
                validation_passed={}
            )
            
            # Validate request format
            self._validate_request_format(execution_request, result)
            
            # Validate user permissions
            self._validate_user_permissions(execution_request, result)
            
            # Validate agent type access
            self._validate_agent_type_access(execution_request, result)
            
            # Validate input security
            self._validate_input_security(execution_request, result)
            
            # Set overall validity based on individual checks
            result.is_valid = all(result.validation_passed.values())
            
            # Set error message if validation failed
            if not result.is_valid:
                failed_checks = [key for key, passed in result.validation_passed.items() if not passed]
                result.error_message = f"Validation failed for: {', '.join(failed_checks)}"
            
            logger.info(f"Agent execution request validation completed for user {execution_request.user_id}: {'PASSED' if result.is_valid else 'FAILED'}")
            return result
            
        except Exception as e:
            logger.error(f"Agent execution validation error for user {execution_request.user_id}: {e}")
            return AgentValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}",
                user_id=execution_request.user_id,
                validation_passed={"system_error": False}
            )
    
    def _validate_request_format(self, request: AgentExecutionRequest, result: AgentValidationResult):
        """Validate basic request format requirements."""
        try:
            # Check required fields
            if not request.request_data:
                result.add_validation_check("request_format", False, "request_data cannot be empty")
                return
            
            # Check user_input exists and is reasonable
            user_input = request.request_data.get("user_input", "")
            if not user_input or len(user_input.strip()) < 3:
                result.add_validation_check("request_format", False, "user_input must be at least 3 characters")
                return
            
            if len(user_input) > 50000:  # Reasonable upper limit
                result.add_validation_check("request_format", False, "user_input exceeds maximum length")
                return
            
            result.add_validation_check("request_format", True)
            
        except Exception as e:
            logger.error(f"Request format validation error: {e}")
            result.add_validation_check("request_format", False, f"Format validation error: {str(e)}")
    
    def _validate_user_permissions(self, request: AgentExecutionRequest, result: AgentValidationResult):
        """Validate user has required permissions for agent execution."""
        try:
            user_permissions = request.user_permissions or []
            
            # Agent execution requires at least 'read' permission
            if "read" not in user_permissions:
                result.add_validation_check("user_permissions", False, "Agent execution requires 'read' permission")
                return
            
            # Check agent type specific requirements
            agent_type = request.request_data.get("agent_type", "")
            if "premium" in agent_type.lower() and "premium" not in user_permissions:
                result.add_validation_check("user_permissions", False, "Premium agent requires 'premium' permission")
                return
            
            result.add_validation_check("user_permissions", True)
            
        except Exception as e:
            logger.error(f"User permissions validation error: {e}")
            result.add_validation_check("user_permissions", False, f"Permission validation error: {str(e)}")
    
    def _validate_agent_type_access(self, request: AgentExecutionRequest, result: AgentValidationResult):
        """Validate user has access to the requested agent type."""
        try:
            agent_type = request.request_data.get("agent_type", "")
            if not agent_type:
                result.add_validation_check("agent_type", False, "agent_type is required")
                return
            
            # Determine user tier based on permissions (simplified logic)
            user_tier = self._determine_user_tier(request.user_permissions)
            tier_config = self.tier_configs.get(user_tier)
            
            if not tier_config:
                result.add_validation_check("agent_type", False, f"Invalid user tier: {user_tier}")
                return
            
            # Check if agent is allowed for this tier
            if "*" not in tier_config.allowed_agents and agent_type not in tier_config.allowed_agents:
                result.add_validation_check("agent_type", False, 
                                          f"Agent type '{agent_type}' not allowed for {user_tier} tier")
                return
            
            result.add_validation_check("agent_type", True)
            
        except Exception as e:
            logger.error(f"Agent type validation error: {e}")
            result.add_validation_check("agent_type", False, f"Agent type validation error: {str(e)}")
    
    def _validate_input_security(self, request: AgentExecutionRequest, result: AgentValidationResult):
        """Validate input for security threats."""
        try:
            user_input = request.request_data.get("user_input", "")
            
            # Check for dangerous patterns
            for pattern in self.dangerous_patterns:
                if pattern.search(user_input):
                    result.add_validation_check("input_security", False, 
                                              "Input contains potentially dangerous content")
                    return
            
            result.add_validation_check("input_security", True)
            
        except Exception as e:
            logger.error(f"Input security validation error: {e}")
            result.add_validation_check("input_security", False, f"Security validation error: {str(e)}")
    
    # =========================================================================
    # Input Sanitization
    # =========================================================================
    
    def sanitize_user_input(self, user_input: str, context_type: str = "general") -> str:
        """Sanitize user input for security while preserving legitimate content.
        
        Args:
            user_input: Raw user input to sanitize
            context_type: Context for sanitization (e.g., "database_optimization")
            
        Returns:
            str: Sanitized input safe for processing
        """
        try:
            if not user_input:
                return ""
            
            sanitized = user_input
            
            # Remove dangerous patterns first, before HTML escaping
            for pattern in self.dangerous_patterns:
                if context_type == "database_optimization" and "select" in pattern.pattern.lower():
                    # Allow legitimate SELECT queries in database context
                    continue
                sanitized = pattern.sub("[FILTERED]", sanitized)
            
            # Only apply HTML escaping if we're not in a technical context where it's needed
            if context_type not in ["database_optimization", "technical_query"]:
                sanitized = html.escape(sanitized)
            
            # Log sanitization if changes were made
            if sanitized != user_input:
                logger.warning(f"User input sanitized for context '{context_type}' - removed potentially dangerous content")
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Input sanitization error: {e}")
            return "[SANITIZATION_ERROR]"
    
    # =========================================================================
    # Business Logic Methods
    # =========================================================================
    
    def calculate_execution_timeout(self, user_tier: str, agent_type: str) -> int:
        """Calculate appropriate execution timeout based on user tier and agent complexity.
        
        Args:
            user_tier: User tier (free, early, enterprise)
            agent_type: Type of agent being executed
            
        Returns:
            int: Timeout in seconds
        """
        try:
            tier_config = self.tier_configs.get(user_tier.lower())
            if not tier_config:
                logger.warning(f"Unknown user tier '{user_tier}', defaulting to free tier timeout")
                return self.tier_configs["free"].timeout_seconds
            
            base_timeout = tier_config.timeout_seconds
            
            # Adjust based on agent complexity
            if "premium" in agent_type.lower() or "advanced" in agent_type.lower():
                return min(base_timeout * 2, 300)  # Max 5 minutes even for complex agents
            
            return base_timeout
            
        except Exception as e:
            logger.error(f"Timeout calculation error: {e}")
            return 30  # Safe default
    
    def calculate_execution_priority(self, user_tier: str, user_permissions: List[str]) -> int:
        """Calculate execution priority based on user tier and permissions.
        
        Args:
            user_tier: User tier (free, early, enterprise)
            user_permissions: List of user permissions
            
        Returns:
            int: Priority level (higher = higher priority)
        """
        try:
            tier_config = self.tier_configs.get(user_tier.lower())
            if not tier_config:
                return 1  # Lowest priority for unknown tiers
            
            base_priority = tier_config.priority_level
            
            # Boost priority for premium permissions
            if "premium" in user_permissions:
                base_priority += 1
            
            return min(base_priority, 5)  # Max priority is 5
            
        except Exception as e:
            logger.error(f"Priority calculation error: {e}")
            return 1
    
    def get_resource_limits(self, user_tier: str) -> Dict[str, int]:
        """Get resource limits for user tier.
        
        Args:
            user_tier: User tier (free, early, enterprise)
            
        Returns:
            Dict: Resource limits configuration
        """
        try:
            tier_config = self.tier_configs.get(user_tier.lower())
            if not tier_config:
                logger.warning(f"Unknown user tier '{user_tier}', defaulting to free tier limits")
                tier_config = self.tier_configs["free"]
            
            return {
                "daily_execution_limit": tier_config.daily_execution_limit,
                "concurrent_execution_limit": tier_config.concurrent_execution_limit,
                "memory_limit_mb": tier_config.memory_limit_mb
            }
            
        except Exception as e:
            logger.error(f"Resource limits error: {e}")
            return self.tier_configs["free"].__dict__
    
    def create_business_friendly_error(self, error_type: str, user_tier: str) -> Dict[str, str]:
        """Create user-friendly error messages with recovery suggestions.
        
        Args:
            error_type: Type of error encountered
            user_tier: User's current tier
            
        Returns:
            Dict: Error response with user message and recovery action
        """
        try:
            error_responses = {
                "insufficient_permissions": {
                    "free": {
                        "user_message": "This feature requires a premium subscription. Upgrade to Early tier to unlock advanced AI analysis and optimization tools.",
                        "recovery_action": "upgrade_to_early_tier"
                    },
                    "early": {
                        "user_message": "This premium feature is available in Enterprise tier. Contact our team to upgrade for unlimited AI-powered optimization.",
                        "recovery_action": "contact_sales_for_enterprise"
                    },
                    "enterprise": {
                        "user_message": "You don't have permission for this operation. Contact your administrator to review your account permissions.",
                        "recovery_action": "contact_administrator"
                    }
                },
                "resource_limit_exceeded": {
                    "free": {
                        "user_message": "You've reached your daily limit of 10 agent executions. Your limit resets tomorrow, or upgrade to Early tier for 100 daily executions.",
                        "recovery_action": "wait_for_reset_or_upgrade"
                    },
                    "early": {
                        "user_message": "You've reached your daily limit of 100 agent executions. Your limit resets tomorrow, or upgrade to Enterprise for 1000 daily executions.",
                        "recovery_action": "wait_for_reset_or_upgrade"
                    },
                    "enterprise": {
                        "user_message": "You've reached your daily limit. This is unusual for Enterprise accounts - please contact support for assistance.",
                        "recovery_action": "contact_support"
                    }
                },
                "agent_timeout": {
                    "free": {
                        "user_message": "Your request took too long to process (30 second limit). Please try with a simpler request, or upgrade for longer processing times.",
                        "recovery_action": "retry_with_simpler_request"
                    },
                    "early": {
                        "user_message": "Your request timed out after 60 seconds. Consider breaking down complex requests, or upgrade to Enterprise for extended processing time.",
                        "recovery_action": "retry_with_simpler_request"
                    },
                    "enterprise": {
                        "user_message": "Your request timed out after 5 minutes. This may indicate a complex analysis - please try again or contact support if the issue persists.",
                        "recovery_action": "retry_with_simpler_request"
                    }
                }
            }
            
            tier_responses = error_responses.get(error_type, {})
            response = tier_responses.get(user_tier.lower())
            
            if not response:
                # Default error response
                response = {
                    "user_message": "An unexpected error occurred. Please try again or contact support if the problem persists.",
                    "recovery_action": "retry_or_contact_support"
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Business friendly error creation error: {e}")
            return {
                "user_message": "A system error occurred. Please contact support.",
                "recovery_action": "contact_support"
            }
    
    # =========================================================================
    # Result Validation
    # =========================================================================
    
    def validate_result_structure(self, execution_result: AgentExecutionResult) -> Dict[str, Any]:
        """Validate agent execution result structure for business requirements.
        
        Args:
            execution_result: Agent execution result to validate
            
        Returns:
            Dict: Validation result with is_valid flag and details
        """
        try:
            validation = {
                "is_valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Check required fields
            required_fields = ["user_id", "success", "result_data"]
            for field in required_fields:
                if not hasattr(execution_result, field) or getattr(execution_result, field) is None:
                    validation["errors"].append(f"Missing required field: {field}")
                    validation["is_valid"] = False
            
            # Validate result data structure
            if hasattr(execution_result, 'result_data') and execution_result.result_data:
                result_data = execution_result.result_data
                
                # Check for business value fields
                if isinstance(result_data, dict):
                    if not any(key in result_data for key in ["recommendations", "analysis", "insights", "optimization"]):
                        validation["warnings"].append("Result may lack business value indicators")
                
            return validation
            
        except Exception as e:
            logger.error(f"Result structure validation error: {e}")
            return {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    # =========================================================================
    # Audit and Compliance
    # =========================================================================
    
    def create_audit_metadata(self, execution_request: AgentExecutionRequest) -> Dict[str, Any]:
        """Create comprehensive audit metadata for compliance tracking.
        
        Args:
            execution_request: The agent execution request
            
        Returns:
            Dict: Audit metadata for compliance logging
        """
        try:
            # Create request fingerprint for tracking
            request_content = f"{execution_request.user_id}:{execution_request.thread_id}:{execution_request.timestamp.isoformat()}"
            request_hash = hashlib.sha256(request_content.encode()).hexdigest()[:16]
            
            audit_metadata = {
                "user_id": str(execution_request.user_id),
                "timestamp": execution_request.timestamp.isoformat(),
                "request_type": "agent_execution",
                "user_permissions": execution_request.user_permissions,
                "request_hash": request_hash,
                "ip_address": "0.0.0.0",  # Would be populated from request context in real implementation
                "user_agent": "Netra-Agent-Executor/1.0",  # Would be from request headers
                "session_id": str(uuid.uuid4()),  # Would be from session context
                "compliance_flags": {
                    "data_processing": True,
                    "user_consent": True,
                    "retention_policy": "90_days"
                }
            }
            
            return audit_metadata
            
        except Exception as e:
            logger.error(f"Audit metadata creation error: {e}")
            return {
                "user_id": str(execution_request.user_id) if execution_request.user_id else "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_type": "agent_execution",
                "error": f"Audit creation failed: {str(e)}"
            }
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _determine_user_tier(self, user_permissions: List[str]) -> str:
        """Determine user tier based on permissions (simplified logic)."""
        if "premium" in user_permissions:
            return "enterprise"
        elif "write" in user_permissions:
            return "early"
        else:
            return "free"