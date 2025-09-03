# Test Suite Remediation Plan
**Date**: 2025-09-02  
**Priority**: CRITICAL  
**Estimated Time**: 4-6 hours

## Executive Summary
This remediation plan addresses critical failures in smoke tests, import tests, and multi-agent team collaboration. The issues stem from environment configuration, module path problems, incomplete refactoring, and missing WebSocket integration components.

## Current State Analysis

### Test Failure Categories
1. **Environment Issues** (30% of failures)
   - Missing environment variables
   - Incorrect Python module paths
   - Service authentication failures

2. **Import/Dependency Issues** (40% of failures)
   - Circular dependencies
   - Missing module imports
   - Incorrect import paths after refactoring

3. **Multi-Agent System Issues** (30% of failures)
   - WebSocket integration broken
   - Tool dispatcher consolidation incomplete
   - Agent communication failures

## Remediation Phases

## Phase 1: Environment and Path Configuration (1 hour)

### 1.1 Create Test Environment Configuration
```python
# Create test_framework/test_env_setup.py
"""
Centralized test environment setup
"""
import os
import sys
from pathlib import Path

def setup_test_environment():
    """Configure environment for all tests"""
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Set required environment variables
    test_env_vars = {
        'ENVIRONMENT': 'testing',
        'TESTING': 'true',
        'SERVICE_SECRET': 'test-secret-key-minimum-32-chars-long',
        'JWT_SECRET': 'test-jwt-secret-minimum-32-chars',
        'DATABASE_URL': 'postgresql://test:test@localhost:5434/test_db',
        'REDIS_URL': 'redis://localhost:6381',
        'AUTH_SERVICE_URL': 'http://localhost:8081',
        'OPENAI_API_KEY': 'test-key',
        'LLM_MODE': 'mock',
        'PYTHONPATH': str(project_root)
    }
    
    for key, value in test_env_vars.items():
        os.environ[key] = value
    
    return project_root
```

### 1.2 Update pytest Configuration
```python
# Update tests/conftest.py
import sys
from pathlib import Path

# Add project root to path BEFORE any imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.test_env_setup import setup_test_environment

# Setup environment at pytest session start
def pytest_sessionstart(session):
    setup_test_environment()
```

### 1.3 Create Environment Validation Script
```bash
# scripts/validate_test_environment.py
"""Validate test environment is properly configured"""
import sys
import os
from pathlib import Path

def validate_environment():
    issues = []
    
    # Check Python path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        issues.append(f"Project root not in PYTHONPATH: {project_root}")
    
    # Check required environment variables
    required_vars = [
        'SERVICE_SECRET', 'JWT_SECRET', 'DATABASE_URL', 
        'REDIS_URL', 'AUTH_SERVICE_URL'
    ]
    
    for var in required_vars:
        if not os.environ.get(var):
            issues.append(f"Missing environment variable: {var}")
    
    # Check module imports
    try:
        import netra_backend
        import auth_service
        import shared
    except ImportError as e:
        issues.append(f"Import error: {e}")
    
    return issues

if __name__ == "__main__":
    issues = validate_environment()
    if issues:
        print("Environment validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("Environment validation passed!")
```

## Phase 2: Fix Import and Dependency Issues (2 hours)

### 2.1 Fix Tool Dispatcher Imports
```python
# netra_backend/app/agents/unified_tool_execution.py
"""Add missing function for WebSocket enhancement"""

def enhance_tool_dispatcher_with_notifications(
    tool_dispatcher,
    websocket_manager=None,
    enable_notifications=True
):
    """
    Enhance tool dispatcher with WebSocket notifications
    
    This function was missing and causing integration failures.
    """
    if not enable_notifications or not websocket_manager:
        return tool_dispatcher
    
    # Wrap tool execution with notification logic
    original_execute = tool_dispatcher.execute_tool
    
    async def execute_with_notifications(tool_name, *args, **kwargs):
        # Send tool_executing event
        if websocket_manager:
            await websocket_manager.send_agent_event({
                'type': 'tool_executing',
                'tool': tool_name,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Execute tool
        result = await original_execute(tool_name, *args, **kwargs)
        
        # Send tool_completed event
        if websocket_manager:
            await websocket_manager.send_agent_event({
                'type': 'tool_completed',
                'tool': tool_name,
                'result': str(result)[:500],  # Truncate for safety
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return result
    
    tool_dispatcher.execute_tool = execute_with_notifications
    return tool_dispatcher
```

