# Netra Apex User Guide
**Enterprise AI Optimization Platform**

**System Health Score: 95% (EXCELLENT)** | **Last Updated: 2025-09-14** | **Status: Production Ready with Complete SSOT Factory Migration**

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Regular User Guide](#regular-user-guide)
4. [Admin User Guide](#admin-user-guide)
5. [Chat Interface & Commands](#chat-interface--commands)
6. [Tips & Best Practices](#tips--best-practices)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)
9. [Developer Notes](#developer-notes)

---

## Introduction

Netra Apex is an enterprise AI optimization platform that helps organizations reduce AI costs by 20-45% while maintaining or improving performance. The platform uses intelligent routing, model selection, and caching to optimize every AI request automatically.

### Current System Status (2025-09-14)
- **Issue #1116 COMPLETE:** SSOT Agent Instance Factory Migration - Complete migration from singleton patterns to factory-based user isolation with full system stability validation
- **System Health:** 95% (EXCELLENT) - All critical infrastructure operational with enhanced stability
- **SSOT Compliance:** 84.4% Real System (333 violations in 135 files - Configuration and Orchestration SSOT complete)
- **Golden Path Status:** ✅ FULLY OPERATIONAL - End-to-end user flow validated through staging environment
- **WebSocket Events:** 100% event delivery guarantee with silent failure prevention
- **Production Readiness:** ✅ CONFIRMED - All critical systems validated for deployment

### Key Value Propositions
- **Cost Reduction**: Save 20-45% on AI/LLM spending
- **Performance Improvement**: Reduce latency by 15-30%
- **Quality Assurance**: Maintain or improve output quality
- **Transparent Pricing**: Pay only 20% of your actual savings

### User Tiers
| Tier | Features | Support |
|------|----------|---------|
| **Free** | Basic optimization, 100 requests/hr | Community |
| **Early** | Full optimization, analytics, 1000 req/hr | Email (99.5% SLA) |
| **Mid** | Bulk operations, 10000 req/hr | Priority (99.9% SLA) |
| **Enterprise** | Custom endpoints, unlimited | Dedicated (99.99% SLA) |

---

## Getting Started

### Initial Setup
1. **Sign up** at https://app.netrasystems.ai
2. **Choose your tier** based on expected usage
3. **Connect via OAuth** (Google supported)
4. **Create your first thread** to start optimizing

### Quick Start Commands
```
User: "Analyze my current AI costs"
User: "Optimize this prompt for cost"
User: "Show me cheaper alternatives to GPT-4"
User: "What's my current savings rate?"
```

**Developer Note**: Authentication uses JWT tokens with Google OAuth. Tokens expire after 24 hours. See `app/auth_integration/auth.py` for implementation.

---

## Regular User Guide

### Basic Chat Interactions

#### 1. Cost Analysis
**Input Examples:**
```
"How much am I spending on AI this month?"
"Break down my costs by model"
"Show me cost trends over the last quarter"
```

**Expected Output:**
- Total spend visualization
- Model-by-model breakdown
- Cost trend charts
- Optimization opportunities identified

#### 2. Optimization Requests
**Input Examples:**
```
"Optimize my text generation workflow"
"Find cheaper alternatives for this task: [describe task]"
"Reduce latency for my chat application"
```

**Expected Output:**
- Recommended model alternatives
- Expected savings percentage
- Performance impact analysis
- Implementation suggestions

#### 3. Quality Validation
**Input Examples:**
```
"Compare quality between GPT-4 and Claude for [task]"
"Validate if this cheaper model maintains quality"
"Run A/B test on model alternatives"
```

**Expected Output:**
- Quality scores comparison
- Side-by-side output examples
- Confidence levels
- Recommendation with reasoning

### Advanced Features

#### Thread Management
Threads organize your optimization conversations and maintain context.

**Commands:**
- `"Create new thread for [project name]"` - Start fresh context
- `"List my recent threads"` - View thread history
- `"Continue thread about [topic]"` - Resume previous work
- `"Auto-rename this thread"` - AI generates descriptive name

#### Bulk Operations
**Input Examples:**
```
"Optimize all my customer service prompts"
"Analyze last week's API usage"
"Batch process these 50 queries for cost optimization"
```

**Expected Output:**
- Progress indicators
- Batch results summary
- Downloadable reports
- Aggregate savings

**Developer Note**: Bulk operations use the `app/agents/supervisor/supervisor.py` to coordinate multi-agent processing. Rate limits apply based on tier.

---

## Admin User Guide

### Admin-Exclusive Features

#### 1. System Configuration
**Commands:**
```
"Set default optimization strategy to aggressive"
"Configure ClickHouse logging table"
"Update rate limits for user tier"
"Set cache retention to 7 days"
```

**Access Required**: Admin role (`role: "admin"` in JWT)

#### 2. User Management
**Commands:**
```
"Show all active users"
"Update user [email] to enterprise tier"
"View user [email] usage statistics"
"Set custom rate limit for [email]"
```

#### 3. System Monitoring
**Commands:**
```
"Show system health metrics"
"Display real-time WebSocket connections"
"Check database performance"
"View agent execution statistics"
```

**Expected Output:**
- System dashboard with key metrics
- Connection count and distribution
- Query performance metrics
- Agent success/failure rates

#### 4. Audit & Compliance
**Commands:**
```
"Show audit logs for last 24 hours"
"Export compliance report for Q4"
"Track all GPT-4 usage this month"
"List users exceeding cost thresholds"
```

### Admin API Endpoints
| Endpoint | Purpose | Required Permission |
|----------|---------|-------------------|
| `/api/admin/settings` | System configuration | `system_config` |
| `/api/admin/users` | User management | `user_management` |
| `/api/admin/audit` | Audit log access | `audit_access` |
| `/api/admin/metrics` | System metrics | `metrics_view` |

**Developer Note**: Admin endpoints are protected by `AdminDep` dependency in `app/routes/admin.py`. Permissions checked via `app/services/permission_service.py`.

---

## Chat Interface & Commands

### Message Types & Formats

#### User Messages
```json
{
  "action": "send_message",
  "data": {
    "content": "Your request here",
    "thread_id": "optional-thread-id",
    "context": {
      "urgency": "high|normal|low",
      "budget_constraint": 50.00
    }
  }
}
```

#### System Responses

**1. Agent Thinking**
```
🤔 TriageSubAgent: Analyzing your request...
```

**2. Tool Execution**
```
🔧 Using cost_analyzer tool...
   Parameters: model=gpt-4, tokens=1M
   Result: Current cost: $30, Optimized: $16.50
```

**3. Final Response**
```
✅ Optimization Complete
   • Savings: 45% ($13.50)
   • Alternative: Claude-3-Sonnet
   • Quality maintained: 98% similarity
   • Implementation: [details]
```

### Special Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show available commands | `/help` |
| `/status` | Current optimization status | `/status` |
| `/savings` | View cumulative savings | `/savings monthly` |
| `/models` | List available models | `/models --providers all` |
| `/cache` | Cache statistics | `/cache stats` |
| `/export` | Export optimization report | `/export pdf --period month` |

**Developer Note**: Special commands handled by `app/routes/websockets.py` message router. Pattern matching in `app/routes/utils/websocket_helpers.py`.

---

## Tips & Best Practices

### For Maximum Savings

1. **Batch Similar Requests**
   - Group similar prompts together
   - Use bulk operations for repetitive tasks
   - Enable caching for frequent queries

2. **Provide Context**
   - Specify acceptable quality thresholds
   - Include latency requirements
   - Mention budget constraints

3. **Use Specific Commands**
   - Instead of: "Help me save money"
   - Use: "Optimize my GPT-4 text generation costing $500/month"

### For Best Results

#### DO:
- ✅ Create separate threads for different projects
- ✅ Provide example inputs/outputs when asking for optimization
- ✅ Specify if quality or cost is priority
- ✅ Use structured data formats (JSON, CSV) for bulk operations
- ✅ Review optimization suggestions before implementing

#### DON'T:
- ❌ Mix unrelated optimization requests in one thread
- ❌ Ignore quality validation recommendations
- ❌ Implement aggressive optimizations without testing
- ❌ Share API keys or credentials in chat
- ❌ Bypass rate limits with multiple accounts

### Performance Tips

1. **WebSocket Connection**
   - Maintain persistent connection for real-time updates
   - Handle reconnection gracefully
   - Implement exponential backoff for retries

2. **Caching Strategy**
   - Enable caching for deterministic queries
   - Set appropriate TTL based on data freshness needs
   - Monitor cache hit rates via `/cache stats`

**Developer Note**: Cache implementation in `app/services/llm_cache_service.py`. Default TTL is 3600s, configurable per tier.

---

## Troubleshooting

### Common Issues & Solutions

#### 1. Authentication Errors
**Problem**: "401 Unauthorized" or "Token expired"
**Solution**: 
- Refresh your token via `/auth/refresh`
- Re-authenticate if refresh fails
- Check token expiry in JWT payload

#### 2. Rate Limiting
**Problem**: "429 Too Many Requests"
**Solution**:
- Check your current tier limits
- Upgrade tier if needed
- Implement request batching
- Use exponential backoff

#### 3. WebSocket Disconnections
**Problem**: Connection drops frequently
**Solution**:
- Check network stability
- Implement auto-reconnect logic
- Monitor heartbeat messages
- Reduce message frequency if needed

#### 4. Optimization Not Applied
**Problem**: Costs remain high despite optimization
**Solution**:
- Verify optimization is enabled for your endpoints
- Check quality thresholds aren't too strict
- Review model compatibility
- Ensure proper API integration

#### 5. Quality Degradation
**Problem**: Output quality decreased after optimization
**Solution**:
- Adjust quality thresholds higher
- Use quality validation before deployment
- Consider hybrid approach (some requests use premium models)
- Report specific examples for model tuning

### Error Codes Reference

| Code | Meaning | Action |
|------|---------|--------|
| `AUTH_001` | Invalid credentials | Check login details |
| `RATE_001` | Rate limit exceeded | Wait or upgrade tier |
| `OPT_001` | Optimization failed | Review request parameters |
| `MODEL_001` | Model unavailable | Use alternative model |
| `CACHE_001` | Cache error | Clear cache and retry |

**Developer Note**: Error handling centralized in `app/core/exceptions_*.py`. All errors include trace_id for debugging.

---

## FAQ

### General Questions

**Q: How much can I really save?**
A: Typical savings range from 20-45% depending on:
- Current model usage (premium models have more optimization potential)
- Query patterns (repetitive queries benefit from caching)
- Quality requirements (lower requirements allow more aggressive optimization)

**Q: Will optimization affect my output quality?**
A: We maintain 95%+ quality similarity by default. You can adjust thresholds based on your needs. All optimizations include quality validation.

**Q: How does billing work?**
A: We charge 20% of your verified savings. If you save $1000, you pay $200. No savings = no charge.

**Q: Can I use Netra with my existing AI infrastructure?**
A: Yes! Netra works as a proxy layer. Simply point your API calls to our endpoints, and we handle optimization transparently.

### Technical Questions

**Q: What models does Netra support?**
A: Current support includes:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude family)
- Google (Gemini models)
- Open-source alternatives
- Custom models (Enterprise tier)

**Q: How does caching work?**
A: We use intelligent semantic caching:
- Exact match caching for identical queries
- Semantic similarity for near-matches
- Configurable TTL per use case
- GDPR-compliant data handling

**Q: Is my data secure?**
A: Yes, we implement:
- End-to-end encryption
- SOC2 Type II compliance
- Data isolation per customer
- No training on customer data
- Regular security audits

**Q: What's the latency impact?**
A: Typically we REDUCE latency by 15-30% through:
- Strategic model selection
- Edge deployment
- Intelligent caching
- Connection pooling

**Developer Note**: Security implementation in `app/middleware/security.py`. Compliance details in `SPEC/security.xml`.

---

## Developer Notes

### Architecture Overview
```
Frontend (Next.js) ↔ WebSocket/REST API ↔ Multi-Agent System ↔ LLM Providers
                                         ↔ PostgreSQL/ClickHouse
                                         ↔ Redis Cache
```

### Key Modules

#### Agent System
- **Location**: `app/agents/`
- **Key Files**: 
  - `supervisor/supervisor.py` - Orchestrates sub-agents
  - `triage_sub_agent/` - Request classification
  - `data_sub_agent/` - Data processing
- **Pattern**: Each agent extends `BaseSubAgent` with 25-line function limit

#### WebSocket Management
- **Location**: `app/routes/websockets.py`, `app/websocket/`
- **Key Features**:
  - Auto-reconnection handling
  - Rate limiting per connection
  - Message validation
  - Heartbeat monitoring

#### Authentication
- **Location**: `app/auth_integration/`
- **Features**:
  - JWT with 24hr expiry
  - Google OAuth integration
  - Role-based permissions
  - Development mode bypass

#### Database Layer
- **PostgreSQL**: User data, threads, configuration
- **ClickHouse**: Analytics, logs, metrics
- **Redis**: Caching, rate limiting, sessions

### Testing Guidelines
```bash
# Unit tests (fast)
python test_runner.py --level unit --no-coverage

# Integration tests (DEFAULT)
python test_runner.py --level integration --no-coverage --fast-fail

# Real LLM tests (before release)
python test_runner.py --level integration --real-llm

# Agent-specific tests
python test_runner.py --level agents --real-llm
```

### Module Constraints
- **Max file size**: 300 lines (MANDATORY)
- **Max function size**: 8 lines (MANDATORY)
- **Type safety**: Pydantic models required
- **Naming**: `*SubAgent` for LLM agents only

### Performance Considerations
- WebSocket connections pooled per user
- Database connections use async/await
- Caching reduces LLM calls by 40-60%
- Circuit breakers prevent cascade failures

### Monitoring & Observability
- Structured logging to ClickHouse
- OpenTelemetry integration (Enterprise)
- Custom metrics via StatsD
- Health endpoints for k8s probes

### Common Pitfalls
1. Don't bypass rate limiters
2. Always validate WebSocket messages
3. Use connection pooling for databases
4. Implement retry logic with backoff
5. Handle agent failures gracefully

### Support Channels
- GitHub Issues: Feature requests & bugs
- Slack: `#netra-apex-dev` (internal)
- Email: dev-support@netrasystems.ai
- Docs: Internal wiki for deep dives

---

## MCP (Model Context Protocol) Documentation

### Overview
The Model Context Protocol (MCP) enables seamless integration between Netra Apex and external tools, services, and data sources. MCP provides a standardized way to extend the platform's capabilities without modifying core code.

### MCP Architecture
```
User Request → Netra Agent → MCP Server → External Tool/Service
                           ← Response ←
```

### Enabling MCP

#### For Regular Users
1. **Enable MCP in Settings**
   ```
   "Enable MCP integration for my account"
   "Connect to MCP server at [server_url]"
   ```

2. **List Available MCP Tools**
   ```
   "Show available MCP tools"
   "What MCP servers are connected?"
   ```

3. **Use MCP Tools**
   ```
   "Use MCP tool [tool_name] to [action]"
   "Execute [tool] via MCP with parameters [...]"
   ```

#### For Administrators

##### MCP Server Configuration
```json
{
  "mcp_config": {
    "enabled": true,
    "servers": [
      {
        "name": "github-mcp",
        "url": "http://mcp-github:3001",
        "auth": "bearer_token",
        "timeout": 30000
      },
      {
        "name": "database-mcp",
        "url": "http://mcp-db:3002",
        "auth": "api_key",
        "capabilities": ["read", "write"]
      }
    ],
    "default_timeout": 15000,
    "retry_policy": {
      "max_retries": 3,
      "backoff": "exponential"
    }
  }
}
```

##### Admin MCP Commands
```
"Add MCP server [name] at [url]"
"Configure MCP authentication for [server]"
"Set MCP timeout to [seconds]"
"Enable MCP caching with TTL [minutes]"
"View MCP server health status"
"Rotate MCP authentication tokens"
```

### MCP Tool Categories

#### 1. Data Source Tools
- **database-query**: Execute SQL queries
- **api-fetch**: Call external APIs
- **file-read**: Read file contents
- **cache-lookup**: Query cache systems

#### 2. Processing Tools
- **data-transform**: Transform data formats
- **text-analysis**: Analyze text content
- **code-review**: Review code quality
- **metric-calculate**: Calculate metrics

#### 3. Integration Tools
- **github-pr**: Manage GitHub PRs
- **slack-notify**: Send Slack messages
- **email-send**: Send emails
- **webhook-trigger**: Trigger webhooks

#### 4. AI Enhancement Tools
- **context-expand**: Expand context window
- **memory-store**: Store long-term memory
- **embedding-search**: Semantic search
- **rag-retrieve**: RAG retrieval

### MCP Request Format

#### Standard MCP Request
```json
{
  "tool": "database-query",
  "server": "database-mcp",
  "parameters": {
    "query": "SELECT * FROM optimizations WHERE savings > 1000",
    "database": "analytics",
    "timeout": 5000
  },
  "context": {
    "user_id": "user-123",
    "thread_id": "thread-456",
    "trace_id": "trace-789"
  }
}
```

#### MCP Response Format
```json
{
  "success": true,
  "tool": "database-query",
  "result": {
    "rows": [...],
    "row_count": 42,
    "execution_time_ms": 234
  },
  "metadata": {
    "server": "database-mcp",
    "timestamp": "2024-01-15T10:00:00Z",
    "cache_hit": false
  }
}
```

### MCP Security

#### Authentication Methods
1. **Bearer Token**: For API-based MCP servers
2. **API Key**: For service integrations
3. **OAuth 2.0**: For third-party services
4. **mTLS**: For enterprise deployments

#### Security Best Practices
- Always use encrypted connections (HTTPS/WSS)
- Rotate authentication tokens regularly
- Implement request signing for sensitive operations
- Use separate MCP servers for different security zones
- Enable audit logging for all MCP operations

### MCP Development

#### Creating Custom MCP Tools
```python
# Example MCP tool implementation
class CustomMCPTool:
    def __init__(self):
        self.name = "custom-optimizer"
        self.version = "1.0.0"
        
    async def execute(self, params: dict) -> dict:
        # Tool logic here
        result = await self.optimize(params)
        return {
            "success": True,
            "result": result
        }
```

#### MCP Server Implementation
```javascript
// Example MCP server in Node.js
const express = require('express');
const app = express();

app.post('/mcp/execute', async (req, res) => {
  const { tool, parameters } = req.body;
  
  try {
    const result = await executeeTool(tool, parameters);
    res.json({ success: true, result });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});
```

### MCP Monitoring

#### Metrics to Track
- Tool execution count
- Average response time
- Error rate by tool
- Cache hit ratio
- Token usage per tool

#### Monitoring Commands
```
"Show MCP metrics for last hour"
"Alert if MCP error rate > 5%"
"Track MCP tool usage by user"
"Generate MCP performance report"
```

**Developer Note**: MCP implementation in `app/services/mcp/`. Configuration in `app/config.py` under `mcp_settings`. Tool registry in `app/services/mcp/tool_registry.py`.

---

## Complete Tools Documentation

### Tool Categories & Capabilities

#### 1. Cost Analysis Tools

##### cost_analyzer
**Purpose**: Analyze current AI/LLM costs
**Input Format**:
```json
{
  "tool": "cost_analyzer",
  "params": {
    "model": "gpt-4",
    "period": "month",
    "breakdown": true
  }
}
```
**Output**: Cost breakdown with optimization opportunities

##### savings_calculator
**Purpose**: Calculate potential savings
**Input Format**:
```json
{
  "tool": "savings_calculator",
  "params": {
    "current_spend": 10000,
    "optimization_level": "aggressive"
  }
}
```
**Output**: Projected savings and ROI

##### cost_forecaster
**Purpose**: Forecast future AI costs
**Input Format**:
```json
{
  "tool": "cost_forecaster",
  "params": {
    "growth_rate": 0.15,
    "horizon_months": 6
  }
}
```
**Output**: Cost projections with confidence intervals

#### 2. Optimization Tools

##### model_router
**Purpose**: Intelligently route requests to optimal models
**Input Format**:
```json
{
  "tool": "model_router",
  "params": {
    "task": "text_generation",
    "requirements": {
      "max_latency": 500,
      "min_quality": 0.9
    }
  }
}
```
**Output**: Recommended model with reasoning

##### prompt_optimizer
**Purpose**: Optimize prompts for efficiency
**Input Format**:
```json
{
  "tool": "prompt_optimizer",
  "params": {
    "prompt": "Your original prompt here",
    "optimization_goal": "token_reduction"
  }
}
```
**Output**: Optimized prompt with token savings

##### batch_processor
**Purpose**: Process multiple requests efficiently
**Input Format**:
```json
{
  "tool": "batch_processor",
  "params": {
    "requests": [...],
    "strategy": "parallel",
    "max_concurrent": 10
  }
}
```
**Output**: Batch results with performance metrics

#### 3. Quality Validation Tools

##### quality_validator
**Purpose**: Validate output quality
**Input Format**:
```json
{
  "tool": "quality_validator",
  "params": {
    "original_output": "...",
    "optimized_output": "...",
    "threshold": 0.95
  }
}
```
**Output**: Quality score with detailed comparison

##### a_b_tester
**Purpose**: Run A/B tests on models
**Input Format**:
```json
{
  "tool": "a_b_tester",
  "params": {
    "model_a": "gpt-4",
    "model_b": "claude-3",
    "test_cases": [...],
    "metrics": ["quality", "speed", "cost"]
  }
}
```
**Output**: Comparative analysis with recommendations

##### semantic_validator
**Purpose**: Validate semantic similarity
**Input Format**:
```json
{
  "tool": "semantic_validator",
  "params": {
    "text_1": "...",
    "text_2": "...",
    "method": "cosine_similarity"
  }
}
```
**Output**: Similarity score with explanation

#### 4. Cache Management Tools

##### cache_manager
**Purpose**: Manage response caching
**Input Format**:
```json
{
  "tool": "cache_manager",
  "params": {
    "action": "get|set|clear",
    "key": "cache_key",
    "ttl": 3600
  }
}
```
**Output**: Cache operation result

##### cache_analyzer
**Purpose**: Analyze cache performance
**Input Format**:
```json
{
  "tool": "cache_analyzer",
  "params": {
    "period": "day",
    "metrics": ["hit_rate", "savings", "size"]
  }
}
```
**Output**: Cache performance metrics

#### 5. Supply Catalog Tools

##### model_catalog
**Purpose**: Browse available models
**Input Format**:
```json
{
  "tool": "model_catalog",
  "params": {
    "filters": {
      "provider": "all",
      "capability": "text_generation",
      "max_cost": 0.05
    }
  }
}
```
**Output**: List of matching models with specs

##### provider_compare
**Purpose**: Compare model providers
**Input Format**:
```json
{
  "tool": "provider_compare",
  "params": {
    "providers": ["openai", "anthropic", "google"],
    "criteria": ["cost", "quality", "latency"]
  }
}
```
**Output**: Provider comparison matrix

##### model_benchmark
**Purpose**: Benchmark model performance
**Input Format**:
```json
{
  "tool": "model_benchmark",
  "params": {
    "models": ["gpt-4", "claude-3"],
    "benchmark_suite": "standard",
    "iterations": 10
  }
}
```
**Output**: Benchmark results with rankings

#### 6. Monitoring & Analytics Tools

##### usage_tracker
**Purpose**: Track AI usage patterns
**Input Format**:
```json
{
  "tool": "usage_tracker",
  "params": {
    "period": "week",
    "group_by": "model",
    "include_costs": true
  }
}
```
**Output**: Usage statistics and trends

##### performance_monitor
**Purpose**: Monitor system performance
**Input Format**:
```json
{
  "tool": "performance_monitor",
  "params": {
    "metrics": ["latency", "throughput", "error_rate"],
    "window": "1h"
  }
}
```
**Output**: Performance metrics dashboard

##### anomaly_detector
**Purpose**: Detect usage anomalies
**Input Format**:
```json
{
  "tool": "anomaly_detector",
  "params": {
    "metric": "cost",
    "sensitivity": "high",
    "lookback_days": 7
  }
}
```
**Output**: Detected anomalies with alerts

#### 7. Data Processing Tools

##### data_transformer
**Purpose**: Transform data formats
**Input Format**:
```json
{
  "tool": "data_transformer",
  "params": {
    "input_format": "csv",
    "output_format": "json",
    "data": "...",
    "schema": {...}
  }
}
```
**Output**: Transformed data

##### text_processor
**Purpose**: Process text data
**Input Format**:
```json
{
  "tool": "text_processor",
  "params": {
    "action": "summarize|extract|clean",
    "text": "...",
    "options": {...}
  }
}
```
**Output**: Processed text

##### embedding_generator
**Purpose**: Generate text embeddings
**Input Format**:
```json
{
  "tool": "embedding_generator",
  "params": {
    "text": "...",
    "model": "text-embedding-ada-002",
    "dimensions": 1536
  }
}
```
**Output**: Vector embeddings

#### 8. Workflow Automation Tools

##### workflow_builder
**Purpose**: Build optimization workflows
**Input Format**:
```json
{
  "tool": "workflow_builder",
  "params": {
    "steps": [...],
    "triggers": [...],
    "conditions": [...]
  }
}
```
**Output**: Workflow configuration

##### scheduler
**Purpose**: Schedule optimization tasks
**Input Format**:
```json
{
  "tool": "scheduler",
  "params": {
    "task": "daily_optimization",
    "cron": "0 9 * * *",
    "config": {...}
  }
}
```
**Output**: Schedule confirmation

##### automation_runner
**Purpose**: Run automated optimizations
**Input Format**:
```json
{
  "tool": "automation_runner",
  "params": {
    "automation_id": "auto-123",
    "dry_run": false
  }
}
```
**Output**: Automation execution results

#### 9. Reporting Tools

##### report_generator
**Purpose**: Generate optimization reports
**Input Format**:
```json
{
  "tool": "report_generator",
  "params": {
    "type": "savings|usage|performance",
    "period": "month",
    "format": "pdf|excel|markdown"
  }
}
```
**Output**: Generated report file

##### dashboard_builder
**Purpose**: Create custom dashboards
**Input Format**:
```json
{
  "tool": "dashboard_builder",
  "params": {
    "widgets": [...],
    "layout": "grid|list",
    "refresh_rate": 60
  }
}
```
**Output**: Dashboard configuration

##### alert_manager
**Purpose**: Manage optimization alerts
**Input Format**:
```json
{
  "tool": "alert_manager",
  "params": {
    "action": "create|update|delete",
    "alert": {
      "condition": "cost > 1000",
      "channel": "email|slack"
    }
  }
}
```
**Output**: Alert management result

### Tool Usage Examples

#### Example 1: Cost Optimization Workflow
```
User: "Optimize my GPT-4 usage that's costing $5000/month"

System uses:
1. cost_analyzer - Analyze current costs
2. model_router - Find alternatives
3. quality_validator - Ensure quality maintained
4. savings_calculator - Calculate savings
5. report_generator - Create recommendation report
```

#### Example 2: Quality Assurance Pipeline
```
User: "Ensure quality while switching to cheaper models"

System uses:
1. a_b_tester - Compare models
2. semantic_validator - Check output similarity
3. quality_validator - Validate quality scores
4. batch_processor - Test at scale
5. alert_manager - Set quality alerts
```

#### Example 3: Performance Optimization
```
User: "Reduce latency for my chat application"

System uses:
1. performance_monitor - Analyze current performance
2. cache_manager - Implement caching
3. model_router - Select faster models
4. batch_processor - Optimize batching
5. dashboard_builder - Create performance dashboard
```

### Tool Integration

#### REST API Integration
```python
import requests

response = requests.post(
    "https://api.netrasystems.ai/tools/execute",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "tool": "cost_analyzer",
        "params": {"model": "gpt-4", "period": "month"}
    }
)
result = response.json()
```

#### WebSocket Integration
```javascript
ws.send(JSON.stringify({
  action: "execute_tool",
  tool: "model_router",
  params: {
    task: "text_generation",
    requirements: {max_latency: 500}
  }
}));
```

#### SDK Integration
```python
from netra_sdk import NetraClient

client = NetraClient(api_key="your-key")
result = client.tools.execute(
    "quality_validator",
    original_output="...",
    optimized_output="...",
    threshold=0.95
)
```

### Tool Permissions

| Tool Category | Free Tier | Early Tier | Mid Tier | Enterprise |
|--------------|-----------|------------|----------|------------|
| Cost Analysis | Basic | Full | Full | Full + Custom |
| Optimization | Limited | Full | Full | Full + Custom |
| Quality Validation | Basic | Full | Full | Full + Custom |
| Cache Management | Read-only | Full | Full | Full + Custom |
| Supply Catalog | Browse | Full | Full | Full + Custom |
| Monitoring | Basic | Standard | Advanced | Full + Custom |
| Data Processing | Limited | Standard | Full | Full + Custom |
| Workflow Automation | None | Basic | Full | Full + Custom |
| Reporting | Basic | Standard | Advanced | Full + Custom |

### Tool Rate Limits

| Tier | Tools/Hour | Concurrent | Cache Size |
|------|------------|------------|------------|
| Free | 100 | 1 | 10 MB |
| Early | 1,000 | 5 | 100 MB |
| Mid | 10,000 | 20 | 1 GB |
| Enterprise | Unlimited | Unlimited | Unlimited |

**Developer Note**: Tool implementations in `app/tools/`. Tool registry in `app/services/tool_service.py`. Rate limiting in `app/middleware/rate_limiter.py`.

---

## Appendix

### Glossary
- **Agent**: AI-powered component that processes requests
- **Thread**: Conversation context container
- **Optimization**: Process of reducing cost/latency while maintaining quality
- **Savings Delta**: Difference between original and optimized costs
- **Quality Score**: Similarity measure between outputs (0-1)
- **TTL**: Time-to-live for cached entries
- **Circuit Breaker**: Failure prevention mechanism

### Version History
- v1.0.0: Initial release with basic optimization
- v1.1.0: Added bulk operations and caching
- v1.2.0: Multi-agent architecture
- v1.3.0: Enterprise features and admin tools
- v1.4.0: Real-time WebSocket optimization
- v2.0.0: SSOT Agent Instance Factory Migration and complete system stability validation

### Additional Resources
- [API Documentation](./API_DOCUMENTATION.md)
- [Architecture Guide](./ARCHITECTURE.md)
- [Testing Guide](./TESTING_GUIDE.md)
- [Security Whitepaper](https://netrasystems.ai/security)
- [ROI Calculator](https://netrasystems.ai/calculator)

---

*Last Updated: 2025-09-14*
*Version: 2.0.0*
*© 2025 Netra Systems - Enterprise AI Optimization*

### Recent Major Infrastructure Achievements (September 2025)
- **✅ Issue #1116 COMPLETE:** SSOT Agent Instance Factory Migration - Complete factory-based user isolation architecture
- **✅ Issue #1107 COMPLETE:** Phase 2 SSOT Mock Factory validation tests - Comprehensive validation suite implementation
- **✅ Issue #1101 COMPLETE:** SSOT WebSocket Bridge Migration - Complete SSOT message routing with comprehensive audit
- **✅ System Stability Validation:** Complete validation report ensuring production readiness with factory patterns
- **✅ Enhanced Security:** Factory-based isolation providing complete user separation and data protection
- **✅ Test Infrastructure:** Comprehensive agent testing with 516% WebSocket bridge improvement (11.1% → 57.4%)
- **✅ Mission Critical Protection:** 169 tests protecting $500K+ ARR core business functionality
- **✅ Production Ready:** All critical infrastructure validated and operational