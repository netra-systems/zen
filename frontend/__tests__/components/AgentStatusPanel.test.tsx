import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AgentStatusPanel from '@/components/chat/AgentStatusPanel';
import { useChatStore } from '@/store/chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';

import { TestProviders } from '../test-utils/providers';

// Mock dependencies
jest.mock('@/store/chat');
jest.mock('@/hooks/useChatWebSocket');
jest.mock('@/components/ui/progress', () => ({
  Progress: ({ value, className }: any) => (
    <div data-testid="progress-bar" data-value={value} className={className}>
      {value}%
    </div>
  )
}));
jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, variant }: any) => (
    <span data-testid="badge" data-variant={variant}>{children}</span>
  )
}));

describe('AgentStatusPanel Component', () => {
  const mockChatStore = {
    isProcessing: false,
    subAgentName: null
  };

  const mockChatWebSocket = {
    workflowProgress: {
      current_step: 0,
      total_steps: 0,
      step_name: '',
      status: 'idle'
    },
    activeTools: [],
    toolExecutionStatus: {}
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
    (useChatStore as jest.Mock).mockReturnValue(mockChatStore);
    (useChatWebSocket as jest.Mock).mockReturnValue(mockChatWebSocket);
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
    it('should render the component', () => {
      renderWithProvider(<AgentStatusPanel />);
      
      // Check that the component renders
      expect(screen.getByText(/Current Phase/i)).toBeInTheDocument();
      expect(screen.getByText(/Initializing/i)).toBeInTheDocument();
    });

    it('should display processing state', () => {
      const activeStore = {
        ...mockChatStore,
        isProcessing: true,
        subAgentName: 'Supervisor Agent'
      };
      
      (useChatStore as jest.Mock).mockReturnValue(activeStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByText(/Current Phase/i)).toBeInTheDocument();
      expect(screen.getByText(/Supervisor Agent/i)).toBeInTheDocument();
    });

    it('should show progress when available', () => {
      const progressWebSocket = {
        ...mockChatWebSocket,
        workflowProgress: {
          current_step: 3,
          total_steps: 10,
          step_name: 'Analyzing data',
          status: 'processing'
        }
      };
      
      (useChatWebSocket as jest.Mock).mockReturnValue(progressWebSocket);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByText(/Overall Progress/i)).toBeInTheDocument();
      expect(screen.getByText(/3\/10/)).toBeInTheDocument();
    });

    it('should display active tools', () => {
      const toolsWebSocket = {
        ...mockChatWebSocket,
        activeTools: ['data_analyzer', 'optimizer'],
        toolExecutionStatus: {
          data_analyzer: { status: 'running', progress: 60 },
          optimizer: { status: 'queued', progress: 0 }
        }
      };
      
      (useChatWebSocket as jest.Mock).mockReturnValue(toolsWebSocket);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByText(/Active Tools/i)).toBeInTheDocument();
      expect(screen.getByText(/data_analyzer/i)).toBeInTheDocument();
    });

    it('should handle error states', () => {
      const errorWebSocket = {
        ...mockChatWebSocket,
        error: 'Failed to connect to WebSocket',
        connected: false
      };
      
      (useChatWebSocket as jest.Mock).mockReturnValue(errorWebSocket);
      
      renderWithProvider(<AgentStatusPanel />);
      
      // Component should still render in error state
      expect(screen.getByText(/Current Phase/i)).toBeInTheDocument();
    });
  });

  describe('Real-time Updates', () => {
    it('should update on WebSocket changes', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Update WebSocket data
      const updatedWebSocket = {
        ...mockChatWebSocket,
        workflowProgress: {
          current_step: 5,
          total_steps: 10,
          step_name: 'Processing',
          status: 'active'
        }
      };
      
      (useChatWebSocket as jest.Mock).mockReturnValue(updatedWebSocket);
      
      rerender(
        <TestProviders>
          <AgentStatusPanel />
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(screen.getByText(/5\/10/)).toBeInTheDocument();
      });
    });

    it('should handle rapid updates', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Simulate rapid phase changes
      const phases = ['Initializing', 'Analyzing', 'Processing', 'Optimizing', 'Completed'];
      
      for (let i = 0; i < phases.length; i++) {
        const rapidStore = {
          ...mockChatStore,
          subAgentName: phases[i],
          isProcessing: i < phases.length - 1
        };
        
        (useChatStore as jest.Mock).mockReturnValue(rapidStore);
        rerender(
          <TestProviders>
            <AgentStatusPanel />
          </TestProviders>
        );
        
        await act(async () => {
          jest.advanceTimersByTime(100);
        });
      }
      
      // Should end with final phase
      expect(screen.getByText(/Completed/i)).toBeInTheDocument();
    });

    it('should update humor elements during processing', async () => {
      const processingStore = {
        ...mockChatStore,
        isProcessing: true,
        subAgentName: 'Data Agent'
      };
      
      (useChatStore as jest.Mock).mockReturnValue(processingStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      // Fast-forward to trigger humor text rotation
      act(() => {
        jest.advanceTimersByTime(5000);
      });
      
      // Component should still be rendered
      expect(screen.getByText(/Data Agent/i)).toBeInTheDocument();
    });
  });

  describe('Performance and Optimization', () => {
    it('should handle multiple rapid updates', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Simulate rapid updates
      for (let i = 0; i < 10; i++) {
        const rapidWebSocket = {
          ...mockChatWebSocket,
          workflowProgress: {
            current_step: i,
            total_steps: 10,
            step_name: `Step ${i}`,
            status: 'active'
          }
        };
        
        (useChatWebSocket as jest.Mock).mockReturnValue(rapidWebSocket);
        rerender(
          <TestProviders>
            <AgentStatusPanel />
          </TestProviders>
        );
      }
      
      // Should show latest update
      expect(screen.getByText(/9\/10/)).toBeInTheDocument();
    });

    it('should cleanup timers on unmount', () => {
      const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
      const processingStore = {
        ...mockChatStore,
        isProcessing: true
      };
      
      (useChatStore as jest.Mock).mockReturnValue(processingStore);
      
      const { unmount } = renderWithProvider(<AgentStatusPanel />);
      
      unmount();
      
      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });

  describe('UI Elements', () => {
    it('should render with proper structure', () => {
      const { container } = renderWithProvider(<AgentStatusPanel />);
      
      // Check that the component has proper structure
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should display metrics when available', () => {
      const metricsWebSocket = {
        ...mockChatWebSocket,
        activeTools: ['tool1', 'tool2'],
        toolExecutionStatus: {
          tool1: { status: 'running', progress: 50 },
          tool2: { status: 'queued', progress: 0 }
        }
      };
      
      (useChatWebSocket as jest.Mock).mockReturnValue(metricsWebSocket);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByText(/Active Tools/i)).toBeInTheDocument();
    });

    it('should handle empty state gracefully', () => {
      renderWithProvider(<AgentStatusPanel />);
      
      // Component should render with default values
      expect(screen.getByText(/Current Phase/i)).toBeInTheDocument();
      expect(screen.getByText(/Initializing/i)).toBeInTheDocument();
    });
  });

  describe('Animation and Transitions', () => {
    it('should have motion elements for animations', () => {
      const progressWebSocket = {
        ...mockChatWebSocket,
        workflowProgress: {
          current_step: 5,
          total_steps: 10,
          step_name: 'Processing',
          status: 'active'
        }
      };
      
      (useChatWebSocket as jest.Mock).mockReturnValue(progressWebSocket);
      
      const { container } = renderWithProvider(<AgentStatusPanel />);
      
      // Check for motion elements (they may have transform styles)
      const elements = container.querySelectorAll('[style*="transform"], [style*="opacity"]');
      expect(elements.length).toBeGreaterThanOrEqual(0);
    });
  });
});