from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Category Configuration Loader - YAML-based configuration with environment overrides
Provides comprehensive configuration management for test categories and execution
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any

import yaml
from dotenv import load_dotenv

from test_framework.category_system import TestCategory, CategoryPriority, TestOrganizationType, CategorySystem
from test_framework.auto_splitter import SplittingStrategy
from test_framework.fail_fast_strategies import FailFastMode, ThresholdConfig
from test_framework.progress_tracker import ProgressTracker


@dataclass
class CategoryConfigData:
    """Configuration data for a test category"""
    name: str
    description: str = ""
    priority: str = "MEDIUM"
    category_type: str = "functional"
    timeout_seconds: int = 300
    
    # Hierarchy
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    
    # Execution settings
    parallel_safe: bool = True
    requires_real_services: bool = False
    requires_real_llm: bool = False
    requires_environment: Optional[str] = None
    max_parallel_instances: int = 8
    
    # Resource requirements
    memory_intensive: bool = False
    cpu_intensive: bool = False
    network_intensive: bool = False
    database_dependent: bool = False
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    estimated_duration_minutes: float = 5.0
    success_rate_threshold: float = 0.95
    retry_count: int = 0
    
    # Environment-specific overrides
    environment_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ExecutionConfig:
    """Test execution configuration"""
    # Splitting strategy
    splitting_strategy: str = "hybrid"
    target_window_duration_minutes: int = 15
    max_windows: Optional[int] = None
    max_parallel_workers: int = 8
    
    # Fail-fast configuration
    fail_fast_mode: str = "smart_adaptive"
    failure_rate_threshold: float = 0.3
    critical_failure_count: int = 1
    consecutive_failures: int = 5
    evaluation_window_minutes: int = 5
    min_sample_size: int = 10
    
    # Progress tracking
    enable_progress_tracking: bool = True
    auto_save_interval_seconds: int = 30
    enable_persistence: bool = True
    
    # Resource limits
    memory_limit_mb: Optional[int] = None
    cpu_limit_percent: Optional[int] = None
    timeout_minutes: int = 60
    
    # Environment-specific settings
    environment: str = "local"
    use_real_services: bool = False
    use_real_llm: bool = False
    
    # Reporting
    generate_reports: bool = True
    report_formats: List[str] = field(default_factory=lambda: ["json", "html"])
    
    # Environment-specific overrides
    environment_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TestRunnerConfig:
    """Complete test runner configuration"""
    # General settings
    project_name: str = "Netra Tests"
    version: str = "1.0.0"
    
    # Categories
    categories: Dict[str, CategoryConfigData] = field(default_factory=dict)
    
    # Execution
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    
    # Service configurations
    services: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Environment configurations
    environments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Metadata
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    config_version: str = "1.0"


