import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AgentStatusPanel from '@/components/chat/AgentStatusPanel';
import { useUnifiedChatStore } from '@/store/unified-chat';

import { TestProviders } from '@/__tests__/test-utils/providers';

// Mock dependencies
jest.mock('@/store/unified-chat');

// Import real UI components
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

describe('AgentStatusPanel Component', () => {
  const mockUnifiedChatStore = {
    isProcessing: false,
    subAgentName: null,
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null
  };

  beforeEach(() => {
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });

    jest.clearAllMocks();
    jest.useFakeTimers();
    jest.mocked(useUnifiedChatStore).mockReturnValue(mockUnifiedChatStore);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(
      <TestProviders>
        {component}
      </TestProviders>
    );
  };

  describe('Agent Status Display', () => {
    it('should render the component when processing', () => {
      const activeStore = {
        ...mockUnifiedChatStore,
        isProcessing: true,
        subAgentName: 'Test Agent'
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(activeStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      // Check that the component renders
      expect(screen.getByText(/Current Phase/i)).toBeInTheDocument();
      expect(screen.getByText(/Test Agent/i)).toBeInTheDocument();
    });

    it('should not render when not processing', () => {
      const inactiveStore = {
        ...mockUnifiedChatStore,
        isProcessing: false
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(inactiveStore);
      
      const { container } = renderWithProvider(<AgentStatusPanel />);
      
      // Component should not render anything when not processing
      expect(container.firstChild).toBeNull();
    });

    it('should display processing state', () => {
      const activeStore = {
        ...mockUnifiedChatStore,
        isProcessing: true,
        subAgentName: 'Supervisor Agent'
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(activeStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByText(/Current Phase/i)).toBeInTheDocument();
      expect(screen.getByText(/Supervisor Agent/i)).toBeInTheDocument();
    });

    it('should show progress when layer data is available', () => {
      const activeStore = {
        ...mockUnifiedChatStore,
        isProcessing: true,
        subAgentName: 'Test Agent',
        fastLayerData: { activeTools: ['tool1'] },
        mediumLayerData: { status: 'processing' },
        slowLayerData: { phase: 'analysis' }
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(activeStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByText(/Overall Progress/i)).toBeInTheDocument();
      expect(screen.getByText(/3\/3/i)).toBeInTheDocument();
    });

    it('should display active tools', () => {
      const activeStore = {
        ...mockUnifiedChatStore,
        isProcessing: true,
        subAgentName: 'Test Agent',
        fastLayerData: { activeTools: ['search', 'analyze'] }
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(activeStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByText(/Active Tools/i)).toBeInTheDocument();
      expect(screen.getByText(/search, analyze/i)).toBeInTheDocument();
    });

    it('should handle null subAgent name', () => {
      const activeStore = {
        ...mockUnifiedChatStore,
        isProcessing: true,
        subAgentName: null
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(activeStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByText(/Current Phase/i)).toBeInTheDocument();
      expect(screen.getByText(/Initializing/i)).toBeInTheDocument();
    });
  });

  describe('Real-time Updates', () => {
    it('should update humor elements during processing', async () => {
      const activeStore = {
        ...mockUnifiedChatStore,
        isProcessing: true,
        subAgentName: 'Test Agent'
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(activeStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      // Check if humor text is present (any of the possible quips)
      const humorTexts = [
        /Optimizing the optimizers/i,
        /Teaching AI to be more intelligent/i,
        /Convincing the models to cooperate/i
      ];
      
      const hasHumorText = humorTexts.some(pattern => 
        screen.queryByText(pattern) !== null
      );
      
      expect(hasHumorText).toBe(true);
    });

    it('should display confidence indicator when available', async () => {
      const activeStore = {
        ...mockUnifiedChatStore,
        isProcessing: true,
        subAgentName: 'Test Agent'
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(activeStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      // Wait for metrics to be generated
      await act(async () => {
        jest.advanceTimersByTime(1000);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Analysis Confidence/i)).toBeInTheDocument();
      });
    });
  });

  describe('Performance and Optimization', () => {
    it('should cleanup timers on unmount', () => {
      const activeStore = {
        ...mockUnifiedChatStore,
        isProcessing: true,
        subAgentName: 'Test Agent'
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(activeStore);
      
      const { unmount } = renderWithProvider(<AgentStatusPanel />);
      
      // Should not throw errors when unmounting
      expect(() => unmount()).not.toThrow();
    });

    it('should handle component re-renders efficiently', () => {
      const activeStore = {
        ...mockUnifiedChatStore,
        isProcessing: true,
        subAgentName: 'Test Agent'
      };
      
      jest.mocked(useUnifiedChatStore).mockReturnValue(activeStore);
      
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Multiple re-renders should not cause issues
      expect(() => {
        rerender(
          <TestProviders>
            <AgentStatusPanel />
          </TestProviders>
        );
        rerender(
          <TestProviders>
            <AgentStatusPanel />
          </TestProviders>
        );
      }).not.toThrow();
    });
  });
});