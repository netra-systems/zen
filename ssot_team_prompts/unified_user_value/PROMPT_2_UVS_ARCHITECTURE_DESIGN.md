# PROMPT 2: UVS System Architect - Technical Design & Loop Architecture

## COPY THIS ENTIRE PROMPT INTO A NEW CLAUDE INSTANCE:

You are a System Architect designing the technical architecture for the Unified User Value System (UVS) that enables iterative user loops and guaranteed value delivery through the enhanced ReportingSubAgent.

## CRITICAL CONTEXT - READ FIRST:

The UVS recognizes that AI optimization is an ITERATIVE PROCESS where users:
1. Start with vague problems ("reduce AI costs")
2. Need help imagining what's possible
3. Progressively provide data through multiple interactions
4. Refine their questions based on insights
5. Loop until they achieve their optimization goals

The ReportingSubAgent is the SINGLE SOURCE OF TRUTH for delivering this value.

## YOUR TASK:

Design the complete technical architecture for UVS implementation.

### 1. Core Architecture Components

```python
# Location: netra_backend/app/agents/reporting_sub_agent.py

class ReportingSubAgent(BaseAgent):
    """UVS Core - Iterative value delivery system"""
    
    def __init__(self, context: Optional[UserExecutionContext] = None):
        super().__init__(...)
        
        # UVS Components
        self.loop_detector = LoopPatternDetector()
        self.value_calculator = ProgressiveValueCalculator()
        self.checkpoint_manager = UVSCheckpointManager(context)
        self.data_helper_coordinator = DataHelperCoordinator(context)
        self.context_preserver = ContextPreserver(context)
```

### 2. Loop Detection Architecture

```python
class LoopPatternDetector:
    """Detects user's position in optimization journey"""
    
    LOOP_PATTERNS = {
        'IMAGINATION': {
            'indicators': ['no data', 'vague request', 'help needed'],
            'confidence_threshold': 0.7,
            'next_action': 'guide_to_data_sources'
        },
        'DATA_DISCOVERY': {
            'indicators': ['has goal', 'missing metrics', 'partial data'],
            'confidence_threshold': 0.6,
            'next_action': 'request_specific_data'
        },
        'REFINEMENT': {
            'indicators': ['has report', 'follow-up question', 'different aspect'],
            'confidence_threshold': 0.5,
            'next_action': 'extend_analysis'
        },
        'CONTEXT': {
            'indicators': ['scope change', 'timeframe adjustment', 'goal shift'],
            'confidence_threshold': 0.6,
            'next_action': 'adjust_parameters'
        }
    }
    
    async def detect_loop(self, context: UserExecutionContext) -> LoopType:
        """Identify which loop the user is in"""
        # Analyze context.metadata, user_request, previous_interactions
        # Return detected loop type with confidence score
```

### 3. Progressive Value Calculator

```python
class ProgressiveValueCalculator:
    """Calculates best possible value from available data"""
    
    def calculate_value_level(self, available_data: Dict) -> ValueLevel:
        """Determine what level of value we can deliver"""
        
        data_completeness = self._assess_completeness(available_data)
        
        if data_completeness >= 0.9:
            return ValueLevel.FULL
        elif data_completeness >= 0.7:
            return ValueLevel.STANDARD
        elif data_completeness >= 0.4:
            return ValueLevel.BASIC
        elif data_completeness >= 0.1:
            return ValueLevel.MINIMAL
        else:
            return ValueLevel.FALLBACK_IMAGINATION
    
    def generate_value_package(self, level: ValueLevel, data: Dict) -> ValuePackage:
        """Create appropriate value package for the level"""
        
        return ValuePackage(
            insights=self._generate_insights(level, data),
            recommendations=self._generate_recommendations(level, data),
            next_steps=self._generate_next_steps(level, data),
            data_requests=self._identify_missing_data(level, data),
            confidence_score=self._calculate_confidence(level, data)
        )
```

### 4. Context Preservation System

