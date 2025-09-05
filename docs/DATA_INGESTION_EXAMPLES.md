# Data Ingestion Examples - Real User Data

## Current State Examples (What Works Now)

### 1. JSON Files (✅ Working)

```json
// Example 1: User metrics data
{
  "user_id": "usr_12345",
  "timestamp": "2024-01-15T10:30:00Z",
  "metrics": {
    "api_calls": 1250,
    "tokens_used": 45000,
    "cost_usd": 2.25
  }
}

// Example 2: Agent execution log
{
  "run_id": "run_abc123",
  "agent": "data_sub_agent",
  "status": "completed",
  "duration_ms": 3400,
  "tools_used": ["search_corpus", "analyze_corpus"]
}

// Example 3: Configuration update
{
  "config_type": "model_params",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000,
  "updated_by": "admin@company.com"
}

// Example 4: Batch user data import
[
  {"id": "1", "name": "John Doe", "role": "developer"},
  {"id": "2", "name": "Jane Smith", "role": "analyst"},
  {"id": "3", "name": "Bob Wilson", "role": "manager"}
]

// Example 5: Error report
{
  "error_id": "err_789xyz",
  "service": "corpus_service",
  "message": "Failed to index document",
  "stack_trace": "...",
  "context": {"file_size": 10485760, "file_type": "pdf"}
}
```

### 2. PDFs (⚠️ Basic Upload Only)

```
// Example 1: Company report upload
POST /api/corpus/upload
Content-Type: multipart/form-data
- file: "Q4_2024_Financial_Report.pdf" (10MB)
- corpus_id: "corp_financial"

// Example 2: Technical documentation
- "AWS_Best_Practices_Guide.pdf" (256 pages)
- "Kubernetes_Architecture.pdf" (180 pages)  
- "Python_Style_Guide.pdf" (45 pages)

// Example 3: Research papers
- "transformer_architecture.pdf"
- "rag_techniques_survey.pdf"
- "llm_fine_tuning_methods.pdf"

// Example 4: Legal documents
- "terms_of_service_v2.pdf"
- "privacy_policy_2024.pdf"
- "data_processing_agreement.pdf"

// Example 5: Training materials
- "onboarding_guide.pdf"
- "api_documentation.pdf"
- "troubleshooting_manual.pdf"
```

### 3. Text Files (⚠️ Simple Upload)

```
// Example 1: README.txt
Netra AI Platform Setup
=======================
1. Install dependencies
2. Configure environment
3. Run migrations

// Example 2: notes.txt
Meeting Notes - Jan 15, 2024
- Discussed RAG implementation
- Need better error handling
- Performance optimization required

// Example 3: config.txt
DATABASE_URL=postgresql://localhost/netra
REDIS_URL=redis://localhost:6379
API_KEY=sk-1234567890abcdef

// Example 4: requirements.txt
langchain==0.1.0
openai==1.6.0
fastapi==0.104.0
pydantic==2.5.0

// Example 5: changelog.txt
v1.2.0 - Added corpus search
v1.1.0 - Improved agent routing  
v1.0.0 - Initial release
```

### 4. Manual ClickHouse Queries (⚠️ Direct SQL Only)

```sql
-- Example 1: Insert metrics
INSERT INTO agent_metrics (timestamp, agent_id, latency_ms)
VALUES (now(), 'agent_123', 450);

-- Example 2: Query performance data
SELECT avg(latency_ms) as avg_latency
FROM agent_metrics
WHERE timestamp > now() - INTERVAL 1 HOUR;

-- Example 3: Bulk insert events
INSERT INTO events (id, type, data)
SELECT * FROM input('id String, type String, data String')
FORMAT CSV;

-- Example 4: Create aggregation table
CREATE TABLE daily_stats
ENGINE = MergeTree()
ORDER BY date
AS SELECT 
  toDate(timestamp) as date,
  count() as total_events
FROM events
GROUP BY date;

-- Example 5: Export data
SELECT * FROM corpus_documents
WHERE corpus_id = 'corp_123'
FORMAT JSONEachRow;
```

