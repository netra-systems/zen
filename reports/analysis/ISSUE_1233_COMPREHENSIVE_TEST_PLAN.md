# Issue #1233 - Missing API Endpoints Test Plan

## 🎯 EXECUTIVE SUMMARY

**Issue**: Missing `/api/conversations` and `/api/history` endpoints returning 404
**Business Impact**: Users cannot access conversation management and history features via REST API
**Test Strategy**: Create comprehensive failing tests that validate the 404 behavior, then define expected functionality for future implementation

## 📋 TEST STRATEGY OVERVIEW

### Test Categories
1. **Unit Tests** - Test individual endpoint handlers and business logic
2. **Integration Tests** - Test request/response cycle with real authentication (NO DOCKER)
3. **E2E Tests** - Test complete user flows on GCP staging environment

### Test Philosophy
- **Tests First Fail** - All tests initially reproduce the 404 issue
- **Real Services** - Use real authentication, database, and services (no mocks in integration/E2E)
- **Business Value** - Tests validate actual user conversation management needs
- **SSOT Compliance** - Follow test framework standards and patterns

## 🔍 CURRENT STATE ANALYSIS

### Existing Infrastructure
- **Thread Management**: `/api/threads` endpoints exist with full CRUD operations
- **Message Handling**: WebSocket-based conversation history handlers exist
- **Authentication**: JWT-based auth with user isolation
- **Database**: Thread and message repositories with PostgreSQL storage

### Missing Components
- **REST API Endpoints**: `/api/conversations` and `/api/history` not implemented
- **Route Registration**: No route configurations for these endpoints
- **Handler Implementation**: Missing FastAPI route handlers

### Expected Functionality (Inferred)
- `/api/conversations` - Manage user conversations (likely alias for threads)
- `/api/history` - Retrieve conversation/message history

## 📁 TEST FILE STRUCTURE

```
tests/
├── unit/
│   ├── test_conversations_endpoint_unit.py
│   ├── test_history_endpoint_unit.py
│   └── test_conversation_business_logic_unit.py
├── integration/
│   ├── test_conversations_api_integration.py
│   ├── test_history_api_integration.py
│   └── test_conversation_auth_integration.py
└── e2e/
    ├── test_conversations_e2e_staging.py
    ├── test_history_e2e_staging.py
    └── test_conversation_flow_e2e_staging.py
```

## 🧪 DETAILED TEST SPECIFICATIONS

### 1. UNIT TESTS

#### 1.1 Conversations Endpoint Unit Tests
**File**: `tests/unit/test_conversations_endpoint_unit.py`

**Test Cases**:
- `test_conversations_endpoint_returns_404` - Current failing behavior
- `test_conversations_get_handler_not_implemented` - Handler doesn't exist
- `test_conversations_post_handler_not_implemented` - POST not available
- `test_conversations_endpoint_expected_functionality` - Future implementation spec

**Business Logic**:
- `test_conversation_list_logic` - List user conversations
- `test_conversation_create_logic` - Create new conversation
- `test_conversation_filter_logic` - Filter by date/status
- `test_conversation_pagination_logic` - Paginated results

#### 1.2 History Endpoint Unit Tests
**File**: `tests/unit/test_history_endpoint_unit.py`

**Test Cases**:
- `test_history_endpoint_returns_404` - Current failing behavior
- `test_history_get_handler_not_implemented` - Handler doesn't exist
- `test_history_query_params_validation` - Expected parameter validation
- `test_history_endpoint_expected_functionality` - Future implementation spec

**Business Logic**:
- `test_history_retrieval_logic` - Get message history
- `test_history_filtering_logic` - Filter by thread/date
- `test_history_format_logic` - Response format validation
- `test_history_permissions_logic` - User isolation validation

#### 1.3 Conversation Business Logic Unit Tests
**File**: `tests/unit/test_conversation_business_logic_unit.py`

**Test Cases**:
- `test_conversation_thread_mapping` - How conversations map to threads
- `test_conversation_metadata_handling` - Metadata management
- `test_conversation_state_management` - Active/archived states
- `test_conversation_user_isolation` - Multi-user separation

### 2. INTEGRATION TESTS (NO DOCKER)

#### 2.1 Conversations API Integration Tests
**File**: `tests/integration/test_conversations_api_integration.py`

