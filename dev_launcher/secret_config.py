"""
Secret configuration and categorization utilities.

Provides secret configuration, categorization, and static defaults.
"""

import os
import logging
from typing import Dict, Set, List, Tuple, Optional

logger = logging.getLogger(__name__)


class SecretConfig:
    """
    Secret configuration and categorization utilities.
    
    Provides centralized configuration for secret requirements,
    categorization, and static default values.
    """
    
    @staticmethod
    def get_required_secrets() -> Set[str]:
        """Get list of critical secret keys that must be present."""
        return {
            "GEMINI_API_KEY",
            "GOOGLE_CLIENT_ID", 
            "GOOGLE_CLIENT_SECRET",
            "LANGFUSE_SECRET_KEY",
            "LANGFUSE_PUBLIC_KEY",
            "CLICKHOUSE_DEFAULT_PASSWORD",
            "CLICKHOUSE_DEVELOPMENT_PASSWORD",
            "JWT_SECRET_KEY",
            "FERNET_KEY",
            "REDIS_PASSWORD",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
        }
    
    @staticmethod
    def get_static_defaults() -> Dict[str, Tuple[str, str]]:
        """Get static default values for non-sensitive configs."""
        return {
            "ENVIRONMENT": ("development", "default"),
            "REDIS_HOST": ("localhost", "default"),
            "REDIS_PORT": ("6379", "default"),
            "CLICKHOUSE_HOST": ("localhost", "default"),
            "CLICKHOUSE_PORT": ("9000", "default"),
            "CLICKHOUSE_USER": ("default", "default"),
            "CLICKHOUSE_DB": ("default", "default"),
        }
    
    @staticmethod
    def get_secret_categories() -> Dict[str, List[str]]:
        """Get categorized grouping of secrets."""
        return {
            "Google OAuth": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
            "API Keys": ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "ClickHouse": [
                "CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER",
                "CLICKHOUSE_DEFAULT_PASSWORD", "CLICKHOUSE_DEVELOPMENT_PASSWORD", 
                "CLICKHOUSE_DB"
            ],
            "Redis": ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"],
            "Langfuse": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
            "Security": ["JWT_SECRET_KEY", "FERNET_KEY"],
            "Environment": ["ENVIRONMENT"]
        }
    
    @staticmethod
    def determine_project_id(project_id: Optional[str] = None) -> str:
        """Determine project ID based on environment."""
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        default_project_id = "701982941522" if environment == "staging" else "304612253870"
        return project_id or os.environ.get('GOOGLE_CLOUD_PROJECT', default_project_id)
    
    @staticmethod
    def mask_value(value: str) -> str:
        """Mask a sensitive value for display."""
        if len(value) > 8:
            return value[:3] + "***" + value[-3:]
        elif len(value) > 3:
            return value[:3] + "***"
        else:
            return "***"