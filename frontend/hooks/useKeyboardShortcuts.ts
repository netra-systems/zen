import { useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useChatStore } from '@/store/chat';
import { useThreadStore } from '@/store/threadStore';

interface ShortcutHandler {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  handler: () => void;
  description: string;
}

export const useKeyboardShortcuts = () => {
  const router = useRouter();
  const { messages, isProcessing, setProcessing } = useChatStore();
  const { threads, currentThreadId, setCurrentThread } = useThreadStore();
  const isSearchOpen = useRef(false);
  const messageInputRef = useRef<HTMLTextAreaElement | null>(null);

  // Register message input ref
  const setMessageInputRef = useCallback((ref: HTMLTextAreaElement | null) => {
    messageInputRef.current = ref;
  }, []);

  // Focus message input
  const focusMessageInput = useCallback(() => {
    if (messageInputRef.current) {
      messageInputRef.current.focus();
    } else {
      // Fallback to finding the textarea
      const textarea = document.querySelector('textarea[aria-label="Message input"]') as HTMLTextAreaElement;
      if (textarea) {
        textarea.focus();
      }
    }
  }, []);

  // Navigate to previous/next thread
  const navigateThread = useCallback((direction: 'prev' | 'next') => {
    if (!threads.length) return;
    
    const currentIndex = threads.findIndex(t => t.id === currentThreadId);
    let newIndex: number;
    
    if (direction === 'prev') {
      newIndex = currentIndex > 0 ? currentIndex - 1 : threads.length - 1;
    } else {
      newIndex = currentIndex < threads.length - 1 ? currentIndex + 1 : 0;
    }
    
    setCurrentThread(threads[newIndex].id);
  }, [threads, currentThreadId, setCurrentThread]);

  // Scroll to top/bottom of messages
  const scrollMessages = useCallback((position: 'top' | 'bottom') => {
    const scrollArea = document.querySelector('[data-radix-scroll-area-viewport]');
    if (scrollArea) {
      if (position === 'top') {
        scrollArea.scrollTop = 0;
      } else {
        scrollArea.scrollTop = scrollArea.scrollHeight;
      }
    }
  }, []);

  // Toggle compact mode
  const toggleCompactMode = useCallback(() => {
    const currentMode = localStorage.getItem('chatCompactMode') === 'true';
    localStorage.setItem('chatCompactMode', (!currentMode).toString());
    window.dispatchEvent(new CustomEvent('compactModeChanged', { detail: !currentMode }));
  }, []);

  // Toggle sidebar
  const toggleSidebar = useCallback(() => {
    const sidebar = document.querySelector('[data-sidebar]');
    if (sidebar) {
      sidebar.classList.toggle('hidden');
    }
  }, []);

  // Open command palette
  const openCommandPalette = useCallback(() => {
    const event = new CustomEvent('openCommandPalette');
    window.dispatchEvent(event);
  }, []);

  // Copy last message
  const copyLastMessage = useCallback(() => {
    const displayedMessages = messages.filter(m => m.displayed_to_user);
    if (displayedMessages.length > 0) {
      const lastMessage = displayedMessages[displayedMessages.length - 1];
      if (lastMessage.content) {
        navigator.clipboard.writeText(lastMessage.content);
        // Show toast notification
        const event = new CustomEvent('showToast', { 
          detail: { message: 'Message copied to clipboard', type: 'success' } 
        });
        window.dispatchEvent(event);
      }
    }
  }, [messages]);

  // Define shortcuts
  const shortcuts: ShortcutHandler[] = [
    // Navigation
    { key: 'k', ctrl: true, handler: openCommandPalette, description: 'Open command palette' },
    { key: 'b', ctrl: true, handler: toggleSidebar, description: 'Toggle sidebar' },
    { key: 'ArrowLeft', alt: true, handler: () => navigateThread('prev'), description: 'Previous thread' },
    { key: 'ArrowRight', alt: true, handler: () => navigateThread('next'), description: 'Next thread' },
    
    // Message control
    { key: 'Escape', handler: () => isProcessing && setProcessing(false), description: 'Stop processing' },
    { key: '/', handler: focusMessageInput, description: 'Focus message input' },
    { key: 'c', ctrl: true, shift: true, handler: copyLastMessage, description: 'Copy last message' },
    
    // View control
    { key: 'g', handler: () => scrollMessages('top'), description: 'Go to first message' },
    { key: 'G', shift: true, handler: () => scrollMessages('bottom'), description: 'Go to last message' },
    { key: 'm', ctrl: true, shift: true, handler: toggleCompactMode, description: 'Toggle compact mode' },
    
    // Thread management
    { key: 'n', ctrl: true, handler: () => router.push('/chat'), description: 'New thread' },
    { key: 'd', ctrl: true, handler: () => {
      const event = new CustomEvent('deleteCurrentThread');
      window.dispatchEvent(event);
    }, description: 'Delete current thread' },
    
    // Debug panel
    { key: 'd', ctrl: true, shift: true, handler: () => {
      const event = new CustomEvent('toggleDebugPanel');
      window.dispatchEvent(event);
    }, description: 'Toggle debug panel' },
  ];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in input fields
      const target = e.target as HTMLElement;
      const isInputField = ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
      const isEditable = target.contentEditable === 'true';
      
      // Allow some shortcuts even in input fields
      const allowedInInput = ['Escape', 'k'];
      
      if (isInputField || isEditable) {
        if (!allowedInInput.includes(e.key)) {
          // Special case: Allow / shortcut only when not in input
          if (e.key === '/' && !isInputField && !isEditable) {
            e.preventDefault();
            focusMessageInput();
          }
          return;
        }
      }

      // Check each shortcut
      for (const shortcut of shortcuts) {
        const ctrlMatch = shortcut.ctrl ? (e.ctrlKey || e.metaKey) : !(e.ctrlKey || e.metaKey);
        const shiftMatch = shortcut.shift ? e.shiftKey : !e.shiftKey;
        const altMatch = shortcut.alt ? e.altKey : !e.altKey;
        
        if (
          e.key === shortcut.key &&
          ctrlMatch &&
          shiftMatch &&
          altMatch
        ) {
          e.preventDefault();
          shortcut.handler();
          break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts, focusMessageInput, isProcessing]);

  return {
    shortcuts,
    setMessageInputRef,
    focusMessageInput,
  };
};

// Export shortcut descriptions for help menu
export const getShortcutDescriptions = (): Record<string, string> => ({
  'Cmd/Ctrl + K': 'Open command palette',
  'Cmd/Ctrl + B': 'Toggle sidebar',
  'Cmd/Ctrl + N': 'New thread',
  'Cmd/Ctrl + D': 'Delete current thread',
  'Cmd/Ctrl + Shift + C': 'Copy last message',
  'Cmd/Ctrl + Shift + D': 'Toggle debug panel',
  'Cmd/Ctrl + Shift + M': 'Toggle compact mode',
  'Alt + ←': 'Previous thread',
  'Alt + →': 'Next thread',
  '/': 'Focus message input',
  'Esc': 'Stop processing',
  'G G': 'Go to first message',
  'Shift + G': 'Go to last message',
});