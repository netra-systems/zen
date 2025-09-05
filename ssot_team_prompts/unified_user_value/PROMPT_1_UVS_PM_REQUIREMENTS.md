# PROMPT 1: UVS Product Manager - Requirements & User Loop Design

## COPY THIS ENTIRE PROMPT INTO A NEW CLAUDE INSTANCE:

You are a Product Manager designing the Unified User Value System (UVS) requirements for the Netra Apex AI Optimization Platform. The UVS ensures that ReportingSubAgent NEVER crashes and ALWAYS delivers actionable user value through iterative loops.

## CRITICAL CONTEXT - READ FIRST:

The UVS is built on the understanding that users engage in ITERATIVE LOOPS:
1. Users bring problems (often vague: "boss says reduce AI costs")
2. We provide the audit process and imagination
3. Users need help collecting concrete data
4. Reports generate new questions
5. Data helper fills gaps
6. Loop continues until user achieves their goal

### User Journey Examples:
- **Imagination Loop**: "Boss says fix costs" → We help imagine what to optimize
- **Data Discovery Loop**: "Need to reduce token spend" → We help find what data is needed
- **Refinement Loop**: "Report missing X" → Data helper collects missing pieces
- **Context Loop**: User refines scope (project vs company level)

## YOUR TASK:

Define comprehensive requirements for the UVS implementation in ReportingSubAgent (`netra_backend/app/agents/reporting_sub_agent.py`).

### 1. Core UVS Requirements

**The UVS Promise:**
- 100% user value delivery (NEVER crash)
- Progressive value levels (FULL → STANDARD → BASIC → MINIMAL → FALLBACK)
- Automatic data helper triggering for missing data
- Iterative loop support (users ask follow-up questions)

**User Value Loops:**
```python
UVS_LOOPS = {
    'IMAGINATION': 'User has problem but no data → Guide to data sources',
    'DATA_DISCOVERY': 'User has goal but missing data → Show what's needed',
    'REFINEMENT': 'User has report but needs more → Collect additional data',
    'CONTEXT': 'User refining scope → Adjust analysis level'
}
```

### 2. ReportingSubAgent UVS Enhancement Requirements

**Location**: `netra_backend/app/agents/reporting_sub_agent.py`

**MUST MAINTAIN:**
- Class name: `ReportingSubAgent` (NO CHANGES)
- Base class: `BaseAgent`
- WebSocket events (agent_started, thinking, tool_executing, completed)
- Factory pattern compatibility

**MUST ADD:**
```python
class ReportingSubAgent(BaseAgent):
    """UVS core - guaranteed user value delivery"""
    
    # UVS value levels
    UVS_LEVELS = {
        'FULL': ['action_plan_result', 'optimizations_result', 'data_result', 'triage_result'],
        'STANDARD': ['optimizations_result', 'data_result', 'triage_result'],
        'BASIC': ['data_result', 'triage_result'],
        'MINIMAL': ['triage_result'],
        'FALLBACK': []  # User request only
    }
    
    # UVS loop detection
    UVS_LOOP_PATTERNS = {
        'needs_imagination': lambda ctx: not ctx.metadata.get('data_result'),
        'needs_data': lambda ctx: len(ctx.metadata) < 2,
        'needs_refinement': lambda ctx: ctx.metadata.get('user_feedback'),
        'needs_context': lambda ctx: not ctx.metadata.get('scope_defined')
    }
```

### 3. Iterative Loop Support

**Loop Detection Requirements:**
- Identify when user needs imagination (no clear starting point)
- Detect missing data requirements
- Recognize refinement requests
- Handle scope changes

**Loop Response Patterns:**
```python
def generate_loop_guidance(self, loop_type: str) -> Dict:
    """Generate guidance for next iteration"""
    if loop_type == 'IMAGINATION':
        return {
            'questions': [
                'What is your current AI spend?',
                'Which models are you using?',
                'What are your latency requirements?'
            ],
            'data_sources': ['CloudWatch', 'OpenAI API', 'Internal logs'],
            'next_steps': 'Collect usage metrics from suggested sources'
        }
    # ... other loop types
```

### 4. Data Helper Integration

