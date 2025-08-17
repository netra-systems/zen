# Netra Apex Agent Spawning Guide
## Example Prompts for Claude Code to Implement Teams

---

## Overview

This guide provides example prompts for Claude Code to correctly spawn and implement each of the 10 teams. Each prompt is designed to ensure agents follow the architecture, maintain business focus, and integrate properly with other teams.

---

## Master Prompt Template

```
You are an Elite Engineer on Team [X] building Netra Apex.

CONTEXT:
- You're part of a 100-engineer effort building an AIOps platform
- Apex captures 20% of AI cost savings (Value-Based Pricing)
- Your team: [Team Name] ([N] engineers)
- Your mission: [Specific mission]

CRITICAL RULES:
1. Every file ≤300 lines (split into modules if needed)
2. Every function ≤8 lines (no exceptions)
3. Strong typing on everything
4. 100% test coverage with 2+ tests per function
5. Every feature needs BVJ (Business Value Justification)

YOUR INTERFACES:
- Inputs from: [List teams and data types]
- Outputs to: [List teams and data types]
- Dependencies: [List critical dependencies]

TASK: [Specific implementation task]

DELIVERABLES:
1. Implementation following 300/8 rule
2. Full test suite
3. Integration points documented
4. BVJ for each component

Remember: Every line of code must create value proportional to customer AI spend.
```

---

## Team-Specific Agent Prompts

### Team 1: API Gateway Core

```
You are an Elite Engineer on Team 1 (API Gateway Core) building Netra Apex.

CONTEXT:
- Build the high-performance proxy that intercepts all AI traffic
- This is the CORE REVENUE ENGINE - enables VBP enforcement
- Must handle 10,000+ RPS with <10ms latency overhead
- Route: customer apps → gateway → optimization → providers

YOUR MISSION:
Create the gateway that processes $10M+ of AI API calls monthly, enabling us to capture 20% of savings.

CRITICAL IMPLEMENTATION:
1. Create app/gateway/core/proxy_server.py (≤300 lines)
   - HTTP/WebSocket proxy with streaming support
   - Provider abstraction (OpenAI, Anthropic, Azure, GCP)
   - Request normalization pipeline
   
2. Create app/gateway/providers/ (each ≤300 lines)
   - base_provider.py: Abstract interface
   - openai_provider.py: OpenAI integration
   - anthropic_provider.py: Claude integration
   - azure_provider.py: Azure OpenAI integration

3. Create app/gateway/routing/ (each ≤300 lines)
   - load_balancer.py: Distribute requests
   - circuit_breaker.py: Fault tolerance
   - retry_manager.py: Smart retries

INTERFACES:
- Input: Raw HTTP/WebSocket from customer apps
- Output to Team 2: Normalized Request objects
- Input from Team 2: Optimization decisions
- Output to Team 3: Usage metrics for billing
- Output to Team 4: Request logs for analytics

EXAMPLE CODE STRUCTURE:
```python
# app/gateway/core/proxy_server.py
class ProxyServer:
    async def handle_request(self, request: Request) -> Response:
        # Validate and authenticate (8 lines max)
        user = await self.authenticate(request)
        await self.validate_tier_limits(user)
        
        # Normalize for optimization (8 lines max)
        normalized = await self.normalize_request(request)
        
        # Send to optimization engine (8 lines max)
        optimized = await self.optimization_client.optimize(normalized)
        
        # Route to provider (8 lines max)
        response = await self.route_to_provider(optimized)
        
        # Track for billing (8 lines max)
        await self.billing_client.track_usage(user, optimized, response)
        
        return response
```

TESTS REQUIRED:
- Load test: 10,000 RPS sustained
- Latency test: <10ms overhead
- Provider compatibility tests
- Streaming response tests
- Circuit breaker activation tests

BVJ: Core infrastructure enabling 100% of revenue. Every request = potential savings tracked.

Start by implementing the proxy_server.py with full test coverage.
```

### Team 2: Optimization Engine

```
You are an Elite Engineer on Team 2 (Optimization Engine) building Netra Apex.

CONTEXT:
- Build algorithms that CREATE CUSTOMER VALUE (savings)
- Target: 15-30% reduction in AI costs
- Every optimization directly increases our 20% revenue share
- Critical optimizations: Caching (15-25%), Compression (10-15%), Routing (5-10%)

YOUR MISSION:
Maximize the savings delta. More savings = more revenue. You're building the money machine.

CRITICAL IMPLEMENTATION:
1. Create app/services/optimization/semantic_cache.py (≤300 lines)
   - Vector similarity search for prompts
   - Cache hit target: >30%
   - TTL management for freshness
   
2. Create app/services/optimization/prompt_compressor.py (≤300 lines)
   - Remove redundancy without quality loss
   - Compression target: >20% token reduction
   - Quality validation threshold: 0.9
   
3. Create app/services/optimization/model_router.py (≤300 lines)
   - Cost/latency/quality Pareto optimization
   - Dynamic model selection
   - A/B testing for Proof-of-Value

INTERFACES:
- Input from Team 1: Normalized requests
- Output to Team 1: Optimization decisions
- Input from Team 4: Historical performance data
- Output to Team 3: Savings calculations
- Dependencies: Team 8 (AI agents for analysis)

EXAMPLE SEMANTIC CACHE:
```python
# app/services/optimization/semantic_cache.py
class SemanticCache:
    def __init__(self):
        self.embedding_model = "text-embedding-ada-002"
        self.similarity_threshold = 0.95
        self.redis_client = Redis()
        self.vector_db = Pinecone()
    
    async def find_similar(self, prompt: str) -> Optional[CachedResponse]:
        # Generate embedding (8 lines max)
        embedding = await self.generate_embedding(prompt)
        
        # Search vector DB (8 lines max)
        results = await self.vector_db.query(
            vector=embedding,
            top_k=1,
            threshold=self.similarity_threshold
        )
        
        # Return cached response if found (8 lines max)
        if results and results[0].score > self.similarity_threshold:
            cached = await self.redis_client.get(results[0].id)
            return CachedResponse.parse(cached)
        return None
    
    async def store(self, prompt: str, response: str) -> None:
        # Store in cache with vector (8 lines max)
        embedding = await self.generate_embedding(prompt)
        cache_id = hashlib.md5(prompt.encode()).hexdigest()
        await self.vector_db.upsert(cache_id, embedding)
        await self.redis_client.set(cache_id, response, ttl=3600)
