
import Link from 'next/link';
import { Icons } from '@/components/Icons';
import { useAuth } from '../hooks/useAuth';

import { NavItem } from '@/types';

const navItems: NavItem[] = [
  {
    href: '/',
    icon: <Icons.home className="h-4 w-4" />,
    label: 'Dashboard',
  },
  {
    href: '/generation',
    icon: <Icons.syntheticData className="h-4 w-4" />,
    label: 'Synthetic Data',
  },
  {
    href: '/corpus-admin',
    icon: <Icons.corpusAdmin className="h-4 w-4" />,
    label: 'Corpus Admin',
  },
  {
    href: '/chat',
    icon: <Icons.apexOptimizer className="h-4 w-4" />,
    label: 'Chat',
  },
  {
    href: '#',
    icon: <Icons.ingestion className="h-4 w-4" />,
    label: 'Ingestion',
    disabled: true,
  },
  {
    href: '#',
    icon: <Icons.supplyCatalog className="h-4 w-4" />,
    label: 'Supply Catalog',
    disabled: true,
  },
  {
    href: '#',
    icon: <Icons.settings className="h-4 w-4" />,
    label: 'Settings',
    disabled: true,
  },
];

export function NavLinks() {
  const { user } = useAuth();

  return (
    <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
      {user ? (
        navItems.map(({ href, icon, label, disabled }) => (
          <Link
            key={label}
            href={href}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary ${
              disabled ? 'cursor-not-allowed pointer-events-none opacity-50' : ''
            }`}
          >
            {icon}
            {label}
          </Link>
        ))
      ) : (
        <Link
          href="/login"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary"
        >
          <Icons.dev className="h-4 w-4" />
          Login
        </Link>
      )}
    </nav>
  );
}
