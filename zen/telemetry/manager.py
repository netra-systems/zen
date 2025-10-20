"""Telemetry manager for Zen orchestrator.

Provides minimal OpenTelemetry integration that records anonymous spans with
token usage and cost metadata. If OpenTelemetry or Google Cloud libraries are
missing, the manager silently degrades to a no-op implementation.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import asdict
from typing import Any, Dict, Optional

# Fix for gRPC DNS resolution issues on macOS - MUST be set before importing gRPC
# This prevents "DNS query cancelled" errors when connecting to cloudtrace.googleapis.com
if "GRPC_DNS_RESOLVER" not in os.environ:
    os.environ["GRPC_DNS_RESOLVER"] = "native"

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import SpanKind

    OPENTELEMETRY_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    OPENTELEMETRY_AVAILABLE = False

try:
    from google.cloud.trace_v2 import TraceServiceClient
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from google.api_core.exceptions import GoogleAPICallError  # type: ignore

    GCP_EXPORT_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    GCP_EXPORT_AVAILABLE = False

    class GoogleAPICallError(Exception):  # type: ignore
        """Fallback exception used when google-api-core is unavailable."""

        pass

from .embedded_credentials import get_embedded_credentials, get_project_id

logger = logging.getLogger(__name__)


def _sanitize_tool_name(tool: str) -> str:
    """Convert tool names to telemetry-safe attribute suffixes."""
    safe = re.sub(r"[^a-z0-9_]+", "_", tool.lower()).strip("_")
    return safe or "tool"


class _NoOpTelemetryManager:
    """Fallback manager when telemetry dependencies are unavailable."""

    def is_enabled(self) -> bool:
        return False

    def record_instance_span(self, *_, **__):  # pragma: no cover - trivial
        return

    def shutdown(self) -> None:  # pragma: no cover - trivial
        return


class TelemetryManager:
    """Manage OpenTelemetry setup and span emission for Zen."""

    def __init__(self) -> None:
        self._enabled = False
        self._provider: Optional[TracerProvider] = None
        self._tracer = None
        self._initialize()

    def _initialize(self) -> None:
        if os.getenv("ZEN_TELEMETRY_DISABLED", "").lower() in {"1", "true", "yes"}:
            logger.debug("Telemetry disabled via ZEN_TELEMETRY_DISABLED")
            return

        if not (OPENTELEMETRY_AVAILABLE and GCP_EXPORT_AVAILABLE):
            logger.debug("OpenTelemetry or Google Cloud exporter not available; telemetry disabled")
            return

        credentials = get_embedded_credentials()
        if credentials is None:
            logger.debug("No telemetry credentials detected; telemetry disabled")
            return

        try:
            project_id = get_project_id()
            client = TraceServiceClient(credentials=credentials)
            exporter = CloudTraceSpanExporter(project_id=project_id, client=client)

            resource_attrs = {
                "service.name": "zen-orchestrator",
                "service.version": os.getenv("ZEN_VERSION", "1.0.3"),
                "telemetry.sdk.language": "python",
                "telemetry.sdk.name": "opentelemetry",
                "zen.analytics.type": "community",
            }

            resource = Resource.create(resource_attrs)
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(BatchSpanProcessor(exporter))

            trace.set_tracer_provider(provider)
            self._provider = provider
            self._tracer = trace.get_tracer("zen.telemetry")
            self._enabled = True
            logger.info("Telemetry initialized with community credentials")
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning(f"Failed to initialize telemetry: {exc}")
            self._enabled = False
            self._provider = None
            self._tracer = None

    # Public API -----------------------------------------------------

    def is_enabled(self) -> bool:
        return self._enabled and self._tracer is not None

    def record_instance_span(
        self,
        batch_id: str,
        instance_name: str,
        status: Any,
        config: Any,
        cost_usd: Optional[float] = None,
        workspace: Optional[str] = None,
    ) -> None:
        if not self.is_enabled():
            return

        assert self._tracer is not None  # mypy hint

        attributes: Dict[str, Any] = {
            "zen.batch.id": batch_id,
            "zen.instance.name": instance_name,
            "zen.instance.status": getattr(status, "status", "unknown"),
            "zen.instance.success": getattr(status, "status", "") == "completed",
            "zen.instance.permission_mode": getattr(config, "permission_mode", "unknown"),
            "zen.instance.tool_calls": getattr(status, "tool_calls", 0),
            "zen.tokens.total": getattr(status, "total_tokens", 0),
            "zen.tokens.input": getattr(status, "input_tokens", 0),
            "zen.tokens.output": getattr(status, "output_tokens", 0),
            "zen.tokens.cache.read": getattr(status, "cache_read_tokens", 0),
            "zen.tokens.cache.creation": getattr(status, "cache_creation_tokens", 0),
            "zen.tokens.cached_total": getattr(status, "cached_tokens", 0),
        }

        start_time = getattr(status, "start_time", None)
        end_time = getattr(status, "end_time", None)
        if start_time and end_time:
            attributes["zen.instance.duration_ms"] = int((end_time - start_time) * 1000)

        command = getattr(config, "command", None) or getattr(config, "prompt", None)
        if isinstance(command, str) and command.startswith("/"):
            attributes["zen.instance.command_type"] = "slash"
            attributes["zen.instance.command"] = command
        elif isinstance(command, str):
            attributes["zen.instance.command_type"] = "prompt"
        else:
            attributes["zen.instance.command_type"] = "unknown"

        session_id = getattr(config, "session_id", None)
        if session_id:
            session_hash = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]
            attributes["zen.session.hash"] = session_hash

        if workspace:
            workspace_hash = hashlib.sha256(workspace.encode("utf-8")).hexdigest()[:16]
            attributes["zen.workspace.hash"] = workspace_hash

        # Tool metadata
        tool_tokens = getattr(status, "tool_tokens", {}) or {}
        attributes["zen.tools.unique"] = len(tool_tokens)
        total_tool_tokens = 0
        for tool_name, tokens in tool_tokens.items():
            sanitized = _sanitize_tool_name(tool_name)
            attributes[f"zen.tools.tokens.{sanitized}"] = int(tokens)
            total_tool_tokens += int(tokens)
        attributes["zen.tokens.tools_total"] = total_tool_tokens

        tool_details = getattr(status, "tool_details", {}) or {}
        for tool_name, count in tool_details.items():
            sanitized = _sanitize_tool_name(tool_name)
            attributes[f"zen.tools.invocations.{sanitized}"] = int(count)

        # Cost metadata
        if cost_usd is not None:
            attributes["zen.cost.usd_total"] = round(float(cost_usd), 6)

        reported_cost = getattr(status, "total_cost_usd", None)
        if reported_cost is not None:
            attributes["zen.cost.usd_reported"] = round(float(reported_cost), 6)

        # Derive cost components using fallback pricing (USD per million tokens)
        input_tokens = getattr(status, "input_tokens", 0)
        output_tokens = getattr(status, "output_tokens", 0)
        cache_read_tokens = getattr(status, "cache_read_tokens", 0)
        cache_creation_tokens = getattr(status, "cache_creation_tokens", 0)

        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00
        cache_read_cost = (cache_read_tokens / 1_000_000) * (3.00 * 0.1)
        cache_creation_cost = (cache_creation_tokens / 1_000_000) * (3.00 * 1.25)
        tool_cost = (total_tool_tokens / 1_000_000) * 3.00

        attributes.update(
            {
                "zen.cost.usd_input": round(input_cost, 6),
                "zen.cost.usd_output": round(output_cost, 6),
                "zen.cost.usd_cache_read": round(cache_read_cost, 6),
                "zen.cost.usd_cache_creation": round(cache_creation_cost, 6),
                "zen.cost.usd_tools": round(tool_cost, 6),
            }
        )

        # Emit span
        try:
            with self._tracer.start_as_current_span(
                "zen.instance", kind=SpanKind.INTERNAL
            ) as span:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
        except GoogleAPICallError as exc:  # pragma: no cover - network failure safety
            logger.warning(f"Failed to export telemetry span: {exc}")

    def shutdown(self) -> None:
        if not self._provider:
            return
        try:
            if hasattr(self._provider, "force_flush"):
                self._provider.force_flush()
            if hasattr(self._provider, "shutdown"):
                self._provider.shutdown()
        except Exception as exc:  # pragma: no cover
            logger.debug(f"Telemetry shutdown warning: {exc}")


def _build_manager() -> TelemetryManager | _NoOpTelemetryManager:
    if not (OPENTELEMETRY_AVAILABLE and GCP_EXPORT_AVAILABLE):
        return _NoOpTelemetryManager()
    return TelemetryManager()


telemetry_manager = _build_manager()

__all__ = ["TelemetryManager", "telemetry_manager"]
