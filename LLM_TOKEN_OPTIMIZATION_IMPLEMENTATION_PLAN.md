# LLM Token Optimization Implementation Plan
## Based on Factory-Based Architecture and DataHelper Integration

---

## Executive Summary

This implementation plan provides a comprehensive blueprint for integrating LLM token optimization into Netra's factory-based, user-isolated architecture. The plan maintains SSOT principles, leverages existing UserExecutionContext patterns, and enhances the DataHelper tool for intelligent data collection.

---

## 1. FIVE WHYS Analysis

### Why Optimize Tokens?
1. **Why optimize?** → To reduce costs (GPT-4: $0.03/1k tokens input, $0.06/1k output)
2. **Why are costs high?** → Agents send redundant context and verbose prompts
3. **Why redundant context?** → No tracking of what data was already collected
4. **Why no tracking?** → Token usage not integrated with UserExecutionContext
5. **Why not integrated?** → No token management layer in factory patterns

### Why is DataHelper Critical?
1. **Why DataHelper?** → It's the primary tool for requesting missing data
2. **Why primary?** → It understands what data is needed for optimization
3. **Why does it matter?** → Inefficient data requests waste tokens
4. **Why inefficient?** → No token-aware chunking or intelligent batching
5. **Why no batching?** → DataHelper lacks token budget awareness

### Why Must We Maintain Isolation?
1. **Why isolation?** → Multi-user concurrent execution requirement
2. **Why concurrent?** → Business needs 10+ simultaneous users
3. **Why 10+ users?** → Scale requirements for Early/Mid tier customers
4. **Why affects tokens?** → Token budgets must be per-user, not global
5. **Why per-user?** → Different users have different optimization needs/budgets

### Why Preserve WebSocket Events?
1. **Why WebSocket?** → Real-time user feedback during optimization
2. **Why real-time?** → Users need to see progress on long-running tasks
3. **Why long-running?** → Complex optimizations take 30-60 seconds
4. **Why show tokens?** → Users want cost transparency
5. **Why transparency?** → Builds trust and enables informed decisions

### Why Integrate with UVS?
1. **Why UVS?** → Unified Value Synthesis is the core value delivery
2. **Why core?** → It orchestrates all agents for business value
3. **Why affects tokens?** → UVS must allocate token budgets across agents
4. **Why allocate?** → Each agent type has different token needs
5. **Why different needs?** → Data agents need more tokens than action agents

---

## 2. Token Tracking Integration Points

### 2.1 UserExecutionContext Enhancement

**File:** `/netra_backend/app/core/execution_context.py`

```python
from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class TokenMetrics:
    """Per-request token tracking"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    token_budget: Optional[int] = None
    by_agent: Dict[str, Dict[str, int]] = field(default_factory=dict)
    by_tool: Dict[str, Dict[str, int]] = field(default_factory=dict)

@dataclass 
class UserExecutionContext:
    """Enhanced with token tracking"""
    # Existing fields...
    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)
    token_optimization_enabled: bool = True
    token_budget_total: Optional[int] = None
    token_budget_per_agent: Dict[str, int] = field(default_factory=dict)
```

### 2.2 Factory Pattern Integration

**File:** `/netra_backend/app/core/user_context_tool_factory.py`

```python
class UserContextToolFactory:
    @staticmethod
    async def create_user_tool_system(
        context: UserExecutionContext,
        tool_classes: List[Type],
        websocket_bridge_factory = None,
        token_tracker: Optional[TokenTracker] = None  # NEW
    ) -> dict:
        # Create token tracker for this user context
        if token_tracker is None:
            token_tracker = TokenTracker(
                context_id=f"{context.user_id}_{context.run_id}",
                budget=context.token_budget_total,
                websocket_manager=websocket_bridge_factory()
            )
        
        # Enhance tools with token tracking
        tracked_tools = []
        for tool_class in tool_classes:
            tool = tool_class()
            if hasattr(tool, 'set_token_tracker'):
                tool.set_token_tracker(token_tracker)
            tracked_tools.append(tool)
        
        return {
            'registry': registry,
            'dispatcher': dispatcher,
            'tools': tracked_tools,
            'bridge': bridge,
            'token_tracker': token_tracker,  # NEW
            'correlation_id': correlation_id
        }
```

