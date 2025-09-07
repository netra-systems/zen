# Manager Consolidation MRO Analysis Report
Generated: 2025-09-04 12:34:04
Analysis Target: Top 5 Most Duplicated Manager Classes

## Executive Summary

This report analyzes the Method Resolution Order (MRO) and dependency patterns 
for the top 5 most duplicated Manager classes in the Netra codebase to support 
consolidation from 808 managers down to 24 (8 mega classes + 16 kept managers).

### Target Managers Analyzed:
1. MockWebSocketManager (24 occurrences)
2. MockLLMManager (9 occurrences) 
3. CircuitBreakerManager (6 occurrences)
4. RedisManager (5 occurrences)
5. SessionManager (5 occurrences)

## Analysis Results


## MockWebSocketManager Analysis

**Status:** No production implementations found

## MockLLMManager Analysis

**Status:** No production implementations found

## CircuitBreakerManager Analysis

**Implementations found:** 5

### Implementation 1: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\db\client_config.py
**Line:** 69
**Definition:** `class CircuitBreakerManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** CircuitBreakerManager -> object

#### Methods (0)

#### State Analysis
**Is Stateful:** No
**State Score:** 0 (higher = more stateful)
**Complexity Score:** 0
**Method Count:** 0
**Property Count:** 0

#### Dependencies (6 files import this)
- netra_backend\app\db\client_postgres.py
- netra_backend\app\db\client_postgres_health.py
- netra_backend\app\db\client_postgres_executors.py
- netra_backend\app\db\postgres_resilience.py
- netra_backend\app\db\client_postgres_session.py
- ... and 1 more files

#### Method Resolution Mapping
- `get_clickhouse_circuit` -> `CircuitBreakerManager`
- `get_postgres_circuit` -> `CircuitBreakerManager`
- `get_read_circuit` -> `CircuitBreakerManager`
- `get_write_circuit` -> `CircuitBreakerManager`

---

### Implementation 2: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\services\circuit_breaker.py
**Line:** 177
**Definition:** `class CircuitBreakerManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** CircuitBreakerManager -> object

#### Methods (5)
- `__init__(self)`
- `create_circuit_breaker(self, name, config)`
- `get_circuit_breaker(self, name)`
- `get_all_status(self)`
- `get_health_summary(self)`

#### State Analysis
**Is Stateful:** Yes
**State Score:** 10 (higher = more stateful)
**Complexity Score:** 10
**Method Count:** 5
**Property Count:** 0

#### Dependencies (7 files import this)
- tests\mission_critical\test_circuit_breaker_comprehensive.py
- tests\mission_critical\test_agent_resilience_patterns.py
- netra_backend\tests\integration\red_team\tier2_major_failures\test_circuit_breaker_state_management.py
- netra_backend\tests\integration\critical_paths\test_circuit_breaker_l4.py
- netra_backend\app\services\circuit_breaker\__init__.py
- ... and 2 more files

#### Method Resolution Mapping
- `call_with_circuit_breaker` -> `CircuitBreakerManager`
- `create_circuit_breaker` -> `CircuitBreakerManager`
- `get_all_status` -> `CircuitBreakerManager`
- `get_circuit_breaker` -> `CircuitBreakerManager`
- `get_health_summary` -> `CircuitBreakerManager`
- `reset_all` -> `CircuitBreakerManager`

---

### Implementation 3: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\services\api_gateway\circuit_breaker.py
**Line:** 71
**Definition:** `class CircuitBreakerManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** CircuitBreakerManager -> object

#### Methods (3)
- `__init__(self)`
- `get_circuit_breaker(self, endpoint, config)`
- `get_stats(self)`

#### State Analysis
**Is Stateful:** Yes
**State Score:** 10 (higher = more stateful)
**Complexity Score:** 6
**Method Count:** 3
**Property Count:** 0

#### Dependencies (2 files import this)
- netra_backend\app\services\synthetic_data\recovery.py
- netra_backend\app\services\api_gateway\__init__.py

#### Method Resolution Mapping
- `get_circuit_breaker` -> `CircuitBreakerManager`
- `get_stats` -> `CircuitBreakerManager`

---

### Implementation 4: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\services\api_gateway\circuit_breaker_manager.py
**Line:** 118
**Definition:** `class CircuitBreakerManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** CircuitBreakerManager -> object

