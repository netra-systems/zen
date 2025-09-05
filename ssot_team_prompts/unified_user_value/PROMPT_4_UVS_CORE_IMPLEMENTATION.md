# PROMPT 4: UVS Core Implementation Engineer - ReportingSubAgent Enhancement

## COPY THIS ENTIRE PROMPT INTO A NEW CLAUDE INSTANCE:

You are implementing the Unified User Value System (UVS) core functionality by enhancing the EXISTING ReportingSubAgent class. This implementation enables iterative user loops and guarantees value delivery.

## CRITICAL CONTEXT - READ FIRST:

The UVS implementation must support real user journeys:
- Users start with problems, not data ("reduce AI costs")  
- They need imagination and guidance on what's possible
- Data collection happens progressively over multiple interactions
- Each report generates new questions (iterative loops)
- The system MUST NEVER crash and ALWAYS provide value

The ReportingSubAgent at `netra_backend/app/agents/reporting_sub_agent.py` is the SINGLE SOURCE OF TRUTH for all user value delivery.

## YOUR IMPLEMENTATION TASK:

Enhance ReportingSubAgent with UVS capabilities while maintaining SSOT.

### 1. Core UVS Implementation

```python
# Location: netra_backend/app/agents/reporting_sub_agent.py

import asyncio
import json
import time
from typing import Any, Dict, Optional, List, Tuple
from enum import Enum
from datetime import datetime

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class LoopType(Enum):
    """UVS Loop Types"""
    IMAGINATION = "imagination"  # User needs help imagining what's possible
    DATA_DISCOVERY = "data_discovery"  # User has goal but needs data
    REFINEMENT = "refinement"  # User refining based on report
    CONTEXT = "context"  # User changing scope/parameters
    COMPLETION = "completion"  # User satisfied with optimization


class ValueLevel(Enum):
    """UVS Progressive Value Levels"""
    FULL = "full"  # 90%+ data completeness
    STANDARD = "standard"  # 70-90% data
    BASIC = "basic"  # 40-70% data  
    MINIMAL = "minimal"  # 10-40% data
    FALLBACK_IMAGINATION = "fallback_imagination"  # <10% data


class ReportingSubAgent(BaseAgent):
    """SSOT ReportingSubAgent - Enhanced with UVS for iterative value delivery
    
    Business Value: 100% user value guarantee through iterative optimization loops
    """
    
    # UVS Value Level Requirements
    UVS_LEVELS = {
        ValueLevel.FULL: ['action_plan_result', 'optimizations_result', 'data_result', 'triage_result'],
        ValueLevel.STANDARD: ['optimizations_result', 'data_result', 'triage_result'],
        ValueLevel.BASIC: ['data_result', 'triage_result'],
        ValueLevel.MINIMAL: ['triage_result'],
        ValueLevel.FALLBACK_IMAGINATION: []
    }
    
    def __init__(self, context: Optional[UserExecutionContext] = None):
        """Initialize with UVS enhancements"""
        super().__init__(
            name="ReportingSubAgent",
            description="UVS core for guaranteed user value delivery",
            enable_reliability=False,
            enable_execution_engine=True,
            enable_caching=True
        )
        
        self._user_context = context
        
        # UVS Components
        self._loop_detector = LoopPatternDetector()
        self._value_calculator = ProgressiveValueCalculator()
        self._context_preserver = ContextPreserver(context) if context else None
        self._data_helper_coordinator = DataHelperCoordinator(context) if context else None
        self._checkpoint_manager = UVSCheckpointManager(context) if context else None
        
        # Iteration tracking
        self._current_iteration = 0
        self._journey_context = {}
    
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with UVS iterative loop support"""
        
        # Validate context
        if not isinstance(context, UserExecutionContext):
            raise ValueError(f"Invalid context type: {type(context)}")
        
        try:
            # Emit start event
            if stream_updates:
                await self.emit_agent_started("Starting UVS value delivery...")
            
            # 1. Detect loop type
            loop_type = await self._detect_loop_type(context)
            
            if stream_updates:
                await self.emit_thinking(f"Detected {loop_type.value} loop pattern...")
            
            # 2. Load journey context
            journey = await self._load_journey_context(context)
            self._current_iteration = journey.get('iteration_count', 0) + 1
            
            # 3. Check for checkpoints
            checkpoint = await self._check_for_checkpoint(context)
            if checkpoint:
                logger.info(f"Resuming from checkpoint: {checkpoint['loop_id']}")
            
            # 4. Calculate value level
            value_level = self._calculate_value_level(context.metadata)
            
            if stream_updates:
                await self.emit_thinking(f"Generating {value_level.value} level value...")
            
            # 5. Generate appropriate response
            result = await self._generate_uvs_response(
                value_level, loop_type, context, journey, stream_updates
            )
            
            # 6. Save iteration context
            await self._save_iteration_context(context, loop_type, value_level, result)
            
            # 7. Emit completion
            if stream_updates:
                await self.emit_agent_completed(result)
            
            return result
            
        except Exception as e:
            # UVS GUARANTEE: Never fail, always provide value
            logger.error(f"Error in UVS execution: {e}")
            return await self._generate_guaranteed_value(context, e, stream_updates)
    
    async def _detect_loop_type(self, context: UserExecutionContext) -> LoopType:
        """Detect which loop the user is in"""
        
        metadata = context.metadata
        request = metadata.get('user_request', '')
        
        # Check for loop indicators
        if not metadata or len(metadata) <= 2:
            # Very little data - needs imagination
            return LoopType.IMAGINATION
        
        if 'previous_report_id' in metadata or 'iteration' in metadata:
            # Follow-up question - refinement
            if any(word in request.lower() for word in ['what about', 'how about', 'but', 'also']):
                return LoopType.REFINEMENT
        
        if 'scope_change' in metadata or 'timeframe' in metadata:
            # Scope adjustment
            return LoopType.CONTEXT
        
        data_completeness = self._assess_data_completeness(metadata)
        if 0.1 <= data_completeness < 0.7:
            # Has some data but needs more
            return LoopType.DATA_DISCOVERY
        
        if data_completeness >= 0.9:
            # Enough data for completion
            return LoopType.COMPLETION
        
        # Default to data discovery
        return LoopType.DATA_DISCOVERY
    
    def _calculate_value_level(self, metadata: Dict) -> ValueLevel:
        """Calculate achievable value level from available data"""
        
        completeness = self._assess_data_completeness(metadata)
        
        if completeness >= 0.9:
            return ValueLevel.FULL
        elif completeness >= 0.7:
            return ValueLevel.STANDARD
        elif completeness >= 0.4:
            return ValueLevel.BASIC
        elif completeness >= 0.1:
            return ValueLevel.MINIMAL
        else:
            return ValueLevel.FALLBACK_IMAGINATION
    
    def _assess_data_completeness(self, metadata: Dict) -> float:
        """Assess how complete the data is"""
        
        required_fields = self.UVS_LEVELS[ValueLevel.FULL]
        present_fields = [f for f in required_fields if metadata.get(f)]
        
        if not required_fields:
            return 0.0
        
        base_completeness = len(present_fields) / len(required_fields)
        
        # Adjust for data quality
        quality_multiplier = 1.0
        for field in present_fields:
            data = metadata.get(field)
            if isinstance(data, dict):
                # Check if dict has meaningful content
                if len(data) < 3:
                    quality_multiplier *= 0.8
            elif data is None or data == "":
                quality_multiplier *= 0.5
        
        return base_completeness * quality_multiplier
    
    async def _generate_uvs_response(self, value_level: ValueLevel, loop_type: LoopType,
                                    context: UserExecutionContext, journey: Dict,
                                    stream_updates: bool) -> Dict[str, Any]:
        """Generate appropriate response for value level and loop type"""
        
        if value_level == ValueLevel.FALLBACK_IMAGINATION:
            # Generate imagination guidance
            report = await self._generate_imagination_guidance(context, journey)
        else:
            # Generate progressive report
            report = await self._generate_progressive_report(
                value_level, context, journey, stream_updates
            )
        
        # Add loop-specific enhancements
        report = await self._enhance_for_loop_type(report, loop_type, context)
        
        # Determine next steps
        next_steps = await self._determine_next_steps(
            report, loop_type, value_level, context
        )
        
        return {
            'success': True,
            'loop_type': loop_type.value,
            'value_level': value_level.value,
            'iteration': self._current_iteration,
            'report': report,
            'next_steps': next_steps,
            'data_completeness': self._assess_data_completeness(context.metadata),
            'journey_progress': self._calculate_journey_progress(journey, value_level),
            'confidence_score': self._calculate_confidence(value_level, context.metadata)
        }
    
    async def _generate_imagination_guidance(self, context: UserExecutionContext, 
                                            journey: Dict) -> Dict[str, Any]:
        """Generate guidance when user has no clear starting point"""
        
        request = context.metadata.get('user_request', '')
        
        # Analyze the problem space
        problem_analysis = self._analyze_problem_statement(request)
        
        # Generate exploration options
        exploration_options = {
            'cost_optimization': {
                'description': 'Reduce AI spending by 20-40%',
                'potential_savings': '$10k-20k/month typical',
                'required_data': [
                    'Current AI/LLM invoices or billing statements',
                    'API usage reports (calls, tokens, models used)',
                    'Application logs showing LLM requests'
                ],
                'how_to_collect': {
                    'OpenAI': 'Dashboard → Usage → Export CSV',
                    'Anthropic': 'Console → Usage → Download',
                    'Azure': 'Cost Management → Export → AI Services',
                    'Internal': 'Query logs for "api.openai.com" or model names'
                },
                'quick_start': 'Start with just your latest invoice'
            },
            'latency_optimization': {
                'description': 'Improve response times by 30-50%',
                'potential_improvement': '500ms → 250ms typical',
                'required_data': [
                    'Response time metrics',
                    'Model selection patterns',
                    'Request/response sizes'
                ],
                'how_to_collect': {
                    'CloudWatch': 'Metrics → API Gateway → Latency',
                    'DataDog': 'APM → Services → Filter by AI',
                    'Logs': 'grep for response times in ms'
                },
                'quick_start': 'Run: curl -w "%{time_total}" your-api'
            },
            'quality_optimization': {
                'description': 'Balance cost and output quality',
                'potential_impact': 'Same quality at 40% less cost',
                'required_data': [
                    'Current model usage distribution',
                    'Quality metrics or user feedback',
                    'Task complexity analysis'
                ],
                'how_to_collect': {
                    'Metrics': 'User satisfaction scores',
                    'A/B Tests': 'Model comparison results',
                    'Feedback': 'Support tickets mentioning AI'
                },
                'quick_start': 'List your use cases and current models'
            }
        }
        
        return {
            'type': 'imagination_guidance',
            'understanding': f"I understand you need to: {problem_analysis['goal']}",
            'exploration_options': exploration_options,
            'recommended_start': problem_analysis['recommended_path'],
            'simple_first_step': {
                'action': 'Gather any AI-related invoice or usage data you have',
                'why': 'Even partial data helps identify optimization opportunities',
                'time_needed': '5-10 minutes'
            },
            'education': {
                'common_optimizations': [
                    'Cache repeated queries (30-50% reduction)',
                    'Use smaller models for simple tasks (60% savings)',
                    'Batch similar requests (40% efficiency gain)',
                    'Implement prompt compression (20% token reduction)'
                ],
                'typical_savings': '25-40% cost reduction without quality loss'
            }
        }
    
    async def _generate_progressive_report(self, value_level: ValueLevel,
                                          context: UserExecutionContext,
                                          journey: Dict, stream_updates: bool) -> Dict:
        """Generate report based on available data"""
        
        metadata = context.metadata
        report = {
            'type': 'progressive_analysis',
            'value_level': value_level.value,
            'sections': {}
        }
        
        # Add sections based on available data
        if metadata.get('triage_result'):
            report['sections']['classification'] = {
                'title': 'Request Analysis',
                'content': self._format_triage_section(metadata['triage_result'])
            }
        
        if metadata.get('data_result'):
            report['sections']['data_insights'] = {
                'title': 'Data Analysis',
                'content': self._format_data_section(metadata['data_result']),
                'visualizations': self._generate_visualizations(metadata['data_result'])
            }
        
        if metadata.get('optimizations_result'):
            report['sections']['recommendations'] = {
                'title': 'Optimization Recommendations',
                'content': self._format_optimization_section(metadata['optimizations_result']),
                'priority': self._prioritize_recommendations(metadata['optimizations_result'])
            }
        
        if metadata.get('action_plan_result'):
            report['sections']['implementation'] = {
                'title': 'Implementation Plan',
                'content': self._format_action_section(metadata['action_plan_result']),
                'timeline': self._generate_timeline(metadata['action_plan_result'])
            }
        
        # Always add next steps based on what's missing
        missing_data = self._identify_missing_data(metadata, value_level)
        if missing_data:
            report['sections']['data_needed'] = {
                'title': 'Additional Data for Deeper Analysis',
                'content': self._format_data_request(missing_data),
                'priority': 'high' if value_level == ValueLevel.MINIMAL else 'medium'
            }
        
        return report
    
    async def _determine_next_steps(self, report: Dict, loop_type: LoopType,
                                   value_level: ValueLevel, 
                                   context: UserExecutionContext) -> Dict:
        """Determine next steps for user"""
        
        next_steps = {
            'immediate_actions': [],
            'data_requests': {},
            'follow_up_questions': [],
            'automation_opportunities': []
        }
        
        # Loop-specific next steps
        if loop_type == LoopType.IMAGINATION:
            next_steps['immediate_actions'] = [
                'Choose one optimization area to start',
                'Gather the "quick start" data suggested',
                'Come back with any data you can find'
            ]
        
        elif loop_type == LoopType.DATA_DISCOVERY:
            missing = self._identify_missing_data(context.metadata, value_level)
            next_steps['data_requests'] = {
                field: self._generate_collection_instructions(field)
                for field in missing[:3]  # Limit to top 3 to not overwhelm
            }
        
        elif loop_type == LoopType.REFINEMENT:
            next_steps['follow_up_questions'] = [
                'Would you like to explore latency optimization?',
                'Should we analyze cost-quality tradeoffs?',
                'Do you need region-specific optimization?'
            ]
        
        # Add value-level specific steps
        if value_level in [ValueLevel.MINIMAL, ValueLevel.BASIC]:
            next_steps['immediate_actions'].append(
                'Provide additional data for comprehensive analysis'
            )
        
        return next_steps
    
    def _identify_missing_data(self, metadata: Dict, current_level: ValueLevel) -> List[str]:
        """Identify what data is missing for next level"""
        
        # Get requirements for next level
        next_level_map = {
            ValueLevel.FALLBACK_IMAGINATION: ValueLevel.MINIMAL,
            ValueLevel.MINIMAL: ValueLevel.BASIC,
            ValueLevel.BASIC: ValueLevel.STANDARD,
            ValueLevel.STANDARD: ValueLevel.FULL,
            ValueLevel.FULL: ValueLevel.FULL
        }
        
        next_level = next_level_map[current_level]
        required = self.UVS_LEVELS[next_level]
        
        missing = [field for field in required if not metadata.get(field)]
        
        # Add quality improvements for existing fields
        for field in required:
            if metadata.get(field):
                data_quality = self._assess_field_quality(metadata[field])
                if data_quality < 0.7:
                    missing.append(f"{field}_enhanced")
        
        return missing
    
    def _generate_collection_instructions(self, field: str) -> Dict[str, str]:
        """Generate specific instructions for collecting missing data"""
        
        instructions = {
            'token_usage': {
                'what': 'Token consumption data',
                'why': 'Identifies optimization opportunities',
                'how': 'Export from provider dashboard or parse API responses',
                'format': 'CSV or JSON with: date, model, input_tokens, output_tokens'
            },
            'model_distribution': {
                'what': 'Which models are used for what',
                'why': 'Enables model right-sizing', 
                'how': 'Log analysis or API audit',
                'format': 'JSON mapping use case to model'
            },
            'latency_metrics': {
                'what': 'Response time measurements',
                'why': 'Identifies performance bottlenecks',
                'how': 'APM tools or custom timing logs',
                'format': 'Time series data with p50, p95, p99'
            }
        }
        
        return instructions.get(field, {
            'what': f'Data for {field}',
            'why': 'Enables deeper analysis',
            'how': 'Check logs or monitoring systems',
            'format': 'Any structured format'
        })
    
    async def _save_iteration_context(self, context: UserExecutionContext,
                                     loop_type: LoopType, value_level: ValueLevel,
                                     result: Dict) -> None:
        """Save context for future iterations"""
        
        if not self._context_preserver:
            return
        
        iteration_data = {
            'iteration': self._current_iteration,
            'timestamp': datetime.utcnow().isoformat(),
            'loop_type': loop_type.value,
            'value_level': value_level.value,
            'request': context.metadata.get('user_request'),
            'data_provided': list(context.metadata.keys()),
            'value_delivered': result.get('report', {}).get('type'),
            'next_steps': result.get('next_steps'),
            'data_completeness': result.get('data_completeness')
        }
        
        await self._context_preserver.save_iteration(iteration_data)
        
        # Save checkpoint for recovery
        if self._checkpoint_manager:
            await self._checkpoint_manager.save_checkpoint({
                'loop_id': f"{context.run_id}_iter_{self._current_iteration}",
                'iteration_data': iteration_data
            })
    
    async def _generate_guaranteed_value(self, context: UserExecutionContext,
                                        error: Exception, 
                                        stream_updates: bool) -> Dict[str, Any]:
        """Guarantee value delivery even on error"""
        
        logger.error(f"Generating guaranteed value after error: {error}")
        
        # Provide educational content as ultimate fallback
        return {
            'success': True,  # Always succeed
            'loop_type': LoopType.IMAGINATION.value,
            'value_level': ValueLevel.FALLBACK_IMAGINATION.value,
            'report': {
                'type': 'educational_guidance',
                'content': {
                    'title': 'AI Optimization Guide',
                    'sections': {
                        'getting_started': {
                            'content': 'Start by collecting any AI-related invoices or usage data',
                            'time_needed': '10 minutes'
                        },
                        'common_optimizations': self._get_optimization_templates(),
                        'next_steps': {
                            'content': 'Gather data and try again, or explore options above'
                        }
                    }
                },
                'error_context': f"Technical issue encountered: {str(error)[:100]}"
            },
            'next_steps': {
                'immediate_actions': ['Start with any data you have', 'Try again in a moment'],
                'support': 'Contact support if issue persists'
            }
        }
```