---

## Ideal State Examples (What Users Want to Send)

### 1. User Prompts (Direct Ingestion)

```
// Example 1: Copy-paste from chat
"Here's our system architecture:
- Frontend: React/Next.js on Vercel
- Backend: FastAPI on GCP Cloud Run  
- Database: PostgreSQL + Redis
- ML: Custom models on Vertex AI
Please analyze and suggest optimizations"

// Example 2: Natural language data entry
"Add these customer feedback points:
1. UI is slow on mobile devices
2. Search doesn't find partial matches
3. Export feature times out for large datasets
4. Need dark mode support
5. Want Slack integration"

// Example 3: Structured data in chat
"Update metrics for Q4:
Revenue: $2.4M (+15% QoQ)
Users: 12,500 (+2,000)
MRR: $200K
Churn: 2.1% (down from 2.8%)"

// Example 4: Code snippet sharing
"Here's the function that's causing issues:
```python
async def process_batch(items):
    results = []
    for item in items:  # This is slow
        result = await api_call(item)
        results.append(result)
    return results
```"

// Example 5: Mixed format instructions
"Ingest these sources:
- https://docs.company.com/api/v2
- The attached spreadsheet (revenue.xlsx)
- All logs from the last 24 hours
- Screenshots from the bug report
- Customer emails in the support folder"
```

### 2. Copy/Paste Data

```
// Example 1: Excel data paste
Date       | User Count | Revenue  | Churn
2024-01-01 | 10,500    | $1.8M    | 2.3%
2024-01-02 | 10,520    | $1.81M   | 2.2%
2024-01-03 | 10,545    | $1.82M   | 2.2%

// Example 2: Stack trace paste
Traceback (most recent call last):
  File "app.py", line 234, in process_request
    result = await handler.execute()
  File "handler.py", line 45, in execute
    data = self.transform_data(raw_data)
ValueError: Invalid data format

// Example 3: JSON from browser console
{
  "network": {
    "requests": 145,
    "failed": 3,
    "avgLatency": "234ms"
  },
  "errors": [
    "Failed to load resource: 404",
    "Uncaught TypeError: Cannot read property 'id'"
  ]
}

// Example 4: CSV paste from spreadsheet
product_id,name,price,stock,category
P001,Laptop Pro,1299.99,45,Electronics
P002,Wireless Mouse,29.99,230,Accessories
P003,USB-C Hub,59.99,120,Accessories

// Example 5: Terminal output paste
$ docker stats
CONTAINER    CPU %    MEM USAGE    NET I/O
backend      45.2%    512MB/1GB    1.2GB/450MB
frontend     12.1%    256MB/512MB  500MB/200MB
postgres     78.3%    2GB/4GB      5GB/3GB
```

### 3. Log Files (Structured Parsing)

```
// Example 1: Application logs
2024-01-15 10:30:45.123 INFO [api.request] GET /api/users 200 45ms
2024-01-15 10:30:46.456 ERROR [db.connection] Connection timeout after 30s
2024-01-15 10:30:47.789 WARN [cache] Cache miss for key: user_123
2024-01-15 10:30:48.012 INFO [auth] User john@example.com logged in
2024-01-15 10:30:49.345 ERROR [payment] Stripe API error: insufficient_funds

// Example 2: Nginx access logs
192.168.1.100 - - [15/Jan/2024:10:30:45 +0000] "GET /api/health HTTP/1.1" 200 15
192.168.1.101 - user123 [15/Jan/2024:10:30:46 +0000] "POST /api/chat HTTP/1.1" 201 1245
192.168.1.102 - - [15/Jan/2024:10:30:47 +0000] "GET /static/css/main.css HTTP/1.1" 304 0

// Example 3: System logs
Jan 15 10:30:45 server01 kernel: Out of memory: Kill process 12345 (python) score 800
Jan 15 10:30:46 server01 systemd: Started PostgreSQL database server
Jan 15 10:30:47 server01 docker: Container backend_app started

// Example 4: CloudWatch/GCP logs
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "message": "Lambda execution failed",
  "requestId": "abc-123-def",
  "duration": 3000,
  "billedDuration": 3000,
  "memorySize": 512,
  "maxMemoryUsed": 450
}

// Example 5: Kubernetes logs
2024-01-15T10:30:45.123Z [pod/backend-5d4c8b-x2j3k] Starting application...
2024-01-15T10:30:46.456Z [pod/backend-5d4c8b-x2j3k] Connected to database
2024-01-15T10:30:47.789Z [pod/backend-5d4c8b-x2j3k] Health check passed
2024-01-15T10:30:48.012Z [pod/frontend-7f9c2a-m5n8p] Scaling to 3 replicas
```

