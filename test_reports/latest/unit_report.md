# Netra AI Platform - Test Report

**Generated:** 2025-08-15T23:09:22.736455  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 779  
**Passed:** 755  
**Failed:** 1  
**Skipped:** 23  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 779 | 755 | 1 | 23 | 0 | 76.43s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 76.43s
- **Exit Code:** 2

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
4 workers [2444 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_advanced_regex_patterns 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_geo_distributed_simulation 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_execution 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_geo_distributed_simulation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_adaptive_generation_feedback 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_adaptive_generation_feedback 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_multi_model_workload_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_multi_model_workload_generation 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_advanced_regex_patterns 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_edge_case_regex_patterns 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_edge_case_regex_patterns 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_complex_expression_patterns 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_execution 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_with_model_dump_fallback 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_complex_expression_patterns 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_nested_array_access_patterns 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_with_model_dump_fallback 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_nested_array_access_patterns 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_mixed_field_type_patterns 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_start_agent 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_mixed_field_type_patterns 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_performance_optimization_caching 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_start_agent 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_performance_optimization_caching 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_pattern_matching_performance 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_user_message 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_pattern_matching_performance 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_special_character_patterns 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_user_message 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_stop_agent 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_special_character_patterns 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_whitespace_handling_patterns 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_incremental 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_ha...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- [gw2][36m [ 16%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer_backup.py::TestClickHouseArraySyntaxFixer::test_edge_case_array_patterns
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
- INTERNALERROR> E             coverage.exceptions.DataError: Couldn't use data file 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\.coverage.Anthony.28428.XkPhpdTx.wgw1': no such table: file
- INTERNALERROR> E           assert False
- INTERNALERROR>
- INTERNALERROR> ..\..\..\..\miniconda3\Lib\site-packages\xdist\dsession.py:232: AssertionError
- [31mFAILED[0m app\tests\services\test_clickhouse_query_fixer_backup.py::[1mTestClickHouseArraySyntaxFixer::test_edge_case_array_patterns[0m - AssertionError: assert 'arrayElement(deep.array, i)' in 'SELECT arrayElement(nested.deep.array, i) FROM complex'
- [FAIL] TESTS FAILED with exit code 2 after 75.02s


---
*Generated by Netra AI Unified Test Runner v3.0*
