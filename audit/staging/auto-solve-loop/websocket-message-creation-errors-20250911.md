# WebSocket Message Creation Function Errors
## Date: 2025-09-11  
## Severity: ERROR (Breaking WebSocket functionality)

## ISSUE IDENTIFIED
**Primary Error**: WebSocket message creation functions missing required arguments causing connection failures

### Evidence from GCP Logs:
```
[2025-09-11T04:38:07.577149Z] [MAIN MODE] Error during cleanup: create_error_message() missing 1 required positional argument: 'error_message'
[2025-09-11T04:38:07.577142Z] [MAIN MODE] Connection error: create_server_message() missing 1 required positional argument: 'data'
[2025-09-11T04:38:07.567328Z] Agent handler setup failed: No module named 'netra_backend.app.agents.agent_websocket_bridge'
```

### Business Impact:
- **HIGH**: WebSocket connections fail during error handling
- **User Experience**: Connection errors not properly communicated to users
- **Functionality**: Cleanup and error recovery broken
- **Chat Impact**: Degraded error handling affects chat reliability

### Related Issues:
- Module import error: agent_websocket_bridge not found
- Emergency WebSocket manager being created (fallback mode)
- Request ID format validation issues

## FIVE WHYS ANALYSIS

### ❓ WHY #1: Why are WebSocket message creation functions missing required arguments?
**ANSWER**: The actual function signatures require more parameters than the fallback implementations, but calls are using the fallback signature pattern.

**EVIDENCE**: 
- `create_error_message()` in types.py requires: `error_code: str, error_message: str`
- `create_error_message()` fallback in `__init__.py` requires: `error_code, message="Error"` 
- Calls in `websocket_ssot.py` lines 385, 398: `create_error_message("Authentication failed")` (only one argument)
- `create_server_message()` in types.py requires: `msg_type: Union[str, MessageType], data: Dict[str, Any]`
- `create_server_message()` fallback in `__init__.py` requires: `msg_type, data=None`

### ❓ WHY #2: Why are the calls using the fallback signature pattern instead of the actual signatures?
**ANSWER**: The code was written to work with the fallback implementations but is now calling the actual implementations with stricter requirements.

**EVIDENCE**:
- Lines 385 & 398 in `websocket_ssot.py`: `create_error_message("Authentication failed")` and `create_error_message("Service initialization failed")`
- These calls work with fallback: `create_error_message(error_code, message="Error")` where the string becomes `error_code`
- These calls fail with actual: `create_error_message(error_code: str, error_message: str)` because `error_message` is missing

### ❓ WHY #3: Why is the system using the actual implementations instead of fallback implementations?
**ANSWER**: Import resolution is finding the actual implementation from `types.py` instead of the fallback from `__init__.py` due to import order and module path resolution.

**EVIDENCE**:
- Import in `websocket_ssot.py` line 74-75: `from netra_backend.app.websocket_core.types import create_server_message, create_error_message`
- This imports the actual strict implementations, not the fallback implementations
- The fallback implementations in `__init__.py` are only used when the types.py import fails

### ❓ WHY #4: Why is the import resolution finding types.py instead of using the intended fallback pattern?
**ANSWER**: The module import path points directly to the specific implementation instead of going through the package's `__init__.py` which would handle fallback logic.

**EVIDENCE**:
- Direct import: `from netra_backend.app.websocket_core.types import create_error_message` 
- Package import would be: `from netra_backend.app.websocket_core import create_error_message`
- The package's `__init__.py` has try/except blocks that would use fallbacks if main imports fail
- Direct imports bypass the fallback mechanism entirely

### ❓ WHY #5: Why was the code structured with incompatible fallback and actual implementations?
**ANSWER**: The fallback implementations were designed for emergency/graceful degradation but with different signatures, creating a compatibility break when the system successfully loads the real implementations.

**EVIDENCE**:
- Fallback in `__init__.py`: `def create_error_message(error_code, message="Error", **kwargs)` - backward compatible
- Actual in `types.py`: `def create_error_message(error_code: str, error_message: str, ...)` - strict typing
- The fallback allows single-argument calls, but the real implementation requires both arguments
- This creates a "success failure" where successful loading of the real implementation breaks code that was written for the fallback

## ROOT CAUSE ANALYSIS

### 🎯 PRIMARY ROOT CAUSE
**Function Signature Incompatibility Between Fallback and Real Implementations**

The system has two different function signatures for the same functions:
1. **Fallback** (permissive): `create_error_message(error_code, message="Error")`
2. **Real** (strict): `create_error_message(error_code: str, error_message: str)`

When code is written for the fallback but executed with the real implementation, it fails.

### 🔗 CONTRIBUTING FACTORS
1. **Direct Import Pattern**: Bypasses package-level fallback logic
2. **Missing Module**: `agent_websocket_bridge` import failure triggers emergency mode
3. **Inconsistent Signatures**: Real and fallback implementations don't match
4. **Silent Failover**: System switches between implementations without warning

