"""Example Message Processor Agent

Specialized agent for processing example messages with real-time updates
and comprehensive result generation for DEV MODE demonstrations.

Business Value: Showcases AI optimization capabilities to drive conversions
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.interfaces import AgentStateProtocol, BaseAgentProtocol
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.agent_result_types import TypedAgentResult
# WebSocket manager accessed via factory pattern for security

logger = central_logger.get_logger(__name__)


class ExampleMessageProcessor(BaseAgent):
    """Agent specialized for processing example messages with real-time feedback"""
    
    def __init__(self, llm_manager: Optional[LLMManager] = None):
        super().__init__(
            llm_manager=llm_manager,
            name="ExampleMessageProcessor",
            description="Processes example optimization messages with real-time updates"
        )
        self.ws_manager = None  # Lazy initialization to avoid import-time WebSocket manager creation
        self.processing_strategies = {
            'cost-optimization': self._process_cost_optimization,
            'latency-optimization': self._process_latency_optimization,
            'model-selection': self._process_model_selection,
            'scaling': self._process_scaling_analysis,
            'advanced': self._process_advanced_optimization
        }
    
    async def _get_websocket_manager(self, user_context=None):
        """Get WebSocket manager using factory pattern for security.
        
        Args:
            user_context: User execution context for WebSocket manager creation
            
        Returns:
            WebSocket manager instance or None if no context provided
        """
        if user_context:
            try:
                from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                return await create_websocket_manager(user_context)
            except Exception as e:
                logger.error(f"Failed to create WebSocket manager: {e}")
                return None
        else:
            logger.debug("WebSocket manager not created - no user context provided")
            return None
        
    async def execute(self, state: AgentStateProtocol, run_id: str, stream_updates: bool = False) -> TypedAgentResult:
        """Execute the example message processor with agent state interface."""
        try:
            # Extract message content from state
            user_request = getattr(state, 'user_request', '')
            user_id = getattr(state, 'user_id', 'default_user')
            
            # Create example message metadata (default for interface compliance)
            metadata = {
                'example_message_id': run_id,
                'category': 'general',
                'complexity': 'basic',
                'business_value': 'conversion',
                'estimated_time': '1-2 minutes'
            }
            
            # Process the message
            result = await self.process_example_message(user_id, user_request, metadata)
            
            return TypedAgentResult(
                success=True,
                result=result,
                error=None,
                metadata={'agent_name': self.name, 'run_id': run_id}
            )
            
        except Exception as e:
            logger.error(f"Example message processor execution failed: {e}")
            return TypedAgentResult(
                success=False,
                result=None,
                error=str(e),
                metadata={'agent_name': self.name, 'run_id': run_id}
            )
        
    async def process_example_message(
        self,
        user_id: str,
        message_content: str,
        message_metadata: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
        user_context=None
    ) -> Dict[str, Any]:
        """Main processing method for example messages"""
        
        self.user_id = user_id
        self.state = SubAgentLifecycle.RUNNING
        
        start_time = time.time()
        message_id = message_metadata.get('example_message_id', str(uuid4()))
        category = message_metadata.get('category', 'general')
        
        logger.info(f"Processing example message", {
            'user_id': user_id,
            'message_id': message_id,
            'category': category
        })
        
        try:
            # Send initial processing notification
            await self._send_update('agent_started', {
                'agent_name': self.name,
                'message': f'Starting {category} analysis...',
                'example_message_id': message_id
            }, user_context)
            
            # Select processing strategy based on category
            strategy = self.processing_strategies.get(
                category,
                self._process_general_optimization
            )
            
            # Execute processing strategy
            result = await strategy(
                message_content,
                message_metadata,
                message_id,
                progress_callback,
                user_context
            )
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            result['processing_time_ms'] = processing_time
            result['message_id'] = message_id
            
            # Send completion notification
            await self._send_update('agent_completed', {
                'agent_name': self.name,
                'example_message_id': message_id,
                'result': result,
                'processing_time_ms': processing_time
            }, user_context)
            
            self.state = SubAgentLifecycle.COMPLETED
            return result
            
        except Exception as e:
            logger.error(f"Error processing example message: {e}")
            
            # Send error notification
            await self._send_update('error', {
                'agent_name': self.name,
                'example_message_id': message_id,
                'error': str(e)
            }, user_context)
            
            self.state = SubAgentLifecycle.FAILED
            raise
            
    async def _process_cost_optimization(
        self,
        content: str,
        metadata: Dict[str, Any],
        message_id: str,
        callback: Optional[Callable] = None,
        user_context=None
    ) -> Dict[str, Any]:
        """Process cost optimization requests"""
        
        # Phase 1: Analysis
        # Note: user_context could be passed to all _send_update calls for consistency
        await self._send_update('tool_executing', {
            'tool_name': 'cost_analyzer',
            'message': 'Analyzing current cost structure and usage patterns...',
            'example_message_id': message_id
        }, user_context)
        await asyncio.sleep(0.8)  # Simulate processing time
        
        # Phase 2: Optimization Discovery
        await self._send_update('agent_thinking', {
            'message': 'Identifying cost reduction opportunities while maintaining quality...',
            'example_message_id': message_id
        })
        await asyncio.sleep(1.2)
        
        # Phase 3: Strategy Generation
        await self._send_update('partial_result', {
            'message': 'Found optimization opportunities with 20-30% potential savings',
            'example_message_id': message_id
        })
        await asyncio.sleep(0.6)
        
        # Generate detailed cost optimization analysis
        result = {
            'optimization_type': 'cost_optimization',
            'analysis': {
                'current_spending': {
                    'monthly_total': '$1,850',
                    'model_costs': '$1,320 (71%)',
                    'api_costs': '$380 (21%)',
                    'infrastructure': '$150 (8%)'
                },
                'optimization_opportunities': [
                    {
                        'strategy': 'Intelligent Model Selection',
                        'description': 'Use GPT-3.5-turbo for simpler tasks, GPT-4 for complex analysis',
                        'potential_savings': '$425/month (32%)',
                        'implementation_effort': 'Medium',
                        'quality_impact': 'Minimal (<5% difference for targeted use cases)'
                    },
                    {
                        'strategy': 'Prompt Optimization',
                        'description': 'Reduce token usage through better prompting and response formatting',
                        'potential_savings': '$180/month (14%)',
                        'implementation_effort': 'Low',
                        'quality_impact': 'None (improved clarity)'
                    },
                    {
                        'strategy': 'Caching & Deduplication',
                        'description': 'Cache similar requests and deduplicate common patterns',
                        'potential_savings': '$220/month (17%)',
                        'implementation_effort': 'Medium',
                        'quality_impact': 'Improved (faster responses)'
                    }
                ]
            },
            'implementation_roadmap': {
                'week_1': [
                    'Implement prompt optimization templates',
                    'Set up basic response caching'
                ],
                'week_2': [
                    'Deploy intelligent model routing',
                    'Configure cost monitoring alerts'
                ],
                'week_3': [
                    'Optimize caching strategy',
                    'Fine-tune model selection rules'
                ],
                'week_4': [
                    'Monitor performance and adjust',
                    'Document savings and quality metrics'
                ]
            },
            'expected_outcomes': {
                'monthly_savings': '$825',
                'savings_percentage': '45%',
                'payback_period': '2 weeks',
                'quality_maintenance': '98%+ of current quality levels'
            }
        }
        
        return result
        
    async def _process_latency_optimization(
        self,
        content: str,
        metadata: Dict[str, Any],
        message_id: str,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Process latency optimization requests"""
        
        await self._send_update('tool_executing', {
            'tool_name': 'latency_analyzer',
            'message': 'Measuring response times and identifying bottlenecks...',
            'example_message_id': message_id
        })
        await asyncio.sleep(1.0)
        
        await self._send_update('agent_thinking', {
            'message': 'Calculating optimization strategies for 3x improvement...',
            'example_message_id': message_id
        })
        await asyncio.sleep(1.5)
        
        await self._send_update('partial_result', {
            'message': 'Identified 4 key optimization vectors for significant improvement',
            'example_message_id': message_id
        })
        await asyncio.sleep(0.7)
        
        result = {
            'optimization_type': 'latency_optimization',
            'current_performance': {
                'average_latency': '1450ms',
                'p95_latency': '2800ms',
                'bottlenecks': [
                    'Model inference: 950ms (66%)',
                    'Network overhead: 280ms (19%)',
                    'Processing/formatting: 220ms (15%)'
                ]
            },
            'optimization_strategies': [
                {
                    'strategy': 'Response Streaming',
                    'description': 'Stream responses as they generate for perceived latency reduction',
                    'latency_improvement': '70% perceived reduction',
                    'implementation': 'Modify API calls to use streaming endpoints',
                    'cost_impact': 'Neutral'
                },
                {
                    'strategy': 'Model Optimization',
                    'description': 'Use Claude-3 Haiku for simple queries, full models for complex ones',
                    'latency_improvement': '60% for simple queries',
                    'implementation': 'Implement request classification',
                    'cost_impact': '-25% overall'
                },
                {
                    'strategy': 'Parallel Processing',
                    'description': 'Execute independent operations simultaneously',
                    'latency_improvement': '45% for multi-step operations',
                    'implementation': 'Refactor sequential calls to parallel',
                    'cost_impact': 'Neutral'
                },
                {
                    'strategy': 'Edge Caching',
                    'description': 'Deploy intelligent caching at edge locations',
                    'latency_improvement': '85% for cached responses',
                    'implementation': 'Set up CDN with smart caching rules',
                    'cost_impact': '+$50/month infrastructure'
                }
            ],
            'projected_results': {
                'new_average_latency': '420ms',
                'new_p95_latency': '680ms',
                'improvement_factor': '3.4x faster',
                'user_satisfaction_increase': '+40%'
            }
        }
        
        return result
        
    async def _process_model_selection(
        self,
        content: str,
        metadata: Dict[str, Any],
        message_id: str,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Process model selection requests"""
        
        await self._send_update('tool_executing', {
            'tool_name': 'model_benchmarker',
            'message': 'Benchmarking GPT-4o and Claude-3 Sonnet performance...',
            'example_message_id': message_id
        })
        await asyncio.sleep(1.1)
        
        await self._send_update('agent_thinking', {
            'message': 'Analyzing model compatibility with your specific use cases...',
            'example_message_id': message_id
        })
        await asyncio.sleep(0.9)
        
        result = {
            'optimization_type': 'model_selection',
            'model_comparison': {
                'gpt-4o': {
                    'overall_score': 92,
                    'strengths': [
                        'Superior reasoning capabilities',
                        'Excellent code generation',
                        'Strong mathematical problem solving'
                    ],
                    'performance_metrics': {
                        'accuracy': '94%',
                        'consistency': '91%',
                        'speed': '680ms avg',
                        'cost_per_1k_tokens': '$0.025'
                    },
                    'best_use_cases': [
                        'Complex analysis tasks',
                        'Technical documentation',
                        'Problem-solving workflows'
                    ]
                },
                LLMModel.GEMINI_2_5_FLASH.value: {
                    'overall_score': 89,
                    'strengths': [
                        'Excellent long-form content',
                        'Superior context understanding',
                        'Better instruction following'
                    ],
                    'performance_metrics': {
                        'accuracy': '91%',
                        'consistency': '95%',
                        'speed': '520ms avg',
                        'cost_per_1k_tokens': '$0.018'
                    },
                    'best_use_cases': [
                        'Content creation',
                        'Summarization tasks',
                        'Customer communication'
                    ]
                }
            },
            'recommendations': {
                'primary_strategy': 'Hybrid approach with intelligent routing',
                'routing_rules': {
                    'use_gpt4o_for': [
                        'Technical analysis (complexity score > 7)',
                        'Code-related queries',
                        'Mathematical calculations'
                    ],
                    'use_claude3_for': [
                        'Content generation',
                        'Simple Q&A (complexity score < 5)',
                        'Summarization tasks'
                    ]
                },
                'expected_impact': {
                    'cost_reduction': '18%',
                    'quality_improvement': '12%',
                    'latency_optimization': '23%'
                }
            }
        }
        
        return result
        
    async def _process_scaling_analysis(
        self,
        content: str,
        metadata: Dict[str, Any],
        message_id: str,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Process scaling analysis requests"""
        
        await self._send_update('tool_executing', {
            'tool_name': 'capacity_planner',
            'message': 'Modeling scaling impact and capacity requirements...',
            'example_message_id': message_id
        })
        await asyncio.sleep(1.3)
        
        await self._send_update('partial_result', {
            'message': 'Analyzing 50% usage increase impact on infrastructure...',
            'example_message_id': message_id
        })
        await asyncio.sleep(0.8)
        
        result = {
            'optimization_type': 'scaling_analysis',
            'current_metrics': {
                'monthly_requests': '150,000',
                'monthly_cost': '$3,200',
                'peak_concurrent_users': '450',
                'average_response_time': '850ms',
                'rate_limit_utilization': '72%'
            },
            'scaling_projections': {
                'with_50_percent_growth': {
                    'monthly_requests': '225,000',
                    'projected_cost_linear': '$4,800',
                    'projected_cost_optimized': '$3,840',
                    'peak_concurrent_users': '675',
                    'infrastructure_changes_needed': [
                        'Additional API key allocation',
                        'Load balancing implementation',
                        'Queue management for peak periods'
                    ]
                }
            },
            'optimization_strategies': [
                {
                    'strategy': 'Request Batching',
                    'description': 'Batch similar requests to reduce API calls',
                    'cost_savings': '15%',
                    'complexity': 'Medium'
                },
                {
                    'strategy': 'Smart Rate Limiting',
                    'description': 'Implement intelligent queuing and priority systems',
                    'performance_improvement': '35% during peak loads',
                    'complexity': 'High'
                },
                {
                    'strategy': 'Caching Layer Enhancement',
                    'description': 'Implement advanced caching with invalidation strategies',
                    'cost_savings': '25%',
                    'latency_improvement': '40%'
                }
            ],
            'implementation_plan': {
                'immediate_actions': [
                    'Implement basic request batching',
                    'Set up monitoring and alerting'
                ],
                'short_term': [
                    'Deploy load balancing',
                    'Enhance caching infrastructure'
                ],
                'long_term': [
                    'Implement predictive scaling',
                    'Optimize for cost efficiency'
                ]
            },
            'projected_outcomes': {
                'cost_efficiency': '20% better than linear scaling',
                'performance_maintained': '99.5% uptime',
                'headroom_created': 'Support for 100% growth beyond target'
            }
        }
        
        return result
        
    async def _process_advanced_optimization(
        self,
        content: str,
        metadata: Dict[str, Any],
        message_id: str,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Process advanced multi-dimensional optimization"""
        
        await self._send_update('tool_executing', {
            'tool_name': 'multi_optimizer',
            'message': 'Running multi-dimensional optimization analysis...',
            'example_message_id': message_id
        })
        await asyncio.sleep(1.5)
        
        await self._send_update('agent_thinking', {
            'message': 'Solving optimization constraints: cost -20%, latency 2x, scale +30%...',
            'example_message_id': message_id
        })
        await asyncio.sleep(2.0)
        
        await self._send_update('partial_result', {
            'message': 'Found optimal configuration exceeding all targets...',
            'example_message_id': message_id
        })
        await asyncio.sleep(0.8)
        
        result = {
            'optimization_type': 'advanced_multi_dimensional',
            'constraints_analysis': {
                'cost_reduction_target': '20%',
                'latency_improvement_target': '2x',
                'scaling_target': '30% usage increase'
            },
            'optimization_solution': {
                'achieved_cost_reduction': '24%',
                'achieved_latency_improvement': '2.3x',
                'achieved_scaling_capacity': '45% growth support'
            },
            'solution_components': [
                {
                    'component': 'Intelligent Model Tiering',
                    'impact': {
                        'cost': '-15%',
                        'latency': '1.4x improvement',
                        'scalability': 'High'
                    }
                },
                {
                    'component': 'Advanced Caching with ML Prediction',
                    'impact': {
                        'cost': '-8%',
                        'latency': '1.6x improvement',
                        'scalability': 'Very High'
                    }
                },
                {
                    'component': 'Async Processing Pipeline',
                    'impact': {
                        'cost': '-3%',
                        'latency': '1.2x improvement',
                        'scalability': 'Unlimited'
                    }
                },
                {
                    'component': 'Dynamic Resource Allocation',
                    'impact': {
                        'cost': '+2% infrastructure',
                        'latency': '1.1x improvement',
                        'scalability': 'Auto-scaling'
                    }
                }
            ],
            'implementation_timeline': {
                'phase_1_week_1': {
                    'tasks': ['Deploy model tiering', 'Implement basic caching'],
                    'expected_improvement': '50% of total gains'
                },
                'phase_2_week_2': {
                    'tasks': ['Advanced caching with ML', 'Async pipeline'],
                    'expected_improvement': '85% of total gains'
                },
                'phase_3_week_3': {
                    'tasks': ['Dynamic scaling', 'Fine-tuning'],
                    'expected_improvement': '100% of total gains'
                }
            },
            'business_impact': {
                'monthly_savings': '$2,100',
                'productivity_increase': '40%',
                'user_satisfaction_score': '+32%',
                'competitive_advantage': 'Significant'
            }
        }
        
        return result
        
    async def _process_general_optimization(
        self,
        content: str,
        metadata: Dict[str, Any],
        message_id: str,
        callback: Optional[Callable] = None,
        user_context=None
    ) -> Dict[str, Any]:
        """General optimization processing for uncategorized requests"""
        
        await self._send_update('agent_thinking', {
            'message': 'Analyzing optimization request and determining best approach...',
            'example_message_id': message_id
        }, user_context)
        await asyncio.sleep(1.0)
        
        result = {
            'optimization_type': 'general_analysis',
            'analysis': {
                'message': 'This request would be analyzed and routed to appropriate specialists',
                'suggested_categories': ['cost-optimization', 'latency-optimization'],
                'next_steps': [
                    'Classify request intent',
                    'Route to specialized agent',
                    'Generate detailed recommendations'
                ]
            },
            'demonstration_note': 'In production, this would trigger the full agent pipeline'
        }
        
        return result
        
    async def _send_update(self, update_type: str, content: Dict[str, Any], user_context=None) -> None:
        """Send real-time updates via WebSocket"""
        
        if not self.user_id:
            return
            
        message = {
            'type': update_type,
            'payload': {
                **content,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agent_name': self.name
            }
        }
        
        try:
            ws_manager = await self._get_websocket_manager(user_context)
            if ws_manager:
                await ws_manager.send_message_to_user(self.user_id, message)
            else:
                logger.debug(f"WebSocket update not sent - no manager available: {update_type}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket update: {e}")


class ExampleMessageSupervisor:
    """Supervisor for managing example message processing workflows"""
    
    def __init__(self, llm_manager: Optional[LLMManager] = None):
        self.llm_manager = llm_manager
        self.active_processors: Dict[str, ExampleMessageProcessor] = {}
        
    async def process_example_message(
        self,
        user_id: str,
        message_content: str,
        message_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Supervise example message processing"""
        
        message_id = message_metadata.get('example_message_id', str(uuid4()))
        
        try:
            # Create processor instance
            processor = ExampleMessageProcessor(self.llm_manager)
            self.active_processors[message_id] = processor
            
            # Process message
            result = await processor.process_example_message(
                user_id,
                message_content,
                message_metadata
            )
            
            return result
            
        finally:
            # Cleanup processor
            self.active_processors.pop(message_id, None)
            
    def get_active_processors(self) -> Dict[str, ExampleMessageProcessor]:
        """Get currently active processors"""
        return self.active_processors.copy()
        
    def get_processor_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        active_count = len(self.active_processors)
        
        # Categorize by processing stage
        stages = {}
        for processor in self.active_processors.values():
            stage = processor.state.value if processor.state else 'unknown'
            stages[stage] = stages.get(stage, 0) + 1
            
        return {
            'active_processors': active_count,
            'processing_stages': stages
        }


# Global supervisor instance
example_supervisor = ExampleMessageSupervisor()


def get_example_message_supervisor() -> ExampleMessageSupervisor:
    """Get the global example message supervisor"""
    return example_supervisor