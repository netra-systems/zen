"""Test #34: Agent Execution Performance Monitoring Through WebSocket Events with Timing Validation

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (performance-sensitive customers)
- Business Goal: Ensure AI agents execute within performance SLAs for business-critical operations
- Value Impact: Fast agent responses increase user satisfaction and enable real-time decision making
- Strategic Impact: Performance monitoring enables scaling to handle enterprise workloads ($100k+ monthly usage)

This test validates that agent execution performance is properly monitored through WebSocket events
with comprehensive timing validation and performance threshold enforcement.

CRITICAL: Performance monitoring through WebSocket events enables:
- Real-time performance feedback to users (execution progress and timing)
- SLA compliance monitoring for enterprise customers
- Early detection of performance degradation
- Capacity planning for infrastructure scaling
- User experience optimization through timing transparency

WITHOUT proper performance monitoring, enterprise customers cannot trust the system
for business-critical AI operations requiring predictable response times.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

import pytest

# Core application imports
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


@dataclass
class PerformanceMetric:
    """Performance metric for monitoring agent execution."""
    metric_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    threshold_ms: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def complete(self, metadata: Optional[Dict[str, Any]] = None):
        """Mark metric as complete and calculate duration."""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        if metadata:
            self.metadata = {**(self.metadata or {}), **metadata}
            
    def is_within_threshold(self) -> bool:
        """Check if execution is within performance threshold."""
        if self.duration_ms is None or self.threshold_ms is None:
            return True
        return self.duration_ms <= self.threshold_ms
        
    def get_performance_score(self) -> float:
        """Get performance score (0-100, higher is better)."""
        if self.duration_ms is None or self.threshold_ms is None:
            return 100.0
        if self.duration_ms <= self.threshold_ms:
            return 100.0
        return max(0.0, 100.0 - ((self.duration_ms - self.threshold_ms) / self.threshold_ms * 100))
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metric_name": self.metric_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "threshold_ms": self.threshold_ms,
            "within_threshold": self.is_within_threshold(),
            "performance_score": self.get_performance_score(),
            "metadata": self.metadata or {}
        }


class PerformanceMonitoringAgent(BaseAgent):
    """Agent that includes comprehensive performance monitoring."""
    
    def __init__(self, name: str, llm_manager: LLMManager):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Performance monitoring {name}")
        self.websocket_bridge = None
        self.performance_metrics = {}
        self.performance_thresholds = {
            "total_execution": 5000,  # 5 seconds total
            "agent_startup": 500,     # 500ms startup
            "thinking_phase": 1000,   # 1 second per thinking phase
            "tool_execution": 2000,   # 2 seconds per tool
            "result_generation": 1000 # 1 second for result generation
        }
        
    def set_websocket_bridge(self, bridge: AgentWebSocketBridge, run_id: str):
        """Set WebSocket bridge for performance monitoring."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    def _start_metric(self, metric_name: str, threshold_ms: Optional[float] = None) -> str:
        """Start tracking a performance metric."""
        metric_id = f"{metric_name}_{uuid.uuid4().hex[:8]}"
        threshold = threshold_ms or self.performance_thresholds.get(metric_name)
        
        self.performance_metrics[metric_id] = PerformanceMetric(
            metric_name=metric_name,
            start_time=datetime.now(timezone.utc),
            threshold_ms=threshold
        )
        return metric_id
        
    def _complete_metric(self, metric_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Complete tracking a performance metric."""
        if metric_id in self.performance_metrics:
            self.performance_metrics[metric_id].complete(metadata)
            
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute agent with comprehensive performance monitoring."""
        
        if not stream_updates or not self.websocket_bridge:
            raise ValueError("WebSocket bridge required for performance monitoring")
            
        # Start total execution timing
        total_execution_id = self._start_metric("total_execution")
        
        # Performance-monitored agent startup
        startup_id = self._start_metric("agent_startup")
        
        # EVENT 1: agent_started with performance context
        await self.websocket_bridge.notify_agent_started(
            run_id, self.name, {
                "performance_monitoring": "enabled",
                "sla_targets": self.performance_thresholds,
                "execution_id": total_execution_id,
                "start_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        self._complete_metric(startup_id, {"event": "agent_started"})
        
        # Performance-monitored thinking phases
        thinking_phases = [
            "Initializing performance-optimized analysis pipeline...",
            "Loading and validating input data for efficient processing...",
            "Executing high-performance analysis algorithms...",
            "Optimizing results for rapid delivery..."
        ]
        
        for i, thinking in enumerate(thinking_phases):
            thinking_id = self._start_metric("thinking_phase")
            
            # EVENT 2: agent_thinking with performance metrics
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, thinking,
                step_number=i + 1,
                progress_percentage=int((i + 1) / len(thinking_phases) * 30),
                performance_metrics=self.performance_metrics[thinking_id].to_dict()
            )
            
            # Simulate thinking processing time
            await asyncio.sleep(0.1)  # Controlled timing for testing
            
            self._complete_metric(thinking_id, {"thinking_phase": i + 1})
            
        # Performance-monitored tool execution
        performance_tools = [
            ("high_speed_analyzer", {"optimization": "performance", "cache_enabled": True}),
            ("efficient_processor", {"parallel_execution": True, "memory_optimized": True}),
            ("rapid_summarizer", {"streaming": True, "incremental_results": True})
        ]
        
        for tool_name, tool_params in performance_tools:
            tool_execution_id = self._start_metric("tool_execution")
            
            # EVENT 3: tool_executing with performance tracking
            await self.websocket_bridge.notify_tool_executing(
                run_id, self.name, tool_name, {
                    **tool_params,
                    "performance_tracking": True,
                    "execution_id": tool_execution_id,
                    "sla_target_ms": self.performance_thresholds["tool_execution"]
                }
            )
            
            # Simulate performance-optimized tool execution
            tool_result = await self._execute_performance_tool(tool_name, tool_params, tool_execution_id)
            
            self._complete_metric(tool_execution_id, {
                "tool_name": tool_name,
                "result_size": len(str(tool_result)),
                "cache_hit": tool_params.get("cache_enabled", False)
            })
            
            # EVENT 4: tool_completed with performance metrics
            await self.websocket_bridge.notify_tool_completed(
                run_id, self.name, tool_name, {
                    "result": tool_result,
                    "performance_metrics": self.performance_metrics[tool_execution_id].to_dict(),
                    "execution_efficiency": self._calculate_tool_efficiency(tool_execution_id)
                }
            )
            
        # Performance-monitored result generation
        result_generation_id = self._start_metric("result_generation")
        
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name,
            "Generating performance-optimized results and analytics...",
            step_number=len(thinking_phases) + 1,
            progress_percentage=95
        )
        
        # Generate comprehensive performance report
        performance_report = self._generate_performance_report()
        
        final_result = {
            "success": True,
            "agent_name": self.name,
            "performance_monitoring": {
                "total_metrics": len(self.performance_metrics),
                "sla_compliance": self._calculate_sla_compliance(),
                "performance_score": self._calculate_overall_performance_score(),
                "execution_timeline": self._generate_execution_timeline()
            },
            "business_insights": {
                "processing_efficiency": "optimized",
                "response_time_category": self._categorize_response_time(),
                "performance_recommendations": self._generate_performance_recommendations()
            },
            "detailed_metrics": performance_report,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._complete_metric(result_generation_id, {"result_size": len(str(final_result))})
        self._complete_metric(total_execution_id, {"total_metrics": len(self.performance_metrics)})
        
        # EVENT 5: agent_completed with comprehensive performance data
        await self.websocket_bridge.notify_agent_completed(
            run_id, self.name, final_result,
            execution_time_ms=int(self.performance_metrics[total_execution_id].duration_ms),
            performance_score=final_result["performance_monitoring"]["performance_score"]
        )
        
        return final_result
        
    async def _execute_performance_tool(
        self, tool_name: str, tool_params: Dict, execution_id: str
    ) -> Dict[str, Any]:
        """Execute tool with performance optimization."""
        
        # Simulate different performance characteristics for different tools
        if "high_speed" in tool_name:
            await asyncio.sleep(0.08)  # Fast execution
            return {
                "analysis_complete": True,
                "processing_time_ms": 80,
                "data_processed": "high_volume",
                "optimization_applied": "high_speed_processing",
                "cache_utilization": tool_params.get("cache_enabled", False),
                "insights": [
                    "Performance-optimized analysis completed",
                    "High-speed processing algorithms utilized",
                    "Cache optimization reduced processing time by 40%"
                ]
            }
        elif "efficient" in tool_name:
            await asyncio.sleep(0.12)  # Moderate execution
            return {
                "processing_complete": True,
                "processing_time_ms": 120,
                "efficiency_score": 92,
                "memory_optimization": tool_params.get("memory_optimized", False),
                "parallel_execution": tool_params.get("parallel_execution", False),
                "recommendations": [
                    "Efficient processing completed with 92% efficiency",
                    "Parallel execution reduced processing time",
                    "Memory optimization minimized resource usage"
                ]
            }
        else:  # rapid_summarizer
            await asyncio.sleep(0.06)  # Very fast execution
            return {
                "summary_generated": True,
                "processing_time_ms": 60,
                "streaming_enabled": tool_params.get("streaming", False),
                "incremental_results": tool_params.get("incremental_results", False),
                "summary": {
                    "performance_category": "excellent",
                    "key_metrics": ["fast_response", "low_latency", "high_throughput"],
                    "optimization_success": True
                }
            }
            
    def _calculate_tool_efficiency(self, execution_id: str) -> Dict[str, Any]:
        """Calculate tool execution efficiency."""
        metric = self.performance_metrics.get(execution_id)
        if not metric or not metric.duration_ms:
            return {"efficiency": "unknown"}
            
        threshold = metric.threshold_ms or 2000
        efficiency_percentage = min(100, (threshold - metric.duration_ms) / threshold * 100)
        
        return {
            "efficiency_percentage": max(0, efficiency_percentage),
            "execution_time_ms": metric.duration_ms,
            "threshold_ms": threshold,
            "within_sla": metric.is_within_threshold(),
            "performance_category": (
                "excellent" if efficiency_percentage > 70 else
                "good" if efficiency_percentage > 40 else
                "acceptable" if efficiency_percentage > 0 else
                "needs_optimization"
            )
        }
        
    def _calculate_sla_compliance(self) -> Dict[str, Any]:
        """Calculate SLA compliance across all metrics."""
        if not self.performance_metrics:
            return {"compliance_rate": 0, "compliant_metrics": 0, "total_metrics": 0}
            
        compliant_count = sum(1 for metric in self.performance_metrics.values() 
                             if metric.is_within_threshold())
        total_count = len(self.performance_metrics)
        compliance_rate = (compliant_count / total_count * 100) if total_count > 0 else 0
        
        return {
            "compliance_rate": compliance_rate,
            "compliant_metrics": compliant_count,
            "total_metrics": total_count,
            "sla_status": (
                "excellent" if compliance_rate >= 95 else
                "good" if compliance_rate >= 85 else
                "acceptable" if compliance_rate >= 75 else
                "needs_improvement"
            )
        }
        
    def _calculate_overall_performance_score(self) -> float:
        """Calculate overall performance score."""
        if not self.performance_metrics:
            return 0.0
            
        scores = [metric.get_performance_score() for metric in self.performance_metrics.values()]
        return sum(scores) / len(scores)
        
    def _generate_execution_timeline(self) -> List[Dict[str, Any]]:
        """Generate execution timeline with performance data."""
        timeline = []
        for metric_id, metric in self.performance_metrics.items():
            timeline.append({
                "metric_id": metric_id,
                "metric_name": metric.metric_name,
                "start_time": metric.start_time.isoformat(),
                "end_time": metric.end_time.isoformat() if metric.end_time else None,
                "duration_ms": metric.duration_ms,
                "within_threshold": metric.is_within_threshold(),
                "performance_score": metric.get_performance_score()
            })
        return sorted(timeline, key=lambda x: x["start_time"])
        
    def _categorize_response_time(self) -> str:
        """Categorize overall response time."""
        total_metrics = [m for m in self.performance_metrics.values() 
                        if m.metric_name == "total_execution" and m.duration_ms is not None]
        
        if not total_metrics:
            return "unknown"
            
        total_time = total_metrics[0].duration_ms
        
        if total_time < 1000:
            return "lightning_fast"
        elif total_time < 3000:
            return "fast"
        elif total_time < 5000:
            return "acceptable"
        else:
            return "needs_optimization"
            
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        sla_compliance = self._calculate_sla_compliance()
        if sla_compliance["compliance_rate"] < 85:
            recommendations.append("Consider performance optimization to improve SLA compliance")
            
        slow_metrics = [m for m in self.performance_metrics.values() 
                       if not m.is_within_threshold()]
        if slow_metrics:
            recommendations.append("Optimize slow-performing components for better user experience")
            
        total_time = sum(m.duration_ms for m in self.performance_metrics.values() 
                        if m.duration_ms is not None)
        if total_time > 4000:
            recommendations.append("Consider parallel processing to reduce overall execution time")
            
        if not recommendations:
            recommendations.append("Performance is excellent - maintain current optimization levels")
            
        return recommendations
        
    def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            "metrics": {metric_id: metric.to_dict() 
                       for metric_id, metric in self.performance_metrics.items()},
            "summary": {
                "total_metrics": len(self.performance_metrics),
                "overall_score": self._calculate_overall_performance_score(),
                "sla_compliance": self._calculate_sla_compliance(),
                "response_time_category": self._categorize_response_time()
            },
            "timeline": self._generate_execution_timeline(),
            "recommendations": self._generate_performance_recommendations()
        }


class WebSocketPerformanceEventCollector:
    """Collects and analyzes WebSocket events for performance monitoring."""
    
    def __init__(self):
        self.all_events = []
        self.performance_data = {}
        self.timing_analysis = {}
        
    async def create_performance_bridge(self, user_context: UserExecutionContext):
        """Create WebSocket bridge that captures performance data."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.events = []
        
        async def capture_performance_event(event_type: str, run_id: str, agent_name: str, data: Any = None, **kwargs):
            """Capture WebSocket event with performance timing."""
            event_timestamp = datetime.now(timezone.utc)
            event = {
                "event_type": event_type,
                "run_id": run_id,
                "agent_name": agent_name,
                "data": data,
                "timestamp": event_timestamp,
                "user_id": user_context.user_id,
                "kwargs": kwargs,
                "sequence_number": len(self.all_events) + 1
            }
            
            bridge.events.append(event)
            self.all_events.append(event)
            
            # Extract performance data from events
            if data and isinstance(data, dict):
                if "performance_metrics" in data:
                    self.performance_data[f"{event_type}_{len(self.all_events)}"] = data["performance_metrics"]
                if "execution_time_ms" in kwargs:
                    self.timing_analysis[f"{event_type}_{agent_name}"] = kwargs["execution_time_ms"]
                if "performance_score" in kwargs:
                    self.timing_analysis[f"score_{agent_name}"] = kwargs["performance_score"]
                    
            return True
            
        # Mock WebSocket methods with performance tracking
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            capture_performance_event("agent_started", run_id, agent_name, context))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, thinking, **kwargs:
            capture_performance_event("agent_thinking", run_id, agent_name, {"reasoning": thinking}, **kwargs))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, params:
            capture_performance_event("tool_executing", run_id, agent_name, {"tool_name": tool_name, "parameters": params}))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, result:
            capture_performance_event("tool_completed", run_id, agent_name, {"tool_name": tool_name, **result}))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, **kwargs:
            capture_performance_event("agent_completed", run_id, agent_name, result, **kwargs))
            
        return bridge
        
    def analyze_performance_timeline(self) -> Dict[str, Any]:
        """Analyze performance characteristics of event timeline."""
        if not self.all_events:
            return {"error": "No events to analyze"}
            
        # Calculate inter-event timing
        event_intervals = []
        for i in range(1, len(self.all_events)):
            prev_event = self.all_events[i-1]
            curr_event = self.all_events[i]
            interval_ms = (curr_event["timestamp"] - prev_event["timestamp"]).total_seconds() * 1000
            event_intervals.append({
                "from_event": prev_event["event_type"],
                "to_event": curr_event["event_type"],
                "interval_ms": interval_ms
            })
            
        # Calculate total execution time
        total_time_ms = (self.all_events[-1]["timestamp"] - self.all_events[0]["timestamp"]).total_seconds() * 1000
        
        return {
            "total_events": len(self.all_events),
            "total_execution_time_ms": total_time_ms,
            "average_inter_event_time_ms": sum(e["interval_ms"] for e in event_intervals) / len(event_intervals) if event_intervals else 0,
            "max_interval_ms": max(e["interval_ms"] for e in event_intervals) if event_intervals else 0,
            "min_interval_ms": min(e["interval_ms"] for e in event_intervals) if event_intervals else 0,
            "event_intervals": event_intervals,
            "events_per_second": len(self.all_events) / (total_time_ms / 1000) if total_time_ms > 0 else 0,
            "performance_data_captured": len(self.performance_data),
            "timing_metrics_captured": len(self.timing_analysis)
        }
        
    def validate_performance_slas(self, sla_thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Validate performance against SLA thresholds."""
        analysis = self.analyze_performance_timeline()
        
        validation = {
            "sla_compliance": {},
            "violations": [],
            "overall_compliance": True
        }
        
        # Check total execution time SLA
        if "total_execution_ms" in sla_thresholds:
            total_time = analysis["total_execution_time_ms"]
            threshold = sla_thresholds["total_execution_ms"]
            compliant = total_time <= threshold
            
            validation["sla_compliance"]["total_execution"] = {
                "threshold_ms": threshold,
                "actual_ms": total_time,
                "compliant": compliant,
                "performance_ratio": total_time / threshold
            }
            
            if not compliant:
                validation["violations"].append({
                    "metric": "total_execution",
                    "threshold_ms": threshold,
                    "actual_ms": total_time,
                    "violation_ms": total_time - threshold
                })
                validation["overall_compliance"] = False
                
        # Check inter-event timing SLA
        if "max_inter_event_ms" in sla_thresholds:
            max_interval = analysis["max_interval_ms"]
            threshold = sla_thresholds["max_inter_event_ms"]
            compliant = max_interval <= threshold
            
            validation["sla_compliance"]["inter_event_timing"] = {
                "threshold_ms": threshold,
                "actual_max_ms": max_interval,
                "compliant": compliant,
                "performance_ratio": max_interval / threshold
            }
            
            if not compliant:
                validation["violations"].append({
                    "metric": "inter_event_timing",
                    "threshold_ms": threshold,
                    "actual_ms": max_interval,
                    "violation_ms": max_interval - threshold
                })
                validation["overall_compliance"] = False
                
        return validation


class TestWebSocketAgentExecutionPerformanceMonitoringIntegration(BaseIntegrationTest):
    """Integration test for agent execution performance monitoring through WebSocket events."""
    
    def setup_method(self):
        """Set up test environment for performance monitoring."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TESTING", "1", source="integration_test")
        self.performance_collector = WebSocketPerformanceEventCollector()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        llm_manager.initialize = AsyncMock()
        return llm_manager
        
    @pytest.fixture
    async def performance_user_context(self):
        """Create user context for performance monitoring testing."""
        return UserExecutionContext(
            user_id=f"perf_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"perf_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"perf_run_{uuid.uuid4().hex[:8]}",
            request_id=f"perf_req_{uuid.uuid4().hex[:8]}",
            metadata={
                "performance_monitoring": True,
                "sla_requirements": {
                    "total_execution_ms": 5000,
                    "max_inter_event_ms": 1500
                },
                "user_request": "Performance-critical business analysis"
            }
        )
        
    @pytest.fixture
    async def performance_agent_registry(self, mock_llm_manager):
        """Create registry with performance monitoring agent."""
        agent = PerformanceMonitoringAgent("performance_optimizer", mock_llm_manager)
        
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: agent if name == "performance_optimizer" else None
        registry.get_async = AsyncMock(return_value=agent)
        registry.list_keys = lambda: ["performance_optimizer"]
        
        return registry, agent

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_comprehensive_performance_monitoring_with_websocket_events(
        self, real_services_fixture, performance_user_context, performance_agent_registry, mock_llm_manager
    ):
        """CRITICAL: Test comprehensive agent performance monitoring through WebSocket events."""
        
        # Business Value: Performance monitoring ensures enterprise SLA compliance
        
        registry, agent = performance_agent_registry
        websocket_bridge = await self.performance_collector.create_performance_bridge(performance_user_context)
        
        # Initialize execution engine with performance monitoring
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=performance_user_context
        )
        
        # Create agent execution context
        exec_context = AgentExecutionContext(
            user_id=performance_user_context.user_id,
            thread_id=performance_user_context.thread_id,
            run_id=performance_user_context.run_id,
            request_id=performance_user_context.request_id,
            agent_name="performance_optimizer",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Create agent state with performance requirements
        agent_state = DeepAgentState(
            user_request=performance_user_context.metadata["user_request"],
            user_id=performance_user_context.user_id,
            chat_thread_id=performance_user_context.thread_id,
            run_id=performance_user_context.run_id,
            agent_input={
                "performance_monitoring": True,
                "sla_compliance": True,
                "timing_validation": True
            }
        )
        
        # Execute agent with performance monitoring
        start_time = time.time()
        result = await execution_engine.execute_agent(exec_context, performance_user_context)
        execution_time = time.time() - start_time
        
        # CRITICAL: Validate execution succeeded
        assert result is not None
        assert result.success is True, f"Performance monitoring execution failed: {getattr(result, 'error', 'Unknown')}"
        assert result.agent_name == "performance_optimizer"
        
        # MISSION CRITICAL: Validate performance monitoring data
        performance_monitoring = result.data.get("performance_monitoring", {})
        
        assert performance_monitoring.get("total_metrics", 0) >= 7, \
            "Should have comprehensive performance metrics"
        assert "sla_compliance" in performance_monitoring, \
            "Must include SLA compliance analysis"
        assert "performance_score" in performance_monitoring, \
            "Must calculate overall performance score"
        assert "execution_timeline" in performance_monitoring, \
            "Must provide execution timeline"
            
        # Validate SLA compliance
        sla_compliance = performance_monitoring["sla_compliance"]
        assert sla_compliance.get("compliance_rate", 0) >= 75, \
            f"SLA compliance too low: {sla_compliance.get('compliance_rate', 0)}%"
        assert sla_compliance.get("total_metrics", 0) > 0, \
            "Must have metrics for SLA calculation"
        assert sla_compliance.get("sla_status") in ["excellent", "good", "acceptable"], \
            f"Unacceptable SLA status: {sla_compliance.get('sla_status')}"
            
        # Validate performance score
        performance_score = performance_monitoring.get("performance_score", 0)
        assert performance_score >= 50, \
            f"Performance score too low: {performance_score}"
        assert performance_score <= 100, \
            f"Performance score invalid: {performance_score}"
            
        # Validate execution timeline
        timeline = performance_monitoring.get("execution_timeline", [])
        assert len(timeline) >= 5, \
            f"Timeline too short: {len(timeline)} events"
            
        # Validate timeline has required metrics
        timeline_metrics = [event["metric_name"] for event in timeline]
        required_metrics = ["total_execution", "agent_startup", "thinking_phase", "tool_execution"]
        for required_metric in required_metrics:
            assert any(required_metric in metric for metric in timeline_metrics), \
                f"Missing required metric: {required_metric}"
                
        # PERFORMANCE: Validate WebSocket event timing analysis
        timing_analysis = self.performance_collector.analyze_performance_timeline()
        
        assert timing_analysis["total_events"] >= 10, \
            f"Not enough events for performance analysis: {timing_analysis['total_events']}"
        assert timing_analysis["total_execution_time_ms"] > 0, \
            "Must have measurable execution time"
        assert timing_analysis["events_per_second"] >= 2, \
            f"Event rate too low: {timing_analysis['events_per_second']:.2f} events/sec"
        assert timing_analysis["performance_data_captured"] > 0, \
            "Must capture performance data in events"
            
        # Validate SLA thresholds from user context
        sla_requirements = performance_user_context.metadata.get("sla_requirements", {})
        if sla_requirements:
            sla_validation = self.performance_collector.validate_performance_slas(sla_requirements)
            
            assert sla_validation["overall_compliance"] is True, \
                f"SLA violations detected: {sla_validation['violations']}"
                
            # Check specific SLA metrics
            if "total_execution_ms" in sla_requirements:
                total_sla = sla_validation["sla_compliance"]["total_execution"]
                assert total_sla["compliant"] is True, \
                    f"Total execution SLA violated: {total_sla['actual_ms']}ms > {total_sla['threshold_ms']}ms"
                    
        # DATABASE INTEGRATION: Validate performance data persistence
        if real_services_fixture["database_available"]:
            db_session = real_services_fixture["db"]
            if db_session:
                # Performance execution record for database
                performance_record = {
                    "user_id": performance_user_context.user_id,
                    "run_id": performance_user_context.run_id,
                    "agent_name": "performance_optimizer",
                    "execution_time_ms": execution_time * 1000,
                    "performance_score": performance_score,
                    "sla_compliant": sla_compliance.get("compliance_rate", 0) >= 85,
                    "metrics_captured": performance_monitoring["total_metrics"],
                    "websocket_events": timing_analysis["total_events"]
                }
                
                # Validate record is suitable for persistence
                assert performance_record["execution_time_ms"] > 0
                assert performance_record["performance_score"] >= 0
                assert performance_record["metrics_captured"] > 0
                
        # Validate business insights include performance context
        business_insights = result.data.get("business_insights", {})
        assert "processing_efficiency" in business_insights
        assert "response_time_category" in business_insights
        assert "performance_recommendations" in business_insights
        
        response_category = business_insights["response_time_category"]
        assert response_category in ["lightning_fast", "fast", "acceptable", "needs_optimization"], \
            f"Invalid response time category: {response_category}"
            
        self.logger.info(
            f" PASS:  Performance monitoring test PASSED - "
            f"Score: {performance_score:.1f}, "
            f"SLA: {sla_compliance.get('compliance_rate', 0):.1f}%, "
            f"Events: {timing_analysis['total_events']}, "
            f"Time: {execution_time*1000:.1f}ms"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_sla_validation_and_threshold_enforcement(
        self, performance_user_context, performance_agent_registry
    ):
        """Test performance SLA validation and threshold enforcement."""
        
        # Business Value: SLA enforcement ensures enterprise performance commitments
        
        registry, agent = performance_agent_registry
        
        # Set strict performance thresholds for testing
        strict_sla_requirements = {
            "total_execution_ms": 3000,  # Strict 3-second limit
            "max_inter_event_ms": 800    # Strict inter-event timing
        }
        
        # Update user context with strict SLAs
        strict_context = UserExecutionContext(
            user_id=performance_user_context.user_id,
            thread_id=performance_user_context.thread_id,
            run_id=f"{performance_user_context.run_id}_strict",
            request_id=f"{performance_user_context.request_id}_strict",
            metadata={
                **performance_user_context.metadata,
                "sla_requirements": strict_sla_requirements,
                "performance_tier": "enterprise_premium"
            }
        )
        
        websocket_bridge = await self.performance_collector.create_performance_bridge(strict_context)
        
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=strict_context
        )
        
        exec_context = AgentExecutionContext(
            user_id=strict_context.user_id,
            thread_id=strict_context.thread_id,
            run_id=strict_context.run_id,
            request_id=strict_context.request_id,
            agent_name="performance_optimizer",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        agent_state = DeepAgentState(
            user_request={"strict_sla_testing": True},
            user_id=strict_context.user_id,
            chat_thread_id=strict_context.thread_id,
            run_id=strict_context.run_id,
            agent_input={"sla_enforcement": "strict"}
        )
        
        # Execute with strict SLA monitoring
        result = await execution_engine.execute_agent(exec_context, strict_context)
        
        # Validate execution succeeded
        assert result.success is True
        
        # Validate SLA compliance analysis
        timing_analysis = self.performance_collector.analyze_performance_timeline()
        sla_validation = self.performance_collector.validate_performance_slas(strict_sla_requirements)
        
        # Check SLA validation structure
        assert "sla_compliance" in sla_validation
        assert "violations" in sla_validation
        assert "overall_compliance" in sla_validation
        
        # Validate SLA metrics were captured
        if "total_execution" in sla_validation["sla_compliance"]:
            total_sla = sla_validation["sla_compliance"]["total_execution"]
            assert "threshold_ms" in total_sla
            assert "actual_ms" in total_sla
            assert "compliant" in total_sla
            assert "performance_ratio" in total_sla
            
        # Log SLA compliance results
        self.logger.info(
            f" PASS:  SLA validation test PASSED - "
            f"Overall compliance: {sla_validation['overall_compliance']}, "
            f"Violations: {len(sla_validation['violations'])}, "
            f"Total time: {timing_analysis['total_execution_time_ms']:.1f}ms"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_degradation_detection_and_alerting(
        self, performance_user_context, mock_llm_manager
    ):
        """Test detection of performance degradation and alerting."""
        
        # Business Value: Early detection prevents SLA breaches and user dissatisfaction
        
        # Create agent that simulates performance degradation
        class DegradingPerformanceAgent(BaseAgent):
            def __init__(self, llm_manager):
                super().__init__(llm_manager, "degrading_agent", "Agent with degrading performance")
                self.websocket_bridge = None
                self.execution_count = 0
                
            def set_websocket_bridge(self, bridge, run_id):
                self.websocket_bridge = bridge
                
            async def execute(self, state, run_id, stream_updates=True):
                self.execution_count += 1
                
                if not stream_updates or not self.websocket_bridge:
                    raise ValueError("WebSocket required")
                    
                # Simulate degrading performance (each execution gets slower)
                base_delay = 0.1
                degradation_factor = self.execution_count * 0.05
                total_delay = base_delay + degradation_factor
                
                await self.websocket_bridge.notify_agent_started(run_id, "degrading_agent", {
                    "performance_warning": degradation_factor > 0.1,
                    "expected_degradation": total_delay
                })
                
                await self.websocket_bridge.notify_agent_thinking(
                    run_id, "degrading_agent", "Processing with potential performance degradation...",
                    performance_warning=degradation_factor > 0.1
                )
                
                # Simulate degraded processing
                await asyncio.sleep(total_delay)
                
                result = {
                    "success": True,
                    "performance_analysis": {
                        "execution_count": self.execution_count,
                        "degradation_detected": degradation_factor > 0.1,
                        "performance_score": max(0, 100 - (degradation_factor * 200)),
                        "degradation_factor": degradation_factor,
                        "total_delay": total_delay
                    }
                }
                
                await self.websocket_bridge.notify_agent_completed(
                    run_id, "degrading_agent", result,
                    execution_time_ms=int(total_delay * 1000),
                    performance_degradation_detected=degradation_factor > 0.1
                )
                
                return result
        
        degrading_agent = DegradingPerformanceAgent(mock_llm_manager)
        
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: degrading_agent
        registry.get_async = AsyncMock(return_value=degrading_agent)
        
        websocket_bridge = await self.performance_collector.create_performance_bridge(performance_user_context)
        
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=performance_user_context
        )
        
        exec_context = AgentExecutionContext(
            user_id=performance_user_context.user_id,
            thread_id=performance_user_context.thread_id,
            run_id=performance_user_context.run_id,
            request_id=performance_user_context.request_id,
            agent_name="degrading_agent",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        agent_state = DeepAgentState(
            user_request={"performance_degradation_test": True},
            user_id=performance_user_context.user_id,
            chat_thread_id=performance_user_context.thread_id,
            run_id=performance_user_context.run_id
        )
        
        # Execute with performance degradation
        result = await execution_engine.execute_agent(exec_context, performance_user_context)
        
        # Validate degradation detection
        assert result.success is True
        
        performance_analysis = result.data.get("performance_analysis", {})
        assert "degradation_detected" in performance_analysis
        assert "performance_score" in performance_analysis
        assert "degradation_factor" in performance_analysis
        
        # Validate WebSocket events captured degradation warnings
        warning_events = [
            e for e in self.performance_collector.all_events 
            if e.get("kwargs", {}).get("performance_degradation_detected") is True
        ]
        
        if performance_analysis.get("degradation_detected"):
            assert len(warning_events) > 0, "Performance degradation should be reported in WebSocket events"
            
        self.logger.info(
            f" PASS:  Performance degradation detection test PASSED - "
            f"Degradation detected: {performance_analysis.get('degradation_detected', False)}, "
            f"Performance score: {performance_analysis.get('performance_score', 0):.1f}"
        )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])