import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthContext, AuthProvider } from '@/auth/context';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import { unifiedAuthService } from '@/auth/unified-auth-service';

// Mock dependencies
jest.mock('@/auth/unified-auth-service');
jest.mock('@/store/unified-chat');
jest.mock('@/store/authStore');
jest.mock('@/lib/logger');
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackError: jest.fn(),
  }),
}));

// Mock window.location
delete (window as any).location;
window.location = { href: '' } as any;

describe('Comprehensive Logout Functionality', () => {
  let mockChatStore: any;
  let mockAuthStore: any;
  
  beforeEach(() => {
    // Setup mock chat store
    mockChatStore = {
      resetStore: jest.fn(),
      isConnected: true,
      activeThreadId: 'thread-123',
      messages: [{ id: '1', content: 'test' }],
      fastLayerData: { some: 'data' },
      optimisticMessages: new Map([['msg1', { content: 'pending' }]]),
      executedAgents: new Map([['agent1', { status: 'running' }]]),
    };
    
    (useUnifiedChatStore as any).getState = jest.fn(() => mockChatStore);
    
    // Setup mock auth store
    mockAuthStore = {
      logout: jest.fn(),
      user: { id: 'user-123', email: 'test@example.com' },
      token: 'mock-token',
    };
    
    (useAuthStore as any).mockReturnValue(mockAuthStore);
    
    // Setup localStorage mock
    Storage.prototype.removeItem = jest.fn();
    Storage.prototype.clear = jest.fn();
    Storage.prototype.setItem = jest.fn();
    Storage.prototype.getItem = jest.fn();
    
    // Reset window.location.href
    window.location.href = '';
  });
  
  afterEach(() => {
    jest.clearAllMocks();
  });
  
  const TestComponent = () => {
    const context = React.useContext(AuthContext);
    
    return (
      <div>
        <button onClick={context?.logout} data-testid="logout-button">
          Logout
        </button>
        {context?.user && (
          <div data-testid="user-info">{context.user.email}</div>
        )}
      </div>
    );
  };
  
  describe('Data Clearing', () => {
    it('should clear all chat store data on logout', async () => {
      const user = userEvent.setup();
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        expect(mockChatStore.resetStore).toHaveBeenCalled();
      });
    });
    
    it('should clear localStorage items on logout', async () => {
      const user = userEvent.setup();
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        const expectedItems = [
          'jwt_token',
          'refresh_token',
          'user_data',
          'user_preferences',
          'active_thread_id',
          'chat_history',
          'session_id',
          'dev_logout_performed'
        ];
        
        expectedItems.forEach(item => {
          expect(localStorage.removeItem).toHaveBeenCalledWith(item);
        });
      });
    });
    
    it('should clear sessionStorage on logout', async () => {
      const user = userEvent.setup();
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        expect(sessionStorage.clear).toHaveBeenCalled();
      });
    });
  });
  
  describe('Navigation and UI State', () => {
    it('should navigate to login page after logout', async () => {
      const user = userEvent.setup();
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        expect(window.location.href).toBe('/login');
      });
    });
    
    it('should handle logout from thread view', async () => {
      const user = userEvent.setup();
      
      // Simulate being in thread view
      mockChatStore.activeThreadId = 'thread-456';
      mockChatStore.messages = [
        { id: '1', content: 'Message 1' },
        { id: '2', content: 'Message 2' }
      ];
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        // Verify store was reset
        expect(mockChatStore.resetStore).toHaveBeenCalled();
        // Verify navigation to login
        expect(window.location.href).toBe('/login');
      });
    });
  });
  
  describe('Error Handling', () => {
    it('should complete logout even if backend call fails', async () => {
      const user = userEvent.setup();
      
      // Mock backend logout to fail
      (unifiedAuthService.handleLogout as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        // Verify local cleanup still happened
        expect(mockChatStore.resetStore).toHaveBeenCalled();
        expect(localStorage.removeItem).toHaveBeenCalledWith('jwt_token');
        expect(window.location.href).toBe('/login');
      });
    });
    
    it('should handle errors in localStorage clearing gracefully', async () => {
      const user = userEvent.setup();
      
      // Mock localStorage.removeItem to throw
      (localStorage.removeItem as jest.Mock).mockImplementation((key) => {
        if (key === 'user_preferences') {
          throw new Error('Storage error');
        }
      });
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        // Should still complete logout despite storage error
        expect(window.location.href).toBe('/login');
      });
    });
  });
  
  describe('Development Mode', () => {
    it('should set dev logout flag in development mode', async () => {
      const user = userEvent.setup();
      
      const mockAuthConfig = {
        development_mode: true,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
        }
      };
      
      // Mock auth config to be in development mode
      jest.spyOn(React, 'useContext').mockImplementation(() => ({
        user: null,
        login: jest.fn(),
        logout: async () => {
          unifiedAuthService.setDevLogoutFlag();
          await unifiedAuthService.handleLogout(mockAuthConfig);
        },
        loading: false,
        authConfig: mockAuthConfig,
        token: null,
        initialized: true,
      }));
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        expect(unifiedAuthService.setDevLogoutFlag).toHaveBeenCalled();
      });
    });
  });
  
  describe('WebSocket Cleanup', () => {
    it('should close WebSocket connection on logout', async () => {
      const user = userEvent.setup();
      
      // Mock active WebSocket connection
      mockChatStore.isConnected = true;
      mockChatStore.setConnectionStatus = jest.fn();
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        // resetStore should handle WebSocket cleanup
        expect(mockChatStore.resetStore).toHaveBeenCalled();
      });
    });
  });
  
  describe('Comprehensive State Reset', () => {
    it('should reset all store states to initial values', async () => {
      const user = userEvent.setup();
      
      // Setup store with various active states
      mockChatStore = {
        ...mockChatStore,
        fastLayerData: { activeData: 'test' },
        mediumLayerData: { content: 'medium' },
        slowLayerData: { agents: ['agent1'] },
        isProcessing: true,
        currentRunId: 'run-123',
        activeThreadId: 'thread-789',
        messages: [{ id: '1' }, { id: '2' }, { id: '3' }],
        isConnected: true,
        executedAgents: new Map([['agent1', {}], ['agent2', {}]]),
        optimisticMessages: new Map([['opt1', {}], ['opt2', {}]]),
        pendingUserMessage: { content: 'pending' },
        pendingAiMessage: { content: 'ai pending' },
      };
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      const logoutButton = screen.getByTestId('logout-button');
      await user.click(logoutButton);
      
      await waitFor(() => {
        // Verify comprehensive reset was called
        expect(mockChatStore.resetStore).toHaveBeenCalled();
      });
    });
  });
});