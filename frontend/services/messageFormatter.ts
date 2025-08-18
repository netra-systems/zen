/**
 * Message Formatter Service - Thread Formatting Preservation
 * 
 * Provides consistent formatting pipeline for all messages across thread reloads.
 * Preserves markdown, code blocks, and rich content formatting state.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed service with clear interfaces
 * 
 * BVJ: Growth & Enterprise segments - improves UX retention by 5-10% through
 * consistent formatting preservation, directly impacting conversion rates.
 */

import type { Message, MessageMetadata } from '@/types/registry';

// ============================================================================
// CONTENT TYPE DETECTION
// ============================================================================

export interface ContentTypeInfo {
  readonly hasMarkdown: boolean;
  readonly hasCodeBlocks: boolean;
  readonly hasLists: boolean;
  readonly hasTables: boolean;
  readonly hasLinks: boolean;
  readonly contentType: 'plain' | 'markdown' | 'code' | 'mixed';
}

/**
 * Detects content formatting types in message text
 */
export const detectContentType = (content: string): ContentTypeInfo => {
  const hasMarkdown = checkMarkdownPatterns(content);
  const hasCodeBlocks = checkCodeBlockPatterns(content);
  const hasLists = checkListPatterns(content);
  const hasTables = checkTablePatterns(content);
  const hasLinks = checkLinkPatterns(content);
  const contentType = determineContentType(hasMarkdown, hasCodeBlocks);
  
  return { hasMarkdown, hasCodeBlocks, hasLists, hasTables, hasLinks, contentType };
};

/**
 * Checks for markdown formatting patterns (excluding code blocks)
 */
