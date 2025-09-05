# Unified User Value System (UVS) Requirements
## ReportingSubAgent Enhancement for Guaranteed Value Delivery v2.0

**Document Status:** IMPLEMENTATION SPEC - SIMPLIFIED ARCHITECTURE  
**Required Agents:** ONLY Triage + Reporting (with UVS)  
**Default Flow:** Triage → Data Helper → Reporting  
**Business Priority:** CHAT IS KING - Reports must ALWAYS deliver value  

---

## 🚨 CRITICAL SIMPLIFICATION: Only 2 Agents Required

### The New Reality
**ONLY 2 agents are truly required:**
1. **Triage** - Determines what user needs (can fail gracefully)
2. **Reporting (with UVS)** - ALWAYS delivers value, handles ALL failures

**Default Flow When No Data:**
```
Triage → Data Helper → Reporting (UVS)
```

**All other agents (Data, Optimization, Actions) are OPTIONAL** based on what Triage determines.

### If Triage Fails
- Reporting (UVS) handles it gracefully
- Falls back to exploratory guidance
- Still delivers value to user

---

## 1. What Must Work NOW (Week 1)

### Business Requirement
**CHAT VALUE IS KING**: Users must ALWAYS get a meaningful response from the system, even with:
- Zero data
- Failed triage
- No optimizations available
- Any agent failures

### Core Implementation

```python
class SupervisorAgent:
    def _get_required_agent_names(self):
        """ONLY 2 required agents for UVS"""
        required = ["triage", "reporting"]  # That's it!
        optional = ["data_helper", "data", "optimization", "actions"]
        return required + optional
    
    def _determine_execution_order(self, triage_result):
        """Dynamic flow based on triage"""
        if triage_result and triage_result.get("data_sufficiency") == "sufficient":
            # Have data - can run more agents
            return ["data", "optimization", "actions", "reporting"]
        else:
            # DEFAULT FLOW - no data or triage failed
            return ["data_helper", "reporting"]
```

### ReportingSubAgent Enhancement

```python
class ReportingSubAgent(BaseAgent):
    """Enhanced with UVS - NEVER crashes, ALWAYS delivers value"""
    
    async def execute(self, context: UserExecutionContext):
        """THIS METHOD MUST ALWAYS RETURN VALUE"""
        
        try:
            # Check what we have from other agents
            has_triage = bool(context.metadata.get('triage_result'))
            has_data = bool(context.metadata.get('data_result'))
            has_optimizations = bool(context.metadata.get('optimizations_result'))
            
            if has_triage and has_data and has_optimizations:
                # Full report - business as usual
                return await self.generate_full_report(context)
            elif has_data or has_optimizations:
                # Partial report - work with what we have
                return await self.generate_partial_report(context)
            else:
                # Guidance report - help user get started
                return await self.generate_guidance_report(context)
                
        except Exception as e:
            # ULTIMATE FALLBACK - Never crash
            return {
                'report_type': 'fallback',
                'message': 'I can help you optimize your AI usage. Let\'s explore your needs.',
                'next_steps': [
                    'Tell me about your current AI usage',
                    'Share any data you have',
                    'Describe what you want to optimize'
                ],
                'error_handled': str(e)
            }
    
    async def generate_guidance_report(self, context):
        """When we have nothing - still provide value"""
        return {
            'report_type': 'guidance',
            'message': 'I\'ll help you optimize your AI costs and performance.',
            'exploration_questions': [
                'What AI models are you currently using?',
                'What\'s your approximate monthly spend?',
                'What are your main use cases?'
            ],
            'next_steps': [
                'Answer any of the questions above',
                'Upload usage data if available',
                'Or describe your optimization goals'
            ],
            'data_collection_guide': self.get_data_collection_guide(context)
        }
```

---

## 2. Simplified Agent Dependencies

```python
AGENT_DEPENDENCIES = {
    "triage": {
        "required": [],  # No dependencies
        "produces": ["triage_result"]
    },
    "reporting": {
        "required": [],  # UVS: Can work with NOTHING
        "optional": ["triage_result", "data_result", "optimizations_result"],
        "produces": ["report_result"],
        "uvs_enabled": True
    },
    "data_helper": {
        "required": [],  # Can work independently
        "optional": ["triage_result"],
        "produces": ["data_helper_result"]
    },
    # Other agents are optional...
}
```

---

## 3. Dynamic Workflow Examples

### Scenario 1: User Has No Data (Most Common)
```
User: "Help me optimize my AI costs"
Flow: Triage → Data Helper → Reporting (UVS)

Triage: Identifies optimization need, no data available
Data Helper: Provides collection instructions
Reporting (UVS): Delivers guidance report with:
  - Understanding of need
  - Data collection steps
  - Next actions
```

