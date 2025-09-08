# Token Optimization Implementation Code Examples
## Concrete Implementation Patterns for Netra

---

## 1. Enhanced UserExecutionContext with Token Tracking

**File:** `/netra_backend/app/core/execution_context_enhanced.py`

```python
"""Enhanced Execution Context with Token Optimization"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib
from enum import Enum

class OptimizationLevel(Enum):
    """Token optimization levels"""
    NONE = "none"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"

@dataclass
class TokenUsageRecord:
    """Record of a single token usage event"""
    agent: str
    tool: Optional[str]
    timestamp: datetime
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    model: str
    optimization_applied: Optional[str] = None
    cache_hit: bool = False

@dataclass
class TokenMetrics:
    """Comprehensive token tracking for a user session"""
    # Cumulative metrics
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    
    # Budget management
    token_budget: Optional[int] = None
    tokens_remaining: Optional[int] = None
    budget_alerts_triggered: List[str] = field(default_factory=list)
    
    # Per-component breakdown
    by_agent: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_tool: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Usage history
    usage_history: List[TokenUsageRecord] = field(default_factory=list)
    
    # Optimization metrics
    tokens_saved: int = 0
    cost_saved_usd: float = 0.0
    cache_hits: int = 0
    compression_ratio: float = 1.0
    
    def add_usage(self, record: TokenUsageRecord):
        """Add a usage record and update metrics"""
        # Update totals
        self.total_prompt_tokens += record.prompt_tokens
        self.total_completion_tokens += record.completion_tokens
        self.total_tokens += record.total_tokens
        self.total_cost_usd += record.cost_usd
        
        # Update remaining budget
        if self.token_budget:
            self.tokens_remaining = self.token_budget - self.total_tokens
            
            # Check budget alerts
            if self.tokens_remaining < self.token_budget * 0.1:
                self.budget_alerts_triggered.append(f"90% budget used at {record.timestamp}")
        
        # Update breakdowns
        if record.agent:
            if record.agent not in self.by_agent:
                self.by_agent[record.agent] = {
                    'tokens': 0, 'cost': 0.0, 'requests': 0
                }
            self.by_agent[record.agent]['tokens'] += record.total_tokens
            self.by_agent[record.agent]['cost'] += record.cost_usd
            self.by_agent[record.agent]['requests'] += 1
        
        if record.tool:
            if record.tool not in self.by_tool:
                self.by_tool[record.tool] = {
                    'tokens': 0, 'cost': 0.0, 'requests': 0
                }
            self.by_tool[record.tool]['tokens'] += record.total_tokens
            self.by_tool[record.tool]['cost'] += record.cost_usd
            self.by_tool[record.tool]['requests'] += 1
        
        # Track cache hits
        if record.cache_hit:
            self.cache_hits += 1
            self.tokens_saved += record.total_tokens
            self.cost_saved_usd += record.cost_usd
        
        # Add to history
        self.usage_history.append(record)

@dataclass
class UserExecutionContext:
    """Enhanced execution context with token optimization"""
    # Existing fields
    user_id: str
    run_id: str
    organization_id: Optional[str] = None
    trace_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Token optimization fields
    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)
    optimization_level: OptimizationLevel = OptimizationLevel.BALANCED
    token_budget_total: Optional[int] = None
    token_budgets_by_agent: Dict[str, int] = field(default_factory=dict)
    
    # Optimization settings
    enable_caching: bool = True
    enable_compression: bool = True
    enable_model_routing: bool = True
    preferred_models: List[str] = field(default_factory=lambda: ["gpt-3.5-turbo", "gpt-4"])
    
    # Cache management
    cache_keys: List[str] = field(default_factory=list)
    
    def get_cache_key(self, prompt: str, agent: str) -> str:
        """Generate cache key for prompt"""
        content = f"{self.user_id}:{agent}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def can_afford_tokens(self, estimated_tokens: int) -> bool:
        """Check if request fits within budget"""
        if not self.token_budget_total:
            return True  # No budget set
        
        remaining = self.token_metrics.tokens_remaining
        if remaining is None:
            remaining = self.token_budget_total - self.token_metrics.total_tokens
            
        return remaining >= estimated_tokens
    
    def get_optimization_config(self) -> Dict:
        """Get current optimization configuration"""
        return {
            'level': self.optimization_level.value,
            'enable_caching': self.enable_caching,
            'enable_compression': self.enable_compression,
            'enable_model_routing': self.enable_model_routing,
            'compression_target': {
                OptimizationLevel.NONE: 1.0,
                OptimizationLevel.BALANCED: 0.7,
                OptimizationLevel.AGGRESSIVE: 0.5,
                OptimizationLevel.MAXIMUM: 0.3
            }[self.optimization_level]
        }
```

