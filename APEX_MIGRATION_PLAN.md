# NETRA APEX MIGRATION PLAN
## Integrating Revenue Systems with Existing Codebase

---

# MIGRATION OVERVIEW

**Principle**: Enhance, don't replace. The existing multi-agent architecture becomes the "brain" while the new Gateway becomes the "body" for revenue capture.

**Strategy**: Incremental migration with revenue features taking priority. Existing functionality continues to work while new revenue streams are added.

---

# EXISTING CODEBASE ANALYSIS

## Current Architecture Assets to Leverage

### 1. Multi-Agent System (KEEP & ENHANCE)
```
app/agents/
├── supervisor/              # ENHANCE: Add Gateway coordination
├── data_sub_agent/         # ENHANCE: Feed optimization decisions
├── corpus_admin/           # KEEP: Knowledge management
├── admin_tool_dispatcher/  # ENHANCE: Add billing tools
└── optimizations_core_sub_agent.py  # INTEGRATE: Core of Gateway logic
```

**Migration**: The agents become the intelligence layer for the Gateway

### 2. LLM Integration (WRAP WITH GATEWAY)
```
app/llm/
├── llm_core_operations.py  # WRAP: Gateway intercepts these calls
├── fallback_handler.py     # INTEGRATE: Into Gateway circuit breaker
└── enhanced_retry.py       # REUSE: In Gateway retry logic
```

**Migration**: Replace direct LLM calls with Gateway routing

### 3. Database Layer (EXTEND FOR BILLING)
```
app/db/
├── client_postgres.py      # EXTEND: Add billing tables
├── clickhouse.py          # REUSE: For telemetry ingestion
└── cache_core.py          # ENHANCE: Semantic caching layer
```

**Migration**: Add new schemas without breaking existing

### 4. Routes & APIs (ADD REVENUE ENDPOINTS)
```
app/routes/
├── agent_route.py         # KEEP: Internal agent coordination
├── unified_tools.py       # KEEP: Tool management
└── [NEW] gateway.py       # ADD: Gateway proxy endpoints
└── [NEW] billing.py       # ADD: Subscription management
```

---

# PHASE 1: REVENUE INFRASTRUCTURE (Week 1-2)

## Step 1.1: Add Gateway Module (Non-Breaking)

```python
# NEW: app/gateway/__init__.py
"""Gateway module - revenue capture layer"""

# NEW: app/gateway/proxy_core.py
from app.llm.llm_core_operations import LLMClient

class GatewayProxy:
    """Wraps existing LLM operations"""
    
    def __init__(self):
        self.llm_client = LLMClient()  # Reuse existing
        self.optimizer = OptimizationEngine()
        self.attributor = AttributionEngine()
    
    async def handle_request(self, request):
        # New optimization layer
        optimized = await self.optimizer.process(request)
        
        # Use existing LLM client
        response = await self.llm_client.execute(optimized)
        
        # New attribution layer
        savings = self.attributor.calculate(request, optimized)
        
        return self.format_response(response, savings)
```

## Step 1.2: Extend Database with Billing Tables

```python
# NEW: app/db/models_billing.py
from app.db.postgres_session import Base

class Customer(Base):
    __tablename__ = 'customers'
    # Extends existing user model with billing fields
    
class UsageRecord(Base):
    __tablename__ = 'usage_records'
    # New table for tracking usage

# Migration script
# alembic/versions/001_add_billing_tables.py
def upgrade():
    op.create_table('customers', ...)
    op.create_table('usage_records', ...)
    # Add billing fields to existing users table
    op.add_column('users', sa.Column('tier', ...))
    op.add_column('users', sa.Column('stripe_customer_id', ...))
```

## Step 1.3: Add Usage Tracking Middleware

```python
# NEW: app/middleware/usage_tracker.py
from app.middleware.middleware_base import BaseMiddleware

class UsageTrackingMiddleware(BaseMiddleware):
    """Tracks all API usage for billing"""
    
    async def dispatch(self, request, call_next):
        # Track before
        start_time = time.time()
        
        # Process request using existing middleware chain
        response = await call_next(request)
        
        # Track after
        await self.record_usage(
            user_id=request.state.user_id,
            endpoint=request.url.path,
            tokens=response.headers.get('x-tokens-used'),
            latency=time.time() - start_time
        )
        
        return response
```

---

# PHASE 2: INTEGRATE OPTIMIZATION (Week 3-4)

## Step 2.1: Enhance Existing Optimization Agent

