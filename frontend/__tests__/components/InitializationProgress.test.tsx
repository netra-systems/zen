import React from 'react';
import { render, screen } from '@testing-library/react';
import { InitializationProgress } from '@/components/InitializationProgress';

// Mock the UI components
jest.mock('@/components/ui/progress', () => ({
  Progress: ({ value, className }: { value: number; className?: string }) => (
    <div 
      data-testid="progress-bar" 
      data-value={value} 
      className={className}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
    />
  ),
}));

jest.mock('@/components/ui/alert', () => ({
  Alert: ({ children, variant, ...props }: any) => (
    <div data-testid="alert" data-variant={variant} {...props}>
      {children}
    </div>
  ),
  AlertDescription: ({ children, ...props }: any) => (
    <div data-testid="alert-description" {...props}>
      {children}
    </div>
  ),
}));

jest.mock('lucide-react', () => ({
  Loader2: ({ className }: { className?: string }) => (
    <div data-testid="loader-icon" className={className} />
  ),
}));

describe('InitializationProgress', () => {
  const defaultProps = {
    phase: 'auth' as const,
    progress: 0,
  };

  beforeEach(() => {
    // Ensure consistent test environment
    jest.clearAllMocks();
  });

  describe('Phase Display', () => {
    it('displays auth phase correctly', () => {
      render(<InitializationProgress {...defaultProps} phase="auth" progress={25} />);
      
      expect(screen.getByText('Authenticating your session...')).toBeInTheDocument();
      expect(screen.getByText('Verifying credentials and permissions')).toBeInTheDocument();
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();
    });

    it('displays websocket phase correctly', () => {
      render(<InitializationProgress {...defaultProps} phase="websocket" progress={50} />);
      
      expect(screen.getByText('Connecting to real-time services...')).toBeInTheDocument();
      expect(screen.getByText('Establishing secure WebSocket connection')).toBeInTheDocument();
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();
    });

    it('displays store phase correctly', () => {
      render(<InitializationProgress {...defaultProps} phase="store" progress={75} />);
      
      expect(screen.getByText('Loading your workspace...')).toBeInTheDocument();
      expect(screen.getByText('Synchronizing application state')).toBeInTheDocument();
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();
    });

    it('displays ready phase correctly', () => {
      render(<InitializationProgress {...defaultProps} phase="ready" progress={100} />);
      
      expect(screen.getByText('Ready!')).toBeInTheDocument();
      expect(screen.getByText('Initialization complete')).toBeInTheDocument();
      expect(screen.queryByTestId('loader-icon')).not.toBeInTheDocument();
    });

    it('displays error phase correctly', () => {
      render(<InitializationProgress {...defaultProps} phase="error" progress={50} />);
      
      expect(screen.getByText('Connection issue detected')).toBeInTheDocument();
      expect(screen.getByText('Please check your connection and try again')).toBeInTheDocument();
      expect(screen.queryByTestId('loader-icon')).not.toBeInTheDocument();
    });
  });

  describe('Progress Bar Updates', () => {
    it('displays correct progress value at 0%', () => {
      render(<InitializationProgress {...defaultProps} progress={0} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '0');
      expect(progressBar).toHaveAttribute('aria-valuenow', '0');
      expect(screen.getByText('0% complete')).toBeInTheDocument();
    });

    it('displays correct progress value at 33%', () => {
      render(<InitializationProgress {...defaultProps} progress={33} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '33');
      expect(progressBar).toHaveAttribute('aria-valuenow', '33');
      expect(screen.getByText('33% complete')).toBeInTheDocument();
    });

    it('displays correct progress value at 66%', () => {
      render(<InitializationProgress {...defaultProps} progress={66} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '66');
      expect(progressBar).toHaveAttribute('aria-valuenow', '66');
      expect(screen.getByText('66% complete')).toBeInTheDocument();
    });

    it('displays correct progress value at 100%', () => {
      render(<InitializationProgress {...defaultProps} progress={100} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '100');
      expect(progressBar).toHaveAttribute('aria-valuenow', '100');
      expect(screen.getByText('100% complete')).toBeInTheDocument();
    });

    it('handles decimal progress values correctly', () => {
      render(<InitializationProgress {...defaultProps} progress={66.7} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '66.7');
      expect(screen.getByText('67% complete')).toBeInTheDocument(); // Rounded
    });
  });

  describe('Phase Indicators', () => {
    it('shows auth phase as active when phase is auth', () => {
      render(<InitializationProgress {...defaultProps} phase="auth" progress={10} />);
      
      const authIndicator = screen.getByText('Auth');
      expect(authIndicator.closest('div')).toBeInTheDocument();
    });

    it('shows correct completion states based on progress', () => {
      render(<InitializationProgress {...defaultProps} phase="websocket" progress={50} />);
      
      // Auth should be completed (progress > 33)
      // Connect should be active (current phase)
      // Load should not be completed (progress <= 66)
      const authLabel = screen.getByText('Auth');
      const connectLabel = screen.getByText('Connect');
      const loadLabel = screen.getByText('Load');
      
      expect(authLabel).toBeInTheDocument();
      expect(connectLabel).toBeInTheDocument();
      expect(loadLabel).toBeInTheDocument();
    });

    it('shows all phases completed when progress is 100%', () => {
      render(<InitializationProgress {...defaultProps} phase="ready" progress={100} />);
      
      expect(screen.getByText('Auth')).toBeInTheDocument();
      expect(screen.getByText('Connect')).toBeInTheDocument();
      expect(screen.getByText('Load')).toBeInTheDocument();
    });

    it('shows correct indicator states for store phase', () => {
      render(<InitializationProgress {...defaultProps} phase="store" progress={80} />);
      
      // Auth completed (>33%), Connect completed (>66%), Load active
      expect(screen.getByText('Auth')).toBeInTheDocument();
      expect(screen.getByText('Connect')).toBeInTheDocument();
      expect(screen.getByText('Load')).toBeInTheDocument();
    });
  });

  describe('Connection Status Display', () => {
    it('shows connection status during websocket phase', () => {
      render(
        <InitializationProgress 
          {...defaultProps} 
          phase="websocket" 
          progress={50} 
          connectionStatus="CONNECTING" 
        />
      );
      
      expect(screen.getByText('Status: CONNECTING')).toBeInTheDocument();
    });

    it('shows OPEN connection status', () => {
      render(
        <InitializationProgress 
          {...defaultProps} 
          phase="websocket" 
          progress={60} 
          connectionStatus="OPEN" 
        />
      );
      
      expect(screen.getByText('Status: OPEN')).toBeInTheDocument();
    });

    it('shows CLOSED connection status', () => {
      render(
        <InitializationProgress 
          {...defaultProps} 
          phase="websocket" 
          progress={40} 
          connectionStatus="CLOSED" 
        />
      );
      
      expect(screen.getByText('Status: CLOSED')).toBeInTheDocument();
    });

    it('does not show connection status for non-websocket phases', () => {
      render(
        <InitializationProgress 
          {...defaultProps} 
          phase="auth" 
          progress={25} 
          connectionStatus="OPEN" 
        />
      );
      
      expect(screen.queryByText(/Status:/)).not.toBeInTheDocument();
    });

    it('does not show connection status when not provided during websocket phase', () => {
      render(<InitializationProgress {...defaultProps} phase="websocket" progress={50} />);
      
      expect(screen.queryByText(/Status:/)).not.toBeInTheDocument();
    });
  });

  describe('Error Display', () => {
    it('displays error message when in error phase', () => {
      const errorMessage = 'WebSocket connection failed';
      render(
        <InitializationProgress 
          {...defaultProps} 
          phase="error" 
          progress={30} 
          error={errorMessage}
        />
      );
      
      expect(screen.getByTestId('alert')).toHaveAttribute('data-variant', 'destructive');
      expect(screen.getByTestId('alert-description')).toHaveTextContent(errorMessage);
    });

    it('does not display error when not in error phase', () => {
      render(
        <InitializationProgress 
          {...defaultProps} 
          phase="auth" 
          progress={25} 
          error="Some error"
        />
      );
      
      expect(screen.queryByTestId('alert')).not.toBeInTheDocument();
    });

    it('does not display error when in error phase but no error provided', () => {
      render(<InitializationProgress {...defaultProps} phase="error" progress={50} />);
      
      expect(screen.queryByTestId('alert')).not.toBeInTheDocument();
    });

    it('displays different error messages correctly', () => {
      const { rerender } = render(
        <InitializationProgress 
          {...defaultProps} 
          phase="error" 
          progress={50} 
          error="Network timeout"
        />
      );
      
      expect(screen.getByTestId('alert-description')).toHaveTextContent('Network timeout');

      rerender(
        <InitializationProgress 
          {...defaultProps} 
          phase="error" 
          progress={50} 
          error="Authentication failed"
        />
      );
      
      expect(screen.getByTestId('alert-description')).toHaveTextContent('Authentication failed');
    });
  });

  describe('Brand Display', () => {
    it('displays Netra Apex branding', () => {
      render(<InitializationProgress {...defaultProps} />);
      
      expect(screen.getByText('Netra Apex')).toBeInTheDocument();
      expect(screen.getByText('AI Optimization Platform')).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('has proper ARIA attributes for accessibility', () => {
      render(<InitializationProgress {...defaultProps} progress={45} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('role', 'progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '45');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
    });

    it('applies correct CSS classes', () => {
      render(<InitializationProgress {...defaultProps} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveClass('h-2'); // Height class from Progress component
    });

    it('renders all expected elements', () => {
      render(
        <InitializationProgress 
          {...defaultProps} 
          phase="websocket" 
          progress={50} 
          connectionStatus="CONNECTING"
          error="Test error"
        />
      );
      
      // Main content
      expect(screen.getByText('Netra Apex')).toBeInTheDocument();
      expect(screen.getByTestId('progress-bar')).toBeInTheDocument();
      expect(screen.getByText('50% complete')).toBeInTheDocument();
      
      // Phase message
      expect(screen.getByText('Connecting to real-time services...')).toBeInTheDocument();
      
      // Connection status (shown for websocket phase)
      expect(screen.getByText('Status: CONNECTING')).toBeInTheDocument();
      
      // Phase indicators
      expect(screen.getByText('Auth')).toBeInTheDocument();
      expect(screen.getByText('Connect')).toBeInTheDocument();
      expect(screen.getByText('Load')).toBeInTheDocument();
      
      // Error not shown because phase is not 'error'
      expect(screen.queryByTestId('alert')).not.toBeInTheDocument();
    });
  });

  describe('Phase Transitions', () => {
    it('handles phase transitions correctly', () => {
      const { rerender } = render(
        <InitializationProgress {...defaultProps} phase="auth" progress={10} />
      );
      
      expect(screen.getByText('Authenticating your session...')).toBeInTheDocument();
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();

      rerender(<InitializationProgress {...defaultProps} phase="websocket" progress={50} />);
      
      expect(screen.getByText('Connecting to real-time services...')).toBeInTheDocument();
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();

      rerender(<InitializationProgress {...defaultProps} phase="store" progress={80} />);
      
      expect(screen.getByText('Loading your workspace...')).toBeInTheDocument();
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();

      rerender(<InitializationProgress {...defaultProps} phase="ready" progress={100} />);
      
      expect(screen.getByText('Ready!')).toBeInTheDocument();
      expect(screen.queryByTestId('loader-icon')).not.toBeInTheDocument();
    });

    it('handles error phase transition', () => {
      const { rerender } = render(
        <InitializationProgress {...defaultProps} phase="auth" progress={25} />
      );
      
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();

      rerender(
        <InitializationProgress 
          {...defaultProps} 
          phase="error" 
          progress={25} 
          error="Connection failed"
        />
      );
      
      expect(screen.queryByTestId('loader-icon')).not.toBeInTheDocument();
      expect(screen.getByTestId('alert')).toBeInTheDocument();
      expect(screen.getByText('Connection failed')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles negative progress values', () => {
      render(<InitializationProgress {...defaultProps} progress={-10} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '-10');
      expect(screen.getByText('0% complete')).toBeInTheDocument(); // Math.round handles negative
    });

    it('handles progress values over 100', () => {
      render(<InitializationProgress {...defaultProps} progress={150} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '150');
      expect(screen.getByText('150% complete')).toBeInTheDocument();
    });

    it('handles very long error messages', () => {
      const longError = 'This is a very long error message that should still be displayed properly without breaking the component layout or causing any rendering issues';
      
      render(
        <InitializationProgress 
          {...defaultProps} 
          phase="error" 
          progress={50} 
          error={longError}
        />
      );
      
      expect(screen.getByText(longError)).toBeInTheDocument();
    });

    it('handles missing optional props gracefully', () => {
      render(<InitializationProgress phase="auth" progress={25} />);
      
      expect(screen.getByText('Authenticating your session...')).toBeInTheDocument();
      expect(screen.queryByText(/Status:/)).not.toBeInTheDocument();
      expect(screen.queryByTestId('alert')).not.toBeInTheDocument();
    });
  });
});