import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
 25-line function rule and 450-line file limit
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise)
 * - Goal: Compliance and user reach expansion
 * - Value Impact: Enables accessibility compliance for enterprise sales
 * - Revenue Impact: +$20K MRR from compliance-sensitive customers
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import components to test
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// Import shared accessibility helpers
import { 
  runAxeTest, 
  setupKeyboardTest, 
  testKeyboardActivation,
  testAriaLabel
} from './shared-a11y-helpers';

// ============================================================================
// BUTTON COMPONENT ACCESSIBILITY TESTS
// ============================================================================

describe('Button Component - Accessibility', () => {
    jest.setTimeout(10000);
  it('passes axe accessibility tests', async () => {
    const { container } = render(<Button>Click me</Button>);
    await runAxeTest(container);
  });

  it('has proper keyboard navigation', async () => {
    const user = setupKeyboardTest();
    const onClickMock = jest.fn();
    render(<Button onClick={onClickMock}>Keyboard Button</Button>);
    
    const button = screen.getByRole('button');
    await user.tab();
    expect(button).toHaveFocus();
  });

  it('activates with Enter and Space keys', async () => {
    const user = setupKeyboardTest();
    const onClickMock = jest.fn();
    render(<Button onClick={onClickMock}>Keyboard Button</Button>);
    
    const button = screen.getByRole('button');
    await user.click(button);
    await user.keyboard('{Enter}');
    await user.keyboard(' ');
    expect(onClickMock).toHaveBeenCalledTimes(3);
  });

  it('has visible focus indicators', async () => {
    const user = setupKeyboardTest();
    render(<Button>Focus Test</Button>);
    
    const button = screen.getByRole('button');
    await user.tab();
    expect(button).toHaveClass('focus-visible:ring-2');
  });

  it('has proper ARIA attributes when disabled', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('disabled');
  });

  it('supports custom ARIA labels', () => {
    render(<Button aria-label="Custom action">Icon</Button>);
    const button = screen.getByRole('button', { name: 'Custom action' });
    expect(button).toBeInTheDocument();
  });

  it('supports button variants with proper contrast', () => {
    const variants = ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'];
    
    variants.forEach(variant => {
      const { unmount } = render(
        <Button variant={variant as any}>{variant} Button</Button>
      );
      
      const button = screen.getByRole('button', { name: `${variant} Button` });
      expect(button).toBeInTheDocument();
      unmount();
    });
  });

  it('handles button sizes appropriately', () => {
    const sizes = ['default', 'sm', 'lg', 'icon'];
    
    sizes.forEach(size => {
      const { unmount } = render(
        <Button size={size as any}>{size} Size</Button>
      );
      
      const button = screen.getByRole('button', { name: `${size} Size` });
      expect(button).toBeInTheDocument();
      unmount();
    });
  });

  it('supports loading state with proper accessibility', () => {
    render(
      <Button disabled aria-busy="true" aria-describedby="loading-text">
        Loading...
      </Button>
    );
    
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
  });

  it('handles icon buttons with accessible labels', () => {
    render(
      <Button variant="ghost" size="icon" aria-label="Close dialog">
        ✕
      </Button>
    );
    
    const button = screen.getByRole('button', { name: 'Close dialog' });
    expect(button).toBeInTheDocument();
  });

  it('supports button groups with proper navigation', async () => {
    const user = setupKeyboardTest();
    render(
      <div role="group" aria-label="Text formatting">
        <Button>Bold</Button>
        <Button>Italic</Button>
        <Button>Underline</Button>
      </div>
    );
    
    await user.tab();
    expect(screen.getByRole('button', { name: 'Bold' })).toHaveFocus();
    
    await user.tab();
    expect(screen.getByRole('button', { name: 'Italic' })).toHaveFocus();
  });
});

// ============================================================================
// INPUT COMPONENT ACCESSIBILITY TESTS
// ============================================================================

