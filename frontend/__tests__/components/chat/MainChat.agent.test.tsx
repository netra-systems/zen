import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { mockStore, setupMocks, cleanupMocks } from './MainChat.fixtures';

describe('MainChat - Agent Status Tests', () => {
  beforeEach(() => {
    setupMocks();
  });

  afterEach(() => {
    cleanupMocks();
  });

  describe('Agent status updates', () => {
    it('should show response card when processing', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123'
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should hide response card when not processing and no run', () => {
      render(<MainChat />);
      
      expect(screen.queryByTestId('response-card')).not.toBeInTheDocument();
    });

    it('should display fast layer data', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123',
        fastLayerData: {
          initialAnalysis: 'Quick analysis',
          suggestions: ['Suggestion 1', 'Suggestion 2']
        }
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should display medium layer data', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123',
        mediumLayerData: {
          deeperAnalysis: 'Detailed analysis',
          recommendations: ['Rec 1', 'Rec 2']
        }
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should display slow layer data with final report', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: false,
        currentRunId: 'run-123',
        slowLayerData: {
          finalReport: 'Complete analysis report',
          metrics: { accuracy: 0.95 }
        }
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should auto-collapse card after completion', async () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: false,
        currentRunId: 'run-123',
        slowLayerData: {
          finalReport: 'Complete'
        }
      });
      
      render(<MainChat />);
      
      const card = screen.getByTestId('response-card');
      expect(card).toHaveAttribute('data-collapsed', 'false');
      
      // Fast-forward timer
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      await waitFor(() => {
        expect(card).toHaveAttribute('data-collapsed', 'true');
      });
    });

    it('should reset collapse state when new processing starts', () => {
      const { rerender } = render(<MainChat />);
      
      // Start with completed state
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: false,
        currentRunId: 'run-123',
        slowLayerData: { finalReport: 'Done' }
      });
      
      rerender(<MainChat />);
      
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      // Start new processing
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-124',
        slowLayerData: null
      });
      
      rerender(<MainChat />);
      
      const card = screen.getByTestId('response-card');
      expect(card).toHaveAttribute('data-collapsed', 'false');
    });

    it('should handle toggle collapse manually', async () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123'
      });
      
      render(<MainChat />);
      
      const card = screen.getByTestId('response-card');
      const toggleButton = within(card).getByText('Toggle');
      
      expect(card).toHaveAttribute('data-collapsed', 'false');
      
      await userEvent.click(toggleButton);
      
      await waitFor(() => {
        expect(card).toHaveAttribute('data-collapsed', 'true');
      });
      
      await userEvent.click(toggleButton);
      
      await waitFor(() => {
        expect(card).toHaveAttribute('data-collapsed', 'false');
      });
    });
  });
});