```python
class ContextPreserver:
    """Maintains context across user iterations"""
    
    def __init__(self, user_context: UserExecutionContext):
        self.user_id = user_context.user_id
        self.thread_id = user_context.thread_id
        self.iteration_history = []
        
    async def save_iteration(self, iteration_data: Dict):
        """Save current iteration for future reference"""
        
        iteration = {
            'timestamp': datetime.utcnow(),
            'user_request': iteration_data['request'],
            'data_provided': iteration_data['data'],
            'value_delivered': iteration_data['value'],
            'loop_type': iteration_data['loop_type'],
            'next_steps_suggested': iteration_data['next_steps']
        }
        
        self.iteration_history.append(iteration)
        await self._persist_to_cache(iteration)
    
    async def get_journey_context(self) -> JourneyContext:
        """Get complete user journey context"""
        
        return JourneyContext(
            iterations=self.iteration_history,
            total_data_collected=self._aggregate_data(),
            optimization_progress=self._calculate_progress(),
            remaining_gaps=self._identify_gaps()
        )
```

### 5. Data Helper Coordination

```python
class DataHelperCoordinator:
    """Coordinates with DataHelperAgent for missing data"""
    
    async def generate_data_request(self, 
                                   missing_fields: List[str],
                                   context: JourneyContext) -> DataRequest:
        """Create contextual data request"""
        
        # Tailor request based on user's journey stage
        if context.is_first_iteration:
            tone = "educational"
            detail_level = "high"
        else:
            tone = "direct"
            detail_level = "concise"
        
        return DataRequest(
            missing_fields=missing_fields,
            collection_instructions=self._generate_instructions(missing_fields),
            example_formats=self._provide_examples(missing_fields),
            integration_options=self._suggest_integrations(missing_fields),
            priority_order=self._prioritize_fields(missing_fields, context)
        )
```

### 6. UVS Execution Flow

```python
async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
    """UVS-enhanced execution with loop support"""
    
    # 1. Detect loop type
    loop_type = await self.loop_detector.detect_loop(context)
    
    # 2. Load journey context
    journey = await self.context_preserver.get_journey_context()
    
    # 3. Calculate value level
    value_level = self.value_calculator.calculate_value_level(context.metadata)
    
    # 4. Generate appropriate response
    if value_level == ValueLevel.FALLBACK_IMAGINATION:
        result = await self._generate_imagination_guidance(context, journey)
    else:
        result = await self._generate_progressive_report(value_level, context, journey)
    
    # 5. Identify next steps
    next_steps = await self._determine_next_steps(result, loop_type, journey)
    
    # 6. Save iteration
    await self.context_preserver.save_iteration({
        'request': context.metadata.get('user_request'),
        'data': context.metadata,
        'value': result,
        'loop_type': loop_type,
        'next_steps': next_steps
    })
    
    # 7. Return UVS result
    return {
        'success': True,
        'loop_type': loop_type.value,
        'value_level': value_level.value,
        'report': result,
        'next_steps': next_steps,
        'journey_progress': journey.optimization_progress,
        'data_completeness': self._calculate_completeness(context.metadata)
    }
```

### 7. Imagination Mode Architecture

```python
async def _generate_imagination_guidance(self, context: UserExecutionContext, 
                                        journey: JourneyContext) -> Dict:
    """Generate guidance when user has no data"""
    
    # Analyze user's problem statement
    problem_analysis = await self._analyze_problem(context.metadata.get('user_request'))
    
    # Generate exploration options
    exploration_paths = {
        'cost_optimization': {
            'description': 'Reduce AI spending by 20-40%',
            'required_data': ['token usage', 'model types', 'request patterns'],
            'how_to_collect': {
                'OpenAI': 'Export from usage dashboard',
                'Claude': 'API usage endpoint',
                'Internal': 'Query logs for LLM calls'
            }
        },
        'latency_optimization': {
            'description': 'Improve response times by 30-50%',
            'required_data': ['response times', 'model sizes', 'batch patterns'],
            'how_to_collect': {...}
        },
        'quality_optimization': {
            'description': 'Balance cost and quality',
            'required_data': ['accuracy metrics', 'user satisfaction', 'error rates'],
            'how_to_collect': {...}
        }
    }
    
    return {
        'understanding': problem_analysis,
        'exploration_options': exploration_paths,
        'recommended_start': self._recommend_starting_point(problem_analysis),
        'quick_wins': self._identify_quick_wins(journey),
        'education': self._provide_optimization_education()
    }
```

### 8. Checkpoint System for Loops

