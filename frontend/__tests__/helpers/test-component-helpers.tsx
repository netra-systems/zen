/**
 * Test Component Helpers
 * React components for use in tests
 */

import React from 'react';

export function WebSocketStatusComponent() {
  return (
    <div data-testid="ws-status">
      Connected
    </div>
  );
}

export function AuthenticatedWebSocketComponent() {
  const handleLogin = () => {
    // Simulate login action
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', 'new-token');
    }
  };

  return (
    <div>
      <button onClick={handleLogin}>Login</button>
      <div data-testid="ws-status">Connected</div>
    </div>
  );
}

export function AuthStatusComponent() {
  return (
    <div data-testid="auth-status">
      Authenticated
    </div>
  );
}

export function MockChatComponent() {
  return (
    <div data-testid="chat-component">
      <div data-testid="message-input">
        <textarea placeholder="Type a message..." />
        <button>Send</button>
      </div>
      <div data-testid="message-list">
        <div data-testid="message">Test message</div>
      </div>
    </div>
  );
}

export function MockThreadComponent({ threadId }: { threadId: string }) {
  return (
    <div data-testid={`thread-${threadId}`}>
      Thread {threadId}
    </div>
  );
}

export function MockMessageComponent({ message }: { message: string }) {
  return (
    <div data-testid="message">
      {message}
    </div>
  );
}

export function LoadingSpinner() {
  return (
    <div data-testid="loading-spinner">
      Loading...
    </div>
  );
}

export function ErrorComponent({ error }: { error: string }) {
  return (
    <div data-testid="error-component">
      Error: {error}
    </div>
  );
}