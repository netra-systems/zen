import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { ThinkingIndicator } from '@/components/chat/ThinkingIndicator';
import { useUnifiedChatStore } from '@/store/unified-chat';

// Mock dependencies
jest.mock('@/store/unified-chat');

describe('ThinkingIndicator Component', () => {
  const mockChatStore = {
    isProcessing: false,
    thinkingState: 'idle',
    processingSteps: [],
    currentStep: null,
    agentStatus: {}
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockChatStore);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Basic Display States', () => {
    it('should not render when not processing', () => {
      render(<ThinkingIndicator />);
      
      expect(screen.queryByTestId('thinking-indicator')).not.toBeInTheDocument();
    });

    it('should render when processing begins', () => {
      const processingStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(processingStore);
      
      render(<ThinkingIndicator />);
      
      expect(screen.getByTestId('thinking-indicator')).toBeInTheDocument();
      expect(screen.getByTestId('thinking-animation')).toBeInTheDocument();
    });

    it('should display basic thinking message', () => {
      const thinkingStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(thinkingStore);
      
      render(<ThinkingIndicator />);
      
      expect(screen.getByText(/ai is thinking/i)).toBeInTheDocument();
    });

    it('should show different states with appropriate messages', () => {
      const states = [
        { state: 'analyzing', message: /analyzing/i },
        { state: 'processing', message: /processing/i },
        { state: 'generating', message: /generating/i },
        { state: 'optimizing', message: /optimizing/i }
      ];
      
      states.forEach(({ state, message }) => {
        const stateStore = {
          ...mockChatStore,
          isProcessing: true,
          thinkingState: state
        };
        
        (useUnifiedChatStore as jest.Mock).mockReturnValue(stateStore);
        
        const { rerender } = render(<ThinkingIndicator />);
        
        expect(screen.getByText(message)).toBeInTheDocument();
        
        rerender(<div />); // Clean up
      });
    });

    it('should handle unknown thinking states gracefully', () => {
      const unknownStateStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'unknown_state'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(unknownStateStore);
      
      render(<ThinkingIndicator />);
      
      // Should fall back to generic thinking message
      expect(screen.getByText(/processing/i)).toBeInTheDocument();
    });
  });

  describe('Animation and Timing', () => {
    it('should animate dots in thinking indicator', async () => {
      const animatingStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(animatingStore);
      
      render(<ThinkingIndicator />);
      
      const dotsElement = screen.getByTestId('thinking-dots');
      
      // Initial state
      expect(dotsElement).toHaveTextContent('');
      
      // After 500ms - should show 1 dot
      act(() => {
        jest.advanceTimersByTime(500);
      });
      
      await waitFor(() => {
        expect(dotsElement).toHaveTextContent('.');
      });
      
      // After 1000ms - should show 2 dots
      act(() => {
        jest.advanceTimersByTime(500);
      });
      
      await waitFor(() => {
        expect(dotsElement).toHaveTextContent('..');
      });
      
      // After 1500ms - should show 3 dots
      act(() => {
        jest.advanceTimersByTime(500);
      });
      
      await waitFor(() => {
        expect(dotsElement).toHaveTextContent('...');
      });
      
      // After 2000ms - should reset to no dots
      act(() => {
        jest.advanceTimersByTime(500);
      });
      
      await waitFor(() => {
        expect(dotsElement).toHaveTextContent('');
      });
    });

    it('should have pulsing animation on indicator container', () => {
      const pulsatingStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(pulsatingStore);
      
      render(<ThinkingIndicator />);
      
      const indicator = screen.getByTestId('thinking-indicator');
      expect(indicator).toHaveClass('animate-pulse');
    });

    it('should show loading spinner for longer operations', async () => {
      const longProcessStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'processing',
        processingDuration: 5000 // 5 seconds
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(longProcessStore);
      
      render(<ThinkingIndicator />);
      
      // Should show spinner after threshold
      act(() => {
        jest.advanceTimersByTime(3000);
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
      });
    });

    it('should vary animation speed based on processing intensity', () => {
      const intensiveStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'analyzing',
        processingIntensity: 'high'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(intensiveStore);
      
      render(<ThinkingIndicator />);
      
      const indicator = screen.getByTestId('thinking-indicator');
      expect(indicator).toHaveClass('animate-pulse-fast');
    });

    it('should pause animation when window loses focus', () => {
      const pausableStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(pausableStore);
      
      render(<ThinkingIndicator />);
      
      const indicator = screen.getByTestId('thinking-indicator');
      
      // Simulate window blur
      window.dispatchEvent(new Event('blur'));
      
      expect(indicator).toHaveClass('animation-paused');
      
      // Simulate window focus
      window.dispatchEvent(new Event('focus'));
      
      expect(indicator).not.toHaveClass('animation-paused');
    });

    it('should cleanup animation timers on unmount', () => {
      const { unmount } = render(<ThinkingIndicator />);
      
      const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
      
      unmount();
      
      expect(clearIntervalSpy).toHaveBeenCalled();
      expect(clearTimeoutSpy).toHaveBeenCalled();
    });
  });

  describe('Processing Steps Display', () => {
    it('should display current processing step', () => {
      const stepStore = {
        ...mockChatStore,
        isProcessing: true,
        currentStep: {
          id: 'step-1',
          title: 'Analyzing user input',
          description: 'Understanding the request context',
          progress: 0.3
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(stepStore);
      
      render(<ThinkingIndicator />);
      
      expect(screen.getByText('Analyzing user input')).toBeInTheDocument();
      expect(screen.getByText('Understanding the request context')).toBeInTheDocument();
    });

    it('should show progress bar for current step', () => {
      const progressStore = {
        ...mockChatStore,
        isProcessing: true,
        currentStep: {
          id: 'step-progress',
          title: 'Processing data',
          progress: 0.65
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(progressStore);
      
      render(<ThinkingIndicator />);
      
      const progressBar = screen.getByTestId('step-progress-bar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '65');
      expect(progressBar).toHaveStyle('width: 65%');
    });

    it('should display list of completed steps', () => {
      const completedStepsStore = {
        ...mockChatStore,
        isProcessing: true,
        processingSteps: [
          { id: 'step-1', title: 'Input validation', status: 'completed' },
          { id: 'step-2', title: 'Context analysis', status: 'completed' },
          { id: 'step-3', title: 'Response generation', status: 'in_progress' }
        ],
        currentStep: { id: 'step-3', title: 'Response generation', status: 'in_progress' }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(completedStepsStore);
      
      render(<ThinkingIndicator />);
      
      expect(screen.getByTestId('completed-steps')).toBeInTheDocument();
      expect(screen.getByText('Input validation')).toBeInTheDocument();
      expect(screen.getByText('Context analysis')).toBeInTheDocument();
      
      // Completed steps should have checkmark
      const completedIcons = screen.getAllByTestId('step-completed-icon');
      expect(completedIcons).toHaveLength(2);
    });

    it('should show step transitions smoothly', async () => {
      const { rerender } = render(<ThinkingIndicator />);
      
      // Start with first step
      const step1Store = {
        ...mockChatStore,
        isProcessing: true,
        currentStep: { id: 'step-1', title: 'Step 1' }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(step1Store);
      rerender(<ThinkingIndicator />);
      
      expect(screen.getByText('Step 1')).toBeInTheDocument();
      
      // Transition to second step
      const step2Store = {
        ...mockChatStore,
        isProcessing: true,
        currentStep: { id: 'step-2', title: 'Step 2' },
        processingSteps: [
          { id: 'step-1', title: 'Step 1', status: 'completed' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(step2Store);
      rerender(<ThinkingIndicator />);
      
      // Should show smooth transition
      expect(screen.getByTestId('step-transition')).toHaveClass('fade-in');
      await waitFor(() => {
        expect(screen.getByText('Step 2')).toBeInTheDocument();
      });
    });

    it('should estimate time remaining for steps', () => {
      const timedStore = {
        ...mockChatStore,
        isProcessing: true,
        currentStep: {
          id: 'step-timed',
          title: 'Complex processing',
          estimatedDuration: 30000, // 30 seconds
          startTime: Date.now() - 10000 // Started 10 seconds ago
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(timedStore);
      
      render(<ThinkingIndicator />);
      
      expect(screen.getByTestId('time-remaining')).toHaveTextContent('~20s remaining');
    });

    it('should handle step errors and retries', () => {
      const errorStore = {
        ...mockChatStore,
        isProcessing: true,
        currentStep: {
          id: 'step-error',
          title: 'Failed step',
          status: 'error',
          error: 'Processing failed',
          retryCount: 1,
          maxRetries: 3
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(errorStore);
      
      render(<ThinkingIndicator />);
      
      expect(screen.getByTestId('step-error')).toBeInTheDocument();
      expect(screen.getByText('Processing failed')).toBeInTheDocument();
      expect(screen.getByText('Retry 1/3')).toBeInTheDocument();
    });
  });

  describe('Agent Status Integration', () => {
    it('should show which agent is currently thinking', () => {
      const agentStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking',
        currentAgent: {
          name: 'optimizations_core',
          displayName: 'Optimization Agent',
          status: 'active'
        }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(agentStore);
      
      render(<ThinkingIndicator />);
      
      expect(screen.getByText(/optimization agent/i)).toBeInTheDocument();
      expect(screen.getByTestId('agent-avatar')).toBeInTheDocument();
    });

    it('should display agent-specific thinking messages', () => {
      const agentMessages = [
        { agent: 'triage', message: 'Analyzing your request...' },
        { agent: 'data', message: 'Processing data patterns...' },
        { agent: 'optimizations_core', message: 'Finding optimization opportunities...' },
        { agent: 'reporting', message: 'Generating comprehensive report...' }
      ];
      
      agentMessages.forEach(({ agent, message }) => {
        const agentStore = {
          ...mockChatStore,
          isProcessing: true,
          currentAgent: { name: agent },
          thinkingState: 'thinking'
        };
        
        (useUnifiedChatStore as jest.Mock).mockReturnValue(agentStore);
        
        const { rerender } = render(<ThinkingIndicator />);
        
        expect(screen.getByText(message)).toBeInTheDocument();
        
        rerender(<div />); // Clean up
      });
    });

    it('should show multiple agents when orchestrating', () => {
      const orchestrationStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'orchestrating',
        activeAgents: [
          { name: 'supervisor', status: 'coordinating' },
          { name: 'data', status: 'analyzing' },
          { name: 'optimizations_core', status: 'processing' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(orchestrationStore);
      
      render(<ThinkingIndicator />);
      
      expect(screen.getByTestId('multi-agent-indicator')).toBeInTheDocument();
      expect(screen.getByText(/coordinating multiple agents/i)).toBeInTheDocument();
      
      const agentIcons = screen.getAllByTestId('agent-icon');
      expect(agentIcons).toHaveLength(3);
    });

    it('should animate agent handoffs', async () => {
      const { rerender } = render(<ThinkingIndicator />);
      
      // Start with triage agent
      const triageStore = {
        ...mockChatStore,
        isProcessing: true,
        currentAgent: { name: 'triage', displayName: 'Triage Agent' }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(triageStore);
      rerender(<ThinkingIndicator />);
      
      expect(screen.getByText('Triage Agent')).toBeInTheDocument();
      
      // Hand off to data agent
      const dataStore = {
        ...mockChatStore,
        isProcessing: true,
        currentAgent: { name: 'data', displayName: 'Data Agent' },
        handoffAnimation: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(dataStore);
      rerender(<ThinkingIndicator />);
      
      expect(screen.getByTestId('agent-handoff-animation')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(screen.getByText('Data Agent')).toBeInTheDocument();
      });
    });
  });

  describe('Customization and Theming', () => {
    it('should support different visual themes', () => {
      const themedStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking',
        theme: 'dark'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(themedStore);
      
      render(<ThinkingIndicator />);
      
      const indicator = screen.getByTestId('thinking-indicator');
      expect(indicator).toHaveClass('theme-dark');
    });

    it('should allow custom thinking messages', () => {
      const customMessageStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'custom',
        customMessage: 'Performing advanced analysis...'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(customMessageStore);
      
      render(<ThinkingIndicator />);
      
      expect(screen.getByText('Performing advanced analysis...')).toBeInTheDocument();
    });

    it('should support minimal mode for compact display', () => {
      const minimalStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(minimalStore);
      
      render(<ThinkingIndicator minimal={true} />);
      
      const indicator = screen.getByTestId('thinking-indicator');
      expect(indicator).toHaveClass('minimal-mode');
      
      // Should not show detailed messages in minimal mode
      expect(screen.queryByTestId('detailed-status')).not.toBeInTheDocument();
    });

    it('should adapt size based on available space', () => {
      const adaptiveStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(adaptiveStore);
      
      // Mock container size
      Object.defineProperty(HTMLElement.prototype, 'getBoundingClientRect', {
        configurable: true,
        value: jest.fn(() => ({ width: 300, height: 100 }))
      });
      
      render(<ThinkingIndicator />);
      
      const indicator = screen.getByTestId('thinking-indicator');
      expect(indicator).toHaveClass('size-compact');
    });
  });

  describe('Performance and Accessibility', () => {
    it('should optimize animation performance', () => {
      const performantStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(performantStore);
      
      render(<ThinkingIndicator />);
      
      const animatedElement = screen.getByTestId('thinking-animation');
      
      // Should use CSS transforms for better performance
      expect(animatedElement).toHaveStyle('will-change: transform');
      expect(animatedElement).toHaveClass('gpu-accelerated');
    });

    it('should respect reduced motion preferences', () => {
      // Mock prefers-reduced-motion
      const matchMediaSpy = jest.spyOn(window, 'matchMedia').mockReturnValue({
        matches: true,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      } as any);
      
      const reducedMotionStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(reducedMotionStore);
      
      render(<ThinkingIndicator />);
      
      const indicator = screen.getByTestId('thinking-indicator');
      expect(indicator).toHaveClass('reduced-motion');
      
      // Should not have complex animations
      expect(indicator).not.toHaveClass('animate-pulse');
      
      matchMediaSpy.mockRestore();
    });

    it('should provide proper ARIA labels and live regions', () => {
      const accessibleStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'analyzing',
        currentStep: { title: 'Analyzing data patterns' }
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(accessibleStore);
      
      render(<ThinkingIndicator />);
      
      const indicator = screen.getByTestId('thinking-indicator');
      expect(indicator).toHaveAttribute('role', 'status');
      expect(indicator).toHaveAttribute('aria-live', 'polite');
      expect(indicator).toHaveAttribute('aria-label', 'AI is analyzing data patterns');
      
      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toBeInTheDocument();
    });

    it('should announce status changes to screen readers', async () => {
      const { rerender } = render(<ThinkingIndicator />);
      
      const announceStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(announceStore);
      rerender(<ThinkingIndicator />);
      
      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toHaveTextContent(/ai is thinking/i);
      
      // Change to different state
      const analyzingStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'analyzing'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(analyzingStore);
      rerender(<ThinkingIndicator />);
      
      await waitFor(() => {
        expect(liveRegion).toHaveTextContent(/analyzing/i);
      });
    });

    it('should handle high frequency updates without performance issues', async () => {
      const { rerender } = render(<ThinkingIndicator />);
      
      // Rapidly change states 100 times
      for (let i = 0; i < 100; i++) {
        const rapidStore = {
          ...mockChatStore,
          isProcessing: true,
          thinkingState: 'thinking',
          currentStep: { title: `Step ${i}`, progress: i / 100 }
        };
        
        (useUnifiedChatStore as jest.Mock).mockReturnValue(rapidStore);
        rerender(<ThinkingIndicator />);
      }
      
      // Should still be responsive
      expect(screen.getByTestId('thinking-indicator')).toBeInTheDocument();
    });

    it('should debounce rapid state changes', async () => {
      const debouncedStore = {
        ...mockChatStore,
        isProcessing: true,
        thinkingState: 'thinking'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(debouncedStore);
      
      const { rerender } = render(<ThinkingIndicator />);
      
      // Fire multiple rapid updates
      for (let i = 0; i < 10; i++) {
        const rapidUpdate = {
          ...debouncedStore,
          currentStep: { title: `Rapid Step ${i}` }
        };
        
        (useUnifiedChatStore as jest.Mock).mockReturnValue(rapidUpdate);
        rerender(<ThinkingIndicator />);
      }
      
      // Should debounce and not update immediately
      act(() => {
        jest.advanceTimersByTime(100);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Rapid Step 9')).toBeInTheDocument();
      });
    });
  });
});