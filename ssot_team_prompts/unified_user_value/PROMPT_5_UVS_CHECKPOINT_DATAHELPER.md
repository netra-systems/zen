# PROMPT 5: UVS Checkpoint & DataHelper Integration Engineer

## COPY THIS ENTIRE PROMPT INTO A NEW CLAUDE INSTANCE:

You are implementing the checkpoint system and DataHelper integration for the Unified User Value System (UVS). This ensures user journeys can span multiple sessions and data collection is intelligently guided.

## CRITICAL CONTEXT - READ FIRST:

Users interact with the system across multiple sessions:
- Session 1: "Help me optimize AI" (gets imagination guidance)
- Session 2: "Here's my OpenAI invoice" (provides initial data)
- Session 3: "I got the token data you asked for" (provides more data)
- Session 4: "What about European traffic?" (refinement)

The system must:
- Remember context across sessions (checkpoint system)
- Guide data collection intelligently (DataHelper integration)
- Never lose progress (recovery from checkpoints)
- Adapt requests based on journey stage (contextual data requests)

## YOUR IMPLEMENTATION TASK:

Implement checkpoint management and DataHelper coordination for UVS.

### 1. UVS Checkpoint Manager Implementation

```python
# Location: netra_backend/app/agents/reporting_checkpoint_manager.py

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.services.cache.redis_manager import get_redis_manager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class UVSCheckpoint:
    """Represents a UVS checkpoint"""
    checkpoint_id: str
    user_id: str
    thread_id: str
    loop_id: str
    loop_type: str
    iteration: int
    value_level: str
    data_collected: Dict[str, Any]
    insights_generated: List[str]
    next_expected_action: str
    journey_progress: float
    created_at: datetime
    expires_at: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UVSCheckpoint':
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


class UVSCheckpointManager:
    """Manages checkpoints for UVS iterative loops
    
    Ensures user journeys can span multiple sessions with full context preservation.
    """
    
    CHECKPOINT_TTL = 86400 * 7  # 7 days for user journeys
    KEY_PREFIX = "uvs_checkpoint"
    JOURNEY_PREFIX = "uvs_journey"
    
    def __init__(self, context: UserExecutionContext):
        """Initialize with user context"""
        self.context = context
        self.user_id = context.user_id
        self.thread_id = context.thread_id
        self.run_id = context.run_id
        self.redis_manager = None
        self._lock = asyncio.Lock()
    
    async def _ensure_redis(self):
        """Ensure Redis connection"""
        if not self.redis_manager:
            self.redis_manager = await get_redis_manager()
    
    def _generate_checkpoint_key(self, loop_id: str) -> str:
        """Generate checkpoint key"""
        return f"{self.KEY_PREFIX}:{self.user_id}:{self.thread_id}:{loop_id}"
    
    def _generate_journey_key(self) -> str:
        """Generate journey tracking key"""
        return f"{self.JOURNEY_PREFIX}:{self.user_id}:{self.thread_id}"
    
    async def save_checkpoint(self, loop_type: str, iteration: int,
                             value_level: str, data_collected: Dict,
                             insights: List[str], next_action: str,
                             progress: float) -> str:
        """Save UVS checkpoint for session continuity
        
        Args:
            loop_type: Current loop type (imagination, data_discovery, etc.)
            iteration: Current iteration number
            value_level: Achieved value level
            data_collected: Data collected so far
            insights: Insights generated
            next_action: Expected next user action
            progress: Journey progress (0-1)
            
        Returns:
            Checkpoint ID for reference
        """
        async with self._lock:
            try:
                await self._ensure_redis()
                
                # Generate checkpoint ID
                loop_id = f"{loop_type}_{iteration}_{datetime.utcnow().timestamp()}"
                checkpoint_id = f"chk_{loop_id}"
                
                # Create checkpoint
                checkpoint = UVSCheckpoint(
                    checkpoint_id=checkpoint_id,
                    user_id=self.user_id,
                    thread_id=self.thread_id,
                    loop_id=loop_id,
                    loop_type=loop_type,
                    iteration=iteration,
                    value_level=value_level,
                    data_collected=data_collected,
                    insights_generated=insights,
                    next_expected_action=next_action,
                    journey_progress=progress,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(seconds=self.CHECKPOINT_TTL)
                )
                
                # Save checkpoint
                key = self._generate_checkpoint_key(loop_id)
                await self.redis_manager.setex(
                    key,
                    self.CHECKPOINT_TTL,
                    json.dumps(checkpoint.to_dict())
                )
                
                # Update journey tracking
                await self._update_journey_tracking(checkpoint)
                
                logger.info(f"Saved UVS checkpoint {checkpoint_id} for user {self.user_id}")
                return checkpoint_id
                
            except Exception as e:
                logger.error(f"Failed to save checkpoint: {e}")
                return None
    
    async def load_latest_checkpoint(self) -> Optional[UVSCheckpoint]:
        """Load most recent checkpoint for user journey
        
        Returns:
            Latest checkpoint or None if no checkpoints exist
        """
        try:
            await self._ensure_redis()
            
            # Find all checkpoints for user
            pattern = f"{self.KEY_PREFIX}:{self.user_id}:{self.thread_id}:*"
            keys = await self.redis_manager.keys(pattern)
            
            if not keys:
                return None
            
            # Load all checkpoints
            checkpoints = []
            for key in keys:
                data = await self.redis_manager.get(key)
                if data:
                    checkpoint = UVSCheckpoint.from_dict(json.loads(data))
                    checkpoints.append(checkpoint)
            
            if not checkpoints:
                return None
            
            # Return most recent
            checkpoints.sort(key=lambda c: c.created_at, reverse=True)
            latest = checkpoints[0]
            
            logger.info(f"Loaded checkpoint {latest.checkpoint_id} for user {self.user_id}")
            return latest
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    async def load_journey_history(self) -> List[UVSCheckpoint]:
        """Load complete journey history for user
        
        Returns:
            List of checkpoints in chronological order
        """
        try:
            await self._ensure_redis()
            
            # Get journey data
            journey_key = self._generate_journey_key()
            journey_data = await self.redis_manager.get(journey_key)
            
            if not journey_data:
                return []
            
            journey = json.loads(journey_data)
            checkpoint_ids = journey.get('checkpoint_ids', [])
            
            # Load checkpoints
            checkpoints = []
            for checkpoint_id in checkpoint_ids:
                # Extract loop_id from checkpoint_id
                loop_id = checkpoint_id.replace('chk_', '')
                key = self._generate_checkpoint_key(loop_id)
                
                data = await self.redis_manager.get(key)
                if data:
                    checkpoint = UVSCheckpoint.from_dict(json.loads(data))
                    checkpoints.append(checkpoint)
            
            # Sort chronologically
            checkpoints.sort(key=lambda c: c.created_at)
            
            logger.info(f"Loaded {len(checkpoints)} checkpoints for user journey")
            return checkpoints
            
        except Exception as e:
            logger.error(f"Failed to load journey history: {e}")
            return []
    
    async def _update_journey_tracking(self, checkpoint: UVSCheckpoint):
        """Update journey tracking with new checkpoint"""
        
        journey_key = self._generate_journey_key()
        
        # Get existing journey or create new
        journey_data = await self.redis_manager.get(journey_key)
        if journey_data:
            journey = json.loads(journey_data)
        else:
            journey = {
                'user_id': self.user_id,
                'thread_id': self.thread_id,
                'started_at': datetime.utcnow().isoformat(),
                'checkpoint_ids': [],
                'total_iterations': 0,
                'current_progress': 0.0
            }
        
        # Update journey
        journey['checkpoint_ids'].append(checkpoint.checkpoint_id)
        journey['total_iterations'] = checkpoint.iteration
        journey['current_progress'] = checkpoint.journey_progress
        journey['last_updated'] = datetime.utcnow().isoformat()
        journey['current_loop_type'] = checkpoint.loop_type
        journey['current_value_level'] = checkpoint.value_level
        
        # Save journey
        await self.redis_manager.setex(
            journey_key,
            self.CHECKPOINT_TTL,
            json.dumps(journey)
        )
    
    async def clear_journey(self):
        """Clear all checkpoints for a journey (completion or reset)"""
        
        try:
            await self._ensure_redis()
            
            # Get all checkpoint keys
            pattern = f"{self.KEY_PREFIX}:{self.user_id}:{self.thread_id}:*"
            keys = await self.redis_manager.keys(pattern)
            
            # Add journey key
            journey_key = self._generate_journey_key()
            keys.append(journey_key)
            
            # Delete all
            if keys:
                await self.redis_manager.delete(*keys)
            
            logger.info(f"Cleared journey for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear journey: {e}")
    
    async def get_journey_summary(self) -> Dict[str, Any]:
        """Get summary of user's journey
        
        Returns:
            Journey summary with progress and insights
        """
        
        checkpoints = await self.load_journey_history()
        
        if not checkpoints:
            return {
                'has_journey': False,
                'iterations': 0,
                'progress': 0.0
            }
        
        latest = checkpoints[-1]
        
        # Aggregate data collected
        all_data = {}
        for checkpoint in checkpoints:
            all_data.update(checkpoint.data_collected)
        
        # Aggregate insights
        all_insights = []
        for checkpoint in checkpoints:
            all_insights.extend(checkpoint.insights_generated)
        
        return {
            'has_journey': True,
            'iterations': latest.iteration,
            'progress': latest.journey_progress,
            'current_loop': latest.loop_type,
            'current_level': latest.value_level,
            'data_collected': list(all_data.keys()),
            'insights_count': len(all_insights),
            'key_insights': all_insights[-3:] if all_insights else [],
            'next_action': latest.next_expected_action,
            'journey_duration': (latest.created_at - checkpoints[0].created_at).total_seconds()
        }
```