```python
class UVSCheckpointManager:
    """Manages checkpoints across user iterations"""
    
    async def save_loop_checkpoint(self, loop_data: Dict):
        """Save loop state for continuation"""
        
        checkpoint = {
            'loop_id': self._generate_loop_id(),
            'loop_type': loop_data['loop_type'],
            'iteration_number': loop_data['iteration'],
            'data_collected': loop_data['data'],
            'insights_generated': loop_data['insights'],
            'next_expected_action': loop_data['next_action'],
            'timestamp': datetime.utcnow()
        }
        
        # Save with 24-hour TTL for loop continuation
        await self.redis_manager.setex(
            f"uvs_checkpoint:{self.user_id}:{checkpoint['loop_id']}",
            86400,  # 24 hours
            json.dumps(checkpoint)
        )
    
    async def resume_from_checkpoint(self, user_id: str) -> Optional[LoopCheckpoint]:
        """Resume previous loop if exists"""
        
        # Find most recent checkpoint
        pattern = f"uvs_checkpoint:{user_id}:*"
        checkpoints = await self.redis_manager.keys(pattern)
        
        if checkpoints:
            latest = await self._get_latest_checkpoint(checkpoints)
            return LoopCheckpoint.from_dict(latest)
        
        return None
```

### 9. Integration Points

```python
# Integration with existing systems

# 1. DataHelperAgent Integration
from netra_backend.app.agents.data_helper_agent import DataHelperAgent

async def trigger_data_collection(self, missing_data: List[str]) -> DataRequest:
    """Trigger DataHelperAgent for specific data"""
    
    data_helper = DataHelperAgent(self.llm_manager, self.tool_dispatcher, self.context)
    
    request = await data_helper.generate_contextual_request(
        missing_fields=missing_data,
        user_journey=self.journey_context,
        optimization_goal=self.current_goal
    )
    
    return request

# 2. UnifiedTriageAgent Integration  
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent

async def classify_user_intent(self, request: str) -> UserIntent:
    """Use triage to understand user intent"""
    
    triage = UnifiedTriageAgent.create_for_context(self.context)
    classification = await triage.classify(request)
    
    return UserIntent(
        primary_goal=classification.category,
        data_sufficiency=classification.data_sufficiency,
        suggested_loop=self._map_to_loop(classification)
    )

# 3. WorkflowOrchestrator Integration
async def adapt_workflow_for_loop(self, loop_type: LoopType) -> List[PipelineStep]:
    """Adapt workflow based on loop needs"""
    
    if loop_type == LoopType.IMAGINATION:
        # Minimal workflow - just guidance
        return [
            PipelineStep('triage', dependencies=[]),
            PipelineStep('data_helper', dependencies=['triage'])
        ]
    elif loop_type == LoopType.DATA_DISCOVERY:
        # Partial workflow with data collection
        return [
            PipelineStep('triage', dependencies=[]),
            PipelineStep('data', dependencies=['triage']),
            PipelineStep('data_helper', dependencies=['data'])
        ]
    # ... other loop types
```

### 10. Error Recovery with Value Guarantee

```python
async def _ensure_value_delivery(self, context: UserExecutionContext) -> Dict:
    """Guarantee value delivery even on failures"""
    
    try:
        # Try progressive generation
        return await self._generate_best_possible_report(context)
    
    except MissingDataError:
        # Fallback to data collection guidance
        return await self._generate_data_collection_guide(context)
    
    except ProcessingError:
        # Fallback to insights from partial processing
        return await self._generate_partial_insights(context)
    
    except Exception as e:
        # Ultimate fallback - educational content
        return {
            'success': True,  # Always succeed in delivering value
            'type': 'educational_guidance',
            'content': self._generate_educational_content(context),
            'error_context': str(e)[:200],
            'next_steps': 'Start with data collection guide above'
        }
```

## DELIVERABLES:

Create technical design documents including:

1. **System Architecture Diagram** - Component relationships
2. **Loop State Machine** - Transitions between loop types
3. **API Specifications** - Complete interface definitions
4. **Integration Diagrams** - How UVS connects to existing systems
5. **Data Flow Diagrams** - How data moves through iterations
6. **Error Recovery Flows** - Fallback chains
7. **Performance Specifications** - Latency and throughput targets

## VALIDATION CHECKLIST:

- [ ] Single ReportingSubAgent class maintained
- [ ] Loop detection implemented
- [ ] Context preservation designed
- [ ] Progressive value calculation defined
- [ ] Checkpoint system specified
- [ ] Data helper integration complete
- [ ] Error recovery guarantees value
- [ ] All integration points identified

Remember: The architecture must support users going through multiple iterations, learning what they need, and progressively achieving their optimization goals. We're not just processing data - we're guiding a journey.