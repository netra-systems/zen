import React from 'react';
import { motion } from 'framer-motion';
import { 
  Plus, 
  MessageSquare,
  Trash2,
  Pencil,
  X,
  Check,
  Loader2
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { Thread, getThreadTitle } from '@/types/unified';

interface ThreadSidebarHeaderProps {
  onCreateThread: () => Promise<void>;
  isCreating: boolean;
  isLoading: boolean;
  isAuthenticated: boolean;
}

/**
 * Header component with new conversation button
 */
export const ThreadSidebarHeader: React.FC<ThreadSidebarHeaderProps> = ({
  onCreateThread,
  isCreating,
  isLoading,
  isAuthenticated
}) => {
  const [isProcessing, setIsProcessing] = React.useState(false);
  const isProcessingRef = React.useRef(false);

  const handleCreateThread = async () => {
    if (isProcessing || isProcessingRef.current || isCreating || isLoading || !isAuthenticated) {
      return;
    }
    
    isProcessingRef.current = true;
    setIsProcessing(true);
    try {
      await onCreateThread();
    } catch (error) {
      // Error handling - could add user notification here
      console.error('Thread creation failed:', error);
    } finally {
      isProcessingRef.current = false;
      setIsProcessing(false);
    }
  };

  return (
    <div className="p-4 border-b border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Conversations</h2>
        <Badge variant="beta" className="text-xs">BETA</Badge>
      </div>
      <button
        type="button"
        onClick={handleCreateThread}
        disabled={isCreating || isLoading || !isAuthenticated || isProcessing}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 glass-button-primary rounded-lg transition-all disabled:glass-disabled"
      >
        {isCreating || isProcessing ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Plus className="w-5 h-5" />
        )}
        <span>New Conversation</span>
      </button>
    </div>
  );
};

interface ThreadEditingInputProps {
  editingTitle: string;
  onTitleChange: (title: string) => void;
  onSave: () => void;
  onCancel: () => void;
}

/**
 * Thread title editing input component
 */
export const ThreadEditingInput: React.FC<ThreadEditingInputProps> = ({
  editingTitle,
  onTitleChange,
  onSave,
  onCancel
}) => (
  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
    <input
      type="text"
      value={editingTitle}
      onChange={(e) => onTitleChange(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onSave();
        if (e.key === 'Escape') onCancel();
      }}
      className="flex-1 px-2 py-1 text-sm border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
      autoFocus
    />
    <button
      type="button"
      onClick={onSave}
      className="p-1 text-green-600 hover:bg-green-50 rounded"
    >
      <Check className="w-4 h-4" />
    </button>
    <button
      type="button"
      onClick={onCancel}
      className="p-1 text-gray-600 hover:bg-gray-100 rounded"
    >
      <X className="w-4 h-4" />
    </button>
  </div>
);

interface ThreadDisplayInfoProps {
  thread: Thread;
  formatDate: (timestamp: number) => string;
}

/**
 * Thread display information component
 */
export const ThreadDisplayInfo: React.FC<ThreadDisplayInfoProps> = ({
  thread,
  formatDate
}) => (
  <>
    <h3 className="text-sm font-medium text-gray-900 truncate">
      {thread.title || 'Untitled Conversation'}
    </h3>
    <div className="flex items-center gap-1 mt-1">
      <span className="text-xs text-gray-500">
        {formatDate(thread.created_at)}
      </span>
      {thread.message_count && thread.message_count > 0 && (
        <span className="text-xs text-gray-400">
          · {thread.message_count} messages
        </span>
      )}
    </div>
  </>
);

interface ThreadActionsProps {
  thread: Thread;
  onEdit: () => void;
  onDelete: () => void;
}

/**
 * Thread action buttons component
 */
export const ThreadActions: React.FC<ThreadActionsProps> = ({
  thread,
  onEdit,
  onDelete
}) => (
  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onEdit();
      }}
      className="p-1 text-gray-600 hover:bg-gray-100 rounded"
    >
      <Pencil className="w-4 h-4" />
    </button>
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onDelete();
      }}
      className="p-1 text-red-600 hover:bg-red-50 rounded"
    >
      <Trash2 className="w-4 h-4" />
    </button>
  </div>
);

interface ThreadItemProps {
  thread: Thread;
  currentThreadId: string | null;
  isLoading: boolean;
  loadingThreadId?: string;
  editingThreadId: string | null;
  editingTitle: string;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onTitleChange: (title: string) => void;
  onSaveTitle: () => void;
  onCancelEdit: () => void;
  formatDate: (timestamp: number) => string;
}

/**
 * Individual thread item component
 */
export const ThreadItem: React.FC<ThreadItemProps> = ({
  thread,
  currentThreadId,
  isLoading,
  loadingThreadId,
  editingThreadId,
  editingTitle,
  onSelect,
  onEdit,
  onDelete,
  onTitleChange,
  onSaveTitle,
  onCancelEdit,
  formatDate
}) => (
  <motion.div
    key={thread.id}
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -20 }}
    className={`
      group relative p-3 rounded-lg cursor-pointer transition-all
      ${currentThreadId === thread.id 
        ? 'bg-white shadow-md border border-blue-200' 
        : 'hover:bg-white hover:shadow-sm'
      }
      ${loadingThreadId === thread.id ? 'opacity-75' : ''}
      ${isLoading && thread.id !== loadingThreadId ? 'pointer-events-none opacity-50' : ''}
    `}
    onClick={onSelect}
  >
    <div className="flex items-start gap-3">
      {loadingThreadId === thread.id ? (
        <Loader2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0 animate-spin" />
      ) : (
        <MessageSquare className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
      )}
      
      <div className="flex-1 min-w-0">
        {editingThreadId === thread.id ? (
          <ThreadEditingInput
            editingTitle={editingTitle}
            onTitleChange={onTitleChange}
            onSave={onSaveTitle}
            onCancel={onCancelEdit}
          />
        ) : (
          <ThreadDisplayInfo thread={thread} formatDate={formatDate} />
        )}
      </div>

      {editingThreadId !== thread.id && (
        <ThreadActions
          thread={thread}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      )}
    </div>
  </motion.div>
);

/**
 * Empty state component for when no threads exist
 */
export const ThreadEmptyState: React.FC = () => (
  <div className="text-center py-8 text-gray-500">
    <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-300" />
    <p className="text-sm">No conversations yet</p>
    <p className="text-xs mt-1">Start a new conversation to begin</p>
  </div>
);

/**
 * Authentication required state component
 */
export const ThreadAuthRequiredState: React.FC = () => (
  <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center">
        <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p className="text-gray-600 mb-2">Please sign in to view conversations</p>
        <p className="text-sm text-gray-500">Sign in to access your chat history</p>
      </div>
    </div>
  </div>
);