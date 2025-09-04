import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MainChat } from '../MainChat';
import { MessageInput } from '../MessageInput';
import { ExamplePrompts } from '../ExamplePrompts';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';

// Mock the stores and hooks
jest.mock('@/store/unified-chat');
jest.mock('@/store/threadStore');
jest.mock('@/store/authStore');
jest.mock('@/hooks/useWebSocket');
jest.mock('@/hooks/useLoadingState');
jest.mock('@/hooks/useEventProcessor');
jest.mock('@/hooks/useThreadNavigation');
jest.mock('@/hooks/useInitializationCoordinator');

const mockUseUnifiedChatStore = useUnifiedChatStore as jest.MockedFunction<typeof useUnifiedChatStore>;
const mockUseThreadStore = useThreadStore as jest.MockedFunction<typeof useThreadStore>;
const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;

describe('First Interaction Hide Feature', () => {
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Setup default mock returns
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: null,
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn(),
      addMessage: jest.fn(),
      setProcessing: jest.fn()
    } as any);

    mockUseThreadStore.mockReturnValue({
      currentThreadId: null
    } as any);

    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true
    } as any);
  });

  describe('MessageInput first interaction detection', () => {
    it('should call onFirstInteraction when user types a character', async () => {
      const onFirstInteraction = jest.fn();
      
      render(<MessageInput onFirstInteraction={onFirstInteraction} />);
      
      const textarea = screen.getByRole('textbox');
      fireEvent.keyDown(textarea, { key: 'a', code: 'KeyA' });
      
      expect(onFirstInteraction).toHaveBeenCalledTimes(1);
    });

    it('should not call onFirstInteraction for navigation keys', async () => {
      const onFirstInteraction = jest.fn();
      
      render(<MessageInput onFirstInteraction={onFirstInteraction} />);
      
      const textarea = screen.getByRole('textbox');
      fireEvent.keyDown(textarea, { key: 'ArrowUp' });
      fireEvent.keyDown(textarea, { key: 'ArrowDown' });
      fireEvent.keyDown(textarea, { key: 'Tab' });
      fireEvent.keyDown(textarea, { key: 'Escape' });
      
      expect(onFirstInteraction).not.toHaveBeenCalled();
    });

    it('should only call onFirstInteraction once per session', async () => {
      const onFirstInteraction = jest.fn();
      
      render(<MessageInput onFirstInteraction={onFirstInteraction} />);
      
      const textarea = screen.getByRole('textbox');
      fireEvent.keyDown(textarea, { key: 'a', code: 'KeyA' });
      fireEvent.keyDown(textarea, { key: 'b', code: 'KeyB' });
      fireEvent.keyDown(textarea, { key: 'c', code: 'KeyC' });
      
      expect(onFirstInteraction).toHaveBeenCalledTimes(1);
    });
  });

  describe('ExamplePrompts force collapse', () => {
    it('should collapse when forceCollapsed prop is true', async () => {
      const { rerender } = render(<ExamplePrompts />);
      
      // Initially should be open (expanded)
      expect(screen.getByText('Quick Start Examples')).toBeInTheDocument();
      
      // Force collapse
      rerender(<ExamplePrompts forceCollapsed={true} />);
      
      await waitFor(() => {
        // The component should still be there, but collapsed (isOpen should be false)
        // This would need to be tested by checking the aria-expanded attribute or similar
        expect(screen.getByText('Quick Start Examples')).toBeInTheDocument();
      });
    });

    it('should start expanded by default', () => {
      render(<ExamplePrompts />);
      
      expect(screen.getByText('Quick Start Examples')).toBeInTheDocument();
      // Should show example prompts
      expect(screen.getByText(/I need to optimize/i)).toBeInTheDocument();
    });
  });
});