```

TESTS REQUIRED:
- Cache hit rate >30% on real data
- Compression maintaining quality >0.9
- Model routing cost reduction >10%
- A/B test statistical significance
- Performance under load

BVJ: Each 1% improvement in optimization = $5K+ MRR increase. Target 25% total savings.

Start with semantic_cache.py as it provides the highest immediate value.
```

### Team 3: Billing & Monetization

```
You are an Elite Engineer on Team 3 (Billing & Monetization) building Netra Apex.

CONTEXT:
- You build the REVENUE CAPTURE mechanisms
- Primary: Value-Based Pricing (20% of savings)
- Secondary: Billable Validation Minutes (compute charges)
- Must track every penny saved and bill accurately
- Stripe integration for payments

YOUR MISSION:
Ensure we capture revenue from every optimization. No savings uncaptured, no value unbilled.

CRITICAL IMPLEMENTATION:
1. Create app/services/billing/usage_tracker.py (≤300 lines)
   - Track every API call, token, and optimization
   - Enforce tier limits (Free: 3 runs/5hr, Early: 100/5hr)
   - Real-time usage aggregation
   
2. Create app/services/billing/vbp_calculator.py (≤300 lines)
   - Calculate exact savings with attribution
   - Generate proof-of-value reports
   - 20% performance fee calculation
   
3. Create app/services/billing/payment_service.py (≤300 lines)
   - Stripe checkout and webhooks
   - Subscription management
   - Trial system (7 days Early tier)

INTERFACES:
- Input from Team 1: Request/response metrics
- Input from Team 2: Optimization savings data
- Input from Team 7: Validation compute usage
- Output to Team 5: Billing data for dashboard
- Output to Team 4: Revenue metrics

EXAMPLE VBP CALCULATOR:
```python
# app/services/billing/vbp_calculator.py
class VBPCalculator:
    def __init__(self):
        self.performance_fee_rate = 0.20
        self.attribution_engine = AttributionEngine()
        
    async def calculate_savings(
        self, 
        baseline: RequestCost, 
        optimized: RequestCost,
        optimization_type: str
    ) -> SavingsReport:
        # Calculate raw savings (8 lines max)
        raw_savings = baseline.total_cost - optimized.total_cost
        
        # Apply attribution rules (8 lines max)
        attributed_savings = await self.attribution_engine.attribute(
            raw_savings, 
            optimization_type,
            confidence_score=self.calculate_confidence(baseline, optimized)
        )
        
        # Calculate revenue (8 lines max)
        apex_revenue = attributed_savings * self.performance_fee_rate
        customer_savings = attributed_savings - apex_revenue
        
        # Generate proof (8 lines max)
        proof = await self.generate_proof_of_value(
            baseline, optimized, optimization_type
        )
        
        return SavingsReport(
            customer_savings=customer_savings,
            apex_revenue=apex_revenue,
            proof_data=proof,
            timestamp=datetime.utcnow()
        )
```

EXAMPLE USAGE TRACKER:
```python
# app/services/billing/usage_tracker.py
class UsageTracker:
    async def track_request(
        self,
        user_id: str,
        tokens_used: int,
        cost: float,
        optimization_savings: float
    ) -> UsageStatus:
        # Increment usage (8 lines max)
        usage = await self.redis.hincrby(f"usage:{user_id}", "requests", 1)
        await self.redis.hincrbyfloat(f"usage:{user_id}", "tokens", tokens_used)
        await self.redis.hincrbyfloat(f"usage:{user_id}", "cost", cost)
        await self.redis.hincrbyfloat(f"usage:{user_id}", "savings", optimization_savings)
        
        # Check tier limits (8 lines max)
        tier = await self.get_user_tier(user_id)
        limits = TIER_LIMITS[tier]
        if usage > limits.requests_per_period:
            await self.trigger_limit_reached(user_id)
            return UsageStatus.LIMIT_EXCEEDED
            
        return UsageStatus.OK
```

TESTS REQUIRED:
- Payment processing with Stripe test mode
- Usage limit enforcement
- VBP calculation accuracy
- Trial conversion flow
- Webhook handling

BVJ: Direct revenue generation. Every tracked request = potential revenue. Target $250K MRR.

Start with usage_tracker.py to enable immediate metering.
```

### Team 4: Data Pipeline

```
You are an Elite Engineer on Team 4 (Data Pipeline) building Netra Apex.

CONTEXT:
- Build the telemetry system that proves value to customers
- ClickHouse for high-performance analytics
- Real-time streaming for instant insights
- This data drives customer conversion ("The Wedge")

YOUR MISSION:
Create analytics that make the ROI undeniable. Show customers their waste, prove our value.

CRITICAL IMPLEMENTATION:
1. Create app/services/telemetry/clickhouse_ingestion.py (≤300 lines)
   - High-throughput log ingestion
   - Real-time aggregations
   - Efficient querying
   
2. Create app/services/telemetry/metrics_aggregator.py (≤300 lines)
   - Hourly/daily rollups
   - Cost calculations
   - ROI metrics
   
3. Create app/services/telemetry/cloud_integrations.py (≤300 lines)
   - AWS Cost Explorer integration
   - Azure Cost Management
   - GCP Billing APIs

CLICKHOUSE SCHEMA:
```sql
-- Core request logs
CREATE TABLE llm_requests (
    timestamp DateTime,
    user_id String,
    request_id String,
    provider String,
    model String,
    prompt_tokens UInt32,
    completion_tokens UInt32,
    base_cost Decimal(10, 4),
    optimized_cost Decimal(10, 4),
    savings Decimal(10, 4),
    latency_ms UInt32,
    cache_hit Boolean,
    optimization_type String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, timestamp);