### 2.3 WebSocket Event Integration

**New Events for Token Visibility:**

```python
# In websocket_manager.py
class TokenUsageEvent:
    """Real-time token usage events"""
    
    async def emit_token_usage(self, user_id: str, data: dict):
        await self.emit_event({
            'type': 'token_usage',
            'user_id': user_id,
            'data': {
                'agent': data.get('agent'),
                'tokens_used': data.get('tokens_used'),
                'tokens_remaining': data.get('tokens_remaining'),
                'cost_usd': data.get('cost_usd'),
                'optimization_applied': data.get('optimization_applied')
            }
        })
    
    async def emit_token_optimization(self, user_id: str, data: dict):
        await self.emit_event({
            'type': 'token_optimization',
            'user_id': user_id,
            'data': {
                'original_tokens': data.get('original_tokens'),
                'optimized_tokens': data.get('optimized_tokens'),
                'savings_percent': data.get('savings_percent'),
                'technique': data.get('technique')
            }
        })
```

---

## 3. DataHelper Optimization Strategy

### 3.1 Intelligent Data Request Chunking

**File:** `/netra_backend/app/tools/data_helper.py`

```python
class DataHelper:
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        self.prompt_template = data_helper_prompt_template
        self.token_tracker: Optional[TokenTracker] = None
        self.chunk_strategies = ChunkingStrategies()
        
    def set_token_tracker(self, tracker: TokenTracker):
        """Inject token tracker for optimization"""
        self.token_tracker = tracker
    
    async def generate_data_request_optimized(
        self, 
        user_request: str,
        triage_result: Dict[str, Any],
        previous_results: Optional[List[Dict[str, Any]]] = None,
        token_budget: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate token-optimized data requests"""
        
        # Step 1: Analyze request complexity
        complexity = self._analyze_request_complexity(user_request, triage_result)
        
        # Step 2: Apply chunking strategy based on complexity
        if complexity == 'high':
            # Break into multiple smaller requests
            chunks = self.chunk_strategies.progressive_disclosure(
                user_request, 
                max_tokens_per_chunk=500
            )
        elif complexity == 'medium':
            # Focused single request with examples
            chunks = self.chunk_strategies.focused_examples(
                user_request,
                max_examples=2
            )
        else:
            # Simple direct request
            chunks = self.chunk_strategies.direct_request(user_request)
        
        # Step 3: Track tokens and optimize
        if self.token_tracker:
            for chunk in chunks:
                estimated_tokens = self._estimate_tokens(chunk)
                if self.token_tracker.can_afford(estimated_tokens):
                    await self.token_tracker.track_usage(
                        'data_helper',
                        estimated_tokens
                    )
                else:
                    # Apply aggressive optimization
                    chunk = self._compress_prompt(chunk)
        
        return {
            'chunks': chunks,
            'estimated_tokens': sum(self._estimate_tokens(c) for c in chunks),
            'optimization_applied': complexity
        }
```

### 3.2 Token-Aware Prompt Engineering

**File:** `/netra_backend/app/tools/prompt_optimizer.py`

```python
class PromptOptimizer:
    """Optimize prompts for token efficiency"""
    
    def __init__(self):
        self.compression_rules = {
            # Remove verbose phrases
            "Please could you": "",
            "I would like you to": "",
            "Can you please": "",
            
            # Shorten instructions
            "Your task is to": "Task:",
            "You should": "Must",
            "Make sure to": "Must",
            
            # Compress formats
            "in JSON format": "JSON:",
            "as a bullet list": "List:",
            "step by step": "Steps:"
        }
        
    def optimize_data_request_prompt(self, prompt: str, target_reduction: float = 0.3) -> str:
        """Reduce prompt tokens by target percentage"""
        
        # Step 1: Apply compression rules
        optimized = prompt
        for long_form, short_form in self.compression_rules.items():
            optimized = optimized.replace(long_form, short_form)
        
        # Step 2: Remove redundant examples if over budget
        if self._count_tokens(optimized) > 1000:
            optimized = self._reduce_examples(optimized, keep_n=2)
        
        # Step 3: Summarize context if still over budget
        if self._count_tokens(optimized) > 800:
            optimized = self._summarize_context(optimized)
        
        # Step 4: Track optimization metrics
        original_tokens = self._count_tokens(prompt)
        optimized_tokens = self._count_tokens(optimized)
        reduction = (original_tokens - optimized_tokens) / original_tokens
        
        logger.info(f"Prompt optimization: {original_tokens} → {optimized_tokens} tokens ({reduction:.1%} reduction)")
        
        return optimized
```

