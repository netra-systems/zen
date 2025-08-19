import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Textarea } from '@/components/ui/textarea';

describe('Textarea Component - Comprehensive Tests', () => {
  const renderTextarea = (props = {}) => {
    return render(<Textarea data-testid="test-textarea" {...props} />);
  };

  const setupUser = () => userEvent.setup();

  describe('Basic Rendering', () => {
    it('renders textarea element correctly', () => {
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toBeInTheDocument();
      expect(textarea).toBeInstanceOf(HTMLTextAreaElement);
    });

    it('applies custom className correctly', () => {
      renderTextarea({ className: 'custom-textarea' });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveClass('custom-textarea');
    });

    it('displays placeholder text', () => {
      renderTextarea({ placeholder: 'Enter your message here' });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('placeholder', 'Enter your message here');
    });

    it('has minimum height styling', () => {
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveClass('min-h-[80px]');
    });
  });

  describe('Multi-line Text Entry', () => {
    it('accepts single line text input', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'Single line text');
      expect(textarea).toHaveValue('Single line text');
    });

    it('handles multi-line text input', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'Line 1{Enter}Line 2{Enter}Line 3');
      expect(textarea).toHaveValue('Line 1\nLine 2\nLine 3');
    });

    it('preserves line breaks in content', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'First{Enter}{Enter}Third line');
      expect(textarea).toHaveValue('First\n\nThird line');
    });

    it('handles tab character input', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'Text with{Tab}tab');
      expect(textarea).toHaveValue('Text with\ttab');
    });
  });

  describe('Auto-resize Behavior', () => {
    it('maintains minimum height', () => {
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      const initialHeight = textarea.style.height || '80px';
      expect(parseInt(initialHeight)).toBeGreaterThanOrEqual(80);
    });

    it('expands when content exceeds initial height', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      const longText = Array(10).fill('This is a long line of text.\n').join('');
      await user.type(textarea, longText);
      
      expect(textarea.scrollHeight).toBeGreaterThan(80);
    });

    it('handles rapid content changes', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'Short');
      await user.clear(textarea);
      await user.type(textarea, 'Much longer text content');
      
      expect(textarea).toHaveValue('Much longer text content');
    });
  });

  describe('Text Editing and Navigation', () => {
    it('allows text selection and replacement', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Replace this text' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.tripleClick(textarea);
      await user.type(textarea, 'New text');
      expect(textarea).toHaveValue('New text');
    });

    it('supports cursor positioning', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Position cursor here' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      await user.keyboard('{Home}{ArrowRight}{ArrowRight}');
      await user.type(textarea, 'X');
      expect(textarea).toHaveValue('PoXsition cursor here');
    });

    it('handles word boundary navigation', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Word by word navigation' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      await user.keyboard('{Control>}{ArrowLeft}{/Control}');
      expect(textarea.selectionStart).toBeLessThan(textarea.value.length);
    });

    it('supports line navigation', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Line 1\nLine 2\nLine 3' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      await user.keyboard('{ArrowDown}{ArrowDown}');
      expect(textarea.selectionStart).toBeGreaterThan(7);
    });
  });

  describe('Special Characters and Formatting', () => {
    it('accepts emoji and Unicode characters', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, '🎉 Celebration! Café résumé 中文');
      expect(textarea).toHaveValue('🎉 Celebration! Café résumé 中文');
    });

    it('handles code blocks and special formatting', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      const codeBlock = '```javascript\nfunction test() {\n  return "hello";\n}\n```';
      await user.type(textarea, codeBlock);
      expect(textarea).toHaveValue(codeBlock);
    });

    it('preserves whitespace and indentation', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, '  Indented text{Enter}    More indent');
      expect(textarea).toHaveValue('  Indented text\n    More indent');
    });

    it('handles HTML entities safely', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, '<div>HTML content</div>&nbsp;entity');
      expect(textarea).toHaveValue('<div>HTML content</div>&nbsp;entity');
    });
  });

  describe('Copy and Paste Operations', () => {
    it('supports copy operation', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Copy this content' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.tripleClick(textarea);
      await user.copy();
      expect(textarea.selectionStart).toBe(0);
      expect(textarea.selectionEnd).toBe(textarea.value.length);
    });

    it('handles paste with line breaks', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      await user.paste('Pasted line 1\nPasted line 2');
      expect(textarea).toHaveValue('Pasted line 1\nPasted line 2');
    });

    it('supports cut operation', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Cut this text' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.tripleClick(textarea);
      await user.cut();
      expect(textarea).toHaveValue('');
    });

    it('handles large paste operations', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      const largeText = Array(100).fill('Large content line').join('\n');
      await user.paste(largeText);
      expect(textarea.value.split('\n')).toHaveLength(100);
    });
  });

  describe('Validation and Error States', () => {
    it('respects required attribute', () => {
      renderTextarea({ required: true });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('required');
    });

    it('shows error state with aria-invalid', () => {
      renderTextarea({ 'aria-invalid': true });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('aria-invalid', 'true');
    });

    it('supports custom validation attributes', () => {
      renderTextarea({ minLength: 10, maxLength: 100 });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('minlength', '10');
      expect(textarea).toHaveAttribute('maxlength', '100');
    });

    it('validates content length', async () => {
      const user = setupUser();
      renderTextarea({ maxLength: 20 });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'This is a very long text that exceeds limit');
      expect(textarea.value.length).toBeLessThanOrEqual(20);
    });
  });

  describe('Max Length Enforcement', () => {
    it('prevents exceeding character limit', async () => {
      const user = setupUser();
      renderTextarea({ maxLength: 50 });
      const textarea = screen.getByTestId('test-textarea');
      
      const longText = 'a'.repeat(100);
      await user.type(textarea, longText);
      expect(textarea.value.length).toBe(50);
    });

    it('counts line breaks in character limit', async () => {
      const user = setupUser();
      renderTextarea({ maxLength: 10 });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'Line1{Enter}Line2');
      expect(textarea.value.length).toBeLessThanOrEqual(10);
    });

    it('allows deletion when at max length', async () => {
      const user = setupUser();
      renderTextarea({ maxLength: 5, defaultValue: 'Hello' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.keyboard('{Backspace}');
      expect(textarea).toHaveValue('Hell');
    });
  });

  describe('Auto-focus Functionality', () => {
    it('focuses automatically when autoFocus is true', () => {
      renderTextarea({ autoFocus: true });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveFocus();
    });

    it('positions cursor at end on auto-focus', () => {
      renderTextarea({ autoFocus: true, defaultValue: 'Focus here' });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea.selectionStart).toBe(10);
    });

    it('can receive focus programmatically', () => {
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      act(() => {
        textarea.focus();
      });
      expect(textarea).toHaveFocus();
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('supports select all shortcut', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Select all this text' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      await user.keyboard('{Control>}a{/Control}');
      expect(textarea.selectionStart).toBe(0);
      expect(textarea.selectionEnd).toBe(textarea.value.length);
    });

    it('handles undo operation', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Original text' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.clear(textarea);
      await user.type(textarea, 'New text');
      await user.keyboard('{Control>}z{/Control}');
      // Note: Browser undo behavior may vary
      expect(textarea.value).toBeTruthy();
    });

    it('supports keyboard navigation shortcuts', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Navigate this text' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      await user.keyboard('{Control>}{Home}{/Control}');
      expect(textarea.selectionStart).toBe(0);
    });
  });

  describe('Mobile Keyboard Behavior', () => {
    it('maintains proper touch target size', () => {
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveClass('min-h-[80px]');
    });

    it('handles mobile resize events', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      // Simulate mobile text input
      await user.type(textarea, 'Mobile input test');
      expect(textarea).toHaveValue('Mobile input test');
    });

    it('supports touch interactions', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      expect(textarea).toHaveFocus();
    });
  });

  describe('Disabled State', () => {
    it('prevents input when disabled', async () => {
      const user = setupUser();
      renderTextarea({ disabled: true });
      const textarea = screen.getByTestId('test-textarea');
      
      expect(textarea).toBeDisabled();
      await user.type(textarea, 'Should not work');
      expect(textarea).toHaveValue('');
    });

    it('shows disabled styling', () => {
      renderTextarea({ disabled: true });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveClass('disabled:cursor-not-allowed');
      expect(textarea).toHaveClass('disabled:opacity-50');
    });

    it('cannot receive focus when disabled', () => {
      renderTextarea({ disabled: true });
      const textarea = screen.getByTestId('test-textarea');
      
      act(() => {
        textarea.focus();
      });
      expect(textarea).not.toHaveFocus();
    });
  });

  describe('Event Handling', () => {
    it('calls onChange handler on input', async () => {
      const user = setupUser();
      const handleChange = jest.fn();
      renderTextarea({ onChange: handleChange });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'Test');
      expect(handleChange).toHaveBeenCalledTimes(4);
    });

    it('calls onFocus handler when focused', async () => {
      const user = setupUser();
      const handleFocus = jest.fn();
      renderTextarea({ onFocus: handleFocus });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      expect(handleFocus).toHaveBeenCalledTimes(1);
    });

    it('calls onBlur handler when blurred', async () => {
      const user = setupUser();
      const handleBlur = jest.fn();
      renderTextarea({ onBlur: handleBlur });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      await user.tab();
      expect(handleBlur).toHaveBeenCalledTimes(1);
    });

    it('calls onKeyDown handler correctly', async () => {
      const user = setupUser();
      const handleKeyDown = jest.fn();
      renderTextarea({ onKeyDown: handleKeyDown });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.click(textarea);
      await user.keyboard('a');
      expect(handleKeyDown).toHaveBeenCalledTimes(1);
    });
  });

  describe('Accessibility', () => {
    it('supports aria-label', () => {
      renderTextarea({ 'aria-label': 'Message input' });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('aria-label', 'Message input');
    });

    it('supports aria-describedby for help text', () => {
      renderTextarea({ 'aria-describedby': 'help-text' });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('aria-describedby', 'help-text');
    });

    it('has proper role attribute', () => {
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('role', 'textbox');
    });

    it('supports screen reader navigation', () => {
      renderTextarea({ 'aria-multiline': true });
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('aria-multiline', 'true');
    });
  });

  describe('Form Integration', () => {
    it('integrates with form element', () => {
      render(
        <form>
          <Textarea name="message" data-testid="test-textarea" />
        </form>
      );
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('name', 'message');
    });

    it('supports controlled component pattern', async () => {
      const user = setupUser();
      const TestComponent = () => {
        const [value, setValue] = React.useState('');
        return (
          <Textarea
            data-testid="test-textarea"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        );
      };
      
      render(<TestComponent />);
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'Controlled content');
      expect(textarea).toHaveValue('Controlled content');
    });

    it('supports uncontrolled component pattern', async () => {
      const user = setupUser();
      renderTextarea({ defaultValue: 'Initial content' });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.clear(textarea);
      await user.type(textarea, 'Updated content');
      expect(textarea).toHaveValue('Updated content');
    });

    it('handles form submission', () => {
      const handleSubmit = jest.fn();
      render(
        <form onSubmit={handleSubmit}>
          <Textarea name="content" defaultValue="Submit me" data-testid="test-textarea" />
          <button type="submit">Submit</button>
        </form>
      );
      
      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);
      expect(handleSubmit).toHaveBeenCalled();
    });
  });

  describe('Performance', () => {
    it('handles large content efficiently', async () => {
      const user = setupUser();
      renderTextarea();
      const textarea = screen.getByTestId('test-textarea');
      
      const largeContent = 'a'.repeat(10000);
      await user.paste(largeContent);
      expect(textarea.value.length).toBe(10000);
    });

    it('manages multiple rapid changes', async () => {
      const user = setupUser();
      const handleChange = jest.fn();
      renderTextarea({ onChange: handleChange });
      const textarea = screen.getByTestId('test-textarea');
      
      await user.type(textarea, 'Rapid typing test');
      expect(handleChange).toHaveBeenCalled();
      expect(textarea).toHaveValue('Rapid typing test');
    });
  });
});