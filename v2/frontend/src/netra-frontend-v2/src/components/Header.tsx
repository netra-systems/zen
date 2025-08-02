"use client";

import React from 'react';
import { Navbar, NavbarBrand, NavbarContent, NavbarItem, Link, Button } from "@nextui-org/react";

export const Header = () => (
  <Navbar>
    <NavbarBrand>
      <p className="font-bold text-inherit">Netra</p>
    </NavbarBrand>
    <NavbarContent justify="end">
      <NavbarItem>
        <Button as={Link} color="primary" href="#" variant="flat">
          Logout
        </Button>
      </NavbarItem>
    </NavbarContent>
  </Navbar>
);
