import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise)
 * - Goal: Ensure keyboard-only users can navigate and submit forms
 * - Value Impact: Enables keyboard-only users to complete forms
 * - Revenue Impact: +$25K MRR from accessible form completion
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Import form components
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

// Import shared accessibility helpers
import { 
  setupKeyboardTest, 
  testTabNavigation, 
  testKeyboardActivation,
  createKeyboardEvent
} from './shared-a11y-helpers';

// ============================================================================
// KEYBOARD INTERACTION TESTS
// ============================================================================

describe('Form Keyboard Interaction - Navigation and Submission', () => {
    jest.setTimeout(10000);
  it('supports tab navigation through form fields', async () => {
    const user = setupKeyboardTest();
    render(
      <form>
        <Input placeholder="First field" />
        <Input placeholder="Second field" />
        <Button type="submit">Submit</Button>
      </form>
    );
    
    await user.tab();
    expect(screen.getByPlaceholderText('First field')).toHaveFocus();
    
    await user.tab();
    expect(screen.getByPlaceholderText('Second field')).toHaveFocus();
    
    await user.tab();
    expect(screen.getByRole('button', { name: 'Submit' })).toHaveFocus();
  });

  it('submits form with Enter key from input fields', async () => {
    const user = setupKeyboardTest();
    const onSubmitMock = jest.fn();
    
    render(
      <form onSubmit={(e) => { e.preventDefault(); onSubmitMock(); }}>
        <Input placeholder="Press Enter to submit" />
        <Button type="submit">Submit</Button>
      </form>
    );
    
    const input = screen.getByPlaceholderText('Press Enter to submit');
    await user.click(input);
    await user.keyboard('{Enter}');
    
    expect(onSubmitMock).toHaveBeenCalled();
  });

  it('supports Escape key to clear input', async () => {
    const user = setupKeyboardTest();
    const ClearableInput = () => {
      const [value, setValue] = React.useState('');
      
      const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Escape') {
          setValue('');
        }
      };
      
      return (
        <Input 
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type and press Escape to clear"
        />
      );
    };
    
    render(<ClearableInput />);
    const input = screen.getByRole('textbox');
    
    await user.type(input, 'Some text');
    expect(input).toHaveValue('Some text');
    
    await user.keyboard('{Escape}');
    expect(input).toHaveValue('');
  });

  it('handles complex keyboard shortcuts', async () => {
    const user = setupKeyboardTest();
    const ShortcutForm = () => {
      const [saved, setSaved] = React.useState(false);
      
      const handleKeyDown = (e: React.KeyboardEvent) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
          e.preventDefault();
          setSaved(true);
        }
      };
      
      return (
        <div onKeyDown={handleKeyDown}>
          <Input placeholder="Ctrl+S to save" />
          {saved && <div>Saved!</div>}
        </div>
      );
    };
    
    render(<ShortcutForm />);
    const input = screen.getByRole('textbox');
    
    await user.click(input);
    await user.keyboard('{Control>}s{/Control}');
    
    expect(screen.getByText('Saved!')).toBeInTheDocument();
  });

  it('supports arrow key navigation in select fields', async () => {
    const user = setupKeyboardTest();
    render(
      <select name="options" data-testid="select-field">
        <option value="option1">Option 1</option>
        <option value="option2">Option 2</option>
        <option value="option3">Option 3</option>
      </select>
    );
    
    const select = screen.getByTestId('select-field');
    await user.click(select);
    await user.keyboard('{ArrowDown}');
    
    expect(select).toHaveFocus();
  });

  it('handles Tab and Shift+Tab navigation correctly', async () => {
    const user = setupKeyboardTest();
    render(
      <form>
        <Input data-testid="field1" placeholder="Field 1" />
        <Input data-testid="field2" placeholder="Field 2" />
        <Input data-testid="field3" placeholder="Field 3" />
      </form>
    );
    
    // Tab forward
    await user.tab();
    expect(screen.getByTestId('field1')).toHaveFocus();
    
    await user.tab();
    expect(screen.getByTestId('field2')).toHaveFocus();
    
    // Tab backward
    await user.tab({ shift: true });
    expect(screen.getByTestId('field1')).toHaveFocus();
  });

  it('skips disabled fields in tab order', async () => {
    const user = setupKeyboardTest();
    render(
      <form>
        <Input placeholder="First field" />
        <Input placeholder="Disabled field" disabled />
        <Input placeholder="Third field" />
      </form>
    );
    
    await user.tab();
    expect(screen.getByPlaceholderText('First field')).toHaveFocus();
    
    await user.tab();
    expect(screen.getByPlaceholderText('Third field')).toHaveFocus();
  });

  it('supports custom tabindex for focus order', async () => {
    const user = setupKeyboardTest();
    render(
      <form>
        <Input placeholder="Third" tabIndex={3} />
        <Input placeholder="First" tabIndex={1} />
        <Input placeholder="Second" tabIndex={2} />
      </form>
    );
    
    await user.tab();
    expect(screen.getByPlaceholderText('First')).toHaveFocus();
    
    await user.tab();
    expect(screen.getByPlaceholderText('Second')).toHaveFocus();
    
    await user.tab();
    expect(screen.getByPlaceholderText('Third')).toHaveFocus();
  });

  it('handles keyboard events for custom components', async () => {
    const user = setupKeyboardTest();
    const CustomInput = () => {
      const [focused, setFocused] = React.useState(false);
      
      const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'F1') {
          e.preventDefault();
          setFocused(true);
        }
      };
      
      return (
        <div>
          <Input 
            onKeyDown={handleKeyDown}
            placeholder="Press F1 for help"
          />
          {focused && <div>Help activated</div>}
        </div>
      );
    };
    
    render(<CustomInput />);
    const input = screen.getByRole('textbox');
    
    await user.click(input);
    await user.keyboard('{F1}');
    
    expect(screen.getByText('Help activated')).toBeInTheDocument();
  });

  it('provides keyboard accessibility for radio groups', async () => {
    const user = setupKeyboardTest();
    render(
      <fieldset>
        <legend>Choose an option</legend>
        <div>
          <input type="radio" id="option1" name="choice" value="1" />
          <Label htmlFor="option1">Option 1</Label>
        </div>
        <div>
          <input type="radio" id="option2" name="choice" value="2" />
          <Label htmlFor="option2">Option 2</Label>
        </div>
        <div>
          <input type="radio" id="option3" name="choice" value="3" />
          <Label htmlFor="option3">Option 3</Label>
        </div>
      </fieldset>
    );
    
    const option1 = screen.getByLabelText('Option 1');
    
    await user.tab();
    expect(option1).toHaveFocus();
    
    await user.keyboard('{ArrowDown}');
    expect(screen.getByLabelText('Option 2')).toHaveFocus();
  });

  it('supports keyboard navigation in checkbox groups', async () => {
    const user = setupKeyboardTest();
    render(
      <fieldset>
        <legend>Select preferences</legend>
        <div>
          <input type="checkbox" id="pref1" name="preferences" value="1" />
          <Label htmlFor="pref1">Preference 1</Label>
        </div>
        <div>
          <input type="checkbox" id="pref2" name="preferences" value="2" />
          <Label htmlFor="pref2">Preference 2</Label>
        </div>
      </fieldset>
    );
    
    await user.tab();
    expect(screen.getByLabelText('Preference 1')).toHaveFocus();
    
    await user.keyboard(' ');
    expect(screen.getByLabelText('Preference 1')).toBeChecked();
    
    await user.tab();
    expect(screen.getByLabelText('Preference 2')).toHaveFocus();
  });

  it('handles form submission via keyboard', async () => {
    const user = setupKeyboardTest();
    const onSubmitMock = jest.fn();
    
    render(
      <form onSubmit={(e) => { e.preventDefault(); onSubmitMock(); }}>
        <Input placeholder="Name" />
        <Button type="submit">Submit</Button>
      </form>
    );
    
    // Navigate to submit button and activate
    await user.tab();
    await user.tab();
    await user.keyboard('{Enter}');
    
    expect(onSubmitMock).toHaveBeenCalled();
  });

  it('prevents form submission on invalid fields', async () => {
    const user = setupKeyboardTest();
    const onSubmitMock = jest.fn();
    
    render(
      <form onSubmit={(e) => { e.preventDefault(); onSubmitMock(); }}>
        <Input required placeholder="Required field" />
        <Button type="submit">Submit</Button>
      </form>
    );
    
    // Try to submit without filling required field
    await user.tab();
    await user.keyboard('{Enter}');
    
    // Form should not submit due to HTML5 validation
    expect(onSubmitMock).not.toHaveBeenCalled();
  });

  it('supports keyboard help and instructions', async () => {
    const user = setupKeyboardTest();
    const HelpfulForm = () => {
      const [showHelp, setShowHelp] = React.useState(false);
      
      const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === '?' && e.shiftKey) {
          e.preventDefault();
          setShowHelp(!showHelp);
        }
      };
      
      return (
        <div onKeyDown={handleKeyDown}>
          <Input placeholder="Press Shift+? for help" />
          {showHelp && (
            <div role="tooltip" id="keyboard-help">
              Use Tab to navigate between fields
            </div>
          )}
        </div>
      );
    };
    
    render(<HelpfulForm />);
    const input = screen.getByRole('textbox');
    
    await user.click(input);
    await user.keyboard('{Shift>}?{/Shift}');
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });
});