/**
 * Formatted Message Content Component
 * 
 * Renders message content with preserved formatting using MessageFormatter service.
 * Integrates react-markdown with syntax highlighting and proper content detection.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed React component
 */

import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '@/types/registry';
import { 
  MessageFormatterService, 
  type FormattedContent,
  type RenderHints 
} from '@/services/messageFormatter';

// ============================================================================
// PROPS AND INTERFACES
// ============================================================================

interface FormattedMessageContentProps {
  readonly message: Message;
  readonly className?: string;
  readonly enableInteractiveElements?: boolean;
}

interface CodeComponentProps {
  readonly node?: any;
  readonly inline?: boolean;
  readonly className?: string;
  readonly children?: React.ReactNode;
}

interface RendererConfig {
  readonly enableMarkdown: boolean;
  readonly enableCodeHighlighting: boolean;
  readonly enableTables: boolean;
  readonly enableMath: boolean;
  readonly preserveWhitespace: boolean;
}

// ============================================================================
// CONFIGURATION HELPERS
// ============================================================================

/**
 * Creates render configuration from render hints
 */
const createRenderConfig = (renderHints: RenderHints): RendererConfig => {
  return {
    enableMarkdown: renderHints.shouldRenderAsMarkdown,
    enableCodeHighlighting: renderHints.shouldHighlightSyntax,
    enableTables: true,
    enableMath: true,
    preserveWhitespace: renderHints.shouldPreserveWhitespace
  };
};

// ============================================================================
// CONTENT PROCESSING HOOKS
// ============================================================================

/**
 * Processes message and creates render configuration
 */
const useMessageProcessing = (message: Message) => {
  return useMemo(() => {
    const formatted = MessageFormatterService.format(message);
    const config = createRenderConfig(formatted.renderHints);
    const content = formatted.content;
    const isValid = Boolean(content && formatted.metadata);
    
    return { formatted, config, content, isValid };
  }, [message.id, message.content, message.metadata?.formattingMetadata]);
};

/**
 * Creates markdown component configuration
 */
const useMarkdownComponents = (config: RendererConfig) => {
  return useMemo(() => ({
    code: createCodeComponent(config.enableCodeHighlighting),
    pre: createPreComponent(),
    table: createTableComponent(config.enableTables),
    th: createTableHeaderComponent(),
    td: createTableCellComponent()
  }), [config.enableCodeHighlighting, config.enableTables]);
};

// ============================================================================
// MARKDOWN COMPONENT FACTORIES
// ============================================================================

/**
 * Creates code block component with syntax highlighting
 */
const createCodeComponent = (enableHighlighting: boolean) => {
  return ({ node, inline, className, children, ...props }: CodeComponentProps) => {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';
    
    return createCodeElement(inline, enableHighlighting, language, children, props);
  };
};

/**
 * Creates appropriate code element based on context
 */
const createCodeElement = (
  inline: boolean | undefined, 
  enableHighlighting: boolean, 
  language: string, 
  children: React.ReactNode, 
  props: any
) => {
  if (inline) {
    return <code className="bg-gray-100 px-1 py-0.5 rounded text-sm" {...props}>{children}</code>;
  }
  
  return createSyntaxHighlighter(enableHighlighting, language, children);
};

/**
 * Creates syntax highlighter component
 */
const createSyntaxHighlighter = (
  enableHighlighting: boolean, 
  language: string, 
  children: React.ReactNode
) => {
  if (!enableHighlighting) {
    return <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto"><code>{children}</code></pre>;
  }
  
  return (
    <SyntaxHighlighter 
      style={oneDark} 
      language={language || 'text'} 
      PreTag="div"
      className="rounded-lg"
    >
      {String(children).replace(/\n$/, '')}
    </SyntaxHighlighter>
  );
};

/**
 * Creates pre-formatted text component
 */
const createPreComponent = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <div className="overflow-x-auto">{children}</div>
  );
};

/**
 * Creates table component with styling
 */
const createTableComponent = (enableTables: boolean) => {
  if (!enableTables) return undefined;
  
  return ({ children }: { children: React.ReactNode }) => (
    <div className="overflow-x-auto my-4">
      <table className="min-w-full border-collapse border border-gray-300">
        {children}
      </table>
    </div>
  );
};

/**
 * Creates table header component
 */
const createTableHeaderComponent = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <th className="border border-gray-300 bg-gray-50 px-4 py-2 text-left font-semibold">
      {children}
    </th>
  );
};

/**
 * Creates table cell component
 */
const createTableCellComponent = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <td className="border border-gray-300 px-4 py-2">{children}</td>
  );
};

// ============================================================================
// RENDERING STRATEGIES
// ============================================================================

/**
 * Renders content based on configuration
 */
const renderFormattedContent = (
  content: string, 
  config: RendererConfig, 
  components: any, 
  className?: string
) => {
  if (config.enableMarkdown) {
    return renderMarkdownContent(content, config, components, className);
  }
  
  return renderPlainContent(content, className);
};

/**
 * Renders markdown content with plugins
 */
const renderMarkdownContent = (
  content: string, 
  config: RendererConfig, 
  components: any, 
  className?: string
) => {
  const plugins = createMarkdownPlugins(config);
  
  return (
    <ReactMarkdown 
      remarkPlugins={plugins.remark}
      rehypePlugins={plugins.rehype}
      components={components}
      className={`prose prose-sm max-w-none ${className || ''}`}
    >
      {content}
    </ReactMarkdown>
  );
};

/**
 * Creates markdown plugins configuration
 */
const createMarkdownPlugins = (config: RendererConfig) => {
  const remark = [remarkGfm];
  const rehype = [];
  
  if (config.enableMath) {
    remark.push(remarkMath);
    rehype.push(rehypeKatex);
  }
  
  return { remark, rehype };
};

/**
 * Renders plain text content
 */
const renderPlainContent = (content: string, className?: string) => {
  return (
    <div className={`whitespace-pre-wrap text-gray-800 leading-relaxed ${className || ''}`}>
      {content}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

/**
 * Main formatted message content component
 */
export const FormattedMessageContent: React.FC<FormattedMessageContentProps> = React.memo(({
  message,
  className = '',
  enableInteractiveElements = true
}) => {
  const { config, content, isValid } = useMessageProcessing(message);
  const components = useMarkdownComponents(config);
  
  if (!isValid || !content) {
    return renderFallbackContent(message.content, className);
  }
  
  return renderFormattedContent(content, config, components, className);
});

/**
 * Renders fallback content for invalid formatting
 */
const renderFallbackContent = (content: string, className: string) => {
  return (
    <div className={`whitespace-pre-wrap text-gray-800 leading-relaxed ${className}`}>
      {content}
    </div>
  );
};

FormattedMessageContent.displayName = 'FormattedMessageContent';