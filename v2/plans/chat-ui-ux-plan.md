# Chat UI/UX Implementation Plan

This document outlines the plan to implement the chat UI/UX as specified in `chat_ui_ux.txt`.

## 1. Consolidate Chat Components

There are two directories with chat components: `components/chat` and `chat`. I will analyze the contents of both and consolidate them into a single `components/chat` directory to have a single source of truth. I will move the files from `chat` to `components/chat` and update the imports.

## 2. Implement the Chat UI based on the spec

- **`ChatHeader.tsx` (`chat_ui_ux:1:0:1`):** I will modify `components/chat/Header.tsx` to display the SubAgent name and status, including the tools being used (`chat_ui_ux:1:0:1:0`).
- **`MessageList.tsx` and `Message.tsx` (`chat_ui_ux:1:0:2`, `chat_ui_ux:1:0:7`):** I will update `components/chat/MessageList.tsx` and `components/chat/Message.tsx` to render the messages. I will ensure user messages display the user's text and references.
- **Collapsible JSON View (`chat_ui_ux:1:0:3`, `chat_ui_ux:1:0:9`):** I will implement a collapsible JSON view within `Message.tsx` for displaying raw message data, using `JsonViewer.tsx`.
- **Error Display (`chat_ui_ux:1:0:4`):** I will implement error display functionality, likely in `ChatWindow.tsx` or a new `ErrorDisplay.tsx` component.
- **"Alive" UI (`chat_ui_ux:1:0:8`):** I will add subtle animations and transitions to make the UI feel more alive.
- **Stop Button (`chat_ui_ux:1:0:10`):** I will integrate the `StopButton.tsx` component into the `ChatWindow.tsx`.

## 3. Implement Example Prompts (`chat_ui_ux:1:0:11`)

- I will create a new component `components/chat/ExamplePrompts.tsx`.
- I will import the example prompts from a new file `lib/examplePrompts.ts` (`chat_ui_ux:1:0:11:Examples:0`).
- The component will display the prompts as cards (`chat_ui_ux:1:0:11:Examples:2`).
- Clicking an example will send it to the chat and collapse the examples panel (`chat_ui_ux:1:0:11:Examples:3`).

## 4. Add Tests (`chat_ui_ux:1:0:12`)

- I will add tests for the new and modified components.
