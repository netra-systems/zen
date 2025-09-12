# Migration Rollback Procedures
**DeepAgentState to UserExecutionContext Migration - Emergency Rollback Guide**

> **Purpose:** Provide comprehensive rollback procedures to quickly restore system functionality if critical issues arise during the DeepAgentState to UserExecutionContext migration.

---

## 🚨 WHEN TO INITIATE ROLLBACK

### Immediate Rollback Triggers (RED ALERT)
- **User Data Leakage Detected:** Cross-user data contamination observed
- **Golden Path Failure:** Chat functionality broken for >5 minutes
- **System Outage:** >30% of user requests failing
- **Performance Degradation:** >50% increase in response times
- **Database Connection Failures:** User context database issues

### Cautionary Rollback Triggers (AMBER ALERT)  
- **WebSocket Event Failures:** Events not delivered to users
- **Agent Execution Errors:** Agents failing to execute properly
- **Test Suite Failures:** >20% of integration tests failing
- **Memory Leaks:** Significant memory usage increase
- **Authentication Issues:** User context validation failures

---

## 🔄 ROLLBACK STRATEGY OVERVIEW

### Phase-Based Rollback Approach
1. **Component-Level Rollback:** Roll back individual components first
2. **Service-Level Rollback:** Roll back entire services if needed  
3. **System-Wide Rollback:** Complete system rollback as last resort

### Rollback Methods
- **Feature Flag Rollback:** Toggle between old and new implementations
- **Code Rollback:** Revert to previous commit/branch
- **Configuration Rollback:** Restore previous configurations
- **Database Rollback:** Restore previous schema/data if needed

---

## 🎛️ FEATURE FLAG ROLLBACK IMPLEMENTATION

### Pre-Migration Setup
Before starting migration, implement feature flags for gradual rollback:

```python
# netra_backend/app/core/migration_flags.py
import os
from typing import Dict, Any

class MigrationFlags:
    """Feature flags for controlling migration rollback."""
    
    @staticmethod
    def use_user_execution_context() -> bool:
        """Check if UserExecutionContext should be used instead of DeepAgentState."""
        return os.getenv("USE_USER_EXECUTION_CONTEXT", "false").lower() == "true"
    
    @staticmethod  
    def enable_agent_execution_core_migration() -> bool:
        """Check if Agent Execution Core migration is enabled."""
        return os.getenv("ENABLE_AGENT_EXECUTION_CORE_MIGRATION", "false").lower() == "true"
    
    @staticmethod
    def enable_workflow_orchestrator_migration() -> bool:
        """Check if Workflow Orchestrator migration is enabled."""
        return os.getenv("ENABLE_WORKFLOW_ORCHESTRATOR_MIGRATION", "false").lower() == "true"
    
    @staticmethod
    def enable_tool_dispatcher_migration() -> bool:
        """Check if Tool Dispatcher migration is enabled."""
        return os.getenv("ENABLE_TOOL_DISPATCHER_MIGRATION", "false").lower() == "true"
    
    @staticmethod
    def enable_websocket_executor_migration() -> bool:
        """Check if WebSocket Executor migration is enabled."""
        return os.getenv("ENABLE_WEBSOCKET_EXECUTOR_MIGRATION", "false").lower() == "true"
```

### Component-Level Feature Flags