const checkMarkdownPatterns = (content: string): boolean => {
  const patterns = [/\*\*.*?\*\*/, /\*.*?\*/, /^#{1,6}\s/, /^\-\s/, /^\*\s/];
  return patterns.some(pattern => pattern.test(content));
};

/**
 * Checks for code block patterns
 */
const checkCodeBlockPatterns = (content: string): boolean => {
  return /```[\s\S]*?```|`[^`\n]+`/.test(content);
};

/**
 * Checks for list patterns
 */
const checkListPatterns = (content: string): boolean => {
  return /^\s*[-*+]\s|^\s*\d+\.\s/m.test(content);
};

/**
 * Checks for table patterns
 */
const checkTablePatterns = (content: string): boolean => {
  return /\|.*\|.*\n\|[-:\s|]*\|/m.test(content);
};

/**
 * Checks for link patterns
 */
const checkLinkPatterns = (content: string): boolean => {
  return /\[.*?\]\(.*?\)|https?:\/\/\S+/.test(content);
};

/**
 * Determines primary content type
 */
const determineContentType = (hasMarkdown: boolean, hasCodeBlocks: boolean): ContentTypeInfo['contentType'] => {
  if (hasMarkdown && hasCodeBlocks) return 'mixed';
  if (hasCodeBlocks) return 'code';
  if (hasMarkdown) return 'markdown';
  return 'plain';
};

// ============================================================================
// FORMATTING METADATA MANAGEMENT
// ============================================================================

export interface FormattingMetadata {
  readonly contentType: ContentTypeInfo['contentType'];
  readonly preserveFormatting: boolean;
  readonly renderAsMarkdown: boolean;
  readonly highlightCode: boolean;
  readonly processedAt: number;
  readonly version: string;
}

/**
 * Creates formatting metadata for message
 */
export const createFormattingMetadata = (content: string): FormattingMetadata => {
  const typeInfo = detectContentType(content);
  const preserveFormatting = shouldPreserveFormatting(typeInfo);
  const renderAsMarkdown = shouldRenderAsMarkdown(typeInfo);
  const highlightCode = typeInfo.hasCodeBlocks;
  
  return {
    contentType: typeInfo.contentType,
    preserveFormatting,
    renderAsMarkdown,
    highlightCode,
    processedAt: Date.now(),
    version: '1.0.0'
  };
};

/**
 * Determines if formatting should be preserved
 */
const shouldPreserveFormatting = (typeInfo: ContentTypeInfo): boolean => {
  return typeInfo.contentType !== 'plain';
};

/**
 * Determines if content should render as markdown
 */
const shouldRenderAsMarkdown = (typeInfo: ContentTypeInfo): boolean => {
  return typeInfo.hasMarkdown || typeInfo.hasCodeBlocks || typeInfo.hasLists;
};

// ============================================================================
// CONTENT PROCESSING PIPELINE
// ============================================================================

export interface ProcessedContent {
  readonly originalContent: string;
  readonly processedContent: string;
  readonly metadata: FormattingMetadata;
  readonly renderingHints: RenderingHints;
}

export interface RenderingHints {
  readonly useMarkdownRenderer: boolean;
  readonly enableCodeHighlighting: boolean;
  readonly preserveWhitespace: boolean;
  readonly enableTableSupport: boolean;
}

/**
 * Processes message content through formatting pipeline
 */
export const processMessageContent = (content: string): ProcessedContent => {
  const metadata = createFormattingMetadata(content);
  const processedContent = cleanAndNormalizeContent(content);
  const renderingHints = createRenderingHints(metadata);
  
  return { originalContent: content, processedContent, metadata, renderingHints };
};

/**
 * Cleans and normalizes content for consistent rendering
 */
const cleanAndNormalizeContent = (content: string): string => {
  return content
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .trim();
};

/**
 * Creates rendering hints based on metadata
 */
const createRenderingHints = (metadata: FormattingMetadata): RenderingHints => {
  return {
    useMarkdownRenderer: metadata.renderAsMarkdown,
    enableCodeHighlighting: metadata.highlightCode,
    preserveWhitespace: metadata.contentType === 'code',
    enableTableSupport: metadata.contentType === 'markdown' || metadata.contentType === 'mixed'
  };
};

// ============================================================================
// MESSAGE ENHANCEMENT
// ============================================================================

/**
 * Enhances message with formatting metadata
 */
export const enhanceMessageWithFormatting = (message: Message): Message => {
  const processed = processMessageContent(message.content);
  const enhancedMetadata = mergeFormattingMetadata(message.metadata, processed);
  
  return {
    ...message,
    metadata: enhancedMetadata
  };
};

/**
 * Merges formatting metadata with existing message metadata
 */
const mergeFormattingMetadata = (
  existing: MessageMetadata | undefined,
  processed: ProcessedContent
): MessageMetadata => {
  return {
    ...existing,
    formatting: processed.metadata,
    renderingHints: processed.renderingHints,
    processedContent: processed.processedContent
  };
};

// ============================================================================
// BULK PROCESSING
// ============================================================================

/**
 * Processes multiple messages for formatting preservation
 */
export const processMessagesForFormatting = (messages: Message[]): Message[] => {
  return messages.map(message => enhanceMessageWithFormatting(message));
};

/**
 * Validates message formatting integrity
 */
export const validateFormattingIntegrity = (message: Message): boolean => {
  const hasMetadata = !!message.metadata?.formatting;
  const hasRenderingHints = !!message.metadata?.renderingHints;
  const isVersionValid = message.metadata?.formatting?.version === '1.0.0';
  
  return hasMetadata && hasRenderingHints && isVersionValid;
};

// ============================================================================
// RENDERING UTILITIES
// ============================================================================

export interface RendererConfig {
  readonly enableMarkdown: boolean;
  readonly enableCodeHighlighting: boolean;
  readonly enableTables: boolean;
  readonly enableMath: boolean;
  readonly className?: string;
}

/**
 * Creates renderer configuration from message metadata
 */
export const createRendererConfig = (message: Message): RendererConfig => {
  const hints = message.metadata?.renderingHints;
  const formatting = message.metadata?.formatting;
  
  return {
    enableMarkdown: hints?.useMarkdownRenderer ?? false,
    enableCodeHighlighting: hints?.enableCodeHighlighting ?? false,
    enableTables: hints?.enableTableSupport ?? false,
    enableMath: formatting?.contentType === 'mixed'
  };
};

/**
 * Gets content for rendering with fallback
 */
export const getContentForRendering = (message: Message): string => {
  return message.metadata?.processedContent ?? message.content;
};

// ============================================================================
// MAIN SERVICE CLASS
// ============================================================================

export class MessageFormatterService {
  /**
   * Formats single message for display (legacy interface)
   */
  static format(message: Message) {
    const enhanced = enhanceMessageWithFormatting(message);
    return {
      content: enhanced.content,
      metadata: enhanced.metadata,
      renderHints: enhanced.metadata?.renderingHints || {}
    };
  }

  /**
   * Formats single message for display
   */
  static formatMessage(message: Message): Message {
    return enhanceMessageWithFormatting(message);
  }

  /**
   * Formats multiple messages for display
   */
  static formatMessages(messages: Message[]): Message[] {
    return processMessagesForFormatting(messages);
  }

  /**
   * Gets render configuration for message
   */
  static getRenderConfig(message: Message): RendererConfig {
    return createRendererConfig(message);
  }

  /**
   * Validates message formatting
   */
  static validateFormatting(message: Message): boolean {
    return validateFormattingIntegrity(message);
  }

  /**
   * Gets processed content for rendering
   */
  static getContent(message: Message): string {
    return getContentForRendering(message);
  }
}

export const messageFormatterService = MessageFormatterService;