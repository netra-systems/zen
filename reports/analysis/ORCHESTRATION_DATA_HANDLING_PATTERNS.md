# Orchestration Agent Data Handling Patterns

## Executive Summary

This document provides comprehensive patterns and examples for handling partial and insufficient data scenarios in system orchestration agent prompts. These patterns ensure graceful degradation, progressive value delivery, and optimal user engagement when data is incomplete.

## Cross-References

### Critical Documentation
- **🆕 UVS Architecture**: [`docs/UVS_TRIAGE_ARCHITECTURE_TRANSITION.md`](docs/UVS_TRIAGE_ARCHITECTURE_TRANSITION.md) - **NEW: Unified Validation System with data sufficiency states**
- **Learnings Entry**: [`SPEC/learnings/orchestration_data_handling_patterns_20250904.xml`](SPEC/learnings/orchestration_data_handling_patterns_20250904.xml)
- **🚨 Agent Execution Order Fix**: [`SPEC/learnings/agent_execution_order_fix_20250904.xml`](SPEC/learnings/agent_execution_order_fix_20250904.xml) - **CRITICAL: Data MUST be collected BEFORE optimization**
- **Execution Order Reasoning**: [`AGENT_EXECUTION_ORDER_REASONING.md`](AGENT_EXECUTION_ORDER_REASONING.md) - Why order matters for business value

### Architecture & Implementation
- **Agent Architecture**: [`docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md`](docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md) - Complete agent architecture patterns (Section 6: Workflow Execution Order)
- **Golden Patterns**: [`docs/GOLDEN_AGENT_INDEX.md`](docs/GOLDEN_AGENT_INDEX.md) - Definitive guide with correct execution order
- **Workflow Orchestrator**: [`netra_backend/app/agents/supervisor/workflow_orchestrator.py`](netra_backend/app/agents/supervisor/workflow_orchestrator.py) - Implementation
- **Supervisor Adaptive Workflow**: [`SPEC/supervisor_adaptive_workflow.xml`](SPEC/supervisor_adaptive_workflow.xml) - Workflow specifications

### Business Value & Requirements
- **Business Value Spec**: [`SPEC/app_business_value.xml`](SPEC/app_business_value.xml) - Test case BV-003: Multi-Agent Workflow Execution
- **Main Project Doc**: [`CLAUDE.md`](CLAUDE.md) - Section 6: WebSocket Agent Events & Implementation Patterns
- **Learnings Index**: [`SPEC/learnings/index.xml`](SPEC/learnings/index.xml) - All critical learnings

### Infrastructure
- **User Context**: [`USER_CONTEXT_ARCHITECTURE.md`](USER_CONTEXT_ARCHITECTURE.md) - Factory-based isolation patterns for request handling
- **WebSocket Events**: [`SPEC/learnings/websocket_agent_integration_critical.xml`](SPEC/learnings/websocket_agent_integration_critical.xml) - Required events for chat value delivery
- **Sequential Execution**: [`SPEC/learnings/workflow_sequential_execution.xml`](SPEC/learnings/workflow_sequential_execution.xml) - Enforcement mechanisms

## Core Principles

1. **Data Before Optimization**: ⚠️ **CRITICAL** - Data collection MUST precede optimization analysis (see [execution order fix](SPEC/learnings/agent_execution_order_fix_20250904.xml))
2. **Progressive Value Delivery**: Always provide immediate value with available data
3. **Transparent Communication**: Clearly indicate confidence levels and data gaps
4. **Actionable Guidance**: Provide specific instructions for data collection
5. **Graceful Degradation**: Never fail completely; always provide something useful

### Execution Order Requirement
**The fundamental rule**: You cannot optimize what you haven't measured. The agent workflow MUST follow:
```
Triage → Data → Optimization → Actions → Reporting
```
Any deviation from this order results in optimization strategies based on assumptions rather than data, destroying business value.

## Data Sufficiency Levels

> **📌 NOTE**: These levels align with the UVS (Unified Validation System) data sufficiency states.  
> See [UVS Triage Architecture](docs/UVS_TRIAGE_ARCHITECTURE_TRANSITION.md) for implementation details.

### 1. Sufficient Data (80-100% Complete) - UVS "OPTIMAL" State
- Full optimization possible
- High confidence recommendations
- Precise metrics and projections

### 2. Partial Data (40-79% Complete)
- Modified workflow with caveats
- Medium confidence recommendations
- Range-based projections

### 3. Insufficient Data (<40% Complete)
- Data collection focused workflow
- Educational content delivery
- Value proposition demonstration

---

## 20 Real-World Examples and Handling Patterns

