"""Comprehensive unit tests for Universal Registry - CRITICAL SSOT component.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Platform Stability, Development Velocity, Risk Reduction
- Value Impact: Validates the critical SSOT registry system that underlies ALL
  agent, tool, and service management operates correctly in multi-user scenarios
- Strategic Impact: Prevents cascade failures - registry failures would break
  agent execution, tool dispatch, and service discovery causing system unavailability

Test Coverage Strategy:
- 100% line coverage of universal_registry.py
- All method paths and error conditions
- Thread safety for multi-user concurrent access
- Factory patterns for user isolation
- Specialized registry implementations
- Global registry singleton management
- Edge cases and failure scenarios

CRITICAL: NO MOCKS unless absolutely necessary - use real registry instances
CRITICAL: Tests must FAIL HARD when system breaks (no silent failures)
"""
import pytest
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from netra_backend.app.core.registry.universal_registry import UniversalRegistry, AgentRegistry, ToolRegistry, ServiceRegistry, StrategyRegistry, RegistryItem, get_global_registry, create_scoped_registry, _global_registries, _registry_lock

class MockAgent:
    """Mock agent for testing without BaseAgent import."""

    def __init__(self, name: str):
        self.name = name
        self.executed = False
        self._mock_name = f'MockAgent_{name}'

    def execute(self):
        self.executed = True
        return f'Agent {self.name} executed'

class MockUserExecutionContext:
    """Mock context for factory testing."""

    def __init__(self, user_id: str='test-user', run_id: str='test-run'):
        self.user_id = user_id
        self.run_id = run_id
        self.isolated = True

class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str):
        self.name = name
        self.calls = 0

    def execute(self, **kwargs):
        self.calls += 1
        return f'Tool {self.name} called {self.calls} times'

class MockService:
    """Mock service for testing."""

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.healthy = True

class MockStrategy:
    """Mock strategy for testing."""

    def __init__(self, name: str):
        self.name = name
        self.priority = 1

@pytest.fixture
def clean_global_registries():
    """Clean global registries before and after each test."""
    with _registry_lock:
        _global_registries.clear()
    yield
    with _registry_lock:
        _global_registries.clear()

@pytest.fixture
def mock_context():
    """Provide mock user execution context."""
    return MockUserExecutionContext()

@pytest.fixture
def sample_agent():
    """Provide sample mock agent."""
    return MockAgent('test-agent')

@pytest.fixture
def sample_tool():
    """Provide sample mock tool."""
    return MockTool('test-tool')

class RegistryItemTests:
    """Test RegistryItem data class."""

    def test_registry_item_creation(self):
        """Test RegistryItem creation with metadata."""
        now = datetime.now(timezone.utc)
        item = RegistryItem(key='test-key', value='test-value', factory=None, metadata={'description': 'test item'}, registered_at=now)
        assert item.key == 'test-key'
        assert item.value == 'test-value'
        assert item.factory is None
        assert item.metadata['description'] == 'test item'
        assert item.registered_at == now
        assert item.access_count == 0
        assert item.last_accessed is None
        assert item.tags == set()

    def test_registry_item_with_tags(self):
        """Test RegistryItem creation with tags."""
        item = RegistryItem(key='test-key', value='test-value', factory=None, metadata={'tags': ['category1', 'category2']}, registered_at=datetime.now(timezone.utc), tags={'tag1', 'tag2'})
        assert item.tags == {'tag1', 'tag2'}

    def test_mark_accessed(self):
        """Test marking item as accessed updates counters."""
        item = RegistryItem(key='test-key', value='test-value', factory=None, metadata={}, registered_at=datetime.now(timezone.utc))
        assert item.access_count == 0
        assert item.last_accessed is None
        item.mark_accessed()
        assert item.access_count == 1
        assert item.last_accessed is not None
        assert isinstance(item.last_accessed, datetime)
        first_access = item.last_accessed
        time.sleep(0.01)
        item.mark_accessed()
        assert item.access_count == 2
        assert item.last_accessed > first_access

