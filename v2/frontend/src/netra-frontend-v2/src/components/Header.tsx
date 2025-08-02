"use client";

import React from 'react';
import { Navbar, NavbarBrand, NavbarContent, NavbarItem, Link, Button } from "@nextui-org/react";
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
            <Button as={Link} color="primary" href="#" variant="flat" onPress={logout}>
              Logout
            </Button>
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
