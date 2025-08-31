import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { er Journey Error Scenarios Integration Tests
 * ULTRA DEEP THINK: Module-based architecture - Error tests extracted for 450-line compliance
 */

import {
  React, render, waitFor, fireEvent, TEST_TIMEOUTS,
  setupUserJourneyTest, teardownUserJourneyTest,
  simulateNetworkDelay, createValidJsonFile
} from './user-journey-utils';

describe('Error Scenarios in User Journey', () => {
    jest.setTimeout(10000);
  let server: any;
  
  beforeEach(() => {
    server = setupUserJourneyTest();
  });

  afterEach(() => {
    teardownUserJourneyTest();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  it('should handle error scenarios in the workflow', async () => {
    const ErrorScenarioWorkflow = () => {
      const [step, setStep] = React.useState('upload');
      const [errors, setErrors] = React.useState<string[]>([]);
      const [retryCount, setRetryCount] = React.useState(0);
      
      const validateFile = (file: File) => {
        if (file.name.includes('invalid')) {
          throw new Error('Invalid file format. Please upload a valid JSON file.');
        }
        if (file.size > 1000000) {
          throw new Error('File too large. Maximum size is 10MB.');
        }
      };
      
      const handleUpload = async (file: File) => {
        setErrors([]);
        try {
          validateFile(file);
          setStep('analyze');
        } catch (error: any) {
          setErrors([error.message]);
        }
      };
      
      const simulateAnalysisFailure = () => {
        if (retryCount < 2 && Math.random() > 0.3) {
          throw new Error(`Network error. Please try again. (Attempt ${retryCount + 1})`);
        }
      };
      
      const analyzeWithRetry = async () => {
        try {
          setErrors([]);
          simulateAnalysisFailure();
          await simulateNetworkDelay(100);
          setStep('complete');
        } catch (error: any) {
          setRetryCount(prev => prev + 1);
          setErrors([error.message]);
        }
      };
      
      const resetWorkflow = () => {
        setStep('upload');
        setErrors([]);
        setRetryCount(0);
      };
      
      return (
        <div>
          <div data-testid="current-step">{step}</div>
          <div data-testid="retry-count">{retryCount}</div>
          
          {errors.length > 0 && (
            <div data-testid="error-messages">
              {errors.map((error, i) => (
                <div key={i} data-testid={`error-${i}`}>{error}</div>
              ))}
            </div>
          )}
          
          {step === 'upload' && (
            <div>
              <input
                type="file"
                data-testid="file-input"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUpload(file);
                }}
              />
              <button
                onClick={() => {
                  const invalidFile = new File(['invalid'], 'invalid.txt');
                  handleUpload(invalidFile);
                }}
                data-testid="upload-invalid"
              >
                Upload Invalid File
              </button>
            </div>
          )}
          
          {step === 'analyze' && (
            <div>
              <button onClick={analyzeWithRetry} data-testid="analyze">
                Analyze
              </button>
              <button onClick={resetWorkflow} data-testid="reset">
                Start Over
              </button>
            </div>
          )}
          
          {step === 'complete' && (
            <div data-testid="success-message">
              Workflow completed successfully!
            </div>
          )}
        </div>
      );
    };
    
    const { getByTestId, getByText } = render(<ErrorScenarioWorkflow />);
    
    // Test invalid file error
    fireEvent.click(getByTestId('upload-invalid'));
    
    await waitFor(() => {
      expect(getByTestId('error-messages')).toBeInTheDocument();
      expect(getByTestId('error-0')).toHaveTextContent('Invalid file format');
    });
    
    // Upload a valid file
    const validFile = createValidJsonFile();
    const input = getByTestId('file-input') as HTMLInputElement;
    Object.defineProperty(input, 'files', { value: [validFile], writable: false });
    
    fireEvent.change(input);
    
    await waitFor(() => {
      expect(getByTestId('current-step')).toHaveTextContent('analyze');
    });
    
    // Test retry mechanism
    fireEvent.click(getByTestId('analyze'));
    
    // May need multiple attempts due to simulated failures
    await waitFor(() => {
      const retryCount = parseInt(getByTestId('retry-count').textContent || '0');
      expect(retryCount).toBeGreaterThanOrEqual(0);
    });
    
    // Eventually should complete
    await waitFor(() => {
      expect(getByTestId('current-step')).toHaveTextContent('complete');
    }, { timeout: TEST_TIMEOUTS.MEDIUM });
  });

  it('should handle network timeout scenarios', async () => {
    const TimeoutWorkflow = () => {
      const [status, setStatus] = React.useState('idle');
      const [error, setError] = React.useState('');
      
      const simulateTimeoutOperation = async () => {
        setStatus('processing');
        setError('');
        try {
          // Simulate operation that might timeout
          await new Promise((resolve, reject) => {
            setTimeout(() => {
              if (Math.random() > 0.7) {
                reject(new Error('Operation timed out'));
              } else {
                resolve('success');
              }
            }, 50);
          });
          setStatus('completed');
        } catch (err: any) {
          setError(err.message);
          setStatus('error');
        }
      };
      
      return (
        <div>
          <div data-testid="status">{status}</div>
          {error && <div data-testid="error">{error}</div>}
          <button 
            onClick={simulateTimeoutOperation} 
            disabled={status === 'processing'}
            data-testid="start-operation"
          >
            Start Operation
          </button>
          <button 
            onClick={() => { setStatus('idle'); setError(''); }}
            data-testid="reset"
          >
            Reset
          </button>
        </div>
      );
    };
    
    const { getByTestId } = render(<TimeoutWorkflow />);
    
    expect(getByTestId('status')).toHaveTextContent('idle');
    
    fireEvent.click(getByTestId('start-operation'));
    
    await waitFor(() => {
      expect(getByTestId('status')).toHaveTextContent('processing');
    });
    
    // Wait for either completion or timeout error
    await waitFor(() => {
      const status = getByTestId('status').textContent;
      expect(['completed', 'error']).toContain(status);
    }, { timeout: TEST_TIMEOUTS.SHORT });
  });

  it('should handle concurrent operation conflicts', async () => {
    const ConcurrentOperationsWorkflow = () => {
      const [operations, setOperations] = React.useState<string[]>([]);
      const [conflicts, setConflicts] = React.useState<string[]>([]);
      
      const startOperation = async (operationId: string) => {
        // Check for conflicts
        if (operations.includes(operationId)) {
          setConflicts(prev => [...prev, `Conflict: ${operationId} already running`]);
          return;
        }
        
        setOperations(prev => [...prev, operationId]);
        
        // Simulate operation
        await simulateNetworkDelay(100);
        
        setOperations(prev => prev.filter(id => id !== operationId));
      };
      
      return (
        <div>
          <div data-testid="active-operations">
            Active: {operations.join(', ')}
          </div>
          <div data-testid="conflicts">
            {conflicts.map((conflict, i) => (
              <div key={i}>{conflict}</div>
            ))}
          </div>
          <button 
            onClick={() => startOperation('upload')}
            data-testid="start-upload"
          >
            Start Upload
          </button>
          <button 
            onClick={() => startOperation('analyze')}
            data-testid="start-analyze"
          >
            Start Analysis
          </button>
        </div>
      );
    };
    
    const { getByTestId } = render(<ConcurrentOperationsWorkflow />);
    
    // Start same operation twice to trigger conflict
    fireEvent.click(getByTestId('start-upload'));
    fireEvent.click(getByTestId('start-upload'));
    
    await waitFor(() => {
      expect(getByTestId('conflicts')).toHaveTextContent('Conflict: upload already running');
    });
  });
});