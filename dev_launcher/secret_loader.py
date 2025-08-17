"""
Secret loading for development environment.
"""

import os
import socket
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SecretLoader:
    """
    Enhanced secret loader with support for multiple sources.
    
    Loads secrets from environment files and Google Cloud Secret Manager,
    providing detailed visibility into the loading process.
    """
    
    def __init__(self, 
                 project_id: Optional[str] = None, 
                 verbose: bool = False,
                 project_root: Optional[Path] = None):
        """Initialize the secret loader."""
        self.project_id = self._determine_project_id(project_id)
        self.verbose = verbose
        self.project_root = project_root or Path.cwd()
        self.loaded_secrets: Dict[str, str] = {}
        self.failed_secrets: List[Tuple[str, str]] = []
    
    def _determine_project_id(self, project_id: Optional[str]) -> str:
        """Determine project ID based on environment."""
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        default_project_id = "701982941522" if environment == "staging" else "304612253870"
        return project_id or os.environ.get('GOOGLE_CLOUD_PROJECT', default_project_id)
    
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
    
    def load_from_google_secrets(self) -> Dict[str, Tuple[str, str]]:
        """Load secrets from Google Secret Manager."""
        logger.info(f"Loading secrets from Google Cloud Secret Manager")
        logger.info(f"  Project ID: {self.project_id}")
        client = self._create_secret_manager_client()
        if not client:
            return {}
        return self._fetch_google_secrets(client)
    
    def _create_secret_manager_client(self):
        """Create Google Secret Manager client."""
        try:
            from google.cloud import secretmanager
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(10)
            try:
                client = secretmanager.SecretManagerServiceClient()
                logger.info("  Connected to Secret Manager")
                return client
            finally:
                socket.setdefaulttimeout(original_timeout)
        except ImportError:
            logger.error("  Google Cloud SDK not installed")
            return None
        except Exception as e:
            logger.error(f"  Failed to connect: {e}")
            return None
    
    def _fetch_google_secrets(self, client) -> Dict[str, Tuple[str, str]]:
        """Fetch secrets from Google Secret Manager."""
        secret_mappings = self._get_secret_mappings()
        loaded = {}
        logger.info(f"  Fetching {len(secret_mappings)} secrets...")
        for secret_name, env_var in secret_mappings.items():
            self._fetch_single_secret(client, secret_name, env_var, loaded)
        return loaded
    
    def _fetch_single_secret(self, client, secret_name: str, env_var: str, loaded: Dict):
        """Fetch single secret from Google Secret Manager."""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(name=name)
            value = response.payload.data.decode("UTF-8")
            loaded[env_var] = (value, "google_secret")
            self._log_google_secret_success(env_var, value, secret_name)
        except Exception as e:
            self._handle_secret_failure(env_var, e)
    
    def _log_google_secret_success(self, env_var: str, value: str, secret_name: str):
        """Log successful Google secret fetch."""
        masked_value = self._mask_value(value)
        logger.info(f"  Loaded {env_var}: {masked_value} (from Google Secret: {secret_name})")
    
    def _handle_secret_failure(self, env_var: str, error: Exception):
        """Handle secret loading failure."""
        self.failed_secrets.append((env_var, str(error)))
        if self.verbose:
            logger.warning(f"  Failed to load {env_var}: {str(error)[:50]}")
    
    def _get_secret_mappings(self) -> Dict[str, str]:
        """Get the mapping of secret names to environment variables."""
        return {
            "gemini-api-key": "GEMINI_API_KEY",
            "google-client-id": "GOOGLE_CLIENT_ID",
            "google-client-secret": "GOOGLE_CLIENT_SECRET",
            "langfuse-secret-key": "LANGFUSE_SECRET_KEY",
            "langfuse-public-key": "LANGFUSE_PUBLIC_KEY",
            "clickhouse-default-password": "CLICKHOUSE_DEFAULT_PASSWORD",
            "clickhouse-development-password": "CLICKHOUSE_DEVELOPMENT_PASSWORD",
            "jwt-secret-key": "JWT_SECRET_KEY",
            "fernet-key": "FERNET_KEY",
            "redis-default": "REDIS_PASSWORD",
            "anthropic-api-key": "ANTHROPIC_API_KEY",
            "openai-api-key": "OPENAI_API_KEY",
        }
    
    def _get_static_config(self) -> Dict[str, Tuple[str, str]]:
        """Get static configuration values - only non-sensitive defaults."""
        return {
            "ENVIRONMENT": ("development", "static"),
            "REDIS_HOST": ("localhost", "static"),
            "REDIS_PORT": ("6379", "static"),
        }
    
    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value for display."""
        if len(value) > 8:
            return value[:3] + "***" + value[-3:]
        elif len(value) > 3:
            return value[:3] + "***"
        else:
            return "***"
    
    def load_all_secrets(self) -> bool:
        """Load secrets from all sources with priority."""
        logger.info("=" * 70)
        logger.info("[LOCK] SECRET AND ENVIRONMENT VARIABLE LOADING PROCESS")
        logger.info("=" * 70)
        env_tracking = {}
        existing_env = self._capture_existing_env()
        env_secrets = self._load_env_file()
        dev_secrets = self._load_dev_env_file()
        terraform_secrets = self._load_terraform_env_file()
        google_secrets = self._load_google_secrets_conditionally(terraform_secrets)
        static_config = self._get_static_config()
        self._merge_and_set_environment(existing_env, env_secrets, dev_secrets, 
                                       terraform_secrets, google_secrets, static_config)
        return True
    
    def _capture_existing_env(self) -> Dict[str, Tuple[str, str]]:
        """Capture existing OS environment variables."""
        logger.info("\n[STEP 1] Checking existing OS environment variables...")
        existing_env = {}
        relevant_keys = set(self._get_secret_mappings().values()) | set(self._get_static_config().keys())
        for key in os.environ:
            if self._is_relevant_env_key(key, relevant_keys):
                existing_env[key] = (os.environ[key], "os_environment")
                logger.info(f"  [OK] Found {key} in OS environment")
        return existing_env
    
    def _is_relevant_env_key(self, key: str, relevant_keys: set) -> bool:
        """Check if environment key is relevant."""
        return (key in relevant_keys or 
                key.startswith(("CLICKHOUSE_", "REDIS_", "GOOGLE_", "JWT_", "LANGFUSE_")))
    
    def _load_env_file(self) -> Dict[str, Tuple[str, str]]:
        """Load from .env file."""
        logger.info("\n[STEP 2] Loading from .env file...")
        env_file = self.project_root / ".env"
        return self._load_env_file_with_logging(env_file, ".env")
    
    def _load_dev_env_file(self) -> Dict[str, Tuple[str, str]]:
        """Load from .env.development file."""
        logger.info("\n[STEP 3] Loading from .env.development...")
        dev_env_file = self.project_root / ".env.development"
        return self._load_env_file_with_logging(dev_env_file, ".env.development")
    
    def _load_terraform_env_file(self) -> Dict[str, Tuple[str, str]]:
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
    
    def _load_google_secrets_conditionally(self, terraform_secrets: Dict) -> Dict[str, Tuple[str, str]]:
        """Load Google secrets conditionally."""
        logger.info("\n[STEP 5] Loading from Google Secret Manager...")
        if self.project_id and not terraform_secrets:
            google_secrets = self.load_from_google_secrets()
            logger.info(f"  [OK] Loaded {len(google_secrets)} secrets from Google")
            return google_secrets
        elif terraform_secrets:
            logger.info("  [SKIP] Skipping (using Terraform config instead)")
        else:
            logger.info("  [WARN] No project ID configured")
        return {}
    
    def _merge_and_set_environment(self, existing_env: Dict, env_secrets: Dict, 
                                   dev_secrets: Dict, terraform_secrets: Dict, 
                                   google_secrets: Dict, static_config: Dict):
        """Merge all sources and set environment variables."""
        logger.info("\n[STEP 6] Adding static configuration defaults...")
        logger.info(f"  [OK] {len(static_config)} static defaults available")
        self._log_precedence_info()
        all_secrets = self._merge_with_precedence(static_config, google_secrets, env_secrets,
                                                 dev_secrets, terraform_secrets, existing_env)
        self._set_environment_variables(all_secrets)
        self._print_detailed_summary()
    
    def _log_precedence_info(self):
        """Log precedence information."""
        logger.info("\n[MERGE] MERGING WITH PRECEDENCE (highest to lowest):")
        logger.info("  1. OS Environment Variables (highest)")
        logger.info("  2. .env.development.local (Terraform)")
        logger.info("  3. .env.development")
        logger.info("  4. .env")
        logger.info("  5. Google Secret Manager")
        logger.info("  6. Static defaults (lowest)")
    
    def _merge_with_precedence(self, static_config: Dict, google_secrets: Dict, 
                              env_secrets: Dict, dev_secrets: Dict, 
                              terraform_secrets: Dict, existing_env: Dict) -> Dict:
        """Merge secrets with proper precedence."""
        all_secrets = {}
        for source, secrets, name in [
            ("static", static_config, "Static defaults"),
            ("google", google_secrets, "Google Secret Manager"),
            ("env", env_secrets, ".env file"),
            ("dev", dev_secrets, ".env.development"),
            ("terraform", terraform_secrets, ".env.development.local"),
            ("os", existing_env, "OS Environment")
        ]:
            self._merge_source_secrets(all_secrets, secrets, source, name)
        return all_secrets
    
    def _merge_source_secrets(self, all_secrets: Dict, secrets: Dict, source: str, name: str):
        """Merge secrets from a single source."""
        if not secrets:
            return
        for key, value_tuple in secrets.items():
            value = value_tuple[0] if isinstance(value_tuple, tuple) else value_tuple
            if key in all_secrets:
                self._log_override(key, name)
            all_secrets[key] = (value, source)
    
    def _log_override(self, key: str, name: str):
        """Log variable override."""
        logger.debug(f"  [OVERRIDE] {key}: overridden by {name}")
    
    def _set_environment_variables(self, all_secrets: Dict):
        """Set environment variables and track them."""
        logger.info("\n[FINAL] ENVIRONMENT VARIABLES:")
        logger.info("-" * 60)
        categories = self._get_secret_categories()
        self._set_categorized_variables(categories, all_secrets)
        self._set_uncategorized_variables(categories, all_secrets)
    
    def _set_categorized_variables(self, categories: Dict, all_secrets: Dict):
        """Set categorized environment variables."""
        for category, keys in categories.items():
            has_vars = any(k in all_secrets for k in keys)
            if has_vars:
                logger.info(f"\n{category}:")
                for key in keys:
                    if key in all_secrets:
                        self._set_single_variable(key, all_secrets[key])
    
    def _set_uncategorized_variables(self, categories: Dict, all_secrets: Dict):
        """Set uncategorized environment variables."""
        categorized = set()
        for keys in categories.values():
            categorized.update(keys)
        uncategorized = {k: v for k, v in all_secrets.items() if k not in categorized}
        if uncategorized:
            logger.info("\nOther:")
            for key, value_tuple in uncategorized.items():
                self._set_single_variable(key, value_tuple)
    
    def _set_single_variable(self, key: str, value_tuple: Tuple[str, str]):
        """Set single environment variable."""
        value, source = value_tuple
        os.environ[key] = value
        self.loaded_secrets[key] = source
        masked = self._mask_value(value)
        logger.info(f"  {key}: {masked} (from: {source})")
    
    def _print_detailed_summary(self):
        """Print detailed summary of loaded environment variables."""
        logger.info("\n" + "=" * 70)
        logger.info("[STATS] ENVIRONMENT VARIABLE LOADING SUMMARY")
        logger.info("=" * 70)
        sources = self._count_sources()
        total = len(self.loaded_secrets)
        self._log_summary_stats(total, sources)
        self._log_failed_secrets()
        self._log_summary_tips()
    
    def _count_sources(self) -> Dict[str, int]:
        """Count variables by source."""
        sources = {}
        for source in self.loaded_secrets.values():
            readable_source = {
                "os": "OS Environment",
                "terraform": ".env.development.local (Terraform)",
                "dev": ".env.development",
                "env": ".env file",
                "env_file": ".env file",
                "google": "Google Secret Manager",
                "google_secret": "Google Secret Manager",
                "static": "Static defaults"
            }.get(source, source)
            sources[readable_source] = sources.get(readable_source, 0) + 1
        return sources
    
    def _log_summary_stats(self, total: int, sources: Dict[str, int]):
        """Log summary statistics."""
        logger.info(f"\n[SUCCESS] Total environment variables set: {total}")
        logger.info("\n[CHART] Variables by source:")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            bar_length = int(percentage / 2)
            bar = "#" * bar_length + "-" * (50 - bar_length)
            logger.info(f"  {source:35} {count:3} vars [{bar}] {percentage:.1f}%")
    
    def _log_failed_secrets(self):
        """Log failed secrets."""
        if self.failed_secrets:
            logger.warning(f"\n[WARNING] Failed to load {len(self.failed_secrets)} secrets:")
            for secret, error in self.failed_secrets[:5]:
                logger.warning(f"  - {secret}: {error[:80]}")
    
    def _log_summary_tips(self):
        """Log summary tips."""
        logger.info("\n[TIP] Environment variables from OS have highest priority")
        logger.info("[TIP] Use .env.development for local overrides")
        logger.info("=" * 70)
    
    def _get_secret_categories(self) -> Dict[str, List[str]]:
        """Get categorized grouping of secrets."""
        return {
            "Google OAuth": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
            "API Keys": ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "ClickHouse": [
                "CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER",
                "CLICKHOUSE_DEFAULT_PASSWORD", "CLICKHOUSE_DEVELOPMENT_PASSWORD", 
                "CLICKHOUSE_DB"
            ],
            "Database": ["DATABASE_URL"],
            "Redis": ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"],
            "Langfuse": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
            "Security": ["JWT_SECRET_KEY", "FERNET_KEY"],
            "Environment": ["ENVIRONMENT"]
        }