### 4. 100+ Page Document Dumps

```
// Example 1: Complete API documentation (Swagger/OpenAPI)
{
  "openapi": "3.0.0",
  "info": { "title": "Netra API", "version": "2.0.0" },
  "paths": {
    "/api/agents": { /* 500+ lines of endpoint definitions */ },
    "/api/corpus": { /* 800+ lines of endpoint definitions */ },
    // ... 100+ more endpoints
  }
}

// Example 2: Database schema export (500+ tables)
CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255)...);
CREATE TABLE organizations (id SERIAL PRIMARY KEY, name VARCHAR(255)...);
CREATE TABLE agents (id SERIAL PRIMARY KEY, type VARCHAR(50)...);
-- ... 497 more table definitions

// Example 3: Full codebase documentation (mdBook/Sphinx)
# Chapter 1: Architecture Overview
## 1.1 System Components
### 1.1.1 Frontend Architecture
[20 pages of content]
### 1.1.2 Backend Services
[35 pages of content]
## 1.2 Data Flow
[15 pages of diagrams and explanations]
-- ... continues for 200+ pages

// Example 4: Compliance audit report
SECURITY AUDIT REPORT - Q4 2024
================================
Executive Summary................page 1
Vulnerability Assessment.........page 10
Penetration Test Results.........page 45  
Compliance Checklist............page 120
Recommendations.................page 180
Appendices.....................page 210

// Example 5: Machine learning model documentation
MODEL CARD: netra-optimizer-v3
==============================
1. Model Details (pages 1-20)
2. Training Data (pages 21-60)
3. Evaluation Metrics (pages 61-90)
4. Ethical Considerations (pages 91-110)
5. Benchmarks (pages 111-150)
```

### 5. Direct Database Queries (ClickHouse, PostgreSQL, etc.)

```sql
-- Example 1: ClickHouse time-series query
SELECT 
  toStartOfHour(timestamp) as hour,
  quantile(0.99)(latency) as p99_latency,
  count() as request_count
FROM metrics
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY hour
ORDER BY hour;

-- Example 2: PostgreSQL complex join
SELECT 
  u.email,
  o.name as org_name,
  COUNT(DISTINCT a.id) as agent_count,
  SUM(am.tokens_used) as total_tokens
FROM users u
JOIN organizations o ON u.org_id = o.id
LEFT JOIN agents a ON a.owner_id = u.id
LEFT JOIN agent_metrics am ON am.agent_id = a.id
WHERE u.created_at >= '2024-01-01'
GROUP BY u.email, o.name;

-- Example 3: MongoDB aggregation pipeline
db.events.aggregate([
  { $match: { timestamp: { $gte: ISODate("2024-01-01") } } },
  { $group: {
    _id: "$user_id",
    total_events: { $sum: 1 },
    unique_types: { $addToSet: "$event_type" }
  }},
  { $sort: { total_events: -1 } },
  { $limit: 100 }
])

-- Example 4: Elasticsearch query
GET /logs-*/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "level": "ERROR" } },
        { "range": { "@timestamp": { "gte": "now-24h" } } }
      ]
    }
  },
  "aggs": {
    "errors_by_service": {
      "terms": { "field": "service.keyword" }
    }
  }
}

-- Example 5: Redis data extraction
SCAN 0 MATCH user:* COUNT 1000
GET user:12345
HGETALL session:abc123
ZRANGE leaderboard 0 10 WITHSCORES
XREAD COUNT 100 STREAMS events:stream 0-0
```

