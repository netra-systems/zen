/**
 * Mock implementation of lucide-react icons for testing
 * Replaces actual icons with simple div elements
 */

import React from 'react';

// Create a mock icon component
const createMockIcon = (iconName: string) => {
  const MockIcon = React.forwardRef<HTMLDivElement, any>(({ className, ...props }, ref) =>
    React.createElement('div', {
      ref,
      'data-testid': `${iconName.toLowerCase()}-icon`,
      'data-icon': iconName,
      className,
      ...props
    })
  );
  MockIcon.displayName = `Mock${iconName}Icon`;
  return MockIcon;
};

// Export all the icons used in the ThinkingIndicator component
export const Brain = createMockIcon('Brain');
export const Sparkles = createMockIcon('Sparkles');
export const Cpu = createMockIcon('Cpu');
export const Loader2 = createMockIcon('Loader2');

// Export any other commonly used lucide icons
export const ChevronDown = createMockIcon('ChevronDown');
export const ChevronUp = createMockIcon('ChevronUp');
export const Send = createMockIcon('Send');
export const Paperclip = createMockIcon('Paperclip');
export const Mic = createMockIcon('Mic');
export const X = createMockIcon('X');
export const Plus = createMockIcon('Plus');
export const Settings = createMockIcon('Settings');
export const User = createMockIcon('User');
export const MessageSquare = createMockIcon('MessageSquare');
export const Search = createMockIcon('Search');
export const Menu = createMockIcon('Menu');
export const Copy = createMockIcon('Copy');
export const Check = createMockIcon('Check');
export const AlertCircle = createMockIcon('AlertCircle');
export const Info = createMockIcon('Info');
export const Trash2 = createMockIcon('Trash2');
export const Edit = createMockIcon('Edit');
export const Eye = createMockIcon('Eye');
export const EyeOff = createMockIcon('EyeOff');
export const ArrowLeft = createMockIcon('ArrowLeft');
export const ArrowRight = createMockIcon('ArrowRight');
export const ArrowUp = createMockIcon('ArrowUp');
export const ArrowDown = createMockIcon('ArrowDown');
export const Home = createMockIcon('Home');
export const Star = createMockIcon('Star');
export const Heart = createMockIcon('Heart');
export const Download = createMockIcon('Download');
export const Upload = createMockIcon('Upload');
export const RefreshCw = createMockIcon('RefreshCw');
export const MoreVertical = createMockIcon('MoreVertical');
export const MoreHorizontal = createMockIcon('MoreHorizontal');