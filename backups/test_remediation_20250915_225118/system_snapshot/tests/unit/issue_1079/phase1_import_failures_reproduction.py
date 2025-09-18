#!/usr/bin/env python3
"""
Issue #1079 Phase 1: Import Failures Reproduction Test

This test reproduces the core import failures discovered in Issue #1079:
- Timeout failures (217 seconds) due to import hangs
- ModuleNotFoundError for 'netra_backend.app.db.supply_database_manager'
- KeyError for missing Agent class
- Infinite loops in import chains
"""

import sys
import time
import unittest
import traceback
from unittest.mock import patch
from contextlib import contextmanager
import threading
import signal

class TimeoutException(Exception):
    """Exception raised when import takes too long"""
    pass

class ImportFailureReproduction(unittest.TestCase):
    """Phase 1: Reproduce the exact import failures found in Issue #1079"""

    def setUp(self):
        """Set up test environment"""
        self.timeout_duration = 30  # Much shorter than 217 seconds for testing
        self.failed_imports = []
        self.hanging_imports = []

    @contextmanager
    def timeout_context(self, seconds):
        """Context manager for timeout handling during imports"""
        def timeout_handler(signum, frame):
            raise TimeoutException(f"Import timed out after {seconds} seconds")

        # Set up signal handler for timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)

        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def test_supply_database_manager_import_failure(self):
        """Test the specific import failure for supply_database_manager"""
        print("\n=== Phase 1.1: Testing supply_database_manager import failure ===")

        # This should reproduce the exact error from Issue #1079
        with self.assertRaises((ModuleNotFoundError, ImportError)) as context:
            try:
                from netra_backend.app.db.supply_database_manager import SupplyDatabaseManager
            except Exception as e:
                print(f"Import failed as expected: {type(e).__name__}: {e}")
                raise

        print(f"✓ Successfully reproduced import failure: {context.exception}")
        self.failed_imports.append("netra_backend.app.db.supply_database_manager")

    def test_agent_class_keyerror_reproduction(self):
        """Test the KeyError for missing Agent class"""
        print("\n=== Phase 1.2: Testing Agent class KeyError ===")

        # Try to import modules that reference Agent class
        problematic_modules = [
            "netra_backend.app.agents.supervisor_agent_modern",
            "netra_backend.app.agents.base_agent",
            "netra_backend.app.agents.registry"
        ]

        for module_name in problematic_modules:
            try:
                with self.timeout_context(self.timeout_duration):
                    __import__(module_name)
                    print(f"✓ {module_name} imported successfully")
            except TimeoutException:
                print(f"✗ {module_name} TIMEOUT - hanging import detected")
                self.hanging_imports.append(module_name)
            except (ImportError, ModuleNotFoundError, KeyError) as e:
                print(f"✗ {module_name} import failed: {type(e).__name__}: {e}")
                self.failed_imports.append(module_name)
            except Exception as e:
                print(f"✗ {module_name} unexpected error: {type(e).__name__}: {e}")

    def test_circular_import_detection(self):
        """Test for circular import patterns that cause hangs"""
        print("\n=== Phase 1.3: Testing circular import detection ===")

        # Monitor import chain to detect circular dependencies
        original_import = __builtins__['__import__']
        import_chain = []

        def tracking_import(name, *args, **kwargs):
            if name.startswith('netra_backend.app.agents'):
                import_chain.append(name)
                print(f"Import chain: {' -> '.join(import_chain[-5:])}")  # Last 5 imports

                # Check for circular pattern
                if len(import_chain) > 10 and name in import_chain[-10:-1]:
                    raise ImportError(f"Circular import detected: {name} appears multiple times in chain")

            return original_import(name, *args, **kwargs)

        try:
            with patch('builtins.__import__', side_effect=tracking_import):
                with self.timeout_context(self.timeout_duration):
                    try:
                        from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgentModern
                    except (ImportError, TimeoutException) as e:
                        print(f"Expected failure during circular import test: {e}")

        except Exception as e:
            print(f"Circular import test completed with: {type(e).__name__}: {e}")

        print(f"Import chain length: {len(import_chain)}")
        if len(import_chain) > 20:
            print("⚠️  Very long import chain detected - potential circular imports")

    def test_import_timeout_simulation(self):
        """Test the 217-second timeout scenario with shorter duration"""
        print("\n=== Phase 1.4: Testing import timeout simulation ===")

        # Simulate the exact timeout scenario but with shorter time
        timeout_modules = [
            "netra_backend.app.agents.supervisor_agent_modern",
            "netra_backend.app.agents.base_agent",
            "netra_backend.app.db.supply_database_manager"
        ]

        for module_name in timeout_modules:
            print(f"Testing timeout for: {module_name}")
            start_time = time.time()

            try:
                with self.timeout_context(5):  # 5 second timeout for testing
                    __import__(module_name)
                    duration = time.time() - start_time
                    print(f"✓ {module_name} imported in {duration:.2f}s")

            except TimeoutException:
                duration = time.time() - start_time
                print(f"✗ {module_name} TIMEOUT after {duration:.2f}s (would be 217s in real scenario)")
                self.hanging_imports.append(module_name)

            except Exception as e:
                duration = time.time() - start_time
                print(f"✗ {module_name} failed in {duration:.2f}s: {type(e).__name__}: {e}")
                self.failed_imports.append(module_name)

    def test_memory_growth_during_import_hangs(self):
        """Test if hanging imports cause memory growth"""
        print("\n=== Phase 1.5: Testing memory growth during import hangs ===")

        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        print(f"Initial memory usage: {initial_memory:.2f} MB")

        # Try problematic imports while monitoring memory
        for i in range(3):
            try:
                with self.timeout_context(2):  # Short timeout
                    from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgentModern
            except:
                pass

            current_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = current_memory - initial_memory
            print(f"Attempt {i+1} memory: {current_memory:.2f} MB (growth: +{memory_growth:.2f} MB)")

            if memory_growth > 50:  # 50MB growth threshold
                print("⚠️  Significant memory growth detected during import attempts")

    def tearDown(self):
        """Report test results"""
        print("\n" + "="*60)
        print("PHASE 1 REPRODUCTION TEST SUMMARY")
        print("="*60)
        print(f"Failed imports: {len(self.failed_imports)}")
        for module in self.failed_imports:
            print(f"  - {module}")

        print(f"\nHanging imports: {len(self.hanging_imports)}")
        for module in self.hanging_imports:
            print(f"  - {module}")

        # Determine if we successfully reproduced the issue
        if self.failed_imports or self.hanging_imports:
            print("\n✓ SUCCESS: Issue #1079 import failures successfully reproduced")
        else:
            print("\n✗ FAILURE: Could not reproduce Issue #1079 import failures")

if __name__ == "__main__":
    print("="*60)
    print("ISSUE #1079 PHASE 1: IMPORT FAILURES REPRODUCTION")
    print("="*60)
    print("This test reproduces the core import failures from Issue #1079:")
    print("- 217-second timeout scenarios")
    print("- ModuleNotFoundError for supply_database_manager")
    print("- KeyError for missing Agent class")
    print("- Circular import detection")
    print("="*60)

    unittest.main(verbosity=2)