#!/usr/bin/env python3
"""Minimal telemetry smoke test.

This script validates that the environment-provided community telemetry
credentials can authenticate against Google Cloud Trace. It configures an
OpenTelemetry tracer provider, emits a single span, flushes it, and exits.

Usage:
    ZEN_COMMUNITY_TELEMETRY_B64="<base64-json>" scripts/telemetry_smoke.py

If credentials are missing or invalid the script exits with a non-zero status.
"""

from __future__ import annotations

import asyncio
import sys
import time

from google.api_core.exceptions import GoogleAPICallError
from google.cloud.trace_v2 import TraceServiceClient
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from zen.telemetry.embedded_credentials import get_embedded_credentials, get_project_id


async def run() -> None:
    creds = get_embedded_credentials()
    if creds is None:
        raise RuntimeError(
            "No telemetry credentials detected. Set ZEN_COMMUNITY_TELEMETRY_B64 or "
            "ZEN_COMMUNITY_TELEMETRY_FILE before running this smoke test."
        )

    project_id = get_project_id()
    client = TraceServiceClient(credentials=creds)

    resource = Resource.create(
        {
            "service.name": "zen-orchestrator",
            "service.version": "1.0.3",
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
            "zen.analytics.type": "community",
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = CloudTraceSpanExporter(project_id=project_id, client=client)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer("zen.telemetry.smoke_test")
    with tracer.start_as_current_span("telemetry_smoke") as span:
        for i in range(3):
            time.sleep(0.2)
            span.set_attribute(f"iteration.{i}", i)

    if hasattr(provider, "force_flush"):
        provider.force_flush()

    # Give the exporter a brief window to send the batch
    await asyncio.sleep(5)


def main() -> int:
    try:
        asyncio.run(run())
    except GoogleAPICallError as exc:
        print(f"Telemetry smoke test failed: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Telemetry smoke test error: {exc}", file=sys.stderr)
        return 1
    else:
        print("Telemetry smoke test succeeded: span exported to Cloud Trace.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