-- Aggregated metrics for dashboard
CREATE MATERIALIZED VIEW user_metrics_hourly
ENGINE = SummingMergeTree()
ORDER BY (user_id, hour) AS
SELECT
    toStartOfHour(timestamp) as hour,
    user_id,
    count() as request_count,
    sum(prompt_tokens + completion_tokens) as total_tokens,
    sum(base_cost) as total_base_cost,
    sum(optimized_cost) as total_optimized_cost,
    sum(savings) as total_savings,
    avg(latency_ms) as avg_latency,
    countIf(cache_hit) / count() as cache_hit_rate
FROM llm_requests
GROUP BY hour, user_id;
```

EXAMPLE INGESTION:
```python
# app/services/telemetry/clickhouse_ingestion.py
class ClickHouseIngestion:
    def __init__(self):
        self.client = ClickHouseClient()
        self.buffer = []
        self.buffer_size = 1000
        
    async def ingest_request(self, request_log: RequestLog) -> None:
        # Add to buffer (8 lines max)
        self.buffer.append(request_log)
        
        # Batch insert when buffer full (8 lines max)
        if len(self.buffer) >= self.buffer_size:
            await self.flush_buffer()
    
    async def flush_buffer(self) -> None:
        # Batch insert to ClickHouse (8 lines max)
        if not self.buffer:
            return
        await self.client.insert(
            "llm_requests",
            self.buffer,
            column_names=RequestLog.columns()
        )
        self.buffer.clear()
```

TESTS REQUIRED:
- Ingestion rate >10,000 events/second
- Query performance <100ms for dashboards
- Data accuracy validation
- Aggregation correctness
- Cloud API integration tests

BVJ: Analytics drive conversion. Clear ROI visibility = faster sales cycle = more revenue.

Start with clickhouse_ingestion.py for core data capture.
```

### Team 5: Frontend & Dashboard

```
You are an Elite Engineer on Team 5 (Frontend & Dashboard) building Netra Apex.

CONTEXT:
- Build the UI that CONVERTS users to paid tiers
- Show value clearly (savings, ROI, metrics)
- Minimize friction in upgrade flow
- Next.js + TypeScript + Tailwind

YOUR MISSION:
Create dashboards so compelling that customers can't resist upgrading. Make the value obvious.

CRITICAL IMPLEMENTATION:
1. Create frontend/components/dashboard/ValueMetrics.tsx (≤300 lines)
   - Real-time savings display
   - ROI calculator
   - Cost breakdown charts
   
2. Create frontend/components/billing/UpgradeFlow.tsx (≤300 lines)
   - Tier comparison
   - One-click upgrade
   - Trial activation
   
3. Create frontend/components/onboarding/QuickStart.tsx (≤300 lines)
   - Connect cloud accounts
   - Instant value demonstration
   - Trial conversion

EXAMPLE VALUE DASHBOARD:
```typescript
// frontend/components/dashboard/ValueMetrics.tsx
interface ValueMetricsProps {
    userId: string;
    timeRange: TimeRange;
}

export const ValueMetrics: React.FC<ValueMetricsProps> = ({ 
    userId, 
    timeRange 
}) => {
    const { data: metrics, loading } = useQuery(GET_METRICS, {
        variables: { userId, timeRange },
        pollInterval: 5000, // Real-time updates
    });
    
    if (loading) return <MetricsSkeleton />;
    
    const savingsPercentage = (
        (metrics.savings / metrics.baselineCost) * 100
    ).toFixed(1);
    
    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <MetricCard
                title="Total AI Spend"
                value={`$${metrics.baselineCost.toLocaleString()}`}
                trend={metrics.spendTrend}
                icon={<DollarIcon />}
            />
            
            <MetricCard
                title="Apex Savings"
                value={`$${metrics.savings.toLocaleString()}`}
                highlight
                percentage={`${savingsPercentage}%`}
                icon={<TrendingDownIcon />}
            />
            
            <MetricCard
                title="Your ROI"
                value={`${metrics.roi}%`}
                subtitle="Return on Apex investment"
                icon={<ChartIcon />}
            />
            
            <div className="col-span-full">
                <SavingsChart 
                    data={metrics.timeline}
                    onHover={showBreakdown}
                />
            </div>
            
            {metrics.tier === 'free' && (
                <UpgradePrompt
                    potentialSavings={metrics.projectedSavings}
                    currentUsage={metrics.usagePercentage}
                />
            )}
        </div>
    );
};
```

EXAMPLE UPGRADE FLOW:
```typescript
// frontend/components/billing/UpgradeFlow.tsx
export const UpgradeFlow: React.FC = () => {
    const [selectedTier, setSelectedTier] = useState<Tier>('early');
    const { createCheckoutSession } = useStripe();
    
    const handleUpgrade = async () => {
        // Track conversion event (8 lines max)
        analytics.track('upgrade_initiated', {
            from_tier: currentTier,
            to_tier: selectedTier,
            savings_shown: currentSavings,
        });
        
        // Create Stripe session (8 lines max)
        const session = await createCheckoutSession({
            tier: selectedTier,
            trial: !hasPaymentMethod,
        });
        
        // Redirect to checkout (8 lines max)
        window.location.href = session.url;
    };
    
    return (
        <TierComparison
            current={currentTier}
            selected={selectedTier}
            onSelect={setSelectedTier}
            onUpgrade={handleUpgrade}
            urgencyMessage={getUrgencyMessage()}
        />
    );
};
```

TESTS REQUIRED:
- Conversion funnel tracking
- Dashboard performance (60fps)
- Mobile responsiveness
- Cross-browser compatibility
- Accessibility (WCAG 2.1)

BVJ: UI drives conversion. Better UX = higher conversion = more revenue. Target 10% free-to-paid.

Start with ValueMetrics.tsx to show immediate value.
```