---

## 2. Token Tracker Implementation

**File:** `/netra_backend/app/optimization/token_tracker.py`

```python
"""Token tracking and optimization system"""

import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime
import tiktoken

from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.core.execution_context_enhanced import (
    TokenUsageRecord, UserExecutionContext
)

class TokenTracker:
    """Track and optimize token usage per user context"""
    
    # Model pricing (per 1K tokens)
    MODEL_PRICING = {
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
        'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
        'claude-3-opus': {'input': 0.015, 'output': 0.075},
        'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
    }
    
    def __init__(
        self,
        context: UserExecutionContext,
        websocket_manager: Optional[Any] = None
    ):
        self.context = context
        self.websocket_manager = websocket_manager
        self.encoding_cache: Dict[str, Any] = {}
        
        # Initialize token budget
        if context.token_budget_total:
            context.token_metrics.token_budget = context.token_budget_total
            context.token_metrics.tokens_remaining = context.token_budget_total
    
    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Count tokens in text for specific model"""
        try:
            # Cache encodings for performance
            if model not in self.encoding_cache:
                if 'gpt' in model:
                    self.encoding_cache[model] = tiktoken.encoding_for_model(model)
                else:
                    # Fallback for non-OpenAI models
                    self.encoding_cache[model] = tiktoken.encoding_for_model("gpt-4")
            
            encoding = self.encoding_cache[model]
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}, using estimate")
            # Rough estimate: 1 token per 4 characters
            return len(text) // 4
    
    def calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str
    ) -> float:
        """Calculate cost in USD"""
        pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING['gpt-4'])
        
        prompt_cost = (prompt_tokens / 1000) * pricing['input']
        completion_cost = (completion_tokens / 1000) * pricing['output']
        
        return prompt_cost + completion_cost
    
    async def track_usage(
        self,
        agent: str,
        prompt: str,
        completion: str,
        model: str = "gpt-4",
        tool: Optional[str] = None,
        optimization_applied: Optional[str] = None,
        cache_hit: bool = False
    ) -> TokenUsageRecord:
        """Track token usage for a request"""
        
        # Count tokens
        prompt_tokens = self.count_tokens(prompt, model)
        completion_tokens = self.count_tokens(completion, model)
        total_tokens = prompt_tokens + completion_tokens
        
        # Calculate cost
        cost_usd = self.calculate_cost(prompt_tokens, completion_tokens, model)
        
        # Create usage record
        record = TokenUsageRecord(
            agent=agent,
            tool=tool,
            timestamp=datetime.now(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            model=model,
            optimization_applied=optimization_applied,
            cache_hit=cache_hit
        )
        
        # Update context metrics
        self.context.token_metrics.add_usage(record)
        
        # Emit WebSocket event if available
        if self.websocket_manager:
            await self._emit_usage_event(record)
        
        # Check budget alerts
        await self._check_budget_alerts()
        
        logger.info(
            f"Token usage - Agent: {agent}, Model: {model}, "
            f"Tokens: {total_tokens}, Cost: ${cost_usd:.4f}, "
            f"Cache: {cache_hit}, Optimization: {optimization_applied}"
        )
        
        return record
    
    async def _emit_usage_event(self, record: TokenUsageRecord):
        """Emit token usage event via WebSocket"""
        if not self.websocket_manager:
            return
            
        try:
            await self.websocket_manager.emit_event({
                'type': 'token_usage',
                'user_id': self.context.user_id,
                'data': {
                    'agent': record.agent,
                    'tool': record.tool,
                    'tokens_used': record.total_tokens,
                    'cost_usd': record.cost_usd,
                    'tokens_remaining': self.context.token_metrics.tokens_remaining,
                    'optimization_applied': record.optimization_applied,
                    'cache_hit': record.cache_hit,
                    'model': record.model
                }
            })
        except Exception as e:
            logger.error(f"Failed to emit token usage event: {e}")
    
    async def _check_budget_alerts(self):
        """Check and emit budget alerts"""
        metrics = self.context.token_metrics
        
        if not metrics.token_budget:
            return
            
        usage_percent = (metrics.total_tokens / metrics.token_budget) * 100
        
        # Alert thresholds
        alerts = [
            (50, "50% of token budget used"),
            (75, "75% of token budget used"),
            (90, "90% of token budget used - consider optimization"),
            (95, "95% of token budget used - aggressive optimization recommended"),
            (100, "Token budget exceeded!")
        ]
        
        for threshold, message in alerts:
            if usage_percent >= threshold:
                alert_key = f"budget_{threshold}"
                if alert_key not in metrics.budget_alerts_triggered:
                    metrics.budget_alerts_triggered.append(alert_key)
                    
                    logger.warning(f"Token budget alert: {message}")
                    
                    if self.websocket_manager:
                        await self.websocket_manager.emit_event({
                            'type': 'token_budget_alert',
                            'user_id': self.context.user_id,
                            'data': {
                                'message': message,
                                'usage_percent': usage_percent,
                                'tokens_used': metrics.total_tokens,
                                'tokens_budget': metrics.token_budget,
                                'severity': 'high' if threshold >= 90 else 'medium'
                            }
                        })
    
    def get_usage_summary(self) -> Dict:
        """Get token usage summary"""
        metrics = self.context.token_metrics
        
        return {
            'total_tokens': metrics.total_tokens,
            'total_cost_usd': metrics.total_cost_usd,
            'tokens_remaining': metrics.tokens_remaining,
            'budget_usage_percent': (
                (metrics.total_tokens / metrics.token_budget * 100)
                if metrics.token_budget else None
            ),
            'by_agent': metrics.by_agent,
            'by_tool': metrics.by_tool,
            'cache_hits': metrics.cache_hits,
            'tokens_saved': metrics.tokens_saved,
            'cost_saved_usd': metrics.cost_saved_usd,
            'optimization_stats': {
                'compression_ratio': metrics.compression_ratio,
                'cache_hit_rate': (
                    metrics.cache_hits / len(metrics.usage_history)
                    if metrics.usage_history else 0
                )
            }
        }
```

