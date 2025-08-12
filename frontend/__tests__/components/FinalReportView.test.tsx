import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FinalReportView } from '@/components/chat/FinalReportView';
import { useUnifiedChatStore } from '@/store/unified-chat';
// Mock dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/components/ui/card', () => ({
  Card: ({ children, className }: any) => <div className={className} data-testid="report-card">{children}</div>,
  CardHeader: ({ children }: any) => <div data-testid="card-header">{children}</div>,
  CardContent: ({ children }: any) => <div data-testid="card-content">{children}</div>,
  CardTitle: ({ children }: any) => <h3 data-testid="card-title">{children}</h3>
}));
jest.mock('@/components/charts/PerformanceChart', () => ({
  PerformanceChart: ({ data, type }: any) => (
    <div data-testid="performance-chart" data-chart-type={type}>
      Chart: {JSON.stringify(data)}
    </div>
  )
}));
jest.mock('@/components/charts/OptimizationMetrics', () => ({
  OptimizationMetrics: ({ metrics }: any) => (
    <div data-testid="optimization-metrics">
      Metrics: {JSON.stringify(metrics)}
    </div>
  )
}));

describe('FinalReportView Component', () => {
  const mockChatStore = {
    slowLayerData: null,
    finalReport: null,
    reportMetrics: null,
    exportReport: jest.fn(),
    generateReport: jest.fn(),
    refreshReport: jest.fn()
  };

  // Removed mockReportData - not used in the component

  beforeEach(() => {
    jest.clearAllMocks();
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockChatStore);
  });

  describe('Report Display and Layout', () => {
    it('should display comprehensive final report with all sections', () => {
      const completeReport = {
        id: 'report-123',
        title: 'AI Workload Optimization Analysis',
        summary: 'Comprehensive analysis of AI workload performance and optimization opportunities.',
        generatedAt: new Date().toISOString(),
        sections: {
          executiveSummary: {
            title: 'Executive Summary',
            content: 'Key findings and recommendations summary',
            keyMetrics: {
              performanceImprovement: 25.5,
              costReduction: 18.2,
              efficiency: 92.3
            }
          },
          performanceAnalysis: {
            title: 'Performance Analysis',
            content: 'Detailed performance analysis results',
            charts: [
              { type: 'line', data: [1, 2, 3, 4, 5], label: 'Performance Trend' },
              { type: 'bar', data: [10, 20, 30], label: 'Resource Usage' }
            ]
          },
          optimizations: {
            title: 'Optimization Recommendations',
            recommendations: [
              { id: 1, title: 'GPU Utilization', impact: 'High', description: 'Optimize GPU memory allocation' },
              { id: 2, title: 'Batch Processing', impact: 'Medium', description: 'Implement dynamic batch sizing' }
            ]
          },
          metrics: {
            throughput: 127.5,
            latency: 45.2,
            accuracy: 98.7,
            resourceUtilization: 85.4,
            costPerInference: 0.023
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: completeReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      // Main report components should be visible
      expect(screen.getByTestId('final-report-container')).toBeInTheDocument();
      expect(screen.getByText('AI Workload Optimization Analysis')).toBeInTheDocument();

      // Executive summary section
      expect(screen.getByTestId('executive-summary')).toBeInTheDocument();
      expect(screen.getByText('Key findings and recommendations summary')).toBeInTheDocument();

      // Key metrics
      expect(screen.getByText('25.5%')).toBeInTheDocument(); // Performance improvement
      expect(screen.getByText('18.2%')).toBeInTheDocument(); // Cost reduction
      expect(screen.getByText('92.3%')).toBeInTheDocument(); // Efficiency

      // Performance analysis with charts
      expect(screen.getByTestId('performance-analysis')).toBeInTheDocument();
      expect(screen.getAllByTestId('performance-chart')).toHaveLength(2);

      // Optimization recommendations
      expect(screen.getByTestId('optimization-recommendations')).toBeInTheDocument();
      expect(screen.getByText('GPU Utilization')).toBeInTheDocument();
      expect(screen.getByText('Batch Processing')).toBeInTheDocument();

      // Detailed metrics
      expect(screen.getByTestId('optimization-metrics')).toBeInTheDocument();
    });

    it('should show loading state while generating report', () => {
      const loadingStore = {
        ...mockChatStore,
        isLoadingReport: true
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(loadingStore);

      render(<FinalReportView runId="run-123" />);

      expect(screen.getByTestId('report-loading')).toBeInTheDocument();
      expect(screen.getByText(/generating final report/i)).toBeInTheDocument();
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('should display error state when report generation fails', () => {
      const errorStore = {
        ...mockChatStore,
        reportError: 'Failed to generate report: Insufficient data'
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(errorStore);

      render(<FinalReportView runId="run-123" />);

      expect(screen.getByTestId('report-error')).toBeInTheDocument();
      expect(screen.getByText(/failed to generate report/i)).toBeInTheDocument();
      expect(screen.getByTestId('retry-report-btn')).toBeInTheDocument();
    });

    it('should display empty state when no report data available', () => {
      render(<FinalReportView runId="run-123" />);

      expect(screen.getByTestId('no-report-available')).toBeInTheDocument();
      expect(screen.getByText(/no final report available/i)).toBeInTheDocument();
      expect(screen.getByTestId('generate-report-btn')).toBeInTheDocument();
    });

    it('should render report sections in correct order', () => {
      const orderedReport = {
        title: 'Ordered Report',
        sections: {
          executiveSummary: { title: 'Executive Summary', order: 1 },
          performanceAnalysis: { title: 'Performance Analysis', order: 2 },
          optimizations: { title: 'Optimizations', order: 3 },
          appendix: { title: 'Appendix', order: 4 }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: orderedReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const sections = screen.getAllByTestId(/section-/);
      expect(sections[0]).toHaveTextContent('Executive Summary');
      expect(sections[1]).toHaveTextContent('Performance Analysis');
      expect(sections[2]).toHaveTextContent('Optimizations');
      expect(sections[3]).toHaveTextContent('Appendix');
    });

    it('should display report metadata and timestamps', () => {
      const timestampedReport = {
        title: 'Timestamped Report',
        generatedAt: '2024-01-15T10:30:00Z',
        runId: 'run-123',
        version: '1.2.3',
        author: 'AI Assistant',
        duration: 45000 // 45 seconds
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: timestampedReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      expect(screen.getByTestId('report-metadata')).toBeInTheDocument();
      expect(screen.getByText(/generated on/i)).toBeInTheDocument();
      expect(screen.getByText(/run id: run-123/i)).toBeInTheDocument();
      expect(screen.getByText(/duration: 45s/i)).toBeInTheDocument();
    });

    it('should handle responsive layout on different screen sizes', () => {
      const responsiveReport = {
        title: 'Responsive Report',
        sections: {
          summary: { title: 'Summary' },
          charts: { title: 'Charts' }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: responsiveReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      // Mock different viewport sizes
      Object.defineProperty(window, 'innerWidth', { value: 768 });
      window.dispatchEvent(new Event('resize'));

      render(<FinalReportView runId="run-123" />);

      const container = screen.getByTestId('final-report-container');
      expect(container).toHaveClass('responsive-layout');
    });
  });

  describe('Data Visualization and Charts', () => {
    it('should render performance charts with correct data', () => {
      const chartReport = {
        sections: {
          performance: {
            charts: [
              {
                type: 'line',
                title: 'Throughput Over Time',
                data: { x: [1, 2, 3, 4], y: [100, 120, 150, 140] },
                config: { color: '#3b82f6', showGrid: true }
              },
              {
                type: 'bar',
                title: 'Resource Utilization',
                data: { labels: ['CPU', 'GPU', 'Memory'], values: [75, 90, 60] }
              }
            ]
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: chartReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const charts = screen.getAllByTestId('performance-chart');
      expect(charts).toHaveLength(2);

      expect(charts[0]).toHaveAttribute('data-chart-type', 'line');
      expect(charts[1]).toHaveAttribute('data-chart-type', 'bar');
    });

    it('should display optimization metrics with visual indicators', () => {
      const metricsReport = {
        sections: {
          metrics: {
            current: {
              throughput: 150.5,
              latency: 32.1,
              accuracy: 97.8,
              cost: 0.045
            },
            baseline: {
              throughput: 120.0,
              latency: 45.0,
              accuracy: 95.2,
              cost: 0.055
            },
            improvements: {
              throughput: '+25.4%',
              latency: '-28.7%',
              accuracy: '+2.7%',
              cost: '-18.2%'
            }
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: metricsReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      expect(screen.getByTestId('optimization-metrics')).toBeInTheDocument();

      // Should show improvements with proper indicators
      expect(screen.getByText('+25.4%')).toBeInTheDocument();
      expect(screen.getByText('-28.7%')).toBeInTheDocument();

      // Improvement indicators should have appropriate styling
      const improvements = screen.getAllByTestId('improvement-indicator');
      expect(improvements[0]).toHaveClass('text-green-600'); // Positive improvement
      expect(improvements[1]).toHaveClass('text-green-600'); // Negative is good for latency
    });

    it('should render comparison charts for before/after analysis', () => {
      const comparisonReport = {
        sections: {
          comparison: {
            beforeAfter: {
              title: 'Before vs After Optimization',
              beforeData: { performance: 85, cost: 100, efficiency: 70 },
              afterData: { performance: 110, cost: 80, efficiency: 95 },
              chartType: 'radar'
            }
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: comparisonReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      expect(screen.getByTestId('comparison-chart')).toBeInTheDocument();
      expect(screen.getByText('Before vs After Optimization')).toBeInTheDocument();
    });

    it('should handle missing or invalid chart data gracefully', () => {
      const invalidChartReport = {
        sections: {
          charts: {
            charts: [
              { type: 'line', data: null },
              { type: 'bar', data: undefined },
              { type: 'invalid', data: [] }
            ]
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: invalidChartReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      expect(screen.getByTestId('chart-error-fallback')).toBeInTheDocument();
      expect(screen.getByText(/unable to display chart/i)).toBeInTheDocument();
    });

    it('should support interactive chart features', async () => {
      const interactiveReport = {
        sections: {
          interactive: {
            charts: [
              {
                type: 'line',
                interactive: true,
                data: { x: [1, 2, 3], y: [10, 20, 15] },
                onDataPointClick: jest.fn()
              }
            ]
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: interactiveReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const interactiveChart = screen.getByTestId('performance-chart');
      
      // Simulate click on chart data point
      await userEvent.click(interactiveChart);

      // Should display tooltip or detailed view
      expect(screen.getByTestId('chart-tooltip')).toBeInTheDocument();
    });
  });

  describe('Report Actions and Export', () => {
    it('should export report to PDF', async () => {
      const exportableReport = {
        title: 'Exportable Report',
        sections: { summary: { title: 'Summary' } }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: exportableReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const exportButton = screen.getByTestId('export-pdf-btn');
      await userEvent.click(exportButton);

      expect(mockChatStore.exportReport).toHaveBeenCalledWith('run-123', 'pdf');
    });

    it('should export report to different formats', async () => {
      const reportStore = {
        ...mockChatStore,
        finalReport: { title: 'Multi-format Report' }
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const exportDropdown = screen.getByTestId('export-dropdown');
      await userEvent.click(exportDropdown);

      // Should show format options
      expect(screen.getByTestId('export-pdf-option')).toBeInTheDocument();
      expect(screen.getByTestId('export-docx-option')).toBeInTheDocument();
      expect(screen.getByTestId('export-json-option')).toBeInTheDocument();

      const jsonOption = screen.getByTestId('export-json-option');
      await userEvent.click(jsonOption);

      expect(mockChatStore.exportReport).toHaveBeenCalledWith('run-123', 'json');
    });

    it('should share report via URL', async () => {
      const shareableReport = {
        title: 'Shareable Report',
        shareUrl: 'https://app.netra.ai/reports/run-123'
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: shareableReport,
        generateShareUrl: jest.fn().mockResolvedValue('https://app.netra.ai/reports/run-123')
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      // Mock clipboard API
      const writeTextSpy = jest.fn();
      Object.assign(navigator, {
        clipboard: { writeText: writeTextSpy }
      });

      render(<FinalReportView runId="run-123" />);

      const shareButton = screen.getByTestId('share-report-btn');
      await userEvent.click(shareButton);

      await waitFor(() => {
        expect(reportStore.generateShareUrl).toHaveBeenCalledWith('run-123');
        expect(writeTextSpy).toHaveBeenCalledWith('https://app.netra.ai/reports/run-123');
      });

      expect(screen.getByTestId('share-success-toast')).toBeInTheDocument();
    });

    it('should print report', async () => {
      const printableReport = {
        title: 'Printable Report'
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: printableReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      const printSpy = jest.spyOn(window, 'print').mockImplementation(() => {});

      render(<FinalReportView runId="run-123" />);

      const printButton = screen.getByTestId('print-report-btn');
      await userEvent.click(printButton);

      expect(printSpy).toHaveBeenCalled();

      printSpy.mockRestore();
    });

    it('should refresh report data', async () => {
      const refreshableReport = {
        title: 'Refreshable Report',
        lastRefresh: new Date(Date.now() - 300000).toISOString() // 5 minutes ago
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: refreshableReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const refreshButton = screen.getByTestId('refresh-report-btn');
      await userEvent.click(refreshButton);

      expect(mockChatStore.refreshReport).toHaveBeenCalledWith('run-123');
    });

    it('should handle export failures gracefully', async () => {
      const reportStore = {
        ...mockChatStore,
        finalReport: { title: 'Export Fail Report' }
      };

      mockChatStore.exportReport.mockRejectedValueOnce(new Error('Export failed'));

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const exportButton = screen.getByTestId('export-pdf-btn');
      await userEvent.click(exportButton);

      await waitFor(() => {
        expect(screen.getByTestId('export-error-toast')).toBeInTheDocument();
        expect(screen.getByText(/export failed/i)).toBeInTheDocument();
      });
    });
  });

  describe('Report Navigation and Interaction', () => {
    it('should provide table of contents navigation', async () => {
      const navReport = {
        title: 'Navigable Report',
        sections: {
          summary: { title: 'Executive Summary', id: 'summary' },
          analysis: { title: 'Analysis', id: 'analysis' },
          recommendations: { title: 'Recommendations', id: 'recommendations' }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: navReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      expect(screen.getByTestId('table-of-contents')).toBeInTheDocument();

      const summaryLink = screen.getByTestId('nav-link-summary');
      await userEvent.click(summaryLink);

      // Should scroll to section
      const summarySection = screen.getByTestId('section-summary');
      expect(summarySection.scrollIntoView).toHaveBeenCalled();
    });

    it('should support section expansion/collapse', async () => {
      const collapsibleReport = {
        sections: {
          detailed: {
            title: 'Detailed Analysis',
            collapsible: true,
            expanded: false,
            content: 'Detailed content here'
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: collapsibleReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const expandButton = screen.getByTestId('expand-section-detailed');
      
      // Initially collapsed
      expect(screen.queryByText('Detailed content here')).not.toBeVisible();

      await userEvent.click(expandButton);

      // Should expand
      expect(screen.getByText('Detailed content here')).toBeVisible();
    });

    it('should highlight active section during scroll', async () => {
      const scrollableReport = {
        sections: {
          section1: { title: 'Section 1' },
          section2: { title: 'Section 2' },
          section3: { title: 'Section 3' }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: scrollableReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      // Mock intersection observer for active section tracking
      const mockIntersectionObserver = jest.fn();
      mockIntersectionObserver.mockReturnValue({
        observe: jest.fn(),
        unobserve: jest.fn(),
        disconnect: jest.fn()
      });
      window.IntersectionObserver = mockIntersectionObserver;

      // Simulate section 2 coming into view
      const [callback] = mockIntersectionObserver.mock.calls[0];
      callback([{ isIntersecting: true, target: { id: 'section-section2' } }]);

      await waitFor(() => {
        const activeNavLink = screen.getByTestId('nav-link-section2');
        expect(activeNavLink).toHaveClass('active');
      });
    });

    it('should support full-screen mode', async () => {
      const reportStore = {
        ...mockChatStore,
        finalReport: { title: 'Fullscreen Report' }
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const fullscreenButton = screen.getByTestId('fullscreen-btn');
      await userEvent.click(fullscreenButton);

      const reportContainer = screen.getByTestId('final-report-container');
      expect(reportContainer).toHaveClass('fullscreen');
    });

    it('should provide search within report', async () => {
      const searchableReport = {
        title: 'Searchable Report',
        sections: {
          content: {
            title: 'Content Section',
            content: 'This section contains optimization recommendations and performance metrics.'
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: searchableReport,
        searchReport: jest.fn()
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const searchInput = screen.getByTestId('report-search-input');
      await userEvent.type(searchInput, 'optimization');

      await waitFor(() => {
        expect(reportStore.searchReport).toHaveBeenCalledWith('optimization');
      });

      // Should highlight search results
      expect(screen.getByTestId('search-highlight')).toBeInTheDocument();
    });
  });

  describe('Performance and Optimization', () => {
    it('should lazy load report sections for large reports', () => {
      const largeReport = {
        title: 'Large Report',
        sections: Array.from({ length: 20 }, (_, i) => ({
          id: `section-${i}`,
          title: `Section ${i}`,
          content: `Content for section ${i}`.repeat(100),
          lazy: true
        }))
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: largeReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      // Should only render visible sections initially
      expect(screen.getAllByTestId(/^section-/)).toHaveLength(5); // First 5 sections
      expect(screen.getByTestId('lazy-load-indicator')).toBeInTheDocument();
    });

    it('should optimize chart rendering for performance', () => {
      const chartHeavyReport = {
        sections: {
          charts: {
            charts: Array.from({ length: 10 }, (_, i) => ({
              id: `chart-${i}`,
              type: 'line',
              data: Array.from({ length: 1000 }, (_, j) => ({ x: j, y: Math.random() * 100 }))
            }))
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: chartHeavyReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      // Should use virtualized rendering for large datasets
      expect(screen.getByTestId('virtualized-chart-container')).toBeInTheDocument();
    });

    it('should cache report data for faster subsequent loads', async () => {
      const cachedReport = {
        title: 'Cached Report',
        cacheKey: 'report-run-123',
        lastCached: new Date().toISOString()
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: cachedReport,
        loadFromCache: jest.fn()
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      const { rerender } = render(<FinalReportView runId="run-123" />);

      // Re-render should use cache
      rerender(<FinalReportView runId="run-123" />);

      expect(reportStore.loadFromCache).toHaveBeenCalledWith('report-run-123');
    });
  });

  describe('Accessibility and User Experience', () => {
    it('should have proper heading hierarchy and structure', () => {
      const structuredReport = {
        title: 'Structured Report',
        sections: {
          summary: { title: 'Summary', level: 2 },
          details: { 
            title: 'Details', 
            level: 2,
            subsections: {
              performance: { title: 'Performance', level: 3 },
              costs: { title: 'Costs', level: 3 }
            }
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: structuredReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      expect(screen.getByRole('heading', { level: 1, name: 'Structured Report' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 2, name: 'Summary' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 3, name: 'Performance' })).toBeInTheDocument();
    });

    it('should provide skip links for navigation', () => {
      const reportStore = {
        ...mockChatStore,
        finalReport: {
          title: 'Accessible Report',
          sections: {
            summary: { title: 'Summary' },
            charts: { title: 'Charts' }
          }
        }
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      expect(screen.getByTestId('skip-to-content')).toBeInTheDocument();
      expect(screen.getByTestId('skip-to-charts')).toBeInTheDocument();
    });

    it('should support keyboard navigation through report sections', async () => {
      const keyboardReport = {
        sections: {
          section1: { title: 'Section 1' },
          section2: { title: 'Section 2' }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: keyboardReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      // Tab through sections
      await userEvent.tab();
      expect(screen.getByTestId('section-section1')).toHaveFocus();

      await userEvent.tab();
      expect(screen.getByTestId('section-section2')).toHaveFocus();
    });

    it('should provide alternative text for charts and visualizations', () => {
      const accessibleChartReport = {
        sections: {
          charts: {
            charts: [{
              type: 'bar',
              title: 'Performance Comparison',
              data: { labels: ['Before', 'After'], values: [80, 120] },
              altText: 'Bar chart showing performance improvement from 80 to 120 units'
            }]
          }
        }
      };

      const reportStore = {
        ...mockChatStore,
        finalReport: accessibleChartReport
      };

      (useUnifiedChatStore as jest.Mock).mockReturnValue(reportStore);

      render(<FinalReportView runId="run-123" />);

      const chart = screen.getByTestId('performance-chart');
      expect(chart).toHaveAttribute('aria-label', 'Bar chart showing performance improvement from 80 to 120 units');
    });
  });
});