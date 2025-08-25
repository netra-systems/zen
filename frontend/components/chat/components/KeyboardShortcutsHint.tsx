import React from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface KeyboardShortcutsHintProps {
  isAuthenticated: boolean;
  hasMessage: boolean;
}

function ShortcutItem({ icon, text }: {
  icon: React.ReactNode;
  text: string;
}) {
  return (
    <span className="flex items-center gap-1">
      {icon}
      <span>{text}</span>
    </span>
  );
}

const SearchShortcut = () => (
  <ShortcutItem 
    icon={<span className="w-3 h-3 flex items-center justify-center text-xs">⌘</span>}
    text="+ K for search"
  />
);

const HistoryShortcut = () => (
  <ShortcutItem 
    icon={
      <>
        <ArrowUp className="w-3 h-3" />
        <ArrowDown className="w-3 h-3" />
      </>
    }
    text="for history"
  />
);

const shouldShowHint = (isAuthenticated: boolean, hasMessage: boolean): boolean => {
  return isAuthenticated && !hasMessage;
};

export const KeyboardShortcutsHint: React.FC<KeyboardShortcutsHintProps> = ({
  isAuthenticated,
  hasMessage,
}) => (
  <AnimatePresence>
    {shouldShowHint(isAuthenticated, hasMessage) && (
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.2 }}
        className="absolute -top-8 left-0 flex items-center gap-4 text-xs text-gray-400"
      >
        <SearchShortcut />
        <HistoryShortcut />
      </motion.div>
    )}
  </AnimatePresence>
);

// Export internal components for testing
export { SearchShortcut, HistoryShortcut };