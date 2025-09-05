# Unified User Value System (UVS) Requirements
## ReportingSubAgent Enhancement Specification v1.0

**Document Status:** FINAL REQUIREMENTS  
**Component:** `netra_backend/app/agents/reporting_sub_agent.py`  
**Business Impact:** 100% user value delivery guarantee  

---

## 1. Executive Summary

The Unified User Value System (UVS) transforms ReportingSubAgent from a static report generator into an adaptive value delivery system that guides users through iterative discovery loops. The system guarantees 100% value delivery through progressive fallback levels and automatic data helper integration.

### Core Value Proposition
- **Zero Crashes:** 100% request success rate through progressive fallbacks
- **Iterative Discovery:** Guide users from vague problems to actionable insights
- **Data Gap Filling:** Automatic detection and resolution of missing data
- **Progressive Value:** Deliver maximum value at every data sufficiency level

---

## 2. UVS Loop Specifications

### 2.1 Loop Type Definitions

```python
class UVSLoopType(Enum):
    IMAGINATION = "imagination"      # User has problem, no data
    DATA_DISCOVERY = "discovery"     # User has goal, missing data  
    REFINEMENT = "refinement"        # User has report, needs more
    CONTEXT = "context"              # User refining scope
    VALIDATION = "validation"        # User verifying recommendations
```

### 2.2 Loop Detection Patterns

```python
UVS_LOOP_DETECTORS = {
    'IMAGINATION': {
        'triggers': [
            lambda ctx: len(ctx.metadata) < 2,
            lambda ctx: not ctx.metadata.get('data_result'),
            lambda ctx: 'help' in ctx.metadata.get('user_request', '').lower()
        ],
        'confidence_threshold': 0.3
    },
    'DATA_DISCOVERY': {
        'triggers': [
            lambda ctx: ctx.metadata.get('data_sufficiency', 0) < 0.4,
            lambda ctx: bool(ctx.metadata.get('missing_data_fields')),
            lambda ctx: 'what data' in ctx.metadata.get('user_request', '').lower()
        ],
        'confidence_threshold': 0.5
    },
    'REFINEMENT': {
        'triggers': [
            lambda ctx: ctx.metadata.get('previous_report_id'),
            lambda ctx: ctx.metadata.get('user_feedback'),
            lambda ctx: any(word in ctx.metadata.get('user_request', '').lower() 
                          for word in ['more', 'also', 'what about', 'additionally'])
        ],
        'confidence_threshold': 0.7
    },
    'CONTEXT': {
        'triggers': [
            lambda ctx: ctx.metadata.get('scope_change_requested'),
            lambda ctx: not ctx.metadata.get('scope_defined'),
            lambda ctx: any(word in ctx.metadata.get('user_request', '').lower()
                          for word in ['project', 'company', 'team', 'specific'])
        ],
        'confidence_threshold': 0.6
    },
    'VALIDATION': {
        'triggers': [
            lambda ctx: ctx.metadata.get('implementation_questions'),
            lambda ctx: 'how to implement' in ctx.metadata.get('user_request', '').lower(),
            lambda ctx: ctx.metadata.get('risk_assessment_requested')
        ],
        'confidence_threshold': 0.8
    }
}
```

### 2.3 Loop Response Strategies

```python
class LoopResponseStrategy:
    """Defines response strategy for each loop type"""
    
    STRATEGIES = {
        'IMAGINATION': {
            'primary_action': 'guide_to_problem_definition',
            'data_helper_mode': 'exploratory',
            'questions': [
                "What specific AI costs concern you most?",
                "Which models/providers are you using?",
                "What's your current monthly spend range?",
                "What are your performance requirements?"
            ],
            'suggested_metrics': [
                'token_usage', 'request_latency', 'error_rates', 
                'model_distribution', 'peak_usage_times'
            ],
            'next_steps': 'Collect baseline metrics from suggested sources'
        },
        'DATA_DISCOVERY': {
            'primary_action': 'identify_data_gaps',
            'data_helper_mode': 'targeted_collection',
            'gap_analysis': True,
            'collection_priority': ['critical', 'important', 'nice_to_have'],
            'next_steps': 'Fill critical data gaps first'
        },
        'REFINEMENT': {
            'primary_action': 'extend_existing_analysis',
            'data_helper_mode': 'supplementary',
            'preserve_context': True,
            'merge_strategy': 'additive',
            'next_steps': 'Add requested dimensions to analysis'
        },
        'CONTEXT': {
            'primary_action': 'adjust_analysis_scope',
            'data_helper_mode': 'scope_specific',
            'scope_options': ['project', 'team', 'department', 'company'],
            'filter_strategy': 'hierarchical',
            'next_steps': 'Apply scope filters and re-analyze'
        },
        'VALIDATION': {
            'primary_action': 'provide_implementation_guidance',
            'data_helper_mode': 'verification',
            'validation_checks': ['feasibility', 'risk', 'dependencies'],
            'next_steps': 'Validate recommendations with real data'
        }
    }
```

