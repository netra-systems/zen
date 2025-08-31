import React from 'react';
import { render } from '@testing-library/react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';

// ============================================================================
// BUTTON COMPONENT VISUAL TESTS
// ============================================================================

describe('Button Visual Snapshots', () => {
    jest.setTimeout(10000);
  const buttonVariants = ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'] as const;
  const buttonSizes = ['default', 'sm', 'lg', 'icon'] as const;

  buttonVariants.forEach(variant => {
    it(`renders ${variant} variant correctly`, () => {
      const { container } = render(<Button variant={variant}>Button Text</Button>);
      expect(container.firstChild).toMatchSnapshot(`button-${variant}-variant`);
    });
  });

  buttonSizes.forEach(size => {
    it(`renders ${size} size correctly`, () => {
      const { container } = render(<Button size={size}>Button</Button>);
      expect(container.firstChild).toMatchSnapshot(`button-${size}-size`);
    });
  });

  it('renders disabled state correctly', () => {
    const { container } = render(<Button disabled>Disabled Button</Button>);
    expect(container.firstChild).toMatchSnapshot('button-disabled-state');
  });

  it('renders loading state correctly', () => {
    const { container } = render(<Button data-loading="true">Loading Button</Button>);
    expect(container.firstChild).toMatchSnapshot('button-loading-state');
  });
});

// ============================================================================
// INPUT COMPONENT VISUAL TESTS
// ============================================================================

describe('Input Visual Snapshots', () => {
    jest.setTimeout(10000);
  it('renders default input correctly', () => {
    const { container } = render(<Input placeholder="Enter text" />);
    expect(container.firstChild).toMatchSnapshot('input-default-state');
  });

  it('renders disabled input correctly', () => {
    const { container } = render(<Input disabled placeholder="Disabled input" />);
    expect(container.firstChild).toMatchSnapshot('input-disabled-state');
  });

  it('renders input with value correctly', () => {
    const { container } = render(<Input value="Sample text" readOnly />);
    expect(container.firstChild).toMatchSnapshot('input-with-value');
  });

  it('renders input with error state correctly', () => {
    const { container } = render(<Input className="border-red-500" placeholder="Error state" />);
    expect(container.firstChild).toMatchSnapshot('input-error-state');
  });
});

// ============================================================================
// BADGE COMPONENT VISUAL TESTS
// ============================================================================

describe('Badge Visual Snapshots', () => {
    jest.setTimeout(10000);
  const badgeVariants = ['default', 'secondary', 'destructive', 'outline'] as const;

  badgeVariants.forEach(variant => {
    it(`renders ${variant} badge correctly`, () => {
      const { container } = render(<Badge variant={variant}>Badge Text</Badge>);
      expect(container.firstChild).toMatchSnapshot(`badge-${variant}-variant`);
    });
  });

  it('renders badge with counter correctly', () => {
    const { container } = render(<Badge>42</Badge>);
    expect(container.firstChild).toMatchSnapshot('badge-counter');
  });
});

// ============================================================================
// CARD COMPONENT VISUAL TESTS
// ============================================================================

describe('Card Visual Snapshots', () => {
    jest.setTimeout(10000);
  it('renders basic card correctly', () => {
    const { container } = render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
        </CardHeader>
        <CardContent>Card content goes here</CardContent>
      </Card>
    );
    expect(container.firstChild).toMatchSnapshot('card-basic-layout');
  });

  it('renders card with long content correctly', () => {
    const longContent = 'This is a very long content that should test how the card handles extended text and content overflow scenarios.';
    const { container } = render(
      <Card>
        <CardHeader>
          <CardTitle>Long Content Card</CardTitle>
        </CardHeader>
        <CardContent>{longContent}</CardContent>
      </Card>
    );
    expect(container.firstChild).toMatchSnapshot('card-long-content');
  });
});

// ============================================================================
// ALERT COMPONENT VISUAL TESTS
// ============================================================================

describe('Alert Visual Snapshots', () => {
    jest.setTimeout(10000);
  const alertVariants = ['default', 'destructive'] as const;

  alertVariants.forEach(variant => {
    it(`renders ${variant} alert correctly`, () => {
      const { container } = render(
        <Alert variant={variant}>
          <AlertDescription>This is an alert message</AlertDescription>
        </Alert>
      );
      expect(container.firstChild).toMatchSnapshot(`alert-${variant}-variant`);
    });
  });

  it('renders alert with long message correctly', () => {
    const longMessage = 'This is a very long alert message that tests how the alert component handles extended content and maintains proper styling.';
    const { container } = render(
      <Alert>
        <AlertDescription>{longMessage}</AlertDescription>
      </Alert>
    );
    expect(container.firstChild).toMatchSnapshot('alert-long-message');
  });
});

// ============================================================================
// TABS COMPONENT VISUAL TESTS
// ============================================================================

