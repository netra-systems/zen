'use client';

import React from 'react';
import { WebSocketDemo } from '../components/WebSocketDemo';

const HomePage: React.FC = () => {
  return (
    <div>
      <h1>Netra</h1>
      <WebSocketDemo />
    </div>
  );
};

export default HomePage;