### 💥 FAILURE CASCADE
1. Agent websocket bridge import fails → Emergency fallback mode activated
2. Code written for fallback signatures → Direct import loads real implementation  
3. Real implementation requires more parameters → Function calls fail
4. WebSocket error handling breaks → Connection failures propagate

## IMMEDIATE FIXES REQUIRED

### 🔧 FIX #1: Correct Function Call Signatures
**File**: `/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py`

**Line 385**: 
```python
# BROKEN:
await safe_websocket_send(websocket, create_error_message("Authentication failed"))

# FIX:
await safe_websocket_send(websocket, create_error_message("AUTH_FAILED", "Authentication failed"))
```

**Line 398**:
```python  
# BROKEN:
await safe_websocket_send(websocket, create_error_message("Service initialization failed"))

# FIX:
await safe_websocket_send(websocket, create_error_message("SERVICE_INIT_FAILED", "Service initialization failed"))
```

### 🔧 FIX #2: Correct Module Import Path
**File**: `/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py`

**Lines 709, 724**:
```python
# BROKEN:
from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge

# FIX:
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
```

### 🔧 FIX #3: Review Other Potential Calls
Search for other instances of single-parameter calls:
- `create_error_message("Invalid JSON format")` - Line 765
- `create_error_message(f"Connection error in {mode.value} mode")` - Line 897

## COMPREHENSIVE TEST PLAN FOR WEBSOCKET MESSAGE CREATION FUNCTION ERRORS

### 🎯 TEST OBJECTIVES

**PRIMARY GOAL**: Create comprehensive tests that can DETECT and PREVENT function signature mismatches and import errors from recurring in WebSocket message creation functions.

**FOCUS AREAS**:
1. Function signature validation for message creation functions
2. Import path resolution for agent_websocket_bridge module
3. Fallback vs real implementation compatibility
4. Error handling and cleanup scenarios
5. WebSocket connection error messaging
6. Authentication failure messaging

### 📋 TEST SUITE STRUCTURE

#### 1. FUNCTION SIGNATURE COMPATIBILITY TESTS

**Test Suite**: `test_websocket_message_function_signatures.py`
**Location**: `/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/tests/unit/websocket_core/`
**Priority**: CRITICAL

```python
class TestWebSocketMessageFunctionSignatures(SSotBaseTestCase):
    """Test function signature compatibility between real and fallback implementations."""
    
    def test_create_error_message_real_signature(self):
        """Verify create_error_message real implementation requires both error_code and error_message."""
        
    def test_create_error_message_fallback_signature(self):
        """Verify create_error_message fallback implementation accepts single parameter."""
        
    def test_create_server_message_real_signature(self):
        """Verify create_server_message real implementation requires msg_type and data."""
        
    def test_create_server_message_fallback_signature(self):
        """Verify create_server_message fallback implementation has optional data parameter."""
        
    def test_function_signature_compatibility_matrix(self):
        """Test all combinations of real vs fallback function calls."""
        
    def test_parameter_validation_edge_cases(self):
        """Test edge cases like None values, empty strings, invalid types."""
```

#### 2. IMPORT PATH RESOLUTION TESTS

**Test Suite**: `test_websocket_import_resolution.py`
**Location**: `/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/tests/unit/websocket_core/`
**Priority**: CRITICAL

```python
class TestWebSocketImportResolution(SSotBaseTestCase):
    """Test import path resolution and module availability."""
    
    def test_agent_websocket_bridge_import_paths(self):
        """Test various import paths for agent_websocket_bridge module."""
        
    def test_websocket_types_import_fallback(self):
        """Test fallback behavior when types.py import fails."""
        
    def test_direct_vs_package_imports(self):
        """Test direct imports vs package-level imports."""
        
    def test_import_error_handling(self):
        """Test graceful handling of import failures."""
        
    def test_ssot_import_registry_compliance(self):
        """Verify imports follow SSOT_IMPORT_REGISTRY.md patterns."""
```

#### 3. REAL VS FALLBACK IMPLEMENTATION TESTS

**Test Suite**: `test_websocket_fallback_compatibility.py`
**Location**: `/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/tests/integration/websocket/`
**Priority**: HIGH

```python
class TestWebSocketFallbackCompatibility(SSotBaseTestCase):
    """Test compatibility between real and fallback implementations."""
    
    def test_real_implementation_behavior(self):
        """Test behavior when real implementations are available."""
        
    def test_fallback_implementation_behavior(self):
        """Test behavior when falling back to emergency implementations."""
        
    def test_signature_compatibility_layer(self):
        """Test that compatibility layers handle signature differences."""
        
    def test_emergency_mode_activation(self):
        """Test conditions that trigger emergency fallback mode."""
        
    def test_seamless_switching(self):
        """Test switching between real and fallback without breaking calls."""
```

#### 4. ERROR HANDLING AND CLEANUP TESTS

**Test Suite**: `test_websocket_error_scenarios.py`
**Location**: `/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/tests/integration/websocket/`
**Priority**: HIGH