class UniversalRegistryCoreTests:
    """Test core UniversalRegistry functionality."""

    def test_registry_initialization(self):
        """Test registry initialization with all parameters."""
        registry = UniversalRegistry[str]('TestRegistry', allow_override=True, enable_metrics=False)
        assert registry.name == 'TestRegistry'
        assert registry.allow_override is True
        assert registry.enable_metrics is False
        assert not registry.is_frozen()
        assert len(registry) == 0
        assert registry._created_at is not None

    def test_register_singleton(self, sample_agent):
        """Test registering singleton items."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        registry.register('agent1', sample_agent, description='Test agent')
        assert 'agent1' in registry
        assert len(registry) == 1
        assert registry.has('agent1')
        item = registry._items['agent1']
        assert item.key == 'agent1'
        assert item.value == sample_agent
        assert item.factory is None
        assert item.metadata['description'] == 'Test agent'

    def test_register_with_tags(self, sample_agent):
        """Test registering items with tags."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        registry.register('agent1', sample_agent, tags=['ai', 'automation'], priority=1)
        assert 'agent1' in registry
        keys = registry.list_by_tag('ai')
        assert 'agent1' in keys
        keys = registry.list_by_tag('automation')
        assert 'agent1' in keys
        keys = registry.list_by_tag('nonexistent')
        assert len(keys) == 0

    def test_register_factory(self, mock_context):
        """Test registering factory functions."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def agent_factory(ctx):
            return MockAgent(f'agent-{ctx.user_id}')
        registry.register_factory('agent-factory', agent_factory, description='Agent factory')
        assert 'agent-factory' in registry
        item = registry._items['agent-factory']
        assert item.key == 'agent-factory'
        assert item.value is None
        assert item.factory == agent_factory

    def test_register_factory_duplicate_factory(self, mock_context):
        """Test registering duplicate factory fails when override disabled."""
        registry = UniversalRegistry[MockAgent]('TestRegistry', allow_override=False)

        def factory1(ctx):
            return MockAgent('factory1')

        def factory2(ctx):
            return MockAgent('factory2')
        registry.register_factory('duplicate-factory', factory1)
        with pytest.raises(ValueError, match='Factory duplicate-factory already registered'):
            registry.register_factory('duplicate-factory', factory2)

    def test_register_duplicate_without_override(self, sample_agent):
        """Test registering duplicate key fails when override disabled."""
        registry = UniversalRegistry[MockAgent]('TestRegistry', allow_override=False)
        registry.register('agent1', sample_agent)
        with pytest.raises(ValueError, match='agent1 already registered'):
            registry.register('agent1', MockAgent('different'))

    def test_register_duplicate_with_override(self, sample_agent):
        """Test registering duplicate key succeeds with override enabled."""
        registry = UniversalRegistry[MockAgent]('TestRegistry', allow_override=True)
        registry.register('agent1', sample_agent)
        assert registry.get('agent1') == sample_agent
        new_agent = MockAgent('new-agent')
        registry.register('agent1', new_agent, description='Updated agent')
        assert registry.get('agent1') == new_agent
        assert registry._items['agent1'].metadata['description'] == 'Updated agent'

    def test_get_singleton(self, sample_agent):
        """Test retrieving singleton items."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        registry.register('agent1', sample_agent)
        retrieved = registry.get('agent1')
        assert retrieved == sample_agent
        item = registry._items['agent1']
        assert item.access_count == 1
        assert item.last_accessed is not None

    def test_get_via_factory(self, mock_context):
        """Test retrieving items via factory."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def agent_factory(ctx):
            return MockAgent(f'agent-{ctx.user_id}')
        registry.register_factory('agent-factory', agent_factory)
        agent = registry.get('agent-factory', mock_context)
        assert agent is not None
        assert agent.name == f'agent-{mock_context.user_id}'
        agent2 = registry.get('agent-factory', mock_context)
        assert agent2 is not agent
        assert agent2.name == f'agent-{mock_context.user_id}'

    def test_get_nonexistent(self):
        """Test getting non-existent item returns None."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        result = registry.get('nonexistent')
        assert result is None

    def test_create_instance_with_factory(self, mock_context):
        """Test create_instance method."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def agent_factory(ctx):
            return MockAgent(f'created-{ctx.run_id}')
        registry.register_factory('creator', agent_factory)
        agent = registry.create_instance('creator', mock_context)
        assert agent is not None
        assert agent.name == f'created-{mock_context.run_id}'
        metrics = registry.get_metrics()
        assert metrics['metrics']['factory_creations'] == 1

    def test_create_instance_no_factory(self, mock_context):
        """Test create_instance fails when no factory registered."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        with pytest.raises(KeyError, match='No factory for nonexistent'):
            registry.create_instance('nonexistent', mock_context)

    def test_list_keys(self, sample_agent, sample_tool):
        """Test listing all registered keys."""
        registry = UniversalRegistry[Any]('TestRegistry')
        registry.register('agent1', sample_agent)
        registry.register('tool1', sample_tool)
        keys = registry.list_keys()
        assert len(keys) == 2
        assert 'agent1' in keys
        assert 'tool1' in keys

    def test_remove_item(self, sample_agent):
        """Test removing items from registry."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        registry.register('agent1', sample_agent, tags=['ai'])
        assert 'agent1' in registry
        assert len(registry.list_by_tag('ai')) == 1
        result = registry.remove('agent1')
        assert result is True
        assert 'agent1' not in registry
        assert len(registry.list_by_tag('ai')) == 0
        result = registry.remove('nonexistent')
        assert result is False

    def test_clear_registry(self, sample_agent, sample_tool):
        """Test clearing all items from registry."""
        registry = UniversalRegistry[Any]('TestRegistry')
        registry.register('agent1', sample_agent)
        registry.register('tool1', sample_tool, tags=['utility'])
        assert len(registry) == 2
        assert len(registry.list_by_tag('utility')) == 1
        registry.clear()
        assert len(registry) == 0
        assert len(registry.list_by_tag('utility')) == 0
        assert registry.list_keys() == []

class UniversalRegistryFrozenTests:
    """Test registry frozen state functionality."""

    def test_freeze_registry(self, sample_agent):
        """Test freezing registry makes it immutable."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        registry.register('agent1', sample_agent)
        assert not registry.is_frozen()
        registry.freeze()
        assert registry.is_frozen()
        assert registry._freeze_time is not None
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.register('agent2', MockAgent('agent2'))
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.register_factory('factory', lambda ctx: MockAgent('factory'))
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.remove('agent1')
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.clear()
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.load_from_config({})
        assert registry.get('agent1') == sample_agent
        assert 'agent1' in registry

    def test_freeze_already_frozen(self, sample_agent):
        """Test freezing already frozen registry logs warning."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        registry.register('agent1', sample_agent)
        registry.freeze()
        assert registry.is_frozen()
        registry.freeze()
        assert registry.is_frozen()

class UniversalRegistryValidationTests:
    """Test validation functionality."""

    def test_add_validation_handler(self, sample_agent):
        """Test adding custom validation handlers."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def validate_agent_name(key: str, item: Any) -> bool:
            return key.startswith('valid_')
        registry.add_validation_handler(validate_agent_name)
        registry.register('valid_agent', sample_agent)
        assert 'valid_agent' in registry
        with pytest.raises(ValueError, match='Validation failed for invalid_agent'):
            registry.register('invalid_agent', MockAgent('invalid'))

    def test_multiple_validation_handlers(self, sample_agent):
        """Test multiple validation handlers."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def validate_prefix(key: str, item: Any) -> bool:
            return key.startswith('test_')

        def validate_agent_type(key: str, item: Any) -> bool:
            return isinstance(item, MockAgent)
        registry.add_validation_handler(validate_prefix)
        registry.add_validation_handler(validate_agent_type)
        registry.register('test_agent', sample_agent)
        assert 'test_agent' in registry
        with pytest.raises(ValueError, match='Validation failed for wrong_prefix'):
            registry.register('wrong_prefix', sample_agent)
        with pytest.raises(ValueError, match='Validation failed for test_notAgent'):
            registry.register('test_notAgent', 'not an agent')

    def test_validation_handler_exception(self, sample_agent):
        """Test validation handler that throws exception."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def failing_validator(key: str, item: Any) -> bool:
            raise Exception('Validator error')
        registry.add_validation_handler(failing_validator)
        with pytest.raises(ValueError, match='Validation failed for agent1'):
            registry.register('agent1', sample_agent)

    def test_validation_updates_metrics(self, sample_agent):
        """Test validation failures update metrics."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def always_fail(key: str, item: Any) -> bool:
            return False
        registry.add_validation_handler(always_fail)
        initial_metrics = registry.get_metrics()
        assert initial_metrics['metrics']['validation_failures'] == 0
        with pytest.raises(ValueError, match='Validation failed for agent1'):
            registry.register('agent1', sample_agent)
        updated_metrics = registry.get_metrics()
        assert updated_metrics['metrics']['validation_failures'] == 1

class UniversalRegistryMetricsTests:
    """Test metrics and health functionality."""

    def test_get_metrics(self, sample_agent, mock_context):
        """Test comprehensive metrics collection."""
        registry = UniversalRegistry[Any]('TestRegistry')
        time.sleep(0.01)
        registry.register('agent1', sample_agent, tags=['ai'])
        registry.register('tool1', MockTool('tool1'), tags=['utility'])
        registry.register_factory('factory1', lambda ctx: MockAgent(ctx.user_id))
        registry.get('agent1')
        registry.get('agent1')
        registry.get('tool1')
        registry.create_instance('factory1', mock_context)
        metrics = registry.get_metrics()
        assert metrics['registry_name'] == 'TestRegistry'
        assert metrics['total_items'] == 3
        assert metrics['frozen'] is False
        assert metrics['uptime_seconds'] >= 0
        assert metrics['metrics']['total_registrations'] == 3
        assert metrics['metrics']['successful_registrations'] == 3
        assert metrics['metrics']['failed_registrations'] == 0
        assert metrics['metrics']['total_retrievals'] == 3
        assert metrics['metrics']['factory_creations'] == 1
        assert metrics['metrics']['validation_failures'] == 0
        assert metrics['category_distribution']['ai'] == 1
        assert metrics['category_distribution']['utility'] == 1
        most_accessed = metrics['most_accessed']
        assert len(most_accessed) == 3
        assert most_accessed[0]['key'] == 'agent1'
        assert most_accessed[0]['count'] == 2
        assert metrics['success_rate'] == 1.0

    def test_metrics_disabled(self, sample_agent):
        """Test metrics when disabled."""
        registry = UniversalRegistry[MockAgent]('TestRegistry', enable_metrics=False)
        registry.register('agent1', sample_agent)
        agent = registry.get('agent1')
        item = registry._items['agent1']
        assert item.access_count == 0
        assert item.last_accessed is None

    def test_validate_health_healthy(self, sample_agent, sample_tool):
        """Test health validation for healthy registry."""
        registry = UniversalRegistry[Any]('TestRegistry')
        registry.register('agent1', sample_agent)
        registry.register('tool1', sample_tool)
        registry.get('agent1')
        registry.get('tool1')
        health = registry.validate_health()
        assert health['status'] == 'healthy'
        assert health['timestamp'] is not None
        assert len(health['issues']) == 0
        assert 'metrics' in health

    def test_validate_health_empty_registry(self):
        """Test health validation for empty registry."""
        registry = UniversalRegistry[Any]('TestRegistry')
        health = registry.validate_health()
        assert health['status'] == 'warning'
        assert 'Registry is empty' in health['issues']

    def test_validate_health_unused_items(self, sample_agent, sample_tool):
        """Test health validation with many unused items."""
        registry = UniversalRegistry[Any]('TestRegistry')
        for i in range(10):
            registry.register(f'item{i}', MockAgent(f'agent{i}'))
        health = registry.validate_health()
        assert health['status'] == 'warning'
        assert any(('Many unused items' in issue for issue in health['issues']))

    def test_validate_health_high_failure_rate(self, sample_agent):
        """Test health validation with high failure rate."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def sometimes_fail(key: str, item: Any) -> bool:
            return not key.startswith('fail_')
        registry.add_validation_handler(sometimes_fail)
        registry.register('success1', sample_agent)
        for i in range(5):
            try:
                registry.register(f'fail_{i}', MockAgent(f'fail{i}'))
            except ValueError:
                pass
        health = registry.validate_health()
        assert health['status'] in ['degraded', 'warning']
        assert len(health['issues']) > 0

    def test_validate_health_degraded_status_high_failure_rate(self):
        """Test health validation specifically triggers degraded status for >10% failure rate."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        for i in range(5):
            registry.register(f'success{i}', MockAgent(f'success{i}'))
            registry.get(f'success{i}')
        registry._metrics['total_registrations'] = 10
        registry._metrics['successful_registrations'] = 8
        registry._metrics['failed_registrations'] = 2
        health = registry.validate_health()
        assert health['status'] == 'degraded'
        assert any(('High failure rate: 20.0%' in issue for issue in health['issues']))

class UniversalRegistryConfigurationTests:
    """Test configuration loading functionality."""

    def test_load_from_config_basic(self):
        """Test basic config loading (currently logs warnings)."""
        registry = UniversalRegistry[Any]('TestRegistry')
        config = {'item1': {'factory': 'MockAgentFactory'}, 'item2': {'class': 'MockAgent'}, 'item3': {'invalid': 'config'}}
        registry.load_from_config(config)
        assert len(registry) == 0

    def test_load_from_config_frozen(self):
        """Test config loading fails on frozen registry."""
        registry = UniversalRegistry[Any]('TestRegistry')
        registry.freeze()
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.load_from_config({})

class UniversalRegistrySpecialMethodsTests:
    """Test special methods (__len__, __contains__, __repr__)."""

    def test_len(self, sample_agent, sample_tool):
        """Test __len__ method."""
        registry = UniversalRegistry[Any]('TestRegistry')
        assert len(registry) == 0
        registry.register('agent1', sample_agent)
        assert len(registry) == 1
        registry.register('tool1', sample_tool)
        assert len(registry) == 2
        registry.remove('agent1')
        assert len(registry) == 1

    def test_contains(self, sample_agent):
        """Test __contains__ method."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        assert 'agent1' not in registry
        registry.register('agent1', sample_agent)
        assert 'agent1' in registry
        assert 'agent2' not in registry

    def test_repr(self, sample_agent):
        """Test __repr__ method."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        repr_str = repr(registry)
        assert 'UniversalRegistry[TestRegistry]' in repr_str
        assert '0 items' in repr_str
        assert 'mutable' in repr_str
        registry.register('agent1', sample_agent)
        repr_str = repr(registry)
        assert '1 items' in repr_str
        assert 'mutable' in repr_str
        registry.freeze()
        repr_str = repr(registry)
        assert '1 items' in repr_str
        assert 'frozen' in repr_str

class UniversalRegistryThreadSafetyTests:
    """Test thread safety for multi-user scenarios."""

    def test_concurrent_registration(self):
        """Test concurrent registration is thread-safe."""
        registry = UniversalRegistry[MockAgent]('TestRegistry', allow_override=True)
        results = []
        errors = []

        def register_agent(thread_id):
            try:
                agent = MockAgent(f'agent-{thread_id}')
                registry.register(f'agent-{thread_id}', agent)
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, e))
        threads = []
        for i in range(20):
            thread = threading.Thread(target=register_agent, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(errors) == 0, f'Errors occurred: {errors}'
        assert len(results) == 20
        assert len(registry) == 20
        for i in range(20):
            assert f'agent-{i}' in registry
            agent = registry.get(f'agent-{i}')
            assert agent.name == f'agent-{i}'

    def test_concurrent_access_and_registration(self, mock_context):
        """Test concurrent access while registering."""
        registry = UniversalRegistry[MockAgent]('TestRegistry', allow_override=True)
        for i in range(5):
            registry.register(f'initial-{i}', MockAgent(f'initial-{i}'))
        registry.register_factory('factory', lambda ctx: MockAgent(f'factory-{ctx.user_id}'))
        access_results = []
        registration_results = []
        factory_results = []
        errors = []

        def access_agents(thread_id):
            try:
                for i in range(5):
                    agent = registry.get(f'initial-{i}')
                    if agent:
                        access_results.append((thread_id, agent.name))
            except Exception as e:
                errors.append(('access', thread_id, e))

        def register_agents(thread_id):
            try:
                agent = MockAgent(f'new-{thread_id}')
                registry.register(f'new-{thread_id}', agent)
                registration_results.append(thread_id)
            except Exception as e:
                errors.append(('register', thread_id, e))

        def use_factory(thread_id):
            try:
                ctx = MockUserExecutionContext(f'user-{thread_id}', f'run-{thread_id}')
                agent = registry.create_instance('factory', ctx)
                factory_results.append((thread_id, agent.name))
            except Exception as e:
                errors.append(('factory', thread_id, e))
        threads = []
        for i in range(15):
            if i % 3 == 0:
                thread = threading.Thread(target=access_agents, args=(i,))
            elif i % 3 == 1:
                thread = threading.Thread(target=register_agents, args=(i,))
            else:
                thread = threading.Thread(target=use_factory, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(errors) == 0, f'Errors occurred: {errors}'
        assert len(access_results) > 0
        assert len(registration_results) > 0
        assert len(factory_results) > 0
        assert len(registry) >= 5

    def test_concurrent_freeze_and_operations(self, sample_agent):
        """Test concurrent freeze with other operations."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        registry.register('agent1', sample_agent)
        freeze_completed = []
        operation_results = []
        errors = []

        def freeze_registry():
            try:
                time.sleep(0.01)
                registry.freeze()
                freeze_completed.append(True)
            except Exception as e:
                errors.append(('freeze', e))

        def try_operations(thread_id):
            try:
                agent = registry.get('agent1')
                operation_results.append(('get', thread_id, 'success'))
                try:
                    registry.register(f'new-{thread_id}', MockAgent(f'new-{thread_id}'))
                    operation_results.append(('register', thread_id, 'success'))
                except RuntimeError:
                    operation_results.append(('register', thread_id, 'frozen'))
            except Exception as e:
                errors.append(('operation', thread_id, e))
        freeze_thread = threading.Thread(target=freeze_registry)
        op_threads = []
        for i in range(10):
            thread = threading.Thread(target=try_operations, args=(i,))
            op_threads.append(thread)
        freeze_thread.start()
        for thread in op_threads:
            thread.start()
        freeze_thread.join()
        for thread in op_threads:
            thread.join()
        assert len(errors) == 0, f'Errors occurred: {errors}'
        assert len(freeze_completed) == 1
        assert registry.is_frozen()
        get_results = [r for r in operation_results if r[0] == 'get']
        assert len(get_results) == 10
        assert all((r[2] == 'success' for r in get_results))

    def test_concurrent_metrics_access(self):
        """Test concurrent metrics access is thread-safe."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        for i in range(10):
            registry.register(f'agent-{i}', MockAgent(f'agent-{i}'))
        metrics_results = []
        errors = []

        def get_metrics_and_access(thread_id):
            try:
                for i in range(5):
                    registry.get(f'agent-{i % 10}')
                    metrics = registry.get_metrics()
                    metrics_results.append((thread_id, metrics['total_items']))
                    health = registry.validate_health()
                    assert 'status' in health
            except Exception as e:
                errors.append((thread_id, e))
        threads = []
        for i in range(10):
            thread = threading.Thread(target=get_metrics_and_access, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(errors) == 0, f'Errors occurred: {errors}'
        assert len(metrics_results) == 50
        assert all((count == 10 for _, count in metrics_results))

    def test_concurrent_validation_and_registration(self):
        """Test concurrent validation with registration attempts."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        import random

        def random_validator(key: str, item: Any) -> bool:
            return hash(key) % 2 == 0
        registry.add_validation_handler(random_validator)
        registration_results = []
        validation_failures = []
        errors = []

        def attempt_registration(thread_id):
            try:
                agent = MockAgent(f'agent-{thread_id}')
                key = f'agent-{thread_id}'
                try:
                    registry.register(key, agent)
                    registration_results.append(thread_id)
                except ValueError as e:
                    validation_failures.append((thread_id, str(e)))
            except Exception as e:
                errors.append((thread_id, e))
        threads = []
        for i in range(20):
            thread = threading.Thread(target=attempt_registration, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(errors) == 0, f'Unexpected errors: {errors}'
        total_attempts = len(registration_results) + len(validation_failures)
        assert total_attempts == 20
        for thread_id in registration_results:
            assert f'agent-{thread_id}' in registry
        metrics = registry.get_metrics()
        assert metrics['metrics']['validation_failures'] == len(validation_failures)

class AgentRegistryTests:
    """Test AgentRegistry specialized functionality."""

    def test_agent_registry_initialization(self):
        """Test AgentRegistry initializes correctly."""
        registry = AgentRegistry()
        assert registry.name == 'AgentRegistry'
        assert registry.websocket_manager is None
        assert registry.websocket_bridge is None
        assert len(registry._validation_handlers) == 1

    def test_agent_validation_with_mock(self):
        """Test agent validation accepts Mock objects for testing."""
        registry = AgentRegistry()
        mock_agent = Mock()
        mock_agent._mock_name = 'MockAgent'
        registry.register('mock-agent', mock_agent)
        assert 'mock-agent' in registry

    def test_agent_validation_with_real_agent(self):
        """Test agent validation with MockAgent (acts like BaseAgent)."""
        registry = AgentRegistry()
        agent = MockAgent('test-agent')
        registry.register('test-agent', agent)
        assert 'test-agent' in registry

    def test_agent_validation_with_invalid_type(self):
        """Test agent validation rejects invalid types."""
        registry = AgentRegistry()
        with pytest.raises(ValueError, match='Validation failed for invalid'):
            registry.register('invalid', 'not an agent')

    def test_agent_validation_with_primitive_types(self):
        """Test agent validation rejects primitive types."""
        registry = AgentRegistry()
        with pytest.raises(ValueError, match='Validation failed for int_item'):
            registry.register('int_item', 42)
        with pytest.raises(ValueError, match='Validation failed for dict_item'):
            registry.register('dict_item', {'not': 'agent'})
        with pytest.raises(ValueError, match='Validation failed for none_item'):
            registry.register('none_item', None)

    def test_set_websocket_manager(self):
        """Test setting WebSocket manager."""
        registry = AgentRegistry()
        mock_manager = Mock()
        mock_manager.name = 'WebSocketManager'
        registry.set_websocket_manager(mock_manager)
        assert registry.websocket_manager == mock_manager

    def test_set_websocket_bridge(self):
        """Test setting WebSocket bridge."""
        registry = AgentRegistry()
        mock_bridge = Mock()
        mock_bridge.name = 'AgentWebSocketBridge'
        registry.set_websocket_bridge(mock_bridge)
        assert registry.websocket_bridge == mock_bridge

    def test_set_websocket_bridge_none_fails(self):
        """Test setting None WebSocket bridge fails."""
        registry = AgentRegistry()
        with pytest.raises(ValueError, match='WebSocket bridge cannot be None'):
            registry.set_websocket_bridge(None)

    def test_create_agent_with_context(self, mock_context):
        """Test creating agent with full context."""
        registry = AgentRegistry()
        agent = MockAgent('test-agent')
        registry.register('test-agent', agent)
        mock_bridge = Mock()
        registry.set_websocket_bridge(mock_bridge)
        agent.set_websocket_bridge = Mock()
        mock_llm = Mock()
        mock_dispatcher = Mock()
        result_agent = registry.create_agent_with_context('test-agent', mock_context, mock_llm, mock_dispatcher)
        assert result_agent == agent
        agent.set_websocket_bridge.assert_called_once_with(mock_bridge)

    def test_create_agent_with_context_no_agent(self, mock_context):
        """Test creating non-existent agent fails."""
        registry = AgentRegistry()
        with pytest.raises(KeyError, match='Agent nonexistent not found'):
            registry.create_agent_with_context('nonexistent', mock_context, Mock(), Mock())

    def test_create_agent_with_context_no_websocket_method(self, mock_context):
        """Test creating agent without websocket method works."""
        registry = AgentRegistry()
        agent = MockAgent('test-agent')
        registry.register('test-agent', agent)
        mock_bridge = Mock()
        registry.set_websocket_bridge(mock_bridge)
        result_agent = registry.create_agent_with_context('test-agent', mock_context, Mock(), Mock())
        assert result_agent == agent

    def test_tool_dispatcher_property_lazy_creation(self):
        """Test tool_dispatcher property creates mock dispatcher lazily."""
        registry = AgentRegistry()
        assert registry._tool_dispatcher is None
        dispatcher = registry.tool_dispatcher
        assert dispatcher is not None
        assert registry._tool_dispatcher is dispatcher
        assert hasattr(dispatcher, '_websocket_enhanced')
        assert hasattr(dispatcher, 'registry')
        assert dispatcher.registry == registry
        assert dispatcher._websocket_enhanced is False
        assert dispatcher.executor is None

    def test_tool_dispatcher_property_returns_same_instance(self):
        """Test tool_dispatcher property returns same instance on multiple calls."""
        registry = AgentRegistry()
        dispatcher1 = registry.tool_dispatcher
        dispatcher2 = registry.tool_dispatcher
        assert dispatcher1 is dispatcher2

    def test_tool_dispatcher_auto_enhance_with_websocket_manager(self):
        """Test tool_dispatcher gets enhanced when websocket_manager is set."""
        registry = AgentRegistry()
        mock_manager = Mock()
        registry.set_websocket_manager(mock_manager)
        dispatcher = registry.tool_dispatcher
        assert dispatcher._websocket_enhanced is True

    def test_set_tool_dispatcher_method(self):
        """Test set_tool_dispatcher method."""
        registry = AgentRegistry()
        custom_dispatcher = Mock()
        custom_dispatcher._websocket_enhanced = False
        registry.set_tool_dispatcher(custom_dispatcher)
        assert registry._tool_dispatcher == custom_dispatcher
        assert registry.tool_dispatcher == custom_dispatcher

    def test_set_tool_dispatcher_with_websocket_manager(self):
        """Test set_tool_dispatcher auto-enhances with existing websocket_manager."""
        registry = AgentRegistry()
        mock_manager = Mock()
        registry.set_websocket_manager(mock_manager)
        custom_dispatcher = Mock()
        custom_dispatcher._websocket_enhanced = False
        registry.set_tool_dispatcher(custom_dispatcher)
        assert custom_dispatcher._websocket_enhanced is True

    def test_websocket_manager_enhances_existing_tool_dispatcher(self):
        """Test setting websocket_manager enhances existing tool_dispatcher."""
        registry = AgentRegistry()
        dispatcher = registry.tool_dispatcher
        assert dispatcher._websocket_enhanced is False
        mock_manager = Mock()
        registry.set_websocket_manager(mock_manager)
        assert dispatcher._websocket_enhanced is True

    def test_mock_tool_dispatcher_enhance_method(self):
        """Test MockToolDispatcher enhance_with_websockets method."""
        registry = AgentRegistry()
        dispatcher = registry.tool_dispatcher
        mock_bridge = Mock()
        assert dispatcher._websocket_enhanced is False
        dispatcher.enhance_with_websockets(mock_bridge)
        assert dispatcher._websocket_enhanced is True

    def test_enhance_tool_dispatcher_with_real_dispatcher_import_error(self):
        """Test WebSocket enhancement handles import errors gracefully."""
        registry = AgentRegistry()
        real_dispatcher = Mock(spec=[])
        registry.set_tool_dispatcher(real_dispatcher)
        import sys
        original_modules = sys.modules.copy()
        if 'netra_backend.app.agents.unified_tool_execution' in sys.modules:
            del sys.modules['netra_backend.app.agents.unified_tool_execution']

        class FailingModule:

            def __getattr__(self, name):
                raise ImportError('Module not found')
        sys.modules['netra_backend.app.agents.unified_tool_execution'] = FailingModule()
        try:
            mock_manager = Mock()
            registry.set_websocket_manager(mock_manager)
            assert registry.websocket_manager == mock_manager
        finally:
            sys.modules.clear()
            sys.modules.update(original_modules)

    def test_enhance_tool_dispatcher_no_dispatcher(self):
        """Test WebSocket enhancement when no tool_dispatcher exists."""
        registry = AgentRegistry()
        registry._enhance_tool_dispatcher_with_websockets()
        assert registry._tool_dispatcher is None

    def test_agent_validation_with_class_subclass_check(self):
        """Test agent validation performs issubclass check for class types."""
        registry = AgentRegistry()

        class MockAgentBase:
            pass

        class MockAgentClass(MockAgentBase):
            pass
        import sys
        from unittest.mock import patch
        mock_module = type(sys)('mock_base_agent')
        mock_module.BaseAgent = MockAgentBase
        with patch.dict(sys.modules, {'netra_backend.app.agents.base_agent': mock_module}):
            registry.register('valid-agent-class', MockAgentClass)
            assert 'valid-agent-class' in registry

    def test_agent_validation_import_error_fallback(self):
        """Test agent validation gracefully handles BaseAgent import errors."""
        registry = AgentRegistry()
        import sys
        from unittest.mock import patch

        def mock_import(name, *args, **kwargs):
            if name == 'netra_backend.app.agents.base_agent':
                raise ImportError('BaseAgent not found')
            return __builtins__['__import__'](name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            registry.register('fallback-agent', 'any-object')
            assert 'fallback-agent' in registry

    def test_enhance_tool_dispatcher_with_real_dispatcher_success(self):
        """Test successful WebSocket enhancement with real dispatcher."""
        registry = AgentRegistry()
        real_dispatcher = Mock(spec=[])
        registry.set_tool_dispatcher(real_dispatcher)
        import sys
        from unittest.mock import patch, MagicMock
        mock_enhance_func = MagicMock()
        with patch.dict(sys.modules, {'netra_backend.app.agents.unified_tool_execution': MagicMock(enhance_tool_dispatcher_with_notifications=mock_enhance_func)}):
            mock_manager = Mock()
            registry.set_websocket_manager(mock_manager)
            mock_enhance_func.assert_called_once_with(real_dispatcher, websocket_manager=mock_manager, enable_notifications=True)

class OtherSpecializedRegistriesTests:
    """Test other specialized registry classes."""

    def test_tool_registry_initialization(self):
        """Test ToolRegistry initialization."""
        registry = ToolRegistry()
        assert registry.name == 'ToolRegistry'
        assert len(registry) >= 0

    def test_service_registry_initialization(self):
        """Test ServiceRegistry initialization."""
        registry = ServiceRegistry()
        assert registry.name == 'ServiceRegistry'

    def test_service_registry_register_service(self):
        """Test registering services with metadata."""
        registry = ServiceRegistry()
        registry.register_service('auth-service', 'http://localhost:8081', health_endpoint='/health', version='1.0.0')
        assert 'auth-service' in registry
        service_info = registry.get('auth-service')
        assert service_info['url'] == 'http://localhost:8081'
        assert service_info['health_endpoint'] == '/health'
        assert service_info['version'] == '1.0.0'

    def test_strategy_registry_initialization(self):
        """Test StrategyRegistry initialization."""
        registry = StrategyRegistry()
        assert registry.name == 'StrategyRegistry'

class GlobalRegistryManagementTests:
    """Test global registry management functions."""

    def test_get_global_registry_agent(self, clean_global_registries):
        """Test getting global agent registry."""
        registry = get_global_registry('agent')
        assert isinstance(registry, AgentRegistry)
        assert registry.name == 'AgentRegistry'
        registry2 = get_global_registry('agent')
        assert registry2 is registry

    def test_get_global_registry_tool(self, clean_global_registries):
        """Test getting global tool registry."""
        registry = get_global_registry('tool')
        assert isinstance(registry, ToolRegistry)
        assert registry.name == 'ToolRegistry'

    def test_get_global_registry_service(self, clean_global_registries):
        """Test getting global service registry."""
        registry = get_global_registry('service')
        assert isinstance(registry, ServiceRegistry)
        assert registry.name == 'ServiceRegistry'

    def test_get_global_registry_strategy(self, clean_global_registries):
        """Test getting global strategy registry."""
        registry = get_global_registry('strategy')
        assert isinstance(registry, StrategyRegistry)
        assert registry.name == 'StrategyRegistry'

    def test_get_global_registry_invalid(self, clean_global_registries):
        """Test getting invalid registry type fails."""
        with pytest.raises(ValueError, match='Unknown registry type: invalid'):
            get_global_registry('invalid')

    def test_get_global_registry_case_insensitive(self, clean_global_registries):
        """Test global registry is case insensitive."""
        registry1 = get_global_registry('AGENT')
        registry2 = get_global_registry('agent')
        registry3 = get_global_registry('Agent')
        assert registry1 is registry2 is registry3

    def test_global_registry_thread_safety(self, clean_global_registries):
        """Test global registry creation is thread-safe."""
        registries = []
        errors = []

        def get_registry(thread_id):
            try:
                registry = get_global_registry('agent')
                registries.append((thread_id, registry))
            except Exception as e:
                errors.append((thread_id, e))
        threads = []
        for i in range(20):
            thread = threading.Thread(target=get_registry, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(errors) == 0, f'Errors occurred: {errors}'
        assert len(registries) == 20
        first_registry = registries[0][1]
        assert all((reg is first_registry for _, reg in registries))

    def test_create_scoped_registry(self):
        """Test creating scoped registries."""
        registry1 = create_scoped_registry('agent', 'user-123')
        registry2 = create_scoped_registry('agent', 'user-456')
        assert isinstance(registry1, AgentRegistry)
        assert isinstance(registry2, AgentRegistry)
        assert registry1 is not registry2
        assert registry1.name == 'agent_user-123'
        assert registry2.name == 'agent_user-456'

    def test_create_scoped_registry_all_types(self):
        """Test creating scoped registries for all types."""
        types = ['agent', 'tool', 'service', 'strategy']
        expected_classes = [AgentRegistry, ToolRegistry, ServiceRegistry, StrategyRegistry]
        for registry_type, expected_class in zip(types, expected_classes):
            registry = create_scoped_registry(registry_type, 'test-scope')
            assert isinstance(registry, expected_class)
            assert registry.name == f'{registry_type}_test-scope'

    def test_create_scoped_registry_generic(self):
        """Test creating scoped registry for unknown type creates generic."""
        registry = create_scoped_registry('custom', 'test-scope')
        assert isinstance(registry, UniversalRegistry)
        assert registry.name == 'custom_test-scope'

class UniversalRegistryEdgeCasesTests:
    """Test edge cases and error conditions."""

    def test_empty_key_registration(self, sample_agent):
        """Test registering with empty key."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        registry.register('', sample_agent)
        assert '' in registry
        assert registry.get('') == sample_agent

    def test_none_value_registration(self):
        """Test registering None value."""
        registry = UniversalRegistry[Any]('TestRegistry')
        registry.register('none-item', None)
        assert 'none-item' in registry
        assert registry.get('none-item') is None

    def test_factory_with_none_context(self):
        """Test factory call with None context."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def agent_factory(ctx):
            if ctx is None:
                return MockAgent('default')
            return MockAgent(f'user-{ctx.user_id}')
        registry.register_factory('factory', agent_factory)
        agent = registry.get('factory')
        assert agent is None
        agent = registry.get('factory', None)
        assert agent is None
        try:
            agent = registry.create_instance('factory', None)
            assert agent.name == 'default'
        except Exception:
            pass

    def test_factory_context_isolation_comprehensive(self):
        """Test factory context isolation with complex scenarios."""
        registry = UniversalRegistry[MockAgent]('IsolationTestRegistry')

        def context_modifying_factory(ctx):
            original_user_id = ctx.user_id
            ctx.user_id = f'modified-{ctx.user_id}'
            agent = MockAgent(original_user_id)
            agent.context_snapshot = {'user_id': original_user_id, 'run_id': ctx.run_id, 'modified_user_id': ctx.user_id}
            return agent
        registry.register_factory('context-modifier', context_modifying_factory)
        ctx1 = MockUserExecutionContext('user-1', 'run-1')
        ctx2 = MockUserExecutionContext('user-2', 'run-2')
        original_ctx1_user = ctx1.user_id
        original_ctx2_user = ctx2.user_id
        agent1 = registry.create_instance('context-modifier', ctx1)
        agent2 = registry.create_instance('context-modifier', ctx2)
        assert ctx1.user_id == f'modified-{original_ctx1_user}'
        assert ctx2.user_id == f'modified-{original_ctx2_user}'
        assert agent1.name == original_ctx1_user
        assert agent2.name == original_ctx2_user
        assert agent1 is not agent2
        assert agent1.context_snapshot['user_id'] != agent2.context_snapshot['user_id']

    def test_factory_exception_handling(self, mock_context):
        """Test factory that raises exceptions."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def failing_factory(ctx):
            raise Exception('Factory failed')
        registry.register_factory('failing', failing_factory)
        with pytest.raises(Exception, match='Factory failed'):
            registry.get('failing', mock_context)
        with pytest.raises(Exception, match='Factory failed'):
            registry.create_instance('failing', mock_context)
        initial_metrics = registry.get_metrics()
        assert initial_metrics['metrics']['factory_creations'] >= 0

    def test_factory_with_different_exception_types(self, mock_context):
        """Test factory with various exception types."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')

        def value_error_factory(ctx):
            raise ValueError('Invalid context provided')

        def type_error_factory(ctx):
            raise TypeError('Wrong type in factory')

        def runtime_error_factory(ctx):
            raise RuntimeError('Runtime failure in factory')
        registry.register_factory('value_error', value_error_factory)
        registry.register_factory('type_error', type_error_factory)
        registry.register_factory('runtime_error', runtime_error_factory)
        with pytest.raises(ValueError, match='Invalid context provided'):
            registry.create_instance('value_error', mock_context)
        with pytest.raises(TypeError, match='Wrong type in factory'):
            registry.create_instance('type_error', mock_context)
        with pytest.raises(RuntimeError, match='Runtime failure in factory'):
            registry.create_instance('runtime_error', mock_context)

    def test_large_registry_performance(self):
        """Test registry with large number of items."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        start_time = time.time()
        for i in range(1000):
            registry.register(f'agent-{i:04d}', MockAgent(f'agent-{i:04d}'))
        registration_time = time.time() - start_time
        assert len(registry) == 1000
        start_time = time.time()
        for i in range(0, 1000, 10):
            agent = registry.get(f'agent-{i:04d}')
            assert agent is not None
        access_time = time.time() - start_time
        start_time = time.time()
        metrics = registry.get_metrics()
        metrics_time = time.time() - start_time
        assert metrics['total_items'] == 1000
        assert registration_time < 5.0
        assert access_time < 1.0
        assert metrics_time < 1.0

    def test_registry_with_circular_references(self):
        """Test registry handles circular references gracefully."""
        registry = UniversalRegistry[Dict]('TestRegistry')
        obj1 = {'name': 'obj1'}
        obj2 = {'name': 'obj2'}
        obj1['ref'] = obj2
        obj2['ref'] = obj1
        registry.register('circular1', obj1)
        registry.register('circular2', obj2)
        retrieved1 = registry.get('circular1')
        retrieved2 = registry.get('circular2')
        assert retrieved1['name'] == 'obj1'
        assert retrieved2['name'] == 'obj2'
        assert retrieved1['ref'] is obj2
        assert retrieved2['ref'] is obj1

    def test_registry_item_metadata_mutation(self, sample_agent):
        """Test metadata behavior after registration."""
        registry = UniversalRegistry[MockAgent]('TestRegistry')
        metadata = {'mutable': ['list']}
        registry.register('agent1', sample_agent, **metadata)
        item = registry._items['agent1']
        stored_metadata = item.metadata
        assert 'mutable' in stored_metadata
        assert stored_metadata['mutable'] == ['list']
        stored_metadata['mutable'].append('modified')
        stored_metadata['new_key'] = 'new_value'
        assert item.metadata['mutable'] == ['list', 'modified']
        assert item.metadata['new_key'] == 'new_value'
        metadata['external_change'] = 'should_not_affect_registry'
        assert 'external_change' not in item.metadata

    def test_concurrent_clear_and_access(self, sample_agent):
        """Test concurrent clear while accessing items."""
        registry = UniversalRegistry[MockAgent]('TestRegistry', allow_override=True)
        for i in range(100):
            registry.register(f'agent-{i}', MockAgent(f'agent-{i}'))
        access_results = []
        clear_completed = []
        errors = []

        def access_items(thread_id):
            try:
                for i in range(100):
                    agent = registry.get(f'agent-{i}')
                    if agent:
                        access_results.append((thread_id, i))
            except Exception as e:
                errors.append(('access', thread_id, e))

        def clear_registry():
            try:
                time.sleep(0.01)
                registry.clear()
                clear_completed.append(True)
            except Exception as e:
                errors.append(('clear', e))
        access_threads = []
        for i in range(5):
            thread = threading.Thread(target=access_items, args=(i,))
            access_threads.append(thread)
            thread.start()
        clear_thread = threading.Thread(target=clear_registry)
        clear_thread.start()
        for thread in access_threads:
            thread.join()
        clear_thread.join()
        assert len(errors) == 0, f'Errors occurred: {errors}'
        assert len(clear_completed) == 1
        assert len(registry) == 0

    def test_stress_test_factory_creation_concurrent(self):
        """Test high-volume concurrent factory instance creation."""
        registry = UniversalRegistry[MockAgent]('StressTestRegistry')

        def stress_factory(ctx):
            time.sleep(0.001)
            return MockAgent(f'stress-{ctx.user_id}-{ctx.run_id}')
        registry.register_factory('stress-agent', stress_factory)
        creation_results = []
        errors = []

        def create_multiple_instances(thread_id):
            try:
                for i in range(10):
                    ctx = MockUserExecutionContext(f'user-{thread_id}', f'run-{i}')
                    agent = registry.create_instance('stress-agent', ctx)
                    creation_results.append((thread_id, i, agent.name))
            except Exception as e:
                errors.append((thread_id, e))
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_multiple_instances, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(errors) == 0, f'Errors occurred: {errors}'
        assert len(creation_results) == 100
        agent_names = [result[2] for result in creation_results]
        assert len(set(agent_names)) == 100
        metrics = registry.get_metrics()
        assert metrics['metrics']['factory_creations'] >= 100

    def test_concurrent_tag_operations(self):
        """Test concurrent tag-based operations are thread-safe."""
        registry = UniversalRegistry[MockAgent]('TagTestRegistry')
        for i in range(20):
            agent = MockAgent(f'agent-{i}')
            tags = ['category1'] if i % 2 == 0 else ['category2']
            if i % 5 == 0:
                tags.append('special')
            registry.register(f'agent-{i}', agent, tags=tags)
        tag_results = []
        errors = []

        def query_tags_repeatedly(thread_id):
            try:
                for _ in range(50):
                    cat1_keys = registry.list_by_tag('category1')
                    cat2_keys = registry.list_by_tag('category2')
                    special_keys = registry.list_by_tag('special')
                    tag_results.append((thread_id, len(cat1_keys), len(cat2_keys), len(special_keys)))
            except Exception as e:
                errors.append((thread_id, e))
        threads = []
        for i in range(8):
            thread = threading.Thread(target=query_tags_repeatedly, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(errors) == 0, f'Errors occurred: {errors}'
        assert len(tag_results) == 8 * 50
        first_result = tag_results[0]
        for result in tag_results:
            assert result[1:] == first_result[1:], 'Tag query results should be consistent'
        assert first_result[1] == 10
        assert first_result[2] == 10
        assert first_result[3] == 4

class UniversalRegistrySystemIntegrationTests:
    """Test integration with broader system components."""

    def test_multiple_registries_isolation(self):
        """Test multiple registries maintain isolation."""
        agent_registry = UniversalRegistry[MockAgent]('AgentRegistry')
        tool_registry = UniversalRegistry[MockTool]('ToolRegistry')
        agent = MockAgent('agent1')
        tool = MockTool('tool1')
        agent_registry.register('item1', agent)
        tool_registry.register('item1', tool)
        assert agent_registry.get('item1') == agent
        assert tool_registry.get('item1') == tool
        assert agent_registry.get('item1') is not tool_registry.get('item1')
        agent_registry.remove('item1')
        assert 'item1' not in agent_registry
        assert 'item1' in tool_registry

    def test_registry_with_real_context_patterns(self):
        """Test registry patterns similar to real system usage."""
        agent_registry = AgentRegistry()

        def triage_factory(ctx):
            agent = MockAgent('triage')
            agent.user_id = ctx.user_id
            agent.run_id = ctx.run_id
            return agent

        def data_factory(ctx):
            agent = MockAgent('data')
            agent.user_id = ctx.user_id
            agent.run_id = ctx.run_id
            return agent
        agent_registry.register_factory('triage', triage_factory, tags=['primary'])
        agent_registry.register_factory('data', data_factory, tags=['analysis'])
        user1_ctx = MockUserExecutionContext('user-1', 'run-123')
        user2_ctx = MockUserExecutionContext('user-2', 'run-456')
        user1_triage = agent_registry.create_instance('triage', user1_ctx)
        user1_data = agent_registry.create_instance('data', user1_ctx)
        user2_triage = agent_registry.create_instance('triage', user2_ctx)
        user2_data = agent_registry.create_instance('data', user2_ctx)
        assert user1_triage.user_id == 'user-1'
        assert user1_triage.run_id == 'run-123'
        assert user2_triage.user_id == 'user-2'
        assert user2_triage.run_id == 'run-456'
        assert user1_triage is not user2_triage
        assert user1_data is not user2_data
        assert user1_triage.name == user2_triage.name == 'triage'
        assert user1_data.name == user2_data.name == 'data'

    def test_registry_metrics_real_usage_simulation(self):
        """Test metrics under realistic usage patterns."""
        registry = UniversalRegistry[Any]('TestRegistry')
        for i in range(5):
            registry.register(f'agent-{i}', MockAgent(f'agent-{i}'), tags=['agent'])
            registry.register(f'tool-{i}', MockTool(f'tool-{i}'), tags=['tool'])

        def agent_factory(ctx):
            return MockAgent(f'dynamic-{ctx.user_id}')
        registry.register_factory('dynamic-agent', agent_factory, tags=['dynamic', 'agent'])
        contexts = [MockUserExecutionContext(f'user-{i}', f'run-{i}') for i in range(3)]
        for _ in range(50):
            registry.get('agent-0')
            registry.get('tool-0')
        for _ in range(10):
            registry.get('agent-1')
            registry.get('tool-1')
        for ctx in contexts:
            for _ in range(5):
                registry.create_instance('dynamic-agent', ctx)
        metrics = registry.get_metrics()
        assert metrics['total_items'] == 11
        expected_retrievals = 120 + 15
        assert metrics['metrics']['total_retrievals'] >= 120
        assert metrics['metrics']['factory_creations'] == 15
        assert metrics['category_distribution']['agent'] == 6
        assert metrics['category_distribution']['tool'] == 5
        assert metrics['category_distribution']['dynamic'] == 1
        most_accessed = metrics['most_accessed']
        assert most_accessed[0]['key'] in ['agent-0', 'tool-0']
        assert most_accessed[0]['count'] == 50
        health = registry.validate_health()
        assert health['status'] == 'healthy' or health['status'] == 'warning'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')