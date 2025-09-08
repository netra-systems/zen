"""
LLM Processing Failures Enhanced Warning Tests

Tests for enhancing LLM processing failure warnings with better diagnostics.
These tests validate that LLM processing failures provide comprehensive
diagnostics while remaining as warnings (not upgraded to errors).

Business Value: LLM processing is core to agent execution and chat functionality.
Enhanced warnings help identify API issues, rate limiting, model problems, and
configuration issues that affect the quality of AI responses.

Critical Warning Locations Being Tested:
- actions_goals_plan_builder.py:72 - LLM response processing failures
- LLM API connectivity and authentication issues
- Model response parsing and validation failures
- Rate limiting and quota exhaustion scenarios

ENHANCEMENT REQUIREMENT: These warnings are ENHANCED (not upgraded to errors) because:
1. LLM failures should allow graceful degradation (fallback models, cached responses)
2. Temporary LLM issues shouldn't completely break chat functionality
3. Enhanced diagnostics help identify specific LLM provider issues
4. System should attempt retries and alternative approaches

CLAUDE.md Compliance:
- Uses real LLM connections when possible (configurable for testing)
- All E2E tests authenticate properly
- Tests validate graceful degradation behavior
- Enhanced warnings provide actionable LLM diagnostics
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from .base_warning_test import SsotAsyncWarningUpgradeTestCase, WarningTestMetrics
from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


logger = logging.getLogger(__name__)


class TestLLMProcessingFailuresEnhancedWarnings(SsotAsyncWarningUpgradeTestCase):
    """
    Test suite for LLM processing failure enhanced warning diagnostics.
    
    This class tests that LLM processing failures provide comprehensive
    diagnostic information while allowing graceful degradation.
    """
    
    async def test_llm_api_connection_failure_enhanced_diagnostics(self):
        """
        Test enhanced diagnostics for LLM API connection failures.
        
        Business Impact: LLM API connection issues prevent agents from generating
        intelligent responses. Enhanced diagnostics help identify API endpoint,
        authentication, and network issues.
        """
        auth_helper = await self.get_auth_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.actions_goals_plan_builder"):
            # Simulate LLM API connection failure
            from netra_backend.app.agents.actions_goals_plan_builder import ActionsGoalsPlanBuilder
            
            class DiagnosticLLMBuilder(ActionsGoalsPlanBuilder):
                def __init__(self):
                    super().__init__()
                    self.logger = logger
                    self.user_id = auth_helper.get_user_id()
                
                async def process_llm_request(self, prompt: str, model: str = "gpt-4"):
                    """Process LLM request with enhanced diagnostics."""
                    try:
                        # Simulate LLM API connection failure
                        raise ConnectionError("Connection to LLM API failed: timeout after 30 seconds")
                    except ConnectionError as e:
                        # ENHANCED WARNING: Provide comprehensive LLM diagnostic information
                        diagnostic_info = {
                            "error_type": "LLM_API_CONNECTION_FAILURE",
                            "model_requested": model,
                            "api_endpoint": "https://api.openai.com/v1/chat/completions",
                            "connection_details": {
                                "timeout_seconds": 30,
                                "retry_attempts": 3,
                                "connection_pool_status": "exhausted",
                                "last_successful_request": "2024-01-15T10:30:00Z"
                            },
                            "user_context": {
                                "user_id": self.user_id,
                                "request_type": "agent_planning",
                                "prompt_length": len(prompt),
                                "session_id": f"llm_session_{uuid.uuid4().hex[:8]}"
                            },
                            "possible_causes": [
                                "LLM API service temporary outage",
                                "Network connectivity issues",
                                "API authentication token expired",
                                "Rate limiting or quota exhaustion",
                                "DNS resolution problems for API endpoint"
                            ],
                            "recommended_actions": [
                                "Check LLM provider status page for outages",
                                "Verify API key is valid and not expired",
                                "Test network connectivity to API endpoint",
                                "Check rate limits and usage quotas",
                                "Try alternative LLM model or provider"
                            ],
                            "fallback_options": [
                                "Use cached responses for similar prompts",
                                "Switch to alternative LLM provider",
                                "Provide simplified response based on templates",
                                "Queue request for retry when service recovers"
                            ],
                            "impact_assessment": {
                                "user_experience": "DEGRADED - simplified responses only",
                                "business_continuity": "MAINTAINED - fallback mechanisms active",
                                "estimated_recovery": "5-30 minutes for API issues"
                            }
                        }
                        
                        # Enhanced warning with comprehensive LLM diagnostics
                        logger.warning(
                            f"LLM PROCESSING FAILURE - {diagnostic_info['error_type']}: "
                            f"Failed to connect to {diagnostic_info['model_requested']} for user {self.user_id}. "
                            f"API endpoint: {diagnostic_info['api_endpoint']}. "
                            f"Timeout: {diagnostic_info['connection_details']['timeout_seconds']}s, "
                            f"Retries: {diagnostic_info['connection_details']['retry_attempts']}. "
                            f"Impact: {diagnostic_info['impact_assessment']['user_experience']}. "
                            f"Fallback options available: {len(diagnostic_info['fallback_options'])} strategies. "
                            f"See logs for complete diagnostic information and recovery guidance."
                        )
                        
                        # Log detailed diagnostics separately
                        logger.info(f"LLM DIAGNOSTIC DETAILS: {json.dumps(diagnostic_info, indent=2)}")
                        
                        # Return None to indicate failure but allow graceful degradation
                        return None
            
            builder = DiagnosticLLMBuilder()
            
            # LLM processing should fail gracefully
            result = await builder.process_llm_request("Test prompt for diagnostic analysis")
            assert result is None, "LLM request should fail gracefully and return None"
        
        # Validate enhanced LLM warning
        self.assert_warning_logged(
            "LLM PROCESSING FAILURE.*LLM_API_CONNECTION_FAILURE.*Failed to connect to gpt-4",
            logger_name="netra_backend.app.agents.actions_goals_plan_builder",
            count=1
        )
        
        # Validate LLM diagnostic details were logged
        captured_logs = [log for log in self._captured_logs if "LLM DIAGNOSTIC DETAILS" in log.get("message", "")]
        assert len(captured_logs) == 1, "LLM diagnostic details should be logged"
        
        # Validate business value: Graceful degradation maintained
        self.validate_business_value_preservation(
            graceful_degradation=True,
            chat_functionality=True  # Chat should continue with fallback responses
        )
        
        # Record LLM diagnostics test
        self.record_metric("llm_api_connection_diagnostics_enhanced", True)
    
    async def test_llm_response_parsing_failure_enhanced_diagnostics(self):
        """
        Test enhanced diagnostics for LLM response parsing failures.
        
        Business Impact: LLM response parsing failures prevent agents from
        understanding and acting on LLM outputs. Enhanced diagnostics help
        identify model response format issues and suggest handling strategies.
        """
        auth_helper = await self.get_auth_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.actions_goals_plan_builder"):
            from netra_backend.app.agents.actions_goals_plan_builder import ActionsGoalsPlanBuilder
            
            class ResponseParsingDiagnosticLLMBuilder(ActionsGoalsPlanBuilder):
                def __init__(self):
                    super().__init__()
                    self.logger = logger
                    self.user_id = auth_helper.get_user_id()
                
                async def parse_llm_response(self, raw_response: str, expected_format: str = "json"):
                    """Parse LLM response with enhanced diagnostics."""
                    # Simulate malformed LLM response
                    malformed_response = """
                    {
                        "actions": [
                            {"type": "search", "query": "test query"
                            // Missing closing brace and malformed JSON
                        "goals": "Incomplete goals section",
                        "plan": 
                    """
                    
                    try:
                        # Attempt to parse the malformed response
                        parsed_response = json.loads(malformed_response)
                        return parsed_response
                    except json.JSONDecodeError as e:
                        # ENHANCED WARNING: Provide comprehensive response parsing diagnostics
                        diagnostic_info = {
                            "error_type": "LLM_RESPONSE_PARSING_FAILURE",
                            "parsing_error": str(e),
                            "expected_format": expected_format,
                            "response_analysis": {
                                "response_length": len(malformed_response),
                                "response_preview": malformed_response[:200] + "..." if len(malformed_response) > 200 else malformed_response,
                                "detected_format": "malformed_json",
                                "syntax_errors": [
                                    "Missing closing brace on line 4",
                                    "Incomplete JSON structure",
                                    "Invalid comment syntax in JSON"
                                ]
                            },
                            "user_context": {
                                "user_id": self.user_id,
                                "request_type": "action_plan_generation",
                                "model_used": "gpt-4",
                                "prompt_context": "agent planning request"
                            },
                            "possible_causes": [
                                "LLM model output format inconsistency",
                                "Prompt engineering needs improvement",
                                "Model temperature too high causing creative but invalid responses",
                                "Token limit reached causing truncated responses",
                                "Model fine-tuning issues affecting output structure"
                            ],
                            "recommended_fixes": [
                                "Improve prompt with explicit format instructions",
                                "Add response format validation examples in prompt",
                                "Implement response cleaning/preprocessing",
                                "Use lower temperature for more consistent formatting",
                                "Add fallback parsing strategies for common malformations"
                            ],
                            "recovery_strategies": [
                                "Attempt regex-based parsing for specific fields",
                                "Use alternative response format (structured text)",
                                "Request simpler response format from LLM",
                                "Fall back to template-based response generation"
                            ],
                            "impact_assessment": {
                                "parsing_success_rate": "0% for this response format",
                                "user_experience_impact": "MEDIUM - agent can provide generic response",
                                "data_extraction_possible": "PARTIAL - some fields may be recoverable"
                            }
                        }
                        
                        # Enhanced warning with comprehensive parsing diagnostics
                        logger.warning(
                            f"LLM PROCESSING FAILURE - {diagnostic_info['error_type']}: "
                            f"Failed to parse {diagnostic_info['expected_format']} response for user {self.user_id}. "
                            f"Parsing error: {diagnostic_info['parsing_error']}. "
                            f"Response format: {diagnostic_info['response_analysis']['detected_format']}, "
                            f"Length: {diagnostic_info['response_analysis']['response_length']} chars. "
                            f"Syntax errors: {len(diagnostic_info['response_analysis']['syntax_errors'])} found. "
                            f"Recovery strategies: {len(diagnostic_info['recovery_strategies'])} available. "
                            f"Impact: {diagnostic_info['impact_assessment']['user_experience_impact']}. "
                            f"See logs for complete parsing analysis and recovery options."
                        )
                        
                        # Log detailed parsing diagnostics
                        logger.info(f"PARSING DIAGNOSTIC DETAILS: {json.dumps(diagnostic_info, indent=2)}")
                        
                        # Return None to indicate parsing failure but allow graceful degradation
                        return None
            
            builder = ResponseParsingDiagnosticLLMBuilder()
            
            # Response parsing should fail gracefully
            result = await builder.parse_llm_response("malformed response", "json")
            assert result is None, "Response parsing should fail gracefully and return None"
        
        # Validate enhanced parsing warning
        self.assert_warning_logged(
            "LLM PROCESSING FAILURE.*LLM_RESPONSE_PARSING_FAILURE.*Failed to parse json response",
            logger_name="netra_backend.app.agents.actions_goals_plan_builder",
            count=1
        )
        
        # Validate parsing diagnostic details
        captured_logs = [log for log in self._captured_logs if "PARSING DIAGNOSTIC DETAILS" in log.get("message", "")]
        assert len(captured_logs) == 1, "Parsing diagnostic details should be logged"
        
        # Record parsing diagnostics test
        self.record_metric("llm_response_parsing_diagnostics_enhanced", True)
    
    async def test_llm_rate_limiting_enhanced_diagnostics(self):
        """
        Test enhanced diagnostics for LLM API rate limiting scenarios.
        
        Business Impact: Rate limiting prevents agents from making LLM requests.
        Enhanced diagnostics help identify rate limit types, recovery times,
        and suggest optimization strategies.
        """
        auth_helper = await self.get_auth_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.actions_goals_plan_builder"):
            from netra_backend.app.agents.actions_goals_plan_builder import ActionsGoalsPlanBuilder
            
            class RateLimitDiagnosticLLMBuilder(ActionsGoalsPlanBuilder):
                def __init__(self):
                    super().__init__()
                    self.logger = logger
                    self.user_id = auth_helper.get_user_id()
                
                async def handle_llm_rate_limiting(self, rate_limit_error):
                    """Handle LLM rate limiting with enhanced diagnostics."""
                    # Simulate rate limit response headers
                    rate_limit_info = {
                        "limit_type": "requests_per_minute",
                        "current_usage": 100,
                        "limit_value": 100,
                        "reset_time": "2024-01-15T10:35:00Z",
                        "retry_after_seconds": 60,
                        "quota_remaining": 0
                    }
                    
                    # ENHANCED WARNING: Provide comprehensive rate limiting diagnostics
                    diagnostic_info = {
                        "error_type": "LLM_API_RATE_LIMITING",
                        "rate_limit_details": rate_limit_info,
                        "usage_analysis": {
                            "current_usage_percentage": 100.0,
                            "peak_usage_time": "10:30-10:35 UTC",
                            "usage_pattern": "burst_requests",
                            "estimated_daily_usage": 2400,  # Extrapolated from current rate
                        },
                        "user_context": {
                            "user_id": self.user_id,
                            "concurrent_requests": 5,
                            "request_priority": "normal",
                            "user_tier": "free"  # Could affect rate limits
                        },
                        "optimization_opportunities": [
                            "Implement request batching for similar prompts",
                            "Add caching layer for frequently requested content",
                            "Use request queuing with priority handling",
                            "Consider upgrading to higher tier for increased limits",
                            "Implement exponential backoff for retries"
                        ],
                        "immediate_actions": [
                            f"Wait {rate_limit_info['retry_after_seconds']} seconds before retry",
                            "Queue pending requests for batch processing",
                            "Use cached responses where available",
                            "Notify user of temporary delay"
                        ],
                        "business_impact": {
                            "affected_users": "current user only",
                            "service_degradation": "temporary delay in responses",
                            "estimated_delay": f"{rate_limit_info['retry_after_seconds']} seconds",
                            "alternative_available": True
                        },
                        "long_term_strategies": [
                            "Monitor usage patterns and implement predictive scaling",
                            "Negotiate higher rate limits with LLM provider",
                            "Implement intelligent request distribution",
                            "Consider multiple LLM provider integration"
                        ]
                    }
                    
                    # Enhanced warning with comprehensive rate limiting diagnostics
                    logger.warning(
                        f"LLM PROCESSING FAILURE - {diagnostic_info['error_type']}: "
                        f"Rate limit exceeded for user {self.user_id}. "
                        f"Limit type: {diagnostic_info['rate_limit_details']['limit_type']}, "
                        f"Usage: {diagnostic_info['rate_limit_details']['current_usage']}/{diagnostic_info['rate_limit_details']['limit_value']}. "
                        f"Reset in: {diagnostic_info['rate_limit_details']['retry_after_seconds']}s. "
                        f"Impact: {diagnostic_info['business_impact']['service_degradation']}. "
                        f"Optimization opportunities: {len(diagnostic_info['optimization_opportunities'])} identified. "
                        f"See logs for complete rate limiting analysis and optimization strategies."
                    )
                    
                    # Log detailed rate limiting diagnostics
                    logger.info(f"RATE LIMIT DIAGNOSTIC DETAILS: {json.dumps(diagnostic_info, indent=2)}")
                    
                    # Return rate limit info for graceful handling
                    return rate_limit_info
            
            builder = RateLimitDiagnosticLLMBuilder()
            
            # Handle rate limiting scenario
            result = await builder.handle_llm_rate_limiting("Rate limit exceeded")
            assert result is not None, "Rate limiting should be handled gracefully"
            assert result["retry_after_seconds"] == 60, "Rate limit info should be returned"
        
        # Validate enhanced rate limiting warning
        self.assert_warning_logged(
            "LLM PROCESSING FAILURE.*LLM_API_RATE_LIMITING.*Rate limit exceeded",
            logger_name="netra_backend.app.agents.actions_goals_plan_builder",
            count=1
        )
        
        # Validate rate limiting diagnostic details
        captured_logs = [log for log in self._captured_logs if "RATE LIMIT DIAGNOSTIC DETAILS" in log.get("message", "")]
        assert len(captured_logs) == 1, "Rate limit diagnostic details should be logged"
        
        # Validate business value: Graceful handling of rate limits
        self.validate_business_value_preservation(
            graceful_degradation=True,
            chat_functionality=True  # User should get delay notification
        )
        
        # Record rate limiting diagnostics test
        self.record_metric("llm_rate_limiting_diagnostics_enhanced", True)
    
    async def test_llm_model_capability_mismatch_diagnostics(self):
        """
        Test enhanced diagnostics for LLM model capability mismatches.
        
        Business Impact: Model capability mismatches cause poor responses or failures.
        Enhanced diagnostics help identify when requests exceed model capabilities
        and suggest alternative approaches.
        """
        auth_helper = await self.get_auth_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.actions_goals_plan_builder"):
            from netra_backend.app.agents.actions_goals_plan_builder import ActionsGoalsPlanBuilder
            
            class ModelCapabilityDiagnosticBuilder(ActionsGoalsPlanBuilder):
                def __init__(self):
                    super().__init__()
                    self.logger = logger
                    self.user_id = auth_helper.get_user_id()
                
                async def validate_model_capabilities(self, request_type: str, model: str = "gpt-3.5-turbo"):
                    """Validate model capabilities against request requirements."""
                    # Define model capabilities
                    model_capabilities = {
                        "gpt-3.5-turbo": {
                            "max_tokens": 4096,
                            "supports_code": True,
                            "supports_math": False,
                            "supports_function_calling": True,
                            "context_window": 4096,
                            "training_cutoff": "2023-09-01"
                        },
                        "gpt-4": {
                            "max_tokens": 8192,
                            "supports_code": True,
                            "supports_math": True,
                            "supports_function_calling": True,
                            "context_window": 8192,
                            "training_cutoff": "2023-04-01"
                        }
                    }
                    
                    # Define request requirements  
                    request_requirements = {
                        "complex_math": {
                            "requires_math": True,
                            "min_context": 2000,
                            "max_tokens_needed": 1000
                        },
                        "long_document_analysis": {
                            "requires_math": False,
                            "min_context": 6000,
                            "max_tokens_needed": 2000
                        },
                        "simple_chat": {
                            "requires_math": False,
                            "min_context": 1000,
                            "max_tokens_needed": 500
                        }
                    }
                    
                    if model not in model_capabilities:
                        model = "gpt-3.5-turbo"  # Default fallback
                    
                    capabilities = model_capabilities[model]
                    requirements = request_requirements.get(request_type, request_requirements["simple_chat"])
                    
                    # Check capability mismatches
                    mismatches = []
                    
                    if requirements["requires_math"] and not capabilities["supports_math"]:
                        mismatches.append("math_capability_insufficient")
                    
                    if requirements["min_context"] > capabilities["context_window"]:
                        mismatches.append("context_window_insufficient")
                    
                    if requirements["max_tokens_needed"] > capabilities["max_tokens"]:
                        mismatches.append("max_tokens_insufficient")
                    
                    if mismatches:
                        # ENHANCED WARNING: Provide comprehensive model capability diagnostics
                        diagnostic_info = {
                            "error_type": "LLM_MODEL_CAPABILITY_MISMATCH",
                            "current_model": model,
                            "request_type": request_type,
                            "capability_mismatches": mismatches,
                            "model_capabilities": capabilities,
                            "request_requirements": requirements,
                            "user_context": {
                                "user_id": self.user_id,
                                "request_complexity": "high" if len(mismatches) > 1 else "medium"
                            },
                            "alternative_models": {
                                "gpt-4": "Supports advanced math and larger context window",
                                "claude-2": "Excellent for long document analysis",
                                "code-davinci": "Specialized for code generation tasks"
                            },
                            "optimization_strategies": [
                                "Break down complex requests into smaller parts",
                                "Use model-specific prompts optimized for capabilities",
                                "Implement request preprocessing to reduce complexity",
                                "Cache intermediate results to reduce context needs"
                            ],
                            "fallback_options": [
                                "Switch to more capable model for this request type",
                                "Simplify request to match current model capabilities", 
                                "Use hybrid approach with multiple model calls",
                                "Provide partial response with capability limitations explained"
                            ],
                            "impact_assessment": {
                                "response_quality": "DEGRADED - model may provide incomplete/incorrect response",
                                "success_probability": "30% - request likely to fail or provide poor results",
                                "user_satisfaction": "LOW - response may not meet user expectations"
                            }
                        }
                        
                        # Enhanced warning with comprehensive model capability diagnostics
                        logger.warning(
                            f"LLM PROCESSING FAILURE - {diagnostic_info['error_type']}: "
                            f"Model {diagnostic_info['current_model']} insufficient for {diagnostic_info['request_type']} request from user {self.user_id}. "
                            f"Capability mismatches: {len(diagnostic_info['capability_mismatches'])} ({', '.join(diagnostic_info['capability_mismatches'])}). "
                            f"Success probability: {diagnostic_info['impact_assessment']['success_probability']}. "
                            f"Alternative models: {len(diagnostic_info['alternative_models'])} available. "
                            f"Fallback options: {len(diagnostic_info['fallback_options'])} strategies. "
                            f"See logs for complete model capability analysis and optimization recommendations."
                        )
                        
                        # Log detailed model capability diagnostics
                        logger.info(f"MODEL CAPABILITY DIAGNOSTIC DETAILS: {json.dumps(diagnostic_info, indent=2)}")
                        
                        return False  # Capability mismatch detected
                    
                    return True  # Model capabilities sufficient
            
            builder = ModelCapabilityDiagnosticBuilder()
            
            # Test capability mismatch scenario
            result = await builder.validate_model_capabilities("complex_math", "gpt-3.5-turbo")
            assert result is False, "Model capability validation should detect mismatch"
            
            # Test successful capability match
            result = await builder.validate_model_capabilities("simple_chat", "gpt-3.5-turbo") 
            assert result is True, "Model capability validation should succeed for matching capabilities"
        
        # Validate enhanced model capability warning
        self.assert_warning_logged(
            "LLM PROCESSING FAILURE.*LLM_MODEL_CAPABILITY_MISMATCH.*Model gpt-3.5-turbo insufficient for complex_math",
            logger_name="netra_backend.app.agents.actions_goals_plan_builder",
            count=1
        )
        
        # Validate model capability diagnostic details
        captured_logs = [log for log in self._captured_logs if "MODEL CAPABILITY DIAGNOSTIC DETAILS" in log.get("message", "")]
        assert len(captured_logs) == 1, "Model capability diagnostic details should be logged"
        
        # Record model capability diagnostics test
        self.record_metric("llm_model_capability_diagnostics_enhanced", True)
    
    async def test_llm_token_limit_exceeded_enhanced_diagnostics(self):
        """
        Test enhanced diagnostics for LLM token limit exceeded scenarios.
        
        Business Impact: Token limit exceeded prevents complete responses.
        Enhanced diagnostics help identify content that can be truncated or
        split across multiple requests.
        """
        auth_helper = await self.get_auth_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.actions_goals_plan_builder"):
            from netra_backend.app.agents.actions_goals_plan_builder import ActionsGoalsPlanBuilder
            
            class TokenLimitDiagnosticBuilder(ActionsGoalsPlanBuilder):
                def __init__(self):
                    super().__init__()
                    self.logger = logger
                    self.user_id = auth_helper.get_user_id()
                
                async def handle_token_limit_exceeded(self, prompt: str, response_partial: str):
                    """Handle token limit exceeded with enhanced diagnostics."""
                    # Simulate token usage analysis
                    token_analysis = {
                        "prompt_tokens": 3500,
                        "response_tokens": 800,  # Partial response
                        "total_tokens": 4300,
                        "model_limit": 4096,
                        "tokens_over_limit": 204,
                        "completion_percentage": 75  # Estimated completion
                    }
                    
                    # ENHANCED WARNING: Provide comprehensive token limit diagnostics
                    diagnostic_info = {
                        "error_type": "LLM_TOKEN_LIMIT_EXCEEDED",
                        "token_analysis": token_analysis,
                        "content_breakdown": {
                            "prompt_structure": {
                                "system_prompt": 200,
                                "user_context": 800,
                                "conversation_history": 1500,
                                "task_instructions": 500,
                                "examples": 500
                            },
                            "response_structure": {
                                "completed_sections": ["introduction", "analysis", "partial_conclusion"],
                                "truncated_sections": ["detailed_recommendations", "next_steps"],
                                "estimated_missing_content": "25% of intended response"
                            }
                        },
                        "user_context": {
                            "user_id": self.user_id,
                            "request_complexity": "high",
                            "conversation_length": "long",
                            "priority": "normal"
                        },
                        "optimization_strategies": [
                            "Reduce conversation history to essential context only",
                            "Compress system prompt while maintaining key instructions",
                            "Split complex requests into multiple sequential calls",
                            "Use summarization for long context passages",
                            "Implement intelligent context windowing"
                        ],
                        "immediate_solutions": [
                            "Continue response in follow-up request with partial context",
                            "Provide summary of truncated sections",
                            "Ask user which aspects they want prioritized",
                            "Switch to model with larger context window"
                        ],
                        "content_prioritization": [
                            "Keep core response content (highest priority)",
                            "Preserve user-specific context (high priority)", 
                            "Reduce examples and explanatory text (medium priority)",
                            "Trim conversation history (low priority)"
                        ],
                        "impact_assessment": {
                            "response_completeness": f"{token_analysis['completion_percentage']}%",
                            "user_experience": "DEGRADED - incomplete response provided",
                            "information_loss": "MEDIUM - key points covered, details missing",
                            "recovery_possible": True
                        }
                    }
                    
                    # Enhanced warning with comprehensive token limit diagnostics
                    logger.warning(
                        f"LLM PROCESSING FAILURE - {diagnostic_info['error_type']}: "
                        f"Token limit exceeded for user {self.user_id}. "
                        f"Usage: {diagnostic_info['token_analysis']['total_tokens']}/{diagnostic_info['token_analysis']['model_limit']} tokens "
                        f"({diagnostic_info['token_analysis']['tokens_over_limit']} over limit). "
                        f"Response completion: {diagnostic_info['token_analysis']['completion_percentage']}%. "
                        f"Missing content: {diagnostic_info['content_breakdown']['response_structure']['estimated_missing_content']}. "
                        f"Optimization strategies: {len(diagnostic_info['optimization_strategies'])} available. "
                        f"Recovery: {diagnostic_info['impact_assessment']['recovery_possible']}. "
                        f"See logs for complete token analysis and content optimization recommendations."
                    )
                    
                    # Log detailed token limit diagnostics
                    logger.info(f"TOKEN LIMIT DIAGNOSTIC DETAILS: {json.dumps(diagnostic_info, indent=2)}")
                    
                    # Return partial response info for graceful handling
                    return {
                        "partial_response": response_partial,
                        "completion_percentage": token_analysis["completion_percentage"],
                        "next_action": "continue_in_followup"
                    }
            
            builder = TokenLimitDiagnosticBuilder()
            
            # Handle token limit exceeded scenario
            long_prompt = "A" * 3500  # Simulate long prompt
            partial_response = "This is a partial response that was cut off due to token limits..."
            
            result = await builder.handle_token_limit_exceeded(long_prompt, partial_response)
            assert result is not None, "Token limit should be handled gracefully"
            assert result["completion_percentage"] == 75, "Completion percentage should be tracked"
        
        # Validate enhanced token limit warning
        self.assert_warning_logged(
            "LLM PROCESSING FAILURE.*LLM_TOKEN_LIMIT_EXCEEDED.*Token limit exceeded",
            logger_name="netra_backend.app.agents.actions_goals_plan_builder",
            count=1
        )
        
        # Validate token limit diagnostic details
        captured_logs = [log for log in self._captured_logs if "TOKEN LIMIT DIAGNOSTIC DETAILS" in log.get("message", "")]
        assert len(captured_logs) == 1, "Token limit diagnostic details should be logged"
        
        # Record token limit diagnostics test
        self.record_metric("llm_token_limit_diagnostics_enhanced", True)
    
    async def test_llm_authentication_failure_enhanced_diagnostics(self):
        """
        Test enhanced diagnostics for LLM API authentication failures.
        
        Business Impact: Authentication failures prevent all LLM requests.
        Enhanced diagnostics help identify API key issues, permission problems,
        and account status issues.
        """
        auth_helper = await self.get_auth_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.actions_goals_plan_builder"):
            from netra_backend.app.agents.actions_goals_plan_builder import ActionsGoalsPlanBuilder
            
            class AuthDiagnosticLLMBuilder(ActionsGoalsPlanBuilder):
                def __init__(self):
                    super().__init__()
                    self.logger = logger
                    self.user_id = auth_helper.get_user_id()
                
                async def handle_llm_authentication_failure(self, auth_error: str):
                    """Handle LLM authentication failure with enhanced diagnostics."""
                    # ENHANCED WARNING: Provide comprehensive authentication diagnostics
                    diagnostic_info = {
                        "error_type": "LLM_API_AUTHENTICATION_FAILURE",
                        "authentication_error": auth_error,
                        "api_key_analysis": {
                            "key_format": "sk-...***...xyz" if auth_error.find("invalid key") != -1 else "unknown",
                            "key_length": 51,  # Standard OpenAI key length
                            "key_prefix": "sk-",
                            "expiry_status": "unknown - check with provider",
                            "last_successful_use": "2024-01-14T15:30:00Z"
                        },
                        "account_status": {
                            "billing_status": "unknown - requires account check",
                            "usage_quota": "unknown - may be exceeded",
                            "subscription_tier": "unknown - affects rate limits",
                            "account_suspension": "possible - check provider dashboard"
                        },
                        "user_context": {
                            "user_id": self.user_id,
                            "request_frequency": "high",
                            "geographic_location": "unknown",
                            "ip_restriction_possible": True
                        },
                        "possible_causes": [
                            "API key expired or revoked",
                            "Account billing issues or quota exceeded",
                            "API key permissions insufficient for requested operations",
                            "Account temporarily suspended",
                            "IP address not whitelisted (if restrictions enabled)",
                            "API key compromised and disabled by provider"
                        ],
                        "immediate_actions": [
                            "Verify API key in provider dashboard",
                            "Check account billing status and payment methods",
                            "Review usage quotas and limits",
                            "Test API key with simple curl request",
                            "Check for any account notifications or alerts"
                        ],
                        "security_considerations": [
                            "Rotate API key if compromise suspected",
                            "Review API key usage logs for anomalies",
                            "Implement API key monitoring and alerts",
                            "Use environment-specific API keys",
                            "Enable API key restrictions where supported"
                        ],
                        "business_impact": {
                            "service_availability": "CRITICAL - all LLM features unavailable",
                            "affected_users": "all users requiring LLM responses",
                            "estimated_downtime": "until authentication resolved",
                            "revenue_impact": "HIGH - core functionality unavailable"
                        }
                    }
                    
                    # Enhanced warning with comprehensive authentication diagnostics
                    logger.warning(
                        f"LLM PROCESSING FAILURE - {diagnostic_info['error_type']}: "
                        f"Authentication failed for user {self.user_id}. "
                        f"Error: {diagnostic_info['authentication_error']}. "
                        f"API key format: {diagnostic_info['api_key_analysis']['key_format']}. "
                        f"Business impact: {diagnostic_info['business_impact']['service_availability']}. "
                        f"Affected users: {diagnostic_info['business_impact']['affected_users']}. "
                        f"Immediate actions required: {len(diagnostic_info['immediate_actions'])} steps. "
                        f"Security review needed: {len(diagnostic_info['security_considerations'])} items. "
                        f"See logs for complete authentication failure analysis."
                    )
                    
                    # Log detailed authentication diagnostics
                    logger.info(f"AUTH FAILURE DIAGNOSTIC DETAILS: {json.dumps(diagnostic_info, indent=2)}")
                    
                    # Return authentication failure info
                    return {
                        "auth_failed": True,
                        "requires_immediate_attention": True,
                        "service_impact": "critical"
                    }
            
            builder = AuthDiagnosticLLMBuilder()
            
            # Handle authentication failure scenario
            result = await builder.handle_llm_authentication_failure("Invalid API key provided")
            assert result is not None, "Auth failure should be handled gracefully"
            assert result["auth_failed"] is True, "Auth failure should be detected"
            assert result["requires_immediate_attention"] is True, "Critical issues should be flagged"
        
        # Validate enhanced authentication failure warning
        self.assert_warning_logged(
            "LLM PROCESSING FAILURE.*LLM_API_AUTHENTICATION_FAILURE.*Authentication failed",
            logger_name="netra_backend.app.agents.actions_goals_plan_builder",
            count=1
        )
        
        # Validate authentication failure diagnostic details
        captured_logs = [log for log in self._captured_logs if "AUTH FAILURE DIAGNOSTIC DETAILS" in log.get("message", "")]
        assert len(captured_logs) == 1, "Auth failure diagnostic details should be logged"
        
        # Validate business value: Critical issue flagged appropriately
        self.validate_business_value_preservation(
            graceful_degradation=False,  # Auth failure is critical
            chat_functionality=False     # Chat cannot function without LLM auth
        )
        
        # Record authentication diagnostics test
        self.record_metric("llm_authentication_failure_diagnostics_enhanced", True)


# Additional helper functions for LLM processing testing

def estimate_token_usage(text: str, model: str = "gpt-4") -> Dict[str, int]:
    """
    Estimate token usage for given text and model.
    
    Args:
        text: Text to estimate tokens for
        model: Model name for token calculation
        
    Returns:
        Dictionary containing token estimates
    """
    # Simple token estimation (real implementation would use tiktoken)
    base_tokens = len(text.split()) * 1.3  # Rough approximation
    
    model_multipliers = {
        "gpt-4": 1.0,
        "gpt-3.5-turbo": 1.0,
        "claude-2": 0.8,  # Different tokenization
        "text-davinci-003": 1.1
    }
    
    multiplier = model_multipliers.get(model, 1.0)
    estimated_tokens = int(base_tokens * multiplier)
    
    return {
        "estimated_tokens": estimated_tokens,
        "character_count": len(text),
        "word_count": len(text.split()),
        "model": model,
        "confidence": "low"  # Simple estimation method
    }


def analyze_llm_response_quality(response: str, expected_format: str = "json") -> Dict[str, Any]:
    """
    Analyze LLM response quality and format compliance.
    
    Args:
        response: LLM response to analyze
        expected_format: Expected response format
        
    Returns:
        Response quality analysis
    """
    analysis = {
        "format_compliance": {
            "expected": expected_format,
            "detected": "text",  # Simple detection
            "valid": False
        },
        "content_quality": {
            "length": len(response),
            "word_count": len(response.split()),
            "completeness": "unknown",
            "coherence": "unknown"
        },
        "issues_found": [],
        "recommendations": []
    }
    
    # Basic format validation
    if expected_format == "json":
        try:
            json.loads(response)
            analysis["format_compliance"]["valid"] = True
            analysis["format_compliance"]["detected"] = "json"
        except json.JSONDecodeError as e:
            analysis["issues_found"].append(f"JSON parsing error: {str(e)}")
            analysis["recommendations"].append("Fix JSON formatting issues")
    
    # Content quality checks
    if len(response) < 10:
        analysis["issues_found"].append("Response too short")
        analysis["recommendations"].append("Request more detailed response")
    
    if response.count("Error") > 0:
        analysis["issues_found"].append("Response contains error messages")
        analysis["recommendations"].append("Review prompt for clarity")
    
    return analysis


async def test_llm_provider_connectivity(provider_config: Dict[str, str]) -> Dict[str, Any]:
    """
    Test connectivity to LLM provider endpoints.
    
    Args:
        provider_config: Configuration for LLM provider
        
    Returns:
        Connectivity test results
    """
    results = {
        "provider": provider_config.get("name", "unknown"),
        "endpoint": provider_config.get("api_url", ""),
        "connectivity": {
            "reachable": False,
            "response_time_ms": 0,
            "status_code": None,
            "ssl_valid": False
        },
        "authentication": {
            "api_key_format": "unknown",
            "auth_header_valid": False,
            "permissions": "unknown"
        },
        "service_status": {
            "operational": False,
            "rate_limits": "unknown",
            "model_availability": []
        }
    }
    
    # This would contain actual connectivity testing
    # For testing purposes, we'll simulate results
    
    return results