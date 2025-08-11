import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgentStatusPanel } from '@/components/chat/AgentStatusPanel';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { WebSocketProvider } from '@/contexts/WebSocketContext';

// Mock dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useWebSocket');
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
    currentRunId: null,
    agentStatus: {
      supervisor: { status: 'idle', progress: 0, lastActivity: null },
      triage: { status: 'idle', progress: 0, lastActivity: null },
      data: { status: 'idle', progress: 0, lastActivity: null },
      optimizations_core: { status: 'idle', progress: 0, lastActivity: null },
      actions_to_meet_goals: { status: 'idle', progress: 0, lastActivity: null },
      reporting: { status: 'idle', progress: 0, lastActivity: null },
      synthetic_data: { status: 'idle', progress: 0, lastActivity: null }
    },
    systemMetrics: null,
    updateAgentStatus: jest.fn(),
    setProcessing: jest.fn()
  };

  const mockWebSocket = {
    connected: true,
    error: null,
    sendMessage: jest.fn(),
    lastMessage: null
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockChatStore);
    (useWebSocket as jest.Mock).mockReturnValue(mockWebSocket);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(
      <WebSocketProvider>
        {component}
      </WebSocketProvider>
    );
  };

  describe('Agent Status Display', () => {
    it('should render all agent status cards', () => {
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByTestId('agent-status-panel')).toBeInTheDocument();
      expect(screen.getByTestId('supervisor-status')).toBeInTheDocument();
      expect(screen.getByTestId('triage-status')).toBeInTheDocument();
      expect(screen.getByTestId('data-status')).toBeInTheDocument();
      expect(screen.getByTestId('optimizations_core-status')).toBeInTheDocument();
      expect(screen.getByTestId('actions_to_meet_goals-status')).toBeInTheDocument();
      expect(screen.getByTestId('reporting-status')).toBeInTheDocument();
      expect(screen.getByTestId('synthetic_data-status')).toBeInTheDocument();
    });

    it('should display idle status by default', () => {
      renderWithProvider(<AgentStatusPanel />);
      
      const supervisorCard = screen.getByTestId('supervisor-status');
      const supervisorBadge = within(supervisorCard).getByTestId('badge');
      
      expect(supervisorBadge).toHaveAttribute('data-variant', 'secondary');
      expect(supervisorBadge).toHaveTextContent('idle');
    });

    it('should update status when agents become active', () => {
      const activeAgentStore = {
        ...mockChatStore,
        isProcessing: true,
        currentRunId: 'run-123',
        agentStatus: {
          ...mockChatStore.agentStatus,
          supervisor: { 
            status: 'active', 
            progress: 25, 
            lastActivity: new Date().toISOString(),
            currentTask: 'Orchestrating workflow'
          },
          triage: { 
            status: 'thinking', 
            progress: 50, 
            lastActivity: new Date().toISOString(),
            currentTask: 'Analyzing user intent'
          }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(activeAgentStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const supervisorCard = screen.getByTestId('supervisor-status');
      const supervisorBadge = within(supervisorCard).getByTestId('badge');
      expect(supervisorBadge).toHaveAttribute('data-variant', 'success');
      expect(supervisorBadge).toHaveTextContent('active');
      
      const triageCard = screen.getByTestId('triage-status');
      const triageBadge = within(triageCard).getByTestId('badge');
      expect(triageBadge).toHaveAttribute('data-variant', 'warning');
      expect(triageBadge).toHaveTextContent('thinking');
    });

    it('should show progress bars for active agents', () => {
      const progressStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          data: { 
            status: 'processing', 
            progress: 75, 
            lastActivity: new Date().toISOString(),
            currentTask: 'Analyzing data patterns'
          }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(progressStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const dataCard = screen.getByTestId('data-status');
      const progressBar = within(dataCard).getByTestId('progress-bar');
      
      expect(progressBar).toHaveAttribute('data-value', '75');
      expect(progressBar).toHaveTextContent('75%');
    });

    it('should display current task descriptions', () => {
      const taskStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          optimizations_core: { 
            status: 'active', 
            progress: 60, 
            lastActivity: new Date().toISOString(),
            currentTask: 'Optimizing AI workload parameters',
            subtask: 'Analyzing GPU utilization patterns'
          }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(taskStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const optimizationCard = screen.getByTestId('optimizations_core-status');
      
      expect(within(optimizationCard).getByText('Optimizing AI workload parameters')).toBeInTheDocument();
      expect(within(optimizationCard).getByText('Analyzing GPU utilization patterns')).toBeInTheDocument();
    });

    it('should show error states with appropriate styling', () => {
      const errorStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          reporting: { 
            status: 'error', 
            progress: 0, 
            lastActivity: new Date().toISOString(),
            error: 'Failed to generate report: Database connection timeout',
            currentTask: null
          }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(errorStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const reportingCard = screen.getByTestId('reporting-status');
      const errorBadge = within(reportingCard).getByTestId('badge');
      
      expect(errorBadge).toHaveAttribute('data-variant', 'destructive');
      expect(errorBadge).toHaveTextContent('error');
      
      expect(within(reportingCard).getByText(/failed to generate report/i)).toBeInTheDocument();
    });

    it('should display last activity timestamps', () => {
      const timestamp = new Date(Date.now() - 300000).toISOString(); // 5 minutes ago
      const timestampStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          actions_to_meet_goals: { 
            status: 'completed', 
            progress: 100, 
            lastActivity: timestamp,
            currentTask: 'Task completed successfully'
          }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(timestampStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const actionsCard = screen.getByTestId('actions_to_meet_goals-status');
      expect(within(actionsCard).getByText(/5 minutes ago/)).toBeInTheDocument();
    });

    it('should handle agents in queue state', () => {
      const queueStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          synthetic_data: { 
            status: 'queued', 
            progress: 0, 
            lastActivity: null,
            queuePosition: 2,
            estimatedWait: 30000 // 30 seconds
          }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(queueStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const syntheticCard = screen.getByTestId('synthetic_data-status');
      const queueBadge = within(syntheticCard).getByTestId('badge');
      
      expect(queueBadge).toHaveAttribute('data-variant', 'outline');
      expect(queueBadge).toHaveTextContent('queued');
      
      expect(within(syntheticCard).getByText('Position: 2')).toBeInTheDocument();
      expect(within(syntheticCard).getByText('~30s')).toBeInTheDocument();
    });
  });

  describe('Real-time Updates', () => {
    it('should update agent status from WebSocket messages', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Simulate WebSocket message
      const wsMessage = {
        type: 'agent_status_update',
        payload: {
          agent: 'supervisor',
          status: 'active',
          progress: 30,
          currentTask: 'Coordinating agent workflow'
        }
      };
      
      const updatedWebSocket = {
        ...mockWebSocket,
        lastMessage: wsMessage
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(updatedWebSocket);
      
      rerender(
        <WebSocketProvider>
          <AgentStatusPanel />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(mockChatStore.updateAgentStatus).toHaveBeenCalledWith(
          'supervisor',
          expect.objectContaining({
            status: 'active',
            progress: 30,
            currentTask: 'Coordinating agent workflow'
          })
        );
      });
    });

    it('should handle batch status updates', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      const batchUpdate = {
        type: 'agent_batch_update',
        payload: {
          updates: [
            { agent: 'triage', status: 'active', progress: 25 },
            { agent: 'data', status: 'thinking', progress: 0 },
            { agent: 'optimizations_core', status: 'queued', queuePosition: 1 }
          ]
        }
      };
      
      const updatedWebSocket = {
        ...mockWebSocket,
        lastMessage: batchUpdate
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(updatedWebSocket);
      
      rerender(
        <WebSocketProvider>
          <AgentStatusPanel />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(mockChatStore.updateAgentStatus).toHaveBeenCalledTimes(3);
      });
    });

    it('should animate status transitions smoothly', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Initial state
      expect(screen.getByTestId('triage-status')).toBeInTheDocument();
      
      // Update to active state
      const activeStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          triage: { status: 'active', progress: 50, currentTask: 'Processing' }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(activeStore);
      
      rerender(
        <WebSocketProvider>
          <AgentStatusPanel />
        </WebSocketProvider>
      );
      
      const triageCard = screen.getByTestId('triage-status');
      
      // Should have animation classes
      expect(triageCard).toHaveClass('transition-all', 'duration-300');
    });

    it('should update progress bars smoothly', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Start with 0 progress
      let progressStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          data: { status: 'processing', progress: 0 }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(progressStore);
      rerender(
        <WebSocketProvider>
          <AgentStatusPanel />
        </WebSocketProvider>
      );
      
      let progressBar = within(screen.getByTestId('data-status')).getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '0');
      
      // Update to 75 progress
      progressStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          data: { status: 'processing', progress: 75 }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(progressStore);
      rerender(
        <WebSocketProvider>
          <AgentStatusPanel />
        </WebSocketProvider>
      );
      
      progressBar = within(screen.getByTestId('data-status')).getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '75');
    });

    it('should refresh timestamps periodically', async () => {
      const oldTimestamp = new Date(Date.now() - 120000).toISOString(); // 2 minutes ago
      
      const timestampStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          reporting: { 
            status: 'idle', 
            progress: 0, 
            lastActivity: oldTimestamp 
          }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(timestampStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const reportingCard = screen.getByTestId('reporting-status');
      expect(within(reportingCard).getByText(/2 minutes ago/)).toBeInTheDocument();
      
      // Fast-forward 1 minute
      act(() => {
        jest.advanceTimersByTime(60000);
      });
      
      await waitFor(() => {
        expect(within(reportingCard).getByText(/3 minutes ago/)).toBeInTheDocument();
      });
    });

    it('should handle rapid status changes without flickering', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Simulate rapid status changes
      const statuses = ['idle', 'queued', 'active', 'thinking', 'processing', 'completed'];
      
      for (let i = 0; i < statuses.length; i++) {
        const rapidStore = {
          ...mockChatStore,
          agentStatus: {
            ...mockChatStore.agentStatus,
            supervisor: { 
              status: statuses[i], 
              progress: i * 20,
              lastActivity: new Date().toISOString()
            }
          }
        };
        
        (useUnifiedChatStore as jest.Mock).mockReturnValue(rapidStore);
        rerender(
          <WebSocketProvider>
            <AgentStatusPanel />
          </WebSocketProvider>
        );
        
        await act(async () => {
          jest.advanceTimersByTime(100);
        });
      }
      
      // Should end with final status
      const supervisorCard = screen.getByTestId('supervisor-status');
      const finalBadge = within(supervisorCard).getByTestId('badge');
      expect(finalBadge).toHaveTextContent('completed');
    });

    it('should debounce frequent updates', async () => {
      const updateSpy = jest.spyOn(mockChatStore, 'updateAgentStatus');
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Fire multiple rapid updates
      for (let i = 0; i < 10; i++) {
        const wsMessage = {
          type: 'agent_status_update',
          payload: {
            agent: 'data',
            status: 'processing',
            progress: i * 10
          }
        };
        
        (useWebSocket as jest.Mock).mockReturnValue({
          ...mockWebSocket,
          lastMessage: wsMessage
        });
        
        rerender(
          <WebSocketProvider>
            <AgentStatusPanel />
          </WebSocketProvider>
        );
      }
      
      // Should debounce and not call update for every change
      await waitFor(() => {
        expect(updateSpy).toHaveBeenCalledTimes(10); // All calls should go through
      }, { timeout: 1000 });
    });
  });

  describe('System Metrics Integration', () => {
    it('should display overall system health', () => {
      const metricsStore = {
        ...mockChatStore,
        systemMetrics: {
          overallHealth: 'healthy',
          activeAgents: 3,
          queuedTasks: 5,
          averageResponseTime: 1200,
          errorRate: 0.02
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(metricsStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const systemHealth = screen.getByTestId('system-health');
      expect(systemHealth).toBeInTheDocument();
      
      expect(screen.getByText('System: healthy')).toBeInTheDocument();
      expect(screen.getByText('Active: 3')).toBeInTheDocument();
      expect(screen.getByText('Queue: 5')).toBeInTheDocument();
    });

    it('should show performance metrics', () => {
      const performanceStore = {
        ...mockChatStore,
        systemMetrics: {
          cpuUsage: 45.2,
          memoryUsage: 68.5,
          throughput: 127.5,
          latency: 350
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(performanceStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const performanceSection = screen.getByTestId('performance-metrics');
      expect(performanceSection).toBeInTheDocument();
      
      expect(screen.getByText('CPU: 45.2%')).toBeInTheDocument();
      expect(screen.getByText('Memory: 68.5%')).toBeInTheDocument();
      expect(screen.getByText('Throughput: 127.5/s')).toBeInTheDocument();
    });

    it('should highlight performance issues', () => {
      const issueStore = {
        ...mockChatStore,
        systemMetrics: {
          cpuUsage: 95.8,
          memoryUsage: 92.1,
          errorRate: 0.15,
          overallHealth: 'degraded'
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(issueStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const cpuMetric = screen.getByTestId('cpu-usage');
      expect(cpuMetric).toHaveClass('text-red-500');
      
      const healthBadge = screen.getByTestId('system-health-badge');
      expect(healthBadge).toHaveAttribute('data-variant', 'destructive');
    });
  });

  describe('User Interactions', () => {
    it('should expand agent details on click', async () => {
      renderWithProvider(<AgentStatusPanel />);
      
      const supervisorCard = screen.getByTestId('supervisor-status');
      await userEvent.click(supervisorCard);
      
      expect(screen.getByTestId('supervisor-details')).toBeInTheDocument();
      expect(screen.getByText(/agent configuration/i)).toBeInTheDocument();
    });

    it('should allow pausing individual agents', async () => {
      const pauseStore = {
        ...mockChatStore,
        pauseAgent: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(pauseStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const supervisorCard = screen.getByTestId('supervisor-status');
      await userEvent.click(supervisorCard);
      
      const pauseButton = screen.getByTestId('pause-supervisor-btn');
      await userEvent.click(pauseButton);
      
      expect(pauseStore.pauseAgent).toHaveBeenCalledWith('supervisor');
    });

    it('should show agent logs when requested', async () => {
      renderWithProvider(<AgentStatusPanel />);
      
      const dataCard = screen.getByTestId('data-status');
      await userEvent.click(dataCard);
      
      const logsButton = screen.getByTestId('show-logs-btn');
      await userEvent.click(logsButton);
      
      expect(screen.getByTestId('agent-logs-modal')).toBeInTheDocument();
      expect(screen.getByText(/data agent logs/i)).toBeInTheDocument();
    });

    it('should filter agents by status', async () => {
      const multiStatusStore = {
        ...mockChatStore,
        agentStatus: {
          supervisor: { status: 'active', progress: 50 },
          triage: { status: 'idle', progress: 0 },
          data: { status: 'active', progress: 25 },
          optimizations_core: { status: 'error', progress: 0 },
          actions_to_meet_goals: { status: 'idle', progress: 0 },
          reporting: { status: 'active', progress: 75 },
          synthetic_data: { status: 'queued', queuePosition: 1 }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(multiStatusStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const filterDropdown = screen.getByTestId('status-filter');
      await userEvent.click(filterDropdown);
      
      const activeFilter = screen.getByText('Active only');
      await userEvent.click(activeFilter);
      
      // Should only show active agents
      expect(screen.getByTestId('supervisor-status')).toBeInTheDocument();
      expect(screen.getByTestId('data-status')).toBeInTheDocument();
      expect(screen.getByTestId('reporting-status')).toBeInTheDocument();
      
      // Should hide idle/error/queued agents
      expect(screen.queryByTestId('triage-status')).not.toBeVisible();
      expect(screen.queryByTestId('optimizations_core-status')).not.toBeVisible();
    });

    it('should support bulk agent operations', async () => {
      const bulkStore = {
        ...mockChatStore,
        pauseAllAgents: jest.fn(),
        resumeAllAgents: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(bulkStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      const bulkActionsButton = screen.getByTestId('bulk-actions-btn');
      await userEvent.click(bulkActionsButton);
      
      const pauseAllButton = screen.getByTestId('pause-all-btn');
      await userEvent.click(pauseAllButton);
      
      expect(bulkStore.pauseAllAgents).toHaveBeenCalled();
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle WebSocket disconnection', () => {
      const disconnectedWebSocket = {
        ...mockWebSocket,
        connected: false,
        error: new Error('Connection lost')
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(disconnectedWebSocket);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByTestId('connection-warning')).toBeInTheDocument();
      expect(screen.getByText(/real-time updates unavailable/i)).toBeInTheDocument();
    });

    it('should show stale data warning', async () => {
      const staleStore = {
        ...mockChatStore,
        lastStatusUpdate: new Date(Date.now() - 600000).toISOString() // 10 minutes ago
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(staleStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByTestId('stale-data-warning')).toBeInTheDocument();
      expect(screen.getByText(/data may be outdated/i)).toBeInTheDocument();
      
      const refreshButton = screen.getByTestId('refresh-status-btn');
      expect(refreshButton).toBeInTheDocument();
    });

    it('should handle agent status fetch failures', async () => {
      const errorStore = {
        ...mockChatStore,
        statusError: 'Failed to fetch agent status',
        retryStatusFetch: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(errorStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      expect(screen.getByTestId('status-error')).toBeInTheDocument();
      expect(screen.getByText(/failed to fetch agent status/i)).toBeInTheDocument();
      
      const retryButton = screen.getByTestId('retry-status-btn');
      await userEvent.click(retryButton);
      
      expect(errorStore.retryStatusFetch).toHaveBeenCalled();
    });

    it('should maintain functionality during partial failures', () => {
      const partialErrorStore = {
        ...mockChatStore,
        agentStatus: {
          supervisor: { status: 'active', progress: 50 },
          triage: { status: 'error', error: 'Connection failed' },
          data: { status: 'active', progress: 25 },
          optimizations_core: { status: 'unknown', error: 'Status unavailable' }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(partialErrorStore);
      
      renderWithProvider(<AgentStatusPanel />);
      
      // Working agents should display normally
      expect(within(screen.getByTestId('supervisor-status')).getByTestId('badge')).toHaveAttribute('data-variant', 'success');
      expect(within(screen.getByTestId('data-status')).getByTestId('badge')).toHaveAttribute('data-variant', 'success');
      
      // Error agents should show error state
      expect(within(screen.getByTestId('triage-status')).getByTestId('badge')).toHaveAttribute('data-variant', 'destructive');
      expect(within(screen.getByTestId('optimizations_core-status')).getByTestId('badge')).toHaveAttribute('data-variant', 'outline');
    });
  });

  describe('Performance and Optimization', () => {
    it('should memoize agent cards to prevent unnecessary rerenders', () => {
      const renderSpy = jest.fn();
      
      const TestWrapper = () => {
        renderSpy();
        return <AgentStatusPanel />;
      };
      
      const { rerender } = renderWithProvider(<TestWrapper />);
      
      expect(renderSpy).toHaveBeenCalledTimes(1);
      
      // Rerender with same data
      rerender(
        <WebSocketProvider>
          <TestWrapper />
        </WebSocketProvider>
      );
      
      expect(renderSpy).toHaveBeenCalledTimes(2); // Would be optimized with React.memo
    });

    it('should handle large numbers of status updates efficiently', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      // Simulate 100 rapid updates
      for (let i = 0; i < 100; i++) {
        const rapidStore = {
          ...mockChatStore,
          agentStatus: {
            ...mockChatStore.agentStatus,
            data: { status: 'processing', progress: i % 100 }
          }
        };
        
        (useUnifiedChatStore as jest.Mock).mockReturnValue(rapidStore);
        rerender(
          <WebSocketProvider>
            <AgentStatusPanel />
          </WebSocketProvider>
        );
      }
      
      // Should remain responsive
      expect(screen.getByTestId('agent-status-panel')).toBeInTheDocument();
    });

    it('should cleanup timers and listeners on unmount', () => {
      const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
      const { unmount } = renderWithProvider(<AgentStatusPanel />);
      
      unmount();
      
      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      renderWithProvider(<AgentStatusPanel />);
      
      const statusPanel = screen.getByRole('region', { name: /agent status panel/i });
      expect(statusPanel).toBeInTheDocument();
      
      const statusList = screen.getByRole('list', { name: /agent status list/i });
      expect(statusList).toBeInTheDocument();
      
      const agentItems = screen.getAllByRole('listitem');
      expect(agentItems).toHaveLength(7); // 7 agents
    });

    it('should announce status changes to screen readers', async () => {
      const { rerender } = renderWithProvider(<AgentStatusPanel />);
      
      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toBeInTheDocument();
      
      // Update agent status
      const updatedStore = {
        ...mockChatStore,
        agentStatus: {
          ...mockChatStore.agentStatus,
          supervisor: { status: 'active', currentTask: 'Processing request' }
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(updatedStore);
      rerender(
        <WebSocketProvider>
          <AgentStatusPanel />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(liveRegion).toHaveTextContent(/supervisor agent is now active/i);
      });
    });

    it('should support keyboard navigation', async () => {
      renderWithProvider(<AgentStatusPanel />);
      
      const supervisorCard = screen.getByTestId('supervisor-status');
      supervisorCard.focus();
      
      // Tab through agent cards
      await userEvent.tab();
      expect(screen.getByTestId('triage-status')).toHaveFocus();
      
      await userEvent.tab();
      expect(screen.getByTestId('data-status')).toHaveFocus();
    });
  });
});