### Example 1: Cost Optimization with Partial Metrics

**User Input:**
```json
{
  "request": "My LLM costs are around $5K monthly",
  "available_data": ["monthly_spend_estimate", "primary_use_case"],
  "missing_data": ["token_usage", "model_distribution", "latency_requirements"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "modified_optimization",
  "confidence": 0.65,
  "immediate_recommendations": [
    {
      "action": "Implement basic model routing",
      "caveat": "Exact savings depend on token distribution",
      "estimated_range": "$800-1500/month"
    }
  ],
  "data_request": {
    "priority": "medium",
    "items": ["7-day token usage report", "Model breakdown by request type"]
  }
}
```

### Example 2: Performance Tuning with Missing Baselines

**User Input:**
```json
{
  "request": "Our AI responses feel slow",
  "available_data": ["subjective_performance_issue"],
  "missing_data": ["current_latency_metrics", "SLA_requirements", "request_patterns"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "diagnostic_first",
  "confidence": 0.30,
  "immediate_actions": [
    {
      "action": "Deploy monitoring script",
      "purpose": "Establish baseline metrics",
      "timeline": "24-48 hours"
    }
  ],
  "educational_content": {
    "typical_latencies": "GPT-4: 2-5s, GPT-3.5: 0.5-2s",
    "optimization_potential": "Usually 30-50% improvement possible"
  }
}
```

### Example 3: Vague Optimization Request

**User Input:**
```json
{
  "request": "Help optimize",
  "available_data": [],
  "missing_data": ["domain", "metrics", "goals", "constraints"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "clarification_required",
  "confidence": 0.05,
  "clarification_request": {
    "message": "I can help optimize several areas. Which is your priority?",
    "options": [
      "AI/LLM cost optimization (Save 30-70% on AI spend)",
      "Performance optimization (Reduce latency by 40-60%)",
      "Scale optimization (Handle 10x more requests)"
    ]
  },
  "quick_assessment": {
    "template": "Current Challenge: ___, Monthly Budget: ___, Primary Goal: ___"
  }
}
```

### Example 4: Partial Usage Pattern Data

**User Input:**
```json
{
  "request": "We use GPT-4 for customer support, spending too much",
  "available_data": ["use_case", "model", "cost_concern"],
  "missing_data": ["request_volume", "complexity_distribution", "quality_requirements"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "phased_optimization",
  "confidence": 0.70,
  "phase_1": {
    "actions": [
      "Implement request classifier",
      "Route simple queries to GPT-3.5"
    ],
    "expected_impact": "20-30% cost reduction",
    "timeline": "3-5 days"
  },
  "phase_2": {
    "dependency": "1 week of classification data",
    "potential": "Additional 30-40% savings"
  }
}
```

### Example 5: Infrastructure Unknown

**User Input:**
```json
{
  "request": "Our AI pipeline needs optimization",
  "available_data": ["optimization_need"],
  "missing_data": ["tech_stack", "deployment_model", "scale", "bottlenecks"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "discovery_driven",
  "confidence": 0.25,
  "discovery_checklist": [
    {
      "area": "Infrastructure",
      "questions": ["Cloud provider?", "Container orchestration?", "Current scale?"],
      "why": "Determines optimization strategies"
    },
    {
      "area": "Pipeline",
      "questions": ["Batch vs real-time?", "Data preprocessing?", "Model serving?"],
      "why": "Identifies bottlenecks"
    }
  ],
  "universal_quick_wins": [
    "Enable request batching (20-40% improvement)",
    "Implement caching layer (30-50% reduction)"
  ]
}
```

### Example 6: Compliance Constraints Unknown

**User Input:**
```json
{
  "request": "Reduce AI costs for our healthcare app",
  "available_data": ["domain", "cost_concern"],
  "missing_data": ["compliance_requirements", "data_residency", "audit_needs"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "compliance_aware",
  "confidence": 0.55,
  "critical_questions": [
    {
      "question": "HIPAA compliance required?",
      "impact": "Limits model and deployment options"
    },
    {
      "question": "Data residency requirements?",
      "impact": "Affects cloud provider selection"
    }
  ],
  "safe_recommendations": [
    "Optimize prompt engineering (15-25% token reduction)",
    "Implement smart caching for non-PHI data"
  ]
}
```

### Example 7: Seasonal Patterns Unknown