### 2.2 Fix Circular Dependencies
```python
# scripts/fix_circular_dependencies.py
"""Identify and fix circular import dependencies"""

import ast
import os
from pathlib import Path
from typing import Dict, Set, List

class CircularDependencyFixer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.import_graph: Dict[str, Set[str]] = {}
        
    def analyze_imports(self):
        """Build import dependency graph"""
        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ['.venv', '__pycache__', 'venv']):
                continue
                
            module_name = self._get_module_name(py_file)
            imports = self._extract_imports(py_file)
            self.import_graph[module_name] = imports
    
    def find_circular_deps(self) -> List[List[str]]:
        """Find all circular dependency chains"""
        cycles = []
        visited = set()
        
        for module in self.import_graph:
            if module not in visited:
                path = []
                if self._has_cycle(module, visited, path, set()):
                    cycles.append(path)
        
        return cycles
    
    def suggest_fixes(self, cycles: List[List[str]]) -> Dict[str, str]:
        """Suggest fixes for circular dependencies"""
        fixes = {}
        
        for cycle in cycles:
            # Identify the best place to break the cycle
            weakest_link = self._find_weakest_link(cycle)
            fixes[weakest_link] = f"Move import to function level or use TYPE_CHECKING"
        
        return fixes
    
    def _find_weakest_link(self, cycle: List[str]) -> str:
        """Find the import that should be delayed or removed"""
        # Prefer to break links from:
        # 1. Test files
        # 2. Utility modules
        # 3. Higher-level modules importing lower-level ones
        
        for module in cycle:
            if 'test' in module or 'utils' in module:
                return module
        
        # Default to the last link in the cycle
        return cycle[-1]
```

### 2.3 Create Import Shim Layer
```python
# shared/import_shims.py
"""
Import shims to handle module reorganization
Provides backward compatibility during transition
"""

import sys
from typing import Any

class ImportShim:
    """Redirect old imports to new locations"""
    
    # Mapping of old paths to new paths
    REDIRECTS = {
        'netra_backend.app.agents.base.tool_dispatcher': 
            'netra_backend.app.agents.tool_dispatcher',
        'netra_backend.app.agents.base.agent_registry':
            'netra_backend.app.orchestration.agent_execution_registry',
        # Add more redirects as needed
    }
    
    @classmethod
    def install(cls):
        """Install import hooks"""
        sys.meta_path.insert(0, cls())
    
    def find_module(self, fullname, path=None):
        if fullname in self.REDIRECTS:
            return self
        return None
    
    def load_module(self, fullname):
        """Load the redirected module"""
        new_name = self.REDIRECTS[fullname]
        __import__(new_name)
        module = sys.modules[new_name]
        sys.modules[fullname] = module
        return module
```

## Phase 3: Fix Multi-Agent System (2 hours)