### 2. DataHelper Coordinator Implementation

```python
# Location: netra_backend/app/agents/reporting_datahelper_coordinator.py

from typing import Dict, List, Any, Optional
from enum import Enum

from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DataRequestPriority(Enum):
    """Priority levels for data requests"""
    CRITICAL = "critical"  # Blocking analysis
    HIGH = "high"  # Significantly improves analysis
    MEDIUM = "medium"  # Enhances analysis
    LOW = "low"  # Nice to have


class DataHelperCoordinator:
    """Coordinates data collection requests for UVS
    
    Provides intelligent, context-aware data collection guidance based on:
    - User's journey stage (first-time vs returning)
    - Current loop type (imagination vs refinement)
    - Data already collected
    - User's technical level
    """
    
    def __init__(self, context: UserExecutionContext):
        """Initialize with user context"""
        self.context = context
        self.data_helper = None
    
    async def _get_data_helper(self) -> DataHelperAgent:
        """Get or create DataHelperAgent"""
        if not self.data_helper:
            from netra_backend.app.llm.llm_manager import get_llm_manager
            from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            
            llm_manager = await get_llm_manager()
            tool_dispatcher = ToolDispatcher(llm_manager, self.context)
            
            self.data_helper = DataHelperAgent(
                llm_manager=llm_manager,
                tool_dispatcher=tool_dispatcher,
                context=self.context
            )
        
        return self.data_helper
    
    async def generate_data_request(self, missing_fields: List[str],
                                   journey_summary: Dict,
                                   loop_type: str) -> Dict[str, Any]:
        """Generate intelligent data collection request
        
        Args:
            missing_fields: Fields needed for analysis
            journey_summary: User's journey context
            loop_type: Current loop type
            
        Returns:
            Contextual data request with instructions
        """
        
        # Determine request tone based on journey
        tone = self._determine_tone(journey_summary)
        
        # Prioritize fields
        prioritized = self._prioritize_fields(missing_fields, loop_type)
        
        # Generate collection instructions
        instructions = await self._generate_collection_instructions(
            prioritized, tone, journey_summary
        )
        
        # Create data request
        request = {
            'type': 'data_collection_request',
            'tone': tone,
            'priority_fields': prioritized[:3],  # Top 3 to avoid overwhelm
            'all_fields': prioritized,
            'instructions': instructions,
            'examples': self._generate_examples(prioritized[:3]),
            'integration_options': self._suggest_integrations(prioritized),
            'estimated_time': self._estimate_collection_time(prioritized[:3]),
            'why_needed': self._explain_importance(prioritized[:3], loop_type)
        }
        
        # Add journey-specific guidance
        if journey_summary.get('iterations', 0) == 0:
            request['getting_started'] = self._generate_starter_guide()
        
        if loop_type == 'refinement':
            request['refinement_focus'] = self._generate_refinement_guide(missing_fields)
        
        return request
    
    def _determine_tone(self, journey_summary: Dict) -> str:
        """Determine appropriate tone for data request"""
        
        iterations = journey_summary.get('iterations', 0)
        
        if iterations == 0:
            return 'educational'  # First time, needs guidance
        elif iterations <= 2:
            return 'supportive'  # Still learning
        else:
            return 'direct'  # Experienced user
    
    def _prioritize_fields(self, fields: List[str], loop_type: str) -> List[str]:
        """Prioritize fields based on impact and loop type"""
        
        priority_map = {
            # Cost optimization priorities
            'token_usage': DataRequestPriority.CRITICAL,
            'model_distribution': DataRequestPriority.CRITICAL,
            'monthly_spend': DataRequestPriority.CRITICAL,
            'api_calls': DataRequestPriority.HIGH,
            'request_patterns': DataRequestPriority.HIGH,
            
            # Latency priorities
            'response_times': DataRequestPriority.CRITICAL,
            'model_latency': DataRequestPriority.HIGH,
            'batch_sizes': DataRequestPriority.MEDIUM,
            
            # Quality priorities  
            'accuracy_metrics': DataRequestPriority.HIGH,
            'user_feedback': DataRequestPriority.MEDIUM,
            'error_rates': DataRequestPriority.HIGH
        }
        
        # Sort by priority
        def get_priority(field):
            return priority_map.get(field, DataRequestPriority.LOW).value
        
        return sorted(fields, key=lambda f: get_priority(f))
    
    async def _generate_collection_instructions(self, fields: List[str],
                                               tone: str,
                                               journey: Dict) -> Dict[str, Dict]:
        """Generate detailed collection instructions"""
        
        instructions = {}
        
        for field in fields[:5]:  # Limit to top 5
            if field == 'token_usage':
                instructions['token_usage'] = {
                    'what': 'Token consumption data showing input and output tokens',
                    'why': 'Identifies biggest cost drivers and optimization opportunities',
                    'how': {
                        'OpenAI': [
                            '1. Go to platform.openai.com/usage',
                            '2. Click "Export" → "Download CSV"',
                            '3. Select last 30 days',
                            '4. Upload the CSV file here'
                        ],
                        'Anthropic': [
                            '1. Visit console.anthropic.com/usage',
                            '2. Click "Export usage data"',
                            '3. Choose JSON format',
                            '4. Share the JSON here'
                        ],
                        'Manual': [
                            '1. Query your logs for "tokens"',
                            '2. Sum input_tokens and output_tokens by day',
                            '3. Group by model name',
                            '4. Provide as CSV or JSON'
                        ]
                    },
                    'format_example': {
                        'date': '2024-01-15',
                        'model': 'gpt-4',
                        'input_tokens': 150000,
                        'output_tokens': 50000
                    },
                    'quick_alternative': 'Just share your last invoice if you don\'t have detailed data'
                }
            
            elif field == 'response_times':
                instructions['response_times'] = {
                    'what': 'API response time measurements',
                    'why': 'Identifies latency bottlenecks for optimization',
                    'how': {
                        'CloudWatch': [
                            '1. Open CloudWatch Metrics',
                            '2. Search for your API Gateway or Lambda',
                            '3. Select "Duration" metric',
                            '4. Export last 7 days as CSV'
                        ],
                        'Application Logs': [
                            '1. Search logs for response times',
                            '2. Extract: timestamp, duration_ms, model',
                            '3. Calculate p50, p95, p99',
                            '4. Share the summary'
                        ],
                        'Quick Test': [
                            '1. Run: curl -w "%{time_total}" your-api-endpoint',
                            '2. Repeat 10 times',
                            '3. Share the times'
                        ]
                    },
                    'format_example': {
                        'endpoint': '/api/generate',
                        'p50_ms': 450,
                        'p95_ms': 1200,
                        'p99_ms': 2500
                    }
                }
            
            # Add more field-specific instructions...
        
        return instructions
    
    def _generate_examples(self, fields: List[str]) -> Dict[str, Any]:
        """Generate example data formats"""
        
        examples = {}
        
        for field in fields:
            if field == 'token_usage':
                examples['token_usage'] = {
                    'csv_format': """date,model,input_tokens,output_tokens,cost
2024-01-15,gpt-4,150000,50000,6.00
2024-01-16,gpt-3.5-turbo,500000,200000,0.90""",
                    'json_format': {
                        'usage': [
                            {
                                'date': '2024-01-15',
                                'model': 'gpt-4',
                                'tokens': {'input': 150000, 'output': 50000}
                            }
                        ]
                    }
                }
        
        return examples
    
    def _suggest_integrations(self, fields: List[str]) -> Dict[str, List[str]]:
        """Suggest integration options for automated collection"""
        
        integrations = {
            'apis': [],
            'scripts': [],
            'tools': []
        }
        
        if 'token_usage' in fields:
            integrations['apis'].append('OpenAI Usage API')
            integrations['scripts'].append('export_openai_usage.py')
        
        if 'response_times' in fields:
            integrations['tools'].append('DataDog APM')
            integrations['tools'].append('New Relic')
        
        return integrations
    
    def _estimate_collection_time(self, fields: List[str]) -> str:
        """Estimate time to collect data"""
        
        time_per_field = {
            'token_usage': 5,  # 5 minutes
            'monthly_spend': 2,  # 2 minutes
            'response_times': 10,  # 10 minutes
            'model_distribution': 15  # 15 minutes
        }
        
        total_minutes = sum(time_per_field.get(f, 5) for f in fields)
        
        if total_minutes <= 10:
            return f"About {total_minutes} minutes"
        elif total_minutes <= 30:
            return f"15-30 minutes"
        else:
            return "30-60 minutes (can be done in stages)"
    
    def _explain_importance(self, fields: List[str], loop_type: str) -> Dict[str, str]:
        """Explain why each field is important"""
        
        explanations = {}
        
        for field in fields:
            if field == 'token_usage':
                explanations['token_usage'] = (
                    "Token data reveals your biggest cost drivers. "
                    "We can typically reduce token usage by 30-40% "
                    "through caching and prompt optimization."
                )
            elif field == 'response_times':
                explanations['response_times'] = (
                    "Response time data shows performance bottlenecks. "
                    "We can often improve latency by 50% through "
                    "model selection and batching strategies."
                )
        
        return explanations
    
    def _generate_starter_guide(self) -> Dict[str, Any]:
        """Generate guide for first-time users"""
        
        return {
            'title': 'Getting Started with Data Collection',
            'steps': [
                {
                    'step': 1,
                    'action': 'Start with what you have',
                    'detail': 'Any invoice, usage report, or screenshot helps'
                },
                {
                    'step': 2,
                    'action': 'Check your AI provider dashboard',
                    'detail': 'Most providers have usage/billing sections'
                },
                {
                    'step': 3,
                    'action': 'Export or screenshot',
                    'detail': 'CSV is best, but any format works'
                }
            ],
            'no_data_option': {
                'message': 'No data yet? No problem!',
                'action': 'Tell us about your use case and we\'ll guide you'
            }
        }
    
    def _generate_refinement_guide(self, missing_fields: List[str]) -> Dict:
        """Generate guide for refinement requests"""
        
        return {
            'focus': 'Enhancing your analysis',
            'why': 'Additional data enables deeper optimization',
            'impact': f'Could improve recommendations by {len(missing_fields) * 10}%',
            'quick_wins': 'Start with the first field for immediate value'
        }
    
    async def trigger_data_helper_agent(self, missing_data: List[str],
                                       context_metadata: Dict) -> Dict:
        """Trigger DataHelperAgent for missing data collection
        
        Args:
            missing_data: List of missing fields
            context_metadata: Current context metadata
            
        Returns:
            Data helper response with collection guidance
        """
        
        data_helper = await self._get_data_helper()
        
        # Prepare state for data helper
        from netra_backend.app.agents.state import DeepAgentState
        state = DeepAgentState()
        state.user_request = context_metadata.get('user_request', 'Need help collecting data')
        state.context_tracking = {
            'missing_fields': missing_data,
            'current_loop': context_metadata.get('loop_type', 'data_discovery'),
            'iteration': context_metadata.get('iteration', 1)
        }
        
        # Execute data helper
        await data_helper.execute(state, self.context.run_id, stream_updates=True)
        
        # Extract result
        result = state.context_tracking.get('data_helper_result', {})
        
        return {
            'success': True,
            'data_request': result.get('data_request', {}),
            'instructions': result.get('user_instructions', ''),
            'structured_items': result.get('structured_items', []),
            'triggered_for': missing_data
        }
```

