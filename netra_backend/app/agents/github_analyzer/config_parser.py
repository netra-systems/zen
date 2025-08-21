"""Configuration Parser Module.

Extracts AI-related configurations from various file formats.
Supports env files, JSON, YAML, TOML, and Python configs.
"""

import json
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional

from netra_backend.app.logging_config import central_logger as logger


class ConfigurationExtractor:
    """Extracts AI configurations from files."""
    
    def __init__(self):
        """Initialize configuration patterns."""
        self.ai_keys = self._init_ai_keys()
        self.parsers = self._init_parsers()
    
    def _init_ai_keys(self) -> List[str]:
        """Initialize AI-related configuration keys."""
        key_groups = [
            self._get_api_keys(), self._get_model_keys(), self._get_param_keys(),
            self._get_endpoint_keys(), self._get_feature_keys(), self._get_limit_keys()
        ]
        return [key for group in key_groups for key in group]
    
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
            ".env": self._parse_env, ".json": self._parse_json,
            ".yaml": self._parse_yaml, ".yml": self._parse_yaml,
            ".toml": self._parse_toml, ".py": self._parse_python,
            ".js": self._parse_javascript, ".ts": self._parse_javascript
        }
    
    async def extract_configurations(self, repo_path: str) -> Dict[str, Any]:
        """Extract all AI configurations."""
        repo = Path(repo_path)
        configs = self._init_config_structure()
        config_files = await self._find_config_files(repo)
        await self._process_config_files(configs, config_files)
        self._finalize_configs(configs)
        return configs
    
    def _finalize_configs(self, configs: Dict[str, Any]) -> None:
        """Finalize configuration extraction."""
        configs["summary"] = self._generate_summary(configs)
    
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
            await self._process_single_config_file(configs, file_path)
    
    async def _process_single_config_file(
        self, configs: Dict[str, Any], file_path: Path
    ) -> None:
        """Process a single configuration file."""
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
    
    async def _extract_from_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract configurations from a file."""
        suffix = file_path.suffix.lower()
        if suffix not in self.parsers:
            return None
        return await self._parse_file_content(file_path, suffix)
    
    async def _parse_file_content(self, file_path: Path, suffix: str) -> Optional[Dict[str, Any]]:
        """Parse file content using appropriate parser."""
        return await self._safe_parse_content(file_path, suffix)
    
    async def _safe_parse_content(self, file_path: Path, suffix: str) -> Optional[Dict[str, Any]]:
        """Safely parse file content with error handling."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return await self.parsers[suffix](content)
        except Exception as e:
            logger.warning(f"Error parsing {file_path}: {e}")
            return None
    
    async def _parse_env(self, content: str) -> Dict[str, Any]:
        """Parse .env file."""
        configs = {}
        self._process_all_env_lines(configs, content)
        return configs
    
    def _process_all_env_lines(self, configs: Dict[str, Any], content: str) -> None:
        """Process all environment file lines."""
        lines = content.split('\n')
        for line in lines:
            self._update_configs_from_env_line(configs, line)
    
    def _update_configs_from_env_line(self, configs: Dict[str, Any], line: str) -> None:
        """Update configs from a single env line."""
        processed_config = self._process_env_line(line)
        if processed_config:
            configs.update(processed_config)
    
    def _process_env_line(self, line: str) -> Optional[Dict[str, str]]:
        """Process a single environment line."""
        line = line.strip()
        if not self._is_valid_env_line(line):
            return None
        key, value = self._parse_env_line_parts(line)
        return self._create_config_if_ai(key, value)
    
    def _is_valid_env_line(self, line: str) -> bool:
        """Check if environment line is valid."""
        return line and not line.startswith('#') and '=' in line
    
    def _parse_env_line_parts(self, line: str) -> tuple[str, str]:
        """Parse key-value parts from environment line."""
        key, value = line.split('=', 1)
        return key.strip(), value.strip().strip('"\'\"')
    
    def _create_config_if_ai(self, key: str, value: str) -> Optional[Dict[str, str]]:
        """Create config entry if key is AI-related."""
        if self._is_ai_config(key):
            return {key: self._mask_sensitive(key, value)}
        return None
    
    async def _parse_json(self, content: str) -> Dict[str, Any]:
        """Parse JSON configuration."""
        return self._safe_json_parse(content)
    
    def _safe_json_parse(self, content: str) -> Dict[str, Any]:
        """Safely parse JSON content."""
        try:
            data = json.loads(content)
            return self._extract_ai_configs(data)
        except json.JSONDecodeError:
            return {}
    
    async def _parse_yaml(self, content: str) -> Dict[str, Any]:
        """Parse YAML configuration."""
        configs = {}
        self._process_all_yaml_lines(configs, content)
        return configs
    
    def _process_all_yaml_lines(self, configs: Dict[str, Any], content: str) -> None:
        """Process all YAML lines."""
        lines = content.split('\n')
        for line in lines:
            self._update_configs_from_yaml_line(configs, line)
    
    def _update_configs_from_yaml_line(self, configs: Dict[str, Any], line: str) -> None:
        """Update configs from a single YAML line."""
        processed_config = self._process_yaml_line(line)
        if processed_config:
            configs.update(processed_config)
    
    def _process_yaml_line(self, line: str) -> Optional[Dict[str, str]]:
        """Process a single YAML line."""
        if not self._is_valid_yaml_line(line):
            return None
        key, value = self._parse_yaml_line_parts(line)
        if self._is_ai_config(key):
            return {key: self._mask_sensitive(key, value)}
        return None
    
    def _is_valid_yaml_line(self, line: str) -> bool:
        """Check if YAML line is valid."""
        return ':' in line and not line.strip().startswith('#')
    
    def _parse_yaml_line_parts(self, line: str) -> tuple[str, str]:
        """Parse key-value parts from YAML line."""
        parts = line.split(':', 1)
        return parts[0].strip(), parts[1].strip() if len(parts) == 2 else ""
    
    async def _parse_toml(self, content: str) -> Dict[str, Any]:
        """Parse TOML configuration."""
        configs = {}
        self._process_all_toml_lines(configs, content)
        return configs
    
    def _process_all_toml_lines(self, configs: Dict[str, Any], content: str) -> None:
        """Process all TOML lines."""
        lines = content.split('\n')
        for line in lines:
            self._process_toml_line(configs, line)
    
    def _process_toml_line(self, configs: Dict[str, Any], line: str) -> None:
        """Process a single TOML line."""
        if not self._is_valid_toml_line(line):
            return
        self._extract_toml_config(configs, line)
    
    def _extract_toml_config(self, configs: Dict[str, Any], line: str) -> None:
        """Extract TOML configuration from line."""
        key, value = self._parse_toml_line_parts(line)
        if key and self._is_ai_config(key):
            configs[key] = self._mask_sensitive(key, value)
    
    def _is_valid_toml_line(self, line: str) -> bool:
        """Check if TOML line is valid."""
        return '=' in line and not line.strip().startswith('#')
    
    def _parse_toml_line_parts(self, line: str) -> tuple[str, str]:
        """Parse key-value parts from TOML line."""
        parts = line.split('=', 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip().strip('"\'')
        return "", ""
    
    async def _parse_python(self, content: str) -> Dict[str, Any]:
        """Parse Python configuration."""
        configs = {}
        self._extract_all_python_patterns(configs, content)
        return configs
    
    def _extract_all_python_patterns(self, configs: Dict[str, Any], content: str) -> None:
        """Extract all Python configuration patterns."""
        self._extract_python_assignments(configs, content)
        self._extract_python_dict_configs(configs, content)
    
    def _extract_python_assignments(self, configs: Dict[str, Any], content: str) -> None:
        """Extract Python assignment patterns."""
        pattern = r'(\w+)\s*=\s*["\']([^"\']+)["\']'
        matches = re.findall(pattern, content)
        self._process_python_assignment_matches(configs, matches)
    
    def _process_python_assignment_matches(self, configs: Dict[str, Any], matches: list) -> None:
        """Process Python assignment matches."""
        for key, value in matches:
            if self._is_ai_config(key):
                configs[key] = self._mask_sensitive(key, value)
    
    def _extract_python_dict_configs(self, configs: Dict[str, Any], content: str) -> None:
        """Extract Python dictionary configuration patterns."""
        dict_pattern = r'["\'](\w+)["\']\s*:\s*["\']([^"\']+)["\']'
        dict_matches = re.findall(dict_pattern, content)
        self._process_python_dict_matches(configs, dict_matches)
    
    def _process_python_dict_matches(self, configs: Dict[str, Any], dict_matches: list) -> None:
        """Process Python dictionary matches."""
        for key, value in dict_matches:
            if self._is_ai_config(key):
                configs[key] = self._mask_sensitive(key, value)
    
    async def _parse_javascript(self, content: str) -> Dict[str, Any]:
        """Parse JavaScript/TypeScript configuration."""
        configs = {}
        self._extract_all_js_patterns(configs, content)
        return configs
    
    def _extract_all_js_patterns(self, configs: Dict[str, Any], content: str) -> None:
        """Extract all JavaScript configuration patterns."""
        patterns = self._get_js_patterns()
        for pattern in patterns:
            self._extract_js_matches(configs, content, pattern)
    
    def _get_js_patterns(self) -> List[str]:
        """Get JavaScript parsing patterns."""
        return [
            r'const\s+(\w+)\s*=\s*["\']([^"\']+)["\']',
            r'let\s+(\w+)\s*=\s*["\']([^"\']+)["\']',
            r'(\w+):\s*["\']([^"\']+)["\']'
        ]
    
    def _extract_js_matches(self, configs: Dict[str, Any], content: str, pattern: str) -> None:
        """Extract matches from JavaScript content using pattern."""
        matches = re.findall(pattern, content)
        for key, value in matches:
            if self._is_ai_config(key):
                configs[key] = self._mask_sensitive(key, value)
    
    def _extract_ai_configs(self, data: Any) -> Dict[str, Any]:
        """Extract AI configs from nested structure."""
        configs = {}
        if isinstance(data, dict):
            self._process_dict_configs(configs, data)
        return configs
    
    def _process_dict_configs(self, configs: Dict[str, Any], data: Dict[str, Any]) -> None:
        """Process dictionary configurations recursively."""
        for key, value in data.items():
            if self._is_ai_config(key):
                configs[key] = self._mask_sensitive(key, str(value))
            elif isinstance(value, dict):
                nested = self._extract_ai_configs(value)
                configs.update(nested)
    
    def _is_ai_config(self, key: str) -> bool:
        """Check if key is AI-related."""
        key_upper = key.upper()
        if key_upper in self.ai_keys:
            return True
        return self._has_ai_keywords(key_upper)
    
    def _has_ai_keywords(self, key_upper: str) -> bool:
        """Check if key contains AI-related keywords."""
        ai_keywords = [
            "OPENAI", "ANTHROPIC", "CLAUDE", "GPT",
            "LLM", "MODEL", "TOKEN", "EMBEDDING",
            "VECTOR", "CHAIN", "AGENT", "PROMPT"
        ]
        return any(keyword in key_upper for keyword in ai_keywords)
    
    def _mask_sensitive(self, key: str, value: str) -> str:
        """Mask sensitive values."""
        if self._is_sensitive_key(key):
            return self._apply_masking(value)
        return value
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if key is sensitive."""
        return "KEY" in key.upper() or "TOKEN" in key.upper()
    
    def _apply_masking(self, value: str) -> str:
        """Apply masking to sensitive value."""
        if len(value) > 8:
            return value[:4] + "****" + value[-4:]
        return "****"
    
    def _merge_configs(self, main_configs: Dict[str, Any], file_configs: Dict[str, Any], file_path: str) -> None:
        """Merge file configs into main configs."""
        if not file_configs:
            return
        self._perform_config_merge(main_configs, file_configs, file_path)
    
    def _perform_config_merge(self, main_configs: Dict[str, Any], file_configs: Dict[str, Any], file_path: str) -> None:
        """Perform the actual configuration merge."""
        self._add_config_file(main_configs, file_configs, file_path)
        self._update_env_variables(main_configs, file_configs, file_path)
    
    def _add_config_file(self, main_configs: Dict[str, Any], file_configs: Dict[str, Any], file_path: str) -> None:
        """Add configuration file to main configs."""
        main_configs["config_files"].append({
            "file": file_path,
            "configs": file_configs
        })
    
    def _update_env_variables(self, main_configs: Dict[str, Any], file_configs: Dict[str, Any], file_path: str) -> None:
        """Update environment variables from file configs."""
        for key, value in file_configs.items():
            self._add_env_variable(main_configs, key, value, file_path)
    
    def _add_env_variable(self, main_configs: Dict[str, Any], key: str, value: str, file_path: str) -> None:
        """Add a single environment variable."""
        if key not in main_configs["env_variables"]:
            main_configs["env_variables"][key] = []
        main_configs["env_variables"][key].append({
            "value": value,
            "source": file_path
        })
    
    def _generate_summary(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate configuration summary."""
        env_vars = configs["env_variables"]
        return self._build_summary_dict(configs, env_vars)
    
    def _build_summary_dict(self, configs: Dict[str, Any], env_vars: Dict[str, Any]) -> Dict[str, Any]:
        """Build the summary dictionary."""
        return {
            "total_config_files": len(configs["config_files"]),
            "unique_variables": len(env_vars),
            "has_api_keys": self._has_api_keys(env_vars),
            "detected_providers": self._detect_providers(env_vars)
        }
    
    def _has_api_keys(self, env_vars: Dict[str, Any]) -> bool:
        """Check if environment variables contain API keys."""
        return any("KEY" in k or "TOKEN" in k for k in env_vars)
    
    def _detect_providers(self, env_vars: Dict[str, Any]) -> List[str]:
        """Detect AI providers from variables."""
        providers = set()
        for key in env_vars:
            self._check_provider_patterns(key.upper(), providers)
        return list(providers)
    
    def _check_provider_patterns(self, key_upper: str, providers: set) -> None:
        """Check key for AI provider patterns."""
        patterns_map = self._get_provider_patterns_map()
        for provider, patterns in patterns_map.items():
            if any(pattern in key_upper for pattern in patterns):
                providers.add(provider)
    
    def _get_provider_patterns_map(self) -> Dict[str, List[str]]:
        """Get provider patterns mapping."""
        return {
            "openai": ["OPENAI"],
            "anthropic": ["ANTHROPIC", "CLAUDE"],
            "huggingface": ["HUGGINGFACE"],
            "cohere": ["COHERE"]
        }