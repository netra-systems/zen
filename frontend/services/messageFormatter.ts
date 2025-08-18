/**
 * Message Formatter Service - Format preservation and rendering pipeline
 * 
 * Provides consistent message formatting across thread loading and real-time updates.
 * Ensures format preservation when threads are reloaded from storage.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed service with clear interfaces
 * 
 * BVJ:
 * Segment: All segments (Free, Early, Mid, Enterprise)
 * Business Goal: Improve user experience and engagement retention
 * Value Impact: Consistent formatting reduces user confusion, improves perceived quality
 * Revenue Impact: Better UX increases conversion rates and reduces churn
 */

import type { Message, ChatMessage, MessageMetadata } from '@/types/registry';

/**
 * Formatting metadata interface for messages
 */
export interface FormattingMetadata {
  readonly preserveWhitespace: boolean;
  readonly renderMarkdown: boolean;
  readonly parseLinks: boolean;
  readonly highlightCode: boolean;
  readonly contentType: ContentType;
  readonly formatVersion: string;
}

/**
 * Content type enumeration for message formatting
 */
export type ContentType = 
  | 'plain_text'
  | 'markdown' 
  | 'code'
  | 'json'
  | 'error'
  | 'system';

/**
 * Formatted content result interface
 */
export interface FormattedContent {
  readonly content: string;
  readonly metadata: FormattingMetadata;
  readonly processedAt: number;
  readonly renderHints: RenderHints;
}

/**
 * Rendering hints for UI components
 */
export interface RenderHints {
  readonly shouldPreserveWhitespace: boolean;
  readonly shouldRenderAsMarkdown: boolean;
  readonly shouldHighlightSyntax: boolean;
  readonly estimatedHeight: number;
}

/**
 * Default formatting metadata
 */
const DEFAULT_FORMATTING: FormattingMetadata = {
  preserveWhitespace: true,
  renderMarkdown: true,
  parseLinks: true,
  highlightCode: true,
  contentType: 'plain_text',
  formatVersion: '1.0'
};

/**
 * Determines content type from message properties
 */
const detectContentType = (message: Message): ContentType => {
  if (message.error) return 'error';
  if (message.role === 'system') return 'system';
  if (message.tool_info) return 'json';
  return detectFromContent(message.content);
};

/**
 * Detects content type from string content
 */
const detectFromContent = (content: string): ContentType => {
  if (isJsonContent(content)) return 'json';
  if (isCodeContent(content)) return 'code';
  if (isMarkdownContent(content)) return 'markdown';
  return 'plain_text';
};

/**
 * Checks if content appears to be JSON
 */
const isJsonContent = (content: string): boolean => {
  const trimmed = content.trim();
  return (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
         (trimmed.startsWith('[') && trimmed.endsWith(']'));
};

/**
 * Checks if content appears to be code
 */
const isCodeContent = (content: string): boolean => {
  const codePatterns = [/```/, /function\s+\w+/, /class\s+\w+/, /import\s+/];
  return codePatterns.some(pattern => pattern.test(content));
};

/**
 * Checks if content contains markdown
 */
const isMarkdownContent = (content: string): boolean => {
  const markdownPatterns = [/^#{1,6}\s/, /\*\*.*\*\*/, /\*.*\*/, /`.*`/];
  return markdownPatterns.some(pattern => pattern.test(content));
};

/**
 * Creates formatting metadata for message
 */
const createFormattingMetadata = (
  message: Message, 
  overrides?: Partial<FormattingMetadata>
): FormattingMetadata => {
  const contentType = detectContentType(message);
  return {
    ...DEFAULT_FORMATTING,
    contentType,
    ...overrides
  };
};

/**
 * Generates render hints based on content and metadata
 */
const generateRenderHints = (
  content: string,
  metadata: FormattingMetadata
): RenderHints => {
  return {
    shouldPreserveWhitespace: metadata.preserveWhitespace,
    shouldRenderAsMarkdown: metadata.renderMarkdown && metadata.contentType === 'markdown',
    shouldHighlightSyntax: metadata.highlightCode && metadata.contentType === 'code',
    estimatedHeight: calculateEstimatedHeight(content)
  };
};

/**
 * Calculates estimated render height for performance
 */
const calculateEstimatedHeight = (content: string): number => {
  const lines = content.split('\n').length;
  const avgCharPerLine = 80;
  const avgLineHeight = 20;
  return Math.max(lines * avgLineHeight, 40);
};

/**
 * Main formatting function - processes message content
 */
export const formatMessage = (
  message: Message,
  options?: Partial<FormattingMetadata>
): FormattedContent => {
  const metadata = createFormattingMetadata(message, options);
  const processedContent = preserveFormattingInContent(message.content, metadata);
  
  return {
    content: processedContent,
    metadata,
    processedAt: Date.now(),
    renderHints: generateRenderHints(processedContent, metadata)
  };
};

/**
 * Preserves formatting in content based on metadata
 */
const preserveFormattingInContent = (
  content: string,
  metadata: FormattingMetadata
): string => {
  if (!metadata.preserveWhitespace) {
    return content.trim();
  }
  return content;
};

/**
 * Extracts formatting metadata from message
 */
export const extractFormattingMetadata = (message: Message): FormattingMetadata => {
  const existingMetadata = message.metadata?.formattingMetadata as FormattingMetadata;
  
  if (existingMetadata && isValidFormattingMetadata(existingMetadata)) {
    return existingMetadata;
  }
  
  return createFormattingMetadata(message);
};

/**
 * Validates formatting metadata structure
 */
const isValidFormattingMetadata = (metadata: any): metadata is FormattingMetadata => {
  return metadata && 
         typeof metadata.preserveWhitespace === 'boolean' &&
         typeof metadata.renderMarkdown === 'boolean' &&
         typeof metadata.contentType === 'string';
};

/**
 * Enriches message with formatting metadata
 */
export const enrichMessageWithFormatting = (message: Message): Message => {
  const formattingMetadata = extractFormattingMetadata(message);
  
  return {
    ...message,
    metadata: {
      ...message.metadata,
      formattingMetadata
    }
  };
};

/**
 * Batch processes messages for formatting
 */
export const formatMessages = (messages: Message[]): FormattedContent[] => {
  return messages.map(message => formatMessage(message));
};

/**
 * Message Formatter Service class
 */
export class MessageFormatterService {
  /**
   * Formats single message with options
   */
  static format(
    message: Message, 
    options?: Partial<FormattingMetadata>
  ): FormattedContent {
    return formatMessage(message, options);
  }

  /**
   * Enriches message with formatting metadata
   */
  static enrich(message: Message): Message {
    return enrichMessageWithFormatting(message);
  }

  /**
   * Batch formats multiple messages
   */
  static formatBatch(messages: Message[]): FormattedContent[] {
    return formatMessages(messages);
  }

  /**
   * Extracts formatting metadata from message
   */
  static extractMetadata(message: Message): FormattingMetadata {
    return extractFormattingMetadata(message);
  }
}

export const messageFormatterService = MessageFormatterService;