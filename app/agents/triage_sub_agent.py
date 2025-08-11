# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T20:15:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Enhanced TriageSubAgent implementation based on SPEC/TRIAGE_SUB_AGENT_SPEC.xml
# Git: v6 | dirty
# Change: Enhancement | Scope: Component | Risk: Medium
# Session: enhanced-triage-implementation | Seq: 1
# Review: Pending | Score: 90
# ================================
import json
import logging
import time
import hashlib
import re
import asyncio
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ValidationError, field_validator
from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import triage_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.redis_manager import RedisManager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Complexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"

class KeyParameters(BaseModel):
    workload_type: Optional[str] = None
    optimization_focus: Optional[str] = None
    time_sensitivity: Optional[str] = None
    scope: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)

class ExtractedEntities(BaseModel):
    models_mentioned: List[str] = Field(default_factory=list)
    metrics_mentioned: List[str] = Field(default_factory=list)
    time_ranges: List[Dict[str, Any]] = Field(default_factory=list)
    thresholds: List[Dict[str, Any]] = Field(default_factory=list)
    targets: List[Dict[str, Any]] = Field(default_factory=list)

class UserIntent(BaseModel):
    primary_intent: str
    secondary_intents: List[str] = Field(default_factory=list)
    action_required: bool = True

class SuggestedWorkflow(BaseModel):
    next_agent: str
    required_data_sources: List[str] = Field(default_factory=list)
    estimated_duration_ms: int = 1000

class ToolRecommendation(BaseModel):
    tool_name: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ValidationStatus(BaseModel):
    is_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class TriageMetadata(BaseModel):
    triage_duration_ms: int
    llm_tokens_used: int = 0
    cache_hit: bool = False
    fallback_used: bool = False
    retry_count: int = 0

class TriageResult(BaseModel):
    """Enhanced triage result with comprehensive categorization and metadata."""
    category: str
    secondary_categories: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.8)
    priority: Priority = Priority.MEDIUM
    complexity: Complexity = Complexity.MODERATE
    key_parameters: KeyParameters = Field(default_factory=KeyParameters)
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    user_intent: UserIntent = Field(default_factory=lambda: UserIntent(primary_intent="analyze"))
    suggested_workflow: SuggestedWorkflow = Field(default_factory=lambda: SuggestedWorkflow(next_agent="DataSubAgent"))
    tool_recommendations: List[ToolRecommendation] = Field(default_factory=list)
    validation_status: ValidationStatus = Field(default_factory=ValidationStatus)
    metadata: Optional[TriageMetadata] = None
    is_admin_mode: bool = False  # Flag for admin mode routing
    require_approval: bool = False  # Flag for operations requiring user approval
    
    @field_validator('confidence_score')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence score must be between 0 and 1')
        return v

class TriageSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher, redis_manager: Optional[RedisManager] = None):
        super().__init__(llm_manager, name="TriageSubAgent", description="Enhanced triage agent with advanced categorization and caching.")
        self.tool_dispatcher = tool_dispatcher
        self.redis_manager = redis_manager
        self.cache_ttl = 3600  # 1 hour cache TTL
        self.max_retries = 3
        self.fallback_categories = {
            "optimize": "Cost Optimization",
            "performance": "Performance Optimization",
            "analyze": "Workload Analysis",
            "configure": "Configuration & Settings",
            "report": "Monitoring & Reporting",
            "model": "Model Selection",
            "supply": "Supply Catalog Management",
            "quality": "Quality Optimization"
        }
        
    def _generate_request_hash(self, request: str) -> str:
        """Generate a hash for caching similar requests."""
        # Normalize the request for better cache hits
        normalized = request.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    async def _get_cached_result(self, request_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached triage result if available."""
        if not self.redis_manager:
            return None
            
        try:
            cache_key = f"triage:cache:{request_hash}"
            cached = await self.redis_manager.get(cache_key)
            if cached:
                self.logger.info(f"Cache hit for request hash: {request_hash}")
                return json.loads(cached)
        except Exception as e:
            self.logger.warning(f"Failed to retrieve from cache: {e}")
        
        return None
    
    async def _cache_result(self, request_hash: str, result: Dict[str, Any]) -> None:
        """Cache triage result for future use."""
        if not self.redis_manager:
            return
            
        try:
            cache_key = f"triage:cache:{request_hash}"
            await self.redis_manager.set(cache_key, json.dumps(result), ex=self.cache_ttl)
            self.logger.debug(f"Cached result for request hash: {request_hash}")
        except Exception as e:
            self.logger.warning(f"Failed to cache result: {e}")
    
    def _validate_request(self, request: str) -> ValidationStatus:
        """Validate and sanitize the user request."""
        validation = ValidationStatus()
        
        # Check request length
        if len(request) > 10000:
            validation.validation_errors.append("Request exceeds maximum length of 10000 characters")
            validation.is_valid = False
        elif len(request) < 3:
            validation.validation_errors.append("Request is too short to process")
            validation.is_valid = False
        
        # Check for potential injection patterns
        injection_patterns = [
            r'<script',
            r'javascript:',
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'INSERT\s+INTO'
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, request, re.IGNORECASE):
                validation.validation_errors.append(f"Potentially malicious pattern detected")
                validation.is_valid = False
                break
        
        # Add warnings for edge cases
        if len(request) > 5000:
            validation.warnings.append("Request is very long, processing may take longer")
        
        if not re.search(r'[a-zA-Z]', request):
            validation.warnings.append("Request contains no alphabetic characters")
        
        return validation
    
    def _extract_entities_from_request(self, request: str) -> ExtractedEntities:
        """Extract key entities from the user request."""
        entities = ExtractedEntities()
        
        # Extract model names (common AI model patterns)
        model_patterns = [
            r'gpt-?[0-9]+\.?[0-9]*(?:-?turbo)?',
            r'claude-?[0-9]+\.?[0-9]*',
            r'llama-?[0-9]+',
            r'mistral',
            r'gemini',
            r'anthropic',
            r'openai'
        ]
        
        for pattern in model_patterns:
            matches = re.findall(pattern, request.lower())
            entities.models_mentioned.extend(matches)
        
        # Extract metrics
        metric_keywords = ['latency', 'throughput', 'cost', 'accuracy', 'error rate', 
                          'response time', 'tokens', 'requests per second', 'rps']
        for keyword in metric_keywords:
            if keyword in request.lower():
                entities.metrics_mentioned.append(keyword)
        
        # Extract numerical values as potential thresholds/targets
        number_pattern = r'\b\d+(?:\.\d+)?(?:\s*(?:ms|s|%|tokens?|requests?|USD|dollars?))?'
        numbers = re.findall(number_pattern, request)
        for i, num in enumerate(numbers):
            # Check if this number is followed by a unit
            remaining_text = request[request.find(num):]
            if 'ms' in remaining_text[:10] or (num.endswith('ms') or num.endswith('s')):
                entities.thresholds.append({"type": "time", "value": num})
            elif '%' in remaining_text[:5] or num.endswith('%'):
                entities.targets.append({"type": "percentage", "value": num + '%' if not num.endswith('%') else num})
            elif 'token' in remaining_text[:20].lower():
                entities.thresholds.append({"type": "tokens", "value": num})
        
        # Extract time ranges
        time_patterns = [
            r'last\s+(\d+)\s+(hours?|days?|weeks?|months?)',
            r'past\s+(\d+)\s+(hours?|days?|weeks?|months?)',
            r'(\d{4}-\d{2}-\d{2})',
            r'today|yesterday|this\s+week|last\s+week'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, request.lower())
            for match in matches:
                entities.time_ranges.append({"pattern": match})
        
        return entities
    
    def _detect_admin_mode(self, request: str) -> bool:
        """Detect if the request is for admin operations"""
        admin_keywords = [
            "admin", "administrator", "corpus", "synthetic data",
            "generate data", "manage corpus", "create corpus",
            "delete corpus", "export corpus", "import corpus"
        ]
        request_lower = request.lower()
        return any(keyword in request_lower for keyword in admin_keywords)
    
    def _determine_intent(self, request: str) -> UserIntent:
        """Determine user intent from the request."""
        request_lower = request.lower()
        
        intent_keywords = {
            "analyze": ["analyze", "analysis", "examine", "investigate", "understand"],
            "optimize": ["optimize", "improve", "enhance", "reduce", "increase"],
            "configure": ["configure", "set", "update", "change", "modify"],
            "report": ["report", "show", "display", "visualize", "dashboard"],
            "troubleshoot": ["fix", "debug", "troubleshoot", "resolve", "issue"],
            "compare": ["compare", "versus", "vs", "difference", "better"],
            "predict": ["predict", "forecast", "estimate", "project"],
            "recommend": ["recommend", "suggest", "advise", "best"]
        }
        
        primary_intent = None
        secondary_intents = []
        action_required = False
        found_intents = []
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in request_lower for keyword in keywords):
                found_intents.append(intent)
                
                if intent in ["optimize", "configure", "troubleshoot"]:
                    action_required = True
        
        # Set primary and secondary intents
        if found_intents:
            primary_intent = found_intents[0]
            secondary_intents = found_intents[1:]
        else:
            primary_intent = "analyze"  # Default if no intents found
        
        return UserIntent(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            action_required=action_required
        )
    
    def _recommend_tools(self, category: str, entities: ExtractedEntities) -> List[ToolRecommendation]:
        """Recommend tools based on category and extracted entities."""
        recommendations = []
        
        # Map categories to relevant tools
        tool_mapping = {
            "Workload Analysis": ["analyze_workload_events", "get_workload_metrics", "identify_patterns"],
            "Cost Optimization": ["calculate_cost_savings", "simulate_cost_optimization", "analyze_cost_trends"],
            "Performance Optimization": ["identify_latency_bottlenecks", "optimize_throughput", "analyze_performance"],
            "Model Selection": ["compare_models", "get_model_capabilities", "recommend_model"],
            "Supply Catalog Management": ["get_supply_catalog", "update_model_config", "add_new_model"],
            "Monitoring & Reporting": ["generate_report", "create_dashboard", "get_metrics_summary"]
        }
        
        if category in tool_mapping:
            for tool_name in tool_mapping[category]:
                relevance = 0.8  # Base relevance
                
                # Increase relevance based on entities
                if entities.models_mentioned and "model" in tool_name:
                    relevance += 0.1
                if entities.metrics_mentioned and any(metric in tool_name for metric in ["metric", "performance", "cost"]):
                    relevance += 0.1
                
                recommendations.append(ToolRecommendation(
                    tool_name=tool_name,
                    relevance_score=min(1.0, relevance)
                ))
        
        # Sort by relevance
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        return recommendations[:5]  # Return top 5 recommendations
    
    def _fallback_categorization(self, request: str) -> TriageResult:
        """Simple fallback categorization when LLM fails."""
        request_lower = request.lower()
        
        # Find best matching category based on keywords
        category = "General Inquiry"
        for keyword, cat in self.fallback_categories.items():
            if keyword in request_lower:
                category = cat
                break
        
        entities = self._extract_entities_from_request(request)
        intent = self._determine_intent(request)
        
        return TriageResult(
            category=category,
            confidence_score=0.5,  # Lower confidence for fallback
            priority=Priority.MEDIUM,
            complexity=Complexity.MODERATE,
            extracted_entities=entities,
            user_intent=intent,
            tool_recommendations=self._recommend_tools(category, entities),
            metadata=TriageMetadata(
                triage_duration_ms=0,
                fallback_used=True,
                retry_count=0
            )
        )
    
    def _extract_and_validate_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Enhanced JSON extraction with multiple strategies and validation."""
        # Strategy 1: Standard extraction
        result = extract_json_from_response(response)
        if result:
            return result
        
        # Strategy 2: Find JSON-like structure with regex
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                # Try to repair common JSON issues
                repaired = match
                repaired = re.sub(r',\s*}', '}', repaired)  # Remove trailing commas
                repaired = re.sub(r',\s*]', ']', repaired)  # Remove trailing commas in arrays
                repaired = repaired.replace("'", '"')  # Replace single quotes
                
                result = json.loads(repaired)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue
        
        # Strategy 3: Extract key-value pairs manually
        try:
            lines = response.split('\n')
            result = {}
            
            for line in lines:
                if ':' in line:
                    key_match = re.match(r'^\s*"?(\w+)"?\s*:\s*(.+)', line)
                    if key_match:
                        key = key_match.group(1)
                        value = key_match.group(2).strip().strip(',').strip('"')
                        
                        # Try to parse value as JSON
                        try:
                            value = json.loads(value)
                        except (json.JSONDecodeError, ValueError):
                            pass  # Keep as string if not valid JSON
                        
                        result[key] = value
            
            if result:
                return result
        except Exception as e:
            self.logger.debug(f"Manual extraction failed: {e}")
        
        return None

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have a user request to triage."""
        if not state.user_request:
            self.logger.warning(f"No user request provided for triage in run_id: {run_id}")
            return False
        
        # Validate request
        validation = self._validate_request(state.user_request)
        if not validation.is_valid:
            self.logger.error(f"Invalid request for run_id {run_id}: {validation.validation_errors}")
            state.triage_result = {
                "error": "Invalid request",
                "validation_errors": validation.validation_errors
            }
            return False
        
        return True
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the enhanced triage logic."""
        start_time = time.time()
        
        # Update status via WebSocket
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Analyzing user request with enhanced categorization..."
            })
        
        # Check cache first
        request_hash = self._generate_request_hash(state.user_request)
        cached_result = await self._get_cached_result(request_hash)
        
        if cached_result:
            # Use cached result
            triage_result = cached_result
            triage_result["metadata"]["cache_hit"] = True
            triage_result["metadata"]["triage_duration_ms"] = int((time.time() - start_time) * 1000)
        else:
            # Process with LLM
            retry_count = 0
            triage_result = None
            
            while retry_count < self.max_retries and not triage_result:
                try:
                    # Enhanced prompt with more context
                    enhanced_prompt = f"""
{triage_prompt_template.format(user_request=state.user_request)}

IMPORTANT: Return a properly formatted JSON object with all required fields.
Consider the following in your analysis:
1. Extract all mentioned models, metrics, and time ranges
2. Determine the urgency and complexity of the request
3. Suggest specific tools that would be helpful
4. Identify any constraints or requirements mentioned

Example output structure:
{{
    "category": "Cost Optimization",
    "secondary_categories": ["Performance Optimization", "Model Selection"],
    "priority": "high",
    "complexity": "moderate",
    "confidence_score": 0.85,
    "key_parameters": {{
        "workload_type": "inference",
        "optimization_focus": "cost",
        "time_sensitivity": "immediate",
        "scope": "system-wide",
        "constraints": ["maintain p95 latency under 100ms", "budget limit $10000/month"]
    }},
    "extracted_entities": {{
        "models_mentioned": ["gpt-4", "claude-2"],
        "metrics_mentioned": ["latency", "cost", "throughput"],
        "time_ranges": [{{"start": "2024-01-01", "end": "2024-01-31"}}],
        "thresholds": [{{"type": "latency", "value": "100ms"}}],
        "targets": [{{"type": "cost_reduction", "value": "30%"}}]
    }},
    "user_intent": {{
        "primary_intent": "optimize",
        "secondary_intents": ["analyze", "compare"],
        "action_required": true
    }},
    "suggested_workflow": {{
        "next_agent": "DataSubAgent",
        "required_data_sources": ["clickhouse", "supply_catalog"],
        "estimated_duration_ms": 5000
    }},
    "tool_recommendations": [
        {{"tool_name": "calculate_cost_savings", "relevance_score": 0.9}},
        {{"tool_name": "compare_models", "relevance_score": 0.8}}
    ]
}}
"""
                    
                    llm_response_str = await self.llm_manager.ask_llm(
                        enhanced_prompt, 
                        llm_config_name='triage'
                    )
                    
                    # Extract and validate JSON
                    extracted_json = self._extract_and_validate_json(llm_response_str)
                    
                    if extracted_json:
                        # Validate with Pydantic
                        try:
                            validated_result = TriageResult(**extracted_json)
                            triage_result = validated_result.model_dump()
                        except ValidationError as e:
                            self.logger.warning(f"Validation error for run_id {run_id}: {e}")
                            # Use extracted JSON with defaults
                            triage_result = extracted_json
                    
                except Exception as e:
                    self.logger.warning(f"Triage attempt {retry_count + 1} failed for run_id {run_id}: {e}")
                    retry_count += 1
                    
                    if retry_count < self.max_retries:
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            
            # If all retries failed, use fallback
            if not triage_result:
                self.logger.warning(f"Using fallback categorization for run_id: {run_id}")
                fallback = self._fallback_categorization(state.user_request)
                triage_result = fallback.model_dump()
            
            # Add metadata
            if not triage_result.get("metadata"):
                triage_result["metadata"] = {}
            
            triage_result["metadata"].update({
                "triage_duration_ms": int((time.time() - start_time) * 1000),
                "cache_hit": False,
                "retry_count": retry_count,
                "fallback_used": retry_count >= self.max_retries
            })
            
            # Cache the result for future use
            await self._cache_result(request_hash, triage_result)
        
        # Extract entities and intent if not already done
        if not triage_result.get("extracted_entities"):
            entities = self._extract_entities_from_request(state.user_request)
            triage_result["extracted_entities"] = entities.model_dump()
        
        if not triage_result.get("user_intent"):
            intent = self._determine_intent(state.user_request)
            triage_result["user_intent"] = intent.model_dump()
        
        # Detect admin mode
        is_admin = self._detect_admin_mode(state.user_request)
        triage_result["is_admin_mode"] = is_admin
        
        # Adjust category for admin mode
        if is_admin and triage_result.get("category") not in ["Synthetic Data Generation", "Corpus Management"]:
            if "synthetic" in state.user_request.lower() or "generate data" in state.user_request.lower():
                triage_result["category"] = "Synthetic Data Generation"
            elif "corpus" in state.user_request.lower():
                triage_result["category"] = "Corpus Management"
        
        # Add tool recommendations if not present
        if not triage_result.get("tool_recommendations"):
            tools = self._recommend_tools(
                triage_result.get("category", "General Inquiry"),
                ExtractedEntities(**triage_result.get("extracted_entities", {}))
            )
            triage_result["tool_recommendations"] = [t.model_dump() for t in tools]
        
        state.triage_result = triage_result
        
        # Log performance metrics
        self.logger.info(
            f"Triage completed for run_id {run_id}: "
            f"category={triage_result.get('category')}, "
            f"confidence={triage_result.get('confidence_score', 0)}, "
            f"duration={triage_result['metadata']['triage_duration_ms']}ms, "
            f"cache_hit={triage_result['metadata']['cache_hit']}"
        )
        
        # Update with results
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": f"Request categorized as: {triage_result.get('category', 'Unknown')} "
                          f"with confidence {triage_result.get('confidence_score', 0):.2f}",
                "result": triage_result
            })
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution."""
        await super().cleanup(state, run_id)
        
        # Log final metrics if available
        if state.triage_result and isinstance(state.triage_result, dict):
            metadata = state.triage_result.get("metadata", {})
            if metadata:
                # Could send metrics to monitoring system here
                self.logger.debug(f"Triage metrics for run_id {run_id}: {metadata}")