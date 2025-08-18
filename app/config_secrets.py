"""Secret mapping definitions split from config.py for modularity."""

from typing import Dict, Any


def get_gemini_mapping() -> Dict[str, Any]:
    """Get Gemini API key mapping."""
    return {
        "targets": [
            "llm_configs.default", "llm_configs.analysis",
            "llm_configs.triage", "llm_configs.data",
            "llm_configs.optimizations_core", "llm_configs.actions_to_meet_goals",
            "llm_configs.reporting", "llm_configs.google"
        ],
        "field": "api_key"
    }


def get_llm_mappings() -> Dict[str, Dict[str, Any]]:
    """Get LLM API key mappings."""
    return {
        "anthropic-api-key": {
            "targets": ["llm_configs.anthropic"],
            "field": "api_key"
        },
        "openai-api-key": {
            "targets": ["llm_configs.openai"],
            "field": "api_key"
        },
        "cohere-api-key": {
            "targets": ["llm_configs.cohere"],
            "field": "api_key"
        },
        "mistral-api-key": {
            "targets": ["llm_configs.mistral"],
            "field": "api_key"
        }
    }


def get_google_mappings() -> Dict[str, Dict[str, Any]]:
    """Get Google/OAuth mappings."""
    return {
        "google-client-id": {
            "targets": ["google_cloud", "oauth_config"],
            "field": "client_id"
        },
        "google-client-secret": {
            "targets": ["google_cloud", "oauth_config"],
            "field": "client_secret"
        }
    }


def get_service_mappings() -> Dict[str, Dict[str, Any]]:
    """Get external service mappings."""
    return {
        "langfuse-secret-key": {
            "targets": ["langfuse"],
            "field": "secret_key"
        },
        "langfuse-public-key": {
            "targets": ["langfuse"],
            "field": "public_key"
        }
    }


def get_database_mappings() -> Dict[str, Dict[str, Any]]:
    """Get database credential mappings."""
    return {
        "clickhouse-default-password": {
            "targets": ["clickhouse_native", "clickhouse_https"],
            "field": "password"
        },
        "redis-default": {
            "targets": ["redis"],
            "field": "password"
        }
    }


def get_auth_mappings() -> Dict[str, Dict[str, Any]]:
    """Get authentication mappings."""
    return {
        "jwt-secret-key": {
            "targets": [],
            "field": "jwt_secret_key"
        },
        "fernet-key": {
            "targets": [],
            "field": "fernet_key"
        }
    }


def get_all_secret_mappings() -> Dict[str, Dict[str, Any]]:
    """Get all secret mappings combined."""
    mappings = _create_base_mappings()
    _update_mappings_with_providers(mappings)
    return mappings


def _create_base_mappings() -> Dict[str, Dict[str, Any]]:
    """Create base mappings with gemini configuration."""
    return {"gemini-api-key": get_gemini_mapping()}


def _update_mappings_with_providers(mappings: Dict[str, Dict[str, Any]]) -> None:
    """Update mappings with all provider configurations."""
    mappings.update(get_llm_mappings())
    mappings.update(get_google_mappings())
    mappings.update(get_service_mappings())
    mappings.update(get_database_mappings())
    mappings.update(get_auth_mappings())