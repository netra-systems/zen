import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { Send, Paperclip, Mic, Command, ArrowUp, ArrowDown, Loader2 } from 'lucide-react';
import { Message } from '@/types/chat';
import { ThreadService } from '@/services/threadService';
import { motion, AnimatePresence } from 'framer-motion';
import { cn, generateUniqueId } from '@/lib/utils';

export const MessageInput: React.FC = () => {
  const [message, setMessage] = useState('');
  const [rows, setRows] = useState(1);
  const [isSending, setIsSending] = useState(false);
  const [messageHistory, setMessageHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { sendMessage } = useWebSocket();
  const { setProcessing, isProcessing, addMessage } = useChatStore();
  const { currentThreadId, setCurrentThread, addThread } = useThreadStore();
  const { isAuthenticated } = useAuthStore();
  
  const MAX_ROWS = 5;
  const CHAR_LIMIT = 10000;

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      const lineHeight = 24; // Approximate line height
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

  const handleSend = async () => {
    // Check if user is authenticated
    if (!isAuthenticated) {
      console.error('User must be authenticated to send messages');
      return;
    }
    
    const trimmedMessage = message.trim();
    if (trimmedMessage && !isSending && trimmedMessage.length <= CHAR_LIMIT) {
      setIsSending(true);
      
      // Add to message history
      setMessageHistory(prev => [...prev, trimmedMessage]);
      setHistoryIndex(-1);
      
      let threadId = currentThreadId;
      
      // Create a new thread if none exists
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
      
      // Add user message to chat immediately
      const userMessage: Message = {
        id: generateUniqueId('msg'),
        type: 'user',
        content: trimmedMessage,
        created_at: new Date().toISOString(),
        displayed_to_user: true
      };
      addMessage(userMessage);
      
      // Send message via WebSocket with thread_id
      sendMessage({ 
        type: 'user_message', 
        payload: { 
          text: trimmedMessage, 
          references: [],
          thread_id: threadId 
        } 
      });
      setProcessing(true);
      setMessage('');
      setRows(1);
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send message on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    
    // Navigate message history with arrow keys when input is empty
    if (message === '') {
      if (e.key === 'ArrowUp' && messageHistory.length > 0) {
        e.preventDefault();
        const newIndex = historyIndex === -1 
          ? messageHistory.length - 1 
          : Math.max(0, historyIndex - 1);
        setHistoryIndex(newIndex);
        setMessage(messageHistory[newIndex]);
      } else if (e.key === 'ArrowDown' && historyIndex !== -1) {
        e.preventDefault();
        const newIndex = Math.min(messageHistory.length - 1, historyIndex + 1);
        if (newIndex === messageHistory.length - 1) {
          setHistoryIndex(-1);
          setMessage('');
        } else {
          setHistoryIndex(newIndex);
          setMessage(messageHistory[newIndex]);
        }
      }
    }
  };

  const getPlaceholder = () => {
    if (!isAuthenticated) return 'Please sign in to send messages';
    if (isProcessing) return 'Agent is thinking...';
    if (message.length > CHAR_LIMIT * 0.9) return `${CHAR_LIMIT - message.length} characters remaining`;
    return 'Type a message... (Shift+Enter for new line)';
  };

  const isDisabled = isProcessing || !isAuthenticated || isSending;

  return (
    <div className="relative w-full">
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={getPlaceholder()}
            rows={rows}
            disabled={isDisabled}
            className={cn(
              "w-full resize-none rounded-2xl px-4 py-3 pr-12",
              "bg-gray-50 border border-gray-200",
              "focus:bg-white focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100",
              "transition-all duration-200 ease-in-out",
              "placeholder:text-gray-400 text-gray-900",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              message.length > CHAR_LIMIT * 0.9 && "border-orange-400 focus:ring-orange-100",
              message.length > CHAR_LIMIT && "border-red-400 focus:ring-red-100"
            )}
            style={{
              minHeight: '48px',
              maxHeight: `${MAX_ROWS * 24 + 24}px`,
              lineHeight: '24px'
            }}
            aria-label="Message input"
            aria-describedby="char-count"
          />
          
          {/* Character count indicator */}
          {message.length > CHAR_LIMIT * 0.8 && (
            <div 
              id="char-count"
              className={cn(
                "absolute bottom-2 right-2 text-xs font-medium",
                message.length > CHAR_LIMIT ? "text-red-500" : 
                message.length > CHAR_LIMIT * 0.9 ? "text-orange-500" : "text-gray-400"
              )}
            >
              {message.length}/{CHAR_LIMIT}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          {/* File attachment button */}
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full w-10 h-10 text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              disabled={isDisabled}
              aria-label="Attach file"
              title="Attach file (coming soon)"
            >
              <Paperclip className="w-5 h-5" />
            </Button>
          </motion.div>

          {/* Voice input button */}
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full w-10 h-10 text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              disabled={isDisabled}
              aria-label="Voice input"
              title="Voice input (coming soon)"
            >
              <Mic className="w-5 h-5" />
            </Button>
          </motion.div>

          {/* Send button */}
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              onClick={handleSend}
              disabled={isDisabled || !message.trim() || message.length > CHAR_LIMIT}
              className={cn(
                "rounded-full w-12 h-12 flex items-center justify-center transition-all duration-200",
                "bg-emerald-500 hover:bg-emerald-600",
                "text-white shadow-lg hover:shadow-xl",
                "disabled:from-gray-300 disabled:to-gray-400 disabled:shadow-none"
              )}
              aria-label="Send message"
            >
              <AnimatePresence mode="wait">
                {isSending ? (
                  <motion.div
                    key="sending"
                    initial={{ opacity: 0, rotate: 0 }}
                    animate={{ opacity: 1, rotate: 360 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3, rotate: { duration: 1, repeat: Infinity, ease: "linear" } }}
                  >
                    <Loader2 className="w-5 h-5" />
                  </motion.div>
                ) : (
                  <motion.div
                    key="send"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Send className="w-5 h-5" />
                  </motion.div>
                )}
              </AnimatePresence>
            </Button>
          </motion.div>
        </div>
      </div>

      {/* Keyboard shortcuts hint */}
      <AnimatePresence>
        {isAuthenticated && !message && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="absolute -top-8 left-0 flex items-center gap-4 text-xs text-gray-400"
          >
            <span className="flex items-center gap-1">
              <Command className="w-3 h-3" />
              <span>+ K for search</span>
            </span>
            <span className="flex items-center gap-1">
              <ArrowUp className="w-3 h-3" />
              <ArrowDown className="w-3 h-3" />
              <span>for history</span>
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};