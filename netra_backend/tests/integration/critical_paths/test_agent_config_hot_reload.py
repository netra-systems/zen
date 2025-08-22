"""Agent Configuration Hot Reload L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (operational continuity)
- Business Goal: Zero-downtime configuration updates
- Value Impact: Protects $5K MRR from restart-related downtime
- Strategic Impact: Enables real-time optimization and tuning

Critical Path: Config change -> Validation -> Hot reload -> Propagation -> Verification
Coverage: Real configuration management, file watching, graceful updates
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
import logging
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.config import get_settings
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager
from netra_backend.app.core.events import EventBus

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Agent configuration structure."""
    agent_id: str
    agent_type: str
    model_settings: Dict[str, Any] = field(default_factory=dict)
    rate_limits: Dict[str, int] = field(default_factory=dict)
    feature_flags: Dict[str, bool] = field(default_factory=dict)
    retry_config: Dict[str, Any] = field(default_factory=dict)
    timeout_config: Dict[str, int] = field(default_factory=dict)
    version: str = "1.0.0"
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["updated_at"] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create from dictionary."""
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)

class ConfigValidator:
    """Validates agent configuration."""
    
    def __init__(self):
        self.validation_rules = {
            "agent_id": self._validate_agent_id,
            "agent_type": self._validate_agent_type,
            "model_settings": self._validate_model_settings,
            "rate_limits": self._validate_rate_limits,
            "timeout_config": self._validate_timeout_config
        }
    
    def validate_config(self, config: AgentConfig) -> Tuple[bool, List[str]]:
        """Validate complete configuration."""
        errors = []
        
        for field_name, validator in self.validation_rules.items():
            try:
                field_value = getattr(config, field_name)
                field_errors = validator(field_value)
                errors.extend(field_errors)
            except Exception as e:
                errors.append(f"Validation error for {field_name}: {e}")
        
        return len(errors) == 0, errors
    
    def _validate_agent_id(self, agent_id: str) -> List[str]:
        """Validate agent ID."""
        errors = []
        if not agent_id or not isinstance(agent_id, str):
            errors.append("Agent ID must be a non-empty string")
        if len(agent_id) > 100:
            errors.append("Agent ID must be less than 100 characters")
        return errors
    
    def _validate_agent_type(self, agent_type: str) -> List[str]:
        """Validate agent type."""
        errors = []
        valid_types = ["supervisor", "worker", "analyzer", "router"]
        if agent_type not in valid_types:
            errors.append(f"Agent type must be one of {valid_types}")
        return errors
    
    def _validate_model_settings(self, settings: Dict[str, Any]) -> List[str]:
        """Validate model settings."""
        errors = []
        if "max_tokens" in settings:
            if not isinstance(settings["max_tokens"], int) or settings["max_tokens"] <= 0:
                errors.append("max_tokens must be a positive integer")
        if "temperature" in settings:
            if not isinstance(settings["temperature"], (int, float)) or not 0 <= settings["temperature"] <= 2:
                errors.append("temperature must be between 0 and 2")
        return errors
    
    def _validate_rate_limits(self, limits: Dict[str, int]) -> List[str]:
        """Validate rate limits."""
        errors = []
        for key, value in limits.items():
            if not isinstance(value, int) or value <= 0:
                errors.append(f"Rate limit {key} must be a positive integer")
        return errors
    
    def _validate_timeout_config(self, timeouts: Dict[str, int]) -> List[str]:
        """Validate timeout configuration."""
        errors = []
        for key, value in timeouts.items():
            if not isinstance(value, int) or value <= 0:
                errors.append(f"Timeout {key} must be a positive integer")
        return errors

class ConfigFileWatcher(FileSystemEventHandler):
    """Watches configuration files for changes."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.last_modified = {}
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        file_path = event.src_path
        
        # Debounce rapid file changes
        current_time = time.time()
        if file_path in self.last_modified:
            if current_time - self.last_modified[file_path] < 1.0:  # 1 second debounce
                return
        
        self.last_modified[file_path] = current_time
        
        # Trigger config reload
        asyncio.create_task(self.config_manager.handle_file_change(file_path))

