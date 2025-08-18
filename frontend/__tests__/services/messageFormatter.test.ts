/**
 * Message Formatter Service Tests
 * 
 * Tests for thread formatting preservation functionality.
 * Ensures proper markdown processing and content type detection.
 */

import { 
  detectContentType, 
  createFormattingMetadata, 
  processMessageContent,
  enhanceMessageWithFormatting,
  messageFormatterService,
  type ContentTypeInfo,
  type FormattingMetadata
} from '@/services/messageFormatter';
import type { Message } from '@/types/registry';

describe('MessageFormatter Service', () => {
  
  describe('Content Type Detection', () => {
    
    test('detects markdown content correctly', () => {
      const markdownContent = '# Header\n\n**Bold text** and *italic text*';
      const result = detectContentType(markdownContent);
      
      expect(result.hasMarkdown).toBe(true);
      expect(result.contentType).toBe('markdown');
    });

    test('detects code blocks correctly', () => {
      const codeContent = '```javascript\nconst test = "hello";\n```';
      const result = detectContentType(codeContent);
      
      expect(result.hasCodeBlocks).toBe(true);
      expect(result.contentType).toBe('code');
    });

    test('detects mixed content correctly', () => {
      const mixedContent = '# Test\n\n```js\ncode here\n```\n\n**bold**';
      const result = detectContentType(mixedContent);
      
      expect(result.hasMarkdown).toBe(true);
      expect(result.hasCodeBlocks).toBe(true);
      expect(result.contentType).toBe('mixed');
    });

    test('detects plain text correctly', () => {
      const plainContent = 'Just plain text with no formatting';
      const result = detectContentType(plainContent);
      
      expect(result.hasMarkdown).toBe(false);
      expect(result.hasCodeBlocks).toBe(false);
      expect(result.contentType).toBe('plain');
    });

  });

  describe('Formatting Metadata Creation', () => {
    
    test('creates metadata for markdown content', () => {
      const content = '# Header\n\n- List item\n- Another item';
      const metadata = createFormattingMetadata(content);
      
      expect(metadata.contentType).toBe('markdown');
      expect(metadata.preserveFormatting).toBe(true);
      expect(metadata.renderAsMarkdown).toBe(true);
      expect(metadata.version).toBe('1.0.0');
    });

    test('creates metadata for plain content', () => {
      const content = 'Plain text content';
      const metadata = createFormattingMetadata(content);
      
      expect(metadata.contentType).toBe('plain');
      expect(metadata.preserveFormatting).toBe(false);
      expect(metadata.renderAsMarkdown).toBe(false);
    });

  });

  describe('Content Processing', () => {
    
    test('processes markdown content correctly', () => {
      const content = '# Test\n\nSome **bold** text';
      const processed = processMessageContent(content);
      
      expect(processed.originalContent).toBe(content);
      expect(processed.processedContent).toBe('# Test\n\nSome **bold** text');
      expect(processed.metadata.contentType).toBe('markdown');
      expect(processed.renderingHints.useMarkdownRenderer).toBe(true);
    });

    test('handles content normalization', () => {
      const content = '  # Test\r\n\r\nContent  ';
      const processed = processMessageContent(content);
      
      expect(processed.processedContent).toBe('# Test\n\nContent');
    });

  });

  describe('Message Enhancement', () => {
    
    test('enhances message with formatting metadata', () => {
      const message: Message = {
        id: 'test-1',
        role: 'assistant',
        content: '# Response\n\n```js\nconst test = true;\n```',
        timestamp: Date.now()
      };

      const enhanced = enhanceMessageWithFormatting(message);
      
      expect(enhanced.metadata?.formatting).toBeDefined();
      expect(enhanced.metadata?.renderingHints).toBeDefined();
      expect(enhanced.metadata?.processedContent).toBeDefined();
      expect(enhanced.metadata?.formatting?.contentType).toBe('mixed');
    });

  });

  describe('MessageFormatterService', () => {
    
    test('formats single message', () => {
      const message: Message = {
        id: 'test-1',
        role: 'user',
        content: '## Question\n\nWhat is **markdown**?',
        timestamp: Date.now()
      };

      const formatted = messageFormatterService.formatMessage(message);
      
      expect(formatted.metadata?.formatting).toBeDefined();
      expect(formatted.metadata?.formatting?.contentType).toBe('markdown');
    });

    test('formats multiple messages', () => {
      const messages: Message[] = [
        {
          id: 'test-1',
          role: 'user',
          content: 'Plain text message',
          timestamp: Date.now()
        },
        {
          id: 'test-2',
          role: 'assistant',
          content: '```python\nprint("hello")\n```',
          timestamp: Date.now()
        }
      ];

      const formatted = messageFormatterService.formatMessages(messages);
      
      expect(formatted).toHaveLength(2);
      expect(formatted[0].metadata?.formatting?.contentType).toBe('plain');
      expect(formatted[1].metadata?.formatting?.contentType).toBe('code');
    });

    test('gets render configuration', () => {
      const message: Message = {
        id: 'test-1',
        role: 'assistant',
        content: '# Test',
        timestamp: Date.now(),
        metadata: {
          formatting: {
            contentType: 'markdown',
            preserveFormatting: true,
            renderAsMarkdown: true,
            highlightCode: false,
            processedAt: Date.now(),
            version: '1.0.0'
          },
          renderingHints: {
            useMarkdownRenderer: true,
            enableCodeHighlighting: false,
            preserveWhitespace: false,
            enableTableSupport: true
          }
        }
      };

      const config = messageFormatterService.getRenderConfig(message);
      
      expect(config.enableMarkdown).toBe(true);
      expect(config.enableCodeHighlighting).toBe(false);
      expect(config.enableTables).toBe(true);
    });

    test('validates formatting integrity', () => {
      const validMessage: Message = {
        id: 'test-1',
        role: 'assistant',
        content: 'Test',
        timestamp: Date.now(),
        metadata: {
          formatting: {
            contentType: 'plain',
            preserveFormatting: false,
            renderAsMarkdown: false,
            highlightCode: false,
            processedAt: Date.now(),
            version: '1.0.0'
          },
          renderingHints: {
            useMarkdownRenderer: false,
            enableCodeHighlighting: false,
            preserveWhitespace: false,
            enableTableSupport: false
          }
        }
      };

      const invalidMessage: Message = {
        id: 'test-2',
        role: 'assistant',
        content: 'Test',
        timestamp: Date.now()
      };

      expect(messageFormatterService.validateFormatting(validMessage)).toBe(true);
      expect(messageFormatterService.validateFormatting(invalidMessage)).toBe(false);
    });

  });

});