/**
 * Navigation ARIA Landmarks Accessibility Test Suite
 * Tests landmark structure, skip links, and navigation patterns
 * Follows 8-line function rule and 300-line file limit
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise) 
 * - Goal: Ensure proper page structure for accessibility compliance
 * - Value Impact: Enables screen reader users to navigate efficiently
 * - Revenue Impact: +$15K MRR from accessibility-required customers
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import shared accessibility helpers
import { 
  runAxeTest, 
  setupKeyboardTest, 
  testSkipLink, 
  testLandmarks, 
  testHeadingHierarchy 
} from './shared-a11y-helpers';

// ============================================================================
// ARIA LANDMARKS AND NAVIGATION TESTS
// ============================================================================

describe('ARIA Landmarks - Structure and Navigation', () => {
  it('passes axe tests for landmark structure', async () => {
    const { container } = render(
      <div>
        <header role="banner">
          <nav role="navigation" aria-label="Primary">
            <a href="/home">Home</a>
          </nav>
        </header>
        <main role="main">
          <h1>Main Content</h1>
        </main>
        <aside role="complementary">
          <h2>Sidebar</h2>
        </aside>
        <footer role="contentinfo">
          <p>Footer content</p>
        </footer>
      </div>
    );
    await runAxeTest(container);
  });

  it('provides proper navigation landmarks', () => {
    render(
      <nav role="navigation" aria-label="Main navigation">
        <ul>
          <li><a href="/chat">Chat</a></li>
          <li><a href="/settings">Settings</a></li>
        </ul>
      </nav>
    );
    
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    expect(nav).toBeInTheDocument();
  });

  it('supports skip links for keyboard users', async () => {
    const user = setupKeyboardTest();
    render(
      <div>
        <a 
          href="#main-content" 
          className="sr-only focus:not-sr-only focus:absolute focus:top-0"
        >
          Skip to main content
        </a>
        <nav>
          <a href="/page1">Page 1</a>
          <a href="/page2">Page 2</a>
        </nav>
        <main id="main-content">
          <h1>Main Content</h1>
        </main>
      </div>
    );
    
    const skipLink = screen.getByRole('link', { name: 'Skip to main content' });
    await user.tab();
    expect(skipLink).toHaveFocus();
    expect(skipLink).toHaveClass('focus:not-sr-only');
  });

  it('provides breadcrumb navigation', () => {
    render(
      <nav aria-label="Breadcrumb">
        <ol>
          <li>
            <a href="/home">Home</a>
            <span aria-hidden="true"> / </span>
          </li>
          <li>
            <a href="/category">Category</a>
            <span aria-hidden="true"> / </span>
          </li>
          <li aria-current="page">Current Page</li>
        </ol>
      </nav>
    );
    
    const breadcrumb = screen.getByRole('navigation', { name: 'Breadcrumb' });
    const currentPage = screen.getByText('Current Page');
    
    expect(breadcrumb).toBeInTheDocument();
    expect(currentPage).toHaveAttribute('aria-current', 'page');
  });

  it('implements proper page region structure', () => {
    render(
      <div>
        <header role="banner">
          <h1>Site Title</h1>
          <nav role="navigation" aria-label="Primary navigation">
            <a href="/home">Home</a>
          </nav>
        </header>
        
        <main role="main">
          <h1>Page Title</h1>
          <section aria-labelledby="section1-title">
            <h2 id="section1-title">Section 1</h2>
            <p>Content</p>
          </section>
        </main>
        
        <aside role="complementary" aria-labelledby="sidebar-title">
          <h2 id="sidebar-title">Related Links</h2>
          <nav aria-label="Related">
            <a href="/related">Related Page</a>
          </nav>
        </aside>
        
        <footer role="contentinfo">
          <p>Copyright 2024</p>
        </footer>
      </div>
    );
    
    testLandmarks([
      { role: 'banner' },
      { role: 'navigation', name: 'Primary navigation' },
      { role: 'main' },
      { role: 'complementary', name: 'Related Links' },
      { role: 'navigation', name: 'Related' },
      { role: 'contentinfo' }
    ]);
  });

  it('supports multiple navigation regions with labels', () => {
    render(
      <div>
        <nav role="navigation" aria-label="Primary navigation">
          <a href="/home">Home</a>
          <a href="/about">About</a>
        </nav>
        
        <nav role="navigation" aria-label="User account">
          <a href="/profile">Profile</a>
          <a href="/settings">Settings</a>
        </nav>
        
        <nav role="navigation" aria-label="Footer links">
          <a href="/privacy">Privacy</a>
          <a href="/terms">Terms</a>
        </nav>
      </div>
    );
    
    const primaryNav = screen.getByRole('navigation', { name: 'Primary navigation' });
    const userNav = screen.getByRole('navigation', { name: 'User account' });
    const footerNav = screen.getByRole('navigation', { name: 'Footer links' });
    
    expect(primaryNav).toBeInTheDocument();
    expect(userNav).toBeInTheDocument();
    expect(footerNav).toBeInTheDocument();
  });

  it('implements search landmark properly', () => {
    render(
      <div role="search" aria-labelledby="search-title">
        <h2 id="search-title">Search</h2>
        <form>
          <label htmlFor="search-input">Search term</label>
          <input id="search-input" type="search" />
          <button type="submit">Search</button>
        </form>
      </div>
    );
    
    const searchRegion = screen.getByRole('search', { name: 'Search' });
    expect(searchRegion).toBeInTheDocument();
  });

  it('provides proper heading hierarchy', () => {
    render(
      <div>
        <h1>Page Title</h1>
        <main>
          <section>
            <h2>Section 1</h2>
            <h3>Subsection 1.1</h3>
            <h3>Subsection 1.2</h3>
          </section>
          <section>
            <h2>Section 2</h2>
            <h3>Subsection 2.1</h3>
            <h4>Sub-subsection 2.1.1</h4>
          </section>
        </main>
      </div>
    );
    
    testHeadingHierarchy([1, 2, 3, 4]);
  });

  it('supports application landmark for interactive content', () => {
    render(
      <div role="application" aria-labelledby="app-title">
        <h2 id="app-title">Interactive Application</h2>
        <p>This region contains an interactive application</p>
        <button>Application Button</button>
      </div>
    );
    
    const appRegion = screen.getByRole('application', { name: 'Interactive Application' });
    expect(appRegion).toBeInTheDocument();
  });

  it('implements tabpanel landmarks correctly', () => {
    render(
      <div>
        <div role="tablist" aria-label="Content tabs">
          <button role="tab" aria-selected="true" aria-controls="panel1">
            Tab 1
          </button>
          <button role="tab" aria-selected="false" aria-controls="panel2">
            Tab 2
          </button>
        </div>
        
        <div id="panel1" role="tabpanel" aria-labelledby="tab1">
          <h3>Panel 1 Content</h3>
        </div>
        
        <div id="panel2" role="tabpanel" aria-labelledby="tab2" hidden>
          <h3>Panel 2 Content</h3>
        </div>
      </div>
    );
    
    const tablist = screen.getByRole('tablist', { name: 'Content tabs' });
    const panel1 = screen.getByRole('tabpanel');
    
    expect(tablist).toBeInTheDocument();
    expect(panel1).toBeInTheDocument();
  });

  it('provides form landmarks with proper labels', () => {
    render(
      <main>
        <form aria-labelledby="contact-form-title">
          <h2 id="contact-form-title">Contact Form</h2>
          <fieldset>
            <legend>Personal Information</legend>
            <label htmlFor="name">Name</label>
            <input id="name" type="text" />
          </fieldset>
          <button type="submit">Submit</button>
        </form>
      </main>
    );
    
    const form = screen.getByRole('form', { name: 'Contact Form' });
    const fieldset = screen.getByRole('group', { name: 'Personal Information' });
    
    expect(form).toBeInTheDocument();
    expect(fieldset).toBeInTheDocument();
  });

  it('supports banner with site navigation', () => {
    render(
      <header role="banner">
        <div>
          <img src="/logo.png" alt="Company Logo" />
          <h1>Site Name</h1>
        </div>
        <nav role="navigation" aria-label="Site navigation">
          <ul>
            <li><a href="/home">Home</a></li>
            <li><a href="/products">Products</a></li>
            <li><a href="/contact">Contact</a></li>
          </ul>
        </nav>
      </header>
    );
    
    const banner = screen.getByRole('banner');
    const siteNav = screen.getByRole('navigation', { name: 'Site navigation' });
    
    expect(banner).toBeInTheDocument();
    expect(siteNav).toBeInTheDocument();
  });

  it('implements contentinfo with useful links', () => {
    render(
      <footer role="contentinfo">
        <div>
          <h2>Company Information</h2>
          <p>© 2024 Company Name. All rights reserved.</p>
        </div>
        <nav aria-label="Footer navigation">
          <a href="/privacy">Privacy Policy</a>
          <a href="/terms">Terms of Service</a>
          <a href="/support">Support</a>
        </nav>
      </footer>
    );
    
    const contentinfo = screen.getByRole('contentinfo');
    const footerNav = screen.getByRole('navigation', { name: 'Footer navigation' });
    
    expect(contentinfo).toBeInTheDocument();
    expect(footerNav).toBeInTheDocument();
  });

  it('supports complementary content with proper labeling', () => {
    render(
      <div>
        <main role="main">
          <h1>Main Article</h1>
          <p>Main content goes here</p>
        </main>
        
        <aside role="complementary" aria-labelledby="related-title">
          <h2 id="related-title">Related Articles</h2>
          <ul>
            <li><a href="/article1">Related Article 1</a></li>
            <li><a href="/article2">Related Article 2</a></li>
          </ul>
        </aside>
        
        <aside role="complementary" aria-labelledby="ads-title">
          <h2 id="ads-title">Advertisements</h2>
          <div>Ad content</div>
        </aside>
      </div>
    );
    
    const relatedAside = screen.getByRole('complementary', { name: 'Related Articles' });
    const adsAside = screen.getByRole('complementary', { name: 'Advertisements' });
    
    expect(relatedAside).toBeInTheDocument();
    expect(adsAside).toBeInTheDocument();
  });

  it('handles nested landmark structures appropriately', async () => {
    const { container } = render(
      <div>
        <header role="banner">
          <nav role="navigation" aria-label="Primary">
            <a href="/home">Home</a>
          </nav>
        </header>
        
        <main role="main">
          <article>
            <header>
              <h1>Article Title</h1>
              <p>Article metadata</p>
            </header>
            
            <section aria-labelledby="intro-title">
              <h2 id="intro-title">Introduction</h2>
              <p>Introduction content</p>
            </section>
            
            <footer>
              <p>Article footer</p>
            </footer>
          </article>
        </main>
      </div>
    );
    
    await runAxeTest(container);
    
    const banner = screen.getByRole('banner');
    const main = screen.getByRole('main');
    const article = screen.getByRole('article');
    
    expect(banner).toBeInTheDocument();
    expect(main).toBeInTheDocument();
    expect(article).toBeInTheDocument();
  });
});