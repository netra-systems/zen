# SSOT Migration Patterns Library

**Purpose:** Standardized find-and-replace patterns for migrating from direct `os.environ` access to SSOT `IsolatedEnvironment` pattern  
**Issue:** #1124 - SSOT-Testing-Direct-Environment-Access-Golden-Path-Blocker  
**Usage:** Reference guide for atomic SSOT migration changes

## Standard Import Pattern

**Add to every modified file:**
```python
from shared.isolated_environment import get_env
```

## Migration Pattern Categories

### **Category 1: Direct Assignment**

#### Pattern 1.1: Simple Assignment
```python
# FIND:
os.environ['KEY'] = 'value'

# REPLACE WITH:
get_env().set('KEY', 'value', source='test_context')
```

#### Pattern 1.2: Assignment with Variable
```python
# FIND:
os.environ[key_name] = value_variable

# REPLACE WITH:
get_env().set(key_name, value_variable, source='test_context')
```

#### Pattern 1.3: Assignment in Setup/Teardown
```python
# FIND:
def setUp(self):
    os.environ['TEST_VAR'] = 'test_value'

# REPLACE WITH:
def setUp(self):
    get_env().set('TEST_VAR', 'test_value', source='test_setup')
```

### **Category 2: Environment Reading**

#### Pattern 2.1: Simple Get with Default
```python
# FIND:
value = os.environ.get('KEY', 'default')

# REPLACE WITH:
value = get_env().get('KEY', 'default')
```

#### Pattern 2.2: Simple Get without Default
```python
# FIND:
value = os.environ.get('KEY')

# REPLACE WITH:
value = get_env().get('KEY')
```

#### Pattern 2.3: Direct Access with KeyError Risk
```python
# FIND:
value = os.environ['KEY']

# REPLACE WITH:
value = get_env().get('KEY')
# OR for strict behavior:
env = get_env()
if not env.exists('KEY'):
    raise KeyError(f"Environment variable 'KEY' not found")
value = env.get('KEY')
```

#### Pattern 2.4: Environment Check
```python
# FIND:
if 'KEY' in os.environ:

# REPLACE WITH:
if get_env().exists('KEY'):
```

### **Category 3: Environment Deletion**

#### Pattern 3.1: Safe Deletion
```python
# FIND:
if 'KEY' in os.environ:
    del os.environ['KEY']

# REPLACE WITH:
env = get_env()
if env.exists('KEY'):
    env.unset('KEY')
```

#### Pattern 3.2: Direct Deletion
```python
# FIND:
del os.environ['KEY']

# REPLACE WITH:
get_env().unset('KEY')
```

#### Pattern 3.3: Pop with Default
```python
# FIND:
value = os.environ.pop('KEY', 'default')

# REPLACE WITH:
env = get_env()
value = env.get('KEY', 'default')
env.unset('KEY')
```

### **Category 4: Batch Operations**

#### Pattern 4.1: Environment Update
```python
# FIND:
test_env = {'KEY1': 'value1', 'KEY2': 'value2'}
os.environ.update(test_env)

# REPLACE WITH:
test_env = {'KEY1': 'value1', 'KEY2': 'value2'}
get_env().update(test_env, source='test_batch_update')
```

#### Pattern 4.2: Environment Items Iteration
```python
# FIND:
for key, value in os.environ.items():
    if key.startswith('PREFIX_'):
        # process

# REPLACE WITH:
env = get_env()
for key, value in env.get_all().items():
    if key.startswith('PREFIX_'):
        # process
```

### **Category 5: Test Context Management**

#### Pattern 5.1: Test Setup/Teardown with Backup
```python
# FIND:
def setUp(self):
    self.original_value = os.environ.get('KEY')
    os.environ['KEY'] = 'test_value'

def tearDown(self):
    if self.original_value is not None:
        os.environ['KEY'] = self.original_value
    else:
        if 'KEY' in os.environ:
            del os.environ['KEY']

# REPLACE WITH:
def setUp(self):
    self.env = get_env()
    self.env.enable_isolation()
    self.env.set('KEY', 'test_value', source='test_setup')

def tearDown(self):
    self.env.disable_isolation(restore_original=True)
```

#### Pattern 5.2: Context Manager Pattern
```python
# FIND:
original_env = dict(os.environ)
try:
    os.environ['KEY'] = 'test_value'
    # test code
finally:
    os.environ.clear()
    os.environ.update(original_env)

# REPLACE WITH:
env = get_env()
with env:  # Context manager enables/disables isolation
    env.set('KEY', 'test_value', source='test_context')
    # test code
# Automatically restores original environment
```

### **Category 6: Advanced Patterns**

#### Pattern 6.1: Environment Variable Validation
```python
# FIND:
required_vars = ['VAR1', 'VAR2', 'VAR3']
missing_vars = [var for var in required_vars if var not in os.environ]
if missing_vars:
    raise ValueError(f"Missing environment variables: {missing_vars}")

# REPLACE WITH:
env = get_env()
required_vars = ['VAR1', 'VAR2', 'VAR3']
missing_vars = [var for var in required_vars if not env.exists(var)]
if missing_vars:
    raise ValueError(f"Missing environment variables: {missing_vars}")
```

