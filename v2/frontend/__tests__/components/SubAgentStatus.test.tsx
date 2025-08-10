import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { SubAgentStatus } from '@/components/SubAgentStatus';
import { useChatStore } from '@/store/chat';

jest.mock('@/store/chat');

describe('SubAgentStatus', () => {
  const mockUseChatStore = useChatStore as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should not render when no sub-agent is active', () => {
    mockUseChatStore.mockReturnValue({
      currentSubAgent: null,
      subAgentStatus: null,
    });

    const { container } = render(<SubAgentStatus />);
    expect(container.firstChild).toBeNull();
  });

  it('should display sub-agent name and status', () => {
    mockUseChatStore.mockReturnValue({
      currentSubAgent: 'DataSubAgent',
      subAgentStatus: 'Analyzing data patterns...',
    });

    render(<SubAgentStatus />);

    expect(screen.getByText('DataSubAgent')).toBeInTheDocument();
    // Use a more flexible text matcher for the status text that may be split by elements
    expect(screen.getByText(/Analyzing data patterns/)).toBeInTheDocument();
  });

  it('should show running indicator for active agents', () => {
    mockUseChatStore.mockReturnValue({
      currentSubAgent: 'TriageSubAgent',
      subAgentStatus: 'RUNNING',
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
        currentSubAgent: 'TestAgent',
        subAgentStatus: state,
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
      currentSubAgent: 'OptimizationsCoreSubAgent',
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
      currentSubAgent: 'ReportingSubAgent',
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
      currentSubAgent: 'TriageSubAgent',
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
      currentSubAgent: 'DataSubAgent',
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
      currentSubAgent: 'ActionsToMeetGoalsSubAgent',
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
      currentSubAgent: 'DataSubAgent',
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
      currentSubAgent: 'ReportingSubAgent',
      subAgentStatus: 'COMPLETED',
      subAgentExecutionTime: 3456, // milliseconds
    });

    render(<SubAgentStatus />);

    expect(screen.getByText('Completed in 3.46s')).toBeInTheDocument();
  });

  it('should show queued agents', () => {
    mockUseChatStore.mockReturnValue({
      currentSubAgent: 'TriageSubAgent',
      subAgentStatus: 'RUNNING',
      queuedSubAgents: [
        'DataSubAgent',
        'OptimizationsCoreSubAgent',
        'ActionsToMeetGoalsSubAgent',
        'ReportingSubAgent',
      ],
    });

    render(<SubAgentStatus />);

    expect(screen.getByText('Next:')).toBeInTheDocument();
    expect(screen.getByText('DataSubAgent → 3 more')).toBeInTheDocument();
  });
});