---

## 3. Progressive Value Matrix

### 3.1 Value Level Definitions

```python
class UVSValueLevel:
    """Progressive value delivery levels with data requirements"""
    
    LEVELS = {
        'FULL': {
            'data_sufficiency': 0.9,  # 90%+ data available
            'required_components': [
                'action_plan_result',
                'optimizations_result', 
                'data_result',
                'triage_result'
            ],
            'deliverables': [
                'Complete analysis with confidence scores',
                'Prioritized action plan with timelines',
                'ROI projections with risk assessment',
                'Implementation roadmap',
                'Success metrics and KPIs'
            ],
            'user_message': "Complete analysis ready with high confidence"
        },
        
        'STANDARD': {
            'data_sufficiency': 0.7,  # 70-89% data available
            'required_components': [
                'optimizations_result',
                'data_result',
                'triage_result'
            ],
            'deliverables': [
                'Core analysis with noted gaps',
                'Key recommendations',
                'Quick wins identification',
                'Missing data impact assessment'
            ],
            'user_message': "Strong analysis complete. Add [specific data] for full optimization"
        },
        
        'BASIC': {
            'data_sufficiency': 0.5,  # 50-69% data available
            'required_components': [
                'data_result',
                'triage_result'
            ],
            'deliverables': [
                'Initial insights and patterns',
                'Preliminary recommendations',
                'Data collection priorities',
                'Next steps guidance'
            ],
            'user_message': "Initial analysis ready. Provide [data list] for deeper insights"
        },
        
        'MINIMAL': {
            'data_sufficiency': 0.25,  # 25-49% data available
            'required_components': ['triage_result'],
            'deliverables': [
                'Problem understanding summary',
                'Data requirements checklist',
                'Collection instructions',
                'Expected outcomes preview'
            ],
            'user_message': "I understand your needs. Let's collect this data: [list]"
        },
        
        'FALLBACK': {
            'data_sufficiency': 0,  # <25% data available
            'required_components': [],
            'deliverables': [
                'Problem exploration guide',
                'Data source suggestions',
                'Getting started checklist',
                'Value proposition preview'
            ],
            'user_message': "Let's explore your optimization goals together"
        }
    }
```

### 3.2 Value Delivery Logic

```python
class ValueDeliveryEngine:
    """Determines and delivers appropriate value level"""
    
    def determine_value_level(self, context: UserExecutionContext) -> str:
        """Calculate data sufficiency and return appropriate level"""
        sufficiency = self.calculate_data_sufficiency(context)
        
        if sufficiency >= 0.9:
            return 'FULL'
        elif sufficiency >= 0.7:
            return 'STANDARD'
        elif sufficiency >= 0.5:
            return 'BASIC'
        elif sufficiency >= 0.25:
            return 'MINIMAL'
        else:
            return 'FALLBACK'
    
    def calculate_data_sufficiency(self, context: UserExecutionContext) -> float:
        """Calculate data sufficiency score"""
        weights = {
            'action_plan_result': 0.2,
            'optimizations_result': 0.3,
            'data_result': 0.3,
            'triage_result': 0.2
        }
        
        score = 0.0
        for component, weight in weights.items():
            if context.metadata.get(component):
                completeness = self.assess_component_completeness(
                    context.metadata[component]
                )
                score += weight * completeness
                
        # Bonus for additional context
        if context.metadata.get('user_feedback'):
            score += 0.05
        if context.metadata.get('scope_defined'):
            score += 0.05
            
        return min(score, 1.0)
```

