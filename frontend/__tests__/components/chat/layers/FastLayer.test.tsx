import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FastLayer } from '@/components/chat/layers/FastLayer';
import type { FastLayerData } from '@/types/unified-chat';

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Activity: () => <div data-testid="activity-icon">Activity</div>,
  Zap: () => <div data-testid="zap-icon">Zap</div>,
}));

describe('FastLayer', () => {
  const mockData: FastLayerData = {
    agentName: 'Optimization Agent',
    activeTools: ['cost_analyzer', 'latency_profiler'],
    timestamp: Date.now(),
    runId: 'run-123',
  };

  it('renders agent name when data is provided', () => {
    render(<FastLayer data={mockData} isProcessing={false} />);
    
    expect(screen.getByText('Optimization Agent')).toBeInTheDocument();
  });

  it('renders active tools as badges', () => {
    render(<FastLayer data={mockData} isProcessing={false} />);
    
    expect(screen.getByText('cost_analyzer')).toBeInTheDocument();
    expect(screen.getByText('latency_profiler')).toBeInTheDocument();
    expect(screen.getAllByTestId('zap-icon')).toHaveLength(2);
  });

  it('shows presence indicator when processing without data', () => {
    render(<FastLayer data={null} isProcessing={true} />);
    
    expect(screen.getByTestId('activity-icon')).toBeInTheDocument();
  });

  it('does not show presence indicator when data is available', () => {
    render(<FastLayer data={mockData} isProcessing={true} />);
    
    expect(screen.queryByTestId('activity-icon')).not.toBeInTheDocument();
  });

  it('renders empty tools list when activeTools is empty', () => {
    const dataWithNoTools: FastLayerData = {
      ...mockData,
      activeTools: [],
    };
    
    render(<FastLayer data={dataWithNoTools} isProcessing={false} />);
    
    expect(screen.getByText('Optimization Agent')).toBeInTheDocument();
    expect(screen.queryByTestId('zap-icon')).not.toBeInTheDocument();
  });

  it('applies correct styling classes', () => {
    const { container } = render(<FastLayer data={mockData} isProcessing={false} />);
    
    const layerElement = container.firstChild as HTMLElement;
    expect(layerElement).toHaveClass('h-12', 'flex', 'items-center', 'px-4');
    expect(layerElement).toHaveStyle({ height: '48px' });
  });

  it('handles null data gracefully', () => {
    render(<FastLayer data={null} isProcessing={false} />);
    
    expect(screen.queryByText('Optimization Agent')).not.toBeInTheDocument();
    expect(screen.queryByTestId('activity-icon')).not.toBeInTheDocument();
  });

  it('renders multiple tools correctly', () => {
    const dataWithManyTools: FastLayerData = {
      ...mockData,
      activeTools: ['tool1', 'tool2', 'tool3', 'tool4'],
    };
    
    render(<FastLayer data={dataWithManyTools} isProcessing={false} />);
    
    expect(screen.getByText('tool1')).toBeInTheDocument();
    expect(screen.getByText('tool2')).toBeInTheDocument();
    expect(screen.getByText('tool3')).toBeInTheDocument();
    expect(screen.getByText('tool4')).toBeInTheDocument();
  });
});