### 3.1 Complete Tool Dispatcher Consolidation
```python
# netra_backend/app/agents/tool_dispatcher_unified.py
"""Complete the unified tool dispatcher implementation"""

class UnifiedToolDispatcher:
    """Single source of truth for tool dispatch"""
    
    def __init__(self, tools=None, websocket_bridge=None, permission_service=None):
        self.tools = tools or []
        self.websocket_bridge = websocket_bridge
        self.permission_service = permission_service
        self.executor = self._create_executor()
        
    def _create_executor(self):
        """Create the execution engine with proper wiring"""
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        
        executor = ExecutionEngine()
        
        # Wire WebSocket bridge if available
        if self.websocket_bridge:
            executor.websocket_bridge = self.websocket_bridge
            
            # Set WebSocket manager if bridge has it
            if hasattr(self.websocket_bridge, 'websocket_manager'):
                executor.websocket_manager = self.websocket_bridge.websocket_manager
        
        return executor
    
    async def execute_tool(self, tool_name: str, *args, **kwargs):
        """Execute a tool with full integration"""
        # Permission check
        if self.permission_service:
            if not await self.permission_service.check_permission(tool_name):
                raise PermissionError(f"Permission denied for tool: {tool_name}")
        
        # Send WebSocket events if available
        if self.websocket_bridge:
            await self._send_tool_event('tool_executing', tool_name)
        
        try:
            # Execute the tool
            result = await self._execute_tool_internal(tool_name, *args, **kwargs)
            
            # Send completion event
            if self.websocket_bridge:
                await self._send_tool_event('tool_completed', tool_name, result)
            
            return result
            
        except Exception as e:
            # Send error event
            if self.websocket_bridge:
                await self._send_tool_event('tool_error', tool_name, str(e))
            raise
    
    async def _send_tool_event(self, event_type: str, tool_name: str, data=None):
        """Send WebSocket event for tool execution"""
        if not self.websocket_bridge or not hasattr(self.websocket_bridge, 'websocket_manager'):
            return
            
        event = {
            'type': event_type,
            'tool': tool_name,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if data:
            event['data'] = str(data)[:500]  # Truncate for safety
        
        await self.websocket_bridge.websocket_manager.send_agent_event(event)
```

### 3.2 Fix WebSocket Bridge Integration
```python
# netra_backend/app/services/agent_websocket_bridge.py
"""Fix the WebSocket bridge integration issues"""

class AgentWebSocketBridge:
    """Bridge between agents and WebSocket connections"""
    
    async def ensure_integration(self, supervisor=None, registry=None, force_reinit=False):
        """Ensure all components are properly integrated"""
        try:
            # Initialize WebSocket manager
            if not self._websocket_manager or force_reinit:
                self._websocket_manager = await self._initialize_websocket_manager()
            
            # Set supervisor reference
            if supervisor:
                self._supervisor = supervisor
                
                # Ensure supervisor has WebSocket reference
                if hasattr(supervisor, 'set_websocket_manager'):
                    await supervisor.set_websocket_manager(self._websocket_manager)
            
            # Set registry reference
            if registry:
                self._registry = registry
                
                # Ensure registry has WebSocket reference
                if hasattr(registry, 'set_websocket_manager'):
                    await registry.set_websocket_manager(self._websocket_manager)
                
                # Setup tool dispatcher enhancement
                await self._enhance_tool_dispatcher()
            
            return IntegrationResult(
                success=True,
                state=IntegrationState.READY,
                duration_ms=0
            )
            
        except Exception as e:
            logger.error(f"Integration failed: {e}")
            return IntegrationResult(
                success=False,
                state=IntegrationState.FAILED,
                error=str(e),
                duration_ms=0
            )
    
    async def _enhance_tool_dispatcher(self):
        """Enhance tool dispatcher with WebSocket notifications"""
        if not self._registry:
            return
            
        # Get or create tool dispatcher
        tool_dispatcher = getattr(self._registry, 'tool_dispatcher', None)
        
        if tool_dispatcher:
            # Import enhancement function locally to avoid circular deps
            from netra_backend.app.agents.unified_tool_execution import (
                enhance_tool_dispatcher_with_notifications
            )
            
            # Enhance the dispatcher
            enhanced = enhance_tool_dispatcher_with_notifications(
                tool_dispatcher,
                websocket_manager=self._websocket_manager,
                enable_notifications=True
            )
            
            # Update registry reference
            self._registry.tool_dispatcher = enhanced
```

## Phase 4: Test Suite Validation (1 hour)