### 6. Streaming Data (Kafka, Webhooks, etc.)

```json
// Example 1: Kafka event stream
{
  "topic": "user-events",
  "partition": 0,
  "offset": 12345,
  "key": "user_123",
  "value": {
    "event": "page_view",
    "page": "/dashboard",
    "timestamp": "2024-01-15T10:30:45.123Z"
  }
}

// Example 2: Webhook from GitHub
{
  "event": "push",
  "repository": "company/backend",
  "commits": [
    {
      "id": "abc123",
      "message": "Fix memory leak in agent executor",
      "author": "dev@company.com"
    }
  ]
}

// Example 3: Stripe webhook
{
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_1234567890",
      "amount": 9900,
      "currency": "usd",
      "customer": "cus_abc123"
    }
  }
}

// Example 4: IoT sensor stream
{
  "device_id": "sensor_001",
  "readings": {
    "temperature": 23.5,
    "humidity": 65.2,
    "pressure": 1013.25
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}

// Example 5: Real-time analytics events
{
  "session_id": "sess_xyz789",
  "events": [
    {"type": "click", "target": "button.submit", "time": 1234567890},
    {"type": "scroll", "position": 0.75, "time": 1234567891},
    {"type": "input", "field": "search", "time": 1234567892}
  ]
}
```

### 7. External API Data

```json
// Example 1: OpenAI API response
{
  "model": "gpt-4",
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 250,
    "total_tokens": 400
  },
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Based on the analysis..."
    }
  }]
}

// Example 2: Stock market data API
{
  "symbol": "AAPL",
  "price": 185.92,
  "volume": 54238900,
  "change": 2.45,
  "change_percent": 1.34,
  "timestamp": "2024-01-15T16:00:00Z"
}

// Example 3: Weather API
{
  "location": "San Francisco",
  "current": {
    "temp_f": 65,
    "condition": "Partly cloudy",
    "wind_mph": 12,
    "humidity": 70
  },
  "forecast": [ /* 7-day forecast */ ]
}

// Example 4: CRM data (Salesforce)
{
  "Account": {
    "Id": "001xx000003DHPh",
    "Name": "Acme Corporation",
    "AnnualRevenue": 5000000,
    "NumberOfEmployees": 200
  },
  "Opportunities": [ /* array of opportunities */ ]
}

// Example 5: Analytics API (Google Analytics)
{
  "dimensions": ["date", "country"],
  "metrics": ["sessions", "pageviews", "users"],
  "rows": [
    ["2024-01-15", "US", 1234, 5678, 890],
    ["2024-01-15", "UK", 456, 1234, 234]
  ]
}
```

### 8. Screenshot/Image Data

```
// Example 1: Error screenshot with console
[Binary PNG data]
- Screenshot showing JavaScript error
- Console tab open with stack trace
- Network tab showing failed requests
- 1920x1080 resolution

// Example 2: Dashboard metrics screenshot  
[Binary PNG data]
- Grafana dashboard
- Multiple charts and graphs
- Time range: Last 7 days
- Showing performance degradation

// Example 3: Whiteboard photo
[Binary JPEG data]
- System architecture diagram
- Hand-drawn components
- Annotations and notes
- Needs OCR processing

// Example 4: PDF with charts
[Binary PDF data]
- Financial report with embedded charts
- Tables with quarterly data
- Graphs needing data extraction

// Example 5: UI mockup
[Binary PNG data]
- Figma design export
- New feature layout
- Color annotations
- Component specifications
```

### 9. Email/Communication Data