**Test Cases**:
- `test_conversations_endpoint_404_with_auth` - 404 with valid JWT
- `test_conversations_endpoint_401_without_auth` - Unauthorized access
- `test_conversations_endpoint_cors_headers` - CORS configuration
- `test_conversations_endpoint_rate_limiting` - Rate limit behavior

**Expected Implementation Tests**:
- `test_conversations_get_with_real_database` - List conversations
- `test_conversations_post_with_real_database` - Create conversation
- `test_conversations_pagination_real_data` - Pagination with real data
- `test_conversations_filtering_real_data` - Filtering with real database

#### 2.2 History API Integration Tests  
**File**: `tests/integration/test_history_api_integration.py`

**Test Cases**:
- `test_history_endpoint_404_with_auth` - 404 with valid JWT
- `test_history_endpoint_query_params` - Query parameter handling
- `test_history_endpoint_response_format` - Expected response structure
- `test_history_endpoint_performance` - Response time validation

**Expected Implementation Tests**:
- `test_history_retrieval_real_database` - Get history from real DB
- `test_history_filtering_real_database` - Filter history by criteria
- `test_history_user_isolation_real_auth` - User data separation
- `test_history_message_format_validation` - Message format consistency

#### 2.3 Conversation Authentication Integration Tests
**File**: `tests/integration/test_conversation_auth_integration.py`

**Test Cases**:
- `test_conversation_endpoints_require_auth` - Auth requirement validation
- `test_conversation_jwt_validation` - JWT token validation
- `test_conversation_user_context_isolation` - User context separation
- `test_conversation_auth_error_handling` - Auth error responses

### 3. E2E TESTS (GCP STAGING)

#### 3.1 Conversations E2E Staging Tests
**File**: `tests/e2e/test_conversations_e2e_staging.py`

**Test Cases**:
- `test_conversations_404_staging_environment` - 404 on staging
- `test_conversations_endpoint_discovery_staging` - OpenAPI discovery
- `test_conversations_load_balancer_routing` - GCP routing behavior
- `test_conversations_https_redirect` - HTTPS enforcement

**Future Implementation E2E**:
- `test_conversations_complete_flow_staging` - End-to-end conversation flow
- `test_conversations_multi_user_staging` - Multiple users simultaneously
- `test_conversations_websocket_integration` - Integration with WebSocket events
- `test_conversations_mobile_compatibility` - Mobile client compatibility

#### 3.2 History E2E Staging Tests
**File**: `tests/e2e/test_history_e2e_staging.py`

**Test Cases**:
- `test_history_404_staging_environment` - 404 on staging
- `test_history_cdn_caching` - CDN cache behavior
- `test_history_geographic_latency` - Multi-region response times
- `test_history_concurrent_users` - Concurrent access patterns

**Future Implementation E2E**:
- `test_history_large_dataset_staging` - Performance with large history
- `test_history_real_time_updates` - Real-time history updates
- `test_history_export_functionality` - History export features
- `test_history_analytics_integration` - Analytics tracking

#### 3.3 Conversation Flow E2E Staging Tests
**File**: `tests/e2e/test_conversation_flow_e2e_staging.py`

**Test Cases**:
- `test_complete_conversation_lifecycle` - Create → Message → History → Archive
- `test_conversation_websocket_rest_integration` - WebSocket + REST API integration
- `test_conversation_agent_integration` - AI agent conversation flows
- `test_conversation_business_value_delivery` - End-to-end business value

## 🔧 TEST DATA AND FIXTURES

### Authentication Strategy
```python
# Real authentication using existing JWT infrastructure
@pytest.fixture
async def authenticated_user():
    """Create real authenticated user for testing."""
    # Use real auth service to create test user
    user = await create_test_user(
        email="test-conversations@example.com",
        password="test-password"
    )
    token = await get_jwt_token(user.email, user.password)
    return {"user": user, "token": token}

@pytest.fixture
async def auth_headers(authenticated_user):
    """HTTP headers with valid JWT token."""
    return {"Authorization": f"Bearer {authenticated_user['token']}"}
```

