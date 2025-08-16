# NETRA APEX QUICK START GUIDE
## Day 1 for 100 Engineers: Start Building Revenue NOW

---

# 🚀 IMMEDIATE SETUP (First 30 Minutes)

## Step 1: Clone and Setup
```bash
# Clone the repository
git clone https://github.com/netra-systems/netra-apex
cd netra-apex

# Create your feature branch (use your squad name)
git checkout -b squad-[YOUR_SQUAD_NUMBER]-week1

# Install dependencies
pip install -r requirements.txt
npm install  # Frontend teams

# Copy environment template
cp .env.example .env
```

## Step 2: Required Environment Variables
```env
# Add these to your .env file
DATABASE_URL=postgresql://localhost:5432/apex_dev
REDIS_URL=redis://localhost:6379
CLICKHOUSE_URL=http://localhost:8123

# Stripe (test keys)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...

# LLM Providers (test keys)
OPENAI_API_KEY=sk-test-...
ANTHROPIC_API_KEY=sk-ant-test-...
```

## Step 3: Start Development Services
```bash
# Terminal 1: Start all services
python dev_launcher/launcher.py

# Terminal 2: Run tests continuously  
python test_runner.py --watch --level unit

# Terminal 3: Frontend (if applicable)
cd frontend && npm run dev
```

---

# 👥 FIND YOUR SQUAD

## Squad Assignments & First Tasks

### Squad 1: Gateway Core (Room: #apex-gateway-core)
**Day 1 Deliverable**: Basic HTTP proxy that forwards requests to OpenAI

```python
# Your first code: app/gateway/proxy_core.py
import httpx
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/v1/completions")
async def proxy_completion(request: Request):
    """Proxy OpenAI completion requests"""
    # TODO: Forward to OpenAI
    # TODO: Return response
    pass  # START HERE
```

### Squad 2: Optimization Engine (Room: #apex-optimization)
**Day 1 Deliverable**: Simple prompt cache check

```python
# Your first code: app/optimizations/semantic_cache.py
import hashlib
from app.db.cache_core import redis_client

async def check_cache(prompt: str) -> Optional[str]:
    """Check if we've seen this prompt before"""
    key = hashlib.md5(prompt.encode()).hexdigest()
    # TODO: Check Redis
    # TODO: Return cached response if exists
    pass  # START HERE
```

### Squad 3: PoV & Attribution (Room: #apex-attribution)
**Day 1 Deliverable**: Calculate token difference between requests

```python
# Your first code: app/attribution/savings_calculator.py
def calculate_savings(original_tokens: int, optimized_tokens: int) -> float:
    """Calculate $ saved from optimization"""
    # TODO: Get token prices
    # TODO: Calculate difference
    # TODO: Return savings amount
    pass  # START HERE
```

### Squad 4: Billing & Monetization (Room: #apex-billing)
**Day 1 Deliverable**: Track API calls per user

```python
# Your first code: app/services/usage_tracking_service.py
async def track_usage(user_id: str, tokens: int):
    """Track usage for billing"""
    # TODO: Insert into database
    # TODO: Check against tier limits
    # TODO: Return usage status
    pass  # START HERE
```

### Squad 5: Analytics & Telemetry (Room: #apex-analytics)
**Day 1 Deliverable**: Parse OpenAI response for token count

```python
# Your first code: app/telemetry/log_parser.py
def parse_openai_response(response: dict) -> dict:
    """Extract metrics from OpenAI response"""
    # TODO: Extract token usage
    # TODO: Extract model used
    # TODO: Return metrics dict
    pass  # START HERE
```

### Squad 6: Frontend & Dashboard (Room: #apex-frontend)
**Day 1 Deliverable**: Basic usage display component

```tsx
// Your first code: frontend/components/UsageDisplay.tsx
export function UsageDisplay({ usage }: { usage: Usage }) {
  // TODO: Show tokens used
  // TODO: Show cost saved
  // TODO: Show tier limits
  return <div>START HERE</div>
}
```

---

# 📋 CRITICAL RULES (MEMORIZE NOW)