### 3.3 Caching Mechanisms

**File:** `/netra_backend/app/tools/token_cache.py`

```python
class TokenAwareCache:
    """Cache responses to avoid redundant token usage"""
    
    def __init__(self, max_size_mb: int = 100):
        self.cache: Dict[str, CachedResponse] = {}
        self.access_patterns: Dict[str, List[datetime]] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
    async def get_or_compute(
        self,
        key: str,
        compute_fn: Callable,
        token_cost: int,
        ttl_seconds: int = 3600
    ) -> Tuple[Any, bool]:
        """Get from cache or compute with token tracking"""
        
        # Check cache first
        if key in self.cache:
            cached = self.cache[key]
            if not cached.is_expired():
                # Track cache hit
                self._track_access(key)
                logger.info(f"Cache hit saved {token_cost} tokens")
                return cached.response, True
        
        # Compute and cache
        response = await compute_fn()
        self.cache[key] = CachedResponse(
            response=response,
            token_cost=token_cost,
            created_at=datetime.now(),
            ttl_seconds=ttl_seconds
        )
        
        # Evict if over size limit
        self._evict_if_needed()
        
        return response, False
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        total_saved_tokens = sum(
            r.token_cost * len(self.access_patterns.get(k, []))
            for k, r in self.cache.items()
        )
        
        return {
            'cached_items': len(self.cache),
            'total_saved_tokens': total_saved_tokens,
            'estimated_savings_usd': total_saved_tokens * 0.00003,  # GPT-4 rate
            'cache_hit_rate': self._calculate_hit_rate()
        }
```

---

## 4. Agent-Level Optimizations

### 4.1 Token Budget Allocation

**File:** `/netra_backend/app/agents/token_budget_manager.py`

```python
class TokenBudgetManager:
    """Allocate token budgets across agents"""
    
    DEFAULT_BUDGETS = {
        'triage_agent': 500,       # Quick classification
        'data_agent': 3000,        # Heavy data collection  
        'optimization_agent': 2000, # Analysis and recommendations
        'action_agent': 1000,       # Execution instructions
        'reporting_agent': 1500     # Summary generation
    }
    
    def allocate_budgets(
        self,
        total_budget: int,
        agent_priorities: Dict[str, float],
        minimum_per_agent: int = 200
    ) -> Dict[str, int]:
        """Dynamically allocate token budgets"""
        
        # Ensure minimums
        budgets = {agent: minimum_per_agent for agent in self.DEFAULT_BUDGETS}
        remaining = total_budget - (len(budgets) * minimum_per_agent)
        
        # Allocate based on priorities
        for agent, priority in agent_priorities.items():
            additional = int(remaining * priority)
            budgets[agent] = budgets.get(agent, 0) + additional
            
        return budgets
```

### 4.2 Context Window Management

**File:** `/netra_backend/app/agents/context_manager.py`

