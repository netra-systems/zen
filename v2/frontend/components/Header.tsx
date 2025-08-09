'use client';

import React from 'react';
import Link from 'next/link';
;
import { Button } from './ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from './ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Icons } from './Icons';
import { authService } from '@/auth';
import LoginButton from './LoginButton';

import { HeaderProps } from '../types';

export const Header = ({ toggleSidebar }: HeaderProps) => {
  const { user, logout } = authService.useAuth();

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