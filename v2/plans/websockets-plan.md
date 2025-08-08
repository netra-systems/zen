# WebSockets Plan

## 1. Introduction

This document outlines the plan for implementing real-time communication between the frontend and backend of the Netra application using WebSockets. The primary goal is to create a robust, scalable, and maintainable WebSocket architecture that supports the application's chat functionality and other real-time features.

## 2. Backend Architecture

The backend WebSocket architecture is built around a central `WebSocketManager` that handles connection management, message broadcasting, and authentication. Redis pub/sub is used to facilitate communication between different instances of the application.

### 2.1. WebSocketManager

The `WebSocketManager` is a singleton class responsible for:

*   **Connection Management:** Tracking all active WebSocket connections and associating them with authenticated users.
*   **Message Broadcasting:** Sending messages to specific clients or broadcasting messages to all connected clients.
*   **Authentication:** Ensuring that only authenticated users can establish a WebSocket connection.

### 2.2. Redis Pub/Sub

Redis pub/sub is used to enable communication between multiple instances of the backend application. When a message needs to be sent to a client, it's published to a Redis channel. All application instances are subscribed to the relevant channels, and the instance that's managing the connection to the target client will send the message.

### 2.3. Authentication

WebSocket connections are authenticated using the same JWT-based authentication mechanism as the rest of the API. The frontend sends the user's access token as a query parameter when establishing the WebSocket connection. The backend validates the token and, if it's valid, establishes the connection.

### 2.4. /ws Endpoint

The `/ws` endpoint is the entry point for all WebSocket connections. It's responsible for:

*   Authenticating the user.
*   Upgrading the HTTP connection to a WebSocket connection.
*   Passing the WebSocket connection to the `WebSocketManager`.

## 3. Frontend Architecture

The frontend WebSocket architecture is built using the `react-use-websocket` library, which provides a robust and easy-to-use hook for managing WebSocket connections.

### 3.1. WebSocketProvider

The `WebSocketProvider` is a React context provider that wraps the entire application. It's responsible for:

*   Establishing and maintaining the WebSocket connection.
*   Providing the WebSocket connection state and methods to its children.
*   Automatically reconnecting if the connection is lost.

### 3.2. useWebSocket Hook

The `useWebSocket` hook is a custom hook that provides a simple way for components to interact with the WebSocket connection. It's responsible for:

*   Sending and receiving messages.
*   Handling different message types.
*   Updating the application's state based on incoming messages.

### 3.3. State Management

The `useChatStore` (a Zustand store) is used to manage the state of the chat application. The `useWebSocket` hook updates the store with new messages and other real-time data received from the backend.

## 4. Message Schema

All messages sent between the frontend and backend are in JSON format and follow the `WebSocketMessage` schema defined in `app/schemas.py` and `frontend/types/index.ts`.

## 5. End-to-End Flow

1.  The frontend establishes a WebSocket connection to the `/ws` endpoint, sending the user's access token as a query parameter.
2.  The backend authenticates the user and, if successful, establishes the connection.
3.  The `WebSocketManager` adds the connection to its list of active connections.
4.  When the user sends a message, the frontend sends a `WebSocketMessage` to the backend.
5.  The backend processes the message and, if necessary, sends a response to the frontend.
6.  The frontend receives the message and updates the UI accordingly.

## 6. Testing

The WebSocket implementation will be thoroughly tested with a combination of unit tests and integration tests.

*   **Unit Tests:** Unit tests will be written for the `WebSocketManager` on the backend and the `useWebSocket` hook on the frontend.
*   **Integration Tests:** Integration tests will be written to verify the end-to-end communication between the frontend and backend.