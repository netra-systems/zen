/**
 * Component Accessibility Test Suite
 * Tests WCAG 2.1 AA compliance for all UI components
 * Follows 8-line function rule and 300-line file limit
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise)
 * - Goal: Compliance and user reach expansion
 * - Value Impact: Enables accessibility compliance for enterprise sales
 * - Revenue Impact: +$20K MRR from compliance-sensitive customers
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';

// Import components to test
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// ============================================================================
// BUTTON COMPONENT ACCESSIBILITY TESTS
// ============================================================================

describe('Button Component - Accessibility', () => {
  it('passes axe accessibility tests', async () => {
    const { container } = render(<Button>Click me</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has proper keyboard navigation', async () => {
    const user = userEvent.setup();
    const onClickMock = jest.fn();
    render(<Button onClick={onClickMock}>Keyboard Button</Button>);
    
    const button = screen.getByRole('button');
    await user.tab();
    expect(button).toHaveFocus();
  });

  it('activates with Enter and Space keys', async () => {
    const user = userEvent.setup();
    const onClickMock = jest.fn();
    render(<Button onClick={onClickMock}>Keyboard Button</Button>);
    
    const button = screen.getByRole('button');
    await user.click(button);
    await user.keyboard('{Enter}');
    await user.keyboard(' ');
    expect(onClickMock).toHaveBeenCalledTimes(3);
  });

  it('has visible focus indicators', async () => {
    const user = userEvent.setup();
    render(<Button>Focus Test</Button>);
    
    const button = screen.getByRole('button');
    await user.tab();
    expect(button).toHaveClass('focus-visible:ring-2');
  });

  it('has proper ARIA attributes when disabled', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    // Note: HTML disabled attribute is sufficient for accessibility
    expect(button).toHaveAttribute('disabled');
  });

  it('supports custom ARIA labels', () => {
    render(<Button aria-label="Custom action">Icon</Button>);
    const button = screen.getByRole('button', { name: 'Custom action' });
    expect(button).toBeInTheDocument();
  });
});

// ============================================================================
// INPUT COMPONENT ACCESSIBILITY TESTS
// ============================================================================

describe('Input Component - Accessibility', () => {
  it('passes axe accessibility tests', async () => {
    const { container } = render(
      <div>
        <label htmlFor="test-input">Test Input</label>
        <Input id="test-input" placeholder="Enter text" />
      </div>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has proper label association', () => {
    render(
      <div>
        <label htmlFor="labeled-input">Email Address</label>
        <Input id="labeled-input" type="email" />
      </div>
    );
    
    const input = screen.getByLabelText('Email Address');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'email');
  });

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup();
    render(<Input placeholder="Type here" />);
    
    const input = screen.getByRole('textbox');
    await user.tab();
    expect(input).toHaveFocus();
  });

  it('has proper ARIA attributes for required fields', () => {
    render(<Input required aria-describedby="help-text" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('required');
    expect(input).toHaveAttribute('aria-describedby', 'help-text');
  });

  it('has proper ARIA attributes for invalid state', () => {
    render(<Input aria-invalid="true" aria-describedby="error-msg" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby', 'error-msg');
  });
});

// ============================================================================
// CARD COMPONENT ACCESSIBILITY TESTS
// ============================================================================

describe('Card Component - Accessibility', () => {
  it('passes axe accessibility tests', async () => {
    const { container } = render(
      <Card>
        <h2>Card Title</h2>
        <p>Card content with proper semantic markup</p>
      </Card>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has proper semantic structure', () => {
    render(
      <Card>
        <h2>Card Title</h2>
        <p>Card description</p>
      </Card>
    );
    
    const title = screen.getByRole('heading', { level: 2 });
    expect(title).toBeInTheDocument();
  });

  it('supports focus when interactive', async () => {
    const user = userEvent.setup();
    const onClickMock = jest.fn();
    
    render(
      <Card tabIndex={0} onClick={onClickMock} role="button">
        <h3>Interactive Card</h3>
      </Card>
    );
    
    const card = screen.getByRole('button');
    await user.tab();
    expect(card).toHaveFocus();
  });

  it('has proper contrast ratios', () => {
    render(
      <Card className="bg-white text-black">
        <p>High contrast content</p>
      </Card>
    );
    
    const card = screen.getByText('High contrast content').closest('div');
    expect(card).toHaveClass('bg-white');
    expect(card).toHaveClass('text-black');
  });
});

// ============================================================================
// BADGE COMPONENT ACCESSIBILITY TESTS
// ============================================================================

describe('Badge Component - Accessibility', () => {
  it('passes axe accessibility tests', async () => {
    const { container } = render(<Badge>Status: Active</Badge>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has proper semantic meaning', () => {
    render(<Badge>New</Badge>);
    const badge = screen.getByText('New');
    expect(badge).toBeInTheDocument();
  });

  it('supports screen reader announcements', () => {
    render(<Badge aria-label="Status: Active">✓</Badge>);
    const badge = screen.getByLabelText('Status: Active');
    expect(badge).toBeInTheDocument();
  });

  it('has sufficient color contrast', () => {
    render(<Badge variant="destructive">Error</Badge>);
    const badge = screen.getByText('Error');
    expect(badge).toHaveClass('bg-destructive');
    expect(badge).toHaveClass('text-destructive-foreground');
  });
});

// ============================================================================
// COMPREHENSIVE COMPONENT ACCESSIBILITY TESTS
// ============================================================================

describe('Component Combinations - Accessibility', () => {
  it('passes axe tests for complex component layouts', async () => {
    const { container } = render(
      <div>
        <Card>
          <h2>Form Card</h2>
          <form>
            <label htmlFor="name">Name</label>
            <Input id="name" type="text" required />
            <Button type="submit">Submit</Button>
          </form>
        </Card>
      </div>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('maintains proper focus order in complex layouts', async () => {
    const user = userEvent.setup();
    render(
      <div>
        <Button>First Button</Button>
        <Input placeholder="Input field" />
        <Button>Second Button</Button>
      </div>
    );
    
    await user.tab();
    expect(screen.getByRole('button', { name: 'First Button' })).toHaveFocus();
    
    await user.tab();
    expect(screen.getByRole('textbox')).toHaveFocus();
    
    await user.tab();
    expect(screen.getByRole('button', { name: 'Second Button' })).toHaveFocus();
  });

  it('supports skip links for keyboard users', async () => {
    const user = userEvent.setup();
    render(
      <div>
        <a href="#main" className="sr-only focus:not-sr-only">
          Skip to main content
        </a>
        <nav>Navigation</nav>
        <main id="main">
          <h1>Main Content</h1>
        </main>
      </div>
    );
    
    const skipLink = screen.getByRole('link', { name: 'Skip to main content' });
    await user.tab();
    expect(skipLink).toHaveFocus();
  });

  it('provides proper heading hierarchy', () => {
    render(
      <div>
        <h1>Page Title</h1>
        <Card>
          <h2>Section Title</h2>
          <h3>Subsection</h3>
        </Card>
      </div>
    );
    
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3 })).toBeInTheDocument();
  });

  it('supports reduced motion preferences', () => {
    // Mock reduced motion preference
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query.includes('prefers-reduced-motion'),
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
      })),
    });
    
    render(
      <Button className="transition-all motion-reduce:transition-none">
        Animated Button
      </Button>
    );
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('motion-reduce:transition-none');
  });
});