#### Pattern 6.2: Environment Dictionary Creation
```python
# FIND:
config = {
    'host': os.environ.get('HOST', 'localhost'),
    'port': int(os.environ.get('PORT', '8000')),
    'debug': os.environ.get('DEBUG', 'false').lower() == 'true'
}

# REPLACE WITH:
env = get_env()
config = {
    'host': env.get('HOST', 'localhost'),
    'port': int(env.get('PORT', '8000')),
    'debug': env.get('DEBUG', 'false').lower() == 'true'
}
```

## Source Context Guidelines

### **Source Parameter Values**
Use descriptive source values to track where variables are set:

```python
# Test setup contexts
source='test_setup'          # In setUp() methods
source='test_context'        # In test methods  
source='test_teardown'       # In tearDown() methods
source='test_batch_update'   # For batch updates
source='test_validation'     # For validation tests
source='test_isolation'      # For isolated test scenarios

# Specific test contexts
source='websocket_test'      # WebSocket-specific tests
source='auth_test'          # Authentication tests
source='config_test'        # Configuration tests
source='integration_test'   # Integration tests
source='unit_test'          # Unit tests
```

## Special Cases & Considerations

### **Case 1: Mock/Patch Integration**
When tests use `patch.dict(os.environ, {...})`:

```python
# FIND:
@patch.dict(os.environ, {'KEY': 'value'})
def test_method(self):
    # test code

# REPLACE WITH:
def test_method(self):
    env = get_env()
    env.enable_isolation()
    env.set('KEY', 'value', source='test_patch')
    try:
        # test code
    finally:
        env.disable_isolation(restore_original=True)
```

### **Case 2: Multiple Environment Variables**
For tests setting many environment variables:

```python
# FIND:
test_env_vars = {
    'VAR1': 'value1',
    'VAR2': 'value2', 
    'VAR3': 'value3'
}
for key, value in test_env_vars.items():
    os.environ[key] = value

# REPLACE WITH:
test_env_vars = {
    'VAR1': 'value1',
    'VAR2': 'value2',
    'VAR3': 'value3'
}
get_env().update(test_env_vars, source='test_multi_vars')
```

### **Case 3: Conditional Environment Setting**
```python
# FIND:
if condition:
    os.environ['KEY'] = 'conditional_value'
else:
    if 'KEY' in os.environ:
        del os.environ['KEY']

# REPLACE WITH:
env = get_env()
if condition:
    env.set('KEY', 'conditional_value', source='test_conditional')
else:
    env.unset('KEY')
```

## Validation After Migration

### **Immediate Validation Commands**
Run after each file migration:

```bash
# Check for remaining violations
grep -n "os\.environ" [modified_file].py

# Run specific tests
python3 -m pytest [modified_file].py -v

# Validate SSOT compliance
python3 scripts/check_architecture_compliance.py --file [modified_file].py
```

### **Integration Validation**
Run after completing a migration group:

```bash
# Run violation detection tests
python3 -m pytest tests/mission_critical/test_ssot_environment_violations.py -v

# Run affected test categories
python3 tests/unified_test_runner.py --category [category] --no-coverage
```

## Common Pitfalls & Solutions

### **Pitfall 1: Forgetting Source Context**
```python
# WRONG:
get_env().set('KEY', 'value')  # No source tracking

# RIGHT:
get_env().set('KEY', 'value', source='test_context')
```

### **Pitfall 2: Not Using Isolation in Tests**
```python
# WRONG - Can pollute other tests:
def test_something(self):
    get_env().set('KEY', 'value', source='test')
    # test code
    # No cleanup

# RIGHT - Proper isolation:
def test_something(self):
    env = get_env()
    env.enable_isolation()
    env.set('KEY', 'value', source='test')
    try:
        # test code
    finally:
        env.disable_isolation(restore_original=True)
```

### **Pitfall 3: Mixing os.environ and get_env()**
```python
# WRONG - Inconsistent access:
get_env().set('KEY1', 'value1', source='test')
value2 = os.environ.get('KEY2')  # Still using os.environ

# RIGHT - Consistent SSOT access:
env = get_env()
env.set('KEY1', 'value1', source='test')
value2 = env.get('KEY2')
```

## Performance Considerations

### **Optimization 1: Reuse Environment Instance**
```python
# LESS EFFICIENT:
def multiple_operations():
    get_env().set('KEY1', 'value1', source='test')
    get_env().set('KEY2', 'value2', source='test')  
    value = get_env().get('KEY3')

# MORE EFFICIENT:
def multiple_operations():
    env = get_env()
    env.set('KEY1', 'value1', source='test')
    env.set('KEY2', 'value2', source='test')
    value = env.get('KEY3')
```

### **Optimization 2: Batch Updates**
```python
# LESS EFFICIENT:
env = get_env()
env.set('KEY1', 'value1', source='test')
env.set('KEY2', 'value2', source='test')
env.set('KEY3', 'value3', source='test')

# MORE EFFICIENT:
env_vars = {
    'KEY1': 'value1',
    'KEY2': 'value2', 
    'KEY3': 'value3'
}
get_env().update(env_vars, source='test_batch')
```

---

**Usage Instructions:**
1. Identify the pattern category for your specific case
2. Use the exact find/replace pattern
3. Add appropriate source context
4. Validate with provided commands
5. Check for common pitfalls
6. Test functionality after migration

**Reference:** Use this library for all Issue #1124 SSOT migration work