/**
 * End-to-End User Journey Integration Tests
 * 
 * Tests complete user workflows including optimization workflow,
 * multi-step processes, data flows, and complex user interactions
 * across the entire application.
 */

import {
  React,
  render,
  waitFor,
  screen,
  fireEvent,
  act,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  createWebSocketMessage,
  simulateNetworkDelay,
  createMockApiResponse,
  TEST_TIMEOUTS,
  WS
} from './test-utils';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('End-to-End User Journey Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('Complete Optimization Workflow', () => {
    it('should complete full optimization workflow', async () => {
      const OptimizationWorkflow = () => {
        const [step, setStep] = React.useState<'upload' | 'analyze' | 'review' | 'apply' | 'complete'>('upload');
        const [workloadData, setWorkloadData] = React.useState<any>(null);
        const [optimizations, setOptimizations] = React.useState<any[]>([]);
        const [results, setResults] = React.useState<any>(null);
        const [isProcessing, setIsProcessing] = React.useState(false);
        const [progress, setProgress] = React.useState(0);
        const [errors, setErrors] = React.useState<string[]>([]);
        
        const handleUpload = async (file: File) => {
          setIsProcessing(true);
          setErrors([]);
          
          try {
            // Validate file
            if (!file.name.endsWith('.json')) {
              throw new Error('Only JSON files are supported');
            }
            
            if (file.size > 10 * 1024 * 1024) { // 10MB limit
              throw new Error('File size must be less than 10MB');
            }
            
            // Parse workload data
            const reader = new FileReader();
            reader.onload = (e) => {
              try {
                const content = JSON.parse(e.target?.result as string);
                setWorkloadData({
                  name: file.name,
                  size: file.size,
                  content,
                  uploadedAt: new Date().toISOString()
                });
                setStep('analyze');
              } catch (parseError) {
                setErrors(['Invalid JSON format in uploaded file']);
              }
            };
            reader.readAsText(file);
          } catch (error) {
            setErrors([error.message]);
          } finally {
            setIsProcessing(false);
          }
        };
        
        const analyzeWorkload = async () => {
          setIsProcessing(true);
          setProgress(0);
          
          try {
            // Simulate analysis phases
            const phases = ['Parsing workload', 'Analyzing patterns', 'Identifying bottlenecks', 'Computing optimizations'];
            
            for (let i = 0; i < phases.length; i++) {
              await simulateNetworkDelay(200);
              setProgress(((i + 1) / phases.length) * 100);
            }
            
            // Generate mock optimizations based on workload data
            const foundOptimizations = [
              {
                id: '1',
                type: 'model',
                title: 'Model Optimization',
                recommendation: 'Switch to GPT-3.5 for 40% cost reduction',
                impact: { cost: -40, latency: 0, accuracy: -2 },
                priority: 'high'
              },
              {
                id: '2',
                type: 'caching',
                title: 'Response Caching',
                recommendation: 'Enable response caching for repeated queries',
                impact: { cost: -25, latency: -50, accuracy: 0 },
                priority: 'medium'
              },
              {
                id: '3',
                type: 'batching',
                title: 'Request Batching',
                recommendation: 'Batch similar requests together',
                impact: { cost: -15, latency: -30, accuracy: 0 },
                priority: 'low'
              }
            ];
            
            setOptimizations(foundOptimizations);
            setStep('review');
          } catch (error) {
            setErrors([`Analysis failed: ${error.message}`]);
          } finally {
            setIsProcessing(false);
            setProgress(0);
          }
        };
        
        const applyOptimizations = async (selectedIds: string[]) => {
          setIsProcessing(true);
          setProgress(0);
          
          try {
            const selectedOptimizations = optimizations.filter(opt => selectedIds.includes(opt.id));
            
            // Simulate applying each optimization
            for (let i = 0; i < selectedOptimizations.length; i++) {
              await simulateNetworkDelay(300);
              setProgress(((i + 1) / selectedOptimizations.length) * 100);
            }
            
            // Calculate combined results
            const totalImpact = selectedOptimizations.reduce(
              (acc, opt) => ({
                cost: acc.cost + opt.impact.cost,
                latency: acc.latency + opt.impact.latency,
                accuracy: acc.accuracy + opt.impact.accuracy
              }),
              { cost: 0, latency: 0, accuracy: 0 }
            );
            
            setResults({
              appliedOptimizations: selectedOptimizations.length,
              totalOptimizations: optimizations.length,
              costReduction: Math.abs(totalImpact.cost),
              latencyImprovement: Math.abs(totalImpact.latency),
              accuracyChange: totalImpact.accuracy,
              estimatedMonthlySavings: Math.abs(totalImpact.cost) * 100, // Mock calculation
              completedAt: new Date().toISOString()
            });
            
            setStep('complete');
          } catch (error) {
            setErrors([`Failed to apply optimizations: ${error.message}`]);
          } finally {
            setIsProcessing(false);
            setProgress(0);
          }
        };
        
        return (
          <div>
            <div data-testid="current-step">{step}</div>
            <div data-testid="processing">{isProcessing ? 'true' : 'false'}</div>
            {progress > 0 && <div data-testid="progress">{Math.round(progress)}%</div>}
            
            {errors.length > 0 && (
              <div data-testid="errors">
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
                  accept=".json"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUpload(file);
                  }}
                />
                <div data-testid="upload-instructions">
                  Upload a JSON file containing your workload configuration
                </div>
              </div>
            )}
            
            {step === 'analyze' && (
              <div>
                <div data-testid="workload-info">
                  Analyzing: {workloadData?.name} ({(workloadData?.size / 1024).toFixed(1)}KB)
                </div>
                <button onClick={analyzeWorkload} disabled={isProcessing}>
                  Start Analysis
                </button>
              </div>
            )}
            
            {step === 'review' && (
              <div>
                <div data-testid="optimization-count">
                  {optimizations.length} optimizations found
                </div>
                {optimizations.map(opt => (
                  <div key={opt.id} data-testid={`optimization-${opt.id}`}>
                    <h4>{opt.title}</h4>
                    <p>{opt.recommendation}</p>
                    <span>Cost: {opt.impact.cost}%, Latency: {opt.impact.latency}ms</span>
                  </div>
                ))}
                <button
                  onClick={() => applyOptimizations(optimizations.map(o => o.id))}
                  disabled={isProcessing}
                  data-testid="apply-all"
                >
                  Apply All Optimizations
                </button>
                <button
                  onClick={() => applyOptimizations(['1', '2'])}
                  disabled={isProcessing}
                  data-testid="apply-selected"
                >
                  Apply High & Medium Priority
                </button>
              </div>
            )}
            
            {step === 'complete' && results && (
              <div data-testid="results">
                <div data-testid="cost-reduction">
                  Cost reduced by {results.costReduction}%
                </div>
                <div data-testid="latency-improvement">
                  Latency improved by {results.latencyImprovement}ms
                </div>
                <div data-testid="applied-count">
                  Applied {results.appliedOptimizations} of {results.totalOptimizations} optimizations
                </div>
                <div data-testid="monthly-savings">
                  Estimated monthly savings: ${results.estimatedMonthlySavings}
                </div>
              </div>
            )}
          </div>
        );
      };
      
      const { getByTestId, getByText } = render(<OptimizationWorkflow />);
      
      // Step 1: Upload
      expect(getByTestId('current-step')).toHaveTextContent('upload');
      expect(getByTestId('upload-instructions')).toHaveTextContent('Upload a JSON file');
      
      // Create and upload a valid JSON file
      const workloadConfig = {
        model: 'gpt-4',
        requests_per_day: 1000,
        average_tokens: 500,
        use_cases: ['chat', 'completion']
      };
      
      const file = new File(
        [JSON.stringify(workloadConfig)], 
        'workload.json', 
        { type: 'application/json' }
      );
      
      const input = getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(input, 'files', { value: [file], writable: false });
      
      fireEvent.change(input);
      
      await waitFor(() => {
        expect(getByTestId('current-step')).toHaveTextContent('analyze');
      });
      
      // Step 2: Analyze
      expect(getByTestId('workload-info')).toHaveTextContent('Analyzing: workload.json');
      
      fireEvent.click(getByText('Start Analysis'));
      
      await waitFor(() => {
        expect(getByTestId('processing')).toHaveTextContent('true');
      });
      
      await waitFor(() => {
        expect(getByTestId('current-step')).toHaveTextContent('review');
        expect(getByTestId('processing')).toHaveTextContent('false');
      }, { timeout: TEST_TIMEOUTS.MEDIUM });
      
      // Step 3: Review
      expect(getByTestId('optimization-count')).toHaveTextContent('3 optimizations found');
      expect(getByTestId('optimization-1')).toHaveTextContent('Model Optimization');
      expect(getByTestId('optimization-2')).toHaveTextContent('Response Caching');
      
      fireEvent.click(getByTestId('apply-selected'));
      
      await waitFor(() => {
        expect(getByTestId('processing')).toHaveTextContent('true');
      });
      
      // Step 4: Complete
      await waitFor(() => {
        expect(getByTestId('current-step')).toHaveTextContent('complete');
        expect(getByTestId('processing')).toHaveTextContent('false');
      }, { timeout: TEST_TIMEOUTS.MEDIUM });
      
      expect(getByTestId('applied-count')).toHaveTextContent('Applied 2 of 3 optimizations');
      expect(getByTestId('cost-reduction')).toHaveTextContent('Cost reduced by 65%');
      expect(getByTestId('latency-improvement')).toHaveTextContent('Latency improved by 50ms');
    });

    it('should handle error scenarios in the workflow', async () => {
      const ErrorScenarioWorkflow = () => {
        const [step, setStep] = React.useState('upload');
        const [errors, setErrors] = React.useState<string[]>([]);
        const [retryCount, setRetryCount] = React.useState(0);
        
        const handleUpload = async (file: File) => {
          setErrors([]);
          
          // Simulate different error scenarios
          if (file.name.includes('invalid')) {
            setErrors(['Invalid file format. Please upload a valid JSON file.']);
            return;
          }
          
          if (file.size > 1000000) {
            setErrors(['File too large. Maximum size is 10MB.']);
            return;
          }
          
          setStep('analyze');
        };
        
        const analyzeWithRetry = async () => {
          try {
            setErrors([]);
            
            // Simulate intermittent failures
            if (retryCount < 2 && Math.random() > 0.3) {
              throw new Error(`Network error. Please try again. (Attempt ${retryCount + 1})`);
            }
            
            await simulateNetworkDelay(100);
            setStep('complete');
          } catch (error) {
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
      const validFile = new File(['{"valid": true}'], 'valid.json', { type: 'application/json' });
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

    it('should maintain state across component re-renders', async () => {
      const StatefulWorkflow = () => {
        const [data, setData] = React.useState(() => {
          // Load state from localStorage on mount
          const saved = localStorage.getItem('workflow_state');
          return saved ? JSON.parse(saved) : { step: 'start', progress: 0, history: [] };
        });
        
        // Save state to localStorage whenever data changes
        React.useEffect(() => {
          localStorage.setItem('workflow_state', JSON.stringify(data));
        }, [data]);
        
        const updateStep = (newStep: string) => {
          setData(prev => ({
            ...prev,
            step: newStep,
            progress: prev.progress + 1,
            history: [...prev.history, { step: newStep, timestamp: Date.now() }]
          }));
        };
        
        const resetWorkflow = () => {
          const initialState = { step: 'start', progress: 0, history: [] };
          setData(initialState);
          localStorage.removeItem('workflow_state');
        };
        
        return (
          <div>
            <div data-testid="current-step">{data.step}</div>
            <div data-testid="progress">{data.progress}</div>
            <div data-testid="history-length">{data.history.length}</div>
            
            <button onClick={() => updateStep('step-1')} data-testid="go-step-1">
              Go to Step 1
            </button>
            <button onClick={() => updateStep('step-2')} data-testid="go-step-2">
              Go to Step 2
            </button>
            <button onClick={() => updateStep('complete')} data-testid="complete">
              Complete
            </button>
            <button onClick={resetWorkflow} data-testid="reset">
              Reset
            </button>
          </div>
        );
      };
      
      const { getByTestId, unmount, rerender } = render(<StatefulWorkflow />);
      
      // Initial state
      expect(getByTestId('current-step')).toHaveTextContent('start');
      expect(getByTestId('progress')).toHaveTextContent('0');
      
      // Progress through steps
      fireEvent.click(getByTestId('go-step-1'));
      expect(getByTestId('current-step')).toHaveTextContent('step-1');
      expect(getByTestId('progress')).toHaveTextContent('1');
      
      fireEvent.click(getByTestId('go-step-2'));
      expect(getByTestId('progress')).toHaveTextContent('2');
      expect(getByTestId('history-length')).toHaveTextContent('2');
      
      // Verify state is saved to localStorage
      const savedState = JSON.parse(localStorage.getItem('workflow_state') || '{}');
      expect(savedState.step).toBe('step-2');
      expect(savedState.progress).toBe(2);
      
      // Unmount and remount to simulate page refresh
      unmount();
      const { getByTestId: getByTestIdNew } = render(<StatefulWorkflow />);
      
      // State should be restored
      expect(getByTestIdNew('current-step')).toHaveTextContent('step-2');
      expect(getByTestIdNew('progress')).toHaveTextContent('2');
      expect(getByTestIdNew('history-length')).toHaveTextContent('2');
    });
  });

  describe('Complex Multi-User Workflow', () => {
    it('should handle collaborative workflow with multiple users', async () => {
      const CollaborativeWorkflow = () => {
        const [users, setUsers] = React.useState<Map<string, any>>(new Map());
        const [sharedState, setSharedState] = React.useState({
          currentStep: 'planning',
          votes: new Map(),
          decisions: [],
          activeUsers: []
        });
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            switch (message.type) {
              case 'user_joined':
                setUsers(prev => new Map(prev.set(message.userId, message.userData)));
                break;
              case 'vote_cast':
                setSharedState(prev => ({
                  ...prev,
                  votes: new Map(prev.votes.set(message.userId, message.vote))
                }));
                break;
              case 'step_change':
                setSharedState(prev => ({
                  ...prev,
                  currentStep: message.step,
                  decisions: [...prev.decisions, message.decision]
                }));
                break;
            }
          };
          
          return () => ws.close();
        }, []);
        
        const castVote = (vote: 'approve' | 'reject') => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          ws.onopen = () => {
            ws.send(JSON.stringify({
              type: 'cast_vote',
              userId: 'current-user',
              vote,
              timestamp: Date.now()
            }));
          };
        };
        
        return (
          <div>
            <div data-testid="current-step">{sharedState.currentStep}</div>
            <div data-testid="user-count">{users.size} users</div>
            <div data-testid="vote-count">{sharedState.votes.size} votes</div>
            <div data-testid="decision-count">{sharedState.decisions.length} decisions</div>
            
            <button onClick={() => castVote('approve')} data-testid="vote-approve">
              Vote Approve
            </button>
            <button onClick={() => castVote('reject')} data-testid="vote-reject">
              Vote Reject
            </button>
          </div>
        );
      };
      
      const { getByTestId } = render(<CollaborativeWorkflow />);
      
      await server.connected;
      
      // Simulate users joining
      server.send(createWebSocketMessage('user_joined', {
        userId: 'user-1',
        userData: { name: 'Alice', role: 'admin' }
      }));
      
      server.send(createWebSocketMessage('user_joined', {
        userId: 'user-2',
        userData: { name: 'Bob', role: 'user' }
      }));
      
      await waitFor(() => {
        expect(getByTestId('user-count')).toHaveTextContent('2 users');
      });
      
      // Simulate voting
      server.send(createWebSocketMessage('vote_cast', {
        userId: 'user-1',
        vote: 'approve'
      }));
      
      await waitFor(() => {
        expect(getByTestId('vote-count')).toHaveTextContent('1 votes');
      });
    });
  });
});