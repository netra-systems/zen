import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { Send, Paperclip, Mic, Command, Loader2, Database, Sparkles, Users, Settings, FileText, Shield } from 'lucide-react';
import { Message } from '@/types/chat';
import { ThreadService } from '@/services/threadService';
import { motion, AnimatePresence } from 'framer-motion';
import { cn, generateUniqueId } from '@/lib/utils';

interface AdminCommand {
  command: string;
  description: string;
  icon: React.ReactNode;
  category: 'corpus' | 'synthetic' | 'users' | 'config' | 'logs';
  template?: string;
}

interface AdminTemplate {
  name: string;
  category: string;
  template: string;
  icon: React.ReactNode;
}

const ADMIN_COMMANDS: AdminCommand[] = [
  {
    command: '/corpus',
    description: 'Corpus management commands',
    icon: <Database className="w-4 h-4" />,
    category: 'corpus',
    template: 'Create a corpus for '
  },
  {
    command: '/synthetic',
    description: 'Synthetic data generation',
    icon: <Sparkles className="w-4 h-4" />,
    category: 'synthetic',
    template: 'Generate synthetic data with '
  },
  {
    command: '/users',
    description: 'User management commands',
    icon: <Users className="w-4 h-4" />,
    category: 'users',
    template: 'List all users with role '
  },
  {
    command: '/config',
    description: 'System configuration',
    icon: <Settings className="w-4 h-4" />,
    category: 'config',
    template: 'Update system setting '
  },
  {
    command: '/logs',
    description: 'Log analysis commands',
    icon: <FileText className="w-4 h-4" />,
    category: 'logs',
    template: 'Show logs from the last '
  }
];

const ADMIN_TEMPLATES: AdminTemplate[] = [
  {
    name: 'Create Financial Corpus',
    category: 'corpus',
    icon: <Database className="w-3 h-3" />,
    template: `Create a corpus for financial services with examples for:
- Market data analysis
- Risk assessment
- Portfolio optimization
- Compliance checking`
  },
  {
    name: 'Generate Test Data',
    category: 'synthetic',
    icon: <Sparkles className="w-3 h-3" />,
    template: `Generate 10,000 synthetic optimization requests with:
- 70% successful optimizations
- 20% partial optimizations
- 10% failed requests
- Realistic latency distribution`
  },
  {
    name: 'User Access Audit',
    category: 'users',
    icon: <Users className="w-3 h-3" />,
    template: `Show me all admin actions performed in the last 7 days, 
grouped by user and sorted by frequency`
  },
  {
    name: 'E-Commerce Load Test',
    category: 'synthetic',
    icon: <Sparkles className="w-3 h-3" />,
    template: `Generate Black Friday e-commerce workload pattern:
- 500,000 requests over 24 hours
- Peak traffic between 6 AM and 2 PM
- 30% cart abandonment rate
- Realistic geographic distribution`
  }
];