### 3. Integration with ReportingSubAgent

```python
# Add to ReportingSubAgent implementation

async def _check_for_checkpoint(self, context: UserExecutionContext) -> Optional[Dict]:
    """Check for and load checkpoint"""
    
    if not self._checkpoint_manager:
        return None
    
    checkpoint = await self._checkpoint_manager.load_latest_checkpoint()
    
    if checkpoint:
        # Restore context from checkpoint
        logger.info(f"Resuming from checkpoint: {checkpoint.checkpoint_id}")
        
        # Merge checkpoint data into context
        context.metadata.update(checkpoint.data_collected)
        
        # Set iteration number
        self._current_iteration = checkpoint.iteration
        
        # Load insights
        self._journey_context['previous_insights'] = checkpoint.insights_generated
        
        return {
            'checkpoint_id': checkpoint.checkpoint_id,
            'loop_type': checkpoint.loop_type,
            'progress': checkpoint.journey_progress
        }
    
    return None

async def _trigger_data_collection(self, missing_fields: List[str]) -> Dict:
    """Trigger data collection through DataHelper"""
    
    if not self._data_helper_coordinator:
        return {}
    
    # Get journey summary
    journey_summary = {}
    if self._checkpoint_manager:
        journey_summary = await self._checkpoint_manager.get_journey_summary()
    
    # Generate data request
    data_request = await self._data_helper_coordinator.generate_data_request(
        missing_fields=missing_fields,
        journey_summary=journey_summary,
        loop_type=self._current_loop_type.value
    )
    
    # Trigger DataHelperAgent if needed
    if len(missing_fields) > 5 or journey_summary.get('iterations', 0) == 0:
        # Complex request or first-timer - use DataHelperAgent
        helper_result = await self._data_helper_coordinator.trigger_data_helper_agent(
            missing_fields,
            self._user_context.metadata
        )
        data_request['helper_guidance'] = helper_result
    
    return data_request
```

## CRITICAL IMPLEMENTATION NOTES:

1. **Checkpoints persist for 7 days** - Allow users to return later
2. **Journey tracking** - Maintain context across all iterations
3. **Adaptive data requests** - Change based on user experience
4. **Never overwhelm** - Limit to 3 priority fields at a time
5. **Educational for beginners** - Detailed instructions for first-timers
6. **Direct for experienced** - Concise requests for returning users

## INTEGRATION REQUIREMENTS:

1. **Redis** - All checkpoints stored in Redis with TTL
2. **DataHelperAgent** - Triggered for complex data requests
3. **ReportingSubAgent** - Load/save checkpoints on execute
4. **UserExecutionContext** - Maintains user isolation

## VALIDATION CHECKLIST:

- [ ] Checkpoints save successfully
- [ ] Checkpoints restore on new session
- [ ] Journey history tracks correctly
- [ ] Data requests are contextual
- [ ] Tone adapts to user experience
- [ ] Instructions are clear and actionable
- [ ] Examples provided for each field
- [ ] Time estimates are realistic
- [ ] Integration with DataHelperAgent works
- [ ] No user data leaks between sessions

Remember: Users may take days to collect data. The system must remember their entire journey and pick up exactly where they left off, with full context preservation.