#### Methods (1)
- `__init__(self)`

#### State Analysis
**Is Stateful:** Yes
**State Score:** 10 (higher = more stateful)
**Complexity Score:** 2
**Method Count:** 1
**Property Count:** 0

#### Dependencies (1 files import this)
- netra_backend\tests\integration\critical_paths\test_api_circuit_breaker_per_endpoint.py

#### Method Resolution Mapping
- `cleanup_inactive_circuits` -> `CircuitBreakerManager`
- `force_close` -> `CircuitBreakerManager`
- `force_open` -> `CircuitBreakerManager`
- `get_all_circuits` -> `CircuitBreakerManager`
- `get_circuit_state` -> `CircuitBreakerManager`
- `get_circuit_stats` -> `CircuitBreakerManager`
- `is_request_allowed` -> `CircuitBreakerManager`
- `record_failure` -> `CircuitBreakerManager`
- `record_success` -> `CircuitBreakerManager`
- `register_endpoint` -> `CircuitBreakerManager`

---

### Implementation 5: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\services\circuit_breaker\circuit_breaker_manager.py
**Line:** 44
**Definition:** `class CircuitBreakerManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** CircuitBreakerManager -> object

#### Methods (1)
- `__init__(self)`

#### State Analysis
**Is Stateful:** Yes
**State Score:** 10 (higher = more stateful)
**Complexity Score:** 2
**Method Count:** 1
**Property Count:** 0

#### Dependencies (2 files import this)
- netra_backend\tests\integration\critical_paths\test_circuit_breaker_l4.py
- netra_backend\app\services\circuit_breaker\__init__.py

#### Method Resolution Mapping
- `call_service` -> `CircuitBreakerManager`
- `force_close` -> `CircuitBreakerManager`
- `force_open` -> `CircuitBreakerManager`
- `get_all_states` -> `CircuitBreakerManager`
- `get_circuit_breaker_state` -> `CircuitBreakerManager`
- `get_health_summary` -> `CircuitBreakerManager`
- `register_service` -> `CircuitBreakerManager`
- `reset_all` -> `CircuitBreakerManager`
- `start` -> `CircuitBreakerManager`
- `stop` -> `CircuitBreakerManager`
- ... and 1 more methods

---


## RedisManager Analysis

**Implementations found:** 4

### Implementation 1: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\analytics_service\analytics_core\database\redis.py
**Line:** 23
**Definition:** `class RedisManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** RedisManager -> object

#### Methods (1)
- `__init__(self, url, max_connections)`

#### Properties (1)
- `@property redis`

#### State Analysis
**Is Stateful:** Yes
**State Score:** 15 (higher = more stateful)
**Complexity Score:** 3
**Method Count:** 1
**Property Count:** 1

#### Dependencies (1 files import this)
- analytics_service\analytics_core\services\event_processor.py

#### Method Resolution Mapping
- `add_hot_prompt` -> `RedisManager`
- `buffer_event` -> `RedisManager`
- `cache_report` -> `RedisManager`
- `check_rate_limit` -> `RedisManager`
- `cleanup_expired_keys` -> `RedisManager`
- `close` -> `RedisManager`
- `get_buffer_size` -> `RedisManager`
- `get_buffered_events` -> `RedisManager`
- `get_cached_report` -> `RedisManager`
- `get_hot_prompts` -> `RedisManager`
- ... and 9 more methods

---

### Implementation 2: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\analytics_service\analytics_core\database\redis_manager.py
**Line:** 40
**Definition:** `class RedisManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** RedisManager -> object

#### Methods (1)
- `__init__(self, host, port, db, password, max_connections, retry_on_timeout, socket_connect_timeout, socket_timeout, health_check_interval)`

#### Properties (2)
- `@property is_connected`
- `@property redis`

#### State Analysis
**Is Stateful:** Yes
**State Score:** 20 (higher = more stateful)
**Complexity Score:** 4
**Method Count:** 1
**Property Count:** 2

#### Dependencies (5 files import this)
- analytics_service\tests\integration\test_database_integration.py
- analytics_service\analytics_core\__init__.py
- analytics_service\analytics_core\database\connection.py
- analytics_service\tests\integration\test_event_pipeline.py
- analytics_service\tests\integration\run_integration_tests.py

#### Method Resolution Mapping
- `close` -> `RedisManager`
- `get_connection` -> `RedisManager`
- `get_info` -> `RedisManager`
- `initialize` -> `RedisManager`
- `is_healthy` -> `RedisManager`

---

### Implementation 3: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\redis_manager.py
**Line:** 15
**Definition:** `class RedisManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** RedisManager -> object

