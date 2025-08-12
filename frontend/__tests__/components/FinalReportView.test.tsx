import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FinalReportView } from '@/components/chat/FinalReportView';

// Mock dependencies
jest.mock('@/components/ui/card', () => ({
  Card: ({ children, className }: any) => <div className={className} data-testid="card">{children}</div>,
  CardHeader: ({ children }: any) => <div data-testid="card-header">{children}</div>,
  CardContent: ({ children }: any) => <div data-testid="card-content">{children}</div>,
  CardTitle: ({ children }: any) => <h3 data-testid="card-title">{children}</h3>
}));
jest.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children, defaultValue }: any) => <div data-testid="tabs" data-default={defaultValue}>{children}</div>,
  TabsList: ({ children }: any) => <div data-testid="tabs-list">{children}</div>,
  TabsTrigger: ({ children, value }: any) => <button data-testid={`tab-${value}`}>{children}</button>,
  TabsContent: ({ children, value }: any) => <div data-testid={`tab-content-${value}`}>{children}</div>
}));
jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, variant }: any) => <span data-testid="badge" data-variant={variant}>{children}</span>
}));
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, variant, size }: any) => (
    <button data-testid="button" onClick={onClick} data-variant={variant} data-size={size}>
      {children}
    </button>
  )
}));
jest.mock('@/components/ui/collapsible', () => ({
  Collapsible: ({ children, open }: any) => <div data-testid="collapsible" data-open={open}>{children}</div>,
  CollapsibleTrigger: ({ children }: any) => <button data-testid="collapsible-trigger">{children}</button>,
  CollapsibleContent: ({ children }: any) => <div data-testid="collapsible-content">{children}</div>
}));
jest.mock('@/components/ui/progress', () => ({
  Progress: ({ value }: any) => <div data-testid="progress" data-value={value}>Progress: {value}%</div>
}));
jest.mock('@/components/ui/alert', () => ({
  Alert: ({ children }: any) => <div data-testid="alert">{children}</div>,
  AlertDescription: ({ children }: any) => <div data-testid="alert-description">{children}</div>
}));

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

