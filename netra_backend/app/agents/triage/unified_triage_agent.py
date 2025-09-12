"""Unified Triage Agent - SSOT Consolidation of 28 Triage Files

This module consolidates all triage functionality into a single, unified implementation
following SSOT principles, factory patterns, and proper user isolation.

Key Features:
- Factory pattern for per-request isolation
- Correct execution order (MUST RUN FIRST)
- WebSocket event integration
- Metadata SSOT methods
- All critical triage logic preserved
"""

import asyncio
import json
import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, ValidationError

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.config import agent_config
from netra_backend.app.core.serialization.unified_json_handler import (
    LLMResponseParser,
    JSONErrorFixer,
    safe_json_loads
)
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.reliability.unified_reliability_manager import (
    get_reliability_manager
)

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

logger = central_logger.get_logger(__name__)


# Import models from separate file to avoid circular imports
from netra_backend.app.agents.triage.models import (
    Priority,
    Complexity,
    ExtractedEntities,
    UserIntent,
    ToolRecommendation,
    TriageResult,
    TriageMetadata,
    KeyParameters,
    SuggestedWorkflow
)


# ============================================================================
# CONFIGURATION (from config.py)
# ============================================================================

class TriageConfig:
    """Centralized configuration for triage operations"""
    
    # Model configuration
    PRIMARY_MODEL = "gemini-2.5-pro"
    FALLBACK_MODEL = "gemini-2.5-flash"
    TEMPERATURE = 0.0  # Deterministic for consistent categorization
    TIMEOUT_SECONDS = 17.0
    
    # Circuit breaker configuration
    CIRCUIT_BREAKER_CONFIG = {
        "failure_threshold": 3,
        "recovery_timeout": 30,
        "expected_exception": Exception
    }
    
    # Validation limits
    MAX_REQUEST_LENGTH = 10000
    MIN_REQUEST_LENGTH = 3
    
    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """Get LLM configuration"""
        return {
            "model": cls.PRIMARY_MODEL,
            "temperature": cls.TEMPERATURE,
            "timeout": cls.TIMEOUT_SECONDS
        }
    
    @classmethod
    def get_fallback_config(cls) -> Dict[str, Any]:
        """Get fallback configuration"""
        return {
            "model": cls.FALLBACK_MODEL,
            "temperature": cls.TEMPERATURE,
            "timeout": 10.0  # Faster timeout for fallback
        }


# ============================================================================
# FACTORY PATTERN FOR USER ISOLATION
# ============================================================================

class UnifiedTriageAgentFactory:
    """Factory for creating isolated triage agents per request
    
    This factory ensures:
    1. Each request gets its own agent instance
    2. No shared state between users
    3. Proper WebSocket routing
    4. Correct execution priority (MUST RUN FIRST)
    """
    
    @staticmethod
    def create_for_context(
        context: 'UserExecutionContext',
        llm_manager: 'LLMManager',
        tool_dispatcher: 'ToolDispatcher',
        websocket_bridge: Optional['AgentWebSocketBridge'] = None
    ) -> 'UnifiedTriageAgent':
        """Create an isolated triage agent for a specific user context
        
        Args:
            context: User execution context for isolation
            llm_manager: LLM manager instance
            tool_dispatcher: Tool dispatcher instance
            websocket_bridge: Optional WebSocket bridge for real-time events
            
        Returns:
            UnifiedTriageAgent instance isolated to this request
        """
        agent = UnifiedTriageAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher,
            context=context,
            execution_priority=0  # CRITICAL: Must run first
        )
        
        # Set WebSocket bridge if available
        if websocket_bridge:
            agent.set_websocket_bridge(websocket_bridge, context.run_id)
            
        logger.info(f"Created UnifiedTriageAgent for user {context.user_id}, "
                   f"request {context.request_id} with priority 0 (FIRST)")
        
        return agent


# ============================================================================
# UNIFIED TRIAGE AGENT - SSOT IMPLEMENTATION
# ============================================================================

