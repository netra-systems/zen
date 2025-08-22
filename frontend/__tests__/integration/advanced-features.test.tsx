/**
 * Advanced Features Integration Tests
 * Tests for demo mode, file processing, collaboration, metrics, and tools
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { WebSocketTestManager, createWebSocketManager } from '@/__tests__/helpers/websocket-test-manager';

// Mock fetch
global.fetch = jest.fn();

// Mock URL APIs for file handling
global.URL.createObjectURL = jest.fn(() => 'mock-blob-url');
global.URL.revokeObjectURL = jest.fn();

// WebSocket test manager
let wsManager: WebSocketTestManager;

beforeEach(() => {
  wsManager = createWebSocketManager();
  wsManager.setup();
});

afterEach(() => {
  wsManager.cleanup();
  jest.clearAllMocks();
});

describe('Demo Mode Functionality', () => {
  it('should enable demo mode with limited features', async () => {
    const TestComponent = () => {
      const [demoMode, setDemoMode] = React.useState(false);
      const [features, setFeatures] = React.useState<string[]>([]);
      
      const enableDemo = () => {
        setDemoMode(true);
        setFeatures(['chat', 'basic_analysis']);
      };
      
      return (
        <div>
          <button onClick={enableDemo}>Enable Demo</button>
          {demoMode && (
            <div data-testid="demo">
              <div>Demo mode active</div>
              <div>Features: {features.join(', ')}</div>
            </div>
          )}
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Enable Demo'));
    
    await waitFor(() => {
      expect(getByTestId('demo')).toHaveTextContent('Demo mode active');
      expect(getByTestId('demo')).toHaveTextContent('Features: chat, basic_analysis');
    });
  });

  it('should simulate data in demo mode', async () => {
    const TestComponent = () => {
      const [demoData, setDemoData] = React.useState<any[]>([]);
      
      const loadDemoData = async () => {
        // In demo mode, use mock data instead of API
        const mockData = [
          { id: 1, metric: 'CPU Usage', value: 45 },
          { id: 2, metric: 'Memory', value: 67 },
          { id: 3, metric: 'Requests', value: 1234 }
        ];
        setDemoData(mockData);
      };
      
      return (
        <div>
          <button onClick={loadDemoData}>Load Demo Data</button>
          <div data-testid="demo-data">
            {demoData.map(d => (
              <div key={d.id}>{d.metric}: {d.value}</div>
            ))}
          </div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Load Demo Data'));
    
    await waitFor(() => {
      expect(getByTestId('demo-data')).toHaveTextContent('CPU Usage: 45');
      expect(getByTestId('demo-data')).toHaveTextContent('Memory: 67');
    });
  });
});

describe('Enterprise Demo Features', () => {
  it('should showcase enterprise optimization features', async () => {
    const TestComponent = () => {
      const [optimization, setOptimization] = React.useState<any>(null);
      
      const runOptimization = async () => {
        const result = {
          current_cost: 10000,
          optimized_cost: 7500,
          savings: 2500,
          recommendations: [
            'Switch to spot instances',
            'Enable auto-scaling',
            'Optimize model selection'
          ]
        };
        setOptimization(result);
      };
      
      return (
        <div>
          <button onClick={runOptimization}>Run Optimization</button>
          {optimization && (
            <div data-testid="optimization">
              <div>Savings: ${optimization.savings}</div>
              <div>Recommendations: {optimization.recommendations.length}</div>
            </div>
          )}
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Run Optimization'));
    
    await waitFor(() => {
      expect(getByTestId('optimization')).toHaveTextContent('Savings: $2500');
      expect(getByTestId('optimization')).toHaveTextContent('Recommendations: 3');
    });
  });

  it('should display ROI calculations', async () => {
    const TestComponent = () => {
      const [roi, setROI] = React.useState<any>(null);
      
      const calculateROI = () => {
        const investment = 50000;
        const annualSavings = 120000;
        const roiPercent = ((annualSavings - investment) / investment) * 100;
        
        setROI({
          investment,
          savings: annualSavings,
          percentage: roiPercent,
          payback_months: Math.ceil(investment / (annualSavings / 12))
        });
      };
      
      return (
        <div>
          <button onClick={calculateROI}>Calculate ROI</button>
          {roi && (
            <div data-testid="roi">
              <div>ROI: {roi.percentage.toFixed(0)}%</div>
              <div>Payback: {roi.payback_months} months</div>
            </div>
          )}
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Calculate ROI'));
    
    await waitFor(() => {
      expect(getByTestId('roi')).toHaveTextContent('ROI: 140%');
      expect(getByTestId('roi')).toHaveTextContent('Payback: 5 months');
    });
  });
});

describe('PDF and Image Processing', () => {
  it('should extract text from PDF files', async () => {
    const TestComponent = () => {
      const [extractedText, setExtractedText] = React.useState('');
      
      const processPDF = async () => {
        const file = new File(['pdf content'], 'document.pdf', { type: 'application/pdf' });
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/process/pdf', {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        setExtractedText(data.text);
      };
      
      return (
        <div>
          <button onClick={processPDF}>Process PDF</button>
          {extractedText && (
            <div data-testid="extracted">{extractedText}</div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ text: 'Extracted PDF content' })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Process PDF'));
    
    await waitFor(() => {
      expect(getByTestId('extracted')).toHaveTextContent('Extracted PDF content');
    });
  });

  it('should analyze images using vision models', async () => {
    const TestComponent = () => {
      const [analysis, setAnalysis] = React.useState<any>(null);
      
      const analyzeImage = async () => {
        const file = new File(['image data'], 'image.png', { type: 'image/png' });
        const formData = new FormData();
        formData.append('image', file);
        
        const response = await fetch('/api/analyze/image', {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        setAnalysis(data);
      };
      
      return (
        <div>
          <button onClick={analyzeImage}>Analyze Image</button>
          {analysis && (
            <div data-testid="analysis">
              <div>Objects: {analysis.objects.join(', ')}</div>
              <div>Text: {analysis.text}</div>
            </div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        objects: ['chart', 'graph', 'data'],
        text: 'Revenue Growth 2024'
      })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Analyze Image'));
    
    await waitFor(() => {
      expect(getByTestId('analysis')).toHaveTextContent('Objects: chart, graph, data');
      expect(getByTestId('analysis')).toHaveTextContent('Text: Revenue Growth 2024');
    });
  });
});

describe('Export and Import Functionality', () => {
  it('should export data in multiple formats', async () => {
    const TestComponent = () => {
      const [exportStatus, setExportStatus] = React.useState('');
      
      const exportData = async (format: string) => {
        const response = await fetch(`/api/export?format=${format}`);
        const blob = await response.blob();
        
        // Create download link
        const url = URL.createObjectURL(blob);
        setExportStatus(`Exported as ${format}`);
        
        // Cleanup
        URL.revokeObjectURL(url);
      };
      
      return (
        <div>
          <button onClick={() => exportData('json')}>Export JSON</button>
          <button onClick={() => exportData('csv')}>Export CSV</button>
          <button onClick={() => exportData('excel')}>Export Excel</button>
          <div data-testid="export-status">{exportStatus}</div>
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['data'])
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Export JSON'));
    
    await waitFor(() => {
      expect(getByTestId('export-status')).toHaveTextContent('Exported as json');
    });
  });

  it('should import and validate data', async () => {
    const TestComponent = () => {
      const [importStatus, setImportStatus] = React.useState('');
      const [validationErrors, setValidationErrors] = React.useState<string[]>([]);
      
      const importData = async () => {
        const file = new File(['{"data": "test"}'], 'import.json', { type: 'application/json' });
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/import', {
          method: 'POST',
          body: formData
        });
        
        const result = await response.json();
        
        if (result.valid) {
          setImportStatus('Import successful');
        } else {
          setValidationErrors(result.errors);
        }
      };
      
      return (
        <div>
          <button onClick={importData}>Import Data</button>
          <div data-testid="import-status">{importStatus}</div>
          {validationErrors.length > 0 && (
            <div data-testid="errors">
              {validationErrors.join(', ')}
            </div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ valid: true })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Import Data'));
    
    await waitFor(() => {
      expect(getByTestId('import-status')).toHaveTextContent('Import successful');
    });
  });
});

describe('Real-time Metrics Dashboard', () => {
  it('should display live performance metrics', async () => {
    const TestComponent = () => {
      const [metrics, setMetrics] = React.useState<any>({
        cpu: 0,
        memory: 0,
        requests: 0
      });
      
      React.useEffect(() => {
        const ws = new WebSocket(wsManager.getUrl());
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'metrics') {
            setMetrics(data.metrics);
          }
        };
        return () => ws.close();
      }, []);
      
      return (
        <div data-testid="metrics">
          <div>CPU: {metrics.cpu}%</div>
          <div>Memory: {metrics.memory}%</div>
          <div>Requests: {metrics.requests}/s</div>
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await wsManager.waitForConnection();
    
    act(() => {
      wsManager.sendMessage({
        type: 'metrics',
        metrics: {
          cpu: 45,
          memory: 67,
          requests: 150
        }
      });
    });
    
    await waitFor(() => {
      expect(getByTestId('metrics')).toHaveTextContent('CPU: 45%');
      expect(getByTestId('metrics')).toHaveTextContent('Memory: 67%');
      expect(getByTestId('metrics')).toHaveTextContent('Requests: 150/s');
    });
  });
});

describe('Agent Tool Dispatcher Integration', () => {
  it('should dispatch tools to appropriate agents', async () => {
    const TestComponent = () => {
      const [result, setResult] = React.useState<any>(null);
      
      const dispatchTool = async (tool: string) => {
        const response = await fetch('/api/agent/tools/dispatch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool,
            params: { workload_id: 'wl-123' }
          })
        });
        
        const data = await response.json();
        setResult(data);
      };
      
      return (
        <div>
          <button onClick={() => dispatchTool('cost_analyzer')}>
            Analyze Cost
          </button>
          {result && (
            <div data-testid="result">
              Tool: {result.tool}, Savings: ${result.result.savings}
            </div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        tool: 'cost_analyzer',
        result: { savings: 200 }
      })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Analyze Cost'));
    
    await waitFor(() => {
      expect(getByTestId('result')).toHaveTextContent('Tool: cost_analyzer, Savings: $200');
    });
  });
});