```python
class ContextWindowManager:
    """Manage context windows to prevent token overflow"""
    
    MODEL_LIMITS = {
        'gpt-4': 8192,
        'gpt-4-turbo': 128000,
        'gpt-3.5-turbo': 16384,
        'claude-3-opus': 200000,
        'claude-3-sonnet': 200000
    }
    
    def __init__(self, model: str = 'gpt-4'):
        self.model = model
        self.max_tokens = self.MODEL_LIMITS.get(model, 8192)
        self.safety_margin = 0.9  # Use only 90% of limit
        
    def manage_context(
        self,
        system_prompt: str,
        conversation_history: List[Dict],
        new_message: str,
        max_response_tokens: int = 2000
    ) -> Tuple[str, List[Dict]]:
        """Manage context to fit within token limits"""
        
        # Calculate available tokens
        available = int(self.max_tokens * self.safety_margin) - max_response_tokens
        
        # Priority order: new message > system prompt > recent history
        token_count = self._count_tokens(new_message) + self._count_tokens(system_prompt)
        
        # Truncate history if needed
        truncated_history = []
        for msg in reversed(conversation_history):
            msg_tokens = self._count_tokens(str(msg))
            if token_count + msg_tokens > available:
                break
            truncated_history.insert(0, msg)
            token_count += msg_tokens
            
        # Summarize if significant truncation
        if len(truncated_history) < len(conversation_history) * 0.5:
            summary = self._summarize_truncated(
                conversation_history[:len(conversation_history) - len(truncated_history)]
            )
            truncated_history.insert(0, {'role': 'system', 'content': f"Previous context summary: {summary}"})
            
        return system_prompt, truncated_history
```

### 4.3 Prompt Template Optimization

**File:** `/netra_backend/app/agents/prompts/optimized_templates.py`

```python
class OptimizedPromptTemplates:
    """Token-optimized prompt templates"""
    
    # Before: 500+ tokens
    # After: 150 tokens
    TRIAGE_TEMPLATE_OPTIMIZED = """Task: Classify user request
    
Request: {user_request}
    
Output JSON:
{{
  "category": "cost|performance|quality|general",
  "urgency": "high|medium|low",
  "data_needed": ["list", "of", "required", "data"],
  "suggested_agent": "data|optimization|action"
}}"""

    # Before: 800+ tokens
    # After: 250 tokens
    DATA_REQUEST_OPTIMIZED = """Generate data request for optimization.
    
User: {user_request}
Triage: {triage_result}
    
Steps:
1. Identify missing data
2. Create 3-5 specific questions
3. Provide example format
    
Output: Actionable data request (max 200 words)"""

    # Smart template selection based on context
    @classmethod
    def select_template(cls, agent_type: str, context_richness: str) -> str:
        templates = {
            ('triage', 'minimal'): cls.TRIAGE_TEMPLATE_OPTIMIZED,
            ('triage', 'rich'): cls.TRIAGE_TEMPLATE_DETAILED,
            ('data', 'minimal'): cls.DATA_REQUEST_OPTIMIZED,
            ('data', 'rich'): cls.DATA_REQUEST_DETAILED,
        }
        return templates.get((agent_type, context_richness), cls.FALLBACK_TEMPLATE)
```

---

## 5. System-Wide Token Management

### 5.1 Token Usage Analytics

**File:** `/netra_backend/app/analytics/token_analytics.py`

```python
class TokenAnalytics:
    """Track and analyze token usage patterns"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.metrics_cache = {}
        
    async def track_usage(
        self,
        user_id: str,
        session_id: str,
        agent: str,
        tokens_used: int,
        cost_usd: float,
        optimization_applied: bool = False
    ):
        """Record token usage"""
        await self.db.execute("""
            INSERT INTO token_usage 
            (user_id, session_id, agent, tokens_used, cost_usd, optimization_applied, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, user_id, session_id, agent, tokens_used, cost_usd, optimization_applied)
        
        # Update real-time metrics
        self._update_metrics_cache(user_id, tokens_used, cost_usd)
        
    async def get_user_analytics(self, user_id: str, period_days: int = 30) -> Dict:
        """Get comprehensive token analytics for user"""
        
        # Query usage data
        usage_data = await self.db.fetch("""
            SELECT 
                agent,
                SUM(tokens_used) as total_tokens,
                SUM(cost_usd) as total_cost,
                AVG(tokens_used) as avg_tokens,
                COUNT(*) as request_count,
                SUM(CASE WHEN optimization_applied THEN tokens_used ELSE 0 END) as optimized_tokens
            FROM token_usage
            WHERE user_id = $1 
            AND timestamp > NOW() - INTERVAL '%s days'
            GROUP BY agent
        """, user_id, period_days)
        
        # Calculate optimization impact
        total_tokens = sum(row['total_tokens'] for row in usage_data)
        optimized_tokens = sum(row['optimized_tokens'] for row in usage_data)
        optimization_rate = optimized_tokens / total_tokens if total_tokens > 0 else 0
        
        return {
            'total_tokens': total_tokens,
            'total_cost_usd': sum(row['total_cost'] for row in usage_data),
            'by_agent': {row['agent']: dict(row) for row in usage_data},
            'optimization_rate': optimization_rate,
            'estimated_savings': self._calculate_savings(usage_data),
            'recommendations': self._generate_recommendations(usage_data)
        }
```

