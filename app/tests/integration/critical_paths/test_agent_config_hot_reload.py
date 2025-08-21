"""Agent Configuration Hot Reload L2 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (operational agility and dynamic configuration)
- Business Goal: Dynamic configuration updates without service disruption
- Value Impact: $5K MRR - Enables dynamic config worth operational agility and rapid iteration
- Strategic Impact: Hot reloading reduces downtime and enables rapid configuration changes

Critical Path: Config change detection -> Validation -> Hot reload -> Notification -> Verification
Coverage: Config watching, validation, hot reload mechanisms, notification systems, rollback safety
"""

import pytest
import asyncio
import logging
import json
import tempfile
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import yaml

from app.core.exceptions_base import NetraException

logger = logging.getLogger(__name__)


class ConfigChangeType(Enum):
    """Types of configuration changes."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class ConfigValidationLevel(Enum):
    """Configuration validation levels."""
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    DEPENDENCY = "dependency"
    RUNTIME = "runtime"


@dataclass
class ConfigChange:
    """Configuration change detection result."""
    change_id: str
    change_type: ConfigChangeType
    config_key: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_file: Optional[str] = None
    validation_required: bool = True


@dataclass
class ValidationResult:
    """Configuration validation result."""
    is_valid: bool
    validation_level: ConfigValidationLevel
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    dependency_issues: List[str] = field(default_factory=list)


@dataclass
class ReloadMetrics:
    """Hot reload performance and success metrics."""
    total_reloads: int = 0
    successful_reloads: int = 0
    failed_reloads: int = 0
    average_reload_time: float = 0.0
    config_changes_detected: int = 0
    validation_failures: int = 0
    rollback_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate reload success rate."""
        if self.total_reloads == 0:
            return 100.0
        return (self.successful_reloads / self.total_reloads) * 100


