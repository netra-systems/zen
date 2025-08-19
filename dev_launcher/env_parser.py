"""
Advanced .env file parsing with interpolation support.

Provides parsing for .env files with ${VAR} interpolation and validation.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class EnvParser:
    """
    Advanced .env file parser with interpolation and validation.
    
    Supports ${VAR} style interpolation, quote handling, and escape sequences.
    """
    
    def __init__(self, verbose: bool = False):
        """Initialize environment parser."""
        self.verbose = verbose
    
    def parse_env_file(self, file_path: Path, source: str) -> Dict[str, Tuple[str, str]]:
        """Parse .env file with advanced features."""
        secrets = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parsed = self._parse_env_line(line, line_num, source)
                    if parsed:
                        key, value = parsed
                        secrets[key] = (value, source)
        except Exception as e:
            logger.error(f"  [ERROR] Failed to parse {file_path}: {e}")
        
        return secrets
    
    def _parse_env_line(self, line: str, line_num: int, source: str) -> Optional[Tuple[str, str]]:
        """Parse single environment line with validation."""
        original_line = line
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            return None
        
        # Must contain equals sign
        if '=' not in line:
            if self.verbose:
                logger.debug(f"    {source}:{line_num} - No '=' found: {original_line[:50]}")
            return None
        
        # Split on first equals only
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        # Validate key format
        if not self._is_valid_env_key(key):
            if self.verbose:
                logger.debug(f"    {source}:{line_num} - Invalid key format: {key}")
            return None
        
        # Process value (handle quotes, escaping)
        processed_value = self._process_env_value(value)
        
        if self.verbose:
            masked_value = self._mask_secret_value(processed_value)
            logger.debug(f"    {source}:{line_num} - {key}={masked_value}")
        
        return key, processed_value
    
    def _is_valid_env_key(self, key: str) -> bool:
        """Validate environment variable key format."""
        # Must be valid identifier: letters, numbers, underscores
        # Cannot start with number
        return re.match(r'^[A-Z_][A-Z0-9_]*$', key) is not None
    
    def _process_env_value(self, value: str) -> str:
        """Process environment value - handle quotes and escaping."""
        # Handle quoted values
        if ((value.startswith('"') and value.endswith('"')) or
            (value.startswith("'") and value.endswith("'"))):
            value = value[1:-1]
        
        # Handle basic escape sequences
        value = value.replace('\\n', '\n')
        value = value.replace('\\t', '\t')
        value = value.replace('\\"', '"')
        value = value.replace("\\'", "'")
        
        return value
    
    def interpolate_value(self, value: str, secrets: Dict[str, Tuple[str, str]]) -> str:
        """Interpolate ${VAR} references in a value."""
        if '${' not in value:
            return value
        
        # Find all ${VAR} patterns
        pattern = re.compile(r'\$\{([^}]+)\}')
        
        def replace_var(match):
            var_name = match.group(1)
            
            # Check if variable exists in our secrets
            if var_name in secrets:
                replacement_value, _ = secrets[var_name]
                # Recursively resolve if needed
                return self.interpolate_value(replacement_value, secrets)
            
            # Check OS environment as fallback
            if var_name in os.environ:
                return os.environ[var_name]
            
            # Variable not found - return original or empty
            logger.warning(f"      [WARN] Variable {var_name} not found for interpolation")
            return match.group(0)  # Return original ${VAR} if not found
        
        return pattern.sub(replace_var, value)
    
    def get_interpolation_dependencies(self, secrets: Dict[str, str]) -> Dict[str, set]:
        """Get dependency graph of variable interpolations."""
        dependencies = {}
        
        for key, value in secrets.items():
            deps = set()
            pattern = re.compile(r'\$\{([^}]+)\}')
            
            for match in pattern.finditer(value):
                var_name = match.group(1)
                deps.add(var_name)
            
            if deps:
                dependencies[key] = deps
        
        return dependencies
    
    def validate_interpolation_cycles(self, secrets: Dict[str, str]) -> bool:
        """Check for circular dependencies in interpolations."""
        dependencies = self.get_interpolation_dependencies(secrets)
        
        def has_cycle(var, visited, rec_stack):
            visited.add(var)
            rec_stack.add(var)
            
            if var in dependencies:
                for dep in dependencies[var]:
                    if dep not in visited:
                        if has_cycle(dep, visited, rec_stack):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(var)
            return False
        
        visited = set()
        for var in dependencies:
            if var not in visited:
                if has_cycle(var, visited, set()):
                    logger.error(f"[ERROR] Circular dependency detected involving {var}")
                    return False
        
        return True
    
    def _mask_secret_value(self, value: str) -> str:
        """Mask secret value for safe display."""
        if len(value) <= 3:
            return "***"
        elif len(value) <= 8:
            return f"{value[:2]}***"
        else:
            return f"{value[:3]}***{value[-3:]}"