# Zen Telemetry Setup and Capabilities Guide

## 🚀 Overview

The `netra-telemetry-public` feature provides **community-driven analytics** for the Zen orchestrator - a key differentiator from Apex's commercial analytics. This implementation follows **Path 1** of the OpenTelemetry plan: **Anonymous Public Telemetry with no authentication required**.

### **🌍 What Makes Zen Different from Apex**

**Zen (Open Source)**:
- ✅ **Community Analytics**: Anonymous usage trends visible to everyone
- ✅ **No Authentication**: Works out-of-the-box with embedded credentials
- ✅ **Public Insights**: Aggregate data contributes to open community knowledge
- ✅ **Free**: No cost for telemetry - Netra covers all GCP expenses

**Apex (Commercial)**:
- 🔒 **Private Analytics**: Data isolated to paying customers only
- 🔒 **Authentication Required**: OAuth/API keys needed
- 🔒 **Proprietary Insights**: Data locked behind commercial license
- 💰 **Paid**: Premium pricing for advanced analytics

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Capabilities](#capabilities)
- [Usage Examples](#usage-examples)
- [Privacy & Security](#privacy--security)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

---

## 🚀 Quick Start

### Community Analytics Enabled (Default)
```python
import zen  # Community analytics auto-enabled - no setup required!

# Your anonymous usage data now contributes to:
# - Community usage trends
# - Performance benchmarks
# - Error rate statistics
# - Popular feature insights
```

**What happens automatically:**
- Anonymous traces sent to `netra-telemetry-public` GCP project
- No authentication or credentials needed
- Completely anonymous - no personal data collected
- Contributes to open community insights

### Disable Telemetry (3 Easy Ways)
```bash
# Method 1: Command-line flag (easiest)
zen --no-telemetry "/analyze-code"

# Method 2: Environment variable
export ZEN_TELEMETRY_DISABLED=true

# Method 3: Programmatic (in Python)
from zen.telemetry import disable_telemetry
disable_telemetry()
```

### Basic Usage
```python
from zen.telemetry import traced, trace_performance

@traced("my_operation")
def my_function(data):
    return process_data(data)

# Performance monitoring
with trace_performance("database_query"):
    result = db.query("SELECT * FROM users")
```

---

## 📦 Installation

### Prerequisites
- Python 3.8+
- Access to Google Cloud Platform (for trace export)
- zen_secrets configured for credential management

### Installation

#### Standard Installation (Community Analytics by Default)
```bash
# Install zen with community analytics enabled by default
pip install netra-zen
```

**✅ Community analytics enabled by default** - contributes to open source insights with zero setup.

#### Development Installation
```bash
# Install with additional development tools
pip install "netra-zen[dev]"
```

#### Disabling Telemetry (Multiple Options)

#### Option 1: Command-Line Flag (Easiest)
```bash
# Disable telemetry for a single zen command
zen --no-telemetry "/analyze-code"

# Disable telemetry for any zen operation
zen --no-telemetry --workspace ~/my-project
```

#### Option 2: Environment Variable
```bash
# Set environment variable before using zen
export ZEN_TELEMETRY_DISABLED=true
zen "/analyze-code"  # Telemetry disabled
```

#### Option 3: Programmatic Control
```python
# Disable telemetry in your Python code
from zen.telemetry import disable_telemetry, enable_telemetry

disable_telemetry()  # Disable for this session
# ... do work ...
enable_telemetry()   # Re-enable if needed
```

### Dependencies (Included Automatically)
When you install `netra-zen`, these OpenTelemetry packages are automatically included:
```
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-gcp-trace>=1.6.0
opentelemetry-instrumentation>=0.41b0
```
**No additional installation steps needed** - community analytics works immediately after `import zen`.

### Community Analytics Data Flow
```
Your Zen Usage → Anonymous Traces → netra-telemetry-public → Public Dashboards
                     ↓
              (All PII Filtered)
```
- **What's collected**: Function performance, error rates, usage patterns
- **What's NOT collected**: Your code, data, credentials, or personal information
- **Who benefits**: Entire open source community gets insights

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEN_TELEMETRY_DISABLED` | `false` | **Complete opt-out** from all telemetry |
| `ZEN_TELEMETRY_LEVEL` | `basic` | Collection level: `disabled`/`basic`/`detailed` |
| `ZEN_TELEMETRY_SAMPLE_RATE` | `0.1` | Sampling rate (0.0-1.0) for performance |
| `ZEN_TELEMETRY_GCP_PROJECT` | auto-detect | GCP project ID for trace export |
| `ZEN_SERVICE_NAME` | `zen-orchestrator` | Service identification in traces |
| `ZEN_TELEMETRY_BATCH_SIZE` | `512` | Batch size for trace export |
| `ZEN_TELEMETRY_QUEUE_SIZE` | `2048` | Memory queue size limit |
| `ZEN_TELEMETRY_EXPORT_TIMEOUT` | `30` | Network timeout (seconds) |

### Service Account Setup

#### 1. Create GCP Service Account
```bash
# Create service account for telemetry
gcloud iam service-accounts create zen-telemetry \
    --description="Zen Orchestrator Telemetry" \
    --display-name="Zen Telemetry"

# Grant trace writer permissions
gcloud projects add-iam-policy-binding netra-telemetry-public \
    --member="serviceAccount:zen-telemetry@netra-telemetry-public.iam.gserviceaccount.com" \
    --role="roles/cloudtrace.agent"
```

#### 2. Configure zen_secrets Integration
```python
from zen_secrets import SecretManager, SecretClassification

# Store service account credentials
secret_manager = SecretManager()
await secret_manager.store_secret(
    name="zen-telemetry-service-account",
    value=service_account_json,
    classification=SecretClassification.MEDIUM
)
```

### Configuration Examples

#### Development Environment
```bash
export ZEN_TELEMETRY_LEVEL=detailed
export ZEN_TELEMETRY_SAMPLE_RATE=1.0  # 100% sampling for dev
export ZEN_SERVICE_NAME=zen-dev
```

#### Production Environment
```bash
export ZEN_TELEMETRY_LEVEL=basic
export ZEN_TELEMETRY_SAMPLE_RATE=0.05  # 5% sampling for production
export ZEN_SERVICE_NAME=zen-prod
```

#### Privacy-First Environment
```bash
export ZEN_TELEMETRY_DISABLED=true  # Complete opt-out
```

---

## 🎯 Capabilities

### 1. **Automatic Instrumentation**
- **Zero-configuration setup**: Works immediately on `import zen`
- **Background initialization**: No performance impact on startup
- **Graceful degradation**: Continues working if telemetry fails

### 2. **Function Instrumentation**
```python
from zen.telemetry import traced

# Instrument any function
@traced("user_authentication")
def authenticate_user(username, password):
    # Function logic here
    return user

# Async function support
@traced("async_data_fetch")
async def fetch_user_data(user_id):
    return await db.get_user(user_id)
```

### 3. **Performance Monitoring**
```python
from zen.telemetry import trace_performance

# Context manager for performance tracking
with trace_performance("database_query") as span:
    span.set_attribute("query_type", "SELECT")
    result = db.query("SELECT * FROM users LIMIT 100")
    span.set_attribute("result_count", len(result))
```

### 4. **Class-Level Instrumentation**
```python
from zen.telemetry import instrument_class

@instrument_class(prefix="user_service")
class UserService:
    def create_user(self, data):
        # Automatically traced as "user_service.create_user"
        return self.db.create(data)

    def update_user(self, user_id, data):
        # Automatically traced as "user_service.update_user"
        return self.db.update(user_id, data)
```

### 5. **Data Sanitization**
Automatic PII detection and redaction:
- **Email addresses**: `user@example.com` → `[EMAIL_REDACTED]`
- **Phone numbers**: `555-123-4567` → `[PHONE_REDACTED]`
- **Credit cards**: `4111-1111-1111-1111` → `[CREDIT_CARD_REDACTED]`
- **API keys**: `sk_live_abc123` → `[API_KEY_REDACTED]`
- **Custom patterns**: Configurable regex patterns

### 6. **Error Tracking**
```python
from zen.telemetry import trace_error

try:
    risky_operation()
except Exception as e:
    trace_error(e, context={"operation": "data_processing"})
    raise
```

### 7. **Custom Attributes**
```python
from zen.telemetry import get_current_span

span = get_current_span()
if span:
    span.set_attribute("user.id", user_id)
    span.set_attribute("operation.complexity", "high")
    span.set_attribute("feature.flag", "new_algorithm_enabled")
```

---

## 📊 Usage Examples

### Basic Function Tracing
```python
from zen.telemetry import traced

@traced("email_service.send")
def send_email(to_address, subject, body):
    """Send email with automatic tracing"""
    # Email sending logic
    return {"status": "sent", "message_id": "msg_123"}

# Usage
result = send_email("user@example.com", "Welcome", "Hello!")
# Creates trace: email_service.send with sanitized email
```

### Advanced Performance Monitoring
```python
from zen.telemetry import trace_performance

class DatabaseService:
    def complex_query(self, filters):
        with trace_performance("db.complex_query") as span:
            # Add context to the span
            span.set_attribute("filter_count", len(filters))
            span.set_attribute("query_type", "analytics")

            # Perform the query
            result = self.execute_query(filters)

            # Add result metrics
            span.set_attribute("result_count", len(result))
            span.set_attribute("execution_time_ms", 150)

            return result
```

### Zen Orchestrator Integration
```python
# Automatic instrumentation of zen_orchestrator.py
from zen.zen_orchestrator import ClaudeInstanceOrchestrator

# These methods are automatically instrumented:
orchestrator = ClaudeInstanceOrchestrator()
orchestrator.run_instance(instance_id="prod-1")  # Traced as "orchestrator.run_instance"
orchestrator.run_all_instances()                 # Traced as "orchestrator.run_all_instances"
```

### Custom Telemetry Manager
```python
from zen.telemetry import TelemetryManager

# Get the global telemetry instance
telemetry = TelemetryManager.get_instance()

# Check if telemetry is enabled
if telemetry.is_enabled():
    # Create custom spans
    with telemetry.tracer.start_as_current_span("custom_operation") as span:
        span.set_attribute("operation.type", "batch_processing")
        # Your custom logic here
```

---

## 🔒 Privacy & Security

### Data Protection Guarantees

#### 1. **Complete Opt-Out**
```bash
# Zero telemetry data collection
export ZEN_TELEMETRY_DISABLED=true
```

#### 2. **Automatic PII Filtering**
All trace data is automatically sanitized:
```python
# Before sanitization (never sent):
{
    "user_email": "john.doe@company.com",
    "phone": "555-123-4567",
    "api_key": "sk_live_abc123def456"
}

# After sanitization (what gets sent):
{
    "user_email": "[EMAIL_REDACTED]",
    "phone": "[PHONE_REDACTED]",
    "api_key": "[API_KEY_REDACTED]"
}
```

#### 3. **Secure Credential Management**
- Service account credentials stored in zen_secrets
- Automatic credential rotation support
- Write-only GCP permissions (roles/cloudtrace.agent)
- No credential logging or exposure

#### 4. **Network Security**
- HTTPS/TLS 1.3 for all telemetry traffic
- Certificate validation enforced
- Configurable timeouts and retry policies
- Graceful handling of network failures

### Privacy Controls

#### Sampling Control
```bash
# Reduce data collection to 1%
export ZEN_TELEMETRY_SAMPLE_RATE=0.01
```

#### Level Control
```bash
# Minimal data collection
export ZEN_TELEMETRY_LEVEL=basic

# No telemetry
export ZEN_TELEMETRY_LEVEL=disabled
```

#### Custom Sanitization
```python
from zen.telemetry.sanitization import DataSanitizer

# Add custom PII patterns
sanitizer = DataSanitizer()
sanitizer.add_pattern(r'internal-id-\d+', '[INTERNAL_ID_REDACTED]')
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. **Telemetry Not Working**

**Symptoms**: No traces appearing in Google Cloud Console

**Diagnosis**:
```python
from zen.telemetry import TelemetryManager

telemetry = TelemetryManager.get_instance()
print(f"Enabled: {telemetry.is_enabled()}")
print(f"Project: {telemetry.config.gcp_project}")
print(f"Sample Rate: {telemetry.config.sample_rate}")
```

**Solutions**:
- Check `ZEN_TELEMETRY_DISABLED` environment variable
- Verify GCP service account credentials in zen_secrets
- Confirm GCP project permissions
- Check sampling rate (increase for testing)

#### 2. **Performance Impact**

**Symptoms**: Zen operations running slower

**Solutions**:
```bash
# Reduce sampling rate
export ZEN_TELEMETRY_SAMPLE_RATE=0.01

# Use basic level
export ZEN_TELEMETRY_LEVEL=basic

# Disable if needed
export ZEN_TELEMETRY_DISABLED=true
```

#### 3. **Missing Dependencies**

**Symptoms**: ImportError for OpenTelemetry packages

**Solution**:
```bash
pip install -r zen/telemetry/requirements.txt
```

#### 4. **Authentication Errors**

**Symptoms**: "Could not load credentials" errors

**Solutions**:
- Verify service account in zen_secrets:
  ```python
  from zen_secrets import SecretManager
  secret_manager = SecretManager()
  creds = await secret_manager.get_secret("zen-telemetry-service-account")
  ```
- Check GCP IAM permissions
- Verify service account key format (JSON)

### Debug Mode

Enable detailed logging:
```python
import logging
logging.getLogger('zen.telemetry').setLevel(logging.DEBUG)
```

### Health Check

```python
from zen.telemetry import health_check

status = health_check()
print(f"Status: {status['status']}")
print(f"Details: {status['details']}")
```

---

## 🏆 Best Practices

### 1. **Performance Optimization**

#### Sampling Strategy
```bash
# Development: High sampling for debugging
export ZEN_TELEMETRY_SAMPLE_RATE=1.0

# Staging: Medium sampling for testing
export ZEN_TELEMETRY_SAMPLE_RATE=0.1

# Production: Low sampling for efficiency
export ZEN_TELEMETRY_SAMPLE_RATE=0.01
```

#### Selective Instrumentation
```python
# Instrument critical paths only
@traced("critical_business_logic")
def process_payment(amount, card):
    return payment_gateway.charge(amount, card)

# Skip instrumentation for trivial operations
def log_debug_message(message):
    # No @traced decorator for simple logging
    logger.debug(message)
```

### 2. **Data Quality**

#### Meaningful Span Names
```python
# Good: Descriptive and hierarchical
@traced("user_service.authentication.validate_credentials")
def validate_credentials(username, password):
    pass

# Bad: Generic and unhelpful
@traced("function1")
def validate_credentials(username, password):
    pass
```

#### Rich Context Attributes
```python
@traced("order_processing.payment")
def process_payment(order):
    span = get_current_span()
    span.set_attribute("order.id", order.id)
    span.set_attribute("order.amount", order.amount)
    span.set_attribute("payment.method", order.payment_method)
    span.set_attribute("customer.tier", order.customer.tier)
```

### 3. **Security Best Practices**

#### Regular Credential Rotation
```python
# Set up automatic rotation in zen_secrets
from zen_secrets import SecretManager
secret_manager = SecretManager()
await secret_manager.enable_rotation(
    "zen-telemetry-service-account",
    rotation_days=90
)
```

#### PII Prevention
```python
# Never add PII to custom attributes
span.set_attribute("user.id", user.id)          # Good: Non-PII identifier
span.set_attribute("user.email", user.email)    # Bad: PII data
```

### 4. **Monitoring Setup**

#### Cloud Console Dashboards
1. Navigate to Google Cloud Trace console
2. Create custom dashboard for zen-orchestrator
3. Set up alerts for error rates and latency
4. Monitor quota usage and costs

#### Key Metrics to Track
- Request latency (95th percentile)
- Error rates by operation
- Throughput trends
- Resource utilization

---

## 📚 API Reference

### Core Functions

#### `@traced(operation_name: str)`
Decorator for automatic function instrumentation.

**Parameters**:
- `operation_name` (str): Name for the trace span

**Example**:
```python
@traced("data_processor.transform")
def transform_data(input_data):
    return processed_data
```

#### `trace_performance(operation_name: str)`
Context manager for performance monitoring.

**Parameters**:
- `operation_name` (str): Name for the performance span

**Returns**: Span object with timing context

**Example**:
```python
with trace_performance("database.bulk_insert") as span:
    span.set_attribute("record_count", len(records))
    db.bulk_insert(records)
```

#### `@instrument_class(prefix: str = None)`
Class decorator for automatic method instrumentation.

**Parameters**:
- `prefix` (str, optional): Prefix for span names

**Example**:
```python
@instrument_class(prefix="api_client")
class APIClient:
    def get_user(self, user_id):  # Traced as "api_client.get_user"
        pass
```

### TelemetryManager

#### `TelemetryManager.get_instance()`
Get the global telemetry manager singleton.

**Returns**: TelemetryManager instance

#### `is_enabled() -> bool`
Check if telemetry is currently enabled.

**Returns**: True if telemetry is active

#### `get_tracer() -> Tracer`
Get the OpenTelemetry tracer instance.

**Returns**: Configured tracer object

### Configuration

#### `TelemetryConfig`
Configuration class for telemetry settings.

**Attributes**:
- `enabled` (bool): Whether telemetry is enabled
- `level` (str): Collection level (disabled/basic/detailed)
- `sample_rate` (float): Sampling rate (0.0-1.0)
- `gcp_project` (str): GCP project ID
- `service_name` (str): Service identification

### Utilities

#### `disable_telemetry()`
Programmatically disable telemetry for this session.

**Example**:
```python
from zen.telemetry import disable_telemetry
disable_telemetry()  # Telemetry now disabled
```

#### `enable_telemetry()`
Programmatically enable telemetry for this session.

**Example**:
```python
from zen.telemetry import enable_telemetry
enable_telemetry()  # Telemetry now enabled
```

#### `is_telemetry_enabled() -> bool`
Check if telemetry is currently enabled.

**Returns**: True if telemetry is active, False otherwise

**Example**:
```python
from zen.telemetry import is_telemetry_enabled
if is_telemetry_enabled():
    print("Telemetry is active")
```

#### `get_current_span() -> Span`
Get the currently active span for adding attributes.

**Returns**: Current span or None

#### `trace_error(exception: Exception, context: dict = None)`
Record an exception in the current span.

**Parameters**:
- `exception` (Exception): The exception to record
- `context` (dict, optional): Additional context

#### `health_check() -> dict`
Perform a health check of the telemetry system.

**Returns**: Status dictionary with health information including enabled status, configuration, and diagnostics

**Example**:
```python
from zen.telemetry import health_check
status = health_check()
print(f"Telemetry status: {status['status']}")
```

---

## 🎯 Summary

The netra-telemetry-public feature provides community-driven analytics that differentiates Zen from commercial alternatives:

✅ **Zero-configuration community analytics** with automatic setup
✅ **Anonymous public insights** - no authentication required
✅ **Open source advantage** - community benefits from aggregate data
✅ **Complete privacy protection** with PII filtering and opt-out
✅ **Minimal performance impact** with optimized sampling
✅ **Production-ready** with comprehensive error handling

## 🌍 Community Analytics Dashboard

**Coming Soon**: Public dashboard at `analytics.zen.dev` showing:
- Global usage trends and patterns
- Performance benchmarks across the community
- Popular features and adoption rates
- Error rates and reliability metrics
- Comparative analysis vs proprietary tools

**This is what makes Zen different** - open, transparent, community-driven insights that benefit everyone, not just paying customers.

For additional support or questions, refer to the zen_secrets documentation and Google Cloud Trace console.