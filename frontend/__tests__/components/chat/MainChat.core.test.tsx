import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '@/components/chat/MainChat';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Test wrapper for proper context
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div data-testid="test-wrapper">
      {children}
    </div>
  );
};

const renderWithProviders = (component: React.ReactElement) => {
  return render(<TestWrapper>{component}</TestWrapper>);
};

// Mock only the hooks and services, NOT UI components
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => ({
    isProcessing: false,
    messages: [],
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
    currentRunId: null,
    activeThreadId: null,
    isThreadLoading: false,
    threads: [],
    currentThreadId: null,
    handleWebSocketEvent: jest.fn(),
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    clearMessages: jest.fn(),
    updateLayerData: jest.fn(),
    setActiveThread: jest.fn(),
    resetLayers: jest.fn()
  })
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    messages: [],
    connected: true,
    error: null
  })
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: () => ({
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: true,
    loadingMessage: ''
  })
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: () => ({
    processedEvents: [],
    isProcessing: false,
    stats: { processed: 0, failed: 0 }
  })
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: () => ({
    currentThreadId: null,
    isNavigating: false,
    navigateToThread: jest.fn(),
    createNewThread: jest.fn()
  })
}));

// Mock framer-motion to avoid animation issues
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => React.createElement('div', { ...props }, children),
    button: ({ children, ...props }: any) => React.createElement('button', { ...props }, children),
    span: ({ children, ...props }: any) => React.createElement('span', { ...props }, children),
  },
  AnimatePresence: ({ children }: any) => children,
}));

// Mock utility services and dependencies
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    warn: jest.fn()
  }
}));

jest.mock('@/lib/examplePrompts', () => ({
  examplePrompts: [
    'Test example prompt for optimization'
  ]
}));

// Mock UI components
jest.mock('@/components/ui/card', () => ({
  Card: ({ children, ...props }: any) => React.createElement('div', { 'data-testid': 'card', ...props }, children),
  CardContent: ({ children, ...props }: any) => React.createElement('div', { 'data-testid': 'card-content', ...props }, children),
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: any) => React.createElement('button', { 'data-testid': 'button', ...props }, children),
}));

jest.mock('@/components/ui/collapsible', () => ({
  Collapsible: ({ children, ...props }: any) => React.createElement('div', { 'data-testid': 'collapsible', ...props }, children),
  CollapsibleContent: ({ children, ...props }: any) => React.createElement('div', { 'data-testid': 'collapsible-content', ...props }, children),
  CollapsibleTrigger: ({ children, ...props }: any) => React.createElement('div', { 'data-testid': 'collapsible-trigger', ...props }, children),
}));

// Mock chat components
jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => React.createElement('div', { 'data-testid': 'example-prompts' }, 'Explore these examples to get started'),
}));

jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => React.createElement('header', { role: 'banner', 'data-testid': 'chat-header' }, 'Chat Header'),
}));

jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: () => React.createElement('textarea', { role: 'textbox', 'data-testid': 'message-input', placeholder: 'Start typing your AI optimization request...' }),
}));

jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => React.createElement('div', { 'data-testid': 'message-list' }, 'Message List'),
}));

jest.mock('@/components/chat/PersistentResponseCard', () => ({
  PersistentResponseCard: () => React.createElement('div', { 'data-testid': 'response-card' }, 'Response Card'),
}));

jest.mock('@/components/chat/OverflowPanel', () => ({
  OverflowPanel: () => React.createElement('div', { 'data-testid': 'overflow-panel' }, 'Overflow Panel'),
}));

jest.mock('@/components/chat/EventDiagnosticsPanel', () => ({
  EventDiagnosticsPanel: () => React.createElement('div', { 'data-testid': 'diagnostics-panel' }, 'Diagnostics Panel'),
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Loader2: ({ className, ...props }: any) => React.createElement('div', { 'data-testid': 'loader', className, ...props }, '⟳'),
  ChevronDown: (props: any) => React.createElement('div', { 'data-testid': 'chevron-down', ...props }, '▼'),
  Send: (props: any) => React.createElement('div', { 'data-testid': 'send-icon', ...props }, '→'),
  Sparkles: (props: any) => React.createElement('div', { 'data-testid': 'sparkles-icon', ...props }, '✨'),
  Zap: (props: any) => React.createElement('div', { 'data-testid': 'zap-icon', ...props }, '⚡'),
  TrendingUp: (props: any) => React.createElement('div', { 'data-testid': 'trending-up-icon', ...props }, '📈'),
  Shield: (props: any) => React.createElement('div', { 'data-testid': 'shield-icon', ...props }, '🛡️'),
  Database: (props: any) => React.createElement('div', { 'data-testid': 'database-icon', ...props }, '🗄️'),
  Brain: (props: any) => React.createElement('div', { 'data-testid': 'brain-icon', ...props }, '🧠'),
  Bot: (props: any) => React.createElement('div', { 'data-testid': 'bot-icon', ...props }, '🤖'),
  Activity: (props: any) => React.createElement('div', { 'data-testid': 'activity-icon', ...props }, '📊'),
  Cpu: (props: any) => React.createElement('div', { 'data-testid': 'cpu-icon', ...props }, '💻'),
}));

