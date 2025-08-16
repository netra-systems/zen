"""LLM Call Mapping Module.

Maps and analyzes LLM API calls across the codebase.
Tracks models, parameters, and usage patterns.
"""

from typing import Dict, List, Any, Optional
import re
from collections import defaultdict

from app.logging_config import central_logger as logger


class LLMCallMapper:
    """Maps LLM API calls and usage."""
    
    def __init__(self):
        """Initialize mapper patterns."""
        self.call_patterns = self._init_call_patterns()
        self.model_patterns = self._init_model_patterns()
        self.param_patterns = self._init_param_patterns()
    
    def _init_call_patterns(self) -> Dict[str, List[str]]:
        """Initialize LLM call patterns."""
        return {
            "openai": [
                r"openai\.ChatCompletion\.create",
                r"openai\.Completion\.create",
                r"chat\.completions\.create",
                r"client\.chat\.completions",
                r"openai\.Embedding\.create"
            ],
            "anthropic": [
                r"anthropic\.messages\.create",
                r"client\.messages\.create",
                r"anthropic\.completions",
                r"claude\.complete"
            ],
            "langchain": [
                r"llm\.invoke",
                r"llm\.predict",
                r"chain\.run",
                r"agent\.run",
                r"llm\.generate"
            ],
            "huggingface": [
                r"pipeline\(.+\)",
                r"model\.generate",
                r"tokenizer\.encode",
                r"AutoModel\.from_pretrained"
            ]
        }
    
    def _init_model_patterns(self) -> Dict[str, str]:
        """Initialize model name patterns."""
        return {
            "gpt-4": "openai",
            "gpt-3.5": "openai",
            "text-davinci": "openai",
            "claude-3": "anthropic",
            "claude-2": "anthropic",
            "claude-instant": "anthropic",
            "llama": "meta",
            "mixtral": "mistral",
            "gemini": "google"
        }
    
    def _init_param_patterns(self) -> List[str]:
        """Initialize parameter patterns."""
        return [
            r"temperature\s*[:=]\s*([0-9.]+)",
            r"max_tokens\s*[:=]\s*(\d+)",
            r"top_p\s*[:=]\s*([0-9.]+)",
            r"top_k\s*[:=]\s*(\d+)",
            r"n\s*[:=]\s*(\d+)",
            r"stream\s*[:=]\s*(True|False|true|false)",
            r"presence_penalty\s*[:=]\s*([0-9.-]+)",
            r"frequency_penalty\s*[:=]\s*([0-9.-]+)"
        ]
    
    async def map_llm_calls(
        self, 
        patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map LLM calls from detected patterns."""
        llm_map = {
            "endpoints": [],
            "models": defaultdict(int),
            "parameters": defaultdict(list),
            "call_sites": [],
            "summary": {}
        }
        
        # Process pattern locations
        for location in patterns.get("pattern_locations", []):
            file_path = location["file"]
            
            for pattern_info in location["patterns"]:
                # Extract LLM call information
                call_info = self._extract_call_info(pattern_info, file_path)
                if call_info:
                    self._add_call_info(llm_map, call_info)
        
        # Generate summary
        llm_map["summary"] = self._generate_summary(llm_map)
        
        # Convert defaultdicts to regular dicts
        llm_map["models"] = dict(llm_map["models"])
        llm_map["parameters"] = dict(llm_map["parameters"])
        
        return llm_map
    
    def _extract_call_info(
        self, 
        pattern_info: Dict[str, Any],
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """Extract LLM call information."""
        provider = pattern_info.get("provider")
        category = pattern_info.get("category")
        content = pattern_info.get("content", "")
        line = pattern_info.get("line", 0)
        
        # Check if this is an API call
        if category not in ["api_calls", "models", "configs"]:
            return None
        
        call_info = {
            "file": file_path,
            "line": line,
            "provider": provider,
            "type": category,
            "content": content
        }
        
        # Extract model if present
        model = self._extract_model(content)
        if model:
            call_info["model"] = model
        
        # Extract parameters
        params = self._extract_parameters(content)
        if params:
            call_info["parameters"] = params
        
        return call_info
    
    def _extract_model(self, content: str) -> Optional[str]:
        """Extract model name from content."""
        # Direct model patterns
        model_patterns = [
            r"model\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"engine\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"model_name\s*[:=]\s*['\"]([^'\"]+)['\"]"
        ]
        
        for pattern in model_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Check for known model names
        for model_prefix in self.model_patterns:
            if model_prefix in content.lower():
                return model_prefix
        
        return None
    
    def _extract_parameters(self, content: str) -> Dict[str, Any]:
        """Extract parameters from content."""
        params = {}
        
        for pattern in self.param_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                param_name = pattern.split(r"\s*[:=]")[0].replace("\\", "")
                param_value = match.group(1)
                
                # Convert to appropriate type
                if param_value in ["True", "true"]:
                    params[param_name] = True
                elif param_value in ["False", "false"]:
                    params[param_name] = False
                elif "." in param_value:
                    try:
                        params[param_name] = float(param_value)
                    except:
                        params[param_name] = param_value
                else:
                    try:
                        params[param_name] = int(param_value)
                    except:
                        params[param_name] = param_value
        
        return params
    
    def _add_call_info(
        self, 
        llm_map: Dict[str, Any],
        call_info: Dict[str, Any]
    ) -> None:
        """Add call information to map."""
        # Add to endpoints
        endpoint = {
            "file": call_info["file"],
            "line": call_info["line"],
            "provider": call_info["provider"],
            "model": call_info.get("model"),
            "parameters": call_info.get("parameters", {})
        }
        llm_map["endpoints"].append(endpoint)
        
        # Update model counts
        if call_info.get("model"):
            llm_map["models"][call_info["model"]] += 1
        
        # Collect parameters
        for param, value in call_info.get("parameters", {}).items():
            llm_map["parameters"][param].append(value)
        
        # Add call site
        llm_map["call_sites"].append({
            "file": call_info["file"],
            "line": call_info["line"],
            "type": call_info["type"]
        })
    
    def _generate_summary(self, llm_map: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LLM usage summary."""
        # Calculate parameter statistics
        param_stats = {}
        for param, values in llm_map["parameters"].items():
            if values and all(isinstance(v, (int, float)) for v in values):
                param_stats[param] = {
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values)
                }
        
        return {
            "total_endpoints": len(llm_map["endpoints"]),
            "unique_models": len(llm_map["models"]),
            "most_used_model": self._get_most_used(llm_map["models"]),
            "parameter_stats": param_stats,
            "providers_used": self._get_providers(llm_map["endpoints"])
        }
    
    def _get_most_used(self, model_counts: Dict[str, int]) -> Optional[str]:
        """Get most used model."""
        if not model_counts:
            return None
        return max(model_counts, key=model_counts.get)
    
    def _get_providers(self, endpoints: List[Dict]) -> List[str]:
        """Get unique providers."""
        providers = set()
        for endpoint in endpoints:
            if endpoint.get("provider"):
                providers.add(endpoint["provider"])
        return list(providers)