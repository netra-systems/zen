import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AdminChat } from '@/components/admin/AdminChat';
import { useAuthStore } from '@/store/auth';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';

// Mock dependencies
jest.mock('@/store/auth');
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useChatWebSocket');
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  )
}));
jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, variant }: any) => (
    <span data-testid="badge" data-variant={variant}>{children}</span>
  )
}));

describe('AdminChat Component', () => {
  const mockAuthStore = {
    user: {
      id: 'admin-123',
      email: 'admin@netra.ai',
      role: 'admin',
      permissions: ['admin_chat', 'user_management', 'system_monitoring']
    },
    isAuthenticated: true,
    hasPermission: jest.fn()
  };

  const mockChatStore = {
    messages: [],
    isProcessing: false,
    adminMessages: [],
    systemMetrics: null,
    addAdminMessage: jest.fn(),
    sendAdminCommand: jest.fn(),
    clearAdminMessages: jest.fn(),
    updateSystemMetrics: jest.fn()
  };

  const mockWebSocket = {
    connected: true,
    error: null,
    sendMessage: jest.fn(),
    onMessage: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockChatStore);
    (useChatWebSocket as jest.Mock).mockReturnValue(mockWebSocket);
    mockAuthStore.hasPermission.mockImplementation((permission) => 
      mockAuthStore.user.permissions.includes(permission)
    );
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(
      <WebSocketProvider>
        {component}
      </WebSocketProvider>
    );
  };

  describe('Access Control and Privileges', () => {
    it('should render admin interface for users with admin privileges', () => {
      renderWithProvider(<AdminChat />);
      
      expect(screen.getByTestId('admin-chat-container')).toBeInTheDocument();
      expect(screen.getByText(/admin control panel/i)).toBeInTheDocument();
    });

    it('should deny access for non-admin users', () => {
      const nonAdminStore = {
        ...mockAuthStore,
        user: {
          ...mockAuthStore.user,
          role: 'user',
          permissions: ['chat_access']
        }
      };
      
      (useAuthStore as jest.Mock).mockReturnValue(nonAdminStore);
      nonAdminStore.hasPermission.mockReturnValue(false);

      renderWithProvider(<AdminChat />);
      
      expect(screen.getByText(/access denied/i)).toBeInTheDocument();
      expect(screen.queryByTestId('admin-chat-container')).not.toBeInTheDocument();
    });

    it('should show different UI elements based on specific permissions', () => {
      renderWithProvider(<AdminChat />);
      
      // Should show user management section if permission exists
      expect(screen.getByTestId('user-management-section')).toBeInTheDocument();
      
      // Should show system monitoring if permission exists
      expect(screen.getByTestId('system-monitoring-section')).toBeInTheDocument();
    });

    it('should hide sensitive features without proper permissions', () => {
      const limitedAdminStore = {
        ...mockAuthStore,
        user: {
          ...mockAuthStore.user,
          permissions: ['admin_chat'] // Only basic admin chat, no other permissions
        }
      };
      
      (useAuthStore as jest.Mock).mockReturnValue(limitedAdminStore);
      limitedAdminStore.hasPermission.mockImplementation((permission) => 
        limitedAdminStore.user.permissions.includes(permission)
      );

      renderWithProvider(<AdminChat />);
      
      expect(screen.queryByTestId('user-management-section')).not.toBeInTheDocument();
      expect(screen.queryByTestId('system-monitoring-section')).not.toBeInTheDocument();
    });

    it('should validate session and re-check permissions periodically', async () => {
      const { rerender } = renderWithProvider(<AdminChat />);
      
      expect(mockAuthStore.hasPermission).toHaveBeenCalledWith('admin_chat');
      
      // Simulate session refresh
      const updatedStore = {
        ...mockAuthStore,
        user: { ...mockAuthStore.user, sessionId: 'new-session' }
      };
      
      (useAuthStore as jest.Mock).mockReturnValue(updatedStore);
      rerender(
        <WebSocketProvider>
          <AdminChat />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(updatedStore.hasPermission).toHaveBeenCalled();
      });
    });

    it('should handle permission escalation attempts gracefully', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      
      renderWithProvider(<AdminChat />);
      
      // Try to access restricted endpoint
      const restrictedButton = screen.getByTestId('restricted-action-btn');
      await userEvent.click(restrictedButton);
      
      // Should log security warning
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Unauthorized access attempt')
      );
      
      consoleErrorSpy.mockRestore();
    });

    it('should audit admin actions', async () => {
      const auditSpy = jest.fn();
      jest.doMock('@/services/auditService', () => ({ logAdminAction: auditSpy }));
      
      renderWithProvider(<AdminChat />);
      
      const adminCommand = screen.getByTestId('admin-command-input');
      await userEvent.type(adminCommand, '/system status');
      
      const sendButton = screen.getByTestId('send-command-btn');
      await userEvent.click(sendButton);
      
      await waitFor(() => {
        expect(mockChatStore.sendAdminCommand).toHaveBeenCalledWith('/system status');
      });
    });

    it('should enforce rate limiting for admin commands', async () => {
      renderWithProvider(<AdminChat />);
      
      const commandInput = screen.getByTestId('admin-command-input');
      const sendButton = screen.getByTestId('send-command-btn');
      
      // Send multiple commands rapidly
      for (let i = 0; i < 5; i++) {
        await userEvent.type(commandInput, `/command${i}`);
        await userEvent.click(sendButton);
        await userEvent.clear(commandInput);
      }
      
      // Should show rate limit warning
      expect(screen.getByText(/rate limit exceeded/i)).toBeInTheDocument();
      expect(sendButton).toBeDisabled();
    });

    it('should handle role changes during session', async () => {
      const { rerender } = renderWithProvider(<AdminChat />);
      
      // Initially admin
      expect(screen.getByTestId('admin-chat-container')).toBeInTheDocument();
      
      // Role downgrade
      const downgradedStore = {
        ...mockAuthStore,
        user: { ...mockAuthStore.user, role: 'user', permissions: [] }
      };
      
      (useAuthStore as jest.Mock).mockReturnValue(downgradedStore);
      downgradedStore.hasPermission.mockReturnValue(false);
      
      rerender(
        <WebSocketProvider>
          <AdminChat />
        </WebSocketProvider>
      );
      
      expect(screen.getByText(/access denied/i)).toBeInTheDocument();
      expect(screen.queryByTestId('admin-chat-container')).not.toBeInTheDocument();
    });
  });

  describe('Admin Commands and Controls', () => {
    it('should display available admin commands', () => {
      renderWithProvider(<AdminChat />);
      
      const commandHelp = screen.getByTestId('command-help-section');
      expect(commandHelp).toBeInTheDocument();
      
      expect(screen.getByText('/system status')).toBeInTheDocument();
      expect(screen.getByText('/user list')).toBeInTheDocument();
      expect(screen.getByText('/metrics')).toBeInTheDocument();
    });

    it('should execute system status command', async () => {
      renderWithProvider(<AdminChat />);
      
      const commandInput = screen.getByTestId('admin-command-input');
      await userEvent.type(commandInput, '/system status');
      
      const sendButton = screen.getByTestId('send-command-btn');
      await userEvent.click(sendButton);
      
      expect(mockChatStore.sendAdminCommand).toHaveBeenCalledWith('/system status');
      expect(mockWebSocket.sendMessage).toHaveBeenCalledWith({
        type: 'admin_command',
        payload: { command: '/system status' }
      });
    });

    it('should handle user management commands', async () => {
      renderWithProvider(<AdminChat />);
      
      const commandInput = screen.getByTestId('admin-command-input');
      await userEvent.type(commandInput, '/user ban user@example.com');
      
      const sendButton = screen.getByTestId('send-command-btn');
      await userEvent.click(sendButton);
      
      // Should show confirmation dialog
      expect(screen.getByText(/confirm user ban/i)).toBeInTheDocument();
      
      const confirmButton = screen.getByTestId('confirm-action-btn');
      await userEvent.click(confirmButton);
      
      expect(mockChatStore.sendAdminCommand).toHaveBeenCalledWith('/user ban user@example.com');
    });

    it('should validate command syntax', async () => {
      renderWithProvider(<AdminChat />);
      
      const commandInput = screen.getByTestId('admin-command-input');
      await userEvent.type(commandInput, 'invalid command');
      
      const sendButton = screen.getByTestId('send-command-btn');
      await userEvent.click(sendButton);
      
      expect(screen.getByText(/invalid command syntax/i)).toBeInTheDocument();
      expect(mockChatStore.sendAdminCommand).not.toHaveBeenCalled();
    });

    it('should provide command autocomplete', async () => {
      renderWithProvider(<AdminChat />);
      
      const commandInput = screen.getByTestId('admin-command-input');
      await userEvent.type(commandInput, '/sys');
      
      // Should show autocomplete suggestions
      const autocomplete = screen.getByTestId('command-autocomplete');
      expect(autocomplete).toBeInTheDocument();
      expect(screen.getByText('/system status')).toBeInTheDocument();
      
      // Select suggestion
      const suggestion = screen.getByText('/system status');
      await userEvent.click(suggestion);
      
      expect(commandInput).toHaveValue('/system status');
    });

    it('should handle command history navigation', async () => {
      renderWithProvider(<AdminChat />);
      
      const commandInput = screen.getByTestId('admin-command-input');
      
      // Execute a few commands
      await userEvent.type(commandInput, '/system status');
      await userEvent.press(commandInput, 'Enter');
      await userEvent.clear(commandInput);
      
      await userEvent.type(commandInput, '/user list');
      await userEvent.press(commandInput, 'Enter');
      await userEvent.clear(commandInput);
      
      // Navigate history with arrow keys
      await userEvent.press(commandInput, 'ArrowUp');
      expect(commandInput).toHaveValue('/user list');
      
      await userEvent.press(commandInput, 'ArrowUp');
      expect(commandInput).toHaveValue('/system status');
    });

    it('should display command execution results', async () => {
      const chatStoreWithMessages = {
        ...mockChatStore,
        adminMessages: [
          {
            id: '1',
            type: 'command_result',
            command: '/system status',
            result: {
              status: 'healthy',
              uptime: '24h 30m',
              memory_usage: '2.4GB'
            },
            timestamp: new Date().toISOString()
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(chatStoreWithMessages);
      
      renderWithProvider(<AdminChat />);
      
      const resultSection = screen.getByTestId('command-results');
      expect(resultSection).toBeInTheDocument();
      
      expect(screen.getByText('System Status: healthy')).toBeInTheDocument();
      expect(screen.getByText('Uptime: 24h 30m')).toBeInTheDocument();
      expect(screen.getByText('Memory: 2.4GB')).toBeInTheDocument();
    });

    it('should handle command errors gracefully', async () => {
      const chatStoreWithError = {
        ...mockChatStore,
        adminMessages: [
          {
            id: '1',
            type: 'command_error',
            command: '/invalid command',
            error: 'Command not found',
            timestamp: new Date().toISOString()
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(chatStoreWithError);
      
      renderWithProvider(<AdminChat />);
      
      expect(screen.getByText(/command not found/i)).toBeInTheDocument();
      expect(screen.getByTestId('error-message')).toHaveClass('text-red-500');
    });
  });

  describe('Real-time System Monitoring', () => {
    it('should display system metrics dashboard', () => {
      const chatStoreWithMetrics = {
        ...mockChatStore,
        systemMetrics: {
          cpu_usage: 45.2,
          memory_usage: 68.5,
          active_connections: 234,
          message_throughput: 127,
          error_rate: 0.02,
          uptime: 86400
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(chatStoreWithMetrics);
      
      renderWithProvider(<AdminChat />);
      
      const metricsPanel = screen.getByTestId('system-metrics-panel');
      expect(metricsPanel).toBeInTheDocument();
      
      expect(screen.getByText('CPU: 45.2%')).toBeInTheDocument();
      expect(screen.getByText('Memory: 68.5%')).toBeInTheDocument();
      expect(screen.getByText('Connections: 234')).toBeInTheDocument();
    });

    it('should update metrics in real-time via WebSocket', async () => {
      const { rerender } = renderWithProvider(<AdminChat />);
      
      // Initial metrics
      const initialMetrics = {
        ...mockChatStore,
        systemMetrics: { cpu_usage: 30.0, memory_usage: 50.0 }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(initialMetrics);
      rerender(
        <WebSocketProvider>
          <AdminChat />
        </WebSocketProvider>
      );
      
      expect(screen.getByText('CPU: 30.0%')).toBeInTheDocument();
      
      // Updated metrics
      const updatedMetrics = {
        ...mockChatStore,
        systemMetrics: { cpu_usage: 75.5, memory_usage: 85.2 }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(updatedMetrics);
      rerender(
        <WebSocketProvider>
          <AdminChat />
        </WebSocketProvider>
      );
      
      expect(screen.getByText('CPU: 75.5%')).toBeInTheDocument();
      expect(screen.getByText('Memory: 85.2%')).toBeInTheDocument();
    });

    it('should highlight critical metrics with alerts', () => {
      const criticalMetrics = {
        ...mockChatStore,
        systemMetrics: {
          cpu_usage: 95.5,
          memory_usage: 98.2,
          error_rate: 0.15,
          active_connections: 1000
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(criticalMetrics);
      
      renderWithProvider(<AdminChat />);
      
      // High CPU usage should be highlighted
      const cpuMetric = screen.getByTestId('cpu-metric');
      expect(cpuMetric).toHaveClass('bg-red-100', 'text-red-800');
      
      // High error rate should show alert badge
      expect(screen.getByTestId('error-rate-alert')).toBeInTheDocument();
    });

    it('should show historical metrics trends', () => {
      const metricsWithHistory = {
        ...mockChatStore,
        systemMetrics: {
          cpu_usage: 45.2,
          memory_usage: 68.5,
          history: {
            cpu_usage: [30, 35, 40, 45.2],
            memory_usage: [60, 62, 65, 68.5]
          }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(metricsWithHistory);
      
      renderWithProvider(<AdminChat />);
      
      const trendsSection = screen.getByTestId('metrics-trends');
      expect(trendsSection).toBeInTheDocument();
      
      // Should show trend indicators
      expect(screen.getByTestId('cpu-trend-up')).toBeInTheDocument();
      expect(screen.getByTestId('memory-trend-up')).toBeInTheDocument();
    });
  });

  describe('User Session Management', () => {
    it('should display active user sessions', () => {
      const chatStoreWithSessions = {
        ...mockChatStore,
        activeSessions: [
          {
            id: 'session-1',
            userId: 'user-123',
            email: 'user@example.com',
            connected: true,
            lastActivity: new Date().toISOString(),
            ipAddress: '192.168.1.100'
          },
          {
            id: 'session-2',
            userId: 'user-456',
            email: 'user2@example.com',
            connected: false,
            lastActivity: new Date(Date.now() - 300000).toISOString(),
            ipAddress: '192.168.1.101'
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(chatStoreWithSessions);
      
      renderWithProvider(<AdminChat />);
      
      const sessionsPanel = screen.getByTestId('active-sessions-panel');
      expect(sessionsPanel).toBeInTheDocument();
      
      expect(screen.getByText('user@example.com')).toBeInTheDocument();
      expect(screen.getByText('user2@example.com')).toBeInTheDocument();
      
      // Should show connection status
      const connectedBadge = screen.getByTestId('session-1-status');
      expect(connectedBadge).toHaveAttribute('data-variant', 'success');
      
      const disconnectedBadge = screen.getByTestId('session-2-status');
      expect(disconnectedBadge).toHaveAttribute('data-variant', 'secondary');
    });

    it('should allow terminating user sessions', async () => {
      const chatStoreWithSessions = {
        ...mockChatStore,
        activeSessions: [
          {
            id: 'session-1',
            userId: 'user-123',
            email: 'user@example.com',
            connected: true
          }
        ],
        terminateSession: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(chatStoreWithSessions);
      
      renderWithProvider(<AdminChat />);
      
      const terminateButton = screen.getByTestId('terminate-session-1');
      await userEvent.click(terminateButton);
      
      // Should show confirmation
      expect(screen.getByText(/terminate session for user@example.com/i)).toBeInTheDocument();
      
      const confirmButton = screen.getByTestId('confirm-terminate');
      await userEvent.click(confirmButton);
      
      expect(chatStoreWithSessions.terminateSession).toHaveBeenCalledWith('session-1');
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle WebSocket disconnection gracefully', () => {
      const disconnectedWebSocket = {
        ...mockWebSocket,
        connected: false,
        error: new Error('Connection lost')
      };
      
      (useChatWebSocket as jest.Mock).mockReturnValue(disconnectedWebSocket);
      
      renderWithProvider(<AdminChat />);
      
      expect(screen.getByTestId('connection-status')).toHaveTextContent('Disconnected');
      expect(screen.getByTestId('reconnect-button')).toBeInTheDocument();
    });

    it('should retry failed admin commands', async () => {
      renderWithProvider(<AdminChat />);
      
      const commandInput = screen.getByTestId('admin-command-input');
      await userEvent.type(commandInput, '/system status');
      
      // Mock command failure
      mockChatStore.sendAdminCommand.mockRejectedValueOnce(new Error('Command failed'));
      
      const sendButton = screen.getByTestId('send-command-btn');
      await userEvent.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText(/command failed/i)).toBeInTheDocument();
      });
      
      const retryButton = screen.getByTestId('retry-command-btn');
      await userEvent.click(retryButton);
      
      expect(mockChatStore.sendAdminCommand).toHaveBeenCalledTimes(2);
    });

    it('should maintain command history across errors', async () => {
      renderWithProvider(<AdminChat />);
      
      const commandInput = screen.getByTestId('admin-command-input');
      
      // Execute successful command
      await userEvent.type(commandInput, '/system status');
      await userEvent.press(commandInput, 'Enter');
      
      // Execute failed command
      mockChatStore.sendAdminCommand.mockRejectedValueOnce(new Error('Failed'));
      await userEvent.clear(commandInput);
      await userEvent.type(commandInput, '/invalid');
      await userEvent.press(commandInput, 'Enter');
      
      // History should still contain successful command
      await userEvent.clear(commandInput);
      await userEvent.press(commandInput, 'ArrowUp');
      await userEvent.press(commandInput, 'ArrowUp');
      
      expect(commandInput).toHaveValue('/system status');
    });
  });

  describe('Accessibility and Keyboard Navigation', () => {
    it('should support keyboard navigation through admin controls', async () => {
      renderWithProvider(<AdminChat />);
      
      const commandInput = screen.getByTestId('admin-command-input');
      commandInput.focus();
      
      // Tab through controls
      await userEvent.tab();
      expect(screen.getByTestId('send-command-btn')).toHaveFocus();
      
      await userEvent.tab();
      expect(screen.getByTestId('clear-messages-btn')).toHaveFocus();
    });

    it('should have proper ARIA labels and roles', () => {
      renderWithProvider(<AdminChat />);
      
      const adminPanel = screen.getByRole('region', { name: /admin control panel/i });
      expect(adminPanel).toBeInTheDocument();
      
      const commandInput = screen.getByLabelText(/admin command input/i);
      expect(commandInput).toBeInTheDocument();
      
      const metricsTable = screen.getByRole('table', { name: /system metrics/i });
      expect(metricsTable).toBeInTheDocument();
    });

    it('should announce important status changes to screen readers', async () => {
      renderWithProvider(<AdminChat />);
      
      const statusRegion = screen.getByRole('status');
      expect(statusRegion).toBeInTheDocument();
      
      // Simulate command execution
      const commandInput = screen.getByTestId('admin-command-input');
      await userEvent.type(commandInput, '/system status');
      await userEvent.press(commandInput, 'Enter');
      
      await waitFor(() => {
        expect(statusRegion).toHaveTextContent(/command executed/i);
      });
    });
  });
});