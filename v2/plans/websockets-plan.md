# WebSocket Implementation Plan

This document outlines the plan to implement a production-grade, real-time WebSocket communication layer between the frontend and backend, adhering to the specified architectural principles.

## Phase 1: Backend Enhancements

The backend provides a solid foundation, but requires minor enhancements for robustness and observability.

1.  **Improve Authentication Logging:**
    *   **File:** `app/auth/auth_dependencies.py`
    *   **Action:** Add explicit `logger.warning` calls within the `get_current_user_ws` dependency to log failed authentication attempts on WebSocket connections. This addresses requirement `1:0:2:1`.

2.  **Verify Supervisor Streaming:**
    *   **File:** `app/agents/supervisor.py`
    *   **Action:** Review the `run` method to ensure it uses the `websocket_manager` to send typed `WebSocketMessage` updates (e.g., `agent_started`, `sub_agent_update`, `agent_completed`). The implementation must guarantee that only complete, valid JSON objects are streamed, in line with `1:0:1:0`, `1:0:1:1`, and `1:0:2:4`.

## Phase 2: Frontend Implementation

This phase focuses on building the frontend components, which will be designed around a single, centralized service to manage the WebSocket lifecycle as per requirement `1:0:1`.

1.  **Generate TypeScript Types:**
    *   **Action:** Utilize the `scripts/generate_frontend_types.py` script to create TypeScript interfaces from the Pydantic schemas in `app/schemas.py`.
    *   **Output:** The generated types will be saved to `frontend/types/websockets.ts`, ensuring a strong type contract between the frontend and backend (`0:1:1:0:0`).

2.  **Create Centralized WebSocket Service:**
    *   **File:** `frontend/services/webSocketService.ts`
    *   **Action:** Create a new service to encapsulate all WebSocket logic. It will manage the connection lifecycle (connect, disconnect, reconnect with exponential backoff), handle message serialization/deserialization, and manage the ping/pong keep-alive. This service will be the single entry point for all WebSocket communication.

3.  **Implement WebSocket React Context:**
    *   **File:** `frontend/contexts/WebSocketContext.tsx`
    *   **Action:** Create a new React context that will serve as the single source of truth for WebSocket state throughout the application.
    *   **Details:**
        *   It will instantiate the `webSocketService`.
        *   It will manage the connection state (`CONNECTING`, `OPEN`, `CLOSED`).
        *   It will provide the connection state and a `sendMessage` function to all child components.
        *   It will be designed to establish the connection on application load and maintain it, making it persistent and resilient to component re-renders, fulfilling requirements `1:0:2:1`, `1:0:2:2`, and `1:0:2:3`.

4.  **Integrate into Application:**
    *   **File:** `frontend/app/layout.tsx` (or the root component)
    *   **Action:** Wrap the main application component with the `WebSocketProvider` to make the context available globally.
    *   **Hook:** Create a `useWebSocket` custom hook for easy and consistent access to the context from any component.

5.  **Develop UI Components for Interaction:**
    *   **Action:** Create or modify a component to demonstrate the WebSocket functionality. This component will:
        *   Use the `useWebSocket` hook to get the connection status and `sendMessage` function.
        *   Provide a UI to send an `analysis_request` to the backend.
        *   Listen for incoming messages and display them, using the generated TypeScript types for parsing.

## Phase 3: Validation and Testing

1.  **Backend Unit/Integration Tests:**
    *   **File:** `integration_tests/test_websocket.py`
    *   **Action:** Enhance the existing test. Mock the `AgentSupervisor` to simulate sending various `WebSocketMessage` types back to the client upon receiving an `analysis_request`. Assert that the test client receives the correct, well-formed JSON messages.

2.  **Frontend Unit Tests:**
    *   **File:** `frontend/__tests__/WebSocket.test.tsx`
    *   **Action:** Create a new test file to validate the `WebSocketContext` and `webSocketService`. Use a library like `mock-socket` to mock the WebSocket server, allowing for testing of connection logic, message sending, and state management in isolation.

3.  **End-to-End Verification:**
    *   **Action:** Manually test the entire flow by running the backend and frontend.
    *   **Steps:**
        1.  Use browser developer tools to monitor the network tab and inspect WebSocket frames.
        2.  Verify the connection is established on page load.
        3.  Trigger an analysis from the UI and confirm the `analysis_request` is sent.
        4.  Confirm the backend streams back typed messages (`agent_started`, etc.).
        5.  Ensure the UI reacts correctly to these messages.
        6.  Confirm the ping/pong keep-alive is working.
