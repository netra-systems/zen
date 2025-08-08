'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from './ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from './ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Icons } from './Icons';

import { HeaderProps } from '../types';

export const Header = ({ toggleSidebar }: HeaderProps) => {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-4 lg:h-[60px] lg:px-6">
      <Button variant="outline" size="icon" className="shrink-0 md:hidden" onClick={toggleSidebar}>
        <Icons.logo className="h-5 w-5" />
        <span className="sr-only">Toggle navigation menu</span>
      </Button>
      <div className="w-full flex-1">
        {/* Add search bar here if needed */}
      </div>
      {user ? (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="secondary" size="icon" className="rounded-full">
              <Avatar className="h-8 w-8">
                {user.picture ? (
                  <>
                    <AvatarImage
                      src={user.picture}
                      alt={user.full_name || 'User'}
                      onError={(e) => {
                        console.error('Error loading profile image:', e);
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                      }}
                    />
                    <AvatarFallback>
                      {user.full_name && user.full_name
                        .split(' ')
                        .map((n) => n[0])
                        .join('')}
                    </AvatarFallback>
                  </>
                ) : (
                  <AvatarFallback>
                    {user.full_name && user.full_name
                      .split(' ')
                      .map((n) => n[0])
                      .join('')}
                  </AvatarFallback>
                )}
              </Avatar>
              <span className="sr-only">Toggle user menu</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{user.full_name}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Settings</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout}>Logout</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ) : (
        <Button asChild variant="outline">
          <Link href="/login">Login</Link>
        </Button>
      )}
    </header>
  );
};