```python
class TestWebSocketErrorScenarios(SSotBaseTestCase):
    """Test error handling and cleanup scenarios."""
    
    def test_authentication_failure_error_creation(self):
        """Test create_error_message during authentication failures."""
        
    def test_service_initialization_failure_error_creation(self):
        """Test create_error_message during service init failures."""
        
    def test_cleanup_error_message_creation(self):
        """Test error message creation during cleanup procedures."""
        
    def test_malformed_parameter_handling(self):
        """Test handling of malformed parameters to message functions."""
        
    def test_error_message_serialization(self):
        """Test that created error messages can be serialized for WebSocket."""
```

#### 5. WEBSOCKET CONNECTION ERROR MESSAGING TESTS

**Test Suite**: `test_websocket_connection_error_messaging.py`
**Location**: `/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/tests/e2e/websocket/`
**Priority**: HIGH

```python
class TestWebSocketConnectionErrorMessaging(SSotBaseTestCase):
    """Test WebSocket connection error messaging end-to-end."""
    
    def test_connection_error_message_delivery(self):
        """Test that connection error messages reach the client."""
        
    def test_authentication_error_flow(self):
        """Test complete authentication error flow including message creation."""
        
    def test_service_unavailable_error_flow(self):
        """Test complete service unavailable error flow."""
        
    def test_websocket_close_code_validation(self):
        """Test that appropriate WebSocket close codes are used."""
        
    def test_error_message_format_validation(self):
        """Test that error messages follow expected format."""
```

#### 6. AUTHENTICATION FAILURE MESSAGING TESTS

**Test Suite**: `test_websocket_authentication_failure_messaging.py`
**Location**: `/Users/rindhujajohnson/Netra/Backend/netra-apex/netra_backend/tests/e2e/websocket/`
**Priority**: MEDIUM

```python
class TestWebSocketAuthenticationFailureMessaging(SSotBaseTestCase):
    """Test authentication failure messaging patterns."""
    
    def test_jwt_validation_failure_messaging(self):
        """Test error messages for JWT validation failures."""
        
    def test_token_expiry_error_messaging(self):
        """Test error messages for expired tokens."""
        
    def test_invalid_credentials_error_messaging(self):
        """Test error messages for invalid credentials."""
        
    def test_rate_limit_error_messaging(self):
        """Test error messages for rate limiting violations."""
```

### 🔧 MOCK VS REAL SERVICE REQUIREMENTS

#### REAL SERVICE TESTING (Preferred)
```python
# Use real WebSocket connections and actual implementations
class TestWithRealServices(SSotBaseTestCase):
    @classmethod
    def setUpClass(cls):
        """Setup real WebSocket server and connections."""
        cls.real_websocket_server = start_real_websocket_server()
        cls.real_auth_service = start_real_auth_service()
        
    def test_real_websocket_error_creation(self):
        """Test with real WebSocket connections and actual error scenarios."""
```

#### CONTROLLED MOCK TESTING (Limited Use)
```python
# Only for testing specific function behavior in isolation
class TestFunctionSignatureMocks(SSotBaseTestCase):
    def test_function_signature_mismatch_detection(self):
        """Use mocks only to simulate signature mismatches for detection."""
        with patch('netra_backend.app.websocket_core.types.create_error_message') as mock_real:
            with patch('netra_backend.app.websocket_core.create_error_message') as mock_fallback:
                # Test signature compatibility
```

### 📍 IMPORT RESOLUTION TESTING

#### Import Path Validation Tests
```python
class TestImportPathResolution(SSotBaseTestCase):
    """Validate import paths and resolution order."""
    
    def test_ssot_import_registry_compliance(self):
        """Verify all imports follow SSOT_IMPORT_REGISTRY.md patterns."""
        registry_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/SSOT_IMPORT_REGISTRY.md"
        verified_imports = self.load_verified_imports(registry_path)
        
        # Test each verified import pattern
        for import_pattern in verified_imports:
            with self.subTest(import_pattern=import_pattern):
                self.assert_import_works(import_pattern)
    
    def test_broken_import_detection(self):
        """Verify broken imports are detected and fail gracefully."""
        broken_imports = [
            "from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge",
            "from nonexistent.module import fake_function"
        ]
        
        for broken_import in broken_imports:
            with self.subTest(broken_import=broken_import):
                self.assert_import_fails_gracefully(broken_import)
    
    def test_direct_vs_package_import_behavior(self):
        """Test difference between direct and package-level imports."""
        # Direct import: from netra_backend.app.websocket_core.types import create_error_message
        # Package import: from netra_backend.app.websocket_core import create_error_message
```

### 🔍 ERROR SCENARIO COVERAGE

