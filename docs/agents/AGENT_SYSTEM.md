# Agent System & Orchestration Documentation

Comprehensive documentation for the Netra Multi-Agent System architecture and orchestration patterns.

> **📣 Architecture Update - January 2025**  
> The agent system has transitioned to the **UVS (Unified Validation System)** architecture with:
> - Streamlined 2-agent triage model (down from 3 agents)
> - Data Intelligence Agent as PRIMARY agent (80% of requests)
> - Intelligent data sufficiency validation states
> 
> See **[UVS Triage Architecture Transition Guide](../UVS_TRIAGE_ARCHITECTURE_TRANSITION.md)** for complete details.

## Table of Contents

- [Overview](#overview)
- [Agent Architecture](#agent-architecture)
- [Supervisor Agent](#supervisor-agent)
- [Sub-Agents](#sub-agents)
- [Agent Communication](#agent-communication)
- [Tool System](#tool-system)
- [Orchestration Patterns](#orchestration-patterns)
- [State Management](#state-management)
- [Agent Development Guide](#agent-development-guide)
- [Performance & Scaling](#performance--scaling)

## Overview

The Netra platform implements a sophisticated multi-agent system designed for intelligent AI workload optimization. The system uses a supervisor-orchestrated architecture where specialized sub-agents handle specific aspects of the optimization process.

### Key Design Principles

1. **Separation of Concerns**: Each agent has a specific, well-defined responsibility
2. **Orchestrated Workflow**: Supervisor manages the flow between agents
3. **Shared State**: Agents communicate through a shared state mechanism
4. **Tool Integration**: Agents can use specialized tools for data gathering and actions
5. **Async Processing**: All agent operations are asynchronous for scalability

## Agent Architecture

### System Hierarchy

```
┌──────────────────────────────────────────────────────────┐
│                    User Request                          │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                  Supervisor Agent                        │
│  • Orchestrates workflow                                 │
│  • Manages agent selection                               │
│  • Maintains conversation state                          │
│  • Handles error recovery                                │
└────────┬──────────────────────────────────┬──────────────┘
         │                                  │
    ┌────▼─────┐                      ┌────▼─────┐
    │  Triage  │                      │Reporting │
    │  Agent   │                      │  Agent   │
    └────┬─────┘                      └──────────┘
         │
    ┌────▼─────────────────────────────────────┐
    │           Specialized Sub-Agents          │
    │  ┌─────────┐  ┌─────────┐  ┌──────────┐ │
    │  │  Data   │  │Optimize │  │ Actions  │ │
    │  │  Agent  │  │  Agent  │  │  Agent   │ │
    │  └─────────┘  └─────────┘  └──────────┘ │
    └───────────────────────────────────────────┘
```

### Agent Roles

| Agent | Primary Responsibility | Key Functions |
|-------|----------------------|---------------|
| **Supervisor** | Orchestration & Control | Workflow management, agent selection, state coordination |
| **Triage** | Request Analysis | Understanding intent, categorizing requests, initial planning |
| **Data** | Information Gathering | Data collection, enrichment, tool operations |
| **Optimization Core** | Analysis & Strategy | Core optimization logic, strategy formulation |
| **Actions** | Implementation | Formulating concrete actions, supply configurations |
| **Reporting** | Results & Communication | Summarizing results, user-facing reports |

## Supervisor Agent

The Supervisor Agent is the central orchestrator of the multi-agent system.

### Implementation

```python
# app/agents/supervisor.py
from typing import Dict, List, Optional
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.prompts import SUPERVISOR_SYSTEM_PROMPT

class SupervisorAgent(BaseAgent):
    def __init__(self, llm_manager, tools=None):
        super().__init__(
            name="SupervisorAgent",
            llm_manager=llm_manager,
            system_prompt=SUPERVISOR_SYSTEM_PROMPT,
            tools=tools
        )
        self.sub_agents = {}
        self.conversation_state = {}
    
    async def orchestrate(self, user_message: str, context: Dict) -> Dict:
        """Main orchestration method"""
        try:
            # Initialize conversation state
            self.conversation_state = {
                "user_message": user_message,
                "context": context,
                "agent_outputs": {},
                "current_phase": "triage"
            }
            
            # Phase 1: Triage
            triage_result = await self.execute_triage()
            
            # Phase 2: Data Gathering
            if triage_result.get("needs_data"):
                data_result = await self.execute_data_gathering()
            
            # Phase 3: Optimization
            optimization_result = await self.execute_optimization()
            
            # Phase 4: Actions
            actions_result = await self.execute_actions()
            
            # Phase 5: Reporting
            final_report = await self.execute_reporting()
            
            return {
                "success": True,
                "result": final_report,
                "metadata": self.conversation_state
            }
            
        except Exception as e:
            return await self.handle_error(e)
    
    async def execute_triage(self) -> Dict:
        """Execute triage phase"""
        self.conversation_state["current_phase"] = "triage"
        
        triage_agent = self.sub_agents["triage"]
        result = await triage_agent.process(
            message=self.conversation_state["user_message"],
            context=self.conversation_state["context"]
        )
        
        self.conversation_state["agent_outputs"]["triage"] = result
        return result
    
    async def execute_data_gathering(self) -> Dict:
        """Execute data gathering phase"""
        self.conversation_state["current_phase"] = "data_gathering"
        
        data_agent = self.sub_agents["data"]
        
        # Prepare context from triage
        data_context = {
            "requirements": self.conversation_state["agent_outputs"]["triage"].get("requirements"),
            "data_needs": self.conversation_state["agent_outputs"]["triage"].get("data_needs")
        }
        
        result = await data_agent.process(
            message="Gather required data",
            context=data_context
        )
        
        self.conversation_state["agent_outputs"]["data"] = result
        return result
    
    async def select_next_agent(self) -> Optional[str]:
        """Determine which agent should process next"""
        current_phase = self.conversation_state["current_phase"]
        
        # Define workflow transitions
        workflow = {
            "triage": "data",
            "data": "optimization",
            "optimization": "actions",
            "actions": "reporting",
            "reporting": None  # Terminal state
        }
        
        return workflow.get(current_phase)
    
    def register_sub_agent(self, name: str, agent: BaseAgent):
        """Register a sub-agent"""
        self.sub_agents[name] = agent
    
    async def handle_error(self, error: Exception) -> Dict:
        """Handle orchestration errors"""
        error_context = {
            "error": str(error),
            "phase": self.conversation_state.get("current_phase"),
            "partial_results": self.conversation_state.get("agent_outputs")
        }
        
        # Attempt recovery or graceful degradation
        return {
            "success": False,
            "error": str(error),
            "context": error_context
        }
```

### Supervisor Prompts

```python
# app/agents/prompts.py
SUPERVISOR_SYSTEM_PROMPT = """
You are the Supervisor Agent for the Netra AI Optimization Platform.

Your role is to:
1. Orchestrate the workflow between specialized sub-agents
2. Maintain conversation state and context
3. Ensure smooth information flow between agents
4. Make decisions about which agents to invoke
5. Handle errors and recovery
6. Provide final synthesis of results

Workflow phases:
1. Triage: Understand and categorize the request
2. Data: Gather necessary information
3. Optimization: Analyze and formulate strategy
4. Actions: Define concrete implementation steps
5. Reporting: Summarize and present results

Always maintain context between agent calls and ensure each agent has the information it needs.
"""
```

## Sub-Agents

### Triage Sub-Agent

```python
# app/agents/triage_sub_agent.py
class TriageSubAgent(BaseAgent):
    def __init__(self, llm_manager):
        super().__init__(
            name="TriageSubAgent",
            llm_manager=llm_manager,
            system_prompt=TRIAGE_SYSTEM_PROMPT
        )
    
    async def process(self, message: str, context: Dict) -> Dict:
        """Analyze and categorize user request"""
        prompt = f"""
        Analyze the following user request and determine:
        1. Intent and objectives
        2. Required data and information
        3. Optimization priorities
        4. Constraints and requirements
        
        User Request: {message}
        Context: {json.dumps(context)}
        """
        
        response = await self.llm_manager.generate(
            prompt=prompt,
            system_prompt=self.system_prompt
        )
        
        return self.parse_response(response)
    
    def parse_response(self, response: str) -> Dict:
        """Parse LLM response into structured format"""
        # Extract structured information from response
        return {
            "intent": extract_intent(response),
            "objectives": extract_objectives(response),
            "data_needs": extract_data_needs(response),
            "priorities": extract_priorities(response),
            "constraints": extract_constraints(response),
            "needs_data": bool(extract_data_needs(response))
        }
```

### Data Sub-Agent

```python
# app/agents/data_sub_agent.py
class DataSubAgent(BaseAgent):
    def __init__(self, llm_manager, tools):
        super().__init__(
            name="DataSubAgent",
            llm_manager=llm_manager,
            system_prompt=DATA_SYSTEM_PROMPT,
            tools=tools
        )
    
    async def process(self, message: str, context: Dict) -> Dict:
        """Gather and enrich data"""
        data_needs = context.get("data_needs", [])
        gathered_data = {}
        
        for need in data_needs:
            if need == "workload_metrics":
                gathered_data["workload_metrics"] = await self.gather_workload_metrics()
            elif need == "cost_analysis":
                gathered_data["cost_analysis"] = await self.gather_cost_data()
            elif need == "performance_data":
                gathered_data["performance_data"] = await self.gather_performance_data()
        
        # Enrich data with analysis
        enriched_data = await self.enrich_data(gathered_data)
        
        return {
            "raw_data": gathered_data,
            "enriched_data": enriched_data,
            "data_quality": self.assess_data_quality(gathered_data)
        }
    
    async def gather_workload_metrics(self) -> Dict:
        """Use tools to gather workload metrics"""
        if "get_workload_metrics" in self.tools:
            return await self.tools["get_workload_metrics"].execute()
        return {}
    
    def assess_data_quality(self, data: Dict) -> Dict:
        """Assess the quality and completeness of gathered data"""
        return {
            "completeness": calculate_completeness(data),
            "freshness": check_data_freshness(data),
            "reliability": assess_reliability(data)
        }
```

### Optimization Core Sub-Agent

```python
# app/agents/optimization_core_sub_agent.py
class OptimizationCoreSubAgent(BaseAgent):
    def __init__(self, llm_manager):
        super().__init__(
            name="OptimizationCoreSubAgent",
            llm_manager=llm_manager,
            system_prompt=OPTIMIZATION_SYSTEM_PROMPT
        )
    
    async def process(self, message: str, context: Dict) -> Dict:
        """Core optimization logic"""
        data = context.get("enriched_data", {})
        priorities = context.get("priorities", [])
        constraints = context.get("constraints", [])
        
        # Perform multi-dimensional optimization
        optimization_strategy = await self.formulate_strategy(
            data=data,
            priorities=priorities,
            constraints=constraints
        )
        
        # Generate optimization recommendations
        recommendations = await self.generate_recommendations(
            strategy=optimization_strategy,
            data=data
        )
        
        return {
            "strategy": optimization_strategy,
            "recommendations": recommendations,
            "expected_improvements": self.calculate_improvements(recommendations, data),
            "risk_assessment": self.assess_risks(recommendations)
        }
    
    async def formulate_strategy(self, data: Dict, priorities: List, constraints: List) -> Dict:
        """Formulate optimization strategy"""
        prompt = f"""
        Based on the following data and requirements, formulate an optimization strategy:
        
        Data: {json.dumps(data)}
        Priorities: {priorities}
        Constraints: {constraints}
        
        Provide a comprehensive strategy that balances all factors.
        """
        
        response = await self.llm_manager.generate(prompt=prompt)
        return parse_strategy(response)
```

### Actions Sub-Agent

```python
# app/agents/actions_sub_agent.py
class ActionsSubAgent(BaseAgent):
    def __init__(self, llm_manager, tools):
        super().__init__(
            name="ActionsSubAgent",
            llm_manager=llm_manager,
            system_prompt=ACTIONS_SYSTEM_PROMPT,
            tools=tools
        )
    
    async def process(self, message: str, context: Dict) -> Dict:
        """Formulate concrete actions"""
        strategy = context.get("strategy", {})
        recommendations = context.get("recommendations", [])
        
        # Convert recommendations to actionable steps
        actions = []
        for recommendation in recommendations:
            action = await self.create_action(recommendation)
            actions.append(action)
        
        # Generate supply configurations
        supply_config = await self.generate_supply_config(actions)
        
        # Validate actions
        validation_result = await self.validate_actions(actions, context)
        
        return {
            "actions": actions,
            "supply_config": supply_config,
            "execution_plan": self.create_execution_plan(actions),
            "validation": validation_result
        }
    
    async def create_action(self, recommendation: Dict) -> Dict:
        """Convert recommendation to concrete action"""
        return {
            "type": recommendation.get("type"),
            "description": recommendation.get("description"),
            "parameters": recommendation.get("parameters"),
            "priority": recommendation.get("priority"),
            "estimated_impact": recommendation.get("impact"),
            "implementation_steps": await self.detail_implementation(recommendation)
        }
    
    async def generate_supply_config(self, actions: List[Dict]) -> Dict:
        """Generate supply catalog configuration"""
        return {
            "compute": extract_compute_config(actions),
            "storage": extract_storage_config(actions),
            "network": extract_network_config(actions),
            "services": extract_services_config(actions)
        }
```

### Reporting Agent

```python
# app/agents/reporting_agent.py
class ReportingAgent(BaseAgent):
    def __init__(self, llm_manager):
        super().__init__(
            name="ReportingAgent",
            llm_manager=llm_manager,
            system_prompt=REPORTING_SYSTEM_PROMPT
        )
    
    async def process(self, message: str, context: Dict) -> Dict:
        """Generate final report"""
        # Gather all agent outputs
        all_outputs = context.get("agent_outputs", {})
        
        # Create executive summary
        executive_summary = await self.create_executive_summary(all_outputs)
        
        # Detail recommendations
        detailed_recommendations = self.format_recommendations(
            all_outputs.get("optimization", {}).get("recommendations", [])
        )
        
        # Create action plan
        action_plan = self.format_action_plan(
            all_outputs.get("actions", {}).get("actions", [])
        )
        
        # Generate metrics and KPIs
        metrics = self.compile_metrics(all_outputs)
        
        return {
            "executive_summary": executive_summary,
            "recommendations": detailed_recommendations,
            "action_plan": action_plan,
            "metrics": metrics,
            "next_steps": self.suggest_next_steps(all_outputs),
            "full_report": self.generate_full_report(all_outputs)
        }
    
    async def create_executive_summary(self, outputs: Dict) -> str:
        """Create executive summary of optimization results"""
        prompt = f"""
        Create a concise executive summary of the optimization analysis:
        
        Triage: {outputs.get("triage")}
        Data: {outputs.get("data")}
        Optimization: {outputs.get("optimization")}
        Actions: {outputs.get("actions")}
        
        Focus on key findings, recommendations, and expected outcomes.
        """
        
        return await self.llm_manager.generate(prompt=prompt)
```

## Agent Communication

### Shared State Management

```python
# app/agents/state_manager.py
class AgentStateManager:
    def __init__(self):
        self.state = {}
        self.history = []
        self.lock = asyncio.Lock()
    
    async def update_state(self, agent_name: str, data: Dict):
        """Update shared state with agent output"""
        async with self.lock:
            self.state[agent_name] = data
            self.history.append({
                "timestamp": datetime.utcnow(),
                "agent": agent_name,
                "action": "update",
                "data": data
            })
    
    async def get_state(self, agent_name: str = None) -> Dict:
        """Retrieve state for specific agent or all"""
        async with self.lock:
            if agent_name:
                return self.state.get(agent_name, {})
            return self.state.copy()
    
    async def get_context_for_agent(self, agent_name: str) -> Dict:
        """Get relevant context for specific agent"""
        async with self.lock:
            context = {}
            
            # Define dependencies between agents
            dependencies = {
                "data": ["triage"],
                "optimization": ["triage", "data"],
                "actions": ["triage", "optimization"],
                "reporting": ["triage", "data", "optimization", "actions"]
            }
            
            # Gather dependent agent outputs
            for dep in dependencies.get(agent_name, []):
                if dep in self.state:
                    context[dep] = self.state[dep]
            
            return context
```

### Message Protocol

```python
# app/agents/protocol.py
from pydantic import BaseModel
from typing import Any, Optional

class AgentMessage(BaseModel):
    """Standard message format for inter-agent communication"""
    sender: str
    recipient: str
    message_type: str  # request, response, error, status
    content: Any
    correlation_id: str
    timestamp: datetime
    metadata: Optional[Dict] = {}

class AgentRequest(AgentMessage):
    """Request from one agent to another"""
    message_type: str = "request"
    timeout: Optional[int] = 30

class AgentResponse(AgentMessage):
    """Response from agent"""
    message_type: str = "response"
    success: bool
    error: Optional[str] = None

class AgentBus:
    """Message bus for agent communication"""
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.message_queue = asyncio.Queue()
    
    async def publish(self, message: AgentMessage):
        """Publish message to bus"""
        await self.message_queue.put(message)
        
        # Notify subscribers
        for subscriber in self.subscribers[message.recipient]:
            await subscriber.handle_message(message)
    
    def subscribe(self, agent_name: str, handler):
        """Subscribe agent to messages"""
        self.subscribers[agent_name].append(handler)
```

## Tool System

### Tool Architecture

```python
# app/agents/tools/base.py
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """Base class for agent tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict:
        """Execute tool with given parameters"""
        pass
    
    @abstractmethod
    def validate_parameters(self, **kwargs) -> bool:
        """Validate tool parameters"""
        pass

# app/agents/tools/tool_registry.py
class ToolRegistry:
    """Registry for available tools"""
    
    def __init__(self):
        self.tools = {}
    
    def register(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List available tools"""
        return list(self.tools.keys())
```

### Example Tools

```python
# app/agents/tools/workload_tools.py
class GetWorkloadMetricsTool(BaseTool):
    def __init__(self, db_service):
        super().__init__(
            name="get_workload_metrics",
            description="Retrieve workload metrics from database"
        )
        self.db_service = db_service
    
    async def execute(self, workload_id: str, time_range: Dict) -> Dict:
        """Get workload metrics"""
        metrics = await self.db_service.get_workload_metrics(
            workload_id=workload_id,
            start_time=time_range.get("start"),
            end_time=time_range.get("end")
        )
        
        return {
            "workload_id": workload_id,
            "metrics": metrics,
            "summary": self.summarize_metrics(metrics)
        }
    
    def validate_parameters(self, **kwargs) -> bool:
        required = ["workload_id", "time_range"]
        return all(k in kwargs for k in required)

class OptimizeResourcesTool(BaseTool):
    def __init__(self, optimization_service):
        super().__init__(
            name="optimize_resources",
            description="Optimize resource allocation"
        )
        self.optimization_service = optimization_service
    
    async def execute(self, current_config: Dict, constraints: Dict) -> Dict:
        """Optimize resource configuration"""
        optimized = await self.optimization_service.optimize(
            current=current_config,
            constraints=constraints
        )
        
        return {
            "original": current_config,
            "optimized": optimized,
            "improvements": self.calculate_improvements(current_config, optimized)
        }
```

### Tool Dispatcher

```python
# app/agents/tools/tool_dispatcher.py
class ToolDispatcher:
    """Dispatches tool calls for agents"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry
    
    async def dispatch(self, tool_name: str, parameters: Dict) -> Dict:
        """Dispatch tool execution"""
        tool = self.registry.get_tool(tool_name)
        
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        
        if not tool.validate_parameters(**parameters):
            raise ValueError(f"Invalid parameters for tool {tool_name}")
        
        try:
            result = await tool.execute(**parameters)
            return {
                "success": True,
                "tool": tool_name,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e)
            }
```

## Orchestration Patterns

### Sequential Orchestration

```python
class SequentialOrchestrator:
    """Execute agents in sequence"""
    
    async def orchestrate(self, agents: List[BaseAgent], initial_input: Dict) -> Dict:
        current_input = initial_input
        results = []
        
        for agent in agents:
            result = await agent.process(current_input)
            results.append(result)
            current_input = result  # Output becomes next input
        
        return {
            "final_result": results[-1],
            "all_results": results
        }
```

### Parallel Orchestration

```python
class ParallelOrchestrator:
    """Execute agents in parallel"""
    
    async def orchestrate(self, agents: List[BaseAgent], input_data: Dict) -> Dict:
        tasks = [agent.process(input_data) for agent in agents]
        results = await asyncio.gather(*tasks)
        
        return {
            "results": results,
            "aggregated": self.aggregate_results(results)
        }
```

### Conditional Orchestration

```python
class ConditionalOrchestrator:
    """Execute agents based on conditions"""
    
    async def orchestrate(self, initial_input: Dict) -> Dict:
        triage_result = await self.triage_agent.process(initial_input)
        
        if triage_result.get("category") == "optimization":
            return await self.optimization_flow(triage_result)
        elif triage_result.get("category") == "analysis":
            return await self.analysis_flow(triage_result)
        else:
            return await self.default_flow(triage_result)
```

## State Management

### Conversation State

```python
# app/agents/conversation_state.py
class ConversationState:
    """Manages conversation state across agent interactions"""
    
    def __init__(self, thread_id: str, user_id: int):
        self.thread_id = thread_id
        self.user_id = user_id
        self.messages = []
        self.agent_states = {}
        self.context = {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add message to conversation"""
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def update_agent_state(self, agent_name: str, state: Dict):
        """Update state for specific agent"""
        self.agent_states[agent_name] = {
            "state": state,
            "updated_at": datetime.utcnow()
        }
        self.updated_at = datetime.utcnow()
    
    def get_conversation_context(self) -> Dict:
        """Get full conversation context"""
        return {
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "messages": self.messages,
            "agent_states": self.agent_states,
            "context": self.context,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
```

### State Persistence

```python
# app/services/state_persistence_service.py
class StatePersistenceService:
    """Persist and retrieve agent states"""
    
    def __init__(self, db_service, redis_client):
        self.db = db_service
        self.redis = redis_client
    
    async def save_state(self, state: ConversationState):
        """Save conversation state"""
        # Save to Redis for quick access
        redis_key = f"state:{state.thread_id}"
        await self.redis.setex(
            redis_key,
            3600,  # 1 hour TTL
            json.dumps(state.get_conversation_context(), default=str)
        )
        
        # Save to database for persistence
        await self.db.save_conversation_state(
            thread_id=state.thread_id,
            state_data=state.get_conversation_context()
        )
    
    async def load_state(self, thread_id: str) -> Optional[ConversationState]:
        """Load conversation state"""
        # Try Redis first
        redis_key = f"state:{thread_id}"
        cached_state = await self.redis.get(redis_key)
        
        if cached_state:
            return self.deserialize_state(json.loads(cached_state))
        
        # Fall back to database
        db_state = await self.db.get_conversation_state(thread_id)
        if db_state:
            state = self.deserialize_state(db_state)
            # Re-cache in Redis
            await self.save_state(state)
            return state
        
        return None
```

## Agent Development Guide

### Creating a New Agent

```python
# Template for new agent
from netra_backend.app.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    """Custom agent for specific task"""
    
    def __init__(self, llm_manager, tools=None):
        system_prompt = """
        You are a specialized agent for [specific task].
        Your responsibilities include:
        1. [Responsibility 1]
        2. [Responsibility 2]
        """
        
        super().__init__(
            name="CustomAgent",
            llm_manager=llm_manager,
            system_prompt=system_prompt,
            tools=tools
        )
    
    async def process(self, message: str, context: Dict) -> Dict:
        """Process input and return results"""
        # 1. Prepare prompt
        prompt = self.prepare_prompt(message, context)
        
        # 2. Call LLM
        response = await self.llm_manager.generate(
            prompt=prompt,
            system_prompt=self.system_prompt
        )
        
        # 3. Parse response
        parsed = self.parse_response(response)
        
        # 4. Execute tools if needed
        if self.tools and parsed.get("needs_tools"):
            tool_results = await self.execute_tools(parsed.get("tool_calls"))
            parsed["tool_results"] = tool_results
        
        # 5. Return structured output
        return self.format_output(parsed)
    
    def prepare_prompt(self, message: str, context: Dict) -> str:
        """Prepare prompt for LLM"""
        return f"""
        Task: {message}
        Context: {json.dumps(context)}
        
        Please provide structured analysis and recommendations.
        """
    
    def parse_response(self, response: str) -> Dict:
        """Parse LLM response"""
        # Implement parsing logic
        return {}
    
    def format_output(self, parsed: Dict) -> Dict:
        """Format agent output"""
        return {
            "status": "success",
            "results": parsed,
            "metadata": {
                "agent": self.name,
                "timestamp": datetime.utcnow()
            }
        }
```

### Agent Registration

```python
# app/agents/agent_factory.py
class AgentFactory:
    """Factory for creating and managing agents"""
    
    def __init__(self, llm_manager, tool_registry):
        self.llm_manager = llm_manager
        self.tool_registry = tool_registry
        self.agents = {}
    
    def create_agent(self, agent_type: str) -> BaseAgent:
        """Create agent by type"""
        if agent_type == "triage":
            return TriageSubAgent(self.llm_manager)
        elif agent_type == "data":
            tools = self.get_tools_for_agent("data")
            return DataSubAgent(self.llm_manager, tools)
        elif agent_type == "optimization":
            return OptimizationCoreSubAgent(self.llm_manager)
        elif agent_type == "actions":
            tools = self.get_tools_for_agent("actions")
            return ActionsSubAgent(self.llm_manager, tools)
        elif agent_type == "reporting":
            return ReportingAgent(self.llm_manager)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    def get_tools_for_agent(self, agent_type: str) -> Dict:
        """Get relevant tools for agent"""
        tool_mapping = {
            "data": ["get_workload_metrics", "get_cost_data"],
            "actions": ["create_supply_config", "validate_config"]
        }
        
        tools = {}
        for tool_name in tool_mapping.get(agent_type, []):
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                tools[tool_name] = tool
        
        return tools
```

## Performance & Scaling

### Agent Performance Monitoring

```python
# app/monitoring/agent_metrics.py
class AgentMetrics:
    """Monitor agent performance"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            "total_calls": 0,
            "total_duration": 0,
            "errors": 0,
            "last_call": None
        })
    
    async def record_call(self, agent_name: str, duration: float, success: bool):
        """Record agent call metrics"""
        self.metrics[agent_name]["total_calls"] += 1
        self.metrics[agent_name]["total_duration"] += duration
        if not success:
            self.metrics[agent_name]["errors"] += 1
        self.metrics[agent_name]["last_call"] = datetime.utcnow()
    
    def get_metrics(self, agent_name: str = None) -> Dict:
        """Get metrics for agent or all agents"""
        if agent_name:
            return dict(self.metrics[agent_name])
        return dict(self.metrics)
    
    def get_average_duration(self, agent_name: str) -> float:
        """Get average call duration for agent"""
        metrics = self.metrics[agent_name]
        if metrics["total_calls"] > 0:
            return metrics["total_duration"] / metrics["total_calls"]
        return 0
```

### Scaling Strategies

```python
# app/agents/scaling.py
class AgentPool:
    """Pool of agent instances for scaling"""
    
    def __init__(self, agent_factory: AgentFactory, max_instances: int = 10):
        self.factory = agent_factory
        self.max_instances = max_instances
        self.pools = defaultdict(list)
        self.in_use = defaultdict(set)
    
    async def get_agent(self, agent_type: str) -> BaseAgent:
        """Get available agent from pool"""
        # Check for available agent
        if self.pools[agent_type]:
            agent = self.pools[agent_type].pop()
        else:
            # Create new agent if under limit
            if len(self.in_use[agent_type]) < self.max_instances:
                agent = self.factory.create_agent(agent_type)
            else:
                # Wait for available agent
                await asyncio.sleep(0.1)
                return await self.get_agent(agent_type)
        
        self.in_use[agent_type].add(agent)
        return agent
    
    async def return_agent(self, agent_type: str, agent: BaseAgent):
        """Return agent to pool"""
        self.in_use[agent_type].discard(agent)
        self.pools[agent_type].append(agent)
```

### Caching Strategy

```python
# app/agents/caching.py
class AgentCache:
    """Cache for agent responses"""
    
    def __init__(self, redis_client, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl
    
    def generate_cache_key(self, agent_name: str, input_hash: str) -> str:
        """Generate cache key"""
        return f"agent_cache:{agent_name}:{input_hash}"
    
    async def get(self, agent_name: str, input_data: Dict) -> Optional[Dict]:
        """Get cached response"""
        input_hash = hashlib.md5(
            json.dumps(input_data, sort_keys=True).encode()
        ).hexdigest()
        
        key = self.generate_cache_key(agent_name, input_hash)
        cached = await self.redis.get(key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def set(self, agent_name: str, input_data: Dict, response: Dict):
        """Cache agent response"""
        input_hash = hashlib.md5(
            json.dumps(input_data, sort_keys=True).encode()
        ).hexdigest()
        
        key = self.generate_cache_key(agent_name, input_hash)
        await self.redis.setex(
            key,
            self.ttl,
            json.dumps(response, default=str)
        )
```

## Testing Agents

### Unit Testing

```python
# tests/agents/test_supervisor.py
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_supervisor_orchestration():
    """Test supervisor orchestration flow"""
    # Mock dependencies
    llm_manager = Mock()
    llm_manager.generate = AsyncMock(return_value="test response")
    
    # Create supervisor
    supervisor = SupervisorAgent(llm_manager)
    
    # Register mock sub-agents
    mock_triage = Mock()
    mock_triage.process = AsyncMock(return_value={"intent": "optimize"})
    supervisor.register_sub_agent("triage", mock_triage)
    
    # Test orchestration
    result = await supervisor.orchestrate(
        user_message="Optimize my workload",
        context={}
    )
    
    assert result["success"] is True
    assert mock_triage.process.called
```

### Integration Testing

```python
# tests/agents/test_agent_integration.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_agent_workflow():
    """Test complete agent workflow"""
    # Setup
    factory = AgentFactory(llm_manager, tool_registry)
    supervisor = factory.create_agent("supervisor")
    
    # Register all sub-agents
    for agent_type in ["triage", "data", "optimization", "actions", "reporting"]:
        sub_agent = factory.create_agent(agent_type)
        supervisor.register_sub_agent(agent_type, sub_agent)
    
    # Execute workflow
    result = await supervisor.orchestrate(
        user_message="Optimize my GPU workload for cost",
        context={"workload_id": "test-123"}
    )
    
    # Assertions
    assert result["success"] is True
    assert "recommendations" in result["result"]
    assert "action_plan" in result["result"]
```