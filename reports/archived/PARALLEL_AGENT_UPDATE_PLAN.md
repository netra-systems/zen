# Parallel Agent Update Plan: Complete UserExecutionContext Migration (No Legacy)

## Executive Summary
This plan outlines the parallel migration strategy to completely replace the legacy execution pattern with the new UserExecutionContext-based pattern across all 15+ agents, ensuring proper request-scoped isolation with NO backward compatibility.

## Current State
- **Updated**: 1 agent (CorpusAdminSubAgent) 
- **Needs Update**: 15+ agents using old execute() pattern
- **Target Pattern**: Complete replacement - `execute(context: UserExecutionContext, stream_updates: bool = False)`
- **Legacy Removal**: All legacy methods will be completely removed

## Critical Changes from Legacy-Free Approach

### 1. BaseAgent Updates Required
```python
# Remove ALL legacy methods from base_agent.py:
# - execute_legacy() - REMOVE
# - execute() with old signature - REMOVE  
# - _convert_legacy_state() - REMOVE

# Keep only:
# - execute(context: UserExecutionContext, stream_updates: bool = False)
# - _validate_session_isolation()
# - _get_session_manager()
```

### 2. All Callers Must Be Updated Simultaneously
- Router/API endpoints must pass UserExecutionContext
- Supervisor must create context for sub-agents
- Test fixtures must use new pattern
- No gradual migration possible

## Parallel Execution Strategy

### Phase 0: Preparation (Must Complete First)
**Timeline**: 2 hours
**Critical**: This phase blocks all others

#### Task 0.1: Update All Entry Points
```python
# Update all API routes/endpoints
# netra_backend/app/api/routes/*.py
async def endpoint(request: Request, db: Session = Depends(get_db)):
    context = UserExecutionContext(
        user_id=current_user.id,
        thread_id=thread_id,
        run_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        db_session=db,
        metadata={}
    )
    result = await agent.execute(context, stream_updates=True)
```

#### Task 0.2: Update BaseAgent Class
```python
# netra_backend/app/agents/base_agent.py
class BaseAgent:
    def execute(
        self,
        context: 'UserExecutionContext',
        stream_updates: bool = False
    ) -> Any:
        """Single execution method - no legacy support."""
        context.validate()
        self._validate_session_isolation()
        # Implementation
```

### Phase 1: High Priority Core Agents (Parallel Batch 1)
**Timeline**: Execute all 3 updates in parallel
**Dependency**: Phase 0 must be complete

#### Agent 1.1: SupervisorAgent
```python
# netra_backend/app/agents/supervisor_consolidated.py
class SupervisorAgent(BaseAgent):
    def execute(
        self,
        context: UserExecutionContext,
        stream_updates: bool = False
    ) -> SupervisorResponse:
        """Execute supervisor with full context isolation."""
        context.validate()
        
        # Create child contexts for sub-agents
        for agent in self.sub_agents:
            child_context = context.create_child_context()
            result = await agent.execute(child_context, stream_updates)
        
        return response
```

#### Agent 1.2: TriageSubAgent
```python
# netra_backend/app/agents/triage_sub_agent.py
class TriageSubAgent(BaseAgent):
    def execute(
        self,
        context: UserExecutionContext,
        stream_updates: bool = False
    ) -> TriageResponse:
        """Execute triage with context-based routing."""
        context.validate()
        session_manager = DatabaseSessionManager(context)
        
        with session_manager.get_session() as session:
            # Triage logic using context
            pass
```

#### Agent 1.3: DataSubAgent
```python
# netra_backend/app/agents/data_sub_agent/data_sub_agent.py
class DataSubAgent(BaseAgent):
    def execute(
        self,
        context: UserExecutionContext,
        stream_updates: bool = False
    ) -> DataResponse:
        """Execute data operations with proper isolation."""
        context.validate()
        # All database operations through context
        return self._process_data(context)
```

### Phase 2: Medium Priority Business Logic Agents (Parallel Batch 2)
**Timeline**: Execute all 6 updates in parallel after Phase 1

#### Standard Implementation Pattern (NO LEGACY):
```python
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.core.database_session_manager import DatabaseSessionManager

class [AgentName](BaseAgent):
    def execute(
        self,
        context: UserExecutionContext,
        stream_updates: bool = False
    ) -> Any:
        """Execute agent with proper request isolation."""
        # Validate context
        context.validate()
        
        # Get session manager
        session_manager = DatabaseSessionManager(context)
        
        # NO STATE CONVERSION - use context directly
        user_id = context.user_id
        thread_id = context.thread_id
        run_id = context.run_id
        
        # Execute logic with context
        with session_manager.get_session() as session:
            # Agent logic here
            result = self._process_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                session=session
            )
        
        return result
    
    # NO LEGACY METHODS - REMOVE ALL OLD EXECUTE METHODS
```