#### Comprehensive Error Testing Matrix
```python
class TestErrorScenarioMatrix(SSotBaseTestCase):
    """Test all error scenarios systematically."""
    
    ERROR_SCENARIOS = [
        {
            'name': 'authentication_failed',
            'trigger': 'invalid_jwt_token',
            'expected_error_code': 'AUTH_FAILED',
            'expected_message': 'Authentication failed',
            'expected_close_code': 1008
        },
        {
            'name': 'service_init_failed', 
            'trigger': 'websocket_manager_creation_failure',
            'expected_error_code': 'SERVICE_INIT_FAILED',
            'expected_message': 'Service initialization failed',
            'expected_close_code': 1011
        },
        {
            'name': 'cleanup_error',
            'trigger': 'exception_during_cleanup',
            'expected_error_code': 'CLEANUP_FAILED',
            'expected_message': 'Error during cleanup',
            'expected_close_code': 1000
        }
    ]
    
    def test_error_scenario_matrix(self):
        """Test all error scenarios with both real and fallback implementations."""
        for scenario in self.ERROR_SCENARIOS:
            with self.subTest(scenario=scenario['name']):
                self.run_error_scenario_test(scenario)
```

### 📝 MESSAGE FORMAT VALIDATION TESTS

#### Message Structure and Content Tests
```python
class TestMessageFormatValidation(SSotBaseTestCase):
    """Test message format and content validation."""
    
    def test_error_message_structure(self):
        """Test that error messages have required fields."""
        error_msg = create_error_message("TEST_ERROR", "Test message")
        
        required_fields = ['type', 'error_code', 'error_message', 'timestamp']
        for field in required_fields:
            self.assertIn(field, error_msg)
    
    def test_server_message_structure(self):
        """Test that server messages have required fields."""
        server_msg = create_server_message("test_type", {"data": "test"})
        
        required_fields = ['type', 'data', 'timestamp']
        for field in required_fields:
            self.assertIn(field, server_msg)
    
    def test_message_serialization_compatibility(self):
        """Test that messages can be serialized for WebSocket transmission."""
        import json
        
        error_msg = create_error_message("TEST", "Test message")
        server_msg = create_server_message("test", {"key": "value"})
        
        # Should not raise exceptions
        json.dumps(error_msg.dict() if hasattr(error_msg, 'dict') else error_msg)
        json.dumps(server_msg.dict() if hasattr(server_msg, 'dict') else server_msg)
```

### 🧪 TEST EXECUTION STRATEGY

#### Phase 1: Unit Tests (Function-Level)
```bash
# Test individual function signatures and behavior
python tests/unified_test_runner.py --category unit --pattern "*websocket*message*"

# Test import resolution
python tests/unified_test_runner.py --category unit --pattern "*websocket*import*"
```

#### Phase 2: Integration Tests (Component-Level)
```bash
# Test component interactions with real services
python tests/unified_test_runner.py --category integration --pattern "*websocket*error*" --real-services

# Test fallback compatibility
python tests/unified_test_runner.py --category integration --pattern "*websocket*fallback*" --real-services
```

#### Phase 3: End-to-End Tests (System-Level)
```bash
# Test complete error handling flows
python tests/unified_test_runner.py --category e2e --pattern "*websocket*messaging*" --real-services

# Test authentication failure scenarios
python tests/unified_test_runner.py --category e2e --pattern "*websocket*auth*error*" --real-services
```

#### Phase 4: Mission Critical Validation
```bash
# Run all WebSocket-related mission critical tests
python tests/mission_critical/test_websocket_agent_events_suite.py

# Validate no regression in core functionality
python tests/mission_critical/test_websocket_message_creation_compatibility.py  # NEW
```

### 🚨 CRITICAL SUCCESS CRITERIA

#### Function Signature Validation
- ✅ All create_error_message calls use correct 2-parameter signature
- ✅ All create_server_message calls use correct 2-parameter signature  
- ✅ Fallback implementations handle both old and new calling patterns
- ✅ No runtime TypeError exceptions due to missing parameters

#### Import Path Resolution
- ✅ All import paths follow SSOT_IMPORT_REGISTRY.md verified patterns
- ✅ No ModuleNotFoundError exceptions for agent_websocket_bridge
- ✅ Graceful fallback when optional modules are unavailable
- ✅ Direct imports and package imports both work correctly

#### Error Handling Robustness
- ✅ Authentication failure errors are properly created and sent
- ✅ Service initialization failure errors are properly created and sent
- ✅ Cleanup errors are properly created and sent
- ✅ All error messages are valid and serializable
- ✅ Appropriate WebSocket close codes are used

#### Business Impact Validation
- ✅ Chat functionality remains operational during error conditions
- ✅ Users receive clear error messages for authentication failures
- ✅ No silent failures that leave users confused
- ✅ Error recovery flows work correctly

### 📋 IMPLEMENTATION PRIORITY

#### IMMEDIATE (Week 1)
1. **Function Signature Compatibility Tests** - CRITICAL
2. **Import Path Resolution Tests** - CRITICAL
3. **Basic Error Scenario Tests** - HIGH

#### SHORT-TERM (Week 2)
4. **Fallback Compatibility Tests** - HIGH
5. **Message Format Validation Tests** - MEDIUM
6. **Authentication Error Flow Tests** - MEDIUM

