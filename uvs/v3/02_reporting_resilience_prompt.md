# Multi-Agent Team: UVS Reporting Resilience v3

## 📚 CRITICAL: Required Reading Before Starting

### Primary Source of Truth
**MUST READ FIRST**: [`../../UVS_REQUIREMENTS.md`](../../UVS_REQUIREMENTS.md) - This is the authoritative specification for UVS implementation.

### Coordination with Other Teams
**If any confusion or conflicts arise**, read the other agent team prompts in this directory:
- `01_action_plan_enhancement_prompt.md` - ActionPlanBuilder enhancements
- `03_supervisor_orchestration_prompt.md` - Supervisor simplification

These prompts work together - understanding all three ensures consistent implementation.

## Team Mission
Transform the ReportingSubAgent into an unbreakable value delivery system that ALWAYS provides meaningful responses to users, regardless of data availability or upstream agent failures.

## Team Composition & Roles

### 1. Principal Engineer (Coordinator)
- **Role**: Architecture leadership and final integration
- **Responsibilities**:
  - Analyze current ReportingSubAgent implementation
  - Design resilience patterns that maintain SSOT
  - Ensure WebSocket event preservation
  - Coordinate agent efforts and synthesize results

### 2. Product Manager Agent
- **Role**: User value optimization and business alignment
- **Responsibilities**:
  - Define value metrics for each report type
  - Create user journey maps for failure scenarios
  - Validate "CHAT IS KING" principle implementation
  - Design next_steps that drive user engagement

### 3. Implementation Agent
- **Role**: Code execution with defensive programming
- **Responsibilities**:
  - Implement three-tier report generation
  - Add comprehensive exception handling
  - Create fallback template system
  - Ensure zero-crash guarantee

### 4. QA/Security Agent
- **Role**: Exhaustive failure testing
- **Responsibilities**:
  - Test every possible failure path
  - Verify data isolation in error scenarios
  - Load test with malformed inputs
  - Validate graceful degradation

## Context & Current State

### UVS Core Requirement
```python
# From UVS_REQUIREMENTS.md
"ReportingSubAgent must NEVER crash and ALWAYS deliver value"
"Works with NO data, partial data, or full data"
"Every response must have actionable next_steps"
```

### Current ReportingSubAgent Structure
```python
class ReportingSubAgent(BaseAgent):
    """Current implementation that needs UVS enhancement"""
    
    async def execute(self, context: UserExecutionContext):
        # Currently can fail if no data
        # Needs UVS resilience patterns
        pass
```

## Required Implementation

### 1. Three-Tier Report Generation System

```python
class ReportingSubAgent(BaseAgent):
    """Enhanced with UVS resilience"""
    
    async def execute(self, context: UserExecutionContext) -> Dict[str, Any]:
        """GUARANTEED to return value - NEVER raises exceptions"""
        
        try:
            # Assess what data we have
            data_assessment = self._assess_available_data(context)
            
            # Generate appropriate report type
            if data_assessment.has_full_data:
                return await self._generate_full_report(context)
            elif data_assessment.has_partial_data:
                return await self._generate_partial_report(context)
            else:
                return await self._generate_guidance_report(context)
                
        except Exception as e:
            # ULTIMATE FALLBACK - This should rarely execute
            logger.error(f"ReportingSubAgent fallback triggered: {e}")
            return self._get_emergency_fallback_report(context, e)
    
    def _assess_available_data(self, context: UserExecutionContext) -> DataAssessment:
        """Safely assess what data is available"""
        return DataAssessment(
            has_triage=bool(context.metadata.get('triage_result')),
            has_data=bool(context.metadata.get('data_result')),
            has_optimizations=bool(context.metadata.get('optimizations_result')),
            has_action_plan=bool(context.metadata.get('action_plan'))
        )
```

### 2. Report Type Implementations