---

## 3. Enhanced DataHelper with Token Optimization

**File:** `/netra_backend/app/tools/data_helper_optimized.py`

```python
"""Optimized Data Helper with token awareness"""

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import json

from netra_backend.app.tools.data_helper import DataHelper
from netra_backend.app.optimization.token_tracker import TokenTracker
from netra_backend.app.optimization.prompt_optimizer import PromptOptimizer
from netra_backend.app.logging_config import central_logger as logger

class DataComplexity(Enum):
    """Data request complexity levels"""
    SIMPLE = "simple"      # Basic single data point
    MEDIUM = "medium"      # Multiple related data points
    COMPLEX = "complex"    # Comprehensive data collection
    CRITICAL = "critical"  # Essential missing data

class OptimizedDataHelper(DataHelper):
    """Token-optimized version of DataHelper"""
    
    def __init__(self, llm_manager, token_tracker: Optional[TokenTracker] = None):
        super().__init__(llm_manager)
        self.token_tracker = token_tracker
        self.prompt_optimizer = PromptOptimizer()
        self.complexity_analyzer = DataComplexityAnalyzer()
        
    async def generate_data_request_optimized(
        self, 
        user_request: str,
        triage_result: Dict[str, Any],
        previous_results: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate token-optimized data request"""
        
        # Analyze complexity
        complexity = self.complexity_analyzer.analyze(
            user_request, triage_result, previous_results
        )
        
        # Determine token budget
        if max_tokens is None and self.token_tracker:
            if self.token_tracker.context.can_afford_tokens(2000):
                max_tokens = 2000
            else:
                max_tokens = min(
                    1000,
                    self.token_tracker.context.token_metrics.tokens_remaining or 1000
                )
        
        # Generate optimized request based on complexity
        if complexity == DataComplexity.SIMPLE:
            result = await self._generate_simple_request(
                user_request, triage_result, max_tokens
            )
        elif complexity == DataComplexity.MEDIUM:
            result = await self._generate_chunked_request(
                user_request, triage_result, previous_results, max_tokens
            )
        elif complexity == DataComplexity.COMPLEX:
            result = await self._generate_progressive_request(
                user_request, triage_result, previous_results, max_tokens
            )
        else:  # CRITICAL
            result = await self._generate_critical_request(
                user_request, triage_result, max_tokens
            )
        
        # Track token usage if tracker available
        if self.token_tracker and 'prompt' in result and 'response' in result:
            await self.token_tracker.track_usage(
                agent='data_helper',
                prompt=result['prompt'],
                completion=result['response'],
                optimization_applied=f"complexity_{complexity.value}",
                tool='data_request_generation'
            )
        
        return result
    
    async def _generate_simple_request(
        self,
        user_request: str,
        triage_result: Dict,
        max_tokens: int
    ) -> Dict:
        """Generate simple, direct data request"""
        
        # Ultra-compressed template for simple requests
        template = """Data needed: {missing_data}
User: {user_request}
Ask: 3 specific questions
Format: numbered list"""
        
        # Extract missing data from triage
        missing_data = triage_result.get('data_needed', ['unknown'])
        
        prompt = template.format(
            missing_data=', '.join(missing_data[:3]),  # Limit to top 3
            user_request=user_request[:200]  # Truncate if needed
        )
        
        # Optimize prompt
        if self.prompt_optimizer:
            prompt = self.prompt_optimizer.compress(prompt, target_tokens=max_tokens // 2)
        
        # Generate response
        response = await self.llm_manager.agenerate(
            prompts=[prompt],
            temperature=0.3,
            max_tokens=max_tokens
        )
        
        return {
            'prompt': prompt,
            'response': response,
            'data_request': self._parse_simple_response(response),
            'complexity': 'simple',
            'tokens_estimated': len(prompt.split()) + len(response.split())
        }
    
    async def _generate_chunked_request(
        self,
        user_request: str,
        triage_result: Dict,
        previous_results: Optional[List],
        max_tokens: int
    ) -> Dict:
        """Generate chunked requests for medium complexity"""
        
        # Divide data needs into chunks
        data_needs = triage_result.get('data_needed', [])
        chunk_size = 3  # Items per chunk
        chunks = [
            data_needs[i:i + chunk_size]
            for i in range(0, len(data_needs), chunk_size)
        ]
        
        all_requests = []
        total_tokens = 0
        
        for i, chunk in enumerate(chunks):
            # Progressive template - more detail for first chunk
            if i == 0:
                template = """Generate data request:
Topic: {topic}
Data points: {data_points}
Output: 2-3 actionable questions with examples"""
            else:
                template = """Additional data:
Points: {data_points}
Output: 1-2 questions"""
            
            prompt = template.format(
                topic=user_request[:100],
                data_points=', '.join(chunk)
            )
            
            # Optimize each chunk
            if self.prompt_optimizer:
                prompt = self.prompt_optimizer.compress(
                    prompt, 
                    target_tokens=max_tokens // len(chunks)
                )
            
            response = await self.llm_manager.agenerate(
                prompts=[prompt],
                temperature=0.3,
                max_tokens=max_tokens // len(chunks)
            )
            
            all_requests.append({
                'chunk': i + 1,
                'prompt': prompt,
                'response': response,
                'data_points': chunk
            })
            
            total_tokens += len(prompt.split()) + len(response.split())
        
        return {
            'chunks': all_requests,
            'total_chunks': len(chunks),
            'complexity': 'medium',
            'tokens_estimated': total_tokens,
            'data_request': self._merge_chunked_responses(all_requests)
        }
    
    async def _generate_progressive_request(
        self,
        user_request: str,
        triage_result: Dict,
        previous_results: Optional[List],
        max_tokens: int
    ) -> Dict:
        """Progressive disclosure for complex requests"""
        
        # Stage 1: Essential data only
        stage1_template = """CRITICAL data for: {request}
Must have: {critical_data}
Output: 2 essential questions only"""
        
        critical_data = self._identify_critical_data(triage_result)
        
        stage1_prompt = stage1_template.format(
            request=user_request[:50],
            critical_data=', '.join(critical_data[:2])
        )
        
        stage1_response = await self.llm_manager.agenerate(
            prompts=[stage1_prompt],
            temperature=0.2,
            max_tokens=max_tokens // 3
        )
        
        # Stage 2: Supporting data
        stage2_template = """Supporting data:
{supporting_data}
Add: 2 clarifying questions"""
        
        supporting_data = self._identify_supporting_data(triage_result)
        
        stage2_prompt = stage2_template.format(
            supporting_data=', '.join(supporting_data[:3])
        )
        
        stage2_response = await self.llm_manager.agenerate(
            prompts=[stage2_prompt],
            temperature=0.3,
            max_tokens=max_tokens // 3
        )
        
        # Stage 3: Optional enrichment
        stage3_template = """Optional enrichment:
Format examples or benchmarks (1-2 items)"""
        
        stage3_response = await self.llm_manager.agenerate(
            prompts=[stage3_template],
            temperature=0.4,
            max_tokens=max_tokens // 3
        )
        
        return {
            'stages': [
                {'stage': 'critical', 'response': stage1_response},
                {'stage': 'supporting', 'response': stage2_response},
                {'stage': 'enrichment', 'response': stage3_response}
            ],
            'complexity': 'complex',
            'progressive_disclosure': True,
            'data_request': self._merge_progressive_responses(
                stage1_response, stage2_response, stage3_response
            )
        }
    
    async def _generate_critical_request(
        self,
        user_request: str,
        triage_result: Dict,
        max_tokens: int
    ) -> Dict:
        """Ultra-minimal critical data request"""
        
        # Absolute minimum template
        template = """URGENT: {data_type}
Ask user: {question}
Example: {example}"""
        
        # Identify single most critical data point
        critical = self._get_most_critical_data(triage_result)
        
        prompt = template.format(
            data_type=critical['type'],
            question=critical['question'],
            example=critical['example']
        )
        
        response = await self.llm_manager.agenerate(
            prompts=[prompt],
            temperature=0.1,  # Very low for consistency
            max_tokens=min(max_tokens, 200)  # Keep it short
        )
        
        return {
            'prompt': prompt,
            'response': response,
            'complexity': 'critical',
            'single_focus': True,
            'data_request': response
        }
    
    def _identify_critical_data(self, triage_result: Dict) -> List[str]:
        """Identify critical data points"""
        data_needed = triage_result.get('data_needed', [])
        
        # Prioritize based on keywords
        critical_keywords = ['cost', 'error', 'failure', 'urgent', 'broken']
        
        critical = []
        for item in data_needed:
            if any(keyword in item.lower() for keyword in critical_keywords):
                critical.append(item)
        
        return critical or data_needed[:2]
    
    def _identify_supporting_data(self, triage_result: Dict) -> List[str]:
        """Identify supporting data points"""
        data_needed = triage_result.get('data_needed', [])
        critical = self._identify_critical_data(triage_result)
        
        # Supporting = everything not critical
        supporting = [d for d in data_needed if d not in critical]
        
        return supporting[:5]  # Limit to top 5


class DataComplexityAnalyzer:
    """Analyze data request complexity"""
    
    def analyze(
        self,
        user_request: str,
        triage_result: Dict,
        previous_results: Optional[List]
    ) -> DataComplexity:
        """Determine request complexity"""
        
        # Count data points needed
        data_needed = triage_result.get('data_needed', [])
        num_data_points = len(data_needed)
        
        # Check for critical keywords
        critical_keywords = ['urgent', 'critical', 'immediate', 'broken', 'down']
        has_critical = any(
            keyword in user_request.lower()
            for keyword in critical_keywords
        )
        
        # Check previous attempts
        num_attempts = len(previous_results) if previous_results else 0
        
        # Determine complexity
        if has_critical:
            return DataComplexity.CRITICAL
        elif num_data_points > 5 or num_attempts > 2:
            return DataComplexity.COMPLEX
        elif num_data_points > 2:
            return DataComplexity.MEDIUM
        else:
            return DataComplexity.SIMPLE
```

