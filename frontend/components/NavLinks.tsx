
import Link from 'next/link';
import { Icons } from '@/components/Icons';
import { authService } from '@/auth';

interface NavItem {
  href: string;
  icon: React.ReactNode;
  label: string;
  disabled?: boolean;
  placeholder?: boolean;
}

const navItems: NavItem[] = [
  {
    href: '/chat',
    icon: <Icons.apexOptimizer className="h-4 w-4" />,
    label: 'Chat',
  },
];

export function NavLinks() {
  const { user } = authService.useAuth();

  return (
    <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
      {user ? (
        navItems.map(({ href, icon, label, disabled, placeholder }) => (
          <Link
            key={label}
            href={href}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all duration-200 ${
              disabled 
                ? 'cursor-not-allowed pointer-events-none opacity-50' 
                : 'hover:text-primary hover:bg-accent hover:scale-[1.02] active:scale-[0.98] cursor-pointer'
            }`}
          >
            {icon}
            <span className="flex-1 flex items-center justify-between">
              {label}
              {placeholder && (
                <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded">
                  Coming Soon
                </span>
              )}
            </span>
          </Link>
        ))
      ) : (
        <Link
          href="/login"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all duration-200 hover:text-primary hover:bg-accent hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
        >
          <Icons.dev className="h-4 w-4" />
          Login
        </Link>
      )}
    </nav>
  );
}