class UnifiedTriageAgent(BaseAgent):
    """Unified Triage Agent - Single Source of Truth for all triage operations
    
    This agent consolidates all triage functionality from 28 separate files
    into a single, cohesive implementation that:
    - MUST RUN FIRST in the agent pipeline
    - Uses factory pattern for user isolation
    - Emits all required WebSocket events
    - Uses SSOT metadata methods
    - Preserves all critical triage logic
    """
    
    EXECUTION_ORDER = 0  # CRITICAL: Must run first
    
    def __init__(
        self,
        llm_manager: 'LLMManager',
        tool_dispatcher: 'ToolDispatcher',
        context: Optional['UserExecutionContext'] = None,
        execution_priority: int = 0
    ):
        """Initialize the unified triage agent
        
        Args:
            llm_manager: LLM manager for AI operations
            tool_dispatcher: Tool dispatcher for tool execution
            context: User execution context for isolation
            execution_priority: Execution order (0 = first)
        """
        super().__init__(
            llm_manager=llm_manager,
            name="UnifiedTriageAgent"
        )
        self.tool_dispatcher = tool_dispatcher
        self.context = context
        self.execution_priority = execution_priority
        
        # Initialize cache helper for SSOT key generation
        self._cache_helper = CacheHelpers(None)
        
        # Initialize reliability manager - use private attribute to avoid property setter issue
        self._reliability_manager_instance = get_reliability_manager()
        
        # Initialize processing components
        self._init_processing_components()
    
    @classmethod
    def create_agent_with_context(cls, user_context: 'UserExecutionContext') -> 'UnifiedTriageAgent':
        """Create UnifiedTriageAgent with proper UserExecutionContext pattern.
        
        This method provides the correct constructor signature for the factory pattern,
        avoiding the constructor parameter mismatch with BaseAgent.create_agent_with_context.
        
        Args:
            user_context: User execution context for isolation
            
        Returns:
            UnifiedTriageAgent instance configured for the user context
            
        Note:
            This overrides the BaseAgent.create_agent_with_context method to use
            the correct constructor signature for UnifiedTriageAgent.
        """
        from netra_backend.app.llm.llm_manager import create_llm_manager
        
        # Create LLM manager with proper user isolation
        llm_manager = create_llm_manager(user_context)
        
        # Create agent with correct constructor signature
        agent = cls(
            llm_manager=llm_manager,
            tool_dispatcher=None,  # Will be injected by factory
            context=user_context,
            execution_priority=0  # Triage runs first
        )
        
        # Set user context for WebSocket integration
        if hasattr(agent, 'set_user_context'):
            agent.set_user_context(user_context)
        
        return agent
        
    def _init_processing_components(self) -> None:
        """Initialize internal processing components"""
        # Intent keywords for detection
        self.intent_keywords = {
            "analyze": ["analyze", "analysis", "examine", "investigate", "understand", "assess", "evaluate"],
            "optimize": ["optimize", "improve", "enhance", "reduce", "increase", "maximize", "minimize"],
            "configure": ["configure", "set", "update", "change", "modify", "adjust", "enable", "disable"],
            "monitor": ["monitor", "track", "watch", "observe", "measure", "report"],
            "troubleshoot": ["troubleshoot", "debug", "fix", "resolve", "diagnose", "issue", "problem"],
            "compare": ["compare", "versus", "vs", "difference", "benchmark", "evaluate"],
            "predict": ["predict", "forecast", "estimate", "project", "anticipate"],
            "recommend": ["recommend", "suggest", "advise", "best", "should", "which"],
            "admin": ["admin", "administrator", "corpus", "synthetic data", "generate data"]
        }
        
        # Tool mapping for recommendations
        self.tool_mapping = {
            "Workload Analysis": ["analyze_workload_events", "get_workload_metrics", "identify_patterns"],
            "Cost Optimization": ["calculate_cost_savings", "simulate_cost_optimization", "analyze_cost_trends"],
            "Performance Optimization": ["identify_latency_bottlenecks", "optimize_throughput", "analyze_performance"],
            "Model Selection": ["compare_models", "get_model_capabilities", "recommend_model"],
            "Configuration & Settings": ["update_configuration", "get_current_settings", "validate_configuration"],
            "Monitoring & Reporting": ["generate_report", "create_dashboard", "export_metrics"],
            "Synthetic Data": ["generate_synthetic_data", "create_test_scenarios", "simulate_workload"],
            "Corpus Management": ["manage_corpus", "update_knowledge_base", "index_documents"]
        }
        
        # Fallback categories with comprehensive keyword matching
        self.fallback_categories = {
            "optimize": "Cost Optimization",
            "optimization": "Cost Optimization", 
            "cost": "Cost Optimization",
            "budget": "Cost Optimization",
            "bills": "Cost Optimization",
            "expensive": "Cost Optimization",
            "reduce": "Cost Optimization",
            "save": "Cost Optimization",
            "performance": "Performance Optimization",
            "latency": "Performance Optimization",
            "throughput": "Performance Optimization",
            "speed": "Performance Optimization",
            "scaling": "Performance Optimization",
            "bottleneck": "Performance Optimization",
            "slow": "Performance Optimization",
            "analyze": "Workload Analysis",
            "analysis": "Workload Analysis",
            "configure": "Configuration & Settings",
            "configuration": "Configuration & Settings",
            "setup": "Configuration & Settings",
            "set up": "Configuration & Settings",
            "deployment": "Configuration & Settings",
            "environment": "Configuration & Settings",
            "monitoring": "Monitoring & Reporting",
            "alerting": "Monitoring & Reporting",
            "report": "Monitoring & Reporting", 
            "model": "Model Selection",
            "supply": "Supply Catalog Management",
            "quality": "Quality Optimization"
        }
        
        # Model patterns for entity extraction
        self.model_patterns = [
            r'gpt-?[0-9]+\.?[0-9]*(?:-?turbo)?',
            r'claude-?[0-9]+(?:-[a-z]+)?',
            r'llama-?[0-9]+(?:b)?(?:-[a-z]+)?',
            r'mistral-?[0-9]+(?:x)?(?:[0-9]+b)?',
            r'gemini(?:-pro)?(?:-[0-9]+)?',
            r'palm-?[0-9]+',
            r'cohere-?[a-z]+',
            r'anthropic-?[a-z]+'
        ]
        
        # Metric keywords
        self.metric_keywords = ['latency', 'throughput', 'cost', 'accuracy', 'error', 
                                'response time', 'tokens', 'rps', 'memory', 'cpu', 
                                'gpu', 'bandwidth', 'requests', 'failures', 'success rate']
        
        # Validation patterns for security
        self.injection_patterns = [
            r'<script', r'javascript:', r'DROP\s+TABLE', r'DELETE\s+FROM',
            r'rm\s+-rf\s+/', r'cat\s+/etc/passwd', r'eval\s*\(',
            r'exec\s*\(', r'system\s*\(', r'__import__', r'os\.system'
        ]
    
    # ========================================================================
    # MAIN EXECUTION METHODS
    # ========================================================================
    
    async def execute(self, state: Any = None, context: Optional['UserExecutionContext'] = None, 
                     message: str = None, **kwargs) -> Dict[str, Any]:
        """Execute triage analysis - MUST RUN FIRST in pipeline
        
        GOLDEN PATH COMPATIBILITY: Supports both modern and legacy call patterns:
        - execute(state, context) - Modern pattern  
        - execute(message="...", context=...) - Legacy Golden Path pattern
        
        Args:
            state: Current execution state (modern pattern) 
            context: User execution context for isolation
            message: User message for legacy compatibility
            **kwargs: Additional legacy parameters
            
        Returns:
            Triage result with category, priority, and next steps
        """
        # GOLDEN PATH COMPATIBILITY: Handle legacy interface patterns
        if state is None and message is not None:
            # Legacy call pattern: execute(message="...", context=...)
            logger.debug(f"TriageAgent: Converting legacy execute(message) call to modern pattern")
            state = message  # Use message as state for triage analysis
        
        if message is not None and context is not None:
            # Inject message into context for legacy compatibility
            if hasattr(context, 'agent_context') and context.agent_context is not None:
                context.agent_context["user_request"] = message
                context.agent_context["message"] = message
            # Enable test mode for compatibility
            if hasattr(self, 'enable_websocket_test_mode'):
                self.enable_websocket_test_mode()
        # Use provided context or instance context
        exec_context = context or self.context
        if not exec_context:
            logger.error("No execution context available for triage")
            return self._create_error_result("No execution context")
        
        # Emit start event
        await self.emit_agent_started("Starting user request triage analysis...")
        
        try:
            # Extract request from state
            request = self._extract_request(state)
            if not request:
                return self._create_error_result("No request found in state")
            
            # Validate request
            validation_result = self._validate_request(request)
            if not validation_result["valid"]:
                await self.emit_error(
                    f"Invalid request: {validation_result['reason']}",
                    "validation_error",
                    validation_result
                )
                fallback_result = self._create_fallback_result(request, validation_result["reason"])
                return self._triage_result_to_dict(fallback_result)
            
            # Generate cache key for similar requests
            cache_key = self._generate_request_hash(request, exec_context)
            
            # Process with LLM
            await self.emit_thinking("Analyzing request intent and requirements...")
            triage_result = await self._process_with_llm(request, exec_context)
            
            # Fallback if LLM fails
            if not triage_result or triage_result.category == "unknown":
                logger.warning("LLM processing failed, using fallback")
                triage_result = self._create_fallback_result(request)
            
            # Store result in context metadata using SSOT method
            # FIX: Replace direct assignment with SSOT method
            self.store_metadata_result(exec_context, 'triage_result', triage_result.__dict__)
            self.store_metadata_result(exec_context, 'triage_category', triage_result.category)
            self.store_metadata_result(exec_context, 'data_sufficiency', triage_result.data_sufficiency)
            self.store_metadata_result(exec_context, 'triage_priority', triage_result.priority.value)
            
            # Determine next agents based on data sufficiency
            next_agents = self._determine_next_agents(triage_result)
            self.store_metadata_result(exec_context, 'next_agents', next_agents)
            
            # Emit completion event
            await self.emit_agent_completed({
                "triage_category": triage_result.category,
                "confidence_score": triage_result.confidence_score,
                "intent": triage_result.user_intent.primary_intent,
                "priority": triage_result.priority.value,
                "data_sufficiency": triage_result.data_sufficiency,
                "next_agents": next_agents
            })
            
            # Return result
            return self._triage_result_to_dict(triage_result, next_agents)
            
        except Exception as e:
            logger.error(f"Triage execution failed: {e}", exc_info=True)
            await self.emit_error(
                f"Triage analysis failed: {str(e)}",
                "execution_error",
                {"exception": str(e)}
            )
            return self._create_error_result(str(e))
    
    # ========================================================================
    # LLM PROCESSING METHODS
    # ========================================================================
    
    async def _process_with_llm(
        self, 
        request: str, 
        context: 'UserExecutionContext'
    ) -> TriageResult:
        """Process request with LLM for intelligent triage
        
        Args:
            request: User request text
            context: Execution context
            
        Returns:
            TriageResult with LLM analysis
        """
        # Build prompt
        prompt = self._build_triage_prompt(request)
        
        # Try structured output first
        try:
            config = TriageConfig.get_llm_config()
            response = await self.llm_manager.generate_structured_response(
                prompt=prompt,
                response_model=TriageResult,
                model=config["model"],
                temperature=config["temperature"],
                timeout=config["timeout"]
            )
            
            if response:
                # Enrich with additional analysis
                response = self._enrich_result(response, request)
                return response
                
        except Exception as e:
            logger.warning(f"Structured output failed: {e}, trying regular LLM")
        
        # Fallback to regular LLM call
        try:
            config = TriageConfig.get_fallback_config()
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                model=config["model"],
                temperature=config["temperature"],
                timeout=config["timeout"]
            )
            
            # Parse JSON from response
            result_dict = self._extract_json_from_response(response)
            if result_dict:
                return self._dict_to_triage_result(result_dict, request)
                
        except Exception as e:
            logger.error(f"LLM fallback failed: {e}")
        
        # Final fallback
        return self._create_fallback_result(request)
    
    def _build_triage_prompt(self, request: str) -> str:
        """Build comprehensive triage analysis prompt
        
        Args:
            request: User request text
            
        Returns:
            Formatted prompt for LLM
        """
        return f"""Analyze this user request and provide a comprehensive triage assessment.

User Request: {request}

Provide a detailed JSON response with the following structure:
{{
    "category": "One of: Workload Analysis, Cost Optimization, Performance Optimization, Model Selection, Configuration & Settings, Monitoring & Reporting, Synthetic Data, Corpus Management, General Request",
    "sub_category": "More specific categorization if applicable",
    "priority": "critical, high, medium, or low",
    "complexity": "high, medium, or low",
    "confidence_score": 0.0-1.0,
    "data_sufficiency": "sufficient, partial, or insufficient",
    "extracted_entities": {{
        "models": ["list of AI models mentioned"],
        "metrics": ["list of metrics mentioned"],
        "time_ranges": ["time periods mentioned"],
        "thresholds": [numerical thresholds],
        "targets": [numerical targets],
        "providers": ["cloud providers mentioned"],
        "regions": ["geographic regions"],
        "services": ["services or components mentioned"]
    }},
    "user_intent": {{
        "primary_intent": "main action user wants",
        "secondary_intents": ["other detected intents"],
        "action_required": true/false,
        "confidence": 0.0-1.0
    }},
    "tool_recommendation": {{
        "primary_tools": ["most relevant tools"],
        "secondary_tools": ["additional useful tools"],
        "tool_scores": {{"tool_name": score}}
    }},
    "next_steps": ["recommended actions in order"],
    "reasoning": "Brief explanation of categorization"
}}

Focus on:
1. Accurately categorizing the request type
2. Assessing data availability for the request
3. Identifying specific entities and values
4. Recommending appropriate tools
5. Determining priority based on business impact"""
    
    # ========================================================================
    # ENTITY EXTRACTION AND INTENT DETECTION
    # ========================================================================
    
    def _extract_entities(self, text: str) -> ExtractedEntities:
        """Extract entities from text using patterns
        
        Args:
            text: Text to analyze
            
        Returns:
            ExtractedEntities with found items
        """
        entities = ExtractedEntities()
        text_lower = text.lower()
        
        # Extract models
        for pattern in self.model_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.models.extend(matches)
        
        # Extract metrics
        for metric in self.metric_keywords:
            if metric in text_lower:
                entities.metrics.append(metric)
        
        # Extract time ranges
        time_patterns = [
            r'last\s+(\d+)\s+(hours?|days?|weeks?|months?)',
            r'(\d{4}-\d{2}-\d{2})',
            r'(today|yesterday|this week|last week|this month|last month)'
        ]
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    entities.time_ranges.append(' '.join(match))
                else:
                    entities.time_ranges.append(match)
        
        # Extract numerical values
        number_pattern = r'\b(\d+(?:\.\d+)?)\b'
        numbers = re.findall(number_pattern, text)
        for num_str in numbers:
            try:
                value = float(num_str)
                # Classify as threshold or target based on context
                if any(word in text_lower for word in ['threshold', 'limit', 'maximum', 'minimum']):
                    entities.thresholds.append(value)
                elif any(word in text_lower for word in ['target', 'goal', 'objective', 'achieve']):
                    entities.targets.append(value)
                else:
                    entities.raw_values[num_str] = value
            except ValueError:
                pass
        
        # Extract providers
        providers = ['aws', 'azure', 'gcp', 'google cloud', 'openai', 'anthropic', 'cohere']
        for provider in providers:
            if provider in text_lower:
                entities.providers.append(provider)
        
        return entities
    
    def _detect_intent(self, text: str) -> UserIntent:
        """Detect user intent from text
        
        Args:
            text: Text to analyze
            
        Returns:
            UserIntent with detected intents
        """
        intent = UserIntent()
        text_lower = text.lower()
        
        # Score each intent category
        intent_scores = {}
        for intent_name, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                intent_scores[intent_name] = score
        
        # Determine primary and secondary intents
        if intent_scores:
            sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
            intent.primary_intent = sorted_intents[0][0]
            intent.confidence = min(sorted_intents[0][1] / 3.0, 1.0)  # Normalize confidence
            
            # Secondary intents
            if len(sorted_intents) > 1:
                intent.secondary_intents = [name for name, _ in sorted_intents[1:3]]
            
            # Determine if action is required - expanded keyword list
            action_keywords = [
                'please', 'need', 'want', 'require', 'must', 'should', 'help', 'how to',
                'can you', 'could you', 'would you', 'implement', 'configure', 'setup',
                'fix', 'resolve', 'solve', 'deploy', 'install', 'create', 'build',
                'optimize', 'improve', 'reduce', 'increase', 'then', 'and'
            ]
            intent.action_required = any(keyword in text_lower for keyword in action_keywords)
        
        return intent
    
    def _recommend_tools(self, category: str, entities: ExtractedEntities) -> ToolRecommendation:
        """Recommend tools based on category and entities
        
        Args:
            category: Request category
            entities: Extracted entities
            
        Returns:
            ToolRecommendation with scored tools
        """
        recommendation = ToolRecommendation()
        
        # Get base tools for category
        if category in self.tool_mapping:
            recommendation.primary_tools = self.tool_mapping[category][:3]
            recommendation.secondary_tools = self.tool_mapping[category][3:6]
            
            # Score tools based on relevance
            for tool in recommendation.primary_tools:
                score = 0.8  # Base score for primary tools
                
                # Bonus for entity matches
                if entities.models and 'model' in tool:
                    score += 0.1
                if entities.metrics and 'metric' in tool:
                    score += 0.1
                
                recommendation.tool_scores[tool] = min(score, 1.0)
            
            for tool in recommendation.secondary_tools:
                recommendation.tool_scores[tool] = 0.5  # Base score for secondary tools
        
        return recommendation
    
    # ========================================================================
    # FALLBACK AND ERROR HANDLING
    # ========================================================================
    
    def _create_fallback_result(self, request: str, reason: str = None) -> TriageResult:
        """Create fallback triage result when LLM fails
        
        Args:
            request: Original request
            reason: Reason for fallback
            
        Returns:
            TriageResult with basic classification
        """
        # Basic keyword-based categorization with scoring
        category = "General Request"
        request_lower = request.lower()
        
        # Score all matching keywords, accumulating scores for same categories
        keyword_scores = {}
        for keyword, cat in self.fallback_categories.items():
            if keyword in request_lower:
                # Count occurrences and consider keyword length for specificity
                count = request_lower.count(keyword)
                specificity = len(keyword)
                score = count + specificity * 0.1
                if cat not in keyword_scores:
                    keyword_scores[cat] = 0
                keyword_scores[cat] += score
        
        # Pick the highest scoring category with tie-breaking preference
        if keyword_scores:
            # Define category priorities for tie-breaking (higher = more preferred)
            category_priorities = {
                "Cost Optimization": 10,
                "Performance Optimization": 9, 
                "Workload Analysis": 8,
                "Configuration & Settings": 7,
                "Monitoring & Reporting": 6,
                "Model Selection": 5,
                "Quality Optimization": 4,
                "Supply Catalog Management": 3
            }
            
            # Sort by score (descending), then by priority (descending)
            sorted_categories = sorted(
                keyword_scores.items(), 
                key=lambda x: (x[1], category_priorities.get(x[0], 0)), 
                reverse=True
            )
            category = sorted_categories[0][0]
        
        # Extract entities manually
        entities = self._extract_entities(request)
        
        # Detect intent manually
        intent = self._detect_intent(request)
        
        # Recommend tools
        tools = self._recommend_tools(category, entities)
        
        # Determine priority based on keywords
        priority = Priority.MEDIUM
        if any(word in request_lower for word in ['urgent', 'critical', 'asap', 'immediately']):
            priority = Priority.HIGH
        elif any(word in request_lower for word in ['when you can', 'low priority', 'eventually']):
            priority = Priority.LOW
        
        # Create result
        result = TriageResult(
            category=category,
            priority=priority,
            complexity=Complexity.MEDIUM,
            confidence_score=0.3,  # Low confidence for fallback
            data_sufficiency="insufficient",
            extracted_entities=entities,
            user_intent=intent,
            tool_recommendation=tools,
            next_steps=["Gather more information", "Analyze request details", "Execute relevant tools"],
            metadata={
                "fallback": True,
                "fallback_reason": reason or "LLM processing failed",
                "processing_time": time.time()
            },
            reasoning=f"Fallback classification based on keyword matching. Reason: {reason or 'LLM unavailable'}"
        )
        
        return result
    
    def _triage_result_to_dict(
        self, 
        triage_result: TriageResult, 
        next_agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Convert TriageResult to dict format for consistent return type
        
        Args:
            triage_result: TriageResult object to convert
            next_agents: Optional list of next agents to include
            
        Returns:
            Dict representation of triage result
        """
        if next_agents is None:
            next_agents = self._determine_next_agents(triage_result)
            
        return {
            "success": True,
            "category": triage_result.category,
            "sub_category": triage_result.sub_category,
            "priority": triage_result.priority.value,
            "complexity": triage_result.complexity.value,
            "confidence_score": triage_result.confidence_score,
            "data_sufficiency": triage_result.data_sufficiency,
            "intent": triage_result.user_intent.__dict__,
            "entities": triage_result.extracted_entities.__dict__,
            "tools": triage_result.tool_recommendation.__dict__,
            "next_steps": triage_result.next_steps,
            "next_agents": next_agents,
            "metadata": triage_result.metadata
        }
    
    def _create_error_result(self, error: str) -> Dict[str, Any]:
        """Create error result for failed triage
        
        Args:
            error: Error message
            
        Returns:
            Error result dict
        """
        return {
            "success": False,
            "error": error,
            "category": "Error",
            "priority": "high",
            "data_sufficiency": "insufficient",
            "next_agents": [],
            "metadata": {
                "error_time": time.time(),
                "error_type": "triage_failure"
            }
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _extract_request(self, state: Any) -> Optional[str]:
        """Extract request from state object
        
        Args:
            state: Execution state
            
        Returns:
            Request string or None
        """
        # Try original_request first (highest priority) - but only if it has a value
        if hasattr(state, 'original_request') and state.original_request:
            return state.original_request
        # Then try request field
        elif hasattr(state, 'request') and state.request:
            return state.request
        # Then try user_request field
        elif hasattr(state, 'user_request') and state.user_request:
            return state.user_request
        # Handle dict state
        elif isinstance(state, dict):
            return (state.get('original_request') or 
                   state.get('request') or 
                   state.get('user_request'))
        return None
    
    def _validate_request(self, request: str) -> Dict[str, Any]:
        """Validate request for security and format
        
        Args:
            request: Request to validate
            
        Returns:
            Validation result with valid flag and reason
        """
        # Check length
        if len(request) < TriageConfig.MIN_REQUEST_LENGTH:
            return {"valid": False, "reason": "Request too short"}
        if len(request) > TriageConfig.MAX_REQUEST_LENGTH:
            return {"valid": False, "reason": "Request too long"}
        
        # Check for injection patterns
        for pattern in self.injection_patterns:
            if re.search(pattern, request, re.IGNORECASE):
                return {"valid": False, "reason": "Potentially malicious content detected"}
        
        return {"valid": True, "reason": None}
    
    def _generate_request_hash(self, request: str, context: 'UserExecutionContext') -> str:
        """Generate hash for request caching (SSOT)
        
        Args:
            request: Request text
            context: Execution context
            
        Returns:
            Hash string for caching
        """
        # Use canonical SSOT method from CacheHelpers
        key_data = {
            "request": request.lower().strip(),
            "user_id": context.user_id,
            "thread_id": context.thread_id
        }
        return self._cache_helper.hash_key_data(key_data)
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response text
        
        Args:
            response: LLM response text
            
        Returns:
            Parsed JSON dict or None
        """
        # Try direct parsing
        try:
            return json.loads(response)
        except:
            pass
        
        # Try to find JSON in text
        json_pattern = r'\{[^{}]*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
        
        # Try with JSON fixer
        try:
            fixer = JSONErrorFixer()
            fixed = fixer.fix_json(response)
            return json.loads(fixed)
        except:
            pass
        
        return None
    
    def _dict_to_triage_result(self, data: Dict[str, Any], request: str) -> TriageResult:
        """Convert dictionary to TriageResult
        
        Args:
            data: Dictionary with triage data
            request: Original request for enrichment
            
        Returns:
            TriageResult object
        """
        # Create base result
        result = TriageResult()
        
        # Map fields
        result.category = data.get('category', 'General Request')
        result.sub_category = data.get('sub_category')
        result.priority = Priority(data.get('priority', 'medium'))
        result.complexity = Complexity(data.get('complexity', 'medium'))
        result.confidence_score = float(data.get('confidence_score', 0.5))
        result.data_sufficiency = data.get('data_sufficiency', 'unknown')
        result.next_steps = data.get('next_steps', [])
        result.reasoning = data.get('reasoning')
        result.metadata = data.get('metadata', {})
        
        # Map entities
        if 'extracted_entities' in data:
            entities_data = data['extracted_entities']
            result.extracted_entities = ExtractedEntities(**entities_data)
        
        # Map intent
        if 'user_intent' in data:
            intent_data = data['user_intent']
            result.user_intent = UserIntent(**intent_data)
        
        # Map tools
        if 'tool_recommendation' in data:
            tools_data = data['tool_recommendation']
            result.tool_recommendation = ToolRecommendation(**tools_data)
        
        # Enrich if needed
        return self._enrich_result(result, request)
    
    def _enrich_result(self, result: TriageResult, request: str) -> TriageResult:
        """Enrich triage result with additional analysis
        
        Args:
            result: Base triage result
            request: Original request
            
        Returns:
            Enriched TriageResult
        """
        # Add missing entities
        if not result.extracted_entities.models:
            result.extracted_entities = self._extract_entities(request)
        
        # Add missing intent
        if result.user_intent.primary_intent == "unknown":
            result.user_intent = self._detect_intent(request)
        
        # Add missing tools
        if not result.tool_recommendation.primary_tools:
            result.tool_recommendation = self._recommend_tools(
                result.category, 
                result.extracted_entities
            )
        
        # Check for admin mode
        if 'admin' in request.lower() or 'corpus' in request.lower():
            if result.category == "General Request":
                result.category = "Corpus Management"
            result.metadata["admin_mode"] = True
        
        return result
    
    def _determine_next_agents(self, triage_result: TriageResult) -> List[str]:
        """Determine which agents should run next based on triage
        
        UVS ENHANCED: Provides intelligent workflow recommendations based on:
        - Data availability
        - User intent
        - Request complexity
        - Optimization opportunities
        
        Args:
            triage_result: Triage analysis result
            
        Returns:
            List of agent names to execute
        """
        next_agents = []
        
        # Analyze user intent for workflow optimization
        user_intent = triage_result.user_intent
        primary_intent = user_intent.primary_intent.lower() if user_intent else ""
        
        # Check data sufficiency first
        if triage_result.data_sufficiency == "insufficient":
            # No data - guidance flow only
            next_agents = ["data_helper"]
            
        elif triage_result.data_sufficiency == "partial":
            # Some data - start with helper, then selective agents
            next_agents = ["data_helper"]
            
            # Add data agent if analysis is needed
            if self._intent_needs_analysis(primary_intent):
                next_agents.append("data")
            
            # Add optimization if relevant
            if self._intent_needs_optimization(primary_intent):
                next_agents.append("optimization")
                
            # Add actions if needed
            if user_intent.action_required or self._intent_needs_actions(primary_intent):
                next_agents.append("actions")
                
        else:  # sufficient data or unknown
            # Selective pipeline based on intent
            
            # Data analysis
            if self._intent_needs_analysis(primary_intent) or triage_result.category in [
                "cost_analysis", "usage_analysis", "performance_analysis"
            ]:
                next_agents.append("data")
            
            # Optimization
            if self._intent_needs_optimization(primary_intent) or triage_result.category in [
                "optimization", "cost_optimization", "performance_optimization"
            ]:
                if "data" not in next_agents:
                    next_agents.append("data")  # Need data for optimization
                next_agents.append("optimization")
            
            # Action planning
            if user_intent.action_required or self._intent_needs_actions(primary_intent) or triage_result.category in [
                "implementation", "migration", "setup"
            ]:
                next_agents.append("actions")
            
            # If no specific agents selected, use data helper for guidance
            if not next_agents:
                next_agents = ["data_helper"]
        
        # Reporting ALWAYS runs last in supervisor (don't include here)
        # The supervisor will add it automatically
        
        logger.info(f"Triage recommends workflow: {'  ->  '.join(next_agents + ['reporting'])}")
        logger.info(f"Reasoning: data={triage_result.data_sufficiency}, "
                   f"category={triage_result.category}, "
                   f"action_required={user_intent.action_required if user_intent else False}")
        
        return next_agents
    
    def _intent_needs_analysis(self, intent: str) -> bool:
        """Check if intent requires data analysis"""
        analysis_keywords = [
            "analyze", "analysis", "review", "examine", "investigate",
            "trend", "pattern", "usage", "cost", "performance",
            "metric", "statistic", "report", "insight", "understand"
        ]
        return any(keyword in intent.lower() for keyword in analysis_keywords)
    
    def _intent_needs_optimization(self, intent: str) -> bool:
        """Check if intent requires optimization"""
        optimization_keywords = [
            "optimize", "improve", "reduce", "save", "efficient",
            "better", "enhance", "minimize", "maximize", "tune",
            "streamline", "accelerate", "boost", "upgrade"
        ]
        return any(keyword in intent.lower() for keyword in optimization_keywords)
    
    def _intent_needs_actions(self, intent: str) -> bool:
        """Check if intent requires action planning"""
        action_keywords = [
            "implement", "deploy", "setup", "configure", "migrate",
            "plan", "roadmap", "steps", "guide", "how to",
            "build", "create", "establish", "install", "integrate"
        ]
        return any(keyword in intent.lower() for keyword in action_keywords)
    
    # ========================================================================
    # REQUIRED BASEAGENT METHODS
    # ========================================================================
    
    async def process(self, request: str) -> Dict[str, Any]:
        """Process a raw request (BaseAgent interface)
        
        Args:
            request: Request text
            
        Returns:
            Processing result
        """
        # Create minimal state for execution
        from dataclasses import dataclass
        
        @dataclass
        class MinimalState:
            original_request: str
        
        state = MinimalState(original_request=request)
        return await self.execute(state, self.context)
    
    def reset_state(self) -> None:
        """Reset agent state for new request (BaseAgent interface)"""
        # Clear any cached data
        self.context = None
        logger.debug("UnifiedTriageAgent state reset")