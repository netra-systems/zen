import React, { useEffect, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Paperclip, Mic, Loader2, FileText, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useMessageInput } from './hooks/useMessageInput';
import { useCommandPalette } from './hooks/useCommandPalette';
import { useMessageSender } from './hooks/useMessageSender';
import { CommandPalette } from './CommandPalette';
import { TemplatePanel } from './TemplatePanel';
import { MESSAGE_INPUT_CONSTANTS } from './constants';

const { MAX_ROWS, CHAR_LIMIT } = MESSAGE_INPUT_CONSTANTS;

export const MessageInputWithCommands: React.FC = () => {
  const { isProcessing } = useUnifiedChatStore();
  
  const messageInput = useMessageInput();
  const commandPalette = useCommandPalette(messageInput.message, useMessageSender().isAdmin);
  const messageSender = useMessageSender();

  // Focus input on mount
  useEffect(() => {
    if (messageInput.textareaRef.current && messageSender.isAuthenticated) {
      messageInput.textareaRef.current.focus();
    }
  }, [messageSender.isAuthenticated, messageInput.textareaRef]);

  const hideOverlays = () => {
    commandPalette.hideCommandPalette();
    commandPalette.hideTemplates();
  };

  const handleSend = async () => {
    await messageSender.handleSend(
      messageInput.message,
      messageInput.isSending,
      messageInput.setIsSending,
      messageInput.addToHistory,
      messageInput.clearMessage,
      hideOverlays
    );
  };

  const handleArrowNavigation = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      commandPalette.navigateCommands('down');
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      commandPalette.navigateCommands('up');
    }
  };

  const handleCommandSelection = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab' || e.key === 'Enter') {
      const selected = commandPalette.getSelectedCommand();
      if (selected) {
        e.preventDefault();
        insertTemplate(selected.template || selected.command + ' ');
      }
    }
  };

  const handleCommandPaletteNavigation = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    handleArrowNavigation(e);
    handleCommandSelection(e);
    if (e.key === 'Escape') {
      e.preventDefault();
      commandPalette.hideCommandPalette();
    }
  };

  const handleHistoryNavigation = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'ArrowUp' && !messageInput.message) {
      e.preventDefault();
      messageInput.navigateHistory('up');
    } else if (e.key === 'ArrowDown' && messageInput.historyIndex !== -1) {
      e.preventDefault();
      messageInput.navigateHistory('down');
    }
  };

  const handleEnterKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isProcessing) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (commandPalette.showCommandPalette) {
      handleCommandPaletteNavigation(e);
      return;
    }
    handleHistoryNavigation(e);
    handleEnterKey(e);
  };

  const insertTemplate = (template: string) => {
    messageInput.updateMessage(template);
    commandPalette.hideTemplates();
    messageInput.textareaRef.current?.focus();
  };

  const isDisabled = !messageSender.isAuthenticated || isProcessing || 
    messageInput.isSending || !messageInput.message.trim() || messageInput.isOverLimit;

  const renderAdminIndicator = () => (
    messageSender.isAdmin && (
      <div className="flex items-center space-x-2 px-3 py-2 bg-purple-50 rounded-lg border border-purple-200">
        <Shield className="w-4 h-4 text-purple-600" />
        <span className="text-xs font-medium text-purple-700">Admin Mode</span>
      </div>
    )
  );

  const getTemplateButtonProps = () => ({
    variant: "outline" as const,
    size: "sm" as const,
    onClick: commandPalette.toggleTemplates,
    className: "text-purple-600 border-purple-200 hover:bg-purple-50"
  });

  const renderTemplateButton = () => {
    if (!messageSender.isAdmin) return null;
    return (
      <Button {...getTemplateButtonProps()}>
        <FileText className="w-4 h-4" />
      </Button>
    );
  };

  return (
    <div className="relative">
      <CommandPalette
        show={commandPalette.showCommandPalette}
        commands={commandPalette.filteredCommands}
        selectedIndex={commandPalette.selectedCommandIndex}
        onCommandSelect={insertTemplate}
        onHoverCommand={commandPalette.setSelectedIndex}
      />
      
      <TemplatePanel
        show={commandPalette.showTemplates}
        onTemplateSelect={insertTemplate}
      />

      <div className="flex items-end space-x-2 p-4 bg-white/95 backdrop-blur-sm border-t border-gray-200">
        {renderAdminIndicator()}
        {renderTemplateButton()}

        {/* Main Input Area */}
        <div className="flex-1 relative">
          <textarea
            ref={messageInput.textareaRef}
            value={messageInput.message}
            onChange={(e) => messageInput.updateMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              messageSender.isAdmin 
                ? "Type '/' for commands or message..." 
                : messageSender.isAuthenticated 
                  ? "Type your message..." 
                  : "Please sign in to send messages"
            }
            rows={messageInput.rows}
            disabled={!messageSender.isAuthenticated || isProcessing}
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
          {messageInput.isNearLimit && (
            <div className={cn(
              "absolute bottom-2 right-12 text-xs",
              messageInput.isOverLimit ? "text-red-500" : "text-amber-500"
            )}>
              {messageInput.message.length}/{CHAR_LIMIT}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="icon"
            disabled={!messageSender.isAuthenticated}
            className="text-gray-500 hover:text-gray-700"
          >
            <Paperclip className="w-4 h-4" />
          </Button>
          
          <Button
            variant="outline"
            size="icon"
            disabled={!messageSender.isAuthenticated}
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
            {messageInput.isSending || isProcessing ? (
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