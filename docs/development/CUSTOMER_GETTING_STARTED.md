# Netra AI Platform - Getting Started Guide

## Welcome to Netra

Netra is your AI optimization copilot - an intelligent platform that analyzes your AI workloads, identifies optimization opportunities, and provides actionable recommendations to reduce costs and improve performance while maintaining quality.

## Prerequisites

### Required Software
- **Python 3.9+** (3.11+ recommended for best performance)
- **Node.js 18+** (for frontend development)
- **Git** (for version control)

### Optional Services (with automatic fallbacks)
- **PostgreSQL 14+** - Primary database (falls back to SQLite if unavailable)
- **Redis 7+** - Caching layer (disabled if unavailable)
- **ClickHouse** - Analytics database (limited analytics if unavailable)

## Quick Start for Development

### Step 1: Clone and Setup
```bash
# Clone repository
git clone https://github.com/netra-systems/netra-apex.git
cd netra-core-generation-1

# Setup Python environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup frontend
cd frontend
npm install
cd ..
```

### Step 2: Configure Environment
Create a `.env` file with your configuration. For development with secrets from Google Secret Manager:

```bash
# Fetch secrets automatically (requires Google Cloud authentication)
python scripts/fetch_secrets_to_env.py
```

Or create `.env` manually:
```bash
# Core Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database (PostgreSQL or SQLite fallback)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/netra_db
# Or use SQLite: DATABASE_URL=sqlite+aiosqlite:///./netra.db

# Required: Primary LLM API Key
GEMINI_API_KEY=your-gemini-api-key

# Optional Services
REDIS_URL=redis://localhost:6379
CLICKHOUSE_URL=clickhouse://localhost:9000/default

# Security Keys (generate secure keys for production)
JWT_SECRET_KEY=your-jwt-secret-key
FERNET_KEY=your-fernet-key
SECRET_KEY=your-secret-key
```

### Step 3: Start Development Environment

#### Recommended: Using Dev Launcher
```bash
# Best configuration for development
python scripts/dev_launcher.py --dynamic --no-backend-reload --load-secrets

# What this does:
# - Finds free ports automatically
# - 30-50% faster without backend reload
# - Loads secrets from cloud if configured
# - Starts both frontend and backend
# - Shows clear status messages
```

#### Alternative Configurations
```bash
# With hot reload (slower but auto-refreshes)
python scripts/dev_launcher.py --dynamic

# Maximum performance (no reload at all)
python scripts/dev_launcher.py --dynamic --no-reload

# Custom ports
python scripts/dev_launcher.py --backend-port 8080 --frontend-port 3001

# Backend only
python scripts/dev_launcher.py --backend-only

# Frontend only  
python scripts/dev_launcher.py --frontend-only
```

### Step 4: Verify Installation
```bash
# Run quick smoke tests (< 30 seconds)
python test_runner.py --level smoke --fast-fail

# Run integration tests (DEFAULT for feature validation)
python test_runner.py --level integration --no-coverage --fast-fail

# If test runner has issues, use fallback
python test_runner.py --simple
```

### Step 5: Validate String Literals Index

Netra uses a centralized string literals index to prevent LLM hallucination and ensure consistency:

```bash
# Generate/update the string literals index
python scripts/scan_string_literals.py

# Validate existing string usage
python scripts/query_string_literals.py --validate

# Check for inconsistencies
python scripts/query_string_literals.py --category all --format table
```

**Why This Matters**: The string literals index ensures that all agents use correct platform-specific constants (API endpoints, configuration keys, database table names, etc.). This prevents bugs from typos and improves system reliability.

**What It Does**:
- Scans codebase for all string constants
- Categorizes them by type (config, paths, identifiers, etc.)
- Creates a searchable index at `SPEC/generated/string_literals.json`
- Validates consistency across the platform

**Integration**: The dev_launcher automatically validates string literals on startup. Any inconsistencies are reported in the logs.

## Quick Start for Users

