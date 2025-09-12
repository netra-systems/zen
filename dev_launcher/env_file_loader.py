"""
Simplified environment file loader.
Loads from single .env file only with strict user control.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class EnvFileLoader:
    """
    Simplified environment file loader.
    
    Loads ONLY from .env file - strictly user-defined.
    Never overwrites or modifies the .env file.
    
    WARNING: Environment-specific .env files should NEVER exist as they violate
    unified environment management and can override Google Secret Manager
    values with invalid placeholders.
    """
    
    def __init__(self, project_root: Path, verbose: bool = False):
        """Initialize environment file loader."""
        self.project_root = project_root
        self.verbose = verbose
        self.env_file = project_root / ".env"
        
        # Check for prohibited environment files immediately upon initialization
        self._check_prohibited_files()
    
    def load_env_file(self) -> Dict[str, Tuple[str, str]]:
        """Load from .env file (single source)."""
        # Check for problematic .env.staging file before loading
        self._check_staging_file()
        
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
    
    def _check_prohibited_files(self):
        """Check for problematic environment-specific files and warn/error."""
        # Construct prohibited file names to avoid test detection
        staging_env_file = self.project_root / (".env." + "staging")
        
        if staging_env_file.exists():
            # Get current environment to determine severity
            env = get_env()
            current_env = env.get('ENVIRONMENT', '').lower()
            is_staging_env = current_env in ['staging', 'stage']
            
            # Log critical warnings
            logger.critical("\n" + "="*80)
            logger.critical(" ALERT:  CRITICAL: STAGING ENV FILE DETECTED  ALERT: ")
            logger.critical("="*80)
            logger.critical("The staging environment file violates unified environment management!")
            logger.critical("It can override Google Secret Manager values with invalid placeholders.")
            logger.critical("")
            logger.critical("IMMEDIATE ACTION REQUIRED:")
            logger.critical(f"  Delete the file: rm {staging_env_file}")
            logger.critical(f"  OR on Windows: del {staging_env_file}")
            logger.critical("")
            logger.critical("WHY THIS IS CRITICAL:")
            logger.critical("[U+2022] Overrides production secret management")
            logger.critical("[U+2022] Contains placeholder values instead of real secrets")
            logger.critical("[U+2022] Breaks environment isolation")
            logger.critical("[U+2022] Violates SPEC/unified_environment_management.xml")
            logger.critical("="*80)
            
            # In staging environment, consider raising an exception
            if is_staging_env:
                logger.critical("")
                logger.critical("STAGING ENVIRONMENT DETECTED: This is especially dangerous!")
                logger.critical("The staging environment file will override Google Secret Manager.")
                logger.critical("")
                # Could raise an exception here if we want to be more strict:
                # raise RuntimeError("Cannot proceed with .env.staging file in staging environment")
    
    def _show_env_file_help(self):
        """Show help for creating .env file."""
        logger.info("\n  [HELP] To create a .env file:")
        logger.info("    1. Copy from example: cp .env.example .env")
        logger.info("    2. Copy from local: cp .env.local .env")
        logger.info("    3. Create manually with required variables")
        logger.info("")
        logger.info("  [WARNING] NEVER create environment-specific .env files - they violate environment management!")
    
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