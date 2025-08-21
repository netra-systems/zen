# Netra Apex Quick Start Guide for Engineers
## Get Productive in 30 Minutes

---

## Welcome Elite Engineer! 🚀

You're part of a 100-person team building the future of AIOps. This guide gets you coding in 30 minutes.

**Your Mission**: Build Netra Apex - the platform that saves companies millions on AI costs while we capture 20% of those savings.

---

## 1. Find Your Team (2 minutes)

### Team Assignments
```
Team 1: API Gateway Core        → Channel: #team-gateway
Team 2: Optimization Engine     → Channel: #team-optimization  
Team 3: Billing & Monetization  → Channel: #team-billing
Team 4: Data Pipeline           → Channel: #team-data
Team 5: Frontend & Dashboard    → Channel: #team-frontend
Team 6: Infrastructure Opt      → Channel: #team-infrastructure
Team 7: Validation Workbench    → Channel: #team-validation
Team 8: AI Agents              → Channel: #team-agents
Team 9: Testing & Quality       → Channel: #team-testing
Team 10: DevOps & Platform      → Channel: #team-devops
```

**Action**: Join your team's Slack channel NOW.

---

## 2. Setup Development Environment (10 minutes)

### Quick Setup Script
```bash
# Clone the repository
git clone https://github.com/netra-systems/apex.git
cd apex

# Run the automated setup
python scripts/dev_setup.py --team=YOUR_TEAM_NUMBER

# This will:
# - Install dependencies for your team
# - Set up your local database
# - Configure your IDE
# - Create your feature branch
```

### Manual Setup (if script fails)
```bash
# Backend setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend setup (Team 5 only)
cd frontend
npm install

# Database setup
docker-compose up -d postgres clickhouse redis

# Apply migrations
alembic upgrade head
```

---

## 3. Critical Rules - MEMORIZE (3 minutes)

### The Three Commandments
1. **300/8 Rule**: No file >300 lines, no function >8 lines
2. **Business First**: Every feature must justify revenue impact
3. **Test Everything**: 100% coverage, 2+ tests per function

### Before You Code
```python
# ALWAYS ask yourself:
# 1. Which customer segment does this serve?
# 2. How much AI spend does this address?
# 3. What's the revenue impact?

# Example Business Value Justification (BVJ):
"""
Feature: Semantic Cache
Segment: All (Free → Enterprise)
AI Spend Impact: 15-25% reduction in API costs
Revenue Impact: +$50K MRR via 20% performance fee
"""
```

### Architecture Compliance
```bash
# Run before EVERY commit
python scripts/check_architecture_compliance.py

# This checks:
# - File length ≤ 300 lines
# - Function length ≤ 8 lines
# - Type safety
# - Test coverage
```

---

## 4. Your First Task (15 minutes)

### Step 1: Get Your Assignment
```bash
# Check your team's task board
python scripts/get_my_task.py --team=YOUR_TEAM_NUMBER

# Or check Jira/Linear
# Your team lead has prepared starter tasks
```

### Step 2: Create Your Branch
```bash
git checkout -b team-X/your-name/task-description
# Example: team-2/john/implement-semantic-cache
```

### Step 3: Code Template
```python
# app/your_module/your_file.py
"""
Module: [Your module name]
Team: [Your team number]
Engineer: [Your name]
BVJ: [Business Value Justification]
"""

from typing import Optional, List, Dict
from netra_backend.app.core.exceptions import NetraException

class YourClass:
    """Single responsibility class."""
    
    def your_method(self, param: str) -> str:
        """8 lines max."""
        # Line 1
        # Line 2
        # ...
        # Line 8 max
        return result

# File must be ≤300 lines total
```

### Step 4: Write Tests FIRST
```python
# app/tests/unit/test_your_module.py
import pytest
from netra_backend.app.your_module.your_file import YourClass

class TestYourClass:
    def test_your_method_success(self):
        """Test successful case."""
        instance = YourClass()
        result = instance.your_method("input")
        assert result == "expected"
    
    def test_your_method_edge_case(self):
        """Test edge case."""
        instance = YourClass()
        result = instance.your_method("")
        assert result == "default"
```

