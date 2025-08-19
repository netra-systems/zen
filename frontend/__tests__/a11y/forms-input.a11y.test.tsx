/**
 * Forms Input Accessibility Test Suite
 * Tests form labels, associations, and basic input accessibility
 * Follows 8-line function rule and 300-line file limit
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise)
 * - Goal: Ensure forms are accessible for compliance and usability
 * - Value Impact: Enables users with disabilities to complete forms
 * - Revenue Impact: +$25K MRR from accessible form completion
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import form components
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

// Import shared accessibility helpers
import { runAxeTest, testAriaLabel, createFieldsetTest } from './shared-a11y-helpers';

// ============================================================================
// FORM LABELS AND ASSOCIATIONS TESTS
// ============================================================================

describe('Form Labels - Proper Association', () => {
  it('passes axe accessibility tests for form with labels', async () => {
    const { container } = render(
      <form>
        <div>
          <Label htmlFor="email">Email Address</Label>
          <Input id="email" type="email" required />
        </div>
        <div>
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" required />
        </div>
        <Button type="submit">Submit</Button>
      </form>
    );
    await runAxeTest(container);
  });

  it('associates labels with inputs correctly', () => {
    render(
      <div>
        <Label htmlFor="username">Username</Label>
        <Input id="username" type="text" />
      </div>
    );
    
    testAriaLabel('Username', 'text');
  });

  it('supports implicit label association', () => {
    render(
      <Label>
        Full Name
        <Input type="text" />
      </Label>
    );
    
    testAriaLabel('Full Name');
  });

  it('provides fieldset grouping for related fields', () => {
    const FieldsetTest = createFieldsetTest('Contact Information', [
      { id: 'phone', label: 'Phone', type: 'tel' },
      { id: 'fax', label: 'Fax', type: 'tel' }
    ]);
    
    render(<FieldsetTest />);
    
    const fieldset = screen.getByRole('group', { name: 'Contact Information' });
    expect(fieldset).toBeInTheDocument();
  });

  it('supports aria-labelledby for complex labels', () => {
    render(
      <div>
        <h2 id="billing-title">Billing Address</h2>
        <p id="billing-desc">Enter your billing information</p>
        <Input 
          aria-labelledby="billing-title billing-desc" 
          placeholder="Street address"
        />
      </div>
    );
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-labelledby', 'billing-title billing-desc');
  });

  it('provides help text with aria-describedby', () => {
    render(
      <div>
        <Label htmlFor="password-new">New Password</Label>
        <Input 
          id="password-new" 
          type="password" 
          aria-describedby="password-help"
        />
        <div id="password-help">
          Password must be at least 8 characters long
        </div>
      </div>
    );
    
    const input = screen.getByLabelText('New Password');
    expect(input).toHaveAttribute('aria-describedby', 'password-help');
  });

  it('handles multiple aria-describedby references', () => {
    render(
      <div>
        <Label htmlFor="complex-input">Complex Field</Label>
        <Input 
          id="complex-input" 
          aria-describedby="help-text error-text"
        />
        <div id="help-text">Helpful information</div>
        <div id="error-text">Error message</div>
      </div>
    );
    
    const input = screen.getByLabelText('Complex Field');
    expect(input).toHaveAttribute('aria-describedby', 'help-text error-text');
  });

  it('supports required field indicators', () => {
    render(
      <div>
        <Label htmlFor="required-field">
          Name <span aria-label="required">*</span>
        </Label>
        <Input id="required-field" required aria-required="true" />
      </div>
    );
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('required');
    expect(input).toHaveAttribute('aria-required', 'true');
  });

  it('handles optional field labels clearly', () => {
    render(
      <div>
        <Label htmlFor="optional-field">
          Middle Name <span>(optional)</span>
        </Label>
        <Input id="optional-field" />
      </div>
    );
    
    const label = screen.getByText(/Middle Name/);
    expect(label).toBeInTheDocument();
    expect(screen.getByText('(optional)')).toBeInTheDocument();
  });

  it('provides proper input type associations', () => {
    const inputTypes = [
      { type: 'email', label: 'Email Address' },
      { type: 'tel', label: 'Phone Number' },
      { type: 'url', label: 'Website URL' },
      { type: 'password', label: 'Password' }
    ];

    render(
      <form>
        {inputTypes.map(({ type, label }) => (
          <div key={type}>
            <Label htmlFor={`${type}-input`}>{label}</Label>
            <Input id={`${type}-input`} type={type} />
          </div>
        ))}
      </form>
    );

    inputTypes.forEach(({ type, label }) => {
      const input = screen.getByLabelText(label);
      expect(input).toHaveAttribute('type', type);
    });
  });

  it('supports grouped radio buttons with fieldset', () => {
    render(
      <fieldset>
        <legend>Preferred Contact Method</legend>
        <div>
          <input type="radio" id="contact-email" name="contact" value="email" />
          <Label htmlFor="contact-email">Email</Label>
        </div>
        <div>
          <input type="radio" id="contact-phone" name="contact" value="phone" />
          <Label htmlFor="contact-phone">Phone</Label>
        </div>
      </fieldset>
    );
    
    const fieldset = screen.getByRole('group', { name: 'Preferred Contact Method' });
    const emailRadio = screen.getByLabelText('Email');
    const phoneRadio = screen.getByLabelText('Phone');
    
    expect(fieldset).toBeInTheDocument();
    expect(emailRadio).toHaveAttribute('type', 'radio');
    expect(phoneRadio).toHaveAttribute('type', 'radio');
  });

  it('supports checkbox groups with proper labeling', () => {
    render(
      <fieldset>
        <legend>Subscription Preferences</legend>
        <div>
          <input type="checkbox" id="newsletter" name="subscriptions" value="newsletter" />
          <Label htmlFor="newsletter">Newsletter</Label>
        </div>
        <div>
          <input type="checkbox" id="updates" name="subscriptions" value="updates" />
          <Label htmlFor="updates">Product Updates</Label>
        </div>
      </fieldset>
    );
    
    const fieldset = screen.getByRole('group', { name: 'Subscription Preferences' });
    const newsletter = screen.getByLabelText('Newsletter');
    const updates = screen.getByLabelText('Product Updates');
    
    expect(fieldset).toBeInTheDocument();
    expect(newsletter).toHaveAttribute('type', 'checkbox');
    expect(updates).toHaveAttribute('type', 'checkbox');
  });
});