```python
# MODIFY: app/agents/optimizations_core_sub_agent.py
class OptimizationsCore:
    """Existing optimization agent - enhance for Gateway"""
    
    # EXISTING CODE STAYS
    
    # ADD: New methods for Gateway integration
    async def optimize_for_gateway(self, request: GatewayRequest):
        """Gateway-specific optimization pipeline"""
        
        # Reuse existing optimization logic
        optimized = await self.optimize_request(request)
        
        # Add new revenue-focused optimizations
        if self.semantic_cache.check(request):
            return self.semantic_cache.get(request)
            
        # Route to cheaper model if possible
        if self.can_downgrade_model(request):
            optimized.model = self.select_cheaper_model(request)
            
        return optimized
```

## Step 2.2: Wrap Existing LLM Calls

```python
# MODIFY: app/llm/llm_core_operations.py
class LLMClient:
    """Existing LLM client - add Gateway mode"""
    
    def __init__(self, use_gateway: bool = False):
        self.use_gateway = use_gateway
        self.gateway = GatewayProxy() if use_gateway else None
        
    async def create_completion(self, **kwargs):
        if self.use_gateway:
            # Route through Gateway for revenue capture
            return await self.gateway.handle_request(kwargs)
        else:
            # Existing direct path (for internal use)
            return await self._direct_completion(**kwargs)
```

## Step 2.3: Add Caching to Existing Redis

```python
# MODIFY: app/db/cache_core.py
class CacheCore:
    """Existing cache - add semantic caching"""
    
    # EXISTING CODE STAYS
    
    # ADD: Semantic cache methods
    async def semantic_set(self, prompt: str, response: str, ttl: int = 3600):
        """Cache LLM responses by semantic similarity"""
        key = self.generate_semantic_key(prompt)
        await self.redis.setex(f"semantic:{key}", ttl, response)
        
    async def semantic_get(self, prompt: str) -> Optional[str]:
        """Retrieve cached response if semantically similar"""
        key = self.generate_semantic_key(prompt)
        return await self.redis.get(f"semantic:{key}")
```

---

# PHASE 3: PAYMENT INTEGRATION (Week 3-4)

## Step 3.1: Add Stripe Service

```python
# NEW: app/services/payment_service.py
import stripe
from app.auth.auth_service import AuthService

class PaymentService:
    """Payment processing - integrates with existing auth"""
    
    def __init__(self):
        self.auth = AuthService()  # Reuse existing
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
    async def create_checkout_session(self, user_id: str, tier: str):
        # Get user from existing auth system
        user = await self.auth.get_user(user_id)
        
        # Create Stripe session
        session = stripe.checkout.Session.create(
            customer_email=user.email,
            payment_method_types=['card'],
            line_items=[self.get_tier_price(tier)],
            mode='subscription',
            success_url=f"{settings.BASE_URL}/billing/success",
            cancel_url=f"{settings.BASE_URL}/billing/cancel"
        )
        
        return session
```

## Step 3.2: Extend Existing Auth with Tiers

```python
# MODIFY: app/auth/auth_dependencies.py
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Existing auth - add tier checking"""
    
    # EXISTING: Validate token and get user
    user = await validate_token(token)
    
    # NEW: Add tier information
    user.tier = await get_user_tier(user.id)
    user.usage_limits = TIER_LIMITS[user.tier]
    
    return user

# NEW: Tier enforcement decorator
def requires_tier(minimum_tier: str):
    def decorator(func):
        async def wrapper(*args, user: User = Depends(get_current_user), **kwargs):
            if not user_has_tier(user, minimum_tier):
                raise HTTPException(403, "Upgrade required")
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator
```

---

# PHASE 4: VALIDATION WORKBENCH (Week 5-6)

## Step 4.1: Leverage Existing Agents for Validation

```python
# NEW: app/validation/workbench.py
from app.agents.supervisor.agent_registry import AgentRegistry

class ValidationWorkbench:
    """Uses existing agents for infrastructure validation"""
    
    def __init__(self):
        self.registry = AgentRegistry()  # Reuse existing
        self.sandbox = SandboxManager()
        
    async def validate_terraform(self, config: str, workload: Workload):
        # Use existing agents to analyze config
        analysis = await self.registry.get_agent("corpus_admin").analyze(config)
        
        # Deploy to sandbox
        deployment = await self.sandbox.deploy(config)
        
        # Replay workload using existing data agent
        results = await self.registry.get_agent("data_sub_agent").replay(
            workload, 
            deployment.endpoint
        )
        
        return ValidationResult(
            baseline=workload.baseline_metrics,
            optimized=results.metrics,
            bvm_minutes=deployment.duration_minutes
        )
```

## Step 4.2: Extend MCP Client for Sandbox Control

