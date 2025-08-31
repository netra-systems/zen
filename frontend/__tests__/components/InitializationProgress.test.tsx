import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { InitializationProgress } from '@/components/InitializationProgress';

// Mock the UI components
jest.mock('@/components/ui/progress', () => ({
  Progress: ({ value, className }: { value: number; className?: string }) => (
    <div 
      data-testid="progress-bar" 
      className={className}
      role="progressbar" 
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
    />
  )
}));

jest.mock('@/components/ui/alert', () => ({
  Alert: ({ children, variant }: { children: React.ReactNode; variant?: string }) => (
    <div data-testid="alert" data-variant={variant}>{children}</div>
  ),
  AlertDescription: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="alert-description">{children}</div>
  )
}));

jest.mock('lucide-react', () => ({
  Loader2: ({ className }: { className?: string }) => (
    <div data-testid="loader" className={className}>Loading...</div>
  )
}));

describe('InitializationProgress', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  describe('Phase Messages and Details', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('displays correct message and detail for auth phase', () => {
      render(<InitializationProgress phase="auth" progress={20} />);
      
      expect(screen.getByText('Authenticating your session...')).toBeInTheDocument();
      expect(screen.getByText('Verifying credentials and permissions')).toBeInTheDocument();
      expect(screen.getByTestId('loader')).toBeInTheDocument();
    });

    it('displays correct message and detail for websocket phase', () => {
      render(<InitializationProgress phase="websocket" progress={50} />);
      
      expect(screen.getByText('Connecting to real-time services...')).toBeInTheDocument();
      expect(screen.getByText('Establishing secure WebSocket connection')).toBeInTheDocument();
      expect(screen.getByTestId('loader')).toBeInTheDocument();
    });

    it('displays correct message and detail for store phase', () => {
      render(<InitializationProgress phase="store" progress={80} />);
      
      expect(screen.getByText('Loading your workspace...')).toBeInTheDocument();
      expect(screen.getByText('Synchronizing application state')).toBeInTheDocument();
      expect(screen.getByTestId('loader')).toBeInTheDocument();
    });

    it('displays correct message and detail for ready phase', () => {
      render(<InitializationProgress phase="ready" progress={100} />);
      
      expect(screen.getByText('Ready!')).toBeInTheDocument();
      expect(screen.getByText('Initialization complete')).toBeInTheDocument();
      expect(screen.queryByTestId('loader')).not.toBeInTheDocument();
    });

    it('displays correct message and detail for error phase', () => {
      render(<InitializationProgress phase="error" progress={0} />);
      
      expect(screen.getByText('Connection issue detected')).toBeInTheDocument();
      expect(screen.getByText('Please check your connection and try again')).toBeInTheDocument();
      expect(screen.queryByTestId('loader')).not.toBeInTheDocument();
    });
  });

  describe('Progress Bar', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('displays progress bar with correct value', () => {
      render(<InitializationProgress phase="auth" progress={25} />);
      
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '25');
    });

    it('displays progress percentage text', () => {
      render(<InitializationProgress phase="websocket" progress={67} />);
      
      expect(screen.getByText('67% complete')).toBeInTheDocument();
    });

    it('handles edge case progress values', () => {
      const { rerender } = render(<InitializationProgress phase="auth" progress={0} />);
      expect(screen.getByText('0% complete')).toBeInTheDocument();
      
      rerender(<InitializationProgress phase="store" progress={100} />);
      expect(screen.getByText('100% complete')).toBeInTheDocument();
      
      // Test values outside normal range
      rerender(<InitializationProgress phase="auth" progress={-10} />);
      expect(screen.getByText('-10% complete')).toBeInTheDocument();
      
      rerender(<InitializationProgress phase="auth" progress={150} />);
      expect(screen.getByText('150% complete')).toBeInTheDocument();
    });
    
    it('handles NaN and undefined progress values', () => {
      const { rerender } = render(<InitializationProgress phase="auth" progress={NaN} />);
      expect(screen.getByText('0% complete')).toBeInTheDocument();
      
      rerender(<InitializationProgress phase="auth" progress={undefined as any} />);
      expect(screen.getByText('0% complete')).toBeInTheDocument();
      
      rerender(<InitializationProgress phase="auth" progress={null as any} />);
      expect(screen.getByText('0% complete')).toBeInTheDocument();
      
      rerender(<InitializationProgress phase="auth" progress={'not a number' as any} />);
      expect(screen.getByText('0% complete')).toBeInTheDocument();
    });
  });

  describe('Phase Indicators', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('shows auth phase as active when in auth phase', () => {
      render(<InitializationProgress phase="auth" progress={20} />);
      
      const authIndicator = screen.getByText('Auth').parentElement;
      expect(authIndicator?.querySelector('.animate-pulse')).toBeInTheDocument();
      expect(authIndicator?.querySelector('.bg-blue-500')).toBeInTheDocument();
    });

    it('shows websocket phase as active when in websocket phase', () => {
      render(<InitializationProgress phase="websocket" progress={50} />);
      
      const connectIndicator = screen.getByText('Connect').parentElement;
      expect(connectIndicator?.querySelector('.animate-pulse')).toBeInTheDocument();
      expect(connectIndicator?.querySelector('.bg-blue-500')).toBeInTheDocument();
    });

    it('shows store phase as active when in store phase', () => {
      render(<InitializationProgress phase="store" progress={80} />);
      
      const loadIndicator = screen.getByText('Load').parentElement;
      expect(loadIndicator?.querySelector('.animate-pulse')).toBeInTheDocument();
      expect(loadIndicator?.querySelector('.bg-blue-500')).toBeInTheDocument();
    });

    it('shows completed indicators based on progress', () => {
      // Progress > 33: Auth completed
      const { rerender } = render(<InitializationProgress phase="websocket" progress={40} />);
      let authIndicator = screen.getByText('Auth').parentElement;
      expect(authIndicator?.querySelector('.bg-green-500')).toBeInTheDocument();
      
      // Progress > 66: Auth and Connect completed
      rerender(<InitializationProgress phase="store" progress={75} />);
      authIndicator = screen.getByText('Auth').parentElement;
      const connectIndicator = screen.getByText('Connect').parentElement;
      expect(authIndicator?.querySelector('.bg-green-500')).toBeInTheDocument();
      expect(connectIndicator?.querySelector('.bg-green-500')).toBeInTheDocument();
      
      // Progress = 100: All completed
      rerender(<InitializationProgress phase="ready" progress={100} />);
      const loadIndicator = screen.getByText('Load').parentElement;
      expect(loadIndicator?.querySelector('.bg-green-500')).toBeInTheDocument();
    });
  });

  describe('Connection Status', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('shows connection status during websocket phase', () => {
      render(
        <InitializationProgress 
          phase="websocket" 
          progress={50} 
          connectionStatus="CONNECTING"
        />
      );
      
      expect(screen.getByText('Status: CONNECTING')).toBeInTheDocument();
    });

    it('does not show connection status in other phases', () => {
      const { rerender } = render(
        <InitializationProgress 
          phase="auth" 
          progress={20} 
          connectionStatus="CONNECTING"
        />
      );
      expect(screen.queryByText('Status: CONNECTING')).not.toBeInTheDocument();
      
      rerender(
        <InitializationProgress 
          phase="store" 
          progress={80} 
          connectionStatus="OPEN"
        />
      );
      expect(screen.queryByText('Status: OPEN')).not.toBeInTheDocument();
    });

    it('handles all connection status values', () => {
      const { rerender } = render(
        <InitializationProgress 
          phase="websocket" 
          progress={50} 
          connectionStatus="CLOSED"
        />
      );
      expect(screen.getByText('Status: CLOSED')).toBeInTheDocument();
      
      rerender(
        <InitializationProgress 
          phase="websocket" 
          progress={50} 
          connectionStatus="CONNECTING"
        />
      );
      expect(screen.getByText('Status: CONNECTING')).toBeInTheDocument();
      
      rerender(
        <InitializationProgress 
          phase="websocket" 
          progress={50} 
          connectionStatus="OPEN"
        />
      );
      expect(screen.getByText('Status: OPEN')).toBeInTheDocument();
    });
  });

  describe('Error Display', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('shows error alert when in error phase with error message', () => {
      render(
        <InitializationProgress 
          phase="error" 
          progress={0} 
          error="Failed to connect to server"
        />
      );
      
      const alert = screen.getByTestId('alert');
      expect(alert).toHaveAttribute('data-variant', 'destructive');
      expect(screen.getByText('Failed to connect to server')).toBeInTheDocument();
    });

    it('does not show error alert when not in error phase', () => {
      render(
        <InitializationProgress 
          phase="auth" 
          progress={20} 
          error="Some error"
        />
      );
      
      expect(screen.queryByTestId('alert')).not.toBeInTheDocument();
    });

    it('does not show error alert in error phase without error message', () => {
      render(
        <InitializationProgress 
          phase="error" 
          progress={0}
        />
      );
      
      expect(screen.queryByTestId('alert')).not.toBeInTheDocument();
    });
  });

  describe('Branding and Layout', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('displays Netra Apex branding', () => {
      render(<InitializationProgress phase="auth" progress={20} />);
      
      expect(screen.getByText('Netra Apex')).toBeInTheDocument();
      expect(screen.getByText('AI Optimization Platform')).toBeInTheDocument();
    });

    it('applies correct styling classes', () => {
      const { container } = render(<InitializationProgress phase="auth" progress={20} />);
      
      // Check for gradient background
      expect(container.querySelector('.bg-gradient-to-br')).toBeInTheDocument();
      expect(container.querySelector('.from-gray-50')).toBeInTheDocument();
      expect(container.querySelector('.via-white')).toBeInTheDocument();
      expect(container.querySelector('.to-gray-50')).toBeInTheDocument();
      
      // Check for card styling
      expect(container.querySelector('.rounded-lg')).toBeInTheDocument();
      expect(container.querySelector('.bg-white')).toBeInTheDocument();
      expect(container.querySelector('.shadow-lg')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('handles missing optional props gracefully', () => {
      render(<InitializationProgress phase="auth" progress={50} />);
      
      // Should not show connection status or error
      expect(screen.queryByText(/Status:/)).not.toBeInTheDocument();
      expect(screen.queryByTestId('alert')).not.toBeInTheDocument();
    });

    it('handles very long error messages', () => {
      const longError = 'A'.repeat(500);
      render(
        <InitializationProgress 
          phase="error" 
          progress={0} 
          error={longError}
        />
      );
      
      const alertDescription = screen.getByTestId('alert-description');
      expect(alertDescription.textContent).toHaveLength(500);
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});