### 2. Supporting Classes Implementation

```python
class LoopPatternDetector:
    """Detects user loop patterns"""
    
    def detect(self, context: UserExecutionContext) -> Tuple[LoopType, float]:
        """Detect loop type with confidence score"""
        # Implementation details...
        pass


class ProgressiveValueCalculator:
    """Calculates progressive value delivery"""
    
    def calculate(self, data: Dict) -> ValueLevel:
        """Calculate achievable value level"""
        # Implementation details...
        pass


class ContextPreserver:
    """Preserves context across iterations"""
    
    def __init__(self, context: UserExecutionContext):
        self.user_id = context.user_id if context else None
        self.thread_id = context.thread_id if context else None
        self.iterations = []
    
    async def save_iteration(self, iteration_data: Dict):
        """Save iteration for continuity"""
        # Implementation details...
        pass


class DataHelperCoordinator:
    """Coordinates data collection requests"""
    
    async def generate_contextual_request(self, missing_data: List[str],
                                         journey_stage: str) -> Dict:
        """Generate context-aware data request"""
        # Implementation details...
        pass


class UVSCheckpointManager:
    """Manages UVS checkpoints"""
    
    async def save_checkpoint(self, checkpoint_data: Dict):
        """Save checkpoint for recovery"""
        # Implementation details...
        pass
```

## CRITICAL IMPLEMENTATION NOTES:

1. **NEVER remove existing functionality** - Only enhance
2. **Maintain all WebSocket events** - agent_started, thinking, tool_executing, completed
3. **Keep factory pattern** - Don't break existing initialization
4. **Preserve SSOT** - This is the ONLY reporting class
5. **Test with real services** - No mocks in testing

## INTEGRATION REQUIREMENTS:

1. **DataHelperAgent** - Trigger when data_completeness < 0.4
2. **UnifiedTriageAgent** - Use for initial classification
3. **WorkflowOrchestrator** - Adapt workflow based on loop type
4. **UnifiedWebSocketManager** - Stream updates throughout iterations

## VALIDATION CHECKLIST:

- [ ] ReportingSubAgent class name unchanged
- [ ] Base class inheritance maintained
- [ ] All loop types implemented
- [ ] All value levels functioning
- [ ] Context preserved across iterations
- [ ] Checkpoints save/restore working
- [ ] Data helper triggers automatically
- [ ] Never crashes (100% success rate)
- [ ] WebSocket events preserved
- [ ] Factory pattern compatible

Remember: The implementation must support users going from "boss wants cost reduction" to fully optimized AI usage through multiple iterations of discovery and refinement.