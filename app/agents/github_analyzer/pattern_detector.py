"""AI Pattern Detection Module.

Detects AI/LLM usage patterns in source code files.
Supports multiple languages and AI frameworks.
"""

import re
import asyncio
from typing import Dict, List, Any, Optional, Set, TypedDict
from pathlib import Path

from app.logging_config import central_logger as logger


class PatternCategory(TypedDict):
    """Type definition for pattern categories."""
    imports: List[str]
    api_calls: List[str]
    models: List[str]
    configs: List[str]


class ProviderPatterns(TypedDict):
    """Type definition for provider patterns."""
    openai: PatternCategory
    anthropic: PatternCategory
    langchain: Dict[str, List[str]]
    agents: Dict[str, List[str]]
    embeddings: Dict[str, List[str]]
    tools: Dict[str, List[str]]


class AIPatternDetector:
    """Detects AI/LLM patterns in code."""
    
    def __init__(self):
        """Initialize pattern definitions."""
        self.patterns = self._init_patterns()
        self.file_extensions = self._init_extensions()
    
    def _init_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize AI pattern definitions."""
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
    
    def _init_extensions(self) -> Set[str]:
        """Initialize supported file extensions."""
        return {
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".go", ".rs", ".rb", ".php",
            ".cs", ".cpp", ".c", ".h", ".hpp"
        }
    
    async def detect_patterns(
        self, 
        files: List[Path]
    ) -> Dict[str, Any]:
        """Detect AI patterns in files."""
        results = {
            "detected_providers": set(),
            "pattern_locations": [],
            "summary": {}
        }
        
        # Process files in batches
        batch_size = 10
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self._analyze_file(f) for f in batch]
            )
            
            for file_result in batch_results:
                if file_result:
                    self._merge_results(results, file_result)
        
        # Convert sets to lists for JSON serialization
        results["detected_providers"] = list(results["detected_providers"])
        results["summary"] = self._generate_summary(results)
        
        return results
    
    async def _analyze_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze single file for patterns."""
        if file_path.suffix not in self.file_extensions:
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return self._scan_content(content, str(file_path))
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            return None
    
    def _scan_content(
        self, 
        content: str, 
        file_path: str
    ) -> Dict[str, Any]:
        """Scan content for patterns."""
        results = {
            "file": file_path,
            "providers": set(),
            "patterns": []
        }
        
        lines = content.split('\n')
        
        for provider, categories in self.patterns.items():
            for category, pattern_list in categories.items():
                for pattern in pattern_list:
                    matches = self._find_matches(lines, pattern)
                    if matches:
                        results["providers"].add(provider)
                        for line_num, line_content in matches:
                            results["patterns"].append({
                                "provider": provider,
                                "category": category,
                                "pattern": pattern,
                                "line": line_num,
                                "content": line_content[:100]
                            })
        
        return results
    
    def _find_matches(
        self, 
        lines: List[str], 
        pattern: str
    ) -> List[tuple]:
        """Find pattern matches in lines."""
        matches = []
        regex = re.compile(pattern, re.IGNORECASE)
        
        for i, line in enumerate(lines, 1):
            if regex.search(line):
                matches.append((i, line.strip()))
        
        return matches
    
    def _merge_results(
        self, 
        main_results: Dict[str, Any], 
        file_result: Dict[str, Any]
    ) -> None:
        """Merge file results into main results."""
        main_results["detected_providers"].update(file_result["providers"])
        
        if file_result["patterns"]:
            main_results["pattern_locations"].append({
                "file": file_result["file"],
                "patterns": file_result["patterns"]
            })
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis summary."""
        pattern_counts = {}
        for location in results["pattern_locations"]:
            for pattern in location["patterns"]:
                provider = pattern["provider"]
                if provider not in pattern_counts:
                    pattern_counts[provider] = 0
                pattern_counts[provider] += 1
        
        return {
            "total_files_analyzed": len(results["pattern_locations"]),
            "providers_detected": len(results["detected_providers"]),
            "pattern_counts": pattern_counts,
            "complexity": self._estimate_complexity(pattern_counts)
        }
    
    def _estimate_complexity(self, pattern_counts: Dict[str, int]) -> str:
        """Estimate AI infrastructure complexity."""
        total_patterns = sum(pattern_counts.values())
        providers = len(pattern_counts)
        
        if total_patterns > 100 or providers > 3:
            return "high"
        elif total_patterns > 30 or providers > 1:
            return "medium"
        else:
            return "low"
    
    async def quick_scan(self, file_paths: List[str]) -> Dict[str, Any]:
        """Perform quick scan on specific files."""
        paths = [Path(p) for p in file_paths]
        return await self.detect_patterns(paths)