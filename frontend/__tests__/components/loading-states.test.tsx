/**
 * Loading States Test
 * Tests various loading states and skeleton components
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

describe('Loading States', () => {
  it('should display loading spinner during async operations', async () => {
    const LoadingSpinnerComponent: React.FC = () => {
      const [isLoading, setIsLoading] = React.useState(true);
      const [data, setData] = React.useState<string>('');
      
      React.useEffect(() => {
        const fetchData = async () => {
          // Simulate API call
          setTimeout(() => {
            setData('Data loaded successfully');
            setIsLoading(false);
          }, 100);
        };
        
        fetchData();
      }, []);
      
      if (isLoading) {
        return (
          <div data-testid="loading-spinner">
            <div>Loading...</div>
          </div>
        );
      }
      
      return (
        <div data-testid="loaded-content">
          {data}
        </div>
      );
    };

    render(<LoadingSpinnerComponent />);
    
    // Check loading state
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByTestId('loaded-content')).toBeInTheDocument();
      expect(screen.getByText('Data loaded successfully')).toBeInTheDocument();
    });
    
    // Loading spinner should be gone
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
  });

  it('should display skeleton loading for list items', async () => {
    const SkeletonLoadingComponent: React.FC = () => {
      const [isLoading, setIsLoading] = React.useState(true);
      const [items, setItems] = React.useState<string[]>([]);
      
      React.useEffect(() => {
        const loadItems = async () => {
          // Simulate loading delay
          setTimeout(() => {
            setItems(['Item 1', 'Item 2', 'Item 3']);
            setIsLoading(false);
          }, 150);
        };
        
        loadItems();
      }, []);
      
      if (isLoading) {
        return (
          <div data-testid="skeleton-container">
            {[1, 2, 3].map(i => (
              <div key={i} data-testid={`skeleton-item-${i}`}>
                <div style={{ width: '100%', height: '20px', backgroundColor: '#f0f0f0', marginBottom: '8px' }} />
                <div style={{ width: '70%', height: '16px', backgroundColor: '#e0e0e0' }} />
              </div>
            ))}
          </div>
        );
      }
      
      return (
        <div data-testid="items-container">
          {items.map(item => (
            <div key={item} data-testid={`item-${item.replace(' ', '-').toLowerCase()}`}>
              {item}
            </div>
          ))}
        </div>
      );
    };

    render(<SkeletonLoadingComponent />);
    
    // Check skeleton loading
    expect(screen.getByTestId('skeleton-container')).toBeInTheDocument();
    expect(screen.getByTestId('skeleton-item-1')).toBeInTheDocument();
    expect(screen.getByTestId('skeleton-item-2')).toBeInTheDocument();
    expect(screen.getByTestId('skeleton-item-3')).toBeInTheDocument();
    
    // Wait for items to load
    await waitFor(() => {
      expect(screen.getByTestId('items-container')).toBeInTheDocument();
      expect(screen.getByTestId('item-item-1')).toBeInTheDocument();
      expect(screen.getByTestId('item-item-2')).toBeInTheDocument();
      expect(screen.getByTestId('item-item-3')).toBeInTheDocument();
    });
  });

  it('should handle loading error states', async () => {
    const LoadingErrorComponent: React.FC = () => {
      const [loadingState, setLoadingState] = React.useState<'loading' | 'error' | 'success'>('loading');
      const [error, setError] = React.useState<string>('');
      
      React.useEffect(() => {
        const simulateError = async () => {
          setTimeout(() => {
            setError('Failed to load data');
            setLoadingState('error');
          }, 100);
        };
        
        simulateError();
      }, []);
      
      if (loadingState === 'loading') {
        return <div data-testid="loading">Loading...</div>;
      }
      
      if (loadingState === 'error') {
        return (
          <div data-testid="error-state">
            <div data-testid="error-message">{error}</div>
            <button 
              onClick={() => setLoadingState('loading')}
              data-testid="retry-button"
            >
              Retry
            </button>
          </div>
        );
      }
      
      return <div data-testid="success">Data loaded</div>;
    };

    render(<LoadingErrorComponent />);
    
    // Initially loading
    expect(screen.getByTestId('loading')).toBeInTheDocument();
    
    // Wait for error state
    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toBeInTheDocument();
      expect(screen.getByTestId('error-message')).toHaveTextContent('Failed to load data');
      expect(screen.getByTestId('retry-button')).toBeInTheDocument();
    });
  });

  it('should display progress indicator for multi-step operations', async () => {
    const ProgressIndicatorComponent: React.FC = () => {
      const [currentStep, setCurrentStep] = React.useState(0);
      const [isComplete, setIsComplete] = React.useState(false);
      
      const steps = ['Step 1', 'Step 2', 'Step 3'];
      
      React.useEffect(() => {
        const progressSteps = async () => {
          for (let i = 0; i < steps.length; i++) {
            await new Promise(resolve => setTimeout(resolve, 50));
            setCurrentStep(i + 1);
          }
          setIsComplete(true);
        };
        
        progressSteps();
      }, []);
      
      if (isComplete) {
        return <div data-testid="completed">All steps completed!</div>;
      }
      
      return (
        <div data-testid="progress-container">
          <div data-testid="current-step">
            {currentStep === 0 ? 'Starting...' : `Completed: ${steps[currentStep - 1]}`}
          </div>
          <div data-testid="progress-indicator">
            {currentStep}/{steps.length} steps
          </div>
        </div>
      );
    };

    render(<ProgressIndicatorComponent />);
    
    // Initially starting
    expect(screen.getByTestId('current-step')).toHaveTextContent('Starting...');
    
    // Wait for progress
    await waitFor(() => {
      expect(screen.getByTestId('current-step')).toHaveTextContent('Completed: Step 3');
    });
    
    // Wait for completion
    await waitFor(() => {
      expect(screen.getByTestId('completed')).toHaveTextContent('All steps completed!');
    });
  });
});