---

## 4. Data Helper Integration

### 4.1 Automatic Trigger Conditions

```python
class DataHelperTriggers:
    """Conditions that automatically invoke data helper"""
    
    AUTOMATIC_TRIGGERS = {
        'insufficient_data': {
            'condition': lambda ctx: ctx.metadata.get('data_sufficiency', 0) < 0.4,
            'priority': 'HIGH',
            'message': "Need more data for meaningful analysis"
        },
        'explicit_request': {
            'condition': lambda ctx: any(phrase in ctx.metadata.get('user_request', '').lower()
                                        for phrase in ['what data', 'need help', 'how to get']),
            'priority': 'IMMEDIATE',
            'message': "User requesting data collection help"
        },
        'missing_critical': {
            'condition': lambda ctx: bool(ctx.metadata.get('critical_missing_fields')),
            'priority': 'HIGH',
            'message': "Critical data fields missing"
        },
        'low_confidence': {
            'condition': lambda ctx: ctx.metadata.get('analysis_confidence', 1.0) < 0.5,
            'priority': 'MEDIUM',
            'message': "Low confidence due to data gaps"
        },
        'loop_detection': {
            'condition': lambda ctx: ctx.metadata.get('detected_loop') in ['IMAGINATION', 'DATA_DISCOVERY'],
            'priority': 'HIGH',
            'message': "User in discovery loop"
        }
    }
```

### 4.2 Data Helper Prompts

```python
class DataHelperPrompts:
    """Context-aware prompts for data collection guidance"""
    
    PROMPT_TEMPLATES = {
        'cost_optimization': {
            'missing_data': [
                'token_usage_by_model',
                'request_frequency',
                'peak_usage_patterns'
            ],
            'collection_guide': """
            To optimize AI costs effectively, I need:
            
            1. **Token Usage Data** (Priority: CRITICAL)
               - Source: OpenAI/Anthropic API dashboard
               - How: Export usage reports for last 30 days
               - Format: CSV with model, tokens, cost columns
               
            2. **Request Patterns** (Priority: HIGH)
               - Source: Application logs or monitoring
               - How: Query for API call timestamps
               - Format: Timestamp, model, request_type
               
            3. **Model Distribution** (Priority: MEDIUM)
               - Source: Internal analytics
               - How: Group requests by model type
               - Format: Model name, count, avg_tokens
            """,
            'quick_start': "Start with OpenAI dashboard > Usage > Export CSV"
        },
        
        'latency_optimization': {
            'missing_data': [
                'response_times_p50_p95_p99',
                'model_sizes',
                'batch_configurations'
            ],
            'collection_guide': """
            For latency optimization, collect:
            
            1. **Response Time Metrics** (Priority: CRITICAL)
               - Tool: Your APM (DataDog, New Relic, CloudWatch)
               - Metrics: p50, p95, p99 latencies
               - Timeframe: Peak hours for last week
               
            2. **Model Configuration** (Priority: HIGH)  
               - Current models and sizes
               - Batch size settings
               - Concurrency limits
               
            3. **Infrastructure Metrics** (Priority: MEDIUM)
               - GPU/CPU utilization
               - Memory usage patterns
               - Network latency
            """,
            'quick_start': "Check CloudWatch > Metrics > API Gateway latencies"
        }
    }
```

### 4.3 Data Helper Response Format

```python
class DataHelperResponse:
    """Standardized data helper response structure"""
    
    def __init__(self):
        self.data_requirements = []
        self.collection_instructions = []
        self.priority_order = []
        self.estimated_time = None
        self.tools_needed = []
        
    def format_response(self) -> Dict:
        return {
            'action': 'collect_data',
            'requirements': {
                'critical': self.filter_by_priority('CRITICAL'),
                'important': self.filter_by_priority('HIGH'),
                'nice_to_have': self.filter_by_priority('MEDIUM')
            },
            'step_by_step': self.collection_instructions,
            'tools': self.tools_needed,
            'time_estimate': self.estimated_time,
            'next_action': 'Run analysis with collected data',
            'partial_analysis_available': self.can_provide_partial_analysis()
        }
```

---

## 5. User Journey Maps

