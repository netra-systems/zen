"use client";

import React from 'react';
import {
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  Link,
  Button,
  Avatar,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem
} from "@nextui-org/react";
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
            <Dropdown placement="bottom-end">
              <DropdownTrigger>
                <Avatar
                  isBordered
                  as="button"
                  className="transition-transform"
                  color="secondary"
                  name={user.full_name}
                  size="sm"
                  src={user.picture}
                />
              </DropdownTrigger>
              <DropdownMenu aria-label="Profile Actions" variant="flat">
                <DropdownItem key="profile" className="h-14 gap-2">
                  <p className="font-semibold">Signed in as</p>
                  <p className="font-semibold">{user.email}</p>
                </DropdownItem>
                <DropdownItem key="logout" color="danger" onPress={logout}>
                  Log Out
                </DropdownItem>
              </DropdownMenu>
            </Dropdown>
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
