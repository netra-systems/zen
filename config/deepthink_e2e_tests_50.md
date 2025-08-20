Based on the comprehensive audit of the `netra-core-generation-1` project and the analysis of the existing validation reports (which highlight critical gaps in E2E infrastructure, concurrency, and resilience), here are the top 5 categories where testing must be added, along with 10 specific examples of missing tests for each.

### 1. True End-to-End (E2E) with Real Services

The validation report highlights that critical E2E tests are broken due to infrastructure issues, specifically "Auth service mock configuration mismatch." Robust testing requires validating critical paths using real services rather than mocks to ensure the system functions correctly in a production-like environment.

**Missing Tests:**

1.  **Complete Cold Start (Zero State to Response):** Validate the entire flow from a clean database: service startup -> user registration -> email verification -> login -> WebSocket connection -> first meaningful agent response (addressing the currently broken test).
2.  **Real OAuth Provider Flow:** Test the authentication flow using a real external provider (e.g., Google/Microsoft sandbox) instead of mocked callbacks, validating token exchange and synchronization.
3.  **Real LLM API Interaction (E2E):** Execute agent interactions using the actual Gemini API (using a cost-effective model) to validate real-world latency, response formats, safety filter responses, and specific error codes.
4.  **Cross-Service Profile Synchronization:** Create a user via the Auth service and immediately verify that the user profile data is accurately synchronized to the Backend service’s database in the E2E environment.
5.  **Redis Cache Population and Invalidation (E2E):** Verify in a real environment that agent actions correctly populate the Redis cache, subsequent actions read from it, and updates trigger proper invalidation.
6.  **Database Consistency (Postgres to ClickHouse):** Validate that transactional data written to Postgres is correctly synchronized and aggregated in ClickHouse without using database mocks.
7.  **Observability Platform Integration (E2E):** Execute a workflow and verify that the telemetry data (logs, traces) correctly appears in the configured observability platform (e.g., Langfuse).
8.  **Service Discovery Synchronization:** In a multi-instance E2E environment, force a service restart and verify that other services correctly update their connection information via service discovery.
9.  **SSL/TLS Negotiation and Validation:** Ensure all inter-service communication and external API calls correctly negotiate and validate SSL/TLS certificates in a production-like environment.
10. **Background Job Processing E2E:** Submit a long-running background task (e.g., corpus indexing) and verify its execution and completion status updates through the full stack.

### 2. WebSocket Resilience and State Management

The validation report indicates 0% coverage for WebSocket reconnection and state preservation due to incomplete test infrastructure. This is a critical gap for a real-time application.

**Missing Tests:**

1.  **Client Reconnection Preserves Context:** Validate that if a client disconnects and reconnects using the same session token, their agent context and conversation history are immediately available (addressing the currently broken test).
2.  **Mid-Stream Disconnection and Recovery:** Simulate a network drop while the agent is actively streaming a response. Verify the agent's state is preserved and the response resumes or re-delivers upon reconnection.
3.  **Message Queuing During Disconnection:** Ensure that messages sent by the agent while the client is briefly disconnected are queued and delivered in the correct order upon reconnection.
4.  **Reconnection with Expired Token:** Verify that attempts to reconnect with an expired JWT are rejected and the user is prompted to re-authenticate.
5.  **Backend Service Restart Recovery:** Test the client-side recovery mechanism when the backend server restarts (e.g., during a deployment), ensuring clients automatically reconnect.
6.  **Rapid Reconnection (Flapping):** Simulate unstable network conditions (rapid connects/disconnects) to ensure the server handles it gracefully without duplicating agent instances.
7.  **WebSocket Heartbeat Validation:** Verify the implementation of the Ping/Pong or heartbeat mechanism to detect and terminate zombie connections (where the client disappeared without closing the connection).
8.  **Invalid/Malformed Payload Handling (Fuzzing):** Send oversized or malformed JSON payloads via WebSocket to validate error handling and prevent denial-of-service (DoS).
9.  **Network Interface Switching:** Simulate a client switching networks (e.g., WiFi to Cellular), forcing a reconnection with a new IP address, and verify seamless continuation.
10. **Token Refresh over WebSocket:** Validate the mechanism for refreshing JWT tokens over an existing WebSocket connection without requiring a full disconnect.

### 3. Concurrency, Isolation, and Load Testing

The infrastructure for testing concurrent user isolation is currently broken, posing significant risks to data security and system stability under load in a multi-tenant environment.

**Missing Tests:**

