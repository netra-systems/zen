"""Critical WebSocket Events Comprehensive Unit Tests

MISSION-CRITICAL TEST SUITE: Complete validation of critical WebSocket events for agent golden path.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Chat Functionality Reliability (90% of platform value)
- Value Impact: WebSocket events = Real-time chat experience = $500K+ ARR protection
- Strategic Impact: Missing WebSocket events destroy user experience and business value delivery

COVERAGE TARGET: 20 unit tests covering all 5 critical WebSocket events:
- agent_started event validation (4 tests)
- agent_thinking event validation (4 tests)
- tool_executing event validation (4 tests)
- tool_completed event validation (4 tests)
- agent_completed event validation (4 tests)

CRITICAL: Uses REAL services approach with minimal mocks per CLAUDE.md standards.
All 5 events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) MUST be tested.
"""

import asyncio
import pytest
import time
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
import threading

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import core WebSocket event components
from netra_backend.app.websocket_core.types import (
    MessageType, WebSocketMessage, ServerMessage, ErrorMessage,
    create_standard_message, create_error_message, create_server_message,
    normalize_message_type
)
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor
from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as UnifiedEventEmitter

# Import agent WebSocket integration components
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# Import WebSocket notification components
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.websocket_tool_enhancement import WebSocketToolEnhancer


@dataclass
class WebSocketEventTestScenario:
    """Test scenario for WebSocket event validation"""
    scenario_name: str
    event_sequence: List[str]
    timing_requirements: Dict[str, int]
    validation_rules: List[str]
    delivery_guarantees: Dict[str, Any]
    performance_metrics: Dict[str, int]


