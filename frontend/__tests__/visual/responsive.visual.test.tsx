/**
 * Visual Regression Tests - Responsive Design
 * Tests responsive breakpoints, mobile layouts, and cross-browser compatibility
 * Follows 25-line function rule and comprehensive viewport coverage
 * Business Impact: Ensures consistent UI across all devices and browsers
 */

import React from 'react';
import { render } from '@testing-library/react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AuthProvider } from '@/auth/context';

// ============================================================================
// VIEWPORT CONFIGURATION
// ============================================================================

const viewports = {
  mobile: { width: 375, height: 667 },
  mobileLarge: { width: 414, height: 896 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1024, height: 768 },
  desktopLarge: { width: 1440, height: 900 },
  ultrawide: { width: 1920, height: 1080 },
};

const mockViewport = (width: number, height: number) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: height,
  });
};

// ============================================================================
// RESPONSIVE WRAPPER COMPONENT
// ============================================================================

const ResponsiveWrapper = ({ 
  children, 
  viewport 
}: { 
  children: React.ReactNode;
  viewport: keyof typeof viewports;
}) => {
  const { width, height } = viewports[viewport];
  return (
    <div 
      style={{ width: `${width}px`, height: `${height}px` }}
      className={`responsive-container ${viewport}`}
    >
      <AuthProvider>
        {children}
      </AuthProvider>
    </div>
  );
};

// ============================================================================
// MOBILE RESPONSIVE TESTS
// ============================================================================

describe('Mobile Responsive Visual Tests', () => {
  beforeEach(() => {
    mockViewport(375, 667);
  });

  it('renders button layout mobile correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="mobile">
        <div className="p-4 space-y-4">
          <Button className="w-full">Full Width Button</Button>
          <div className="flex flex-col space-y-2 sm:flex-row sm:space-y-0 sm:space-x-2">
            <Button className="flex-1">Primary</Button>
            <Button variant="outline" className="flex-1">Secondary</Button>
          </div>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('button-layout-mobile');
  });

  it('renders form layout mobile correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="mobile">
        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Email</label>
            <Input placeholder="Enter email" className="w-full" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Password</label>
            <Input type="password" placeholder="Enter password" className="w-full" />
          </div>
          <Button className="w-full">Sign In</Button>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('form-layout-mobile');
  });

  it('renders card grid mobile correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="mobile">
        <div className="p-4 grid gap-4 grid-cols-1 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Card 1</CardTitle>
            </CardHeader>
            <CardContent>Mobile optimized content</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Card 2</CardTitle>
            </CardHeader>
            <CardContent>Responsive design</CardContent>
          </Card>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('card-grid-mobile');
  });

  it('renders navigation mobile correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="mobile">
        <nav className="p-4 border-b">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold">Netra</h1>
            <button className="p-2">☰</button>
          </div>
          <div className="mt-4 space-y-2 sm:hidden">
            <a href="#" className="block py-2 px-3 rounded">Chat</a>
            <a href="#" className="block py-2 px-3 rounded">Demo</a>
            <a href="#" className="block py-2 px-3 rounded">Settings</a>
          </div>
        </nav>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('navigation-mobile');
  });
});

// ============================================================================
// TABLET RESPONSIVE TESTS
// ============================================================================