### 5.1 Journey: Zero to Hero
```mermaid
graph TD
    A[User: Help optimize AI] -->|FALLBACK| B[UVS: Exploration Mode]
    B --> C{Choose Focus Area}
    C -->|Costs| D[Cost Discovery Loop]
    C -->|Performance| E[Performance Discovery Loop]
    C -->|Quality| F[Quality Discovery Loop]
    
    D --> G[IMAGINATION: What costs concern you?]
    G --> H[User: Too expensive]
    H --> I[DATA_DISCOVERY: Need token usage data]
    I --> J[Data Helper: Collection Guide]
    J --> K[User: Provides partial data]
    K -->|BASIC| L[Initial cost analysis]
    L --> M[REFINEMENT: User wants more detail]
    M --> N[Data Helper: Additional metrics]
    N --> O[User: Complete data]
    O -->|FULL| P[Complete optimization plan]
```

### 5.2 Journey: Iterative Refinement
```mermaid
graph TD
    A[User: Cost report ready] -->|STANDARD| B[Cost Analysis Report]
    B --> C[User: What about quality?]
    C -->|REFINEMENT| D[UVS: Quality dimension needed]
    D --> E[Data Helper: Quality metrics guide]
    E --> F[User: Provides quality data]
    F --> G[Enhanced Report: Cost + Quality]
    G --> H[User: Project-specific view?]
    H -->|CONTEXT| I[UVS: Scope adjustment]
    I --> J[Filtered Analysis: Project A]
    J --> K[User: How to implement?]
    K -->|VALIDATION| L[Implementation roadmap]
```

### 5.3 Journey: Expert Fast Track
```mermaid
graph TD
    A[User: Complete dataset] -->|FULL| B[Comprehensive Analysis]
    B --> C[Action Plan + ROI]
    C --> D[User: Validate assumptions]
    D -->|VALIDATION| E[Assumption testing]
    E --> F[Risk assessment]
    F --> G[Final recommendations]
```

---

## 6. API Contract Changes

### 6.1 Enhanced ReportingSubAgent Interface

```python
class ReportingSubAgent(BaseAgent):
    """Enhanced with UVS capabilities"""
    
    # New class attributes for UVS
    UVS_LEVELS = {
        'FULL': ['action_plan_result', 'optimizations_result', 'data_result', 'triage_result'],
        'STANDARD': ['optimizations_result', 'data_result', 'triage_result'],
        'BASIC': ['data_result', 'triage_result'],
        'MINIMAL': ['triage_result'],
        'FALLBACK': []
    }
    
    # New methods for UVS
    async def detect_user_loop(self, context: UserExecutionContext) -> Optional[str]:
        """Detect which iterative loop user is in"""
        
    async def determine_value_level(self, context: UserExecutionContext) -> str:
        """Calculate appropriate value delivery level"""
        
    async def trigger_data_helper(self, context: UserExecutionContext, 
                                  missing_data: List[str]) -> Dict:
        """Invoke data helper for missing data"""
        
    async def generate_progressive_report(self, context: UserExecutionContext,
                                         value_level: str) -> Dict:
        """Generate report appropriate for value level"""
        
    async def provide_loop_guidance(self, context: UserExecutionContext,
                                   loop_type: str) -> Dict:
        """Generate guidance for user's current loop"""
        
    def calculate_data_sufficiency(self, context: UserExecutionContext) -> float:
        """Calculate data sufficiency score 0-1"""
        
    def identify_missing_critical_data(self, context: UserExecutionContext) -> List[str]:
        """Identify critical missing data fields"""
```

### 6.2 Context Metadata Extensions

```python
class EnhancedContextMetadata:
    """Extended metadata for UVS tracking"""
    
    # Loop tracking
    detected_loop: Optional[str]
    loop_iteration: int
    previous_loops: List[str]
    
    # Data sufficiency
    data_sufficiency: float
    missing_data_fields: List[str]
    critical_missing_fields: List[str]
    
    # User journey
    user_journey_stage: str
    previous_report_id: Optional[str]
    user_feedback: Optional[str]
    
    # Scope definition
    scope_defined: bool
    scope_level: Optional[str]  # project, team, company
    scope_filters: Dict[str, Any]
    
    # Analysis confidence
    analysis_confidence: float
    confidence_factors: Dict[str, float]
```

---

## 7. Implementation Requirements