---

## 4. Prompt Optimizer Implementation

**File:** `/netra_backend/app/optimization/prompt_optimizer.py`

```python
"""Prompt optimization for token efficiency"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger as logger

@dataclass
class OptimizationResult:
    """Result of prompt optimization"""
    original_text: str
    optimized_text: str
    original_tokens: int
    optimized_tokens: int
    reduction_percent: float
    techniques_applied: List[str]

class PromptOptimizer:
    """Optimize prompts to reduce token usage"""
    
    def __init__(self):
        # Compression rules ordered by impact
        self.compression_rules = [
            # Remove pleasantries
            (r'\bPlease\s+could\s+you\b', ''),
            (r'\bI\s+would\s+like\s+you\s+to\b', ''),
            (r'\bCan\s+you\s+please\b', ''),
            (r'\bWould\s+you\s+be\s+able\s+to\b', ''),
            (r'\bKindly\b', ''),
            
            # Compress instructions
            (r'\bYour\s+task\s+is\s+to\b', 'Task:'),
            (r'\bYou\s+should\b', 'Must'),
            (r'\bMake\s+sure\s+to\b', 'Must'),
            (r'\bIt\s+is\s+important\s+that\b', 'Important:'),
            (r'\bIn\s+order\s+to\b', 'To'),
            
            # Format compressions
            (r'\bin\s+JSON\s+format\b', 'JSON:'),
            (r'\bas\s+a\s+bullet\s+list\b', 'List:'),
            (r'\bstep\s+by\s+step\b', 'Steps:'),
            (r'\bin\s+the\s+following\s+format\b', 'Format:'),
            
            # Remove redundancy
            (r'\bvery\s+', ''),
            (r'\breally\s+', ''),
            (r'\bactually\s+', ''),
            (r'\bbasically\s+', ''),
            (r'\bsimply\s+', ''),
            
            # Compress common phrases
            (r'\bat\s+the\s+same\s+time\b', 'simultaneously'),
            (r'\bin\s+addition\s+to\b', 'plus'),
            (r'\bas\s+well\s+as\b', 'and'),
            (r'\bin\s+order\s+to\b', 'to'),
        ]
        
        # Example reduction strategies
        self.example_strategies = ExampleReducer()
        
        # Context summarization
        self.context_summarizer = ContextSummarizer()
    
    def optimize(
        self,
        prompt: str,
        target_reduction: float = 0.3,
        preserve_examples: int = 2
    ) -> OptimizationResult:
        """Optimize prompt with target reduction"""
        
        original_tokens = self._estimate_tokens(prompt)
        optimized = prompt
        techniques = []
        
        # Step 1: Apply compression rules
        optimized, rules_applied = self._apply_compression_rules(optimized)
        if rules_applied:
            techniques.append(f"compression_rules({len(rules_applied)})")
        
        # Step 2: Reduce whitespace
        optimized = self._reduce_whitespace(optimized)
        techniques.append("whitespace_reduction")
        
        # Step 3: Optimize examples if present
        if "Example:" in optimized or "example" in optimized.lower():
            optimized = self.example_strategies.reduce_examples(
                optimized, keep_n=preserve_examples
            )
            techniques.append(f"example_reduction(keep={preserve_examples})")
        
        # Step 4: Check if we met target
        current_tokens = self._estimate_tokens(optimized)
        current_reduction = 1 - (current_tokens / original_tokens)
        
        # Step 5: More aggressive if needed
        if current_reduction < target_reduction:
            # Summarize context sections
            if len(optimized) > 1000:
                optimized = self.context_summarizer.summarize_sections(optimized)
                techniques.append("context_summarization")
            
            # Remove all examples if desperate
            if current_reduction < target_reduction * 0.7:
                optimized = self.example_strategies.remove_all_examples(optimized)
                techniques.append("remove_all_examples")
        
        # Calculate final metrics
        optimized_tokens = self._estimate_tokens(optimized)
        reduction_percent = 1 - (optimized_tokens / original_tokens)
        
        logger.info(
            f"Prompt optimization: {original_tokens} → {optimized_tokens} tokens "
            f"({reduction_percent:.1%} reduction)"
        )
        
        return OptimizationResult(
            original_text=prompt,
            optimized_text=optimized,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            reduction_percent=reduction_percent,
            techniques_applied=techniques
        )
    
    def compress(self, prompt: str, target_tokens: int) -> str:
        """Compress prompt to target token count"""
        
        current_tokens = self._estimate_tokens(prompt)
        
        if current_tokens <= target_tokens:
            return prompt
        
        # Calculate required reduction
        required_reduction = 1 - (target_tokens / current_tokens)
        
        # Optimize with calculated reduction
        result = self.optimize(prompt, target_reduction=required_reduction)
        
        # If still over, truncate
        if result.optimized_tokens > target_tokens:
            result.optimized_text = self._truncate_to_tokens(
                result.optimized_text, target_tokens
            )
        
        return result.optimized_text
    
    def _apply_compression_rules(self, text: str) -> Tuple[str, List[str]]:
        """Apply compression rules"""
        applied_rules = []
        
        for pattern, replacement in self.compression_rules:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
                applied_rules.append(pattern)
        
        return text, applied_rules
    
    def _reduce_whitespace(self, text: str) -> str:
        """Reduce excessive whitespace"""
        # Multiple spaces to single
        text = re.sub(r'\s+', ' ', text)
        # Multiple newlines to double
        text = re.sub(r'\n\n+', '\n\n', text)
        # Remove trailing whitespace
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        
        return text.strip()
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 1 token per 4 chars)"""
        return len(text) // 4
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximate token count"""
        max_chars = max_tokens * 4  # Rough estimate
        
        if len(text) <= max_chars:
            return text
        
        # Try to truncate at sentence boundary
        truncated = text[:max_chars]
        last_period = truncated.rfind('.')
        if last_period > max_chars * 0.8:  # If we have 80% of content
            return truncated[:last_period + 1]
        
        return truncated + "..."


class ExampleReducer:
    """Reduce examples in prompts"""
    
    def reduce_examples(self, text: str, keep_n: int = 2) -> str:
        """Keep only N examples"""
        
        # Find example blocks
        example_pattern = r'Example\s*\d*:.*?(?=Example\s*\d*:|$)'
        examples = re.findall(example_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if len(examples) <= keep_n:
            return text
        
        # Keep first N examples
        kept_examples = examples[:keep_n]
        
        # Replace all examples with kept ones
        result = re.sub(example_pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        result += '\n\n' + '\n\n'.join(kept_examples)
        
        return result
    
    def remove_all_examples(self, text: str) -> str:
        """Remove all examples"""
        
        # Remove example blocks
        text = re.sub(
            r'Example\s*\d*:.*?(?=\n\n|$)',
            '',
            text,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Remove inline examples
        text = re.sub(
            r'\(e\.g\.,.*?\)',
            '',
            text,
            flags=re.IGNORECASE
        )
        
        text = re.sub(
            r'For example,.*?\.',
            '',
            text,
            flags=re.IGNORECASE
        )
        
        return text


class ContextSummarizer:
    """Summarize context sections"""
    
    def summarize_sections(self, text: str, max_section_length: int = 500) -> str:
        """Summarize long sections"""
        
        sections = text.split('\n\n')
        summarized_sections = []
        
        for section in sections:
            if len(section) > max_section_length:
                # Keep first and last sentences
                sentences = section.split('.')
                if len(sentences) > 3:
                    summary = (
                        sentences[0] + '.' +
                        ' [...] ' +
                        sentences[-1] + '.'
                    )
                    summarized_sections.append(summary)
                else:
                    summarized_sections.append(section)
            else:
                summarized_sections.append(section)
        
        return '\n\n'.join(summarized_sections)
```

