'use client';

import { Button } from '@/components/ui/button';
import useAppStore from '@/store';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

export function Header({ toggleSidebar }: { toggleSidebar: () => void }) {
  const { user, logout } = useAppStore();

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-4 lg:h-[60px] lg:px-6">
      <Button variant="outline" size="icon" className="shrink-0 md:hidden" onClick={toggleSidebar}>
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
          <path d="M3 12h18M3 6h18M3 18h18" />
        </svg>
        <span className="sr-only">Toggle navigation menu</span>
      </Button>
      <div className="w-full flex-1">
        {/* Add search bar or other header content here */}
      </div>
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-2">
            <Avatar>
              <AvatarImage src={user.picture || ''} />
              <AvatarFallback>{user.full_name ? user.full_name.charAt(0) : user.email.charAt(0)}</AvatarFallback>
            </Avatar>
            <Button onClick={logout} variant="outline">Logout</Button>
          </div>
        )}
      </div>
    </header>
  );
}