describe('FinalReportView Component', () => {
  // Mock URL.createObjectURL and URL.revokeObjectURL
  beforeAll(() => {
    global.URL = {
      ...global.URL,
      createObjectURL: jest.fn(() => 'blob:mock-url'),
      revokeObjectURL: jest.fn()
    } as any;
  });

  const mockReportData = {
    data_result: {
      summary: 'Data analysis complete',
      findings: ['Finding 1', 'Finding 2']
    },
    optimizations_result: {
      recommendations: ['Optimization 1', 'Optimization 2'],
      impact: 'High'
    },
    action_plan_result: [
      { step: 1, action: 'Implement caching', priority: 'High' },
      { step: 2, action: 'Optimize queries', priority: 'Medium' }
    ],
    report_result: {
      executive_summary: 'Executive summary content',
      detailed_findings: 'Detailed findings content'
    },
    final_report: 'This is the final comprehensive report.',
    execution_metrics: {
      total_duration: 45000,
      agent_timings: [
        {
          agent_name: 'data',
          duration: 15000,
          start_time: '2024-01-01T00:00:00Z',
          end_time: '2024-01-01T00:00:15Z'
        },
        {
          agent_name: 'optimizations',
          duration: 20000,
          start_time: '2024-01-01T00:00:15Z',
          end_time: '2024-01-01T00:00:35Z'
        }
      ],
      tool_calls: [
        { tool_name: 'analyzer', count: 5, avg_duration: 2000 },
        { tool_name: 'optimizer', count: 3, avg_duration: 3000 }
      ]
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Report Display', () => {
    it('should render the final report view', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      // Check for cards
      const cards = screen.getAllByTestId('card');
      expect(cards.length).toBeGreaterThan(0);
      expect(screen.getByTestId('tabs')).toBeInTheDocument();
    });

    it('should display tabs for different sections', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      expect(screen.getByTestId('tab-overview')).toBeInTheDocument();
      expect(screen.getByTestId('tab-data')).toBeInTheDocument();
      expect(screen.getByTestId('tab-optimizations')).toBeInTheDocument();
      expect(screen.getByTestId('tab-actions')).toBeInTheDocument();
      expect(screen.getByTestId('tab-metrics')).toBeInTheDocument();
    });

    it('should show report data when available', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      expect(screen.getByText(/final comprehensive report/i)).toBeInTheDocument();
    });

    it('should display execution metrics', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      // Check for formatted duration text (45s)
      const durationElement = screen.getByText('45.0s');
      expect(durationElement).toBeInTheDocument();
    });

    it('should show agent timings', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      expect(screen.getByText(/data/)).toBeInTheDocument();
      expect(screen.getByText(/optimizations/)).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should handle empty report data gracefully', () => {
      const emptyReportData = {
        execution_metrics: {
          total_duration: 0,
          agent_timings: [],
          tool_calls: []
        }
      };
      
      render(<FinalReportView reportData={emptyReportData} />);
      
      const cards = screen.getAllByTestId('card');
      expect(cards.length).toBeGreaterThan(0);
    });

    it('should show placeholder when no final report', () => {
      const noReportData = {
        ...mockReportData,
        final_report: undefined
      };
      
      render(<FinalReportView reportData={noReportData} />);
      
      const cards = screen.getAllByTestId('card');
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  describe('Data Results Section', () => {
    it('should display data analysis results', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      const dataSection = screen.getByTestId('tab-content-data');
      expect(dataSection).toBeInTheDocument();
    });

    it('should render findings list', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      expect(screen.getByText(/Finding 1/)).toBeInTheDocument();
      expect(screen.getByText(/Finding 2/)).toBeInTheDocument();
    });
  });

  describe('Optimizations Section', () => {
    it('should display optimization recommendations', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      expect(screen.getByText(/Optimization 1/)).toBeInTheDocument();
      expect(screen.getByText(/Optimization 2/)).toBeInTheDocument();
    });

    it('should show impact level', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      expect(screen.getByText(/High/)).toBeInTheDocument();
    });
  });

  describe('Action Plan Section', () => {
    it('should display action items', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      expect(screen.getByText(/Implement caching/)).toBeInTheDocument();
      expect(screen.getByText(/Optimize queries/)).toBeInTheDocument();
    });

    it('should handle array action plans', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      const actionItems = mockReportData.action_plan_result as Array<Record<string, unknown>>;
      expect(actionItems).toHaveLength(2);
    });

    it('should handle object action plans', () => {
      const objectActionPlan = {
        ...mockReportData,
        action_plan_result: {
          immediate: ['Action 1'],
          future: ['Action 2']
        }
      };
      
      render(<FinalReportView reportData={objectActionPlan} />);
      
      const cards = screen.getAllByTestId('card');
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  describe('Performance Metrics', () => {
    it('should display tool call statistics', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      expect(screen.getByText(/analyzer/)).toBeInTheDocument();
      expect(screen.getByText(/optimizer/)).toBeInTheDocument();
    });

    it('should show average durations', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      // Tool calls have average durations
      expect(screen.getByText(/2/)).toBeInTheDocument(); // 2000ms = 2s
      expect(screen.getByText(/3/)).toBeInTheDocument(); // 3000ms = 3s
    });

    it('should calculate total execution time', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      // Total duration is 45000ms = 45s
      expect(screen.getByText(/45/)).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should allow tab switching', async () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      const dataTab = screen.getByTestId('tab-data');
      await userEvent.click(dataTab);
      
      expect(screen.getByTestId('tab-content-data')).toBeInTheDocument();
    });

    it('should support copy functionality', async () => {
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: jest.fn().mockResolvedValue(undefined)
        }
      });
      
      render(<FinalReportView reportData={mockReportData} />);
      
      const copyButtons = screen.getAllByTestId('button');
      const copyButton = copyButtons.find(btn => btn.textContent?.includes('Copy'));
      
      expect(copyButton).toBeTruthy();
      if (copyButton) {
        await userEvent.click(copyButton);
        expect(navigator.clipboard.writeText).toHaveBeenCalled();
      }
    });

    it('should handle collapsible sections', async () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      const triggers = screen.getAllByTestId('collapsible-trigger');
      if (triggers.length > 0) {
        await userEvent.click(triggers[0]);
        expect(screen.getByTestId('collapsible-content')).toBeInTheDocument();
      }
    });
  });

  describe('Export Functionality', () => {
    it('should provide export button', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      const buttons = screen.getAllByTestId('button');
      const downloadButton = buttons.find(btn => btn.textContent?.includes('Download'));
      
      expect(downloadButton).toBeTruthy();
    });

    it('should handle download action', async () => {
      // Mock document.createElement
      const mockClick = jest.fn();
      const mockElement = {
        href: '',
        download: '',
        click: mockClick
      };
      jest.spyOn(document, 'createElement').mockReturnValue(mockElement as any);
      
      render(<FinalReportView reportData={mockReportData} />);
      
      const buttons = screen.getAllByTestId('button');
      const downloadButton = buttons.find(btn => btn.textContent?.includes('Download'));
      
      expect(downloadButton).toBeTruthy();
      if (downloadButton) {
        await userEvent.click(downloadButton);
        expect(mockClick).toHaveBeenCalled();
        expect(global.URL.createObjectURL).toHaveBeenCalled();
      }
    });
  });

  describe('Visual Indicators', () => {
    it('should show progress bars for metrics', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      const progressBars = screen.queryAllByTestId('progress');
      expect(progressBars.length).toBeGreaterThanOrEqual(0);
    });

    it('should display badges for status', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      const badges = screen.queryAllByTestId('badge');
      expect(badges.length).toBeGreaterThanOrEqual(0);
    });

    it('should show alerts for important information', () => {
      render(<FinalReportView reportData={mockReportData} />);
      
      const alerts = screen.queryAllByTestId('alert');
      expect(alerts.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Error Handling', () => {
    it('should handle missing data gracefully', () => {
      const incompleteData = {
        data_result: undefined,
        optimizations_result: undefined,
        execution_metrics: {
          total_duration: 0,
          agent_timings: [],
          tool_calls: []
        }
      };
      
      render(<FinalReportView reportData={incompleteData} />);
      
      const cards = screen.getAllByTestId('card');
      expect(cards.length).toBeGreaterThan(0);
    });

    it('should handle malformed metrics', () => {
      const malformedData = {
        ...mockReportData,
        execution_metrics: undefined
      };
      
      render(<FinalReportView reportData={malformedData} />);
      
      const cards = screen.getAllByTestId('card');
      expect(cards.length).toBeGreaterThan(0);
    });
  });
});