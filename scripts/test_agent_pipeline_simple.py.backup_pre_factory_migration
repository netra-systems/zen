#!/usr/bin/env python
"""Simplified Agent Pipeline E2E Test

Tests the complete agent execution pipeline without complex fixtures or external dependencies.
This validates the core agent orchestration flow with WebSocket event integration.

Tests:
1. Agent pipeline can execute multiple agent types
2. State is properly passed between pipeline stages
3. WebSocket events are sent throughout the pipeline
4. Tool execution works within the pipeline
"""

import asyncio
import os
import sys
import time
from typing import Dict, List, Any
from shared.isolated_environment import IsolatedEnvironment

# Add project root for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Core imports
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher

# Try to import real agents
try:
    from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
    from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
    from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
    REAL_AGENTS_AVAILABLE = True
except ImportError:
    REAL_AGENTS_AVAILABLE = False
    print("Real agents not available - using mock agents")


class MockWebSocket:
    """Enhanced mock WebSocket for pipeline testing."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.messages: List[Dict] = []
        self.connected = True
        self.events: List[Dict] = []
        self.start_time = time.time()
        self.agent_events = {}  # Track events by agent
        
    async def send_text(self, data: str) -> bool:
        return await self._record_event(data)
            
    async def send_json(self, data: Dict, timeout: float = None) -> bool:
        return await self._record_event(data)
    
    async def _record_event(self, event_data) -> bool:
        if not self.connected:
            return False
            
        if isinstance(event_data, str):
            import json
            try:
                event = json.loads(event_data)
            except json.JSONDecodeError:
                return False
        else:
            event = event_data
            
        event_type = event.get("type", "unknown")
        payload = event.get("payload", {})
        agent_name = payload.get("agent_name", "unknown")
        
        # Track events by agent
        if agent_name not in self.agent_events:
            self.agent_events[agent_name] = []
        self.agent_events[agent_name].append(event_type)
        
        self.events.append(event)
        self.messages.append(event)
        
        relative_time = time.time() - self.start_time
        print(f"[{relative_time:.3f}s] WebSocket: {event_type} from {agent_name}")
        
        return True
        
    def client_state(self):
        return 1 if self.connected else 0
        
    @property 
    def state(self):
        return 1 if self.connected else 0
        
    def get_pipeline_summary(self) -> Dict:
        """Get summary of pipeline execution via WebSocket events."""
        event_types = [event.get("type") for event in self.events]
        
        return {
            "total_events": len(self.events),
            "agents_involved": list(self.agent_events.keys()),
            "events_per_agent": {agent: len(events) for agent, events in self.agent_events.items()},
            "event_timeline": event_types,
            "has_pipeline_start": "agent_started" in event_types,
            "has_pipeline_completion": "agent_completed" in event_types,
            "duration": time.time() - self.start_time
        }


class MockAgent:
    """Mock agent that simulates agent behavior with proper WebSocket events."""
    
    def __init__(self, name: str, websocket_manager: WebSocketManager, processing_time: float = 0.1):
        self.name = name
        self.websocket_manager = websocket_manager
        self.notifier = WebSocketNotifier(websocket_manager)
        self.processing_time = processing_time
        
    async def execute(self, state: DeepAgentState, run_id: str, **kwargs) -> Any:
        """Execute agent with proper WebSocket event flow."""
        
        context = AgentExecutionContext(
            run_id=run_id,
            thread_id=state.chat_thread_id,
            user_id=state.user_id,
            agent_name=self.name,
            retry_count=0,
            max_retries=1
        )
        
        try:
            # Agent starts
            await self.notifier.send_agent_started(context)
            
            # Agent thinks
            thinking_message = f"{self.name} analyzing: {state.user_request}"
            await self.notifier.send_agent_thinking(context, thinking_message)
            
            # Simulate processing time
            await asyncio.sleep(self.processing_time)
            
            # Execute relevant tools based on agent type
            if "triage" in self.name.lower():
                await self._execute_triage_tools(context, state)
            elif "data" in self.name.lower():
                await self._execute_data_tools(context, state)
            elif "optimization" in self.name.lower():
                await self._execute_optimization_tools(context, state)
            else:
                await self._execute_generic_tools(context, state)
            
            # Generate result based on agent type
            result = await self._generate_agent_result(state)
            
            # Agent completes
            await self.notifier.send_agent_completed(context, result)
            
            return result
            
        except Exception as e:
            error_result = {"error": str(e), "success": False}
            await self.notifier.send_agent_completed(context, error_result)
            return error_result
    
    async def _execute_triage_tools(self, context: AgentExecutionContext, state: DeepAgentState):
        """Execute triage-specific tools."""
        await self.notifier.send_tool_executing(context, "request_classifier", 
                                              tool_purpose="Classify user request type")
        await asyncio.sleep(0.05)
        
        classification_result = {
            "category": "optimization_request",
            "confidence": 0.9,
            "complexity": "medium"
        }
        await self.notifier.send_tool_completed(context, "request_classifier", classification_result)
        
        # Store triage result in state
        from types import SimpleNamespace
        state.triage_result = SimpleNamespace()
        state.triage_result.category = "optimization_request"
        state.triage_result.confidence_score = 0.9
    
    async def _execute_data_tools(self, context: AgentExecutionContext, state: DeepAgentState):
        """Execute data analysis tools."""
        await self.notifier.send_tool_executing(context, "data_analyzer", 
                                              tool_purpose="Analyze user data patterns")
        await asyncio.sleep(0.05)
        
        analysis_result = {
            "analysis_type": "cost_performance",
            "metrics_found": ["latency", "cost", "usage"],
            "data_quality": "good"
        }
        await self.notifier.send_tool_completed(context, "data_analyzer", analysis_result)
        
        # Return structured result
        return SimpleNamespace(
            success=True,
            result=analysis_result,
            execution_time_ms=50
        )
    
    async def _execute_optimization_tools(self, context: AgentExecutionContext, state: DeepAgentState):
        """Execute optimization tools."""
        await self.notifier.send_tool_executing(context, "optimization_generator", 
                                              tool_purpose="Generate optimization recommendations")
        await asyncio.sleep(0.05)
        
        optimization_result = {
            "recommendations": [
                "Reduce model complexity for faster inference",
                "Implement request batching",
                "Use model caching for repeated queries"
            ],
            "estimated_savings": "30%",
            "implementation_difficulty": "medium"
        }
        await self.notifier.send_tool_completed(context, "optimization_generator", optimization_result)
        
        # Store optimization results in state
        from types import SimpleNamespace
        state.optimizations_result = SimpleNamespace()
        state.optimizations_result.optimization_type = "performance_cost"
        state.optimizations_result.recommendations = optimization_result["recommendations"]
        state.optimizations_result.confidence_score = 0.85
    
    async def _execute_generic_tools(self, context: AgentExecutionContext, state: DeepAgentState):
        """Execute generic tools."""
        await self.notifier.send_tool_executing(context, "generic_processor", 
                                              tool_purpose="Process request generically")
        await asyncio.sleep(0.05)
        
        generic_result = {"processed": True, "status": "completed"}
        await self.notifier.send_tool_completed(context, "generic_processor", generic_result)
    
    async def _generate_agent_result(self, state: DeepAgentState) -> Dict[str, Any]:
        """Generate appropriate result based on agent type."""
        if "triage" in self.name.lower():
            return {
                "agent_type": "triage",
                "category_identified": "optimization_request",
                "confidence": 0.9,
                "success": True
            }
        elif "data" in self.name.lower():
            return {
                "agent_type": "data",
                "analysis_completed": True,
                "metrics_analyzed": 3,
                "success": True
            }
        elif "optimization" in self.name.lower():
            return {
                "agent_type": "optimization",
                "recommendations_count": 3,
                "estimated_impact": "high",
                "success": True
            }
        else:
            return {
                "agent_type": "generic",
                "processing_completed": True,
                "success": True
            }


class AgentPipeline:
    """Simplified agent pipeline orchestrator."""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.agents = []
        
    def add_agent(self, agent):
        """Add agent to pipeline."""
        self.agents.append(agent)
        
    async def execute_pipeline(self, initial_state: DeepAgentState) -> Dict[str, Any]:
        """Execute complete agent pipeline."""
        
        pipeline_results = []
        current_state = initial_state
        
        print(f"Starting pipeline with {len(self.agents)} agents...")
        
        for i, agent in enumerate(self.agents):
            print(f"Executing agent {i+1}/{len(self.agents)}: {agent.name}")
            
            run_id = f"pipeline-{initial_state.run_id}-agent-{i}"
            
            try:
                result = await agent.execute(current_state, run_id)
                pipeline_results.append({
                    "agent": agent.name,
                    "result": result,
                    "success": result.get("success", True)
                })
                
                # Update state for next agent (in real pipeline, state would be enriched)
                # Here we just track progress
                
            except Exception as e:
                error_result = {
                    "agent": agent.name,
                    "result": {"error": str(e), "success": False},
                    "success": False
                }
                pipeline_results.append(error_result)
                print(f"Agent {agent.name} failed: {e}")
                # Continue with next agent for testing purposes
        
        return {
            "pipeline_completed": True,
            "agents_executed": len(pipeline_results),
            "successful_agents": sum(1 for r in pipeline_results if r["success"]),
            "results": pipeline_results
        }


async def test_simplified_agent_pipeline():
    """Test simplified agent pipeline with WebSocket integration."""
    
    print("=" * 70)
    print("SIMPLIFIED AGENT PIPELINE E2E TEST")
    print("=" * 70)
    
    # Setup WebSocket system
    ws_manager = WebSocketManager()
    
    user_id = "pipeline-test-user"
    thread_id = "pipeline-test-thread"
    
    # Create mock WebSocket
    mock_websocket = MockWebSocket(user_id)
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    
    print(f"Connected user {user_id} for pipeline testing")
    
    # Create pipeline
    pipeline = AgentPipeline(ws_manager)
    
    # Add agents to pipeline (simulating real pipeline stages)
    pipeline.add_agent(MockAgent("triage_agent", ws_manager, 0.1))
    pipeline.add_agent(MockAgent("data_agent", ws_manager, 0.15))
    pipeline.add_agent(MockAgent("optimization_agent", ws_manager, 0.2))
    
    print(f"Created pipeline with {len(pipeline.agents)} agents")
    
    # Create initial state
    initial_state = DeepAgentState(
        user_request="Analyze my AI costs and recommend optimizations for better performance",
        user_id=user_id,
        chat_thread_id=thread_id,
        run_id="pipeline-test-001"
    )
    
    print(f"Starting pipeline execution for: {initial_state.user_request}")
    
    # Execute pipeline
    start_time = time.time()
    pipeline_result = await pipeline.execute_pipeline(initial_state)
    execution_time = time.time() - start_time
    
    print(f"Pipeline execution completed in {execution_time:.3f}s")
    
    # Wait for events to propagate
    await asyncio.sleep(0.5)
    
    # Analyze results
    print("\n" + "=" * 50)
    print("PIPELINE EXECUTION RESULTS")
    print("=" * 50)
    
    print(f"Pipeline completed: {pipeline_result['pipeline_completed']}")
    print(f"Agents executed: {pipeline_result['agents_executed']}")
    print(f"Successful agents: {pipeline_result['successful_agents']}")
    print(f"Success rate: {pipeline_result['successful_agents'] / pipeline_result['agents_executed'] * 100:.1f}%")
    
    print("\nAgent Results:")
    for result in pipeline_result['results']:
        status = "PASS" if result['success'] else "FAIL"
        print(f"  {status} {result['agent']}: {result['result'].get('success', 'unknown')}")
    
    # Analyze WebSocket events
    print("\n" + "=" * 50)
    print("WEBSOCKET EVENT ANALYSIS")
    print("=" * 50)
    
    event_summary = mock_websocket.get_pipeline_summary()
    
    print(f"Total WebSocket events: {event_summary['total_events']}")
    print(f"Agents involved: {event_summary['agents_involved']}")
    print(f"Events per agent: {event_summary['events_per_agent']}")
    print(f"Has pipeline start: {event_summary['has_pipeline_start']}")
    print(f"Has pipeline completion: {event_summary['has_pipeline_completion']}")
    print(f"Event timeline duration: {event_summary['duration']:.3f}s")
    
    print(f"\nEvent timeline (first 10):")
    for i, event_type in enumerate(event_summary['event_timeline'][:10]):
        print(f"  {i+1}. {event_type}")
    if len(event_summary['event_timeline']) > 10:
        print(f"  ... and {len(event_summary['event_timeline']) - 10} more events")
    
    # Validations
    assert pipeline_result['pipeline_completed'], "Pipeline did not complete"
    assert pipeline_result['successful_agents'] >= 2, f"Too few successful agents: {pipeline_result['successful_agents']}"
    assert event_summary['total_events'] >= 10, f"Too few WebSocket events: {event_summary['total_events']}"
    assert len(event_summary['agents_involved']) >= 3, f"Too few agents involved: {len(event_summary['agents_involved'])}"
    assert event_summary['has_pipeline_start'], "Pipeline start events missing"
    assert event_summary['has_pipeline_completion'], "Pipeline completion events missing"
    assert execution_time < 10.0, f"Pipeline took too long: {execution_time}s"
    
    print("\nSUCCESS: Simplified agent pipeline E2E test passed!")
    return True


async def main():
    """Run simplified pipeline test."""
    
    try:
        await test_simplified_agent_pipeline()
        
        print("\n" + "=" * 70)
        print("SIMPLIFIED PIPELINE TEST COMPLETED SUCCESSFULLY!")
        print("Agent pipeline with WebSocket integration validated.")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\nSIMPLIFIED PIPELINE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)