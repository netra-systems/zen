# Alpine Container Selection Test Suite

## Overview

This comprehensive test suite (`test_alpine_container_selection.py`) is designed to expose and verify bugs in Alpine container functionality within the UnifiedDockerManager system. The tests are intentionally written to **FAIL** until the Alpine support is properly implemented.

## Current Bug Status

### Confirmed Bugs Found:

1. **Parameter Acceptance Bug**: 
   - `UnifiedDockerManager.__init__()` does not accept `use_alpine` parameter
   - Results in: `TypeError: unexpected keyword argument 'use_alpine'`

2. **Compose File Selection Bug**:
   - `_get_compose_file()` method ignores Alpine compose files
   - Always selects regular compose files even when Alpine is requested

3. **Infrastructure Available**:
   - ✅ `docker-compose.alpine.yml` exists
   - ✅ `docker-compose.alpine-test.yml` exists  
   - ❌ Not being used due to bugs above

## Test Categories

### 1. Parameter Acceptance Tests
- `TestAlpineParameterAcceptance`
- Tests that `use_alpine` parameter is accepted and stored correctly
- Tests default behavior (should default to False for backwards compatibility)
- Tests parameter type handling

### 2. Compose File Selection Tests  
- `TestComposeFileSelection`
- Tests Alpine compose file selection based on environment type
- Tests fallback behavior when Alpine files are missing
- Tests file selection priority

### 3. Integration Tests
- `TestAlpineIntegration`
- Tests actual container startup with Alpine images
- Memory usage comparison between Alpine vs regular containers
- Health check verification for Alpine containers

### 4. Edge Cases Tests
- `TestAlpineEdgeCases`
- Container switching scenarios
- Parallel execution with mixed container types
- Error handling for invalid compose files

### 5. Performance Benchmarks
- `TestAlpinePerformanceBenchmarks`
- Startup time comparisons
- Image size comparisons
- Memory usage analysis

### 6. Environment Integration Tests
- `TestAlpineEnvironmentIntegration`
- Tests across different environment types (SHARED, DEDICATED, etc.)
- Environment variable handling

## Business Value Justification (BVJ)

**Segment**: Platform/Internal - Development Velocity, Risk Reduction  
**Business Goal**: Enable memory-optimized test execution, reduce CI costs  
**Value Impact**: 40-60% memory reduction in test containers, 2x faster startup  
**Revenue Impact**: Reduces CI/CD costs by $500+/month, prevents test timeouts

## Running the Tests

### Quick Verification
```bash
# Verify the bugs exist
python -c "
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
try:
    UnifiedDockerManager(environment_type=EnvironmentType.SHARED, use_alpine=True)
    print('Bug fixed!')
except TypeError:
    print('Bug confirmed: use_alpine parameter not accepted')
"
```

### Full Test Suite
```bash
# Run all tests (will fail until bugs are fixed)
python -m pytest tests/test_alpine_container_selection.py -v

# Run without slow/benchmark tests
python -m pytest tests/test_alpine_container_selection.py -m "not slow and not benchmark" -v

# Run specific test category
python -m pytest tests/test_alpine_container_selection.py::TestAlpineParameterAcceptance -v
```

## Expected Implementation

Once the bugs are fixed, the implementation should:

1. **Add `use_alpine` parameter to UnifiedDockerManager.__init__()**
   ```python
   def __init__(self, 
                environment_type: EnvironmentType = EnvironmentType.SHARED,
                test_id: Optional[str] = None,
                use_production_images: bool = True,
                use_alpine: bool = False):  # <- Add this
   ```

2. **Update `_get_compose_file()` method**
   ```python
   def _get_compose_file(self) -> str:
       if self.use_alpine:
           alpine_files = [
               "docker-compose.alpine-test.yml" if test_env else "docker-compose.alpine.yml"
           ]
           # Check for Alpine files first, fall back to regular
   ```

3. **Store Alpine preference**
   ```python
   self.use_alpine = bool(use_alpine)  # Store as instance attribute
   ```

## Integration with Existing Systems

The tests are designed to work with the current infrastructure:

- **UnifiedDockerManager**: Primary system under test
- **Existing compose files**: Both regular and Alpine versions
- **Environment types**: SHARED, DEDICATED, etc.
- **Port allocation**: Dynamic port allocation system
- **Health checks**: Existing health monitoring

## Test Failure Patterns

**Before Fix** (Current State):
```
FAILED tests/test_alpine_container_selection.py::TestAlpineParameterAcceptance::test_init_accepts_use_alpine_parameter
TypeError: UnifiedDockerManager.__init__() got an unexpected keyword argument 'use_alpine'
```

**After Fix** (Expected State):
```
PASSED tests/test_alpine_container_selection.py::TestAlpineParameterAcceptance::test_init_accepts_use_alpine_parameter
PASSED tests/test_alpine_container_selection.py::TestComposeFileSelection::test_alpine_true_selects_alpine_test_compose
```

## Monitoring and Validation

The test suite includes comprehensive validation:

- **Parameter validation**: Ensures proper type handling
- **File existence checks**: Validates compose files exist
- **Container verification**: Confirms Alpine images are used
- **Performance monitoring**: Tracks memory and startup improvements
- **Health validation**: Ensures Alpine containers pass health checks

## Maintenance Notes

- Tests use **absolute imports** (CLAUDE.md compliant)
- No mocks in integration tests (real Docker required)
- Comprehensive error handling and skip conditions
- Performance benchmarks for memory optimization validation
- Cross-platform compatibility considerations

The test suite is ready to verify the Alpine container implementation once the bugs are fixed.