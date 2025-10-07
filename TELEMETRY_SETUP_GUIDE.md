# Zen Telemetry Guide

## Overview

Zen includes optional telemetry to help understand usage patterns. Telemetry is completely optional and can be disabled at any time.

## Quick Start

### Telemetry is Opt-In

By default, telemetry is **disabled** unless explicitly configured with credentials.

### Disable Telemetry

```bash
# Method 1: Environment variable (recommended)
export ZEN_TELEMETRY_DISABLED=true

# Method 2: Remove any telemetry credentials if previously configured
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEN_TELEMETRY_DISABLED` | `false` | Complete opt-out from all telemetry |

## Privacy & Security

### Data Protection

- **Complete Opt-Out**: Set `ZEN_TELEMETRY_DISABLED=true` to disable all telemetry
- **No PII Collection**: No personal data is collected when telemetry is enabled
- **Secure Credentials**: Any credentials are stored securely and never logged

### What is NOT Collected

- Your code or data
- Personal information
- Credentials or API keys
- File contents or paths

## Technical Details

The telemetry system is implemented in `zen/telemetry/` and includes:
- Minimal OpenTelemetry integration
- Optional span recording for performance metrics
- Graceful degradation if dependencies are missing

If OpenTelemetry or cloud libraries are not installed, Zen continues to work normally with telemetry disabled.

## Support

For questions or issues related to telemetry:
- GitHub Issues: https://github.com/netra-systems/zen/issues
