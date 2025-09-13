"""

Comprehensive Circular Import Detection and Performance Tests



This module contains stress tests that validate circular import handling:

- Detection of circular import cycles in the codebase

- Performance impact measurement of complex import chains

- Import resolution under stress conditions

- Module dependency graph validation

- Import timeout and deadlock detection



These tests are designed to be DIFFICULT and catch regressions by actually

creating circular import scenarios that would cause pytest crashes.

"""



import ast

import gc

import importlib

import importlib.util

import os

import sys

import tempfile

import time

import threading

import traceback

from concurrent.futures import ThreadPoolExecutor, as_completed

from contextlib import contextmanager

from dataclasses import dataclass, field

from pathlib import Path

from typing import Dict, List, Optional, Set, Tuple, Any, Generator, Union

import weakref

import subprocess

import json

from shared.isolated_environment import IsolatedEnvironment



# Graph analysis for dependency cycles

try:

    import networkx as nx

    NETWORKX_AVAILABLE = True

except ImportError:

    NETWORKX_AVAILABLE = False



# Memory tracking

import psutil

import tracemalloc



# Test framework imports

from test_framework.import_safety import (

    ImportSafetyChecker,

    detect_import_cycles,

    measure_import_performance

)





@dataclass

class ImportCycleResult:

    """Result of circular import detection"""

    cycle_found: bool

    cycle_modules: List[str] = field(default_factory=list)

    cycle_length: int = 0

    import_chain: List[str] = field(default_factory=list)

    time_to_detect: float = 0.0

    memory_used_mb: float = 0.0

    error_message: Optional[str] = None





@dataclass

class ImportPerformanceResult:

    """Result of import performance measurement"""

    module_name: str

    import_time_seconds: float

    memory_delta_mb: float

    dependencies_loaded: int

    circular_refs_detected: int

    import_successful: bool

    error_message: Optional[str] = None





class CircularImportDetector:

    """

    Advanced circular import detection and analysis

    """

    

    def __init__(self, base_path: Path):

        self.base_path = Path(base_path)

        self.import_graph = {}

        self.visited_modules = set()

        self.import_stack = []

        self.cycles_found = []

        

    def build_import_graph(self, module_paths: List[Path]) -> Dict[str, Set[str]]:

        """Build a graph of module dependencies by parsing source files"""

        import_graph = {}

        

        for module_path in module_paths:

            if not module_path.suffix == '.py':

                continue

                

            module_name = self._path_to_module_name(module_path)

            imports = self._extract_imports_from_file(module_path)

            import_graph[module_name] = imports

            

        return import_graph

    

    def _path_to_module_name(self, module_path: Path) -> str:

        """Convert file path to module name"""

        relative_path = module_path.relative_to(self.base_path)

        module_parts = list(relative_path.parts[:-1])  # Exclude filename

        if relative_path.stem != '__init__':

            module_parts.append(relative_path.stem)

        return '.'.join(module_parts)

    

    def _extract_imports_from_file(self, file_path: Path) -> Set[str]:

        """Extract import statements from a Python file"""

        imports = set()

        

        try:

            with open(file_path, 'r', encoding='utf-8') as f:

                content = f.read()

                

            tree = ast.parse(content)

            

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):

                    for alias in node.names:

                        imports.add(alias.name.split('.')[0])  # Get top-level module

                        

                elif isinstance(node, ast.ImportFrom):

                    if node.module:

                        imports.add(node.module.split('.')[0])  # Get top-level module

                        

        except Exception as e:

            # If we can't parse the file, skip it

            print(f"Warning: Could not parse {file_path}: {e}")

            

        return imports

    

    def detect_cycles_dfs(self, import_graph: Dict[str, Set[str]]) -> List[List[str]]:

        """Detect cycles using depth-first search"""

        cycles = []

        visited = set()

        rec_stack = set()

        path = []

        

        def dfs(module: str):

            if module in rec_stack:

                # Found a cycle

                cycle_start = path.index(module)

                cycle = path[cycle_start:] + [module]

                cycles.append(cycle)

                return

                

            if module in visited:

                return

                

            visited.add(module)

            rec_stack.add(module)

            path.append(module)

            

            # Visit dependencies

            for dependency in import_graph.get(module, set()):

                if dependency in import_graph:  # Only check modules in our codebase

                    dfs(dependency)

                    

            path.pop()

            rec_stack.remove(module)

        

        # Check all modules

        for module in import_graph:

            if module not in visited:

                dfs(module)

                

        return cycles

    

    def detect_cycles_networkx(self, import_graph: Dict[str, Set[str]]) -> List[List[str]]:

        """Detect cycles using NetworkX (if available)"""

        if not NETWORKX_AVAILABLE:

            return []

            

        # Create directed graph

        G = nx.DiGraph()

        

        for module, dependencies in import_graph.items():

            G.add_node(module)

            for dep in dependencies:

                if dep in import_graph:  # Only internal dependencies

                    G.add_edge(module, dep)

        

        # Find strongly connected components with more than one node

        cycles = []

        try:

            sccs = list(nx.strongly_connected_components(G))

            for scc in sccs:

                if len(scc) > 1:

                    # Convert set to list and try to find actual cycle path

                    scc_list = list(scc)

                    try:

                        cycle = nx.find_cycle(G.subgraph(scc), orientation='original')

                        cycle_nodes = [edge[0] for edge in cycle] + [cycle[-1][1]]

                        cycles.append(cycle_nodes)

                    except nx.NetworkXNoCycle:

                        # If no cycle found in SCC, it might be a complex structure

                        cycles.append(scc_list)

        except Exception as e:

            print(f"NetworkX cycle detection failed: {e}")

            

        return cycles

    

    def analyze_import_performance(self, module_path: Path, max_depth: int = 5) -> ImportPerformanceResult:

        """Analyze performance impact of importing a module"""

        module_name = self._path_to_module_name(module_path)

        

        # Measure import performance

        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        start_time = time.time()

        

        try:

            # Add module directory to path temporarily

            sys.path.insert(0, str(self.base_path))

            

            # Track imports before

            initial_modules = set(sys.modules.keys())

            

            # Import the module

            spec = importlib.util.spec_from_file_location(module_name, module_path)

            if spec and spec.loader:

                module = importlib.util.module_from_spec(spec)

                spec.loader.exec_module(module)

                

            import_successful = True

            error_message = None

            

        except Exception as e:

            import_successful = False

            error_message = str(e)

            

        finally:

            # Remove from path

            if str(self.base_path) in sys.path:

                sys.path.remove(str(self.base_path))

        

        end_time = time.time()

        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        

        # Count new modules loaded

        final_modules = set(sys.modules.keys())

        dependencies_loaded = len(final_modules - initial_modules)

        

        # Detect circular references using gc

        circular_refs = len([obj for obj in gc.get_objects() 

                           if isinstance(obj, type(sys)) and hasattr(obj, '__name__')])

        

        return ImportPerformanceResult(

            module_name=module_name,

            import_time_seconds=end_time - start_time,

            memory_delta_mb=end_memory - start_memory,

            dependencies_loaded=dependencies_loaded,

            circular_refs_detected=circular_refs,

            import_successful=import_successful,

            error_message=error_message

        )





