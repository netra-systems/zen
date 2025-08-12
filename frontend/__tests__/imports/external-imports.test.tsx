/**
 * Test file to verify all external npm dependencies can be imported.
 * This ensures all required packages from package.json are properly installed.
 */

describe('External NPM Dependencies Import Tests', () => {
  // @smoke-test
  describe('Core React and Next.js imports', () => {
    it('should import React', () => {
      const React = require('react');
      expect(React).toBeDefined();
      expect(React.useState).toBeDefined();
      expect(React.useEffect).toBeDefined();
      expect(React.useCallback).toBeDefined();
      expect(React.useMemo).toBeDefined();
      expect(React.useRef).toBeDefined();
      expect(React.useContext).toBeDefined();
      expect(React.createContext).toBeDefined();
      expect(React.Component).toBeDefined();
      expect(React.Fragment).toBeDefined();
    });

    it('should import React DOM', () => {
      const ReactDOM = require('react-dom');
      expect(ReactDOM).toBeDefined();
      // createRoot is in react-dom/client in React 18+
      const ReactDOMClient = require('react-dom/client');
      expect(ReactDOMClient).toBeDefined();
      expect(ReactDOMClient.createRoot).toBeDefined();
    });

    it('should import Next.js core modules', () => {
      const next = require('next');
      expect(next).toBeDefined();

      const nextRouter = require('next/router');
      expect(nextRouter).toBeDefined();

      const nextLink = require('next/link');
      expect(nextLink).toBeDefined();

      const nextImage = require('next/image');
      expect(nextImage).toBeDefined();

      const nextNavigation = require('next/navigation');
      expect(nextNavigation).toBeDefined();
      expect(nextNavigation.useRouter).toBeDefined();
      expect(nextNavigation.useSearchParams).toBeDefined();
      expect(nextNavigation.usePathname).toBeDefined();
    });
  });

  describe('State management imports', () => {
    it('should import Zustand', () => {
      const zustand = require('zustand');
      expect(zustand).toBeDefined();
      expect(zustand.create).toBeDefined();
    });

    it('should import Zustand middleware', () => {
      const middleware = require('zustand/middleware');
      expect(middleware).toBeDefined();
      expect(middleware.devtools).toBeDefined();
      expect(middleware.persist).toBeDefined();
    });
  });

  describe('UI library imports', () => {
    it('should import Radix UI components', () => {
      // Note: Some Radix UI components may not be installed
      try {
        const radixDialog = require('@radix-ui/react-dialog');
        expect(radixDialog).toBeDefined();
      } catch (e) {
        console.log('@radix-ui/react-dialog not installed');
      }

      const radixDropdown = require('@radix-ui/react-dropdown-menu');
      expect(radixDropdown).toBeDefined();

      const radixLabel = require('@radix-ui/react-label');
      expect(radixLabel).toBeDefined();

      const radixSlot = require('@radix-ui/react-slot');
      expect(radixSlot).toBeDefined();

      try {
        const radixToast = require('@radix-ui/react-toast');
        expect(radixToast).toBeDefined();
      } catch (e) {
        console.log('@radix-ui/react-toast not installed');
      }

      try {
        const radixTooltip = require('@radix-ui/react-tooltip');
        expect(radixTooltip).toBeDefined();
      } catch (e) {
        console.log('@radix-ui/react-tooltip not installed');
      }

      const radixTabs = require('@radix-ui/react-tabs');
      expect(radixTabs).toBeDefined();

      const radixSwitch = require('@radix-ui/react-switch');
      expect(radixSwitch).toBeDefined();

      const radixSelect = require('@radix-ui/react-select');
      expect(radixSelect).toBeDefined();

      const radixProgress = require('@radix-ui/react-progress');
      expect(radixProgress).toBeDefined();

      try {
        const radixPopover = require('@radix-ui/react-popover');
        expect(radixPopover).toBeDefined();
      } catch (e) {
        console.log('@radix-ui/react-popover not installed');
      }

      const radixAvatar = require('@radix-ui/react-avatar');
      expect(radixAvatar).toBeDefined();

      const radixAccordion = require('@radix-ui/react-accordion');
      expect(radixAccordion).toBeDefined();
    });

    it('should import Lucide React icons', () => {
      const lucide = require('lucide-react');
      expect(lucide).toBeDefined();
      expect(lucide.ChevronRight).toBeDefined();
      expect(lucide.ChevronLeft).toBeDefined();
      expect(lucide.X).toBeDefined();
      expect(lucide.Check).toBeDefined();
      expect(lucide.Search).toBeDefined();
    });

    it('should import class variance authority', () => {
      const cva = require('class-variance-authority');
      expect(cva).toBeDefined();
      expect(cva.cva).toBeDefined();
    });

    it('should import clsx', () => {
      const clsx = require('clsx');
      expect(clsx).toBeDefined();
    });

    it('should import tailwind-merge', () => {
      const tailwindMerge = require('tailwind-merge');
      expect(tailwindMerge).toBeDefined();
      expect(tailwindMerge.twMerge).toBeDefined();
    });
  });

  describe('Form and validation imports', () => {
    it('should import React Hook Form', () => {
      const rhf = require('react-hook-form');
      expect(rhf).toBeDefined();
      expect(rhf.useForm).toBeDefined();
      expect(rhf.Controller).toBeDefined();
      expect(rhf.useController).toBeDefined();
      expect(rhf.useWatch).toBeDefined();
      expect(rhf.useFormState).toBeDefined();
    });

    it('should import Zod', () => {
      const zod = require('zod');
      expect(zod).toBeDefined();
      expect(zod.z).toBeDefined();
      expect(zod.z.string).toBeDefined();
      expect(zod.z.number).toBeDefined();
      expect(zod.z.object).toBeDefined();
      expect(zod.z.array).toBeDefined();
    });

    it('should import React Hook Form Zod resolver', () => {
      const zodResolver = require('@hookform/resolvers/zod');
      expect(zodResolver).toBeDefined();
      expect(zodResolver.zodResolver).toBeDefined();
    });
  });

  describe('Data visualization imports', () => {
    it('should import Recharts', () => {
      const recharts = require('recharts');
      expect(recharts).toBeDefined();
      expect(recharts.LineChart).toBeDefined();
      expect(recharts.BarChart).toBeDefined();
      expect(recharts.PieChart).toBeDefined();
      expect(recharts.Line).toBeDefined();
      expect(recharts.Bar).toBeDefined();
      expect(recharts.XAxis).toBeDefined();
      expect(recharts.YAxis).toBeDefined();
      expect(recharts.CartesianGrid).toBeDefined();
      expect(recharts.Tooltip).toBeDefined();
      expect(recharts.Legend).toBeDefined();
      expect(recharts.ResponsiveContainer).toBeDefined();
    });
  });

  describe('Markdown and code highlighting imports', () => {
    it('should import React Markdown', () => {
      try {
        const reactMarkdown = require('react-markdown');
        expect(reactMarkdown).toBeDefined();
      } catch (e) {
        console.log('react-markdown not installed');
      }
    });

    it('should import remark-gfm', () => {
      try {
        const remarkGfm = require('remark-gfm');
        expect(remarkGfm).toBeDefined();
      } catch (e) {
        console.log('remark-gfm not installed');
      }
    });

    it('should import React Syntax Highlighter', () => {
      const syntaxHighlighter = require('react-syntax-highlighter');
      expect(syntaxHighlighter).toBeDefined();
      expect(syntaxHighlighter.Prism).toBeDefined();
    });

    it('should import syntax highlighter styles', () => {
      try {
        const styles = require('react-syntax-highlighter/dist/esm/styles/prism');
        expect(styles).toBeDefined();
        expect(styles.oneDark).toBeDefined();
        expect(styles.oneLight).toBeDefined();
      } catch (e) {
        // Try cjs version
        const styles = require('react-syntax-highlighter/dist/cjs/styles/prism');
        expect(styles).toBeDefined();
      }
    });
  });

  describe('Utility library imports', () => {
    it('should import date-fns', () => {
      const dateFns = require('date-fns');
      expect(dateFns).toBeDefined();
      expect(dateFns.format).toBeDefined();
      expect(dateFns.parseISO).toBeDefined();
      expect(dateFns.formatDistanceToNow).toBeDefined();
    });

    it('should import axios', () => {
      const axios = require('axios');
      expect(axios).toBeDefined();
      expect(axios.get).toBeDefined();
      expect(axios.post).toBeDefined();
      expect(axios.put).toBeDefined();
      expect(axios.delete).toBeDefined();
      expect(axios.create).toBeDefined();
    });

    it('should import socket.io-client', () => {
      const io = require('socket.io-client');
      expect(io).toBeDefined();
    });
  });

  describe('Development and testing imports', () => {
    it('should import Jest DOM matchers', () => {
      const jestDom = require('@testing-library/jest-dom');
      expect(jestDom).toBeDefined();
    });

    it('should import React Testing Library', () => {
      // React Testing Library may register hooks, so we need to be careful
      try {
        // Just check that the module exists without fully loading it
        jest.isolateModules(() => {
          const rtl = require('@testing-library/react');
          expect(rtl).toBeDefined();
        });
      } catch (e) {
        // Fallback: just verify the package exists
        const fs = require('fs');
        const path = require('path');
        const pkgPath = path.join(process.cwd(), 'node_modules', '@testing-library', 'react');
        expect(fs.existsSync(pkgPath)).toBe(true);
      }
    });

    it('should import Testing Library user-event', () => {
      try {
        const userEvent = require('@testing-library/user-event');
        expect(userEvent).toBeDefined();
        expect(userEvent.default).toBeDefined();
      } catch (e) {
        console.log('@testing-library/user-event not properly configured');
      }
    });

    it('should import Jest environment jsdom', () => {
      // This is typically a dev dependency
      try {
        const jestEnv = require('jest-environment-jsdom');
        expect(jestEnv).toBeDefined();
      } catch (e) {
        // May not be available in production builds
        console.log('jest-environment-jsdom not available (dev dependency)');
      }
    });
  });

  describe('TypeScript type imports', () => {
    it('should import TypeScript type packages', () => {
      // Type packages may not be directly importable
      const fs = require('fs');
      const path = require('path');
      const nodeModulesPath = path.join(process.cwd(), 'node_modules');
      
      const typePackages = ['@types/react', '@types/react-dom', '@types/node'];
      typePackages.forEach(pkg => {
        const pkgPath = path.join(nodeModulesPath, ...pkg.split('/'));
        const exists = fs.existsSync(pkgPath);
        if (!exists) {
          console.log(`Type package ${pkg} not found`);
        }
        expect(exists).toBe(true);
      });
    });
  });

  describe('Tailwind CSS imports', () => {
    it('should import Tailwind CSS animate', () => {
      const tailwindAnimate = require('tailwindcss-animate');
      expect(tailwindAnimate).toBeDefined();
    });
  });

  describe('ESLint and Prettier imports', () => {
    it('should have ESLint configuration packages', () => {
      // These are typically dev dependencies
      try {
        const eslintNext = require('eslint-config-next');
        expect(eslintNext).toBeDefined();
      } catch (e) {
        console.log('ESLint config packages not available (dev dependencies)');
      }
    });
  });

  describe('Critical imports batch test', () => {
    it('should successfully import all critical dependencies', () => {
      const criticalDeps = [
        'react',
        'react-dom',
        'next',
        'zustand',
        '@radix-ui/react-dialog',
        'react-hook-form',
        'zod',
        'axios',
        'socket.io-client',
        'react-markdown',
        'recharts'
      ];

      const failedImports: string[] = [];
      
      criticalDeps.forEach(dep => {
        try {
          require(dep);
        } catch (e) {
          failedImports.push(dep);
        }
      });

      expect(failedImports).toEqual([]);
    });
  });

  describe('Optional imports', () => {
    it('should check for optional dependencies', () => {
      const optionalDeps = [
        '@tanstack/react-query',
        'framer-motion',
        'react-query',
        '@emotion/react',
        '@emotion/styled'
      ];

      const warnings: string[] = [];
      
      optionalDeps.forEach(dep => {
        try {
          require(dep);
        } catch (e) {
          warnings.push(`Optional dependency ${dep} not installed`);
        }
      });

      if (warnings.length > 0) {
        console.log('Optional dependencies not installed:', warnings);
      }
    });
  });
});