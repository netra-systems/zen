# Zen Telemetry Guide

## Overview

Zen includes automatic telemetry that sends anonymous usage data to help improve the project. When you install zen from PyPI, telemetry is **enabled by default** with embedded credentials. You can opt-out at any time.

## Quick Start

### Telemetry is Enabled by Default

When you install zen via `pip install netra-zen`, telemetry is automatically enabled and will send anonymous spans to Cloud Trace. This helps the community understand usage patterns and improve zen.

### Disable Telemetry (Opt-Out)

If you prefer not to send telemetry data:

```bash
# Set environment variable before running zen
export ZEN_TELEMETRY_DISABLED=true

# Or set it inline
ZEN_TELEMETRY_DISABLED=true zen --config my-config.json
```

You can also add this to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to disable permanently:

```bash
echo 'export ZEN_TELEMETRY_DISABLED=true' >> ~/.bashrc
source ~/.bashrc
```

## What Data is Collected

Zen telemetry collects **anonymous usage metrics** to help improve the project:

### ✅ Data Collected
- **Token usage**: Input, output, cache read/creation token counts
- **Cost metrics**: USD breakdown by token type (for transparency)
- **Tool usage**: Which tools are invoked and token consumption per tool
- **Performance**: Instance duration and execution status
- **Anonymous identifiers**: Hashed session ID and workspace hash (not reversible)

### ❌ Data NOT Collected
- Your code or prompts
- File contents or paths
- Personal information
- Credentials or API keys
- Command-line arguments beyond slash command names
- Any identifiable information about you or your organization

All session and workspace identifiers are **one-way hashed** before being sent, making it impossible to identify individual users.

## How It Works

### For Users (Installing from PyPI)

1. You install zen: `pip install netra-zen`
2. The package includes embedded credentials (added during release build)
3. When you run zen, telemetry automatically sends anonymous spans
4. You can opt-out anytime with `ZEN_TELEMETRY_DISABLED=true`

### For Maintainers (Building Releases)

1. Telemetry credentials stored in GitHub Secret: `COMMUNITY_CREDENTIALS`
2. Release workflow triggered by pushing a version tag (e.g., `v1.0.4`)
3. `scripts/embed_release_credentials.py` embeds credentials into the build
4. Package built with `python -m build`
5. Original credential loader file restored (keeps secrets out of git)
6. Built package uploaded as artifact for publishing to PyPI

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEN_TELEMETRY_DISABLED` | `false` | Set to `true` to completely disable telemetry |
| `ZEN_COMMUNITY_TELEMETRY_B64` | (embedded) | Base64-encoded service account JSON (for development) |
| `ZEN_COMMUNITY_TELEMETRY_FILE` | (none) | Path to service account JSON file (for development) |
| `ZEN_COMMUNITY_TELEMETRY_PROJECT` | `netra-telemetry-public` | Override GCP project ID |

## Privacy & Security

### Data Protection Guarantees

- **Complete Opt-Out**: Set `ZEN_TELEMETRY_DISABLED=true` to disable all telemetry
- **Anonymous Only**: All identifiers are one-way hashed
- **No PII**: No personal data, code, or credentials collected
- **Secure Transport**: All data sent over HTTPS to Google Cloud Trace
- **Limited Scope**: Embedded credentials can only write traces, not read data

### Security Model

The embedded service account has **minimal permissions**:
- ✅ Can write traces to Cloud Trace (`trace.append` permission)
- ❌ Cannot read traces or any other data
- ❌ Cannot access other GCP services
- ❌ Cannot modify project settings

Even if someone extracts the credentials from the package, they can only contribute anonymous traces - they cannot access any existing data.

## Technical Details

### Architecture

```
Zen Orchestrator
  ↓ (OpenTelemetry SDK)
Google Cloud Trace
  ↓ (Embedded service account: write-only)
netra-telemetry-public project
```

### Implementation

The telemetry system is implemented in `zen/telemetry/`:
- **`manager.py`**: OpenTelemetry integration and span recording
- **`embedded_credentials.py`**: Runtime credential loader (or embedded credentials in releases)
- **`__init__.py`**: Module exports

### Graceful Degradation

If OpenTelemetry or Google Cloud libraries are not installed, zen continues to work normally with telemetry automatically disabled. No errors or warnings are shown to the user.

## For Developers

### Running Zen from Source

When running from source (not installed from PyPI), telemetry is disabled by default because no credentials are embedded. To enable telemetry during development:

```bash
# Option 1: Set base64-encoded credentials
export ZEN_COMMUNITY_TELEMETRY_B64="<base64-encoded-service-account-json>"

# Option 2: Point to credentials file
export ZEN_COMMUNITY_TELEMETRY_FILE="/path/to/service-account.json"

# Then run zen
python zen_orchestrator.py --config my-config.json
```

### Building a Release

The release process automatically embeds credentials:

```bash
# 1. Ensure COMMUNITY_CREDENTIALS secret exists in GitHub
gh secret list --repo netra-systems/zen

# 2. Tag a new version
git tag v1.0.4
git push origin v1.0.4

# 3. GitHub Actions will:
#    - Embed credentials from COMMUNITY_CREDENTIALS secret
#    - Build wheel and sdist
#    - Upload as artifacts
#    - Restore original credential loader

# 4. Download and publish to PyPI
gh run download <run-id>
twine upload dist/*
```

## Verifying Telemetry Status

To check if telemetry is enabled:

```python
from zen.telemetry import telemetry_manager

if telemetry_manager.is_enabled():
    print("✅ Telemetry is enabled")
else:
    print("❌ Telemetry is disabled")
```

Or check the logs when running zen - you'll see:
```
INFO - Telemetry initialized with community credentials
```

If telemetry is disabled, you'll see:
```
DEBUG - Telemetry disabled via ZEN_TELEMETRY_DISABLED
```

## Frequently Asked Questions

### Why is telemetry enabled by default?

Telemetry helps us understand how zen is being used in the wild, which features are most valuable, and where improvements are needed. All data is anonymous and helps the entire community.

### Can I use zen without telemetry?

Yes! Simply set `ZEN_TELEMETRY_DISABLED=true` and zen works exactly the same without sending any data.

### What happens to the telemetry data?

Data is sent to Google Cloud Trace in the `netra-telemetry-public` project. It may be analyzed to create aggregate reports about zen usage patterns (e.g., "Most users run 5-10 instances concurrently" or "Cache tokens save an average of 30% on costs").

### Can you identify me from the telemetry data?

No. All identifiers (session ID, workspace path) are one-way hashed before being sent. We cannot reverse these hashes to identify individual users or organizations.

### How much data does telemetry send?

Very little - each zen instance sends a single span (typically a few KB) containing only the metrics listed in the "What Data is Collected" section above.

### Does telemetry affect performance?

Minimal impact. Spans are sent asynchronously in the background and do not block zen operations. If telemetry fails for any reason, zen continues normally.

## Support

For questions or issues related to telemetry:
- GitHub Issues: https://github.com/netra-systems/zen/issues
- Documentation: https://github.com/netra-systems/zen

To report privacy concerns:
- Email: privacy@netrasystems.ai (if available)
- GitHub Issues: Tag with `privacy` label
