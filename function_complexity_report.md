
# FUNCTION COMPLEXITY REDUCTION REPORT
Generated: Function exceeding 8-line mandate analysis

## EXECUTIVE SUMMARY
This report identifies all functions exceeding the mandatory 8-line limit 
per CLAUDE.md specifications across critical system modules.


## VIOLATION SUMMARY
- **Total Functions Exceeding 8 Lines**: 1190
- **Critical Areas Affected**: 5

### Violations by Area:
- **core**: 588 functions
- **agents**: 251 functions
- **websocket**: 164 functions
- **database**: 115 functions
- **test_framework**: 72 functions

## DETAILED ANALYSIS

### TEST_FRAMEWORK AREA


#### `_discover_frontend_tests_into()` - 18 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 122-139 (18 lines)
- **Complexity Score**: 2.75
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_check_secondary_categories()` - 18 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 194-211 (18 lines)
- **Complexity Score**: 2.70
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_check_primary_categories()` - 13 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 180-192 (13 lines)
- **Complexity Score**: 2.25
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_print_markdown_selected_tests()` - 12 lines
- **File**: `test_runner.py`
- **Lines**: 178-189 (12 lines)
- **Complexity Score**: 2.15
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_add_failure_details()` - 13 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 112-124 (13 lines)
- **Complexity Score**: 2.15
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `handle_failing_test_commands()` - 13 lines
- **File**: `test_runner.py`
- **Lines**: 486-498 (13 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_discover_cypress_tests_into()` - 9 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 141-149 (9 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `apply_shard_filtering()` - 14 lines
- **File**: `test_runner.py`
- **Lines**: 547-560 (14 lines)
- **Complexity Score**: 2.00
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `save_additional_reports()` - 11 lines
- **File**: `test_runner.py`
- **Lines**: 652-662 (11 lines)
- **Complexity Score**: 1.95
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_print_text_test_levels()` - 14 lines
- **File**: `test_runner.py`
- **Lines**: 209-222 (14 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_discover_backend_tests_into()` - 13 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 108-120 (13 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_calculate_trend()` - 14 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 298-311 (14 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_print_text_selected_category()` - 10 lines
- **File**: `test_runner.py`
- **Lines**: 234-243 (10 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_add_broken_tests()` - 10 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 81-90 (10 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_add_fixed_tests()` - 10 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 92-101 (10 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_add_flaky_tests_and_links()` - 14 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 126-139 (14 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_add_component_breakdown()` - 13 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 185-197 (13 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_extract_component_failures()` - 12 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 285-296 (12 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_add_test_levels_to_json()` - 11 lines
- **File**: `test_runner.py`
- **Lines**: 114-124 (11 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_print_markdown_test_levels()` - 12 lines
- **File**: `test_runner.py`
- **Lines**: 155-166 (12 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_print_markdown_categories()` - 9 lines
- **File**: `test_runner.py`
- **Lines**: 168-176 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_print_text_categories()` - 9 lines
- **File**: `test_runner.py`
- **Lines**: 224-232 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `run_tests_with_configuration()` - 9 lines
- **File**: `test_runner.py`
- **Lines**: 519-527 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `execute_full_test_suite()` - 19 lines
- **File**: `test_runner.py`
- **Lines**: 617-635 (19 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `generate_coverage_report()` - 15 lines
- **File**: `test_runner.py`
- **Lines**: 678-692 (15 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_format_summary_table()` - 11 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 246-256 (11 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_get_all_failures()` - 9 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 275-283 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `configure_real_llm_if_requested()` - 10 lines
- **File**: `test_runner.py`
- **Lines**: 568-577 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `run_backend_tests()` - 11 lines
- **File**: `test_framework\runner.py`
- **Lines**: 95-105 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `run_frontend_tests()` - 11 lines
- **File**: `test_framework\runner.py`
- **Lines**: 107-117 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `run_e2e_tests()` - 11 lines
- **File**: `test_framework\runner.py`
- **Lines**: 119-129 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `save_test_report()` - 9 lines
- **File**: `test_framework\runner.py`
- **Lines**: 140-148 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_test_structure()` - 9 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 98-106 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_add_trends_table()` - 18 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 166-183 (18 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_categorize_test()` - 9 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 58-66 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `__init__()` - 48 lines
- **File**: `test_framework\runner.py`
- **Lines**: 46-93 (48 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_create_dashboard()` - 11 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 141-151 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_add_key_metrics()` - 11 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 214-224 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_create_json_structure()` - 12 lines
- **File**: `test_runner.py`
- **Lines**: 101-112 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_print_text_header()` - 9 lines
- **File**: `test_runner.py`
- **Lines**: 199-207 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_argument_parser()` - 9 lines
- **File**: `test_runner.py`
- **Lines**: 253-261 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_parser_epilog()` - 27 lines
- **File**: `test_runner.py`
- **Lines**: 263-289 (27 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `add_all_arguments()` - 10 lines
- **File**: `test_runner.py`
- **Lines**: 291-300 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `add_main_test_arguments()` - 10 lines
- **File**: `test_runner.py`
- **Lines**: 302-311 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `add_component_arguments()` - 10 lines
- **File**: `test_runner.py`
- **Lines**: 313-322 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `add_output_arguments()` - 11 lines
- **File**: `test_runner.py`
- **Lines**: 324-334 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `add_llm_arguments()` - 19 lines
- **File**: `test_runner.py`
- **Lines**: 336-354 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `add_staging_arguments()` - 12 lines
- **File**: `test_runner.py`
- **Lines**: 356-367 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `add_cicd_arguments()` - 9 lines
- **File**: `test_runner.py`
- **Lines**: 369-377 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `add_discovery_arguments()` - 15 lines
- **File**: `test_runner.py`
- **Lines**: 379-393 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `add_discovery_listing_arguments()` - 18 lines
- **File**: `test_runner.py`
- **Lines**: 395-412 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `add_failing_test_arguments()` - 22 lines
- **File**: `test_runner.py`
- **Lines**: 414-435 (22 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_failing_tests()` - 12 lines
- **File**: `test_runner.py`
- **Lines**: 500-511 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `run_level_based_tests()` - 9 lines
- **File**: `test_runner.py`
- **Lines**: 537-545 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `print_real_llm_configuration()` - 9 lines
- **File**: `test_runner.py`
- **Lines**: 579-587 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute_backend_only_tests()` - 9 lines
- **File**: `test_runner.py`
- **Lines**: 598-606 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `discover_tests()` - 10 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 18-27 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `discover_frontend_tests()` - 9 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 38-46 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `discover_e2e_tests()` - 9 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 48-56 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_test_categories()` - 9 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 68-76 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_tests_by_pattern()` - 9 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 83-91 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_critical_categories()` - 14 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 213-226 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_standard_categories()` - 19 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 228-246 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_specialized_categories()` - 44 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 248-291 (44 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_real_llm_categories()` - 16 lines
- **File**: `test_framework\test_discovery.py`
- **Lines**: 293-308 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_try_enhanced_report()` - 11 lines
- **File**: `test_framework\runner.py`
- **Lines**: 150-160 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_calculate_test_metrics()` - 10 lines
- **File**: `test_framework\runner.py`
- **Lines**: 171-180 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_unified_view()` - 12 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 49-60 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_dashboard_structure()` - 12 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 153-164 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_add_component_details()` - 14 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 199-212 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_add_quick_actions()` - 11 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 226-236 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_add_component_row()` - 16 lines
- **File**: `test_framework\unified_reporter.py`
- **Lines**: 258-273 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


### WEBSOCKET AREA


#### `cleanup_old_errors()` - 26 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 313-338 (26 lines)
- **Complexity Score**: 2.70
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `send_message()` - 34 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 266-299 (34 lines)
- **Complexity Score**: 2.20
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_remove_connection_from_room()` - 29 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 100-128 (29 lines)
- **Complexity Score**: 2.20
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_log_error()` - 30 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 162-191 (30 lines)
- **Complexity Score**: 2.05
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `check_memory_health()` - 42 lines
- **File**: `app\websocket\memory_manager.py`
- **Lines**: 252-293 (42 lines)
- **Complexity Score**: 2.05
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `remove_connection()` - 38 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 204-241 (38 lines)
- **Complexity Score**: 2.05
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_perform_cleanup()` - 40 lines
- **File**: `app\websocket\memory_manager.py`
- **Lines**: 160-199 (40 lines)
- **Complexity Score**: 2.00
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_and_flush_batches()` - 14 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 227-240 (14 lines)
- **Complexity Score**: 2.00
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_run_cleanup()` - 29 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 334-362 (29 lines)
- **Complexity Score**: 2.00
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_compress_data()` - 14 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 112-125 (14 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_decompress_data()` - 12 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 127-138 (12 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_apply_type_specific_recovery()` - 10 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 245-254 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `should_flush()` - 23 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 105-127 (23 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `add_message()` - 26 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 181-206 (26 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_update_metrics()` - 23 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 274-296 (23 lines)
- **Complexity Score**: 1.85
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_execute_recovery_strategies()` - 18 lines
- **File**: `app\websocket\recovery.py`
- **Lines**: 102-119 (18 lines)
- **Complexity Score**: 1.85
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_circuit_breaker_recovery()` - 22 lines
- **File**: `app\websocket\recovery.py`
- **Lines**: 146-167 (22 lines)
- **Complexity Score**: 1.85
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_run_heartbeat_monitoring()` - 15 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 196-210 (15 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_reconnection_loop()` - 11 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 128-138 (11 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `broadcast_message()` - 15 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 301-315 (15 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_user_connections()` - 12 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 382-393 (12 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `add_message_to_buffer()` - 22 lines
- **File**: `app\websocket\memory_manager.py`
- **Lines**: 57-78 (22 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_flush_batch()` - 26 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 242-267 (26 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_remove_connection()` - 25 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 207-231 (25 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `check_connection_sync()` - 21 lines
- **File**: `app\websocket\state_synchronizer.py`
- **Lines**: 87-107 (21 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `route_message()` - 9 lines
- **File**: `app\websocket\message_router.py`
- **Lines**: 39-47 (9 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_notify_sync_callbacks()` - 11 lines
- **File**: `app\websocket\state_synchronizer.py`
- **Lines**: 166-176 (11 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `update_broadcast_counters()` - 10 lines
- **File**: `app\websocket\broadcast_utils.py`
- **Lines**: 67-76 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `update_room_broadcast_counters()` - 10 lines
- **File**: `app\websocket\broadcast_utils.py`
- **Lines**: 89-98 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_notify_state_change()` - 10 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 281-290 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `delete_room()` - 20 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 42-61 (20 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `leave_all_rooms()` - 12 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 130-141 (12 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_perform_sync_check()` - 11 lines
- **File**: `app\websocket\state_synchronizer.py`
- **Lines**: 132-142 (11 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_attempt_error_recovery()` - 10 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 70-79 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_recover_heartbeat_error()` - 13 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 278-290 (13 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_connection_heartbeat_info()` - 15 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 436-450 (15 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_can_add_message()` - 12 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 92-103 (12 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_process_message_steps()` - 9 lines
- **File**: `app\websocket\message_handler_core.py`
- **Lines**: 114-122 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `handle_disconnect()` - 10 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 45-54 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `initiate_recovery()` - 36 lines
- **File**: `app\websocket\recovery.py`
- **Lines**: 65-100 (36 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_exponential_backoff_recovery()` - 17 lines
- **File**: `app\websocket\recovery.py`
- **Lines**: 128-144 (17 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `stop()` - 22 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 94-115 (22 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `handle_message()` - 22 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 243-264 (22 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_send_message()` - 13 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 269-281 (13 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `join_room()` - 24 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 63-86 (24 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `broadcast_to_user()` - 9 lines
- **File**: `app\websocket\batch_broadcast_manager.py`
- **Lines**: 35-43 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_accumulate_weighted_values()` - 11 lines
- **File**: `app\websocket\batch_load_monitor.py`
- **Lines**: 67-77 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_evaluate_and_flush_batch()` - 9 lines
- **File**: `app\websocket\batch_message_core.py`
- **Lines**: 114-122 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_broadcast_to_connections()` - 10 lines
- **File**: `app\websocket\broadcast_core.py`
- **Lines**: 102-111 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_broadcast_to_user_connections()` - 9 lines
- **File**: `app\websocket\broadcast_core.py`
- **Lines**: 149-157 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_broadcast_to_room_connections()` - 10 lines
- **File**: `app\websocket\broadcast_core.py`
- **Lines**: 189-198 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `benchmark_algorithms()` - 35 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 262-296 (35 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_cleanup_loop()` - 12 lines
- **File**: `app\websocket\memory_manager.py`
- **Lines**: 147-158 (12 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `get_memory_stats()` - 21 lines
- **File**: `app\websocket\memory_manager.py`
- **Lines**: 230-250 (21 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_flush_loop()` - 11 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 215-225 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_execute_callback()` - 9 lines
- **File**: `app\websocket\performance_monitor_alerts.py`
- **Lines**: 63-71 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_monitoring_loop()` - 10 lines
- **File**: `app\websocket\performance_monitor_core.py`
- **Lines**: 106-115 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_cleanup_loop()` - 11 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 322-332 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_close_all_connections()` - 13 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 364-376 (13 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `get_stats()` - 15 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 165-179 (15 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_sync_loop()` - 11 lines
- **File**: `app\websocket\state_synchronizer.py`
- **Lines**: 120-130 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_queue_message_to_connections()` - 11 lines
- **File**: `app\websocket\batch_message_core.py`
- **Lines**: 61-71 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_extract_pending_batch()` - 9 lines
- **File**: `app\websocket\batch_message_core.py`
- **Lines**: 139-147 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_batch_send()` - 9 lines
- **File**: `app\websocket\batch_message_core.py`
- **Lines**: 160-168 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `send_batch_to_connection()` - 10 lines
- **File**: `app\websocket\batch_message_operations.py`
- **Lines**: 18-27 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `broadcast_to_user()` - 17 lines
- **File**: `app\websocket\broadcast_core.py`
- **Lines**: 57-73 (17 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `broadcast_to_room()` - 17 lines
- **File**: `app\websocket\broadcast_core.py`
- **Lines**: 75-91 (17 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_send_to_room_connection()` - 10 lines
- **File**: `app\websocket\broadcast_core.py`
- **Lines**: 200-209 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_send_to_connection()` - 20 lines
- **File**: `app\websocket\broadcast_core.py`
- **Lines**: 230-249 (20 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `compress_message()` - 9 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 64-72 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `decompress_message()` - 28 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 74-101 (28 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_perform_compression()` - 10 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 222-231 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_evaluate_rate_limit_timing()` - 9 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 213-221 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_recover_connection_error()` - 9 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 262-270 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `start_heartbeat_for_connection()` - 11 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 44-54 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `stop_heartbeat_for_connection()` - 12 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 76-87 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `is_connection_alive()` - 12 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 141-152 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_report_loop_error()` - 9 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 256-264 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_check_pong_response()` - 9 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 293-301 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_report_timeout_error()` - 9 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 319-327 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_report_heartbeat_error()` - 9 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 344-352 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `stop_monitoring()` - 10 lines
- **File**: `app\websocket\memory_manager.py`
- **Lines**: 118-127 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_collect_garbage()` - 9 lines
- **File**: `app\websocket\memory_manager.py`
- **Lines**: 201-209 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `add_message()` - 13 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 78-90 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `start()` - 9 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 156-164 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `stop()` - 14 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 166-179 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_connection_batch_info()` - 18 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 317-334 (18 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_get_response_time_stats()` - 11 lines
- **File**: `app\websocket\performance_monitor_core.py`
- **Lines**: 230-240 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_state_sync_recovery()` - 15 lines
- **File**: `app\websocket\recovery.py`
- **Lines**: 169-183 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_recovery_status()` - 15 lines
- **File**: `app\websocket\recovery.py`
- **Lines**: 196-210 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `start()` - 11 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 82-92 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `create_room()` - 15 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 26-40 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `stop_monitoring()` - 10 lines
- **File**: `app\websocket\state_synchronizer.py`
- **Lines**: 60-69 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_send_to_single_connection()` - 9 lines
- **File**: `app\websocket\batch_broadcast_manager.py`
- **Lines**: 79-87 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_pending_message()` - 9 lines
- **File**: `app\websocket\batch_message_core.py`
- **Lines**: 91-99 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_core_metrics()` - 9 lines
- **File**: `app\websocket\batch_message_core.py`
- **Lines**: 250-258 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_process_batch_send()` - 12 lines
- **File**: `app\websocket\batch_message_operations.py`
- **Lines**: 30-41 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_batch_with_metrics()` - 10 lines
- **File**: `app\websocket\batch_message_operations.py`
- **Lines**: 44-53 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_handle_batch_send_error()` - 9 lines
- **File**: `app\websocket\batch_message_operations.py`
- **Lines**: 56-64 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_evaluate_strategy_condition()` - 11 lines
- **File**: `app\websocket\batch_message_strategies.py`
- **Lines**: 26-36 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 14 lines
- **File**: `app\websocket\broadcast_core.py`
- **Lines**: 25-38 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `broadcast_to_all()` - 16 lines
- **File**: `app\websocket\broadcast_core.py`
- **Lines**: 40-55 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `create_broadcast_result()` - 9 lines
- **File**: `app\websocket\broadcast_utils.py`
- **Lines**: 44-52 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_room_broadcast_result()` - 10 lines
- **File**: `app\websocket\broadcast_utils.py`
- **Lines**: 55-64 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 10 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 53-62 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_compression_stats()` - 31 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 140-170 (31 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `reset_stats()` - 11 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 172-182 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_uncompressed_result()` - 10 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 202-211 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_compressed_result()` - 13 lines
- **File**: `app\websocket\compression.py`
- **Lines**: 233-245 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 15 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 21-35 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `handle_connection_error()` - 31 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 81-111 (31 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `handle_validation_error()` - 24 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 113-136 (24 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `handle_rate_limit_error()` - 23 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 138-160 (23 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_error_stats()` - 12 lines
- **File**: `app\websocket\error_handler.py`
- **Lines**: 292-303 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 19 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 24-42 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `handle_pong()` - 10 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 113-122 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_heartbeat_loop()` - 14 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 177-190 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_send_ping()` - 14 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 271-284 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_handle_heartbeat_error()` - 10 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 329-338 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_stats()` - 11 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 405-415 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_base_stats()` - 10 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 417-426 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_connection_heartbeat_info()` - 13 lines
- **File**: `app\websocket\heartbeat_manager.py`
- **Lines**: 456-468 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_connection_memory_info()` - 11 lines
- **File**: `app\websocket\memory_manager.py`
- **Lines**: 85-95 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_collect_metrics()` - 18 lines
- **File**: `app\websocket\memory_manager.py`
- **Lines**: 211-228 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_batch_data()` - 10 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 133-142 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_stats()` - 13 lines
- **File**: `app\websocket\message_batcher.py`
- **Lines**: 298-310 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_default_stats()` - 9 lines
- **File**: `app\websocket\message_handler_core.py`
- **Lines**: 68-76 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `handle_message()` - 10 lines
- **File**: `app\websocket\message_handler_core.py`
- **Lines**: 78-87 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_try_process_message_with_fallback()` - 10 lines
- **File**: `app\websocket\message_handler_core.py`
- **Lines**: 97-106 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_send_error_response()` - 9 lines
- **File**: `app\websocket\message_handler_core.py`
- **Lines**: 291-299 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_alert()` - 11 lines
- **File**: `app\websocket\performance_monitor_alerts.py`
- **Lines**: 40-50 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_format_single_alert()` - 9 lines
- **File**: `app\websocket\performance_monitor_alerts.py`
- **Lines**: 143-151 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_trigger_response_time_alert()` - 9 lines
- **File**: `app\websocket\performance_monitor_core.py`
- **Lines**: 139-147 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_trigger_memory_alert()` - 9 lines
- **File**: `app\websocket\performance_monitor_core.py`
- **Lines**: 155-163 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_trigger_error_rate_alert()` - 9 lines
- **File**: `app\websocket\performance_monitor_core.py`
- **Lines**: 171-179 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_trigger_throughput_alert()` - 9 lines
- **File**: `app\websocket\performance_monitor_core.py`
- **Lines**: 187-195 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_trigger_cpu_alert()` - 9 lines
- **File**: `app\websocket\performance_monitor_core.py`
- **Lines**: 203-211 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_current_performance_summary()` - 12 lines
- **File**: `app\websocket\performance_monitor_core.py`
- **Lines**: 217-228 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_export_data()` - 9 lines
- **File**: `app\websocket\performance_monitor_core.py`
- **Lines**: 292-300 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\websocket\rate_limiter.py`
- **Lines**: 19-27 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `is_rate_limited()` - 10 lines
- **File**: `app\websocket\rate_limiter.py`
- **Lines**: 29-38 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_rate_limit_info()` - 10 lines
- **File**: `app\websocket\rate_limiter.py`
- **Lines**: 64-73 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `reset_rate_limit()` - 9 lines
- **File**: `app\websocket\rate_limiter.py`
- **Lines**: 114-122 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 10 lines
- **File**: `app\websocket\rate_limiter.py`
- **Lines**: 128-137 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `adjust_limit_for_connection()` - 9 lines
- **File**: `app\websocket\rate_limiter.py`
- **Lines**: 158-166 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_global_stats()` - 9 lines
- **File**: `app\websocket\reconnection_global.py`
- **Lines**: 35-43 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_calculate_global_stats()` - 10 lines
- **File**: `app\websocket\reconnection_global.py`
- **Lines**: 45-54 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 24-32 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_initialize_tracking_state()` - 10 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 34-43 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_attempt_connection()` - 11 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 177-187 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_handle_connection_failure()` - 9 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 208-216 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_calculate_backoff_delay()` - 10 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 248-257 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_status()` - 13 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 292-304 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_format_recent_attempts()` - 13 lines
- **File**: `app\websocket\reconnection_manager.py`
- **Lines**: 315-327 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 53 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 28-80 (53 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_execute_connection_addition()` - 11 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 125-135 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_health_status()` - 20 lines
- **File**: `app\websocket\reliable_connection_manager.py`
- **Lines**: 395-414 (20 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 16-24 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `leave_room()` - 11 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 88-98 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_room_connections()` - 10 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 143-152 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_connection_rooms()` - 10 lines
- **File**: `app\websocket\room_manager.py`
- **Lines**: 154-163 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `register_connection()` - 9 lines
- **File**: `app\websocket\state_synchronizer.py`
- **Lines**: 71-79 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_handle_state_desync()` - 12 lines
- **File**: `app\websocket\state_synchronizer.py`
- **Lines**: 144-155 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_sync_stats()` - 13 lines
- **File**: `app\websocket\state_synchronizer.py`
- **Lines**: 178-190 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


### DATABASE AREA


#### `setup_sync_engine_events()` - 29 lines
- **File**: `app\db\postgres_events.py`
- **Lines**: 84-112 (29 lines)
- **Complexity Score**: 3.10
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `setup_async_engine_events()` - 15 lines
- **File**: `app\db\postgres_events.py`
- **Lines**: 67-81 (15 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `get_cached_result()` - 40 lines
- **File**: `app\db\cache_retrieval.py`
- **Lines**: 64-103 (40 lines)
- **Complexity Score**: 2.00
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_single_database()` - 12 lines
- **File**: `app\db\health_checks.py`
- **Lines**: 112-123 (12 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `should_cache_query()` - 15 lines
- **File**: `app\db\cache_config.py`
- **Lines**: 213-227 (15 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `analyze_single_query()` - 41 lines
- **File**: `app\db\postgres_query_analyzer.py`
- **Lines**: 39-79 (41 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `cached_query()` - 20 lines
- **File**: `app\db\cache_core.py`
- **Lines**: 158-177 (20 lines)
- **Complexity Score**: 1.70
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `log_alert_by_severity()` - 11 lines
- **File**: `app\db\observability_alerts.py`
- **Lines**: 161-171 (11 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `add_performance_stats()` - 12 lines
- **File**: `app\db\cache_storage.py`
- **Lines**: 128-139 (12 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_avg_durations()` - 12 lines
- **File**: `app\db\cache_strategies.py`
- **Lines**: 200-211 (12 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_clickhouse_mode()` - 12 lines
- **File**: `app\db\clickhouse_init.py`
- **Lines**: 31-42 (12 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_async_database_url()` - 9 lines
- **File**: `app\db\testing.py`
- **Lines**: 7-15 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `is_result_cacheable()` - 11 lines
- **File**: `app\db\cache_config.py`
- **Lines**: 191-201 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `execute_with_cache_check()` - 22 lines
- **File**: `app\db\cache_core.py`
- **Lines**: 111-132 (22 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `update_pattern_tracking()` - 17 lines
- **File**: `app\db\cache_storage.py`
- **Lines**: 53-69 (17 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `cache_result()` - 41 lines
- **File**: `app\db\cache_storage.py`
- **Lines**: 72-112 (41 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `track_query_duration()` - 10 lines
- **File**: `app\db\cache_strategies.py`
- **Lines**: 181-190 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `start_background_tasks()` - 19 lines
- **File**: `app\db\cache_strategies.py`
- **Lines**: 229-247 (19 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_evaluate_merge_tree_optimization()` - 14 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 88-101 (14 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_database_url()` - 9 lines
- **File**: `app\db\migration_utils.py`
- **Lines**: 75-83 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_raw_connection()` - 12 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 31-42 (12 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_is_operational_error_retryable()` - 11 lines
- **File**: `app\db\transaction_errors.py`
- **Lines**: 43-53 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `is_retryable_error()` - 9 lines
- **File**: `app\db\transaction_errors.py`
- **Lines**: 56-64 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `run_cleanup_worker()` - 14 lines
- **File**: `app\db\cache_strategies.py`
- **Lines**: 117-130 (14 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `run_metrics_worker()` - 14 lines
- **File**: `app\db\cache_strategies.py`
- **Lines**: 154-167 (14 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `optimize_table_engines()` - 17 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 112-128 (17 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `create_materialized_views()` - 10 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 219-228 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `check_database_health()` - 10 lines
- **File**: `app\db\health_checks.py`
- **Lines**: 63-72 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `run_monitoring_cycle()` - 14 lines
- **File**: `app\db\observability_collectors.py`
- **Lines**: 201-214 (14 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_handle_creation_exception()` - 9 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 100-108 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_analyze_slow_queries()` - 9 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 241-249 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_parse_usage_stats_result()` - 9 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 283-291 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `generate_recommendations_from_queries()` - 9 lines
- **File**: `app\db\postgres_query_analyzer.py`
- **Lines**: 81-89 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_execute_database_query()` - 9 lines
- **File**: `app\db\query_execution_strategies.py`
- **Lines**: 78-86 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_calculate_transaction_durations_and_retries()` - 11 lines
- **File**: `app\db\transaction_stats.py`
- **Lines**: 39-49 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `calculate_adaptive_ttl()` - 25 lines
- **File**: `app\db\cache_config.py`
- **Lines**: 256-280 (25 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `cache_result()` - 21 lines
- **File**: `app\db\cache_core.py`
- **Lines**: 53-73 (21 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute_with_tags()` - 21 lines
- **File**: `app\db\cache_core.py`
- **Lines**: 135-155 (21 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `delete_tagged_keys()` - 9 lines
- **File**: `app\db\cache_retrieval.py`
- **Lines**: 116-124 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `invalidate_by_tag()` - 16 lines
- **File**: `app\db\cache_retrieval.py`
- **Lines**: 127-142 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `invalidate_pattern()` - 14 lines
- **File**: `app\db\cache_retrieval.py`
- **Lines**: 159-172 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `clear_all_cache()` - 18 lines
- **File**: `app\db\cache_retrieval.py`
- **Lines**: 175-192 (18 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `evict_lru_entries()` - 10 lines
- **File**: `app\db\cache_strategies.py`
- **Lines**: 20-29 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `create_single_view()` - 12 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 206-217 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `initialize_clickhouse_tables()` - 10 lines
- **File**: `app\db\clickhouse_init.py`
- **Lines**: 106-115 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `fix_clickhouse_array_syntax()` - 13 lines
- **File**: `app\db\clickhouse_query_fixer.py`
- **Lines**: 39-51 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `extract_where_conditions()` - 12 lines
- **File**: `app\db\index_optimizer_core.py`
- **Lines**: 73-84 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `calculate_rates()` - 10 lines
- **File**: `app\db\observability_collectors.py`
- **Lines**: 138-147 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `calculate_trends()` - 23 lines
- **File**: `app\db\observability_metrics.py`
- **Lines**: 145-167 (23 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `build_performance_summary()` - 24 lines
- **File**: `app\db\observability_metrics.py`
- **Lines**: 174-197 (24 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_index_creation()` - 11 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 75-85 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `create_single_index()` - 12 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 110-121 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `create_performance_indexes()` - 9 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 231-239 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_index_usage_stats()` - 11 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 301-311 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `close_async_db()` - 10 lines
- **File**: `app\db\postgres_pool.py`
- **Lines**: 59-68 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute()` - 9 lines
- **File**: `app\db\query_execution_strategies.py`
- **Lines**: 36-44 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_setup_transaction_metrics()` - 10 lines
- **File**: `app\db\transaction_core.py`
- **Lines**: 76-85 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_classify_operational_error()` - 9 lines
- **File**: `app\db\transaction_errors.py`
- **Lines**: 81-89 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_transaction_stats()` - 10 lines
- **File**: `app\db\transaction_stats.py`
- **Lines**: 62-71 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `to_dict()` - 12 lines
- **File**: `app\db\cache_config.py`
- **Lines**: 65-76 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `from_dict()` - 12 lines
- **File**: `app\db\cache_config.py`
- **Lines**: 79-90 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `generate_cache_key()` - 12 lines
- **File**: `app\db\cache_config.py`
- **Lines**: 134-145 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `normalize_query_pattern()` - 13 lines
- **File**: `app\db\cache_config.py`
- **Lines**: 152-164 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_cached_result()` - 9 lines
- **File**: `app\db\cache_core.py`
- **Lines**: 43-51 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_cache_entry()` - 11 lines
- **File**: `app\db\cache_storage.py`
- **Lines**: 23-33 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `build_metrics()` - 12 lines
- **File**: `app\db\cache_storage.py`
- **Lines**: 142-153 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `table_exists()` - 10 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 19-28 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_table_engine_info()` - 9 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 48-56 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_user_activity_view_sql()` - 16 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 145-160 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_performance_metrics_view_sql()` - 17 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 167-183 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_calculate_optimization_stats()` - 11 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 246-256 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_optimization_summary()` - 9 lines
- **File**: `app\db\clickhouse_index_optimizer.py`
- **Lines**: 258-266 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_test_workload_events_accessibility()` - 9 lines
- **File**: `app\db\clickhouse_init.py`
- **Lines**: 118-126 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_workload_events_table()` - 10 lines
- **File**: `app\db\clickhouse_init.py`
- **Lines**: 137-146 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_apply_llm_fixes()` - 9 lines
- **File**: `app\db\clickhouse_query_fixer.py`
- **Lines**: 117-125 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `health_check()` - 9 lines
- **File**: `app\db\client_clickhouse.py`
- **Lines**: 63-71 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `handle_session_transaction()` - 9 lines
- **File**: `app\db\client_postgres.py`
- **Lines**: 54-62 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_circuits_status()` - 11 lines
- **File**: `app\db\client_postgres.py`
- **Lines**: 235-245 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_run_postgres_optimizations()` - 15 lines
- **File**: `app\db\database_index_manager.py`
- **Lines**: 25-39 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_run_clickhouse_optimizations()` - 13 lines
- **File**: `app\db\database_index_manager.py`
- **Lines**: 41-53 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `run_all_optimizations()` - 17 lines
- **File**: `app\db\database_index_manager.py`
- **Lines**: 55-71 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `generate_optimization_report()` - 17 lines
- **File**: `app\db\database_index_manager.py`
- **Lines**: 97-113 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `optimize_all_databases()` - 13 lines
- **File**: `app\db\database_index_manager.py`
- **Lines**: 127-139 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_initialize_health_check_results()` - 9 lines
- **File**: `app\db\health_checks.py`
- **Lines**: 25-33 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `check_connection_pools()` - 16 lines
- **File**: `app\db\health_checks.py`
- **Lines**: 133-148 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `run_diagnostic_queries()` - 14 lines
- **File**: `app\db\health_checks.py`
- **Lines**: 150-163 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_content_corpus_schema()` - 14 lines
- **File**: `app\db\models_clickhouse.py`
- **Lines**: 45-58 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_llm_events_table_schema()` - 59 lines
- **File**: `app\db\models_clickhouse.py`
- **Lines**: 85-143 (59 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `create_connection_usage_alert()` - 9 lines
- **File**: `app\db\observability_alerts.py`
- **Lines**: 37-45 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_slow_query_alert()` - 9 lines
- **File**: `app\db\observability_alerts.py`
- **Lines**: 61-69 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_slow_query_rate_alert()` - 9 lines
- **File**: `app\db\observability_alerts.py`
- **Lines**: 72-80 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_cache_hit_rate_alert()` - 9 lines
- **File**: `app\db\observability_alerts.py`
- **Lines**: 109-117 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_active_transactions_alert()` - 9 lines
- **File**: `app\db\observability_alerts.py`
- **Lines**: 131-139 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `check_and_process_alerts()` - 12 lines
- **File**: `app\db\observability_alerts.py`
- **Lines**: 211-222 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `collect_connection_status()` - 14 lines
- **File**: `app\db\observability_collectors.py`
- **Lines**: 40-53 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `collect_comprehensive_metrics()` - 11 lines
- **File**: `app\db\observability_collectors.py`
- **Lines**: 171-181 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\db\observability_core.py`
- **Lines**: 26-34 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_database_dashboard()` - 17 lines
- **File**: `app\db\observability_core.py`
- **Lines**: 134-150 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `build_dashboard_data()` - 18 lines
- **File**: `app\db\observability_metrics.py`
- **Lines**: 200-217 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_configure_async_connection_timeouts()` - 10 lines
- **File**: `app\db\postgres_events.py`
- **Lines**: 32-41 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_index_query()` - 9 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 127-135 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `load_existing_indexes()` - 9 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 137-145 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_setup_performance_indexes()` - 23 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 177-199 (23 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_build_usage_stats_query()` - 12 lines
- **File**: `app\db\postgres_index_optimizer.py`
- **Lines**: 270-281 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_slow_queries()` - 15 lines
- **File**: `app\db\postgres_query_analyzer.py`
- **Lines**: 23-37 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_general_recommendations()` - 34 lines
- **File**: `app\db\postgres_query_analyzer.py`
- **Lines**: 95-128 (34 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_composite_index_recommendations()` - 22 lines
- **File**: `app\db\postgres_query_analyzer.py`
- **Lines**: 130-151 (22 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_async_db()` - 12 lines
- **File**: `app\db\postgres_session.py`
- **Lines**: 105-116 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute_with_timing()` - 9 lines
- **File**: `app\db\query_execution_strategies.py`
- **Lines**: 68-76 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_session()` - 9 lines
- **File**: `app\db\session.py`
- **Lines**: 40-48 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_db_session()` - 9 lines
- **File**: `app\db\session.py`
- **Lines**: 67-75 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_transaction_with_retry()` - 10 lines
- **File**: `app\db\transaction_core.py`
- **Lines**: 145-154 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `transaction()` - 15 lines
- **File**: `app\db\transaction_core.py`
- **Lines**: 157-171 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute_with_retry()` - 9 lines
- **File**: `app\db\transaction_core.py`
- **Lines**: 173-181 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `transactional()` - 10 lines
- **File**: `app\db\transaction_core.py`
- **Lines**: 205-214 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


### AGENTS AREA


#### `handle_agent_error()` - 37 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 286-322 (37 lines)
- **Complexity Score**: 2.40
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `validate_optimizations_result()` - 20 lines
- **File**: `app\agents\state.py`
- **Lines**: 146-165 (20 lines)
- **Complexity Score**: 2.35
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_create_optimizations_result()` - 31 lines
- **File**: `app\agents\optimizations_core_sub_agent.py`
- **Lines**: 181-211 (31 lines)
- **Complexity Score**: 2.25
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `decorator()` - 34 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 288-321 (34 lines)
- **Complexity Score**: 2.10
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `should_retry()` - 23 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 84-106 (23 lines)
- **Complexity Score**: 2.05
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `check_admin_command()` - 38 lines
- **File**: `app\agents\supervisor_admin_init.py`
- **Lines**: 126-163 (38 lines)
- **Complexity Score**: 2.00
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `execute_corpus_manager()` - 10 lines
- **File**: `app\agents\admin_tool_executors.py`
- **Lines**: 35-44 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_run_agent_specific_validation()` - 11 lines
- **File**: `app\agents\artifact_validator.py`
- **Lines**: 314-324 (11 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_determine_error_severity()` - 12 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 186-197 (12 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_log_error()` - 13 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 204-216 (13 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_sanitize_value()` - 10 lines
- **File**: `app\agents\tool_dispatcher_validation.py`
- **Lines**: 113-122 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_agent_input()` - 17 lines
- **File**: `app\agents\input_validation.py`
- **Lines**: 250-266 (17 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: MEDIUM


#### `extract_with_patterns()` - 9 lines
- **File**: `app\agents\utils_json_parsers.py`
- **Lines**: 132-140 (9 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_available_tools()` - 10 lines
- **File**: `app\agents\admin_tool_permissions.py`
- **Lines**: 67-76 (10 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_send_update()` - 24 lines
- **File**: `app\agents\agent_communication.py`
- **Lines**: 23-46 (24 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `wrapper()` - 31 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 289-319 (31 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_and_raise()` - 22 lines
- **File**: `app\agents\input_validation.py`
- **Lines**: 222-243 (22 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `attempt_recovery_iterations()` - 10 lines
- **File**: `app\agents\utils_json_extraction.py`
- **Lines**: 62-71 (10 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `execute_strategies()` - 12 lines
- **File**: `app\agents\utils_json_extraction.py`
- **Lines**: 122-133 (12 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_get_websocket_user_id()` - 11 lines
- **File**: `app\agents\agent_communication.py`
- **Lines**: 76-86 (11 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_triage_state()` - 12 lines
- **File**: `app\agents\input_validation.py`
- **Lines**: 34-45 (12 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_approval_requirements()` - 9 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 270-278 (9 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_tool_name()` - 14 lines
- **File**: `app\agents\tool_dispatcher_validation.py`
- **Lines**: 14-27 (14 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_run_id()` - 14 lines
- **File**: `app\agents\tool_dispatcher_validation.py`
- **Lines**: 73-86 (14 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `extract_partial_json()` - 13 lines
- **File**: `app\agents\utils_json_extraction.py`
- **Lines**: 145-157 (13 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `parse_simple_value()` - 9 lines
- **File**: `app\agents\utils_json_parsers.py`
- **Lines**: 56-64 (9 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `fix_unclosed_quotes()` - 9 lines
- **File**: `app\agents\utils_json_validators.py`
- **Lines**: 65-73 (9 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_log_validation_result()` - 10 lines
- **File**: `app\agents\artifact_validator.py`
- **Lines**: 296-305 (10 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_process_validation_errors()` - 15 lines
- **File**: `app\agents\input_validation.py`
- **Lines**: 196-210 (15 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_execute_by_type()` - 14 lines
- **File**: `app\agents\tool_dispatcher_execution.py`
- **Lines**: 55-68 (14 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_execute_tool_by_type()` - 11 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 109-119 (11 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `add_missing_commas_to_lines()` - 10 lines
- **File**: `app\agents\utils_json_validators.py`
- **Lines**: 53-62 (10 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_get_missing_permissions()` - 10 lines
- **File**: `app\agents\admin_tool_permissions.py`
- **Lines**: 122-131 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_post_run()` - 27 lines
- **File**: `app\agents\agent_lifecycle.py`
- **Lines**: 35-61 (27 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_validate_data_required_fields()` - 9 lines
- **File**: `app\agents\artifact_validator.py`
- **Lines**: 97-105 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_validate_data_quality()` - 9 lines
- **File**: `app\agents\artifact_validator.py`
- **Lines**: 107-115 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_error_stats()` - 29 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 251-279 (29 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_run_hooks()` - 9 lines
- **File**: `app\agents\supervisor_consolidated.py`
- **Lines**: 200-208 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_generate_batched_data()` - 27 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 88-114 (27 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_register_synthetic_tools()` - 10 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 22-31 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `sanitize_parameters()` - 12 lines
- **File**: `app\agents\tool_dispatcher_validation.py`
- **Lines**: 88-99 (12 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_sanitize_string()` - 11 lines
- **File**: `app\agents\tool_dispatcher_validation.py`
- **Lines**: 101-111 (11 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `apply_recovery_strategy()` - 10 lines
- **File**: `app\agents\utils_json_extraction.py`
- **Lines**: 85-94 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `extract_complex_field()` - 10 lines
- **File**: `app\agents\utils_json_parsers.py`
- **Lines**: 120-129 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_create_main_executor()` - 11 lines
- **File**: `app\agents\actions_to_meet_goals_sub_agent.py`
- **Lines**: 56-66 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `_create_fallback_executor()` - 9 lines
- **File**: `app\agents\actions_to_meet_goals_sub_agent.py`
- **Lines**: 68-76 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `validate_tool_access()` - 10 lines
- **File**: `app\agents\admin_tool_permissions.py`
- **Lines**: 82-91 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_handle_websocket_failure()` - 30 lines
- **File**: `app\agents\agent_communication.py`
- **Lines**: 88-117 (30 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_calculate_data_size()` - 11 lines
- **File**: `app\agents\agent_observability.py`
- **Lines**: 67-77 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `handle_error()` - 31 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 117-147 (31 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_synthetic_data_state()` - 10 lines
- **File**: `app\agents\input_validation.py`
- **Lines**: 115-124 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `decorator()` - 14 lines
- **File**: `app\agents\input_validation.py`
- **Lines**: 252-265 (14 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `_create_main_optimization_operation()` - 33 lines
- **File**: `app\agents\optimizations_core_sub_agent.py`
- **Lines**: 71-103 (33 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: MEDIUM


#### `_create_fallback_optimization_operation()` - 9 lines
- **File**: `app\agents\optimizations_core_sub_agent.py`
- **Lines**: 105-113 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `_execute_internal()` - 16 lines
- **File**: `app\agents\production_tool.py`
- **Lines**: 65-80 (16 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_execute_search_corpus()` - 14 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 72-85 (14 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_agent_output()` - 20 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 34-53 (20 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_apply_prompt_adjustments()` - 12 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 188-199 (12 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_apply_prompt_adjustments()` - 15 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 134-148 (15 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_extract_agent_output()` - 12 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 179-190 (12 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_handle_validation_result()` - 13 lines
- **File**: `app\agents\quality_supervisor.py`
- **Lines**: 111-123 (13 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_create_main_reporting_operation()` - 33 lines
- **File**: `app\agents\reporting_sub_agent.py`
- **Lines**: 76-108 (33 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: MEDIUM


#### `_create_fallback_reporting_operation()` - 9 lines
- **File**: `app\agents\reporting_sub_agent.py`
- **Lines**: 110-118 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `merge_from()` - 31 lines
- **File**: `app\agents\state.py`
- **Lines**: 205-235 (31 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `handle_admin_request()` - 35 lines
- **File**: `app\agents\supervisor_admin_init.py`
- **Lines**: 166-200 (35 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_admin_permissions()` - 9 lines
- **File**: `app\agents\supervisor_admin_init.py`
- **Lines**: 203-211 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `check_entry_conditions()` - 9 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 48-56 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_determine_workload_profile()` - 10 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 196-205 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_execute_internal()` - 16 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 187-202 (16 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_execute_search_corpus()` - 40 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 287-326 (40 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_parameters()` - 13 lines
- **File**: `app\agents\tool_dispatcher_validation.py`
- **Lines**: 29-41 (13 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_tool_result()` - 12 lines
- **File**: `app\agents\tool_dispatcher_validation.py`
- **Lines**: 48-59 (12 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_state_object()` - 11 lines
- **File**: `app\agents\tool_dispatcher_validation.py`
- **Lines**: 61-71 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `cleanup()` - 9 lines
- **File**: `app\agents\triage_sub_agent.py`
- **Lines**: 207-215 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `extract_json_from_response()` - 10 lines
- **File**: `app\agents\utils_json_extraction.py`
- **Lines**: 97-106 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_build_action_plan_from_partial()` - 9 lines
- **File**: `app\agents\actions_to_meet_goals_sub_agent.py`
- **Lines**: 230-238 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_collect_triage_validation_issues()` - 9 lines
- **File**: `app\agents\artifact_validator.py`
- **Lines**: 169-177 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_collect_data_validation_issues()` - 9 lines
- **File**: `app\agents\artifact_validator.py`
- **Lines**: 179-187 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_collect_optimization_validation_issues()` - 9 lines
- **File**: `app\agents\artifact_validator.py`
- **Lines**: 189-197 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_log_validation_result()` - 11 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 88-98 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `handle_validation_failure()` - 15 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 156-170 (15 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_update_validation_stats()` - 10 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 110-119 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_initialize_quality_services()` - 10 lines
- **File**: `app\agents\quality_supervisor.py`
- **Lines**: 58-67 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_failed_validation()` - 14 lines
- **File**: `app\agents\quality_supervisor.py`
- **Lines**: 137-150 (14 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `create_supervisor_with_admin_support()` - 33 lines
- **File**: `app\agents\supervisor_admin_init.py`
- **Lines**: 91-123 (33 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_generate_inference_logs()` - 13 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 175-187 (13 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_generate_performance_metrics()` - 12 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 189-200 (12 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_create_user()` - 14 lines
- **File**: `app\agents\admin_tool_executors.py`
- **Lines**: 117-130 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_grant_permission()` - 14 lines
- **File**: `app\agents\admin_tool_executors.py`
- **Lines**: 132-145 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_update_system_setting()` - 16 lines
- **File**: `app\agents\admin_tool_executors.py`
- **Lines**: 156-171 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `log_access_attempt()` - 10 lines
- **File**: `app\agents\admin_tool_permissions.py`
- **Lines**: 133-142 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_user_permissions_summary()` - 12 lines
- **File**: `app\agents\admin_tool_permissions.py`
- **Lines**: 151-162 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_pre_run()` - 15 lines
- **File**: `app\agents\agent_lifecycle.py`
- **Lines**: 19-33 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `run()` - 18 lines
- **File**: `app\agents\agent_lifecycle.py`
- **Lines**: 63-80 (18 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_entry_conditions()` - 9 lines
- **File**: `app\agents\agent_lifecycle.py`
- **Lines**: 82-90 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_send_entry_condition_warning()` - 14 lines
- **File**: `app\agents\agent_lifecycle.py`
- **Lines**: 92-105 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_send_error_notification()` - 14 lines
- **File**: `app\agents\agent_lifecycle.py`
- **Lines**: 118-131 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `set_state()` - 10 lines
- **File**: `app\agents\agent_state.py`
- **Lines**: 13-22 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_convert_to_agent_error()` - 17 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 149-165 (17 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `validate_reporting_state()` - 10 lines
- **File**: `app\agents\input_validation.py`
- **Lines**: 98-107 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_update_corpus()` - 11 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 125-135 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_delete_corpus()` - 11 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 154-164 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_analyze_corpus()` - 11 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 180-190 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_validate_corpus()` - 12 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 228-239 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute()` - 10 lines
- **File**: `app\agents\production_tool_synthetic.py`
- **Lines**: 14-23 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_retry_with_quality_adjustments()` - 15 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 172-186 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_apply_fallback_response()` - 17 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 217-233 (17 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `fallback_generation_hook()` - 12 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 40-51 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `retry_with_quality_adjustments()` - 17 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 94-110 (17 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `apply_fallback_response()` - 15 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 161-175 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `quality_validation_hook()` - 12 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 55-66 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_perform_validation()` - 15 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 68-82 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `quality_monitoring_hook()` - 12 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 141-152 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `quality_retry_hook()` - 9 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 214-222 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_should_retry_based_on_quality()` - 14 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 231-244 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_quality_dashboard()` - 12 lines
- **File**: `app\agents\quality_supervisor.py`
- **Lines**: 173-184 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `shutdown()` - 9 lines
- **File**: `app\agents\quality_supervisor.py`
- **Lines**: 208-216 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_validate_command_type()` - 11 lines
- **File**: `app\agents\supervisor_admin_init.py`
- **Lines**: 225-235 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute()` - 14 lines
- **File**: `app\agents\supervisor_consolidated.py`
- **Lines**: 119-132 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_generate_batch()` - 20 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 120-139 (20 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_is_admin_request()` - 9 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 58-66 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute()` - 26 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 75-100 (26 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_approval_flow()` - 16 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 115-130 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_send_generation_update()` - 10 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 150-159 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_send_completion_update()` - 12 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 161-172 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_generation_error()` - 14 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 181-194 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_parse_custom_profile()` - 35 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 216-250 (35 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `cleanup()` - 16 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 334-349 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `dispatch_tool()` - 13 lines
- **File**: `app\agents\tool_dispatcher_core.py`
- **Lines**: 71-83 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `dispatch_tool()` - 13 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 76-88 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_try_synthetic_tools()` - 10 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 204-213 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_try_corpus_tools()` - 15 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 215-229 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_update_corpus()` - 21 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 363-383 (21 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_delete_corpus()` - 19 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 385-403 (19 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_analyze_corpus()` - 19 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 405-423 (19 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_validate_corpus()` - 20 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 447-466 (20 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `try_recovery_with_closing()` - 9 lines
- **File**: `app\agents\utils_json_extraction.py`
- **Lines**: 74-82 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `try_close_truncated_array()` - 13 lines
- **File**: `app\agents\utils_json_parsers.py`
- **Lines**: 96-108 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute()` - 12 lines
- **File**: `app\agents\actions_to_meet_goals_sub_agent.py`
- **Lines**: 43-54 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_llm_response()` - 24 lines
- **File**: `app\agents\actions_to_meet_goals_sub_agent.py`
- **Lines**: 94-117 (24 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_base_action_plan_structure()` - 12 lines
- **File**: `app\agents\actions_to_meet_goals_sub_agent.py`
- **Lines**: 240-251 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_default_cost_benefit()` - 10 lines
- **File**: `app\agents\actions_to_meet_goals_sub_agent.py`
- **Lines**: 262-271 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_corpus()` - 13 lines
- **File**: `app\agents\admin_tool_executors.py`
- **Lines**: 46-58 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_generate_synthetic_data()` - 14 lines
- **File**: `app\agents\admin_tool_executors.py`
- **Lines**: 85-98 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_system_settings()` - 12 lines
- **File**: `app\agents\admin_tool_executors.py`
- **Lines**: 173-184 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_analyze_logs()` - 19 lines
- **File**: `app\agents\admin_tool_executors.py`
- **Lines**: 195-213 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_recent_logs()` - 19 lines
- **File**: `app\agents\admin_tool_executors.py`
- **Lines**: 215-233 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_permission_map()` - 9 lines
- **File**: `app\agents\admin_tool_permissions.py`
- **Lines**: 37-45 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_permission_check()` - 12 lines
- **File**: `app\agents\admin_tool_permissions.py`
- **Lines**: 98-109 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_required_permissions()` - 10 lines
- **File**: `app\agents\admin_tool_permissions.py`
- **Lines**: 111-120 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_attempt_websocket_update()` - 27 lines
- **File**: `app\agents\agent_communication.py`
- **Lines**: 48-74 (27 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_failure_result()` - 10 lines
- **File**: `app\agents\agent_observability.py`
- **Lines**: 19-28 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_success_result()` - 10 lines
- **File**: `app\agents\agent_observability.py`
- **Lines**: 30-39 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_valid_transitions()` - 9 lines
- **File**: `app\agents\agent_state.py`
- **Lines**: 36-44 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 13 lines
- **File**: `app\agents\base_agent.py`
- **Lines**: 32-44 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `from_env()` - 17 lines
- **File**: `app\agents\config.py`
- **Lines**: 66-82 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_recovery_delay()` - 18 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 64-81 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_category_mapping()` - 13 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 167-179 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_retry_with_delay()` - 17 lines
- **File**: `app\agents\error_handler.py`
- **Lines**: 233-249 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `validate_execution_input()` - 18 lines
- **File**: `app\agents\input_validation.py`
- **Lines**: 144-161 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `wrapper()` - 11 lines
- **File**: `app\agents\input_validation.py`
- **Lines**: 253-263 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 18 lines
- **File**: `app\agents\optimizations_core_sub_agent.py`
- **Lines**: 30-47 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute()` - 17 lines
- **File**: `app\agents\optimizations_core_sub_agent.py`
- **Lines**: 53-69 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_execute_optimization()` - 30 lines
- **File**: `app\agents\optimizations_core_sub_agent.py`
- **Lines**: 73-102 (30 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_default_fallback_result()` - 15 lines
- **File**: `app\agents\optimizations_core_sub_agent.py`
- **Lines**: 148-162 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute()` - 11 lines
- **File**: `app\agents\production_tool.py`
- **Lines**: 36-46 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_corpus_tool_mapping()` - 12 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 20-31 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_create_corpus()` - 9 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 33-41 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_corpus()` - 10 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 43-52 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_search_success_response()` - 11 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 104-114 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_export_corpus()` - 10 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 206-215 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_import_corpus()` - 10 lines
- **File**: `app\agents\production_tool_corpus.py`
- **Lines**: 217-226 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_synthetic_data_batch()` - 9 lines
- **File**: `app\agents\production_tool_synthetic.py`
- **Lines**: 25-33 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_store_synthetic_data()` - 9 lines
- **File**: `app\agents\production_tool_synthetic.py`
- **Lines**: 89-97 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 12 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 21-32 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_perform_validation()` - 13 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 55-67 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_validation_context()` - 10 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 69-78 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_output_extractor()` - 10 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 118-127 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_content_type_for_agent()` - 10 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 135-144 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_fallback_context()` - 17 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 235-251 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_output_updater()` - 10 lines
- **File**: `app\agents\quality_checks.py`
- **Lines**: 273-282 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_generate_error_fallback()` - 16 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 53-68 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_error_fallback_context()` - 14 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 70-83 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_retry_with_adjustments()` - 13 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 120-132 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_generate_quality_fallback()` - 17 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 177-193 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_quality_fallback_context()` - 15 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 195-209 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_apply_quality_fallback_response()` - 10 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 211-220 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_agent_update_map()` - 9 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 230-238 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_content_type_for_agent()` - 10 lines
- **File**: `app\agents\quality_fallback.py`
- **Lines**: 246-255 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_init_stats()` - 9 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 45-53 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_validate_content()` - 14 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 84-97 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_validation_context()` - 10 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 99-108 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_record_quality_event()` - 16 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 162-177 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_agent_output_map()` - 10 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 192-201 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_content_type_for_agent()` - 10 lines
- **File**: `app\agents\quality_hooks.py`
- **Lines**: 203-212 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 16 lines
- **File**: `app\agents\quality_supervisor.py`
- **Lines**: 41-56 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_configuration()` - 11 lines
- **File**: `app\agents\quality_supervisor.py`
- **Lines**: 230-240 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 18 lines
- **File**: `app\agents\reporting_sub_agent.py`
- **Lines**: 31-48 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute()` - 17 lines
- **File**: `app\agents\reporting_sub_agent.py`
- **Lines**: 58-74 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_execute_reporting()` - 30 lines
- **File**: `app\agents\reporting_sub_agent.py`
- **Lines**: 78-107 (30 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_build_reporting_prompt()` - 9 lines
- **File**: `app\agents\reporting_sub_agent.py`
- **Lines**: 128-136 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_default_fallback_report()` - 16 lines
- **File**: `app\agents\reporting_sub_agent.py`
- **Lines**: 155-170 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_report_result()` - 9 lines
- **File**: `app\agents\reporting_sub_agent.py`
- **Lines**: 189-197 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `clear_sensitive_data()` - 13 lines
- **File**: `app\agents\state.py`
- **Lines**: 191-203 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_supervisor_instance()` - 19 lines
- **File**: `app\agents\supervisor_admin_init.py`
- **Lines**: 70-88 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_agent_mapping()` - 9 lines
- **File**: `app\agents\supervisor_admin_init.py`
- **Lines**: 214-222 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_admin_request()` - 15 lines
- **File**: `app\agents\supervisor_admin_init.py`
- **Lines**: 238-252 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 10 lines
- **File**: `app\agents\supervisor_consolidated.py`
- **Lines**: 40-49 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_init_components()` - 15 lines
- **File**: `app\agents\supervisor_consolidated.py`
- **Lines**: 68-82 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_init_hooks()` - 9 lines
- **File**: `app\agents\supervisor_consolidated.py`
- **Lines**: 84-92 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `run()` - 13 lines
- **File**: `app\agents\supervisor_consolidated.py`
- **Lines**: 134-146 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `generate_data()` - 23 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 52-74 (23 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_generate_via_tool()` - 14 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 141-154 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_tool_params()` - 9 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 156-164 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_generate_generic_records()` - 10 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 202-211 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_progress_message()` - 12 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 306-317 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_success_result()` - 19 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 319-337 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_error_result()` - 10 lines
- **File**: `app\agents\synthetic_data_generator.py`
- **Lines**: 339-348 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_ecommerce_preset()` - 10 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 40-49 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_ecommerce_params()` - 9 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 51-59 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_financial_preset()` - 10 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 61-70 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_financial_params()` - 9 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 72-80 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_healthcare_preset()` - 10 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 82-91 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_healthcare_params()` - 9 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 93-101 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_gaming_preset()` - 10 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 103-112 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_gaming_params()` - 9 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 114-122 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_research_preset()` - 10 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 124-133 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_research_params()` - 9 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 135-143 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_all_presets()` - 9 lines
- **File**: `app\agents\synthetic_data_presets.py`
- **Lines**: 145-153 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 38-46 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_generation()` - 17 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 132-148 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_parsing_prompt()` - 9 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 252-260 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_approval_result()` - 9 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 301-309 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_send_approval_update()` - 11 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 311-321 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_error_result()` - 10 lines
- **File**: `app\agents\synthetic_data_sub_agent.py`
- **Lines**: 323-332 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_tool_with_error_handling()` - 10 lines
- **File**: `app\agents\tool_dispatcher_core.py`
- **Lines**: 97-106 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_tool_by_type()` - 9 lines
- **File**: `app\agents\tool_dispatcher_core.py`
- **Lines**: 108-116 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute_with_state()` - 14 lines
- **File**: `app\agents\tool_dispatcher_execution.py`
- **Lines**: 40-53 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_error_response()` - 9 lines
- **File**: `app\agents\tool_dispatcher_execution.py`
- **Lines**: 79-87 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_tool_with_error_handling()` - 10 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 98-107 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute()` - 11 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 158-168 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_synthetic_data_batch()` - 22 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 231-252 (22 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_execute_create_corpus()` - 32 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 254-285 (32 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_execute_validate_synthetic_data()` - 16 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 328-343 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_execute_store_synthetic_data()` - 17 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 345-361 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_execute_export_corpus()` - 10 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 425-434 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_import_corpus()` - 10 lines
- **File**: `app\agents\tool_dispatcher_old.py`
- **Lines**: 436-445 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `try_extraction_strategies()` - 11 lines
- **File**: `app\agents\utils_json_extraction.py`
- **Lines**: 109-119 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `try_parse_complex_value()` - 12 lines
- **File**: `app\agents\utils_json_parsers.py`
- **Lines**: 67-78 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `fix_common_json_errors()` - 10 lines
- **File**: `app\agents\utils_json_validators.py`
- **Lines**: 76-85 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `find_json_boundaries()` - 9 lines
- **File**: `app\agents\utils_json_validators.py`
- **Lines**: 139-147 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


### CORE AREA


#### `_validate_llm_config()` - 42 lines
- **File**: `app\core\config_validator.py`
- **Lines**: 105-146 (42 lines)
- **Complexity Score**: 3.15
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `validate_input_data()` - 27 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 394-420 (27 lines)
- **Complexity Score**: 2.90
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `shutdown_all()` - 37 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 71-107 (37 lines)
- **Complexity Score**: 2.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_validate_database_config()` - 36 lines
- **File**: `app\core\config_validator.py`
- **Lines**: 40-75 (36 lines)
- **Complexity Score**: 2.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `decorator()` - 24 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 396-419 (24 lines)
- **Complexity Score**: 2.60
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_validate_auth_config()` - 27 lines
- **File**: `app\core\config_validator.py`
- **Lines**: 77-103 (27 lines)
- **Complexity Score**: 2.55
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_validate_external_services()` - 23 lines
- **File**: `app\core\config_validator.py`
- **Lines**: 148-170 (23 lines)
- **Complexity Score**: 2.55
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `execute()` - 50 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 255-304 (50 lines)
- **Complexity Score**: 2.55
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_calculate_target_degradation_level()` - 29 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 405-433 (29 lines)
- **Complexity Score**: 2.50
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `recover()` - 37 lines
- **File**: `app\core\agent_recovery_base.py`
- **Lines**: 54-90 (37 lines)
- **Complexity Score**: 2.35
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `recover()` - 37 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 101-137 (37 lines)
- **Complexity Score**: 2.35
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_process_received_message()` - 36 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 265-300 (36 lines)
- **Complexity Score**: 2.35
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `wrapper()` - 22 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 397-418 (22 lines)
- **Complexity Score**: 2.30
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_load_from_environment()` - 53 lines
- **File**: `app\core\secret_manager.py`
- **Lines**: 182-234 (53 lines)
- **Complexity Score**: 2.30
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `execute_recovery()` - 38 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 197-234 (38 lines)
- **Complexity Score**: 2.25
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `check_and_recover()` - 38 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 441-478 (38 lines)
- **Complexity Score**: 2.25
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `register()` - 30 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 26-55 (30 lines)
- **Complexity Score**: 2.25
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `handle_exception()` - 34 lines
- **File**: `app\core\error_handlers.py`
- **Lines**: 62-95 (34 lines)
- **Complexity Score**: 2.20
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_adapt_failure_threshold()` - 26 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 237-262 (26 lines)
- **Complexity Score**: 2.15
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_health_check_loop()` - 25 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 308-332 (25 lines)
- **Complexity Score**: 2.15
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_heartbeat_loop()` - 41 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 430-470 (41 lines)
- **Complexity Score**: 2.15
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_record_success()` - 20 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 200-219 (20 lines)
- **Complexity Score**: 2.10
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_get_pool_metrics()` - 34 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 116-149 (34 lines)
- **Complexity Score**: 2.10
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_log_error()` - 17 lines
- **File**: `app\core\error_handlers.py`
- **Lines**: 236-252 (17 lines)
- **Complexity Score**: 2.10
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_filter_value()` - 12 lines
- **File**: `app\core\logging_formatters.py`
- **Lines**: 107-118 (12 lines)
- **Complexity Score**: 2.10
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_calculate_pressure_level()` - 12 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 480-491 (12 lines)
- **Complexity Score**: 2.10
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_categorize_data_failure()` - 10 lines
- **File**: `app\core\agent_recovery_data.py`
- **Lines**: 36-45 (10 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_categorize_triage_failure()` - 10 lines
- **File**: `app\core\agent_recovery_strategies.py`
- **Lines**: 26-35 (10 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_categorize_data_failure()` - 10 lines
- **File**: `app\core\agent_recovery_strategies.py`
- **Lines**: 121-130 (10 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `assess_failure()` - 27 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 164-190 (27 lines)
- **Complexity Score**: 2.05
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `assess_failure()` - 28 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 251-278 (28 lines)
- **Complexity Score**: 2.05
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `assess_failure()` - 28 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 350-377 (28 lines)
- **Complexity Score**: 2.05
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_categorize_triage_failure()` - 10 lines
- **File**: `app\core\agent_recovery_triage.py`
- **Lines**: 27-36 (10 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_validate_context()` - 13 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 323-335 (13 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `create_strategy()` - 16 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 253-268 (16 lines)
- **Complexity Score**: 2.05
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `default()` - 11 lines
- **File**: `app\core\json_utils.py`
- **Lines**: 21-31 (11 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_convert_datetime_fields()` - 11 lines
- **File**: `app\core\json_utils.py`
- **Lines**: 75-85 (11 lines)
- **Complexity Score**: 2.05
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `_check_agent_performance()` - 35 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 124-158 (35 lines)
- **Complexity Score**: 2.05
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: HIGH


#### `execute()` - 39 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 185-223 (39 lines)
- **Complexity Score**: 2.00
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `restore_original_sizes()` - 15 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 310-324 (15 lines)
- **Complexity Score**: 2.00
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `clear_expired()` - 15 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 114-128 (15 lines)
- **Complexity Score**: 2.00
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_registry()` - 36 lines
- **File**: `app\core\agent_recovery_registry.py`
- **Lines**: 140-175 (36 lines)
- **Complexity Score**: 1.95
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `mark_backup_code_used()` - 25 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 468-492 (25 lines)
- **Complexity Score**: 1.95
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_record_failure()` - 15 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 221-235 (15 lines)
- **Complexity Score**: 1.95
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `calculate_health_status_from_score()` - 10 lines
- **File**: `app\core\agent_health_checker.py`
- **Lines**: 57-66 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `determine_system_status()` - 10 lines
- **File**: `app\core\agent_health_checker.py`
- **Lines**: 69-78 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_classify_error_severity()` - 30 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 176-205 (30 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_log_error()` - 21 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 207-227 (21 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_calculate_base_delay()` - 10 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 68-77 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_apply_jitter()` - 11 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 79-89 (11 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_calculate_health_level()` - 10 lines
- **File**: `app\core\fallback_coordinator_health.py`
- **Lines**: 152-161 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `ensure_agent_response_is_json()` - 15 lines
- **File**: `app\core\json_parsing_utils.py`
- **Lines**: 224-238 (15 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_determine_cache_ttl()` - 12 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 198-209 (12 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_get_performance_category()` - 10 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 194-203 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `should_allow_request()` - 15 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 184-198 (15 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `circuit_breaker()` - 11 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 414-424 (11 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `with_health_check()` - 14 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 427-440 (14 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `_setup_default_recovery_actions()` - 10 lines
- **File**: `app\core\alert_manager.py`
- **Lines**: 182-191 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `with_timeout()` - 9 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 28-36 (9 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `with_retry()` - 15 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 39-53 (15 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `circuit_breaker()` - 10 lines
- **File**: `app\core\circuit_breaker_registry_adaptive.py`
- **Lines**: 104-113 (10 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `with_health_check()` - 11 lines
- **File**: `app\core\circuit_breaker_registry_adaptive.py`
- **Lines**: 116-126 (11 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `circuit_breaker_sync()` - 12 lines
- **File**: `app\core\circuit_breaker_registry_adaptive.py`
- **Lines**: 129-140 (12 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `_sanitize_input()` - 21 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 301-321 (21 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `should_retry()` - 20 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 110-129 (20 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `should_retry()` - 18 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 135-152 (18 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_validate_access()` - 21 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 266-286 (21 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_build_trend_message_parts()` - 12 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 206-217 (12 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_get_trend_message_parts()` - 14 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 204-217 (14 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `is_origin_allowed()` - 17 lines
- **File**: `app\core\middleware_setup.py`
- **Lines**: 113-129 (17 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get()` - 24 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 58-81 (24 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_agent_health_details()` - 42 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 205-246 (42 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_normalize_backend_type()` - 11 lines
- **File**: `app\core\type_validation_rules.py`
- **Lines**: 40-50 (11 lines)
- **Complexity Score**: 1.90
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_generate_type_suggestion()` - 16 lines
- **File**: `app\core\type_validation_rules.py`
- **Lines**: 164-179 (16 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `disconnect()` - 28 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 172-199 (28 lines)
- **Complexity Score**: 1.90
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `should_allow_request()` - 9 lines
- **File**: `app\core\adaptive_circuit_breaker_core.py`
- **Lines**: 86-94 (9 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_determine_recovery_action()` - 12 lines
- **File**: `app\core\alert_manager.py`
- **Lines**: 169-180 (12 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `can_execute()` - 11 lines
- **File**: `app\core\circuit_breaker_core.py`
- **Lines**: 37-47 (11 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_determine_health_status()` - 9 lines
- **File**: `app\core\database_health_monitoring.py`
- **Lines**: 114-122 (9 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_detect_threats()` - 15 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 269-283 (15 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_user_sms_codes()` - 14 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 494-507 (14 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `degrade_to_level()` - 16 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 84-99 (16 lines)
- **Complexity Score**: 1.85
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `degrade_to_level()` - 14 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 159-172 (14 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `degrade_to_level()` - 16 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 234-249 (16 lines)
- **Complexity Score**: 1.85
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `comprehensive_json_fix()` - 9 lines
- **File**: `app\core\json_parsing_utils.py`
- **Lines**: 157-165 (9 lines)
- **Complexity Score**: 1.85
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `startup()` - 20 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 184-203 (20 lines)
- **Complexity Score**: 1.85
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `shutdown()` - 28 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 205-232 (28 lines)
- **Complexity Score**: 1.85
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `create_agent_checker()` - 30 lines
- **File**: `app\core\agent_health_checker.py`
- **Lines**: 25-54 (30 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_error_summary()` - 25 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 385-409 (25 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `execute_recovery()` - 25 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 251-275 (25 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_all_pools()` - 24 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 418-441 (24 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_attempt_recovery()` - 31 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 443-473 (31 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `should_retry()` - 17 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 199-215 (17 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `exponential_backoff_retry()` - 35 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 471-505 (35 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `evaluate_pattern()` - 15 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 34-48 (15 lines)
- **Complexity Score**: 1.80
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `evaluate_pattern()` - 19 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 91-109 (19 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_execute_compensation()` - 18 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 355-372 (18 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `add_to_batch()` - 24 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 264-287 (24 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `load_secrets()` - 43 lines
- **File**: `app\core\secret_manager.py`
- **Lines**: 41-83 (43 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `generate_validation_report()` - 22 lines
- **File**: `app\core\type_validation_errors.py`
- **Lines**: 27-48 (22 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `strict_types()` - 19 lines
- **File**: `app\core\type_validators.py`
- **Lines**: 60-78 (19 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_reconnection_loop()` - 40 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 350-389 (40 lines)
- **Complexity Score**: 1.80
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_determine_health_status()` - 15 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 151-165 (15 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_input()` - 43 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 197-239 (43 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_encoding()` - 21 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 247-267 (21 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `should_retry()` - 16 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 163-178 (16 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `invalidate_user_sms_code()` - 19 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 426-444 (19 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `should_retry()` - 14 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 146-159 (14 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `execute_with_coordination()` - 51 lines
- **File**: `app\core\fallback_coordinator.py`
- **Lines**: 83-133 (51 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `reset_agent_status()` - 27 lines
- **File**: `app\core\fallback_coordinator.py`
- **Lines**: 139-165 (27 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_calculate_global_degradation_level()` - 21 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 435-455 (21 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_try_json_parse()` - 36 lines
- **File**: `app\core\json_parsing_utils.py`
- **Lines**: 22-57 (36 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `parse_string_list_field()` - 9 lines
- **File**: `app\core\json_parsing_utils.py`
- **Lines**: 98-106 (9 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_parse_string_to_string_list()` - 14 lines
- **File**: `app\core\json_parsing_utils.py`
- **Lines**: 109-122 (14 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `set()` - 23 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 83-105 (23 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `execute_with_cache()` - 33 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 159-191 (33 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_create_wrapped_operation()` - 11 lines
- **File**: `app\core\reliability.py`
- **Lines**: 109-119 (11 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `log_critical_failures()` - 14 lines
- **File**: `app\core\secret_manager_helpers.py`
- **Lines**: 63-76 (14 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_extract_complex_field_type()` - 9 lines
- **File**: `app\core\type_validation_helpers.py`
- **Lines**: 139-147 (9 lines)
- **Complexity Score**: 1.75
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_determine_mismatch_severity()` - 17 lines
- **File**: `app\core\type_validation_rules.py`
- **Lines**: 119-135 (17 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `connect()` - 45 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 126-170 (45 lines)
- **Complexity Score**: 1.75
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `check_health()` - 37 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 84-120 (37 lines)
- **Complexity Score**: 1.70
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `convert_legacy_result()` - 16 lines
- **File**: `app\core\agent_health_checker.py`
- **Lines**: 81-96 (16 lines)
- **Complexity Score**: 1.70
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_notify_callbacks()` - 10 lines
- **File**: `app\core\alert_manager.py`
- **Lines**: 107-116 (10 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_determine_threshold_severity()` - 9 lines
- **File**: `app\core\alert_manager.py`
- **Lines**: 159-167 (9 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_can_execute()` - 9 lines
- **File**: `app\core\circuit_breaker_core.py`
- **Lines**: 108-116 (9 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_create_result_from_check()` - 10 lines
- **File**: `app\core\circuit_breaker_health_checkers.py`
- **Lines**: 113-122 (10 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `create_secret_manager()` - 12 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 529-540 (12 lines)
- **Complexity Score**: 1.70
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `execute()` - 39 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 107-145 (39 lines)
- **Complexity Score**: 1.70
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `perform_health_checks()` - 32 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 300-331 (32 lines)
- **Complexity Score**: 1.70
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_fetch_secret()` - 17 lines
- **File**: `app\core\secret_manager.py`
- **Lines**: 164-180 (17 lines)
- **Complexity Score**: 1.70
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_adapt_based_on_response_time()` - 9 lines
- **File**: `app\core\adaptive_circuit_breaker_core.py`
- **Lines**: 156-164 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_retry_with_backoff()` - 25 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 56-80 (25 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_and_update_state()` - 10 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 122-131 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `record_failure()` - 14 lines
- **File**: `app\core\circuit_breaker_core.py`
- **Lines**: 60-73 (14 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_execute_recovery_strategies()` - 11 lines
- **File**: `app\core\database_connection_manager.py`
- **Lines**: 136-146 (11 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_get_total_connections()` - 10 lines
- **File**: `app\core\database_health_monitoring.py`
- **Lines**: 84-93 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_get_active_connections()` - 10 lines
- **File**: `app\core\database_health_monitoring.py`
- **Lines**: 95-104 (10 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `record_retry_attempt()` - 16 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 339-354 (16 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_load_production_secrets()` - 25 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 136-160 (25 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_load_staging_secrets()` - 22 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 162-183 (22 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `check_and_degrade_services()` - 14 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 334-347 (14 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `dispatch()` - 21 lines
- **File**: `app\core\middleware_setup.py`
- **Lines**: 135-155 (21 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_periodic_cleanup()` - 12 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 347-358 (12 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `execute_with_retry()` - 16 lines
- **File**: `app\core\reliability_retry.py`
- **Lines**: 38-53 (16 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_register_signal_handlers()` - 13 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 135-147 (13 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `__init__()` - 22 lines
- **File**: `app\core\secret_manager.py`
- **Lines**: 18-39 (22 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_validate_frontend_schemas()` - 12 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 51-62 (12 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_missing_frontend_fields()` - 13 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 79-91 (13 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_field_type_compatibility()` - 15 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 94-108 (15 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_check_extra_frontend_fields()` - 13 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 111-123 (13 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_group_mismatches_by_severity()` - 9 lines
- **File**: `app\core\type_validation_errors.py`
- **Lines**: 51-59 (9 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_is_critical_mismatch()` - 13 lines
- **File**: `app\core\type_validation_rules.py`
- **Lines**: 138-150 (13 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `send_message()` - 26 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 201-226 (26 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_handle_connection_error()` - 15 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 324-338 (15 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_restore_pending_messages()` - 21 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 391-411 (21 lines)
- **Complexity Score**: 1.65
- **Issues**: Very Long, Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `recover_all_connections()` - 14 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 536-549 (14 lines)
- **Complexity Score**: 1.65
- **Issues**: Nested Functions, Contains Loops, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_should_attempt_reset()` - 14 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 264-277 (14 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_analyze_error_message()` - 19 lines
- **File**: `app\core\agent_recovery_base.py`
- **Lines**: 123-141 (19 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_attempt_operation_recovery()` - 24 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 229-252 (24 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_calculate_overall_health()` - 16 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 359-374 (16 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_attempt_recovery()` - 12 lines
- **File**: `app\core\alert_manager.py`
- **Lines**: 118-129 (12 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `setup_root_endpoint()` - 9 lines
- **File**: `app\core\app_factory.py`
- **Lines**: 154-162 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `acquire()` - 17 lines
- **File**: `app\core\async_connection_pool.py`
- **Lines**: 74-90 (17 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `shutdown()` - 12 lines
- **File**: `app\core\async_resource_manager.py`
- **Lines**: 144-155 (12 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `decorator()` - 9 lines
- **File**: `app\core\circuit_breaker_registry_adaptive.py`
- **Lines**: 131-139 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `_try_recovery_strategy()` - 9 lines
- **File**: `app\core\database_connection_manager.py`
- **Lines**: 148-156 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_pool_status()` - 22 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 485-506 (22 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_validate_url()` - 13 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 344-356 (13 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_validate_filename()` - 14 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 358-371 (14 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_handle_retryable_exception()` - 16 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 433-448 (16 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_secret()` - 35 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 230-264 (35 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_user_credentials()` - 27 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 361-387 (27 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_user_sms_verification_code()` - 21 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 404-424 (21 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `get_user_backup_codes()` - 21 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 446-466 (21 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_calculate_growth_rate()` - 11 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 136-146 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_calculate_acceleration()` - 11 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 165-175 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_detect_spike()` - 13 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 198-210 (13 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `with_error_context()` - 10 lines
- **File**: `app\core\error_context.py`
- **Lines**: 219-228 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `_update_aggregation_components()` - 10 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 236-245 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_execute_recovery_strategy()` - 17 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 304-320 (17 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `restore_service()` - 17 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 370-386 (17 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `check_redis_health()` - 21 lines
- **File**: `app\core\health_checkers.py`
- **Lines**: 57-77 (21 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_fix_string_response_to_json()` - 33 lines
- **File**: `app\core\json_parsing_utils.py`
- **Lines**: 189-221 (33 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_create_async_wrapper()` - 17 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 114-130 (17 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: MEDIUM


#### `_create_sync_wrapper()` - 17 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 132-148 (17 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: MEDIUM


#### `should_log()` - 9 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 162-170 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `setup_interception()` - 10 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 194-203 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `can_apply()` - 10 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 96-105 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `can_apply()` - 14 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 170-183 (14 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_update_query_metrics()` - 14 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 211-224 (14 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_flush_batch()` - 23 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 289-311 (23 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_should_retry()` - 14 lines
- **File**: `app\core\reliability_retry.py`
- **Lines**: 86-99 (14 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `create_error_context_middleware()` - 9 lines
- **File**: `app\core\request_context.py`
- **Lines**: 48-56 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `create_request_logging_middleware()` - 11 lines
- **File**: `app\core\request_context.py`
- **Lines**: 71-81 (11 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `unregister()` - 9 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 61-69 (9 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `stop_monitoring()` - 12 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 275-286 (12 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `check_field_compatibility()` - 25 lines
- **File**: `app\core\type_validation_rules.py`
- **Lines**: 14-38 (25 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `validate_agent_execute_params()` - 10 lines
- **File**: `app\core\type_validators.py`
- **Lines**: 81-90 (10 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions

**Decomposition Priority**: MEDIUM


#### `validate()` - 14 lines
- **File**: `app\core\type_validators.py`
- **Lines**: 168-181 (14 lines)
- **Complexity Score**: 1.60
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `_send_message_now()` - 22 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 228-249 (22 lines)
- **Complexity Score**: 1.60
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: MEDIUM


#### `check_agent_health()` - 27 lines
- **File**: `app\core\agent_health_checker.py`
- **Lines**: 27-53 (27 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `batch_recover_operations()` - 29 lines
- **File**: `app\core\agent_recovery_registry.py`
- **Lines**: 110-138 (29 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_close_available_connections()` - 11 lines
- **File**: `app\core\async_connection_pool.py`
- **Lines**: 92-102 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_monitoring_loop()` - 11 lines
- **File**: `app\core\database_connection_manager.py`
- **Lines**: 90-100 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `check_pool_health()` - 39 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 76-114 (39 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_monitoring_loop()` - 11 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 406-416 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `validate_bulk()` - 10 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 381-390 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_create_fernet_from_env()` - 9 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 90-98 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_load_development_secrets()` - 19 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 185-203 (19 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_processing_loop()` - 10 lines
- **File**: `app\core\error_aggregation_core.py`
- **Lines**: 236-245 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_build_windows()` - 20 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 93-112 (20 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_processing_loop()` - 12 lines
- **File**: `app\core\error_aggregation_service.py`
- **Lines**: 79-90 (12 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_generate_windows()` - 14 lines
- **File**: `app\core\error_aggregation_utils.py`
- **Lines**: 203-216 (14 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_handle_pydantic_validation_error()` - 27 lines
- **File**: `app\core\error_handlers.py`
- **Lines**: 122-148 (27 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_check_with_event_loop()` - 9 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 191-199 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_find_caller_frame_static()` - 9 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 230-238 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_configure_specific_loggers()` - 11 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 249-259 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_monitoring_loop()` - 12 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 374-385 (12 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `setup_cors_middleware()` - 16 lines
- **File**: `app\core\middleware_setup.py`
- **Lines**: 64-79 (16 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_get_query_hash()` - 9 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 149-157 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `create_default_tool_result()` - 12 lines
- **File**: `app\core\reliability_utils.py`
- **Lines**: 42-53 (12 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_resource_info()` - 10 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 109-118 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_monitor_loop()` - 11 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 288-298 (11 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_process_secret_names()` - 9 lines
- **File**: `app\core\secret_manager.py`
- **Lines**: 129-137 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_monitoring_loop()` - 10 lines
- **File**: `app\core\system_health_monitor.py`
- **Lines**: 87-96 (10 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_check_agent_health()` - 33 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 90-122 (33 lines)
- **Complexity Score**: 1.50
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_validate_backend_schemas()` - 12 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 37-48 (12 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_create_severity_section()` - 13 lines
- **File**: `app\core\type_validation_errors.py`
- **Lines**: 72-84 (13 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `_parse_interfaces()` - 9 lines
- **File**: `app\core\type_validation_helpers.py`
- **Lines**: 49-57 (9 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `wrapper()` - 14 lines
- **File**: `app\core\type_validators.py`
- **Lines**: 64-77 (14 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_message_handler()` - 13 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 251-263 (13 lines)
- **Complexity Score**: 1.50
- **Issues**: Nested Functions, Contains Loops

**Decomposition Priority**: LOW


#### `call()` - 21 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 162-182 (21 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_breaker()` - 14 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 381-394 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `recover_agent_operation()` - 12 lines
- **File**: `app\core\agent_recovery_registry.py`
- **Lines**: 97-108 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `recover_agent_operation()` - 12 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 605-616 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute_with_reliability()` - 40 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 99-138 (40 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_record_failed_operation()` - 27 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 140-166 (27 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `perform_health_check()` - 14 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 422-435 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `process_items()` - 15 lines
- **File**: `app\core\async_batch_processor.py`
- **Lines**: 16-30 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_report_progress()` - 9 lines
- **File**: `app\core\async_batch_processor.py`
- **Lines**: 65-73 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `acquire()` - 10 lines
- **File**: `app\core\async_rate_limiter.py`
- **Lines**: 17-26 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `register_resource()` - 9 lines
- **File**: `app\core\async_resource_manager.py`
- **Lines**: 24-32 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `submit_task()` - 10 lines
- **File**: `app\core\async_resource_manager.py`
- **Lines**: 85-94 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `submit_background_task()` - 11 lines
- **File**: `app\core\async_resource_manager.py`
- **Lines**: 107-117 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `acquire()` - 14 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 228-241 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `record_success()` - 10 lines
- **File**: `app\core\circuit_breaker_core.py`
- **Lines**: 75-84 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute_recovery()` - 10 lines
- **File**: `app\core\database_recovery_core.py`
- **Lines**: 152-161 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute_recovery()` - 29 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 297-325 (29 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `register_pool()` - 16 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 369-384 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `stop_monitoring()` - 10 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 395-404 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `force_recovery()` - 9 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 475-483 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_strategy()` - 15 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 323-337 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_should_retry_exception()` - 10 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 372-381 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_log_retry_attempt()` - 12 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 390-401 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_get_from_secret_manager()` - 11 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 205-215 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_log_access()` - 14 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 288-301 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `rotate_secret()` - 21 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 307-327 (21 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_user_totp_secret()` - 14 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 389-402 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_invalidate_sms_code()` - 17 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 509-525 (17 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_evaluate_single_rule()` - 10 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 113-122 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_is_in_cooldown()` - 10 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 115-124 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_create_time_windows()` - 16 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 76-91 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_compute_slope()` - 16 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 148-163 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_detect_sustained_error()` - 12 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 216-227 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_project_future_occurrences()` - 13 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 229-241 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_project_future_occurrences()` - 11 lines
- **File**: `app\core\error_aggregation_trend.py`
- **Lines**: 104-114 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `create_time_windows()` - 10 lines
- **File**: `app\core\error_aggregation_utils.py`
- **Lines**: 179-188 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_sqlalchemy_error()` - 31 lines
- **File**: `app\core\error_handlers.py`
- **Lines**: 150-180 (31 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `netra_exception_handler()` - 19 lines
- **File**: `app\core\error_handlers.py`
- **Lines**: 309-327 (19 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_ensure_context()` - 10 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 66-75 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_error_patterns()` - 14 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 142-155 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_aggregate_error()` - 10 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 203-212 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_add_stack_trace_fingerprint()` - 11 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 291-301 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_prepare_log_data()` - 12 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 332-343 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `log_business_impact_context()` - 16 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 174-189 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `log_security_incident_context()` - 13 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 191-203 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_build_api_metadata()` - 13 lines
- **File**: `app\core\error_logging_helpers.py`
- **Lines**: 87-99 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute()` - 11 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 121-131 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `attempt_recovery()` - 12 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 280-291 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_check_circuit_breaker()` - 10 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 293-302 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_agent_recovery()` - 14 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 223-236 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_database_recovery()` - 14 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 248-261 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_execute_api_recovery()` - 13 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 263-275 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `generate_summary_report()` - 19 lines
- **File**: `app\core\error_report_generator.py`
- **Lines**: 20-38 (19 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `generate_detailed_report()` - 15 lines
- **File**: `app\core\error_report_generator.py`
- **Lines**: 76-90 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_add_frequency_recommendations()` - 10 lines
- **File**: `app\core\error_report_generator.py`
- **Lines**: 117-126 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_add_component_recommendations()` - 10 lines
- **File**: `app\core\error_report_generator.py`
- **Lines**: 128-137 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_add_severity_recommendations()` - 11 lines
- **File**: `app\core\error_report_generator.py`
- **Lines**: 139-149 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_add_user_impact_recommendations()` - 10 lines
- **File**: `app\core\error_report_generator.py`
- **Lines**: 151-160 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `register_agent()` - 33 lines
- **File**: `app\core\fallback_coordinator.py`
- **Lines**: 39-71 (33 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_system_status()` - 24 lines
- **File**: `app\core\fallback_coordinator_health.py`
- **Lines**: 163-186 (24 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `safe_websocket_send()` - 16 lines
- **File**: `app\core\fallback_utils.py`
- **Lines**: 48-63 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `can_restore_service()` - 14 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 101-114 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_use_cache_only()` - 13 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 126-138 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `can_restore_service()` - 13 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 174-186 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_use_smaller_model()` - 16 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 188-203 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `can_restore_service()` - 13 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 251-263 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_switch_to_polling()` - 11 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 277-287 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `degrade_service()` - 20 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 349-368 (20 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_degrade_service_if_needed()` - 16 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 388-403 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `check_postgres_health()` - 19 lines
- **File**: `app\core\health_checkers.py`
- **Lines**: 18-36 (19 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `delete()` - 10 lines
- **File**: `app\core\interfaces_repository.py`
- **Lines**: 142-151 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `prepare_websocket_message()` - 12 lines
- **File**: `app\core\json_utils.py`
- **Lines**: 54-65 (12 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `start_monitoring()` - 10 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 352-361 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `stop_monitoring()` - 10 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 363-372 (10 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `take_snapshot()` - 53 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 387-439 (53 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_memory_status()` - 16 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 493-508 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `setup_memory_recovery()` - 17 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 516-532 (17 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_get_staging_cors_origins()` - 14 lines
- **File**: `app\core\middleware_setup.py`
- **Lines**: 32-45 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_get_development_cors_origins()` - 14 lines
- **File**: `app\core\middleware_setup.py`
- **Lines**: 48-61 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `shutdown()` - 11 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 335-345 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `execute_safely()` - 19 lines
- **File**: `app\core\reliability.py`
- **Lines**: 47-65 (19 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_circuit_breaker_open()` - 14 lines
- **File**: `app\core\reliability.py`
- **Lines**: 67-80 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_operation_failure()` - 15 lines
- **File**: `app\core\reliability.py`
- **Lines**: 121-135 (15 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_calculate_health_score()` - 9 lines
- **File**: `app\core\reliability.py`
- **Lines**: 238-246 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `get_reliability_wrapper()` - 11 lines
- **File**: `app\core\reliability.py`
- **Lines**: 268-278 (11 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_execution_error()` - 13 lines
- **File**: `app\core\reliability_retry.py`
- **Lines**: 72-84 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_retry_delay()` - 16 lines
- **File**: `app\core\reliability_retry.py`
- **Lines**: 101-116 (16 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `is_healthy()` - 9 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 337-345 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_get_secret_client()` - 9 lines
- **File**: `app\core\secret_manager.py`
- **Lines**: 86-94 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `prepare_secrets_dict()` - 13 lines
- **File**: `app\core\secret_manager_helpers.py`
- **Lines**: 48-60 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_handle_alert_notification()` - 29 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 60-88 (29 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_check_agent_errors()` - 33 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 160-192 (33 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_validate_existing_frontend_schema()` - 9 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 144-152 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_create_mismatch_entry()` - 14 lines
- **File**: `app\core\type_validation_errors.py`
- **Lines**: 98-111 (14 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_validate_execute_state()` - 9 lines
- **File**: `app\core\type_validators.py`
- **Lines**: 93-101 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_validate_execute_run_id()` - 9 lines
- **File**: `app\core\type_validators.py`
- **Lines**: 104-112 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_validate_execute_stream_flag()` - 9 lines
- **File**: `app\core\type_validators.py`
- **Lines**: 115-123 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_configure_handlers()` - 13 lines
- **File**: `app\core\unified_logging.py`
- **Lines**: 60-72 (13 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_start_reconnection()` - 9 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 340-348 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `_stop_heartbeat()` - 9 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 420-428 (9 lines)
- **Complexity Score**: 1.45
- **Issues**: Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `create_connection()` - 18 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 509-526 (18 lines)
- **Complexity Score**: 1.45
- **Issues**: Very Long, Nested Functions, Complex Conditionals

**Decomposition Priority**: LOW


#### `check_health()` - 24 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 50-73 (24 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 35 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 126-160 (35 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_metrics()` - 17 lines
- **File**: `app\core\adaptive_circuit_breakers.py`
- **Lines**: 334-350 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\core\adaptive_circuit_breaker_core.py`
- **Lines**: 23-31 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_protected_operation()` - 12 lines
- **File**: `app\core\adaptive_circuit_breaker_core.py`
- **Lines**: 69-80 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_metrics_dict()` - 13 lines
- **File**: `app\core\adaptive_circuit_breaker_core.py`
- **Lines**: 255-267 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_trigger_manual_intervention()` - 20 lines
- **File**: `app\core\agent_recovery_base.py`
- **Lines**: 92-111 (20 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_default_assessment()` - 9 lines
- **File**: `app\core\agent_recovery_base.py`
- **Lines**: 113-121 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_register_default_strategies()` - 16 lines
- **File**: `app\core\agent_recovery_registry.py`
- **Lines**: 38-53 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_registry_status()` - 11 lines
- **File**: `app\core\agent_recovery_registry.py`
- **Lines**: 85-95 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute_degraded_mode()` - 10 lines
- **File**: `app\core\agent_recovery_strategies.py`
- **Lines**: 90-99 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_trigger_manual_intervention()` - 20 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 139-158 (20 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_primary_recovery()` - 21 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 192-212 (21 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_fallback_recovery()` - 18 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 214-231 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_degraded_mode()` - 13 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 233-245 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute_primary_recovery()` - 24 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 280-303 (24 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_fallback_recovery()` - 22 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 305-326 (22 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_degraded_mode()` - 17 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 328-344 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_primary_recovery()` - 20 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 379-398 (20 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_fallback_recovery()` - 19 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 400-418 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_degraded_mode()` - 12 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 420-431 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `assess_failure()` - 16 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 437-452 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_primary_recovery()` - 19 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 454-472 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_fallback_recovery()` - 16 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 474-489 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute_degraded_mode()` - 12 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 491-502 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_setup_default_configs()` - 53 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 517-569 (53 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_register_default_strategies()` - 16 lines
- **File**: `app\core\agent_recovery_strategies_original.py`
- **Lines**: 571-586 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `create_default_config()` - 58 lines
- **File**: `app\core\agent_recovery_types.py`
- **Lines**: 48-105 (58 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 28 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 54-81 (28 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_default_llm_recovery()` - 9 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 269-277 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_default_db_recovery()` - 9 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 279-287 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_default_api_recovery()` - 9 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 289-297 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_comprehensive_health_status()` - 36 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 299-334 (36 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `reset_health_metrics()` - 10 lines
- **File**: `app\core\agent_reliability_mixin.py`
- **Lines**: 411-420 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_status_change_alert()` - 13 lines
- **File**: `app\core\alert_manager.py`
- **Lines**: 44-56 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_threshold_alert()` - 13 lines
- **File**: `app\core\alert_manager.py`
- **Lines**: 58-70 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_log_alert()` - 10 lines
- **File**: `app\core\alert_manager.py`
- **Lines**: 96-105 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_alert_severity()` - 9 lines
- **File**: `app\core\alert_manager.py`
- **Lines**: 131-139 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `setup_middleware()` - 22 lines
- **File**: `app\core\app_factory.py`
- **Lines**: 46-67 (22 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_import_route_modules()` - 30 lines
- **File**: `app\core\app_factory.py`
- **Lines**: 87-116 (30 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_route_configurations()` - 27 lines
- **File**: `app\core\app_factory.py`
- **Lines**: 119-145 (27 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `create_app()` - 9 lines
- **File**: `app\core\app_factory.py`
- **Lines**: 165-173 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_batch_tasks()` - 11 lines
- **File**: `app\core\async_batch_processor.py`
- **Lines**: 39-49 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_process_batch()` - 13 lines
- **File**: `app\core\async_batch_processor.py`
- **Lines**: 51-63 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 12 lines
- **File**: `app\core\async_connection_pool.py`
- **Lines**: 16-27 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_task()` - 10 lines
- **File**: `app\core\async_resource_manager.py`
- **Lines**: 96-105 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_wait_for_task_completion()` - 9 lines
- **File**: `app\core\async_resource_manager.py`
- **Lines**: 167-175 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `run_in_threadpool()` - 9 lines
- **File**: `app\core\async_resource_manager.py`
- **Lines**: 194-202 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `async_timeout()` - 10 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 16-25 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 10 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 91-100 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `call()` - 12 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 109-120 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `circuit_info()` - 9 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 163-171 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `lock_info()` - 9 lines
- **File**: `app\core\async_retry_logic.py`
- **Lines**: 213-221 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_with_monitoring()` - 12 lines
- **File**: `app\core\circuit_breaker_core.py`
- **Lines**: 132-143 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_status_dict()` - 11 lines
- **File**: `app\core\circuit_breaker_core.py`
- **Lines**: 248-258 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_metrics_status()` - 9 lines
- **File**: `app\core\circuit_breaker_core.py`
- **Lines**: 274-282 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `check_health()` - 9 lines
- **File**: `app\core\circuit_breaker_health_checkers.py`
- **Lines**: 26-34 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_api_check()` - 9 lines
- **File**: `app\core\circuit_breaker_health_checkers.py`
- **Lines**: 36-44 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `validate_config()` - 15 lines
- **File**: `app\core\config_validator.py`
- **Lines**: 24-38 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_validation_report()` - 19 lines
- **File**: `app\core\config_validator.py`
- **Lines**: 172-190 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_build_pool_status()` - 12 lines
- **File**: `app\core\database_connection_manager.py`
- **Lines**: 172-183 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_all_status()` - 10 lines
- **File**: `app\core\database_connection_manager.py`
- **Lines**: 185-194 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute_recovery()` - 9 lines
- **File**: `app\core\database_recovery_core.py`
- **Lines**: 43-51 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_test_new_connections()` - 11 lines
- **File**: `app\core\database_recovery_core.py`
- **Lines**: 60-70 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute_recovery()` - 10 lines
- **File**: `app\core\database_recovery_core.py`
- **Lines**: 106-115 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_perform_failover()` - 14 lines
- **File**: `app\core\database_recovery_core.py`
- **Lines**: 171-184 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 18 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 335-352 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_setup_default_strategies()` - 9 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 354-362 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_all_status()` - 10 lines
- **File**: `app\core\database_recovery_strategies.py`
- **Lines**: 508-517 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_compile_patterns()` - 40 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 146-185 (40 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_max_length()` - 9 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 187-195 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_normalize_for_detection()` - 15 lines
- **File**: `app\core\enhanced_input_validation.py`
- **Lines**: 285-299 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_extract_error_pattern()` - 10 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 229-238 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_retry_metrics()` - 10 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 356-365 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_generator_with_metadata()` - 9 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 422-430 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_retry_attempt()` - 18 lines
- **File**: `app\core\enhanced_retry_strategies.py`
- **Lines**: 451-468 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 11 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 36-46 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_fernet_from_key()` - 11 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 78-88 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 14 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 112-125 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_register_secret()` - 12 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 217-228 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_security_metrics()` - 13 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 336-348 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `cleanup_access_log()` - 10 lines
- **File**: `app\core\enhanced_secret_manager.py`
- **Lines**: 350-359 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_high_error_rate_rule()` - 11 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 59-69 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_critical_spike_rule()` - 10 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 71-80 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_sustained_error_rule()` - 10 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 82-91 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_new_pattern_rule()` - 11 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 93-103 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_evaluate_rule_condition()` - 13 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 137-149 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_evaluation_context()` - 13 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 151-163 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_alert()` - 16 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 169-184 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_generate_alert_message()` - 10 lines
- **File**: `app\core\error_aggregation_alerts.py`
- **Lines**: 186-195 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\core\error_aggregation_core.py`
- **Lines**: 23-31 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `add_error()` - 9 lines
- **File**: `app\core\error_aggregation_core.py`
- **Lines**: 33-41 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_high_error_rate_rule()` - 11 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 40-50 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_critical_spike_rule()` - 10 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 52-61 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_sustained_errors_rule()` - 10 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 63-72 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_new_pattern_rule()` - 11 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 74-84 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_evaluate_rule_condition()` - 14 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 130-143 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_evaluation_context()` - 15 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 145-159 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_alert()` - 17 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 161-177 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_generate_alert_message()` - 11 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 179-189 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_base_message_parts()` - 12 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 191-202 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_system_status()` - 9 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 228-236 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_top_patterns_summary()` - 11 lines
- **File**: `app\core\error_aggregation_metrics.py`
- **Lines**: 245-255 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `analyze_pattern_trend()` - 24 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 28-51 (24 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_filter_pattern_history()` - 10 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 53-62 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_matches_pattern()` - 11 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 64-74 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_count_errors_in_window()` - 11 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 114-124 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_calculate_trend_metrics()` - 9 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 126-134 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_compute_second_derivative()` - 13 lines
- **File**: `app\core\error_aggregation_patterns.py`
- **Lines**: 177-189 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 11 lines
- **File**: `app\core\error_aggregation_service.py`
- **Lines**: 22-32 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `analyze_pattern_trend()` - 9 lines
- **File**: `app\core\error_aggregation_trend.py`
- **Lines**: 31-39 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_filter_pattern_history()` - 10 lines
- **File**: `app\core\error_aggregation_trend.py`
- **Lines**: 48-57 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_error_trend()` - 18 lines
- **File**: `app\core\error_aggregation_trend.py`
- **Lines**: 121-138 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_build_signature()` - 9 lines
- **File**: `app\core\error_aggregation_utils.py`
- **Lines**: 114-122 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_setup_window_config()` - 12 lines
- **File**: `app\core\error_aggregation_utils.py`
- **Lines**: 190-201 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_count_errors_in_window()` - 11 lines
- **File**: `app\core\error_aggregation_utils.py`
- **Lines**: 218-228 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\core\error_context.py`
- **Lines**: 135-143 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_handle_netra_exception()` - 24 lines
- **File**: `app\core\error_handlers.py`
- **Lines**: 97-120 (24 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_handle_http_exception()` - 31 lines
- **File**: `app\core\error_handlers.py`
- **Lines**: 182-212 (31 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_handle_unknown_exception()` - 21 lines
- **File**: `app\core\error_handlers.py`
- **Lines**: 214-234 (21 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_http_status_code()` - 33 lines
- **File**: `app\core\error_handlers.py`
- **Lines**: 254-286 (33 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `log_error()` - 19 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 46-64 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `log_recovery_attempt()` - 17 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 92-108 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `log_business_impact()` - 13 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 115-127 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `log_security_incident()` - 12 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 129-140 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_format_pattern()` - 11 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 166-176 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_metrics()` - 9 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 182-190 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_update_aggregation()` - 12 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 223-234 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_update_aggregation_severity()` - 10 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 247-256 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_update_aggregation_occurrences()` - 13 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 258-270 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_signature_components()` - 12 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 278-289 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_write_log()` - 14 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 353-366 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_write_log_level()` - 15 lines
- **File**: `app\core\error_logger_core.py`
- **Lines**: 368-382 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_context()` - 10 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 31-40 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_base_context()` - 10 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 42-51 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_prepare_context_data()` - 13 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 53-65 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_copy_parent_fields()` - 11 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 74-84 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_severity_mapping()` - 15 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 114-128 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_category_mapping()` - 12 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 130-141 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_code_mapping()` - 9 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 143-151 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `log_recovery_attempt()` - 12 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 161-172 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_recovery_context()` - 19 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 205-223 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_enhance_business_context()` - 14 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 225-238 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_enhance_security_context()` - 16 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 240-255 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_build_recovery_metadata()` - 15 lines
- **File**: `app\core\error_logging_context.py`
- **Lines**: 257-271 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `log_agent_error()` - 18 lines
- **File**: `app\core\error_logging_helpers.py`
- **Lines**: 13-30 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `log_database_error()` - 18 lines
- **File**: `app\core\error_logging_helpers.py`
- **Lines**: 33-50 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `log_api_error()` - 16 lines
- **File**: `app\core\error_logging_helpers.py`
- **Lines**: 53-68 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `execute()` - 11 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 94-104 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 172-180 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 239-247 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_setup_default_strategies()` - 12 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 249-260 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_retry()` - 12 lines
- **File**: `app\core\error_recovery.py`
- **Lines**: 342-353 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 23 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 34-56 (23 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `handle_agent_error()` - 13 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 58-70 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_agent_error_recovery()` - 9 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 72-80 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `handle_database_error()` - 13 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 82-94 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_prepare_database_error_data()` - 10 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 96-105 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_database_error_recovery()` - 9 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 107-115 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `handle_api_error()` - 14 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 117-130 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_prepare_api_error_data()` - 10 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 132-141 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_api_error_recovery()` - 9 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 143-151 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `handle_websocket_error()` - 18 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 153-170 (18 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_prepare_error_data()` - 11 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 193-203 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_base_error_data()` - 9 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 205-213 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_recovery_context()` - 9 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 238-246 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_api_recovery_context()` - 9 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 277-285 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_attempt_agent_degradation()` - 13 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 294-306 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_agent_type_mapping()` - 9 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 331-339 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_error_severity_mapping()` - 9 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 348-356 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `recover_agent_operation()` - 10 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 403-412 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `recover_database_operation()` - 10 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 415-424 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `recover_api_operation()` - 10 lines
- **File**: `app\core\error_recovery_integration.py`
- **Lines**: 427-436 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_calculate_summary_metrics()` - 16 lines
- **File**: `app\core\error_report_generator.py`
- **Lines**: 40-55 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_format_statistics()` - 10 lines
- **File**: `app\core\error_report_generator.py`
- **Lines**: 92-101 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_generate_recommendations()` - 13 lines
- **File**: `app\core\error_report_generator.py`
- **Lines**: 103-115 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 13 lines
- **File**: `app\core\fallback_coordinator.py`
- **Lines**: 25-37 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_default_fallback_config()` - 9 lines
- **File**: `app\core\fallback_coordinator.py`
- **Lines**: 73-81 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_init_emergency_responses()` - 23 lines
- **File**: `app\core\fallback_coordinator_emergency.py`
- **Lines**: 19-41 (23 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_add_emergency_metadata()` - 9 lines
- **File**: `app\core\fallback_coordinator_emergency.py`
- **Lines**: 54-62 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_basic_cascade_response()` - 10 lines
- **File**: `app\core\fallback_coordinator_emergency.py`
- **Lines**: 70-79 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_calculate_system_metrics()` - 11 lines
- **File**: `app\core\fallback_coordinator_health.py`
- **Lines**: 114-124 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_system_status()` - 11 lines
- **File**: `app\core\fallback_coordinator_health.py`
- **Lines**: 126-136 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `generate_fallback()` - 9 lines
- **File**: `app\core\fallback_handler.py`
- **Lines**: 29-37 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `execute_with_fallback()` - 16 lines
- **File**: `app\core\fallback_utils.py`
- **Lines**: 14-29 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `create_default_fallback_result()` - 10 lines
- **File**: `app\core\fallback_utils.py`
- **Lines**: 31-40 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_use_read_replica()` - 9 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 116-124 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_use_template_response()` - 11 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 205-215 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_reduce_message_frequency()` - 11 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 265-275 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 14 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 301-314 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `register_service()` - 17 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 316-332 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_get_resource_usage()` - 16 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 457-472 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_degradation_status()` - 14 lines
- **File**: `app\core\graceful_degradation.py`
- **Lines**: 474-487 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `check_clickhouse_health()` - 16 lines
- **File**: `app\core\health_checkers.py`
- **Lines**: 39-54 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `check_websocket_health()` - 25 lines
- **File**: `app\core\health_checkers.py`
- **Lines**: 80-104 (25 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `check_system_resources()` - 34 lines
- **File**: `app\core\health_checkers.py`
- **Lines**: 107-140 (34 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_create_failed_result()` - 9 lines
- **File**: `app\core\health_checkers.py`
- **Lines**: 153-161 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_disabled_result()` - 9 lines
- **File**: `app\core\health_checkers.py`
- **Lines**: 164-172 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_db_session()` - 11 lines
- **File**: `app\core\interfaces_repository.py`
- **Lines**: 32-42 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_multi()` - 12 lines
- **File**: `app\core\interfaces_repository.py`
- **Lines**: 95-106 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_unhealthy_service_health()` - 9 lines
- **File**: `app\core\interfaces_repository.py`
- **Lines**: 223-231 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_multi()` - 9 lines
- **File**: `app\core\interfaces_service.py`
- **Lines**: 69-77 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `serialize_for_websocket()` - 14 lines
- **File**: `app\core\json_utils.py`
- **Lines**: 34-47 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `safe_json_dumps()` - 12 lines
- **File**: `app\core\json_utils.py`
- **Lines**: 96-107 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `validate_json_serializable()` - 14 lines
- **File**: `app\core\json_utils.py`
- **Lines**: 115-128 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `log_api_call()` - 11 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 86-96 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `async_wrapper()` - 13 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 117-129 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `sync_wrapper()` - 13 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 135-147 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_emit_to_loguru()` - 10 lines
- **File**: `app\core\logging_context.py`
- **Lines**: 206-215 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_log_entry()` - 13 lines
- **File**: `app\core\logging_formatters.py`
- **Lines**: 146-158 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_add_json_console_handler()` - 11 lines
- **File**: `app\core\logging_formatters.py`
- **Lines**: 216-226 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_add_readable_console_handler()` - 11 lines
- **File**: `app\core\logging_formatters.py`
- **Lines**: 228-238 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `add_file_handler()` - 17 lines
- **File**: `app\core\logging_formatters.py`
- **Lines**: 240-256 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 15 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 330-344 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `emergency_memory_recovery()` - 10 lines
- **File**: `app\core\memory_recovery_strategies.py`
- **Lines**: 535-544 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_stats()` - 9 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 130-138 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_performance_report()` - 19 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 232-250 (19 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `get_performance_stats()` - 9 lines
- **File**: `app\core\performance_optimization_manager.py`
- **Lines**: 360-368 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 9 lines
- **File**: `app\core\reliability.py`
- **Lines**: 22-30 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_initialize_components()` - 9 lines
- **File**: `app\core\reliability.py`
- **Lines**: 32-40 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_operation_successfully()` - 12 lines
- **File**: `app\core\reliability.py`
- **Lines**: 82-93 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_with_protection()` - 13 lines
- **File**: `app\core\reliability.py`
- **Lines**: 95-107 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_attempt_fallback()` - 13 lines
- **File**: `app\core\reliability.py`
- **Lines**: 137-149 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_execute_fallback()` - 11 lines
- **File**: `app\core\reliability.py`
- **Lines**: 165-175 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_should_retry_error()` - 10 lines
- **File**: `app\core\reliability.py`
- **Lines**: 177-186 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_error_info()` - 9 lines
- **File**: `app\core\reliability.py`
- **Lines**: 194-202 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_health_status_dict()` - 14 lines
- **File**: `app\core\reliability.py`
- **Lines**: 215-228 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_system_health()` - 14 lines
- **File**: `app\core\reliability.py`
- **Lines**: 281-294 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_attempt_execution()` - 16 lines
- **File**: `app\core\reliability_retry.py`
- **Lines**: 55-70 (16 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_log_retry_attempt()` - 12 lines
- **File**: `app\core\reliability_retry.py`
- **Lines**: 118-129 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_agent_reliability_wrapper()` - 15 lines
- **File**: `app\core\reliability_utils.py`
- **Lines**: 8-22 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `create_tool_reliability_wrapper()` - 15 lines
- **File**: `app\core\reliability_utils.py`
- **Lines**: 25-39 (15 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 10 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 124-133 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `register_resource()` - 9 lines
- **File**: `app\core\resource_manager.py`
- **Lines**: 170-178 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_load_from_secret_manager()` - 10 lines
- **File**: `app\core\secret_manager.py`
- **Lines**: 96-105 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_fetch_individual_secret()` - 10 lines
- **File**: `app\core\secret_manager.py`
- **Lines**: 139-148 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_secret_names_list()` - 10 lines
- **File**: `app\core\secret_manager_helpers.py`
- **Lines**: 17-26 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_setup_alert_manager_integration()` - 14 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 45-58 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_comprehensive_health_report()` - 37 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 248-284 (37 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `start_monitoring()` - 11 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 286-296 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `stop_monitoring()` - 11 lines
- **File**: `app\core\system_health_monitor_enhanced.py`
- **Lines**: 298-308 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_validate_schema_fields()` - 12 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 65-76 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_perform_all_field_checks()` - 9 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 155-163 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_check_single_field_compatibility()` - 9 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 191-199 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_perform_validation_checks()` - 10 lines
- **File**: `app\core\type_validation_core.py`
- **Lines**: 226-235 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_severity_icon()` - 9 lines
- **File**: `app\core\type_validation_errors.py`
- **Lines**: 87-95 (9 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `parse_typescript_file()` - 12 lines
- **File**: `app\core\type_validation_helpers.py`
- **Lines**: 20-31 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_parse_typescript_content()` - 11 lines
- **File**: `app\core\type_validation_helpers.py`
- **Lines**: 105-115 (11 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_create_type_mismatch()` - 14 lines
- **File**: `app\core\type_validation_rules.py`
- **Lines**: 103-116 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_get_default_type_mappings()` - 14 lines
- **File**: `app\core\type_validation_rules.py`
- **Lines**: 182-195 (14 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_build_type_mismatch_object()` - 13 lines
- **File**: `app\core\type_validation_rules.py`
- **Lines**: 236-248 (13 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `_log_type_error()` - 10 lines
- **File**: `app\core\type_validators.py`
- **Lines**: 126-135 (10 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `__init__()` - 43 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 82-124 (43 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW


#### `_send_acknowledgment()` - 12 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 311-322 (12 lines)
- **Complexity Score**: 1.30
- **Issues**: Nested Functions

**Decomposition Priority**: LOW


#### `get_status()` - 17 lines
- **File**: `app\core\websocket_recovery_strategies.py`
- **Lines**: 482-498 (17 lines)
- **Complexity Score**: 1.30
- **Issues**: Very Long, Nested Functions

**Decomposition Priority**: LOW



## DECOMPOSITION STRATEGIES

### Immediate Actions Required:
1. **Extract Helper Functions**: Break out repeated logic patterns
2. **Apply Guard Clauses**: Reduce nesting with early returns
3. **Use Composition**: Split complex functions into smaller components
4. **Leverage Python Features**: Use comprehensions, map/filter where appropriate

### Refactoring Techniques by Pattern:

#### For Validation/Parsing Functions:
- Extract validation steps into separate functions
- Use validator pattern for complex checks
- Apply chain-of-responsibility for multi-step validation

#### For Data Processing Functions:
- Extract transformation steps
- Use functional programming patterns
- Apply pipeline pattern for multi-stage processing

#### For Connection/Session Management:
- Extract setup/teardown functions
- Use context managers for resource management
- Apply factory pattern for object creation

#### For Error Handling Functions:
- Extract error classification logic
- Use strategy pattern for different error types
- Apply command pattern for error recovery

### Performance Considerations:
- **Maintain Performance**: Ensure decomposition doesn't degrade performance
- **Measure Impact**: Profile before/after refactoring
- **Optimize Hot Paths**: Prioritize performance-critical functions

### Testing Strategy:
- **Unit Test Each Function**: Ensure every new function has tests
- **Maintain Coverage**: Don't lose test coverage during refactoring
- **Test Integration**: Verify composed functions work together

## IMPLEMENTATION PRIORITY

### Phase 1 (Immediate - High Complexity):
Functions with complexity score > 2.0 and >20 lines

### Phase 2 (Next Sprint - Medium Complexity):
Functions with complexity score 1.5-2.0 and >15 lines

### Phase 3 (Continuous - Low Complexity):
Remaining functions >8 lines for consistency

