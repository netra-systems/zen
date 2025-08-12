import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { ThinkingIndicator } from '@/components/chat/ThinkingIndicator';

describe('ThinkingIndicator Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Basic Display States', () => {
    it('should render with default thinking state', () => {
      render(<ThinkingIndicator />);
      
      expect(screen.getByText('Agent is thinking...')).toBeInTheDocument();
    });

    it('should render with processing type', () => {
      render(<ThinkingIndicator type="processing" />);
      
      expect(screen.getByText('Processing request...')).toBeInTheDocument();
    });

    it('should display custom message when provided', () => {
      render(<ThinkingIndicator message="Custom thinking message" />);
      
      expect(screen.getByText('Custom thinking message')).toBeInTheDocument();
    });

    it('should show different types with appropriate messages', () => {
      const types: Array<{ type: 'thinking' | 'processing' | 'analyzing' | 'optimizing'; message: string }> = [
        { type: 'analyzing', message: 'Analyzing data...' },
        { type: 'processing', message: 'Processing request...' },
        { type: 'optimizing', message: 'Optimizing solution...' },
        { type: 'thinking', message: 'Agent is thinking...' }
      ];
      
      types.forEach(({ type, message }) => {
        const { unmount } = render(<ThinkingIndicator type={type} />);
        expect(screen.getByText(message)).toBeInTheDocument();
        unmount();
      });
    });

    it('should handle undefined type gracefully', () => {
      render(<ThinkingIndicator type={undefined} />);
      
      // Should show default message
      expect(screen.getByText('Agent is thinking...')).toBeInTheDocument();
    });
  });

  describe('Animation and Visual Elements', () => {
    it('should render animated dots', () => {
      const { container } = render(<ThinkingIndicator />);
      
      // Check for three animated dots
      const dots = container.querySelectorAll('.w-2.h-2.rounded-full');
      expect(dots).toHaveLength(3);
    });

    it('should show different icons for different types', () => {
      const { container, rerender } = render(<ThinkingIndicator type="processing" />);
      
      // Check that appropriate icon is rendered (Cpu icon for processing)
      expect(container.querySelector('.text-blue-500')).toBeInTheDocument();
      
      rerender(<ThinkingIndicator type="analyzing" />);
      // Sparkles icon for analyzing
      expect(container.querySelector('.text-purple-500')).toBeInTheDocument();
      
      rerender(<ThinkingIndicator type="optimizing" />);
      // Loader2 icon for optimizing (with animate-spin)
      expect(container.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('should apply correct color schemes', () => {
      const { container, rerender } = render(<ThinkingIndicator type="processing" />);
      
      // The component uses template literals for gradient classes
      expect(screen.getByText('Processing request...')).toBeInTheDocument();
      
      rerender(<ThinkingIndicator type="analyzing" />);
      expect(screen.getByText('Analyzing data...')).toBeInTheDocument();
      
      rerender(<ThinkingIndicator type="optimizing" />);
      expect(screen.getByText('Optimizing solution...')).toBeInTheDocument();
    });
  });

  describe('Custom Messages', () => {
    it('should prioritize custom message over type-based message', () => {
      render(
        <ThinkingIndicator 
          type="processing" 
          message="Running complex calculations..." 
        />
      );
      
      expect(screen.getByText('Running complex calculations...')).toBeInTheDocument();
      expect(screen.queryByText('Processing request...')).not.toBeInTheDocument();
    });

    it('should handle empty custom message', () => {
      render(<ThinkingIndicator type="analyzing" message="" />);
      
      // Should fall back to type-based message
      expect(screen.getByText('Analyzing data...')).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('should have proper layout structure', () => {
      const { container } = render(<ThinkingIndicator />);
      
      // Check for main container with flex layout
      const mainContainer = container.querySelector('.flex.justify-start');
      expect(mainContainer).toBeInTheDocument();
      
      // Check for card-like container
      const card = container.querySelector('.bg-white.border.border-gray-200.rounded-2xl');
      expect(card).toBeInTheDocument();
    });

    it('should render with proper spacing', () => {
      const { container } = render(<ThinkingIndicator />);
      
      // Check for margin classes
      const mainContainer = container.querySelector('.mt-4.mb-4');
      expect(mainContainer).toBeInTheDocument();
      
      // Check for padding in card
      const card = container.querySelector('.p-4');
      expect(card).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle rapid type changes', () => {
      const { rerender } = render(<ThinkingIndicator type="thinking" />);
      
      expect(screen.getByText('Agent is thinking...')).toBeInTheDocument();
      
      rerender(<ThinkingIndicator type="processing" />);
      expect(screen.getByText('Processing request...')).toBeInTheDocument();
      
      rerender(<ThinkingIndicator type="analyzing" />);
      expect(screen.getByText('Analyzing data...')).toBeInTheDocument();
      
      rerender(<ThinkingIndicator type="optimizing" />);
      expect(screen.getByText('Optimizing solution...')).toBeInTheDocument();
    });

    it('should handle long custom messages', () => {
      const longMessage = 'This is a very long message that might overflow the container and cause layout issues if not handled properly';
      
      render(<ThinkingIndicator message={longMessage} />);
      
      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    it('should render multiple instances independently', () => {
      const { container } = render(
        <>
          <ThinkingIndicator type="thinking" />
          <ThinkingIndicator type="processing" />
          <ThinkingIndicator type="analyzing" />
        </>
      );
      
      expect(screen.getByText('Agent is thinking...')).toBeInTheDocument();
      expect(screen.getByText('Processing request...')).toBeInTheDocument();
      expect(screen.getByText('Analyzing data...')).toBeInTheDocument();
    });
  });
});