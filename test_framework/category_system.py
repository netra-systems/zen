#!/usr/bin/env python3
"""
Test Category System - Enhanced categorization with hierarchy support
Provides comprehensive test categorization with dependencies and execution planning
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union


class CategoryPriority(Enum):
    """Category execution priorities"""
    CRITICAL = 1    # Must run first (smoke, auth, startup)
    HIGH = 2        # High priority (unit, security, database) 
    MEDIUM = 3      # Medium priority (integration, api, websocket)
    LOW = 4         # Lower priority (performance, e2e)
    OPTIONAL = 5    # Optional (experimental, legacy)


class TestOrganizationType(Enum):
    """Test organization types for categorization purposes."""
    FUNCTIONAL = "functional"       # Feature-based tests
    TECHNICAL = "technical"         # Implementation-based tests
    QUALITY = "quality"            # Quality assurance tests
    INTEGRATION = "integration"     # Cross-service tests
    PERFORMANCE = "performance"     # Performance/load tests
    SECURITY = "security"          # Security/auth tests
    E2E = "e2e"                    # End-to-end tests


# Backward compatibility alias - DEPRECATED: Use TestOrganizationType instead  
CategoryType = TestOrganizationType


@dataclass
class TestCategory:
    """Enhanced test category with full hierarchy and dependency support"""
    name: str
    description: str
    priority: CategoryPriority = CategoryPriority.MEDIUM
    category_type: TestOrganizationType = TestOrganizationType.FUNCTIONAL
    timeout_seconds: int = 300
    
    # Hierarchy and relationships
    parent: Optional[str] = None
    children: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    conflicts: Set[str] = field(default_factory=set)
    
    # Execution configuration
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
    tags: Set[str] = field(default_factory=set)
    estimated_duration: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    success_rate_threshold: float = 0.95
    retry_count: int = 0
    
    # Historical data
    average_duration: Optional[timedelta] = None
    success_rate: Optional[float] = None
    last_run: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize computed properties"""
        if isinstance(self.children, (list, tuple)):
            self.children = set(self.children)
        if isinstance(self.dependencies, (list, tuple)):
            self.dependencies = set(self.dependencies)
        if isinstance(self.conflicts, (list, tuple)):
            self.conflicts = set(self.conflicts)
        if isinstance(self.tags, (list, tuple)):
            self.tags = set(self.tags)
    
    def is_leaf_category(self) -> bool:
        """Check if this is a leaf category (no children)"""
        return len(self.children) == 0
    
    def is_root_category(self) -> bool:
        """Check if this is a root category (no parent)"""
        return self.parent is None
    
    def get_full_hierarchy_path(self, category_system: 'CategorySystem') -> List[str]:
        """Get the full hierarchy path from root to this category"""
        path = [self.name]
        current = self
        
        while current.parent:
            parent_category = category_system.get_category(current.parent)
            if not parent_category:
                break
            path.insert(0, parent_category.name)
            current = parent_category
        
        return path
    
    def can_run_with(self, other_category: 'TestCategory') -> bool:
        """Check if this category can run in parallel with another"""
        if not self.parallel_safe or not other_category.parallel_safe:
            return False
        
        if self.name in other_category.conflicts or other_category.name in self.conflicts:
            return False
        
        # Resource conflict detection
        if (self.memory_intensive and other_category.memory_intensive or
            self.cpu_intensive and other_category.cpu_intensive or
            (self.database_dependent and other_category.database_dependent and 
             self.requires_environment == other_category.requires_environment)):
            return False
        
        return True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "priority": self.priority.name,
            "category_type": self.category_type.value,
            "timeout_seconds": self.timeout_seconds,
            "parent": self.parent,
            "children": list(self.children),
            "dependencies": list(self.dependencies),
            "conflicts": list(self.conflicts),
            "parallel_safe": self.parallel_safe,
            "requires_real_services": self.requires_real_services,
            "requires_real_llm": self.requires_real_llm,
            "requires_environment": self.requires_environment,
            "max_parallel_instances": self.max_parallel_instances,
            "memory_intensive": self.memory_intensive,
            "cpu_intensive": self.cpu_intensive,
            "network_intensive": self.network_intensive,
            "database_dependent": self.database_dependent,
            "tags": list(self.tags),
            "estimated_duration": self.estimated_duration.total_seconds(),
            "success_rate_threshold": self.success_rate_threshold,
            "retry_count": self.retry_count,
            "average_duration": self.average_duration.total_seconds() if self.average_duration else None,
            "success_rate": self.success_rate,
            "last_run": self.last_run.isoformat() if self.last_run else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TestCategory':
        """Create from dictionary"""
        category = cls(
            name=data["name"],
            description=data["description"],
            priority=CategoryPriority[data.get("priority", "MEDIUM")],
            category_type=TestOrganizationType(data.get("category_type", "functional")),
            timeout_seconds=data.get("timeout_seconds", 300),
            parent=data.get("parent"),
            children=set(data.get("children", [])),
            dependencies=set(data.get("dependencies", [])),
            conflicts=set(data.get("conflicts", [])),
            parallel_safe=data.get("parallel_safe", True),
            requires_real_services=data.get("requires_real_services", False),
            requires_real_llm=data.get("requires_real_llm", False),
            requires_environment=data.get("requires_environment"),
            max_parallel_instances=data.get("max_parallel_instances", 8),
            memory_intensive=data.get("memory_intensive", False),
            cpu_intensive=data.get("cpu_intensive", False),
            network_intensive=data.get("network_intensive", False),
            database_dependent=data.get("database_dependent", False),
            tags=set(data.get("tags", [])),
            estimated_duration=timedelta(seconds=data.get("estimated_duration", 300)),
            success_rate_threshold=data.get("success_rate_threshold", 0.95),
            retry_count=data.get("retry_count", 0)
        )
        
        # Set historical data if available
        if data.get("average_duration"):
            category.average_duration = timedelta(seconds=data["average_duration"])
        if data.get("success_rate") is not None:
            category.success_rate = data["success_rate"]
        if data.get("last_run"):
            category.last_run = datetime.fromisoformat(data["last_run"])
        
        return category