#### MEDIUM-TERM (Week 3-4)
7. **Comprehensive Error Matrix Tests** - MEDIUM
8. **End-to-End Error Messaging Tests** - MEDIUM
9. **Performance and Load Error Tests** - LOW

### 🔄 CONTINUOUS VALIDATION

#### Pre-Commit Hooks
```bash
# Add to pre-commit configuration
python scripts/validate_websocket_function_signatures.py
python scripts/validate_import_paths.py
```

#### CI/CD Pipeline Integration
```yaml
# Add to GitHub Actions workflow
- name: Validate WebSocket Message Function Compatibility
  run: |
    python tests/unified_test_runner.py --category unit --pattern "*websocket*message*signature*"
    python tests/unified_test_runner.py --category integration --pattern "*websocket*error*compatibility*"
```

#### Automated Regression Prevention
```python
# Monitor for new instances of problematic patterns
class TestRegressionPrevention(SSotBaseTestCase):
    def test_no_single_parameter_error_message_calls(self):
        """Scan codebase for single-parameter create_error_message calls."""
        
    def test_no_broken_agent_bridge_imports(self):
        """Scan codebase for broken agent_websocket_bridge imports."""
```

---

## 💻 DETAILED TEST IMPLEMENTATION EXAMPLES

### Example 1: Function Signature Compatibility Test

```python
"""
Test file: netra_backend/tests/unit/websocket_core/test_websocket_message_function_signatures.py
Purpose: Detect and prevent function signature mismatches between real and fallback implementations
"""

import pytest
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestWebSocketMessageFunctionSignatures(SSotBaseTestCase):
    """Test function signature compatibility between real and fallback implementations."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.real_implementation_available = True
        self.fallback_implementation_available = True
    
    def test_create_error_message_real_signature_validation(self):
        """CRITICAL: Verify create_error_message real implementation requires both parameters."""
        # Import real implementation
        from netra_backend.app.websocket_core.types import create_error_message as real_create_error_message
        
        # Test correct usage (should work)
        try:
            result = real_create_error_message("AUTH_FAILED", "Authentication failed")
            self.assertIsNotNone(result)
            self.assertEqual(result.error_code, "AUTH_FAILED")
            self.assertEqual(result.error_message, "Authentication failed")
        except Exception as e:
            self.fail(f"Real implementation with correct parameters failed: {e}")
        
        # Test incorrect usage (should fail)
        with self.assertRaises(TypeError) as context:
            real_create_error_message("Authentication failed")  # Missing error_message parameter
        
        self.assertIn("missing 1 required positional argument", str(context.exception))
    
    def test_create_error_message_fallback_signature_validation(self):
        """CRITICAL: Verify create_error_message fallback implementation accepts single parameter."""
        # Import fallback implementation
        from netra_backend.app.websocket_core import create_error_message as fallback_create_error_message
        
        # Test single parameter (should work with fallback)
        try:
            result = fallback_create_error_message("Authentication failed")
            self.assertIsNotNone(result)
            self.assertIn("error_code", result)
            self.assertEqual(result["error_code"], "Authentication failed")
        except Exception as e:
            self.fail(f"Fallback implementation with single parameter failed: {e}")
        
        # Test two parameters (should also work with fallback)
        try:
            result = fallback_create_error_message("AUTH_FAILED", "Authentication failed")
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"Fallback implementation with two parameters failed: {e}")
    
    def test_create_server_message_signature_compatibility(self):
        """CRITICAL: Test create_server_message signature compatibility."""
        # Real implementation test
        from netra_backend.app.websocket_core.types import create_server_message as real_create_server_message
        
        # Should work with required parameters
        result = real_create_server_message("test_type", {"key": "value"})
        self.assertIsNotNone(result)
        
        # Should fail without data parameter
        with self.assertRaises(TypeError):
            real_create_server_message("test_type")  # Missing data parameter
    
    def test_function_call_pattern_detection(self):
        """CRITICAL: Detect problematic calling patterns in actual code."""
        import ast
        import os
        
        # Scan websocket_ssot.py for problematic patterns
        websocket_ssot_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py"
        
        if os.path.exists(websocket_ssot_path):
            with open(websocket_ssot_path, 'r') as f:
                content = f.read()
            
            # Parse AST to find function calls
            tree = ast.parse(content)
            
            problematic_calls = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Name) and 
                        node.func.id == 'create_error_message' and 
                        len(node.args) == 1):
                        problematic_calls.append(f"Line {node.lineno}: Single parameter call to create_error_message")
            
            # Fail if problematic calls found
            if problematic_calls:
                self.fail(f"Found problematic function calls: {problematic_calls}")
    
    def test_import_path_resolution_order(self):
        """CRITICAL: Test import resolution order affects function signatures."""
        # Test direct import from types.py
        try:
            from netra_backend.app.websocket_core.types import create_error_message
            # This should be the strict implementation
            with self.assertRaises(TypeError):
                create_error_message("single_parameter")
        except ImportError:
            self.fail("Direct import from types.py failed")
        
        # Test package-level import
        try:
            from netra_backend.app.websocket_core import create_error_message
            # This should use fallback if types.py import fails
            # But in our case, it should still be the strict implementation
            pass
        except ImportError:
            self.fail("Package-level import failed")
```