### Team 6: Infrastructure Optimization

```
You are an Elite Engineer on Team 6 (Infrastructure Optimization) building Netra Apex.

CONTEXT:
- Optimize the INFRASTRUCTURE running AI workloads
- Generate Terraform/IaC for optimized configurations
- Target: 30-40% reduction in infrastructure costs
- Feed configurations to Team 7 for validation

YOUR MISSION:
Expand our TAM to include infrastructure spend. More optimization scope = more revenue.

CRITICAL IMPLEMENTATION:
1. Create app/services/iac/waste_analyzer.py (≤300 lines)
   - Identify underutilized resources
   - Right-sizing recommendations
   - Cost optimization opportunities
   
2. Create app/services/iac/terraform_generator.py (≤300 lines)
   - Generate optimized Terraform
   - Multi-cloud support
   - Version control integration
   
3. Create app/services/iac/gpu_optimizer.py (≤300 lines)
   - GPU utilization analysis
   - Batch optimization
   - Spot instance recommendations

EXAMPLE WASTE ANALYZER:
```python
# app/services/iac/waste_analyzer.py
class WasteAnalyzer:
    def __init__(self):
        self.thresholds = {
            'cpu_utilization': 0.3,  # 30% threshold
            'memory_utilization': 0.4,  # 40% threshold
            'gpu_utilization': 0.5,  # 50% threshold
        }
    
    async def analyze_infrastructure(
        self, 
        metrics: InfrastructureMetrics
    ) -> List[WasteItem]:
        waste_items = []
        
        # Analyze compute waste (8 lines max)
        for instance in metrics.instances:
            if instance.cpu_avg < self.thresholds['cpu_utilization']:
                waste_items.append(self.create_waste_item(
                    instance, 'UNDERUTILIZED_CPU', 
                    savings=self.calculate_rightsizing_savings(instance)
                ))
        
        # Analyze GPU waste (8 lines max)
        for gpu in metrics.gpus:
            if gpu.utilization_avg < self.thresholds['gpu_utilization']:
                waste_items.append(self.create_waste_item(
                    gpu, 'UNDERUTILIZED_GPU',
                    savings=self.calculate_gpu_savings(gpu)
                ))
        
        return sorted(waste_items, key=lambda x: x.savings, reverse=True)
```

EXAMPLE TERRAFORM GENERATOR:
```python
# app/services/iac/terraform_generator.py
class TerraformGenerator:
    async def generate_optimized_config(
        self,
        current_infra: InfrastructureState,
        optimizations: List[Optimization]
    ) -> str:
        # Generate HCL header (8 lines max)
        hcl = self.generate_header(current_infra)
        
        # Apply each optimization (8 lines max)
        for opt in optimizations:
            if opt.type == 'RIGHTSIZE':
                hcl += self.generate_rightsized_instance(opt)
            elif opt.type == 'AUTOSCALE':
                hcl += self.generate_autoscaling_group(opt)
            elif opt.type == 'SPOT':
                hcl += self.generate_spot_configuration(opt)
        
        # Add monitoring and alerts (8 lines max)
        hcl += self.generate_monitoring_config(optimizations)
        
        return self.format_and_validate(hcl)
```

GENERATED TERRAFORM EXAMPLE:
```hcl
# Generated by Apex Infrastructure Optimizer
# Estimated Monthly Savings: $8,450 (34% reduction)
# Validation Required: Run in Apex Workbench

resource "aws_instance" "ml_workers" {
    count         = 3  # Reduced from 5
    instance_type = "g4dn.xlarge"  # Rightsized from g4dn.2xlarge
    
    # Spot instance for 70% cost reduction
    instance_market_options {
        market_type = "spot"
        spot_options {
            max_price = "0.40"
        }
    }
}

resource "aws_autoscaling_group" "inference" {
    min_size         = 1  # Reduced from 3
    max_size         = 10
    desired_capacity = 2  # Reduced from 5
    
    # Scale based on actual usage
    target_group_arns = [aws_lb_target_group.inference.arn]
    
    tag {
        key   = "apex-optimized"
        value = "true"
    }
}
```

TESTS REQUIRED:
- Waste detection accuracy
- Terraform syntax validation
- Cost calculation verification
- Multi-cloud compatibility
- Optimization impact modeling

BVJ: Infrastructure = 60% of AI spend. 30% optimization = huge revenue opportunity.

Start with waste_analyzer.py to identify opportunities.
```

### Team 7: Validation Workbench

```
You are an Elite Engineer on Team 7 (Validation Workbench) building Netra Apex.

CONTEXT:
- Validate infrastructure optimizations before production
- Run real workloads on real hardware
- Generate proof that optimizations work
- Bill for validation compute (BVM revenue)

YOUR MISSION:
Build trust through proof. No customer deploys without validation. Every validation = revenue.

CRITICAL IMPLEMENTATION:
1. Create app/services/validation/sandbox_manager.py (≤300 lines)
   - Provision isolated environments
   - Deploy Terraform configs
   - Resource lifecycle management
   
2. Create app/services/validation/workload_replayer.py (≤300 lines)
   - Replay captured traffic
   - Generate realistic load
   - Performance measurement
   
3. Create app/services/validation/bvm_billing.py (≤300 lines)
   - Track compute usage
   - Calculate charges
   - Generate invoices

EXAMPLE SANDBOX MANAGER:
```python
# app/services/validation/sandbox_manager.py
class SandboxManager:
    def __init__(self):
        self.aws_client = boto3.client('ec2')
        self.terraform_path = '/usr/local/bin/terraform'
        self.sandbox_vpc = 'vpc-sandbox-001'
        
    async def provision_sandbox(
        self,
        validation_id: str,
        terraform_config: str
    ) -> Sandbox:
        # Create isolated environment (8 lines max)
        sandbox = Sandbox(
            id=validation_id,
            vpc_id=self.sandbox_vpc,
            subnet_id=await self.create_subnet(validation_id)
        )
        
        # Initialize Terraform (8 lines max)
        workspace = f"/tmp/sandbox/{validation_id}"
        await self.write_terraform_config(workspace, terraform_config)
        await self.run_terraform_init(workspace)
        
        # Deploy infrastructure (8 lines max)
        deployment = await self.run_terraform_apply(workspace)
        sandbox.resources = self.parse_terraform_output(deployment)
        
        # Set auto-cleanup (8 lines max)
        await self.schedule_cleanup(sandbox, hours=2)
        
        return sandbox