### 7.1 Core Implementation Changes

```python
class ReportingSubAgent(BaseAgent):
    
    async def execute(self, context: UserExecutionContext, 
                     stream_updates: bool = False) -> Dict[str, Any]:
        """Enhanced execute with UVS logic"""
        
        # 1. Detect user loop
        loop_type = await self.detect_user_loop(context)
        if loop_type:
            context.metadata['detected_loop'] = loop_type
            
        # 2. Calculate data sufficiency
        sufficiency = self.calculate_data_sufficiency(context)
        context.metadata['data_sufficiency'] = sufficiency
        
        # 3. Determine value level
        value_level = await self.determine_value_level(context)
        
        # 4. Check for data helper triggers
        if await self.should_trigger_data_helper(context):
            missing_data = self.identify_missing_critical_data(context)
            data_helper_response = await self.trigger_data_helper(context, missing_data)
            context.metadata['data_helper_guidance'] = data_helper_response
            
        # 5. Generate progressive report
        try:
            # Never crash - always deliver value
            report = await self.generate_progressive_report(context, value_level)
            
            # 6. Add loop guidance if needed
            if loop_type:
                guidance = await self.provide_loop_guidance(context, loop_type)
                report['loop_guidance'] = guidance
                
            # 7. Include data helper guidance if triggered
            if context.metadata.get('data_helper_guidance'):
                report['next_steps'] = context.metadata['data_helper_guidance']
                
            return report
            
        except Exception as e:
            # FALLBACK: Always deliver value
            self.logger.error(f"Report generation failed: {e}")
            return await self.create_fallback_value_report(context)
```

### 7.2 Checkpoint System

```python
class UVSCheckpointManager:
    """Manages checkpoints for loop continuity"""
    
    async def save_checkpoint(self, context: UserExecutionContext, 
                             report: Dict) -> str:
        """Save checkpoint for iteration continuity"""
        checkpoint = {
            'context': context.metadata,
            'report': report,
            'timestamp': time.time(),
            'loop_iteration': context.metadata.get('loop_iteration', 0),
            'value_level': report.get('value_level')
        }
        checkpoint_id = await self.redis_manager.save_checkpoint(checkpoint)
        return checkpoint_id
    
    async def restore_checkpoint(self, checkpoint_id: str) -> Dict:
        """Restore previous iteration state"""
        return await self.redis_manager.get_checkpoint(checkpoint_id)
```

---

## 8. Success Criteria

### 8.1 Technical Metrics
- **Zero Crash Rate:** 100% request success (may use fallback)
- **Value Delivery:** 99.9% requests receive actionable output
- **Loop Detection Accuracy:** 85% correct loop identification
- **Data Helper Effectiveness:** 75% successful data collection after guidance
- **Progressive Level Distribution:**
  - FULL: 30%
  - STANDARD: 25%
  - BASIC: 20%
  - MINIMAL: 15%
  - FALLBACK: 10%

### 8.2 Business Metrics
- **User Retention:** +30% through iterative value
- **Time to First Value:** <2 minutes (MINIMAL level)
- **Complete Optimization Rate:** 60% reach FULL level within 3 loops
- **User Satisfaction:** 95% find guidance helpful
- **Data Collection Success:** 85% successfully provide requested data

### 8.3 Loop Efficiency Metrics
- **Average Loops to Completion:** 2.3 iterations
- **Loop Type Distribution:**
  - IMAGINATION: 35% (first-time users)
  - DATA_DISCOVERY: 25%
  - REFINEMENT: 20%
  - CONTEXT: 15%
  - VALIDATION: 5%

---

## 9. Migration Plan

### 9.1 Phase 1: Non-Breaking Additions (Week 1)
```python
# Add new methods without changing existing interface
class ReportingSubAgent(BaseAgent):
    # Existing methods remain unchanged
    
    # Add new UVS methods
    async def detect_user_loop(self, context): ...
    async def determine_value_level(self, context): ...
    # etc.
```

### 9.2 Phase 2: Progressive Enhancement (Week 2)
```python
# Enhance execute() to use UVS when available
async def execute(self, context, stream_updates=False):
    # Check for UVS flag in context
    if context.metadata.get('enable_uvs', False):
        return await self.execute_with_uvs(context, stream_updates)
    else:
        # Original logic
        return await self.execute_original(context, stream_updates)
```