**User Input:**
```json
{
  "request": "AI costs spike randomly, need consistency",
  "available_data": ["cost_variability_issue"],
  "missing_data": ["usage_timeline", "peak_patterns", "trigger_events"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "pattern_analysis_first",
  "confidence": 0.45,
  "data_collection": {
    "required_period": "30-60 days",
    "metrics": ["Hourly request counts", "Daily token usage", "Peak event correlation"]
  },
  "immediate_mitigations": [
    "Implement rate limiting",
    "Set up cost alerts",
    "Create usage dashboard"
  ]
}
```

### Example 8: Multi-Model Environment Partial Data

**User Input:**
```json
{
  "request": "We use OpenAI, Anthropic, and Cohere - optimize costs",
  "available_data": ["model_providers", "cost_concern"],
  "missing_data": ["usage_per_provider", "use_case_mapping", "performance_requirements"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "multi_model_optimization",
  "confidence": 0.60,
  "immediate_strategy": {
    "approach": "Model arbitrage",
    "implementation": "Route by cost-performance ratio",
    "expected_savings": "25-40%"
  },
  "optimization_matrix_request": {
    "template": "Model: ___, Use Case: ___, Monthly Cost: ___, Critical?: Y/N"
  }
}
```

### Example 9: Error Rates Without Context

**User Input:**
```json
{
  "request": "Getting too many AI errors",
  "available_data": ["error_issue"],
  "missing_data": ["error_types", "frequency", "patterns", "impact"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "diagnostic_triage",
  "confidence": 0.20,
  "error_categorization": {
    "common_causes": [
      "Rate limits (429 errors)",
      "Token limits (context too long)",
      "Timeout errors (slow responses)",
      "API errors (service issues)"
    ],
    "diagnostic_script": "provided_error_analyzer.py"
  },
  "immediate_safeguards": [
    "Implement exponential backoff",
    "Add retry logic",
    "Create fallback responses"
  ]
}
```

### Example 10: Budget Without Usage Details

**User Input:**
```json
{
  "request": "Have $10K monthly budget for AI, currently over",
  "available_data": ["budget_limit", "overspend_issue"],
  "missing_data": ["current_spend", "usage_breakdown", "priority_features"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "budget_driven_optimization",
  "confidence": 0.50,
  "budget_allocation": {
    "recommended_split": {
      "critical_features": "60% ($6K)",
      "standard_features": "30% ($3K)",
      "experimental": "10% ($1K)"
    }
  },
  "spend_audit_request": {
    "urgency": "high",
    "needed": ["Last 3 months invoices", "Feature-to-cost mapping"]
  }
}
```

### Example 11: Scale Requirements Unknown

**User Input:**
```json
{
  "request": "Need to optimize for growth",
  "available_data": ["growth_intention"],
  "missing_data": ["current_scale", "growth_projections", "bottlenecks"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "scalability_assessment",
  "confidence": 0.35,
  "scale_questionnaire": {
    "current_state": "Requests/day: ___, Peak concurrent: ___, P99 latency: ___",
    "growth_target": "Expected in 6 months: ___, 1 year: ___"
  },
  "scale_ready_patterns": [
    "Implement request queuing",
    "Design for horizontal scaling",
    "Add circuit breakers"
  ]
}
```

### Example 12: Integration Complexity Unknown

**User Input:**
```json
{
  "request": "Want to optimize our AI integrations",
  "available_data": ["integration_optimization_need"],
  "missing_data": ["integration_points", "data_flow", "dependencies"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "integration_mapping",
  "confidence": 0.30,
  "integration_audit": {
    "map_template": {
      "source": "___",
      "destination": "___",
      "data_volume": "___",
      "frequency": "___",
      "criticality": "___"
    }
  },
  "common_optimizations": [
    "Batch API calls (40-60% reduction)",
    "Implement webhook patterns",
    "Add integration caching"
  ]
}
```

### Example 13: Quality Requirements Undefined

**User Input:**
```json
{
  "request": "Reduce costs but maintain quality",
  "available_data": ["cost_concern", "quality_concern"],
  "missing_data": ["quality_metrics", "acceptable_tradeoffs", "user_expectations"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "quality_preserving_optimization",
  "confidence": 0.55,
  "quality_framework": {
    "define_metrics": ["Accuracy threshold: ___", "User satisfaction: ___", "Response coherence: ___"],
    "test_approach": "A/B testing with gradual rollout"
  },
  "safe_optimizations": [
    "Optimize prompts (maintain quality, reduce tokens)",
    "Selective model downgrade for non-critical paths"
  ]
}
```

### Example 14: Team Capabilities Unknown

