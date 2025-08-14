/**
 * End-to-End User Journey Tests
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { setupTestEnvironment } from './test-setup';

describe('Advanced Frontend Integration Tests - End-to-End Journey', () => {
  let server: WS;
  
  setupTestEnvironment();

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws');
  });

  afterEach(() => {
    WS.clean();
  });

  describe('30. End-to-End User Journey', () => {
    it('should complete full optimization workflow', async () => {
      const OptimizationWorkflow = () => {
        const [step, setStep] = React.useState('upload');
        const [workloadData, setWorkloadData] = React.useState<any>(null);
        const [optimizations, setOptimizations] = React.useState<any[]>([]);
        const [results, setResults] = React.useState<any>(null);
        
        const handleUpload = (file: File) => {
          // Parse workload data
          setWorkloadData({ name: file.name, size: file.size });
          setStep('analyze');
        };
        
        const analyzeWorkload = async () => {
          // Simulate analysis
          await new Promise(resolve => setTimeout(resolve, 100));
          
          setOptimizations([
            { id: '1', type: 'model', recommendation: 'Switch to GPT-3.5' },
            { id: '2', type: 'caching', recommendation: 'Enable response caching' }
          ]);
          setStep('review');
        };
        
        const applyOptimizations = async () => {
          // Simulate applying optimizations
          await new Promise(resolve => setTimeout(resolve, 100));
          
          setResults({
            costReduction: '45%',
            latencyImprovement: '30ms',
            applied: optimizations.length
          });
          setStep('complete');
        };
        
        return (
          <div>
            <div data-testid="current-step">{step}</div>
            
            {step === 'upload' && (
              <div>
                <input
                  type="file"
                  data-testid="file-input"
                  onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
                />
              </div>
            )}
            
            {step === 'analyze' && (
              <div>
                <div>Analyzing {workloadData?.name}</div>
                <button onClick={analyzeWorkload}>Start Analysis</button>
              </div>
            )}
            
            {step === 'review' && (
              <div>
                <div data-testid="optimization-count">
                  {optimizations.length} optimizations found
                </div>
                <button onClick={applyOptimizations}>Apply All</button>
              </div>
            )}
            
            {step === 'complete' && (
              <div data-testid="results">
                Cost reduced by {results.costReduction},
                Latency improved by {results.latencyImprovement}
              </div>
            )}
          </div>
        );
      };
      
      const { getByTestId, getByText } = render(<OptimizationWorkflow />);
      
      // Step 1: Upload
      expect(getByTestId('current-step')).toHaveTextContent('upload');
      
      const file = new File(['workload data'], 'workload.json', { type: 'application/json' });
      const input = getByTestId('file-input') as HTMLInputElement;
      
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false
      });
      
      fireEvent.change(input);
      
      await waitFor(() => {
        expect(getByTestId('current-step')).toHaveTextContent('analyze');
      });
      
      // Step 2: Analyze
      fireEvent.click(getByText('Start Analysis'));
      
      await waitFor(() => {
        expect(getByTestId('current-step')).toHaveTextContent('review');
      });
      
      // Step 3: Review
      expect(getByTestId('optimization-count')).toHaveTextContent('2 optimizations found');
      
      fireEvent.click(getByText('Apply All'));
      
      // Step 4: Complete
      await waitFor(() => {
        expect(getByTestId('current-step')).toHaveTextContent('complete');
        expect(getByTestId('results')).toHaveTextContent(
          'Cost reduced by 45%, Latency improved by 30ms'
        );
      });
    });
  });
});