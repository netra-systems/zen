# Chat UI/UX Implementation Plan

This document outlines the plan to implement the chat UI/UX, as specified in `chat_ui_ux.txt`.

## 1. Backend Changes

### 1.1. `schemas.py`
- **`MessageToUser`:** Create a new Pydantic schema `MessageToUser` which will define the structure of messages sent to the user. This will include fields for the message content, the sender (user or agent), and any relevant metadata. This will address `chat_ui_ux:1:0:6`.
- **`SubAgentStatus`:** Create a new Pydantic schema `SubAgentStatus` to represent the status of a sub-agent. This will include the agent's name, the tools it's currently using, and its current state. This will address `chat_ui_ux:1:0:1:0`.

### 1.2. WebSocket Broadcasting
- **`ws_manager.py`:** The `ws_manager` will be updated to broadcast `SubAgentStatus` updates to the frontend. This will allow the UI to display the current status of each sub-agent in real-time.
- **Agent Integration:** The `Supervisor` agent will be responsible for sending `MessageToUser` and `SubAgentStatus` updates through the `ws_manager`.

## 2. Frontend Implementation

### 2.1. `types/index.ts`
- **`MessageToUser`:** Create a new TypeScript type `MessageToUser` that mirrors the Pydantic schema on the backend.
- **`SubAgentStatus`:** Create a new TypeScript type `SubAgentStatus` that mirrors the Pydantic schema on the backend.

### 2.2. `services/websocket.ts`
- The websocket service will be updated to handle incoming `MessageToUser` and `SubAgentStatus` messages.
- It will provide a way for components to subscribe to these messages.

### 2.3. Chat UI Components

- **`components/Chat.tsx`:** This will be the main chat component. It will:
    - Display the conversation history, including messages from the user and the agent.
    - Display the current status of the sub-agents.
    - Provide an input field for the user to send messages.
    - Include a "Stop" button to send a "stop" message to the backend. (`chat_ui_ux:1:0:10`)

- **`components/Message.tsx`:** This component will render a single message in the conversation. It will:
    - Differentiate between user messages and agent messages.
    - Display user messages with the user's text and any references. (`chat_ui_ux:1:0:7`)
    - Display agent messages, with a collapsible "Raw" view to show the full JSON object. (`chat_ui_ux:1:0:9`)

- **`components/SubAgentStatus.tsx`:** This component will display the status of a single sub-agent. It will:
    - Display the agent's name as the primary header. (`chat_ui_ux:1:0:1`)
    - Display the tools the agent is currently using. (`chat_ui_ux:1:0:1:0`)
    - Be updated in real-time as the agent's status changes.

### 2.4. State Management (`store/chat.ts`)
- A new Zustand store will be created to manage the state of the chat.
- It will store the conversation history, the status of the sub-agents, and any errors.

## 3. Testing

- **Backend:**
    - Unit tests for the new Pydantic schemas.
    - Integration tests to verify that the `Supervisor` agent sends the correct messages through the `ws_manager`.
- **Frontend:**
    - Unit tests for the new React components.
    - End-to-end tests to verify the entire chat UI, including sending and receiving messages, displaying sub-agent status, and the "Stop" button.

This plan addresses all the requirements in `chat_ui_ux.txt` and integrates with the existing architecture.