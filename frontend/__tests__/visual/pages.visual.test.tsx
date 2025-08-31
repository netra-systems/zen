import React from 'react';
import { render } from '@testing-library/react';
import { AuthProvider } from '@/auth/context';
import ChatPage from '@/app/chat/page';
import LoginPage from '@/app/login/page';
import DemoPage from '@/app/demo/page';
import CorpusPage from '@/app/corpus/page';
import AdminPage from '@/app/admin/page';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
der } from '@/auth/context';
import ChatPage from '@/app/chat/page';
import LoginPage from '@/app/login/page';
import DemoPage from '@/app/demo/page';
import CorpusPage from '@/app/corpus/page';
import AdminPage from '@/app/admin/page';

// Mock Next.js Image component for consistent snapshots
jest.mock('next/image', () => ({
  __esModule: true,
  default: ({ src, alt, width, height, ...props }) => (
    <img src={src} alt={alt} width={width} height={height} {...props} />
  ),
}));

// Mock demo components to avoid import issues
jest.mock('@/components/demo/DemoHeader', () => {
  return function MockDemoHeader() {
    return <div data-testid="demo-header">Demo Header</div>;
  };
});

// Mock other problematic components
jest.mock('@/components/demo/DemoProgress', () => {
  return function MockDemoProgress() {
    return <div data-testid="demo-progress">Demo Progress</div>;
  };
});

jest.mock('@/components/demo/DemoTabs', () => {
  return function MockDemoTabs() {
    return <div data-testid="demo-tabs">Demo Tabs</div>;
  };
});

jest.mock('@/components/demo/IndustrySelectionCard', () => {
  return function MockIndustrySelectionCard() {
    return <div data-testid="industry-selection">Industry Selection</div>;
  };
});

jest.mock('@/components/demo/DemoCompletion', () => {
  return function MockDemoCompletion() {
    return <div data-testid="demo-completion">Demo Completion</div>;
  };
});

// Mock auth store to avoid dependencies
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({}),
}));

// Mock auth service
jest.mock('@/auth', () => ({
  authService: {
    getCurrentUser: jest.fn().mockReturnValue(null),
    login: jest.fn(),
    logout: jest.fn(),
    useAuth: () => ({
      user: null,
      loading: false,
    }),
  },
}));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
  }),
  useSearchParams: () => ({
    get: jest.fn().mockReturnValue(null),
    has: jest.fn().mockReturnValue(false),
  }),
}));

// Mock corpus components
jest.mock('@/app/corpus/components/corpus-header', () => ({
  CorpusHeader: () => <div data-testid="corpus-header">Corpus Header</div>,
}));

jest.mock('@/app/corpus/components/corpus-stats', () => ({
  CorpusStatsGrid: () => <div data-testid="corpus-stats">Corpus Stats</div>,
}));

jest.mock('@/app/corpus/components/corpus-storage', () => ({
  CorpusStorage: () => <div data-testid="corpus-storage">Corpus Storage</div>,
}));

jest.mock('@/app/corpus/components/corpus-browse', () => ({
  CorpusBrowse: () => <div data-testid="corpus-browse">Corpus Browse</div>,
}));

jest.mock('@/app/corpus/components/corpus-search', () => ({
  CorpusSearch: () => <div data-testid="corpus-search">Corpus Search</div>,
}));

jest.mock('@/app/corpus/components/corpus-versions', () => ({
  CorpusVersions: () => <div data-testid="corpus-versions">Corpus Versions</div>,
}));

jest.mock('@/app/corpus/components/corpus-permissions', () => ({
  CorpusPermissions: () => <div data-testid="corpus-permissions">Corpus Permissions</div>,
}));

jest.mock('@/app/corpus/hooks/use-corpus-state', () => ({
  useCorpusState: () => ({
    activeTab: 'browse',
    setActiveTab: jest.fn(),
  }),
}));

jest.mock('@/app/corpus/data/corpus-data', () => ({
  corpusData: [],
  statsData: {},
  STORAGE_USED_PERCENTAGE: 75,
}));

// Mock chat components
jest.mock('@/components/chat/MainChat', () => {
  return function MockMainChat() {
    return (
      <div className="flex h-full items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin text-blue-600" data-testid="loader2-icon" data-icon="Loader2" />
          <div className="text-sm text-gray-600">Loading chat...</div>
        </div>
      </div>
    );
  };
});

