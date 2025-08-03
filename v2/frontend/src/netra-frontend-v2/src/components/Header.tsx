"use client";

import React from 'react';
import { Navbar, NavbarBrand, NavbarContent, NavbarItem, Link, Button, Avatar } from "@nextui-org/react";
import { useAppStore } from '../store';

export const Header = () => {
  const { user, logout } = useAppStore();

  return (
    <Navbar>
      <NavbarBrand>
        <p className="font-bold text-inherit">Netra</p>
      </NavbarBrand>
      <NavbarContent justify="end">
        <NavbarItem>
          {user ? (
            <div className="flex items-center gap-4">
              <Avatar name={user.full_name} size="sm" />
              <span>{user.full_name}</span>
              <Button as={Link} color="primary" href="#" variant="flat" onPress={logout}>
                Logout
              </Button>
            </div>
          ) : (
            <Button as={Link} color="primary" href="/login" variant="flat">
              Login
            </Button>
          )}
        </NavbarItem>
      </NavbarContent>
    </Navbar>
  );
};
