/**
 * Optimization Workflow Test Helpers
 * Extracted components and helpers for end-to-end journey tests
 * Keeps test functions ≤8 lines
 */

import React from 'react';

export const createOptimizationWorkflowComponent = () => {
  return () => {
    const [step, setStep] = React.useState('upload');
    const [workloadData, setWorkloadData] = React.useState<any>(null);
    const [optimizations, setOptimizations] = React.useState<any[]>([]);
    const [results, setResults] = React.useState<any>(null);
    
    const handleUpload = (file: File) => {
      setWorkloadData({ name: file.name, size: file.size });
      setStep('analyze');
    };
    
    const analyzeWorkload = async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
      setOptimizations([
        { id: '1', type: 'model', recommendation: 'Switch to GPT-3.5' },
        { id: '2', type: 'caching', recommendation: 'Enable response caching' }
      ]);
      setStep('review');
    };
    
    const applyOptimizations = async () => {
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
};

export const createTestFile = () => {
  return new File(['workload data'], 'workload.json', { type: 'application/json' });
};

export const simulateFileInput = (input: HTMLInputElement, file: File) => {
  Object.defineProperty(input, 'files', {
    value: [file],
    writable: false
  });
};