#### Agent Execution Core Rollback
```python
# netra_backend/app/agents/supervisor/agent_execution_core.py
from netra_backend.app.core.migration_flags import MigrationFlags

class AgentExecutionCore:
    async def execute_agent_safely(
        self,
        agent_name: str,
        context_or_state: Union[UserExecutionContext, DeepAgentState],
        execution_context: AgentExecutionContext,
        bridge: Optional["AgentWebSocketBridge"] = None
    ) -> AgentExecutionResult:
        """Execute agent with rollback capability."""
        
        if MigrationFlags.enable_agent_execution_core_migration():
            # Use new UserExecutionContext implementation
            if isinstance(context_or_state, DeepAgentState):
                # Convert DeepAgentState to UserExecutionContext for compatibility
                user_context = self._convert_state_to_context(context_or_state)
            else:
                user_context = context_or_state
            
            return await self._execute_with_user_context(
                agent_name, user_context, execution_context, bridge
            )
        else:
            # ROLLBACK: Use legacy DeepAgentState implementation  
            if isinstance(context_or_state, UserExecutionContext):
                # Convert UserExecutionContext to DeepAgentState for rollback
                state = self._convert_context_to_state(context_or_state)
            else:
                state = context_or_state
            
            return await self._execute_with_deep_agent_state(
                agent_name, state, execution_context, bridge
            )
    
    def _convert_state_to_context(self, state: DeepAgentState) -> UserExecutionContext:
        """Convert DeepAgentState to UserExecutionContext during migration."""
        return UserExecutionContext.from_request(
            user_id=state.user_id or "unknown_user",
            thread_id=state.chat_thread_id or "unknown_thread",
            run_id=state.run_id or "unknown_run",
            agent_context={
                "user_request": state.user_request,
                "triage_result": state.triage_result,
                "optimizations_result": state.optimizations_result
            }
        )
    
    def _convert_context_to_state(self, context: UserExecutionContext) -> DeepAgentState:
        """Convert UserExecutionContext to DeepAgentState during rollback."""
        from netra_backend.app.agents.state import DeepAgentState
        
        return DeepAgentState(
            user_request=context.agent_context.get("user_request", ""),
            user_id=context.user_id,
            chat_thread_id=context.thread_id,
            run_id=context.run_id
        )
    
    async def _execute_with_user_context(
        self, 
        agent_name: str,
        user_context: UserExecutionContext,
        execution_context: AgentExecutionContext,
        bridge: Optional["AgentWebSocketBridge"] = None
    ) -> AgentExecutionResult:
        """NEW: Execute with UserExecutionContext (migrated implementation)."""
        # Implementation from Phase 1 migration
        pass
    
    async def _execute_with_deep_agent_state(
        self,
        agent_name: str, 
        state: DeepAgentState,
        execution_context: AgentExecutionContext,
        bridge: Optional["AgentWebSocketBridge"] = None
    ) -> AgentExecutionResult:
        """ROLLBACK: Execute with DeepAgentState (original implementation)."""
        # Keep original implementation for rollback
        pass
```

---

## 🔧 COMPONENT-SPECIFIC ROLLBACK PROCEDURES

### Component 1: Agent Execution Core Rollback

#### Immediate Rollback (30 seconds)
```bash
# Set environment variable to disable migration
export ENABLE_AGENT_EXECUTION_CORE_MIGRATION=false

# Restart application services
kubectl rollout restart deployment/netra-backend
kubectl rollout restart deployment/netra-websocket

# Verify rollback
curl -X GET https://staging.netra.ai/health/agent-execution-core
```

#### Code Rollback (5 minutes)
```bash
# If feature flag rollback doesn't work, revert code changes
git checkout develop-long-lived
git revert <migration_commit_hash>
git push origin develop-long-lived

# Deploy reverted code
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```

#### Validation Steps
1. **Test Agent Execution:** Verify agents execute successfully
2. **Check User Isolation:** Run concurrent user tests
3. **Validate WebSocket Events:** Ensure events delivered properly
4. **Monitor Error Rates:** Check for execution errors

### Component 2: Workflow Orchestrator Rollback

#### Immediate Rollback
```bash
export ENABLE_WORKFLOW_ORCHESTRATOR_MIGRATION=false
kubectl rollout restart deployment/netra-backend
```

#### Code Rollback
```bash
# Revert workflow orchestrator changes
git checkout netra_backend/app/agents/supervisor/workflow_orchestrator.py develop-long-lived
git commit -m "rollback: Revert workflow orchestrator migration"
git push origin feat/phase1-deepagentstate-migration
```

#### Validation Steps
1. **Test Multi-Agent Workflows:** Verify complex workflows execute
2. **Check State Transitions:** Ensure proper state handling
3. **Validate Agent Coordination:** Test agent-to-agent communication

### Component 3: Tool Dispatcher Rollback

#### Immediate Rollback
```bash
export ENABLE_TOOL_DISPATCHER_MIGRATION=false
kubectl rollout restart deployment/netra-backend
```

#### Code Rollback
```bash
git checkout netra_backend/app/agents/tool_dispatcher_core.py develop-long-lived
git commit -m "rollback: Revert tool dispatcher migration"
git push origin feat/phase1-deepagentstate-migration
```

#### Validation Steps
1. **Test Tool Execution:** Verify tools execute correctly
2. **Check User Permissions:** Ensure proper tool access control
3. **Validate Tool Results:** Test tool result handling

### Component 4: WebSocket Connection Executor Rollback

#### Immediate Rollback
```bash
export ENABLE_WEBSOCKET_EXECUTOR_MIGRATION=false
kubectl rollout restart deployment/netra-websocket
```