// Mock any missing functions that might be called
global.handleOAuthTokens = jest.fn();
global.handleThreadParameterRedirect = jest.fn();

// ============================================================================
// PAGE LAYOUT TEST WRAPPER
// ============================================================================

const PageTestWrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>
    <div className="min-h-screen bg-background text-foreground">
      {children}
    </div>
  </AuthProvider>
);

// ============================================================================
// CHAT PAGE VISUAL TESTS
// ============================================================================

describe('Chat Page Visual Layout', () => {
    jest.setTimeout(10000);
  it('renders chat page basic layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <ChatPage />
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('chat-page-basic-layout');
  });

  it('renders chat page with sidebar collapsed', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="chat-layout sidebar-collapsed">
          <ChatPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('chat-page-sidebar-collapsed');
  });

  it('renders chat page with mobile viewport', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="mobile-viewport w-full max-w-sm">
          <ChatPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('chat-page-mobile-layout');
  });

  it('renders chat page with loading state', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="loading-state">
          <ChatPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('chat-page-loading-state');
  });
});

// ============================================================================
// LOGIN PAGE VISUAL TESTS
// ============================================================================

describe('Login Page Visual Layout', () => {
    jest.setTimeout(10000);
  it('renders login page layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <LoginPage />
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('login-page-layout');
  });

  it('renders login page with center alignment', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="flex items-center justify-center min-h-screen">
          <LoginPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('login-page-centered');
  });

  it('renders login page mobile layout', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="mobile-viewport w-full max-w-sm px-4">
          <LoginPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('login-page-mobile');
  });

  it('renders login page with error state', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="error-state">
          <LoginPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('login-page-error-state');
  });
});

// ============================================================================
// DEMO PAGE VISUAL TESTS
// ============================================================================

describe('Demo Page Visual Layout', () => {
    jest.setTimeout(10000);
  it('renders demo page layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <DemoPage />
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('demo-page-layout');
  });

  it('renders demo page with analytics sections', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="demo-analytics-view">
          <DemoPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('demo-page-analytics');
  });

  it('renders demo page tablet layout', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="tablet-viewport w-full max-w-2xl">
          <DemoPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('demo-page-tablet');
  });

  it('renders demo page with performance metrics', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="performance-metrics-view">
          <DemoPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('demo-page-metrics');
  });
});

// ============================================================================
// CORPUS PAGE VISUAL TESTS
// ============================================================================

describe('Corpus Page Visual Layout', () => {
    jest.setTimeout(10000);
  it('renders corpus page layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <CorpusPage />
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('corpus-page-layout');
  });

  it('renders corpus page with data grid', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="corpus-data-grid">
          <CorpusPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('corpus-page-data-grid');
  });

  it('renders corpus page with search active', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="corpus-search-active">
          <CorpusPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('corpus-page-search');
  });

  it('renders corpus page empty state', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="corpus-empty-state">
          <CorpusPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('corpus-page-empty');
  });
});

// ============================================================================
// ADMIN PAGE VISUAL TESTS
// ============================================================================

describe('Admin Page Visual Layout', () => {
    jest.setTimeout(10000);
  it('renders admin page layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <AdminPage />
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('admin-page-layout');
  });

  it('renders admin page with dashboard view', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="admin-dashboard-view">
          <AdminPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('admin-page-dashboard');
  });

  it('renders admin page with settings panel', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="admin-settings-panel">
          <AdminPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('admin-page-settings');
  });

  it('renders admin page with user management', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="admin-user-management">
          <AdminPage />
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('admin-page-users');
  });
});

// ============================================================================
// LAYOUT COMPONENT TESTS
// ============================================================================

