# OpenTelemetry Implementation Plan for Zen Library

## Overview
Implement minimal OpenTelemetry data capture for the Zen library with automatic Google Cloud export, enabled by default with opt-out capability.

## System Architecture

```mermaid
graph TB
    subgraph "Zen Library"
        A[User Application] --> B[zen/__init__.py]
        B -->|Auto-initialize| C[TelemetryManager]
        C -->|Check env vars| D{Telemetry Enabled?}
        D -->|Yes| E[Initialize TracerProvider]
        D -->|No| F[NoOp Tracer]
        E --> G[Configure GCP Exporter]
        G --> H[BatchSpanProcessor]
        H -->|Async export| I[Google Cloud Trace]
    end

    subgraph "Instrumented Functions"
        J[Traced Decorator] --> K[Function Execution]
        K --> L{Success?}
        L -->|Yes| M[Set OK Status]
        L -->|No| N[Record Exception]
        M --> O[Create Span]
        N --> O
        O --> H
    end

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style I fill:#9cf,stroke:#333,stroke-width:2px
    style D fill:#ff9,stroke:#333,stroke-width:2px
```

## Component Flow Diagram

```mermaid
flowchart LR
    subgraph "Initialization Flow"
        Start([Library Import]) --> Init{First Use?}
        Init -->|Yes| Check[Check ZEN_TELEMETRY_DISABLED]
        Init -->|No| Ready[Return Existing Instance]
        Check -->|Not Set| Enable[Enable Telemetry]
        Check -->|Set| Disable[Disable Telemetry]
        Enable --> GCP[Detect GCP Project]
        GCP -->|Found| Export[Setup Cloud Exporter]
        GCP -->|Not Found| Local[Local Tracing Only]
        Export --> Ready
        Local --> Ready
        Disable --> NoOp[NoOp Implementation]
        NoOp --> Ready
    end
```

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant App as Application
    participant Zen as Zen Library
    participant TM as TelemetryManager
    participant Trace as OpenTelemetry
    participant GCP as Google Cloud

    App->>Zen: import zen
    Zen->>TM: initialize()
    TM->>TM: Check ENV vars

    alt Telemetry Enabled
        TM->>Trace: Create TracerProvider
        TM->>GCP: Setup CloudTraceExporter
        TM-->>Zen: Ready
    else Telemetry Disabled
        TM-->>Zen: NoOp Mode
    end

    App->>Zen: orchestrator.run()
    Zen->>Trace: Start Span
    Note over Trace: Function executes

    alt Success
        Trace->>Trace: Set OK Status
    else Error
        Trace->>Trace: Record Exception
    end

    Trace->>GCP: Export Span (async)
    Trace-->>Zen: Return result
    Zen-->>App: Result
```

## Class Diagram

```mermaid
classDiagram
    class TelemetryManager {
        -_instance: TelemetryManager
        -_initialized: bool
        +initialize() void
        +tracer: Tracer
    }

    class TelemetryConfig {
        +is_enabled() bool
        +get_gcp_project() str
        +get_service_name() str
        +get_sample_rate() float
    }

    class CloudExporter {
        -exporter: CloudTraceSpanExporter
        -processor: BatchSpanProcessor
        +setup_gcp_exporter(provider) void
    }

    class Instrumentation {
        +traced(name, attributes) decorator
        +add_span_attributes(**kwargs) void
    }

    class ZenOrchestrator {
        +run(config) void
        +process_command(command) void
    }

    TelemetryManager --> TelemetryConfig: uses
    TelemetryManager --> CloudExporter: configures
    ZenOrchestrator --> Instrumentation: decorated by
    Instrumentation --> TelemetryConfig: checks
```

## Architecture Design

### Core Components

1. **Telemetry Module** (`zen/telemetry/__init__.py`)
   - Singleton telemetry manager
   - Lazy initialization on first use
   - Automatic shutdown handling

2. **Configuration** (`zen/telemetry/config.py`)
   - Environment variable checking for opt-out
   - Google Cloud project detection
   - Service name and version configuration

3. **Instrumentation** (`zen/telemetry/instrumentation.py`)
   - Decorator for automatic tracing
   - Context propagation helpers
   - Error capture and reporting

## Implementation Steps

### Step 1: Add Dependencies
Update `pyproject.toml` or `requirements.txt`:
```python
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-gcp-trace>=1.6.0
opentelemetry-instrumentation>=0.41b0
```

### Step 2: Create Telemetry Module Structure
```
zen/
├── telemetry/
│   ├── __init__.py       # Main telemetry interface
│   ├── config.py         # Configuration and opt-out logic
│   ├── exporter.py       # Google Cloud exporter setup
│   └── instrumentation.py # Decorators and helpers
```

### Step 3: Implement Configuration Module
```python
# zen/telemetry/config.py
import os
from typing import Optional

