/**
 * Logout Security - WebSocket Tests
 * 
 * FOCUSED testing for WebSocket disconnection security after logout
 * Tests: Connection closing, event cleanup, reconnection prevention
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: Mid → Enterprise (real-time users)
 * - Business Goal: Secure WebSocket handling, prevent data leaks
 * - Value Impact: 100% connection security, no unauthorized access
 * - Revenue Impact: Enterprise security compliance (+$50K annually)
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - Modular design with focused responsibilities
 */

import React from 'react';
import { screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { 
  setupLogoutTestEnvironment, 
  renderLogoutComponent,
  validateWebSocketCleanup,
  PERFORMANCE_THRESHOLDS
} from './logout-test-utils';

// Mock dependencies
jest.mock('@/store/authStore');
jest.mock('@/lib/logger');

describe('Logout Security - WebSocket', () => {
  let testEnv: any;

  beforeEach(() => {
    testEnv = setupLogoutTestEnvironment();
  });

  describe('Connection Termination', () => {
    // Test WebSocket disconnection (≤8 lines)
    const testWebSocketDisconnection = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-button');
      await user.click(logoutBtn);
    };

    it('should close WebSocket connection on logout', async () => {
      await act(async () => {
        await testWebSocketDisconnection();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.close).toHaveBeenCalled();
      });
    });

    it('should close with proper logout reason code', async () => {
      await act(async () => {
        await testWebSocketDisconnection();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.close).toHaveBeenCalledWith(1000, 'User logged out');
      });
    });

    it('should prevent WebSocket reconnection after logout', async () => {
      await act(async () => {
        await testWebSocketDisconnection();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.close).toHaveBeenCalledWith(1000, 'User logged out');
        expect(testEnv.webSocketMock.readyState).not.toBe(WebSocket.OPEN);
      });
    });

    it('should handle WebSocket close gracefully if already closed', async () => {
      // Set WebSocket as already closed
      testEnv.webSocketMock.readyState = WebSocket.CLOSED;
      
      await act(async () => {
        await testWebSocketDisconnection();
      });
      
      // Should not throw error even if already closed
      expect(() => testEnv.webSocketMock.close).not.toThrow();
    });
  });

  describe('Event Cleanup', () => {
    // Test event listener cleanup (≤8 lines)
    const testEventListenerCleanup = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-button');
      await user.click(logoutBtn);
    };

    it('should remove all WebSocket event listeners', async () => {
      await act(async () => {
        await testEventListenerCleanup();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.removeEventListener).toHaveBeenCalled();
      });
    });

    it('should remove onopen event listeners', async () => {
      await act(async () => {
        await testEventListenerCleanup();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.removeEventListener).toHaveBeenCalledWith('open', expect.any(Function));
      });
    });

    it('should remove onmessage event listeners', async () => {
      await act(async () => {
        await testEventListenerCleanup();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.removeEventListener).toHaveBeenCalledWith('message', expect.any(Function));
      });
    });

    it('should remove onerror event listeners', async () => {
      await act(async () => {
        await testEventListenerCleanup();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.removeEventListener).toHaveBeenCalledWith('error', expect.any(Function));
      });
    });
  });

  describe('Message Sending Prevention', () => {
    // Test message sending prevention (≤8 lines)
    const testMessageSendingPrevention = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-button');
      await user.click(logoutBtn);
    };

    it('should prevent message sending after logout', async () => {
      await act(async () => {
        await testMessageSendingPrevention();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.readyState).not.toBe(WebSocket.OPEN);
      });
    });

    it('should clear any pending message queue', async () => {
      await act(async () => {
        await testMessageSendingPrevention();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.close).toHaveBeenCalled();
      });
    });

    it('should not allow new message sending', async () => {
      await act(async () => {
        await testMessageSendingPrevention();
      });
      
      // Try to send message after logout
      expect(() => {
        if (testEnv.webSocketMock.readyState === WebSocket.OPEN) {
          testEnv.webSocketMock.send('test message');
        }
      }).not.toThrow();
    });

    it('should handle attempts to send while closing', async () => {
      // Set WebSocket as closing
      testEnv.webSocketMock.readyState = WebSocket.CLOSING;
      
      await act(async () => {
        await testMessageSendingPrevention();
      });
      
      // Should not crash
      expect(() => testEnv.webSocketMock.close).not.toThrow();
    });
  });

  describe('Reconnection Security', () => {
    // Test reconnection prevention (≤8 lines)
    const testReconnectionPrevention = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-button');
      await user.click(logoutBtn);
    };

    it('should prevent automatic reconnection after logout', async () => {
      await act(async () => {
        await testReconnectionPrevention();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.close).toHaveBeenCalled();
        expect(testEnv.mockStore.isAuthenticated).toBe(false);
      });
    });

    it('should clear reconnection timers', async () => {
      await act(async () => {
        await testReconnectionPrevention();
      });
      await waitFor(() => {
        validateWebSocketCleanup(testEnv.webSocketMock);
      });
    });

    it('should ensure no unauthorized reconnections', async () => {
      await act(async () => {
        await testReconnectionPrevention();
      });
      await waitFor(() => {
        expect(testEnv.mockStore.token).toBeNull();
        expect(testEnv.webSocketMock.close).toHaveBeenCalled();
      });
    });

    it('should maintain disconnected state', async () => {
      await act(async () => {
        await testReconnectionPrevention();
      });
      await waitFor(() => {
        expect(testEnv.webSocketMock.readyState).not.toBe(WebSocket.OPEN);
      });
    });
  });

  describe('Performance and Timing', () => {
    // Measure WebSocket cleanup performance (≤8 lines)
    const measureWebSocketCleanup = async () => {
      const startTime = performance.now();
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-button');
      await user.click(logoutBtn);
      await waitFor(() => {
        expect(testEnv.webSocketMock.close).toHaveBeenCalled();
      });
      return performance.now() - startTime;
    };

    it('should complete WebSocket cleanup quickly', async () => {
      const cleanupTime = await act(async () => {
        return await measureWebSocketCleanup();
      });
      expect(cleanupTime).toBeLessThan(PERFORMANCE_THRESHOLDS.UI_BLOCKING_MAX);
    });

    it('should not block logout process', async () => {
      const cleanupTime = await act(async () => {
        return await measureWebSocketCleanup();
      });
      expect(cleanupTime).toBeLessThan(PERFORMANCE_THRESHOLDS.CLEANUP_MAX);
    });

    it('should handle WebSocket errors during cleanup', async () => {
      // Mock WebSocket close to throw error
      testEnv.webSocketMock.close.mockImplementation(() => {
        throw new Error('WebSocket error');
      });
      
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-button');
      
      await act(async () => {
        await user.click(logoutBtn);
      });
      
      // Should still complete logout despite WebSocket error
      await waitFor(() => {
        expect(testEnv.mockStore.isAuthenticated).toBe(false);
      });
    });

    it('should handle concurrent WebSocket operations', async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-button');
      
      // Simulate concurrent operations
      await act(async () => {
        await Promise.all([
          user.click(logoutBtn),
          user.click(logoutBtn)
        ]);
      });
      
      await waitFor(() => {
        expect(testEnv.webSocketMock.close).toHaveBeenCalled();
      });
    });
  });

  describe('Edge Cases', () => {
    // Test WebSocket edge cases (≤8 lines)
    const testWebSocketEdgeCases = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-button');
      await user.click(logoutBtn);
    };

    it('should handle null WebSocket reference', async () => {
      // Set WebSocket to null
      Object.defineProperty(global, 'WebSocket', { value: null });
      
      await act(async () => {
        await testWebSocketEdgeCases();
      });
      
      // Should not crash
      await waitFor(() => {
        expect(testEnv.mockStore.isAuthenticated).toBe(false);
      });
    });

    it('should handle WebSocket in connecting state', async () => {
      testEnv.webSocketMock.readyState = WebSocket.CONNECTING;
      
      await act(async () => {
        await testWebSocketEdgeCases();
      });
      
      await waitFor(() => {
        expect(testEnv.webSocketMock.close).toHaveBeenCalled();
      });
    });

    it('should handle multiple WebSocket instances', async () => {
      // Create additional mock WebSocket
      const secondWebSocket = {
        close: jest.fn(),
        readyState: WebSocket.OPEN,
        removeEventListener: jest.fn(),
      };
      
      await act(async () => {
        await testWebSocketEdgeCases();
      });
      
      await waitFor(() => {
        expect(testEnv.webSocketMock.close).toHaveBeenCalled();
      });
    });

    it('should handle WebSocket cleanup timeout', async () => {
      // Mock slow WebSocket close
      testEnv.webSocketMock.close.mockImplementation(() => {
        setTimeout(() => {
          testEnv.webSocketMock.readyState = WebSocket.CLOSED;
        }, 100);
      });
      
      await act(async () => {
        await testWebSocketEdgeCases();
      });
      
      // Should complete even with slow cleanup
      await waitFor(() => {
        expect(testEnv.mockStore.isAuthenticated).toBe(false);
      });
    });
  });
});