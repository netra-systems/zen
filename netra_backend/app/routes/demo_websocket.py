"""
Simple Demo WebSocket Endpoint - NO AUTHENTICATION REQUIRED
For staging demo purposes only

This endpoint provides a simplified WebSocket connection for demo purposes
that properly emits all required agent events without authentication.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.config import get_config

logger = central_logger.get_logger(__name__)

router = APIRouter(prefix="/api/demo", tags=["demo"])


async def execute_real_agent_workflow(websocket: WebSocket, user_message: str, connection_id: str) -> None:
    """Execute real agent workflow with actual AI processing.
    
    This function:
    1. Creates proper execution context with database session
    2. Initializes real supervisor agent
    3. Processes the message through actual agent workflow
    4. Sends real WebSocket events as agents execute
    """
    try:
        # Create demo user context - use UUID format to avoid placeholder validation issues
        demo_user_id = f"demo-user-{uuid.uuid4()}"
        thread_id = f"demo-thread-{uuid.uuid4()}"
        run_id = f"demo-run-{uuid.uuid4()}"
        
        # Get database session - required for SupervisorAgent
        from netra_backend.app.db.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        
        # Use async context manager for database session
        async with db_manager.get_async_session() as db_session:
            # Create user execution context with proper metadata
            user_context = UserExecutionContext(
                user_id=demo_user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=str(uuid.uuid4()),  # Use plain UUID format
                db_session=db_session,
                websocket_client_id=connection_id,
                agent_context={"user_request": user_message, "demo_mode": True},
                audit_metadata={"demo_session": True, "connection_id": connection_id}
            )
            
            # Create WebSocket bridge adapter that implements all required methods
            class WebSocketAdapter:
                """Adapter to make WebSocket compatible with AgentWebSocketBridge"""
                
                async def send_event(self, event_type: str, data: dict):
                    """Send WebSocket event to client"""
                    await websocket.send_json({
                        "type": event_type,
                        "timestamp": datetime.utcnow().isoformat(),
                        **data
                    })
                    logger.info(f"Demo WebSocket sent {event_type}: {data.get('run_id', 'unknown')}")
                
                async def notify_agent_started(self, run_id: str, agent_name: str, context=None, **kwargs):
                    """Send agent started notification"""
                    await self.send_event("agent_started", {
                        "agent": agent_name,
                        "run_id": run_id,
                        "message": "Starting AI analysis..."
                    })
                    
                async def notify_agent_thinking(self, run_id: str, agent_name: str, reasoning: str = "", **kwargs):
                    """Send agent thinking notification"""
                    await self.send_event("agent_thinking", {
                        "agent": agent_name,
                        "run_id": run_id,
                        "message": reasoning or "Analyzing your request..."
                    })
                    
                async def notify_tool_executing(self, run_id: str, tool_name: str, agent_name: Optional[str] = None, parameters=None, **kwargs):
                    """Send tool executing notification"""
                    await self.send_event("tool_executing", {
                        "agent": agent_name or "Agent",
                        "run_id": run_id,
                        "tool": tool_name,
                        "message": f"Executing {tool_name}..."
                    })
                    
                async def notify_tool_completed(self, run_id: str, tool_name: str, result=None, agent_name: Optional[str] = None, **kwargs):
                    """Send tool completed notification"""
                    await self.send_event("tool_completed", {
                        "agent": agent_name or "Agent",
                        "run_id": run_id,
                        "tool": tool_name,
                        "message": f"Completed {tool_name}"
                    })
                    
                async def notify_agent_completed(self, run_id: str, agent_name: str, result=None, **kwargs):
                    """Send agent completed notification with final result"""
                    # Extract the response text from the result
                    response_text = "Analysis completed."
                    if result and isinstance(result, dict):
                        # Look for the actual response data
                        if "data" in result and isinstance(result["data"], dict):
                            result_data = result["data"]
                            if "results" in result_data:
                                response_text = str(result_data["results"])
                            elif "reporting" in result_data:
                                response_text = str(result_data["reporting"])
                        elif "results" in result:
                            response_text = str(result["results"])
                    elif result:
                        response_text = str(result)
                        
                    await self.send_event("agent_completed", {
                        "agent": agent_name,
                        "run_id": run_id,
                        "message": response_text
                    })
                    
                async def notify_agent_error(self, run_id: str, agent_name: str, error: str, **kwargs):
                    """Send agent error notification"""
                    await self.send_event("agent_error", {
                        "agent": agent_name,
                        "run_id": run_id,
                        "error": error,
                        "message": f"Error in {agent_name}: {error}"
                    })
            
            # Create a custom bridge that uses our WebSocket adapter
            class DemoWebSocketBridge(AgentWebSocketBridge):
                """Demo WebSocket bridge that sends events directly to the demo WebSocket"""
                
                def __init__(self, websocket_adapter):
                    super().__init__(user_context=user_context)
                    self.websocket_adapter = websocket_adapter
                
                async def notify_agent_started(self, run_id: str, agent_name: str, **kwargs):
                    return await self.websocket_adapter.notify_agent_started(run_id, agent_name, **kwargs)
                    
                async def notify_agent_thinking(self, run_id: str, agent_name: str, reasoning: str = "", **kwargs):
                    return await self.websocket_adapter.notify_agent_thinking(run_id, agent_name, reasoning, **kwargs)
                    
                async def notify_tool_executing(self, run_id: str, tool_name: str, **kwargs):
                    return await self.websocket_adapter.notify_tool_executing(run_id, tool_name, **kwargs)
                    
                async def notify_tool_completed(self, run_id: str, tool_name: str, **kwargs):
                    return await self.websocket_adapter.notify_tool_completed(run_id, tool_name, **kwargs)
                    
                async def notify_agent_completed(self, run_id: str, agent_name: str, **kwargs):
                    return await self.websocket_adapter.notify_agent_completed(run_id, agent_name, **kwargs)
                    
                async def notify_agent_error(self, run_id: str, agent_name: str, error: str, **kwargs):
                    return await self.websocket_adapter.notify_agent_error(run_id, agent_name, error, **kwargs)
            
            ws_adapter = WebSocketAdapter()
            bridge = DemoWebSocketBridge(ws_adapter)
            
            # Get LLM manager with user context
            llm_manager = LLMManager(user_context)
            
            # CRITICAL FIX: Initialize agent registry before creating supervisor
            # This ensures the agent factory has a populated registry
            from netra_backend.app.agents.supervisor.agent_class_initialization import initialize_agent_class_registry
            from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
            
            # Initialize the agent class registry if not already done
            agent_registry = initialize_agent_class_registry()
            logger.info(f"Agent registry initialized with {len(agent_registry)} agents for demo")
            
            # Configure the agent factory with the registry
            factory = get_agent_instance_factory()
            factory.configure(
                agent_class_registry=agent_registry,
                websocket_bridge=bridge,
                llm_manager=llm_manager
            )
            
            # Import and create supervisor agent using SSOT pattern
            from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
            supervisor = SupervisorAgent(
                llm_manager=llm_manager,
                websocket_bridge=bridge
            )
                
            # Execute using SSOT execute method with proper UserExecutionContext
            result = await supervisor.execute(user_context, stream_updates=True)
            
            logger.info(f"Demo agent execution completed: {result}")
            
            # Database session will be automatically closed by context manager
        
    except Exception as e:
        logger.error(f"Real agent execution failed: {e}", exc_info=True)
        
        # Send error notification to user
        try:
            await websocket.send_json({
                "type": "agent_error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "message": "Sorry, there was an issue processing your request. Please try again."
            })
        except Exception as ws_error:
            logger.error(f"Failed to send error notification: {ws_error}")
        
        # Don't fall back to simulator - we want to fix real agent execution
        # If you want fallback for production, you can uncomment the next line:
        # await DemoAgentSimulator.simulate_agent_execution(websocket, user_message)

class DemoAgentSimulator:
    """Simulates agent execution with proper event emissions"""
    
    @staticmethod
    async def send_event(websocket: WebSocket, event_type: str, data: Dict[str, Any]) -> None:
        """Send a WebSocket event to the client"""
        message = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }
        await websocket.send_json(message)
        logger.info(f"Demo WebSocket sent {event_type}: {data.get('run_id', 'unknown')}")
    
    @staticmethod
    async def simulate_agent_execution(websocket: WebSocket, user_message: str) -> None:
        """Simulate full agent execution with all required events"""
        run_id = str(uuid.uuid4())
        
        try:
            # 1. Agent Started Event
            await DemoAgentSimulator.send_event(websocket, "agent_started", {
                "run_id": run_id,
                "agent_name": "Netra AI Assistant",
                "message": "Processing your request..."
            })
            await asyncio.sleep(0.5)
            
            # 2. Agent Thinking Event
            await DemoAgentSimulator.send_event(websocket, "agent_thinking", {
                "run_id": run_id,
                "agent_name": "Netra AI Assistant",
                "thought": "Analyzing your request and preparing optimization strategies..."
            })
            await asyncio.sleep(1.0)
            
            # 3. Tool Executing Event
            await DemoAgentSimulator.send_event(websocket, "tool_executing", {
                "run_id": run_id,
                "tool_name": "AI Optimization Analyzer",
                "parameters": {"query": user_message}
            })
            await asyncio.sleep(1.5)
            
            # 4. Tool Completed Event
            optimization_result = DemoAgentSimulator.generate_demo_response(user_message)
            await DemoAgentSimulator.send_event(websocket, "tool_completed", {
                "run_id": run_id,
                "tool_name": "AI Optimization Analyzer",
                "result": optimization_result
            })
            await asyncio.sleep(0.5)
            
            # 5. Agent Completed Event
            await DemoAgentSimulator.send_event(websocket, "agent_completed", {
                "run_id": run_id,
                "agent_name": "Netra AI Assistant",
                "response": optimization_result,
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"Error in demo agent simulation: {e}")
            await DemoAgentSimulator.send_event(websocket, "error", {
                "run_id": run_id,
                "error": str(e),
                "message": "An error occurred during processing. Please try again."
            })
    
    @staticmethod
    def generate_demo_response(user_message: str) -> str:
        """Generate a demo response based on the user message"""
        responses = {
            "default": """Based on my analysis, here are your AI optimization opportunities:

1. **Cost Optimization**: Identified potential 35% reduction in compute costs through intelligent workload scheduling
2. **Performance Enhancement**: Can improve response times by 2.3x using our multi-agent orchestration
3. **Resource Utilization**: Current utilization at 45%, can optimize to 80% with smart batching

**Recommended Actions:**
- Implement dynamic resource allocation
- Enable predictive scaling based on usage patterns
- Deploy intelligent caching strategies

Estimated Annual Savings: $125,000
ROI Timeline: 3-4 months""",
            
            "healthcare": """Healthcare AI Optimization Analysis Complete:

**Key Findings:**
- Patient data processing can be accelerated by 4x
- HIPAA-compliant infrastructure already optimized
- Medical imaging AI workloads showing 60% idle time

**Optimization Strategy:**
- Implement federated learning for distributed training
- Enable GPU sharing for inference workloads
- Deploy edge computing for real-time diagnostics

Projected Impact: 250% faster diagnoses, $450K annual savings""",
            
            "finance": """Financial Services AI Optimization Report:

**Current State Analysis:**
- Fraud detection models using 3x more compute than necessary
- Risk assessment pipelines have 40% redundant calculations
- Trading algorithms not utilizing available GPU acceleration

**Optimization Recommendations:**
- Consolidate model serving infrastructure
- Implement intelligent batching for risk calculations
- Enable hardware acceleration for real-time trading