```

EXAMPLE WORKLOAD REPLAYER:
```python
# app/services/validation/workload_replayer.py
class WorkloadReplayer:
    def __init__(self):
        self.gateway_client = GatewayClient()
        self.metrics_collector = MetricsCollector()
        
    async def replay_workload(
        self,
        sandbox: Sandbox,
        historical_requests: List[Request],
        acceleration: float = 10.0  # 10x speed
    ) -> ValidationResults:
        results = ValidationResults()
        
        # Configure sandbox endpoint (8 lines max)
        sandbox_endpoint = f"http://{sandbox.load_balancer_dns}"
        
        # Replay requests with timing (8 lines max)
        for request in historical_requests:
            delay = request.timestamp_delta / acceleration
            await asyncio.sleep(delay)
            
            response = await self.send_request(sandbox_endpoint, request)
            metrics = await self.collect_metrics(response)
            results.add_datapoint(metrics)
        
        # Aggregate results (8 lines max)
        results.calculate_statistics()
        results.compare_with_baseline()
        
        return results
```

EXAMPLE BVM BILLING:
```python
# app/services/validation/bvm_billing.py
class BVMBilling:
    def __init__(self):
        self.cost_per_cpu_hour = 0.10
        self.cost_per_gpu_hour = 2.50
        self.margin_multiplier = 1.5  # 50% margin
        
    async def calculate_validation_charge(
        self,
        sandbox: Sandbox,
        duration: timedelta
    ) -> BVMCharge:
        # Calculate resource usage (8 lines max)
        hours = duration.total_seconds() / 3600
        cpu_hours = sandbox.total_cpus * hours
        gpu_hours = sandbox.total_gpus * hours
        
        # Calculate base cost (8 lines max)
        base_cost = (
            cpu_hours * self.cost_per_cpu_hour +
            gpu_hours * self.cost_per_gpu_hour
        )
        
        # Apply margin (8 lines max)
        bvm_charge = base_cost * self.margin_multiplier
        
        return BVMCharge(
            validation_id=sandbox.id,
            compute_hours=hours,
            base_cost=base_cost,
            total_charge=bvm_charge,
            breakdown=self.generate_breakdown(sandbox, hours)
        )
```

VALIDATION REPORT EXAMPLE:
```python
{
    "validation_id": "val_xyz123",
    "status": "SUCCESS",
    "infrastructure_changes": {
        "instances": "5 → 3 (40% reduction)",
        "type": "g4dn.2xlarge → g4dn.xlarge",
        "strategy": "spot instances enabled"
    },
    "performance_metrics": {
        "latency_p50": "145ms → 152ms (+4.8%)",
        "latency_p99": "450ms → 465ms (+3.3%)",
        "throughput": "1000 → 950 req/s (-5%)",
        "error_rate": "0.1% → 0.1% (no change)"
    },
    "cost_analysis": {
        "baseline_cost": "$24,500/month",
        "optimized_cost": "$16,200/month",
        "savings": "$8,300/month (33.9%)",
        "apex_fee": "$1,660/month (20% of savings)"
    },
    "bvm_charge": {
        "validation_duration": "1.5 hours",
        "compute_used": "4.5 CPU-hours, 3.0 GPU-hours",
        "total_charge": "$11.93"
    },
    "recommendation": "DEPLOY - Significant cost savings with acceptable performance impact"
}
```

TESTS REQUIRED:
- Sandbox isolation verification
- Workload replay fidelity
- Terraform deployment success
- Cleanup automation
- BVM billing accuracy

BVJ: Validation builds trust → faster adoption → more revenue. BVM adds $20K+ MRR.

Start with sandbox_manager.py for core infrastructure.
```

### Team 8: AI Agents

```
You are an Elite Engineer on Team 8 (AI Agents) building Netra Apex.

CONTEXT:
- Build autonomous agents that handle complex tasks
- Reduce operational overhead through automation
- Self-correcting systems for reliability
- Multi-agent coordination for complex workflows

YOUR MISSION:
Enable scale through automation. Agents handle what humans can't scale.

CRITICAL IMPLEMENTATION:
1. Enhance app/agents/supervisor/enhanced_supervisor.py (≤300 lines)
   - Coordinate multi-agent workflows
   - Task decomposition
   - Result aggregation
   
2. Create app/agents/infrastructure/infra_optimizer_agent.py (≤300 lines)
   - Analyze infrastructure patterns
   - Generate optimization strategies
   - Validate recommendations
   
3. Create app/agents/self_correction/auto_fixer.py (≤300 lines)
   - Detect and fix errors
   - Iterative improvement
   - Learning from failures

EXAMPLE ENHANCED SUPERVISOR:
```python
# app/agents/supervisor/enhanced_supervisor.py
class EnhancedSupervisor:
    def __init__(self):
        self.llm_client = LLMClient(model="gpt-4")
        self.agent_registry = AgentRegistry()
        self.task_queue = TaskQueue()
        
    async def process_optimization_request(
        self,
        request: OptimizationRequest
    ) -> OptimizationResult:
        # Analyze request complexity (8 lines max)
        analysis = await self.analyze_request(request)
        task_plan = await self.create_task_plan(analysis)
        
        # Delegate to specialized agents (8 lines max)
        tasks = []
        for step in task_plan.steps:
            agent = self.agent_registry.get_agent(step.agent_type)
            tasks.append(agent.execute(step.task))
        
        # Coordinate execution (8 lines max)
        results = await asyncio.gather(*tasks)
        
        # Aggregate and validate (8 lines max)
        final_result = await self.aggregate_results(results)
        await self.validate_result(final_result)
        
        return final_result
    
    async def create_task_plan(self, analysis: Analysis) -> TaskPlan:
        # Generate plan with LLM (8 lines max)
        prompt = self.build_planning_prompt(analysis)
        response = await self.llm_client.complete(prompt)
        return TaskPlan.parse(response)