#### Methods (14)
- `__init__(self, test_mode)`
- `_namespace_key(self, user_id, key)`
- `reinitialize_configuration(self)`
- `_is_redis_disabled_by_flag(self)`
- `_get_redis_mode(self)`
- `_handle_redis_mode(self, redis_mode)`
- `_check_development_redis(self)`
- `_check_if_enabled(self)`
- `_check_redis_mode_and_development(self)`
- `_create_redis_builder(self)`
- ... and 4 more methods

#### State Analysis
**Is Stateful:** Yes
**State Score:** 10 (higher = more stateful)
**Complexity Score:** 28
**Method Count:** 14
**Property Count:** 0

#### Dependencies (142 files import this)
- netra_backend\tests\integration\critical_paths\test_auth_failover_scenarios_l4.py
- netra_backend\tests\unit\agents\test_base_agent_infrastructure.py
- netra_backend\app\startup_health_checks.py
- netra_backend\tests\test_startup_dependencies.py
- netra_backend\app\services\demo\demo_session_manager.py
- ... and 137 more files

#### Method Resolution Mapping
- `acquire_leader_lock` -> `RedisManager`
- `add_to_list` -> `RedisManager`
- `connect` -> `RedisManager`
- `delete` -> `RedisManager`
- `disconnect` -> `RedisManager`
- `exists` -> `RedisManager`
- `expire` -> `RedisManager`
- `get` -> `RedisManager`
- `get_client` -> `RedisManager`
- `get_list` -> `RedisManager`
- ... and 20 more methods

---

### Implementation 4: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\data_sub_agent\clickhouse_operations.py
**Line:** 52
**Definition:** `class RedisManagerProtocol(Protocol):`

---


## SessionManager Analysis

**Implementations found:** 6

### Implementation 1: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\auth_service\auth_core\core\session_manager.py
**Line:** 21
**Definition:** `class SessionManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** SessionManager -> object

#### Methods (14)
- `__init__(self)`
- `_connect_redis(self)`
- `create_session(self, user_or_user_id, user_data, session_id, client_ip, user_agent, fingerprint, device_id, session_timeout, force_create, user_id)`
- `delete_session(self, session_id)`
- `_store_session(self, session_id, session_data)`
- `_update_activity(self, session_id)`
- `_get_session_key(self, session_id)`
- `health_check(self)`
- `get_performance_stats(self)`
- `_enable_fallback_mode(self)`
- ... and 4 more methods

#### Properties (1)
- `@property redis_client`

#### State Analysis
**Is Stateful:** Yes
**State Score:** 18 (higher = more stateful)
**Complexity Score:** 29
**Method Count:** 14
**Property Count:** 1

#### Dependencies (10 files import this)
- auth_service\auth_core\unified_auth_interface.py
- auth_service\tests\test_auth_session_persistence_edge_cases.py
- auth_service\tests\test_refresh_token_fix.py
- auth_service\auth_core\services\auth_service.py
- auth_service\tests\test_redis_staging_connectivity_fixes.py
- ... and 5 more files

#### Method Resolution Mapping
- `async_health_check` -> `SessionManager`
- `cleanup` -> `SessionManager`
- `close_redis` -> `SessionManager`
- `create_session` -> `SessionManager`
- `create_session_async` -> `SessionManager`
- `delete_session` -> `SessionManager`
- `get_active_sessions` -> `SessionManager`
- `get_invalidation_history` -> `SessionManager`
- `get_performance_stats` -> `SessionManager`
- `get_session` -> `SessionManager`
- ... and 13 more methods

---

### Implementation 2: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\auth_integration\interfaces.py
**Line:** 81
**Definition:** `class SessionManagerProtocol(Protocol):`

---

### Implementation 3: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\database\session_manager.py
**Line:** 36
**Definition:** `class SessionManagerError(Exception):`

---

### Implementation 4: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\database\__init__.py
**Line:** 77
**Definition:** `class SessionManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** SessionManager -> object

