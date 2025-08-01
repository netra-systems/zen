# fast_mcp_consolidated_v2.py
#
# This file contains the complete, consolidated code for the Fast-MCP 2.0 system.
# Version 2 introduces a more advanced agentic architecture with deep observability
# using LangGraph and LangFuse, and an async-first server design.
#
# https://gemini.google.com/u/0/app/beb4fcff1b938dc4

import logging
import sys
import socket
import json
import os
import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict, Annotated, List, Union, Optional
from operator import itemgetter

# --- Core Dependencies ---
# Ensure these are installed:
# pip install langfuse langgraph langchain langchain_anthropic langchain_community langchain_core tavily-python
try:
    import langfuse
    from langfuse.decorators import observe
    from langfuse.model import CreateTrace, CreateSpan

    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolNode, tools_condition

    from langchain_core.messages import (
        BaseMessage,
        HumanMessage,
        ToolMessage,
        AIMessage,
    )
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_anthropic import ChatAnthropic
    from langchain_community.tools.tavily_search import TavilySearchResults

except ImportError:
    print(
        "Please install all required libraries: "
        "pip install langfuse langgraph langchain langchain_anthropic "
        "langchain_community langchain_core tavily-python"
    )
    sys.exit(1)


# ==============================================================================
# Section 1: Logger
# ==============================================================================

def setup_logger(name, level='INFO'):
    """Sets up a consistent logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

# ==============================================================================
# Section 2: Core Tooling Infrastructure
# ==============================================================================

class BaseTool(ABC):
    """Abstract base class for all tools."""
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the tool does and its parameters."""
        pass

    @abstractmethod
    def execute(self, params: dict) -> dict:
        """Main execution logic of the tool."""
        pass

class ToolManager:
    """Manages the loading and execution of tools."""
    def __init__(self):
        self.tools = {}
        self.logger = setup_logger(__name__)

    def register_tool(self, tool: BaseTool):
        """Registers a new tool."""
        if not isinstance(tool, BaseTool):
            raise TypeError("Tool must be an instance of BaseTool")
        if tool.name in self.tools:
            self.logger.warning(f"Overwriting tool: {tool.name}")
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieves a tool by name."""
        return self.tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """Returns a list of all registered tool instances."""
        return list(self.tools.values())

    def get_tool_schemas_for_agent(self) -> List[dict]:
        """Returns a list of tool schemas formatted for an agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    # Basic schema inference; can be expanded
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
            for tool in self.tools.values()
        ]

# ==============================================================================
# Section 3: System Tools
# ==============================================================================

class ExampleTool(BaseTool):
    """An example tool that demonstrates the basic structure."""
    @property
    def name(self):
        return "example_tool"

    @property
    def description(self):
        return "An example tool that returns a simple hello message. Params: {'name': 'your_name'}"

    @observe()
    def execute(self, params):
        langfuse.span(name="execute-example-tool-span", input=params)
        name = params.get('name', 'World')
        output = {'message': f'Hello, {name}!'}
        langfuse.span(name="execute-example-tool-span").update(output=output)
        return output

class NetraTool(BaseTool):
    """A tool that integrates with the (mocked) Netra Core Generation 1 services."""
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger(__name__, self.config.get('log_level', 'INFO'))
        self.logger.info("NetraTool initialized.")

    @property
    def name(self):
        return "netra"

    @property
    def description(self):
        return "Interfaces with Netra services. Use sub-tools: getSystemRecommendations, applySystemRecommendations, findModelCalls, refactorForMiddleware."

    @observe()
    def execute(self, params):
        sub_tool = params.get('sub_tool')
        span = langfuse.span(name=f"netra-sub-tool-{sub_tool}", input=params)

        if not sub_tool:
            raise ValueError("Missing 'sub_tool' parameter.")

        if sub_tool == 'getSystemRecommendations':
            result = self._get_system_recommendations(params)
        elif sub_tool == 'applySystemRecommendations':
            result = self._apply_system_recommendations(params)
        else:
            raise ValueError(f"Unknown sub-tool: {sub_tool}")

        span.update(output=result)
        return result

    def _get_system_recommendations(self, params):
        app_id = params.get('appId')
        if not app_id:
            raise ValueError("Missing 'appId' parameter.")
        return {"status": "success", "recommendations": f"System recommendations for app ID: {app_id}"}

    def _apply_system_recommendations(self, params):
        app_id = params.get('appId')
        if not app_id:
            raise ValueError("Missing 'appId' parameter.")
        return {"status": "success", "message": f"Applied recommendations for app ID: {app_id}"}


# ==============================================================================
# Section 4: Advanced Agent Tool using LangGraph
# ==============================================================================

class AgentState(TypedDict):
    """Represents the state of our agent graph."""
    messages: Annotated[list, add_messages]

class AgentTool(BaseTool):
    """A sophisticated agent that can use other tools to answer questions."""
    def __init__(self, tool_manager: ToolManager):
        self.tool_manager = tool_manager
        self.graph = self._build_graph()
        self.logger = setup_logger(__name__)

    @property
    def name(self):
        return "agent_tool"

    @property
    def description(self):
        return "A powerful agent that can reason and use other system tools to answer complex questions."

    def _build_graph(self):
        """Constructs the LangGraph agent."""
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant. You have access to the following tools. "
                    "Only use the tools if necessary. If you can answer directly, do so.\n\n{tools}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        llm = ChatAnthropic(model="claude-3-haiku-20240307")
        
        # Bind the tools to the LLM
        agent_llm = llm.bind_tools(self.tool_manager.get_all_tools())

        # Define the agent node
        def agent_node(state):
            self.logger.info("Agent Node: Calling model...")
            response = agent_llm.invoke(state["messages"])
            return {"messages": [response]}

        # Define the tool node
        tool_node = ToolNode(self.tool_manager.get_all_tools())

        # Build the graph
        graph_builder = StateGraph(AgentState)
        graph_builder.add_node("agent", agent_node)
        graph_builder.add_node("tools", tool_node)

        graph_builder.set_entry_point("agent")
        graph_builder.add_conditional_edges(
            "agent",
            tools_condition,
        )
        graph_builder.add_edge("tools", "agent")
        return graph_builder.compile()

    @observe()
    def execute(self, params):
        """Executes the agent graph."""
        prompt = params.get("prompt")
        if not prompt:
            raise ValueError("Missing 'prompt' parameter for the agent.")

        self.logger.info(f"Agent executing with prompt: {prompt}")
        span = langfuse.span(name="agent-execution", input=params)

        final_state = self.graph.invoke({"messages": [HumanMessage(content=prompt)]})
        
        final_response = final_state['messages'][-1].content
        self.logger.info(f"Agent finished with response: {final_response}")
        span.update(output={"response": final_response})

        return {"response": final_response}


# ==============================================================================
# Section 5: Async Server and Request Handling
# ==============================================================================

class AsyncRequestHandler:
    """Handles individual client requests asynchronously."""
    def __init__(self, tool_manager: ToolManager, config: dict, langfuse_client: Optional[langfuse.Langfuse]):
        self.tool_manager = tool_manager
        self.config = config
        self.langfuse = langfuse_client
        self.logger = setup_logger(__name__, self.config.get('log_level', 'INFO'))

    async def handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Callback for each client connection."""
        addr = writer.get_extra_info('peername')
        self.logger.info(f"Accepted connection from {addr}")
        
        trac