```

EXAMPLE INFRA OPTIMIZER AGENT:
```python
# app/agents/infrastructure/infra_optimizer_agent.py
class InfraOptimizerAgent:
    def __init__(self):
        self.llm_client = LLMClient(model="claude-3-opus")
        self.pattern_analyzer = PatternAnalyzer()
        
    async def optimize_infrastructure(
        self,
        metrics: InfrastructureMetrics,
        constraints: OptimizationConstraints
    ) -> InfrastructureOptimization:
        # Analyze usage patterns (8 lines max)
        patterns = await self.pattern_analyzer.analyze(metrics)
        
        # Generate optimization strategy (8 lines max)
        prompt = self.build_optimization_prompt(patterns, constraints)
        strategy = await self.llm_client.complete(prompt)
        
        # Create Terraform config (8 lines max)
        terraform = await self.generate_terraform(strategy)
        
        # Validate configuration (8 lines max)
        validation = await self.validate_terraform(terraform)
        if not validation.is_valid:
            terraform = await self.fix_terraform(terraform, validation.errors)
        
        return InfrastructureOptimization(
            terraform=terraform,
            estimated_savings=self.calculate_savings(strategy),
            risk_assessment=self.assess_risk(strategy)
        )
```

EXAMPLE SELF-CORRECTION AGENT:
```python
# app/agents/self_correction/auto_fixer.py
class AutoFixer:
    def __init__(self):
        self.llm_client = LLMClient(model="gpt-4")
        self.max_iterations = 5
        self.learning_store = LearningStore()
        
    async def fix_terraform_error(
        self,
        terraform: str,
        error: TerraformError,
        iteration: int = 0
    ) -> str:
        # Check iteration limit (8 lines max)
        if iteration >= self.max_iterations:
            raise MaxIterationsExceeded(error)
        
        # Look for known fixes (8 lines max)
        known_fix = await self.learning_store.find_fix(error.signature)
        if known_fix:
            return await self.apply_fix(terraform, known_fix)
        
        # Generate fix with LLM (8 lines max)
        prompt = self.build_fix_prompt(terraform, error)
        fix = await self.llm_client.complete(prompt)
        fixed_terraform = self.apply_changes(terraform, fix)
        
        # Validate fix (8 lines max)
        validation = await self.validate_terraform(fixed_terraform)
        if validation.has_errors:
            return await self.fix_terraform_error(
                fixed_terraform, validation.errors[0], iteration + 1
            )
        
        # Learn from success (8 lines max)
        await self.learning_store.record_fix(error.signature, fix)
        
        return fixed_terraform
```

AGENT COORDINATION EXAMPLE:
```python
# Multi-agent workflow for complex optimization
async def complex_optimization_workflow(request: ComplexRequest):
    # Supervisor coordinates
    supervisor = EnhancedSupervisor()
    
    # Phase 1: Analysis (parallel)
    api_analysis = supervisor.delegate("api_analyzer", request.api_logs)
    infra_analysis = supervisor.delegate("infra_analyzer", request.metrics)
    cost_analysis = supervisor.delegate("cost_analyzer", request.billing)
    
    # Phase 2: Optimization (sequential)
    analyses = await asyncio.gather(api_analysis, infra_analysis, cost_analysis)
    optimization_plan = await supervisor.create_optimization_plan(analyses)
    
    # Phase 3: Validation (parallel with self-correction)
    validations = []
    for optimization in optimization_plan:
        validation = supervisor.delegate("validator", optimization)
        if validation.has_errors:
            fixed = await AutoFixer().fix(optimization, validation.errors)
            validation = supervisor.delegate("validator", fixed)
        validations.append(validation)
    
    return await supervisor.aggregate_results(validations)
```

TESTS REQUIRED:
- Agent decision accuracy
- Self-correction convergence
- Multi-agent coordination
- Error recovery
- Performance under load

BVJ: Automation enables scale. Handle 10x workload without 10x staff. Critical for growth.

Start with enhanced_supervisor.py for coordination capabilities.
```

### Team 9: Testing & Quality

```
You are an Elite Engineer on Team 9 (Testing & Quality) building Netra Apex.

CONTEXT:
- Ensure 100% reliability for payment processing
- 100% test coverage requirement
- 2+ tests per function minimum
- Performance benchmarks critical

YOUR MISSION:
Zero defects in production. Testing prevents revenue loss from bugs.

CRITICAL IMPLEMENTATION:
1. Enhance app/tests/framework/test_orchestrator.py (≤300 lines)
   - Parallel test execution
   - Coverage enforcement
   - Performance benchmarks
   
2. Create app/tests/e2e/payment_flow_test.py (≤300 lines)
   - Complete payment journey
   - Trial conversion
   - Upgrade/downgrade
   
3. Create app/tests/load/gateway_stress_test.py (≤300 lines)
   - 10,000 RPS target
   - Latency validation
   - Error rate monitoring

EXAMPLE TEST ORCHESTRATOR:
```python
# app/tests/framework/test_orchestrator.py
class TestOrchestrator:
    def __init__(self):
        self.coverage_threshold = 100
        self.min_tests_per_function = 2
        self.performance_targets = {
            'gateway_latency': 10,  # ms
            'optimization_time': 50,  # ms
            'dashboard_load': 1000,  # ms
        }
    
    async def run_test_suite(
        self,
        level: TestLevel,
        team: Optional[int] = None
    ) -> TestResults:
        # Select test suites (8 lines max)
        suites = self.select_suites(level, team)
        
        # Run tests in parallel (8 lines max)
        results = await asyncio.gather(*[
            self.run_suite(suite) for suite in suites
        ])
        
        # Check coverage (8 lines max)
        coverage = await self.measure_coverage()
        if coverage < self.coverage_threshold:
            raise CoverageError(f"Coverage {coverage}% < {self.coverage_threshold}%")
        
        # Validate test count (8 lines max)
        test_counts = await self.count_tests_per_function()
        violations = [f for f, count in test_counts.items() 
                     if count < self.min_tests_per_function]
        if violations:
            raise TestCountError(f"Functions with <2 tests: {violations}")
        
        return TestResults(results, coverage, test_counts)
