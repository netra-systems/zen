import React from 'react';
import { Button } from '@/components/ui/button';
import { Send, Paperclip, Mic, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

interface MessageActionButtonsProps {
  isDisabled: boolean;
  canSend: boolean;
  isSending: boolean;
  onSend: () => void;
}

const AnimatedButton: React.FC<{
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  'aria-label'?: string;
  title?: string;
}> = ({ children, ...props }) => (
  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
    <Button variant="ghost" size="icon" {...props}>
      {children}
    </Button>
  </motion.div>
);

const FileAttachmentButton: React.FC<{ isDisabled: boolean }> = ({ isDisabled }) => (
  <AnimatedButton
    className="rounded-full w-10 h-10 text-gray-500 hover:text-gray-700 hover:bg-gray-100"
    disabled={isDisabled}
    aria-label="Attach file"
    title="Attach file (coming soon)"
  >
    <Paperclip className="w-5 h-5" data-testid="paperclip-icon" />
  </AnimatedButton>
);

const VoiceInputButton: React.FC<{ isDisabled: boolean }> = ({ isDisabled }) => (
  <AnimatedButton
    className="rounded-full w-10 h-10 text-gray-500 hover:text-gray-700 hover:bg-gray-100"
    disabled={isDisabled}
    aria-label="Voice input"
    title="Voice input (coming soon)"
  >
    <Mic className="w-5 h-5" data-testid="mic-icon" />
  </AnimatedButton>
);

const SendButtonIcon: React.FC<{ isSending: boolean }> = ({ isSending }) => (
  <AnimatePresence mode="wait">
    {isSending ? (
      <motion.div
        key="sending"
        initial={{ opacity: 0, rotate: 0 }}
        animate={{ opacity: 1, rotate: 360 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3, rotate: { duration: 1, repeat: Infinity, ease: "linear" } }}
      >
        <Loader2 className="w-5 h-5" data-testid="loading-icon" />
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
);

const SendButton: React.FC<{
  canSend: boolean;
  isSending: boolean;
  onSend: () => void;
}> = ({ canSend, isSending, onSend }) => (
  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
    <Button
      onClick={onSend}
      disabled={!canSend || isSending}
      className={cn(
        "rounded-full flex items-center justify-center transition-all duration-200",
        "bg-emerald-500 hover:bg-emerald-600",
        "text-white shadow-lg hover:shadow-xl",
        "disabled:from-gray-300 disabled:to-gray-400 disabled:shadow-none",
        isSending ? "w-auto px-4 h-12" : "w-12 h-12"
      )}
      aria-label="Send message"
      data-testid="send-button"
    >
      {isSending ? (
        <div className="flex items-center gap-2">
          <SendButtonIcon isSending={isSending} />
          <span>Sending...</span>
        </div>
      ) : (
        <SendButtonIcon isSending={isSending} />
      )}
    </Button>
  </motion.div>
);

export const MessageActionButtons: React.FC<MessageActionButtonsProps> = ({
  isDisabled,
  canSend,
  isSending,
  onSend,
}) => (
  <div className="flex items-center gap-1">
    <FileAttachmentButton isDisabled={isDisabled} />
    <VoiceInputButton isDisabled={isDisabled} />
    <SendButton canSend={canSend} isSending={isSending} onSend={onSend} />
  </div>
);