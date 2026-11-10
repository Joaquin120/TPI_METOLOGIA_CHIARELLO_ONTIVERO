import React, { ReactNode } from 'react';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';

export const Layout: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <div className="app-layout" data-testid="app-layout">
      <Navbar />
      <div className="layout-body">
        <Sidebar />
        <main className="main-content" data-testid="main-content">
          {children}
        </main>
      </div>
    </div>
  );
};
