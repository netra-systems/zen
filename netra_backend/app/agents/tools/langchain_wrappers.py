"""LangChain tool wrappers for Netra platform tools.

This module provides LangChain-compatible wrappers for the platform's tools,
enabling integration with LangChain agents and chains.

Date Created: 2025-01-29
Last Updated: 2025-01-29

Business Value: Enables seamless integration of platform tools with LangChain-based agents.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.tools.data_helper import DataHelper
from netra_backend.app.tools.deep_research_api import DeepResearchAPI
from netra_backend.app.tools.reliability_scorer import ReliabilityScorer
from netra_backend.app.tools.sandboxed_interpreter import SandboxedInterpreter

logger = central_logger.get_logger(__name__)


# ===========================
# Input Schema Definitions
# ===========================

class DataHelperInput(BaseModel):
    """Input schema for DataHelper tool."""
    user_request: str = Field(description="The original user request to analyze")
    triage_result: str = Field(default="", description="Results from triage agent")
    previous_results: str = Field(default="", description="Previous agent results if available")


class DeepResearchInput(BaseModel):
    """Input schema for DeepResearch tool."""
    query: str = Field(description="The search query")
    source_types: List[str] = Field(default_factory=list, description="Types of sources to search")
    max_results: int = Field(default=10, description="Maximum number of results")
    require_dates: bool = Field(default=False, description="Whether to require publication dates")
    domains: List[str] = Field(default_factory=list, description="Specific domains to search")


class ReliabilityScorerInput(BaseModel):
    """Input schema for ReliabilityScorer tool."""
    results: str = Field(description="JSON string of search results to score")


class SandboxedInterpreterInput(BaseModel):
    """Input schema for SandboxedInterpreter tool."""
    code: str = Field(description="Python code to execute")
    timeout_ms: int = Field(default=10000, description="Execution timeout in milliseconds")


# ===========================
# LangChain Tool Wrappers
# ===========================

class DataHelperTool(BaseTool):
    """LangChain wrapper for DataHelper tool."""
    
    name: str = "data_helper"
    description: str = """Generates prompts to request additional data from users when insufficient 
    data is available for optimization. Use this when you need to collect more information from 
    the user to provide comprehensive optimization strategies."""
    args_schema: Type[BaseModel] = DataHelperInput
    
    llm_manager: Optional[LLMManager] = None
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, **kwargs):
        """Initialize with optional LLM manager."""
        super().__init__(**kwargs)
        self.llm_manager = llm_manager
        self._tool = None
    
    def _get_tool(self) -> DataHelper:
        """Get or create the DataHelper instance."""
        if self._tool is None:
            if self.llm_manager is None:
                logger.warning("🚨 DataHelperTool: No LLM manager provided, creating default")
                from netra_backend.app.llm.llm_manager import LLMManager
                self.llm_manager = LLMManager()
            self._tool = DataHelper(self.llm_manager)
        return self._tool
    
    def _run(self, user_request: str, triage_result: str = "", previous_results: str = "") -> str:
        """Synchronous execution of DataHelper."""
        logger.info(f"🔧 DataHelperTool executed for user request: {user_request[:100]}")
        
        try:
            # Parse previous results if provided
            prev_results_list = []
            if previous_results:
                try:
                    prev_results_list = json.loads(previous_results)
                except json.JSONDecodeError:
                    prev_results_list = [{"result": previous_results}]
            
            # Parse triage result
            triage_dict = {}
            if triage_result:
                try:
                    triage_dict = json.loads(triage_result)
                except json.JSONDecodeError:
                    triage_dict = {"raw": triage_result}
            
            # Run async method in sync context
            result = asyncio.run(
                self._get_tool().generate_data_request(
                    user_request=user_request,
                    triage_result=triage_dict,
                    previous_results=prev_results_list if prev_results_list else None
                )
            )
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"❌ DataHelperTool error: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "data_request": f"Please provide more details about: {user_request[:50]}",
                "suggested_questions": [
                    "What is your current AI infrastructure?",
                    "What are your monthly AI costs?",
                    "What are your optimization goals?"
                ]
            })
    
    async def _arun(self, user_request: str, triage_result: str = "", previous_results: str = "") -> str:
        """Asynchronous execution of DataHelper."""
        logger.info(f"🔧 DataHelperTool async executed for user request: {user_request[:100]}")
        
        try:
            # Parse previous results if provided
            prev_results_list = []
            if previous_results:
                try:
                    prev_results_list = json.loads(previous_results)
                except json.JSONDecodeError:
                    prev_results_list = [{"result": previous_results}]
            
            # Parse triage result
            triage_dict = {}
            if triage_result:
                try:
                    triage_dict = json.loads(triage_result)
                except json.JSONDecodeError:
                    triage_dict = {"raw": triage_result}
            
            result = await self._get_tool().generate_data_request(
                user_request=user_request,
                triage_result=triage_dict,
                previous_results=prev_results_list if prev_results_list else None
            )
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"❌ DataHelperTool async error: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "data_request": f"Please provide more details about: {user_request[:50]}"
            })


class DeepResearchTool(BaseTool):
    """LangChain wrapper for DeepResearch API tool."""
    
    name: str = "deep_research"
    description: str = """Searches for verified, up-to-date information using Deep Research API. 
    Use this to find reliable sources, documentation, and recent information about AI services, 
    pricing, and optimization strategies."""
    args_schema: Type[BaseModel] = DeepResearchInput
    
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        """Initialize with optional API configuration."""
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url
        self._tool = None
    
    def _get_tool(self) -> DeepResearchAPI:
        """Get or create the DeepResearchAPI instance."""
        if self._tool is None:
            self._tool = DeepResearchAPI(api_key=self.api_key, base_url=self.base_url)
        return self._tool
    
    def _run(self, query: str, source_types: List[str] = None, max_results: int = 10,
             require_dates: bool = False, domains: List[str] = None) -> str:
        """Synchronous execution of DeepResearch."""
        logger.info(f"🔍 DeepResearchTool executed for query: {query[:100]}")
        
        try:
            params = {
                "query": query,
                "source_types": source_types or [],
                "max_results": max_results,
                "require_dates": require_dates,
                "domains": domains or []
            }
            
            # Run async method in sync context
            results = asyncio.run(self._get_tool().search(params))
            
            return json.dumps({
                "status": "success",
                "results": results,
                "query": query,
                "result_count": len(results)
            })
        except Exception as e:
            logger.error(f"❌ DeepResearchTool error: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "results": [],
                "query": query
            })
    
    async def _arun(self, query: str, source_types: List[str] = None, max_results: int = 10,
                    require_dates: bool = False, domains: List[str] = None) -> str:
        """Asynchronous execution of DeepResearch."""
        logger.info(f"🔍 DeepResearchTool async executed for query: {query[:100]}")
        
        try:
            params = {
                "query": query,
                "source_types": source_types or [],
                "max_results": max_results,
                "require_dates": require_dates,
                "domains": domains or []
            }
            
            results = await self._get_tool().search(params)
            
            return json.dumps({
                "status": "success",
                "results": results,
                "query": query,
                "result_count": len(results)
            })
        except Exception as e:
            logger.error(f"❌ DeepResearchTool async error: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "results": [],
                "query": query
            })


class ReliabilityScorerTool(BaseTool):
    """LangChain wrapper for ReliabilityScorer tool."""
    
    name: str = "reliability_scorer"
    description: str = """Scores research sources based on Georgetown reliability criteria to ensure 
    95%+ accuracy. Use this to evaluate the credibility and recency of information sources."""
    args_schema: Type[BaseModel] = ReliabilityScorerInput
    
    def __init__(self, **kwargs):
        """Initialize the tool."""
        super().__init__(**kwargs)
        self._tool = None
    
    def _get_tool(self) -> ReliabilityScorer:
        """Get or create the ReliabilityScorer instance."""
        if self._tool is None:
            self._tool = ReliabilityScorer()
        return self._tool
    
    def _run(self, results: str) -> str:
        """Synchronous execution of ReliabilityScorer."""
        logger.info(f"📊 ReliabilityScorerTool executed for scoring results")
        
        try:
            # Parse results string
            results_list = []
            if results:
                try:
                    results_list = json.loads(results)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse results as JSON, treating as single result")
                    results_list = [{"content": results}]
            
            scorer = self._get_tool()
            scored_results = []
            
            for result in results_list:
                source_score = scorer.score_source(result.get("source", "unknown"))
                recency_score = scorer.score_recency(result.get("publication_date", ""))
                completeness_score = scorer.score_completeness(result)
                
                scored_results.append({
                    "result": result,
                    "scores": {
                        "source_reliability": source_score,
                        "recency": recency_score,
                        "completeness": completeness_score,
                        "overall": (source_score + recency_score + completeness_score) / 3
                    }
                })
            
            # Sort by overall score
            scored_results.sort(key=lambda x: x["scores"]["overall"], reverse=True)
            
            return json.dumps({
                "status": "success",
                "scored_results": scored_results,
                "top_score": scored_results[0]["scores"]["overall"] if scored_results else 0,
                "result_count": len(scored_results)
            })
        except Exception as e:
            logger.error(f"❌ ReliabilityScorerTool error: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "scored_results": []
            })
    
    async def _arun(self, results: str) -> str:
        """Asynchronous execution of ReliabilityScorer."""
        # ReliabilityScorer is synchronous, so we just call _run
        return self._run(results)


class SandboxedInterpreterTool(BaseTool):
    """LangChain wrapper for SandboxedInterpreter tool."""
    
    name: str = "sandboxed_interpreter"
    description: str = """Executes Python code in a secure, sandboxed environment with strict 
    resource limits. Use this for safe execution of calculations, data analysis, and optimization 
    algorithms."""
    args_schema: Type[BaseModel] = SandboxedInterpreterInput
    
    docker_image: Optional[str] = None
    
    def __init__(self, docker_image: Optional[str] = None, **kwargs):
        """Initialize with optional Docker image."""
        super().__init__(**kwargs)
        self.docker_image = docker_image
        self._tool = None
    
    def _get_tool(self) -> SandboxedInterpreter:
        """Get or create the SandboxedInterpreter instance."""
        if self._tool is None:
            self._tool = SandboxedInterpreter(docker_image=self.docker_image)
        return self._tool
    
    def _run(self, code: str, timeout_ms: int = 10000) -> str:
        """Synchronous execution of SandboxedInterpreter."""
        logger.info(f"💻 SandboxedInterpreterTool executed for code execution")
        
        try:
            # Run async method in sync context
            result = asyncio.run(
                self._get_tool().execute(code, timeout_ms)
            )
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"❌ SandboxedInterpreterTool error: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "output": {}
            })
    
    async def _arun(self, code: str, timeout_ms: int = 10000) -> str:
        """Asynchronous execution of SandboxedInterpreter."""
        logger.info(f"💻 SandboxedInterpreterTool async executed for code execution")
        
        try:
            result = await self._get_tool().execute(code, timeout_ms)
            return json.dumps(result)
        except Exception as e:
            logger.error(f"❌ SandboxedInterpreterTool async error: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "output": {}
            })


# ===========================
# Factory Functions
# ===========================

def create_langchain_tools(
    llm_manager: Optional[LLMManager] = None,
    deep_research_api_key: Optional[str] = None,
    deep_research_base_url: Optional[str] = None,
    sandbox_docker_image: Optional[str] = None
) -> List[BaseTool]:
    """Create all LangChain-wrapped tools with optional configuration.
    
    Args:
        llm_manager: LLM manager for DataHelper tool
        deep_research_api_key: API key for Deep Research API
        deep_research_base_url: Base URL for Deep Research API
        sandbox_docker_image: Docker image for sandboxed execution
        
    Returns:
        List of configured LangChain tools
    """
    logger.info("🛠️ Creating LangChain-wrapped tools")
    
    tools = [
        DataHelperTool(llm_manager=llm_manager),
        DeepResearchTool(
            api_key=deep_research_api_key,
            base_url=deep_research_base_url
        ),
        ReliabilityScorerTool(),
        SandboxedInterpreterTool(docker_image=sandbox_docker_image)
    ]
    
    logger.info(f"✅ Created {len(tools)} LangChain tools: {[tool.name for tool in tools]}")
    return tools


def get_tool_by_name(
    name: str,
    llm_manager: Optional[LLMManager] = None,
    **kwargs
) -> Optional[BaseTool]:
    """Get a specific LangChain-wrapped tool by name.
    
    Args:
        name: Name of the tool to retrieve
        llm_manager: LLM manager for DataHelper tool
        **kwargs: Additional configuration for specific tools
        
    Returns:
        The requested tool or None if not found
    """
    tool_mapping = {
        "data_helper": DataHelperTool,
        "deep_research": DeepResearchTool,
        "reliability_scorer": ReliabilityScorerTool,
        "sandboxed_interpreter": SandboxedInterpreterTool
    }
    
    tool_class = tool_mapping.get(name)
    if tool_class is None:
        logger.warning(f"⚠️ Tool '{name}' not found in LangChain wrappers")
        return None
    
    # Create tool with appropriate parameters
    if name == "data_helper":
        return tool_class(llm_manager=llm_manager)
    elif name == "deep_research":
        return tool_class(
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url")
        )
    elif name == "sandboxed_interpreter":
        return tool_class(docker_image=kwargs.get("docker_image"))
    else:
        return tool_class()


# ===========================
# Module Exports
# ===========================

__all__ = [
    "DataHelperTool",
    "DeepResearchTool",
    "ReliabilityScorerTool",
    "SandboxedInterpreterTool",
    "create_langchain_tools",
    "get_tool_by_name",
]