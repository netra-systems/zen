# Chat UI/UX Implementation Plan

This document outlines the plan to implement the chat UI/UX, as specified in `chat_ui_ux.txt`.

## 1. Project Conventions and Coherence

*   **Types:** All new frontend types will be defined in `frontend/types/index.ts`, and all new backend schemas will be in `app/schemas.py`.
*   **Single Source of Truth:** New concepts will be defined once and referenced elsewhere.
*   **Frontend Imports:** All frontend imports will be absolute, using the `@/` alias.
*   **Connection:** The connection between frontend and backend will align with `shared/schema.json`.

## 2. Backend Changes

### 2.1. `app/schemas.py`

*   **`SubAgentStatus` (chat_ui_ux:1:0:1:0):**
    *   Create a new Pydantic schema `SubAgentStatus` with the following fields:
        *   `agent_name: str`
        *   `tools: List[str]`
        *   `status: str`
*   **`MessageToUser` (chat_ui_ux:1:0:6):**
    *   Create a new Pydantic schema `MessageToUser` with the following fields:
        *   `sender: str` (e.g., "user", "agent")
        *   `content: str`
        *   `references: Optional[List[str]] = None`
        *   `raw_json: Optional[Dict] = None`
        *   `error: Optional[str] = None`
*   **`WebSocketMessage`:**
    *   Update the `WebSocketMessage` schema to include a new `message_type` of `sub_agent_status` and `user_message`.
    *   The `data` field will contain either a `SubAgentStatus` or `MessageToUser` object.

### 2.2. `app/ws_manager.py`

*   Update the `broadcast` method to handle the new `sub_agent_status` and `user_message` message types.

### 2.3. `app/agents/supervisor.py`

*   The `Supervisor` agent will be responsible for sending `SubAgentStatus` and `MessageToUser` updates through the `ws_manager`.
*   When a sub-agent is activated, the `Supervisor` will send a `SubAgentStatus` message.
*   When a sub-agent completes its task, the `Supervisor` will send an updated `SubAgentStatus` message.
*   When the `Supervisor` sends a message to the user, it will use the `MessageToUser` schema.

## 3. Frontend Implementation

### 3.1. `frontend/types/index.ts`

*   Create TypeScript interfaces `SubAgentStatus` and `MessageToUser` that mirror the Pydantic schemas.
*   Update the `WebSocketMessage` type to include the new message types.

### 3.2. `frontend/services/websocket.ts`

*   Update the WebSocket service to handle incoming `sub_agent_status` and `user_message` messages.
*   It will provide a way for components to subscribe to these messages.

### 3.3. `frontend/store/chat.ts`

*   Create a new Zustand store to manage the chat state.
*   It will store:
    *   `messages: MessageToUser[]`
    *   `subAgentStatus: SubAgentStatus | null`
    *   `error: string | null`

### 3.4. Chat UI Components

*   **`frontend/components/chat/Chat.tsx` (chat_ui_ux:1:0):**
    *   This will be the main chat component.
    *   It will use the `useChatStore` to get the latest state.
    *   It will render the `SubAgentHeader`, `MessageList`, and `ChatInput` components.
*   **`frontend/components/chat/SubAgentHeader.tsx` (chat_ui_ux:1:0:1):**
    *   Display the `subAgentStatus.agent_name` as the primary header.
    *   Display `subAgentStatus.tools` and `subAgentStatus.status` as secondary items.
*   **`frontend/components/chat/MessageList.tsx` (chat_ui_ux:1:0:2):**
    *   Render a list of messages from the `chatStore`.
*   **`frontend/components/chat/Message.tsx` (chat_ui_ux:1:0:3, chat_ui_ux:1:0:4, chat_ui_ux:1:0:7, chat_ui_ux:1:0:9):**
    *   Render a single message.
    *   Use different styles for user and agent messages.
    *   Display user messages with text and references.
    *   Display agent messages with a collapsible card that contains the `raw_json` in a tree view.
    *   Display errors prominently.
*   **`frontend/components/chat/ChatInput.tsx` (chat_ui_ux:1:0:10):**
    *   Provide a text input for the user to send messages.
    *   Include a "Stop" button that sends a "stop_processing" message via WebSocket.
*   **`frontend/components/common/JsonTreeView.tsx` (chat_ui_ux:1:0:9):**
    *   A component to render a JSON object in an expandable tree view.

### 3.5. UI/UX Feel (`chat_ui_ux:1:0:8`)

*   Use subtle animations and transitions to make the UI feel "alive".
*   For example, new messages can fade in, and the sub-agent status can have a subtle pulsing effect when active.

## 4. Testing (`chat_ui_ux:1:0:12`)

*   **Backend:**
    *   Unit tests for the new Pydantic schemas.
    *   Integration tests for the `Supervisor` agent to verify that it sends the correct messages through the `ws_manager`.
*   **Frontend:**
    *   Unit tests for all new React components.
    *   End-to-end tests using Cypress to verify the entire chat UI, including:
        *   Sending and receiving messages.
        *   Displaying sub-agent status.
        *   The "Stop" button.
        *   The "Raw" JSON view.

## 5. Documentation

*   Create `docs/chat_ui_ux-doc.md` to document the new chat components and their usage.

## 6. Schema Alignment

*   Update `shared/schemas.json` with the new `SubAgentStatus` and `MessageToUser` schemas.
