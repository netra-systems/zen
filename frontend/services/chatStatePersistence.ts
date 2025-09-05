import { logger } from '@/lib/logger';
import { Message, WebSocketMessage } from '@/types/unified';

interface ChatStateData {
  activeThreadId: string | null;
  messages: Message[];
  draftMessage: string;
  scrollPosition: number;
  timestamp: number;
  connectionId?: string;
  lastMessageId?: string;
}

interface PersistenceOptions {
  maxMessages?: number;
  ttlMinutes?: number;
  storageKey?: string;
}

class ChatStatePersistenceService {
  private readonly defaultOptions: Required<PersistenceOptions> = {
    maxMessages: 100,
    ttlMinutes: 30,
    storageKey: 'chat_state_persistence'
  };
  
  private options: Required<PersistenceOptions>;
  private saveTimer: NodeJS.Timeout | null = null;
  private debouncedSaveDelay = 500; // ms
  private storage: Storage | null = null;
  private isClientSide: boolean = false;
  
  constructor(options: PersistenceOptions = {}) {
    this.options = { ...this.defaultOptions, ...options };
    
    // SSR safety: Only initialize client-side features in browser environment
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      this.storage = window.localStorage;
      this.isClientSide = true;
      this.setupEventListeners();
      this.cleanupExpiredState();
    }
  }
  
  private setupEventListeners(): void {
    // Listen for visibility changes to save state when tab becomes hidden
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          this.saveStateImmediate();
        }
      });
    }
    
    // Save state before page unload
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => {
        this.saveStateImmediate();
      });
    }
  }
  
  private cleanupExpiredState(): void {
    // SSR safety check
    if (!this.storage) {
      return;
    }
    
    try {
      const stored = this.storage.getItem(this.options.storageKey);
      if (!stored) return;
      
      const state: ChatStateData = JSON.parse(stored);
      const age = Date.now() - state.timestamp;
      const maxAge = this.options.ttlMinutes * 60 * 1000;
      
      if (age > maxAge) {
        this.storage.removeItem(this.options.storageKey);
        logger.debug('Cleaned up expired chat state', undefined, {
          component: 'ChatStatePersistence',
          action: 'cleanup_expired',
          metadata: { ageMinutes: Math.round(age / 60000) }
        });
      }
    } catch (error) {
      logger.error('Failed to cleanup expired state', error as Error, {
        component: 'ChatStatePersistence',
        action: 'cleanup_failed'
      });
    }
  }
  
  public saveState(data: Partial<ChatStateData>): void {
    // Debounce saves to avoid excessive localStorage writes
    if (this.saveTimer) {
      clearTimeout(this.saveTimer);
    }
    
    this.saveTimer = setTimeout(() => {
      this.saveStateImmediate(data);
    }, this.debouncedSaveDelay);
  }
  
  private saveStateImmediate(data: Partial<ChatStateData> = {}): void {
    // SSR safety check
    if (!this.storage) {
      return;
    }
    
    try {
      const currentState = this.getState();
      const newState: ChatStateData = {
        ...currentState,
        ...data,
        timestamp: Date.now()
      };
      
      // Limit messages to prevent excessive storage
      if (newState.messages && newState.messages.length > this.options.maxMessages) {
        newState.messages = newState.messages.slice(-this.options.maxMessages);
      }
      
      // Sanitize draft message
      if (newState.draftMessage && newState.draftMessage.length > 10000) {
        newState.draftMessage = newState.draftMessage.substring(0, 10000);
      }
      
      this.storage.setItem(this.options.storageKey, JSON.stringify(newState));
      
      logger.debug('Chat state saved', undefined, {
        component: 'ChatStatePersistence',
        action: 'state_saved',
        metadata: {
          threadId: newState.activeThreadId,
          messageCount: newState.messages?.length || 0,
          hasDraft: !!newState.draftMessage
        }
      });
    } catch (error) {
      // Handle quota exceeded error
      if (error instanceof Error && error.name === 'QuotaExceededError') {
        this.handleQuotaExceeded();
      } else {
        logger.error('Failed to save chat state', error as Error, {
          component: 'ChatStatePersistence',
          action: 'save_failed'
        });
      }
    }
  }
  
  private handleQuotaExceeded(): void {
    // SSR safety check
    if (!this.storage) {
      return;
    }
    
    try {
      // Clear old messages to make room
      const state = this.getState();
      if (state.messages && state.messages.length > 10) {
        state.messages = state.messages.slice(-10);
        this.storage.setItem(this.options.storageKey, JSON.stringify(state));
        logger.warn('Reduced message history due to storage quota', undefined, {
          component: 'ChatStatePersistence',
          action: 'quota_exceeded_handled'
        });
      }
    } catch (error) {
      // If still failing, clear the state entirely
      this.clearState();
      logger.error('Cleared chat state due to persistent quota issues', undefined, {
        component: 'ChatStatePersistence',
        action: 'quota_exceeded_cleared'
      });
    }
  }
  
  public getState(): ChatStateData {
    // SSR safety check
    if (!this.storage) {
      return this.getDefaultState();
    }
    
    try {
      const stored = this.storage.getItem(this.options.storageKey);
      if (!stored) {
        return this.getDefaultState();
      }
      
      const state: ChatStateData = JSON.parse(stored);
      const age = Date.now() - state.timestamp;
      const maxAge = this.options.ttlMinutes * 60 * 1000;
      
      // Return default state if expired
      if (age > maxAge) {
        return this.getDefaultState();
      }
      
      return state;
    } catch (error) {
      logger.error('Failed to retrieve chat state', error as Error, {
        component: 'ChatStatePersistence',
        action: 'get_failed'
      });
      return this.getDefaultState();
    }
  }
  
  private getDefaultState(): ChatStateData {
    return {
      activeThreadId: null,
      messages: [],
      draftMessage: '',
      scrollPosition: 0,
      timestamp: Date.now()
    };
  }
  
  public clearState(): void {
    // SSR safety check
    if (!this.storage) {
      return;
    }
    
    try {
      this.storage.removeItem(this.options.storageKey);
      logger.debug('Chat state cleared', undefined, {
        component: 'ChatStatePersistence',
        action: 'state_cleared'
      });
    } catch (error) {
      logger.error('Failed to clear chat state', error as Error, {
        component: 'ChatStatePersistence',
        action: 'clear_failed'
      });
    }
  }
  
  public updateMessages(messages: Message[]): void {
    this.saveState({ messages });
  }
  
  public updateDraft(draftMessage: string): void {
    this.saveState({ draftMessage });
  }
  
  public updateThread(threadId: string | null): void {
    this.saveState({ activeThreadId: threadId });
  }
  
  public updateScrollPosition(position: number): void {
    this.saveState({ scrollPosition: position });
  }
  
  public updateConnectionInfo(connectionId: string, lastMessageId?: string): void {
    this.saveState({ connectionId, lastMessageId });
  }
  
  public shouldRestoreState(): boolean {
    const state = this.getState();
    const age = Date.now() - state.timestamp;
    const maxAge = 5 * 60 * 1000; // 5 minutes
    
    // Only restore if state is recent and has content
    return age < maxAge && (
      !!state.activeThreadId ||
      state.messages.length > 0 ||
      !!state.draftMessage
    );
  }
  
  public getRestorableState(): {
    threadId: string | null;
    messages: Message[];
    draftMessage: string;
    scrollPosition: number;
  } | null {
    if (!this.shouldRestoreState()) {
      return null;
    }
    
    const state = this.getState();
    return {
      threadId: state.activeThreadId,
      messages: state.messages,
      draftMessage: state.draftMessage,
      scrollPosition: state.scrollPosition
    };
  }
  
  public destroy(): void {
    if (this.saveTimer) {
      clearTimeout(this.saveTimer);
      this.saveTimer = null;
    }
  }
}

// Export singleton instance
export const chatStatePersistence = new ChatStatePersistenceService();

// Export class for testing
export { ChatStatePersistenceService };