## The 300/8 Rule
```python
# ❌ BAD: Files over 300 lines
# ❌ BAD: Functions over 8 lines

# ✅ GOOD: Modular files under 300 lines
# ✅ GOOD: Functions under 8 lines

def process_request(request):  # Max 8 lines!
    validated = validate(request)
    optimized = optimize(validated)
    cached = check_cache(optimized)
    if cached:
        return cached
    response = execute(optimized)
    save_to_cache(response)
    return response
```

## The Revenue Rule
```python
# Before writing ANY code, ask:
# 1. What customer segment does this serve?
# 2. How much revenue does this generate?
# 3. What % of AI spend does this capture?

# Document it:
"""
Feature: Semantic Caching
BVJ:
- Segment: All tiers
- Revenue Impact: 15-25% cost savings = $3-5K MRR per customer
- Business Goal: Direct value creation through optimization
"""
```

---

# 🔥 WEEK 1 SPRINT GOALS

## Overall Goal: Gateway Processing Requests

### Success Metrics (End of Week 1)
- [ ] Gateway proxy working end-to-end
- [ ] Basic caching operational
- [ ] Usage tracking active
- [ ] 1000+ test requests processed
- [ ] All tests passing

### Daily Checkpoints

#### Day 1 (Today)
- [ ] Environment setup complete
- [ ] First module created and tested
- [ ] Squad communication established
- [ ] Initial commit pushed

#### Day 2
- [ ] Core proxy forwarding requests
- [ ] Basic cache implementation
- [ ] Usage database schema created

#### Day 3
- [ ] Optimization pipeline structure
- [ ] Attribution calculations working
- [ ] Frontend scaffolding complete

#### Day 4
- [ ] Integration testing between squads
- [ ] Performance benchmarks met (<50ms latency)
- [ ] Error handling implemented

#### Day 5
- [ ] Full end-to-end flow working
- [ ] Code review and cleanup
- [ ] Documentation updated
- [ ] Demo prepared

---

# 💻 DEVELOPMENT WORKFLOW

## Git Workflow
```bash
# Daily workflow
git pull origin main
git checkout -b feature/squad-X-description

# Make changes (keep commits small)
git add -p  # Stage selectively
git commit -m "feat(gateway): implement request forwarding"

# Push for review
git push origin feature/squad-X-description

# Create PR with template
```

## PR Template
```markdown
## Summary
[What does this PR do?]

## BVJ (Business Value Justification)
- Segment: [Free/Early/Mid/Enterprise]
- Revenue Impact: [Specific $ or %]
- Business Goal: [How this makes money]

## Checklist
- [ ] All files < 300 lines
- [ ] All functions < 8 lines
- [ ] Tests written and passing
- [ ] Types properly defined
- [ ] No test stubs in production code
```

## Testing Requirements
```bash
# Before EVERY commit
python test_runner.py --level unit

# Before PR
python scripts/check_architecture_compliance.py
python test_runner.py --level integration

# Squad-specific tests
pytest app/tests/test_[your_module].py -v
```

---

# 🛠 TOOLING & HELPERS

## Architecture Compliance Checker
```bash
# Check your code meets requirements
python scripts/check_architecture_compliance.py app/gateway/

# Output:
# ✅ proxy_core.py: 245 lines (OK)
# ❌ router.py: 312 lines (VIOLATION - split required)
# ❌ function 'process_all': 12 lines (VIOLATION - max 8)
```

## Module Splitter Helper
```bash
# Automatically split large files
python scripts/split_large_files.py app/gateway/large_file.py

# Creates:
# app/gateway/large_file_core.py (250 lines)
# app/gateway/large_file_helpers.py (200 lines)
```

## BVJ Generator
```bash
# Generate BVJ for your feature
python scripts/generate_bvj.py "Semantic Caching" "All" "15-25% savings"

# Output:
# BVJ generated and added to feature documentation
```

---

# 📚 ESSENTIAL DOCUMENTATION