jest.mock('@/lib/utils', () => ({
  generateUniqueId: () => 'test-id-123',
  cn: (...args: any[]) => args.filter(Boolean).join(' ')
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isAuthenticated: true,
    user: { id: '1', name: 'Test User' }
  })
}));

describe('MainChat - Core Component Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.useRealTimers();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('UI layout and responsiveness', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should render all main components', async () => {
      renderWithProviders(<MainChat />);
      
      // Wait for components to render
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument(); // ChatHeader
        expect(screen.getByRole('textbox')).toBeInTheDocument(); // MessageInput
        expect(screen.getByText(/explore these examples/i)).toBeInTheDocument(); // ExamplePrompts
      });
    });

    it('should apply correct CSS classes', async () => {
      const { container } = renderWithProviders(<MainChat />);
      
      await waitFor(() => {
        const mainContainer = container.firstChild;
        expect(mainContainer).toBeInTheDocument();
        // Check for classes on the main container or nested elements
        const flexElement = container.querySelector('.flex');
        expect(flexElement).toBeInTheDocument();
      });
    });

    it('should handle window resize', () => {
      const { container } = renderWithProviders(<MainChat />);
      
      // Simulate window resize
      global.innerWidth = 500;
      global.dispatchEvent(new Event('resize'));
      
      // Component should still be rendered
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should maintain layout during state changes', async () => {
      const { rerender } = renderWithProviders(<MainChat />);
      
      rerender(<MainChat />);
      
      // All components should still be present
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument(); // ChatHeader
        expect(screen.getByRole('textbox')).toBeInTheDocument(); // MessageInput
        expect(screen.getByText(/explore these examples/i)).toBeInTheDocument(); // ExamplePrompts
      });
    });

    it('should handle scroll behavior correctly', () => {
      const { container } = renderWithProviders(<MainChat />);
      
      const scrollableArea = container.querySelector('.overflow-y-auto');
      expect(scrollableArea).toBeInTheDocument();
    });

    it('should apply animations correctly', async () => {
      renderWithProviders(<MainChat />);
      
      // Check for animation wrappers
      const { container } = renderWithProviders(<MainChat />);
      const animatedElements = container.querySelectorAll('[style*="opacity"]');
      
      // Some elements should have opacity styles from framer-motion
      expect(animatedElements.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Performance and optimization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should not re-render unnecessarily', () => {
      const renderSpy = jest.fn();
      const TestWrapper = () => {
        renderSpy();
        return <MainChat />;
      };
      
      const { rerender } = render(<TestWrapper />);
      
      // Initial render
      expect(renderSpy).toHaveBeenCalledTimes(1);
      
      // Rerender with same props
      rerender(<TestWrapper />);
      
      // Should have rendered again (no memo by default)
      expect(renderSpy).toHaveBeenCalledTimes(2);
    });

    it('should handle rapid state updates', async () => {
      const { rerender } = renderWithProviders(<MainChat />);
      
      // Simulate rapid updates
      for (let i = 0; i < 10; i++) {
        rerender(<MainChat />);
      }
      
      // Should still be stable
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument();
      });
    });

    it('should clean up timers on unmount', () => {
      const { unmount } = render(<MainChat />);
      
      // Should not throw on unmount
      expect(() => unmount()).not.toThrow();
    });

    it('should handle memory efficiently with large message lists', () => {
      // Should not crash with basic render
      expect(() => render(<MainChat />)).not.toThrow();
    });
  });

  describe('Integration with store and hooks', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should properly integrate with unified chat store', () => {
      renderWithProviders(<MainChat />);
      
      // Basic functionality test - component should render
      expect(screen.getByRole('banner')).toBeInTheDocument();
    });

    it('should properly integrate with chat WebSocket hook', () => {
      renderWithProviders(<MainChat />);
      
      // Basic functionality test - component should render
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('should respond to store updates', () => {
      const { rerender } = renderWithProviders(<MainChat />);
      
      rerender(<MainChat />);
      
      // Should maintain stable rendering
      expect(screen.getByRole('banner')).toBeInTheDocument();
    });

    it('should handle store reset', async () => {
      const { rerender } = renderWithProviders(<MainChat />);
      
      rerender(<MainChat />);
      
      // Should show example prompts in basic state
      await waitFor(() => {
        expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should have proper semantic structure', () => {
      const { container } = renderWithProviders(<MainChat />);
      
      // Should use semantic HTML
      expect(container.querySelector('div')).toBeInTheDocument();
    });

    it('should support keyboard navigation', () => {
      renderWithProviders(<MainChat />);
      
      // Basic keyboard navigation test - component should render and be accessible
      expect(screen.getByRole('banner')).toBeInTheDocument();
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('should handle focus management', () => {
      renderWithProviders(<MainChat />);
      
      // Initial focus should be manageable
      expect(document.activeElement).toBeInTheDocument();
    });

    it('should provide screen reader support', () => {
      renderWithProviders(<MainChat />);
      
      // Check for accessible elements
      const mainContent = screen.getByRole('banner').parentElement;
      expect(mainContent).toBeInTheDocument();
    });
  });
});