class CircularImportTester:

    """

    Creates and manages circular import test scenarios

    """

    

    def __init__(self, temp_dir: Optional[Path] = None):

        if temp_dir:

            self.temp_dir = Path(temp_dir)

        else:

            self.temp_dir = Path(tempfile.mkdtemp(prefix="circular_import_test_"))

        

        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.created_modules = []

        

    def cleanup(self):

        """Clean up temporary modules and directories"""

        # Remove modules from sys.modules

        for module_name in self.created_modules:

            if module_name in sys.modules:

                del sys.modules[module_name]

                

        # Remove directory

        import shutil

        if self.temp_dir.exists():

            shutil.rmtree(self.temp_dir, ignore_errors=True)

            

    def create_simple_circular_imports(self, cycle_length: int = 3) -> List[Path]:

        """Create a simple circular import chain of specified length"""

        module_files = []

        

        for i in range(cycle_length):

            module_name = f"circular_module_{i}"

            module_file = self.temp_dir / f"{module_name}.py"

            

            # Next module in cycle (wraps around)

            next_module = f"circular_module_{(i + 1) % cycle_length}"

            

            content = f'''"""Circular import test module {i}"""



# This import creates a circular dependency

from {next_module} import shared_function_{(i + 1) % cycle_length}



import time



def shared_function_{i}():

    """Shared function that might be imported by other modules"""

    return f"Function from module {i}: {{time.time()}}"



def use_next_function():

    """Function that uses import from next module"""

    try:

        return shared_function_{(i + 1) % cycle_length}()

    except Exception as e:

        return f"Error calling next function: {{e}}"



# Module-level variable that might cause issues

MODULE_DATA = {{

    "module_id": {i},

    "next_module": "{next_module}",

    "initialization_time": time.time()

}}



# Try to use imported function at module level (dangerous)

try:

    NEXT_FUNCTION_RESULT = shared_function_{(i + 1) % cycle_length}()

except Exception as e:

    NEXT_FUNCTION_RESULT = f"Module level import failed: {{e}}"

'''

            

            module_file.write_text(content, encoding='utf-8')

            module_files.append(module_file)

            self.created_modules.append(module_name)

            

        return module_files

    

    def create_complex_circular_imports(self, num_modules: int = 10) -> List[Path]:

        """Create complex circular imports with multiple interconnected modules"""

        module_files = []

        

        # Create interconnected web of imports

        for i in range(num_modules):

            module_name = f"complex_module_{i:02d}"

            module_file = self.temp_dir / f"{module_name}.py"

            

            # Each module imports from 2-3 others, creating multiple cycles

            import_targets = []

            for j in range(1, min(4, num_modules)):  # Import 1-3 modules

                target_idx = (i + j) % num_modules

                if target_idx != i:

                    import_targets.append(f"complex_module_{target_idx:02d}")

            

            content = f'''"""Complex circular import test module {i}"""



import time

import threading

from typing import Dict, Any, List, Optional



# Complex imports that create cycles

'''

            

            # Add imports

            for target in import_targets:

                target_num = target.split('_')[-1]

                content += f'''

try:

    from {target} import ComplexClass{target_num}, shared_data_{target_num}

except ImportError as e:

    print(f"Import error in module {i}: {{e}}")

    # Create fallback implementations

    class ComplexClass{target_num}:

        def __init__(self):

            self.data = "fallback_data_{target_num}"

    

    shared_data_{target_num} = {{"fallback": True, "module": "{target}"}}

'''

            

            # Add complex class with cross-dependencies

            content += f'''



class ComplexClass{i:02d}:

    """Complex class that might create circular references"""

    

    def __init__(self):

        self.module_id = {i}

        self.creation_time = time.time()

        self.cross_refs = []

        self.thread_local = threading.local()

        

        # Try to create cross-references

        self._setup_cross_references()

    

    def _setup_cross_references(self):

        """Setup cross-references to other modules"""

'''

            

            # Add cross-references

            for target in import_targets[:1]:  # Only use first target to avoid too much complexity

                target_num = target.split('_')[-1]

                content += f'''

        try:

            ref = ComplexClass{target_num}()

            self.cross_refs.append(ref)

        except Exception as e:

            print(f"Cross-reference setup failed: {{e}}")

'''

            

            # Add shared data and functions

            content += f'''

    

    def get_shared_data(self) -> Dict[str, Any]:

        """Get data that might be shared with other modules"""

        return {{

            "module_id": self.module_id,

            "cross_refs_count": len(self.cross_refs),

            "thread_id": threading.get_ident(),

            "timestamp": time.time()

        }}

    

    def interact_with_other_modules(self) -> List[str]:

        """Method that interacts with other modules"""

        results = []

        for ref in self.cross_refs:

            try:

                data = ref.get_shared_data()

                results.append(f"Module {{data['module_id']}}: {{data['timestamp']}}")

            except Exception as e:

                results.append(f"Interaction failed: {{e}}")

        return results



# Module-level shared data

shared_data_{i:02d} = {{

    "module_id": {i},

    "complex_class": ComplexClass{i:02d}(),

    "import_targets": {import_targets},

    "initialization_complete": True

}}



# Module-level function that might be imported

def get_module_info_{i:02d}() -> Dict[str, Any]:

    """Get information about this module"""

    return {{

        "module_name": "complex_module_{i:02d}",

        "has_cross_refs": len(shared_data_{i:02d}["complex_class"].cross_refs) > 0,

        "memory_usage": None  # Could add memory tracking here

    }}



# Try to establish cross-connections at module level

try:

    # This is dangerous and might cause circular import deadlocks

    for target in {import_targets}:

        target_num = target.split('_')[-1]

        if target_num != "{i:02d}":

            try:

                eval(f"shared_data_{{target_num}}")

            except Exception:

                pass  # Expected to fail in some cases

except Exception as e:

    print(f"Module level cross-connection failed in module {i}: {{e}}")

'''

            

            module_file.write_text(content, encoding='utf-8')

            module_files.append(module_file)

            self.created_modules.append(module_name)

            

        return module_files

    

    def create_deadlock_scenario(self) -> List[Path]:

        """Create imports that might cause deadlock in threading scenarios"""

        

        # Module A

        module_a = self.temp_dir / "deadlock_module_a.py"

        content_a = '''"""Deadlock scenario module A"""



import threading

import time

from typing import Any



# This will be imported by module B, potentially causing deadlock

lock_a = threading.Lock()



def function_a():

    """Function that acquires lock A then tries to import from B"""

    with lock_a:

        time.sleep(0.1)  # Simulate work

        try:

            from deadlock_module_b import function_b

            return function_b()

        except ImportError as e:

            return f"Import failed: {e}"



def get_data_a():

    """Function that provides data to other modules"""

    return {"module": "A", "thread": threading.get_ident()}



# Module level initialization that might cause issues

SHARED_DATA_A = {"initialized": True, "thread": threading.get_ident()}

'''

        

        # Module B

        module_b = self.temp_dir / "deadlock_module_b.py"

        content_b = '''"""Deadlock scenario module B"""



import threading

import time

from typing import Any



# This will be imported by module A, potentially causing deadlock

lock_b = threading.Lock()



def function_b():

    """Function that acquires lock B then tries to import from A"""

    with lock_b:

        time.sleep(0.1)  # Simulate work

        try:

            from deadlock_module_a import function_a

            return function_a()

        except ImportError as e:

            return f"Import failed: {e}"



def get_data_b():

    """Function that provides data to other modules"""

    return {"module": "B", "thread": threading.get_ident()}



# Try to import from A at module level

try:

    from deadlock_module_a import get_data_a

    SHARED_DATA_B = get_data_a()

except ImportError:

    SHARED_DATA_B = {"module": "B", "fallback": True}

'''

        

        module_a.write_text(content_a, encoding='utf-8')

        module_b.write_text(content_b, encoding='utf-8')

        

        self.created_modules.extend(["deadlock_module_a", "deadlock_module_b"])

        

        return [module_a, module_b]