### 5.2 Cost Tracking and Reporting

**File:** `/netra_backend/app/reporting/token_cost_reporter.py`

```python
class TokenCostReporter:
    """Generate token cost reports"""
    
    def __init__(self, analytics: TokenAnalytics):
        self.analytics = analytics
        
    async def generate_cost_report(
        self,
        user_id: str,
        format: str = 'summary'
    ) -> Dict:
        """Generate cost report for user"""
        
        # Get analytics data
        data = await self.analytics.get_user_analytics(user_id)
        
        if format == 'summary':
            return {
                'period': 'Last 30 days',
                'total_cost': f"${data['total_cost_usd']:.2f}",
                'total_tokens': f"{data['total_tokens']:,}",
                'average_cost_per_request': f"${data['total_cost_usd'] / data['request_count']:.4f}",
                'top_consumer': max(data['by_agent'].items(), key=lambda x: x[1]['total_cost'])[0],
                'optimization_savings': f"${data['estimated_savings']:.2f}",
                'recommendations': data['recommendations'][:3]
            }
        
        elif format == 'detailed':
            return {
                'period': 'Last 30 days',
                'summary': {
                    'total_cost': data['total_cost_usd'],
                    'total_tokens': data['total_tokens'],
                    'optimization_rate': data['optimization_rate']
                },
                'breakdown_by_agent': data['by_agent'],
                'daily_trend': await self._get_daily_trend(user_id),
                'cost_by_model': await self._get_model_breakdown(user_id),
                'optimization_impact': {
                    'tokens_saved': data['optimized_tokens'],
                    'cost_saved': data['estimated_savings'],
                    'techniques_used': await self._get_optimization_techniques(user_id)
                }
            }
```

### 5.3 Automatic Optimization Triggers

**File:** `/netra_backend/app/optimization/auto_optimizer.py`

```python
class AutoTokenOptimizer:
    """Automatically trigger optimizations based on patterns"""
    
    def __init__(self, analytics: TokenAnalytics, threshold_config: Dict):
        self.analytics = analytics
        self.thresholds = threshold_config
        
    async def check_optimization_triggers(self, context: UserExecutionContext) -> List[str]:
        """Check if optimization should be triggered"""
        
        triggers = []
        
        # Check token usage rate
        if context.token_metrics.total_tokens > self.thresholds['high_usage_tokens']:
            triggers.append('high_token_usage')
            
        # Check cost threshold  
        if context.token_metrics.cost_usd > self.thresholds['high_cost_usd']:
            triggers.append('high_cost')
            
        # Check inefficiency patterns
        efficiency = await self._calculate_efficiency(context)
        if efficiency < self.thresholds['min_efficiency']:
            triggers.append('low_efficiency')
            
        # Check repetitive patterns
        if await self._detect_repetitive_patterns(context):
            triggers.append('repetitive_queries')
            
        return triggers
    
    async def apply_optimizations(
        self,
        context: UserExecutionContext,
        triggers: List[str]
    ) -> Dict:
        """Apply appropriate optimizations"""
        
        optimizations_applied = []
        
        if 'high_token_usage' in triggers:
            # Switch to more aggressive compression
            context.token_optimization_level = 'aggressive'
            optimizations_applied.append('aggressive_compression')
            
        if 'high_cost' in triggers:
            # Switch to cheaper models where possible
            context.preferred_model = 'gpt-3.5-turbo'
            optimizations_applied.append('model_downgrade')
            
        if 'low_efficiency' in triggers:
            # Enable smart caching
            context.enable_smart_caching = True
            optimizations_applied.append('smart_caching')
            
        if 'repetitive_queries' in triggers:
            # Enable pattern-based responses
            context.enable_pattern_matching = True
            optimizations_applied.append('pattern_matching')
            
        return {
            'triggers': triggers,
            'optimizations': optimizations_applied,
            'estimated_savings': await self._estimate_savings(optimizations_applied)
        }
```

