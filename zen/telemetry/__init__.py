"""Helpers for accessing community telemetry credentials at runtime."""

from .embedded_credentials import get_embedded_credentials, get_project_id

__all__ = ["get_embedded_credentials", "get_project_id"]