### Step 5: Run Tests
```bash
# Run your tests
python test_runner.py --level unit --module your_module

# Run all tests for your team
python test_runner.py --team YOUR_TEAM_NUMBER
```

---

## 5. Team-Specific Quick Starts

### Team 1: API Gateway
```python
# Your focus: High-performance proxy
# Key files: app/gateway/
# First task: Implement provider abstraction

# Example starter code:
class ProviderRouter:
    async def route_request(self, request: Request) -> Response:
        provider = self.select_provider(request)
        return await provider.execute(request)
```

### Team 2: Optimization Engine
```python
# Your focus: Maximize savings
# Key files: app/services/optimization/
# First task: Implement semantic cache

# Example starter code:
class SemanticCache:
    async def find_similar(self, prompt: str) -> Optional[str]:
        embedding = await self.embed(prompt)
        return await self.search_cache(embedding)
```

### Team 3: Billing & Monetization
```python
# Your focus: Revenue capture
# Key files: app/services/billing/
# First task: Usage tracking

# Example starter code:
class UsageTracker:
    async def track_request(self, user_id: str, tokens: int, cost: float):
        await self.increment_usage(user_id, tokens, cost)
        await self.check_limits(user_id)
```

### Team 4: Data Pipeline
```sql
-- Your focus: Analytics at scale
-- Key files: app/services/telemetry/
-- First task: ClickHouse schema

CREATE TABLE llm_requests (
    timestamp DateTime,
    user_id String,
    tokens UInt32,
    cost Decimal(10,4)
) ENGINE = MergeTree()
ORDER BY (user_id, timestamp);
```

### Team 5: Frontend & Dashboard
```typescript
// Your focus: User conversion
// Key files: frontend/components/
// First task: Value metrics dashboard

export const ValueMetrics: React.FC = () => {
    const { savings } = useMetrics();
    return <MetricCard title="Your Savings" value={savings} />;
};
```

### Team 6: Infrastructure Optimization
```python
# Your focus: Infrastructure savings
# Key files: app/services/iac/
# First task: Waste detection

class WasteDetector:
    def analyze_utilization(self, metrics: CloudMetrics) -> List[Waste]:
        return self.find_underutilized_resources(metrics)
```

### Team 7: Validation Workbench
```python
# Your focus: Prove optimizations work
# Key files: app/services/validation/
# First task: Sandbox provisioning

class SandboxManager:
    async def provision(self) -> Sandbox:
        return await self.create_isolated_environment()
```

### Team 8: AI Agents
```python
# Your focus: Autonomous operations
# Key files: app/agents/
# First task: Enhanced supervisor

class EnhancedSupervisor:
    async def coordinate(self, task: Task):
        agents = self.select_agents(task)
        return await self.orchestrate(agents, task)
```

### Team 9: Testing & Quality
```python
# Your focus: 100% reliability
# Key files: app/tests/
# First task: E2E test framework

class E2ETestFramework:
    async def test_user_journey(self):
        await self.signup()
        await self.onboard()
        await self.upgrade()
```

### Team 10: DevOps & Platform
```yaml
# Your focus: Scale & reliability
# Key files: k8s/, terraform/
# First task: Auto-scaling config

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 3
  maxReplicas: 100
  targetCPUUtilizationPercentage: 70
```

---

## 6. Daily Workflow

### Morning Routine (9 AM)
```bash
# 1. Pull latest changes
git pull origin main

# 2. Check team tasks
python scripts/team_tasks.py --status

# 3. Join team standup (15 min)
# Slack: /standup
```

### Coding Flow
```bash
# 1. Create feature branch
git checkout -b team-X/feature

# 2. Code with compliance checks
python scripts/watch_compliance.py  # Runs in background

# 3. Test continuously
python test_runner.py --watch

# 4. Commit with BVJ
git commit -m "feat: [Feature] - BVJ: Saves X% of AI spend"
```

### Evening Routine (5 PM)
```bash
# 1. Run full test suite
python test_runner.py --level all

# 2. Create PR
gh pr create --title "Team X: [Feature]" --body "BVJ: [Impact]"

# 3. Update team board
python scripts/update_progress.py
```

