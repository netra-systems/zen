/**
 * UI Components Accessibility Test Suite
 * Tests Card, Badge, and other UI component accessibility compliance
 * Follows 25-line function rule and 450-line file limit
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise)
 * - Goal: Compliance and user reach expansion for UI components
 * - Value Impact: Enables accessibility compliance for enterprise sales
 * - Revenue Impact: +$20K MRR from compliance-sensitive customers
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import components to test
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

// Import shared accessibility helpers
import { 
  runAxeTest, 
  setupKeyboardTest,
  testColorContrast,
  testHeadingHierarchy
} from './shared-a11y-helpers';

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
    await runAxeTest(container);
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
    const user = setupKeyboardTest();
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
    testColorContrast(card!, ['bg-white', 'text-black']);
  });

  it('supports card with header and footer sections', () => {
    render(
      <Card>
        <header>
          <h3>Card Header</h3>
          <p>Subtitle</p>
        </header>
        <main>
          <p>Main card content</p>
        </main>
        <footer>
          <Button>Action</Button>
        </footer>
      </Card>
    );
    
    const header = screen.getByRole('banner');
    const main = screen.getByRole('main');
    const footer = screen.getByRole('contentinfo');
    
    expect(header).toBeInTheDocument();
    expect(main).toBeInTheDocument();
    expect(footer).toBeInTheDocument();
  });

  it('handles card as clickable container', async () => {
    const user = setupKeyboardTest();
    const onClickMock = jest.fn();
    
    render(
      <Card 
        as="button"
        onClick={onClickMock}
        className="cursor-pointer hover:bg-gray-50"
        aria-describedby="card-description"
      >
        <h3>Clickable Card</h3>
        <p id="card-description">Click to view details</p>
      </Card>
    );
    
    const card = screen.getByRole('button');
    await user.click(card);
    expect(onClickMock).toHaveBeenCalled();
  });

  it('supports card with image and proper alt text', () => {
    render(
      <Card>
        <img 
          src="/placeholder.jpg" 
          alt="Product showcase image" 
          className="w-full h-48 object-cover"
        />
        <div className="p-4">
          <h3>Product Name</h3>
          <p>Product description</p>
        </div>
      </Card>
    );
    
    const image = screen.getByRole('img', { name: 'Product showcase image' });
    expect(image).toHaveAttribute('alt', 'Product showcase image');
  });

  it('handles nested interactive elements appropriately', async () => {
    const user = setupKeyboardTest();
    render(
      <Card>
        <h3>Card with Actions</h3>
        <p>Card content</p>
        <div className="flex gap-2">
          <Button>Primary Action</Button>
          <Button variant="outline">Secondary Action</Button>
        </div>
      </Card>
    );
    
    await user.tab();
    expect(screen.getByRole('button', { name: 'Primary Action' })).toHaveFocus();
    
    await user.tab();
    expect(screen.getByRole('button', { name: 'Secondary Action' })).toHaveFocus();
  });

  it('supports card variants with proper styling', () => {
    const variants = ['default', 'outline', 'ghost'];
    
    variants.forEach(variant => {
      const { unmount } = render(
        <Card variant={variant as any}>
          <h3>{variant} Card</h3>
        </Card>
      );
      
      const heading = screen.getByRole('heading', { name: `${variant} Card` });
      expect(heading).toBeInTheDocument();
      unmount();
    });
  });

  it('handles card loading states', () => {
    render(
      <Card aria-busy="true" aria-describedby="loading-message">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        </div>
        <div id="loading-message" className="sr-only">
          Loading card content
        </div>
      </Card>
    );
    
    const card = screen.getByText('Loading card content').closest('[aria-busy="true"]');
    expect(card).toHaveAttribute('aria-busy', 'true');
  });

  it('supports expandable cards with proper ARIA', async () => {
    const user = setupKeyboardTest();
    const ExpandableCard = () => {
      const [isExpanded, setIsExpanded] = React.useState(false);
      
      return (
        <Card>
          <Button
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            aria-controls="card-content"
          >
            {isExpanded ? 'Collapse' : 'Expand'} Details
          </Button>
          {isExpanded && (
            <div id="card-content">
              <p>Expanded card content</p>
            </div>
          )}
        </Card>
      );
    };
    
    render(<ExpandableCard />);
    const button = screen.getByRole('button', { name: 'Expand Details' });
    
    expect(button).toHaveAttribute('aria-expanded', 'false');
    
    await user.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Expanded card content')).toBeInTheDocument();
  });
});

// ============================================================================
// BADGE COMPONENT ACCESSIBILITY TESTS
// ============================================================================

describe('Badge Component - Accessibility', () => {
  it('passes axe accessibility tests', async () => {
    const { container } = render(<Badge>Status: Active</Badge>);
    await runAxeTest(container);
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
    testColorContrast(badge, ['bg-destructive', 'text-destructive-foreground']);
  });

  it('supports different badge variants with accessibility', () => {
    const variants = [
      { variant: 'default', text: 'Default' },
      { variant: 'secondary', text: 'Secondary' },
      { variant: 'destructive', text: 'Error' },
      { variant: 'outline', text: 'Outline' }
    ];
    
    variants.forEach(({ variant, text }) => {
      const { unmount } = render(
        <Badge variant={variant as any}>{text}</Badge>
      );
      
      const badge = screen.getByText(text);
      expect(badge).toBeInTheDocument();
      unmount();
    });
  });

  it('handles interactive badges appropriately', async () => {
    const user = setupKeyboardTest();
    const onClickMock = jest.fn();
    
    render(
      <Badge 
        as="button"
        onClick={onClickMock}
        aria-label="Remove tag: JavaScript"
      >
        JavaScript ✕
      </Badge>
    );
    
    const badge = screen.getByRole('button', { name: 'Remove tag: JavaScript' });
    await user.click(badge);
    expect(onClickMock).toHaveBeenCalled();
  });

  it('supports notification badges with counts', () => {
    render(
      <div className="relative">
        <Button>Messages</Button>
        <Badge 
          className="absolute -top-2 -right-2"
          aria-label="3 unread messages"
        >
          3
        </Badge>
      </div>
    );
    
    const badge = screen.getByLabelText('3 unread messages');
    expect(badge).toHaveTextContent('3');
  });

  it('handles status badges with proper semantics', () => {
    const statuses = [
      { status: 'online', color: 'green', label: 'User is online' },
      { status: 'offline', color: 'gray', label: 'User is offline' },
      { status: 'busy', color: 'red', label: 'User is busy' },
      { status: 'away', color: 'yellow', label: 'User is away' }
    ];
    
    statuses.forEach(({ status, label }) => {
      const { unmount } = render(
        <div className="flex items-center gap-2">
          <Badge variant="outline" aria-label={label}>
            {status}
          </Badge>
          <span>John Doe</span>
        </div>
      );
      
      const badge = screen.getByLabelText(label);
      expect(badge).toBeInTheDocument();
      unmount();
    });
  });

  it('supports progress badges with ARIA attributes', () => {
    render(
      <Badge 
        role="status"
        aria-label="Task completion: 75%"
        className="bg-blue-100 text-blue-800"
      >
        75% Complete
      </Badge>
    );
    
    const badge = screen.getByRole('status', { name: 'Task completion: 75%' });
    expect(badge).toBeInTheDocument();
  });

  it('handles badge groups with proper navigation', async () => {
    const user = setupKeyboardTest();
    render(
      <div role="group" aria-label="Selected tags">
        <Badge as="button" aria-label="Remove tag: React">
          React ✕
        </Badge>
        <Badge as="button" aria-label="Remove tag: TypeScript">
          TypeScript ✕
        </Badge>
        <Badge as="button" aria-label="Remove tag: Testing">
          Testing ✕
        </Badge>
      </div>
    );
    
    const group = screen.getByRole('group', { name: 'Selected tags' });
    expect(group).toBeInTheDocument();
    
    await user.tab();
    expect(screen.getByRole('button', { name: 'Remove tag: React' })).toHaveFocus();
  });

  it('supports badge tooltips for additional context', () => {
    render(
      <Badge 
        aria-describedby="badge-tooltip"
        className="cursor-help"
      >
        Pro
        <div id="badge-tooltip" role="tooltip" className="sr-only">
          Premium subscription feature
        </div>
      </Badge>
    );
    
    const badge = screen.getByText('Pro');
    expect(badge).toHaveAttribute('aria-describedby', 'badge-tooltip');
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('handles animated badges with reduced motion support', () => {
    render(
      <Badge className="animate-pulse motion-reduce:animate-none">
        Live
      </Badge>
    );
    
    const badge = screen.getByText('Live');
    expect(badge).toHaveClass('motion-reduce:animate-none');
  });
});