#### Code Rollback  
```bash
git checkout netra_backend/app/websocket_core/connection_executor.py develop-long-lived
git commit -m "rollback: Revert WebSocket executor migration"
git push origin feat/phase1-deepagentstate-migration
```

#### Validation Steps
1. **Test WebSocket Connections:** Verify connections establish properly
2. **Check Event Delivery:** Ensure events reach correct users
3. **Validate Real-time Communication:** Test bi-directional communication

---

## 🚨 EMERGENCY SYSTEM-WIDE ROLLBACK

### Complete System Rollback (10 minutes)

#### Step 1: Stop Migration Immediately
```bash
# Disable all migration flags
export USE_USER_EXECUTION_CONTEXT=false
export ENABLE_AGENT_EXECUTION_CORE_MIGRATION=false
export ENABLE_WORKFLOW_ORCHESTRATOR_MIGRATION=false
export ENABLE_TOOL_DISPATCHER_MIGRATION=false
export ENABLE_WEBSOCKET_EXECUTOR_MIGRATION=false

# Update deployment config
kubectl create configmap migration-flags \
  --from-literal=USE_USER_EXECUTION_CONTEXT=false \
  --from-literal=ENABLE_AGENT_EXECUTION_CORE_MIGRATION=false \
  --from-literal=ENABLE_WORKFLOW_ORCHESTRATOR_MIGRATION=false \
  --from-literal=ENABLE_TOOL_DISPATCHER_MIGRATION=false \
  --from-literal=ENABLE_WEBSOCKET_EXECUTOR_MIGRATION=false \
  --dry-run=client -o yaml | kubectl apply -f -
```

#### Step 2: Revert to Previous Stable Branch
```bash
# Switch to previous stable state
git checkout develop-long-lived
git branch migration-rollback-$(date +%Y%m%d-%H%M%S)
git reset --hard $(git log --oneline | grep "feat(agents): enhance OptimizationsCoreSubAgent Golden Path compatibility" | head -1 | cut -d' ' -f1)

# Push rollback branch
git push origin migration-rollback-$(date +%Y%m%d-%H%M%S)
```

#### Step 3: Deploy Rollback
```bash
# Deploy previous stable version
python scripts/deploy_to_gcp.py --project netra-staging --build-local --force

# Monitor deployment
kubectl rollout status deployment/netra-backend
kubectl rollout status deployment/netra-websocket
```

#### Step 4: Verify System Recovery
```bash
# Run health checks
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_golden_path_user_flow.py

# Check system metrics
curl -X GET https://staging.netra.ai/health
curl -X GET https://staging.netra.ai/health/agents
curl -X GET https://staging.netra.ai/health/websockets
```

---

## 📊 ROLLBACK VALIDATION CHECKLIST

### Immediate Validation (1-2 minutes)
- [ ] **Service Health:** All services reporting healthy status
- [ ] **Agent Execution:** Sample agent executions completing successfully  
- [ ] **WebSocket Events:** Test WebSocket event delivery
- [ ] **User Authentication:** User login and context creation working
- [ ] **Database Connectivity:** All database operations functional

### Functional Validation (5-10 minutes)  
- [ ] **Golden Path Flow:** Complete user chat workflow functional
- [ ] **Multi-User Isolation:** Concurrent user requests properly isolated
- [ ] **Agent Workflows:** Multi-agent workflows executing correctly
- [ ] **Tool Integration:** Tools executing with proper user permissions
- [ ] **Error Handling:** Error boundaries and recovery working

### Business Validation (10-15 minutes)
- [ ] **Enterprise Features:** Enterprise customer workflows functional
- [ ] **Performance Metrics:** Response times within acceptable ranges
- [ ] **Data Integrity:** No data loss or corruption detected
- [ ] **Compliance Features:** Audit trails and logging functional
- [ ] **User Experience:** Chat quality and responsiveness maintained

---

## 📈 MONITORING AND ALERTING

### Rollback Monitoring Dashboard
Create monitoring dashboard to track rollback success:

```yaml
# monitoring/rollback-dashboard.yaml
rollback_metrics:
  - name: "agent_execution_success_rate"
    target: ">95%"
    alert_threshold: "<90%"
    
  - name: "websocket_event_delivery_rate" 
    target: ">98%"
    alert_threshold: "<95%"
    
  - name: "user_isolation_violations"
    target: "0"
    alert_threshold: ">0"
    
  - name: "system_response_time_p95"
    target: "<2s"
    alert_threshold: ">5s"
    
  - name: "error_rate"
    target: "<1%"
    alert_threshold: ">5%"
```