class ConfigManager:
    """Manages agent configuration with hot reload capabilities."""
    
    def __init__(self, redis_service: RedisService, event_bus: EventBus):
        self.redis_service = redis_service
        self.event_bus = event_bus
        self.validator = ConfigValidator()
        self.active_configs = {}
        self.file_watchers = {}
        self.config_observers = {}
        self.reload_callbacks = {}
        
    async def load_config(self, config_path: str) -> Optional[AgentConfig]:
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            config = AgentConfig.from_dict(data)
            
            # Validate configuration
            is_valid, errors = self.validator.validate_config(config)
            if not is_valid:
                logger.error(f"Invalid configuration: {errors}")
                return None
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return None
    
    async def save_config(self, config: AgentConfig, config_path: str) -> bool:
        """Save configuration to file."""
        try:
            config_data = config.to_dict()
            
            with open(config_path, 'w') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    yaml.dump(config_data, f, default_flow_style=False)
                else:
                    json.dump(config_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
            return False
    
    async def register_config(self, agent_id: str, config_path: str) -> bool:
        """Register configuration for hot reload."""
        try:
            # Load initial configuration
            config = await self.load_config(config_path)
            if not config:
                return False
            
            # Store in Redis for fast access
            config_key = f"agent_config:{agent_id}"
            await self.redis_service.client.setex(
                config_key, 
                3600,  # 1 hour TTL
                json.dumps(config.to_dict())
            )
            
            # Store active config
            self.active_configs[agent_id] = config
            
            # Set up file watcher
            self.setup_file_watcher(agent_id, config_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register config for {agent_id}: {e}")
            return False
    
    def setup_file_watcher(self, agent_id: str, config_path: str):
        """Set up file watcher for configuration."""
        try:
            config_dir = os.path.dirname(config_path)
            
            if agent_id not in self.config_observers:
                event_handler = ConfigFileWatcher(self)
                observer = Observer()
                observer.schedule(event_handler, config_dir, recursive=False)
                observer.start()
                
                self.config_observers[agent_id] = observer
                self.file_watchers[agent_id] = config_path
                
        except Exception as e:
            logger.error(f"Failed to set up file watcher for {agent_id}: {e}")
    
    async def handle_file_change(self, file_path: str):
        """Handle configuration file changes."""
        try:
            # Find agent ID for this file
            agent_id = None
            for aid, path in self.file_watchers.items():
                if path == file_path:
                    agent_id = aid
                    break
            
            if not agent_id:
                return
            
            logger.info(f"Configuration file changed for agent {agent_id}: {file_path}")
            
            # Reload configuration
            await self.reload_config(agent_id, file_path)
            
        except Exception as e:
            logger.error(f"Failed to handle file change: {e}")
    
    async def reload_config(self, agent_id: str, config_path: str = None) -> bool:
        """Reload configuration for an agent."""
        try:
            if not config_path:
                config_path = self.file_watchers.get(agent_id)
                if not config_path:
                    return False
            
            # Load new configuration
            new_config = await self.load_config(config_path)
            if not new_config:
                logger.error(f"Failed to load new configuration for {agent_id}")
                return False
            
            # Compare with current config
            old_config = self.active_configs.get(agent_id)
            if old_config and self.configs_equal(old_config, new_config):
                logger.info(f"No changes detected in configuration for {agent_id}")
                return True
            
            # Update active config
            self.active_configs[agent_id] = new_config
            
            # Update Redis cache
            config_key = f"agent_config:{agent_id}"
            await self.redis_service.client.setex(
                config_key,
                3600,
                json.dumps(new_config.to_dict())
            )
            
            # Trigger callbacks
            await self.notify_config_change(agent_id, old_config, new_config)
            
            # Publish event
            await self.event_bus.publish("config_reloaded", {
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat(),
                "config_version": new_config.version
            })
            
            logger.info(f"Configuration reloaded successfully for {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload configuration for {agent_id}: {e}")
            return False
    
    def configs_equal(self, config1: AgentConfig, config2: AgentConfig) -> bool:
        """Check if two configurations are equal."""
        # Compare all fields except updated_at
        return (
            config1.agent_id == config2.agent_id and
            config1.agent_type == config2.agent_type and
            config1.model_settings == config2.model_settings and
            config1.rate_limits == config2.rate_limits and
            config1.feature_flags == config2.feature_flags and
            config1.retry_config == config2.retry_config and
            config1.timeout_config == config2.timeout_config and
            config1.version == config2.version
        )
    
    async def get_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Get current configuration for an agent."""
        try:
            # Try active configs first
            if agent_id in self.active_configs:
                return self.active_configs[agent_id]
            
            # Fallback to Redis
            config_key = f"agent_config:{agent_id}"
            cached_data = await self.redis_service.client.get(config_key)
            
            if cached_data:
                data = json.loads(cached_data)
                config = AgentConfig.from_dict(data)
                self.active_configs[agent_id] = config
                return config
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get configuration for {agent_id}: {e}")
            return None
    
    def register_reload_callback(self, agent_id: str, callback: Callable):
        """Register callback for configuration reloads."""
        if agent_id not in self.reload_callbacks:
            self.reload_callbacks[agent_id] = []
        self.reload_callbacks[agent_id].append(callback)
    
    async def notify_config_change(self, agent_id: str, old_config: AgentConfig, new_config: AgentConfig):
        """Notify registered callbacks of configuration changes."""
        if agent_id in self.reload_callbacks:
            for callback in self.reload_callbacks[agent_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(old_config, new_config)
                    else:
                        callback(old_config, new_config)
                except Exception as e:
                    logger.error(f"Config reload callback failed: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        # Stop file observers
        for observer in self.config_observers.values():
            observer.stop()
            observer.join()

class MockAgent:
    """Mock agent for testing configuration hot reload."""
    
    def __init__(self, agent_id: str, config_manager: ConfigManager):
        self.agent_id = agent_id
        self.config_manager = config_manager
        self.current_config = None
        self.config_changes = []
        self.is_running = False
        
        # Register for config changes
        self.config_manager.register_reload_callback(
            agent_id, self.handle_config_change
        )
    
    async def start(self):
        """Start the mock agent."""
        self.current_config = await self.config_manager.get_config(self.agent_id)
        self.is_running = True
    
    async def handle_config_change(self, old_config: AgentConfig, new_config: AgentConfig):
        """Handle configuration changes."""
        self.config_changes.append({
            "timestamp": datetime.now(),
            "old_config": old_config,
            "new_config": new_config
        })
        self.current_config = new_config
        logger.info(f"Agent {self.agent_id} received config update")

class ConfigHotReloadManager:
    """Manages configuration hot reload testing."""
    
    def __init__(self):
        self.redis_service = None
        self.event_bus = None
        self.config_manager = None
        self.temp_dir = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.event_bus = EventBus()
        self.config_manager = ConfigManager(self.redis_service, self.event_bus)
        
        # Create temporary directory for test configs
        self.temp_dir = tempfile.mkdtemp()
        
    def create_test_config(self, agent_id: str) -> AgentConfig:
        """Create a test configuration."""
        return AgentConfig(
            agent_id=agent_id,
            agent_type="worker",
            model_settings={
                "max_tokens": 2000,
                "temperature": 0.7,
                "model": "gpt-4"
            },
            rate_limits={
                "requests_per_minute": 60,
                "tokens_per_hour": 100000
            },
            feature_flags={
                "enhanced_memory": True,
                "debug_mode": False
            },
            retry_config={
                "max_retries": 3,
                "backoff_factor": 2
            },
            timeout_config={
                "request_timeout": 30,
                "total_timeout": 300
            }
        )
    
    async def cleanup(self):
        """Clean up resources."""
        if self.config_manager:
            await self.config_manager.cleanup()
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

@pytest.fixture
async def hot_reload_manager():
    """Create hot reload manager for testing."""
    manager = ConfigHotReloadManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_config_loading_and_validation(hot_reload_manager):
    """Test configuration loading and validation."""
    manager = hot_reload_manager
    
    # Create test config
    test_config = manager.create_test_config("test_agent_1")
    config_path = os.path.join(manager.temp_dir, "test_config.json")
    
    # Save config to file
    save_result = await manager.config_manager.save_config(test_config, config_path)
    assert save_result is True
    
    # Load config from file
    loaded_config = await manager.config_manager.load_config(config_path)
    assert loaded_config is not None
    assert loaded_config.agent_id == "test_agent_1"
    assert loaded_config.model_settings["max_tokens"] == 2000

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_config_registration_and_caching(hot_reload_manager):
    """Test configuration registration and Redis caching."""
    manager = hot_reload_manager
    
    # Create and save test config
    test_config = manager.create_test_config("cache_test_agent")
    config_path = os.path.join(manager.temp_dir, "cache_test.json")
    await manager.config_manager.save_config(test_config, config_path)
    
    # Register configuration
    register_result = await manager.config_manager.register_config("cache_test_agent", config_path)
    assert register_result is True
    
    # Retrieve from cache
    cached_config = await manager.config_manager.get_config("cache_test_agent")
    assert cached_config is not None
    assert cached_config.agent_id == "cache_test_agent"

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_config_file_watching(hot_reload_manager):
    """Test configuration file watching and hot reload."""
    manager = hot_reload_manager
    
    # Create initial config
    test_config = manager.create_test_config("watch_test_agent")
    config_path = os.path.join(manager.temp_dir, "watch_test.json")
    await manager.config_manager.save_config(test_config, config_path)
    
    # Register configuration with file watching
    await manager.config_manager.register_config("watch_test_agent", config_path)
    
    # Give file watcher time to set up
    await asyncio.sleep(0.5)
    
    # Modify configuration
    test_config.model_settings["max_tokens"] = 4000
    test_config.updated_at = datetime.now()
    await manager.config_manager.save_config(test_config, config_path)
    
    # Wait for file watcher to detect change
    await asyncio.sleep(2.0)
    
    # Verify configuration was reloaded
    updated_config = await manager.config_manager.get_config("watch_test_agent")
    assert updated_config.model_settings["max_tokens"] == 4000

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_config_validation_rules(hot_reload_manager):
    """Test configuration validation rules."""
    manager = hot_reload_manager
    
    validator = manager.config_manager.validator
    
    # Test valid configuration
    valid_config = manager.create_test_config("valid_agent")
    is_valid, errors = validator.validate_config(valid_config)
    assert is_valid is True
    assert len(errors) == 0
    
    # Test invalid agent ID
    invalid_config = manager.create_test_config("")
    is_valid, errors = validator.validate_config(invalid_config)
    assert is_valid is False
    assert any("Agent ID" in error for error in errors)
    
    # Test invalid temperature
    invalid_config = manager.create_test_config("temp_test")
    invalid_config.model_settings["temperature"] = 5.0  # Out of range
    is_valid, errors = validator.validate_config(invalid_config)
    assert is_valid is False
    assert any("temperature" in error for error in errors)

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_agent_config_callbacks(hot_reload_manager):
    """Test agent configuration change callbacks."""
    manager = hot_reload_manager
    
    # Create mock agent
    agent_id = "callback_test_agent"
    test_config = manager.create_test_config(agent_id)
    config_path = os.path.join(manager.temp_dir, "callback_test.json")
    await manager.config_manager.save_config(test_config, config_path)
    
    # Register configuration
    await manager.config_manager.register_config(agent_id, config_path)
    
    # Create mock agent
    mock_agent = MockAgent(agent_id, manager.config_manager)
    await mock_agent.start()
    
    # Trigger configuration reload
    test_config.rate_limits["requests_per_minute"] = 120
    await manager.config_manager.save_config(test_config, config_path)
    await manager.config_manager.reload_config(agent_id, config_path)
    
    # Wait for callback processing
    await asyncio.sleep(0.1)
    
    # Verify callback was triggered
    assert len(mock_agent.config_changes) == 1
    assert mock_agent.current_config.rate_limits["requests_per_minute"] == 120

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_config_operations(hot_reload_manager):
    """Test concurrent configuration operations."""
    manager = hot_reload_manager
    
    # Create multiple configurations
    agent_ids = [f"concurrent_agent_{i}" for i in range(10)]
    configs = [manager.create_test_config(aid) for aid in agent_ids]
    config_paths = [
        os.path.join(manager.temp_dir, f"concurrent_{i}.json") 
        for i in range(10)
    ]
    
    # Save configs concurrently
    save_tasks = [
        manager.config_manager.save_config(config, path)
        for config, path in zip(configs, config_paths)
    ]
    save_results = await asyncio.gather(*save_tasks)
    assert all(save_results)
    
    # Register configs concurrently
    register_tasks = [
        manager.config_manager.register_config(agent_id, path)
        for agent_id, path in zip(agent_ids, config_paths)
    ]
    register_results = await asyncio.gather(*register_tasks)
    assert all(register_results)
    
    # Retrieve configs concurrently
    get_tasks = [
        manager.config_manager.get_config(agent_id)
        for agent_id in agent_ids
    ]
    retrieved_configs = await asyncio.gather(*get_tasks)
    
    assert len(retrieved_configs) == 10
    assert all(config is not None for config in retrieved_configs)

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_config_reload_performance(hot_reload_manager):
    """Benchmark configuration reload performance."""
    manager = hot_reload_manager
    
    # Create test configuration
    test_config = manager.create_test_config("perf_test_agent")
    config_path = os.path.join(manager.temp_dir, "perf_test.json")
    await manager.config_manager.save_config(test_config, config_path)
    await manager.config_manager.register_config("perf_test_agent", config_path)
    
    # Benchmark reload operations
    start_time = time.time()
    
    reload_tasks = []
    for i in range(50):
        # Modify config slightly
        test_config.model_settings["max_tokens"] = 2000 + i
        await manager.config_manager.save_config(test_config, config_path)
        
        task = manager.config_manager.reload_config("perf_test_agent", config_path)
        reload_tasks.append(task)
    
    reload_results = await asyncio.gather(*reload_tasks)
    reload_time = time.time() - start_time
    
    assert all(reload_results)
    
    # Performance assertions
    assert reload_time < 3.0  # 50 reloads in under 3 seconds
    avg_reload_time = reload_time / 50
    assert avg_reload_time < 0.06  # Average reload under 60ms
    
    logger.info(f"Performance: {avg_reload_time*1000:.1f}ms per config reload")

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_yaml_config_support(hot_reload_manager):
    """Test YAML configuration file support."""
    manager = hot_reload_manager
    
    # Create test config
    test_config = manager.create_test_config("yaml_test_agent")
    config_path = os.path.join(manager.temp_dir, "yaml_test.yaml")
    
    # Save as YAML
    save_result = await manager.config_manager.save_config(test_config, config_path)
    assert save_result is True
    
    # Load from YAML
    loaded_config = await manager.config_manager.load_config(config_path)
    assert loaded_config is not None
    assert loaded_config.agent_id == "yaml_test_agent"
    assert loaded_config.model_settings["temperature"] == 0.7

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_config_error_handling(hot_reload_manager):
    """Test configuration error handling."""
    manager = hot_reload_manager
    
    # Test loading non-existent file
    non_existent_config = await manager.config_manager.load_config("non_existent.json")
    assert non_existent_config is None
    
    # Test loading invalid JSON
    invalid_path = os.path.join(manager.temp_dir, "invalid.json")
    with open(invalid_path, 'w') as f:
        f.write("invalid json content")
    
    invalid_config = await manager.config_manager.load_config(invalid_path)
    assert invalid_config is None
    
    # Test registering invalid configuration
    invalid_config_obj = manager.create_test_config("invalid_agent")
    invalid_config_obj.agent_type = "invalid_type"  # Invalid type
    
    invalid_config_path = os.path.join(manager.temp_dir, "invalid_config.json")
    await manager.config_manager.save_config(invalid_config_obj, invalid_config_path)
    
    register_result = await manager.config_manager.register_config("invalid_agent", invalid_config_path)
    assert register_result is False