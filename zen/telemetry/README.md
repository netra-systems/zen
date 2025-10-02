# Zen Telemetry Module

Comprehensive telemetry and observability solution for the Zen orchestrator, providing OpenTelemetry integration with Google Cloud Trace, secure credential management through zen_secrets, and privacy-first data collection.

## Features

### ✅ Core Capabilities
- **OpenTelemetry Integration**: Full distributed tracing with Google Cloud Trace export
- **Privacy-First Design**: Comprehensive PII filtering and data sanitization
- **zen_secrets Integration**: Secure credential management for service accounts
- **Opt-Out Mechanism**: Respects `ZEN_TELEMETRY_DISABLED` environment variable
- **Graceful Degradation**: Works without OpenTelemetry dependencies
- **Performance Optimized**: Minimal overhead with lazy initialization

### ✅ Security & Privacy
- **Data Sanitization**: Automatic PII detection and redaction
- **Secure Credentials**: Integration with zen_secrets for service account management
- **Network Security**: Proper error handling and timeout management
- **Compliance Ready**: Privacy standards compliance built-in

### ✅ Developer Experience
- **Easy Integration**: Simple `@traced` decorator for instrumentation
- **Auto-Initialization**: Automatic setup via zen package import
- **Error Resilient**: Continues working even if telemetry fails
- **Configurable**: Extensive configuration options via environment variables

## Quick Start

### 1. Basic Usage

The telemetry module is automatically initialized when importing zen:

```python
import zen  # Telemetry auto-initializes in background

from zen.telemetry import traced

@traced("my_operation")
def my_function(data):
    return process_data(data)
```

### 2. Opt-Out

To disable telemetry completely:

```bash
export ZEN_TELEMETRY_DISABLED=true
```

### 3. Configuration

Configure telemetry behavior via environment variables:

```bash
# Telemetry level (basic, detailed, disabled)
export ZEN_TELEMETRY_LEVEL=basic

# Sampling rate (0.0 to 1.0)
export ZEN_TELEMETRY_SAMPLE_RATE=0.1

# GCP project for trace export
export ZEN_TELEMETRY_GCP_PROJECT=my-project-id

# Service identification
export ZEN_SERVICE_NAME=zen-orchestrator
export ZEN_SERVICE_VERSION=1.0.3
```

## Architecture

### Module Structure

```
zen/telemetry/
├── __init__.py          # Public API and global instance
├── config.py            # Configuration management
├── manager.py           # Core TelemetryManager class
├── instrumentation.py   # @traced decorator and utilities
├── sanitization.py      # Data sanitization and PII filtering
├── requirements.txt     # OpenTelemetry dependencies
├── test_telemetry.py    # Comprehensive test suite
└── README.md           # This documentation
```

### Key Components

#### TelemetryManager
- Singleton pattern for global telemetry management
- zen_secrets integration for secure credential handling
- Automatic GCP project detection and configuration
- Lazy initialization for optimal performance

#### TelemetryConfig
- Environment-based configuration with sensible defaults
- Built-in opt-out mechanism via `ZEN_TELEMETRY_DISABLED`
- Validation and error handling
- Support for different telemetry levels

#### DataSanitizer
- Comprehensive PII detection and filtering
- Configurable sanitization patterns
- Handles nested data structures safely
- Performance optimized with caching

#### Instrumentation Framework
- `@traced` decorator for function-level tracing
- `@instrument_class` for class-level instrumentation
- Performance tracking with automatic duration calculation
- Exception recording with sanitized stack traces

## Integration Details

### zen_secrets Integration

The telemetry manager integrates with zen_secrets for secure credential management:

```python
# Automatic service account credential loading
credentials = await secret_manager.get_secret("zen-telemetry-service-account")

# Fallback chain:
# 1. zen_secrets ("zen-telemetry-service-account")
# 2. GOOGLE_APPLICATION_CREDENTIALS environment variable
# 3. Default service account (GKE/Cloud Run)
```

### Orchestrator Integration

Key orchestrator methods are automatically instrumented:

```python
# Automatically traced methods:
@traced("orchestrator.init")
def __init__(...)

@traced("orchestrator.run_instance")
async def run_instance(...)

@traced("orchestrator.run_all_instances")
async def run_all_instances(...)

@traced("orchestrator.main")
async def main(...)
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEN_TELEMETRY_DISABLED` | `false` | Disable all telemetry collection |
| `ZEN_TELEMETRY_LEVEL` | `basic` | Telemetry level: `disabled`, `basic`, `detailed` |
| `ZEN_TELEMETRY_SAMPLE_RATE` | `0.1` | Sampling rate (0.0-1.0) |
| `ZEN_TELEMETRY_GCP_PROJECT` | auto-detect | GCP project for trace export |
| `ZEN_SERVICE_NAME` | `zen-orchestrator` | Service name for telemetry |
| `ZEN_SERVICE_VERSION` | `1.0.3` | Service version |
| `ZEN_TELEMETRY_MAX_ATTRIBUTES` | `32` | Max attributes per span |
| `ZEN_TELEMETRY_EXPORT_TIMEOUT` | `30` | Export timeout in seconds |
| `ZEN_TELEMETRY_BATCH_SIZE` | `512` | Batch size for span export |
| `ZEN_TELEMETRY_QUEUE_SIZE` | `2048` | Queue size for span processor |

### Telemetry Levels

- **`disabled`**: No telemetry collection
- **`basic`**: Essential operations only (default)
- **`detailed`**: Comprehensive tracing with full context

## Data Privacy

### PII Filtering

The sanitization module automatically detects and redacts:

- **Authentication**: passwords, tokens, API keys, bearer tokens
- **Personal Info**: emails, phone numbers, SSNs, addresses
- **Financial**: credit cards, account numbers, routing numbers
- **Technical**: IP addresses, file paths, UUIDs
- **Custom Patterns**: Configurable regex patterns

### Sensitive Field Detection

Fields containing these keywords are automatically redacted:
- `password`, `secret`, `token`, `auth`, `credential`, `key`
- `email`, `phone`, `ssn`, `address`, `account`
- `private`, `internal`, `confidential`

### Data Retention

- Traces are exported to Google Cloud Trace with standard retention policies
- No sensitive data is stored locally
- All data is sanitized before export

## Performance

### Overhead Minimization

- **Lazy Initialization**: Telemetry initializes in background thread
- **Sampling**: Configurable sampling rate (default 10%)
- **Batching**: Efficient batch export to reduce network calls
- **Graceful Degradation**: Zero overhead when telemetry is disabled

### Memory Usage

- Bounded queue sizes prevent memory bloat
- Automatic cleanup of completed spans
- Efficient serialization for export

## Error Handling

### Graceful Degradation

The telemetry module is designed to never break the main application:

```python
# Always works even if OpenTelemetry is not installed
@traced("operation")
def my_function():
    return "success"

# Telemetry failures are logged but don't propagate
with trace_performance("expensive_operation"):
    result = expensive_computation()
```

### Fallback Behavior

1. **Missing Dependencies**: Uses no-op tracers and decorators
2. **Network Issues**: Buffers locally with configurable limits
3. **Configuration Errors**: Falls back to disabled mode
4. **Authentication Failures**: Continues without GCP export

## Testing

Run the comprehensive test suite:

```bash
python zen/telemetry/test_telemetry.py
```

Tests cover:
- Configuration management and opt-out mechanism
- Data sanitization and PII filtering
- Instrumentation decorators (sync/async)
- Manager initialization and singleton behavior
- Error handling and graceful degradation
- Integration with zen orchestrator

## Dependencies

### Required (zen core)
- `zen_secrets`: Secure credential management

### Optional (telemetry features)
- `opentelemetry-api>=1.20.0`: Core OpenTelemetry
- `opentelemetry-sdk>=1.20.0`: OpenTelemetry SDK
- `opentelemetry-exporter-gcp-trace>=1.5.0`: Google Cloud integration
- `google-cloud-trace>=1.12.0`: Google Cloud Trace client
- `aiohttp>=3.8.0`: HTTP client for metadata service

