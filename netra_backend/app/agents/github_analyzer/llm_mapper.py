"""LLM Call Mapping Module.

Maps and analyzes LLM API calls across the codebase.
Tracks models, parameters, and usage patterns.
"""

from typing import Dict, List, Any, Optional
import re
from collections import defaultdict

from netra_backend.app.logging_config import central_logger as logger


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
            "openai": self._get_openai_patterns(),
            "anthropic": self._get_anthropic_patterns(),
            "langchain": self._get_langchain_patterns(),
            "huggingface": self._get_huggingface_patterns()
        }

    def _get_openai_patterns(self) -> List[str]:
        """Get OpenAI API patterns."""
        return [
            r"openai\.ChatCompletion\.create",
            r"openai\.Completion\.create",
            r"chat\.completions\.create",
            r"client\.chat\.completions",
            r"openai\.Embedding\.create"
        ]

    def _get_anthropic_patterns(self) -> List[str]:
        """Get Anthropic API patterns."""
        return [
            r"anthropic\.messages\.create",
            r"client\.messages\.create",
            r"anthropic\.completions",
            r"claude\.complete"
        ]

    def _get_langchain_patterns(self) -> List[str]:
        """Get LangChain API patterns."""
        return [
            r"llm\.invoke",
            r"llm\.predict",
            r"chain\.run",
            r"agent\.run",
            r"llm\.generate"
        ]

    def _get_huggingface_patterns(self) -> List[str]:
        """Get HuggingFace API patterns."""
        return [
            r"pipeline\(.+\)",
            r"model\.generate",
            r"tokenizer\.encode",
            r"AutoModel\.from_pretrained"
        ]
    
    def _init_model_patterns(self) -> Dict[str, str]:
        """Initialize model name patterns."""
        openai_models = self._get_openai_model_mappings()
        anthropic_models = self._get_anthropic_model_mappings()
        other_models = self._get_other_model_mappings()
        return {**openai_models, **anthropic_models, **other_models}

    def _get_openai_model_mappings(self) -> Dict[str, str]:
        """Get OpenAI model mappings."""
        return {
            "gpt-4": "openai",
            "gpt-3.5": "openai",
            "text-davinci": "openai"
        }

    def _get_anthropic_model_mappings(self) -> Dict[str, str]:
        """Get Anthropic model mappings."""
        return {
            "claude-3": "anthropic",
            "claude-2": "anthropic",
            "claude-instant": "anthropic"
        }

    def _get_other_model_mappings(self) -> Dict[str, str]:
        """Get other provider model mappings."""
        return {
            "llama": "meta",
            "mixtral": "mistral",
            "gemini": "google"
        }
    
    def _init_param_patterns(self) -> List[str]:
        """Initialize parameter patterns."""
        basic_patterns = self._get_basic_param_patterns()
        advanced_patterns = self._get_advanced_param_patterns()
        return basic_patterns + advanced_patterns

    def _get_basic_param_patterns(self) -> List[str]:
        """Get basic parameter patterns."""
        return [
            r"temperature\s*[:=]\s*([0-9.]+)",
            r"max_tokens\s*[:=]\s*(\d+)",
            r"top_p\s*[:=]\s*([0-9.]+)",
            r"top_k\s*[:=]\s*(\d+)"
        ]

    def _get_advanced_param_patterns(self) -> List[str]:
        """Get advanced parameter patterns."""
        return [
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
        llm_map = self._create_empty_llm_map()
        self._process_pattern_locations(llm_map, patterns)
        self._finalize_llm_map(llm_map)
        return llm_map

    def _create_empty_llm_map(self) -> Dict[str, Any]:
        """Create empty LLM map structure."""
        return {
            "endpoints": [],
            "models": defaultdict(int),
            "parameters": defaultdict(list),
            "call_sites": [],
            "summary": {}
        }

    def _process_pattern_locations(self, llm_map: Dict[str, Any], patterns: Dict[str, Any]) -> None:
        """Process pattern locations and extract call info."""
        for location in patterns.get("pattern_locations", []):
            file_path = location["file"]
            for pattern_info in location["patterns"]:
                call_info = self._extract_call_info(pattern_info, file_path)
                if call_info:
                    self._add_call_info(llm_map, call_info)

    def _finalize_llm_map(self, llm_map: Dict[str, Any]) -> None:
        """Finalize LLM map with summary and conversions."""
        llm_map["summary"] = self._generate_summary(llm_map)
        llm_map["models"] = dict(llm_map["models"])
        llm_map["parameters"] = dict(llm_map["parameters"])
    
    def _extract_call_info(
        self, 
        pattern_info: Dict[str, Any],
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """Extract LLM call information."""
        if not self._is_valid_api_call(pattern_info):
            return None
        return self._build_enriched_call_info(pattern_info, file_path)

    def _build_enriched_call_info(self, pattern_info: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Build and enrich call information."""
        call_info = self._create_base_call_info(pattern_info, file_path)
        self._enrich_call_info(call_info)
        return call_info

    def _is_valid_api_call(self, pattern_info: Dict[str, Any]) -> bool:
        """Check if pattern info represents a valid API call."""
        category = pattern_info.get("category")
        return category in ["api_calls", "models", "configs"]

    def _create_base_call_info(self, pattern_info: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Create base call info structure."""
        return {
            "file": file_path,
            "line": pattern_info.get("line", 0),
            "provider": pattern_info.get("provider"),
            "type": pattern_info.get("category"),
            "content": pattern_info.get("content", "")
        }

    def _enrich_call_info(self, call_info: Dict[str, Any]) -> None:
        """Enrich call info with model and parameters."""
        content = call_info["content"]
        model = self._extract_model(content)
        if model:
            call_info["model"] = model
        params = self._extract_parameters(content)
        if params:
            call_info["parameters"] = params
    
    def _extract_model(self, content: str) -> Optional[str]:
        """Extract model name from content."""
        direct_model = self._extract_direct_model(content)
        if direct_model:
            return direct_model
        return self._find_known_model(content)
    
    def _extract_direct_model(self, content: str) -> Optional[str]:
        """Extract model from direct patterns."""
        patterns = self._get_model_extraction_patterns()
        return self._search_model_patterns(content, patterns)

    def _get_model_extraction_patterns(self) -> List[str]:
        """Get model extraction patterns."""
        return [
            r"model\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"engine\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"model_name\s*[:=]\s*['\"]([^'\"]+)['\"]"
        ]

    def _search_model_patterns(self, content: str, patterns: List[str]) -> Optional[str]:
        """Search content for model patterns."""
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _find_known_model(self, content: str) -> Optional[str]:
        """Find known model names in content."""
        content_lower = content.lower()
        for model_prefix in self.model_patterns:
            if model_prefix in content_lower:
                return model_prefix
        return None
    
    def _extract_parameters(self, content: str) -> Dict[str, Any]:
        """Extract parameters from content."""
        params = {}
        for pattern in self.param_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                param_name, param_value = self._process_param_match(pattern, match)
                params[param_name] = self._convert_param_value(param_value)
        return params

    def _process_param_match(self, pattern: str, match) -> tuple:
        """Process parameter match to extract name and value."""
        param_name = pattern.split(r"\s*[:=]")[0].replace("\\", "")
        param_value = match.group(1)
        return param_name, param_value

    def _convert_param_value(self, param_value: str) -> Any:
        """Convert parameter value to appropriate type."""
        bool_value = self._try_convert_bool(param_value)
        if bool_value is not None:
            return bool_value
        return self._convert_numeric_value(param_value)

    def _try_convert_bool(self, param_value: str) -> Optional[bool]:
        """Try to convert parameter value to boolean."""
        if param_value in ["True", "true"]:
            return True
        elif param_value in ["False", "false"]:
            return False
        return None

    def _convert_numeric_value(self, param_value: str) -> Any:
        """Convert parameter value to numeric type."""
        if "." in param_value:
            return self._try_parse_float(param_value)
        else:
            return self._try_parse_int(param_value)

    def _try_parse_float(self, value: str) -> Any:
        """Try to parse value as float."""
        try:
            return float(value)
        except:
            return value

    def _try_parse_int(self, value: str) -> Any:
        """Try to parse value as int."""
        try:
            return int(value)
        except:
            return value
    
    def _add_call_info(
        self, 
        llm_map: Dict[str, Any],
        call_info: Dict[str, Any]
    ) -> None:
        """Add call information to map."""
        self._add_endpoint_info(llm_map, call_info)
        self._update_call_statistics(llm_map, call_info)

    def _update_call_statistics(self, llm_map: Dict[str, Any], call_info: Dict[str, Any]) -> None:
        """Update call statistics in map."""
        self._update_model_counts(llm_map, call_info)
        self._collect_parameters(llm_map, call_info)
        self._add_call_site(llm_map, call_info)

    def _add_endpoint_info(self, llm_map: Dict[str, Any], call_info: Dict[str, Any]) -> None:
        """Add endpoint information to map."""
        endpoint = self._create_endpoint_entry(call_info)
        llm_map["endpoints"].append(endpoint)

    def _create_endpoint_entry(self, call_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create endpoint entry from call info."""
        return {
            "file": call_info["file"],
            "line": call_info["line"],
            "provider": call_info["provider"],
            "model": call_info.get("model"),
            "parameters": call_info.get("parameters", {})
        }

    def _update_model_counts(self, llm_map: Dict[str, Any], call_info: Dict[str, Any]) -> None:
        """Update model usage counts."""
        if call_info.get("model"):
            llm_map["models"][call_info["model"]] += 1

    def _collect_parameters(self, llm_map: Dict[str, Any], call_info: Dict[str, Any]) -> None:
        """Collect parameter values."""
        for param, value in call_info.get("parameters", {}).items():
            llm_map["parameters"][param].append(value)

    def _add_call_site(self, llm_map: Dict[str, Any], call_info: Dict[str, Any]) -> None:
        """Add call site information."""
        llm_map["call_sites"].append({
            "file": call_info["file"],
            "line": call_info["line"],
            "type": call_info["type"]
        })
    
    def _generate_summary(self, llm_map: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LLM usage summary."""
        param_stats = self._calculate_parameter_statistics(llm_map["parameters"])
        return self._build_summary_data(llm_map, param_stats)

    def _calculate_parameter_statistics(self, parameters: Dict[str, List]) -> Dict[str, Dict[str, float]]:
        """Calculate parameter statistics."""
        param_stats = {}
        for param, values in parameters.items():
            if self._has_numeric_values(values):
                param_stats[param] = self._compute_stats(values)
        return param_stats

    def _has_numeric_values(self, values: List) -> bool:
        """Check if values are numeric."""
        return values and all(isinstance(v, (int, float)) for v in values)

    def _compute_stats(self, values: List[float]) -> Dict[str, float]:
        """Compute min, max, and average statistics."""
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values)
        }

    def _build_summary_data(self, llm_map: Dict[str, Any], param_stats: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Build summary data structure."""
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