class CategoryConfigLoader:
    """Enhanced configuration loader with YAML support and environment overrides"""
    
    def __init__(self, project_root: Path, config_dir: Optional[Path] = None):
        self.project_root = project_root
        self.config_dir = config_dir or (project_root / "test_framework" / "config")
        
        # Configuration file paths
        self.main_config_file = self.config_dir / "test_config.yaml"
        self.categories_config_file = self.config_dir / "categories.yaml"
        self.execution_config_file = self.config_dir / "execution.yaml"
        self.environments_dir = self.config_dir / "environments"
        
        # Environment configuration
        self.current_environment = get_env().get("TEST_ENVIRONMENT", "local")
        self.load_env_files()
        
        # Loaded configuration
        self._config: Optional[TestRunnerConfig] = None
        self._category_system: Optional[CategorySystem] = None
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_env_files(self):
        """Load environment variables from .env files"""
        env_files = [
            self.project_root / ".env",
            self.project_root / f".env.{self.current_environment}",
            self.config_dir / ".env",
            self.config_dir / f".env.{self.current_environment}"
        ]
        
        for env_file in env_files:
            if env_file.exists():
                load_dotenv(env_file, override=True)
    
    def load_config(self, environment: Optional[str] = None) -> TestRunnerConfig:
        """Load complete configuration with environment overrides"""
        env = environment or self.current_environment
        
        # Load base configuration
        config = self._load_base_config()
        
        # Apply environment-specific overrides
        self._apply_environment_overrides(config, env)
        
        # Apply environment variable overrides
        self._apply_env_var_overrides(config)
        
        # Validate configuration
        self._validate_config(config)
        
        self._config = config
        return config
    
    def _load_base_config(self) -> TestRunnerConfig:
        """Load base configuration from files"""
        config = TestRunnerConfig()
        
        # Load main config if exists
        if self.main_config_file.exists():
            with open(self.main_config_file) as f:
                main_data = yaml.safe_load(f) or {}
            
            config.project_name = main_data.get("project_name", config.project_name)
            config.version = main_data.get("version", config.version)
            config.config_version = main_data.get("config_version", config.config_version)
        
        # Load categories configuration
        config.categories = self._load_categories_config()
        
        # Load execution configuration
        config.execution = self._load_execution_config()
        
        # Load service configurations
        config.services = self._load_service_configs()
        
        # Load environment configurations
        config.environments = self._load_environment_configs()
        
        return config
    
    def _load_categories_config(self) -> Dict[str, CategoryConfigData]:
        """Load categories configuration"""
        categories = {}
        
        if self.categories_config_file.exists():
            with open(self.categories_config_file) as f:
                categories_data = yaml.safe_load(f) or {}
        else:
            # Create default categories config
            categories_data = self._create_default_categories_config()
            self._save_categories_config(categories_data)
        
        # Convert to CategoryConfigData objects
        for name, data in categories_data.get("categories", {}).items():
            categories[name] = CategoryConfigData(
                name=name,
                description=data.get("description", ""),
                priority=data.get("priority", "MEDIUM"),
                category_type=data.get("category_type", "functional"),
                timeout_seconds=data.get("timeout_seconds", 300),
                parent=data.get("parent"),
                children=data.get("children", []),
                dependencies=data.get("dependencies", []),
                conflicts=data.get("conflicts", []),
                parallel_safe=data.get("parallel_safe", True),
                requires_real_services=data.get("requires_real_services", False),
                requires_real_llm=data.get("requires_real_llm", False),
                requires_environment=data.get("requires_environment"),
                max_parallel_instances=data.get("max_parallel_instances", 8),
                memory_intensive=data.get("memory_intensive", False),
                cpu_intensive=data.get("cpu_intensive", False),
                network_intensive=data.get("network_intensive", False),
                database_dependent=data.get("database_dependent", False),
                tags=data.get("tags", []),
                estimated_duration_minutes=data.get("estimated_duration_minutes", 5.0),
                success_rate_threshold=data.get("success_rate_threshold", 0.95),
                retry_count=data.get("retry_count", 0),
                environment_overrides=data.get("environment_overrides", {})
            )
        
        return categories
    
    def _load_execution_config(self) -> ExecutionConfig:
        """Load execution configuration"""
        if self.execution_config_file.exists():
            with open(self.execution_config_file) as f:
                execution_data = yaml.safe_load(f) or {}
        else:
            # Create default execution config
            execution_data = self._create_default_execution_config()
            self._save_execution_config(execution_data)
        
        return ExecutionConfig(
            splitting_strategy=execution_data.get("splitting_strategy", "hybrid"),
            target_window_duration_minutes=execution_data.get("target_window_duration_minutes", 15),
            max_windows=execution_data.get("max_windows"),
            max_parallel_workers=execution_data.get("max_parallel_workers", 8),
            fail_fast_mode=execution_data.get("fail_fast_mode", "smart_adaptive"),
            failure_rate_threshold=execution_data.get("failure_rate_threshold", 0.3),
            critical_failure_count=execution_data.get("critical_failure_count", 1),
            consecutive_failures=execution_data.get("consecutive_failures", 5),
            evaluation_window_minutes=execution_data.get("evaluation_window_minutes", 5),
            min_sample_size=execution_data.get("min_sample_size", 10),
            enable_progress_tracking=execution_data.get("enable_progress_tracking", True),
            auto_save_interval_seconds=execution_data.get("auto_save_interval_seconds", 30),
            enable_persistence=execution_data.get("enable_persistence", True),
            memory_limit_mb=execution_data.get("memory_limit_mb"),
            cpu_limit_percent=execution_data.get("cpu_limit_percent"),
            timeout_minutes=execution_data.get("timeout_minutes", 60),
            environment=execution_data.get("environment", "local"),
            use_real_services=execution_data.get("use_real_services", False),
            use_real_llm=execution_data.get("use_real_llm", False),
            generate_reports=execution_data.get("generate_reports", True),
            report_formats=execution_data.get("report_formats", ["json", "html"]),
            environment_overrides=execution_data.get("environment_overrides", {})
        )
    
    def _load_service_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load service configurations"""
        services_file = self.config_dir / "services.yaml"
        
        if services_file.exists():
            with open(services_file) as f:
                return yaml.safe_load(f) or {}
        
        return {}
    
    def _load_environment_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load environment-specific configurations"""
        environments = {}
        
        if self.environments_dir.exists():
            for env_file in self.environments_dir.glob("*.yaml"):
                env_name = env_file.stem
                with open(env_file) as f:
                    environments[env_name] = yaml.safe_load(f) or {}
        
        return environments
    
    def _apply_environment_overrides(self, config: TestRunnerConfig, environment: str):
        """Apply environment-specific overrides"""
        env_config = config.environments.get(environment, {})
        
        # Apply execution overrides
        execution_overrides = env_config.get("execution", {})
        for key, value in execution_overrides.items():
            if hasattr(config.execution, key):
                setattr(config.execution, key, value)
        
        # Apply category-specific overrides
        categories_overrides = env_config.get("categories", {})
        for category_name, category_overrides in categories_overrides.items():
            if category_name in config.categories:
                category_config = config.categories[category_name]
                
                # Apply overrides from category's environment_overrides
                category_env_overrides = category_config.environment_overrides.get(environment, {})
                for key, value in category_env_overrides.items():
                    if hasattr(category_config, key):
                        setattr(category_config, key, value)
                
                # Apply overrides from environment config
                for key, value in category_overrides.items():
                    if hasattr(category_config, key):
                        setattr(category_config, key, value)
    
    def _apply_env_var_overrides(self, config: TestRunnerConfig):
        """Apply environment variable overrides"""
        # Pattern: TEST_CONFIG_<SECTION>_<KEY>
        pattern = re.compile(r'^TEST_CONFIG_(.+)$')
        
        for env_key, env_value in os.environ.items():
            match = pattern.match(env_key)
            if not match:
                continue
            
            config_path = match.group(1).lower()
            
            # Parse the configuration path
            if config_path.startswith('execution_'):
                # Execution configuration override
                key = config_path[10:]  # Remove 'execution_' prefix
                if hasattr(config.execution, key):
                    # Type conversion
                    value = self._convert_env_value(env_value, getattr(config.execution, key))
                    setattr(config.execution, key, value)
            
            elif config_path.startswith('category_'):
                # Category configuration override
                parts = config_path.split('_', 2)  # category_<name>_<key>
                if len(parts) >= 3:
                    category_name = parts[1]
                    key = parts[2]
                    if category_name in config.categories:
                        category_config = config.categories[category_name]
                        if hasattr(category_config, key):
                            value = self._convert_env_value(env_value, getattr(category_config, key))
                            setattr(category_config, key, value)
            
            elif hasattr(config, config_path):
                # Top-level configuration override
                value = self._convert_env_value(env_value, getattr(config, config_path))
                setattr(config, config_path, value)
    
    def _convert_env_value(self, env_value: str, current_value: Any) -> Any:
        """Convert environment variable string to appropriate type"""
        if current_value is None:
            return env_value
        
        if isinstance(current_value, bool):
            return env_value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(current_value, int):
            try:
                return int(env_value)
            except ValueError:
                return current_value
        elif isinstance(current_value, float):
            try:
                return float(env_value)
            except ValueError:
                return current_value
        elif isinstance(current_value, list):
            # Split by comma and strip whitespace
            return [item.strip() for item in env_value.split(',') if item.strip()]
        elif isinstance(current_value, set):
            return set(item.strip() for item in env_value.split(',') if item.strip())
        else:
            return env_value
    
    def _validate_config(self, config: TestRunnerConfig):
        """Validate configuration for consistency and correctness"""
        errors = []
        
        # Validate execution configuration
        execution = config.execution
        
        if execution.target_window_duration_minutes <= 0:
            errors.append("target_window_duration_minutes must be positive")
        
        if execution.max_parallel_workers <= 0:
            errors.append("max_parallel_workers must be positive")
        
        if not (0 <= execution.failure_rate_threshold <= 1):
            errors.append("failure_rate_threshold must be between 0 and 1")
        
        if execution.critical_failure_count < 0:
            errors.append("critical_failure_count must be non-negative")
        
        # Validate splitting strategy
        try:
            SplittingStrategy(execution.splitting_strategy)
        except ValueError:
            errors.append(f"Invalid splitting_strategy: {execution.splitting_strategy}")
        
        # Validate fail-fast mode
        try:
            FailFastMode(execution.fail_fast_mode)
        except ValueError:
            errors.append(f"Invalid fail_fast_mode: {execution.fail_fast_mode}")
        
        # Validate categories
        for name, category in config.categories.items():
            # Validate priority
            try:
                CategoryPriority[category.priority]
            except KeyError:
                errors.append(f"Invalid priority for category {name}: {category.priority}")
            
            # Validate category type
            try:
                TestOrganizationType(category.category_type)
            except ValueError:
                errors.append(f"Invalid category_type for category {name}: {category.category_type}")
            
            # Check dependency consistency
            for dep in category.dependencies:
                if dep not in config.categories:
                    errors.append(f"Category {name} depends on non-existent category: {dep}")
            
            # Check conflict consistency
            for conflict in category.conflicts:
                if conflict not in config.categories:
                    errors.append(f"Category {name} conflicts with non-existent category: {conflict}")
        
        if errors:
            raise ValueError(f"Configuration validation errors:\n" + "\n".join(f"  - {error}" for error in errors))
    
    def create_category_system(self, config: Optional[TestRunnerConfig] = None) -> CategorySystem:
        """Create CategorySystem from configuration"""
        if not config:
            config = self._config or self.load_config()
        
        category_system = CategorySystem(self.project_root)
        
        # Clear default categories and add configured ones
        category_system.categories.clear()
        
        for name, category_config in config.categories.items():
            test_category = TestCategory(
                name=name,
                description=category_config.description,
                priority=CategoryPriority[category_config.priority],
                category_type=TestOrganizationType(category_config.category_type),
                timeout_seconds=category_config.timeout_seconds,
                parent=category_config.parent,
                children=set(category_config.children),
                dependencies=set(category_config.dependencies),
                conflicts=set(category_config.conflicts),
                parallel_safe=category_config.parallel_safe,
                requires_real_services=category_config.requires_real_services,
                requires_real_llm=category_config.requires_real_llm,
                requires_environment=category_config.requires_environment,
                max_parallel_instances=category_config.max_parallel_instances,
                memory_intensive=category_config.memory_intensive,
                cpu_intensive=category_config.cpu_intensive,
                network_intensive=category_config.network_intensive,
                database_dependent=category_config.database_dependent,
                tags=set(category_config.tags),
                estimated_duration=timedelta(minutes=category_config.estimated_duration_minutes),
                success_rate_threshold=category_config.success_rate_threshold,
                retry_count=category_config.retry_count
            )
            
            category_system.add_category(test_category)
        
        self._category_system = category_system
        return category_system
    
    def create_progress_tracker(self, config: Optional[TestRunnerConfig] = None) -> ProgressTracker:
        """Create ProgressTracker from configuration"""
        if not config:
            config = self._config or self.load_config()
        
        execution = config.execution
        
        return ProgressTracker(
            project_root=self.project_root,
            enable_persistence=execution.enable_persistence,
            auto_save_interval=execution.auto_save_interval_seconds
        )
    
    def create_threshold_config(self, config: Optional[TestRunnerConfig] = None) -> ThresholdConfig:
        """Create ThresholdConfig from configuration"""
        if not config:
            config = self._config or self.load_config()
        
        execution = config.execution
        
        # Create category-specific thresholds
        category_thresholds = {}
        for name, category_config in config.categories.items():
            category_thresholds[name] = category_config.success_rate_threshold
        
        return ThresholdConfig(
            failure_rate_threshold=execution.failure_rate_threshold,
            critical_failure_count=execution.critical_failure_count,
            consecutive_failures=execution.consecutive_failures,
            time_window=timedelta(minutes=execution.evaluation_window_minutes),
            category_thresholds=category_thresholds,
            min_sample_size=execution.min_sample_size
        )
    
    def _create_default_categories_config(self) -> Dict[str, Any]:
        """Create default categories configuration"""
        return {
            "categories": {
                "smoke": {
                    "description": "Quick validation tests for pre-commit checks",
                    "priority": "CRITICAL",
                    "category_type": "quality",
                    "timeout_seconds": 60,
                    "estimated_duration_minutes": 1.0,
                    "max_parallel_instances": 4,
                    "tags": ["pre-commit", "quick", "validation"]
                },
                "unit": {
                    "description": "Unit tests for individual components",
                    "priority": "HIGH",
                    "category_type": "functional",
                    "timeout_seconds": 300,
                    "estimated_duration_minutes": 5.0,
                    "parallel_safe": True,
                    "max_parallel_instances": 8,
                    "tags": ["unit", "components", "isolated"]
                },
                "integration": {
                    "description": "Integration tests for feature validation",
                    "priority": "MEDIUM",
                    "category_type": "integration",
                    "timeout_seconds": 600,
                    "estimated_duration_minutes": 10.0,
                    "dependencies": ["unit", "database"],
                    "network_intensive": True,
                    "tags": ["integration", "features", "services"]
                },
                "database": {
                    "description": "Database and data persistence tests",
                    "priority": "HIGH",
                    "category_type": "technical",
                    "timeout_seconds": 300,
                    "estimated_duration_minutes": 5.0,
                    "database_dependent": True,
                    "memory_intensive": True,
                    "conflicts": ["performance"],
                    "tags": ["database", "persistence", "data"]
                },
                "api": {
                    "description": "API endpoint and route tests",
                    "priority": "MEDIUM",
                    "category_type": "functional",
                    "timeout_seconds": 300,
                    "estimated_duration_minutes": 5.0,
                    "dependencies": ["database"],
                    "network_intensive": True,
                    "tags": ["api", "endpoints", "routes"]
                },
                "websocket": {
                    "description": "WebSocket communication tests",
                    "priority": "MEDIUM",
                    "category_type": "technical",
                    "timeout_seconds": 300,
                    "estimated_duration_minutes": 5.0,
                    "dependencies": ["unit"],
                    "network_intensive": True,
                    "max_parallel_instances": 4,
                    "tags": ["websocket", "realtime", "communication"]
                },
                "frontend": {
                    "description": "React component and UI tests",
                    "priority": "LOW",
                    "category_type": "functional",
                    "timeout_seconds": 300,
                    "estimated_duration_minutes": 5.0,
                    "parallel_safe": True,
                    "max_parallel_instances": 6,
                    "tags": ["frontend", "ui", "react"]
                },
                "e2e": {
                    "description": "End-to-end user journey tests",
                    "priority": "LOW",
                    "category_type": "e2e",
                    "timeout_seconds": 1800,
                    "estimated_duration_minutes": 30.0,
                    "dependencies": ["integration", "api", "frontend"],
                    "requires_real_services": True,
                    "parallel_safe": False,
                    "max_parallel_instances": 2,
                    "conflicts": ["performance"],
                    "tags": ["e2e", "user-journeys", "end-to-end"]
                },
                "performance": {
                    "description": "Performance and load tests",
                    "priority": "LOW",
                    "category_type": "performance",
                    "timeout_seconds": 1800,
                    "estimated_duration_minutes": 30.0,
                    "dependencies": ["integration"],
                    "parallel_safe": False,
                    "cpu_intensive": True,
                    "memory_intensive": True,
                    "network_intensive": True,
                    "conflicts": ["database", "e2e"],
                    "tags": ["performance", "load", "stress"]
                }
            }
        }
    
    def _create_default_execution_config(self) -> Dict[str, Any]:
        """Create default execution configuration"""
        return {
            "splitting_strategy": "hybrid",
            "target_window_duration_minutes": 15,
            "max_parallel_workers": 8,
            "fail_fast_mode": "smart_adaptive",
            "failure_rate_threshold": 0.3,
            "critical_failure_count": 1,
            "consecutive_failures": 5,
            "evaluation_window_minutes": 5,
            "min_sample_size": 10,
            "enable_progress_tracking": True,
            "auto_save_interval_seconds": 30,
            "enable_persistence": True,
            "timeout_minutes": 60,
            "environment": "local",
            "use_real_services": False,
            "use_real_llm": False,
            "generate_reports": True,
            "report_formats": ["json", "html"]
        }
    
    def _save_categories_config(self, categories_data: Dict[str, Any]):
        """Save categories configuration to file"""
        with open(self.categories_config_file, 'w') as f:
            yaml.dump(categories_data, f, default_flow_style=False, sort_keys=False)
    
    def _save_execution_config(self, execution_data: Dict[str, Any]):
        """Save execution configuration to file"""
        with open(self.execution_config_file, 'w') as f:
            yaml.dump(execution_data, f, default_flow_style=False)
    
    def save_config(self, config: TestRunnerConfig):
        """Save complete configuration to files"""
        # Save main config
        main_data = {
            "project_name": config.project_name,
            "version": config.version,
            "config_version": config.config_version
        }
        
        with open(self.main_config_file, 'w') as f:
            yaml.dump(main_data, f, default_flow_style=False)
        
        # Save categories config
        categories_data = {
            "categories": {
                name: {
                    "description": cat.description,
                    "priority": cat.priority,
                    "category_type": cat.category_type,
                    "timeout_seconds": cat.timeout_seconds,
                    "parent": cat.parent,
                    "children": cat.children,
                    "dependencies": cat.dependencies,
                    "conflicts": cat.conflicts,
                    "parallel_safe": cat.parallel_safe,
                    "requires_real_services": cat.requires_real_services,
                    "requires_real_llm": cat.requires_real_llm,
                    "requires_environment": cat.requires_environment,
                    "max_parallel_instances": cat.max_parallel_instances,
                    "memory_intensive": cat.memory_intensive,
                    "cpu_intensive": cat.cpu_intensive,
                    "network_intensive": cat.network_intensive,
                    "database_dependent": cat.database_dependent,
                    "tags": cat.tags,
                    "estimated_duration_minutes": cat.estimated_duration_minutes,
                    "success_rate_threshold": cat.success_rate_threshold,
                    "retry_count": cat.retry_count,
                    "environment_overrides": cat.environment_overrides
                }
                for name, cat in config.categories.items()
            }
        }
        
        self._save_categories_config(categories_data)
        
        # Save execution config
        execution_data = {
            "splitting_strategy": config.execution.splitting_strategy,
            "target_window_duration_minutes": config.execution.target_window_duration_minutes,
            "max_windows": config.execution.max_windows,
            "max_parallel_workers": config.execution.max_parallel_workers,
            "fail_fast_mode": config.execution.fail_fast_mode,
            "failure_rate_threshold": config.execution.failure_rate_threshold,
            "critical_failure_count": config.execution.critical_failure_count,
            "consecutive_failures": config.execution.consecutive_failures,
            "evaluation_window_minutes": config.execution.evaluation_window_minutes,
            "min_sample_size": config.execution.min_sample_size,
            "enable_progress_tracking": config.execution.enable_progress_tracking,
            "auto_save_interval_seconds": config.execution.auto_save_interval_seconds,
            "enable_persistence": config.execution.enable_persistence,
            "memory_limit_mb": config.execution.memory_limit_mb,
            "cpu_limit_percent": config.execution.cpu_limit_percent,
            "timeout_minutes": config.execution.timeout_minutes,
            "environment": config.execution.environment,
            "use_real_services": config.execution.use_real_services,
            "use_real_llm": config.execution.use_real_llm,
            "generate_reports": config.execution.generate_reports,
            "report_formats": config.execution.report_formats,
            "environment_overrides": config.execution.environment_overrides
        }
        
        self._save_execution_config(execution_data)
        
        # Save services config if not empty
        if config.services:
            services_file = self.config_dir / "services.yaml"
            with open(services_file, 'w') as f:
                yaml.dump(config.services, f, default_flow_style=False)
        
        # Save environment configs
        self.environments_dir.mkdir(exist_ok=True)
        for env_name, env_config in config.environments.items():
            env_file = self.environments_dir / f"{env_name}.yaml"
            with open(env_file, 'w') as f:
                yaml.dump(env_config, f, default_flow_style=False)
    
    def export_config_template(self, output_path: Path):
        """Export a configuration template"""
        template = {
            "# Netra Test Runner Configuration Template": None,
            "project_name": "My Project Tests",
            "version": "1.0.0",
            "config_version": "1.0",
            
            "execution": {
                "splitting_strategy": "hybrid",
                "target_window_duration_minutes": 15,
                "max_parallel_workers": 8,
                "fail_fast_mode": "smart_adaptive",
                "failure_rate_threshold": 0.3,
                "critical_failure_count": 1,
                "consecutive_failures": 5,
                "evaluation_window_minutes": 5,
                "enable_progress_tracking": True,
                "generate_reports": True,
                "report_formats": ["json", "html"]
            },
            
            "categories": {
                "example_category": {
                    "description": "Example test category",
                    "priority": "MEDIUM",
                    "category_type": "functional",
                    "timeout_seconds": 300,
                    "parallel_safe": True,
                    "estimated_duration_minutes": 5.0,
                    "tags": ["example"],
                    "environment_overrides": {
                        "staging": {
                            "timeout_seconds": 600,
                            "requires_real_services": True
                        }
                    }
                }
            },
            
            "environments": {
                "staging": {
                    "execution": {
                        "use_real_services": True,
                        "timeout_minutes": 120
                    }
                }
            }
        }
        
        # Remove the comment key
        del template["# Netra Test Runner Configuration Template"]
        
        with open(output_path, 'w') as f:
            f.write("# Netra Test Runner Configuration Template\n")
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
    
    def get_config_summary(self, config: Optional[TestRunnerConfig] = None) -> Dict[str, Any]:
        """Get configuration summary"""
        if not config:
            config = self._config or self.load_config()
        
        return {
            "project_name": config.project_name,
            "version": config.version,
            "environment": config.execution.environment,
            "total_categories": len(config.categories),
            "categories_by_priority": {
                priority: len([cat for cat in config.categories.values() if cat.priority == priority])
                for priority in set(cat.priority for cat in config.categories.values())
            },
            "execution_config": {
                "splitting_strategy": config.execution.splitting_strategy,
                "fail_fast_mode": config.execution.fail_fast_mode,
                "max_parallel_workers": config.execution.max_parallel_workers,
                "target_window_duration": config.execution.target_window_duration_minutes,
                "progress_tracking_enabled": config.execution.enable_progress_tracking
            },
            "feature_flags": {
                "real_services": config.execution.use_real_services,
                "real_llm": config.execution.use_real_llm,
                "progress_persistence": config.execution.enable_persistence
            }
        }
    
    def validate_environment(self, environment: str) -> List[str]:
        """Validate environment configuration"""
        warnings = []
        
        # Check if environment configuration exists
        if environment not in self.environments_dir.glob("*.yaml"):
            warnings.append(f"No configuration file found for environment '{environment}'")
        
        # Check environment variables
        required_env_vars = {
            "staging": ["STAGING_URL", "STAGING_API_URL"],
            "production": ["PRODUCTION_URL", "PRODUCTION_API_URL"],
            "docker": ["DOCKER_HOST"]
        }
        
        if environment in required_env_vars:
            for var in required_env_vars[environment]:
                if not get_env().get(var):
                    warnings.append(f"Environment variable '{var}' not set for environment '{environment}'")
        
        return warnings
