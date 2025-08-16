/**
 * User Journey Workflow Integration Tests
 * ULTRA DEEP THINK: Module-based architecture - Workflow tests extracted for 300-line compliance
 */

import {
  React, render, waitFor, fireEvent, TEST_TIMEOUTS,
  setupUserJourneyTest, teardownUserJourneyTest,
  validateFileType, validateFileSize, parseFileContent,
  createMockOptimizations, simulateAnalysisPhases, calculateTotalImpact,
  createResults, simulateOptimizationApplication, createWorkloadConfigFile,
  expectSuccessfulUpload, expectSuccessfulAnalysis, expectCompletedWorkflow
} from './user-journey-utils';

describe('Complete Optimization Workflow Tests', () => {
  let server: any;
  
  beforeEach(() => {
    server = setupUserJourneyTest();
  });

  afterEach(() => {
    teardownUserJourneyTest();
  });

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
          validateFileType(file);
          validateFileSize(file);
          await parseFileContent(file, setWorkloadData, setStep, setErrors);
        } catch (error: any) {
          setErrors([error.message]);
        } finally {
          setIsProcessing(false);
        }
      };
      
      const analyzeWorkload = async () => {
        setIsProcessing(true);
        setProgress(0);
        try {
          await simulateAnalysisPhases(setProgress);
          const foundOptimizations = createMockOptimizations();
          setOptimizations(foundOptimizations);
          setStep('review');
        } catch (error: any) {
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
          await simulateOptimizationApplication(selectedOptimizations, setProgress);
          const totalImpact = calculateTotalImpact(selectedOptimizations);
          setResults(createResults(selectedOptimizations, optimizations, totalImpact));
          setStep('complete');
        } catch (error: any) {
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
    const file = createWorkloadConfigFile();
    const input = getByTestId('file-input') as HTMLInputElement;
    Object.defineProperty(input, 'files', { value: [file], writable: false });
    
    fireEvent.change(input);
    
    await waitFor(() => {
      expectSuccessfulUpload(getByTestId);
    });
    
    // Step 2: Analyze
    expect(getByTestId('workload-info')).toHaveTextContent('Analyzing: workload.json');
    
    fireEvent.click(getByText('Start Analysis'));
    
    await waitFor(() => {
      expect(getByTestId('processing')).toHaveTextContent('true');
    });
    
    await waitFor(() => {
      expectSuccessfulAnalysis(getByTestId);
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
      expectCompletedWorkflow(getByTestId);
    }, { timeout: TEST_TIMEOUTS.MEDIUM });
    
    expect(getByTestId('applied-count')).toHaveTextContent('Applied 2 of 3 optimizations');
    expect(getByTestId('cost-reduction')).toHaveTextContent('Cost reduced by 65%');
    expect(getByTestId('latency-improvement')).toHaveTextContent('Latency improved by 50ms');
  });

  it('should validate file requirements during upload', async () => {
    const FileValidationWorkflow = () => {
      const [errors, setErrors] = React.useState<string[]>([]);
      
      const handleFileValidation = (file: File) => {
        setErrors([]);
        try {
          validateFileType(file);
          validateFileSize(file);
          setErrors(['File validation passed']);
        } catch (error: any) {
          setErrors([error.message]);
        }
      };
      
      return (
        <div>
          {errors.length > 0 && (
            <div data-testid="validation-result">
              {errors[0]}
            </div>
          )}
          <button
            onClick={() => {
              const validFile = createWorkloadConfigFile();
              handleFileValidation(validFile);
            }}
            data-testid="test-valid-file"
          >
            Test Valid File
          </button>
          <button
            onClick={() => {
              const invalidFile = new File(['content'], 'test.txt', { type: 'text/plain' });
              handleFileValidation(invalidFile);
            }}
            data-testid="test-invalid-type"
          >
            Test Invalid Type
          </button>
        </div>
      );
    };
    
    const { getByTestId } = render(<FileValidationWorkflow />);
    
    // Test valid file
    fireEvent.click(getByTestId('test-valid-file'));
    await waitFor(() => {
      expect(getByTestId('validation-result')).toHaveTextContent('File validation passed');
    });
    
    // Test invalid file type
    fireEvent.click(getByTestId('test-invalid-type'));
    await waitFor(() => {
      expect(getByTestId('validation-result')).toHaveTextContent('Only JSON files are supported');
    });
  });
});