```python
async def _generate_full_report(self, context: UserExecutionContext) -> Dict:
    """Generate comprehensive report with all data available"""
    return {
        'report_type': 'full_analysis',
        'status': 'success',
        'summary': self._create_executive_summary(context),
        'data_insights': self._extract_data_insights(context),
        'optimizations': self._format_optimizations(context),
        'action_plan': self._format_action_plan(context),
        'savings_potential': self._calculate_savings(context),
        'next_steps': self._generate_implementation_steps(context),
        'visualizations': self._create_charts(context)
    }

async def _generate_partial_report(self, context: UserExecutionContext) -> Dict:
    """Generate report with incomplete data"""
    available_sections = []
    report = {
        'report_type': 'partial_analysis',
        'status': 'partial',
        'data_completeness': self._calculate_completeness(context)
    }
    
    # Add whatever sections we can
    if context.metadata.get('data_result'):
        report['data_insights'] = self._extract_data_insights(context)
        available_sections.append('data analysis')
    
    if context.metadata.get('optimizations_result'):
        report['optimizations'] = self._format_optimizations(context)
        available_sections.append('optimization recommendations')
    
    # Always add guidance for missing data
    report['missing_data_guidance'] = self._identify_missing_data(context)
    report['next_steps'] = [
        f"Review {', '.join(available_sections)}",
        "Provide additional data for complete analysis",
        "Start with quick wins from current recommendations"
    ]
    
    return report

async def _generate_guidance_report(self, context: UserExecutionContext) -> Dict:
    """Generate helpful guidance when no data is available"""
    return {
        'report_type': 'guidance',
        'status': 'awaiting_data',
        'welcome_message': self._create_welcome_message(context),
        'value_proposition': self._explain_optimization_benefits(),
        'data_collection_guide': self._create_data_collection_guide(context),
        'quick_assessment': self._provide_quick_assessment_questions(),
        'next_steps': [
            "Answer the quick assessment questions",
            "Upload any available usage data",
            "Or describe your current AI setup"
        ],
        'example_optimizations': self._show_example_savings(),
        'resources': self._provide_helpful_resources()
    }
```

### 3. Fallback Template System

```python
class ReportTemplates:
    """Pre-built templates for various scenarios"""
    
    NO_DATA_TEMPLATE = {
        'report_type': 'guidance',
        'welcome_message': "I'm here to help optimize your AI costs and performance.",
        'quick_assessment': [
            "What AI/ML services are you currently using?",
            "What's your approximate monthly spend?",
            "What are your primary use cases?",
            "Are you experiencing any performance issues?"
        ],
        'data_collection_guide': {
            'aws': "Export Cost and Usage Reports from AWS Cost Explorer",
            'azure': "Download usage details from Azure Cost Management",
            'gcp': "Export billing data from Cloud Billing reports",
            'openai': "Export usage from OpenAI dashboard"
        },
        'next_steps': [
            "Share any of the above information",
            "Upload usage data in CSV/JSON format",
            "Or simply describe what you'd like to optimize"
        ]
    }
    
    ERROR_RECOVERY_TEMPLATE = {
        'report_type': 'recovery',
        'message': "I encountered an issue but can still help you.",
        'alternative_actions': [
            "Try uploading your data in a different format",
            "Share specific questions about optimization",
            "Describe your use case for tailored advice"
        ],
        'general_tips': [
            "Monitor token usage across all models",
            "Consider caching frequent requests",
            "Batch process where possible"
        ]
    }
```

### 4. Emergency Fallback Handler

```python
def _get_emergency_fallback_report(self, context: UserExecutionContext, error: Exception) -> Dict:
    """Ultimate fallback - MUST return valid response"""
    
    # Log error for debugging but don't expose to user
    error_id = self._log_error_safely(error, context)
    
    return {
        'report_type': 'fallback',
        'status': 'ready_to_help',
        'message': "I'm ready to help optimize your AI usage.",
        'conversation_starters': [
            "Tell me about your current AI/ML workloads",
            "Share any cost concerns you have",
            "Describe performance bottlenecks you're facing"
        ],
        'capabilities': [
            "Cost optimization across all major AI providers",
            "Performance tuning recommendations",
            "Model selection guidance",
            "Usage pattern analysis"
        ],
        'next_steps': [
            "Choose a conversation starter above",
            "Upload any usage data you have",
            "Or ask a specific optimization question"
        ],
        '_debug_id': error_id if context.debug_mode else None
    }
```

## WebSocket Event Preservation

```python
async def execute(self, context: UserExecutionContext) -> Dict:
    """Execute with WebSocket notifications preserved"""
    
    # Send start event
    await self._notify_websocket(context, 'agent_started', {
        'agent': 'reporting',
        'message': 'Generating your optimization report'
    })
    
    try:
        # Generate report (with all resilience)
        report = await self._generate_appropriate_report(context)
        
        # Send completion event
        await self._notify_websocket(context, 'agent_completed', {
            'agent': 'reporting',
            'report_type': report.get('report_type'),
            'status': 'success'
        })
        
        return report
        
    except Exception as e:
        # Even in failure, send completion
        report = self._get_emergency_fallback_report(context, e)
        
        await self._notify_websocket(context, 'agent_completed', {
            'agent': 'reporting',
            'report_type': 'fallback',
            'status': 'recovered'
        })
        
        return report
```

