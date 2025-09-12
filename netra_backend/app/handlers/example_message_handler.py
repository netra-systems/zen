"""Example Message Handler for DEV MODE

Handles example messages sent from the frontend, validates them, and routes them
to the appropriate agents for processing. Provides comprehensive error handling
and progress tracking.

Business Value: Demonstrates AI optimization capabilities to drive Free tier conversion
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from pydantic import BaseModel, Field, ValidationError

from netra_backend.app.agents.example_message_processor import (
    get_example_message_supervisor,
)
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.error_handling import (
    ErrorCategory,
    handle_example_message_error,
)
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import WebSocketMessage
# SECURITY FIX: Use factory pattern instead of singleton
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory

logger = central_logger.get_logger(__name__)


class ExampleMessageMetadata(BaseModel):
    """Metadata for example messages"""
    title: str
    category: str = Field(..., pattern=r'^(cost-optimization|latency-optimization|model-selection|scaling|advanced)$')
    complexity: str = Field(..., pattern=r'^(basic|intermediate|advanced)$')
    business_value: str = Field(..., pattern=r'^(conversion|retention|expansion)$', alias='businessValue')
    estimated_time: str = Field(..., alias='estimatedTime')


class ExampleMessageRequest(BaseModel):
    """Validated example message request"""
    content: str = Field(..., min_length=10, max_length=2000)
    example_message_id: str
    example_message_metadata: ExampleMessageMetadata
    user_id: str
    timestamp: int


class ExampleMessageResponse(BaseModel):
    """Response structure for example messages"""
    message_id: str
    status: str
    agent_used: Optional[str] = None
    processing_time_ms: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    business_insights: Optional[Dict[str, Any]] = None


class ExampleMessageHandler:
    """Handles example message processing workflow"""
    
    def __init__(self):
        # SECURITY FIX: Use factory pattern for per-user WebSocket isolation
        self.websocket_factory = WebSocketBridgeFactory()
        self.supervisor = get_example_message_supervisor()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        # Cache for user emitters (cleared on session end)
        self._user_emitters: Dict[str, Any] = {}
        
    async def _get_user_emitter(self, user_id: str, message_id: str):
        """Get or create per-user WebSocket emitter with complete isolation."""
        if user_id not in self._user_emitters:
            try:
                # Create isolated WebSocket emitter for this specific user
                thread_id = f"example_msg_{message_id}"
                connection_id = f"conn_{user_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
                
                emitter = await self.websocket_factory.create_user_emitter(
                    user_id=user_id,
                    thread_id=thread_id,
                    connection_id=connection_id
                )
                
                self._user_emitters[user_id] = emitter
                logger.debug(f"Created isolated WebSocket emitter for user {user_id}")
                
            except Exception as e:
                logger.warning(f"Failed to create WebSocket emitter for user {user_id}: {e}")
                # Create fallback emitter that logs instead of failing
                class FallbackEmitter:
                    async def send_message(self, message):
                        logger.info(f"WebSocket message for {user_id}: {message}")
                
                self._user_emitters[user_id] = FallbackEmitter()
        
        return self._user_emitters[user_id]
        
    async def handle_example_message(self, raw_message: Dict[str, Any]) -> ExampleMessageResponse:
        """Main handler for example messages"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate message structure
            validated_message = self._validate_message(raw_message)
            
            # Create session tracking
            session_id = str(uuid4())
            self.active_sessions[session_id] = {
                'message_id': validated_message.example_message_id,
                'user_id': validated_message.user_id,
                'start_time': start_time,
                'status': 'processing',
                'metadata': validated_message.example_message_metadata.model_dump()
            }
            
            # Process through supervisor with integrated error handling
            agent_result = await self.supervisor.process_example_message(
                validated_message.user_id,
                validated_message.content,
                validated_message.example_message_metadata.model_dump()
            )
            
            # Calculate processing time
            end_time = datetime.now(timezone.utc)
            processing_time = int((end_time - start_time).total_seconds() * 1000)
            
            # Update session
            self.active_sessions[session_id]['status'] = 'completed'
            self.active_sessions[session_id]['end_time'] = end_time
            
            # Send completion notification
            await self._send_completion_notification(
                validated_message.user_id,
                validated_message.example_message_id,
                agent_result,
                processing_time
            )
            
            # Generate business insights
            business_insights = self._generate_business_insights(
                validated_message.example_message_metadata,
                agent_result,
                processing_time
            )
            
            return ExampleMessageResponse(
                message_id=validated_message.example_message_id,
                status='completed',
                agent_used=agent_result.get('agent_name'),
                processing_time_ms=processing_time,
                result=agent_result,
                business_insights=business_insights
            )
            
        except ValidationError as e:
            # Handle validation errors through error handling system
            error_context = ErrorContext(
                trace_id=ErrorContext.generate_trace_id(),
                operation='validation',
                user_id=raw_message.get('user_id'),
                correlation_id=raw_message.get('example_message_id'),
                details={'category': raw_message.get('example_message_metadata', {}).get('category'), 'processing_stage': 'validation'},
                component='ExampleMessageHandler'
            )
            error_info = await handle_example_message_error(e, error_context)
            
            return ExampleMessageResponse(
                message_id=raw_message.get('example_message_id', 'unknown'),
                status='error',
                error=error_info.user_message
            )
            
        except Exception as e:
            # Handle general errors through error handling system
            error_context = ErrorContext(
                trace_id=ErrorContext.generate_trace_id(),
                operation='processing',
                user_id=raw_message.get('user_id'),
                correlation_id=raw_message.get('example_message_id'),
                details={'category': raw_message.get('example_message_metadata', {}).get('category'), 'processing_stage': 'processing'},
                component='ExampleMessageHandler'
            )
            error_info = await handle_example_message_error(e, error_context)
            
            return ExampleMessageResponse(
                message_id=raw_message.get('example_message_id', 'unknown'),
                status='error',
                error=error_info.user_message
            )
            
        finally:
            # Cleanup session and user emitter
            if 'session_id' in locals():
                self.active_sessions.pop(session_id, None)
            
            # SECURITY FIX: Clean up user emitter to prevent memory leaks and isolation issues
            user_id = raw_message.get('user_id')
            if user_id and user_id in self._user_emitters:
                try:
                    emitter = self._user_emitters.pop(user_id)
                    if hasattr(emitter, 'cleanup'):
                        await emitter.cleanup()
                    logger.debug(f"Cleaned up WebSocket emitter for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup WebSocket emitter for user {user_id}: {e}")

    def _validate_message(self, raw_message: Dict[str, Any]) -> ExampleMessageRequest:
        """Validate and parse example message request"""
        try:
            return ExampleMessageRequest(**raw_message)
        except ValidationError as e:
            logger.error(f"Message validation failed: {e}")
            raise

    async def _route_to_agent(self, message: ExampleMessageRequest, session_id: str) -> Dict[str, Any]:
        """Route message to appropriate agent based on category and complexity"""
        
        category = message.example_message_metadata.category
        complexity = message.example_message_metadata.complexity
        
        logger.info(f"Routing message to agent", {
            'category': category,
            'complexity': complexity,
            'message_id': message.example_message_id
        })
        
        # Send initial processing notification
        await self._send_processing_notification(
            message.user_id,
            message.example_message_id,
            category,
            complexity
        )
        
        try:
            # Route based on category
            if category == 'cost-optimization':
                return await self._process_cost_optimization(message, session_id)
            elif category == 'latency-optimization':
                return await self._process_latency_optimization(message, session_id)
            elif category == 'model-selection':
                return await self._process_model_selection(message, session_id)
            elif category == 'scaling':
                return await self._process_scaling_analysis(message, session_id)
            elif category == 'advanced':
                return await self._process_advanced_optimization(message, session_id)
            else:
                # Fallback to triage agent
                return await self._process_with_triage_agent(message, session_id)
                
        except Exception as e:
            logger.error(f"Agent routing failed: {e}")
            # Fallback to basic processing
            return await self._process_fallback(message, session_id)

    async def _process_cost_optimization(self, message: ExampleMessageRequest, session_id: str) -> Dict[str, Any]:
        """Process cost optimization example messages"""
        
        # Send agent started notification
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'agent_started',
            {
                'agent_name': 'Cost Optimization Agent',
                'message': 'Analyzing cost optimization requirements...'
            }
        )
        
        # Simulate agent processing with real-looking updates
        await asyncio.sleep(0.5)
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'tool_executing',
            {
                'tool_name': 'cost_analyzer',
                'message': 'Analyzing current cost patterns and usage metrics'
            }
        )
        
        await asyncio.sleep(1.0)
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'agent_thinking',
            {
                'message': 'Identifying cost reduction opportunities while maintaining quality'
            }
        )
        
        await asyncio.sleep(0.8)
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'partial_result',
            {
                'message': 'Found 3 optimization opportunities with potential 25% cost reduction'
            }
        )
        
        # Generate cost optimization results
        result = {
            'agent_name': 'Cost Optimization Agent',
            'optimization_type': 'cost_reduction',
            'recommendations': [
                {
                    'feature': 'Feature X',
                    'current_cost': '$450/month',
                    'optimized_cost': '$315/month',
                    'savings': '30%',
                    'method': 'Model switching: GPT-4  ->  GPT-3.5-turbo for non-critical requests',
                    'latency_impact': '+50ms (within acceptable 500ms limit)'
                },
                {
                    'feature': 'Feature Y',
                    'current_cost': '$280/month',
                    'optimized_cost': '$245/month',
                    'savings': '12.5%',
                    'method': 'Prompt optimization and caching',
                    'latency_impact': '-20ms (improved to 180ms)'
                }
            ],
            'total_savings': {
                'monthly': '$170',
                'annual': '$2040',
                'percentage': '23%'
            },
            'implementation_steps': [
                'Implement request classification for Feature X',
                'Deploy prompt optimization for Feature Y',
                'Set up cost monitoring alerts',
                'Monitor quality metrics for 1 week'
            ]
        }
        
        return result

    async def _process_latency_optimization(self, message: ExampleMessageRequest, session_id: str) -> Dict[str, Any]:
        """Process latency optimization example messages"""
        
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'agent_started',
            {
                'agent_name': 'Latency Optimization Agent',
                'message': 'Analyzing latency bottlenecks and optimization opportunities...'
            }
        )
        
        await asyncio.sleep(0.7)
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'tool_executing',
            {
                'tool_name': 'latency_analyzer',
                'message': 'Measuring current response times and identifying bottlenecks'
            }
        )
        
        await asyncio.sleep(1.2)
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'agent_thinking',
            {
                'message': 'Calculating optimization strategies for 3x latency improvement'
            }
        )
        
        result = {
            'agent_name': 'Latency Optimization Agent',
            'optimization_type': 'latency_reduction',
            'current_metrics': {
                'average_latency': '1200ms',
                'p95_latency': '2100ms',
                'bottlenecks': ['Model inference: 800ms', 'Network: 250ms', 'Processing: 150ms']
            },
            'optimized_metrics': {
                'target_latency': '400ms',
                'improvement': '3x faster',
                'methods': [
                    'Streaming responses: -60% perceived latency',
                    'Model optimization: Switch to Claude-3 Haiku for simple queries',
                    'Caching layer: 90% cache hit rate for common patterns',
                    'Parallel processing: Execute multiple tool calls simultaneously'
                ]
            },
            'implementation_plan': {
                'phase_1': 'Implement streaming (Week 1)',
                'phase_2': 'Deploy intelligent model routing (Week 2)',
                'phase_3': 'Optimize caching strategy (Week 3)',
                'expected_results': '3.2x latency improvement with budget-neutral cost impact'
            }
        }
        
        return result

    async def _process_model_selection(self, message: ExampleMessageRequest, session_id: str) -> Dict[str, Any]:
        """Process model selection example messages"""
        
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'agent_started',
            {
                'agent_name': 'Model Selection Agent',
                'message': 'Analyzing model compatibility and performance for your use case...'
            }
        )
        
        # Simulate model analysis
        await asyncio.sleep(0.6)
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'tool_executing',
            {
                'tool_name': 'model_benchmarker',
                'message': 'Benchmarking GPT-4o and Claude-3 Sonnet against current setup'
            }
        )
        
        result = {
            'agent_name': 'Model Selection Agent',
            'optimization_type': 'model_optimization',
            'model_analysis': {
                'gpt-4o': {
                    'performance_score': 92,
                    'cost_efficiency': 85,
                    'latency': '650ms average',
                    'best_for': ['Complex reasoning', 'Code generation', 'Analysis tasks'],
                    'cost_impact': '+15% vs current',
                    'quality_improvement': '+25%'
                },
                LLMModel.GEMINI_2_5_FLASH.value: {
                    'performance_score': 89,
                    'cost_efficiency': 95,
                    'latency': '580ms average',
                    'best_for': ['Long-form content', 'Summarization', 'Creative tasks'],
                    'cost_impact': '-8% vs current',
                    'quality_improvement': '+18%'
                }
            },
            'recommendations': {
                'primary_model': 'GPT-4o for 70% of requests',
                'secondary_model': 'Claude-3 Sonnet for 30% of requests',
                'routing_logic': 'Based on request type classification',
                'expected_outcome': '22% quality improvement, 4% cost reduction'
            }
        }
        
        return result

    async def _process_scaling_analysis(self, message: ExampleMessageRequest, session_id: str) -> Dict[str, Any]:
        """Process scaling analysis example messages"""
        
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'agent_started',
            {
                'agent_name': 'Scaling Analysis Agent',
                'message': 'Analyzing scaling impact and capacity planning...'
            }
        )
        
        await asyncio.sleep(1.0)
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'tool_executing',
            {
                'tool_name': 'capacity_planner',
                'message': 'Modeling 50% usage increase impact on costs and rate limits'
            }
        )
        
        result = {
            'agent_name': 'Scaling Analysis Agent',
            'optimization_type': 'scaling_analysis',
            'current_usage': {
                'monthly_requests': '125,000',
                'monthly_cost': '$2,800',
                'average_tokens_per_request': '450',
                'rate_limit_utilization': '65%'
            },
            'projected_usage': {
                'monthly_requests': '187,500 (+50%)',
                'projected_cost': '$4,200 (+50%)',
                'rate_limit_impact': 'Will exceed limits during peak hours'
            },
            'optimization_plan': {
                'cost_optimization': [
                    'Implement request batching: -15% cost',
                    'Smart caching: -20% redundant requests',
                    'Model tiering: -12% average cost per request'
                ],
                'capacity_management': [
                    'Upgrade to higher rate limits: $150/month',
                    'Implement request queuing for peak periods',
                    'Load balancing across multiple API keys'
                ],
                'final_projections': {
                    'optimized_monthly_cost': '$3,150 (25% savings vs linear scaling)',
                    'performance_maintained': 'Yes, with 99.8% availability',
                    'implementation_timeline': '2-3 weeks'
                }
            }
        }
        
        return result

    async def _process_advanced_optimization(self, message: ExampleMessageRequest, session_id: str) -> Dict[str, Any]:
        """Process advanced multi-dimensional optimization"""
        
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'agent_started',
            {
                'agent_name': 'Advanced Optimization Agent',
                'message': 'Performing multi-dimensional optimization analysis...'
            }
        )
        
        # Simulate complex processing
        await asyncio.sleep(0.8)
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'tool_executing',
            {
                'tool_name': 'optimization_engine',
                'message': 'Solving for 20% cost reduction + 2x latency improvement + 30% usage growth'
            }
        )
        
        await asyncio.sleep(1.5)
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'agent_thinking',
            {
                'message': 'Evaluating trade-offs and generating optimal configuration...'
            }
        )
        
        result = {
            'agent_name': 'Advanced Optimization Agent',
            'optimization_type': 'multi_dimensional',
            'optimization_results': {
                'cost_reduction': {
                    'target': '20%',
                    'achieved': '23%',
                    'methods': ['Model tiering', 'Prompt optimization', 'Caching', 'Batching']
                },
                'latency_improvement': {
                    'target': '2x faster',
                    'achieved': '2.1x faster',
                    'methods': ['Streaming', 'Parallel processing', 'Edge deployment']
                },
                'scaling_capacity': {
                    'target': '+30% usage',
                    'supported': '+45% usage',
                    'headroom': 'Additional 15% for future growth'
                }
            },
            'implementation_roadmap': {
                'week_1': 'Deploy streaming and basic caching',
                'week_2': 'Implement model tiering and optimization',
                'week_3': 'Scale infrastructure and monitoring',
                'week_4': 'Fine-tune and validate performance'
            },
            'success_metrics': {
                'monthly_savings': '$2,240',
                'latency_p95': '420ms (was 920ms)',
                'capacity_headroom': '45%',
                'roi_timeline': '2.1 months to break even'
            }
        }
        
        return result

    async def _process_with_triage_agent(self, message: ExampleMessageRequest, session_id: str) -> Dict[str, Any]:
        """Fallback processing with triage agent"""
        
        await self._send_agent_update(
            message.user_id,
            message.example_message_id,
            'agent_started',
            {
                'agent_name': 'Triage Agent',
                'message': 'Analyzing request and determining best approach...'
            }
        )
        
        # Basic triage processing
        result = {
            'agent_name': 'Triage Agent',
            'optimization_type': 'general_analysis',
            'analysis': 'Request processed by triage agent - would route to specialized agents in production',
            'next_steps': ['Classify request type', 'Route to appropriate specialist', 'Generate detailed recommendations']
        }
        
        return result

    async def _process_fallback(self, message: ExampleMessageRequest, session_id: str) -> Dict[str, Any]:
        """Fallback processing when agents fail"""
        
        return {
            'agent_name': 'Fallback Handler',
            'optimization_type': 'fallback',
            'message': 'Request processed successfully with fallback handler',
            'note': 'This would be handled by the full agent system in production'
        }

    async def _send_agent_update(
        self, 
        user_id: str, 
        message_id: str, 
        update_type: str, 
        content: Dict[str, Any]
    ) -> None:
        """Send agent update via WebSocket"""
        
        update_message = {
            'type': update_type,
            'payload': {
                **content,
                'example_message_id': message_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        
        # SECURITY FIX: Use isolated per-user emitter
        emitter = await self._get_user_emitter(user_id, message_id)
        await emitter.send_message(update_message)

    async def _send_processing_notification(
        self, 
        user_id: str, 
        message_id: str, 
        category: str, 
        complexity: str
    ) -> None:
        """Send initial processing notification"""
        
        await self._send_agent_update(
            user_id,
            message_id,
            'agent_started',
            {
                'message': f'Processing {category} request with {complexity} complexity...',
                'category': category,
                'complexity': complexity
            }
        )

    async def _send_completion_notification(
        self, 
        user_id: str, 
        message_id: str, 
        result: Dict[str, Any], 
        processing_time: int
    ) -> None:
        """Send completion notification"""
        
        completion_message = {
            'type': 'agent_completed',
            'payload': {
                'example_message_id': message_id,
                'result': result,
                'processing_time_ms': processing_time,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        
        # SECURITY FIX: Use isolated per-user emitter  
        emitter = await self._get_user_emitter(user_id, message_id)
        await emitter.send_message(completion_message)

    async def _send_error_notification(
        self, 
        user_id: Optional[str], 
        message_id: Optional[str], 
        error: str
    ) -> None:
        """Send error notification"""
        
        if not user_id:
            return
            
        error_message = {
            'type': 'error',
            'payload': {
                'example_message_id': message_id,
                'error': error,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        
        # SECURITY FIX: Use isolated per-user emitter
        emitter = await self._get_user_emitter(user_id, message_id or "error") 
        await emitter.send_message(error_message)

    def _generate_business_insights(
        self, 
        metadata: ExampleMessageMetadata, 
        result: Dict[str, Any], 
        processing_time: int
    ) -> Dict[str, Any]:
        """Generate business insights for tracking and optimization"""
        
        # Map business value to concrete metrics
        value_mapping = {
            'conversion': {
                'metric': 'free_to_paid_likelihood',
                'score': 0.85 if processing_time < 2000 else 0.65,
                'message': 'Strong demonstration of value for Free tier users'
            },
            'retention': {
                'metric': 'user_satisfaction',
                'score': 0.90 if processing_time < 3000 else 0.70,
                'message': 'Enhanced user experience for existing customers'
            },
            'expansion': {
                'metric': 'upgrade_potential',
                'score': 0.80 if processing_time < 4000 else 0.60,
                'message': 'Advanced features showcase for tier upgrades'
            }
        }
        
        business_value = metadata.business_value
        insights = value_mapping.get(business_value, value_mapping['conversion'])
        
        return {
            'business_value_type': business_value,
            'performance_score': insights['score'],
            'processing_efficiency': 'excellent' if processing_time < 2000 else 'good' if processing_time < 5000 else 'needs_improvement',
            'user_engagement_impact': insights['message'],
            'revenue_impact_category': metadata.category,
            'complexity_handled': metadata.complexity
        }

    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get current active processing sessions"""
        return self.active_sessions.copy()

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        total_sessions = len(self.active_sessions)
        processing_sessions = len([s for s in self.active_sessions.values() if s['status'] == 'processing'])
        
        return {
            'total_active_sessions': total_sessions,
            'processing_sessions': processing_sessions,
            'avg_processing_time': self._calculate_avg_processing_time()
        }

    def _calculate_avg_processing_time(self) -> Optional[float]:
        """Calculate average processing time for completed sessions"""
        completed_sessions = [
            s for s in self.active_sessions.values() 
            if s['status'] == 'completed' and 'end_time' in s
        ]
        
        if not completed_sessions:
            return None
            
        total_time = sum(
            (s['end_time'] - s['start_time']).total_seconds() 
            for s in completed_sessions
        )
        
        return total_time / len(completed_sessions)


# Global handler instance
example_message_handler = ExampleMessageHandler()


async def handle_example_message(raw_message: Dict[str, Any]) -> ExampleMessageResponse:
    """Public interface for handling example messages"""
    return await example_message_handler.handle_example_message(raw_message)


def get_example_message_handler() -> ExampleMessageHandler:
    """Get the global example message handler instance"""
    return example_message_handler