# NETRA APEX TECHNICAL ARCHITECTURE
## System Design & Data Flow Documentation

---

# SYSTEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                         CUSTOMER ENVIRONMENT                      │
├─────────────────────────────────────────────────────────────────┤
│  Applications  →  Changed Base URL  →  api.netrasystems.ai         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APEX GATEWAY LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Request  │→ │Optimize  │→ │ Execute  │→ │Attribute │       │
│  │Intercept │  │ Engine   │  │ Provider │  │ Savings  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│   LLM PROVIDERS  │ │  VALIDATION  │ │    ANALYTICS     │
├──────────────────┤ │   WORKBENCH  │ │   & TELEMETRY    │
│ • OpenAI         │ │              │ │                  │
│ • Anthropic      │ │ • Terraform  │ │ • Clickhouse     │
│ • Azure          │ │ • Sandbox    │ │ • CloudWatch     │
│ • Cohere         │ │ • Workload   │ │ • Metrics        │
└──────────────────┘ └──────────────┘ └──────────────────┘
```

---

# COMPONENT ARCHITECTURE

## 1. GATEWAY CORE ARCHITECTURE

### Request Flow Pipeline
```python
# Data flow through Gateway components

REQUEST_PIPELINE = [
    "1. HTTP/HTTPS Request Received",
    "2. Authentication & Rate Limiting",  
    "3. Request Parser & Validator",
    "4. Optimization Pipeline",
    "5. Provider Router",
    "6. Response Handler",
    "7. Attribution Engine",
    "8. Response Formatter"
]
```

### Gateway Component Specification
```yaml
gateway:
  proxy_core:
    max_lines: 250
    responsibilities:
      - HTTP server setup
      - Request routing
      - Connection pooling
      - Keep-alive management
    
  interceptor:
    max_lines: 200
    responsibilities:
      - Request parsing
      - Header manipulation
      - Body extraction
      - Provider detection
      
  router:
    max_lines: 150
    responsibilities:
      - Provider selection
      - Load balancing
      - Circuit breaking
      - Fallback logic
```

## 2. OPTIMIZATION ENGINE ARCHITECTURE

### Multi-Stage Optimization Pipeline
```
REQUEST → [CACHE CHECK] → [COMPRESSION] → [ROUTING] → [BATCHING] → OPTIMIZED
             ↓                ↓              ↓            ↓
          15-25%           10-15%         20-30%       5-10%
          savings          savings        savings      savings
```

### Optimization Stages Detail
```python
class OptimizationArchitecture:
    stages = {
        "semantic_cache": {
            "savings_range": "15-25%",
            "latency_impact": "-50ms (cache hit)",
            "implementation": "Redis with vector similarity"
        },
        "prompt_compression": {
            "savings_range": "10-15%", 
            "latency_impact": "+10ms",
            "implementation": "Token reduction algorithms"
        },
        "model_routing": {
            "savings_range": "20-30%",
            "latency_impact": "0ms",
            "implementation": "Cost/quality optimizer"
        },
        "request_batching": {
            "savings_range": "5-10%",
            "latency_impact": "+100ms (wait time)",
            "implementation": "Time-window aggregation"
        }
    }
```

## 3. PROOF-OF-VALUE (PoV) ENGINE

### Attribution Flow
```
┌────────────────────────────────────────────────┐
│              A/B TESTING FRAMEWORK              │
├────────────────────────────────────────────────┤
│                                                 │
│  10% Traffic → Baseline (No Optimization)      │
│  90% Traffic → Optimized Path                  │
│                                                 │
│  Metrics Captured:                             │
│  • Token Count Delta                           │
│  • Latency Delta                               │
│  • Cost Delta                                  │
│  • Quality Score (via sampling)                │
│                                                 │
└────────────────────────────────────────────────┘
                        │
                        ▼
            ┌──────────────────────┐
            │  SAVINGS CALCULATION  │
            ├──────────────────────┤
            │ VBP Amount = Delta    │
            │     × 0.20 (20%)     │
            └──────────────────────┘
