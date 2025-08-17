import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Command } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AdminCommand } from './types';

interface CommandPaletteProps {
  show: boolean;
  commands: AdminCommand[];
  selectedIndex: number;
  onCommandSelect: (template: string) => void;
  onHoverCommand: (index: number) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  show,
  commands,
  selectedIndex,
  onCommandSelect,
  onHoverCommand
}) => {
  const handleCommandClick = (cmd: AdminCommand) => {
    const template = cmd.template || cmd.command + ' ';
    onCommandSelect(template);
  };

  const getCommandClasses = (index: number) => {
    return cn(
      "w-full flex items-center space-x-3 px-3 py-2 rounded-md text-left transition-colors",
      index === selectedIndex
        ? "bg-purple-100 text-purple-900"
        : "hover:bg-gray-50 text-gray-700"
    );
  };

  const renderCommandButton = (cmd: AdminCommand, index: number) => (
    <button
      key={cmd.command}
      className={getCommandClasses(index)}
      onMouseEnter={() => onHoverCommand(index)}
      onClick={() => handleCommandClick(cmd)}
    >
      {cmd.icon}
      <div className="flex-1">
        <p className="text-sm font-medium">{cmd.command}</p>
        <p className="text-xs text-gray-500">{cmd.description}</p>
      </div>
    </button>
  );

  const renderHeader = () => (
    <div className="flex items-center space-x-2 px-2 py-1 text-xs text-gray-500">
      <Command className="w-3 h-3" />
      <span>Admin Commands</span>
    </div>
  );

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          className="absolute bottom-full mb-2 left-0 right-0 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden"
        >
          <div className="p-2">
            {renderHeader()}
            {commands.map((cmd, index) => renderCommandButton(cmd, index))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};