Install telemetry dependencies:
```bash
pip install -r zen/telemetry/requirements.txt
```

## Advanced Usage

### Custom Instrumentation

```python
from zen.telemetry import traced, trace_performance, telemetry_manager

# Function-level tracing with custom attributes
@traced("data_processing", {"component": "parser"}, capture_args=True)
def process_data(data):
    return parsed_data

# Performance monitoring
with trace_performance("database_query", table="users", operation="select"):
    results = database.query("SELECT * FROM users")

# Manual span creation
with telemetry_manager.create_span("custom_operation") as span:
    span.set_attribute("custom.field", "value")
    result = do_work()
```

### Class Instrumentation

```python
from zen.telemetry import instrument_class

@instrument_class(methods=["process", "validate"], prefix="data")
class DataProcessor:
    def process(self, data):
        return self.validate(data)

    def validate(self, data):
        return data is not None
```

### Custom Data Sanitization

```python
from zen.telemetry.sanitization import DataSanitizer, SanitizationConfig

# Configure custom sanitization
custom_config = SanitizationConfig(
    sensitive_fields=["custom_field", "internal_id"],
    pii_patterns=[r"CUSTOM-\d{6}"],
    aggressive_mode=True
)

DataSanitizer.configure(custom_config)
```

## Monitoring and Observability

### Google Cloud Trace Integration

When properly configured, traces appear in Google Cloud Trace console:

1. **Service Map**: Visual representation of service dependencies
2. **Trace Timeline**: Detailed timing information for operations
3. **Performance Insights**: Latency distribution and error rates
4. **Custom Dashboards**: Create alerts and monitoring dashboards

### Key Metrics

Automatically captured metrics include:
- Operation duration and frequency
- Error rates and exception details
- Service dependencies and call patterns
- Performance bottlenecks and optimization opportunities

## Troubleshooting

### Common Issues

**Telemetry not working:**
```bash
# Check if disabled
echo $ZEN_TELEMETRY_DISABLED

# Enable debug logging
export PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from zen.telemetry import telemetry_manager
print(f'Enabled: {telemetry_manager.is_enabled()}')
"
```

**GCP export failing:**
```bash
# Check credentials
gcloud auth application-default print-access-token

# Check project configuration
echo $ZEN_TELEMETRY_GCP_PROJECT

# Test metadata service (on GCP)
curl -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/project/project-id
```

**Performance issues:**
```bash
# Reduce sampling rate
export ZEN_TELEMETRY_SAMPLE_RATE=0.01

# Increase batch size
export ZEN_TELEMETRY_BATCH_SIZE=1024

# Monitor queue size
export ZEN_TELEMETRY_QUEUE_SIZE=4096
```

### Debug Mode

Enable comprehensive debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Import with debug enabled
from zen.telemetry import telemetry_manager

# Check configuration
config = telemetry_manager.get_config()
print(f"Config: {config}")

# Test initialization
import asyncio
success = asyncio.run(telemetry_manager.initialize())
print(f"Initialization success: {success}")
```

## Contributing

When modifying the telemetry module:

1. **Run Tests**: Always run the full test suite
2. **Privacy First**: Ensure new features maintain PII protection
3. **Graceful Degradation**: Handle missing dependencies
4. **Performance**: Minimize overhead in hot paths
5. **Documentation**: Update this README for new features

## Security Considerations

### Data Handling
- All data is sanitized before transmission
- Credentials are managed through zen_secrets
- Network connections use secure protocols
- Local data is not persisted beyond memory buffers

### Access Control
- Service account permissions should follow principle of least privilege
- GCP IAM roles should be minimal for trace writing
- zen_secrets provides credential rotation and management

### Compliance
- GDPR compliance through PII filtering
- SOX compliance through audit trail capabilities
- HIPAA considerations through data sanitization
- Custom compliance patterns can be configured

For security issues, please follow the zen project security disclosure process.