export const MessageInputWithCommands: React.FC = () => {
  const [message, setMessage] = useState('');
  const [rows, setRows] = useState(1);
  const [isSending, setIsSending] = useState(false);
  const [messageHistory, setMessageHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);
  const [filteredCommands, setFilteredCommands] = useState<AdminCommand[]>([]);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { sendMessage } = useWebSocket();
  const { setProcessing, isProcessing, addMessage } = useUnifiedChatStore();
  const { currentThreadId, setCurrentThread, addThread } = useThreadStore();
  const { isAuthenticated, isDeveloperOrHigher } = useAuthStore();
  
  const isAdmin = isDeveloperOrHigher();
  const MAX_ROWS = 5;
  const CHAR_LIMIT = 10000;

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      const lineHeight = 24;
      const newRows = Math.min(Math.ceil(scrollHeight / lineHeight), MAX_ROWS);
      setRows(newRows);
      textareaRef.current.style.height = `${scrollHeight}px`;
    }
  }, [message]);

  // Focus input on mount
  useEffect(() => {
    if (textareaRef.current && isAuthenticated) {
      textareaRef.current.focus();
    }
  }, [isAuthenticated]);

  // Handle command palette visibility
  useEffect(() => {
    if (isAdmin && message.startsWith('/')) {
      const query = message.slice(1).toLowerCase();
      const filtered = ADMIN_COMMANDS.filter(cmd => 
        cmd.command.toLowerCase().includes(query) || 
        cmd.description.toLowerCase().includes(query)
      );
      setFilteredCommands(filtered);
      setShowCommandPalette(filtered.length > 0);
      setSelectedCommandIndex(0);
    } else {
      setShowCommandPalette(false);
    }
  }, [message, isAdmin]);

  const handleSend = async () => {
    if (!isAuthenticated) {
      console.error('User must be authenticated to send messages');
      return;
    }
    
    const trimmedMessage = message.trim();
    if (trimmedMessage && !isSending && trimmedMessage.length <= CHAR_LIMIT) {
      setIsSending(true);
      
      setMessageHistory(prev => [...prev, trimmedMessage]);
      setHistoryIndex(-1);
      
      let threadId = currentThreadId;
      
      if (!threadId) {
        try {
          const newThread = await ThreadService.createThread(
            trimmedMessage.substring(0, 50) + (trimmedMessage.length > 50 ? '...' : '')
          );
          addThread(newThread);
          setCurrentThread(newThread.id);
          threadId = newThread.id;
        } catch (error) {
          console.error('Failed to create thread:', error);
          setIsSending(false);
          return;
        }
      }
      
      const userMessage: Message = {
        id: generateUniqueId('msg'),
        type: 'user',
        content: trimmedMessage,
        created_at: new Date().toISOString(),
        displayed_to_user: true
      };
      addMessage(userMessage);
      
      sendMessage({ 
        type: 'user_message', 
        payload: { 
          text: trimmedMessage, 
          references: [],
          thread_id: threadId,
          admin_context: isAdmin && trimmedMessage.startsWith('/') ? true : undefined
        } 
      });
      setProcessing(true);
      setMessage('');
      setRows(1);
      setShowCommandPalette(false);
      setShowTemplates(false);
      
      setTimeout(() => {
        setIsSending(false);
      }, 100);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Command palette navigation
    if (showCommandPalette) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedCommandIndex((prev) => 
          Math.min(prev + 1, filteredCommands.length - 1)
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedCommandIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Tab' || e.key === 'Enter') {
        if (filteredCommands[selectedCommandIndex]) {
          e.preventDefault();
          const cmd = filteredCommands[selectedCommandIndex];
          setMessage(cmd.template || cmd.command + ' ');
          setShowCommandPalette(false);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        setShowCommandPalette(false);
      }
      return;
    }

    // Message history navigation
    if (e.key === 'ArrowUp' && !message) {
      e.preventDefault();
      if (messageHistory.length > 0) {
        const newIndex = historyIndex === -1 
          ? messageHistory.length - 1 
          : Math.max(0, historyIndex - 1);
        setHistoryIndex(newIndex);
        setMessage(messageHistory[newIndex]);
      }
    } else if (e.key === 'ArrowDown' && historyIndex !== -1) {
      e.preventDefault();
      if (historyIndex < messageHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setMessage(messageHistory[newIndex]);
      } else {
        setHistoryIndex(-1);
        setMessage('');
      }
    } else if (e.key === 'Enter' && !e.shiftKey && !isProcessing) {
      e.preventDefault();
      handleSend();
    }
  };

  const insertTemplate = (template: string) => {
    setMessage(template);
    setShowTemplates(false);
    textareaRef.current?.focus();
  };

  const isDisabled = !isAuthenticated || isProcessing || isSending || !message.trim() || message.length > CHAR_LIMIT;

  return (
    <div className="relative">
      {/* Command Palette */}
      <AnimatePresence>
        {showCommandPalette && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute bottom-full mb-2 left-0 right-0 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden"
          >
            <div className="p-2">
              <div className="flex items-center space-x-2 px-2 py-1 text-xs text-gray-500">
                <Command className="w-3 h-3" />
                <span>Admin Commands</span>
              </div>
              {filteredCommands.map((cmd, index) => (
                <button
                  key={cmd.command}
                  className={cn(
                    "w-full flex items-center space-x-3 px-3 py-2 rounded-md text-left transition-colors",
                    index === selectedCommandIndex
                      ? "bg-purple-100 text-purple-900"
                      : "hover:bg-gray-50 text-gray-700"
                  )}
                  onMouseEnter={() => setSelectedCommandIndex(index)}
                  onClick={() => insertTemplate(cmd.template || cmd.command + ' ')}
                >
                  {cmd.icon}
                  <div className="flex-1">
                    <p className="text-sm font-medium">{cmd.command}</p>
                    <p className="text-xs text-gray-500">{cmd.description}</p>
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Template Panel */}
      <AnimatePresence>
        {showTemplates && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute bottom-full mb-2 left-0 right-0 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden max-h-64 overflow-y-auto"
          >
            <div className="p-2">
              <div className="flex items-center space-x-2 px-2 py-1 text-xs text-gray-500 mb-1">
                <FileText className="w-3 h-3" />
                <span>Admin Templates</span>
              </div>
              {ADMIN_TEMPLATES.map((tpl) => (
                <button
                  key={tpl.name}
                  className="w-full text-left px-3 py-2 rounded-md hover:bg-purple-50 transition-colors group"
                  onClick={() => insertTemplate(tpl.template)}
                >
                  <div className="flex items-start space-x-2">
                    <div className="mt-0.5 text-purple-600">{tpl.icon}</div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 group-hover:text-purple-900">
                        {tpl.name}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                        {tpl.template.split('\n')[0]}...
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-end space-x-2 p-4 bg-white/95 backdrop-blur-sm border-t border-gray-200">
        {/* Admin Indicator */}
        {isAdmin && (
          <div className="flex items-center space-x-2 px-3 py-2 bg-purple-50 rounded-lg border border-purple-200">
            <Shield className="w-4 h-4 text-purple-600" />
            <span className="text-xs font-medium text-purple-700">Admin Mode</span>
          </div>
        )}

        {/* Template Button for Admins */}
        {isAdmin && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowTemplates(!showTemplates)}
            className="text-purple-600 border-purple-200 hover:bg-purple-50"
          >
            <FileText className="w-4 h-4" />
          </Button>
        )}

        {/* Main Input Area */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isAdmin 
                ? "Type '/' for commands or message..." 
                : isAuthenticated 
                  ? "Type your message..." 
                  : "Please sign in to send messages"
            }
            rows={rows}
            disabled={!isAuthenticated || isProcessing}
            className={cn(
              "w-full px-4 py-3 pr-12 bg-gray-50 border border-gray-200 rounded-lg",
              "resize-none overflow-y-auto transition-all duration-200",
              "focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "placeholder:text-gray-400"
            )}
            style={{ maxHeight: `${MAX_ROWS * 24}px` }}
          />
          
          {/* Character Count */}
          {message.length > CHAR_LIMIT * 0.9 && (
            <div className={cn(
              "absolute bottom-2 right-12 text-xs",
              message.length > CHAR_LIMIT ? "text-red-500" : "text-amber-500"
            )}>
              {message.length}/{CHAR_LIMIT}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="icon"
            disabled={!isAuthenticated}
            className="text-gray-500 hover:text-gray-700"
          >
            <Paperclip className="w-4 h-4" />
          </Button>
          
          <Button
            variant="outline"
            size="icon"
            disabled={!isAuthenticated}
            className="text-gray-500 hover:text-gray-700"
          >
            <Mic className="w-4 h-4" />
          </Button>
          
          <Button
            onClick={handleSend}
            disabled={isDisabled}
            className={cn(
              "bg-emerald-500 hover:bg-emerald-600 text-white",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-all duration-200"
            )}
          >
            {isSending || isProcessing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};