"""AI Pattern Definitions Module.

Defines patterns for detecting various AI providers and frameworks.
Handles OpenAI, Anthropic, LangChain, agents, embeddings, and tools.
"""

from typing import Dict, List, Any

from netra_backend.app.logging_config import central_logger as logger


class AIPatternDefinitions:
    """Defines AI detection patterns for various providers and frameworks."""
    
    def get_all_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Get all AI pattern definitions."""
        patterns = self._get_base_patterns()
        patterns.update(self._get_extended_patterns())
        return patterns
    
    def _get_base_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Get base AI patterns."""
        return {
            "openai": self._create_openai_patterns(),
            "anthropic": self._create_anthropic_patterns(),
            "langchain": self._create_langchain_patterns()
        }
    
    def _get_extended_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Get extended AI patterns."""
        return {
            "agents": self._create_agents_patterns(),
            "embeddings": self._create_embeddings_patterns(),
            "tools": self._create_tools_patterns()
        }
    
    def _create_openai_patterns(self) -> Dict[str, List[str]]:
        """Create OpenAI detection patterns."""
        return {
            "imports": self._get_openai_imports(),
            "api_calls": self._get_openai_api_calls(),
            "models": self._get_openai_models(),
            "configs": self._get_openai_configs()
        }
    
    def _get_openai_imports(self) -> List[str]:
        """Get OpenAI import patterns."""
        return [
            r"import openai",
            r"from openai import",
            r"require\(['\"]openai",
            r"import.*OpenAI"
        ]
    
    def _get_openai_api_calls(self) -> List[str]:
        """Get OpenAI API call patterns."""
        return [
            r"openai\.ChatCompletion",
            r"openai\.Completion",
            r"chat\.completions\.create",
            r"OpenAI\(\)"
        ]
    
    def _get_openai_models(self) -> List[str]:
        """Get OpenAI model patterns."""
        return [
            r"gpt-4",
            r"gpt-3\.5-turbo",
            r"text-davinci-\d+",
            r"text-embedding-ada-\d+"
        ]
    
    def _get_openai_configs(self) -> List[str]:
        """Get OpenAI configuration patterns."""
        return [
            r"OPENAI_API_KEY",
            r"temperature\s*[:=]",
            r"max_tokens\s*[:=]",
            r"top_p\s*[:=]"
        ]
    
    def _create_anthropic_patterns(self) -> Dict[str, List[str]]:
        """Create Anthropic detection patterns."""
        return {
            "imports": self._get_anthropic_imports(),
            "api_calls": self._get_anthropic_api_calls(),
            "models": self._get_anthropic_models(),
            "configs": self._get_anthropic_configs()
        }
    
    def _get_anthropic_imports(self) -> List[str]:
        """Get Anthropic import patterns."""
        return [
            r"import anthropic",
            r"from anthropic import",
            r"require\(['\"]anthropic",
            r"import.*Anthropic"
        ]
    
    def _get_anthropic_api_calls(self) -> List[str]:
        """Get Anthropic API call patterns."""
        return [
            r"anthropic\.Client",
            r"anthropic\.Anthropic",
            r"messages\.create",
            r"completions\.create"
        ]
    
    def _get_anthropic_models(self) -> List[str]:
        """Get Anthropic model patterns."""
        return [
            r"claude-3",
            r"claude-2",
            r"claude-instant"
        ]
    
    def _get_anthropic_configs(self) -> List[str]:
        """Get Anthropic configuration patterns."""
        return [
            r"ANTHROPIC_API_KEY",
            r"CLAUDE_API_KEY",
            r"max_tokens_to_sample"
        ]
    
    def _create_langchain_patterns(self) -> Dict[str, List[str]]:
        """Create LangChain detection patterns."""
        return {
            "imports": self._get_langchain_imports(),
            "components": self._get_langchain_components(),
            "agents": self._get_langchain_agents()
        }
    
    def _get_langchain_imports(self) -> List[str]:
        """Get LangChain import patterns."""
        return [
            r"from langchain",
            r"import langchain",
            r"require\(['\"]langchain"
        ]
    
    def _get_langchain_components(self) -> List[str]:
        """Get LangChain component patterns."""
        core_components = self._get_langchain_core_components()
        chain_components = self._get_langchain_chain_components()
        return core_components + chain_components
    
    def _get_langchain_core_components(self) -> List[str]:
        """Get core LangChain components."""
        return [
            r"ChatOpenAI",
            r"ChatAnthropic",
            r"PromptTemplate",
            r"VectorStore"
        ]
    
    def _get_langchain_chain_components(self) -> List[str]:
        """Get LangChain chain components."""
        return [
            r"LLMChain",
            r"ConversationChain",
            r"RetrievalQA"
        ]
    
    def _get_langchain_agents(self) -> List[str]:
        """Get LangChain agent patterns."""
        return [
            r"create_.*_agent",
            r"AgentExecutor",
            r"initialize_agent"
        ]
    
    def _create_agents_patterns(self) -> Dict[str, List[str]]:
        """Create agent framework patterns."""
        return {
            "frameworks": self._get_agent_frameworks(),
            "patterns": self._get_agent_patterns()
        }
    
    def _get_agent_frameworks(self) -> List[str]:
        """Get agent framework patterns."""
        return [
            r"from crewai",
            r"import autogen",
            r"from agency",
            r"SuperAGI"
        ]
    
    def _get_agent_patterns(self) -> List[str]:
        """Get agent usage patterns."""
        return [
            r"class\s+\w*Agent",
            r"def execute_agent",
            r"agent\.run\(",
            r"ConversableAgent"
        ]
    
    def _create_embeddings_patterns(self) -> Dict[str, List[str]]:
        """Create embeddings detection patterns."""
        return {
            "providers": self._get_embedding_providers(),
            "vectorstores": self._get_vectorstore_patterns()
        }
    
    def _get_embedding_providers(self) -> List[str]:
        """Get embedding provider patterns."""
        return [
            r"Embeddings",
            r"embed_documents",
            r"embed_query",
            r"text-embedding"
        ]
    
    def _get_vectorstore_patterns(self) -> List[str]:
        """Get vectorstore patterns."""
        cloud_stores = self._get_cloud_vectorstores()
        local_stores = self._get_local_vectorstores()
        return cloud_stores + local_stores
    
    def _get_cloud_vectorstores(self) -> List[str]:
        """Get cloud vectorstore patterns."""
        return [
            r"Pinecone",
            r"Weaviate",
            r"Qdrant"
        ]
    
    def _get_local_vectorstores(self) -> List[str]:
        """Get local vectorstore patterns."""
        return [
            r"Chroma",
            r"FAISS"
        ]
    
    def _create_tools_patterns(self) -> Dict[str, List[str]]:
        """Create tools detection patterns."""
        return {
            "function_calling": self._get_function_calling_patterns(),
            "definitions": self._get_tool_definition_patterns()
        }
    
    def _get_function_calling_patterns(self) -> List[str]:
        """Get function calling patterns."""
        return [
            r"tools\s*=",
            r"functions\s*=",
            r"function_call",
            r"tool_calls"
        ]
    
    def _get_tool_definition_patterns(self) -> List[str]:
        """Get tool definition patterns."""
        return [
            r"@tool",
            r"Tool\(",
            r"StructuredTool",
            r"FunctionTool"
        ]