### Scenario 2: Triage Fails
```
User: [Complex or unclear request]
Flow: Triage (fails) → Reporting (UVS)

Triage: Fails to parse request
Reporting (UVS): Handles gracefully with:
  - Exploratory questions
  - General optimization guidance
  - Help user clarify needs
```

### Scenario 3: User Has Data
```
User: [Provides CSV with usage data]
Flow: Triage → Data → Optimization → Reporting

Triage: Identifies data is available
Data: Processes the CSV
Optimization: Generates recommendations
Reporting: Full analysis report
```

---

## 4. Testing Requirements (Week 1 Priority)

### Must-Pass Tests

```python
# Test 1: Only Triage + Reporting Required
async def test_minimal_agents_work():
    """System works with just 2 agents"""
    supervisor = SupervisorAgent()
    required = supervisor._get_required_agent_names()
    assert "triage" in required[:2]
    assert "reporting" in required[:2]
    assert len([a for a in required if a in ["triage", "reporting"]]) == 2

# Test 2: Reporting Handles Everything
async def test_reporting_never_fails():
    """Reporting works even with no data"""
    context = UserExecutionContext()
    # No data, no triage result
    report = await ReportingSubAgent().execute(context)
    assert report is not None
    assert 'next_steps' in report
    assert report['report_type'] in ['guidance', 'fallback']

# Test 3: Dynamic Flow Based on Triage
async def test_dynamic_workflow():
    """Workflow adapts to triage result"""
    # No data scenario
    triage_result = {"data_sufficiency": "insufficient"}
    order = supervisor._determine_execution_order(triage_result)
    assert order == ["data_helper", "reporting"]
    
    # With data scenario
    triage_result = {"data_sufficiency": "sufficient"}
    order = supervisor._determine_execution_order(triage_result)
    assert "reporting" in order  # Always included
    assert len(order) > 2  # More agents when data available
```

---

## 5. What We're NOT Changing

- **WebSocket Infrastructure** - NO CHANGES
- **Tool Architecture** - NO CHANGES
- **Database Layer** - NO CHANGES
- **Authentication** - NO CHANGES
- **Frontend** - NO CHANGES

We're ONLY:
1. Simplifying agent requirements (2 required instead of 5+)
2. Enhancing ReportingSubAgent with UVS fallbacks
3. Making workflow dynamic based on triage

---

## 6. Success Criteria for Week 1

### MUST HAVE:
✅ Only Triage + Reporting required to run  
✅ Default flow: Triage → Data Helper → Reporting  
✅ Reporting NEVER crashes  
✅ Reporting works with NO data  
✅ Reporting handles triage failures  
✅ Every response has next_steps  
✅ Dynamic workflow based on data availability  

### NICE TO HAVE (Week 2+):
- Multi-turn context support
- Sophisticated data guidance
- Performance optimizations
- Advanced error recovery

---

## 7. Implementation Checklist

### Day 1: Core Changes
- [ ] Update `_get_required_agent_names()` to return only ["triage", "reporting"]
- [ ] Add `_determine_execution_order()` method for dynamic flow
- [ ] Update `AGENT_DEPENDENCIES` to reflect optional nature
- [ ] Modify execution flow to be dynamic

### Day 2: ReportingSubAgent UVS
- [ ] Add three report modes (full/partial/guidance)
- [ ] Implement fallback handling
- [ ] Ensure always returns value
- [ ] Add next_steps to every response

### Day 3: Integration
- [ ] Update WorkflowOrchestrator for dynamic flow
- [ ] Test with various scenarios
- [ ] Verify no crashes in 24 hours
- [ ] Deploy to staging

---

## 8. Migration Path

```python
# OLD COMPLEX FLOW (remove this):
execution_order = ["triage", "data", "optimization", "actions", "reporting"]

# NEW SIMPLE FLOW (implement this):
def get_execution_order(triage_result):
    if has_data(triage_result):
        return ["data", "optimization", "actions", "reporting"]
    else:
        return ["data_helper", "reporting"]  # DEFAULT
```

---

## Remember: SIMPLICITY IS KEY

**The Big Insight**: We don't need complex orchestration. Just:
1. **Triage** to understand the need (optional - can fail)
2. **Reporting with UVS** to ALWAYS deliver value

Everything else is gravy. The system should feel like:
- User asks for help
- We either analyze their data OR guide them to get data
- Always ends with actionable value

**This is about making the system bulletproof AND simple.**