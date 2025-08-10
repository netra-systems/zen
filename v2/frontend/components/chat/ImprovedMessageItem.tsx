import React, { useState, useCallback } from 'react';
import { Message as MessageType } from '@/types/chat';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { RawJsonView } from './RawJsonView';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  AlertCircle, Bot, ChevronDown, ChevronRight, Clock, Code, FileText, 
  User, Wrench, Copy, Check, ThumbsUp, ThumbsDown, RefreshCw, Edit2, 
  MessageSquare, Sparkles, BrainCircuit
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

interface MessageProps {
  message: MessageType;
  isCompact?: boolean;
  onEdit?: (messageId: string, newContent: string) => void;
  onRegenerate?: (messageId: string) => void;
  onFeedback?: (messageId: string, feedback: 'helpful' | 'not-helpful') => void;
}

export const ImprovedMessageItem: React.FC<MessageProps> = ({ 
  message, 
  isCompact = false,
  onEdit,
  onRegenerate,
  onFeedback
}) => {
  const { type, content, sub_agent_name, tool_info, raw_data, references, error, created_at, id } = message;
  const [isToolExpanded, setIsToolExpanded] = useState(false);
  const [isRawExpanded, setIsRawExpanded] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(content || '');
  const [feedback, setFeedback] = useState<'helpful' | 'not-helpful' | null>(null);

  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) return new Date().toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit'
    });
    
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return new Date().toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit'
    });
    
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric'
    });
  };

  const copyToClipboard = useCallback(async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedCode(id);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

  const handleEdit = () => {
    if (isEditing && onEdit && id) {
      onEdit(id, editContent);
    }
    setIsEditing(!isEditing);
  };

  const handleFeedback = (type: 'helpful' | 'not-helpful') => {
    setFeedback(type);
    if (onFeedback && id) {
      onFeedback(id, type);
    }
  };

  const getMessageIcon = () => {
    switch (type) {
      case 'user':
        return <User className="w-4 h-4" />;
      case 'tool':
        return <Wrench className="w-4 h-4" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        if (sub_agent_name?.includes('optimization')) {
          return <Sparkles className="w-4 h-4" />;
        }
        return <Bot className="w-4 h-4" />;
    }
  };

  const getAgentColor = () => {
    if (type === 'user') return 'from-blue-500 to-blue-600';
    if (type === 'error') return 'from-red-500 to-red-600';
    if (sub_agent_name?.includes('triage')) return 'from-purple-500 to-purple-600';
    if (sub_agent_name?.includes('data')) return 'from-green-500 to-green-600';
    if (sub_agent_name?.includes('optimization')) return 'from-orange-500 to-orange-600';
    if (sub_agent_name?.includes('action')) return 'from-indigo-500 to-indigo-600';
    if (sub_agent_name?.includes('report')) return 'from-pink-500 to-pink-600';
    return 'from-gray-500 to-gray-600';
  };

  const renderContent = () => {
    if (error) {
      return (
        <div className="flex items-start space-x-2 p-3 bg-red-50 rounded-lg border border-red-200">
          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      );
    }
    
    if (tool_info) {
      return (
        <div className="space-y-3">
          <Collapsible open={isToolExpanded} onOpenChange={setIsToolExpanded}>
            <CollapsibleTrigger className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 font-medium text-sm">
              {isToolExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <Code className="w-4 h-4" />
              <span>Tool Information</span>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-3">
              <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                <RawJsonView data={tool_info} />
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      );
    }
    
    if (isEditing && type === 'user') {
      return (
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="w-full p-3 border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
          rows={4}
          autoFocus
        />
      );
    }
    
    return (
      <div className="space-y-3">
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
            components={{
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              code(props: any) {
                const { className, children } = props;
                const match = /language-(\w+)/.exec(className || '');
                const codeString = String(children).replace(/\n$/, '');
                const codeId = `code-${id}-${Math.random()}`;
                const inline = props.inline as boolean | undefined;
                
                return !inline && match ? (
                  <div className="relative group my-3">
                    <div className="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="text-xs text-gray-400 bg-gray-900 px-2 py-1 rounded">
                        {match[1]}
                      </span>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 bg-gray-800 hover:bg-gray-700 text-white"
                        onClick={() => copyToClipboard(codeString, codeId)}
                      >
                        {copiedCode === codeId ? (
                          <Check className="w-3 h-3" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </Button>
                    </div>
                    <SyntaxHighlighter
                      style={oneDark}
                      language={match[1]}
                      PreTag="div"
                      customStyle={{
                        margin: 0,
                        borderRadius: '0.5rem',
                        fontSize: '0.875rem',
                        padding: '1rem',
                      }}
                      {...props}
                    >
                      {codeString}
                    </SyntaxHighlighter>
                  </div>
                ) : (
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                    {children}
                  </code>
                );
              },
              table({ children }) {
                return (
                  <div className="overflow-x-auto my-4">
                    <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
                      {children}
                    </table>
                  </div>
                );
              },
              a({ href, children }) {
                return (
                  <a 
                    href={href} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-700 underline decoration-blue-300 hover:decoration-blue-400"
                  >
                    {children}
                  </a>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
        
        {type === 'user' && references && references.length > 0 && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center space-x-2 mb-2">
              <FileText className="w-4 h-4 text-blue-600" />
              <span className="font-semibold text-sm text-blue-800">References</span>
            </div>
            <ul className="space-y-1">
              {references.map((ref, index) => (
                <li key={`${id}-ref-${index}`} className="text-sm text-blue-700 flex items-start">
                  <span className="mr-2 text-blue-500">•</span>
                  <span>{ref}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  if (isCompact) {
    return (
      <div className={cn(
        "flex gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors",
        type === 'user' ? 'flex-row-reverse' : 'flex-row'
      )}>
        <Avatar className="w-8 h-8 flex-shrink-0">
          <AvatarFallback className={cn("text-xs font-bold bg-gradient-to-r text-white", getAgentColor())}>
            {type === 'user' ? 'U' : sub_agent_name ? sub_agent_name.charAt(0).toUpperCase() : 'AI'}
          </AvatarFallback>
        </Avatar>
        <div className={cn("flex-1", type === 'user' && 'text-right')}>
          <div className="text-xs text-gray-500 mb-1">{formatTimestamp(created_at)}</div>
          <div className="text-sm text-gray-800">{content}</div>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={cn("mb-4 flex", type === 'user' ? 'justify-end' : 'justify-start')}
    >
      <Card className={cn(
        "w-full max-w-3xl shadow-sm hover:shadow-md transition-all duration-200",
        type === 'user' 
          ? 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200' 
          : type === 'error'
          ? 'bg-red-50 border-red-200'
          : 'bg-white border-gray-200 hover:border-gray-300'
      )}>
        <CardHeader className="pb-3 pt-4 px-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <Avatar className="w-9 h-9 border-2 border-white shadow-sm">
                <AvatarFallback className={cn("font-bold text-sm bg-gradient-to-r text-white", getAgentColor())}>
                  {type === 'user' ? 'U' : sub_agent_name ? sub_agent_name.charAt(0).toUpperCase() : 'AI'}
                </AvatarFallback>
              </Avatar>
              <div>
                <div className="flex items-center space-x-2">
                  {getMessageIcon()}
                  <span className="text-base font-semibold text-gray-900">
                    {sub_agent_name || (type === 'user' ? 'You' : 'Netra Agent')}
                  </span>
                </div>
                {type !== 'user' && sub_agent_name && (
                  <p className="text-xs text-gray-500 mt-0.5">
                    {type === 'tool' ? 'Tool Execution' : 'Agent Response'}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Action buttons */}
              <div className="flex items-center gap-1 opacity-0 hover:opacity-100 transition-opacity">
                {type === 'user' && onEdit && (
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7 text-gray-500 hover:text-gray-700"
                    onClick={handleEdit}
                    aria-label={isEditing ? "Save edit" : "Edit message"}
                  >
                    {isEditing ? <Check className="w-3 h-3" /> : <Edit2 className="w-3 h-3" />}
                  </Button>
                )}
                
                {type !== 'user' && type !== 'error' && onRegenerate && (
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7 text-gray-500 hover:text-gray-700"
                    onClick={() => onRegenerate(id!)}
                    aria-label="Regenerate response"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </Button>
                )}
                
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7 text-gray-500 hover:text-gray-700"
                  onClick={() => copyToClipboard(content || '', `msg-${id}`)}
                  aria-label="Copy message"
                >
                  {copiedCode === `msg-${id}` ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </Button>
              </div>
              
              {/* Timestamp */}
              <div className="flex items-center space-x-1 text-xs text-gray-500">
                <Clock className="w-3 h-3" />
                <span>{formatTimestamp(created_at)}</span>
              </div>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="px-5 pb-4">
          {renderContent()}
          
          {/* Feedback buttons for AI messages */}
          {type !== 'user' && type !== 'error' && onFeedback && (
            <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Was this helpful?</span>
                <div className="flex items-center gap-1">
                  <Button
                    size="icon"
                    variant="ghost"
                    className={cn(
                      "h-7 w-7",
                      feedback === 'helpful' 
                        ? "text-green-600 bg-green-50" 
                        : "text-gray-400 hover:text-green-600"
                    )}
                    onClick={() => handleFeedback('helpful')}
                    aria-label="Mark as helpful"
                  >
                    <ThumbsUp className="w-3 h-3" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className={cn(
                      "h-7 w-7",
                      feedback === 'not-helpful' 
                        ? "text-red-600 bg-red-50" 
                        : "text-gray-400 hover:text-red-600"
                    )}
                    onClick={() => handleFeedback('not-helpful')}
                    aria-label="Mark as not helpful"
                  >
                    <ThumbsDown className="w-3 h-3" />
                  </Button>
                </div>
              </div>
              
              {id && (
                <p className="text-xs text-gray-400">ID: {id}</p>
              )}
            </div>
          )}
          
          {raw_data && (
            <Collapsible open={isRawExpanded} onOpenChange={setIsRawExpanded} className="mt-4">
              <CollapsibleTrigger className="flex items-center space-x-2 text-xs text-gray-500 hover:text-gray-700 transition-colors">
                {isRawExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                <Code className="w-3 h-3" />
                <span>Raw Data</span>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2">
                <div className="bg-gray-50 rounded-md p-3 border border-gray-200">
                  <RawJsonView data={raw_data} />
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};