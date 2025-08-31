import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PersistentResponseCard } from '@/components/chat/PersistentResponseCard';
import type { 
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
  FastLayerData, 
  MediumLayerData, 
  SlowLayerData 
} from '@/types/unified-chat';

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock the layer components
jest.mock('@/components/chat/layers/FastLayer', () => ({
  FastLayer: ({ data, isProcessing }: any) => (
    <div data-testid="fast-layer">
      {isProcessing && <span>Processing...</span>}
      {data?.agentName && <span>{data.agentName}</span>}
    </div>
  ),
}));

jest.mock('@/components/chat/layers/MediumLayer', () => ({
  MediumLayer: ({ data }: any) => (
    <div data-testid="medium-layer">
      {data?.thought && <span>{data.thought}</span>}
    </div>
  ),
}));

jest.mock('@/components/chat/layers/SlowLayer', () => ({
  SlowLayer: ({ data }: any) => (
    <div data-testid="slow-layer">
      {data?.finalReport && <span>Final Report</span>}
    </div>
  ),
}));

describe('PersistentResponseCard', () => {
    jest.setTimeout(10000);
  const mockFastLayerData: FastLayerData = {
    agentName: 'Test Agent',
    activeTools: ['tool1', 'tool2'],
    timestamp: Date.now(),
    runId: 'test-run-123',
  };

  const mockMediumLayerData: MediumLayerData = {
    thought: 'Processing data...',
    partialContent: 'Partial results here',
    stepNumber: 2,
    totalSteps: 5,
    agentName: 'Test Agent',
  };

  const mockSlowLayerData: SlowLayerData = {
    completedAgents: [
      {
        agentName: 'Agent 1',
        duration: 1000,
        result: {},
        metrics: {},
      },
    ],
    finalReport: {
      report: {},
      recommendations: [],
      actionPlan: [],
      agentMetrics: [],
    },
    totalDuration: 5000,
    metrics: {
      total_duration_ms: 5000,
      total_tokens: 1000,
    },
  };

  it('renders with fast layer when processing', () => {
    render(
      <PersistentResponseCard
        fastLayerData={mockFastLayerData}
        mediumLayerData={null}
        slowLayerData={null}
        isProcessing={true}
      />
    );

    expect(screen.getByTestId('fast-layer')).toBeInTheDocument();
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
  });

  it('renders all three layers when data is available', () => {
    render(
      <PersistentResponseCard
        fastLayerData={mockFastLayerData}
        mediumLayerData={mockMediumLayerData}
        slowLayerData={mockSlowLayerData}
        isProcessing={false}
      />
    );

    expect(screen.getByTestId('fast-layer')).toBeInTheDocument();
    expect(screen.getByTestId('medium-layer')).toBeInTheDocument();
    expect(screen.getByTestId('slow-layer')).toBeInTheDocument();
  });

  it('shows collapsed view when isCollapsed is true and has final report', () => {
    const { container } = render(
      <PersistentResponseCard
        fastLayerData={mockFastLayerData}
        mediumLayerData={mockMediumLayerData}
        slowLayerData={mockSlowLayerData}
        isProcessing={false}
        isCollapsed={true}
        onToggleCollapse={jest.fn()}
      />
    );

    expect(screen.getByText(/Analysis Complete/)).toBeInTheDocument();
    expect(screen.getByText(/1 agents/)).toBeInTheDocument();
    expect(screen.queryByTestId('fast-layer')).not.toBeInTheDocument();
    expect(screen.queryByTestId('medium-layer')).not.toBeInTheDocument();
  });

  it('calls onToggleCollapse when clicking collapse header', () => {
    const mockToggle = jest.fn();
    render(
      <PersistentResponseCard
        fastLayerData={mockFastLayerData}
        mediumLayerData={mockMediumLayerData}
        slowLayerData={mockSlowLayerData}
        isProcessing={false}
        isCollapsed={true}
        onToggleCollapse={mockToggle}
      />
    );

    const collapseHeader = screen.getByText(/Analysis Complete/).parentElement;
    fireEvent.click(collapseHeader!);
    expect(mockToggle).toHaveBeenCalled();
  });

  it('renders empty card when no data and not processing', () => {
    const { container } = render(
      <PersistentResponseCard
        fastLayerData={null}
        mediumLayerData={null}
        slowLayerData={null}
        isProcessing={false}
      />
    );

    // Card should still render but be minimal
    expect(container.firstChild).toBeInTheDocument();
    expect(screen.queryByTestId('fast-layer')).not.toBeInTheDocument();
    expect(screen.queryByTestId('medium-layer')).not.toBeInTheDocument();
    expect(screen.queryByTestId('slow-layer')).not.toBeInTheDocument();
  });

  it('shows only presence indicator when processing without data', () => {
    render(
      <PersistentResponseCard
        fastLayerData={null}
        mediumLayerData={null}
        slowLayerData={null}
        isProcessing={true}
      />
    );

    expect(screen.getByTestId('fast-layer')).toBeInTheDocument();
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  it('progressively shows layers as data becomes available', () => {
    const { rerender } = render(
      <PersistentResponseCard
        fastLayerData={null}
        mediumLayerData={null}
        slowLayerData={null}
        isProcessing={true}
      />
    );

    // Initially only fast layer with processing
    expect(screen.getByTestId('fast-layer')).toBeInTheDocument();
    expect(screen.queryByTestId('medium-layer')).not.toBeInTheDocument();

    // Add fast layer data
    rerender(
      <PersistentResponseCard
        fastLayerData={mockFastLayerData}
        mediumLayerData={null}
        slowLayerData={null}
        isProcessing={true}
      />
    );

    expect(screen.getByText('Test Agent')).toBeInTheDocument();

    // Add medium layer data
    rerender(
      <PersistentResponseCard
        fastLayerData={mockFastLayerData}
        mediumLayerData={mockMediumLayerData}
        slowLayerData={null}
        isProcessing={true}
      />
    );

    expect(screen.getByTestId('medium-layer')).toBeInTheDocument();
    expect(screen.getByText('Processing data...')).toBeInTheDocument();

    // Add slow layer data
    rerender(
      <PersistentResponseCard
        fastLayerData={mockFastLayerData}
        mediumLayerData={mockMediumLayerData}
        slowLayerData={mockSlowLayerData}
        isProcessing={false}
      />
    );

    expect(screen.getByTestId('slow-layer')).toBeInTheDocument();
    expect(screen.getByText('Final Report')).toBeInTheDocument();
  });
});