```

## 4. VALIDATION WORKBENCH ARCHITECTURE

### Validation Pipeline
```
CUSTOMER REQUEST
       ↓
[GENERATE TERRAFORM]
       ↓
[PROVISION SANDBOX]
       ↓
[DEPLOY INFRASTRUCTURE]
       ↓
[REPLAY WORKLOAD]
       ↓
[MEASURE PERFORMANCE]
       ↓
[CALCULATE BVM]
       ↓
[GENERATE REPORT]
```

### Sandbox Isolation Model
```yaml
sandbox_architecture:
  isolation_level: "customer"
  
  resource_allocation:
    per_customer:
      vcpu: 16
      memory_gb: 64
      storage_gb: 500
      
  network_isolation:
    type: "vpc_per_customer"
    ingress: "restricted"
    egress: "metered"
    
  billing_model:
    base_cost: "AWS/Azure actual"
    markup: "50%"
    minimum_charge: "$10"
```

---

# DATA MODELS

## Core Request/Response Models

```python
# app/schemas/gateway_models.py

class LLMRequest(BaseModel):
    """Incoming LLM request - all providers normalized"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    customer_id: str
    provider: Literal["openai", "anthropic", "azure", "cohere"]
    endpoint: str  # e.g., "/v1/completions"
    
    # Normalized parameters
    prompt: str
    model: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    
    # Original request for passthrough
    raw_body: Dict[str, Any]
    raw_headers: Dict[str, str]
    
    # Tracking
    tier: Literal["free", "early", "mid", "enterprise"]
    
class OptimizationMetrics(BaseModel):
    """Metrics from optimization pipeline"""
    cache_hit: bool = False
    compression_ratio: float = 1.0
    original_tokens: int
    optimized_tokens: int
    routing_decision: str
    estimated_savings: Decimal
    
class LLMResponse(BaseModel):
    """Response to send back to customer"""
    request_id: str
    provider_response: Dict[str, Any]
    
    # Apex additions
    apex_metadata: Dict[str, Any] = {
        "optimizations_applied": [],
        "tokens_saved": 0,
        "cost_saved": 0.0,
        "cache_hit": False
    }
```

## Billing & Usage Models

```python
# app/schemas/billing_models.py

class UsageRecord(BaseModel):
    """Individual usage record for billing"""
    customer_id: str
    timestamp: datetime
    
    # Usage metrics
    requests_count: int
    tokens_processed: int
    tokens_saved: int
    
    # Cost metrics
    baseline_cost: Decimal
    optimized_cost: Decimal
    savings: Decimal
    vbp_charge: Decimal  # 20% of savings
    
    # BVM metrics
    validation_minutes: int = 0
    bvm_charge: Decimal = Decimal("0.00")
    
class SubscriptionTier(BaseModel):
    """Customer subscription tier"""
    customer_id: str
    tier: Literal["free", "early", "mid", "enterprise"]
    
    # Limits
    requests_per_hour: int
    tokens_per_month: int
    validation_minutes_included: int
    
    # Pricing
    base_fee: Decimal
    vbp_percentage: float = 0.20
    bvm_rate_per_minute: Decimal = Decimal("0.50")
    
    # Features
    features_enabled: List[str]
    
class Invoice(BaseModel):
    """Monthly invoice"""
    invoice_id: str
    customer_id: str
    period_start: datetime
    period_end: datetime
    
    # Line items
    base_subscription: Decimal
    vbp_charges: Decimal
    bvm_charges: Decimal
    
    # Totals
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    
    # Supporting data
    total_savings_generated: Decimal
    total_validation_minutes: int
```

## Validation Workbench Models

```python
# app/schemas/validation_models.py

class ValidationRequest(BaseModel):
    """Request to validate infrastructure config"""
    customer_id: str
    terraform_config: str
    workload_profile: 'WorkloadProfile'
    
    # Options
    sandbox_type: Literal["managed", "customer_vpc"] = "managed"
    max_duration_minutes: int = 30
    comparison_baseline: Optional[str] = None
    
class WorkloadProfile(BaseModel):
    """Captured workload for replay"""
    captured_from: datetime
    captured_to: datetime
    
    # Request patterns
    requests: List[LLMRequest]
    request_rate: float  # requests per second
    
    # Traffic characteristics
    token_distribution: Dict[str, int]
    model_usage: Dict[str, float]
    
class ValidationResult(BaseModel):
    """Results from validation run"""
    validation_id: str
    customer_id: str
    
    # Performance metrics
    baseline_metrics: 'PerformanceMetrics'
    optimized_metrics: 'PerformanceMetrics'
    
    # Cost analysis
    baseline_cost: Decimal
    optimized_cost: Decimal
    savings_percentage: float
    
    # BVM billing
    sandbox_minutes_used: int
    bvm_cost: Decimal
    
    # Report
    detailed_report_url: str
    recommendations: List[str]
    
class PerformanceMetrics(BaseModel):
    """Performance measurement"""
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    
    error_rate: float
    throughput_rps: float
    
    # Resource utilization
    cpu_utilization: float
    memory_utilization: float
    gpu_utilization: Optional[float]
```

---

# DATABASE ARCHITECTURE

## Primary Database (PostgreSQL)

```sql
-- Core customer and billing data

CREATE SCHEMA apex;

-- Customers and authentication
CREATE TABLE apex.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    company_name VARCHAR(255),
    tier VARCHAR(50) NOT NULL DEFAULT 'free',
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    trial_ends_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Usage tracking (hot data)
CREATE TABLE apex.usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES apex.customers(id),
    timestamp TIMESTAMP NOT NULL,
    endpoint VARCHAR(255),
    provider VARCHAR(50),
    
    -- Metrics
    tokens_original INTEGER,
    tokens_optimized INTEGER,
    tokens_saved INTEGER,
    
    -- Costs
    baseline_cost DECIMAL(10,6),
    optimized_cost DECIMAL(10,6),
    savings DECIMAL(10,6),
    vbp_charge DECIMAL(10,6),
    
    -- Optimization details
    cache_hit BOOLEAN DEFAULT false,
    optimizations_applied JSONB,
    
    INDEX idx_customer_timestamp (customer_id, timestamp DESC)
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE apex.usage_records_2025_01 
    PARTITION OF apex.usage_records 
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
    
-- Validation jobs
CREATE TABLE apex.validation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES apex.customers(id),
    
    -- Job details
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Configuration
    terraform_config TEXT,
    workload_data JSONB,
    
    -- Results
    baseline_metrics JSONB,
    optimized_metrics JSONB,
    savings_percentage DECIMAL(5,2),
    
    -- BVM billing
    sandbox_minutes INTEGER,
    bvm_cost DECIMAL(10,2),
    
    -- Report
    report_url VARCHAR(500),
    error_message TEXT
);

-- Billing and invoices
CREATE TABLE apex.invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES apex.customers(id),
    
    -- Period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Charges
    base_subscription DECIMAL(10,2),
    vbp_charges DECIMAL(10,2),
    bvm_charges DECIMAL(10,2),
    total DECIMAL(10,2),
    
    -- Status
    status VARCHAR(50) NOT NULL,
    stripe_invoice_id VARCHAR(255),
    paid_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Analytics Database (ClickHouse)

```sql
-- High-performance analytics for telemetry

CREATE DATABASE apex;

-- Request logs (for analysis)
CREATE TABLE apex.request_logs (
    timestamp DateTime,
    customer_id UUID,
    request_id UUID,
    
    -- Request details
    provider LowCardinality(String),
    endpoint LowCardinality(String),
    model LowCardinality(String),
    
    -- Metrics
    tokens_input UInt32,
    tokens_output UInt32,
    latency_ms UInt32,
    
    -- Optimization
    cache_hit UInt8,
    compression_ratio Float32,
    routing_decision LowCardinality(String),
    
    -- Costs
    baseline_cost Decimal64(6),
    optimized_cost Decimal64(6),
    savings Decimal64(6)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (customer_id, timestamp);

-- Aggregated metrics (materialized view)
CREATE MATERIALIZED VIEW apex.customer_metrics_hourly
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (customer_id, hour)
AS SELECT
    toStartOfHour(timestamp) as hour,
    customer_id,
    provider,
    
    count() as requests,
    sum(tokens_input + tokens_output) as total_tokens,
    sum(savings) as total_savings,
    
    avg(latency_ms) as avg_latency,
    quantile(0.95)(latency_ms) as p95_latency,
    
    sum(cache_hit) / count() as cache_hit_rate
FROM apex.request_logs
GROUP BY hour, customer_id, provider;
```

## Cache Layer (Redis)

```python
# Cache architecture

REDIS_STRUCTURE = {
    # Semantic cache for responses
    "cache:semantic:{hash}": {
        "type": "string",
        "ttl": 3600,  # 1 hour
        "value": "compressed_response"
    },
    
    # Rate limiting
    "rate:{customer_id}:{window}": {
        "type": "counter",
        "ttl": 60,
        "value": "request_count"
    },
    
    # Session data
    "session:{session_id}": {
        "type": "hash",
        "ttl": 86400,  # 24 hours
        "fields": {
            "customer_id": "uuid",
            "tier": "string",
            "features": "json"
        }
    },
    
    # Real-time metrics
    "metrics:{customer_id}:current": {
        "type": "hash",
        "ttl": 300,  # 5 minutes
        "fields": {
            "requests_count": "counter",
            "tokens_saved": "counter",
            "current_cost": "decimal"
        }
    }
}
```

---

# API SPECIFICATIONS

## Gateway API Endpoints

```yaml
# OpenAPI specification for Gateway

paths:
  # OpenAI compatibility
  /v1/completions:
    post:
      summary: "OpenAI completions endpoint"
      x-apex-optimization: "full"
      
  /v1/chat/completions:
    post:
      summary: "OpenAI chat endpoint"
      x-apex-optimization: "full"
      
  # Anthropic compatibility
  /v1/messages:
    post:
      summary: "Anthropic messages endpoint"
      x-apex-optimization: "full"
      
  # Apex control plane
  /apex/v1/config:
    get:
      summary: "Get optimization config"
    put:
      summary: "Update optimization preferences"
      
  /apex/v1/metrics:
    get:
      summary: "Real-time metrics"
      
  /apex/v1/savings:
    get:
      summary: "Savings report"
```

## Validation API Endpoints

```yaml
paths:
  /validation/v1/jobs:
    post:
      summary: "Create validation job"
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ValidationRequest'
              
  /validation/v1/jobs/{job_id}:
    get:
      summary: "Get job status"
      
  /validation/v1/jobs/{job_id}/report:
    get:
      summary: "Get validation report"
      
  /validation/v1/workloads:
    post:
      summary: "Upload workload profile"
```

---

# DEPLOYMENT ARCHITECTURE

## Infrastructure Stack

```yaml
production:
  regions:
    primary: "us-east-1"
    secondary: "us-west-2"
    
  compute:
    gateway:
      type: "ECS Fargate"
      instances: 10
      cpu: 4
      memory: 8
      autoscaling:
        min: 10
        max: 100
        target_cpu: 70
        
    validation_workbench:
      type: "EKS"
      nodes:
        min: 3
        max: 20
      instance_type: "m5.2xlarge"
      
  databases:
    postgres:
      type: "RDS Aurora"
      instances: 3
      size: "db.r6g.2xlarge"
      
    clickhouse:
      type: "EC2 Cluster"
      nodes: 3
      storage: "10TB SSD"
      
    redis:
      type: "ElastiCache"
      nodes: 3
      node_type: "cache.r6g.xlarge"
      
  networking:
    cdn: "CloudFront"
    load_balancer: "ALB"
    waf: "enabled"
```

## CI/CD Pipeline

```yaml
pipeline:
  stages:
    - build:
        - lint (ruff, black)
        - type_check (mypy)
        - security_scan (bandit)
        
    - test:
        - unit_tests (pytest)
        - integration_tests
        - e2e_tests
        
    - deploy_staging:
        - terraform_plan
        - deploy_services
        - smoke_tests
        
    - deploy_production:
        - blue_green_deployment
        - health_checks
        - rollback_on_failure
```

---

# MONITORING & OBSERVABILITY

## Metrics Collection

```python
# Key metrics to track

BUSINESS_METRICS = {
    "revenue": {
        "mrr": "Monthly recurring revenue",
        "vbp_collected": "Value-based pricing collected",
        "bvm_revenue": "Validation minutes revenue"
    },
    "conversion": {
        "trial_to_paid": "Trial conversion rate",
        "tier_upgrades": "Customers upgrading tiers",
        "churn_rate": "Monthly churn"
    },
    "usage": {
        "api_requests": "Total API requests",
        "tokens_saved": "Total tokens saved",
        "cache_hit_rate": "Cache effectiveness"
    }
}

TECHNICAL_METRICS = {
    "performance": {
        "gateway_latency": "P50, P95, P99",
        "optimization_time": "Time to optimize",
        "provider_latency": "Upstream latency"
    },
    "reliability": {
        "error_rate": "4xx, 5xx rates",
        "uptime": "Service availability",
        "circuit_breaker": "Trip frequency"
    },
    "infrastructure": {
        "cpu_usage": "Container CPU",
        "memory_usage": "Container memory",
        "database_connections": "Pool utilization"
    }
}
```

## Alerting Rules

```yaml
alerts:
  critical:
    - name: "revenue_drop"
      condition: "mrr_delta < -10%"
      window: "1h"
      
    - name: "high_error_rate"
      condition: "error_rate > 1%"
      window: "5m"
      
    - name: "gateway_down"
      condition: "health_check_failures > 3"
      window: "1m"
      
  warning:
    - name: "high_latency"
      condition: "p95_latency > 500ms"
      window: "5m"
      
    - name: "cache_miss_rate"
      condition: "cache_hit_rate < 0.3"
      window: "15m"
```

---

# SECURITY ARCHITECTURE

## Data Isolation

```python
# Customer data isolation model

class DataIsolation:
    """Ensures complete customer data separation"""
    
    patterns = {
        "database": "Row-level security with customer_id",
        "cache": "Prefixed keys with customer_id",
        "storage": "Separate S3 prefixes per customer",
        "sandbox": "Isolated VPCs per validation job"
    }
    
    encryption = {
        "at_rest": "AES-256",
        "in_transit": "TLS 1.3",
        "keys": "AWS KMS per-customer keys"
    }
```

## Authentication & Authorization

```yaml
auth:
  methods:
    - api_key (for gateway)
    - jwt (for dashboard)
    - oauth2 (enterprise SSO)
    
  rbac:
    roles:
      - viewer: "Read-only access"
      - developer: "Can configure optimizations"
      - admin: "Full access including billing"
      
  rate_limiting:
    free: "100 requests/hour"
    early: "1000 requests/hour"
    mid: "10000 requests/hour"
    enterprise: "unlimited"
```

---

**END OF TECHNICAL ARCHITECTURE**

This architecture ensures:
1. **Scalability**: Can handle millions of requests
2. **Reliability**: Multiple failure points addressed
3. **Security**: Customer data completely isolated
4. **Performance**: Sub-50ms added latency
5. **Monetization**: Every optimization tracked and billed