**User Input:**
```json
{
  "request": "Help us implement AI optimizations",
  "available_data": ["implementation_request"],
  "missing_data": ["team_size", "technical_expertise", "available_time"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "capability_matched_planning",
  "confidence": 0.40,
  "team_assessment": {
    "questions": [
      "Team size and roles?",
      "Python/API experience level?",
      "Available hours per week?"
    ]
  },
  "implementation_tiers": {
    "low_complexity": "Config changes only (1-2 days)",
    "medium_complexity": "API integration (1-2 weeks)",
    "high_complexity": "Full pipeline redesign (1-2 months)"
  }
}
```

### Example 15: Historical Data Unavailable

**User Input:**
```json
{
  "request": "New to AI, need cost optimization from start",
  "available_data": ["new_implementation"],
  "missing_data": ["baseline_metrics", "usage_patterns", "growth_trajectory"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "greenfield_optimization",
  "confidence": 0.70,
  "best_practices": {
    "start_with": [
      "Implement usage tracking from day 1",
      "Use tiered model strategy",
      "Set up cost alerts early"
    ]
  },
  "reference_benchmarks": {
    "typical_costs": "Per 1K users: $500-2000/month",
    "optimization_potential": "50-70% with proper setup"
  }
}
```

### Example 16: Partial Performance Metrics

**User Input:**
```json
{
  "request": "P95 latency is 3s, need faster",
  "available_data": ["p95_latency"],
  "missing_data": ["full_latency_distribution", "request_types", "infrastructure_details"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "performance_optimization",
  "confidence": 0.60,
  "targeted_improvements": [
    {
      "action": "Enable streaming responses",
      "impact": "Perceived latency -50%",
      "caveat": "Needs client support"
    }
  ],
  "diagnostic_gaps": {
    "needed": ["P50, P99 latencies", "Request size distribution"],
    "collection_method": "Add performance logging for 48 hours"
  }
}
```

### Example 17: Regulatory Environment Partial

**User Input:**
```json
{
  "request": "Financial services AI optimization needed",
  "available_data": ["industry", "optimization_need"],
  "missing_data": ["specific_regulations", "audit_requirements", "data_handling_rules"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "compliance_first_optimization",
  "confidence": 0.50,
  "regulatory_checklist": [
    "SOC2 compliance required?",
    "PCI DSS applicable?",
    "Model explainability needed?"
  ],
  "compliant_strategies": [
    "On-premise model deployment options",
    "Audit trail implementation",
    "Data anonymization techniques"
  ]
}
```

### Example 18: Cost Allocation Unknown

**User Input:**
```json
{
  "request": "Multiple departments using AI, need cost control",
  "available_data": ["multi_department_usage"],
  "missing_data": ["department_breakdown", "usage_attribution", "budget_per_department"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "cost_attribution_setup",
  "confidence": 0.45,
  "attribution_framework": {
    "implementation": [
      "Tag requests by department",
      "Implement usage quotas",
      "Create chargeback model"
    ]
  },
  "department_template": {
    "name": "___",
    "monthly_budget": "$___",
    "primary_use_cases": "___",
    "priority_level": "___"
  }
}
```

### Example 19: Minimal Context Emergency

**User Input:**
```json
{
  "request": "AI costs killing our startup",
  "available_data": ["urgent_cost_issue", "startup_context"],
  "missing_data": ["specific_costs", "runway", "core_features"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "emergency_triage",
  "confidence": 0.40,
  "immediate_actions": [
    {
      "action": "Implement hard spending caps",
      "timeline": "Today",
      "impact": "Prevent overruns"
    },
    {
      "action": "Switch to cheaper models for non-critical",
      "timeline": "24 hours",
      "impact": "40-60% reduction"
    }
  ],
  "survival_mode": {
    "essential_only": "Identify 3 core features to maintain",
    "everything_else": "Pause or significantly downgrade"
  }
}
```

### Example 20: Complex Multi-System Partial

**User Input:**
```json
{
  "request": "Optimize AI across microservices architecture",
  "available_data": ["architecture_type", "optimization_goal"],
  "missing_data": ["service_count", "communication_patterns", "ai_touchpoints"]
}
```

**Agent Response Pattern:**
```python
{
  "workflow": "distributed_optimization",
  "confidence": 0.35,
  "architecture_discovery": {
    "service_map": "List all services using AI",
    "communication_matrix": "Map inter-service AI calls",
    "bottleneck_identification": "Trace request flows"
  },
  "universal_patterns": [
    "Implement service mesh for AI calls",
    "Centralize model serving",
    "Add distributed caching layer"
  ]
}
```

---

## Implementation Instructions

### 1. Prompt Engineering Guidelines

