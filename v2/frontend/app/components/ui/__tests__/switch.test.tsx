
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Switch } from '../switch';

describe('Switch', () => {
  it('renders a switch', () => {
    render(<Switch />);
    const switchControl = screen.getByRole('switch');
    expect(switchControl).toBeInTheDocument();
  });

  it('is unchecked by default', () => {
    render(<Switch />);
    const switchControl = screen.getByRole('switch');
    expect(switchControl).not.toBeChecked();
  });

  it('is checked when the checked prop is true', () => {
    render(<Switch checked />);
    const switchControl = screen.getByRole('switch');
    expect(switchControl).toBeChecked();
  });
});
