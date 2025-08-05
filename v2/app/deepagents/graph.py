
import inspect
from typing import Any, Callable, List, Optional, Sequence, TypedDict, Union

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from app.llm.llm_manager import LLMManager

from .state import DeepAgentState
from .supervisor import create_supervisor_graph
from .tools import (
    edit_file,
    ls,
    read_file,
    update_todo,
    write_file,
    write_todos,
)

class SubAgent(TypedDict):
    name: str
    description: str
    prompt: str
    tools: Optional[list] = None

class Team:
    def __init__(self, agents: List[SubAgent], llm_manager: LLMManager, supervisor_llm_name: str = "default"):
        self.agents = agents
        self.llm_manager = llm_manager
        self.supervisor_llm_name = supervisor_llm_name

    def create_graph(self):
        # Create the supervisor graph
        supervisor_graph = create_supervisor_graph(self.llm_manager, self.supervisor_llm_name)

        # Create the agent graphs
        agent_graphs = {}
        for agent in self.agents:
            agent_graphs[agent["name"]] = create_deep_agent(
                tools=agent.get("tools", []),
                instructions=agent["prompt"],
                llm_manager=self.llm_manager,
            )

        # Define the main graph
        workflow = StateGraph(DeepAgentState)
        workflow.add_node("supervisor", supervisor_graph)

        for agent_name, agent_graph in agent_graphs.items():
            workflow.add_node(agent_name, agent_graph)

        # Add edges
        for agent_name in agent_graphs:
            workflow.add_edge(agent_name, "supervisor")

        # The conditional edge will decide which agent to call
        workflow.add_conditional_edges(
            "supervisor",
            lambda x: x["next"],
            {**{agent: agent for agent in agent_graphs}, **{"FINISH": END}},
        )

        workflow.set_entry_point("supervisor")
        return workflow.compile()

def create_deep_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    llm_manager: LLMManager,
    model_name: str = "default",
    state_schema: Optional[DeepAgentState] = None,
):
    base_prompt = """You have access to a number of standard tools to help you manage and plan your work.

## Todos

You can manage a todo list to track your progress.

### `write_todos`

Use the `write_todos` tool to add new tasks to your todo list. This is especially useful for breaking down large, complex tasks into smaller, more manageable steps.

### `update_todo`

Use the `update_todo` tool to update the status of a task in your todo list. The available statuses are "pending", "in_progress", and "completed".

It is critical that you follow this lifecycle for each task:

1.  When you start working on a task, mark it as "in_progress".
2.  When you have completed a task, mark it as "completed".

Do not batch up multiple tasks before marking them as completed.
"""
    prompt = instructions + base_prompt
    built_in_tools = [write_todos, update_todo, write_file, read_file, ls, edit_file]
    all_tools = [t if isinstance(t, BaseTool) else tool(t) for t in built_in_tools + list(tools)]
    model_with_tools = model.bind_tools(all_tools)

    state_schema = state_schema or DeepAgentState
    workflow = StateGraph(state_schema)

    async def agent_node(state: DeepAgentState):
        result = await model_with_tools.ainvoke(state["messages"])
        return {"messages": [result]}

    workflow.add_node("agent", agent_node)

    def tool_node(state: DeepAgentState):
        tool_calls = state["messages"][-1].tool_calls
        tool_messages = []
        state_updates = {}
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_to_execute = next(
                (t for t in all_tools if getattr(t, "name", None) == tool_name), None
            )
            if tool_to_execute:
                tool_input = tool_call["args"].copy()
                
                sig = inspect.signature(getattr(tool_to_execute, "func", tool_to_execute))
                if "state" in sig.parameters:
                    tool_input["state"] = DeepAgentState(**state)

                result = tool_to_execute.invoke(tool_input)

                if isinstance(result, dict):
                    state_updates.update(result)
                    tool_messages.append(
                        ToolMessage(
                            content=f"Tool {tool_call['name']} executed successfully.",
                            tool_call_id=tool_call["id"],
                        )
                    )
                else:
                    tool_messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                    )
            else:
                tool_messages.append(
                    ToolMessage(
                        content=f"Error: Tool '{tool_call['name']}' not found.",
                        tool_call_id=tool_call["id"],
                    )
                )
        return {**state_updates, "messages": tool_messages}

    workflow.add_node("tools", tool_node)

    def should_continue(state: DeepAgentState):
        if not state["messages"] or isinstance(state["messages"][-1], ToolMessage):
            return "agent"
        if getattr(state["messages"][-1], "tool_calls", None):
            return "tools"
        return END

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"agent": "agent", "tools": "tools", END: END},
    )
    workflow.add_edge("tools", "agent")
    workflow.set_entry_point("agent")

    return workflow.compile()

if __name__ == "__main__":
    from app.config import settings
    # Define your agents
    agents = [
        SubAgent(
            name="researcher",
            description="This agent is responsible for conducting research and gathering information.",
            prompt="You are a research agent. Your goal is to find and synthesize information on a given topic.",
            tools=[]
        ),
        SubAgent(
            name="writer",
            description="This agent is responsible for writing content based on the research provided.",
            prompt="You are a writer. Your goal is to create a well-written piece of content based on the provided information.",
            tools=[]
        ),
    ]

    # Create the team
    llm_manager = LLMManager(settings)
    team = Team(agents, llm_manager)

    # Create the graph
    graph = team.create_graph()

    # Run the graph
    initial_state = {
        "messages": [HumanMessage(content="Write a blog post about the latest advancements in AI.")]
    }

    for event in graph.stream(initial_state, {"recursion_limit": 100}):
        print(event)