```python
SYSTEM_PROMPT = """
You are an orchestration agent that must handle varying levels of data completeness.

Data Sufficiency Classification:
- SUFFICIENT (>80%): Execute full optimization workflow
- PARTIAL (40-80%): Execute modified workflow with caveats
- INSUFFICIENT (<40%): Focus on data collection and education

For EVERY request:
1. Assess data completeness
2. Select appropriate workflow
3. Communicate confidence level
4. Provide immediate value
5. Request missing data with clear justification

Always structure responses with:
- workflow: selected execution path
- confidence: 0.0-1.0 score
- immediate_value: what we can do now
- data_needs: what would unlock more value
"""
```

### 2. Workflow Selection Logic

```python
def select_workflow(available_data: dict, required_data: list) -> dict:
    """Select appropriate workflow based on data completeness."""
    
    completeness = len(available_data) / len(required_data)
    
    if completeness >= 0.80:
        return {
            "type": "full_optimization",
            "confidence": 0.85 + (completeness * 0.15),
            "phases": ["analyze", "optimize", "implement", "monitor"]
        }
    elif completeness >= 0.40:
        return {
            "type": "modified_optimization",
            "confidence": 0.50 + (completeness * 0.35),
            "phases": ["quick_wins", "data_request", "phased_optimization"]
        }
    else:
        return {
            "type": "data_collection_focus",
            "confidence": completeness * 0.50,
            "phases": ["educate", "collect", "demonstrate_value"]
        }
```

### 3. Response Generation Template

```python
def generate_response(workflow: dict, context: dict) -> dict:
    """Generate appropriate response based on workflow and context."""
    
    response = {
        "workflow": workflow["type"],
        "confidence": workflow["confidence"],
        "execution_plan": []
    }
    
    # Always provide immediate value
    response["immediate_actions"] = get_immediate_actions(context)
    
    # Add caveats for partial data
    if workflow["confidence"] < 0.80:
        response["caveats"] = generate_caveats(context)
        response["confidence_factors"] = explain_confidence(workflow)
    
    # Include data request for incomplete scenarios
    if workflow["type"] != "full_optimization":
        response["data_request"] = generate_data_request(context)
        response["value_with_complete_data"] = project_full_value(context)
    
    return response
```

### 4. Error Handling Patterns

```python
def handle_insufficient_data(context: dict) -> dict:
    """Handle cases with insufficient data gracefully."""
    
    return {
        "status": "data_needed",
        "user_message": "I'll need more information to provide specific recommendations.",
        "guidance": {
            "quick_template": generate_quick_template(context),
            "detailed_questions": generate_questions(context),
            "why_needed": explain_data_importance(context)
        },
        "value_proposition": {
            "with_data": "Specific optimization plan with 30-70% cost reduction",
            "timeline": "Results within 24 hours of data submission",
            "success_rate": "87% of users achieve target savings"
        }
    }
```

### 5. Testing Validation Patterns

```python
async def validate_data_handling(agent, test_case: dict):
    """Validate agent handles data completeness correctly."""
    
    result = await agent.execute(test_case["input"])
    
    # Verify workflow selection
    assert result["workflow"] == test_case["expected_workflow"]
    
    # Verify confidence scoring
    assert abs(result["confidence"] - test_case["expected_confidence"]) < 0.1
    
    # Verify immediate value delivery
    assert "immediate_actions" in result or "immediate_value" in result
    
    # Verify data request for incomplete cases
    if test_case["data_completeness"] < 0.8:
        assert "data_request" in result
        assert all(field in result["data_request"] 
                  for field in ["priority", "items", "justification"])
    
    # Verify graceful degradation
    assert result.get("status") != "error"
    assert len(result.get("user_message", "")) > 0
```

---

## Best Practices

1. **Always Provide Value**: Never return empty responses; always offer something actionable
2. **Progressive Enhancement**: Start with what's possible, build toward ideal
3. **Clear Communication**: Be transparent about limitations and confidence levels
4. **Educational Approach**: Help users understand why data matters
5. **Fail Gracefully**: Degrade functionality smoothly rather than failing completely

## Monitoring and Metrics

Track these metrics to ensure effective data handling:

1. **Conversion Rate**: Users who provide requested data
2. **Value Delivery Rate**: Successful optimizations despite partial data
3. **User Satisfaction**: Feedback on partial data handling
4. **Data Collection Success**: Percentage of complete data sets obtained
5. **Confidence Accuracy**: Correlation between confidence scores and outcomes

## Continuous Improvement

1. Analyze patterns in missing data to improve initial data collection
2. Refine confidence scoring based on actual outcomes
3. Update templates based on successful data collection patterns
4. Enhance value delivery for common partial data scenarios
5. Build pattern library from successful interventions

---

*This document should be updated as new patterns emerge and validated through production usage.*