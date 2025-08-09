import { render, screen, fireEvent } from '@testing-library/react';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store';

jest.mock('@/hooks/useWebSocket');
jest.mock('@/store');

describe('ExamplePrompts', () => {
  const sendMessage = jest.fn();
  const setProcessing = jest.fn();

  beforeEach(() => {
    (useWebSocket as jest.Mock).mockReturnValue({
      sendMessage,
    });
    (useChatStore as jest.Mock).mockReturnValue({
      setProcessing,
    });
  });

  it('should render the example prompts section', () => {
    render(<ExamplePrompts />);
    expect(screen.getByText('Example Prompts')).toBeInTheDocument();
    expect(screen.getByText('Show')).toBeInTheDocument();
  });

  it('should display example prompts as cards', () => {
    render(<ExamplePrompts />);
    expect(screen.getByText(/I need to reduce costs but keep quality the same/i)).toBeInTheDocument();
    expect(screen.getByText(/My tools are too slow/i)).toBeInTheDocument();
  });

  it('should send a message and collapse the panel when a prompt is clicked', () => {
    render(<ExamplePrompts />);
    const promptText = /I need to reduce costs but keep quality the same/i;
    fireEvent.click(screen.getByText(promptText));

    expect(sendMessage).toHaveBeenCalledWith(JSON.stringify({ type: 'user_message', payload: { text: screen.getByText(promptText).textContent } }));
    expect(setProcessing).toHaveBeenCalledWith(true);
    expect(screen.getByText('Show')).toBeInTheDocument(); // Panel should be collapsed
  });

  it('should toggle the collapsible panel', () => {
    render(<ExamplePrompts />);
    const toggleButton = screen.getByRole('button', { name: /show/i });

    fireEvent.click(toggleButton);
    expect(screen.getByText('Hide')).toBeInTheDocument();

    fireEvent.click(toggleButton);
    expect(screen.getByText('Show')).toBeInTheDocument();
  });
});