### Phase 3: Low Priority Support/Demo Agents (Parallel Batch 3)
**Timeline**: Execute all 6 updates in parallel after Phase 1

## Implementation Checklist for Each Agent

### Required Changes (NO EXCEPTIONS):
- [ ] **REMOVE** old execute(state, run_id, stream_updates) method completely
- [ ] **REMOVE** any execute_legacy() methods
- [ ] **REMOVE** DeepAgentState imports and usage
- [ ] **ADD** new execute(context, stream_updates) method
- [ ] **ADD** UserExecutionContext import
- [ ] **ADD** DatabaseSessionManager for all DB operations
- [ ] **UPDATE** all internal method calls to use context
- [ ] **UPDATE** all sub-agent calls to pass context
- [ ] **VALIDATE** context at method entry
- [ ] **ENSURE** no session storage in instance variables

## Parallel Execution Commands

### Phase 0: Preparation (Sequential)
```bash
# Must complete before other phases
python update_base_agent.py --remove-legacy
python update_api_endpoints.py --use-context
python update_test_fixtures.py --use-context
```

### Phase 1: Core Agents (Parallel)
```bash
# Run in 3 parallel terminals
python migrate_agent.py --agent supervisor --no-legacy
python migrate_agent.py --agent triage --no-legacy
python migrate_agent.py --agent data --no-legacy
```

### Phase 2: Business Logic (Parallel)
```bash
# Run in 6 parallel terminals
python migrate_agent.py --agent reporting --no-legacy
python migrate_agent.py --agent optimizations --no-legacy
python migrate_agent.py --agent synthetic_data --no-legacy
python migrate_agent.py --agent goals_triage --no-legacy
python migrate_agent.py --agent actions_goals --no-legacy
python migrate_agent.py --agent enhanced_execution --no-legacy
```

### Phase 3: Support Agents (Parallel)
```bash
# Run in 6 parallel terminals
python migrate_agent.py --agent validation --no-legacy
python migrate_agent.py --agent data_helper --no-legacy
python migrate_agent.py --agent supply_researcher --no-legacy
python migrate_agent.py --agent demo_triage --no-legacy
python migrate_agent.py --agent demo_reporting --no-legacy
python migrate_agent.py --agent demo_core --no-legacy
```

## Migration Script (No Legacy)

```python
#!/usr/bin/env python
"""Complete migration to UserExecutionContext - NO LEGACY SUPPORT."""

import ast
import argparse
from pathlib import Path

class AgentMigrator(ast.NodeTransformer):
    """AST transformer to completely replace execution pattern."""
    
    def visit_FunctionDef(self, node):
        if node.name == 'execute':
            # Check if old signature
            if self._has_old_signature(node):
                # Replace with new signature
                return self._create_new_execute(node)
        elif node.name in ['execute_legacy', 'execute_with_context']:
            # Remove legacy methods completely
            return None
        return node
    
    def _has_old_signature(self, node):
        """Check if execute has old signature."""
        params = [arg.arg for arg in node.args.args]
        return 'state' in params or 'run_id' in params
    
    def _create_new_execute(self, node):
        """Create new execute method with context."""
        # Build new method with context parameter
        new_method = ast.FunctionDef(
            name='execute',
            args=ast.arguments(
                args=[
                    ast.arg(arg='self', annotation=None),
                    ast.arg(arg='context', 
                           annotation=ast.Constant(value='UserExecutionContext')),
                    ast.arg(arg='stream_updates',
                           annotation=ast.Name(id='bool'))
                ],
                defaults=[ast.Constant(value=False)]
            ),
            body=[
                # Add context validation
                ast.Expr(ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='context'),
                        attr='validate'
                    ),
                    args=[],
                    keywords=[]
                )),
                # Transform body to use context
                *self._transform_body_for_context(node.body)
            ],
            decorator_list=node.decorator_list,
            returns=node.returns
        )
        return new_method

def migrate_agent(file_path: Path):
    """Migrate agent file to new pattern."""
    # Read file
    with open(file_path, 'r') as f:
        source = f.read()
    
    # Parse AST
    tree = ast.parse(source)
    
    # Transform
    migrator = AgentMigrator()
    new_tree = migrator.visit(tree)
    
    # Add imports
    new_imports = [
        ast.ImportFrom(
            module='netra_backend.app.agents.supervisor.user_execution_context',
            names=[ast.alias(name='UserExecutionContext', asname=None)],
            level=0
        ),
        ast.ImportFrom(
            module='netra_backend.app.core.database_session_manager',
            names=[ast.alias(name='DatabaseSessionManager', asname=None)],
            level=0
        )
    ]
    
    # Remove DeepAgentState imports
    tree.body = [node for node in tree.body 
                 if not (isinstance(node, ast.ImportFrom) and 
                        'DeepAgentState' in str(node.names))]
    
    # Add new imports at top
    tree.body = new_imports + tree.body
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(ast.unparse(new_tree))
    
    print(f"✓ Migrated {file_path} - NO LEGACY SUPPORT")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--no-legacy", action="store_true", required=True)
    args = parser.parse_args()
    
    file_map = {
        'supervisor': 'netra_backend/app/agents/supervisor_consolidated.py',
        'triage': 'netra_backend/app/agents/triage_sub_agent.py',
        # ... etc
    }
    
    migrate_agent(Path(file_map[args.agent]))
```