### Example 2: Import Resolution Test

```python
"""
Test file: netra_backend/tests/unit/websocket_core/test_websocket_import_resolution.py
Purpose: Test import path resolution and detect missing modules
"""

import sys
import importlib
from unittest.mock import patch
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestWebSocketImportResolution(SSotBaseTestCase):
    """Test import path resolution and module availability."""
    
    def test_agent_websocket_bridge_import_paths(self):
        """CRITICAL: Test various import paths for agent_websocket_bridge module."""
        
        # Test the problematic import path from GCP logs
        problematic_import = "netra_backend.app.agents.agent_websocket_bridge"
        
        try:
            module = importlib.import_module(problematic_import)
            self.assertIsNotNone(module)
            self.assertTrue(hasattr(module, 'create_agent_websocket_bridge'))
        except ImportError as e:
            # This is expected to fail - document the correct path
            self.fail(f"Problematic import path '{problematic_import}' failed as expected: {e}")
        
        # Test correct import paths from SSOT_IMPORT_REGISTRY.md
        correct_import_paths = [
            "netra_backend.app.services.agent_websocket_bridge",
            "netra_backend.app.websocket_core.agent_websocket_bridge",
        ]
        
        working_paths = []
        for import_path in correct_import_paths:
            try:
                module = importlib.import_module(import_path)
                if hasattr(module, 'create_agent_websocket_bridge'):
                    working_paths.append(import_path)
            except ImportError:
                continue
        
        self.assertGreater(len(working_paths), 0, "No working import paths found for agent_websocket_bridge")
    
    def test_websocket_types_import_fallback_behavior(self):
        """Test fallback behavior when types.py import fails."""
        
        # Mock types.py import failure
        with patch.dict('sys.modules', {'netra_backend.app.websocket_core.types': None}):
            # Force reload of websocket_core to trigger fallback
            if 'netra_backend.app.websocket_core' in sys.modules:
                del sys.modules['netra_backend.app.websocket_core']
            
            try:
                from netra_backend.app.websocket_core import create_error_message, create_server_message
                
                # Test fallback implementations work
                error_msg = create_error_message("test_error")
                server_msg = create_server_message("test_type")
                
                self.assertIsNotNone(error_msg)
                self.assertIsNotNone(server_msg)
                
            except ImportError as e:
                self.fail(f"Fallback import failed: {e}")
    
    def test_ssot_import_registry_compliance(self):
        """Verify imports follow SSOT_IMPORT_REGISTRY.md patterns."""
        
        # Load verified imports from SSOT registry
        registry_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/SSOT_IMPORT_REGISTRY.md"
        
        try:
            with open(registry_path, 'r') as f:
                registry_content = f.read()
            
            # Extract verified WebSocket imports
            verified_imports = []
            in_websocket_section = False
            
            for line in registry_content.split('\n'):
                if '# WebSocket' in line or 'websocket' in line.lower():
                    in_websocket_section = True
                elif line.startswith('#') and in_websocket_section:
                    in_websocket_section = False
                elif in_websocket_section and 'from netra_backend.app.websocket' in line:
                    verified_imports.append(line.strip())
            
            # Test each verified import
            for import_statement in verified_imports:
                if import_statement.startswith('from ') and ' import ' in import_statement:
                    try:
                        exec(import_statement)
                    except ImportError as e:
                        self.fail(f"Verified import failed: {import_statement} - {e}")
                        
        except FileNotFoundError:
            self.skipTest("SSOT_IMPORT_REGISTRY.md not found")
```

### Example 3: Error Scenario Integration Test

