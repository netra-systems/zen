import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FastLayer } from '@/components/chat/layers/FastLayer';
import type { FastLayerData } from '@/types/unified-chat';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

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
    jest.setTimeout(10000);
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
    const { container } = render(<FastLayer data={null} isProcessing={true} />);
    
    // Check for the presence indicator divs (green dots)
    const presenceIndicator = container.querySelector('.bg-emerald-500.rounded-full');
    expect(presenceIndicator).toBeInTheDocument();
  });

  it('shows activity indicator when processing with data', () => {
    const { container } = render(<FastLayer data={mockData} isProcessing={true} />);
    
    // Should show activity indicator when processing with data
    const activityIndicator = container.querySelector('.bg-emerald-500.rounded-full');
    expect(activityIndicator).toBeInTheDocument();
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
    const { container } = render(<FastLayer data={null} isProcessing={false} />);
    
    expect(screen.queryByText('Optimization Agent')).not.toBeInTheDocument();
    // No presence indicator when not processing
    const presenceIndicator = container.querySelector('.bg-emerald-500.rounded-full');
    expect(presenceIndicator).not.toBeInTheDocument();
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

  it('shows fallback text when processing but no agent name', () => {
    render(<FastLayer data={null} isProcessing={true} />);
    
    expect(screen.getByText('Starting agent...')).toBeInTheDocument();
  });

  it('shows initializing text when agent active but no tools', () => {
    const dataWithNoTools: FastLayerData = {
      ...mockData,
      activeTools: [],
    };
    
    render(<FastLayer data={dataWithNoTools} isProcessing={true} />);
    
    expect(screen.getByText('Initializing...')).toBeInTheDocument();
  });
});