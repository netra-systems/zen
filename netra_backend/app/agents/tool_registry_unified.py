"""Unified Tool Registry - Centralized tool registration and management.

This module provides the unified tool registry that consolidates all tool
registration and management functionality with clean separation from
execution concerns.

Key Features:
- Thread-safe tool registration and retrieval
- Support for multiple tool types (BaseTool, ProductionTool, etc.)
- Tool validation and metadata management
- Registry snapshots for isolation
- Comprehensive error handling and logging
- Tool discovery and introspection
"""

import threading
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime, timezone
from collections import defaultdict

from langchain_core.tools import BaseTool
from netra_backend.app.agents.production_tool import ProductionTool
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import ToolRegistryInterface

logger = central_logger.get_logger(__name__)


class ToolMetadata:
    """Metadata container for registered tools."""
    
    def __init__(
        self,
        tool: Any,
        registered_at: datetime,
        registry_id: str,
        description: Optional[str] = None,
        tags: Optional[Set[str]] = None
    ):
        self.tool = tool
        self.registered_at = registered_at
        self.registry_id = registry_id
        self.description = description or getattr(tool, 'description', '')
        self.tags = tags or set()
        self.access_count = 0
        self.last_accessed = None
        
    def mark_accessed(self) -> None:
        """Mark tool as accessed and update metrics."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'tool_name': getattr(self.tool, 'name', str(self.tool)),
            'tool_type': type(self.tool).__name__,
            'description': self.description,
            'tags': list(self.tags),
            'registered_at': self.registered_at.isoformat(),
            'registry_id': self.registry_id,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }


class UnifiedToolRegistry(ToolRegistryInterface):
    """Unified tool registry with thread-safe operations and comprehensive management.
    
    This registry provides centralized tool management with:
    - Thread-safe registration and retrieval
    - Tool metadata and usage tracking
    - Multiple tool type support
    - Validation and error handling
    - Registry snapshots for isolation
    - Tool discovery and introspection
    
    Key Design Principles:
    1. Thread-safe operations for concurrent access
    2. Tool metadata tracking for debugging and monitoring
    3. Support for all tool types (BaseTool, ProductionTool, functions, etc.)
    4. Clean separation from execution concerns
    5. Registry snapshots for request-scoped isolation
    """
    
    def __init__(self, registry_id: Optional[str] = None):
        """Initialize the unified tool registry.
        
        Args:
            registry_id: Optional identifier for this registry instance
        """
        self.registry_id = registry_id or f"registry_{int(datetime.now().timestamp() * 1000)}"
        self.created_at = datetime.now(timezone.utc)
        
        # Thread-safe storage
        self._lock = threading.RLock()
        self._tools: Dict[str, ToolMetadata] = {}
        self._tool_categories: Dict[str, Set[str]] = defaultdict(set)
        self._validation_handlers: List[Callable[[str, Any], bool]] = []
        
        # Registry metrics
        self._metrics = {
            'total_registrations': 0,
            'successful_registrations': 0,
            'failed_registrations': 0,
            'total_retrievals': 0,
            'unique_tools': 0,
            'last_registration_time': None
        }
        
        # Initialize with default tools
        self._register_default_tools()
        
        logger.info(f"✅ Created UnifiedToolRegistry {self.registry_id}")
    
    def _register_default_tools(self) -> None:
        """Register default synthetic and corpus tools."""
        try:
            # Register synthetic data generation tools
            synthetic_tools = [
                "generate_synthetic_data_batch",
                "validate_synthetic_data", 
                "store_synthetic_data"
            ]
            self._register_tool_batch(synthetic_tools, "synthetic")
            
            # Register corpus management tools
            corpus_tools = [
                "create_corpus", "search_corpus", "update_corpus", "delete_corpus",
                "analyze_corpus", "export_corpus", "import_corpus", "validate_corpus"
            ]
            self._register_tool_batch(corpus_tools, "corpus")
            
            logger.debug(f"Registered {len(synthetic_tools + corpus_tools)} default tools")
            
        except Exception as e:
            logger.error(f"Failed to register default tools: {e}")
    
    def _register_tool_batch(self, tool_names: List[str], category: str) -> None:
        """Register batch of tools if not already present."""
        with self._lock:
            for tool_name in tool_names:
                if tool_name not in self._tools:
                    try:
                        tool = ProductionTool(tool_name)
                        metadata = ToolMetadata(
                            tool=tool,
                            registered_at=datetime.now(timezone.utc),
                            registry_id=self.registry_id,
                            description=f"Default {category} tool: {tool_name}",
                            tags={category, "default"}
                        )
                        
                        self._tools[tool_name] = metadata
                        self._tool_categories[category].add(tool_name)
                        self._metrics['successful_registrations'] += 1
                        self._metrics['total_registrations'] += 1
                        
                    except Exception as e:
                        self._metrics['failed_registrations'] += 1
                        self._metrics['total_registrations'] += 1
                        logger.error(f"Failed to register default tool {tool_name}: {e}")
            
            self._metrics['unique_tools'] = len(self._tools)
            self._metrics['last_registration_time'] = datetime.now(timezone.utc)
    
    # ===================== CORE REGISTRY OPERATIONS =====================
    
    def register_tool(self, tool: BaseTool, tags: Optional[Set[str]] = None) -> bool:
        """Register a single tool with metadata tracking.
        
        Args:
            tool: Tool to register (must have 'name' attribute)
            tags: Optional set of tags for categorization
            
        Returns:
            bool: True if registration successful, False otherwise
        """
        if not hasattr(tool, 'name'):
            logger.error(f"Tool {tool} missing required 'name' attribute")
            self._metrics['failed_registrations'] += 1
            self._metrics['total_registrations'] += 1
            return False
        
        tool_name = tool.name
        
        # Run validation handlers
        for validator in self._validation_handlers:
            try:
                if not validator(tool_name, tool):
                    logger.warning(f"Tool {tool_name} failed validation")
                    self._metrics['failed_registrations'] += 1
                    self._metrics['total_registrations'] += 1
                    return False
            except Exception as e:
                logger.error(f"Validation error for tool {tool_name}: {e}")
                self._metrics['failed_registrations'] += 1
                self._metrics['total_registrations'] += 1
                return False
        
        with self._lock:
            try:
                # Create metadata
                metadata = ToolMetadata(
                    tool=tool,
                    registered_at=datetime.now(timezone.utc),
                    registry_id=self.registry_id,
                    description=getattr(tool, 'description', ''),
                    tags=tags or set()
                )
                
                # Register tool
                self._tools[tool_name] = metadata
                
                # Update categories
                if tags:
                    for tag in tags:
                        self._tool_categories[tag].add(tool_name)
                
                # Update metrics
                self._metrics['successful_registrations'] += 1
                self._metrics['total_registrations'] += 1
                self._metrics['unique_tools'] = len(self._tools)
                self._metrics['last_registration_time'] = datetime.now(timezone.utc)
                
                logger.debug(f"✅ Registered tool {tool_name} in registry {self.registry_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to register tool {tool_name}: {e}")
                self._metrics['failed_registrations'] += 1
                self._metrics['total_registrations'] += 1
                return False
    
    def register_tools(self, tools: List[BaseTool]) -> int:
        """Register list of tools and return count of successful registrations."""
        successful_count = 0
        for tool in tools:
            if self.register_tool(tool):
                successful_count += 1
        
        logger.info(f"Registered {successful_count}/{len(tools)} tools in registry {self.registry_id}")
        return successful_count
    
    def register_function_tool(
        self,
        tool_name: str,
        tool_func: Callable,
        description: str = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Register a function as a tool by wrapping it in BaseTool.
        
        Args:
            tool_name: Name for the tool
            tool_func: Function to wrap
            description: Optional description
            tags: Optional set of tags
            
        Returns:
            bool: True if registration successful, False otherwise
        """
        try:
            # Create BaseTool wrapper
            class FunctionTool(BaseTool):
                name: str = tool_name
                description: str = description or f"Function tool: {tool_name}"
                
                def _run(self, *args, **kwargs):
                    return tool_func(*args, **kwargs)
                
                async def _arun(self, *args, **kwargs):
                    import asyncio
                    if asyncio.iscoroutinefunction(tool_func):
                        return await tool_func(*args, **kwargs)
                    else:
                        return tool_func(*args, **kwargs)
            
            # Register the wrapped tool
            wrapped_tool = FunctionTool()
            return self.register_tool(wrapped_tool, tags)
            
        except Exception as e:
            logger.error(f"Failed to register function tool {tool_name}: {e}")
            return False
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists in the registry."""
        with self._lock:
            exists = tool_name in self._tools
            if exists:
                self._metrics['total_retrievals'] += 1
            return exists
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """Get a tool by name with usage tracking."""
        with self._lock:
            metadata = self._tools.get(tool_name)
            if metadata:
                metadata.mark_accessed()
                self._metrics['total_retrievals'] += 1
                return metadata.tool
            return None
    
    def get_tool_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """Get tool metadata by name."""
        with self._lock:
            return self._tools.get(tool_name)
    
    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from registry."""
        with self._lock:
            if tool_name in self._tools:
                # Remove from categories
                metadata = self._tools[tool_name]
                for tag in metadata.tags:
                    self._tool_categories[tag].discard(tool_name)
                
                # Remove tool
                del self._tools[tool_name]
                self._metrics['unique_tools'] = len(self._tools)
                
                logger.debug(f"Removed tool {tool_name} from registry {self.registry_id}")
                return True
            return False
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        with self._lock:
            return list(self._tools.keys())
    
    def list_tools_by_category(self, category: str) -> List[str]:
        """List tools by category/tag."""
        with self._lock:
            return list(self._tool_categories.get(category, set()))
    
    def list_categories(self) -> List[str]:
        """List all available categories."""
        with self._lock:
            return list(self._tool_categories.keys())
    
    def clear_tools(self) -> None:
        """Clear all tools from registry and re-register defaults."""
        with self._lock:
            self._tools.clear()
            self._tool_categories.clear()
            self._register_default_tools()
            self._metrics['unique_tools'] = len(self._tools)
            
        logger.info(f"Cleared and reset registry {self.registry_id}")
    
    def get_tool_count(self) -> int:
        """Get total number of registered tools."""
        with self._lock:
            return len(self._tools)
    
    # ===================== ADVANCED OPERATIONS =====================
    
    def create_snapshot(self) -> 'ToolRegistrySnapshot':
        """Create immutable snapshot of current registry state."""
        with self._lock:
            tools_copy = {}
            for name, metadata in self._tools.items():
                tools_copy[name] = metadata.tool
            
            return ToolRegistrySnapshot(
                tools=tools_copy,
                snapshot_time=datetime.now(timezone.utc),
                source_registry_id=self.registry_id
            )
    
    def add_validation_handler(self, validator: Callable[[str, Any], bool]) -> None:
        """Add validation handler for tool registration."""
        self._validation_handlers.append(validator)
        logger.debug(f"Added validation handler to registry {self.registry_id}")
    
    def remove_validation_handler(self, validator: Callable[[str, Any], bool]) -> bool:
        """Remove validation handler."""
        try:
            self._validation_handlers.remove(validator)
            logger.debug(f"Removed validation handler from registry {self.registry_id}")
            return True
        except ValueError:
            return False
    
    def search_tools(self, query: str) -> List[str]:
        """Search tools by name, description, or tags."""
        query_lower = query.lower()
        matches = []
        
        with self._lock:
            for tool_name, metadata in self._tools.items():
                # Check name match
                if query_lower in tool_name.lower():
                    matches.append(tool_name)
                    continue
                
                # Check description match
                if query_lower in metadata.description.lower():
                    matches.append(tool_name)
                    continue
                
                # Check tag match
                if any(query_lower in tag.lower() for tag in metadata.tags):
                    matches.append(tool_name)
                    continue
        
        return matches
    
    def get_registry_metrics(self) -> Dict[str, Any]:
        """Get comprehensive registry metrics."""
        with self._lock:
            uptime_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
            
            # Calculate category distribution
            category_distribution = {}
            for category, tools in self._tool_categories.items():
                category_distribution[category] = len(tools)
            
            # Calculate usage statistics
            total_accesses = sum(
                metadata.access_count for metadata in self._tools.values()
            )
            
            most_used_tools = sorted(
                self._tools.items(),
                key=lambda x: x[1].access_count,
                reverse=True
            )[:5]
            
            return {
                **self._metrics,
                'registry_id': self.registry_id,
                'uptime_seconds': uptime_seconds,
                'category_distribution': category_distribution,
                'total_accesses': total_accesses,
                'most_used_tools': [
                    {'name': name, 'access_count': metadata.access_count}
                    for name, metadata in most_used_tools
                ],
                'success_rate': (
                    self._metrics['successful_registrations'] / 
                    max(1, self._metrics['total_registrations'])
                ),
                'created_at': self.created_at.isoformat()
            }
    
    def get_tool_details(self) -> List[Dict[str, Any]]:
        """Get detailed information about all registered tools."""
        with self._lock:
            return [metadata.to_dict() for metadata in self._tools.values()]
    
    def validate_registry_health(self) -> Dict[str, Any]:
        """Validate registry health and integrity."""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'issues': [],
            'metrics': self.get_registry_metrics()
        }
        
        with self._lock:
            # Check for empty registry
            if len(self._tools) == 0:
                health_status['status'] = 'warning'
                health_status['issues'].append("Registry is empty")
            
            # Check for failed registrations
            if self._metrics['failed_registrations'] > 0:
                failure_rate = (
                    self._metrics['failed_registrations'] / 
                    max(1, self._metrics['total_registrations'])
                )
                if failure_rate > 0.1:  # More than 10% failures
                    health_status['status'] = 'degraded'
                    health_status['issues'].append(f"High registration failure rate: {failure_rate:.1%}")
            
            # Check for tools with no access
            unused_tools = [
                name for name, metadata in self._tools.items()
                if metadata.access_count == 0
            ]
            if len(unused_tools) > len(self._tools) * 0.8:  # More than 80% unused
                health_status['status'] = 'warning'
                health_status['issues'].append(f"High unused tool ratio: {len(unused_tools)}/{len(self._tools)}")
            
            # Check for tool validation errors
            validation_errors = []
            for tool_name, metadata in self._tools.items():
                try:
                    tool = metadata.tool
                    if not hasattr(tool, 'name') or tool.name != tool_name:
                        validation_errors.append(tool_name)
                except Exception as e:
                    validation_errors.append(f"{tool_name}: {e}")
            
            if validation_errors:
                health_status['status'] = 'degraded'
                health_status['issues'].append(f"Tool validation errors: {validation_errors}")
        
        return health_status


