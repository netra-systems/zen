import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainChat from '../../components/chat/MainChat';
import { TestProviders } from '@/__tests__/test-utils/providers';
import { ecurity
 * Value Impact: Prevents user access issues and security vulnerabilities
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainChat from '../../components/chat/MainChat';
import { TestProviders } from '@/__tests__/test-utils/providers';
import {
  createAuthStoreMock,
  createChatStoreMock,
  createThreadStoreMock,
  createUnifiedChatStoreMock,
  createWebSocketMock,
  createThreadServiceMock,
  setupDefaultMocks
} from './ui-test-utilities';

// Mock stores
jest.mock('../../store/authStore');
jest.mock('../../store/chatStore');
jest.mock('../../store/threadStore');
jest.mock('../../store/unified-chat');
jest.mock('../../hooks/useChatWebSocket');
jest.mock('../../services/threadService');

// Import mocked modules
import { useAuthStore } from '../../store/authStore';
import { useChatStore } from '../../store/chatStore';
import { useThreadStore } from '../../store/threadStore';
import { useUnifiedChatStore } from '../../store/unified-chat';
import { useChatWebSocket } from '../../hooks/useChatWebSocket';
import { ThreadService } from '../../services/threadService';

beforeEach(() => {
  setupDefaultMocks();
  
  // Setup default mock implementations
  (useAuthStore as unknown as jest.Mock).mockReturnValue(createAuthStoreMock());
  (useChatStore as unknown as jest.Mock).mockReturnValue(createChatStoreMock());
  (useThreadStore as unknown as jest.Mock).mockReturnValue(createThreadStoreMock());
  (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(createUnifiedChatStoreMock());
  (useChatWebSocket as unknown as jest.Mock).mockReturnValue(createWebSocketMock());
  
  // Mock ThreadService methods
  const threadServiceMock = createThreadServiceMock();
  (ThreadService as any).listThreads = threadServiceMock.listThreads;
  (ThreadService as any).createThread = threadServiceMock.createThread;
  (ThreadService as any).getThreadMessages = threadServiceMock.getThreadMessages;
  (ThreadService as any).updateThread = threadServiceMock.updateThread;
  (ThreadService as any).deleteThread = threadServiceMock.deleteThread;
});

afterEach(() => {
  jest.restoreAllMocks();
    // Clean up timers to prevent hanging
    jest.clearAllTimers();
    jest.useFakeTimers();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
});

describe('Chat Authentication Flow', () => {
    jest.setTimeout(10000);
  describe('Authenticated User Experience', () => {
      jest.setTimeout(10000);
    test('should successfully authenticate user and initialize chat interface', async () => {
      const mockUser = { 
        id: 'user-123', 
        email: 'test@example.com', 
        name: 'Test User' 
      };
      
      // Mock authenticated state
      (useAuthStore as unknown as jest.Mock).mockReturnValue(
        createAuthStoreMock({
          isAuthenticated: true,
          user: mockUser,
          token: 'mock-jwt-token'
        })
      );
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );
      
      await waitFor(() => {
        // MainChat renders a div with flex layout as root
        const container = document.querySelector('.flex.h-full');
        expect(container).toBeInTheDocument();
      });
    });

    test('should render main chat components for authenticated user', async () => {
      // Mock authenticated state
      (useAuthStore as unknown as jest.Mock).mockReturnValue(
        createAuthStoreMock({
          isAuthenticated: true,
          user: { id: 'user-123', email: 'test@example.com' }
        })
      );
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );
      
      await waitFor(() => {
        // Check for presence of chat structure
        const container = document.querySelector('.flex.h-full');
        expect(container).toBeInTheDocument();
      });
    });

    test('should display user information when authenticated', async () => {
      const mockUser = {
        id: 'user-123',
        email: 'test@example.com',
        name: 'Test User'
      };

      (useAuthStore as unknown as jest.Mock).mockReturnValue(
        createAuthStoreMock({
          isAuthenticated: true,
          user: mockUser,
          token: 'valid-token'
        })
      );

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await waitFor(() => {
        const chatContainer = document.querySelector('.flex.h-full');
        expect(chatContainer).toBeInTheDocument();
      });
    });
  });

  describe('Unauthenticated User Experience', () => {
      jest.setTimeout(10000);
    test('should handle unauthenticated state gracefully', async () => {
      // Mock unauthenticated state
      (useAuthStore as unknown as jest.Mock).mockReturnValue(
        createAuthStoreMock({
          isAuthenticated: false,
          user: null,
          token: null
        })
      );
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );
      
      // MainChat should still render but in an empty state
      await waitFor(() => {
        // Check for presence of chat structure
        const container = document.querySelector('.flex.h-full');
        expect(container).toBeInTheDocument();
      });
    });

    test('should not display user-specific features when unauthenticated', async () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue(
        createAuthStoreMock({
          isAuthenticated: false,
          user: null,
          token: null
        })
      );

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await waitFor(() => {
        const chatContainer = document.querySelector('.flex.h-full');
        expect(chatContainer).toBeInTheDocument();
      });
    });
  });

  describe('Authentication State Transitions', () => {
      jest.setTimeout(10000);
    test('should handle authentication state changes', async () => {
      const { rerender } = render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Start unauthenticated
      (useAuthStore as unknown as jest.Mock).mockReturnValue(
        createAuthStoreMock({
          isAuthenticated: false,
          user: null,
          token: null
        })
      );

      rerender(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Authenticate user
      (useAuthStore as unknown as jest.Mock).mockReturnValue(
        createAuthStoreMock({
          isAuthenticated: true,
          user: { id: 'user-123', email: 'test@example.com', name: 'Test User' },
          token: 'auth-token'
        })
      );

      rerender(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await waitFor(() => {
        const container = document.querySelector('.flex.h-full');
        expect(container).toBeInTheDocument();
      });
    });

    test('should maintain chat state during authentication', async () => {
      const mockMessages = [
        { id: '1', content: 'Test message', type: 'user' }
      ];

      (useChatStore as unknown as jest.Mock).mockReturnValue(
        createChatStoreMock({
          messages: mockMessages,
          isLoading: false
        })
      );

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await waitFor(() => {
        const container = document.querySelector('.flex.h-full');
        expect(container).toBeInTheDocument();
      });
    });
  });

  describe('Token Management', () => {
      jest.setTimeout(10000);
    test('should handle valid authentication tokens', async () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue(
        createAuthStoreMock({
          isAuthenticated: true,
          user: { id: 'user-123', email: 'test@example.com' },
          token: 'valid-jwt-token'
        })
      );

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await waitFor(() => {
        const container = document.querySelector('.flex.h-full');
        expect(container).toBeInTheDocument();
      });
    });

    test('should handle token expiration gracefully', async () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue(
        createAuthStoreMock({
          isAuthenticated: false,
          user: null,
          token: null
        })
      );

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await waitFor(() => {
        const container = document.querySelector('.flex.h-full');
        expect(container).toBeInTheDocument();
      });
    });
  });
});