#### Methods (2)
- `__init__(self)`
- `get_stats(self)`

#### State Analysis
**Is Stateful:** Yes
**State Score:** 10 (higher = more stateful)
**Complexity Score:** 4
**Method Count:** 2
**Property Count:** 0

#### Dependencies (155 files import this)
- netra_backend\tests\integration\test_chat_orchestrator_nacis_real_llm.py
- netra_backend\tests\mission_critical\test_actions_to_meet_goals_ssot_compliance.py
- netra_backend\app\agents\supply_researcher\agent.py
- netra_backend\tests\e2e\test_multi_service.py
- netra_backend\tests\integration\critical_paths\test_cross_database_transaction_consistency.py
- ... and 150 more files

#### Method Resolution Mapping
- `get_session` -> `SessionManager`
- `get_stats` -> `SessionManager`

---

### Implementation 5: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\db\client_postgres_session.py
**Line:** 22
**Definition:** `class SessionManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** SessionManager -> object

#### Methods (0)

#### State Analysis
**Is Stateful:** No
**State Score:** 0 (higher = more stateful)
**Complexity Score:** 0
**Method Count:** 0
**Property Count:** 0

#### Dependencies (3 files import this)
- netra_backend\app\db\client_postgres.py
- netra_backend\app\db\client_postgres_executors.py
- netra_backend\app\db\client.py

#### Method Resolution Mapping
- `close_session` -> `SessionManager`
- `commit_session` -> `SessionManager`
- `create_session_factory` -> `SessionManager`
- `rollback_session` -> `SessionManager`

---

### Implementation 6: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\services\database\session_manager.py
**Line:** 13
**Definition:** `class SessionManager:`

#### Inheritance Hierarchy
**Direct Bases:** None (base class)
**MRO:** SessionManager -> object

#### Methods (3)
- `__init__(self, model_name)`
- `validate_session(self, db, session)`
- `validate_session_with_id(self, db, entity_id, session)`

#### State Analysis
**Is Stateful:** Yes
**State Score:** 10 (higher = more stateful)
**Complexity Score:** 6
**Method Count:** 3
**Property Count:** 0

#### Dependencies (4 files import this)
- netra_backend\app\services\database\bulk_operations.py
- netra_backend\app\services\database\base_crud.py
- netra_backend\tests\integration\critical_paths\test_oauth_jwt_websocket_flow.py
- netra_backend\tests\integration\critical_paths\test_subscription_tier_enforcement.py

#### Method Resolution Mapping
- `validate_session` -> `SessionManager`
- `validate_session_with_id` -> `SessionManager`

---


## Consolidation Recommendations

### State Analysis Summary

**Stateful Managers (require instance isolation):** SessionManager, CircuitBreakerManager, RedisManager
**Stateless Managers (candidates for consolidation):** SessionManager, CircuitBreakerManager

### Recommended Consolidation Strategy

1. **Phase 1:** Consolidate stateless managers first
2. **Phase 2:** Create factory patterns for stateful managers
3. **Phase 3:** Implement unified interfaces
4. **Phase 4:** Migration and cleanup

### Risk Assessment

**High Risk:**
- Managers with >50 dependencies
- Complex inheritance hierarchies (>3 levels)
- Circular dependencies

**Medium Risk:**
- Stateful managers requiring migration
- Managers with >20 methods

**Low Risk:**
- Simple stateless managers
- Managers with clear single responsibility

## Dependency Graph Summary

**Total dependency relationships analyzed:** 0
**Most connected managers:** Top managers by dependency count

## Next Steps

1. **Resolve Circular Dependencies:** Address any cycles found
2. **Create Consolidation Plan:** Based on state and complexity analysis
3. **Design Unified Interfaces:** Create common base classes
4. **Implement Factory Patterns:** For stateful manager creation
5. **Migration Testing:** Comprehensive test suite for consolidation
6. **Performance Impact:** Benchmark before/after consolidation

---
*Analysis completed at 2025-09-04 12:35:39*
