# Test Failure Classification and Tracking

## Classification System

### By Error Type

#### 1. Type Errors
- **Pattern**: `TypeError: X takes Y positional arguments but Z were given`
- **Common Causes**: 
  - Function signature changes
  - Constructor parameter mismatches
  - Mocked objects with wrong signatures
- **Fix Strategy**: Update test calls to match current signatures

#### 2. Attribute Errors  
- **Pattern**: `AttributeError: 'NoneType' object has no attribute 'X'`
- **Common Causes**:
  - Uninitialized objects
  - Missing mocks
  - Async operations not awaited
- **Fix Strategy**: Ensure proper initialization and mock setup

#### 3. Validation Errors
- **Pattern**: `ValidationError: X validation errors for Model`
- **Common Causes**:
  - Missing required fields
  - Invalid data types
  - Schema changes
- **Fix Strategy**: Update test data to match current schemas

#### 4. Import Errors
- **Pattern**: `ImportError/ModuleNotFoundError`
- **Common Causes**:
  - Module refactoring
  - Missing dependencies
  - Path issues
- **Fix Strategy**: Update import paths, install dependencies

#### 5. Navigation/DOM Errors (Frontend)
- **Pattern**: `Error: Not implemented: navigation`
- **Common Causes**:
  - jsdom limitations
  - Missing router mocks
- **Fix Strategy**: Mock navigation/router properly

### By Priority

#### Critical (P0)
- Import tests
- Database connection tests
- Authentication tests
- Core service initialization tests

#### High (P1)
- API endpoint tests
- Agent orchestration tests
- WebSocket communication tests
- Data validation tests

#### Medium (P2)
- UI component tests
- Integration tests
- Performance tests
- Edge case tests

#### Low (P3)
- Utility function tests
- Simple getter/setter tests
- Deprecated feature tests

### By Component

#### Backend
- **Database**: Repository, ClickHouse, PostgreSQL tests
- **Services**: Business logic, agent services, LLM services
- **API**: Route handlers, middleware, authentication
- **Agents**: Sub-agents, orchestration, tool selection
- **WebSocket**: Real-time communication, message handling

#### Frontend
- **Components**: React components, hooks
- **Store**: State management, actions, reducers
- **Services**: API clients, WebSocket clients
- **Utils**: Helper functions, formatters

## Current Status Summary

### Backend Tests
- **Total Tests**: ~500+
- **Categories**:
  - Database: 50+ tests
  - Services: 150+ tests
  - API: 100+ tests
  - Agents: 80+ tests
  - WebSocket: 40+ tests
  - Core: 30+ tests

### Frontend Tests
- **Total Tests**: 240+
- **Categories**:
  - Components: 100+ tests
  - Hooks: 40+ tests
  - Store: 30+ tests
  - Services: 30+ tests
  - Utils: 40+ tests

## Test Fixing Workflow

### 1. Identify Pattern
```bash
# Group failures by error type
python test_runner.py --show-failing | grep "Error:" | sort | uniq -c
```

### 2. Fix in Batches
- Group similar errors together
- Fix root causes first (e.g., schema changes)
- Update mocks and fixtures
- Run tests after each batch

### 3. Verify Fixes
```bash
# Run specific test file
python -m pytest path/to/test.py -xvs

# Run test category
python test_runner.py --level unit --backend-only
```

### 4. Document Changes
- Update this classification when new patterns emerge
- Add to learnings.xml for future reference
- Update test documentation

## Common Fix Patterns

### Pattern 1: Async Test Issues
```python
# Before (fails)
def test_async_operation():
    result = async_function()
    
# After (works)
async def test_async_operation():
    result = await async_function()
```

### Pattern 2: Mock Setup Issues
```python
# Before (fails)
mock_service = Mock()
mock_service.method()  # AttributeError

# After (works)
mock_service = Mock()
mock_service.method = Mock(return_value="expected")
```

### Pattern 3: Schema Validation Issues
```python
# Before (fails)
data = {"field1": "value"}  # Missing required fields

# After (works)
data = {
    "field1": "value",
    "required_field": "value",
    "user_id": "test-user"
}
```

### Pattern 4: Navigation Mock Issues (Frontend)
```typescript
// Before (fails)
window.location.href = "/new-page";

// After (works)
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate
}));
```

## Metrics Tracking

### Test Health Metrics
- **Pass Rate**: Percentage of passing tests
- **Flakiness Rate**: Tests that pass/fail inconsistently
- **Average Duration**: Time to run test suites
- **Coverage**: Code coverage percentage

### Progress Tracking
- Tests Fixed Today: 0
- Tests Remaining: TBD (after full run)
- Estimated Completion: TBD

## Next Steps

1. Complete full test run to identify all failures
2. Categorize failures by type and priority
3. Start fixing Critical (P0) failures first
4. Process in batches of 50 as requested
5. Update this document with progress