describe('Layout Component Visual Tests', () => {
    jest.setTimeout(10000);
  it('renders header layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container flex h-14 items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-lg font-semibold">Netra Apex</h1>
            </div>
            <nav className="flex items-center space-x-4">
              <button className="text-sm">Profile</button>
              <button className="text-sm">Settings</button>
            </nav>
          </div>
        </header>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('header-layout');
  });

  it('renders footer layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <footer className="border-t bg-muted/50">
          <div className="container flex h-16 items-center justify-between text-sm text-muted-foreground">
            <p>&copy; 2025 Netra Apex. All rights reserved.</p>
            <div className="flex space-x-4">
              <a href="/privacy">Privacy</a>
              <a href="/terms">Terms</a>
              <a href="/support">Support</a>
            </div>
          </div>
        </footer>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('footer-layout');
  });

  it('renders sidebar navigation layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <aside className="w-64 border-r bg-background">
          <div className="flex h-full flex-col">
            <div className="p-4">
              <h2 className="text-lg font-semibold">Navigation</h2>
            </div>
            <nav className="flex-1 space-y-1 p-4">
              <a href="/chat" className="block px-3 py-2 rounded-md bg-muted">Chat</a>
              <a href="/demo" className="block px-3 py-2 rounded-md">Demo</a>
              <a href="/corpus" className="block px-3 py-2 rounded-md">Corpus</a>
              <a href="/admin" className="block px-3 py-2 rounded-md">Admin</a>
            </nav>
          </div>
        </aside>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('sidebar-navigation');
  });

  it('renders main content area layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <main className="flex-1 overflow-auto">
          <div className="container mx-auto p-6">
            <div className="mb-6">
              <h1 className="text-3xl font-bold">Page Title</h1>
              <p className="text-muted-foreground">Page description goes here</p>
            </div>
            <div className="grid gap-6">
              <div className="rounded-lg border bg-card p-6">
                <h2 className="text-xl font-semibold mb-4">Section Title</h2>
                <p>Section content goes here</p>
              </div>
            </div>
          </div>
        </main>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('main-content-layout');
  });
});

// ============================================================================
// RESPONSIVE GRID LAYOUTS
// ============================================================================

describe('Grid Layout Visual Tests', () => {
    jest.setTimeout(10000);
  it('renders dashboard grid layout correctly', () => {
    const { container } = render(
      <PageTestWrapper>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-semibold">Metric 1</h3>
            <p className="text-2xl font-bold">1,234</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-semibold">Metric 2</h3>
            <p className="text-2xl font-bold">5,678</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-semibold">Metric 3</h3>
            <p className="text-2xl font-bold">9,012</p>
          </div>
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('dashboard-grid-layout');
  });

  it('renders content list layout correctly', () => {
    const items = ['Item 1', 'Item 2', 'Item 3', 'Item 4'];
    const { container } = render(
      <PageTestWrapper>
        <div className="space-y-2">
          {items.map((item, index) => (
            <div key={index} className="flex items-center justify-between rounded-lg border p-4">
              <span>{item}</span>
              <button className="text-sm text-muted-foreground hover:text-foreground">
                Action
              </button>
            </div>
          ))}
        </div>
      </PageTestWrapper>
    );
    expect(container.firstChild).toMatchSnapshot('content-list-layout');
  });
});

// ============================================================================
// DARK THEME PAGE LAYOUTS
// ============================================================================

describe('Dark Theme Page Layout Tests', () => {
    jest.setTimeout(10000);
  it('renders chat page in dark theme correctly', () => {
    const { container } = render(
      <div className="dark">
        <PageTestWrapper>
          <ChatPage />
        </PageTestWrapper>
      </div>
    );
    expect(container.firstChild).toMatchSnapshot('chat-page-dark-theme');
  });

  it('renders login page in dark theme correctly', () => {
    const { container } = render(
      <div className="dark">
        <PageTestWrapper>
          <LoginPage />
        </PageTestWrapper>
      </div>
    );
    expect(container.firstChild).toMatchSnapshot('login-page-dark-theme');
  });

  it('renders demo page in dark theme correctly', () => {
    const { container } = render(
      <div className="dark">
        <PageTestWrapper>
          <DemoPage />
        </PageTestWrapper>
      </div>
    );
    expect(container.firstChild).toMatchSnapshot('demo-page-dark-theme');
  });

  it('renders admin page in dark theme correctly', () => {
    const { container } = render(
      <div className="dark">
        <PageTestWrapper>
          <AdminPage />
        </PageTestWrapper>
      </div>
    );
    expect(container.firstChild).toMatchSnapshot('admin-page-dark-theme');
  });
});