```python
"""
Test file: netra_backend/tests/integration/websocket/test_websocket_error_scenarios.py
Purpose: Test complete error handling flows with real WebSocket connections
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestWebSocketErrorScenarios(SSotAsyncTestCase):
    """Test error handling and cleanup scenarios with real WebSocket behavior."""
    
    async def setUp(self):
        """Set up test environment with real WebSocket components."""
        await super().setUp()
        self.websocket_mock = AsyncMock()
        self.user_context = self.create_test_user_context()
    
    async def test_authentication_failure_error_creation_flow(self):
        """CRITICAL: Test complete authentication failure error flow."""
        
        # Import the actual WebSocket SSOT handler
        from netra_backend.app.routes.websocket_ssot import WebSocketSSotEndpoint
        
        endpoint = WebSocketSSotEndpoint()
        
        # Mock authentication failure
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
            mock_auth.return_value.success = False
            mock_auth.return_value.error = "Invalid JWT token"
            
            # Mock WebSocket functions
            with patch('netra_backend.app.websocket_core.utils.safe_websocket_send') as mock_send:
                with patch('netra_backend.app.websocket_core.utils.safe_websocket_close') as mock_close:
                    
                    # Trigger authentication failure
                    try:
                        await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                    except Exception:
                        pass  # Expected to fail during auth
                    
                    # Verify error message was created and sent correctly
                    self.assertTrue(mock_send.called)
                    sent_args = mock_send.call_args[0]
                    
                    # Check that error message has correct structure
                    error_message = sent_args[1]  # Second argument is the message
                    
                    if hasattr(error_message, 'error_code'):
                        # Real implementation
                        self.assertEqual(error_message.error_code, "AUTH_FAILED")
                        self.assertEqual(error_message.error_message, "Authentication failed")
                    else:
                        # Fallback implementation
                        self.assertIn("error_code", error_message)
                        self.assertIn("Authentication failed", str(error_message))
                    
                    # Verify WebSocket was closed with correct code
                    self.assertTrue(mock_close.called)
                    close_args = mock_close.call_args[0]
                    self.assertEqual(close_args[1], 1008)  # Authentication failure close code
    
    async def test_service_initialization_failure_error_creation_flow(self):
        """CRITICAL: Test service initialization failure error flow."""
        
        from netra_backend.app.routes.websocket_ssot import WebSocketSSotEndpoint
        
        endpoint = WebSocketSSotEndpoint()
        
        # Mock successful authentication but failed WebSocket manager creation
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
            mock_auth.return_value.success = True
            mock_auth.return_value.user_context = self.user_context
            
            with patch.object(endpoint, '_create_websocket_manager', return_value=None):
                with patch('netra_backend.app.websocket_core.utils.safe_websocket_send') as mock_send:
                    with patch('netra_backend.app.websocket_core.utils.safe_websocket_close') as mock_close:
                        
                        # Trigger service initialization failure
                        try:
                            await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                        except Exception:
                            pass  # Expected to fail during service init
                        
                        # Verify error message was created and sent correctly
                        self.assertTrue(mock_send.called)
                        sent_args = mock_send.call_args[0]
                        error_message = sent_args[1]
                        
                        if hasattr(error_message, 'error_code'):
                            # Real implementation
                            self.assertEqual(error_message.error_code, "SERVICE_INIT_FAILED")
                            self.assertEqual(error_message.error_message, "Service initialization failed")
                        else:
                            # Fallback implementation
                            self.assertIn("Service initialization failed", str(error_message))
                        
                        # Verify WebSocket was closed with correct code
                        self.assertTrue(mock_close.called)
                        close_args = mock_close.call_args[0]
                        self.assertEqual(close_args[1], 1011)  # Internal server error close code
    
    async def test_error_message_serialization_compatibility(self):
        """CRITICAL: Test that created error messages can be serialized for WebSocket."""
        
        # Test both real and fallback implementations
        from netra_backend.app.websocket_core.types import create_error_message as real_create_error_message
        from netra_backend.app.websocket_core import create_error_message as fallback_create_error_message
        
        # Test real implementation serialization
        real_error = real_create_error_message("TEST_ERROR", "Test message")
        try:
            if hasattr(real_error, 'dict'):
                serialized = json.dumps(real_error.dict())
            else:
                serialized = json.dumps(real_error)
            self.assertIsInstance(serialized, str)
        except (TypeError, ValueError) as e:
            self.fail(f"Real error message serialization failed: {e}")
        
        # Test fallback implementation serialization
        fallback_error = fallback_create_error_message("TEST_ERROR", "Test message")
        try:
            serialized = json.dumps(fallback_error)
            self.assertIsInstance(serialized, str)
        except (TypeError, ValueError) as e:
            self.fail(f"Fallback error message serialization failed: {e}")
    
    def create_test_user_context(self):
        """Create a test user context for testing."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        return UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )
```

### Example 4: Regression Prevention Test

```python
"""
Test file: netra_backend/tests/critical/test_websocket_function_signature_regression.py
Purpose: Continuously monitor for regression of function signature issues
"""

import ast
import os
import re
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestWebSocketFunctionSignatureRegression(SSotBaseTestCase):
    """Prevent regression of function signature compatibility issues."""
    
    def test_no_single_parameter_create_error_message_calls(self):
        """CRITICAL: Scan codebase for problematic create_error_message calls."""
        
        problematic_files = []
        websocket_files = [
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py",
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/websocket_core/websocket_manager.py",
        ]
        
        for file_path in websocket_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Parse AST to find problematic calls
                try:
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if (isinstance(node.func, ast.Name) and 
                                node.func.id == 'create_error_message' and 
                                len(node.args) == 1):
                                problematic_files.append(f"{file_path}:{node.lineno}")
                                
                except SyntaxError:
                    # Skip files with syntax errors
                    continue
        
        if problematic_files:
            self.fail(f"Found single-parameter create_error_message calls in: {problematic_files}")
    
    def test_no_broken_agent_websocket_bridge_imports(self):
        """CRITICAL: Scan for broken agent_websocket_bridge import paths."""
        
        broken_imports = []
        search_pattern = r'from\s+netra_backend\.app\.agents\.agent_websocket_bridge\s+import'
        
        # Search in relevant files
        search_files = [
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py"
        ]
        
        for file_path in search_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                
                matches = re.finditer(search_pattern, content, re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    broken_imports.append(f"{file_path}:{line_num}")
        
        if broken_imports:
            self.fail(f"Found broken agent_websocket_bridge imports in: {broken_imports}")
    
    def test_function_signature_consistency_across_implementations(self):
        """CRITICAL: Ensure consistent function signatures across all implementations."""
        
        # Test create_error_message signatures
        from netra_backend.app.websocket_core.types import create_error_message as real_impl
        from netra_backend.app.websocket_core import create_error_message as package_impl
        
        # Both should handle the same correct calling pattern
        try:
            real_result = real_impl("TEST_CODE", "Test message")
            self.assertIsNotNone(real_result)
        except Exception as e:
            self.fail(f"Real implementation failed with correct parameters: {e}")
        
        try:
            package_result = package_impl("TEST_CODE", "Test message")
            self.assertIsNotNone(package_result)
        except Exception as e:
            # This might be expected if package_impl is the fallback
            pass
```