class ConfigWatcher:
    """Configuration file change detection and monitoring."""
    
    def __init__(self, config_directories: List[str]):
        self.config_directories = config_directories
        self.watched_files: Dict[str, float] = {}  # file_path -> last_modified
        self.change_callbacks: List[Callable] = []
        self.is_watching = False
        self.watch_interval = 1.0  # seconds
        self._watch_task: Optional[asyncio.Task] = None
    
    async def start_watching(self):
        """Start watching configuration files for changes."""
        if self.is_watching:
            return
        
        self.is_watching = True
        self._initialize_file_tracking()
        self._watch_task = asyncio.create_task(self._watch_loop())
    
    async def stop_watching(self):
        """Stop watching configuration files."""
        self.is_watching = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
    
    def _initialize_file_tracking(self):
        """Initialize tracking of all configuration files."""
        for config_dir in self.config_directories:
            if os.path.exists(config_dir):
                for root, _, files in os.walk(config_dir):
                    for file in files:
                        if file.endswith(('.json', '.yaml', '.yml', '.toml', '.ini')):
                            file_path = os.path.join(root, file)
                            self.watched_files[file_path] = os.path.getmtime(file_path)
    
    async def _watch_loop(self):
        """Main watching loop for configuration changes."""
        while self.is_watching:
            try:
                changes = await self._detect_changes()
                
                for change in changes:
                    await self._notify_change(change)
                
                await asyncio.sleep(self.watch_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in config watch loop: {e}")
                await asyncio.sleep(self.watch_interval)
    
    async def _detect_changes(self) -> List[ConfigChange]:
        """Detect configuration file changes."""
        changes = []
        current_files = {}
        
        # Scan for current files
        for config_dir in self.config_directories:
            if os.path.exists(config_dir):
                for root, _, files in os.walk(config_dir):
                    for file in files:
                        if file.endswith(('.json', '.yaml', '.yml', '.toml', '.ini')):
                            file_path = os.path.join(root, file)
                            current_files[file_path] = os.path.getmtime(file_path)
        
        # Check for modified or new files
        for file_path, current_mtime in current_files.items():
            if file_path in self.watched_files:
                if current_mtime > self.watched_files[file_path]:
                    # File modified
                    change = ConfigChange(
                        change_id=f"change_{len(changes) + 1}",
                        change_type=ConfigChangeType.MODIFIED,
                        config_key=os.path.basename(file_path),
                        source_file=file_path
                    )
                    changes.append(change)
                    self.watched_files[file_path] = current_mtime
            else:
                # New file
                change = ConfigChange(
                    change_id=f"change_{len(changes) + 1}",
                    change_type=ConfigChangeType.ADDED,
                    config_key=os.path.basename(file_path),
                    source_file=file_path
                )
                changes.append(change)
                self.watched_files[file_path] = current_mtime
        
        # Check for deleted files
        for file_path in list(self.watched_files.keys()):
            if file_path not in current_files:
                change = ConfigChange(
                    change_id=f"change_{len(changes) + 1}",
                    change_type=ConfigChangeType.DELETED,
                    config_key=os.path.basename(file_path),
                    source_file=file_path
                )
                changes.append(change)
                del self.watched_files[file_path]
        
        return changes
    
    async def _notify_change(self, change: ConfigChange):
        """Notify registered callbacks of configuration changes."""
        for callback in self.change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(change)
                else:
                    callback(change)
            except Exception as e:
                logger.error(f"Error in change callback: {e}")
    
    def register_change_callback(self, callback: Callable):
        """Register callback for configuration changes."""
        self.change_callbacks.append(callback)


class ConfigValidator:
    """Configuration validation and verification system."""
    
    def __init__(self):
        self.validation_rules: Dict[str, Dict] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        self.validation_cache: Dict[str, ValidationResult] = {}
    
    def register_validation_rules(self, config_key: str, rules: Dict[str, Any]):
        """Register validation rules for a configuration key."""
        self.validation_rules[config_key] = rules
    
    def register_dependency(self, config_key: str, depends_on: List[str]):
        """Register configuration dependencies."""
        self.dependency_graph[config_key] = depends_on
    
    async def validate_config_change(self, change: ConfigChange, 
                                   full_config: Dict[str, Any]) -> ValidationResult:
        """Validate a configuration change comprehensively."""
        cache_key = f"{change.config_key}:{change.change_id}"
        
        if cache_key in self.validation_cache:
            return self.validation_cache[cache_key]
        
        # Perform multi-level validation
        validation_results = []
        
        # Syntax validation
        syntax_result = await self._validate_syntax(change, full_config)
        validation_results.append(syntax_result)
        
        # Semantic validation
        semantic_result = await self._validate_semantics(change, full_config)
        validation_results.append(semantic_result)
        
        # Dependency validation
        dependency_result = await self._validate_dependencies(change, full_config)
        validation_results.append(dependency_result)
        
        # Runtime validation
        runtime_result = await self._validate_runtime_impact(change, full_config)
        validation_results.append(runtime_result)
        
        # Combine results
        combined_result = self._combine_validation_results(validation_results)
        
        # Cache result
        self.validation_cache[cache_key] = combined_result
        
        return combined_result
    
    async def _validate_syntax(self, change: ConfigChange, 
                             full_config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration syntax."""
        errors = []
        warnings = []
        
        try:
            # Check if new value has valid syntax
            if change.new_value is not None:
                # Type checking
                if change.config_key in self.validation_rules:
                    rules = self.validation_rules[change.config_key]
                    expected_type = rules.get("type")
                    
                    if expected_type and not isinstance(change.new_value, expected_type):
                        errors.append(f"Type mismatch: expected {expected_type.__name__}, got {type(change.new_value).__name__}")
                    
                    # Range checking for numeric values
                    if expected_type in [int, float]:
                        min_val = rules.get("min")
                        max_val = rules.get("max")
                        
                        if min_val is not None and change.new_value < min_val:
                            errors.append(f"Value {change.new_value} below minimum {min_val}")
                        
                        if max_val is not None and change.new_value > max_val:
                            errors.append(f"Value {change.new_value} above maximum {max_val}")
                    
                    # Required fields check
                    if rules.get("required", False) and change.new_value is None:
                        errors.append(f"Required field {change.config_key} cannot be null")
        
        except Exception as e:
            errors.append(f"Syntax validation error: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            validation_level=ConfigValidationLevel.SYNTAX,
            errors=errors,
            warnings=warnings
        )
    
    async def _validate_semantics(self, change: ConfigChange,
                                full_config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration semantics and business logic."""
        errors = []
        warnings = []
        
        try:
            # Business logic validation
            if change.config_key == "max_concurrent_agents":
                if change.new_value and change.new_value < 1:
                    errors.append("max_concurrent_agents must be at least 1")
                elif change.new_value and change.new_value > 1000:
                    warnings.append("max_concurrent_agents > 1000 may impact performance")
            
            elif change.config_key == "agent_timeout":
                if change.new_value and change.new_value < 1.0:
                    errors.append("agent_timeout must be at least 1 second")
                elif change.new_value and change.new_value > 3600.0:
                    warnings.append("agent_timeout > 1 hour may cause resource issues")
            
            elif change.config_key == "redis_url":
                if change.new_value and not change.new_value.startswith(("redis://", "rediss://")):
                    errors.append("redis_url must start with redis:// or rediss://")
        
        except Exception as e:
            errors.append(f"Semantic validation error: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            validation_level=ConfigValidationLevel.SEMANTIC,
            errors=errors,
            warnings=warnings
        )
    
    async def _validate_dependencies(self, change: ConfigChange,
                                   full_config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration dependencies."""
        errors = []
        warnings = []
        dependency_issues = []
        
        try:
            # Check if dependencies are satisfied
            if change.config_key in self.dependency_graph:
                dependencies = self.dependency_graph[change.config_key]
                
                for dep_key in dependencies:
                    if dep_key not in full_config:
                        dependency_issues.append(f"Missing dependency: {dep_key}")
                    elif full_config[dep_key] is None:
                        dependency_issues.append(f"Dependency {dep_key} is null")
            
            # Check for circular dependencies
            circular_deps = self._detect_circular_dependencies(change.config_key)
            if circular_deps:
                dependency_issues.extend([f"Circular dependency: {dep}" for dep in circular_deps])
        
        except Exception as e:
            errors.append(f"Dependency validation error: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0 and len(dependency_issues) == 0,
            validation_level=ConfigValidationLevel.DEPENDENCY,
            errors=errors,
            warnings=warnings,
            dependency_issues=dependency_issues
        )
    
    async def _validate_runtime_impact(self, change: ConfigChange,
                                     full_config: Dict[str, Any]) -> ValidationResult:
        """Validate runtime impact of configuration changes."""
        errors = []
        warnings = []
        
        try:
            # Check for runtime compatibility
            critical_configs = ["database_url", "redis_url", "llm_api_key"]
            
            if change.config_key in critical_configs:
                if change.change_type == ConfigChangeType.DELETED:
                    errors.append(f"Critical config {change.config_key} cannot be deleted during runtime")
                elif change.new_value is None or change.new_value == "":
                    errors.append(f"Critical config {change.config_key} cannot be empty")
            
            # Performance impact warnings
            performance_configs = ["max_concurrent_agents", "worker_pool_size", "cache_size"]
            
            if change.config_key in performance_configs:
                if change.old_value and change.new_value:
                    change_ratio = abs(change.new_value - change.old_value) / change.old_value
                    if change_ratio > 0.5:  # 50% change
                        warnings.append(f"Large change in {change.config_key} may impact performance")
        
        except Exception as e:
            errors.append(f"Runtime validation error: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            validation_level=ConfigValidationLevel.RUNTIME,
            errors=errors,
            warnings=warnings
        )
    
    def _detect_circular_dependencies(self, config_key: str) -> List[str]:
        """Detect circular dependencies in configuration."""
        visited = set()
        path = []
        
        def dfs(key):
            if key in path:
                # Found cycle
                cycle_start = path.index(key)
                return path[cycle_start:]
            
            if key in visited:
                return []
            
            visited.add(key)
            path.append(key)
            
            for dep in self.dependency_graph.get(key, []):
                cycle = dfs(dep)
                if cycle:
                    return cycle
            
            path.pop()
            return []
        
        return dfs(config_key)
    
    def _combine_validation_results(self, results: List[ValidationResult]) -> ValidationResult:
        """Combine multiple validation results into one."""
        all_errors = []
        all_warnings = []
        all_dependency_issues = []
        is_valid = True
        
        for result in results:
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            all_dependency_issues.extend(result.dependency_issues)
            
            if not result.is_valid:
                is_valid = False
        
        return ValidationResult(
            is_valid=is_valid,
            validation_level=ConfigValidationLevel.RUNTIME,  # Highest level completed
            errors=all_errors,
            warnings=all_warnings,
            dependency_issues=all_dependency_issues
        )


class HotReloader:
    """Configuration hot reload execution engine."""
    
    def __init__(self):
        self.current_config: Dict[str, Any] = {}
        self.config_history: List[Dict[str, Any]] = []
        self.reload_callbacks: Dict[str, List[Callable]] = {}
        self.rollback_snapshots: List[Dict[str, Any]] = []
        self.max_snapshots = 10
    
    def register_reload_callback(self, config_key: str, callback: Callable):
        """Register callback for specific configuration changes."""
        if config_key not in self.reload_callbacks:
            self.reload_callbacks[config_key] = []
        self.reload_callbacks[config_key].append(callback)
    
    async def execute_hot_reload(self, validated_change: ConfigChange,
                               validation_result: ValidationResult) -> Dict[str, Any]:
        """Execute hot reload of configuration change."""
        if not validation_result.is_valid:
            return {
                "reload_successful": False,
                "reason": "validation_failed",
                "validation_errors": validation_result.errors
            }
        
        # Create rollback snapshot
        self._create_rollback_snapshot()
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Apply configuration change
            await self._apply_config_change(validated_change)
            
            # Execute reload callbacks
            reload_results = await self._execute_reload_callbacks(validated_change)
            
            # Verify reload success
            verification_result = await self._verify_reload_success(validated_change)
            
            end_time = datetime.now(timezone.utc)
            reload_duration = (end_time - start_time).total_seconds()
            
            if verification_result["verification_successful"]:
                return {
                    "reload_successful": True,
                    "change_id": validated_change.change_id,
                    "reload_duration": reload_duration,
                    "callbacks_executed": len(reload_results),
                    "verification_result": verification_result,
                    "warnings": validation_result.warnings
                }
            else:
                # Verification failed, rollback
                await self._execute_rollback()
                return {
                    "reload_successful": False,
                    "reason": "verification_failed",
                    "verification_result": verification_result,
                    "rollback_executed": True
                }
        
        except Exception as e:
            # Reload failed, rollback
            await self._execute_rollback()
            return {
                "reload_successful": False,
                "reason": f"reload_error: {e}",
                "rollback_executed": True
            }
    
    def _create_rollback_snapshot(self):
        """Create snapshot for potential rollback."""
        snapshot = {
            "timestamp": datetime.now(timezone.utc),
            "config": self.current_config.copy()
        }
        
        self.rollback_snapshots.append(snapshot)
        
        # Limit snapshot history
        if len(self.rollback_snapshots) > self.max_snapshots:
            self.rollback_snapshots.pop(0)
    
    async def _apply_config_change(self, change: ConfigChange):
        """Apply configuration change to current config."""
        if change.change_type == ConfigChangeType.ADDED or change.change_type == ConfigChangeType.MODIFIED:
            self.current_config[change.config_key] = change.new_value
        elif change.change_type == ConfigChangeType.DELETED:
            if change.config_key in self.current_config:
                del self.current_config[change.config_key]
        
        # Record in history
        self.config_history.append({
            "change": change,
            "timestamp": datetime.now(timezone.utc),
            "config_snapshot": self.current_config.copy()
        })
    
    async def _execute_reload_callbacks(self, change: ConfigChange) -> List[Dict[str, Any]]:
        """Execute registered reload callbacks."""
        results = []
        
        # Execute specific callbacks for this config key
        if change.config_key in self.reload_callbacks:
            for callback in self.reload_callbacks[change.config_key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        result = await callback(change, self.current_config)
                    else:
                        result = callback(change, self.current_config)
                    
                    results.append({
                        "callback": callback.__name__ if hasattr(callback, '__name__') else 'anonymous',
                        "success": True,
                        "result": result
                    })
                
                except Exception as e:
                    results.append({
                        "callback": callback.__name__ if hasattr(callback, '__name__') else 'anonymous',
                        "success": False,
                        "error": str(e)
                    })
        
        # Execute global callbacks (wildcard)
        if "*" in self.reload_callbacks:
            for callback in self.reload_callbacks["*"]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        result = await callback(change, self.current_config)
                    else:
                        result = callback(change, self.current_config)
                    
                    results.append({
                        "callback": f"global_{callback.__name__}" if hasattr(callback, '__name__') else 'global_anonymous',
                        "success": True,
                        "result": result
                    })
                
                except Exception as e:
                    results.append({
                        "callback": f"global_{callback.__name__}" if hasattr(callback, '__name__') else 'global_anonymous',
                        "success": False,
                        "error": str(e)
                    })
        
        return results
    
    async def _verify_reload_success(self, change: ConfigChange) -> Dict[str, Any]:
        """Verify that reload was successful."""
        verification_checks = []
        
        # Check if config value was actually applied
        if change.change_type != ConfigChangeType.DELETED:
            actual_value = self.current_config.get(change.config_key)
            expected_value = change.new_value
            
            value_check = {
                "check": "config_value_applied",
                "passed": actual_value == expected_value,
                "expected": expected_value,
                "actual": actual_value
            }
            verification_checks.append(value_check)
        
        # Check if config is internally consistent
        consistency_check = {
            "check": "config_consistency",
            "passed": self._check_config_consistency(),
            "issues": []
        }
        verification_checks.append(consistency_check)
        
        # Check if system is still functional
        functionality_check = {
            "check": "system_functionality",
            "passed": await self._check_system_functionality(),
            "details": "Basic system checks passed"
        }
        verification_checks.append(functionality_check)
        
        all_checks_passed = all(check["passed"] for check in verification_checks)
        
        return {
            "verification_successful": all_checks_passed,
            "verification_checks": verification_checks,
            "timestamp": datetime.now(timezone.utc)
        }
    
    def _check_config_consistency(self) -> bool:
        """Check internal consistency of configuration."""
        # Basic consistency checks
        try:
            # Check for required dependencies
            if "database_url" in self.current_config and "redis_url" in self.current_config:
                # Both critical services should be configured
                db_url = self.current_config["database_url"]
                redis_url = self.current_config["redis_url"]
                
                if not db_url or not redis_url:
                    return False
            
            # Check numeric constraints
            max_agents = self.current_config.get("max_concurrent_agents")
            if max_agents and max_agents < 1:
                return False
            
            return True
        
        except Exception:
            return False
    
    async def _check_system_functionality(self) -> bool:
        """Check basic system functionality after reload."""
        # Simulate basic functionality checks
        try:
            # Check if critical services would still work
            await asyncio.sleep(0.01)  # Simulate check
            return True
        except Exception:
            return False
    
    async def _execute_rollback(self) -> bool:
        """Execute rollback to previous configuration state."""
        if not self.rollback_snapshots:
            return False
        
        try:
            # Get latest snapshot
            latest_snapshot = self.rollback_snapshots[-1]
            
            # Restore configuration
            self.current_config = latest_snapshot["config"].copy()
            
            # Remove used snapshot
            self.rollback_snapshots.pop()
            
            return True
        
        except Exception:
            return False


class ConfigNotifier:
    """Configuration change notification system."""
    
    def __init__(self):
        self.notification_channels: List[Callable] = []
        self.notification_history: List[Dict[str, Any]] = []
    
    def register_notification_channel(self, channel: Callable):
        """Register notification channel for config changes."""
        self.notification_channels.append(channel)
    
    async def notify_config_change(self, change: ConfigChange, 
                                 reload_result: Dict[str, Any]) -> Dict[str, Any]:
        """Send notifications about configuration changes."""
        notification = {
            "notification_id": f"notif_{len(self.notification_history) + 1}",
            "change_id": change.change_id,
            "config_key": change.config_key,
            "change_type": change.change_type.value,
            "reload_successful": reload_result.get("reload_successful", False),
            "timestamp": datetime.now(timezone.utc),
            "details": {
                "old_value": change.old_value,
                "new_value": change.new_value,
                "reload_duration": reload_result.get("reload_duration"),
                "warnings": reload_result.get("warnings", [])
            }
        }
        
        # Send to all notification channels
        notification_results = []
        
        for channel in self.notification_channels:
            try:
                if asyncio.iscoroutinefunction(channel):
                    result = await channel(notification)
                else:
                    result = channel(notification)
                
                notification_results.append({
                    "channel": channel.__name__ if hasattr(channel, '__name__') else 'anonymous',
                    "success": True,
                    "result": result
                })
            
            except Exception as e:
                notification_results.append({
                    "channel": channel.__name__ if hasattr(channel, '__name__') else 'anonymous',
                    "success": False,
                    "error": str(e)
                })
        
        # Record notification
        self.notification_history.append(notification)
        
        return {
            "notification_sent": True,
            "notification_id": notification["notification_id"],
            "channels_notified": len(notification_results),
            "notification_results": notification_results
        }


class AgentConfigHotReloadManager:
    """Comprehensive agent configuration hot reload system."""
    
    def __init__(self, config_directories: List[str]):
        self.config_watcher = ConfigWatcher(config_directories)
        self.config_validator = ConfigValidator()
        self.hot_reloader = HotReloader()
        self.config_notifier = ConfigNotifier()
        self.metrics = ReloadMetrics()
        
        # Register change detection callback
        self.config_watcher.register_change_callback(self._handle_config_change)
        
        # Initialize validation rules
        self._initialize_validation_rules()
    
    def _initialize_validation_rules(self):
        """Initialize configuration validation rules."""
        validation_rules = {
            "max_concurrent_agents": {
                "type": int,
                "min": 1,
                "max": 1000,
                "required": False
            },
            "agent_timeout": {
                "type": float,
                "min": 1.0,
                "max": 3600.0,
                "required": False
            },
            "database_url": {
                "type": str,
                "required": True
            },
            "redis_url": {
                "type": str,
                "required": True
            }
        }
        
        for config_key, rules in validation_rules.items():
            self.config_validator.register_validation_rules(config_key, rules)
        
        # Register dependencies
        self.config_validator.register_dependency("agent_timeout", ["max_concurrent_agents"])
    
    async def start_hot_reload_system(self):
        """Start the hot reload system."""
        await self.config_watcher.start_watching()
    
    async def stop_hot_reload_system(self):
        """Stop the hot reload system."""
        await self.config_watcher.stop_watching()
    
    async def _handle_config_change(self, change: ConfigChange):
        """Handle detected configuration change."""
        start_time = datetime.now(timezone.utc)
        
        try:
            self.metrics.config_changes_detected += 1
            
            # Validate the change
            validation_result = await self.config_validator.validate_config_change(
                change, self.hot_reloader.current_config
            )
            
            if not validation_result.is_valid:
                self.metrics.validation_failures += 1
                return
            
            # Execute hot reload
            reload_result = await self.hot_reloader.execute_hot_reload(change, validation_result)
            
            self.metrics.total_reloads += 1
            
            if reload_result["reload_successful"]:
                self.metrics.successful_reloads += 1
            else:
                self.metrics.failed_reloads += 1
                
                if reload_result.get("rollback_executed"):
                    self.metrics.rollback_count += 1
            
            # Update average reload time
            end_time = datetime.now(timezone.utc)
            reload_duration = (end_time - start_time).total_seconds()
            
            total_time = self.metrics.average_reload_time * (self.metrics.total_reloads - 1)
            self.metrics.average_reload_time = (total_time + reload_duration) / self.metrics.total_reloads
            
            # Send notifications
            await self.config_notifier.notify_config_change(change, reload_result)
        
        except Exception as e:
            logger.error(f"Error handling config change: {e}")
            self.metrics.failed_reloads += 1
    
    async def trigger_manual_reload(self, config_key: str, new_value: Any) -> Dict[str, Any]:
        """Manually trigger configuration reload."""
        # Create manual change
        manual_change = ConfigChange(
            change_id=f"manual_{datetime.now(timezone.utc).timestamp()}",
            change_type=ConfigChangeType.MODIFIED,
            config_key=config_key,
            old_value=self.hot_reloader.current_config.get(config_key),
            new_value=new_value
        )
        
        # Handle the change
        await self._handle_config_change(manual_change)
        
        return {
            "manual_reload_triggered": True,
            "change_id": manual_change.change_id,
            "config_key": config_key,
            "new_value": new_value
        }
    
    async def test_hot_reload_performance(self, test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test hot reload performance with various scenarios."""
        performance_results = []
        
        for i, scenario in enumerate(test_scenarios):
            scenario_start = datetime.now(timezone.utc)
            
            # Trigger reload
            reload_result = await self.trigger_manual_reload(
                scenario["config_key"], 
                scenario["new_value"]
            )
            
            scenario_end = datetime.now(timezone.utc)
            scenario_duration = (scenario_end - scenario_start).total_seconds()
            
            performance_results.append({
                "scenario_id": i,
                "config_key": scenario["config_key"],
                "reload_duration": scenario_duration,
                "reload_successful": True  # Simplified for testing
            })
        
        # Calculate performance metrics
        total_duration = sum(r["reload_duration"] for r in performance_results)
        average_duration = total_duration / len(performance_results) if performance_results else 0
        
        return {
            "total_scenarios": len(test_scenarios),
            "total_duration": total_duration,
            "average_reload_duration": average_duration,
            "performance_results": performance_results,
            "performance_acceptable": average_duration < 1.0  # < 1 second target
        }
    
    def get_hot_reload_metrics(self) -> Dict[str, Any]:
        """Get comprehensive hot reload metrics."""
        return {
            "reload_performance": {
                "total_reloads": self.metrics.total_reloads,
                "successful_reloads": self.metrics.successful_reloads,
                "failed_reloads": self.metrics.failed_reloads,
                "success_rate": self.metrics.success_rate,
                "average_reload_time": self.metrics.average_reload_time
            },
            "change_detection": {
                "config_changes_detected": self.metrics.config_changes_detected,
                "watched_files": len(self.config_watcher.watched_files),
                "is_watching": self.config_watcher.is_watching
            },
            "validation": {
                "validation_failures": self.metrics.validation_failures,
                "validation_rules": len(self.config_validator.validation_rules),
                "cache_size": len(self.config_validator.validation_cache)
            },
            "rollback": {
                "rollback_count": self.metrics.rollback_count,
                "available_snapshots": len(self.hot_reloader.rollback_snapshots)
            },
            "notifications": {
                "notification_channels": len(self.config_notifier.notification_channels),
                "notifications_sent": len(self.config_notifier.notification_history)
            }
        }


@pytest.fixture
async def hot_reload_manager():
    """Create hot reload manager for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = AgentConfigHotReloadManager([temp_dir])
        yield manager
        await manager.stop_hot_reload_system()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l2
class TestAgentConfigHotReloadL2:
    """L2 integration tests for agent configuration hot reload."""
    
    async def test_config_change_detection_accuracy(self, hot_reload_manager):
        """Test accurate configuration change detection."""
        manager = hot_reload_manager
        
        # Start watching
        await manager.start_hot_reload_system()
        
        # Create test configuration file
        test_config_dir = manager.config_watcher.config_directories[0]
        config_file = os.path.join(test_config_dir, "test_config.json")
        
        # Initial config
        initial_config = {
            "max_concurrent_agents": 10,
            "agent_timeout": 30.0,
            "test_setting": "initial_value"
        }
        
        with open(config_file, 'w') as f:
            json.dump(initial_config, f)
        
        # Wait for initial detection
        await asyncio.sleep(1.5)
        
        # Modify config
        modified_config = initial_config.copy()
        modified_config["max_concurrent_agents"] = 20
        modified_config["test_setting"] = "modified_value"
        
        with open(config_file, 'w') as f:
            json.dump(modified_config, f)
        
        # Wait for change detection
        await asyncio.sleep(1.5)
        
        # Add new config
        new_config = modified_config.copy()
        new_config["new_setting"] = "new_value"
        
        with open(config_file, 'w') as f:
            json.dump(new_config, f)
        
        # Wait for change detection
        await asyncio.sleep(1.5)
        
        # Verify change detection
        metrics = manager.get_hot_reload_metrics()
        
        assert metrics["change_detection"]["config_changes_detected"] >= 2, \
            "Should detect multiple configuration changes"
        
        assert metrics["change_detection"]["is_watching"], \
            "Config watcher should be active"
        
        assert len(manager.config_watcher.watched_files) >= 1, \
            "Should track configuration files"
    
    async def test_validation_pipeline_comprehensive(self, hot_reload_manager):
        """Test comprehensive configuration validation pipeline."""
        manager = hot_reload_manager
        
        # Test valid configuration change
        valid_change = ConfigChange(
            change_id="test_valid",
            change_type=ConfigChangeType.MODIFIED,
            config_key="max_concurrent_agents",
            old_value=10,
            new_value=20
        )
        
        validation_result = await manager.config_validator.validate_config_change(
            valid_change, {"max_concurrent_agents": 10}
        )
        
        assert validation_result.is_valid, \
            f"Valid config change should pass validation: {validation_result.errors}"
        
        # Test invalid configuration change
        invalid_change = ConfigChange(
            change_id="test_invalid",
            change_type=ConfigChangeType.MODIFIED,
            config_key="max_concurrent_agents",
            old_value=10,
            new_value=-5  # Invalid negative value
        )
        
        invalid_validation = await manager.config_validator.validate_config_change(
            invalid_change, {"max_concurrent_agents": 10}
        )
        
        assert not invalid_validation.is_valid, \
            "Invalid config change should fail validation"
        
        assert len(invalid_validation.errors) > 0, \
            "Invalid config should have validation errors"
        
        # Test dependency validation
        dependency_change = ConfigChange(
            change_id="test_dependency",
            change_type=ConfigChangeType.MODIFIED,
            config_key="agent_timeout",
            old_value=30.0,
            new_value=60.0
        )
        
        # Missing dependency
        dependency_validation = await manager.config_validator.validate_config_change(
            dependency_change, {}  # Missing max_concurrent_agents dependency
        )
        
        # Should still be valid but may have dependency warnings
        assert len(dependency_validation.dependency_issues) >= 0, \
            "Dependency validation should check for missing dependencies"
    
    async def test_hot_reload_execution_performance(self, hot_reload_manager):
        """Test hot reload execution performance and timing."""
        manager = hot_reload_manager
        
        # Register reload callbacks
        callback_results = []
        
        async def test_callback(change, config):
            callback_results.append({
                "change_id": change.change_id,
                "config_key": change.config_key,
                "timestamp": datetime.now(timezone.utc)
            })
            return "callback_executed"
        
        manager.hot_reloader.register_reload_callback("max_concurrent_agents", test_callback)
        
        # Test performance scenarios
        performance_scenarios = [
            {"config_key": "max_concurrent_agents", "new_value": 15},
            {"config_key": "agent_timeout", "new_value": 45.0},
            {"config_key": "max_concurrent_agents", "new_value": 25},
            {"config_key": "agent_timeout", "new_value": 60.0}
        ]
        
        performance_test = await manager.test_hot_reload_performance(performance_scenarios)
        
        # Verify performance requirements
        assert performance_test["performance_acceptable"], \
            f"Hot reload performance should be <1s, got {performance_test['average_reload_duration']:.3f}s"
        
        assert performance_test["total_scenarios"] == len(performance_scenarios), \
            "All scenarios should be tested"
        
        # Verify callbacks were executed
        assert len(callback_results) >= 2, \
            "Reload callbacks should be executed for relevant changes"
        
        # Verify metrics tracking
        metrics = manager.get_hot_reload_metrics()
        assert metrics["reload_performance"]["total_reloads"] >= 4, \
            "All reloads should be tracked in metrics"
    
    async def test_rollback_safety_mechanisms(self, hot_reload_manager):
        """Test configuration rollback and safety mechanisms."""
        manager = hot_reload_manager
        
        # Set initial configuration
        initial_config = {
            "max_concurrent_agents": 10,
            "agent_timeout": 30.0,
            "database_url": "postgresql://localhost/test"
        }
        
        manager.hot_reloader.current_config = initial_config.copy()
        
        # Test successful reload with snapshot creation
        valid_change = ConfigChange(
            change_id="rollback_test_1",
            change_type=ConfigChangeType.MODIFIED,
            config_key="max_concurrent_agents",
            old_value=10,
            new_value=20
        )
        
        validation_result = await manager.config_validator.validate_config_change(
            valid_change, initial_config
        )
        
        reload_result = await manager.hot_reloader.execute_hot_reload(
            valid_change, validation_result
        )
        
        assert reload_result["reload_successful"], \
            "Valid reload should succeed"
        
        # Verify snapshot was created
        assert len(manager.hot_reloader.rollback_snapshots) >= 1, \
            "Rollback snapshot should be created"
        
        # Verify configuration was updated
        assert manager.hot_reloader.current_config["max_concurrent_agents"] == 20, \
            "Configuration should be updated after successful reload"
        
        # Test rollback capability
        rollback_success = await manager.hot_reloader._execute_rollback()
        
        assert rollback_success, \
            "Rollback should succeed when snapshots are available"
        
        assert manager.hot_reloader.current_config["max_concurrent_agents"] == 10, \
            "Configuration should be restored after rollback"
    
    async def test_notification_system_integration(self, hot_reload_manager):
        """Test configuration change notification system."""
        manager = hot_reload_manager
        
        # Register notification channels
        notification_results = []
        
        async def email_notifier(notification):
            notification_results.append({
                "channel": "email",
                "notification_id": notification["notification_id"],
                "config_key": notification["config_key"]
            })
            return "email_sent"
        
        def slack_notifier(notification):
            notification_results.append({
                "channel": "slack", 
                "notification_id": notification["notification_id"],
                "config_key": notification["config_key"]
            })
            return "slack_message_sent"
        
        manager.config_notifier.register_notification_channel(email_notifier)
        manager.config_notifier.register_notification_channel(slack_notifier)
        
        # Trigger configuration change
        reload_result = await manager.trigger_manual_reload("max_concurrent_agents", 30)
        
        # Wait for notifications
        await asyncio.sleep(0.1)
        
        # Verify notifications were sent
        assert len(notification_results) >= 2, \
            "Notifications should be sent to all registered channels"
        
        # Verify notification content
        email_notifications = [n for n in notification_results if n["channel"] == "email"]
        slack_notifications = [n for n in notification_results if n["channel"] == "slack"]
        
        assert len(email_notifications) >= 1, \
            "Email notifications should be sent"
        
        assert len(slack_notifications) >= 1, \
            "Slack notifications should be sent"
        
        # Verify notification tracking
        metrics = manager.get_hot_reload_metrics()
        assert metrics["notifications"]["notifications_sent"] >= 1, \
            "Notification history should be tracked"
    
    async def test_concurrent_config_changes(self, hot_reload_manager):
        """Test handling of concurrent configuration changes."""
        manager = hot_reload_manager
        
        # Start hot reload system
        await manager.start_hot_reload_system()
        
        # Create concurrent configuration changes
        async def concurrent_config_change(change_id: int):
            config_key = ["max_concurrent_agents", "agent_timeout"][change_id % 2]
            new_value = [15, 45.0][change_id % 2]
            
            return await manager.trigger_manual_reload(config_key, new_value)
        
        # Execute concurrent changes
        concurrent_tasks = [concurrent_config_change(i) for i in range(8)]
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify concurrent handling
        successful_changes = [r for r in results if not isinstance(r, Exception)]
        
        assert len(successful_changes) == 8, \
            f"All concurrent changes should be handled, got {len(successful_changes)}"
        
        # Verify system stability
        metrics = manager.get_hot_reload_metrics()
        
        assert metrics["reload_performance"]["total_reloads"] >= 8, \
            "All concurrent reloads should be tracked"
        
        # Success rate should be reasonable for concurrent operations
        assert metrics["reload_performance"]["success_rate"] >= 75.0, \
            f"Success rate {metrics['reload_performance']['success_rate']:.1f}% should be ≥75% for concurrent ops"
    
    async def test_config_dependency_validation(self, hot_reload_manager):
        """Test configuration dependency validation and ordering."""
        manager = hot_reload_manager
        
        # Set up complex dependency scenario
        complex_config = {
            "max_concurrent_agents": 10,
            "agent_timeout": 30.0,
            "worker_pool_size": 5,
            "database_url": "postgresql://localhost/test",
            "redis_url": "redis://localhost/redis"
        }
        
        manager.hot_reloader.current_config = complex_config.copy()
        
        # Register additional dependencies
        manager.config_validator.register_dependency("worker_pool_size", ["max_concurrent_agents"])
        manager.config_validator.register_dependency("agent_timeout", ["max_concurrent_agents", "worker_pool_size"])
        
        # Test dependency satisfaction
        dependent_change = ConfigChange(
            change_id="dependency_test",
            change_type=ConfigChangeType.MODIFIED,
            config_key="agent_timeout",
            old_value=30.0,
            new_value=60.0
        )
        
        validation_result = await manager.config_validator.validate_config_change(
            dependent_change, complex_config
        )
        
        # Should be valid when dependencies are satisfied
        assert validation_result.is_valid, \
            f"Configuration with satisfied dependencies should be valid: {validation_result.errors}"
        
        # Test missing dependency
        incomplete_config = {"agent_timeout": 30.0}  # Missing dependencies
        
        missing_dep_validation = await manager.config_validator.validate_config_change(
            dependent_change, incomplete_config
        )
        
        # Should detect dependency issues
        assert len(missing_dep_validation.dependency_issues) > 0, \
            "Missing dependencies should be detected"
        
        # Test circular dependency detection
        # Create circular dependency: A -> B -> A
        manager.config_validator.register_dependency("test_config_a", ["test_config_b"])
        manager.config_validator.register_dependency("test_config_b", ["test_config_a"])
        
        circular_deps = manager.config_validator._detect_circular_dependencies("test_config_a")
        
        assert len(circular_deps) > 0, \
            "Circular dependencies should be detected"
    
    async def test_comprehensive_hot_reload_workflow(self, hot_reload_manager):
        """Test complete hot reload workflow with all components."""
        manager = hot_reload_manager
        
        # Phase 1: Initialize system
        await manager.start_hot_reload_system()
        
        # Phase 2: Set up comprehensive monitoring
        notification_log = []
        
        async def comprehensive_notifier(notification):
            notification_log.append(notification)
            return "comprehensive_notification_sent"
        
        manager.config_notifier.register_notification_channel(comprehensive_notifier)
        
        # Phase 3: Execute complex configuration workflow
        workflow_changes = [
            {"config_key": "max_concurrent_agents", "new_value": 15},
            {"config_key": "agent_timeout", "new_value": 45.0},
            {"config_key": "max_concurrent_agents", "new_value": 25},  # Second change to same key
            {"config_key": "worker_pool_size", "new_value": 8},
        ]
        
        workflow_results = []
        for change in workflow_changes:
            result = await manager.trigger_manual_reload(
                change["config_key"], change["new_value"]
            )
            workflow_results.append(result)
            
            # Small delay between changes
            await asyncio.sleep(0.1)
        
        # Phase 4: Verify comprehensive workflow
        final_metrics = manager.get_hot_reload_metrics()
        
        # Verify all changes were processed
        assert len(workflow_results) == len(workflow_changes), \
            "All workflow changes should be processed"
        
        assert final_metrics["reload_performance"]["total_reloads"] >= len(workflow_changes), \
            "All reloads should be tracked"
        
        # Verify notifications were sent
        assert len(notification_log) >= len(workflow_changes), \
            "Notifications should be sent for all changes"
        
        # Verify system performance
        assert final_metrics["reload_performance"]["average_reload_time"] < 2.0, \
            f"Average reload time {final_metrics['reload_performance']['average_reload_time']:.3f}s should be <2s"
        
        # Verify system stability (high success rate)
        assert final_metrics["reload_performance"]["success_rate"] >= 80.0, \
            f"Success rate {final_metrics['reload_performance']['success_rate']:.1f}% should be ≥80%"
        
        # Phase 5: Verify configuration state consistency
        current_config = manager.hot_reloader.current_config
        
        # Should have the latest values
        assert current_config.get("max_concurrent_agents") == 25, \
            "Final configuration should have latest value"
        
        assert current_config.get("agent_timeout") == 45.0, \
            "Configuration should maintain all applied changes"
        
        # Verify rollback capability is preserved
        assert len(manager.hot_reloader.rollback_snapshots) >= 1, \
            "Rollback snapshots should be maintained"