### 4.1 Create Test Validation Suite
```python
# tests/test_validation_suite.py
"""Comprehensive test validation suite"""

import pytest
import asyncio
from pathlib import Path

class TestSuiteValidator:
    """Validate all test categories work correctly"""
    
    @pytest.mark.validation
    async def test_smoke_tests_run(self):
        """Verify smoke tests can run"""
        result = pytest.main([
            'tests/smoke/',
            '-v',
            '--tb=short',
            '--maxfail=1'
        ])
        assert result == 0, "Smoke tests failed"
    
    @pytest.mark.validation
    async def test_import_tests_run(self):
        """Verify import tests can run"""
        result = pytest.main([
            'tests/chat_system/test_imports.py',
            '-v',
            '--tb=short'
        ])
        assert result == 0, "Import tests failed"
    
    @pytest.mark.validation
    async def test_multi_agent_tests_run(self):
        """Verify multi-agent tests can run"""
        result = pytest.main([
            'netra_backend/tests/integration/real_services/test_multi_agent_real_services.py',
            '-v',
            '--tb=short',
            '-k', 'not real_services'  # Skip real service tests
        ])
        assert result == 0, "Multi-agent tests failed"
```

### 4.2 Create Automated Fix Script
```bash
#!/bin/bash
# scripts/auto_fix_tests.sh

echo "Starting automated test fix process..."

# Phase 1: Environment setup
echo "Phase 1: Setting up environment..."
python scripts/validate_test_environment.py
if [ $? -ne 0 ]; then
    echo "Environment validation failed. Setting up..."
    python test_framework/test_env_setup.py
fi

# Phase 2: Fix imports
echo "Phase 2: Fixing import issues..."
python scripts/fix_circular_dependencies.py
python scripts/fix_import_issues.py

# Phase 3: Validate fixes
echo "Phase 3: Validating fixes..."
python -m pytest tests/test_validation_suite.py -v

echo "Test fix process complete!"
```

## Implementation Order

1. **Immediate Actions** (30 minutes)
   - Create and run environment setup script
   - Update pytest configuration
   - Add project root to PYTHONPATH

2. **Short-term Fixes** (2 hours)
   - Implement missing WebSocket enhancement function
   - Fix tool dispatcher initialization
   - Update smoke test mocking

3. **Medium-term Fixes** (2 hours)
   - Complete tool dispatcher consolidation
   - Fix circular dependencies
   - Implement import shims

4. **Validation** (1 hour)
   - Run full test suite
   - Document remaining issues
   - Create monitoring dashboard

## Success Metrics

- ✅ All smoke tests pass (15/15)
- ✅ Import tests find all modules
- ✅ Multi-agent communication works
- ✅ No circular dependencies
- ✅ Environment properly configured
- ✅ WebSocket events properly sent

## Risk Mitigation

1. **Backup Current State**
   ```bash
   git stash
   git checkout -b test-remediation-backup
   ```

2. **Incremental Testing**
   - Test each fix in isolation
   - Commit working fixes immediately
   - Maintain rollback points

3. **Documentation**
   - Document all changes made
   - Update CLAUDE.md with new patterns
   - Create troubleshooting guide

## Monitoring and Maintenance

### Create Test Health Dashboard
```python
# scripts/test_health_dashboard.py
"""Monitor test suite health"""

def generate_dashboard():
    """Generate HTML dashboard of test health"""
    metrics = {
        'smoke_tests': run_category_tests('smoke'),
        'import_tests': run_category_tests('import'),
        'unit_tests': run_category_tests('unit'),
        'integration_tests': run_category_tests('integration'),
        'e2e_tests': run_category_tests('e2e')
    }
    
    # Generate HTML report
    html = render_dashboard_template(metrics)
    
    # Save to file
    with open('test_health_dashboard.html', 'w') as f:
        f.write(html)
    
    print(f"Dashboard generated: test_health_dashboard.html")
```

## Next Steps

1. Review and approve this plan
2. Create backup of current state
3. Execute Phase 1 immediately
4. Proceed with Phases 2-4 sequentially
5. Validate all fixes work together
6. Update documentation
7. Set up CI/CD monitoring

## Estimated Timeline

- **Total Time**: 4-6 hours
- **Phase 1**: 1 hour (Environment setup)
- **Phase 2**: 2 hours (Import fixes)
- **Phase 3**: 2 hours (Multi-agent fixes)
- **Phase 4**: 1 hour (Validation)

## Contact for Issues

If you encounter blockers during implementation:
1. Check CLAUDE.md for architectural guidance
2. Review SPEC/learnings/ for similar issues
3. Use Five Whys analysis for root cause
4. Document new learnings in SPEC/learnings/