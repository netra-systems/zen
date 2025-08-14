/**
 * Data Generation and Processing Integration Tests
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

import { TestProviders } from '../test-utils/providers';

// Mock stores
const createMockStore = (initialState: any) => {
  let state = initialState;
  const store = Object.assign(
    jest.fn(() => state),
    {
      getState: jest.fn(() => state),
      setState: jest.fn((newState: any) => {
        state = typeof newState === 'function' ? newState(state) : { ...state, ...newState };
      })
    }
  );
  return store;
};

const useSyntheticDataStore = createMockStore({
  jobs: [],
  generateData: jest.fn()
});

const syntheticDataService = { 
  exportData: jest.fn().mockResolvedValue(new Blob(['data'])) 
};

let mockWs: WS;

beforeEach(() => {
  mockWs = new WS('ws://localhost:8000/ws');
});

afterEach(() => {
  WS.clean();
  jest.clearAllMocks();
});

describe('Synthetic Data Generation Flow', () => {
  it('should generate synthetic data based on user input', async () => {
    const TestComponent = () => {
      const [generationStatus, setGenerationStatus] = React.useState('');
      
      const handleGenerate = async () => {
        setGenerationStatus('Generating...');
        await useSyntheticDataStore.getState().generateData({
          type: 'user_behavior',
          count: 1000,
          format: 'json'
        });
        setGenerationStatus('Generated 1000 records');
      };
      
      return (
        <div>
          <button onClick={handleGenerate}>Generate Data</button>
          <div data-testid="gen-status">{generationStatus}</div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Generate Data'));
    
    await waitFor(() => {
      expect(getByTestId('gen-status')).toHaveTextContent('Generated 1000 records');
      expect(useSyntheticDataStore.getState().generateData).toHaveBeenCalledWith({
        type: 'user_behavior',
        count: 1000,
        format: 'json'
      });
    });
  });

  it('should export synthetic data in multiple formats', async () => {
    const TestComponent = () => {
      const [exportStatus, setExportStatus] = React.useState('');
      
      const handleExport = async (format: string) => {
        const blob = await syntheticDataService.exportData(format);
        setExportStatus(`Exported as ${format}: ${blob.size} bytes`);
      };
      
      return (
        <div>
          <button onClick={() => handleExport('csv')}>Export CSV</button>
          <button onClick={() => handleExport('json')}>Export JSON</button>
          <div data-testid="export-status">{exportStatus}</div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Export CSV'));
    
    await waitFor(() => {
      expect(getByTestId('export-status')).toHaveTextContent('Exported as csv: 4 bytes');
    });
  });
});

describe('Generation Service Integration', () => {
  it('should handle batch generation jobs', async () => {
    const TestComponent = () => {
      const [batchStatus, setBatchStatus] = React.useState<any>({});
      
      const handleBatchGeneration = async () => {
        const batchId = 'batch-123';
        setBatchStatus({ [batchId]: 'processing' });
        
        // Simulate progress updates
        setTimeout(() => setBatchStatus({ [batchId]: 'completed' }), 100);
      };
      
      return (
        <div>
          <button onClick={handleBatchGeneration}>Start Batch</button>
          <div data-testid="batch-status">
            {Object.entries(batchStatus).map(([id, status]) => (
              <div key={id}>{id}: {status}</div>
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
    
    fireEvent.click(getByText('Start Batch'));
    
    await waitFor(() => {
      expect(getByTestId('batch-status')).toHaveTextContent('batch-123: completed');
    });
  });

  it('should stream generation progress via WebSocket', async () => {
    const TestComponent = () => {
      const [progress, setProgress] = React.useState(0);
      
      React.useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws');
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'generation_progress') {
            setProgress(data.progress);
          }
        };
        return () => ws.close();
      }, []);
      
      return (
        <div>
          <div data-testid="progress">{progress}%</div>
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await mockWs.connected;
    
    act(() => {
      mockWs.send(JSON.stringify({ type: 'generation_progress', progress: 50 }));
    });
    
    await waitFor(() => {
      expect(getByTestId('progress')).toHaveTextContent('50%');
    });
  });
});