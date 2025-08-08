# Chat UI/UX Implementation Plan

This document outlines the plan to implement the chat UI/UX, following the specifications in `chat_ui_ux.txt`.

## Phase 1: Backend - Message Schema and API

1.  **Define `Message` Schema:**
    *   In `app/schemas.py`, define a new Pydantic schema for `Message`. This will include fields like `content`, `type` (e.g., 'user', 'agent', 'system', 'error'), `sub_agent_name`, `tool_info`, and a field for expandable JSON data.
    *   Ensure there's a clear distinction between messages that should be displayed to the user by default and those that are for debugging or raw view.

2.  **Update WebSocket Manager:**
    *   In `app/ws_manager.py`, modify the `WebSocketManager` to handle the new `Message` schema.
    *   Ensure that messages are properly serialized to JSON before being sent over the websocket.

## Phase 2: Frontend - Component-Based UI

1.  **`Message` Component:**
    *   Create a new component `frontend/app/components/Message.tsx`.
    *   This component will be responsible for rendering a single message.
    *   It will conditionally render different styles based on the message `type`.
    *   It will display the `sub_agent_name` as the primary header.
    *   It will display `tool_info` and other secondary information.
    *   It will include a collapsible section for displaying raw JSON data in a tree view.

2.  **`ChatHistory` Component:**
    *   Create a new component `frontend/app/components/ChatHistory.tsx`.
    *   This component will be responsible for rendering a list of messages.
    *   It will fetch the message history from the `WebSocketContext`.

3.  **`Chat` Component:**
    *   Update the existing `frontend/app/components/Chat.tsx` to incorporate the new `ChatHistory` and `Message` components.
    *   Add a "Stop" button that sends a "stop_processing" message to the backend via the websocket.

## Phase 3: Frontend - State Management and WebSocket Integration

1.  **`WebSocketContext`:**
    *   Update `frontend/app/contexts/WebSocketContext.tsx` to manage the state of the chat.
    *   It will store the list of messages.
    *   It will handle incoming messages from the websocket and update the message list.
    *   It will provide a function for sending messages to the websocket.

2.  **Types:**
    *   Update `frontend/app/types/index.ts` with the new `Message` type, ensuring it's consistent with the backend schema.

## Phase 4: Styling and UX

1.  **"Alive" UI:**
    *   Use subtle animations and transitions to make the UI feel more responsive and "alive".
    *   For example, new messages can fade in, and the "thinking" indicator can have a subtle animation.

2.  **Collapsible Sections:**
    *   Implement the collapsible sections for raw JSON data using a library like `react-json-view`.

## Phase 5: Testing

1.  **Backend Tests:**
    *   Write unit tests for the new `Message` schema and any new logic in the `WebSocketManager`.

2.  **Frontend Tests:**
    *   Write unit tests for the new `Message` and `ChatHistory` components.
    *   Write end-to-end tests to verify the entire chat UI, including sending and receiving messages, stopping processing, and displaying raw JSON data.