---

## 7. Integration Points

### Your Team's Interfaces
Each team has specific integration points. Know yours:

```python
# Team 1 → Team 2: Request optimization
optimizer = OptimizationEngine()
optimized_request = await optimizer.optimize(request)

# Team 2 → Team 3: Track savings
billing = BillingService()
await billing.track_savings(user_id, amount)

# Team 3 → Team 5: Show metrics
metrics = await get_user_metrics(user_id)
return MetricsResponse(metrics)
```

---

## 8. Communication Channels

### Slack Channels
```
#general           - Company updates
#team-X            - Your team channel
#apex-dev          - Development discussion
#apex-integration  - Cross-team coordination
#apex-blockers     - Urgent issues
#apex-wins         - Celebrate successes
```

### Daily Meetings
```
9:00 AM  - Team standup (15 min)
9:30 AM  - Cross-team sync (Team leads only)
5:00 PM  - Integration testing (If needed)
Friday   - All-hands demo (30 min)
```

---

## 9. Getting Help

### Quick Help
```bash
# Get help on any topic
python scripts/apex_help.py --topic "semantic cache"

# Find code examples
python scripts/find_examples.py --pattern "optimization"

# Ask team lead
slack: /ask-lead [your question]
```

### Documentation
```
docs/API_DOCUMENTATION.md      - API specs
docs/ARCHITECTURE.md           - System design
SPEC/*.xml                     - Detailed specifications
CLAUDE.md                      - AI assistant instructions
```

### Escalation Path
1. Team member → Team channel
2. Team lead → Cross-team channel
3. Architect → Architecture channel
4. CTO → Direct message

---

## 10. Success Metrics

### Your Personal KPIs
- Code coverage: 100%
- Functions ≤8 lines: 100%
- Files ≤300 lines: 100%
- PR review time: <2 hours
- Bug rate: <1 per week

### Team KPIs
- Sprint velocity: 100 points/week
- Integration success: 95%
- Test pass rate: 100%
- Revenue impact: Track weekly

---

## First Day Checklist

### By End of Day 1
- [ ] Environment setup complete
- [ ] First PR submitted
- [ ] Tests passing
- [ ] Met team members
- [ ] Understood team interfaces
- [ ] Completed first task

### By End of Week 1
- [ ] 5+ PRs merged
- [ ] 100% test coverage on your code
- [ ] Integrated with another team
- [ ] Contributed to team documentation
- [ ] Identified optimization opportunity

---

## Pro Tips from the Architects

### Performance
```python
# ALWAYS use async/await for I/O
async def fetch_data():
    return await db.query()  # Good

def fetch_data():
    return db.query()  # Bad - blocks event loop
```

### Error Handling
```python
# Use NetraException for better error tracking
from netra_backend.app.core.exceptions import NetraException

raise NetraException(
    code="CACHE_MISS",
    message="Semantic cache miss",
    context={"prompt_hash": hash}
)
```

### Testing
```python
# Use fixtures for common test data
@pytest.fixture
def sample_request():
    return Request(
        prompt="Test prompt",
        model="gpt-4",
        user_id="test_user"
    )
```

---

## Remember: You're Building a Money Machine 💰

Every line of code should:
1. Save customer money on AI
2. Generate revenue for Apex
3. Be maintainable and scalable

**Your code directly impacts our $250K MRR target!**

---

## Quick Commands Reference

```bash
# Development
python dev_launcher.py              # Start all services
python test_runner.py               # Run tests
python scripts/check_compliance.py  # Check code standards

# Git
git checkout -b team-X/feature     # Create branch
git commit -m "feat: X - BVJ: Y"   # Commit with BVJ
gh pr create                        # Create PR

# Help
python scripts/apex_help.py         # Get help
python scripts/find_examples.py     # Find code examples
slack: /ask-lead                    # Ask team lead
```

---

**Welcome to the team! Let's build something incredible together.**

*Questions? Join #apex-onboarding*

---

*Quick Start Guide v1.0*
*Updated: 2025-08-17*
*Time to First Commit: 30 minutes*