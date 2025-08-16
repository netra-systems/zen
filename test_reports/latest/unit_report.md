# Netra AI Platform - Test Report

**Generated:** 2025-08-15T17:45:17.114752  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 799  
**Passed:** 779  
**Failed:** 1  
**Skipped:** 19  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 799 | 779 | 1 | 19 | 0 | 50.20s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 1.25s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 51.46s
- **Exit Code:** 15

### Backend Configuration
```
--category unit -v --coverage --fail-fast --parallel=4 --markers not real_services
```

### Frontend Configuration
```
--category unit
```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: unit
  Parallel: 4
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/services app/tests/core -vv -n 4 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 4/4 workers
4 workers [2287 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_circuit_breaker_pattern <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_performance_profiling 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_with_duration 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_performance_profiling 
app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_alert_configuration 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_circuit_breaker_pattern <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_graceful_degradation_under_load <- tests\services\test_agent_service_orchestration_workflows.py 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_graceful_degradation_under_load <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_error_propagation_and_isolation <- tests\services\test_agent_service_orchestration_workflows.py 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_with_duration 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_failure 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_failure 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_success 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_success 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_failure 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_failure 
app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_measures_duration 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_measures_duration 
app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_without_context 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_without_context 
app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_create_audit_logger_factory 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_create_audit_logger_factory 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_end_to_end_audit_workflow 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_llm_name 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_llm_name 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_multiple_executions 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_end_to_end_audit_workflow 
app\tests\services\test_corpus_audit.py::TestAuditPerformance::test_large_result_data_handling 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_multiple_executions 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditPerformance::test_large_result_data_handling 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_concurrent_execution 
app\tests\services\test_corpus_audit.py::TestAuditPerformance::test_metadata_edge_cases 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_concurrent_execution 
[gw2][36m [  1%]...(truncated)
```

### Frontend Output
```

'hooks' is not recognized as an internal or external command,
operable program or batch file.

```

## Error Summary

### Backend Errors
- [gw2][36m [ 34%] [0m[31mFAILED[0m app\tests\services\test_supply_research_service_basic.py::TestSupplyItemRetrieval::test_get_supply_items_with_confidence_filter
- INTERNALERROR> def worker_internal_error(
- INTERNALERROR>         self, node: WorkerController, formatted_error: str
- INTERNALERROR>     ) -> None:
- INTERNALERROR>         """
- INTERNALERROR>         pytest_internalerror() was called on the worker.
- INTERNALERROR>
- INTERNALERROR>         pytest_internalerror() arguments are an excinfo and an excrepr, which can't
- INTERNALERROR>         be serialized, so we go with a poor man's solution of raising an exception
- INTERNALERROR>         here ourselves using the formatted message.
- INTERNALERROR>         """
- INTERNALERROR>         self._active_nodes.remove(node)
- INTERNALERROR>         try:
- INTERNALERROR> >           assert False, formatted_error
- INTERNALERROR> E           AssertionError: Traceback (most recent call last):
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 115, in _execute
- INTERNALERROR> E                 return self.con.execute(sql, parameters)    # type: ignore[arg-type]
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E             sqlite3.OperationalError: no such table: file
- INTERNALERROR> E
- INTERNALERROR> E             During handling of the above exception, another exception occurred:
- INTERNALERROR> E
- INTERNALERROR> E             Traceback (most recent call last):
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 120, in _execute
- INTERNALERROR> E                 return self.con.execute(sql, parameters)    # type: ignore[arg-type]
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E             sqlite3.OperationalError: no such table: file
- INTERNALERROR> E
- INTERNALERROR> E             The above exception was the direct cause of the following exception:
- INTERNALERROR> E
- INTERNALERROR> E             Traceback (most recent call last):
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\main.py", line 289, in wrap_session
- INTERNALERROR> E                 session.exitstatus = doit(config, session) or 0
- INTERNALERROR> E                                      ^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\main.py", line 343, in _main
- INTERNALERROR> E                 config.hook.pytest_runtestloop(session=session)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_hooks.py", line 512, in __call__
- INTERNALERROR> E                 return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_manager.py", line 120, in _hookexec
- INTERNALERROR> E                 return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 167, in _multicall
- INTERNALERROR> E                 raise exception
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR> E                 teardown.throw(exception)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\logging.py", line 801, in pytest_runtestloop
- INTERNALERROR> E                 return (yield)  # Run all the tests.
- INTERNALERROR> E                         ^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR> E                 teardown.throw(exception)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\terminal.py", line 688, in pytest_runtestloop
- INTERNALERROR> E                 result = yield
- INTERNALERROR> E                          ^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 152, in _multicall
- INTERNALERROR> E                 teardown.send(result)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pytest_cov\plugin.py", line 346, in pytest_runtestloop
- INTERNALERROR> E                 self.cov_controller.finish()
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pytest_cov\engine.py", line 57, in ensure_topdir_wrapper
- INTERNALERROR> E                 return meth(self, *args, **kwargs)
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pytest_cov\engine.py", line 471, in finish
- INTERNALERROR> E                 self.cov.save()
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\control.py", line 818, in save
- INTERNALERROR> E                 data = self.get_data()
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\control.py", line 899, in get_data
- INTERNALERROR> E                 self._post_save_work()
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\control.py", line 930, in _post_save_work
- INTERNALERROR> E                 self._data.touch_files(paths, plugin_name)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqldata.py", line 620, in touch_files
- INTERNALERROR> E                 self._file_id(filename, add=True)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqldata.py", line 416, in _file_id
- INTERNALERROR> E                 self._file_map[filename] = con.execute_for_rowid(
- INTERNALERROR> E                                            ^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 171, in execute_for_rowid
- INTERNALERROR> E                 with self.execute(sql, parameters) as cur:
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\contextlib.py", line 137, in __enter__
- INTERNALERROR> E                 return next(self.gen)
- INTERNALERROR> E                        ^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 150, in execute
- INTERNALERROR> E                 cur = self._execute(sql, parameters)
- INTERNALERROR> E                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 138, in _execute
- INTERNALERROR> E                 raise DataError(f"Couldn't use data file {self.filename!r}: {msg}") from exc
- INTERNALERROR> E             coverage.exceptions.DataError: Couldn't use data file 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\.coverage.Anthony.49376.Xwooxuex.wgw2': no such table: file
- INTERNALERROR> E           assert False
- INTERNALERROR>
- INTERNALERROR> ..\..\..\..\miniconda3\Lib\site-packages\xdist\dsession.py:232: AssertionError
- INTERNALERROR> Traceback (most recent call last):
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\main.py", line 289, in wrap_session
- INTERNALERROR>     session.exitstatus = doit(config, session) or 0
- INTERNALERROR>                          ^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\main.py", line 343, in _main
- INTERNALERROR>     config.hook.pytest_runtestloop(session=session)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_hooks.py", line 512, in __call__
- INTERNALERROR>     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
- INTERNALERROR>            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_manager.py", line 120, in _hookexec
- INTERNALERROR>     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
- INTERNALERROR>            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 167, in _multicall
- INTERNALERROR>     raise exception
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR>     teardown.throw(exception)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\logging.py", line 801, in pytest_runtestloop
- INTERNALERROR>     return (yield)  # Run all the tests.
- INTERNALERROR>             ^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR>     teardown.throw(exception)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\terminal.py", line 688, in pytest_runtestloop
- INTERNALERROR>     result = yield
- INTERNALERROR>              ^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR>     teardown.throw(exception)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pytest_cov\plugin.py", line 340, in pytest_runtestloop
- INTERNALERROR>     result = yield
- INTERNALERROR>              ^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 121, in _multicall
- INTERNALERROR>     res = hook_impl.function(*args)
- INTERNALERROR>           ^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\xdist\dsession.py", line 138, in pytest_runtestloop
- INTERNALERROR>     self.loop_once()
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\xdist\dsession.py", line 163, in loop_once
- INTERNALERROR>     call(**kwargs)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\xdist\dsession.py", line 218, in worker_workerfinished
- INTERNALERROR>     self._active_nodes.remove(node)
- INTERNALERROR> KeyError: <WorkerController gw2>
- [FAIL] TESTS FAILED with exit code 3 after 49.22s


---
*Generated by Netra AI Unified Test Runner v3.0*