### Automated Rollback Triggers
```python
# monitoring/automated_rollback.py
class AutomatedRollbackMonitor:
    """Monitor system health and trigger automatic rollback if needed."""
    
    def __init__(self):
        self.rollback_triggers = {
            'user_isolation_violations': 0,
            'agent_execution_failure_rate': 0.1,  # 10%
            'websocket_event_failure_rate': 0.05,  # 5%
            'system_error_rate': 0.1,  # 10%
        }
    
    async def monitor_and_rollback(self):
        """Monitor system health and initiate rollback if triggers hit."""
        metrics = await self.get_current_metrics()
        
        for metric, threshold in self.rollback_triggers.items():
            if metrics.get(metric, 0) > threshold:
                await self.initiate_emergency_rollback(f"Metric {metric} exceeded threshold")
                break
    
    async def initiate_emergency_rollback(self, reason: str):
        """Initiate emergency rollback due to system issues."""
        logger.critical(f"EMERGENCY ROLLBACK INITIATED: {reason}")
        
        # Disable all migration flags immediately
        await self.disable_migration_flags()
        
        # Send alerts
        await self.send_emergency_alerts(reason)
        
        # Log rollback event
        await self.log_rollback_event(reason)
```

---

## 🔍 POST-ROLLBACK ANALYSIS

### Rollback Analysis Template
```markdown
## Rollback Analysis Report

### Incident Details
- **Rollback Date/Time:** [TIMESTAMP]
- **Trigger Reason:** [DESCRIPTION] 
- **Components Affected:** [LIST]
- **Duration:** [TIME_TO_RECOVERY]

### Root Cause Analysis
- **Primary Cause:** [ANALYSIS]
- **Contributing Factors:** [LIST]
- **Detection Method:** [HOW_DISCOVERED]

### Impact Assessment
- **User Impact:** [DESCRIPTION]
- **Business Impact:** [QUANTIFIED_IMPACT]
- **System Impact:** [TECHNICAL_DETAILS]

### Lessons Learned
- **What Worked Well:** [LIST]
- **What Could Improve:** [LIST]
- **Process Improvements:** [RECOMMENDATIONS]

### Action Items  
- [ ] [ACTION_ITEM_1]
- [ ] [ACTION_ITEM_2]
- [ ] [ACTION_ITEM_3]

### Prevention Measures
- **Testing Improvements:** [DETAILS]
- **Monitoring Enhancements:** [DETAILS] 
- **Process Changes:** [DETAILS]
```

---

## 🚀 RECOVERY AND RE-MIGRATION PLAN

### Post-Rollback Recovery Steps

#### 1. Stabilize System (Day 1)
- Verify all functionality restored
- Monitor system health for 24 hours
- Document rollback root cause
- Communicate status to stakeholders

#### 2. Analyze Issues (Days 2-3)
- Conduct thorough root cause analysis
- Review migration approach and testing
- Identify process improvements
- Update migration plan based on learnings

#### 3. Improve Migration Plan (Days 4-7)
- Address identified issues
- Enhance testing procedures
- Improve rollback mechanisms
- Validate fixes in isolated environment

#### 4. Re-attempt Migration (Week 2+)
- Apply lessons learned to migration plan
- Execute improved migration with better safeguards
- Monitor more closely during migration
- Have improved rollback procedures ready

### Re-Migration Success Criteria
- All original issues resolved
- Enhanced testing coverage
- Improved monitoring and alerting
- Faster rollback capabilities
- Stakeholder confidence restored

---

## 📞 EMERGENCY CONTACTS

### Rollback Decision Authority
- **Primary:** Engineering Lead
- **Secondary:** CTO
- **Emergency:** CEO

### Technical Execution Team
- **Lead Engineer:** [CONTACT]
- **DevOps Engineer:** [CONTACT]
- **Database Administrator:** [CONTACT]
- **Security Engineer:** [CONTACT]

### Communication Team
- **Customer Success:** [CONTACT]
- **Product Manager:** [CONTACT]
- **Marketing/PR:** [CONTACT]

---

**Document Status:** READY FOR USE  
**Last Updated:** 2025-09-10  
**Review Frequency:** Monthly or after each rollback event  
**Next Review:** 2025-10-10