**Automatic Triggering:**
- When data sufficiency < 40%
- When user explicitly asks "what data do I need?"
- When report confidence < threshold
- When loop pattern detected

**Data Helper Prompts:**
```python
DATA_HELPER_TRIGGERS = {
    'missing_costs': 'To optimize costs, I need: token usage, model types, request frequency',
    'missing_latency': 'For latency optimization: response times, model sizes, batch sizes',
    'missing_context': 'Please specify: project name, time range, optimization goals'
}
```

### 5. Progressive Value Delivery

**Value Levels with User Guidance:**

**FULL (100% data):**
- Complete analysis
- Actionable recommendations
- Implementation plan

**STANDARD (75% data):**
- Core analysis
- Key recommendations
- "Get these 3 data points for complete analysis"

**BASIC (50% data):**
- Initial insights
- "Here's what I found, provide X, Y, Z for deeper analysis"

**MINIMAL (25% data):**
- Problem understanding
- "I understand your goal, let's collect this data..."

**FALLBACK (0% data):**
- Imagination mode
- "Let's explore what you want to optimize. Consider these areas..."

### 6. User Story Examples

```markdown
AS A first-time user
WHEN I say "boss wants me to reduce AI costs"
THEN UVS provides imagination guidance
AND suggests specific data to collect
AND explains how to get it

AS A returning user
WHEN I provide partial data
THEN UVS delivers value from available data
AND clearly states what's missing
AND provides collection instructions

AS A user with a report
WHEN I ask "what about latency?"
THEN UVS detects refinement loop
AND triggers data helper for latency data
AND maintains context from previous analysis
```

### 7. Success Metrics

**UVS Performance:**
- Zero crashes: 100% success rate
- Value delivery: 99.9% of requests get actionable output
- Loop completion: Average 2.3 iterations to user satisfaction
- Data helper effectiveness: 85% of users successfully collect requested data

**Business Impact:**
- User retention: +30% through iterative value
- Time to value: <5 minutes for initial insights
- Complete optimization: 1-3 iteration loops
- User satisfaction: 95% find guidance helpful

### 8. Implementation Constraints

**Technical Requirements:**
- Checkpoint system for loop continuity
- Context preservation across iterations
- Graceful degradation on missing data
- WebSocket events for real-time updates

**Integration Points:**
- DataHelperAgent for data collection guidance
- UnifiedTriageAgent for problem classification
- UnifiedDataAgent for data processing
- WorkflowOrchestrator for execution flow

### 9. Example User Flows

**Flow 1: Zero to Hero**
```
User: "Help me optimize AI"
UVS: [FALLBACK] "Let's explore. What's your main concern?"
User: "Costs are too high"
UVS: [IMAGINATION] "I can help! First, collect: [data list]"
User: [provides data]
UVS: [BASIC] "Initial analysis shows X. For full optimization, add: [more data]"
User: [provides more data]
UVS: [FULL] "Complete analysis with action plan"
```

**Flow 2: Iterative Refinement**
```
User: [provides cost data]
UVS: [STANDARD] "Cost analysis complete. Save 30% by..."
User: "What about quality impact?"
UVS: [DATA_HELPER] "To assess quality, I need: [quality metrics]"
User: [provides quality data]
UVS: [FULL] "Balanced optimization: 25% cost reduction, maintaining quality"
```

## DELIVERABLES:

Create a requirements document that includes:

1. **UVS Loop Specifications** - How each loop type works
2. **Progressive Value Matrix** - What's delivered at each level
3. **Data Helper Triggers** - When/how to request data
4. **User Journey Maps** - Common paths through the system
5. **Success Criteria** - Measurable outcomes
6. **API Contracts** - ReportingSubAgent interface changes
7. **Migration Plan** - How to enhance existing code

## VALIDATION CHECKLIST:

- [ ] ReportingSubAgent remains single class (SSOT)
- [ ] Supports iterative user loops
- [ ] Progressive value delivery defined
- [ ] Data helper integration clear
- [ ] Zero crash guarantee designed
- [ ] User guidance at every level
- [ ] Context preservation across loops
- [ ] Business value quantified

Remember: The UVS is about HELPING USERS through iterative discovery, not just generating reports. We provide both the route instructions AND the options of how to get there.