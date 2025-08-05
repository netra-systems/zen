
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Input } from '../input';

describe('Input', () => {
  it('renders an input', () => {
    render(<Input placeholder='username' />);
    const input = screen.getByPlaceholderText('username');
    expect(input).toBeInTheDocument();
  });

  it('applies the correct type', () => {
    render(<Input type="password" placeholder='password' />);
    const input = screen.getByPlaceholderText('password');
    expect(input).toHaveAttribute('type', 'password');
  });

  it('is disabled when the disabled prop is true', () => {
    render(<Input disabled placeholder='disabled' />);
    const input = screen.getByPlaceholderText('disabled');
    expect(input).toBeDisabled();
  });
});
