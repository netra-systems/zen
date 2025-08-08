
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Thinking } from '../components/Thinking';

describe('Thinking component', () => {
  it('renders three dots', () => {
    render(<Thinking />);
    const dots = screen.getAllByRole('status');
    expect(dots).toHaveLength(3);
  });
});