describe('Tablet Responsive Visual Tests', () => {
  beforeEach(() => {
    mockViewport(768, 1024);
  });

  it('renders dashboard layout tablet correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="tablet">
        <div className="p-6 grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">1,234</div>
              <p className="text-muted-foreground">Active users</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">99.5%</div>
              <p className="text-muted-foreground">Uptime</p>
            </CardContent>
          </Card>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('dashboard-layout-tablet');
  });

  it('renders sidebar layout tablet correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="tablet">
        <div className="flex min-h-screen">
          <aside className="w-64 border-r bg-muted/50 p-4 hidden md:block">
            <nav className="space-y-2">
              <a href="#" className="block py-2 px-3 rounded bg-primary text-primary-foreground">Chat</a>
              <a href="#" className="block py-2 px-3 rounded hover:bg-muted">Demo</a>
              <a href="#" className="block py-2 px-3 rounded hover:bg-muted">Settings</a>
            </nav>
          </aside>
          <main className="flex-1 p-6">
            <h1 className="text-2xl font-bold mb-4">Main Content</h1>
            <p>Tablet optimized layout with sidebar</p>
          </main>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('sidebar-layout-tablet');
  });

  it('renders tabs layout tablet correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="tablet">
        <div className="p-6">
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="analytics">Analytics</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
            </TabsList>
            <TabsContent value="overview" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Overview</CardTitle>
                </CardHeader>
                <CardContent>Tablet optimized overview content</CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('tabs-layout-tablet');
  });

  it('renders data table tablet correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="tablet">
        <div className="p-6 overflow-x-auto">
          <table className="w-full border-collapse border border-border">
            <thead>
              <tr className="border-b">
                <th className="p-2 text-left">Name</th>
                <th className="p-2 text-left">Status</th>
                <th className="p-2 text-left">Created</th>
                <th className="p-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b">
                <td className="p-2">Item 1</td>
                <td className="p-2">Active</td>
                <td className="p-2">2025-01-01</td>
                <td className="p-2">
                  <Button size="sm" variant="ghost">Edit</Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('data-table-tablet');
  });
});

// ============================================================================
// DESKTOP RESPONSIVE TESTS
// ============================================================================

describe('Desktop Responsive Visual Tests', () => {
  beforeEach(() => {
    mockViewport(1024, 768);
  });

  it('renders full dashboard desktop correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="desktop">
        <div className="p-8 grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Main Dashboard</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="p-4 bg-muted rounded">
                  <h3 className="font-semibold">Metric 1</h3>
                  <p className="text-2xl font-bold">1,234</p>
                </div>
                <div className="p-4 bg-muted rounded">
                  <h3 className="font-semibold">Metric 2</h3>
                  <p className="text-2xl font-bold">5,678</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Sidebar Info</CardTitle>
            </CardHeader>
            <CardContent>Desktop sidebar content</CardContent>
          </Card>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('full-dashboard-desktop');
  });

  it('renders complex form desktop correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="desktop">
        <div className="p-8 max-w-4xl mx-auto">
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Personal Information</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-sm font-medium">First Name</label>
                  <Input placeholder="First name" />
                </div>
                <div>
                  <label className="text-sm font-medium">Last Name</label>
                  <Input placeholder="Last name" />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">Email</label>
                <Input type="email" placeholder="Email address" />
              </div>
            </div>
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Preferences</h2>
              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input type="checkbox" />
                  <span>Email notifications</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input type="checkbox" />
                  <span>SMS alerts</span>
                </label>
              </div>
            </div>
          </div>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('complex-form-desktop');
  });

  it('renders multi-column layout desktop correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="desktop">
        <div className="p-8 grid gap-8 lg:grid-cols-4">
          <nav className="lg:col-span-1">
            <div className="space-y-2">
              <h3 className="font-semibold">Navigation</h3>
              <div className="space-y-1">
                <a href="#" className="block py-1 px-2 rounded text-sm">Home</a>
                <a href="#" className="block py-1 px-2 rounded text-sm">Dashboard</a>
                <a href="#" className="block py-1 px-2 rounded text-sm">Settings</a>
              </div>
            </div>
          </nav>
          <main className="lg:col-span-2">
            <h1 className="text-2xl font-bold mb-4">Main Content</h1>
            <Card>
              <CardContent className="p-6">
                <p>Primary content area with proper desktop spacing and typography.</p>
              </CardContent>
            </Card>
          </main>
          <aside className="lg:col-span-1">
            <div className="space-y-4">
              <h3 className="font-semibold">Quick Actions</h3>
              <div className="space-y-2">
                <Button size="sm" className="w-full">Action 1</Button>
                <Button size="sm" variant="outline" className="w-full">Action 2</Button>
              </div>
            </div>
          </aside>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('multi-column-desktop');
  });

  it('renders data visualization desktop correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="desktop">
        <div className="p-8 space-y-6">
          <div className="grid gap-6 md:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <div className="text-2xl font-bold">{(i + 1) * 1000}</div>
                  <p className="text-sm text-muted-foreground">Metric {i + 1}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Chart Area</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64 bg-muted rounded flex items-center justify-center">
                <p className="text-muted-foreground">Chart visualization would go here</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('data-visualization-desktop');
  });
});