---

## 5. Integration with Factory Pattern

**File:** `/netra_backend/app/core/user_context_tool_factory_enhanced.py`

```python
"""Enhanced factory with token optimization"""

from typing import List, Type, Optional, Dict, Any

from netra_backend.app.core.user_context_tool_factory import UserContextToolFactory
from netra_backend.app.core.execution_context_enhanced import UserExecutionContext
from netra_backend.app.optimization.token_tracker import TokenTracker
from netra_backend.app.optimization.token_budget_manager import TokenBudgetManager
from netra_backend.app.logging_config import central_logger as logger

class EnhancedUserContextToolFactory(UserContextToolFactory):
    """Factory with integrated token optimization"""
    
    @staticmethod
    async def create_optimized_tool_system(
        context: UserExecutionContext,
        tool_classes: List[Type],
        websocket_bridge_factory = None,
        enable_token_optimization: bool = True
    ) -> dict:
        """Create user tool system with token optimization"""
        
        # Initialize token tracker if optimization enabled
        token_tracker = None
        if enable_token_optimization:
            # Set up token budgets
            if context.token_budget_total:
                budget_manager = TokenBudgetManager()
                context.token_budgets_by_agent = budget_manager.allocate_budgets(
                    total_budget=context.token_budget_total,
                    agent_priorities={
                        'triage_agent': 0.1,
                        'data_agent': 0.35,
                        'optimization_agent': 0.25,
                        'action_agent': 0.15,
                        'reporting_agent': 0.15
                    }
                )
                
                logger.info(
                    f"Token budgets allocated for user {context.user_id}: "
                    f"{context.token_budgets_by_agent}"
                )
            
            # Create tracker
            websocket_manager = websocket_bridge_factory() if websocket_bridge_factory else None
            token_tracker = TokenTracker(
                context=context,
                websocket_manager=websocket_manager
            )
        
        # Create base tool system
        tool_system = await UserContextToolFactory.create_user_tool_system(
            context=context,
            tool_classes=tool_classes,
            websocket_bridge_factory=websocket_bridge_factory
        )
        
        # Enhance tools with token tracking
        if token_tracker:
            for tool in tool_system['tools']:
                # Inject tracker if tool supports it
                if hasattr(tool, 'set_token_tracker'):
                    tool.set_token_tracker(token_tracker)
                    logger.debug(f"Token tracker injected into {tool.__class__.__name__}")
                
                # Set optimization level if supported
                if hasattr(tool, 'set_optimization_level'):
                    tool.set_optimization_level(context.optimization_level)
        
        # Add token components to system
        tool_system['token_tracker'] = token_tracker
        tool_system['token_optimization_enabled'] = enable_token_optimization
        tool_system['optimization_level'] = context.optimization_level.value
        
        # Log system creation
        logger.info(
            f"Created optimized tool system for user {context.user_id}: "
            f"Tools: {len(tool_system['tools'])}, "
            f"Token optimization: {enable_token_optimization}, "
            f"Level: {context.optimization_level.value}"
        )
        
        return tool_system
```

---

## Conclusion

These implementation examples provide concrete, production-ready code that:

1. **Maintains Factory Isolation**: All token tracking is scoped to UserExecutionContext
2. **Integrates with WebSockets**: Real-time token usage events for transparency
3. **Optimizes DataHelper**: Smart chunking and progressive disclosure
4. **Provides Flexible Optimization**: Multiple levels from balanced to maximum
5. **Tracks Comprehensive Metrics**: Per-agent, per-tool, per-model breakdowns
6. **Ensures Backward Compatibility**: Existing code paths work unchanged

The implementation follows SSOT principles and integrates seamlessly with the existing factory-based architecture while providing significant token optimization capabilities.