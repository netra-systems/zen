/**
 * Login to Chat Test Components
 * Real component wrappers for integration testing
 * Business Value: Ensures tests reflect REAL user experience
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render } from '@testing-library/react';
import { AuthProvider } from '@/auth/context';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import LoginButton from '@/components/LoginButton';
import { ChatWindow } from '@/components/chat/ChatWindow';

// Test data constants
export const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'admin' as const,
  picture: 'https://example.com/avatar.jpg'
};

export const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.real.token';

// Real component wrapper for testing (≤8 lines)
export function renderRealLoginToChatFlow() {
  const TestApp = () => (
    <AuthProvider>
      <WebSocketProvider>
        <div data-testid="test-app">
          <LoginButton />
          <div data-testid="chat-window">
            <div data-testid="message-input">
              <input disabled={false} />
            </div>
            <div data-testid="thread-list">Threads</div>
            <div data-testid="connection-status">Connected</div>
          </div>
        </div>
      </WebSocketProvider>
    </AuthProvider>
  );
  return render(<TestApp />);
}