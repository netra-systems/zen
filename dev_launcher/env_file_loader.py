"""
Simplified environment file loader.
Loads from single .env file only with strict user control.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from dev_launcher.isolated_environment import get_env

logger = logging.getLogger(__name__)


class EnvFileLoader:
    """
    Simplified environment file loader.
    
    Loads ONLY from .env file - strictly user-defined.
    Never overwrites or modifies the .env file.
    """
    
    def __init__(self, project_root: Path, verbose: bool = False):
        """Initialize environment file loader."""
        self.project_root = project_root
        self.verbose = verbose
        self.env_file = project_root / ".env"
    
    def load_env_file(self) -> Dict[str, Tuple[str, str]]:
        """Load from .env file (single source)."""
        logger.info("\n[ENV LOADER] Loading from .env file...")
        logger.info(f"  [FILE] Path: {self.env_file}")
        
        loaded = {}
        if self.env_file.exists():
            self._load_existing_env_file(self.env_file, loaded)
            logger.info(f"  [OK] Loaded {len(loaded)} variables from .env")
        else:
            logger.info("  [INFO] No .env file found (user can create one)")
            self._show_env_file_help()
        return loaded
    
    def _load_existing_env_file(self, env_file: Path, loaded: Dict):
        """Load from existing .env file."""
        try:
            with open(env_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    self._process_env_line(line, loaded, line_num)
        except Exception as e:
            logger.error(f"  [ERROR] Failed to read .env: {e}")
    
    def _process_env_line(self, line: str, loaded: Dict, line_num: int):
        """Process single environment file line."""
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip('"\'').strip()
            loaded[key] = (value, "env_file")
            if self.verbose:
                self._log_loaded_value(key, value, line_num)
    
    def _log_loaded_value(self, key: str, value: str, line_num: int):
        """Log loaded value if verbose."""
        masked_value = self._mask_value(value)
        logger.debug(f"    Line {line_num}: {key}={masked_value}")
    
    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value for display."""
        if len(value) > 8:
            return value[:3] + "***" + value[-3:]
        elif len(value) > 3:
            return value[:3] + "***"
        else:
            return "***"
    
    def _show_env_file_help(self):
        """Show help for creating .env file."""
        logger.info("\n  [HELP] To create a .env file:")
        logger.info("    1. Copy from example: cp .env.example .env")
        logger.info("    2. Copy from local: cp .env.local .env")
        logger.info("    3. Create manually with required variables")
    
    def get_missing_variables(self, loaded: Dict, required: Set[str]) -> Set[str]:
        """Get missing required variables."""
        return required - set(loaded.keys())
    
    def capture_existing_env(self, relevant_keys: Set[str]) -> Dict[str, Tuple[str, str]]:
        """Capture existing OS environment variables."""
        logger.info("\n[ENV CHECK] Checking OS environment variables...")
        existing_env = {}
        env = get_env()
        found_count = 0
        for key in relevant_keys:
            value = env.get(key)
            if value is not None:
                existing_env[key] = (value, "isolated_environment")
                found_count += 1
                if self.verbose:
                    logger.debug(f"  Found: {key}")
        logger.info(f"  [OK] Found {found_count} relevant variables in OS")
        return existing_env
    
    def validate_env_file(self) -> bool:
        """Validate .env file is user-controlled."""
        if not self.env_file.exists():
            return True  # No file is valid (user choice)
        
        # Check if file is readable and not system-generated
        try:
            with open(self.env_file, 'r') as f:
                first_line = f.readline().strip()
                if "AUTO-GENERATED" in first_line or "DO NOT EDIT" in first_line:
                    logger.warning("  [WARN] .env appears to be auto-generated")
                    logger.warning("  [WARN] User should create their own .env file")
                    return False
            return True
        except Exception as e:
            logger.error(f"  [ERROR] Cannot validate .env: {e}")
            return False