## Testing Strategy (No Legacy Fallback)

### Unit Tests - Complete Rewrite
```python
# All tests must use new pattern
def test_agent_execution():
    context = UserExecutionContext(
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run",
        request_id="test_request",
        db_session=mock_session,
        metadata={}
    )
    
    agent = MyAgent()
    result = agent.execute(context, stream_updates=False)
    
    # NO LEGACY TESTING - context only
    assert result is not None
    context.validate()  # Ensure context still valid
```

### Integration Tests
```python
# Test full flow with context
async def test_full_pipeline():
    # Create root context
    root_context = UserExecutionContext.create_root_context(
        user_id=user.id,
        db_session=session
    )
    
    # Execute through supervisor
    supervisor = SupervisorAgent()
    result = await supervisor.execute(root_context)
    
    # Verify isolation
    assert root_context.request_id != result.request_id
```

## Rollback Strategy (Complete Reversion)

Since we're removing legacy completely, rollback requires:

### Emergency Rollback Plan
1. **Git Reversion**: Full git revert to previous commit
2. **Database Restore**: If schema changed, restore from backup
3. **Service Restart**: Rolling restart of all services
4. **Time to Rollback**: < 15 minutes

### Pre-Migration Backup
```bash
# Before migration
git checkout -b pre-context-migration
git push origin pre-context-migration
pg_dump production_db > backup_$(date +%Y%m%d).sql
```

## Risk Assessment (Higher Risk, Cleaner Code)

### Increased Risks (No Legacy)
1. **All-or-Nothing**: System fully broken if migration incomplete
2. **No Gradual Rollout**: Cannot test incrementally
3. **Testing Gap**: All tests must be rewritten
4. **Integration Risk**: All components must work together immediately

### Mitigation Strategies
1. **Complete Testing Environment**: Full duplicate environment for testing
2. **Automated Validation**: Script validates all agents before deployment
3. **Coordinated Deployment**: All changes deployed atomically
4. **Monitoring Enhanced**: Real-time monitoring during migration

## Success Criteria (Strict)

### Must Pass ALL:
- [ ] Zero legacy methods remain in codebase
- [ ] All agents use UserExecutionContext exclusively
- [ ] No DeepAgentState references remain
- [ ] All tests pass with new pattern
- [ ] Zero user data leakage
- [ ] WebSocket events functioning
- [ ] Performance metrics maintained
- [ ] Concurrent user isolation verified

## Timeline (Aggressive)

### Day 1: Preparation & Core
- **Morning (2 hrs)**: Phase 0 - Update base and endpoints
- **Afternoon (3 hrs)**: Phase 1 - Core agents parallel migration
- **Evening (2 hrs)**: Validation and testing

### Day 2: Complete Migration
- **Morning (4 hrs)**: Phase 2 & 3 - All remaining agents in parallel
- **Afternoon (3 hrs)**: Integration testing
- **Evening (1 hr)**: Final validation

### Day 3: Deployment
- **Morning**: Staging deployment
- **Afternoon**: Production deployment
- **Evening**: Monitoring and validation

## Post-Migration Cleanup

### Remove All Legacy Code
```bash
# Find and remove all legacy patterns
grep -r "execute_legacy" --include="*.py" | xargs rm
grep -r "DeepAgentState" --include="*.py" | xargs sed -i '/DeepAgentState/d'
grep -r "execute.*state.*run_id" --include="*.py" # Manual review
```

### Update Documentation
- Remove all references to legacy patterns
- Update API documentation
- Update developer guides
- Archive migration documentation

## Conclusion

This complete migration plan removes ALL legacy support, providing:
- **Clean Architecture**: No technical debt from backward compatibility
- **Enforced Isolation**: No possibility of legacy bypass
- **Simplified Codebase**: Single execution pattern throughout
- **Future-Proof**: No migration debt to handle later

The trade-off is higher risk during migration, but results in a cleaner, more maintainable system with guaranteed request isolation and no legacy burden.