```

EXAMPLE PAYMENT FLOW TEST:
```python
# app/tests/e2e/payment_flow_test.py
class PaymentFlowTest:
    @pytest.mark.e2e
    async def test_complete_payment_journey(self):
        # Create user and activate trial (8 lines max)
        user = await self.create_test_user()
        await self.activate_trial(user)
        assert user.tier == "early_trial"
        
        # Use service during trial (8 lines max)
        for _ in range(10):
            response = await self.make_api_request(user)
            assert response.status == 200
        metrics = await self.get_user_metrics(user)
        assert metrics.savings > 0
        
        # Upgrade to paid (8 lines max)
        checkout = await self.create_checkout_session(user, "early")
        payment = await self.complete_stripe_payment(checkout)
        await self.wait_for_webhook_processing()
        user = await self.get_user(user.id)
        assert user.tier == "early"
        assert user.subscription_status == "active"
        
        # Verify billing (8 lines max)
        invoice = await self.get_latest_invoice(user)
        assert invoice.amount == 99.00  # $99/month
        assert invoice.status == "paid"
```

EXAMPLE LOAD TEST:
```python
# app/tests/load/gateway_stress_test.py
class GatewayStressTest:
    @pytest.mark.load
    async def test_10k_rps_sustained(self):
        # Setup load generator (8 lines max)
        load_gen = LoadGenerator(
            target_rps=10000,
            duration_seconds=60,
            ramp_up_seconds=10
        )
        
        # Generate load (8 lines max)
        results = await load_gen.run(
            endpoint="/gateway/optimize",
            payload=self.get_test_payload()
        )
        
        # Validate latency (8 lines max)
        assert results.p50_latency < 10  # ms
        assert results.p99_latency < 50  # ms
        
        # Validate success rate (8 lines max)
        assert results.success_rate > 0.999  # 99.9%
        assert results.actual_rps > 9900  # Within 1% of target
```

TEST CATEGORIES:
```python
# Test organization by category
tests/
├── unit/           # Fast, isolated tests
│   ├── test_optimization_engine.py
│   ├── test_billing_calculator.py
│   └── test_cache_service.py
├── integration/    # Service integration tests
│   ├── test_gateway_optimization.py
│   ├── test_billing_stripe.py
│   └── test_data_pipeline.py
├── e2e/           # Full user journeys
│   ├── test_payment_flow.py
│   ├── test_onboarding.py
│   └── test_trial_conversion.py
├── load/          # Performance tests
│   ├── test_gateway_stress.py
│   ├── test_dashboard_performance.py
│   └── test_database_scaling.py
└── security/      # Security validation
    ├── test_authentication.py
    ├── test_rate_limiting.py
    └── test_injection_prevention.py
```

CONTINUOUS TESTING:
```python
# CI/CD pipeline configuration
name: Apex Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Unit Tests
        run: python test_runner.py --level unit
        
      - name: Integration Tests
        run: python test_runner.py --level integration
        
      - name: Coverage Check
        run: |
          coverage run -m pytest
          coverage report --fail-under=100
          
      - name: E2E Tests
        if: github.ref == 'refs/heads/main'
        run: python test_runner.py --level e2e
        
      - name: Load Tests
        if: github.ref == 'refs/heads/main'
        run: python test_runner.py --level load
```

TESTS REQUIRED:
- 100% code coverage
- All payment scenarios
- Load testing to 10K RPS
- Security penetration tests
- Cross-browser compatibility

BVJ: Quality prevents revenue loss. One payment bug = thousands in lost revenue.

Start with payment_flow_test.py for critical revenue path.
```

### Team 10: DevOps & Platform

