/**
 * Initial State Integration Tests for Netra Apex Frontend
 * Critical for user onboarding and conversion - Phase 2, Agent 4
 * Tests default store state, localStorage, cookies, WebSocket connections, and UI visibility
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { TestProviders } from '../setup/test-providers';
import { useAppStore } from '@/store/app';
import { AppWithLayout } from '@/components/AppWithLayout';
import {
  setupInitialStateMocks,
  validateStorageAccess,
  validateCookieAccess,
  InitialStateTestComponent,
  WebSocketConnectionComponent
} from '../helpers/initial-state-helpers';
import.*from '@/__tests__/helpers/initial-state-storage-helpers';
import.*from '@/__tests__/helpers/initial-state-mock-components';

// Setup all mocks
setupInitialStateMockComponents();

describe('Initial State Integration Tests', () => {
  beforeEach(() => {
    setupInitialStateMocks();
  });

  describe('Default Store State', () => {
    it('should initialize app store with default values', () => {
      const TestComponent = () => {
        const store = useAppStore();
        return (
          <div data-testid="test-component">
            Sidebar collapsed: {store.isSidebarCollapsed.toString()}
          </div>
        );
      };
      
      render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      expect(useAppStore).toHaveBeenCalled();
      expect(screen.getByTestId('test-component')).toBeInTheDocument();
    });

    it('should provide sidebar toggle functionality', async () => {
      const mockToggle = jest.fn();
      jest.mocked(useAppStore).mockReturnValue({
        isSidebarCollapsed: false,
        toggleSidebar: mockToggle
      });
      
      render(
        <TestProviders>
          <AppWithLayout>
            <div>Test Content</div>
          </AppWithLayout>
        </TestProviders>
      );
      
      const toggleButton = screen.getByTestId('toggle-sidebar');
      expect(toggleButton).toBeInTheDocument();
      
      const user = userEvent.setup();
      await user.click(toggleButton);
      
      expect(mockToggle).toHaveBeenCalled();
    });

    it('should render sidebar by default when not collapsed', () => {
      jest.mocked(useAppStore).mockReturnValue({
        isSidebarCollapsed: false,
        toggleSidebar: jest.fn()
      });
      
      render(
        <TestProviders>
          <AppWithLayout>
            <div>Test Content</div>
          </AppWithLayout>
        </TestProviders>
      );
      
      expect(screen.getByTestId('chat-sidebar')).toBeInTheDocument();
    });

    it('should handle hydration state correctly', async () => {
      render(
        <TestProviders>
          <AppWithLayout>
            <div data-testid="main-content">Main Content</div>
          </AppWithLayout>
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('main-content')).toBeInTheDocument();
      });
    });
  });

  describe('LocalStorage Checks', () => {
    beforeEach(() => {
      setupStorageTestMocks();
    });

    it('should access localStorage without errors', () => {
      validateStorageAccess();
      
      render(
        <TestProviders>
          <InitialStateTestComponent testType="localStorage" />
        </TestProviders>
      );
      
      expect(screen.queryByTestId('state-errors')).not.toBeInTheDocument();
    });

    it('should handle persisted app state from localStorage', () => {
      const savedState = JSON.stringify({ isSidebarCollapsed: true });
      window.localStorage.setItem('app-storage', savedState);
      
      render(
        <TestProviders>
          <InitialStateTestComponent testType="localStorage" />
        </TestProviders>
      );
      
      expect(localStorage.getItem).toHaveBeenCalledWith('app-storage');
      expect(screen.getByTestId('state-loaded')).toBeInTheDocument();
    });

    it('should handle corrupted localStorage gracefully', () => {
      window.localStorage.setItem('app-storage', 'invalid-json');
      
      render(
        <TestProviders>
          <InitialStateTestComponent testType="localStorage" />
        </TestProviders>
      );
      
      expect(screen.getByTestId('state-errors')).toBeInTheDocument();
    });
  });

  describe('Cookie Validation', () => {
    beforeEach(() => {
      setupCookieTestMocks();
    });

    it('should access cookies without errors', () => {
      validateCookieAccess();
      
      render(
        <TestProviders>
          <InitialStateTestComponent testType="cookies" />
        </TestProviders>
      );
      
      expect(screen.getByTestId('state-loaded')).toBeInTheDocument();
    });

    it('should handle auth token cookie properly', () => {
      render(
        <TestProviders>
          <InitialStateTestComponent testType="cookies" />
        </TestProviders>
      );
      
      expect(screen.getByTestId('state-loaded')).toBeInTheDocument();
    });

    it('should handle malformed cookies gracefully', () => {
      Object.defineProperty(document, 'cookie', {
        writable: true,
        value: 'malformed;cookie;string;'
      });
      
      render(
        <TestProviders>
          <InitialStateTestComponent testType="cookies" />
        </TestProviders>
      );
      
      expect(screen.getByTestId('state-loaded')).toBeInTheDocument();
    });
  });

  describe('WebSocket Initial Connection Attempts', () => {
    it('should attempt WebSocket connection on initialization', async () => {
      render(
        <TestProviders>
          <WebSocketConnectionComponent />
        </TestProviders>
      );
      
      expect(screen.getByTestId('connection-state')).toHaveTextContent('connecting');
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-attempts')).toHaveTextContent('Attempts: 1');
      });
    });

    it('should handle WebSocket connection failure gracefully', async () => {
      const mockWebSocketService = require('@/services/webSocketService').webSocketService;
      mockWebSocketService.isConnected = jest.fn().mockReturnValue(false);
      
      render(
        <TestProviders>
          <WebSocketConnectionComponent />
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('failed');
        expect(screen.getByTestId('retry-connection')).toBeInTheDocument();
      });
    });

    it('should handle successful WebSocket connection', async () => {
      const mockWebSocketService = require('@/services/webSocketService').webSocketService;
      mockWebSocketService.isConnected = jest.fn().mockReturnValue(true);
      
      render(
        <TestProviders>
          <WebSocketConnectionComponent />
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
      });
      
      expect(screen.queryByTestId('retry-connection')).not.toBeInTheDocument();
    });
  });

  describe('UI Element Visibility', () => {
    it('should render essential UI elements on load', () => {
      render(
        <TestProviders>
          <AppWithLayout>
            <div data-testid="main-content">Content</div>
          </AppWithLayout>
        </TestProviders>
      );
      
      expect(screen.getByTestId('header')).toBeInTheDocument();
      expect(screen.getByTestId('main-content')).toBeInTheDocument();
    });

    it('should show sidebar when not collapsed', () => {
      jest.mocked(useAppStore).mockReturnValue({
        isSidebarCollapsed: false,
        toggleSidebar: jest.fn()
      });
      
      render(
        <TestProviders>
          <AppWithLayout>
            <div>Content</div>
          </AppWithLayout>
        </TestProviders>
      );
      
      expect(screen.getByTestId('chat-sidebar')).toBeInTheDocument();
    });

    it('should hide sidebar when collapsed', () => {
      jest.mocked(useAppStore).mockReturnValue({
        isSidebarCollapsed: true,
        toggleSidebar: jest.fn()
      });
      
      render(
        <TestProviders>
          <AppWithLayout>
            <div>Content</div>
          </AppWithLayout>
        </TestProviders>
      );
      
      expect(screen.queryByTestId('chat-sidebar')).not.toBeInTheDocument();
    });

    it('should handle responsive layout changes', async () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768
      });
      
      render(
        <TestProviders>
          <AppWithLayout>
            <div data-testid="responsive-content">Responsive Content</div>
          </AppWithLayout>
        </TestProviders>
      );
      
      expect(screen.getByTestId('responsive-content')).toBeInTheDocument();
      
      act(() => {
        window.innerWidth = 1200;
        window.dispatchEvent(new Event('resize'));
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('responsive-content')).toBeInTheDocument();
      });
    });
  });
});