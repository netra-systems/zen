import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { SubAgentStatus } from '@/components/SubAgentStatus';
import { useUnifiedChatStore } from '@/store/unified-chat';

jest.mock('@/store/unified-chat');

describe('SubAgentStatus', () => {
  const mockUseChatStore = useUnifiedChatStore as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should not render when no sub-agent is active', () => {
    mockUseChatStore.mockReturnValue({
      subAgentName: null,
      subAgentStatus: null,
      subAgentTools: [],
      subAgentProgress: null,
      subAgentError: null,
      subAgentDescription: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });

    const { container } = render(<SubAgentStatus />);
    expect(container.firstChild).toBeNull();
  });

  it('should display sub-agent name and status', () => {
    mockUseChatStore.mockReturnValue({
      subAgentName: 'DataSubAgent',
      subAgentStatus: 'Analyzing data patterns...',
      subAgentTools: [],
      subAgentProgress: null,
      subAgentError: null,
      subAgentDescription: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });

    render(<SubAgentStatus />);

    expect(screen.getByText('DataSubAgent')).toBeInTheDocument();
    // Use a more flexible text matcher for the status text that may be split by elements
    expect(screen.getByText(/Analyzing data patterns/)).toBeInTheDocument();
  });

  it('should show running indicator for active agents', () => {
    mockUseChatStore.mockReturnValue({
      subAgentName: 'TriageSubAgent',
      subAgentStatus: 'RUNNING',
      subAgentTools: [],
      subAgentProgress: null,
      subAgentError: null,
      subAgentDescription: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });

    render(<SubAgentStatus />);

    const indicator = screen.getByTestId('status-indicator');
    expect(indicator).toHaveClass('animate-pulse');
    expect(indicator).toHaveClass('bg-green-500');
  });

  it('should handle different lifecycle states', () => {
    const lifecycleStates = [
      { state: 'PENDING', color: 'bg-gray-500' },
      { state: 'RUNNING', color: 'bg-green-500' },
      { state: 'COMPLETED', color: 'bg-blue-500' },
      { state: 'FAILED', color: 'bg-red-500' },
    ];

    lifecycleStates.forEach(({ state, color }) => {
      mockUseChatStore.mockReturnValue({
        subAgentName: 'TestAgent',
        subAgentStatus: state,
        subAgentTools: [],
        subAgentProgress: null,
        subAgentError: null,
        subAgentDescription: null,
        subAgentExecutionTime: null,
        queuedSubAgents: []
      });

      const { getByTestId, unmount } = render(<SubAgentStatus />);
      
      const indicator = getByTestId('status-indicator');
      expect(indicator).toHaveClass(color);
      
      // Clean up between iterations to avoid multiple instances
      unmount();
    });
  });

  it('should display tool usage information', () => {
    mockUseChatStore.mockReturnValue({
      subAgentName: 'OptimizationsCoreSubAgent',
      subAgentStatus: 'RUNNING',
      subAgentTools: ['cost_analyzer', 'performance_profiler'],
      subAgentProgress: null,
      subAgentError: null,
      subAgentDescription: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });

    render(<SubAgentStatus />);

    expect(screen.getByText(/Tools:/)).toBeInTheDocument();
    expect(screen.getByText(/cost_analyzer/)).toBeInTheDocument();
    expect(screen.getByText(/performance_profiler/)).toBeInTheDocument();
  });

  it('should show progress for multi-step agents', () => {
    mockUseChatStore.mockReturnValue({
      subAgentName: 'ReportingSubAgent',
      subAgentStatus: 'RUNNING',
      subAgentProgress: {
        current: 3,
        total: 5,
        message: 'Generating visualizations...',
      },
      subAgentTools: [],
      subAgentError: null,
      subAgentDescription: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });

    render(<SubAgentStatus />);

    expect(screen.getByText('Step 3 of 5')).toBeInTheDocument();
    expect(screen.getByText('Generating visualizations...')).toBeInTheDocument();
    
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '60');
  });

  it('should animate transitions between agents', async () => {
    const { rerender } = render(<SubAgentStatus />);
    
    // First agent
    mockUseChatStore.mockReturnValue({
      subAgentName: 'TriageSubAgent',
      subAgentStatus: 'COMPLETED',
      subAgentTools: [],
      subAgentProgress: null,
      subAgentError: null,
      subAgentDescription: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });

    rerender(<SubAgentStatus />);
    expect(screen.getByText('TriageSubAgent')).toBeInTheDocument();

    // Transition to second agent
    mockUseChatStore.mockReturnValue({
      subAgentName: 'DataSubAgent',
      subAgentStatus: 'RUNNING',
      subAgentTools: [],
      subAgentProgress: null,
      subAgentError: null,
      subAgentDescription: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });

    rerender(<SubAgentStatus />);

    await waitFor(() => {
      expect(screen.getByText('DataSubAgent')).toBeInTheDocument();
    });
  });

  it('should handle error states gracefully', () => {
    mockUseChatStore.mockReturnValue({
      subAgentName: 'ActionsToMeetGoalsSubAgent',
      subAgentStatus: 'FAILED',
      subAgentError: 'Unable to generate action plan: Insufficient data',
      subAgentTools: [],
      subAgentProgress: null,
      subAgentDescription: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });

    render(<SubAgentStatus />);

    expect(screen.getByText('ActionsToMeetGoalsSubAgent')).toBeInTheDocument();
    expect(screen.getByText(/FAILED/)).toBeInTheDocument();
    expect(screen.getByText('Unable to generate action plan: Insufficient data')).toBeInTheDocument();
    
    const indicator = screen.getByTestId('status-indicator');
    expect(indicator).toHaveClass('bg-red-500');
  });

  it('should show agent descriptions on hover', async () => {
    mockUseChatStore.mockReturnValue({
      subAgentName: 'DataSubAgent',
      subAgentStatus: 'RUNNING',
      subAgentDescription: 'Gathers and enriches data from various sources',
      subAgentTools: [],
      subAgentProgress: null,
      subAgentError: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });

    render(<SubAgentStatus />);

    const agentName = screen.getByText('DataSubAgent');
    
    // Hover over agent name
    agentName.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));

    await waitFor(() => {
      expect(screen.getByText('Gathers and enriches data from various sources')).toBeInTheDocument();
    });
  });

  it('should display execution time', () => {
    mockUseChatStore.mockReturnValue({
      subAgentName: 'ReportingSubAgent',
      subAgentStatus: 'COMPLETED',
      subAgentExecutionTime: 3456, // milliseconds
      subAgentTools: [],
      subAgentProgress: null,
      subAgentError: null,
      subAgentDescription: null,
      queuedSubAgents: []
    });

    render(<SubAgentStatus />);

    expect(screen.getByText('Completed in 3.46s')).toBeInTheDocument();
  });

  it('should show queued agents', () => {
    mockUseChatStore.mockReturnValue({
      subAgentName: 'TriageSubAgent',
      subAgentStatus: 'RUNNING',
      queuedSubAgents: [
        'DataSubAgent',
        'OptimizationsCoreSubAgent',
        'ActionsToMeetGoalsSubAgent',
        'ReportingSubAgent',
      ],
      subAgentTools: [],
      subAgentProgress: null,
      subAgentError: null,
      subAgentDescription: null,
      subAgentExecutionTime: null
    });

    render(<SubAgentStatus />);

    expect(screen.getByText(/Next:/)).toBeInTheDocument();
    expect(screen.getByText(/DataSubAgent/)).toBeInTheDocument();
    expect(screen.getByText(/3 more/)).toBeInTheDocument();
  });
});