## Testing Requirements

### Critical Test Scenarios

```python
# Test 1: Absolutely no data
async def test_no_data_still_delivers_value():
    context = UserExecutionContext()  # Empty
    agent = ReportingSubAgent()
    report = await agent.execute(context)
    
    assert report is not None
    assert report['report_type'] == 'guidance'
    assert len(report['next_steps']) >= 3
    assert 'data_collection_guide' in report

# Test 2: Malformed context
async def test_corrupted_context_recovery():
    context = UserExecutionContext()
    context.metadata = "NOT_A_DICT"  # Intentionally broken
    
    agent = ReportingSubAgent()
    report = await agent.execute(context)
    
    assert report is not None
    assert report['report_type'] in ['guidance', 'fallback']

# Test 3: Exception during generation
async def test_exception_during_generation():
    context = UserExecutionContext()
    agent = ReportingSubAgent()
    
    with patch.object(agent, '_generate_full_report', side_effect=Exception("Catastrophic failure")):
        report = await agent.execute(context)
    
    assert report is not None
    assert 'next_steps' in report
    assert report['status'] in ['ready_to_help', 'recovery']

# Test 4: Partial data handling
async def test_partial_data_report():
    context = UserExecutionContext()
    context.metadata['data_result'] = {'usage': [1, 2, 3]}
    # No optimizations or action plan
    
    agent = ReportingSubAgent()
    report = await agent.execute(context)
    
    assert report['report_type'] == 'partial_analysis'
    assert 'data_insights' in report
    assert 'missing_data_guidance' in report
```

## Performance Considerations

```python
class ReportingSubAgent(BaseAgent):
    """Performance-optimized implementation"""
    
    def __init__(self):
        super().__init__()
        # Pre-compile templates for speed
        self._compiled_templates = self._compile_templates()
        # Cache frequently used resources
        self._resource_cache = {}
    
    @lru_cache(maxsize=100)
    def _create_data_collection_guide(self, context_hash: str) -> Dict:
        """Cache guide generation for repeated requests"""
        # Generate once, reuse many times
        pass
```

## Success Metrics

### Week 1 Must-Haves
✅ Zero crashes in 24 hours of testing  
✅ 100% of requests return valid reports  
✅ All report types have next_steps  
✅ WebSocket events fire correctly  
✅ Existing tests still pass  
✅ Response time < 2 seconds for fallback  

### Week 2 Improvements
- A/B test report effectiveness
- User engagement metrics
- Conversion from guidance to data upload
- Time to first optimization

## Integration Points

### Files to Modify
- `netra_backend/app/agents/reporting/reporting_subagent.py` - Main implementation
- `netra_backend/app/agents/state.py` - Report result structures

### Files to Create
- `netra_backend/app/agents/reporting/templates.py` - Report templates
- `netra_backend/tests/unit/test_reporting_resilience.py` - UVS tests

### Dependencies
- Must work with existing SupervisorAgent
- Must consume any ActionPlanResult format
- Must handle WebSocketNotifier correctly
- Must respect user context isolation

## Deployment Strategy

1. **Feature Flag Implementation**
   ```python
   if settings.UVS_ENABLED:
       return enhanced_reporting
   else:
       return legacy_reporting
   ```

2. **Gradual Rollout**
   - 10% traffic for 24 hours
   - Monitor error rates and user feedback
   - 50% traffic if metrics good
   - 100% after validation

3. **Rollback Plan**
   - Feature flag allows instant rollback
   - No database migrations required
   - No API changes

## Team Execution Flow

1. **Principal** analyzes current implementation
2. **PM** defines value metrics and user journeys
3. **Principal** designs resilience architecture
4. **Implementation** codes three-tier system
5. **QA** performs chaos testing
6. **Implementation** adds fallback templates
7. **QA** validates all edge cases
8. **Principal** ensures WebSocket preservation
9. **Full team** reviews and documents

## Critical Reminders

- **NEVER** let ReportingSubAgent crash
- **ALWAYS** include next_steps in response
- **PRESERVE** all WebSocket events
- **MAINTAIN** user context isolation
- **TEST** with malformed/missing data
- **OPTIMIZE** for sub-2-second responses

## Final Note

This is about making ReportingSubAgent bulletproof, not perfect. A simple guidance report delivered quickly is infinitely more valuable than a crash or timeout. Start simple, test thoroughly, then enhance iteratively.