### Step 1: Access the Platform
1. Navigate to your Netra instance (http://localhost:3000 for development)
2. Sign in using Google OAuth (SSO) if configured
3. You'll be greeted with the modern glassmorphic chat interface

### Step 2: Start Your First Conversation
Simply describe your optimization goal in natural language. Netra understands context and will guide you through the process.

**Example first prompts:**
- "Help me reduce my AI costs by 30%"
- "My AI responses are too slow, I need them 2x faster"
- "Analyze my GPT-4 usage and suggest optimizations"

## Understanding How Netra Works

### The Multi-Agent System
When you submit a request, Netra orchestrates multiple specialized agents:

1. **Triage Agent** - Understands your request and determines complexity
2. **Data Agent** - Analyzes your historical usage and performance data
3. **Optimization Agent** - Applies 30+ specialized optimization techniques
4. **Action Agent** - Creates your implementation roadmap
5. **Reporting Agent** - Compiles findings into actionable reports

You'll see real-time updates as each agent works on your request.

## Effective Prompt Patterns

### 1. Cost Optimization Prompts

**Basic Pattern:**
```
"I need to reduce [cost metric] by [percentage] for [workload/model]"
```

**Examples:**
- "I need to reduce my monthly AI spend by 40%"
- "Our GPT-4 costs are too high, find optimization opportunities"
- "Analyze our API usage and identify the most expensive operations"

**Advanced Pattern with Constraints:**
```
"Reduce costs by [percentage] while maintaining [quality metric] above [threshold]"
```

**Examples:**
- "Reduce costs by 30% while keeping response accuracy above 95%"
- "Cut API expenses in half but maintain sub-2 second latency"

### 2. Performance Optimization Prompts

**Basic Pattern:**
```
"Improve [performance metric] by [factor] for [use case]"
```

**Examples:**
- "Make our chatbot responses 3x faster"
- "Reduce latency for our document processing pipeline by 50%"
- "Optimize throughput for high-volume API calls"

**Detailed Analysis Pattern:**
```
"Analyze [component] for [issue type] and provide [deliverable]"
```

**Examples:**
- "Analyze our embedding generation for bottlenecks and provide optimization recommendations"
- "Review our caching strategy for inefficiencies and suggest improvements"

### 3. Capacity Planning Prompts

**Future Planning Pattern:**
```
"We expect [change] in [timeframe]. What's the impact on [metric]?"
```

**Examples:**
- "We're expecting 50% more users next month. How will this affect our costs?"
- "Planning to launch in 3 new regions. What's the infrastructure impact?"
- "If we double our API calls, where will we hit rate limits?"

### 4. Model Selection & Migration Prompts

**Model Comparison Pattern:**
```
"Compare [current model] with [alternative models] for [use case]"
```

**Examples:**
- "Should we switch from GPT-4 to Claude-3-Sonnet for customer support?"
- "Which of our GPT-3.5 calls could use GPT-4o-mini instead?"
- "Evaluate if upgrading to GPT-5 is worth it for our use case"

**Migration Analysis Pattern:**
```
"Analyze the impact of migrating from [current] to [target] for [workload]"
```

**Examples:**
- "What's the ROI of moving our summarization tasks to a cheaper model?"
- "Should we keep using GPT-4 or downgrade some features to GPT-3.5?"

### 5. Comprehensive Audit Prompts

**System-Wide Analysis Pattern:**
```
"Audit all [component type] and identify [optimization type] opportunities"
```

**Examples:**
- "Audit all API calls and identify caching opportunities"
- "Review all model usage and suggest optimal configurations"
- "Analyze our entire AI stack for cost reduction opportunities"

## Advanced Prompt Techniques

### 1. Multi-Objective Optimization
Combine multiple goals in a single prompt:

**Pattern:**
```
"I need to [objective 1] and [objective 2] while [constraint]"
```

**Example:**
```
"I need to reduce costs by 25% and improve latency by 2x while maintaining current accuracy levels"
```

### 2. Prioritized Optimization
Specify what matters most:

**Pattern:**
```
"Optimize for [primary goal], with [secondary goals] as nice-to-haves"
```

**Example:**
```
"Optimize for maximum cost reduction, with latency improvements as a bonus if possible"
```

### 3. Scenario-Based Analysis
Test different scenarios:

**Pattern:**
```
"Compare optimization strategies for [scenario A] vs [scenario B]"
```

**Example:**
```
"Compare cost optimization strategies for steady-state traffic vs 10x traffic spikes"
```

### 4. Time-Boxed Improvements
Focus on quick wins:

**Pattern:**
```
"What optimizations can we implement in [timeframe] for [impact]?"
```

**Example:**
```
"What can we do this week to reduce costs by at least 15%?"
```

## Best Practices for Maximum Value

### 1. Start with High-Level Goals
Begin with your business objective, not technical details:
- ✅ "We need to cut our AI budget in half"
- ❌ "Optimize the temperature parameter on our GPT-4 calls"

### 2. Provide Context When Available
The more context you provide, the better the recommendations:
```
"We're a customer support platform handling 10k tickets daily using GPT-4. 
Our average response time is 5 seconds and costs are $3k/month. 
We need to reduce costs by 40% without hurting customer satisfaction."
```

### 3. Ask for Specific Deliverables
Be clear about what you need:
- "Provide a step-by-step implementation plan"
- "Generate a cost comparison table"
- "Create a migration roadmap with timelines"
- "Calculate ROI for each optimization"

### 4. Iterate and Refine
Start broad, then drill down:
1. First: "Analyze our AI costs"
2. Then: "Focus on the document processing costs"
3. Finally: "Show me how to optimize the embedding generation"

### 5. Use Follow-Up Questions
Netra maintains conversation context:
- Initial: "What are our biggest cost drivers?"
- Follow-up: "How much would we save by optimizing the top 3?"
- Next: "Create an implementation plan for the first one"

## Common Use Cases and Templates

### Use Case 1: Monthly Cost Review
```
"Perform a monthly cost analysis for [Month]. 
Identify the top 5 cost drivers and provide optimization recommendations for each. 
Calculate potential savings and implementation effort."
```

### Use Case 2: New Feature Impact Assessment
```
"We're launching [feature] expecting [usage pattern]. 
Analyze the cost and performance impact. 
Recommend the optimal model and configuration."
```

### Use Case 3: Emergency Cost Reduction
```
"Our AI costs exceeded budget by [amount]. 
Need immediate actions to reduce spend by [percentage] this month. 
Prioritize by ease of implementation and impact."
```

### Use Case 4: Performance SLA Compliance
```
"Our SLA requires [latency requirement]. 
Current p99 latency is [current latency]. 
Find all optimization opportunities to meet SLA at minimum cost."
```

### Use Case 5: Model Upgrade Decision
```
"[New model] was just released. 
Compare it with our current [existing model] setup. 
Should we upgrade? What's the ROI? What are the risks?"
```

## Interpreting Results

### Understanding Agent Responses

Each agent provides specific insights:

- **Triage Results**: Problem classification and priority
- **Data Analysis**: Metrics, trends, and patterns from your usage
- **Optimization Recommendations**: Ranked by impact and effort
- **Action Plans**: Step-by-step implementation guides
- **Reports**: Executive summaries with ROI calculations

### Key Metrics to Watch

- **Cost Reduction**: Actual dollar amounts saved
- **Performance Gains**: Latency reduction percentages
- **Quality Scores**: Accuracy/effectiveness maintenance
- **Implementation Effort**: Hours or days required
- **Risk Level**: Potential impact on operations

## Tips for Success

### DO:
- Start with clear business objectives
- Provide usage context and constraints
- Ask for specific metrics and ROI calculations
- Request implementation roadmaps
- Iterate based on findings

### DON'T:
- Jump straight to technical implementations
- Ignore quality impacts of cost optimizations
- Optimize in isolation without considering system-wide effects
- Implement all recommendations at once
- Forget to measure results after implementation

## Getting Help

### For Technical Questions:
Ask Netra directly:
- "How do I implement caching for my use case?"
- "Explain the trade-offs between different optimization strategies"
- "What metrics should I track after optimization?"

### For Business Cases:
Request specific deliverables:
- "Generate an executive summary of optimization opportunities"
- "Create a business case for the recommended changes"
- "Calculate 6-month and 12-month ROI projections"

## Next Steps

1. **Run Your First Analysis**: Start with a high-level cost or performance audit
2. **Review Recommendations**: Focus on high-impact, low-effort optimizations
3. **Create Implementation Plan**: Ask Netra for detailed steps
4. **Track Results**: Monitor metrics before and after changes
5. **Iterate**: Continue optimizing based on results

Remember: Netra is your optimization copilot. The more you interact with it, the better it understands your specific needs and constraints. Don't hesitate to ask clarifying questions or request different perspectives on your optimization challenges.

## Development Workflow

### Complete Developer Workflow: Setup to First Commit

#### 1. Initial Setup
```bash
# Clone and setup (Steps 1-2 above)
git clone https://github.com/netra-systems/netra-apex.git
cd netra-core-generation-1
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt requirements-dev.txt
```

#### 2. Environment Configuration
```bash
# Option A: Auto-fetch secrets (if Google Cloud is configured)
python scripts/fetch_secrets_to_env.py

# Option B: Manual .env creation (see Step 2 above for template)
cp config/.env.example .env  # Edit with your settings
```

#### 3. String Literals Validation
```bash
# Update string literals index (critical for consistency)
python scripts/scan_string_literals.py
python scripts/query_string_literals.py --validate
```

#### 4. Development Environment Start
```bash
# Start development environment
python scripts/dev_launcher.py --dynamic --no-backend-reload --load-secrets
```

#### 5. Pre-Development Validation
```bash
# Smoke tests (< 30s) - ALWAYS run before starting work
python test_runner.py --level smoke --fast-fail

# If working on agents specifically
python test_runner.py --level agents --real-llm
```

#### 6. Development & Testing Cycle
```bash
# During development - fast feedback loop
python test_runner.py --level integration --no-coverage --fast-fail

# Code quality checks
ruff check app/ && black app/ --check && mypy app/
cd frontend && npm run lint && npm run typecheck
```

#### 7. Pre-Commit Validation
```bash
# Before committing - comprehensive validation
python test_runner.py --level integration --no-coverage --fast-fail

# Update string literals if you added new constants
python scripts/scan_string_literals.py

# Architecture compliance check
python scripts/check_architecture_compliance.py
```

#### 8. Commit & Push
```bash
# Standard commit workflow
git add .
git commit -m "feat: add optimization feature with BVJ analysis"
git push origin feature/optimization-feature
```

### Running Tests

#### Unified Test Runner (Recommended)
```bash
# Quick validation before commits (< 30s)
python test_runner.py --level smoke --fast-fail

# Development testing (1-2 min)
python test_runner.py --level unit --no-coverage --fast-fail

# Feature validation (3-5 min) - DEFAULT
python test_runner.py --level integration --no-coverage --fast-fail

# Agent changes with real LLM
python test_runner.py --level agents --real-llm

# Before releases
python test_runner.py --level integration --real-llm

# Full suite with coverage (10-15 min)
python test_runner.py --level comprehensive

# Critical paths only (1-2 min)
python test_runner.py --level critical
```

### Code Quality
```bash
# Python linting
ruff check app/
black app/ --check
mypy app/

# JavaScript/TypeScript linting
cd frontend
npm run lint
npm run typecheck
```

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Use dynamic ports to automatically find free ports
python dev_launcher.py --dynamic
```

#### Database Connection Errors
```bash
# Check PostgreSQL is running
pg_isready

# Or use SQLite fallback
export DATABASE_URL=sqlite+aiosqlite:///./netra.db
```

#### Missing Dependencies
```bash
# Reinstall Python dependencies
pip install -r requirements.txt --force-reinstall

# Reinstall Node dependencies
cd frontend && rm -rf node_modules package-lock.json
npm install
```

#### String Literals Validation Errors
```bash
# Regenerate the index
python scripts/scan_string_literals.py --force

# Check for specific category issues
python scripts/query_string_literals.py --category config --validate

# View inconsistencies in table format
python scripts/query_string_literals.py --category all --format table
```

#### Architecture Compliance Issues
```bash
# Check compliance status
python scripts/check_architecture_compliance.py

# View detailed compliance report
python scripts/check_architecture_compliance.py --detailed

# Fix specific compliance issues
python scripts/check_architecture_compliance.py --fix-module <module_name>
```

#### LLM API Errors
```bash
# Disable LLM for development
export DEV_MODE_DISABLE_LLM=true

# Or mock responses
export LLM_MOCK_MODE=true
```

## Important Notes

### Following CLAUDE.md Guidelines
When developing, always refer to `CLAUDE.md` for:
- Core principles and conventions
- Specification map and critical specs
- Testing strategy and requirements
- Common operations and quick fixes

### Key Development Patterns
- **Async First**: Use async/await for all I/O operations
- **Type Safety**: Pydantic models (backend), TypeScript types (frontend)
- **Repository Pattern**: All database access through repositories
- **Error Handling**: Use NetraException with proper context
- **UI Design**: Glassmorphic design, NO blue gradient bars
- **NO Test Stubs**: Never add test implementations in production services

### Before Any Code Change (Critical Checklist)
1. ✅ **Check Learnings**: Consult [`SPEC/learnings/index.xml`](../../SPEC/learnings/index.xml) for related insights
2. ✅ **Review Specs**: Check [`SPEC/type_safety.xml`](../../SPEC/type_safety.xml) and [`SPEC/conventions.xml`](../../SPEC/conventions.xml)
3. ✅ **Code Changes**: Consult [`SPEC/code_changes.xml`](../../SPEC/code_changes.xml) for change checklist
4. ✅ **Smoke Tests**: Run `python test_runner.py --level smoke --fast-fail`
5. ✅ **String Literals**: Update index if adding new constants: `python scripts/scan_string_literals.py`
6. ✅ **No Test Stubs**: Check [`SPEC/no_test_stubs.xml`](../../SPEC/no_test_stubs.xml) - NO test stubs in production
7. ✅ **Update Specs**: Update documentation to reflect implemented reality

### After Code Changes (Verification Checklist)
1. ✅ **Integration Tests**: `python test_runner.py --level integration --no-coverage --fast-fail`
2. ✅ **Architecture Compliance**: `python scripts/check_architecture_compliance.py`
3. ✅ **String Literals**: Validate consistency: `python scripts/query_string_literals.py --validate`
4. ✅ **Update Specs**: Finalize specs to reflect implemented changes
5. ✅ **Commit Message**: Include BVJ (Business Value Justification) context

### Business Value Justification (BVJ) Template

Every development task must include BVJ context:

```
**BVJ**: 
- Segment: [Free/Early/Mid/Enterprise/Platform]
- Business Goal: [Conversion/Expansion/Retention/Stability]
- Value Impact: [How this enhances customer AI operations]
- Strategic/Revenue Impact: [Quantifiable benefit to Netra]
```

---

*Welcome to smarter AI operations with Netra!*