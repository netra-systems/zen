"""
Environment file loading functionality.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)


class EnvFileLoader:
    """
    Handles loading environment variables from files.
    
    Manages loading from various .env file types with
    proper precedence and logging.
    """
    
    def __init__(self, project_root: Path, verbose: bool = False):
        """Initialize environment file loader."""
        self.project_root = project_root
        self.verbose = verbose
    
    def load_from_env_file(self, env_file: Optional[Path] = None) -> Dict[str, Tuple[str, str]]:
        """Load secrets from an environment file."""
        if env_file is None:
            env_file = self.project_root / ".env"
        loaded = {}
        if env_file.exists():
            self._load_existing_env_file(env_file, loaded)
        else:
            logger.debug(f"No .env file found at {env_file}")
        return loaded
    
    def _load_existing_env_file(self, env_file: Path, loaded: Dict):
        """Load from existing environment file."""
        logger.info(f"Loading from existing .env file: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                self._process_env_line(line, loaded)
    
    def _process_env_line(self, line: str, loaded: Dict):
        """Process single environment file line."""
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            loaded[key] = (value.strip('"\''), "env_file")
            self._log_loaded_value(key, value)
    
    def _log_loaded_value(self, key: str, value: str):
        """Log loaded value if verbose."""
        if self.verbose:
            masked_value = self._mask_value(value)
            logger.debug(f"  Loaded {key}: {masked_value} (from .env file)")
    
    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value for display."""
        if len(value) > 8:
            return value[:3] + "***" + value[-3:]
        elif len(value) > 3:
            return value[:3] + "***"
        else:
            return "***"
    
    def load_env_file(self) -> Dict[str, Tuple[str, str]]:
        """Load from .env file."""
        logger.info("\n[STEP 2] Loading from .env file...")
        env_file = self.project_root / ".env"
        return self._load_env_file_with_logging(env_file, ".env")
    
    def load_dev_env_file(self) -> Dict[str, Tuple[str, str]]:
        """Load from .env.development file."""
        logger.info("\n[STEP 3] Loading from .env.development...")
        dev_env_file = self.project_root / ".env.development"
        return self._load_env_file_with_logging(dev_env_file, ".env.development")
    
    def load_terraform_env_file(self) -> Dict[str, Tuple[str, str]]:
        """Load from Terraform-generated .env.development.local."""
        logger.info("\n[STEP 4] Loading from .env.development.local (Terraform)...")
        terraform_env_file = self.project_root / ".env.development.local"
        return self._load_env_file_with_logging(terraform_env_file, "Terraform config")
    
    def _load_env_file_with_logging(self, env_file: Path, description: str) -> Dict[str, Tuple[str, str]]:
        """Load environment file with logging."""
        if env_file.exists():
            logger.info(f"  [FILE] Reading: {env_file}")
            secrets = self.load_from_env_file(env_file)
            logger.info(f"  [OK] Loaded {len(secrets)} variables from {description}")
            return secrets
        else:
            logger.info(f"  [WARN] No {description} file found")
            return {}
    
    def capture_existing_env(self, relevant_keys: set) -> Dict[str, Tuple[str, str]]:
        """Capture existing OS environment variables."""
        logger.info("\n[STEP 1] Checking existing OS environment variables...")
        existing_env = {}
        for key in os.environ:
            if self._is_relevant_env_key(key, relevant_keys):
                existing_env[key] = (os.environ[key], "os_environment")
                logger.info(f"  [OK] Found {key} in OS environment")
        return existing_env
    
    def _is_relevant_env_key(self, key: str, relevant_keys: set) -> bool:
        """Check if environment key is relevant."""
        return (key in relevant_keys or 
                key.startswith(("CLICKHOUSE_", "REDIS_", "GOOGLE_", "JWT_", "LANGFUSE_")))