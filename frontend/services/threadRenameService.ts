/**
 * Automatic Thread Renaming Service
 * Analyzes first user message to generate concise, descriptive thread titles
 */

import { ThreadService } from './threadService';
import { logger } from '@/lib/logger';

interface ThreadRenameConfig {
  maxTitleLength: number;
  fallbackPrefix: string;
  enableAutoRename: boolean;
}

const DEFAULT_CONFIG: ThreadRenameConfig = {
  maxTitleLength: 50,
  fallbackPrefix: 'Chat',
  enableAutoRename: true
};

export class ThreadRenameService {
  private static config = DEFAULT_CONFIG;
  private static renamingInProgress = new Set<string>();

  /**
   * Automatically rename thread based on first user message
   */
  static async autoRenameThread(
    threadId: string, 
    firstMessage: string
  ): Promise<string | null> {
    // Check if auto-rename is enabled
    if (!this.config.enableAutoRename) {
      return null;
    }

    // Prevent duplicate rename attempts
    if (this.renamingInProgress.has(threadId)) {
      return null;
    }

    try {
      this.renamingInProgress.add(threadId);

      // Generate title from message
      const generatedTitle = await this.generateTitle(firstMessage);
      
      if (!generatedTitle) {
        return this.getFallbackTitle();
      }

      // Update thread metadata
      await ThreadService.updateThread(threadId, generatedTitle, {
        auto_renamed: true,
        renamed_at: Date.now()
      });

      // Emit rename event
      const renameEvent = new CustomEvent('threadRenamed', {
        detail: {
          threadId,
          newTitle: generatedTitle
        }
      });
      window.dispatchEvent(renameEvent);

      return generatedTitle;
    } catch (error) {
      logger.error('Failed to auto-rename thread', error as Error, {
        component: 'ThreadRenameService',
        action: 'auto_rename_failed',
        metadata: { threadId, messageContent: firstMessage.substring(0, 100) }
      });
      return this.getFallbackTitle();
    } finally {
      this.renamingInProgress.delete(threadId);
    }
  }

  /**
   * Generate title from message content
   * Uses simple heuristics for now, can be enhanced with LLM
   */
  private static async generateTitle(message: string): Promise<string> {
    // Remove extra whitespace
    const cleanMessage = message.trim().replace(/\s+/g, ' ');
    
    // Extract key intent patterns
    const patterns = [
      { regex: /^(how|what|why|when|where|who|can|should|would|could)\s+(.+)/i, group: 0 },
      { regex: /^(optimize|analyze|review|check|fix|debug|help with|explain)\s+(.+)/i, group: 0 },
      { regex: /^(.+?)\s*(question|issue|problem|error|bug)/i, group: 1 },
      { regex: /^(.+?)[\?\.\!]/i, group: 1 }
    ];

    let title = '';
    
    for (const pattern of patterns) {
      const match = cleanMessage.match(pattern.regex);
      if (match) {
        title = match[pattern.group] || match[0];
        break;
      }
    }

    // If no pattern matched, use first sentence/phrase
    if (!title) {
      const firstSentence = cleanMessage.split(/[.!?]/)[0];
      title = firstSentence || cleanMessage;
    }

    // Clean up title
    title = title
      .replace(/^(please|i need|i want|help me|can you)/i, '') // Remove common prefixes
      .replace(/[^\w\s-]/g, '') // Remove special chars except spaces and hyphens
      .trim();

    // Capitalize first letter
    title = title.charAt(0).toUpperCase() + title.slice(1);

    // Truncate if too long
    if (title.length > this.config.maxTitleLength) {
      title = title.substring(0, this.config.maxTitleLength - 3) + '...';
    }

    return title || this.getFallbackTitle();
  }

  /**
   * Generate fallback title with timestamp
   */
  private static getFallbackTitle(): string {
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    const date = now.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric' 
    });
    return `${this.config.fallbackPrefix} - ${date} ${time}`;
  }

  /**
   * Manually rename a thread
   */
  static async manualRenameThread(
    threadId: string,
    newTitle: string
  ): Promise<boolean> {
    try {
      // Validate title
      if (!newTitle || newTitle.trim().length === 0) {
        throw new Error('Title cannot be empty');
      }

      const trimmedTitle = newTitle.trim().substring(0, this.config.maxTitleLength);

      // Update thread metadata
      await ThreadService.updateThread(threadId, trimmedTitle, {
        manually_renamed: true,
        renamed_at: Date.now()
      });

      // Emit rename event
      const renameEvent = new CustomEvent('threadRenamed', {
        detail: {
          threadId,
          newTitle: trimmedTitle,
          manual: true
        }
      });
      window.dispatchEvent(renameEvent);

      return true;
    } catch (error) {
      logger.error('Failed to manually rename thread', error as Error, {
        component: 'ThreadRenameService',
        action: 'manual_rename_failed',
        metadata: { threadId, newTitle }
      });
      return false;
    }
  }

  /**
   * Configure the rename service
   */
  static configure(config: Partial<ThreadRenameConfig>) {
    this.config = { ...this.config, ...config };
  }
}