class TelemetryConfig:
    @staticmethod
    def is_enabled() -> bool:
        """Check if telemetry is enabled (default: True)"""
        opt_out = os.environ.get('ZEN_TELEMETRY_DISABLED', '').lower()
        return opt_out not in ('true', '1', 'yes')

    @staticmethod
    def get_gcp_project() -> Optional[str]:
        """Get GCP project from environment or metadata"""
        return os.environ.get('GOOGLE_CLOUD_PROJECT') or \
               os.environ.get('GCP_PROJECT') or \
               _detect_gcp_project()

    @staticmethod
    def get_service_name() -> str:
        """Get service name for telemetry"""
        return os.environ.get('ZEN_SERVICE_NAME', 'zen-library')
```

### Step 4: Implement Telemetry Manager
```python
# zen/telemetry/__init__.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from .config import TelemetryConfig
from .exporter import setup_gcp_exporter

class TelemetryManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize telemetry if enabled"""
        if self._initialized or not TelemetryConfig.is_enabled():
            return

        # Create resource with service metadata
        resource = Resource.create({
            "service.name": TelemetryConfig.get_service_name(),
            "service.version": get_zen_version(),
            "telemetry.sdk.language": "python",
            "telemetry.sdk.name": "opentelemetry",
        })

        # Setup tracer provider
        provider = TracerProvider(resource=resource)

        # Add GCP exporter if project is available
        if TelemetryConfig.get_gcp_project():
            setup_gcp_exporter(provider)

        trace.set_tracer_provider(provider)
        self._initialized = True

    @property
    def tracer(self):
        """Get tracer instance"""
        self.initialize()
        if TelemetryConfig.is_enabled():
            return trace.get_tracer(__name__)
        return NoOpTracer()

# Global instance
telemetry = TelemetryManager()
```

### Step 5: Implement Google Cloud Exporter
```python
# zen/telemetry/exporter.py
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import logging

logger = logging.getLogger(__name__)

def setup_gcp_exporter(provider):
    """Setup Google Cloud Trace exporter"""
    try:
        exporter = CloudTraceSpanExporter()
        processor = BatchSpanProcessor(
            exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        )
        provider.add_span_processor(processor)
        logger.debug("Google Cloud Trace exporter configured")
    except Exception as e:
        logger.warning(f"Failed to setup GCP exporter: {e}")
```

### Step 6: Create Instrumentation Decorators
```python
# zen/telemetry/instrumentation.py
from functools import wraps
from opentelemetry import trace
from .config import TelemetryConfig

def traced(name: str = None, attributes: dict = None):
    """Decorator to add tracing to functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not TelemetryConfig.is_enabled():
                return func(*args, **kwargs)

            tracer = trace.get_tracer(__name__)
            span_name = name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(
                span_name,
                attributes=attributes or {}
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(
                        trace.Status(trace.StatusCode.ERROR, str(e))
                    )
                    raise

        return wrapper
    return decorator

def add_span_attributes(**attributes):
    """Add attributes to current span"""
    if not TelemetryConfig.is_enabled():
        return

    span = trace.get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
```

### Step 7: Integrate with Core Zen Functions
```python
# zen_orchestrator.py (example integration)
from zen.telemetry.instrumentation import traced

class ZenOrchestrator:
    @traced("zen.orchestrator.run", {"operation": "main_loop"})
    def run(self, config):
        """Main orchestration loop with telemetry"""
        # Existing implementation
        pass

    @traced("zen.orchestrator.process_command")
    def process_command(self, command):
        """Process command with telemetry"""
        # Existing implementation
        pass
```

### Step 8: Auto-initialization
```python
# zen/__init__.py (add to existing file)
from .telemetry import telemetry

# Initialize telemetry on import
telemetry.initialize()
```

## Usage Examples

### Default Behavior (Telemetry Enabled)
```python
import zen

# Telemetry is automatically initialized and sending to GCP
orchestrator = zen.ZenOrchestrator()
orchestrator.run(config)  # Traced automatically
```

### Opt-Out via Environment Variable
```bash
# Disable telemetry
export ZEN_TELEMETRY_DISABLED=true

# Or
export ZEN_TELEMETRY_DISABLED=1

# Run application - no telemetry data collected
python my_app.py
```

### Custom Instrumentation
```python
from zen.telemetry.instrumentation import traced, add_span_attributes

@traced("custom.operation")
def my_function():
    add_span_attributes(
        user_id="123",
        operation_type="batch_process"
    )
    # Function logic
```

## GCP Project ID Configuration & Security

### Project ID Loading Hierarchy

```mermaid
flowchart TD
    Start([Need GCP Project]) --> Env1{ZEN_GCP_PROJECT set?}
    Env1 -->|Yes| Use1[Use ZEN_GCP_PROJECT]
    Env1 -->|No| Env2{GOOGLE_CLOUD_PROJECT set?}

    Env2 -->|Yes| Use2[Use GOOGLE_CLOUD_PROJECT]
    Env2 -->|No| Env3{GCP_PROJECT set?}

    Env3 -->|Yes| Use3[Use GCP_PROJECT]
    Env3 -->|No| Meta{Running on GCP?}

    Meta -->|Yes| Metadata[Query Metadata Service]
    Meta -->|No| Fallback[Use Zen Default Project]

    Metadata --> Valid{Valid Response?}
    Valid -->|Yes| UseMetadata[Use Metadata Project]
    Valid -->|No| Fallback

    Use1 --> Validate[Validate Project ID Format]
    Use2 --> Validate
    Use3 --> Validate
    UseMetadata --> Validate
    Fallback --> Validate

    Validate --> Final[Configure Exporter]

    style Fallback fill:#ffc,stroke:#333,stroke-width:2px
    style Validate fill:#cfc,stroke:#333,stroke-width:2px
```

### Configuration Implementation

```python
# zen/telemetry/config.py
import os
import re
import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class GCPConfig:
    # Zen's default public project for community telemetry
    DEFAULT_PUBLIC_PROJECT = "zen-telemetry-public"

    # Regex for valid GCP project IDs
    PROJECT_ID_PATTERN = re.compile(r'^[a-z][a-z0-9-]{4,28}[a-z0-9]$')

    @classmethod
    def get_project_id(cls) -> str:
        """
        Get GCP project ID with fallback hierarchy:
        1. ZEN_GCP_PROJECT (for Zen-specific override)
        2. GOOGLE_CLOUD_PROJECT (standard GCP env var)
        3. GCP_PROJECT (alternate GCP env var)
        4. GCP Metadata service (if on GCP)
        5. Zen's default public project
        """
        # Check environment variables in order
        for env_var in ['ZEN_GCP_PROJECT', 'GOOGLE_CLOUD_PROJECT', 'GCP_PROJECT']:
            project_id = os.environ.get(env_var)
            if project_id and cls._validate_project_id(project_id):
                logger.debug(f"Using GCP project from {env_var}: {project_id}")
                return project_id

        # Try GCP metadata service
        metadata_project = cls._get_metadata_project()
        if metadata_project:
            logger.debug(f"Using GCP project from metadata: {metadata_project}")
            return metadata_project

        # Fall back to Zen's public project
        logger.info(f"Using Zen default public project: {cls.DEFAULT_PUBLIC_PROJECT}")
        return cls.DEFAULT_PUBLIC_PROJECT

    @classmethod
    def _validate_project_id(cls, project_id: str) -> bool:
        """Validate GCP project ID format"""
        if not cls.PROJECT_ID_PATTERN.match(project_id):
            logger.warning(f"Invalid GCP project ID format: {project_id}")
            return False
        return True

    @classmethod
    def _get_metadata_project(cls) -> Optional[str]:
        """Query GCP metadata service for project ID"""
        try:
            response = requests.get(
                "http://metadata.google.internal/computeMetadata/v1/project/project-id",
                headers={"Metadata-Flavor": "Google"},
                timeout=1.0
            )
            if response.status_code == 200:
                project_id = response.text.strip()
                if cls._validate_project_id(project_id):
                    return project_id
        except Exception:
            pass  # Not on GCP or metadata unavailable
        return None
```

### Public Project Implications

```mermaid
graph LR
    subgraph "User's Environment"
        A[Zen Library] -->|Sends traces| B{Which Project?}
    end

    subgraph "Project Types"
        B -->|User's Project| C[Private GCP Project]
        B -->|No Config| D[zen-telemetry-public]

        C --> E[User Controls]
        C --> F[User Pays]
        C --> G[User's Data]

        D --> H[Zen Controls]
        D --> I[Zen Pays]
        D --> J[Aggregated Data]
    end

    subgraph "Security & Privacy"
        G --> K[Full Isolation]
        J --> L[Shared Pool]
        L --> M[No PII]
        L --> N[Rate Limited]
        L --> O[Sampled]
    end

    style D fill:#ffc,stroke:#333,stroke-width:2px
    style C fill:#cfc,stroke:#333,stroke-width:2px
```

### Rate Limiting & Quotas

```python
# zen/telemetry/rate_limiter.py
from time import time
from threading import Lock
from typing import Dict, Tuple

class TelemetryRateLimiter:
    """
    Rate limiter for telemetry to prevent quota exhaustion
    """
    def __init__(self):
        self.limits = {
            'zen-telemetry-public': {
                'spans_per_minute': 1000,
                'spans_per_hour': 10000,
                'bytes_per_minute': 1_000_000  # 1MB
            },
            'default': {
                'spans_per_minute': 10000,
                'spans_per_hour': 100000,
                'bytes_per_minute': 10_000_000  # 10MB
            }
        }
        self.counters: Dict[str, Tuple[float, int]] = {}
        self.lock = Lock()

    def should_send(self, project_id: str, span_size: int) -> bool:
        """Check if span should be sent based on rate limits"""
        with self.lock:
            limits = self.limits.get(project_id, self.limits['default'])
            current_time = time()

            # Check per-minute limit
            minute_key = f"{project_id}:minute"
            minute_start, minute_count = self.counters.get(minute_key, (current_time, 0))

            if current_time - minute_start > 60:
                # Reset minute counter
                self.counters[minute_key] = (current_time, 1)
            elif minute_count >= limits['spans_per_minute']:
                logger.warning(f"Rate limit exceeded for {project_id}")
                return False
            else:
                self.counters[minute_key] = (minute_start, minute_count + 1)

            return True
```

### Security Considerations

```mermaid
mindmap
  root((GCP Project Security))
    Public Project Risks
      Data Exposure
        Aggregated only
        No user secrets
        Function names visible
      Resource Limits
        Shared quotas
        Rate limiting
        Potential blocking
      Access Control
        Read-only for users
        Zen admin access
        Public dashboards
    Private Project Benefits
      Full Control
        Custom quotas
        Access policies
        Data retention
      Cost Management
        Direct billing
        Usage monitoring
        Budget alerts
      Compliance
        Data residency
        Audit logs
        Regulatory needs
    Mitigation Strategies
      Default Sampling
        10% rate
        Configurable
        Reduces volume
      Data Filtering
        No PII
        No credentials
        Technical only
      Automatic Fallback
        Graceful degradation
        Local-only mode
        Silent failures
```

## Environment Variables

| Variable | Description | Default | Security Notes |
|----------|-------------|---------|----------------|
| `ZEN_TELEMETRY_DISABLED` | Set to `true`, `1`, or `yes` to disable telemetry | `false` (enabled) | Immediate opt-out |
| `ZEN_GCP_PROJECT` | Override GCP project for Zen telemetry | None | Use for private isolation |
| `GOOGLE_CLOUD_PROJECT` | Standard GCP project ID | Auto-detected | Respects existing GCP config |
| `GCP_PROJECT` | Alternate GCP project ID | Auto-detected | Fallback option |
| `ZEN_SERVICE_NAME` | Service name in traces | `zen-library` | Identifies your service |
| `ZEN_TELEMETRY_SAMPLE_RATE` | Sampling rate (0.0-1.0) | `0.1` (10%) | Reduces data volume |
| `ZEN_TELEMETRY_BATCH_SIZE` | Max spans per batch | `512` | Controls memory usage |
| `ZEN_TELEMETRY_FLUSH_INTERVAL` | Seconds between exports | `5` | Balances latency/efficiency |

## Privacy and Security Considerations

```mermaid
mindmap
  root((Telemetry Security))
    Data Collection
      No PII
        Function names only
        No user data
        No credentials
      Minimal scope
        Technical metrics
        Error rates
        Latency data
    Transport Security
      HTTPS only
      TLS 1.3
      Certificate validation
      No fallback to HTTP
    Privacy Controls
      Opt-out mechanism
        Environment variable
        Immediate effect
        No restart needed
      Data sampling
        10% default rate
        Configurable
        Reduces data volume
    Data Handling
      Google Cloud compliance
        SOC 2
        ISO 27001
        GDPR compliant
      Retention policies
        30 day default
        Auto-deletion
        No long-term storage
```

## Data Privacy Flow

```mermaid
flowchart TB
    subgraph "Data Collection"
        A[Function Call] --> B{Contains PII?}
        B -->|Yes| C[Filter Out]
        B -->|No| D[Add to Trace]
        C --> E[Technical Data Only]
        D --> E
    end

    subgraph "Sampling Decision"
        E --> F{Within Sample Rate?}
        F -->|Yes 10%| G[Process Span]
        F -->|No 90%| H[Discard]
    end

    subgraph "Export Pipeline"
        G --> I[Batch Processor]
        I --> J{Batch Ready?}
        J -->|Yes| K[Encrypt with TLS]
        J -->|No| L[Buffer]
        K --> M[Send to GCP]
    end

    subgraph "User Control"
        N[ENV: ZEN_TELEMETRY_DISABLED] -.->|Override| B
        N -.-> F
    end

    style A fill:#f9f9f9
    style M fill:#9cf
    style H fill:#fcc
    style N fill:#ffc
```

## Performance Impact

- **Minimal Overhead**: < 1% CPU overhead with default sampling
- **Async Export**: Telemetry export happens in background threads
- **Bounded Queues**: Prevents memory issues under high load
- **Automatic Batching**: Reduces network calls

## Testing

### Unit Tests
```python
# tests/test_telemetry.py
import os
import pytest
from zen.telemetry.config import TelemetryConfig

def test_opt_out():
    os.environ['ZEN_TELEMETRY_DISABLED'] = 'true'
    assert not TelemetryConfig.is_enabled()

def test_default_enabled():
    os.environ.pop('ZEN_TELEMETRY_DISABLED', None)
    assert TelemetryConfig.is_enabled()
```

### Integration Tests
```python
def test_gcp_export():
    # Mock GCP exporter
    # Verify spans are exported correctly
    pass
```

## Rollout Plan

```mermaid
gantt
    title OpenTelemetry Implementation Roadmap
    dateFormat YYYY-MM-DD
    section Phase 1
    Core Telemetry Module           :a1, 2025-01-20, 5d
    Opt-out Mechanism               :a2, after a1, 2d
    Basic Tests                     :a3, after a2, 3d

    section Phase 2
    Instrument Critical Paths       :b1, after a3, 5d
    Add GCP Exporter               :b2, after b1, 3d
    Integration Tests              :b3, after b2, 3d

    section Phase 3
    Monitor Usage Patterns         :c1, after b3, 7d
    Adjust Sampling Rates         :c2, after c1, 2d
    Performance Optimization      :c3, after c2, 3d

    section Phase 4
    Custom Metrics                :d1, after c3, 5d
    Enhanced Instrumentation      :d2, after d1, 5d
    Documentation & Examples      :d3, after d2, 3d
```

## Telemetry Decision Tree

```mermaid
graph TD
    Start([Zen Library Imported]) --> Check{ZEN_TELEMETRY_DISABLED?}
    Check -->|Not Set| Default[Enable Telemetry]
    Check -->|true/1/yes| Disabled[Disable Telemetry]

    Default --> GCPCheck{GCP Project Available?}
    GCPCheck -->|Yes| CloudExport[Export to Cloud Trace]
    GCPCheck -->|No| LocalOnly[Local Traces Only]

    CloudExport --> Sample{Sample Rate Check}
    LocalOnly --> Sample
    Sample -->|Within Rate| Collect[Collect Span]
    Sample -->|Outside Rate| Skip[Skip Collection]

    Collect --> Batch[Add to Batch]
    Batch --> Export{Batch Full?}
    Export -->|Yes| Send[Send to GCP]
    Export -->|No| Wait[Wait for More]

    Disabled --> NoOp[No Operation]
    Skip --> NoOp

    style Start fill:#e1f5e1
    style CloudExport fill:#b3d9ff
    style Disabled fill:#ffcccc
    style NoOp fill:#f0f0f0
```

## Documentation Updates

Update README.md with:
- Telemetry section explaining default behavior
- Opt-out instructions prominently displayed
- Link to this implementation plan
- Privacy policy statement

## Monitoring and Alerts

Set up in Google Cloud:
- Dashboard for library usage metrics
- Error rate alerts
- Performance degradation alerts
- Usage anomaly detection