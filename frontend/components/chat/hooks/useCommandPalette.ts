import { useState, useEffect } from 'react';
import { ADMIN_COMMANDS } from '../constants';
import { AdminCommand, CommandPaletteState } from '../types';

export const useCommandPalette = (message: string, isAdmin: boolean) => {
  const [state, setState] = useState<CommandPaletteState>({
    showCommandPalette: false,
    showTemplates: false,
    selectedCommandIndex: 0,
    filteredCommands: []
  });

  const filterCommands = (query: string): AdminCommand[] => {
    return ADMIN_COMMANDS.filter(cmd => 
      cmd.command.toLowerCase().includes(query) || 
      cmd.description.toLowerCase().includes(query)
    );
  };

  const updateCommandFilter = (message: string) => {
    if (isAdmin && message.startsWith('/')) {
      const query = message.slice(1).toLowerCase();
      const filtered = filterCommands(query);
      setState(prev => ({
        ...prev,
        filteredCommands: filtered,
        showCommandPalette: filtered.length > 0,
        selectedCommandIndex: 0
      }));
    } else {
      hideCommandPalette();
    }
  };

  const hideCommandPalette = () => {
    setState(prev => ({ ...prev, showCommandPalette: false }));
  };

  const hideTemplates = () => {
    setState(prev => ({ ...prev, showTemplates: false }));
  };

  const toggleTemplates = () => {
    setState(prev => ({ ...prev, showTemplates: !prev.showTemplates }));
  };

  const navigateCommands = (direction: 'up' | 'down') => {
    setState(prev => {
      if (direction === 'down') {
        return {
          ...prev,
          selectedCommandIndex: Math.min(
            prev.selectedCommandIndex + 1, 
            prev.filteredCommands.length - 1
          )
        };
      } else {
        return {
          ...prev,
          selectedCommandIndex: Math.max(prev.selectedCommandIndex - 1, 0)
        };
      }
    });
  };

  const setSelectedIndex = (index: number) => {
    setState(prev => ({ ...prev, selectedCommandIndex: index }));
  };

  const getSelectedCommand = (): AdminCommand | null => {
    return state.filteredCommands[state.selectedCommandIndex] || null;
  };

  // Update command filter when message changes
  useEffect(() => {
    updateCommandFilter(message);
  }, [message, isAdmin]);

  return {
    ...state,
    hideCommandPalette,
    hideTemplates,
    toggleTemplates,
    navigateCommands,
    setSelectedIndex,
    getSelectedCommand
  };
};