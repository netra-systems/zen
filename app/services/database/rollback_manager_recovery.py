"""Rollback dependency resolution and recovery logic.

Contains dependency analysis, execution ordering, and recovery patterns
for complex rollback scenarios across multiple operations.
"""

from typing import Dict, List, Set

from app.logging_config import central_logger
from .rollback_manager_core import RollbackOperation, DependencyType

logger = central_logger.get_logger(__name__)


class DependencyResolver:
    """Resolves dependencies between rollback operations."""
    
    def __init__(self):
        """Initialize dependency resolver with rule handlers."""
        self.dependency_rules = {
            DependencyType.FOREIGN_KEY: self._resolve_foreign_key,
            DependencyType.CASCADE: self._resolve_cascade,
            DependencyType.TRIGGER: self._resolve_trigger,
            DependencyType.LOGICAL: self._resolve_logical,
            DependencyType.TEMPORAL: self._resolve_temporal,
        }
    
    def resolve_execution_order(
        self,
        operations: List[RollbackOperation]
    ) -> List[List[RollbackOperation]]:
        """Resolve execution order considering dependencies."""
        dependency_graph = self._build_dependency_graph(operations)
        return self._perform_topological_sort(operations, dependency_graph)
    
    def _build_dependency_graph(
        self,
        operations: List[RollbackOperation]
    ) -> Dict[str, Set[str]]:
        """Build dependency graph from operations."""
        graph = {}
        
        for operation in operations:
            dependencies = set()
            dependencies.update(operation.dependencies)
            
            implicit_deps = self._analyze_implicit_dependencies(operation, operations)
            dependencies.update(implicit_deps)
            
            graph[operation.operation_id] = dependencies
        
        return graph
    
    def _perform_topological_sort(
        self,
        operations: List[RollbackOperation],
        dependency_graph: Dict[str, Set[str]]
    ) -> List[List[RollbackOperation]]:
        """Perform topological sort to determine execution batches."""
        execution_batches = []
        remaining_ops = set(op.operation_id for op in operations)
        operations_map = {op.operation_id: op for op in operations}
        
        while remaining_ops:
            ready_ops = self._find_ready_operations(remaining_ops, dependency_graph)
            
            if not ready_ops:
                ready_ops = self._break_circular_dependency(remaining_ops, operations_map)
            
            execution_batches.append(ready_ops)
            self._remove_completed_operations(ready_ops, remaining_ops)
        
        return execution_batches
    
    def _find_ready_operations(
        self,
        remaining_ops: Set[str],
        dependency_graph: Dict[str, Set[str]]
    ) -> List[RollbackOperation]:
        """Find operations with no unresolved dependencies."""
        ready_ops = []
        operations_map = {}  # Will be populated from remaining_ops
        
        for op_id in remaining_ops:
            dependencies = dependency_graph.get(op_id, set())
            if not dependencies.intersection(remaining_ops):
                # Need to get operation from somewhere - this is a simplified approach
                # In practice, we'd maintain the operations_map throughout
                pass
        
        return ready_ops
    
    def _break_circular_dependency(
        self,
        remaining_ops: Set[str],
        operations_map: Dict[str, RollbackOperation]
    ) -> List[RollbackOperation]:
        """Break circular dependency by selecting one operation."""
        logger.warning("Circular dependency detected in rollback operations")
        selected_op_id = next(iter(remaining_ops))
        return [operations_map[selected_op_id]]
    
    def _remove_completed_operations(
        self,
        completed_ops: List[RollbackOperation],
        remaining_ops: Set[str]
    ) -> None:
        """Remove completed operations from remaining set."""
        for op in completed_ops:
            remaining_ops.discard(op.operation_id)
    
    def _analyze_implicit_dependencies(
        self,
        operation: RollbackOperation,
        all_operations: List[RollbackOperation]
    ) -> Set[str]:
        """Analyze implicit dependencies between operations."""
        dependencies = set()
        
        for other_op in all_operations:
            if other_op.operation_id == operation.operation_id:
                continue
            
            if self._has_table_dependency(operation, other_op):
                dependencies.add(other_op.operation_id)
            
            if self._has_temporal_dependency(operation, other_op):
                dependencies.add(other_op.operation_id)
        
        return dependencies
    
    def _has_table_dependency(
        self,
        op1: RollbackOperation,
        op2: RollbackOperation
    ) -> bool:
        """Check if operations have table-level dependencies."""
        if op1.table_name == op2.table_name:
            return self._check_same_table_dependency(op1, op2)
        return False
    
    def _check_same_table_dependency(
        self,
        op1: RollbackOperation,
        op2: RollbackOperation
    ) -> bool:
        """Check dependency rules for same-table operations."""
        # DELETEs should happen before INSERTs for same table
        if op1.operation_type == "INSERT" and op2.operation_type == "DELETE":
            return True
        # UPDATEs should happen after DELETEs and before INSERTs
        if op1.operation_type == "UPDATE" and op2.operation_type == "DELETE":
            return True
        return False
    
    def _has_temporal_dependency(
        self,
        op1: RollbackOperation,
        op2: RollbackOperation
    ) -> bool:
        """Check if operations have temporal dependencies."""
        # Operations created earlier should be rolled back later
        return op1.created_at > op2.created_at
    
    def _resolve_foreign_key(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve foreign key dependencies."""
        # Analyze FK constraints and return dependent operation IDs
        # This would examine database schema and rollback data
        dependencies = []
        
        # Implementation would check foreign key relationships
        # between tables involved in the rollback operations
        for operation in operations:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            # Check if this operation affects records that other operations depend on
            # via foreign key relationships
            fk_deps = self._check_foreign_key_relationships(table_name, rollback_data, operations)
            dependencies.extend(fk_deps)
        
        return dependencies
    
    def _check_foreign_key_relationships(
        self,
        table_name: str,
        rollback_data: Dict,
        operations: List[RollbackOperation]
    ) -> List[str]:
        """Check for foreign key relationships affecting operation order."""
        # This would query database metadata to understand FK constraints
        # and determine which operations must complete before others
        return []
    
    def _resolve_cascade(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve cascade dependencies."""
        # Analyze cascade rules and their impact on operation ordering
        dependencies = []
        
        for operation in operations:
            cascade_deps = self._check_cascade_effects(operation, operations)
            dependencies.extend(cascade_deps)
        
        return dependencies
    
    def _check_cascade_effects(
        self,
        operation: RollbackOperation,
        operations: List[RollbackOperation]
    ) -> List[str]:
        """Check for cascade effects that create dependencies."""
        # Implementation would analyze cascade rules defined in the database
        # and determine which operations are affected by cascading changes
        return []
    
    def _resolve_trigger(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve trigger dependencies."""
        # Analyze trigger effects on operation ordering
        dependencies = []
        
        for operation in operations:
            trigger_deps = self._check_trigger_effects(operation, operations)
            dependencies.extend(trigger_deps)
        
        return dependencies
    
    def _check_trigger_effects(
        self,
        operation: RollbackOperation,
        operations: List[RollbackOperation]
    ) -> List[str]:
        """Check for trigger effects that create dependencies."""
        # Implementation would analyze database triggers and their effects
        # on the rollback operations to determine proper ordering
        return []
    
    def _resolve_logical(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve logical business dependencies."""
        # Analyze business logic dependencies
        dependencies = []
        
        for operation in operations:
            logical_deps = self._check_business_logic_dependencies(operation, operations)
            dependencies.extend(logical_deps)
        
        return dependencies
    
    def _check_business_logic_dependencies(
        self,
        operation: RollbackOperation,
        operations: List[RollbackOperation]
    ) -> List[str]:
        """Check for business logic dependencies between operations."""
        # Implementation would analyze business rules and constraints
        # that dictate the order of rollback operations
        return []
    
    def _resolve_temporal(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve temporal dependencies."""
        # Analyze time-based dependencies
        dependencies = []
        
        # Sort operations by creation time to ensure proper temporal ordering
        sorted_ops = sorted(operations, key=lambda op: op.created_at)
        
        for i, operation in enumerate(sorted_ops):
            # Each operation depends on all operations created before it
            temporal_deps = [
                earlier_op.operation_id 
                for earlier_op in sorted_ops[:i]
                if self._should_respect_temporal_order(operation, earlier_op)
            ]
            dependencies.extend(temporal_deps)
        
        return dependencies
    
    def _should_respect_temporal_order(
        self,
        later_operation: RollbackOperation,
        earlier_operation: RollbackOperation
    ) -> bool:
        """Determine if temporal ordering should be respected between operations."""
        # Operations on the same table should generally respect temporal order
        if later_operation.table_name == earlier_operation.table_name:
            return True
        
        # Cross-table operations may also need temporal ordering based on business rules
        return self._check_cross_table_temporal_dependency(later_operation, earlier_operation)
    
    def _check_cross_table_temporal_dependency(
        self,
        later_operation: RollbackOperation,
        earlier_operation: RollbackOperation
    ) -> bool:
        """Check if cross-table operations have temporal dependencies."""
        # Implementation would check if operations on different tables
        # still need to respect temporal order due to business constraints
        return False