---

## 6. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Enhance UserExecutionContext with TokenMetrics
- [ ] Create TokenTracker class
- [ ] Integrate with UserContextToolFactory
- [ ] Add basic token counting to LLMManager

### Phase 2: DataHelper Enhancement (Week 2)
- [ ] Implement token-aware data chunking
- [ ] Add prompt compression
- [ ] Create caching layer
- [ ] Integrate with WebSocket events

### Phase 3: Agent Optimization (Week 3)
- [ ] Implement TokenBudgetManager
- [ ] Create ContextWindowManager
- [ ] Optimize prompt templates
- [ ] Add per-agent token tracking

### Phase 4: Analytics & Automation (Week 4)
- [ ] Build TokenAnalytics system
- [ ] Create cost reporting
- [ ] Implement auto-optimization triggers
- [ ] Add monitoring dashboard

---

## 7. Success Metrics

### Token Reduction Targets
- **Overall:** 40-60% reduction in token usage
- **DataHelper:** 50% reduction through smart chunking
- **Prompt Templates:** 70% reduction through optimization
- **Caching:** 30% of requests served from cache

### Performance Improvements
- **Response Time:** 25% faster through smaller prompts
- **Throughput:** 2x more requests within same token budget
- **Cache Hit Rate:** >40% for common patterns

### Cost Savings Projections
- **Monthly Savings:** $5,000-$15,000 per enterprise customer
- **Per-Request Cost:** Reduce from $0.50 to $0.15 average
- **ROI:** 10-20x return on optimization investment

### User Experience Enhancements
- **Transparency:** Real-time token usage visibility
- **Control:** User-defined token budgets
- **Insights:** Optimization recommendations
- **Trust:** Clear cost breakdowns

---

## 8. Backward Compatibility

### Maintaining Existing Interfaces
- All optimizations are opt-in via configuration
- Existing code paths remain unchanged
- New methods alongside existing ones
- Gradual migration strategy

### Migration Path
```python
# Old interface still works
response = await data_helper.generate_data_request(...)

# New optimized interface available
response = await data_helper.generate_data_request_optimized(
    ...,
    token_budget=5000,
    optimization_level='balanced'
)
```

---

## 9. Testing Strategy

### Unit Tests
- Token counting accuracy
- Prompt compression effectiveness
- Cache hit/miss scenarios
- Budget allocation logic

### Integration Tests
- Factory pattern with token tracking
- WebSocket event emission
- Multi-user isolation
- Agent coordination with budgets

### Performance Tests
- Token reduction measurements
- Response time improvements
- Cache performance under load
- Memory usage with caching

### Business Value Tests
- Cost savings calculations
- User experience metrics
- Optimization trigger accuracy
- Report generation accuracy

---

## 10. Monitoring & Observability

### Key Metrics to Track
```python
TOKEN_METRICS = {
    'token_usage_per_user': Gauge,
    'token_cost_per_request': Histogram,
    'cache_hit_rate': Gauge,
    'optimization_trigger_rate': Counter,
    'prompt_compression_ratio': Histogram,
    'model_selection_distribution': Counter,
    'budget_exceeded_events': Counter,
    'websocket_token_events': Counter
}
```

### Alerts
- Token budget exceeded (>90% of limit)
- Unusual token spike (>3x average)
- Cache performance degradation (<20% hit rate)
- Optimization failure rate (>5%)

---

## Conclusion

This implementation plan provides a comprehensive approach to integrating token optimization into Netra's factory-based architecture. By maintaining user isolation, enhancing the DataHelper tool, and adding systematic token tracking, we can achieve significant cost savings while improving user experience.

The phased approach ensures backward compatibility and allows for iterative improvements based on real-world usage patterns. Success will be measured through concrete metrics including token reduction, cost savings, and user satisfaction.

**Next Steps:**
1. Review and approve implementation plan
2. Begin Phase 1 implementation
3. Set up monitoring infrastructure
4. Create user documentation for token features