```
// Example 1: Customer support email
From: customer@example.com
Subject: API rate limiting issue
Body: "We're hitting rate limits even though we're well below our quota.
Error: 429 Too Many Requests
Endpoint: /api/v2/analyze
Request rate: 10/minute (limit should be 100/minute)"

// Example 2: Slack message export
{
  "channel": "engineering",
  "messages": [
    {
      "user": "john.doe",
      "text": "Deployment failed with OOM error",
      "timestamp": "2024-01-15T10:30:45.123Z",
      "thread": [ /* replies */ ]
    }
  ]
}

// Example 3: Teams conversation
{
  "conversation_id": "19:meeting_123",
  "participants": ["alice", "bob", "charlie"],
  "messages": [ /* array of messages */ ],
  "files": [ /* shared files */ ]
}

// Example 4: Support ticket
{
  "ticket_id": "SUP-12345",
  "priority": "high",
  "subject": "Data not syncing",
  "description": "...",
  "attachments": [ /* screenshots, logs */ ],
  "history": [ /* conversation thread */ ]
}

// Example 5: SMS/WhatsApp backup
[
  {
    "from": "+1234567890",
    "to": "+0987654321",
    "message": "System alert: Database CPU at 95%",
    "timestamp": "2024-01-15T10:30:45Z"
  }
]
```

### 10. Mixed/Hybrid Data Sources

```
// Example 1: Data lake dump (Parquet + JSON + CSV)
/datalake/
├── users/
│   ├── 2024-01-15.parquet (columnar user data)
│   └── metadata.json (schema info)
├── events/
│   ├── events_2024_01_15_*.csv (hourly files)
│   └── schema.sql
└── models/
    ├── model_v1.pkl (scikit-learn model)
    └── config.yaml

// Example 2: Research dataset (mixed formats)
{
  "study_id": "STUDY_001",
  "participants": "participants.csv",  // 10,000 rows
  "surveys": "surveys/*.json",         // 10,000 JSON files
  "audio": "interviews/*.mp3",         // 500 audio files
  "transcripts": "transcripts/*.txt",  // 500 text files
  "analysis": "analysis.ipynb"         // Jupyter notebook
}

// Example 3: Migration package
{
  "source_db": "mysql://old-server/database",
  "export": {
    "tables": ["users", "orders", "products"],
    "format": "sql",
    "size": "15GB"
  },
  "transformations": "transform.py",
  "target": "postgresql://new-server/database"
}

// Example 4: Monitoring bundle
{
  "metrics": {
    "prometheus": "http://prometheus:9090/api/v1/query_range",
    "datadog": { "api_key": "***", "metrics": ["system.cpu", "custom.*"] }
  },
  "logs": {
    "elasticsearch": "http://elastic:9200/logs-*",
    "cloudwatch": { "log_groups": ["/aws/lambda/*"] }
  },
  "traces": {
    "jaeger": "http://jaeger:16686/api/traces"
  }
}

// Example 5: Complete environment snapshot
{
  "timestamp": "2024-01-15T10:30:45Z",
  "environment": "production",
  "components": {
    "database_dump": "backup_20240115.sql.gz",      // 5GB
    "redis_snapshot": "dump.rdb",                   // 500MB
    "config_files": "configs/*.yaml",               // 50 files
    "docker_images": ["app:v1.2.3", "nginx:latest"],
    "kubernetes_manifests": "k8s/*.yaml",           // 30 files
    "secrets": "vault://secret/production/*",       // Vault paths
    "monitoring_dashboards": "grafana_export.json"  // 10MB
  }
}
```

## Data Volume Examples

### Small (< 1MB)
- Single JSON configuration
- Text note or README
- Individual log file
- Single CSV export
- API response

### Medium (1MB - 100MB)  
- PDF documentation
- Day of logs
- Small database export
- Batch of images
- Excel workbook

### Large (100MB - 1GB)
- Week of application logs
- Database table export
- Video tutorial
- Complete API documentation
- ML model file

### Extra Large (> 1GB)
- Full database dump
- Month of metrics data
- Complete codebase
- Data lake export
- Compliance audit package