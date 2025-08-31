import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { MessageInput } from '@/components/chat/MessageInput';
import { 
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
t from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { MessageInput } from '@/components/chat/MessageInput';
import { 
  setupMessageInputMocks, 
  mockHooks,
  measurePerformance,
  createMockClipboardData
} from './shared-test-setup';

describe('MessageInput - Core Edge Cases', () => {
    jest.setTimeout(10000);
  const user = userEvent.setup();

  beforeEach(() => {
    setupMessageInputMocks();
    jest.clearAllMocks();
  });

  describe('Paste Handling', () => {
      jest.setTimeout(10000);
    it('handles plain text paste correctly', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const pasteText = 'This is pasted plain text';
      
      const clipboardData = createMockClipboardData(
        { 'text/plain': pasteText },
        ['text/plain']
      );
      
      fireEvent.paste(textarea, { clipboardData });
      
      expect(textarea).toHaveValue(pasteText);
    });

    it('strips HTML from rich text paste', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const richText = '<p>This is <strong>bold</strong> and <em>italic</em> text</p>';
      const expectedPlainText = 'This is bold and italic text';
      
      const clipboardData = createMockClipboardData(
        { 'text/html': richText, 'text/plain': expectedPlainText },
        ['text/html', 'text/plain']
      );
      
      fireEvent.paste(textarea, { clipboardData });
      
      expect(textarea).toHaveValue(expectedPlainText);
    });

    it('handles large paste within character limit', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const largeText = 'A'.repeat(9500);
      
      const clipboardData = createMockClipboardData(
        { 'text/plain': largeText },
        ['text/plain']
      );
      
      fireEvent.paste(textarea, { clipboardData });
      
      expect(textarea.value.length).toBe(9500);
    });

    it('truncates paste exceeding character limit', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const oversizedText = 'A'.repeat(15000);
      
      const clipboardData = createMockClipboardData(
        { 'text/plain': oversizedText },
        ['text/plain']
      );
      
      fireEvent.paste(textarea, { clipboardData });
      
      expect(textarea.value.length).toBeLessThanOrEqual(10000);
    });

    it('handles image paste gracefully', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const mockFile = new File(['fake-image-data'], 'test.png', { type: 'image/png' });
      
      const clipboardData = {
        getData: jest.fn().mockReturnValue(''),
        types: ['Files'],
        files: [mockFile]
      };
      
      fireEvent.paste(textarea, { clipboardData });
      
      expect(textarea).toBeInTheDocument();
    });
  });

  describe('Performance Tests', () => {
      jest.setTimeout(10000);
    it('handles typing up to character limit', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const longMessage = 'Long message text. '.repeat(500);
      
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      expect(textarea.value.length).toBeLessThanOrEqual(10000);
    });

    it('maintains performance with input changes', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      
      const duration = await measurePerformance(async () => {
        for (let i = 0; i < 25; i++) {
          fireEvent.change(textarea, { target: { value: 'A'.repeat(i * 40) } });
        }
      });
      
      expect(duration).toBeLessThan(1000);
    });
  });

  describe('Special Unicode Characters', () => {
      jest.setTimeout(10000);
    it('handles emoji input correctly', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const emojiText = 'Hello 👋 World 🌍 Fun! 🎉';
      
      await user.type(textarea, emojiText);
      
      expect(textarea).toHaveValue(emojiText);
    });

    it('handles complex Unicode characters', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const unicodeText = 'नमस्ते 你好 مرحبا Здравствуйте';
      
      await user.type(textarea, unicodeText);
      
      expect(textarea).toHaveValue(unicodeText);
    });

    it('handles combining characters correctly', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const combiningText = 'Café résumé naïve';
      
      await user.type(textarea, combiningText);
      
      expect(textarea).toHaveValue(combiningText);
    });

    it('handles zero-width characters', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const zwjText = 'Hello\u200DWorld';
      
      fireEvent.change(textarea, { target: { value: zwjText } });
      
      expect(textarea).toHaveValue(zwjText);
    });
  });

  describe('RTL (Right-to-Left) Text Support', () => {
      jest.setTimeout(10000);
    it('handles Arabic text input', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const arabicText = 'مرحبا بالعالم';
      
      await user.type(textarea, arabicText);
      
      expect(textarea).toHaveValue(arabicText);
    });

    it('handles Hebrew text input', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const hebrewText = 'שלום עולם';
      
      await user.type(textarea, hebrewText);
      
      expect(textarea).toHaveValue(hebrewText);
    });

    it('handles mixed LTR and RTL text', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const mixedText = 'Hello مرحبا World עולם';
      
      await user.type(textarea, mixedText);
      
      expect(textarea).toHaveValue(mixedText);
    });
  });

  describe('State Management', () => {
      jest.setTimeout(10000);
    it('prevents typing when sending', async () => {
      mockHooks.mockUseMessageSending.mockReturnValue({
        isSending: true,
        handleSend: jest.fn()
      });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeDisabled();
    });

    it('re-enables after sending', async () => {
      const { rerender } = render(<MessageInput />);
      
      mockHooks.mockUseMessageSending.mockReturnValue({
        isSending: true,
        handleSend: jest.fn()
      });
      
      rerender(<MessageInput />);
      expect(screen.getByRole('textbox')).toBeDisabled();
      
      mockHooks.mockUseMessageSending.mockReturnValue({
        isSending: false,
        handleSend: jest.fn()
      });
      
      rerender(<MessageInput />);
      expect(screen.getByRole('textbox')).not.toBeDisabled();
    });
  });

  describe('Code Blocks', () => {
      jest.setTimeout(10000);
    it('handles code blocks', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const codeBlock = '```js\nconsole.log("test");\n```';
      
      await user.type(textarea, codeBlock);
      expect(textarea).toHaveValue(codeBlock);
    });

    it('handles inline code', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Use `console.log()` for debug');
      expect(textarea).toHaveValue('Use `console.log()` for debug');
    });
  });

  describe('File Drag and Drop', () => {
      jest.setTimeout(10000);
    it('handles drag over events', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      
      fireEvent.dragOver(textarea);
      fireEvent.dragLeave(textarea);
      
      expect(textarea).toBeInTheDocument();
    });

    it('handles drop events gracefully', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const mockFile = new File(['test'], 'test.txt', { type: 'text/plain' });
      
      const dataTransfer = {
        files: [mockFile],
        types: ['Files']
      };
      
      fireEvent.drop(textarea, { dataTransfer });
      
      expect(textarea).toBeInTheDocument();
    });
  });
});