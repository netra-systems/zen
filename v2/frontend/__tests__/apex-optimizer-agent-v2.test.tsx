import { render, screen, fireEvent } from '@testing-library/react';
import ApexOptimizerAgentV2 from '../app/components/apex-optimizer-agent-v2';
import { useAgent } from '../app/hooks/useAgent';

jest.mock('../app/hooks/useAgent');

describe('ApexOptimizerAgentV2', () => {
  const mockStartAgent = jest.fn();
  const mockSetMessageFilters = jest.fn();

  beforeEach(() => {
    (useAgent as jest.Mock).mockReturnValue({
      messages: [],
      messageFilters: new Set(),
      setMessageFilters: mockSetMessageFilters,
      showThinking: false,
      startAgent: mockStartAgent,
    });
  });

  it('should render the chat window', () => {
    render(<ApexOptimizerAgentV2 />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('should call startAgent when a message is sent', () => {
    render(<ApexOptimizerAgentV2 />);
    const input = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    expect(mockStartAgent).toHaveBeenCalledWith('Test message');
  });

  it('should display messages', () => {
    (useAgent as jest.Mock).mockReturnValue({
      messages: [{ id: '1', role: 'user', type: 'text', content: 'Test message' }],
      messageFilters: new Set(),
      setMessageFilters: mockSetMessageFilters,
      showThinking: false,
      startAgent: mockStartAgent,
    });

    render(<ApexOptimizerAgentV2 />);
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('should call startAgent when an example query is clicked', () => {
    render(<ApexOptimizerAgentV2 />);
    const exampleButton = screen.getByText('Example Query 1');

    fireEvent.click(exampleButton);

    expect(mockStartAgent).toHaveBeenCalledWith('Example Query 1');
  });

  it('should populate the input field when an example query is clicked', () => {
    render(<ApexOptimizerAgentV2 />);
    const exampleButton = screen.getByText('Example Query 1');

    fireEvent.click(exampleButton);

    const input = screen.getByRole('textbox');
    expect(input.value).toBe('Example Query 1');
  });

  it('should still send a message after an example is clicked', () => {
    render(<ApexOptimizerAgentV2 />);
    const exampleButton = screen.getByText('Example Query 1');

    fireEvent.click(exampleButton);

    const input = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Another message' } });
    fireEvent.click(sendButton);

    expect(mockStartAgent).toHaveBeenCalledWith('Another message');
  });
});