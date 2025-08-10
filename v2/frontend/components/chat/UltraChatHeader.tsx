"use client";

import React, { useState, useEffect } from 'react';
import { useChatStore } from '@/store/chat';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import {
  Bot,
  Activity,
  Plus,
  Settings,
  HelpCircle,
  User,
  LogOut,
  ChevronDown,
  Command,
  Moon,
  Sun,
  Sparkles,
  Zap,
  Clock,
  CheckCircle,
  AlertCircle,
  Menu,
  X,
  Download,
  Share2,
  History,
  Keyboard
} from 'lucide-react';

interface UltraChatHeaderProps {
  onToggleSidebar?: () => void;
  onNewChat?: () => void;
  onOpenSettings?: () => void;
  onOpenHelp?: () => void;
  isSidebarOpen?: boolean;
  userName?: string;
  userAvatar?: string;
  isDarkMode?: boolean;
  onToggleDarkMode?: () => void;
}

const thoughtMessages = [
  "Analyzing your request...",
  "Optimizing AI workloads...",
  "Gathering performance metrics...",
  "Identifying bottlenecks...",
  "Calculating cost savings...",
  "Preparing recommendations...",
  "Simulating optimizations...",
  "Evaluating resource usage...",
  "Processing data insights...",
  "Finalizing analysis..."
];

export const UltraChatHeader: React.FC<UltraChatHeaderProps> = ({
  onToggleSidebar,
  onNewChat,
  onOpenSettings,
  onOpenHelp,
  isSidebarOpen = true,
  userName = "User",
  userAvatar,
  isDarkMode = false,
  onToggleDarkMode
}) => {
  const { currentSubAgent, subAgentStatus, isProcessing, messages } = useChatStore();
  const [thoughtIndex, setThoughtIndex] = useState(0);
  const [showShortcuts, setShowShortcuts] = useState(false);

  // Cycle through thought messages
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        setThoughtIndex((prev) => (prev + 1) % thoughtMessages.length);
      }, 3000);
      return () => clearInterval(interval);
    } else {
      setThoughtIndex(0);
    }
  }, [isProcessing]);

  const getStatusIcon = () => {
    if (!isProcessing) return <CheckCircle className="w-4 h-4 text-green-500" />;
    if (subAgentStatus?.lifecycle === 'failed' || subAgentStatus?.error_message) return <AlertCircle className="w-4 h-4 text-red-500" />;
    return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
  };

  const getStatusText = () => {
    if (!isProcessing) return 'Ready';
    if (currentSubAgent) return `${currentSubAgent} Processing`;
    return 'Processing';
  };

  const getProgressPercentage = () => {
    // Calculate approximate progress based on messages and agent
    const agentSteps = ['TriageSubAgent', 'DataSubAgent', 'OptimizationsCoreSubAgent', 'ActionsToMeetGoalsSubAgent', 'ReportingSubAgent'];
    const currentIndex = agentSteps.indexOf(currentSubAgent || '');
    if (currentIndex === -1) return 0;
    return Math.round(((currentIndex + 1) / agentSteps.length) * 100);
  };

  return (
    <header className={cn(
      "sticky top-0 z-50 w-full",
      "bg-white/95 backdrop-blur-lg border-b",
      "transition-all duration-300",
      isDarkMode && "bg-gray-900/95 border-gray-800"
    )}>
      <div className="h-16 px-4 flex items-center justify-between">
        {/* Left Section */}
        <div className="flex items-center gap-3">
          {/* Sidebar Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className="md:hidden"
          >
            {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </Button>

          {/* Logo and Brand */}
          <div className="flex items-center gap-2">
            <div className={cn(
              "p-2 rounded-lg",
              "bg-gradient-to-br from-blue-500 to-purple-600"
            )}>
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg hidden sm:inline">Netra AI</span>
          </div>

          {/* Agent Status */}
          <AnimatePresence mode="wait">
            {isProcessing && (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="flex items-center gap-3"
              >
                <div className="h-6 w-px bg-gray-300" />
                <div className="flex items-center gap-2">
                  {getStatusIcon()}
                  <div>
                    <div className="text-sm font-medium">{getStatusText()}</div>
                    <AnimatePresence mode="wait">
                      <motion.div
                        key={thoughtIndex}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -5 }}
                        transition={{ duration: 0.3 }}
                        className="text-xs text-gray-500"
                      >
                        {thoughtMessages[thoughtIndex]}
                      </motion.div>
                    </AnimatePresence>
                  </div>
                </div>

                {/* Progress Indicator */}
                <div className="hidden lg:flex items-center gap-2">
                  <div className="text-xs text-gray-500">Progress</div>
                  <div className="w-32 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${getProgressPercentage()}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  <span className="text-xs font-medium">{getProgressPercentage()}%</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Step Counter */}
          {messages.length > 0 && (
            <Badge variant="secondary" className="hidden sm:inline-flex">
              <Clock className="w-3 h-3 mr-1" />
              {messages.filter(m => m.displayed_to_user).length} messages
            </Badge>
          )}
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-2">
          {/* Quick Actions */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onNewChat}
            className="hidden sm:inline-flex"
          >
            <Plus className="w-4 h-4 mr-1" />
            New Chat
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowShortcuts(!showShortcuts)}
            className="hidden md:inline-flex"
          >
            <Keyboard className="w-4 h-4" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleDarkMode}
          >
            {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={onOpenSettings}
          >
            <Settings className="w-4 h-4" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={onOpenHelp}
          >
            <HelpCircle className="w-4 h-4" />
          </Button>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="gap-2 px-2">
                <Avatar className="w-8 h-8">
                  <AvatarFallback className="bg-gradient-to-br from-blue-500 to-purple-600 text-white">
                    {userAvatar ? (
                      <img src={userAvatar} alt={userName} className="w-full h-full object-cover" />
                    ) : (
                      <User className="w-4 h-4" />
                    )}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden lg:inline text-sm font-medium">{userName}</span>
                <ChevronDown className="w-4 h-4 hidden lg:inline" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <User className="w-4 h-4 mr-2" />
                Profile
              </DropdownMenuItem>
              <DropdownMenuItem>
                <History className="w-4 h-4 mr-2" />
                Chat History
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Download className="w-4 h-4 mr-2" />
                Export Data
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Share2 className="w-4 h-4 mr-2" />
                Share & Collaborate
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Command className="w-4 h-4 mr-2" />
                Keyboard Shortcuts
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-red-600">
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Keyboard Shortcuts Panel */}
      <AnimatePresence>
        {showShortcuts && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t bg-gray-50 px-4 py-3"
          >
            <div className="flex flex-wrap gap-4 text-xs">
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-white border rounded shadow-sm">⌘K</kbd>
                <span>Command Palette</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-white border rounded shadow-sm">⌘↵</kbd>
                <span>Send Message</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-white border rounded shadow-sm">⌘⇧C</kbd>
                <span>Copy Chat</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-white border rounded shadow-sm">Esc</kbd>
                <span>Cancel</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-white border rounded shadow-sm">↑</kbd>
                <span>Edit Last Message</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Processing Progress Bar */}
      {isProcessing && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-200">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500"
            animate={{ x: ['0%', '100%', '0%'] }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            style={{ width: '50%' }}
          />
        </div>
      )}
    </header>
  );
};