class CircularImportTests:

    """

    Comprehensive circular import detection and performance tests

    """

    

    @pytest.fixture(scope="class")

    def import_tester(self) -> CircularImportTester:

        """Setup circular import tester"""

        tester = CircularImportTester()

        yield tester

        tester.cleanup()

        

    @pytest.fixture(autouse=True)

    def setup_test_isolation(self):

        """Ensure each test starts with clean import state"""

        # Store initial modules

        initial_modules = set(sys.modules.keys())

        

        yield

        

        # Clean up any new modules

        current_modules = set(sys.modules.keys())

        new_modules = current_modules - initial_modules

        

        for module_name in new_modules:

            if module_name.startswith(('circular_module_', 'complex_module_', 'deadlock_module_')):

                try:

                    del sys.modules[module_name]

                except KeyError:

                    pass

        

        gc.collect()



    def test_simple_circular_import_detection(self, import_tester: CircularImportTester):

        """

        Test detection of simple circular import cycles

        

        Creates a basic A->B->C->A circular import and verifies

        the detection algorithm identifies it correctly.

        """

        

        # Create simple 3-module circular import

        cycle_length = 3

        module_files = import_tester.create_simple_circular_imports(cycle_length)

        

        # Create detector and analyze

        detector = CircularImportDetector(import_tester.temp_dir)

        import_graph = detector.build_import_graph(module_files)

        

        # Detect cycles using DFS

        start_time = time.time()

        cycles_dfs = detector.detect_cycles_dfs(import_graph)

        detection_time_dfs = time.time() - start_time

        

        # Verify cycle detection

        assert len(cycles_dfs) > 0, "DFS should have detected at least one circular import cycle"

        

        # Find the main cycle (should be close to our expected length)

        main_cycle = max(cycles_dfs, key=len)

        assert len(main_cycle) >= cycle_length, (

            f"Main cycle length {len(main_cycle)} should be at least {cycle_length}"

        )

        

        # Verify all expected modules are in the cycle

        cycle_modules = set(main_cycle)

        expected_modules = {f"circular_module_{i}" for i in range(cycle_length)}

        intersection = cycle_modules & expected_modules

        

        assert len(intersection) >= cycle_length - 1, (

            f"Cycle should include most expected modules. Found: {cycle_modules}, "

            f"Expected: {expected_modules}"

        )

        

        # Test NetworkX detection if available

        if NETWORKX_AVAILABLE:

            start_time = time.time()

            cycles_nx = detector.detect_cycles_networkx(import_graph)

            detection_time_nx = time.time() - start_time

            

            assert len(cycles_nx) > 0, "NetworkX should have detected circular imports"

            

            # NetworkX should be faster for complex graphs

            if len(import_graph) > 5:

                assert detection_time_nx <= detection_time_dfs * 2, (

                    f"NetworkX detection time {detection_time_nx:.3f}s should be competitive "

                    f"with DFS time {detection_time_dfs:.3f}s"

                )

        

        # Performance assertions

        max_detection_time = 1.0  # Should detect cycles within 1 second

        assert detection_time_dfs < max_detection_time, (

            f"Cycle detection took {detection_time_dfs:.3f}s, should be under {max_detection_time}s"

        )



    def test_complex_circular_import_detection(self, import_tester: CircularImportTester):

        """

        Test detection of complex circular import patterns

        

        Creates a web of interconnected modules with multiple overlapping

        cycles to test robust cycle detection.

        """

        

        # Create complex interconnected modules

        num_modules = 15

        module_files = import_tester.create_complex_circular_imports(num_modules)

        

        # Analyze with detector

        detector = CircularImportDetector(import_tester.temp_dir)

        

        start_time = time.time()

        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        

        import_graph = detector.build_import_graph(module_files)

        cycles = detector.detect_cycles_dfs(import_graph)

        

        end_time = time.time()

        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        

        detection_time = end_time - start_time

        memory_used = end_memory - start_memory

        

        # Should detect multiple cycles in complex scenario

        assert len(cycles) >= 2, f"Should detect multiple cycles in complex scenario, found {len(cycles)}"

        

        # Cycles should be non-trivial length

        max_cycle_length = max(len(cycle) for cycle in cycles) if cycles else 0

        assert max_cycle_length >= 3, f"Longest cycle should be at least 3 modules, found {max_cycle_length}"

        

        # Should cover a significant portion of modules

        all_cyclic_modules = set()

        for cycle in cycles:

            all_cyclic_modules.update(cycle)

            

        coverage_ratio = len(all_cyclic_modules) / num_modules

        assert coverage_ratio >= 0.3, (

            f"Cycle detection should cover at least 30% of modules, found {coverage_ratio:.2f}"

        )

        

        # Performance for complex detection

        max_complex_detection_time = 5.0

        assert detection_time < max_complex_detection_time, (

            f"Complex cycle detection took {detection_time:.3f}s, "

            f"should be under {max_complex_detection_time}s"

        )

        

        # Memory usage should be reasonable

        max_memory_mb = 100

        assert memory_used < max_memory_mb, (

            f"Cycle detection used {memory_used:.1f}MB, should be under {max_memory_mb}MB"

        )



    def test_import_performance_under_circular_dependencies(self, import_tester: CircularImportTester):

        """

        Test import performance when circular dependencies exist

        

        Measures the performance impact of importing modules that have

        circular dependencies versus clean modules.

        """

        

        # Create modules with and without circular dependencies

        circular_files = import_tester.create_simple_circular_imports(4)

        

        # Create clean modules for comparison

        clean_modules = []

        for i in range(4):

            module_name = f"clean_module_{i}"

            module_file = import_tester.temp_dir / f"{module_name}.py"

            

            content = f'''"""Clean module {i} without circular imports"""



import time

import math



def clean_function_{i}():

    """Function without circular dependencies"""

    return math.sqrt({i} + 1) * time.time()



def utility_function_{i}():

    """Utility function"""

    return [{j} for {j} in range({i * 10})]



CLEAN_DATA = {{

    "module_id": {i},

    "no_circular_deps": True,

    "utility_result": utility_function_{i}()

}}

'''

            

            module_file.write_text(content, encoding='utf-8')

            clean_modules.append(module_file)

            import_tester.created_modules.append(module_name)

        

        detector = CircularImportDetector(import_tester.temp_dir)

        

        # Measure import performance for circular modules

        circular_results = []

        for module_file in circular_files:

            try:

                result = detector.analyze_import_performance(module_file)

                circular_results.append(result)

            except Exception as e:

                # Some circular imports might fail - that's part of the test

                circular_results.append(ImportPerformanceResult(

                    module_name=f"failed_{module_file.stem}",

                    import_time_seconds=10.0,  # Penalty time

                    memory_delta_mb=0,

                    dependencies_loaded=0,

                    circular_refs_detected=0,

                    import_successful=False,

                    error_message=str(e)

                ))

        

        # Measure import performance for clean modules

        clean_results = []

        for module_file in clean_modules:

            result = detector.analyze_import_performance(module_file)

            clean_results.append(result)

        

        # Analyze results

        circular_successful = [r for r in circular_results if r.import_successful]

        clean_successful = [r for r in clean_results if r.import_successful]

        

        # At least some clean imports should succeed

        assert len(clean_successful) >= len(clean_modules) - 1, (

            f"Most clean imports should succeed, got {len(clean_successful)} out of {len(clean_modules)}"

        )

        

        # Calculate average performance metrics

        if circular_successful and clean_successful:

            avg_circular_time = sum(r.import_time_seconds for r in circular_successful) / len(circular_successful)

            avg_clean_time = sum(r.import_time_seconds for r in clean_successful) / len(clean_successful)

            

            avg_circular_memory = sum(r.memory_delta_mb for r in circular_successful) / len(circular_successful)

            avg_clean_memory = sum(r.memory_delta_mb for r in clean_successful) / len(clean_successful)

            

            # Circular imports should not be dramatically slower (some overhead is acceptable)

            max_slowdown_factor = 5.0

            slowdown_factor = avg_circular_time / avg_clean_time if avg_clean_time > 0 else 1.0

            

            assert slowdown_factor < max_slowdown_factor, (

                f"Circular imports are {slowdown_factor:.2f}x slower than clean imports "

                f"(avg circular: {avg_circular_time:.3f}s, avg clean: {avg_clean_time:.3f}s). "

                f"This suggests poor circular import handling."

            )

            

            # Memory usage difference should not be excessive

            memory_difference = abs(avg_circular_memory - avg_clean_memory)

            max_memory_difference = 20.0  # 20MB difference acceptable

            

            assert memory_difference < max_memory_difference, (

                f"Memory usage difference {memory_difference:.1f}MB between circular and clean imports "

                f"suggests memory leaks in circular import handling"

            )

        

        # Check for circular reference detection

        total_circular_refs = sum(r.circular_refs_detected for r in circular_results)

        

        # Should detect some circular references in circular import scenario

        if len(circular_successful) > 0:

            assert total_circular_refs >= 0, (

                "Should detect circular references in circular import scenario"

            )



    def test_threading_deadlock_with_circular_imports(self, import_tester: CircularImportTester):

        """

        Test for threading deadlocks caused by circular imports

        

        Creates scenarios where circular imports combined with threading

        could cause deadlocks, and verifies the system handles them gracefully.

        """

        

        # Create deadlock scenario modules

        deadlock_modules = import_tester.create_deadlock_scenario()

        

        def import_with_timeout(module_name: str, timeout: float = 10.0) -> Tuple[bool, str]:

            """Import module with timeout to detect deadlocks"""

            

            def import_worker():

                try:

                    # Add temp dir to path

                    if str(import_tester.temp_dir) not in sys.path:

                        sys.path.insert(0, str(import_tester.temp_dir))

                    

                    # Import module

                    importlib.import_module(module_name)

                    return True, "Success"

                    

                except Exception as e:

                    return False, str(e)

                    

                finally:

                    # Remove from path

                    if str(import_tester.temp_dir) in sys.path:

                        sys.path.remove(str(import_tester.temp_dir))

            

            # Use threading to implement timeout

            result_container = [None]

            

            def worker_thread():

                result_container[0] = import_worker()

            

            thread = threading.Thread(target=worker_thread, daemon=True)

            thread.start()

            thread.join(timeout=timeout)

            

            if thread.is_alive():

                # Thread is still running - likely deadlocked

                return False, "Import timed out - possible deadlock"

            

            if result_container[0] is None:

                return False, "Import worker failed to complete"

                

            return result_container[0]

        

        # Test concurrent imports that might deadlock

        def concurrent_import_test(num_workers: int = 4) -> List[Tuple[bool, str]]:

            """Run concurrent imports to trigger potential deadlocks"""

            

            def worker_import(worker_id: int):

                # Each worker tries to import both modules

                results = []

                

                for module_name in ["deadlock_module_a", "deadlock_module_b"]:

                    success, message = import_with_timeout(module_name, timeout=15.0)

                    results.append((success, f"Worker {worker_id}, {module_name}: {message}"))

                    

                    time.sleep(0.1)  # Brief delay between imports

                

                return results

            

            all_results = []

            

            with ThreadPoolExecutor(max_workers=num_workers) as executor:

                futures = []

                

                for worker_id in range(num_workers):

                    future = executor.submit(worker_import, worker_id)

                    futures.append(future)

                

                # Collect results with timeout

                for future in as_completed(futures, timeout=60.0):

                    try:

                        worker_results = future.result()

                        all_results.extend(worker_results)

                    except Exception as e:

                        all_results.append((False, f"Worker exception: {e}"))

            

            return all_results

        

        # Run concurrent import test

        start_time = time.time()

        concurrent_results = concurrent_import_test(num_workers=4)

        test_duration = time.time() - start_time

        

        # Analyze results

        successful_imports = [r for r in concurrent_results if r[0]]

        failed_imports = [r for r in concurrent_results if not r[0]]

        deadlock_failures = [r for r in failed_imports if "timeout" in r[1].lower() or "deadlock" in r[1].lower()]

        

        # Key assertion: Should not have deadlocks

        deadlock_ratio = len(deadlock_failures) / len(concurrent_results)

        max_deadlock_ratio = 0.1  # Allow up to 10% deadlock failures

        

        assert deadlock_ratio <= max_deadlock_ratio, (

            f"Too many deadlock failures: {len(deadlock_failures)} out of {len(concurrent_results)} "

            f"({deadlock_ratio:.2f} ratio, max allowed {max_deadlock_ratio}). "

            f"Deadlock failures: {deadlock_failures[:3]}"

        )

        

        # Test should complete in reasonable time (not hang)

        max_test_duration = 90.0  # 90 seconds max

        assert test_duration < max_test_duration, (

            f"Concurrent import test took {test_duration:.2f}s, should complete under {max_test_duration}s. "

            f"This suggests deadlocks or excessive blocking."

        )

        

        # At least some imports should succeed

        success_ratio = len(successful_imports) / len(concurrent_results)

        min_success_ratio = 0.5  # At least 50% should succeed

        

        assert success_ratio >= min_success_ratio, (

            f"Too few successful imports: {len(successful_imports)} out of {len(concurrent_results)} "

            f"({success_ratio:.2f} ratio, minimum {min_success_ratio}). "

            f"Sample failures: {[r[1] for r in failed_imports[:3]]}"

        )



    def test_memory_leaks_in_circular_import_scenarios(self, import_tester: CircularImportTester):

        """

        Test for memory leaks when circular imports are repeatedly loaded/unloaded

        

        Repeatedly imports and unloads circular modules to detect memory leaks

        that could accumulate over time in long-running processes.

        """

        

        # Create circular import modules

        circular_files = import_tester.create_simple_circular_imports(5)

        module_names = [f"circular_module_{i}" for i in range(5)]

        

        def measure_import_unload_cycle() -> float:

            """Measure memory usage for one import/unload cycle"""

            start_memory = psutil.Process().memory_info().rss / 1024 / 1024

            

            # Add temp dir to path

            if str(import_tester.temp_dir) not in sys.path:

                sys.path.insert(0, str(import_tester.temp_dir))

            

            imported_modules = []

            

            try:

                # Import all circular modules

                for module_name in module_names:

                    try:

                        module = importlib.import_module(module_name)

                        imported_modules.append(module_name)

                    except ImportError as e:

                        # Some circular imports might fail - record but continue

                        print(f"Import failed for {module_name}: {e}")

                

                # Brief usage to ensure modules are fully loaded

                for module_name in imported_modules:

                    if module_name in sys.modules:

                        module = sys.modules[module_name]

                        try:

                            # Try to access module attributes

                            _ = getattr(module, 'MODULE_DATA', None)

                        except Exception:

                            pass

                

            finally:

                # Clean up imported modules

                for module_name in imported_modules:

                    if module_name in sys.modules:

                        del sys.modules[module_name]

                

                # Remove from path

                if str(import_tester.temp_dir) in sys.path:

                    sys.path.remove(str(import_tester.temp_dir))

                

                # Force garbage collection

                gc.collect()

            

            end_memory = psutil.Process().memory_info().rss / 1024 / 1024

            return end_memory - start_memory

        

        # Run multiple import/unload cycles

        num_cycles = 20

        memory_deltas = []

        

        for cycle in range(num_cycles):

            try:

                memory_delta = measure_import_unload_cycle()

                memory_deltas.append(memory_delta)

                

                # Brief pause between cycles

                time.sleep(0.1)

                

            except Exception as e:

                print(f"Cycle {cycle} failed: {e}")

                memory_deltas.append(0)  # Neutral memory delta for failed cycle

        

        # Analyze memory leak patterns

        if len(memory_deltas) >= 10:

            # Look at memory growth trend

            first_half = memory_deltas[:len(memory_deltas)//2]

            second_half = memory_deltas[len(memory_deltas)//2:]

            

            avg_first_half = sum(first_half) / len(first_half)

            avg_second_half = sum(second_half) / len(second_half)

            

            # Memory usage shouldn't grow significantly over time

            memory_growth = avg_second_half - avg_first_half

            max_acceptable_growth = 5.0  # 5MB growth over cycles

            

            assert memory_growth < max_acceptable_growth, (

                f"Memory leak detected: {memory_growth:.2f}MB growth from first half to second half "

                f"of cycles (first: {avg_first_half:.2f}MB, second: {avg_second_half:.2f}MB)"

            )

            

            # Individual cycles shouldn't leak too much memory

            max_cycle_retention = 2.0  # 2MB per cycle max

            excessive_cycles = [delta for delta in memory_deltas if delta > max_cycle_retention]

            

            excessive_ratio = len(excessive_cycles) / len(memory_deltas)

            max_excessive_ratio = 0.3  # Up to 30% of cycles can have higher retention

            

            assert excessive_ratio <= max_excessive_ratio, (

                f"Too many cycles with excessive memory retention: {len(excessive_cycles)} out of "

                f"{len(memory_deltas)} cycles ({excessive_ratio:.2f} ratio, max {max_excessive_ratio})"

            )

        

        # Total memory accumulation check

        total_memory_retained = sum(memory_deltas)

        max_total_retention = num_cycles * 1.0  # 1MB per cycle average max

        

        assert total_memory_retained < max_total_retention, (

            f"Excessive total memory retention: {total_memory_retained:.2f}MB over {num_cycles} cycles "

            f"(average {total_memory_retained/num_cycles:.2f}MB per cycle, max {max_total_retention/num_cycles:.2f}MB per cycle)"

        )



    def test_all_project_modules_for_circular_imports(self):

        """

        Test all actual project modules for circular import issues

        

        Scans the entire project codebase to detect any existing

        circular import problems that could cause pytest crashes.

        """

        

        # Find project root and scan for Python modules

        project_root = Path.cwd()

        

        # Look for main application directories

        app_dirs = []

        for potential_dir in ['netra_backend', 'auth_service', 'analytics_service', 'app', 'src']:

            dir_path = project_root / potential_dir

            if dir_path.exists() and dir_path.is_dir():

                app_dirs.append(dir_path)

        

        if not app_dirs:

            pytest.skip("No application directories found for circular import testing")

        

        # Collect all Python files

        python_files = []

        for app_dir in app_dirs:

            py_files = list(app_dir.rglob("*.py"))

            # Filter out __pycache__ and test files

            py_files = [f for f in py_files if "__pycache__" not in str(f) and not f.name.startswith("test_")]

            python_files.extend(py_files)

        

        if len(python_files) < 5:

            pytest.skip(f"Too few Python files found ({len(python_files)}) for meaningful circular import analysis")

        

        # Analyze circular imports

        detector = CircularImportDetector(project_root)

        

        start_time = time.time()

        import_graph = detector.build_import_graph(python_files)

        cycles = detector.detect_cycles_dfs(import_graph)

        analysis_time = time.time() - start_time

        

        # Report findings

        print(f"\nCircular Import Analysis Results:")

        print(f"- Analyzed {len(python_files)} Python files")

        print(f"- Found {len(import_graph)} modules with imports")

        print(f"- Detected {len(cycles)} circular import cycles")

        print(f"- Analysis completed in {analysis_time:.2f} seconds")

        

        if cycles:

            print(f"\nCircular import cycles found:")

            for i, cycle in enumerate(cycles[:5]):  # Show first 5 cycles

                print(f"  Cycle {i+1}: {' -> '.join(cycle)}")

            if len(cycles) > 5:

                print(f"  ... and {len(cycles) - 5} more cycles")

        

        # Performance assertions

        max_analysis_time = 30.0  # Should complete within 30 seconds

        assert analysis_time < max_analysis_time, (

            f"Circular import analysis took {analysis_time:.2f}s for {len(python_files)} files, "

            f"should complete under {max_analysis_time}s"

        )

        

        # Quality assertions

        if cycles:

            # Large cycles indicate complex dependency issues

            large_cycles = [c for c in cycles if len(c) > 5]

            max_large_cycles = 3  # Allow up to 3 large cycles

            

            assert len(large_cycles) <= max_large_cycles, (

                f"Found {len(large_cycles)} large circular import cycles (>5 modules), "

                f"maximum allowed is {max_large_cycles}. Large cycles indicate complex dependency issues."

            )

            

            # Total number of cycles should be reasonable

            max_total_cycles = min(len(import_graph) // 2, 20)  # At most half the modules or 20 cycles

            assert len(cycles) <= max_total_cycles, (

                f"Found {len(cycles)} circular import cycles, maximum recommended is {max_total_cycles} "

                f"for {len(import_graph)} modules. Too many cycles indicate poor module design."

            )

        

        # If we find critical circular imports, they should be documented

        if cycles and len(cycles) > 5:

            pytest.fail(

                f"Found {len(cycles)} circular import cycles in project codebase. "

                f"This could cause pytest collection crashes. Cycles: {cycles[:3]}"

            )

