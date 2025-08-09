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
    expect(screen.getByRole('button', { name: /hide/i })).toBeInTheDocument();
  });

  it('should display example prompts as cards', () => {
    render(<ExamplePrompts />);
    expect(screen.getByText(/I need to reduce costs but keep quality the same/i)).toBeInTheDocument();
    expect(screen.getByText(/My tools are too slow/i)).toBeInTheDocument();
  });

  it('should send a message and collapse the panel when a prompt is clicked', () => {
    render(<ExamplePrompts />);
    const promptText = screen.getByText(/I need to reduce costs but keep quality the same/i).textContent;
    fireEvent.click(screen.getByText(/I need to reduce costs but keep quality the same/i));

    expect(sendMessage).toHaveBeenCalledWith(JSON.stringify({ type: 'user_message', payload: { text: promptText } }));
    expect(setProcessing).toHaveBeenCalledWith(true);
    expect(screen.getByRole('button', { name: /show/i })).toBeInTheDocument(); // Panel should be collapsed
  });

  it('should toggle the collapsible panel', () => {
    render(<ExamplePrompts />);
    const toggleButton = screen.getByRole('button', { name: /hide/i });

    fireEvent.click(toggleButton);
    expect(screen.getByRole('button', { name: /show/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /show/i }));
    expect(screen.getByRole('button', { name: /hide/i })).toBeInTheDocument();
  });
});