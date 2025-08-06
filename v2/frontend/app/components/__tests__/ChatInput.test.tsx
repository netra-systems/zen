import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '../ChatInput';

describe('ChatInput', () => {
  it('should disable the submit button when the input is empty', () => {
    render(<ChatInput />);
    const submitButton = screen.getByText('Submit');
    expect(submitButton).toBeDisabled();
  });

  it('should populate the input field when the "Load Example" button is clicked', () => {
    render(<ChatInput />);
    const loadExampleButton = screen.getByText('Load Example');
    fireEvent.click(loadExampleButton);
    const input = screen.getByPlaceholderText('Type your message...');
    expect(input.value).not.toBe('');
  });
});