```python
# MODIFY: app/mcp_client/client_core.py
class MCPClient:
    """Existing MCP client - add sandbox operations"""
    
    # EXISTING CODE STAYS
    
    # ADD: Sandbox management
    async def create_sandbox(self, customer_id: str) -> Sandbox:
        """Create isolated sandbox using MCP"""
        return await self.execute_tool(
            "create_sandbox",
            parameters={"customer_id": customer_id}
        )
        
    async def deploy_terraform(self, sandbox: Sandbox, config: str):
        """Deploy Terraform to sandbox"""
        return await self.execute_tool(
            "deploy_terraform",
            parameters={"sandbox_id": sandbox.id, "config": config}
        )
```

---

# MIGRATION EXECUTION PLAN

## Week 1-2: Foundation (No Breaking Changes)
- [ ] Add Gateway module alongside existing code
- [ ] Create billing database tables
- [ ] Add usage tracking middleware
- [ ] Deploy new endpoints without removing old ones

## Week 3-4: Integration & Testing
- [ ] Enable Gateway mode for 10% of traffic
- [ ] Test billing flow with test Stripe account  
- [ ] Verify usage tracking accuracy
- [ ] Add tier enforcement to new endpoints only

## Week 5-6: Validation & Expansion
- [ ] Launch validation workbench using existing agents
- [ ] Test BVM billing calculation
- [ ] Migrate 50% of traffic to Gateway

## Week 7-8: Full Migration
- [ ] Move 100% of customer traffic through Gateway
- [ ] Enable all revenue features
- [ ] Deprecate direct LLM endpoints
- [ ] Full production launch

---

# ROLLBACK PLAN

Each phase can be rolled back independently:

```python
# Feature flags for safe rollback
FEATURE_FLAGS = {
    "gateway_enabled": False,          # Start false, gradually true
    "billing_enabled": False,          # Enable after testing
    "usage_limits_enforced": False,    # Soft launch first
    "validation_workbench": False,     # Beta test first
}

# Traffic routing for gradual migration
TRAFFIC_ROUTING = {
    "gateway_percentage": 0,  # 0 -> 10 -> 50 -> 100
    "legacy_percentage": 100, # 100 -> 90 -> 50 -> 0
}
```

---

# EXISTING CODE TO PRESERVE

## Critical Components (DO NOT MODIFY)
```
app/agents/supervisor/          # Core agent orchestration
app/auth/auth_service.py       # Authentication logic
app/db/postgres_session.py     # Database connections
app/core/exceptions_file.py    # Error handling
SPEC/*.xml                      # Specification files
```

## Components to Enhance (BACKWARD COMPATIBLE)
```
app/llm/                        # Add Gateway mode
app/middleware/                 # Add usage tracking
app/routes/                     # Add new endpoints
app/services/                   # Add payment service
```

## Components to Deprecate (AFTER MIGRATION)
```
Direct LLM endpoints            # After Gateway proven
Unlimited free usage           # After billing active
Manual optimization            # After Gateway automatic
```

---

# TESTING STRATEGY

## Parallel Testing Approach

```python
# Test both paths to ensure compatibility

async def test_llm_compatibility():
    """Ensure Gateway and direct paths produce same results"""
    
    request = create_test_request()
    
    # Test existing direct path
    direct_response = await llm_client.create_completion(**request)
    
    # Test new Gateway path
    gateway_response = await gateway.handle_request(request)
    
    # Verify compatibility
    assert direct_response.content == gateway_response.content
    assert gateway_response.metadata.get('savings') >= 0
```

## Revenue Testing

```python
async def test_billing_integration():
    """Test billing without affecting production"""
    
    # Use test Stripe keys
    with stripe_test_mode():
        # Create test customer
        customer = await create_test_customer(tier="early")
        
        # Simulate usage
        await simulate_api_usage(customer, requests=100)
        
        # Verify billing
        invoice = await generate_invoice(customer)
        assert invoice.vbp_charges > 0
        assert invoice.total > 0
```

---

# TEAM COORDINATION

## Migration Responsibilities

### Existing Team Members
- Continue maintaining current functionality
- Review new code for compatibility
- Test existing features still work

### New Revenue Teams  
- Build Gateway and billing systems
- Ensure backward compatibility
- Create migration tools and scripts

### Joint Responsibilities
- Daily sync on migration progress
- Coordinate testing efforts
- Monitor production metrics

---

# SUCCESS CRITERIA

## Phase 1-2 Success (Week 4)
- [ ] Gateway handling 10% of traffic successfully
- [ ] No degradation in existing functionality
- [ ] First test payment processed
- [ ] Usage tracking accurate to 99%

## Phase 3-4 Success (Week 8)
- [ ] 100% traffic through Gateway
- [ ] $100K MRR achieved
- [ ] No increase in error rates
- [ ] All existing features still functional

---

**END OF MIGRATION PLAN**

**Key Principle**: Revenue first, but preserve what works. The existing codebase is the foundation; we're adding the revenue layer on top.