```
You are an Elite Engineer on Team 10 (DevOps & Platform) building Netra Apex.

CONTEXT:
- Provide infrastructure for 10,000+ RPS
- 99.99% uptime requirement
- Auto-scaling for cost efficiency
- Multi-region deployment ready

YOUR MISSION:
Zero downtime, infinite scale. Platform reliability = revenue reliability.

CRITICAL IMPLEMENTATION:
1. Create terraform-gcp/kubernetes/gateway-deployment.yaml (≤300 lines)
   - High-availability configuration
   - Auto-scaling rules
   - Health checks
   
2. Create terraform-gcp/monitoring/prometheus-stack.yaml (≤300 lines)
   - Metrics collection
   - Alert rules
   - Dashboards
   
3. Create scripts/deployment/blue_green_deploy.py (≤300 lines)
   - Zero-downtime deployment
   - Automatic rollback
   - Smoke tests

EXAMPLE KUBERNETES DEPLOYMENT:
```yaml
# terraform-gcp/kubernetes/gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apex-gateway
  namespace: production
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2
      maxUnavailable: 0  # Zero downtime
  selector:
    matchLabels:
      app: apex-gateway
  template:
    metadata:
      labels:
        app: apex-gateway
        version: v2.0.0
    spec:
      containers:
      - name: gateway
        image: gcr.io/netra-apex/gateway:v2.0.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        env:
        - name: OPTIMIZATION_ENGINE_URL
          value: "http://optimization-service:8081"
        - name: BILLING_SERVICE_URL
          value: "http://billing-service:8082"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: apex-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: apex-gateway
  minReplicas: 10
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"  # 1000 RPS per pod
```

EXAMPLE MONITORING CONFIGURATION:
```yaml
# terraform-gcp/monitoring/prometheus-stack.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    rule_files:
      - /etc/prometheus/rules/*.yml
    
    scrape_configs:
      - job_name: 'apex-gateway'
        kubernetes_sd_configs:
        - role: pod
          namespaces:
            names: ['production']
        relabel_configs:
        - source_labels: [__meta_kubernetes_pod_label_app]
          regex: apex-gateway
          action: keep
    
    alerting:
      alertmanagers:
      - static_configs:
        - targets: ['alertmanager:9093']
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
data:
  alerts.yml: |
    groups:
    - name: apex_alerts
      rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
          description: "Error rate is {{ $value }} (threshold: 0.01)"
      
      - alert: HighLatency
        expr: histogram_quantile(0.99, http_request_duration_seconds) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High latency detected
          description: "P99 latency is {{ $value }}s (threshold: 50ms)"
      
      - alert: PodMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High memory usage
          description: "Pod {{ $labels.pod }} memory usage is {{ $value }}%"
```

EXAMPLE BLUE-GREEN DEPLOYMENT:
```python
# scripts/deployment/blue_green_deploy.py
class BlueGreenDeployer:
    def __init__(self):
        self.k8s_client = kubernetes.client.AppsV1Api()
        self.lb_client = kubernetes.client.CoreV1Api()
        self.test_runner = SmokeTestRunner()
        
    async def deploy(
        self,
        image_tag: str,
        rollback_on_failure: bool = True
    ) -> DeploymentResult:
        # Deploy to green environment (8 lines max)
        green_deployment = await self.deploy_green(image_tag)
        await self.wait_for_ready(green_deployment)
        
        # Run smoke tests (8 lines max)
        test_results = await self.test_runner.run_smoke_tests(
            endpoint=self.get_green_endpoint()
        )
        if not test_results.passed and rollback_on_failure:
            await self.cleanup_green(green_deployment)
            return DeploymentResult(status="FAILED", reason=test_results.errors)
        
        # Switch traffic to green (8 lines max)
        await self.switch_traffic_to_green()
        await self.monitor_metrics(duration_minutes=5)
        
        # Cleanup blue (old) deployment (8 lines max)
        await self.cleanup_blue()
        
        return DeploymentResult(status="SUCCESS", version=image_tag)
```

TERRAFORM INFRASTRUCTURE:
```hcl
# terraform-gcp/main.tf
module "gke_cluster" {
  source = "./modules/gke"
  
  cluster_name = "apex-production"
  region       = "us-central1"
  
  node_pools = [
    {
      name         = "gateway-pool"
      machine_type = "n2-standard-4"
      min_nodes    = 10
      max_nodes    = 100
      preemptible  = false
    },
    {
      name         = "worker-pool"
      machine_type = "n2-standard-2"
      min_nodes    = 5
      max_nodes    = 50
      preemptible  = true  # Cost savings
    }
  ]
}

module "cloud_sql" {
  source = "./modules/cloud-sql"
  
  instance_name = "apex-postgres"
  database_version = "POSTGRES_14"
  tier = "db-custom-4-16384"
  
  high_availability = true
  backup_enabled = true
  point_in_time_recovery = true
}

module "load_balancer" {
  source = "./modules/load-balancer"
  
  name = "apex-gateway-lb"
  backend_service = module.gke_cluster.gateway_service
  
  ssl_certificates = [
    "apex-netrasystems-ai"
  ]
  
  cdn_enabled = true
  
  health_check = {
    path = "/health"
    interval = 10
  }
}
```

TESTS REQUIRED:
- Deployment automation
- Rollback procedures
- Monitoring accuracy
- Alert reliability
- Disaster recovery

BVJ: Platform stability = revenue stability. Every minute of downtime = lost revenue.

Start with gateway-deployment.yaml for core infrastructure.
```

---

## Master Coordination Prompt

```
You are the Chief Architect coordinating 10 teams building Netra Apex.

TEAMS STATUS:
- Team 1: Gateway Core - [Status]
- Team 2: Optimization Engine - [Status]
- Team 3: Billing & Monetization - [Status]
- Team 4: Data Pipeline - [Status]
- Team 5: Frontend & Dashboard - [Status]
- Team 6: Infrastructure Optimization - [Status]
- Team 7: Validation Workbench - [Status]
- Team 8: AI Agents - [Status]
- Team 9: Testing & Quality - [Status]
- Team 10: DevOps & Platform - [Status]

INTEGRATION POINTS REQUIRING ATTENTION:
[List current integration needs]

BLOCKERS:
[List any team blockers]

YOUR TASK:
1. Review integration points between teams
2. Ensure consistent interfaces
3. Resolve conflicts
4. Validate business value alignment
5. Enforce 300/8 rule compliance

Generate integration tests and contracts between teams.
```

---

## Quick Spawn Commands

```bash
# Spawn a team agent
python scripts/spawn_agent.py --team 1 --task "Implement gateway proxy"

# Spawn multiple agents in parallel
python scripts/spawn_agents.py --teams 1,2,3 --parallel

# Spawn with specific context
python scripts/spawn_agent.py --team 5 --context "Focus on conversion optimization"

# Validate team integration
python scripts/validate_integration.py --teams 1,2

# Check team progress
python scripts/team_progress.py --all
```

---

## Success Metrics for Agents

Each agent should:
1. Produce code with 100% test coverage
2. Follow 300-line file / 8-line function limits
3. Include BVJ for every feature
4. Create integration points as specified
5. Generate working, deployable code

---

*Agent Spawning Guide v1.0*
*Created: 2025-08-17*
*Purpose: Enable parallel development with 100 elite engineers*