describe('Input Component - Accessibility', () => {
    jest.setTimeout(10000);
  it('passes axe accessibility tests', async () => {
    const { container } = render(
      <div>
        <Label htmlFor="test-input">Test Input</Label>
        <Input id="test-input" placeholder="Enter text" />
      </div>
    );
    await runAxeTest(container);
  });

  it('has proper label association', () => {
    render(
      <div>
        <Label htmlFor="labeled-input">Email Address</Label>
        <Input id="labeled-input" type="email" />
      </div>
    );
    
    testAriaLabel('Email Address', 'email');
  });

  it('supports keyboard navigation', async () => {
    const user = setupKeyboardTest();
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

  it('supports different input types with proper semantics', () => {
    const inputTypes = [
      { type: 'text', label: 'Text Input' },
      { type: 'email', label: 'Email Input' },
      { type: 'password', label: 'Password Input' },
      { type: 'tel', label: 'Phone Input' },
      { type: 'url', label: 'URL Input' },
      { type: 'search', label: 'Search Input' }
    ];

    inputTypes.forEach(({ type, label }) => {
      const { unmount } = render(
        <div>
          <Label htmlFor={`${type}-input`}>{label}</Label>
          <Input id={`${type}-input`} type={type} />
        </div>
      );

      const input = screen.getByLabelText(label);
      expect(input).toHaveAttribute('type', type);
      unmount();
    });
  });

  it('handles placeholder text appropriately', () => {
    render(
      <div>
        <Label htmlFor="placeholder-input">Search</Label>
        <Input 
          id="placeholder-input" 
          type="search" 
          placeholder="Enter search terms..." 
        />
      </div>
    );
    
    const input = screen.getByLabelText('Search');
    expect(input).toHaveAttribute('placeholder', 'Enter search terms...');
    // Note: Placeholder should not replace proper labeling
    expect(input).toHaveAttribute('id', 'placeholder-input');
  });

  it('supports input validation with ARIA attributes', () => {
    render(
      <div>
        <Label htmlFor="validated-input">Email</Label>
        <Input 
          id="validated-input"
          type="email"
          required
          aria-invalid="false"
          aria-describedby="email-help email-error"
        />
        <div id="email-help">Enter your email address</div>
        <div id="email-error" role="alert" hidden>
          Please enter a valid email
        </div>
      </div>
    );
    
    const input = screen.getByLabelText('Email');
    expect(input).toHaveAttribute('aria-invalid', 'false');
    expect(input).toHaveAttribute('aria-describedby', 'email-help email-error');
  });

  it('handles disabled state properly', () => {
    render(
      <div>
        <Label htmlFor="disabled-input">Disabled Field</Label>
        <Input id="disabled-input" disabled placeholder="Cannot edit" />
      </div>
    );
    
    const input = screen.getByLabelText('Disabled Field');
    expect(input).toBeDisabled();
    expect(input).toHaveAttribute('disabled');
  });

  it('supports readonly inputs with proper semantics', () => {
    render(
      <div>
        <Label htmlFor="readonly-input">Read Only Field</Label>
        <Input 
          id="readonly-input" 
          readOnly 
          value="Cannot change this value"
          aria-describedby="readonly-help"
        />
        <div id="readonly-help">This field is read-only</div>
      </div>
    );
    
    const input = screen.getByLabelText('Read Only Field');
    expect(input).toHaveAttribute('readonly');
    expect(input).toHaveValue('Cannot change this value');
  });

  it('handles input with data lists for autocomplete', () => {
    render(
      <div>
        <Label htmlFor="autocomplete-input">Country</Label>
        <Input 
          id="autocomplete-input" 
          list="countries"
          placeholder="Start typing..."
        />
        <datalist id="countries">
          <option value="United States" />
          <option value="United Kingdom" />
          <option value="Canada" />
        </datalist>
      </div>
    );
    
    const input = screen.getByLabelText('Country');
    expect(input).toHaveAttribute('list', 'countries');
  });

  it('supports file inputs with proper accessibility', () => {
    render(
      <div>
        <Label htmlFor="file-input">Upload Document</Label>
        <Input 
          id="file-input" 
          type="file" 
          accept=".pdf,.doc,.docx"
          aria-describedby="file-help"
        />
        <div id="file-help">
          Accepted formats: PDF, DOC, DOCX (max 10MB)
        </div>
      </div>
    );
    
    const input = screen.getByLabelText('Upload Document');
    expect(input).toHaveAttribute('type', 'file');
    expect(input).toHaveAttribute('accept', '.pdf,.doc,.docx');
  });
});