class CriticalWebSocketEventsComprehensiveTests(SSotAsyncTestCase):
    """Comprehensive unit tests for critical WebSocket events in agent golden path"""

    def setup_method(self, method):
        """Set up test environment for each test method"""
        super().setup_method(method)
        
        # Create test IDs
        self.user_id = str(uuid.uuid4())
        id_manager = UnifiedIDManager()
        self.execution_id = id_manager.generate_id(IDType.EXECUTION)
        self.connection_id = str(uuid.uuid4())
        
        # Create mock user execution context
        self.user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id=str(uuid.uuid4()),
            run_id=self.execution_id,
            websocket_client_id=self.connection_id,
            agent_context={"test_case": method.__name__, "websocket_events_test": True}
        )
        
        # Initialize WebSocket event components with mocked externals
        self.mock_llm_manager = AsyncMock()
        self.mock_redis_manager = AsyncMock()
        
        # Create real internal WebSocket components (following SSOT patterns)
        self.websocket_manager = AsyncMock()  # WebSocket manager needs to be mocked for unit tests
        self.event_monitor = ChatEventMonitor()
        self.event_validator = UnifiedEventValidator()
        self.unified_emitter = UnifiedEventEmitter()
        
        # Track emitted events for validation
        self.emitted_events = []
        self.event_timestamps = {}
        
        # Define the 5 critical WebSocket events that MUST be tested
        self.critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Define comprehensive test scenarios
        self.websocket_scenarios = [
            WebSocketEventTestScenario(
                scenario_name="simple_agent_execution_events",
                event_sequence=["agent_started", "agent_thinking", "agent_completed"],
                timing_requirements={"max_event_delay_ms": 100, "sequence_timeout_ms": 5000},
                validation_rules=["event_order", "event_content", "event_timing"],
                delivery_guarantees={"at_least_once": True, "ordered_delivery": True},
                performance_metrics={"event_emission_time_ms": 10, "validation_time_ms": 20}
            ),
            WebSocketEventTestScenario(
                scenario_name="tool_execution_events",
                event_sequence=["agent_started", "tool_executing", "tool_completed", "agent_completed"],
                timing_requirements={"max_event_delay_ms": 100, "sequence_timeout_ms": 10000},
                validation_rules=["event_order", "event_content", "event_timing", "tool_correlation"],
                delivery_guarantees={"at_least_once": True, "ordered_delivery": True},
                performance_metrics={"event_emission_time_ms": 15, "validation_time_ms": 25}
            ),
            WebSocketEventTestScenario(
                scenario_name="complete_agent_lifecycle_events",
                event_sequence=["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
                timing_requirements={"max_event_delay_ms": 150, "sequence_timeout_ms": 15000},
                validation_rules=["event_order", "event_content", "event_timing", "tool_correlation", "lifecycle_completeness"],
                delivery_guarantees={"at_least_once": True, "ordered_delivery": True, "guaranteed_completion": True},
                performance_metrics={"event_emission_time_ms": 20, "validation_time_ms": 30}
            )
        ]

    async def test_agent_started_event_validation_basic(self):
        """Test basic agent_started event validation and emission"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            # Initialize event monitoring
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Create agent_started event
            agent_started_event = {
                "event_type": "agent_started",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_info": {
                    "agent_type": "SupervisorAgent",
                    "agent_id": str(uuid.uuid4()),
                    "capabilities": ["planning", "tool_execution", "reasoning"]
                },
                "metadata": {
                    "session_start": True,
                    "user_query": "Help me optimize my AI infrastructure"
                }
            }
            
            # Emit agent_started event
            start_time = time.time()
            
            emission_result = await self.unified_emitter.emit_agent_started(
                agent_started_event, self.user_context
            )
            
            end_time = time.time()
            emission_time_ms = (end_time - start_time) * 1000
            
            # Validate agent_started event emission
            assert emission_result is not None
            assert emission_result.event_emitted is True
            assert emission_result.event_type == "agent_started"
            assert emission_result.delivery_confirmed is True
            
            # Validate event content
            assert emission_result.event_data["event_type"] == "agent_started"
            assert emission_result.event_data["user_id"] == self.user_id
            assert emission_result.event_data["execution_id"] == self.execution_id
            assert "agent_info" in emission_result.event_data
            
            # Validate performance
            assert emission_time_ms < 50  # Should emit quickly
            
            # Validate event tracking
            self.emitted_events.append(emission_result)
            self.event_timestamps["agent_started"] = emission_result.timestamp

    async def test_agent_started_event_validation_comprehensive(self):
        """Test comprehensive agent_started event validation with full metadata"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Create comprehensive agent_started event
            comprehensive_agent_started = {
                "event_type": "agent_started",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_info": {
                    "agent_type": "SupervisorAgent",
                    "agent_id": str(uuid.uuid4()),
                    "agent_version": "2.1.0",
                    "capabilities": ["planning", "tool_execution", "reasoning", "multi_step_workflow"],
                    "configuration": {
                        "max_iterations": 10,
                        "timeout_seconds": 300,
                        "tool_access_level": "full"
                    }
                },
                "execution_context": {
                    "user_query": "Analyze and optimize my AI infrastructure for cost and performance",
                    "context_type": "optimization_request",
                    "priority": "high",
                    "estimated_complexity": "high",
                    "tools_required": ["data_analyzer", "cost_calculator", "performance_optimizer"]
                },
                "metadata": {
                    "session_start": True,
                    "session_id": str(uuid.uuid4()),
                    "user_tier": "enterprise",
                    "feature_flags": ["advanced_optimization", "real_time_monitoring"]
                }
            }
            
            # Validate comprehensive event structure
            validation_result = await self.event_validator.validate_agent_started_event(
                comprehensive_agent_started, self.user_context
            )
            
            assert validation_result is not None
            assert validation_result.is_valid is True
            assert validation_result.validation_errors == []
            assert validation_result.required_fields_present is True
            
            # Emit and verify comprehensive event
            emission_result = await self.unified_emitter.emit_agent_started(
                comprehensive_agent_started, self.user_context
            )
            
            assert emission_result.event_emitted is True
            assert emission_result.comprehensive_data_included is True
            assert "execution_context" in emission_result.event_data
            assert "configuration" in emission_result.event_data["agent_info"]

    async def test_agent_thinking_event_validation_basic(self):
        """Test basic agent_thinking event validation and emission"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Create agent_thinking event
            agent_thinking_event = {
                "event_type": "agent_thinking",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "thinking_content": {
                    "current_step": "Analyzing user query for optimization requirements",
                    "reasoning": "Need to understand current infrastructure and identify optimization opportunities",
                    "progress": 25,
                    "estimated_remaining_time": 180
                },
                "metadata": {
                    "thinking_stage": "analysis",
                    "step_number": 1,
                    "total_steps": 4
                }
            }
            
            # Emit agent_thinking event
            start_time = time.time()
            
            emission_result = await self.unified_emitter.emit_agent_thinking(
                agent_thinking_event, self.user_context
            )
            
            end_time = time.time()
            emission_time_ms = (end_time - start_time) * 1000
            
            # Validate agent_thinking event emission
            assert emission_result is not None
            assert emission_result.event_emitted is True
            assert emission_result.event_type == "agent_thinking"
            assert emission_result.delivery_confirmed is True
            
            # Validate thinking content
            assert "thinking_content" in emission_result.event_data
            assert emission_result.event_data["thinking_content"]["current_step"] is not None
            assert emission_result.event_data["thinking_content"]["progress"] == 25
            
            # Validate performance
            assert emission_time_ms < 30
            
            # Track event
            self.emitted_events.append(emission_result)
            self.event_timestamps["agent_thinking"] = emission_result.timestamp

    async def test_agent_thinking_event_validation_progressive(self):
        """Test progressive agent_thinking events with multiple steps"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Create sequence of thinking events showing progression
            thinking_steps = [
                {
                    "step": 1,
                    "content": "Analyzing current AI infrastructure setup",
                    "progress": 20,
                    "stage": "analysis"
                },
                {
                    "step": 2,
                    "content": "Identifying cost optimization opportunities",
                    "progress": 40,
                    "stage": "optimization_planning"
                },
                {
                    "step": 3,
                    "content": "Evaluating performance improvement strategies",
                    "progress": 60,
                    "stage": "performance_analysis"
                },
                {
                    "step": 4,
                    "content": "Formulating comprehensive optimization plan",
                    "progress": 80,
                    "stage": "plan_formulation"
                }
            ]
            
            progressive_emissions = []
            
            for step_data in thinking_steps:
                thinking_event = {
                    "event_type": "agent_thinking",
                    "user_id": self.user_id,
                    "execution_id": self.execution_id,
                    "connection_id": self.connection_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "thinking_content": {
                        "current_step": step_data["content"],
                        "reasoning": f"Step {step_data['step']} reasoning for {step_data['stage']}",
                        "progress": step_data["progress"],
                        "estimated_remaining_time": 200 - (step_data["progress"] * 2)
                    },
                    "metadata": {
                        "thinking_stage": step_data["stage"],
                        "step_number": step_data["step"],
                        "total_steps": 4
                    }
                }
                
                emission_result = await self.unified_emitter.emit_agent_thinking(
                    thinking_event, self.user_context
                )
                
                assert emission_result.event_emitted is True
                assert emission_result.event_data["thinking_content"]["progress"] == step_data["progress"]
                
                progressive_emissions.append(emission_result)
                
                # Small delay between thinking steps
                await asyncio.sleep(0.01)
            
            # Validate progression
            for i in range(1, len(progressive_emissions)):
                current = progressive_emissions[i]
                previous = progressive_emissions[i-1]
                
                current_progress = current.event_data["thinking_content"]["progress"]
                previous_progress = previous.event_data["thinking_content"]["progress"]
                
                assert current_progress > previous_progress

    async def test_tool_executing_event_validation_basic(self):
        """Test basic tool_executing event validation and emission"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Create tool_executing event
            tool_executing_event = {
                "event_type": "tool_executing",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool_info": {
                    "tool_name": "data_analyzer",
                    "tool_id": str(uuid.uuid4()),
                    "tool_version": "1.3.0",
                    "operation": "analyze_infrastructure_costs"
                },
                "execution_details": {
                    "input_parameters": {
                        "data_source": "infrastructure_metrics",
                        "time_range": "last_30_days",
                        "analysis_type": "cost_optimization"
                    },
                    "estimated_duration": 45,
                    "progress_tracking": True
                },
                "metadata": {
                    "execution_step": "tool_execution",
                    "tool_category": "data_analysis"
                }
            }
            
            # Emit tool_executing event
            start_time = time.time()
            
            emission_result = await self.unified_emitter.emit_tool_executing(
                tool_executing_event, self.user_context
            )
            
            end_time = time.time()
            emission_time_ms = (end_time - start_time) * 1000
            
            # Validate tool_executing event emission
            assert emission_result is not None
            assert emission_result.event_emitted is True
            assert emission_result.event_type == "tool_executing"
            assert emission_result.delivery_confirmed is True
            
            # Validate tool information
            assert "tool_info" in emission_result.event_data
            assert emission_result.event_data["tool_info"]["tool_name"] == "data_analyzer"
            assert emission_result.event_data["tool_info"]["operation"] == "analyze_infrastructure_costs"
            
            # Validate execution details
            assert "execution_details" in emission_result.event_data
            assert "input_parameters" in emission_result.event_data["execution_details"]
            
            # Validate performance
            assert emission_time_ms < 40
            
            # Track event
            self.emitted_events.append(emission_result)
            self.event_timestamps["tool_executing"] = emission_result.timestamp

    async def test_tool_executing_event_validation_multiple_tools(self):
        """Test tool_executing events for multiple concurrent tools"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Define multiple tools that could execute concurrently
            concurrent_tools = [
                {
                    "tool_name": "cost_calculator",
                    "operation": "calculate_optimization_savings",
                    "duration": 30
                },
                {
                    "tool_name": "performance_analyzer",
                    "operation": "analyze_performance_metrics",
                    "duration": 60
                },
                {
                    "tool_name": "security_scanner",
                    "operation": "scan_security_configurations",
                    "duration": 45
                }
            ]
            
            # Emit tool_executing events for all tools
            tool_execution_tasks = []
            
            for tool_info in concurrent_tools:
                tool_event = {
                    "event_type": "tool_executing",
                    "user_id": self.user_id,
                    "execution_id": self.execution_id,
                    "connection_id": self.connection_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tool_info": {
                        "tool_name": tool_info["tool_name"],
                        "tool_id": str(uuid.uuid4()),
                        "operation": tool_info["operation"]
                    },
                    "execution_details": {
                        "estimated_duration": tool_info["duration"],
                        "concurrent_execution": True,
                        "execution_order": concurrent_tools.index(tool_info)
                    },
                    "metadata": {
                        "concurrent_tool_execution": True,
                        "total_concurrent_tools": len(concurrent_tools)
                    }
                }
                
                task = asyncio.create_task(
                    self.unified_emitter.emit_tool_executing(tool_event, self.user_context)
                )
                tool_execution_tasks.append((tool_info["tool_name"], task))
            
            # Wait for all tool execution events to emit
            tool_emissions = []
            for tool_name, task in tool_execution_tasks:
                emission_result = await task
                tool_emissions.append((tool_name, emission_result))
            
            # Validate all tool executions
            assert len(tool_emissions) == len(concurrent_tools)
            
            for tool_name, emission_result in tool_emissions:
                assert emission_result.event_emitted is True
                assert emission_result.event_data["tool_info"]["tool_name"] == tool_name
                assert emission_result.event_data["execution_details"]["concurrent_execution"] is True

    async def test_tool_completed_event_validation_basic(self):
        """Test basic tool_completed event validation and emission"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Create tool_completed event
            tool_completed_event = {
                "event_type": "tool_completed",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool_info": {
                    "tool_name": "data_analyzer",
                    "tool_id": str(uuid.uuid4()),
                    "operation": "analyze_infrastructure_costs"
                },
                "completion_details": {
                    "status": "success",
                    "execution_time": 42.5,
                    "result_summary": "Analysis completed successfully with 15 optimization recommendations",
                    "output_size": 2048,
                    "performance_metrics": {
                        "cpu_usage": 45,
                        "memory_usage": 234,
                        "network_calls": 12
                    }
                },
                "results": {
                    "recommendations_count": 15,
                    "potential_savings": "$2,400/month",
                    "confidence_score": 0.87,
                    "next_steps": ["implement_caching", "optimize_queries", "scale_resources"]
                },
                "metadata": {
                    "completion_step": "tool_completion",
                    "success": True
                }
            }
            
            # Emit tool_completed event
            start_time = time.time()
            
            emission_result = await self.unified_emitter.emit_tool_completed(
                tool_completed_event, self.user_context
            )
            
            end_time = time.time()
            emission_time_ms = (end_time - start_time) * 1000
            
            # Validate tool_completed event emission
            assert emission_result is not None
            assert emission_result.event_emitted is True
            assert emission_result.event_type == "tool_completed"
            assert emission_result.delivery_confirmed is True
            
            # Validate completion details
            assert "completion_details" in emission_result.event_data
            assert emission_result.event_data["completion_details"]["status"] == "success"
            assert emission_result.event_data["completion_details"]["execution_time"] == 42.5
            
            # Validate results
            assert "results" in emission_result.event_data
            assert emission_result.event_data["results"]["recommendations_count"] == 15
            
            # Validate performance
            assert emission_time_ms < 35
            
            # Track event
            self.emitted_events.append(emission_result)
            self.event_timestamps["tool_completed"] = emission_result.timestamp

    async def test_tool_completed_event_validation_with_errors(self):
        """Test tool_completed event validation when tools complete with errors"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Create tool_completed event with error
            tool_error_event = {
                "event_type": "tool_completed",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool_info": {
                    "tool_name": "external_api_caller",
                    "tool_id": str(uuid.uuid4()),
                    "operation": "fetch_market_data"
                },
                "completion_details": {
                    "status": "error",
                    "execution_time": 15.2,
                    "error_message": "API rate limit exceeded",
                    "error_code": "RATE_LIMIT_ERROR",
                    "retry_attempted": True,
                    "retry_count": 3
                },
                "error_details": {
                    "error_type": "external_api_error",
                    "recoverable": True,
                    "suggested_action": "retry_with_backoff",
                    "retry_after_seconds": 60
                },
                "metadata": {
                    "completion_step": "tool_completion",
                    "success": False,
                    "error_handled": True
                }
            }
            
            # Validate error event structure
            validation_result = await self.event_validator.validate_tool_completed_event(
                tool_error_event, self.user_context
            )
            
            assert validation_result.is_valid is True
            assert validation_result.error_event_valid is True
            assert "error_details" in tool_error_event
            
            # Emit error completion event
            emission_result = await self.unified_emitter.emit_tool_completed(
                tool_error_event, self.user_context
            )
            
            assert emission_result.event_emitted is True
            assert emission_result.event_data["completion_details"]["status"] == "error"
            assert emission_result.event_data["error_details"]["recoverable"] is True

    async def test_agent_completed_event_validation_basic(self):
        """Test basic agent_completed event validation and emission"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Create agent_completed event
            agent_completed_event = {
                "event_type": "agent_completed",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "completion_details": {
                    "status": "success",
                    "total_execution_time": 145.7,
                    "steps_completed": 4,
                    "tools_executed": 3,
                    "final_result": "AI infrastructure optimization plan generated successfully"
                },
                "results": {
                    "optimization_plan": {
                        "cost_savings": "$2,400/month",
                        "performance_improvements": "35% faster response times",
                        "implementation_steps": 8,
                        "priority_actions": ["implement_caching", "optimize_database_queries", "scale_compute_resources"]
                    },
                    "success_metrics": {
                        "recommendations_generated": 15,
                        "confidence_score": 0.92,
                        "user_satisfaction_predicted": 0.89
                    }
                },
                "metadata": {
                    "session_complete": True,
                    "user_goals_achieved": True,
                    "follow_up_required": False
                }
            }
            
            # Emit agent_completed event
            start_time = time.time()
            
            emission_result = await self.unified_emitter.emit_agent_completed(
                agent_completed_event, self.user_context
            )
            
            end_time = time.time()
            emission_time_ms = (end_time - start_time) * 1000
            
            # Validate agent_completed event emission
            assert emission_result is not None
            assert emission_result.event_emitted is True
            assert emission_result.event_type == "agent_completed"
            assert emission_result.delivery_confirmed is True
            
            # Validate completion details
            assert "completion_details" in emission_result.event_data
            assert emission_result.event_data["completion_details"]["status"] == "success"
            assert emission_result.event_data["completion_details"]["total_execution_time"] == 145.7
            
            # Validate results
            assert "results" in emission_result.event_data
            assert "optimization_plan" in emission_result.event_data["results"]
            
            # Validate performance
            assert emission_time_ms < 40
            
            # Track event
            self.emitted_events.append(emission_result)
            self.event_timestamps["agent_completed"] = emission_result.timestamp

    async def test_agent_completed_event_validation_comprehensive(self):
        """Test comprehensive agent_completed event with full execution summary"""
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Create comprehensive agent_completed event
            comprehensive_completion = {
                "event_type": "agent_completed",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "completion_details": {
                    "status": "success",
                    "total_execution_time": 287.3,
                    "steps_completed": 6,
                    "tools_executed": 5,
                    "iterations": 2,
                    "final_result": "Comprehensive AI infrastructure optimization completed with implementation roadmap"
                },
                "execution_summary": {
                    "thinking_time": 45.2,
                    "tool_execution_time": 198.1,
                    "planning_time": 32.8,
                    "validation_time": 11.2,
                    "tokens_used": 15420,
                    "api_calls_made": 23,
                    "data_processed_mb": 12.7
                },
                "results": {
                    "optimization_plan": {
                        "cost_savings_annual": "$28,800",
                        "performance_improvements": {
                            "response_time_reduction": "35%",
                            "throughput_increase": "42%",
                            "error_rate_reduction": "67%"
                        },
                        "implementation_roadmap": {
                            "phase_1": "Infrastructure caching implementation (2 weeks)",
                            "phase_2": "Database optimization (3 weeks)",
                            "phase_3": "Resource scaling automation (4 weeks)"
                        },
                        "priority_actions": [
                            "implement_redis_caching",
                            "optimize_database_queries",
                            "configure_auto_scaling",
                            "setup_performance_monitoring"
                        ]
                    },
                    "success_metrics": {
                        "recommendations_generated": 22,
                        "confidence_score": 0.94,
                        "completeness_score": 0.96,
                        "actionability_score": 0.91
                    },
                    "business_impact": {
                        "roi_projected": "340% in first year",
                        "payback_period": "3.2 months",
                        "risk_level": "low"
                    }
                },
                "metadata": {
                    "session_complete": True,
                    "user_goals_achieved": True,
                    "follow_up_required": True,
                    "follow_up_type": "implementation_support",
                    "quality_score": 0.93
                }
            }
            
            # Validate comprehensive completion structure
            validation_result = await self.event_validator.validate_agent_completed_event(
                comprehensive_completion, self.user_context
            )
            
            assert validation_result.is_valid is True
            assert validation_result.comprehensive_completion is True
            assert "execution_summary" in comprehensive_completion
            assert "business_impact" in comprehensive_completion["results"]
            
            # Emit comprehensive completion event
            emission_result = await self.unified_emitter.emit_agent_completed(
                comprehensive_completion, self.user_context
            )
            
            assert emission_result.event_emitted is True
            assert emission_result.comprehensive_data_included is True
            assert emission_result.event_data["results"]["success_metrics"]["confidence_score"] == 0.94

    async def test_complete_event_sequence_validation(self):
        """Test complete sequence of all 5 critical WebSocket events"""
        scenario = self.websocket_scenarios[2]  # complete_agent_lifecycle_events
        
        with patch('netra_backend.app.llm.llm_manager.LLMManager', return_value=self.mock_llm_manager):
            await self.event_monitor.initialize(self.user_context)
            await self.unified_emitter.initialize(self.websocket_manager, self.user_context)
            
            # Clear previous events
            self.emitted_events.clear()
            self.event_timestamps.clear()
            
            # Execute complete event sequence
            sequence_start_time = time.time()
            
            # 1. agent_started
            agent_started = await self.unified_emitter.emit_agent_started({
                "event_type": "agent_started",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_info": {"agent_type": "SupervisorAgent"},
                "metadata": {"sequence_test": True}
            }, self.user_context)
            
            await asyncio.sleep(0.01)
            
            # 2. agent_thinking
            agent_thinking = await self.unified_emitter.emit_agent_thinking({
                "event_type": "agent_thinking",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "thinking_content": {"current_step": "Planning optimization approach"},
                "metadata": {"sequence_test": True}
            }, self.user_context)
            
            await asyncio.sleep(0.01)
            
            # 3. tool_executing
            tool_executing = await self.unified_emitter.emit_tool_executing({
                "event_type": "tool_executing",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool_info": {"tool_name": "optimizer", "operation": "analyze"},
                "metadata": {"sequence_test": True}
            }, self.user_context)
            
            await asyncio.sleep(0.02)
            
            # 4. tool_completed
            tool_completed = await self.unified_emitter.emit_tool_completed({
                "event_type": "tool_completed",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool_info": {"tool_name": "optimizer"},
                "completion_details": {"status": "success"},
                "metadata": {"sequence_test": True}
            }, self.user_context)
            
            await asyncio.sleep(0.01)
            
            # 5. agent_completed
            agent_completed = await self.unified_emitter.emit_agent_completed({
                "event_type": "agent_completed",
                "user_id": self.user_id,
                "execution_id": self.execution_id,
                "connection_id": self.connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "completion_details": {"status": "success"},
                "results": {"optimization_complete": True},
                "metadata": {"sequence_test": True}
            }, self.user_context)
            
            sequence_end_time = time.time()
            total_sequence_time_ms = (sequence_end_time - sequence_start_time) * 1000
            
            # Validate complete sequence
            all_events = [agent_started, agent_thinking, tool_executing, tool_completed, agent_completed]
            
            # Verify all events emitted successfully
            for event in all_events:
                assert event is not None
                assert event.event_emitted is True
            
            # Verify event sequence order
            event_types = [event.event_type for event in all_events]
            expected_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            assert event_types == expected_sequence
            
            # Verify sequence timing
            assert total_sequence_time_ms < scenario.timing_requirements["sequence_timeout_ms"]
            
            # Verify all 5 critical events were emitted
            assert len(all_events) == 5
            assert set(event_types) == set(self.critical_events)

    def teardown_method(self, method):
        """Clean up test environment after each test method"""
        # Clear tracked events
        self.emitted_events.clear()
        self.event_timestamps.clear()
        
        # Clean up any remaining state
        asyncio.create_task(self._cleanup_test_state())
        super().teardown_method(method)

    async def _cleanup_test_state(self):
        """Helper method to clean up test state"""
        try:
            if hasattr(self, 'event_monitor') and self.event_monitor:
                await self.event_monitor.cleanup(self.user_context)
            if hasattr(self, 'unified_emitter') and self.unified_emitter:
                await self.unified_emitter.cleanup(self.user_context)
        except Exception:
            # Ignore cleanup errors in tests
            pass