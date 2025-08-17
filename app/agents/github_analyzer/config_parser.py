"""Configuration Parser Module.

Extracts AI-related configurations from various file formats.
Supports env files, JSON, YAML, TOML, and Python configs.
"""

import json
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.logging_config import central_logger as logger


class ConfigurationExtractor:
    """Extracts AI configurations from files."""
    
    def __init__(self):
        """Initialize configuration patterns."""
        self.ai_keys = self._init_ai_keys()
        self.parsers = self._init_parsers()
    
    def _init_ai_keys(self) -> List[str]:
        """Initialize AI-related configuration keys."""
        api_keys = self._get_api_keys()
        model_keys = self._get_model_keys()
        param_keys = self._get_param_keys()
        endpoint_keys = self._get_endpoint_keys()
        feature_keys = self._get_feature_keys()
        limit_keys = self._get_limit_keys()
        return api_keys + model_keys + param_keys + endpoint_keys + feature_keys + limit_keys
    
    def _get_api_keys(self) -> List[str]:
        """Get API key patterns."""
        return [
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CLAUDE_API_KEY",
            "HUGGINGFACE_TOKEN", "COHERE_API_KEY", "AI21_API_KEY",
            "REPLICATE_API_TOKEN", "AZURE_OPENAI_KEY"
        ]
    
    def _get_model_keys(self) -> List[str]:
        """Get model configuration keys."""
        return [
            "MODEL", "MODEL_NAME", "LLM_MODEL", "AI_MODEL",
            "GPT_MODEL", "CLAUDE_MODEL", "DEFAULT_MODEL"
        ]
    
    def _get_param_keys(self) -> List[str]:
        """Get parameter keys."""
        return [
            "TEMPERATURE", "MAX_TOKENS", "TOP_P", "TOP_K",
            "FREQUENCY_PENALTY", "PRESENCE_PENALTY",
            "MAX_LENGTH", "MIN_LENGTH", "BEAM_SIZE"
        ]
    
    def _get_endpoint_keys(self) -> List[str]:
        """Get endpoint configuration keys."""
        return [
            "API_ENDPOINT", "LLM_ENDPOINT", "OPENAI_BASE_URL",
            "AZURE_ENDPOINT", "API_BASE", "BASE_URL"
        ]
    
    def _get_feature_keys(self) -> List[str]:
        """Get feature configuration keys."""
        return [
            "STREAMING", "FUNCTION_CALLING", "EMBEDDINGS",
            "VECTOR_STORE", "MEMORY_TYPE", "CHAIN_TYPE"
        ]
    
    def _get_limit_keys(self) -> List[str]:
        """Get limit configuration keys."""
        return [
            "RATE_LIMIT", "TOKEN_LIMIT", "REQUEST_TIMEOUT",
            "MAX_RETRIES", "BATCH_SIZE"
        ]
    
    def _init_parsers(self) -> Dict[str, callable]:
        """Initialize file parsers."""
        return {
            ".env": self._parse_env,
            ".json": self._parse_json,
            ".yaml": self._parse_yaml,
            ".yml": self._parse_yaml,
            ".toml": self._parse_toml,
            ".py": self._parse_python,
            ".js": self._parse_javascript,
            ".ts": self._parse_javascript
        }
    
    async def extract_configurations(
        self, 
        repo_path: str
    ) -> Dict[str, Any]:
        """Extract all AI configurations."""
        repo = Path(repo_path)
        configs = self._init_config_structure()
        config_files = await self._find_config_files(repo)
        await self._process_config_files(configs, config_files)
        configs["summary"] = self._generate_summary(configs)
        return configs
    
    def _init_config_structure(self) -> Dict[str, Any]:
        """Initialize configuration data structure."""
        return {
            "env_variables": {},
            "config_files": [],
            "inline_configs": [],
            "summary": {}
        }
    
    async def _process_config_files(
        self, 
        configs: Dict[str, Any], 
        config_files: List[Path]
    ) -> None:
        """Process all configuration files."""
        for file_path in config_files:
            file_configs = await self._extract_from_file(file_path)
            if file_configs:
                self._merge_configs(configs, file_configs, str(file_path))
    
    async def _find_config_files(self, repo: Path) -> List[Path]:
        """Find all configuration files."""
        config_files = []
        patterns = self._get_config_patterns()
        for pattern in patterns:
            found_files = self._find_files_by_pattern(repo, pattern)
            config_files.extend(found_files)
        return config_files
    
    def _get_config_patterns(self) -> List[str]:
        """Get configuration file patterns."""
        return [
            "**/.env*", "**/config.*", "**/settings.*",
            "**/*config.json", "**/*config.yaml", "**/*config.yml",
            "**/pyproject.toml", "**/package.json", "**/requirements.txt"
        ]
    
    def _find_files_by_pattern(self, repo: Path, pattern: str) -> List[Path]:
        """Find files matching a specific pattern."""
        found_files = []
        for file_path in repo.glob(pattern):
            if file_path.is_file():
                found_files.append(file_path)
        return found_files
    
    async def _extract_from_file(
        self, 
        file_path: Path
    ) -> Optional[Dict[str, Any]]:
        """Extract configurations from a file."""
        suffix = file_path.suffix.lower()
        if suffix not in self.parsers:
            return None
        return await self._parse_file_content(file_path, suffix)
    
    async def _parse_file_content(
        self, 
        file_path: Path, 
        suffix: str
    ) -> Optional[Dict[str, Any]]:
        """Parse file content using appropriate parser."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            parser = self.parsers[suffix]
            return await parser(content)
        except Exception as e:
            logger.warning(f"Error parsing {file_path}: {e}")
            return None
    
    async def _parse_env(self, content: str) -> Dict[str, Any]:
        """Parse .env file."""
        configs = {}
        lines = content.split('\n')
        for line in lines:
            processed_config = self._process_env_line(line)
            if processed_config:
                configs.update(processed_config)
        return configs
    
    def _process_env_line(self, line: str) -> Optional[Dict[str, str]]:
        """Process a single environment line."""
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            return None
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip().strip('"\'')
        if self._is_ai_config(key):
            return {key: self._mask_sensitive(key, value)}
        return None
    
    async def _parse_json(self, content: str) -> Dict[str, Any]:
        """Parse JSON configuration."""
        try:
            data = json.loads(content)
            return self._extract_ai_configs(data)
        except json.JSONDecodeError:
            return {}
    
    async def _parse_yaml(self, content: str) -> Dict[str, Any]:
        """Parse YAML configuration."""
        configs = {}
        lines = content.split('\n')
        for line in lines:
            processed_config = self._process_yaml_line(line)
            if processed_config:
                configs.update(processed_config)
        return configs
    
    def _process_yaml_line(self, line: str) -> Optional[Dict[str, str]]:
        """Process a single YAML line."""
        if ':' not in line or line.strip().startswith('#'):
            return None
        parts = line.split(':', 1)
        if len(parts) != 2:
            return None
        key, value = parts[0].strip(), parts[1].strip()
        if self._is_ai_config(key):
            return {key: self._mask_sensitive(key, value)}
        return None
    
    async def _parse_toml(self, content: str) -> Dict[str, Any]:
        """Parse TOML configuration."""
        configs = {}
        lines = content.split('\n')
        
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip('"\'')
                    
                    if self._is_ai_config(key):
                        configs[key] = self._mask_sensitive(key, value)
        
        return configs
    
    async def _parse_python(self, content: str) -> Dict[str, Any]:
        """Parse Python configuration."""
        configs = {}
        
        # Look for configuration assignments
        pattern = r'(\w+)\s*=\s*["\']([^"\']+)["\']'
        matches = re.findall(pattern, content)
        
        for key, value in matches:
            if self._is_ai_config(key):
                configs[key] = self._mask_sensitive(key, value)
        
        # Look for dictionary configs
        dict_pattern = r'["\'](\w+)["\']\s*:\s*["\']([^"\']+)["\']'
        dict_matches = re.findall(dict_pattern, content)
        
        for key, value in dict_matches:
            if self._is_ai_config(key):
                configs[key] = self._mask_sensitive(key, value)
        
        return configs
    
    async def _parse_javascript(self, content: str) -> Dict[str, Any]:
        """Parse JavaScript/TypeScript configuration."""
        configs = {}
        
        # Look for configuration assignments
        patterns = [
            r'const\s+(\w+)\s*=\s*["\']([^"\']+)["\']',
            r'let\s+(\w+)\s*=\s*["\']([^"\']+)["\']',
            r'(\w+):\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for key, value in matches:
                if self._is_ai_config(key):
                    configs[key] = self._mask_sensitive(key, value)
        
        return configs
    
    def _extract_ai_configs(self, data: Any) -> Dict[str, Any]:
        """Extract AI configs from nested structure."""
        configs = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                if self._is_ai_config(key):
                    configs[key] = self._mask_sensitive(key, str(value))
                elif isinstance(value, dict):
                    nested = self._extract_ai_configs(value)
                    configs.update(nested)
        
        return configs
    
    def _is_ai_config(self, key: str) -> bool:
        """Check if key is AI-related."""
        key_upper = key.upper()
        
        # Check exact matches
        if key_upper in self.ai_keys:
            return True
        
        # Check partial matches
        ai_keywords = [
            "OPENAI", "ANTHROPIC", "CLAUDE", "GPT",
            "LLM", "MODEL", "TOKEN", "EMBEDDING",
            "VECTOR", "CHAIN", "AGENT", "PROMPT"
        ]
        
        return any(keyword in key_upper for keyword in ai_keywords)
    
    def _mask_sensitive(self, key: str, value: str) -> str:
        """Mask sensitive values."""
        if "KEY" in key.upper() or "TOKEN" in key.upper():
            if len(value) > 8:
                return value[:4] + "****" + value[-4:]
            else:
                return "****"
        return value
    
    def _merge_configs(
        self, 
        main_configs: Dict[str, Any],
        file_configs: Dict[str, Any],
        file_path: str
    ) -> None:
        """Merge file configs into main configs."""
        if file_configs:
            main_configs["config_files"].append({
                "file": file_path,
                "configs": file_configs
            })
            
            # Update env variables
            for key, value in file_configs.items():
                if key not in main_configs["env_variables"]:
                    main_configs["env_variables"][key] = []
                main_configs["env_variables"][key].append({
                    "value": value,
                    "source": file_path
                })
    
    def _generate_summary(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate configuration summary."""
        return {
            "total_config_files": len(configs["config_files"]),
            "unique_variables": len(configs["env_variables"]),
            "has_api_keys": any(
                "KEY" in k or "TOKEN" in k 
                for k in configs["env_variables"]
            ),
            "detected_providers": self._detect_providers(configs["env_variables"])
        }
    
    def _detect_providers(self, env_vars: Dict[str, Any]) -> List[str]:
        """Detect AI providers from variables."""
        providers = set()
        
        for key in env_vars:
            key_upper = key.upper()
            if "OPENAI" in key_upper:
                providers.add("openai")
            elif "ANTHROPIC" in key_upper or "CLAUDE" in key_upper:
                providers.add("anthropic")
            elif "HUGGINGFACE" in key_upper:
                providers.add("huggingface")
            elif "COHERE" in key_upper:
                providers.add("cohere")
        
        return list(providers)