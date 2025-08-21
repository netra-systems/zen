"""Secret mapping definitions split from config.py for modularity."""

from typing import Dict, Any


def _get_gemini_targets() -> list[str]:
    """Get list of Gemini API targets."""
    return [
        "llm_configs.default", "llm_configs.analysis",
        "llm_configs.triage", "llm_configs.data",
        "llm_configs.optimizations_core", "llm_configs.actions_to_meet_goals",
        "llm_configs.reporting", "llm_configs.google"
    ]


def get_gemini_mapping() -> Dict[str, Any]:
    """Get Gemini API key mapping."""
    return {
        "targets": _get_gemini_targets(),
        "field": "api_key"
    }


def _get_anthropic_mapping() -> Dict[str, Any]:
    """Get Anthropic API mapping."""
    return {
        "targets": ["llm_configs.anthropic"],
        "field": "api_key"
    }


def _get_openai_mapping() -> Dict[str, Any]:
    """Get OpenAI API mapping."""
    return {
        "targets": ["llm_configs.openai"],
        "field": "api_key"
    }


def _get_cohere_mapping() -> Dict[str, Any]:
    """Get Cohere API mapping."""
    return {
        "targets": ["llm_configs.cohere"],
        "field": "api_key"
    }


def _get_mistral_mapping() -> Dict[str, Any]:
    """Get Mistral API mapping."""
    return {
        "targets": ["llm_configs.mistral"],
        "field": "api_key"
    }


def get_llm_mappings() -> Dict[str, Dict[str, Any]]:
    """Get LLM API key mappings."""
    return {
        "anthropic-api-key": _get_anthropic_mapping(),
        "openai-api-key": _get_openai_mapping(),
        "cohere-api-key": _get_cohere_mapping(),
        "mistral-api-key": _get_mistral_mapping()
    }


def _get_google_client_id_mapping() -> Dict[str, Any]:
    """Get Google client ID mapping."""
    return {
        "targets": ["google_cloud", "oauth_config"],
        "field": "client_id"
    }


def _get_google_client_secret_mapping() -> Dict[str, Any]:
    """Get Google client secret mapping."""
    return {
        "targets": ["google_cloud", "oauth_config"],
        "field": "client_secret"
    }


def get_google_mappings() -> Dict[str, Dict[str, Any]]:
    """Get Google/OAuth mappings."""
    return {
        "google-client-id": _get_google_client_id_mapping(),
        "google-client-secret": _get_google_client_secret_mapping()
    }


def _get_langfuse_secret_mapping() -> Dict[str, Any]:
    """Get Langfuse secret key mapping."""
    return {
        "targets": ["langfuse"],
        "field": "secret_key"
    }


def _get_langfuse_public_mapping() -> Dict[str, Any]:
    """Get Langfuse public key mapping."""
    return {
        "targets": ["langfuse"],
        "field": "public_key"
    }


def get_service_mappings() -> Dict[str, Dict[str, Any]]:
    """Get external service mappings."""
    return {
        "langfuse-secret-key": _get_langfuse_secret_mapping(),
        "langfuse-public-key": _get_langfuse_public_mapping()
    }


def _get_clickhouse_mapping() -> Dict[str, Any]:
    """Get ClickHouse password mapping."""
    return {
        "targets": ["clickhouse_native", "clickhouse_https"],
        "field": "password"
    }


def _get_redis_mapping() -> Dict[str, Any]:
    """Get Redis password mapping."""
    return {
        "targets": ["redis"],
        "field": "password"
    }


def get_database_mappings() -> Dict[str, Dict[str, Any]]:
    """Get database credential mappings."""
    return {
        "clickhouse-default-password": _get_clickhouse_mapping(),
        "redis-default": _get_redis_mapping()
    }


def _get_jwt_mapping() -> Dict[str, Any]:
    """Get JWT secret key mapping."""
    return {
        "targets": [],
        "field": "jwt_secret_key"
    }


def _get_fernet_mapping() -> Dict[str, Any]:
    """Get Fernet key mapping."""
    return {
        "targets": [],
        "field": "fernet_key"
    }


def get_auth_mappings() -> Dict[str, Dict[str, Any]]:
    """Get authentication mappings."""
    return {
        "jwt-secret-key": _get_jwt_mapping(),
        "fernet-key": _get_fernet_mapping()
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