### Test Data Strategy
```python
# Real database fixtures
@pytest.fixture
async def test_conversations(real_db, authenticated_user):
    """Create test conversation data in real database."""
    conversations = []
    for i in range(5):
        conv = await create_conversation(
            db=real_db,
            user_id=authenticated_user["user"].id,
            title=f"Test Conversation {i}",
            metadata={"test": True, "index": i}
        )
        conversations.append(conv)
    return conversations

@pytest.fixture
async def test_message_history(real_db, test_conversations):
    """Create test message history in real database."""
    history = []
    for conv in test_conversations:
        for j in range(3):
            message = await create_message(
                db=real_db,
                thread_id=conv.id,
                content=f"Test message {j} in conversation {conv.id}",
                role="user" if j % 2 == 0 else "assistant"
            )
            history.append(message)
    return history
```

## 🎯 TEST EXECUTION PLAN

### Phase 1: Validate Current 404 Behavior
```bash
# Run failing tests to confirm 404 behavior
python tests/unified_test_runner.py --test-file tests/unit/test_conversations_endpoint_unit.py
python tests/unified_test_runner.py --test-file tests/unit/test_history_endpoint_unit.py

# Integration tests with real services (no Docker)
python tests/unified_test_runner.py --test-file tests/integration/test_conversations_api_integration.py --real-services
python tests/unified_test_runner.py --test-file tests/integration/test_history_api_integration.py --real-services

# E2E tests on staging
python tests/unified_test_runner.py --test-file tests/e2e/test_conversations_e2e_staging.py --env staging
python tests/unified_test_runner.py --test-file tests/e2e/test_history_e2e_staging.py --env staging
```

### Phase 2: Implementation Validation (Future)
```bash
# After endpoints are implemented, these tests should pass
python tests/unified_test_runner.py --category integration --real-services --filter "conversation|history"
python tests/unified_test_runner.py --category e2e --env staging --filter "conversation|history"
```

## 📊 SUCCESS CRITERIA

### Failing Tests (Current State)
- [ ] All 404 tests pass (confirming current issue)
- [ ] Authentication tests fail appropriately (401/403)
- [ ] Route discovery tests confirm missing endpoints

### Implementation Tests (Future Success)
- [ ] Conversation CRUD operations work end-to-end
- [ ] History retrieval works with filtering and pagination
- [ ] User isolation works correctly
- [ ] WebSocket + REST API integration functions
- [ ] Performance meets SLA requirements (< 500ms response time)

## 🔍 BUSINESS VALUE JUSTIFICATION

### Segment
- **All tiers**: Free, Early, Mid, Enterprise users need conversation management

### Business Goals
- **Retention**: Users need to access conversation history
- **Expansion**: Conversation management enables advanced features
- **Conversion**: Essential functionality for trial-to-paid conversion

### Value Impact
- **User Experience**: REST API access to conversations improves integration
- **Developer Experience**: Standard REST endpoints enable third-party integrations
- **Platform Completeness**: Fills gap in API coverage

### Strategic Impact
- **API Completeness**: Achieves feature parity between WebSocket and REST
- **Integration Enablement**: Allows mobile apps and integrations
- **Revenue Protection**: Prevents churn due to missing functionality

## 🚨 CRITICAL REQUIREMENTS

### Test Standards
- **No Docker Dependencies**: Integration tests use real services without Docker
- **Real Authentication**: All tests use actual JWT authentication
- **SSOT Compliance**: Follow test framework patterns from `test_framework/`
- **Business Value Focus**: Tests validate actual user needs, not just technical functionality

### Implementation Requirements (Future)
- **User Isolation**: Conversations must be properly isolated by user
- **Performance**: < 500ms response time for conversation listing
- **Security**: Proper JWT validation and CORS headers
- **Consistency**: API patterns consistent with existing `/api/threads` endpoints

## 📝 NEXT STEPS

1. **Create Test Files**: Implement all test files according to this plan
2. **Validate 404 Behavior**: Run tests to confirm current failing state
3. **Document Expected API**: Define OpenAPI specifications for missing endpoints
4. **Implementation Planning**: Use test cases to guide endpoint implementation
5. **Continuous Validation**: Run tests after implementation to ensure functionality

---

**Business Priority**: HIGH - Conversation management is core platform functionality
**Technical Complexity**: MEDIUM - Leverages existing thread infrastructure
**Test Coverage**: COMPREHENSIVE - Unit, Integration, and E2E validation
**Execution Timeline**: 2-3 days for test creation, TBD for implementation