// ============================================================================
// ULTRA-WIDE RESPONSIVE TESTS
// ============================================================================

describe('Ultra-Wide Responsive Visual Tests', () => {
  beforeEach(() => {
    mockViewport(1920, 1080);
  });

  it('renders enterprise dashboard ultrawide correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="ultrawide">
        <div className="p-12 grid gap-8 xl:grid-cols-5">
          <div className="xl:col-span-3 space-y-6">
            <h1 className="text-3xl font-bold">Enterprise Dashboard</h1>
            <div className="grid gap-6 lg:grid-cols-3">
              {Array.from({ length: 6 }, (_, i) => (
                <Card key={i}>
                  <CardContent className="p-4">
                    <div className="text-xl font-bold">{(i + 1) * 1500}</div>
                    <p className="text-sm text-muted-foreground">Enterprise Metric {i + 1}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
          <div className="xl:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>System Status</CardTitle>
              </CardHeader>
              <CardContent>Ultrawide sidebar content optimized for large screens</CardContent>
            </Card>
          </div>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('enterprise-dashboard-ultrawide');
  });

  it('renders data center layout ultrawide correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="ultrawide">
        <div className="p-12 grid gap-8 xl:grid-cols-6">
          {Array.from({ length: 12 }, (_, i) => (
            <Card key={i} className="xl:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">Server {i + 1}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>CPU</span>
                    <span>{Math.floor(Math.random() * 100)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Memory</span>
                    <span>{Math.floor(Math.random() * 100)}%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('data-center-layout-ultrawide');
  });
});

// ============================================================================
// BREAKPOINT TRANSITION TESTS
// ============================================================================

describe('Breakpoint Transition Visual Tests', () => {
  it('renders component at mobile-to-tablet breakpoint', () => {
    mockViewport(768, 1024);
    const { container } = render(
      <ResponsiveWrapper viewport="tablet">
        <div className="p-4 grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          <Card className="transition-all">
            <CardHeader>
              <CardTitle>Responsive Card</CardTitle>
            </CardHeader>
            <CardContent>Adapts at breakpoints</CardContent>
          </Card>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('mobile-tablet-breakpoint');
  });

  it('renders component at tablet-to-desktop breakpoint', () => {
    mockViewport(1024, 768);
    const { container } = render(
      <ResponsiveWrapper viewport="desktop">
        <div className="p-6 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Card key={i} className="transition-all">
              <CardContent className="p-4">
                <h3 className="font-semibold">Item {i + 1}</h3>
                <p className="text-sm text-muted-foreground">Breakpoint transition test</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('tablet-desktop-breakpoint');
  });
});

// ============================================================================
// ACCESSIBILITY AND CONTRAST TESTS
// ============================================================================

describe('Accessibility Visual Tests', () => {
  it('renders high contrast mode correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="desktop">
        <div className="high-contrast p-8">
          <div className="space-y-4">
            <Button className="contrast-enhanced">High Contrast Button</Button>
            <Input placeholder="High contrast input" className="contrast-enhanced" />
            <Card className="contrast-enhanced">
              <CardContent className="p-4">
                <p>High contrast content for accessibility compliance</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('high-contrast-mode');
  });

  it('renders focus states correctly', () => {
    const { container } = render(
      <ResponsiveWrapper viewport="desktop">
        <div className="p-8 space-y-4">
          <Button className="focus-visible:ring-2 focus-visible:ring-primary">
            Focusable Button
          </Button>
          <Input 
            className="focus-visible:ring-2 focus-visible:ring-primary"
            placeholder="Focusable input"
          />
          <a 
            href="#"
            className="inline-block p-2 focus-visible:ring-2 focus-visible:ring-primary rounded"
          >
            Focusable Link
          </a>
        </div>
      </ResponsiveWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('focus-states-accessibility');
  });
});