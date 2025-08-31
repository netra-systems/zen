/**
 * Error Boundary Test
 * Tests error boundaries and error recovery mechanisms
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock console.error to prevent error output in tests
const originalError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalError;
});

class TestErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ComponentType<{ error: Error }> },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ComponentType<{ error: Error }> }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error for monitoring
  }

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return <FallbackComponent error={this.state.error} />;
      }
      
      return (
        <div data-testid="error-fallback">
          <h2>Something went wrong</h2>
          <p data-testid="error-message">{this.state.error.message}</p>
          <button
            data-testid="retry-button"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

describe('Error Boundary', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should catch and display component errors', () => {
    const ThrowingComponent: React.FC = () => {
      throw new Error('Test error message');
    };

    render(
      <TestErrorBoundary>
        <ThrowingComponent />
      </TestErrorBoundary>
    );

    expect(screen.getByTestId('error-fallback')).toBeInTheDocument();
    expect(screen.getByTestId('error-message')).toHaveTextContent('Test error message');
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('should recover from errors when retry is clicked', () => {
    let shouldThrow = true;

    const ConditionallyThrowingComponent: React.FC = () => {
      if (shouldThrow) {
        throw new Error('Initial error');
      }
      return <div data-testid="success-content">Component loaded successfully</div>;
    };

    render(
      <TestErrorBoundary>
        <ConditionallyThrowingComponent />
      </TestErrorBoundary>
    );

    // Initially shows error
    expect(screen.getByTestId('error-fallback')).toBeInTheDocument();

    // Change condition and retry
    shouldThrow = false;
    fireEvent.click(screen.getByTestId('retry-button'));

    // Should now show success content
    expect(screen.getByTestId('success-content')).toBeInTheDocument();
    expect(screen.queryByTestId('error-fallback')).not.toBeInTheDocument();
  });

  it('should use custom fallback component when provided', () => {
    const CustomFallback: React.FC<{ error: Error }> = ({ error }) => (
      <div data-testid="custom-fallback">
        <h3>Custom Error Handler</h3>
        <p data-testid="custom-error-message">{error.message}</p>
      </div>
    );

    const ThrowingComponent: React.FC = () => {
      throw new Error('Custom error test');
    };

    render(
      <TestErrorBoundary fallback={CustomFallback}>
        <ThrowingComponent />
      </TestErrorBoundary>
    );

    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.getByText('Custom Error Handler')).toBeInTheDocument();
    expect(screen.getByTestId('custom-error-message')).toHaveTextContent('Custom error test');
  });

  it('should handle async errors', async () => {
    const AsyncErrorComponent: React.FC = () => {
      const [error, setError] = React.useState<Error | null>(null);

      React.useEffect(() => {
        const simulateAsyncError = async () => {
          try {
            // Simulate async operation that fails
            await new Promise((_, reject) => {
              setTimeout(() => reject(new Error('Async operation failed')), 10);
            });
          } catch (err) {
            setError(err as Error);
          }
        };

        simulateAsyncError();
      }, []);

      if (error) {
        throw error;
      }

      return <div data-testid="async-content">Async content loaded</div>;
    };

    render(
      <TestErrorBoundary>
        <AsyncErrorComponent />
      </TestErrorBoundary>
    );

    // Wait for async error to be thrown
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(screen.getByTestId('error-fallback')).toBeInTheDocument();
    expect(screen.getByTestId('error-message')).toHaveTextContent('Async operation failed');
  });

  it('should not catch errors in event handlers', () => {
    const EventHandlerErrorComponent: React.FC = () => {
      const [hasError, setHasError] = React.useState(false);

      const handleClick = () => {
        try {
          throw new Error('Event handler error');
        } catch (error) {
          setHasError(true);
        }
      };

      if (hasError) {
        return <div data-testid="event-error">Event handler error occurred</div>;
      }

      return (
        <div>
          <button data-testid="error-button" onClick={handleClick}>
            Click to trigger error
          </button>
          <div data-testid="normal-content">Normal content</div>
        </div>
      );
    };

    render(
      <TestErrorBoundary>
        <EventHandlerErrorComponent />
      </TestErrorBoundary>
    );

    // Click button to trigger error in event handler
    fireEvent.click(screen.getByTestId('error-button'));

    // Error boundary should not catch this, component should handle it
    expect(screen.getByTestId('event-error')).toBeInTheDocument();
    expect(screen.queryByTestId('error-fallback')).not.toBeInTheDocument();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});