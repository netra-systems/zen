# Netra AI Platform - Test Report

**Generated:** 2025-08-14T00:14:50.244931  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 113  
**Passed:** 102  
**Failed:** 1  
**Skipped:** 10  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 113 | 102 | 1 | 10 | 0 | 56.03s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.49s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 56.52s
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
4 workers [1540 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestChangeNotifications::test_check_and_notify_changes_new_models 
app\tests\services\synthetic_data\test_error_recovery.py::TestErrorRecovery::test_graceful_degradation 
app\tests\services\test_agent_service_orchestration.py::TestAgentLifecycleManagement::test_concurrent_agent_orchestration 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_error_recovery.py::TestErrorRecovery::test_graceful_degradation 
app\tests\services\synthetic_data\test_ingestion.py::TestIngestionMethods::test_ingest_with_retry_success 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestChangeNotifications::test_check_and_notify_changes_new_models 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_ingestion.py::TestIngestionMethods::test_ingest_with_retry_success 
app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestChangeNotifications::test_check_and_notify_changes_no_significant_changes 
app\tests\services\synthetic_data\test_ingestion.py::TestIngestionMethods::test_ingest_with_retry_failure 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestChangeNotifications::test_check_and_notify_changes_no_significant_changes 
app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestChangeNotifications::test_check_and_notify_changes_error_handling 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestChangeNotifications::test_check_and_notify_changes_error_handling 
app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerInitialization::test_initialization_with_redis 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerInitialization::test_initialization_with_redis 
app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerInitialization::test_initialization_without_redis 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerInitialization::test_initialization_without_redis 
app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerInitialization::test_default_schedules_created 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerInitialization::test_default_schedules_created 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerInitialization::test_default_schedule_configurations 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerInitialization::test_default_schedule_configurations 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerStartStop::test_start_scheduler 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerStartStop::test_start_scheduler 
app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerStartStop::test_start_scheduler_already_running 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerStartStop::test_start_scheduler_already_running 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerStartStop::test_stop_scheduler 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduler_initialization.py::TestSchedulerStartStop::test_stop_scheduler 
app\tests\services\supply_research_scheduler\test_scheduler_loop.py::TestSchedulerLoop::test_scheduler_loop_execution 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_ingestion.py::TestIngestionMethods::test_ingest_with_retry_failure 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentLifecycleManagement::test_concurrent_agent_orchestration 
app\tests\services\synthetic_data\test_ingestion.py::TestIngestionMethods::test_ingest_with_deduplication 
app\tests\services\test_agent_service_orchestration.py::TestAgentLifecycleManagement::test_agent_state_transitions 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_ingestion.py::TestIngestionMethods::test_ingest_with_deduplication 
app\tests\services\synthetic_data\test_ingestion.py::TestIngestionMethods::test_ingest_with_transform 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_ingestion.py::TestIngestionMethods::test_ingest_with_transform 
app\tests\services\synthetic_data\test_initialization.py::TestServiceInitialization::test_initialization 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_initialization.py::TestServiceInitialization::test_initialization 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\synthetic_data\test_initialization.py::TestServiceInitialization::test_default_tools_structure 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_initialization.py::TestServiceInitialization::test_default_tools_structure 
app\tests\services\synthetic_data\test_initialization.py::TestWorkloadTypeSelection::test_select_workload_type 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_scheduler_loop.py::TestSchedulerLoop::test_scheduler_loop_execution 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\supply_research_scheduler\test_scheduler_loop.py::TestSchedulerLoop::test_scheduler_loop_no_due_schedules 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_initialization.py::TestWorkloadTypeSelection::test_select_workload_type 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
app\tests\services\synthetic_data\test_initialization.py::TestWorkloadTypeSelection::test_select_agent_type 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_initialization.py::TestWorkloadTypeSelection::test_select_agent_type 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
app\tests\services\synthetic_data\test_integration.py::TestIntegration::test_complete_generation_workflow 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\a...(truncated)
```

### Frontend Output
```

'hooks' is not recognized as an internal or external command,
operable program or batch file.

```

## Error Summary

### Backend Errors
- [gw1][36m [  3%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_integration.py::TestIntegration::test_security_and_access_control
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
- INTERNALERROR> E             coverage.exceptions.DataError: Couldn't use data file 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\.coverage.Anthony.45980.XdaoThNx.wgw1': no such table: file
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
- INTERNALERROR> KeyError: <WorkerController gw1>
- [FAIL] TESTS FAILED with exit code 3 after 54.91s


---
*Generated by Netra AI Unified Test Runner v3.0*
