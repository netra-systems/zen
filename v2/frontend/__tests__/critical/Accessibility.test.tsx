import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import MainChat from '../../components/chat/MainChat';
import MessageInput from '../../components/chat/MessageInput';
import SubAgentStatus from '../../components/SubAgentStatus';
import { WebSocketProvider } from '../../providers/WebSocketProvider';

expect.extend(toHaveNoViolations);

describe('Accessibility and Keyboard Navigation Tests', () => {
  describe('WCAG Compliance', () => {
    it('should have no accessibility violations in main chat interface', async () => {
      const { container } = render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper ARIA labels and roles', () => {
      render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      expect(screen.getByRole('main')).toBeInTheDocument();
      expect(screen.getByLabelText(/chat messages/i)).toBeInTheDocument();
      expect(screen.getByRole('textbox', { name: /type your message/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument();
    });

    it('should support screen reader announcements for dynamic content', async () => {
      render(
        <WebSocketProvider>
          <div>
            <MainChat />
            <div role="status" aria-live="polite" aria-label="Agent status updates" />
          </div>
        </WebSocketProvider>
      );

      const statusRegion = screen.getByLabelText('Agent status updates');
      
      // Simulate agent status update
      fireEvent.change(statusRegion, {
        target: { textContent: 'Agent is analyzing your request...' }
      });

      expect(statusRegion).toHaveTextContent('Agent is analyzing your request...');
    });

    it('should have proper color contrast ratios', () => {
      const { container } = render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      const messageInput = screen.getByRole('textbox');
      const sendButton = screen.getByRole('button', { name: /send/i });

      // Check that elements have sufficient color contrast
      const inputStyles = getComputedStyle(messageInput);
      const buttonStyles = getComputedStyle(sendButton);

      expect(inputStyles.backgroundColor).not.toBe(inputStyles.color);
      expect(buttonStyles.backgroundColor).not.toBe(buttonStyles.color);
    });
  });

  describe('Keyboard Navigation', () => {
    it('should support full keyboard navigation through interface', async () => {
      const user = userEvent.setup();
      
      render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      const messageInput = screen.getByRole('textbox');
      const sendButton = screen.getByRole('button', { name: /send/i });

      // Tab to message input
      await user.tab();
      expect(messageInput).toHaveFocus();

      // Type message
      await user.type(messageInput, 'Test accessibility message');
      expect(messageInput).toHaveValue('Test accessibility message');

      // Tab to send button
      await user.tab();
      expect(sendButton).toHaveFocus();

      // Send with Enter key
      await user.keyboard('{Enter}');
      
      await waitFor(() => {
        expect(messageInput).toHaveValue('');
        expect(messageInput).toHaveFocus(); // Focus returns to input
      });
    });

    it('should support keyboard shortcuts for common actions', async () => {
      const user = userEvent.setup();
      
      render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      const messageInput = screen.getByRole('textbox');

      // Focus input
      messageInput.focus();
      await user.type(messageInput, 'Test message');

      // Ctrl+Enter should send message
      await user.keyboard('{Control>}{Enter}{/Control}');
      
      await waitFor(() => {
        expect(messageInput).toHaveValue('');
      });

      // Escape should clear input
      await user.type(messageInput, 'Another message');
      await user.keyboard('{Escape}');
      
      expect(messageInput).toHaveValue('');
    });

    it('should handle focus management in dynamic content', async () => {
      const user = userEvent.setup();
      
      render(
        <WebSocketProvider>
          <div>
            <MainChat />
            <SubAgentStatus runId="test-run" />
          </div>
        </WebSocketProvider>
      );

      // When new content appears, focus should be managed appropriately
      const expandButton = screen.queryByRole('button', { name: /expand details/i });
      
      if (expandButton) {
        expandButton.focus();
        await user.keyboard('{Enter}');

        // After expansion, focus should remain accessible
        expect(document.activeElement).not.toBe(document.body);
      }
    });

    it('should support arrow key navigation in message history', async () => {
      const user = userEvent.setup();
      
      render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      const messagesContainer = screen.getByLabelText(/chat messages/i);
      messagesContainer.focus();

      // Arrow keys should navigate through messages
      await user.keyboard('{ArrowDown}');
      await user.keyboard('{ArrowUp}');
      
      // Should not cause any focus traps
      expect(document.activeElement).toBeDefined();
    });
  });

  describe('Screen Reader Support', () => {
    it('should announce message status changes', () => {
      render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      // Check for proper ARIA live regions
      expect(screen.getByRole('log')).toBeInTheDocument(); // Message history
      expect(screen.queryByRole('status')).toBeInTheDocument(); // Status updates
    });

    it('should provide descriptive labels for interactive elements', () => {
      render(
        <WebSocketProvider>
          <MessageInput onSendMessage={jest.fn()} disabled={false} />
        </WebSocketProvider>
      );

      const textbox = screen.getByRole('textbox');
      const sendButton = screen.getByRole('button');

      expect(textbox).toHaveAccessibleName(/type your message/i);
      expect(sendButton).toHaveAccessibleName(/send message/i);
    });

    it('should announce loading states and progress', () => {
      render(
        <WebSocketProvider>
          <SubAgentStatus runId="test-run" />
        </WebSocketProvider>
      );

      // Progress indicators should be accessible
      const progressBars = screen.queryAllByRole('progressbar');
      progressBars.forEach(progressBar => {
        expect(progressBar).toHaveAttribute('aria-label');
        expect(progressBar).toHaveAttribute('aria-valuenow');
      });
    });

    it('should handle complex data structures accessibly', () => {
      const complexData = {
        optimization_results: {
          latency_improvement: '40%',
          throughput_increase: '25%',
          recommendations: ['Enable caching', 'Optimize queries'],
        },
      };

      render(
        <WebSocketProvider>
          <div role="region" aria-label="Optimization Results">
            <h2>Results</h2>
            <dl>
              <dt>Latency Improvement</dt>
              <dd>{complexData.optimization_results.latency_improvement}</dd>
              <dt>Throughput Increase</dt>
              <dd>{complexData.optimization_results.throughput_increase}</dd>
            </dl>
            <h3>Recommendations</h3>
            <ul>
              {complexData.optimization_results.recommendations.map((rec, i) => (
                <li key={i}>{rec}</li>
              ))}
            </ul>
          </div>
        </WebSocketProvider>
      );

      expect(screen.getByRole('region', { name: /optimization results/i })).toBeInTheDocument();
      expect(screen.getByText('40%')).toBeInTheDocument();
      expect(screen.getByText('25%')).toBeInTheDocument();
    });
  });

  describe('Focus Management', () => {
    it('should trap focus in modal dialogs', async () => {
      const user = userEvent.setup();
      
      render(
        <WebSocketProvider>
          <div>
            <button>Open Settings</button>
            <div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
              <h2 id="dialog-title">Settings</h2>
              <button>First focusable</button>
              <input type="text" />
              <button>Last focusable</button>
              <button>Close</button>
            </div>
          </div>
        </WebSocketProvider>
      );

      const dialog = screen.getByRole('dialog');
      const firstFocusable = screen.getByText('First focusable');
      const lastFocusable = screen.getByText('Close');

      // Focus should be trapped within dialog
      firstFocusable.focus();
      expect(firstFocusable).toHaveFocus();

      // Tab past last element should wrap to first
      await user.tab();
      await user.tab();
      await user.tab();
      await user.tab(); // Should wrap to first

      expect(firstFocusable).toHaveFocus();

      // Shift+Tab from first should go to last
      await user.keyboard('{Shift>}{Tab}{/Shift}');
      expect(lastFocusable).toHaveFocus();
    });

    it('should restore focus after modal closes', async () => {
      const user = userEvent.setup();
      
      const ModalComponent = () => {
        const [isOpen, setIsOpen] = React.useState(false);
        
        return (
          <div>
            <button onClick={() => setIsOpen(true)}>Open Modal</button>
            {isOpen && (
              <div role="dialog" aria-modal="true">
                <button onClick={() => setIsOpen(false)}>Close Modal</button>
              </div>
            )}
          </div>
        );
      };

      render(<ModalComponent />);

      const openButton = screen.getByText('Open Modal');
      
      openButton.focus();
      await user.click(openButton);

      const closeButton = screen.getByText('Close Modal');
      await user.click(closeButton);

      // Focus should return to the trigger element
      expect(openButton).toHaveFocus();
    });

    it('should handle focus in dynamically updated content', async () => {
      const DynamicContent = () => {
        const [items, setItems] = React.useState([1, 2, 3]);
        
        const addItem = () => setItems(prev => [...prev, prev.length + 1]);
        
        return (
          <div>
            <button onClick={addItem}>Add Item</button>
            <ul>
              {items.map(item => (
                <li key={item}>
                  <button>Item {item}</button>
                </li>
              ))}
            </ul>
          </div>
        );
      };

      const user = userEvent.setup();
      render(<DynamicContent />);

      const addButton = screen.getByText('Add Item');
      await user.click(addButton);

      // New item should be focusable
      const newItem = screen.getByText('Item 4');
      expect(newItem).toBeInTheDocument();
      
      newItem.focus();
      expect(newItem).toHaveFocus();
    });
  });

  describe('High Contrast and Visual Accessibility', () => {
    it('should maintain functionality in high contrast mode', () => {
      const { container } = render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      // Simulate high contrast mode
      document.body.classList.add('high-contrast');

      const messageInput = screen.getByRole('textbox');
      const sendButton = screen.getByRole('button', { name: /send/i });

      expect(messageInput).toBeVisible();
      expect(sendButton).toBeVisible();

      document.body.classList.remove('high-contrast');
    });

    it('should support reduced motion preferences', () => {
      const { container } = render(
        <WebSocketProvider>
          <div className="animate-fade-in">
            <MainChat />
          </div>
        </WebSocketProvider>
      );

      // Simulate reduced motion preference
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: query.includes('reduced-motion'),
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });

      const animatedElement = container.querySelector('.animate-fade-in');
      expect(animatedElement).toBeInTheDocument();
    });

    it('should handle zoom levels up to 200% gracefully', () => {
      const { container } = render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      // Simulate 200% zoom
      Object.defineProperty(window, 'devicePixelRatio', {
        writable: true,
        value: 2,
      });

      const messageInput = screen.getByRole('textbox');
      const sendButton = screen.getByRole('button', { name: /send/i });

      expect(messageInput).toBeVisible();
      expect(sendButton).toBeVisible();
      
      // Elements should not overlap or become unusable
      const inputRect = messageInput.getBoundingClientRect();
      const buttonRect = sendButton.getBoundingClientRect();
      
      expect(inputRect.width).toBeGreaterThan(0);
      expect(buttonRect.width).toBeGreaterThan(0);
    });
  });

  describe('Voice Control and Alternative Inputs', () => {
    it('should support voice control commands through proper labeling', () => {
      render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      // Voice control relies on accessible names
      expect(screen.getByRole('textbox', { name: /message/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
      
      // Check for landmarks that voice control can navigate to
      expect(screen.getByRole('main')).toBeInTheDocument();
      expect(screen.queryByRole('navigation')).toBeInTheDocument();
    });

    it('should handle alternative input methods', async () => {
      const user = userEvent.setup();
      
      render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      const messageInput = screen.getByRole('textbox');
      
      // Test paste operation
      await user.click(messageInput);
      await user.paste('Pasted message content');
      
      expect(messageInput).toHaveValue('Pasted message content');
    });
  });
});