describe('Tabs Visual Snapshots', () => {
    jest.setTimeout(10000);
  it('renders tabs layout correctly', () => {
    const { container } = render(
      <Tabs defaultValue="tab1">
        <TabsList>
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          <TabsTrigger value="tab2">Tab 2</TabsTrigger>
          <TabsTrigger value="tab3">Tab 3</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content for Tab 1</TabsContent>
        <TabsContent value="tab2">Content for Tab 2</TabsContent>
        <TabsContent value="tab3">Content for Tab 3</TabsContent>
      </Tabs>
    );
    expect(container.firstChild).toMatchSnapshot('tabs-layout');
  });

  it('renders tabs with many items correctly', () => {
    const tabItems = Array.from({ length: 6 }, (_, i) => `Tab ${i + 1}`);
    const { container } = render(
      <Tabs defaultValue="tab1">
        <TabsList>
          {tabItems.map((tab, index) => (
            <TabsTrigger key={index} value={`tab${index + 1}`}>{tab}</TabsTrigger>
          ))}
        </TabsList>
        {tabItems.map((tab, index) => (
          <TabsContent key={index} value={`tab${index + 1}`}>Content for {tab}</TabsContent>
        ))}
      </Tabs>
    );
    expect(container.firstChild).toMatchSnapshot('tabs-many-items');
  });
});

// ============================================================================
// PROGRESS COMPONENT VISUAL TESTS
// ============================================================================

describe('Progress Visual Snapshots', () => {
    jest.setTimeout(10000);
  const progressValues = [0, 25, 50, 75, 100];

  progressValues.forEach(value => {
    it(`renders progress at ${value}% correctly`, () => {
      const { container } = render(<Progress value={value} />);
      expect(container.firstChild).toMatchSnapshot(`progress-${value}-percent`);
    });
  });

  it('renders indeterminate progress correctly', () => {
    const { container } = render(<Progress />);
    expect(container.firstChild).toMatchSnapshot('progress-indeterminate');
  });
});

// ============================================================================
// SWITCH COMPONENT VISUAL TESTS
// ============================================================================

describe('Switch Visual Snapshots', () => {
    jest.setTimeout(10000);
  it('renders unchecked switch correctly', () => {
    const { container } = render(<Switch />);
    expect(container.firstChild).toMatchSnapshot('switch-unchecked-state');
  });

  it('renders checked switch correctly', () => {
    const { container } = render(<Switch checked />);
    expect(container.firstChild).toMatchSnapshot('switch-checked-state');
  });

  it('renders disabled switch correctly', () => {
    const { container } = render(<Switch disabled />);
    expect(container.firstChild).toMatchSnapshot('switch-disabled-state');
  });

  it('renders disabled checked switch correctly', () => {
    const { container } = render(<Switch disabled checked />);
    expect(container.firstChild).toMatchSnapshot('switch-disabled-checked');
  });
});

// ============================================================================
// COMPONENT COMBINATION TESTS
// ============================================================================

describe('Component Combinations Visual Tests', () => {
    jest.setTimeout(10000);
  it('renders form layout with multiple components', () => {
    const { container } = render(
      <div className="space-y-4 p-4 max-w-md">
        <div>
          <label htmlFor="email" className="block text-sm font-medium mb-2">
            Email Address
          </label>
          <Input id="email" type="email" placeholder="Enter your email" />
        </div>
        <div className="flex items-center space-x-2">
          <Switch id="notifications" />
          <label htmlFor="notifications" className="text-sm">
            Enable notifications
          </label>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline">Cancel</Button>
          <Button>Save Changes</Button>
        </div>
      </div>
    );
    expect(container.firstChild).toMatchSnapshot('form-layout-combination');
  });

  it('renders status dashboard layout', () => {
    const { container } = render(
      <div className="grid gap-4 p-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              System Status
              <Badge variant="default">Online</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>CPU Usage</span>
                <span>45%</span>
              </div>
              <Progress value={45} />
            </div>
          </CardContent>
        </Card>
        <Alert>
          <AlertDescription>All systems are operational</AlertDescription>
        </Alert>
      </div>
    );
    expect(container.firstChild).toMatchSnapshot('status-dashboard-layout');
  });
});

// ============================================================================
// DARK THEME VISUAL TESTS
// ============================================================================

describe('Dark Theme Component Tests', () => {
    jest.setTimeout(10000);
  it('renders button in dark theme correctly', () => {
    const { container } = render(
      <div className="dark">
        <Button variant="default">Dark Theme Button</Button>
      </div>
    );
    expect(container.firstChild).toMatchSnapshot('button-dark-theme');
  });

  it('renders card in dark theme correctly', () => {
    const { container } = render(
      <div className="dark">
        <Card>
          <CardHeader>
            <CardTitle>Dark Theme Card</CardTitle>
          </CardHeader>
          <CardContent>Content in dark theme</CardContent>
        </Card>
      </div>
    );
    expect(container.firstChild).toMatchSnapshot('card-dark-theme');
  });

  it('renders form elements in dark theme correctly', () => {
    const { container } = render(
      <div className="dark">
        <div className="space-y-4 p-4">
          <Input placeholder="Dark theme input" />
          <Switch />
          <Badge>Dark Badge</Badge>
          <Alert>
            <AlertDescription>Dark theme alert</AlertDescription>
          </Alert>
        </div>
      </div>
    );
    expect(container.firstChild).toMatchSnapshot('form-elements-dark-theme');
  });
});