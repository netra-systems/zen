import { render, screen, fireEvent, within } from '@testing-library/react';
import {
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
} from '@/components/ui/select';

describe('Select Component', () => {
    jest.setTimeout(10000);
  it('should render all parts of the select component', async () => {
    render(
      <Select>
        <SelectTrigger data-testid="select-trigger">
          <SelectValue placeholder="Select an option" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Options</SelectLabel>
            <SelectItem value="option1">Option 1</SelectItem>
            <SelectItem value="option2">Option 2</SelectItem>
            <SelectSeparator />
            <SelectItem value="option3">Option 3</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    );

    // Check if the trigger is rendered
    const trigger = screen.getByTestId('select-trigger');
    expect(trigger).toBeInTheDocument();

    // Open the select dropdown
    fireEvent.click(trigger);

    // Check if the content is rendered
    const content = await screen.findByRole('listbox');
    expect(within(content).getByText('Options')).toBeInTheDocument();

    // Check if the items are rendered
    const item1 = screen.getByText('Option 1');
    const item2 = screen.getByText('Option 2');
    const item3 = screen.getByText('Option 3');
    expect(item1).toBeInTheDocument();
    expect(item2).toBeInTheDocument();
    expect(item3).toBeInTheDocument();
  });
});