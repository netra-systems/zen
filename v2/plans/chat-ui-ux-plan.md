# Chat UI/UX Implementation Plan

This document outlines the plan to implement the features and improvements for the chat interface as specified in `chat_ui_ux.txt`.

## 1. Project Setup & Analysis

*   **Analyze Existing Code:** Review the existing chat components, state management, and type definitions to ensure the new implementation is consistent with the current architecture.
*   **Key Files for Review:**
    *   `frontend/app/chat/page.tsx`: Main entry point for the chat page.
    *   `frontend/components/Chat.tsx`: Core chat component.
    *   `frontend/store/index.ts`: Zustand store for chat state.
    *   `frontend/types/chat.ts` & `frontend/types/index.ts`: Type definitions.
    *   `frontend/hooks/useWebSocket.ts`: WebSocket handling logic.
    *   `app/schemas.py`: Backend Pydantic schemas for data consistency.

## 2. Type Definition (`frontend/types/chat.ts`)

*   **Refine Message Types:** Create a more detailed `Message` type in `frontend/types/chat.ts` that aligns with the `schemas.py` `Message` model. This will include fields like `id`, `created_at`, `content`, `type`, `sub_agent_name`, `tool_info`, `raw_data`, and `displayed_to_user`.
*   **Displayable Messages:** Introduce a mechanism or a specific type to filter which messages are displayed to the user by default, based on the `displayed_to_user` flag from the backend.

## 3. State Management (`frontend/store/index.ts`)

*   **Update Chat Store:** Enhance the `useChatStore` to manage the new, more detailed message objects.
*   **Add State for Stop Button:** Include a state to handle the "Stop" button's status (e.g., `isProcessing`, `canStop`).

## 4. Component Implementation

*   **`chat/Header.tsx`:**
    *   Display the `subAgentName` from the `useChatStore`.
    *   Display the `subAgentStatus` (lifecycle state) from the `useChatStore`.
    *   Add an indicator for tool usage when available in the message stream.
*   **`chat/Message.tsx`:**
    *   Update the component to render the new `Message` type.
    *   Display user messages with their text and any associated references.
    *   Render different message types (user, agent, tool, error) with distinct styling.
    *   Implement collapsible sections using a UI component like `Collapsible` for displaying complex data (e.g., `tool_info`, `raw_data`).
*   **`chat/JsonViewer.tsx`:**
    *   Create a new component that renders a JSON object in an expandable tree view.
    *   Integrate this component into `Message.tsx` under a "Raw" expandable section.
*   **`chat/StopButton.tsx`:**
    *   Create a button that, when clicked, sends a `stop_agent` WebSocket message.
    *   The button should be enabled only when a process is running.
*   **`chat/MessageList.tsx`:**
    *   Update to filter messages based on the `displayed_to_user` flag.
*   **`chat/page.tsx`:**
    *   Integrate all the new and updated components to form the complete chat UI.

## 5. WebSocket Integration (`frontend/hooks/useWebSocket.ts`)

*   **Update Message Handling:** Modify the `useWebSocket` hook to handle the new `WebSocketMessage` structure from `schemas.py`.
*   **Stop Message:** Implement the logic to send the `stop_agent` message when the stop button is clicked.

## 6. UI/UX Enhancements

*   **"Alive" Feel:** Add subtle animations and transitions to the chat interface to make it feel more dynamic. This includes loading indicators when the agent is processing and smooth scrolling for new messages.
*   **Error Display:** Ensure that error messages from the backend are clearly displayed to the user in a distinct format.

## 7. Testing

*   **Unit Tests:**
    *   Write tests for the new components (`JsonViewer`, `StopButton`).
    *   Update tests for existing components (`Header`, `Message`, `MessageList`) to reflect the new props and functionality.
    *   Test the updated `useChatStore` logic.
*   **E2E Tests (Cypress):**
    *   Create a new test suite in `cypress/e2e/chat.cy.ts`.
    *   Simulate a full chat conversation, including sending messages, receiving various types of responses, and interacting with collapsible sections.
    *   Test the functionality of the "Stop" button.

## 8. Documentation

*   Create a `docs/chat_ui_ux-doc.md` file to document the new chat components, their props, and the overall architecture of the chat feature.

## 9. Schema Alignment

*   After implementation, review `shared/schemas.json` and update it if any new shared concepts were introduced that need to be aligned between the frontend and backend.
