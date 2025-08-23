// Thread management store - Focused on thread operations
// Clean separation of concerns from layer management

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { generateUniqueId } from '@/lib/utils';
import type { ChatMessage } from '@/types/unified';

// ============================================
// Thread Store State
// ============================================

interface ThreadStoreState {
  // Thread state
  activeThreadId: string | null;
  threads: Map<string, unknown>;
  isThreadLoading: boolean;
  
  // Message history
  messages: ChatMessage[];
  
  // Thread actions
  setActiveThread: (threadId: string | null) => void;
  setThreadLoading: (isLoading: boolean) => void;
  startThreadLoading: (threadId: string) => void;
  completeThreadLoading: (threadId: string, messages: ChatMessage[]) => void;
  
  // Message actions
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  loadMessages: (messages: ChatMessage[]) => void;
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void;
  
  // Thread event handlers
  handleThreadCreated: (threadId: string, userId: string) => void;
  handleThreadRenamed: (threadId: string, newTitle: string) => void;
  handleThreadDeleted: (threadId: string) => void;
  handleThreadSwitched: (fromThreadId: string | undefined, toThreadId: string) => void;
}

// ============================================
// Thread Store Implementation
// ============================================

export const useThreadStore = create<ThreadStoreState>()(devtools(
  (set, get) => ({
    // Initial state
    activeThreadId: null,
    threads: new Map(),
    isThreadLoading: false,
    messages: [],
    
    // Thread management
    setActiveThread: (threadId) => {
      set({ activeThreadId: threadId });
    },
    
    setThreadLoading: (isLoading) => {
      set({ isThreadLoading: isLoading });
    },
    
    startThreadLoading: (threadId) => {
      set({
        activeThreadId: threadId,
        isThreadLoading: true,
        messages: []
      });
    },
    
    completeThreadLoading: (threadId, messages) => {
      set({
        activeThreadId: threadId,
        isThreadLoading: false,
        messages: formatMessages(messages)
      });
    },
    
    // Message management
    addMessage: (message) => {
      set((state) => ({
        messages: [...state.messages, message]
      }));
    },
    
    clearMessages: () => {
      set({ messages: [] });
    },
    
    loadMessages: (messages) => {
      set({ messages: formatMessages(messages), isThreadLoading: false });
    },
    
    updateMessage: (messageId, updates) => {
      set((state) => ({
        messages: updateMessageInList(state.messages, messageId, updates)
      }));
    },
    
    // Thread event handlers
    handleThreadCreated: (threadId, userId) => {
      handleThreadCreatedEvent(threadId, userId, set);
    },
    
    handleThreadRenamed: (threadId, newTitle) => {
      handleThreadRenamedEvent(threadId, newTitle, get, set);
    },
    
    handleThreadDeleted: (threadId) => {
      handleThreadDeletedEvent(threadId, get, set);
    },
    
    handleThreadSwitched: (fromThreadId, toThreadId) => {
      handleThreadSwitchedEvent(fromThreadId, toThreadId, set);
    }
  }),
  { name: 'thread-store' }
));

// ============================================
// Message Utilities
// ============================================

const formatMessages = (messages: ChatMessage[]): ChatMessage[] => {
  return messages.map(formatSingleMessage);
};

const formatSingleMessage = (msg: any): ChatMessage => {
  return {
    id: msg.id || generateUniqueId('msg'),
    role: determineChatMessageRole(msg.role),
    content: msg.content || '',
    timestamp: normalizeTimestamp(msg.timestamp, msg.created_at),
    threadId: msg.threadId,
    threadTitle: msg.threadTitle,
    metadata: msg.metadata
  };
};

const determineChatMessageRole = (role: string): 'user' | 'assistant' | 'system' => {
  if (role === 'user') return 'user';
  if (role === 'system') return 'system';
  return 'assistant';
};

const normalizeTimestamp = (timestamp?: number, createdAt?: number): number => {
  if (typeof timestamp === 'number') return timestamp;
  if (typeof createdAt === 'number') return createdAt > 9999999999 ? createdAt : createdAt * 1000;
  return Date.now();
};

const updateMessageInList = (
  messages: ChatMessage[],
  messageId: string,
  updates: Partial<ChatMessage>
): ChatMessage[] => {
  return messages.map(msg => 
    msg.id === messageId ? { ...msg, ...updates } : msg
  );
};

// ============================================
// Thread Event Handlers
// ============================================

const handleThreadCreatedEvent = (
  threadId: string,
  userId: string,
  set: (partial: Partial<ThreadStoreState>) => void
): void => {
  // Handle thread creation logic
  set({ activeThreadId: threadId });
};

const handleThreadRenamedEvent = (
  threadId: string,
  newTitle: string,
  get: () => ThreadStoreState,
  set: (partial: Partial<ThreadStoreState>) => void
): void => {
  const state = get();
  const updatedMessages = updateMessagesWithThreadTitle(state.messages, threadId, newTitle);
  set({ messages: updatedMessages });
};

const updateMessagesWithThreadTitle = (
  messages: ChatMessage[],
  threadId: string,
  newTitle: string
): ChatMessage[] => {
  return messages.map(msg => 
    msg.threadId === threadId ? { ...msg, threadTitle: newTitle } : msg
  );
};

const handleThreadDeletedEvent = (
  threadId: string,
  get: () => ThreadStoreState,
  set: (partial: Partial<ThreadStoreState>) => void
): void => {
  const state = get();
  if (state.activeThreadId === threadId) {
    set({ activeThreadId: null, messages: [] });
  }
};

const handleThreadSwitchedEvent = (
  fromThreadId: string | undefined,
  toThreadId: string,
  set: (partial: Partial<ThreadStoreState>) => void
): void => {
  set({
    activeThreadId: toThreadId,
    isThreadLoading: true,
    messages: []
  });
};

// ============================================
// Thread Store Selectors
// ============================================

export const threadStoreSelectors = {
  activeThreadId: (state: ThreadStoreState) => state.activeThreadId,
  isThreadLoading: (state: ThreadStoreState) => state.isThreadLoading,
  messages: (state: ThreadStoreState) => state.messages,
  messageCount: (state: ThreadStoreState) => state.messages.length,
  latestMessage: (state: ThreadStoreState) => {
    const messages = state.messages;
    return messages.length > 0 ? messages[messages.length - 1] : null;
  },
  hasActiveThread: (state: ThreadStoreState) => Boolean(state.activeThreadId)
};