class ToolRegistrySnapshot:
    """Immutable snapshot of a tool registry state.
    
    This class provides an immutable view of a registry at a specific point in time,
    useful for request-scoped isolation and debugging.
    """
    
    def __init__(self, tools: Dict[str, Any], snapshot_time: datetime, source_registry_id: str):
        self._tools = tools.copy()  # Shallow copy for immutability
        self.snapshot_time = snapshot_time
        self.source_registry_id = source_registry_id
        self.snapshot_id = f"snapshot_{int(snapshot_time.timestamp() * 1000)}"
        
    @property
    def tools(self) -> Dict[str, Any]:
        """Get read-only view of tools."""
        return self._tools.copy()
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if tool exists in snapshot."""
        return tool_name in self._tools
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """Get tool from snapshot."""
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """List all tools in snapshot."""
        return list(self._tools.keys())
    
    def get_tool_count(self) -> int:
        """Get tool count in snapshot."""
        return len(self._tools)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            'snapshot_id': self.snapshot_id,
            'source_registry_id': self.source_registry_id,
            'snapshot_time': self.snapshot_time.isoformat(),
            'tool_count': len(self._tools),
            'tools': list(self._tools.keys())
        }


# ===================== GLOBAL REGISTRY INSTANCE =====================

_global_registry: Optional[UnifiedToolRegistry] = None
_registry_lock = threading.Lock()


def get_global_tool_registry() -> UnifiedToolRegistry:
    """Get the global tool registry instance (thread-safe).
    
    WARNING: Global registry may cause isolation issues in multi-tenant scenarios.
    Consider using request-scoped registries for better isolation.
    
    Returns:
        UnifiedToolRegistry: Global registry instance
    """
    global _global_registry
    
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = UnifiedToolRegistry(registry_id="global")
                logger.info("Created global UnifiedToolRegistry instance")
    
    return _global_registry


def create_request_scoped_registry(registry_id: Optional[str] = None) -> UnifiedToolRegistry:
    """Create a new request-scoped tool registry.
    
    RECOMMENDED: Use this for request-scoped isolation.
    
    Args:
        registry_id: Optional identifier for the registry
        
    Returns:
        UnifiedToolRegistry: New registry instance
    """
    return UnifiedToolRegistry(registry_id)


# ===================== BACKWARD COMPATIBILITY =====================

# Alias for backward compatibility
ToolRegistry = UnifiedToolRegistry

# Export all public interfaces
__all__ = [
    'UnifiedToolRegistry',
    'ToolRegistrySnapshot',
    'ToolMetadata',
    'get_global_tool_registry',
    'create_request_scoped_registry',
    # Backward compatibility
    'ToolRegistry'
]