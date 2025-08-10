"use client";

import React, { useState, useEffect } from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { StopButton } from '@/components/chat/StopButton';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { ThreadSidebar } from '@/components/chat/ThreadSidebar';
import { useChatStore } from '@/store/chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Menu, X, MessageSquarePlus, Command } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useMediaQuery } from '@/hooks/useMediaQuery';

const ResponsiveMainChat: React.FC = () => {
  const { isProcessing, messages } = useChatStore();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isCompactMode, setIsCompactMode] = useState(false);
  const isMobile = useMediaQuery('(max-width: 640px)');
  const isTablet = useMediaQuery('(max-width: 1024px)');
  
  // Connect WebSocket messages to chat store
  useChatWebSocket();
  
  // Initialize keyboard shortcuts
  const { setMessageInputRef } = useKeyboardShortcuts();

  const hasMessages = messages.filter(m => m.displayed_to_user).length > 0;

  // Load compact mode preference
  useEffect(() => {
    const savedMode = localStorage.getItem('chatCompactMode') === 'true';
    setIsCompactMode(savedMode);
    
    const handleCompactModeChange = (e: CustomEvent) => {
      setIsCompactMode(e.detail);
    };
    
    window.addEventListener('compactModeChanged', handleCompactModeChange as EventListener);
    return () => window.removeEventListener('compactModeChanged', handleCompactModeChange as EventListener);
  }, []);

  // Auto-close sidebar on mobile when route changes
  useEffect(() => {
    if (isMobile) {
      setIsSidebarOpen(false);
    }
  }, [isMobile]);

  // Handle swipe gestures on mobile
  useEffect(() => {
    if (!isMobile) return;
    
    let touchStartX = 0;
    let touchEndX = 0;
    
    const handleTouchStart = (e: TouchEvent) => {
      touchStartX = e.changedTouches[0].screenX;
    };
    
    const handleTouchEnd = (e: TouchEvent) => {
      touchEndX = e.changedTouches[0].screenX;
      handleSwipe();
    };
    
    const handleSwipe = () => {
      const swipeThreshold = 75;
      const diff = touchEndX - touchStartX;
      
      if (Math.abs(diff) > swipeThreshold) {
        if (diff > 0 && touchStartX < 50) {
          // Swipe right from left edge - open sidebar
          setIsSidebarOpen(true);
        } else if (diff < 0 && isSidebarOpen) {
          // Swipe left - close sidebar
          setIsSidebarOpen(false);
        }
      }
    };
    
    document.addEventListener('touchstart', handleTouchStart);
    document.addEventListener('touchend', handleTouchEnd);
    
    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [isMobile, isSidebarOpen]);

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 relative">
      {/* Mobile overlay */}
      <AnimatePresence>
        {isSidebarOpen && isTablet && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.div
        initial={false}
        animate={{
          x: isTablet ? (isSidebarOpen ? 0 : -320) : 0,
        }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className={cn(
          "fixed lg:relative z-50 lg:z-auto",
          "w-80 lg:w-64 xl:w-80",
          "h-full bg-white border-r border-gray-200 shadow-xl lg:shadow-none",
          isTablet && !isSidebarOpen && "pointer-events-none"
        )}
        data-sidebar
      >
        <ThreadSidebar />
        {isTablet && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-4 right-4 lg:hidden"
            onClick={() => setIsSidebarOpen(false)}
          >
            <X className="w-5 h-5" />
          </Button>
        )}
      </motion.div>

      {/* Main chat area */}
      <div className="flex flex-col flex-1 max-w-full relative">
        {/* Header */}
        <div className="border-b bg-white/95 backdrop-blur-sm shadow-sm relative z-30">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-2">
              {isTablet && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                  className="lg:hidden"
                  aria-label="Toggle sidebar"
                >
                  <Menu className="w-5 h-5" />
                </Button>
              )}
              <ChatHeader />
            </div>
            
            <div className="flex items-center gap-2">
              {!isMobile && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const event = new CustomEvent('openCommandPalette');
                      window.dispatchEvent(event);
                    }}
                    className="hidden sm:flex items-center gap-2 text-xs"
                  >
                    <Command className="w-3 h-3" />
                    <span>Cmd K</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsCompactMode(!isCompactMode)}
                    className="hidden sm:block"
                  >
                    {isCompactMode ? 'Detailed' : 'Compact'}
                  </Button>
                </>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => window.location.href = '/chat'}
                aria-label="New chat"
              >
                <MessageSquarePlus className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
        
        {/* Messages area */}
        <div className="flex-grow overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/50 pointer-events-none z-10" />
          
          <div className={cn(
            "h-full overflow-y-auto",
            isMobile && "pb-safe" // Account for iOS safe area
          )}>
            <AnimatePresence mode="wait">
              {!hasMessages && (
                <motion.div
                  initial={{ opacity: 1 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className={cn(
                    "px-4",
                    isMobile && "pt-8"
                  )}
                >
                  <ExamplePrompts />
                </motion.div>
              )}
            </AnimatePresence>
            
            <div className={cn(
              "px-2 sm:px-4 lg:px-6",
              isCompactMode && "max-w-4xl mx-auto"
            )}>
              <MessageList />
            </div>
          </div>
        </div>
        
        {/* Input area */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={cn(
            "border-t bg-white/95 backdrop-blur-sm shadow-lg",
            isMobile && "pb-safe sticky bottom-0" // iOS safe area
          )}
        >
          <div className={cn(
            "px-4 py-3 sm:py-4",
            "max-w-5xl mx-auto w-full"
          )}>
            <div className="space-y-3">
              <MessageInput />
              
              {isProcessing && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className="flex justify-center"
                >
                  <StopButton />
                </motion.div>
              )}
            </div>
            
            {/* Mobile keyboard shortcuts hint */}
            {isMobile && (
              <div className="mt-2 flex items-center justify-center gap-4 text-xs text-gray-400">
                <button
                  onClick={() => setIsSidebarOpen(true)}
                  className="flex items-center gap-1"
                >
                  <Menu className="w-3 h-3" />
                  <span>Threads</span>
                </button>
                <button
                  onClick={() => setIsCompactMode(!isCompactMode)}
                  className="flex items-center gap-1"
                >
                  <span>{isCompactMode ? 'Detailed View' : 'Compact View'}</span>
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </div>
      
      {/* Floating action button on mobile */}
      {isMobile && hasMessages && (
        <motion.button
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0 }}
          transition={{ type: 'spring', stiffness: 260, damping: 20 }}
          className="fixed bottom-24 right-4 w-12 h-12 bg-blue-500 text-white rounded-full shadow-lg flex items-center justify-center z-40"
          onClick={() => {
            const scrollArea = document.querySelector('[data-radix-scroll-area-viewport]');
            if (scrollArea) {
              scrollArea.scrollTop = scrollArea.scrollHeight;
            }
          }}
          aria-label="Scroll to bottom"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </motion.button>
      )}
    </div>
  );
};

export default ResponsiveMainChat;