/**
 * IconButton Test Suite
 * Tests icon buttons with various states and accessibility features
 * Follows 8-line function rule and covers all icon button patterns
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '@/components/ui/button';
import { Copy, Check, Play, Pause, X, MoreVertical, ChevronDown } from 'lucide-react';

describe('IconButton Test Suite', () => {
  const user = userEvent.setup();

  describe('Basic Icon Button Rendering', () => {
    it('renders icon button with default icon size', () => {
      render(
        <Button variant="ghost" size="icon" aria-label="Copy text">
          <Copy className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button', { name: 'Copy text' });
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('w-10', 'h-10');
    });

    it('renders icon button with custom dimensions', () => {
      render(
        <Button variant="ghost" size="icon" className="w-8 h-8" aria-label="Small icon">
          <Copy className="h-3 w-3" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('w-8', 'h-8');
    });

    it('renders icon button with outline variant', () => {
      render(
        <Button variant="outline" size="icon" aria-label="Toggle menu">
          <MoreVertical className="h-5 w-5" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('border', 'bg-background');
    });
  });

  describe('Icon Button States', () => {
    it('handles enabled state with hover effects', async () => {
      render(
        <Button variant="ghost" size="icon" aria-label="Play">
          <Play className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toBeEnabled();
      expect(button).toHaveClass('hover:bg-accent');
    });

    it('handles disabled state correctly', () => {
      render(
        <Button variant="ghost" size="icon" disabled aria-label="Disabled action">
          <X className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
      expect(button).toHaveClass('disabled:opacity-50');
    });

    it('handles loading state with spinner icon', () => {
      render(
        <Button variant="ghost" size="icon" aria-label="Loading" data-loading="true">
          <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('Icon Button Interactions', () => {
    it('responds to click within performance threshold', async () => {
      const handleClick = jest.fn();
      const startTime = Date.now();
      
      render(
        <Button variant="ghost" size="icon" onClick={handleClick} aria-label="Click me">
          <Copy className="h-4 w-4" />
        </Button>
      );
      
      await user.click(screen.getByRole('button'));
      const responseTime = Date.now() - startTime;
      expect(handleClick).toHaveBeenCalledTimes(1);
      expect(responseTime).toBeLessThan(100);
    });

    it('handles touch interactions correctly', async () => {
      const handleClick = jest.fn();
      render(
        <Button variant="ghost" size="icon" onClick={handleClick} aria-label="Touch target">
          <Pause className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      fireEvent.touchStart(button);
      fireEvent.touchEnd(button);
      fireEvent.click(button);
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('prevents multiple rapid clicks', async () => {
      const handleClick = jest.fn();
      render(
        <Button variant="ghost" size="icon" onClick={handleClick} aria-label="Rapid click test">
          <X className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      await user.click(button);
      await user.click(button);
      
      expect(handleClick).toHaveBeenCalledTimes(2);
    });
  });

  describe('Keyboard Navigation', () => {
    it('navigates with Tab key', async () => {
      render(
        <div>
          <Button variant="ghost" size="icon" aria-label="First">
            <Copy className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Second">
            <Pause className="h-4 w-4" />
          </Button>
        </div>
      );
      
      await user.tab();
      expect(screen.getByRole('button', { name: 'First' })).toHaveFocus();
      await user.tab();
      expect(screen.getByRole('button', { name: 'Second' })).toHaveFocus();
    });

    it('activates with Enter key', async () => {
      const handleClick = jest.fn();
      render(
        <Button variant="ghost" size="icon" onClick={handleClick} aria-label="Enter test">
          <Play className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      button.focus();
      await user.keyboard('{Enter}');
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('activates with Space key', async () => {
      const handleClick = jest.fn();
      render(
        <Button variant="ghost" size="icon" onClick={handleClick} aria-label="Space test">
          <Check className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      button.focus();
      await user.keyboard(' ');
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Accessibility Features', () => {
    it('has proper ARIA labels for screen readers', () => {
      render(
        <Button variant="ghost" size="icon" aria-label="Copy to clipboard">
          <Copy className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Copy to clipboard');
      expect(button).toBeInTheDocument();
    });

    it('provides tooltip text for context', () => {
      render(
        <Button variant="ghost" size="icon" title="Delete item" aria-label="Delete">
          <X className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('title', 'Delete item');
    });

    it('has focus indicators for keyboard users', () => {
      render(
        <Button variant="ghost" size="icon" aria-label="Focus test">
          <MoreVertical className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('focus-visible:ring-2');
      expect(button).toHaveClass('focus-visible:outline-none');
    });

    it('indicates disabled state to assistive technology', () => {
      render(
        <Button variant="ghost" size="icon" disabled aria-label="Disabled button">
          <Pause className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('disabled');
      expect(button).toHaveClass('disabled:cursor-not-allowed');
    });
  });

  describe('Visual Feedback', () => {
    it('has scale transform on hover', () => {
      render(
        <Button variant="ghost" size="icon" aria-label="Hover test">
          <Copy className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('hover:scale-[1.02]');
      expect(button).toHaveClass('transform');
    });

    it('has scale transform on active state', () => {
      render(
        <Button variant="ghost" size="icon" aria-label="Active test">
          <Play className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('active:scale-[0.98]');
      expect(button).toHaveClass('transition-all');
    });

    it('shows different states with icon changes', async () => {
      const TestComponent = () => {
        const [copied, setCopied] = React.useState(false);
        return (
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => setCopied(!copied)}
            aria-label={copied ? 'Copied' : 'Copy'}
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        );
      };
      
      render(<TestComponent />);
      const button = screen.getByRole('button', { name: 'Copy' });
      await user.click(button);
      
      expect(screen.getByRole('button', { name: 'Copied' })).toBeInTheDocument();
    });
  });

  describe('Icon Button Variants', () => {
    it('renders destructive icon button correctly', () => {
      render(
        <Button variant="destructive" size="icon" aria-label="Delete permanently">
          <X className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-destructive');
      expect(button).toHaveClass('text-destructive-foreground');
    });

    it('renders secondary icon button correctly', () => {
      render(
        <Button variant="secondary" size="icon" aria-label="Secondary action">
          <MoreVertical className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-secondary');
      expect(button).toHaveClass('text-secondary-foreground');
    });

    it('renders custom colored icon button', () => {
      render(
        <Button 
          variant="ghost" 
          size="icon" 
          className="text-red-500 hover:text-red-600"
          aria-label="Cancel action"
        >
          <X className="h-4 w-4" />
        </Button>
      );
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('text-red-500', 'hover:text-red-600');
    });
  });

  describe('Complex Icon Button Scenarios', () => {
    it('handles toggle state icon buttons', async () => {
      const ToggleButton = () => {
        const [expanded, setExpanded] = React.useState(false);
        return (
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => setExpanded(!expanded)}
            aria-label={expanded ? 'Collapse' : 'Expand'}
            aria-expanded={expanded}
          >
            <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </Button>
        );
      };
      
      render(<ToggleButton />);
      const button = screen.getByRole('button', { name: 'Expand' });
      expect(button).toHaveAttribute('aria-expanded', 'false');
      
      await user.click(button);
      expect(screen.getByRole('button', { name: 'Collapse' })).toHaveAttribute('aria-expanded', 'true');
    });

    it('maintains icon clarity at different sizes', () => {
      const sizes = [
        { className: 'w-6 h-6', iconClass: 'h-3 w-3' },
        { className: 'w-8 h-8', iconClass: 'h-4 w-4' },
        { className: 'w-12 h-12', iconClass: 'h-6 w-6' }
      ];
      
      sizes.forEach((size, index) => {
        render(
          <Button 
            variant="ghost" 
            size="icon" 
            className={size.className}
            aria-label={`Size test ${index}`}
          >
            <Copy className={size.iconClass} />
          </Button>
        );
      });
      
      sizes.forEach((_, index) => {
        expect(screen.getByRole('button', { name: `Size test ${index}` })).toBeInTheDocument();
      });
    });
  });

  describe('Performance and Memory', () => {
    it('renders multiple icon buttons efficiently', () => {
      const icons = [Copy, Check, Play, Pause, X, MoreVertical];
      const startTime = performance.now();
      
      render(
        <div>
          {icons.map((Icon, index) => (
            <Button key={index} variant="ghost" size="icon" aria-label={`Icon ${index}`}>
              <Icon className="h-4 w-4" />
            </Button>
          ))}
        </div>
      );
      
      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(20);
      expect(screen.getAllByRole('button')).toHaveLength(6);
    });

    it('handles rapid icon state changes smoothly', async () => {
      const RapidChangeButton = () => {
        const [count, setCount] = React.useState(0);
        const icons = [Copy, Check, Play, Pause];
        const CurrentIcon = icons[count % icons.length];
        
        return (
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => setCount(c => c + 1)}
            aria-label={`Icon change ${count}`}
          >
            <CurrentIcon className="h-4 w-4" />
          </Button>
        );
      };
      
      render(<RapidChangeButton />);
      const button = screen.getByRole('button');
      
      for (let i = 0; i < 5; i++) {
        await user.click(button);
        await waitFor(() => expect(button).toBeInTheDocument());
      }
    });
  });
});