## Must Read (Before Coding)
1. `CLAUDE.md` - System constraints and principles
2. `SPEC/type_safety.xml` - Type requirements
3. `SPEC/conventions.xml` - Coding standards
4. `business_execution_plan.md` - Why we're building this

## Squad-Specific Docs
- Gateway: `docs/gateway_architecture.md`
- Optimization: `docs/optimization_pipeline.md`
- Billing: `docs/payment_integration.md`
- Frontend: `docs/frontend_patterns.md`

---

# 🎯 QUICK WINS (Start Here)

## Gateway Squad
```python
# Simplest working proxy (30 mins)
@app.post("/v1/completions")
async def proxy(request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/completions",
            json=await request.json(),
            headers={"Authorization": f"Bearer {OPENAI_KEY}"}
        )
    return response.json()
```

## Optimization Squad
```python
# Simplest cache (30 mins)
cache = {}  # In-memory for now

def get_from_cache(prompt: str):
    key = hashlib.md5(prompt.encode()).hexdigest()
    return cache.get(key)

def save_to_cache(prompt: str, response: str):
    key = hashlib.md5(prompt.encode()).hexdigest()
    cache[key] = response
```

## Attribution Squad
```python
# Simplest savings calc (30 mins)
PRICE_PER_1K_TOKENS = 0.002  # OpenAI pricing

def calculate_savings(original: int, optimized: int) -> float:
    saved_tokens = original - optimized
    return (saved_tokens / 1000) * PRICE_PER_1K_TOKENS
```

---

# 🚨 TROUBLESHOOTING

## Common Issues & Solutions

### Database Connection Error
```bash
# Fix: Start local postgres
docker run -p 5432:5432 -e POSTGRES_PASSWORD=apex postgres:14

# Or use shared dev database
DATABASE_URL=postgresql://apex_dev@dev.netra.ai:5432/apex
```

### Redis Connection Error
```bash
# Fix: Start local redis
docker run -p 6379:6379 redis:alpine

# Or use shared dev redis
REDIS_URL=redis://dev.netra.ai:6379
```

### Import Errors
```bash
# Fix: Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version (must be 3.11+)
python --version
```

### Test Failures
```bash
# Fix: Reset test database
python scripts/reset_test_db.py

# Run specific test with debug
pytest app/tests/test_specific.py -vvs
```

---

# 📞 GET HELP

## Slack Channels
- **#apex-help** - General questions
- **#apex-blockers** - Blocking issues (urgent)
- **#apex-dev** - Development discussion
- **Your Squad Channel** - Squad-specific help

## Key People
- **Tech Lead**: @tech-lead - Architecture decisions
- **Revenue Lead**: @revenue-lead - Business/BVJ questions  
- **DevOps**: @devops - Infrastructure/deployment
- **QA Lead**: @qa-lead - Testing strategies

## Daily Standups
- **9:00 AM**: Squad standups (15 min)
- **10:00 AM**: Cross-squad sync (leads only)
- **5:00 PM**: EOD progress check

---

# ✅ YOUR DAY 1 CHECKLIST

Before you leave today, ensure:

- [ ] Development environment fully working
- [ ] Joined your squad Slack channel
- [ ] Created your first module file
- [ ] Written at least one function (< 8 lines!)
- [ ] Run tests successfully
- [ ] Pushed first commit to feature branch
- [ ] Updated squad progress tracker

---

# 🎉 WELCOME TO APEX!

Remember:
- **Ship Daily** - Small increments, constant progress
- **Revenue First** - Every line creates value
- **300/8 Rule** - Keep it modular
- **Test Everything** - Quality matters
- **Ask Questions** - We're here to help

**LET'S BUILD THE FUTURE OF AIOPS!**

---

**Quick Commands Reference Card**
```bash
# Most used commands
python dev_launcher.py              # Start everything
python test_runner.py --level unit  # Run tests
python scripts/check_architecture_compliance.py  # Check code
git checkout -b feature/...        # New feature branch
pytest app/tests/... -v            # Run specific tests
```

**END OF QUICK START GUIDE**

**Now stop reading and START CODING! Revenue awaits! 🚀💰**