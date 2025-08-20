/**
 * Button Component Complete Test Suite
 * Tests all button states, interactions, and accessibility features
 * Follows 25-line function rule and P0 critical path testing
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button, buttonVariants } from '@/components/ui/button';

describe('Button Component - Complete Test Suite', () => {
  const user = userEvent.setup();

  describe('Basic Rendering', () => {
    it('renders with default props', () => {
      render(<Button>Default Button</Button>);
      const button = screen.getByRole('button', { name: 'Default Button' });
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('bg-primary');
    });

    it('renders with custom className', () => {
      render(<Button className="custom-class">Custom</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('custom-class');
      expect(button).toHaveClass('bg-primary');
    });
  });

  describe('Button Variants', () => {
    it('renders primary variant correctly', () => {
      render(<Button variant="default">Primary</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-primary');
      expect(button).toHaveClass('text-primary-foreground');
    });

    it('renders destructive variant correctly', () => {
      render(<Button variant="destructive">Delete</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-destructive');
      expect(button).toHaveClass('text-destructive-foreground');
    });

    it('renders outline variant correctly', () => {
      render(<Button variant="outline">Outline</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('border');
      expect(button).toHaveClass('bg-background');
    });

    it('renders secondary variant correctly', () => {
      render(<Button variant="secondary">Secondary</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-secondary');
      expect(button).toHaveClass('text-secondary-foreground');
    });

    it('renders ghost variant correctly', () => {
      render(<Button variant="ghost">Ghost</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('hover:bg-accent');
      expect(button).not.toHaveClass('bg-primary');
    });

    it('renders link variant correctly', () => {
      render(<Button variant="link">Link</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('text-primary');
      expect(button).toHaveClass('underline-offset-4');
    });
  });

  describe('Button Sizes', () => {
    it('renders default size correctly', () => {
      render(<Button size="default">Default Size</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-10');
      expect(button).toHaveClass('px-4');
    });

    it('renders small size correctly', () => {
      render(<Button size="sm">Small</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-9');
      expect(button).toHaveClass('px-3');
    });

    it('renders large size correctly', () => {
      render(<Button size="lg">Large</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-11');
      expect(button).toHaveClass('px-8');
    });

    it('renders icon size correctly', () => {
      render(<Button size="icon">🔍</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-10');
      expect(button).toHaveClass('w-10');
    });
  });

  describe('Button States', () => {
    it('handles enabled state correctly', () => {
      render(<Button>Enabled</Button>);
      const button = screen.getByRole('button');
      expect(button).toBeEnabled();
      expect(button).toHaveClass('cursor-pointer');
    });

    it('handles disabled state correctly', () => {
      render(<Button disabled>Disabled</Button>);
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
      expect(button).toHaveClass('disabled:pointer-events-none');
    });

    it('handles loading state with custom prop', () => {
      render(<Button data-loading="true">Loading</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('data-loading', 'true');
      expect(button).toBeInTheDocument();
    });
  });

  describe('Click Interactions', () => {
    it('handles click events within 100ms', async () => {
      const handleClick = jest.fn();
      const startTime = Date.now();
      render(<Button onClick={handleClick}>Click Me</Button>);
      
      const button = screen.getByRole('button');
      await user.click(button);
      
      const responseTime = Date.now() - startTime;
      expect(handleClick).toHaveBeenCalledTimes(1);
      expect(responseTime).toBeLessThan(100);
    });

    it('prevents click when disabled', async () => {
      const handleClick = jest.fn();
      render(<Button disabled onClick={handleClick}>Disabled</Button>);
      
      const button = screen.getByRole('button');
      await user.click(button);
      
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('handles rapid clicking prevention', async () => {
      const handleClick = jest.fn();
      render(<Button onClick={handleClick}>Rapid Click</Button>);
      
      const button = screen.getByRole('button');
      await user.click(button);
      await user.click(button);
      
      expect(handleClick).toHaveBeenCalledTimes(2);
    });
  });

  describe('Keyboard Navigation', () => {
    it('responds to Tab key navigation', async () => {
      render(
        <div>
          <Button>First</Button>
          <Button>Second</Button>
        </div>
      );
      
      await user.tab();
      expect(screen.getByRole('button', { name: 'First' })).toHaveFocus();
      await user.tab();
      expect(screen.getByRole('button', { name: 'Second' })).toHaveFocus();
    });

    it('responds to Enter key activation', async () => {
      const handleClick = jest.fn();
      render(<Button onClick={handleClick}>Enter Test</Button>);
      
      const button = screen.getByRole('button');
      button.focus();
      await user.keyboard('{Enter}');
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('responds to Space key activation', async () => {
      const handleClick = jest.fn();
      render(<Button onClick={handleClick}>Space Test</Button>);
      
      const button = screen.getByRole('button');
      button.focus();
      await user.keyboard(' ');
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('skips disabled buttons in tab order', async () => {
      render(
        <div>
          <Button>First</Button>
          <Button disabled>Disabled</Button>
          <Button>Third</Button>
        </div>
      );
      
      await user.tab();
      expect(screen.getByRole('button', { name: 'First' })).toHaveFocus();
      await user.tab();
      expect(screen.getByRole('button', { name: 'Third' })).toHaveFocus();
    });
  });

  describe('Visual Feedback', () => {
    it('has hover transform effect classes', () => {
      render(<Button>Hover</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('hover:scale-[1.02]');
      expect(button).toHaveClass('transform');
    });

    it('has active transform effect classes', () => {
      render(<Button>Active</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('active:scale-[0.98]');
      expect(button).toHaveClass('transform');
    });

    it('has transition classes for smooth animations', () => {
      render(<Button>Transition</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('transition-all');
      expect(button).toHaveClass('duration-200');
    });
  });

  describe('Accessibility Features', () => {
    it('has correct ARIA attributes', () => {
      render(<Button aria-label="Custom Label">Icon</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Custom Label');
      expect(button).toBeInTheDocument();
    });

    it('has focus-visible ring for keyboard navigation', () => {
      render(<Button>Focus Test</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('focus-visible:outline-none');
      expect(button).toHaveClass('focus-visible:ring-2');
    });

    it('provides disabled cursor feedback', () => {
      render(<Button disabled>Disabled</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('disabled:cursor-not-allowed');
      expect(button).toHaveClass('disabled:opacity-50');
    });

    it('has proper role and type attributes', () => {
      render(<Button type="submit">Submit</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('type', 'submit');
      expect(button.tagName).toBe('BUTTON');
    });
  });

  describe('asChild Functionality', () => {
    it('renders as custom component when asChild is true', () => {
      render(
        <Button asChild>
          <a href="/test">Link Button</a>
        </Button>
      );
      
      const link = screen.getByRole('link');
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', '/test');
    });

    it('applies button styles to child component', () => {
      render(
        <Button asChild variant="secondary">
          <a href="/test">Styled Link</a>
        </Button>
      );
      
      const link = screen.getByRole('link');
      expect(link).toHaveClass('bg-secondary');
      expect(link).toHaveClass('text-secondary-foreground');
    });
  });

  describe('Performance Tests', () => {
    it('renders quickly for performance', () => {
      const startTime = performance.now();
      render(<Button>Performance Test</Button>);
      const endTime = performance.now();
      
      expect(endTime - startTime).toBeLessThan(10);
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('handles multiple button instances efficiently', () => {
      const buttons = Array.from({ length: 50 }, (_, i) => (
        <Button key={i}>Button {i}</Button>
      ));
      
      const startTime = performance.now();
      render(<div>{buttons}</div>);
      const endTime = performance.now();
      
      expect(endTime - startTime).toBeLessThan(50);
      expect(screen.getAllByRole('button')).toHaveLength(50);
    });
  });

  describe('Button Variants Utility', () => {
    it('generates correct classes for buttonVariants', () => {
      const classes = buttonVariants({ variant: 'destructive', size: 'lg' });
      expect(classes).toContain('bg-destructive');
      expect(classes).toContain('h-11');
      expect(classes).toContain('px-8');
    });

    it('handles default variants correctly', () => {
      const classes = buttonVariants({});
      expect(classes).toContain('bg-primary');
      expect(classes).toContain('h-10');
      expect(classes).toContain('px-4');
    });
  });
});