1.  **Concurrent Agent Startup Isolation (The "100 User Test"):** Simulate 100+ different users sending their first message simultaneously and verify that each receives a unique, isolated agent instance with no cross-contamination (addressing the currently broken test).
2.  **Race Conditions in Authentication:** Test concurrent token refresh requests or simultaneous logins from multiple devices for the same user, ensuring correct session management.
3.  **Rapid Message Succession (Idempotency/Ordering):** Test a single user sending messages in rapid succession to ensure messages are processed sequentially and the agent state updates correctly without duplication.
4.  **Database Connection Pool Exhaustion:** Stress test the system to the point of database connection pool exhaustion and verify the system queues requests or returns appropriate backpressure signals rather than crashing.
5.  **Spike Testing and Recovery:** Simulate a sudden, massive influx of user logins (Thundering Herd problem) and measure system response and recovery time.
6.  **Agent Resource Utilization Isolation:** Monitor CPU and Memory usage per agent instance under load to ensure one tenant's activity does not degrade the performance of others (noisy neighbor problem).
7.  **Concurrent Tool Execution Conflicts:** Simulate concurrent agent tools attempting to modify the same database resource, testing transaction isolation and deadlock handling.
8.  **Long-Duration Soak Testing:** Run the system under sustained load (e.g., 48 hours) to detect memory leaks and resource exhaustion issues.
9.  **Cache Contention Under Load:** Test performance when multiple users simultaneously access and update the same cached resources in Redis, verifying atomic updates.
10. **High-Volume Message Throughput:** Flood the WebSocket server with thousands of messages per second and verify message ordering, latency, and delivery guarantees.

### 4. System Resilience and Fallback Mechanisms

Testing for failures in external dependencies (LLM providers, databases) is limited. Robust testing requires validating these scenarios against real (or accurately simulated) service failures.

**Missing Tests:**

1.  **LLM Provider Failover (Automatic):** Simulate the failure of the primary LLM provider (e.g., Gemini API down) and verify automatic, seamless fallback to a secondary provider.
2.  **LLM Rate Limit Handling (Exponential Backoff):** Simulate the LLM API returning "Rate Limit Exceeded" errors and verify the system implements exponential backoff and queuing, rather than dropping the request.
3.  **Total LLM Outage (Graceful Degradation):** Simulate failure of all configured LLM providers and verify the agent returns a graceful "Service Temporarily Unavailable" message rather than crashing.
4.  **Database Connectivity Loss and Recovery:** Simulate temporary loss of connection to PostgreSQL during an agent interaction and validate the agent's automatic recovery and transaction handling.
5.  **Redis (Cache/Session Store) Failure:** Validate the impact when Redis is unavailable, ensuring the system remains operational by falling back to the primary database.
6.  **Circuit Breaker Activation and Recovery:** Verify that circuit breakers trip open when external services fail repeatedly and close automatically (half-open state) when services recover.
7.  **Analytics Database (ClickHouse) Failure Isolation:** Ensure that failures in the analytics database do not impact the core transactional workflows of the agents.
8.  **LLM Malformed Response Handling:** Simulate the LLM returning syntactically invalid JSON or truncated responses. Verify the robustness of the JSON extraction utilities and agent error handling.
9.  **Agent Recovery from Internal Crash:** Simulate an internal sub-agent crash (panic) and validate the supervisor's ability to restart the agent and recover the session state.
10. **Corrupted State Recovery (E2E):** Intentionally corrupt a user's agent state in the database/cache and verify the system detects the corruption, resets to a clean state, and allows the conversation to continue.

### 5. Security and Permissions Enforcement

The presence of powerful administrative tools (`admin_tool_dispatcher`) and a multi-tiered user system requires rigorous security testing, which is not explicitly detailed in current reports.

**Missing Tests:**

1.  **Tenant Isolation (Horizontal Privilege Escalation):** Verify that a user belonging to Organization A cannot access, view, or modify data (conversations, corpus) belonging to Organization B (Insecure Direct Object Reference - IDOR).
2.  **Unauthorized Admin Tool Execution (Vertical Privilege Escalation):** Test a standard user attempting to execute restricted admin tools (e.g., `_update_system_setting`, `_create_user`) and verify access is denied.
3.  **Tier-Based Feature Gating:** Ensure that users on lower tiers (e.g., Free) cannot access features or exceed usage limits reserved for higher tiers (e.g., Enterprise).
4.  **Prompt Injection and Jailbreaking:** Attempt to manipulate the LLM's behavior or extract sensitive system prompts by embedding malicious instructions in the user input.
5.  **JWT Tampering and Validation:** Test for common JWT vulnerabilities, including signature stripping, algorithm confusion, and improper validation of claims.
6.  **Permissions Revocation Latency:** Revoke an administrator's permission and immediately attempt to use that permission, verifying the change is enforced in real-time, even for active WebSocket sessions.
7.  **Cross-Site Scripting (XSS) in Agent Responses:** Validate that agent-generated content (especially LLM outputs) is properly sanitized by the frontend to prevent XSS attacks.
8.  **PII/Secret Leakage in Logs:** Verify that sensitive information (passwords, tokens, API keys) is not inadvertently leaked in application logs, crash reports, or observability tools (Langfuse).
9.  **Brute Force Login Protection:** Verify that rate limiting and account lockout policies are enforced on the authentication endpoints.
10. **Insecure File Upload Validation:** Attempt to upload malicious files or files exceeding size limits to the corpus service, testing validation mechanisms.