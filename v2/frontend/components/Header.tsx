'use client';

import React from 'react';
;
import { Button } from './ui/button';
import { Icons } from './Icons';
import LoginButton from './LoginButton';

interface HeaderProps {
  toggleSidebar: () => void;
}

export const Header = ({ toggleSidebar }: HeaderProps) => {

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-4 lg:h-[60px] lg:px-6">
      <Button variant="outline" size="icon" className="shrink-0 md:hidden" onClick={toggleSidebar}>
        <Icons.logo className="h-5 w-5" />
        <span className="sr-only">Toggle navigation menu</span>
      </Button>
      <div className="w-full flex-1">
        {/* Add search bar here if needed */}
      </div>
      <LoginButton />
    </header>
  );
};