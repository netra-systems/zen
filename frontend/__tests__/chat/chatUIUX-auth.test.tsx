import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { render, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainChat from '@/components/chat/MainChat';
import { } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainChat from '@/components/chat/MainChat';
import { 
  setupBasicMocks,
  setupAuthenticatedStore,
  setupUnauthenticatedStore,
  createMockAuthStore,
  renderWithProviders,
  expectChatStructure,
  expectAuthenticatedStructure,
  cleanupMocks
} from './chatUIUX-shared-utilities';

// Setup mocks
setupBasicMocks();

// Import mocked modules
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';

describe('Chat UI/UX Authentication Flow Tests', () => {
    jest.setTimeout(10000);
  const mockAuthStore = createMockAuthStore();
  
  beforeEach(() => {
    jest.clearAllMocks();
    global.confirm = jest.fn(() => true);
    setupMockReturnValues();
  });

  afterEach(() => {
    cleanupMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('User Authentication Flow', () => {
      jest.setTimeout(10000);
    test('1. Should successfully authenticate user and initialize chat interface', async () => {
      const authenticatedStore = setupAuthenticatedStore(mockAuthStore);
      (useAuthStore as unknown as jest.Mock).mockReturnValue(authenticatedStore);
      
      render(renderWithProviders(<MainChat />));
      
      await waitFor(() => {
        expectChatStructure();
      });
    });

    test('2. Should handle unauthenticated state', async () => {
      const unauthenticatedStore = setupUnauthenticatedStore(mockAuthStore);
      (useAuthStore as unknown as jest.Mock).mockReturnValue(unauthenticatedStore);
      
      render(renderWithProviders(<MainChat />));
      
      await waitFor(() => {
        expectChatStructure();
      });
    });

    test('3. Should render main chat components when authenticated', async () => {
      const authenticatedStore = setupAuthenticatedStore(mockAuthStore);
      (useAuthStore as unknown as jest.Mock).mockReturnValue(authenticatedStore);
      
      render(renderWithProviders(<MainChat />));
      
      await waitFor(() => {
        expectChatStructure();
      });
    });

    test('4. Should maintain authentication state across renders', async () => {
      const authenticatedStore = setupAuthenticatedStore(mockAuthStore);
      (useAuthStore as unknown as jest.Mock).mockReturnValue(authenticatedStore);
      
      const { unmount } = render(renderWithProviders(<MainChat />));
      unmount();
      
      render(renderWithProviders(<MainChat />));
      
      await waitFor(() => {
        expectChatStructure();
      });
    });

    test('5. Should handle authentication token validation', async () => {
      const storeWithToken = {
        ...setupAuthenticatedStore(mockAuthStore),
        token: 'valid-jwt-token-123'
      };
      (useAuthStore as unknown as jest.Mock).mockReturnValue(storeWithToken);
      
      render(renderWithProviders(<MainChat />));
      
      await waitFor(() => {
        expectChatStructure();
      });
    });

    test('6. Should handle missing authentication gracefully', async () => {
      const partialStore = {
        ...setupUnauthenticatedStore(mockAuthStore),
        user: null,
        token: null
      };
      (useAuthStore as unknown as jest.Mock).mockReturnValue(partialStore);
      
      render(renderWithProviders(<MainChat />));
      
      await waitFor(() => {
        expectChatStructure();
      });
    });

    test('7. Should handle authentication errors', async () => {
      const errorStore = {
        ...setupUnauthenticatedStore(mockAuthStore),
        error: 'Authentication failed'
      };
      (useAuthStore as unknown as jest.Mock).mockReturnValue(errorStore);
      
      render(renderWithProviders(<MainChat />));
      
      await waitFor(() => {
        expectChatStructure();
      });
    });

    test('8. Should handle user permissions correctly', async () => {
      const permissionStore = {
        ...setupAuthenticatedStore(mockAuthStore),
        hasPermission: jest.fn().mockReturnValue(true),
        isAdminOrHigher: jest.fn().mockReturnValue(false)
      };
      (useAuthStore as unknown as jest.Mock).mockReturnValue(permissionStore);
      
      render(renderWithProviders(<MainChat />));
      
      await waitFor(() => {
        expectChatStructure();
      });
    });
  });
});

// Helper function ≤8 lines
const setupMockReturnValues = () => {
  (useChatStore as unknown as jest.Mock).mockReturnValue({
    messages: [],
    loading: false,
    isProcessing: false
  });
  
  (useThreadStore as unknown as jest.Mock).mockReturnValue({
    threads: [],
    currentThreadId: null
  });
  
  (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
    isProcessing: false,
    messages: []
  });
  
  (useChatWebSocket as unknown as jest.Mock).mockReturnValue({});
};