@dataclass
class ExecutionPlan:
    """Execution plan for test categories with dependencies resolved"""
    phases: List[List[str]] = field(default_factory=list)  # List of parallel execution phases
    total_estimated_duration: timedelta = field(default_factory=lambda: timedelta(0))
    dependency_graph: Dict[str, Set[str]] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    parallel_groups: Dict[int, List[str]] = field(default_factory=dict)
    requested_categories: Set[str] = field(default_factory=set)  # Originally requested categories (not dependencies)
    
    def get_phase_for_category(self, category_name: str) -> int:
        """Get the execution phase number for a category"""
        for phase_num, phase_categories in enumerate(self.phases):
            if category_name in phase_categories:
                return phase_num
        return -1
    
    def can_start_category(self, category_name: str, completed_categories: Set[str]) -> bool:
        """Check if a category can start based on completed dependencies"""
        dependencies = self.dependency_graph.get(category_name, set())
        return dependencies.issubset(completed_categories)


class CategorySystem:
    """Enhanced category management system with hierarchy and dependency resolution"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.categories: Dict[str, TestCategory] = {}
        self._initialize_default_categories()
    
    def _initialize_default_categories(self):
        """Initialize default test categories with enhanced configuration"""
        default_categories = [
            # Critical categories - must run first
            TestCategory(
                name="mission_critical",
                description="Business-critical tests protecting core functionality",
                priority=CategoryPriority.CRITICAL,
                category_type=TestOrganizationType.QUALITY,
                timeout_seconds=1200,  # 20 minutes for comprehensive tests
                estimated_duration=timedelta(minutes=15),
                max_parallel_instances=4,
                database_dependent=True,
                network_intensive=True,
                tags={"mission-critical", "business-value", "core", "deployment"}
            ),
            TestCategory(
                name="smoke",
                description="Quick validation tests for pre-commit checks",
                priority=CategoryPriority.CRITICAL,
                category_type=TestOrganizationType.QUALITY,
                timeout_seconds=60,
                estimated_duration=timedelta(minutes=1),
                max_parallel_instances=4,
                tags={"pre-commit", "quick", "validation"}
            ),
            TestCategory(
                name="startup", 
                description="System startup and initialization tests",
                priority=CategoryPriority.CRITICAL,
                category_type=TestOrganizationType.TECHNICAL,
                timeout_seconds=180,
                estimated_duration=timedelta(minutes=3),
                database_dependent=True,
                tags={"startup", "initialization"}
            ),
            
            # High priority categories
            TestCategory(
                name="unit",
                description="Unit tests for individual components",
                priority=CategoryPriority.HIGH,
                category_type=TestOrganizationType.FUNCTIONAL,
                timeout_seconds=300,
                estimated_duration=timedelta(minutes=5),
                parallel_safe=True,
                max_parallel_instances=8,
                tags={"unit", "components", "isolated"}
            ),
            TestCategory(
                name="security",
                description="Security and authentication tests",
                priority=CategoryPriority.HIGH,
                category_type=TestOrganizationType.SECURITY,
                timeout_seconds=300,
                estimated_duration=timedelta(minutes=5),
                database_dependent=True,
                tags={"security", "auth", "validation"}
            ),
            TestCategory(
                name="database",
                description="Database and data persistence tests", 
                priority=CategoryPriority.HIGH,
                category_type=TestOrganizationType.TECHNICAL,
                timeout_seconds=300,
                estimated_duration=timedelta(minutes=5),
                database_dependent=True,
                memory_intensive=True,
                conflicts={"performance"},
                tags={"database", "persistence", "data"}
            ),
            
            # Medium priority categories
            TestCategory(
                name="integration",
                description="Integration tests for feature validation",
                priority=CategoryPriority.MEDIUM,
                category_type=TestOrganizationType.INTEGRATION,
                timeout_seconds=600,
                estimated_duration=timedelta(minutes=10),
                dependencies={"unit", "database"},
                network_intensive=True,
                tags={"integration", "features", "services"}
            ),
            TestCategory(
                name="api",
                description="API endpoint and route tests",
                priority=CategoryPriority.MEDIUM,
                category_type=TestOrganizationType.FUNCTIONAL,
                timeout_seconds=300,
                estimated_duration=timedelta(minutes=5),
                dependencies={"database"},
                network_intensive=True,
                tags={"api", "endpoints", "routes"}
            ),
            TestCategory(
                name="websocket",
                description="WebSocket communication tests",
                priority=CategoryPriority.MEDIUM,
                category_type=TestOrganizationType.TECHNICAL,
                timeout_seconds=300,
                estimated_duration=timedelta(minutes=5),
                dependencies={"unit"},
                network_intensive=True,
                max_parallel_instances=4,
                tags={"websocket", "realtime", "communication"}
            ),
            TestCategory(
                name="agent",
                description="AI agent and workflow tests",
                priority=CategoryPriority.MEDIUM,
                category_type=TestOrganizationType.FUNCTIONAL,
                timeout_seconds=600,
                estimated_duration=timedelta(minutes=10),
                dependencies={"unit", "database"},
                memory_intensive=True,
                max_parallel_instances=4,
                tags={"agents", "ai", "workflows"}
            ),
            
            # Lower priority categories
            TestCategory(
                name="frontend",
                description="React component and UI tests",
                priority=CategoryPriority.LOW,
                category_type=TestOrganizationType.FUNCTIONAL,
                timeout_seconds=300,
                estimated_duration=timedelta(minutes=5),
                parallel_safe=True,
                max_parallel_instances=6,
                tags={"frontend", "ui", "react"}
            ),
            TestCategory(
                name="performance",
                description="Performance and load tests",
                priority=CategoryPriority.LOW,
                category_type=TestOrganizationType.PERFORMANCE,
                timeout_seconds=1800,
                estimated_duration=timedelta(minutes=30),
                dependencies={"integration"},
                parallel_safe=False,
                cpu_intensive=True,
                memory_intensive=True,
                network_intensive=True,
                conflicts={"database", "e2e"},
                tags={"performance", "load", "stress"}
            ),
            TestCategory(
                name="e2e",
                description="End-to-end user journey tests",
                priority=CategoryPriority.LOW,
                category_type=TestOrganizationType.E2E,
                timeout_seconds=1800,
                estimated_duration=timedelta(minutes=30),
                dependencies={"integration", "api", "frontend"},
                requires_real_services=True,
                parallel_safe=False,
                max_parallel_instances=2,
                conflicts={"performance"},
                tags={"e2e", "user-journeys", "end-to-end"}
            ),
            
            # Real service categories  
            TestCategory(
                name="real_e2e",
                description="E2E tests with real LLM calls and services",
                priority=CategoryPriority.LOW,
                category_type=TestOrganizationType.E2E,
                timeout_seconds=1800,
                estimated_duration=timedelta(minutes=30),
                dependencies={"e2e"},
                requires_real_services=True,
                requires_real_llm=True,
                parallel_safe=False,
                max_parallel_instances=1,
                network_intensive=True,
                tags={"real", "e2e", "llm", "external"}
            ),
            TestCategory(
                name="real_services",
                description="Service integration tests with real services",
                priority=CategoryPriority.LOW,
                category_type=TestOrganizationType.INTEGRATION,
                timeout_seconds=900,
                estimated_duration=timedelta(minutes=15),
                dependencies={"integration"},
                requires_real_services=True,
                max_parallel_instances=2,
                network_intensive=True,
                tags={"real", "services", "integration", "external"}
            )
        ]
        
        for category in default_categories:
            self.categories[category.name] = category
        
        # Update parent-child relationships
        self._update_parent_child_relationships()
    
    def _update_parent_child_relationships(self):
        """Update parent-child relationships based on dependencies"""
        # For now, keep flat structure but this could be enhanced
        # to create hierarchical relationships based on logical groupings
        pass
    
    def add_category(self, category: TestCategory) -> None:
        """Add a new category to the system"""
        self.categories[category.name] = category
        
        # Update relationships
        if category.parent and category.parent in self.categories:
            self.categories[category.parent].children.add(category.name)
        
        for child_name in category.children:
            if child_name in self.categories:
                self.categories[child_name].parent = category.name
    
    def remove_category(self, name: str) -> bool:
        """Remove a category and update relationships"""
        if name not in self.categories:
            return False
        
        category = self.categories[name]
        
        # Update parent-child relationships
        if category.parent and category.parent in self.categories:
            self.categories[category.parent].children.discard(name)
        
        for child_name in category.children:
            if child_name in self.categories:
                self.categories[child_name].parent = None
        
        # Remove from dependencies and conflicts
        for cat in self.categories.values():
            cat.dependencies.discard(name)
            cat.conflicts.discard(name)
        
        del self.categories[name]
        return True
    
    def get_category(self, name: str) -> Optional[TestCategory]:
        """Get category by name"""
        return self.categories.get(name)
    
    def get_categories_by_priority(self, priority: CategoryPriority) -> List[TestCategory]:
        """Get all categories with specified priority"""
        return [cat for cat in self.categories.values() if cat.priority == priority]
    
    def get_categories_by_type(self, category_type: TestOrganizationType) -> List[TestCategory]:
        """Get all categories of specified type"""
        return [cat for cat in self.categories.values() if cat.category_type == category_type]
    
    def get_leaf_categories(self) -> List[TestCategory]:
        """Get all leaf categories (no children)"""
        return [cat for cat in self.categories.values() if cat.is_leaf_category()]
    
    def get_root_categories(self) -> List[TestCategory]:
        """Get all root categories (no parent)"""
        return [cat for cat in self.categories.values() if cat.is_root_category()]
    
    def create_execution_plan(self, selected_categories: List[str], 
                            max_parallel: int = 8, skip_dependencies: bool = False) -> ExecutionPlan:
        """Create optimized execution plan with dependency resolution"""
        # Validate categories exist
        valid_categories = [name for name in selected_categories if name in self.categories]
        
        if not valid_categories:
            return ExecutionPlan()
        
        # Add dependencies automatically (unless skipped)
        if skip_dependencies:
            all_required = valid_categories
        else:
            all_required = self._resolve_dependencies(valid_categories)
        
        # Topological sort for dependency order
        execution_order = self._topological_sort(all_required)
        
        # Create parallel execution phases
        phases = self._create_parallel_phases(execution_order, max_parallel)
        
        # Calculate total estimated duration
        total_duration = self._calculate_parallel_duration(phases)
        
        # Build dependency graph
        dependency_graph = {
            name: self.categories[name].dependencies.intersection(set(all_required))
            for name in all_required
        }
        
        # Create parallel groups
        parallel_groups = {i: phase for i, phase in enumerate(phases)}
        
        return ExecutionPlan(
            phases=phases,
            total_estimated_duration=total_duration,
            dependency_graph=dependency_graph,
            execution_order=execution_order,
            parallel_groups=parallel_groups,
            requested_categories=set(valid_categories)  # Track originally requested categories
        )
    
    def _resolve_dependencies(self, category_names: List[str]) -> List[str]:
        """Resolve all dependencies recursively"""
        resolved = set()
        to_process = set(category_names)
        
        while to_process:
            current = to_process.pop()
            if current in resolved or current not in self.categories:
                continue
            
            resolved.add(current)
            category = self.categories[current]
            
            # Add dependencies that aren't already resolved
            for dep in category.dependencies:
                if dep not in resolved and dep in self.categories:
                    to_process.add(dep)
        
        return list(resolved)
    
    def _topological_sort(self, category_names: List[str]) -> List[str]:
        """Topological sort of categories based on dependencies"""
        # Build adjacency list
        graph = {name: [] for name in category_names}
        in_degree = {name: 0 for name in category_names}
        
        for name in category_names:
            if name not in self.categories:
                continue
                
            category = self.categories[name]
            for dep in category.dependencies:
                if dep in category_names:
                    graph[dep].append(name)
                    in_degree[name] += 1
        
        # Kahn's algorithm with priority consideration
        queue = []
        
        # Start with nodes that have no dependencies, sorted by priority
        for name in category_names:
            if in_degree[name] == 0:
                priority = self.categories[name].priority.value if name in self.categories else 999
                queue.append((priority, name))
        
        queue.sort()  # Sort by priority
        result = []
        
        while queue:
            priority, current = queue.pop(0)
            result.append(current)
            
            # Process neighbors
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    neighbor_priority = self.categories[neighbor].priority.value if neighbor in self.categories else 999
                    queue.append((neighbor_priority, neighbor))
                    queue.sort()  # Re-sort after adding
        
        if len(result) != len(category_names):
            raise ValueError("Circular dependency detected in categories")
        
        return result
    
    def _create_parallel_phases(self, execution_order: List[str], 
                              max_parallel: int) -> List[List[str]]:
        """Create parallel execution phases respecting constraints"""
        phases = []
        remaining = execution_order.copy()
        
        while remaining:
            current_phase = []
            used_slots = 0
            conflicts_in_phase = set()
            
            # Process categories in priority order
            for category_name in remaining[:]:
                if used_slots >= max_parallel:
                    break
                
                category = self.categories.get(category_name)
                if not category:
                    remaining.remove(category_name)
                    continue
                
                # Check if dependencies are satisfied
                deps_satisfied = all(
                    dep_name in [cat for phase in phases for cat in phase]
                    for dep_name in category.dependencies
                    if dep_name in execution_order
                )
                
                if not deps_satisfied:
                    continue
                
                # Check conflicts
                if category.conflicts.intersection(conflicts_in_phase):
                    continue
                
                # Check parallel compatibility with current phase
                can_run_parallel = True
                for other_name in current_phase:
                    other_category = self.categories.get(other_name)
                    if other_category and not category.can_run_with(other_category):
                        can_run_parallel = False
                        break
                
                if can_run_parallel:
                    current_phase.append(category_name)
                    conflicts_in_phase.update(category.conflicts)
                    used_slots += 1
                    remaining.remove(category_name)
            
            if current_phase:
                phases.append(current_phase)
            elif remaining:
                # Force add one category to prevent infinite loop
                category_name = remaining.pop(0)
                phases.append([category_name])
        
        return phases
    
    def _calculate_parallel_duration(self, phases: List[List[str]]) -> timedelta:
        """Calculate total duration considering parallel execution"""
        total_duration = timedelta(0)
        
        for phase in phases:
            phase_duration = timedelta(0)
            
            for category_name in phase:
                category = self.categories.get(category_name)
                if category:
                    duration = category.average_duration or category.estimated_duration
                    phase_duration = max(phase_duration, duration)
            
            total_duration += phase_duration
        
        return total_duration
    
    def update_category_history(self, name: str, duration: timedelta, 
                              success: bool) -> None:
        """Update category historical performance data"""
        if name not in self.categories:
            return
        
        category = self.categories[name]
        category.last_run = datetime.now()
        
        # Update average duration (simple moving average)
        if category.average_duration:
            category.average_duration = (category.average_duration + duration) / 2
        else:
            category.average_duration = duration
        
        # Update success rate (simple moving average)
        if category.success_rate is not None:
            category.success_rate = (category.success_rate * 0.8) + (1.0 if success else 0.0) * 0.2
        else:
            category.success_rate = 1.0 if success else 0.0
    
    def export_categories(self, output_path: Path) -> None:
        """Export categories to JSON file"""
        data = {
            "categories": {name: cat.to_dict() for name, cat in self.categories.items()},
            "exported_at": datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def import_categories(self, input_path: Path) -> None:
        """Import categories from JSON file"""
        if not input_path.exists():
            return
        
        with open(input_path) as f:
            data = json.load(f)
        
        for name, cat_data in data.get("categories", {}).items():
            category = TestCategory.from_dict(cat_data)
            self.categories[name] = category
        
        self._update_parent_child_relationships()
    
    def get_category_statistics(self) -> Dict:
        """Get comprehensive statistics about the category system"""
        stats = {
            "total_categories": len(self.categories),
            "by_priority": {},
            "by_type": {},
            "parallel_safe": 0,
            "requires_real_services": 0,
            "requires_real_llm": 0,
            "memory_intensive": 0,
            "cpu_intensive": 0,
            "database_dependent": 0,
            "average_estimated_duration": timedelta(0),
            "categories_with_history": 0,
            "average_success_rate": 0.0
        }
        
        # Count by priority
        for priority in CategoryPriority:
            stats["by_priority"][priority.name] = len(self.get_categories_by_priority(priority))
        
        # Count by type
        for category_type in TestOrganizationType:
            stats["by_type"][category_type.value] = len(self.get_categories_by_type(category_type))
        
        # Calculate other statistics
        total_duration = timedelta(0)
        total_success_rate = 0.0
        categories_with_success_rate = 0
        
        for category in self.categories.values():
            if category.parallel_safe:
                stats["parallel_safe"] += 1
            if category.requires_real_services:
                stats["requires_real_services"] += 1
            if category.requires_real_llm:
                stats["requires_real_llm"] += 1
            if category.memory_intensive:
                stats["memory_intensive"] += 1
            if category.cpu_intensive:
                stats["cpu_intensive"] += 1
            if category.database_dependent:
                stats["database_dependent"] += 1
            
            total_duration += category.estimated_duration
            
            if category.success_rate is not None:
                total_success_rate += category.success_rate
                categories_with_success_rate += 1
                stats["categories_with_history"] += 1
        
        if len(self.categories) > 0:
            stats["average_estimated_duration"] = total_duration / len(self.categories)
        
        if categories_with_success_rate > 0:
            stats["average_success_rate"] = total_success_rate / categories_with_success_rate
        
        return stats