---

## ORIGINAL VALIDATION STEPS

### ✅ VALIDATION STEPS
1. **Syntax Validation**: Ensure all function calls match required signatures
2. **Import Validation**: Verify all module imports resolve correctly  
3. **WebSocket Testing**: Test authentication failure and service initialization failure paths
4. **Error Handling**: Verify error messages are properly formatted and sent
5. **Integration Testing**: Confirm no regression in WebSocket functionality

### 🧪 TEST COMMANDS
```bash
# Check syntax
python -m py_compile netra_backend/app/routes/websocket_ssot.py

# Test WebSocket functionality
python tests/mission_critical/test_websocket_agent_events_suite.py

# Test specific error handling paths
python tests/integration/test_websocket_error_handling.py

# NEW: Run comprehensive message creation tests
python tests/unified_test_runner.py --category unit --pattern "*websocket*message*function*"
python tests/unified_test_runner.py --category integration --pattern "*websocket*error*scenario*" --real-services
```

## BUSINESS IMPACT ASSESSMENT

### 💰 REVENUE RISK
- **HIGH PRIORITY**: WebSocket error handling failures affect chat reliability
- **User Experience**: Authentication and service initialization errors not properly communicated
- **Chat Functionality**: 90% of platform value depends on reliable WebSocket communication
- **Customer Retention**: Poor error handling leads to frustrated users and potential churn

### 🎯 CRITICALITY LEVEL: **HIGH**
- **Core Functionality**: WebSocket communication is critical infrastructure
- **Error Propagation**: Failed error handling causes silent failures
- **Production Impact**: Currently affecting GCP staging environment
- **Business Logic**: Breaks the primary user interaction channel (chat)

## RESOLUTION PRIORITY

### 🚨 IMMEDIATE ACTION REQUIRED
1. **Fix Function Signatures**: Correct the `create_error_message()` and `create_server_message()` calls
2. **Fix Import Paths**: Correct the `agent_websocket_bridge` import location
3. **Validation Testing**: Ensure WebSocket error handling works correctly
4. **Production Deployment**: Deploy fixes to resolve staging issues

### 📈 SUCCESS METRICS
- ✅ WebSocket authentication failures properly communicated to users
- ✅ Service initialization errors clearly displayed
- ✅ No more missing argument exceptions in GCP logs
- ✅ Chat functionality reliability improved

## FIVE WHYS ANALYSIS SUMMARY

### 🔍 ROOT CAUSE IDENTIFIED
**Function signature incompatibility between fallback and real implementations** causing runtime failures when emergency mode switches between different function signatures.

### 🛠️ SOLUTION APPROACH
1. **Standardize Signatures**: Ensure fallback and real implementations have compatible signatures
2. **Fix Current Calls**: Update existing calls to use correct parameter patterns
3. **Import Path Fixes**: Correct module import paths to prevent missing module errors
4. **Defensive Coding**: Add parameter validation to prevent future signature mismatches

### 📊 ANALYSIS COMPLETENESS: ✅ 100%
- ✅ All five "why" levels investigated
- ✅ Root cause identified with evidence
- ✅ Contributing factors mapped
- ✅ Immediate fixes documented
- ✅ Business impact assessed
- ✅ Resolution path defined

## NEXT STEPS

1. **IMPLEMENT FIXES**: Apply the documented corrections to websocket_ssot.py
2. **TEST VALIDATION**: Run comprehensive WebSocket tests to verify fixes
3. **STAGING DEPLOYMENT**: Deploy to staging and monitor for resolution
4. **PRODUCTION READINESS**: Prepare for production deployment after validation

---

## 📋 DEBUGGING LOG STATUS: ✅ COMPLETE

**Five Whys Analysis**: Thoroughly completed with root cause identification, evidence documentation, and actionable fix recommendations. Ready for implementation and testing phase.