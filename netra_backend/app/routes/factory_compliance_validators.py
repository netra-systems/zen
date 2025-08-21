"""Factory compliance validators."""
from fastapi import HTTPException

from netra_backend.app.core.configuration import unified_config_manager


def validate_claude_cli_access(use_claude_cli: bool) -> None:
    """Validate Claude CLI access."""
    if use_claude_cli and not is_dev_environment():
        raise HTTPException(403, "Claude CLI only in dev")


def validate_dev_environment() -> None:
    """Validate development environment access."""
    if not is_dev_environment():
        raise HTTPException(403, "Claude CLI only available in development")


def is_dev_environment() -> bool:
    """Check if running in development environment."""
    config = unified_config_manager.get_config()
    env = getattr(config, 'environment', 'staging')  # Default to staging for safety
    return env in ["development", "dev", "local"]