Expected Results: 5x faster processing, $380K cost reduction"""
        }
        
        # Check for industry-specific keywords
        message_lower = user_message.lower()
        if "healthcare" in message_lower or "medical" in message_lower:
            return responses["healthcare"]
        elif "finance" in message_lower or "trading" in message_lower or "banking" in message_lower:
            return responses["finance"]
        else:
            return responses["default"]


@router.websocket("/ws")
async def demo_websocket_endpoint(websocket: WebSocket):
    """
    Demo WebSocket endpoint - NO AUTHENTICATION REQUIRED
    
    This endpoint:
    1. Accepts WebSocket connections without authentication
    2. Receives user messages
    3. Simulates agent execution with all 5 required events
    4. Returns optimization recommendations
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    logger.info(f"Demo WebSocket connection established: {connection_id}")
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "connection_id": connection_id,
            "message": "Welcome to Netra AI Demo! Send a message to start."
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                # Handle ping/pong for connection keep-alive
                await websocket.send_json({"type": "pong"})
                continue
            
            if data.get("type") == "chat" and data.get("message"):
                user_message = data["message"]
                logger.info(f"Demo received message: {user_message[:100]}...")
                
                # Use real agent execution instead of simulation
                await execute_real_agent_workflow(websocket, user_message, connection_id)
            
    except WebSocketDisconnect:
        logger.info(f"Demo WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Demo WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "An unexpected error occurred. Please refresh and try again."
            })
        except:
            pass
        await websocket.close()


@router.get("/health")
async def demo_health_check():
    """Health check endpoint for demo service"""
    return {
        "status": "healthy",
        "service": "demo_websocket",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "authentication_required": False,
            "agent_events": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
            "ready_for_demo": True
        }
    }