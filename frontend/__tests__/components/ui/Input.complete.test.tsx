import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '@/components/ui/input';

describe('Input Component - Comprehensive Tests', () => {
  const renderInput = (props = {}) => {
    return render(<Input data-testid="test-input" {...props} />);
  };

  const setupUser = () => userEvent.setup();

  describe('Basic Rendering', () => {
    it('renders input element correctly', () => {
      renderInput();
      const input = screen.getByTestId('test-input');
      expect(input).toBeInTheDocument();
      expect(input).toBeInstanceOf(HTMLInputElement);
    });

    it('applies custom className correctly', () => {
      renderInput({ className: 'custom-class' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveClass('custom-class');
    });

    it('sets input type correctly', () => {
      renderInput({ type: 'email' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('type', 'email');
    });

    it('displays placeholder text', () => {
      renderInput({ placeholder: 'Enter text here' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('placeholder', 'Enter text here');
    });
  });

  describe('Text Entry and Editing', () => {
    it('accepts text input correctly', async () => {
      const user = setupUser();
      renderInput();
      const input = screen.getByTestId('test-input');
      
      await user.type(input, 'Hello World');
      expect(input).toHaveValue('Hello World');
    });

    it('handles multi-character input', async () => {
      const user = setupUser();
      renderInput();
      const input = screen.getByTestId('test-input');
      
      await user.type(input, 'Test 123');
      expect(input).toHaveValue('Test 123');
    });

    it('allows text editing and deletion', async () => {
      const user = setupUser();
      renderInput();
      const input = screen.getByTestId('test-input');
      
      await user.type(input, 'Hello');
      await user.keyboard('{Backspace}{Backspace}');
      expect(input).toHaveValue('Hel');
    });

    it('handles clearing all text', async () => {
      const user = setupUser();
      renderInput();
      const input = screen.getByTestId('test-input');
      
      await user.type(input, 'Test text');
      await user.clear(input);
      expect(input).toHaveValue('');
    });
  });

  describe('Special Characters and Emoji', () => {
    it('accepts emoji input', async () => {
      const user = setupUser();
      renderInput();
      const input = screen.getByTestId('test-input');
      
      await user.type(input, '🚀 Rocket');
      expect(input).toHaveValue('🚀 Rocket');
    });

    it('handles special characters', async () => {
      const user = setupUser();
      renderInput();
      const input = screen.getByTestId('test-input');
      
      await user.type(input, '!@#$%^&*()');
      expect(input).toHaveValue('!@#$%^&*()');
    });

    it('accepts Unicode characters', async () => {
      const user = setupUser();
      renderInput();
      const input = screen.getByTestId('test-input');
      
      await user.type(input, 'Café résumé naïve');
      expect(input).toHaveValue('Café résumé naïve');
    });

    it('handles HTML entities safely', async () => {
      const user = setupUser();
      renderInput();
      const input = screen.getByTestId('test-input');
      
      await user.type(input, '<script>alert("test")</script>');
      expect(input).toHaveValue('<script>alert("test")</script>');
    });
  });

  describe('Copy and Paste Functionality', () => {
    it('supports keyboard copy operation', async () => {
      const user = setupUser();
      renderInput({ defaultValue: 'Copy me' });
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      await user.keyboard('{Control>}a{/Control}');
      expect(input.selectionStart).toBe(0);
      expect(input.selectionEnd).toBe(7);
    });

    it('handles paste operation', async () => {
      const user = setupUser();
      renderInput();
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      await user.paste('Pasted content');
      expect(input).toHaveValue('Pasted content');
    });

    it('supports select all shortcut', async () => {
      const user = setupUser();
      renderInput({ defaultValue: 'Select all text' });
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      await user.keyboard('{Control>}a{/Control}');
      expect(input.selectionStart).toBe(0);
      expect(input.selectionEnd).toBe(15);
    });

    it('handles cut operation', async () => {
      const user = setupUser();
      renderInput({ defaultValue: 'Cut this text' });
      const input = screen.getByTestId('test-input');
      
      await user.tripleClick(input);
      await user.cut();
      expect(input).toHaveValue('');
    });
  });

  describe('Validation and Error States', () => {
    it('shows required validation', () => {
      renderInput({ required: true });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('required');
    });

    it('respects aria-invalid for error states', () => {
      renderInput({ 'aria-invalid': true });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('supports aria-describedby for error messages', () => {
      renderInput({ 'aria-describedby': 'error-message' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('aria-describedby', 'error-message');
    });

    it('validates email format when type is email', () => {
      renderInput({ type: 'email' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('type', 'email');
    });
  });

  describe('Max Length Enforcement', () => {
    it('respects maxLength attribute', async () => {
      const user = setupUser();
      renderInput({ maxLength: 5 });
      const input = screen.getByTestId('test-input');
      
      await user.type(input, 'ThisIsLongerThanFive');
      expect(input).toHaveValue('ThisI');
    });

    it('prevents exceeding character limit', async () => {
      const user = setupUser();
      renderInput({ maxLength: 3 });
      const input = screen.getByTestId('test-input');
      
      await user.type(input, 'Test');
      expect(input.value.length).toBeLessThanOrEqual(3);
    });

    it('allows deletion when at max length', async () => {
      const user = setupUser();
      renderInput({ maxLength: 5, defaultValue: 'Hello' });
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      await user.keyboard('{End}{Backspace}');
      expect(input).toHaveValue('Hell');
    });
  });

  describe('Auto-focus Functionality', () => {
    it('focuses automatically when autoFocus is true', () => {
      renderInput({ autoFocus: true });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveFocus();
    });

    it('does not auto-focus by default', () => {
      renderInput();
      const input = screen.getByTestId('test-input');
      expect(input).not.toHaveFocus();
    });

    it('can receive focus programmatically', () => {
      renderInput();
      const input = screen.getByTestId('test-input');
      
      act(() => {
        input.focus();
      });
      expect(input).toHaveFocus();
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('supports Home key navigation', async () => {
      const user = setupUser();
      renderInput({ defaultValue: 'Navigate me' });
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      await user.keyboard('{End}');
      expect(input.selectionStart).toBe(11);
      
      await user.keyboard('{Home}');
      expect(input.selectionStart).toBe(0);
    });

    it('supports End key navigation', async () => {
      const user = setupUser();
      renderInput({ defaultValue: 'Test text' });
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      await user.keyboard('{Home}{End}');
      expect(input.selectionStart).toBe(9);
    });

    it('supports arrow key navigation', async () => {
      const user = setupUser();
      renderInput({ defaultValue: 'Arrow keys' });
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      await user.keyboard('{Home}{ArrowRight}{ArrowRight}');
      expect(input.selectionStart).toBe(2);
    });
  });

  describe('Disabled State', () => {
    it('prevents input when disabled', async () => {
      const user = setupUser();
      renderInput({ disabled: true });
      const input = screen.getByTestId('test-input');
      
      expect(input).toBeDisabled();
      await user.type(input, 'Should not work');
      expect(input).toHaveValue('');
    });

    it('shows disabled styling', () => {
      renderInput({ disabled: true });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveClass('disabled:cursor-not-allowed');
      expect(input).toHaveClass('disabled:opacity-50');
    });

    it('cannot receive focus when disabled', () => {
      renderInput({ disabled: true });
      const input = screen.getByTestId('test-input');
      
      act(() => {
        input.focus();
      });
      expect(input).not.toHaveFocus();
    });
  });

  describe('Event Handling', () => {
    it('calls onChange handler on input', async () => {
      const handleChange = jest.fn();
      renderInput({ onChange: handleChange });
      const input = screen.getByTestId('test-input');
      
      // Simulate typing "Test" character by character using fireEvent
      fireEvent.change(input, { target: { value: 'T' } });
      fireEvent.change(input, { target: { value: 'Te' } });
      fireEvent.change(input, { target: { value: 'Tes' } });
      fireEvent.change(input, { target: { value: 'Test' } });
      expect(handleChange).toHaveBeenCalledTimes(4);
    });

    it('calls onFocus handler when focused', async () => {
      const user = setupUser();
      const handleFocus = jest.fn();
      renderInput({ onFocus: handleFocus });
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      expect(handleFocus).toHaveBeenCalledTimes(1);
    });

    it('calls onBlur handler when blurred', async () => {
      const user = setupUser();
      const handleBlur = jest.fn();
      renderInput({ onBlur: handleBlur });
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      await user.tab();
      expect(handleBlur).toHaveBeenCalledTimes(1);
    });

    it('calls onKeyDown handler on key press', async () => {
      const user = setupUser();
      const handleKeyDown = jest.fn();
      renderInput({ onKeyDown: handleKeyDown });
      const input = screen.getByTestId('test-input');
      
      await user.click(input);
      await user.keyboard('a');
      expect(handleKeyDown).toHaveBeenCalledTimes(1);
    });
  });

  describe('Mobile Keyboard Behavior', () => {
    it('shows numeric keyboard for number input', () => {
      renderInput({ type: 'number' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('type', 'number');
    });

    it('shows email keyboard for email input', () => {
      renderInput({ type: 'email' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('type', 'email');
    });

    it('shows telephone keyboard for tel input', () => {
      renderInput({ type: 'tel' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('type', 'tel');
    });

    it('shows URL keyboard for url input', () => {
      renderInput({ type: 'url' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('type', 'url');
    });
  });

  describe('Accessibility', () => {
    it('supports aria-label', () => {
      renderInput({ 'aria-label': 'Search input' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('aria-label', 'Search input');
    });

    it('supports aria-labelledby', () => {
      renderInput({ 'aria-labelledby': 'label-id' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('aria-labelledby', 'label-id');
    });

    it('has proper input type for screen readers', () => {
      renderInput();
      const input = screen.getByTestId('test-input');
      expect(input).toBeInstanceOf(HTMLInputElement);
      expect(input.tagName.toLowerCase()).toBe('input');
    });

    it('supports screen reader descriptions', () => {
      renderInput({ 'aria-describedby': 'help-text' });
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('aria-describedby', 'help-text');
    });
  });

  describe('Form Integration', () => {
    it('integrates with form element', () => {
      render(
        <form>
          <Input name="test-field" data-testid="test-input" />
        </form>
      );
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('name', 'test-field');
    });

    it('supports controlled component pattern', async () => {
      const user = setupUser();
      const TestComponent = () => {
        const [value, setValue] = React.useState('');
        return (
          <Input
            data-testid="test-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        );
      };
      
      render(<TestComponent />);
      const input = screen.getByTestId('test-input');
      
      await user.type(input, 'Controlled');
      expect(input).toHaveValue('Controlled');
    });

    it('supports uncontrolled component pattern', async () => {
      const user = setupUser();
      renderInput({ defaultValue: 'Initial' });
      const input = screen.getByTestId('test-input');
      
      await user.clear(input);
      await user.type(input, 'Updated');
      expect(input).toHaveValue('Updated');
    });
  });
});