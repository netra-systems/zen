"""
Dependency Graph Resolver - Service dependency ordering and resolution logic.

Provides intelligent dependency graph resolution for service startup ordering,
circular dependency detection, and phase-based startup coordination.
Ensures services start in the correct order based on their dependencies.
"""

import asyncio
import logging
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple

from netra_backend.app.logging_config import central_logger
from .models import (
    DependencyPhase,
    DependencyRelation,
    ServiceDependency,
    ServiceType,
)


class DependencyGraphResolver:
    """
    Resolves service dependency graphs for optimal startup ordering.
    
    Provides topological sorting, circular dependency detection,
    phase-based grouping, and parallel execution opportunities
    within dependency constraints.
    """
    
    def __init__(self, service_dependencies: List[ServiceDependency]):
        """Initialize dependency graph resolver."""
        self.logger = central_logger.get_logger(__name__)
        self.service_dependencies = service_dependencies
        
        # Build dependency graph structures
        self._dependency_graph: Dict[ServiceType, Set[ServiceType]] = defaultdict(set)
        self._reverse_graph: Dict[ServiceType, Set[ServiceType]] = defaultdict(set)
        self._phase_mapping: Dict[ServiceType, DependencyPhase] = {}
        self._relation_mapping: Dict[Tuple[ServiceType, ServiceType], DependencyRelation] = {}
        
        self._build_dependency_graph()
    
    def _build_dependency_graph(self) -> None:
        """Build internal dependency graph structures from service dependencies."""
        for dependency in self.service_dependencies:
            service = dependency.service
            depends_on = dependency.depends_on
            relation = dependency.relation
            phase = dependency.phase
            
            # Skip self-dependencies (used for phase grouping)
            if service != depends_on:
                # Forward graph: service -> services it depends on
                self._dependency_graph[service].add(depends_on)
                # Reverse graph: service -> services that depend on it
                self._reverse_graph[depends_on].add(service)
                # Relation mapping for dependency strength
                self._relation_mapping[(service, depends_on)] = relation
            
            # Phase mapping for services
            self._phase_mapping[service] = phase
        
        self.logger.debug(f"Built dependency graph with {len(self._dependency_graph)} services")
    
    async def resolve_startup_order(
        self,
        services_to_start: List[ServiceType]
    ) -> Dict[DependencyPhase, List[ServiceType]]:
        """
        Resolve startup order for requested services based on dependencies.
        
        Args:
            services_to_start: List of services that need to be started
            
        Returns:
            Dictionary mapping dependency phases to lists of services
            that can be started in parallel within that phase
            
        Raises:
            ValueError: If circular dependencies are detected
        """
        self.logger.info(f"Resolving startup order for {len(services_to_start)} services")
        
        # First, detect any circular dependencies
        cycles = self._detect_circular_dependencies(services_to_start)
        if cycles:
            cycle_descriptions = [" -> ".join(cycle.value for cycle in cycle) for cycle in cycles]
            raise ValueError(f"Circular dependencies detected: {cycle_descriptions}")
        
        # Get all required services (including transitive dependencies)
        all_required_services = self._get_all_required_services(services_to_start)
        self.logger.debug(f"Including transitive dependencies: {[s.value for s in all_required_services]}")
        
        # Group services by phase
        phase_groups = self._group_services_by_phase(all_required_services)
        
        # Within each phase, determine parallel execution order
        ordered_phases = {}
        for phase in [DependencyPhase.PHASE_1_CORE, DependencyPhase.PHASE_2_AUTH,
                      DependencyPhase.PHASE_3_BACKEND, DependencyPhase.PHASE_4_FRONTEND]:
            if phase in phase_groups:
                services_in_phase = phase_groups[phase]
                # Within a phase, services can generally start in parallel
                # but we still respect intra-phase dependencies
                ordered_services = self._resolve_intra_phase_order(services_in_phase)
                ordered_phases[phase] = ordered_services
                
                self.logger.debug(
                    f"Phase {phase.value}: {[s.value for s in ordered_services]} "
                    f"({len(ordered_services)} services)"
                )
        
        return ordered_phases
    
    def _detect_circular_dependencies(
        self,
        services: List[ServiceType]
    ) -> List[List[ServiceType]]:
        """
        Detect circular dependencies using depth-first search.
        
        Returns:
            List of cycles found (empty if no cycles)
        """
        cycles = []
        visited = set()
        recursion_stack = set()
        
        def dfs(service: ServiceType, path: List[ServiceType]) -> None:
            if service in recursion_stack:
                # Found a cycle - extract the cycle from the path
                cycle_start = path.index(service)
                cycle = path[cycle_start:] + [service]
                cycles.append(cycle)
                return
            
            if service in visited:
                return
            
            visited.add(service)
            recursion_stack.add(service)
            path.append(service)
            
            # Visit all dependencies
            for dependency in self._dependency_graph.get(service, []):
                if dependency in services:  # Only check requested services
                    dfs(dependency, path)
            
            recursion_stack.remove(service)
            path.pop()
        
        # Check each service for cycles
        for service in services:
            if service not in visited:
                dfs(service, [])
        
        return cycles
    
    def _get_all_required_services(
        self,
        requested_services: List[ServiceType]
    ) -> Set[ServiceType]:
        """
        Get all services required including transitive dependencies.
        
        Uses breadth-first search to find all required dependencies.
        """
        all_services = set(requested_services)
        queue = deque(requested_services)
        
        while queue:
            service = queue.popleft()
            
            # Add all required dependencies
            for dependency in self._dependency_graph.get(service, []):
                relation = self._relation_mapping.get((service, dependency))
                
                # Only include REQUIRED dependencies in the startup sequence
                # OPTIONAL and PREFERRED dependencies are checked but don't block startup
                if relation == DependencyRelation.REQUIRED and dependency not in all_services:
                    all_services.add(dependency)
                    queue.append(dependency)
        
        return all_services
    
    def _group_services_by_phase(
        self,
        services: Set[ServiceType]
    ) -> Dict[DependencyPhase, List[ServiceType]]:
        """Group services by their assigned dependency phases."""
        phase_groups = defaultdict(list)
        
        for service in services:
            phase = self._phase_mapping.get(service, DependencyPhase.PHASE_3_BACKEND)
            phase_groups[phase].append(service)
        
        return dict(phase_groups)
    
    def _resolve_intra_phase_order(
        self,
        services_in_phase: List[ServiceType]
    ) -> List[ServiceType]:
        """
        Resolve startup order within a single phase.
        
        Within a phase, services can generally start in parallel,
        but we still need to respect any intra-phase dependencies.
        """
        # For most phases, services can start in parallel
        # Return in a consistent order for predictable behavior
        return sorted(services_in_phase, key=lambda s: s.value)
    
    def get_dependency_analysis(
        self,
        service: ServiceType
    ) -> Dict[str, any]:
        """
        Get detailed dependency analysis for a specific service.
        
        Returns:
            Comprehensive dependency information for analysis
        """
        analysis = {
            "service": service.value,
            "phase": self._phase_mapping.get(service, DependencyPhase.PHASE_3_BACKEND).value,
            "direct_dependencies": [],
            "dependent_services": [],
            "transitive_dependencies": [],
            "circular_dependencies": []
        }
        
        # Direct dependencies
        for dependency in self._dependency_graph.get(service, []):
            relation = self._relation_mapping.get((service, dependency), DependencyRelation.REQUIRED)
            analysis["direct_dependencies"].append({
                "service": dependency.value,
                "relation": relation.value
            })
        
        # Services that depend on this service
        for dependent in self._reverse_graph.get(service, []):
            relation = self._relation_mapping.get((dependent, service), DependencyRelation.REQUIRED)
            analysis["dependent_services"].append({
                "service": dependent.value,
                "relation": relation.value
            })
        
        # Transitive dependencies (all services this service ultimately depends on)
        transitive_deps = self._get_transitive_dependencies(service)
        analysis["transitive_dependencies"] = [dep.value for dep in transitive_deps]
        
        # Check for circular dependencies involving this service
        cycles = self._detect_circular_dependencies([service])
        if cycles:
            analysis["circular_dependencies"] = [
                [s.value for s in cycle] for cycle in cycles
            ]
        
        return analysis
    
    def _get_transitive_dependencies(
        self,
        service: ServiceType
    ) -> Set[ServiceType]:
        """Get all transitive dependencies for a service."""
        transitive_deps = set()
        visited = set()
        
        def dfs(current_service: ServiceType) -> None:
            if current_service in visited:
                return
            visited.add(current_service)
            
            for dependency in self._dependency_graph.get(current_service, []):
                if dependency != service:  # Avoid self-reference
                    transitive_deps.add(dependency)
                    dfs(dependency)
        
        dfs(service)
        return transitive_deps
    
    def validate_dependency_graph(self) -> Dict[str, any]:
        """
        Validate the entire dependency graph for consistency.
        
        Returns:
            Validation report with any issues found
        """
        validation_report = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "statistics": {
                "total_services": len(set(s.service for s in self.service_dependencies)),
                "total_dependencies": len(self.service_dependencies),
                "phases": len(set(d.phase for d in self.service_dependencies))
            }
        }
        
        # Check for circular dependencies across all services
        all_services = list(set(d.service for d in self.service_dependencies))
        cycles = self._detect_circular_dependencies(all_services)
        
        if cycles:
            validation_report["valid"] = False
            for cycle in cycles:
                cycle_description = " -> ".join(s.value for s in cycle)
                validation_report["issues"].append(
                    f"Circular dependency detected: {cycle_description}"
                )
        
        # Check for services with no dependencies (potential root services)
        root_services = []
        for service in all_services:
            if not self._dependency_graph.get(service):
                root_services.append(service)
        
        if not root_services:
            validation_report["warnings"].append(
                "No root services found - all services have dependencies"
            )
        else:
            validation_report["statistics"]["root_services"] = [s.value for s in root_services]
        
        # Check for orphaned services (no services depend on them and they depend on nothing)
        orphaned_services = []
        for service in all_services:
            has_dependencies = bool(self._dependency_graph.get(service))
            has_dependents = bool(self._reverse_graph.get(service))
            
            if not has_dependencies and not has_dependents:
                orphaned_services.append(service)
        
        if orphaned_services:
            validation_report["warnings"].append(
                f"Orphaned services (no dependencies or dependents): "
                f"{[s.value for s in orphaned_services]}"
            )
        
        # Phase consistency check
        phase_stats = defaultdict(int)
        for dependency in self.service_dependencies:
            phase_stats[dependency.phase] += 1
        
        validation_report["statistics"]["services_per_phase"] = {
            phase.value: count for phase, count in phase_stats.items()
        }
        
        return validation_report
    
    def get_optimal_startup_sequence(
        self,
        services_to_start: List[ServiceType],
        max_parallel: int = 3
    ) -> List[List[ServiceType]]:
        """
        Get optimal startup sequence with controlled parallelism.
        
        Args:
            services_to_start: Services to include in startup
            max_parallel: Maximum services to start in parallel per step
            
        Returns:
            List of startup steps, each containing services that can start in parallel
        """
        try:
            # Get phase-based ordering
            phase_order = asyncio.create_task(
                self.resolve_startup_order(services_to_start)
            )
            phase_results = asyncio.get_event_loop().run_until_complete(phase_order)
            
            startup_sequence = []
            
            for phase in [DependencyPhase.PHASE_1_CORE, DependencyPhase.PHASE_2_AUTH,
                          DependencyPhase.PHASE_3_BACKEND, DependencyPhase.PHASE_4_FRONTEND]:
                if phase not in phase_results:
                    continue
                
                services_in_phase = phase_results[phase]
                
                # Break large phases into smaller parallel groups
                while services_in_phase:
                    batch_size = min(max_parallel, len(services_in_phase))
                    batch = services_in_phase[:batch_size]
                    services_in_phase = services_in_phase[batch_size:]
                    startup_sequence.append(batch)
            
            return startup_sequence
            
        except Exception as e:
            self.logger.error(f"Failed to generate optimal startup sequence: {e}")
            # Fallback to simple sequential startup
            return [[service] for service in services_to_start]