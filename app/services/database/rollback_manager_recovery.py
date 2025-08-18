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
        self.dependency_rules = self._build_dependency_rules()
    
    def _build_dependency_rules(self) -> dict:
        """Build dependency rule mapping."""
        return {
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
            dependencies = self._collect_operation_dependencies(operation, operations)
            graph[operation.operation_id] = dependencies
        return graph
    
    def _collect_operation_dependencies(self, operation: RollbackOperation,
                                       operations: List[RollbackOperation]) -> Set[str]:
        """Collect all dependencies for an operation."""
        dependencies = set(operation.dependencies)
        implicit_deps = self._analyze_implicit_dependencies(operation, operations)
        dependencies.update(implicit_deps)
        return dependencies
    
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
            ready_ops = self._get_next_batch(remaining_ops, dependency_graph, operations_map)
            execution_batches.append(ready_ops)
            self._remove_completed_operations(ready_ops, remaining_ops)
        return execution_batches
    
    def _get_next_batch(self, remaining_ops: Set[str], dependency_graph: Dict[str, Set[str]],
                       operations_map: Dict[str, RollbackOperation]) -> List[RollbackOperation]:
        """Get next batch of ready operations."""
        ready_ops = self._find_ready_operations(remaining_ops, dependency_graph, operations_map)
        if not ready_ops:
            ready_ops = self._break_circular_dependency(remaining_ops, operations_map)
        return ready_ops
    
    def _find_ready_operations(
        self,
        remaining_ops: Set[str],
        dependency_graph: Dict[str, Set[str]],
        operations_map: Dict[str, RollbackOperation]
    ) -> List[RollbackOperation]:
        """Find operations with no unresolved dependencies."""
        ready_ops = []
        for op_id in remaining_ops:
            if self._is_operation_ready(op_id, remaining_ops, dependency_graph):
                ready_ops.append(operations_map[op_id])
        return ready_ops
    
    def _is_operation_ready(self, op_id: str, remaining_ops: Set[str],
                           dependency_graph: Dict[str, Set[str]]) -> bool:
        """Check if operation has no unresolved dependencies."""
        dependencies = dependency_graph.get(op_id, set())
        return not dependencies.intersection(remaining_ops)
    
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
            if self._should_skip_operation(operation, other_op):
                continue
            dependencies.update(self._check_operation_dependencies(operation, other_op))
        return dependencies
    
    def _should_skip_operation(self, op1: RollbackOperation, op2: RollbackOperation) -> bool:
        """Check if operation should be skipped in dependency analysis."""
        return op1.operation_id == op2.operation_id
    
    def _check_operation_dependencies(self, op1: RollbackOperation,
                                    op2: RollbackOperation) -> Set[str]:
        """Check dependencies between two operations."""
        dependencies = set()
        if self._has_table_dependency(op1, op2):
            dependencies.add(op2.operation_id)
        if self._has_temporal_dependency(op1, op2):
            dependencies.add(op2.operation_id)
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
        if self._is_insert_after_delete(op1, op2):
            return True
        return self._is_update_after_delete(op1, op2)
    
    def _is_insert_after_delete(self, op1: RollbackOperation, op2: RollbackOperation) -> bool:
        """Check if INSERT should wait for DELETE."""
        return op1.operation_type == "INSERT" and op2.operation_type == "DELETE"
    
    def _is_update_after_delete(self, op1: RollbackOperation, op2: RollbackOperation) -> bool:
        """Check if UPDATE should wait for DELETE."""
        return op1.operation_type == "UPDATE" and op2.operation_type == "DELETE"
    
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
        dependencies = []
        for operation in operations:
            fk_deps = self._analyze_fk_dependencies(operation, operations)
            dependencies.extend(fk_deps)
        return dependencies
    
    def _analyze_fk_dependencies(self, operation: RollbackOperation,
                                operations: List[RollbackOperation]) -> List[str]:
        """Analyze foreign key dependencies for operation."""
        return self._check_foreign_key_relationships(
            operation.table_name,
            operation.rollback_data,
            operations
        )
    
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
        dependencies = []
        sorted_ops = sorted(operations, key=lambda op: op.created_at)
        
        for i, operation in enumerate(sorted_ops):
            temporal_deps = self._get_temporal_dependencies(operation, sorted_ops[:i])
            dependencies.extend(temporal_deps)
        return dependencies
    
    def _get_temporal_dependencies(self, operation: RollbackOperation,
                                  earlier_ops: List[RollbackOperation]) -> List[str]:
        """Get temporal dependencies for operation."""
        return [
            earlier_op.operation_id
            for earlier_op in earlier_ops
            if self._should_respect_temporal_order(operation, earlier_op)
        ]
    
    def _should_respect_temporal_order(
        self,
        later_operation: RollbackOperation,
        earlier_operation: RollbackOperation
    ) -> bool:
        """Determine if temporal ordering should be respected between operations."""
        if self._is_same_table_operation(later_operation, earlier_operation):
            return True
        return self._check_cross_table_temporal_dependency(later_operation, earlier_operation)
    
    def _is_same_table_operation(self, op1: RollbackOperation, op2: RollbackOperation) -> bool:
        """Check if operations are on the same table."""
        return op1.table_name == op2.table_name
    
    def _check_cross_table_temporal_dependency(
        self,
        later_operation: RollbackOperation,
        earlier_operation: RollbackOperation
    ) -> bool:
        """Check if cross-table operations have temporal dependencies."""
        # Implementation would check if operations on different tables
        # still need to respect temporal order due to business constraints
        return False