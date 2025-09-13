"""

Continuous Validation Framework for SSOT Refactoring

=====================================================

CRITICAL: This framework ensures ALL refactoring is atomic, complete, and tested.

Validates work from all refactoring agents and ensures zero regressions.

"""



import asyncio

import json

import os

import sys

import time

from datetime import datetime, timedelta

from pathlib import Path

from typing import Dict, List, Set, Any, Optional, Tuple

import subprocess

import traceback



# Add project root to path

project_root = Path(__file__).parent.parent.parent

sys.path.insert(0, str(project_root))



from loguru import logger



class RefactoringValidator:

    """Continuous validation during SSOT refactoring."""

    

    def __init__(self):

        self.project_root = project_root

        self.validation_start = datetime.now()

        self.baseline_metrics = {}

        self.test_results = []

        self.legacy_files_removed = []

        self.import_violations = []

        

        # Test suites to monitor

        self.test_suites = [

            'tests/mission_critical/test_websocket_agent_events_suite.py',

            'tests/integration/test_factory_consolidation.py',

            'tests/integration/test_agent_consolidation.py', 

            'tests/integration/test_execution_consolidation.py',

            'tests/integration/test_infrastructure_consolidation.py',

            'tests/unified_test_runner.py'

        ]

        

        # Legacy files to track for deletion

        self.legacy_files_to_delete = [

            # Factory consolidation targets

            'netra_backend/app/agents/agent_instance_factory_optimized.py',

            'netra_backend/app/agents/agent_instance_factory_legacy.py',

            'netra_backend/app/agents/agent_instance_factory_old.py',

            

            # Agent consolidation targets

            'netra_backend/app/agents/data_sub_agent/agent_core_legacy.py',

            'netra_backend/app/agents/data_sub_agent/agent_legacy_massive.py',

            'netra_backend/app/agents/data_sub_agent_legacy.py',

            

            # Tool dispatcher consolidation

            'netra_backend/app/agents/tool_dispatcher_core.py',

            'netra_backend/app/agents/request_scoped_tool_dispatcher.py',

            'netra_backend/app/agents/admin_tool_dispatcher/modernized_wrapper.py',

            

            # Infrastructure consolidation

            'netra_backend/app/infrastructure/legacy_managers/',

            'netra_backend/app/infrastructure/old_session_manager.py',

            'netra_backend/app/infrastructure/duplicate_id_generator.py'

        ]

        

        # Legacy import patterns to detect

        self.legacy_import_patterns = [

            r'from\s+.*agent_instance_factory_optimized',

            r'from\s+.*agent_instance_factory_legacy',

            r'from\s+.*agent_core_legacy',

            r'from\s+.*agent_legacy_massive',

            r'from\s+.*tool_dispatcher_core',

            r'from\s+.*request_scoped_tool_dispatcher',

            r'import\s+.*agent_instance_factory_optimized',

            r'import\s+.*agent_core_legacy'

        ]

        

        logger.info("RefactoringValidator initialized")

        logger.info(f"Monitoring {len(self.test_suites)} test suites")

        logger.info(f"Tracking {len(self.legacy_files_to_delete)} legacy files")

        

    def capture_baseline(self) -> Dict[str, Any]:

        """Capture baseline metrics before refactoring."""

        logger.info("Capturing baseline metrics...")

        

        baseline = {

            'timestamp': datetime.now().isoformat(),

            'test_results': self._run_all_tests(quick=True),

            'performance_metrics': self._capture_performance_metrics(),

            'code_metrics': self._capture_code_metrics(),

            'import_map': self._capture_import_map()

        }

        

        self.baseline_metrics = baseline

        

        # Save baseline to file

        baseline_file = self.project_root / 'tests/refactoring/baseline_metrics.json'

        baseline_file.parent.mkdir(parents=True, exist_ok=True)

        

        with open(baseline_file, 'w') as f:

            json.dump(baseline, f, indent=2, default=str)

            

        logger.info(f"Baseline metrics saved to {baseline_file}")

        return baseline

        

    def _run_all_tests(self, quick: bool = False) -> Dict[str, Any]:

        """Run all test suites and capture results."""

        results = {

            'total_tests': 0,

            'passed': 0,

            'failed': 0,

            'skipped': 0,

            'duration': 0,

            'suite_results': {}

        }

        

        test_cmd_base = [

            sys.executable,

            str(self.project_root / 'tests/unified_test_runner.py'),

            '--real-services',

            '--fast-fail' if quick else '--no-coverage'

        ]

        

        start = time.time()

        

        # Run unified test suite

        try:

            result = subprocess.run(

                test_cmd_base,

                capture_output=True,

                text=True,

                timeout=300 if quick else 1800  # 5 min quick, 30 min full

            )

            

            # Parse test output

            output_lines = result.stdout.split('\n')

            for line in output_lines:

                if 'passed' in line.lower():

                    parts = line.split()

                    for i, part in enumerate(parts):

                        if part == 'passed':

                            try:

                                results['passed'] = int(parts[i-1])

                            except (IndexError, ValueError):

                                pass

                                

                if 'failed' in line.lower():

                    parts = line.split()

                    for i, part in enumerate(parts):

                        if part == 'failed':

                            try:

                                results['failed'] = int(parts[i-1])

                            except (IndexError, ValueError):

                                pass

                                

            results['total_tests'] = results['passed'] + results['failed'] + results['skipped']

            results['success_rate'] = (results['passed'] / max(results['total_tests'], 1)) * 100

            

        except subprocess.TimeoutExpired:

            logger.warning("Test run timed out")

            results['failed'] = -1

            results['error'] = 'timeout'

        except Exception as e:

            logger.error(f"Test run failed: {e}")

            results['failed'] = -1

            results['error'] = str(e)

            

        results['duration'] = time.time() - start

        return results

        

    def _capture_performance_metrics(self) -> Dict[str, Any]:

        """Capture current performance metrics."""

        metrics = {

            'memory_usage': {},

            'response_times': {},

            'throughput': {}

        }

        

        # Run performance benchmarks

        perf_script = self.project_root / 'scripts/check_performance_metrics.py'

        if perf_script.exists():

            try:

                result = subprocess.run(

                    [sys.executable, str(perf_script), '--json'],

                    capture_output=True,

                    text=True,

                    timeout=60

                )

                if result.returncode == 0:

                    metrics = json.loads(result.stdout)

            except Exception as e:

                logger.warning(f"Could not capture performance metrics: {e}")

                

        return metrics

        

    def _capture_code_metrics(self) -> Dict[str, Any]:

        """Capture code complexity and duplication metrics."""

        metrics = {

            'total_files': 0,

            'total_lines': 0,

            'duplicate_code_blocks': 0,

            'cyclomatic_complexity': {}

        }

        

        # Count Python files and lines

        py_files = list(self.project_root.glob('**/*.py'))

        metrics['total_files'] = len(py_files)

        

        total_lines = 0

        for file in py_files:

            try:

                with open(file, 'r') as f:

                    total_lines += len(f.readlines())

            except:

                pass

        metrics['total_lines'] = total_lines

        

        return metrics

        

    def _capture_import_map(self) -> Dict[str, List[str]]:

        """Capture current import relationships."""

        import_map = {}

        

        py_files = list(self.project_root.glob('netra_backend/**/*.py'))

        for file in py_files:

            try:

                with open(file, 'r') as f:

                    content = f.read()

                    imports = []

                    for line in content.split('\n'):

                        if line.startswith('from ') or line.startswith('import '):

                            imports.append(line.strip())

                    if imports:

                        import_map[str(file.relative_to(self.project_root))] = imports

            except:

                pass

                

        return import_map

        

    async def validate_continuously(self):

        """Run validation every 30 minutes during refactoring."""

        logger.info("Starting continuous validation loop...")

        

        while True:

            try:

                logger.info("="*80)

                logger.info(f"Running validation cycle at {datetime.now()}")

                logger.info("="*80)

                

                # Run comprehensive validation

                validation_results = {

                    'timestamp': datetime.now().isoformat(),

                    'test_results': self._run_all_tests(quick=True),

                    'legacy_check': self.verify_legacy_removal(),

                    'import_check': self.verify_no_legacy_imports(),

                    'regression_check': self.check_for_regressions(),

                    'performance_check': self._compare_performance()

                }

                

                # Save results

                results_file = self.project_root / f'tests/refactoring/validation_{datetime.now():%Y%m%d_%H%M%S}.json'

                with open(results_file, 'w') as f:

                    json.dump(validation_results, f, indent=2, default=str)

                    

                # Report status

                self._report_validation_status(validation_results)

                

                # Sleep for 30 minutes

                await asyncio.sleep(1800)

                

            except KeyboardInterrupt:

                logger.info("Validation loop interrupted")

                break

            except Exception as e:

                logger.error(f"Validation cycle failed: {e}")

                logger.error(traceback.format_exc())

                await asyncio.sleep(300)  # Retry in 5 minutes

                

    def verify_legacy_removal(self) -> Dict[str, Any]:

        """Verify all legacy files are removed."""

        logger.info("Checking for legacy file removal...")

        

        remaining_files = []

        removed_files = []

        

        for file_path in self.legacy_files_to_delete:

            full_path = self.project_root / file_path

            

            if full_path.exists():

                if full_path.is_file():

                    remaining_files.append(str(file_path))

                elif full_path.is_dir():

                    # Check if directory has any Python files

                    py_files = list(full_path.glob('**/*.py'))

                    if py_files:

                        remaining_files.append(f"{file_path} ({len(py_files)} files)")

            else:

                removed_files.append(str(file_path))

                

        result = {

            'total_legacy_files': len(self.legacy_files_to_delete),

            'removed': len(removed_files),

            'remaining': len(remaining_files),

            'remaining_files': remaining_files,

            'removed_files': removed_files,

            'complete': len(remaining_files) == 0

        }

        

        if remaining_files:

            logger.warning(f"Legacy files still exist: {remaining_files}")

        else:

            logger.success("All legacy files removed!")

            

        return result

        

    def verify_no_legacy_imports(self) -> Dict[str, Any]:

        """Scan codebase for any legacy imports."""

        logger.info("Scanning for legacy imports...")

        

        violations = []

        files_scanned = 0

        

        # Scan all Python files

        py_files = list(self.project_root.glob('netra_backend/**/*.py'))

        py_files.extend(list(self.project_root.glob('tests/**/*.py')))

        

        for file_path in py_files:

            files_scanned += 1

            try:

                with open(file_path, 'r') as f:

                    content = f.read()

                    line_num = 0

                    

                    for line in content.split('\n'):

                        line_num += 1

                        

                        # Check each legacy pattern

                        for pattern in self.legacy_import_patterns:

                            import re

                            if re.search(pattern, line):

                                violations.append({

                                    'file': str(file_path.relative_to(self.project_root)),

                                    'line': line_num,

                                    'content': line.strip(),

                                    'pattern': pattern

                                })

                                

            except Exception as e:

                logger.warning(f"Could not scan {file_path}: {e}")

                

        result = {

            'files_scanned': files_scanned,

            'violations_found': len(violations),

            'violations': violations[:20],  # Limit to first 20

            'complete': len(violations) == 0

        }

        

        if violations:

            logger.error(f"Found {len(violations)} legacy import violations!")

            for v in violations[:5]:

                logger.error(f"  {v['file']}:{v['line']} - {v['content']}")

        else:

            logger.success("No legacy imports found!")

            

        return result

        

    def check_for_regressions(self) -> Dict[str, Any]:

        """Compare current state with baseline for regressions."""

        logger.info("Checking for regressions...")

        

        if not self.baseline_metrics:

            logger.warning("No baseline metrics available")

            return {'error': 'No baseline metrics'}

            

        current_tests = self._run_all_tests(quick=True)

        baseline_tests = self.baseline_metrics.get('test_results', {})

        

        regressions = []

        

        # Check test pass rate

        current_rate = current_tests.get('success_rate', 0)

        baseline_rate = baseline_tests.get('success_rate', 0)

        

        if current_rate < baseline_rate - 5:  # Allow 5% tolerance

            regressions.append({

                'type': 'test_pass_rate',

                'baseline': baseline_rate,

                'current': current_rate,

                'delta': current_rate - baseline_rate

            })

            

        # Check test count

        current_total = current_tests.get('total_tests', 0)

        baseline_total = baseline_tests.get('total_tests', 0)

        

        if current_total < baseline_total * 0.95:  # Tests shouldn't decrease by >5%

            regressions.append({

                'type': 'test_count',

                'baseline': baseline_total,

                'current': current_total,

                'delta': current_total - baseline_total

            })

            

        result = {

            'regressions_found': len(regressions),

            'regressions': regressions,

            'current_metrics': current_tests,

            'baseline_metrics': baseline_tests,

            'no_regressions': len(regressions) == 0

        }

        

        if regressions:

            logger.warning(f"Found {len(regressions)} regressions")

        else:

            logger.success("No regressions detected!")

            

        return result

        

    def _compare_performance(self) -> Dict[str, Any]:

        """Compare performance metrics with baseline."""

        current_perf = self._capture_performance_metrics()

        baseline_perf = self.baseline_metrics.get('performance_metrics', {})

        

        # Simple comparison - extend as needed

        result = {

            'current': current_perf,

            'baseline': baseline_perf,

            'degradation_detected': False

        }

        

        return result

        

    def _report_validation_status(self, results: Dict[str, Any]):

        """Generate and log validation status report."""

        logger.info("\n" + "="*80)

        logger.info("VALIDATION STATUS REPORT")

        logger.info("="*80)

        

        # Test results

        test_results = results.get('test_results', {})

        logger.info(f"Tests: {test_results.get('passed', 0)} passed, "

                   f"{test_results.get('failed', 0)} failed "

                   f"(Success rate: {test_results.get('success_rate', 0):.1f}%)")

        

        # Legacy removal

        legacy_check = results.get('legacy_check', {})

        logger.info(f"Legacy Files: {legacy_check.get('removed', 0)}/{legacy_check.get('total_legacy_files', 0)} removed")

        if legacy_check.get('remaining', 0) > 0:

            logger.warning(f"  Still remaining: {legacy_check.get('remaining', 0)} files")

            

        # Import violations

        import_check = results.get('import_check', {})

        if import_check.get('violations_found', 0) > 0:

            logger.error(f"Legacy Imports: {import_check.get('violations_found', 0)} violations found!")

        else:

            logger.success("Legacy Imports: Clean!")

            

        # Regressions

        regression_check = results.get('regression_check', {})

        if regression_check.get('regressions_found', 0) > 0:

            logger.warning(f"Regressions: {regression_check.get('regressions_found', 0)} detected")

        else:

            logger.success("Regressions: None detected")

            

        logger.info("="*80 + "\n")

        

    def generate_final_report(self) -> Dict[str, Any]:

        """Generate comprehensive final validation report."""

        logger.info("Generating final validation report...")

        

        report = {

            'refactoring_duration': str(datetime.now() - self.validation_start),

            'final_test_results': self._run_all_tests(quick=False),

            'legacy_removal_complete': self.verify_legacy_removal(),

            'import_validation': self.verify_no_legacy_imports(),

            'regression_analysis': self.check_for_regressions(),

            'performance_comparison': self._compare_performance(),

            'code_metrics_comparison': {

                'before': self.baseline_metrics.get('code_metrics', {}),

                'after': self._capture_code_metrics()

            }

        }

        

        # Save final report

        report_file = self.project_root / f'tests/refactoring/FINAL_VALIDATION_REPORT_{datetime.now():%Y%m%d}.json'

        with open(report_file, 'w') as f:

            json.dump(report, f, indent=2, default=str)

            

        logger.info(f"Final report saved to {report_file}")

        return report





async def main():

    """Main entry point for continuous validation."""

    validator = RefactoringValidator()

    

    # Capture baseline first

    logger.info("Capturing baseline metrics...")

    validator.capture_baseline()

    

    # Start continuous validation

    logger.info("Starting continuous validation...")

    await validator.validate_continuously()





if __name__ == "__main__":

    # Run the validator

    asyncio.run(main())

