# UVS Implementation Guide - ReportingSubAgent Focus

## Master Requirements
**See [`../../UVS_REQUIREMENTS.md`](../../UVS_REQUIREMENTS.md) for authoritative specifications.**

## Week 1: Critical Implementation

### 1. Enhance ReportingSubAgent (ONLY Change Required)

```python
# File: netra_backend/app/agents/reporting_sub_agent.py

class ReportingSubAgent(BaseAgent):
    """Enhanced with UVS fallback capabilities"""
    
    def determine_report_mode(self, context: UserExecutionContext) -> str:
        """Determine which report mode based on available data"""
        has_data = bool(context.metadata.get('data_result'))
        has_optimizations = bool(context.metadata.get('optimizations_result'))
        
        if has_data and has_optimizations:
            return 'FULL_REPORT'
        elif has_data or has_optimizations:
            return 'PARTIAL_REPORT'
        else:
            return 'GUIDANCE_REPORT'
    
    async def execute(self, context: UserExecutionContext) -> Dict:
        """Enhanced execute that NEVER crashes"""
        try:
            mode = self.determine_report_mode(context)
            
            if mode == 'FULL_REPORT':
                # Business as usual
                report = await self.generate_full_report(context)
                
            elif mode == 'PARTIAL_REPORT':
                # Work with what we have
                report = await self.generate_partial_report(context)
                report['missing_data_note'] = 'Additional data would enhance this analysis'
                
            else:  # GUIDANCE_REPORT
                # Help user get started
                report = await self.generate_guidance_report(context)
            
            # ALWAYS add next steps
            report['next_steps'] = self.generate_next_steps(context, mode)
            return report
            
        except Exception as e:
            # ULTIMATE FALLBACK - Never crash
            self.logger.error(f"Report generation failed: {e}")
            return {
                'report_type': 'fallback',
                'message': 'I can help you optimize your AI usage. Let\'s start by understanding your needs.',
                'next_steps': [
                    'Share any usage data you have',
                    'Describe your current AI setup',
                    'Tell me your optimization goals'
                ],
                'error_logged': str(e)
            }
    
    def generate_next_steps(self, context: UserExecutionContext, mode: str) -> List[str]:
        """Always provide actionable next steps"""
        
        if mode == 'FULL_REPORT':
            # Have everything - suggest implementation
            opts = context.metadata.get('optimizations_result', {}).get('optimizations', [])
            if opts:
                return [f"Implement: {opts[0].get('title', 'top optimization')}",
                       "Review other optimization opportunities",
                       "Track metrics after implementation"]
        
        elif mode == 'PARTIAL_REPORT':
            # Missing some data
            return ["Provide additional data for deeper analysis",
                   "Review current findings",
                   "Share more context about your use case"]
        
        else:  # GUIDANCE_REPORT
            # Need data
            return ["Share your AI usage data (CSV, logs, dashboards)",
                   "Describe your current setup and challenges",
                   "Tell me what you want to optimize (cost, speed, quality)"]
```

### 2. Minimal WorkflowOrchestrator Update

```python
# File: netra_backend/app/workflow/orchestrator.py
# MINIMAL CHANGE - Just add error handling

class WorkflowOrchestrator:
    """Existing orchestrator with minimal changes"""
    
    async def execute_workflow(self, context: UserExecutionContext):
        # EXISTING agent pipeline
        agents = [
            self.triage_agent,
            self.data_agent,
            self.optimization_agent,
            self.reporting_agent  # Now enhanced with UVS
        ]
        
        for agent in agents:
            try:
                result = await agent.execute(context)
                context.metadata[f'{agent.name}_result'] = result
            except Exception as e:
                # NEW: Log but continue - ReportingSubAgent handles gracefully
                self.logger.error(f"Agent {agent.name} failed: {e}")
                context.metadata[f'{agent.name}_error'] = str(e)
                # Don't break - let ReportingSubAgent handle it
        
        # ReportingSubAgent ALWAYS produces a result now
        return context.metadata.get('reporting_result')
```

## Testing Implementation

### Test 1: No Data Scenario
```python
async def test_reporting_no_data():
    """Must pass - ReportingSubAgent handles no data"""
    context = UserExecutionContext()
    # Empty context - no results from other agents
    
    agent = ReportingSubAgent(context_factory, tool_factory)
    report = await agent.execute(context)
    
    assert report is not None
    assert report['report_type'] == 'guidance'
    assert 'next_steps' in report
    assert len(report['next_steps']) > 0
```

### Test 2: Partial Data
```python
async def test_reporting_partial_data():
    """Must pass - Works with incomplete data"""
    context = UserExecutionContext()
    context.metadata['data_result'] = {'some': 'data'}
    # No optimizations
    
    agent = ReportingSubAgent(context_factory, tool_factory)
    report = await agent.execute(context)
    
    assert report is not None
    assert report['report_type'] == 'partial'
    assert 'next_steps' in report
```

### Test 3: Exception Handling
```python
async def test_reporting_handles_exceptions():
    """Must pass - Never crashes"""
    context = UserExecutionContext()
    context.metadata['data_result'] = None  # Will cause issues
    
    agent = ReportingSubAgent(context_factory, tool_factory)
    # Force an error scenario
    with patch.object(agent, 'generate_full_report', side_effect=Exception("Test error")):
        report = await agent.execute(context)
    
    assert report is not None  # Still returns something
    assert 'next_steps' in report
    assert report['report_type'] == 'fallback'
```

## Deployment Checklist

### Pre-Deployment (Local)
- [ ] Update ReportingSubAgent with fallback logic
- [ ] Add comprehensive try/catch blocks
- [ ] Implement three report modes
- [ ] Add next_steps generation
- [ ] Run local tests

### Testing
- [ ] Test with no data
- [ ] Test with partial data  
- [ ] Test with full data
- [ ] Test exception scenarios
- [ ] Verify WebSocket events still fire

### Deployment
- [ ] Deploy to staging
- [ ] Monitor error logs
- [ ] Test user scenarios
- [ ] Verify no crashes in 24 hours
- [ ] Deploy to production

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Report crashes with no data | Add GUIDANCE_REPORT mode |
| Missing next_steps | Ensure generate_next_steps() always called |
| WebSocket events not firing | Don't change event emission code |
| Other agents failing | WorkflowOrchestrator continues, ReportingSubAgent handles |

## What NOT to Do

❌ Don't change UnifiedTriageAgent  
❌ Don't modify UnifiedDataAgent  
❌ Don't alter OptimizationAgent  
❌ Don't rewrite WorkflowOrchestrator  
❌ Don't change WebSocket infrastructure  
❌ Don't modify tool architecture  

## Success Metrics

After deployment, verify:
- Zero crashes in ReportingSubAgent logs
- 100% of requests get a response
- All responses have next_steps
- Existing workflows still function
- WebSocket events continue

## Remember

**CHAT VALUE IS KING** - Every user interaction must deliver value, even with zero data.

This is a targeted fix to make ReportingSubAgent bulletproof, not a system redesign.