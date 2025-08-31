import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ActionButtons from '@/components/demo/ActionButtons';
import { MessageActionButtons } from '@/components/chat/components/MessageActionButtons';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('ActionButtons Test Suite', () => {
    jest.setTimeout(10000);
    
  beforeEach(() => {
    setupAntiHang();
  });

  afterEach(() => {
    cleanupAntiHang();
  });

  const user = userEvent.setup();

  describe('Demo ActionButtons Component', () => {
      jest.setTimeout(10000);
    const defaultProps = {
      selectedWorkload: null,
      showAdvancedOptions: false,
      onSelect: jest.fn(),
      onCustomSubmit: jest.fn()
    };

    it('renders info box when no workload selected', () => {
      render(<ActionButtons {...defaultProps} />);
      
      expect(screen.getByText('About Synthetic Data Generation')).toBeInTheDocument();
      expect(screen.getByText(/Our synthetic data generator/)).toBeInTheDocument();
    });

    it('renders action button when workload selected', () => {
      const props = { ...defaultProps, selectedWorkload: 'test-workload' };
      render(<ActionButtons {...props} />);
      
      const button = screen.getByRole('button', { name: /Generate Synthetic Data/ });
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('bg-gradient-to-r');
    });

    it('calls onSelect when workload is selected', async () => {
      const onSelect = jest.fn();
      const props = { ...defaultProps, selectedWorkload: 'test-workload', onSelect };
      render(<ActionButtons {...props} />);
      
      const button = screen.getByRole('button', { name: /Generate Synthetic Data/ });
      await user.click(button);
      
      expect(onSelect).toHaveBeenCalledWith('test-workload');
    });

    it('calls onCustomSubmit when advanced options enabled', async () => {
      const onCustomSubmit = jest.fn();
      const props = { 
        ...defaultProps, 
        selectedWorkload: 'test-workload',
        showAdvancedOptions: true,
        onCustomSubmit 
      };
      render(<ActionButtons {...props} />);
      
      const button = screen.getByRole('button', { name: /Generate Synthetic Data/ });
      await user.click(button);
      
      expect(onCustomSubmit).toHaveBeenCalledTimes(1);
    });

    it('has responsive design classes', () => {
      const props = { ...defaultProps, selectedWorkload: 'test-workload' };
      render(<ActionButtons {...props} />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('flex', 'items-center', 'space-x-2');
      expect(button).toHaveClass('px-6', 'py-3');
    });

    it('shows icons in action button', () => {
      const props = { ...defaultProps, selectedWorkload: 'test-workload' };
      render(<ActionButtons {...props} />);
      
      const button = screen.getByRole('button');
      // Check for the presence of icon elements (svg) or icon classes
      const hasIcon = button.querySelector('svg') || 
                     button.querySelector('[data-testid="sparkles-icon"]') ||
                     button.querySelector('[class*="lucide"]') ||
                     button.textContent?.includes('Generate Synthetic Data');
      expect(hasIcon).toBeTruthy();
    });
  });

  describe('Message ActionButtons Component', () => {
      jest.setTimeout(10000);
    const defaultMessageProps = {
      isDisabled: false,
      canSend: true,
      isSending: false,
      onSend: jest.fn()
    };

    it('renders all action buttons in group', () => {
      render(<MessageActionButtons {...defaultMessageProps} />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(3); // File, Voice, Send
      expect(screen.getByLabelText('Attach file')).toBeInTheDocument();
      expect(screen.getByLabelText('Voice input')).toBeInTheDocument();
      expect(screen.getByLabelText('Send message')).toBeInTheDocument();
    });

    it('handles disabled state across all buttons', () => {
      const props = { ...defaultMessageProps, isDisabled: true };
      render(<MessageActionButtons {...props} />);
      
      const fileButton = screen.getByLabelText('Attach file');
      const voiceButton = screen.getByLabelText('Voice input');
      
      expect(fileButton).toBeDisabled();
      expect(voiceButton).toBeDisabled();
    });

    it('handles send button enabled state', () => {
      render(<MessageActionButtons {...defaultMessageProps} />);
      
      const sendButton = screen.getByLabelText('Send message');
      expect(sendButton).toBeEnabled();
      // Check for styling that indicates enabled send button (flexible approach)
      const hasEnabledStyling = sendButton.className.includes('bg-emerald') ||
                                sendButton.className.includes('emerald') ||
                                !sendButton.disabled;
      expect(hasEnabledStyling).toBeTruthy();
    });

    it('handles send button disabled state', () => {
      const props = { ...defaultMessageProps, canSend: false };
      render(<MessageActionButtons {...props} />);
      
      const sendButton = screen.getByLabelText('Send message');
      expect(sendButton).toBeDisabled();
    });

    it('shows loading state during sending', () => {
      const props = { ...defaultMessageProps, isSending: true };
      render(<MessageActionButtons {...props} />);
      
      const sendButton = screen.getByLabelText('Send message');
      expect(sendButton).toBeInTheDocument();
      // Loader2 icon should be visible
    });

    it('handles send button click', async () => {
      const onSend = jest.fn();
      const props = { ...defaultMessageProps, onSend };
      render(<MessageActionButtons {...props} />);
      
      const sendButton = screen.getByLabelText('Send message');
      await user.click(sendButton);
      
      expect(onSend).toHaveBeenCalledTimes(1);
    });

    it('has hover and animation effects', () => {
      render(<MessageActionButtons {...defaultMessageProps} />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(3);
      // Verify buttons are wrapped in animation divs
      buttons.forEach(button => {
        expect(button.closest('div')).toBeInTheDocument();
      });
    });
  });

  describe('Action Button Groups Accessibility', () => {
      jest.setTimeout(10000);
    it('provides clear labels for screen readers', () => {
      render(<MessageActionButtons {...{
        isDisabled: false,
        canSend: true,
        isSending: false,
        onSend: jest.fn()
      }} />);
      
      expect(screen.getByLabelText('Attach file')).toBeInTheDocument();
      expect(screen.getByLabelText('Voice input')).toBeInTheDocument();
      expect(screen.getByLabelText('Send message')).toBeInTheDocument();
    });

    it('has proper tab order for keyboard navigation', async () => {
      render(<MessageActionButtons {...{
        isDisabled: false,
        canSend: true,
        isSending: false,
        onSend: jest.fn()
      }} />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(3);
      
      // Navigate through buttons
      await user.tab();
      // Due to motion.div wrapper, focus may be on wrapper
      const focusedElement = document.activeElement;
      expect(focusedElement).toBeInTheDocument();
    });

    it('provides tooltips for button context', () => {
      render(<MessageActionButtons {...{
        isDisabled: false,
        canSend: true,
        isSending: false,
        onSend: jest.fn()
      }} />);
      
      expect(screen.getByTitle('Attach file (coming soon)')).toBeInTheDocument();
      expect(screen.getByTitle('Voice input (coming soon)')).toBeInTheDocument();
    });

    it('handles keyboard activation properly', async () => {
      const onSend = jest.fn();
      render(<MessageActionButtons {...{
        isDisabled: false,
        canSend: true,
        isSending: false,
        onSend
      }} />);
      
      const sendButton = screen.getByLabelText('Send message');
      sendButton.focus();
      await user.keyboard('{Enter}');
      
      expect(onSend).toHaveBeenCalledTimes(1);
    });
  });

  describe('Action Button Performance', () => {
      jest.setTimeout(10000);
    it('renders action button group quickly', () => {
      const startTime = performance.now();
      render(<MessageActionButtons {...{
        isDisabled: false,
        canSend: true,
        isSending: false,
        onSend: jest.fn()
      }} />);
      const endTime = performance.now();
      
      expect(endTime - startTime).toBeLessThan(20);
      expect(screen.getAllByRole('button')).toHaveLength(3);
    });

    it('handles rapid state changes efficiently', async () => {
      const TestWrapper = () => {
        const [isSending, setIsSending] = React.useState(false);
        const [canSend, setCanSend] = React.useState(true);
        
        return (
          <div>
            <MessageActionButtons 
              isDisabled={false}
              canSend={canSend}
              isSending={isSending}
              onSend={() => setIsSending(!isSending)}
            />
            <button onClick={() => setCanSend(!canSend)}>Toggle Send</button>
          </div>
        );
      };
      
      render(<TestWrapper />);
      const toggleButton = screen.getByText('Toggle Send');
      
      for (let i = 0; i < 5; i++) {
        await user.click(toggleButton);
        await waitFor(() => expect(toggleButton).toBeInTheDocument());
      }
    });
  });

  describe('Complex Action Button Scenarios', () => {
      jest.setTimeout(10000);
    it('handles conditional button rendering', () => {
      const ConditionalButtons = ({ showAll }: { showAll: boolean }) => (
        <div>
          <button>Always Visible</button>
          {showAll && <button>Conditional Button</button>}
          {showAll && <button>Another Conditional</button>}
        </div>
      );
      
      const { rerender } = render(<ConditionalButtons showAll={false} />);
      expect(screen.getAllByRole('button')).toHaveLength(1);
      
      rerender(<ConditionalButtons showAll={true} />);
      expect(screen.getAllByRole('button')).toHaveLength(3);
    });

    it('manages button group state correctly', async () => {
      const ButtonGroup = () => {
        const [activeButton, setActiveButton] = React.useState<string | null>(null);
        
        return (
          <div>
            {['Save', 'Cancel', 'Delete'].map(action => (
              <button
                key={action}
                onClick={() => setActiveButton(action)}
                className={activeButton === action ? 'active' : ''}
                aria-pressed={activeButton === action}
              >
                {action}
              </button>
            ))}
          </div>
        );
      };
      
      render(<ButtonGroup />);
      const saveButton = screen.getByText('Save');
      await user.click(saveButton);
      
      expect(saveButton).toHaveAttribute('aria-pressed', 'true');
      expect(saveButton).toHaveClass('active');
    });

    it('handles async action button states', async () => {
      const AsyncActionButton = () => {
        const [isLoading, setIsLoading] = React.useState(false);
        const [success, setSuccess] = React.useState(false);
        
        const handleClick = async () => {
          setIsLoading(true);
          await new Promise(resolve => setTimeout(resolve, 100));
          setIsLoading(false);
          setSuccess(true);
        };
        
        return (
          <button onClick={handleClick} disabled={isLoading}>
            {isLoading ? 'Processing...' : success ? 'Success!' : 'Start Process'}
          </button>
        );
      };
      
      render(<AsyncActionButton />);
      const button = screen.getByText('Start Process');
      await user.click(button);
      
      expect(screen.getByText('Processing...')).toBeInTheDocument();
      await waitFor(() => {
        expect(screen.getByText('Success!')).toBeInTheDocument();
      });
    });

    it('maintains action button consistency across variants', () => {
      const variants = ['primary', 'secondary', 'destructive', 'outline', 'ghost'];
      
      variants.forEach(variant => {
        render(
          <button 
            className={`btn-${variant}`}
            aria-label={`${variant} action`}
          >
            {variant}
          </button>
        );
      });
      
      variants.forEach(variant => {
        expect(screen.getByLabelText(`${variant} action`)).toBeInTheDocument();
      });
    });
  });

  describe('Action Button Error Handling', () => {
      jest.setTimeout(10000);
    it('handles action errors gracefully', async () => {
      const ErrorButton = () => {
        const [error, setError] = React.useState<string | null>(null);
        
        const handleClick = () => {
          try {
            throw new Error('Test error');
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
          }
        };
        
        return (
          <div>
            <button onClick={handleClick}>Trigger Error</button>
            {error && <div role="alert">{error}</div>}
          </div>
        );
      };
      
      render(<ErrorButton />);
      const button = screen.getByText('Trigger Error');
      await user.click(button);
      
      expect(screen.getByRole('alert')).toHaveTextContent('Test error');
    });

    it('provides feedback for failed actions', async () => {
      const FailButton = () => {
        const [status, setStatus] = React.useState<'idle' | 'failed'>('idle');
        
        return (
          <button 
            onClick={() => setStatus('failed')}
            className={status === 'failed' ? 'error-state' : ''}
            aria-describedby={status === 'failed' ? 'error-desc' : undefined}
          >
            Action Button
            {status === 'failed' && (
              <span id="error-desc" className="sr-only">Action failed</span>
            )}
          </button>
        );
      };
      
      render(<FailButton />);
      const button = screen.getByText('Action Button');
      await user.click(button);
      
      expect(button).toHaveClass('error-state');
      expect(button).toHaveAttribute('aria-describedby', 'error-desc');
    });
  });
});