### 9.3 Phase 3: Full Integration (Week 3)
- Enable UVS by default
- Monitor metrics
- Tune thresholds based on real data
- A/B test different guidance messages

---

## 10. Validation Checklist

- [ ] **ReportingSubAgent remains single class (SSOT)**
- [ ] **Supports iterative user loops**
- [ ] **Progressive value delivery at 5 levels**
- [ ] **Data helper integration defined**
- [ ] **Zero crash guarantee through fallbacks**
- [ ] **User guidance at every level**
- [ ] **Context preservation across loops**
- [ ] **Business value quantified**
- [ ] **WebSocket events preserved**
- [ ] **Factory pattern compatibility maintained**
- [ ] **Backward compatibility ensured**
- [ ] **Performance impact assessed**

---

## 11. Example Implementation Snippets

### 11.1 Loop Detection Implementation
```python
async def detect_user_loop(self, context: UserExecutionContext) -> Optional[str]:
    """Detect which iterative loop the user is in"""
    
    for loop_type, config in UVS_LOOP_DETECTORS.items():
        triggers_met = sum(
            1 for trigger in config['triggers'] 
            if trigger(context)
        )
        
        confidence = triggers_met / len(config['triggers'])
        if confidence >= config['confidence_threshold']:
            self.logger.info(f"Detected {loop_type} loop with {confidence:.2%} confidence")
            return loop_type
            
    return None
```

### 11.2 Progressive Report Generation
```python
async def generate_progressive_report(self, context: UserExecutionContext,
                                     value_level: str) -> Dict:
    """Generate report appropriate for value level"""
    
    level_config = UVSValueLevel.LEVELS[value_level]
    available_components = [
        comp for comp in level_config['required_components']
        if context.metadata.get(comp)
    ]
    
    report = {
        'value_level': value_level,
        'data_sufficiency': context.metadata.get('data_sufficiency', 0),
        'deliverables': [],
        'user_message': level_config['user_message']
    }
    
    # Build report from available components
    if 'action_plan_result' in available_components:
        report['action_plan'] = self.format_action_plan(
            context.metadata['action_plan_result']
        )
        
    if 'optimizations_result' in available_components:
        report['optimizations'] = self.format_optimizations(
            context.metadata['optimizations_result']
        )
        
    # Add progressive guidance
    if value_level != 'FULL':
        missing = self.identify_missing_critical_data(context)
        report['to_reach_next_level'] = {
            'required_data': missing[:3],  # Top 3 missing items
            'expected_improvement': self.estimate_improvement(missing),
            'collection_guide': self.generate_collection_guide(missing)
        }
        
    return report
```

---

## Appendix A: Data Flow Diagram

```mermaid
graph TB
    subgraph User Input
        A[User Request]
        B[Previous Context]
        C[User Feedback]
    end
    
    subgraph UVS Engine
        D[Loop Detector]
        E[Sufficiency Calculator]
        F[Value Level Selector]
        G[Data Helper Trigger]
    end
    
    subgraph Report Generation
        H[Progressive Report Builder]
        I[Loop Guidance Generator]
        J[Data Collection Guide]
    end
    
    subgraph Output
        K[Value-Appropriate Report]
        L[Next Steps Guidance]
        M[Data Helper Instructions]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    I --> J
    J --> K
    K --> L
    L --> M
```

---

## Appendix B: Risk Mitigation

### B.1 Technical Risks
- **Risk:** Loop detection false positives
- **Mitigation:** Confidence thresholds, user confirmation option

- **Risk:** Data helper overwhelming users
- **Mitigation:** Prioritized collection, quick-start guides

- **Risk:** Context loss between iterations
- **Mitigation:** Redis checkpoint system, session continuity

### B.2 Business Risks
- **Risk:** Users abandon due to data requirements
- **Mitigation:** Progressive value, partial analysis capability

- **Risk:** Reduced report quality at lower levels
- **Mitigation:** Clear communication of limitations, upgrade path

---

**END OF REQUIREMENTS DOCUMENT**

*This document defines the complete requirements for implementing the Unified User Value System in ReportingSubAgent. The system guarantees 100% value delivery through progressive fallbacks and iterative discovery loops.*